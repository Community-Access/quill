"""Plain-language batches and saved REST requests (PRD 15.8, 15.9; W7).

A mixin on :class:`quill.ui.wordpress_workbench_window.WordPressWorkbenchProvider`:

- **Plain-Language Batch** (Ctrl+Alt+B): a phrase such as "move all drafts by
  Sam to pending on Radio" read by the fixed grammar in
  :mod:`quill.core.wordpress.workbench_plain_batch` -- no AI, so the same
  words always make the same batch. Each named site is checked for Workbench
  access and the role's capability first; the exact items are then listed as
  an editable checklist (uncheck what should not change), and what stays
  checked goes through the conflict check and ``batch/v1``, with a report line
  per item and an entry in Change History. A phrase may say how old ("older
  than a year", "before March 2024"); "move ... to Trash" moves the checked
  items to WordPress's Trash, and Ctrl+Z puts them back with the status each
  had; a question ("how many drafts are older than six months?") is answered
  with a count from each site and changes nothing. The AI command catalogue is
  not used here; the grammar is the whole path.
- **Saved requests**: Tools > Run a Saved Request (Ctrl+Alt+Q) and the Saved
  Requests submenu (its rows numbered 1 to 9) open the REST Console filled in
  -- a read is sent at once, a write still shows its preview; Forget a Saved
  Request (Ctrl+Alt+Shift+F) removes one. The console's Save Request button
  keeps them (:mod:`quill.core.wordpress.workbench_rest_saved`).
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from quill.core.wordpress.workbench_plain_batch import (
    EXAMPLES,
    PhraseError,
    SitePlan,
    answer,
    parse_request,
    resolve,
    run_site,
    undo_trash,
)
from quill.core.wordpress.workbench_rest_saved import SavedRequest, forget, load_saved
from quill.core.wordpress.workbench_rows import WbRow
from quill.core.workbench.actions import Tier
from quill.core.workbench.history import Change
from quill.ui import wordpress_dialogs as dlg
from quill.ui import wordpress_workbench_dialogs as wdlg

__all__ = ["WorkbenchMoreCommands"]


class WorkbenchMoreCommands:
    """Plain-Language Batch; Run, list and Forget saved REST requests."""

    parent: Any
    history: Any
    _data_dir: Any
    _profiles: dict[str, Any]
    say: Callable[[str], None]
    background: Callable[..., None]
    ctx: Callable[[str], Any]
    ensure: Callable[[Any], Any]
    show_modal: Callable[[Any, str], int]
    refresh: Callable[[], None]
    current_site: Callable[[], str]
    site_of: Callable[[Any], str]
    write_refusal: Callable[[WbRow, Tier], str]

    # -- plain-language batches (15.8) --------------------------------------------

    def do_plain_batch(self, ref: Any, _row: WbRow | None) -> None:
        text = dlg.ask_text(
            self.parent,
            self.show_modal,
            title="Plain-Language Batch",
            prompt="&What to do:",
            help_text="Say a change in words, for example: " + "; or ".join(EXAMPLES) + ". "
            "A phrase may say how old, such as older than a year or before March 2024. "
            "Nothing is sent until you check the list that follows and press OK; a question "
            "that starts How many changes nothing.",
        )
        if not text or not text.strip():
            return
        current = self.site_of(ref) or self.current_site()
        try:
            request = parse_request(text, list(self._profiles), current)
        except PhraseError as exc:
            self.say(exc.plain)
            return
        refused: list[SitePlan] = []
        allowed: list[str] = []
        for site in request.sites:
            probe = WbRow("item", site, "0", {}, "", subkind=request.kind)
            reason = self.write_refusal(probe, Tier.WRITE) if request.changes else ""
            if reason:
                refused.append(SitePlan(site, problem=reason))
            else:
                allowed.append(site)

        def work() -> list[SitePlan]:
            return refused + [resolve(request, s, self.ctx(s).api) for s in allowed]

        def found(plans: list[SitePlan]) -> None:
            if request.changes:
                self._batch_checks(request, plans)
            else:
                self.say(answer(request, plans))

        self.background("finding what the batch changes", work, found)

    def _batch_checks(self, request: Any, plans: list[SitePlan]) -> None:
        labels: list[str] = []
        where: list[tuple[int, int]] = []
        for p, plan in enumerate(plans):
            for i, row in enumerate(plan.rows):
                labels.append(f"{plan.site}: {row.title}")
                where.append((p, i))
        summary = " ".join(plan.sentence for plan in plans)
        trashing = request.action == "trash"
        if not labels:
            self.say(f"Nothing to change. {summary}")
            return
        picked = wdlg.ask_checks(
            self.parent,
            self.show_modal,
            title="Plain-Language Batch",
            prompt="&Change these:",
            rows=labels,
            checked=list(range(len(labels))),
            help_text=f"{request.words} {summary} Uncheck anything that should not change; "
            "OK sends the rest, each checked for a change made since it was read."
            + (" They go to the site's Trash, and Ctrl+Z puts them back." if trashing else ""),
        )
        if not picked:
            return
        keep: dict[int, list[int]] = {}
        for index in picked:
            p, i = where[index]
            keep.setdefault(p, []).append(i)

        def work() -> list[str]:
            said: list[str] = []
            for p, rows in keep.items():
                said += run_site(self.ctx(plans[p].site).api, plans[p], rows)
            return said

        def done(said: list[str]) -> None:
            ok = sum(1 for s in said if s.endswith((": saved", ": moved to the Trash")))
            if trashing:
                moved = [plans[p] for p in keep]
                self.history.record(
                    Change(
                        "batch",
                        f"Moved {ok} to the Trash: {request.words}",
                        undo=(lambda: undo_trash(lambda site: self.ctx(site).api, moved))
                        if ok
                        else None,
                    )
                )
                self.say(f"Batch done: {ok} of {len(picked)} moved to the Trash."
                         + (" Ctrl+Z puts them back." if ok else ""))  # fmt: skip
            else:
                self.history.record(Change("batch", request.words))
                self.say(f"Batch done: {ok} of {len(picked)} changed.")
            dlg.show_report(
                self.parent,
                self.show_modal,
                title="Plain-Language Batch",
                text="\n".join([request.words, *said]),
                help_text="What happened to each item of the batch.",
            )
            self.refresh()

        self.background("running the batch", work, done)

    # -- saved REST requests (15.9) -------------------------------------------------

    def dynamic_menu(self, key: str) -> list[tuple[str, Callable[[], None]]]:
        if key != "rest_saved":
            return []
        return [
            (saved.label, lambda s=saved: self.run_saved(s))
            for saved in load_saved(self._data_dir)[:9]
        ]

    def run_saved(self, saved: SavedRequest) -> None:
        site = saved.site if saved.site in self._profiles else self.current_site()
        if not site:
            self.say("Connect a site first: File > WordPress > Connect a Site, in the editor.")
            return
        from quill.ui.wordpress_rest_console import RestConsole

        ctx = self.ensure(self.ctx(site))
        console = RestConsole(self, site, ctx)
        console.prefill(saved)
        if saved.method in ("GET", "OPTIONS"):
            console.send()
        console.show()

    def _pick_saved(self, title: str, help_text: str) -> SavedRequest | None:
        saved = load_saved(self._data_dir)
        if not saved:
            self.say("No saved requests yet: the REST Console's Save Request button keeps one.")
            return None
        index = dlg.ask_choice(
            self.parent,
            self.show_modal,
            title=title,
            prompt="&Request:",
            rows=[s.label for s in saved],
            help_text=help_text,
        )
        return None if index is None else saved[index]

    def do_run_saved(self, _ref: Any, _row: WbRow | None) -> None:
        saved = self._pick_saved(
            "Run a Saved Request",
            "Opens the REST Console with it filled in. A read is sent at once; a write "
            "shows its preview first.",
        )
        if saved is not None:
            self.run_saved(saved)

    def do_forget_saved(self, _ref: Any, _row: WbRow | None) -> None:
        saved = self._pick_saved("Forget a Saved Request", "The request to remove from the list.")
        if saved is not None:
            forget(saved.name, self._data_dir)
            self.say(f"Forgot {saved.name}.")
