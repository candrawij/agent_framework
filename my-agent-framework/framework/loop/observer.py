"""
observer.py — Proses Hasil Tool → Observasi

Observer menerima output mentah dari tool/agent dan
mengubahnya menjadi observasi terstruktur yang bisa
digunakan oleh Reflector atau agent berikutnya.
"""

import json
import logging
import re
from typing import Any, Dict, List, Optional, Union

logger = logging.getLogger("framework.loop.observer")


class Observation:
    """Representasi satu observasi dari hasil tool/agent."""

    def __init__(
        self,
        source: str,
        content: Any,
        observation_type: str = "text",
        metadata: Optional[Dict] = None,
        success: bool = True,
    ):
        self.source = source          # Nama tool/agent yang menghasilkan
        self.content = content        # Konten observasi
        self.observation_type = observation_type  # "text", "json", "error", "empty"
        self.metadata = metadata or {}
        self.success = success

    def to_string(self, max_length: int = 2000) -> str:
        """Konversi observasi ke string untuk dimasukkan ke context."""
        if self.observation_type == "error":
            return f"[ERROR dari {self.source}]: {str(self.content)[:max_length]}"
        if self.observation_type == "empty":
            return f"[{self.source}]: Tidak ada hasil"
        if self.observation_type == "json":
            try:
                formatted = json.dumps(self.content, ensure_ascii=False, indent=2)
                return f"[{self.source}]:\n{formatted[:max_length]}"
            except Exception:
                pass
        return f"[{self.source}]: {str(self.content)[:max_length]}"

    def to_dict(self) -> Dict:
        return {
            "source": self.source,
            "content": str(self.content)[:500],
            "type": self.observation_type,
            "success": self.success,
            "metadata": self.metadata,
        }

    def __repr__(self) -> str:
        return f"<Observation source={self.source!r} type={self.observation_type} success={self.success}>"


class Observer:
    """
    Memproses output dari tool/agent menjadi observasi terstruktur.

    Fitur:
    - Parse berbagai format output (string, dict, list, dll)
    - Truncate output panjang dengan summary
    - Filter dan sanitize konten berbahaya
    - Agregasi beberapa observasi
    """

    def __init__(
        self,
        max_observation_length: int = 4000,
        model_adapter: Optional[Any] = None,  # Untuk summarize observasi panjang
    ):
        self.max_observation_length = max_observation_length
        self.model_adapter = model_adapter
        self._observations: List[Observation] = []

    # ==================== OBSERVE ====================

    def observe(
        self,
        source: str,
        raw_output: Any,
        observation_type: Optional[str] = None,
        metadata: Optional[Dict] = None,
    ) -> Observation:
        """
        Proses satu output menjadi Observation.

        Args:
            source: Nama tool/agent yang menghasilkan output.
            raw_output: Output mentah.
            observation_type: Override tipe observasi.
            metadata: Metadata tambahan.

        Returns:
            Observation terstruktur.
        """
        # Deteksi tipe
        detected_type = observation_type or self._detect_type(raw_output)

        # Normalize content
        content = self._normalize(raw_output, detected_type)

        # Truncate jika terlalu panjang
        content_str = str(content)
        if len(content_str) > self.max_observation_length:
            content = self._truncate(content_str, source)
            detected_type = "text"

        obs = Observation(
            source=source,
            content=content,
            observation_type=detected_type,
            metadata=metadata or {},
            success=detected_type != "error",
        )

        self._observations.append(obs)
        logger.debug(f"Observed: {source} → type={detected_type}, len={len(str(content))}")
        return obs

    def observe_error(self, source: str, error: Union[str, Exception]) -> Observation:
        """Buat observasi error."""
        error_msg = str(error)
        obs = Observation(
            source=source,
            content=error_msg,
            observation_type="error",
            success=False,
        )
        self._observations.append(obs)
        logger.debug(f"Error observed from {source}: {error_msg[:100]}")
        return obs

    def observe_batch(
        self,
        results: List[Dict],  # [{source, output, metadata}]
    ) -> List[Observation]:
        """Proses beberapa output sekaligus."""
        observations = []
        for item in results:
            obs = self.observe(
                source=item.get("source", "unknown"),
                raw_output=item.get("output"),
                metadata=item.get("metadata"),
            )
            observations.append(obs)
        return observations

    # ==================== AGGREGATION ====================

    def aggregate(
        self,
        observations: List[Observation],
        separator: str = "\n\n",
    ) -> str:
        """
        Gabungkan beberapa observasi menjadi satu string konteks.

        Args:
            observations: List observasi yang akan digabungkan.
            separator: Pemisah antar observasi.

        Returns:
            String gabungan observasi.
        """
        parts = []
        for obs in observations:
            if obs.success or obs.observation_type == "error":
                parts.append(obs.to_string(self.max_observation_length // len(observations)))
        return separator.join(parts)

    def get_context_string(self, last_n: int = 5) -> str:
        """Ambil N observasi terakhir sebagai context string."""
        recent = self._observations[-last_n:]
        return self.aggregate(recent)

    # ==================== HELPERS ====================

    def _detect_type(self, output: Any) -> str:
        """Deteksi tipe output secara otomatis."""
        if output is None:
            return "empty"
        if isinstance(output, Exception):
            return "error"
        if isinstance(output, (dict, list)):
            return "json"
        text = str(output).strip()
        if not text:
            return "empty"
        # Cek apakah JSON string
        if text.startswith(("{", "[")) and text.endswith(("}", "]")):
            try:
                json.loads(text)
                return "json"
            except Exception:
                pass
        return "text"

    def _normalize(self, output: Any, obs_type: str) -> Any:
        """Normalisasi output ke format yang sesuai."""
        if obs_type == "empty":
            return ""
        if obs_type == "json" and isinstance(output, str):
            try:
                return json.loads(output)
            except Exception:
                return output
        if obs_type == "error":
            return str(output)
        return output

    def _truncate(self, text: str, source: str) -> str:
        """
        Truncate teks panjang.
        Jika ada model adapter, gunakan LLM untuk summarize.
        """
        limit = self.max_observation_length

        if self.model_adapter:
            try:
                response = self.model_adapter.complete(
                    messages=[
                        {"role": "user", "content": (
                            f"Ringkas output berikut dalam maksimal 200 kata:\n\n{text[:4000]}"
                        )}
                    ],
                    temperature=0.3,
                )
                summary = response.get("content", "")
                return f"[Ringkasan dari {source}]: {summary}"
            except Exception as e:
                logger.debug(f"Summarize failed, using truncation: {e}")

        # Fallback: ambil awal + akhir
        half = limit // 2
        return f"{text[:half]}\n... [truncated {len(text) - limit} chars] ...\n{text[-half:]}"

    # ==================== HISTORY ====================

    def get_history(self, last_n: int = 20) -> List[Dict]:
        """Ambil N observasi terakhir sebagai dict."""
        return [obs.to_dict() for obs in self._observations[-last_n:]]

    def clear(self):
        """Bersihkan history observasi."""
        self._observations.clear()

    def get_stats(self) -> Dict:
        """Statistik observer."""
        total = len(self._observations)
        success = sum(1 for o in self._observations if o.success)
        return {
            "total": total,
            "success": success,
            "errors": total - success,
            "types": {
                t: sum(1 for o in self._observations if o.observation_type == t)
                for t in {"text", "json", "error", "empty"}
            },
        }
