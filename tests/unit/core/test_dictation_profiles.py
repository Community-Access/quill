"""Named dictation profiles and format-aware structure (D-23, 2026-10-16).

The shared controller with fakes: an editor-like document that may or may not
hold formatting, and the external document QUILL Transcribe types through.
Nothing here needs a microphone or a real window.
"""

from __future__ import annotations

from dataclasses import replace
from typing import Any

from quill.core.windows_dictation import (
    DictationController,
    DictationPreferences,
    RecognizedPhrase,
    words_from_text,
)
from quill.core.windows_dictation.profiles import (
    FORMAT_REFUSAL,
    HEADING_REFUSAL,
    PLAIN_REFUSAL,
    PROFILES,
    active_profile,
    active_profile_name,
    coerce_profile,
    profile_labels,
)
from quill.core.windows_dictation.reference import commands_reference
from quill.core.windows_dictation.settings_fields import DictationSettings, load_fields
from quill.ui.windows_dictation_external import ExternalDocument


class _Document:
    def __init__(self, formatting: str = "") -> None:
        self.text = ""
        self.sel: tuple[int, int] | None = None
        self._formatting = formatting
        self.styles: list[tuple[str, int, int]] = []

    def unavailable_reason(self, *, writing: bool) -> str:
        return ""

    def context(self) -> tuple[str, str]:
        return self.text, ""

    def selection(self) -> tuple[int, int]:
        return self.sel or (len(self.text), len(self.text))

    def select(self, start: int, end: int) -> None:
        self.sel = (start, end)

    def insert(self, text: str) -> tuple[int, int]:
        start = len(self.text)
        self.text += text
        return start, len(self.text)

    def text_between(self, start: int, end: int) -> str:
        return self.text[start:end]

    def remove(self, start: int, end: int) -> None:
        self.text = self.text[:start] + self.text[end:]

    def replace(self, start: int, end: int, text: str) -> tuple[int, int]:
        self.text = self.text[:start] + text + self.text[end:]
        return start, start + len(text)

    def line_bounds(self) -> tuple[int, int]:
        return 0, len(self.text)

    def last_position(self) -> int:
        return len(self.text)

    def undo(self) -> bool:
        return False

    def formatting(self) -> str:
        return self._formatting

    def apply_style(self, style: str, start: int, end: int) -> str:
        self.styles.append((style, start, end))
        return ""  # the editor's own command said it


class _Feedback:
    def __init__(self, *, saves: bool = True) -> None:
        self.said: list[str] = []
        self.shown: list[str] = []
        self.saved: list[str] = []
        if not saves:
            self.set_dictation_profile = None  # type: ignore[assignment]

    def has_cue(self, moment: Any) -> bool:
        return False

    def cue(self, moment: Any) -> None:
        pass

    def say(self, text: str) -> None:
        self.said.append(text)

    def read_back(self, text: str) -> None:
        pass

    def show(self, text: str) -> None:
        self.shown.append(text)

    def state_changed(self, state: Any) -> None:
        pass

    def show_commands(self) -> None:
        pass

    def set_dictation_profile(self, profile_id: str) -> None:
        self.saved.append(profile_id)


class _Recognizer:
    def start(self, _microphone: str) -> None:
        pass

    def stop(self) -> None:
        pass


def _preferences(profile: str = "standard", **more: Any) -> DictationPreferences:
    settings = DictationSettings(windows_dictation_profile=profile, **more)
    base = DictationPreferences.from_settings(settings)
    return replace(base, phrase_feedback="silent", announce=False, cue_sounds=False)


def _controller(
    profile: str = "standard", document: Any = None, feedback: Any = None, **more: Any
) -> tuple[DictationController, Any, _Feedback]:
    document = document if document is not None else _Document()
    feedback = feedback or _Feedback()
    holder = {"preferences": _preferences(profile, **more)}

    def save(profile_id: str) -> None:
        feedback.saved.append(profile_id)
        holder["preferences"] = _preferences(profile_id, **more)

    if getattr(feedback, "set_dictation_profile", None) is not None:
        feedback.set_dictation_profile = save
    controller = DictationController(
        recognizer=lambda _c, _p: _Recognizer(),
        document=document,
        feedback=feedback,
        preferences=lambda: holder["preferences"],
    )
    controller.start()
    feedback.said.clear()
    return controller, document, feedback


def _say(controller: DictationController, text: str) -> None:
    controller.on_phrase(RecognizedPhrase(words_from_text(text), text=text))


# -- the profiles ----------------------------------------------------------------- #


def test_six_named_profiles_and_standard_which_changes_nothing() -> None:
    ids = [profile.id for profile in PROFILES]
    assert ids == ["standard", "email", "document", "markdown", "chat", "coding", "verbatim"]
    assert coerce_profile("EMAIL") == "email"
    assert coerce_profile("nonsense") == "standard"
    assert len(profile_labels()) == 7
    plain = DictationPreferences.from_settings(DictationSettings())
    assert plain.named_profile == "standard" and plain.structure == "markdown"
    assert plain.pause == "normal" and plain.remove_fillers is False


