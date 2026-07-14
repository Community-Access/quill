"""Windows UI-automation harness: launch the real QUILL through UIA.

Opt-in by design: these tests spawn the actual application on a desktop
session, so they never run in the default suite. Run them with::

    set QUILL_UIA_TESTS=1
    pytest -m uia -q

The harness gives every test an isolated app profile (its own
``QUILL_DATA_DIR`` under the user's home, which the dev-build gate requires),
pre-seeded so nothing modal blocks automation:

- ``settings.json``: setup wizard marked completed, update checks off (no
  network in tests), announcement trace on (spoken output lands in
  ``diagnostics/announcement-trace.log`` for assertions).
- ``trust-consent.json``: accepted at the current consent version.

The announcement trace is the accessibility-regression primitive: tests can
assert what QUILL *said*, not just what it drew.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
import uuid
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

import pytest

pytestmark = pytest.mark.uia

_LAUNCH_TIMEOUT_SECONDS = 45.0
_TITLE_MARKER = "QUILL for All"


def pytest_collection_modifyitems(config: object, items: list[pytest.Item]) -> None:
    enabled = os.environ.get("QUILL_UIA_TESTS", "").strip() == "1" and sys.platform == "win32"
    skip = pytest.mark.skip(
        reason="UI-automation tests are opt-in: set QUILL_UIA_TESTS=1 on a Windows desktop"
    )
    for item in items:
        if not (item.path and "uia" in item.path.parts):
            continue
        if enabled:
            # Launching the real app dwarfs the repo-wide 30 s pytest-timeout.
            item.add_marker(pytest.mark.timeout(180))
        else:
            item.add_marker(skip)


@dataclass
class QuillApp:
    """A running QUILL instance plus the paths tests assert against."""

    process: subprocess.Popen[bytes]
    data_dir: Path
    main_window: object  # pywinauto WindowSpecification

    @property
    def announcement_trace(self) -> Path:
        return self.data_dir / "diagnostics" / "announcement-trace.log"

    def spoken(self) -> list[str]:
        """Every announcement QUILL has made so far, oldest first."""
        try:
            text = self.announcement_trace.read_text(encoding="utf-8")
        except OSError:
            return []
        return [line for line in text.splitlines() if line.strip()]

    def wait_spoken(self, fragment: str, timeout: float = 10.0) -> str:
        """Wait until an announcement containing ``fragment`` appears; return it."""
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            for line in self.spoken():
                if fragment.lower() in line.lower():
                    return line
            time.sleep(0.25)
        raise AssertionError(
            f"QUILL never announced anything containing {fragment!r}. "
            f"Spoken so far: {self.spoken()!r}"
        )


def _corpus_sample_path() -> Path:
    """Path to the chaptered MP3 the UIA suite opens in the Workbench.

    Resolved from the repo root, not from ``cwd``, so the suite works under
    any working directory the CI runner uses. The fixture is the same
    ``tests/corpus/audio/chaptered-sample.mp3`` the unit tests use for
    ``quill/core/speech/book_file.py``.
    """
    return (
        Path(__file__).resolve().parents[2] / "tests" / "corpus" / "audio" / "chaptered-sample.mp3"
    )


def _seed_profile(data_dir: Path) -> None:
    data_dir.mkdir(parents=True, exist_ok=True)
    from quill.core.onboarding import current_trust_consent_version

    (data_dir / "settings.json").write_text(
        json.dumps({
            "setup_wizard_completed": True,
            "auto_check_updates": False,
            "announcement_trace_enabled": True,
            # Keep runs deterministic and quiet: no tips, no tray.
            "show_tips_on_startup": False,
        }),
        encoding="utf-8",
    )
    (data_dir / "trust-consent.json").write_text(
        json.dumps({"accepted": True, "version": current_trust_consent_version()}),
        encoding="utf-8",
    )
    # Pre-seed the Audio Studio audiobooks MRU so the edit journey's
    # EditSourcePage ComboBox already has the corpus sample at the top.
    # The Workbench-on-corpus UIA test does not need to drive a FileDialog.
    corpus = _corpus_sample_path()
    if corpus.is_file():
        (data_dir / "audio-studio-recent-audiobooks.json").write_text(
            json.dumps([str(corpus)]),
            encoding="utf-8",
        )


@pytest.fixture
def quill_app(tmp_path_factory: pytest.TempPathFactory) -> Iterator[QuillApp]:
    """Launch QUILL on an isolated profile; yield the connected UIA app."""
    from pywinauto import Application

    # The dev-build QUILL_DATA_DIR override must live under the user's home
    # directory (core.paths constraint), so the profile goes to LOCALAPPDATA.
    base = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "QuillUiaTests"
    data_dir = base / uuid.uuid4().hex[:12]
    _seed_profile(data_dir)

    env = dict(os.environ)
    env["QUILL_DATA_DIR"] = str(data_dir)
    env["QUILL_DEV_BUILD"] = "1"

    process = subprocess.Popen(  # noqa: S603 - launching our own app under test
        [sys.executable, "-m", "quill"],
        env=env,
        cwd=str(Path(__file__).resolve().parents[2]),
    )
    try:
        app = Application(backend="uia")
        deadline = time.monotonic() + _LAUNCH_TIMEOUT_SECONDS
        window = None
        last_error: Exception | None = None
        while time.monotonic() < deadline:
            if process.poll() is not None:
                raise AssertionError(f"QUILL exited during launch with code {process.returncode}")
            try:
                app.connect(process=process.pid)
                window = app.window(title_re=f".*{_TITLE_MARKER}.*")
                window.wait("exists visible", timeout=2)
                break
            except Exception as exc:  # noqa: BLE001 - keep polling until deadline
                last_error = exc
                time.sleep(0.5)
        else:
            raise AssertionError(f"QUILL main window never appeared: {last_error}")

        yield QuillApp(process=process, data_dir=data_dir, main_window=window)
    finally:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
        shutil.rmtree(data_dir, ignore_errors=True)
