"""Tests for announcement history (§24)."""

from __future__ import annotations

from datetime import datetime

from quill.core.verbosity.engine import VerbosityEngine
from quill.core.verbosity.history import AnnouncementHistory, HistoryEntry
from quill.core.verbosity.profiles import NORMAL
from quill.core.verbosity.verbs import Severity


def _record(history: AnnouncementHistory, verb: str, ctx: dict, profile=NORMAL) -> HistoryEntry:
    rendered = VerbosityEngine(profile=profile).speak(verb, ctx)
    return history.record_announcement(rendered)


def test_record_and_last() -> None:
    history = AnnouncementHistory()
    _record(history, "doc.save", {"name": "a.md"})
    last = history.last()
    assert last is not None
    assert last.verb_id == "doc.save"
    assert last.visual == "Saved a.md"


def test_empty_last_is_none() -> None:
    assert AnnouncementHistory().last() is None


def test_bounded_to_max_entries() -> None:
    history = AnnouncementHistory(max_entries=3)
    for i in range(6):
        _record(history, "nav.next_line", {"line": i})
    assert len(history) == 3
    assert history.last().visual == "Line 5"


def test_redaction_drops_token_values_by_default() -> None:
    history = AnnouncementHistory(redact_text=True)
    rendered = VerbosityEngine().speak("doc.save", {"name": "secret.md"})
    entry = history.record_announcement(rendered, token_values={"name": "secret.md"})
    assert entry.token_values == {}  # redacted
    # The already-user-facing rendered text is still kept.
    assert entry.visual == "Saved secret.md"


def test_no_redaction_keeps_token_values() -> None:
    history = AnnouncementHistory(redact_text=False)
    rendered = VerbosityEngine().speak("doc.save", {"name": "a.md"})
    entry = history.record_announcement(rendered, token_values={"name": "a.md"})
    assert entry.token_values == {"name": "a.md"}


def test_filter_by_verb_profile_and_severity() -> None:
    history = AnnouncementHistory()
    _record(history, "doc.save", {"name": "a"})
    _record(history, "nav.next_line", {"line": 1})
    _record(history, "system.error", {"message": "boom"})
    assert len(history.filter(verb_id="doc.save")) == 1
    assert len(history.filter(severity=Severity.ERROR)) == 1
    assert len(history.filter(profile="Normal")) == 3


def test_filter_warnings_only() -> None:
    history = AnnouncementHistory()
    _record(history, "doc.save", {"name": "a"})
    assert history.filter(warnings_only=True) == ()


def test_clear() -> None:
    history = AnnouncementHistory()
    _record(history, "doc.save", {"name": "a"})
    history.clear()
    assert len(history) == 0


def test_explicit_timestamp() -> None:
    rendered = VerbosityEngine().speak("doc.save", {"name": "a"})
    ts = datetime(2026, 6, 21, 10, 0, 0)
    entry = HistoryEntry.from_announcement(rendered, timestamp=ts)
    assert entry.timestamp == ts
