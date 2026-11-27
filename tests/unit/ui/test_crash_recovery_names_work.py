"""FUX-05: QUILL's crash recovery speaks of the document, one offer per document."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from quill.core.recovery import RecoveryOffer
from quill.ui import main_frame_crash_recovery as crash
from quill.ui.main_frame_crash_recovery import CrashRecoveryMixin


def _offer(tmp_path: Path, text: str, original: str | None) -> RecoveryOffer:
    snap = tmp_path / "k-20261124T000000000000Z-000.snap"
    snap.write_text(text, encoding="utf-8")
    return RecoveryOffer(session_id="s", snapshot=snap, original_path=original)


def test_the_offer_names_the_document_and_how_it_differs(tmp_path: Path) -> None:
    saved = tmp_path / "chapter3.md"
    saved.write_text("It was a dark night.", encoding="utf-8")
    offer = _offer(tmp_path, "It was a dark and stormy night, and then.", str(saved))

    about = crash.describe_crash_offer(offer, offer.snapshot.read_text(encoding="utf-8"))

    assert about.startswith("Unsaved changes to chapter3.md, autosaved today at ")
    assert about.endswith(": 4 words more than the saved file.")
    assert "snapshot" not in about.lower()
    assert str(tmp_path) not in about


def test_the_answers_say_what_happens_to_the_file_and_the_copy(tmp_path: Path) -> None:
    offer = _offer(tmp_path, "x", str(tmp_path / "chapter3.md"))
    said = crash._answers_sentence(offer)
    assert (
        "Restore Document opens this copy as a new, unsaved document; "
        "the saved file is not changed." in said
    )
    assert "Skip Recovery, or Escape, leaves the copy in QUILL's autosave folder" in said


def test_the_recovered_sentence_names_the_document(tmp_path: Path) -> None:
    offer = _offer(tmp_path, "x", str(tmp_path / "chapter3.md"))
    said = crash._recovered_sentence(offer.snapshot, offer.original_path)
    assert said.startswith("Recovered your changes to chapter3.md, as it was today at ")
    assert said.endswith("It is not saved yet. chapter3.md on disk is unchanged.")


def test_an_older_snapshot_with_no_note_still_reads_plainly(tmp_path: Path) -> None:
    offer = _offer(tmp_path, "x", None)
    assert crash._work_name(offer) == "the autosaved document"
    about = crash.describe_crash_offer(offer, "x")
    assert about.startswith("A document whose name was not recorded, autosaved ")


def test_answering_one_offer_puts_up_the_next(tmp_path: Path, wx_call_after) -> None:
    """Before: only the newest document was offered; the rest were never mentioned."""
    import wx

    queued: list[object] = []
    wx_call_after(lambda fn, *a, **k: queued.append(fn))
    first = _offer(tmp_path, "a", "")
    second = RecoveryOffer(session_id="s", snapshot=tmp_path / "other.snap", original_path="")
    editor = SimpleNamespace(SetFocus=lambda: None)
    host = SimpleNamespace(_recovery_offers=[first, second], _wx=wx, editor=editor)
    host._put_up_next_offer = lambda: None

    CrashRecoveryMixin._next_recovery_offer(host, first)

    assert host._recovery_offers == [second]
    assert queued == [host._put_up_next_offer]

    queued.clear()
    CrashRecoveryMixin._next_recovery_offer(host, second)
    assert host._recovery_offers == []
    assert queued == [editor.SetFocus], "after the last offer, focus goes to the editor"


def test_the_next_offer_waits_while_another_window_is_modal() -> None:
    from quill.ui import modal_stack

    later: list[object] = []
    shown: list[str] = []
    fake_wx = SimpleNamespace(CallLater=lambda ms, fn: later.append(fn))
    host = SimpleNamespace(_wx=fake_wx)
    host._offer_crash_recovery = lambda: shown.append("offer")
    host._put_up_next_offer = lambda: CrashRecoveryMixin._put_up_next_offer(host)
    stack = modal_stack.stack_of(host)
    dialog = object()
    stack.push(dialog)

    CrashRecoveryMixin._put_up_next_offer(host)
    assert shown == [] and len(later) == 1

    stack.pop(dialog)
    CrashRecoveryMixin._put_up_next_offer(host)
    assert shown == ["offer"]


def test_the_restore_failure_names_the_work_not_the_exception() -> None:
    source = Path(crash.__file__).read_text(encoding="utf-8")
    assert "Could not restore snapshot: {error}" not in source
    assert "Discard and Continue" not in source, "Skip never discarded anything"


def test_the_comparison_runs_off_the_ui_thread(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The payload worker carries the sentence, so reading the saved file never blocks."""
    monkeypatch.setenv("QUILL_DATA_DIR", str(tmp_path / "data"))
    saved = tmp_path / "notes.txt"
    saved.write_text("one", encoding="utf-8")
    offer = _offer(tmp_path, "one two", str(saved))
    host = SimpleNamespace()
    prepared = CrashRecoveryMixin._prepare_crash_recovery_payload(host, offer)
    assert prepared["about"].startswith("Unsaved changes to notes.txt, autosaved ")
