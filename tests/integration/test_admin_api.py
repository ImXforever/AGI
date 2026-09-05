"""Integration tests for the admin API against a real PostgreSQL + Redis stack.

These exercise the whole request path — session auth, RBAC, SQL, serialisation —
which is exactly the surface where every critical bug in this project hid.
"""

from __future__ import annotations

from typing import Any

import pytest

from tests.conftest import requires_infra

pytestmark = requires_infra


# ---------------------------------------------------------------------------
# Health & meta
# ---------------------------------------------------------------------------


class TestHealth:
    async def test_healthz_reports_dependencies(self, client: Any):
        resp = await client.get("/healthz")
        assert resp.status_code == 200
        body = resp.json()
        assert body["checks"]["postgres"]["ok"] is True
        assert body["checks"]["redis"]["ok"] is True

    async def test_healthz_includes_schema_guard(self, client: Any):
        body = (await client.get("/healthz")).json()
        schema = body["checks"]["schema"]
        assert schema["ok"] is True, schema
        assert schema["violations"] == 0
        assert schema["checked_tables"] > 20

    async def test_buildinfo(self, client: Any):
        """Build facts moved to /buildinfo; /metrics is now Prometheus text."""
        body = (await client.get("/buildinfo")).json()
        assert body["service"] == "Kia-Agent-app"

    async def test_openapi_served(self, client: Any):
        resp = await client.get("/api/openapi.json")
        assert resp.status_code == 200
        assert "/admin/api/catalog/products" in resp.json()["paths"]

    async def test_root_serves_public_landing(self, client: Any):
        resp = await client.get("/")
        assert resp.status_code == 200
        assert "text/html" in resp.headers.get("content-type", "")
        assert b"Start a conversation" in resp.content

    async def test_status_advertises_entrypoints(self, client: Any):
        body = (await client.get("/status")).json()
        assert body["service"] == "Kia-Agent-app"
        assert body["tenant"] == "test-tenant"
        assert body["health"] == "/healthz"
        assert body["public"] == "/"

    async def test_health_payload_leaks_no_secrets(self, client: Any):
        """The public probe must never echo credentials back to the caller."""
        raw = (await client.get("/healthz")).text.lower()
        for secret in ("integration-web-secret", "integrationtestpass", "testsecret1234567890"):
            assert secret.lower() not in raw


# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------


class TestAuthentication:
    async def test_unauthenticated_is_rejected(self, client: Any):
        fresh = client.cookies.jar.clear() or client
        resp = await fresh.get("/admin/api/catalog/products")
        assert resp.status_code == 401

    async def test_bad_password_rejected(self, client: Any):
        resp = await client.post(
            "/admin/api/auth/login", json={"username": "admin", "password": "wrong"}
        )
        assert resp.status_code in (401, 403)

    async def test_unknown_user_rejected(self, client: Any):
        resp = await client.post(
            "/admin/api/auth/login", json={"username": "ghost", "password": "x"}
        )
        assert resp.status_code in (401, 403)

    async def test_session_reports_identity(self, superadmin_client: Any):
        body = (await superadmin_client.get("/admin/api/auth/session")).json()
        assert body["authenticated"] is True
        assert body["username"] == "it_super"


# ---------------------------------------------------------------------------
# RBAC — the privilege boundary that previously did not exist
# ---------------------------------------------------------------------------


class TestRBACEnforcement:
    async def test_viewer_can_read(self, viewer_client: Any):
        assert (await viewer_client.get("/admin/api/catalog/products")).status_code == 200

    async def test_viewer_cannot_create(self, viewer_client: Any):
        resp = await viewer_client.post(
            "/admin/api/catalog/products",
            json={
                "sku": "VIEWER-DENIED",
                "name_ar": "x",
                "name_en": "x",
                "category": "c",
                "unit_price": 1.0,
                "currency": "SAR",
            },
        )
        assert resp.status_code == 403

    async def test_viewer_cannot_delete(self, viewer_client: Any, sample_product: dict):
        resp = await viewer_client.delete(f"/admin/api/catalog/products/{sample_product['id']}")
        assert resp.status_code == 403

    async def test_writer_can_create_but_not_delete(self, writer_client: Any, unique_sku: str):
        created = await writer_client.post(
            "/admin/api/catalog/products",
            json={
                "sku": unique_sku,
                "name_ar": "منتج",
                "name_en": "Prod",
                "category": "c",
                "unit_price": 5.0,
                "currency": "SAR",
            },
        )
        assert created.status_code == 200
        pid = created.json()["product_id"]

        denied = await writer_client.delete(f"/admin/api/catalog/products/{pid}")
        assert denied.status_code == 403

    async def test_superadmin_can_delete(self, superadmin_client: Any, sample_product: dict):
        resp = await superadmin_client.delete(f"/admin/api/catalog/products/{sample_product['id']}")
        assert resp.status_code == 200

    async def test_viewer_cannot_decide_approvals(self, viewer_client: Any):
        resp = await viewer_client.post(
            "/admin/api/approvals/00000000-0000-0000-0000-000000000000/decide",
            json={"status": "approved"},
        )
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Catalog CRUD
# ---------------------------------------------------------------------------


