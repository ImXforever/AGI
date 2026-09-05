"""Central operations router — one orchestrator, five specialist agents.

Does not execute side effects. Every plan carries a PolicyDecision so the
HITL executor (or the auto path) can apply it without asking the LLM again.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.core.company_charter import FUTURE_AGENTS, is_future_agent
from app.core.email_smart_reply import match_smart_reply, render_reply
from app.core.email_workflow import EmailCategory, should_auto_reply, triage_email
from app.core.policy import PolicyDecision, evaluate_action
from app.core.social_workflow import prepare_post
from app.core.task_workflow import extract_task
from app.core.website_workflow import classify_content_change, normalize_contact_form


@dataclass(frozen=True)
class AgentPlan:
    agent: str
    domain: str
    action: str
    summary: str
    payload: dict[str, Any]
    policy: PolicyDecision
    auto_execute: bool
    needs_manager: bool
    audit: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "agent": self.agent,
            "domain": self.domain,
            "action": self.action,
            "summary": self.summary,
            "payload": self.payload,
            "policy": self.policy.as_dict(),
            "auto_execute": self.auto_execute,
            "needs_manager": self.needs_manager,
            "audit": self.audit,
        }


def _plan(
    *,
    agent: str,
    domain: str,
    action: str,
    summary: str,
    payload: dict[str, Any],
    context: dict[str, Any] | None = None,
    actor_role: str = "agent",
    approved: bool = False,
) -> AgentPlan:
    policy = evaluate_action(
        action, actor_role=actor_role, approved=approved, context=context
    )
    return AgentPlan(
        agent=agent,
        domain=domain,
        action=policy.action,
        summary=summary,
        payload=payload,
        policy=policy,
        auto_execute=policy.allowed and not policy.requires_approval,
        needs_manager=policy.requires_approval and not policy.allowed,
        audit={"actor_role": actor_role, "context": dict(context or {})},
    )


def _email_plan(
    text: str,
    *,
    subject: str,
    sender: str,
    actor_role: str,
    approved: bool,
    extras: dict[str, Any],
) -> AgentPlan:
    triage = triage_email(subject, text, sender=sender)
    smart = match_smart_reply(subject, text)
    payload: dict[str, Any] = {
        "category": triage.category.value,
        "priority": triage.priority,
        "confidence": triage.confidence,
        "reason": triage.reason,
        "subject": subject,
        "sender": sender,
    }
    if triage.category == EmailCategory.SPAM:
        return _plan(
            agent="email_agent",
            domain="email",
            action="classify_email",
            summary="spam dropped, no outbound",
            payload=payload,
            context={"category": "spam"},
            actor_role=actor_role,
            approved=approved,
        )

    sensitive = triage.category in {EmailCategory.FINANCE, EmailCategory.LEGAL}
    if smart is not None and should_auto_reply(triage) and not sensitive:
        rendered = render_reply(
            smart,
            original_subject=subject,
            sender_name=str(extras.get("sender_name") or sender or "Customer"),
            company_name=str(extras.get("company_name") or "Our Company"),
        )
        payload["smart_template"] = smart.template_key
        payload["draft"] = rendered
        return _plan(
            agent="email_agent",
            domain="email",
            action="reply_common",
            summary=f"auto-reply via {smart.template_key}",
            payload=payload,
            context={"routine": True, "category": triage.category.value},
            actor_role=actor_role,
            approved=approved,
        )

    payload["draft_required"] = True
    action = "send_email" if sensitive or triage.requires_human else "create_draft"
    if sensitive:
        action = "send_email"
    return _plan(
        agent="email_agent",
        domain="email",
        action=action,
        summary=f"email {triage.category.value} queued ({triage.reason})",
        payload=payload,
        context={"sensitivity": triage.category.value, "category": triage.category.value},
        actor_role=actor_role,
        approved=approved,
    )


def _website_plan(
    text: str,
    *,
    extras: dict[str, Any],
    actor_role: str,
    approved: bool,
) -> AgentPlan:
    if extras.get("form"):
        form = extras["form"]
        lead = normalize_contact_form(
            name=str(form.get("name", "")),
            email=str(form.get("email", "")),
            message=str(form.get("message", text)),
        )
        return _plan(
            agent="website_agent",
            domain="website",
            action="create_lead",
            summary=f"contact form from {lead.email}",
            payload={"name": lead.name, "email": lead.email, "message": lead.message},
            actor_role=actor_role,
            approved=approved,
        )

    field = str(extras.get("field") or extras.get("cms_field") or "description")
    after = str(extras.get("after") or text)
    before = str(extras.get("before") or "")
    change = classify_content_change(before=before, after=after, field=field)
    return _plan(
        agent="website_agent",
        domain="website",
        action=change.action,
        summary=f"cms {change.kind.value} change",
        payload={
            "kind": change.kind.value,
            "field": field,
            "before": before,
            "after": after,
        },
        context={"kind": change.kind.value, "sensitivity": change.kind.value},
        actor_role=actor_role,
        approved=approved,
    )


def _social_plan(
    text: str,
    *,
    extras: dict[str, Any],
    actor_role: str,
    approved: bool,
) -> AgentPlan:
    platform = str(extras.get("platform") or "instagram")
    scheduled_at = float(extras.get("scheduled_at") or 0.0)
    post = prepare_post(
        platform=platform,
        caption=str(extras.get("caption") or text),
        scheduled_at=scheduled_at,
        media_url=str(extras.get("media_url") or ""),
        hashtags=list(extras.get("hashtags") or []),
    )
    action = "publish_calendar" if (scheduled_at > 0 and not post.requires_approval) else "publish_content"
    return _plan(
        agent="social_agent",
        domain="social",
        action=action,
        summary=f"{post.platform} post {post.status.value}",
        payload={
            "platform": post.platform,
            "caption": post.caption,
            "status": post.status.value,
            "scheduled_at": post.scheduled_at,
            "reason": post.reason,
        },
        context={
            "calendar_scheduled": scheduled_at > 0,
            "sensitive": post.risk.value >= 2,
            "sensitivity": "important" if post.requires_approval else "routine",
        },
        actor_role=actor_role,
        approved=approved,
    )


def _sales_plan(text: str, *, actor_role: str, approved: bool) -> AgentPlan:
    task = extract_task(text, source="sales")
    wants_quote = any(
        token in text.casefold()
        for token in ("quote", "قیمت", "پیش فاکتور", "پیش‌فاکتور", "price", "عرض سعر")
    )
    action = "create_quote" if wants_quote else "create_lead"
    return _plan(
        agent="sales_agent",
        domain="sales",
        action=action,
        summary="sales quote" if wants_quote else "sales lead",
        payload={"text": text[:500], "task": None if task is None else task.kind.value},
        context={"sensitivity": "important" if wants_quote else "routine"},
        actor_role=actor_role,
        approved=approved,
    )


def _support_plan(text: str, *, actor_role: str, approved: bool) -> AgentPlan:
    task = extract_task(text, source="support")
    return _plan(
        agent="support_agent",
        domain="support",
        action="create_ticket",
        summary="support ticket",
        payload={
            "text": text[:500],
            "priority": None if task is None else task.priority,
            "requires_human": bool(task and task.requires_human),
        },
        actor_role=actor_role,
        approved=approved,
    )


def _ops_plan(text: str, *, source: str, actor_role: str, approved: bool) -> AgentPlan:
    task = extract_task(text, source=source)
    if task is None:
        return _plan(
            agent="ops_agent",
            domain="ops",
            action="search_knowledge",
            summary="no actionable task; consult knowledge base",
            payload={"text": text[:500]},
            actor_role=actor_role,
            approved=approved,
        )
    action = "create_task"
    context: dict[str, Any] = {}
    if task.kind.value in {"finance", "legal"}:
        action = "contract" if task.kind.value == "legal" else "payment"
        context["sensitivity"] = task.kind.value
    return _plan(
        agent="ops_agent",
        domain="ops",
        action=action,
        summary=f"ops task {task.kind.value}",
        payload={
            "title": task.title,
            "kind": task.kind.value,
            "priority": task.priority,
            "requires_human": task.requires_human,
        },
        context=context,
        actor_role=actor_role,
        approved=approved,
    )


def route_work(
    text: str,
    *,
    source: str = "conversation",
    subject: str = "",
    sender: str = "",
    requested_agent: str = "",
    actor_role: str = "agent",
    approved: bool = False,
    extras: dict[str, Any] | None = None,
) -> AgentPlan:
    """Route a unit of work to a specialist. Never executes the side effect."""
    extras = dict(extras or {})
    source_n = (source or "conversation").strip().lower()
    requested = (requested_agent or extras.get("agent") or "").strip().lower()

    if requested and is_future_agent(requested):
        return _plan(
            agent=requested,
            domain="future",
            action="unknown_future",
            summary=f"{requested} is declared for a later phase and is inactive",
            payload={"future_agents": list(FUTURE_AGENTS)},
            actor_role=actor_role,
            approved=approved,
        )

    if requested in {"email_agent", "email"} or source_n == "email":
        return _email_plan(
            text,
            subject=subject,
            sender=sender,
            actor_role=actor_role,
            approved=approved,
            extras=extras,
        )
    if requested in {"website_agent", "website"} or source_n in {"website", "cms", "form"}:
        return _website_plan(text, extras=extras, actor_role=actor_role, approved=approved)
    if requested in {"social_agent", "social"} or source_n in {"social", "instagram", "twitter"}:
        return _social_plan(text, extras=extras, actor_role=actor_role, approved=approved)
    if requested in {"sales_agent", "sales"} or source_n == "sales":
        return _sales_plan(text, actor_role=actor_role, approved=approved)
    if requested in {"support_agent", "support"} or source_n == "support":
        return _support_plan(text, actor_role=actor_role, approved=approved)
    if requested in {"ops_agent", "ops"}:
        return _ops_plan(text, source=source_n, actor_role=actor_role, approved=approved)

    lowered = text.casefold()
    if any(k in lowered for k in ("invoice", "payment", "قرارداد", "contract", "فاکتور")):
        return _ops_plan(text, source=source_n, actor_role=actor_role, approved=approved)
    if any(k in lowered for k in ("quote", "قیمت", "خرید", "price", "catalog")):
        return _sales_plan(text, actor_role=actor_role, approved=approved)
    if any(k in lowered for k in ("error", "support", "خطا", "مشکل", "پشتیبانی")):
        return _support_plan(text, actor_role=actor_role, approved=approved)
    return _ops_plan(text, source=source_n, actor_role=actor_role, approved=approved)
