"""Two QUILL Lites, one settings file (qc.md F-11).

``--new-instance`` runs two processes against the same settings file. Each used
to write its whole in-memory copy, so the last to save undid every preference
the other had changed. A save is now a three-way merge, field by field: what
this process changed since it loaded wins; everything else keeps what is on
disk.

The first group drives the pure merge; the second runs two real persistence
objects against one real file, which is the failure as a listener met it.
"""

from __future__ import annotations

import copy
from pathlib import Path

import pytest

from quill.apps import lite_settings_persistence as persistence
from quill.core.lite import settings as settings_mod
from quill.core.lite import settings_merge
from quill.core.lite.settings import Settings

# -- the merge -------------------------------------------------------------------- #


def test_a_field_we_changed_wins_and_a_field_we_did_not_keeps_the_disk_value() -> None:
    baseline = Settings()
    ours = copy.deepcopy(baseline)
    ours.word_wrap = not baseline.word_wrap  # we changed this
    disk = copy.deepcopy(baseline)
    disk.theme = "dark" if baseline.theme != "dark" else "system"  # the other one changed this
    merged = settings_merge.merge_for_save(baseline, ours, disk)
    assert merged.word_wrap == ours.word_wrap
    assert merged.theme == disk.theme


def test_when_both_changed_one_field_the_one_saving_now_wins() -> None:
    baseline = Settings()
    ours = copy.deepcopy(baseline)
    ours.theme = "dark"
    disk = copy.deepcopy(baseline)
    disk.theme = "system" if baseline.theme == "dark" else baseline.theme
    merged = settings_merge.merge_for_save(baseline, ours, disk)
    assert merged.theme == "dark"


def test_the_merge_does_not_alias_our_objects() -> None:
    baseline = Settings()
    ours = copy.deepcopy(baseline)
    ours.recent_files = ["C:/a.txt"]
    merged = settings_merge.merge_for_save(baseline, ours, copy.deepcopy(baseline))
    merged.recent_files.append("C:/b.txt")
    assert ours.recent_files == ["C:/a.txt"]


def test_no_readable_file_means_nothing_to_merge_with(tmp_path: Path) -> None:
    assert settings_merge.load_if_present(tmp_path / "missing.json") is None
    corrupt = tmp_path / "corrupt.json"
    corrupt.write_text("{not json", encoding="utf-8")
    assert settings_merge.load_if_present(corrupt) is None
    good = tmp_path / "good.json"
    settings_mod.save(Settings(word_wrap=False), good)
    loaded = settings_merge.load_if_present(good)
    assert loaded is not None and loaded.word_wrap is False


# -- two instances, one file ------------------------------------------------------- #


class _App(persistence.LiteSettingsPersistenceMixin):
    shutting_down = False
    frames: list = []

    def __init__(self) -> None:
        self.settings = settings_mod.load()
        self._settings_baseline = copy.deepcopy(self.settings)
        self.voice = type("V", (), {"speak": lambda _self, _m: None})()


@pytest.fixture
def shared_file(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    target = tmp_path / "settings.json"
    monkeypatch.setattr(settings_mod, "settings_path", lambda: target)
    monkeypatch.setattr(settings_merge, "settings_path", lambda: target)
    return target


def test_the_second_instance_no_longer_undoes_the_first(shared_file: Path) -> None:
    first, second = _App(), _App()
    first.settings.word_wrap = not first.settings.word_wrap
    assert first.save_settings()
    wanted_wrap = first.settings.word_wrap
    second.settings.theme = "dark" if second.settings.theme != "dark" else "system"
    assert second.save_settings()
    on_disk = settings_mod.load(shared_file)
    assert on_disk.word_wrap == wanted_wrap  # first's change survived second's save
    assert on_disk.theme == second.settings.theme


def test_a_running_instance_is_not_changed_under_the_listener(shared_file: Path) -> None:
    first, second = _App(), _App()
    second.settings.theme = "dark" if second.settings.theme != "dark" else "system"
    second.save_settings()
    before = first.settings.theme
    first.settings.word_wrap = not first.settings.word_wrap
    first.save_settings()
    assert first.settings.theme == before  # in memory: untouched
    assert settings_mod.load(shared_file).theme == second.settings.theme  # on disk: kept


def test_without_a_baseline_the_save_is_the_old_whole_object_write(shared_file: Path) -> None:
    app = _App()
    del app._settings_baseline
    app.settings.word_wrap = not app.settings.word_wrap
    assert app.save_settings()
    assert settings_mod.load(shared_file).word_wrap == app.settings.word_wrap
