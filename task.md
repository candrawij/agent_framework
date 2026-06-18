# Task: Build my-agent-framework Project Structure

## Phase 1: Create Directory Structure
- [x] Create base folder `my-agent-framework/`
- [x] Create all subdirectories

## Phase 2: Framework Core (Python)
- [x] `framework/agents/base_agent.py` — refactor dari src/agents/base.py
- [x] `framework/agents/react_agent.py` — ReAct loop
- [x] `framework/agents/supervisor_agent.py` — refactor dari src/agents/router.py
- [x] `framework/agents/agent_registry.py` — refactor dari plugins/registry.py
- [x] `framework/loop/planner.py`
- [x] `framework/loop/executor.py`
- [x] `framework/loop/observer.py`
- [x] `framework/loop/reflector.py`
- [x] `framework/loop/agent_loop.py`
- [x] `framework/tools/base_tool.py`
- [x] `framework/tools/web_search.py`
- [x] `framework/tools/http_request.py` (+ CodeExecutorTool)
- [x] `framework/tools/file_io.py` — refactor dari agents/skills/filesystem.py
- [x] `framework/tools/shell_command.py` — refactor dari agents/skills/windows.py
- [x] `framework/tools/plugins/__init__.py`
- [x] `framework/tools/plugins/base_plugin.py`
- [x] `framework/tools/plugins/loader.py` — refactor dari plugins/loader.py
- [x] `framework/tools/plugins/example_plugin.py`
- [x] `framework/memory/short_term.py`
- [x] `framework/memory/long_term.py`
- [x] `framework/memory/episodic.py`
- [x] `framework/memory/compressor.py`
- [x] `framework/memory/memory_manager.py`
- [x] `framework/api/server.py` — FastAPI
- [x] `framework/api/routes/chat.py`
- [x] `framework/api/routes/agents.py`
- [x] `framework/api/routes/sessions.py`
- [x] `framework/api/routes/models.py`
- [x] `framework/api/routes/upload.py`
- [x] `framework/api/websocket.py`
- [x] `framework/api/auth.py`
- [x] `framework/api/middleware.py`
- [x] `framework/security/jwt_handler.py`
- [x] `framework/security/input_sanitizer.py`
- [x] `framework/security/audit_log.py` — refactor dari src/audit_pipeline.py
- [x] `framework/security/secrets.py`

## Phase 3: Model Layer
- [x] `model_layer/adapters/base_adapter.py`
- [x] `model_layer/adapters/ollama_adapter.py` — refactor dari src/model_router.py
- [x] `model_layer/adapters/openai_compat_adapter.py`
- [x] `model_layer/adapters/llamacpp_adapter.py`
- [x] `model_layer/adapters/vllm_adapter.py`
- [x] `model_layer/adapters/custom_adapter.py`
- [x] `model_layer/profiles/reasoning.yaml`
- [x] `model_layer/profiles/coding.yaml`
- [x] `model_layer/profiles/fast.yaml`
- [x] `model_layer/profiles/embedding.yaml`
- [x] `model_layer/model_manager.py`
- [x] `model_layer/tokenizer_utils.py`
- [x] `config/models.yaml`
- [x] `config/agents.yaml`
- [x] `config/server.yaml`
- [x] `config/.env.example`

## Phase 4: Gateway Mobile (Flutter)
- [x] `gateway_mobile/pubspec.yaml`
- [x] `gateway_mobile/lib/main.dart`
- [x] `gateway_mobile/lib/core/` (config.dart, api_client.dart)
- [x] `gateway_mobile/lib/models/chat_message.dart`
- [x] `gateway_mobile/lib/providers/` (chat_provider.dart, settings_provider.dart)
- [x] `gateway_mobile/lib/screens/` (chat_screen.dart, settings_screen.dart)
- [x] `gateway_mobile/README.md`

## Phase 5: Gateway Desktop (Electron+React)
- [x] `gateway_desktop/package.json`
- [x] `gateway_desktop/vite.config.ts`
- [x] `gateway_desktop/tsconfig.json`
- [x] `gateway_desktop/index.html`
- [x] `gateway_desktop/electron/` (main.js, preload.js)
- [x] `gateway_desktop/src/main.tsx`
- [x] `gateway_desktop/src/App.tsx`
- [x] `gateway_desktop/src/index.css` (dark theme UI)
- [x] `gateway_desktop/src/api/client.ts`
- [x] `gateway_desktop/src/stores/` (chatStore.ts, settingsStore.ts)
- [x] `gateway_desktop/src/components/` (ChatWindow, MessageBubble, InputBar, Sidebar, SettingsModal)
- [x] `gateway_desktop/README.md`

## Phase 6: Shared, Scripts, Tests, Docs
- [x] `shared/` files (api_schema.ts, api_schema.py, ws_events.ts)
- [x] `scripts/` files (start, benchmark, gen_jwt_secret, setup_qdrant)
- [x] `tests/framework/` (test_agent_loop.py, test_tool_calling.py, test_memory.py)
- [x] `tests/model_layer/test_adapters.py`
- [x] `docs/` (architecture.md, api_reference.md, plugin_guide.md, model_setup.md)
- [x] Root files (README.md, docker-compose.yml, Makefile, pyproject.toml, Dockerfile, .gitignore, CHANGELOG.md)
- [x] `plugins/README.md`
- [x] `data/` dan `logs/` placeholder

## ✅ SEMUA TASK SELESAI
