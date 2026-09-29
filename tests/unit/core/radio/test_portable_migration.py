"""A new portable copy can bring an earlier copy's favorites (2026-09-26).

Quill Radio 2.x kept its data in the computer's profile even when run from the
portable zip; 3.0's portable copy keeps its own. These tests hold the rules:
offer only when there is something to bring and nowhere for it yet, copy
without ever touching the earlier copy, never overwrite, and ask once.
"""

from __future__ import annotations

from pathlib import Path

import pytest  # type: ignore[import-not-found]

from quill.core.radio import portable_migration as pm
from quill.core.radio.favorites import (
    FavoriteStation,
    RadioFavoritesStore,
    load_favorites,
    save_favorites,
)
from quill.core.radio.models import RadioStation


def _favorites(folder: Path, *names: str) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    store = RadioFavoritesStore(
        favorites=[
            FavoriteStation(station=RadioStation(name=n, stream_url=f"https://s/{n}"))
            for n in names
        ]
    )
    save_favorites(folder, store)


@pytest.fixture
def dirs(tmp_path: Path) -> tuple[Path, Path]:
    profile = tmp_path / "AppData" / "Quill"
    bundle = tmp_path / "stick" / "QuillRadio" / "data"
    bundle.mkdir(parents=True)
    return profile, bundle


def test_offered_when_the_profile_has_favorites_and_the_bundle_has_none(dirs) -> None:
    profile, bundle = dirs
    _favorites(profile, "WQXR", "KUSC")

    earlier = pm.find_earlier_data(bundle, profile)

    assert earlier is not None and earlier.favorites == 2


def test_not_offered_when_the_bundle_already_has_favorites(dirs) -> None:
    profile, bundle = dirs
    _favorites(profile, "WQXR")
    _favorites(bundle, "Mine")

    assert pm.find_earlier_data(bundle, profile) is None


def test_not_offered_when_there_is_nothing_to_bring(dirs) -> None:
    profile, bundle = dirs
    profile.mkdir(parents=True)

    assert pm.find_earlier_data(bundle, profile) is None
    assert pm.find_earlier_data(bundle, None) is None


def test_copy_brings_the_files_and_leaves_the_earlier_copy_alone(dirs) -> None:
    profile, bundle = dirs
    _favorites(profile, "WQXR", "KUSC")
    (profile / "radio_history.json").write_text('{"volume": 40}', encoding="utf-8")
    before = {p.name: p.read_bytes() for p in profile.iterdir()}

    copied = pm.copy_earlier_data(pm.find_earlier_data(bundle, profile), bundle)

    assert set(copied) == {"radio_favorites.json", "radio_history.json"}
    assert [f.station.name for f in load_favorites(bundle).favorites] == ["WQXR", "KUSC"]
    assert {p.name: p.read_bytes() for p in profile.iterdir()} == before
    assert not list(bundle.glob("*.copying"))


def test_copy_never_overwrites_what_the_bundle_has(dirs) -> None:
    profile, bundle = dirs
    _favorites(profile, "WQXR")
    (profile / "radio_history.json").write_text('{"volume": 40}', encoding="utf-8")
    (bundle / "radio_history.json").write_text('{"volume": 90}', encoding="utf-8")

    copied = pm.copy_earlier_data(pm.find_earlier_data(bundle, profile), bundle)

    assert "radio_history.json" not in copied
    assert (bundle / "radio_history.json").read_text(encoding="utf-8") == '{"volume": 90}'


def test_copy_replaces_a_favorites_file_that_has_no_favorites(dirs) -> None:
    """The offer exists because the bundle has none; a file with none in it is
    not "something the bundle has" (C:\qr, 2026-09-28: Yes did nothing)."""
    profile, bundle = dirs
    _favorites(profile, "WQXR")
    _favorites(bundle)  # a 3.0.0 bundle opened once: a favorites file, empty
    earlier = pm.find_earlier_data(bundle, profile)
    assert earlier is not None  # still offered

    copied = pm.copy_earlier_data(earlier, bundle)

    assert "radio_favorites.json" in copied
    assert [f.station.name for f in load_favorites(bundle).favorites] == ["WQXR"]


@pytest.mark.parametrize("copied", [True, False])
def test_the_question_is_asked_once(dirs, copied) -> None:
    profile, bundle = dirs
    _favorites(profile, "WQXR")

    pm.remember_answer(bundle, copied=copied)

    assert pm.find_earlier_data(bundle, profile) is None


def test_the_profile_is_found_under_appdata(tmp_path: Path) -> None:
    (tmp_path / "Quill").mkdir()

    assert pm.host_profile_dir({"APPDATA": str(tmp_path)}) == tmp_path / "Quill"
    assert pm.host_profile_dir({"APPDATA": str(tmp_path / "missing")}) is None
    assert pm.host_profile_dir({}) is None


# -- the offer itself ----------------------------------------------------------


@pytest.fixture
def portable(monkeypatch, dirs):
    import quill.core.paths as paths

    profile, bundle = dirs
    monkeypatch.setattr(paths, "portable_bundle_root", lambda: bundle.parent)
    monkeypatch.setattr(paths, "app_data_dir", lambda: bundle)
    monkeypatch.setattr(pm, "host_profile_dir", lambda: profile)
    return profile, bundle


def _answer(monkeypatch, reply: str) -> list[str]:
    wx = pytest.importorskip("wx")
    import quill.ui.dialog_contract as contract

    asked: list[str] = []

    def _box(message, _caption, style, *_a, **_k):
        asked.append(message)
        assert not style & wx.NO_DEFAULT  # Enter brings them (YES_DEFAULT is 0)
        return getattr(wx, reply)

    monkeypatch.setattr(contract, "show_message_box", _box)
    return asked


def test_yes_copies_and_is_remembered(monkeypatch, portable) -> None:
    from quill.ui.radio.portable_migration_ui import offer_earlier_favorites

    profile, bundle = portable
    _favorites(profile, "WQXR", "KUSC")
    asked = _answer(monkeypatch, "YES")

    offer_earlier_favorites()
    offer_earlier_favorites()

    assert len(asked) == 1 and "2 favorite stations" in asked[0]
    assert len(load_favorites(bundle).favorites) == 2


def test_no_starts_empty_and_is_remembered(monkeypatch, portable) -> None:
    from quill.ui.radio.portable_migration_ui import offer_earlier_favorites

    profile, bundle = portable
    _favorites(profile, "WQXR")
    asked = _answer(monkeypatch, "NO")

    offer_earlier_favorites()
    offer_earlier_favorites()

    assert len(asked) == 1
    assert load_favorites(bundle).favorites == []


def test_an_installed_copy_is_never_asked(monkeypatch, dirs) -> None:
    import quill.core.paths as paths
    from quill.ui.radio.portable_migration_ui import offer_earlier_favorites

    monkeypatch.setattr(paths, "portable_bundle_root", lambda: None)
    asked = _answer(monkeypatch, "YES")

    offer_earlier_favorites()

    assert asked == []
