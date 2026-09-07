"""The command table. wx-free so tests and the F1 list can import it.

Every enabled menu item shows its key in its label, and no two items claim
the same key: a rule borrowed from QUILL, enforced by tests/test_commands.py.
"""

from __future__ import annotations

from quilllite import APP_NAME, __version__

# (menu, label, key, handler name, kind). kind: "" normal, "check" checkable, "sep" separator.
COMMANDS: list[tuple[str, str, str, str, str]] = [
    ("&File", "&New", "Ctrl+N", "cmd_new", ""),
    ("&File", "New &Rich Text Document", "Ctrl+Shift+N", "cmd_new_rich", ""),
    ("&File", "New &Plain Text Document", "Ctrl+Alt+N", "cmd_new_plain", ""),
    ("&File", "&Open...", "Ctrl+O", "cmd_open", ""),
    ("&File", "", "", "", "sep"),
    ("&File", "&Save", "Ctrl+S", "cmd_save", ""),
    ("&File", "Save &As...", "Ctrl+Shift+S", "cmd_save_as", ""),
    ("&File", "", "", "", "sep"),
    ("&File", "&Close Window", "Ctrl+W", "cmd_close", ""),
    ("&File", "E&xit QuillLite", "Ctrl+Q", "cmd_exit", ""),
    ("&Edit", "&Undo", "Ctrl+Z", "cmd_undo", ""),
    ("&Edit", "&Redo", "Ctrl+Y", "cmd_redo", ""),
    ("&Edit", "", "", "", "sep"),
    ("&Edit", "Cu&t", "Ctrl+X", "cmd_cut", ""),
    ("&Edit", "&Copy", "Ctrl+C", "cmd_copy", ""),
    ("&Edit", "&Paste", "Ctrl+V", "cmd_paste", ""),
    ("&Edit", "Select &All", "Ctrl+A", "cmd_select_all", ""),
    ("&Edit", "Insert &Date and Time", "F5", "cmd_insert_datetime", ""),
    ("&Edit", "", "", "", "sep"),
    ("&Edit", "&Find...", "Ctrl+F", "cmd_find", ""),
    ("&Edit", "Find &Next", "F3", "cmd_find_next", ""),
    ("&Edit", "Find Pre&vious", "Shift+F3", "cmd_find_previous", ""),
    ("&Edit", "R&eplace...", "Ctrl+H", "cmd_replace", ""),
    ("&Edit", "&Go to Line...", "Ctrl+G", "cmd_goto_line", ""),
    ("F&ormat", "&Bold", "Ctrl+B", "cmd_bold", ""),
    ("F&ormat", "&Italic", "Ctrl+I", "cmd_italic", ""),
    ("F&ormat", "&Underline", "Ctrl+U", "cmd_underline", ""),
    ("F&ormat", "", "", "", "sep"),
    ("F&ormat", "Heading &1", "Ctrl+Alt+1", "cmd_heading_1", ""),
    ("F&ormat", "Heading &2", "Ctrl+Alt+2", "cmd_heading_2", ""),
    ("F&ormat", "Heading &3", "Ctrl+Alt+3", "cmd_heading_3", ""),
    ("F&ormat", "Heading &4", "Ctrl+Alt+4", "cmd_heading_4", ""),
    ("F&ormat", "Body &Text", "Ctrl+Alt+0", "cmd_heading_0", ""),
    ("F&ormat", "", "", "", "sep"),
    ("F&ormat", "Align &Left", "Ctrl+L", "cmd_align_left", ""),
    ("F&ormat", "&Centre", "Ctrl+E", "cmd_align_center", ""),
    ("F&ormat", "Align &Right", "Ctrl+R", "cmd_align_right", ""),
    ("F&ormat", "", "", "", "sep"),
    ("F&ormat", "&Font for Selection...", "Ctrl+Shift+F", "cmd_selection_font", ""),
    ("F&ormat", "&Describe Formatting at Cursor", "Ctrl+Shift+D", "cmd_describe", ""),
    ("F&ormat", "", "", "", "sep"),
    ("F&ormat", "Switch Document &Mode", "Ctrl+Shift+M", "cmd_switch_mode", ""),
    ("&Navigate", "&Next Heading", "Ctrl+Alt+H", "cmd_next_heading", ""),
    ("&Navigate", "&Previous Heading", "Ctrl+Alt+Shift+H", "cmd_previous_heading", ""),
    ("&Navigate", "&List Headings...", "Ctrl+Alt+L", "cmd_list_headings", ""),
    ("&View", "&Dark Mode", "Alt+Shift+D", "cmd_toggle_dark", "check"),
    ("&View", "&Word Wrap", "Alt+Z", "cmd_toggle_wrap", "check"),
    ("&View", "", "", "", "sep"),
    ("&View", "&Increase Text Size", "Ctrl+=", "cmd_zoom_in", ""),
    ("&View", "D&ecrease Text Size", "Ctrl+-", "cmd_zoom_out", ""),
    ("&View", "&Reset Text Size", "Ctrl+0", "cmd_zoom_reset", ""),
    ("&View", "Editor &Font...", "Ctrl+Alt+F", "cmd_editor_font", ""),
    ("&View", "", "", "", "sep"),
    ("&View", "Document &Statistics", "Ctrl+Alt+W", "cmd_statistics", ""),
    ("&Window", "&Next Window", "Ctrl+Tab", "cmd_next_window", ""),
    ("&Window", "&Previous Window", "Ctrl+Shift+Tab", "cmd_previous_window", ""),
    ("&Help", "&Keyboard Shortcuts", "F1", "cmd_shortcuts", ""),
    ("&Help", "&About QuillLite", "Shift+F1", "cmd_about", ""),
]

_HTML_KEY_FIX = str.maketrans({"&": ""})


def shortcut_text() -> str:
    lines = [f"{APP_NAME} {__version__} keyboard shortcuts", ""]
    current = ""
    for menu, label, key, _handler, kind in COMMANDS:
        if kind == "sep":
            continue
        if menu != current:
            current = menu
            lines.append("")
            lines.append(menu.translate(_HTML_KEY_FIX) + " menu")
        lines.append(f"  {key}: {label.translate(_HTML_KEY_FIX)}")
    lines += [
        "",
        "Window menu",
        "  Alt+1 to Alt+9: switch to that open window",
        "",
        "Headings use Quill's ladder: bold plus 20, 16, 14 and 12 point for levels 1 to 4.",
    ]
    return "\n".join(lines)
