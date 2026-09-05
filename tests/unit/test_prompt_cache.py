"""Unit tests for the prompt cache / context budget manager.

The cache exists to keep the message prefix byte-stable across calls so the
provider can reuse its cached prefix computation. If `build()` produces a
different prefix each turn the saving silently disappears, so the stability
property is asserted directly.
"""

from __future__ import annotations

import pytest

from app.core import prompt_cache as pc

pytestmark = pytest.mark.unit

SYSTEM = "You are a helpful petroleum assistant."


@pytest.fixture
def cache() -> pc.PromptCache:
    return pc.PromptCache()


def turns(n: int, size: int = 20) -> list[dict[str, str]]:
    return [
        {"role": "user" if i % 2 == 0 else "assistant", "content": f"m{i} " + "x" * size}
        for i in range(n)
    ]


# ---------------------------------------------------------------------------
# build()
# ---------------------------------------------------------------------------


class TestBuild:
    def test_system_prompt_comes_first(self, cache: pc.PromptCache):
        msgs = cache.build(SYSTEM, [], "hello")
        assert msgs[0] == {"role": "system", "content": SYSTEM}

    def test_the_user_message_comes_last(self, cache: pc.PromptCache):
        msgs = cache.build(SYSTEM, [], "hello")
        assert msgs[-1] == {"role": "user", "content": "hello"}

    def test_an_empty_history_yields_just_system_and_user(self, cache: pc.PromptCache):
        assert len(cache.build(SYSTEM, [], "hello")) == 2

    def test_short_history_is_passed_through_verbatim(self, cache: pc.PromptCache):
        history = turns(4)
        msgs = cache.build(SYSTEM, history, "hello")
        assert msgs[1:-1] == history

    def test_long_history_is_compressed(self, cache: pc.PromptCache):
        msgs = cache.build(SYSTEM, turns(pc.COMPRESS_THRESHOLD + 6), "hello")
        assert len(msgs) < pc.COMPRESS_THRESHOLD + 8

    def test_the_most_recent_turns_survive_compression(self, cache: pc.PromptCache):
        history = turns(pc.COMPRESS_THRESHOLD + 6)
        msgs = cache.build(SYSTEM, history, "hello")
        assert history[-1] in msgs

    def test_a_summary_message_is_inserted(self, cache: pc.PromptCache):
        msgs = cache.build(SYSTEM, turns(pc.COMPRESS_THRESHOLD + 6), "hello")
        assert any("خلاصه" in m["content"] for m in msgs[1:2])

    def test_a_custom_compressor_is_used(self, cache: pc.PromptCache):
        msgs = cache.build(
            SYSTEM,
            turns(pc.COMPRESS_THRESHOLD + 6),
            "hello",
            compress_callback=lambda old: "CUSTOM SUMMARY",
        )
        assert any("CUSTOM SUMMARY" in m["content"] for m in msgs)

    def test_the_context_budget_is_enforced(self, cache: pc.PromptCache):
        msgs = cache.build(SYSTEM, turns(40, size=800), "hello")
        assert sum(len(m["content"]) for m in msgs) <= pc.MAX_CONTEXT_CHARS + 500

    def test_an_oversized_system_prompt_leaves_only_system_and_user(self, cache: pc.PromptCache):
        msgs = cache.build("S" * (pc.MAX_CONTEXT_CHARS + 100), turns(10), "hello")
        assert len(msgs) == 2

    def test_every_message_keeps_role_and_content(self, cache: pc.PromptCache):
        for m in cache.build(SYSTEM, turns(20), "hello"):
            assert "role" in m and "content" in m


# ---------------------------------------------------------------------------
# Prefix stability & tracking
# ---------------------------------------------------------------------------


