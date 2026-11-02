"""QUILL Transcribe -- say it, and it is typed into the program you are using.

A tray-first app for dictating into other programs: an email in Outlook, a form
in a browser, a note in Notepad, a document in Word. It is a product shell over
QUILL's own dictation, not a second speech stack: the controller, the engines,
the models, the words, the punctuation and the checked typing into other
programs are all shared with QUILL, QUILL Lite and Quill Inkwell
(:mod:`quill.core.windows_dictation`, :mod:`quill.ui.windows_dictation_external`).

What it adds is the promise in its spec
(``docs/Product Requirement Documents and Specifications/quilltranscribe.md``):

* the words go into the field you started in, and a focus change pauses rather
  than typing somewhere else (:mod:`quill.apps.transcribe_dictation`);
* the model you choose is the model that runs (:mod:`quill.core.transcribe.models`);
* nothing is registered with Windows until you choose a key
  (:mod:`quill.apps.transcribe_keys`);
* one app owns Dictate Anywhere at a time: while QUILL Transcribe runs, Quill
  Inkwell passes its key on (:mod:`quill.core.dictation_owner`).

The window is small and calm on purpose: what dictation is doing, with which
model and microphone, and what happened last. The tray menu does everything the
window does. Bootstrap mirrors the other family apps: single-instance via
``core.ipc``, an :class:`~quill.ui.app_shell.AppShellFrame` host.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import wx
import wx.adv

from quill.apps.transcribe_ai import TranscribeAiMixin
from quill.apps.transcribe_coach import TranscribeCoachMixin
from quill.apps.transcribe_commands import TranscribeCommandsMixin
from quill.apps.transcribe_dictation import TranscribeDictationMixin
from quill.apps.transcribe_files import TranscribeFilesMixin
from quill.apps.transcribe_keys import TranscribeKeysMixin
from quill.apps.transcribe_menus import build_menu_bar, build_tray_menu, start_stop_label
from quill.apps.transcribe_recent import TranscribeRecentMixin
from quill.apps.transcribe_review import TranscribeReviewMixin
from quill.core.app_version import describe_version
from quill.core.net import configure_ssl_trust
from quill.core.support_message import SUPPORT_EMAIL
from quill.core.transcribe.settings import TranscribeSettings, load_settings, take_from_inkwell
from quill.ui.app_shell import AppShellFrame
from quill.ui.dpi import dip_size

_TITLE = "QUILL Transcribe"
_VERSION = "1.0.0"
_BUILD = 3  # this version's build (docs/release/RELEASE.md, "Build numbers")
_REPO = "Community-Access/quill"
_IPC_SLOT = "transcribe"
_PAD = 10

_WHAT_HAPPENS = (
    "When you start dictation, QUILL Transcribe types what you say into the field "
    "that has the focus, and only that field. If you move somewhere else it pauses "
    "and keeps your words until you resume. It never reads the other program's text."
)


class QuillTranscribeFrame(
    AppShellFrame,
    TranscribeDictationMixin,
    TranscribeKeysMixin,
    TranscribeCommandsMixin,
    TranscribeFilesMixin,
    TranscribeRecentMixin,
    TranscribeReviewMixin,
    TranscribeCoachMixin,
    TranscribeAiMixin,
):
    """The status window for a dictation service that lives in the tray."""

    def __init__(self, *, safe_mode: bool = False) -> None:
        self._init_app_shell(
            _TITLE, safe_mode=safe_mode, size=dip_size(None, 600, 480), app_id="transcribe"
        )
        from quill.core.paths import app_data_dir
        from quill.ui.window_menu import WindowManager

        self._data_dir: Path = app_data_dir()
        self._settings: TranscribeSettings = load_settings(self._data_dir)
        self._last_message = ""
        self._last_refusal = ""
        self._engine_override = ""
        checked = self._settings.inkwell_checked
        brought = take_from_inkwell(self._settings, self._data_dir)
        if not checked:
            self._save()  # once: Inkwell was looked at, so it is never looked at again
        self._windows = WindowManager(wx)
        # The family's AI rows read their keys from APP_KEYMAPS (codex.md Phase 3).
        self._apply_app_keymap("transcribe")
        # F1: QUILL Transcribe's authored purposes lead every answer
        # (GATE-TRANSCRIBE-HELP); the shell activated the generic resolver.
        from quill.core.transcribe import surface_help
        from quill.ui import app_context_help

        app_context_help.activate(surface_help.purpose_for_title)
        self._build_menu_bar()
        self._build_main_panel()
        self._tray_available = self._tray_works()
        if self._tray_available:
            self._ensure_tray_icon(self._build_tray_menu, tooltip=f"{_TITLE} - Ready")
        key_notice = self._start_transcribe_keys()
        if not safe_mode:
            self._own_dictate_anywhere()  # Inkwell defers to us from now on
        self.frame.Bind(wx.EVT_CLOSE, self._on_close)
        self._start_ipc_poll()
        self._refresh_view()
        notices = [sentence for sentence in (brought, key_notice) if sentence]
        kept = self.kept_words_notice()  # words from last time (D-2 review, D-5 rescue)
        if kept:
            notices.append(kept)
        if safe_mode:
            notices.insert(0, "Safe Mode: QUILL Transcribe does not listen or register keys.")
        if not self._tray_available:
            notices.append(
                "Windows has no notification area for QUILL Transcribe, so its window "
                "stays open; minimizing puts it on the taskbar."
            )
        if notices:
            wx.CallLater(1500, self._say_once, " ".join(notices))
        if not safe_mode:
            from quill.platform.windows import launch_heal, transcribe_startup

            launch_heal.heal_in_background(
                self._task_manager, transcribe_startup.heal_launch_at_startup
            )

    @staticmethod
    def _tray_works() -> bool:
        if sys.platform == "darwin":
            return False
        try:
            return bool(wx.adv.TaskBarIcon.IsAvailable())
        except Exception:  # noqa: BLE001 - assume the usual Windows desktop
            return True

    def _say_once(self, sentence: str) -> None:
        self._set_status(sentence)
        self._announce(sentence)

    # -- menus --------------------------------------------------------------------- #

    def _build_menu_bar(self) -> None:
        build_menu_bar(self, title=_TITLE, version=_VERSION)
        self._windows.register(self.frame, _TITLE)

    def _build_tray_menu(self, menu: wx.Menu) -> None:
        build_tray_menu(self, menu)

    # -- the window ------------------------------------------------------------------ #

    def _build_main_panel(self) -> None:
        panel = wx.Panel(self.frame)
        root = wx.BoxSizer(wx.VERTICAL)

        # Alt+E, not Alt+A: Alt+A is the AI menu since codex.md Phase 3, and a
        # label sharing a menu's letter takes it from the menu (GATE-14).
        state_label = wx.StaticText(panel, label="Stat&e:")
        self._state_text = wx.TextCtrl(panel, style=wx.TE_READONLY)
        self._state_text.SetName("Dictation state")
        self._state_text.SetHelpText(
            "What dictation is doing now: Ready, Listening, Hearing you, Paused with "
            "words held, Waiting for you to switch to a field, or Listening for your "
            "wake phrase. The tray icon's name says the same, and Alt+F9 says it with "
            "the program, the model and what is held."
        )
        font = self._state_text.GetFont()
        font.SetPointSize(font.GetPointSize() + 4)
        font.MakeBold()
        self._state_text.SetFont(font)
        root.Add(state_label, 0, wx.LEFT | wx.RIGHT | wx.TOP, _PAD)
        root.Add(self._state_text, 0, wx.EXPAND | wx.ALL, _PAD)

        self._start_button = wx.Button(panel, label="&Start Dictation")
        self._start_button.SetHelpText(
            "Starts dictation in the next field you switch to, or stops it. From "
            "another program, your start and stop key does the same without "
            "coming here."
        )
        self._start_button.Bind(wx.EVT_BUTTON, lambda _e: self.start_or_stop_from_here())
        self._resume_button = wx.Button(panel, label="&Resume")
        self._resume_button.SetHelpText(
            "When dictation is paused: writes the held words into the field you "
            "started in, once you are back there, and carries on."
        )
        self._resume_button.Bind(wx.EVT_BUTTON, lambda _e: self.resume_dictation())
        self._here_button = wx.Button(panel, label="Resume in &This Field")
        self._here_button.SetHelpText(
            "When dictation is paused: makes the field you switch to next the one "
            "dictation writes into, after the same safety checks as a new start."
        )
        self._here_button.Bind(wx.EVT_BUTTON, lambda _e: self.resume_in_this_field())
        self._discard_button = wx.Button(panel, label="Dis&card Held Words")
        self._discard_button.SetHelpText(
            "When dictation is paused: throws away the words held while paused. "
            "Dictation stays paused until you resume or stop."
        )
        self._discard_button.Bind(wx.EVT_BUTTON, lambda _e: self.discard_held_words())
        row = wx.BoxSizer(wx.HORIZONTAL)
        for button in (
            self._start_button,
            self._resume_button,
            self._here_button,
            self._discard_button,
        ):
            row.Add(button, 0, wx.RIGHT, 6)
        root.Add(row, 0, wx.LEFT | wx.RIGHT, _PAD)

        setup_label = wx.StaticText(panel, label="Model and m&icrophone:")
        self._setup_text = wx.TextCtrl(panel, style=wx.TE_MULTILINE | wx.TE_READONLY)
        self._setup_text.SetName("Model and microphone")
        self._setup_text.SetHelpText(
            "The speech model, microphone, dictation profile and start and stop key "
            "dictation uses now. "
            "The model you chose is the one that runs; it never changes on its own."
        )
        root.Add(setup_label, 0, wx.LEFT | wx.RIGHT | wx.TOP, _PAD)
        root.Add(self._setup_text, 1, wx.EXPAND | wx.ALL, _PAD)

        next_label = wx.StaticText(panel, label="What happens &next:")
        self._next_text = wx.TextCtrl(panel, style=wx.TE_MULTILINE | wx.TE_READONLY)
        self._next_text.SetName("What happens next")
        self._next_text.SetHelpText(
            "What starting dictation will do, why it paused or could not start, and "
            "the last thing it said."
        )
        root.Add(next_label, 0, wx.LEFT | wx.RIGHT, _PAD)
        root.Add(self._next_text, 1, wx.EXPAND | wx.ALL, _PAD)

        # The AI line (codex.md decision 19): what Which AI Am I Using says,
        # shortened. No access key: this window has none left that is not
        # already a menu's (GATE-14); Tab reaches it.
        ai_label = wx.StaticText(panel, label="AI:")
        self._ai_text = wx.TextCtrl(panel, style=wx.TE_READONLY)
        self._ai_text.SetName("AI")
        self._ai_text.SetHelpText(
            "Which AI is in use, as Which AI Am I Using says it. Press Enter to open "
            "Choose Your AI."
        )
        self._ai_text.Bind(wx.EVT_KEY_DOWN, self._on_ai_line_key)
        ai_row = wx.BoxSizer(wx.HORIZONTAL)
        ai_row.Add(ai_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6)
        ai_row.Add(self._ai_text, 1)
        root.Add(ai_row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, _PAD)

        choices = wx.BoxSizer(wx.HORIZONTAL)
        model_button = wx.Button(panel, label="Choose Mode&l...")
        model_button.SetHelpText(
            "Choose the speech model: each is marked as running on this computer or "
            "sending your speech over the internet."
        )
        model_button.Bind(wx.EVT_BUTTON, lambda _e: self.choose_model())
        mic_button = wx.Button(panel, label="Choose Micro&phone...")
        mic_button.SetHelpText("Choose the microphone dictation listens on.")
        mic_button.Bind(wx.EVT_BUTTON, lambda _e: self.choose_microphone())
        settings_button = wx.Button(panel, label="Dictation Settin&gs...")
        settings_button.SetHelpText(
            "Language, punctuation, fillers, pauses and what you hear after each "
            "phrase: the same settings as dictation in QUILL."
        )
        settings_button.Bind(wx.EVT_BUTTON, lambda _e: self.edit_dictation_settings())
        for button in (model_button, mic_button, settings_button):
            choices.Add(button, 0, wx.RIGHT, 6)
        root.Add(choices, 0, wx.ALL, _PAD)

        panel.SetSizer(root)
        self._panel = panel

    def _on_ai_line_key(self, event: wx.KeyEvent) -> None:
        if event.GetKeyCode() in (wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER):
            self.cmd_ai_choose()
            return
        event.Skip()

    def _focus_initial_control(self) -> None:
        self._state_text.SetFocus()

    def _setup_sentence(self) -> str:
        from quill.core.transcribe.models import model_name

        chosen = model_name(self.chosen_engine())
        model = f"Model: {chosen}."
        if self._engine_override:
            stand_in = model_name(self._engine_override)
            model = f"Model: {stand_in}, this session only. Yours is {chosen}."
        mic = str(self._settings.dictation.get("windows_dictation_microphone", "") or "")
        microphone = f"Microphone: {mic or 'the Windows default'}."
        key = self.dictation_key() or self._settings.dictation_hotkey
        keys = (
            f"Start and stop key: {key}."
            if key
            else "Start and stop key: none chosen. Use the tray menu, or choose one "
            "in the File menu."
        )
        command = self.command_key() or self._settings.command_hotkey
        commands = (
            f"Command Key: {command}." if command else "Command Key: none chosen; say QUILL first."
        )
        from quill.apps.transcribe_keys import OPTIONAL_KEYS

        chosen_keys = [  # Dictation Status, Resume, Discard (D-6): said only once chosen
            f"{row[1]}: {self.optional_key(field)}."
            for field, row in OPTIONAL_KEYS.items()
            if self.optional_key(field)
        ]
        profile = f"Profile: {self.dictation_profile_name()}" + (
            ", locked." if self.profile_locked() else "."
        )  # D-23
        return "\n".join((model, microphone, profile, keys, commands, *chosen_keys))

    def _next_sentence(self) -> str:
        controller = getattr(self, "_dictation", None)
        if controller is not None and controller.paused_for_target:
            return (
                f"Paused. {controller.hold_reason} {controller.held_count} phrase(s) held. "
                "Go back and choose Resume, choose Resume in This Field, or Discard Held Words."
            )
        lines = [_WHAT_HAPPENS]
        if self._last_message:
            lines.append(f"Last: {self._last_message}")
        return "\n\n".join(lines)

    def _refresh_view(self) -> None:
        """Bring the window, the menus and the tray name up to date."""
        if not hasattr(self, "_state_text"):
            return
        state = self.dictation_state_word()
        for control, value in (
            (self._state_text, state),
            (self._setup_text, self._setup_sentence()),
            (self._next_text, self._next_sentence()),
        ):
            if control.GetValue() != value:
                control.SetValue(value)
        self._refresh_ai_line()
        label = start_stop_label(self)
        if self._start_button.GetLabel() != label:
            self._start_button.SetLabel(label)
        paused = self.dictation_paused()
        for button in (self._resume_button, self._here_button, self._discard_button):
            button.Enable(paused)
        self._refresh_menus(label, paused)
        icon = getattr(self, "_tray_icon", None)
        if icon is not None:
            art = self._app_icon or wx.ArtProvider.GetIcon(
                wx.ART_INFORMATION, wx.ART_OTHER, (16, 16)
            )
            try:
                icon.SetIcon(art, self._tray_name(state))
            except Exception:  # noqa: BLE001 - a tooltip is never worth a failure
                pass

    def _tray_name(self, state: str) -> str:
        """The tray icon's name: the state, and a profile other than Standard (D-23)."""
        profile = self.dictation_profile_name()
        if profile == "Standard":
            return f"{_TITLE} - {state}"
        return f"{_TITLE} - {state} - {profile} profile"

    def _refresh_menus(self, label: str, paused: bool) -> None:
        menu_bar = self.frame.GetMenuBar()
        if menu_bar is None:
            return
        item = menu_bar.FindItemById(int(self._start_item_id))
        if item is not None:
            from quill.core.transcribe.parity import chord

            item.SetItemLabel(f"{label}\t{chord('tools.windows_dictation_toggle')}")
        for item_id in (self._resume_item_id, self._here_item_id, self._discard_item_id):
            found = menu_bar.FindItemById(int(item_id))
            if found is not None:
                found.Enable(paused)

    # -- about --------------------------------------------------------------------- #

    def _show_about(self) -> None:
        from quill.ui.about_notices import show_app_about

        show_app_about(
            self,
            f"{_TITLE} {describe_version(_VERSION, build=_BUILD)}\n\n"
            "Say it, and it is typed into the program you are using, with QUILL's "
            "own speech models. Your speech stays on this computer unless you choose "
            "an internet model.\n\nFree, and part of the QuillVille family."
            f"\n\nSupport: {SUPPORT_EMAIL}",
            app="transcribe",
            app_name=_TITLE,
        )

    def check_for_updates(self) -> None:
        """Help > Check for Updates. The installer's recorded version, not the
        runtime's constant, so a sibling's newer runtime never makes this copy
        look up to date; the release channel decides what may be offered
        (release channels, joined 2026-10-24). Transcribe ships an installer and
        a portable zip, as Cast does: ``match_edition=False``."""
        from quill.ui.updates.shell import installed_app_version

        self.check_for_app_updates(
            repo_slug=_REPO,
            current_version=installed_app_version("transcribe"),
            app_key="transcribe",
            match_edition=False,
        )

    def open_release_channel(self) -> None:
        """Help > Release Channel..."""
        from quill.ui.updates.shell import open_for_shell

        open_for_shell(self, "transcribe")

    # -- a second launch, and Inkwell's requests ------------------------------------- #

    def _start_ipc_poll(self) -> None:
        timer = wx.Timer(self.frame)
        self.frame.Bind(wx.EVT_TIMER, self._on_ipc_timer, timer)
        timer.Start(800)
        self._ipc_timer = timer

    def _on_ipc_timer(self, _event: object) -> None:
        from quill.core.ipc import drain_open_requests

        if drain_open_requests(slot=_IPC_SLOT):
            self._restore_from_tray()
            self.take_dictation_handoff()  # an editor's Dictate in Other Programs
        self._answer_owner_requests()
        self.take_family_dictation()  # what another program saved (D-13): one stat a tick
        controller = getattr(self, "_dictation", None)
        if controller is not None:
            controller.finish_overdue()
        if not self._safe_mode:
            self._keep_wake_standby()  # the wake phrase, as the program in front allows (D-9)

    # -- closing -------------------------------------------------------------------- #

    def _held_count(self) -> int:
        controller = getattr(self, "_dictation", None)
        return int(controller.held_count) if controller is not None else 0

    def _on_close(self, event: wx.CloseEvent) -> None:
        if not event.CanVeto():  # Windows is signing out: no questions
            self._shut_down()
            event.Skip()
            return
        if not self._exit_requested and self._settings.close_to_tray:
            event.Veto()
            if self._tray_available:
                self.frame.Hide()
                self._announce(f"{_TITLE} is still running, in the tray.")
            else:
                self.frame.Iconize(True)
                self._announce(f"{_TITLE} is still running, on the taskbar.")
            return
        if not self._exit_requested and self._held_count():
            event.Veto()
            wx.CallAfter(self._exit_application)  # asks about the held words first
            return
        self._exit_requested = False
        self._shut_down()
        event.Skip()

    def _exit_application(self) -> None:
        held = self._held_count()
        # Held words already on disk (D-5) are not lost: Recent Phrases has them
        # next time, so there is nothing to ask. Only words that could not be
        # kept are worth the question.
        on_disk = bool(getattr(getattr(self, "_dictation", None), "held_on_disk", False))
        if held and not on_disk:
            answer = self._show_message_box(
                f"Dictation is paused with {held} phrase{'s' if held != 1 else ''} that "
                "were never written. Exit and throw them away?",
                f"Exit {_TITLE}",
                wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION,
            )
            if answer != wx.YES:
                return
        super()._exit_application()

    def _shut_down(self) -> None:
        """Microphone closed, keys released, owner lock let go, tray icon gone."""
        timer = getattr(self, "_ipc_timer", None)
        if timer is not None:
            timer.Stop()
        self._close_review()  # an open review's words are kept for next time (D-2)
        self._release_dictate_anywhere()
        self._release_transcribe_keys()
        self._remove_tray_icon()

    # -- first run ------------------------------------------------------------------- #

    def first_run(self) -> None:
        if not self._settings.setup_done and not self._safe_mode:
            self.open_setup()


