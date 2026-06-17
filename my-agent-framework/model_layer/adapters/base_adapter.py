"""
base_adapter.py — Abstract Model Adapter Interface

Semua model backend harus mengimplementasikan BaseModelAdapter.
Menyediakan interface standar untuk complete(), stream(), dan embed().
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Iterator, List, Optional


class BaseModelAdapter(ABC):
    """
    Interface standar untuk semua model backend.

    Backend yang tersedia:
    - OllamaAdapter   → Model lokal via Ollama
    - OpenAICompatAdapter → OpenAI API atau kompatibel (LocalAI, dll)
    - LlamaCppAdapter → llama.cpp langsung
    - VLLMAdapter     → vLLM inference server

    Semua adapter harus mengembalikan format yang konsisten:
    {
        "content": str,   # Teks response
        "model": str,     # Nama model yang digunakan
        "usage": {        # Token usage (jika tersedia)
            "input_tokens": int,
            "output_tokens": int,
        }
    }
    """

    def __init__(self, model_name: str, **kwargs: Any):
        self.model_name = model_name
        self._config: Dict[str, Any] = kwargs

    @property
    def name(self) -> str:
        """Nama backend adapter."""
        return self.__class__.__name__

    @abstractmethod
    def complete(
        self,
        messages: List[Dict],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        tools: Optional[List[Dict]] = None,
        **kwargs: Any,
    ) -> Dict:
        """
        Kirim messages ke model dan kembalikan response penuh.

        Args:
            messages: List {role, content} dalam format OpenAI.
            temperature: Kreativitas model (0.0 = deterministic).
            max_tokens: Batas token output.
            tools: Tool definitions untuk tool calling.
            **kwargs: Parameter model spesifik.

        Returns:
            {
                "content": str,
                "model": str,
                "usage": {"input_tokens": int, "output_tokens": int},
                "tool_calls": List[Dict],  # Jika ada tool calls
            }
        """
        pass

    @abstractmethod
    def stream(
        self,
        messages: List[Dict],
        temperature: float = 0.7,
        **kwargs: Any,
    ) -> Iterator[str]:
        """
        Streaming response — yield token/chunk satu per satu.

        Args:
            messages: List {role, content}.
            temperature: Kreativitas model.
            **kwargs: Parameter tambahan.

        Yields:
            Token atau chunk teks.
        """
        pass

    def embed(self, text: str) -> List[float]:
        """
        Generate embedding vector untuk teks.
        Override di adapter yang mendukung embedding.

        Args:
            text: Teks yang akan di-embed.

        Returns:
            List float (embedding vector).

        Raises:
            NotImplementedError jika adapter tidak mendukung embedding.
        """
        raise NotImplementedError(f"{self.name} tidak mendukung embedding")

    def check_health(self) -> bool:
        """
        Cek apakah backend model dapat dijangkau.

        Returns:
            True jika tersedia.
        """
        try:
            self.complete([{"role": "user", "content": "ping"}], max_tokens=5)
            return True
        except Exception:
            return False

    def get_info(self) -> Dict:
        """Info adapter untuk API/logging."""
        return {
            "adapter": self.name,
            "model": self.model_name,
            "config": {k: v for k, v in self._config.items() if "key" not in k.lower()},
        }

    def __repr__(self) -> str:
        return f"<{self.name} model={self.model_name!r}>"
