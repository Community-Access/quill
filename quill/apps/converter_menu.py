"""Quill Converter's menu bar, and the Help menu the family shares.

Split out of :mod:`quill.apps.converter` (GATE-11). Every enabled item shows
its key (the menu-accelerator rule), no key is claimed twice, and the Help
menu carries the same doors as Quill Radio's and QUILL Lite's, on the same
keys wherever the two agree:

* F1 -- help for the window and control you are on;
* Ctrl+F1 the User Guide, Shift+F1 the Release Notes, Ctrl+Shift+F1 the
  Changelog, Alt+Shift+F1 the Product Requirements (Radio's ladder);
* Ctrl+Alt+K -- every key in this app, in one read-only list;
* Ctrl+Alt+F2 -- Get Help from Support, the family's one door to a person;
* Ctrl+Alt+F -- Get FFmpeg, the repair door for the one tool the app needs;
* Ctrl+Alt+U -- Check for Updates; Alt+F1 -- About.

The documents are the rendered HTML the build ships in ``docs\\`` beside the
app; in a checkout they come from ``standalone/converter/docs``.
"""

from __future__ import annotations

from typing import Any

#: Which document each Help item opens, by file stem -> window title.
DOC_TITLES: dict[str, str] = {
    "userguide": "Quill Converter User Guide",
    "release-notes-1.0": "Quill Converter Release Notes",
    "CHANGELOG": "Quill Converter Changelog",
    "prd": "Quill Converter Product Requirements",
}


def open_doc(host: Any, stem: str) -> None:
    """Open the rendered document *stem* in the browser."""
    host.open_app_document(
        host._doc_candidates("quill-converter", stem),
        title=DOC_TITLES.get(stem, stem),
        cache_name="app-docs",
    )


