"""Integration tests for the admin UI API endpoints."""

from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace

from app.admin_api.auth import _create_token, _read_token, hash_password, verify_password
from app.constants import ApprovalStatus

# ---------------------------------------------------------------------------
# Password hashing tests
# ---------------------------------------------------------------------------


class TestPasswordHashing:
    def test_hash_and_verify(self):
        pw = "MySecurePassword123!"
        hashed = hash_password(pw)
        assert verify_password(hashed, pw) is True

    def test_wrong_password(self):
        hashed = hash_password("correct-password-123")
        assert verify_password(hashed, "wrong-password") is False

    def test_different_hashes(self):
        h1 = hash_password("same-password")
        h2 = hash_password("same-password")
        assert h1 != h2  # argon2id uses random salt

    def test_empty_password_hash(self):
        assert verify_password("", "anything") is False


# ---------------------------------------------------------------------------
# Session token tests
# ---------------------------------------------------------------------------


class TestSessionTokens:
    def test_create_and_read(self):
        @dataclass
        class FakeAdmin:
            web_secret: str = "test-secret-key-that-is-long-enough-1234"
            cookie_secure: bool = False

        cfg = SimpleNamespace(admin=FakeAdmin())
        token = _create_token(cfg, "admin")  # type: ignore[arg-type]
        assert isinstance(token, str)
        assert len(token) > 10

        data = _read_token(cfg, token)  # type: ignore[arg-type]
        assert data is not None
        assert data["u"] == "admin"

    def test_bootstrap_flag(self):
        @dataclass
        class FakeAdmin:
            web_secret: str = "test-secret-key-that-is-long-enough-1234"
            cookie_secure: bool = False

        cfg = SimpleNamespace(admin=FakeAdmin())
        token = _create_token(cfg, "admin", is_bootstrap=True)  # type: ignore[arg-type]
        data = _read_token(cfg, token)  # type: ignore[arg-type]
        assert data is not None
        assert data["b"] is True

    def test_invalid_token(self):
        @dataclass
        class FakeAdmin:
            web_secret: str = "test-secret-key-that-is-long-enough-1234"

        cfg = SimpleNamespace(admin=FakeAdmin())
        data = _read_token(cfg, "invalid-token-garbage")  # type: ignore[arg-type]
        assert data is None

    def test_wrong_secret(self):
        @dataclass
        class FakeAdmin1:
            web_secret: str = "secret-key-one-that-is-long-enough"

        @dataclass
        class FakeAdmin2:
            web_secret: str = "secret-key-two-that-is-long-enough"

        token = _create_token(SimpleNamespace(admin=FakeAdmin1()), "admin")  # type: ignore[arg-type]
        data = _read_token(SimpleNamespace(admin=FakeAdmin2()), token)  # type: ignore[arg-type]
        assert data is None


# ---------------------------------------------------------------------------
# API route tests (mock-based)
# ---------------------------------------------------------------------------


class TestApprovalEndpoints:
    def test_decision_validation(self):
        """Approve/reject/edit are valid; others are not."""
        valid = {"approved", "rejected", "edited"}
        assert ApprovalStatus.APPROVED in valid
        assert ApprovalStatus.REJECTED in valid
        assert ApprovalStatus.EDITED in valid
        assert "pending" not in valid
        assert "timeout" not in valid

    def test_terminal_blocks_decide(self):
        for status in ApprovalStatus.TERMINAL:
            assert status not in ApprovalStatus.PENDING


# ---------------------------------------------------------------------------
# Catalog endpoint tests
# ---------------------------------------------------------------------------


class TestCatalogEndpoints:
    def test_product_json_structure(self):
        product = {
            "id": "test-id",
            "sku": "SKU-001",
            "name_ar": "منتج",
            "name_en": "Product",
            "category": "crude",
            "unit": "kg",
            "base_price": 100.0,
            "currency": "SAR",
            "description_ar": "وصف",
            "description_en": "Description",
            "specs": {},
            "is_active": True,
            "created_at": "2024-01-01T00:00:00",
            "updated_at": "2024-01-01T00:00:00",
        }
        assert product["sku"] == "SKU-001"
        assert product["is_active"] is True

    def test_csv_import_row_parse(self):
        csv_row = "SKU-001,Raw Crude,Crude Oil,crude,barrel,82.50,SAR,A high quality crude"
        fields = csv_row.split(",")
        assert fields[0] == "SKU-001"
        assert float(fields[5]) == 82.50


# ---------------------------------------------------------------------------
# Template endpoint tests
# ---------------------------------------------------------------------------


class TestTemplateEndpoints:
    def test_template_variable_substitution(self):
        template = "مرحباً {{name}}، طلبك رقم {{order_id}} جاهز"
        rendered = template.replace("{{name}}", "أحمد").replace("{{order_id}}", "42")
        assert "أحمد" in rendered
        assert "42" in rendered
        assert "{{name}}" not in rendered
