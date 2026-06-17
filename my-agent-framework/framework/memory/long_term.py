"""
long_term.py — Long-Term Memory (Vector Store)

Menyimpan fakta, dokumen, dan pengetahuan jangka panjang
menggunakan vector database untuk semantic search.

Backend didukung:
- "memory" (in-memory, tanpa persistence, untuk testing)
- "chromadb" (lokal, persisten)
- "qdrant" (production-grade, self-hosted atau cloud)
- "faiss" (lokal, fast similarity search)
"""

import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("framework.memory.long_term")


class LongTermMemory:
    """
    Long-term semantic memory menggunakan vector store.

    Mendukung pluggable backend via parameter `backend`.
    Default: in-memory (tanpa persistence, cocok untuk development).
    """

    def __init__(
        self,
        backend: str = "memory",
        collection_name: str = "agent_memory",
        embedding_model: Optional[Any] = None,
        persist_dir: Optional[str] = None,
        **backend_kwargs: Any,
    ):
        self.backend = backend
        self.collection_name = collection_name
        self._persist_dir = persist_dir
        self._embedding_model = embedding_model
        self._store: List[Dict] = []  # Fallback in-memory store
        self._client: Optional[Any] = None
        self._collection: Optional[Any] = None
        self._init_backend(**backend_kwargs)

    def _init_backend(self, **kwargs):
        """Inisialisasi backend sesuai konfigurasi."""
        if self.backend == "memory":
            logger.info("LongTermMemory: using in-memory backend (no persistence)")
        elif self.backend == "chromadb":
            self._init_chromadb(**kwargs)
        elif self.backend == "qdrant":
            self._init_qdrant(**kwargs)
        else:
            logger.warning(f"Unknown backend '{self.backend}', falling back to in-memory")

    def _init_chromadb(self, **kwargs):
        """Inisialisasi ChromaDB."""
        try:
            import chromadb
            if self._persist_dir:
                self._client = chromadb.PersistentClient(path=self._persist_dir)
            else:
                self._client = chromadb.Client()
            self._collection = self._client.get_or_create_collection(
                name=self.collection_name,
            )
            logger.info(f"ChromaDB initialized: collection='{self.collection_name}'")
        except ImportError:
            logger.warning("ChromaDB tidak terinstall. Gunakan: pip install chromadb")
            self.backend = "memory"
        except Exception as e:
            logger.error(f"ChromaDB init failed: {e}. Falling back to in-memory")
            self.backend = "memory"

    def _init_qdrant(self, host: str = "localhost", port: int = 6333, **kwargs):
        """Inisialisasi Qdrant."""
        try:
            from qdrant_client import QdrantClient
            from qdrant_client.http.models import Distance, VectorParams

            self._client = QdrantClient(host=host, port=port)
            # TODO: Create collection jika belum ada
            logger.info(f"Qdrant initialized: {host}:{port}")
        except ImportError:
            logger.warning("Qdrant client tidak terinstall. Gunakan: pip install qdrant-client")
            self.backend = "memory"
        except Exception as e:
            logger.error(f"Qdrant init failed: {e}. Falling back to in-memory")
            self.backend = "memory"

    # ==================== ADD ====================

    def add(self, content: str, metadata: Optional[Dict] = None) -> str:
        """
        Simpan teks ke long-term memory.

        Args:
            content: Teks yang akan disimpan.
            metadata: Metadata tambahan (source, timestamp, tags, dll).

        Returns:
            ID entry yang disimpan.
        """
        entry_id = str(uuid.uuid4())[:8]
        metadata = metadata or {}
        metadata["timestamp"] = datetime.now().isoformat()

        if self.backend == "chromadb" and self._collection:
            try:
                self._collection.add(
                    ids=[entry_id],
                    documents=[content],
                    metadatas=[metadata],
                )
                logger.debug(f"Added to ChromaDB: id={entry_id}")
                return entry_id
            except Exception as e:
                logger.error(f"ChromaDB add failed: {e}")

        # Fallback in-memory
        self._store.append({
            "id": entry_id,
            "content": content,
            "metadata": metadata,
        })
        return entry_id

    # ==================== SEARCH ====================

    def search(self, query: str, top_k: int = 5) -> List[str]:
        """
        Cari konten yang semantically mirip dengan query.

        Args:
            query: Query pencarian.
            top_k: Jumlah hasil maksimum.

        Returns:
            List konten yang relevan.
        """
        if self.backend == "chromadb" and self._collection:
            try:
                results = self._collection.query(
                    query_texts=[query],
                    n_results=min(top_k, self._collection.count()),
                )
                docs = results.get("documents", [[]])[0]
                return docs
            except Exception as e:
                logger.error(f"ChromaDB search failed: {e}")

        # Fallback: simple keyword search
        query_lower = query.lower()
        scored: List[Tuple[float, str]] = []

        for item in self._store:
            content = item.get("content", "")
            # Hitung keyword overlap sederhana
            words_q = set(query_lower.split())
            words_c = set(content.lower().split())
            overlap = len(words_q & words_c)
            if overlap > 0:
                scored.append((overlap, content))

        scored.sort(key=lambda x: -x[0])
        return [content for _, content in scored[:top_k]]

    def search_with_metadata(self, query: str, top_k: int = 5) -> List[Dict]:
        """Search dan kembalikan beserta metadata."""
        if self.backend == "chromadb" and self._collection:
            try:
                results = self._collection.query(
                    query_texts=[query],
                    n_results=min(top_k, max(1, self._collection.count())),
                    include=["documents", "metadatas", "distances"],
                )
                output = []
                docs = results.get("documents", [[]])[0]
                metas = results.get("metadatas", [[]])[0]
                dists = results.get("distances", [[]])[0]
                for doc, meta, dist in zip(docs, metas, dists):
                    output.append({"content": doc, "metadata": meta, "distance": dist})
                return output
            except Exception as e:
                logger.error(f"ChromaDB search_with_metadata failed: {e}")

        # Fallback in-memory
        results = self.search(query, top_k)
        return [{"content": r, "metadata": {}, "distance": 0.0} for r in results]

    # ==================== MANAGE ====================

    def delete(self, entry_id: str) -> bool:
        """Hapus entry berdasarkan ID."""
        if self.backend == "chromadb" and self._collection:
            try:
                self._collection.delete(ids=[entry_id])
                return True
            except Exception as e:
                logger.error(f"ChromaDB delete failed: {e}")

        before = len(self._store)
        self._store = [item for item in self._store if item.get("id") != entry_id]
        return len(self._store) < before

    def clear(self):
        """Bersihkan semua entri."""
        self._store.clear()
        if self.backend == "chromadb" and self._collection:
            try:
                self._collection.delete(where={"timestamp": {"$gt": "0"}})
            except Exception:
                pass
        logger.warning(f"LongTermMemory '{self.collection_name}' cleared")

    def size(self) -> int:
        """Jumlah entri tersimpan."""
        if self.backend == "chromadb" and self._collection:
            try:
                return self._collection.count()
            except Exception:
                pass
        return len(self._store)

    def __repr__(self) -> str:
        return f"<LongTermMemory backend={self.backend!r} size={self.size()}>"
