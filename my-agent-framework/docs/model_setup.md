# Model Setup Guide

## Menggunakan Ollama (Rekomendasi)

### 1. Install Ollama
```bash
# Windows: download dari https://ollama.ai
# Linux/Mac:
curl -fsSL https://ollama.ai/install.sh | sh
```

### 2. Pull Model
```bash
ollama pull qwen2.5:3b        # Fast model
ollama pull qwen3:4b          # Reasoning model
ollama pull nomic-embed-text  # Embedding model (opsional)
```

### 3. Konfigurasi Framework
```yaml
# config/models.yaml
default_adapter: ollama
adapters:
  ollama:
    base_url: "http://localhost:11434"
    profiles:
      fast: "qwen2.5:3b"
      reasoning: "qwen3:4b"
```

---

## Menggunakan OpenAI API

```python
from model_layer import ModelManager

manager = ModelManager.with_openai(
    api_key="sk-...",
    model_name="gpt-4o-mini",
)
```

---

## Benchmark Model

```bash
python scripts/benchmark_model.py qwen2.5:3b
python scripts/benchmark_model.py qwen3:4b
```

---

## Custom Model (Template)

```python
from model_layer.adapters.custom_adapter import CustomAdapter

class MyBackendAdapter(CustomAdapter):
    def complete(self, messages, **kwargs):
        # Implementasi pemanggilan model kamu di sini
        result = my_model.generate(messages)
        return {"content": result, "model": self.model_name, "tool_calls": [], "usage": {}}
```
