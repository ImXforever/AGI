"""Turn model Markdown into clean chat text.

Chat models love Markdown (``**bold**``, ``## headings``, ``---`` rules, fenced
code, tables). Telegram, WhatsApp and e-mail do not render it, so customers saw
raw stars and hashes in every reply. This module converts that syntax into what
messengers actually understand:

* ``markdown_to_telegram_html`` — Telegram HTML (``<b>`` for bold/headings,
  ``•`` bullets, everything else escaped). WhatsApp and e-mail adapters already
  translate Telegram HTML into their own plain formats.
* ``strip_markdown`` — pure plain text (no tags at all).

Both are deterministic, never raise, and leave prose untouched.
"""

from __future__ import annotations

import html
import re

_B_OPEN = "\x01"
_B_CLOSE = "\x02"

_FENCE_RE = re.compile(r"^\s*(```+|~~~+)[^\n]*$")
_HR_RE = re.compile(r"^\s*([-*_])(?:\s*\1){2,}\s*$")
_HEADING_RE = re.compile(r"^\s{0,3}#{1,6}\s+(.*?)\s*#*\s*$")
_BULLET_RE = re.compile(r"^(\s*)[-*+•◦▪]\s+(.*)$")
_NUMBERED_RE = re.compile(r"^(\s*)(\d{1,3})[.)]\s+(.*)$")
_QUOTE_RE = re.compile(r"^\s*>\s?(.*)$")
_TABLE_SEP_RE = re.compile(r"^\s*\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)*\|?\s*$")
_TABLE_ROW_RE = re.compile(r"^\s*\|(.*)\|\s*$")

_IMG_RE = re.compile(r"!\[([^\]]*)\]\([^)]*\)")
_LINK_RE = re.compile(r"\[([^\]]+)\]\(\s*<?([^)\s>]+)>?(?:\s+\"[^\"]*\")?\s*\)")
_CODE_RE = re.compile(r"`{1,2}([^`\n]+?)`{1,2}")
_BOLD_RE = re.compile(r"\*\*(?!\s)(.+?)(?<!\s)\*\*|__(?!\s)(.+?)(?<!\s)__")
_ITALIC_STAR_RE = re.compile(r"(?<![\w*])\*(?!\s)([^*\n]+?)(?<!\s)\*(?![\w*])")
_ITALIC_UNDER_RE = re.compile(r"(?<![\w_])_(?!\s)([^_\n]+?)(?<!\s)_(?![\w_])")
_STRIKE_RE = re.compile(r"~~(?!\s)(.+?)(?<!\s)~~")
_ESCAPED_RE = re.compile(r"\\([\\`*_{}\[\]()#+\-.!>|~])")
_LEFTOVER_MARKS_RE = re.compile(r"(\*\*+|__+|~~+)")

_HTML_TAG_RE = re.compile(
    r"</?(b|strong|i|em|u|ins|s|strike|del|code|pre|br|span|tg-spoiler|blockquote|a)\b[^>]*>",
    re.IGNORECASE,
)
_A_TAG_RE = re.compile(
    r"<a\s+[^>]*href=[\"']([^\"']+)[\"'][^>]*>(.*?)</a>", re.IGNORECASE | re.DOTALL
)


def _pre_html(text: str) -> str:
    """Fold any HTML the model produced into the same Markdown-ish markers."""
    if "<" not in text:
        return text
    text = _A_TAG_RE.sub(lambda m: f"{m.group(2).strip()} ({m.group(1).strip()})", text)

    def _swap(m: re.Match[str]) -> str:
        tag = m.group(1).lower()
        closing = m.group(0).startswith("</")
        if tag in ("b", "strong"):
            return "**"
        if tag == "br":
            return "\n"
        if tag in ("pre", "blockquote") and closing:
            return "\n"
        return ""

    return _HTML_TAG_RE.sub(_swap, text)


def _inline(raw: str, *, mode: str) -> str:
    """Convert inline Markdown of one line; returns escaped HTML or plain text."""
    s = _IMG_RE.sub(lambda m: m.group(1), raw)
    s = _LINK_RE.sub(lambda m: f"{m.group(1)} ({m.group(2)})", s)
    s = _CODE_RE.sub(lambda m: m.group(1), s)
    s = _BOLD_RE.sub(lambda m: f"{_B_OPEN}{m.group(1) or m.group(2)}{_B_CLOSE}", s)
    s = _ITALIC_STAR_RE.sub(lambda m: m.group(1), s)
    s = _ITALIC_UNDER_RE.sub(lambda m: m.group(1), s)
    s = _STRIKE_RE.sub(lambda m: m.group(1), s)
    s = _ESCAPED_RE.sub(lambda m: m.group(1), s)
    s = _LEFTOVER_MARKS_RE.sub("", s)
    if mode == "html":
        s = html.escape(s, quote=False)
        s = s.replace(_B_OPEN, "<b>").replace(_B_CLOSE, "</b>")
    else:
        s = s.replace(_B_OPEN, "").replace(_B_CLOSE, "")
    return s


def _convert(text: str, *, mode: str) -> str:
    if not text:
        return ""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = _pre_html(text)

    out: list[str] = []
    in_fence = False
    for line in text.split("\n"):
        if _FENCE_RE.match(line):
            in_fence = not in_fence
            continue
        if in_fence:
            out.append(html.escape(line, quote=False) if mode == "html" else line)
            continue
        if _HR_RE.match(line):
            continue
        if _TABLE_SEP_RE.match(line) and "|" in line:
            continue

        m = _TABLE_ROW_RE.match(line)
        if m and line.count("|") >= 2:
            cells = [c.strip() for c in m.group(1).split("|")]
            cells = [c for c in cells if c]
            out.append(" · ".join(_inline(c, mode=mode) for c in cells))
            continue

        m = _HEADING_RE.match(line)
        if m:
            content = m.group(1).replace("**", "").replace("__", "")
            body = _inline(content, mode=mode)
            if mode == "html":
                body = body.replace("<b>", "").replace("</b>", "")
                out.append(f"<b>{body}</b>" if body else "")
            else:
                out.append(body)
            continue

        m = _QUOTE_RE.match(line)
        if m:
            line = m.group(1)

        m = _BULLET_RE.match(line)
        if m:
            indent = " " * (2 * (len(m.group(1).expandtabs(2)) // 2))
            out.append(f"{indent}• {_inline(m.group(2), mode=mode)}")
            continue

        m = _NUMBERED_RE.match(line)
        if m:
            out.append(f"{m.group(1)}{m.group(2)}. {_inline(m.group(3), mode=mode)}")
            continue

        out.append(_inline(line, mode=mode))

    result = "\n".join(s.rstrip() for s in out)
    result = re.sub(r"\n{3,}", "\n\n", result)
    return result.strip()


def markdown_to_telegram_html(text: str) -> str:
    """Markdown/HTML soup → safe Telegram HTML (only ``<b>`` survives)."""
    try:
        return _convert(text, mode="html")
    except Exception:  # pragma: no cover - defensive; formatting must never break a reply
        return html.escape(text or "", quote=False)


def strip_markdown(text: str) -> str:
    """Markdown/HTML soup → plain text with ``•`` bullets and no markers."""
    try:
        return _convert(text, mode="plain")
    except Exception:  # pragma: no cover
        return text or ""


def looks_like_markdown(text: str) -> bool:
    """Cheap detector used by tests and logs."""
    if not text:
        return False
    return bool(
        re.search(
            r"\*\*|__|^\s{0,3}#{1,6}\s|^\s*[-*+]\s|```|^\s*\|.*\|\s*$|^\s*-{3,}\s*$", text, re.M
        )
    )
