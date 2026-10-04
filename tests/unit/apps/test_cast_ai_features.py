"""ear.md A2-A9 in the real QUILL Cast window, with the AI answered locally."""

from __future__ import annotations

from pathlib import Path

import pytest

wx = pytest.importorskip("wx")

pytestmark = pytest.mark.machine_global


@pytest.fixture
def cast(quill_data_dir: Path, monkeypatch):
    from quill.core.podcasts.models import PodcastShow
    from quill.core.podcasts.models_episode import PodcastEpisode
    from quill.core.podcasts.subscriptions import PodcastLibrary, save_library

    library = PodcastLibrary()
    for index, title in enumerate(("The Daily", "Tech Talk", "Old Show"), start=1):
        show = PodcastShow(id=f"s{index}", title=title, feed_url=f"http://x.invalid/{index}")
        show.description = f"About {title}."
        published = (
            "2022-01-01T00:00:00+00:00" if title == "Old Show" else "2026-09-30T06:00:00+00:00"
        )
        show.episodes.append(
            PodcastEpisode(
                guid=f"e{index}",
                title=f"Episode of {title}",
                audio_url="http://x.invalid/a.mp3",
                published=published,
                duration_seconds=600 * index,
            )
        )
        show.route_to_inbox = True
        library.add_show(show)
    save_library(quill_data_dir, library)
    app = wx.App()
    from quill.apps.podcasts import PodcastsAppFrame
    from quill.ui.dialog_contract import set_transition_announcement_policy

    frame = PodcastsAppFrame()
    said: list[str] = []
    frame._announce = lambda message, **_kw: said.append(str(message))
    frame.said = said
    frame.answers: list[str] = []
    frame.prompts: list[str] = []

    class _Service:
        def ask(self, feature, prompt, chunks, *, on_done, on_error, language=""):
            frame.prompts.append(prompt)
            on_done(frame.answers.pop(0), None)

    monkeypatch.setattr(type(frame), "_ai_ready", lambda self: True)
    monkeypatch.setattr(type(frame), "_ai_service", lambda self: _Service())
    reviewed: list[list[str]] = []
    frame.reviewed = reviewed

    def _review(_host, _title, _intro, rows):
        reviewed.append(list(rows))
        return list(range(len(rows)))

    monkeypatch.setattr("quill.ui.podcasts.ai_review_dialog.review", _review)
    monkeypatch.setattr("quill.ui.podcasts.ai_answer_dialog.show_answer", lambda *_a: None)
    try:
        yield frame
    finally:
        set_transition_announcement_policy(None)
        try:
            frame.frame.Destroy()
        except Exception:  # noqa: BLE001
            pass
        del app


def test_the_ai_verbs_are_rows_in_help_ai_features(cast) -> None:
    from quill.ui.podcasts.cast_ai_features import AI_FEATURE_ROWS

    labels = []
    bar = cast.frame.GetMenuBar()
    for index in range(bar.GetMenuCount()):
        for item in bar.GetMenu(index).GetMenuItems():
            if item.GetSubMenu():
                labels += [sub.GetItemLabel() for sub in item.GetSubMenu().GetMenuItems()]
    for _command, label, _handler in AI_FEATURE_ROWS:
        assert label in labels


def test_organise_creates_folders_and_moves_only_what_resolves(cast) -> None:
    cast.answers.append(
        '{"create": [{"name": "News", "reason": "daily news"}],'
        ' "move": [{"id": "s1", "folder": "News", "reason": "news"},'
        ' {"id": "nope", "folder": "News", "reason": "invented"}]}'
    )
    cast.ai_organise_podcasts()
    library = cast._podcast_library
    news = next(f for f in library.folders if f.name == "News")
    assert library.find_show("s1").folder_id == news.id
    assert "https://" not in cast.prompts[0] and "x.invalid" not in cast.prompts[0]
    assert any("Made 1 folder and moved 1 podcast." in s for s in cast.said)


def test_a_listening_run_fills_the_queue_in_order(cast, monkeypatch) -> None:
    class _Entry:
        def __init__(self, *_a, **_k) -> None: ...
        def __enter__(self):
            return self

        def __exit__(self, *_a) -> None: ...
        def ShowModal(self) -> int:
            return wx.ID_OK

        def GetValue(self) -> str:
            return "30"

    monkeypatch.setattr(wx, "TextEntryDialog", _Entry)
    cast.answers.append('{"run": [{"number": 2}, {"number": 1}]}')
    cast.ai_listening_run()
    queued = [item.episode_guid for item in cast._podcast_library.queue]
    assert len(queued) == 2 and len(set(queued)) == 2


def test_a_sentence_becomes_a_smart_playlist(cast, monkeypatch) -> None:
    class _Entry:
        def __init__(self, *_a, **_k) -> None: ...
        def __enter__(self):
            return self

        def __exit__(self, *_a) -> None: ...
        def ShowModal(self) -> int:
            return wx.ID_OK

        def GetValue(self) -> str:
            return "unheard Daily episodes"

    monkeypatch.setattr(wx, "TextEntryDialog", _Entry)
    cast.answers.append('{"name": "Daily", "episode_status": "unplayed", "shows": ["The Daily"]}')
    cast.ai_playlist_from_sentence()
    playlist = cast._podcast_library.playlists[-1]
    assert playlist.kind == "smart" and playlist.rules.show_ids == ["s1"]


def test_tidy_needs_no_ai_and_pauses_a_dormant_podcast(cast, monkeypatch) -> None:
    monkeypatch.setattr(type(cast), "_ai_ready", lambda self: False)
    cast.tidy_subscriptions()
    assert cast._podcast_library.find_show("s3").paused
    assert cast.prompts == []


def test_for_me_asks_for_the_note_first(cast) -> None:
    cast.show_place("podcasts", focus=False)
    cast._podcast_controller.state.show_id = "s1"
    cast._podcast_controller.state.episode_guid = "e1"
    cast.ai_for_me()
    assert any("What I care about in this podcast" in s for s in cast.said)
    assert cast.prompts == []
