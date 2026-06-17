"""
memory_manager.py — Koordinator Semua Layer Memori

MemoryManager adalah pintu masuk tunggal ke sistem memori.
Menyatukan short-term, long-term, dan episodic memory.
"""

import logging
from typing import Any, Dict, List, Optional

from .short_term import ShortTermMemory
from .long_term import LongTermMemory
from .episodic import EpisodicMemory
from .compressor import MemoryCompressor

logger = logging.getLogger("framework.memory.manager")


class MemoryManager:
    """
    Koordinator terpusat untuk semua jenis memori.

    Urutan penyimpanan:
    1. Short-term: percakapan aktif (sliding window)
    2. Long-term: fakta penting & dokumen (vector DB)
    3. Episodic: episode percakapan yang sudah selesai

    Urutan retrieval (saat query):
    1. Short-term (terbaru)
    2. Long-term (semantically relevant)
    3. Episodic (historical context)
    """

    def __init__(
        self,
        short_term: Optional[ShortTermMemory] = None,
        long_term: Optional[LongTermMemory] = None,
        episodic: Optional[EpisodicMemory] = None,
        compressor: Optional[MemoryCompressor] = None,
        auto_compress: bool = True,
    ):
        self.short_term = short_term or ShortTermMemory()
        self.long_term = long_term or LongTermMemory()
        self.episodic = episodic or EpisodicMemory()
        self.compressor = compressor or MemoryCompressor()
        self.auto_compress = auto_compress
        self._session_count: int = 0

    # ==================== ADD ====================

    def add(
        self,
        content: str,
        source: str = "agent",
        metadata: Optional[Dict] = None,
        layer: str = "auto",
    ):
        """
        Tambah konten ke memori.

        Args:
            content: Teks yang akan disimpan.
            source: Asal konten (agent, user, tool, dll).
            metadata: Metadata tambahan.
            layer: "short" | "long" | "episodic" | "auto"
        """
        metadata = metadata or {}
        metadata["source"] = source

        if layer == "short" or layer == "auto":
            self.short_term.add(content, metadata)

        if layer == "long":
            self.long_term.add(content, metadata)

        if layer == "episodic":
            self.episodic.add_episode(content, metadata)

        # Auto compress jika short-term penuh
        if self.auto_compress and self.short_term.is_full():
            self._compress_short_term()

    def add_message(self, role: str, content: str):
        """
        Tambah pesan chat ke short-term memory.

        Args:
            role: "user" | "assistant" | "system"
            content: Teks pesan.
        """
        self.short_term.add(content, {"role": role})

    # ==================== GET ====================

    def get_relevant(self, query: str, top_k: int = 5) -> str:
        """
        Ambil memori yang relevan untuk query tertentu.

        Args:
            query: Pertanyaan atau konteks.
            top_k: Jumlah item dari long-term yang diambil.

        Returns:
            String gabungan dari semua layer memori.
        """
        parts = []

        # Short-term: selalu relevan
        short = self.short_term.get_context()
        if short:
            parts.append(f"[Percakapan terkini]\n{short}")

        # Long-term: semantic search
        long_results = self.long_term.search(query, top_k=top_k)
        if long_results:
            formatted = "\n".join([f"- {r}" for r in long_results])
            parts.append(f"[Memori jangka panjang]\n{formatted}")

        # Episodic: episode terkait (jika ada)
        episodes = self.episodic.search(query, top_k=2)
        if episodes:
            formatted = "\n".join([f"- {ep}" for ep in episodes])
            parts.append(f"[Episode terdahulu]\n{formatted}")

        return "\n\n".join(parts) if parts else ""

    def get_history(self, last_n: int = 10) -> List[Dict]:
        """Ambil N pesan terakhir dari short-term."""
        return self.short_term.get_recent(last_n)

    # ==================== MANAGE ====================

    def promote_to_long_term(self, content: str, metadata: Optional[Dict] = None):
        """Simpan konten penting ke long-term memory."""
        self.long_term.add(content, metadata or {})
        logger.debug(f"Promoted to long-term: '{content[:60]}'")

    def archive_session(self, session_id: str):
        """Arsipkan sesi aktif ke episodic memory."""
        messages = self.short_term.get_all()
        if messages:
            summary = self.compressor.summarize(
                "\n".join([m.get("content", "") for m in messages])
            )
            self.episodic.add_episode(
                summary or str(messages),
                {"session_id": session_id, "message_count": len(messages)},
            )
            self.short_term.clear()
            self._session_count += 1
            logger.info(f"Session '{session_id}' archived to episodic memory")

    def clear_short_term(self):
        """Bersihkan short-term memory."""
        self.short_term.clear()

    def clear_all(self):
        """Bersihkan SEMUA memori (hati-hati!)."""
        self.short_term.clear()
        self.long_term.clear()
        self.episodic.clear()
        logger.warning("All memory cleared!")

    def _compress_short_term(self):
        """Kompres short-term memory yang penuh ke long-term."""
        messages = self.short_term.get_all()
        if not messages:
            return
        text = "\n".join([m.get("content", "") for m in messages])
        compressed = self.compressor.compress(text)
        if compressed:
            self.long_term.add(compressed, {"source": "compression"})
        self.short_term.trim()
        logger.debug("Short-term memory compressed and trimmed")

    # ==================== STATS ====================

    def get_stats(self) -> Dict:
        return {
            "short_term_size": self.short_term.size(),
            "long_term_size": self.long_term.size(),
            "episodic_count": self.episodic.count(),
            "sessions_archived": self._session_count,
            "short_term_capacity": self.short_term.capacity,
        }
