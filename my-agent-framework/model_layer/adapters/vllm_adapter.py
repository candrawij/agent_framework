"""
vllm_adapter.py — Adapter untuk vLLM Inference Server

vLLM menyediakan OpenAI-compatible API dengan throughput tinggi.
"""
import logging
from typing import Any, Dict, Iterator, List, Optional
from .openai_compat_adapter import OpenAICompatAdapter

logger = logging.getLogger("framework.adapters.vllm")


class VLLMAdapter(OpenAICompatAdapter):
    """
    Adapter untuk vLLM server.

    vLLM menggunakan OpenAI-compatible API, jadi kita
    reuse OpenAICompatAdapter dengan base_url yang berbeda.

    Jalankan: python -m vllm.entrypoints.openai.api_server --model MODEL --port 8000
    """

    def __init__(
        self,
        model_name: str,
        base_url: str = "http://localhost:8000/v1",
        timeout: int = 120,
        max_concurrency: int = 256,
    ):
        super().__init__(
            model_name=model_name,
            api_key="EMPTY",  # vLLM tidak butuh API key
            base_url=base_url,
            timeout=timeout,
        )
        self._max_concurrency = max_concurrency
        logger.info(f"VLLMAdapter initialized: {base_url}, model={model_name}")

    def complete(self, messages: List[Dict], temperature: float = 0.7, **kwargs: Any) -> Dict:
        # vLLM: tambahkan skip_special_tokens
        kwargs.setdefault("extra_body", {"skip_special_tokens": True})
        return super().complete(messages, temperature, **kwargs)
