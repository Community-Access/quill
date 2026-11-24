"""Convert with Scribe's dialects, voices and Play Sample (Jeff, 2026-11-23).

The part of :class:`quill.ui.scribe_convert_settings.SettingsGroups` that
fills Dialect and Voice from :mod:`quill.core.scribe.voices` and answers Play
Sample; the controls themselves are built there, in Tab order.

**Play Sample always answers** (the same test: "the play button does
nothing"): "Choose a voice to hear a sample." with no voice chosen, "<name>
has no sample." for a voice without one, "The voices are still loading." and
"The voices could not be loaded. Use Retry Loading, Alt+Y." while there are
none, and "The sample is still coming." while it downloads (never a second
download). Two quick presses say one answer.
Each is said a moment after the press (:meth:`_say`), not inside it: said
inside the key press, the screen reader's own handling of that key could
cut it off before a word was heard, which is how it went silent in QUILL
Lite.
"""

from __future__ import annotations

from typing import Any

import wx

from quill.core.scribe.model import ScribeSettings
from quill.core.scribe.voices import guess_language, suggest_dialect, voice_items

#: The first row of Language, and of Dialect, Voice and Braille table.
DETECT = "Detect automatically"
SCRIBE_DEFAULT = "Scribe's default"

#: How long after the press Play Sample's answer is said (see the module notes).
SAY_AFTER_MS = 150
NO_VOICE = "Choose a voice to hear a sample."
STILL_LOADING = "The voices are still loading."
NOT_LOADED = "The voices could not be loaded. Use Retry Loading, Alt+Y."
NOT_PLAYED = "The sample could not be played."
STILL_COMING = "The sample is still coming."


