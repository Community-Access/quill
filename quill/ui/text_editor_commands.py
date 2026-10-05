"""Make <app> My Text Editor, and Open <app> Instead of Notepad -- in both editors.

Two commands for somebody who wants QUILL or QUILL Lite to be the editor Windows
reaches for, and they are deliberately different in how far they go.

**Make <app> My Text Editor** does what Windows allows an app to do and no
more: it tells Windows that the app can open these types, for this account,
and then opens the Settings page where the choice is actually made. Windows
keeps that choice for the user alone, and an app that pretends otherwise is
writing keys Windows ignores. So the dialog says plainly what the app does and
what you choose, before anything happens.

**Open <app> Instead of Notepad** catches the launches no association can: a
program that runs ``notepad.exe`` by name, or a Run box with "notepad" typed in
it. It is machine-wide and needs administrator approval, so it is off until
somebody turns it on, it says so before asking, and its check mark is read back
from the registry rather than remembered -- a switch that shows what it was
*asked* to be, rather than what Windows did, is the worst kind of switch. There
is one hook, so when the *other* family editor already owns it the question
says so by name before replacing it.

This is the one implementation. QUILL Lite reaches it through
:mod:`quill.apps.lite_window_text_editor` and QUILL through
:mod:`quill.ui.main_frame_text_editor`; each supplies its profile and a few
hooks (the dialog parent, where focus returns), and neither has a command of
its own. Since 2026-10-03 the only door in either editor is Preferences >
Windows and your files (:mod:`quill.ui.text_editor_prefs`): no menu row, no
chord. What to write is decided in :mod:`quill.core.windows_editor`; the
registry, the prompt and Settings are reached through
:mod:`quill.platform.windows.editor_registration`, which the tests replace.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import wx

from quill.core import windows_editor as editor
from quill.core.app_command import app_argv
from quill.platform.windows import editor_registration as system
from quill.ui.dialog_contract import show_message_box

__all__ = ["TextEditorCommandsMixin", "launcher"]

_ALIAS_PAGE = "ms-settings:advanced-apps"


def launcher(profile: editor.EditorProfile) -> tuple[list[str], str]:
    """``(argv that starts the app, DefaultIcon string)`` for the running copy."""
    argv = editor.editor_argv(profile, app_argv(profile.module, profile.launcher_name))
    if profile.icon_name:
        icon = Path(argv[0]).with_name(profile.icon_name)
        if icon.is_file():
            return argv, str(icon)
    return argv, f"{argv[0]},0"


def _register_text(name: str, types: str) -> str:
    return (
        "Windows lets an app offer to open your files, but only you can choose "
        "which app opens them.\n\n"
        f"When you press OK, {name} tells Windows, for your account only, that it "
        f"can open {types}. Then it opens Windows' Default apps page for {name}.\n\n"
        f"On that page, choose .txt, pick {name}, and choose Set default. Do the "
        f"same for any other type you want {name} to open. Anything you leave "
        "alone stays with the app that opens it now, and you can change any of them "
        "back on the same page."
    )


def _notepad_on_text(name: str) -> str:
    return (
        f"Turn this on and {name} opens whenever anything on this computer starts "
        "Notepad, including the Run box and other programs.\n\n"
        "It affects every user on this computer, so Windows will ask for "
        "administrator approval.\n\n"
        f"To undo it, come back to Windows and your files in Preferences and "
        f"clear Open {name} instead of Notepad.\n\n"
        f"On Windows 11 there is one more step afterwards, and {name} will show "
        "you where it is.\n\n"
        "Turn it on now?"
    )


def _replacing_text(state: editor.NotepadState) -> str:
    """The sentence that comes first when somebody else already owns the hook."""
    if state.other_owner:
        return (
            f"{state.other_owner} opens in place of Notepad now. Only one program "
            f"can, so turning this on means {state.other_owner} no longer will.\n\n"
        )
    return (
        f"Another program already opens in place of Notepad: {state.other}. "
        "Turning this on replaces it.\n\n"
    )


_NOTEPAD_OFF_TEXT = (
    "Put Notepad back? Notepad will open again for every user on this computer. "
    "Windows will ask for administrator approval."
)
_ALIAS_TEXT = (
    "One more step on Windows 11. The new Notepad can also start through an app "
    "execution alias, which goes around this switch.\n\n"
    "To turn it off, open Settings, then Apps, then Advanced app settings, then "
    "App execution aliases, and turn off Notepad.\n\n"
    "Open Advanced app settings now?"
)


class TextEditorCommandsMixin:
    """The two flows that make an editor the one Windows opens (run from Preferences).

    The host supplies :meth:`_text_editor_profile` and ``_announce``; the other
    hooks have defaults that fit QUILL Lite's document window.
    """

    # -- hooks --------------------------------------------------------------- #

    def _text_editor_profile(self) -> editor.EditorProfile:
        raise NotImplementedError

    def _text_editor_parent(self) -> Any:
        return self

    def _text_editor_refocus(self) -> None:
        self.control.SetFocus()

    def _text_editor_system(self) -> Any:
        return system

    def _text_editor_launcher(self) -> tuple[list[str], str]:
        return launcher(self._text_editor_profile())

    def _text_editor_owner(self) -> Any:
        """Where a question belongs: Preferences while it is open, else the app."""
        owner = getattr(self, "_text_editor_dialog_owner", None)
        return owner if owner is not None else self._text_editor_parent()

    def _text_editor_return(self) -> None:
        """Back to the document -- unless Preferences asked, which keeps focus."""
        if getattr(self, "_text_editor_dialog_owner", None) is None:
            self._text_editor_refocus()

    def _text_editor_ask(self, text: str, caption: str, style: int) -> int:
        return show_message_box(text, caption, style, self._text_editor_owner())

    # -- the commands -------------------------------------------------------- #

    def cmd_make_default_editor(self) -> bool:
        """Register the app for this account, then open Default apps; True when it did."""
        profile = self._text_editor_profile()
        name = profile.app_name
        answer = self._text_editor_ask(
            _register_text(name, profile.types_phrase),
            f"Make {name} My Text Editor",
            wx.OK | wx.CANCEL | wx.ICON_INFORMATION,
        )
        if answer != wx.OK:
            self._text_editor_return()
            return False
        sys_ = self._text_editor_system()
        argv, icon = self._text_editor_launcher()
        # An administrator install already registered this copy for everyone;
        # a second, per-user copy of the same keys is one no uninstaller removes.
        machine = editor.machine_registered(profile, sys_.MachineReader(), argv)
        try:
            if not machine:
                plan = editor.registration_plan(profile, argv, icon)
                editor.write_plan(plan, sys_.CurrentUserWriter())
        except OSError as error:
            self._announce(f"Windows would not record {name} as a text editor: {error}")
            self._text_editor_return()
            return False
        sys_.notify_association_change()
        uri = editor.default_apps_uri(profile, sys_.windows_build(), machine=machine)
        if sys_.open_settings(uri):
            self._announce(
                f"{name} is ready in Default apps. Choose it for .txt and any other type."
            )
        else:
            self._announce(
                f"{name} is registered. Open Settings, then Apps, then Default apps, "
                f"and choose {name} for .txt and any other type."
            )
        return True

    def cmd_toggle_notepad_replacement(self) -> str:
        """Turn the machine-wide Notepad hook on or off, after asking.

        Returns what happened -- ``"cancelled"``, ``"refused"``, ``"declined"``,
        ``"failed"``, ``"on"`` or ``"off"`` -- for Preferences, which has to
        put its checkbox back and say so once when nothing changed. Everything
        but ``"cancelled"`` has already been spoken here.
        """
        profile = self._text_editor_profile()
        name = profile.app_name
        sys_ = self._text_editor_system()
        reader = sys_.MachineReader()
        state = editor.read_notepad_state(profile, reader)
        turning_on = not state.on
        if turning_on:
            text = _notepad_on_text(name)
            if state.other:
                text = _replacing_text(state) + text
            commands = editor.turn_on_commands(reader, self._text_editor_launcher()[0])
        else:
            text = _NOTEPAD_OFF_TEXT
            commands = editor.turn_off_commands(profile, reader)
        answer = self._text_editor_ask(
            text, f"Open {name} Instead of Notepad", wx.YES_NO | wx.ICON_QUESTION
        )
        if answer != wx.YES:
            self._text_editor_return()
            return "cancelled"
        if not editor.safe_for_cmd(commands):
            self._announce(
                f"{name} is in a folder whose name Windows cannot pass along safely, "
                "so nothing was changed. Move it to a folder without & or % in the name."
            )
            return "refused"
        folder = sys_.system32()
        outcome = sys_.run_elevated(
            str(folder / "cmd.exe"), editor.elevated_parameters(commands, str(folder / "reg.exe"))
        )
        now_on = editor.read_notepad_state(profile, reader).on
        if outcome == sys_.DECLINED:
            outcome_word = "declined"
            self._announce("Nothing changed. Windows did not get administrator approval.")
        elif now_on != turning_on:
            outcome_word = "failed"
            self._announce("Windows did not make the change, so nothing is different.")
        elif not now_on:
            outcome_word = "off"
            self._announce(f"Notepad is back. {name} no longer opens in its place.")
        else:
            outcome_word = "on"
            self._announce(f"{name} now opens in place of Notepad.")
            if sys_.windows_build() >= 22000:
                self._offer_alias_settings(f"Open {name} Instead of Notepad")
        self._text_editor_return()
        return outcome_word

    def _offer_alias_settings(self, caption: str) -> None:
        answer = self._text_editor_ask(_ALIAS_TEXT, caption, wx.YES_NO | wx.ICON_INFORMATION)
        sys_ = self._text_editor_system()
        if answer == wx.YES and not sys_.open_settings(_ALIAS_PAGE):
            self._announce("Settings would not open. Press Windows+I and go to Apps.")
