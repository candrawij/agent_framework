"""
loader.py — Plugin Loader & Global Registry

Refactored dari saki_ai_assistant/plugins/loader.py dengan
penghapusan coupling ke Saki dan generalisasi path discovery.
"""

import importlib
import logging
from pathlib import Path
from typing import Dict, List, Optional

from .base_plugin import BasePlugin, PluginStatus

logger = logging.getLogger("framework.plugins.loader")


class PluginRegistry:
    """Registry untuk semua plugin yang terdaftar."""

    def __init__(self):
        self._plugins: Dict[str, BasePlugin] = {}

    def register(self, plugin: BasePlugin, overwrite: bool = False) -> bool:
        if plugin.name in self._plugins and not overwrite:
            logger.warning(f"Plugin '{plugin.name}' already registered")
            return False
        self._plugins[plugin.name] = plugin
        logger.info(f"Plugin registered: '{plugin.name}' v{plugin.version}")
        return True

    def unregister(self, name: str) -> bool:
        if name not in self._plugins:
            return False
        plugin = self._plugins.pop(name)
        if plugin.status == PluginStatus.ENABLED:
            plugin.disable()
        logger.info(f"Plugin unregistered: '{name}'")
        return True

    def get(self, name: str) -> Optional[BasePlugin]:
        return self._plugins.get(name)

    def get_all(self) -> List[BasePlugin]:
        return list(self._plugins.values())

    def get_enabled(self) -> List[BasePlugin]:
        return [p for p in self._plugins.values() if p.status == PluginStatus.ENABLED]

    def get_disabled(self) -> List[BasePlugin]:
        return [p for p in self._plugins.values() if p.status != PluginStatus.ENABLED]

    def enable(self, name: str) -> bool:
        plugin = self.get(name)
        return plugin.enable() if plugin else False

    def disable(self, name: str) -> bool:
        plugin = self.get(name)
        if plugin:
            plugin.disable()
            return True
        return False

    def enable_all(self) -> int:
        """Enable semua plugin. Returns jumlah berhasil."""
        return sum(1 for p in self._plugins.values() if p.enable())

    def get_all_commands(self) -> Dict[str, List[Dict]]:
        """Semua commands dari plugin yang enabled."""
        return {p.name: p.get_commands() for p in self.get_enabled() if p.get_commands()}

    def find_handler(self, user_message: str) -> Optional[tuple]:
        """
        Cari plugin yang bisa handle pesan.
        Returns: (plugin, command_dict) atau None
        """
        msg = user_message.lower()
        for plugin in self.get_enabled():
            for cmd in plugin.get_commands():
                if any(kw in msg for kw in cmd.get("keywords", [])):
                    return plugin, cmd
        return None

    def execute_message(self, user_message: str) -> Optional[str]:
        """Cari dan eksekusi handler untuk pesan user."""
        result = self.find_handler(user_message)
        if result:
            plugin, cmd = result
            return plugin.execute(cmd["name"], {"message": user_message})
        return None

    def get_stats(self) -> Dict:
        total = len(self._plugins)
        enabled = len(self.get_enabled())
        return {
            "total": total,
            "enabled": enabled,
            "disabled": total - enabled,
            "plugins": [p.get_info() for p in self._plugins.values()],
        }

    def __len__(self) -> int:
        return len(self._plugins)

    def __repr__(self) -> str:
        return f"<PluginRegistry total={len(self._plugins)} enabled={len(self.get_enabled())}>"


# ==================== LOADER ====================

class PluginLoader:
    """
    Auto-loader plugin dari folder.

    Konvensi folder plugin:
    plugins/
        my_plugin/
            __init__.py
            plugin.py    ← harus ada class 'Plugin' atau nama class opsional
    """

    def __init__(self, registry: Optional[PluginRegistry] = None):
        self.registry = registry or PluginRegistry()

    def load_from_path(
        self,
        plugin_path: Path,
        class_name: str = "Plugin",
        auto_enable: bool = True,
    ) -> Optional[BasePlugin]:
        """
        Load satu plugin dari folder.

        Args:
            plugin_path: Path ke folder plugin.
            class_name: Nama class plugin di dalam plugin.py.
            auto_enable: Enable plugin setelah load.

        Returns:
            Plugin instance atau None jika gagal.
        """
        if not plugin_path.is_dir():
            return None

        plugin_file = plugin_path / "plugin.py"
        if not plugin_file.exists():
            logger.debug(f"No plugin.py in {plugin_path.name}, skipping")
            return None

        try:
            # Dynamic import
            module_name = f"{plugin_path.parent.name}.{plugin_path.name}.plugin"
            try:
                module = importlib.import_module(module_name)
            except ModuleNotFoundError:
                import importlib.util
                spec = importlib.util.spec_from_file_location(module_name, plugin_file)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)

            if not hasattr(module, class_name):
                logger.warning(f"No '{class_name}' class in {plugin_path.name}/plugin.py")
                return None

            cls = getattr(module, class_name)
            instance = cls()

            if not isinstance(instance, BasePlugin):
                logger.warning(f"{plugin_path.name}: Plugin class doesn't inherit BasePlugin")
                return None

            self.registry.register(instance)

            if auto_enable:
                if not instance.enable():
                    logger.warning(f"Plugin '{instance.name}' failed to enable")

            return instance

        except Exception as e:
            logger.error(f"Failed to load plugin from '{plugin_path.name}': {e}", exc_info=True)
            return None

    def load_all_from_folder(
        self,
        folder: Path,
        class_name: str = "Plugin",
        auto_enable: bool = True,
        skip_prefixes: Optional[List[str]] = None,
    ) -> int:
        """
        Load semua plugin dari folder.

        Args:
            folder: Root folder berisi subfolder-subfolder plugin.
            class_name: Nama class plugin.
            auto_enable: Enable semua setelah load.
            skip_prefixes: Prefix nama folder yang di-skip.

        Returns:
            Jumlah plugin berhasil di-load.
        """
        skip_prefixes = skip_prefixes or ["_", "__", "."]
        count = 0

        if not folder.is_dir():
            logger.warning(f"Plugin folder tidak ditemukan: {folder}")
            return 0

        for item in sorted(folder.iterdir()):
            if not item.is_dir():
                continue
            if any(item.name.startswith(p) for p in skip_prefixes):
                continue

            result = self.load_from_path(item, class_name, auto_enable)
            if result:
                count += 1

        logger.info(
            f"Loaded {count} plugins from '{folder}' "
            f"(enabled: {len(self.registry.get_enabled())})"
        )
        return count


# ==================== GLOBAL SINGLETON ====================

_global_registry: Optional[PluginRegistry] = None
_global_loader: Optional[PluginLoader] = None


def get_plugin_manager() -> PluginRegistry:
    """Get global plugin registry singleton."""
    global _global_registry
    if _global_registry is None:
        _global_registry = PluginRegistry()
    return _global_registry


def load_all_plugins(
    folder: Optional[Path] = None,
    auto_enable: bool = True,
) -> PluginRegistry:
    """
    Load semua plugin dari folder (singleton-safe).

    Args:
        folder: Folder plugin (default: plugins/ di root project).
        auto_enable: Enable semua plugin setelah load.

    Returns:
        Global plugin registry.
    """
    global _global_registry, _global_loader
    registry = get_plugin_manager()

    if folder is None:
        # Default: cari folder 'plugins' di project root
        folder = Path(__file__).parent.parent.parent.parent / "plugins"

    if not _global_loader:
        _global_loader = PluginLoader(registry)

    _global_loader.load_all_from_folder(folder, auto_enable=auto_enable)
    return registry
