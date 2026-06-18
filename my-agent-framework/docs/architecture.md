# Architecture Overview

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Gateway Layer                            │
│  ┌──────────────────┐          ┌──────────────────────────────┐ │
│  │  gateway_mobile  │          │      gateway_desktop         │ │
│  │  (Flutter)       │◄────────►│   (Electron + React)         │ │
│  └──────────────────┘  WS/REST └──────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                               │ REST / WebSocket
┌──────────────────────────────▼─────────────────────────────────┐
│                     framework/api/                              │
│         FastAPI Server (REST + WebSocket streaming)             │
└──────────────────────────────┬─────────────────────────────────┘
                               │
┌──────────────────────────────▼─────────────────────────────────┐
│                     Agent Loop                                  │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────────────┐ │
│  │ Planner  │→ │ Executor │→ │ Observer │→ │   Reflector    │ │
│  └──────────┘  └──────────┘  └──────────┘  └────────────────┘ │
└──────────────────────────────┬─────────────────────────────────┘
                               │
┌────────────┬─────────────────┼──────────────────┬─────────────┐
│  Agents    │     Tools       │      Memory      │  Security   │
│ ─────────  │ ─────────────── │ ──────────────── │ ─────────── │
│ Base       │ WebSearch       │ ShortTerm        │ JWT         │
│ ReAct      │ FileIO          │ LongTerm (vec)   │ Sanitizer   │
│ Supervisor │ ShellCommand    │ Episodic         │ AuditLog    │
│ Registry   │ HttpRequest     │ Compressor       │ Secrets     │
│            │ CodeExecutor    │ MemoryManager    │             │
│            │ Plugins         │                  │             │
└────────────┴─────────────────┴──────────────────┴─────────────┘
                               │
┌──────────────────────────────▼─────────────────────────────────┐
│                     model_layer/                                │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                   ModelManager                          │   │
│  ├───────────────────────────────────────────────────────  │   │
│  │  OllamaAdapter │ OpenAICompatAdapter │ LlamaCppAdapter  │   │
│  │  VLLMAdapter   │ CustomAdapter                          │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

## Component Descriptions

### framework/agents/
| Class | Fungsi |
|-------|--------|
| `BaseAgent` | Abstract base dengan lifecycle hooks, tools, history |
| `ReActAgent` | Thought→Action→Observation loop dengan tool calling |
| `SupervisorAgent` | Orchestrator yang routing ke sub-agent |
| `AgentRegistry` | Registry dengan auto-discover & factory methods |

### framework/loop/
| Class | Fungsi |
|-------|--------|
| `Planner` | Decompose goal → task graph dengan topological sort |
| `Executor` | Jalankan tool calls dengan timeout, retry, sandbox |
| `Observer` | Proses output → structured Observation |
| `Reflector` | Evaluasi apakah task selesai (rule/LLM-based) |
| `AgentLoop` | Orchestrator siklus Plan→Execute→Observe→Reflect |

### model_layer/
| Adapter | Backend |
|---------|---------|
| `OllamaAdapter` | Ollama lokal (multi-model routing) |
| `OpenAICompatAdapter` | OpenAI, Groq, Together AI, LocalAI, LM Studio |
| `LlamaCppAdapter` | llama.cpp HTTP server |
| `VLLMAdapter` | vLLM inference server |
| `CustomAdapter` | Template untuk backend kustom |

## Data Flow

```
User Input
    │
    ▼
InputSanitizer ──► [BLOCKED if injection detected]
    │
    ▼
SupervisorAgent (routing: keyword / LLM)
    │
    ▼
AgentLoop.run(goal)
    ├── Planner.plan(goal) ──► [Task1, Task2, ...]
    │
    ├── for each Task:
    │   ├── Executor.execute(tool_name, input)
    │   ├── Observer.observe(output)
    │   └── Reflector.evaluate(observations) ──► DONE / CONTINUE / FAILED
    │
    └── LoopRunResult(final_answer, stats)
           │
           ▼
    API Response (REST or WebSocket stream)
```
