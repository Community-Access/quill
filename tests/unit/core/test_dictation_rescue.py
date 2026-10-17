"""Never lose what was said (D-5): words not written, kept until delivered.

The store (``rescue.py``) with a stand-in seal, and once with Windows DPAPI
itself; the controller's half (``rescue_mixin.py``) through the shared
controller and a document that pauses for its field, as QUILL Transcribe's
does; the opt-in history; and the acceptance criteria from the plan:

* killing the process while words are held loses nothing on the next start;
* with history off, nothing remains on disk after delivery;
* no transcript text appears in logs or crash bundles.

Nothing here needs a microphone or touches a real window.
"""

from __future__ import annotations

import logging
import sys
import zipfile
from pathlib import Path
from typing import Any

import pytest

from quill.core.windows_dictation import (
    DictationController,
    DictationPreferences,
    RecognizedPhrase,
    words_from_text,
)
from quill.core.windows_dictation.rescue import (
    DictationKeep,
    coerce_history_days,
    kept_notice,
)
from quill.core.windows_dictation.rescue_mixin import KEPT_SENTENCE, RecentPhrases

SECRET = "Meet Dana at the clinic at nine"


def _seal(text: str) -> str:
    return text[::-1]  # reversible and plainly not the text


class _Clock:
    def __init__(self) -> None:
        self.now = 1_000_000.0

    def __call__(self) -> float:
        return self.now


def _keep(
    folder: Path, clock: _Clock | None = None, app: str = "QUILL Transcribe"
) -> DictationKeep:
    return DictationKeep(folder, app, seal=_seal, unseal=_seal, clock=clock or _Clock())


# -- the store ------------------------------------------------------------------- #


def test_kept_words_survive_a_new_process_and_go_when_dropped(tmp_path: Path) -> None:
    first = _keep(tmp_path)
    entry = first.keep("held", SECRET)
    assert entry
    again = _keep(tmp_path)  # the next start
    [kept] = again.kept()
    assert (kept.kind, kept.text) == ("held", SECRET)
    assert kept.label.startswith("Not written, held while paused, ")
    again.drop(kept.entry_id)
    assert _keep(tmp_path).kept() == []


def test_rewriting_an_entry_keeps_one_file(tmp_path: Path) -> None:
    keep = _keep(tmp_path)
    entry = keep.keep("held", "one")
    assert keep.keep("held", "one two", entry) == entry
    assert [k.text for k in keep.kept()] == ["one two"]
    keep.keep("held", "", entry)  # nothing left: the entry goes
    assert keep.kept() == []


def test_each_app_sees_only_its_own_entries(tmp_path: Path) -> None:
    _keep(tmp_path, app="QUILL").keep("held", "the editor's")
    _keep(tmp_path, app="QUILL Transcribe").keep("held", "the service's")
    assert [k.text for k in _keep(tmp_path, app="QUILL").kept()] == ["the editor's"]


def test_words_that_cannot_be_sealed_are_not_written(tmp_path: Path) -> None:
    def refuse(_text: str) -> str:
        raise RuntimeError("no DPAPI here")

    keep = DictationKeep(tmp_path, "QUILL", seal=refuse, unseal=_seal)
    assert keep.keep("held", SECRET) == ""
    keep.remember(SECRET, 7)
    assert not any(tmp_path.rglob("*.json"))


def test_the_words_on_disk_are_sealed(tmp_path: Path) -> None:
    keep = _keep(tmp_path)
    keep.keep("unwritten", SECRET)
    keep.remember(SECRET, 7)
    for path in tmp_path.rglob("*.json"):
        assert SECRET not in path.read_text(encoding="utf-8")


@pytest.mark.skipif(sys.platform != "win32", reason="Windows DPAPI")
def test_windows_dpapi_seals_them_for_real(tmp_path: Path) -> None:
    keep = DictationKeep(tmp_path, "QUILL")
    keep.keep("held", SECRET)
    keep.remember(SECRET, 1)
    for path in tmp_path.rglob("*.json"):
        assert SECRET not in path.read_text(encoding="utf-8")
    assert [k.text for k in DictationKeep(tmp_path, "QUILL").kept()] == [SECRET]


def test_the_history_is_off_unless_chosen_and_offers_only_earlier_phrases(
    tmp_path: Path,
) -> None:
    clock = _Clock()
    keep = _keep(tmp_path, clock)
    keep.remember("off by default", 0)
    assert not keep.history_path.exists()
    keep.remember("this run", 7)
    assert keep.history(7) == []  # Recent Phrases already lists this run's
    assert [k.text for k in keep.history(7, earlier_only=False)] == ["this run"]
    later = _keep(tmp_path, clock)  # the next start
    [earlier] = later.history(7)
    assert earlier.text == "this run" and earlier.label.startswith("Earlier, ")


