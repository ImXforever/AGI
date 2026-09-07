"""Unit tests for the skills manager.

Skills are markdown files with YAML-ish frontmatter that get injected into the
model prompt, and they can be written and deleted through the admin surface.
That combination — user-supplied names turned into filesystem paths — makes the
`_safe()` name validator a path-traversal boundary, so it is tested hard here.

The tests point SKILL_DIR at a tmp_path so nothing touches the real data dir.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from app.core import skills_manager as sm

pytestmark = pytest.mark.unit


@pytest.fixture(autouse=True)
def skill_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    d = tmp_path / "skills"
    d.mkdir()
    monkeypatch.setattr(sm, "SKILL_DIR", str(d))
    return d


def write_skill(skill_dir: Path, name: str, frontmatter: str, body: str = "Body text.") -> Path:
    d = skill_dir / name
    d.mkdir(parents=True, exist_ok=True)
    path = d / "SKILL.md"
    path.write_text(f"---\n{frontmatter}\n---\n{body}\n", encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# Name validation — a security boundary
# ---------------------------------------------------------------------------


class TestSafeName:
    @pytest.mark.parametrize("name", ["quoting", "lead_scoring", "a-b", "ab", "x" * 32])
    def test_valid_names_are_accepted(self, name: str):
        assert sm._safe(name) == name

    def test_names_are_lowercased_and_spaces_become_underscores(self):
        assert sm._safe("Lead Scoring") == "lead_scoring"

    def test_surrounding_whitespace_is_trimmed(self):
        assert sm._safe("  quoting  ") == "quoting"

    def test_arabic_and_persian_names_are_allowed(self):
        assert sm._safe("تسعير") == "تسعير"

    @pytest.mark.parametrize(
        "attack",
        [
            "../../etc/passwd",
            "..",
            "a/b",
            "a\\b",
            "skill;rm -rf /",
            "sk ill!",
            "$(whoami)",
            "a\x00b",
        ],
    )
    def test_path_traversal_and_injection_attempts_are_refused(self, attack: str):
        assert sm._safe(attack) is None

    @pytest.mark.parametrize("name", ["", "   ", "a", "x" * 33])
    def test_out_of_range_names_are_refused(self, name: str):
        assert sm._safe(name) is None

    def test_none_is_tolerated(self):
        assert sm._safe(None) is None  # type: ignore[arg-type]


class TestSkillFileResolution:
    def test_directory_style_skill_is_found(self, skill_dir: Path):
        write_skill(skill_dir, "quoting", "description: q")
        assert sm._skill_file("quoting").endswith(os.path.join("quoting", "SKILL.md"))

    def test_flat_markdown_skill_is_found(self, skill_dir: Path):
        (skill_dir / "flat.md").write_text("---\ndescription: f\n---\nbody", encoding="utf-8")
        assert sm._skill_file("flat").endswith("flat.md")

    def test_missing_skill_resolves_to_none(self):
        assert sm._skill_file("nonexistent") is None

    def test_an_invalid_name_never_resolves_to_a_path(self):
        assert sm._skill_file("../../etc/passwd") is None


# ---------------------------------------------------------------------------
# Frontmatter parsing
# ---------------------------------------------------------------------------


class TestFrontmatter:
    def test_text_without_frontmatter_is_all_body(self):
        fm, body = sm.parse_frontmatter("just a body")
        assert fm == {} and body == "just a body"

    def test_empty_input(self):
        assert sm.parse_frontmatter("") == ({}, "")

    def test_scalars_are_parsed_and_body_separated(self):
        fm, body = sm.parse_frontmatter(
            "---\nname: quoting\ndescription: Make quotes\n---\nBody here"
        )
        assert fm["name"] == "quoting"
        assert fm["description"] == "Make quotes"
        assert body.strip() == "Body here"

    def test_quotes_are_stripped(self):
        fm, _ = sm.parse_frontmatter('---\ndescription: "quoted value"\n---\n')
        assert fm["description"] == "quoted value"

    def test_single_quotes_are_stripped(self):
        fm, _ = sm.parse_frontmatter("---\ndescription: 'quoted'\n---\n")
        assert fm["description"] == "quoted"

    def test_inline_lists_are_parsed(self):
        fm, _ = sm.parse_frontmatter('---\ntags: [sales, "pricing"]\n---\n')
        assert fm["tags"] == ["sales", "pricing"]

    def test_dash_lists_are_parsed(self):
        fm, _ = sm.parse_frontmatter("---\ntags:\n  - sales\n  - pricing\n---\n")
        assert fm["tags"] == ["sales", "pricing"]

    def test_comments_are_ignored(self):
        fm, _ = sm.parse_frontmatter("---\n# a comment\ndescription: d\n---\n")
        assert fm == {"description": "d"}

    def test_keys_are_lowercased(self):
        fm, _ = sm.parse_frontmatter("---\nDescription: d\n---\n")
        assert "description" in fm

    def test_unterminated_frontmatter_is_treated_as_body(self):
        fm, body = sm.parse_frontmatter("---\ndescription: d\nno closing fence")
        assert fm == {}
        assert "description" in body


class TestUnquoteAndList:
    def test_unquote_leaves_bare_values_alone(self):
        assert sm._unquote("bare") == "bare"

    def test_unquote_requires_matching_delimiters(self):
        assert sm._unquote("\"mismatched'") == "\"mismatched'"

    def test_parse_list_on_a_non_list_yields_empty(self):
        assert sm._parse_list("not a list") == []

    def test_parse_list_ignores_empty_entries(self):
        assert sm._parse_list("[a, , b]") == ["a", "b"]


# ---------------------------------------------------------------------------
# Relevance scoring
# ---------------------------------------------------------------------------


class TestMatchScore:
    def test_empty_query_scores_zero(self):
        assert sm._match_score("", "quoting", "make quotes", []) == 0

    def test_short_tokens_are_ignored(self):
        assert sm._match_score("a an", "quoting", "desc", []) == 0

    def test_a_name_hit_scores(self):
        assert sm._match_score("quoting please", "quoting", "", []) > 0

    def test_a_description_hit_scores(self):
        assert sm._match_score("pricing", "x", "handles pricing", []) > 0

    def test_a_tag_hit_scores(self):
        assert sm._match_score("pricing", "x", "", ["pricing"]) > 0

    def test_more_hits_score_higher(self):
        one = sm._match_score("pricing", "x", "pricing", [])
        two = sm._match_score("pricing quotes", "x", "pricing quotes", [])
        assert two > one

    def test_matching_is_case_insensitive(self):
        assert sm._match_score("PRICING", "x", "pricing", []) > 0


# ---------------------------------------------------------------------------
# Scanning & CRUD
# ---------------------------------------------------------------------------


class TestScan:
    def test_a_missing_directory_scans_empty(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
        monkeypatch.setattr(sm, "SKILL_DIR", str(tmp_path / "nope"))
        assert sm._scan_sync() == []

    def test_an_empty_directory_scans_empty(self):
        assert sm._scan_sync() == []

    def test_both_layouts_are_discovered(self, skill_dir: Path):
        write_skill(skill_dir, "dir_skill", "description: d")
        (skill_dir / "flat.md").write_text("---\ndescription: f\n---\nbody", encoding="utf-8")
        assert {row[0] for row in sm._scan_sync()} == {"dir_skill", "flat"}

    def test_non_markdown_files_are_ignored(self, skill_dir: Path):
        (skill_dir / "readme.txt").write_text("nope", encoding="utf-8")
        assert sm._scan_sync() == []

    def test_the_frontmatter_name_overrides_the_filename(self, skill_dir: Path):
        write_skill(skill_dir, "folder", "name: real_name\ndescription: d")
        assert sm._scan_sync()[0][0] == "real_name"


class TestCrud:
    VALID = "---\ndescription: A valid skill\n---\nDo the thing."

    async def test_write_then_read_round_trip(self):
        ok, err = await sm.skill_write("quoting", self.VALID)
        assert ok is True and err == ""
        assert "Do the thing." in await sm.skill_read("quoting")

    async def test_write_refuses_an_invalid_name(self):
        ok, err = await sm.skill_write("../escape", self.VALID)
        assert ok is False and err

    async def test_write_requires_a_description(self):
        ok, err = await sm.skill_write("quoting", "---\nname: x\n---\nbody")
        assert ok is False and "description" in err

    async def test_oversized_content_is_truncated_not_rejected(self):
        big = self.VALID + "\n" + ("x" * (sm.MAX_BODY_CHARS * 2))
        assert (await sm.skill_write("bigskill", big))[0] is True
        assert len(await sm.skill_read("bigskill")) <= 4000

    async def test_reading_a_missing_skill_yields_none(self):
        assert await sm.skill_read("nope") is None

    async def test_delete_removes_the_skill(self):
        await sm.skill_write("temp", self.VALID)
        assert await sm.skill_delete("temp") is True
        assert await sm.skill_read("temp") is None

    async def test_deleting_a_missing_skill_reports_false(self):
        assert await sm.skill_delete("nope") is False

    async def test_deleting_an_invalid_name_reports_false(self):
        assert await sm.skill_delete("../../etc") is False

    async def test_toggle_requires_an_existing_skill(self):
        assert await sm.skill_toggle("nope", True) is False

    async def test_toggle_succeeds_for_an_existing_skill(self):
        await sm.skill_write("quoting", self.VALID)
        assert await sm.skill_toggle("quoting", False) is True

    async def test_legacy_add_and_del_shims(self):
        assert await sm.skill_add("legacy", self.VALID) is True
        assert await sm.skill_del("legacy") is True


# ---------------------------------------------------------------------------
# Prompt injection budget
# ---------------------------------------------------------------------------


class TestBuildSkillsPrompt:
    async def test_no_skills_produces_no_prompt(self):
        assert await sm.build_skills_prompt("anything") == ""

    async def test_the_index_lists_every_enabled_skill(self, skill_dir: Path):
        write_skill(skill_dir, "quoting", "description: Make quotes")
        write_skill(skill_dir, "support", "description: Fix problems")
        prompt = await sm.build_skills_prompt("")
        assert "quoting" in prompt and "support" in prompt

    async def test_the_character_budget_is_respected(self, skill_dir: Path):
        for i in range(10):
            write_skill(skill_dir, f"skill_{i}", f"description: Skill {i}", "body " * 500)
        prompt = await sm.build_skills_prompt("skill", max_chars=1200)
        assert len(prompt) <= 1200

    async def test_a_relevant_skill_body_is_injected(self, skill_dir: Path):
        write_skill(
            skill_dir,
            "quoting",
            "description: pricing quotes\ntags: [pricing]",
            "Detailed quoting instructions. " * 20,
        )
        prompt = await sm.build_skills_prompt("pricing")
        assert "Detailed quoting instructions." in prompt

    async def test_at_most_two_bodies_are_injected(self, skill_dir: Path):
        for i in range(5):
            write_skill(
                skill_dir,
                f"pricing_{i}",
                f"description: pricing skill {i}\ntags: [pricing]",
                f"Body number {i}. " * 30,
            )
        prompt = await sm.build_skills_prompt("pricing", max_chars=100_000)
        assert sum(1 for i in range(5) if f"#### 🧩 pricing_{i}" in prompt) <= 2

    async def test_an_irrelevant_query_injects_no_bodies(self, skill_dir: Path):
        write_skill(skill_dir, "quoting", "description: pricing", "Long body. " * 40)
        prompt = await sm.build_skills_prompt("completely unrelated zzz")
        assert "####" not in prompt
