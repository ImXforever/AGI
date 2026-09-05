"""HITL execute_action is a real dispatcher gated by policy."""

from __future__ import annotations

from app.core.hitl.execute import execute_action, register_handler, reset_idempotency


def setup_function() -> None:
    reset_idempotency()


def test_auto_action_dispatches_ledger() -> None:
    out = execute_action("create_lead", {"email": "a@b.c"})
    assert out.executed is True
    assert out.result["status"] == "executed"
    assert "email" in out.result["payload_keys"]


def test_payment_without_approval_is_blocked() -> None:
    out = execute_action("payment", {"amount": 12400})
    assert out.executed is False
    assert out.ok is False


def test_payment_with_manager_approval_dispatches_ledger_only() -> None:
    out = execute_action("payment", {"amount": 12400}, actor_role="admin", approved=True)
    assert out.executed is True
    assert out.result["external"] is False
    assert out.result["mode"] == "hitl-dispatch"


def test_custom_handler_is_used() -> None:
    calls: list[str] = []

    def h(action: str, payload: dict, context: dict) -> dict:
        calls.append(action)
        return {"status": "executed", "echo": payload["n"]}

    register_handler("create_task", h)
    try:
        out = execute_action("create_task", {"n": 7})
        assert out.result["echo"] == 7
        assert calls == ["create_task"]
    finally:
        from app.core.hitl import execute as ex

        ex.register_handler("create_task", ex._audit_handler)


def test_idempotency_returns_same_object() -> None:
    a = execute_action("reply_common", {"k": 1}, idempotency_key="x")
    b = execute_action("reply_common", {"k": 2}, idempotency_key="x")
    assert a is b
