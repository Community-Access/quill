"""Import and export My Words and Phrases, and the shared family list (dict.md D-12).

**Two formats, chosen by the file's extension.**

* ``.md`` -- the same Markdown ``dictation.md`` is (:mod:`words_file`), so an
  exported file is a word list any copy of QUILL, QUILL Lite or QUILL
  Transcribe can take back, and a person can read or edit it as text.
* ``.csv`` -- ``say,write`` columns, for a spreadsheet. A third column,
  ``kind`` (``word``, ``phrase`` or ``correction``), keeps the three lists
  apart; it is optional on import. Without it a row with nothing to write is
  a word and any other row a phrase. A row's ``write`` keeps its real line
  breaks (CSV quotes them), so nothing is escaped by hand.

**Import merges; it never replaces.** Each entry in the file is one of:
new (added at the end of its list), already there (same kind, same text), or
different from yours (same word or same spoken phrase, other spelling or
other text): yours is kept and the count says so. Nothing is written until
the person has seen the counts and said yes, and the list as it was is copied
to ``dictation-before-import.md`` beside it first, so one import can always
be taken back.

Export then import into an empty list gives back the same file, byte for
byte (the acceptance test in dict.md D-12), including a ``## Commands``
section, which is adopted only when the list has none of its own.

**The shared list** (:class:`SharedWords`): QUILL, QUILL Transcribe and Quill
Inkwell already read one ``dictation.md``, QUILL's. QUILL Lite keeps its own
unless the person checks "Use the shared word list" in My Words and Phrases;
its own words are then merged into the shared list the same way an import is.
A portable copy is never offered it, so a USB stick stays self-contained.

wx-free.
"""

from __future__ import annotations

import csv
import io
import shutil
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from quill.core.error_codes import CodedError
from quill.core.windows_dictation.words_file import Entry, WordsFile, parse_words, render_words

__all__ = [
    "BACKUP_NAME",
    "CSV_COLUMNS",
    "MergePlan",
    "SharedWords",
    "WordsImportError",
    "apply_merge",
    "back_up",
    "count_phrase",
    "export_words",
    "plan_merge",
    "preview_sentence",
    "read_import",
    "render_csv",
    "summary_sentence",
]

#: The column order an exported CSV uses, and the header it writes.
CSV_COLUMNS = ("say", "write", "kind")
#: The copy of the list taken before an import changes it.
BACKUP_NAME = "dictation-before-import.md"
_MARKDOWN = {".md", ".markdown", ".txt"}
_KINDS = {"word", "phrase", "correction"}


class WordsImportError(CodedError):
    """A file could not be imported as a word list. The message is a sentence."""

    code = "QUILL-DICTATION-WORDS-IMPORT"


@dataclass
class MergePlan:
    """What an import would do, before it does it."""

    new: list[Entry] = field(default_factory=list)
    already: list[Entry] = field(default_factory=list)
    #: (the file's entry, yours) -- same word or spoken phrase, different text.
    different: list[tuple[Entry, Entry]] = field(default_factory=list)
    commands_lines: list[str] = field(default_factory=list)

    @property
    def total(self) -> int:
        return len(self.new) + len(self.already) + len(self.different)


@dataclass(frozen=True)
class SharedWords:
    """QUILL Lite's choice between its own list and the family's shared one."""

    own_path: Path
    shared_path: Path
    is_on: Callable[[], bool]
    set_on: Callable[[bool], None]

    def current_path(self) -> Path:
        return self.shared_path if self.is_on() else self.own_path


# -- counting in words ----------------------------------------------------------


def count_phrase(entries: list[Entry]) -> str:
    """ "12 words", "1 phrase", "3 entries" -- the noun the kinds deserve."""
    count = len(entries)
    kinds = {entry.kind for entry in entries}
    noun = next(iter(kinds)) if len(kinds) == 1 else "entry"
    if count == 1:
        return f"1 {noun}"
    return f"{count} {'entries' if noun == 'entry' else noun + 's'}"


def summary_sentence(plan: MergePlan) -> str:
    """What an import did: "Imported 12 words, 3 already there."."""
    parts = [f"Imported {count_phrase(plan.new)}" if plan.new else "Imported nothing new"]
    if plan.already:
        parts.append(f"{len(plan.already)} already there")
    if plan.different:
        verb = "differs" if len(plan.different) == 1 else "differ"
        parts.append(f"{len(plan.different)} {verb} from yours and yours were kept")
    return ", ".join(parts) + "."


def preview_sentence(plan: MergePlan, *, verb: str = "added") -> str:
    """The question before an import: what will happen, in counts."""
    parts = [f"{count_phrase(plan.new)} will be {verb}."]
    if plan.already:
        parts.append(f"{len(plan.already)} already in your list.")
    if plan.different:
        noun = "entry differs" if len(plan.different) == 1 else "entries differ"
        parts.append(f"{len(plan.different)} {noun} from yours; yours will be kept.")
    return " ".join(parts)


