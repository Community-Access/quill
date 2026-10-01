"""Add Podcast dialog: after subscribing from a search result, focus returns
to the results list so a screen-reader user can keep arrowing through hits.

Source-contract style (matches the other wx dialog tests): assert the wiring
is present rather than driving real wx widgets, plus a pure check of the
row-clamping helper's intent."""

from __future__ import annotations

import ast
from pathlib import Path

_SRC = (
    Path(__file__).resolve().parents[3] / "quill" / "ui" / "podcasts" / "add_podcast_dialog.py"
).read_text(encoding="utf-8")


def test_subscribe_from_result_threads_the_row_index() -> None:
    # The iTunes-search subscribe path tags the request with its row so focus
    # can return to exactly that row.
    actions = Path(__file__).resolve().parents[3] / "quill/ui/podcasts/add_podcast_actions.py"
    assert "follow_action(self)" in _SRC
    assert any(
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "_subscribe_to_feed"
        and any(
            keyword.arg == "result_index"
            and isinstance(keyword.value, ast.Name)
            and keyword.value.id == "index"
            for keyword in node.keywords
        )
        for node in ast.walk(ast.parse(actions.read_text(encoding="utf-8")))
    )
    assert "result_index: int | None" in _SRC


def test_fetch_done_returns_focus_on_every_outcome() -> None:
    # Success, already-subscribed, and error all end by returning focus to the
    # list -- otherwise focus would be stranded on the Subscribe button.
    assert _SRC.count("self._return_focus_to_results(result_index)") >= 3


def test_focus_helper_only_acts_for_the_search_results_path() -> None:
    # Add-by-Feed-URL passes no index, so the helper is a no-op there and the
    # URL box keeps focus.
    assert "if result_index is None:\n            return" in _SRC
    # It re-selects, focuses the row, and moves keyboard focus to the list.
    assert "self._results.Select(target)" in _SRC
    assert "self._results.Focus(target)" in _SRC
    assert "self._results.SetFocus()" in _SRC


def test_focus_target_is_clamped_into_range() -> None:
    # A row index is clamped to the current list bounds so a shrunken result
    # set can never focus a phantom row.
    assert "target = max(0, min(result_index, count - 1))" in _SRC
