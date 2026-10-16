"""The launcher's release-channel slots, compiled and run (not read as text).

``test_runtime_slot_resolver.py`` pins the slot rules with a Python mirror and
by reading the C. This file compiles the real C and asks it:

* ``runtime_resolve.c``, through a probe, for every slot case -- including the
  one slots exist for: a Beta app whose Beta runtime is missing must NOT fall
  back to Stable's folder;
* the whole launcher (``QuillRadio.exe``, built by
  ``scripts/build_native_launcher.py`` exactly as a release builds it), started
  beside an ini that says ``slot=3.14-beta``, with a fake runtime in both the
  Stable and the Beta folder: only the Beta one may be started.

Skipped where MSVC and CMake are not installed (``compiled_harness.build``).
The two tests that start the built launcher run only in CI, or when
``QUILL_RUN_NATIVE_PROGRAMS=1`` asks for them (``may_run_real_programs``).
Nothing here touches the real profile: ``LOCALAPPDATA`` and ``APPDATA`` point
into the test's own folder.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

from quill.core.updater.runtime_slots import PYTHON_MAJOR
from tests.unit.native import compiled_harness as ch

BASE_URL = (
    "https://github.com/Community-Access/quill/releases/download/runtime-3.14/"
    "QuillVille-Runtime-Setup.exe"
)

pytestmark = pytest.mark.timeout(600)


@pytest.fixture(scope="module")
def harness(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Path]:
    built = ch.build(tmp_path_factory.mktemp("launcher harness"))
    if built is None:
        pytest.skip("MSVC and CMake are not installed (or have no generator here)")
    return built


def _runtime(local: Path, slot: str, fakeproc: Path, *, python: str = "3.14.8") -> Path:
    folder = local / "QuillVille" / "Runtime" / slot
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "quillville-runtime.json").write_text(
        json.dumps({"python": python, "build": "2026-10-15T00:00:00Z"}), encoding="utf-8"
    )
    ch.fake(fakeproc, folder / "QuillVilleRuntime.exe")
    return folder


def _app(tmp: Path, ini: str | None) -> Path:
    app = tmp / "Quill Radio"
    app.mkdir(parents=True, exist_ok=True)
    if ini is not None:
        (app / "quill-app-version.ini").write_bytes(ini.encode("utf-8"))
    return app


def _probe(harness: dict[str, Path], app: Path, local: Path) -> dict[str, str]:
    env = dict(os.environ, LOCALAPPDATA=str(local))
    done = subprocess.run(
        [str(harness["resolve_probe"]), str(app / "QuillRadio.exe"), BASE_URL],
        capture_output=True,
        text=True,
        env=env,
        timeout=60,
        check=True,
    )
    return dict(line.split("=", 1) for line in done.stdout.splitlines() if "=" in line)


def test_no_slot_means_the_stable_folder(harness: dict[str, Path], tmp_path: Path) -> None:
    local = tmp_path / "local"
    stable = _runtime(local, PYTHON_MAJOR, harness["fakeproc"])
    found = _probe(harness, _app(tmp_path, "[app]\nversion=3.2.0\n"), local)
    assert found["rc"] == "0"
    assert found["slot"] == ""
    assert found["root"] == str(stable)
    assert found["url"] == BASE_URL


def test_a_beta_slot_resolves_the_beta_folder(harness: dict[str, Path], tmp_path: Path) -> None:
    local = tmp_path / "local"
    _runtime(local, PYTHON_MAJOR, harness["fakeproc"])
    beta = _runtime(local, f"{PYTHON_MAJOR}-beta", harness["fakeproc"])
    ini = f"[app]\nversion=3.3.0-beta.1\nchannel=beta\n[runtime]\nslot={PYTHON_MAJOR}-beta\n"
    found = _probe(harness, _app(tmp_path, ini), local)
    assert found["rc"] == "0"
    assert found["slot"] == f"{PYTHON_MAJOR}-beta"
    assert found["python"] == str(beta / "QuillVilleRuntime.exe")


def test_a_missing_beta_runtime_never_falls_back_to_stable(
    harness: dict[str, Path], tmp_path: Path
) -> None:
    """The mix-up slots exist to prevent: Beta code silently on Stable's runtime."""
    local = tmp_path / "local"
    _runtime(local, PYTHON_MAJOR, harness["fakeproc"])
    ini = f"[runtime]\nslot={PYTHON_MAJOR}-beta\n"
    found = _probe(harness, _app(tmp_path, ini), local)
    assert found["rc"] == "-1"
    assert found["python"] == ""
    assert found["slot"] == f"{PYTHON_MAJOR}-beta"
    # ...and it repairs from the Beta tag, never the Stable one.
    assert found["url_rc"] == "0"
    assert found["url"] == BASE_URL.replace("/runtime-3.14/", f"/runtime-{PYTHON_MAJOR}-beta/")


def test_a_dev_slot_does_not_repair_itself(harness: dict[str, Path], tmp_path: Path) -> None:
    local = tmp_path / "local"
    _runtime(local, PYTHON_MAJOR, harness["fakeproc"])
    found = _probe(harness, _app(tmp_path, f"[runtime]\nslot={PYTHON_MAJOR}-dev\n"), local)
    assert found["rc"] == "-1"
    assert found["url_rc"] == "-1"


