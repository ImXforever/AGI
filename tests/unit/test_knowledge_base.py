"""Tests for governed v0.3 company knowledge documents."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.core import knowledge_base as kb


def _write(path: Path, body: str) -> None:
    path.write_text(body, encoding="utf-8")


def test_load_documents_accepts_approved_markdown(tmp_path: Path) -> None:
    _write(
        tmp_path / "faq.md",
        """---
title: FAQ
version: 2
status: approved
sensitivity: public
---

پاسخ رسمی شرکت.
""",
    )
    docs, errors = kb.load_documents(tmp_path)
    assert not errors
    assert len(docs) == 1
    assert docs[0].title == "FAQ"
    assert docs[0].version == 2


def test_unapproved_document_is_rejected(tmp_path: Path) -> None:
    _write(
        tmp_path / "draft.md",
        """---
title: Draft
version: 1
status: draft
sensitivity: internal
---

متن پیش‌نویس.
""",
    )
    docs, errors = kb.load_documents(tmp_path)
    assert docs == []
    assert len(errors) == 1


def test_invalid_sensitivity_is_rejected(tmp_path: Path) -> None:
    _write(
        tmp_path / "bad.md",
        """---
title: Bad
version: 1
status: approved
sensitivity: secret
---

متن.
""",
    )
    _, errors = kb.load_documents(tmp_path)
    assert "invalid sensitivity" in errors[0]


@pytest.mark.asyncio
async def test_rebuild_index_indexes_only_valid_documents(tmp_path: Path) -> None:
    _write(
        tmp_path / "public.md",
        """---
title: Public
version: 1
status: approved
sensitivity: public
---

پاسخ درباره محصول عمومی.
""",
    )
    _write(
        tmp_path / "draft.md",
        """---
title: Draft
version: 1
status: draft
sensitivity: internal
---

نباید ایندکس شود.
""",
    )
    result = await kb.rebuild_index(tmp_path)
    assert result["documents"] == 1
    assert result["chunks"] >= 1
    assert result["errors"]


@pytest.mark.asyncio
async def test_confidential_results_are_hidden_from_public_access(tmp_path: Path) -> None:
    _write(
        tmp_path / "public.md",
        """---
title: Public
version: 1
status: approved
sensitivity: public
---

اطلاعات عمومی شرکت و محصول.
""",
    )
    _write(
        tmp_path / "private.md",
        """---
title: Private
version: 1
status: approved
sensitivity: confidential
---

اطلاعات محرمانه شرکت و محصول.
""",
    )
    await kb.rebuild_index(tmp_path)
    public_results = await kb.search("اطلاعات شرکت و محصول", access_level="public")
    assert all(r["metadata"]["sensitivity"] == "public" for r in public_results)


def test_invalid_access_level_is_rejected() -> None:
    with pytest.raises(kb.KnowledgeDocumentError, match="invalid access level"):
        # Search is async; validation is deliberately exercised through the
        # same public API by creating and closing the coroutine safely.
        import asyncio

        asyncio.run(kb.search("x", access_level="secret"))
