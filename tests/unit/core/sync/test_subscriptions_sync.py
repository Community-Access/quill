"""ear.md B3: subscriptions and folders through Listening Places (sync.md 6.7)."""

from __future__ import annotations

import json
from pathlib import Path

from quill.core.podcasts.models import PodcastFolder, PodcastShow
from quill.core.podcasts.subscriptions import PodcastLibrary
from quill.core.sync import listening_places as lp
from quill.core.sync.places_interchange import sync_interchange
from quill.core.sync.subscriptions_sync import canonical_url, is_private, subscription_id

FEED = "https://feeds.example.com/blindabilities"


def _sync(tmp: Path, name: str, device: str, library: PodcastLibrary, *, share: bool = True):
    return sync_interchange(
        data_dir=tmp / name,
        remote_dir=tmp / "remote",
        device_id=device,
        device_label=name,
        library=library,
        save_library=lambda _library: None,
        share_subscriptions=share,
    )


def _rows(tmp: Path, device: str) -> list[dict]:
    path = lp.device_file_path(tmp / "remote", device)
    return json.loads(path.read_text(encoding="utf-8"))["records"]


def _desk() -> PodcastLibrary:
    library = PodcastLibrary()
    library.folders.append(PodcastFolder(id="news", name="News"))
    show = PodcastShow(id="ba", title="Blind Abilities", feed_url=FEED, folder_id="news")
    library.shows.append(show)
    library.apply_show_override(show, speed=1.4)
    return library


def _setup(tmp: Path) -> None:
    (tmp / "remote").mkdir()
    (tmp / "desk").mkdir()
    (tmp / "laptop").mkdir()


def test_canonical_url_follows_the_proposal() -> None:
    assert canonical_url("HTTPS://Feeds.Example.com:443/Show/?a=1#x") == (
        "https://feeds.example.com/Show?a=1"
    )
    assert subscription_id("https://feeds.example.com/x/") == subscription_id(
        "https://FEEDS.example.com/x"
    )


def test_a_follow_and_its_folder_and_speed_reach_the_other_device(tmp_path: Path) -> None:
    _setup(tmp_path)
    _sync(tmp_path, "desk", "aaaaaaaa", _desk())
    laptop = PodcastLibrary()
    report = _sync(tmp_path, "laptop", "bbbbbbbb", laptop)
    assert [s.feed_url for s in laptop.shows] == [FEED]
    show = laptop.shows[0]
    assert laptop.find_folder(show.folder_id).name == "News"
    assert laptop.effective_settings(show).speed == 1.4
    assert "Now following Blind Abilities, added on desk." in report.summary()


def test_nothing_about_subscriptions_is_written_unless_asked(tmp_path: Path) -> None:
    _setup(tmp_path)
    _sync(tmp_path, "desk", "aaaaaaaa", _desk(), share=False)
    assert not lp.device_file_path(tmp_path / "remote", "aaaaaaaa").exists() or not [
        row for row in _rows(tmp_path, "aaaaaaaa") if str(row.get("id")).startswith("sub:")
    ]


def test_a_private_feed_never_goes_in_the_plain_file(tmp_path: Path) -> None:
    _setup(tmp_path)
    library = _desk()
    library.shows.append(
        PodcastShow(id="paid", title="Paid", feed_url="https://x.example.com/f?token=abc")
    )
    assert is_private(library.shows[-1])
    report = _sync(tmp_path, "desk", "aaaaaaaa", library)
    written = json.dumps(_rows(tmp_path, "aaaaaaaa"))
    assert "token=abc" not in written
    assert "1 private feed stayed on this device." in report.summary()


