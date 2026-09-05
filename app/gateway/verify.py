"""Constant-time signature verification for inbound webhooks."""

from __future__ import annotations

import base64
import hashlib
import hmac
import re
import time
from dataclasses import dataclass
from typing import Any

from app.logging_setup import get_logger

log = get_logger("app.gateway.verify")

__all__ = [
    "VerifyResult",
    "verify_telegram",
    "verify_meta_signature",
    "verify_meta_handshake",
    "verify_twilio_signature",
    "verify_sendgrid_signature",
    "verify_svix_signature",
]


@dataclass(frozen=True)
class VerifyResult:
    """Outcome of a webhook signature check."""

    ok: bool
    reason: str = ""
    data: dict[str, Any] | None = None


# ── Telegram ───────────────────────────────────────────────────────


def verify_telegram(
    secret_token: str,
    header_value: str | None,
    *,
    max_age: int = 300,
    timestamp: int | None = None,
) -> VerifyResult:
    """Verify ``X-Telegram-Bot-Api-Secret-Token`` header.

    Telegram sends this header with every webhook call.  The value must
    match the secret token set during ``setWebhook``.

    For added replay protection the optional ``timestamp`` and ``max_age``
    parameters can enforce a time window.
    """
    if not header_value:
        return VerifyResult(ok=False, reason="missing header")

    if not hmac.compare_digest(header_value, secret_token):
        return VerifyResult(ok=False, reason="token mismatch")

    if timestamp is not None and max_age > 0:
        if abs(time.time() - timestamp) > max_age:
            return VerifyResult(ok=False, reason="timestamp expired")

    return VerifyResult(ok=True)


# ── Meta (WhatsApp Cloud API) ──────────────────────────────────────


def verify_meta_signature(
    app_secret: str,
    body: bytes,
    header_signature: str | None,
    header_signature_256: str | None = None,
) -> VerifyResult:
    """Verify ``X-Hub-Signature`` or ``X-Hub-Signature-256`` from Meta.

    Uses HMAC-SHA1 (legacy) or HMAC-SHA256 (preferred).
    Constant-time comparison throughout.
    """
    if not header_signature and not header_signature_256:
        return VerifyResult(ok=False, reason="no signature header")

    # Prefer SHA-256 if available
    raw_header = header_signature_256 or header_signature or ""
    match = re.match(r"sha(1|256)=(.+)", raw_header)
    if not match:
        return VerifyResult(ok=False, reason="malformed signature")

    algo = match.group(1)
    expected_hex = match.group(2)

    if algo == "256":
        computed = hmac.new(app_secret.encode(), body, hashlib.sha256).hexdigest()
    else:
        computed = hmac.new(app_secret.encode(), body, hashlib.sha1).hexdigest()

    if not hmac.compare_digest(computed, expected_hex):
        return VerifyResult(ok=False, reason="signature mismatch")

    return VerifyResult(ok=True)


def verify_meta_handshake(
    verify_token: str,
    mode: str | None,
    challenge: str | None,
    hub_verify_token: str | None,
) -> VerifyResult:
    """Handle the Meta webhook verification GET request.

    Returns ``VerifyResult`` with the challenge in ``data`` on success.
    """
    if mode != "subscribe" or not hub_verify_token:
        return VerifyResult(ok=False, reason="invalid mode or token")

    if not hmac.compare_digest(hub_verify_token, verify_token):
        return VerifyResult(ok=False, reason="verify token mismatch")

    if not challenge:
        return VerifyResult(ok=False, reason="missing challenge")

    return VerifyResult(ok=True, data={"challenge": challenge})


# ── Twilio ─────────────────────────────────────────────────────────


def verify_twilio_signature(
    auth_token: str,
    url: str,
    params: dict[str, str],
    header_signature: str | None,
) -> VerifyResult:
    """Verify ``X-Twilio-Signature`` using HMAC-SHA1.

    Twilio's signing algorithm concatenates the full URL + sorted params
    and signs with HMAC-SHA1, then base64-encodes the result.
    """
    if not header_signature:
        return VerifyResult(ok=False, reason="missing signature")

    # Build the data string: URL + sorted key-value pairs
    sorted_params = sorted(params.items())
    data_str = url
    for key, value in sorted_params:
        data_str += f"{key}{value}"

    computed_bytes = hmac.new(auth_token.encode(), data_str.encode(), hashlib.sha1).digest()
    expected = base64.b64encode(computed_bytes).decode("ascii")

    if not hmac.compare_digest(expected, header_signature):
        return VerifyResult(ok=False, reason="signature mismatch")

    return VerifyResult(ok=True)


