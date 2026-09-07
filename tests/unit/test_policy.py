"""Tests for v0.4 fail-closed risk and approval decisions."""

from __future__ import annotations

from app.core.policy import RiskLevel, evaluate_action, registered_actions


def test_low_risk_action_is_allowed_without_approval() -> None:
    decision = evaluate_action("read_email")
    assert decision.allowed is True
    assert decision.requires_approval is False
    assert decision.risk == RiskLevel.LOW


def test_medium_mutation_requires_approval() -> None:
    decision = evaluate_action("update_customer")
    assert decision.allowed is False
    assert decision.requires_approval is True
    assert decision.risk == RiskLevel.MEDIUM


def test_approval_requires_manager_role() -> None:
    agent = evaluate_action("payment", actor_role="agent", approved=True, approval_id="a1")
    manager = evaluate_action("payment", actor_role="admin", approved=True, approval_id="a1")
    assert agent.allowed is False
    assert manager.allowed is True
    assert manager.risk == RiskLevel.CRITICAL


def test_approved_flag_without_record_id_is_denied() -> None:
    decision = evaluate_action("payment", actor_role="admin", approved=True)
    assert decision.allowed is False
    assert "approval record" in decision.reason


def test_unknown_actions_fail_closed() -> None:
    decision = evaluate_action("send_money_to_unknown_place")
    assert decision.allowed is False
    assert decision.requires_approval is True
    assert decision.risk == RiskLevel.HIGH


def test_sweeper_times_out_orphan_postgres_rows() -> None:
    from app.core.hitl.sweeper import should_timeout_without_redis

    assert should_timeout_without_redis(claimed=True, redis_status="pending") is True
    assert should_timeout_without_redis(claimed=False, redis_status="pending") is False
    assert should_timeout_without_redis(claimed=False, redis_status="approved") is False
    assert should_timeout_without_redis(claimed=False, redis_status=None) is True
    assert should_timeout_without_redis(claimed=False, redis_status="timeout") is True


def test_timeout_never_auto_acks_money_or_legal() -> None:
    from app.core.hitl.fallback import may_auto_ack

    assert may_auto_ack({"action": "reply_common"}) is True
    assert may_auto_ack({"action": "payment"}) is False
    assert may_auto_ack({"action": "contract"}) is False
    assert may_auto_ack({"action": "change_price"}) is False
    assert may_auto_ack({"action": "delete_data"}) is False
    assert may_auto_ack(skill="send_email") is False
    assert may_auto_ack({}) is False
    assert may_auto_ack(skill="sales_agent") is False


def test_action_names_are_stable_and_sorted() -> None:
    actions = registered_actions()
    assert actions == tuple(sorted(actions))
    assert "payment" in actions
    assert "read_email" in actions
