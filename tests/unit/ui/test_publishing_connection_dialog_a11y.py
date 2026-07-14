from __future__ import annotations

from pathlib import Path


def _publishing_tools_source() -> str:
    return Path("quill/ui/publishing_tools.py").read_text(encoding="utf-8")


def _edit_dialog_source() -> str:
    source = _publishing_tools_source()
    start = source.index("class EditPublishingConnectionDialog")
    end = source.index("class PublishingConnectionsDialog")
    return source[start:end]


def _manager_dialog_source() -> str:
    source = _publishing_tools_source()
    start = source.index("class PublishingConnectionsDialog")
    return source[start:]


def test_edit_connection_controls_set_accessible_names() -> None:
    body = _edit_dialog_source()
    assert 'self.connection_label.SetName("Connection name")' in body
    assert 'self.provider.SetName("Publishing type")' in body
    assert 'self.site_url.SetName("Site address")' in body
    assert 'self.auth_method.SetName("Sign-in method")' in body
    assert 'self.account_identifier.SetName("Username or email")' in body
    assert 'self.secret_masked.SetName("Application password")' in body
    assert 'self.secret_plain.SetName("Application password")' in body
    assert 'self.reveal_secret.SetName("Reveal application password")' in body


def test_manager_dialog_names_the_connections_list() -> None:
    body = _manager_dialog_source()
    assert 'wx.StaticText(self.dialog, label="Saved publishing connections")' in body
    assert 'self.connection_list.SetName("Saved publishing connections")' in body
    assert 'wx.StaticText(self.dialog, label="Selected publishing connection details")' in body
    assert 'self.summary.SetName("Selected publishing connection details")' in body


def test_browse_dialog_names_the_content_list() -> None:
    source = _publishing_tools_source()
    assert 'title="Browse Publishing Content"' in source
    assert 'wx.StaticText(self.dialog, label="Publishing content")' in source
    assert 'self.content_list.SetName("Publishing content")' in source
    assert 'wx.StaticText(self.dialog, label="Selected publishing content details")' in source
    assert 'self.summary.SetName("Selected publishing content details")' in source
    assert 'self.content_scope.SetName("Content to browse")' in source
    assert 'self.status_scope.SetName("Status to browse")' in source
    assert 'self.open_as.SetName("Open in Quill as")' in source
    assert (
        'self.status_scope_caption = wx.StaticText(self.dialog, label="Status to browse")' in source
    )


def test_publishing_dialogs_set_initial_focus_and_stable_secret_tab_order() -> None:
    source = _publishing_tools_source()
    assert "self.connection_label.SetFocus()" in source
    assert "self.connection_list.SetFocus()" in source
    assert "self.content_scope.SetFocus()" in source
    assert 'choices=["Published and drafts", "Published only", "Drafts only"]' in source
    assert "self.reveal_secret.MoveAfterInTabOrder(self.secret)" in source
    assert "self.verify_button.MoveAfterInTabOrder(self.reveal_secret)" in source
    assert "self.secret_masked = wx.TextCtrl(panel, style=wx.TE_PASSWORD)" in source
    assert "self.secret_plain = wx.TextCtrl(panel)" in source
    assert "self.secret_plain.Hide()" in source


def test_publishing_dialogs_keep_a_simple_label_then_control_flow() -> None:
    body = _edit_dialog_source()
    for helper_name in (
        "connection_label_hint",
        "provider_hint",
        "site_url_hint",
        "auth_hint",
        "account_identifier_hint",
        "secret_hint",
    ):
        assert helper_name not in body


def test_publishing_dialogs_keep_plain_language_status_copy() -> None:
    source = _publishing_tools_source()
    assert "Create or edit a publishing connection." in source
    assert "Save and verify this connection before publishing." in source
    assert "Browse publishing content from the current publishing connection" in source
    assert "Manage your saved publishing connections here." not in source


def test_publishing_dialog_labels_are_immediately_paired_with_controls() -> None:
    body = _edit_dialog_source()
    assert "wx.FlexGridSizer(0, 2, 8, 8)" in body
    assert "form.AddGrowableCol(1, 1)" in body
    assert 'self.connection_label_caption = wx.StaticText(panel, label="Connection name")' in body
    assert "self.connection_label = wx.TextCtrl(panel)" in body
    assert "add_row(self.connection_label_caption, self.connection_label)" in body
    assert 'self.provider_caption = wx.StaticText(panel, label="Publishing type")' in body
    assert "add_row(self.provider_caption, self.provider)" in body
    assert 'self.site_url_caption = wx.StaticText(panel, label="Site address")' in body
    assert "add_row(self.site_url_caption, self.site_url)" in body
    assert 'self.auth_method_caption = wx.StaticText(panel, label="Sign-in method")' in body
    assert "add_row(self.auth_method_caption, self.auth_method)" in body


def test_publishing_dialogs_do_not_rely_on_placeholder_examples_for_labels() -> None:
    body = _edit_dialog_source()
    assert ".SetHint(" not in body
    assert "self.secret.Destroy()" not in body


def test_publishing_dialog_only_surfaces_working_wordpress_sign_in_method() -> None:
    source = _publishing_tools_source()
    assert "provider_auth_methods(provider_id)" in source
    assert "provider_supported_auth_methods(" not in source
    assert "provider_help_text" not in source


def test_publishing_dialogs_have_no_storage_jargon() -> None:
    source = _publishing_tools_source()
    for term in ("Credential Manager", "DPAPI", "encrypted fallback"):
        assert term not in source


def test_publishing_dialogs_use_modal_contract() -> None:
    source = _publishing_tools_source()
    assert "apply_modal_ids(" in source
    assert "show_modal_dialog(" in source
    assert ".ShowModal()" not in source


def test_publishing_provider_choices_come_from_registry() -> None:
    body = _edit_dialog_source()
    assert "available_publishing_providers()" in body
    assert "_PROVIDER_CHOICES" not in body


def _browse_dialog_source() -> str:
    source = _publishing_tools_source()
    start = source.index("class BrowsePublishingContentDialog")
    end = source.index("class PublishingConnectionsDialog")
    return source[start:end]


def test_browse_dialog_dispatches_load_through_task_manager() -> None:
    body = _browse_dialog_source()
    assert "self._task_manager.submit(" in body
    assert "func=browse_publishing_content_task," in body
    assert "self._task_manager.cancel(" in body


def test_browse_dialog_has_named_cancel_button() -> None:
    body = _browse_dialog_source()
    assert 'self.cancel_load_button = wx.Button(self.dialog, label="Cancel")' in body
    assert 'self.cancel_load_button.SetName("Cancel loading publishing content")' in body
    assert "self.cancel_load_button.Hide()" in body


def test_browse_dialog_does_not_disable_or_trap_the_escape_button() -> None:
    body = _browse_dialog_source()
    assert "apply_modal_ids(self.dialog, affirmative_id=wx.ID_OK, escape_id=wx.ID_CANCEL)" in body
    assert 'wx.Button(self.dialog, wx.ID_CANCEL, label="Close")' in body
    assert 'self.cancel_load_button = wx.Button(self.dialog, label="Cancel")' in body


def test_browse_dialog_ignores_stale_task_callbacks() -> None:
    body = _browse_dialog_source()
    assert "if self._destroyed or operation_id != self._active_operation_id:" in body
    assert "self._destroyed = True" in body
