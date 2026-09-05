"""Deep approval gates — adapted from Hermes Agent's tools/approval.py.

Layer 1 (existing): Pattern-matching for shell commands (safe/guard/block)
Layer 2 (new):       File content analysis (injection, malware, XSS detection)
Layer 3 (new):       URL safety analysis (SSRF, phishing, suspicious patterns)
Layer 4 (new):       Context-aware risk scoring (role-based, history-aware)
Layer 5 (new):       Persistent audit trail (PostgreSQL)
Layer 6 (new):       Smart auto-approve / auto-reject rules

All layers compose into a single classify() call that returns an
ApprovalDecision with full reasoning.
"""

from __future__ import annotations

import hashlib
import json
import re
import time
from dataclasses import dataclass, field
from typing import Any

from app.logging_setup import get_logger

log = get_logger("app.core.hitl.approval")

# =========================================================
# Layer 1: Shell command patterns (from existing approval.py)
# =========================================================

BLOCK_PATTERNS = [
    re.compile(r"\brm\s+(-\w*r\w*\s+)?/", re.I),
    re.compile(r"\brm\s+(-\w*r\w*\s+)~", re.I),
    re.compile(r"\bmkfs\b", re.I),
    re.compile(r"\bdd\s+if=.*of=/dev/", re.I),
    re.compile(r"\bformat\s+[a-zA-Z]:", re.I),
    re.compile(r"\b(SYSTEM|SAM|SECURITY|boot)\s+registry\b", re.I),
    re.compile(r"\bcd\s+/\s*&&", re.I),
    re.compile(r":\(\)\{\s*:\|:\s*&\s*\}", re.I),
    re.compile(r">\s*/dev/sd[a-z]", re.I),
    re.compile(r"shutdown|reboot|poweroff|halt", re.I),
    re.compile(r"chmod\s+777\s+/", re.I),
    re.compile(r"\bsudo\s+rm\b", re.I),
]

GUARD_PATTERNS = [
    re.compile(
        r"\b(pip\s+install|npm\s+i|npm\s+install|yarn\s+add|apt\s+(install|remove|purge)|brew\s+install)\b",
        re.I,
    ),
    re.compile(r"\b(curl|wget|ssh|scp|rsync|sftp)\b", re.I),
    re.compile(r"\bdocker\s+(run|exec|rm|stop|kill|push|pull)\b", re.I),
    re.compile(r"\bkubectl\b", re.I),
    re.compile(r"\bdocker\s+compose\b", re.I),
    re.compile(r"\brm\s+(-[a-zA-Z]*\s+)*\S+", re.I),
    re.compile(r"\bmv\s+.+/\s*$", re.I),
    re.compile(r">\s*\S+", re.I),
    re.compile(r"\benv\b.*=", re.I),
    re.compile(r"\bexport\b.*=", re.I),
    re.compile(r"\bcurl\s.*\|\s*(bash|sh)\b", re.I),
    re.compile(r"\bchmod\b", re.I),
    re.compile(r"\bchown\b", re.I),
    re.compile(r"\bsudo\b", re.I),
    re.compile(r"\bDROP\s+TABLE\b", re.I),
    re.compile(r"\bDELETE\s+FROM\b", re.I),
    re.compile(r"\bTRUNCATE\b", re.I),
    re.compile(r"\bkill\s+-9\b", re.I),
    re.compile(r"\bpkill\b", re.I),
    re.compile(r"\bunzip\b", re.I),
    re.compile(r"\btar\s+.*x\w*f\b", re.I),
    re.compile(r"\b7z\s+(x|e)\b", re.I),
]

SAFE_PATTERNS = [
    re.compile(r"\b(python|python3|node|npm)\s+-c\b", re.I),
    re.compile(r"\bgit\s+(status|log|diff|branch|show|remote|tag)\b", re.I),
    re.compile(r"\b(ls|pwd|echo|date|whoami|which|cat|head|tail|wc|grep|find|sort|uniq)\b", re.I),
    re.compile(r"\b(pytest|unittest|ruff|black|isort|mypy)\b", re.I),
    re.compile(r"\bpip\s+(list|show|freeze)\b", re.I),
]

# =========================================================
# Layer 2: File content analysis patterns
# =========================================================

