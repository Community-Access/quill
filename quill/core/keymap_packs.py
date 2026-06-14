"""Keyboard pack definitions and accessors (GATE-11 extraction from keymap.py).

This module owns the pack catalogue so keymap.py can stay focused on
load/save/merge logic and stay within its module-size budget.
"""

from __future__ import annotations

from dataclasses import dataclass

KEYBOARD_PACK_DEFAULT = "Quill Default"
KEYBOARD_PACK_CUSTOM = "Custom"


@dataclass(frozen=True, slots=True)
class KeyboardPack:
    name: str
    description: str
    bindings: dict[str, str]


_PACK_LABELS: dict[str, str] = {
    "app.command_palette": "Command Palette",
    "app.menu_editor": "Customize Menus",
    "edit.copy_with_source": "Copy With Source",
    "edit.copy_selection_for_email": "Copy Selection For Email",
    "edit.find": "Find",
    "edit.find_all_matches": "Find All Matches",
    "edit.find_next": "Find Next",
    "edit.insert_link": "Insert Link",
    "edit.redo": "Redo",
    "edit.replace": "Replace",
    "edit.replace_all": "Replace All",
    "edit.word_prediction": "Word Prediction",
    "edit.start_selection": "Start Selection",
    "edit.complete_selection": "Complete Selection",
    "edit.reselect": "Reselect",
    "edit.go_to_start_of_selection": "Go to Start of Selection",
    "edit.copy_all": "Copy All",
    "edit.unselect_all": "Unselect All",
    "edit.say_selected": "Say Selected",
    "edit.read_all": "Read All",
    "edit.select_line": "Select Line",
    "edit.expand_selection": "Expand Selection",
    "edit.shrink_selection": "Shrink Selection",
    "edit.select_paragraph": "Select Paragraph",
    "edit.select_block": "Select Block",
    "edit.set_named_mark": "Set Named Mark",
    "edit.jump_to_named_mark": "Jump to Named Mark",
    "edit.open_review_buffer": "Open Review Buffer",
    "edit.selection_actions": "Selection Actions",
    "edit.undo": "Undo",
    "file.new": "New",
    "file.open": "Open",
    "file.save": "Save",
    "file.save_as": "Save As",
    "file.open_from_remote": "Open From Remote...",
    "file.save_to_remote": "Save To Remote",
    "file.save_copy_to_remote": "Save Copy To Remote...",
    "file.manage_remote_sites": "Manage Remote Sites...",
    "file.open_url": "Open From URL...",
    "format.bold": "Bold",
    "format.delete_line": "Delete Line",
    "format.duplicate_line": "Duplicate Line",
    "format.indent": "Indent",
    "format.italic": "Italic",
    "format.lower_case": "Lower Case",
    "format.move_line_down": "Move Line Down",
    "format.move_line_up": "Move Line Up",
    "format.outdent": "Outdent",
    "format.list_manager": "List Manager",
    "format.insert_snippet": "Insert Snippet",
    "format.manage_snippets": "Manage Snippets",
    "format.expand_abbreviation": "Expand Abbreviation",
    "format.manage_abbreviations": "Manage Abbreviations",
    "format.toggle_abbreviation_expansion": "Toggle Abbreviation Expansion",
    "format.toggle_line_comment": "Toggle Line Comment",
    "format.upper_case": "Upper Case",
    "navigate.speak_window_title": "Speak Window Title",
    "navigate.speak_full_path": "Speak Full Path",
    "navigate.speak_status_summary": "Speak Status Summary",
    "navigate.back_location": "Back",
    "navigate.forward_location": "Forward",
    "navigate.go_to_line": "Go To Line",
    "navigate.go_to_page": "Go To Page",
    "navigate.list_bookmarks": "List Bookmarks",
    "navigate.quick_nav": "Quick Nav (Go to Anything)",
    "navigate.next_region": "Next Region",
    "navigate.next_structure": "Next Structure",
    "navigate.heading_organizer": "Heading Organizer",
    "navigate.outline_navigator": "Outline Navigator",
    "navigate.previous_region": "Previous Region",
    "navigate.previous_structure": "Previous Structure",
    "tools.document_intake_report": "Document Intake Report",
    "tools.describe_image": "Describe Image",
    "tools.previous_misspelling": "Previous Misspelling",
    "tools.next_misspelling": "Next Misspelling",
    "tools.misspelling_list": "Misspelling List",
    "tools.spell_check_dialog": "Spell Check",
    "tools.replace_in_files": "Replace Across Files",
    "tools.thesaurus": "Thesaurus",
    "tools.search_in_files": "Search In Files",
    "tools.ask_quill_chat": "Ask Quill",
    "tools.prompt_library": "Prompt Library",
    "tools.check_grammar_ai": "Check Grammar with AI",
    "tools.word_count": "Word Count",
    "tools.writing_instructions": "Open Writing Instructions",
    "view.browser_preview": "Browser Preview",
    "view.preview": "Preview",
    "view.split_preview": "Preview Side by Side",
    "view.focus_preview": "Focus Preview",
    "help.switch_feature_profile": "Switch Feature Profile",
    "view.toggle_tab_control": "Tab Control",
}


