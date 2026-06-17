"""
input_sanitizer.py — Prompt Injection Protection & Input Sanitization

Lindungi framework dari:
- Prompt injection attacks
- Jailbreak attempts
- Oversized inputs
- Malicious code injection
"""

import logging
import re
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger("framework.security.sanitizer")

# Pattern prompt injection yang umum
_INJECTION_PATTERNS = [
    r"ignore (all |previous |above |prior )?instructions?",
    r"disregard (all |previous |above )?instructions?",
    r"forget (all |everything|your|what you).{0,30}(told|said|instructed)",
    r"you are now.{0,50}(no longer|not)",
    r"new instructions?:",
    r"system prompt:",
    r"<\|?system\|?>",
    r"\[INST\]",
    r"####.{0,20}new (role|persona|instructions?)",
    r"pretend (you are|to be) (a|an) .{0,50}(without|no|ignore)",
    r"jailbreak",
    r"dan (do anything now|mode)",
    r"developer mode",
]

_COMPILED_PATTERNS = [re.compile(p, re.IGNORECASE) for p in _INJECTION_PATTERNS]


class InputSanitizer:
    """
    Sanitasi dan validasi input sebelum dikirim ke model.

    Fitur:
    - Deteksi prompt injection
    - Trim input berlebihan
    - Filter karakter berbahaya
    - Logging pelanggaran keamanan
    """

    def __init__(
        self,
        max_input_length: int = 50_000,
        block_on_injection: bool = True,
        audit_logger: Optional[object] = None,
        custom_blocked_patterns: Optional[List[str]] = None,
    ):
        self.max_input_length = max_input_length
        self.block_on_injection = block_on_injection
        self.audit_logger = audit_logger
        self._violation_count: int = 0

        # Compile custom patterns
        self._custom_patterns = []
        if custom_blocked_patterns:
            for p in custom_blocked_patterns:
                try:
                    self._custom_patterns.append(re.compile(p, re.IGNORECASE))
                except re.error as e:
                    logger.warning(f"Invalid custom pattern '{p}': {e}")

    def sanitize(self, text: str, context: Optional[str] = None) -> Tuple[str, bool, List[str]]:
        """
        Sanitasi satu teks input.

        Args:
            text: Input teks yang akan disanitasi.
            context: Konteks opsional (untuk logging).

        Returns:
            (sanitized_text, is_safe, violations)
            - sanitized_text: Teks setelah sanitasi
            - is_safe: False jika ada injection terdeteksi dan block_on_injection=True
            - violations: List pelanggaran yang ditemukan
        """
        violations: List[str] = []
        sanitized = text

        # 1. Cek panjang
        if len(text) > self.max_input_length:
            sanitized = sanitized[:self.max_input_length]
            violations.append(f"Input truncated from {len(text)} to {self.max_input_length} chars")
            logger.warning(f"Input truncated: {len(text)} → {self.max_input_length} chars")

        # 2. Strip null bytes dan control characters berbahaya
        sanitized = sanitized.replace("\x00", "").replace("\r", "\n")

        # 3. Deteksi prompt injection
        injection_found = self._detect_injection(sanitized)
        if injection_found:
            violations.extend(injection_found)
            self._violation_count += 1

            self._log_security_event(
                "prompt_injection_detected",
                severity="high",
                details={"patterns": injection_found, "context": context or "unknown"},
            )

            if self.block_on_injection:
                return "[INPUT DIBLOKIR: Prompt injection terdeteksi]", False, violations

        # 4. Cek custom patterns
        custom_violations = self._check_custom_patterns(sanitized)
        if custom_violations:
            violations.extend(custom_violations)
            if self.block_on_injection:
                return "[INPUT DIBLOKIR: Konten tidak diizinkan]", False, violations

        return sanitized, True, violations

    def sanitize_messages(
        self, messages: List[Dict]
    ) -> Tuple[List[Dict], bool, List[str]]:
        """
        Sanitasi list messages (format chat).

        Args:
            messages: List {role, content}.

        Returns:
            (sanitized_messages, all_safe, all_violations)
        """
        sanitized_messages = []
        all_violations: List[str] = []
        all_safe = True

        for msg in messages:
            content = msg.get("content", "")
            role = msg.get("role", "user")

            # Hanya sanitasi pesan dari user (bukan system/assistant)
            if role == "user":
                clean_content, is_safe, violations = self.sanitize(content, context=f"role={role}")
                all_violations.extend(violations)
                if not is_safe:
                    all_safe = False
                sanitized_messages.append({**msg, "content": clean_content})
            else:
                sanitized_messages.append(msg)

        return sanitized_messages, all_safe, all_violations

    def check_tool_input(self, tool_name: str, tool_input: Dict) -> Tuple[bool, Optional[str]]:
        """
        Validasi input tool sebelum dieksekusi.

        Returns:
            (is_safe, reason) — reason berisi alasan jika tidak aman.
        """
        # Cek string values dalam tool_input
        for key, value in tool_input.items():
            if isinstance(value, str):
                _, is_safe, violations = self.sanitize(value, context=f"tool={tool_name}.{key}")
                if not is_safe:
                    return False, f"Unsafe content in {key}: {violations[0]}"

        return True, None

    def _detect_injection(self, text: str) -> List[str]:
        """Deteksi prompt injection patterns."""
        found = []
        for pattern in _COMPILED_PATTERNS:
            if pattern.search(text):
                found.append(pattern.pattern)
        for pattern in self._custom_patterns:
            if pattern.search(text):
                found.append(pattern.pattern)
        return found

    def _check_custom_patterns(self, text: str) -> List[str]:
        """Cek custom blocked patterns."""
        found = []
        for pattern in self._custom_patterns:
            if pattern.search(text):
                found.append(f"Custom blocked pattern: {pattern.pattern}")
        return found

    def _log_security_event(self, event: str, severity: str, details: Dict):
        """Log event ke audit logger jika tersedia."""
        if self.audit_logger and hasattr(self.audit_logger, "log_security_event"):
            self.audit_logger.log_security_event(event, severity, details)
        else:
            logger.warning(f"SECURITY [{severity.upper()}] {event}: {details}")

    def get_stats(self) -> Dict:
        return {
            "total_violations": self._violation_count,
            "max_input_length": self.max_input_length,
            "block_on_injection": self.block_on_injection,
            "custom_patterns_count": len(self._custom_patterns),
        }
