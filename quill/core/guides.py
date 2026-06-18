from __future__ import annotations

from collections import defaultdict
from html import escape

from quill.core.commands import Command
from quill.core.features import FeatureManager
from quill.core.quill_key_help import (
    MODE_BROWSE,
    MODE_PREFIX,
    build_cheat_sheet,
)


def build_welcome_guide(feature_manager: FeatureManager | None = None) -> str:
    profile_block = ""
    if feature_manager is not None:
        profile_block = f"## Current profile\n\n{feature_manager.profile_summary()}\n\n"
    return (
        "# Welcome to Quill\n\n"
        "Quill is a keyboard-first writing editor focused on accessibility.\n\n"
        f"{profile_block}"
        "## Quick start\n\n"
        "1. Open a file with `Ctrl+O` or create one with `Ctrl+N`.\n"
        "2. Use `Ctrl+Shift+P` to open the Command Palette.\n"
        "3. Search with `Ctrl+F`, then `F3` / `Shift+F3` to move through matches.\n"
        "4. Use the Navigate menu for line, page, heading, block, and location jumps.\n\n"
        "## Editing highlights\n\n"
        "- Markdown/HTML formatting shortcuts: `Ctrl+B`, `Ctrl+I`, `Ctrl+Alt+1..6`.\n"
        "- Tag helpers: Insert HTML Tag and Insert Markdown Tag from the Format menu.\n"
        "- Find all matches with `Alt+F3`.\n\n"
        "## Learn shortcuts\n\n"
        "Open **Tools -> Keyboard Reference** to generate the latest keymap reference."
    )


def build_keyboard_reference(
    commands: list[Command], feature_manager: FeatureManager | None = None
) -> str:
    grouped: dict[str, list[Command]] = defaultdict(list)
    if feature_manager is not None:
        commands = feature_manager.visible_commands(commands)
    for command in sorted(commands, key=lambda item: item.id):
        section = command.id.split(".", 1)[0].capitalize()
        grouped[section].append(command)

    lines = ["# Keyboard Reference", "", "Generated from the active command registry.", ""]
    for section in sorted(grouped.keys()):
        lines.append(f"## {section}")
        lines.append("")
        for command in grouped[section]:
            binding = command.keybinding or "(unbound)"
            lines.append(f"- `{binding}` — **{command.title}** (`{command.id}`)")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def build_keyboard_shortcut_html(
    commands: list[Command], feature_manager: FeatureManager | None = None
) -> str:
    """Render every command and its current keybinding as an accessible HTML page.

    Mirrors the grouping used by :func:`build_keyboard_reference`, but produces a
    self-contained, screen-reader-friendly HTML table (one row per command) that
    can be opened in a browser, similar to Reaper's keyboard shortcut export.
    """

    grouped: dict[str, list[Command]] = defaultdict(list)
    if feature_manager is not None:
        commands = feature_manager.visible_commands(commands)
    for command in sorted(commands, key=lambda item: item.id):
        section = command.id.split(".", 1)[0].capitalize()
        grouped[section].append(command)

    parts: list[str] = [
        "<!DOCTYPE html>",
        '<html lang="en">',
        "<head>",
        '<meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        "<title>QUILL Keyboard Shortcuts</title>",
        "<style>",
        "body{font-family:system-ui,Segoe UI,Arial,sans-serif;margin:1.5rem;line-height:1.4;}",
        "h1{font-size:1.5rem;}",
        "h2{margin-top:1.75rem;font-size:1.2rem;}",
        "table{border-collapse:collapse;width:100%;margin-top:0.5rem;}",
        "caption{text-align:left;font-weight:bold;padding:0.25rem 0;}",
        "th,td{border:1px solid #999;padding:0.4rem 0.6rem;text-align:left;vertical-align:top;}",
        "th{background:#f0f0f0;}",
        "tbody tr:nth-child(even){background:#f7f7f7;}",
        "code{font-family:Consolas,Menlo,monospace;}",
        "</style>",
        "</head>",
        "<body>",
        "<h1>QUILL Keyboard Shortcuts</h1>",
        "<p>Generated from the active command registry. "
        "Commands without an assigned key are marked <em>Unassigned</em>.</p>",
    ]
    for section in sorted(grouped.keys()):
        parts.append(f"<h2>{escape(section)}</h2>")
        parts.append("<table>")
        parts.append(f"<caption>{escape(section)} commands</caption>")
        parts.append(
            "<thead><tr>"
            '<th scope="col">Keystroke</th>'
            '<th scope="col">Command</th>'
            '<th scope="col">Command ID</th>'
            "</tr></thead>"
        )
        parts.append("<tbody>")
        for command in grouped[section]:
            binding = command.keybinding
            keystroke = f"<code>{escape(binding)}</code>" if binding else "<em>Unassigned</em>"
            parts.append(
                "<tr>"
                f"<td>{keystroke}</td>"
                f"<td>{escape(command.title)}</td>"
                f"<td><code>{escape(command.id)}</code></td>"
                "</tr>"
            )
        parts.append("</tbody>")
        parts.append("</table>")

    # ----------------------------------------------------------------------
    # QUILL Key Layered Shortcuts (Dynamic)
    # ----------------------------------------------------------------------
    def binding_lookup(cmd_id: str) -> str | None:
        return next((c.keybinding for c in commands if c.id == cmd_id), None)

    for mode, title in [(MODE_PREFIX, "QUILL Key Prefix"), (MODE_BROWSE, "QUILL Key Browse Mode")]:
        groups = build_cheat_sheet(
            mode=mode,
            binding_lookup=binding_lookup,
            counts={},  # Omit counts for static export
            quill_key_label="QUILL key",
        )
        parts.append(f"<h2>{escape(title)}</h2>")
        for group in groups:
            parts.append(f"<h3>{escape(group.title)}</h3>")
            parts.append("<table>")
            parts.append(
                "<thead><tr><th scope='col'>Key</th><th scope='col'>Description</th></tr></thead>"
            )
            parts.append("<tbody>")
            for entry in group.entries:
                key_text = f"<code>{escape(entry.key)}</code>" if entry.key else "<em>Unbound</em>"
                parts.append(f"<tr><td>{key_text}</td><td>{escape(entry.description)}</td></tr>")
            parts.append("</tbody></table>")

    parts.append("</body>")
    parts.append("</html>")
    return "\n".join(parts) + "\n"
