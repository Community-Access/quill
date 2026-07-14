from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError, available_timezones

from quill.core.publishing import (
    PublishingConnectionProfile,
    current_publishing_connection,
    load_publishing_connections,
    load_publishing_remote_item,
    load_publishing_secret,
    remove_publishing_connection,
    save_publishing_secret,
    set_current_publishing_connection,
    upsert_publishing_connection,
    verify_publishing_connection,
)
from quill.core.publishing_clients import PublishingRemoteDocument, PublishingRemoteItemSummary
from quill.core.publishing_providers import (
    auth_method_definition,
    available_publishing_providers,
    provider_auth_methods,
    provider_content_kind_label,
    provider_content_kinds,
    publishing_auth_method_name,
    publishing_provider_display_name,
)
from quill.core.publishing_schedule import validate_scheduled_publish_time
from quill.core.publishing_worker import browse_publishing_content_task
from quill.stability.task_manager import CancelledError, TaskManager
from quill.ui.dialog_contract import (
    apply_listbox_activation,
    apply_modal_ids,
    show_message_box,
    show_modal_dialog,
)

_TIMEZONE_CHOICES = sorted(available_timezones())


@dataclass(frozen=True, slots=True)
class ScheduledPublishChoice:
    content_kind: str
    scheduled_at: datetime


