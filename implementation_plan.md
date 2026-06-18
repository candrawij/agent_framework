# Rancangan Project: Custom Agent Framework

## Latar Belakang

Berdasarkan PRD dan `custom_agent_framework_folder_structure.html`, proyek baru bernama **`my-agent-framework/`** akan dibuat di `e:\ProjectLily\`. 

Folder `saki_ai_assistant` sudah berisi kode yang *sebagian* relevan dengan framework ini — terutama di bagian **model layer**, **agents**, **plugins**, **memory**, dan **API server**. File-file yang sesuai akan **dipindahkan/disalin** ke dalam `my-agent-framework/`, sedangkan yang tidak sesuai dibiarkan tetap di `saki_ai_assistant`.

---

## Analisis: Pemetaan `saki_ai_assistant` → `my-agent-framework/`

### ✅ File yang AKAN dipindahkan/disalin

| File Asal (`saki_ai_assistant/`) | Tujuan di `my-agent-framework/`) | Keterangan |
|---|---|---|
| `src/model_router.py` | `model_layer/adapters/ollama_adapter.py` + `model_layer/model_manager.py` | ModelRouter = logika routing + ollama backend |
| `src/ai.py` | `framework/agents/react_agent.py` (sebagian) | Logic chat+reflection = ReAct-like loop |
| `src/agents/base.py` | `framework/agents/base_agent.py` | Abstract base agent |
| `src/agents/router.py` | `framework/agents/supervisor_agent.py` | AgentRouter = supervisor/orchestrator |
| `src/agents/file_agent.py` | `framework/tools/file_io.py` | File agent → file tool |
| `src/agents/task_agent.py` | `framework/tools/` (bagian) | Task management tool |
| `src/agents/note_agent.py` | `framework/tools/` (bagian) | Note tool |
| `src/agents/skills/filesystem.py` | `framework/tools/file_io.py` | Filesystem skill → file tool |
| `src/agents/skills/windows.py` | `framework/tools/shell_command.py` | Windows shell skill |
| `src/permissions.py` | `framework/security/` | Permission system → security layer |
| `src/audit_pipeline.py` | `framework/security/audit_log.py` | Audit → security layer |
| `plugins/base.py` | `framework/tools/plugins/` | Plugin base class |
| `plugins/loader.py` | `framework/tools/plugins/loader.py` | Plugin loader |
| `plugins/registry.py` | `framework/agents/agent_registry.py` | Plugin registry → agent registry |
| `saki_hub/main.py` | `gateway_desktop/src/renderer/` (referensi) | Desktop gateway (Python → Electron reference) |
| `tests/test_agents.py` | `tests/framework/test_agent_loop.py` | Agent tests |
| `tests/test_plugins.py` | `tests/framework/test_tool_calling.py` | Plugin/tool tests |
| `scripts/start_saki.bat` | `scripts/start_framework.sh` | Start script |
| `scripts/install_service.bat` | `scripts/` | Service install |

### ❌ File yang TIDAK dipindahkan (tetap di `saki_ai_assistant/`)

| File | Alasan |
|---|---|
| `src/server.py` | Streamlit-specific UI, tidak cocok dengan FastAPI server |
| `src/database.py` | SQLite+ChromaDB specific to Saki, bukan generic framework |
| `src/files.py` | Saki-specific file processor (PDF/DOCX uploader) |
| `src/memory_health.py` | Saki-specific memory analytics |
| `src/evidence.py` | Saki-specific evidence system |
| `saki_hub/` | Desktop hub Saki (Python-based, bukan Electron/React) |
| `plugins/whatsapp/` | Saki-specific WhatsApp plugin |
| `plugins/ocr_struk/` | OCR plugin Saki-specific |
| `plugins/speech/` | Speech plugin Saki-specific |
| `plugins/email_digest/` | Email digest Saki-specific |
| `data/` | Data user Saki |
| `saki_core/` | Service lifecycle Saki |
| `SAKI_SELF.md` | Identity file Saki |
| `whatsapp_config.json` | Konfigurasi WhatsApp Saki |

---

## Struktur Folder Target

```
e:\ProjectLily\my-agent-framework\
├── framework/                        ← 🧠 Core Agent Framework
│   ├── agents/
│   │   ├── base_agent.py             [COPY dari src/agents/base.py]
│   │   ├── react_agent.py            [BARU — stub dari pola di ai.py]
│   │   ├── supervisor_agent.py       [COPY dari src/agents/router.py]
│   │   └── agent_registry.py         [COPY dari plugins/registry.py]
│   ├── loop/
│   │   ├── planner.py                [BARU — stub]
│   │   ├── executor.py               [BARU — stub]
│   │   ├── observer.py               [BARU — stub]
│   │   ├── reflector.py              [BARU — stub dari pola ai.py]
│   │   └── agent_loop.py             [BARU — orchestrator stub]
│   ├── tools/
│   │   ├── base_tool.py              [BARU — abstract tool interface]
│   │   ├── web_search.py             [BARU — stub]
│   │   ├── code_executor.py          [BARU — stub]
│   │   ├── file_io.py                [COPY dari src/agents/skills/filesystem.py]
│   │   ├── http_request.py           [BARU — stub]
│   │   ├── shell_command.py          [COPY dari src/agents/skills/windows.py]
│   │   └── plugins/
│   │       ├── __init__.py           [COPY dari plugins/__init__.py]
│   │       ├── loader.py             [COPY dari plugins/loader.py]
│   │       └── example_plugin.py     [BARU — contoh]
│   ├── memory/
│   │   ├── short_term.py             [BARU — sliding window stub]
│   │   ├── long_term.py              [BARU — vector DB stub]
│   │   ├── episodic.py               [BARU — stub]
│   │   ├── compressor.py             [BARU — stub]
│   │   └── memory_manager.py         [BARU — stub]
│   ├── api/
│   │   ├── server.py                 [BARU — FastAPI entry point]
│   │   ├── routes/
│   │   │   ├── chat.py               [BARU — POST /api/v1/chat]
│   │   │   ├── agents.py             [BARU — GET /api/v1/agents]
│   │   │   ├── sessions.py           [BARU]
│   │   │   ├── models.py             [BARU]
│   │   │   └── upload.py             [BARU]
│   │   ├── websocket.py              [BARU — streaming]
│   │   ├── auth.py                   [BARU — JWT middleware]
│   │   └── middleware.py             [BARU]
│   └── security/
│       ├── jwt_handler.py            [BARU]
│       ├── input_sanitizer.py        [BARU — prompt injection protection]
│       ├── audit_log.py              [COPY dari src/audit_pipeline.py]
│       └── secrets.py                [BARU]
│
├── model_layer/                      ← ⚙️ Model Layer (Inference)
│   ├── adapters/
│   │   ├── base_adapter.py           [BARU — interface]
│   │   ├── ollama_adapter.py         [COPY dari src/model_router.py]
│   │   ├── openai_compat_adapter.py  [BARU — stub]
│   │   ├── llamacpp_adapter.py       [BARU — stub]
│   │   ├── vllm_adapter.py           [BARU — stub]
│   │   └── custom_adapter.py         [BARU — template]
│   ├── profiles/
│   │   ├── reasoning.yaml            [BARU]
│   │   ├── coding.yaml               [BARU]
│   │   ├── fast.yaml                 [BARU]
│   │   └── embedding.yaml            [BARU]
│   ├── model_manager.py              [COPY/refactor dari src/model_router.py]
│   └── tokenizer_utils.py            [BARU]
│
├── config/                           ← Konfigurasi
│   ├── models.yaml                   [BARU]
│   ├── agents.yaml                   [BARU]
│   ├── server.yaml                   [BARU]
│   └── .env.example                  [COPY dari saki_ai_assistant/.env.example]
│
├── gateway_mobile/                   ← 📱 Mobile (Flutter placeholder)
│   ├── lib/
│   │   ├── core/
│   │   │   ├── api_client.dart       [BARU — stub]
│   │   │   ├── auth_service.dart     [BARU — stub]
│   │   │   ├── websocket_service.dart [BARU — stub]
│   │   │   └── local_db.dart         [BARU — stub]
│   │   ├── screens/
│   │   │   ├── home_screen.dart      [BARU — stub]
│   │   │   ├── chat_screen.dart      [BARU — stub]
│   │   │   ├── agent_detail_screen.dart [BARU]
│   │   │   └── settings_screen.dart  [BARU]
│   │   ├── widgets/
│   │   │   ├── chat_bubble.dart      [BARU]
│   │   │   ├── tool_trace_card.dart  [BARU]
│   │   │   ├── agent_status_indicator.dart [BARU]
│   │   │   └── file_attachment_picker.dart [BARU]
│   │   ├── models/
│   │   │   ├── message.dart          [BARU]
│   │   │   ├── session.dart          [BARU]
│   │   │   └── agent.dart            [BARU]
│   │   └── main.dart                 [BARU]
│   ├── android/
│   │   ├── AndroidManifest.xml       [BARU — stub]
│   │   ├── build.gradle              [BARU — stub]
│   │   └── src/main/kotlin/
│   │       ├── MainActivity.kt       [BARU]
│   │       ├── NotificationPlugin.kt [BARU]
│   │       └── BiometricPlugin.kt    [BARU]
│   ├── ios/
│   │   ├── Info.plist                [BARU]
│   │   └── Runner/
│   │       ├── AppDelegate.swift     [BARU]
│   │       └── NotificationService.swift [BARU]
│   └── pubspec.yaml                  [BARU]
│
├── gateway_desktop/                  ← 🖥️ Desktop (Electron+React placeholder)
│   ├── src/
│   │   ├── main/
│   │   │   ├── main.ts               [BARU — stub]
│   │   │   ├── ipc_handlers.ts       [BARU]
│   │   │   ├── tray_menu.ts          [BARU]
│   │   │   └── auto_updater.ts       [BARU]
│   │   └── renderer/
│   │       ├── pages/
│   │       │   ├── Chat.tsx          [BARU]
│   │       │   ├── Dashboard.tsx     [BARU]
│   │       │   ├── AgentManager.tsx  [BARU]
│   │       │   ├── ModelConfig.tsx   [BARU]
│   │       │   ├── KnowledgeBase.tsx [BARU]
│   │       │   └── Settings.tsx      [BARU]
│   │       ├── components/
│   │       │   ├── ChatBubble.tsx    [BARU]
│   │       │   ├── ToolTracePanel.tsx [BARU]
│   │       │   ├── LogStream.tsx     [BARU]
│   │       │   ├── MemoryViewer.tsx  [BARU]
│   │       │   ├── MetricsCard.tsx   [BARU]
│   │       │   └── SplitView.tsx     [BARU]
│   │       ├── services/
│   │       │   ├── api.ts            [BARU]
│   │       │   ├── websocket.ts      [BARU]
│   │       │   └── auth.ts           [BARU]
│   │       ├── App.tsx               [BARU]
│   │       └── router.tsx            [BARU]
│   ├── package.json                  [BARU]
│   ├── electron-builder.json         [BARU]
│   └── tsconfig.json                 [BARU]
│
├── shared/                           ← 📄 Shared
│   ├── api_schema.ts                 [BARU]
│   ├── api_schema.py                 [BARU]
│   └── ws_events.ts                  [BARU]
│
├── scripts/                          ← DevOps scripts
│   ├── start_framework.sh            [COPY dari saki_ai_assistant/scripts/start_saki.bat]
│   ├── setup_qdrant.sh               [BARU]
│   ├── gen_jwt_secret.py             [BARU]
│   └── benchmark_model.py            [BARU]
│
├── tests/                            ← Testing
│   ├── framework/
│   │   ├── test_agent_loop.py        [COPY dari saki_ai_assistant/tests/test_agents.py]
│   │   ├── test_tool_calling.py      [COPY dari saki_ai_assistant/tests/test_plugins.py]
│   │   └── test_memory.py            [COPY dari saki_ai_assistant/tests/test_memory_health.py]
│   └── model_layer/
│       └── test_adapters.py          [COPY dari saki_ai_assistant/tests/test_model_router.py]
│
├── docs/                             ← Dokumentasi
│   ├── architecture.md               [BARU]
│   ├── api_reference.md              [BARU]
│   ├── plugin_guide.md               [BARU]
│   └── model_setup.md                [BARU]
│
├── README.md                         [BARU — framework README]
├── docker-compose.yml                [BARU — Framework + Qdrant + Ollama]
└── Makefile                          [BARU — shortcut dev commands]
```

---

## Open Questions

> [!IMPORTANT]
> **Apakah file yang di-copy ke framework harus direfactor isi-nya**, atau cukup disalin dulu dengan konten aslinya sebagai "starting point"?
> Rekomendasi saya: **salin dulu**, lalu tambahkan komentar TODO refactor di bagian yang perlu disesuaikan dengan arsitektur framework.

> [!NOTE]
> **Gateway Mobile & Desktop** — Folder `gateway_mobile/` (Flutter) dan `gateway_desktop/` (Electron+React) akan dibuat sebagai **stub** dengan file placeholder (berisi komentar tujuan file). Implementasi penuh membutuhkan toolchain Flutter/Node.js yang terpisah.

> [!NOTE]
> **Saki AI Assistant** — File yang TIDAK dipindahkan akan **tetap di tempat aslinya** di `e:\ProjectLily\saki_ai_assistant\`. Tidak ada file yang dihapus dari sana.

---

## Rencana Eksekusi

1. **Buat folder struktur** `my-agent-framework/` di `e:\ProjectLily\`
2. **Copy file relevan** dari `saki_ai_assistant/` ke lokasi baru (tidak memindahkan/menghapus dari sumber)
3. **Buat file stub/baru** untuk file yang belum ada di `saki_ai_assistant/`
4. **Buat file konfigurasi** (YAML, JSON, .env.example)
5. **Buat README.md** dan dokumentasi dasar

## Verification Plan

### Manual Verification
- Verifikasi seluruh struktur folder sudah sesuai dengan `custom_agent_framework_folder_structure.html`
- Pastikan file yang di-copy masih bisa diimport dengan benar (relative imports diupdate)
- Pastikan saki_ai_assistant tidak ada file yang hilang
