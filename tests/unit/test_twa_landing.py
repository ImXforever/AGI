"""Static contract tests for the public Telegram Web App landing page."""

from __future__ import annotations

from pathlib import Path

LANDING = Path(__file__).parents[2] / "admin" / "landing.html"


def test_landing_page_exists_and_is_ltr_mobile_ready() -> None:
    html = LANDING.read_text(encoding="utf-8")
    assert '<html lang="en" dir="ltr">' in html
    assert 'name="viewport"' in html
    assert "Telegram.WebApp" in html


def test_landing_page_has_user_ctas() -> None:
    html = LANDING.read_text(encoding="utf-8")
    assert "Start a conversation" in html
    assert 'data-action="products"' in html
    assert 'data-action="support"' in html
    assert 'data-action="quote"' in html


def test_login_is_hidden_until_twa_admin_probe() -> None:
    html = LANDING.read_text(encoding="utf-8")
    assert "data-admin-login" in html
    assert "/admin/api/twa/probe" in html
    assert "/admin/api/twa/login" in html
    assert "/admin/ops/ecosystem.html" in html
    # Must not advertise the admin SPA to the public audience.
    assert 'href="/admin/"' not in html
    assert "Admin panel" not in html
