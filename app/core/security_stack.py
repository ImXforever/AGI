"""Fifteen fail-closed security layers for Zenovix Ops.

Order is inbound → execution → outbound. A deny at any layer stops the work.
Existing modules (guard, policy, HITL, webhook verify, rate limit) are
called from here so there is one verdict the rest of the app can trust.
"""

from __future__ import annotations

import ipaddress
import re
import unicodedata
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlparse

from app.logging_setup import get_logger

log = get_logger("app.core.security_stack")

LAYERS: tuple[tuple[int, str, str], ...] = (
    (1, "unicode", "Normalize homoglyphs, strip bidi/zero-width, reject overlays"),
    (2, "length", "Cap inbound size so a single message cannot DoS the model"),
    (3, "prompt_injection", "Direct jailbreak / ignore-previous-instructions"),
    (4, "role_smuggling", "Chat-template and system-role markup in user text"),
    (5, "indirect_injection", "Commands hidden in retrieved docs or web data"),
    (6, "secret_harvest", "Attempts to extract keys, tokens, or private prompts"),
    (7, "tool_smuggle", "Shell, SQL, path-traversal smuggled as natural language"),
    (8, "attachments", "MIME allowlist, size cap, safe filenames"),
    (9, "ssrf", "Block private, loopback, metadata and non-http URLs"),
    (10, "rate_limit", "Per-sender window (enforced at ingest with Redis)"),
    (11, "webhook_auth", "Channel signatures verified at the gateway"),
    (12, "policy_hitl", "Unknown/high-risk actions need a manager record"),
    (13, "moderation", "Blocklist for fraud, malware and illegal content"),
    (14, "output_exfil", "Stop prompt leaks, secrets and suspicious links in replies"),
    (15, "audit", "Every deny is logged with layer id — never silent"),
)

MAX_INBOUND_CHARS = 4000
MAX_URLS = 8
#: 1.6.0 — attachment text is appended to the customer's message as framed
#: ``ATTACHED FILE … (DATA …):`` blocks (simulator + Telegram/WhatsApp
#: documents). That part is *data*, not the customer's words: it is split off
#: before the length / injection / smuggling layers, sanitised line by line
#: (``paksazi_dade``) and re-attached, so a 6-page PDF is neither rejected as
#: "over 4000 chars" nor able to smuggle instructions.
FILE_BLOCK_MARKER = "\n\nATTACHED FILE "
MAX_FILE_BLOCK_CHARS = 16000

# Hard deny: real bidi overrides / isolates and word-joiner tricks that can
# visually re-order or hide text. U+200C (ZWNJ) and U+200D (ZWJ) are NOT in
# this set on purpose: ZWNJ is the Persian/Urdu half-space typed on every
# keyboard ("می\u200cخوام") and ZWJ is inside most emoji sequences. In 1.2.0
# they were denied here, so ordinary Persian messages got no reply at all.
_BIDI = re.compile(r"[\u200b\u200e\u200f\u202a-\u202e\u2060-\u2069\ufeff]")
# Cosmetic zero-width characters: stripped by the normaliser, never denied.
_ZW_SOFT = re.compile(r"[\u200c\u200d]")
_ROLE_MARKUP = re.compile(
    r"(<\|im_start\|>|<\|im_end\|>|<\|system\|>|\[INST\]|\[/INST\]|<<SYS>>|"
    r"</s>|<s>|###\s*System|###\s*Instruction)",
    re.I,
)
_SECRET_ASK = re.compile(
    r"(api[_ -]?key|secret[_ -]?key|private[_ -]?key|webhook[_ -]?secret|"
    r"show\s+(me\s+)?(your\s+)?(system\s+)?prompt|print\s+env|"
    r"BEGIN\s+PRIVATE\s+KEY|sk-[A-Za-z0-9]{16,}|tsec_[A-Za-z0-9_-]{8,})",
    re.I,
)
_TOOL_SMUGGLE = re.compile(
    r"(\brm\s+-rf\b|\bdrop\s+table\b|\btruncate\s+table\b|"
    r"\bunion\s+select\b|\.\./|\bcurl\s+[^\n]+\|\s*(sh|bash)\b|"
    r"\bwget\s+[^\n]+\|\s*(sh|bash)\b|\beval\s*\(|\bexec\s*\("
    r"|/etc/passwd|file://)",
    re.I,
)
_URL = re.compile(r"https?://[^\s<>\"']+", re.I)
_SECRET_OUT = re.compile(
    r"(sk-[A-Za-z0-9]{16,}|tsec_[A-Za-z0-9_-]{8,}|BEGIN RSA PRIVATE KEY|"
    r"pa_session=|TELEGRAM_BOT_TOKEN)",
    re.I,
)
_BLOCK_SYNC = (
    "keygen",
    "cracked",
    "botnet",
    "ddos",
    "stealer",
    "سود تضمینی",
    "پول رایگان",
    "مخدر",
    "اسلحه",
)

