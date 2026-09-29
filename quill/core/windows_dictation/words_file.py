"""``dictation.md`` as three lists a window can edit, instead of a file to hand-edit.

The file format is unchanged (:mod:`quill.core.speech.dictation_profile`),
so anyone who did edit it by hand loses nothing, and QUILL's Locked
Dictation keeps reading the same file. What this adds is a model with three
kinds of entry -- **words** (Vocabulary), **phrases** (Replacements: say
this, write that) and **corrections** (a "Corrections" section: heard this,
write that) -- and a writer that puts them back in that shape.

Phrases and corrections are the same mechanism at recognition time (the
parser folds both headings into ``replacements``, applied case-insensitively
on word boundaries). They are kept apart in the file and the window because
they are different things to a person: a phrase is a shortcut you *say on
purpose*, a correction is what the engine *keeps getting wrong*. Listing "quill
light writes QUILL Lite" under "your own phrases" would tell someone to say
"quill light".

Saving rewrites the whole file from the model: the explanatory text is
regenerated, a ``## Commands`` section (QUILL-only, parsed but unused here) is
carried across verbatim, and anything else is dropped -- the window is the
editor now. wx-free.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from quill.core.speech.dictation_profile import _HEADING_RE, _SEP, _section_of, looks_like_prose

__all__ = ["Entry", "WordsFile", "load_words", "save_words"]

_CORRECTION_HEADINGS = {"corrections"}
_ESCAPES = (("\n", "\\n"), ("\t", "\\t"), ("\r", "\\r"))
_UNESCAPES = tuple((token, char) for char, token in _ESCAPES)


@dataclass(frozen=True, slots=True)
class Entry:
    """One line of the file: a word, a phrase, or a correction."""

    kind: str  # "word" | "phrase" | "correction"
    spoken: str  # the word itself, the phrase you say, or what was heard
    written: str = ""  # what it writes (empty for a word)

    def label(self) -> str:
        """One line for a list: the kind, then the entry in plain words."""
        if self.kind == "word":
            return f"Word: {self.spoken}"
        writes = self.written.replace("\n", " (new line) ").replace("\t", " (tab) ")
        if self.kind == "phrase":
            return f"Phrase: say {self.spoken}, writes {writes}"
        return f"Correction: heard {self.spoken}, write {writes}"


@dataclass
class WordsFile:
    """The three lists, plus any Commands section carried across untouched."""

    words: list[str] = field(default_factory=list)
    phrases: list[tuple[str, str]] = field(default_factory=list)
    corrections: list[tuple[str, str]] = field(default_factory=list)
    commands_lines: list[str] = field(default_factory=list)

    def entries(self) -> list[Entry]:
        """Every entry, words first, then phrases, then corrections."""
        out = [Entry("word", w) for w in self.words]
        out += [Entry("phrase", s, w) for s, w in self.phrases]
        out += [Entry("correction", s, w) for s, w in self.corrections]
        return out

    def add(self, entry: Entry) -> bool:
        """Add *entry*; ``False`` (and nothing changes) for a duplicate or a blank."""
        spoken = " ".join(entry.spoken.split())
        if not spoken:
            return False
        if entry.kind == "word":
            if any(w.lower() == spoken.lower() for w in self.words):
                return False
            self.words.append(spoken)
            return True
        written = entry.written.strip("\r\n")
        if not written:
            return False
        target = self.phrases if entry.kind == "phrase" else self.corrections
        if any(s.lower() == spoken.lower() for s, _w in target):
            return False
        target.append((spoken, written))
        return True

    def remove(self, entry: Entry) -> bool:
        if entry.kind == "word":
            before = len(self.words)
            self.words = [w for w in self.words if w != entry.spoken]
            return len(self.words) != before
        target = self.phrases if entry.kind == "phrase" else self.corrections
        kept = [(s, w) for s, w in target if s != entry.spoken]
        changed = len(kept) != len(target)
        if entry.kind == "phrase":
            self.phrases = kept
        else:
            self.corrections = kept
        return changed

    def replace(self, old: Entry, new: Entry) -> bool:
        """Edit in place: *old* becomes *new*, keeping its position."""
        if old.kind != new.kind:
            return self.remove(old) and self.add(new)
        spoken = " ".join(new.spoken.split())
        if not spoken:
            return False
        if new.kind == "word":
            if spoken.lower() != old.spoken.lower() and any(
                w.lower() == spoken.lower() for w in self.words
            ):
                return False
            self.words = [spoken if w == old.spoken else w for w in self.words]
            return True
        written = new.written.strip("\r\n")
        if not written:
            return False
        target = self.phrases if new.kind == "phrase" else self.corrections
        if spoken.lower() != old.spoken.lower() and any(
            s.lower() == spoken.lower() for s, _w in target
        ):
            return False
        edited = [(spoken, written) if s == old.spoken else (s, w) for s, w in target]
        if new.kind == "phrase":
            self.phrases = edited
        else:
            self.corrections = edited
        return True


def _unescape(value: str) -> str:
    for token, char in _UNESCAPES:
        value = value.replace(token, char)
    return value


def _escape(value: str) -> str:
    for char, token in _ESCAPES:
        value = value.replace(char, token)
    return value


def parse_words(text: str) -> WordsFile:
    """The file's three lists. Tolerant of the same headings the profile parser takes."""
    result = WordsFile()
    section: str | None = None
    seen: set[str] = set()
    for raw in text.splitlines():
        line = raw.strip()
        heading = _HEADING_RE.match(line)
        if heading:
            name = heading.group(1).strip().lower()
            if name in _CORRECTION_HEADINGS:
                section = "corrections"
            else:
                section = _section_of(heading.group(1))
            continue
        if section == "commands":
            if line:
                result.commands_lines.append(raw.rstrip())
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
            if line.lower() not in seen:
                seen.add(line.lower())
                result.words.append(line)
        elif _SEP in line:
            left, right = line.split(_SEP, 1)
            left, right = left.strip(), right.strip()
            if not left:
                continue
            pair = (left, _unescape(right))
            (result.corrections if section == "corrections" else result.phrases).append(pair)
    return result