class EditPublishingConnectionDialog:
    def __init__(
        self,
        parent: object,
        profile: PublishingConnectionProfile | None = None,
        *,
        announce_cb: Callable[[str], None] | None = None,
    ) -> None:
        import wx

        self._wx = wx
        self._announce = announce_cb or (lambda _message: None)
        self._provider_choices = tuple(
            (item.id, item.name) for item in available_publishing_providers()
        )
        self.dialog = wx.Dialog(
            parent,
            title="Edit Publishing Connection",
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        self.dialog.SetSize((760, 560))

        self._profile = profile or PublishingConnectionProfile()
        self._secret = load_publishing_secret(self._profile.id) if self._profile.id else ""
        self.last_verification_ok: bool | None = None
        self.last_verification_message: str = "Not checked"

        root = wx.BoxSizer(wx.VERTICAL)
        root.Add(
            wx.StaticText(
                self.dialog,
                label=(
                    "Create or edit a publishing connection. Quill stays generic until you "
                    "choose a provider, then shows the sign-in options known for that provider."
                ),
            ),
            0,
            wx.EXPAND | wx.ALL,
            8,
        )

        panel = wx.Panel(self.dialog)
        panel_sizer = wx.BoxSizer(wx.VERTICAL)
        form = wx.FlexGridSizer(0, 2, 8, 8)
        form.AddGrowableCol(1, 1)

        def add_row(label: object, control: object) -> None:
            form.Add(label, 0, wx.ALIGN_CENTER_VERTICAL | wx.LEFT, 8)
            form.Add(control, 1, wx.EXPAND | wx.RIGHT, 8)

        self.connection_label_caption = wx.StaticText(panel, label="Connection name")
        self.connection_label = wx.TextCtrl(panel)
        self.connection_label.SetValue(self._profile.label)
        self.connection_label.SetName("Connection name")
        add_row(self.connection_label_caption, self.connection_label)

        self.provider_caption = wx.StaticText(panel, label="Publishing type")
        self.provider = wx.Choice(
            panel,
            choices=[label for _value, label in self._provider_choices],
        )
        self.provider.SetName("Publishing type")
        self.provider.SetSelection(self._provider_choice_index(self._profile.provider_id))
        add_row(self.provider_caption, self.provider)

        self.site_url_caption = wx.StaticText(panel, label="Site address")
        self.site_url = wx.TextCtrl(panel)
        self.site_url.SetValue(self._profile.site_url)
        self.site_url.SetName("Site address")
        add_row(self.site_url_caption, self.site_url)

        self.auth_method_caption = wx.StaticText(panel, label="Sign-in method")
        self.auth_method = wx.Choice(panel)
        self.auth_method.SetName("Sign-in method")
        add_row(self.auth_method_caption, self.auth_method)

        self.identifier_label = wx.StaticText(panel, label="Username or email")
        self.account_identifier = wx.TextCtrl(panel)
        self.account_identifier.SetValue(self._profile.account_identifier)
        self.account_identifier.SetName("Username or email")
        form.Add(self.identifier_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.LEFT, 8)
        form.Add(self.account_identifier, 1, wx.EXPAND | wx.RIGHT, 8)

        self.secret_label = wx.StaticText(panel, label="Application password")
        self.secret_row = wx.BoxSizer(wx.HORIZONTAL)
        self.secret_stack = wx.BoxSizer(wx.VERTICAL)
        self.secret_masked = wx.TextCtrl(panel, style=wx.TE_PASSWORD)
        self.secret_masked.SetValue(self._secret)
        self.secret_masked.SetName("Application password")
        self.secret_plain = wx.TextCtrl(panel)
        self.secret_plain.SetValue(self._secret)
        self.secret_plain.SetName("Application password")
        self.secret_plain.Hide()
        self.secret = self.secret_masked
        self.secret_stack.Add(self.secret_masked, 1, wx.EXPAND)
        self.secret_stack.Add(self.secret_plain, 1, wx.EXPAND)
        self.secret_row.Add(self.secret_stack, 1, wx.EXPAND | wx.RIGHT, 8)
        self.reveal_secret = wx.Button(panel, label="Reveal")
        self.reveal_secret.SetName("Reveal application password")
        self.secret_row.Add(self.reveal_secret, 0)
        form.Add(self.secret_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.LEFT, 8)
        form.Add(self.secret_row, 1, wx.EXPAND | wx.RIGHT, 8)

        panel_sizer.Add(form, 0, wx.EXPAND | wx.TOP | wx.BOTTOM, 8)

        self.verify_button = wx.Button(panel, label="Verify Connection")
        panel_sizer.Add(self.verify_button, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)
        self.connection_status = wx.StaticText(
            panel, label="Save and verify this connection before publishing."
        )
        panel_sizer.Add(self.connection_status, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        panel.SetSizer(panel_sizer)
        root.Add(panel, 1, wx.EXPAND | wx.ALL, 8)

        buttons = self.dialog.CreateButtonSizer(wx.OK | wx.CANCEL)
        if buttons is not None:
            root.Add(buttons, 0, wx.EXPAND | wx.ALL, 8)
        self.dialog.SetSizerAndFit(root)
        apply_modal_ids(self.dialog, affirmative_id=wx.ID_OK, escape_id=wx.ID_CANCEL)
        self.provider.Bind(wx.EVT_CHOICE, self._on_provider_changed)
        self.auth_method.Bind(wx.EVT_CHOICE, self._on_auth_method_changed)
        self.verify_button.Bind(wx.EVT_BUTTON, self._on_verify_connection)
        self.reveal_secret.Bind(wx.EVT_BUTTON, self._on_toggle_secret_reveal)
        self._secret_revealed = False
        self._on_provider_changed(None)
        self._restore_secret_tab_order()
        self.connection_label.SetFocus()

    def _provider_choice_index(self, provider_id: str) -> int:
        normalized = provider_id.strip().lower()
        for index, (value, _label) in enumerate(self._provider_choices):
            if value == normalized:
                return index
        return 0

    def _provider_value(self) -> str:
        selection = self.provider.GetSelection()
        if selection < 0 or selection >= len(self._provider_choices):
            return self._provider_choices[0][0]
        return self._provider_choices[selection][0]

    def _auth_method_value(self) -> str:
        selection = self.auth_method.GetSelection()
        methods = provider_auth_methods(self._provider_value())
        if selection < 0 or selection >= len(methods):
            return methods[0]
        return methods[selection]

    def _current_profile(self) -> PublishingConnectionProfile:
        return PublishingConnectionProfile(
            id=self._profile.id or "",
            label=self.connection_label.GetValue().strip(),
            provider_id=self._provider_value(),
            site_url=self.site_url.GetValue().strip(),
            auth_method=self._auth_method_value(),
            account_identifier=self.account_identifier.GetValue().strip(),
            content_format="html",
        )

    def _on_provider_changed(self, _event: object | None) -> None:
        provider_id = self._provider_value()
        methods = provider_auth_methods(provider_id)
        self.auth_method.SetItems([publishing_auth_method_name(item) for item in methods])
        try:
            selection = methods.index(self._profile.auth_method)
        except ValueError:
            selection = 0
        self.auth_method.SetSelection(selection)
        self._on_auth_method_changed(None)

    def _on_auth_method_changed(self, _event: object | None) -> None:
        method = auth_method_definition(self._auth_method_value())
        self.identifier_label.Show(method.requires_identifier)
        self.account_identifier.Show(method.requires_identifier)
        self.secret_label.Show(method.requires_secret)
        self.secret.Show(method.requires_secret)
        self.reveal_secret.Show(method.requires_secret)
        self.secret_label.SetLabel(
            "Application password" if method.requires_secret else "Saved sign-in secret"
        )
        if not method.requires_secret:
            self._set_secret_revealed(False)
        self.dialog.Layout()

    def _on_toggle_secret_reveal(self, _event: object) -> None:
        self._set_secret_revealed(not self._secret_revealed)

    def _set_secret_revealed(self, revealed: bool) -> None:
        value = self.secret.GetValue()
        self.secret_masked.SetValue(value)
        self.secret_plain.SetValue(value)
        self.secret_masked.Show(not revealed)
        self.secret_plain.Show(revealed)
        self.secret = self.secret_plain if revealed else self.secret_masked
        self._secret_revealed = revealed
        self.reveal_secret.SetLabel("Hide" if revealed else "Reveal")
        self.reveal_secret.SetName(
            "Hide application password" if revealed else "Reveal application password"
        )
        self._restore_secret_tab_order()
        self.dialog.Layout()

    def _restore_secret_tab_order(self) -> None:
        self.reveal_secret.MoveAfterInTabOrder(self.secret)
        self.verify_button.MoveAfterInTabOrder(self.reveal_secret)

    def _on_verify_connection(self, _event: object) -> None:
        ok, message = verify_publishing_connection(self._current_profile(), self.secret.GetValue())
        self.last_verification_ok = ok
        self.last_verification_message = message
        self.connection_status.SetLabel(message)
        self._announce(message)
        icon = self._wx.ICON_INFORMATION if ok else self._wx.ICON_WARNING
        show_message_box(
            message,
            "Publishing Connection Check",
            icon | self._wx.OK,
            self.dialog,
            announce=self._announce,
        )

    def show_modal(self) -> PublishingConnectionProfile | None:
        self.dialog.CentreOnParent()
        try:
            if show_modal_dialog(self.dialog, "Edit Publishing Connection") != self._wx.ID_OK:
                return None
            draft = self._current_profile()
            had_id = bool(draft.id)
            store = upsert_publishing_connection(draft)
            saved = None
            if had_id:
                for item in store.connections:
                    if item.id == draft.id:
                        saved = item
                        break
            else:
                for item in reversed(store.connections):
                    if (
                        item.site_url == draft.site_url
                        and item.label == (draft.label or item.label)
                        and item.account_identifier == draft.account_identifier
                    ):
                        saved = item
                        break
            if saved is None:
                return None
            save_publishing_secret(saved.id, self.secret.GetValue())
            self._profile = saved
            return saved
        finally:
            self.dialog.Destroy()


class BrowsePublishingContentDialog:
    def __init__(
        self,
        parent: object,
        task_manager: TaskManager,
        *,
        announce_cb: Callable[[str], None] | None = None,
    ) -> None:
        import wx

        self._wx = wx
        self._task_manager = task_manager
        self._announce = announce_cb or (lambda _message: None)
        self._profile = current_publishing_connection()
        self._secret = load_publishing_secret(self._profile.id) if self._profile is not None else ""
        self._items: list[PublishingRemoteItemSummary] = []
        self._selected_document: PublishingRemoteDocument | None = None
        self.selected_open_representation = "readable_markdown"
        self._active_operation_id: str | None = None
        self._destroyed = False

        self.dialog = wx.Dialog(
            parent,
            title="Browse Publishing Content",
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        self.dialog.SetSize((860, 620))

        root = wx.BoxSizer(wx.VERTICAL)
        root.Add(
            wx.StaticText(
                self.dialog,
                label=(
                    "Browse publishing content from the current publishing connection, "
                    "then open one in Quill."
                ),
            ),
            0,
            wx.EXPAND | wx.ALL,
            8,
        )

        filters = wx.BoxSizer(wx.HORIZONTAL)
        self.content_scope_caption = wx.StaticText(self.dialog, label="Content to browse")
        filters.Add(self.content_scope_caption, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 8)
        self.content_scope = wx.Choice(
            self.dialog,
            choices=self._content_scope_choices(),
        )
        self.content_scope.SetName("Content to browse")
        self.content_scope.SetSelection(0)
        filters.Add(self.content_scope, 0)
        filters.AddSpacer(16)
        self.status_scope_caption = wx.StaticText(self.dialog, label="Status to browse")
        filters.Add(self.status_scope_caption, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 8)
        self.status_scope = wx.Choice(
            self.dialog,
            choices=["Published and drafts", "Published only", "Drafts only"],
        )
        self.status_scope.SetName("Status to browse")
        self.status_scope.SetSelection(0)
        filters.Add(self.status_scope, 0)
        filters.AddSpacer(16)
        self.open_as_caption = wx.StaticText(self.dialog, label="Open in Quill as")
        filters.Add(self.open_as_caption, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 8)
        self.open_as = wx.Choice(
            self.dialog,
            choices=["Readable Markdown", "Raw HTML"],
        )
        self.open_as.SetName("Open in Quill as")
        self.open_as.SetSelection(0)
        filters.Add(self.open_as, 0)
        root.Add(filters, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        load_row = wx.BoxSizer(wx.HORIZONTAL)
        self.load_button = wx.Button(self.dialog, label="Load Content")
        load_row.Add(self.load_button, 0, wx.RIGHT, 8)
        self.cancel_load_button = wx.Button(self.dialog, label="Cancel")
        self.cancel_load_button.SetName("Cancel loading publishing content")
        self.cancel_load_button.Hide()
        load_row.Add(self.cancel_load_button, 0)
        root.Add(load_row, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        root.Add(
            wx.StaticText(self.dialog, label="Publishing content"),
            0,
            wx.LEFT | wx.RIGHT,
            8,
        )
        self.content_list = wx.ListBox(self.dialog)
        self.content_list.SetName("Publishing content")
        root.Add(self.content_list, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        root.Add(
            wx.StaticText(self.dialog, label="Selected publishing content details"),
            0,
            wx.LEFT | wx.RIGHT,
            8,
        )
        self.summary = wx.TextCtrl(
            self.dialog,
            style=wx.TE_MULTILINE | wx.TE_READONLY | wx.BORDER_SIMPLE,
            size=(-1, 140),
        )
        self.summary.SetName("Selected publishing content details")
        root.Add(self.summary, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        buttons = wx.BoxSizer(wx.HORIZONTAL)
        self.open_button = wx.Button(self.dialog, wx.ID_OK, label="Open in Quill")
        self.open_button.SetName("Open in Quill")
        buttons.Add(self.open_button, 0, wx.RIGHT, 8)
        buttons.Add(wx.Button(self.dialog, wx.ID_CANCEL, label="Close"), 0)
        root.Add(buttons, 0, wx.EXPAND | wx.ALL, 8)

        self.dialog.SetSizerAndFit(root)
        apply_modal_ids(self.dialog, affirmative_id=wx.ID_OK, escape_id=wx.ID_CANCEL)
        self.load_button.Bind(wx.EVT_BUTTON, self._on_load)
        self.cancel_load_button.Bind(wx.EVT_BUTTON, self._on_cancel_load)
        self.content_list.Bind(wx.EVT_LISTBOX, self._on_selection_changed)
        apply_listbox_activation(self.content_list, self._on_open)
        self.open_button.Bind(wx.EVT_BUTTON, self._on_open)
        self._update_summary("Choose Load Content to browse publishing content.")
        self.content_scope.SetFocus()

    def _content_scope_choices(self) -> list[str]:
        kinds = self._available_kinds()
        if len(kinds) < 2:
            return [f"{self._content_kind_label(kinds[0])} only"] if kinds else ["Content"]
        choices = ["All content types"]
        choices.extend(f"{self._content_kind_label(kind)} only" for kind in kinds)
        return choices

    def _available_kinds(self) -> tuple[str, ...]:
        if self._profile is None:
            return ("post", "page")
        return provider_content_kinds(self._profile.provider_id)

    def _content_kind_label(self, content_kind: str) -> str:
        provider_id = self._profile.provider_id if self._profile is not None else "wordpress"
        return provider_content_kind_label(provider_id, content_kind)

    def _scope_kinds(self) -> tuple[str, ...]:
        available = self._available_kinds()
        selection = self.content_scope.GetSelection()
        if selection > 0:
            index = selection - 1
            if index < len(available):
                return (available[index],)
        return available

    def _scope_statuses(self) -> tuple[str, ...]:
        selection = self.status_scope.GetSelection()
        if selection == 1:
            return ("publish",)
        if selection == 2:
            return ("draft",)
        return ("publish", "draft")

    def _open_representation(self) -> str:
        if self.open_as.GetSelection() == 1:
            return "raw_html"
        return "readable_markdown"

    def _selected_item(self) -> PublishingRemoteItemSummary | None:
        selection = self.content_list.GetSelection()
        if selection == self._wx.NOT_FOUND or selection < 0:
            return None
        if selection >= len(self._items):
            return None
        return self._items[selection]

    def _item_label(self, item: PublishingRemoteItemSummary) -> str:
        kind = self._content_kind_label(item.content_kind)
        status = item.status or "unknown"
        return f"{kind}: {item.title} ({status})"

    def _update_summary(self, fallback: str | None = None) -> None:
        selected = self._selected_item()
        if selected is None:
            self.summary.SetValue(fallback or "No publishing content selected.")
            return
        lines = [
            f"Title: {selected.title}",
            f"Type: {self._content_kind_label(selected.content_kind)}",
            f"Status: {selected.status or 'unknown'}",
            f"Updated: {selected.updated_at or '(unknown)'}",
            f"Link: {selected.remote_url or '(not available)'}",
        ]
        self.summary.SetValue("\n".join(lines))

    def _on_load(self, _event: object) -> None:
        if self._profile is None:
            self._update_summary("No current publishing connection is selected.")
            return
        if self._active_operation_id is not None:
            return
        self._set_loading_state(True)
        self._update_summary("Loading publishing content...")
        task = self._task_manager.submit(
            name="publishing-browse",
            func=browse_publishing_content_task,
            on_success=self._on_browse_task_success,
            on_failure=self._on_browse_task_failure,
            profile=self._profile,
            secret=self._secret,
            content_kinds=self._scope_kinds(),
            statuses=self._scope_statuses(),
        )
        self._active_operation_id = task.operation_id

    def _set_loading_state(self, loading: bool) -> None:
        self.load_button.Enable(not loading)
        self.cancel_load_button.Show(loading)
        self.cancel_load_button.Enable(loading)
        self.open_button.Enable(not loading)
        self.dialog.Layout()

    def _on_cancel_load(self, _event: object) -> None:
        if self._active_operation_id is None:
            return
        self._task_manager.cancel(self._active_operation_id)
        self._active_operation_id = None
        self._set_loading_state(False)
        message = "Browse cancelled."
        self._update_summary(message)
        self._announce(message)

    def _on_browse_task_success(self, operation_id: str, result: object) -> None:
        if self._destroyed or operation_id != self._active_operation_id:
            return
        self._active_operation_id = None
        self._set_loading_state(False)
        ok, message, items = result
        self._items = items
        self.content_list.Set([self._item_label(item) for item in items])
        if items:
            self.content_list.SetSelection(0)
        self._update_summary(message if not items else None)
        if ok and items:
            self._update_summary()
        icon = self._wx.ICON_INFORMATION if ok else self._wx.ICON_WARNING
        show_message_box(
            message,
            "Browse Publishing Content",
            icon | self._wx.OK,
            self.dialog,
            announce=self._announce,
        )

    def _on_browse_task_failure(self, operation_id: str, exc: BaseException) -> None:
        if self._destroyed or operation_id != self._active_operation_id:
            return
        self._active_operation_id = None
        self._set_loading_state(False)
        if isinstance(exc, CancelledError):
            self._update_summary("Browse cancelled.")
            return
        message = f"Browse publishing content failed unexpectedly: {exc}"
        self._update_summary(message)
        show_message_box(
            message,
            "Browse Publishing Content",
            self._wx.ICON_WARNING | self._wx.OK,
            self.dialog,
            announce=self._announce,
        )

    def _on_selection_changed(self, _event: object) -> None:
        self._update_summary()

    def _on_open(self, _event: object) -> None:
        selected = self._selected_item()
        if selected is None or self._profile is None:
            self._update_summary("Select publishing content before opening it.")
            return
        ok, message, document = load_publishing_remote_item(
            self._profile,
            self._secret,
            content_kind=selected.content_kind,
            remote_id=selected.remote_id,
        )
        if not ok or document is None:
            show_message_box(
                message,
                "Browse Publishing Content",
                self._wx.ICON_WARNING | self._wx.OK,
                self.dialog,
                announce=self._announce,
            )
            self._update_summary(message)
            return
        self.selected_open_representation = self._open_representation()
        self._selected_document = document
        self.dialog.EndModal(self._wx.ID_OK)

    def show_modal(self) -> PublishingRemoteDocument | None:
        self.dialog.CentreOnParent()
        try:
            if show_modal_dialog(self.dialog, "Browse Publishing Content") != self._wx.ID_OK:
                return None
            return self._selected_document
        finally:
            self._destroyed = True
            if self._active_operation_id is not None:
                self._task_manager.cancel(self._active_operation_id)
                self._active_operation_id = None
            self.dialog.Destroy()


class PublishingConnectionsDialog:
    def __init__(
        self,
        parent: object,
        *,
        announce_cb: Callable[[str], None] | None = None,
    ) -> None:
        import wx

        self._wx = wx
        self._announce = announce_cb or (lambda _message: None)
        self.dialog = wx.Dialog(
            parent,
            title="Publishing Connections",
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        self.dialog.SetSize((820, 520))

        root = wx.BoxSizer(wx.VERTICAL)
        root.Add(
            wx.StaticText(self.dialog, label="Saved publishing connections"),
            0,
            wx.LEFT | wx.RIGHT | wx.TOP,
            8,
        )
        self.connection_list = wx.ListBox(self.dialog)
        self.connection_list.SetName("Saved publishing connections")
        root.Add(self.connection_list, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        root.Add(
            wx.StaticText(self.dialog, label="Selected publishing connection details"),
            0,
            wx.LEFT | wx.RIGHT,
            8,
        )
        self.summary = wx.TextCtrl(
            self.dialog,
            style=wx.TE_MULTILINE | wx.TE_READONLY | wx.BORDER_SIMPLE,
            size=(-1, 120),
        )
        self.summary.SetName("Selected publishing connection details")
        root.Add(self.summary, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        actions = wx.BoxSizer(wx.HORIZONTAL)
        self.add_button = wx.Button(self.dialog, label="Add")
        self.edit_button = wx.Button(self.dialog, label="Edit")
        self.remove_button = wx.Button(self.dialog, label="Remove")
        self.use_button = wx.Button(self.dialog, label="Use This Connection")
        self.verify_button = wx.Button(self.dialog, label="Verify Current Connection")
        actions.Add(self.add_button, 0, wx.RIGHT, 8)
        actions.Add(self.edit_button, 0, wx.RIGHT, 8)
        actions.Add(self.remove_button, 0, wx.RIGHT, 8)
        actions.Add(self.use_button, 0, wx.RIGHT, 8)
        actions.Add(self.verify_button, 0)
        root.Add(actions, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        buttons = self.dialog.CreateButtonSizer(wx.OK | wx.CANCEL)
        if buttons is not None:
            root.Add(buttons, 0, wx.EXPAND | wx.ALL, 8)
        self.dialog.SetSizerAndFit(root)
        apply_modal_ids(self.dialog, affirmative_id=wx.ID_OK, escape_id=wx.ID_CANCEL)

        self.connection_list.Bind(wx.EVT_LISTBOX, self._on_selection_changed)
        self.add_button.Bind(wx.EVT_BUTTON, self._on_add)
        self.edit_button.Bind(wx.EVT_BUTTON, self._on_edit)
        self.remove_button.Bind(wx.EVT_BUTTON, self._on_remove)
        self.use_button.Bind(wx.EVT_BUTTON, self._on_use)
        self.verify_button.Bind(wx.EVT_BUTTON, self._on_verify)

        self._store = load_publishing_connections()
        self._refresh_connections()
        self.connection_list.SetFocus()

    def _refresh_connections(self) -> None:
        labels: list[str] = []
        selection = 0
        for index, item in enumerate(self._store.connections):
            label = (
                item.label or item.site_url or publishing_provider_display_name(item.provider_id)
            )
            if item.id == self._store.current_connection_id:
                label += " (Current)"
                selection = index
            labels.append(label)
        self.connection_list.Set(labels)
        if labels:
            self.connection_list.SetSelection(selection)
        self._update_summary()

    def _selected_connection(self) -> PublishingConnectionProfile | None:
        selection = self.connection_list.GetSelection()
        if selection == self._wx.NOT_FOUND or selection < 0:
            return None
        if selection >= len(self._store.connections):
            return None
        return self._store.connections[selection]

    def _update_summary(self) -> None:
        selected = self._selected_connection()
        if selected is None:
            self.summary.SetValue("No publishing connection selected.")
            return
        method = auth_method_definition(selected.auth_method)
        lines = [
            f"Label: {selected.label or '(unnamed connection)'}",
            f"Provider: {publishing_provider_display_name(selected.provider_id)}",
            f"Site URL: {selected.site_url or '(not set)'}",
            f"Sign-in method: {method.name}",
        ]
        if method.requires_identifier:
            lines.append(f"Sign-in name or email: {selected.account_identifier or '(not set)'}")
        lines.append(
            "Current connection: yes"
            if selected.id == self._store.current_connection_id
            else "Current connection: no"
        )
        self.summary.SetValue("\n".join(lines))

    def _on_selection_changed(self, _event: object) -> None:
        self._update_summary()

    def _on_add(self, _event: object) -> None:
        dialog = EditPublishingConnectionDialog(self.dialog, announce_cb=self._announce)
        if dialog.show_modal() is None:
            return
        self._store = load_publishing_connections()
        self._refresh_connections()

    def _on_edit(self, _event: object) -> None:
        selected = self._selected_connection()
        if selected is None:
            return
        dialog = EditPublishingConnectionDialog(
            self.dialog,
            selected,
            announce_cb=self._announce,
        )
        if dialog.show_modal() is None:
            return
        self._store = load_publishing_connections()
        self._refresh_connections()

    def _on_remove(self, _event: object) -> None:
        selected = self._selected_connection()
        if selected is None:
            return
        answer = show_message_box(
            f"Remove the publishing connection '{selected.label or selected.site_url}'?",
            "Remove Publishing Connection",
            self._wx.YES_NO | self._wx.ICON_WARNING,
            self.dialog,
            announce=self._announce,
        )
        if answer != self._wx.YES:
            return
        self._store = remove_publishing_connection(selected.id)
        self._refresh_connections()

    def _on_use(self, _event: object) -> None:
        selected = self._selected_connection()
        if selected is None:
            return
        self._store = set_current_publishing_connection(selected.id)
        self._refresh_connections()

    def _on_verify(self, _event: object) -> None:
        selected = self._selected_connection()
        if selected is None:
            return
        secret = load_publishing_secret(selected.id)
        ok, message = verify_publishing_connection(selected, secret)
        icon = self._wx.ICON_INFORMATION if ok else self._wx.ICON_WARNING
        show_message_box(
            message,
            "Publishing Connection Check",
            icon | self._wx.OK,
            self.dialog,
            announce=self._announce,
        )
        self._announce(message)
        self.summary.SetValue(self.summary.GetValue() + f"\n\nLast check: {message}")

    def show_modal(self) -> bool:
        self.dialog.CentreOnParent()
        try:
            return show_modal_dialog(self.dialog, "Publishing Connections") == self._wx.ID_OK
        finally:
            self.dialog.Destroy()


class SchedulePublishDialog:
    def __init__(
        self,
        parent: object,
        *,
        provider_id: str,
        fixed_content_kind: str | None = None,
        announce_cb: Callable[[str], None] | None = None,
    ) -> None:
        import wx

        self._wx = wx
        self._announce = announce_cb or (lambda _message: None)
        self._provider_id = provider_id
        self._fixed_content_kind = fixed_content_kind
        self._content_kinds = provider_content_kinds(provider_id) or ("post", "page")

        self.dialog = wx.Dialog(
            parent,
            title="Schedule Publish",
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        self.dialog.SetSize((520, 380))

        root = wx.BoxSizer(wx.VERTICAL)
        root.Add(
            wx.StaticText(
                self.dialog,
                label=(
                    "Choose when this content should publish. Quill sends the document "
                    "and the chosen time to the publishing site only after you confirm."
                ),
            ),
            0,
            wx.EXPAND | wx.ALL,
            8,
        )

        panel = wx.Panel(self.dialog)
        form = wx.FlexGridSizer(0, 2, 8, 8)
        form.AddGrowableCol(1, 1)

        def add_row(label: object, control: object) -> None:
            form.Add(label, 0, wx.ALIGN_CENTER_VERTICAL | wx.LEFT, 8)
            form.Add(control, 1, wx.EXPAND | wx.RIGHT, 8)

        self.content_kind_caption = wx.StaticText(panel, label="Content type")
        if fixed_content_kind:
            self.content_kind: object = wx.StaticText(
                panel,
                label=provider_content_kind_label(provider_id, fixed_content_kind),
            )
        else:
            self.content_kind = wx.Choice(
                panel,
                choices=[
                    provider_content_kind_label(provider_id, kind) for kind in self._content_kinds
                ],
            )
            self.content_kind.SetSelection(0)
        self.content_kind.SetName("Content type")
        add_row(self.content_kind_caption, self.content_kind)

        self.date_caption = wx.StaticText(panel, label="Publish date (YYYY-MM-DD)")
        self.date = wx.TextCtrl(panel)
        self.date.SetName("Publish date (YYYY-MM-DD)")
        add_row(self.date_caption, self.date)

        self.time_caption = wx.StaticText(panel, label="Publish time (24-hour HH:MM)")
        self.time = wx.TextCtrl(panel)
        self.time.SetName("Publish time (24-hour HH:MM)")
        add_row(self.time_caption, self.time)

        self.timezone_caption = wx.StaticText(panel, label="Time zone")
        self.timezone = wx.Choice(panel, choices=_TIMEZONE_CHOICES)
        self.timezone.SetName("Time zone")
        self.timezone.SetSelection(self._default_timezone_index())
        add_row(self.timezone_caption, self.timezone)

        panel.SetSizer(form)
        root.Add(panel, 1, wx.EXPAND | wx.ALL, 8)

        self.status = wx.StaticText(
            self.dialog,
            label="Enter a future date, time, and time zone, then choose OK.",
        )
        root.Add(self.status, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        buttons = self.dialog.CreateButtonSizer(wx.OK | wx.CANCEL)
        if buttons is not None:
            root.Add(buttons, 0, wx.EXPAND | wx.ALL, 8)
        self.dialog.SetSizerAndFit(root)
        apply_modal_ids(self.dialog, affirmative_id=wx.ID_OK, escape_id=wx.ID_CANCEL)
        self.content_kind.SetFocus()

    def _default_timezone_index(self) -> int:
        try:
            return _TIMEZONE_CHOICES.index("UTC")
        except ValueError:
            return 0

    def _selected_content_kind(self) -> str:
        if self._fixed_content_kind:
            return self._fixed_content_kind
        selection = self.content_kind.GetSelection()
        if selection < 0 or selection >= len(self._content_kinds):
            return self._content_kinds[0]
        return self._content_kinds[selection]

    def _build_choice(self) -> tuple[ScheduledPublishChoice | None, str | None]:
        date_text = self.date.GetValue().strip()
        time_text = self.time.GetValue().strip()
        selection = self.timezone.GetSelection()
        zone_name = (
            _TIMEZONE_CHOICES[selection] if 0 <= selection < len(_TIMEZONE_CHOICES) else "UTC"
        )
        try:
            naive = datetime.strptime(f"{date_text} {time_text}", "%Y-%m-%d %H:%M")
        except ValueError:
            return None, "Enter the publish date as YYYY-MM-DD and time as 24-hour HH:MM."
        try:
            zone = ZoneInfo(zone_name)
        except ZoneInfoNotFoundError:
            return None, "Choose a valid time zone before scheduling."
        scheduled_at = naive.replace(tzinfo=zone)
        schedule_error = validate_scheduled_publish_time(scheduled_at)
        if schedule_error:
            return None, schedule_error
        return (
            ScheduledPublishChoice(
                content_kind=self._selected_content_kind(),
                scheduled_at=scheduled_at,
            ),
            None,
        )

    def show_modal(self) -> ScheduledPublishChoice | None:
        self.dialog.CentreOnParent()
        try:
            while True:
                if show_modal_dialog(self.dialog, "Schedule Publish") != self._wx.ID_OK:
                    return None
                choice, error = self._build_choice()
                if error:
                    self.status.SetLabel(error)
                    self._announce(error)
                    show_message_box(
                        error,
                        "Schedule Publish",
                        self._wx.ICON_WARNING | self._wx.OK,
                        self.dialog,
                        announce=self._announce,
                    )
                    continue
                return choice
        finally:
            self.dialog.Destroy()
