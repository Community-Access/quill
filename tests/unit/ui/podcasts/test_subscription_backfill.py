from __future__ import annotations

from types import SimpleNamespace

from quill.ui.podcasts import subscription_backfill


def test_apply_backfill_marks_only_unstreamed_undownloaded_episodes(monkeypatch) -> None:
    wanted = [
        SimpleNamespace(downloaded_path=None, mode_override=None),
        SimpleNamespace(downloaded_path="episode.mp3", mode_override=None),
        SimpleNamespace(downloaded_path=None, mode_override="stream"),
    ]
    monkeypatch.setattr(
        "quill.core.podcasts.show_policy.backfill_episodes",
        lambda _library, _show, _episodes: wanted,
    )

    count = subscription_backfill._apply_backfill(SimpleNamespace(), SimpleNamespace(episodes=[]))

    assert count == 3
    assert [episode.mode_override for episode in wanted] == ["download", None, "stream"]


def test_apply_backfill_treats_policy_failure_as_no_backfill(monkeypatch) -> None:
    def fail(*_args):
        raise RuntimeError("policy unavailable")

    monkeypatch.setattr("quill.core.podcasts.show_policy.backfill_episodes", fail)

    assert (
        subscription_backfill._apply_backfill(SimpleNamespace(), SimpleNamespace(episodes=[])) == 0
    )