def test_bom_crlf_and_case_are_read(harness: dict[str, Path], tmp_path: Path) -> None:
    local = tmp_path / "local"
    dev = _runtime(local, f"{PYTHON_MAJOR}-dev", harness["fakeproc"])
    ini = f"\ufeff[app]\r\nchannel=dev\r\n[Runtime]\r\nSlot={PYTHON_MAJOR}-dev\r\n"
    found = _probe(harness, _app(tmp_path, ini), local)
    assert found["rc"] == "0"
    assert found["root"] == str(dev)


@pytest.mark.parametrize(
    "bad", ["..\\..\\Windows", "3.14-stable", "3.14-beta\\..\\3.14", "beta", "3.14-BETA"]
)
def test_a_malformed_slot_is_ignored_not_used_as_a_path(
    harness: dict[str, Path], tmp_path: Path, bad: str
) -> None:
    local = tmp_path / "local"
    stable = _runtime(local, PYTHON_MAJOR, harness["fakeproc"])
    found = _probe(harness, _app(tmp_path, f"[runtime]\nslot={bad}\n"), local)
    assert found["slot"] == ""
    assert found["root"] == str(stable)


def test_a_runtime_for_another_python_is_refused(harness: dict[str, Path], tmp_path: Path) -> None:
    local = tmp_path / "local"
    _runtime(local, f"{PYTHON_MAJOR}-beta", harness["fakeproc"], python="3.13.9")
    found = _probe(harness, _app(tmp_path, f"[runtime]\nslot={PYTHON_MAJOR}-beta\n"), local)
    assert found["rc"] == "-1"


def test_a_private_runtime_still_wins_over_any_slot(
    harness: dict[str, Path], tmp_path: Path
) -> None:
    """A portable copy carries its own interpreter, so it has no slot question."""
    local = tmp_path / "local"
    _runtime(local, f"{PYTHON_MAJOR}-beta", harness["fakeproc"])
    app = _app(tmp_path, f"[runtime]\nslot={PYTHON_MAJOR}-beta\n")
    ch.fake(harness["fakeproc"], app / "python.exe")
    found = _probe(harness, app, local)
    assert found["rc"] == "0"
    assert found["python"] == str(app / "python.exe")
    assert found["data"] == str(app)


@pytest.fixture(scope="module")
def radio_launcher(tmp_path_factory: pytest.TempPathFactory, harness: dict[str, Path]) -> Path:
    """The real QuillRadio.exe, built the way a release builds it."""
    from scripts import build_native_launcher as bnl

    if not ch.may_run_real_programs():
        pytest.skip("runs the built launcher: CI only, or QUILL_RUN_NATIVE_PROGRAMS=1")
    root = tmp_path_factory.mktemp("radio launcher")
    return bnl.build_launcher(bnl.PRODUCTS["radio"], root / "out", build_root=root / "build")


def test_the_built_launcher_starts_the_beta_runtime_only(
    radio_launcher: Path, harness: dict[str, Path], tmp_path: Path
) -> None:
    local = tmp_path / "local"
    stable = _runtime(local, PYTHON_MAJOR, harness["fakeproc"])
    beta = _runtime(local, f"{PYTHON_MAJOR}-beta", harness["fakeproc"])
    app = _app(tmp_path, f"[app]\nchannel=beta\n[runtime]\nslot={PYTHON_MAJOR}-beta\n")
    launcher = app / radio_launcher.name
    launcher.write_bytes(radio_launcher.read_bytes())
    env = dict(os.environ, LOCALAPPDATA=str(local), APPDATA=str(tmp_path / "roaming"))
    done = subprocess.run([str(launcher), "C:\\My Music\\a b.m3u"], env=env, timeout=120)
    assert done.returncode == 0

    started = ch.calls(beta / "QuillVilleRuntime.exe")
    assert len(started) == 1, started
    assert "-m quill.apps.radio" in started[0]
    assert '"C:\\My Music\\a b.m3u"' in started[0]
    assert ch.roots(beta / "QuillVilleRuntime.exe") == [str(beta)]
    assert ch.calls(stable / "QuillVilleRuntime.exe") == []


def test_the_built_launcher_without_a_slot_starts_stable(
    radio_launcher: Path, harness: dict[str, Path], tmp_path: Path
) -> None:
    local = tmp_path / "local"
    stable = _runtime(local, PYTHON_MAJOR, harness["fakeproc"])
    beta = _runtime(local, f"{PYTHON_MAJOR}-beta", harness["fakeproc"])
    app = _app(tmp_path, "[app]\nversion=3.2.0\n")
    launcher = app / radio_launcher.name
    launcher.write_bytes(radio_launcher.read_bytes())
    env = dict(os.environ, LOCALAPPDATA=str(local), APPDATA=str(tmp_path / "roaming"))
    assert subprocess.run([str(launcher)], env=env, timeout=120).returncode == 0
    assert len(ch.calls(stable / "QuillVilleRuntime.exe")) == 1
    assert ch.calls(beta / "QuillVilleRuntime.exe") == []
