"""Every file left out has a name and a reason a listener can act on.

Reported 2026-10-04: Quill Radio said some items were skipped and never said
which, to a listener about to reset two computers whose recordings and
backups live in OneDrive. These pin the vocabulary that replaces the count.
No real OneDrive: placeholders are faked through the injectable ``stat``.
"""

from __future__ import annotations

import errno
import os
from pathlib import Path
from types import SimpleNamespace

from quill.core import skipped_files as sf


def _stat_with(attributes: int):
    def _stat(_path: Path) -> os.stat_result:
        return SimpleNamespace(st_file_attributes=attributes, st_size=10)  # type: ignore[return-value]

    return _stat


def _winerror(code: int) -> OSError:
    error = OSError(errno.EACCES, "denied")
    error.winerror = code  # type: ignore[attr-defined]
    return error


def test_a_recall_on_data_access_placeholder_is_cloud_only(tmp_path: Path) -> None:
    path = tmp_path / "show.mp3"
    assert sf.is_cloud_only(path, stat=_stat_with(sf.FILE_ATTRIBUTE_RECALL_ON_DATA_ACCESS))
    assert sf.is_cloud_only(path, stat=_stat_with(sf.FILE_ATTRIBUTE_RECALL_ON_OPEN))
    assert sf.is_cloud_only(path, stat=_stat_with(sf.FILE_ATTRIBUTE_OFFLINE))


def test_a_downloaded_file_is_not_cloud_only(tmp_path: Path) -> None:
    path = tmp_path / "show.mp3"
    assert not sf.is_cloud_only(path, stat=_stat_with(0x20))  # FILE_ATTRIBUTE_ARCHIVE


def test_a_file_that_cannot_be_statted_is_not_called_cloud_only(tmp_path: Path) -> None:
    assert not sf.is_cloud_only(tmp_path / "missing.mp3")


def test_a_sharing_violation_reads_as_in_use(tmp_path: Path) -> None:
    assert sf.classify_error(_winerror(32), tmp_path / "a.mp3") == sf.REASON_IN_USE


def test_a_cloud_provider_error_reads_as_onedrive_only(tmp_path: Path) -> None:
    # 362: ERROR_CLOUD_FILE_PROVIDER_NOT_RUNNING (OneDrive is not running).
    assert sf.classify_error(_winerror(362), tmp_path / "a.mp3") == sf.REASON_CLOUD_ONLY


def test_any_failure_on_a_placeholder_reads_as_onedrive_only(tmp_path: Path) -> None:
    reason = sf.classify_error(
        OSError(errno.EIO, "io"), tmp_path / "a.mp3", stat=_stat_with(sf.CLOUD_ONLY_ATTRIBUTES)
    )
    assert reason == sf.REASON_CLOUD_ONLY


def test_a_path_past_the_windows_limit_reads_as_too_long(tmp_path: Path) -> None:
    long_path = tmp_path / ("x" * 300) / "a.mp3"
    assert sf.classify_error(OSError(errno.ENOENT, "nope"), long_path) == sf.REASON_TOO_LONG
    assert sf.classify_error(_winerror(206), tmp_path / "a.mp3") == sf.REASON_TOO_LONG


def test_anything_else_reads_as_could_not_be_read(tmp_path: Path) -> None:
    reason = sf.classify_error(OSError(errno.EIO, "io"), tmp_path / "a.mp3", stat=_stat_with(0))
    assert reason == sf.REASON_UNREADABLE


def test_the_report_names_every_item_grouped_by_reason() -> None:
    rows = [
        sf.SkippedFile("a.mp3", sf.REASON_CLOUD_ONLY),
        sf.SkippedFile("b.mp3", sf.REASON_IN_USE),
        sf.SkippedFile("c.mp3", sf.REASON_CLOUD_ONLY),
    ]
    assert sf.report_lines(rows) == [
        f"a.mp3: {sf.REASON_CLOUD_ONLY}",
        f"c.mp3: {sf.REASON_CLOUD_ONLY}",
        f"b.mp3: {sf.REASON_IN_USE}",
    ]


def test_onedrive_advice_says_always_keep_on_this_device_once() -> None:
    rows = [sf.SkippedFile(f"{n}.mp3", sf.REASON_CLOUD_ONLY) for n in range(3)]
    advice = sf.what_to_do(rows)
    assert len(advice) == 1
    assert "Always keep on this device" in advice[0]


def test_nothing_to_carry_has_no_advice() -> None:
    assert sf.what_to_do([sf.SkippedFile("Your quiet hours", sf.REASON_NOT_ON_THIS_COMPUTER)]) == []
