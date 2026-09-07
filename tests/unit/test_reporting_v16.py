"""Tests for v16 extended reporting."""

from __future__ import annotations

from app.core.reporting import (
    DailyReport,
    EmailReport,
    WebsiteReport,
    build_daily_report_from_db,
    build_email_report_from_db,
    build_website_report_from_db,
)


class TestDailyReport:
    def test_build_from_empty_rows(self):
        report = build_daily_report_from_db([], date="2025-01-01")
        assert report.date == "2025-01-01"
        assert report.total_messages == 0
        assert report.errors == 0

    def test_build_from_rows(self):
        rows = [
            {"channel": "telegram", "type": "incoming", "category": "support"},
            {"channel": "email", "type": "email_received", "category": "sales"},
            {"channel": "email", "type": "email_auto_replied", "category": "sales"},
            {"channel": "telegram", "type": "error", "category": ""},
            {"type": "task_created", "channel": "", "category": ""},
            {"type": "approval_pending", "channel": "", "category": ""},
            {"response_time_ms": 150.0, "type": "incoming", "channel": "", "category": ""},
            {"response_time_ms": 250.0, "type": "incoming", "channel": "", "category": ""},
        ]
        report = build_daily_report_from_db(rows, date="2025-06-15")
        assert report.total_messages in (3, 8)
        assert report.emails_received == 1
        assert report.emails_auto_replied == 1
        assert report.errors == 1
        assert report.tasks_created == 1
        assert report.approvals_pending == 1
        assert report.average_response_ms == 200.0

    def test_to_text(self):
        report = DailyReport(
            date="2025-01-01",
            total_messages=10,
            messages_by_channel={"telegram": 5, "email": 5},
            messages_by_category={"support": 3, "sales": 7},
            emails_received=5,
            emails_auto_replied=2,
            emails_escalated=1,
            tasks_created=3,
            tasks_completed=2,
            approvals_pending=1,
            approvals_completed=4,
            errors=0,
            average_response_ms=150.0,
        )
        text = report.to_text()
        assert "2025-01-01" in text
        assert "10" in text
        assert "Telegram: 5" in text

    def test_as_dict(self):
        report = build_daily_report_from_db([], date="2025-01-01")
        d = report.as_dict()
        assert "date" in d
        assert "total_messages" in d
        assert "emails_received" in d


class TestEmailReport:
    def test_build_from_empty_rows(self):
        report = build_email_report_from_db([], period="2025-01-01")
        assert report.total_received == 0
        assert report.period == "2025-01-01"

    def test_build_from_rows(self):
        rows = [
            {"category": "sales", "status": "received", "response_time_ms": 100.0},
            {"category": "sales", "status": "auto_replied", "response_time_ms": 50.0},
            {"category": "support", "status": "escalated", "response_time_ms": 200.0},
            {"category": "support", "status": "pending", "response_time_ms": None},
            {"category": "sales", "status": "received", "followup_sent": True},
        ]
        report = build_email_report_from_db(rows, period="2025-06-15")
        assert report.total_received == 2
        assert report.auto_replied == 1
        assert report.escalated == 1
        assert report.pending == 1
        assert report.followups_sent == 1
        assert report.average_response_ms == 116.67

    def test_to_text(self):
        report = EmailReport(
            period="2025-01-01",
            total_received=10,
            total_sent=5,
            auto_replied=3,
            escalated=1,
            pending=1,
            by_category={"sales": 6, "support": 4},
            average_response_ms=120.0,
            followups_sent=2,
            followups_completed=1,
        )
        text = report.to_text()
        assert "2025-01-01" in text
        assert "Received: 10" in text


class TestWebsiteReport:
    def test_build_from_empty_rows(self):
        report = build_website_report_from_db([], period="2025-01-01")
        assert report.contact_forms_received == 0

    def test_build_from_rows(self):
        rows = [
            {"type": "contact_form", "processed": True, "change_type": None, "approved": None},
            {"type": "contact_form", "processed": False, "change_type": None, "approved": None},
            {"type": "content_change", "change_type": "price", "approved": True, "processed": None},
            {
                "type": "content_change",
                "change_type": "content",
                "approved": False,
                "processed": None,
            },
            {"type": "product_updated", "change_type": None, "approved": None, "processed": None},
        ]
        report = build_website_report_from_db(rows, period="2025-06-15")
        assert report.contact_forms_received == 2
        assert report.contact_forms_processed == 1
        assert report.contact_forms_pending == 1
        assert report.content_changes == 2
        assert report.content_changes_approved == 1
        assert report.products_updated == 1
        assert report.by_change_type.get("price") == 1

    def test_to_text(self):
        report = WebsiteReport(
            period="2025-01-01",
            contact_forms_received=5,
            contact_forms_processed=3,
            contact_forms_pending=2,
            content_changes=4,
            content_changes_approved=2,
            content_changes_pending=2,
            products_updated=1,
            errors_detected=0,
            by_change_type={"content": 2, "price": 2},
        )
        text = report.to_text()
        assert "2025-01-01" in text
        assert "Contact Forms: 5" in text
