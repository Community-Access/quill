# One-Click Update (Apply and Restart) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a one-click "Install and restart now" that downloads (existing), applies, and relaunches the app, for both portable and installed Windows builds across **every Quill app**: Quill Radio, Quill Cast, QUILL, and Audio Studio.

**Architecture:** A new wx-free `quill/core/self_update.py` owns applying an already-downloaded update: stage a portable zip, build a Windows helper `.bat` (pure text), and launch it detached. The helper waits for the app's PID to exit, then either robocopies staged files over the install dir (excluding `data`) or runs the setup elevated-and-silent, then relaunches the exe and cleans up. This core is app-agnostic. The UI seams call `begin_self_update()`: `app_shell.py` (covers Radio + Cast, both subclass `AppShellFrame`) and `main_frame_updates.py` (QUILL). Audio Studio lives in its own repo (`S:\QUILL-AS`) that vendors quill as `quillas` and whose `StudioAppFrame` also subclasses `AppShellFrame`, so it gets the identical one-click apply via its own copy of these files (`quillas/core/self_update.py`, `quillas/ui/update_apply.py`, and the same `quillas/ui/app_shell.py` edit).

**Tech Stack:** Python 3.13, wxPython (UI only), Windows `cmd.exe`/`robocopy`/`powershell`, existing `quill.core.updates` + `quill.core.safe_archive`.

## Global Constraints

