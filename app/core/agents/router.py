"""Central operations router — one orchestrator, five specialist agents.

Does not execute side effects. Every plan carries a PolicyDecision so the
HITL executor (or the auto path) can apply it without asking the LLM again.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.core.company_charter import FUTURE_AGENTS, is_future_agent
from app.core.email_workflow import handle_inbound_email
from app.core.ops_workflow import handle_ops
from app.core.policy import PolicyDecision, evaluate_action
from app.core.sales_workflow import handle_sales
from app.core.social_workflow import handle_social
from app.core.support_workflow import handle_support
from app.core.website_workflow import handle_website


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
    policy = evaluate_action(action, actor_role=actor_role, approved=approved, context=context)
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
    result = handle_inbound_email(
        subject,
        text,
        sender=sender,
        message_id=str(extras.get("message_id") or ""),
        in_reply_to=str(extras.get("in_reply_to") or extras.get("reply_to_ref") or ""),
        references=str(extras.get("references") or ""),
        sender_name=str(extras.get("sender_name") or sender or "Customer"),
        company_name=str(extras.get("company_name") or "Our Company"),
    )
    triage = result.triage
    payload: dict[str, Any] = {
        "category": triage.category.value,
        "priority": triage.priority,
        "confidence": triage.confidence,
        "reason": result.reason,
        "subject": subject,
        "sender": sender,
        "thread_id": result.thread_id,
        "bounce": result.bounce,
        "sla_hours": result.sla_hours,
        "phase": result.phase.value,
    }
    if result.template_key:
        payload["smart_template"] = result.template_key
    if result.draft is not None:
        payload["draft"] = result.draft
    if result.phase.value == "draft":
        payload["draft_required"] = True

    context: dict[str, Any] = {"category": triage.category.value}
    if result.action == "reply_common":
        context["routine"] = True
    else:
        context["sensitivity"] = triage.category.value

    return _plan(
        agent="email_agent",
        domain="email",
        action=result.action,
        summary=result.reason,
        payload=payload,
        context=context,
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
    result = handle_website(
        text,
        extras=extras,
        approved=approved,
        approval_id=str(extras.get("approval_id") or ""),
        actor_role=actor_role,
    )
    context: dict[str, Any] = {}
    if result.change is not None:
        context = {
            "kind": result.change.kind.value,
            "sensitivity": result.change.kind.value,
        }
    return _plan(
        agent="website_agent",
        domain="website",
        action=result.action,
        summary=result.reason,
        payload=dict(result.payload),
        context=context,
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
    result = handle_social(text, extras=extras)
    context: dict[str, Any] = {
        "calendar_scheduled": result.action == "publish_calendar",
        "sensitive": result.phase.value in {"hold", "refuse_ad_spend"},
        "sensitivity": "important" if result.action != "publish_calendar" else "routine",
    }
    return _plan(
        agent="social_agent",
        domain="social",
        action=result.action,
        summary=result.reason,
        payload=dict(result.payload),
        context=context,
        actor_role=actor_role,
        approved=approved,
    )


def _sales_plan(
    text: str,
    *,
    extras: dict[str, Any],
    actor_role: str,
    approved: bool,
) -> AgentPlan:
    result = handle_sales(text, extras=extras)
    context: dict[str, Any] = {}
    if result.action in {"create_quote", "payment", "contract"}:
        context["sensitivity"] = "important"
    return _plan(
        agent="sales_agent",
        domain="sales",
        action=result.action,
        summary=result.reason,
        payload=dict(result.payload),
        context=context,
        actor_role=actor_role,
        approved=approved,
    )


def _support_plan(
    text: str,
    *,
    extras: dict[str, Any],
    actor_role: str,
    approved: bool,
) -> AgentPlan:
    result = handle_support(text, extras=extras)
    return _plan(
        agent="support_agent",
        domain="support",
        action=result.action,
        summary=result.reason,
        payload=dict(result.payload),
        actor_role=actor_role,
        approved=approved,
    )


def _ops_plan(
    text: str,
    *,
    source: str,
    extras: dict[str, Any],
    actor_role: str,
    approved: bool,
) -> AgentPlan:
    result = handle_ops(text, extras=extras, source=source)
    context: dict[str, Any] = {}
    if result.action in {"payment", "contract"}:
        context["sensitivity"] = "legal" if result.action == "contract" else "finance"
    return _plan(
        agent="ops_agent",
        domain="ops",
        action=result.action,
        summary=result.reason,
        payload=dict(result.payload),
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
        return _sales_plan(text, extras=extras, actor_role=actor_role, approved=approved)
    if requested in {"support_agent", "support"} or source_n == "support":
        return _support_plan(text, extras=extras, actor_role=actor_role, approved=approved)
    if requested in {"ops_agent", "ops"}:
        return _ops_plan(
            text, source=source_n, extras=extras, actor_role=actor_role, approved=approved
        )

    lowered = text.casefold()
    if any(k in lowered for k in ("invoice", "payment", "قرارداد", "contract", "فاکتور")):
        return _ops_plan(
            text, source=source_n, extras=extras, actor_role=actor_role, approved=approved
        )
    if any(k in lowered for k in ("quote", "قیمت", "خرید", "price", "catalog")):
        return _sales_plan(text, extras=extras, actor_role=actor_role, approved=approved)
    if any(k in lowered for k in ("error", "support", "خطا", "مشکل", "پشتیبانی")):
        return _support_plan(text, extras=extras, actor_role=actor_role, approved=approved)
    return _ops_plan(text, source=source_n, extras=extras, actor_role=actor_role, approved=approved)
