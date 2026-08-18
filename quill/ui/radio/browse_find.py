"""Find in this folder: the browse tree's scoped, bounded search.

Extracted from ``browse_tree_dialog`` under GATE-11 (extract, never
rebaseline), and a self-contained concern: everything here answers *which rows
under this folder match*, and how the tree shows and then clears that answer.
The host passes itself in, exactly like ``browse_refresh`` and
``browse_tree_menu``.

The search recurses the subtree under the highlighted folder only, within
bounds -- depth, results, and folder fetches -- so searching from a big branch
(or TuneIn's remote tree) stays scoped instead of walking the whole internet.
Hitting a bound is reported, never silent.
"""

from __future__ import annotations

from typing import Any

#: How deep to recurse, the most results to collect, and the most folder
#: fetches to spend before saying "search a smaller folder for the rest".
FIND_MAX_DEPTH = 6
FIND_MAX_RESULTS = 2000
FIND_MAX_FETCHES = 80


def _collect_matches(
    host: Any, node_id: str, ql: str, depth: int, acc: list[dict], budget: dict
) -> bool:
    """Recurse the subtree under *node_id*, appending leaf node-data whose
    label contains *ql*. Returns True if a bound cut the walk short.

    One loop for every source, because every source now answers the same
    question the same way. The old version needed a parallel mapping
    (``_subtree_children``) kept in step with ``_add_children`` by hand, and
    it silently skipped any source nobody remembered to add to it.
    """
    if len(acc) >= FIND_MAX_RESULTS:
        return True
    if depth > FIND_MAX_DEPTH or budget["fetches"] >= FIND_MAX_FETCHES:
        return True
    budget["fetches"] += 1
    capped = False
    for child in host._fetch_children(node_id):
        if child.is_action:
            continue
        if child.is_folder:
            capped = _collect_matches(host, child.node_id, ql, depth + 1, acc, budget) or capped
        elif ql in child.label.lower():
            acc.append(host._leaf_data(child))
        if len(acc) >= FIND_MAX_RESULTS:
            return True
    return capped


def find_matches(host: Any, node_id: str, query: str) -> tuple[list[dict], bool]:
    """Leaf node-data under *node_id* matching *query* (case-insensitive),
    plus whether a bound cut the search short."""
    acc: list[dict] = []
    budget = {"fetches": 0}
    capped = _collect_matches(host, node_id, query.strip().lower(), 0, acc, budget)
    return acc, capped


def find_anchor_node(host: Any) -> Any:
    """The folder to search from: the highlighted node if it is one, else
    the nearest folder above it, so searching while on a station searches
    the folder that station is in. None if nothing searchable is selected."""
    tree = host._tree
    try:
        node = tree.GetSelection()
    except RuntimeError:
        return None
    while node is not None and node.IsOk():
        if host._is_folder_data(host._node_data(node)):
            return node
        node = tree.GetItemParent(node)
    return None


def on_find(host: Any) -> None:
    query = host._find_ctrl.GetValue().strip()
    if not query:
        host._announce("Type something to find in this folder.")
        return
    anchor = find_anchor_node(host)
    if anchor is None:
        host._announce("Highlight a source or folder to search in first.")
        return
    data = host._node_data(anchor)
    if data is None:
        return
    node_id = str(data["node_id"])
    label = host._tree.GetItemText(anchor)
    host._announce(f"Searching {label} for {query}...")

    def _work(**_kwargs: Any) -> tuple[list[dict], bool, str]:
        # The fast, branch-aware route first (Apple's search API, the local
        # catalog); the bounded crawl only when no faster channel fits.
        from quill.core.radio import branch_find

        fast = branch_find.fast_find(
            node_id,
            query,
            safe_mode=host._safe_mode,
            catalog=getattr(host, "_catalog", None),
        )
        if fast is not None:
            nodes, provenance = fast
            return [{**host._row_data(n), "note": n.note} for n in nodes], False, provenance
        matches, capped = find_matches(host, node_id, query)
        return matches, capped, ""

    def _ok(_op: str, result: object) -> None:
        # Already on the UI thread (call_ui_safely marshals + guards this);
        # call directly. A second raw CallAfter would run outside that guard,
        # so a closed dialog would hit a destroyed TreeCtrl and raise.
        matches, capped, provenance = result if isinstance(result, tuple) else ([], False, "")
        show_find_results(host, anchor, label, matches, capped, provenance=provenance)

    host._task_manager.submit("radio-browse-find", _work, on_success=_ok, on_failure=None)


def show_find_results(
    host: Any,
    anchor: Any,
    label: str,
    matches: list[dict],
    capped: bool,
    *,
    provenance: str = "",
) -> None:
    if not host._tree:  # dialog closed while the search was in flight
        return
    tree = host._tree
    if not anchor.IsOk():
        return
    host._find_return_node = anchor
    host._find_active = True
    tree.DeleteChildren(anchor)
    for node_data in matches:
        # The note travels with the row: a ccMixter result keeps its licence,
        # a TuneIn result keeps "resolves when you play it". A search result
        # stripped of what its source said about it is a worse row than the
        # one browsing would have shown.
        text = str(node_data["label"])
        note = str(node_data.get("note") or "")
        child = tree.AppendItem(anchor, f"{text}  ({note})" if note else text)
        tree.SetItemData(child, node_data)
        if host._is_folder_data(node_data):
            # A fast route can answer with folders (a podcast show that expands
            # into its episodes); give each its lazy placeholder so it does.
            tree.SetItemData(tree.AppendItem(child, "Loading..."), dict(host._placeholder()))
    if not matches:
        empty = tree.AppendItem(anchor, f"No matches in {label}.")
        tree.SetItemData(empty, dict(host._placeholder()))
    anchor_data = host._node_data(anchor)
    if anchor_data is not None:
        anchor_data["loaded"] = True  # results replace the normal lazy children
    tree.Expand(anchor)
    count = len(matches)
    more = " Showing the first results; search a smaller folder for the rest." if capped else ""
    origin = f" {provenance.capitalize()}." if provenance else ""
    host._announce(
        f"{count} match{'es' if count != 1 else ''} in {label}.{origin}"
        f"{more} Clear to return to the folder."
    )
    first, _cookie = tree.GetFirstChild(anchor)
    if first.IsOk():
        tree.SelectItem(first)
        tree.SetFocus()


def clear_find(host: Any) -> None:
    # ChangeValue, not SetValue: this also runs from the empty-query reset
    # (typing then erasing the field), and SetValue would fire EVT_TEXT back
    # into that binding (see search_reset.bind_empty_query_reset's contract).
    host._find_ctrl.ChangeValue("")
    node = host._find_return_node
    host._find_return_node = None
    was_active = host._find_active
    host._find_active = False
    if node is None or not node.IsOk():
        return
    data = host._node_data(node)
    if host._is_folder_data(data) and data is not None:
        # Drop the result leaves and reset the folder to its unexpanded state,
        # so re-opening it browses normally again.
        data["loaded"] = False
        host._tree.DeleteChildren(node)
        host._tree.SetItemData(host._tree.AppendItem(node, "Loading..."), dict(host._placeholder()))
        host._tree.Collapse(node)
    host._tree.SelectItem(node)  # cursor back on the folder you searched from
    host._tree.SetFocus()
    if was_active:
        host._announce(f"Search cleared. Back on {host._tree.GetItemText(node)}.")
