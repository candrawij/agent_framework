"""
llamacpp_adapter.py — Adapter untuk llama.cpp Server

Menghubungkan ke llama.cpp HTTP server (llama-server).
"""
import logging
import time
from typing import Any, Dict, Iterator, List, Optional
from .base_adapter import BaseModelAdapter

logger = logging.getLogger("framework.adapters.llamacpp")


class LlamaCppAdapter(BaseModelAdapter):
    """
    Adapter untuk llama.cpp server (llama-server --port 8080).
    
    Jalankan: llama-server -m model.gguf --port 8080
    """

    def __init__(self, model_name: str = "local", base_url: str = "http://localhost:8080", timeout: int = 120):
        super().__init__(model_name, base_url=base_url)
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout

    def complete(self, messages: List[Dict], temperature: float = 0.7, max_tokens: Optional[int] = None, **kwargs: Any) -> Dict:
        import httpx, time
        start = time.time()
        payload = {"messages": messages, "temperature": temperature}
        if max_tokens:
            payload["n_predict"] = max_tokens
        try:
            resp = httpx.post(f"{self._base_url}/v1/chat/completions", json=payload, timeout=self._timeout)
            resp.raise_for_status()
            data = resp.json()
            content = data["choices"][0]["message"].get("content", "")
            return {"content": content, "model": self.model_name, "elapsed": time.time() - start, "tool_calls": [], "usage": {}}
        except Exception as e:
            return {"content": f"[llama.cpp error: {e}]", "model": self.model_name, "usage": {}, "tool_calls": []}

    def stream(self, messages: List[Dict], temperature: float = 0.7, **kwargs: Any) -> Iterator[str]:
        # TODO: Implement streaming via llama.cpp SSE endpoint
        result = self.complete(messages, temperature)
        yield result.get("content", "")

    def check_health(self) -> bool:
        try:
            import httpx
            return httpx.get(f"{self._base_url}/health", timeout=5).status_code == 200
        except Exception:
            return False
