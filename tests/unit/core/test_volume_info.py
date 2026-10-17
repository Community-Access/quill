"""The drive a file is on, as labelled lines for a properties box (todo item
46). Units match File Explorer; every failure is one line, never an error."""

from __future__ import annotations

import sys
from dataclasses import replace
from pathlib import Path

import pytest

from quill.core.volume_info import (
    VolumeInfo,
    describe_volume,
    format_capacity,
    probe_volume,
    volume_problem,
)


@pytest.mark.parametrize(
    ("size", "expected"),
    [
        (0, "0 bytes"),
        (1, "1 byte"),
        (1023, "1,023 bytes"),
        (1024, "1.00 KB (1,024 bytes)"),
        (15 * 1024 * 1024, "15.0 MB (15,728,640 bytes)"),
        (999_543_627_776, "931 GB (999,543,627,776 bytes)"),
        (1_649_267_441_664, "1.50 TB (1,649,267,441,664 bytes)"),
        (-5, "0 bytes"),
    ],
)
def test_sizes_read_like_file_explorer_with_exact_bytes(size: int, expected: str) -> None:
    assert format_capacity(size) == expected


def _fixed(**changes: object):
    info = VolumeInfo(
        root="D:\\",
        label="Music",
        file_system="NTFS",
        kind="local disk",
        total=1000 * 1024**3,
        used=660 * 1024**3,
        free=340 * 1024**3,
    )
    changed = replace(info, **changes)  # type: ignore[arg-type]
    return lambda _path: changed


def test_a_local_disk_names_itself_and_says_how_full() -> None:
    lines = describe_volume(Path("D:/Music/song.mp3"), probe=_fixed())
    assert lines == [
        "Drive: D:\\ (Music), local disk, NTFS",
        "Drive capacity: 1000 GB (1,073,741,824,000 bytes)",
        "Drive used: 660 GB (708,669,603,840 bytes), 66 percent",
        "Drive free: 340 GB (365,072,220,160 bytes)",
    ]


def test_a_removable_drive_without_a_label() -> None:
    lines = describe_volume(
        Path("E:/a.wav"),
        probe=_fixed(root="E:\\", label="", kind="removable drive", file_system="FAT32"),
    )
    assert lines[0] == "Drive: E:\\, removable drive, FAT32"


def test_a_network_share_is_named_by_its_share() -> None:
    lines = describe_volume(
        Path("//server/media/a.mp3"),
        probe=_fixed(
            root="\\\\server\\media\\", label="", kind="network drive", file_system="NTFS"
        ),
    )
    assert lines[0] == "Drive: \\\\server\\media, network drive, NTFS"


def test_a_drive_that_reports_no_size_says_so() -> None:
    lines = describe_volume(Path("F:/x"), probe=_fixed(total=0, used=0, free=0))
    assert lines[-1] == "Drive capacity: not reported by this drive."


def _failing(error: OSError):
    def probe(_path: Path) -> VolumeInfo:
        raise error

    return probe


def test_a_pulled_out_drive_is_one_line() -> None:
    lines = describe_volume(Path("E:/a.wav"), probe=_failing(FileNotFoundError(2, "gone")))
    assert lines == [
        "Drive: not available. The drive could not be found or is not ready. "
        "It may have been removed or disconnected."
    ]


def test_a_permission_refusal_is_said_plainly() -> None:
    lines = describe_volume(Path("C:/secret/a"), probe=_failing(PermissionError(13, "denied")))
    assert "did not allow this drive to be read" in lines[0]


def test_an_unreachable_share_says_network() -> None:
    lines = describe_volume(Path("//server/gone/a.mp3"), probe=_failing(FileNotFoundError(2, "x")))
    assert "network location could not be reached" in lines[0]


def test_a_windows_network_error_code_says_network() -> None:
    error = OSError(0, "The network path was not found")
    error.winerror = 53  # type: ignore[attr-defined]
    assert "network" in volume_problem(error)


def test_any_other_failure_still_says_something() -> None:
    assert volume_problem(OSError(5, "odd")).startswith("The drive could not be read")


@pytest.mark.skipif(sys.platform != "win32", reason="the Windows volume calls")
def test_the_real_probe_reads_the_drive_this_test_runs_on(tmp_path: Path) -> None:
    info = probe_volume(tmp_path / "not-yet-written.txt")
    assert info.total > 0 and 0 <= info.free <= info.total
    assert info.root.endswith("\\")
    assert info.kind in {"local disk", "removable drive", "network drive", "RAM disk", "drive"}


@pytest.mark.skipif(sys.platform != "win32", reason="the Windows volume calls")
def test_a_drive_letter_that_is_not_there_is_not_guessed(tmp_path: Path) -> None:
    import string
    from os.path import exists

    free = next(
        (f"{c}:\\" for c in reversed(string.ascii_uppercase) if not exists(f"{c}:\\")), None
    )
    if free is None:
        pytest.skip("every drive letter is in use")
    with pytest.raises(FileNotFoundError):
        probe_volume(Path(free) / "a.mp3")
