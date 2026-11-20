"""A sheet's typed values as GitHub wants them, before anything is sent (GitHub PRD 15.3).

A Properties sheet's number box is a text box, so what comes back from it is
the text "2", while GitHub answers (and the sheet loaded) the number 2. Left
as text, a number would be sent as a string and the re-read after the save
would never match it, so every number field would say "did not change" even
when it had. :func:`as_sent` turns each change into the value its field kind
means: a whole number for a number field (an emptied box is 0, which is how
GitHub turns off an approvals count or a wait timer), and everything else as
it is. A number that is not one stops the save with a sentence, before
anything is sent.

Some fields GitHub will not hold empty: a title, a name, a tag, the branch a
pull request merges into, a retention period. Emptying one is never sent
(GitHub would refuse it, or worse, read it as something else); the sheet
leaves it as it is and says why (:func:`emptied_refusal`).

wx-free and strict-typed; the engine (:mod:`quill.core.github.sheet_engine`)
and batches (:mod:`quill.core.github.batch`) both call it.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import replace

from quill.core.error_codes import CodedError
from quill.core.workbench.properties import FieldChange, FieldKind, SheetSpec, Value

__all__ = ["EmptyValueError", "NEVER_EMPTY", "NotANumberError", "as_sent", "emptied_refusal"]

#: Fields GitHub needs a value in, by (sheet kind, field), with a sentence where
#: the plain one ("Title cannot be empty on GitHub, ...") would not say why.
NEVER_EMPTY: dict[tuple[str, str], str] = {
    ("pull_request", "base"): (
        "A pull request always merges into a branch, so Into branch was left as it is."
    ),
    ("issue", "title"): "",
    ("pull_request", "title"): "",
    ("repository", "name"): "",
    ("repository", "default_branch"): "",
    ("label", "name"): "",
    ("milestone", "title"): "",
    ("branch", "name"): "",
    ("ruleset", "name"): "",
    ("release", "tag"): "",
    ("release_asset", "name"): "",
    ("team", "name"): "",
    ("discussion", "title"): "",
    ("project", "title"): "",
    ("issue_type", "name"): "",
    ("webhook", "address"): "",
    ("comment", "body"): "",
    ("repository", "retention_days"): "",
    ("organization", "org_retention_days"): "",
    ("team", "review_count"): "",
}


class EmptyValueError(CodedError):
    """A field GitHub needs a value in was emptied; the message says so."""

    code = "QUILL-GITHUB-SHEET-EMPTY-VALUE"


class NotANumberError(CodedError):
    """A number field holds text that is not a whole number; the message says which."""

    code = "QUILL-GITHUB-SHEET-NOT-A-NUMBER"


def _number(label: str, value: Value) -> Value:
    if not isinstance(value, str):
        return value
    text = value.strip()
    if not text:
        return 0
    try:
        return int(text)
    except ValueError:
        raise NotANumberError(f"{label} must be a whole number, such as 2.") from None


def emptied_refusal(kind: str, change: FieldChange) -> str:
    """The sentence when *change* empties a field GitHub needs a value in; else empty."""
    if (kind, change.key) not in NEVER_EMPTY:
        return ""
    after = change.after
    if after not in (None, "") and not (isinstance(after, str) and not after.strip()):
        return ""
    return NEVER_EMPTY[(kind, change.key)] or (
        f"{change.label} cannot be empty on GitHub, so it was left as it is."
    )


def as_sent(sheet: SheetSpec, changed: Sequence[FieldChange]) -> list[FieldChange]:
    """*changed* with each value as its field's kind means it (a number box's text as a number).

    An emptied field GitHub needs a value in stops the save (:class:`EmptyValueError`).
    """
    kinds = {spec.key: spec.kind for spec in sheet.fields()}
    found: list[FieldChange] = []
    for change in changed:
        refused = emptied_refusal(sheet.kind, change)
        if refused:
            raise EmptyValueError(refused)
        if kinds.get(change.key) is FieldKind.NUMBER:
            change = replace(change, after=_number(change.label, change.after))
        found.append(change)
    return found
