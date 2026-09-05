"""Unit tests for the orchestrator's decision logic.

`handle_incoming` needs the full service stack, but the decisions it makes are
delegated to pure helpers: parsing the LLM's JSON, validating the resulting
classification, deciding whether a draft is usable, and building the honest
admission used when the system cannot answer. Those are tested here.
"""

from __future__ import annotations

import pytest

from app.core import orchestrator as orch

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# LLM JSON extraction — models rarely return clean JSON
# ---------------------------------------------------------------------------


class TestExtractJson:
    async def test_bare_json_object(self):
        assert await orch._extract_json('{"intent": "x"}') == {"intent": "x"}

    async def test_json_inside_a_fenced_code_block(self):
        assert await orch._extract_json('```json\n{"a": 1}\n```') == {"a": 1}

    async def test_json_inside_an_unlabelled_code_block(self):
        assert await orch._extract_json('```\n{"a": 1}\n```') == {"a": 1}

    async def test_json_surrounded_by_prose(self):
        raw = 'Sure! Here is the result:\n{"intent": "sales"}\nHope that helps.'
        assert await orch._extract_json(raw) == {"intent": "sales"}

    async def test_nested_braces_are_balanced_correctly(self):
        assert await orch._extract_json('{"a": {"b": 2}}') == {"a": {"b": 2}}

    async def test_text_without_any_object_yields_none(self):
        assert await orch._extract_json("no json here") is None

    async def test_malformed_json_yields_none_rather_than_raising(self):
        assert await orch._extract_json("{not valid json at all") is None

    async def test_empty_string_yields_none(self):
        assert await orch._extract_json("") is None


# ---------------------------------------------------------------------------
# Classification validation
# ---------------------------------------------------------------------------


class TestValidateClassification:
    def test_valid_payload_is_accepted(self):
        c = orch.validate_classification(
            {"intent": "price_request", "skill": "sales", "confidence": 0.9, "language": "en"}
        )
        assert c is not None
        assert c.intent == "price_request"
        assert c.confidence == 0.9
        assert c.language == "en"

    def test_missing_intent_is_rejected(self):
        assert orch.validate_classification({"skill": "sales", "confidence": 0.9}) is None

    def test_missing_skill_is_rejected(self):
        assert orch.validate_classification({"intent": "x", "confidence": 0.9}) is None

    def test_empty_dict_is_rejected(self):
        assert orch.validate_classification({}) is None

    @pytest.mark.parametrize("bad", [-0.5, 1.5, 99])
    def test_out_of_range_confidence_is_clamped_to_a_neutral_half(self, bad: float):
        c = orch.validate_classification({"intent": "x", "skill": "sales", "confidence": bad})
        assert c is not None and c.confidence == 0.5

    def test_unsupported_language_falls_back_to_default(self):
        c = orch.validate_classification(
            {"intent": "x", "skill": "sales", "confidence": 0.5, "language": "klingon"}
        )
        assert c is not None and c.language in (orch.LANG_AR, orch.LANG_EN)

    def test_input_is_case_insensitive_and_trimmed(self):
        c = orch.validate_classification(
            {"intent": "  PRICE  ", "skill": " SALES ", "confidence": 0.5}
        )
        assert c is not None and c.intent == "price"

    @pytest.mark.parametrize(
        "short,expected",
        [
            ("knowledge", orch.SKILL_KNOWLEDGE),
            ("customer", orch.SKILL_CUSTOMER),
            ("sales", orch.SKILL_SALES),
            ("support", orch.SKILL_SUPPORT),
            ("analytics", orch.SKILL_ANALYTICS),
            ("email", orch.SKILL_EMAIL),
            ("website", orch.SKILL_WEBSITE),
            ("social", orch.SKILL_SOCIAL),
            ("ops", orch.SKILL_OPS),
            ("greeting", orch.SKILL_ORCHESTRATOR),
            ("general", orch.SKILL_ORCHESTRATOR),
        ],
    )
    def test_short_skill_names_map_to_canonical_agents(self, short: str, expected: str):
        c = orch.validate_classification({"intent": "x", "skill": short, "confidence": 0.5})
        assert c is not None and c.skill == expected

    def test_unknown_skill_is_passed_through_untouched(self):
        c = orch.validate_classification({"intent": "x", "skill": "weather", "confidence": 0.5})
        assert c is not None and c.skill == "weather"

    def test_classification_serialises_without_the_raw_payload(self):
        c = orch.validate_classification({"intent": "x", "skill": "sales", "confidence": 0.5})
        assert c is not None
        assert set(c.as_dict()) == {"intent", "skill", "confidence", "language"}


# ---------------------------------------------------------------------------
# Safety routing
# ---------------------------------------------------------------------------


class TestSafetyDetection:
    def test_safety_markers_are_detected(self):
        assert any(orch._is_safety(m) for m in orch.SAFETY_MARKERS)

    def test_detection_is_case_insensitive(self):
        marker = next(iter(orch.SAFETY_MARKERS))
        assert orch._is_safety(marker.upper()) is True

    def test_ordinary_commercial_text_is_not_safety(self):
        assert orch._is_safety("what is the price of the 200L drum") is False

    def test_empty_text_is_not_safety(self):
        assert orch._is_safety("") is False


