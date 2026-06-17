"""
model_manager.py — Koordinator Model Layer

ModelManager adalah entry point ke semua model backend.
Mengelola multiple adapters, routing, dan fallback.
"""

import logging
from typing import Any, Dict, Iterator, List, Optional

from .adapters.base_adapter import BaseModelAdapter
from .adapters.ollama_adapter import OllamaAdapter, TaskType

logger = logging.getLogger("framework.model_manager")


class ModelManager:
    """
    Manager terpusat untuk semua model adapters.

    Fitur:
    - Register multiple adapters
    - Route request ke adapter yang tepat
    - Global fallback chain
    - Health monitoring
    """

    def __init__(self, default_adapter: Optional[BaseModelAdapter] = None):
        self._adapters: Dict[str, BaseModelAdapter] = {}
        self._default_adapter: Optional[BaseModelAdapter] = default_adapter

        if default_adapter:
            self.register("default", default_adapter)

    # ==================== REGISTER ====================

    def register(
        self,
        name: str,
        adapter: BaseModelAdapter,
        set_as_default: bool = False,
    ) -> "ModelManager":
        """
        Daftarkan adapter dengan nama.

        Args:
            name: Alias adapter (contoh: "ollama", "openai", "fast").
            adapter: Instance BaseModelAdapter.
            set_as_default: Jadikan default adapter.
        """
        self._adapters[name] = adapter
        if set_as_default or self._default_adapter is None:
            self._default_adapter = adapter
        logger.info(f"Adapter registered: '{name}' ({adapter.name})")
        return self

    def get_adapter(self, name: str) -> Optional[BaseModelAdapter]:
        """Ambil adapter berdasarkan nama."""
        return self._adapters.get(name)

    def set_default(self, name: str) -> bool:
        """Set adapter default."""
        adapter = self._adapters.get(name)
        if adapter:
            self._default_adapter = adapter
            return True
        return False

    # ==================== INFERENCE ====================

    def complete(
        self,
        messages: List[Dict],
        adapter_name: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        tools: Optional[List[Dict]] = None,
        **kwargs: Any,
    ) -> Dict:
        """
        Kirim request ke model.

        Args:
            messages: List {role, content}.
            adapter_name: Nama adapter yang digunakan (None = default).
            temperature: Kreativitas.
            max_tokens: Batas token.
            tools: Tool definitions.

        Returns:
            Dict response standar.
        """
        adapter = self._get_adapter(adapter_name)
        if adapter is None:
            return {
                "content": "[ModelManager: Tidak ada adapter terdaftar]",
                "model": "none",
                "usage": {},
                "tool_calls": [],
            }

        return adapter.complete(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            tools=tools,
            **kwargs,
        )

    def stream(
        self,
        messages: List[Dict],
        adapter_name: Optional[str] = None,
        temperature: float = 0.7,
        **kwargs: Any,
    ) -> Iterator[str]:
        """Streaming inference."""
        adapter = self._get_adapter(adapter_name)
        if adapter is None:
            yield "[ModelManager: Tidak ada adapter terdaftar]"
            return

        yield from adapter.stream(messages=messages, temperature=temperature, **kwargs)

    def embed(self, text: str, adapter_name: Optional[str] = None) -> List[float]:
        """Generate embedding."""
        adapter = self._get_adapter(adapter_name)
        if adapter is None:
            return []
        return adapter.embed(text)

    # ==================== HEALTH ====================

    def check_all_health(self) -> Dict[str, bool]:
        """Cek health semua adapter yang terdaftar."""
        status = {}
        for name, adapter in self._adapters.items():
            try:
                status[name] = adapter.check_health()
            except Exception:
                status[name] = False
        return status

    def get_default_info(self) -> Dict:
        """Info adapter default."""
        if self._default_adapter:
            return self._default_adapter.get_info()
        return {"status": "no adapter registered"}

    def get_stats(self) -> Dict:
        """Statistik semua adapter."""
        return {
            "adapters": list(self._adapters.keys()),
            "default": self._default_adapter.name if self._default_adapter else None,
            "health": self.check_all_health(),
        }

    # ==================== HELPERS ====================

    def _get_adapter(self, name: Optional[str]) -> Optional[BaseModelAdapter]:
        """Pilih adapter berdasarkan nama atau default."""
        if name:
            adapter = self._adapters.get(name)
            if adapter is None:
                logger.warning(f"Adapter '{name}' tidak ditemukan, menggunakan default")
            else:
                return adapter
        return self._default_adapter

    # ==================== FACTORY METHODS ====================

    @classmethod
    def with_ollama(
        cls,
        fast_model: str = "qwen2.5:3b",
        reasoning_model: str = "qwen3:4b",
        base_url: str = "http://localhost:11434",
    ) -> "ModelManager":
        """
        Factory: buat ModelManager dengan OllamaAdapter.

        Args:
            fast_model: Model untuk task ringan.
            reasoning_model: Model untuk reasoning berat.

        Returns:
            ModelManager yang sudah dikonfigurasi.
        """
        adapter = OllamaAdapter(
            model_name=fast_model,
            base_url=base_url,
            model_profiles={
                "fast": fast_model,
                "reasoning": reasoning_model,
                "embedding": "nomic-embed-text:latest",
                "fallback": fast_model,
            },
        )
        manager = cls(default_adapter=adapter)
        manager.register("ollama", adapter)
        return manager

    @classmethod
    def with_openai(
        cls,
        api_key: str,
        model_name: str = "gpt-4o-mini",
        base_url: str = "https://api.openai.com/v1",
    ) -> "ModelManager":
        """Factory: buat ModelManager dengan OpenAI adapter."""
        from .adapters.openai_compat_adapter import OpenAICompatAdapter
        adapter = OpenAICompatAdapter(
            model_name=model_name,
            api_key=api_key,
            base_url=base_url,
        )
        manager = cls(default_adapter=adapter)
        manager.register("openai", adapter)
        return manager

    def __repr__(self) -> str:
        return (
            f"<ModelManager adapters={list(self._adapters.keys())} "
            f"default={self._default_adapter.name if self._default_adapter else None}>"
        )
