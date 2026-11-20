"""Tools > Plain-Language Batch... in the GitHub Workbench (GitHub PRD 22.6, GH-R-086).

A sentence in, a previewed batch out, with no AI: the grammar is
:mod:`quill.core.github.plain_batch`, the age in it the one both Workbenches
share (:mod:`quill.core.workbench.plain_age`), and the dialogs the WordPress
Workbench's own Plain-Language Batch uses (the sentence box, and the checklist
of exact items). Then:

1. GitHub's search finds the exact items in the repository you are in (at
   most :data:`~quill.core.github.plain_batch.LIMIT`), in the order asked for;
2. a question ("how many", "which") is answered, or the list shown filtered
   to that search, and nothing changes;
3. a change shows every item it found as a checked row, which you can
   uncheck: the editable preview;
4. what is left checked goes through the same batch as several rows'
   Properties: this account's Workbench level, the tier preview, a conflict
   check per item, the verify re-read, Change History and Undo, and a result
   per item with Retry Failed.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

__all__ = ["PLAIN_BATCH_REASONS", "PLAIN_BATCH_VERBS", "GitHubWorkbenchPlainBatchMixin"]

PLAIN_BATCH_VERBS: dict[str, frozenset[str]] = {"plain_batch": frozenset({"view"})}
PLAIN_BATCH_REASONS: dict[str, str] = {
    "plain_batch": "Plain-Language Batch works in a repository, while you are signed in."
}

_HELP = (
    "Say a change to many issues or pull requests in this repository in plain words. "
    "QUILL reads a fixed set of words, without AI, so the same sentence always means the "
    "same thing; then it shows every item it found, checked, for you to uncheck any, before "
    "anything is sent. For example: "
)


class _AfterBatch:
    """What a batch tells the sheet it came from; here the list is filled again instead."""

    def __init__(self, reload: Callable[[], None]) -> None:
        self._reload = reload

    def saved(self, _values: object, _said: str, *, close: bool) -> None:
        self._reload()  # the list keeps its place: the same item, wherever it is now


class GitHubWorkbenchPlainBatchMixin:
    """Plain-Language Batch for the GitHub provider."""

    items: Any
    frame: Any
    signed_in: bool
    _say: Callable[[str], None]
    _background: Callable[..., None]
    _last_plain: str = ""

    def _do_plain_batch(self, ref: Any, _row: object) -> None:
        from quill.core.github.plain_batch import EXAMPLES, PlainError, parse_request

        repository = str(getattr(ref, "instance", "") or "") or self.current_repository_name()  # type: ignore[attr-defined]
        if not repository or "/" not in repository or not self.signed_in:
            self._say(PLAIN_BATCH_REASONS["plain_batch"] + " Ctrl+L opens one by name.")
            return
        text = self._last_plain
        while True:
            answer = self._ask_sentence(repository, text, EXAMPLES)
            if answer is None:
                return
            text = self._last_plain = answer
            try:
                request = parse_request(text)
                break
            except PlainError as exc:
                self._say(exc.plain)  # then the same sentence again, to correct it
        # A question only reads; a change is held to the account's level first,
        # through the one write gate (quill.core.github.write_gate).
        if request.changes_anything and self.refused(  # type: ignore[attr-defined]
            "github.workbench.plain_batch"
        ):
            return
        self._resolve(repository, request)

    def _ask_sentence(self, repository: str, text: str, examples: tuple[str, ...]) -> str | None:
        from quill.ui.dialog_contract import show_modal_dialog
        from quill.ui.wordpress_dialogs import ask_text

        answer = ask_text(
            self.frame.frame,
            show_modal_dialog,
            title="Plain-Language Batch",
            prompt=f"What to do in {repository}, in words:",
            value=text,
            help_text=_HELP + "; ".join(examples) + ".",
        )
        return answer.strip() if answer and answer.strip() else None

    def _resolve(self, repository: str, request: Any) -> None:
        from quill.core.github.plain_batch import LIMIT, order_items

        items = self.items

        def work() -> list[Any]:
            found = items.search_items(repository, request.query, limit=LIMIT)
            return order_items(found, request.order)

        self._background(
            f"find {request.noun} for a plain-language batch",
            work,
            lambda found: self._found(repository, request, list(found)),
        )

    def _found(self, repository: str, request: Any, found: list[Any]) -> None:
        from quill.core.counted import plural
        from quill.core.github.plain_batch import LIMIT

        noun = request.noun.removesuffix("s")
        count = plural(len(found), noun)
        more = f" (the first {LIMIT}; there may be more)" if len(found) >= LIMIT else ""
        if request.action == "count":
            self._say(f"{count} match{'es' if len(found) == 1 else ''}{more}: {request.query}.")
            return
        if request.action == "list":
            self._go_filtered(  # type: ignore[attr-defined]
                "repository", "issues_and_pulls", repository, " ".join(request.qualifiers)
            )
            return
        if not found:
            self._say(f"No {request.noun} match {request.query}. Nothing changed.")
            return
        kept = self._preview(request, found, count + more)
        if not kept:
            return
        self._send(repository, request, kept)

    def _preview(self, request: Any, found: list[Any], count: str) -> list[Any]:
        """The editable preview: every item found, checked; what is left checked goes."""
        from quill.ui.dialog_contract import show_modal_dialog
        from quill.ui.wordpress_workbench_dialogs import ask_checks

        rows = [
            f"#{row.number} {row.title}"
            + (f" (labels: {', '.join(row.labels)})" if getattr(row, "labels", ()) else "")
            for row in found
        ]
        chosen = ask_checks(
            self.frame.frame,
            show_modal_dialog,
            title="Plain-Language Batch",
            prompt=f"{request.said()}. {count} found; uncheck any to leave alone:",
            rows=rows,
            checked=range(len(rows)),
            help_text=(
                "Every item the sentence found, checked. Uncheck any you want left alone; "
                "OK goes on to the preview of the change, Cancel sends nothing."
            ),
        )
        if not chosen:
            if chosen is not None:
                self._say("Nothing was checked. Nothing changed.")
            return []
        return [found[index] for index in chosen]

    def _send(self, repository: str, request: Any, rows: list[Any]) -> None:
        """Load each item's sheet, then the several-items batch: tier, preview, result."""
        from quill.core.github.batch import BatchItem
        from quill.core.github.sheet_catalog import SHEETS
        from quill.core.github.sheet_engine import load, load_options

        api = self.github_api()  # type: ignore[attr-defined]
        sheet = SHEETS[request.kind]
        changes = self._changes_for(request)

        def work() -> tuple[list[Any], dict[str, dict[str, object]]]:
            idents = [{"repo": repository, "number": str(row.number)} for row in rows]
            loaded = [
                BatchItem(sheet.title(ident) or request.kind, ident, load(api, sheet, ident).values)
                for ident in idents
            ]
            return loaded, load_options(api, sheet, idents[0])

        def go(got: tuple[list[Any], dict[str, dict[str, object]]]) -> None:
            items, choices = got
            after = _AfterBatch(self.frame.reload)
            self._apply_many(  # type: ignore[attr-defined]
                request.kind, request.noun, items, changes, choices, after, True
            )

        self._background(f"load {len(rows)} {request.noun}", work, go)

    def _changes_for(self, request: Any) -> list[Any]:
        """The request's change, with "me" named as the signed-in account."""
        from dataclasses import replace

        from quill.core.workbench.properties import ListDelta

        changes = request.changes()
        if request.value != "@me":
            return list(changes)
        login = self.account_name()  # type: ignore[attr-defined]
        fixed = []
        for change in changes:
            delta = change.after
            if isinstance(delta, ListDelta):
                delta = ListDelta(
                    tuple(login if v == "@me" else v for v in delta.added),
                    tuple(login if v == "@me" else v for v in delta.removed),
                )
            fixed.append(replace(change, after=delta))
        return fixed