def test_a_profile_is_an_overlay_on_the_settings() -> None:
    coding = DictationPreferences.from_settings(
        DictationSettings(windows_dictation_profile="coding")
    )
    assert (coding.pause, coding.remove_fillers, coding.auto_punctuation) == (
        "long",
        True,
        False,
    )
    verbatim = DictationPreferences.from_settings(
        DictationSettings(
            windows_dictation_profile="verbatim", windows_dictation_remove_fillers=True
        )
    )
    assert verbatim.remove_fillers is False and verbatim.structure == "plain"
    # What the profile does not override is the person's own setting.
    document = DictationPreferences.from_settings(
        DictationSettings(windows_dictation_profile="document", windows_dictation_pause="short")
    )
    assert document.pause == "short" and document.structure == "formatted"


def test_the_simple_api_names_the_active_profile_for_any_settings_object() -> None:
    assert active_profile_name(DictationSettings(windows_dictation_profile="chat")) == "chat"
    assert active_profile_name(object()) == "standard"
    assert active_profile(DictationSettings(windows_dictation_profile="email")).word_list == "email"


def test_the_settings_load_and_clean_the_profile() -> None:
    fields = load_fields({"windows_dictation_profile": "Markdown"})
    assert fields["windows_dictation_profile"] == "markdown"
    assert fields["windows_dictation_profile_locked"] is False
    assert load_fields({"windows_dictation_profile": 7})["windows_dictation_profile"] == "standard"


# -- headings by structure -------------------------------------------------------- #


def test_markdown_and_standard_type_the_heading_marks() -> None:
    for profile in ("standard", "markdown"):
        controller, document, _ = _controller(profile)
        _say(controller, "heading two plans")
        assert document.text == "## Plans"


def test_document_in_a_formatted_quill_document_uses_the_editors_heading() -> None:
    controller, document, feedback = _controller("document", _Document("rich"))
    _say(controller, "heading two plans")
    assert document.text == "Plans"
    assert document.styles == [("heading_2", 5, 5)]
    assert HEADING_REFUSAL not in feedback.said


def test_document_elsewhere_types_nothing_for_the_heading_and_says_why() -> None:
    controller, document, feedback = _controller("document", _Document(""))
    _say(controller, "heading two plans")
    assert document.text == "Plans"
    assert feedback.said == [HEADING_REFUSAL]


def test_chat_writes_plain_text_silently() -> None:
    controller, document, feedback = _controller("chat")
    document.text = "Hello"
    _say(controller, "heading one news")
    assert document.text == "Hello\nNews"
    assert feedback.said == []


# -- bold and italic --------------------------------------------------------------- #


def test_bold_that_in_markdown_wraps_the_last_phrase_in_one_step() -> None:
    controller, document, feedback = _controller("markdown")
    _say(controller, "very important")
    _say(controller, "bold that")
    assert document.text == "**Very important**"
    assert feedback.said[-1] == "Bold: Very important"
    _say(controller, "scratch that")  # the history follows the change
    assert document.text == ""


def test_italic_that_on_a_selection() -> None:
    controller, document, _ = _controller("coding")
    document.text = "one two three"
    document.sel = (4, 7)
    _say(controller, "italicize that")
    assert document.text == "one *two* three"


def test_bold_that_in_a_formatted_document_uses_the_editors_bold() -> None:
    controller, document, feedback = _controller("email", _Document("markdown"))
    _say(controller, "hello there")
    _say(controller, "bold that")
    assert document.styles == [("bold", 0, len("Hello there"))]
    assert document.text == "Hello there"
    assert feedback.said == []  # the editor's Bold said it


def test_formatting_refused_where_it_cannot_happen() -> None:
    controller, _document, feedback = _controller("document", _Document(""))
    _say(controller, "hello")
    _say(controller, "bold that")
    assert feedback.said[-1] == FORMAT_REFUSAL
    controller, _document, feedback = _controller("chat")
    _say(controller, "hello")
    _say(controller, "italic that")
    assert feedback.said[-1] == PLAIN_REFUSAL


def test_markdown_bold_in_another_program_retypes_the_sessions_own_phrase() -> None:
    typed: list[str] = []
    backspaces: list[int] = []
    document = ExternalDocument(
        problem=lambda: "",
        where=lambda: "field",
        type_text=lambda text, *_: typed.append(text) or True,
        backspace=lambda count: backspaces.append(count) or True,
    )
    controller, _doc, feedback = _controller("markdown", document)
    _say(controller, "ship it")
    _say(controller, "bold that")
    assert backspaces == [len("Ship it")]
    assert typed[-1] == "**Ship it**"
    assert feedback.said[-1] == "Bold: Ship it"


# -- switching ----------------------------------------------------------------------- #


def test_switching_by_voice_saves_and_says_it_once() -> None:
    controller, document, feedback = _controller("standard")
    _say(controller, "email mode")
    assert feedback.saved == ["email"]
    assert feedback.said == ["Email profile."]
    assert document.text == ""  # a command is never typed
    assert controller.mode_text == "Email profile"


def test_lock_profile_stops_voice_switching() -> None:
    controller, _document, feedback = _controller("document", windows_dictation_profile_locked=True)
    _say(controller, "chat mode")
    assert feedback.saved == []
    assert feedback.said == ["Lock Profile is on, so the profile stays Document."]


def test_a_host_that_cannot_keep_a_profile_says_where_to_choose_one() -> None:
    controller, _document, feedback = _controller("standard", feedback=_Feedback(saves=False))
    _say(controller, "markdown profile")
    assert feedback.said == ["Choose a dictation profile in Dictation Settings."]


def test_the_reference_lists_the_new_commands_for_editors_and_transcribe() -> None:
    for external in (False, True):
        text = commands_reference(external=external)
        assert "bold that" in text and "email mode" in text
