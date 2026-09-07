"""Public website endpoints — the Zenovix landing page talks to these.

Unauthenticated by design (they sit outside ``/admin``), so every input is
validated, size-capped and rate-limited, and nothing here can read business
data back out: the enquiry endpoint only *creates* a lead (customer + ticket)
and the chat endpoint only answers from the approved knowledge base through
the same guarded pipeline the Telegram bot uses.
"""

from __future__ import annotations

import re
import time
import uuid
from typing import Any

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel, Field, field_validator

from app.config import get_config
from app.constants import APP_VERSION, CHANNEL_TELEGRAM, CHANNEL_WEB
from app.logging_setup import get_logger

log = get_logger("app.gateway.public_site")

router = APIRouter(prefix="/api/public", tags=["public-site"])


_EMAIL_RE = re.compile(r"^[^\s@]{1,64}@[^\s@]{1,255}\.[A-Za-z]{2,24}$")
_PHONE_RE = re.compile(r"^[+\d][\d\s().-]{5,24}$")

SERVICES = (
    "Artificial Intelligence",
    "Cloud & ICT",
    "Web & Mobile",
    "Intelligent Automation",
    "Data & Analytics",
    "Animation & 3D",
    "Other",
)

# Per-IP budget for the public endpoints (sliding window in Redis).
ENQUIRY_LIMIT_PER_HOUR = 6
CHAT_LIMIT_PER_MINUTE = 10


