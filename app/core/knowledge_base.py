"""Persistent, versioned company knowledge base for v0.3.

The v0.2 RAG index is intentionally kept as the search engine. This module
adds a governed document boundary: only valid, approved documents are loaded,
and result visibility is filtered by sensitivity before an answer can use it.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from app.core import rag
from app.core.security_stack import inspect_data

_ALLOWED_SENSITIVITY = {"public": 0, "internal": 1, "confidential": 2}


class KnowledgeDocumentError(ValueError):
    """Raised for an invalid or unapproved knowledge document."""


@dataclass(frozen=True)
class KnowledgeDocument:
    title: str
    version: int
    status: str
    sensitivity: str
    source: str
    text: str
    metadata: dict[str, Any]


def _parse_document(path: Path) -> KnowledgeDocument:
    raw = path.read_text(encoding="utf-8")
    metadata: dict[str, Any] = {}
    text = raw
    if raw.startswith("---"):
        parts = raw.split("---", 2)
        if len(parts) != 3:
            raise KnowledgeDocumentError(f"invalid frontmatter: {path}")
        parsed = yaml.safe_load(parts[1]) or {}
        if not isinstance(parsed, dict):
            raise KnowledgeDocumentError(f"frontmatter must be an object: {path}")
        metadata = parsed
        text = parts[2].strip()

    title = str(metadata.get("title", "")).strip()
    try:
        version = int(metadata.get("version", 0))
    except (TypeError, ValueError) as exc:
        raise KnowledgeDocumentError(f"version must be an integer: {path}") from exc
    status = str(metadata.get("status", "")).strip().lower()
    sensitivity = str(metadata.get("sensitivity", "internal")).strip().lower()
    if not title or version < 1 or status != "approved":
        raise KnowledgeDocumentError(f"document is not valid and approved: {path}")
    if sensitivity not in _ALLOWED_SENSITIVITY:
        raise KnowledgeDocumentError(f"invalid sensitivity {sensitivity!r}: {path}")
    if not text:
        raise KnowledgeDocumentError(f"document body is empty: {path}")

    return KnowledgeDocument(
        title=title,
        version=version,
        status=status,
        sensitivity=sensitivity,
        source=str(path),
        text=text,
        metadata={**metadata, "title": title, "version": version, "sensitivity": sensitivity},
    )


def load_documents(root: str | Path) -> tuple[list[KnowledgeDocument], list[str]]:
    """Load approved Markdown documents, returning valid docs and errors."""
    root_path = Path(root)
    documents: list[KnowledgeDocument] = []
    errors: list[str] = []
    if not root_path.exists():
        return [], [f"knowledge root does not exist: {root_path}"]
    for path in sorted(root_path.rglob("*.md")):
        try:
            documents.append(_parse_document(path))
        except KnowledgeDocumentError as exc:
            errors.append(str(exc))
    return documents, errors


async def rebuild_index(root: str | Path) -> dict[str, Any]:
    """Replace the RAG index with valid approved company documents."""
    documents, errors = load_documents(root)
    rag.clear_index()
    indexed = await rag.index_documents(
        [
            {
                "text": doc.text,
                "source": doc.source,
                "metadata": doc.metadata,
            }
            for doc in documents
        ]
    )
    return {"documents": len(documents), "chunks": indexed, "errors": errors}


async def search(
    query: str,
    *,
    top_k: int = 5,
    access_level: str = "internal",
) -> list[dict[str, Any]]:
    """Search only documents visible at the requested access level."""
    if access_level not in _ALLOWED_SENSITIVITY:
        raise KnowledgeDocumentError(f"invalid access level: {access_level!r}")
    results = await rag.search_similar(query, top_k=top_k * 2)
    maximum = _ALLOWED_SENSITIVITY[access_level]
    visible = [
        result
        for result in results
        if _ALLOWED_SENSITIVITY.get(
            str(result.get("metadata", {}).get("sensitivity", "internal")), 1
        )
        <= maximum
    ]
    return visible[:top_k]


def citation_label(hit: dict[str, Any]) -> str:
    """Human citation: title + version, never a raw URL."""
    raw_meta = hit.get("metadata")
    meta: dict[str, Any] = dict(raw_meta) if isinstance(raw_meta, dict) else {}
    title = str(meta.get("title") or "").strip()
    if not title:
        source = str(hit.get("source") or "")
        title = Path(source).name or "company document"
    if title.lower().startswith("http"):
        title = "company document"
    version = meta.get("version")
    label = f"{title} v{version}" if version else title
    return label.replace("\n", " ")[:80]


def pack_for_llm(hits: list[dict[str, Any]]) -> str:
    """Frame retrieved chunks as DATA, not instructions."""
    parts: list[str] = []
    for hit in hits or []:
        text = str(hit.get("text") or "")
        if not text.strip():
            continue
        framed = inspect_data(text, source=citation_label(hit))
        if framed.text:
            parts.append(framed.text)
    return "\n\n".join(parts)


async def retrieve_for_answer(
    query: str,
    *,
    top_k: int = 5,
    access_level: str = "internal",
) -> dict[str, Any]:
    """One call for agents: hits + empty flag + LLM pack. Empty → honest admission."""
    q = (query or "").strip()
    if not q:
        return {"hits": [], "empty": True, "pack": "", "query": ""}
    hits = await search(q, top_k=top_k, access_level=access_level)
    labelled = []
    for hit in hits:
        item = dict(hit)
        item["citation"] = citation_label(hit)
        labelled.append(item)
    return {
        "hits": labelled,
        "empty": not labelled,
        "pack": pack_for_llm(labelled),
        "query": q[:200],
    }
