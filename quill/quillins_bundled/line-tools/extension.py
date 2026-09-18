"""Line Tools - a bundled Layer 2 Quillin (Tier C).

**One** cursor-aware line operation: join with the next line. It shipped with
six, and the other five -- duplicate line, delete line, move line up, move line
down, join paragraph lines -- were verbs QUILL's core already registers on real
chords (`Ctrl+D`, `Ctrl+Shift+Delete`, `Ctrl+Shift+Up`/`Down`,
`Ctrl+Alt+Shift+J`). A Quillin may *add* a verb and may never re-ship one the
core has: two registrations of one verb is two places for the behaviour and the
wording to drift, and the audit found pairs that already had (bad.md 7.1,
P2.5). They were retired on 2026-09-18; the core commands are unchanged and
keep their keys.

Each operation uses the new ``get_cursor_offset()`` and ``set_cursor()`` API
methods to read and reposition the caret as an integer character offset, so
the algorithm can work with the same coordinate system as the pure text
functions it calls. Changes are applied as a single ``set_text`` undoable edit
followed by a ``set_cursor`` reposition.

Capabilities used: ``editor.read`` (read buffer text and cursor offset),
``editor.write`` (replace document text and set cursor position),
``ui.announce`` (optional no-op), ``ui.command`` (handler commands). No
filesystem, network, clipboard, or storage access.
"""

from __future__ import annotations

from line_ops import join_with_next_line


def register(api):
    """Register every line-tool handler."""

    def _make_simple_command(transform):
        """Build a command that applies a (text, cursor) -> (text, cursor) transform."""

        def command(ctx):
            text = ctx.get_text()
            cursor = ctx.get_cursor_offset()
            new_text, new_cursor = transform(text, cursor)
            if new_text != text:
                ctx.set_text(new_text)
            ctx.set_cursor(new_cursor)

        return command

    api.register_command("join_with_next_line", _make_simple_command(join_with_next_line))
