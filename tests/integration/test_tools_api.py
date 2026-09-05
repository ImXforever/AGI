"""Integration tests for the tool execution layer.

Two privilege bugs lived here and are pinned by regression tests below:

* ``execute_tool`` ranked roles with the legacy ``viewer/editor/admin`` table,
  under which a real ``superadmin`` scored 0 — below a viewer — and was denied
  every ``min_role``-guarded tool.
* ``/tools/execute`` read the caller's role from the **request body**, so any
  authenticated viewer could escalate by posting ``{"role": "superadmin"}``.
"""

from __future__ import annotations

from typing import Any

import pytest

from app.core.tools import ALL_TOOLS, TOOLS_BY_SKILL
from tests.conftest import requires_infra

pytestmark = [pytest.mark.integration, requires_infra]


class TestRegistry:
    def test_tools_are_registered(self):
        assert len(ALL_TOOLS) > 0

    def test_every_tool_has_a_callable_and_a_skill(self):
        for name, tool in ALL_TOOLS.items():
            assert callable(tool["fn"]), name
            assert tool.get("skill"), name

    def test_the_skill_index_matches_the_flat_registry(self):
        flattened = {n for tools in TOOLS_BY_SKILL.values() for n in tools}
        assert flattened == set(ALL_TOOLS)

    def test_declared_min_roles_are_all_recognised(self):
        from app.admin_api.rbac import normalize_role

        for name, tool in ALL_TOOLS.items():
            role = tool.get("min_role")
            if role:
                assert normalize_role(role) in {"viewer", "admin", "superadmin"}, name


class TestCatalogEndpoints:
    async def test_the_tool_catalog_is_listed(self, superadmin_client: Any):
        body = (await superadmin_client.get("/tools/catalog")).json()
        assert body["total"] == len(ALL_TOOLS)
        assert body["by_skill"]

    async def test_mutating_tools_are_listed(self, superadmin_client: Any):
        resp = await superadmin_client.get("/tools/mutating")
        assert resp.status_code == 200

    async def test_the_catalog_requires_authentication(self, client: Any):
        client.cookies.clear()
        assert (await client.get("/tools/mutating")).status_code == 401


class TestExecute:
    async def test_an_unknown_tool_is_reported_with_the_available_list(
        self, superadmin_client: Any
    ):
        body = (
            await superadmin_client.post(
                "/tools/execute", json={"tool": "no_such_tool", "params": {}}
            )
        ).json()
        assert body["error"] == "unknown_tool"
        assert "available" in body

    async def test_a_real_tool_executes(self, superadmin_client: Any):
        body = (
            await superadmin_client.post(
                "/tools/execute", json={"tool": "search_products", "params": {"query": "oil"}}
            )
        ).json()
        assert body.get("error") != "insufficient_role"

    async def test_bad_parameters_are_reported_not_raised(self, superadmin_client: Any):
        body = (
            await superadmin_client.post(
                "/tools/execute",
                json={"tool": "search_products", "params": {"nonexistent_kwarg": 1}},
            )
        ).json()
        assert body["error"] == "tool_execution_failed"

    async def test_execution_requires_authentication(self, client: Any):
        client.cookies.clear()
        resp = await client.post("/tools/execute", json={"tool": "search_products", "params": {}})
        assert resp.status_code == 401


class TestPrivilegeEscalation:
    async def test_a_viewer_cannot_escalate_via_the_request_body(self, viewer_client: Any):
        """Regression: the role used to come from the payload, so this
        request would have run with superadmin privileges."""
        guarded = [
            name
            for name, tool in ALL_TOOLS.items()
            if tool.get("min_role") in {"admin", "editor", "superadmin"}
        ]
        if not guarded:
            pytest.skip("no role-guarded tools registered")

        body = (
            await viewer_client.post(
                "/tools/execute",
                json={"tool": guarded[0], "params": {}, "role": "superadmin"},
            )
        ).json()
        assert body.get("error") == "insufficient_role"
        assert body["caller"] != "superadmin"

    async def test_a_superadmin_is_not_demoted_by_the_legacy_rank_table(
        self, superadmin_client: Any
    ):
        """Regression: 'superadmin' was absent from the tools ROLE_RANK map and
        defaulted to 0, so the highest role was refused every guarded tool."""
        guarded = [
            name for name, tool in ALL_TOOLS.items() if tool.get("min_role") in {"admin", "editor"}
        ]
        if not guarded:
            pytest.skip("no role-guarded tools registered")

        body = (
            await superadmin_client.post("/tools/execute", json={"tool": guarded[0], "params": {}})
        ).json()
        assert body.get("error") != "insufficient_role"


class TestSequence:
    async def test_a_sequence_runs_every_step(self, superadmin_client: Any):
        body = (
            await superadmin_client.post(
                "/tools/sequence",
                json={
                    "steps": [
                        {"tool": "search_products", "params": {"query": "a"}},
                        {"tool": "search_products", "params": {"query": "b"}},
                    ],
                },
            )
        ).json()
        assert body["count"] == 2

    async def test_a_sequence_stops_at_the_first_error_by_default(self, superadmin_client: Any):
        body = (
            await superadmin_client.post(
                "/tools/sequence",
                json={
                    "steps": [
                        {"tool": "no_such_tool", "params": {}},
                        {"tool": "search_products", "params": {"query": "b"}},
                    ],
                },
            )
        ).json()
        assert body["count"] == 1

    async def test_continue_on_error_runs_the_remaining_steps(self, superadmin_client: Any):
        body = (
            await superadmin_client.post(
                "/tools/sequence",
                json={
                    "steps": [
                        {"tool": "no_such_tool", "params": {}},
                        {"tool": "search_products", "params": {"query": "b"}},
                    ],
                    "continue_on_error": True,
                },
            )
        ).json()
        assert body["count"] == 2

    async def test_an_empty_sequence_is_accepted(self, superadmin_client: Any):
        body = (await superadmin_client.post("/tools/sequence", json={"steps": []})).json()
        assert body["count"] == 0

    async def test_sequence_steps_cannot_escalate_either(self, viewer_client: Any):
        guarded = [
            name
            for name, tool in ALL_TOOLS.items()
            if tool.get("min_role") in {"admin", "editor", "superadmin"}
        ]
        if not guarded:
            pytest.skip("no role-guarded tools registered")

        body = (
            await viewer_client.post(
                "/tools/sequence",
                json={
                    "steps": [{"tool": guarded[0], "params": {}, "role": "superadmin"}],
                },
            )
        ).json()
        assert body["results"][0].get("error") == "insufficient_role"
