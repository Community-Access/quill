from __future__ import annotations

import re
from pathlib import Path


def _menu_source() -> str:
    ui = Path(__file__).resolve().parents[3] / "quill" / "ui"
    return (
        (ui / "main_frame.py").read_text(encoding="utf-8")
        + "\n"
        + (ui / "main_frame_menu.py").read_text(encoding="utf-8")
        + "\n"
        + (ui / "main_frame_ssh.py").read_text(encoding="utf-8")
        + "\n"
        + (ui / "main_frame_github.py").read_text(encoding="utf-8")
        + "\n"
        + (ui / "main_frame_devtools.py").read_text(encoding="utf-8")
        + "\n"
        + (ui / "main_frame_braille.py").read_text(encoding="utf-8")
        + "\n"
        + (ui / "main_frame_braille_phase2.py").read_text(encoding="utf-8")
        + "\n"
        + (ui / "main_frame_braille_phase3.py").read_text(encoding="utf-8")
        + "\n"
        + (ui / "main_frame_power_tools_menu.py").read_text(encoding="utf-8")
    )


def test_menu_item_ids_have_menu_bindings() -> None:
    source = _menu_source()
    menu_ids = set(
        re.findall(
            r"\.(?:Append|AppendCheckItem|AppendRadioItem)\(\s*(self\._id_[A-Za-z0-9_]+)",
            source,
        )
    )
    bound_ids = set(
        re.findall(
            r"self\.frame\.Bind\(\s*wx\.EVT_MENU,.*?id\s*=\s*(self\._id_[A-Za-z0-9_]+)",
            source,
            flags=re.S,
        )
    )
    # Some mixins (e.g. main_frame_braille_phase3) bind a batch of items in a
    # loop over (id, handler) pairs and call Bind(..., id=loop_var), which the
    # literal-id regex above cannot see. Treat an id paired with a handler in a
    # (self._id_X, self.handler) tuple as bound — that is the loop-bind idiom.
    bound_ids |= set(
        re.findall(r"\(\s*(self\._id_[A-Za-z0-9_]+)\s*,\s*self\.[A-Za-z0-9_]+", source)
    )

    # These are handled by dynamic menu callbacks rather than direct id-specific
    # Bind(...) calls.
    dynamically_handled_ids = {
        "self._id_clear_recent",
        "self._id_clear_recent_sessions",
    }

    missing_bindings = menu_ids - bound_ids - dynamically_handled_ids
    assert missing_bindings == set()


def test_top_level_menu_append_order_is_conventional() -> None:
    # MENU-REORDER (menus.md Phase 1): top-level menus are attached in one place
    # in the conventional Windows order: File, Edit, View, Insert, Format,
    # Navigate, Search, (AI), Tools, Window, Help.
    source = _menu_source()

    # Accept both i18n-wrapped _("...") and bare string forms.
    def _find_menu(name: str, label: str) -> int:
        wrapped = f'menu_bar.Append({name}_menu, _("{label}"))'
        bare = f'menu_bar.Append({name}_menu, "{label}")'
        try:
            return source.index(wrapped)
        except ValueError:
            return source.index(bare)

    edit_index = _find_menu("edit", "&Edit")
    view_index = _find_menu("view", "&View")
    insert_index = _find_menu("insert", "&Insert")
    format_index = _find_menu("format", "F&ormat")
    navigate_index = _find_menu("navigate", "&Navigate")
    search_index = _find_menu("search", "&Search")
    tools_index = _find_menu("tools", "&Tools")

    assert (
        edit_index
        < view_index
        < insert_index
        < format_index
        < navigate_index
        < search_index
        < tools_index
    )


def test_update_toggle_is_in_help_menu_not_view_menu() -> None:
    source = _menu_source()
    assert "view_menu.AppendCheckItem(self._id_toggle_auto_check_updates" not in source
    # Accept both i18n-wrapped _("...") and bare string forms.
    support_marker = 'support_menu.Append(self._id_check_updates, _("Check for &Updates"))'
    support_bare = 'support_menu.Append(self._id_check_updates, "Check for &Updates")'
    help_marker = 'help_menu.Append(self._id_check_updates, _("Check for &Updates..."))'
    help_bare = 'help_menu.Append(self._id_check_updates, "Check for &Updates...")'
    assert support_marker in source or support_bare in source
    assert help_marker in source or help_bare in source
    support_index = source.index(support_marker if support_marker in source else support_bare)
    help_index = source.index(help_marker if help_marker in source else help_bare)
    assert support_index < help_index


def test_replace_menu_uses_interactive_replace_command() -> None:
    source = _menu_source()
    # Accept both i18n-wrapped _("...") and bare string forms.
    assert (
        '_menu_label(_("Rep&lace..."), "edit.replace")' in source
        or '_menu_label("Rep&lace...", "edit.replace")' in source
    )


def test_find_group_lives_in_edit_not_search() -> None:
    # menus.md Phase 3: in-document Find/Replace and the find-navigation commands
    # live in Edit; the Search menu is the cross-file search hub only.
    source = _menu_source()
    for fid in (
        "self._id_find",
        "self._id_replace",
        "self._id_find_next",
        "self._id_find_previous",
        "self._id_find_all_matches",
    ):
        assert re.search(rf"edit_menu\.Append\(\s*{re.escape(fid)}\b", source), fid
        assert not re.search(rf"search_menu\.Append\(\s*{re.escape(fid)}\b", source), fid
    assert re.search(r"search_menu\.Append\(\s*self\._id_search_in_files\b", source)
    assert re.search(r"search_menu\.Append\(\s*self\._id_replace_in_files\b", source)