def build_menu_bar(host: Any, wx: Any, *, title: str, version: str, repo: str) -> Any:
    """Build, bind and return the menu bar. Every id is pinned on *host*."""
    bar = wx.MenuBar()
    ids: list[Any] = []

    def add(menu: Any, label: str, handler: Any) -> Any:
        item_id = wx.NewIdRef()
        menu.Append(item_id, label)
        host.frame.Bind(wx.EVT_MENU, lambda _e: handler(), id=item_id)
        ids.append(item_id)
        return item_id

    file_menu = wx.Menu()
    add(file_menu, "&Add Files...\tCtrl+O", lambda: host._on_add_files(None))
    add(file_menu, "Add F&older...\tCtrl+Shift+O", lambda: host._on_add_folder(None))
    add(file_menu, "&Paste Files\tCtrl+V", host.paste_files)
    add(file_menu, "Convert from &URL...\tCtrl+U", lambda: host._on_convert_url(None))
    file_menu.AppendSeparator()
    add(file_menu, "Open Output &Folder\tCtrl+Shift+F", host.open_output_folder)
    add(file_menu, "Minimize to &Tray\tCtrl+W", host.toggle_window_to_tray)
    add(file_menu, "E&xit\tCtrl+Q", host._exit_application)
    bar.Append(file_menu, "&File")

    queue_menu = wx.Menu()
    add(queue_menu, "File &Properties...\tAlt+Enter", host.show_properties)
    add(queue_menu, "Chapter &Workbench...\tCtrl+H", host.open_chapter_workbench)
    add(queue_menu, "&Remove from Queue\tCtrl+Delete", lambda: host._on_remove(None))
    add(queue_menu, "&Clear Queue\tCtrl+Shift+Delete", host.clear_queue)
    add(queue_menu, "Move &Up\tAlt+Up", lambda: host.move_entry(-1))
    add(queue_menu, "Move &Down\tAlt+Down", lambda: host.move_entry(1))
    bar.Append(queue_menu, "&Queue")

    # View > Advanced Options shows more of the main window, the Windows way,
    # rather than opening a second window with its own Convert button.
    view_menu = wx.Menu()
    advanced_item = wx.NewIdRef()
    view_menu.AppendCheckItem(advanced_item, "&Advanced Options" + chr(9) + "Ctrl+Alt+V")
    view_menu.Check(advanced_item, host._settings.show_advanced)
    host.frame.Bind(
        wx.EVT_MENU, lambda e: host.set_advanced_visible(e.IsChecked()), id=advanced_item
    )
    ids.append(advanced_item)
    bar.Append(view_menu, "&View")

    convert_menu = wx.Menu()
    host._convert_item = add(convert_menu, "&Convert Now\tCtrl+Enter", host.convert_or_stop)
    add(convert_menu, "Pre&view with Your Settings\tCtrl+P", lambda: host.preview(original=False))
    add(convert_menu, "Preview &Original\tCtrl+Shift+P", lambda: host.preview(original=True))
    convert_menu.AppendSeparator()
    add(convert_menu, "Custom &Effects...\tCtrl+E", lambda: host._on_custom_effects(None))
    add(convert_menu, "&Join into One File...\tCtrl+J", host.join_into_one)
    add(convert_menu, "&Split by Chapters\tCtrl+Shift+S", host.split_by_chapters)
    convert_menu.AppendSeparator()
    add(convert_menu, "Conversion &Report...\tCtrl+R", host.show_report)
    open_item = wx.NewIdRef()
    convert_menu.AppendCheckItem(open_item, "Open Output Folder &When Done\tCtrl+Shift+W")
    convert_menu.Check(open_item, host._settings.open_folder_when_done)
    host.frame.Bind(wx.EVT_MENU, lambda e: host.set_open_when_done(e.IsChecked()), id=open_item)
    ids.append(open_item)
    bar.Append(convert_menu, "&Convert")

    from quill.ui.quillville_menu import build_quillville_menu

    bar.Append(
        build_quillville_menu(
            wx, host.frame, host._launch_sibling, exclude="converter", retain=host._keep_menu_ids
        ),
        "Q&uillVille",  # V is View; the window's own controls avoid every menu letter
    )

    help_menu = wx.Menu()
    add(help_menu, "&Help for This Window\tF1", host.show_context_help)
    add(help_menu, "&User Guide\tCtrl+F1", lambda: open_doc(host, "userguide"))
    add(help_menu, "&Release Notes\tShift+F1", lambda: open_doc(host, "release-notes-1.0"))
    add(help_menu, "Chan&gelog\tCtrl+Shift+F1", lambda: open_doc(host, "CHANGELOG"))
    add(help_menu, "Product Re&quirements\tAlt+Shift+F1", lambda: open_doc(host, "prd"))
    add(help_menu, "&Keyboard Shortcuts...\tCtrl+Alt+K", host.show_keyboard_shortcuts)
    help_menu.AppendSeparator()
    from quill.ui.support_menu import append_get_help_item

    append_get_help_item(host, help_menu, wx, source_app=title, app_version=version)
    add(help_menu, "Get &FFmpeg...\tCtrl+Alt+F", host.download_ffmpeg_component)
    add(
        help_menu,
        "Check for Up&dates...\tCtrl+Alt+U",
        lambda: host.check_for_app_updates(
            repo_slug=repo, current_version=version, app_key="converter", match_edition=False
        ),
    )
    help_menu.AppendSeparator()
    add(help_menu, f"&About {title}\tAlt+F1", host._show_about)
    bar.Append(help_menu, "&Help")

    host._keep_menu_ids(*ids)
    return bar


def shortcut_list(bar: Any) -> str:
    """Every menu item and its key, grouped by menu, as plain text."""
    lines: list[str] = []
    for index in range(bar.GetMenuCount()):
        menu = bar.GetMenu(index)
        heading = bar.GetMenuLabelText(index)
        rows = []
        for item in menu.GetMenuItems():
            if item.IsSeparator() or item.GetSubMenu() is not None:
                continue
            label = item.GetItemLabelText().rstrip(".")
            accel = item.GetItemLabel().partition("\t")[2]
            rows.append(f"  {label}: {accel}" if accel else f"  {label}")
        if rows:
            lines.append(heading)
            lines += rows
            lines.append("")
    lines.append(
        "In the queue: Delete removes the highlighted row; Alt+Up and Alt+Down reorder it."
    )
    lines.append("Anywhere: Ctrl+Alt+Shift+C shows or hides Quill Converter from the tray.")
    return "\n".join(lines).strip()
