"""
custom_adapter.py — Template untuk Custom Model Adapter

Salin dan modifikasi file ini untuk mengintegrasikan
model atau inference backend yang belum didukung.
"""
import logging
from typing import Any, Dict, Iterator, List, Optional
from .base_adapter import BaseModelAdapter

logger = logging.getLogger("framework.adapters.custom")


class CustomAdapter(BaseModelAdapter):
    """
    Template custom adapter.

    Langkah untuk membuat adapter baru:
    1. Salin file ini
    2. Rename class ke NamaBackendAdapter
    3. Implementasikan complete() dan stream()
    4. Register di model_manager.py
    """

    def __init__(self, model_name: str, **kwargs: Any):
        super().__init__(model_name, **kwargs)
        # TODO: Inisialisasi backend/client di sini
        logger.info(f"CustomAdapter initialized: model={model_name}")

    def complete(
        self,
        messages: List[Dict],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        tools: Optional[List[Dict]] = None,
        **kwargs: Any,
    ) -> Dict:
        """
        TODO: Implementasikan pemanggilan model di sini.

        Pastikan mengembalikan format standar:
        {
            "content": str,
            "model": str,
            "elapsed": float,
            "tool_calls": List[Dict],
            "usage": {"input_tokens": int, "output_tokens": int},
        }
        """
        raise NotImplementedError("Implementasikan complete() untuk CustomAdapter")

    def stream(
        self,
        messages: List[Dict],
        temperature: float = 0.7,
        **kwargs: Any,
    ) -> Iterator[str]:
        """
        TODO: Implementasikan streaming response di sini.
        
        Yield setiap token/chunk sebagai string.
        """
        # Fallback ke complete() jika streaming belum diimplementasikan
        result = self.complete(messages, temperature, **kwargs)
        yield result.get("content", "")
