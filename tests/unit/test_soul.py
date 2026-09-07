"""Agent Soul — DB-backed identity rendered into every prompt."""

from __future__ import annotations

import pytest

from app.core import soul as soul_mod
from app.core.soul import DEFAULT_SOUL, Soul, load_soul, save_soul
from app.storage.seed import _conflict_column


class _Pool:
    """Tiny asyncpg stand-in: one soul row, records executed SQL."""

    def __init__(self, row: dict | None = None, fail: bool = False) -> None:
        self.row = row
        self.fail = fail
        self.executed: list[tuple] = []

    async def fetchrow(self, sql: str, *args):
        if self.fail:
            raise RuntimeError("relation agent_soul does not exist")
        return self.row

    async def execute(self, sql: str, *args):
        self.executed.append((sql, args))
        keys = [
            "id",
            "agent_name",
            "company_name",
            "role_title",
            "mission",
            "personality",
            "tone",
            "languages",
            "greeting",
            "boundaries",
            "style_rules",
            "signature",
            "extra",
            "updated_by",
        ]
        self.row = dict(zip(keys, args, strict=False))
        self.row["version"] = int((self.row or {}).get("version") or 0) + 1


@pytest.fixture(autouse=True)
def _fresh_cache():
    soul_mod.invalidate_cache()
    yield
    soul_mod.invalidate_cache()


def test_render_contains_identity_and_plain_text_rule():
    s = Soul(agent_name="Nova", company_name="ACME", role_title="Ops Lead")
    text = s.render()
    assert "You are Nova, the Ops Lead at ACME." in text
    assert "Do NOT use Markdown" in text
    assert "**" not in text.replace("**bold**", "")


@pytest.mark.asyncio
async def test_load_from_db_row():
    pool = _Pool(
        {
            "agent_name": "Zenovix",
            "company_name": "EGL",
            "role_title": "Digital Operations Manager",
            "mission": "help",
            "extra": '{"currency": "USD"}',
            "version": 3,
            "updated_by": "ops",
        }
    )
    s = await load_soul(pool)
    assert s.source == "db"
    assert s.company_name == "EGL"
    assert s.extra == {"currency": "USD"}
    assert s.version == 3
    # cached now: a failing pool is not consulted
    s2 = await load_soul(_Pool(fail=True))
    assert s2 is s


@pytest.mark.asyncio
async def test_missing_table_falls_back_to_default():
    s = await load_soul(_Pool(fail=True), use_cache=False)
    assert s.agent_name == DEFAULT_SOUL.agent_name
    assert s.source == "default"
    assert "You are Zenovix" in s.render()


@pytest.mark.asyncio
async def test_save_upserts_and_refreshes_cache():
    pool = _Pool(None)
    s = await save_soul(
        pool, {"agent_name": "Nova", "tone": "playful", "ignored": "x"}, updated_by="boss"
    )
    assert pool.executed and "ON CONFLICT (id) DO UPDATE" in pool.executed[0][0]
    assert s.agent_name == "Nova"
    assert s.tone == "playful"
    assert s.source == "db"
    assert s.updated_by == "boss"


def test_seed_conflict_columns():
    assert _conflict_column("products", ["sku", "name_ar"]) == "sku"
    assert _conflict_column("fallback_templates", ["key", "body_ar"]) == "key"
    assert _conflict_column("agent_soul", ["id", "agent_name"]) == "id"
    assert _conflict_column("faq", ["question_ar"]) == ""