def main() -> int:
    configure_ssl_trust()  # one certificate check, before any network use
    from quill.core.data_location import apply_pending_at_launch

    apply_pending_at_launch()  # queued Data Folder move, before any data read
    safe_mode = bool(os.environ.get("QUILL_SAFE_MODE")) or "--safe-mode" in sys.argv
    from quill.core.ipc import (
        enqueue_open_request,
        release_primary_instance,
        try_claim_primary_instance,
    )

    if not try_claim_primary_instance(slot=_IPC_SLOT):
        enqueue_open_request(None, slot=_IPC_SLOT)
        return 0

    from quill.core.paths import app_data_dir
    from quill.stability.logging_config import configure_logging

    log_listener = configure_logging(app_data_dir() / "logs")
    from quill.platform.windows.dpi_awareness import enable_dpi_awareness

    enable_dpi_awareness()  # before the first window, or Windows stretches it (#1702)
    app = wx.App()
    frame = QuillTranscribeFrame(safe_mode=safe_mode)
    frame._log_listener = log_listener
    tray = frame._tray_available and frame._settings.setup_done
    if tray and ("--tray" in sys.argv or frame._settings.start_in_tray):
        frame.frame.Hide()
    else:
        frame.frame.Show()
        frame.frame.Raise()
        wx.CallAfter(frame._focus_initial_control)
        wx.CallAfter(frame.first_run)
    if "--dictate-anywhere" in sys.argv:
        wx.CallAfter(frame.take_dictation_handoff)
    if "--dictate-here" in sys.argv:  # Quill Cast's or Quill Radio's Dictate Here (D-16)
        wx.CallAfter(frame.dictate_here_at_launch)
    try:
        app.MainLoop()
    finally:
        release_primary_instance(slot=_IPC_SLOT)
        log_listener.stop()
    return 0


__all__ = ["QuillTranscribeFrame", "main"]

if __name__ == "__main__":
    raise SystemExit(main())
