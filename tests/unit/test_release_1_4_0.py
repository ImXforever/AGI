"""Release tests for 1.4.0 — English-first catalog, order flow, one-tap approvals.

Pure contracts only (no config, no database): the per-language renderer, the
callback protocol of the purchase flow, business-variable validation, the
approval-notice buttons, the desk summary and the static console/app files.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.core import catalog_i18n as ci
from app.core.business_settings import SPEC_BY_KEY, SettingError, coerce, merge, validate
from app.core.hitl.notify import (
    build_pending_notice,
    decision_buttons,
    parse_decision_callback,
)

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[2]

DIESEL = {
    "id": "p-203",
    "sku": "EGL-PRD-DIESEL10",
    "code": "203",
    "name_en": "Diesel 10 PPM",
    "title_en": "Ultra-low sulphur diesel",
    "names": {"tr": "Dizel 10 PPM", "fa": "دیزل ۱۰ پی‌پی‌ام"},
    "titles": {"tr": "Ultra düşük kükürtlü dizel"},
    "name_ar": "ديزل قديم",
    "category": "clean-oils",
    "unit": "metric ton",
    "unit_price": 640,
    "currency": "USD",
}
STORAGE = {
    "id": "p-101",
    "sku": "EGL-SVC-STORAGE",
    "code": "101",
    "name_en": "Fujairah Terminal Storage",
    "names": json.dumps({"ar": "تخزين محطة الفجيرة"}),  # jsonb may arrive as str
    "category": "services",
    "unit": "service",
    "unit_price": 0,
    "currency": "USD",
}


# ---------------------------------------------------------------------------
# English-first reference + per-language display
# ---------------------------------------------------------------------------


def test_english_is_the_reference_and_other_languages_are_display() -> None:
    assert ci.product_name(DIESEL, "en") == "Diesel 10 PPM"
    assert ci.product_name(DIESEL, "tr") == "Dizel 10 PPM"
    assert ci.product_name(DIESEL, "fa") == "دیزل ۱۰ پی‌پی‌ام"
    # No German translation → English, never the legacy Arabic column.
    assert ci.product_name(DIESEL, "de") == "Diesel 10 PPM"
    # Arabic falls back to English too when name_en exists (legacy name_ar is last resort).
    assert ci.product_name(DIESEL, "ar") == "Diesel 10 PPM"
    assert ci.product_name({"name_ar": "قديم", "sku": "X"}, "ar") == "قديم"


def test_jsonb_string_translations_are_decoded() -> None:
    assert ci.product_name(STORAGE, "ar") == "تخزين محطة الفجيرة"
    assert ci.product_title(DIESEL, "tr") == "Ultra düşük kükürtlü dizel"
    assert ci.product_title(DIESEL, "ru") == "Ultra-low sulphur diesel"


def test_render_catalog_is_clean_per_language() -> None:
    cats = {
        "services": {
            "name_en": "Services",
            "names": {"tr": "Hizmetler"},
            "icon": "⚓",
            "sort_order": 10,
        },
        "clean-oils": {
            "name_en": "Clean products",
            "names": {"tr": "Beyaz ürünler"},
            "sort_order": 20,
        },
    }
    tr = ci.render_catalog([DIESEL, STORAGE], language="tr", categories=cats)
    assert "Hizmetler" in tr and "Beyaz ürünler" in tr
    assert "203 · Dizel 10 PPM — 640 USD / ton" in tr
    assert "101 · Fujairah Terminal Storage — fiyat talep üzerine" in tr
    assert tr.index("Hizmetler") < tr.index("Beyaz ürünler")  # sort_order respected
    for forbidden in ("**", "list_products", "SKU", "{", "}"):
        assert forbidden not in tr
    ar = ci.render_catalog([DIESEL], language="ar")
    assert "203" in ar and "Diesel 10 PPM" in ar and "دولار" not in ar
    assert ci.render_catalog([], language="fa") == ci.t("fa", "empty")


def test_every_language_table_falls_back_to_english() -> None:
    for lang in ("en", "fa", "ar", "tr", "de", "fr", "es", "ru", "it", "zz"):
        for key in ("pick_category", "confirm_btn", "sent", "approved", "no_requests"):
            text = ci.t(lang, key, ref="Q-1", summary="s")
            assert text and text != key


def test_money_and_quantity_formatting() -> None:
    assert ci.format_money(1250, "USD", "en") == "1,250 USD"
    assert ci.format_money(12.5, "USD", "en") == "12.5 USD"
    assert ci.format_money(0, "USD", "fa") == ci.t("fa", "price_on_request")
    assert ci.format_quantity(5000, "metric ton", "en") == "5,000 MT"
    assert ci.format_quantity(1, "service", "tr") == "1 hizmet"


# ---------------------------------------------------------------------------
# Purchase flow protocol (category → product → quantity → request)
# ---------------------------------------------------------------------------


def test_callback_protocol_round_trips() -> None:
    assert ci.parse_callback("shop").kind == "categories"
    assert ci.parse_callback("menu_prices").kind == "categories"
    act = ci.parse_callback("cat_clean-oils")
    assert act.kind == "products" and act.category == "clean-oils"
    act = ci.parse_callback("prod_203")
    assert act.kind == "product" and act.code == "203"
    act = ci.parse_callback("qty_203_500")
    assert act.kind == "confirm" and act.code == "203" and act.quantity == 500
    assert ci.parse_callback("qty_203_custom").kind == "ask_qty"
    act = ci.parse_callback("ord_203_500")
    assert act.kind == "submit" and act.quantity == 500
    assert ci.parse_callback("ord_cancel").kind == "cancel"
    assert ci.parse_callback("apr_ok_x").kind == "unknown"
    assert ci.parse_callback("").kind == "unknown"


def test_buttons_keep_telegram_limits_and_back_navigation() -> None:
    grouped = ci.group_by_category([DIESEL, STORAGE])
    rows = ci.category_buttons(grouped, "fa")
    assert rows[-1][0][1] == "menu_home"
    assert all(len(data.encode()) <= 64 for row in rows for _, data in row)

    rows = ci.product_buttons([DIESEL], "tr")
    assert rows[0][0] == ("203 · Dizel 10 PPM", "prod_203")
    assert ("Geri", "shop") in rows[-1]

    rows = ci.quantity_buttons(DIESEL, "en")
    datas = [d for row in rows for _, d in row]
    assert "qty_203_500" in datas and "qty_203_custom" in datas and "cat_clean-oils" in datas
    # services: one preset, no custom quantity
    rows = ci.quantity_buttons(STORAGE, "en")
    datas = [d for row in rows for _, d in row]
    assert "qty_101_1" in datas and not any(d.endswith("_custom") for d in datas)

    rows = ci.confirm_buttons(DIESEL, 500, "ar")
    assert rows[0][0][1] == "ord_203_500"
    assert ("إلغاء", "ord_cancel") in rows[1]


def test_quantity_parsing_accepts_local_digits_and_rejects_garbage() -> None:
    assert ci.parse_quantity("500") == 500
    assert ci.parse_quantity("1,000") == 1000
    assert ci.parse_quantity("۵۰۰ تن") == 500
    assert ci.parse_quantity("٢٠٠٠") == 2000
    assert ci.parse_quantity("about 5000 please") == 5000
    assert ci.parse_quantity("zero") is None
    assert ci.parse_quantity("0") is None
    assert ci.parse_quantity("-4") is None
    assert ci.parse_quantity("99999999999") is None


def test_product_card_and_summary_render_in_customer_language() -> None:
    card = ci.render_product_card(DIESEL, "fa")
    assert "دیزل ۱۰ پی‌پی‌ام" in card and "کد: 203" in card and "640 USD / تن" in card
    summary = ci.order_summary(DIESEL, 500, "en")
    assert "Diesel 10 PPM (Code 203)" in summary
    assert "Quantity: 500 MT" in summary
    assert "Price: 320,000 USD" in summary
    summary = ci.order_summary(STORAGE, 1, "de")
    assert ci.t("de", "price_on_request") in summary


# ---------------------------------------------------------------------------
# Manager one-tap approvals
# ---------------------------------------------------------------------------


def test_decision_buttons_and_parser() -> None:
    rows = decision_buttons("ap-9")
    assert rows[0][0][1] == "apr_ok_ap-9" and rows[0][1][1] == "apr_no_ap-9"
    assert parse_decision_callback("apr_ok_ap-9") == ("approved", "ap-9")
    assert parse_decision_callback("apr_no_ap-9") == ("rejected", "ap-9")
    assert parse_decision_callback("apr_open_ap-9") == ("open", "ap-9")
    assert parse_decision_callback("prod_203") is None
    text = build_pending_notice(
        approval_id="ap-9", action="quote_request", snippet="Q-1 · Ali\nDiesel · 500 MT"
    )
    assert "ap-9" in text and "quote_request" in text and "Diesel · 500 MT" in text


def test_decide_customer_text_prefers_edit_then_status() -> None:
    from app.core.hitl.decide import customer_text_for

    payload = {"text": "approved text", "rejected_text": "sorry text"}
    assert customer_text_for("approved", payload, "draft", None) == "approved text"
    assert customer_text_for("rejected", payload, "draft", None) == "sorry text"
    assert (
        customer_text_for("edited", payload, "draft", {"text": "manager wrote this"})
        == "manager wrote this"
    )
    assert customer_text_for("approved", {}, "draft only", None) == "draft only"


def test_desk_summary_is_readable() -> None:
    from app.admin_api.desk import approval_summary

    row = {
        "id": "a1",
        "conversation_id": "c1",
        "channel": "telegram",
        "payload": json.dumps(
            {
                "type": "quote_request",
                "reference": "Q-7F3A2B",
                "sender_name": "Ali",
                "product_name": "Diesel 10 PPM",
                "quantity": 500,
                "unit": "metric ton",
                "total": 320000,
                "currency": "USD",
                "language": "fa",
            }
        ),
        "created_at": None,
    }
    card = approval_summary(row)
    assert card["who"] == "Ali" and card["reference"] == "Q-7F3A2B"
    assert card["what"] == "Diesel 10 PPM · 500 metric ton"
    assert card["amount"] == "320,000.00 USD"
    assert card["severity"] == "high" and card["language"] == "fa"
    plain = approval_summary(
        {"id": "a2", "payload": {}, "draft_text": "hello", "skill": "support_agent"}
    )
    assert plain["kind"] == "support_agent" and plain["what"] == "hello" and plain["amount"] is None


def test_web_app_data_maps_to_bot_commands() -> None:
    from app.channels.telegram import TelegramAdapter, _web_app_command

    assert _web_app_command('{"v":1,"action":"products","code":"203"}') == "/prod_203"
    assert _web_app_command('{"v":1,"action":"products"}') == "/shop"
    assert _web_app_command('{"v":1,"action":"support"}') == "/menu_support"
    assert _web_app_command('{"v":1,"action":"quote"}') == "/menu_quote"
    assert _web_app_command('{"action":"products","code":"<script>"}') == "/prod_script"
    assert _web_app_command("not json") == ""
    markup = TelegramAdapter.inline_keyboard([[("x" * 90, "d" * 90)], []])
    btn = markup["inline_keyboard"][0][0]
    assert len(btn["text"]) == 64 and len(btn["callback_data"].encode()) == 64
    assert len(markup["inline_keyboard"]) == 1


# ---------------------------------------------------------------------------
# Business variables (settings table, validated)
# ---------------------------------------------------------------------------


def test_business_settings_validation() -> None:
    assert coerce(SPEC_BY_KEY["bot_show_prices"], "false") is False
    assert coerce(SPEC_BY_KEY["bot_languages"], "en, TR ,fa,en") == ["en", "tr", "fa"]
    assert coerce(SPEC_BY_KEY["quote_tax_rate"], "0.05") == 0.05
    assert coerce(SPEC_BY_KEY["quote_tax_rate"], "") is None
    with pytest.raises(SettingError):
        coerce(SPEC_BY_KEY["quote_tax_rate"], "5")
    with pytest.raises(SettingError):
        coerce(SPEC_BY_KEY["bot_languages"], "en,klingon")
    with pytest.raises(SettingError):
        coerce(SPEC_BY_KEY["bot_default_language"], "xx")
    with pytest.raises(SettingError):
        validate({"not_a_setting": 1})
    merged = merge({"bot_show_prices": False, "junk": 1, "quote_tax_rate": "bad"})
    assert merged["bot_show_prices"] is False
    assert merged["quote_tax_rate"] is None
    assert "junk" not in merged
    assert merged["company_short"] == "ZX"


def test_translations_cover_new_buttons_in_all_menu_languages() -> None:
    from app.core.translations import BUTTONS, MENUS, get_button_text

    for lang in ("en", "fa", "ar", "es", "fr", "de", "tr", "ru"):
        for key in ("shop", "my_requests", "back", "new_ticket", "call", "hours"):
            assert BUTTONS[lang][key]
        for key in ("talk_sales", "faq", "contact_missing", "waiting_manager"):
            assert MENUS[lang][key]
    assert get_button_text("it", "back") == BUTTONS["en"]["back"]


# ---------------------------------------------------------------------------
# Static surfaces: console, app, migration, seed
# ---------------------------------------------------------------------------


def test_console_has_desk_catalog_and_variables_pages() -> None:
    ops = ROOT / "admin" / "ops"
    build = (ops / "_build.py").read_text(encoding="utf-8")
    assert '("ecosystem.html", "Ecosystem"' in build.split("NAV =", 1)[1][:400]
    assert '("catalog.html", "Catalog"' in build and '("index.html", "Desk"' in build
    assert "NAV_MORE" in build and "Zenovix Ops 1.6.0" in build
    index = (ops / "index.html").read_text(encoding="utf-8")
    assert (
        'id="desk-pending"' in index and 'id="desk-recent"' in index and 'id="desk-system"' in index
    )
    catalog = (ops / "catalog.html").read_text(encoding="utf-8")
    assert (
        'id="prod-form"' in catalog and 'name="name_en"' in catalog and 'id="prod-file"' in catalog
    )
    assert 'id="cat-form"' in catalog
    settings = (ops / "settings.html").read_text(encoding="utf-8")
    assert 'id="variables"' in settings and 'id="vars-save"' in settings
    assert "settings-table" in settings and "bot-status" in settings
    js = (ops / "ops.js").read_text(encoding="utf-8")
    assert "/desk" in js and "/settings/business" in js and "/catalog/categories" in js
    assert "/products/" in js and "/image" in js
    css = (ops / "ops.css").read_text(encoding="utf-8")
    assert (
        ".panel-head" in css
        and ".event-row" in css
        and ".led-row" in css
        and "JetBrains Mono" in css
    )
    for name in ("index.html", "catalog.html", "settings.html", "queue.html"):
        html = (ops / name).read_text(encoding="utf-8")
        assert "TELEGRAM_BOT_TOKEN" not in html
        assert 'data-theme="neon"' in html and 'data-theme="light"' in html


def test_customer_app_shows_live_catalog_without_admin_data() -> None:
    app = (ROOT / "web" / "app.html").read_text(encoding="utf-8")
    assert "Customer app" in app and 'id="cat-list"' in app and 'data-action="quote"' in app
    assert "ecosystem" not in app.lower() and "/admin/ops" not in app
    js = (ROOT / "web" / "js" / "public.js").read_text(encoding="utf-8")
    assert "/api/public/catalog" in js and "data-order" in js and "sendData" in js
    assert "/admin/api/catalog" not in js


def test_migration_0017_and_seed_are_english_first() -> None:
    sql = (ROOT / "db" / "migrations" / "0017_catalog_i18n_orders.sql").read_text(encoding="utf-8")
    for column in ("code", "title_en", "names", "titles", "image_url", "sort_order"):
        assert f"ADD COLUMN IF NOT EXISTS {column}" in sql
    assert "CREATE TABLE IF NOT EXISTS product_images" in sql
    assert "CREATE TABLE IF NOT EXISTS catalog_categories" in sql
    assert "preferred_language" in sql and "approval_id" in sql
    assert "DROP TABLE" not in sql and "DROP COLUMN" not in sql
    rows = json.loads((ROOT / "db" / "seed" / "001_products.json").read_text(encoding="utf-8"))
    codes = [r["code"] for r in rows]
    assert len(codes) == len(set(codes)) == 6
    for r in rows:
        assert r["name_en"] and r["title_en"] and r["image_url"].startswith("/web/assets/img/")
        assert r["currency"] == "USD"
        assert {"fa", "ar", "tr", "de", "fr", "es", "ru"} <= set(r["names"])
        assert (ROOT / r["image_url"].lstrip("/")).is_file()
    cats = json.loads(
        (ROOT / "db" / "seed" / "006_catalog_categories.json").read_text(encoding="utf-8")
    )
    assert {c["key"] for c in cats} == {r["category"] for r in rows}
    from app.storage.schema_guard import REQUIRED_SCHEMA
    from app.storage.seed import _conflict_column

    assert _conflict_column("catalog_categories", ["key", "name_en"]) == "key"
    assert (
        "code" in REQUIRED_SCHEMA["products"]
        and "preferred_language" in REQUIRED_SCHEMA["customers"]
    )


def test_version_is_1_4_0_everywhere() -> None:
    import tomllib

    from app.constants import APP_VERSION

    assert APP_VERSION == "1.6.0"
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert project["project"]["version"] == "1.6.0"
    assert (ROOT / "README.md").read_text(encoding="utf-8").startswith(
        "<!--"
    ) or "Zenovix 1.6.0" in (ROOT / "README.md").read_text(encoding="utf-8")[:400]
