"""The Sound Scheme window: one list of events, and what each one plays.

The shape every desktop has used for this since Windows 95, because it is the
right one: a **scheme** at the top, a **list of events** in the middle, and the
controls that act on the selected event underneath. Somebody who has ever
changed a system sound already knows how to drive this window, and that is worth
more than any arrangement invented here.

Four decisions are QUILL's own.

**A list box, not a grid of checkboxes.** The house rule
(``wx.CheckListBox`` and checkbox columns are out) exists because a checkbox
inside a list control is announced inconsistently and cannot be reached the same
way twice. So the state is *in the row text* -- "Save a document: on, save.wav,
80 ms" -- which a screen reader reads in full on arrival, and the controls below
act on whatever row you are on. One row, one utterance, everything in it.

**It plays as you move.** That is the whole point of the window: a list of
ninety earcon names is unusable, and a list you *hear* as you arrow through it is
a catalogue. It is a checkbox rather than a rule, because somebody who knows
what they are looking for should be able to arrow past forty rows in silence,
and because playing a sound on every selection change is exactly the kind of
thing that is delightful for a week and tiring afterwards.

**Everything is reversible, at three scales.** *Use Default* on one event, and
*Restore All Defaults* for the lot, and Cancel for the whole visit. None of the
three can fail, because none of them replays anything: the bundled pack is
read-only, so "the default" is not a saved copy to be recovered but simply what
is left when an override is dropped.

**Saving makes an ordinary pack.** Save As writes a directory with the same
manifest every shipped pack has (:mod:`quill.core.sound_scheme`), so a scheme
can be zipped, sent to somebody, or read in a text editor. It is not a private
format that traps the work.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from pathlib import Path

import wx

from quill.core.sound_app_events import events_for
from quill.core.sound_scheme import (
    SchemeDraft,
    SchemeError,
    delete_scheme,
    describe_sound,
    save_scheme,
    user_schemes,
)
from quill.ui.dialog_contract import (
    apply_modal_ids,
    set_accessible_name,
    show_message_box,
    show_modal_dialog,
)
from quill.ui.sound_event_labels import EVENT_GROUPS, GROUP_FOR, label_for

__all__ = ["SoundSchemeDialog", "SoundSchemeResult", "draft_for_pack", "known_events"]

_PAD = 8

#: How wide the list is. Wide enough that the longest row -- a group name, a
#: state, a file name and a duration -- fits without truncation, because a
#: truncated row is one a sighted user has to scroll to finish reading.
_LIST_SIZE = (620, 380)


class SoundSchemeResult:
    """What the window decided: which scheme, which events are silenced.

    A small object rather than a tuple, so a caller reads ``result.pack_path``
    instead of remembering which slot it was in.
    """

    __slots__ = ("changed", "disabled_csv", "pack_path")

    def __init__(self, changed: bool, pack_path: str, disabled_csv: str) -> None:
        self.changed = changed
        self.pack_path = pack_path
        self.disabled_csv = disabled_csv


class SoundSchemeDialog:
    """Browse every sound event, hear it, change it, save the set as a scheme."""

    def __init__(
        self,
        parent: object,
        *,
        draft: SchemeDraft,
        disabled: frozenset[str],
        data_dir: Path,
        available: Sequence[tuple[str, str]] = (),
        current_pack: str = "",
        play: Callable[[Path], None] | None = None,
        announce: Callable[[str], None] | None = None,
        app_title: str = "QUILL",
        app_id: str = "",
    ) -> None:
        self._draft = draft
        #: The events *this app* can actually fire. Reported by ear: the window
        #: used to list every event the enum declares, most of which the app in
        #: front of you never posts -- so somebody could pick a sound for
        #: "Radio playing" in a text editor and wait a long time to hear it. A
        #: settings list that promises more than the code delivers is worse than
        #: a shorter one. An app with no roster gets everything, which is right
        #: for the full editor and safe for anything new: a spare row costs one
        #: press of Down, a missing one is a sound nobody can switch off.
        self._app_events = events_for(app_id)
        self._data_dir = Path(data_dir)
        self._disabled = set(disabled)
        self._play = play
        self._announce = announce or (lambda _m: None)
        self._saved_pack = current_pack
        self._changed = False
        #: (event id, group) in display order, so the list index maps back to an
        #: event without a second lookup table to keep in step.
        self._rows: list[str] = []

        self.dialog = wx.Dialog(
            parent,
            title=f"{app_title} Sound Scheme",
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        root = wx.BoxSizer(wx.VERTICAL)
        root.Add(
            wx.StaticText(
                self.dialog,
                label=(
                    "Choose a scheme, then pick an event to hear it, change it, or switch it off."
                ),
            ),
            0,
            wx.ALL,
            _PAD,
        )
        root.Add(self._build_scheme_row(available, current_pack), 0, wx.EXPAND | wx.ALL, _PAD)
        root.Add(self._build_list(), 1, wx.EXPAND | wx.LEFT | wx.RIGHT, _PAD)
        root.Add(self._build_event_controls(), 0, wx.EXPAND | wx.ALL, _PAD)
        root.Add(self._build_scheme_buttons(), 0, wx.EXPAND | wx.LEFT | wx.RIGHT, _PAD)

        buttons = self.dialog.CreateStdDialogButtonSizer(wx.OK | wx.CANCEL)
        root.Add(buttons, 0, wx.EXPAND | wx.ALL, _PAD)
        self.dialog.SetSizerAndFit(root)
        apply_modal_ids(self.dialog, affirmative_id=wx.ID_OK, cancel_id=wx.ID_CANCEL)
        self._fill_list()

    # ------------------------------------------------------------------ #
    # Construction
    # ------------------------------------------------------------------ #

    def _build_scheme_row(self, available, current_pack):  # type: ignore[no-untyped-def]
        row = wx.BoxSizer(wx.HORIZONTAL)
        label = wx.StaticText(self.dialog, label="Sc&heme:")
        self._schemes = list(available)
        self.scheme_choice = wx.Choice(
            self.dialog, choices=[name for name, _value in self._schemes] or ["Default"]
        )
        set_accessible_name(self.scheme_choice, "Scheme")
        self.scheme_choice.SetHelpText(
            "The set of sounds in use. Choosing a different one changes every event "
            "at once; the list below then shows what that scheme plays."
        )
        values = [value for _name, value in self._schemes]
        self.scheme_choice.SetSelection(values.index(current_pack) if current_pack in values else 0)
        self.scheme_choice.Bind(wx.EVT_CHOICE, lambda _e: self._on_scheme_chosen())
        row.Add(label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6)
        row.Add(self.scheme_choice, 1, wx.ALIGN_CENTER_VERTICAL)
        return row

    def _build_list(self):  # type: ignore[no-untyped-def]
        column = wx.BoxSizer(wx.VERTICAL)
        label = wx.StaticText(self.dialog, label="&Events:")
        self.events = wx.ListBox(self.dialog, size=_LIST_SIZE)
        set_accessible_name(self.events, "Events")
        self.events.SetHelpText(
            "Every moment this app can make a sound for. Each row says whether it "
            "is switched on, which file it plays, and how long that file is. Move "
            "through the list to hear each one; the buttons below change whichever "
            "row you are on."
        )
        self.events.Bind(wx.EVT_LISTBOX, lambda _e: self._on_row_changed())
        column.Add(label, 0, wx.BOTTOM, 4)
        column.Add(self.events, 1, wx.EXPAND)

        self.preview_as_you_go = wx.CheckBox(
            self.dialog, label="Play each sound as I &move through the list"
        )
        self.preview_as_you_go.SetValue(True)
        self.preview_as_you_go.SetHelpText(
            "On: arrowing onto an event plays it. That is what makes a list of "
            "ninety earcon names something you can actually browse. Off: nothing "
            "plays until you press Play, which is faster when you know the row you "
            "are looking for."
        )
        column.Add(self.preview_as_you_go, 0, wx.TOP, 4)
        return column

    def _build_event_controls(self):  # type: ignore[no-untyped-def]
        box = wx.StaticBoxSizer(wx.VERTICAL, self.dialog, "The event you are on")
        # Parented to the box, not the dialog: wx asserts on the other way round
        # and lays the group out wrong on Windows.
        panel = box.GetStaticBox()
        self.detail = wx.TextCtrl(
            panel, value="", style=wx.TE_READONLY | wx.TE_MULTILINE, size=(-1, 44)
        )
        set_accessible_name(self.detail, "About this event")
        self.detail.SetHelpText("What this event means, and what it currently plays.")
        box.Add(self.detail, 0, wx.EXPAND | wx.ALL, _PAD // 2)

        row = wx.BoxSizer(wx.HORIZONTAL)
        self.play_button = wx.Button(panel, label="&Play")
        self.play_button.SetHelpText("Play this event's sound now.")
        self.play_button.Bind(wx.EVT_BUTTON, lambda _e: self._play_current(spoken=True))
        row.Add(self.play_button, 0, wx.RIGHT, 6)

        self.enabled_box = wx.CheckBox(panel, label="S&witched on")
        self.enabled_box.SetHelpText(
            "Off silences this one event without changing which sound it would "
            "play, so switching it back on gives you the same sound again."
        )
        self.enabled_box.Bind(wx.EVT_CHECKBOX, lambda _e: self._on_enabled_toggled())
        row.Add(self.enabled_box, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 12)

        browse = wx.Button(panel, label="&Browse...")
        browse.SetHelpText("Choose a WAV file of your own for this event.")
        browse.Bind(wx.EVT_BUTTON, lambda _e: self._browse())
        row.Add(browse, 0, wx.RIGHT, 6)

        silence = wx.Button(panel, label="&No Sound")
        silence.SetHelpText(
            "Give this event no sound at all. Different from switching it off: "
            "this removes the sound from the scheme rather than muting the event."
        )
        silence.Bind(wx.EVT_BUTTON, lambda _e: self._silence())
        row.Add(silence, 0, wx.RIGHT, 6)

        self.default_button = wx.Button(panel, label="&Use Default")
        self.default_button.SetHelpText("Put this one event back to the sound the scheme ships.")
        self.default_button.Bind(wx.EVT_BUTTON, lambda _e: self._restore_one())
        row.Add(self.default_button, 0)
        box.Add(row, 0, wx.ALL, _PAD // 2)
        return box

    def _build_scheme_buttons(self):  # type: ignore[no-untyped-def]
        row = wx.BoxSizer(wx.HORIZONTAL)
        save_as = wx.Button(self.dialog, label="Save &As Scheme...")
        save_as.SetHelpText(
            "Save every sound in the list as a scheme of your own, under a name you "
            "choose. Schemes are ordinary folders you can copy or send to somebody."
        )
        save_as.Bind(wx.EVT_BUTTON, lambda _e: self._save_as())
        row.Add(save_as, 0, wx.RIGHT, 6)

        self.delete_button = wx.Button(self.dialog, label="De&lete Scheme")
        self.delete_button.SetHelpText("Remove one of your own saved schemes. Never a shipped one.")
        self.delete_button.Bind(wx.EVT_BUTTON, lambda _e: self._delete_scheme())
        row.Add(self.delete_button, 0, wx.RIGHT, 6)

        restore = wx.Button(self.dialog, label="&Restore All Defaults")
        restore.SetHelpText(
            "Put every event back to the sound this scheme ships, and switch them "
            "all on. Nothing you have saved is deleted."
        )
        restore.Bind(wx.EVT_BUTTON, lambda _e: self._restore_all())
        row.Add(restore, 0)
        return row

    # ------------------------------------------------------------------ #
    # The list
    # ------------------------------------------------------------------ #

    def _fill_list(self, keep_index: int = 0) -> None:
        """Rebuild every row. Cheap enough at this size, and always correct."""
        self._rows = []
        labels: list[str] = []
        for group, events in EVENT_GROUPS:
            for event in events:
                if event not in self._app_events:
                    continue
                self._rows.append(event)
                labels.append(f"{group}: {self._row_text(event)}")
        self.events.Set(labels)
        if labels:
            self.events.SetSelection(min(keep_index, len(labels) - 1))
        self._refresh_detail(play=False)

    def _row_text(self, event: str) -> str:
        """One row, read in full by a screen reader on arrival.

        Everything in the row rather than spread across the controls below it:
        a listener arrowing a list hears the row and nothing else, so a state
        that lives only in a checkbox underneath is a state they have to Tab to
        discover, once per row, ninety times.
        """
        state = "off" if event in self._disabled else "on"
        source = self._draft.source_for(event)
        sound = describe_sound(source)
        custom = "" if self._draft.is_default(event) else ", changed"
        return f"{label_for(event)}: {state}, {sound}{custom}"

    def _selected(self) -> str | None:
        index = self.events.GetSelection()
        if index == wx.NOT_FOUND or index >= len(self._rows):
            return None
        return self._rows[index]

    def _refresh_row(self) -> None:
        index = self.events.GetSelection()
        event = self._selected()
        if event is None:
            return
        group = GROUP_FOR.get(event, "")
        self.events.SetString(index, f"{group}: {self._row_text(event)}")

    def _on_row_changed(self) -> None:
        self._refresh_detail(play=bool(self.preview_as_you_go.GetValue()))

    def _refresh_detail(self, *, play: bool) -> None:
        event = self._selected()
        if event is None:
            self.detail.SetValue("")
            return
        source = self._draft.source_for(event)
        self.enabled_box.SetValue(event not in self._disabled)
        self.default_button.Enable(not self._draft.is_default(event))
        self.detail.SetValue(f"{label_for(event)}\n{describe_sound(source)}")
        if play:
            self._play_current(spoken=False)

    # ------------------------------------------------------------------ #
    # Acting on the selected event
    # ------------------------------------------------------------------ #

    def _play_current(self, *, spoken: bool) -> None:
        """Play the selected event's sound, or say why there is nothing to play.

        Silence and a broken file are different answers and the user needs both:
        "Silent" is a choice they may have made, and "cannot be read" is a file
        that has moved. Only said when the button was pressed -- arrowing through
        the list must not narrate every silent row.
        """
        event = self._selected()
        if event is None:
            return
        source = self._draft.source_for(event)
        if source is None:
            if spoken:
                self._announce(f"{label_for(event)} has no sound.")
            return
        if self._play is None:
            if spoken:
                self._announce("No sound player is available.")
            return
        try:
            self._play(source)
        except Exception:  # noqa: BLE001 - a preview must never take the window down
            if spoken:
                self._announce(f"Could not play {source.name}.")

    def _on_enabled_toggled(self) -> None:
        event = self._selected()
        if event is None:
            return
        if self.enabled_box.GetValue():
            self._disabled.discard(event)
            said = "on"
        else:
            self._disabled.add(event)
            said = "off"
        self._changed = True
        self._refresh_row()
        # The row's text just changed on an unfocused control, which is exactly
        # what a reader does not say (GATE-12), and the checkbox announces only
        # its own new state -- not which event it belongs to.
        self._announce(f"{label_for(event)} {said}")

    def _browse(self) -> None:
        event = self._selected()
        if event is None:
            return
        with wx.FileDialog(
            self.dialog,
            message=f"Choose a sound for {label_for(event)}",
            wildcard="Sound files (*.wav)|*.wav|All files (*.*)|*.*",
            style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
        ) as picker:
            if picker.ShowModal() != wx.ID_OK:
                return
            chosen = Path(picker.GetPath())
        try:
            self._draft.set_sound(event, chosen)
        except SchemeError as error:
            # Refused at the moment of choosing, with a sentence. A sound that
            # fails at playback fails *silently*, and a silent event is
            # indistinguishable from one nobody set.
            self._announce(str(error))
            show_message_box(
                str(error), "Cannot use that sound", wx.OK | wx.ICON_WARNING, self.dialog
            )
            return
        self._changed = True
        self._refresh_row()
        self._refresh_detail(play=False)
        self._announce(f"{label_for(event)} now plays {chosen.name}")
        self._play_current(spoken=False)

    def _silence(self) -> None:
        event = self._selected()
        if event is None:
            return
        self._draft.silence(event)
        self._changed = True
        self._refresh_row()
        self._refresh_detail(play=False)
        self._announce(f"{label_for(event)} now has no sound")

    def _restore_one(self) -> None:
        event = self._selected()
        if event is None:
            return
        self._draft.restore(event)
        self._changed = True
        self._refresh_row()
        self._refresh_detail(play=False)
        self._announce(f"{label_for(event)} back to the default: {self._current_sound_name(event)}")
        self._play_current(spoken=False)

    def _current_sound_name(self, event: str) -> str:
        source = self._draft.source_for(event)
        return source.name if source is not None else "no sound"

    def _restore_all(self) -> None:
        """The escape hatch. One press, and it cannot half-succeed."""
        self._draft.restore_all()
        self._disabled.clear()
        self._changed = True
        index = self.events.GetSelection()
        self._fill_list(keep_index=max(0, index))
        self._announce(
            "Every event is back to the sound this scheme ships, and all of them are switched on."
        )

    # ------------------------------------------------------------------ #
    # Schemes
    # ------------------------------------------------------------------ #

    def _on_scheme_chosen(self) -> None:
        index = self.scheme_choice.GetSelection()
        if index < 0 or index >= len(self._schemes):
            return
        name, value = self._schemes[index]
        self._saved_pack = value
        self._changed = True
        self._announce(
            f"{name}. The list now shows what that scheme plays; nothing is saved "
            "until you press OK."
        )
        # The draft's base has to follow the scheme, or the list would keep
        # describing the old one. Overrides are dropped with it: they were
        # expressed against a pack that is no longer the base, and silently
        # re-pointing them at a different scheme's events would be a change
        # nobody asked for.
        self._reload_draft_for(value)
        self._fill_list(keep_index=max(0, self.events.GetSelection()))

    def _reload_draft_for(self, pack_value: str) -> None:
        from quill.core.sound_pack import resolve_sound_pack_path

        path = resolve_sound_pack_path(pack_value)
        self._draft.overrides.clear()
        self._draft.removed.clear()
        self._draft.base_dir = path if path is not None and path.is_dir() else None
        self._draft.base_events = _manifest_events(path)

    def _save_as(self) -> None:
        with wx.TextEntryDialog(
            self.dialog,
            "Name for this scheme:",
            "Save Sound Scheme",
        ) as prompt:
            if prompt.ShowModal() != wx.ID_OK:
                return
            name = prompt.GetValue().strip()
        if not name:
            self._announce("A scheme needs a name. Nothing was saved.")
            return
        try:
            path = save_scheme(self._draft, name, self._data_dir)
        except SchemeError as error:
            self._announce(str(error))
            show_message_box(str(error), "Could not save", wx.OK | wx.ICON_WARNING, self.dialog)
            return
        self._saved_pack = str(path)
        self._changed = True
        self._refresh_scheme_choices(select=str(path))
        self._announce(
            f"Saved as {name}, and it is now the scheme in use. It is a folder you "
            "can copy or send to somebody."
        )

    def _delete_scheme(self) -> None:
        index = self.scheme_choice.GetSelection()
        if index < 0 or index >= len(self._schemes):
            return
        name, value = self._schemes[index]
        mine = {str(scheme.path): scheme for scheme in user_schemes(self._data_dir)}
        scheme = mine.get(value)
        if scheme is None:
            # A shipped scheme. Refused in words rather than by a greyed button
            # that says nothing about why: the answer "that one is part of the
            # app" is information, and a disabled control is not.
            self._announce(f"{name} ships with the app and cannot be deleted.")
            return
        confirmed = show_message_box(
            f"Delete the scheme {name}? The sounds in it are removed from your computer.",
            "Delete Scheme",
            wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION,
            self.dialog,
        )
        if confirmed != wx.YES:
            return
        try:
            delete_scheme(scheme)
        except SchemeError as error:
            self._announce(str(error))
            return
        self._saved_pack = ""
        self._changed = True
        self._refresh_scheme_choices(select="")
        self._reload_draft_for("")
        self._fill_list()
        self._announce(f"{name} deleted. Back to the sounds the app ships.")

    def _refresh_scheme_choices(self, *, select: str) -> None:
        from quill.core.sound_pack import available_sound_packs

        schemes: list[tuple[str, str]] = [
            (pack.name, pack.setting_value) for pack in available_sound_packs()
        ]
        schemes.extend(
            (scheme.name, scheme.setting_value) for scheme in user_schemes(self._data_dir)
        )
        self._schemes = schemes
        self.scheme_choice.Set([name for name, _value in schemes] or ["Default"])
        values = [value for _name, value in schemes]
        self.scheme_choice.SetSelection(values.index(select) if select in values else 0)

    # ------------------------------------------------------------------ #
    # Showing it
    # ------------------------------------------------------------------ #

    def show(self) -> SoundSchemeResult:
        self.dialog.CentreOnParent()
        self.events.SetFocus()
        try:
            if show_modal_dialog(self.dialog, "Sound Scheme") != wx.ID_OK:
                return SoundSchemeResult(False, "", "")
            return SoundSchemeResult(
                self._changed,
                self._saved_pack,
                ",".join(sorted(self._disabled)),
            )
        finally:
            self.dialog.Destroy()


def _manifest_events(path: Path | None) -> dict[str, str]:
    """The event map inside a pack directory, or {} for anything unreadable."""
    import json

    if path is None or not path.is_dir():
        return {}
    manifest = path / "manifest.json"
    try:
        raw = json.loads(manifest.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    events = raw.get("events") if isinstance(raw, dict) else None
    if not isinstance(events, dict):
        return {}
    return {str(key): str(value) for key, value in events.items() if isinstance(value, str)}


def draft_for_pack(pack_value: str) -> SchemeDraft:
    """A fresh, unedited draft over the pack *pack_value* names."""
    from quill.core.sound_pack import resolve_sound_pack_path

    path = resolve_sound_pack_path(pack_value)
    return SchemeDraft(
        base_events=_manifest_events(path),
        base_dir=path if path is not None and path.is_dir() else None,
    )


def known_events(app_id: str = "") -> list[str]:
    """The events this window offers for *app_id*, in the order it shows them."""
    allowed = events_for(app_id)
    return [event for _group, events in EVENT_GROUPS for event in events if event in allowed]