class TestCatalog:
    async def test_list_products_returns_seeds(self, superadmin_client: Any):
        body = (await superadmin_client.get("/admin/api/catalog/products")).json()
        assert body["total"] >= 5
        assert {"id", "sku", "unit_price", "stock_qty"} <= set(body["items"][0])

    async def test_create_read_update_delete(self, superadmin_client: Any, unique_sku: str):
        created = await superadmin_client.post(
            "/admin/api/catalog/products",
            json={
                "sku": unique_sku,
                "name_ar": "زيت",
                "name_en": "Oil",
                "category": "lubricants",
                "unit_price": 99.5,
                "currency": "SAR",
                "stock_qty": 7,
                "reorder_point": 2,
                "discount_tiers": [{"qty": 10, "pct": 5}],
                "technical_specs": {"viscosity": "10W-40"},
            },
        )
        assert created.status_code == 200, created.text
        pid = created.json()["product_id"]

        got = await superadmin_client.get(f"/admin/api/catalog/products/{pid}")
        assert got.status_code == 200
        assert got.json()["sku"] == unique_sku

        updated = await superadmin_client.put(
            f"/admin/api/catalog/products/{pid}", json={"unit_price": 120.0}
        )
        assert updated.status_code == 200

        deleted = await superadmin_client.delete(f"/admin/api/catalog/products/{pid}")
        assert deleted.status_code == 200

    async def test_duplicate_sku_conflicts(self, superadmin_client: Any, sample_product: dict):
        resp = await superadmin_client.post(
            "/admin/api/catalog/products",
            json={
                "sku": sample_product["sku"],
                "name_ar": "x",
                "name_en": "x",
                "category": "c",
                "unit_price": 1.0,
                "currency": "SAR",
            },
        )
        assert resp.status_code == 409

    async def test_missing_product_is_404(self, superadmin_client: Any):
        resp = await superadmin_client.get(
            "/admin/api/catalog/products/00000000-0000-0000-0000-000000000000"
        )
        assert resp.status_code == 404

    async def test_negative_price_rejected(self, superadmin_client: Any, unique_sku: str):
        resp = await superadmin_client.post(
            "/admin/api/catalog/products",
            json={
                "sku": unique_sku,
                "name_ar": "x",
                "name_en": "x",
                "category": "c",
                "unit_price": -5.0,
                "currency": "SAR",
            },
        )
        assert resp.status_code == 422

    async def test_search_filter(self, superadmin_client: Any, sample_product: dict):
        body = (
            await superadmin_client.get(
                f"/admin/api/catalog/products?search={sample_product['sku']}"
            )
        ).json()
        assert body["total"] == 1

    async def test_faq_and_troubleshooting_seeded(self, superadmin_client: Any):
        faq = (await superadmin_client.get("/admin/api/catalog/faq")).json()
        ts = (await superadmin_client.get("/admin/api/catalog/troubleshooting")).json()
        assert faq["total"] >= 3
        assert ts["total"] >= 3

    async def test_msds_lifecycle(self, superadmin_client: Any, sample_product: dict):
        created = await superadmin_client.post(
            "/admin/api/catalog/msds",
            json={
                "product_id": sample_product["id"],
                "title_ar": "ورقة بيانات",
                "title_en": "Safety Sheet",
                "r2_key": "msds/test.pdf",
                "version": 1,
                "language": "ar",
            },
        )
        assert created.status_code == 200
        listed = (await superadmin_client.get("/admin/api/catalog/msds")).json()
        assert listed["total"] >= 1


# ---------------------------------------------------------------------------
# Remaining admin surfaces
# ---------------------------------------------------------------------------


class TestAdminSurfaces:
    @pytest.mark.parametrize(
        "path",
        [
            "/admin/api/approvals",
            "/admin/api/customers",
            "/admin/api/quotes",
            "/admin/api/tickets",
            "/admin/api/audit",
            "/admin/api/templates",
            "/admin/api/analytics/overview",
            "/admin/api/analytics/channels",
            "/admin/api/analytics/hourly",
            "/admin/api/analytics/top-products",
            "/admin/api/analytics/response-times",
            "/admin/api/stream/stats",
        ],
    )
    async def test_endpoint_is_healthy(self, superadmin_client: Any, path: str):
        resp = await superadmin_client.get(path)
        assert resp.status_code == 200, f"{path} -> {resp.status_code}: {resp.text[:200]}"

    async def test_template_crud(self, superadmin_client: Any):
        created = await superadmin_client.post(
            "/admin/api/templates",
            json={"key": "it_tpl", "name_ar": "قالب", "body_ar": "مرحبا"},
        )
        assert created.status_code == 201
        tid = created.json()["id"]

        updated = await superadmin_client.put(
            f"/admin/api/templates/{tid}", json={"body_ar": "محدث"}
        )
        assert updated.status_code == 200

        assert (await superadmin_client.delete(f"/admin/api/templates/{tid}")).status_code == 200

    async def test_analytics_overview_shape(self, superadmin_client: Any):
        body = (await superadmin_client.get("/admin/api/analytics/overview")).json()
        for key in ("total_conversations", "total_customers", "pending_approvals"):
            assert key in body