class EnquiryIn(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: str = Field(min_length=5, max_length=254)
    company: str = Field(default="", max_length=160)
    phone: str = Field(default="", max_length=40)
    service: str = Field(default="Other", max_length=80)
    message: str = Field(min_length=10, max_length=4000)
    # Honeypot — real visitors never fill this; bots do.
    website: str = Field(default="", max_length=200)

    @field_validator("name", "company", "phone", "service", "message", mode="before")
    @classmethod
    def _strip(cls, v: Any) -> Any:
        return v.strip() if isinstance(v, str) else v

    @field_validator("email", mode="before")
    @classmethod
    def _email(cls, v: Any) -> Any:
        v = (v or "").strip().lower() if isinstance(v, str) else v
        if not isinstance(v, str) or not _EMAIL_RE.match(v):
            raise ValueError("a valid e-mail address is required")
        return v

    @field_validator("phone")
    @classmethod
    def _phone(cls, v: str) -> str:
        if v and not _PHONE_RE.match(v):
            raise ValueError("phone number looks invalid")
        return v

    @field_validator("service")
    @classmethod
    def _service(cls, v: str) -> str:
        return v if v in SERVICES else "Other"


class ChatIn(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    session: str = Field(default="", max_length=64)

    @field_validator("session")
    @classmethod
    def _session(cls, v: str) -> str:
        v = (v or "").strip()
        return v if re.fullmatch(r"[A-Za-z0-9_-]{0,64}", v) else ""


def _client_ip(request: Request) -> str:
    fwd = request.headers.get("x-forwarded-for", "")
    if fwd:
        return fwd.split(",")[0].strip()[:64]
    return (request.client.host if request.client else "unknown")[:64]


async def _rate_limit(kind: str, key: str, *, window: int, limit: int) -> None:
    """Fail closed with 429; a Redis outage must not open the endpoint."""
    from app.storage.redis import check_rate_limit

    try:
        allowed, _remaining, retry_after = await check_rate_limit(
            f"web-{kind}", key, window=window, limit=limit
        )
    except Exception as exc:
        log.warning("public_rate_limit_unavailable", extra={"action": kind, "error": str(exc)})
        raise HTTPException(status_code=503, detail="temporarily unavailable") from exc
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail="too many requests — please try again shortly",
            headers={"Retry-After": str(int(retry_after) or 60)},
        )


def format_lead_alert(
    *,
    reference: str,
    name: str,
    company: str,
    email: str,
    phone: str,
    service: str,
    message: str,
) -> str:
    """Plain-text Telegram alert for a new website lead (1.3.1 option).

    Plain text on purpose: ``notify_admins`` HTML-escapes the body, so no
    customer-supplied text can inject Telegram markup.
    """
    snippet = " ".join((message or "").split())
    if len(snippet) > 300:
        snippet = snippet[:297].rstrip() + "..."
    lines = [
        f"New website lead {reference}",
        f"Name: {name}",
        f"Company: {company or '-'}",
        f"E-mail: {email}",
        f"Phone: {phone or '-'}",
        f"Service: {service}",
        "",
        snippet,
        "",
        "Open the ticket in the admin panel: /admin/ops/support.html",
    ]
    return "\n".join(lines)


async def _send_lead_alert(services: dict[str, Any], text: str) -> bool:
    """Push *text* to the Telegram managers if the option is on.

    Returns True when an alert was handed to the adapter. Any failure is
    logged and swallowed — the enquiry itself is already stored.
    """
    try:
        cfg = get_config()
    except Exception:  # noqa: BLE001 - config unavailable in some test rigs
        return False
    if not cfg.domain.lead_alert_enabled:
        return False
    registry = services.get("registry")
    adapter = registry.get(CHANNEL_TELEGRAM) if registry is not None else None
    notify = getattr(adapter, "notify_admins", None)
    if notify is None:
        log.info("lead_alert_skipped", extra={"action": "lead_alert", "reason": "no telegram"})
        return False
    try:
        await notify(text)
    except Exception as exc:  # noqa: BLE001 - alert must never break the form
        log.warning("lead_alert_failed", extra={"action": "lead_alert", "error": str(exc)})
        return False
    log.info("lead_alert_sent", extra={"action": "lead_alert", "channel": CHANNEL_TELEGRAM})
    return True


@router.get("/site")
async def site_info() -> dict[str, Any]:
    """Non-secret tenant facts the page renders (name, currency, services)."""
    try:
        cfg = get_config()
        tenant = cfg.tenant.name_en or cfg.tenant.id
        currency = cfg.domain.currency
    except Exception:  # config not loaded (e.g. unit tests) — never 500 the page
        tenant, currency = "Zenovix", "USD"
    return {
        "tenant": tenant,
        "currency": currency,
        "services": list(SERVICES),
        "agent": "Zenovix",
        "version": APP_VERSION,
    }


@router.get("/catalog")
async def public_catalog(request: Request, lang: str = "en") -> dict[str, Any]:
    """Active products for the customer app, rendered in *lang* (1.4.0).

    Only display fields leave the server: code, name, title, category, unit,
    price (or ``null`` when the manager hides prices) and an image URL. No
    SKUs, stock or internal ids.
    """
    from app.core import catalog_i18n as ci
    from app.core.business_settings import load_settings
    from app.core.shop_flow import load_catalog

    services: dict[str, Any] = getattr(request.app.state, "services", {}) or {}
    pool = services.get("pg")
    code = (lang or "en").lower().strip()[:5]
    if pool is None:
        return {"language": code, "categories": [], "items": [], "currency": "USD"}
    settings = await load_settings(pool)
    show_prices = bool(settings.get("bot_show_prices", True))
    products, categories = await load_catalog(pool)
    grouped = ci.group_by_category(products)
    cats = []
    for key in ci.order_categories(list(grouped), categories):
        meta = categories.get(key)
        cats.append(
            {
                "key": key,
                "name": ci.category_name(meta, key, code),
                "icon": str((meta or {}).get("icon") or ""),
                "count": len(grouped[key]),
            }
        )
    items = []
    for row in products:
        price = ci.product_price(row) if show_prices else 0.0
        image = str(row.get("image_url") or "")
        if image.startswith("/admin/"):
            image = f"/api/public/catalog/{ci.product_code(row)}/image"
        items.append(
            {
                "code": ci.product_code(row),
                "name": ci.product_name(row, code),
                "title": ci.product_title(row, code),
                "category": str(row.get("category") or "other"),
                "unit": ci.unit_label(str(row.get("unit") or ""), code),
                "price": price if price > 0 else None,
                "price_text": ci.format_money(price, str(row.get("currency") or "USD"), code),
                "image": image,
            }
        )
    return {
        "language": code,
        "rtl": code in ci.RTL_LANGUAGES,
        "currency": str(settings.get("quote_currency") or "USD"),
        "categories": cats,
        "items": items,
        "labels": {
            "title": ci.t(code, "list_title"),
            "pick_category": ci.t(code, "pick_category"),
            "order": ci.t(code, "order_btn"),
            "price_on_request": ci.t(code, "price_on_request"),
            "code": ci.t(code, "code"),
        },
    }


@router.get("/catalog/{code}/image", include_in_schema=False)
async def public_product_image(code: str, request: Request) -> Response:
    """Uploaded product image (public — it is shown to customers anyway)."""
    services: dict[str, Any] = getattr(request.app.state, "services", {}) or {}
    pool = services.get("pg")
    if pool is None:
        raise HTTPException(status_code=404, detail="no image")
    row = await pool.fetchrow(
        """SELECT i.mime, i.data FROM product_images i JOIN products p ON p.id = i.product_id
           WHERE p.code = $1 AND p.is_active LIMIT 1""",
        code[:12],
    )
    if row is None:
        raise HTTPException(status_code=404, detail="no image")
    return Response(
        content=bytes(row["data"]),
        media_type=str(row["mime"] or "image/jpeg"),
        headers={"Cache-Control": "public, max-age=600"},
    )


@router.post("/enquiry", status_code=201)
async def create_enquiry(payload: EnquiryIn, request: Request) -> dict[str, Any]:
    """Website quote/contact form → customer + support ticket (lead)."""
    if payload.website:
        # Honeypot tripped: pretend success, store nothing.
        log.info("public_enquiry_honeypot", extra={"action": "enquiry", "channel": CHANNEL_WEB})
        return {"ok": True, "reference": "ZX-" + uuid.uuid4().hex[:8].upper()}

    ip = _client_ip(request)
    await _rate_limit("enquiry", ip, window=3600, limit=ENQUIRY_LIMIT_PER_HOUR)

    services: dict[str, Any] = request.app.state.services
    pg = services.get("pg")
    if pg is None:
        raise HTTPException(status_code=503, detail="storage unavailable")

    from app.core.repository import get_or_create_customer, update_customer
    from app.core.security_stack import inspect_inbound
    from app.core.tools.support import create_ticket

    verdict = inspect_inbound(payload.message)
    if not verdict.allowed:
        raise HTTPException(status_code=400, detail="message contains disallowed content")

    customer = await get_or_create_customer(
        pg, channel=CHANNEL_WEB, sender_id=payload.email, sender_name=payload.name
    )
    customer_id = str(customer.get("id", ""))
    fields: dict[str, Any] = {"email": payload.email}
    if payload.company:
        fields["company"] = payload.company
    if payload.phone:
        fields["phone"] = payload.phone
    try:
        await update_customer(pg, customer_id, fields)
    except Exception as exc:  # optional columns may be absent on old schemas
        log.debug("public_enquiry_customer_update_skipped", extra={"error": str(exc)})

    subject = f"Website enquiry — {payload.service}"
    body_lines = [
        f"Name: {payload.name}",
        f"Company: {payload.company or '-'}",
        f"E-mail: {payload.email}",
        f"Phone: {payload.phone or '-'}",
        f"Service: {payload.service}",
        "",
        payload.message,
    ]
    ticket = await create_ticket(
        pg,
        customer_id=customer_id,
        subject=subject,
        body="\n".join(body_lines),
        severity="normal",
        channel=CHANNEL_WEB,
        auto_open=True,
    )
    reference = "ZX-" + str(ticket.get("ticket_id") or uuid.uuid4().hex)[:8].upper()

    try:
        from app.storage.pg import audit

        await audit(
            action="website.enquiry",
            actor="public-site",
            entity="ticket",
            entity_id=str(ticket.get("ticket_id", "")),
            details={"service": payload.service, "email": payload.email, "ip": ip},
            channel=CHANNEL_WEB,
        )
    except Exception:
        log.debug("public_enquiry_audit_skipped", exc_info=True)

    log.info(
        "public_enquiry_created",
        extra={
            "action": "enquiry",
            "channel": CHANNEL_WEB,
            "entity": f"ticket:{ticket.get('ticket_id', '')}",
        },
    )

    # 1.3.1 option — LEAD_ALERT_ENABLED: managers get the lead on Telegram
    # within seconds instead of discovering it in the ticket queue later.
    alerted = await _send_lead_alert(
        services,
        format_lead_alert(
            reference=reference,
            name=payload.name,
            company=payload.company,
            email=payload.email,
            phone=payload.phone,
            service=payload.service,
            message=payload.message,
        ),
    )
    return {"ok": True, "reference": reference, "alerted": alerted}


@router.post("/chat")
async def public_chat(payload: ChatIn, request: Request) -> dict[str, Any]:
    """Ask Zenovix from the website. Same guards + knowledge base as Telegram.

    Runs the reply *inline* (no Telegram delivery) and never exposes admin
    tools: the orchestrator is bypassed in favour of the knowledge-grounded
    inline brain, and the security stack screens both directions.
    """
    ip = _client_ip(request)
    await _rate_limit("chat", ip, window=60, limit=CHAT_LIMIT_PER_MINUTE)

    from app.core.security_stack import inspect_inbound, inspect_outbound

    inbound = inspect_inbound(payload.message)
    if not inbound.allowed:
        return {
            "ok": False,
            "reply": "I can't help with that request. If you have a genuine question about "
            "storage, bunkering, chartering or trade support, please rephrase it.",
        }

    services: dict[str, Any] = request.app.state.services
    hermes = services.get("hermes")
    if hermes is None:
        raise HTTPException(status_code=503, detail="assistant unavailable")

    session = payload.session or uuid.uuid4().hex[:16]
    t0 = time.perf_counter()
    try:
        reply_text = await _answer(hermes, services, inbound.text or payload.message, session)
    except Exception as exc:
        log.error(
            "public_chat_failed: %s: %s",
            type(exc).__name__,
            str(exc)[:200],
            extra={"action": "chat", "channel": CHANNEL_WEB, "error": str(exc)},
        )
        raise HTTPException(status_code=503, detail="assistant unavailable") from exc

    outbound = inspect_outbound(reply_text)
    reply_text = outbound.text or reply_text
    if not outbound.allowed or not reply_text.strip():
        reply_text = (
            "Thanks for your question. Our team can answer this directly — "
            "please use the enquiry form or write to studio@zenovix.com."
        )

    log.info(
        "public_chat_answered",
        extra={
            "action": "chat",
            "channel": CHANNEL_WEB,
            "latency_ms": round((time.perf_counter() - t0) * 1000, 1),
        },
    )
    return {"ok": True, "reply": reply_text, "session": session}


async def _answer(hermes: Any, services: dict[str, Any], text: str, session: str) -> str:
    """Knowledge-grounded answer via the same inline brain the bot uses.

    ``run_skill`` builds the COMPANY KNOWLEDGE block from the approved FAQ /
    guides / docs itself; we only pin the customer-facing knowledge skill and
    the website surface so no admin/ops tools are ever planned.
    """
    from app.constants import SKILL_KNOWLEDGE
    from app.core.reply_format import strip_markdown

    result = await hermes.run_skill(
        SKILL_KNOWLEDGE,
        text,
        conversation_id=f"web:{session}",
        customer_id="",
        context={
            "channel": CHANNEL_WEB,
            "sender_name": "Website visitor",
            "language": "en",
            "surface": "website",
        },
    )
    if not isinstance(result, dict) or not result.get("success"):
        raise RuntimeError(str(result.get("error") if isinstance(result, dict) else result))
    reply = strip_markdown(str(result.get("text") or ""))
    sources = result.get("sources") or []
    if sources:
        reply = f"{reply}\n\nSource: {sources[0]}"
    return reply.strip()