def test_insert_link_is_not_duplicated_in_edit_menu() -> None:
    # MENU-3: Insert Link lives only in the Insert menu (its primary home); the
    # Edit menu must not also append the same edit.insert_link command.
    source = _menu_source()
    insert_link_appends = re.findall(
        r"(\w+_menu)\.Append\(\s*self\._id_insert_link\b",
        source,
    )
    assert insert_link_appends == ["insert_menu"], insert_link_appends


def test_publishing_actions_live_in_file_menu_not_top_level_publishing_menu() -> None:
    source = _menu_source()
    assert 'menu_bar.Append(publishing_menu, "P&ublishing")' not in source
    assert 'file_menu.AppendSubMenu(self._publishing_file_menu, _("P&ublish"))' in source
    assert (
        "self._publishing_file_menu.Append(\n                self._id_publishing_connections,"
        in source
    )
    assert (
        "self._publishing_file_menu.Append(\n"
        "                self._id_publishing_verify_connection," in source
    )
    assert (
        "self._publishing_file_menu.Append(\n"
        "                self._id_publishing_browse_content," in source
    )
    assert (
        "self._publishing_file_menu.Append(\n"
        "                self._id_publishing_create_draft," in source
    )
    assert (
        "self._publishing_file_menu.Append(\n"
        "                self._id_publishing_publish_current," in source
    )
    assert (
        "self._publishing_file_menu.Append(\n"
        "                self._id_publishing_create_page_draft," in source
    )
    assert (
        "self._publishing_file_menu.Append(\n"
        "                self._id_publishing_publish_current_page," in source
    )
    assert (
        "self._publishing_file_menu.Append(\n"
        "                self._id_publishing_compare_remote_item," in source
    )
    assert (
        "self._publishing_file_menu.Append(\n"
        "                self._id_publishing_update_remote_item," in source
    )
    assert (
        "self._publishing_file_menu.Append(\n"
        "                self._id_publishing_publish_remote_item," in source
    )
    assert "lambda _e: self._publish_open_remote_item()" in source
    assert (
        "self._publishing_file_menu.Append(\n"
        "                self._id_publishing_schedule_publish," in source
    )
    assert "lambda _e: self._schedule_publishing_publish()" in source
    assert "lambda _e: self._compare_publishing_remote_item()" in source


def test_publishing_menu_is_split_into_read_and_locked_send_halves() -> None:
    # The Publish submenu is gated in two independent halves so the read-only
    # inbound tools can ship while the content-send half stays locked off:
    #   - future.publishing_read (not locked): connections, verify, browse.
    #   - future.publishing (locked off, quill/core/feature_catalog.py): the
    #     create/update/publish/schedule send commands.
    # Construction (not just Command Palette filtering) must honor the split,
    # mirroring the core.glow pattern (ids stay unconditional; only .Append()
    # is gated).
    source = _menu_source()
    assert 'publishing_read_enabled = self._feature_enabled("future.publishing_read")' in source
    assert 'publishing_send_enabled = self._feature_enabled("future.publishing")' in source
    assert (
        "if publishing_read_enabled or publishing_send_enabled:\n"
        "            self._publishing_file_menu = wx.Menu()" in source
    )
    # Inbound items are gated by the read flag; send items by the locked flag.
    assert (
        "if publishing_read_enabled:\n"
        "            self._publishing_file_menu.Append(\n"
        "                self._id_publishing_connections," in source
    )
    assert (
        "if publishing_send_enabled:\n"
        "            self._publishing_file_menu.Append(\n"
        "                self._id_publishing_create_draft," in source
    )
    assert (
        "        if publishing_read_enabled or publishing_send_enabled:\n"
        "            file_menu.AppendSeparator()\n"
        '            file_menu.AppendSubMenu(self._publishing_file_menu, _("P&ublish"))' in source
    )


def test_menu_builder_only_calls_power_tools_helpers_that_exist() -> None:
    source = _menu_source()
    helper_names = set(re.findall(r"def (_append_power_tools_[A-Za-z0-9_]+)\(", source))
    called_helpers = set(re.findall(r"self\.(_append_power_tools_[A-Za-z0-9_]+)\(", source))

    missing_helpers = {name for name in called_helpers if name not in helper_names}
    assert missing_helpers == set()


# ---------------------------------------------------------------------------
# #613: macOS Help menu is registered as the system Help menu.
# ---------------------------------------------------------------------------


def test_macos_help_menu_is_marked_as_system_help_menu() -> None:
    """#613: on macOS, the Help menu must be marked as the system Help
    menu (via menu_bar.SetHelpMenu or MacSetHelpMenuTitle) so the OS
    moves it to the rightmost position, where macOS users expect
    it. Without this hint, wx leaves the menu in the slot the bar
    gave it and VoiceOver users see a top-level menu order that
    does not match the macOS AppKit convention."""
    source = _menu_source()
    # The platform gate is required so the call only runs on macOS
    # (a Windows build that touches the wx method with the wrong
    # signature should be a no-op, not a startup crash).
    assert 'platform.system() == "Darwin"' in source, (
        "#613: SetHelpMenu must be gated on the macOS platform check"
    )
    # Either the modern SetHelpMenu API or the classic
    # MacSetHelpMenuTitle API must be called.
    assert "SetHelpMenu(" in source or "MacSetHelpMenuTitle(" in source, (
        "#613: macOS Help-menu hook must call SetHelpMenu or MacSetHelpMenuTitle"
    )
    # The call must be wrapped so a wx build without the API degrades
    # gracefully (do not raise out of menu construction).
    assert "except Exception" in source, (
        "#613: SetHelpMenu must be wrapped in try/except so an "
        "incompatible wx build degrades to the bar-order fallback"
    )