_PRIVATE_HOSTS = {"localhost", "127.0.0.1", "0.0.0.0", "::1", "metadata.google.internal"}  # nosec B104 - SSRF blocklist, not a bind


@dataclass(frozen=True)
class LayerResult:
    layer: int
    name: str
    allowed: bool
    reason: str = ""


@dataclass
class SecurityVerdict:
    allowed: bool
    layer: int = 0
    name: str = ""
    reason: str = ""
    text: str = ""
    trail: list[LayerResult] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "allowed": self.allowed,
            "layer": self.layer,
            "name": self.name,
            "reason": self.reason,
            "layers": [{"id": n, "name": k, "purpose": p} for n, k, p in LAYERS],
            "trail": [
                {"layer": r.layer, "name": r.name, "allowed": r.allowed, "reason": r.reason}
                for r in self.trail
            ],
        }


def _normalize(text: str) -> str:
    decomposed = unicodedata.normalize("NFKC", text or "")
    stripped = "".join(c for c in decomposed if unicodedata.category(c) != "Mn")
    return _BIDI.sub("", stripped)


def _deny(
    layer: int, name: str, reason: str, text: str, trail: list[LayerResult]
) -> SecurityVerdict:
    trail.append(LayerResult(layer, name, False, reason))
    log.warning(
        "security_deny",
        extra={"action": "security.deny", "layer": layer, "name": name, "reason": reason},
    )
    return SecurityVerdict(False, layer, name, reason, text, trail)


def _ok(layer: int, name: str, trail: list[LayerResult]) -> None:
    trail.append(LayerResult(layer, name, True, ""))


def split_file_block(text: str) -> tuple[str, str]:
    """Return ``(customer_text, file_block)``.

    The file block starts at the first ``ATTACHED FILE`` frame that sits on its
    own paragraph (how :func:`app.core.simulator.frame_file_text` and
    :func:`app.core.pipeline.attach_file_text` build it). A message that *is*
    only a file block (photo without caption) yields an empty customer text.
    """
    raw = text or ""
    if raw.startswith("ATTACHED FILE "):
        return "", raw
    idx = raw.find(FILE_BLOCK_MARKER)
    if idx < 0:
        return raw, ""
    return raw[:idx], raw[idx + 2 :]


def sanitize_file_block(block: str) -> str:
    """Layer-5 treatment for attachment text: strip command-like lines, cap size."""
    if not block:
        return ""
    from app.core.guard import paksazi_dade

    cleaned = _normalize(block)
    if len(cleaned) > MAX_FILE_BLOCK_CHARS:
        cleaned = cleaned[:MAX_FILE_BLOCK_CHARS] + " …[truncated]"
    safe, removed = paksazi_dade(cleaned)
    if removed:
        log.info(
            "file_block_sanitized",
            extra={"action": "security.file_block", "removed_lines": removed},
        )
    return safe


