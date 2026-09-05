"""Documentation tools — FAQ search and MSDS retrieval with R2 signed URLs."""

from __future__ import annotations

from typing import Any

from asyncpg.pool import Pool

from app.logging_setup import get_logger

log = get_logger("tools.docs")


async def search_faq(pool: Pool, *, query: str, limit: int = 5) -> dict[str, Any]:
    """Search the FAQ knowledge base by keyword in Arabic or English."""
    rows = await pool.fetch(
        """
        SELECT id, question_ar, question_en, answer_ar, answer_en,
               category, language
        FROM faq
        WHERE (
            question_ar ILIKE '%' || $1 || '%'
            OR answer_ar ILIKE '%' || $1 || '%'
            OR question_en ILIKE '%' || $1 || '%'
            OR answer_en ILIKE '%' || $1 || '%'
            OR category ILIKE '%' || $1 || '%'
        )
        ORDER BY category, id
        LIMIT $2
        """,
        query,
        max(1, min(limit, 20)),
    )
    return {
        "count": len(rows),
        "faqs": [dict(r) for r in rows],
    }


async def get_msds_doc(
    pool: Pool, *, doc_id: str | None = None, product_id: str | None = None
) -> dict[str, Any]:
    """Retrieve an MSDS (Material Safety Data Sheet) document.

    Returns metadata from the database and a pre-signed R2 URL for download.
    Either *doc_id* or *product_id* must be provided.
    """
    if doc_id:
        row = await pool.fetchrow(
            """
            SELECT id, product_id, title_ar, title_en, r2_key,
                   version, language, created_at
            FROM msds_documents
            WHERE id = $1
            """,
            doc_id,
        )
    elif product_id:
        row = await pool.fetchrow(
            """
            SELECT id, product_id, title_ar, title_en, r2_key,
                   version, language, created_at
            FROM msds_documents
            WHERE product_id = $1
            ORDER BY version DESC
            LIMIT 1
            """,
            product_id,
        )
    else:
        return {"error": "provide_doc_id_or_product_id"}

    if row is None:
        return {"error": "msds_not_found"}

    from app.config import get_config

    cfg = get_config()
    r2 = _get_r2_client(cfg)
    signed_url = r2.generate_presigned_url(
        bucket=cfg.storage.r2_bucket,
        key=f"{cfg.storage.r2_prefix}/msds/{row['r2_key']}",
        ttl_seconds=cfg.storage.r2_signed_url_ttl,
    )

    log.info(
        "msds doc retrieved",
        extra={"action": "tools.get_msds_doc", "entity": f"msds:{row['id']}"},
    )

    return {
        "doc_id": row["id"],
        "product_id": row["product_id"],
        "title_ar": row["title_ar"],
        "title_en": row["title_en"],
        "version": row["version"],
        "language": row["language"],
        "created_at": str(row["created_at"]),
        "download_url": signed_url,
        "url_expires_in": cfg.storage.r2_signed_url_ttl,
    }


def _get_r2_client(cfg: Any) -> Any:
    """Lazy-import and cache an S3-compatible client for R2 signed URLs."""
    import boto3

    return boto3.client(
        "s3",
        endpoint_url=cfg.storage.r2_endpoint,
        aws_access_key_id=cfg.storage.r2_access_key_id,
        aws_secret_access_key=cfg.storage.r2_secret_access_key,
        region_name="auto",
    )


REGISTRY: dict[str, dict[str, Any]] = {
    "search_faq": {
        "fn": search_faq,
        "description": "Search the FAQ knowledge base (Arabic + English).",
        "skill": "knowledge_agent",
        "params": {
            "query": {"type": "string", "required": True},
            "limit": {"type": "integer", "default": 5},
        },
        "mutating": False,
    },
    "get_msds_doc": {
        "fn": get_msds_doc,
        "description": "Retrieve MSDS document metadata and a signed R2 download URL.",
        "skill": "knowledge_agent",
        "params": {
            "doc_id": {"type": "integer", "required": False},
            "product_id": {"type": "integer", "required": False},
        },
        "mutating": False,
    },
}
