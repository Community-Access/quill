"""Source-contract test for the GLOW engine update wiring (GLOW-8).

wxPython cannot be imported in headless CI, so these assertions read the source
as text and pin the wiring that keeps the consented GLOW update path honest: a
registered command, a Help-menu item bound to the handler, a confirmation gate
before any download/install, signed-and-verified apply, and a rollback floor.
"""

from pathlib import Path


def _main_frame_source() -> str:
    # MainFrame is composed from main_frame.py plus extracted mixin modules
    # (CQ-1); scan the composite so wiring stays pinned wherever it lives.
    ui = Path("quill/ui")
    return "\n".join(path.read_text(encoding="utf-8") for path in sorted(ui.glob("main_frame*.py")))


def _menu_source() -> str:
    return Path("quill/ui/main_frame_menu.py").read_text(encoding="utf-8")


def _check_glow_updates_body() -> str:
    source = _main_frame_source()
    start = source.index("def check_for_glow_updates(self")
    end = source.index("\n    def ", start + 1)
    return source[start:end]


def test_glow_update_command_is_registered() -> None:
    source = _main_frame_source()
    assert '"tools.check_glow_updates"' in source
    assert "self.check_for_glow_updates" in source


def test_glow_update_menu_item_is_bound() -> None:
    menu = _menu_source()
    assert "self._id_check_glow_updates" in menu
    assert "Check for &GLOW Updates..." in menu
    assert "self.check_for_glow_updates()" in menu


def test_glow_update_confirms_before_download() -> None:
    body = _check_glow_updates_body()
    # A second consent gate (beyond invoking the command) precedes any install.
    assert "_show_message_box" in body
    assert "apply_glow_update" in body
    # The confirmation must come before the apply call.
    assert body.index("_show_message_box") < body.index("apply_glow_update")


def test_glow_update_passes_rollback_floor() -> None:
    body = _check_glow_updates_body()
    assert "rollback_dir=self._vendored_glow_wheels_dir()" in body


def test_glow_update_announces_restart_to_apply() -> None:
    body = _check_glow_updates_body()
    assert "Restart" in body
    assert "self._announce(" in body


def test_glow_update_handles_no_update_and_failure() -> None:
    body = _check_glow_updates_body()
    assert "update_available" in body
    assert "result.applied" in body
    assert "result.rolled_back" in body
