"""
base_tool.py — Abstract Tool Interface

Semua tool dalam framework harus mewarisi BaseTool.
Menyediakan interface standar, schema generation untuk LLM,
dan logging eksekusi.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class BaseTool(ABC):
    """
    Abstract base class untuk semua tool.

    Setiap tool wajib mengimplementasikan:
    - name (property) → str
    - description (property) → str
    - parameters (property) → Dict  [JSON Schema]
    - run(**kwargs) → Any

    Framework akan memanggil run() dengan argumen dari LLM.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Nama tool (unik, snake_case). Digunakan LLM untuk memanggil tool."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Deskripsi singkat apa yang dilakukan tool ini. Digunakan LLM."""
        pass

    @property
    def parameters(self) -> Dict:
        """
        JSON Schema parameter tool untuk LLM tool calling.

        Override ini untuk mendefinisikan parameter yang diterima.
        Default: tidak ada parameter.
        """
        return {"type": "object", "properties": {}, "required": []}

    @property
    def tags(self) -> List[str]:
        """Label opsional untuk kategorisasi tool."""
        return []

    @property
    def enabled(self) -> bool:
        """Apakah tool ini aktif."""
        return True

    @abstractmethod
    def run(self, **kwargs: Any) -> Any:
        """
        Eksekusi tool dengan argumen yang diberikan.

        Args:
            **kwargs: Argumen sesuai schema `parameters`.

        Returns:
            Hasil eksekusi. Akan dikonversi ke string oleh Observer.
        """
        pass

    def get_schema(self) -> Dict:
        """
        Generate schema tool dalam format OpenAI function calling.
        Digunakan oleh model adapter.
        """
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }

    def get_info(self) -> Dict:
        """Info ringkas tool untuk registry/API."""
        return {
            "name": self.name,
            "description": self.description,
            "tags": self.tags,
            "enabled": self.enabled,
            "parameters": list(self.parameters.get("properties", {}).keys()),
        }

    def validate_input(self, kwargs: Dict) -> Optional[str]:
        """
        Validasi input sebelum dijalankan.

        Returns:
            None jika valid, string error jika tidak valid.
        """
        required = self.parameters.get("required", [])
        for req in required:
            if req not in kwargs:
                return f"Parameter wajib '{req}' tidak ditemukan"
        return None

    def safe_run(self, **kwargs: Any) -> Dict:
        """
        Jalankan tool dengan validasi dan error handling.

        Returns:
            {"success": bool, "output": Any, "error": Optional[str]}
        """
        # Validasi
        error = self.validate_input(kwargs)
        if error:
            return {"success": False, "output": None, "error": error}

        # Eksekusi
        try:
            output = self.run(**kwargs)
            return {"success": True, "output": output, "error": None}
        except Exception as e:
            return {"success": False, "output": None, "error": f"{type(e).__name__}: {e}"}

    def __repr__(self) -> str:
        return f"<Tool name={self.name!r} enabled={self.enabled}>"

    def __str__(self) -> str:
        return f"{self.name}: {self.description}"