def inspect_inbound(
    text: str,
    *,
    attachments: tuple[Any, ...] | list[Any] = (),
    rate_limited: bool = False,
    webhook_ok: bool = True,
) -> SecurityVerdict:
    """Layers 1–11 + 13 on user-controlled input. Fail closed."""
    trail: list[LayerResult] = []
    raw, file_block = split_file_block(text or "")
    if file_block:
        # 1.6.0 — attachment text is data: sanitised, size-capped, never a
        # reason to reject the customer's own message (see FILE_BLOCK_MARKER).
        file_block = sanitize_file_block(file_block)

    # L01 unicode — deny only genuine overrides. ZWNJ/ZWJ are legitimate
    # (Persian half-space, emoji joiner); they only get stripped for the
    # pattern checks below, the original text is what the model answers.
    if _BIDI.search(raw):
        return _deny(1, "unicode", "bidi or zero-width overlay", raw, trail)
    cleaned = _normalize(raw)
    # Pattern layers look at a copy without ZWNJ/ZWJ so "ig\u200cnore" cannot
    # dodge them; the customer's text itself keeps its half-spaces.
    probe = _ZW_SOFT.sub("", cleaned)
    _ok(1, "unicode", trail)

    # L02 length
    if len(cleaned) > MAX_INBOUND_CHARS:
        return _deny(2, "length", f"over {MAX_INBOUND_CHARS} chars", cleaned, trail)
    _ok(2, "length", trail)

    has_files = bool(attachments) or bool(file_block)
    if not cleaned.strip() and not has_files:
        return _deny(3, "prompt_injection", "empty question", cleaned, trail)

    # L03–L07 apply to user text. Attachment-only messages skip them.
    if cleaned.strip():
        from app.core.guard import barresi_vorodi

        safe, reason = barresi_vorodi(probe)
        if not safe:
            return _deny(3, "prompt_injection", reason or "injection", cleaned, trail)
        _ok(3, "prompt_injection", trail)

        if _ROLE_MARKUP.search(probe):
            return _deny(4, "role_smuggling", "chat-template markup in user text", cleaned, trail)
        _ok(4, "role_smuggling", trail)

        # L05 is inspect_data() on retrieved docs — not user chat (false positives).
        _ok(5, "indirect_injection", trail)

        if _SECRET_ASK.search(probe):
            return _deny(6, "secret_harvest", "credential or prompt extraction", cleaned, trail)
        _ok(6, "secret_harvest", trail)

        if _TOOL_SMUGGLE.search(probe):
            return _deny(7, "tool_smuggle", "shell/sql/path payload", cleaned, trail)
        _ok(7, "tool_smuggle", trail)
    else:
        _ok(3, "prompt_injection", trail)
        _ok(4, "role_smuggling", trail)
        _ok(5, "indirect_injection", trail)
        _ok(6, "secret_harvest", trail)
        _ok(7, "tool_smuggle", trail)

    # L08 attachments
    from app.core.security_validate import validate_inbound_attachment

    for att in attachments or ():
        filename = str(
            getattr(att, "filename", None)
            or (att.get("filename") if isinstance(att, dict) else "file")
        )
        ctype = str(
            getattr(att, "content_type", None)
            or (att.get("content_type") if isinstance(att, dict) else "application/octet-stream")
        )
        size = int(
            getattr(att, "size", None) or (att.get("size") if isinstance(att, dict) else 0) or 0
        )
        check = validate_inbound_attachment(filename=filename, content_type=ctype, size_bytes=size)
        if not check.get("ok"):
            return _deny(8, "attachments", str(check.get("reason") or "attachment"), cleaned, trail)
    _ok(8, "attachments", trail)

    # L09 SSRF
    urls = _URL.findall(probe)[: MAX_URLS + 1]
    if len(urls) > MAX_URLS:
        return _deny(9, "ssrf", "too many urls", cleaned, trail)
    for url in urls:
        bad = _ssrf_reason(url)
        if bad:
            return _deny(9, "ssrf", bad, cleaned, trail)
    _ok(9, "ssrf", trail)

    # L10 rate limit (flag from ingest)
    if rate_limited:
        return _deny(10, "rate_limit", "sender exceeded window", cleaned, trail)
    _ok(10, "rate_limit", trail)

    # L11 webhook
    if not webhook_ok:
        return _deny(11, "webhook_auth", "channel signature failed", cleaned, trail)
    _ok(11, "webhook_auth", trail)

    # L13 moderation (sync, no DB — extra words applied at publish time)
    lowered = probe.lower()
    for word in _BLOCK_SYNC:
        if word.lower() in lowered:
            return _deny(13, "moderation", f"blocked term: {word}", cleaned, trail)
    _ok(13, "moderation", trail)

    if file_block:
        cleaned = f"{cleaned}\n\n{file_block}" if cleaned.strip() else file_block
    return SecurityVerdict(True, 0, "", "", cleaned, trail)


