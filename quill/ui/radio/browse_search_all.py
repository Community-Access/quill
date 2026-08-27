"""Search All Sources, answered inside the browse tree.

The tree-top **Search All Sources...** row used to open the Find Stations
window: a different surface, a different list widget, a different set of verbs,
and the browse tree you were standing in gone from under you. Reported plainly
(2026-08-18): *"search all sources is taking me somewhere else, I would prefer
to stay in the browse dialog and show the results in a general list with its
type showing and rich context menu options as though it was done from that
folder."*

That is what this module does. The search runs off the UI thread, and the
answer lands as a **Search Results** branch at the top of the same tree -- one
flat list, ordered by type, every row saying what it is and who answered, and
every row carrying the node id its own source would have produced. So the
context menu is not a reduced search-result menu: a podcast show found by
typing offers Subscribe and expands into its episodes, a LibriVox book expands
into its chapters, and a station offers everything a browsed station does,
because they *are* browse rows.

Escape in the Find box drops the branch (see :mod:`quill.ui.radio.browse_find`);
searching again replaces it.
"""

from __future__ import annotations

from typing import Any

from quill.core.radio import federated_browse
from quill.ui.radio import browse_feedback

#: The results branch's node id. Not a browse source -- nothing ever fetches
#: it, because its children are written straight in and it is marked loaded.
RESULTS_ID = "searchresults"

#: How long the first pass may take. Everything it asks answers from local
#: data, so this is a guard against a cold cache rather than a budget.
FAST_PASS_SECONDS = 3.0

#: The last few completed searches, ``query -> (monotonic instant, answer)``.
#: Searching the same thing twice is common -- checking whether a station came
#: back up, re-finding the row you just closed -- and the second ask used to
#: cost the full fan-out again. Now the finished answer renders instantly (as a
#: partial, because a refresh is already running to replace it). Session-only
#: and small on purpose: results carry live counts and reachability, so
#: yesterday's answer is not worth persisting.
_RECENT_RESULTS: dict[str, tuple[float, federated_browse.FederatedBrowse]] = {}
RECENT_TTL_SECONDS = 600.0
_RECENT_LIMIT = 8


def _ask_query(host: Any, *, title: str, prompt: str) -> str:
    """One line of text, or "" if they cancelled.

    ``wx.TextEntryDialog`` for the reason every other prompt in the tree uses
    it (``browse_actions._ask``): the platform's own prompt is one every screen
    reader already reads correctly. Unlike the address prompts it does *not*
    pre-fill from the clipboard -- what you last copied is almost never what
    you want to search for, and a field that arrives full costs a Ctrl+A.
    """
    wx = host._wx
    entry = wx.TextEntryDialog(host._win, prompt, title)  # dialog_button_contract: exempt
    try:
        if entry.ShowModal() != wx.ID_OK:
            return ""
        return str(entry.GetValue()).strip()
    finally:
        entry.Destroy()
        # Escaping out of a prompt must land somewhere. Without this the
        # closing dialog leaves focus on whatever wx decides, which reads as a
        # dead window to a screen reader -- reported against the old search
        # (2026-08-18) and just as possible here.
        _focus_tree(host)


