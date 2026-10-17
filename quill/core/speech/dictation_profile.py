"""User dictation profile -- a QUILL-native ``dictation.md`` (Speech S6).

Adapted from VS Code's ``dictation.md`` idea: a single, human-editable Markdown
file that teaches the recogniser *your* words. Three sections, all optional:

    ## Vocabulary
    - GitHub
    - wxPython
    - QUILL

    ## Replacements
    new line => \\n
    get hub => GitHub
    smiley => :)

    ## Commands
    save everything => file.save_all

* **Vocabulary** biases the speech engine toward these spellings, fed as
  Whisper's ``initial_prompt`` (so "wxPython" comes back capitalised, not
  "w x python"). Only engines that accept a prompt use it; the rest ignore it.
* **Replacements** are spoken->written substitutions applied to the finished
  transcript (``\\n`` / ``\\t`` escapes supported), for punctuation macros and
  fixing names the engine mishears.
* **Commands** add spoken phrases for existing voice commands, merged onto the
  built-in aliases (still constrained to the safe-tool allowlist by the caller).

Pure and wx-free: parsing, the prompt string, and the substitution pass are all
unit-tested with no engine and no microphone.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

__all__ = [
    "DictationProfile",
    "TEMPLATE",
    "default_profile_path",
    "ensure_profile_file",
    "load_profile",
    "looks_like_prose",
    "parse_profile",
]

_HEADING_RE = re.compile(r"^#{1,6}\s*(.+?)\s*$")
_SEP = "=>"

_VOCAB_HEADINGS = {"vocabulary", "words", "terms", "dictionary"}
_REPLACE_HEADINGS = {"replacements", "substitutions", "corrections", "replace"}
_COMMAND_HEADINGS = {"commands", "voice commands", "actions"}

TEMPLATE = """\
# QUILL Dictation Profile

Teach dictation your words. Every section is optional; edit and save, and QUILL
picks it up the next time you dictate.

## Vocabulary

List names, jargon, and acronyms you use so the recogniser spells them your way.

- QUILL
- wxPython
- GitHub

## Replacements

One per line, `spoken => written`. Use \\n for a new line.

new line => \\n
open paren => (
close paren => )

## Commands

Add your own spoken phrases for existing commands, `phrase => command.id`.

