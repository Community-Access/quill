"""The suite must never write into a developer's real profile.

``tests/conftest.py`` refuses writes under ``%APPDATA%\\Quill`` and
``%LOCALAPPDATA%\\QuillLite``. Both halves of that guard have been wrong once,
and neither failure announced itself:

* **QUILL Lite's profile was not guarded at all** until 2026-09-21. QUILL's was.
* **The guard patched only ``builtins.open``**, so every ``Path.write_text`` and
  ``Path.write_bytes`` walked past it -- ``pathlib`` calls ``io.open`` by
  attribute lookup on the module, which is a different binding to the same
  object. ``write_json_atomic`` goes that way, so the recovery store went
  unguarded even after the folder was named.

The cost was not theoretical: two tests in ``test_lite_save_path.py`` called
``quill.core.lite.recovery.new_slot`` without isolation, leaving a slot in the
developer's live QUILL Lite store on every run of the suite, for months. Those
slots were part of the sixty-nine unsaved documents a user was offered in a
single Yes/No box on launch.

These tests hold the guard itself, because a guard that has silently stopped
working looks exactly like a guard that has nothing to catch.
"""

from __future__ import annotations

import builtins
import io
import os
from pathlib import Path

import pytest


def test_the_guard_is_installed_over_both_open_names() -> None:
    """Patching ``builtins`` alone leaves every pathlib write unguarded."""
    if not os.environ.get("APPDATA"):
        pytest.skip("the guard only arms when APPDATA is set")
    assert builtins.open is io.open
    assert builtins.open.__name__ == "_guarded_open"


def test_a_pathlib_write_into_quilllites_profile_is_refused(tmp_path: Path) -> None:
    """The exact shape of the leak: Path.write_bytes into the real store."""
    local = os.environ.get("LOCALAPPDATA")
    if not local:
        pytest.skip("no LOCALAPPDATA on this platform")
    target = Path(local) / "QuillLite" / "recovery" / "guard-probe.txt"
    with pytest.raises(AssertionError, match="real profile"):
        target.write_bytes(b"this must never reach the disk")
    assert not target.exists()


def test_a_pathlib_write_into_quills_profile_is_refused() -> None:
    appdata = os.environ.get("APPDATA")
    if not appdata:
        pytest.skip("no APPDATA on this platform")
    target = Path(appdata) / "Quill" / "guard-probe.json"
    with pytest.raises(AssertionError, match="real profile"):
        target.write_text("{}", encoding="utf-8")
    assert not target.exists()


def test_reads_from_a_real_profile_are_untouched() -> None:
    """The guard refuses writes only. A read is how the app starts at all."""
    appdata = os.environ.get("APPDATA")
    if not appdata:
        pytest.skip("no APPDATA on this platform")
    missing = Path(appdata) / "Quill" / "does-not-exist-guard-probe.json"
    with pytest.raises(FileNotFoundError):
        missing.read_text(encoding="utf-8")


def test_writing_anywhere_else_still_works(tmp_path: Path) -> None:
    """A guard that refused everything would pass the tests above and be useless."""
    target = tmp_path / "ordinary.txt"
    target.write_text("fine", encoding="utf-8")
    assert target.read_text(encoding="utf-8") == "fine"


def test_the_lite_recovery_store_fixture_redirects_new_slot(lite_recovery_store) -> None:
    """``new_slot`` resolves the folder itself, so only a patch can move it."""
    from quill.core.lite import recovery

    slot = recovery.new_slot("plain", "")
    assert slot.content_path.parent == lite_recovery_store
