"""View, Go and the Filter menu in the GitHub Workbench (GitHub PRD 4, 17; Part C, C5).

The GitHub provider's half of the bar's View and Go rows:

- **View > Show, Open or Closed, Sort By:** radio rows, the choice kept per
  window until changed, and the Issues lists load accordingly.
- **View > Quick Filters:** each toggle writes or removes its qualifier in
  the one filter box (:mod:`quill.core.github.filter_menu`), checked while it
  is on, and named in the window title and the Items cell.
- **Show Only and Hide** on any cell of a row (its context menu), the same
  query again.
- **Group By:** the groups become tree nodes under the list's node.
- **Local filtering, honestly:** what GitHub's search cannot answer (Has
  Conflicts) is checked over the loaded rows and the Items cell says so,
  with Load All (Ctrl+Shift+Page Down) to be sure.
- **Columns...** chooses the list's columns, remembered per view.
- **Go > Next and Previous Unread** (Ctrl+Period, Ctrl+Shift+Period), and the
  dynamic Pinned, Favorites and saved-search submenus.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from quill.core.github.filter_menu import (
    TOGGLES,
    active,
    cell_choices,
    clear_toggles,
    group_rows,
    local_only,
    local_status,
    matches_local,
    show_only,
    toggle,
    toggle_words,
)
from quill.core.github.items_provider import GitHubItem

__all__ = ["GitHubWorkbenchViewMixin", "row_values"]

_P = "github.workbench."
_TOGGLE_KEYS = {item.key for item in TOGGLES}
_VALUE_PROMPTS = {"assigned_to": "Assigned to (a login)", "opened_by": "Opened by (a login)"}


def row_values(row: object) -> dict[str, object]:
    """A row's attributes for Show Only, Group By and local filtering."""
    if isinstance(row, GitHubItem):
        return {
            "labels": row.labels,
            "assignees": row.assignees,
            "author": row.author,
            "state": row.state,
            "review": row.review_status,
            "base": row.base_branch,
            "head": row.head_branch,
            "repository": "",
        }
    repo = str(getattr(row, "repo", "") or "")
    return {"repo": repo, "repository": repo}


