"""
audit_log.py — Audit Logging & Performance Monitoring

Refactored dari saki_ai_assistant/src/audit_pipeline.py dengan:
- Penghapusan dependency ke src.database dan src.ai Saki
- Generalisasi sebagai generic audit system
- Pemisahan antara AuditMetrics dan AuditLogger
"""

import json
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("framework.security.audit")

# Token counting (opsional, tanpa dependency keras)
_TOKENIZER = None
try:
    from tokenizers import Tokenizer
    _TOKENIZER = Tokenizer.from_pretrained("Xenova/qwen2-tokenizer")
except Exception:
    pass  # Gunakan char-count fallback


def count_tokens(text: str) -> int:
    """Hitung jumlah token dalam text."""
    if not text:
        return 0
    if _TOKENIZER:
        try:
            return len(_TOKENIZER.encode(text).ids)
        except Exception:
            pass
    return max(1, len(text) // 4)  # ~4 chars per token


def count_messages_tokens(messages: List[Dict]) -> int:
    """Hitung total token dalam message list."""
    return sum(count_tokens(m.get("content", "")) for m in messages)


class AuditMetrics:
    """Simpan metrics untuk satu request/operasi."""

    def __init__(self, request_id: Optional[str] = None):
        self.request_id = request_id or datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:20]
        self.start_time = time.time()
        self.timestamps: Dict[str, float] = {}
        self.timings: Dict[str, float] = {}
        self.token_counts: Dict[str, int] = {}
        self.context_composition: Dict[str, int] = {}
        self.response_metrics: Dict[str, Any] = {}
        self.custom_data: Dict[str, Any] = {}

    def mark_start(self, operation: str):
        """Tandai mulai operasi."""
        self.timestamps[f"{operation}_start"] = time.time()

    def mark_end(self, operation: str) -> Optional[float]:
        """Tandai selesai operasi dan hitung durasi."""
        end = time.time()
        start_key = f"{operation}_start"
        if start_key in self.timestamps:
            duration = end - self.timestamps[start_key]
            self.timings[operation] = duration
            return duration
        return None

    def set_token_count(self, key: str, count: int):
        self.token_counts[key] = count

    def set_context_composition(self, composition: Dict[str, int]):
        self.context_composition = composition

    def set_response_metrics(self, response_tokens: int, inference_time: float):
        self.response_metrics = {
            "response_tokens": response_tokens,
            "inference_time": inference_time,
            "tps": response_tokens / inference_time if inference_time > 0 else 0,
        }

    def set_custom(self, key: str, value: Any):
        self.custom_data[key] = value

    def get_summary(self) -> Dict:
        return {
            "request_id": self.request_id,
            "total_time": time.time() - self.start_time,
            "timings": self.timings,
            "token_counts": self.token_counts,
            "context_composition": self.context_composition,
            "response_metrics": self.response_metrics,
            "custom": self.custom_data,
            "timestamp": datetime.now().isoformat(),
        }

    def log_summary(self) -> Dict:
        """Log ringkasan audit ke logger."""
        summary = self.get_summary()
        logger.info(f"AUDIT #{summary['request_id']}")
        for op, duration in summary["timings"].items():
            logger.info(f"  {op:25s}: {duration:.3f}s")
        logger.info(f"  TOTAL: {summary['total_time']:.3f}s")
        return summary


