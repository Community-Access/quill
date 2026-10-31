"""Is this computer ready for a long recording? (roadmap P3)

Three measurements the spoken check adds, each cheap and read-only:

- **Keeping up**: three seconds of the real screen capture at the chosen
  settings, encoded and thrown away, counting frames dropped because the
  computer fell behind.
- **Power**: on battery or mains, the charge and the estimated time left.
- **A pending restart** from Windows Update, which can end a recording.

Windows-only; anything unreadable is reported as unknown, never guessed.
"""

from __future__ import annotations

import ctypes
import subprocess
from ctypes import wintypes
from dataclasses import dataclass
from pathlib import Path

from quill.core.demo_recording import DemoPlan
from quill.core.demo_recording_ffmpeg import parse_stats, screen_capture_command
from quill.stability.safe_subprocess import run_subprocess_safely

_TEST_SECONDS = 3


@dataclass(frozen=True)
class Power:
    on_battery: bool
    percent: int  # -1 unknown
    minutes_left: int  # -1 unknown


class _PowerStatus(ctypes.Structure):
    _fields_ = [
        ("ACLineStatus", ctypes.c_ubyte),
        ("BatteryFlag", ctypes.c_ubyte),
        ("BatteryLifePercent", ctypes.c_ubyte),
        ("SystemStatusFlag", ctypes.c_ubyte),
        ("BatteryLifeTime", wintypes.DWORD),
        ("BatteryFullLifeTime", wintypes.DWORD),
    ]


def power() -> Power | None:
    status = _PowerStatus()
    try:
        if not ctypes.windll.kernel32.GetSystemPowerStatus(ctypes.byref(status)):
            return None
    except (AttributeError, OSError):
        return None
    no_battery = status.BatteryFlag == 128
    percent = -1 if status.BatteryLifePercent == 255 or no_battery else status.BatteryLifePercent
    seconds = status.BatteryLifeTime
    minutes = -1 if seconds == 0xFFFFFFFF else seconds // 60
    return Power(status.ACLineStatus == 0 and not no_battery, int(percent), int(minutes))


def restart_pending() -> bool:
    """Windows Update is waiting to restart the computer."""
    import winreg

    keys = (
        r"SOFTWARE\Microsoft\Windows\CurrentVersion\WindowsUpdate\Auto Update\RebootRequired",
        r"SOFTWARE\Microsoft\Windows\CurrentVersion\Component Based Servicing\RebootPending",
    )
    for key in keys:
        try:
            winreg.CloseKey(winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key))
            return True
        except OSError:
            continue
    return False


def dropped_share(ffmpeg: str, plan: DemoPlan, backend: str, encoder: str) -> float | None:
    """The share of frames dropped in a 3-second trial at these settings, or None.

    A live capture always runs at real time, so FFmpeg's ``speed`` says little;
    frames dropped because the encoder fell behind are what spoil a recording.
    """
    if not plan.screen or not backend:
        return None
    command = screen_capture_command(ffmpeg, plan, Path("NUL"), backend=backend, encoder=encoder)
    cut = command.index("-f", command.index("-an"))
    command = [*command[:cut], "-t", str(_TEST_SECONDS), "-f", "null", "-"]
    try:
        result = run_subprocess_safely(command, timeout_seconds=_TEST_SECONDS + 30)
    except (OSError, subprocess.TimeoutExpired, ValueError):
        return None
    output = (result.stderr or "") + (result.stdout or "")
    last = None
    for line in output.replace(chr(13), chr(10)).splitlines():
        stats = parse_stats(line)
        if stats is not None:
            last = stats
    if last is None or last.frames <= 0:
        return None
    return last.dropped / (last.frames + last.dropped)
