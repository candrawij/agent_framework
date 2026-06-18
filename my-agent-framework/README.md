# My Agent Framework

**Custom Multi-Agent Framework** — arsitektur modular untuk membangun agen AI yang bisa berjalan lokal maupun terdistribusi.

---

## 🏗️ Struktur Project

```
my-agent-framework/
├── framework/
│   ├── agents/          # BaseAgent, ReActAgent, SupervisorAgent, Registry
│   ├── loop/            # AgentLoop (Plan → Execute → Observe → Reflect)
│   ├── tools/           # Tools (FileIO, Shell, WebSearch) + Plugin System
│   ├── memory/          # Short-term, Long-term (Vector), Episodic
│   ├── security/        # JWT, Input Sanitizer, Audit Log, Secrets
│   └── api/             # FastAPI REST + WebSocket server
│
├── model_layer/
│   ├── adapters/        # Ollama, OpenAI-compat, llama.cpp, vLLM, Custom
│   ├── profiles/        # Model profiles YAML
│   └── model_manager.py # Koordinator semua adapters
│
├── gateway_mobile/      # Flutter app (iOS & Android)
├── gateway_desktop/     # Electron + React (Windows, Mac, Linux)
│
├── plugins/             # Plugin-plugin custom (auto-loaded)
├── config/              # Konfigurasi (models.yaml, agents.yaml, server.yaml)
├── shared/              # TypeScript & Python types yang dibagi
├── scripts/             # Helper scripts
├── tests/               # Unit & integration tests
└── docs/                # Dokumentasi
```

---

## 🚀 Quick Start

### 1. Install

```bash
cd my-agent-framework
pip install -e ".[dev]"
```

### 2. Setup Ollama

```bash
ollama pull qwen2.5:3b    # Fast model
ollama pull qwen3:4b      # Reasoning model
```

### 3. Konfigurasi

```bash
cp config/.env.example config/.env
python scripts/gen_jwt_secret.py  # Generate JWT secret
```

### 4. Jalankan Server

```bash
# Windows
scripts\start_framework.bat

# Linux/Mac
bash scripts/start_framework.sh

# Atau manual
uvicorn framework.api.server:app --reload --port 8000
```

API tersedia di: **http://localhost:8000**  
Swagger UI: **http://localhost:8000/api/docs**

---

## 💡 Penggunaan Dasar

### Python API

```python
from model_layer import ModelManager
from framework.agents import AgentRegistry
from framework.loop import AgentLoop

# Setup model
model = ModelManager.with_ollama(
    fast_model="qwen2.5:3b",
    reasoning_model="qwen3:4b",
)

# Setup loop
loop = AgentLoop(max_iterations=10)

# Jalankan goal
result = loop.run(
    goal="Cari informasi tentang Python asyncio dan buat ringkasannya",
    context={"user": "developer"},
)

print(result.final_answer)
print(f"Status: {result.outcome}, Iterasi: {result.iterations}")
```

### REST API

```bash
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"messages": [{"role": "user", "content": "Halo!"}]}'
```

### Buat Plugin Baru

```python
# plugins/my_plugin/plugin.py
from framework.tools.plugins.base_plugin import BasePlugin

class Plugin(BasePlugin):
    @property
    def name(self): return "my_plugin"
    
    @property
    def description(self): return "Plugin saya"
    
    @property
    def version(self): return "1.0.0"
    
    def on_enable(self): return True
    def on_disable(self): pass
    
    def get_commands(self):
        return [{"name": "hello", "keywords": ["halo"], "description": "Sapa user"}]
    
    def execute(self, command, args=None):
        return "Halo dari plugin saya!"
```

### Buat Custom Tool

```python
from framework.tools.base_tool import BaseTool

class MyCustomTool(BaseTool):
    name = "my_tool"
    description = "Tool kustom saya"
    
    @property
    def parameters(self):
        return {
            "type": "object",
            "properties": {
                "input": {"type": "string", "description": "Input teks"}
            },
            "required": ["input"]
        }
    
    def run(self, input: str) -> str:
        return f"Processed: {input}"
```

---

## 🧪 Testing

```bash
# Semua tests
make test

# Tests cepat
make test-fast

# Coverage report
pytest tests/ --cov=framework --cov=model_layer --cov-report=html
```

---

## 📱 Gateway

### Mobile (Flutter)
```bash
cd gateway_mobile
flutter pub get
flutter run
```

### Desktop (Electron + React)
```bash
cd gateway_desktop
npm install
npm run dev      # Development
npm run build    # Production build
npm run electron # Jalankan desktop app
```

---

## 🛠️ Development

```bash
make format   # Format kode
make lint     # Lint & type check
make clean    # Bersihkan build artifacts
```

---

## 📚 Dokumentasi

- [Architecture Overview](docs/architecture.md)
- [API Reference](docs/api_reference.md)
- [Plugin Development Guide](docs/plugin_guide.md)
- [Model Setup Guide](docs/model_setup.md)

---

## 🔄 Migrasi dari Saki AI Assistant

| Saki | Framework |
|------|-----------|
| `src/agents/base.py` | `framework/agents/base_agent.py` |
| `src/agents/router.py` | `framework/agents/supervisor_agent.py` |
| `plugins/registry.py` | `framework/tools/plugins/loader.py` |
| `src/model_router.py` | `model_layer/adapters/ollama_adapter.py` |
| `src/audit_pipeline.py` | `framework/security/audit_log.py` |
| `src/agents/skills/filesystem.py` | `framework/tools/file_io.py` |
| `src/agents/skills/windows.py` | `framework/tools/shell_command.py` |
