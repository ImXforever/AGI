"""Manager ops console: ecosystem first, English HTML, gate, masked settings."""

from __future__ import annotations

from pathlib import Path

from app.config import _is_secret_field, _mask_secret

ROOT = Path(__file__).parents[2]
OPS = ROOT / "admin" / "ops"


def test_unauthenticated_html_redirects_to_public_home() -> None:
    src = (ROOT / "app" / "admin_api" / "gate.py").read_text(encoding="utf-8")
    assert 'UNAUTH_HTML_REDIRECT = "/"' in src
    assert "RedirectResponse(UNAUTH_HTML_REDIRECT" in src
    assert 'RedirectResponse("/admin/index.html"' not in src
    assert '"/admin/twa.html"' in src
    assert '"/admin/ops/login.html"' in src
    assert '"/admin/api/twa/"' in src
    assert '"/admin/api/auth/login"' in src
    assert '"/admin/ops/"' not in src.split("_PUBLIC_PREFIXES", 1)[1][:400]


def test_ecosystem_is_first_nav_and_english() -> None:
    build = (OPS / "_build.py").read_text(encoding="utf-8")
    assert '("ecosystem.html", "Ecosystem"' in build.split("NAV =", 1)[1][:400]
    html = (OPS / "ecosystem.html").read_text(encoding="utf-8")
    assert 'lang="en"' in html
    assert 'charset="utf-8"' in html
    assert 'id="eco-stage"' in html
    assert "TELEGRAM_BOT_TOKEN" not in html
    assert "âœ¦" not in html[:8000]
    js = (OPS / "ecosystem-view.js").read_text(encoding="utf-8")
    assert "HITL" in js
    assert "future agents inactive" in js
    assert "WhatsApp (optional)" in js


def test_login_never_opens_console_on_failure() -> None:
    login = (OPS / "login.html").read_text(encoding="utf-8")
    assert "demo console still opens" not in login
    assert 'if (r.ok) window.location.href = "ecosystem.html"' in login
    assert "Sign-in failed" in login
    assert 'action="ecosystem.html"' not in login
    index = (ROOT / "admin" / "index.html").read_text(encoding="utf-8")
    assert "/admin/ops/ecosystem.html" in index
    assert "Sign-in failed" in index


def test_variables_and_hitl_surface() -> None:
    settings = (OPS / "settings.html").read_text(encoding="utf-8")
    assert "settings-table" in settings
    assert "bot-status" in settings
    assert "TELEGRAM_BOT_TOKEN" not in settings
    js = (OPS / "ops.js").read_text(encoding="utf-8")
    assert "/auth/logout" in js
    assert "data-logout" in js
    assert "/approvals/" in js
    assert "/decide" in js
    queue = (OPS / "queue.html").read_text(encoding="utf-8")
    assert "queue-live" in queue
    twa = (ROOT / "admin" / "twa.html").read_text(encoding="utf-8")
    assert "/approvals/" in twa
    assert "/decide" in twa
    assert "Zenovix Ops" in twa
    assert "/decision" not in twa


def test_ops_command_palette_english_no_wallet() -> None:
    js = (OPS / "ops.js").read_text(encoding="utf-8")
    assert "Ctrl+K" in js
    assert "pal-ovl" in js
    assert "netBanner" in js
    assert "nav-badge" in js
    assert "queue.html" in js
    assert "/api/admin/deposits" not in js
    assert "/api/admin/withdrawals" not in js
    css = (OPS / "ops.css").read_text(encoding="utf-8")
    assert "#netBanner" in css
    assert ".pal-ovl" in css
    html = (OPS / "insights.html").read_text(encoding="utf-8")
    assert 'id="expJson"' in html
    assert "Ctrl+K" in html


def test_admin_settings_mask_secrets_not_admin_ids() -> None:
    assert _is_secret_field("telegram_bot_token")
    assert _is_secret_field("web_secret")
    assert not _is_secret_field("telegram_admin_ids")
    masked = _mask_secret("1234567890abcdef")
    assert masked.startswith("***")
    assert "1234567890" not in masked
