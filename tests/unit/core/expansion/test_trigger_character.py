"""The trigger character is swallowed and retyped, never raced.

When the hook finds a match, the character that ended the word has not reached
the application yet -- the hook runs before delivery. Letting it through while
backspaces are on their way is the classic way an expander corrupts the very
word it is replacing, and the corruption is timing-dependent, so it shows up on
a loaded machine and nowhere else.

The rule: the hook swallows the trigger key, the worker types it back after the
expansion.
"""

from __future__ import annotations

from pathlib import Path

from quill.core.abbreviations import Abbreviation, AbbreviationLibrary
from quill.core.expansion.matcher import match_buffer
from quill.core.expansion.ring_buffer import RingBuffer

_ROOT = Path(__file__).resolve().parents[4]


def _typed(text: str) -> RingBuffer:
    buffer = RingBuffer()
    for char in text:
        buffer.push(char)
    return buffer


def _library(**fields: object) -> AbbreviationLibrary:
    return AbbreviationLibrary(
        version=2,
        abbreviations=[
            Abbreviation(id="a", abbreviation="btw", expansion="by the way", **fields)  # type: ignore[arg-type]
        ],
    )


def test_the_match_carries_the_trigger_character() -> None:
    match = match_buffer(_typed("btw "), _library())
    assert match is not None
    assert match.trigger_char == " "


def test_punctuation_is_carried_too() -> None:
    match = match_buffer(_typed("btw."), _library())
    assert match is not None
    assert match.trigger_char == "."


def test_only_the_abbreviation_is_erased() -> None:
    # The trigger never reached the application, so it must not be backspaced.
    match = match_buffer(_typed("btw,"), _library())
    assert match is not None
    assert match.backspace_count == len("btw")


def test_the_hook_swallows_the_key_when_it_expands() -> None:
    source = (_ROOT / "quill" / "platform" / "windows" / "expansion_hook.py").read_text(
        encoding="utf-8"
    )
    # Returning 1 from a low-level hook procedure suppresses the keystroke.
    assert "return 1" in source
    assert "def _handle_key(self, vk: int) -> bool:" in source
    assert "def _queue_match(self, match: GlobalMatch) -> bool:" in source


def test_the_injector_types_the_trigger_back_after_the_expansion() -> None:
    source = (_ROOT / "quill" / "platform" / "windows" / "text_injector.py").read_text(
        encoding="utf-8"
    )
    assert 'trigger_char: str = ""' in source
    assert "tail = text + trigger_char" in source


def test_the_caret_offset_accounts_for_what_follows_the_expansion() -> None:
    source = (_ROOT / "quill" / "platform" / "windows" / "text_injector.py").read_text(
        encoding="utf-8"
    )
    assert "caret_from_end + len(trigger_char) + (1 if trailing_space else 0)" in source
