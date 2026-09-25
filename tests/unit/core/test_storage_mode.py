from __future__ import annotations

import re
from pathlib import Path

import pytest

from quill.core import storage_mode
from quill.core.paths import app_data_dir
from quill.core.storage_mode import custom_path, load_storage_mode, save_storage_mode

pytestmark = pytest.mark.smoke


def _make_portable_bundle(tmp_path: Path) -> Path:
    """Create the *new* portable-bundle layout: quill.exe + data/ at the root.

    The portable bundle ships quill.exe (the hoisted launcher) and an empty
    ``data/`` folder next to it. Both must be present for detection -- the
    data/ folder is the user's deliberate opt-in, not an env-var say-so.
    """
    root = tmp_path / "QuillPortable"
    root.mkdir()
    (root / "quill.exe").write_bytes(b"MZ\x00\x00")
    (root / "data").mkdir()
    return root


def _make_legacy_portable_bundle(tmp_path: Path) -> Path:
    """Create a beta-1 portable bundle: only run-quill.cmd at the root.

    Back-compat evidence: a beta-1 user upgrading to a 0.7.0 bundle that
    still ships run-quill.cmd but no data/ folder must keep working.
    """
    root = tmp_path / "QuillPortableLegacy"
    root.mkdir()
    (root / "run-quill.cmd").write_text("@echo off\r\n", encoding="utf-8")
    return root


def _pin_executable_away_from_any_real_bundle(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Make the sys.executable fallback chain deterministic in tests.

    Without this, portable_root_dir()'s fallback (walking up from
    sys.executable) would check the real dev machine's Python install
    location, which happens to lack run-quill.cmd today but is not a
    guarantee a test should depend on.
    """
    fake_exe_dir = tmp_path / "fake-python" / "bin"
    fake_exe_dir.mkdir(parents=True)
    monkeypatch.setattr(storage_mode.sys, "executable", str(fake_exe_dir / "python.exe"))


def test_portable_root_requires_run_quill_cmd_evidence(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """L-9: a bare QUILL_APP_ROOT value is not enough on its own."""
    _pin_executable_away_from_any_real_bundle(monkeypatch, tmp_path)
    bare_dir = tmp_path / "not-a-real-bundle"
    bare_dir.mkdir()
    monkeypatch.setenv("QUILL_APP_ROOT", str(bare_dir))
    assert storage_mode.portable_root_dir() is None


def test_portable_root_resolves_with_verified_bundle(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    root = _make_portable_bundle(tmp_path)
    monkeypatch.setenv("QUILL_APP_ROOT", str(root))
    resolved = storage_mode.portable_root_dir()
    assert resolved == (root / "data").resolve()
    # The data folder is created by the build, not at first run.
    assert resolved.is_dir()


def test_legacy_run_quill_cmd_bundle_still_resolves_as_portable(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A beta-1 portable bundle (run-quill.cmd, no data/) keeps working.

    The detection contract accepts run-quill.cmd as back-compat evidence
    so a user upgrading from a beta-1 portable bundle isn't broken.
    """
    root = _make_legacy_portable_bundle(tmp_path)
    monkeypatch.setenv("QUILL_APP_ROOT", str(root))
    resolved = storage_mode.portable_root_dir()
    assert resolved == (root / "data").resolve()
    # data/ does not yet exist on a legacy bundle; the helper just
    # returns the path the user can opt into.
    assert not resolved.exists()


