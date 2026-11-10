"""GitHub Workbench Mode: one table for the GitHub menu in both editors (2026-11-08).

Workbench mode is a per-window switch, **View > GitHub Workbench Mode**, a
check item in QUILL and QUILL Lite. While it is on, a **GitHub** menu sits on
the bar right after Tools, and the GitHub rows that normally live in File and
Tools move into it. Nothing is duplicated and no key changes: a row keeps its
command id wherever it sits, and both editors render the label from whatever
is bound to that id, so a key the user assigned follows the row into the menu.

This module is the one table both editors build from, the way
:mod:`quill.core.wordpress.menu` and :mod:`quill.core.ai.ai_menu_layout` work:

* :data:`WORKBENCH_ROWS` is the GitHub menu, in order. Each :class:`Row` names
  QUILL's command id, and QUILL Lite's handler when QUILL Lite has the row.
  QUILL Lite's menu is therefore a subset of QUILL's by construction -- the
  small product is never ahead of the big one.
* :data:`NORMAL_REMOTE_ROWS`, :data:`REPOSITORY_ROWS` and :data:`LOCAL_GIT_ROWS`
  are where QUILL's moved rows sit while the mode is off (File > Open from
  Remote, Tools > Git and GitHub > GitHub and Local Git), and
  :data:`LITE_NORMAL_HANDLERS` is the same for QUILL Lite's File menu, so leaving
  the mode is read from the same module as entering it.
* :func:`fill` appends a list of entries to a menu through callbacks, so the same
  code serves wx menus and the tests' stand-ins.
* :func:`lite_arrange` turns QUILL Lite's resolved command rows into the bar for
  one mode.

The switch has no chord (rule 9: a few presses a day at most, and no chord is
free in both keymaps). Neither does any row here: every GitHub command in both
keymaps is keyless for the reason on the ``github.*`` block in ``keymap.py``.

wx-free and strict-typed.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from typing import Any

__all__ = [
    "ANNOUNCE_OFF",
    "ANNOUNCE_ON",
    "GITHUB_MENU_KEY",
    "GITHUB_MENU_TITLE",
    "LITE_GITHUB_MENU",
    "LITE_NORMAL_HANDLERS",
    "LOCAL_GIT_ROWS",
    "MOVED_OUT_ROWS",
    "NEW_COMMAND_IDS",
    "NORMAL_REMOTE_ROWS",
    "REPOSITORY_ROWS",
    "STATUS_CELL_HELP",
    "STATUS_CELL_KEY",
    "STATUS_CELL_LABEL",
    "TOGGLE_COMMAND_ID",
    "TOGGLE_LITE_HANDLER",
    "TOGGLE_VIEW_LABEL",
    "WORKBENCH_ROWS",
    "Entry",
    "Row",
    "Submenu",
    "command_ids",
    "fill",
    "lite_arrange",
    "lite_handlers",
    "lite_rows",
    "readout_label",
    "status_cell_text",
]

#: The menu's title on the bar. G is free on both bars.
GITHUB_MENU_TITLE = "&GitHub"
#: The stable key the QUILL Menu Editor files the menu under, so a person's
#: arrangement survives the menu coming and going with the mode.
GITHUB_MENU_KEY = "github"

#: The switch: one command id, two labels -- a check item in View, and the first
#: row of the GitHub menu, so the way out is where you already are.
TOGGLE_COMMAND_ID = "view.github_workbench_mode"
TOGGLE_LITE_HANDLER = "cmd_toggle_github_workbench"
#: K: the only letter of its name the View menus of both editors left free.
TOGGLE_VIEW_LABEL = "GitHub Wor&kbench Mode"

#: What is said on the way in and out (GATE-13: the bar changed somewhere the
#: screen reader is not looking, so it is the one thing the reader cannot say).
ANNOUNCE_ON = "Workbench mode on. GitHub menu added."
ANNOUNCE_OFF = "Workbench mode off."


@dataclass(frozen=True, slots=True)
class Row:
    """One menu row: QUILL's command id, its label, and QUILL Lite's handler.

    ``lite_handler`` is ``""`` when QUILL Lite has no such command.
    """

    command_id: str
    label: str
    lite_handler: str = ""


@dataclass(frozen=True, slots=True)
class Submenu:
    """A submenu: its title (with its access letter) and its entries."""

    title: str
    entries: tuple[Entry, ...]


#: A row, a submenu, or ``None`` for a separator.
Entry = Row | Submenu | None


# ---------------------------------------------------------------------------
# The rows that move, in their normal homes (QUILL)
# ---------------------------------------------------------------------------

#: File > Open from Remote's GitHub rows while the mode is off, after the
#: generic remote rows. Clone Repository is new here (2026-11-08).
NORMAL_REMOTE_ROWS: tuple[Entry, ...] = (
    Row("file.open_github_repository", "&GitHub Repository..."),
    Row("github.clone_repository", "C&lone Repository...", "cmd_github_clone"),
    Row("file.open_github_file_url", "GitHub File &URL..."),
    # T: Commit's own letters went to Copy (C) and Manage Remote Sites (M).
    Row("file.github_save_back", "Commi&t to GitHub..."),
    Row("file.open_github_items", "GitHub &Items...", "cmd_github_workbench"),
    Row("file.open_github_reference", "Open GitHub &Reference..."),
    Row("file.github_manage_accounts", "Ma&nage GitHub Accounts...", "cmd_github_manage_accounts"),
)

#: The repository admin rows: Tools > Git and GitHub > GitHub while the mode is
#: off (after Open a Repository and Sync Folder), the Repository Admin submenu
#: while it is on.
_ADMIN_ROWS: tuple[Entry, ...] = (
    Row("github.create_repository", "&Create Repository..."),
    Row("github.fork_repository", "&Fork Repository..."),
    Row("github.rename_repository", "&Rename Repository..."),
    Row("github.change_repository_visibility", "Change &Visibility..."),
    Row("github.change_default_branch", "Change &Default Branch..."),
    Row("github.configure_branch_protection", "Configure Branch &Protection..."),
    Row("github.delete_branch", "D&elete Branch..."),
    Row("github.commit_multiple_files", "Commit &Multiple Files..."),
    None,
    Row("github.browse_organization", "&Browse Organization Repositories..."),
    Row("github.create_release", "Cre&ate Release..."),
    Row("github.dispatch_workflow", "Dispatch &Workflow..."),
    Row("github.view_security_alerts", "&Security Alerts..."),
)

#: The Codespaces submenu of the GitHub menu.
_CODESPACE_ROWS: tuple[Entry, ...] = (
    Row("github.list_codespaces", "&Codespaces..."),
    Row("github.create_codespace", "C&reate Codespace..."),
)
#: The same two rows in Tools > Git and GitHub > GitHub, where C and R are
#: Create and Rename Repository's: no free letter, so none (GATE-14's third fix).
_CODESPACE_ROWS_NORMAL: tuple[Entry, ...] = (
    Row("github.list_codespaces", "Codespaces..."),
    Row("github.create_codespace", "Create Codespace..."),
)

#: Tools > Git and GitHub > GitHub while the mode is off.
REPOSITORY_ROWS: tuple[Entry, ...] = (
    Row("file.open_github_repository", "&Open a Repository..."),
    Row("sync.sync_folder", "S&ync Folder with GitHub..."),
    None,
    *_ADMIN_ROWS[:12],
    Row("github.view_notifications", "&Notifications...", "cmd_github_notifications"),
    *_ADMIN_ROWS[12:],
    None,
    *_CODESPACE_ROWS_NORMAL,
)

#: Tools > Git and GitHub > Local Git while the mode is off; the Local Git
#: submenu of the GitHub menu while it is on.
LOCAL_GIT_ROWS: tuple[Entry, ...] = (
    Row("localgit.uncommitted_changes", "&Uncommitted Changes..."),
    Row("localgit.switch_branch", "Switch &Branch..."),
    None,
    Row("localgit.stash_changes", "&Stash Changes..."),
    Row("localgit.manage_stashes", "Manage St&ashes..."),
    None,
    Row("localgit.blame_at_cursor", "&Who Wrote This Line..."),
    None,
    Row("localgit.bisect_start", "S&tart Bisect..."),
    Row("localgit.bisect_reset", "&End Bisect"),
    None,
    Row("localgit.resolve_conflicts", "&Resolve Conflicts..."),
    Row("localgit.interactive_rebase", "&Interactive Rebase..."),
    Row("localgit.rebase_abort", "Ab&ort Rebase"),
    None,
    Row("localgit.worktrees", "Wor&ktrees..."),
    Row("localgit.new_worktree", "&New Worktree..."),
)

#: QUILL Lite's File rows that move into the GitHub menu, by handler.
LITE_NORMAL_HANDLERS: tuple[str, ...] = (
    "cmd_github_workbench",
    "cmd_github_clone",
    "cmd_github_manage_accounts",
)


# ---------------------------------------------------------------------------
# The GitHub menu
# ---------------------------------------------------------------------------

#: The GitHub menu, in order: a short list of doors into the GitHub Workbench
#: window (GitHub PRD section 6, Phase 4). The repository readout (a disabled
#: row, the one exemption from the accelerator rule) goes above all of it when
#: the window knows a repository; see :func:`readout_label`.
WORKBENCH_ROWS: tuple[Entry, ...] = (
    # V: L is Local Git's, below.
    Row(TOGGLE_COMMAND_ID, "Lea&ve Workbench Mode", TOGGLE_LITE_HANDLER),
    None,
    # The doors: the Workbench, and the places people open it for.
    Row("file.open_github_items", "Open GitHub &Workbench", "cmd_github_workbench"),
    Row("github.workbench_inbox", "&Inbox", "cmd_github_inbox"),
    # S: I is Inbox's.
    Row("github.workbench_issues", "This Repository's I&ssues", "cmd_github_issues"),
    Row("github.workbench_pulls", "This Repository's &Pull Requests", "cmd_github_pulls"),
    Row("github.workbench_actions_runs", "&Actions Runs", "cmd_github_actions_runs"),
    None,
    # D: A is Actions Runs'. QUILL only: QUILL Lite has no such command.
    Row("file.open_github_reference", "Open GitHub A&ddress..."),
    Row("github.clone_repository", "&Clone Repository...", "cmd_github_clone"),
    None,
    # The working copy (QUILL only: QUILL Lite has no such commands).
    Row("file.github_save_back", "Co&mmit to GitHub..."),
    Row("sync.sync_folder", "S&ync Folder with GitHub..."),
    Submenu("&Local Git", LOCAL_GIT_ROWS),
    None,
    # A few times a year, so last, as the AI menu's Accounts and Usage is.
    Row("file.github_manage_accounts", "Mana&ge GitHub Accounts...", "cmd_github_manage_accounts"),
    # H: G is Manage Accounts'. Help keeps its own row too.
    Row("help.github_guide", "Open Git&Hub Guide", "cmd_github_guide"),
)

#: The rows that left the GitHub menu in Phase 4 (GitHub PRD section 6). Each
#: keeps its command id, its registration and any key somebody bound to it,
#: and opens the Workbench at the matching place (My Work, Notifications,
#: Releases, Repository Items, Explore GitHub) or runs as before (Repository
#: Admin and Codespaces, which the Workbench's Repository > Repository
#: Actions... now lists). Inbox is the one door for "what needs me".
MOVED_OUT_ROWS: tuple[Row, ...] = (
    Row("github.workbench_my_work", "My &Work...", "cmd_github_my_work"),
    Row("github.view_notifications", "&Notifications...", "cmd_github_notifications"),
    Row("github.workbench_releases", "R&eleases...", "cmd_github_releases"),
    Row("github.workbench_explore", "E&xplore GitHub...", "cmd_github_explore"),
    Row("file.open_github_repository", "&Open a Repository..."),
    Row("file.open_github_file_url", "GitHub File &URL..."),
    *(row for row in _ADMIN_ROWS if isinstance(row, Row)),
    *(row for row in _CODESPACE_ROWS if isinstance(row, Row)),
)

#: The command ids this program added (everything else in the table existed).
NEW_COMMAND_IDS: tuple[str, ...] = (
    TOGGLE_COMMAND_ID,
    "github.workbench_inbox",
    "github.workbench_my_work",
    "github.workbench_issues",
    "github.workbench_actions_runs",
    "github.workbench_releases",
    "github.workbench_explore",
    "github.clone_repository",
    # Phase 4 (GitHub PRD section 6): the Workbench's Pull Requests door.
    "github.workbench_pulls",
)


#: The status-bar readout both editors show while the mode is on (2026-11-08):
#: its key in each editor's cell table, the name a screen reader gives it, and
#: what F1 says about it. It is never announced (GATE-13): entering and leaving
#: the mode already is, and the cell's text is only ever read when somebody
#: arrives on it.
STATUS_CELL_KEY = "workbench"
STATUS_CELL_LABEL = "Workbench"
STATUS_CELL_HELP = (
    "GitHub Workbench Mode is on, and this is the repository the GitHub menu works "
    "on: the one the current document belongs to. It reads Workbench alone when the "
    "document is not in a GitHub repository. Shown only while the mode is on; "
    "View, GitHub Workbench Mode turns it off."
)


def status_cell_text(repository: str) -> str:
    """``"Workbench: owner/name"``, or ``"Workbench"`` when no repository is known."""
    name = (repository or "").strip()
    return f"{STATUS_CELL_LABEL}: {name}" if name else STATUS_CELL_LABEL


def readout_label(repository: str) -> str:
    """The disabled first row, or ``""`` when the window knows no repository.

    Omitted rather than reading "none": a row that says nothing is still a row
    somebody has to listen past.
    """
    name = (repository or "").strip()
    return f"Repository: {name}" if name else ""


def _walk(entries: Iterable[Entry]) -> Iterable[Row]:
    for entry in entries:
        if isinstance(entry, Row):
            yield entry
        elif isinstance(entry, Submenu):
            yield from _walk(entry.entries)


def command_ids(entries: Iterable[Entry] = WORKBENCH_ROWS) -> list[str]:
    """Every command id in *entries*, submenus included, in order."""
    return [row.command_id for row in _walk(entries)]


def lite_handlers(entries: Iterable[Entry] = WORKBENCH_ROWS) -> list[str]:
    """QUILL Lite's handlers in *entries*, in order."""
    return [row.lite_handler for row in _walk(entries) if row.lite_handler]


