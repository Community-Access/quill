"""Find a setting speaks its match count in QUILL (OSAF testing-4 review).

QUILL withholds ``announce`` from ``show_modal_dialog`` unless the "Entered /
Exited dialog" cues are turned on, and Find a setting took its announcer from
the same argument, so with the default settings it counted matches into a label
and said nothing. The keyboard-only CI run of core task 5 found it.
"""

from __future__ import annotations

from types import SimpleNamespace

import quill.ui.main_frame as main_frame_module
from quill.core.a11y_regions import RegionTracker
from quill.ui.main_frame import MainFrame


def test_settings_search_gets_an_announcer_with_cues_off(monkeypatch) -> None:
    seen: dict[str, object] = {}

    def fake_show(dialog: object, label: str, **kwargs: object) -> int:
        seen.update(kwargs)
        return 0

    monkeypatch.setattr(main_frame_module, "show_modal_dialog", fake_show)
    frame = MainFrame.__new__(MainFrame)
    frame._region_tracker = RegionTracker()
    frame.settings = SimpleNamespace(announce_dialog_transitions=False)

    frame._show_modal_dialog(object(), "Settings", restore_editor_focus=False)

    assert seen["announce"] is None
    assert callable(seen["search_announce"])


def test_settings_dialog_sets_its_own_sizer() -> None:
    # Without a top-level sizer the Settings dialog had no layout, and Find a
    # setting, which wraps the dialog's sizer, was silently never installed.
    import ast
    import inspect
    import textwrap

    from quill.ui.main_frame_preferences import PreferencesMixin

    source = textwrap.dedent(inspect.getsource(PreferencesMixin.open_general_preferences))
    calls = [
        node
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.Call)
        and getattr(node.func, "attr", "") in {"SetSizer", "SetSizerAndFit"}
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "dialog"
    ]
    assert calls, "open_general_preferences never gives the Settings dialog a sizer"
