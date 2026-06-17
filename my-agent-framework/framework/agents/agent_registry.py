"""
agent_registry.py — Registry & Factory untuk semua Agent

Menyimpan, mengelola, dan menyediakan akses ke semua agent
yang terdaftar dalam framework. Mendukung dinamis registrasi,
enable/disable, dan pencarian agent.
"""

import importlib
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Type

logger = logging.getLogger("framework.agents.registry")


class AgentRegistry:
    """
    Pusat registrasi untuk semua agent dalam framework.

    Fitur:
    - Register/unregister agent instances
    - Enable / disable agent
    - Query berdasarkan nama, tipe, atau kapabilitas
    - Auto-discover agent dari folder (opsional)
    """

    def __init__(self):
        self._agents: Dict[str, Any] = {}  # name → BaseAgent instance
        self._tags: Dict[str, List[str]] = {}  # name → [tag, ...]

    # ==================== REGISTER ====================

    def register(
        self,
        agent: Any,
        tags: Optional[List[str]] = None,
        overwrite: bool = False,
    ) -> bool:
        """
        Daftarkan agent ke registry.

        Args:
            agent: Instance agent (harus punya .name attribute).
            tags: Label opsional (contoh: ["file", "tools"]).
            overwrite: Jika True, timpa agent dengan nama sama.

        Returns:
            True jika berhasil didaftarkan.
        """
        if not hasattr(agent, "name"):
            logger.error(f"Agent tidak punya attribute 'name': {agent!r}")
            return False

        name = agent.name

        if name in self._agents and not overwrite:
            logger.warning(f"Agent '{name}' sudah terdaftar. Gunakan overwrite=True untuk menimpa.")
            return False

        self._agents[name] = agent
        self._tags[name] = tags or []
        logger.info(f"Agent registered: '{name}' (tags={self._tags[name]})")
        return True

    def unregister(self, name: str) -> bool:
        """
        Hapus agent dari registry.

        Args:
            name: Nama agent yang akan dihapus.

        Returns:
            True jika berhasil dihapus.
        """
        if name not in self._agents:
            logger.warning(f"Agent '{name}' tidak ditemukan untuk dihapus.")
            return False

        agent = self._agents.pop(name)
        self._tags.pop(name, None)

        # Lifecycle: panggil on_shutdown jika ada
        if hasattr(agent, "on_shutdown"):
            try:
                agent.on_shutdown()
            except Exception as e:
                logger.warning(f"on_shutdown() error for '{name}': {e}")

        logger.info(f"Agent unregistered: '{name}'")
        return True

    # ==================== QUERY ====================

    def get(self, name: str) -> Optional[Any]:
        """Ambil agent berdasarkan nama."""
        return self._agents.get(name)

    def get_all(self) -> List[Any]:
        """Ambil semua agent (enabled maupun tidak)."""
        return list(self._agents.values())

    def get_enabled(self) -> List[Any]:
        """Ambil hanya agent yang sedang enabled."""
        return [a for a in self._agents.values() if getattr(a, "enabled", True)]

    def get_disabled(self) -> List[Any]:
        """Ambil hanya agent yang sedang disabled."""
        return [a for a in self._agents.values() if not getattr(a, "enabled", True)]

    def get_by_tag(self, tag: str) -> List[Any]:
        """Ambil semua agent dengan tag tertentu."""
        return [
            self._agents[name]
            for name, tags in self._tags.items()
            if tag in tags
        ]

    def has(self, name: str) -> bool:
        """Cek apakah agent sudah terdaftar."""
        return name in self._agents

    # ==================== ENABLE / DISABLE ====================

    def enable(self, name: str) -> bool:
        """Enable agent berdasarkan nama."""
        agent = self.get(name)
        if agent is None:
            return False
        if hasattr(agent, "enable"):
            agent.enable()
        else:
            agent.enabled = True
        logger.info(f"Agent enabled: '{name}'")
        return True

    def disable(self, name: str) -> bool:
        """Disable agent berdasarkan nama."""
        agent = self.get(name)
        if agent is None:
            return False
        if hasattr(agent, "disable"):
            agent.disable()
        else:
            agent.enabled = False
        logger.info(f"Agent disabled: '{name}'")
        return True

    # ==================== FACTORY ====================

    @staticmethod
    def create_from_class(
        agent_class: Type,
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        """
        Buat instance agent dari class-nya.

        Args:
            agent_class: Class agent yang akan di-instantiate.
            *args, **kwargs: Argumen konstruktor.

        Returns:
            Instance agent baru.
        """
        try:
            instance = agent_class(*args, **kwargs)
            logger.debug(f"Agent created from class: {agent_class.__name__}")
            return instance
        except Exception as e:
            logger.error(f"Failed to create agent from {agent_class.__name__}: {e}")
            raise

    @staticmethod
    def create_from_module(
        module_path: str,
        class_name: str,
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        """
        Buat instance agent dari module path.

        Args:
            module_path: Contoh 'framework.agents.react_agent'
            class_name: Nama class dalam module tersebut.
            *args, **kwargs: Argumen konstruktor.

        Returns:
            Instance agent baru.
        """
        try:
            module = importlib.import_module(module_path)
            cls = getattr(module, class_name)
            return cls(*args, **kwargs)
        except (ImportError, AttributeError) as e:
            logger.error(f"Failed to load agent from {module_path}.{class_name}: {e}")
            raise

    # ==================== AUTO-DISCOVER ====================

    def discover_from_folder(
        self,
        folder: Path,
        base_class: Optional[Any] = None,
        class_name: str = "Agent",
    ) -> int:
        """
        Auto-scan folder dan register semua agent yang ditemukan.

        Setiap file Python di folder diasumsikan punya class 'Agent'
        (atau sesuai class_name) yang mewarisi base_class.

        Args:
            folder: Path folder yang akan di-scan.
            base_class: Base class untuk validasi (opsional).
            class_name: Nama class yang dicari di tiap file.

        Returns:
            Jumlah agent berhasil di-register.
        """
        count = 0
        for py_file in sorted(folder.glob("*.py")):
            if py_file.stem.startswith("_"):
                continue
            try:
                module_name = f"{folder.name}.{py_file.stem}"
                module = importlib.import_module(module_name)
                if hasattr(module, class_name):
                    cls = getattr(module, class_name)
                    if base_class and not issubclass(cls, base_class):
                        continue
                    instance = cls()
                    if self.register(instance):
                        count += 1
            except Exception as e:
                logger.warning(f"Auto-discover: gagal load {py_file.name}: {e}")

        logger.info(f"Auto-discovered {count} agents from {folder}")
        return count

    # ==================== INFO ====================

    def list_agents(self) -> List[Dict]:
        """Daftar info semua agent."""
        result = []
        for name, agent in self._agents.items():
            info = {
                "name": name,
                "description": getattr(agent, "description", ""),
                "enabled": getattr(agent, "enabled", True),
                "tags": self._tags.get(name, []),
            }
            # Tambah info tambahan jika tersedia
            if hasattr(agent, "get_info"):
                extra = agent.get_info()
                info.update(extra)
            result.append(info)
        return result

    def get_stats(self) -> Dict:
        """Statistik registry."""
        total = len(self._agents)
        enabled = len(self.get_enabled())
        return {
            "total": total,
            "enabled": enabled,
            "disabled": total - enabled,
            "agents": [a["name"] for a in self.list_agents()],
        }

    def __len__(self) -> int:
        return len(self._agents)

    def __repr__(self) -> str:
        return f"<AgentRegistry total={len(self._agents)} enabled={len(self.get_enabled())}>"