- `quill/core` is wx-free and strict-typed; always in `mypy` scope. No `wx` imports in `self_update.py`.
- GATE-EC: every new top-level exception in `quill/core` must inherit `CodedError` (`quill.core.error_codes`) with a unique `code = "QUILL-<DOMAIN>-<SUBSYSTEM>-<REASON>"`. Shape is `class X(CodedError):`, never `class X(Exception, CodedError):`.
- Platform: Windows primary (this feature is Windows-only); macOS/dev runs must fall through to today's download-and-reveal, never crash. No Linux promises.
- All JSON/atomic-write and safe-archive conventions already in the repo apply. Reuse `quill.core.updates.extract_portable_update` (zip-slip + bomb guarded) — do not write a second extractor.
- Downloads are already HTTPS + trusted-host verified; do not relax that. This feature only acts on an already-downloaded, verified asset.
- Line endings: repo `S:\QUILL` is `core.autocrlf=false` — keep new files LF; if an edit flips a file to CRLF, convert back to LF (never with a truncating `open('wb')...read()` one-liner).
- Run `ruff check` and scoped `mypy quill\core` after core changes; `pytest -q` for touched tests.
- Do not commit unless the user asks (user global rule overrides the skill's per-task commit step — perform the `git add`/`commit` steps only if the user has said to commit; otherwise stop at "tests pass").

---

## File Structure

- Create: `quill/core/self_update.py` — apply-an-update engine (wx-free): `SelfUpdateError`, `install_root_and_exe()`, `stage_portable_update()`, `build_apply_update_script()`, `write_and_launch_helper()`, `begin_self_update()`.
- Create: `tests/unit/core/test_self_update.py` — pure + temp-dir tests, plus a Windows-guarded end-to-end batch run.
- Modify: `quill/ui/app_shell.py` — rewire `_offer_app_update_install` to a one-click apply (Radio + Cast).
- Create: `tests/unit/ui/test_app_shell_self_update.py` — UI-seam unit tests with fakes.
- Modify: `quill/ui/main_frame_updates.py` — same apply behavior for QUILL Windows in `_offer_post_download_actions`.
- Create/Modify in `S:\QUILL-AS` (vendored `quillas`): `quillas/core/self_update.py` + `quillas/ui/update_apply.py` (copies of the quill files with `quill.*`→`quillas.*` imports) and the same one-click edit to `quillas/ui/app_shell.py`. Add `tests/unit/core/test_self_update.py` + `tests/unit/ui/test_app_shell_self_update.py` (ported with quillas imports).
- Modify: `S:\quill-radio\docs\release-notes-2.0.md` and `S:\quill-radio\CHANGELOG.md` — a 2.0.3 bullet for one-click update. Add matching notes to `S:\quill-cast\CHANGELOG.md` and `S:\QUILL-AS\CHANGELOG.md`.

---

## Task 1: `build_apply_update_script()` — the pure helper-script generator

**Files:**
- Create: `quill/core/self_update.py`
- Test: `tests/unit/core/test_self_update.py`

**Interfaces:**
- Produces: `SelfUpdateError(CodedError)` with `code = "QUILL-UPDATE-SELF-APPLY"`; `build_apply_update_script(*, pid: int, mode: str, install_dir: Path, exe_path: Path, log_path: Path, source_dir: Path | None = None, setup_exe: Path | None = None, data_dirname: str = "data") -> str` where `mode` is `"portable"` or `"installer"`.

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/core/test_self_update.py
from __future__ import annotations

from pathlib import Path

import pytest

from quill.core.self_update import SelfUpdateError, build_apply_update_script


def _portable_script() -> str:
    return build_apply_update_script(
        pid=4242,
        mode="portable",
        install_dir=Path(r"C:\Apps\QuillRadio"),
        exe_path=Path(r"C:\Apps\QuillRadio\QuillRadio.exe"),
        log_path=Path(r"C:\Users\me\AppData\Roaming\Quill\updates\apply-update.log"),
        source_dir=Path(r"C:\Users\me\AppData\Roaming\Quill\updates\staging\app"),
    )


def test_portable_script_waits_for_pid_then_copies_excluding_data_then_relaunches() -> None:
    script = _portable_script()
    # Waits for our PID to exit before touching anything.
    assert "4242" in script
    assert "tasklist" in script.lower() or "pid eq 4242" in script.lower()
    # Robocopy mirrors staged files into the install dir, excluding the data dir.
    assert "robocopy" in script.lower()
    assert r'"C:\Apps\QuillRadio\data"' in script  # excluded via /XD
    assert "/xd" in script.lower()
    # Relaunch the (new) exe.
    assert r'"C:\Apps\QuillRadio\QuillRadio.exe"' in script
    # Everything logged.
    assert "apply-update.log" in script


def test_installer_script_runs_setup_elevated_and_silent_then_relaunches() -> None:
    script = build_apply_update_script(
        pid=99,
        mode="installer",
        install_dir=Path(r"C:\Program Files\Quill Radio"),
        exe_path=Path(r"C:\Program Files\Quill Radio\QuillRadio.exe"),
        log_path=Path(r"C:\Users\me\AppData\Roaming\Quill\updates\apply-update.log"),
        setup_exe=Path(r"C:\Users\me\AppData\Roaming\Quill\updates\Setup-2.0.3.exe"),
    )
    assert "Start-Process" in script  # powershell elevation
    assert "RunAs" in script
    assert "/VERYSILENT" in script
    assert "Setup-2.0.3.exe" in script
    assert r'"C:\Program Files\Quill Radio\QuillRadio.exe"' in script


def test_portable_mode_requires_source_dir() -> None:
    with pytest.raises(SelfUpdateError):
        build_apply_update_script(
            pid=1, mode="portable",
            install_dir=Path(r"C:\a"), exe_path=Path(r"C:\a\x.exe"),
            log_path=Path(r"C:\a\l.log"), source_dir=None,
        )


def test_installer_mode_requires_setup_exe() -> None:
    with pytest.raises(SelfUpdateError):
        build_apply_update_script(
            pid=1, mode="installer",
            install_dir=Path(r"C:\a"), exe_path=Path(r"C:\a\x.exe"),
            log_path=Path(r"C:\a\l.log"), setup_exe=None,
        )
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/core/test_self_update.py -q`
Expected: FAIL with `ModuleNotFoundError: quill.core.self_update`.

- [ ] **Step 3: Write minimal implementation**

```python
# quill/core/self_update.py
"""Apply an already-downloaded Quill update and relaunch, on Windows.

A running .exe cannot overwrite itself, so applying a portable update means
handing the swap to a tiny external helper that runs after this process exits.
This module builds that helper (a pure, unit-tested batch script), stages the
downloaded zip, and launches the helper detached. The two UI update flows
(``quill.ui.app_shell`` for the standalone apps, ``quill.ui.main_frame_updates``
for QUILL) call :func:`begin_self_update` from their post-download dialog and
then close the window; the helper waits for this PID to exit before touching a
single file. wx-free, strict-typed.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from quill.core.error_codes import CodedError

#: How long the helper waits for the app to exit before proceeding anyway. The
#: app is expected to exit within a second or two of launching the helper; the
#: ceiling only prevents a wedged process from stranding the helper forever.
_PID_WAIT_SECONDS = 60


class SelfUpdateError(CodedError):
    """A downloaded update could not be staged or applied."""

    code = "QUILL-UPDATE-SELF-APPLY"


def build_apply_update_script(
    *,
    pid: int,
    mode: str,
    install_dir: Path,
    exe_path: Path,
    log_path: Path,
    source_dir: Path | None = None,
    setup_exe: Path | None = None,
    data_dirname: str = "data",
) -> str:
    """The Windows ``.bat`` that applies an update after this process exits (pure).

    ``mode="portable"``: robocopy ``source_dir`` over ``install_dir`` excluding
    the ``data_dirname`` folder (favorites/recordings/settings survive), then
    relaunch ``exe_path``. ``mode="installer"``: run ``setup_exe`` elevated and
    silent, then relaunch. Both wait for ``pid`` to exit first and tee every
    step to ``log_path``.
    """
    if mode == "portable" and source_dir is None:
        raise SelfUpdateError("Portable apply needs a staged source directory.")
    if mode == "installer" and setup_exe is None:
        raise SelfUpdateError("Installer apply needs the setup executable.")

    data_dir = install_dir / data_dirname
    log = str(log_path)
    lines = [
        "@echo off",
        "setlocal",
        f'set "LOG={log}"',
        f'echo [apply] start pid={pid} mode={mode} >>"%LOG%" 2>&1',
        # Wait for the app process to exit (up to the ceiling), then proceed.
        f"set /a WAITED=0",
        ":waitloop",
        f'tasklist /FI "PID eq {pid}" 2>NUL | find " {pid} " >NUL',
        "if errorlevel 1 goto :exited",
        "ping -n 2 127.0.0.1 >NUL",
        "set /a WAITED+=1",
        f"if %WAITED% LSS {_PID_WAIT_SECONDS} goto :waitloop",
        ":exited",
        f'echo [apply] app exited (waited %WAITED%s) >>"%LOG%" 2>&1',
    ]
    if mode == "portable":
        lines += [
            f'echo [apply] robocopy "{source_dir}" -> "{install_dir}" (xd data) >>"%LOG%" 2>&1',
            f'robocopy "{source_dir}" "{install_dir}" /MIR /XD "{data_dir}" '
            f'/R:2 /W:1 /NP >>"%LOG%" 2>&1',
            f'echo [apply] robocopy exit %ERRORLEVEL% >>"%LOG%" 2>&1',
        ]
    else:
        lines += [
            f'echo [apply] running installer "{setup_exe}" >>"%LOG%" 2>&1',
            "powershell -NoProfile -Command "
            f'"Start-Process -FilePath \'{setup_exe}\' '
            "-ArgumentList '/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART' "
            f'-Verb RunAs -Wait" >>"%LOG%" 2>&1',
            f'echo [apply] installer done %ERRORLEVEL% >>"%LOG%" 2>&1',
        ]
    lines += [
        f'echo [apply] relaunching "{exe_path}" >>"%LOG%" 2>&1',
        f'start "" "{exe_path}"',
        # Best-effort cleanup: remove the staged tree and this script.
    ]
    if mode == "portable" and source_dir is not None:
        # Delete the staging *parent* (…/staging) so a re-run starts clean.
        lines.append(f'rmdir /S /Q "{source_dir.parent}" >>"%LOG%" 2>&1')
    lines += [
        f'echo [apply] done >>"%LOG%" 2>&1',
        '(goto) 2>nul & del "%~f0"',  # delete the running batch on exit
    ]
    return "\r\n".join(lines) + "\r\n"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/unit/core/test_self_update.py -q`
Expected: PASS (4 tests).

- [ ] **Step 5: Lint + typecheck**

Run: `ruff check quill/core/self_update.py && mypy quill\core\self_update.py`
Expected: clean (mypy prints the usual unused-section note, then `Success`).

- [ ] **Step 6: Commit** (only if the user asked to commit)

```bash
git add quill/core/self_update.py tests/unit/core/test_self_update.py
git commit -m "feat(update): pure apply-update helper-script generator (portable + installer)"
```

---

## Task 2: `install_root_and_exe()` and `stage_portable_update()`

**Files:**
- Modify: `quill/core/self_update.py`
- Test: `tests/unit/core/test_self_update.py`

**Interfaces:**
- Consumes: `quill.core.updates.extract_portable_update`.
- Produces: `install_root_and_exe() -> tuple[Path, Path] | None` (install dir, exe path; `None` when not a frozen build); `stage_portable_update(zip_path: Path, staging_root: Path, *, exe_name: str) -> Path` returns the directory that actually contains `exe_name`.

- [ ] **Step 1: Write the failing test**

```python
# add to tests/unit/core/test_self_update.py
import zipfile

from quill.core.self_update import install_root_and_exe, stage_portable_update


def _make_zip(path: Path, arcnames: list[str]) -> None:
    with zipfile.ZipFile(path, "w") as zf:
        for name in arcnames:
            zf.writestr(name, b"x")


def test_stage_flat_layout_returns_root_with_exe(tmp_path: Path) -> None:
    zip_path = tmp_path / "portable.zip"
    _make_zip(zip_path, ["QuillRadio.exe", "tools/ffmpeg/ffmpeg.exe"])
    staging = tmp_path / "staging"
    root = stage_portable_update(zip_path, staging, exe_name="QuillRadio.exe")
    assert (root / "QuillRadio.exe").is_file()


def test_stage_descends_single_wrapping_folder(tmp_path: Path) -> None:
    zip_path = tmp_path / "portable.zip"
    _make_zip(zip_path, ["QuillRadio-2.0.3/QuillRadio.exe", "QuillRadio-2.0.3/docs/readme.txt"])
    staging = tmp_path / "staging"
    root = stage_portable_update(zip_path, staging, exe_name="QuillRadio.exe")
    assert root.name == "QuillRadio-2.0.3"
    assert (root / "QuillRadio.exe").is_file()


def test_stage_rejects_zip_without_exe(tmp_path: Path) -> None:
    zip_path = tmp_path / "portable.zip"
    _make_zip(zip_path, ["readme.txt"])
    with pytest.raises(SelfUpdateError):
        stage_portable_update(zip_path, tmp_path / "staging", exe_name="QuillRadio.exe")


def test_install_root_and_exe_is_none_in_dev_run() -> None:
    # Not a frozen build under pytest, so there is nothing to apply into.
    assert install_root_and_exe() is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/core/test_self_update.py -q`
Expected: FAIL with `ImportError: cannot import name 'stage_portable_update'`.

- [ ] **Step 3: Write minimal implementation**

```python
# add to quill/core/self_update.py

def install_root_and_exe() -> tuple[Path, Path] | None:
    """The frozen exe and its install directory, or ``None`` in a dev run.

    ``sys.frozen`` is set only in a PyInstaller build; ``sys.executable`` is
    then the app exe (QuillRadio.exe / QUILLCast.exe / quill.exe). A dev run
    (``python -m quill``) returns ``None`` so callers fall back to reveal.
    """
    if not getattr(sys, "frozen", False):
        return None
    exe = Path(sys.executable).resolve()
    return exe.parent, exe


def stage_portable_update(zip_path: Path, staging_root: Path, *, exe_name: str) -> Path:
    """Extract a portable update zip and return the dir that holds ``exe_name``.

    Extracts into ``staging_root`` (cleared first) using the zip-slip- and
    bomb-guarded :func:`quill.core.updates.extract_portable_update`. If the zip
    wraps everything in a single top-level folder, descends into it. Raises
    :class:`SelfUpdateError` if no ``exe_name`` is found -- so a wrong/corrupt
    asset never drives a swap that would break the install.
    """
    import shutil

    from quill.core.updates import extract_portable_update

    if staging_root.exists():
        shutil.rmtree(staging_root, ignore_errors=True)
    staging_root.mkdir(parents=True, exist_ok=True)
    try:
        extract_portable_update(zip_path, staging_root)
    except Exception as exc:  # noqa: BLE001 - surface as a coded error
        raise SelfUpdateError(f"Could not extract the update: {exc}") from exc
    if (staging_root / exe_name).is_file():
        return staging_root
    entries = [p for p in staging_root.iterdir()]
    if len(entries) == 1 and entries[0].is_dir() and (entries[0] / exe_name).is_file():
        return entries[0]
    raise SelfUpdateError(
        f"The downloaded update does not contain {exe_name}; not applying it."
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/unit/core/test_self_update.py -q`
Expected: PASS (all Task 1 + Task 2 tests).

- [ ] **Step 5: Lint + typecheck**

Run: `ruff check quill/core/self_update.py && mypy quill\core\self_update.py`
Expected: clean.

- [ ] **Step 6: Commit** (only if the user asked to commit)

```bash
git add quill/core/self_update.py tests/unit/core/test_self_update.py
git commit -m "feat(update): stage portable update zip and locate install root/exe"
```

---

## Task 3: `write_and_launch_helper()` and `begin_self_update()` orchestration

**Files:**
- Modify: `quill/core/self_update.py`
- Test: `tests/unit/core/test_self_update.py`

**Interfaces:**
- Consumes: Task 1 `build_apply_update_script`, Task 2 `install_root_and_exe`/`stage_portable_update`.
- Produces:
  - `write_and_launch_helper(script_text: str, helper_dir: Path) -> Path` — writes `apply-update.bat` and launches it detached; returns its path.
  - `begin_self_update(*, download_path: Path, portable: bool, app_data_dir: Path, pid: int | None = None) -> None` — the single entry point the UI calls. Determines mode, stages if portable, builds the script, launches the helper. Raises `SelfUpdateError` on any failure (UI announces and stays open). Caller closes the window on success.

- [ ] **Step 1: Write the failing test**

```python
# add to tests/unit/core/test_self_update.py
import quill.core.self_update as su


def test_begin_self_update_portable_stages_and_launches(tmp_path, monkeypatch):
    # Fake a frozen install with an exe.
    install = tmp_path / "install"
    (install / "data").mkdir(parents=True)
    (install / "QuillRadio.exe").write_bytes(b"old")
    monkeypatch.setattr(su, "install_root_and_exe", lambda: (install, install / "QuillRadio.exe"))

    # A portable zip with the new exe.
    zip_path = tmp_path / "updates" / "QuillRadio-Portable-2.0.3.zip"
    zip_path.parent.mkdir(parents=True)
    _make_zip(zip_path, ["QuillRadio.exe"])

    launched: dict = {}
    monkeypatch.setattr(
        su, "write_and_launch_helper",
        lambda script, helper_dir: launched.setdefault("script", script) or (helper_dir / "apply-update.bat"),
    )

    su.begin_self_update(
        download_path=zip_path, portable=True, app_data_dir=tmp_path / "appdata", pid=1234,
    )
    assert "robocopy" in launched["script"].lower()
    assert "1234" in launched["script"]
    # Staged the zip so the helper has a real source to copy from.
    assert (tmp_path / "appdata" / "updates" / "staging" / "QuillRadio.exe").is_file()


def test_begin_self_update_installer_builds_installer_script(tmp_path, monkeypatch):
    install = tmp_path / "install"
    (install).mkdir(parents=True)
    (install / "QuillRadio.exe").write_bytes(b"old")
    monkeypatch.setattr(su, "install_root_and_exe", lambda: (install, install / "QuillRadio.exe"))
    setup = tmp_path / "updates" / "Setup-2.0.3.exe"
    setup.parent.mkdir(parents=True)
    setup.write_bytes(b"setup")
    captured: dict = {}
    monkeypatch.setattr(
        su, "write_and_launch_helper",
        lambda script, helper_dir: captured.setdefault("script", script) or (helper_dir / "apply-update.bat"),
    )
    su.begin_self_update(
        download_path=setup, portable=False, app_data_dir=tmp_path / "appdata", pid=7,
    )
    assert "/VERYSILENT" in captured["script"]
    assert "Setup-2.0.3.exe" in captured["script"]


def test_begin_self_update_raises_in_dev_run(tmp_path, monkeypatch):
    monkeypatch.setattr(su, "install_root_and_exe", lambda: None)
    with pytest.raises(SelfUpdateError):
        su.begin_self_update(
            download_path=tmp_path / "x.zip", portable=True, app_data_dir=tmp_path, pid=1,
        )
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/core/test_self_update.py -q`
Expected: FAIL with `AttributeError: module ... has no attribute 'begin_self_update'`.

- [ ] **Step 3: Write minimal implementation**

```python
# add to quill/core/self_update.py

def write_and_launch_helper(script_text: str, helper_dir: Path) -> Path:
    """Write ``apply-update.bat`` into ``helper_dir`` and launch it detached.

    ``helper_dir`` MUST be outside the install directory (the system temp dir),
    so overwriting the install never clobbers the running helper. Launched with
    no console window and fully detached so it outlives this process.
    """
    helper_dir.mkdir(parents=True, exist_ok=True)
    helper = helper_dir / "apply-update.bat"
    helper.write_text(script_text, encoding="utf-8")
    creationflags = 0
    if os.name == "nt":
        creationflags = subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS  # type: ignore[attr-defined]
    subprocess.Popen(  # noqa: S603 - our own generated script, fixed path
        ["cmd.exe", "/c", str(helper)],
        creationflags=creationflags,
        close_fds=True,
        cwd=str(helper_dir),
    )
    return helper


def begin_self_update(
    *,
    download_path: Path,
    portable: bool,
    app_data_dir: Path,
    pid: int | None = None,
) -> None:
    """Apply the already-downloaded update at ``download_path`` and relaunch.

    Stages a portable zip (or targets the setup exe), builds the helper script,
    and launches it detached. Raises :class:`SelfUpdateError` if this is not a
    packaged build or the asset can't be staged -- the caller then leaves the
    app running. On success the caller closes the window; the helper waits for
    this process to exit before applying anything.
    """
    import tempfile

    target = install_root_and_exe()
    if target is None:
        raise SelfUpdateError("This is not a packaged build; nothing to update in place.")
    install_dir, exe_path = target
    updates_dir = app_data_dir / "updates"
    log_path = updates_dir / "apply-update.log"
    resolved_pid = os.getpid() if pid is None else pid

    if portable:
        staging = updates_dir / "staging"
        source = stage_portable_update(download_path, staging, exe_name=exe_path.name)
        script = build_apply_update_script(
            pid=resolved_pid,
            mode="portable",
            install_dir=install_dir,
            exe_path=exe_path,
            log_path=log_path,
            source_dir=source,
        )
    else:
        script = build_apply_update_script(
            pid=resolved_pid,
            mode="installer",
            install_dir=install_dir,
            exe_path=exe_path,
            log_path=log_path,
            setup_exe=download_path,
        )
    helper_dir = Path(tempfile.gettempdir()) / "quill-apply-update"
    write_and_launch_helper(script, helper_dir)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/unit/core/test_self_update.py -q`
Expected: PASS.

- [ ] **Step 5: Lint + typecheck**

Run: `ruff check quill/core/self_update.py && mypy quill\core\self_update.py`
Expected: clean.

- [ ] **Step 6: Commit** (only if the user asked to commit)

```bash
git add quill/core/self_update.py tests/unit/core/test_self_update.py
git commit -m "feat(update): begin_self_update orchestration + detached helper launch"
```

---

## Task 4: End-to-end helper batch test (Windows-guarded)

**Files:**
- Test: `tests/unit/core/test_self_update.py`

**Interfaces:**
- Consumes: `build_apply_update_script` (portable mode).

- [ ] **Step 1: Write the failing test**

```python
# add to tests/unit/core/test_self_update.py
import subprocess as _subprocess
import sys as _sys


@pytest.mark.skipif(not _sys.platform.startswith("win"), reason="Windows helper batch")
def test_portable_helper_batch_copies_and_preserves_data(tmp_path: Path) -> None:
    install = tmp_path / "install"
    (install / "data").mkdir(parents=True)
    (install / "QuillRadio.exe").write_text("OLD", encoding="utf-8")
    (install / "data" / "favorites.json").write_text("keep me", encoding="utf-8")

    source = tmp_path / "staging" / "app"
    source.mkdir(parents=True)
    (source / "QuillRadio.exe").write_text("NEW", encoding="utf-8")
    (source / "docs").mkdir()
    (source / "docs" / "readme.txt").write_text("hello", encoding="utf-8")

    log = tmp_path / "apply.log"
    # A PID that is already gone so the wait loop falls straight through, and a
    # relaunch target that is a harmless no-op (cmd /c exit).
    script = build_apply_update_script(
        pid=999999,
        mode="portable",
        install_dir=install,
        exe_path=Path("cmd.exe"),  # relaunch is a no-op we don't assert on
        log_path=log,
        source_dir=source,
    )
    bat = tmp_path / "apply-update.bat"
    bat.write_text(script, encoding="utf-8")
    _subprocess.run(["cmd.exe", "/c", str(bat)], check=False, timeout=60)

    assert (install / "QuillRadio.exe").read_text(encoding="utf-8") == "NEW"
    assert (install / "docs" / "readme.txt").read_text(encoding="utf-8") == "hello"
    # User data survived the swap.
    assert (install / "data" / "favorites.json").read_text(encoding="utf-8") == "keep me"
```

- [ ] **Step 2: Run test to verify it fails or passes**

Run: `python -m pytest tests/unit/core/test_self_update.py -q -k helper_batch`
Expected: on Windows, PASS (the helper already exists from Task 1). On non-Windows, SKIPPED. If it FAILS, the batch text is wrong — fix `build_apply_update_script` until this passes (this is the real behavioral guard for the pure generator).

- [ ] **Step 3: Commit** (only if the user asked to commit)

```bash
git add tests/unit/core/test_self_update.py
git commit -m "test(update): end-to-end portable helper batch preserves data"
```

---

## Task 5: Wire the standalone apps (Radio + Cast) — `app_shell.py`

**Files:**
- Modify: `quill/ui/app_shell.py` (`_offer_app_update_install`, ~lines 617-678)
- Test: `tests/unit/ui/test_app_shell_self_update.py`

**Interfaces:**
- Consumes: `quill.core.self_update.begin_self_update`; existing `self._running_portable_build()`, `self._announce`, `self._show_modal_dialog`, `self.frame`, `quill.core.paths.app_data_dir`.

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/ui/test_app_shell_self_update.py
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import quill.core.self_update as self_update
from quill.ui.app_shell import AppShellFrame


def _frame(monkeypatch, *, portable: bool):
    calls: list[str] = []
    frame = AppShellFrame.__new__(AppShellFrame)
    frame._announce = lambda msg, **k: calls.append(f"announce:{msg}")
    frame.frame = SimpleNamespace(Close=lambda: calls.append("close"))
    frame._running_portable_build = lambda: portable  # type: ignore[method-assign]
    return frame, calls


def test_apply_now_portable_calls_begin_self_update_then_closes(monkeypatch, tmp_path):
    frame, calls = _frame(monkeypatch, portable=True)
    got: dict = {}
    monkeypatch.setattr(
        self_update, "begin_self_update",
        lambda **kw: got.update(kw),
    )
    target = tmp_path / "QuillRadio-Portable-2.0.3.zip"
    release = SimpleNamespace(version="2.0.3")

    frame._apply_update_and_restart(release, target)  # type: ignore[attr-defined]

    assert got["portable"] is True
    assert got["download_path"] == target
    assert "close" in calls


def test_apply_now_failure_keeps_app_open(monkeypatch, tmp_path):
    frame, calls = _frame(monkeypatch, portable=True)

    def boom(**kw):
        raise self_update.SelfUpdateError("nope")

    monkeypatch.setattr(self_update, "begin_self_update", boom)
    frame._apply_update_and_restart(SimpleNamespace(version="2.0.3"), tmp_path / "x.zip")  # type: ignore[attr-defined]

    assert "close" not in calls
    assert any("could not" in c.lower() or "nope" in c.lower() for c in calls)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/ui/test_app_shell_self_update.py -q`
Expected: FAIL with `AttributeError: 'AppShellFrame' object has no attribute '_apply_update_and_restart'`.

- [ ] **Step 3: Write minimal implementation**

Add the helper method to `AppShellFrame` and call it from the post-download dialog. New method:

```python
# quill/ui/app_shell.py — add method to AppShellFrame
    def _apply_update_and_restart(self, release: object, target: Path) -> None:
        """Apply the downloaded update and relaunch (one-click). On any failure
        the app stays open and the user can still Open folder."""
        from quill.core import self_update
        from quill.core.paths import app_data_dir

        self._announce(f"Installing update {getattr(release, 'version', '')} and restarting")
        try:
            self_update.begin_self_update(
                download_path=Path(str(target)),
                portable=self._running_portable_build(),
                app_data_dir=app_data_dir(),
            )
        except self_update.SelfUpdateError as exc:
            self._show_message_box(
                f"Could not install the update automatically: {exc}\n\n"
                "You can still choose Open folder to update manually.",
                "Update",
                wx.ICON_ERROR | wx.OK,
            )
            return
        self.frame.Close()
```

Then in `_offer_app_update_install`, replace the button set so BOTH portable (.zip) and installer (.exe/.msi) get an **"Install and restart now"** default button, and route it to the new method:

```python
# quill/ui/app_shell.py — inside _offer_app_update_install, replace the
# runnable/zip branching for the action button with:
        applyable = str(target).lower().endswith((".exe", ".msi", ".zip")) and sys.platform.startswith("win")
        if applyable:
            action_line = "Select 'Install and restart now' to update and relaunch automatically, or "
        else:
            action_line = ""
        # ... build dialog body with action_line as today ...
        if applyable:
            apply_btn = wx.Button(dialog, wx.ID_OK, label="Install and restart now")
            apply_btn.Bind(wx.EVT_BUTTON, lambda _e: dialog.EndModal(wx.ID_OK))
            apply_btn.SetDefault()
            buttons.Add(apply_btn, 0)
        else:
            close_btn.SetDefault()
        # ... after ShowModal ...
        if result == wx.ID_OPEN:
            subprocess.Popen(["explorer", "/select,", str(target)])  # noqa: S603,S607
            return
        if result == wx.ID_OK and applyable:
            self._apply_update_and_restart(release, Path(str(target)))
```

Keep the existing `import` of `Path` (add `from pathlib import Path` at method top if not already in scope — `app_shell.py` already imports `Path`).

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/unit/ui/test_app_shell_self_update.py -q`
Expected: PASS (2 tests).

- [ ] **Step 5: Regression + lint**

Run: `python -m pytest tests/unit/ui/test_radio_app_close_and_keys.py -q && ruff check quill/ui/app_shell.py`
Expected: PASS + clean.

- [ ] **Step 6: Commit** (only if the user asked to commit)

```bash
git add quill/ui/app_shell.py tests/unit/ui/test_app_shell_self_update.py
git commit -m "feat(update): one-click Install and restart for Radio/Cast (app_shell)"
```

---

## Task 6: Wire QUILL — `main_frame_updates.py`

**Files:**
- Modify: `quill/ui/main_frame_updates.py` (`_offer_post_download_actions`, ~lines 738-808; `_extract_and_reveal_portable_update` stays as a fallback)
- Test: `tests/unit/ui/test_app_shell_self_update.py` (add a QUILL-seam case) or a new `tests/unit/ui/test_main_frame_updates_self_update.py`

**Interfaces:**
- Consumes: `quill.core.self_update.begin_self_update`, `quill.core.updates.running_portable`, `app_data_dir`, `self.frame`, `self._announce`, `self._show_message_box`.

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/ui/test_main_frame_updates_self_update.py
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import quill.core.self_update as self_update
from quill.ui.main_frame_updates import UpdatesMixin  # adjust to the actual mixin/class name


def test_quill_apply_now_calls_begin_self_update_then_closes(monkeypatch, tmp_path):
    calls: list[str] = []
    frame = UpdatesMixin.__new__(UpdatesMixin)
    frame._announce = lambda m, **k: calls.append("announce")
    frame.frame = SimpleNamespace(Close=lambda: calls.append("close"))
    monkeypatch.setattr(self_update, "install_root_and_exe", lambda: (tmp_path, tmp_path / "quill.exe"))
    got: dict = {}
    monkeypatch.setattr(self_update, "begin_self_update", lambda **kw: got.update(kw))
    monkeypatch.setattr("quill.core.updates.running_portable", lambda: True)

    frame._apply_update_and_restart(SimpleNamespace(version="2.0.3"), tmp_path / "q.zip")  # type: ignore[attr-defined]

    assert got["portable"] is True
    assert "close" in calls
```

> NOTE for the implementer: open `quill/ui/main_frame_updates.py` and use the actual class/mixin name that defines `_offer_post_download_actions` (it is the class `MainFrame` inherits for updates). Import that name in the test.

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/ui/test_main_frame_updates_self_update.py -q`
Expected: FAIL (`_apply_update_and_restart` not defined).

- [ ] **Step 3: Write minimal implementation**

Add the same-shaped method to the updates mixin, using `running_portable()` (QUILL's own detection):

```python
# quill/ui/main_frame_updates.py — add to the updates mixin class
    def _apply_update_and_restart(self, release: object, target: Path) -> None:
        """One-click apply + relaunch on Windows; leaves the app open on failure."""
        from quill.core import self_update
        from quill.core.paths import app_data_dir
        from quill.core.updates import running_portable

        self._announce(f"Installing update {getattr(release, 'version', '')} and restarting")
        try:
            self_update.begin_self_update(
                download_path=Path(str(target)),
                portable=running_portable(),
                app_data_dir=app_data_dir(),
            )
        except self_update.SelfUpdateError as exc:
            self._show_message_box(
                f"Could not install the update automatically: {exc}\n\n"
                "You can still choose Open folder to update manually.",
                "Update",
                self._wx.ICON_ERROR | self._wx.OK,
            )
            return
        self.frame.Close()
```

In `_offer_post_download_actions`, add an **"Install and restart now"** default button when `sys.platform.startswith("win")` and the asset is `.exe/.msi/.zip`, routing `wx.ID_OK` to `_apply_update_and_restart`. Keep the existing `.zip` "Extract now" behavior as the **non-Windows / fallback** path (rename its button to "Extract only" when the apply button is present, so both are available). Preserve the installer `_launch_installer` path as a secondary option if desired, but the primary default becomes apply-and-restart.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/unit/ui/test_main_frame_updates_self_update.py -q`
Expected: PASS.

- [ ] **Step 5: Regression + lint + typecheck**

Run: `python -m pytest tests/unit/ui -q -k update && ruff check quill/ui/main_frame_updates.py`
Expected: PASS + clean. (`main_frame_updates.py` is gradually typed / mypy-excluded — do not run mypy on it.)

- [ ] **Step 6: Commit** (only if the user asked to commit)

```bash
git add quill/ui/main_frame_updates.py tests/unit/ui/test_main_frame_updates_self_update.py
git commit -m "feat(update): one-click Install and restart for QUILL (Windows)"
```

---

## Task 7: Wire Audio Studio (`S:\QUILL-AS`, vendored `quillas`)

**Repo:** `S:\QUILL-AS` vendors quill as a self-contained `quillas` package (it does NOT import the live `quill`). Its `StudioAppFrame` subclasses `quillas.ui.app_shell.AppShellFrame` and already calls `check_for_app_updates`, so it needs the identical seam Radio/Cast got — but placed in `quillas`, not picked up automatically.

**Files:**
- Create: `quillas/core/self_update.py` and `quillas/ui/update_apply.py` — copies of the quill files with `from quill.core`→`from quillas.core` (and `from quill.core import`→`from quillas.core import`). quillas already has `core/updates.py` (`extract_portable_update`, `running_portable`), `core/paths.py` (`app_data_dir`), and `core/error_codes.py` (`CodedError`); it keeps the `QUILL-` error-code prefix, so `SelfUpdateError.code = "QUILL-UPDATE-SELF-APPLY"` is consistent. quillas has no error-code/module-budget gate, so no extra gate to satisfy.
- Modify: `quillas/ui/app_shell.py` `_offer_app_update_install` — apply the same "Install and restart now" edit + add `_apply_update_and_restart` (importing `quillas.core.paths.app_data_dir` and `quillas.ui.update_apply`).
- Create: `tests/unit/core/test_self_update.py` and `tests/unit/ui/test_app_shell_self_update.py` in `S:\QUILL-AS` — ported from the quill tests with `quill.*`→`quillas.*` imports.

- [ ] **Step 1: Port the two core files with import swaps**

Copy `quill/core/self_update.py`→`quillas/core/self_update.py` and `quill/ui/update_apply.py`→`quillas/ui/update_apply.py`, replacing `from quill.core`→`from quillas.core`. Verify: `python -c "import quillas.core.self_update, quillas.ui.update_apply"` from `S:\QUILL-AS`.

- [ ] **Step 2: Apply the app_shell edit** (same two edits as Task 5, but `quillas.core.paths` / `quillas.ui.update_apply` imports).

- [ ] **Step 3: Port the tests and run**

Run (from `S:\QUILL-AS`): `python -m pytest tests/unit/core/test_self_update.py tests/unit/ui/test_app_shell_self_update.py -q`
Expected: PASS (15, incl. the Windows e2e batch). Then `ruff check quillas/core/self_update.py quillas/ui/update_apply.py quillas/ui/app_shell.py` clean, and `python -m pytest tests/unit/ui -q` shows no regression.

> Historical note: an earlier draft of this plan wired Quill Social (`S:\q-social`) here instead. That was reverted per direction; Audio Studio replaces it.

## Task 8: Module budget, full test sweep, and docs

**Files:**
- Modify (if needed): `quill/tools/module_size_budgets.json`
- Modify: `S:\quill-radio\docs\release-notes-2.0.md`, `S:\quill-radio\CHANGELOG.md`
- Regenerate: `S:\quill-radio\docs\release-notes-2.0.html`

- [ ] **Step 1: Full targeted test sweep**

Run: `python -m pytest tests/unit/core/test_self_update.py tests/unit/ui/test_app_shell_self_update.py tests/unit/ui/test_main_frame_updates_self_update.py tests/unit/ui/test_radio_app_close_and_keys.py -q`
Expected: all PASS (Windows-only batch test PASSES on this Windows box).

- [ ] **Step 2: Module size budget gate**

Run: `python -m quill.tools.module_size_budget`
Expected: no NEW violations for `quill/ui/app_shell.py` or `quill/core/self_update.py`. If `app_shell.py` is newly over budget because of the added method, note it to the user (do not raise the ratchet without asking — pre-existing radio.py/main_frame_radio.py violations are unrelated and already known).

- [ ] **Step 3: Error-code audit**

Run: `python -m quill.tools.error_code_audit` (or `pytest tests/unit/tools -q -k error_code`)
Expected: PASS — `SelfUpdateError` is coded `QUILL-UPDATE-SELF-APPLY`.

- [ ] **Step 4: Release-notes bullet**

Add to `S:\quill-radio\docs\release-notes-2.0.md` under `## Update 2.0.3` and to `S:\quill-radio\CHANGELOG.md` under `## 2.0.3`:

```markdown
- **Update in one click -- Quill Radio installs it and restarts itself.** When an update is available, choose Download, then **Install and restart now**: Quill Radio applies the update (extracting the new portable files over your folder, or running the installer silently) and relaunches automatically, keeping all your favorites, recordings, and settings. No more closing the app, unzipping, and swapping folders by hand.
```

- [ ] **Step 5: Re-render HTML**

Run: `cd /s/quill-radio && pandoc docs/release-notes-2.0.md -f gfm -t html5 -s -o docs/release-notes-2.0.html`
Expected: HTML regenerated. (quill-radio is `autocrlf=true`; the QUILL repo is not — keep new QUILL files LF.)

- [ ] **Step 6: Commit** (only if the user asked to commit)

```bash
git add quill/tools/module_size_budgets.json
git -C /s/quill-radio add docs/release-notes-2.0.md docs/release-notes-2.0.html CHANGELOG.md
git commit -m "docs(update): document one-click update in 2.0.3"
```

---

## Self-Review

**Spec coverage:**
- Installed silent+relaunch → Task 1 (installer mode script) + Task 3 (begin_self_update installer branch) + Tasks 5/6 (UI). ✓
- Portable stage → helper → swap-excluding-data → relaunch → Tasks 1-4. ✓
- Build-flavor detection → reuse `_running_portable_build()` / `running_portable()` in Tasks 5/6. ✓
- Consent (one-click) → Tasks 5/6 button. ✓
- Safety (validate exe, exclude data, fail-soft, log) → Tasks 1/2 + `_apply_update_and_restart` error handling. ✓
- Single-instance coordination → helper PID-wait (Task 1); app close releases the lock (existing close paths). ✓
- macOS/dev fallthrough → `install_root_and_exe()` None + `applyable` guarded to `sys.platform.startswith("win")` (Tasks 2/5/6). ✓
- Tests, docs, budget/error-code gates → Tasks 4/7. ✓

**Placeholder scan:** Task 6 intentionally instructs the implementer to look up the exact updates mixin class name (it varies) — this is a lookup, not a placeholder; the method body is complete. No other TBDs.

**Type consistency:** `begin_self_update(*, download_path, portable, app_data_dir, pid=None)`, `stage_portable_update(zip_path, staging_root, *, exe_name) -> Path`, `install_root_and_exe() -> tuple[Path, Path] | None`, `build_apply_update_script(*, pid, mode, install_dir, exe_path, log_path, source_dir=None, setup_exe=None, data_dirname="data") -> str`, `write_and_launch_helper(script_text, helper_dir) -> Path`, `_apply_update_and_restart(release, target)` — consistent across all tasks.
