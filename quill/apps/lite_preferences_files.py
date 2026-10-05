"""Preferences: when another program changes the file you are editing.

QUILL's four settings from Settings > General, under QUILL's names and labels,
for the watcher QUILL Lite gained on 2026-10-04 (``lite_window_watch.py``):
whether to watch, whether to reload by itself when you have changed nothing,
whether to ask when you have, and how long to wait. Plus the way back from the
question's "do not ask me again" box, which QUILL reaches from its File menu
and QUILL Lite reaches here.

Its own module because ``lite_preferences.py`` sits at the line cap (GATE-11).
Built into that window beside "Windows and your files", the other group about
your files. Access keys: A and L are the only two letters these labels contain
that nothing else in Preferences claims (GATE-14); the rest go without, and Tab
reaches them.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import wx

from quill.core.external_change import forget_answers, forget_answers_sentence
from quill.ui.dialog_contract import set_accessible_name

__all__ = ["GROUP_TITLE", "FileChangePrefs"]

GROUP_TITLE = "When another program changes the file"


class FileChangePrefs:
    """The group, built into QUILL Lite's Preferences; :meth:`apply` on OK."""

    def __init__(
        self,
        dialog: Any,
        sizer: Any,
        settings: Any,
        *,
        announce: Callable[[str], None] | None = None,
        pad: int = 8,
    ) -> None:
        self._settings = settings
        self._announce = announce or (lambda _message: None)
        self._forget = False
        flags = wx.LEFT | wx.RIGHT | wx.TOP
        self.heading = wx.StaticText(dialog, label=GROUP_TITLE)
        self.heading.SetHelpText(
            "What QUILL Lite does when another program writes to or deletes a file "
            "you have open. QUILL has the same settings."
        )
        sizer.Add(self.heading, 0, flags, pad)

        self.watch = wx.CheckBox(dialog, label="W&atch the open file for external changes")
        self.watch.SetHelpText(
            "On: QUILL Lite notices when another program changes or deletes a file you "
            "have open, and tells you or asks you. Off: it notices only when you save."
        )
        self.watch.SetValue(bool(getattr(settings, "external_change_watch_enabled", True)))
        sizer.Add(self.watch, 0, flags, pad)

        self.auto_reload = wx.CheckBox(
            dialog, label="Re&load automatically when you have no unsaved edits"
        )
        self.auto_reload.SetHelpText(
            "On: if you have not changed the document since it was opened or saved, "
            "a changed file is read again by itself, the cursor stays on its line, and "
            "QUILL Lite says so once. Off: you are asked first. An answer you asked to "
            "have remembered for that kind of file still comes first."
        )
        self.auto_reload.SetValue(
            bool(getattr(settings, "external_change_auto_reload_when_clean", False))
        )
        sizer.Add(self.auto_reload, 0, flags, pad)

        self.prompt = wx.CheckBox(dialog, label="Ask before discarding unsaved edits on a conflict")
        self.prompt.SetHelpText(
            "On: when the file changes while you have unsaved edits, you choose Reload "
            "from Disk, Keep Mine or Save As, and a deleted file is reported once. Off: "
            "QUILL Lite says nothing in those cases and leaves your text alone."
        )
        self.prompt.SetValue(bool(getattr(settings, "external_change_prompt_on_conflict", True)))
        sizer.Add(self.prompt, 0, flags, pad)

        self.debounce_label = wx.StaticText(
            dialog, label="External-change debounce (milliseconds):"
        )
        self.debounce = wx.SpinCtrl(
            dialog,
            min=0,
            max=10000,
            initial=int(getattr(settings, "external_change_debounce_ms", 750)),
        )
        set_accessible_name(self.debounce, "External-change debounce, milliseconds")
        self.debounce.SetHelpText(
            "How often QUILL Lite looks at your open files, so a program that writes a "
            "file in several steps is dealt with once. The default is 750."
        )
        sizer.Add(self.debounce_label, 0, flags, pad)
        sizer.Add(self.debounce, 0, wx.LEFT | wx.RIGHT, pad)

        self.forget_button = wx.Button(dialog, label="Forget remembered file-change answers")
        self.forget_button.SetHelpText(
            "Takes back every Do not ask me again answer, so QUILL Lite asks again "
            "about every kind of file. Happens when you press OK."
        )
        self.forget_button.Bind(wx.EVT_BUTTON, lambda _event: self.forget())
        sizer.Add(self.forget_button, 0, wx.ALL, pad)

    def remembered_count(self) -> int:
        settings = self._settings
        return len(getattr(settings, "external_change_always_reload", []) or []) + len(
            getattr(settings, "external_change_always_keep", []) or []
        )

    def forget(self) -> None:
        """Mark the remembered answers to be forgotten on OK, and say how many."""
        count = self.remembered_count()
        if not count:
            self._announce(forget_answers_sentence(0, "QUILL Lite"))
            return
        self._forget = True
        self._announce(
            f"{count} remembered file-format answer{'s' if count != 1 else ''} "
            "will be forgotten when you press OK."
        )

    def apply(self) -> bool:
        """Write the controls back; ``True`` when anything changed."""
        settings = self._settings
        before = (
            getattr(settings, "external_change_watch_enabled", True),
            getattr(settings, "external_change_auto_reload_when_clean", False),
            getattr(settings, "external_change_prompt_on_conflict", True),
            getattr(settings, "external_change_debounce_ms", 750),
        )
        settings.external_change_watch_enabled = bool(self.watch.GetValue())
        settings.external_change_auto_reload_when_clean = bool(self.auto_reload.GetValue())
        settings.external_change_prompt_on_conflict = bool(self.prompt.GetValue())
        settings.external_change_debounce_ms = int(self.debounce.GetValue())
        forgotten = forget_answers(settings) if self._forget else 0
        after = (
            settings.external_change_watch_enabled,
            settings.external_change_auto_reload_when_clean,
            settings.external_change_prompt_on_conflict,
            settings.external_change_debounce_ms,
        )
        return bool(forgotten) or before != after
