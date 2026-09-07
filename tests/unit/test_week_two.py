"""Week-two five: cron load, HITL ping, hold, outbound once, backup restore drill."""

from __future__ import annotations

import asyncio
import time

from app.core.conversation_hold import HOLD_NOTICE_EN, is_held, is_manager_sender
from app.core.email_followup import FollowUpEntry, FollowUpStatus, followup_from_row
from app.core.hitl.notify import build_pending_notice
from app.core.ops_jobs import run_calendar_publish, run_followup_check
from app.core.outbound import MemoryClaimStore, OutboundJob, deliver_once
from app.core.reporting import build_daily_report_from_db
from app.storage.backup_restore import backup_key_allowed, restore_backup


def test_cron_followup_empty_is_zero() -> None:
    out = asyncio.run(run_followup_check([]))
    assert out["pending"] == 0
    assert out["escalated"] == 0


def test_cron_followup_due_row_escalates() -> None:
    now = time.time()
    row = followup_from_row(
        {
            "id": "f1",
            "email_id": "e1",
            "sender": "a@b.c",
            "recipient": "ops@x",
            "subject": "hello",
            "category": "urgent",
            "rule_name": "urgent",
            "status": FollowUpStatus.ACTIVE,
            "created_at": now - 90000,
            "last_followup_at": None,
            "followup_count": 0,
            "next_followup_at": now + 3600,
            "escalation_at": now - 10,
        }
    )
    assert isinstance(row, FollowUpEntry)
    out = asyncio.run(run_followup_check([row]))
    assert out["escalated"] >= 1


def test_calendar_cron_does_not_publish_ads() -> None:
    from app.core.content_calendar import CalendarPost, CalendarPostStatus, ContentPlatform

    post = CalendarPost(
        id="p1",
        title="ad",
        caption="boost this post spend $50",
        platform=ContentPlatform.INSTAGRAM,
        scheduled_at=time.time() - 10,
        status=CalendarPostStatus.SCHEDULED,
        created_at=time.time(),
        published_at=None,
        post_id=None,
        media_url="",
        hashtags=(),
        created_by="admin",
        notes="",
    )
    out = asyncio.run(run_calendar_publish([post]))
    assert out["ready"] == 0
    assert out["published"] == 0


def test_daily_report_honors_count() -> None:
    report = build_daily_report_from_db([{"type": "incoming", "channel": "telegram", "count": 12}])
    assert report.total_messages == 12
    assert report.messages_by_channel["telegram"] == 12


def test_hitl_notice_contains_approval_id() -> None:
    text = build_pending_notice(approval_id="ap-9", action="create_quote", snippet="Q1")
    assert "ap-9" in text
    assert "create_quote" in text


def test_hold_skips_non_manager() -> None:
    assert is_held(redis_value="hitl") is True
    assert is_held(until=time.time() - 5, now=time.time()) is False
    assert is_manager_sender("99", [99, 100]) is True
    assert is_manager_sender("1", [99]) is False
    assert "manager" in HOLD_NOTICE_EN.lower()


def test_outbound_deliver_once() -> None:
    store = MemoryClaimStore()
    sent: list[str] = []

    def sender(job: OutboundJob) -> bool:
        sent.append(job.text)
        return True

    job = OutboundJob(channel="telegram", recipient_id="u1", text="hi", approval_id="a1")
    a = deliver_once(store, job, sender)
    b = deliver_once(store, job, sender)
    assert a.sent is True and a.duplicate is False
    assert b.duplicate is True and b.sent is False
    assert sent == ["hi"]


def test_courtesy_timeout_copy() -> None:
    from app.core.hitl.fallback import COURTESY_TIMEOUT_EN

    assert "business hours" in COURTESY_TIMEOUT_EN.lower()


def test_identity_merge_needs_hitl() -> None:
    from app.core.identity import plan_merge

    assert plan_merge("a", "b").allowed is False
    assert plan_merge("a", "a", approval_id="x").allowed is False
    assert plan_merge("a", "b", approval_id="ap-1").allowed is True


def test_channel_health_telegram_secret() -> None:
    from app.core.channel_health import is_red, snapshot

    red = snapshot(telegram_token="t", telegram_webhook_secret="")
    assert is_red(red) is True
    ok = snapshot(telegram_token="t", telegram_webhook_secret="secret-16-chars")
    assert is_red(ok) is False


def test_subject_access_needs_approval() -> None:
    from app.core.subject_access import build_export

    denied = build_export("c1")
    assert denied.allowed is False
    pack = build_export("c1", approval_id="ap-1", messages=[{"id": "m1"}])
    assert pack.allowed is True
    assert pack.records["messages"][0]["id"] == "m1"


def test_business_hours_weekend_closed() -> None:
    from datetime import datetime

    from app.core.business_hours import is_open, ooo_notice

    saturday = datetime(2026, 9, 5, 12, 0, 0)  # Saturday
    assert is_open(saturday) is False
    assert ooo_notice(open_now=False)


def test_restore_requires_approval_and_superadmin() -> None:
    denied = restore_backup("backups/pg.sql.gz", approval_id="", role="superadmin")
    assert denied.ok is False
    viewer = restore_backup("backups/pg.sql.gz", approval_id="ap-1", role="viewer")
    assert viewer.ok is False
    ok = restore_backup("backups/pg.sql.gz", approval_id="ap-1", role="superadmin")
    assert ok.ok is True and ok.applied is False and ok.verified is True
    assert backup_key_allowed("../etc/passwd") is False
