"""
jwt_handler.py — JWT Authentication Handler

Generate, verify, dan decode JWT tokens untuk autentikasi API.
"""

import hashlib
import hmac
import json
import logging
import os
import time
from base64 import urlsafe_b64decode, urlsafe_b64encode
from typing import Any, Dict, Optional

logger = logging.getLogger("framework.security.jwt")


class JWTHandler:
    """
    Handler JWT sederhana tanpa dependency PyJWT.

    Mendukung:
    - HS256 (HMAC-SHA256)
    - Access tokens dan refresh tokens
    - Configurable expiry
    """

    ALGORITHM = "HS256"

    def __init__(
        self,
        secret: Optional[str] = None,
        access_ttl: int = 3600,       # 1 jam
        refresh_ttl: int = 86400 * 7, # 7 hari
    ):
        self.secret = secret or os.environ.get("JWT_SECRET", "")
        if not self.secret:
            logger.warning(
                "JWT_SECRET tidak ditemukan di env! "
                "Set JWT_SECRET atau berikan secret ke JWTHandler(secret=...)"
            )
            # Generate random secret untuk session ini (tidak persisten)
            import secrets
            self.secret = secrets.token_hex(32)

        self.access_ttl = access_ttl
        self.refresh_ttl = refresh_ttl

    def create_access_token(self, payload: Dict[str, Any]) -> str:
        """
        Buat access token dengan TTL pendek.

        Args:
            payload: Data yang akan disimpan dalam token.

        Returns:
            JWT string.
        """
        data = {
            **payload,
            "iat": int(time.time()),
            "exp": int(time.time()) + self.access_ttl,
            "type": "access",
        }
        return self._encode(data)

    def create_refresh_token(self, user_id: str) -> str:
        """
        Buat refresh token dengan TTL panjang.

        Args:
            user_id: ID user.

        Returns:
            JWT string.
        """
        data = {
            "sub": user_id,
            "iat": int(time.time()),
            "exp": int(time.time()) + self.refresh_ttl,
            "type": "refresh",
        }
        return self._encode(data)

    def verify(self, token: str) -> Optional[Dict]:
        """
        Verifikasi dan decode JWT token.

        Args:
            token: JWT string.

        Returns:
            Payload dict jika valid, None jika tidak valid atau expired.
        """
        try:
            payload = self._decode(token)

            # Cek expiry
            if payload.get("exp", 0) < time.time():
                logger.debug("Token expired")
                return None

            return payload

        except Exception as e:
            logger.debug(f"Token verification failed: {e}")
            return None

    def refresh(self, refresh_token: str) -> Optional[str]:
        """
        Buat access token baru dari refresh token.

        Args:
            refresh_token: Refresh token yang valid.

        Returns:
            Access token baru, atau None jika refresh token tidak valid.
        """
        payload = self.verify(refresh_token)
        if not payload or payload.get("type") != "refresh":
            return None

        return self.create_access_token({"sub": payload.get("sub")})

    def extract_user_id(self, token: str) -> Optional[str]:
        """Ambil user ID dari token tanpa verifikasi penuh."""
        try:
            payload = self._decode(token)
            return payload.get("sub")
        except Exception:
            return None

    # ==================== INTERNAL ====================

    def _encode(self, payload: Dict) -> str:
        """Encode payload ke JWT string."""
        header = {"alg": self.ALGORITHM, "typ": "JWT"}
        header_b64 = self._b64encode(json.dumps(header, separators=(",", ":")))
        payload_b64 = self._b64encode(json.dumps(payload, separators=(",", ":")))
        signing_input = f"{header_b64}.{payload_b64}"
        signature = self._sign(signing_input)
        return f"{signing_input}.{signature}"

    def _decode(self, token: str) -> Dict:
        """Decode dan verify JWT string."""
        parts = token.split(".")
        if len(parts) != 3:
            raise ValueError("Invalid JWT format")

        header_b64, payload_b64, signature = parts
        signing_input = f"{header_b64}.{payload_b64}"

        # Verify signature
        expected_sig = self._sign(signing_input)
        if not hmac.compare_digest(signature, expected_sig):
            raise ValueError("Invalid JWT signature")

        payload_json = self._b64decode(payload_b64)
        return json.loads(payload_json)

    def _sign(self, data: str) -> str:
        """Generate HMAC-SHA256 signature."""
        sig = hmac.new(
            self.secret.encode("utf-8"),
            data.encode("utf-8"),
            hashlib.sha256,
        ).digest()
        return self._b64encode(sig)

    @staticmethod
    def _b64encode(data) -> str:
        if isinstance(data, str):
            data = data.encode("utf-8")
        return urlsafe_b64encode(data).rstrip(b"=").decode("utf-8")

    @staticmethod
    def _b64decode(data: str) -> bytes:
        padding = 4 - len(data) % 4
        if padding != 4:
            data += "=" * padding
        return urlsafe_b64decode(data)
