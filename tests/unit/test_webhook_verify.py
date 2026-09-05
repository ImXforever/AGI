"""Unit tests for inbound webhook signature verification.

This module is the front door of the system: everything that arrives from
Telegram, Meta, Twilio, SendGrid or Svix is authenticated here. Each verifier
is tested for the happy path *and* for the ways an attacker would probe it —
missing header, wrong secret, malformed prefix, stale timestamp, tampered body.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import time

import pytest

from app.gateway import verify

pytestmark = pytest.mark.unit

SECRET = "super-secret-token-value-0123456789"
BODY = b'{"event":"message","id":1}'


# ---------------------------------------------------------------------------
# Telegram
# ---------------------------------------------------------------------------


class TestTelegram:
    def test_matching_token_is_accepted(self):
        assert verify.verify_telegram(SECRET, SECRET).ok is True

    def test_missing_header_is_rejected(self):
        result = verify.verify_telegram(SECRET, None)
        assert result.ok is False and result.reason == "missing header"

    def test_empty_header_is_rejected(self):
        assert verify.verify_telegram(SECRET, "").ok is False

    def test_wrong_token_is_rejected(self):
        result = verify.verify_telegram(SECRET, "not-the-token")
        assert result.ok is False and result.reason == "token mismatch"

    def test_fresh_timestamp_is_accepted(self):
        assert verify.verify_telegram(SECRET, SECRET, timestamp=int(time.time())).ok is True

    def test_stale_timestamp_is_rejected(self):
        result = verify.verify_telegram(
            SECRET, SECRET, timestamp=int(time.time()) - 10_000, max_age=300
        )
        assert result.ok is False and result.reason == "timestamp expired"

    def test_replay_window_can_be_disabled(self):
        assert verify.verify_telegram(SECRET, SECRET, timestamp=0, max_age=0).ok is True


# ---------------------------------------------------------------------------
# Meta / WhatsApp Cloud
# ---------------------------------------------------------------------------


def _meta_sig(body: bytes, algo: str = "256") -> str:
    digest = hashlib.sha256 if algo == "256" else hashlib.sha1
    return f"sha{algo}=" + hmac.new(SECRET.encode(), body, digest).hexdigest()


class TestMetaSignature:
    def test_valid_sha256_signature(self):
        assert verify.verify_meta_signature(SECRET, BODY, None, _meta_sig(BODY)).ok is True

    def test_valid_legacy_sha1_signature(self):
        assert verify.verify_meta_signature(SECRET, BODY, _meta_sig(BODY, "1")).ok is True

    def test_sha256_is_preferred_when_both_are_present(self):
        result = verify.verify_meta_signature(SECRET, BODY, "sha1=deadbeef", _meta_sig(BODY))
        assert result.ok is True

    def test_no_signature_header_is_rejected(self):
        result = verify.verify_meta_signature(SECRET, BODY, None, None)
        assert result.ok is False and result.reason == "no signature header"

    def test_malformed_header_is_rejected(self):
        result = verify.verify_meta_signature(SECRET, BODY, "garbage")
        assert result.ok is False and result.reason == "malformed signature"

    def test_tampered_body_is_rejected(self):
        sig = _meta_sig(BODY)
        result = verify.verify_meta_signature(SECRET, b'{"event":"tampered"}', None, sig)
        assert result.ok is False and result.reason == "signature mismatch"

    def test_wrong_secret_is_rejected(self):
        assert verify.verify_meta_signature("other-secret", BODY, None, _meta_sig(BODY)).ok is False


class TestMetaHandshake:
    def test_valid_handshake_returns_the_challenge(self):
        result = verify.verify_meta_handshake(SECRET, "subscribe", "chal-123", SECRET)
        assert result.ok is True
        assert result.data == {"challenge": "chal-123"}

    def test_wrong_mode_is_rejected(self):
        assert verify.verify_meta_handshake(SECRET, "unsubscribe", "c", SECRET).ok is False

    def test_missing_token_is_rejected(self):
        assert verify.verify_meta_handshake(SECRET, "subscribe", "c", None).ok is False

    def test_wrong_token_is_rejected(self):
        result = verify.verify_meta_handshake(SECRET, "subscribe", "c", "wrong")
        assert result.ok is False and result.reason == "verify token mismatch"

    def test_missing_challenge_is_rejected(self):
        result = verify.verify_meta_handshake(SECRET, "subscribe", None, SECRET)
        assert result.ok is False and result.reason == "missing challenge"


# ---------------------------------------------------------------------------
# Twilio
# ---------------------------------------------------------------------------


def _twilio_sig(url: str, params: dict[str, str]) -> str:
    data = url + "".join(f"{k}{v}" for k, v in sorted(params.items()))
    return base64.b64encode(
        hmac.new(SECRET.encode(), data.encode(), hashlib.sha1).digest()
    ).decode()


class TestTwilio:
    URL = "https://example.com/webhooks/twilio"
    PARAMS = {"From": "+123", "Body": "hello", "To": "+456"}

    def test_valid_signature(self):
        sig = _twilio_sig(self.URL, self.PARAMS)
        assert verify.verify_twilio_signature(SECRET, self.URL, self.PARAMS, sig).ok is True

    def test_missing_signature_is_rejected(self):
        result = verify.verify_twilio_signature(SECRET, self.URL, self.PARAMS, None)
        assert result.ok is False and result.reason == "missing signature"

    def test_param_order_does_not_matter(self):
        """Twilio sorts the params, so a reordered dict must still verify."""
        sig = _twilio_sig(self.URL, self.PARAMS)
        reordered = dict(reversed(list(self.PARAMS.items())))
        assert verify.verify_twilio_signature(SECRET, self.URL, reordered, sig).ok is True

    def test_tampered_param_is_rejected(self):
        sig = _twilio_sig(self.URL, self.PARAMS)
        tampered = dict(self.PARAMS, Body="goodbye")
        assert verify.verify_twilio_signature(SECRET, self.URL, tampered, sig).ok is False

    def test_different_url_is_rejected(self):
        sig = _twilio_sig(self.URL, self.PARAMS)
        result = verify.verify_twilio_signature(SECRET, "https://evil.com/hook", self.PARAMS, sig)
        assert result.ok is False

    def test_empty_params_still_verify(self):
        sig = _twilio_sig(self.URL, {})
        assert verify.verify_twilio_signature(SECRET, self.URL, {}, sig).ok is True


# ---------------------------------------------------------------------------
# SendGrid
# ---------------------------------------------------------------------------


class TestSendGrid:
    def _sig(self, ts: str, nonce: str, payload: bytes = BODY) -> str:
        content = f"{ts}{payload.decode()}{nonce}"
        return hmac.new(SECRET.encode(), content.encode(), hashlib.sha256).hexdigest()

    def test_valid_hmac_fallback_signature(self):
        ts = str(int(time.time()))
        assert (
            verify.verify_sendgrid_signature(SECRET, BODY, ts, "n1", self._sig(ts, "n1")).ok is True
        )

    @pytest.mark.parametrize("missing", ["ts", "nonce", "sig"])
    def test_missing_fields_are_rejected(self, missing: str):
        ts = str(int(time.time()))
        args = {"timestamp": ts, "nonce": "n1", "signature": self._sig(ts, "n1")}
        args[{"ts": "timestamp", "nonce": "nonce", "sig": "signature"}[missing]] = None
        result = verify.verify_sendgrid_signature(SECRET, BODY, **args)
        assert result.ok is False and result.reason == "missing verification fields"

    def test_non_numeric_timestamp_is_rejected(self):
        result = verify.verify_sendgrid_signature(SECRET, BODY, "not-a-number", "n", "s")
        assert result.ok is False and result.reason == "invalid timestamp"

    def test_stale_timestamp_is_rejected(self):
        old = str(int(time.time()) - 100_000)
        result = verify.verify_sendgrid_signature(SECRET, BODY, old, "n1", self._sig(old, "n1"))
        assert result.ok is False and result.reason == "timestamp expired"

    def test_tampered_payload_is_rejected(self):
        ts = str(int(time.time()))
        sig = self._sig(ts, "n1")
        assert verify.verify_sendgrid_signature(SECRET, b"tampered", ts, "n1", sig).ok is False

    def test_nonce_is_part_of_the_signature(self):
        ts = str(int(time.time()))
        sig = self._sig(ts, "n1")
        assert verify.verify_sendgrid_signature(SECRET, BODY, ts, "n2", sig).ok is False


# ---------------------------------------------------------------------------
# Svix
# ---------------------------------------------------------------------------


class TestSvix:
    KEY = "whsec_" + SECRET

    def _sig(self, msg_id: str, ts: str, body: bytes = BODY) -> str:
        to_sign = f"{msg_id}.{ts}.{base64.b64encode(body).decode()}"
        return base64.b64encode(
            hmac.new(SECRET.encode(), to_sign.encode(), hashlib.sha256).digest()
        ).decode()

    def test_valid_signature_with_whsec_prefix(self):
        ts = str(int(time.time()))
        assert (
            verify.verify_svix_signature(self.KEY, BODY, "msg_1", ts, self._sig("msg_1", ts)).ok
            is True
        )

    def test_key_without_the_prefix_also_works(self):
        ts = str(int(time.time()))
        assert (
            verify.verify_svix_signature(SECRET, BODY, "msg_1", ts, self._sig("msg_1", ts)).ok
            is True
        )

    @pytest.mark.parametrize("field", ["whkey", "msg_id", "timestamp", "signature"])
    def test_missing_fields_are_rejected(self, field: str):
        ts = str(int(time.time()))
        args = {
            "whkey": self.KEY,
            "body": BODY,
            "msg_id": "msg_1",
            "timestamp": ts,
            "signature": self._sig("msg_1", ts),
        }
        args[field] = None
        result = verify.verify_svix_signature(**args)
        assert result.ok is False and result.reason == "missing verification fields"

    def test_non_numeric_timestamp_is_rejected(self):
        result = verify.verify_svix_signature(self.KEY, BODY, "m", "abc", "s")
        assert result.ok is False and result.reason == "invalid timestamp"

    def test_stale_timestamp_is_rejected(self):
        old = str(int(time.time()) - 100_000)
        result = verify.verify_svix_signature(self.KEY, BODY, "msg_1", old, self._sig("msg_1", old))
        assert result.ok is False and result.reason == "timestamp expired"

    def test_message_id_is_bound_into_the_signature(self):
        """Re-using a valid signature under a different message id must fail."""
        ts = str(int(time.time()))
        sig = self._sig("msg_1", ts)
        assert verify.verify_svix_signature(self.KEY, BODY, "msg_2", ts, sig).ok is False

    def test_tampered_body_is_rejected(self):
        ts = str(int(time.time()))
        sig = self._sig("msg_1", ts)
        assert verify.verify_svix_signature(self.KEY, b"tampered", "msg_1", ts, sig).ok is False


class TestVerifyResult:
    def test_result_is_immutable(self):
        result = verify.VerifyResult(ok=True)
        with pytest.raises(Exception):
            result.ok = False  # type: ignore[misc]

    def test_defaults(self):
        result = verify.VerifyResult(ok=True)
        assert result.reason == "" and result.data is None
