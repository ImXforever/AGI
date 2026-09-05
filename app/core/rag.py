"""RAG — document indexing, chunking, and vector search with numpy cosine similarity."""

from __future__ import annotations

import hashlib
import re
import time
from typing import Any

from app.logging_setup import get_logger

log = get_logger("app.core.rag")

_documents: list[dict[str, Any]] = []
_embeddings: list[list[float]] = []
_index_ready = False

_CHUNK_SIZE = 512
_CHUNK_OVERLAP = 64


def chunk_text(
    text: str, *, chunk_size: int = _CHUNK_SIZE, overlap: int = _CHUNK_OVERLAP
) -> list[str]:
    """Split text into overlapping chunks suitable for embedding.

    Respects paragraph and sentence boundaries when possible.
    """
    text = text.strip()
    if not text:
        return []

    paragraphs = re.split(r"\n{2,}", text)
    chunks: list[str] = []
    current = ""

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue

        if len(current) + len(para) + 1 <= chunk_size:
            current = f"{current}\n{para}" if current else para
        else:
            if current:
                chunks.append(current)
                if overlap > 0 and len(current) > overlap:
                    current = current[-overlap:] + "\n" + para
                else:
                    current = para
            else:
                sentences = re.split(r"(?<=[.!?؟])\s+", para)
                current = ""
                for sentence in sentences:
                    if len(current) + len(sentence) + 1 <= chunk_size:
                        current = f"{current} {sentence}" if current else sentence
                    else:
                        if current:
                            chunks.append(current)
                        current = sentence

    if current.strip():
        chunks.append(current.strip())

    return chunks


def _simple_embed(text: str) -> list[float]:
    """Deterministic character-frequency embedding (dimension 64).

    This is a lightweight embedding that requires no external model.
    For production, replace with a real embedding model call.
    """
    dim = 64
    vec = [0.0] * dim
    for i, ch in enumerate(text.lower()):
        vec[ord(ch) % dim] += 1.0
        vec[(ord(ch) * 7 + i) % dim] += 0.5
        vec[(ord(ch) * 13 + i * 3) % dim] += 0.25

    norm = sum(v * v for v in vec) ** 0.5
    if norm > 0:
        vec = [v / norm for v in vec]
    return vec


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity between two vectors."""
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(x * x for x in b) ** 0.5
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def _doc_id(text: str, source: str = "") -> str:
    """Generate a deterministic document ID for deduplication."""
    h = hashlib.sha256(f"{source}:{text[:500]}".encode()).hexdigest()[:16]
    return h


async def index_documents(
    documents: list[dict[str, Any]],
    *,
    deduplicate: bool = True,
) -> int:
    """Index documents into the in-memory vector store.

    Each document dict should have at minimum a ``text`` field.
    Optional: ``source``, ``metadata``.

    Returns the number of new chunks indexed.
    """
    global _index_ready
    t0 = time.perf_counter()
    indexed = 0

    for doc in documents:
        text = doc.get("text", "").strip()
        if not text:
            continue

        source = doc.get("source", "")
        metadata = doc.get("metadata", {})

        chunks = chunk_text(text)
        for chunk in chunks:
            doc_id = _doc_id(chunk, source)
            if deduplicate:
                existing = any(d.get("doc_id") == doc_id for d in _documents)
                if existing:
                    continue

            embedding = _simple_embed(chunk)
            _documents.append(
                {
                    "doc_id": doc_id,
                    "text": chunk,
                    "source": source,
                    "metadata": metadata,
                }
            )
            _embeddings.append(embedding)
            indexed += 1

    _index_ready = len(_documents) > 0
    latency_ms = round((time.perf_counter() - t0) * 1000, 1)
    log.info(
        "rag_indexed",
        extra={
            "action": "index_documents",
            "indexed": indexed,
            "total_docs": len(_documents),
            "latency_ms": latency_ms,
        },
    )
    return indexed


async def search_similar(
    query: str,
    *,
    top_k: int = 5,
    threshold: float = 0.3,
    source_filter: str | None = None,
) -> list[dict[str, Any]]:
    """Search the vector store for documents similar to the query.

    Returns a list of results sorted by similarity (descending), each with
    ``text``, ``score``, ``source``, and ``metadata`` fields.
    """
    if not _index_ready or not _documents:
        return []

    t0 = time.perf_counter()
    query_embedding = _simple_embed(query)

    scored: list[tuple[float, int]] = []
    for i, emb in enumerate(_embeddings):
        sim = _cosine_similarity(query_embedding, emb)
        if sim >= threshold:
            scored.append((sim, i))

    scored.sort(key=lambda x: x[0], reverse=True)
    results: list[dict[str, Any]] = []
    for score, idx in scored[:top_k]:
        doc = _documents[idx]
        if source_filter and doc.get("source") != source_filter:
            continue
        results.append(
            {
                "text": doc["text"],
                "score": round(score, 4),
                "source": doc.get("source", ""),
                "metadata": doc.get("metadata", {}),
            }
        )

    latency_ms = round((time.perf_counter() - t0) * 1000, 1)
    log.debug(
        "rag_search",
        extra={
            "action": "search_similar",
            "query_len": len(query),
            "results": len(results),
            "latency_ms": latency_ms,
        },
    )
    return results


def clear_index() -> None:
    """Clear the entire in-memory vector store."""
    global _documents, _embeddings, _index_ready
    _documents.clear()
    _embeddings.clear()
    _index_ready = False
    log.info("rag_cleared", extra={"action": "clear_index"})


def index_stats() -> dict[str, Any]:
    """Return statistics about the current index."""
    return {
        "total_documents": len(_documents),
        "total_embeddings": len(_embeddings),
        "ready": _index_ready,
    }
