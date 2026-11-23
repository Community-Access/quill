"""The settings groups of Convert with Scribe for Documents (PRD 7.3 part 3).

Four labelled static boxes -- "Language and voice", "Braille", "Print" and
"Pictures and maths" -- all created when the dialog is built, in display
order (wx tab order follows creation order), each label created immediately
before its control and parented to its box so screen readers say the group
name on entering it. A group is only shown or hidden to match the chosen
formats; hidden groups keep their values, and hiding never removes the
focused control (focus moves to the format check box that hid it first).

**Starting values** (3.3, Pneuma 2026-11-21) are the person's Scribe account
defaults, read when the dialog opens (or, for a document already in the
account, that document's own settings), with this app's last choices on
top. They arrive after the dialog is built; :meth:`SettingsGroups.apply`
puts them in silently, unless the person has already changed a setting.
For a document already uploaded, the settings its upload fixed (language,
picture descriptions, mathematics, large print) are hidden and their values
are listed instead in a read-only field, "Fixed when <title> was uploaded",
at the top of the first group: a disabled control would drop out of Tab, so
nobody could find out what the values are (accessibility review, 2026-11-21).

Speed is a choice of the website's speeds, 3 and 4 times labelled "(may not
be faster than 2)"; line length is a spin control from 20 to 42 cells and
lines per page from 20 to 30.

Choice lists come from the server, cached for the session by the
controller. While a list loads its control says "Loading voices..." (enabled,
not dimmed, so Tab still reaches it); if loading fails it says "Voices could
not be loaded" and Retry Loading appears right after it. A list is never
empty.
"""

from __future__ import annotations

from typing import Any

import wx

from quill.core.scribe.model import (
    BRAILLE_CELLS_RANGE,
    BRAILLE_LINES_RANGE,
    GROUPS,
    TTS_GENDERS,
    TTS_RATES,
    ScribeSettings,
    nearest_rate,
    visible_groups,
)

DETECT = "Detect automatically"
SCRIBE_DEFAULT = "Scribe's default"


