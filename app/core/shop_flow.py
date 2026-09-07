"""Telegram purchase flow (1.4.0): category → product → quantity → request.

Every step is an inline keyboard; the customer never types a SKU.  The last
step creates a *quote request*: a ``quotes`` row (status ``draft``) plus a
HITL approval that the manager decides with one tap in Telegram or in the
admin console.  Nothing is sold or charged here — approval is the gate.

The module only needs ``services`` (pg / redis / registry) and the parsed
:class:`~app.core.catalog_i18n.FlowAction`; it is called from the
orchestrator's command router.
"""

from __future__ import annotations

import json
import secrets
import time
from typing import Any

from app.core import catalog_i18n as ci
from app.core.catalog_i18n import FlowAction
from app.logging_setup import get_logger

log = get_logger("app.core.shop_flow")

_PENDING_QTY_KEY = "shop:qty:{sender_id}"
_PENDING_QTY_TTL = 900  # seconds a typed-quantity prompt stays valid


# ---------------------------------------------------------------------------
# Data access
# ---------------------------------------------------------------------------


async def load_catalog(pool: Any) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    """Active products (ordered) + category metadata keyed by category key."""
    products: list[dict[str, Any]] = []
    categories: dict[str, dict[str, Any]] = {}
    if pool is None:
        return products, categories
    try:
        rows = await pool.fetch(
            """
            SELECT id, sku, code, name_en, title_en, names, titles, name_ar, category, unit,
                   unit_price, base_price, currency, description_en, description_ar,
                   image_url, sort_order, stock_qty
            FROM products
            WHERE COALESCE(is_active, TRUE) = TRUE
            ORDER BY sort_order, name_en
            LIMIT 200
            """
        )
        products = [_row(r) for r in rows]
    except Exception as exc:
        log.warning(
            "catalog load failed", extra={"action": "shop.catalog", "error": str(exc)[:200]}
        )
        return [], {}
    try:
        crow = await pool.fetch(
            "SELECT key, name_en, names, icon, sort_order FROM catalog_categories WHERE is_active = TRUE"
        )
        categories = {str(r["key"]): _row(r) for r in crow}
    except Exception:
        categories = {}
    return products, categories


def _row(record: Any) -> dict[str, Any]:
    data = dict(record)
    for key in ("names", "titles", "descriptions"):
        raw = data.get(key)
        if isinstance(raw, (str, bytes)) and raw:
            try:
                data[key] = json.loads(raw)
            except (ValueError, TypeError):
                data[key] = {}
        elif raw is None:
            data[key] = {}
    for key in ("id", "code", "sku"):
        if data.get(key) is not None:
            data[key] = str(data[key])
    return data


def find_product(products: list[dict[str, Any]], code: str) -> dict[str, Any] | None:
    needle = (code or "").strip().lower()
    if not needle:
        return None
    for row in products:
        if (
            str(row.get("code") or "").lower() == needle
            or str(row.get("sku") or "").lower() == needle
        ):
            return row
    return None


async def load_product_image(pool: Any, product_id: str) -> bytes | None:
    """Image bytes uploaded from the admin console (product_images), if any."""
    if pool is None or not product_id:
        return None
    try:
        row = await pool.fetchrow(
            "SELECT data FROM product_images WHERE product_id = $1", product_id
        )
    except Exception:
        return None
    if row is None:
        return None
    data = row["data"]
    return bytes(data) if data else None


# ---------------------------------------------------------------------------
# Rendering helpers
# ---------------------------------------------------------------------------


def _visible_price_rows(products: list[dict[str, Any]], show_prices: bool) -> list[dict[str, Any]]:
    if show_prices:
        return products
    hidden = []
    for row in products:
        copy = dict(row)
        copy["unit_price"] = 0
        copy["base_price"] = 0
        hidden.append(copy)
    return hidden


def new_reference(prefix: str = "Q") -> str:
    return f"{(prefix or 'Q').strip().upper()[:6]}-{secrets.token_hex(3).upper()}"


# ---------------------------------------------------------------------------
# Flow steps
# ---------------------------------------------------------------------------


