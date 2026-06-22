"""Unit tests for the QUILL Key chord-prefix display rewriter.

The rewriter is the single source of truth for turning a stored
binding (``"Ctrl+Shift+Grave, S"``) into a user-visible label
(``"QUILL Key + S"``). These tests pin every documented branch of
the rewrite plus the no-op cases so a future edit cannot silently
regress the display.
"""

from __future__ import annotations

from quill.branding import QUILL_KEY_LABEL
from quill.core.keymap_format import (
    format_binding_for_display,
    format_quill_key_chord,
)


class TestFormatBindingForDisplay:
    """format_binding_for_display(...) rewrites a stored binding."""

    def test_chord_with_simple_second_key(self) -> None:
        assert format_binding_for_display("Ctrl+Shift+Grave, S") == f"{QUILL_KEY_LABEL} + S"

    def test_chord_with_shift_modifier(self) -> None:
        assert (
            format_binding_for_display("Ctrl+Shift+Grave, Shift+S")
            == f"{QUILL_KEY_LABEL} + Shift+S"
        )

    def test_chord_with_alt_modifier(self) -> None:
        assert format_binding_for_display("Ctrl+Shift+Grave, Alt+1") == f"{QUILL_KEY_LABEL} + Alt+1"

    def test_non_chord_binding_passes_through(self) -> None:
        assert format_binding_for_display("Ctrl+N") == "Ctrl+N"
        assert format_binding_for_display("Ctrl+Shift+S") == "Ctrl+Shift+S"
        assert format_binding_for_display("F7") == "F7"

    def test_empty_string_returns_empty(self) -> None:
        assert format_binding_for_display("") == ""

    def test_none_returns_empty(self) -> None:
        assert format_binding_for_display(None) == ""

    def test_whitespace_only_returns_empty(self) -> None:
        assert format_binding_for_display("   ") == ""

    def test_bare_prefix_returns_label(self) -> None:
        assert format_binding_for_display("Ctrl+Shift+Grave") == QUILL_KEY_LABEL

    def test_chord_without_space_after_comma_passes_through(self) -> None:
        # Must match exactly "<prefix>, " (with a trailing space);
        # a binding like "Ctrl+Shift+Grave,1" with no space is not
        # a valid chord and is left untouched.
        assert format_binding_for_display("Ctrl+Shift+Grave,1") == "Ctrl+Shift+Grave,1"

    def test_chord_with_empty_second_key_passes_through(self) -> None:
        # "Ctrl+Shift+Grave, " has the grammar prefix but the
        # second-key is whitespace. After the formatter's leading
        # .strip() the binding becomes "Ctrl+Shift+Grave," which
        # no longer matches the "<prefix>, " needle, so the binding
        # passes through unchanged. The grammar parser would not
        # accept this as a valid chord either.
        assert format_binding_for_display("Ctrl+Shift+Grave, ") == "Ctrl+Shift+Grave,"

    def test_custom_prefix(self) -> None:
        # When a user rebinds quill_key_binding, the rewrite follows
        # the configured prefix.
        assert (
            format_binding_for_display("Ctrl+Alt+Grave, V", prefix="Ctrl+Alt+Grave")
            == f"{QUILL_KEY_LABEL} + V"
        )

    def test_custom_prefix_with_default_prefix_does_not_match(self) -> None:
        # A binding in the default prefix form is left alone when
        # the caller is asking us to use a different prefix.
        assert (
            format_binding_for_display("Ctrl+Shift+Grave, V", prefix="Ctrl+Alt+Grave")
            == "Ctrl+Shift+Grave, V"
        )

    def test_surrounding_whitespace_stripped(self) -> None:
        assert format_binding_for_display("  Ctrl+Shift+Grave, F  ") == f"{QUILL_KEY_LABEL} + F"


class TestFormatQuillKeyChord:
    """format_quill_key_chord(prefix, second_key) builds a chord label."""

    def test_normal_call(self) -> None:
        assert format_quill_key_chord("Ctrl+Shift+Grave", "F") == f"{QUILL_KEY_LABEL} + F"

    def test_second_key_whitespace_trimmed(self) -> None:
        assert (
            format_quill_key_chord("Ctrl+Shift+Grave", "  Shift+S  ")
            == f"{QUILL_KEY_LABEL} + Shift+S"
        )

    def test_empty_prefix_returns_label(self) -> None:
        assert format_quill_key_chord("", "F") == QUILL_KEY_LABEL

    def test_empty_second_key_returns_label(self) -> None:
        assert format_quill_key_chord("Ctrl+Shift+Grave", "") == QUILL_KEY_LABEL

    def test_both_empty_returns_label(self) -> None:
        assert format_quill_key_chord("", "") == QUILL_KEY_LABEL
