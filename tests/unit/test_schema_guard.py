"""Unit tests for app.storage.schema_guard — the code/database contract check."""

from __future__ import annotations

import pytest

from app.storage import schema_guard
from app.storage.schema_guard import (
    MODE_OFF,
    MODE_STRICT,
    MODE_WARN,
    REQUIRED_SCHEMA,
    REQUIRED_VIEWS,
    SchemaDriftError,
    SchemaReport,
    diff_schema,
    resolve_mode,
    verify_schema,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

TINY_CONTRACT: dict[str, tuple[str, ...]] = {
    "products": ("id", "sku", "unit_price"),
    "approvals": ("id", "skill"),
}


def _complete_actual() -> dict[str, set[str]]:
    return {
        "products": {"id", "sku", "unit_price", "extra_col"},
        "approvals": {"id", "skill"},
    }


class FakePool:
    """Minimal asyncpg-pool stand-in returning canned information_schema rows."""

    def __init__(self, actual: dict[str, set[str]], views: set[str] | None = None):
        self._actual = actual
        self._views = views or set()

    async def fetch(self, query: str, *args):
        if "information_schema.views" in query:
            return [{"table_name": v} for v in sorted(self._views)]
        rows = []
        for table, columns in sorted(self._actual.items()):
            for column in sorted(columns):
                rows.append({"table_name": table, "column_name": column})
        return rows


# ---------------------------------------------------------------------------
# resolve_mode
# ---------------------------------------------------------------------------


class TestResolveMode:
    def test_explicit_modes(self):
        assert resolve_mode("off") == MODE_OFF
        assert resolve_mode("warn") == MODE_WARN
        assert resolve_mode("strict") == MODE_STRICT

    def test_case_and_whitespace_insensitive(self):
        assert resolve_mode("  STRICT  ") == MODE_STRICT

    def test_invalid_falls_back_to_warn(self):
        assert resolve_mode("banana") == MODE_WARN

    def test_reads_env(self, monkeypatch):
        monkeypatch.setenv("SCHEMA_GUARD_MODE", "strict")
        assert resolve_mode() == MODE_STRICT

    def test_defaults_to_warn(self, monkeypatch):
        # Neither the process env nor a .env file supplies the setting.
        monkeypatch.delenv("SCHEMA_GUARD_MODE", raising=False)
        monkeypatch.setattr(schema_guard, "_dotenv_lookup", lambda: {})
        assert resolve_mode() == MODE_WARN

    def test_falls_back_to_dotenv_when_not_in_process_env(self, monkeypatch):
        monkeypatch.delenv("SCHEMA_GUARD_MODE", raising=False)
        monkeypatch.setattr(schema_guard, "_dotenv_lookup", lambda: {"SCHEMA_GUARD_MODE": "strict"})
        assert resolve_mode() == MODE_STRICT

    def test_process_env_wins_over_dotenv(self, monkeypatch):
        monkeypatch.setenv("SCHEMA_GUARD_MODE", "off")
        monkeypatch.setattr(schema_guard, "_dotenv_lookup", lambda: {"SCHEMA_GUARD_MODE": "strict"})
        assert resolve_mode() == MODE_OFF


# ---------------------------------------------------------------------------
# diff_schema (pure)
# ---------------------------------------------------------------------------


class TestDiffSchema:
    def test_complete_schema_passes(self):
        report = diff_schema(_complete_actual(), set(), expected=TINY_CONTRACT, expected_views=())
        assert report.ok
        assert report.violation_count == 0
        assert report.checked_tables == 2
        assert report.checked_columns == 5

    def test_detects_missing_table(self):
        actual = _complete_actual()
        del actual["approvals"]
        report = diff_schema(actual, set(), expected=TINY_CONTRACT, expected_views=())
        assert not report.ok
        assert report.missing_tables == ("approvals",)

    def test_detects_missing_column(self):
        actual = _complete_actual()
        actual["products"].remove("unit_price")
        report = diff_schema(actual, set(), expected=TINY_CONTRACT, expected_views=())
        assert not report.ok
        assert "products.unit_price" in report.missing_columns

    def test_missing_table_does_not_also_report_its_columns(self):
        actual = _complete_actual()
        del actual["products"]
        report = diff_schema(actual, set(), expected=TINY_CONTRACT, expected_views=())
        assert report.missing_tables == ("products",)
        assert not any(c.startswith("products.") for c in report.missing_columns)

    def test_extra_columns_are_allowed(self):
        actual = _complete_actual()
        actual["products"].add("some_future_column")
        report = diff_schema(actual, set(), expected=TINY_CONTRACT, expected_views=())
        assert report.ok

    def test_detects_missing_view(self):
        report = diff_schema(
            _complete_actual(), set(), expected=TINY_CONTRACT, expected_views=("catalog_items",)
        )
        assert not report.ok
        assert report.missing_views == ("catalog_items",)

    def test_view_present_passes(self):
        report = diff_schema(
            _complete_actual(),
            {"catalog_items"},
            expected=TINY_CONTRACT,
            expected_views=("catalog_items",),
        )
        assert report.ok

    def test_summary_is_human_readable(self):
        actual = _complete_actual()
        actual["products"].remove("unit_price")
        report = diff_schema(actual, set(), expected=TINY_CONTRACT, expected_views=())
        assert "products.unit_price" in report.summary()
        assert "drift" in report.summary()

    def test_ok_summary(self):
        report = diff_schema(_complete_actual(), set(), expected=TINY_CONTRACT, expected_views=())
        assert "OK" in report.summary()

    def test_as_dict_is_json_safe(self):
        report = diff_schema(_complete_actual(), set(), expected=TINY_CONTRACT, expected_views=())
        d = report.as_dict()
        assert isinstance(d["missing_tables"], list)
        assert d["ok"] is True
        assert d["violations"] == 0


# ---------------------------------------------------------------------------
# verify_schema (async, against a fake pool)
# ---------------------------------------------------------------------------


class TestVerifySchema:
    async def test_off_mode_skips_entirely(self):
        report = await verify_schema(FakePool({}), mode=MODE_OFF)
        assert report.ok
        assert report.mode == MODE_OFF
        assert report.checked_tables == 0

    async def test_warn_mode_reports_but_does_not_raise(self):
        report = await verify_schema(FakePool({}), mode=MODE_WARN)
        assert not report.ok
        assert report.violation_count > 0

    async def test_strict_mode_raises_on_drift(self):
        with pytest.raises(SchemaDriftError):
            await verify_schema(FakePool({}), mode=MODE_STRICT)

    async def test_full_contract_passes_against_matching_pool(self):
        actual = {table: set(cols) for table, cols in REQUIRED_SCHEMA.items()}
        pool = FakePool(actual, views=set(REQUIRED_VIEWS))
        report = await verify_schema(pool, mode=MODE_STRICT)
        assert report.ok, report.summary()

    async def test_regression_products_unit_price(self):
        """The exact drift that produced HTTP 500 on /admin/api/catalog/products."""
        actual = {table: set(cols) for table, cols in REQUIRED_SCHEMA.items()}
        actual["products"].discard("unit_price")
        pool = FakePool(actual, views=set(REQUIRED_VIEWS))
        report = await verify_schema(pool, mode=MODE_WARN)
        assert not report.ok
        assert "products.unit_price" in report.missing_columns

    async def test_regression_approvals_skill(self):
        """The exact drift that killed the HITL sweeper loop."""
        actual = {table: set(cols) for table, cols in REQUIRED_SCHEMA.items()}
        actual["approvals"].discard("skill")
        pool = FakePool(actual, views=set(REQUIRED_VIEWS))
        report = await verify_schema(pool, mode=MODE_WARN)
        assert "approvals.skill" in report.missing_columns


# ---------------------------------------------------------------------------
# Contract sanity
# ---------------------------------------------------------------------------


class TestContractSanity:
    def test_contract_is_not_empty(self):
        assert len(REQUIRED_SCHEMA) > 15

    def test_every_table_declares_an_id_like_key(self):
        for table, columns in REQUIRED_SCHEMA.items():
            assert columns, f"{table} declares no columns"

    def test_no_duplicate_columns_declared(self):
        for table, columns in REQUIRED_SCHEMA.items():
            assert len(columns) == len(set(columns)), f"{table} has duplicate columns"

    def test_report_is_immutable(self):
        report = SchemaReport(ok=True, mode=MODE_WARN)
        with pytest.raises(Exception):
            report.ok = False  # type: ignore[misc]
