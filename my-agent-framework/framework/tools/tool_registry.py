"""
tool_registry.py — Registry & Auto-Discovery Tools

ToolRegistry adalah pusat registrasi semua tool dalam framework.
Mendukung:
- Manual registration
- Auto-discovery dari folder (scan modul)
- Enable/disable tool tanpa restart
- Schema generation untuk LLM tool calling
"""

import importlib
import importlib.util
import inspect
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from .base_tool import BaseTool

logger = logging.getLogger("framework.tools.registry")


class ToolRegistry:
    """
    Registry terpusat untuk semua tool yang tersedia dalam framework.

    Usage:
        registry = ToolRegistry()
        registry.register(CalculatorTool())
        registry.register(DatetimeTool())

        # Jalankan tool
        result = registry.execute("calculator", {"expression": "15 * 27"})

        # Daftar tool untuk LLM
        schemas = registry.get_schemas()
    """

    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}
        self._disabled: set = set()
        self._execution_log: List[Dict] = []

    # ==================== REGISTRATION ====================

    def register(self, tool: BaseTool, override: bool = False) -> "ToolRegistry":
        """Daftarkan satu tool ke registry."""
        if tool.name in self._tools and not override:
            logger.warning(f"Tool '{tool.name}' sudah terdaftar. Gunakan override=True untuk menimpa.")
            return self
        self._tools[tool.name] = tool
        logger.info(f"Tool registered: '{tool.name}' — {tool.description[:60]}")
        return self

    def register_all(self, tools: List[BaseTool]) -> "ToolRegistry":
        """Daftarkan banyak tool sekaligus."""
        for tool in tools:
            self.register(tool)
        return self

    def unregister(self, name: str) -> bool:
        """Hapus tool dari registry."""
        if name in self._tools:
            del self._tools[name]
            self._disabled.discard(name)
            logger.info(f"Tool unregistered: '{name}'")
            return True
        return False

    def enable(self, name: str) -> bool:
        """Aktifkan tool yang sebelumnya dinonaktifkan."""
        if name in self._tools:
            self._disabled.discard(name)
            logger.info(f"Tool enabled: '{name}'")
            return True
        return False

    def disable(self, name: str) -> bool:
        """Nonaktifkan tool tanpa menghapusnya."""
        if name in self._tools:
            self._disabled.add(name)
            logger.info(f"Tool disabled: '{name}'")
            return True
        return False

    # ==================== LOOKUP ====================

    def get(self, name: str) -> Optional[BaseTool]:
        """Ambil tool berdasarkan nama. None jika tidak ada / disabled."""
        tool = self._tools.get(name)
        if tool and name not in self._disabled:
            return tool
        return None

    def get_all(self, include_disabled: bool = False) -> List[BaseTool]:
        """Ambil semua tool."""
        tools = list(self._tools.values())
        if not include_disabled:
            tools = [t for t in tools if t.name not in self._disabled]
        return tools

    def get_by_tag(self, tag: str) -> List[BaseTool]:
        """Ambil tool berdasarkan tag."""
        return [t for t in self.get_all() if tag in t.tags]

    def list_names(self, include_disabled: bool = False) -> List[str]:
        """Daftar nama tool."""
        return [t.name for t in self.get_all(include_disabled)]

    # ==================== SCHEMA ====================

    def get_schemas(self) -> List[Dict]:
        """
        Kembalikan schemas semua tool aktif dalam format OpenAI function calling.
        Digunakan untuk inject ke model prompt.
        """
        return [t.get_schema() for t in self.get_all()]

    def get_info_list(self) -> List[Dict]:
        """Info ringkas semua tool untuk API endpoint."""
        result = []
        for t in self._tools.values():
            info = t.get_info()
            info["enabled"] = t.name not in self._disabled
            result.append(info)
        return result

    # ==================== EXECUTION ====================

    def execute(self, tool_name: str, tool_input: Dict) -> Dict:
        """
        Eksekusi tool berdasarkan nama.

        Returns:
            {"success": bool, "output": str, "error": Optional[str], "tool_name": str}
        """
        import time

        tool = self.get(tool_name)
        if tool is None:
            if tool_name in self._disabled:
                return {
                    "success": False,
                    "output": None,
                    "error": f"Tool '{tool_name}' dinonaktifkan",
                    "tool_name": tool_name,
                }
            available = self.list_names()
            return {
                "success": False,
                "output": None,
                "error": f"Tool '{tool_name}' tidak ditemukan. Tersedia: {available}",
                "tool_name": tool_name,
            }

        start = time.time()
        result = tool.safe_run(**tool_input)
        duration_ms = (time.time() - start) * 1000

        # Log eksekusi
        log_entry = {
            "tool_name": tool_name,
            "success": result["success"],
            "duration_ms": round(duration_ms, 1),
            "input_keys": list(tool_input.keys()),
            "output_preview": str(result.get("output", ""))[:200],
            "error": result.get("error"),
        }
        self._execution_log.append(log_entry)
        if len(self._execution_log) > 1000:
            self._execution_log.pop(0)

        logger.info(
            f"Tool '{tool_name}': {'✓' if result['success'] else '✗'} "
            f"in {duration_ms:.0f}ms"
        )

        return {
            "success": result["success"],
            "output": result.get("output"),
            "error": result.get("error"),
            "tool_name": tool_name,
            "duration_ms": round(duration_ms, 1),
        }

    # ==================== AUTO-DISCOVERY ====================

    def auto_discover(self, tools_dir: Optional[str] = None) -> int:
        """
        Auto-discover dan register semua tool dari folder tools/.

        Mencari semua kelas yang mewarisi BaseTool di modul Python.
        Returns jumlah tool yang berhasil didaftarkan.
        """
        if tools_dir is None:
            tools_dir = str(Path(__file__).parent)

        discovered = 0
        tools_path = Path(tools_dir)

        for py_file in tools_path.glob("*.py"):
            if py_file.name.startswith("_") or py_file.name == "base_tool.py":
                continue
            if py_file.stem in ("tool_registry",):
                continue

            try:
                module_name = f"framework.tools.{py_file.stem}"
                if module_name in sys.modules:
                    module = sys.modules[module_name]
                else:
                    spec = importlib.util.spec_from_file_location(module_name, py_file)
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)

                for _, cls in inspect.getmembers(module, inspect.isclass):
                    if (
                        issubclass(cls, BaseTool)
                        and cls is not BaseTool
                        and not inspect.isabstract(cls)
                    ):
                        try:
                            instance = cls()
                            if instance.name not in self._tools:
                                self.register(instance)
                                discovered += 1
                        except Exception as e:
                            logger.warning(f"Cannot instantiate {cls.__name__}: {e}")

            except Exception as e:
                logger.warning(f"Cannot load tool module {py_file.name}: {e}")

        logger.info(f"Auto-discovery: {discovered} new tools registered")
        return discovered

    # ==================== STATS ====================

    def get_stats(self) -> Dict:
        """Statistik registry."""
        return {
            "total": len(self._tools),
            "enabled": len(self._tools) - len(self._disabled),
            "disabled": len(self._disabled),
            "tools": self.list_names(),
            "disabled_tools": list(self._disabled),
        }

    def get_execution_log(self, last_n: int = 20) -> List[Dict]:
        """Log eksekusi N terakhir."""
        return self._execution_log[-last_n:]

    def __len__(self) -> int:
        return len(self._tools)

    def __contains__(self, name: str) -> bool:
        return name in self._tools

    def __repr__(self) -> str:
        return f"<ToolRegistry tools={self.list_names()}>"


# ==================== DEFAULT REGISTRY ====================

def create_default_registry() -> ToolRegistry:
    """
    Buat ToolRegistry dengan semua tool bawaan framework yang sudah diregister.
    Digunakan oleh server.py saat startup.
    """
    registry = ToolRegistry()

    # Import dan register semua tool bawaan
    try:
        from .datetime_tool import DatetimeTool
        registry.register(DatetimeTool())
    except Exception as e:
        logger.warning(f"DatetimeTool tidak bisa diload: {e}")

    try:
        from .calculator_tool import CalculatorTool
        registry.register(CalculatorTool())
    except Exception as e:
        logger.warning(f"CalculatorTool tidak bisa diload: {e}")

    try:
        from .file_io import ReadFileTool, WriteFileTool, ListFolderTool, SearchFilesTool
        registry.register_all([ReadFileTool(), WriteFileTool(), ListFolderTool(), SearchFilesTool()])
    except Exception as e:
        logger.warning(f"FileTool tidak bisa diload: {e}")

    try:
        from .http_request import HttpRequestTool
        registry.register(HttpRequestTool())
    except Exception as e:
        logger.warning(f"HttpRequestTool tidak bisa diload: {e}")

    logger.info(f"Default registry created: {registry.list_names()}")
    return registry
