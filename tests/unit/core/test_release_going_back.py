"""Release channels, Phase 4: safe downgrades, saved copies and undoing updates.

"Back to Stable only if safe" as a table (the ledger against what Stable can
read, losses declared by the writer, withdrawn builds, the security floor);
restoring the copy saved when an app joined Beta (a copy of now first, shared
files a sibling on Beta wrote left alone, the ledger lowered); and the update
helper's books -- the start marker, the kept installer, the undo notice, the
3-starts-or-7-days ageing -- plus the batch lines for the portable swap and the
health check. No installer runs and nothing is downloaded.
"""

from __future__ import annotations

import json
import zipfile
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from quill.core.data_format_ledger import Ledger, LedgerEntry, read_ledger, record
from quill.core.data_formats import formats_for
from quill.core.self_update import build_apply_update_script
from quill.core.updater import apply, history
from quill.core.updater.apply_script import health_lines, swap_lines
from quill.core.updater.channels import ChannelState
from quill.core.updater.feed import FeedAsset, FeedRelease, ReleaseFeed
from quill.core.updater.going_back import (
    UnsafeDowngradeError,
    assess_return,
    authorize_downgrade,
    downgrade_verdict,
    shared_formats_kept,
)
from quill.core.updater.snapshots import restore_snapshot, take_snapshot
from quill.core.updater.wording import return_text

NOW = datetime(2026, 10, 20, 12, 0, tzinfo=UTC)


def _release(version: str, reads: dict[str, int], **kw) -> FeedRelease:
    asset = FeedAsset(
        "installer",
        f"Quill-Radio-Setup-Shared-{version}.exe",
        f"https://github.com/Community-Access/quill/releases/download/quill-radio-v{version}/x.exe",
        10,
        "a" * 64,
    )
    return FeedRelease(
        version=version,
        tag=f"quill-radio-v{version}",
        channels=kw.pop("channels", ("stable", "beta")),
        assets=(asset,),
        reads_formats=reads,
        data_formats=dict(reads),
        **kw,
    )


def _ledger(**highs: int) -> Ledger:
    return Ledger({k.replace("_", ".", 1): LedgerEntry(v) for k, v in highs.items()})


# -- the verdict -------------------------------------------------------------------


@pytest.mark.parametrize(
    ("reads", "ledger", "lossy", "kind", "named"),
    [
        ({"radio.favorites": 1}, {"radio_favorites": 1}, {}, "safe", ()),
        ({"radio.favorites": 1}, {"radio_favorites": 2}, {}, "unsafe", ("radio.favorites",)),
        ({}, {"radio_favorites": 1}, {}, "unsafe", ("radio.favorites",)),
        (
            {"radio.favorites": 1},
            {"radio_favorites": 2},
            {"radio.favorites": 1},
            "safe_with_losses",
            ("radio.favorites",),
        ),
        ({"radio.favorites": 1}, {"quill_settings": 9, "radio_favorites": 1}, {}, "safe", ()),
    ],
)
def test_downgrade_verdict_table(reads, ledger, lossy, kind, named) -> None:
    verdict = downgrade_verdict(
        _release("3.2.0", reads), [_ledger(**ledger)], app_key="radio", lossy_ok=lossy
    )
    assert verdict.kind == kind
    assert (verdict.blockers or verdict.losses) == named


def test_a_withdrawn_or_insecure_target_is_never_safe() -> None:
    reads = {"radio.favorites": 1}
    assert downgrade_verdict(_release("3.2.0", reads, revoked=True), [], app_key="radio").kind == (
        "unsafe"
    )
    floor = downgrade_verdict(_release("3.1.0", reads), [], app_key="radio", security_floor="3.2.0")
    assert floor.kind == "unsafe" and "security" in floor.reason


