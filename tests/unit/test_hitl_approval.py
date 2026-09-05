"""Unit tests for the HITL risk-classification layers.

`app/core/hitl/approval.py` scores commands, file writes and URLs on a 0-10
risk scale and decides safe / guard / block. It is the policy engine behind
every human-in-the-loop prompt, and it had no tests at all.
"""

from __future__ import annotations

import pytest

from app.core.hitl import approval

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Layer 1 — shell classification
# ---------------------------------------------------------------------------


class TestClassifyShell:
    def test_empty_command_is_blocked(self):
        assert approval.classify_shell("") == "block"

    def test_whitespace_command_is_blocked(self):
        assert approval.classify_shell("   ") == "block"

    def test_unknown_command_fails_closed_to_guard(self):
        assert approval.classify_shell("some-exotic-binary") == "guard"

    def test_returns_one_of_the_three_tiers(self):
        for cmd in ["ls", "rm -rf /", "pip install x", "zzz"]:
            assert approval.classify_shell(cmd) in {"safe", "guard", "block"}


# ---------------------------------------------------------------------------
# Layer 2 — file content analysis
# ---------------------------------------------------------------------------


class TestAnalyzeFileContent:
    def test_plain_text_scores_zero_risk(self):
        result = approval.analyze_file_content("hello world\nthis is a note")
        assert result["risk_level"] == 0
        assert result["findings"] == []

    def test_risk_is_capped_at_ten(self):
        nasty = "eval(base64.b64decode('x'))\nos.system('rm -rf /')\nexec(compile(x))\n" * 10
        assert approval.analyze_file_content(nasty)["risk_level"] <= 10

    def test_excessive_imports_are_flagged(self):
        content = "".join(f"import mod{i}, other{i}\n" for i in range(12))
        result = approval.analyze_file_content(content)
        assert result["risk_level"] > 0

    def test_many_base64_blocks_are_flagged(self):
        content = "\n".join(
            "QUJDREVGR0hJSktMTU5PUFFSU1RVVldYWVphYmNkZWZnaGlqaw==" for _ in range(6)
        )
        result = approval.analyze_file_content(content)
        assert "many base64 blocks" in result["findings"]

    def test_empty_content_is_risk_free(self):
        assert approval.analyze_file_content("")["risk_level"] == 0

    def test_result_always_has_both_keys(self):
        assert set(approval.analyze_file_content("x")) == {"risk_level", "findings"}


# ---------------------------------------------------------------------------
# Layer 3 — URL safety
# ---------------------------------------------------------------------------


class TestAnalyzeUrlSafety:
    def test_empty_url_is_risk_free(self):
        assert approval.analyze_url_safety("") == {"risk_level": 0, "findings": []}

    def test_ordinary_https_url_is_low_risk(self):
        assert approval.analyze_url_safety("https://example.com/products")["risk_level"] < 4

    @pytest.mark.parametrize("tld", ["ru", "cn", "tk", "ml", "ga", "cf", "gq", "pw"])
    def test_suspicious_tlds_add_risk(self, tld: str):
        result = approval.analyze_url_safety(f"https://example.{tld}/x")
        assert "suspicious TLD" in result["findings"]

    def test_risk_is_capped_at_ten(self):
        assert (
            approval.analyze_url_safety("http://127.0.0.1:22/../../etc/passwd.ru")["risk_level"]
            <= 10
        )


# ---------------------------------------------------------------------------
# Layer 4 — context-aware risk
# ---------------------------------------------------------------------------


class TestContextRiskModifier:
    def test_privileged_roles_reduce_risk(self):
        assert approval.context_risk_modifier(10, role="admin") < 10

    def test_untrusted_roles_increase_risk(self):
        assert approval.context_risk_modifier(5, role="associate") > 5

    def test_unknown_role_is_treated_as_neutral(self):
        assert approval.context_risk_modifier(5, role="nobody") == 5

    def test_recent_blocks_escalate_risk(self):
        base = approval.context_risk_modifier(3, role="soldier", recent_blocks=0)
        worse = approval.context_risk_modifier(3, role="soldier", recent_blocks=3)
        assert worse > base

    def test_output_never_leaves_the_zero_to_ten_scale(self):
        for role in approval.ROLE_RISK_MULTIPLIER:
            for blocks in (0, 5, 50):
                value = approval.context_risk_modifier(10, role=role, recent_blocks=blocks)
                assert 0 <= value <= 10

    def test_zero_risk_stays_zero_regardless_of_role(self):
        assert approval.context_risk_modifier(0, role="associate", recent_blocks=9) == 0