class TestTracking:
    def test_a_fresh_cache_has_no_activity(self, cache: pc.PromptCache):
        stats = cache.stats()
        assert stats["hits"] == 0 and stats["misses"] == 0
        assert stats["hit_rate"] == "0.0%"

    def test_the_first_call_is_always_a_miss(self, cache: pc.PromptCache):
        cache.track(cache.build(SYSTEM, [], "one"))
        assert cache.stats()["misses"] == 1

    def test_an_unchanged_prefix_registers_a_hit(self, cache: pc.PromptCache):
        """Same system prompt and history, new user turn -> prefix is reusable."""
        history = turns(2)
        cache.track(cache.build(SYSTEM, history, "first"))
        cache.track(cache.build(SYSTEM, history, "second"))
        assert cache.stats()["hits"] == 1

    def test_a_changed_system_prompt_breaks_the_cache(self, cache: pc.PromptCache):
        cache.track(cache.build(SYSTEM, [], "q"))
        cache.track(cache.build("A different system prompt", [], "q"))
        assert cache.stats()["hits"] == 0

    def test_hits_accumulate_estimated_savings(self, cache: pc.PromptCache):
        history = turns(2)
        cache.track(cache.build(SYSTEM, history, "a"))
        cache.track(cache.build(SYSTEM, history, "b"))
        assert cache.stats()["est_tokens_saved"] > 0

    def test_a_single_message_is_not_tracked(self, cache: pc.PromptCache):
        cache.track([{"role": "user", "content": "x"}])
        assert cache.stats()["total"] == 0

    def test_an_empty_list_is_not_tracked(self, cache: pc.PromptCache):
        cache.track([])
        assert cache.stats()["total"] == 0

    def test_the_hit_rate_is_reported_as_a_percentage(self, cache: pc.PromptCache):
        history = turns(2)
        cache.track(cache.build(SYSTEM, history, "a"))
        cache.track(cache.build(SYSTEM, history, "b"))
        assert cache.stats()["hit_rate"] == "50.0%"

    def test_reset_clears_all_counters(self, cache: pc.PromptCache):
        cache.track(cache.build(SYSTEM, [], "a"))
        cache.reset()
        assert cache.stats()["total"] == 0
        assert cache.stats()["est_tokens_saved"] == 0


class TestCompaction:
    def test_compaction_renders_both_roles(self, cache: pc.PromptCache):
        out = cache._compact(
            [{"role": "user", "content": "q"}, {"role": "assistant", "content": "a"}]
        )
        assert "q" in out and "a" in out

    def test_unknown_roles_are_dropped(self, cache: pc.PromptCache):
        assert cache._compact([{"role": "tool", "content": "internal"}]) == ""

    def test_empty_turns_compact_to_nothing(self, cache: pc.PromptCache):
        assert cache._compact([]) == ""

    def test_a_long_summary_is_truncated(self, cache: pc.PromptCache):
        long_turns = [{"role": "user", "content": "x" * 200} for _ in range(50)]
        assert len(cache._compact(long_turns)) <= pc.MAX_SUMMARY_CHARS


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------


class TestModuleHelpers:
    def test_the_shared_cache_is_a_singleton(self):
        assert pc.get_prompt_cache() is pc.get_prompt_cache()

    def test_resetting_returns_the_cleared_singleton(self):
        pc.get_prompt_cache().track(
            [{"role": "system", "content": "s"}, {"role": "user", "content": "u"}]
        )
        assert pc.reset_prompt_cache().stats()["total"] == 0

    def test_the_system_prompt_gets_a_cache_marker(self):
        marked = pc.add_anthropic_cache_markers([{"role": "system", "content": "s"}])
        assert marked[0]["cache_control"] == {"type": "ephemeral"}

    def test_ordinary_user_turns_are_not_marked(self):
        marked = pc.add_anthropic_cache_markers(
            [{"role": "system", "content": "s"}, {"role": "user", "content": "u"}]
        )
        assert "cache_control" not in marked[1]

    def test_the_summary_block_is_also_marked(self):
        marked = pc.add_anthropic_cache_markers(
            [
                {"role": "system", "content": "s"},
                {"role": "system", "content": "[خلاصه] previous turns"},
            ]
        )
        assert "cache_control" in marked[1]

    def test_marking_does_not_mutate_the_input(self):
        original = [{"role": "system", "content": "s"}]
        pc.add_anthropic_cache_markers(original)
        assert original == [{"role": "system", "content": "s"}]

    def test_no_hits_means_no_savings(self):
        assert pc.estimate_savings({"hits": 0, "est_tokens_saved": 0})["estimated_savings_usd"] == 0

    def test_savings_are_positive_when_there_are_hits(self):
        result = pc.estimate_savings({"hits": 10, "est_tokens_saved": 5000})
        assert result["estimated_savings_usd"] > 0
        assert result["cache_hits"] == 10
