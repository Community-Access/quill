"""Issues in, from a spreadsheet or from lines of text (GitHub PRD 22.7).

- **Import Issues from a Spreadsheet**: a CSV file or an Excel workbook, the
  first row naming the columns. Columns are matched by name, with the usual
  other names (Summary for Title, Description for Body, Tags for Labels,
  Owner for Assignees, Issue Type for Type); a column that matches nothing is
  said, not guessed at. :func:`import_plan` gives a sentence per row and the
  reason any row is skipped, before anything is sent.
- **New Issues from Lines**: each line of the editor's selection one issue,
  its list marker or check box taken off (:func:`titles_from_lines`), and,
  if asked, each a sub-issue of a parent.

:func:`issue_payload` is the body GitHub's create-issue request takes, with a
milestone named by its title turned into its number. Nothing here talks to
the network; the Workbench sends the requests and reports a sentence a row.

wx-free and strict-typed.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass

from quill.core.workbench.spreadsheet import header_name

__all__ = [
    "IMPORT_FIELDS",
    "IssueImportRow",
    "import_mapping",
    "import_plan",
    "issue_payload",
    "mapping_lines",
    "split_names",
    "titles_from_lines",
]

#: The fields an imported issue can fill, in the order the preview names them.
IMPORT_FIELDS = ("title", "body", "labels", "assignees", "milestone", "type")
SYNONYMS: dict[str, str] = {
    "name": "title",
    "summary": "title",
    "subject": "title",
    "issue": "title",
    "description": "body",
    "details": "body",
    "text": "body",
    "label": "labels",
    "tags": "labels",
    "tag": "labels",
    "assignee": "assignees",
    "owner": "assignees",
    "owners": "assignees",
    "issue type": "type",
    "kind": "type",
}
#: GitHub's own limit on an issue title.
TITLE_LIMIT = 256
_MARKER = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+(?:\[[ xX]\]\s+)?")


@dataclass(frozen=True)
class IssueImportRow:
    """One row of the plan: its spreadsheet row number, its fields, and why not."""

    number: int
    fields: Mapping[str, str]
    problem: str = ""

    @property
    def title(self) -> str:
        return self.fields.get("title", "")

    @property
    def sentence(self) -> str:
        if self.problem:
            return f"Row {self.number}: skipped, {self.problem}"
        extras = []
        for name in ("labels", "assignees", "milestone", "type"):
            if self.fields.get(name):
                extras.append(f"{name} {self.fields[name]}")
        tail = f" ({'; '.join(extras)})" if extras else ""
        return f"Row {self.number}: {self.title}{tail}"


def import_mapping(headers: Iterable[str]) -> tuple[dict[str, str], list[str]]:
    """Each column the import uses and the field it fills; the columns left out."""
    mapping: dict[str, str] = {}
    ignored: list[str] = []
    for header in headers:
        clean = header_name(header)
        name = clean if clean in IMPORT_FIELDS else SYNONYMS.get(clean, "")
        if name and name not in mapping.values():
            mapping[clean] = name
        elif clean:
            ignored.append(clean)
    return mapping, ignored


def mapping_lines(mapping: Mapping[str, str], ignored: Sequence[str]) -> list[str]:
    """The mapping as the preview's first lines."""
    lines = [f"Column {column} fills {name}." for column, name in mapping.items()]
    if ignored:
        lines.append(f"Left out, matching no field: {', '.join(ignored)}.")
    if "title" not in mapping.values():
        lines.append("No column is the title, so nothing can be made. Name one Title.")
    return lines


def import_plan(
    rows: Sequence[Mapping[str, str]],
    *,
    milestones: Iterable[str] = (),
    numbers: Sequence[int] = (),
) -> list[IssueImportRow]:
    """The preview: one row each, with the reason any row is left out.

    *milestones* are the repository's milestone titles; a row naming another
    is skipped, because GitHub would refuse it. *numbers* are the rows'
    numbers in the spreadsheet (:func:`~quill.core.workbench.spreadsheet.numbered_rows`);
    without them, rows count from 2, the header being row 1.
    """
    mapping, _ignored = import_mapping(rows[0].keys() if rows else ())
    known = {title.casefold() for title in milestones}
    plan: list[IssueImportRow] = []
    numbered = numbers or range(2, len(rows) + 2)
    for number, row in zip(numbered, rows, strict=True):
        fields = {
            mapping[header_name(key)]: value.strip()
            for key, value in row.items()
            if header_name(key) in mapping
        }
        title = fields.get("title", "")
        if not title:
            problem = "it has no title."
        elif len(title) > TITLE_LIMIT:
            problem = f"its title is longer than GitHub's {TITLE_LIMIT} characters."
        elif fields.get("milestone") and fields["milestone"].casefold() not in known:
            problem = f"this repository has no milestone called {fields['milestone']}."
        else:
            problem = ""
        plan.append(IssueImportRow(number, fields, problem))
    return plan


def split_names(text: str) -> list[str]:
    """Labels or assignees written with commas or semicolons, without @ signs."""
    return [part.strip().lstrip("@") for part in re.split(r"[,;]", text) if part.strip()]


def issue_payload(
    row: IssueImportRow, milestone_numbers: Mapping[str, int] | None = None
) -> dict[str, object]:
    """The body of ``POST /repos/{owner}/{repo}/issues`` for *row*."""
    fields = row.fields
    payload: dict[str, object] = {"title": fields["title"]}
    if fields.get("body"):
        payload["body"] = fields["body"]
    if fields.get("labels"):
        payload["labels"] = split_names(fields["labels"])
    if fields.get("assignees"):
        payload["assignees"] = split_names(fields["assignees"])
    if fields.get("milestone") and milestone_numbers:
        numbers = {title.casefold(): number for title, number in milestone_numbers.items()}
        number = numbers.get(fields["milestone"].casefold())
        if number is not None:
            payload["milestone"] = number
    if fields.get("type"):
        payload["type"] = fields["type"]
    return payload


def titles_from_lines(text: str) -> list[str]:
    """One title per non-blank line, without its list marker or check box."""
    titles: list[str] = []
    for line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        title = _MARKER.sub("", line).strip()
        if title:
            titles.append(title[:TITLE_LIMIT])
    return titles