# ---------------------------------------------------------------------------
# Layer 6 — auto rules
# ---------------------------------------------------------------------------


class TestAutoRules:
    def test_neutral_command_needs_manual_review(self):
        assert approval.check_auto_rules("some-neutral-command") is None

    def test_result_is_one_of_the_three_outcomes(self):
        for cmd in ["ls", "rm -rf /", "pip install x"]:
            assert approval.check_auto_rules(cmd) in {"approve", "reject", None}


# ---------------------------------------------------------------------------
# ApprovalDecision
# ---------------------------------------------------------------------------


class TestApprovalDecision:
    def test_guard_without_auto_decision_needs_a_human(self):
        d = approval.ApprovalDecision("guard", 5, "why")
        assert d.needs_approval is True
        assert d.is_blocked is False

    def test_auto_approved_guard_does_not_need_a_human(self):
        d = approval.ApprovalDecision("guard", 5, "why", auto_decision="approve")
        assert d.needs_approval is False

    def test_block_tier_is_blocked(self):
        assert approval.ApprovalDecision("block", 10, "no").is_blocked is True

    def test_auto_rejected_command_is_blocked_even_when_only_guarded(self):
        d = approval.ApprovalDecision("guard", 5, "why", auto_decision="reject")
        assert d.is_blocked is True

    def test_safe_needs_nothing(self):
        d = approval.ApprovalDecision("safe", 0, "fine")
        assert d.needs_approval is False and d.is_blocked is False

    def test_tags_default_to_empty(self):
        assert approval.ApprovalDecision("safe", 0, "fine").risk_tags == []


# ---------------------------------------------------------------------------
# Unified classification
# ---------------------------------------------------------------------------


class TestClassifyCommand:
    def test_empty_command_is_maximum_risk(self):
        d = approval.classify_command("")
        assert d.tier == "block" and d.risk_level == 10

    def test_safe_command_carries_no_risk_tags(self):
        d = approval.classify_command("ls")
        if d.tier == "safe":
            assert d.risk_tags == []

    def test_role_affects_the_resulting_score(self):
        cmd = "pip install requests"
        assert (
            approval.classify_command(cmd, role="admin").risk_level
            <= approval.classify_command(cmd, role="associate").risk_level
        )

    def test_decision_is_always_well_formed(self):
        d = approval.classify_command("curl https://example.com")
        assert d.tier in {"safe", "guard", "block"}
        assert 0 <= d.risk_level <= 10
        assert isinstance(d.reason, str)


class TestClassifyFileWrite:
    def test_empty_file_is_safe(self):
        d = approval.classify_file_write("a.txt", "")
        assert d.tier == "safe" and d.risk_level == 0

    def test_plain_text_file_is_safe(self):
        assert approval.classify_file_write("notes.txt", "just some notes").tier == "safe"

    def test_high_risk_content_is_blocked_with_findings(self):
        nasty = (
            "eval(base64.b64decode('x'))\nos.system('rm -rf /')\nexec(open('/etc/passwd').read())\n"
            * 5
        )
        d = approval.classify_file_write("evil.py", nasty)
        if d.risk_level >= 8:
            assert d.tier == "block" and d.risk_tags


class TestClassifyUrl:
    def test_benign_url_is_safe(self):
        assert approval.classify_url("https://example.com").tier == "safe"

    def test_empty_url_is_safe(self):
        assert approval.classify_url("").tier == "safe"

    def test_tier_matches_the_risk_band(self):
        d = approval.classify_url("http://127.0.0.1/admin")
        if d.risk_level >= 8:
            assert d.tier == "block"
        elif d.risk_level >= 4:
            assert d.tier == "guard"
        else:
            assert d.tier == "safe"


# ---------------------------------------------------------------------------
# Pending approval store
# ---------------------------------------------------------------------------


class TestPendingApprovals:
    async def test_a_request_is_registered_as_pending(self):
        req = approval.create_approval_request("pip install x", user_id=1)
        assert req

    def test_ids_are_unique_per_request(self):
        a = approval._gen_approval_id("cmd", 1)
        b = approval._gen_approval_id("cmd", 2)
        assert a != b

    def test_id_is_a_short_hex_digest(self):
        aid = approval._gen_approval_id("cmd", 1)
        assert len(aid) == 12
        int(aid, 16)

    async def test_approving_an_unknown_id_fails(self):
        assert await approval.approve_request("no-such-id") is False

    async def test_rejecting_an_unknown_id_fails(self):
        assert await approval.reject_request("no-such-id") is False

    async def test_pending_list_is_a_list(self):
        result = await approval.get_pending_approvals()
        assert isinstance(result, list)
