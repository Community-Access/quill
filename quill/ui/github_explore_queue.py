"""Attention queue controls for the GitHub Explore dialog."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime, timedelta

from quill.core.github.attention_queue import QUEUE_CATEGORIES
from quill.core.github.explore_models import ExploreRow
from quill.ui.dialog_contract import show_modal_dialog


def queue_item_key(row: ExploreRow) -> str:
    return row.url or f"{row.repo}/{row.kind}/{row.key}"


class GitHubExploreQueueMixin:
    """Adds settings and snooze actions for the attention queue."""

    def _attention_options_menu(self, _event: object) -> None:
        state = self._attention_state
        if state is None:
            self._announce("Load the attention queue before changing its filters.")
            return
        wx = self._wx
        menu = wx.Menu()

        def add(label: str, callback: Callable[[], None]) -> None:
            item_id = wx.NewIdRef()
            menu.Append(item_id, label)
            menu.Bind(wx.EVT_MENU, lambda _e, action=callback: action(), id=item_id)

        add("Choose Repositories...", self._configure_queue_repositories)
        add("Choose Categories...", self._configure_queue_categories)
        add("Save Current Filter...", self._save_queue_filter)
        if state.filters:
            menu.AppendSeparator()
            for saved_filter in state.filters:
                add(
                    f"Use Filter: {saved_filter.name}",
                    lambda name=saved_filter.name: self._apply_queue_filter(name),
                )
                add(
                    f"Remove Filter: {saved_filter.name}",
                    lambda name=saved_filter.name: self._remove_queue_filter(name),
                )
        menu.AppendSeparator()
        show_item = menu.AppendCheckItem(wx.NewIdRef(), "Show Snoozed Items")
        show_item.Check(self._include_snoozed)
        menu.Bind(
            wx.EVT_MENU,
            lambda event: self._set_include_snoozed(event.IsChecked()),
            id=show_item.GetId(),
        )
        try:
            self._queue_options_btn.PopupMenu(menu)
        finally:
            menu.Destroy()

    def _configure_queue_repositories(self) -> None:
        state = self._attention_state
        if state is None:
            return
        wx = self._wx
        with wx.TextEntryDialog(
            self.dialog,
            "Enter up to ten owner/repo names separated by commas. "
            "Leave blank to search all repositories.",
            "Attention Queue Repositories",
            value=", ".join(state.repositories),
        ) as dialog:
            dialog.SetName("Repositories included in the local attention queue")
            if (
                show_modal_dialog(dialog, "Attention Queue Repositories", announce=self._announce)
                != wx.ID_OK
            ):
                return
            value = dialog.GetValue()
        repositories = [
            part.strip()
            for part in value.replace(";", ",").replace("\n", ",").split(",")
            if part.strip()
        ]
        try:
            state.set_repositories(repositories)
        except ValueError as exc:
            self._show_error(str(exc), "Attention Queue Repositories")
            return
        state.save()
        self._announce(
            f"Attention queue scope saved for {len(state.repositories)} repositories."
            if state.repositories
            else "Attention queue will search all accessible repositories."
        )
        self._load(None)

    def _configure_queue_categories(self) -> None:
        state = self._attention_state
        if state is None:
            return
        wx = self._wx
        labels = [label for _key, label in QUEUE_CATEGORIES]
        with wx.MultiChoiceDialog(
            self.dialog,
            "Choose the kinds of work to include.",
            "Attention Queue Categories",
            labels,
        ) as dialog:
            dialog.SetSelections([
                index
                for index, (key, _label) in enumerate(QUEUE_CATEGORIES)
                if key in state.categories
            ])
            if (
                show_modal_dialog(dialog, "Attention Queue Categories", announce=self._announce)
                != wx.ID_OK
            ):
                return
            selections = dialog.GetSelections()
        if not selections:
            self._show_error("Choose at least one category.", "Attention Queue Categories")
            return
        state.set_categories([QUEUE_CATEGORIES[index][0] for index in selections])
        state.save()
        self._announce("Attention queue categories saved locally.")
        self._load(None)

    def _save_queue_filter(self) -> None:
        state = self._attention_state
        if state is None:
            return
        name = self._prompt("Name this repository and category filter:", "Save Attention Filter")
        if not name:
            return
        state.save_filter(name)
        self._announce(f"Saved attention filter {name} locally.")

    def _apply_queue_filter(self, name: str) -> None:
        if self._attention_state and self._attention_state.apply_filter(name):
            self._announce(f"Applied attention filter {name}.")
            self._load(None)

    def _remove_queue_filter(self, name: str) -> None:
        if self._attention_state and self._attention_state.remove_filter(name):
            self._announce(f"Removed attention filter {name} locally.")

    def _set_include_snoozed(self, include: bool) -> None:
        self._include_snoozed = include
        self._load(None)

    def _snooze_attention_item(self, key: str) -> None:
        if self._attention_state is None:
            return
        self._attention_state.snooze(key, datetime.now(UTC) + timedelta(days=1))
        self._announce("Item snoozed locally for one day. GitHub was not changed.")
        self._load(None)

    def _unsnooze_attention_item(self, key: str) -> None:
        if self._attention_state and self._attention_state.unsnooze(key):
            self._announce("Item unsnoozed locally. GitHub was not changed.")
            self._load(None)

    def _show_error(self, message: str, title: str) -> None:
        wx = self._wx
        with wx.MessageDialog(self.dialog, message, title, wx.OK | wx.ICON_ERROR) as dialog:
            show_modal_dialog(dialog, title, announce=self._announce)


__all__ = ["GitHubExploreQueueMixin", "queue_item_key"]
