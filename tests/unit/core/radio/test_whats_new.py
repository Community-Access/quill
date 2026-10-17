"""What's New: one sentence for what arrived since you last looked."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from quill.core import notification_targets
from quill.core.notifications import add_notice, load_notifications
from quill.core.radio.whats_new import NOTHING_NEW, gather, summary


def _seed(path: Path) -> None:
    add_notice(
        app="Quill Radio",
        title="3 new episodes",
        body="The Tech Show",
        target=notification_targets.for_show("show-1"),
        path=path,
    )
    add_notice(
        app="Quill Radio",
        title="1 new episode",
        body="Main Menu",
        target=notification_targets.for_show("show-2"),
        path=path,
    )
    add_notice(
        app="Quill Radio",
        title="A new video",
        body="Blind Abilities",
        target=notification_targets.for_stream("https://youtube.test/v"),
        path=path,
    )
    add_notice(app="Quill Radio", title="Reminder", body="Reminder: X is starting now.", path=path)
    add_notice(app="QUILL", title="Dictation saved", path=path)


def test_the_summary_counts_and_names_what_arrived(tmp_path: Path) -> None:
    path = tmp_path / "notifications.json"
    _seed(path)

    said = summary(gather(load_notifications(path=path)))

    assert said == (
        "Since you last looked: 4 new episodes in The Tech Show, Main Menu. "
        "1 new video from Blind Abilities. 1 reminder went off."
    )


def test_other_apps_and_read_entries_are_not_news(tmp_path: Path) -> None:
    path = tmp_path / "notifications.json"
    add_notice(app="QUILL", title="Dictation saved", path=path)
    assert summary(gather(load_notifications(path=path))) == NOTHING_NEW


def test_many_names_are_cut_short_with_a_count() -> None:
    from quill.core.radio.whats_new import WhatsNew

    news = WhatsNew(episodes=5, shows=["A", "B", "C", "D", "E"], ids=["x"])
    assert summary(news) == "Since you last looked: 5 new episodes in A, B, C, and 2 more."


def test_the_key_says_it_once_then_nothing_new(tmp_path: Path) -> None:
    from quill.ui.radio.whats_new_wiring import announce_whats_new

    path = tmp_path / "notifications.json"
    _seed(path)
    said: list[str] = []
    host = SimpleNamespace(_announce=said.append)

    announce_whats_new(host, path=path)
    announce_whats_new(host, path=path)

    assert said[0].startswith("Since you last looked: 4 new episodes")
    assert said[1] == NOTHING_NEW
    unread_radio = [
        n for n in load_notifications(path=path) if n.app == "Quill Radio" and not n.read
    ]
    assert unread_radio == []
    assert [n.read for n in load_notifications(path=path) if n.app == "QUILL"] == [False]
