"""The update helper, run for real: swap, health check and undo (release channels).

``quill.core.self_update.build_apply_update_script`` writes a batch file that
runs after the app has closed. Until 2026-10-15 its release-channel half -- the
portable folder swap, the two-minute health check and the automatic undo -- had
only ever been read as text, and running it found two bugs the text could not
show: the user's ``data`` folder landed in ``data\\data`` (every portable zip
ships an empty ``data`` folder), and a first update's undo was never reported
because nobody knew the version being replaced.

Every test here writes the real batch, runs it with ``cmd.exe`` against folders
under ``tmp_path``, and plays the app with stand-ins:

* the app is ``pythonw.exe`` running an ``app.py`` that lives in the copy being
  started, so which copy ran is exactly what it logs; a good build writes the
  "I started" marker, a broken one does not;
* an installer, and an app that hangs, are copies of ``fakeproc.exe`` from
  ``tests/unit/native/compiled_harness.py`` (skipped without MSVC).

The health check waits a few seconds instead of two minutes. Windows only.
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

import pytest

from quill.core.self_update import build_apply_update_script
from quill.core.updater import apply
from tests.unit.native import compiled_harness as ch

pytestmark = [
    pytest.mark.skipif(sys.platform != "win32", reason="the helper is a Windows batch file"),
    pytest.mark.timeout(300),
]

PYTHONW = Path(sys.executable).with_name("pythonw.exe")
WAIT = 6  # seconds the health check waits here (two minutes in the field)

_APP = """
import json, pathlib
here = pathlib.Path(__file__).resolve().parent
cfg = json.loads((here / "behaviour.json").read_text(encoding="utf-8"))
with open(cfg["log"], "a", encoding="utf-8") as log:
    log.write(cfg["version"] + "\\n")
if cfg["starts"]:
    pathlib.Path(cfg["marker"]).write_text("started", encoding="utf-8")
"""


class Rig:
    """One app, its updates folder, and the bookkeeping a test asserts on."""

    def __init__(self, tmp: Path) -> None:
        self.tmp = tmp
        self.install = tmp / "Quill Radio"  # a space, as in every real install
        self.updates = tmp / "profile" / "updates"
        self.updates.mkdir(parents=True)
        self.launches = tmp / "launches.txt"
        self.log = self.updates / "apply-update.log"
        self.marker = apply.started_marker(self.updates, "2.0.0")
        self.result = apply.result_path(self.updates)

    def behaviour(self, version: str, *, starts: bool) -> str:
        return json.dumps({
            "version": version,
            "starts": starts,
            "log": str(self.launches),
            "marker": str(self.marker),
        })

    def copy(self, folder: Path, version: str, *, starts: bool, data: bool = True) -> Path:
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "app.py").write_text(_APP, encoding="utf-8")
        (folder / "behaviour.json").write_text(self.behaviour(version, starts=starts), "utf-8")
        if data:  # every portable zip ships this folder: it marks the copy portable
            (folder / "data").mkdir(exist_ok=True)
            (folder / "data" / "README.txt").write_text(f"shipped with {version}", "utf-8")
        return folder

    def user_data(self) -> None:
        (self.install / "data" / "favorites.json").write_text('["WQXR"]', encoding="utf-8")

    def script(self, **kwargs: object) -> str:
        base: dict[str, object] = {
            "pid": _gone_pid(),
            "install_dir": self.install,
            "exe_path": PYTHONW,
            "relaunch_args": [str(self.install / "app.py")],
            "log_path": self.log,
            "health_marker": self.marker,
            "result_file": self.result,
            "from_version": "1.0.0",
            "to_version": "2.0.0",
            "health_wait_seconds": WAIT,
        }
        base.update(kwargs)
        return build_apply_update_script(**base)  # type: ignore[arg-type]

    def run(self, script: str, *, expect_launches: int) -> list[str]:
        helper = self.tmp / "helper"
        helper.mkdir(exist_ok=True)
        bat = helper / "apply-update.bat"
        bat.write_text(script, encoding="utf-8")
        subprocess.run(
            ["cmd.exe", "/c", str(bat)],
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            timeout=WAIT + 120,
            check=False,
        )
        return self.wait_for_launches(expect_launches)

    def wait_for_launches(self, count: int) -> list[str]:
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            seen = self.launched()
            if len(seen) >= count:
                time.sleep(0.5)  # anything late would be a launch too many
                return self.launched()
            time.sleep(0.2)
        return self.launched()

    def launched(self) -> list[str]:
        try:
            return self.launches.read_text(encoding="utf-8").split()
        except OSError:
            return []

    def helper_log(self) -> str:
        return self.log.read_text(encoding="utf-8", errors="replace")

    def result_data(self) -> dict[str, object]:
        return json.loads(self.result.read_text(encoding="utf-8"))


def _gone_pid() -> int:
    """The PID of a process that has already exited: the helper's wait falls through."""
    proc = subprocess.Popen([str(PYTHONW), "-c", "pass"])
    proc.wait(timeout=30)
    return proc.pid


