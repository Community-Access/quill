from __future__ import annotations

from pathlib import Path

import pytest

from quill.core.document import Document
from quill.core.sessions import (
    active_index_from_session,
    add_recent_session,
    build_session_payload,
    clear_recent_sessions,
    documents_from_session,
    load_recent_sessions,
    load_session,
    save_session,
    session_title,
)


def test_session_save_and_restore_roundtrip(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("QUILL_DATA_DIR", str(tmp_path))
    docs = [
        Document(text="alpha", path=tmp_path / "alpha.txt", modified=False),
        Document(
            text="beta",
            path=None,
            modified=True,
            encoding="utf-16",
            line_ending="\r\n",
            source_metadata={"source_kind": "text"},
        ),
    ]

    target = tmp_path / "sessions" / "demo.quill-session.json"
    payload = build_session_payload("Demo Session", 1, docs)
    save_session(target, payload, limit=5)

    loaded = load_session(target)
    restored = documents_from_session(loaded)

    assert session_title(loaded, "fallback") == "Demo Session"
    assert active_index_from_session(loaded, len(restored)) == 1
    assert restored[0].text == "alpha"
    assert restored[0].path == (tmp_path / "alpha.txt")
    assert restored[1].text == "beta"
    assert restored[1].encoding == "utf-16"
    assert restored[1].line_ending == "\r\n"
    assert restored[1].source_metadata == {"source_kind": "text"}
    assert load_recent_sessions() == [target.resolve()]


def test_recent_sessions_can_be_cleared(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("QUILL_DATA_DIR", str(tmp_path))
    target = tmp_path / "sessions" / "one.quill-session.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("{}", encoding="utf-8")

    add_recent_session(target, limit=5)
    clear_recent_sessions()

    assert load_recent_sessions() == []


# ---------------------------------------------------------------------------
# #342 -- documents_from_session distinguishes "no documents key" from
# "documents key present and empty".
# ---------------------------------------------------------------------------


def test_documents_from_session_missing_key_returns_untitled_fallback() -> None:
    """When the payload has no 'documents' key, the editor opens with one
    untitled document so the user has something to type into."""
    restored = documents_from_session({"title": "Demo"})

    assert len(restored) == 1
    assert restored[0].text == ""


def test_documents_from_session_empty_list_returns_empty_list() -> None:
    """When the payload has 'documents': [] the editor honours the empty
    session and does not invent a placeholder document (#342)."""
    restored = documents_from_session({"title": "Demo", "documents": []})

    assert restored == []


def test_documents_from_session_non_list_documents_returns_untitled_fallback() -> None:
    """A malformed 'documents' value falls back to a single untitled
    document rather than crashing or returning an empty list."""
    restored = documents_from_session({"title": "Demo", "documents": "not a list"})

    assert len(restored) == 1
    assert restored[0].text == ""


def test_documents_from_session_populated_list_round_trips() -> None:
    """A populated 'documents' list round-trips with each item deserialised."""
    payload = {
        "title": "Demo",
        "documents": [
            {"text": "alpha", "caret_position": 0, "modified": False},
            {"text": "beta", "caret_position": 0, "modified": False},
        ],
    }
    restored = documents_from_session(payload)

    assert [doc.text for doc in restored] == ["alpha", "beta"]


# ---------------------------------------------------------------------------
# #304 -- build_session_payload pairs documents with caret_positions via
# zip(strict=True); the internal assert documents the length invariant and the
# default-zero padding makes the API lenient for callers who only know the
# active document's caret position.
# ---------------------------------------------------------------------------


def test_build_session_payload_pads_short_caret_positions_to_zero() -> None:
    """When the caller passes fewer caret positions than documents, missing
    positions default to 0 rather than dropping trailing documents."""
    docs = [
        Document(text="alpha", path=Path("alpha.txt"), modified=False),
        Document(text="beta", path=Path("beta.txt"), modified=False),
    ]
    payload = build_session_payload("Demo", 0, docs, caret_positions=[7])
    assert len(payload["documents"]) == 2
    positions = [entry["caret_position"] for entry in payload["documents"]]  # type: ignore[index]
    assert positions == [7, 0]


def test_build_session_payload_uses_zip_strict_true() -> None:
    """The internal zip uses strict=True; an exact length match still succeeds."""
    docs = [
        Document(text="alpha", path=Path("alpha.txt"), modified=False),
        Document(text="beta", path=Path("beta.txt"), modified=False),
    ]
    payload = build_session_payload("Demo", 0, docs, caret_positions=[3, 9])
    assert len(payload["documents"]) == 2
    positions = [entry["caret_position"] for entry in payload["documents"]]  # type: ignore[index]
    assert positions == [3, 9]


def test_build_session_payload_invariant_holds_for_default_none() -> None:
    """When caret_positions is omitted, every document gets position 0 and the
    zip(strict=True) call does not raise."""
    docs = [
        Document(text="alpha", path=Path("alpha.txt"), modified=False),
        Document(text="beta", path=Path("beta.txt"), modified=False),
        Document(text="gamma", path=Path("gamma.txt"), modified=False),
    ]
    payload = build_session_payload("Demo", 0, docs)
    assert len(payload["documents"]) == 3
    positions = [entry["caret_position"] for entry in payload["documents"]]  # type: ignore[index]
    assert positions == [0, 0, 0]
