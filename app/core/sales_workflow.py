"""Sales agent: leads, catalog-priced quote drafts, no payments."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from app.core.policy import evaluate_action


class SalesPhase(StrEnum):
    ANSWER = "answer_product"
    LEAD = "register_lead"
    DRAFT_QUOTE = "draft_quote"
    TRACK = "track_order"
    HANDOFF = "handoff"
    REFUSE = "refuse_payment"


@dataclass(frozen=True)
class SalesLead:
    name: str
    email: str
    company: str
    interest: str
    source: str = "sales"


@dataclass(frozen=True)
class QuoteLine:
    product_id: str
    quantity: int
    unit_price: float
    discount_pct: float
    line_total: float


@dataclass(frozen=True)
class SalesAgentResult:
    """One sales-agent step. Never takes payment. Never sends a quote."""

    phase: SalesPhase
    action: str
    lead: SalesLead | None
    lines: tuple[QuoteLine, ...]
    production: bool
    reason: str
    payload: dict[str, Any]


_EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
_QUOTE_MARKERS = (
    "quote",
    "quotation",
    "قیمت",
    "پیش فاکتور",
    "پیش‌فاکتور",
    "عرض سعر",
)
_PAYMENT_MARKERS = (
    "payment",
    "pay now",
    "charge card",
    "stripe",
    "wire transfer",
    "پرداخت",
    "کارت",
)
_COMPLEX_MARKERS = (
    "tender",
    "rfp",
    "custom spec",
    "exclusive",
    "contract",
    "قرارداد",
)
_ORDER_MARKERS = (
    "order status",
    "tracking",
    "where is my order",
    "وضعیت سفارش",
    "پیگیری سفارش",
)


def catalog_unit_price(catalog_row: dict[str, Any]) -> float:
    """Catalog is the only price source. Missing/invalid → 0 (caller must hold)."""
    raw = catalog_row.get("unit_price")
    if raw is None or raw == "":
        return 0.0
    try:
        price = float(raw)
    except (TypeError, ValueError):
        return 0.0
    return price if price > 0 else 0.0


def discount_pct_for_qty(tiers: list[dict[str, Any]] | None, quantity: int) -> float:
    best = 0.0
    for tier in sorted(tiers or [], key=lambda t: int(t.get("min_qty") or 0), reverse=True):
        if quantity >= int(tier.get("min_qty") or 0):
            try:
                best = float(tier.get("discount_pct") or 0.0)
            except (TypeError, ValueError):
                best = 0.0
            break
    return max(0.0, min(best, 100.0))


def quote_line_from_catalog(
    *,
    product_id: str,
    quantity: int,
    catalog_row: dict[str, Any],
    requested_unit_price: Any = None,
) -> QuoteLine | None:
    """Build a line from catalog only. Price overrides are ignored."""
    del requested_unit_price  # never used — catalog is source of truth
    qty = max(1, int(quantity or 1))
    unit = catalog_unit_price(catalog_row)
    if unit <= 0:
        return None
    pct = discount_pct_for_qty(catalog_row.get("discount_tiers") or [], qty)
    discounted = unit * (1 - pct / 100)
    return QuoteLine(
        product_id=str(product_id),
        quantity=qty,
        unit_price=round(unit, 4),
        discount_pct=pct,
        line_total=round(discounted * qty, 4),
    )


def normalize_lead(
    *,
    name: str,
    email: str = "",
    company: str = "",
    interest: str = "",
    source: str = "sales",
) -> SalesLead:
    clean_name = " ".join((name or "").split())
    clean_email = (email or "").strip().lower()
    if not clean_name:
        raise ValueError("lead name must not be empty")
    if clean_email and not _EMAIL_RE.fullmatch(clean_email):
        raise ValueError("lead email is invalid")
    if len(clean_name) > 200 or len(clean_email) > 320:
        raise ValueError("lead field is too long")
    return SalesLead(
        name=clean_name,
        email=clean_email,
        company=" ".join((company or "").split())[:200],
        interest=(interest or "")[:500],
        source=source or "sales",
    )


def _has_any(text: str, markers: tuple[str, ...]) -> bool:
    hay = (text or "").casefold()
    return any(m.casefold() in hay for m in markers)


def handle_sales(
    text: str,
    *,
    extras: dict[str, Any] | None = None,
) -> SalesAgentResult:
    """State machine: refuse payment | quote HITL | lead AUTO | handoff | track."""
    extras = dict(extras or {})
    blob = f"{text} {extras.get('interest') or ''}"

    if extras.get("pay") or _has_any(blob, _PAYMENT_MARKERS):
        decision = evaluate_action("payment")
        return SalesAgentResult(
            phase=SalesPhase.REFUSE,
            action="payment",
            lead=None,
            lines=(),
            production=False,
            reason="sales agent never executes payment",
            payload={"text": (text or "")[:500], "allowed": decision.allowed},
        )

    if extras.get("lead") or extras.get("form"):
        raw = extras.get("lead") or extras.get("form") or {}
        if not isinstance(raw, dict):
            raw = {}
        try:
            lead = normalize_lead(
                name=str(raw.get("name") or extras.get("name") or ""),
                email=str(raw.get("email") or extras.get("email") or ""),
                company=str(raw.get("company") or ""),
                interest=str(raw.get("interest") or text or ""),
            )
        except ValueError as exc:
            return SalesAgentResult(
                phase=SalesPhase.REFUSE,
                action="invalid_lead",
                lead=None,
                lines=(),
                production=False,
                reason=str(exc),
                payload={"error": str(exc)},
            )
        return SalesAgentResult(
            phase=SalesPhase.LEAD,
            action="create_lead",
            lead=lead,
            lines=(),
            production=False,
            reason=f"lead {lead.name}",
            payload={
                "name": lead.name,
                "email": lead.email,
                "company": lead.company,
                "interest": lead.interest,
                "source": lead.source,
            },
        )

    if extras.get("items") or _has_any(blob, _QUOTE_MARKERS):
        raw_catalog = extras.get("catalog")
        catalog: dict[str, Any] = dict(raw_catalog) if isinstance(raw_catalog, dict) else {}
        raw_items_value = extras.get("items")
        raw_items: list[Any] = list(raw_items_value) if isinstance(raw_items_value, list) else []
        lines: list[QuoteLine] = []
        for item in raw_items:
            if not isinstance(item, dict):
                continue
            pid = str(item.get("product_id") or "")
            row = catalog.get(pid) if pid else None
            if not isinstance(row, dict):
                continue
            line = quote_line_from_catalog(
                product_id=pid,
                quantity=int(item.get("quantity") or 1),
                catalog_row=row,
                requested_unit_price=item.get("unit_price"),
            )
            if line is not None:
                lines.append(line)
        return SalesAgentResult(
            phase=SalesPhase.DRAFT_QUOTE,
            action="create_quote",
            lead=None,
            lines=tuple(lines),
            production=False,
            reason="quote draft held for manager — not sent",
            payload={
                "text": (text or "")[:500],
                "items": [
                    {
                        "product_id": ln.product_id,
                        "quantity": ln.quantity,
                        "unit_price": ln.unit_price,
                        "discount_pct": ln.discount_pct,
                        "line_total": ln.line_total,
                    }
                    for ln in lines
                ],
                "sent": False,
            },
        )

    if extras.get("order") or _has_any(blob, _ORDER_MARKERS):
        return SalesAgentResult(
            phase=SalesPhase.TRACK,
            action="create_task",
            lead=None,
            lines=(),
            production=False,
            reason="order tracking task",
            payload={"text": (text or "")[:500], "kind": "sales"},
        )

    if _has_any(blob, _COMPLEX_MARKERS):
        return SalesAgentResult(
            phase=SalesPhase.HANDOFF,
            action="contract",
            lead=None,
            lines=(),
            production=False,
            reason="complex deal handed to manager",
            payload={"text": (text or "")[:500]},
        )

    return SalesAgentResult(
        phase=SalesPhase.LEAD,
        action="create_lead",
        lead=None,
        lines=(),
        production=False,
        reason="sales lead",
        payload={"text": (text or "")[:500]},
    )
