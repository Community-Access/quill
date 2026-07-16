"""Source-contract test for issue #132.

The "AI Detail" menu line is informational and must not be a second launcher for
the AI Connection dialog (connection setup lives only in "AI Model &
Connection..."). wxPython is headless-unfriendly, so this reads the menu source
and pins the binding.
"""

from __future__ import annotations

from pathlib import Path


def _menu_source() -> str:
    return Path("quill/ui/main_frame_menu.py").read_text(encoding="utf-8") + Path(
        "quill/ui/main_frame_menu_bindings.py"
    ).read_text(encoding="utf-8")


def test_ai_detail_refreshes_status_instead_of_opening_connection() -> None:
    source = _menu_source()
    assert (
        "lambda _e: self._refresh_ai_status(),\n            id=self._id_ai_status_detail," in source
    )
    # It must not be wired to the connection dialog any more.
    assert (
        "lambda _e: self.open_ai_preferences(),\n            id=self._id_ai_status_detail,"
        not in source
    )


def test_ai_detail_label_does_not_advertise_opening_a_dialog() -> None:
    source = _menu_source()
    assert "AI Detail: Open AI Connection" not in source
