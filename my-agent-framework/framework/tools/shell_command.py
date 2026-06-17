"""
shell_command.py — Eksekusi Shell Command dengan Sandbox

Tool untuk menjalankan perintah shell dengan:
- Blocklist commands berbahaya
- Timeout enforcement
- Output capture dan formatting
- Cross-platform support (Windows & Unix)

Refactored dari saki_ai_assistant/src/agents/skills/windows.py
dengan generalisasi lintas platform.
"""

import logging
import os
import platform
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from .base_tool import BaseTool

logger = logging.getLogger("framework.tools.shell_command")

# Commands yang diblokir karena berbahaya
_BLOCKED_COMMANDS = [
    "del /f", "del /s", "rd /s", "rmdir /s",
    "rm -rf", "rm -r",
    "format", "fdisk", "mkfs",
    "shutdown", "restart", "reboot",
    "reg delete", "regedit",
    "net user", "net localgroup",
    "cipher /w",
]


def _is_blocked(command: str) -> bool:
    """Cek apakah command termasuk yang diblokir."""
    cmd_lower = command.lower().strip()
    return any(blocked in cmd_lower for blocked in _BLOCKED_COMMANDS)


class RunCommandTool(BaseTool):
    """Eksekusi shell command dan kembalikan output."""

    name = "run_command"
    description = (
        "Jalankan perintah shell (cmd/bash) dan kembalikan output-nya. "
        "Commands berbahaya (delete, format, shutdown) diblokir."
    )
    tags = ["shell", "system"]

    def __init__(self, working_dir: Optional[str] = None, timeout: int = 30):
        self._working_dir = working_dir or str(Path.home())
        self._timeout = timeout

    @property
    def parameters(self) -> Dict:
        return {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "Perintah shell yang akan dijalankan",
                },
                "working_dir": {
                    "type": "string",
                    "description": "Working directory untuk perintah (opsional)",
                },
                "timeout": {
                    "type": "integer",
                    "description": "Timeout dalam detik (default: 30)",
                    "default": 30,
                },
            },
            "required": ["command"],
        }

    def run(
        self,
        command: str,
        working_dir: Optional[str] = None,
        timeout: Optional[int] = None,
    ) -> str:
        # Security check
        if _is_blocked(command):
            return f"❌ Command diblokir oleh security policy: '{command}'"

        timeout = timeout or self._timeout
        cwd = working_dir or self._working_dir

        logger.info(f"Running command: '{command}' in '{cwd}' (timeout={timeout}s)")

        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=cwd,
                encoding="utf-8",
                errors="replace",
            )

            output_parts = []
            if result.stdout and result.stdout.strip():
                output_parts.append(f"stdout:\n{result.stdout.strip()[:2000]}")
            if result.stderr and result.stderr.strip():
                output_parts.append(f"stderr:\n{result.stderr.strip()[:500]}")

            status = "✅" if result.returncode == 0 else "⚠️"
            header = f"{status} Command: `{command}` (returncode={result.returncode})"

            if output_parts:
                return header + "\n\n" + "\n\n".join(output_parts)
            return header + "\n(Tidak ada output)"

        except subprocess.TimeoutExpired:
            return f"⏰ Command timeout setelah {timeout}s: `{command}`"
        except FileNotFoundError:
            return f"❌ Command tidak ditemukan: `{command}`"
        except Exception as e:
            return f"❌ Error menjalankan command: {type(e).__name__}: {e}"


class GetSystemInfoTool(BaseTool):
    """Ambil informasi sistem (OS, CPU, RAM, dsb.)."""

    name = "get_system_info"
    description = "Dapatkan informasi sistem: OS, CPU, RAM, uptime, user"
    tags = ["system", "info"]

    @property
    def parameters(self) -> Dict:
        return {"type": "object", "properties": {}, "required": []}

    def run(self, **kwargs: Any) -> str:
        info: Dict[str, Any] = {
            "os": platform.system(),
            "os_version": platform.version(),
            "machine": platform.machine(),
            "processor": platform.processor() or "Unknown",
            "python": sys.version.split()[0],
            "hostname": platform.node(),
        }

        # User
        try:
            info["user"] = os.getlogin()
        except Exception:
            info["user"] = os.environ.get("USERNAME") or os.environ.get("USER") or "Unknown"

        # RAM dan CPU dengan psutil (opsional)
        try:
            import psutil
            mem = psutil.virtual_memory()
            info["ram_total_gb"] = round(mem.total / (1024 ** 3), 1)
            info["ram_used_percent"] = mem.percent
            info["cpu_count"] = psutil.cpu_count(logical=True)
            info["cpu_usage_percent"] = psutil.cpu_percent(interval=0.5)
            boot = psutil.boot_time()
            info["boot_time"] = datetime.fromtimestamp(boot).strftime("%Y-%m-%d %H:%M")
        except ImportError:
            info["cpu_count"] = os.cpu_count()

        lines = ["📊 Informasi Sistem"]
        lines.append(f"  OS       : {info['os']} {info.get('os_version', '')[:50]}")
        lines.append(f"  Machine  : {info['machine']}")
        lines.append(f"  Processor: {info['processor'][:60]}")
        lines.append(f"  Python   : {info['python']}")
        lines.append(f"  User     : {info['user']}")
        lines.append(f"  Hostname : {info['hostname']}")
        if "ram_total_gb" in info:
            lines.append(f"  RAM      : {info['ram_total_gb']} GB ({info['ram_used_percent']}% used)")
        if "cpu_count" in info:
            lines.append(f"  CPU      : {info['cpu_count']} cores")
        if "cpu_usage_percent" in info:
            lines.append(f"  CPU Load : {info['cpu_usage_percent']}%")
        if "boot_time" in info:
            lines.append(f"  Boot     : {info['boot_time']}")

        return "\n".join(lines)


class ScreenshotTool(BaseTool):
    """Ambil screenshot layar dan simpan ke file."""

    name = "take_screenshot"
    description = "Ambil screenshot layar saat ini dan simpan ke file"
    tags = ["system", "screen"]

    @property
    def parameters(self) -> Dict:
        return {
            "type": "object",
            "properties": {
                "save_path": {
                    "type": "string",
                    "description": "Path folder untuk menyimpan screenshot (default: home/screenshots)",
                },
            },
            "required": [],
        }

    def run(self, save_path: Optional[str] = None) -> str:
        if save_path:
            folder = Path(save_path)
        else:
            folder = Path.home() / "screenshots"

        folder.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = folder / f"screenshot_{timestamp}.png"

        # Coba pyautogui
        try:
            import pyautogui
            pyautogui.screenshot(str(filepath))
            return f"✅ Screenshot disimpan: {filepath}"
        except ImportError:
            pass

        # Fallback: PIL
        try:
            from PIL import ImageGrab
            img = ImageGrab.grab()
            img.save(str(filepath))
            return f"✅ Screenshot disimpan: {filepath}"
        except ImportError:
            pass

        # Fallback: PowerShell (Windows)
        if platform.system() == "Windows":
            try:
                ps_cmd = (
                    "Add-Type -AssemblyName System.Windows.Forms; "
                    "[System.Windows.Forms.SendKeys]::SendWait('%{PRTSC}')"
                )
                subprocess.run(["powershell", "-Command", ps_cmd], capture_output=True)
                return "📸 Screenshot disalin ke clipboard (install pyautogui untuk save otomatis)"
            except Exception as e:
                return f"❌ Screenshot gagal: {e}"

        return "❌ Screenshot tidak didukung di sistem ini (install pyautogui atau Pillow)"