class AuditLogger:
    """
    Logger audit yang menyimpan semua event ke file dan/atau database.
    Menggantikan peran audit_pipeline Saki dengan interface yang lebih generik.
    """

    def __init__(
        self,
        log_file: Optional[str] = None,
        log_level: int = logging.INFO,
        max_log_entries: int = 1000,
    ):
        self.log_file = Path(log_file) if log_file else None
        self._entries: List[Dict] = []
        self.max_log_entries = max_log_entries
        self._current_metrics: Optional[AuditMetrics] = None

        # Setup file handler jika ada log_file
        if self.log_file:
            self.log_file.parent.mkdir(parents=True, exist_ok=True)

    def start_request(self, request_id: Optional[str] = None) -> AuditMetrics:
        """Mulai audit untuk satu request baru."""
        self._current_metrics = AuditMetrics(request_id)
        return self._current_metrics

    def get_current(self) -> Optional[AuditMetrics]:
        """Get metrics request yang sedang berjalan."""
        return self._current_metrics

    def log_event(
        self,
        event_type: str,
        data: Dict,
        level: str = "info",
    ):
        """
        Log satu event audit.

        Args:
            event_type: Tipe event (contoh: "tool_call", "model_request", dll)
            data: Data event.
            level: "debug" | "info" | "warning" | "error"
        """
        entry = {
            "timestamp": datetime.now().isoformat(),
            "event_type": event_type,
            "level": level,
            **data,
        }

        self._entries.append(entry)
        if len(self._entries) > self.max_log_entries:
            self._entries.pop(0)

        # Log ke file
        if self.log_file:
            try:
                with open(self.log_file, "a", encoding="utf-8") as f:
                    f.write(json.dumps(entry, ensure_ascii=False) + "\n")
            except Exception as e:
                logger.warning(f"Failed to write audit log: {e}")

        # Log ke Python logger
        log_fn = getattr(logger, level, logger.info)
        log_fn(f"[{event_type}] {json.dumps(data, ensure_ascii=False)[:200]}")

    def log_model_call(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int,
        inference_time: float,
    ):
        """Log satu model call."""
        tps = output_tokens / inference_time if inference_time > 0 else 0
        self.log_event("model_call", {
            "model": model,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "inference_time_s": round(inference_time, 3),
            "tps": round(tps, 2),
        })

    def log_tool_call(
        self,
        tool_name: str,
        success: bool,
        duration_ms: float,
        error: Optional[str] = None,
    ):
        """Log satu tool call."""
        self.log_event("tool_call", {
            "tool": tool_name,
            "success": success,
            "duration_ms": round(duration_ms, 1),
            "error": error,
        }, level="info" if success else "warning")

    def log_security_event(
        self,
        event: str,
        severity: str = "medium",
        details: Optional[Dict] = None,
    ):
        """Log security event."""
        self.log_event("security", {
            "event": event,
            "severity": severity,
            **(details or {}),
        }, level="warning" if severity != "low" else "info")

    def get_entries(self, last_n: int = 100, event_type: Optional[str] = None) -> List[Dict]:
        """Ambil N entri log terakhir, dengan filter opsional."""
        entries = self._entries
        if event_type:
            entries = [e for e in entries if e.get("event_type") == event_type]
        return entries[-last_n:]

    def generate_report(self, metrics: Optional[AuditMetrics] = None) -> str:
        """
        Generate laporan audit yang bisa dibaca manusia.
        Menggantikan generate_audit_report() dari audit_pipeline.py Saki.
        """
        metrics = metrics or self._current_metrics
        if not metrics:
            return "No audit metrics available"

        summary = metrics.get_summary()
        lines = ["=" * 70, f"AUDIT REPORT #{summary['request_id']}", "=" * 70]

        # Context composition
        comp = summary.get("context_composition", {})
        if comp:
            total = sum(comp.values())
            lines.append("\nPROMPT COMPOSITION:")
            for component, tokens in sorted(comp.items(), key=lambda x: -x[1]):
                pct = (tokens / total * 100) if total > 0 else 0
                bar = "█" * int(pct / 5)
                lines.append(f"  {component:20s}: {tokens:5d} tokens ({pct:5.1f}%) {bar}")
            lines.append(f"  {'TOTAL':20s}: {total:5d} tokens")

        # Timings
        lines.append("\nOPERATION TIMINGS:")
        for op, duration in sorted(summary["timings"].items(), key=lambda x: -x[1]):
            bar = "█" * int(duration * 20)
            lines.append(f"  {op:25s}: {duration:.3f}s {bar}")

        # Response metrics
        rm = summary.get("response_metrics", {})
        if rm:
            tps = rm.get("tps", 0)
            lines.append(f"\nRESPONSE METRICS:")
            lines.append(f"  Response Tokens : {rm.get('response_tokens', 0)}")
            lines.append(f"  Inference Time  : {rm.get('inference_time', 0):.3f}s")
            lines.append(f"  TPS             : {tps:.2f}")
            perf = "✅ Excellent" if tps > 100 else "⚠️ Low" if tps < 20 else "✓ Normal"
            lines.append(f"  Performance     : {perf}")

        lines.append(f"\nTOTAL TIME: {summary['total_time']:.3f}s")
        lines.append("=" * 70)
        return "\n".join(lines)


# Global audit logger instance
_global_audit_logger: Optional[AuditLogger] = None


def get_audit_logger() -> AuditLogger:
    """Get global audit logger singleton."""
    global _global_audit_logger
    if _global_audit_logger is None:
        _global_audit_logger = AuditLogger()
    return _global_audit_logger
