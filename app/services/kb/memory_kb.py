"""In-memory knowledge base for curriculum, policy, and topic content with simple search."""

from typing import Any

# Document type constants for syllabus/admin/topic content
DOC_TYPE_SYLLABUS = "syllabus"
DOC_TYPE_ADMIN = "admin"
DOC_TYPE_TOPIC = "topic"


class InMemoryKnowledgeBase:
    """
    Basic knowledge base: store documents by id and type, search by keyword in content.
    For Phase 1 uses in-memory storage; can be replaced with app/services/db or vector later.
    """

    def __init__(self) -> None:
        self._docs: dict[str, dict[str, Any]] = {}  # id -> {type, content, metadata}
        self._by_type: dict[str, list[str]] = {
            DOC_TYPE_SYLLABUS: [],
            DOC_TYPE_ADMIN: [],
            DOC_TYPE_TOPIC: [],
        }

    def add_document(
        self,
        doc_id: str,
        doc_type: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Add or replace a document. doc_type should be syllabus, admin, or topic."""
        self._docs[doc_id] = {
            "type": doc_type,
            "content": content,
            "metadata": metadata or {},
        }
        if doc_type not in self._by_type:
            self._by_type[doc_type] = []
        if doc_id not in self._by_type[doc_type]:
            self._by_type[doc_type].append(doc_id)

    def get(self, doc_id: str) -> dict[str, Any] | None:
        """Return document by id or None."""
        return self._docs.get(doc_id)

    def search(self, query: str, doc_type: str | None = None) -> list[dict[str, Any]]:
        """
        Simple keyword search in document content. If doc_type is set, limit to that type.
        Returns list of matching documents (id, type, content, metadata).
        """
        if not query or not query.strip():
            return []
        q = query.strip().lower()
        ids = (
            self._by_type.get(doc_type, [])
            if doc_type
            else list(self._docs.keys())
        )
        results = []
        for doc_id in ids:
            doc = self._docs.get(doc_id)
            if not doc or q not in (doc.get("content") or "").lower():
                continue
            results.append(
                {
                    "id": doc_id,
                    "type": doc.get("type", ""),
                    "content": doc.get("content", ""),
                    "metadata": doc.get("metadata", {}),
                }
            )
        return results

    def search_by_type(self, doc_type: str, query: str) -> list[dict[str, Any]]:
        """Search only within documents of the given type."""
        return self.search(query, doc_type=doc_type)
