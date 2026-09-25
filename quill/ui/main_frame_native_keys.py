"""The native control brings its own keyboard, and it has to be answered.

Every document tab in QUILL is a Windows Rich Edit control -- plain text and
Markdown included, because that is what gives the braille display and the
screen reader a text surface worth reading. The cost is the control's own
chords: Ctrl+U underlines, Ctrl+L, Ctrl+R, Ctrl+E and Ctrl+J re-align,
Ctrl+Shift+= raises the baseline. In a Rich Text document those are exactly
right. In a Markdown or plain one they apply a formatting run to a document
that has no formatting -- not marked dirty, not announced, not saved, but on
the undo stack and on the screen, so the buffer and the file it will write
disagree and nothing in the app ever mentions it (bad.md R9).

Extracted from ``main_frame.py`` on 2026-09-18 under GATE-11, and it is a real
seam: this is the only place in the frame that cares what the *toolkit* does
with a key rather than what QUILL does with it.

The vocabulary -- which chords, and what each would have done -- is shared with
QUILL Lite in :mod:`quill.core.native_richedit_keys`, so the two products cannot
explain one dead key two different ways.
"""

from __future__ import annotations

__all__ = ["NativeKeyGuardMixin"]


class NativeKeyGuardMixin:
    """Swallow the toolkit's own formatting chords where they mean nothing."""

    def _swallow_native_formatting_key(self, event: object) -> bool:
        """Stop the native control formatting a document that has no formatting.

        Every document tab is a Rich Edit control, plain text and Markdown
        included, because that is what gives the braille display and the reader
        a text surface worth reading. The control brings its own keyboard with
        it: Ctrl+U underlines, Ctrl+L/R/E/J re-align, Ctrl+Shift+= raises the
        baseline. In a Rich Text document those are right. In a Markdown or
        plain one they apply a formatting run to a document that has none --
        not dirty, not announced, not saved, but on the undo stack and on the
        screen, so the document differs from what will be written and nothing
        ever says so (bad.md R9).

        Said once per document, which was Jeff's call on 2026-09-18: a key that
        does nothing and explains nothing reads as a broken key, and one that
        explains itself on every press becomes noise for exactly the person
        whose Word habits keep reaching for it.

        A chord QUILL itself binds never reaches here -- the registry runs it
        first -- so this only ever swallows keys that would otherwise be the
        control acting on its own.
        """
        from quill.core.native_richedit_keys import (
            native_formatting_effect,
            native_formatting_notice,
        )

        if self._current_editor_mode() in {"rich", "rich_converted"}:
            return False
        # getattr, not a direct call: a key event reaches this handler from
        # several places, and the guard must never be the reason a keystroke
        # raises. No key code means nothing to swallow.
        unicode_key = getattr(event, "GetUnicodeKey", None)
        key_code = getattr(event, "GetKeyCode", None)
        try:
            raw = (unicode_key() if callable(unicode_key) else 0) or (
                key_code() if callable(key_code) else 0
            )
            key = chr(int(raw))
        except (ValueError, OverflowError, TypeError):
            return False

        def held(name: str) -> bool:
            probe = getattr(event, name, None)
            return bool(probe()) if callable(probe) else False

        effect = native_formatting_effect(
            ctrl=held("ControlDown"),
            shift=held("ShiftDown"),
            alt=held("AltDown"),
            key=key,
        )
        if effect is None:
            return False
        if self._run_chord_through_registry(self._chord_text(event, key)):
            return True
        seen = getattr(self, "_native_key_notices", None)
        if seen is None:
            seen = set()
            self._native_key_notices = seen
        token = (id(self.document), effect)
        if token not in seen:
            seen.add(token)
            self._set_status(native_formatting_notice(effect, self._native_key_kind_label()))
        return True

    @staticmethod
    def _chord_text(event: object, key: str) -> str:
        parts = ["Ctrl"]
        if event.ShiftDown():
            parts.append("Shift")
        parts.append(key.upper())
        return "+".join(parts)

    def _native_key_kind_label(self) -> str:
        """ "Markdown", "HTML" or "plain text" -- what this document actually is.

        The names come from the shared table so that QUILL Lite, whose own
        status cell spells these differently, cannot end up saying a different
        sentence about the same key in the same file.
        """
        from quill.core.native_richedit_keys import notice_kind_label

        return notice_kind_label(str(self._effective_markup_kind() or ""))
