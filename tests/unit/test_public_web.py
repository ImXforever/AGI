"""Public landing + customer Mini App contracts (no admin leak)."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).parents[2]
WEB = ROOT / "web"


def _read(*parts: str) -> str:
    return WEB.joinpath(*parts).read_text(encoding="utf-8")


def test_public_html_is_english_utf8_without_mojibake() -> None:
    for name in ("index.html", "app.html"):
        html = _read(name)
        assert 'lang="en"' in html
        assert 'charset="utf-8"' in html
        assert "âœ¦" not in html
        assert "â˜°" not in html
        assert "â†—" not in html
        assert "TELEGRAM_BOT_TOKEN" not in html
        assert "BOT_TOKEN" not in html


def test_visitor_never_sees_login_without_hidden() -> None:
    html = _read("index.html")
    assert "data-admin-login" in html
    assert "hidden" in html
    assert "Admin panel" not in html
    assert "/admin/ops/ecosystem.html" in html  # target after TWA admin login only


def test_senddata_is_action_only() -> None:
    js = _read("js", "public.js")
    assert "tg.sendData" in js
    assert "actionPayload" in js
    assert "TELEGRAM_BOT_TOKEN" not in js
    assert "initData" in js  # TWA admin probe only
    assert "/config/snapshot" not in js
    assert "/admin/api/" in js  # probe/login, not ops data


def test_mini_app_is_not_admin() -> None:
    app = _read("app.html")
    assert "Customer app" in app
    assert "ecosystem" not in app.lower()
    assert 'data-action="quote"' in app
    js = _read("js", "public.js")
    assert "Open the customer app from Telegram" in js or "sendData" in js


def test_main_serves_utf8_public_routes() -> None:
    main = (ROOT / "app" / "main.py").read_text(encoding="utf-8")
    assert 'media_type="text/html; charset=utf-8"' in main
    assert '"/app"' in main