def test_what_cast_cannot_hold_is_carried_back_untouched(tmp_path: Path) -> None:
    _setup(tmp_path)
    phone = {
        "format": "listening-places/1",
        "device": "cccccccc",
        "app": "earshot/1.3.0",
        "written_at": "2026-10-03T10:00:00Z",
        "records": [
            {
                "id": "folder:11111111",
                "kind": "folder",
                "name": "News",
                "updated_at": "2026-10-03T10:00:00Z",
                "sortOrder": 2,
            },
            {
                "id": "folder:22222222",
                "kind": "folder",
                "name": "Tech",
                "updated_at": "2026-10-03T10:00:00Z",
            },
            {
                "id": subscription_id(FEED),
                "kind": "subscription",
                "feed_url": FEED,
                "title": "Blind Abilities",
                "updated_at": "2026-10-03T10:00:00Z",
                "folders": ["folder:11111111", "folder:22222222"],
                "app_private": {"earshot": {"autoQueue": True}},
            },
        ],
    }
    devices = lp.devices_dir(tmp_path / "remote")
    devices.mkdir(parents=True)
    (devices / "cccccccc.json").write_text(json.dumps(phone), encoding="utf-8")
    laptop = PodcastLibrary()
    _sync(tmp_path, "laptop", "bbbbbbbb", laptop)
    assert laptop.find_folder(laptop.shows[0].folder_id).name == "News"
    sub = next(r for r in _rows(tmp_path, "bbbbbbbb") if r["id"] == subscription_id(FEED))
    assert sub["folders"][1] == "folder:22222222"
    assert sub["app_private"]["earshot"] == {"autoQueue": True}
    folder = next(r for r in _rows(tmp_path, "bbbbbbbb") if r["id"] == "folder:11111111")
    assert folder["sortOrder"] == 2


def test_unfollowing_reaches_the_other_device_and_is_named(tmp_path: Path) -> None:
    _setup(tmp_path)
    desk = _desk()
    _sync(tmp_path, "desk", "aaaaaaaa", desk)
    laptop = PodcastLibrary()
    _sync(tmp_path, "laptop", "bbbbbbbb", laptop)
    desk.remove_show("ba")
    _sync(tmp_path, "desk", "aaaaaaaa", desk)
    tombstone = next(r for r in _rows(tmp_path, "aaaaaaaa") if r["id"] == subscription_id(FEED))
    assert tombstone["deleted"] is True
    report = _sync(tmp_path, "laptop", "bbbbbbbb", laptop)
    assert laptop.shows == []
    assert "Stopped following Blind Abilities, removed on desk." in report.summary()


def test_an_old_unfollow_does_not_undo_a_new_follow(tmp_path: Path) -> None:
    _setup(tmp_path)
    old = {
        "format": "listening-places/1",
        "device": "cccccccc",
        "app": "earshot/1.3.0",
        "written_at": "2020-01-01T00:00:00Z",
        "records": [
            {"id": subscription_id(FEED), "deleted": True, "updated_at": "2020-01-01T00:00:00Z"}
        ],
    }
    devices = lp.devices_dir(tmp_path / "remote")
    devices.mkdir(parents=True)
    (devices / "cccccccc.json").write_text(json.dumps(old), encoding="utf-8")
    desk = _desk()
    _sync(tmp_path, "desk", "aaaaaaaa", desk)
    _sync(tmp_path, "desk", "aaaaaaaa", desk)
    assert [s.id for s in desk.shows] == ["ba"]


# -- what another device may change here (ear.md 6.9) -----------------------------


def _sync_with(tmp: Path, name: str, device: str, library: PodcastLibrary, policy):
    return sync_interchange(
        data_dir=tmp / name,
        remote_dir=tmp / "remote",
        device_id=device,
        device_label=name,
        library=library,
        save_library=lambda _library: None,
        share_subscriptions=True,
        subscription_policy=policy,
    )