def _lite_only(entries: Sequence[Entry]) -> tuple[Entry, ...]:
    """*entries* with QUILL-only rows and empty submenus removed, then tidied."""
    kept: list[Entry] = []
    for entry in entries:
        if isinstance(entry, Row):
            if entry.lite_handler:
                kept.append(entry)
        elif isinstance(entry, Submenu):
            inner = _lite_only(entry.entries)
            if inner:
                kept.append(Submenu(entry.title, inner))
        else:
            kept.append(None)
    return _tidy(kept)


def _tidy(entries: Sequence[Entry]) -> tuple[Entry, ...]:
    """No separator first, last, or twice in a row."""
    out: list[Entry] = []
    for entry in entries:
        if entry is None and (not out or out[-1] is None):
            continue
        out.append(entry)
    while out and out[-1] is None:
        out.pop()
    return tuple(out)


#: QUILL Lite's GitHub menu: :data:`WORKBENCH_ROWS` less QUILL's own rows.
LITE_GITHUB_MENU: tuple[Entry, ...] = _lite_only(WORKBENCH_ROWS)


def fill(
    menu: Any,
    entries: Sequence[Entry],
    append_row: Callable[[Any, Row], None],
    new_menu: Callable[[], Any],
    *,
    keep: Callable[[Row], bool] | None = None,
) -> int:
    """Append *entries* to *menu*; return how many rows and submenus went in.

    *keep*, when given, answers whether a row goes in at all (a host leaves out
    a row whose feature is off). A separator is only written between two things
    that both went in, and a submenu left with nothing in it is not attached,
    so a host that leaves rows out never ends up with a dangling separator or an
    empty submenu -- either of which a screen reader dutifully reads out.
    """
    count = 0
    pending_separator = False
    for entry in entries:
        if entry is None:
            pending_separator = count > 0
            continue
        if isinstance(entry, Submenu):
            sub = new_menu()
            if not fill(sub, entry.entries, append_row, new_menu, keep=keep):
                continue
            if pending_separator:
                menu.AppendSeparator()
                pending_separator = False
            menu.AppendSubMenu(sub, entry.title)
            count += 1
            continue
        if keep is not None and not keep(entry):
            continue
        if pending_separator:
            menu.AppendSeparator()
            pending_separator = False
        append_row(menu, entry)
        count += 1
    return count


