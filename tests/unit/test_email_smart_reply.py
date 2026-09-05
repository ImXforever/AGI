"""Tests for v16 email smart reply engine."""

from __future__ import annotations

from app.core.email_smart_reply import (
    list_templates,
    match_smart_reply,
    render_reply,
)


class TestSmartReplyMatch:
    def test_pricing_email_matched(self):
        result = match_smart_reply("Price inquiry", "What is the price of lubricant oil?")
        assert result is not None
        assert result.template_key == "pricing"
        assert result.confidence >= 0.6

    def test_availability_email_matched(self):
        result = match_smart_reply("Stock check", "Is drilling fluid available in stock?")
        assert result is not None
        assert result.template_key == "availability"

    def test_delivery_email_matched(self):
        result = match_smart_reply("Shipping", "When will my order be delivered?")
        assert result is not None
        assert result.template_key == "delivery"

    def test_catalog_request_matched(self):
        result = match_smart_reply("Catalog", "Please send me your product catalog")
        assert result is not None
        assert result.template_key == "catalog"

    def test_no_match_returns_none(self):
        result = match_smart_reply("Random subject", "This is completely unrelated content")
        assert result is None

    def test_arabic_keywords_matched(self):
        result = match_smart_reply("استفسار", "ما هو سعر زيت التخمير")
        assert result is not None

    def test_multiple_keywords_increase_confidence(self):
        result = match_smart_reply("Price and quote", "I need pricing and a quote for oil")
        assert result is not None
        assert result.confidence >= 0.7

    def test_render_reply_formats_correctly(self):
        match = match_smart_reply("Price inquiry", "What is the price?")
        assert match is not None
        rendered = render_reply(
            match,
            original_subject="Price inquiry",
            sender_name="John",
            company_name="ACME",
        )
        assert "John" in rendered["body"]
        assert "ACME" in rendered["body"]
        assert "Price inquiry" in rendered["subject"]

    def test_list_templates_returns_all(self):
        templates = list_templates()
        assert len(templates) >= 8
        assert all("key" in t for t in templates)
        assert all("keywords" in t for t in templates)


class TestSmartReplyEdgeCases:
    def test_empty_subject_body(self):
        result = match_smart_reply("", "")
        assert result is None

    def test_case_insensitive(self):
        result = match_smart_reply("PRICE", "WHAT IS THE PRICE")
        assert result is not None

    def test_warranty_email(self):
        result = match_smart_reply("Warranty question", "What is your warranty policy?")
        assert result is not None
        assert result.template_key == "warranty"

    def test_payment_terms_email(self):
        result = match_smart_reply("Payment", "What are your payment terms?")
        assert result is not None
        assert result.template_key == "payment_terms"

    def test_sample_request_email(self):
        result = match_smart_reply("Samples", "Can I get product samples?")
        assert result is not None
        assert result.template_key == "sample_request"
