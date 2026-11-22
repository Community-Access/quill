"""QUILL's Scribe for Documents rows: NEVER, named so the palette finds them.

A sentence never sends a document to Scribe, signs in or out, or swaps a
finished document in: every one of these follows the person's own choice in
a menu or the palette (PRD 10.1.1). They have rows only so the palette's
aliases and a refusal's "It's in Tools, Scribe for Documents" can find them.
"""

from __future__ import annotations

from quill.core.command_catalogue.spec import CommandSpec, Risk

__all__ = ["SCRIBE_ROWS"]

#: Kept short: a refusal reads "Not from a sentence: it's in <where>." in 12 words.
_TOOLS_MENU = "Tools, Scribe for Documents"

#: (command id, title, aliases, group, where)
_TABLE: tuple[tuple[str, str, tuple[str, ...], str, str], ...] = (
    (
        "scribe.convert_file",
        "Convert a File with Scribe",
        ("scribe a file",),
        "Tools",
        _TOOLS_MENU,
    ),
    (
        "scribe.convert_this",
        "Convert This Document with Scribe",
        ("scribe this document",),
        "Tools",
        _TOOLS_MENU,
    ),
    (
        "scribe.convert_link",
        "Convert from a Link with Scribe",
        ("scribe a link",),
        "Tools",
        _TOOLS_MENU,
    ),
    (
        "scribe.my_documents",
        "My Scribe Documents",
        ("scribe documents", "scribe library"),
        "Tools",
        _TOOLS_MENU,
    ),
    (
        "scribe.conversions",
        "Scribe Conversions",
        ("scribe conversions", "scribe progress"),
        "Tools",
        _TOOLS_MENU,
    ),
    (
        "scribe.status",
        "Scribe Status",
        ("scribe status", "conversion status"),
        "Tools",
        _TOOLS_MENU,
    ),
    (
        "scribe.repeat",
        "Repeat Last Scribe Message",
        ("repeat scribe",),
        "Tools",
        _TOOLS_MENU,
    ),
    (
        "scribe.replace_finished",
        "Replace with Finished Document",
        ("finished document",),
        "Tools",
        _TOOLS_MENU,
    ),
    ("scribe.sign_in", "Sign In to Scribe", ("scribe sign in",), "Tools", _TOOLS_MENU),
    ("scribe.sign_out", "Sign Out of Scribe", ("scribe sign out",), "Tools", _TOOLS_MENU),
    (
        "scribe.account",
        "Open My Scribe Account",
        ("scribe account",),
        "Tools",
        _TOOLS_MENU,
    ),
    (
        "scribe.options",
        "Scribe Options",
        ("scribe options", "scribe settings"),
        "Tools",
        _TOOLS_MENU,
    ),
    (
        "scribe.about",
        "About Scribe for Documents",
        ("about scribe",),
        "Tools",
        _TOOLS_MENU,
    ),
    (
        "scribe.file_documents",
        "My Scribe Documents (File)",
        (),
        "File",
        "File",
    ),
    (
        "scribe.import",
        "Import with Scribe",
        ("scribe import",),
        "File",
        "File, Import",
    ),
    (
        "scribe.export",
        "Export with Scribe",
        ("scribe export",),
        "File",
        "File, Export",
    ),
    (
        "scribe.braille",
        "Translate with Scribe",
        ("scribe braille",),
        "Tools",
        "Tools, Braille",
    ),
    ("scribe.window", "Scribe Conversions Window", (), "Window", "Window"),
)

SCRIBE_ROWS: tuple[CommandSpec, ...] = tuple(
    CommandSpec(command_id, title, aliases=aliases, risk=Risk.NEVER, group=group, where=where)
    for command_id, title, aliases, group, where in _TABLE
)