def inspect_data(text: str, *, source: str = "") -> SecurityVerdict:
    """Layer 5 on retrieved documents before they enter the prompt."""
    from app.core.guard import sanitize_for_llm

    trail: list[LayerResult] = []
    framed = sanitize_for_llm(text or "", source=source)
    _ok(5, "indirect_injection", trail)
    return SecurityVerdict(True, 5, "indirect_injection", "", framed, trail)


def inspect_action(
    action: str,
    *,
    actor_role: str = "agent",
    approved: bool = False,
    approval_id: str = "",
    context: dict[str, Any] | None = None,
) -> SecurityVerdict:
    """Layer 12 — policy + HITL."""
    from app.core.policy import evaluate_action

    trail: list[LayerResult] = []
    decision = evaluate_action(
        action,
        actor_role=actor_role,
        approved=approved,
        approval_id=approval_id,
        context=context,
    )
    if not decision.allowed:
        return _deny(12, "policy_hitl", decision.reason, action, trail)
    _ok(12, "policy_hitl", trail)
    return SecurityVerdict(True, 12, "policy_hitl", "", action, trail)


def inspect_outbound(text: str) -> SecurityVerdict:
    """Layer 14 — replies cannot leak prompts, secrets or exfil links."""
    from app.core.catalog_context import leaked_tool_protocol, strip_tool_protocol
    from app.core.guard import barresi_khorooji, paksazi_khorooji

    trail: list[LayerResult] = []
    raw = strip_tool_protocol(text or "")
    if leaked_tool_protocol(raw):
        return _deny(14, "output_exfil", "tool protocol leaked to customer", raw, trail)
    safe, reason = barresi_khorooji(raw)
    if not safe:
        return _deny(14, "output_exfil", reason or "output leak", raw, trail)
    if _SECRET_OUT.search(raw):
        return _deny(14, "output_exfil", "secret material in reply", raw, trail)
    cleaned, removed = paksazi_khorooji(raw)
    if removed:
        trail.append(LayerResult(14, "output_exfil", True, f"stripped {removed} sentences"))
        return SecurityVerdict(True, 14, "output_exfil", "", cleaned, trail)
    _ok(14, "output_exfil", trail)
    return SecurityVerdict(True, 14, "output_exfil", "", cleaned, trail)


def audit_verdict(verdict: SecurityVerdict, *, channel: str = "", sender_id: str = "") -> None:
    """Layer 15 — always record. Never raises. Sender is hashed, not stored raw."""
    import hashlib

    sid = ""
    if sender_id:
        sid = hashlib.sha256(str(sender_id).encode("utf-8")).hexdigest()[:12]
    log.info(
        "security_audit",
        extra={
            "action": "security.audit",
            "allowed": verdict.allowed,
            "layer": verdict.layer,
            "name": verdict.name,
            "reason": verdict.reason,
            "channel": channel,
            "sender_hash": sid,
        },
    )


def check_url(url: str) -> str:
    """Layer 9 helper for webtools: empty string means allowed."""
    return _ssrf_reason(url)


def layers_catalog() -> list[dict[str, Any]]:
    return [{"id": n, "name": k, "purpose": p} for n, k, p in LAYERS]


def _ssrf_reason(url: str) -> str:
    try:
        parsed = urlparse(url)
    except Exception:
        return "malformed url"
    scheme = (parsed.scheme or "").lower()
    if scheme not in {"http", "https"}:
        return f"scheme {scheme or 'none'} blocked"
    host = (parsed.hostname or "").lower()
    if not host or host in _PRIVATE_HOSTS or host.endswith(".internal"):
        return f"host {host or 'empty'} blocked"
    if host == "169.254.169.254":
        return "cloud metadata blocked"
    try:
        ip = ipaddress.ip_address(host)
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
            return "private ip blocked"
    except ValueError:
        pass
    return ""