@pytest.fixture
def rig(tmp_path: Path) -> Rig:
    if not PYTHONW.is_file():
        pytest.skip("no pythonw.exe beside this interpreter")
    return Rig(tmp_path)


# -- portable copies ------------------------------------------------------------------


def _portable(rig: Rig, *, new_starts: bool) -> tuple[str, Path]:
    rig.copy(rig.install, "1.0.0", starts=True)
    rig.user_data()
    staged = rig.copy(rig.updates / "staging" / "Quill Radio", "2.0.0", starts=new_starts)
    return rig.script(mode="portable", source_dir=staged, swap=True), staged


def test_a_good_portable_update_swaps_folders_and_keeps_your_data(rig: Rig) -> None:
    script, _staged = _portable(rig, new_starts=True)
    assert rig.run(script, expect_launches=1) == ["2.0.0"]

    assert json.loads((rig.install / "behaviour.json").read_text("utf-8"))["version"] == "2.0.0"
    # The user's data, where the app looks for it -- never data\data.
    assert (rig.install / "data" / "favorites.json").read_text("utf-8") == '["WQXR"]'
    assert not (rig.install / "data" / "data").exists()
    # The old copy is kept, without the data, for an undo.
    previous = Path(f"{rig.install}.previous")
    assert json.loads((previous / "behaviour.json").read_text("utf-8"))["version"] == "1.0.0"
    assert not (previous / "data").exists()
    assert not Path(f"{rig.install}.new").exists()
    assert not (rig.updates / "staging").exists()
    assert not rig.result.exists()
    assert "2.0.0 started" in rig.helper_log()


def test_a_portable_update_that_does_not_start_is_undone(rig: Rig) -> None:
    script, _staged = _portable(rig, new_starts=False)
    assert rig.run(script, expect_launches=2) == ["2.0.0", "1.0.0"]

    assert json.loads((rig.install / "behaviour.json").read_text("utf-8"))["version"] == "1.0.0"
    assert (rig.install / "data" / "favorites.json").read_text("utf-8") == '["WQXR"]'
    assert not (rig.install / "data" / "data").exists()
    for leftover in (".previous", ".failed", ".new"):
        assert not Path(f"{rig.install}{leftover}").exists(), leftover
    assert rig.result_data() == {
        "version": "1.0.0",
        "rolled_back": True,
        "failed_version": "2.0.0",
    }
    # ...and the old version, starting again, says so once.
    report = apply.confirm_started(
        rig.updates,
        app_key="radio",
        app_name="Quill Radio",
        version="1.0.0",
        history_path=rig.tmp / "history.jsonl",
    )
    assert report.rolled_back_from == "2.0.0"
    assert report.notice.startswith("The update to 2.0.0 didn't start, so Quill Radio went back")


