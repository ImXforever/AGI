"""Tests for v20 QA engine."""

from __future__ import annotations

from app.core.qa_engine import (
    auto_rewrite,
    check_response,
    score_response,
)


class TestQAScoring:
    def test_good_response_scores_high(self):
        score = score_response(
            "Our industrial lubricants are available in various grades. "
            "Please contact our sales team for pricing details.",
            original_question="What lubricants do you have?",
        )
        assert score.total >= 70

    def test_empty_response_scores_low(self):
        score = score_response("")
        assert score.total < 50

    def test_all_caps_penalized(self):
        score = score_response("THIS IS ALL CAPS AND VERY LOUD TEXT")
        assert score.tone < 80

    def test_casual_language_penalized(self):
        score = score_response("lol idk gonna check btw")
        assert score.tone < 60

    def test_profanity_penalized(self):
        score = score_response("This is stupid and damn annoying")
        assert score.tone < 50

    def test_credit_card_detected(self):
        score = score_response("Your card number is 4111 1111 1111 1111")
        assert score.safety < 80

    def test_email_detected(self):
        score = score_response("Contact john@example.com for details")
        assert score.safety < 80

    def test_uncertainty_penalized(self):
        score = score_response("I think maybe it probably could be available")
        assert score.accuracy < 80


class TestQACheck:
    def test_pass_above_threshold(self):
        check = check_response(
            "Our petroleum products include drilling fluids, lubricants, and chemicals. "
            "Contact our sales team for detailed pricing.",
            threshold=70,
        )
        assert check.passed is True

    def test_fail_below_threshold(self):
        check = check_response(
            "idk lol",
            threshold=70,
        )
        assert check.passed is False

    def test_rewrite_attempted(self):
        check = check_response(
            "LOL IDK GONNA CHECK",
            threshold=70,
        )
        assert check.rewritten is True


class TestAutoRewrite:
    def test_fix_all_caps(self):
        result = auto_rewrite("THIS IS A TEST.", ["ALL CAPS in text"])
        assert not result.isupper()

    def test_fix_exclamation(self):
        result = auto_rewrite("Great!!!", ["exclamation mark"])
        assert "!" not in result

    def test_fix_casual(self):
        result = auto_rewrite("I gonna wanna check lol", ["Casual language"])
        assert "gonna" not in result.lower()
        assert "wanna" not in result.lower()


class TestQAIntegration:
    def test_score_total_is_weighted(self):
        score = score_response(
            "We provide high-quality petroleum products. Our team is available 24/7 for support.",
            original_question="What do you offer?",
        )
        assert 0 <= score.total <= 100
        assert 0 <= score.clarity <= 100
        assert 0 <= score.tone <= 100
        assert 0 <= score.accuracy <= 100
