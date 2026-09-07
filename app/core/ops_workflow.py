"""Ops agent: tasks, reminders, manager brief, cross-domain links."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from app.core.company_charter import FUTURE_AGENTS, is_future_agent
from app.core.task_workflow import extract_task


class OpsPhase(StrEnum):
    TASK = "create_task"
    REMIND = "remind"
    REPORT = "report"
    LINK = "cross_link"
    REFUSE_FUTURE = "refuse_future"


_LINK_KINDS = frozenset({"lead", "ticket", "quote", "task", "email", "page"})
_REPORT_MARKERS = ("daily report", "weekly report", "ops digest", "manager report", "گزارش روزانه")
_REMIND_MARKERS = ("remind", "reminder", "یادآوری", "تذكير")
_FUTURE_MARKERS = (
    "payroll",
    "hire someone",
    "job posting",
    "accounting close",
    "studio render",
    "gantt",
)


@dataclass(frozen=True)
class OpsAgentResult:
    """One ops step. Never activates future agents. Reports never include message bodies."""

    phase: OpsPhase
    action: str
    reason: str
    payload: dict[str, Any]


def make_domain_links(
    *,
    lead_id: str = "",
    ticket_id: str = "",
    quote_id: str = "",
    task_id: str = "",
    email_id: str = "",
    page_id: str = "",
) -> list[dict[str, str]]:
    """Lead ↔ ticket ↔ quote (and task/email/page). No accounting/HR ids."""
    raw = {
        "lead": lead_id,
        "ticket": ticket_id,
        "quote": quote_id,
        "task": task_id,
        "email": email_id,
        "page": page_id,
    }
    out: list[dict[str, str]] = []
    for kind, value in raw.items():
        ident = str(value or "").strip()[:64]
        if ident and kind in _LINK_KINDS:
            out.append({"kind": kind, "id": ident})
    return out


def _count(events: list[dict[str, Any]], types: set[str]) -> int:
    total = 0
    for e in events:
        if str(e.get("type") or "").lower() in types:
            total += int(e["count"]) if e.get("count") is not None else 1
    return total


def manager_brief(
    events: list[dict[str, Any]] | None = None,
    *,
    links: list[dict[str, str]] | None = None,
    period: str = "daily",
) -> str:
    """Sections a manager actually reads. Counts only — no message text."""
    rows = list(events or [])
    need = _count(rows, {"approval_pending", "pending_approval"})
    quotes = _count(rows, {"quote_pending", "quote_draft"})
    safety = _count(rows, {"safety_ticket", "ticket_safety"})
    tickets = _count(rows, {"ticket_created"})
    leads = _count(rows, {"lead_created"})
    errors = _count(rows, {"error", "failed", "tool_execution_failed"})
    messages = _count(rows, {"message", "incoming", "outbound"})
    emails_auto = _count(rows, {"email_auto_replied"})
    emails_held = _count(rows, {"email_escalated"})
    calendar = _count(rows, {"calendar_ready"})
    link_n = len(links or [])
    inactive = ", ".join(FUTURE_AGENTS)
    return (
        f"Manager brief ({period})\n"
        "NEEDS YOU\n"
        f"- Approvals waiting: {need}\n"
        f"- Quotes not sent: {quotes}\n"
        f"- Safety tickets: {safety}\n"
        "WORK\n"
        f"- Messages: {messages}\n"
        f"- Email auto-replied / held: {emails_auto} / {emails_held}\n"
        f"- Leads / tickets: {leads} / {tickets}\n"
        f"- Calendar ready: {calendar}\n"
        f"- Errors: {errors}\n"
        f"LINKS: {link_n} cross-domain (lead↔ticket↔quote)\n"
        f"INACTIVE (declared only): {inactive}\n"
    )


def handle_ops(
    text: str,
    *,
    extras: dict[str, Any] | None = None,
    source: str = "ops",
) -> OpsAgentResult:
    extras = dict(extras or {})
    blob = (text or "").casefold()

    requested = str(extras.get("agent") or extras.get("requested_agent") or "")
    if requested and is_future_agent(requested):
        return OpsAgentResult(
            phase=OpsPhase.REFUSE_FUTURE,
            action="unknown_future",
            reason=f"{requested} is declared for a later phase and is inactive",
            payload={"future_agents": list(FUTURE_AGENTS)},
        )
    if any(m in blob for m in _FUTURE_MARKERS):
        return OpsAgentResult(
            phase=OpsPhase.REFUSE_FUTURE,
            action="unknown_future",
            reason="future agent requested — not live",
            payload={"future_agents": list(FUTURE_AGENTS)},
        )

    links = make_domain_links(
        lead_id=str(extras.get("lead_id") or ""),
        ticket_id=str(extras.get("ticket_id") or ""),
        quote_id=str(extras.get("quote_id") or ""),
        task_id=str(extras.get("task_id") or ""),
        email_id=str(extras.get("email_id") or ""),
        page_id=str(extras.get("page_id") or ""),
    )
    if extras.get("link") and links:
        return OpsAgentResult(
            phase=OpsPhase.LINK,
            action="create_task",
            reason="cross-domain link recorded",
            payload={"links": links, "title": "cross-link lead/ticket/quote"},
        )

    events = extras.get("events") if isinstance(extras.get("events"), list) else []
    if extras.get("report") or any(m in blob for m in _REPORT_MARKERS):
        period = "weekly" if "weekly" in blob else "daily"
        brief = manager_brief(events, links=links, period=period)
        return OpsAgentResult(
            phase=OpsPhase.REPORT,
            action="create_task",
            reason="manager brief compiled",
            payload={
                "title": f"{period} manager brief",
                "kind": "ops",
                "brief": brief,
                "links": links,
            },
        )

    if extras.get("reminder") or any(m in blob for m in _REMIND_MARKERS):
        minutes = int(extras.get("minutes") or 60)
        minutes = max(1, min(minutes, 43200))
        return OpsAgentResult(
            phase=OpsPhase.REMIND,
            action="create_task",
            reason="reminder scheduled",
            payload={
                "title": (text or "reminder")[:200],
                "kind": "ops",
                "minutes": minutes,
            },
        )

    task = extract_task(text, source=source)
    if task is not None and task.kind.value == "legal":
        return OpsAgentResult(
            phase=OpsPhase.TASK,
            action="contract",
            reason="ops task legal",
            payload={
                "title": task.title,
                "kind": task.kind.value,
                "priority": task.priority,
                "requires_human": True,
                "links": links,
            },
        )
    if task is not None and task.kind.value == "finance":
        return OpsAgentResult(
            phase=OpsPhase.TASK,
            action="payment",
            reason="ops task finance",
            payload={
                "title": task.title,
                "kind": task.kind.value,
                "priority": task.priority,
                "requires_human": True,
                "links": links,
            },
        )
    if task is not None:
        return OpsAgentResult(
            phase=OpsPhase.TASK,
            action="create_task",
            reason=f"ops task {task.kind.value}",
            payload={
                "title": task.title,
                "kind": task.kind.value,
                "priority": task.priority,
                "requires_human": task.requires_human,
                "links": links,
            },
        )

    return OpsAgentResult(
        phase=OpsPhase.TASK,
        action="search_knowledge",
        reason="no actionable task; consult knowledge base",
        payload={"text": (text or "")[:500], "links": links},
    )
