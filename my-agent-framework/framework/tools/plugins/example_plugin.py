"""
example_plugin.py — Contoh Plugin

Template yang bisa dijadikan referensi untuk membuat plugin baru.
Salin file ini ke folder plugins/nama_plugin/plugin.py
dan rename class-nya.
"""

from typing import Dict, List, Optional

# Import dari parent package
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from framework.tools.plugins.base_plugin import BasePlugin, PluginStatus


class Plugin(BasePlugin):
    """
    Contoh plugin: Hello World

    Plugin ini menunjukkan cara mengimplementasikan
    BasePlugin untuk framework ini.
    """

    @property
    def name(self) -> str:
        return "hello_world"

    @property
    def description(self) -> str:
        return "Plugin demo yang menyapa user"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def icon(self) -> str:
        return "👋"

    @property
    def author(self) -> str:
        return "Framework Team"

    def on_enable(self) -> bool:
        """Setup plugin: inisialisasi resource yang dibutuhkan."""
        print(f"✅ {self.name} plugin enabled!")
        # Contoh: load config, buka koneksi, dll
        return True

    def on_disable(self):
        """Cleanup: bebaskan resource."""
        print(f"❌ {self.name} plugin disabled")

    def get_commands(self) -> List[Dict]:
        """
        Daftar command yang didukung plugin ini.
        Keywords digunakan untuk routing dari supervisor.
        """
        return [
            {
                "name": "greet",
                "description": "Menyapa user",
                "keywords": ["halo", "hello", "hi", "sapa", "greet"],
                "handler": "greet_user",
            },
            {
                "name": "farewell",
                "description": "Berpamitan ke user",
                "keywords": ["bye", "selamat tinggal", "dadah", "farewell"],
                "handler": "say_goodbye",
            },
        ]

    def execute(self, command: str, args: Optional[Dict] = None) -> str:
        """
        Eksekusi command berdasarkan nama.

        Args:
            command: Nama command dari get_commands().
            args: Dict argumen tambahan (bisa berisi 'message', dll).
        """
        args = args or {}

        if command == "greet":
            return self.greet_user(args)
        elif command == "farewell":
            return self.say_goodbye(args)
        else:
            return f"❓ Command '{command}' tidak dikenal oleh plugin {self.name}"

    # ==================== COMMAND HANDLERS ====================

    def greet_user(self, args: Dict) -> str:
        """Sapa user."""
        name = args.get("user_name", "")
        if name:
            return f"👋 Halo, {name}! Selamat datang di framework ini."
        return "👋 Halo! Ada yang bisa saya bantu?"

    def say_goodbye(self, args: Dict) -> str:
        """Berpamitan."""
        return "👋 Sampai jumpa! Semoga harimu menyenangkan! 😊"
