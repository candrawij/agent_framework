# Plugin Development Guide

## Struktur Plugin

```
plugins/
└── my_plugin/
    ├── __init__.py
    ├── plugin.py    ← WAJIB, berisi class Plugin(BasePlugin)
    └── README.md    ← Opsional
```

## Implementasi Plugin

```python
# plugins/my_plugin/plugin.py
from framework.tools.plugins.base_plugin import BasePlugin, PluginStatus

class Plugin(BasePlugin):
    @property
    def name(self): return "my_plugin"
    
    @property
    def description(self): return "Deskripsi plugin saya"
    
    @property
    def version(self): return "1.0.0"
    
    def on_enable(self) -> bool:
        # Setup resources
        return True
    
    def on_disable(self):
        # Cleanup resources
        pass
    
    def get_commands(self):
        return [{
            "name": "my_command",
            "description": "Jalankan perintah saya",
            "keywords": ["perintahku", "my command"],
        }]
    
    def execute(self, command: str, args=None) -> str:
        if command == "my_command":
            return "Perintah berhasil dijalankan!"
        return f"Command tidak dikenal: {command}"
```

## Load Plugin

```python
from framework.tools.plugins.loader import load_all_plugins
from pathlib import Path

registry = load_all_plugins(folder=Path("plugins/"), auto_enable=True)
print(registry.get_stats())
```

## Plugin vs Tool

| Fitur | Plugin | Tool |
|-------|--------|------|
| Lifecycle (enable/disable) | ✅ | ❌ |
| Bisa berisi banyak command | ✅ | ❌ (1 tool = 1 aksi) |
| Diakses via LLM tool calling | ❌ | ✅ |
| Diakses via keyword routing | ✅ | ❌ |
| Config storage | ✅ | ❌ |
