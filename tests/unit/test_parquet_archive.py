"""Unit tests for app.storage.parquet_archive (was 18% covered).

pyarrow is NOT installed here, so the json-only fallback branch is genuine.
The pyarrow-present and pyarrow-raises branches are covered by patching the
module-level `_has_pyarrow` / `_to_parquet_bytes` seams, and the cached
`_pyarrow_available` global is reset around every test.
"""

from __future__ import annotations

import json

import pytest

from app.storage import parquet_archive as pa_mod


@pytest.fixture(autouse=True)
def _reset_pyarrow_cache():
    pa_mod._pyarrow_available = None
    yield
    pa_mod._pyarrow_available = None


class _FakeR2:
    """Records every _put and hands out deterministic keys."""

    def __init__(self):
        self.puts: list[dict] = []

    def _date_prefix(self, directory):
        return f"{directory}/2026/09/02"

    def _key(self, prefix, filename):
        return f"{prefix}/{filename}"

    def write_transcript(self, conversation_id, payload, content_type="application/json"):
        key = f"transcripts/2026/09/02/{conversation_id}.json"
        self.puts.append(
            {"key": key, "data": payload, "content_type": content_type, "metadata": None}
        )
        return key

    def _put(self, key, data, content_type=None, metadata=None):
        self.puts.append(
            {"key": key, "data": data, "content_type": content_type, "metadata": metadata}
        )
        return key


@pytest.fixture
def r2():
    return _FakeR2()


def _use_pyarrow(monkeypatch, *, raises=False):
    monkeypatch.setattr(pa_mod, "_has_pyarrow", lambda: True)

    def _to_bytes(records):
        if raises:
            raise RuntimeError("pyarrow serialisation failed")
        return b"PAR1" + json.dumps(records, default=str).encode() + b"PAR1"

    monkeypatch.setattr(pa_mod, "_to_parquet_bytes", _to_bytes)


# --------------------------------------------------------------------------
# _has_pyarrow
# --------------------------------------------------------------------------


def test_has_pyarrow_is_false_when_not_installed():
    assert pa_mod._has_pyarrow() is False


def test_has_pyarrow_result_is_cached():
    assert pa_mod._has_pyarrow() is False
    pa_mod._pyarrow_available = True  # simulate a cached positive
    assert pa_mod._has_pyarrow() is True


# --------------------------------------------------------------------------
# write_transcript
# --------------------------------------------------------------------------


def test_transcript_returns_both_keys(r2):
    out = pa_mod.write_transcript(r2=r2, conversation_id="c1", record={"a": 1})
    assert out["json"].endswith("c1.json")
    assert out["parquet"].endswith("c1.parquet")


def test_transcript_json_payload_is_utf8_unescaped(r2):
    pa_mod.write_transcript(r2=r2, conversation_id="c1", record={"msg": "مرحبا"})
    assert "مرحبا" in r2.puts[0]["data"].decode()


def test_transcript_serialises_non_json_types(r2):
    from datetime import datetime

    pa_mod.write_transcript(r2=r2, conversation_id="c1", record={"at": datetime(2026, 9, 2)})
    assert "2026-09-02" in r2.puts[0]["data"].decode()


def test_transcript_without_pyarrow_writes_json_fallback(r2):
    pa_mod.write_transcript(r2=r2, conversation_id="c1", record={"a": 1})
    second = r2.puts[1]
    assert second["content_type"] == "application/json"
    assert second["metadata"]["type"] == "transcript-fallback"
    assert second["metadata"]["conversation-id"] == "c1"


def test_transcript_with_pyarrow_writes_real_parquet(r2, monkeypatch):
    _use_pyarrow(monkeypatch)
    pa_mod.write_transcript(r2=r2, conversation_id="c1", record={"a": 1})
    second = r2.puts[1]
    assert second["content_type"] == "application/vnd.apache.parquet"
    assert second["data"].startswith(b"PAR1")
    assert second["metadata"]["type"] == "transcript"


