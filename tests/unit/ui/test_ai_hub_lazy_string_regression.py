"""Regression tests for issue #614 — AI Hub crash on first open.

The user (Developer profile, NVDA) pressed the wizard's "Open AI Hub" button
during first-run setup. The dialog raised ``TypeError: Item at index 0 has
type '_LazyString' but a sequence of bytes or strings is expected`` and
Quill crashed. After that, every launch crashed inside
``_on_editor_caret_activity`` because ``MainFrame.editor`` had not been
bound yet but ``_maybe_play_indent_tone`` read it directly.

These tests pin the fixes at the source level (mirroring the pattern from
issue #261 — see ``tests/unit/ui/test_setup_wizard.py``) and exercise the
indent-tone guard directly.
"""

from __future__ import annotations

import re
import types
from pathlib import Path

# ---------------------------------------------------------------------------
# Source pins — AI Hub dialog must coerce lazy_gettext proxies to str
# ---------------------------------------------------------------------------


def _ai_hub_source() -> str:
    ui = Path(__file__).resolve().parents[3] / "quill" / "ui"
    return (ui / "ai_hub_dialog.py").read_text(encoding="utf-8")


def test_ai_hub_provider_choice_coerces_labels_to_str() -> None:
    """#614: ``wx.Choice(choices=...)`` rejects _LazyString on Windows.

    ``_PROVIDER_CHOICES`` wraps each label in ``lazy_gettext(...)`` for
    Babel extraction. The provider tab must coerce each label to ``str``
    at the wx boundary or the dialog raises ``TypeError`` the first
    time it is opened.
    """
    src = _ai_hub_source()
    # The labels are computed in a separate statement, then passed to wx.Choice.
    # The fix lives in the comprehension that builds ``provider_labels`` —
    # pin the comprehension, not the wx.Choice call.
    match = re.search(
        r"provider_labels\s*=\s*\[[^\]]+\]",
        src,
    )
    assert match is not None, "AIHubDialog provider_labels comprehension not found"
    assert "str(label)" in match.group(0), (
        "AIHubDialog provider_labels must coerce lazy_gettext labels to str"
    )
    # And the wx.Choice call must use that variable.
    assert "choices=provider_labels" in src, (
        "AIHubDialog provider Choice must read from the coerced provider_labels"
    )


def test_ai_hub_instructions_listbox_coerces_titles_to_str() -> None:
    """#614 follow-up: same class of bug in the instructions ListBox."""
    src = _ai_hub_source()
    # The ListBox.Append is inside a loop; pin the call site.
    match = re.search(
        r"self\._inst_list\.Append\([^)]*\)",
        src,
    )
    assert match is not None, "AIHubDialog instructions ListBox.Append not found"
    assert "str(inst.title)" in match.group(0), (
        "AIHubDialog instructions ListBox.Append must coerce inst.title to str"
    )


def test_ai_hub_image_listbox_coerces_titles_to_str() -> None:
    """#614 follow-up: same class of bug in the image-style ListBox."""
    src = _ai_hub_source()
    match = re.search(
        r"self\._img_list\.Append\([^)]*\)",
        src,
    )
    assert match is not None, "AIHubDialog image-style ListBox.Append not found"
    assert "str(style['title'])" in match.group(0), (
        "AIHubDialog image-style ListBox.Append must coerce style title to str"
    )


def test_ai_hub_notebook_pages_coerce_labels_to_str() -> None:
    """#614 follow-up: wx.Notebook.AddPage on Windows also rejects
    _LazyString proxies — the proxy is the page title, not just a
    Choice/ListBox choice. Every AddPage call in the AI Hub dialog
    must wrap its label in ``str(...)`` or the dialog crashes before
    the first tab is built.
    """
    src = _ai_hub_source()
    # Stronger: at least one str(_(...)) wrapping on the outer notebook.
    assert re.search(r"self\._notebook\.AddPage\([^,]+,\s*str\(_\(", src), (
        "AIHubDialog outer Notebook.AddPage must wrap label in str()"
    )
    # And on the sub-notebook too.
    assert re.search(r"sub\.AddPage\([^,]+,\s*str\(_\(", src), (
        "AIHubDialog sub-Notebook.AddPage must wrap label in str()"
    )


# ---------------------------------------------------------------------------
# Direct test — _maybe_play_indent_tone must not crash when editor is unset
# ---------------------------------------------------------------------------


def test_maybe_play_indent_tone_short_circuits_without_editor() -> None:
    """#614: every-launch crash when caret-activity fires before any tab opens.

    The handler ``_on_editor_caret_activity`` calls
    ``_maybe_play_indent_tone``. The mixin reads ``self.editor`` directly,
    but ``self.editor`` is only bound when a tab is selected. Before that
    first selection, the attribute is missing. The mixin must short-circuit
    cleanly rather than raising ``AttributeError``.
    """
    from quill.ui.main_frame_power_tools import PowerToolsActionsMixin

    class _Stub:
        # Indent tone is on iff indent_tone_scale is set; this guarantees
        # the mixin gets past the first guard and reaches the editor access.
        settings = types.SimpleNamespace(indent_tone_scale="pentatonic", indent_size=4)
        # Deliberately NO `editor` attribute — mirrors a fresh launch.
        _indent_tone_last_level: int | None = None

    stub = _Stub()
    # Bind the method onto the stub and call it. Must not raise.
    PowerToolsActionsMixin._maybe_play_indent_tone(stub)

    # And the level tracker must remain unset (no tone fired).
    assert stub._indent_tone_last_level is None


def test_maybe_play_indent_tone_works_with_editor_present() -> None:
    """Sanity: with an editor present, the level tracker updates as before."""
    from quill.ui.main_frame_power_tools import PowerToolsActionsMixin

    class _FakeEditor:
        def __init__(self, text: str, pos: int) -> None:
            self._text = text
            self._pos = pos

        def GetValue(self) -> str:
            return self._text

        def GetInsertionPoint(self) -> int:
            return self._pos

    class _Stub:
        settings = types.SimpleNamespace(indent_tone_scale="pentatonic", indent_size=4)
        editor = _FakeEditor("    x = 1\n", 0)
        _indent_tone_last_level: int | None = None

        def _current_indent_columns(self) -> int:
            return 4

    stub = _Stub()
    PowerToolsActionsMixin._maybe_play_indent_tone(stub)
    # First fire from level None -> 1 sets the tracker.
    assert stub._indent_tone_last_level == 1