def test_quill_exe_alone_without_data_folder_is_not_portable(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A folder with quill.exe but no data/ is NOT a portable install.

    The data/ folder is the user's deliberate opt-in. A bundle freshly
    copied from a zip that missed the data/ folder must not silently
    route settings to the wrong place.
    """
    _pin_executable_away_from_any_real_bundle(monkeypatch, tmp_path)
    root = tmp_path / "QuillNoData"
    root.mkdir()
    (root / "quill.exe").write_bytes(b"MZ\x00\x00")
    monkeypatch.setenv("QUILL_APP_ROOT", str(root))
    monkeypatch.setenv("APPDATA", str(tmp_path / "appdata"))
    assert storage_mode.portable_root_dir() is None
    assert app_data_dir() == (tmp_path / "appdata" / "Quill").resolve()


def test_data_folder_alone_without_quill_exe_is_not_portable(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A data/ folder without quill.exe is NOT a portable install.

    Some third-party tools create data/ folders as part of their own
    layout. We do not mistake those for a portable QUILL install.
    """
    _pin_executable_away_from_any_real_bundle(monkeypatch, tmp_path)
    root = tmp_path / "NotAQuillBundle"
    root.mkdir()
    (root / "data").mkdir()
    monkeypatch.setenv("QUILL_APP_ROOT", str(root))
    monkeypatch.setenv("APPDATA", str(tmp_path / "appdata"))
    assert storage_mode.portable_root_dir() is None
    assert app_data_dir() == (tmp_path / "appdata" / "Quill").resolve()


def test_storage_mode_uses_portable_root(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, isolated_profile: Path
) -> None:
    # isolated_profile points APPDATA at a clean temp dir: the appdata fallback is
    # always in storage_mode_paths(), so without it this test reads the real
    # %APPDATA%\Quill\storage-mode.json on a developer machine and fails.
    root = _make_portable_bundle(tmp_path)
    monkeypatch.setenv("QUILL_APP_ROOT", str(root))
    assert load_storage_mode() is None

    save_storage_mode("portable")

    assert load_storage_mode() == "portable"
    assert app_data_dir() == (root / "data").resolve()


def test_storage_mode_can_prefer_appdata(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    root = _make_portable_bundle(tmp_path)
    monkeypatch.setenv("QUILL_APP_ROOT", str(root))
    monkeypatch.setenv("APPDATA", str(tmp_path / "appdata"))
    save_storage_mode("appdata")

    assert load_storage_mode() == "appdata"
    assert app_data_dir() == (tmp_path / "appdata" / "Quill").resolve()


def test_custom_mode_works_without_a_portable_bundle(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """#615: non-portable users can also redirect their data folder."""
    _pin_executable_away_from_any_real_bundle(monkeypatch, tmp_path)
    monkeypatch.delenv("QUILL_APP_ROOT", raising=False)
    monkeypatch.setenv("APPDATA", str(tmp_path / "appdata"))
    target = tmp_path / "MyQuillData"

    save_storage_mode("custom", path=target)

    assert load_storage_mode() == "custom"
    assert custom_path() == target.resolve()
    assert app_data_dir() == target.resolve()


def test_save_storage_mode_custom_requires_a_path(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _pin_executable_away_from_any_real_bundle(monkeypatch, tmp_path)
    monkeypatch.delenv("QUILL_APP_ROOT", raising=False)
    monkeypatch.setenv("APPDATA", str(tmp_path / "appdata"))
    with pytest.raises(ValueError, match="requires a path"):
        save_storage_mode("custom")


def test_arbitrary_quill_app_root_alone_does_not_redirect_data(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """L-9 (carried forward): setting QUILL_APP_ROOT to an attacker-chosen

    directory with no run-quill.cmd there must not be treated as portable.
    """
    _pin_executable_away_from_any_real_bundle(monkeypatch, tmp_path)
    monkeypatch.setenv("QUILL_APP_ROOT", str(tmp_path / "attacker-controlled"))
    monkeypatch.setenv("APPDATA", str(tmp_path / "appdata"))
    monkeypatch.delenv("QUILL_DATA_DIR", raising=False)
    assert storage_mode.portable_root_dir() is None
    assert app_data_dir() == (tmp_path / "appdata" / "Quill").resolve()


# ----------------------------------------------------------------------
# Per-product portable-bundle recognition
# ----------------------------------------------------------------------
# Each per-product portable bundle ships its own native launcher (a
# .exe at the anchor root) and a sibling data/ folder. The
# _has_portable_evidence allowlist must list every shipped name --
# otherwise a portable install of that product silently writes to
# %APPDATA% instead of the bundle data/ folder. The on-disk exe names
# are the contract committed to by scripts/build_native_launcher.py and
# quill/native/launcher/ -- see the cross-check in
# tests/unit/scripts/test_build_native_launcher.py.


def _shipped_launcher_exe_names() -> list[str]:
    """Every launcher basename the build actually writes.

    Read out of ``scripts/build_native_launcher.py`` by text rather than by
    import, because that module is a build script that imports build-time
    machinery and is not on the runtime path. ``name=`` in a ``Product(...)``
    is authoritative: it becomes ``PRODUCT_NAME``, the CMake target, and
    therefore the filename on disk.
    """
    script = Path(__file__).resolve().parents[3] / "scripts" / "build_native_launcher.py"
    source = script.read_text(encoding="utf-8")
    return sorted({f"{match}.exe" for match in re.findall(r'^\s*name="([^"]+)",', source, re.M)})


def test_every_shipped_launcher_is_in_the_portable_allowlist() -> None:
    """The gate that stops the sixth app repeating the first five.

    Five products -- QUILL Lite, Inkwell, Beacon, Social and Cast under its
    registry spelling -- were missing from this allowlist until 2026-09-09, so
    their portable builds silently wrote the user's settings and recovery files
    to ``%APPDATA%`` on the host machine instead of to the stick. Nothing failed
    and nothing was announced; it just quietly stopped being portable, on
    somebody else's computer.

    Listing the products by hand in the test below is what let that happen, so
    the list is derived here instead: a new app that builds a launcher and
    forgets the allowlist fails this immediately.
    """
    shipped = _shipped_launcher_exe_names()
    assert shipped, "no Product(name=...) entries found; has the build script moved?"
    missing = [name for name in shipped if name not in storage_mode.PORTABLE_LAUNCHER_EXES]
    assert missing == [], (
        "These products build a native launcher but are not in "
        "storage_mode.PORTABLE_LAUNCHER_EXES, so their portable bundles will "
        f"write to %APPDATA% instead of the bundle's data/ folder: {missing}"
    )


@pytest.mark.parametrize("exe_name", _shipped_launcher_exe_names())
def test_per_product_portable_bundle_recognized(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, exe_name: str
) -> None:
    """A portable bundle of Quill Radio / Weather / Audio Studio is
    recognized when its native launcher + data/ are at the anchor.

    The allowlist in _has_portable_evidence must list every shipped
    per-product exe name. A regression (e.g. a renamed native launcher)
    is a data-loss bug for portable users: their data silently writes
    to %APPDATA% instead of the bundle data/ folder.
    """
    _pin_executable_away_from_any_real_bundle(monkeypatch, tmp_path)
    root = tmp_path / exe_name.replace(".exe", "")
    root.mkdir()
    (root / exe_name).write_bytes(b"MZ\x00\x00")
    (root / "data").mkdir()
    monkeypatch.setenv("QUILL_APP_ROOT", str(root))
    monkeypatch.setenv("APPDATA", str(tmp_path / "appdata"))
    assert storage_mode.portable_root_dir() == (root / "data").resolve(), (
        f"{exe_name} must be in the _has_portable_evidence allowlist so "
        f"this product's portable installs route data to the bundle."
    )


def test_storage_mode_allowlist_is_internally_consistent() -> None:
    """The allowlist in _has_portable_evidence is duplicated knowledge:
    the same names live in scripts/build_native_launcher.py. This test
    keeps the allowlist honest -- every entry must be a plausible
    Windows executable name (ends in .exe, no path separators, non-empty
    stem). If you add a new portable product, the new name must pass
    these checks here AND be wired in build_native_launcher.py
    AND be exercised by test_per_product_portable_bundle_recognized.
    """
    for name in ("quill.exe", "run-quill.cmd"):
        assert name.lower().endswith((".exe", ".cmd")), name
        assert "/" not in name and "\\" not in name, name
        assert name, "empty name in allowlist"


def test_storage_mode_falls_back_when_portable_path_is_not_writable(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    root = _make_portable_bundle(tmp_path)
    monkeypatch.setenv("QUILL_APP_ROOT", str(root))
    monkeypatch.setenv("APPDATA", str(tmp_path / "appdata"))
    monkeypatch.setattr("quill.core.storage_mode.os.access", lambda *_args: False)

    save_storage_mode("appdata")

    fallback_path = tmp_path / "appdata" / "Quill" / "storage-mode.json"
    assert fallback_path.exists()
    assert not (root / "data" / "storage-mode.json").exists()
    assert load_storage_mode() == "appdata"

    stale_portable_path = root / "data" / "storage-mode.json"
    stale_portable_path.parent.mkdir(parents=True, exist_ok=True)
    stale_portable_path.write_text('{"mode":"portable"}', encoding="utf-8")
    assert load_storage_mode() == "appdata"


# ----------------------------------------------------------------------
# A portable bundle is portable before anybody is asked
# ----------------------------------------------------------------------


def test_a_portable_bundle_defaults_to_the_stick_not_the_host_machine(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, isolated_profile: Path
) -> None:
    """Extract the zip, run it, and nothing is written to %APPDATA%.

    Until 2026-09-09 an unanswered storage-mode question meant appdata, so a
    freshly extracted portable QUILL created a folder on the host machine's
    hard drive on first run -- exactly what somebody running from a USB stick
    picked the portable build to avoid, and with nothing to tell them. The user
    guide has said "portable mode is a property of the bundle, not of the
    running environment" throughout; this is what makes that sentence true.
    """
    root = _make_portable_bundle(tmp_path)
    monkeypatch.setenv("QUILL_APP_ROOT", str(root))
    monkeypatch.delenv("QUILL_DATA_DIR", raising=False)
    assert load_storage_mode() is None, "no choice has been made yet"

    assert app_data_dir() == (root / "data").resolve()


def test_an_explicit_appdata_choice_still_beats_the_portable_default(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Defaulting is not overriding. Somebody who asked for appdata gets it."""
    root = _make_portable_bundle(tmp_path)
    monkeypatch.setenv("QUILL_APP_ROOT", str(root))
    monkeypatch.setenv("APPDATA", str(tmp_path / "appdata"))
    monkeypatch.delenv("QUILL_DATA_DIR", raising=False)
    save_storage_mode("appdata")

    assert app_data_dir() == (tmp_path / "appdata" / "Quill").resolve()


def test_a_normal_install_is_unaffected_by_the_portable_default(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """There is no portable root to default to, so nothing moves."""
    _pin_executable_away_from_any_real_bundle(monkeypatch, tmp_path)
    monkeypatch.delenv("QUILL_APP_ROOT", raising=False)
    monkeypatch.setenv("APPDATA", str(tmp_path / "appdata"))
    monkeypatch.delenv("QUILL_DATA_DIR", raising=False)

    assert app_data_dir() == (tmp_path / "appdata" / "Quill").resolve()
