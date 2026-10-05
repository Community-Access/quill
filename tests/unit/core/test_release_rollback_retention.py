"""How long the installer kept for undoing an update stays, by channel.

Owner decision 2026-10-04 (questions.md 32): on Beta and Dev the running
version's installer is kept for as long as that version runs; on Stable only
for seven days or three successful starts after each update, so a Stable
computer gets its ~200 MB back.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from quill.core.updater import apply

NOW = datetime(2026, 10, 20, 12, 0, tzinfo=UTC)


def _updated(tmp_path: Path, channel: str) -> tuple[Path, Path, Path]:
    """An update from 3.2.0 to 3.3.0 that started, on *channel*."""
    updates = tmp_path / "updates"
    log = tmp_path / "history.jsonl"
    new_setup = updates / "Setup-3.3.0.exe"
    new_setup.parent.mkdir(parents=True)
    new_setup.write_bytes(b"new")
    apply.record_pending(
        updates, app_key="radio", from_version="3.2.0", to_version="3.3.0", setup=new_setup
    )
    report = apply.confirm_started(
        updates,
        app_key="radio",
        app_name="Quill Radio",
        version="3.3.0",
        now=NOW,
        history_path=log,
        channel=channel,
    )
    assert report.installed == "3.3.0"
    return updates, log, updates / "rollback" / "Setup-3.3.0.exe"


def _start(updates: Path, log: Path, channel: str, when: datetime) -> None:
    apply.confirm_started(
        updates,
        app_key="radio",
        app_name="Quill Radio",
        version="3.3.0",
        now=when,
        history_path=log,
        channel=channel,
    )


@pytest.mark.parametrize("channel", ["beta", "dev"])
def test_beta_and_dev_keep_the_installer_for_as_long_as_the_version_runs(
    tmp_path: Path, channel: str
) -> None:
    updates, log, kept = _updated(tmp_path, channel)
    for day in range(1, 40):
        _start(updates, log, channel, NOW + timedelta(days=day))
    assert kept.is_file()
    assert apply.rollback_setup_for(updates, "3.3.0") == kept


def test_stable_lets_it_go_after_three_starts(tmp_path: Path) -> None:
    updates, log, kept = _updated(tmp_path, "stable")
    _start(updates, log, "stable", NOW + timedelta(hours=1))
    assert kept.is_file()
    _start(updates, log, "stable", NOW + timedelta(hours=2))
    assert not kept.exists()
    assert apply.rollback_setup_for(updates, "3.3.0") is None
    # The version stays known, so the next update still says where it came from.
    assert apply.installed_version(updates) == "3.3.0"


def test_stable_lets_it_go_after_seven_days_even_without_three_starts(tmp_path: Path) -> None:
    updates, log, kept = _updated(tmp_path, "stable")
    _start(updates, log, "stable", NOW + timedelta(days=6))
    assert kept.is_file()
    _start(updates, log, "stable", NOW + timedelta(days=7))
    assert not kept.exists()


def test_moving_from_beta_to_stable_starts_the_clock_then(tmp_path: Path) -> None:
    updates, log, kept = _updated(tmp_path, "beta")
    _start(updates, log, "beta", NOW + timedelta(days=30))
    later = NOW + timedelta(days=31)
    _start(updates, log, "stable", later)
    assert kept.is_file()
    _start(updates, log, "stable", later + timedelta(days=7))
    assert not kept.exists()


def test_the_next_update_still_records_where_it_came_from(tmp_path: Path) -> None:
    updates, log, kept = _updated(tmp_path, "stable")
    for hour in (1, 2):
        _start(updates, log, "stable", NOW + timedelta(hours=hour))
    assert not kept.exists()
    newer = updates / "Setup-3.4.0.exe"
    newer.write_bytes(b"newer")
    apply.record_pending(
        updates,
        app_key="radio",
        from_version=apply.installed_version(updates),
        to_version="3.4.0",
        setup=newer,
    )
    pending = json.loads(apply.pending_path(updates).read_text("utf-8"))
    assert pending["from"] == "3.3.0"


def test_an_unknown_channel_is_treated_as_stable() -> None:
    assert apply.keeps_installer("beta") and apply.keeps_installer("dev")
    assert not apply.keeps_installer("stable")
    assert not apply.keeps_installer("nonsense")
