"""
reflector.py — Evaluasi apakah task sudah selesai

Reflector mengevaluasi apakah agent sudah mencapai goal
yang ditetapkan, berdasarkan observasi yang terkumpul.
Juga bisa generate insight dari hasil iterasi.
"""

import json
import logging
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger("framework.loop.reflector")


class ReflectionOutcome(Enum):
    DONE = "done"           # Task selesai, keluar dari loop
    CONTINUE = "continue"   # Perlu iterasi lagi
    FAILED = "failed"       # Task gagal, tidak bisa dilanjutkan
    CLARIFY = "clarify"     # Perlu clarifikasi dari user


@dataclass
class ReflectionResult:
    """Hasil evaluasi reflector."""
    outcome: ReflectionOutcome
    confidence: float          # 0.0 - 1.0
    reasoning: str             # Alasan keputusan
    next_action: Optional[str] = None   # Saran aksi berikutnya
    insights: Optional[List[Dict]] = None  # Insight opsional

    @property
    def is_done(self) -> bool:
        return self.outcome == ReflectionOutcome.DONE

    @property
    def should_continue(self) -> bool:
        return self.outcome == ReflectionOutcome.CONTINUE

    def to_dict(self) -> Dict:
        return {
            "outcome": self.outcome.value,
            "confidence": self.confidence,
            "reasoning": self.reasoning,
            "next_action": self.next_action,
            "has_insights": bool(self.insights),
        }


