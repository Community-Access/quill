"""The quick commands of ``quill.core.github.quick_actions``, on the Workbench's rows.

Each :class:`~quill.core.github.quick_actions.Quick` becomes a verb of its
own (``_fits_<verb>`` and ``_do_<verb>``, made below from the table): it
works out what the row is about (its repository, organization, key or
number), reads a list to pick from if it needs one, asks its questions,
asks before it changes anything, then calls GitHub off the UI thread and
says what happened, or shows a long answer in a window to read. A write is
refused first, in words, when the account's Workbench level (Read Only or
Organize) does not allow its tier.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from quill.core.github.explore_models import ExploreRow
from quill.core.github.items_provider import GitHubCommit, GitHubItem
from quill.core.github.quick_actions import Quick, QuickError
from quill.core.github.quick_tables import _WRITE_TIER, QUICK
from quill.core.github.workflow_models import GitHubWorkflowRun

__all__ = ["QUICK_REASONS", "QUICK_VERBS", "GitHubWorkbenchQuickMixin", "quick_context"]

QUICK_VERBS: dict[str, frozenset[str]] = {q.verb: q.kinds for q in QUICK}
QUICK_REASONS: dict[str, str] = {
    q.verb: f"{q.label.rstrip('.')} is for {', '.join(sorted(q.menu))}"
    + (", while you are signed in." if q.writes else ".")
    for q in QUICK
}
_BY_VERB = {q.verb: q for q in QUICK}


def quick_context(instance: str, node: str, row: object) -> dict[str, str]:
    """What a row is about, by the names the table's paths use."""
    ctx: dict[str, str] = {"node": node}
    if "/" in instance:
        ctx["repo"] = instance
    elif instance:
        ctx["org"] = ctx["login"] = instance
    if isinstance(row, ExploreRow):
        if row.repo and "/" in row.repo:
            ctx["repo"] = row.repo
        elif row.repo:
            ctx["org"] = row.repo
        key = row.key.split(":", 1)[1] if row.kind == "resource" and ":" in row.key else row.key
        if key:
            ctx["key"] = key
        if row.kind == "resource" and ":" in row.key:
            ctx["spec"] = row.key.split(":", 1)[0]
        if row.kind in ("org",) and row.key:
            ctx["org"] = row.key
        if row.kind == "person" and row.key:
            ctx["login"] = row.key
        if row.kind == "project" and "/projects/" in row.url:
            # https://github.com/orgs/acme/projects/3 or https://github.com/users/jo/projects/3
            parts = row.url.split("github.com/", 1)[-1].split("/")
            if len(parts) >= 4:
                ctx["owner_kind"], ctx["owner"], ctx["pnumber"] = parts[0], parts[1], parts[3]
        ctx["name"] = row.title or row.label or row.key
    elif isinstance(row, GitHubItem):
        ctx["number"] = str(row.number)
        ctx["name"] = f"#{row.number}, {row.title}"
    elif isinstance(row, GitHubCommit):
        ctx["sha"] = row.sha
        ctx["name"] = f"commit {row.short_sha}"
    elif isinstance(row, GitHubWorkflowRun):
        ctx["key"] = str(row.id)
        ctx["sha"] = row.head_sha
        ctx["name"] = f"run {row.run_number}, {row.name}"
    elif row is not None:
        ctx["name"] = str(getattr(row, "name", "") or getattr(row, "tag", "") or "")
        if getattr(row, "tag", ""):
            ctx["tag"] = str(row.tag)  # type: ignore[attr-defined]
    return ctx