def _feed(stable_reads: dict[str, int]) -> ReleaseFeed:
    return ReleaseFeed(
        app="radio",
        app_name="Quill Radio",
        sequence=4,
        generated_at="",
        expires_at=(NOW + timedelta(days=60)).isoformat(),
        releases=(
            _release("3.2.0", stable_reads),
            _release("3.4.0-beta.1", {"radio.favorites": 2}, channels=("beta",)),
        ),
    )


def test_assess_and_authorize(tmp_path: Path) -> None:
    copy = tmp_path / "radio-3.2.0-joined-beta.qrbackup"
    copy.write_bytes(b"x")
    state = ChannelState(channel="beta", snapshot=str(copy), joined_at="2026-10-03T10:00:00Z")
    unsafe = assess_return(
        "radio",
        "3.4.0-beta.1",
        _feed({"radio.favorites": 1}),
        state,
        [_ledger(radio_favorites=2)],
        {},
    )
    assert unsafe.is_downgrade and unsafe.verdict.kind == "unsafe"
    assert unsafe.snapshot == copy and unsafe.snapshot_date == "3 October"
    with pytest.raises(UnsafeDowngradeError, match="favorites"):
        authorize_downgrade(unsafe)
    assert authorize_downgrade(unsafe, restored=True).version == "3.2.0"
    text = return_text(unsafe, "Quill Radio", "beta")
    assert "Use the copy from 3 October" in text and "Wait for Stable" in text
    safe = assess_return(
        "radio",
        "3.4.0-beta.1",
        _feed({"radio.favorites": 2}),
        state,
        [_ledger(radio_favorites=2)],
        {},
    )
    assert authorize_downgrade(safe).version == "3.2.0"
    assert "safe to go back now" in return_text(safe, "Quill Radio", "beta")


def test_no_copy_means_waiting_is_the_only_choice() -> None:
    state = ChannelState(channel="beta")
    unsafe = assess_return(
        "radio",
        "3.4.0-beta.1",
        _feed({"radio.favorites": 1}),
        state,
        [_ledger(radio_favorites=2)],
        {},
    )
    assert "only safe choice is to wait" in return_text(unsafe, "Quill Radio", "beta")


def test_shared_files_stay_while_a_sibling_is_on_beta() -> None:
    channels = {"radio": ChannelState(channel="beta")}
    assert set(shared_formats_kept("cast", channels)) == {
        "shared.media_bookmarks",
        "shared.listens",
    }
    assert shared_formats_kept("cast", {}) == ()


# -- restoring the saved copy --------------------------------------------------------


def test_restore_puts_the_copy_back_and_lowers_the_ledger(tmp_path: Path) -> None:
    data = tmp_path / "data"
    data.mkdir()
    (data / "podcasts_library.json").write_text('{"old": true}', encoding="utf-8")
    (data / "media_bookmarks.json").write_text('{"bookmarks": "old"}', encoding="utf-8")
    record(data, formats_for("cast"), "cast 2.0.0")
    copy = take_snapshot("cast", "2.0.0", "joined-beta", data=data, now=NOW)
    assert copy.with_name(copy.name + ".ledger.json").is_file()
    # Beta moves on: newer files, a newer format in the ledger.
    (data / "podcasts_library.json").write_text('{"new": true}', encoding="utf-8")
    (data / "media_bookmarks.json").write_text('{"bookmarks": "new"}', encoding="utf-8")
    raised = tuple(
        type(f)(**{**f.__dict__, "current": 2})
        for f in formats_for("cast")
        if f.id == "cast.library"
    )
    record(data, raised, "cast 2.1.0-beta.1")
    assert read_ledger(data).high("cast.library") == 2
    outcome = restore_snapshot(
        "cast",
        copy,
        version_now="2.1.0-beta.1",
        keep_shared=("shared.media_bookmarks",),
        data=data,
        now=NOW + timedelta(seconds=5),
    )
    assert json.loads((data / "podcasts_library.json").read_text("utf-8")) == {"old": True}
    assert json.loads((data / "media_bookmarks.json").read_text("utf-8")) == {"bookmarks": "new"}
    assert "media_bookmarks.json" in outcome.kept
    assert outcome.before.is_file() and "before-restore" in outcome.before.name
    assert read_ledger(data).high("cast.library") == 1


