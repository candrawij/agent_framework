"""
datetime_tool.py — Waktu dan Tanggal Sekarang

Tool untuk mendapatkan informasi waktu aktual.
Agent tidak bisa mengetahui waktu real-time tanpa tool ini.
"""

import logging
from datetime import datetime, timezone
from typing import Dict
from zoneinfo import ZoneInfo, available_timezones

from .base_tool import BaseTool

logger = logging.getLogger("framework.tools.datetime_tool")


class DatetimeTool(BaseTool):
    """Dapatkan waktu dan tanggal aktual."""

    name = "get_datetime"
    description = (
        "Dapatkan waktu dan tanggal sekarang secara akurat. "
        "Gunakan tool ini setiap kali user bertanya tentang waktu, tanggal, hari, bulan, atau tahun saat ini."
    )
    tags = ["time", "datetime", "utility"]

    @property
    def parameters(self) -> Dict:
        return {
            "type": "object",
            "properties": {
                "timezone": {
                    "type": "string",
                    "description": "Timezone IANA (misal: 'Asia/Jakarta', 'UTC', 'America/New_York'). Default: Asia/Jakarta",
                    "default": "Asia/Jakarta",
                },
                "format": {
                    "type": "string",
                    "description": "Format output: 'full' (lengkap), 'date' (tanggal saja), 'time' (jam saja), 'iso' (ISO 8601)",
                    "enum": ["full", "date", "time", "iso"],
                    "default": "full",
                },
            },
            "required": [],
        }

    def run(self, timezone: str = "Asia/Jakarta", format: str = "full") -> str:
        try:
            tz = ZoneInfo(timezone)
        except Exception:
            tz = ZoneInfo("Asia/Jakarta")
            timezone = "Asia/Jakarta"

        now = datetime.now(tz)

        # Format hari dalam Bahasa Indonesia
        days_id = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]
        months_id = [
            "Januari", "Februari", "Maret", "April", "Mei", "Juni",
            "Juli", "Agustus", "September", "Oktober", "November", "Desember"
        ]
        day_name = days_id[now.weekday()]
        month_name = months_id[now.month - 1]

        if format == "iso":
            return now.isoformat()
        elif format == "date":
            return f"{day_name}, {now.day} {month_name} {now.year}"
        elif format == "time":
            return now.strftime("%H:%M:%S") + f" {timezone}"
        else:  # full
            return (
                f"{day_name}, {now.day} {month_name} {now.year} "
                f"pukul {now.strftime('%H:%M:%S')} {timezone}"
            )
