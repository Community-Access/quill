"""Dictation is the same in QUILL and QUILL Lite: commands, keys, settings, windows.

Family rule 2: the command both products have keeps the chord. Dictation goes
further than most features, because both editors run one implementation
(``quill/ui/windows_dictation_*.py``, ``quill/core/windows_dictation/``): QUILL's
adapter and QUILL Lite's mixin may only answer hooks. This fails on any
difference in either direction, so a dictation command, key or setting added to
one editor and not the other cannot ship.

QUILL's Locked Dictation (F9, Ctrl+F9) is a different engine that records first
and transcribes afterwards; it is QUILL's own and is outside this comparison.
"""

from __future__ import annotations

import dataclasses

from quill.core.keymap import DEFAULT_KEYMAP
from quill.core.lite.commands import COMMANDS
from quill.core.lite.parity import COMMAND_EQUIVALENTS

#: QUILL's ids for live dictation, and the AI tool that tidies dictated text.
_QUILL_DICTATION = {
    command for command in DEFAULT_KEYMAP if command.startswith("tools.windows_dictation_")
} | {"tools.dictation_tidy"}


def _lite_dictation_rows() -> dict[str, str]:
    """``handler -> chord`` for every dictation row in QUILL Lite's command table."""
    rows: dict[str, str] = {}
    for row in COMMANDS:
        menu, _label, chord, handler = row[0], row[1], row[2], row[3]
        if handler and ("Dictation" in menu or "dictation" in handler):
            rows[handler] = chord
    return rows


def test_every_lite_dictation_command_is_in_quill_on_the_same_chord() -> None:
    rows = _lite_dictation_rows()
    assert rows, "QUILL Lite's command table lost its Dictation rows"
    for handler, chord in rows.items():
        quill_id = COMMAND_EQUIVALENTS.get(handler)
        assert quill_id, f"{handler} has no QUILL equivalent"
        assert DEFAULT_KEYMAP.get(quill_id) == chord, (handler, quill_id)


def test_every_quill_dictation_command_is_in_quill_lite() -> None:
    lite_handlers = set(_lite_dictation_rows())
    reached = {COMMAND_EQUIVALENTS[handler] for handler in lite_handlers}
    assert _QUILL_DICTATION <= reached, sorted(_QUILL_DICTATION - reached)


def test_quill_registers_every_dictation_command_it_binds() -> None:
    """The adapter's registration, read from source rather than a running frame."""
    from pathlib import Path

    import quill.ui.main_frame_hosted_ai as hosted
    import quill.ui.main_frame_windows_dictation as adapter

    source = Path(adapter.__file__).read_text(encoding="utf-8")
    source += Path(hosted.__file__).read_text(encoding="utf-8")
    for command in _QUILL_DICTATION:
        short = command.split(".", 1)[1]
        assert command in source or short.upper() in source or f'"{command}"' in source, command


def test_both_editors_have_the_same_dictation_settings_and_defaults() -> None:
    from quill.core.lite.settings import Settings as LiteSettings
    from quill.core.settings import Settings as QuillSettings

    def dictation(cls: type) -> dict[str, object]:
        return {
            field.name: field.default
            for field in dataclasses.fields(cls)
            if field.name.startswith("windows_dictation_")
        }

    assert dictation(QuillSettings) == dictation(LiteSettings)
    assert len(dictation(QuillSettings)) >= 24


def test_the_settings_load_the_same_way_in_both() -> None:
    from quill.core.lite.settings import Settings as LiteSettings
    from quill.core.windows_dictation.settings_fields import load_fields

    lite = LiteSettings()
    lite.windows_dictation_preview = "loud"
    lite.windows_dictation_ai_send = "whenever"
    lite.normalized()
    assert (
        lite.windows_dictation_preview
        == load_fields({"windows_dictation_preview": "loud"})["windows_dictation_preview"]
    )
    assert lite.windows_dictation_ai_send == "pause"


def test_neither_editor_has_a_dictation_command_of_its_own() -> None:
    from quill.apps.lite_window_dictation import DocumentDictationMixin
    from quill.ui.main_frame_windows_dictation import WindowsDictationCommandsMixin
    from quill.ui.windows_dictation_commands import WindowsDictationMixin

    for adapter in (DocumentDictationMixin, WindowsDictationCommandsMixin):
        assert issubclass(adapter, WindowsDictationMixin)
        own = [name for name in vars(adapter) if name.startswith("cmd_")]
        assert own == [], (adapter.__name__, own)


def test_the_dictation_windows_are_shared_modules() -> None:
    """Every dictation window lives in quill/ui, which both editors import."""
    import quill.ui.dictation_lists_dialog as lists
    import quill.ui.dictation_models_dialog as models
    import quill.ui.dictation_more_dialog as more
    import quill.ui.dictation_transcribe_dialog as transcribe
    import quill.ui.dictation_words_dialog as words
    import quill.ui.windows_dictation_dialog as settings

    for module in (lists, models, more, transcribe, words, settings):
        assert module.__name__.startswith("quill.ui."), module.__name__


