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

#: The results branch's node id. Not a browse source -- nothing ever fetches
#: it, because its children are written straight in and it is marked loaded.
RESULTS_ID = "searchresults"


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
) -> None:
    """Ask, search off-thread, and show the answer in this tree.

    *targets* narrows which sources are asked -- how "Search for a Podcast..."
    reaches the same machinery without leaving the tree either.
    """
    query = _ask_query(host, title=title, prompt=prompt)
    if not query:
        return
    host._announce(f"Searching {what} for {query}...")

    def _work(**_kwargs: Any) -> federated_browse.FederatedBrowse:
        return federated_browse.search_everything(
            query,
            safe_mode=host._safe_mode,
            # getattr: tests build the dialog with __new__ and no __init__.
            catalog=getattr(host, "_catalog", None),
            targets=targets,
        )

    def _ok(_op: str, found: object) -> None:
        # Already on the UI thread (call_ui_safely marshals and guards this).
        if isinstance(found, federated_browse.FederatedBrowse):
            show_results(host, query, found)

    def _failed(_op: str, error: BaseException) -> None:
        if host._tree:
            host._announce(f"That search could not be completed. {error}.")

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


def show_results(host: Any, query: str, found: federated_browse.FederatedBrowse) -> None:
    """Render *found* as the Search Results branch and land the cursor in it."""
    if not host._tree:  # the window closed while the search was in flight
        return
    tree = host._tree
    count = found.total
    node = _results_node(host, f'Search Results: "{query}"  ({count})')
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
    host._announce(federated_browse.describe(query, found, safe_mode=host._safe_mode))
    first, _cookie = tree.GetFirstChild(node)
    if first.IsOk():
        tree.SelectItem(first)
        tree.SetFocus()
