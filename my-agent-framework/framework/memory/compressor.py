"""
compressor.py — Memory Compression

Kompres konten memori yang terlalu panjang menjadi ringkasan singkat.
Menggunakan LLM jika tersedia, atau fallback ke ekstraksi kalimat.
"""

import logging
import re
from typing import Any, List, Optional

logger = logging.getLogger("framework.memory.compressor")


class MemoryCompressor:
    """
    Kompres dan ringkas konten memori.

    Mode:
    - "extractive": Ambil kalimat paling penting (tanpa LLM)
    - "abstractive": Gunakan LLM untuk summarize (butuh model_adapter)
    """

    def __init__(
        self,
        model_adapter: Optional[Any] = None,
        mode: str = "extractive",
        max_output_chars: int = 500,
    ):
        self.model_adapter = model_adapter
        self.mode = mode if model_adapter else "extractive"
        self.max_output_chars = max_output_chars

    def compress(self, text: str) -> Optional[str]:
        """
        Kompres teks menjadi versi yang lebih singkat.

        Args:
            text: Teks yang akan dikompres.

        Returns:
            Teks yang dikompres, atau None jika gagal.
        """
        if not text or len(text) <= self.max_output_chars:
            return text

        if self.mode == "abstractive" and self.model_adapter:
            return self._abstractive_compress(text)
        return self._extractive_compress(text)

    def summarize(self, text: str, max_words: int = 100) -> Optional[str]:
        """
        Buat ringkasan singkat dari teks.

        Args:
            text: Teks sumber.
            max_words: Batas kata dalam ringkasan.

        Returns:
            Ringkasan atau None.
        """
        if not text:
            return None

        if self.model_adapter:
            try:
                response = self.model_adapter.complete(
                    messages=[
                        {
                            "role": "user",
                            "content": (
                                f"Ringkas teks berikut dalam maksimal {max_words} kata. "
                                f"Fokus pada informasi paling penting.\n\n{text[:3000]}"
                            ),
                        }
                    ],
                    temperature=0.3,
                )
                return response.get("content", "").strip()
            except Exception as e:
                logger.warning(f"LLM summarize failed: {e}")

        # Fallback: ambil beberapa kalimat pertama
        sentences = self._split_sentences(text)
        result = ""
        for sent in sentences:
            if len(result) + len(sent) > self.max_output_chars:
                break
            result += sent + " "
        return result.strip() or text[:self.max_output_chars]

    def _abstractive_compress(self, text: str) -> Optional[str]:
        """Kompres menggunakan LLM."""
        try:
            response = self.model_adapter.complete(
                messages=[
                    {
                        "role": "user",
                        "content": (
                            f"Kompres konten ini menjadi poin-poin penting "
                            f"dalam maksimal {self.max_output_chars} karakter:\n\n{text[:4000]}"
                        ),
                    }
                ],
                temperature=0.2,
            )
            compressed = response.get("content", "").strip()
            if compressed:
                return compressed[:self.max_output_chars]
        except Exception as e:
            logger.warning(f"LLM compression failed: {e}, using extractive")

        return self._extractive_compress(text)

    def _extractive_compress(self, text: str) -> str:
        """
        Kompres ekstraktif: ambil kalimat paling penting.
        Menggunakan TF-IDF sederhana tanpa library eksternal.
        """
        sentences = self._split_sentences(text)
        if not sentences:
            return text[:self.max_output_chars]

        # Hitung word frequency
        all_words = re.findall(r'\w+', text.lower())
        word_freq: dict = {}
        for word in all_words:
            if len(word) > 3:  # Skip stop words pendek
                word_freq[word] = word_freq.get(word, 0) + 1

        # Score setiap kalimat
        scored = []
        for sent in sentences:
            words = re.findall(r'\w+', sent.lower())
            score = sum(word_freq.get(w, 0) for w in words if len(w) > 3)
            score = score / max(len(words), 1)  # Normalize per word
            scored.append((score, sent))

        scored.sort(key=lambda x: -x[0])

        # Ambil kalimat terbaik sampai limit
        result = ""
        for _, sent in scored:
            if len(result) + len(sent) + 2 > self.max_output_chars:
                break
            result += sent + " "

        return result.strip() or text[:self.max_output_chars]

    def _split_sentences(self, text: str) -> List[str]:
        """Pisahkan teks menjadi kalimat."""
        sentences = re.split(r'(?<=[.!?])\s+', text.strip())
        return [s.strip() for s in sentences if s.strip() and len(s) > 10]