def test_the_history_keeps_its_days_and_no_more(tmp_path: Path) -> None:
    clock = _Clock()
    keep = _keep(tmp_path, clock)
    keep.remember("old", 1)
    clock.now += 2 * 86400
    keep.remember("new", 1)
    assert [k.text for k in _keep(tmp_path, clock).history(1)] == ["new"]


def test_forget_and_clear_the_history(tmp_path: Path) -> None:
    clock = _Clock()
    keep = _keep(tmp_path, clock)
    keep.remember("one", 30)
    clock.now += 1
    keep.remember("two", 30)
    later = _keep(tmp_path, clock)
    newest, oldest = later.history(30)
    later.forget(newest)
    assert [k.text for k in later.history(30)] == ["one"]
    assert later.clear_history() is True
    assert not later.history_path.exists() and later.clear_history() is False


def test_turning_the_history_off_deletes_it(tmp_path: Path) -> None:
    keep = _keep(tmp_path)
    keep.remember("kept", 7)
    assert keep.history_path.exists()
    keep.remember("next phrase", 0)
    assert not keep.history_path.exists()


def test_history_days_and_the_start_sentence() -> None:
    assert [coerce_history_days(v) for v in (0, 1, 7, 30, 3, "7", None)] == [0, 1, 7, 30, 0, 7, 0]
    assert kept_notice(0, "x") == ""
    assert kept_notice(1, "Recent Phrases brings it back.") == (
        "1 dictated phrase was not written last time and is kept. Recent Phrases brings it back."
    )
    assert kept_notice(3, "W.").startswith("3 dictated phrases were not written")


def test_recent_phrases_tells_the_history() -> None:
    told: list[str] = []
    recent = RecentPhrases(2, told.append)
    for text in ("a", "b", "c"):
        recent.appendleft(text)
    assert list(recent) == ["c", "b"] and told == ["a", "b", "c"]


# -- the controller ----------------------------------------------------------------- #


class _Field:
    """QUILL Transcribe's locked field, in miniature: it can move away."""

    holds_phrases = True
    pause_advice = ""

    def __init__(self) -> None:
        self.text = ""
        self.reason = ""
        self.fail = False

    def unavailable_reason(self, *, writing: bool) -> str:
        return self.reason if writing else ""

    def context(self) -> tuple[str, str]:
        return self.text, ""

    def selection(self) -> tuple[int, int]:
        return len(self.text), len(self.text)

    def select(self, start: int, end: int) -> None:
        pass

    def insert(self, text: str) -> tuple[int, int]:
        if self.fail:
            raise OSError("Windows stopped taking keys")
        start = len(self.text)
        self.text += text
        return start, len(self.text)

    def text_between(self, start: int, end: int) -> str:
        return self.text[start:end]

    def remove(self, start: int, end: int) -> None:
        self.text = self.text[:start] + self.text[end:]

    def last_position(self) -> int:
        return len(self.text)


class _Feedback:
    def __init__(self, keep: DictationKeep | None) -> None:
        self.keep = keep
        self.said: list[str] = []

    def has_cue(self, _m: Any) -> bool:
        return False

    def cue(self, _m: Any) -> None:
        pass

    def say(self, text: str) -> None:
        self.said.append(text)

    def read_back(self, _t: str) -> None:
        pass

    def show(self, _t: str) -> None:
        pass

    def state_changed(self, _s: Any) -> None:
        pass

    def show_commands(self) -> None:
        pass

    def rescue(self) -> DictationKeep | None:
        return self.keep


class _Recognizer:
    def start(self, _microphone: str) -> None:
        pass

    def stop(self) -> None:
        pass


def _session(
    keep: DictationKeep | None, history_days: int = 0
) -> tuple[DictationController, _Field, _Feedback]:
    field = _Field()
    feedback = _Feedback(keep)
    settings = DictationPreferences(
        phrase_feedback="silent", announce=False, history_days=history_days
    )
    controller = DictationController(
        recognizer=lambda _c, _p: _Recognizer(),
        document=field,
        feedback=feedback,
        preferences=lambda: settings,
    )
    controller.start()
    return controller, field, feedback


def _hear(controller: DictationController, text: str) -> None:
    controller.on_phrase(RecognizedPhrase(words_from_text(text)))


