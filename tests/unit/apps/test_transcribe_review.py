"""Review Dictation in QUILL Transcribe (D-2): nothing typed before Insert, and
Insert types once into the field the session is locked to.

The shared controller over the shared locked external document, typing into a
fake desktop that records what would have been typed; the review window is
built in memory; the AI is a fake. Nothing reaches a real window.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from quill.apps import transcribe_dictation, transcribe_review
from quill.apps.transcribe_commands import TranscribeCommandsMixin
from quill.apps.transcribe_dictation import TranscribeDictationMixin
from quill.apps.transcribe_recent import TranscribeRecentMixin
from quill.apps.transcribe_review import TranscribeReviewMixin
from quill.core.dictation_owner import MicrophoneLock, OwnerLock
from quill.core.transcribe import models
from quill.core.transcribe.settings import TranscribeSettings
from quill.core.windows_dictation import (
    DictationController,
    DictationPreferences,
    RecognizedPhrase,
    words_from_text,
)
from quill.core.windows_dictation.target_lock import LockedTarget
from quill.ui import dictation_review_frame as frame_module
from quill.ui.windows_dictation_external import ExternalDocument
from tests.wx_session import shared_wx_app


class _World:
    def __init__(self) -> None:
        self.field: Any = (101, 1, "edit-1")
        self.typed: list[str] = []
        self.allowed = False
        self.raised: list[int] = []

    def type_text(self, text: str, *_args: Any) -> bool:
        assert self.allowed, f"typed before Insert: {text!r}"
        self.typed.append(f"{self.field[2]}:{text}")
        return True


class _Feedback:
    def __init__(self, host: Any) -> None:
        self.host = host
        self.said: list[str] = []

    def has_cue(self, _moment: Any) -> bool:
        return False

    def cue(self, _moment: Any) -> None:
        pass

    def say(self, text: str) -> None:
        self.said.append(text)

    def read_back(self, _text: str) -> None:
        pass

    def show(self, _text: str) -> None:
        pass

    def state_changed(self, _state: Any) -> None:
        pass

    def show_commands(self) -> None:
        pass

    def review(self) -> Any:
        return self.host._review_desk()


class _Recognizer:
    def start(self, _microphone: str) -> None:
        pass

    def stop(self) -> None:
        pass


class _Ai:
    def __init__(self) -> None:
        self.pending: list[Any] = []

    def reason(self) -> str:
        return ""

    def provider(self) -> str:
        return "OpenAI, with your own key"

    def consented(self) -> bool:
        return True

    def agree(self) -> None:
        pass

    def ask(self, prompt: str, on_done: Any, on_error: Any) -> object:
        self.pending.append(on_done)
        return object()

    def cancel(self, request: Any) -> None:
        pass


class Host(
    TranscribeDictationMixin, TranscribeCommandsMixin, TranscribeRecentMixin, TranscribeReviewMixin
):
    def __init__(self, data_dir: Path) -> None:
        self.frame = None
        self._settings = TranscribeSettings(dictation={"windows_dictation_engine": "windows"})
        self._data_dir = data_dir
        self._safe_mode = False
        self._engine_override = ""
        self.said: list[str] = []
        self.status: list[str] = []
        self.world = _World()
        self.ai = _Ai()
        self._owner_lock = OwnerLock("transcribe", folder=data_dir / "ipc")
        self._microphone = MicrophoneLock("transcribe")
        inner = ExternalDocument(
            problem=lambda: "", where=lambda: self.world.field, type_text=self.world.type_text
        )
        self._dictation = DictationController(
            recognizer=lambda _c, _p: _Recognizer(),
            document=LockedTarget(inner, where=lambda: self.world.field),
            feedback=_Feedback(self),
            preferences=lambda: DictationPreferences(
                phrase_feedback="silent", command_prefix_required=True
            ),
            microphone=self._microphone,
        )

    def _announce(self, text: str, *, force: bool = False, sound: str = "") -> None:
        self.said.append(text)

    def _set_status(self, text: str) -> None:
        self.status.append(text)

    def _review_ai(self) -> Any:
        return self.ai

    def hear(self, text: str) -> None:
        self._dictation.on_phrase(RecognizedPhrase(words_from_text(text)))


@pytest.fixture(scope="module")
def wx_app():
    app = shared_wx_app()
    yield app


@pytest.fixture()
def host(wx_app, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(models, "start_problem", lambda *_a, **_k: "")
    monkeypatch.setattr(
        transcribe_dictation.TranscribeDictationMixin, "_front_is_own_window", lambda _s: False
    )
    monkeypatch.setattr(frame_module, "defer", lambda fn, *args: fn(*args))
    monkeypatch.setattr(frame_module, "take_focus", lambda _frame: None)
    monkeypatch.setattr(transcribe_review, "later", lambda _ms, fn, *args: fn(*args))
    made = Host(tmp_path)
    import quill.platform.windows.foreground as foreground

    monkeypatch.setattr(foreground, "force_foreground_window", made.world.raised.append)
    yield made
    made._close_review()
    made._release_dictate_anywhere()


def test_nothing_is_typed_while_reviewing_and_insert_types_once(host: Host) -> None:
    host.world.allowed = True
    host.start_dictation()
    host.hear("dear sam")
    assert host.world.typed == ["edit-1:Dear sam"]
    host.world.typed.clear()
    host.hear("quill review that")  # backspaced away, and into the review
    frame = host._review_desk().frame
    assert frame is not None and frame.text.GetValue() == "Dear sam"
    host.world.allowed = False  # from here the fake desktop fails the test if typed into
    host.hear("thanks for the notes")
    host.hear("quill make it more formal")
    host.ai.pending.pop()("Dear Sam, thank you for the notes.")
    assert host.world.typed == []
    host.world.allowed = True
    host._dictation.unmute()
    host.hear("quill insert it")
    assert host.world.raised[-1] == 101  # the locked field's window brought back first
    assert host.world.typed == ["edit-1:Dear Sam, thank you for the notes."]
    assert not host._review_desk().is_open()


def test_insert_is_refused_out_loud_when_the_field_has_moved(host: Host) -> None:
    host.world.allowed = True
    host.start_dictation()
    host.hear("hello")
    host.hear("quill review that")
    host.world.field = (202, 2, "edit-9")  # somewhere else is in front at Insert
    host._dictation.unmute()
    host.hear("quill insert it")
    assert host.world.typed == ["edit-1:Hello"]  # only the original phrase, before review
    assert "Nothing was typed" in host.said[-1] and "Recent Phrases" in host.said[-1]
    assert "Hello" in list(host._dictation.recent)


def test_review_dictation_from_the_menu_opens_an_empty_review(host: Host) -> None:
    host.review_dictation()
    frame = host._review_desk().frame
    assert frame is not None and frame.text.GetValue() == ""


def test_an_unfinished_review_is_kept_in_transcribes_own_file(host: Host) -> None:
    host.review_dictation()
    frame = host._review_desk().frame
    assert frame is not None
    frame.text.SetValue("keep me")
    host._close_review()
    assert (host._data_dir / transcribe_review.RESCUE_FILE).exists()
