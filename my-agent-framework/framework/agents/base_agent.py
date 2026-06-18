"""
base_agent.py — Abstract Base Class untuk semua Agent

Semua agent dalam framework ini harus mewarisi kelas ini.
Menyediakan lifecycle hooks, tool access, execution history,
dan interface standar untuk agent loop.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, Iterator, List, Optional


class BaseAgent(ABC):
    """
    Abstract base class untuk semua agent dalam framework.

    Subclass wajib mengimplementasikan:
    - can_handle(message) → bool
    - execute(message, context) → str

    Subclass opsional override:
    - stream(message, context) → Iterator[str]
    - on_init() — dipanggil setelah __init__
    - on_shutdown() — cleanup saat agent dimatikan
    """

    def __init__(
        self,
        name: str,
        description: str,
        tools: Optional[List[Any]] = None,
        max_iterations: int = 10,
    ):
        self.name = name
        self.description = description
        self.tools: List[Any] = tools or []
        self.max_iterations = max_iterations
        self.enabled: bool = True
        self.metadata: Dict[str, Any] = {}
        self._execution_history: List[Dict] = []
        self.on_init()

    # ==================== LIFECYCLE ====================

    def on_init(self):
        """Hook dipanggil setelah inisialisasi. Override untuk setup tambahan."""
        pass

    def on_shutdown(self):
        """Hook dipanggil saat agent dimatikan. Override untuk cleanup."""
        pass

    def enable(self) -> "BaseAgent":
        """Aktifkan agent."""
        self.enabled = True
        return self

    def disable(self) -> "BaseAgent":
        """Nonaktifkan agent."""
        self.enabled = False
        return self

    # ==================== CORE INTERFACE ====================

    @abstractmethod
    def can_handle(self, message: str, context: Optional[Dict] = None) -> bool:
        """
        Tentukan apakah agent ini bisa menangani pesan.

        Args:
            message: Pesan atau perintah dari user/supervisor.
            context: Konteks tambahan (session, history, dll).

        Returns:
            True jika agent mampu menangani pesan ini.
        """
        pass

    @abstractmethod
    def execute(self, message: str, context: Optional[Dict] = None) -> str:
        """
        Eksekusi pesan dan kembalikan hasil sebagai string.

        Args:
            message: Pesan yang akan diproses.
            context: Konteks tambahan (session, memory, dll).

        Returns:
            Hasil eksekusi sebagai string.
        """
        pass

    def stream(
        self, message: str, context: Optional[Dict] = None
    ) -> Iterator[str]:
        """
        Streaming response (token by token).
        Default: jalankan execute() lalu yield hasilnya sekaligus.
        Override untuk implementasi streaming asli.

        Args:
            message: Pesan yang akan diproses.
            context: Konteks tambahan.

        Yields:
            Token atau chunk teks.
        """
        result = self.execute(message, context)
        yield result

    # ==================== REACT LOOP CONTRACT (Sprint 0) ====================
    # Method ini memetakan ke fase ReAct loop.
    # Subclass dapat override untuk perilaku kustom per fase.

    def think(self, goal: str, context: Optional[Dict] = None) -> str:
        """
        Fase Think (Plan) — tentukan langkah berikutnya untuk mencapai goal.

        Dipanggil oleh AgentLoop.Planner setiap iterasi.
        Default: delegasi ke execute(). Override untuk logika planning kustom.

        Args:
            goal: Goal atau instruksi yang sedang dikerjakan.
            context: Konteks saat ini (memory, previous observations, dll).

        Returns:
            Rencana atau keputusan langkah berikutnya sebagai string.
        """
        return self.execute(goal, context)

    def act(self, action: str, tool_name: Optional[str] = None, tool_input: Optional[Dict] = None) -> str:
        """
        Fase Act — jalankan aksi (panggil tool atau buat output langsung).

        Dipanggil oleh AgentLoop.Executor.
        Default: jalankan tool jika ada, atau kembalikan action sebagai output.

        Args:
            action: Deskripsi aksi yang akan diambil.
            tool_name: Nama tool yang akan dipanggil (opsional).
            tool_input: Input untuk tool (opsional).

        Returns:
            Hasil dari aksi sebagai string.
        """
        if tool_name:
            tool = self.get_tool(tool_name)
            if tool:
                try:
                    result = tool.run(**(tool_input or {}))
                    return str(result)
                except Exception as e:
                    return f"[Tool error: {e}]"
        return action

    def observe(self, action_result: str, context: Optional[Dict] = None) -> str:
        """
        Fase Observe — proses hasil aksi menjadi observasi yang berguna.

        Dipanggil oleh AgentLoop.Observer.
        Default: kembalikan hasil aksi apa adanya.

        Args:
            action_result: Output dari fase Act.
            context: Konteks saat ini.

        Returns:
            Observasi yang telah diproses.
        """
        return action_result

    def reflect(self, goal: str, observations: List[str], context: Optional[Dict] = None) -> bool:
        """
        Fase Reflect — evaluasi apakah goal sudah tercapai.

        Dipanggil oleh AgentLoop.Reflector.
        Default: anggap selesai jika sudah ada setidaknya satu observasi.
        Override untuk logika evaluasi yang lebih canggih.

        Args:
            goal: Goal awal yang ingin dicapai.
            observations: List semua observasi yang telah dikumpulkan.
            context: Konteks saat ini.

        Returns:
            True jika goal sudah tercapai, False jika perlu iterasi lagi.
        """
        return len(observations) > 0

    # ==================== TOOL ACCESS ====================

    def get_tool(self, tool_name: str) -> Optional[Any]:
        """Cari tool berdasarkan nama."""
        for tool in self.tools:
            if hasattr(tool, "name") and tool.name == tool_name:
                return tool
        return None

    def add_tool(self, tool: Any) -> "BaseAgent":
        """Tambahkan tool ke agent."""
        self.tools.append(tool)
        return self

    def list_tools(self) -> List[str]:
        """Daftar nama tool yang dimiliki agent."""
        return [t.name for t in self.tools if hasattr(t, "name")]

    # ==================== HISTORY & METADATA ====================

    def log_execution(
        self,
        message: str,
        result: str,
        duration_ms: Optional[float] = None,
        error: Optional[str] = None,
    ):
        """Catat satu eksekusi ke history."""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "agent": self.name,
            "message": message[:200],
            "result": result[:500],
        }
        if duration_ms is not None:
            entry["duration_ms"] = round(duration_ms, 2)
        if error:
            entry["error"] = error
        self._execution_history.append(entry)
        # Jaga agar history tidak terlalu besar
        if len(self._execution_history) > 200:
            self._execution_history.pop(0)

    def get_history(self, last_n: int = 20) -> List[Dict]:
        """Ambil N eksekusi terakhir."""
        return self._execution_history[-last_n:]

    def clear_history(self):
        """Bersihkan execution history."""
        self._execution_history.clear()

    def get_info(self) -> Dict:
        """Ringkasan info agent untuk registry/API."""
        return {
            "name": self.name,
            "description": self.description,
            "enabled": self.enabled,
            "tools": self.list_tools(),
            "max_iterations": self.max_iterations,
            "executions": len(self._execution_history),
            "metadata": self.metadata,
        }

    def set_metadata(self, key: str, value: Any) -> "BaseAgent":
        """Set metadata key-value."""
        self.metadata[key] = value
        return self

    # ==================== DUNDER ====================

    def __repr__(self) -> str:
        status = "enabled" if self.enabled else "disabled"
        return f"<Agent name={self.name!r} status={status} tools={len(self.tools)}>"

    def __str__(self) -> str:
        return f"{self.name}: {self.description}"
