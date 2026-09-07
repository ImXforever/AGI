"""Rule-based automation engine (v20).

Create, evaluate, and execute automation rules without LLM calls.
Rules follow: trigger → condition → action pattern.
"""

from __future__ import annotations

import hashlib
import os
import re
import time
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from app.logging_setup import get_logger

log = get_logger("app.core.automation_engine")


class TriggerType(StrEnum):
    EMAIL_RECEIVED = "email_received"
    MESSAGE_RECEIVED = "message_received"
    TASK_CREATED = "task_created"
    APPROVAL_PENDING = "approval_pending"
    SOCIAL_MENTION = "social_mention"
    FORM_SUBMITTED = "form_submitted"
    SCHEDULE = "schedule"


class ActionType(StrEnum):
    SEND_REPLY = "send_reply"
    CREATE_TICKET = "create_ticket"
    ASSIGN_TASK = "assign_task"
    SEND_NOTIFICATION = "send_notification"
    CATEGORIZE = "categorize"
    ESCALATE = "escalate"
    ADD_TAG = "add_tag"


@dataclass
class AutomationRule:
    id: str
    name: str
    description: str
    trigger: TriggerType
    conditions: dict[str, Any]
    actions: list[dict[str, Any]]
    enabled: bool
    priority: int
    created_at: float
    last_triggered: float | None
    trigger_count: int

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "trigger": self.trigger.value,
            "conditions": self.conditions,
            "actions": self.actions,
            "enabled": self.enabled,
            "priority": self.priority,
            "created_at": self.created_at,
            "last_triggered": self.last_triggered,
            "trigger_count": self.trigger_count,
        }


@dataclass
class AutomationResult:
    rule_id: str
    rule_name: str
    matched: bool
    actions_executed: list[dict[str, Any]]
    executed_at: float

    def as_dict(self) -> dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "rule_name": self.rule_name,
            "matched": self.matched,
            "actions_executed": self.actions_executed,
            "executed_at": self.executed_at,
        }


def _gen_id() -> str:
    return hashlib.sha256(os.urandom(32)).hexdigest()[:12]


def create_rule(
    name: str,
    description: str,
    trigger: str,
    conditions: dict[str, Any],
    actions: list[dict[str, Any]],
    *,
    priority: int = 0,
) -> AutomationRule:
    """Create a new automation rule."""
    return AutomationRule(
        id=_gen_id(),
        name=name,
        description=description,
        trigger=TriggerType(trigger),
        conditions=conditions,
        actions=actions,
        enabled=True,
        priority=priority,
        created_at=time.time(),
        last_triggered=None,
        trigger_count=0,
    )


def _as_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _match_condition(event: dict[str, Any], condition_key: str, condition_value: Any) -> bool:
    """Check if an event matches a single condition."""
    event_value = event.get(condition_key, "")

    if isinstance(condition_value, str):
        if condition_value.startswith("~"):
            pattern = condition_value[1:]
            return bool(re.search(pattern, str(event_value), re.IGNORECASE))
        return str(event_value).lower() == condition_value.lower()

    if isinstance(condition_value, list):
        return str(event_value).lower() in [str(v).lower() for v in condition_value]

    if isinstance(condition_value, dict):
        op = condition_value.get("op", "eq")
        val = condition_value.get("value")
        if op == "eq":
            return str(event_value).lower() == str(val).lower()
        if op == "neq":
            return str(event_value).lower() != str(val).lower()
        if op == "contains":
            return str(val).lower() in str(event_value).lower()
        if op == "gt":
            return _as_float(event_value) > _as_float(val)
        if op == "lt":
            return _as_float(event_value) < _as_float(val)
        if op == "regex":
            return bool(re.search(str(val), str(event_value), re.IGNORECASE))

    return str(event_value).lower() == str(condition_value).lower()


def evaluate_rule(rule: AutomationRule, event: dict[str, Any]) -> bool:
    """Evaluate if a rule matches an event."""
    if not rule.enabled:
        return False
    if rule.trigger.value != event.get("trigger", ""):
        return False
    for key, value in rule.conditions.items():
        if not _match_condition(event, key, value):
            return False
    return True


