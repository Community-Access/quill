import sys
from pathlib import Path

from quill.platform.windows import sr_detect
from quill.platform.windows.sr_detect import detect_screen_reader


def test_detect_screen_reader_nvda() -> None:
    result = detect_screen_reader(["explorer.exe", "nvda.exe"])
    assert result.detected is True
    assert result.name == "NVDA"


def test_detect_screen_reader_jaws() -> None:
    result = detect_screen_reader(["jfw.exe"])
    assert result.detected is True
    assert result.name == "JAWS"


def test_detect_screen_reader_none() -> None:
    result = detect_screen_reader(["explorer.exe", "chrome.exe"])
    assert result.detected is False
    assert result.name == "none"


def test_detection_uses_api_not_a_subprocess() -> None:
    """The probe must use the Windows API, never spawn tasklist.exe.

    Spawning the console app flashed a terminal window a screen reader announced
    on every launch; guard against re-introducing the shell-out. ``import
    subprocess`` would expose ``sr_detect.subprocess``; the source must contain
    no ``subprocess.run`` call or ``tasklist`` command literal (prose in the
    module docstring may still mention them for historical context).
    """
    assert not hasattr(sr_detect, "subprocess")
    source = Path(sr_detect.__file__).read_text(encoding="utf-8")
    assert "subprocess.run" not in source
    assert '"tasklist"' not in source


def test_running_process_names_returns_list() -> None:
    names = sr_detect._running_process_names()
    assert isinstance(names, list)
    if sys.platform == "win32":
        # On Windows the live snapshot includes this very test process.
        assert any("python" in name.lower() for name in names)
