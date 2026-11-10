"""The Explore context menu offers each row's actions in every view, not only in notifications.

A block for the notifications view was once added half-way through the row block, at
the outer indent, so everything after it -- Start in Local Worktree, the label actions,
snoozing -- was only ever offered while the notifications view was showing, where none
of those rows exist. These tests read what the menu offers without a window.
"""

from __future__ import annotations

from types import SimpleNamespace

from quill.core.github.explore_models import ExploreRow
from quill.ui.github_explore_context_menu import GitHubExploreContextMenuMixin


class _Explore(GitHubExploreContextMenuMixin):
    def __init__(self, view: str, *, authenticated: bool = True, snoozed: bool = False) -> None:
        self._view = view
        self._client = SimpleNamespace(_provider=SimpleNamespace(is_authenticated=authenticated))
        self._rows = [object()]
        self._query = SimpleNamespace(GetValue=lambda: "")
        self._on_start_issue_worktree = lambda *_args: None
        self._attention_state = (
            SimpleNamespace(is_snoozed=lambda _key: snoozed) if view == "attention" else None
        )

    def _view_key(self) -> str:
        return self._view

    def _add_community_actions(self, _add: object) -> None:
        pass

    def _add_wave4_actions(self, _menu: object, _add: object, _row: object) -> None:
        pass

    def __getattr__(self, name: str) -> object:
        # Every action is a dialog method; the menu only needs them to exist.
        if name.startswith("_"):
            return lambda *_args, **_kwargs: None
        raise AttributeError(name)


def _offered(explore: _Explore, row: ExploreRow | None) -> list[str]:
    labels: list[str] = []

    def add(label: str, _action: object, _enabled: bool = True) -> None:
        labels.append(label)

    explore._fill_context_menu(None, add, row)
    return labels


def test_an_issue_row_offers_a_local_worktree_outside_notifications() -> None:
    row = ExploreRow(label="Fix it", detail="", repo="owner/repo", kind="issue", key="12")
    assert "Start in Local Worktree..." in _offered(_Explore("search"), row)


def test_a_label_row_offers_edit_delete_and_find_in_the_labels_view() -> None:
    row = ExploreRow(label="bug", detail="", repo="owner/repo", kind="label", key="bug")
    labels = _offered(_Explore("labels"), row)
    assert {"Edit Label...", "Delete Label...", "Find Issues with Label"} <= set(labels)
    assert "Create Label..." in labels


def test_an_attention_row_can_be_snoozed_and_unsnoozed() -> None:
    row = ExploreRow(label="Review", detail="", repo="owner/repo", kind="pr", key="3")
    assert "Snooze for One Day" in _offered(_Explore("attention"), row)
    assert "Unsnooze Locally" in _offered(_Explore("attention", snoozed=True), row)


def test_mark_all_read_is_offered_only_in_notifications() -> None:
    row = ExploreRow(label="Thread", detail="", kind="notification", key="99")
    assert "Mark All Read..." in _offered(_Explore("notifications"), row)
    assert "Mark All Read..." not in _offered(_Explore("search"), row)
    assert "Mark All Read..." in _offered(_Explore("notifications"), None)


def _laid_out(explore: _Explore, row: ExploreRow | None) -> list[str]:
    """The top-level labels the menu shows once the Workbench rules lay it out."""
    from quill.ui.github_context_rows import ContextRows
    from quill.ui.github_explore_context_menu import VIEW_ROW_LABELS

    rows = ContextRows(view_labels=VIEW_ROW_LABELS)
    explore._fill_context_menu(rows, rows.add, row)

    class _Menu:
        def __init__(self) -> None:
            self.labels: list[str] = []

        def Append(self, _id: object, label: str) -> None:
            self.labels.append(label)

        def AppendSubMenu(self, _sub: object, label: str) -> None:
            self.labels.append(label)

        def Enable(self, *_args: object) -> None:
            pass

        def Bind(self, *_args: object, **_kwargs: object) -> None:
            pass

    fake_wx = SimpleNamespace(Menu=_Menu, NewIdRef=object, EVT_MENU=None)
    menu = _Menu()
    rows.populate(fake_wx, menu, item_selected=bool(row))
    return menu.labels


def test_the_first_row_is_what_enter_does() -> None:
    repo = ExploreRow(label="o/r", detail="", repo="o/r", kind="repo", key="o/r")
    assert _laid_out(_Explore("repositories"), repo)[0] == "Use Repository"
    note = ExploreRow(label="Thread", detail="", kind="notification", key="9")
    assert _laid_out(_Explore("notifications"), note)[0] == "Open"
    issue = ExploreRow(label="Fix", detail="", url="https://x", repo="o/r", kind="issue", key="1")
    assert _laid_out(_Explore("search"), issue)[0] == "Open on GitHub"


def test_view_rows_follow_the_items_own_rows_under_this_view() -> None:
    row = ExploreRow(label="bug", detail="", repo="o/r", kind="label", key="bug")
    labels = _laid_out(_Explore("labels"), row)
    assert "Refresh" not in labels
    assert "Create Label..." not in labels
    assert labels[-1] == "This View"
    assert "Refresh" in _laid_out(_Explore("labels"), None)