def test_suggest_names_a_new_follow_once_and_does_not_add_it(tmp_path: Path) -> None:
    from quill.core.sync.subscriptions_sync import SubscriptionPolicy

    _setup(tmp_path)
    _sync(tmp_path, "desk", "aaaaaaaa", _desk())
    laptop = PodcastLibrary()
    rules = SubscriptionPolicy(follow_new="suggest")
    first = _sync_with(tmp_path, "laptop", "bbbbbbbb", laptop, rules)
    assert laptop.shows == []
    assert "Blind Abilities is followed on desk" in first.summary()
    again = _sync_with(tmp_path, "laptop", "bbbbbbbb", laptop, rules)
    assert "Blind Abilities is followed on desk" not in again.summary()  # said once


def test_keep_names_an_unfollow_once_and_keeps_the_podcast(tmp_path: Path) -> None:
    from quill.core.sync.subscriptions_sync import SubscriptionPolicy

    _setup(tmp_path)
    desk = _desk()
    _sync(tmp_path, "desk", "aaaaaaaa", desk)
    laptop = PodcastLibrary()
    _sync(tmp_path, "laptop", "bbbbbbbb", laptop)
    assert len(laptop.shows) == 1
    desk.remove_show("ba")
    _sync(tmp_path, "desk", "aaaaaaaa", desk)
    rules = SubscriptionPolicy(unfollows="keep")
    report = _sync_with(tmp_path, "laptop", "bbbbbbbb", laptop, rules)
    assert len(laptop.shows) == 1
    assert "still followed here" in report.summary()
    again = _sync_with(tmp_path, "laptop", "bbbbbbbb", laptop, rules)
    assert "still followed here" not in again.summary()


def test_folders_off_keeps_folders_on_this_device(tmp_path: Path) -> None:
    from quill.core.sync.subscriptions_sync import SubscriptionPolicy

    _setup(tmp_path)
    _sync_with(tmp_path, "desk", "aaaaaaaa", _desk(), SubscriptionPolicy(folders=False))
    rows = _rows(tmp_path, "aaaaaaaa")
    assert not [r for r in rows if str(r.get("id", "")).startswith("folder:")]
    sub = next(r for r in rows if str(r.get("id", "")).startswith("sub:"))
    assert sub["folders"] == []
    laptop = PodcastLibrary()
    _sync_with(tmp_path, "laptop", "bbbbbbbb", laptop, SubscriptionPolicy(folders=False))
    assert laptop.shows[0].folder_id in (None, "")


def test_speed_off_neither_sends_nor_takes_a_speed(tmp_path: Path) -> None:
    from quill.core.sync.subscriptions_sync import SubscriptionPolicy

    _setup(tmp_path)
    _sync(tmp_path, "desk", "aaaaaaaa", _desk())  # desk shares 1.4
    laptop = PodcastLibrary()
    _sync_with(tmp_path, "laptop", "bbbbbbbb", laptop, SubscriptionPolicy(speed=False))
    assert laptop.effective_settings(laptop.shows[0]).speed != 1.4
    _sync_with(tmp_path, "desk2", "cccccccc", _desk(), SubscriptionPolicy(speed=False))
    sub = next(r for r in _rows(tmp_path, "cccccccc") if str(r.get("id", "")).startswith("sub:"))
    assert "prefs" not in sub


def test_the_policy_settings_round_trip_and_default_to_the_old_behaviour() -> None:
    from quill.core.sync.places_config import PlacesConfig

    old = PlacesConfig.from_dict({"enabled": True})
    assert (old.sub_follow_new, old.sub_unfollows, old.sync_folders, old.sync_speed) == (
        "follow",
        "remove",
        True,
        True,
    )
    chosen = PlacesConfig(
        sub_follow_new="suggest", sub_unfollows="keep", sync_folders=False, sync_speed=False
    )
    again = PlacesConfig.from_dict(chosen.to_dict())
    policy = again.subscription_policy()
    assert (policy.follow_new, policy.unfollows, policy.folders, policy.speed) == (
        "suggest",
        "keep",
        False,
        False,
    )
    assert PlacesConfig(sub_follow_new="nonsense").subscription_policy().follow_new == "follow"
