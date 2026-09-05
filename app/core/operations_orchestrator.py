"""Small, deterministic operations orchestrator for the v10 release."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.core.agents.router import AgentPlan, route_work
from app.core.email_workflow import EmailTriage, triage_email
from app.core.policy import PolicyDecision, evaluate_action
from app.core.task_workflow import TaskDraft, extract_task


@dataclass(frozen=True)
class OperationPlan:
    route: str
    source: str
    email: EmailTriage | None
    task: TaskDraft | None
    policy: PolicyDecision
    specialist: AgentPlan | None = None


def plan_operation(
    text: str,
    *,
    source: str = "conversation",
    subject: str = "",
    requested_action: str = "create_task",
    extras: dict[str, Any] | None = None,
) -> OperationPlan:
    """Create an explainable plan without executing an external side effect.

    v10 composes the tested domain modules. Execution remains a separate step,
    so this plan can be shown to a manager or passed through an approval gate.
    """
    clean_source = source.strip().lower() or "conversation"
    email_result = triage_email(subject, text) if clean_source == "email" else None
    task = extract_task(text, source=clean_source)

    if email_result is not None:
        route = email_result.category.value
    elif task is not None:
        route = task.kind.value
    else:
        route = "general"

    policy = evaluate_action(requested_action)
    specialist = route_work(text, source=clean_source, subject=subject, extras=extras)
    return OperationPlan(
        route=route,
        source=clean_source,
        email=email_result,
        task=task,
        policy=policy,
        specialist=specialist,
    )