def test_quill_restores_only_its_own_files_from_the_shared_folder(tmp_path: Path) -> None:
    data = tmp_path / "data"
    data.mkdir()
    copy = tmp_path / "quill-1.1.0-joined-beta.zip"
    with zipfile.ZipFile(copy, "w") as archive:
        archive.writestr("settings.json", '{"v": "old"}')
        archive.writestr("radio_favorites.json", '{"radio": "old"}')
    (data / "radio_favorites.json").write_text('{"radio": "mine"}', encoding="utf-8")
    restore_snapshot("quill", copy, version_now="1.1.0-beta.2", data=data, now=NOW)
    assert (data / "settings.json").read_text("utf-8") == '{"v": "old"}'
    assert (data / "radio_favorites.json").read_text("utf-8") == '{"radio": "mine"}'


def test_the_joined_copy_outlives_ordinary_pruning(tmp_path: Path) -> None:
    data = tmp_path / "data"
    data.mkdir()
    (data / "settings.json").write_text("{}", encoding="utf-8")
    joined = take_snapshot("quilllite", "1.2.0", "joined-beta", data=data, now=NOW)
    for minute in range(1, 6):
        take_snapshot(
            "quilllite", "1.3.0", "before-update", data=data, now=NOW + timedelta(minutes=minute)
        )
    assert joined.is_file()
    others = [
        p
        for p in joined.parent.glob("quilllite-*")
        if "before-update" in p.name and not p.name.endswith(".json")
    ]
    assert len(others) == 3


# -- the helper's books ------------------------------------------------------------


def test_a_good_update_keeps_the_new_installer_and_ages_out_the_old(tmp_path: Path) -> None:
    updates = tmp_path / "updates"
    log = tmp_path / "history.jsonl"
    old_setup = updates / "rollback" / "Setup-3.2.0.exe"
    old_setup.parent.mkdir(parents=True)
    old_setup.write_bytes(b"old")
    (updates / "rollback" / "rollback-state.json").write_text(
        json.dumps({"installed": {"version": "3.2.0", "setup": str(old_setup)}}), "utf-8"
    )
    assert apply.rollback_setup_for(updates, "3.2.0") == old_setup
    new_setup = updates / "Setup-3.3.0.exe"
    new_setup.write_bytes(b"new")
    apply.record_pending(
        updates, app_key="radio", from_version="3.2.0", to_version="3.3.0", setup=new_setup
    )
    report = apply.confirm_started(
        updates, app_key="radio", app_name="Quill Radio", version="3.3.0", now=NOW, history_path=log
    )
    assert report.installed == "3.3.0" and not report.notice
    assert apply.started_marker(updates, "3.3.0").is_file()
    assert apply.rollback_setup_for(updates, "3.3.0") == updates / "rollback" / "Setup-3.3.0.exe"
    assert old_setup.is_file()
    for day in (1, 2):
        apply.confirm_started(
            updates,
            app_key="radio",
            app_name="Quill Radio",
            version="3.3.0",
            now=NOW + timedelta(days=day),
            history_path=log,
        )
    assert not old_setup.exists()
    assert [e.kind for e in history.read_events(path=log)] == ["installed"]


def test_a_failed_update_is_reported_once_and_recorded(tmp_path: Path) -> None:
    updates = tmp_path / "updates"
    log = tmp_path / "history.jsonl"
    apply.record_pending(
        updates, app_key="radio", from_version="3.2.0", to_version="3.3.0", setup=None
    )
    apply.result_path(updates).write_text(
        '{"version": "3.2.0", "rolled_back": true, "failed_version": "3.3.0"}', "utf-8"
    )
    report = apply.confirm_started(
        updates, app_key="radio", app_name="Quill Radio", version="3.2.0", now=NOW, history_path=log
    )
    assert report.rolled_back_from == "3.3.0"
    assert report.notice.startswith(
        "The update to 3.3.0 didn't start, so Quill Radio went back to 3.2.0."
    )
    assert history.read_events(path=log)[0].kind == "rolled_back"
    again = apply.confirm_started(
        updates, app_key="radio", app_name="Quill Radio", version="3.2.0", now=NOW, history_path=log
    )
    assert again.notice == ""


