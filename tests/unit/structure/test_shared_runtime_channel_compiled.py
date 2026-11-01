"""``/CHANNEL=`` in the shared-runtime installer, compiled by Inno Setup and run.

``installer/shared-runtime.iss`` decides which runtime slot an install lands in:
``/CHANNEL=stable|beta|dev`` when the updater passes it, else Stable for a final
version and Beta for any pre-release. Until 2026-10-15 that Pascal had only ever
been read as text. Here a tiny setup includes the real fragment, its
``InitializeSetup`` writes what ``InstallChannel``, ``RuntimeSlot`` and
``RuntimeDir`` answer to a file and returns False -- so Inno's own Pascal runs
with the real command line, and nothing is ever installed -- and every answer
is compared with the Python mirror (``quill.core.updater.runtime_slots``).

Skipped where Inno Setup 7 is not installed, and -- because it runs a setup
program, even one told to install nothing -- outside CI unless
``QUILL_RUN_NATIVE_PROGRAMS=1`` asks for it.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

from quill.core.updater.runtime_slots import PYTHON_MAJOR, default_channel, slot_for

REPO = Path(__file__).resolve().parents[3]
FRAGMENT = REPO / "installer" / "shared-runtime.iss"

pytestmark = pytest.mark.timeout(600)

_PROBE = """
#define RuntimeVersion "{runtime}"
#define RuntimeSourceDir "{payload}"
#define AppRefId "probe"

[Setup]
AppId=QuillChannelProbe
AppName=Quill channel probe
AppVersion={{#AppVersion}}
DefaultDirName={{localappdata}}\\QuillChannelProbe
PrivilegesRequired=lowest
Compression=none
OutputDir={out}
OutputBaseFilename=probe-{name}
Uninstallable=no

[Types]
Name: "full"; Description: "Full"

[Components]
Name: "runtime"; Description: "Runtime"; Types: full; Flags: fixed

#include "{fragment}"

[Code]
function InitializeSetup(): Boolean;
begin
  SaveStringToFile(ExpandConstant('{{param:PROBE|}}'),
    InstallChannel('') + '|' + RuntimeSlot('') + '|' + RuntimeDir('') + '|' + RuntimeExe(''),
    False);
  Result := False;
end;
"""


def _iscc() -> Path | None:
    if os.name != "nt":
        return None
    from scripts.build_windows_distribution import find_inno_setup_compiler

    return find_inno_setup_compiler()


@pytest.fixture(scope="module")
def setups(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Path]:
    from tests.unit.native.compiled_harness import may_run_real_programs

    if not may_run_real_programs():
        pytest.skip("runs a compiled setup: CI only, or QUILL_RUN_NATIVE_PROGRAMS=1")
    iscc = _iscc()
    if iscc is None:
        pytest.skip("Inno Setup 7 is not installed")
    root = tmp_path_factory.mktemp("channel probe")
    payload = root / "payload"
    payload.mkdir()
    (payload / "quillville-runtime.json").write_text(
        json.dumps({"python": f"{PYTHON_MAJOR}.8", "build": "2026-10-15T00:00:00Z"}),
        encoding="utf-8",
    )
    (payload / "QuillVilleRuntime.exe").write_bytes(b"not a program")
    # The two AI engines are named one by one with no skipifsourcedoesntexist
    # (installer/shared-runtime.iss: neither may ship without its licence), so
    # the probe payload carries a stand-in for each named file.
    for engine, names in {
        "copilot": (
            "copilot.exe",
            "copilot-runtime.exe",
            "runtime.node",
            ".hostless-runtime-assets-v2",
            "COPILOT-CLI-LICENSE.txt",
        ),
        "codex": ("codex-app-server.exe", "CODEX-LICENSE.txt", "CODEX-NOTICE.txt"),
    }.items():
        folder = payload / "tools" / engine
        folder.mkdir(parents=True)
        for file_name in names:
            (folder / file_name).write_bytes(b"stand-in")
    # The rest of the Copilot bundle rides one recursive wildcard that
    # excludes the five named files, and ISCC refuses a wildcard that matches
    # nothing, so one runtime asset stands in for that rest.
    (payload / "tools" / "copilot" / "assets").mkdir()
    (payload / "tools" / "copilot" / "assets" / "stand-in.txt").write_bytes(b"stand-in")
    built: dict[str, Path] = {}
    for name, version in {
        "final": "3.2.0",
        "beta": "3.3.0-beta.1",
        "rc": "3.3.0-rc.2",
        "dev": "3.4.0-dev.20261015.1",
    }.items():
        script = root / f"probe-{name}.iss"
        script.write_text(
            _PROBE.format(
                runtime=f"{PYTHON_MAJOR}.8",
                payload=payload,
                out=root / "out",
                name=name,
                fragment=FRAGMENT,
            ),
            encoding="utf-8",
        )
        done = subprocess.run(
            [str(iscc), "/Q", f"/DAppVersion={version}", str(script)],
            capture_output=True,
            text=True,
            timeout=300,
        )
        assert done.returncode == 0, done.stdout[-4000:] + done.stderr[-4000:]
        built[version] = root / "out" / f"probe-{name}.exe"
    return built


def _ask(setup: Path, tmp: Path, *args: str) -> list[str]:
    answer = tmp / "answer.txt"
    answer.unlink(missing_ok=True)
    subprocess.run(
        [str(setup), "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART", f"/PROBE={answer}", *args],
        timeout=120,
        check=False,
    )
    return answer.read_text(encoding="utf-8").split("|")


CASES = [
    # (version, /CHANNEL= or None)
    ("3.2.0", None),
    ("3.2.0", "stable"),
    ("3.2.0", "beta"),
    ("3.2.0", "dev"),
    ("3.2.0", "BETA"),
    ("3.2.0", "nightly"),
    ("3.3.0-beta.1", None),
    ("3.3.0-beta.1", "stable"),
    ("3.3.0-beta.1", "nightly"),
    ("3.3.0-rc.2", None),
    ("3.4.0-dev.20261015.1", None),
    ("3.4.0-dev.20261015.1", "beta"),
]


@pytest.mark.parametrize(("version", "requested"), CASES)
def test_the_installer_and_its_python_mirror_agree(
    setups: dict[str, Path], tmp_path: Path, version: str, requested: str | None
) -> None:
    args = [] if requested is None else [f"/CHANNEL={requested}"]
    channel, slot, runtime_dir, runtime_exe = _ask(setups[version], tmp_path, *args)

    expected = default_channel(version, requested or "")
    assert channel == expected
    assert slot == slot_for(expected)
    local = Path(os.environ["LOCALAPPDATA"])
    assert Path(runtime_dir) == local / "QuillVille" / "Runtime" / slot
    assert Path(runtime_exe) == Path(runtime_dir) / "QuillVilleRuntime.exe"


def test_a_stable_install_keeps_the_folder_that_always_existed(
    setups: dict[str, Path], tmp_path: Path
) -> None:
    _channel, slot, _dir, _exe = _ask(setups["3.2.0"], tmp_path, "/CHANNEL=stable")
    assert slot == PYTHON_MAJOR
