"""
http_request.py — HTTP Request Tool

Tool untuk melakukan HTTP requests ke API atau URL eksternal.
"""

import json
import logging
from typing import Any, Dict, Optional

from .base_tool import BaseTool

logger = logging.getLogger("framework.tools.http_request")


class HttpRequestTool(BaseTool):
    """Lakukan HTTP request ke URL/API dan kembalikan response."""

    name = "http_request"
    description = (
        "Kirim HTTP request (GET/POST/PUT/DELETE) ke URL atau API endpoint "
        "dan kembalikan response body."
    )
    tags = ["http", "api", "web"]

    def __init__(self, timeout: int = 15, allowed_domains: Optional[list] = None):
        self._timeout = timeout
        self._allowed_domains = allowed_domains  # None = semua domain diizinkan

    @property
    def parameters(self) -> Dict:
        return {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "URL tujuan (harus https://)",
                },
                "method": {
                    "type": "string",
                    "description": "HTTP method: GET, POST, PUT, DELETE",
                    "enum": ["GET", "POST", "PUT", "DELETE", "PATCH"],
                    "default": "GET",
                },
                "headers": {
                    "type": "object",
                    "description": "HTTP headers opsional",
                },
                "body": {
                    "type": "object",
                    "description": "Request body untuk POST/PUT (JSON)",
                },
                "timeout": {
                    "type": "integer",
                    "description": "Timeout dalam detik",
                    "default": 15,
                },
            },
            "required": ["url"],
        }

    def run(
        self,
        url: str,
        method: str = "GET",
        headers: Optional[Dict] = None,
        body: Optional[Dict] = None,
        timeout: Optional[int] = None,
    ) -> str:
        # Validasi URL
        if not url.startswith(("http://", "https://")):
            return f"❌ URL tidak valid: harus diawali http:// atau https://"

        # Cek domain whitelist
        if self._allowed_domains:
            from urllib.parse import urlparse
            domain = urlparse(url).netloc
            if not any(ad in domain for ad in self._allowed_domains):
                return f"❌ Domain '{domain}' tidak diizinkan"

        timeout = timeout or self._timeout
        headers = headers or {}
        method = method.upper()

        logger.info(f"HTTP {method}: {url}")

        try:
            import httpx

            with httpx.Client(timeout=timeout) as client:
                if method == "GET":
                    resp = client.get(url, headers=headers)
                elif method == "POST":
                    resp = client.post(url, json=body, headers=headers)
                elif method == "PUT":
                    resp = client.put(url, json=body, headers=headers)
                elif method == "DELETE":
                    resp = client.delete(url, headers=headers)
                elif method == "PATCH":
                    resp = client.patch(url, json=body, headers=headers)
                else:
                    return f"❌ Method tidak dikenal: {method}"

            status_icon = "✅" if resp.status_code < 400 else "⚠️"
            content_type = resp.headers.get("content-type", "")

            # Parse response body
            body_str = ""
            if "json" in content_type:
                try:
                    body_str = json.dumps(resp.json(), ensure_ascii=False, indent=2)[:3000]
                except Exception:
                    body_str = resp.text[:3000]
            else:
                body_str = resp.text[:3000]

            return (
                f"{status_icon} {method} {url}\n"
                f"Status: {resp.status_code}\n"
                f"Content-Type: {content_type}\n"
                f"\n{body_str}"
            )

        except ImportError:
            return "❌ Package 'httpx' tidak terinstall. Jalankan: pip install httpx"
        except Exception as e:
            logger.error(f"HTTP request failed: {e}")
            return f"❌ Request gagal: {type(e).__name__}: {e}"


class CodeExecutorTool(BaseTool):
    """
    Eksekusi kode Python dalam sandbox terbatas.

    ⚠️  PERINGATAN: Tool ini mengeksekusi kode arbitrer.
    Gunakan hanya dalam lingkungan terpercaya atau dengan sandboxing.
    """

    name = "execute_python"
    description = (
        "Eksekusi kode Python dan kembalikan output. "
        "Hanya untuk kalkulasi dan transformasi data sederhana."
    )
    tags = ["code", "python", "compute"]

    @property
    def parameters(self) -> Dict:
        return {
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "Kode Python yang akan dieksekusi",
                },
                "timeout": {
                    "type": "integer",
                    "description": "Batas waktu eksekusi dalam detik (default: 10)",
                    "default": 10,
                },
            },
            "required": ["code"],
        }

    def run(self, code: str, timeout: int = 10) -> str:
        import io
        import sys
        import threading

        # Batasi import berbahaya
        blocked_imports = ["os", "subprocess", "shutil", "socket", "sys"]
        code_lower = code.lower()
        for blocked in blocked_imports:
            if f"import {blocked}" in code_lower or f"from {blocked}" in code_lower:
                return f"❌ Import '{blocked}' diblokir di sandbox ini"

        output_buffer = io.StringIO()
        error_buffer = io.StringIO()
        result_container: Dict = {"done": False, "error": None}

        def execute():
            try:
                # Redirect stdout
                old_stdout = sys.stdout
                sys.stdout = output_buffer
                try:
                    exec(code, {"__builtins__": {"print": print, "range": range,
                                                  "len": len, "str": str, "int": int,
                                                  "float": float, "list": list,
                                                  "dict": dict, "set": set,
                                                  "sorted": sorted, "sum": sum,
                                                  "max": max, "min": min}})
                finally:
                    sys.stdout = old_stdout
            except Exception as e:
                result_container["error"] = f"{type(e).__name__}: {e}"
            result_container["done"] = True

        thread = threading.Thread(target=execute, daemon=True)
        thread.start()
        thread.join(timeout=timeout)

        if not result_container["done"]:
            return f"⏰ Eksekusi timeout setelah {timeout}s"

        if result_container["error"]:
            return f"❌ Error:\n{result_container['error']}"

        output = output_buffer.getvalue()
        if not output.strip():
            return "✅ Kode dieksekusi (tidak ada output)"
        return f"✅ Output:\n{output[:2000]}"