class SettingsGroups:
    """Builds the four groups into *parent*'s *sizer*; owns their controls."""

    def __init__(
        self,
        parent: Any,
        sizer: Any,
        controller: Any,
        settings: ScribeSettings,
        *,
        ai_off: bool,
        app_name: str,
    ) -> None:
        self._parent = parent
        self._controller = controller
        self._settings = settings
        self._lists: dict[str, Any] = {}
        self._player: Any = None
        self.boxes: dict[str, Any] = {}
        labels = {key: label for key, label, _shown in GROUPS}

        box = self._box(sizer, "language", labels["language"])
        parent = box.GetStaticBox()
        self.fixed_label = wx.StaticText(parent, label="Fi&xed when uploaded:")
        box.Add(self.fixed_label, 0, wx.LEFT | wx.TOP, 4)
        self.fixed = wx.TextCtrl(parent, style=wx.TE_READONLY, value="Loading...")
        self.fixed.SetName("Fixed when uploaded")
        self.fixed.SetHelpText(
            "The settings this document's upload fixed: language, picture descriptions, "
            "mathematics and large print. They cannot be changed for it."
        )
        box.Add(self.fixed, 0, wx.EXPAND | wx.ALL, 4)
        self.fixed_label.Hide()
        self.fixed.Hide()
        self._fixed_shown = False
        self.language = self._choice(
            box,
            "&Language:",
            ["Loading languages..."],
            "The document's language. Detect automatically lets Scribe find it.",
        )
        self.retry = wx.Button(box.GetStaticBox(), label="Retr&y Loading")
        self.retry.SetHelpText(
            "Asks Scribe for its lists of languages, voices and braille tables again."
        )
        box.Add(self.retry, 0, wx.ALL, 4)
        self.retry.Hide()
        self.dialect = self._choice(
            box,
            "&Dialect:",
            ["Loading dialects..."],
            "The dialect of the chosen language, which decides the voices offered.",
        )
        row = wx.BoxSizer(wx.HORIZONTAL)
        self.voice = self._choice(
            box,
            "&Voice:",
            ["Loading voices..."],
            "The voice for MP3 and DAISY audio. Play Sample lets you hear it.",
            into=row,
        )
        self.sample = wx.Button(box.GetStaticBox(), label="Play &Sample")
        self.sample.SetHelpText(
            "Plays a short sample of the chosen voice. While it plays the button reads Stop "
            "Sample, and Escape stops the sample without closing the dialog."
        )
        row.Add(self.sample, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 4)
        box.Add(row, 0, wx.EXPAND)
        self.gender = self._choice(
            box,
            "&Gender of the voice when the language is detected:",
            [label for _key, label in TTS_GENDERS],
            "Used only when Scribe detects the language itself.",
        )
        self.gender.SetSelection(
            next((i for i, (key, _l) in enumerate(TTS_GENDERS) if key == settings.tts_gender), 0)
        )
        self.speed = self._choice(
            box,
            "Sp&eed:",
            [label for _rate, label in TTS_RATES],
            "How fast the voice reads, from half to four times normal speed. Scribe may not "
            "read faster than 2 times yet, even at 3 or 4.",
        )
        self._set_speed(settings.tts_rate)

        box = self._box(sizer, "braille", labels["braille"])
        self.table = self._choice(
            box,
            "Braille &table:",
            ["Loading braille tables..."],
            "The braille code: Grade 1, Grade 2, UEB, computer braille and other languages.",
        )
        self.cells = self._spin(
            box,
            "&Cells per line:",
            *BRAILLE_CELLS_RANGE,
            settings.braille_cells_per_line,
            "How many braille cells on a line; 40 is usual. From 20 to 42.",
        )
        self.split = self._check(
            box,
            "Spl&it into pages",
            settings.braille_split_into_pages,
            "Breaks the braille into pages of the length below.",
        )
        self.lines = self._spin(
            box,
            "Li&nes per page:",
            *BRAILLE_LINES_RANGE,
            settings.braille_lines_per_page,
            "How many lines on a braille page, when it is split into pages. From 20 to 30.",
        )

        box = self._box(sizer, "print", labels["print"])
        self.large_print = self._check(
            box,
            "Large p&rint",
            settings.large_print,
            "Makes the Word and tagged PDF results in large print.",
        )

        box = self._box(sizer, "pictures", labels["pictures"])
        describe = "Describe the pict&ures"
        if ai_off:
            describe += f" (off because AI is turned off in {app_name})"
        self.describe = self._check(
            box,
            describe,
            settings.add_image_descriptions and not ai_off,
            "Scribe's AI describes the pictures in the document. This is Scribe's processing, "
            f"not {app_name}'s AI, so you may check it even with AI turned off.",
        )
        self.math = self._check(
            box,
            "&Mathematics (beta)",
            settings.math,
            # What it does today (F7, Pneuma's corpus): no MathML in any format yet.
            "Scribe's beta setting for mathematics. Today it makes no MathML, on or off: "
            "an equation comes as a picture whose alt text reads it in words.",
        )
        self.notify = self._check(
            box,
            "Email me when it is finis&hed (Scribe's own email)",
            settings.notify_when_complete,
            "Asks Scribe to email you when it finishes, one email for each format. It "
            "starts unchecked unless you checked it last time, because "
            f"{app_name} already tells you when each result is ready.",
        )

        self.touched = False
        for control in (self.gender, self.speed, self.table, self.voice):
            control.Bind(wx.EVT_CHOICE, self._on_touched)
        for control in (self.cells, self.lines):
            control.Bind(wx.EVT_SPINCTRL, self._on_touched)
        for control in (self.split, self.large_print, self.describe, self.math, self.notify):
            control.Bind(wx.EVT_CHECKBOX, self._on_touched)
        # Reaching a setting counts too: a late reply never changes a value under
        # focus, nor one the person has already read (accessibility review, 2026-11-21).
        for control in (
            self.language, self.dialect, self.voice, self.gender, self.speed, self.table,
            self.cells, self.lines, self.split, self.large_print, self.describe, self.math,
            self.notify,
        ):  # fmt: skip
            control.Bind(wx.EVT_SET_FOCUS, self._on_touched)
        self._ai_off = ai_off
        self.language.Bind(wx.EVT_CHOICE, lambda e: (self._on_touched(e), self._fill_dialects()))
        self.dialect.Bind(wx.EVT_CHOICE, lambda e: (self._on_touched(e), self._fill_voices()))
        self.sample.Bind(wx.EVT_BUTTON, lambda _e: self.toggle_sample())
        self.retry.Bind(wx.EVT_BUTTON, lambda _e: self.load())
        self.load()

    # ------------------------------------------------------- starting values

    def _on_touched(self, event: Any) -> None:
        self.touched = True
        event.Skip()

    def _set_speed(self, rate: float) -> None:
        rates = [value for value, _label in TTS_RATES]
        self.speed.SetSelection(rates.index(nearest_rate(rate)))

    def apply(self, settings: ScribeSettings) -> bool:
        """Put *settings* in as the starting values, silently -- unless the person
        has already changed one, whose choice wins. True when applied."""
        if not self._alive():
            return False
        self._refresh_fixed(settings)
        if self.touched:
            return False
        self._settings = settings
        self.gender.SetSelection(
            next((i for i, (key, _l) in enumerate(TTS_GENDERS) if key == settings.tts_gender), 0)
        )
        self._set_speed(settings.tts_rate)
        self.cells.SetValue(settings.braille_cells_per_line)
        self.split.SetValue(settings.braille_split_into_pages)
        self.lines.SetValue(settings.braille_lines_per_page)
        self.large_print.SetValue(settings.large_print)
        self.describe.SetValue(settings.add_image_descriptions and not self._ai_off)
        self.math.SetValue(settings.math)
        self.notify.SetValue(settings.notify_when_complete)
        if self._lists.get("languages"):
            self._apply(self._lists)
        return True

    def _fixed_controls(self) -> tuple[Any, ...]:
        return (
            self.language._quill_label,
            self.language,
            self.large_print,
            self.describe,
            self.math,
        )

    def fix_upload_settings(self, title: str) -> None:
        """A document already uploaded: its language, pictures, mathematics and
        large print were fixed then (3.3). Their controls are hidden (they keep
        their values) and the values are listed in the read-only field."""
        self._fixed_shown = True
        self.fixed_label.SetLabel(f"Fi&xed when {title} was uploaded:")
        self.fixed.SetName(f"Fixed when {title} was uploaded")
        self.fixed_label.Show()
        self.fixed.Show()
        for control in self._fixed_controls():
            control.Hide()
        self._parent.Layout()

    def _refresh_fixed(self, settings: ScribeSettings) -> None:
        if not self._fixed_shown or wx.Window.FindFocus() is self.fixed:
            return  # never rewrite what is being read
        names = dict((code, name) for name, code in self._lists.get("languages") or [])
        language = names.get(settings.language, settings.language) or DETECT

        def on(value: bool) -> str:
            return "on" if value else "off"

        self.fixed.SetValue(
            f"Language: {language}. Describe the pictures: {on(settings.add_image_descriptions)}. "
            f"Mathematics: {on(settings.math)}. Large print: {on(settings.large_print)}."
        )

    # ---------------------------------------------------------------- build

    def _box(self, sizer: Any, key: str, label: str) -> Any:
        box = wx.StaticBoxSizer(wx.VERTICAL, self._parent, label)
        sizer.Add(box, 0, wx.EXPAND | wx.ALL, 6)
        self.boxes[key] = box
        return box

    @staticmethod
    def _choice(box: Any, label: str, items: list[str], help_text: str, *, into: Any = None) -> Any:
        parent = box.GetStaticBox()
        target = into if into is not None else box
        text = wx.StaticText(parent, label=label)
        target.Add(text, 0, wx.LEFT | wx.TOP, 4)
        choice = wx.Choice(parent, choices=items)
        choice._quill_label = text
        choice.SetSelection(0)
        choice.SetName(label.replace("&", "").rstrip(":"))
        choice.SetHelpText(help_text)
        target.Add(choice, 1 if into is not None else 0, wx.EXPAND | wx.ALL, 4)
        return choice

    @staticmethod
    def _spin(box: Any, label: str, low: int, high: int, value: int, help_text: str) -> Any:
        parent = box.GetStaticBox()
        box.Add(wx.StaticText(parent, label=label), 0, wx.LEFT | wx.TOP, 4)
        spin = wx.SpinCtrl(parent, min=low, max=high, initial=max(low, min(high, value)))
        spin.SetName(label.replace("&", "").rstrip(":"))
        spin.SetHelpText(help_text)
        box.Add(spin, 0, wx.ALL, 4)
        return spin

    @staticmethod
    def _check(box: Any, label: str, value: bool, help_text: str) -> Any:
        check = wx.CheckBox(box.GetStaticBox(), label=label)
        check.SetValue(bool(value))
        check.SetHelpText(help_text)
        box.Add(check, 0, wx.ALL, 4)
        return check

    # ----------------------------------------------------------- show/hide

    def show_for(self, format_ids: list[str], focus_fallback: Any = None) -> None:
        """Show the groups the chosen formats need; keep the hidden ones' values."""
        wanted = set(visible_groups(format_ids))
        if self._fixed_shown:
            wanted.discard("print")  # its one control, large print, is fixed
        focused = wx.Window.FindFocus()
        for key, box in self.boxes.items():
            show = key in wanted
            static = box.GetStaticBox()
            if not show and focused is not None and _is_inside(focused, static):
                if focus_fallback is not None:
                    focus_fallback.SetFocus()
            box.ShowItems(show)
            static.Show(show)
        if not self._lists.get("failed"):
            self.retry.Hide()
        self.fixed_label.Show(self._fixed_shown)
        self.fixed.Show(self._fixed_shown)
        if self._fixed_shown:
            for control in self._fixed_controls():
                control.Hide()

    # --------------------------------------------------------------- lists

    def load(self) -> None:
        """Fetch (or reuse the session's cache of) the server's choice lists."""
        cached = getattr(self._controller, "_choice_lists", None)
        if cached:
            self._apply(cached)
            return
        self.retry.Hide()

        def work() -> dict[str, Any]:
            client = self._controller.client()
            return {
                "languages": client.languages(),
                "dialects": client.dialects(),
                "voices": client.voices(),
                "tables": client.braille_tables(),
            }

        def done(lists: dict[str, Any]) -> None:
            self._controller._choice_lists = lists
            self._apply(lists)

        self._controller._background(work, done, lambda _error: self._failed())

    def _alive(self) -> bool:
        try:
            return bool(self.language) and not self.language.IsBeingDeleted()
        except RuntimeError:
            return False

    def _failed(self) -> None:
        if not self._alive():
            return
        self._lists = {"failed": True}
        for control, words in (
            (self.language, "Languages"),
            (self.dialect, "Dialects"),
            (self.voice, "Voices"),
            (self.table, "Braille tables"),
        ):
            control.Set([f"{words} could not be loaded"])
            control.SetSelection(0)
        self.retry.Show()
        self._parent.Layout()
        if wx.Window.FindFocus() in (self.language, self.voice, self.table, self.dialect):
            self._controller.host.scribe_announce(
                "The lists could not be loaded. Use Retry Loading."
            )

    def _apply(self, lists: dict[str, Any]) -> None:
        if not self._alive():
            return
        self._lists = lists
        self._set(self.language, [(DETECT, "")] + list(lists["languages"]), self._settings.language)
        self._set(
            self.table,
            [(SCRIBE_DEFAULT, "")] + list(lists["tables"]),
            self._settings.braille_translation_table,
        )
        self._fill_dialects()
        self._refresh_fixed(self._settings)
        self.retry.Hide()
        self._parent.Layout()

    def _set(self, control: Any, pairs: list[tuple[str, str]], value: str) -> None:
        control._quill_ids = [item_id for _name, item_id in pairs]
        control.Set([name for name, _id in pairs])
        ids = control._quill_ids
        control.SetSelection(ids.index(value) if value in ids else 0)

    @staticmethod
    def _value(control: Any) -> str:
        ids = getattr(control, "_quill_ids", None)
        index = control.GetSelection()
        if not ids or index < 0 or index >= len(ids):
            return ""
        return str(ids[index])

    def _fill_dialects(self) -> None:
        language = self._value(self.language)
        dialects = list(self._lists.get("dialects", {}).get(language, [])) if language else []
        chosen = self._settings.dialects.get(language, "")
        self._set(self.dialect, [(SCRIBE_DEFAULT, "")] + dialects, chosen)
        self._fill_voices()

    def _fill_voices(self) -> None:
        locale = self._value(self.dialect)
        voices = self._lists.get("voices", {}).get(locale, []) if locale else []
        self._samples = {short: has for _n, short, has in voices}
        chosen = self._settings.voices.get(locale, "")
        self._set(self.voice, [(SCRIBE_DEFAULT, "")] + [(n, s) for n, s, _h in voices], chosen)

    # -------------------------------------------------------------- sample

    def sample_playing(self) -> bool:
        return self._player is not None and self._player.is_playing()

    def toggle_sample(self) -> None:
        if self.sample_playing():
            self.stop_sample()
            return
        short = self._value(self.voice)
        if not short or not getattr(self, "_samples", {}).get(short):
            self._controller.host.scribe_announce("This voice has no sample.")
            return

        self._controller._background(
            lambda: self._controller.client().voice_sample(short),
            self._play,
            lambda _error: self._controller.host.scribe_announce("The sample could not be played."),
        )

    def _play(self, data: bytes) -> None:
        from quill.ui.scribe_sample_player import SamplePlayer

        if not self._alive():
            return
        self._player = self._player or SamplePlayer()
        if self._player.play(data):
            self.sample.SetLabel("&Stop Sample")
            # Back to Play Sample when the sample ends on its own.
            self._sample_timer = wx.CallLater(500, self._watch_sample)
        else:
            self._controller.host.scribe_announce("The sample could not be played.")

    def _watch_sample(self) -> None:
        if not self._alive():
            return
        if self.sample_playing():
            self._sample_timer = wx.CallLater(500, self._watch_sample)
        elif self._player is not None:
            self.stop_sample()

    def stop_sample(self) -> None:
        if self._player is not None:
            self._player.stop()
        if self._alive():
            self.sample.SetLabel("Play &Sample")

    # -------------------------------------------------------------- result

    def email_changed(self) -> bool:
        """True when the person changed Scribe's email from where it started."""
        return bool(self.notify.GetValue()) != bool(self._settings.notify_when_complete)

    def settings(self) -> ScribeSettings:
        language = self._value(self.language)
        dialect = self._value(self.dialect)
        voice = self._value(self.voice)
        dialects = dict(self._settings.dialects)
        voices = dict(self._settings.voices)
        if language and dialect:
            dialects[language] = dialect
        if dialect and voice:
            voices[dialect] = voice
        gender_index = max(0, self.gender.GetSelection())
        return ScribeSettings(
            language=language if self._lists.get("languages") else self._settings.language,
            dialects=dialects,
            voices=voices,
            tts_gender=TTS_GENDERS[gender_index][0],
            tts_rate=TTS_RATES[max(0, self.speed.GetSelection())][0],
            braille_translation_table=self._value(self.table)
            if self._lists.get("tables")
            else self._settings.braille_translation_table,
            braille_cells_per_line=self.cells.GetValue(),
            braille_split_into_pages=self.split.GetValue(),
            braille_lines_per_page=self.lines.GetValue(),
            large_print=self.large_print.GetValue(),
            add_image_descriptions=self.describe.GetValue(),
            math=self.math.GetValue(),
            notify_when_complete=self.notify.GetValue(),
        )


def _is_inside(window: Any, container: Any) -> bool:
    while window is not None:
        if window is container:
            return True
        window = window.GetParent()
    return False


__all__ = ["SettingsGroups"]
