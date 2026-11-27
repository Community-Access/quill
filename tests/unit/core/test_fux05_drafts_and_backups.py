"""FUX-05: drafts, the Inkwell library and Beacon snapshots say what they are.

Each test fails without the change it names: a recovered draft named only by
its repository, a draft file read as empty and saved over, a stale line
comment that a rewrite left stale, an Inkwell library replaced by the defaults
with nothing kept, and a Beacon rollback that could not be undone.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

from quill.apps.beacon import sync_snapshots
from quill.apps.beacon.db import BeaconStore
from quill.apps.beacon.model import Beacon, Resource
from quill.apps.beacon.sync_ui import SyncConfig, SyncController
from quill.core import settings_recovery
from quill.core.abbreviations import load_abbreviation_library
from quill.core.github import local_drafts
from quill.core.github.diff_lines import LineCommentAnchor
from quill.core.github.line_comment_drafts import LineCommentDraftStore
from quill.core.github.local_drafts import (
    GitHubIssueDraftData,
    GitHubIssueDraftStore,
    GitHubReviewDraftData,
    damaged_drafts_notice,
    recovered_issue_notice,
    recovered_review_notice,
)

_NOW = datetime(2026, 11, 24, 15, 0, tzinfo=UTC)


def _fresh_launch() -> None:
    settings_recovery._forget()


# -- GitHub issue and review drafts -------------------------------------------------


def test_recovered_issue_names_title_size_and_when() -> None:
    draft = GitHubIssueDraftData(
        title="Crash on save",
        body="Open a file and press save twice",
        updated_at=_NOW.replace(hour=14).isoformat(),
    )
    said = recovered_issue_notice(draft, "owner/repo", now=_NOW)
    assert said.startswith('Recovered your unsent issue for owner/repo, "Crash on save", 7 words')
    assert "saved today at" in said
    assert said.endswith("It has not been submitted.")


def test_untitled_issue_draft_is_named_by_its_opening_words() -> None:
    draft = GitHubIssueDraftData(body="The export drops every footnote")
    said = recovered_issue_notice(draft, "owner/repo", now=_NOW)
    assert 'beginning "The export drops every footnote"' in said


def test_stale_review_draft_says_the_pull_request_moved_and_when() -> None:
    draft = GitHubReviewDraftData(
        event="request changes",
        body="Please check the guard",
        head_sha="aaaaaaa1111",
        updated_at=_NOW.isoformat(),
    )
    said = recovered_review_notice(draft, 7, "bbbbbbb2222", now=_NOW)
    assert "pull request #7: a request for changes of 4 words, saved today at" in said
    assert "new commits since you wrote it" in said
    assert "aaaaaaa" not in said  # no commit ids read aloud
    assert said.endswith("It has not been submitted.")


def test_damaged_draft_file_is_kept_and_said_once(tmp_path: Path, monkeypatch) -> None:
    _fresh_launch()
    monkeypatch.setattr(local_drafts, "app_data_dir", lambda: tmp_path)
    damaged = tmp_path / "github_local_drafts.json"
    damaged.write_text("{not json", encoding="utf-8")

    store = GitHubIssueDraftStore.load("account-token")
    assert store.save_issue("owner/repo", title="New", body="", labels=(), assignees=())

    kept = list(tmp_path.glob("github_local_drafts.damaged-*.json"))
    assert len(kept) == 1
    assert kept[0].read_text(encoding="utf-8") == "{not json"
    said = damaged_drafts_notice()
    assert "could not be read" in said and kept[0].name in said
    assert damaged_drafts_notice() == ""  # once


def test_damaged_draft_file_that_cannot_be_kept_is_not_written_over(
    tmp_path: Path, monkeypatch
) -> None:
    _fresh_launch()
    monkeypatch.setattr(local_drafts, "app_data_dir", lambda: tmp_path)
    damaged = tmp_path / "github_local_drafts.json"
    damaged.write_text("{not json", encoding="utf-8")
    monkeypatch.setattr(settings_recovery, "keep_damaged", lambda *_a, **_k: None)

    store = GitHubIssueDraftStore.load("account-token")
    assert not store.save_issue("owner/repo", title="New", body="", labels=(), assignees=())
    assert damaged.read_text(encoding="utf-8") == "{not json"


# -- pending line comments ----------------------------------------------------------


def test_rewriting_a_stale_line_comment_moves_it_to_the_current_head(tmp_path: Path) -> None:
    store = LineCommentDraftStore.load("token", tmp_path / "comments.json")
    anchor = LineCommentAnchor(path="a.py", line=3, side="RIGHT")
    comment = store.add("owner/repo", 5, anchor, "First thought", "oldhead")
    assert comment is not None

    assert store.update("owner/repo", 5, comment.id, "Second thought", head_sha="newhead")
    (rewritten,) = store.pending("owner/repo", 5)
    assert rewritten.body == "Second thought"
    assert rewritten.head_sha == "newhead"

    assert store.update("owner/repo", 5, comment.id, "Third thought")
    assert store.pending("owner/repo", 5)[0].head_sha == "newhead"


# -- Inkwell's library --------------------------------------------------------------


def test_damaged_abbreviation_library_is_kept_and_named(tmp_path: Path) -> None:
    _fresh_launch()
    (tmp_path / "abbreviations.json").write_text("not json{{{", encoding="utf-8")

    loaded = load_abbreviation_library(tmp_path)

    assert loaded.abbreviations  # the built-in defaults, never an empty library
    kept = list(tmp_path.glob("abbreviations.damaged-*.json"))
    assert len(kept) == 1
    assert kept[0].read_text(encoding="utf-8") == "not json{{{"
    said = settings_recovery.take_notice("Quill Inkwell")
    assert said.startswith("Your abbreviation library could not be read")
    assert kept[0].name in said


def test_readable_library_says_nothing(tmp_path: Path) -> None:
    _fresh_launch()
    (tmp_path / "abbreviations.json").write_text(
        json.dumps({"version": 2, "abbreviations": []}), encoding="utf-8"
    )
    load_abbreviation_library(tmp_path)
    assert settings_recovery.take_notice("Quill Inkwell") == ""
    assert not list(tmp_path.glob("abbreviations.damaged-*.json"))


# -- Beacon's snapshots -------------------------------------------------------------


def _beacon(tmp_path: Path) -> tuple[BeaconStore, SyncController]:
    store = BeaconStore(str(tmp_path / "beacons.db"))
    return store, SyncController(store, tmp_path)


def _seed(store: BeaconStore, title: str) -> None:
    res = Resource(title=title, type="web", primary_uri=f"https://x/{title}")
    store.put_beacon(Beacon(resource_id=res.resource_id, title=title, in_inbox=False), resource=res)


def test_snapshot_rows_say_when_and_how_big() -> None:
    now = datetime(2026, 11, 24, 15, 0)
    stamp = int(datetime(2026, 11, 24, 14, 5).timestamp() * 1000)
    row = {"name": f"sync_{stamp}.db", "created": stamp, "size": 1_250_000}
    assert sync_snapshots.snapshot_label(row, now) == "Today at 2:05 PM, before a sync, 1.2 MB"
    back = {"name": f"rollback_{stamp}.db", "created": stamp, "size": 900}
    assert (
        sync_snapshots.snapshot_label(back, now) == "Today at 2:05 PM, before a rollback, 900 bytes"
    )
    assert "kept as a snapshot first" in sync_snapshots.confirm_rollback(row, now)


def test_rollback_keeps_the_library_it_replaces(tmp_path: Path) -> None:
    store, ctrl = _beacon(tmp_path)
    ctrl.save_config(SyncConfig(transport="folder", folder=str(tmp_path / "r"), device="d"))
    ctrl.setup_vault("p")
    _seed(store, "Before")
    backup = ctrl.sync_now()["backup"]
    _seed(store, "After")
    store.close()

    assert ctrl.restore_backup(backup)

    kept = [b for b in ctrl.list_backups() if b["name"].startswith("rollback_")]
    assert len(kept) == 1
    # The kept library is the one with "After" in it: the rollback can be undone.
    assert ctrl.restore_backup(kept[0]["name"])
    reopened = BeaconStore(str(tmp_path / "beacons.db"))
    assert "After" in [b.title for b in reopened.list_beacons()]
    reopened.close()


def test_rollback_that_cannot_keep_the_library_does_not_overwrite_it(
    tmp_path: Path, monkeypatch
) -> None:
    store, ctrl = _beacon(tmp_path)
    ctrl.save_config(SyncConfig(transport="folder", folder=str(tmp_path / "r"), device="d"))
    ctrl.setup_vault("p")
    _seed(store, "Before")
    backup = ctrl.sync_now()["backup"]
    _seed(store, "After")
    store.close()
    monkeypatch.setattr(sync_snapshots, "keep_before_rollback", lambda *_a: None)

    assert ctrl.restore_backup(backup) is False

    reopened = BeaconStore(str(tmp_path / "beacons.db"))
    assert "After" in [b.title for b in reopened.list_beacons()]
    reopened.close()
    assert "not rolled back" in sync_snapshots.rollback_failed()


def test_export_then_import_brings_every_per_entry_setting_back(
    tmp_path: Path, monkeypatch
) -> None:
    from quill.core.abbreviations import Abbreviation, AbbreviationLibrary
    from quill.ui import abbreviation_transfer as transfer

    entry = Abbreviation(
        id="teh",
        abbreviation="teh",
        expansion="the",
        category="AutoCorrect",
        speak_mode="expansion",
        sound="off",
        trailing_space=True,
        triggers="space",
        apps=("winword",),
    )
    target = tmp_path / "backup.json"
    monkeypatch.setattr(transfer, "_choose", lambda *_a, **_k: target)
    monkeypatch.setattr(transfer, "_error", lambda *_a: None)
    host = SimpleNamespace(_announce=lambda *_a, **_k: None)  # said, not a message box
    transfer.export_abbreviations(None, AbbreviationLibrary(version=2, abbreviations=[entry]), host)

    empty = AbbreviationLibrary(version=2, abbreviations=[])
    incoming = json.loads(target.read_text(encoding="utf-8"))["abbreviations"]
    assert transfer.merge_imported(empty, incoming).added == 1
    (back,) = empty.abbreviations
    assert (back.category, back.speak_mode, back.sound) == ("AutoCorrect", "expansion", "off")
    assert (back.trailing_space, back.triggers, back.apps) == (True, "space", ("winword",))


def test_rollback_outcome_picks_the_right_sentence() -> None:
    from quill.apps.beacon import sync_snapshots

    assert sync_snapshots.rollback_outcome({}, "b1", False) == sync_snapshots.rollback_failed()
    said = sync_snapshots.rollback_outcome({}, "beacons-1700000000000-sync.db", True)
    assert said.startswith("Rolled the library back")
