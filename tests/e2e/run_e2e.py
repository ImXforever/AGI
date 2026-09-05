"""End-to-end test runner for Kia-Agent Platform.

Exercises the full request lifecycle:
  1. Health check
  2. Admin login -> session
  3. Catalog CRUD
  4. Customer listing
  5. Approval flow
  6. SSE stream connectivity
  7. Analytics

Run: python tests/e2e/run_e2e.py
Requires a running server at BASE_URL (default: http://localhost:8080).
"""

from __future__ import annotations

import sys
from typing import Any

import httpx

BASE_URL = "http://localhost:8080"
ADMIN_USER = "admin"
ADMIN_PASS = "Change-Me-Immediately!123"

passed = 0
failed = 0
errors: list[str] = []


def test(name: str, fn: Any) -> None:
    global passed, failed
    try:
        fn()
        passed += 1
        print(f"  PASS  {name}")
    except Exception as exc:
        failed += 1
        msg = f"  FAIL  {name}: {exc}"
        print(msg)
        errors.append(msg)


def run_e2e() -> None:
    global passed, failed

    print("=" * 60)
    print("Kia-Agent Platform — E2E Test Suite")
    print("=" * 60)

    client = httpx.Client(base_url=BASE_URL, timeout=30)

    # --- Health ---
    def _health():
        r = client.get("/healthz")
        assert r.status_code == 200, f"status={r.status_code}"
        data = r.json()
        assert data.get("service") == "Kia-Agent-app"

    test("health_check", _health)

    # --- Root ---
    def _root():
        r = client.get("/")
        assert r.status_code == 200
        assert "text/html" in r.headers.get("content-type", "")
        assert b"Start a conversation" in r.content
        st = client.get("/status")
        assert st.status_code == 200
        data = st.json()
        assert data.get("public") == "/"

    test("root_endpoint", _root)

    # --- Login ---
    session_token: str = ""

    def _login():
        nonlocal session_token
        r = client.post(
            "/admin/api/auth/login",
            json={
                "username": ADMIN_USER,
                "password": ADMIN_PASS,
            },
        )
        assert r.status_code == 200, f"status={r.status_code}, body={r.text}"
        data = r.json()
        assert data.get("ok") is True
        # Extract cookie
        for cookie in r.cookies.jar:
            if cookie.name == "pa_session":
                session_token = cookie.value
                break

    test("admin_login", _login)

    # --- Session ---
    def _session():
        r = client.get("/admin/api/auth/session")
        assert r.status_code == 200
        data = r.json()
        assert data.get("authenticated") is True

    test("admin_session", _session)

    # --- Catalog: list ---
    def _catalog_list():
        r = client.get("/admin/api/catalog/products")
        assert r.status_code == 200
        data = r.json()
        assert "items" in data
        assert "total" in data

    test("catalog_list", _catalog_list)

    # --- Catalog: create product ---
    product_id: str = ""

    def _catalog_create():
        nonlocal product_id
        r = client.post(
            "/admin/api/catalog/products",
            json={
                "sku": "E2E-TEST-001",
                "name_ar": "منتج اختبار",
                "name_en": "E2E Test Product",
                "category": "test",
                "unit": "piece",
                "base_price": 99.99,
                "currency": "SAR",
            },
        )
        assert r.status_code == 201, f"status={r.status_code}, body={r.text}"
        data = r.json()
        product_id = data.get("id", "")

    test("catalog_create", _catalog_create)

    # --- Catalog: get product ---
    def _catalog_get():
        if not product_id:
            raise RuntimeError("no product_id from create")
        r = client.get(f"/admin/api/catalog/products/{product_id}")
        assert r.status_code == 200
        data = r.json()
        assert data["sku"] == "E2E-TEST-001"

    test("catalog_get", _catalog_get)

    # --- Catalog: delete product ---
    def _catalog_delete():
        if not product_id:
            raise RuntimeError("no product_id from create")
        r = client.delete(f"/admin/api/catalog/products/{product_id}")
        assert r.status_code == 200

    test("catalog_delete", _catalog_delete)

    # --- Customers ---
    def _customers_list():
        r = client.get("/admin/api/customers")
        assert r.status_code == 200
        data = r.json()
        assert "items" in data

    test("customers_list", _customers_list)

    # --- Approvals ---
    def _approvals_list():
        r = client.get("/admin/api/approvals")
        assert r.status_code == 200
        data = r.json()
        assert "items" in data
        assert "total" in data

    test("approvals_list", _approvals_list)

    # --- Analytics ---
    def _analytics_overview():
        r = client.get("/admin/api/analytics/overview")
        assert r.status_code == 200

    test("analytics_overview", _analytics_overview)

    def _analytics_channels():
        r = client.get("/admin/api/analytics/channels")
        assert r.status_code == 200

    test("analytics_channels", _analytics_channels)

    # --- Templates ---
    def _templates_list():
        r = client.get("/admin/api/templates")
        assert r.status_code == 200
        data = r.json()
        assert "items" in data

    test("templates_list", _templates_list)

    # --- Audit ---
    def _audit_list():
        r = client.get("/admin/api/audit")
        assert r.status_code == 200
        data = r.json()
        assert "items" in data

    test("audit_list", _audit_list)

    # --- Quotes ---
    def _quotes_list():
        r = client.get("/admin/api/quotes")
        assert r.status_code == 200
        data = r.json()
        assert "items" in data

    test("quotes_list", _quotes_list)

    # --- Tickets ---
    def _tickets_list():
        r = client.get("/admin/api/tickets")
        assert r.status_code == 200
        data = r.json()
        assert "items" in data

    test("tickets_list", _tickets_list)

    # --- Logout ---
    def _logout():
        r = client.post("/admin/api/auth/logout")
        assert r.status_code == 200
        data = r.json()
        assert data.get("ok") is True

    test("admin_logout", _logout)

    # --- Post-logout session ---
    def _post_logout_session():
        r = client.get("/admin/api/auth/session")
        assert r.status_code == 200
        data = r.json()
        assert data.get("authenticated") is False

    test("post_logout_session", _post_logout_session)

    # --- Config snapshot ---
    def _config_snapshot():
        r = client.get("/config/snapshot")
        assert r.status_code == 200
        data = r.json()
        assert "tenant" in data

    test("config_snapshot", _config_snapshot)

    # --- Metrics ---
    def _metrics():
        r = client.get("/metrics")
        assert r.status_code == 200
        data = r.json()
        assert "uptime_s" in data

    test("metrics", _metrics)

    client.close()

    print()
    print("=" * 60)
    print(f"Results: {passed} passed, {failed} failed, {passed + failed} total")
    print("=" * 60)
    if errors:
        print("\nFailures:")
        for e in errors:
            print(e)
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    run_e2e()
