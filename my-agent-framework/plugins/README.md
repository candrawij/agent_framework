# Plugins

Letakkan plugin kamu di sini. Setiap plugin adalah folder dengan file `plugin.py` di dalamnya.

```
plugins/
└── my_plugin/
    ├── __init__.py     # Bisa kosong
    └── plugin.py       # Berisi class Plugin(BasePlugin)
```

Lihat `framework/tools/plugins/example_plugin.py` untuk template plugin.

Plugin akan otomatis di-load saat framework start jika `auto_load: true` di `config/agents.yaml`.
