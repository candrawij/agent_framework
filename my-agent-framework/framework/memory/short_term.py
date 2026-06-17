"""
short_term.py — Short-Term Memory (Sliding Window)

Menyimpan percakapan aktif dalam window terbatas.
Menggunakan deque untuk efisiensi FIFO.
"""

from collections import deque
from datetime import datetime
from typing import Any, Deque, Dict, List, Optional


class ShortTermMemory:
    """
    Memori jangka pendek berbasis sliding window.

    Menyimpan pesan percakapan aktif dengan batasan jumlah
    (capacity) dan ukuran total karakter (max_chars).
    """

    def __init__(self, capacity: int = 20, max_chars: int = 8000):
        self.capacity = capacity
        self.max_chars = max_chars
        self._buffer: Deque[Dict] = deque(maxlen=capacity)
        self._total_chars: int = 0

    def add(self, content: str, metadata: Optional[Dict] = None):
        """
        Tambah konten ke buffer.

        Args:
            content: Teks yang disimpan.
            metadata: Metadata (role, timestamp, source, dll).
        """
        entry = {
            "content": content,
            "timestamp": datetime.now().isoformat(),
            **(metadata or {}),
        }

        # Jika buffer penuh, hitung chars yang akan dihapus
        if len(self._buffer) == self.capacity:
            removed = self._buffer[0]
            self._total_chars -= len(removed.get("content", ""))

        self._buffer.append(entry)
        self._total_chars += len(content)

        # Jika masih melebihi max_chars, trim dari depan
        while self._total_chars > self.max_chars and len(self._buffer) > 1:
            removed = self._buffer.popleft()
            self._total_chars -= len(removed.get("content", ""))

    def get_recent(self, n: int = 10) -> List[Dict]:
        """Ambil N item terbaru."""
        items = list(self._buffer)
        return items[-n:]

    def get_all(self) -> List[Dict]:
        """Ambil semua item dalam buffer."""
        return list(self._buffer)

    def get_context(self, format: str = "flat") -> str:
        """
        Ambil semua konten sebagai string konteks.

        Args:
            format: "flat" (hanya content) | "chat" (role: content)
        """
        items = list(self._buffer)
        if not items:
            return ""

        if format == "chat":
            lines = []
            for item in items:
                role = item.get("role", "unknown")
                content = item.get("content", "")
                lines.append(f"{role}: {content}")
            return "\n".join(lines)
        else:
            return "\n".join([item.get("content", "") for item in items])

    def is_full(self) -> bool:
        """Apakah buffer sudah penuh."""
        return len(self._buffer) >= self.capacity or self._total_chars >= self.max_chars

    def trim(self, keep_last: Optional[int] = None):
        """
        Pangkas buffer — simpan hanya N item terakhir.

        Args:
            keep_last: Jumlah item yang dipertahankan (default: capacity // 2).
        """
        keep = keep_last or (self.capacity // 2)
        items = list(self._buffer)[-keep:]
        self._buffer.clear()
        self._total_chars = 0
        for item in items:
            self._buffer.append(item)
            self._total_chars += len(item.get("content", ""))

    def clear(self):
        """Bersihkan buffer."""
        self._buffer.clear()
        self._total_chars = 0

    def size(self) -> int:
        """Jumlah item dalam buffer."""
        return len(self._buffer)

    def __len__(self) -> int:
        return len(self._buffer)

    def __repr__(self) -> str:
        return f"<ShortTermMemory size={len(self._buffer)}/{self.capacity} chars={self._total_chars}>"
