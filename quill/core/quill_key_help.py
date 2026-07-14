"""Live, grouped cheat sheet for the QUILL key (QK-2 and QK-9).

This module is UI-agnostic: it builds a structured, screen-reader-friendly cheat
sheet of the follow-on keys available from the QUILL key prefix and inside browse
mode. The cheat sheet reflects the *active* key bindings (resolved through a
caller-supplied lookup) and *live* element counts, so the help always matches
what the user can actually do in the current document right now.

The UI layer renders the returned groups in an accessible read-only surface and
uses :func:`summarize_cheat_sheet` for the spoken announcement.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass

from quill.branding import QUILL_KEY_LABEL

#: Cheat-sheet for the prefix-pending state (just after the QUILL key is pressed).
MODE_PREFIX = "prefix"
#: Cheat-sheet for browse mode (after the QUILL key, then N).
MODE_BROWSE = "browse"

#: Command ids for the structural quick-nav follow-on keys, mapped to the
#: documented default key shown when no binding is configured.
_DEFAULT_KEYS: dict[str, str] = {
    "quill.quick_nav.heading": "H",
    "quill.quick_nav.link": "A",
    "quill.quick_nav.list": "L",
    "quill.quick_nav.list_item": "I",
    "quill.quick_nav.table": "T",
    "quill.quick_nav.block_quote": "Q",
    "quill.quick_nav.bookmark": "B",
    "quill.quick_nav.code_block": "'",
    "quill.quick_nav.table_of_contents": "C",
    "quill.quick_nav.paragraph": "P",
    "quill.quick_nav.sentence": "S",
    "quill.quick_nav.block": "Tab",
    "quill.quick_nav.skip_forward": "]",
    "quill.quick_nav.skip_backward": "[",
}


@dataclass(frozen=True)
class KeyHelpEntry:
    """A single follow-on key, its effect, and an optional live element count."""

    key: str
    description: str
    count: int | None = None


@dataclass(frozen=True)
class KeyHelpGroup:
    """A purpose-titled group of follow-on keys."""

    title: str
    entries: tuple[KeyHelpEntry, ...]


def _key_for(binding_lookup: Callable[[str], str | None], command_id: str) -> str:
    """Return the active key for a command, falling back to the documented default."""
    configured = binding_lookup(command_id)
    if configured:
        text = str(configured).strip()
        if text and "," not in text:
            return text
    return _DEFAULT_KEYS.get(command_id, "")


def _count(counts: Mapping[str, int], key: str) -> int | None:
    value = counts.get(key)
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def build_cheat_sheet(
    *,
    mode: str,
    binding_lookup: Callable[[str], str | None],
    counts: Mapping[str, int],
    selection_active: bool = False,
    quill_key_label: str = QUILL_KEY_LABEL,
    chord_map: Mapping[str, str] | None = None,
    prefix: str = "Ctrl+Shift+Grave",
) -> tuple[KeyHelpGroup, ...]:
    """Build the grouped cheat sheet for the given mode.

    ``mode`` is :data:`MODE_PREFIX` or :data:`MODE_BROWSE`. ``binding_lookup``
    resolves a command id to its active key string (or ``None``). ``counts`` maps
    count keys (``"links"``, ``"headings"``, ``"heading_level_1"`` .. ``"6"``,
    ``"lists"``, ``"list_items"``, ``"tables"``, ``"block_quotes"``,
    ``"bookmarks"``, ``"code_blocks"``, ``"paragraphs"``, ``"sentences"``) to
    live counts. Unknown counts are simply omitted.

    When ``chord_map`` is provided, the cheat sheet also lists every chord
    command bound to ``<prefix>, <second-key>``, grouped by command prefix
    in fixed order (file / edit / format / navigate / view / tools / help)
    and alphabetical within each group. ``binding_lookup`` resolves the
    active second-key for each chord command.
    """
    if mode == MODE_PREFIX:
        return _build_prefix_groups(quill_key_label, selection_active)
    if mode == MODE_BROWSE:
        groups = list(_build_browse_groups(binding_lookup, counts))
    else:
        raise ValueError(f"Unknown QUILL key help mode: {mode!r}")
    if chord_map is not None:
        groups.extend(_build_chord_groups(chord_map, prefix, binding_lookup))
    return tuple(groups)


def _build_prefix_groups(quill_key_label: str, selection_active: bool) -> tuple[KeyHelpGroup, ...]:
    entries = [KeyHelpEntry("N", "Enter browse mode")]
    entries.append(KeyHelpEntry("G", "Go to anything (Quick Nav)"))
    entries.append(KeyHelpEntry("M", "Paste HTML clipboard as Markdown (magic paste)"))
    entries.append(KeyHelpEntry("V", "Browser Preview"))
    if selection_active:
        entries.append(KeyHelpEntry("A", "Selection actions for the current selection"))
    entries.append(KeyHelpEntry(quill_key_label, "Press again to lock browse mode"))
    entries.append(KeyHelpEntry("?", "Show this help"))
    entries.append(KeyHelpEntry("Escape", "Cancel the QUILL key"))
    return (KeyHelpGroup("QUILL key prefix", tuple(entries)),)


def _build_browse_groups(
    binding_lookup: Callable[[str], str | None],
    counts: Mapping[str, int],
) -> tuple[KeyHelpGroup, ...]:
    def entry(command_id: str, description: str, count_key: str | None) -> KeyHelpEntry:
        return KeyHelpEntry(
            _key_for(binding_lookup, command_id),
            description,
            _count(counts, count_key) if count_key else None,
        )

    def _sorted(entries: tuple[KeyHelpEntry, ...]) -> tuple[KeyHelpEntry, ...]:
        return tuple(sorted(entries, key=lambda item: item.key.lower()))

    move = KeyHelpGroup(
        "Move by structure",
        _sorted((
            entry("quill.quick_nav.heading", "Next or previous heading", "headings"),
            entry("quill.quick_nav.paragraph", "Next or previous paragraph", "paragraphs"),
            entry("quill.quick_nav.sentence", "Next or previous sentence", "sentences"),
            entry("quill.quick_nav.block", "Next or previous block", None),
        )),
    )
    jump = KeyHelpGroup(
        "Jump to elements",
        _sorted((
            entry("quill.quick_nav.link", "Next or previous link", "links"),
            entry("quill.quick_nav.list", "Next or previous list", "lists"),
            entry("quill.quick_nav.list_item", "Next or previous list item", "list_items"),
            entry("quill.quick_nav.table", "Next or previous table", "tables"),
            entry("quill.quick_nav.block_quote", "Next or previous block quote", "block_quotes"),
            entry("quill.quick_nav.bookmark", "Next or previous bookmark", "bookmarks"),
            entry("quill.quick_nav.code_block", "Next or previous code block", "code_blocks"),
            entry(
                "quill.quick_nav.table_of_contents",
                "Open the table of contents",
                "headings",
            ),
        )),
    )
    levels = KeyHelpGroup(
        "Headings by level",
        tuple(
            KeyHelpEntry(
                str(level),
                f"Next or previous level {level} heading",
                _count(counts, f"heading_level_{level}"),
            )
            for level in range(1, 7)
        ),
    )
    skip = KeyHelpGroup(
        "Skip past containers",
        _sorted((
            entry("quill.quick_nav.skip_forward", "Skip forward past a list or table", None),
            entry("quill.quick_nav.skip_backward", "Skip backward past a list or table", None),
        )),
    )
    control = KeyHelpGroup(
        "Control",
        (
            KeyHelpEntry("Shift+Escape", "Refresh the navigation cache"),
            KeyHelpEntry("?", "Show this help"),
            KeyHelpEntry("Escape", "Exit browse mode"),
        ),
    )
    return (move, jump, levels, skip, control)


#: Display order for chord-group categories. Unknown prefixes fall through to
#: "Other" so a fresh command prefix still surfaces in the cheat sheet.
_CHORD_CATEGORY_ORDER: tuple[str, ...] = (
    "file",
    "edit",
    "format",
    "navigate",
    "view",
    "tools",
    "help",
    "power",
)

#: Display title for each chord category. Keeps titles consistent with the
#: rest of the cheat sheet rather than leaking the raw command prefix.
_CHORD_CATEGORY_TITLES: dict[str, str] = {
    "file": "File",
    "edit": "Edit",
    "format": "Format",
    "navigate": "Navigate",
    "view": "View",
    "tools": "Tools",
    "help": "Help",
    "power": "Power",
}


#: Display titles for known command ids in the chord cheat sheet. Falls
#: back to the bare command id (with the prefix stripped) for any unknown
#: command so user-defined chords still surface in some recognizable form.
_CHORD_COMMAND_TITLES: dict[str, str] = {
    "file.open_from_remote": "Open From Remote",
    "file.save_to_remote": "Save To Remote",
    "file.manage_remote_sites": "Manage Remote Sites",
    "navigate.speak_window_title": "Speak Window Title",
    "navigate.speak_full_path": "Speak Full Path",
    "navigate.speak_status_summary": "Speak Status Summary",
    "view.send_to_tray": "Send To Tray",
    "view.toggle_tab_control": "Toggle Tab Control",
    "navigate.heading_organizer": "Heading Organizer",
    "tools.read_aloud_start_pause": "Read Aloud Start / Pause",
    "tools.read_aloud_stop": "Read Aloud Stop",
    "tools.dictation_toggle": "Dictation Toggle",
    "tools.describe_image": "Describe Image",
    "edit.copy_selection_for_email": "Copy Selection For Email",
    "tools.sticky_note_capture": "Sticky Note Capture",
    "view.browser_preview": "Browser Preview",
    "view.switch_editing_lens": "Switch Editing Lens",
    "format.list_manager": "List Manager",
    "format.insert_html_tag": "Insert HTML Tag",
    "power.paste_html_as_markdown": "Paste HTML As Markdown",
    "power.open_snippet_gallery": "Open Snippet Gallery",
    "format.insert_snippet": "Insert Snippet",
    "format.manage_snippets": "Manage Snippets",
    "format.expand_abbreviation": "Expand Abbreviation",
    "format.manage_abbreviations": "Manage Abbreviations",
    "format.toggle_abbreviation_expansion": "Toggle Abbreviation Expansion",
    "help.context_help": "Context Help",
    "navigate.go_to_anything": "Go To Anything",
    "view.announce_contrast": "Announce Contrast",
    "edit.open_copy_tray": "Open Copy Tray",
}


def _chord_description(command_id: str) -> str:
    title = _CHORD_COMMAND_TITLES.get(command_id)
    if title:
        return title
    if "." in command_id:
        return command_id.split(".", 1)[1].replace("_", " ").title()
    return command_id


def _build_chord_groups(
    chord_map: Mapping[str, str],
    prefix: str,
    binding_lookup: Callable[[str], str | None],
) -> tuple[KeyHelpGroup, ...]:
    """Build chord-command groups (file / edit / format / ...) for the cheat sheet.

    Walks ``chord_map`` for any binding of the form ``<prefix>, <second-key>``.
    The active second-key is resolved through ``binding_lookup`` so user
    remappings show up immediately. Commands whose binding is empty or
    returns None from ``binding_lookup`` are skipped — they are effectively
    unbound and would only add clutter.
    """
    if not prefix:
        return ()
    chord_prefix = prefix.strip() + ", "
    by_category: dict[str, list[tuple[str, str]]] = {}
    for command_id, binding in chord_map.items():
        if not binding or not binding.startswith(chord_prefix):
            continue
        active = binding_lookup(command_id)
        if not active:
            continue
        text = str(active).strip()
        if not text:
            continue
        # Extract the second key (everything after the first comma) so a
        # full chord binding like "Ctrl+Shift+Grave, F" surfaces as "F"
        # in the cheat sheet. The user-facing key is the second key, not
        # the prefix.
        if "," in text:
            second_key = text.split(",", 1)[1].strip()
            if not second_key:
                continue
            text = second_key
        category = command_id.split(".", 1)[0] if "." in command_id else "other"
        by_category.setdefault(category, []).append((text, command_id))
    if not by_category:
        return ()

    groups: list[KeyHelpGroup] = []
    ordered_categories = sorted(
        by_category,
        key=lambda name: (
            _CHORD_CATEGORY_ORDER.index(name)
            if name in _CHORD_CATEGORY_ORDER
            else len(_CHORD_CATEGORY_ORDER)
        ),
    )
    for category in ordered_categories:
        title = _CHORD_CATEGORY_TITLES.get(category, category.title())
        entries = tuple(
            KeyHelpEntry(second_key, _chord_description(command_id))
            for second_key, command_id in sorted(by_category[category], key=lambda item: item[1])
        )
        groups.append(KeyHelpGroup(title, entries))
    return tuple(groups)


def format_cheat_sheet(groups: tuple[KeyHelpGroup, ...]) -> str:
    """Render the cheat sheet as plain text for an accessible read-only surface."""
    lines: list[str] = []
    for group in groups:
        lines.append(group.title)
        for item in group.entries:
            suffix = f"  ({item.count})" if item.count is not None else ""
            key = item.key or "(unbound)"
            lines.append(f"  {key}\t{item.description}{suffix}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def summarize_cheat_sheet(groups: tuple[KeyHelpGroup, ...]) -> str:
    """Return a one-line spoken summary of the cheat sheet."""
    total = sum(len(group.entries) for group in groups)
    action_word = "action" if total == 1 else "actions"
    group_word = "group" if len(groups) == 1 else "groups"
    return f"QUILL key help, {total} {action_word} in {len(groups)} {group_word}."