def render_words(words: WordsFile) -> str:
    """The file, regenerated: three sections, each explained in a sentence."""
    lines = [
        "# My dictation words and phrases",
        "",
        "Kept up to date by My Words and Phrases in Dictation Settings. You can",
        "also edit it by hand; the next phrase you dictate uses it either way.",
        "",
        "## Vocabulary",
        "",
        "Names, jargon and acronyms, spelled the way you want them. When the speech",
        "engine writes something that sounds or looks close, it is corrected to this.",
        "",
    ]
    lines += [f"- {word}" for word in words.words]
    lines += [
        "",
        "## Replacements",
        "",
        "Your own spoken phrases: say the words on the left and dictation writes",
        "the text on the right. \\n is a new line and \\t a tab.",
        "",
    ]
    lines += [f"{spoken} {_SEP} {_escape(written)}" for spoken, written in words.phrases]
    lines += [
        "",
        "## Corrections",
        "",
        "What the engine keeps hearing wrong, and what to write instead.",
        "",
    ]
    lines += [f"{heard} {_SEP} {_escape(written)}" for heard, written in words.corrections]
    if words.commands_lines:
        lines += ["", "## Commands", ""] + words.commands_lines
    return "\n".join(lines).rstrip("\n") + "\n"


def load_words(path: Path) -> WordsFile:
    """The lists at *path*; empty lists for a missing or unreadable file."""
    try:
        return parse_words(path.read_text(encoding="utf-8", errors="replace"))
    except OSError:
        return WordsFile()


def save_words(path: Path, words: WordsFile) -> None:
    """Write *words* back. Raises ``OSError`` for the caller to say out loud."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_words(words), encoding="utf-8")
