"""CODEOWNERS as a table, Who Owns This?, and the problems GitHub reports (PRD 21.8).

The CODEOWNERS sheet shows the file as rows of a path pattern and its owners
in file order, because order is the whole meaning: **the last matching rule
wins**, so moving a rule down can change who reviews a folder.
:class:`CodeownersLines` keeps every line of the file (notes, blank lines and
each rule's trailing ``# note``), so editing a rule rewrites that one line
and nothing else.

**Who Owns This?** on a file or folder in the repository's files, or on any
path typed in the sheet, reads the CODEOWNERS file GitHub uses -- the first
of ``.github/CODEOWNERS``, ``CODEOWNERS`` and ``docs/CODEOWNERS`` -- and says
the winning rule, with its line, the way GitHub evaluates it
(:func:`quill.core.github.template_files.owners_for`).

**GitHub's own problems** come from ``GET /repos/{owner}/{repo}/codeowners/errors``
(the ``codeownersErrors`` list GitHub keeps for the default branch): each
line GitHub could not use, with its kind and GitHub's suggestion.

wx-free and strict-typed.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any
from urllib.parse import quote

from quill.core.github.template_files import CodeownersRule, owners_for, parse_codeowners
from quill.core.github.workbench_api import GitHubApi

__all__ = [
    "CODEOWNERS_PATHS",
    "CodeownersLines",
    "OwnersRow",
    "codeowners_errors",
    "owner_problem",
    "pattern_problem",
    "read_codeowners",
    "who_owns",
]

#: Where GitHub looks, in its order; the first one found is the one it uses.
CODEOWNERS_PATHS: tuple[str, ...] = (".github/CODEOWNERS", "CODEOWNERS", "docs/CODEOWNERS")


@dataclass(frozen=True, slots=True)
class OwnersRow:
    """One rule as a table row: its index among the file's lines, pattern, owners, note."""

    index: int
    line: int
    pattern: str
    owners: tuple[str, ...]
    note: str = ""

    def text(self) -> str:
        owners = ", ".join(self.owners) if self.owners else "no owners (nobody is asked)"
        return f"Line {self.line}: {self.pattern}, {owners}"


def pattern_problem(pattern: str) -> str:
    """Why GitHub would not use *pattern*, or ""; CODEOWNERS is not quite .gitignore."""
    if not pattern.strip():
        return "A rule needs a path pattern."
    if pattern.startswith("!"):
        return "CODEOWNERS has no ! to exclude a path; a later rule with no owners does that."
    if "[" in pattern or "]" in pattern:
        return "CODEOWNERS does not take [ ] character ranges."
    if pattern.startswith("\\#"):
        return "CODEOWNERS does not take \\# to escape a pattern starting with #."
    if any(ch.isspace() for ch in pattern):
        return "A pattern cannot contain spaces."
    return ""


def owner_problem(owner: str) -> str:
    """Why *owner* is not a CODEOWNERS owner by its shape alone, or ""."""
    if owner.startswith("@"):
        name = owner[1:]
        if not name or name.endswith("/") or name.count("/") > 1:
            return f"{owner} is not @person or @organization/team."
        return ""
    if "@" in owner and "." in owner.rsplit("@", 1)[-1]:
        return ""
    return f"{owner} is not an owner: start a person or team with @, or give an email address."


class CodeownersLines:
    """Every line of a CODEOWNERS file; rules are edited in place, notes are kept."""

    def __init__(self, text: str) -> None:
        self.lines = text.replace("\r\n", "\n").split("\n")
        if self.lines and self.lines[-1] == "":
            self.lines.pop()

    def rows(self) -> list[OwnersRow]:
        found: list[OwnersRow] = []
        for index, raw in enumerate(self.lines):
            body, _sep, note = raw.partition(" #")
            stripped = body.strip()
            if not stripped or stripped.startswith("#"):
                continue
            pattern, *owners = stripped.split()
            found.append(OwnersRow(index, index + 1, pattern, tuple(owners), note.strip()))
        return found

    @staticmethod
    def _line(pattern: str, owners: Sequence[str], note: str) -> str:
        line = " ".join([pattern.strip(), *[o.strip() for o in owners if o.strip()]])
        return f"{line} # {note}" if note else line

    def set_rule(self, row: OwnersRow, pattern: str, owners: Sequence[str]) -> None:
        self.lines[row.index] = self._line(pattern, owners, row.note)

    def add_rule(self, pattern: str, owners: Sequence[str]) -> OwnersRow:
        """A new rule at the end, where it wins over every rule before it."""
        self.lines.append(self._line(pattern, owners, ""))
        return self.rows()[-1]

    def remove_rule(self, row: OwnersRow) -> None:
        del self.lines[row.index]

    def move_rule(self, row: OwnersRow, delta: int) -> bool:
        """Swap a rule with the rule above (-1) or below (+1); notes stay where they are."""
        rows = self.rows()
        position = next((i for i, r in enumerate(rows) if r.index == row.index), -1)
        target = position + delta
        if position < 0 or not 0 <= target < len(rows):
            return False
        other = rows[target]
        self.lines[row.index], self.lines[other.index] = (
            self.lines[other.index],
            self.lines[row.index],
        )
        return True

    def text(self) -> str:
        return "\n".join(self.lines) + "\n"

    def problems(self) -> list[str]:
        """Each rule GitHub would skip, by its shape alone (no network)."""
        out: list[str] = []
        for row in self.rows():
            said = pattern_problem(row.pattern)
            if said:
                out.append(f"Line {row.line}: {said}")
            for owner in row.owners:
                said = owner_problem(owner)
                if said:
                    out.append(f"Line {row.line}: {said}")
        return out


