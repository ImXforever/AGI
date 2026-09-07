"""Static contract tests for the public Telegram Web App landing page."""

from __future__ import annotations

from pathlib import Path

LANDING = Path(__file__).parents[2] / "web" / "index.html"


def test_landing_page_exists_and_is_ltr_mobile_ready() -> None:
    html = LANDING.read_text(encoding="utf-8")
    assert '<html lang="en" dir="ltr">' in html
    assert 'name="viewport"' in html
    assert "telegram-web-app.js" in html
    assert "safe-area-inset" in html


def test_landing_page_has_user_ctas() -> None:
    html = LANDING.read_text(encoding="utf-8")
    assert "Start a conversation" in html
    assert 'data-action="products"' in html
    assert 'data-action="support"' in html
    assert 'data-action="quote"' in html
    assert 'href="/app"' in html
    assert "t.me/AGI_bot" not in html
    assert "TELEGRAM_BOT_TOKEN" not in html
    assert "â" not in html
    assert 'charset="utf-8"' in html


def test_login_is_hidden_until_twa_admin_probe() -> None:
    html = LANDING.read_text(encoding="utf-8")
    js = (Path(__file__).parents[2] / "web" / "js" / "public.js").read_text(encoding="utf-8")
    assert "data-admin-login" in html
    assert "/admin/api/twa/probe" in js
    assert "/admin/api/twa/login" in js
    assert "/admin/ops/ecosystem.html" in js
    assert 'href="/admin/"' not in html
    assert "Admin panel" not in html


def test_user_app_is_separate_from_admin() -> None:
    app = (Path(__file__).parents[2] / "web" / "app.html").read_text(encoding="utf-8")
    assert "Customer app" in app
    assert "bottom" in app
    assert 'data-action="quote"' in app
