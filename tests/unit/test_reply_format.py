"""Markdown → channel-safe text (no stars, hashes, tables or fences reach the customer)."""

from __future__ import annotations

from app.core import postprocess
from app.core.reply_format import looks_like_markdown, markdown_to_telegram_html, strip_markdown


class _Domain:
    numeral_style = "western"


class _Cfg:
    domain = _Domain()


class TestMarkdownToTelegramHtml:
    def test_bold_and_headings_become_b_tags(self):
        out = markdown_to_telegram_html("## Title\n\nSome **bold** text")
        assert "**" not in out
        assert "##" not in out
        assert "<b>Title</b>" in out
        assert "<b>bold</b>" in out

    def test_bullets_and_rules(self):
        out = markdown_to_telegram_html("- one\n* two\n---\n1. three")
        assert "• one" in out
        assert "• two" in out
        assert "---" not in out
        assert "1. three" in out

    def test_tables_and_fences_are_flattened(self):
        src = '| a | b |\n|---|---|\n| 1 | 2 |\n\n```json\n{"x": 1}\n```'
        out = markdown_to_telegram_html(src)
        assert "|" not in out
        assert "```" not in out
        assert "1 · 2" in out

    def test_html_is_escaped_and_math_is_preserved(self):
        out = markdown_to_telegram_html("5 * 3 < 20 & a_b_c")
        assert "5 * 3" in out
        assert "&lt;" in out
        assert "&amp;" in out
        assert "a_b_c" in out

    def test_persian_untouched(self):
        text = "سلام! چطور می‌توانم کمک کنم؟"
        assert markdown_to_telegram_html(text) == text

    def test_links_keep_text_and_url(self):
        out = markdown_to_telegram_html("see [docs](https://example.com)")
        assert "docs" in out
        assert "https://example.com" in out
        assert "[" not in out

    def test_strip_markdown_is_plain(self):
        out = strip_markdown("**Hi** there\n- one")
        assert "<b>" not in out
        assert "**" not in out
        assert "Hi there" in out
        assert "• one" in out

    def test_looks_like_markdown(self):
        assert looks_like_markdown("**x**")
        assert looks_like_markdown("## head")
        assert not looks_like_markdown("plain sentence.")


class TestPostprocessIntegration:
    def test_run_reports_markdown_fix(self):
        report = postprocess.run("**Bold** intro\n\n- a\n- b", config=_Cfg())
        assert "markdown_to_html" in report.fixes_applied
        assert "**" not in report.text
        assert "<b>Bold</b>" in report.text
        assert "• a" in report.text

    def test_run_keeps_plain_text_unchanged(self):
        report = postprocess.run("Hello, how can I help?", config=_Cfg())
        assert report.text == "Hello, how can I help?"
        assert "markdown_to_html" not in report.fixes_applied
