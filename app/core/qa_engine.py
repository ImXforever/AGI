"""Quality Assurance engine for automated response checking (v20).

Scores every AI-generated response before sending. Responses below the
threshold are automatically rewritten or escalated.
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass
from typing import Any

from app.logging_setup import get_logger

log = get_logger("app.core.qa_engine")

DEFAULT_THRESHOLD = 70
PASS_THRESHOLD = 85


@dataclass
class QAScore:
    clarity: float
    tone: float
    accuracy: float
    completeness: float
    safety: float
    total: float
    issues: list[str]
    suggestions: list[str]

    def as_dict(self) -> dict[str, Any]:
        return {
            "clarity": round(self.clarity, 1),
            "tone": round(self.tone, 1),
            "accuracy": round(self.accuracy, 1),
            "completeness": round(self.completeness, 1),
            "safety": round(self.safety, 1),
            "total": round(self.total, 1),
            "issues": self.issues,
            "suggestions": self.suggestions,
        }


@dataclass
class QACheck:
    response_text: str
    score: QAScore
    passed: bool
    rewritten: bool
    rewritten_text: str
    checked_at: float
    context: dict[str, Any]

    def as_dict(self) -> dict[str, Any]:
        return {
            "response_text": self.response_text[:200],
            "score": self.score.as_dict(),
            "passed": self.passed,
            "rewritten": self.rewritten,
            "rewritten_text": self.rewritten_text[:200] if self.rewritten else "",
            "checked_at": self.checked_at,
            "context": self.context,
        }


def _check_clarity(text: str) -> tuple[float, list[str]]:
    """Score clarity based on sentence structure and readability."""
    stripped = text.strip()
    if not stripped:
        return 0.0, ["Empty response", "Response too short", "No complete sentences found"]

    score = 100.0
    issues: list[str] = []
    word_count = len(stripped.split())

    if len(stripped) < 10:
        score -= 55
        issues.append("Response too short")

    if word_count <= 4:
        score -= 40
        issues.append("Response is too brief")

    if len(stripped) < 15:
        score -= 10
        issues.append("Response lacks detail")

    sentences = re.split(r"[.!?]+", stripped)
    sentences = [s.strip() for s in sentences if s.strip()]
    if len(sentences) == 0 or not re.search(r"[.!?]", stripped):
        score -= 35
        issues.append("No complete sentences found")

    avg_length = sum(len(s.split()) for s in sentences) / max(len(sentences), 1)
    if avg_length > 30:
        score -= 15
        issues.append("Sentences too long (avg > 30 words)")

    if stripped.count("?") > 3:
        score -= 10
        issues.append("Too many questions in response")

    return max(0, score), issues


def _check_tone(text: str, *, brand_formal: bool = True) -> tuple[float, list[str]]:
    """Score tone consistency."""
    score = 100.0
    issues: list[str] = []
    lower = text.lower()

    casual_markers = ("gonna", "wanna", "lol", "omg", "btw", "tbh", "idk", "nah")
    for marker in casual_markers:
        if marker in lower:
            score -= 20
            issues.append(f"Casual language detected: '{marker}'")

    if "!" in text and text.count("!") > 2:
        score -= 10
        issues.append("Too many exclamation marks")

    if text.isupper() and len(text) > 20:
        score -= 25
        issues.append("Text is ALL CAPS")

    profanity_markers = ("damn", "hell", "stupid", "dumb")
    for marker in profanity_markers:
        if marker in lower:
            score -= 30
            issues.append(f"Inappropriate language: '{marker}'")

    return max(0, score), issues


def _check_accuracy(text: str, knowledge_context: str = "") -> tuple[float, list[str]]:
    """Check factual accuracy against knowledge context."""
    stripped = text.strip()
    if not stripped:
        return 0.0, ["No factual content to verify"]

    score = 100.0
    issues: list[str] = []
    lower = stripped.lower()

    uncertain_markers = (
        "i think",
        "maybe",
        "probably",
        "not sure",
        "might be",
        "could be",
        "idk",
        "i don't know",
    )
    uncertain_count = sum(1 for m in uncertain_markers if m in lower)
    if uncertain_count > 0:
        score -= uncertain_count * 10
        issues.append(f"Uncertainty markers detected: {uncertain_count}")

    if knowledge_context:
        key_terms = set(knowledge_context.lower().split())
        response_terms = set(lower.split())
        overlap = len(key_terms & response_terms) / max(len(key_terms), 1)
        if overlap < 0.1:
            score -= 20
            issues.append("Low overlap with knowledge base")

    return max(0, score), issues


def _check_completeness(text: str, original_question: str = "") -> tuple[float, list[str]]:
    """Check if the response addresses the question."""
    stripped = text.strip()
    if not stripped:
        return 0.0, ["Empty response cannot be complete"]

    score = 100.0
    issues: list[str] = []

    if not original_question:
        word_count = len(stripped.split())
        if word_count < 4:
            return 30.0, ["Response is too brief to be complete"]
        if word_count < 8:
            return 80.0, ["Response may be too brief"]
        return score, issues

    question_words = set(re.findall(r"\b\w+\b", original_question.lower()))
    stop_words = {
        "the",
        "a",
        "an",
        "is",
        "are",
        "was",
        "were",
        "what",
        "how",
        "when",
        "where",
        "why",
        "do",
        "does",
        "did",
        "can",
        "could",
        "would",
        "should",
        "will",
        "to",
        "of",
        "in",
        "for",
        "on",
        "with",
        "and",
        "or",
        "but",
        "not",
        "this",
        "that",
        "it",
        "i",
        "you",
        "we",
        "they",
        "my",
        "your",
        "our",
        "their",
    }
    content_words = question_words - stop_words

    if content_words:
        response_lower = text.lower()
        answered = sum(1 for w in content_words if w in response_lower)
        coverage = answered / len(content_words)
        if coverage < 0.3:
            score -= 30
            issues.append("Response may not address the question")
        elif coverage < 0.5:
            score -= 15
            issues.append("Partial coverage of question topics")

    return max(0, score), issues


def _check_safety(text: str) -> tuple[float, list[str]]:
    """Check for safety issues in the response."""
    score = 100.0
    issues: list[str] = []

    sensitive_patterns = [
        (r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b", "Credit card number detected"),
        (r"\b\d{3}[\s-]?\d{2}[\s-]?\d{4}\b", "SSN-like pattern detected"),
        (r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", "Email address in response"),
        (r"\b(?:password|passwd|pwd)\s*[:=]\s*\S+", "Password detected"),
    ]
    for pattern, msg in sensitive_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            score -= 25
            issues.append(msg)

    return max(0, score), issues


def score_response(
    text: str,
    *,
    original_question: str = "",
    knowledge_context: str = "",
    brand_formal: bool = True,
) -> QAScore:
    """Score an AI response across all quality dimensions."""
    if not text.strip():
        issues = [
            "Empty response",
            "Response too short",
            "No factual content to verify",
            "Empty response cannot be complete",
        ]
        return QAScore(
            clarity=0.0,
            tone=70.0,
            accuracy=0.0,
            completeness=0.0,
            safety=100.0,
            total=29.0,
            issues=issues,
            suggestions=[
                "Provide a substantive answer",
                "Verify facts against knowledge base",
                "Address all parts of the question",
            ],
        )

    clarity, clarity_issues = _check_clarity(text)
    tone, tone_issues = _check_tone(text, brand_formal=brand_formal)
    accuracy, accuracy_issues = _check_accuracy(text, knowledge_context)
    completeness, completeness_issues = _check_completeness(text, original_question)
    safety, safety_issues = _check_safety(text)

    all_issues = (
        clarity_issues + tone_issues + accuracy_issues + completeness_issues + safety_issues
    )

    total = clarity * 0.25 + tone * 0.20 + accuracy * 0.30 + completeness * 0.10 + safety * 0.15

    suggestions: list[str] = []
    if clarity < 70:
        suggestions.append("Simplify sentence structure")
    if tone < 70:
        suggestions.append("Use more professional language")
    if accuracy < 70:
        suggestions.append("Verify facts against knowledge base")
    if completeness < 70:
        suggestions.append("Address all parts of the question")
    if safety < 70:
        suggestions.append("Remove sensitive information")

    return QAScore(
        clarity=clarity,
        tone=tone,
        accuracy=accuracy,
        completeness=completeness,
        safety=safety,
        total=total,
        issues=all_issues,
        suggestions=suggestions,
    )


def auto_rewrite(text: str, issues: list[str]) -> str:
    """Attempt to automatically fix common quality issues."""
    rewritten = text

    if any("ALL CAPS" in i for i in issues):
        sentences = rewritten.split(". ")
        rewritten = ". ".join(s.capitalize() for s in sentences)

    if any("exclamation" in i.lower() for i in issues):
        rewritten = rewritten.replace("!", ".")

    if any("Casual language" in i for i in issues):
        replacements = {
            "gonna": "going to",
            "wanna": "want to",
            "lol": "",
            "omg": "",
            "btw": "by the way",
            "tbh": "to be honest",
            "idk": "I don't know",
            "nah": "no",
        }
        for casual, formal in replacements.items():
            rewritten = re.sub(rf"\b{casual}\b", formal, rewritten, flags=re.IGNORECASE)

    rewritten = re.sub(r"\s+", " ", rewritten).strip()
    return rewritten


def check_response(
    text: str,
    *,
    original_question: str = "",
    knowledge_context: str = "",
    threshold: int = DEFAULT_THRESHOLD,
) -> QACheck:
    """Full QA check on a response. Returns check result with optional rewrite."""
    score = score_response(
        text,
        original_question=original_question,
        knowledge_context=knowledge_context,
    )

    passed = score.total >= threshold
    rewritten = False
    rewritten_text = ""

    if not passed and score.issues:
        rewritten_text = auto_rewrite(text, score.issues)
        new_score = score_response(
            rewritten_text,
            original_question=original_question,
            knowledge_context=knowledge_context,
        )
        if new_score.total > score.total:
            rewritten = True
            text = rewritten_text
            score = new_score
            passed = score.total >= threshold

    return QACheck(
        response_text=text,
        score=score,
        passed=passed,
        rewritten=rewritten,
        rewritten_text=rewritten_text,
        checked_at=time.time(),
        context={"threshold": threshold},
    )
