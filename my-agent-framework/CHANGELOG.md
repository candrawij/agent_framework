# Changelog

## [1.0.0] - 2026-06-18

### Added
- Initial framework structure berdasarkan PRD Custom Agent Framework
- `framework/agents/`: BaseAgent, ReActAgent, SupervisorAgent, AgentRegistry
- `framework/loop/`: Planner, Executor, Observer, Reflector, AgentLoop
- `framework/tools/`: BaseTool, FileIO, ShellCommand, WebSearch, HttpRequest
- `framework/tools/plugins/`: BasePlugin, PluginLoader, PluginRegistry
- `framework/memory/`: ShortTermMemory, LongTermMemory, EpisodicMemory, MemoryManager
- `framework/security/`: AuditLog, InputSanitizer, JWTHandler, SecretsManager
- `framework/api/`: FastAPI server dengan REST dan WebSocket endpoints
- `model_layer/`: ModelManager dengan adapters (Ollama, OpenAI-compat, llama.cpp, vLLM)
- `gateway_mobile/`: Flutter boilerplate
- `gateway_desktop/`: Electron + React boilerplate
- `tests/`: Unit test untuk semua komponen utama
- `docs/`: Architecture, API Reference, Plugin Guide, Model Setup

### Migrated From
- `saki_ai_assistant/src/agents/base.py` → `framework/agents/base_agent.py`
- `saki_ai_assistant/src/agents/router.py` → `framework/agents/supervisor_agent.py`
- `saki_ai_assistant/plugins/registry.py` → `framework/tools/plugins/loader.py`
- `saki_ai_assistant/src/model_router.py` → `model_layer/adapters/ollama_adapter.py`
- `saki_ai_assistant/src/audit_pipeline.py` → `framework/security/audit_log.py`
- `saki_ai_assistant/src/agents/skills/filesystem.py` → `framework/tools/file_io.py`
- `saki_ai_assistant/src/agents/skills/windows.py` → `framework/tools/shell_command.py`