async def show_categories(
    *,
    adapter: Any,
    chat_id: str,
    lang: str,
    pool: Any,
    settings: dict[str, Any],
) -> None:
    products, categories = await load_catalog(pool)
    products = _visible_price_rows(products, bool(settings.get("bot_show_prices", True)))
    if not products:
        await adapter.send(recipient_id=chat_id, text=ci.t(lang, "empty"))
        return
    grouped = ci.group_by_category(products)
    if not settings.get("bot_order_flow", True) or not hasattr(adapter, "send_with_buttons"):
        await adapter.send(
            recipient_id=chat_id,
            text=ci.render_catalog(products, language=lang, categories=categories),
        )
        return
    header = f"{ci.t(lang, 'list_title')}\n{ci.t(lang, 'pick_category')}"
    await adapter.send_with_buttons(chat_id, header, ci.category_buttons(grouped, lang, categories))


async def show_products(
    *,
    adapter: Any,
    chat_id: str,
    lang: str,
    pool: Any,
    settings: dict[str, Any],
    category: str,
) -> None:
    products, categories = await load_catalog(pool)
    products = _visible_price_rows(products, bool(settings.get("bot_show_prices", True)))
    rows = [p for p in products if str(p.get("category") or "other") == category]
    if not rows:
        await show_categories(
            adapter=adapter, chat_id=chat_id, lang=lang, pool=pool, settings=settings
        )
        return
    meta = categories.get(category)
    title = ci.category_name(meta, category, lang)
    lines = [title, ""]
    for row in rows:
        lines.append("- " + ci.render_product_line(row, lang))
    lines.append("")
    lines.append(ci.t(lang, "pick_product"))
    await adapter.send_with_buttons(chat_id, "\n".join(lines), ci.product_buttons(rows, lang))


async def show_product(
    *,
    adapter: Any,
    chat_id: str,
    lang: str,
    pool: Any,
    settings: dict[str, Any],
    code: str,
) -> bool:
    products, _ = await load_catalog(pool)
    products = _visible_price_rows(products, bool(settings.get("bot_show_prices", True)))
    row = find_product(products, code)
    if row is None:
        return False
    text = ci.render_product_card(row, lang) + "\n\n" + ci.t(lang, "pick_qty")
    rows = ci.quantity_buttons(row, lang)
    if not settings.get("bot_custom_quantity", True):
        rows = [r for r in rows if not any(d.endswith("_custom") for _, d in r)]
    photo_bytes = None
    photo_url = None
    if settings.get("bot_show_images", True):
        photo_bytes = await load_product_image(pool, str(row.get("id") or ""))
        url = str(row.get("image_url") or "").strip()
        if not photo_bytes and url.startswith("http"):
            photo_url = url
    await adapter.send_with_buttons(
        chat_id, text, rows, photo_url=photo_url, photo_bytes=photo_bytes
    )
    return True


async def ask_quantity(
    *,
    adapter: Any,
    chat_id: str,
    sender_id: str,
    lang: str,
    redis: Any,
    code: str,
) -> None:
    if redis is not None:
        try:
            await redis.set(_PENDING_QTY_KEY.format(sender_id=sender_id), code, ex=_PENDING_QTY_TTL)
        except Exception:
            pass
    await adapter.send(recipient_id=chat_id, text=ci.t(lang, "qty_prompt"))


async def pending_quantity_code(redis: Any, sender_id: str) -> str:
    if redis is None or not sender_id:
        return ""
    try:
        raw = await redis.get(_PENDING_QTY_KEY.format(sender_id=sender_id))
    except Exception:
        return ""
    if not raw:
        return ""
    return raw.decode() if isinstance(raw, bytes) else str(raw)


async def clear_pending_quantity(redis: Any, sender_id: str) -> None:
    if redis is None or not sender_id:
        return
    try:
        await redis.delete(_PENDING_QTY_KEY.format(sender_id=sender_id))
    except Exception:
        pass


async def show_confirmation(
    *,
    adapter: Any,
    chat_id: str,
    lang: str,
    pool: Any,
    settings: dict[str, Any],
    code: str,
    quantity: int,
) -> bool:
    products, _ = await load_catalog(pool)
    products = _visible_price_rows(products, bool(settings.get("bot_show_prices", True)))
    row = find_product(products, code)
    if row is None:
        return False
    minimum = int(settings.get("quote_min_quantity") or 1)
    quantity = max(minimum, int(quantity))
    text = ci.t(lang, "confirm") + "\n\n" + ci.order_summary(row, quantity, lang)
    await adapter.send_with_buttons(chat_id, text, ci.confirm_buttons(row, quantity, lang))
    return True


