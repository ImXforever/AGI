"""Telegram ping when a HITL draft is queued — not only on low-confidence escalate.

1.4.0: the ping carries **Approve / Reject** inline buttons (``apr_ok_<id>`` /
``apr_no_<id>``) so a manager decides from the phone without opening the
console. Buttons are only attached when the adapter supports them; every
other channel still receives the plain text line.
"""

from __future__ import annotations

from typing import Any

from app.logging_setup import get_logger

log = get_logger("app.core.hitl.notify")

CB_APPROVE = "apr_ok_"
CB_REJECT = "apr_no_"
CB_OPEN = "apr_open_"


def build_pending_notice(
    *,
    approval_id: str,
    action: str = "",
    snippet: str = "",
    skill: str = "",
) -> str:
    aid = str(approval_id or "").strip()
    act = str(action or skill or "review").strip()[:64]
    text = str(snippet or "").strip()[:600]
    lines = [f"HITL pending {aid}", f"Action: {act}"]
    if text:
        lines.append(text)
    return "\n".join(lines)


def decision_buttons(approval_id: str) -> list[list[tuple[str, str]]]:
    aid = str(approval_id or "").strip()
    return [
        [("✅ Approve", f"{CB_APPROVE}{aid}"), ("✖ Reject", f"{CB_REJECT}{aid}")],
        [("Open in console", f"{CB_OPEN}{aid}")],
    ]


def parse_decision_callback(data: str) -> tuple[str, str] | None:
    """``apr_ok_<id>`` → ("approved", id); ``apr_no_<id>`` → ("rejected", id)."""
    raw = (data or "").strip()
    if raw.startswith(CB_APPROVE):
        return "approved", raw[len(CB_APPROVE) :]
    if raw.startswith(CB_REJECT):
        return "rejected", raw[len(CB_REJECT) :]
    if raw.startswith(CB_OPEN):
        return "open", raw[len(CB_OPEN) :]
    return None


async def notify_pending(
    *,
    approval_id: str,
    action: str = "",
    snippet: str = "",
    skill: str = "",
    admin_ids: list[Any] | tuple[Any, ...] | None = None,
    adapter: Any = None,
    ping: bool = True,
    buttons: bool = True,
) -> int:
    """Send one notice per admin. Failures never raise into ingest."""
    if not ping or adapter is None:
        return 0
    ids = [str(x).strip() for x in (admin_ids or ()) if str(x).strip()]
    if not ids:
        return 0
    body = build_pending_notice(
        approval_id=approval_id, action=action, snippet=snippet, skill=skill
    )
    rows = decision_buttons(approval_id)
    sent = 0
    for admin_id in ids:
        try:
            if buttons and hasattr(adapter, "send_with_buttons"):
                await adapter.send_with_buttons(admin_id, body, rows)
            else:
                await adapter.send(recipient_id=admin_id, text=body)
            sent += 1
        except Exception as exc:
            log.warning(
                "hitl_ping_failed",
                extra={"action": "hitl.notify", "admin_id": admin_id, "error": str(exc)[:200]},
            )
    return sent
