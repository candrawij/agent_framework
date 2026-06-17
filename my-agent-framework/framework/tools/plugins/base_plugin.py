"""
base_plugin.py — Base Class Plugin

Refactored dari saki_ai_assistant/plugins/base.py dengan
pemisahan dari logika Saki-specific dan generalisasi interface.
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Dict, List, Optional


class PluginStatus(Enum):
    DISABLED = "disabled"
    ENABLED = "enabled"
    ERROR = "error"
    LOADING = "loading"


class BasePlugin(ABC):
    """
    Base class untuk semua plugin framework.

    Plugin berbeda dari Tool:
    - Plugin adalah bundel fitur lengkap (bisa berisi beberapa tool/command)
    - Plugin punya lifecycle (enable/disable)
    - Plugin bisa punya konfigurasi sendiri

    Subclass wajib implement:
    - name, description, version (properties)
    - on_enable() → bool
    - on_disable()
    - get_commands() → List[Dict]
    - execute(command, args) → str
    """

    def __init__(self):
        self.status = PluginStatus.DISABLED
        self._config: Dict[str, Any] = {}

    @property
    @abstractmethod
    def name(self) -> str:
        """Nama unik plugin (snake_case)."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Deskripsi plugin."""
        pass

    @property
    @abstractmethod
    def version(self) -> str:
        """Versi plugin (semver: '1.0.0')."""
        pass

    @property
    def icon(self) -> str:
        """Emoji ikon opsional."""
        return "🔌"

    @property
    def author(self) -> str:
        """Nama pembuat plugin."""
        return "Unknown"

    @abstractmethod
    def on_enable(self) -> bool:
        """
        Dipanggil saat plugin di-enable.
        Lakukan setup (buka koneksi, load model, dll).

        Returns:
            True jika berhasil.
        """
        pass

    @abstractmethod
    def on_disable(self):
        """
        Dipanggil saat plugin di-disable.
        Lakukan cleanup (tutup koneksi, bebaskan resource).
        """
        pass

    @abstractmethod
    def get_commands(self) -> List[Dict]:
        """
        Kembalikan daftar commands yang tersedia.

        Format setiap command:
        {
            "name": "command_name",
            "description": "Deskripsi singkat",
            "keywords": ["kata kunci", "untuk routing"],
            "handler": "method_name",  # opsional
        }
        """
        pass

    @abstractmethod
    def execute(self, command: str, args: Optional[Dict] = None) -> str:
        """
        Eksekusi sebuah command.

        Args:
            command: Nama command.
            args: Argumen tambahan.

        Returns:
            Hasil eksekusi sebagai string.
        """
        pass

    # ==================== LIFECYCLE ====================

    def enable(self) -> bool:
        """Enable plugin."""
        self.status = PluginStatus.LOADING
        try:
            if self.on_enable():
                self.status = PluginStatus.ENABLED
                return True
            else:
                self.status = PluginStatus.ERROR
                return False
        except Exception as e:
            self.status = PluginStatus.ERROR
            print(f"Plugin '{self.name}' enable error: {e}")
            return False

    def disable(self):
        """Disable plugin."""
        try:
            self.on_disable()
        except Exception:
            pass
        self.status = PluginStatus.DISABLED

    # ==================== CONFIG ====================

    def get_config(self) -> Dict:
        return self._config.copy()

    def set_config(self, config: Dict):
        self._config.update(config)

    def get_config_value(self, key: str, default: Any = None) -> Any:
        return self._config.get(key, default)

    # ==================== INFO ====================

    def get_info(self) -> Dict:
        return {
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "icon": self.icon,
            "author": self.author,
            "status": self.status.value,
            "commands": len(self.get_commands()),
        }

    def __repr__(self) -> str:
        return f"Plugin({self.name} v{self.version} [{self.status.value}])"
