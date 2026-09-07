"""Admin training data management for v12."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field, field_validator

from app.admin_api.auth import require_admin
from app.admin_api.rbac import require_superadmin, require_writer

router = APIRouter(prefix="/training", tags=["admin-training"])


class TrainingEntryCreate(BaseModel):
    question_ar: str = Field(..., min_length=2, max_length=2_000)
    answer_ar: str = Field(..., min_length=2, max_length=10_000)
    question_en: str = Field(default="", max_length=2_000)
    answer_en: str = Field(default="", max_length=10_000)
    category: str = Field(default="general", min_length=1, max_length=80)
    language: str = Field(default="ar", min_length=2, max_length=10)

    @field_validator("question_ar", "answer_ar", "question_en", "answer_en", "category", "language")
    @classmethod
    def strip_values(cls, value: str) -> str:
        return value.strip()


class TrainingEntryUpdate(BaseModel):
    question_ar: str | None = Field(default=None, min_length=2, max_length=2_000)
    answer_ar: str | None = Field(default=None, min_length=2, max_length=10_000)
    question_en: str | None = Field(default=None, max_length=2_000)
    answer_en: str | None = Field(default=None, max_length=10_000)
    category: str | None = Field(default=None, min_length=1, max_length=80)
    language: str | None = Field(default=None, min_length=2, max_length=10)
    is_active: bool | None = None


def validate_training_id(value: str) -> str:
    """Validate ids before they reach a SQL parameter."""
    try:
        return str(UUID(value))
    except (ValueError, AttributeError, TypeError) as exc:
        raise ValueError("training entry id must be a UUID") from exc


@router.get("/entries")
async def list_training_entries(
    request: Request,
    language: str | None = None,
    active_only: bool = True,
    admin: dict[str, Any] = Depends(require_admin),
) -> dict[str, Any]:
    pool = request.app.state.services["pg"]
    params: list[Any] = []
    conditions: list[str] = []
    if active_only:
        conditions.append("is_active = TRUE")
    if language:
        params.append(language.strip())
        conditions.append(f"language = ${len(params)}")
    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    rows = await pool.fetch(
        f"SELECT id, question_ar, answer_ar, question_en, answer_en, category, language, is_active, created_at, updated_at FROM faq {where} ORDER BY updated_at DESC",
        *params,
    )
    return {"items": [dict(row) for row in rows]}


@router.post("/entries", status_code=201)
async def create_training_entry(
    req: TrainingEntryCreate,
    request: Request,
    admin: dict[str, Any] = Depends(require_writer),
) -> dict[str, Any]:
    pool = request.app.state.services["pg"]
    row = await pool.fetchrow(
        """INSERT INTO faq (question_ar, answer_ar, question_en, answer_en, category, language)
           VALUES ($1, $2, $3, $4, $5, $6)
           RETURNING id, question_ar, answer_ar, question_en, answer_en, category, language, is_active, created_at, updated_at""",
        req.question_ar,
        req.answer_ar,
        req.question_en,
        req.answer_en,
        req.category,
        req.language,
    )
    return dict(row)


@router.put("/entries/{entry_id}")
async def update_training_entry(
    entry_id: str,
    req: TrainingEntryUpdate,
    request: Request,
    admin: dict[str, Any] = Depends(require_writer),
) -> dict[str, Any]:
    try:
        normalized_id = validate_training_id(entry_id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    changes = req.model_dump(exclude_none=True)
    if not changes:
        raise HTTPException(status_code=400, detail="no fields to update")
    assignments = [f"{key} = ${index}" for index, key in enumerate(changes, start=1)]
    values = list(changes.values()) + [normalized_id]
    row = await request.app.state.services["pg"].fetchrow(
        f"UPDATE faq SET {', '.join(assignments)}, updated_at = NOW() WHERE id = ${len(values)} RETURNING id, question_ar, answer_ar, question_en, answer_en, category, language, is_active, created_at, updated_at",
        *values,
    )
    if row is None:
        raise HTTPException(status_code=404, detail="training entry not found")
    return dict(row)


@router.delete("/entries/{entry_id}")
async def delete_training_entry(
    entry_id: str,
    request: Request,
    admin: dict[str, Any] = Depends(require_superadmin),
) -> dict[str, bool]:
    try:
        normalized_id = validate_training_id(entry_id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    result = await request.app.state.services["pg"].execute(
        "DELETE FROM faq WHERE id = $1", normalized_id
    )
    if result == "DELETE 0":
        raise HTTPException(status_code=404, detail="training entry not found")
    return {"ok": True}
