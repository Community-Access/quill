"""File > WordPress in QUILL Lite: every row runs the shared command, and only that.

QUILL Lite may never be ahead of QUILL, and the cheapest way to break that is a
second implementation. So each ``cmd_wp_*`` is checked to hand straight to the
shared :class:`~quill.ui.wordpress_commands.WordPressCommands` method its row
names, and neither adapter is allowed a ``cmd_*`` of its own beyond those.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from quill.apps.lite_window_wordpress import DocumentWordPressMixin, LiteWordPressHost
from quill.core.lite.commands import COMMANDS
from quill.core.wordpress.menu import all_rows, lite_handler


class _Recorder:
    def __init__(self) -> None:
        self.ran: list[str] = []

    def __getattr__(self, name: str):
        if not name.startswith("cmd_"):
            raise AttributeError(name)
        return lambda: self.ran.append(name)


class _Window(DocumentWordPressMixin):
    def __init__(self) -> None:
        self._wordpress_commands = _Recorder()


@pytest.mark.parametrize(
    ("run", "shared"),
    [
        (lambda w: w.cmd_wp_new_page(), "cmd_new_page"),
        (lambda w: w.cmd_wp_new_post(), "cmd_new_post"),
        (lambda w: w.cmd_wp_open(), "cmd_open"),
        (lambda w: w.cmd_wp_open_by_address(), "cmd_open_by_address"),
        (lambda w: w.cmd_wp_open_local_draft(), "cmd_open_local_draft"),
        (lambda w: w.cmd_wp_save_draft(), "cmd_save_draft"),
        (lambda w: w.cmd_wp_publish(), "cmd_publish"),
        (lambda w: w.cmd_wp_schedule(), "cmd_schedule"),
        (lambda w: w.cmd_wp_open_on_site(), "cmd_open_on_site"),
        (lambda w: w.cmd_wp_copy_address(), "cmd_copy_address"),
        (lambda w: w.cmd_wp_properties(), "cmd_properties"),
        (lambda w: w.cmd_wp_versions(), "cmd_versions"),
        (lambda w: w.cmd_wp_compare(), "cmd_compare"),
        (lambda w: w.cmd_wp_trash(), "cmd_trash"),
        (lambda w: w.cmd_wp_switch_site(), "cmd_switch_site"),
        (lambda w: w.cmd_wp_sites(), "cmd_sites"),
        (lambda w: w.cmd_wp_connect(), "cmd_connect"),
        (lambda w: w.cmd_wp_next_block(), "cmd_next_block"),
        (lambda w: w.cmd_wp_previous_block(), "cmd_previous_block"),
        (lambda w: w.cmd_wp_where_am_i(), "cmd_where_am_i"),
        (lambda w: w.cmd_wp_blocks(), "cmd_blocks_window"),
        (lambda w: w.cmd_wp_preview_blocks(), "cmd_preview_blocks"),
        (lambda w: w.cmd_wp_play_media_here(), "cmd_play_media_here"),
        (lambda w: w.cmd_wp_plugin_fields(), "cmd_plugin_fields"),
        (lambda w: w.cmd_wp_style_variations(), "cmd_style_variations"),
        (lambda w: w.cmd_wp_site_styles(), "cmd_site_styles"),
        (lambda w: w.cmd_wp_events_coming_up(), "cmd_events_coming_up"),
        (lambda w: w.cmd_wp_new_event(), "cmd_new_event"),
        (lambda w: w.cmd_wp_shop_orders(), "cmd_shop_orders"),
        (lambda w: w.cmd_wp_abilities(), "cmd_abilities"),
        (lambda w: w.cmd_wp_ask_site(), "cmd_ask_site"),
        (lambda w: w.cmd_wp_send_document(), "cmd_send_document"),
        (lambda w: w.cmd_wp_publish_elsewhere(), "cmd_publish_elsewhere"),
        (lambda w: w.cmd_wp_duplicate(), "cmd_duplicate"),
        (lambda w: w.cmd_wp_send_folder(), "cmd_send_folder"),
        (lambda w: w.cmd_wp_download_writing(), "cmd_download_writing"),
        (lambda w: w.cmd_wp_hear_link(), "cmd_hear_link"),
        (lambda w: w.cmd_wp_fix_link_text(), "cmd_fix_link_text"),
        (lambda w: w.cmd_wp_insert_icon(), "cmd_insert_icon"),
        (lambda w: w.cmd_wp_upload_large_file(), "cmd_upload_large_file"),
        (lambda w: w.cmd_wp_regenerate_sizes(), "cmd_regenerate_sizes"),
        (lambda w: w.cmd_wp_menu_history(), "cmd_menu_history"),
        (lambda w: w.cmd_wp_previous_looks(), "cmd_previous_looks"),
        (lambda w: w.cmd_wp_site_space(), "cmd_site_space"),
        (lambda w: w.cmd_wp_download_design(), "cmd_download_design"),
        (lambda w: w.cmd_wp_coming_up(), "cmd_coming_up"),
        (lambda w: w.cmd_wp_what_changed(), "cmd_what_changed"),
        (lambda w: w.cmd_wp_custom_fields(), "cmd_custom_fields"),
        (lambda w: w.cmd_wp_notes(), "cmd_notes"),
        (lambda w: w.cmd_wp_add_note(), "cmd_add_note"),
        (lambda w: w.cmd_wp_library_alt_text(), "cmd_library_alt_text"),
        (lambda w: w.cmd_wp_edit_picture_on_site(), "cmd_edit_picture_on_site"),
        (lambda w: w.cmd_wp_insert_block(), "cmd_insert_block"),
        (lambda w: w.cmd_wp_insert_from_library(), "cmd_insert_from_library"),
        (lambda w: w.cmd_wp_insert_picture(), "cmd_insert_picture"),
        (lambda w: w.cmd_wp_insert_link(), "cmd_insert_link"),
        (lambda w: w.cmd_wp_picture_maker(), "cmd_picture_maker"),
        (lambda w: w.cmd_wp_block_settings(), "cmd_block_settings"),
        (lambda w: w.cmd_wp_image_size(), "cmd_image_size"),
        (lambda w: w.cmd_wp_mark_language(), "cmd_mark_language"),
        (lambda w: w.cmd_wp_check(), "cmd_check"),
        (lambda w: w.cmd_wp_check_page(), "cmd_check_page"),
        (lambda w: w.cmd_wp_check_site(), "cmd_check_site"),
        (lambda w: w.cmd_wp_undo_site_fix(), "cmd_undo_site_fix"),
        (lambda w: w.cmd_wp_site_find_replace(), "cmd_site_find_replace"),
        (lambda w: w.cmd_wp_accessibility_statement(), "cmd_accessibility_statement"),
        (lambda w: w.cmd_wp_palette_report(), "cmd_palette_report"),
        (lambda w: w.cmd_wp_in_short(), "cmd_in_short"),
        (lambda w: w.cmd_wp_workbench(), "cmd_workbench"),
        (lambda w: w.cmd_wp_media_library(), "cmd_media_library"),
        (lambda w: w.cmd_wp_alt_text_review(), "cmd_alt_text_review"),
        (lambda w: w.cmd_wp_visual_review(), "cmd_visual_review"),
        (lambda w: w.cmd_wp_upload_files(), "cmd_upload_files"),
        (lambda w: w.cmd_wp_upload_from_address(), "cmd_upload_from_address"),
        (lambda w: w.cmd_wp_paste_image(), "cmd_paste_image"),
        (lambda w: w.cmd_wp_smaller_copy(), "cmd_smaller_copy"),
        (lambda w: w.cmd_wp_site_logo(), "cmd_site_logo"),
        (lambda w: w.cmd_wp_preview_and_review(), "cmd_preview_and_review"),
        (lambda w: w.cmd_wp_captions(), "cmd_captions"),
        (lambda w: w.cmd_wp_transcript(), "cmd_transcript"),
        (lambda w: w.cmd_wp_listening_version(), "cmd_listening_version"),
        (lambda w: w.cmd_wp_name_embeds(), "cmd_name_embeds"),
        (lambda w: w.cmd_wp_document_as_page(), "cmd_document_as_page"),
        (lambda w: w.cmd_wp_comments(), "cmd_comments"),
        (lambda w: w.cmd_wp_manage_terms(), "cmd_manage_terms"),
        (lambda w: w.cmd_wp_menus(), "cmd_menus"),
        (lambda w: w.cmd_wp_site_check(), "cmd_site_check"),
        (lambda w: w.cmd_wp_site_settings(), "cmd_site_settings"),
        (lambda w: w.cmd_wp_users(), "cmd_users"),
        (lambda w: w.cmd_wp_app_passwords(), "cmd_app_passwords"),
        (lambda w: w.cmd_wp_plugins(), "cmd_plugins"),
        (lambda w: w.cmd_wp_themes(), "cmd_themes"),
        (lambda w: w.cmd_wp_fonts(), "cmd_fonts"),
        (lambda w: w.cmd_wp_synced_patterns(), "cmd_synced_patterns"),
        (lambda w: w.cmd_wp_widgets(), "cmd_widgets"),
        (lambda w: w.cmd_wp_site_map(), "cmd_site_map"),
        (lambda w: w.cmd_wp_template_outline(), "cmd_template_outline"),
        (lambda w: w.cmd_wp_bulk_edit(), "cmd_bulk_edit"),
        (lambda w: w.cmd_wp_page_order(), "cmd_page_order"),
        (lambda w: w.cmd_wp_sign_out(), "cmd_sign_out"),
    ],
)
def test_each_lite_row_runs_the_shared_command(run, shared) -> None:
    window = _Window()
    run(window)
    assert window._wordpress_commands.ran == [shared]


def test_the_lite_table_and_the_shared_table_match() -> None:
    handlers = {lite_handler(cid) for _p, (cid, _t, _h) in all_rows()}
    lite = [
        (menu, label, handler) for menu, label, _k, handler, kind in COMMANDS if handler in handlers
    ]
    shared = [(path, title, lite_handler(cid)) for path, (cid, title, _h) in all_rows()]
    assert sorted(lite) == sorted(shared)
    assert len(lite) == len(shared)


def test_every_submenu_switches_off_with_the_wordpress_area() -> None:
    from quill.core.lite.command_areas import visible_commands

    off = visible_commands(lambda area: area != "wordpress")
    handlers = {lite_handler(cid) for _p, (cid, _t, _h) in all_rows()}
    assert not [row for row in off if "WordPress" in row[0] or "WordPress" in row[1]]
    assert not [row for row in off if row[3] in handlers]


def test_every_shared_handler_exists() -> None:
    from quill.ui.wordpress_commands import WordPressCommands

    missing = [h for _sub, (_c, _t, h) in all_rows() if not hasattr(WordPressCommands, h)]
    assert missing == []


@pytest.mark.parametrize(
    "module",
    ["quill/apps/lite_window_wordpress.py", "quill/ui/main_frame_wordpress.py"],
)
def test_the_adapters_have_no_second_implementation(module) -> None:
    """Only one-line hand-offs: no adapter method does WordPress work itself."""
    tree = ast.parse(Path(module).read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name.startswith("cmd_"):
            body = [
                n
                for n in node.body
                if not isinstance(n, ast.Expr) or not isinstance(n.value, ast.Constant)
            ]
            assert len(body) == 1, f"{module}: {node.name} does more than hand off"
            call = body[0].value if isinstance(body[0], ast.Expr) else None
            assert isinstance(call, ast.Call), f"{module}: {node.name} does more than hand off"


def test_the_host_opens_through_the_app() -> None:
    opened = []

    class _App:
        def open_path(self, path):
            opened.append(path)

    class _Win:
        app = _App()

    LiteWordPressHost(_Win()).open_path(Path("x.md"))
    assert opened == [Path("x.md")]
