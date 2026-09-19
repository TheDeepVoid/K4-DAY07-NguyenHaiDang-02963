from __future__ import annotations

from typing import Any, Callable

from .chunking import _dot
from .embeddings import _mock_embed
from .models import Document
import math


class EmbeddingStore:
    """
    A vector store for text chunks.

    Tries to use ChromaDB if available; falls back to an in-memory store.
    The embedding_fn parameter allows injection of mock embeddings for tests.
    """

    def __init__(
        self,
        collection_name: str = "documents",
        embedding_fn: Callable[[str], list[float]] | None = None,
    ) -> None:
        self._embedding_fn = embedding_fn or _mock_embed
        self._collection_name = collection_name
        self._use_chroma = False
        self._store: list[dict[str, Any]] = []
        self._collection = None
        self._next_index = 0

        try:
            import chromadb  # noqa: F401

            # TODO: initialize chromadb client + collection
            self._use_chroma = True
        except Exception:
            self._use_chroma = False
            self._collection = None

    def _make_record(self, doc: Document) -> dict[str, Any]:
        embedding = self._embedding_fn(doc.content)
        return {
            "id": doc.id,
            "content": doc.content,
            "embedding": embedding,
            "metadata": dict(doc.metadata),
            "doc_id": doc.id,
        }

    def _search_records(self, query: str, records: list[dict[str, Any]], top_k: int) -> list[dict[str, Any]]:
        query_embedding = self._embedding_fn(query)
        scored: list[tuple[dict[str, Any], float]] = []
        for record in records:
            sim = _dot(query_embedding, record["embedding"]) / (
                math.sqrt(sum(x * x for x in query_embedding)) * math.sqrt(sum(x * x for x in record["embedding"]))
            ) if any(query_embedding) or any(record["embedding"]) else 0.0
            scored.append((record, sim))
        scored.sort(key=lambda x: x[1], reverse=True)
        return [
            {"id": r["id"], "content": r["content"], "score": sim, "metadata": r["metadata"]}
            for r, sim in scored[:top_k]
        ]

    def add_documents(self, docs: list[Document]) -> None:
        for doc in docs:
            record = self._make_record(doc)
            if self._use_chroma:
                # Use ChromaDB
                self._collection.add(
                    ids=[record["id"]],
                    documents=[record["content"]],
                    embeddings=[record["embedding"]],
                )
            else:
                # In-memory storage
                self._store.append(record)
                self._next_index += 1

    def search(self, query: str, top_k: int = 5) -> list[dict[str, Any]]:
        if self._use_chroma:
            # Use ChromaDB search
            results = self._collection.query(
                query_texts=[query],
                n_results=top_k,
            )
            docs = results.get("documents", [[]])[0] if results else []
            ids = results.get("ids", [[]])[0] if results else []
            metadatas = results.get("metadatas", [[]])[0] if results else []
            return [
                {"id": idx, "content": doc, "score": sim, "metadata": meta}
                for idx, doc, sim, meta in zip(ids, docs, sims, metadatas)
            ] if (sims := results.get("similarities", [[]])) else []
        else:
            # In-memory: compute similarities and return top_k
            query_embedding = self._embedding_fn(query)
            scored: list[tuple[dict[str, Any], float]] = []
            for record in self._store:
                sim = _dot(query_embedding, record["embedding"]) / (
                    math.sqrt(sum(x * x for x in query_embedding)) * math.sqrt(sum(x * x for x in record["embedding"]))
                ) if any(query_embedding) or any(record["embedding"]) else 0.0
                scored.append((record, sim))
            scored.sort(key=lambda x: x[1], reverse=True)
            return [
                {"id": r["id"], "content": r["content"], "score": sim, "metadata": r["metadata"]}
                for r, sim in scored[:top_k]
            ]

    def get_collection_size(self) -> int:
        if self._use_chroma:
            return len(self._collection.get()["ids"]) if self._collection else 0
        return len(self._store)

    def search_with_filter(self, query: str, top_k: int = 3, metadata_filter: dict = None) -> list[dict]:
        # Filter by metadata first
        if metadata_filter:
            filtered = [r for r in self._store if all(r["metadata"].get(k) == v for k, v in metadata_filter.items())]
        else:
            filtered = self._store
        if not filtered:
            return []
        query_embedding = self._embedding_fn(query)
        scored: list[tuple[dict[str, Any], float]] = []
        for record in filtered:
            sim = _dot(query_embedding, record["embedding"]) / (
                math.sqrt(sum(x * x for x in query_embedding)) * math.sqrt(sum(x * x for x in record["embedding"]))
            ) if any(query_embedding) or any(record["embedding"]) else 0.0
            scored.append((record, sim))
        scored.sort(key=lambda x: x[1], reverse=True)
        return [
            {"id": r["id"], "content": r["content"], "score": sim, "metadata": r["metadata"]}
            for r, sim in scored[:top_k]
        ]

    def delete_document(self, doc_id: str) -> bool:
        if self._use_chroma:
            # For ChromaDB, remove by doc_id metadata
            # This is a simplified approach - in practice ChromaDB has its own filtering
            self._collection.delete(where={"doc_id": doc_id})
            return True
        else:
            # In-memory: remove all chunks where id matches doc_id
            original_len = len(self._store)
            self._store = [r for r in self._store if r["id"] != doc_id]
            return len(self._store) < original_len
