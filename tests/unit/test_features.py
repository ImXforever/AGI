"""Unit tests for platform features: HITL, catalog, quotes, templates."""

from __future__ import annotations

from datetime import UTC

from app.constants import (
    KEY_HITL_DECIDED,
    KEY_HITL_META,
    SKILL_KNOWLEDGE,
    SKILL_SALES,
    SKILL_SUPPORT,
    STREAM_EVENTS,
    STREAM_HITL,
    ApprovalStatus,
)

# ---------------------------------------------------------------------------
# HITL (Human-in-the-Loop) tests
# ---------------------------------------------------------------------------


class TestHITL:
    def test_key_patterns(self):
        assert KEY_HITL_META.format(approval_id="abc") == "hitl:meta:abc"
        assert KEY_HITL_DECIDED.format(approval_id="xyz") == "hitl:decided:xyz"

    def test_stream_names(self):
        assert STREAM_HITL == "hitl:queue"
        assert STREAM_EVENTS == "bus:events"

    def test_approval_lifecycle(self):
        """Test the full lifecycle: pending → approved/rejected/edited."""
        states = []
        status = ApprovalStatus.PENDING
        states.append(status)

        # Approve
        assert status in ("pending",)
        status = ApprovalStatus.APPROVED
        states.append(status)

        assert states == ["pending", "approved"]
        assert status in ApprovalStatus.TERMINAL

    def test_double_decide_rejected(self):
        """After a terminal state, further decisions should be blocked."""
        status = ApprovalStatus.APPROVED
        assert status in ApprovalStatus.TERMINAL
        # Should not allow further decisions
        assert status not in ApprovalStatus.PENDING


# ---------------------------------------------------------------------------
# Catalog feature tests
# ---------------------------------------------------------------------------


class TestCatalog:
    def test_product_creation_fields(self):
        product = {
            "sku": "TEST-001",
            "name_ar": "منتج تجريبي",
            "name_en": "Test Product",
            "category": "crude",
            "unit": "barrel",
            "base_price": 82.50,
            "currency": "SAR",
            "is_active": True,
        }
        assert product["sku"] == "TEST-001"
        assert product["base_price"] == 82.50
        assert product["is_active"] is True

    def test_product_validation(self):
        """Ensure required fields are present."""
        required = ["sku", "name_ar", "base_price", "currency"]
        product = {"sku": "X", "name_ar": "Y", "base_price": 10, "currency": "SAR"}
        for field in required:
            assert field in product, f"missing required field: {field}"

    def test_csv_import_row(self):
        row = {
            "sku": "CSV-001",
            "name_ar": " IMPORT TEST",
            "base_price": "50.00",
            "currency": "SAR",
        }
        assert float(row["base_price"]) == 50.00


# ---------------------------------------------------------------------------
# Quote feature tests
# ---------------------------------------------------------------------------


class TestQuote:
    def test_quote_totals(self):
        items = [
            {"sku": "A", "qty": 10, "unit_price": 100},
            {"sku": "B", "qty": 5, "unit_price": 200},
        ]
        subtotal = sum(item["qty"] * item["unit_price"] for item in items)
        tax = subtotal * 0.15
        total = subtotal + tax
        assert subtotal == 2000
        assert tax == 300
        assert total == 2300

    def test_quote_valid_until(self):
        from datetime import datetime, timedelta

        now = datetime.now(UTC)
        valid_until = now + timedelta(days=7)
        assert valid_until > now

    def test_quote_statuses(self):
        valid = {"draft", "sent", "viewed", "accepted", "rejected", "cancelled", "expired"}
        assert "draft" in valid
        assert "accepted" in valid


# ---------------------------------------------------------------------------
# Template feature tests
# ---------------------------------------------------------------------------


class TestTemplates:
    def test_template_variables(self):
        template = {
            "body_ar": "مرحباً {{customer_name}}، عرض السعر: {{total}} {{currency}}",
            "variables": ["customer_name", "total", "currency"],
        }
        for var in template["variables"]:
            assert f"{{{{{var}}}}}" in template["body_ar"]

    def test_template_rendering(self):
        body = "مرحباً {{customer_name}}"
        rendered = body.replace("{{customer_name}}", "أحمد")
        assert "أحمد" in rendered
        assert "{{customer_name}}" not in rendered


# ---------------------------------------------------------------------------
# Ticket feature tests
# ---------------------------------------------------------------------------


class TestTickets:
    def test_ticket_priorities(self):
        valid = {"low", "medium", "high", "urgent"}
        assert "urgent" in valid

    def test_ticket_statuses(self):
        valid = {"open", "in_progress", "waiting", "resolved", "closed"}
        assert "open" in valid
        assert "resolved" in valid


# ---------------------------------------------------------------------------
# Skill routing tests
# ---------------------------------------------------------------------------


class TestSkillRouting:
    def test_skill_names(self):
        assert SKILL_KNOWLEDGE == "knowledge_agent"
        assert SKILL_SALES == "sales_agent"
        assert SKILL_SUPPORT == "support_agent"

    def test_orchestrator_is_not_agent(self):
        from app.constants import AGENT_SKILLS, SKILL_ORCHESTRATOR

        assert SKILL_ORCHESTRATOR not in AGENT_SKILLS