async def submit_request(
    *,
    services: dict[str, Any],
    adapter: Any,
    chat_id: str,
    sender_id: str,
    sender_name: str,
    channel: str,
    lang: str,
    conversation_id: str,
    customer_id: str,
    settings: dict[str, Any],
    code: str,
    quantity: int,
) -> str | None:
    """Create quote (draft) + approval, notify managers, thank the customer."""
    pool = services.get("pg")
    products, _ = await load_catalog(pool)
    row = find_product(products, code)
    if row is None or pool is None:
        return None

    from app.core.repository import create_approval

    currency = str(settings.get("quote_currency") or row.get("currency") or "USD")
    unit_price = ci.product_price(row) if settings.get("bot_show_prices", True) else 0.0
    line_total = round(unit_price * quantity, 2)
    reference = new_reference(str(settings.get("quote_reference_prefix") or "Q"))
    summary = ci.order_summary(row, quantity, lang)
    summary_en = ci.order_summary(row, quantity, "en")

    approval_id = await create_approval(
        pg=pool,
        conversation_id=conversation_id,
        customer_id=customer_id,
        skill="sales_agent",
        intent="quote_request",
        draft_text=ci.t(lang, "approved", ref=reference, summary=summary),
        confidence=1.0,
        needs_hitl=True,
    )

    payload = {
        "action": "create_quote",
        "type": "quote_request",
        "reference": reference,
        "channel": channel,
        "recipient_id": sender_id,
        "sender_name": sender_name,
        "language": lang,
        "customer_id": customer_id,
        "product_id": str(row.get("id") or ""),
        "product_code": ci.product_code(row),
        "product_name": ci.product_name(row, "en"),
        "quantity": quantity,
        "unit": str(row.get("unit") or ""),
        "unit_price": unit_price,
        "total": line_total,
        "currency": currency,
        "summary_en": summary_en,
        "text": ci.t(lang, "approved", ref=reference, summary=summary),
        "rejected_text": ci.t(lang, "rejected", ref=reference),
    }
    try:
        await pool.execute(
            "UPDATE approvals SET channel = $2, payload = $3::jsonb WHERE id = $1",
            approval_id,
            channel,
            json.dumps(payload, ensure_ascii=False),
        )
    except Exception as exc:
        log.warning(
            "approval payload update failed",
            extra={"action": "shop.submit", "error": str(exc)[:200]},
        )

    quote_id = None
    try:
        quote_id = await pool.fetchval(
            """
            INSERT INTO quotes (customer_id, conversation_id, status, items, subtotal, tax, total,
                                currency, notes, reference, channel, approval_id, language)
            VALUES ($1, $2, 'draft', $3::jsonb, $4, 0, $4, $5, $6, $7, $8, $9, $10)
            RETURNING id
            """,
            customer_id or None,
            conversation_id or None,
            json.dumps(
                [
                    {
                        "product_id": str(row.get("id") or ""),
                        "code": ci.product_code(row),
                        "sku": str(row.get("sku") or ""),
                        "name": ci.product_name(row, "en"),
                        "quantity": quantity,
                        "unit": str(row.get("unit") or ""),
                        "unit_price": unit_price,
                        "line_total": line_total,
                    }
                ],
                ensure_ascii=False,
            ),
            line_total,
            currency,
            f"Telegram request by {sender_name or sender_id}",
            reference,
            channel,
            approval_id,
            lang,
        )
    except Exception as exc:
        log.warning("quote insert failed", extra={"action": "shop.submit", "error": str(exc)[:200]})

    # Manager alert with one-tap buttons.
    if settings.get("notify_new_request", True):
        from app.config import get_config
        from app.core.hitl.notify import notify_pending

        cfg = get_config()
        registry = services.get("registry")
        tg = registry.get("telegram") if registry else None
        await notify_pending(
            approval_id=approval_id,
            action="quote_request",
            snippet=f"{reference} · {sender_name or sender_id}\n{summary_en}",
            skill="sales_agent",
            admin_ids=cfg.channels.telegram_admin_ids,
            adapter=tg,
            ping=cfg.hitl.ping_telegram,
            buttons=True,
        )

    # Redis meta so the sweeper / decide path know channel + customer.
    redis = services.get("redis")
    if redis is not None:
        try:
            await redis.hset(
                f"hitl:meta:{approval_id}",
                mapping={
                    "status": "pending",
                    "conversation_id": conversation_id,
                    "customer_id": customer_id,
                    "channel": channel,
                    "skill": "sales_agent",
                    "reference": reference,
                    "created_at": str(int(time.time())),
                },
            )
            await redis.expire(f"hitl:meta:{approval_id}", 86400 * 7)
        except Exception:
            pass

    await adapter.send(recipient_id=chat_id, text=ci.t(lang, "sent", ref=reference))
    log.info(
        "quote request submitted",
        extra={
            "action": "shop.submit",
            "approval_id": approval_id,
            "quote_id": str(quote_id or ""),
            "reference": reference,
            "code": ci.product_code(row),
            "quantity": quantity,
        },
    )
    return approval_id