def run(
    host: Any,
    *,
    title: str = "Search All Sources",
    prompt: str = "What are you looking for? Every source is searched at once.",
    what: str = "every source",
    targets: tuple[federated_browse.SearchTarget, ...] | None = None,
    query: str = "",
) -> None:
    """Ask, search off-thread, and show the answer in this tree.

    *targets* narrows which sources are asked -- how "Search for a Podcast..."
    reaches the same machinery without leaving the tree either.

    *query* skips the prompt, for a listener who has already typed. Asked for
    2026-08-26: somebody standing on the Search All Sources row who reaches the
    Find box instead (Ctrl+F, or Shift+Tab) and types there means the same
    thing, and being made to press Enter, read a prompt and type it again is the
    app failing to meet them where they are.
    """
    query = query.strip() or _ask_query(host, title=title, prompt=prompt)
    if not query:
        return
    host._announce(f"Searching {what} for {query}...")
    browse_feedback.start_search_notice(host, what, query)

    import time

    remembered = _RECENT_RESULTS.get(query.casefold()) if targets is None else None
    if remembered is not None and (time.monotonic() - remembered[0]) > RECENT_TTL_SECONDS:
        remembered = None

    def _search(
        chosen: tuple[federated_browse.SearchTarget, ...] | None, deadline: float
    ) -> federated_browse.FederatedBrowse:
        return federated_browse.search_everything(
            query,
            safe_mode=host._safe_mode,
            # getattr: tests build the dialog with __new__ and no __init__.
            catalog=getattr(host, "_catalog", None),
            targets=chosen,
            deadline_seconds=deadline,
        )

    def _work(**_kwargs: Any) -> federated_browse.FederatedBrowse:
        return _search(targets, federated_browse.SEARCH_DEADLINE_SECONDS)

    def _work_fast(**_kwargs: Any) -> federated_browse.FederatedBrowse:
        return _search(federated_browse.fast_targets(targets), FAST_PASS_SECONDS)

    def _ok(_op: str, found: object) -> None:
        # Already on the UI thread (call_ui_safely marshals and guards this).
        browse_feedback.stop_search_notice(host)
        if isinstance(found, federated_browse.FederatedBrowse):
            if targets is None:
                import time

                _RECENT_RESULTS[query.casefold()] = (time.monotonic(), found)
                while len(_RECENT_RESULTS) > _RECENT_LIMIT:
                    _RECENT_RESULTS.pop(next(iter(_RECENT_RESULTS)))
            show_results(host, query, found)

    def _ok_fast(_op: str, found: object) -> None:
        """The first pass: render what is already on this machine.

        Reported 2026-08-26 -- "search is still slow when it is performed" --
        after the fan-out and the per-result resolution had both been fixed.
        What was left is simply that the answer waited for the slowest of
        sixteen services. It no longer does: the catalog, NOAA and the two
        cached directories come back in well under a second and are shown, and
        the full answer replaces them when it arrives.

        Deliberately quiet about *focus*: the second render must not yank the
        cursor out from under somebody already reading the first (see
        ``show_results(..., land_focus=)``). The first one lands the cursor as
        it always did.
        """
        if isinstance(found, federated_browse.FederatedBrowse) and found.rows:
            show_results(host, query, found, partial=True)

    def _failed(_op: str, error: BaseException) -> None:
        browse_feedback.stop_search_notice(host)
        if host._tree:
            host._announce(f"That search could not be completed. {error}.")

    if remembered is not None:
        # The finished answer from a few minutes ago, instantly, marked as
        # partial because the refresh below will replace it. Rendering the fast
        # pass on top of it would be a downgrade -- fewer sources than the
        # remembered answer already has -- so only the full search runs.
        show_results(host, query, remembered[1], partial=True)
    else:
        # The fast pass first, so it is already running while the full one
        # starts. It asks a subset of the same sources, so the only cost of
        # doing both is a second read of a local database.
        host._task_manager.submit("radio-search-all-fast", _work_fast, on_success=_ok_fast)
    host._task_manager.submit("radio-search-all", _work, on_success=_ok, on_failure=_failed)


def _focus_tree(host: Any) -> None:
    """Put the cursor back in the tree. Never raises."""
    tree = getattr(host, "_tree", None)
    if not tree:
        return
    try:
        tree.SetFocus()
    except Exception:  # noqa: BLE001 - a focus call must never break a search
        return


def find_results_node(host: Any) -> Any:
    """The existing Search Results branch, or ``None``.

    getattr, because this is also reached from ``browse_find.clear_find`` --
    which the find tests drive with a bare stand-in host that has a Find box
    and no tree at all.
    """
    tree = getattr(host, "_tree", None)
    if not tree:
        return None
    root = tree.GetRootItem()
    if root is None or not root.IsOk():
        return None
    node, cookie = tree.GetFirstChild(root)
    while node is not None and node.IsOk():
        data = host._node_data(node)
        if data is not None and str(data.get("node_id", "")) == RESULTS_ID:
            return node
        node, cookie = tree.GetNextChild(root, cookie)
    return None


