"""The Tutorials window's contents page: the filter, the tree, and the buttons.

Extracted from :mod:`quill.ui.tutorials_window` under GATE-11 (extract, never
rebaseline). It is a clean seam: the contents page is a list you search and
choose from, the lesson page is one step at a time, and the two share only the
window they sit in. Functions take the window rather than being methods on it,
so the split is a real one rather than a file with two halves of a class.

Like the window itself, this is shared by every app that has lessons: it reads
the tracks and tutorials off the window's own :class:`TutorialSet` and never
names an app.
"""

from __future__ import annotations

from typing import Any

from quill.core.tutorials.model import Tutorial, contents_label
from quill.core.tutorials.progress import summary
from quill.ui import tutorial_checks
from quill.ui.dialog_contract import show_message_box


def build(window: Any, parent: Any) -> None:
    """Fill the contents panel, and wire it back to *window*."""
    wx = window._wx
    sizer = wx.BoxSizer(wx.VERTICAL)
    sizer.Add(
        wx.StaticText(parent, label="&Find a tutorial (or type 'here' for this window):"),
        0,
        wx.ALL,
        8,
    )
    window._filter = wx.TextCtrl(parent, style=wx.TE_PROCESS_ENTER)
    window._filter.SetName("Filter the tutorials")
    window._filter.SetHelpText(
        "Narrows the list below: every word you type has to appear somewhere in "
        "a tutorial -- its title, a step, a key, or the window it is about. Type "
        "'here' for the tutorials about the window you came from. Enter moves "
        "into the list."
    )
    sizer.Add(window._filter, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)

    window._status = wx.StaticText(parent, label=status_text(window, len(window._catalogue)))
    sizer.Add(window._status, 0, wx.ALL, 8)

    window._tree = wx.TreeCtrl(
        parent,
        style=wx.TR_HIDE_ROOT | wx.TR_HAS_BUTTONS | wx.TR_LINES_AT_ROOT | wx.TR_SINGLE,
    )
    window._tree.SetName("Tutorials, grouped by track")
    window._tree.SetHelpText(
        "Tracks, each holding its tutorials. Right arrow opens a track, Enter "
        "starts the tutorial you are on -- or picks it up where you left it. "
        "Each row says how many steps it has, roughly how long it takes, and "
        "whether you have finished it."
    )
    sizer.Add(window._tree, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)

    row = wx.BoxSizer(wx.HORIZONTAL)
    window._start_btn = wx.Button(parent, label="St&art")
    window._start_btn.SetHelpText(
        "Opens the selected tutorial at the step you left it on, or at step one."
    )
    window._read_btn = wx.Button(parent, label="&Read it all")
    window._read_btn.SetHelpText(
        "Shows the whole tutorial as one page of text to arrow through, instead "
        "of one step at a time."
    )
    window._book_btn = wx.Button(parent, label="The whole book as a &document")
    window._book_btn.SetHelpText(
        f"Opens all {len(window._catalogue)} tutorials as one page in your browser, "
        "for reading straight through or printing. It states the keys this app "
        "ships with; only this window can know the ones you rebound."
    )
    window._forget_btn = wx.Button(parent, label="Forget my &progress")
    window._forget_btn.SetHelpText(
        "Clears where you had got to in every tutorial. It changes nothing else and asks first."
    )
    for button in (window._start_btn, window._read_btn, window._book_btn, window._forget_btn):
        row.Add(button, 0, wx.RIGHT, 6)
    sizer.Add(row, 0, wx.ALL, 8)
    parent.SetSizer(sizer)

    window._filter.Bind(wx.EVT_TEXT, lambda _e: rebuild_tree(window))
    window._filter.Bind(wx.EVT_TEXT_ENTER, lambda _e: enter_the_list(window))
    window._tree.Bind(wx.EVT_TREE_ITEM_ACTIVATED, lambda _e: window._start_selected())
    window._start_btn.Bind(wx.EVT_BUTTON, lambda _e: window._start_selected())
    window._read_btn.Bind(wx.EVT_BUTTON, lambda _e: window._start_selected(whole=True))
    window._book_btn.Bind(wx.EVT_BUTTON, lambda _e: window._open_book())
    window._forget_btn.Bind(wx.EVT_BUTTON, lambda _e: forget_progress(window))
    rebuild_tree(window)


def enter_the_list(window: Any) -> None:
    """Enter in the filter box: say what is left, then move into the tree.

    Said on Enter rather than on every keystroke (GATE-12 wants a label change
    spoken; GATE-13 wants nothing said that the reader already says). Typing
    changes a label nobody is looking at, so the count is worth one sentence at
    the moment somebody commits to the filtered list -- and the tree itself
    announces each row from there.
    """
    if callable(getattr(window, "_announce", None)):
        window._announce(status_text(window, len(matching(window))))
    window._tree.SetFocus()


def status_text(window: Any, shown: int) -> str:
    return f"{summary(window._progress, len(window._catalogue))} Showing {shown}."


def front_window_title(window: Any) -> str:
    """The window this one was opened over, for "tutorials about here".

    The newest registered window that is not this one. Captured before this
    window registers itself, which is why it is worth a function rather than a
    lookup at the moment somebody types.
    """
    own = window._title
    titles = [title for title in tutorial_checks.open_titles(window._host) if title != own]
    if titles:
        return titles[-1]
    home = tutorial_checks.peer_windows(window._app.app_id)
    return next(iter(sorted(home)), "")


def here_hint(window: Any) -> str:
    """The one sentence worth saying on open, or "".

    Said because it is something only this window knows and the screen reader
    will not say: that some of these lessons are about the window you just
    left. Said once, on open, and never repeated.
    """
    here = window._catalogue.for_surface(window._came_from)
    if not here:
        return ""
    count = len(here)
    lesson = "tutorial" if count == 1 else "tutorials"
    return f"{count} {lesson} here are about {window._came_from}. Type 'here' to see just those."


def matching(window: Any) -> list[Tutorial]:
    query = window._filter.GetValue().strip()
    if query.lower() == "here":
        here = window._catalogue.for_surface(window._came_from)
        if here:
            return here
    return window._catalogue.search(query)


def rebuild_tree(window: Any) -> None:
    shown = matching(window)
    window._tree.DeleteAllItems()
    window._rows = {}
    root = window._tree.AddRoot("tutorials")
    for track in window._catalogue.tracks:
        lessons = [tutorial for tutorial in shown if tutorial.track == track.id]
        if not lessons:
            continue
        node = window._tree.AppendItem(root, f"{track.title}, {len(lessons)} tutorials")
        for tutorial in lessons:
            label = contents_label(tutorial, window._progress.get(tutorial.slug))
            item = window._tree.AppendItem(node, label)
            window._rows[item] = tutorial.slug
        window._tree.Expand(node)
    window._status.SetLabel(status_text(window, len(shown)))
    first = window._tree.GetFirstVisibleItem()
    if first and first.IsOk():
        window._tree.SelectItem(first)


def selected_slug(window: Any) -> str:
    item = window._tree.GetSelection()
    if not item or not item.IsOk():
        return ""
    return str(window._rows.get(item, ""))


def forget_progress(window: Any) -> None:
    wx = window._wx
    answer = show_message_box(
        "Forget where you had got to in every tutorial? Nothing else changes.",
        "Forget my progress",
        wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION,
        window._win,
        announce=window._announce,
    )
    if answer != wx.YES:
        return
    count = window._progress.forget_all()
    window._save_progress()
    rebuild_tree(window)
    window._say(f"Forgot your place in {count} tutorials.")