async def my_requests_text(pool: Any, customer_id: str, lang: str) -> str:
    """Status list for the customer's own requests (last 5)."""
    if pool is None or not customer_id:
        return ci.t(lang, "empty")
    try:
        rows = await pool.fetch(
            """
            SELECT q.reference, q.status, q.total, q.currency, q.created_at, a.status AS approval_status
            FROM quotes q LEFT JOIN approvals a ON a.id = q.approval_id
            WHERE q.customer_id = $1 AND q.reference IS NOT NULL
            ORDER BY q.created_at DESC LIMIT 5
            """,
            customer_id,
        )
    except Exception:
        rows = []
    if not rows:
        return ci.t(lang, "no_requests")
    lines = [ci.t(lang, "my_requests_title")]
    for r in rows:
        state = str(r["approval_status"] or r["status"] or "pending")
        badge = {"approved": "✅", "edited": "✅", "rejected": "✖", "pending": "⏳"}.get(state, "•")
        total = ci.format_money(r["total"], str(r["currency"] or "USD"), lang)
        lines.append(f"{badge} {r['reference']} · {total} · {state}")
    return "\n".join(lines)


async def handle(
    action: FlowAction,
    *,
    services: dict[str, Any],
    adapter: Any,
    chat_id: str,
    sender_id: str,
    sender_name: str,
    channel: str,
    lang: str,
    conversation_id: str,
    customer_id: str,
    settings: dict[str, Any],
) -> dict[str, Any]:
    """Dispatch one flow action. Returns ``{"handled": bool, "approval_id": ...}``."""
    pool = services.get("pg")
    redis = services.get("redis")
    out: dict[str, Any] = {"handled": True, "approval_id": None}
    common = {
        "adapter": adapter,
        "chat_id": chat_id,
        "lang": lang,
        "pool": pool,
        "settings": settings,
    }

    if action.kind == "categories":
        await show_categories(**common)
    elif action.kind == "products":
        await show_products(category=action.category, **common)
    elif action.kind == "product":
        if not await show_product(code=action.code, **common):
            await show_categories(**common)
    elif action.kind == "ask_qty":
        await ask_quantity(
            adapter=adapter,
            chat_id=chat_id,
            sender_id=sender_id,
            lang=lang,
            redis=redis,
            code=action.code,
        )
    elif action.kind == "confirm":
        if not await show_confirmation(code=action.code, quantity=action.quantity, **common):
            await show_categories(**common)
    elif action.kind == "submit":
        await clear_pending_quantity(redis, sender_id)
        out["approval_id"] = await submit_request(
            services=services,
            adapter=adapter,
            chat_id=chat_id,
            sender_id=sender_id,
            sender_name=sender_name,
            channel=channel,
            lang=lang,
            conversation_id=conversation_id,
            customer_id=customer_id,
            settings=settings,
            code=action.code,
            quantity=action.quantity,
        )
        if out["approval_id"] is None:
            await show_categories(**common)
    elif action.kind == "cancel":
        await clear_pending_quantity(redis, sender_id)
        await adapter.send(recipient_id=chat_id, text=ci.t(lang, "cancelled"))
    else:
        out["handled"] = False
    return out
