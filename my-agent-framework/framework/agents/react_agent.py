"""
react_agent.py — Implementasi ReAct (Reasoning + Acting) Loop

Pola ReAct: Thought → Action → Observation → (repeat) → Final Answer
Agent ini dapat memanggil tools secara iteratif berdasarkan reasoning
sampai menemukan jawaban atau mencapai max_iterations.
"""

import json
import logging
import time
from typing import Any, Dict, Iterator, List, Optional

from .base_agent import BaseAgent

logger = logging.getLogger("framework.agents.react")


class ReActAgent(BaseAgent):
    """
    Agent yang mengikuti pola ReAct loop:
    1. Thought  — agent berpikir apa yang perlu dilakukan
    2. Action   — agent memilih dan memanggil tool
    3. Observation — hasil tool dikembalikan sebagai observasi
    4. Repeat   — sampai selesai atau max_iterations

    Membutuhkan model adapter yang mendukung tool calling.
    """

    def __init__(
        self,
        name: str,
        description: str,
        model_adapter: Any,
        system_prompt: str = "",
        tools: Optional[List[Any]] = None,
        max_iterations: int = 10,
        temperature: float = 0.7,
    ):
        super().__init__(name, description, tools, max_iterations)
        self.model_adapter = model_adapter
        self.system_prompt = system_prompt or self._default_system_prompt()
        self.temperature = temperature

    def _default_system_prompt(self) -> str:
        return (
            "Kamu adalah agen AI yang dapat menggunakan tools untuk menyelesaikan tugas.\n"
            "Ikuti format berikut:\n"
            "Thought: [pikirkan apa yang perlu dilakukan]\n"
            "Action: [nama_tool]\n"
            "Action Input: [input untuk tool]\n"
            "Observation: [hasil tool]\n"
            "... (ulangi Thought/Action/Observation seperlunya)\n"
            "Final Answer: [jawaban akhir untuk user]\n"
        )

    def can_handle(self, message: str, context: Optional[Dict] = None) -> bool:
        """ReActAgent dapat menangani semua pesan umum."""
        return self.enabled and bool(message.strip())

    def execute(self, message: str, context: Optional[Dict] = None) -> str:
        """
        Jalankan ReAct loop untuk pesan yang diberikan.

        Args:
            message: Pertanyaan atau perintah dari user.
            context: Konteks tambahan (history, memory, dll).

        Returns:
            Final answer dari agent.
        """
        if not self.enabled:
            return "[Agent tidak aktif]"

        context = context or {}
        start_time = time.time()

        # Bangun pesan awal
        messages = self._build_initial_messages(message, context)

        # Tool definitions untuk model
        tool_schemas = self._build_tool_schemas()

        scratchpad: List[Dict] = []
        final_answer: Optional[str] = None

        logger.info(
            f"ReActAgent '{self.name}' starting — message='{message[:60]}...'"
        )

        for iteration in range(self.max_iterations):
            logger.debug(f"  Iteration {iteration + 1}/{self.max_iterations}")

            try:
                # Panggil model
                if tool_schemas:
                    response = self.model_adapter.complete(
                        messages=messages + scratchpad,
                        tools=tool_schemas,
                        temperature=self.temperature,
                    )
                else:
                    response = self.model_adapter.complete(
                        messages=messages + scratchpad,
                        temperature=self.temperature,
                    )

                # Parse response
                content = response.get("content", "")
                tool_calls = response.get("tool_calls", [])

                # Jika ada tool call
                if tool_calls:
                    for tc in tool_calls:
                        tool_name = tc.get("name", "")
                        tool_input = tc.get("arguments", {})

                        logger.info(
                            f"  Action: {tool_name}({json.dumps(tool_input)[:80]})"
                        )

                        # Eksekusi tool
                        observation = self._run_tool(tool_name, tool_input)
                        logger.info(f"  Observation: {str(observation)[:100]}")

                        # Tambah ke scratchpad
                        scratchpad.append(
                            {"role": "assistant", "content": content, "tool_calls": tool_calls}
                        )
                        scratchpad.append(
                            {
                                "role": "tool",
                                "tool_call_id": tc.get("id", tool_name),
                                "content": str(observation),
                            }
                        )
                    continue

                # Tidak ada tool call → final answer
                if "Final Answer:" in content:
                    final_answer = content.split("Final Answer:")[-1].strip()
                else:
                    final_answer = content.strip()

                logger.info(f"  Final answer found after {iteration + 1} iterations")
                break

            except Exception as e:
                logger.error(f"ReAct iteration {iteration + 1} failed: {e}", exc_info=True)
                final_answer = f"[Error pada iterasi {iteration + 1}: {type(e).__name__}]"
                break

        if final_answer is None:
            final_answer = "[Batas iterasi tercapai tanpa jawaban final]"

        duration_ms = (time.time() - start_time) * 1000
        self.log_execution(message, final_answer, duration_ms)

        return final_answer

    def stream(
        self, message: str, context: Optional[Dict] = None
    ) -> Iterator[str]:
        """
        Streaming ReAct loop — yield token per token dari model.
        Untuk tool calls, yield hasil observasi sebagai blok.
        """
        context = context or {}
        messages = self._build_initial_messages(message, context)

        try:
            for chunk in self.model_adapter.stream(
                messages=messages,
                tools=self._build_tool_schemas(),
                temperature=self.temperature,
            ):
                yield chunk
        except Exception as e:
            logger.error(f"ReAct stream failed: {e}")
            yield f"\n[Stream error: {type(e).__name__}]"

    # ==================== HELPERS ====================

    def _build_initial_messages(
        self, message: str, context: Dict
    ) -> List[Dict]:
        """Bangun message list awal dengan system prompt dan history."""
        messages = [{"role": "system", "content": self.system_prompt}]

        # Inject memory dari context
        if "memory" in context:
            memory_text = context["memory"]
            if memory_text:
                messages.append(
                    {"role": "system", "content": f"Konteks memori:\n{memory_text}"}
                )

        # Inject conversation history
        if "history" in context:
            history = context["history"]
            # Ambil 6 pesan terakhir
            messages.extend(history[-6:])

        # Tambah pesan user
        messages.append({"role": "user", "content": message})
        return messages

    def _build_tool_schemas(self) -> List[Dict]:
        """Bangun schema tool untuk dikirim ke model."""
        schemas = []
        for tool in self.tools:
            if hasattr(tool, "get_schema"):
                schemas.append(tool.get_schema())
        return schemas

    def _run_tool(self, tool_name: str, tool_input: Dict) -> str:
        """Jalankan tool berdasarkan nama dan input."""
        tool = self.get_tool(tool_name)
        if tool is None:
            return f"[Tool '{tool_name}' tidak ditemukan. Tersedia: {self.list_tools()}]"

        try:
            if hasattr(tool, "run"):
                return str(tool.run(**tool_input))
            elif callable(tool):
                return str(tool(**tool_input))
            else:
                return f"[Tool '{tool_name}' tidak bisa dipanggil]"
        except Exception as e:
            logger.error(f"Tool '{tool_name}' execution failed: {e}")
            return f"[Error tool '{tool_name}': {type(e).__name__}: {e}]"
