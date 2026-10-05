"""QUILL's half of Windows Dictation: the hooks and the wiring, and no commands.

Windows Dictation was designed for QUILL Lite, and the family rule is that the
small editor is never ahead of the big one -- a feature nobody has seen in QUILL
is one nobody files a bug about missing. So the commands live in
:mod:`quill.ui.windows_dictation_commands`, QUILL Lite mixes them in directly,
and QUILL reaches the same two commands on the same two chords through this
adapter.

It sits beside QUILL's own Locked Dictation (Ctrl+F9, offline Whisper) rather
than replacing it, and it is mixed in *through* that feature's mixin
(:class:`~quill.ui.main_frame_dictation_hotkeys.DictationHotkeysMixin`), which
is where QUILL's dictation lives. The two answer different needs: Locked
Dictation records a passage and transcribes it with a model you download;
Windows Dictation needs nothing downloaded and writes each phrase as you pause.

Two kinds of method here. The hooks map each question the shared module asks
onto QUILL's own vocabulary. The wiring -- the menu rows, their ids, the command
registration -- is here rather than in ``main_frame_menu.py`` and
``main_frame_commands.py`` because those are at their size budgets (GATE-11),
and a feature's wiring in one small file is easier to read than spread across
four large ones. If this class ever grows a *command* of its own, the capability
has forked.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from quill.ui.windows_dictation_commands import WindowsDictationMixin

__all__ = ["WindowsDictationCommandsMixin"]

_TOGGLE = "tools.windows_dictation_toggle"
_SETTINGS = "tools.windows_dictation_settings"
_RECENT = "tools.windows_dictation_recent"
_WORDS = "tools.windows_dictation_words"
_TRANSCRIBE = "tools.windows_dictation_transcribe_file"
_LANGUAGE = "tools.windows_dictation_switch_language"
_LIVE_TRANSCRIPT = "tools.windows_dictation_live_transcript"
_CONTEXT = "tools.windows_dictation_context"

#: ``(command id, menu label, palette title, handler)``, in menu order. The
#: first is a check item. The labels are QUILL Lite's (commands_dictation.py).
_ROWS: tuple[tuple[str, str, str, str], ...] = (
    (_TOGGLE, "Dictation &On", "Start or Stop Live Dictation", "cmd_toggle_dictation"),
    (_SETTINGS, "Dictation &Settings...", "Live Dictation Settings", "cmd_dictation_settings"),
    (_RECENT, "Recent &Phrases...", "Live Dictation: Recent Phrases", "cmd_dictation_recent"),
    (
        _WORDS,
        "My &Words and Phrases...",
        "Live Dictation: My Words and Phrases",
        "cmd_dictation_words",
    ),
    (
        _TRANSCRIBE,
        "Transcribe a &Recording...",
        "Transcribe a Recording",
        "cmd_transcribe_audio_file",
    ),
    (
        _LANGUAGE,
        "Switch Dictation &Language",
        "Switch Dictation Language",
        "cmd_switch_dictation_language",
    ),
    (
        _LIVE_TRANSCRIPT,
        "Start or Stop Live &Transcript",
        "Start or Stop Live Transcript",
        "cmd_live_transcript",
    ),
    (
        _CONTEXT,
        "Dictation &Context for This Document...",
        "Dictation Context for This Document",
        "cmd_dictation_context",
    ),
)


class WindowsDictationCommandsMixin(WindowsDictationMixin):
    """The shared Windows Dictation commands, wired to QUILL's frame and editor."""

    # -- hooks ------------------------------------------------------------ #

    def _dictation_control(self):  # noqa: ANN201 - the active tab's editor
        return self.editor

    def _dictation_parent(self):  # noqa: ANN201 - QUILL's MainFrame owns a frame
        return self.frame

    def _dictation_settings(self) -> Any:
        return self.settings

    def _dictation_save_settings(self) -> None:
        from quill.core.settings import save_settings

        try:
            save_settings(self.settings)
        except Exception:  # noqa: BLE001 - the choice still holds for this session
            pass

    def _dictation_say(self, text: str) -> None:
        # Forced past the verbosity gate: every sentence dictation speaks is
        # either something the user asked to hear read back or a failure.
        self._announce(text, force=True)

    def _dictation_status(self, text: str) -> None:
        self._set_status_quiet(text)

    def _dictation_cue(self, event: str) -> None:
        self._play_speech_sound(event)

    def _dictation_run_modal(self, dialog: Any, label: str) -> int:
        return int(self._show_modal_dialog(dialog, label))

    def _dictation_top_window(self):  # noqa: ANN201 - QUILL's one top-level frame
        return self.frame

    def _dictation_current_host(self) -> Any:
        return self

    def _dictation_profile_path(self) -> Path:
        """QUILL's own ``dictation.md`` -- the one Locked Dictation reads too, so
        one set of words serves both kinds of dictation."""
        from quill.core.speech.dictation_profile import default_profile_path

        return default_profile_path()

    def _dictation_open_file(self, path: Path) -> None:
        self.open_file(path)

    def _dictation_document_name(self) -> str:
        path = getattr(getattr(self, "document", None), "path", None)
        return Path(path).name if path else "Untitled"

    def _dictation_toggle_chord(self) -> str:
        return str(self._binding_for(_TOGGLE) or "Ctrl+F11")

    def _dictation_say_quietly(self, text: str) -> None:
        # Not forced: the spoken preview is the one thing dictation says that
        # the verbosity settings may hold back.
        self._announce(text)

    def _dictation_task_manager(self) -> Any:
        return self._task_manager

    def _dictation_new_document(self, text: str, name: str) -> None:
        del name  # a new tab is Untitled until it is saved, as in QUILL Lite
        self._power_tools_open_text_in_new_buffer(text, "Transcript opened in a new document.")

    def _dictation_state_changed(self, state: Any) -> None:
        """QUILL's mirror of the state: the menu's check mark, and the status
        bar, quietly (QUILL Lite has a Dictation cell for the same words)."""
        del state
        toggle_id = self._windows_dictation_ids()[0]
        try:
            menu_bar = self.frame.GetMenuBar()
            item = menu_bar.FindItemById(int(toggle_id)) if menu_bar is not None else None
            if item is not None and item.IsCheckable():
                item.Check(self.dictation_active())
        except Exception:  # noqa: BLE001 - a mirror is never worth a session
            pass
        text = self.dictation_state_text()
        if text:
            self._set_status_quiet(text)

    # -- the 2026-10-05 voice commands' answers (windows_dictation_library.py) -- #

    def _dictation_copy_all(self) -> None:
        self.copy_all()

    def _dictation_set_clipboard(self, text: str) -> bool:
        return bool(self._copy_to_clipboard(text))

    def _dictation_show_clips(self) -> None:
        self.open_copy_tray()

    def _dictation_show_snippets(self) -> None:
        self.insert_snippet()

    def _dictation_slot_text(self, number: int) -> str | None:
        tray = self._tray()
        if not 1 <= number <= tray.SLOT_COUNT:
            return None
        return str(tray.slot(number).text or "")

    def _dictation_snippet_names(self) -> list[str]:
        library = getattr(self, "_snippet_library", None)
        snippets = getattr(library, "snippets", []) or []
        return [snippet.name for snippet in snippets if snippet.enabled and snippet.name]

    def _dictation_snippet_text(self, name: str) -> tuple[str, int] | None:
        from quill.ui.windows_dictation_library import snippet_with_blanks

        library = getattr(self, "_snippet_library", None)
        for snippet in getattr(library, "snippets", []) or []:
            if snippet.enabled and snippet.name == name:
                try:
                    return snippet_with_blanks(snippet.body)
                except ValueError:
                    return None
        return None

    def _dictation_abbreviation_entries(self) -> list[Any]:
        library = getattr(self, "_abbreviation_library", None)
        return list(library.enabled_only()) if library is not None else []

    def _dictation_clipboard_text(self) -> str:
        return str(self._get_clipboard_text_for_abbreviation() or "")

    # -- live transcripts and the document (windows_dictation_extras.py) -------- #

    def _dictation_document_path(self) -> Path | None:
        path = getattr(getattr(self, "document", None), "path", None)
        return Path(path) if path else None

    def _dictation_open_transcript_document(self) -> tuple[Any, Any]:
        from quill.core.document import Document

        self._clear_empty_workspace_state()
        self._create_document_tab(Document(text=""), select=True)
        return self, self.editor

    def _dictation_background_edit(self, control: Any) -> None:
        """A live transcript wrote into *control*: keep its tab's document in
        step when it is not the tab in front (the front tab's own text event
        does that for it)."""
        if control is self.editor:
            return
        for tab in getattr(self, "_document_tabs", []):
            if tab.editor is control:
                tab.document.set_text(control.GetValue())
                return

    # -- wiring ----------------------------------------------------------- #

    def _windows_dictation_ids(self) -> tuple[Any, ...]:
        """The menu ids, made once: a menu rebuild must reuse them, because
        the bindings were made against the first set."""
        ids = getattr(self, "_windows_dictation_menu_ids", None)
        if ids is None:
            import wx

            ids = tuple(wx.NewIdRef() for _row in _ROWS)
            self._windows_dictation_menu_ids = ids
        return ids

    def _append_windows_dictation_menu(self, speech_menu: Any) -> None:
        """Tools > Speech > Live Dictation. Its own submenu beside Locked
        Dictation, because the two are different engines and a row that did not
        say which would be a guess."""
        import wx

        from quill.core.i18n import _

        menu = wx.Menu()
        for index, (command_id, label, _title, _handler) in enumerate(_ROWS):
            item_id = self._windows_dictation_ids()[index]
            # The first is a check item, as in QUILL Lite: "am I heard?"
            append = menu.AppendCheckItem if index == 0 else menu.Append
            append(item_id, self._menu_label(_(label), command_id))
        speech_menu.AppendSubMenu(menu, _("L&ive Dictation"))

    def _bind_windows_dictation_menu(self) -> None:
        import wx

        for item_id, (_id, _label, _title, handler) in zip(
            self._windows_dictation_ids(), _ROWS, strict=True
        ):
            self.frame.Bind(wx.EVT_MENU, lambda _e, h=handler: getattr(self, h)(), id=item_id)
        # And follow the frame's activation, for the wake phrase.
        self._dictation_install()

    def _register_windows_dictation_commands(self) -> None:
        for command_id, _label, title, handler in _ROWS:
            self.commands.try_register(
                command_id, title, getattr(self, handler), self._binding_for(command_id)
            )

    def _command_to_menu_id_map(self) -> dict[str, int]:
        mapping: dict[str, int] = super()._command_to_menu_id_map()  # type: ignore[misc]
        for item_id, (command_id, _label, _title, _handler) in zip(
            self._windows_dictation_ids(), _ROWS, strict=True
        ):
            mapping[command_id] = item_id
        return mapping
