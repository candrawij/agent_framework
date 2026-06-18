"""test_memory.py — Test untuk Memory System"""
import pytest
from framework.memory.short_term import ShortTermMemory
from framework.memory.episodic import EpisodicMemory
from framework.memory.compressor import MemoryCompressor


class TestShortTermMemory:
    def test_add_and_get(self):
        mem = ShortTermMemory(capacity=5)
        mem.add("Hello world", {"role": "user"})
        items = mem.get_all()
        assert len(items) == 1
        assert items[0]["content"] == "Hello world"

    def test_capacity_limit(self):
        mem = ShortTermMemory(capacity=3)
        for i in range(5):
            mem.add(f"message {i}")
        assert mem.size() == 3

    def test_get_context(self):
        mem = ShortTermMemory()
        mem.add("Line 1", {"role": "user"})
        mem.add("Line 2", {"role": "assistant"})
        ctx = mem.get_context("chat")
        assert "user: Line 1" in ctx
        assert "assistant: Line 2" in ctx

    def test_clear(self):
        mem = ShortTermMemory()
        mem.add("test")
        mem.clear()
        assert mem.size() == 0


class TestEpisodicMemory:
    def test_add_and_search(self):
        mem = EpisodicMemory()
        mem.add_episode("User asked about Python programming and we discussed loops")
        results = mem.search("Python loops")
        assert len(results) > 0

    def test_count(self):
        mem = EpisodicMemory()
        mem.add_episode("Episode 1")
        mem.add_episode("Episode 2")
        assert mem.count() == 2

    def test_clear(self):
        mem = EpisodicMemory()
        mem.add_episode("test")
        mem.clear()
        assert mem.count() == 0


class TestMemoryCompressor:
    def test_short_text_unchanged(self):
        comp = MemoryCompressor(max_output_chars=1000)
        short = "This is short text"
        result = comp.compress(short)
        assert result == short

    def test_long_text_compressed(self):
        comp = MemoryCompressor(max_output_chars=100)
        long_text = "Important word. " * 200
        result = comp.compress(long_text)
        assert result is not None
        assert len(result) <= 200  # Lebih pendek dari aslinya
