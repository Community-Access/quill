"""The watcher decisions both editors share (2026-10-04).

QUILL's watcher kept these in its UI mixin until QUILL Lite gained a watcher of
its own; they moved to :mod:`quill.core.external_change` so the two cannot
answer the same change differently. Real files in a temporary folder, with
modification times set explicitly so nothing depends on the file system's clock
resolution.
"""

from __future__ import annotations

import os
from pathlib import Path
from types import SimpleNamespace

import pytest

from quill.core import external_change as ec
from quill.core.external_change import (
    CHANGE_DELETED,
    CHANGE_MODIFIED,
    CHANGE_NONE,
    REMEMBER_KEEP,
    REMEMBER_RELOAD,
    FileSnapshot,
    ReloadAction,
)


def _write(path: Path, text: str, mtime: int) -> None:
    path.write_bytes(text.encode("utf-8"))
    os.utime(path, ns=(mtime, mtime))


def _settings(**overrides: object) -> SimpleNamespace:
    values: dict[str, object] = {
        "external_change_watch_enabled": True,
        "external_change_auto_reload_when_clean": False,
        "external_change_prompt_on_conflict": True,
        "external_change_always_reload": [],
        "external_change_always_keep": [],
        "external_change_debounce_ms": 750,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


# -- poll_disk: changed, unchanged, touched, deleted, once ---------------------- #


def test_an_untouched_file_is_unchanged_and_never_read(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "plan.md"
    _write(path, "first", 1_000_000_000)
    baseline = FileSnapshot.of(path)
    reads: list[Path] = []
    monkeypatch.setattr(ec, "_hash_file", lambda p, **_k: reads.append(p) or "x")

    assert ec.poll_disk(path, baseline).change == CHANGE_NONE
    assert reads == []  # a stat, and nothing else


def test_new_bytes_are_a_change(tmp_path: Path) -> None:
    path = tmp_path / "plan.md"
    _write(path, "first", 1_000_000_000)
    baseline = FileSnapshot.of(path)
    _write(path, "rewritten", 2_000_000_000)

    poll = ec.poll_disk(path, baseline)
    assert poll.change == CHANGE_MODIFIED
    assert poll.current is not None and poll.current.size == len("rewritten")


def test_a_touch_with_the_same_bytes_is_not_a_change_and_offers_a_new_baseline(
    tmp_path: Path,
) -> None:
    path = tmp_path / "plan.md"
    _write(path, "first", 1_000_000_000)
    baseline = FileSnapshot.of(path)
    os.utime(path, ns=(3_000_000_000, 3_000_000_000))

    poll = ec.poll_disk(path, baseline)
    assert poll.change == CHANGE_NONE
    assert poll.current is not None and poll.current.mtime_ns == 3_000_000_000


def test_one_change_is_reported_once(tmp_path: Path) -> None:
    path = tmp_path / "plan.md"
    _write(path, "first", 1_000_000_000)
    baseline = FileSnapshot.of(path)
    _write(path, "second", 2_000_000_000)
    first = ec.poll_disk(path, baseline)

    again = ec.poll_disk(path, baseline, first.current)
    assert again.change == CHANGE_NONE

    _write(path, "third!", 4_000_000_000)
    assert ec.poll_disk(path, baseline, first.current).change == CHANGE_MODIFIED


def test_a_deleted_file_is_reported_once(tmp_path: Path) -> None:
    path = tmp_path / "plan.md"
    _write(path, "first", 1_000_000_000)
    baseline = FileSnapshot.of(path)
    path.unlink()

    gone = ec.poll_disk(path, baseline)
    assert gone.change == CHANGE_DELETED
    assert ec.poll_disk(path, baseline, gone.current).change == CHANGE_NONE


def test_no_baseline_watches_nothing(tmp_path: Path) -> None:
    assert ec.poll_disk(tmp_path / "x.txt", None).change == CHANGE_NONE


# -- decide_for: reload or ask, read from either editor's settings ------------- #


def test_a_clean_document_is_asked_about_by_default() -> None:
    decision = ec.decide_for(CHANGE_MODIFIED, _settings(), buffer_dirty=False, file_name="plan.md")
    assert decision.action is ReloadAction.PROMPT_CLEAN


def test_reload_when_clean_reloads_a_clean_document_and_asks_about_a_dirty_one() -> None:
    settings = _settings(external_change_auto_reload_when_clean=True)
    clean = ec.decide_for(CHANGE_MODIFIED, settings, buffer_dirty=False, file_name="plan.md")
    dirty = ec.decide_for(CHANGE_MODIFIED, settings, buffer_dirty=True, file_name="plan.md")
    assert clean.action is ReloadAction.RELOAD
    assert dirty.action is ReloadAction.PROMPT_CONFLICT


def test_do_not_ask_again_is_honoured_for_that_format_only() -> None:
    settings = _settings(external_change_always_keep=[".docx"])
    kept = ec.decide_for(CHANGE_MODIFIED, settings, buffer_dirty=False, file_name="r.DOCX")
    other = ec.decide_for(CHANGE_MODIFIED, settings, buffer_dirty=False, file_name="r.md")
    assert kept.action is ReloadAction.KEEP_MINE
    assert other.action is ReloadAction.PROMPT_CLEAN


def test_watching_off_does_nothing_and_a_deletion_is_never_reloaded() -> None:
    off = _settings(external_change_watch_enabled=False)
    assert (
        ec.decide_for(CHANGE_MODIFIED, off, buffer_dirty=False, file_name="a.md").action
        is ReloadAction.NONE
    )
    remembered = _settings(external_change_always_reload=[".md"])
    assert (
        ec.decide_for(CHANGE_DELETED, remembered, buffer_dirty=False, file_name="a.md").action
        is ReloadAction.PROMPT_DELETED
    )


# -- the kept answers ---------------------------------------------------------- #


def test_remembering_moves_a_format_between_the_lists() -> None:
    settings = _settings()
    assert ec.remember_answer(settings, "notes.md", REMEMBER_RELOAD)
    assert ec.remembered_for(settings, "other.MD") == REMEMBER_RELOAD
    assert ec.remember_answer(settings, "notes.md", REMEMBER_KEEP)
    assert settings.external_change_always_reload == []
    assert settings.external_change_always_keep == [".md"]


def test_nothing_to_remember_records_nothing() -> None:
    settings = _settings()
    assert not ec.remember_answer(settings, "notes.md", "")
    assert not ec.remember_answer(settings, "Makefile", REMEMBER_RELOAD)
    assert settings.external_change_always_reload == []


def test_forgetting_counts_and_says_so_in_the_apps_name() -> None:
    settings = _settings(
        external_change_always_reload=[".md"], external_change_always_keep=[".docx"]
    )
    assert ec.forget_answers(settings) == 2
    assert settings.external_change_always_reload == []
    assert ec.forget_answers_sentence(2, "QUILL Lite").startswith("Forgot 2 remembered")
    assert "QUILL Lite will ask again" in ec.forget_answers_sentence(2, "QUILL Lite")
    assert ec.forget_answers_sentence(0, "QUILL") == "No file formats are being answered for you."


def test_the_poll_interval_never_spins() -> None:
    assert ec.poll_interval_ms(_settings(external_change_debounce_ms=0)) == 100
    assert ec.poll_interval_ms(_settings()) == 750


def test_the_sentences_name_the_file() -> None:
    assert ec.reloaded_sentence("plan.md") == "Reloaded plan.md: changed by another program."
    assert "plan.md" in ec.deleted_sentence("plan.md")


# -- QUILL Lite stores the same six fields, under the same names --------------- #


def test_lite_settings_carry_quills_six_fields() -> None:
    from quill.core.lite.settings import Settings as LiteSettings
    from quill.core.settings import Settings as QuillSettings

    names = [
        "external_change_watch_enabled",
        "external_change_auto_reload_when_clean",
        "external_change_prompt_on_conflict",
        "external_change_always_reload",
        "external_change_always_keep",
        "external_change_debounce_ms",
    ]
    lite, quill = LiteSettings(), QuillSettings()
    for name in names:
        assert getattr(lite, name) == getattr(quill, name), name


def test_lite_settings_round_trip_and_clean_the_lists(tmp_path: Path) -> None:
    from quill.core.lite import settings as lite_settings

    target = tmp_path / "settings.json"
    settings = lite_settings.Settings()
    settings.external_change_always_keep = ["DOCX", ".docx", "md"]
    settings.external_change_auto_reload_when_clean = True
    lite_settings.save(settings, target)

    loaded = lite_settings.load(target)
    assert loaded.external_change_always_keep == [".docx", ".md"]
    assert loaded.external_change_auto_reload_when_clean is True
