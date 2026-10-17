"""Named profiles and format-aware structure, on the controller (D-23).

The profiles themselves are :mod:`~quill.core.windows_dictation.profiles`'s;
their pause, fillers and punctuation reach the controller through
:class:`~quill.core.windows_dictation.preferences.DictationPreferences`. What
this mixin adds is everything a profile changes about *writing*:

* **Headings by structure.** "heading two" said at the start of a phrase:
  ``markdown`` types ``## `` as it always has; ``formatted`` starts the line,
  writes the words, and then applies Heading 2 through the editor's own
  command when the document holds formatting (the document port's optional
  ``formatting()`` and ``apply_style()``), or types nothing for it and says
  :data:`~quill.core.windows_dictation.profiles.HEADING_REFUSAL`; ``plain``
  starts the line and writes the words, nothing else.
* **Bold and italic by voice** ("bold that", "italic that"): the selection, or
  the phrase dictated last. ``markdown`` puts the marks round it (in another
  program, by retyping the session's own last phrase, as "capitalize that"
  does); ``formatted`` uses the editor's own Bold or Italic; ``plain`` says it
  writes plain text. One undo step either way.
* **Switching by voice** ("QUILL email mode"), refused out loud while Lock
  Profile is on; the host keeps the choice (the feedback port's optional
  ``set_dictation_profile``).
* **The status cell** names a profile other than Standard beside the modes, so
  a braille display shows it; it is not spoken again (GATE-13).

Kept out of :mod:`~quill.core.windows_dictation.controller`, which is at its
size ceiling: the controller only lists this mixin first among its bases, and
the four hooks below wrap the voice-command mixin's own.

wx-free.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from quill.core.windows_dictation.history import DictatedPhrase
from quill.core.windows_dictation.parser import ParsedPhrase, Piece
from quill.core.windows_dictation.profiles import (
    FORMAT_REFUSAL,
    HEADING_REFUSAL,
    PLAIN_REFUSAL,
    profile_by_id,
)
from quill.core.windows_dictation.vocabulary import Command, Glue, Mark

if TYPE_CHECKING:
    from quill.core.windows_dictation.preferences import DictationPreferences

__all__ = ["PROFILE_COMMANDS", "ProfileMixin", "heading_level"]

#: Each profile command, and the profile it chooses.
PROFILE_COMMANDS: dict[Command, str] = {
    Command.PROFILE_STANDARD: "standard",
    Command.PROFILE_EMAIL: "email",
    Command.PROFILE_DOCUMENT: "document",
    Command.PROFILE_MARKDOWN: "markdown",
    Command.PROFILE_CHAT: "chat",
    Command.PROFILE_CODING: "coding",
    Command.PROFILE_VERBATIM: "verbatim",
}
_STYLES = {
    Command.BOLD_THAT: ("bold", "**", "Bold"),
    Command.ITALIC_THAT: ("italic", "*", "Italic"),
}


def heading_level(mark: Mark | None) -> int:
    """The heading level a mark writes ("## " is 2), or 0 when it is not one."""
    if mark is None or mark.glue is not Glue.LINE_START or not mark.text.startswith("#"):
        return 0
    return len(mark.text.strip())


def _line_only(mark: Mark) -> Mark:
    """*mark* starting its line and writing nothing of its own."""
    return Mark(mark.phrase, "", Glue.LINE_START, mark.ends_sentence, mark.spoken, mark.group)


class ProfileMixin:
    """Profiles, headings by structure, and bold and italic by voice."""

    _document: Any
    _feedback: Any
    history: Any

    #: A heading said in the phrase being written: its level, 0 for none.
    _pending_heading = 0

    # Provided further along the controller's bases (this mixin comes first,
    # so it must not define them): ``_say`` and ``_preferences`` by the
    # controller, ``_last_intact`` by editing.py.
    _say: Callable[[str], None]
    _preferences: Callable[[], DictationPreferences]
    _last_intact: Callable[[], DictatedPhrase | None]

    # -- the status cell ------------------------------------------------------- #

    @property
    def mode_text(self) -> str:
        modes = str(super().mode_text)  # type: ignore[misc]
        try:
            profile = profile_by_id(self._preferences().named_profile)
        except Exception:  # noqa: BLE001 - a status line is never worth a failure
            return modes
        if profile.id == "standard":
            return modes
        return ", ".join(part for part in (f"{profile.name} profile", modes) if part)

    # -- switching -------------------------------------------------------------- #

    def _mode_command(self, parsed: ParsedPhrase, preferences: DictationPreferences) -> bool:
        chosen = PROFILE_COMMANDS.get(parsed.command)  # type: ignore[arg-type]
        if chosen is None:
            return bool(super()._mode_command(parsed, preferences))  # type: ignore[misc]
        self.use_profile(chosen, by_voice=True)
        return True

    def use_profile(self, profile_id: str, *, by_voice: bool = False) -> None:
        """Switch to *profile_id* from the next phrase on, and say so once."""
        preferences = self._preferences()
        current = profile_by_id(preferences.named_profile)
        profile = profile_by_id(profile_id)
        if by_voice and preferences.profile_locked:
            self._say(f"Lock Profile is on, so the profile stays {current.name}.")
            return
        setter = getattr(self._feedback, "set_dictation_profile", None)
        if not callable(setter):
            self._say("Choose a dictation profile in Dictation Settings.")
            return
        setter(profile.id)
        self._say(f"{profile.name} profile.")

    # -- headings by structure --------------------------------------------------- #

    def _in_mode(self, pieces: tuple[Piece, ...]) -> tuple[Piece, ...]:
        pieces = super()._in_mode(pieces)  # type: ignore[misc]
        self._pending_heading = 0
        structure = self._preferences().structure
        if structure == "markdown":
            return pieces
        out = []
        for piece in pieces:
            level = heading_level(piece.mark)
            if level and piece.mark is not None:
                self._pending_heading = level
                piece = Piece(piece.text, _line_only(piece.mark), piece.verbatim)
            out.append(piece)
        return tuple(out)

    def _after_phrase(self) -> None:
        super()._after_phrase()  # type: ignore[misc]
        level, self._pending_heading = self._pending_heading, 0
        if not level or self._preferences().structure != "formatted":
            return  # plain: the words on their own line, and nothing to say
        phrase = self.history.peek()
        said = None
        if phrase is not None and self._formatting():
            said = self._apply_style(f"heading_{level}", phrase.end, phrase.end)
        if said is None:
            self._feedback.say(HEADING_REFUSAL)
            self._feedback.show(HEADING_REFUSAL)

    # -- bold and italic ---------------------------------------------------------- #

    def _voice_command(self, parsed: ParsedPhrase, preferences: DictationPreferences) -> bool:
        if parsed.command not in _STYLES:
            return bool(super()._voice_command(parsed, preferences))  # type: ignore[misc]
        style, marks, label = _STYLES[parsed.command]  # type: ignore[index]
        if preferences.structure == "plain":
            self._say(PLAIN_REFUSAL)
            return True
        if preferences.structure == "formatted" and not self._formatting():
            self._say(FORMAT_REFUSAL)
            return True
        start, end = self._document.selection()
        latest = None
        if start == end:
            latest = self._last_intact()
            if latest is None:
                return True  # it said why
            start, end = latest.start, latest.end
        words = " ".join(self._document.text_between(start, end).split())
        if preferences.structure == "formatted":
            said = self._apply_style(style, start, end)
            if said is None:
                self._say(FORMAT_REFUSAL)
            elif said:
                self._say(said)
            return True
        text = self._document.text_between(start, end)
        core = text.strip()
        lead, tail = text[: len(text) - len(text.lstrip())], text[len(text.rstrip()) :]
        try:
            new_start, new_end = self._document.replace(
                start, end, f"{lead}{marks}{core}{marks}{tail}"
            )
        except OSError:
            self._say("The focus has moved, so nothing was changed.")
            return True
        if latest is not None:
            changed = self._document.text_between(new_start, new_end)
            self.history.replace_last(DictatedPhrase(changed, new_start, new_end))
        self._say(f"{label}: {words}" if words else f"{label}.")
        return True

    def _formatting(self) -> str:
        """What formatting the document holds: ``rich``, ``markdown``, ``html``, or ``""``."""
        formatting = getattr(self._document, "formatting", None)
        try:
            return str(formatting()) if callable(formatting) else ""
        except Exception:  # noqa: BLE001 - treat a failing question as "none"
            return ""

    def _apply_style(self, style: str, start: int, end: int) -> str | None:
        """The editor's own command over ``start..end``: ``None`` when it could not,
        else what to say ("" when the editor said it itself)."""
        apply = getattr(self._document, "apply_style", None)
        if not callable(apply):
            return None
        try:
            result = apply(style, start, end)
        except Exception:  # noqa: BLE001 - the formatting failed; the words stand
            return None
        return None if result is None else str(result)