def execute_actions(rule: AutomationRule, event: dict[str, Any]) -> list[dict[str, Any]]:
    """Execute all actions for a matched rule. Returns action results."""
    results: list[dict[str, Any]] = []
    for action in rule.actions:
        action_type = action.get("type", "")
        result: dict[str, Any] = {
            "type": action_type,
            "params": action.get("params", {}),
            "status": "executed",
        }
        results.append(result)
        log.info(
            "automation_action_executed",
            extra={"action": "automation.execute", "rule": rule.name, "type": action_type},
        )
    return results


def process_event(rule: AutomationRule, event: dict[str, Any]) -> AutomationResult:
    """Process an event against a rule: evaluate + execute."""
    matched = evaluate_rule(rule, event)
    actions_executed: list[dict[str, Any]] = []
    if matched:
        actions_executed = execute_actions(rule, event)
        rule.last_triggered = time.time()
        rule.trigger_count += 1
    return AutomationResult(
        rule_id=rule.id,
        rule_name=rule.name,
        matched=matched,
        actions_executed=actions_executed,
        executed_at=time.time(),
    )


def process_batch(rules: list[AutomationRule], event: dict[str, Any]) -> list[AutomationResult]:
    """Process an event against all enabled rules, sorted by priority."""
    enabled = [r for r in rules if r.enabled]
    enabled.sort(key=lambda r: -r.priority)
    results: list[AutomationResult] = []
    for rule in enabled:
        result = process_event(rule, event)
        if result.matched:
            results.append(result)
    return results


def get_rules_for_trigger(rules: list[AutomationRule], trigger: str) -> list[AutomationRule]:
    """Get all enabled rules for a specific trigger type."""
    return [r for r in rules if r.enabled and r.trigger.value == trigger]


def get_rule_stats(rules: list[AutomationRule]) -> dict[str, Any]:
    """Get statistics for all rules."""
    return {
        "total": len(rules),
        "enabled": sum(1 for r in rules if r.enabled),
        "disabled": sum(1 for r in rules if not r.enabled),
        "total_triggers": sum(r.trigger_count for r in rules),
        "by_trigger": _count_by_trigger(rules),
    }


def _count_by_trigger(rules: list[AutomationRule]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for r in rules:
        counts[r.trigger.value] = counts.get(r.trigger.value, 0) + 1
    return counts


# Pre-built templates for common automation scenarios

TEMPLATES: dict[str, dict[str, Any]] = {
    "auto_reply_support": {
        "name": "Auto-reply to support emails",
        "description": "Send automatic reply when support email received",
        "trigger": "email_received",
        "conditions": {"category": "support"},
        "actions": [{"type": "send_reply", "params": {"template": "support_ack"}}],
    },
    "escalate_urgent": {
        "name": "Escalate urgent tasks",
        "description": "Notify manager when urgent task created",
        "trigger": "task_created",
        "conditions": {"priority": "urgent"},
        "actions": [
            {"type": "send_notification", "params": {"channel": "telegram", "target": "admin"}},
            {"type": "assign_task", "params": {"assignee": "manager"}},
        ],
    },
    "auto_tag_sales": {
        "name": "Auto-tag sales inquiries",
        "description": "Add sales tag to price-related messages",
        "trigger": "message_received",
        "conditions": {"text": "~price|quote|buy|cost|قیمت"},
        "actions": [{"type": "add_tag", "params": {"tag": "sales"}}],
    },
    "form_to_ticket": {
        "name": "Convert form submissions to tickets",
        "description": "Create support ticket from website form",
        "trigger": "form_submitted",
        "conditions": {"form_type": "contact"},
        "actions": [{"type": "create_ticket", "params": {"priority": "normal"}}],
    },
}


def create_from_template(template_key: str) -> AutomationRule | None:
    """Create a rule from a pre-built template."""
    template = TEMPLATES.get(template_key)
    if not template:
        return None
    return create_rule(
        name=template["name"],
        description=template["description"],
        trigger=template["trigger"],
        conditions=template["conditions"],
        actions=template["actions"],
    )
