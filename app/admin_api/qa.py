"""QA history API endpoints (v20)."""

from __future__ import annotations

import time
from typing import Any

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel

from app.admin_api.auth import require_admin
from app.logging_setup import get_logger

log = get_logger("app.admin_api.qa")

router = APIRouter(prefix="/qa", tags=["admin-qa"])


class QACheckRequest(BaseModel):
    response_text: str
    original_question: str = ""
    knowledge_context: str = ""
    threshold: int = 70


@router.get("/history")
async def qa_history(
    request: Request,
    limit: int = 50,
    passed_only: bool = False,
    admin: dict[str, Any] = Depends(require_admin),
) -> dict[str, Any]:
    pool = request.app.state.services["pg"]
    if passed_only:
        rows = await pool.fetch(
            "SELECT * FROM qa_checks WHERE passed = TRUE ORDER BY checked_at DESC LIMIT $1", limit
        )
    else:
        rows = await pool.fetch("SELECT * FROM qa_checks ORDER BY checked_at DESC LIMIT $1", limit)
    return {"checks": [dict(r) for r in rows], "count": len(rows)}


@router.get("/stats")
async def qa_stats(
    request: Request,
    admin: dict[str, Any] = Depends(require_admin),
) -> dict[str, Any]:
    pool = request.app.state.services["pg"]
    row = await pool.fetchrow(
        """
        SELECT
            COUNT(*) as total_checks,
            COUNT(*) FILTER (WHERE passed = TRUE) as passed,
            COUNT(*) FILTER (WHERE passed = FALSE) as failed,
            COUNT(*) FILTER (WHERE rewritten = TRUE) as rewritten,
            AVG(score_total) as avg_score
        FROM qa_checks
        WHERE checked_at >= $1
    """,
        time.time() - 86400,
    )
    return dict(row) if row else {}


@router.post("/check")
async def check_response_endpoint(
    request: Request,
    body: QACheckRequest,
    admin: dict[str, Any] = Depends(require_admin),
) -> dict[str, Any]:
    from app.core.qa_engine import check_response

    check = check_response(
        body.response_text,
        original_question=body.original_question,
        knowledge_context=body.knowledge_context,
        threshold=body.threshold,
    )
    pool = request.app.state.services["pg"]
    try:
        await pool.execute(
            """
            INSERT INTO qa_checks (response_text, score_total, passed, rewritten, rewritten_text, checked_at)
            VALUES ($1, $2, $3, $4, $5, $6)
        """,
            check.response_text[:2000],
            check.score.total,
            check.passed,
            check.rewritten,
            check.rewritten_text[:2000],
            check.checked_at,
        )
    except Exception:
        log.debug("qa_check_save_failed", extra={"action": "qa.check"})
    return check.as_dict()