INJECTION_PATTERNS = [
    re.compile(r"\{\{.*eval.*\}\}", re.I),
    re.compile(r"\{\{.*exec.*\}\}", re.I),
    re.compile(r"<script[^>]*>", re.I),
    re.compile(r"on\w+\s*=\s*['\"]?\s*javascript:", re.I),
    re.compile(r"__import__\s*\(", re.I),
    re.compile(r"subprocess\.(?:call|run|Popen)", re.I),
    re.compile(r"os\.(?:system|popen)\s*\(", re.I),
    re.compile(r"eval\s*\(", re.I),
    re.compile(r"exec\s*\(", re.I),
    re.compile(r"UNION\s+SELECT", re.I),
    re.compile(r"';?\s*DROP\s", re.I),
    re.compile(r"\bbase64\b.*\bdecode\b.*\bexec\b", re.I),
    re.compile(r"\\x[0-9a-f]{2}.*\\x[0-9a-f]{2}.*\\x[0-9a-f]{2}", re.I),
    re.compile(r"\bcurl\b.*\|\s*(?:bash|sh|zsh)\b", re.I),
    re.compile(r"\bwget\b.*\|\s*(?:bash|sh|zsh)\b", re.I),
    re.compile(r"\bsh\s*-c\b", re.I),
]

MALWARE_INDICATORS = [
    re.compile(r"reverse\s+shell", re.I),
    re.compile(r"nc\s+-l[ep]", re.I),
    re.compile(r"bash\s+-i\b", re.I),
    re.compile(r"/dev/tcp/", re.I),
    re.compile(r"msfvenom|metasploit", re.I),
    re.compile(r"keylogger|backdoor|trojan", re.I),
    re.compile(r"crypto\s*mining|stratum\+tcp", re.I),
]


# =========================================================
# Layer 3: URL safety analysis
# =========================================================

PHISHING_INDICATORS = [
    re.compile(
        r"(?:login|signin|verify|secure|account|paypal|apple|microsoft)\b.*\.(?!com|org|net)", re.I
    ),
    re.compile(r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}", re.I),
    re.compile(r"\.onion\b", re.I),
    re.compile(r"bit\.ly|tinyurl|t\.co", re.I),
]

SSRF_PATTERNS = [
    re.compile(r"169\.254\.", re.I),
    re.compile(r"127\.0\.", re.I),
    re.compile(r"10\.\d+\.\d+\.\d+", re.I),
    re.compile(r"172\.(1[6-9]|2\d|3[01])\.", re.I),
    re.compile(r"192\.168\.", re.I),
    re.compile(r"metadata\.google", re.I),
    re.compile(r"localhost", re.I),
]


# =========================================================
# Layer 1: Shell command classification
# =========================================================


def classify_shell(command: str) -> str:
    """Classify shell command: safe / guard / block."""
    if not command or not command.strip():
        return "block"
    cmd = command.strip()
    for pat in BLOCK_PATTERNS:
        if pat.search(cmd):
            return "block"
    for pat in GUARD_PATTERNS:
        if pat.search(cmd):
            return "guard"
    for pat in SAFE_PATTERNS:
        if pat.search(cmd):
            return "safe"
    return "guard"


# =========================================================
# Layer 2: File content analysis
# =========================================================


def analyze_file_content(content: str) -> dict[str, Any]:
    """Analyze file content for injections, malware, XSS.

    Returns {"risk_level": 0-10, "findings": list[str]}.
    """
    findings: list[str] = []
    risk = 0

    for pat in INJECTION_PATTERNS:
        if pat.search(content):
            findings.append(f"inject: {pat.pattern[:30]}")
            risk += 3

    for pat in MALWARE_INDICATORS:
        if pat.search(content):
            findings.append(f"malware: {pat.pattern[:30]}")
            risk += 5

    # NOTE: the previous pattern required eight *consecutive* "import <name>"
    # tokens on one run, so it never matched real multi-line source and the
    # heuristic was dead. Count import statements across lines instead.
    if len(re.findall(r"^\s*(?:import|from)\s+\w+", content, re.MULTILINE)) >= 8:
        findings.append("excessive imports")
        risk += 2

    b64_blocks = re.findall(r"[A-Za-z0-9+/]{40,}={0,2}", content)
    if len(b64_blocks) > 3:
        findings.append("many base64 blocks")
        risk += 2

    return {"risk_level": min(risk, 10), "findings": findings}


# =========================================================
# Layer 3: URL safety
# =========================================================


