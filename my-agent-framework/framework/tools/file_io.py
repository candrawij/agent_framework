"""
file_io.py — Baca / Tulis File Lokal

Tool untuk operasi file system: baca, tulis, list folder, cari file.
Dilengkapi sandbox path dan proteksi sistem.

Refactored dari saki_ai_assistant/src/agents/skills/filesystem.py
dengan generalisasi path mapping dan penghapusan hardcoded paths.
"""

import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .base_tool import BaseTool

logger = logging.getLogger("framework.tools.file_io")

# Folder sistem yang diblokir dari akses
_BLOCKED_PATHS = [
    "\\Windows\\", "\\System32\\", "\\Program Files\\",
    "\\ProgramData\\", "/etc/", "/usr/bin/", "/boot/",
]


def _is_blocked(path: str) -> bool:
    """Cek apakah path adalah folder sistem yang diblokir."""
    return any(blocked in str(path) for blocked in _BLOCKED_PATHS)


class ReadFileTool(BaseTool):
    """Baca konten file teks."""

    name = "read_file"
    description = "Baca konten file teks (txt, md, py, js, json, yaml, dll)"
    tags = ["file", "read"]

    @property
    def parameters(self) -> Dict:
        return {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path absolut atau relatif ke file",
                },
                "encoding": {
                    "type": "string",
                    "description": "Encoding file (default: utf-8)",
                    "default": "utf-8",
                },
                "max_chars": {
                    "type": "integer",
                    "description": "Batas karakter yang dibaca (default: 10000)",
                    "default": 10000,
                },
            },
            "required": ["path"],
        }

    def run(self, path: str, encoding: str = "utf-8", max_chars: int = 10000) -> str:
        file_path = Path(path).resolve()

        if _is_blocked(str(file_path)):
            return f"❌ Akses ke '{file_path}' diblokir oleh security policy"

        if not file_path.exists():
            return f"❌ File tidak ditemukan: {path}"

        if not file_path.is_file():
            return f"❌ Path ini adalah folder, bukan file: {path}"

        try:
            content = file_path.read_text(encoding=encoding)
            if len(content) > max_chars:
                content = content[:max_chars] + f"\n... [truncated, total {len(content)} chars]"
            return content
        except UnicodeDecodeError:
            return f"❌ File tidak bisa dibaca sebagai teks (mungkin binary): {path}"
        except PermissionError:
            return f"❌ Akses ditolak: {path}"


class WriteFileTool(BaseTool):
    """Tulis konten ke file teks."""

    name = "write_file"
    description = "Tulis atau buat file teks baru"
    tags = ["file", "write"]

    @property
    def parameters(self) -> Dict:
        return {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Path file tujuan"},
                "content": {"type": "string", "description": "Konten yang akan ditulis"},
                "mode": {
                    "type": "string",
                    "description": "'write' (timpa) atau 'append' (tambah di akhir)",
                    "enum": ["write", "append"],
                    "default": "write",
                },
                "encoding": {"type": "string", "default": "utf-8"},
            },
            "required": ["path", "content"],
        }

    def run(self, path: str, content: str, mode: str = "write", encoding: str = "utf-8") -> str:
        file_path = Path(path).resolve()

        if _is_blocked(str(file_path)):
            return f"❌ Akses ke '{file_path}' diblokir oleh security policy"

        try:
            file_path.parent.mkdir(parents=True, exist_ok=True)
            write_mode = "a" if mode == "append" else "w"
            file_path.write_text(content, encoding=encoding) if write_mode == "w" else \
                open(file_path, "a", encoding=encoding).write(content)
            return f"✅ File ditulis: {file_path} ({len(content)} karakter)"
        except PermissionError:
            return f"❌ Tidak ada izin untuk menulis ke: {path}"
        except Exception as e:
            return f"❌ Gagal menulis file: {type(e).__name__}: {e}"


