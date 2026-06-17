"""
supervisor_agent.py — Multi-Agent Orchestrator

Supervisor menerima pesan dari user, memilih agent yang paling tepat
dari registry, mendelegasikan pekerjaan, dan mengembalikan hasilnya.
Mendukung sequential dan parallel task decomposition.
"""

import logging
import re
import time
from typing import Any, Dict, List, Optional, Tuple

from .base_agent import BaseAgent
from .agent_registry import AgentRegistry

logger = logging.getLogger("framework.agents.supervisor")


class SupervisorAgent(BaseAgent):
    """
    Supervisor yang mengorkestrasi beberapa sub-agent.

    Alur:
    1. Terima pesan dari user
    2. Analisis pesan untuk menentukan agent yang tepat
    3. Delegasikan ke sub-agent
    4. Gabungkan dan kembalikan hasil

    Routing bisa dilakukan via:
    - Keyword matching (ringan, cepat)
    - Model-based routing (lebih akurat, pakai LLM)
    """

    def __init__(
        self,
        name: str = "Supervisor",
        description: str = "Orchestrator yang mendelegasikan tugas ke sub-agent yang tepat",
        registry: Optional[AgentRegistry] = None,
        model_adapter: Optional[Any] = None,
        routing_mode: str = "keyword",  # "keyword" | "model"
    ):
        super().__init__(name, description)
        self.registry = registry or AgentRegistry()
        self.model_adapter = model_adapter
        self.routing_mode = routing_mode
        self._routing_table: List[Dict] = []  # [{keywords, agent_name, priority}]

    # ==================== ROUTING SETUP ====================

    def register_route(
        self,
        agent_name: str,
        keywords: List[str],
        priority: int = 0,
        patterns: Optional[List[str]] = None,
    ) -> "SupervisorAgent":
        """
        Daftarkan routing rule untuk sebuah agent.

        Args:
            agent_name: Nama agent tujuan.
            keywords: Kata kunci yang memicu routing ke agent ini.
            priority: Prioritas (lebih tinggi = lebih dipilih saat konflik).
            patterns: Regex patterns opsional.
        """
        self._routing_table.append({
            "agent_name": agent_name,
            "keywords": [k.lower() for k in keywords],
            "patterns": patterns or [],
            "priority": priority,
        })
        # Sort by priority descending
        self._routing_table.sort(key=lambda r: r["priority"], reverse=True)
        logger.debug(f"Route registered: {keywords} → {agent_name} (priority={priority})")
        return self

    # ==================== CORE INTERFACE ====================

    def can_handle(self, message: str, context: Optional[Dict] = None) -> bool:
        """Supervisor selalu dapat menangani — ia akan cari agent yang tepat."""
        return self.enabled

    def execute(self, message: str, context: Optional[Dict] = None) -> str:
        """
        Proses pesan: routing → delegasi → hasil.

        Args:
            message: Pesan dari user.
            context: Konteks tambahan.

        Returns:
            Hasil dari sub-agent, atau fallback response.
        """
        if not self.enabled:
            return "[Supervisor tidak aktif]"

        context = context or {}
        start_time = time.time()

        # 1. Route
        agent, routed_message = self._route(message, context)

        # 2. Delegasi
        if agent is None:
            logger.info(f"Supervisor: no agent found for '{message[:60]}'")
            result = self._fallback_response(message, context)
        else:
            logger.info(
                f"Supervisor: delegating to '{agent.name}' — '{routed_message[:60]}'"
            )
            try:
                result = agent.execute(routed_message, context)
                result = f"[{agent.name}]\n{result}"
            except Exception as e:
                logger.error(f"Agent '{agent.name}' failed: {e}", exc_info=True)
                result = f"[{agent.name} error: {type(e).__name__}]"

        duration_ms = (time.time() - start_time) * 1000
        self.log_execution(message, result, duration_ms)
        return result

    def execute_parallel(
        self, message: str, agent_names: List[str], context: Optional[Dict] = None
    ) -> Dict[str, str]:
        """
        Delegasikan pesan ke beberapa agent secara paralel.

        Args:
            message: Pesan yang sama dikirim ke semua agent.
            agent_names: Daftar nama agent tujuan.
            context: Konteks tambahan.

        Returns:
            Dict {agent_name: result}
        """
        import concurrent.futures

        context = context or {}
        results: Dict[str, str] = {}

        def run_agent(name: str) -> Tuple[str, str]:
            agent = self.registry.get(name)
            if agent is None:
                return name, f"[Agent '{name}' tidak ditemukan]"
            try:
                return name, agent.execute(message, context)
            except Exception as e:
                return name, f"[Error: {type(e).__name__}]"

        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = {executor.submit(run_agent, name): name for name in agent_names}
            for future in concurrent.futures.as_completed(futures):
                name, result = future.result()
                results[name] = result

        return results

    # ==================== ROUTING ENGINE ====================

    def _route(
        self, message: str, context: Dict
    ) -> Tuple[Optional[BaseAgent], str]:
        """
        Tentukan agent yang paling tepat untuk pesan ini.

        Returns:
            (agent_instance, transformed_message) atau (None, message)
        """
        if self.routing_mode == "model" and self.model_adapter:
            return self._route_by_model(message, context)
        return self._route_by_keyword(message, context)

    def _route_by_keyword(
        self, message: str, context: Dict
    ) -> Tuple[Optional[BaseAgent], str]:
        """Routing berbasis keyword matching dari routing table."""
        msg_lower = message.lower().strip()

        for route in self._routing_table:
            # Cek keywords
            for kw in route["keywords"]:
                if kw in msg_lower:
                    agent = self.registry.get(route["agent_name"])
                    if agent and agent.enabled:
                        return agent, message

            # Cek regex patterns
            for pattern in route.get("patterns", []):
                if re.search(pattern, msg_lower):
                    agent = self.registry.get(route["agent_name"])
                    if agent and agent.enabled:
                        return agent, message

        # Fallback: tanya tiap agent apakah bisa menangani
        for agent in self.registry.get_enabled():
            if agent.name != self.name and agent.can_handle(message, context):
                return agent, message

        return None, message

    def _route_by_model(
        self, message: str, context: Dict
    ) -> Tuple[Optional[BaseAgent], str]:
        """Routing menggunakan LLM untuk memilih agent yang paling tepat."""
        agents_info = self.registry.list_agents()
        agent_descriptions = "\n".join(
            [f"- {a['name']}: {a['description']}" for a in agents_info]
        )

        prompt = (
            f"Pilih agent yang paling tepat untuk menangani pesan berikut.\n\n"
            f"Daftar agent:\n{agent_descriptions}\n\n"
            f"Pesan user: {message}\n\n"
            f"Jawab HANYA dengan nama agent (contoh: FileAgent). "
            f"Jika tidak ada yang cocok, jawab: none"
        )

        try:
            response = self.model_adapter.complete(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,
            )
            chosen = response.get("content", "none").strip()
            agent = self.registry.get(chosen)
            if agent and agent.enabled:
                logger.info(f"Model routing chose: {chosen}")
                return agent, message
        except Exception as e:
            logger.warning(f"Model routing failed, falling back to keyword: {e}")

        return self._route_by_keyword(message, context)

    def _fallback_response(self, message: str, context: Dict) -> str:
        """Response ketika tidak ada agent yang bisa menangani."""
        return (
            "Maaf, tidak ada agent yang bisa menangani permintaan ini. "
            "Coba reformulasikan atau tambahkan agent yang sesuai."
        )

    # ==================== AGENT MANAGEMENT ====================

    def add_agent(self, agent: BaseAgent) -> "SupervisorAgent":
        """Tambah agent ke registry supervisor."""
        self.registry.register(agent)
        return self

    def get_agent_info(self) -> List[Dict]:
        """Info semua agent yang terdaftar."""
        return self.registry.list_agents()

    def get_routing_table(self) -> List[Dict]:
        """Tampilkan routing table saat ini."""
        return self._routing_table
