"""Component reference counting -- dedup/GC of the shared component store."""

from __future__ import annotations

from pathlib import Path

from quill.core import components as c


def test_two_apps_share_one_component(tmp_path: Path) -> None:
    c.register(tmp_path, "radio", ["ffmpeg", "mpv"])
    c.register(tmp_path, "cast", ["ffmpeg"])
    assert c.apps_requiring(tmp_path, "ffmpeg") == ["cast", "radio"]  # deduped, sorted
    assert c.apps_requiring(tmp_path, "mpv") == ["radio"]
    assert c.is_referenced(tmp_path, "ffmpeg")


def test_register_is_idempotent_and_drops_stale_refs(tmp_path: Path) -> None:
    c.register(tmp_path, "radio", ["ffmpeg", "mpv"])
    c.register(tmp_path, "radio", ["ffmpeg", "mpv"])  # re-launch: no change
    assert c.apps_requiring(tmp_path, "mpv") == ["radio"]
    c.register(tmp_path, "radio", ["ffmpeg"])  # radio no longer needs mpv
    assert c.apps_requiring(tmp_path, "mpv") == []
    assert not c.is_referenced(tmp_path, "mpv")


def test_unregister_removes_all_of_an_apps_refs(tmp_path: Path) -> None:
    c.register(tmp_path, "radio", ["ffmpeg", "mpv"])
    c.register(tmp_path, "cast", ["ffmpeg"])
    c.unregister(tmp_path, "radio")  # e.g. the radio uninstaller
    assert c.apps_requiring(tmp_path, "ffmpeg") == ["cast"]  # cast still needs it
    assert c.apps_requiring(tmp_path, "mpv") == []  # nothing needs mpv now


def test_unreferenced_lists_only_gc_candidates(tmp_path: Path) -> None:
    c.register(tmp_path, "radio", ["ffmpeg"])
    assert c.unreferenced(tmp_path, ["ffmpeg", "mpv", "whisper"]) == ["mpv", "whisper"]


def test_state_persists_and_stays_tidy(tmp_path: Path) -> None:
    c.register(tmp_path, "radio", ["ffmpeg"])
    assert (tmp_path / "components.state.json").is_file()
    assert c.apps_requiring(tmp_path, "ffmpeg") == ["radio"]  # a fresh read sees it
    c.unregister(tmp_path, "radio")
    # the file drops empty components rather than accreting junk
    import json

    payload = json.loads((tmp_path / "components.state.json").read_text(encoding="utf-8"))
    assert payload == {"refs": {}}
