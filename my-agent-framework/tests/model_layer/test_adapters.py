"""
test_adapters.py — Test untuk Model Adapters

Refactored dari saki_ai_assistant/tests/test_model_router.py
"""
import pytest
from unittest.mock import patch, MagicMock

from model_layer.adapters.ollama_adapter import OllamaAdapter, TaskType
from model_layer.model_manager import ModelManager


class TestOllamaAdapter:
    def test_init(self):
        adapter = OllamaAdapter(model_name="test:model")
        assert adapter.model_name == "test:model"

    def test_select_model_fast(self):
        adapter = OllamaAdapter()
        model = adapter._select_model(TaskType.FAST)
        assert model == adapter._profiles["fast"]

    def test_select_model_reasoning(self):
        adapter = OllamaAdapter()
        model = adapter._select_model(TaskType.REASONING)
        assert model == adapter._profiles["reasoning"]

    def test_set_model_profile(self):
        adapter = OllamaAdapter()
        adapter.set_model_profile("fast", "custom:model")
        assert adapter._profiles["fast"] == "custom:model"

    def test_get_stats(self):
        adapter = OllamaAdapter()
        stats = adapter.get_stats()
        assert "adapter" in stats
        assert "profiles" in stats


class TestModelManager:
    def test_init_empty(self):
        manager = ModelManager()
        assert manager._default_adapter is None

    def test_register_and_get(self):
        mock_adapter = MagicMock()
        mock_adapter.name = "MockAdapter"
        manager = ModelManager()
        manager.register("mock", mock_adapter, set_as_default=True)
        assert manager.get_adapter("mock") is mock_adapter

    def test_factory_with_ollama(self):
        manager = ModelManager.with_ollama(
            fast_model="qwen2.5:3b",
            reasoning_model="qwen3:4b",
        )
        assert "ollama" in manager._adapters
        assert manager._default_adapter is not None

    def test_complete_no_adapter(self):
        manager = ModelManager()
        result = manager.complete([{"role": "user", "content": "test"}])
        assert "Tidak ada adapter" in result["content"]