def test_spellings_of_one_version_agree() -> None:
    assert apply.started_marker(Path("u"), "1.1.0 Beta 1") == apply.started_marker(
        Path("u"), "1.1.0-beta.1"
    )


# -- the batch lines -----------------------------------------------------------------


def test_portable_swap_keeps_previous_and_falls_back_to_copying(tmp_path: Path) -> None:
    lines = swap_lines(
        source_dir=tmp_path / "staging" / "QuillRadio",
        install_dir=tmp_path / "QuillRadio",
        data_dirname="data",
        mir_fallback="robocopy MIR",
    )
    text = "\n".join(lines)
    assert f'move "{tmp_path / "QuillRadio"}" "{tmp_path / "QuillRadio"}.previous"' in text
    assert "robocopy MIR" in text and ":swapfailed" in text


def test_health_check_undoes_an_installed_update_with_the_kept_installer(tmp_path: Path) -> None:
    script = build_apply_update_script(
        pid=7,
        mode="installer",
        install_dir=tmp_path,
        exe_path=tmp_path / "QuillRadio.exe",
        log_path=tmp_path / "apply.log",
        setup_exe=tmp_path / "Setup-3.3.0.exe",
        channel="beta",
        health_marker=tmp_path / "started-3.3.0.ok",
        result_file=tmp_path / "apply-result.json",
        from_version="3.2.0",
        to_version="3.3.0",
        rollback_setup=tmp_path / "rollback" / "Setup-3.2.0.exe",
    )
    assert "started-3.3.0.ok" in script
    assert "if %HEALTH% LSS 120 goto :healthloop" in script
    assert "Setup-3.2.0.exe" in script and '"rolled_back": true' in script


def test_an_installed_copy_with_nothing_kept_cannot_undo() -> None:
    lines = health_lines(
        marker=Path("m.ok"),
        result_file=Path("r.json"),
        from_version="3.2.0",
        to_version="3.3.0",
        relaunch='start "" x',
        portable=False,
        install_dir=Path("app"),
    )
    assert "Start-Process" not in "\n".join(lines)
    assert "nothing to go back to" in "\n".join(lines)


def test_an_apostrophe_in_the_installer_path_is_escaped_for_powershell() -> None:
    """PowerShell ends a single-quoted string at the next quote unless it is
    doubled, so O'Brien's profile folder used to break both installer lines."""
    from quill.core.updater.apply_script import ps_single_quoted

    assert ps_single_quoted("C:/Users/O'Brien/Setup.exe") == "'C:/Users/O''Brien/Setup.exe'"
    folder = Path("C:/Users/O'Brien/AppData/Local/Quill")
    lines = health_lines(
        marker=Path("m.ok"),
        result_file=Path("r.json"),
        from_version="3.2.0",
        to_version="3.3.0",
        relaunch='start "" x',
        portable=False,
        install_dir=Path("app"),
        rollback_setup=folder / "rollback" / "Setup-3.2.0.exe",
    )
    undo = next(line for line in lines if "Start-Process" in line)
    assert f"-FilePath '{str(folder).replace(chr(39), chr(39) * 2)}" in undo
    assert "O'Brien" not in undo.replace("O''Brien", "")
    script = build_apply_update_script(
        pid=7,
        mode="installer",
        install_dir=folder,
        exe_path=folder / "QuillRadio.exe",
        log_path=folder / "apply.log",
        setup_exe=folder / "Setup-3.3.0.exe",
    )
    forward = next(line for line in script.splitlines() if "Start-Process" in line)
    assert "O'Brien" not in forward.replace("O''Brien", "")
    assert "O''Brien" in forward