def analyze_url_safety(url: str) -> dict[str, Any]:
    """Analyze URL for phishing, SSRF, suspicious patterns.

    Returns {"risk_level": 0-10, "findings": list[str]}.
    """
    findings: list[str] = []
    risk = 0

    if not url:
        return {"risk_level": 0, "findings": []}

    for pat in PHISHING_INDICATORS:
        if pat.search(url):
            findings.append(f"phishing: {pat.pattern[:30]}")
            risk += 4

    for pat in SSRF_PATTERNS:
        if pat.search(url):
            findings.append(f"SSRF: {pat.pattern[:30]}")
            risk += 5

    if re.search(r"\.(ru|cn|tk|ml|ga|cf|gq|pw)\b", url, re.I):
        findings.append("suspicious TLD")
        risk += 1

    return {"risk_level": min(risk, 10), "findings": findings}


# =========================================================
# Layer 4: Context-aware risk scoring
# =========================================================

ROLE_RISK_MULTIPLIER: dict[str, float] = {
    "admin": 0.5,
    "godfather": 0.3,
    "underboss": 0.6,
    "capo": 0.8,
    "soldier": 1.0,
    "associate": 1.3,
}


def context_risk_modifier(risk: int, role: str = "associate", recent_blocks: int = 0) -> int:
    """Modify risk based on user context."""
    multiplier = ROLE_RISK_MULTIPLIER.get(role, 1.0)
    modifier = multiplier * (1.0 + recent_blocks * 0.3)
    return max(0, min(10, int(risk * modifier)))


# =========================================================
# Layer 5: Audit trail (PostgreSQL via app.storage.pg)
# =========================================================


async def audit_log(
    user_id: int,
    action: str,
    target: str,
    risk_level: int,
    decision: str,
    risk_tags: list[str] | None = None,
) -> None:
    """Log an approval decision to the PostgreSQL audit trail."""
    try:
        from app.storage.pg import audit

        await audit(
            action=f"approval.{decision}",
            actor=str(user_id),
            entity="approval_audit",
            entity_id=target[:200],
            details={
                "user_id": user_id,
                "action": action,
                "target": target[:500],
                "risk_level": risk_level,
                "decision": decision,
                "risk_tags": risk_tags or [],
            },
        )
    except Exception:
        log.exception("audit_log_failed", extra={"action": "approval.audit_log"})


async def audit_history(user_id: int = 0, limit: int = 20) -> list[dict[str, Any]]:
    """Get recent audit entries from PostgreSQL."""
    try:
        from app.storage.pg import get_pool

        pool = await get_pool()
        if user_id:
            rows = await pool.fetch(
                """
                SELECT id, action, actor, entity, entity_id, details,
                       created_at
                FROM audit_log
                WHERE entity = 'approval_audit'
                  AND actor = $1
                ORDER BY id DESC
                LIMIT $2
                """,
                str(user_id),
                limit,
            )
        else:
            rows = await pool.fetch(
                """
                SELECT id, action, actor, entity, entity_id, details,
                       created_at
                FROM audit_log
                WHERE entity = 'approval_audit'
                ORDER BY id DESC
                LIMIT $1
                """,
                limit,
            )
        results: list[dict[str, Any]] = []
        for row in rows:
            r = dict(row)
            if r.get("created_at"):
                r["created_at"] = str(r["created_at"])
            if r.get("details") and isinstance(r["details"], str):
                try:
                    r["details"] = json.loads(r["details"])
                except (json.JSONDecodeError, TypeError):
                    pass
            results.append(r)
        return results
    except Exception:
        log.exception("audit_history_failed", extra={"action": "approval.audit_history"})
        return []


# =========================================================
# Layer 6: Smart auto-approve / auto-reject rules
# =========================================================

_AUTO_APPROVE_CONTEXTS = [
    re.compile(r"(pytest|unittest|test_|_test\.py)\b", re.I),
    re.compile(r"\b(ruff|black|isort|mypy|flake8)\b", re.I),
]

_AUTO_REJECT_CONTEXTS = [
    re.compile(r"(format\s+[a-zA-Z]:|rm\s+-rf\s+/)", re.I),
    re.compile(r"eval\s*\(\s*input", re.I),
]


def check_auto_rules(command: str, context: str = "") -> str | None:
    """Check if command should be auto-approved or auto-rejected.
    Returns 'approve', 'reject', or None (needs manual review).
    """
    combined = f"{command} {context}"
    for pat in _AUTO_REJECT_CONTEXTS:
        if pat.search(combined):
            return "reject"
    for pat in _AUTO_APPROVE_CONTEXTS:
        if pat.search(combined):
            return "approve"
    return None


# =========================================================
# Main classification (unified Layer 1-6)
# =========================================================