def _status(exc: BaseException) -> int | None:
    status = getattr(exc, "status", None)
    return status if isinstance(status, int) else None


def read_codeowners(repo: Any) -> tuple[str, str]:
    """``(path, text)`` of the CODEOWNERS file GitHub uses, or ``("", "")`` when none."""
    for path in CODEOWNERS_PATHS:
        try:
            found = repo.get_contents(path)
        except Exception as exc:  # noqa: BLE001 - not there is the normal case
            if _status(exc) == 404:
                continue
            raise
        if isinstance(found, list):
            continue
        raw = getattr(found, "decoded_content", b"")
        text = raw.decode("utf-8", errors="replace") if isinstance(raw, bytes) else str(raw)
        return path, text
    return "", ""


def who_owns(where: str, text: str, path: str) -> str:
    """The sentence for *path*: the winning rule and its owners, or that nobody owns it.

    A path ending in ``/`` is a folder: the answer is for a file directly in it,
    which is what a review of a change there asks.
    """
    folder = path.strip().endswith("/")
    target = path.strip().strip("/")
    probe = f"{target}/file" if folder else target
    if folder:
        target = f"the files in {target}/"
    if not where:
        return (
            "This repository has no CODEOWNERS file, so nobody is asked to review "
            f"{target or 'anything'} by ownership."
        )
    rule: CodeownersRule | None = owners_for(text, probe)
    if rule is None:
        return f"No rule in {where} matches {target}, so nobody is asked to review it."
    rules = parse_codeowners(text)
    earlier = sum(1 for r in rules if r.line < rule.line and owners_for(f"{r.pattern} x\n", probe))
    beaten = (
        f" It wins over {earlier} earlier matching rule{'s' if earlier != 1 else ''}."
        if earlier
        else ""
    )
    if not rule.owners:
        return (
            f"Line {rule.line} of {where}, {rule.pattern}, matches {target} and names no "
            f"owners, so nobody is asked.{beaten}"
        )
    return (
        f"{', '.join(rule.owners)} own {target}: line {rule.line} of {where}, "
        f"{rule.pattern}, the last rule that matches.{beaten}"
    )


def codeowners_errors(api: GitHubApi, repository: str, ref: str = "") -> list[str]:
    """GitHub's own list of CODEOWNERS lines it could not use, as sentences.

    ``[]`` when GitHub found none; one sentence saying so when there is no
    CODEOWNERS file (GitHub answers 404).
    """
    from quill.core.github.rest_transport import GitHubRestError

    query = {"ref": ref} if ref else None
    try:
        response = api.rest(
            "GET", f"/repos/{quote(repository, safe='/')}/codeowners/errors", query=query
        )
    except GitHubRestError as exc:
        if exc.status == 404:
            return ["GitHub found no CODEOWNERS file on the default branch to check."]
        raise
    data = response.data if isinstance(response.data, dict) else {}
    out: list[str] = []
    for error in data.get("errors") or []:
        if not isinstance(error, dict):
            continue
        where = f"Line {error.get('line', '?')}"
        if error.get("column"):
            where += f", column {error['column']}"
        kind = str(error.get("kind") or "Problem")
        message = str(error.get("message") or "").strip().splitlines()
        said = f"{where}: {kind}."
        source = str(error.get("source") or "").strip()
        if source:
            said += f" The line is: {source}"
        suggestion = str(error.get("suggestion") or "").strip()
        if suggestion:
            said += f" GitHub suggests: {suggestion}"
        elif message and not source:
            said += f" {message[0]}"
        out.append(said)
    return out