def clear_results(host: Any) -> bool:
    """Drop the Search Results branch. True when there was one.

    The cursor lands on the row that produced the results (Search All
    Sources..., the first row) because the row it was standing on is one of the
    ones being deleted -- a tree whose selection was just destroyed is the
    dead-focus state Escape exists to rescue somebody from.

    **Focus itself is not moved.** Clearing is a refresh, not a destination:
    somebody who cleared from the Find box is still typing there ("do not move
    focus automagically when clearing search, refresh is fine but let the user
    move", 2026-08-18).
    """
    node = find_results_node(host)
    if node is None:
        return False
    tree = host._tree
    tree.Delete(node)
    root = tree.GetRootItem()
    first, _cookie = tree.GetFirstChild(root)
    if first is not None and first.IsOk():
        tree.SelectItem(first)
    return True


def _results_node(host: Any, label: str) -> Any:
    """A fresh, empty Search Results branch directly under the search row.

    Deleted and remade rather than emptied, so the label (which carries the
    query and the count) is always the one for the rows underneath it.
    """
    tree = host._tree
    clear_results(host)
    root = tree.GetRootItem()
    first, _cookie = tree.GetFirstChild(root)
    # Immediately below Search All Sources..., which is always the first row --
    # the results belong next to the thing that produced them. If the tree is
    # somehow empty, the top is still the right place.
    node = tree.InsertItem(root, first, label) if first.IsOk() else tree.PrependItem(root, label)
    tree.SetItemData(
        node,
        # loaded: nothing may ever fetch this id -- the children are written
        # below and there is no source behind it.
        {"node_id": RESULTS_ID, "label": label, "loaded": True},
    )
    return node


def show_results(
    host: Any,
    query: str,
    found: federated_browse.FederatedBrowse,
    *,
    partial: bool = False,
) -> None:
    """Render *found* as the Search Results branch and land the cursor in it.

    *partial* marks the first of the two passes (see ``run``): the branch says
    so in its own label, the spoken line says more is coming, and -- the part
    that matters most -- the **second** render does not move the cursor, so a
    listener already arrowing through the early results is not thrown back to
    the top when the rest arrive.
    """
    if not host._tree:  # the window closed while the search was in flight
        return
    tree = host._tree
    count = found.total
    # Where the cursor is *now* decides whether the full pass may move it: if
    # they are already inside the results, they are reading, and being sent
    # back to the top by an arriving source is worse than arriving quietly.
    land_focus = partial or not _cursor_in_results(host)
    label = (
        f'Search Results: "{query}"  ({count}, still searching...)'
        if partial
        else f'Search Results: "{query}"  ({count})'
    )
    node = _results_node(host, label)
    for row in found.rows:
        item = tree.AppendItem(node, host._row_label(row))
        tree.SetItemData(item, host._row_data(row))
        if row.is_folder:
            # A show, a book, an Archive item: give it the lazy placeholder so
            # it opens into its episodes/chapters exactly as browsing does.
            tree.SetItemData(tree.AppendItem(item, "Loading..."), dict(host._placeholder()))
    if not found.rows:
        empty = tree.AppendItem(node, f"Nothing found for {query}.")
        tree.SetItemData(empty, dict(host._placeholder()))
    tree.Expand(node)
    # Escape in the Find box clears "the results", and these are results: the
    # flag is what makes that keystroke reach browse_find.clear_find at all
    # when the Find box itself was never used.
    host._find_active = True
    said = federated_browse.describe(query, found, safe_mode=host._safe_mode)
    host._announce(f"{said} Still searching the rest." if partial else said)
    first, _cookie = tree.GetFirstChild(node)
    if land_focus and first.IsOk():
        tree.SelectItem(first)
        tree.SetFocus()


def _cursor_in_results(host: Any) -> bool:
    """True when the highlighted row is the results branch or inside it."""
    tree = host._tree
    try:
        node = tree.GetSelection()
        while node is not None and node.IsOk():
            data = host._node_data(node)
            if data is not None and str(data.get("node_id", "")) == RESULTS_ID:
                return True
            node = tree.GetItemParent(node)
    except (RuntimeError, AttributeError):
        return False
    return False