@dataclass
class ApprovalDecision:
    """Unified output from all approval layers."""

    tier: str  # "safe", "guard", "block"
    risk_level: int  # 0-10 scale
    reason: str
    risk_tags: list[str] = field(default_factory=list)
    auto_decision: str = ""  # "approve", "reject", "" (from Layer 6)
    context_notes: str = ""

    @property
    def needs_approval(self) -> bool:
        return self.tier == "guard" and not self.auto_decision == "approve"

    @property
    def is_blocked(self) -> bool:
        return self.tier == "block" or self.auto_decision == "reject"


def classify_command(
    command: str,
    role: str = "associate",
    recent_blocks: int = 0,
) -> ApprovalDecision:
    """Full classification pipeline (Layers 1-6)."""
    if not command or not command.strip():
        return ApprovalDecision("block", 10, "empty command")

    cmd = command.strip()

    # Layer 1: Shell command patterns
    shell_tier = classify_shell(cmd)
    risk_map = {"safe": 0, "guard": 5, "block": 10}
    risk = risk_map.get(shell_tier, 5)

    tag = _identify_risk(cmd) if shell_tier != "safe" else ""
    tags = [tag] if tag else []
    reason = {
        "safe": "safe command",
        "guard": f"needs approval: {tag}" if tag else "needs approval: unknown",
        "block": "blocked",
    }.get(shell_tier, "")

    # Layer 4: Context modifier
    risk = context_risk_modifier(risk, role, recent_blocks)

    # Layer 6: Auto rules
    auto_decision = check_auto_rules(cmd)

    return ApprovalDecision(
        tier=shell_tier,
        risk_level=risk,
        reason=reason,
        risk_tags=tags,
        auto_decision=auto_decision or "",
    )


def classify_file_write(
    path: str,
    content: str,
    role: str = "associate",
) -> ApprovalDecision:
    """Classify a file write operation (Layers 1-6 for files)."""
    if not content:
        return ApprovalDecision("safe", 0, "empty file")

    analysis = analyze_file_content(content)
    risk = analysis["risk_level"]
    findings = analysis["findings"]

    if risk >= 8:
        return ApprovalDecision(
            "block", risk, f"dangerous content: {'; '.join(findings[:3])}", risk_tags=findings
        )
    elif risk >= 4:
        return ApprovalDecision(
            "guard", risk, f"suspicious content: {'; '.join(findings[:3])}", risk_tags=findings
        )
    return ApprovalDecision("safe", risk, "file content appears safe")


def classify_url(url: str, role: str = "associate") -> ApprovalDecision:
    """Classify a URL operation (Layer 3)."""
    analysis = analyze_url_safety(url)
    risk = analysis["risk_level"]
    findings = analysis["findings"]

    if risk >= 8:
        return ApprovalDecision(
            "block", risk, f"dangerous URL: {'; '.join(findings[:3])}", risk_tags=findings
        )
    elif risk >= 4:
        return ApprovalDecision(
            "guard", risk, f"suspicious URL: {'; '.join(findings[:3])}", risk_tags=findings
        )
    return ApprovalDecision("safe", risk, "URL appears safe")


# =========================================================
# Pending approval storage (Redis-backed, survives restarts)
# =========================================================

_PENDING_KEY_PREFIX = "hitl:pending:"
_PENDING_EXPIRY = 300  # 5 minutes


async def _get_redis():
    try:
        from app.storage.redis import get_redis

        return await get_redis()
    except Exception:
        return None


def _gen_approval_id(command: str, user_id: int) -> str:
    raw = f"{command}:{user_id}:{time.time()}"
    return hashlib.sha256(raw.encode()).hexdigest()[:12]


def create_approval_request(
    command: str,
    user_id: int,
    role: str = "associate",
) -> dict[str, Any]:
    decision = classify_command(command, role)
    aid = _gen_approval_id(command, user_id)
    import asyncio

    try:
        loop = asyncio.get_running_loop()
        loop.create_task(_store_pending(aid, command, user_id, role, decision))
    except RuntimeError:
        pass
    return {
        "approval_id": aid,
        "command": command,
        "reason": decision.reason,
        "risk_level": decision.risk_level,
        "risk_tags": decision.risk_tags,
    }