def test_transcribe_audio_file_is_one_command_on_one_key_in_both() -> None:
    """2026-10-05: a recording into text with dictation's engines. One handler,
    on the shared mixin both editors inherit; one key; one window; one help topic."""
    from quill.apps.lite_window_dictation import DocumentDictationMixin
    from quill.core.help.renderer import load_topics
    from quill.ui.main_frame_windows_dictation import WindowsDictationCommandsMixin
    from quill.ui.windows_dictation_transcribe import DictationTranscribeMixin

    rows = _lite_dictation_rows()
    assert rows["cmd_transcribe_audio_file"] == "Shift+F5"
    quill_id = COMMAND_EQUIVALENTS["cmd_transcribe_audio_file"]
    assert quill_id == "tools.windows_dictation_transcribe_file"
    assert DEFAULT_KEYMAP[quill_id] == "Shift+F5"
    for adapter in (DocumentDictationMixin, WindowsDictationCommandsMixin):
        assert issubclass(adapter, DictationTranscribeMixin)
        assert (
            adapter.cmd_transcribe_audio_file is DictationTranscribeMixin.cmd_transcribe_audio_file
        )
    topic = load_topics()[quill_id]
    assert "Shift+F5" in topic.keystrokes


def test_the_ai_conversation_window_dictates_in_both() -> None:
    """Talking to the AI is wired where the window is opened, which both
    editors share (quill.ui.hosted_ai_chat.open_for)."""
    import inspect

    import quill.ui.hosted_ai_chat as chat

    assert "_talk_to_it(frame, host)" in inspect.getsource(chat.open_for)


def test_the_command_word_and_its_key_are_one_thing_in_all_three() -> None:
    """D-1 (2026-10-15): Speak a Command is F11 in QUILL, QUILL Lite and QUILL
    Transcribe's window, from one handler in the editors; the command word's
    three settings are shared fields; the phrases come from one table."""
    from quill.apps.lite_window_dictation import DocumentDictationMixin
    from quill.core.lite.settings import Settings as LiteSettings
    from quill.core.settings import Settings as QuillSettings
    from quill.core.transcribe.parity import SHARED_COMMANDS
    from quill.ui.main_frame_windows_dictation import WindowsDictationCommandsMixin
    from quill.ui.windows_dictation_command_key import DictationCommandKeyMixin

    assert _lite_dictation_rows()["cmd_dictation_command"] == "F11"
    assert COMMAND_EQUIVALENTS["cmd_dictation_command"] == "tools.windows_dictation_command"
    assert DEFAULT_KEYMAP["tools.windows_dictation_command"] == "F11"
    assert SHARED_COMMANDS["tools.windows_dictation_command"] == "speak_a_command"
    for adapter in (DocumentDictationMixin, WindowsDictationCommandsMixin):
        assert adapter.cmd_dictation_command is DictationCommandKeyMixin.cmd_dictation_command
    names = (
        "windows_dictation_command_prefix",
        "windows_dictation_command_prefix_required",
        "windows_dictation_command_timeout",
    )
    for name in names:
        assert getattr(QuillSettings(), name) == getattr(LiteSettings(), name), name


def test_kept_words_history_and_snippet_prompts_are_one_thing_in_all_three() -> None:
    """D-5, D-8 and D-18 (2026-10-16): one store for words not written and the
    opt-in history, offered by one Recent Phrases on Shift+F11; one place the
    spoken snippet prompts and the read-back commands live (the controller's
    mixins); the history length one shared field, off in every host."""
    import inspect

    from quill.apps.lite_window_dictation import DocumentDictationMixin
    from quill.apps.transcribe_dictation import _Feedback as TranscribeFeedback
    from quill.apps.transcribe_recent import TranscribeRecentMixin
    from quill.core.lite.settings import Settings as LiteSettings
    from quill.core.settings import Settings as QuillSettings
    from quill.core.transcribe.parity import SHARED_COMMANDS
    from quill.core.transcribe.settings import TRANSCRIBE_DICTATION_DEFAULTS
    from quill.core.windows_dictation.controller import DictationController
    from quill.core.windows_dictation.rescue_mixin import RescueMixin
    from quill.core.windows_dictation.snippet_fill import SnippetFillMixin
    from quill.ui.main_frame_windows_dictation import WindowsDictationCommandsMixin
    from quill.ui.windows_dictation_ports import HostFeedback
    from quill.ui.windows_dictation_tools import DictationToolsMixin

    assert issubclass(DictationController, RescueMixin)
    assert issubclass(DictationController, SnippetFillMixin)
    assert _lite_dictation_rows()["cmd_dictation_recent"] == "Shift+F11"
    assert SHARED_COMMANDS["tools.windows_dictation_recent"] == "show_recent_phrases"
    for adapter in (DocumentDictationMixin, WindowsDictationCommandsMixin):
        assert adapter._dictation_kept is DictationToolsMixin._dictation_kept
    for port in (HostFeedback, TranscribeFeedback):
        assert callable(getattr(port, "rescue", None)), port
    for show in (
        DictationToolsMixin.cmd_dictation_recent,
        TranscribeRecentMixin.show_recent_phrases,
    ):
        assert "kept=" in inspect.getsource(show)
    name = "windows_dictation_history_days"
    assert getattr(QuillSettings(), name) == getattr(LiteSettings(), name) == 0
    assert name not in TRANSCRIBE_DICTATION_DEFAULTS
