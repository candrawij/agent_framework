"""
ollama_adapter.py — Adapter untuk Ollama Backend

Menghubungkan framework ke Ollama lokal.
Mendukung routing ke beberapa model berdasarkan TaskType.

Refactored dari saki_ai_assistant/src/model_router.py dengan:
- Implementasi BaseModelAdapter interface
- Generalisasi TaskType (tidak hanya Saki-specific)
- Penambahan stream() dan embed()
- Proper fallback chain
"""

import logging
import time
from enum import Enum
from typing import Any, Dict, Iterator, List, Optional

from .base_adapter import BaseModelAdapter

logger = logging.getLogger("framework.adapters.ollama")


class TaskType(Enum):
    """Kategori task berdasarkan kompleksitas kognitif."""
    FAST = "fast"             # Chat ringan, greeting, agent commands
    REASONING = "reasoning"   # Analisis mendalam, reflection, merge
    EMBEDDING = "embedding"   # Generate embedding
    CODING = "coding"         # Generate / debug kode
    SUMMARIZE = "summarize"   # Ringkasan dokumen


class OllamaAdapter(BaseModelAdapter):
    """
    Adapter untuk Ollama — model inference lokal.

    Mendukung:
    - Multi-model routing (fast / reasoning / coding)
    - Automatic fallback
    - Tool calling (format OpenAI)
    - Streaming
    - Embedding generation
    """

    def __init__(
        self,
        model_name: str = "qwen2.5:3b",
        base_url: str = "http://localhost:11434",
        timeout: int = 120,
        model_profiles: Optional[Dict[str, str]] = None,
        task_routing: Optional[Dict[TaskType, str]] = None,
    ):
        super().__init__(model_name, base_url=base_url, timeout=timeout)
        self._base_url = base_url
        self._timeout = timeout

        # Profil model: tier → model name
        self._profiles: Dict[str, str] = model_profiles or {
            "fast": model_name,
            "reasoning": "qwen3:4b",
            "coding": "qwen2.5-coder:7b",
            "embedding": "nomic-embed-text:latest",
            "fallback": model_name,
        }

        # Routing task → tier
        self._task_routing: Dict[TaskType, str] = task_routing or {
            TaskType.FAST: "fast",
            TaskType.SUMMARIZE: "fast",
            TaskType.CODING: "coding",
            TaskType.REASONING: "reasoning",
            TaskType.EMBEDDING: "embedding",
        }

        # Cache ketersediaan model
        self._model_cache: List[str] = []
        self._cache_time: float = 0
        self._cache_ttl: float = 300  # 5 menit

    # ==================== CORE INTERFACE ====================

    def complete(
        self,
        messages: List[Dict],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        tools: Optional[List[Dict]] = None,
        task_type: Optional[TaskType] = None,
        model_override: Optional[str] = None,
        **kwargs: Any,
    ) -> Dict:
        """
        Kirim request ke Ollama dan kembalikan response.

        Args:
            messages: List {role, content}.
            temperature: 0.0 = deterministic.
            max_tokens: Batas token output.
            tools: Tool definitions untuk tool calling.
            task_type: Tipe task untuk routing otomatis.
            model_override: Override model secara eksplisit.

        Returns:
            {content, model, usage, tool_calls}
        """
        try:
            import ollama as _ollama
        except ImportError:
            return {"content": "❌ Ollama tidak terinstall: pip install ollama", "model": "none", "usage": {}}

        # Pilih model
        model = model_override or self._select_model(task_type)
        logger.info(f"Ollama complete: model={model}, messages={len(messages)}, task={task_type}")

        start = time.time()

        options: Dict = {"temperature": temperature}
        if max_tokens:
            options["num_predict"] = max_tokens

        try:
            kwargs_send: Dict = {"model": model, "messages": messages, "options": options}
            if tools:
                kwargs_send["tools"] = tools

            response = _ollama.chat(**kwargs_send)
            elapsed = time.time() - start

            message = response.get("message", {})
            content = message.get("content", "")
            tool_calls_raw = message.get("tool_calls", [])

            # Normalize tool calls ke format standar
            tool_calls = []
            for tc in (tool_calls_raw or []):
                func = tc.get("function", tc)
                tool_calls.append({
                    "id": str(time.time()),
                    "name": func.get("name", ""),
                    "arguments": func.get("arguments", {}),
                })

            # Token usage
            usage_raw = response.get("usage", {})
            input_tokens = usage_raw.get("prompt_tokens", len(str(messages)) // 4)
            output_tokens = usage_raw.get("completion_tokens", len(content) // 4)

            logger.info(
                f"Ollama response: {output_tokens} tokens, {elapsed:.1f}s, "
                f"TPS={output_tokens/elapsed:.1f}"
            )

            return {
                "content": content,
                "model": model,
                "elapsed": elapsed,
                "tool_calls": tool_calls,
                "usage": {
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                },
            }

        except Exception as e:
            elapsed = time.time() - start
            logger.error(f"Ollama {model} failed ({elapsed:.1f}s): {e}")

            # Fallback ke model lain
            fallback = self._get_fallback(model)
            if fallback and fallback != model:
                logger.warning(f"Falling back to {fallback}")
                try:
                    fb_response = _ollama.chat(
                        model=fallback,
                        messages=messages,
                        options={"temperature": temperature},
                    )
                    fb_elapsed = time.time() - start
                    return {
                        "content": fb_response.get("message", {}).get("content", ""),
                        "model": f"{fallback} (fallback)",
                        "elapsed": fb_elapsed,
                        "tool_calls": [],
                        "usage": {},
                    }
                except Exception as e2:
                    logger.error(f"Fallback {fallback} also failed: {e2}")

            return {
                "content": f"[Model tidak tersedia: {type(e).__name__}]",
                "model": "none",
                "elapsed": elapsed,
                "tool_calls": [],
                "usage": {},
            }

    def stream(
        self,
        messages: List[Dict],
        temperature: float = 0.7,
        task_type: Optional[TaskType] = None,
        model_override: Optional[str] = None,
        **kwargs: Any,
    ) -> Iterator[str]:
        """Streaming response dari Ollama."""
        try:
            import ollama as _ollama
        except ImportError:
            yield "❌ Ollama tidak terinstall"
            return

        model = model_override or self._select_model(task_type)
        logger.info(f"Ollama stream: model={model}")

        try:
            for chunk in _ollama.chat(
                model=model,
                messages=messages,
                stream=True,
                options={"temperature": temperature},
            ):
                content = chunk.get("message", {}).get("content", "")
                if content:
                    yield content
        except Exception as e:
            logger.error(f"Ollama stream failed: {e}")
            yield f"\n[Stream error: {type(e).__name__}]"

    def embed(self, text: str, model_override: Optional[str] = None) -> List[float]:
        """Generate embedding dengan Ollama."""
        try:
            import ollama as _ollama
            model = model_override or self._profiles.get("embedding", self.model_name)
            response = _ollama.embeddings(model=model, prompt=text)
            return response.get("embedding", [])
        except ImportError:
            raise NotImplementedError("Ollama tidak terinstall")
        except Exception as e:
            logger.error(f"Ollama embed failed: {e}")
            return []

    # ==================== MODEL MANAGEMENT ====================

    def get_available_models(self, use_cache: bool = True) -> List[str]:
        """Daftar model yang tersedia di Ollama lokal."""
        now = time.time()
        if use_cache and self._model_cache and (now - self._cache_time) < self._cache_ttl:
            return self._model_cache

        try:
            import ollama as _ollama
            result = _ollama.list()
            models = [m["name"] for m in result.get("models", [])]
            self._model_cache = models
            self._cache_time = now
            return models
        except Exception as e:
            logger.warning(f"Cannot list Ollama models: {e}")
            return list(self._profiles.values())

    def check_health(self) -> bool:
        """Cek apakah Ollama server bisa dijangkau."""
        try:
            import httpx
            resp = httpx.get(f"{self._base_url}/api/tags", timeout=5)
            return resp.status_code == 200
        except Exception:
            return False

    def set_model_profile(self, tier: str, model_name: str) -> "OllamaAdapter":
        """Set model untuk tier tertentu."""
        self._profiles[tier] = model_name
        return self

    def set_task_routing(self, task_type: TaskType, tier: str) -> "OllamaAdapter":
        """Set routing task ke tier."""
        self._task_routing[task_type] = tier
        return self

    # ==================== HELPERS ====================

    def _select_model(self, task_type: Optional[TaskType] = None) -> str:
        """Pilih model berdasarkan task type."""
        if task_type is None:
            return self._profiles.get("fast", self.model_name)
        tier = self._task_routing.get(task_type, "fast")
        return self._profiles.get(tier, self.model_name)

    def _get_fallback(self, current_model: str) -> Optional[str]:
        """Cari model fallback untuk model yang gagal."""
        fallback = self._profiles.get("fallback", self.model_name)
        if fallback == current_model:
            # Cari tier yang berbeda
            for tier, model in self._profiles.items():
                if model != current_model and tier != "embedding":
                    return model
        return fallback

    def get_stats(self) -> Dict:
        return {
            "adapter": "OllamaAdapter",
            "base_url": self._base_url,
            "default_model": self.model_name,
            "profiles": self._profiles,
            "task_routing": {t.value: tier for t, tier in self._task_routing.items()},
            "available_models": self.get_available_models(),
        }