save everything => file.save_all
"""


@dataclass(frozen=True, slots=True)
class DictationProfile:
    """A parsed dictation profile: vocabulary, replacements, and command aliases."""

    vocabulary: tuple[str, ...] = ()
    replacements: tuple[tuple[str, str], ...] = ()
    commands: tuple[tuple[str, str], ...] = ()  # (spoken phrase, command id)
    _extra: dict[str, str] = field(default_factory=dict, compare=False)

    @property
    def is_empty(self) -> bool:
        return not (self.vocabulary or self.replacements or self.commands)

    def initial_prompt(self) -> str:
        """A Whisper ``initial_prompt`` biasing recognition toward the vocabulary.

        Empty when there is no vocabulary, so callers can pass it through
        unconditionally (an empty prompt is a no-op).
        """
        if not self.vocabulary:
            return ""
        return "Vocabulary: " + ", ".join(self.vocabulary) + "."

    def apply_replacements(self, text: str) -> str:
        """Apply the spoken->written substitutions to a finished transcript.

        Case-insensitive, whole-phrase (word-boundary) matches, applied in file
        order. The written side may contain ``\\n`` / ``\\t`` escapes.
        """
        result = text
        for spoken, written in self.replacements:
            if not spoken:
                continue
            pattern = re.compile(rf"(?<!\w){re.escape(spoken)}(?!\w)", re.IGNORECASE)

            def _replace(_match: re.Match[str], value: str = written) -> str:
                return value  # a function repl inserts the text literally (no \g escapes)

            result = pattern.sub(_replace, result)
        return result

    def command_aliases(self) -> dict[str, tuple[str, ...]]:
        """Custom phrases grouped by command id, for merging into voice commands."""
        grouped: dict[str, list[str]] = {}
        for phrase, command_id in self.commands:
            grouped.setdefault(command_id, []).append(phrase)
        return {cid: tuple(phrases) for cid, phrases in grouped.items()}


_UNESCAPED = {"n": "\n", "t": "\t", "r": "\r", "\\": "\\"}


def _unescape(value: str) -> str:
    r"""The written side of ``spoken => written``, escapes read left to right.

    ``\n``, ``\t`` and ``\r`` are a new line, a tab and a return, and ``\\`` is
    one backslash; any other backslash is kept as typed. Read in one pass, not
    with a ``replace`` per escape: that turned the ``\n`` in a replacement
    writing ``C:\new`` into a new line, and left a writer no way to keep a
    backslash before an ``n`` (found by a property test, 2026-10-17). A
    hand-written ``C:\temp`` still reads as it always did, with a tab.
    """
    if "\\" not in value:
        return value
    out: list[str] = []
    index = 0
    while index < len(value):
        char = value[index]
        if char == "\\" and index + 1 < len(value) and value[index + 1] in _UNESCAPED:
            out.append(_UNESCAPED[value[index + 1]])
            index += 2
            continue
        out.append(char)
        index += 1
    return "".join(out)


def escape_written(value: str) -> str:
    """The inverse of :func:`_unescape`: what to write after ``=>`` so that
    reading it back gives *value* exactly."""
    return (
        value.replace("\\", "\\\\").replace("\n", "\\n").replace("\t", "\\t").replace("\r", "\\r")
    )


def looks_like_prose(line: str) -> bool:
    """Whether a line under Vocabulary is explanation, not a word.

    The starter files explain each section in a sentence or two under its
    heading, and until 2026-09-28 those sentences were read as vocabulary
    ("Names, jargon and acronyms you use, spelled the way you want them." was
    a "word"). A name or a term is a few words at most and never ends a
    sentence; a sentence is longer, or ends with a full stop or a colon.
    """
    words = line.split()
    return len(words) > 4 or line.rstrip().endswith((".", ":", "!", "?"))


def _section_of(heading: str) -> str | None:
    key = heading.strip().lower()
    if key in _VOCAB_HEADINGS:
        return "vocabulary"
    if key in _REPLACE_HEADINGS:
        return "replacements"
    if key in _COMMAND_HEADINGS:
        return "commands"
    return None


def parse_profile(text: str) -> DictationProfile:
    """Parse a ``dictation.md`` document into a :class:`DictationProfile`."""
    vocabulary: list[str] = []
    replacements: list[tuple[str, str]] = []
    commands: list[tuple[str, str]] = []
    section: str | None = None
    seen_vocab: set[str] = set()

    for raw in text.splitlines():
        line = raw.strip()
        heading = _HEADING_RE.match(line)
        if heading:
            section = _section_of(heading.group(1))
            continue
        if not line or section is None:
            continue
        if line.startswith(("-", "*", "+")):
            line = line[1:].strip()
        if not line:
            continue
        if section == "vocabulary":
            if looks_like_prose(line):
                continue
            if line.lower() not in seen_vocab:
                seen_vocab.add(line.lower())
                vocabulary.append(line)
        elif section in ("replacements", "commands") and _SEP in line:
            left, right = line.split(_SEP, 1)
            left, right = left.strip(), right.strip()
            if not left:
                continue
            if section == "replacements":
                replacements.append((left, _unescape(right)))
            elif right:
                commands.append((left, right))

    return DictationProfile(
        vocabulary=tuple(vocabulary),
        replacements=tuple(replacements),
        commands=tuple(commands),
    )


def default_profile_path() -> Path:
    """The family's word list (``dictation.md`` in the family's dictation folder).

    Until 2026-10-16 it was in QUILL's data folder; the first call copies it,
    and its two neighbours, from there (dict.md D-12/D-13,
    :mod:`quill.core.windows_dictation.family_words`). The old file is left as
    it was."""
    from quill.core.paths import app_data_dir
    from quill.core.windows_dictation.family_words import family_profile_path

    return family_profile_path(app_data_dir())


def ensure_profile_file(path: Path | str | None = None) -> Path:
    """Return the profile path, writing the starter :data:`TEMPLATE` if absent.

    Lets a menu command ("Edit Dictation Profile...") open a ready-to-edit file
    the first time, instead of a blank one.
    """
    target = Path(path) if path is not None else default_profile_path()
    if not target.exists():
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(TEMPLATE, encoding="utf-8")
    return target


def load_profile(path: Path | str | None = None) -> DictationProfile:
    """Load and parse the dictation profile, or an empty one when absent.

    Never raises: a missing or unreadable file yields an empty profile so
    dictation works exactly as before when the user has not made one.
    """
    target = Path(path) if path is not None else default_profile_path()
    try:
        if not target.is_file():
            return DictationProfile()
        return parse_profile(target.read_text(encoding="utf-8", errors="replace"))
    except OSError:
        return DictationProfile()