# ── SendGrid ───────────────────────────────────────────────────────


def verify_sendgrid_signature(
    public_key: str,
    payload: bytes,
    timestamp: str | None,
    nonce: str | None,
    signature: str | None,
    max_age: int = 600,
) -> VerifyResult:
    """Verify ``X-Twilio-Email-Event-Webhook-Signature`` (SendGrid).

    Uses Ed25519 if a public key is provided (preferred), otherwise
    falls back to HMAC-SHA256 comparison.

    For constant-time safety we always use ``hmac.compare_digest`` on
    the final strings; Ed25519 verification delegates to
    ``cryptography`` which uses constant-time C code internally.
    """
    if not timestamp or not nonce or not signature:
        return VerifyResult(ok=False, reason="missing verification fields")

    # Timestamp freshness check
    try:
        ts_int = int(timestamp)
    except (ValueError, TypeError):
        return VerifyResult(ok=False, reason="invalid timestamp")
    if max_age > 0 and abs(time.time() - ts_int) > max_age:
        return VerifyResult(ok=False, reason="timestamp expired")

    payload_str = payload.decode("utf-8", errors="replace")
    content_to_verify = f"{timestamp}{payload_str}{nonce}"

    # Try Ed25519 verification if the public key looks like one
    if public_key and len(public_key) == 68 and public_key.startswith("-----BEGIN PUBLIC KEY-----"):
        try:
            from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
            from cryptography.hazmat.primitives.serialization import load_pem_public_key

            key = load_pem_public_key(public_key.encode())
            if isinstance(key, Ed25519PublicKey):
                sig_bytes = base64.b64decode(signature)
                key.verify(sig_bytes, content_to_verify.encode("utf-8"))
                return VerifyResult(ok=True)
        except Exception as exc:
            log.warning(
                "ed25519 verify failed",
                extra={"action": "verify.sendgrid", "error": str(exc)},
            )
            return VerifyResult(ok=False, reason="ed25519 verification failed")

    # Fallback: HMAC-SHA256
    computed = hmac.new(
        public_key.encode(), content_to_verify.encode("utf-8"), hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(computed, signature):
        return VerifyResult(ok=False, reason="signature mismatch")

    return VerifyResult(ok=True)


# ── Svix (generic / 9router) ──────────────────────────────────────


def verify_svix_signature(
    whkey: str,
    body: bytes,
    msg_id: str | None,
    timestamp: str | None,
    signature: str | None,
    tolerance: int = 300,
) -> VerifyResult:
    """Verify Svix-style webhook signatures (``whsec_`` keys).

    Svix uses HMAC-SHA256 with a message format of
    ``"{msg_id}.{timestamp}.{body}"``.
    """
    if not whkey or not msg_id or not timestamp or not signature:
        return VerifyResult(ok=False, reason="missing verification fields")

    # Extract the signing key (strip ``whsec_`` prefix if present)
    signing_key = whkey
    if signing_key.startswith("whsec_"):
        signing_key = signing_key[6:]

    # Timestamp freshness
    try:
        ts_int = int(timestamp)
    except (ValueError, TypeError):
        return VerifyResult(ok=False, reason="invalid timestamp")
    if tolerance > 0 and abs(time.time() - ts_int) > tolerance:
        return VerifyResult(ok=False, reason="timestamp expired")

    body_b64 = base64.b64encode(body).decode("ascii")
    to_sign = f"{msg_id}.{timestamp}.{body_b64}"
    expected = base64.b64encode(
        hmac.new(signing_key.encode(), to_sign.encode(), hashlib.sha256).digest()
    ).decode("ascii")

    if not hmac.compare_digest(expected, signature):
        return VerifyResult(ok=False, reason="signature mismatch")

    return VerifyResult(ok=True)
