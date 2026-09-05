"""Tests for v20 automation engine."""

from __future__ import annotations

from app.core.automation_engine import (
    TEMPLATES,
    TriggerType,
    create_from_template,
    create_rule,
    evaluate_rule,
    get_rule_stats,
    get_rules_for_trigger,
    process_batch,
    process_event,
)


class TestRuleCreation:
    def test_create_basic(self):
        rule = create_rule(
            "Test Rule",
            "A test rule",
            "email_received",
            {"category": "support"},
            [{"type": "send_reply", "params": {}}],
        )
        assert rule.name == "Test Rule"
        assert rule.trigger == TriggerType.EMAIL_RECEIVED
        assert rule.enabled is True

    def test_create_with_priority(self):
        rule = create_rule(
            "High Priority",
            "Desc",
            "task_created",
            {"priority": "urgent"},
            [{"type": "escalate", "params": {}}],
            priority=10,
        )
        assert rule.priority == 10


class TestRuleEvaluation:
    def test_match_simple_condition(self):
        rule = create_rule(
            "Test",
            "Desc",
            "email_received",
            {"category": "support"},
            [],
        )
        event = {"trigger": "email_received", "category": "support"}
        assert evaluate_rule(rule, event) is True

    def test_no_match_wrong_category(self):
        rule = create_rule(
            "Test",
            "Desc",
            "email_received",
            {"category": "support"},
            [],
        )
        event = {"trigger": "email_received", "category": "sales"}
        assert evaluate_rule(rule, event) is False

    def test_no_match_wrong_trigger(self):
        rule = create_rule(
            "Test",
            "Desc",
            "email_received",
            {"category": "support"},
            [],
        )
        event = {"trigger": "message_received", "category": "support"}
        assert evaluate_rule(rule, event) is False

    def test_disabled_rule_never_matches(self):
        rule = create_rule(
            "Test",
            "Desc",
            "email_received",
            {"category": "support"},
            [],
        )
        rule.enabled = False
        event = {"trigger": "email_received", "category": "support"}
        assert evaluate_rule(rule, event) is False

    def test_regex_condition(self):
        rule = create_rule(
            "Test",
            "Desc",
            "message_received",
            {"text": "~price|quote|buy"},
            [],
        )
        event = {"trigger": "message_received", "text": "What is the price?"}
        assert evaluate_rule(rule, event) is True

    def test_list_condition(self):
        rule = create_rule(
            "Test",
            "Desc",
            "message_received",
            {"priority": ["urgent", "high"]},
            [],
        )
        event = {"trigger": "message_received", "priority": "urgent"}
        assert evaluate_rule(rule, event) is True

    def test_dict_condition_gt(self):
        rule = create_rule(
            "Test",
            "Desc",
            "task_created",
            {"hours_overdue": {"op": "gt", "value": 24}},
            [],
        )
        event = {"trigger": "task_created", "hours_overdue": 48}
        assert evaluate_rule(rule, event) is True


class TestEventProcessing:
    def test_process_event_matched(self):
        rule = create_rule(
            "Auto Reply",
            "Desc",
            "email_received",
            {"category": "support"},
            [{"type": "send_reply", "params": {"template": "ack"}}],
        )
        event = {"trigger": "email_received", "category": "support"}
        result = process_event(rule, event)
        assert result.matched is True
        assert len(result.actions_executed) == 1
        assert rule.trigger_count == 1

    def test_process_event_not_matched(self):
        rule = create_rule(
            "Auto Reply",
            "Desc",
            "email_received",
            {"category": "support"},
            [{"type": "send_reply", "params": {}}],
        )
        event = {"trigger": "email_received", "category": "sales"}
        result = process_event(rule, event)
        assert result.matched is False
        assert rule.trigger_count == 0

    def test_process_batch(self):
        r1 = create_rule(
            "R1",
            "Desc",
            "email_received",
            {"category": "support"},
            [{"type": "send_reply", "params": {}}],
            priority=10,
        )
        r2 = create_rule(
            "R2",
            "Desc",
            "email_received",
            {"category": "support"},
            [{"type": "create_ticket", "params": {}}],
            priority=5,
        )
        event = {"trigger": "email_received", "category": "support"}
        results = process_batch([r1, r2], event)
        assert len(results) == 2


class TestRuleFiltering:
    def test_get_by_trigger(self):
        r1 = create_rule("R1", "Desc", "email_received", {}, [])
        r2 = create_rule("R2", "Desc", "task_created", {}, [])
        result = get_rules_for_trigger([r1, r2], "email_received")
        assert len(result) == 1
        assert result[0].trigger == TriggerType.EMAIL_RECEIVED


class TestRuleStats:
    def test_stats(self):
        r1 = create_rule("R1", "Desc", "email_received", {}, [])
        r2 = create_rule("R2", "Desc", "task_created", {}, [])
        r2.enabled = False
        stats = get_rule_stats([r1, r2])
        assert stats["total"] == 2
        assert stats["enabled"] == 1
        assert stats["disabled"] == 1


class TestTemplates:
    def test_template_list(self):
        assert len(TEMPLATES) >= 4

    def test_create_from_template(self):
        rule = create_from_template("auto_reply_support")
        assert rule is not None
        assert rule.name == "Auto-reply to support emails"

    def test_create_from_unknown_template(self):
        rule = create_from_template("nonexistent")
        assert rule is None


class TestRuleSerialization:
    def test_as_dict(self):
        rule = create_rule(
            "Test",
            "Desc",
            "email_received",
            {"category": "support"},
            [{"type": "send_reply", "params": {}}],
        )
        d = rule.as_dict()
        assert "id" in d
        assert "name" in d
        assert d["trigger"] == "email_received"
