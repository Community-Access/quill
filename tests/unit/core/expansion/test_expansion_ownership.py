"""One keystroke must never fire two expanders.

QUILL's editor expands from the document; Quill Inkwell expands by synthesising
keystrokes. Both are correct on their own, and both together would erase and
retype the same word twice. The contract that prevents it is a window property
QUILL sets on its own frame and the hook checks before it acts.

These are source-contract tests: the Windows API calls themselves cannot run in
CI, but the wiring that must exist can be asserted directly.
"""

from __future__ import annotations

from pathlib import Path

_ROOT = Path(__file__).resolve().parents[4]


def _read(relative: str) -> str:
    return (_ROOT / "quill" / relative).read_text(encoding="utf-8")


def test_the_marker_has_one_definition() -> None:
    source = _read("platform/windows/text_target.py")
    assert 'EXPANSION_OWNER_PROPERTY = "QuillHandlesOwnExpansion"' in source
    for helper in ("claim_own_expansion", "release_own_expansion", "window_handles_own_expansion"):
        assert f"def {helper}(" in source, helper


def test_quill_claims_the_window_it_expands_in() -> None:
    source = _read("ui/main_frame_abbreviations.py")
    assert "claim_own_expansion" in source
    # Claimed while the abbreviation subsystem starts, so the marker is in place
    # before the first keystroke can reach either expander.
    assert "self._claim_own_expansion()" in source


def test_the_hook_yields_to_a_window_that_expands_for_itself() -> None:
    source = _read("platform/windows/expansion_hook.py")
    assert "window_handles_own_expansion" in source
    assert "_window_expands_for_itself" in source


def test_the_check_happens_before_anything_is_typed() -> None:
    """The guard must sit in the key path, not only at injection time.

    Checking later would still let the buffer accumulate and the match fire; the
    point is that Inkwell never even considers a window QUILL owns.
    """
    source = _read("platform/windows/expansion_hook.py")
    guard = source.index("_window_expands_for_itself(window.hwnd)")
    match_call = source.index("match = match_buffer(")
    assert guard < match_call, "the ownership guard must precede matching"