KEYBOARD_PACKS: dict[str, KeyboardPack] = {
    KEYBOARD_PACK_DEFAULT: KeyboardPack(
        KEYBOARD_PACK_DEFAULT,
        (
            "Quill's balanced default layout: writing, navigation, and "
            "accessibility commands stay available without overloading the keyboard."
        ),
        {},
    ),
    "Quill Writer": KeyboardPack(
        "Quill Writer",
        (
            "A writing-first pack that keeps revision, spelling, links, "
            "and formatting under familiar document-editing keys."
        ),
        {
            "file.save_as": "F12",
            "edit.select_line": "Ctrl+L",
            "edit.insert_link": "Ctrl+K",
            "tools.spell_check_dialog": "F7",
            "tools.next_misspelling": "Alt+F7",
            "tools.thesaurus": "Shift+F7",
            "format.bold": "Ctrl+B",
            "format.italic": "Ctrl+I",
            "format.upper_case": "Ctrl+Shift+U",
        },
    ),
    "Quill Navigation": KeyboardPack(
        "Quill Navigation",
        (
            "Optimized for structural movement, screen-reader review, "
            "and rapid movement around long documents."
        ),
        {
            "navigate.next_region": "F6",
            "navigate.previous_region": "Shift+F6",
            "navigate.go_to_line": "Ctrl+G",
            "navigate.go_to_page": "Ctrl+Shift+G",
            "navigate.outline_navigator": "Ctrl+Shift+O",
            "navigate.back_location": "Alt+Left",
            "navigate.forward_location": "Alt+Right",
            "navigate.next_structure": "Alt+Down",
            "navigate.previous_structure": "Alt+Up",
            "edit.select_line": "Ctrl+L",
            "format.move_line_up": "Alt+Shift+Up",
            "format.move_line_down": "Alt+Shift+Down",
        },
    ),
    "Quill Review": KeyboardPack(
        "Quill Review",
        (
            "A review-and-analysis pack for outlines, intake reports, "
            "source-aware copying, and find-all workflows."
        ),
        {
            "tools.word_count": "Ctrl+Shift+W",
            "tools.document_intake_report": "Ctrl+Shift+I",
            "edit.copy_with_source": "Ctrl+Shift+C",
            "edit.find_all_matches": "Alt+F3",
            "navigate.outline_navigator": "Ctrl+Shift+O",
            "navigate.go_to_page": "Ctrl+Shift+G",
            "edit.select_line": "Ctrl+L",
        },
    ),
    "Windows Notepad": KeyboardPack(
        "Windows Notepad",
        (
            "A deliberately plain Windows-editor feel that preserves the classic "
            "file, find, replace, and go-to-line muscle memory."
        ),
        {
            "file.new": "Ctrl+N",
            "file.open": "Ctrl+O",
            "file.save": "Ctrl+S",
            "file.save_as": "Ctrl+Shift+S",
            "edit.undo": "Ctrl+Z",
            "edit.redo": "Ctrl+Y",
            "edit.find": "Ctrl+F",
            "edit.find_next": "F3",
            "edit.replace_all": "Ctrl+Shift+H",
            "navigate.go_to_line": "Ctrl+G",
        },
    ),
    "Notepad++": KeyboardPack(
        "Notepad++",
        (
            "A quick, utility-style text editing pack centered on "
            "duplicate/delete-line commands and Windows-friendly search shortcuts."
        ),
        {
            "navigate.go_to_line": "Ctrl+G",
            "edit.find_all_matches": "Alt+F3",
            "format.duplicate_line": "Ctrl+D",
            "format.delete_line": "Ctrl+L",
            "format.move_line_up": "Alt+Up",
            "format.move_line_down": "Alt+Down",
        },
    ),
    "VS Code": KeyboardPack(
        "VS Code",
        (
            "A modern development-oriented pack with quick open, command "
            "palette, outline navigation, and line manipulation."
        ),
        {
            "app.command_palette": "Ctrl+Shift+P",
            "file.open": "Ctrl+P",
            "navigate.go_to_line": "Ctrl+G",
            "navigate.outline_navigator": "Ctrl+Shift+O",
            "edit.select_line": "Ctrl+L",
            "format.duplicate_line": "Shift+Alt+Down",
            "format.move_line_up": "Alt+Up",
            "format.move_line_down": "Alt+Down",
            "format.toggle_line_comment": "Ctrl+/",
            "format.indent": "Ctrl+]",
            "format.outdent": "Ctrl+[",
        },
    ),
    "Microsoft Word": KeyboardPack(
        "Microsoft Word",
        (
            "A document-centric pack that leans on familiar Word shortcuts "
            "for save-as, links, formatting, and spelling tools."
        ),
        {
            "file.save_as": "F12",
            "edit.insert_link": "Ctrl+K",
            "tools.spell_check_dialog": "F7",
            "tools.thesaurus": "Shift+F7",
            "format.bold": "Ctrl+B",
            "format.italic": "Ctrl+I",
        },
    ),
}


def keyboard_pack_names(include_custom: bool = False) -> list[str]:
    names = list(KEYBOARD_PACKS)
    if include_custom:
        names.append(KEYBOARD_PACK_CUSTOM)
    return names


def keyboard_pack_description(name: str) -> str:
    if name == KEYBOARD_PACK_CUSTOM:
        return "A hand-tuned keyboard layout created from manual edits or imported bindings."
    pack = KEYBOARD_PACKS.get(name)
    if pack is None:
        return KEYBOARD_PACKS[KEYBOARD_PACK_DEFAULT].description
    return pack.description


def keyboard_pack_preview(name: str) -> str:
    if name == KEYBOARD_PACK_CUSTOM:
        return keyboard_pack_description(name)
    pack = KEYBOARD_PACKS.get(name)
    if pack is None:
        pack = KEYBOARD_PACKS[KEYBOARD_PACK_DEFAULT]
    if not pack.bindings:
        return pack.description
    lines = [pack.description, "", "Highlights:"]
    for command_id, binding in pack.bindings.items():
        label = _PACK_LABELS.get(command_id, command_id)
        lines.append(f"- {label}: {binding}")
    return "\n".join(lines)
