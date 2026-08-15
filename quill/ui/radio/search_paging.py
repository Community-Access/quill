"""**More Stations**: the next page of results, and where the cursor lands.

Extracted from ``station_browser_dialog`` under GATE-11 (extract, never
rebaseline). One concern -- paging the community directory -- and one behaviour
in it worth protecting, which is why it earns a module rather than a comment:

**Focus goes to the first *newly added* station**, not back to the top of the
list. Somebody who pressed More Stations was at the end of the results, and
returning them to row 0 would make them arrow back through everything they had
already read to reach the rows they asked for. That single line is most of the
value of the feature.
"""

from __future__ import annotations

from typing import Any


def fetch_more(host: Any) -> None:
    """Fetch and append the next page of Radio Browser results (#1064)."""
    from quill.core.radio import radio_browser
    from quill.ui.radio.station_browser_dialog import _SEARCH_LIMIT

    if not host._search_more_available:
        return
    host._more_btn.Enable(False)
    host._status.SetLabel("Loading more stations...")
    offset = host._search_offset
    name, tag, country = host._search_query, host._search_tag, host._search_country

    def _do_more(**_kwargs: Any) -> list:
        return radio_browser.search_stations(
            name,
            tag=tag,
            country=country,
            limit=_SEARCH_LIMIT,
            offset=offset,
            safe_mode=host._safe_mode,
        )

    host._task_manager.submit(
        "radio-search-more",
        _do_more,
        on_success=lambda _op, stations: host._on_more_done(stations, None),
        on_failure=lambda _op, exc: host._on_more_done([], exc),
    )


def more_arrived(host: Any, stations: list, error: BaseException | None) -> None:
    """Merge the new page in and put the cursor on its first row."""
    from quill.core.radio.directory_search import merge_and_rank
    from quill.ui.radio.station_browser_dialog import _SEARCH_LIMIT, _SEARCH_RESULTS

    if error is not None:
        host._status.SetLabel(f"Could not load more: {error}")
        host._more_btn.Enable(True)  # let the user try again
        return
    first_new_index = len(host._search_results)
    host._search_rb = host._search_rb + stations
    host._search_results = merge_and_rank(
        [host._search_rb, host._search_extras], host._search_query
    )
    host._search_offset += len(stations)
    host._search_more_available = len(stations) >= _SEARCH_LIMIT
    host._more_btn.Enable(host._search_more_available)
    host._show_category(_SEARCH_RESULTS)
    # Land on the first newly added station, so the reader picks up where the
    # previous page ended rather than back at the top.
    if stations and first_new_index < len(host._current_results):
        host._results.Select(first_new_index)
        host._results.Focus(first_new_index)
        host._results.EnsureVisible(first_new_index)
    host._announce(
        f"Added {len(stations)} more; {len(host._search_results)} stations now."
        if stations
        else "No more stations."
    )
