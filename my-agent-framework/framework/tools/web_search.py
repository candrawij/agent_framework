"""
web_search.py — Web Search Tool

Tool untuk pencarian web menggunakan berbagai provider:
DuckDuckGo (default, tanpa API key), SerpAPI, atau Tavily.
"""

import logging
from typing import Any, Dict, List, Optional

from .base_tool import BaseTool

logger = logging.getLogger("framework.tools.web_search")


class WebSearchTool(BaseTool):
    """
    Lakukan pencarian web dan kembalikan hasil ringkas.

    Mendukung backend:
    - "duckduckgo" (default, gratis, tanpa API key)
    - "serpapi"    (butuh SERPAPI_KEY di env)
    - "tavily"     (butuh TAVILY_API_KEY di env)
    """

    name = "web_search"
    description = (
        "Cari informasi di internet. Gunakan saat butuh informasi terkini "
        "atau fakta yang tidak ada di memory."
    )
    tags = ["search", "web", "internet"]

    def __init__(self, backend: str = "duckduckgo", max_results: int = 5):
        self._backend = backend
        self._max_results = max_results

    @property
    def parameters(self) -> Dict:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Query pencarian dalam bahasa natural",
                },
                "max_results": {
                    "type": "integer",
                    "description": "Jumlah hasil maksimum (default: 5)",
                    "default": 5,
                },
            },
            "required": ["query"],
        }

    def run(self, query: str, max_results: Optional[int] = None) -> str:
        max_results = max_results or self._max_results
        logger.info(f"WebSearch [{self._backend}]: '{query}' (max={max_results})")

        if self._backend == "duckduckgo":
            return self._search_duckduckgo(query, max_results)
        elif self._backend == "serpapi":
            return self._search_serpapi(query, max_results)
        elif self._backend == "tavily":
            return self._search_tavily(query, max_results)
        else:
            return f"❌ Backend pencarian tidak dikenal: {self._backend}"

    def _search_duckduckgo(self, query: str, max_results: int) -> str:
        """Pencarian menggunakan DuckDuckGo (gratis, tanpa API key)."""
        try:
            from duckduckgo_search import DDGS
            results: List[Dict] = []
            with DDGS() as ddgs:
                for r in ddgs.text(query, max_results=max_results):
                    results.append(r)

            if not results:
                return f"🔍 Tidak ditemukan hasil untuk: '{query}'"

            lines = [f"🔍 Hasil pencarian: '{query}'\n"]
            for i, r in enumerate(results, 1):
                title = r.get("title", "No title")
                snippet = r.get("body", r.get("snippet", ""))[:300]
                url = r.get("href", r.get("link", ""))
                lines.append(f"{i}. **{title}**")
                if snippet:
                    lines.append(f"   {snippet}")
                if url:
                    lines.append(f"   🔗 {url}")
                lines.append("")

            return "\n".join(lines)

        except ImportError:
            return (
                "❌ Package 'duckduckgo_search' tidak terinstall. "
                "Jalankan: pip install duckduckgo-search"
            )
        except Exception as e:
            logger.error(f"DuckDuckGo search failed: {e}")
            return f"❌ Pencarian gagal: {type(e).__name__}: {e}"

    def _search_serpapi(self, query: str, max_results: int) -> str:
        """Pencarian menggunakan SerpAPI."""
        import os
        api_key = os.getenv("SERPAPI_KEY")
        if not api_key:
            return "❌ SERPAPI_KEY tidak ditemukan di environment variables"

        try:
            import httpx
            response = httpx.get(
                "https://serpapi.com/search",
                params={"q": query, "api_key": api_key, "num": max_results},
                timeout=10,
            )
            data = response.json()
            results = data.get("organic_results", [])

            if not results:
                return f"🔍 Tidak ditemukan hasil untuk: '{query}'"

            lines = [f"🔍 Hasil pencarian: '{query}'\n"]
            for i, r in enumerate(results[:max_results], 1):
                lines.append(f"{i}. **{r.get('title', '')}**")
                lines.append(f"   {r.get('snippet', '')[:300]}")
                lines.append(f"   🔗 {r.get('link', '')}")
                lines.append("")

            return "\n".join(lines)

        except Exception as e:
            return f"❌ SerpAPI search failed: {type(e).__name__}: {e}"

    def _search_tavily(self, query: str, max_results: int) -> str:
        """Pencarian menggunakan Tavily AI Search."""
        import os
        api_key = os.getenv("TAVILY_API_KEY")
        if not api_key:
            return "❌ TAVILY_API_KEY tidak ditemukan di environment variables"

        try:
            import httpx
            response = httpx.post(
                "https://api.tavily.com/search",
                json={"query": query, "max_results": max_results, "api_key": api_key},
                timeout=15,
            )
            data = response.json()
            results = data.get("results", [])

            if not results:
                return f"🔍 Tidak ditemukan hasil untuk: '{query}'"

            lines = [f"🔍 Hasil pencarian: '{query}'\n"]
            for i, r in enumerate(results, 1):
                lines.append(f"{i}. **{r.get('title', '')}**")
                lines.append(f"   {r.get('content', '')[:300]}")
                lines.append(f"   🔗 {r.get('url', '')}")
                lines.append("")

            return "\n".join(lines)

        except Exception as e:
            return f"❌ Tavily search failed: {type(e).__name__}: {e}"
