"""Positions a native text control counts versus Python's len (todo P3: an
emoji typed into a plain edit control lost its first half)."""

from __future__ import annotations

from quill.core.text_units import native_length, utf16_length


def test_an_emoji_is_two_units_and_one_character() -> None:
    assert len("\U0001f600") == 1
    assert utf16_length("\U0001f600") == 2
    assert utf16_length("a\U0001f44db\U00020041") == 6


def test_utf16_length_matches_the_encoder() -> None:
    for text in ("", "plain", "é\n\t", "\U0001f468‍\U0001f469", "\U0010ffff"):
        assert utf16_length(text) == len(text.encode("utf-16-le")) // 2


def test_native_length_is_utf16_on_windows_only() -> None:
    assert native_length("\U0001f600!", platform="win32") == 3
    assert native_length("\U0001f600!", platform="linux") == 2
    assert native_length("\U0001f600!", platform="darwin") == 2


class _Utf16Control:
    """A text control that counts positions the way wxMSW does: UTF-16 units,
    handing GetRange back as an ordinary (code point) Python string."""

    def __init__(self, text: str, caret_units: int) -> None:
        self._units = text.encode("utf-16-le")
        self._caret = caret_units

    def GetInsertionPoint(self) -> int:  # noqa: N802 - wx's name
        return self._caret

    def GetLastPosition(self) -> int:  # noqa: N802
        return len(self._units) // 2

    def GetRange(self, start: int, end: int) -> str:  # noqa: N802
        return self._units[start * 2 : end * 2].decode("utf-16-le")


def test_dictation_line_bounds_count_an_emoji_as_the_control_does() -> None:
    from quill.ui.windows_dictation_ports import EditorDocument

    text = "first\nhi \U0001f600 there\nlast"
    line_start = utf16_length("first\n")
    line_end = line_start + utf16_length("hi \U0001f600 there")
    caret = line_start + utf16_length("hi \U0001f600 th")
    document = EditorDocument.__new__(EditorDocument)
    document._control = _Utf16Control(text, caret)

    start, end = document.line_bounds()

    import sys

    if sys.platform == "win32":
        assert (start, end) == (line_start, line_end)
        assert document._control.GetRange(start, end) == "hi \U0001f600 there"


def test_offsets_convert_both_ways_around_emoji() -> None:
    """Review 2026-11-09, QUILL 5: code points to the control's units and back."""
    from quill.core.text_units import native_offset, text_index

    text = "a\U0001f600b\U0001f600\U0001f600c"
    units = [native_offset(text, i, platform="win32") for i in range(len(text) + 1)]
    assert units == [0, 1, 3, 4, 6, 8, 9]
    assert [text_index(text, u, platform="win32") for u in units] == list(range(len(text) + 1))
    assert text_index(text, 2, platform="win32") == 2, "inside a pair: the character after"
    assert text_index(text, 99, platform="win32") == len(text)
    assert native_offset(text, 3, platform="linux") == text_index(text, 3, platform="linux") == 3
