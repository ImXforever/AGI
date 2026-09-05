"""Tests for v12 admin training entry validation."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.admin_api.training import TrainingEntryCreate, validate_training_id


def test_training_entry_strips_text() -> None:
    entry = TrainingEntryCreate(
        question_ar="  ما السعر؟  ",
        answer_ar="  السعر حسب الكمية.  ",
        category=" sales ",
        language=" ar ",
    )
    assert entry.question_ar == "ما السعر؟"
    assert entry.answer_ar == "السعر حسب الكمية."
    assert entry.category == "sales"
    assert entry.language == "ar"


def test_training_entry_requires_a_real_question_and_answer() -> None:
    with pytest.raises(ValidationError):
        TrainingEntryCreate(question_ar="x", answer_ar="ok")
    with pytest.raises(ValidationError):
        TrainingEntryCreate(question_ar="سؤال", answer_ar="x")


def test_training_id_is_uuid_only() -> None:
    value = "123e4567-e89b-12d3-a456-426614174000"
    assert validate_training_id(value) == value
    with pytest.raises(ValueError, match="UUID"):
        validate_training_id("faq-1")