class GitHubWorkbenchQuickMixin:
    frame: Any
    signed_in: bool
    _say: Callable[[str], None]
    _background: Callable[[str, Callable[[], Any], Callable[[Any], None]], None]
    _choose: Callable[[str, str, list[str]], int]
    _confirm: Callable[[str, str], bool]
    _ask_text: Callable[..., str]

    def github_api(self) -> Any:
        raise NotImplementedError

    def _quick_ctx(self, row: object) -> dict[str, str]:
        current = getattr(self.frame, "current", None)
        return quick_context(
            str(getattr(current, "instance", "") or ""), str(getattr(current, "key", "")), row
        )

    def _quick_fits(self, quick: Quick, row: object) -> bool:
        if quick.writes and not self.signed_in:
            return False
        ctx = self._quick_ctx(row)
        if quick.node and ctx.get("node") != quick.node:
            return False
        spec = ctx.get("spec", "")
        wanted = {k.split(":", 1)[1] for k in quick.kinds if k.startswith("resource:")}
        if wanted and spec not in wanted:
            return False
        return all(ctx.get(key) for key in quick.needs)

    def _quick_refusal(self, quick: Quick) -> str:
        """Why the account's Workbench level refuses *quick*; "" when it may run."""
        level = getattr(self, "access_level", None)
        if not quick.writes or not callable(level):
            return ""
        from quill.core.github.permissions import level_refusal

        return level_refusal(level(), _WRITE_TIER[quick.tier])

    def _quick_run(self, quick: Quick, row: object) -> None:
        self.quick_start(quick, self._quick_ctx(row))

    def quick_start(self, quick: Quick, ctx: dict[str, str]) -> None:
        """Run *quick* on what *ctx* names: a row's context, or a sheet's (Vote... there)."""
        refusal = self._quick_refusal(quick)
        if refusal:
            self._say(refusal)
            return
        if quick.pick is None:
            self._quick_ask(quick, ctx)
            return
        api, picker = self.github_api(), quick.pick
        self._background(
            f"read what {quick.label.rstrip('.')} offers",
            lambda: picker(api, ctx),
            lambda found: self._quick_picked(quick, ctx, list(found)),
        )

    def _quick_picked(self, quick: Quick, ctx: dict[str, str], found: list[Any]) -> None:
        if not found:
            self._say("There is nothing to choose from here.")
            return
        picked = self._choose(quick.label.rstrip("."), quick.pick_question, [f[0] for f in found])
        if picked < 0:
            return
        ctx[quick.pick_key] = str(found[picked][1])
        ctx[f"{quick.pick_key}_label"] = str(found[picked][0])
        self._quick_ask(quick, ctx)

    def _quick_ask(self, quick: Quick, ctx: dict[str, str]) -> None:
        title = quick.label.rstrip(".")
        for ask in quick.asks:
            if ask.kind in ("choice", "yesno"):
                labels = list(ask.choices or ("Yes", "No"))
                values = list(ask.values or (("true", "false") if ask.kind == "yesno" else labels))
                picked = self._choose(title, ask.question, labels)
                if picked < 0:
                    return
                ctx[ask.key] = values[picked]
                continue
            typed = self._ask_text(title, ask.question, value=ask.default).strip()
            if not typed and not ask.optional:
                return
            if typed and ask.kind == "number" and not typed.lstrip("#").isdigit():
                self._say(f"{typed} is not a number.")
                return
            ctx[ask.key] = typed.lstrip("#") if ask.kind == "number" else typed
        if quick.confirm and not self._confirm(title, quick.confirm.format_map(_Blank(ctx))):
            return
        api = self.github_api()

        def work() -> Any:
            return quick.said(quick.run(api, ctx), ctx)

        self._background(title.lower(), work, lambda said: self._quick_done(quick, str(said)))

    def _quick_done(self, quick: Quick, said: str) -> None:
        if quick.copies:
            self.frame.copy_text(said)  # holds a token: never said, never shown
            self._say(quick.copies)
        elif quick.report:
            from quill.ui.github_workbench_results import show_results

            show_results(
                self.frame.frame, quick.label.rstrip("."), said, copy_text=self.frame.copy_text
            )
        else:
            self._say(said)
        if quick.reload:
            self.frame.reload()


class _Blank(dict):  # type: ignore[type-arg]
    def __missing__(self, key: str) -> str:
        return "this"


def _make(quick: Quick) -> tuple[Callable[..., bool], Callable[..., None]]:
    def fits(self: GitHubWorkbenchQuickMixin, row: object) -> bool:
        return self._quick_fits(quick, row)

    def do(self: GitHubWorkbenchQuickMixin, _ref: Any, row: object) -> None:
        try:
            self._quick_run(quick, row)
        except QuickError as exc:
            self._say(str(exc))

    return fits, do


for _quick in QUICK:
    _fits, _do = _make(_quick)
    setattr(GitHubWorkbenchQuickMixin, f"_fits_{_quick.verb}", _fits)
    setattr(GitHubWorkbenchQuickMixin, f"_do_{_quick.verb}", _do)
