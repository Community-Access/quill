"""Authored help, as records: one per node, command, field or glossary word.

F1 in the Workbench says the window's purpose, then the focused thing's
help (GitHub PRD section 7, Part D). The words live here as data, keyed by
the same ids the tree, the action table and the sheets use, so a test can
say which node or command has no help yet and the generated reference can
print them all. Provider-neutral: GitHub's words and WordPress's words are
two catalogues of the same shape.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from quill.core.workbench import WorkbenchSpecError

__all__ = ["HelpCatalogue", "HelpRecord"]


@dataclass(frozen=True)
class HelpRecord:
    """One help topic.

    *keys* are the keys that reach it or that it teaches ("Alt+Enter");
    *commands* the command ids it explains; *related* other record ids,
    which must exist in the same catalogue.
    """

    id: str
    title: str
    body: str
    keys: tuple[str, ...] = ()
    commands: tuple[str, ...] = ()
    related: tuple[str, ...] = ()

    def spoken(self) -> str:
        """Title and body as F1 says them."""
        return f"{self.title}. {self.body}" if self.body else self.title


class HelpCatalogue:
    """A provider's help, checked so a related link never leads nowhere."""

    def __init__(self, records: Sequence[HelpRecord]) -> None:
        self._records: dict[str, HelpRecord] = {}
        for record in records:
            if not record.id or not record.title:
                raise WorkbenchSpecError(f"A help record needs an id and a title: {record!r}.")
            if record.id in self._records:
                raise WorkbenchSpecError(f"Help id {record.id!r} is used twice.")
            self._records[record.id] = record
        for record in self._records.values():
            for other in record.related:
                if other not in self._records:
                    raise WorkbenchSpecError(f"{record.id} points to missing help {other!r}.")

    def __contains__(self, record_id: object) -> bool:
        return record_id in self._records

    def __len__(self) -> int:
        return len(self._records)

    def get(self, record_id: str) -> HelpRecord | None:
        return self._records.get(record_id)

    def for_command(self, command_id: str) -> HelpRecord | None:
        """The record that explains *command_id*: its own id, else one naming it."""
        own = self._records.get(command_id)
        if own is not None:
            return own
        return next((r for r in self._records.values() if command_id in r.commands), None)

    def missing(self, ids: Iterable[str]) -> tuple[str, ...]:
        """The *ids* that have no record, in the order given."""
        return tuple(record_id for record_id in ids if record_id not in self._records)

    def search(self, words: str) -> tuple[HelpRecord, ...]:
        """Records whose title or body holds every word (Search Help)."""
        terms = [word.casefold() for word in words.split() if word]
        if not terms:
            return ()
        return tuple(
            record
            for record in self._records.values()
            if all(term in f"{record.title} {record.body}".casefold() for term in terms)
        )
