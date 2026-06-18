"""
openai_compat_adapter.py — Adapter untuk OpenAI API & Compatible Servers

Mendukung: OpenAI, LocalAI, LM Studio, Groq, Together AI,
dan server lain yang kompatibel dengan OpenAI API.
"""
import logging
import time
from typing import Any, Dict, Iterator, List, Optional
from .base_adapter import BaseModelAdapter

logger = logging.getLogger("framework.adapters.openai_compat")


class OpenAICompatAdapter(BaseModelAdapter):
    """
    Adapter untuk OpenAI-compatible API endpoints.

    Mendukung:
    - api.openai.com (OpenAI)
    - localhost:1234 (LM Studio)
    - localhost:8080 (LocalAI)
    - api.groq.com/openai/v1 (Groq)
    - api.together.xyz/v1 (Together AI)
    """

    def __init__(
        self,
        model_name: str,
        api_key: Optional[str] = None,
        base_url: str = "https://api.openai.com/v1",
        timeout: int = 60,
        organization: Optional[str] = None,
    ):
        super().__init__(model_name, api_key=api_key, base_url=base_url)
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._organization = organization

    def _get_client(self):
        """Buat httpx client dengan headers yang benar."""
        import httpx
        headers = {"Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        if self._organization:
            headers["OpenAI-Organization"] = self._organization
        return httpx.Client(headers=headers, timeout=self._timeout)

    def complete(
        self,
        messages: List[Dict],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        tools: Optional[List[Dict]] = None,
        **kwargs: Any,
    ) -> Dict:
        start = time.time()
        payload: Dict = {
            "model": self.model_name,
            "messages": messages,
            "temperature": temperature,
        }
        if max_tokens:
            payload["max_tokens"] = max_tokens
        if tools:
            payload["tools"] = tools

        try:
            with self._get_client() as client:
                resp = client.post(f"{self._base_url}/chat/completions", json=payload)
                resp.raise_for_status()
                data = resp.json()

            choice = data["choices"][0]
            message = choice["message"]
            content = message.get("content") or ""
            tool_calls_raw = message.get("tool_calls") or []

            tool_calls = [{
                "id": tc.get("id", ""),
                "name": tc["function"]["name"],
                "arguments": tc["function"].get("arguments", {}),
            } for tc in tool_calls_raw]

            usage = data.get("usage", {})
            elapsed = time.time() - start
            return {
                "content": content,
                "model": data.get("model", self.model_name),
                "elapsed": elapsed,
                "tool_calls": tool_calls,
                "usage": {
                    "input_tokens": usage.get("prompt_tokens", 0),
                    "output_tokens": usage.get("completion_tokens", 0),
                },
            }
        except Exception as e:
            logger.error(f"OpenAI API call failed: {e}")
            return {"content": f"[API Error: {type(e).__name__}]", "model": self.model_name, "usage": {}, "tool_calls": []}

    def stream(self, messages: List[Dict], temperature: float = 0.7, **kwargs: Any) -> Iterator[str]:
        payload = {
            "model": self.model_name,
            "messages": messages,
            "temperature": temperature,
            "stream": True,
        }
        try:
            import httpx
            import json as _json
            headers = {"Authorization": f"Bearer {self._api_key}", "Content-Type": "application/json"}
            with httpx.stream("POST", f"{self._base_url}/chat/completions",
                              json=payload, headers=headers, timeout=self._timeout) as resp:
                for line in resp.iter_lines():
                    if line.startswith("data: ") and not line.endswith("[DONE]"):
                        try:
                            chunk = _json.loads(line[6:])
                            delta = chunk["choices"][0].get("delta", {})
                            content = delta.get("content", "")
                            if content:
                                yield content
                        except Exception:
                            pass
        except Exception as e:
            yield f"\n[Stream error: {type(e).__name__}]"

    def check_health(self) -> bool:
        try:
            import httpx
            headers = {"Authorization": f"Bearer {self._api_key}"}
            resp = httpx.get(f"{self._base_url}/models", headers=headers, timeout=5)
            return resp.status_code == 200
        except Exception:
            return False
