"""
episodic.py — Episodic Memory

Menyimpan episode percakapan yang sudah selesai (diarsipkan).
Berguna untuk memahami konteks historis jangka panjang.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("framework.memory.episodic")


class EpisodicMemory:
    """
    Menyimpan episode percakapan yang sudah diarsipkan.

    Setiap episode berisi:
    - summary: Ringkasan percakapan
    - timestamp: Kapan terjadi
    - metadata: Info tambahan (session_id, topics, dll)

    Mendukung persistence ke file JSON (opsional).
    """

    def __init__(
        self,
        persist_path: Optional[str] = None,
        max_episodes: int = 500,
    ):
        self.persist_path = Path(persist_path) if persist_path else None
        self.max_episodes = max_episodes
        self._episodes: List[Dict] = []
        self._load_from_file()

    def add_episode(self, summary: str, metadata: Optional[Dict] = None) -> str:
        """
        Tambah episode baru.

        Args:
            summary: Ringkasan episode.
            metadata: Info tambahan (session_id, duration, dll).

        Returns:
            ID episode yang dibuat.
        """
        episode_id = f"ep_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')[:18]}"
        episode = {
            "id": episode_id,
            "summary": summary,
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata or {},
        }
        self._episodes.append(episode)

        # Trim jika terlalu banyak
        if len(self._episodes) > self.max_episodes:
            self._episodes = self._episodes[-self.max_episodes:]

        self._save_to_file()
        logger.debug(f"Episode saved: {episode_id} ({len(summary)} chars)")
        return episode_id

    def search(self, query: str, top_k: int = 3) -> List[str]:
        """
        Cari episode yang relevan dengan query (keyword-based).

        Args:
            query: Query pencarian.
            top_k: Jumlah episode yang dikembalikan.

        Returns:
            List summary episode yang relevan.
        """
        query_lower = query.lower()
        words = set(query_lower.split())

        scored: List[tuple] = []
        for ep in self._episodes:
            summary = ep.get("summary", "")
            ep_words = set(summary.lower().split())
            overlap = len(words & ep_words)
            if overlap > 0:
                scored.append((overlap, summary))

        scored.sort(key=lambda x: -x[0])
        return [s for _, s in scored[:top_k]]

    def get_recent(self, n: int = 5) -> List[Dict]:
        """Ambil N episode terbaru."""
        return self._episodes[-n:]

    def get_by_id(self, episode_id: str) -> Optional[Dict]:
        """Ambil episode berdasarkan ID."""
        for ep in self._episodes:
            if ep["id"] == episode_id:
                return ep
        return None

    def count(self) -> int:
        """Jumlah episode tersimpan."""
        return len(self._episodes)

    def clear(self):
        """Bersihkan semua episode."""
        self._episodes.clear()
        self._save_to_file()

    def _load_from_file(self):
        """Load episodes dari file JSON jika ada."""
        if self.persist_path and self.persist_path.exists():
            try:
                data = json.loads(self.persist_path.read_text(encoding="utf-8"))
                self._episodes = data if isinstance(data, list) else []
                logger.info(f"Loaded {len(self._episodes)} episodes from {self.persist_path}")
            except Exception as e:
                logger.warning(f"Failed to load episodes: {e}")

    def _save_to_file(self):
        """Simpan episodes ke file JSON."""
        if self.persist_path:
            try:
                self.persist_path.parent.mkdir(parents=True, exist_ok=True)
                self.persist_path.write_text(
                    json.dumps(self._episodes, ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )
            except Exception as e:
                logger.warning(f"Failed to save episodes: {e}")

    def __repr__(self) -> str:
        return f"<EpisodicMemory count={len(self._episodes)} max={self.max_episodes}>"