def test_transcript_pyarrow_failure_falls_back_to_json(r2, monkeypatch):
    _use_pyarrow(monkeypatch, raises=True)
    out = pa_mod.write_transcript(r2=r2, conversation_id="c1", record={"a": 1})
    second = r2.puts[1]
    assert second["content_type"] == "application/json"
    assert second["metadata"]["type"] == "transcript-fallback"
    assert out["parquet"].endswith(".parquet")


# --------------------------------------------------------------------------
# write_quote_archive
# --------------------------------------------------------------------------


def test_quote_uses_the_quotes_date_prefix(r2):
    out = pa_mod.write_quote_archive(r2=r2, quote_id="q9", record={"total": 100})
    assert out["json"] == "quotes/2026/09/02/q9.json"
    assert out["parquet"] == "quotes/2026/09/02/q9.parquet"


def test_quote_json_metadata(r2):
    pa_mod.write_quote_archive(r2=r2, quote_id="q9", record={"total": 100})
    assert r2.puts[0]["metadata"] == {"quote-id": "q9", "type": "quote"}


def test_quote_without_pyarrow_marks_fallback(r2):
    pa_mod.write_quote_archive(r2=r2, quote_id="q9", record={"total": 100})
    assert r2.puts[1]["metadata"]["type"] == "quote-fallback"


def test_quote_with_pyarrow(r2, monkeypatch):
    _use_pyarrow(monkeypatch)
    pa_mod.write_quote_archive(r2=r2, quote_id="q9", record={"total": 100})
    assert r2.puts[1]["metadata"]["type"] == "quote"
    assert r2.puts[1]["data"].startswith(b"PAR1")


def test_quote_pyarrow_failure_reuses_the_json_payload(r2, monkeypatch):
    _use_pyarrow(monkeypatch, raises=True)
    pa_mod.write_quote_archive(r2=r2, quote_id="q9", record={"total": 100})
    assert r2.puts[1]["metadata"]["type"] == "quote-fallback"
    assert json.loads(r2.puts[1]["data"]) == {"total": 100}


# --------------------------------------------------------------------------
# write_ticket_archive
# --------------------------------------------------------------------------


def test_ticket_accepts_a_list_of_records(r2):
    records = [{"event": "opened"}, {"event": "closed"}]
    out = pa_mod.write_ticket_archive(r2=r2, ticket_id="t1", records=records)
    assert out["json"] == "tickets/2026/09/02/t1.json"
    assert json.loads(r2.puts[0]["data"]) == records


def test_ticket_metadata(r2):
    pa_mod.write_ticket_archive(r2=r2, ticket_id="t1", records=[{"e": 1}])
    assert r2.puts[0]["metadata"] == {"ticket-id": "t1", "type": "ticket"}


def test_ticket_without_pyarrow_marks_fallback(r2):
    pa_mod.write_ticket_archive(r2=r2, ticket_id="t1", records=[{"e": 1}])
    assert r2.puts[1]["metadata"]["type"] == "ticket-fallback"


def test_ticket_with_pyarrow_passes_all_records(r2, monkeypatch):
    captured = {}

    monkeypatch.setattr(pa_mod, "_has_pyarrow", lambda: True)

    def _to_bytes(records):
        captured["n"] = len(records)
        return b"PAR1"

    monkeypatch.setattr(pa_mod, "_to_parquet_bytes", _to_bytes)
    pa_mod.write_ticket_archive(r2=r2, ticket_id="t1", records=[{"e": 1}, {"e": 2}, {"e": 3}])
    assert captured["n"] == 3


def test_ticket_pyarrow_failure_falls_back(r2, monkeypatch):
    _use_pyarrow(monkeypatch, raises=True)
    pa_mod.write_ticket_archive(r2=r2, ticket_id="t1", records=[{"e": 1}])
    assert r2.puts[1]["metadata"]["type"] == "ticket-fallback"


def test_ticket_empty_record_list_still_writes_json(r2):
    out = pa_mod.write_ticket_archive(r2=r2, ticket_id="t1", records=[])
    assert json.loads(r2.puts[0]["data"]) == []
    assert out["parquet"].endswith(".parquet")