# ---------------------------------------------------------------------------
# RAG source handling
# ---------------------------------------------------------------------------


class TestRagSources:
    def test_sources_list_counts_as_grounding(self):
        assert orch._has_rag_sources({"sources": ["doc.pdf"]}) is True

    def test_metadata_source_counts_as_grounding(self):
        assert orch._has_rag_sources({"metadata": {"source": "msds.pdf"}}) is True

    def test_metadata_rag_results_count_as_grounding(self):
        assert orch._has_rag_sources({"metadata": {"rag_results": [{"source": "a"}]}}) is True

    def test_bare_result_is_ungrounded(self):
        assert orch._has_rag_sources({}) is False

    def test_empty_sources_list_is_ungrounded(self):
        assert orch._has_rag_sources({"sources": [], "metadata": {}}) is False

    def test_label_prefers_the_first_explicit_source(self):
        assert orch._extract_source_label({"sources": ["a.pdf", "b.pdf"]}) == "a.pdf"

    def test_label_falls_back_to_metadata_source(self):
        assert orch._extract_source_label({"metadata": {"source": "m.pdf"}}) == "m.pdf"

    def test_label_falls_back_to_first_rag_result(self):
        result = {"metadata": {"rag_results": [{"source": "r.pdf"}]}}
        assert orch._extract_source_label(result) == "r.pdf"

    def test_label_uses_rag_title_when_source_is_absent(self):
        result = {"metadata": {"rag_results": [{"title": "Spec Sheet"}]}}
        assert orch._extract_source_label(result) == "Spec Sheet"

    def test_no_source_yields_none(self):
        assert orch._extract_source_label({}) is None


class TestSourceCitation:
    def test_citation_is_appended(self):
        out = orch._append_source_citation("الجواب", "msds.pdf", orch.LANG_AR)
        assert "msds.pdf" in out and out.startswith("الجواب")

    def test_citation_is_not_duplicated_when_already_present(self):
        text = "see msds.pdf for details"
        assert orch._append_source_citation(text, "msds.pdf", "en") == text

    def test_empty_source_leaves_text_untouched(self):
        assert orch._append_source_citation("answer", "", "en") == "answer"

    def test_english_and_arabic_and_persian_use_different_templates(self):
        ar = orch._append_source_citation("x", "a.pdf", orch.LANG_AR)
        en = orch._append_source_citation("x", "a.pdf", "en")
        fa = orch._append_source_citation("x", "a.pdf", "fa")
        assert ar != en
        assert fa != en
        assert "منبع" in fa


# ---------------------------------------------------------------------------
# Honest admission — the anti-hallucination path
# ---------------------------------------------------------------------------


class TestHonestAdmission:
    def test_arabic_admission_lists_capabilities(self):
        text = orch._build_honest_admission(orch.LANG_AR)
        assert orch.HONEST_ADMISSION_AR in text
        assert "-" in text

    def test_english_admission_lists_capabilities(self):
        text = orch._build_honest_admission("en")
        assert orch.HONEST_ADMISSION_EN in text

    def test_persian_admission_lists_capabilities(self):
        text = orch._build_honest_admission("fa")
        assert orch.HONEST_ADMISSION_FA in text
        assert "-" in text

    def test_the_failing_skill_is_not_re_offered(self):
        """If sales just failed, don't suggest sales as an alternative."""
        text = orch._build_honest_admission("en", skill=orch.SKILL_SALES)
        assert "(sales)" not in text
        assert "(support)" in text

    def test_admissions_are_recognised_to_avoid_double_wrapping(self):
        assert orch._is_honest_admission_response(orch._build_honest_admission("en")) is True
        assert (
            orch._is_honest_admission_response(orch._build_honest_admission(orch.LANG_AR)) is True
        )
        assert (
            orch._is_honest_admission_response(orch._build_honest_admission("fa")) is True
        )

    def test_a_real_answer_is_not_mistaken_for_an_admission(self):
        assert orch._is_honest_admission_response("السعر 300 ريال للبرميل") is False


# ---------------------------------------------------------------------------
# Draft quality gate
# ---------------------------------------------------------------------------


class TestGibberishDetection:
    @pytest.mark.parametrize("text", ["", "  ", "ok", "!!!!", "1234567890", "...."])
    def test_unusable_drafts_are_rejected(self, text: str):
        assert orch._is_gibberish(text) is True

    @pytest.mark.parametrize(
        "text",
        [
            "السعر 300 ريال للبرميل الواحد",
            "The price is 300 SAR per drum.",
        ],
    )
    def test_real_answers_pass_the_gate(self, text: str):
        assert orch._is_gibberish(text) is False


class TestElapsed:
    def test_elapsed_is_a_non_negative_rounded_millisecond_value(self):
        import time

        value = orch._elapsed_ms(time.perf_counter())
        assert value >= 0
        assert round(value, 1) == value