# -- export ---------------------------------------------------------------------


def render_csv(words: WordsFile) -> str:
    """The list as ``say,write,kind`` rows under a header row."""
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\r\n")
    writer.writerow(CSV_COLUMNS)
    for entry in words.entries():
        writer.writerow((entry.spoken, entry.written, entry.kind))
    return buffer.getvalue()


def export_words(words: WordsFile, path: Path) -> int:
    """Write *words* to *path* in the format its extension names; the entry count.

    Raises ``OSError`` for the caller to say out loud.
    """
    if path.suffix.lower() == ".csv":
        # A byte-order mark so a spreadsheet reads accented names correctly.
        path.write_text(render_csv(words), encoding="utf-8-sig", newline="")
    else:
        path.write_text(render_words(words), encoding="utf-8", newline="\n")
    return len(words.entries())


# -- import ---------------------------------------------------------------------


def _decode(data: bytes) -> str:
    try:
        return data.decode("utf-8-sig")
    except UnicodeDecodeError:
        # A spreadsheet's "CSV" on Windows is often the ANSI code page.
        return data.decode("cp1252", errors="replace")


def _parse_csv(text: str) -> WordsFile:
    rows = [row for row in csv.reader(io.StringIO(text, newline="")) if any(c.strip() for c in row)]
    if not rows:
        return WordsFile()
    header = [cell.strip().lower() for cell in rows[0]]
    if "say" in header:
        say_at = header.index("say")
        write_at = header.index("write") if "write" in header else None
        kind_at = header.index("kind") if "kind" in header else None
        rows = rows[1:]
    else:
        say_at, write_at, kind_at = 0, 1, 2
    words = WordsFile()
    for row in rows:

        def cell(index: int | None, row: list[str] = row) -> str:
            return row[index] if index is not None and index < len(row) else ""

        say = cell(say_at).strip()
        write = cell(write_at)
        kind = cell(kind_at).strip().lower()
        if kind not in _KINDS:
            kind = "phrase" if write.strip() else "word"
        words.add(Entry(kind, say, write if kind != "word" else ""))
    return words


def read_import(path: Path) -> WordsFile:
    """The word list in *path*, ``.md`` or ``.csv``.

    Raises :class:`WordsImportError` with a sentence when the file cannot be
    read, is another kind of file, or holds no words, phrases or corrections.
    """
    suffix = path.suffix.lower()
    if suffix != ".csv" and suffix not in _MARKDOWN:
        raise WordsImportError(
            f"{path.name} is not a word list. Choose a Markdown file (.md) "
            "exported from My Words and Phrases, or a CSV file with say and write columns."
        )
    try:
        text = _decode(path.read_bytes())
    except OSError as error:
        raise WordsImportError(
            f"{path.name} could not be read. {error.strerror or error}"
        ) from error
    words = _parse_csv(text) if suffix == ".csv" else parse_words(text)
    if not words.entries():
        where = (
            "a header row of say and write, then one row each"
            if suffix == ".csv"
            else "Vocabulary, Replacements or Corrections headings"
        )
        raise WordsImportError(
            f"No words, phrases or corrections were found in {path.name}. A word list has {where}."
        )
    return words


def _key(entry: Entry) -> tuple[str, str]:
    group = "word" if entry.kind == "word" else entry.kind
    return group, entry.spoken.lower()


def plan_merge(current: WordsFile, incoming: WordsFile) -> MergePlan:
    """Sort every entry in *incoming* into new, already there, or different."""
    plan = MergePlan()
    known: dict[tuple[str, str], Entry] = {_key(e): e for e in current.entries()}
    for entry in incoming.entries():
        mine = known.get(_key(entry))
        if mine is None:
            plan.new.append(entry)
            known[_key(entry)] = entry
        elif mine.spoken == entry.spoken and mine.written == entry.written:
            plan.already.append(entry)
        elif mine in plan.new:
            plan.already.append(entry)  # the file repeats itself; count it once
        else:
            plan.different.append((entry, mine))
    if not current.commands_lines:
        plan.commands_lines = list(incoming.commands_lines)
    return plan


def apply_merge(current: WordsFile, plan: MergePlan) -> int:
    """Add the plan's new entries to *current*; how many went in."""
    added = sum(1 for entry in plan.new if current.add(entry))
    if plan.commands_lines and not current.commands_lines:
        current.commands_lines = list(plan.commands_lines)
    return added


def back_up(path: Path) -> Path | None:
    """Copy *path* to :data:`BACKUP_NAME` beside it; ``None`` when there is no file yet.

    Raises ``OSError`` for the caller to say out loud.
    """
    if not path.is_file():
        return None
    backup = path.with_name(BACKUP_NAME)
    shutil.copyfile(path, backup)
    return backup