# ---------------------------------------------------------------------------
# QUILL Lite
# ---------------------------------------------------------------------------

#: One row of QUILL Lite's command table: ``(menu, label, key, handler, kind)``.
LiteRow = tuple[str, str, str, str, str]


def lite_rows() -> tuple[LiteRow, ...]:
    """The GitHub menu's own rows for QUILL Lite's command table.

    Only the commands that exist *nowhere else* in that table (Inbox, the three
    repository doors, and the rows that left the menu in Phase 4 but keep their
    command: My Work, Notifications, Releases, Explore): the moved rows keep
    their one row in File, the switch its row in View and the guide its row in
    Help, so every handler is in the table once. :func:`lite_arrange` builds the
    real menu, which holds only :data:`LITE_GITHUB_MENU`; the rest stay in the
    Command Palette.
    """
    elsewhere = {*LITE_NORMAL_HANDLERS, TOGGLE_LITE_HANDLER, "cmd_github_guide"}
    moved = tuple(row for row in MOVED_OUT_ROWS if row.lite_handler)
    return tuple(
        (GITHUB_MENU_TITLE, row.label, "", row.lite_handler, "")
        for row in (*_walk(LITE_GITHUB_MENU), *moved)
        if row.lite_handler not in elsewhere
    )


def lite_arrange(
    rows: Sequence[LiteRow], *, workbench: bool, repository: str = ""
) -> list[LiteRow]:
    """QUILL Lite's resolved rows arranged for one mode.

    Off: the GitHub menu's rows are dropped and everything else is as it was.
    On: the moved File rows leave File and the GitHub menu is built from
    :data:`LITE_GITHUB_MENU`, right after Tools, each row carrying the key the
    command resolved to wherever it sat -- so a key the user bound follows the
    row. The switch and the guide keep their own rows in View and Help too, and
    sit in the GitHub menu as a second, keyless route (a label can carry a key
    only once on a bar). Rows whose area is switched off simply are not there to
    move, and the GitHub menu goes with them. *repository*, when known, becomes
    the menu's first row: a disabled readout (kind ``"readout"``).
    """
    if not workbench:
        return [row for row in rows if row[0] != GITHUB_MENU_TITLE]
    by_handler = {row[3]: row for row in rows if row[4] not in {"sep", "sub"} and row[3]}
    if TOGGLE_LITE_HANDLER not in by_handler:
        # GitHub is switched off in this window: there is nothing to arrange.
        return [row for row in rows if row[0] != GITHUB_MENU_TITLE]
    moved = set(LITE_NORMAL_HANDLERS)
    second_routes = {TOGGLE_LITE_HANDLER, "cmd_github_guide"}
    menu: list[LiteRow] = []
    for entry in LITE_GITHUB_MENU:
        if entry is None:
            if menu and menu[-1][4] != "sep":
                menu.append((GITHUB_MENU_TITLE, "", "", "", "sep"))
            continue
        if not isinstance(entry, Row):
            continue  # QUILL Lite's menu has no submenus
        found = by_handler.get(entry.lite_handler)
        if found is None:
            continue
        key = "" if entry.lite_handler in second_routes else found[2]
        menu.append((GITHUB_MENU_TITLE, entry.label, key, entry.lite_handler, ""))
    while menu and menu[-1][4] == "sep":
        menu.pop()
    readout = readout_label(repository)
    if readout:
        # kind "readout": a disabled row the bar builders append unbound.
        menu.insert(0, (GITHUB_MENU_TITLE, readout, "", "", "readout"))
    out: list[LiteRow] = []
    placed = False
    for row in rows:
        if row[0] == GITHUB_MENU_TITLE:
            continue
        if row[3] in moved and row[4] not in {"sep", "sub"}:
            continue
        if not placed and row[0].split("|", 1)[0] not in _BEFORE_GITHUB:
            out.extend(menu)
            placed = True
        out.append(row)
    if not placed:
        out.extend(menu)
    return _lite_tidy(out)


#: The menus that come before GitHub on QUILL Lite's bar: Microsoft's order up to
#: Tools, where the menu-shape gate first allows a menu Microsoft does not have.
_BEFORE_GITHUB = frozenset({"&File", "&Edit", "&View", "&Insert", "F&ormat", "&Navigate", "&Tools"})


def _lite_tidy(rows: list[LiteRow]) -> list[LiteRow]:
    """Drop separators a moved row left first, last or doubled in its menu.

    Grouped by menu path in order of first appearance, which is the order both
    of QUILL Lite's bar builders use anyway.
    """
    groups: dict[str, list[LiteRow]] = {}
    for row in rows:
        groups.setdefault(row[0], []).append(row)
    out: list[LiteRow] = []
    for items in groups.values():
        cleaned: list[LiteRow] = []
        for row in items:
            if row[4] == "sep" and (not cleaned or cleaned[-1][4] == "sep"):
                continue
            cleaned.append(row)
        while cleaned and cleaned[-1][4] == "sep":
            cleaned.pop()
        out.extend(cleaned)
    return out