class ListFolderTool(BaseTool):
    """Tampilkan isi folder."""

    name = "list_folder"
    description = "Tampilkan daftar file dan subfolder dalam sebuah folder"
    tags = ["file", "read"]

    @property
    def parameters(self) -> Dict:
        return {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Path folder yang akan dilihat"},
                "show_hidden": {
                    "type": "boolean",
                    "description": "Tampilkan file tersembunyi (awalan .)",
                    "default": False,
                },
                "max_items": {
                    "type": "integer",
                    "description": "Batas jumlah item yang ditampilkan",
                    "default": 50,
                },
            },
            "required": ["path"],
        }

    def run(self, path: str, show_hidden: bool = False, max_items: int = 50) -> str:
        folder_path = Path(path).resolve()

        if _is_blocked(str(folder_path)):
            return f"❌ Akses ke '{folder_path}' diblokir"

        if not folder_path.exists():
            return f"❌ Folder tidak ditemukan: {path}"

        if not folder_path.is_dir():
            return f"❌ Path ini adalah file, bukan folder: {path}"

        try:
            items = []
            for item in sorted(folder_path.iterdir()):
                if not show_hidden and item.name.startswith("."):
                    continue
                try:
                    stat = item.stat()
                    items.append({
                        "name": item.name,
                        "type": "folder" if item.is_dir() else "file",
                        "size_mb": round(stat.st_size / (1024 * 1024), 2) if item.is_file() else 0,
                        "modified": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M"),
                    })
                except OSError:
                    continue

            # Sort: folder dulu
            items.sort(key=lambda x: (x["type"] != "folder", x["name"].lower()))

            total = len(items)
            items = items[:max_items]

            lines = [f"📂 {folder_path} ({total} item)"]
            for item in items:
                icon = "📁" if item["type"] == "folder" else "📄"
                size_str = f" ({item['size_mb']} MB)" if item["size_mb"] > 0 else ""
                lines.append(f"  {icon} {item['name']}{size_str}  [{item['modified']}]")

            if total > max_items:
                lines.append(f"  ... dan {total - max_items} item lainnya")

            return "\n".join(lines)

        except PermissionError:
            return f"❌ Akses ditolak: {path}"


class SearchFilesTool(BaseTool):
    """Cari file berdasarkan nama di folder tertentu."""

    name = "search_files"
    description = "Cari file berdasarkan nama atau ekstensi dalam folder"
    tags = ["file", "search"]

    @property
    def parameters(self) -> Dict:
        return {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Kata kunci nama file"},
                "folder": {
                    "type": "string",
                    "description": "Folder pencarian (default: home dir)",
                },
                "extension": {
                    "type": "string",
                    "description": "Filter ekstensi (contoh: .py, .txt)",
                },
                "max_results": {
                    "type": "integer",
                    "description": "Batas hasil pencarian",
                    "default": 20,
                },
                "max_depth": {
                    "type": "integer",
                    "description": "Kedalaman rekursif maksimum",
                    "default": 5,
                },
            },
            "required": ["query"],
        }

    def run(
        self,
        query: str,
        folder: Optional[str] = None,
        extension: Optional[str] = None,
        max_results: int = 20,
        max_depth: int = 5,
    ) -> str:
        search_root = Path(folder).resolve() if folder else Path.home()

        if _is_blocked(str(search_root)):
            return f"❌ Folder pencarian diblokir: {search_root}"

        results: List[str] = []
        query_lower = query.lower()

        try:
            for root, dirs, files in os.walk(search_root):
                # Hitung kedalaman
                try:
                    depth = len(Path(root).relative_to(search_root).parts)
                except ValueError:
                    depth = 0
                if depth > max_depth:
                    dirs.clear()
                    continue

                # Skip hidden & system
                dirs[:] = [
                    d for d in dirs
                    if not d.startswith(".") and not d.startswith("__")
                    and not _is_blocked(os.path.join(root, d))
                ]

                for filename in files:
                    if query_lower in filename.lower():
                        if extension and not filename.endswith(extension):
                            continue
                        results.append(os.path.join(root, filename))
                        if len(results) >= max_results:
                            break

                if len(results) >= max_results:
                    break

        except PermissionError:
            pass

        if not results:
            return f"🔍 Tidak ditemukan file yang cocok dengan '{query}' di {search_root}"

        lines = [f"🔍 Ditemukan {len(results)} file:"]
        for r in results:
            lines.append(f"  📄 {r}")
        return "\n".join(lines)