def test_a_copy_without_a_data_folder_keeps_the_new_one(rig: Rig) -> None:
    """The data folder is what marks a copy portable; never leave it without one."""
    rig.copy(rig.install, "1.0.0", starts=True, data=False)
    staged = rig.copy(rig.updates / "staging" / "Quill Radio", "2.0.0", starts=True)
    script = rig.script(mode="portable", source_dir=staged, swap=True)
    assert rig.run(script, expect_launches=1) == ["2.0.0"]
    assert (rig.install / "data" / "README.txt").read_text("utf-8") == "shipped with 2.0.0"


def test_a_file_held_open_falls_back_to_copying_in_place(rig: Rig) -> None:
    """A folder cannot be renamed while a file in it is open; the swap is undone
    step by step and the old robocopy runs instead, data excluded."""
    script, staged = _portable(rig, new_starts=True)
    (rig.install / "locked.bin").write_bytes(b"old")
    (staged / "locked.bin").write_bytes(b"new")
    with open(rig.install / "locked.bin", "rb"):
        assert rig.run(script, expect_launches=1) == ["2.0.0"]
    assert json.loads((rig.install / "behaviour.json").read_text("utf-8"))["version"] == "2.0.0"
    assert (rig.install / "data" / "favorites.json").read_text("utf-8") == '["WQXR"]'
    assert (rig.install / "data" / "README.txt").read_text("utf-8") == "shipped with 1.0.0"
    assert not Path(f"{rig.install}.previous").exists()
    assert not Path(f"{rig.install}.new").exists()
    assert "copying in place instead" in rig.helper_log()


def test_the_helper_waits_for_the_app_to_close_first(rig: Rig) -> None:
    script, _staged = _portable(rig, new_starts=True)
    app = subprocess.Popen([str(PYTHONW), "-c", "import time; time.sleep(4)"])
    script = script.replace(f"PID eq {_pid_in(script)}", f"PID eq {app.pid}").replace(
        f'" {_pid_in(script)} "', f'" {app.pid} "'
    )
    started = time.monotonic()
    assert rig.run(script, expect_launches=1) == ["2.0.0"]
    assert app.poll() is not None
    assert time.monotonic() - started >= 3


def _pid_in(script: str) -> str:
    line = next(text for text in script.splitlines() if "PID eq" in text)
    return line.split("PID eq ", 1)[1].split('"', 1)[0]


# -- stand-in programs (compiled) -----------------------------------------------------


@pytest.fixture(scope="module")
def fakeproc(tmp_path_factory: pytest.TempPathFactory) -> Path:
    if sys.platform != "win32":
        pytest.skip("Windows only")
    built = ch.build(tmp_path_factory.mktemp("helper harness"))
    if built is None:
        pytest.skip("MSVC and CMake are not installed (or have no generator here)")
    return built["fakeproc"]


def test_an_app_that_hangs_is_stopped_and_the_update_undone(rig: Rig, fakeproc: Path) -> None:
    """The new version runs but never says it started. Its folder cannot be
    renamed while it runs, so the helper stops what runs from that folder --
    and nothing else -- and then goes back."""
    rig.copy(rig.install, "1.0.0", starts=True)
    rig.user_data()
    ch.fake(fakeproc, rig.install / "QuillRadio.exe")
    staged = rig.copy(rig.updates / "staging" / "Quill Radio", "2.0.0", starts=False)
    ch.fake(fakeproc, staged / "QuillRadio.exe", sleep=240)
    bystander = ch.fake(fakeproc, rig.tmp / "elsewhere" / "QuillRadio.exe", sleep=30)
    other = subprocess.Popen([str(bystander)])
    try:
        script = rig.script(
            mode="portable",
            source_dir=staged,
            swap=True,
            exe_path=rig.install / "QuillRadio.exe",
            relaunch_args=[],
        )
        rig.run(script, expect_launches=0)
        old_exe = rig.install / "QuillRadio.exe"
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline and not ch.calls(old_exe):
            time.sleep(0.2)
        assert len(ch.calls(old_exe)) == 1, rig.helper_log()
        assert not Path(f"{old_exe}.sleep").exists()  # it is the old copy that ran
        assert (rig.install / "data" / "favorites.json").read_text("utf-8") == '["WQXR"]'
        assert rig.result_data()["rolled_back"] is True
        assert not Path(f"{rig.install}.failed").exists()
        assert other.poll() is None, "a program outside the app's folder was stopped"
    finally:
        other.kill()


