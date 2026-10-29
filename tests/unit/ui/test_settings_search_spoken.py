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