def test_killing_the_process_while_words_are_held_loses_nothing(tmp_path: Path) -> None:
    controller, field, _feedback = _session(_keep(tmp_path))
    field.reason = "The focus moved to another program."
    _hear(controller, "dear sam")
    _hear(controller, "the meeting moved")
    assert controller.held_count == 2
    # No stop, no shut-down: the process is simply gone. The next start finds them.
    [kept] = _keep(tmp_path).kept()
    assert kept.kind == "held"
    assert kept.text == "Dear sam the meeting moved"


def test_resume_delivers_them_and_lets_go(tmp_path: Path) -> None:
    controller, field, _feedback = _session(_keep(tmp_path))
    field.reason = "The focus moved."
    _hear(controller, "hello")
    field.reason = ""
    assert controller.resume_held()
    assert field.text == "Hello"
    assert _keep(tmp_path).kept() == []


def test_discarding_held_words_deletes_them(tmp_path: Path) -> None:
    controller, field, _feedback = _session(_keep(tmp_path))
    field.reason = "The focus moved."
    _hear(controller, "hello")
    controller.discard_held()
    assert _keep(tmp_path).kept() == []


def test_scratch_while_paused_rewrites_what_is_kept(tmp_path: Path) -> None:
    controller, field, _feedback = _session(_keep(tmp_path))
    field.reason = "The focus moved."
    _hear(controller, "keep this")
    _hear(controller, "not this")
    _hear(controller, "scratch that")
    assert [k.text for k in _keep(tmp_path).kept()] == ["Keep this"]


def test_stopping_with_words_held_keeps_them_and_says_where(tmp_path: Path) -> None:
    controller, field, feedback = _session(_keep(tmp_path))
    field.reason = "The focus moved."
    _hear(controller, "hello")
    controller.stop()
    assert "1 phrase held while paused was not written." in feedback.said[-1]
    assert KEPT_SENTENCE in feedback.said[-1]
    assert [k.text for k in _keep(tmp_path).kept()] == ["Hello"]
    # A second pause in the same run is an entry of its own.
    controller.start()
    _hear(controller, "again")
    assert len(_keep(tmp_path).kept()) == 2


def test_a_phrase_that_could_not_be_written_is_kept(tmp_path: Path) -> None:
    controller, field, _feedback = _session(_keep(tmp_path))
    field.fail = True
    _hear(controller, "this one matters")
    assert not controller.active  # the session ended, as it always did
    [kept] = _keep(tmp_path).kept()
    assert (kept.kind, kept.text) == ("unwritten", "This one matters")


def test_with_history_off_nothing_remains_on_disk_after_delivery(tmp_path: Path) -> None:
    controller, field, _feedback = _session(_keep(tmp_path), history_days=0)
    _hear(controller, "an ordinary phrase")
    field.reason = "The focus moved."
    _hear(controller, "held for a moment")
    field.reason = ""
    controller.resume_held()
    controller.stop()
    assert field.text.endswith("held for a moment")
    assert [p for p in tmp_path.rglob("*") if p.is_file()] == []


def test_with_history_on_written_phrases_are_kept_sealed(tmp_path: Path) -> None:
    controller, _field, _feedback = _session(_keep(tmp_path), history_days=7)
    _hear(controller, "an ordinary phrase")
    controller.stop()
    [earlier] = _keep(tmp_path).history(7)
    assert earlier.text == "An ordinary phrase"


def test_a_host_without_a_store_keeps_words_in_memory_only(tmp_path: Path) -> None:
    controller, field, _feedback = _session(None)
    field.reason = "The focus moved."
    _hear(controller, "hello")
    assert controller.held_count == 1
    assert [p for p in tmp_path.rglob("*") if p.is_file()] == []


def test_no_transcript_text_reaches_the_log_or_a_crash_bundle(
    tmp_path: Path, caplog: pytest.LogCaptureFixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    from quill.stability.crash_report import build_diagnostic_bundle

    caplog.set_level(logging.DEBUG)
    monkeypatch.delenv("QUILL_DICTATION_TRACE", raising=False)
    keep = _keep(tmp_path / "data")
    controller, field, _feedback = _session(keep, history_days=7)
    _hear(controller, SECRET)
    field.reason = "The focus moved."
    _hear(controller, SECRET)
    field.reason, field.fail = "", True
    controller.resume_held()
    assert SECRET.lower() not in caplog.text.lower()
    log = tmp_path / "quill.log"
    log.write_text(caplog.text, encoding="utf-8")
    bundle = build_diagnostic_bundle(logs_path=log, output_path=tmp_path / "bundle.zip")
    with zipfile.ZipFile(bundle) as archive:
        for name in archive.namelist():
            assert SECRET.lower() not in archive.read(name).decode("utf-8", "replace").lower()
