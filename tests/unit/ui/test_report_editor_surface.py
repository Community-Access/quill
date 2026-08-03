"""The spoken Report Editor Surface diagnostic (assessment item).

One keystroke speaks the surface kind, native class/emulation state when a
QuillRichEdit wrapper is present, the two braille editor settings, and the
braille bridge state -- so a braille bug report from someone who cannot
screenshot is actionable on the first message. Content-free by design.
"""

from __future__ import annotations

from types import SimpleNamespace

from quill.ui.main_frame_devtools import DevToolsMixin


class _Frame(DevToolsMixin):
    def __init__(self, *, engine_env: dict[str, object] | None = None) -> None:
        self.editor = SimpleNamespace(surface_kind="quill_richedit")
        self.settings = SimpleNamespace(
            braille_editor_system_edit_fix=True,
            braille_editor_hide_border=True,
        )
        env = engine_env
        if env is not None:
            self._announcement_engine = SimpleNamespace(
                diagnostics_environment=lambda: env,
            )
        self.announced: list[str] = []
        self.status: list[str] = []

    def _announce(self, message: str) -> None:
        self.announced.append(message)

    def _set_status(self, message: str) -> None:
        self.status.append(message)


def test_report_speaks_surface_settings_and_braille_state() -> None:
    frame = _Frame(
        engine_env={
            "announcement_backend_name": "JAWS",
            "announcement_braille_enabled": True,
            "announcement_braille_supported": True,
            "announcement_braille_active": True,
        }
    )

    frame.report_editor_surface()

    assert len(frame.announced) == 1
    message = frame.announced[0]
    assert "Editor surface" in message
    assert "Braille system edit fix on" in message
    assert "Editor border hidden" in message
    assert "Braille output active" in message
    assert "Announcement backend JAWS" in message
    # The same text lands on the status bar for later review.
    assert frame.status == frame.announced


def test_report_names_a_missing_display_bridge() -> None:
    frame = _Frame(
        engine_env={
            "announcement_backend_name": "SAPI",
            "announcement_braille_enabled": True,
            "announcement_braille_supported": False,
            "announcement_braille_active": False,
        }
    )

    frame.report_editor_surface()

    assert "Braille output no display bridge" in frame.announced[0]


def test_report_degrades_without_an_engine() -> None:
    frame = _Frame(engine_env=None)

    frame.report_editor_surface()

    assert len(frame.announced) == 1
    assert "Editor surface" in frame.announced[0]