class GitHubWorkbenchViewMixin:
    """View, Go and filters for the GitHub provider."""

    items: Any
    frame: Any
    _say: Callable[[str], None]
    _ask_text: Callable[..., str]
    _view: dict[str, str]
    local_note: str = ""
    _load_all_for: Any = None

    # -- state -----------------------------------------------------------------

    def view_choice(self, name: str) -> str:
        if getattr(self, "_view", None) is None:
            from quill.core.github.workbench_prefs import load_prefs

            prefs = load_prefs()
            self._view = {"show": "", "state": "", "sort": prefs.default_sort, "group": "none"}
            self._default_state = prefs.default_state
        return self._view.get(name, "")

    def state_in_force(self) -> str:
        """The chosen Open or Closed, or the Workbench Options default until one is chosen."""
        return self.view_choice("state") or getattr(self, "_default_state", "open")

    def is_checked(self, command_id: str) -> bool:
        verb = command_id.removeprefix(_P)
        for name in ("show", "state", "sort", "group"):
            if verb.startswith(f"{name}_"):
                current = self.view_choice(name) or {
                    "show": "both",
                    "state": self.state_in_force(),
                }.get(name, "")
                return verb == f"{name}_{current}"
        if verb.startswith("filter_") and verb[7:] in _TOGGLE_KEYS:
            frame = self.frame
            return frame is not None and verb[7:] in active(frame.filter.GetValue())
        return False

    def supports_view(self, command_id: str) -> bool:
        verb = command_id.removeprefix(_P)
        if verb.startswith(("show_", "state_", "sort_", "group_")):
            return True
        if verb.startswith("filter_"):
            return verb[7:] in _TOGGLE_KEYS or verb == "filter_clear"
        if verb in ("show_only_cell", "hide_cell"):
            return self._selected_row() is not None
        return verb in ("columns", "load_all", "next_unread", "previous_unread")

    def _selected_row(self) -> object | None:
        return self.frame.selected_row() if self.frame is not None else None

    def run_view(self, command_id: str) -> bool:
        """The View and Go rows above; False when *command_id* is not one of them."""
        verb = command_id.removeprefix(_P)
        frame = self.frame
        if frame is None or not self.supports_view(command_id):
            return False
        for name in ("show", "state", "sort", "group"):
            if verb.startswith(f"{name}_"):
                self.view_choice(name)
                self._view[name] = verb[len(name) + 1 :]
                if name == "group":
                    self.apply_grouping()
                elif name == "sort":
                    frame.reload()
                else:
                    frame.reload()
                return True
        if verb == "filter_clear":
            frame.filter.ChangeValue(clear_toggles(frame.filter.GetValue()))
            frame.apply_filter()
            return True
        if verb.startswith("filter_"):
            self._toggle(verb[7:])
            return True
        actions = {
            "columns": self.choose_columns,
            "load_all": self.load_all,
            "next_unread": lambda: self.move_unread(1),
            "previous_unread": lambda: self.move_unread(-1),
        }
        actions[verb]()
        return True

    # -- filters ---------------------------------------------------------------

    def _toggle(self, key: str) -> None:
        frame = self.frame
        text = frame.filter.GetValue()
        value = ""
        if key in _VALUE_PROMPTS and key not in active(text):
            value = self._ask_text(_VALUE_PROMPTS[key].split(" (")[0], _VALUE_PROMPTS[key] + ":")
            if not value:
                return
        frame.filter.ChangeValue(toggle(text, key, value.lstrip("@")))
        frame.apply_filter()

    def cell_rows(self) -> list[tuple[str, str]]:
        """Show Only and Hide, for each value in the selected row (its context menu)."""
        row = self._selected_row()
        return cell_choices(row_values(row)) if row is not None else []

    def show_only_cell(self, qualifier: str, *, hide: bool = False) -> None:
        frame = self.frame
        frame.filter.ChangeValue(show_only(frame.filter.GetValue(), qualifier, hide=hide))
        frame.apply_filter()

    def split_query(self, text: str) -> tuple[str, list[tuple[str, str, bool]]]:
        return local_only(text)

    def filter_locally(self, rows: list[object], text: str, *, complete: bool) -> list[object]:
        """Rows that meet the local conditions in *text*; the note says it honestly."""
        _server, local = local_only(text)
        if not local:
            self.local_note = ""
            return rows
        kept = [row for row in rows if matches_local(self._local_values(row), local)]
        self.local_note = local_status(len(rows), len(kept), complete=complete)
        return kept

    def _local_values(self, row: object) -> dict[str, object]:
        values = row_values(row)
        if isinstance(row, GitHubItem) and row.is_pr:
            values["conflicts"] = getattr(self, "_merge_states", {}).get(row.number, "")
        return values

    def fetch_merge_states(self, repository: str, rows: list[object]) -> None:
        """Each loaded pull request's merge state, for Has Conflicts (off the UI thread)."""
        api = self.github_api()  # type: ignore[attr-defined]
        found: dict[int, str] = {}
        for row in rows:
            if isinstance(row, GitHubItem) and row.is_pr:
                try:
                    answer = api.rest("GET", f"/repos/{repository}/pulls/{row.number}")
                except Exception:  # noqa: BLE001 - an unknown state is not a conflict
                    continue
                data = answer.data if isinstance(answer.data, dict) else {}
                found[row.number] = str(data.get("mergeable_state") or "")
        self._merge_states = found

    def title_words(self) -> str:
        """The filters on, for the window title: ", assigned to me, no milestone"."""
        frame = self.frame
        words = toggle_words(frame.filter.GetValue()) if frame is not None else ""
        return f", {words}" if words else ""

    def after_fill(self, frame: Any) -> None:
        """After a list fills: the title names the filters, the groups are rebuilt."""
        current = frame.current
        instance = current.instance if current is not None else ""
        state = self.state_in_force()
        what = f"{len(frame.rows)} shown ({state})"
        title = f"{self.window_title(instance)} - {what}{self.title_words()}"  # type: ignore[attr-defined]
        frame.frame.SetTitle(title)
        if self.view_choice("group") != "none":
            self.apply_grouping()

    # -- grouping ----------------------------------------------------------------

    def apply_grouping(self) -> None:
        frame = self.frame
        field = self.view_choice("group")
        if field == "none":
            frame.show_groups([])
            return

        def values(row: object) -> list[str]:
            found = row_values(row)
            key = {"label": "labels", "assignee": "assignees", "type": "issue_type"}.get(
                field, field
            )
            value = found.get(key)
            if isinstance(value, tuple):
                return [str(v) for v in value]
            return [str(value)] if value else []

        groups = group_rows(list(frame.rows), field, values)
        frame.show_groups([(f"{name} ({len(rows)})", rows) for name, rows in groups])

    # -- columns, Load All, unread ------------------------------------------------

    def visible_columns(self, view: str, columns: tuple[str, ...]) -> tuple[str, ...]:
        try:
            from quill.ui.github_workbench_loaders import saved_items_for

            chosen = saved_items_for(self.items).get_columns(f"workbench:{view}", list(columns))
        except Exception:  # noqa: BLE001 - unreadable choices show every column
            return columns
        kept = tuple(c for c in chosen if c in columns)
        return kept or columns

    def choose_columns(self) -> None:
        frame = self.frame
        if frame.current is None:
            return
        node = frame.node(frame.current)
        everything = self.all_columns(node)  # type: ignore[attr-defined]
        if len(everything) < 2:
            self._say("This list has one column.")
            return
        wx = frame._wx
        from quill.ui.dialog_contract import show_modal_dialog

        shown = set(frame._columns)
        labels = [name.replace("_", " ").capitalize() for name in everything]
        with wx.MultiChoiceDialog(
            frame.frame, "Columns to show, in order:", "Columns", labels
        ) as dialog:
            dialog.SetSelections([i for i, name in enumerate(everything) if name in shown])
            if show_modal_dialog(dialog, "Columns") != wx.ID_OK:
                return
            picked = [everything[i] for i in dialog.GetSelections()]
        if not picked:
            self._say("Keep at least one column.")
            return
        from quill.ui.github_workbench_loaders import saved_items_for

        saved = saved_items_for(self.items)
        saved.set_columns(f"workbench:{node.loader}", picked)
        frame._set_columns(node)
        frame._fill_list()
        self._say(f"{len(picked)} columns.")

    def load_all(self) -> None:
        frame = self.frame
        self._load_all_for = frame.current
        frame.reload()

    def page_limit(self, ref: Any, default: int) -> int:
        return 1000 if ref is not None and ref == self._load_all_for else default

    def move_unread(self, step: int) -> None:
        frame = self.frame
        rows = frame.rows
        if not rows:
            self._say("Nothing here.")
            return
        chosen = frame.selected_indices()
        start = chosen[0] if chosen else (-1 if step > 0 else len(rows))
        index = start + step
        while 0 <= index < len(rows):
            if str(getattr(rows[index], "label", "")).startswith("Unread"):
                for other in chosen:
                    frame.list.Select(other, False)
                frame.list.Select(index)
                frame.list.Focus(index)
                frame.list.EnsureVisible(index)
                frame.list.SetFocus()
                return
            index += step
        self._say("No more unread." if step > 0 else "No unread before this one.")

    # -- Go's dynamic submenus ------------------------------------------------------

    def dynamic_menu(self, key: str) -> list[tuple[str, Callable[[], None]]]:
        from quill.ui.github_workbench_loaders import saved_items_for

        try:
            saved = saved_items_for(self.items)
        except Exception:  # noqa: BLE001
            return []
        if key == "pinned":
            return [(repo, lambda r=repo: self._go_repository(r)) for repo in saved.pinned]
        if key == "favorites":
            return [
                (entry.title or entry.url, lambda e=entry: self._open_favorite(e.url))
                for entry in saved.favorites
            ]
        if key == "saved_searches":
            return [
                (query, lambda q=query: self._go_filtered("", "search_issues", "", q))  # type: ignore[attr-defined]
                for query in saved.searches or []
            ]
        return []

    def _go_repository(self, repository: str) -> None:
        target = self.add_instance("repository", repository)  # type: ignore[attr-defined]
        if target is None:
            return
        self.frame.rebuild_tree()
        self.frame.select(target)
        self.frame.tree.SetFocus()

    def _open_favorite(self, url: str) -> None:
        self._open_classic(None, None, reference=url)  # type: ignore[attr-defined]
