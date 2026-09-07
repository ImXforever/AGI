"""Tests for v16 email follow-up system."""

from __future__ import annotations

import time

from app.core.email_followup import (
    FollowUpStatus,
    build_followup_message,
    create_followup,
    get_escalatable,
    get_pending_followups,
    get_rule,
    mark_cancelled,
    mark_completed,
    mark_followup_sent,
    should_escalate,
    should_followup,
)


class TestFollowUpCreation:
    def test_create_followup_basic(self):
        entry = create_followup(
            email_id="msg-001",
            sender="john@example.com",
            recipient="sales@company.com",
            subject="Price inquiry",
        )
        assert entry.status == FollowUpStatus.ACTIVE
        assert entry.followup_count == 0
        assert entry.email_id == "msg-001"

    def test_create_followup_urgent_rule(self):
        rule = get_rule("urgent")
        entry = create_followup(
            email_id="msg-002",
            sender="jane@example.com",
            recipient="support@company.com",
            subject="Urgent issue",
            rule=rule,
        )
        assert entry.rule_name == "urgent"
        assert entry.escalation_at > entry.created_at


class TestFollowUpLogic:
    def test_should_followup_after_delay(self):
        entry = create_followup(
            email_id="msg-003",
            sender="test@example.com",
            recipient="info@company.com",
            subject="Test",
        )
        assert not should_followup(entry)
        entry.next_followup_at = time.time() - 1
        assert should_followup(entry)

    def test_should_not_followup_when_completed(self):
        entry = create_followup(
            email_id="msg-004",
            sender="test@example.com",
            recipient="info@company.com",
            subject="Test",
        )
        entry = mark_completed(entry)
        assert not should_followup(entry)

    def test_should_escalate_after_timeout(self):
        entry = create_followup(
            email_id="msg-005",
            sender="test@example.com",
            recipient="info@company.com",
            subject="Test",
        )
        entry.escalation_at = time.time() - 1
        assert should_escalate(entry)

    def test_mark_followup_sent_increments_count(self):
        entry = create_followup(
            email_id="msg-006",
            sender="test@example.com",
            recipient="info@company.com",
            subject="Test",
        )
        entry = mark_followup_sent(entry)
        assert entry.followup_count == 1
        assert entry.last_followup_at is not None

    def test_mark_cancelled(self):
        entry = create_followup(
            email_id="msg-007",
            sender="test@example.com",
            recipient="info@company.com",
            subject="Test",
        )
        entry = mark_cancelled(entry)
        assert entry.status == FollowUpStatus.CANCELLED
        assert not should_followup(entry)


class TestFollowUpMessage:
    def test_first_followup_message(self):
        entry = create_followup(
            email_id="msg-008",
            sender="John",
            recipient="sales@company.com",
            subject="Price list",
        )
        msg = build_followup_message(entry, company_name="ACME")
        assert "John" in msg["body"]
        assert "ACME" in msg["body"]
        assert "Follow-up #1" in msg["subject"]

    def test_second_followup_message(self):
        entry = create_followup(
            email_id="msg-009",
            sender="Jane",
            recipient="sales@company.com",
            subject="Quote request",
        )
        entry.followup_count = 1
        msg = build_followup_message(entry)
        assert "Follow-up #2" in msg["subject"]


class TestFollowUpFiltering:
    def test_get_pending_followups(self):
        entries = [
            create_followup("m1", "a@b.com", "x@y.com", "S1"),
            create_followup("m2", "c@d.com", "e@f.com", "S2"),
        ]
        entries[0].next_followup_at = time.time() - 1
        pending = get_pending_followups(entries)
        assert len(pending) == 1
        assert pending[0].email_id == "m1"

    def test_get_escalatable(self):
        entries = [
            create_followup("m3", "a@b.com", "x@y.com", "S3"),
        ]
        entries[0].escalation_at = time.time() - 1
        esc = get_escalatable(entries)
        assert len(esc) == 1