class VoiceSettingsMixin:
    """Dialect, Voice and Play Sample; mixed into ``SettingsGroups``."""

    # Built by SettingsGroups.
    language: Any
    dialect: Any
    voice: Any
    sample: Any
    _controller: Any
    _settings: ScribeSettings
    _lists: dict[str, Any]
    _player: Any
    _hints: list[str]
    _suggestion: tuple[str, str] | None
    _voice_chosen: bool
    _voice_rows: dict[str, Any]

    def _alive(self) -> bool:  # pragma: no cover - SettingsGroups'
        raise NotImplementedError

    def _set(
        self, control: Any, pairs: list[tuple[str, str]], value: str
    ) -> None:  # pragma: no cover
        raise NotImplementedError

    @staticmethod
    def _value(control: Any) -> str:  # pragma: no cover - SettingsGroups'
        raise NotImplementedError

    def settings(self) -> ScribeSettings:  # pragma: no cover - SettingsGroups'
        raise NotImplementedError

    def voice_language(self) -> str:
        """The language whose dialects and voices are shown: the one chosen, or
        for "Detect automatically" the document's or Windows' (when Scribe has it)."""
        language = self._value(self.language)
        if language:
            return language
        return guess_language(self._lists.get("dialects") or {}, self._hints)

    def _dialects(self, language: str) -> list[tuple[str, str]]:
        return list((self._lists.get("dialects") or {}).get(language, [])) if language else []

    def _fill_dialects(self) -> None:
        language = self.voice_language()
        dialects = self._dialects(language)
        chosen = self._settings.dialects.get(language, "")
        self._suggestion = None
        if not chosen:  # nothing saved: a starting suggestion, never over a saved choice
            suggested = suggest_dialect(dialects, self._hints, language)
            if suggested:
                chosen = suggested
                self._suggestion = (language, suggested)
        self._set(self.dialect, [(SCRIBE_DEFAULT, "")] + dialects, chosen)
        self._fill_voices()

    def _fill_voices(self, keep: str = "") -> None:
        """The Voice list for the dialect shown, or every dialect's when it is
        Scribe's default; *keep* is a voice to stay on when it is still listed."""
        locale = self._value(self.dialect)
        language = self.voice_language()
        items = (
            voice_items(locale, self._dialects(language), self._lists.get("voices") or {})
            if language or locale
            else []
        )
        self._voice_rows = {item.short_name: item for item in items}
        #: Every dialect's voices: a voice chosen there chooses its dialect.
        self._voices_all_dialects = not locale
        chosen = keep if keep in self._voice_rows else ""
        if not chosen:
            locales = [locale] if locale else [loc for _n, loc in self._dialects(language)]
            chosen = next(
                (
                    self._settings.voices[loc]
                    for loc in locales
                    if self._settings.voices.get(loc) in self._voice_rows
                ),
                "",
            )
        self._set(
            self.voice,
            [(SCRIBE_DEFAULT, "")] + [(item.label, item.short_name) for item in items],
            chosen,
        )

    def dialect_chosen(self) -> None:
        """The person chose a dialect: its voices, staying on the voice if it is one."""
        self._voice_chosen = True
        self._fill_voices(keep=self._value(self.voice))

    def voice_chosen(self) -> None:
        """The person chose a voice. From every dialect's list, its dialect is
        chosen too -- silently: the voice's name already said which."""
        self._voice_chosen = True
        if not getattr(self, "_voices_all_dialects", False):
            return
        # Every time, not only the first: arrowing through a closed list chooses
        # each voice in turn (accessibility review, 2026-11-23).
        item = self._voice_rows.get(self._value(self.voice))
        ids = getattr(self.dialect, "_quill_ids", [])
        locale = item.locale if item is not None else ""
        if locale in ids:
            self.dialect.SetSelection(ids.index(locale))

    def suggested(self) -> bool:
        """The dialect shown is still only this dialog's suggestion."""
        return bool(
            self._suggestion is not None
            and not self._voice_chosen
            and self._value(self.dialect) == self._suggestion[1]
        )

    # -------------------------------------------------------------- sample

    def sample_playing(self) -> bool:
        return self._player is not None and self._player.is_playing()

    def _say(self, text: str) -> None:
        """Say Play Sample's answer a moment after the press (module notes).
        A second press before then replaces the first answer, so it is said once."""
        timer = getattr(self, "_say_timer", None)
        if timer is not None and timer.IsRunning():
            timer.Stop()
        self._say_timer = wx.CallLater(SAY_AFTER_MS, self._say_now, text)

    def _say_now(self, text: str) -> None:
        if self._alive():  # never after the dialog has closed
            self._controller.host.scribe_announce(text)

    def toggle_sample(self) -> None:
        if self.sample_playing():
            self.stop_sample()
            return
        if getattr(self, "_fetching", False):
            self._say(STILL_COMING)  # never a second download
            return
        if self._lists.get("failed"):
            self._say(NOT_LOADED)
            return
        if not self._lists.get("languages"):
            self._say(STILL_LOADING)
            return
        short = self._value(self.voice)
        item = self._voice_rows.get(short)
        if not short or item is None:
            self._say(NO_VOICE)
            return
        if not item.has_sample:
            self._say(f"{item.name} has no sample.")
            return

        self._fetching = True

        def failed(_error: BaseException) -> None:
            self._fetching = False
            self._say(NOT_PLAYED)

        self._controller._background(
            lambda: self._controller.client().voice_sample(short), self._play, failed
        )

    def _play(self, data: bytes) -> None:
        from quill.ui.scribe_sample_player import SamplePlayer

        self._fetching = False
        if not self._alive():
            return
        self._player = self._player or SamplePlayer()
        if self._player.play(data):
            self.sample.SetLabel("&Stop Sample")
            # Back to Play Sample when the sample ends on its own.
            self._sample_timer = wx.CallLater(500, self._watch_sample)
        else:
            self._say(NOT_PLAYED)

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

    def remembered(self) -> ScribeSettings:
        """:meth:`settings` as this app remembers them: without a dialect that
        is still only the suggestion, so it is suggested afresh next time."""
        chosen = self.settings()
        if self.suggested() and self._suggestion is not None:
            language = self._suggestion[0]
            saved = self._settings.dialects.get(language)
            if saved:
                chosen.dialects[language] = saved
            else:
                chosen.dialects.pop(language, None)
        return chosen


__all__ = [
    "DETECT",
    "SCRIBE_DEFAULT",
    "NOT_LOADED",
    "NOT_PLAYED",
    "NO_VOICE",
    "STILL_COMING",
    "STILL_LOADING",
    "VoiceSettingsMixin",
]
