"""My GitHub in the Workbench: the loader, and View > My GitHub View Options...

The loader (``explore:my_github``) reads what the Workbench already reads for
Notifications and for Inbox's assigned issues, review requests and failing
pull requests, puts it through :mod:`quill.core.github.my_github`, applies the
person's remembered filter, sort and group, and says what it found in the one
status sentence ("4 need your attention: 2 unread notifications, ..."). It
makes no request Inbox and Notifications do not already make.

The options are asked one question at a time, as Inbox Rules are, so a screen
reader hears each choice and the one it is on. Each answer is saved at once.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from quill.core.github.explore_models import ExploreRow
from quill.core.github.my_github import (
    assemble,
    changes_sentence,
    empty_sentence,
    group_counts_sentence,
    present,
    refine,
    summary_sentence,
)
from quill.core.github.my_github_prefs import (
    GROUPS,
    KINDS,
    SORTS,
    MyGitHubPrefs,
    load_prefs,
    save,
)
from quill.core.workbench.filters import Query
from quill.core.workbench.tree import NodeSpec

__all__ = [
    "MY_GITHUB_REASONS",
    "MY_GITHUB_VERBS",
    "GitHubWorkbenchMyGitHubMixin",
    "load_my_github",
]

#: What the queue asks the attention search for: Mentioned is left to Notifications,
#: which already carries every mention GitHub sent.
_ATTENTION_CATEGORIES = ("assigned", "review_requested", "failed_checks")

MY_GITHUB_VERBS: dict[str, frozenset[str]] = {"my_github_options": frozenset({"view"})}
MY_GITHUB_REASONS: dict[str, str] = {
    "my_github_options": "My GitHub Options are for the My GitHub list, while you are signed in.",
}


def _notification_node() -> NodeSpec:
    from quill.core.github.workbench_tree import GITHUB_TREE

    return next(spec for spec in GITHUB_TREE if spec.key == "notifications")


def load_my_github(
    client: Any,
    *,
    account: str = "",
    limit: int = 50,
    notes: list[str] | None = None,
) -> list[ExploreRow]:
    """The My GitHub rows, in the person's order. Runs off the UI thread."""
    from quill.core.github.attention_queue import GitHubAttentionQueue
    from quill.ui.github_workbench_explore import _without_snoozed, load_explore

    login = account or client.account_login()
    scope = GitHubAttentionQueue.load(login)
    warnings: list[str] = []

    def notifications() -> list[ExploreRow]:
        return load_explore(
            client,
            _notification_node(),
            instance="",
            query=Query(),
            account=login,
            limit=limit,
            notes=warnings,
        )

    def attention() -> list[ExploreRow]:
        result = client.fetch_with_status(
            "attention",
            repositories=tuple(scope.repositories),
            categories=_ATTENTION_CATEGORIES,
            limit=limit,
        )
        warnings.append(str(getattr(result, "warning", "") or ""))
        return _without_snoozed(client, list(result.items), login, show=False, notes=None)

    queue = assemble(notifications=notifications, attention=attention)
    prefs = load_prefs(login)
    shown = refine(queue.items, prefs)
    previous = getattr(client, "_my_github_keys", None)
    client._my_github_keys = frozenset(item.key for item in queue.items)  # noqa: SLF001
    if notes is not None:
        notes.extend(failure.sentence for failure in queue.failures)
        notes.append(
            summary_sentence(shown)
            if shown
            else empty_sentence(hidden=len(queue.items) - len(shown))
        )
        if len(shown) != len(queue.items) and shown:
            notes.append(f"{len(queue.items) - len(shown)} hidden by your filter.")
        notes.append(group_counts_sentence(shown, prefs.group))
        if not queue.failures:
            notes.append(changes_sentence(previous, queue.items))
        notes.extend(w.rstrip(".") + "." for w in warnings if w.strip())
    return [present(item) for item in shown]


class GitHubWorkbenchMyGitHubMixin:
    frame: Any
    signed_in: bool
    _say: Callable[[str], None]
    _choose: Callable[[str, str, list[str]], int]
    _ask_text: Callable[..., str]

    def _explore_client(self) -> Any:
        raise NotImplementedError

    def _fits_my_github_options(self, _row: object) -> bool:
        return self.signed_in

    def _do_my_github_options(self, _ref: Any, _row: object) -> None:
        title = "My GitHub Options"
        client = self._explore_client()
        account = client.account_login()
        prefs = load_prefs(account)
        kinds = self._choose(
            title,
            "Show which kinds? Now: "
            + (
                ", ".join(label for key, label in KINDS if key in prefs.kinds)
                if prefs.kinds
                else "all kinds"
            )
            + ".",
            ["All kinds", *(label for _key, label in KINDS)],
        )
        if kinds < 0:
            return
        repository = self._ask_text(
            title,
            "Only one repository? owner/name, or blank for every repository:",
            value=prefs.repository,
        )
        unread = self._choose(
            title,
            "Notifications you have already read:",
            ["Show them", "Hide them"],
        )
        if unread < 0:
            return
        sort = self._choose(title, "Order the list:", [label for _key, label in SORTS])
        if sort < 0:
            return
        group = self._choose(title, "Group the list:", [label for _key, label in GROUPS])
        if group < 0:
            return
        chosen = MyGitHubPrefs(
            kinds=() if kinds == 0 else (KINDS[kinds - 1][0],),
            repository=repository.strip(),
            unread_only=unread == 1,
            sort=SORTS[sort][0],
            group=GROUPS[group][0],
        )
        try:
            save(account, chosen)
        except OSError as exc:
            self._say(f"Could not save your choices: {exc}")
            return
        self._say("Saved.")
        self.frame.reload(report=True)