def _installed(
    rig: Rig, fakeproc: Path, *, new_exit: int = 0, new_starts: bool = False, old_exit: int = 0
) -> tuple[str, Path, Path]:
    rig.copy(rig.install, "1.0.0", starts=True, data=False)
    good = rig.tmp / "payload-1.json"
    good.write_text(rig.behaviour("1.0.0", starts=True), encoding="utf-8")
    new = rig.tmp / "payload-2.json"
    new.write_text(rig.behaviour("2.0.0", starts=new_starts), encoding="utf-8")
    target = rig.install / "behaviour.json"
    setup = ch.fake(
        fakeproc,
        rig.updates / "Quill-Radio-Setup-Shared-2.0.0.exe",
        exit=new_exit,
        **({} if new_exit else {"copy": (new, target)}),
    )
    kept = ch.fake(
        fakeproc,
        rig.updates / "rollback" / "Quill-Radio-Setup-Shared-1.0.0.exe",
        exit=old_exit,
        **({} if old_exit else {"copy": (good, target)}),
    )
    script = rig.script(
        mode="installer",
        setup_exe=setup,
        channel="beta",
        setup_log=rig.updates / "setup-2.0.0.log",
        rollback_setup=kept,
    )
    return script, setup, kept


def test_an_installed_update_that_does_not_start_reinstalls_the_kept_version(
    rig: Rig, fakeproc: Path
) -> None:
    script, setup, kept = _installed(rig, fakeproc)
    assert rig.run(script, expect_launches=2) == ["2.0.0", "1.0.0"]

    forward = ch.calls(setup)
    assert len(forward) == 1
    assert "/VERYSILENT" in forward[0] and "/CHANNEL=beta" in forward[0]
    # The log path reaches the installer as one quoted argument, spaces and all.
    assert f'/LOG="{rig.updates / "setup-2.0.0.log"}"' in forward[0]
    back = ch.calls(kept)
    assert len(back) == 1 and "/CHANNEL=beta" in back[0] and "/VERYSILENT" in back[0]
    assert json.loads((rig.install / "behaviour.json").read_text("utf-8"))["version"] == "1.0.0"
    assert rig.result_data()["rolled_back"] is True


def test_a_good_installed_update_is_left_alone(rig: Rig, fakeproc: Path) -> None:
    script, setup, kept = _installed(rig, fakeproc, new_starts=True)
    assert rig.run(script, expect_launches=1) == ["2.0.0"]
    assert len(ch.calls(setup)) == 1
    assert ch.calls(kept) == []
    assert not rig.result.exists()


def test_an_installer_that_fails_restarts_the_old_version_at_once(rig: Rig, fakeproc: Path) -> None:
    """Nothing was installed, so there is nothing to health-check or undo."""
    script, setup, kept = _installed(rig, fakeproc, new_exit=5)
    started = time.monotonic()
    assert rig.run(script, expect_launches=1) == ["1.0.0"]
    assert time.monotonic() - started < WAIT + 20
    assert len(ch.calls(setup)) == 1
    assert ch.calls(kept) == []
    assert rig.result_data() == {
        "version": "1.0.0",
        "install_failed": True,
        "failed_version": "2.0.0",
    }
    assert "exit code 5" in rig.helper_log()


def test_an_undo_that_fails_never_claims_it_went_back(rig: Rig, fakeproc: Path) -> None:
    script, _setup, kept = _installed(rig, fakeproc, old_exit=3)
    assert rig.run(script, expect_launches=1) == ["2.0.0"]
    assert len(ch.calls(kept)) == 1
    assert not rig.result.exists()
    assert "could not go back" in rig.helper_log()
