"""Unit tests for app.admin_api.rbac — role enforcement on the admin API."""

from __future__ import annotations

import pytest
from fastapi import HTTPException

from app.admin_api.rbac import (
    ROLE_ADMIN,
    ROLE_RANK,
    ROLE_SUPERADMIN,
    ROLE_VIEWER,
    has_role,
    normalize_role,
    rank_of,
    require_role,
)


class TestNormalizeRole:
    def test_canonical_roles_pass_through(self):
        assert normalize_role("viewer") == ROLE_VIEWER
        assert normalize_role("admin") == ROLE_ADMIN
        assert normalize_role("superadmin") == ROLE_SUPERADMIN

    def test_case_and_whitespace_insensitive(self):
        assert normalize_role("  SuperAdmin ") == ROLE_SUPERADMIN

    def test_legacy_editor_maps_to_admin(self):
        # The tools layer used viewer/editor/admin; align it with the DB.
        assert normalize_role("editor") == ROLE_ADMIN

    def test_aliases(self):
        assert normalize_role("readonly") == ROLE_VIEWER
        assert normalize_role("owner") == ROLE_SUPERADMIN
        assert normalize_role("root") == ROLE_SUPERADMIN

    @pytest.mark.parametrize("bad", [None, "", "   ", "wizard", "DROP TABLE", "1"])
    def test_unknown_degrades_to_viewer_not_escalate(self, bad):
        """A malformed role must never grant privilege."""
        assert normalize_role(bad) == ROLE_VIEWER


class TestRanking:
    def test_rank_order(self):
        assert ROLE_RANK[ROLE_VIEWER] < ROLE_RANK[ROLE_ADMIN] < ROLE_RANK[ROLE_SUPERADMIN]

    def test_rank_of_unknown_is_lowest(self):
        assert rank_of("nonsense") == 0

    def test_superadmin_satisfies_everything(self):
        for required in (ROLE_VIEWER, ROLE_ADMIN, ROLE_SUPERADMIN):
            assert has_role(ROLE_SUPERADMIN, required)

    def test_viewer_only_satisfies_viewer(self):
        assert has_role(ROLE_VIEWER, ROLE_VIEWER)
        assert not has_role(ROLE_VIEWER, ROLE_ADMIN)
        assert not has_role(ROLE_VIEWER, ROLE_SUPERADMIN)

    def test_admin_cannot_do_superadmin(self):
        assert has_role(ROLE_ADMIN, ROLE_ADMIN)
        assert not has_role(ROLE_ADMIN, ROLE_SUPERADMIN)


class TestRequireRoleDependency:
    async def test_allows_sufficient_role(self):
        dep = require_role(ROLE_ADMIN)
        admin = {"username": "u", "role": "superadmin"}
        assert await dep(admin) is admin

    async def test_rejects_insufficient_role_with_403(self):
        dep = require_role(ROLE_SUPERADMIN)
        with pytest.raises(HTTPException) as exc:
            await dep({"username": "v", "role": "viewer"})
        assert exc.value.status_code == 403

    async def test_error_message_names_both_roles(self):
        dep = require_role(ROLE_SUPERADMIN)
        with pytest.raises(HTTPException) as exc:
            await dep({"username": "v", "role": "viewer"})
        assert "superadmin" in str(exc.value.detail)
        assert "viewer" in str(exc.value.detail)

    async def test_missing_role_field_is_treated_as_viewer(self):
        """A row without a role must not be able to write."""
        dep = require_role(ROLE_ADMIN)
        with pytest.raises(HTTPException) as exc:
            await dep({"username": "legacy"})
        assert exc.value.status_code == 403

    async def test_viewer_dependency_allows_any_authenticated(self):
        dep = require_role(ROLE_VIEWER)
        for role in ("viewer", "admin", "superadmin", "garbage"):
            assert await dep({"username": "u", "role": role})

    async def test_editor_alias_can_write(self):
        dep = require_role(ROLE_ADMIN)
        assert await dep({"username": "e", "role": "editor"})


class TestEndpointWiring:
    """Guard against regressions: destructive routes must not accept viewers."""

    def _deps(self, fn):
        import inspect

        return [
            p.default.dependency.__name__
            for p in inspect.signature(fn).parameters.values()
            if hasattr(p.default, "dependency")
        ]

    def test_delete_product_requires_superadmin(self):
        from app.admin_api.catalog import delete_product

        assert any("superadmin" in d for d in self._deps(delete_product))

    def test_create_product_requires_writer(self):
        from app.admin_api.catalog import create_product

        assert any("admin" in d for d in self._deps(create_product))

    def test_approval_decide_requires_writer(self):
        from app.admin_api.approvals import decide_approval

        assert any("admin" in d for d in self._deps(decide_approval))

    def test_list_products_stays_readable(self):
        """Read endpoints must NOT have been over-restricted."""
        from app.admin_api.catalog import list_products

        deps = self._deps(list_products)
        assert not any("superadmin" in d for d in deps)
