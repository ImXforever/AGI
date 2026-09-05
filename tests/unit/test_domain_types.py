"""Unit tests for the domain model and the reply postprocessor.

`app.core.types` carries the ticket state machine that every conversation walks
through, and `app.core.postprocess` is the last thing that touches a message
before it reaches a customer. Both were previously untested.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.core import postprocess
from app.core.types import (
    AgentResult,
    InboundMessage,
    ProposedAction,
    ProposedResponse,
    TicketState,
)

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class TestInboundMessage:
    def test_minimal_valid_message(self):
        msg = InboundMessage(
            channel="telegram",
            external_user_id="42",
            text="مرحبا",
            provider_message_id="m-1",
        )
        assert msg.attachments == [] and msg.raw == {}
        assert msg.display_name is None

    def test_unknown_channel_is_rejected(self):
        with pytest.raises(ValidationError):
            InboundMessage(
                channel="carrier-pigeon",  # type: ignore[arg-type]
                external_user_id="42",
                text="hi",
                provider_message_id="m-1",
            )

    def test_missing_required_field_is_rejected(self):
        with pytest.raises(ValidationError):
            InboundMessage(channel="telegram", external_user_id="42", text="hi")  # type: ignore[call-arg]


class TestProposedResponse:
    def _valid(self, **over):
        base = dict(
            customer_reply_ar="مرحبا بك",
            rationale_ar="ترحيب",
            specialist="sales",
        )
        base.update(over)
        return ProposedResponse(**base)  # type: ignore[arg-type]

    def test_defaults_are_conservative(self):
        r = self._valid()
        assert r.risk == "low"
        assert r.language == "ar"
        assert r.citations == [] and r.actions == []

    def test_reply_shorter_than_two_chars_is_rejected(self):
        with pytest.raises(ValidationError):
            self._valid(customer_reply_ar="x")

    def test_reply_longer_than_4000_chars_is_rejected(self):
        with pytest.raises(ValidationError):
            self._valid(customer_reply_ar="ا" * 4001)

    def test_unknown_specialist_is_rejected(self):
        with pytest.raises(ValidationError):
            self._valid(specialist="astrologer")

    def test_unknown_action_type_is_rejected(self):
        with pytest.raises(ValidationError):
            ProposedAction(type="drop_database")  # type: ignore[arg-type]

    def test_actions_default_to_reversible(self):
        assert ProposedAction(type="draft_quote").reversible is True


# ---------------------------------------------------------------------------
# Ticket state machine
# ---------------------------------------------------------------------------


class TestTicketState:
    def _ticket(self) -> TicketState:
        return TicketState(
            ticket_id="T-1", tenant_id="t", channel="telegram", external_user_id="42"
        )

    def test_initial_state_is_received_and_low_risk(self):
        t = self._ticket()
        assert t.status == "received" and t.risk == "low"
        assert t.history == []

    def test_transition_records_an_audit_trail_entry(self):
        t = self._ticket()
        t.transition("processing")
        assert t.status == "processing"
        assert t.history == [{"from": "received", "to": "processing"}]

    def test_history_accumulates_across_transitions(self):
        t = self._ticket()
        t.transition("processing")
        t.transition("answered")
        assert [h["to"] for h in t.history] == ["processing", "answered"]
        assert t.history[1]["from"] == "processing"

    def test_escalation_raises_risk_and_routes_to_support(self):
        t = self._ticket()
        t.escalate("gas leak reported")
        assert t.risk == "high"
        assert t.specialist == "support"
        assert t.status == "needs_human"
        assert t.history[-1]["reason"] == "gas leak reported"

    def test_escalation_reason_is_optional(self):
        t = self._ticket()
        t.escalate()
        assert t.history[-1]["reason"] == ""


class TestAgentResult:
    def test_conversion_carries_risk_and_citations(self):
        result = AgentResult(
            success=True,
            response="الجواب هنا",
            risk="high",
            specialist="sales",
            citations=["doc-1"],
            metadata={"rationale": "لأن"},
        )
        proposed = result.to_proposed_response()
        assert proposed.customer_reply_ar == "الجواب هنا"
        assert proposed.risk == "high"
        assert proposed.citations == ["doc-1"]
        assert proposed.rationale_ar == "لأن"

    def test_missing_specialist_defaults_to_support(self):
        result = AgentResult(success=True, response="نعم")
        assert result.to_proposed_response().specialist == "support"

    def test_actions_are_converted_into_proposed_actions(self):
        result = AgentResult(
            success=True,
            response="تم",
            actions=[{"type": "draft_quote", "payload": {"sku": "X"}}],
        )
        actions = result.to_proposed_response().actions
        assert len(actions) == 1
        assert actions[0].type == "draft_quote"
        assert actions[0].payload == {"sku": "X"}

    def test_malformed_action_falls_back_to_none_type(self):
        result = AgentResult(success=True, response="تم", actions=[{}])
        assert result.to_proposed_response().actions[0].type == "none"


# ---------------------------------------------------------------------------
# Postprocess
# ---------------------------------------------------------------------------


class TestPostprocessHelpers:
    def test_control_characters_are_stripped(self):
        assert "\x00" not in postprocess._sanitize("ab\x00c")

    def test_bidi_override_characters_are_stripped(self):
        """Bidi overrides can visually disguise text — they must not survive."""
        assert postprocess._sanitize("a\u202eb") == "ab"

    def test_runs_of_spaces_collapse(self):
        assert postprocess._sanitize("a     b") == "a b"

    def test_more_than_two_newlines_collapse_to_two(self):
        assert postprocess._sanitize("a\n\n\n\n\nb") == "a\n\nb"

    def test_paragraphs_are_not_welded_together(self):
        """Regression: the MULTILINE strip used to eat the newlines themselves,
        turning "para one\n\n\npara two" into "para onepara two"."""
        assert postprocess._sanitize("para one\n\n\npara two") == "para one\n\npara two"

    def test_per_line_indentation_is_stripped_without_joining_lines(self):
        assert postprocess._sanitize("  a  \n  b  ") == "a\nb"

    def test_code_blocks_are_removed(self):
        assert "print" not in postprocess._strip_unwanted("before ```print(1)``` after")

    def test_markdown_links_are_removed(self):
        assert "http" not in postprocess._strip_unwanted("see [here](http://x.com)")

    def test_arabic_ratio_check_is_non_destructive(self):
        text = "this is mostly latin text with no arabic"
        assert postprocess._verify_arabic_ratio(text) == text

    def test_arabic_ratio_check_tolerates_empty(self):
        assert postprocess._verify_arabic_ratio("") == ""

    def test_digit_swap_produces_arabic_indic(self):
        assert postprocess._arabic_digit_swap("2024") == "٢٠٢٤"


class TestPostprocessRun:
    def test_clean_text_needs_no_fixes(self, monkeypatch: pytest.MonkeyPatch):
        report = postprocess.run("مرحبا بك", config=_cfg(monkeypatch))
        assert report.fixes_applied == []
        assert report.sanitized is False
        assert report.has_content is True

    def test_report_records_before_and_after_lengths(self, monkeypatch: pytest.MonkeyPatch):
        report = postprocess.run("a     b", config=_cfg(monkeypatch))
        assert report.original_length == 7
        assert report.final_length == len(report.text) == 3
        assert "sanitize" in report.fixes_applied

    def test_empty_text_reports_no_content(self, monkeypatch: pytest.MonkeyPatch):
        assert postprocess.run("", config=_cfg(monkeypatch)).has_content is False

    def test_whitespace_only_reports_no_content(self, monkeypatch: pytest.MonkeyPatch):
        assert postprocess.run("   \n  ", config=_cfg(monkeypatch)).has_content is False

    def test_arabic_indic_conversion_is_applied_when_configured(
        self, monkeypatch: pytest.MonkeyPatch
    ):
        report = postprocess.run(
            "السعر 300", config=_cfg(monkeypatch, numeral_style="arabic-indic")
        )
        assert "٣٠٠" in report.text
        assert "arabic_indic_digits" in report.fixes_applied

    def test_western_digits_survive_when_not_configured(self, monkeypatch: pytest.MonkeyPatch):
        report = postprocess.run("السعر 300", config=_cfg(monkeypatch, numeral_style="western"))
        assert "300" in report.text

    def test_report_serialises_to_a_dict(self, monkeypatch: pytest.MonkeyPatch):
        d = postprocess.run("مرحبا", config=_cfg(monkeypatch)).as_dict()
        assert set(d) == {
            "text",
            "original_length",
            "final_length",
            "fixes_applied",
            "language",
            "has_content",
            "sanitized",
        }


class _Domain:
    def __init__(self, numeral_style: str) -> None:
        self.numeral_style = numeral_style


class _Cfg:
    def __init__(self, numeral_style: str) -> None:
        self.domain = _Domain(numeral_style)


def _cfg(monkeypatch: pytest.MonkeyPatch, numeral_style: str = "western"):
    """A minimal config stub — postprocess only reads domain.numeral_style."""
    return _Cfg(numeral_style)
