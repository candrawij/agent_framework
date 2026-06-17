"""
secrets.py — Secrets Management

Kelola secrets (API keys, tokens) dengan aman dari environment
variables atau file .env, dengan caching dan masking untuk log.
"""

import logging
import os
from pathlib import Path
from typing import Dict, Optional

logger = logging.getLogger("framework.security.secrets")


class SecretsManager:
    """
    Manager untuk secrets (API keys, credentials).

    Urutan resolusi secret:
    1. Loaded values (set via set_secret)
    2. Environment variables
    3. .env file (jika ada)
    4. Default value

    Semua secrets di-mask dalam logging.
    """

    def __init__(self, env_file: Optional[str] = None):
        self._secrets: Dict[str, str] = {}
        self._env_file = Path(env_file) if env_file else self._find_env_file()
        self._load_env_file()

    def get(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """
        Ambil nilai secret.

        Args:
            key: Nama secret/env var.
            default: Nilai default jika tidak ditemukan.

        Returns:
            Nilai secret atau default.
        """
        # 1. In-memory
        if key in self._secrets:
            return self._secrets[key]

        # 2. Environment
        value = os.environ.get(key)
        if value:
            return value

        # 3. Default
        if default is not None:
            return default

        logger.debug(f"Secret '{key}' tidak ditemukan")
        return None

    def get_required(self, key: str) -> str:
        """
        Ambil secret yang wajib ada.

        Raises:
            ValueError jika secret tidak ditemukan.
        """
        value = self.get(key)
        if not value:
            raise ValueError(
                f"Secret '{key}' wajib ada tapi tidak ditemukan. "
                f"Set via environment variable atau file .env"
            )
        return value

    def set_secret(self, key: str, value: str):
        """Set secret secara programatis."""
        self._secrets[key] = value

    def mask(self, value: str, visible_chars: int = 4) -> str:
        """Mask secret untuk logging aman."""
        if not value or len(value) <= visible_chars:
            return "***"
        return value[:visible_chars] + "*" * (len(value) - visible_chars)

    def get_masked(self, key: str) -> str:
        """Ambil nilai secret dalam format masked (untuk logging)."""
        value = self.get(key)
        if not value:
            return "[not set]"
        return self.mask(value)

    def check_all(self, required_keys: list) -> Dict[str, bool]:
        """
        Cek apakah semua required keys tersedia.

        Returns:
            Dict {key: is_present}
        """
        result = {}
        for key in required_keys:
            result[key] = bool(self.get(key))
        missing = [k for k, v in result.items() if not v]
        if missing:
            logger.warning(f"Missing secrets: {missing}")
        return result

    def _find_env_file(self) -> Optional[Path]:
        """Cari file .env di direktori project."""
        candidates = [
            Path.cwd() / ".env",
            Path.cwd() / "config" / ".env",
            Path(__file__).parent.parent.parent / ".env",
            Path(__file__).parent.parent.parent / "config" / ".env",
        ]
        for path in candidates:
            if path.exists():
                return path
        return None

    def _load_env_file(self):
        """Load secrets dari file .env."""
        if not self._env_file or not self._env_file.exists():
            return

        try:
            lines = self._env_file.read_text(encoding="utf-8").splitlines()
            loaded = 0
            for line in lines:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    key, _, value = line.partition("=")
                    key = key.strip()
                    value = value.strip().strip('"').strip("'")
                    # Jangan override env var yang sudah ada
                    if key and value and key not in os.environ:
                        os.environ[key] = value
                        loaded += 1
            logger.info(f"Loaded {loaded} secrets from {self._env_file}")
        except Exception as e:
            logger.warning(f"Failed to load .env file: {e}")


# Global instance
_global_secrets: Optional[SecretsManager] = None


def get_secrets() -> SecretsManager:
    """Get global SecretsManager singleton."""
    global _global_secrets
    if _global_secrets is None:
        _global_secrets = SecretsManager()
    return _global_secrets
