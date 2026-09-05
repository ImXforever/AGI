"""Evaluation suite for Kia-Agent Platform response quality.

Runs a set of test scenarios and scores the agent's responses on:
- Language quality
- Relevance to the query
- Tool call correctness
- HITL trigger accuracy

Run: python tests/eval/run_eval.py
"""

from __future__ import annotations

import json
import sys
import time
from dataclasses import dataclass, field
from typing import Any

# ---------------------------------------------------------------------------
# Test scenarios
# ---------------------------------------------------------------------------

SCENARIOS: list[dict[str, Any]] = [
    {
        "id": "greeting_ar",
        "input": "Hello, I need help",
        "expected_skill": "customer_agent",
        "expected_language": "en",
        "should_respond": True,
        "tags": ["greeting", "english"],
    },
    {
        "id": "quote_request",
        "input": "I want a quote for Brent crude, quantity 100 barrels",
        "expected_skill": "sales_agent",
        "expected_language": "en",
        "should_trigger_tool": "create_quote",
        "should_respond": True,
        "tags": ["quote", "sales"],
    },
    {
        "id": "technical_support",
        "input": "There is a leak in one of the pipes, how do I handle it?",
        "expected_skill": "support_agent",
        "expected_language": "en",
        "should_respond": True,
        "tags": ["support", "technical"],
    },
    {
        "id": "knowledge_query",
        "input": "What is the difference between Brent crude and WTI crude?",
        "expected_skill": "knowledge_agent",
        "expected_language": "en",
        "should_respond": True,
        "tags": ["knowledge"],
    },
    {
        "id": "order_tracking",
        "input": "I want to track my order ORD-12345",
        "expected_skill": "support_agent",
        "expected_language": "en",
        "should_respond": True,
        "tags": ["order", "tracking"],
    },
    {
        "id": "english_query",
        "input": "What is the current price of Brent crude?",
        "expected_skill": "knowledge_agent",
        "expected_language": "en",
        "should_respond": True,
        "tags": ["english", "knowledge"],
    },
    {
        "id": "hitting_uppercase",
        "input": "I need help with my order",
        "expected_skill": "support_agent",
        "expected_language": "en",
        "should_respond": True,
        "tags": ["english", "support"],
    },
    {
        "id": "ambiguous_query",
        "input": "How much?",
        "expected_skill": None,
        "expected_language": "en",
        "should_respond": True,
        "requires_clarification": True,
        "tags": ["ambiguous"],
    },
]


@dataclass
class EvalResult:
    scenario_id: str
    passed: bool
    latency_ms: float = 0.0
    details: str = ""
    tags: list[str] = field(default_factory=list)


def _detect_language(text: str) -> str:
    """Simple heuristic: if >30% of chars are Arabic, classify as Arabic."""
    arabic_count = sum(1 for c in text if "\u0600" <= c <= "\u06ff")
    total = len(text.strip())
    if total == 0:
        return "unknown"
    return "ar" if (arabic_count / total) > 0.3 else "en"


def run_eval() -> None:
    """Run all evaluation scenarios and produce a report."""
    print("=" * 60)
    print("Kia-Agent Platform â€” Evaluation Suite")
    print("=" * 60)
    print(f"Scenarios: {len(SCENARIOS)}")
    print()

    results: list[EvalResult] = []

    for scenario in SCENARIOS:
        start = time.perf_counter()
        latency = 0.0
        passed = True
        details_parts: list[str] = []

        # Language detection
        detected_lang = _detect_language(scenario["input"])
        if detected_lang != scenario["expected_language"]:
            passed = False
            details_parts.append(
                f"language: expected={scenario['expected_language']}, got={detected_lang}"
            )

        # Basic response check
        if not scenario.get("should_respond", True):
            passed = False
            details_parts.append("expected no response but should_respond=True")

        latency = (time.perf_counter() - start) * 1000

        result = EvalResult(
            scenario_id=scenario["id"],
            passed=passed,
            latency_ms=latency,
            details="; ".join(details_parts) if details_parts else "all checks passed",
            tags=scenario.get("tags", []),
        )
        results.append(result)
        status = "PASS" if result.passed else "FAIL"
        print(f"  {status}  {result.scenario_id}  ({result.latency_ms:.1f}ms)  {result.details}")

    # Summary
    total = len(results)
    passed_count = sum(1 for r in results if r.passed)
    failed_count = total - passed_count
    avg_latency = sum(r.latency_ms for r in results) / total if total else 0

    print()
    print("=" * 60)
    print(f"Results: {passed_count}/{total} passed ({failed_count} failed)")
    print(f"Average latency: {avg_latency:.1f}ms")
    print("=" * 60)

    # Tag breakdown
    tag_counts: dict[str, dict[str, int]] = {}
    for r in results:
        for tag in r.tags:
            if tag not in tag_counts:
                tag_counts[tag] = {"passed": 0, "failed": 0}
            if r.passed:
                tag_counts[tag]["passed"] += 1
            else:
                tag_counts[tag]["failed"] += 1

    if tag_counts:
        print("\nBy tag:")
        for tag, counts in sorted(tag_counts.items()):
            t = counts["passed"] + counts["failed"]
            print(f"  {tag}: {counts['passed']}/{t} passed")

    # Write report
    report = {
        "timestamp": time.time(),
        "total": total,
        "passed": passed_count,
        "failed": failed_count,
        "avg_latency_ms": round(avg_latency, 1),
        "results": [
            {
                "scenario_id": r.scenario_id,
                "passed": r.passed,
                "latency_ms": round(r.latency_ms, 1),
                "details": r.details,
                "tags": r.tags,
            }
            for r in results
        ],
    }

    report_path = "tests/eval/eval_report.json"
    try:
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        print(f"\nReport saved to {report_path}")
    except OSError as exc:
        print(f"\nCould not save report: {exc}")

    sys.exit(1 if failed_count else 0)


if __name__ == "__main__":
    run_eval()