class Reflector:
    """
    Evaluator apakah agent loop sudah selesai.

    Dua mode:
    1. Rule-based: Cek kata kunci dalam response (cepat, tanpa model)
    2. Model-based: Gunakan LLM untuk evaluasi semantik (akurat)

    Juga bisa generate insight dari pattern observasi yang terkumpul.
    """

    def __init__(
        self,
        model_adapter: Optional[Any] = None,
        confidence_threshold: float = 0.8,
        mode: str = "rule",   # "rule" | "model" | "hybrid"
    ):
        self.model_adapter = model_adapter
        self.confidence_threshold = confidence_threshold
        self.mode = mode

        # Kata kunci yang menandakan task selesai
        self._done_signals = [
            "final answer", "jawaban akhir", "selesai", "done",
            "complete", "berhasil", "sukses", "telah berhasil",
        ]
        # Kata kunci yang menandakan masih perlu lanjut
        self._continue_signals = [
            "belum", "masih perlu", "selanjutnya", "kemudian",
            "next step", "then", "also need", "but first",
        ]
        # Kata kunci error fatal
        self._failure_signals = [
            "tidak bisa", "gagal total", "error fatal", "cannot",
            "impossible", "not possible", "tidak tersedia",
        ]

    # ==================== EVALUATE ====================

    def evaluate(
        self,
        goal: str,
        observations: List[Any],    # List Observation objects atau strings
        last_response: str,
        iteration: int,
        max_iterations: int,
    ) -> ReflectionResult:
        """
        Evaluasi apakah task sudah selesai.

        Args:
            goal: Goal asli yang ingin dicapai.
            observations: Semua observasi yang terkumpul.
            last_response: Response terakhir dari agent.
            iteration: Iterasi saat ini (0-indexed).
            max_iterations: Batas iterasi.

        Returns:
            ReflectionResult dengan outcome dan reasoning.
        """
        # Forced termination: batas iterasi tercapai
        if iteration >= max_iterations - 1:
            return ReflectionResult(
                outcome=ReflectionOutcome.DONE,
                confidence=1.0,
                reasoning=f"Batas iterasi maksimum ({max_iterations}) tercapai.",
            )

        if self.mode == "model" and self.model_adapter:
            return self._evaluate_with_model(
                goal, observations, last_response, iteration
            )
        elif self.mode == "hybrid" and self.model_adapter:
            rule_result = self._evaluate_with_rules(last_response, iteration)
            if rule_result.confidence >= self.confidence_threshold:
                return rule_result
            return self._evaluate_with_model(goal, observations, last_response, iteration)
        else:
            return self._evaluate_with_rules(last_response, iteration)

    def _evaluate_with_rules(
        self, last_response: str, iteration: int
    ) -> ReflectionResult:
        """Evaluasi berbasis kata kunci (cepat, tanpa model)."""
        response_lower = last_response.lower()

        # Cek tanda selesai
        for signal in self._done_signals:
            if signal in response_lower:
                return ReflectionResult(
                    outcome=ReflectionOutcome.DONE,
                    confidence=0.85,
                    reasoning=f"Ditemukan sinyal selesai: '{signal}'",
                )

        # Cek kegagalan fatal
        for signal in self._failure_signals:
            if signal in response_lower:
                return ReflectionResult(
                    outcome=ReflectionOutcome.FAILED,
                    confidence=0.75,
                    reasoning=f"Ditemukan sinyal kegagalan: '{signal}'",
                )

        # Cek sinyal lanjut
        for signal in self._continue_signals:
            if signal in response_lower:
                return ReflectionResult(
                    outcome=ReflectionOutcome.CONTINUE,
                    confidence=0.7,
                    reasoning=f"Ditemukan sinyal lanjut: '{signal}'",
                    next_action="Lanjutkan eksekusi berdasarkan sinyal.",
                )

        # Default: setelah iterasi pertama, anggap selesai
        if iteration > 0:
            return ReflectionResult(
                outcome=ReflectionOutcome.DONE,
                confidence=0.6,
                reasoning="Tidak ada sinyal lanjut ditemukan, task dianggap selesai.",
            )

        return ReflectionResult(
            outcome=ReflectionOutcome.CONTINUE,
            confidence=0.55,
            reasoning="Iterasi pertama, melanjutkan loop.",
        )

    def _evaluate_with_model(
        self,
        goal: str,
        observations: List[Any],
        last_response: str,
        iteration: int,
    ) -> ReflectionResult:
        """Evaluasi semantik menggunakan LLM."""
        obs_summary = "\n".join([
            str(o.to_string(300) if hasattr(o, "to_string") else str(o)[:300])
            for o in observations[-5:]  # Ambil 5 observasi terakhir
        ])

        prompt = (
            f"Evaluasi apakah task berikut sudah selesai.\n\n"
            f"Goal: {goal}\n\n"
            f"Observasi terakhir:\n{obs_summary}\n\n"
            f"Response terakhir agent:\n{last_response[:500]}\n\n"
            f"Iterasi: {iteration + 1}\n\n"
            f"Jawab JSON:\n"
            '{"outcome": "done|continue|failed|clarify", '
            '"confidence": 0.0-1.0, "reasoning": "...", "next_action": "..."}'
        )

        try:
            response = self.model_adapter.complete(
                messages=[
                    {"role": "system", "content": "Kamu adalah evaluator yang menilai apakah task AI sudah selesai."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.1,
            )
            content = response.get("content", "")
            # Parse JSON
            match_start = content.find("{")
            match_end = content.rfind("}") + 1
            if match_start >= 0 and match_end > match_start:
                data = json.loads(content[match_start:match_end])
                outcome_str = data.get("outcome", "continue")
                try:
                    outcome = ReflectionOutcome(outcome_str)
                except ValueError:
                    outcome = ReflectionOutcome.CONTINUE

                return ReflectionResult(
                    outcome=outcome,
                    confidence=float(data.get("confidence", 0.7)),
                    reasoning=data.get("reasoning", ""),
                    next_action=data.get("next_action"),
                )
        except Exception as e:
            logger.warning(f"Model reflection failed: {e}, falling back to rules")

        return self._evaluate_with_rules(last_response, iteration)

    # ==================== INSIGHTS ====================

    def generate_insights(
        self,
        observations: List[Any],
        context: Optional[Dict] = None,
    ) -> List[Dict]:
        """
        Generate insight dari kumpulan observasi.
        Membutuhkan model_adapter.

        Args:
            observations: List observasi.
            context: Konteks tambahan.

        Returns:
            List insight dalam format dict.
        """
        if not self.model_adapter or not observations:
            return []

        obs_text = "\n".join([
            str(o.to_string(200) if hasattr(o, "to_string") else str(o)[:200])
            for o in observations
        ])

        prompt = (
            f"Analisis observasi berikut dan temukan pola atau insight penting.\n\n"
            f"Observasi:\n{obs_text}\n\n"
            f"Format JSON:\n"
            '[{"title": "...", "insight": "...", "category": "..."}]\n'
            "Jawab HANYA JSON array."
        )

        try:
            response = self.model_adapter.complete(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.4,
            )
            content = response.get("content", "[]")
            match_start = content.find("[")
            match_end = content.rfind("]") + 1
            if match_start >= 0:
                insights = json.loads(content[match_start:match_end])
                if isinstance(insights, list):
                    return insights
        except Exception as e:
            logger.warning(f"Insight generation failed: {e}")

        return []

    # ==================== CONFIGURATION ====================

    def add_done_signal(self, signal: str) -> "Reflector":
        """Tambah kata kunci 'selesai'."""
        self._done_signals.append(signal.lower())
        return self

    def add_continue_signal(self, signal: str) -> "Reflector":
        """Tambah kata kunci 'lanjut'."""
        self._continue_signals.append(signal.lower())
        return self

    def add_failure_signal(self, signal: str) -> "Reflector":
        """Tambah kata kunci 'gagal'."""
        self._failure_signals.append(signal.lower())
        return self
