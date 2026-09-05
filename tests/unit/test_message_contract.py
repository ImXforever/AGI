"""Unit tests for the v0.2 inbound message contract."""

from __future__ import annotations

import pytest

from app.core.message_contract import (
    MessageContractError,
    MessageEnvelope,
    normalize_envelope,
)


def _envelope(**overrides: object) -> MessageEnvelope:
    values: dict[str, object] = {
        "channel": "telegram",
        "sender_id": "42",
        "sender_name": "  User  ",
        "text": "  سلام   دنیا  ",
        "external_ref": "msg-1",
    }
    values.update(overrides)
    return MessageEnvelope(**values)  # type: ignore[arg-type]


def test_normalize_envelope_is_deterministic_and_cleans_text() -> None:
    result = normalize_envelope(_envelope())
    assert result.channel == "telegram"
    assert result.sender_id == "42"
    assert result.sender_name == "User"
    assert result.text == "سلام دنیا"
    assert result.external_ref == "msg-1"
    assert result.metadata == {}


@pytest.mark.parametrize("channel", ["", "sms"])
def test_invalid_channel_is_rejected(channel: str) -> None:
    with pytest.raises(MessageContractError, match="unsupported channel"):
        normalize_envelope(_envelope(channel=channel))


def test_channel_whitespace_is_normalized() -> None:
    assert normalize_envelope(_envelope(channel=" telegram ")).channel == "telegram"


def test_empty_identity_is_rejected() -> None:
    with pytest.raises(MessageContractError, match="sender_id"):
        normalize_envelope(_envelope(sender_id="  "))


def test_empty_external_reference_is_rejected() -> None:
    with pytest.raises(MessageContractError, match="external_ref"):
        normalize_envelope(_envelope(external_ref=""))


def test_attachment_only_message_can_have_empty_text() -> None:
    result = normalize_envelope(_envelope(text=""))
    assert result.text == ""


def test_oversized_message_is_rejected() -> None:
    with pytest.raises(MessageContractError, match="100000"):
        normalize_envelope(_envelope(text="x" * 100001))


def test_metadata_is_copied() -> None:
    metadata = {"source": "test"}
    result = normalize_envelope(_envelope(metadata=metadata))
    metadata["mutated"] = True
    assert result.metadata == {"source": "test"}