async def _store_pending(aid: str, command: str, user_id: int, role: str, decision: Any) -> None:
    import json

    redis = await _get_redis()
    if redis is None:
        return
    key = f"{_PENDING_KEY_PREFIX}{aid}"
    await redis.hset(
        key,
        mapping={
            "command": command,
            "user_id": str(user_id),
            "role": role,
            "risk_tags": json.dumps(decision.risk_tags),
            "reason": decision.reason,
            "risk_level": str(decision.risk_level),
            "timestamp": str(time.time()),
        },
    )
    await redis.expire(key, _PENDING_EXPIRY)


async def _pop_pending(approval_id: str) -> dict[str, Any] | None:
    redis = await _get_redis()
    if redis is None:
        return None
    key = f"{_PENDING_KEY_PREFIX}{approval_id}"
    try:
        data = await redis.hgetall(key)
        if not data:
            return None
        await redis.delete(key)
    except Exception:
        log.warning("pending_approval_unavailable", extra={"action": "approval.pending.read"})
        return None
    return {
        "command": data.get(b"command", b"").decode(),
        "user_id": int(data.get(b"user_id", b"0").decode()),
        "role": data.get(b"role", b"associate").decode(),
        "risk_tags": json.loads(data.get(b"risk_tags", b"[]").decode()),
        "reason": data.get(b"reason", b"").decode(),
        "risk_level": int(data.get(b"risk_level", b"0").decode()),
        "timestamp": float(data.get(b"timestamp", b"0").decode()),
    }


async def approve_request(approval_id: str, admin_id: int = 0) -> bool:
    req = await _pop_pending(approval_id)
    if req and time.time() - req["timestamp"] < _PENDING_EXPIRY:
        await audit_log(
            admin_id, "approve", req["command"], req["risk_level"], "approved", req["risk_tags"]
        )
        return True
    return False


async def reject_request(approval_id: str, admin_id: int = 0) -> bool:
    req = await _pop_pending(approval_id)
    if req:
        await audit_log(
            admin_id, "reject", req["command"], req["risk_level"], "rejected", req["risk_tags"]
        )
        return True
    return False


async def get_pending_approvals() -> list[dict[str, Any]]:
    redis = await _get_redis()
    if redis is None:
        return []
    try:
        keys = []
        cursor: bytes | int = 0
        while True:
            cursor, batch = await redis.scan(
                cursor=cursor,
                match=f"{_PENDING_KEY_PREFIX}*",
                count=100,
            )
            keys.extend(batch)
            if cursor in (0, b"0", "0"):
                break
    except Exception:
        log.warning("pending_approval_scan_failed", extra={"action": "approval.pending.scan"})
        return []

    results: list[dict[str, Any]] = []
    now = time.time()
    for key in keys:
        try:
            data = await redis.hgetall(key)
            if not data:
                continue
            ts = float(data.get(b"timestamp", b"0").decode())
            if now - ts > _PENDING_EXPIRY:
                await redis.delete(key)
                continue
        except Exception:
            log.debug("hitl_pending_scan_item_failed", exc_info=True)
            data = None
        if not data:
            continue
        aid = (
            key.decode().removeprefix(_PENDING_KEY_PREFIX)
            if isinstance(key, bytes)
            else key.removeprefix(_PENDING_KEY_PREFIX)
        )
        results.append(
            {
                "approval_id": aid,
                "command": data.get(b"command", b"").decode(),
                "user_id": int(data.get(b"user_id", b"0").decode()),
                "role": data.get(b"role", b"associate").decode(),
                "reason": data.get(b"reason", b"").decode(),
                "risk_level": int(data.get(b"risk_level", b"0").decode()),
                "timestamp": ts,
            }
        )
    return results


# =========================================================
# Legacy compatibility
# =========================================================


@dataclass
class ApprovalResult:
    tier: str
    reason: str
    needs_approval: bool = False
    risk_tags: list[str] | None = None

    def __post_init__(self) -> None:
        if self.risk_tags is None:
            self.risk_tags = []


def _identify_risk(cmd: str, matched_pat: Any = None) -> str:
    low = cmd.lower()
    if any(x in low for x in ("pip", "npm", "apt", "brew", "yarn")):
        return "package install"
    if any(x in low for x in ("curl", "wget", "ssh", "scp", "rsync")):
        return "network operation"
    if any(x in low for x in ("docker", "kubectl", "compose")):
        return "container"
    if "rm" in low:
        return "file deletion"
    if any(x in low for x in ("chmod", "chown", "sudo")):
        return "permission change"
    if any(x in low for x in ("env", "export")):
        return "env variable"
    if any(x in low for x in ("drop", "truncate", "delete")):
        return "database operation"
    if any(x in low for x in ("kill", "pkill")):
        return "process management"
    return "unknown"
