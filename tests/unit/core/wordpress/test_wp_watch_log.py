"""Review item 27: Watches keep what they said, fail one at a time, and speak once a round."""

from __future__ import annotations

from typing import Any

from quill.core.wordpress.api import WordPressApiError
from quill.core.wordpress.workbench_watch_log import KEPT, one_announcement, recent, remember
from quill.core.wordpress.workbench_watches import WatchState, check, load_state, save_state
from quill.core.wordpress.workbench_watches_more import WatchContext


class Site:
    """Comments read fine; the plugin list is refused, as for an editor."""

    def __init__(self) -> None:
        self.comments: list[int] = []
        self.refuse_plugins = True

    def get(self, route: str, **_params: Any) -> Any:
        return []

    def iter_collection(self, route: str, params: Any = None, **_kw: Any):
        if route == "wp/v2/plugins" and self.refuse_plugins:
            raise WordPressApiError("Sorry, you are not allowed to manage plugins.")
        if route == "wp/v2/comments":
            for ident in self.comments:
                yield {"id": ident}


def _round(site: Site, state: WatchState, now: float) -> list[str]:
    return check(
        [("Radio", site, ["wp/v2"])],
        state,
        ["comment", "update"],
        now=lambda: now,
        context=WatchContext(),
    )


def test_a_refused_watch_costs_only_itself_and_is_said_once() -> None:
    site, state = Site(), WatchState()
    first = _round(site, state, 1000.0)
    assert first == [
        "The Watch for plugin updates available could not read Radio, so it skips that "
        "site: Sorry, you are not allowed to manage plugins."
    ]
    site.comments = [5]
    second = _round(site, state, 2000.0)
    assert second == ["1 new comment waiting on Radio."]  # the comment Watch still works
    site.refuse_plugins = False
    third = _round(site, state, 3000.0)
    assert third == ["The Watch for plugin updates available reads Radio again."]


def test_what_watches_said_is_kept_newest_first(tmp_path) -> None:
    site, state = Site(), WatchState()
    _round(site, state, 1000.0)
    site.comments = [5, 6]
    _round(site, state, 2000.0)
    save_state(state, tmp_path)
    kept = recent(load_state(tmp_path))
    assert [text for _when, text in kept][0] == "2 new comments waiting on Radio."
    assert kept[0][0] == 2000.0 and kept[-1][0] == 1000.0


def test_the_log_keeps_only_the_newest() -> None:
    state = WatchState()
    for index in range(KEPT + 5):
        remember(state, [f"Said {index}."], float(index))
    kept = recent(state, KEPT + 10)
    assert len(kept) == KEPT and kept[0][1] == f"Said {KEPT + 4}."


def test_a_busy_round_is_one_announcement() -> None:
    assert one_announcement([]) == ""
    assert one_announcement(["A."]) == "A."
    assert one_announcement(["A.", "B."]) == "Watches found 2 things. A. B."
