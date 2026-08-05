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
    "parse_profile",
]

_HEADING_RE = re.compile(r"^#{1,6}\s*(.+?)\s*$")
_SEP = "=>"

_VOCAB_HEADINGS = {"vocabulary", "words", "terms", "dictionary"}
_REPLACE_HEADINGS = {"replacements", "substitutions", "corrections", "replace"}
_COMMAND_HEADINGS = {"commands", "voice commands", "actions"}

_ESCAPES = (("\\n", "\n"), ("\\t", "\t"), ("\\r", "\r"))

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


def _unescape(value: str) -> str:
    for token, char in _ESCAPES:
        value = value.replace(token, char)
    return value


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
    """The user's dictation profile file (``dictation.md`` in the data dir)."""
    from quill.core.paths import app_data_dir

    return app_data_dir() / "dictation.md"


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
