"""QUILL Cast's Ask, What Did I Miss and pictures, in the real window (codex.md Phase 3).

The AI is a stand-in on the real service and the one picture fetch is a
stand-in too, so nothing leaves the machine.
"""

from __future__ import annotations

import io
from pathlib import Path

import pytest

wx = pytest.importorskip("wx")

#: A real window with its machine-wide doors closed (closed_machine_doors in conftest).
pytestmark = pytest.mark.usefixtures("closed_machine_doors")

_NOTES = (
    '<p>We talk about tides.</p><img src="https://x.invalid/chart.png" '
    'alt="A tide chart for March"><p>And the moon.</p>'
)


class _Account:
    def __init__(self, signed_in: bool = True) -> None:
        self.signed_in = signed_in
        self.model = ""
        self.slug = "quill-cast"
        self.web_search = False
        self.ended_by_openai = False


def _png() -> bytes:
    from PIL import Image

    out = io.BytesIO()
    Image.new("RGB", (2400, 1200), (200, 30, 30)).save(out, format="PNG")
    return out.getvalue()


@pytest.fixture
def cast(quill_data_dir: Path, wx_app, quiet_cast_startup, close_cast, monkeypatch):
    from quill.core.podcasts.models import PodcastShow
    from quill.core.podcasts.models_episode import PodcastEpisode
    from quill.core.podcasts.subscriptions import PodcastLibrary, save_library

    library = PodcastLibrary()
    show = PodcastShow(id="s1", title="Sea Stories", feed_url="http://x.invalid/feed")
    show.artwork_url = "https://x.invalid/art.jpg"
    show.episodes.append(
        PodcastEpisode(
            guid="e1",
            title="Tides",
            audio_url="http://x.invalid/a.mp3",
            published="2026-10-30T06:00:00+00:00",
            duration_seconds=1800,
            description=_NOTES,
            position_ms=60_000,
        )
    )
    library.add_show(show)
    save_library(quill_data_dir, library)
    from quill.apps.podcasts import PodcastsAppFrame
    from quill.ui.dialog_contract import set_transition_announcement_policy

    frame = PodcastsAppFrame()
    said: list[str] = []
    frame._announce = lambda message, **_kw: said.append(str(message))
    frame.said = said
    frame._podcast_history.ai_help_enabled = True
    frame._podcast_history.ai_connection = ""
    service = frame._ai_service()
    service._chatgpt = _Account(signed_in=True)
    frame._ai_host()._ai_status_text = None
    monkeypatch.setattr(type(service), "refresh_limits", lambda self, on_done=None: None)
    monkeypatch.setattr(type(frame), "_ai_episode", lambda self: (show, show.episodes[0]))
    frame.sent = []

    def converse(message, excerpts, history, *, on_done, on_error, requires=("text",)):
        frame.sent.append((message, list(excerpts)))
        on_done("An answer.", None, 0)

    def ask(feature, prompt, chunks, *, on_done, on_error, requires=("text",), **_kw):
        frame.sent.append((feature, prompt))
        on_done("You missed the tides.", None)

    service.converse = converse
    service.ask = ask
    answers: list[tuple[str, str]] = []
    monkeypatch.setattr(
        "quill.ui.podcasts.ai_answer_dialog.show_answer",
        lambda _host, title, text: answers.append((title, text)),
    )
    frame.answers = answers
    try:
        yield frame
    finally:
        for window in list(getattr(frame, "_ai_windows", {}).values()):
            if window:
                window.Destroy()
        set_transition_announcement_policy(None)
        close_cast(frame)


def _ai_submenu(frame):
    bar = frame.frame.GetMenuBar()
    help_menu = bar.GetMenu(bar.FindMenu("Help"))
    item = next(i for i in help_menu.GetMenuItems() if i.GetItemLabel() == "AI &Features")
    return [i.GetItemLabel() for i in item.GetSubMenu().GetMenuItems() if not i.IsSeparator()]


def test_ai_features_open_on_ask_which_ai_and_choose_your_ai_on_casts_keys(cast) -> None:
    labels = _ai_submenu(cast)
    assert labels[:3] == [
        "&Ask...\tCtrl+Shift+8",
        "Which AI A&m I Using\tCtrl+F8",
        "Choose You&r AI...\tCtrl+Shift+F8",
    ]
    assert "AI Usa&ge...\tCtrl+Alt+Shift+F2" in labels
    assert "What &Did I Miss in This Episode?" in labels


def test_ask_is_about_this_episode_with_its_notes_and_place(cast, quill_data_dir) -> None:
    cast.cmd_ai_chat_key()
    frame = cast._ai_windows["ask"]
    assert frame.GetTitle() == "Ask"
    assert frame._about.GetValue().startswith("Asking My ChatGPT plan about this episode.")
    assert frame._rows[0].label == "What did I miss in this episode?"
    assert frame._rows[1].label == "Is this episode worth my time?"
    frame._message.SetValue("Who is the guest?")
    frame._send()
    facts = cast.sent[0][1][0]
    assert "Show: Sea Stories" in facts
    assert "Episode: Tides" in facts
    assert "Position: 1:00 of 30:00" in facts
    assert "We talk about tides." in facts
    assert list((quill_data_dir / "ai-sessions" / "cast").glob("*.json"))


def test_what_did_i_miss_asks_only_about_what_came_before(cast) -> None:
    cast.ai_what_did_i_miss()
    feature, prompt = cast.sent[0]
    assert feature == "ask"
    assert "before my position" in prompt
    assert "Position: 1:00" in prompt
    assert cast.answers == [("What I missed in Tides", "You missed the tides.")]


def test_what_did_i_miss_before_starting_says_so_and_sends_nothing(cast) -> None:
    cast._ai_episode()[1].position_ms = 0
    cast.ai_what_did_i_miss()
    assert cast.sent == []
    assert cast.said[-1] == "You have not started Tides yet, so there is nothing to miss."


def test_a_picture_where_the_connection_cannot_see_reads_the_notes_alt_text(
    cast, monkeypatch
) -> None:
    cast._podcast_history.ai_connection = "free"
    monkeypatch.setattr(type(cast._ai_service()), "signed_in", property(lambda self: True))
    monkeypatch.setattr("quill.ui.hosted_ai_connections.ask_yes_no", lambda *_a, **_k: False)
    fetched: list[str] = []
    monkeypatch.setattr(
        "quill.core.podcasts.picture_fetch.fetch_picture",
        lambda url, **_k: fetched.append(url) or b"",
    )
    cast.cmd_ai_image()
    assert fetched == []
    assert cast.said[-1] == "The show notes describe their pictures: A tide chart for March."


def test_a_chosen_picture_is_fetched_once_fitted_and_described(cast, monkeypatch) -> None:
    from PIL import Image

    from quill.ui.podcasts import cast_ai_ask

    fetched: list[str] = []
    monkeypatch.setattr(
        "quill.core.podcasts.picture_fetch.fetch_picture",
        lambda url, **_k: fetched.append(url) or _png(),
    )
    monkeypatch.setattr(
        cast_ai_ask,
        "_background",
        lambda _host, _name, work, *, on_done, on_error: on_done(work()),
    )
    offered: list[list[str]] = []
    monkeypatch.setattr(
        type(cast), "_cast_choose_picture", lambda self, labels: offered.append(labels) or 0
    )
    sizes: list[int] = []

    def describe(path, question, *, on_done, on_error, requires):
        with Image.open(path) as picture:
            sizes.append(max(picture.size))
        on_done("A red square.")

    cast._ai_service().describe_image = describe
    questions: list[str] = []
    monkeypatch.setattr(
        type(cast),
        "_show_message_box",
        lambda self, message, caption, style: questions.append(message) or wx.YES,
        raising=False,
    )
    cast.cmd_ai_image()
    assert len(questions) == 1  # 10B.4: asked once, before anything is fetched
    assert "QUILL Cast go to OpenAI on your ChatGPT plan" in questions[0]
    assert cast._podcast_history.ai_picture_consent == ["chatgpt"]
    assert offered[0] == [
        "Podcast artwork for Sea Stories",
        "Show-note picture 1: A tide chart for March",
    ]
    assert fetched == ["https://x.invalid/art.jpg"]
    assert sizes and sizes[0] <= 2048
    title, text = cast.answers[-1]
    assert title == "Podcast artwork for Sea Stories"
    assert text.startswith("Looked at 1 picture. Described by My ChatGPT plan. A red square.")


def test_the_status_bar_ends_with_the_ai_cell(cast) -> None:
    from quill.ui.podcasts.status_bar_cells import build_specs

    specs = build_specs(cast, wx)
    assert specs[-1].key == "ai"
    assert specs[-1].text() == "AI: ChatGPT plan"


def test_casts_sentences_name_its_choose_key(cast) -> None:
    assert cast._ai_service()._keyed("Press Ctrl+4.") == "Press Ctrl+Shift+F8."


def test_ask_about_an_image_says_what_it_needs_on_the_free_ai(cast, monkeypatch) -> None:
    cast._podcast_history.ai_connection = "free"
    monkeypatch.setattr(type(cast._ai_service()), "signed_in", property(lambda self: True))
    cast._build_menu_bar()
    labels = _ai_submenu(cast)
    assert "As&k About an Image (needs a connection that sees)...\tCtrl+Alt+F5" in labels


def test_ask_about_an_image_fetches_and_sends_nothing_when_consent_is_no(cast, monkeypatch) -> None:
    fetched: list[str] = []
    monkeypatch.setattr(
        "quill.core.podcasts.picture_fetch.fetch_picture",
        lambda url, **_k: fetched.append(url) or _png(),
    )
    offered: list[list[str]] = []
    monkeypatch.setattr(
        type(cast), "_cast_choose_picture", lambda self, labels: offered.append(labels) or 0
    )
    sent: list[str] = []
    cast._ai_service().describe_image = lambda *a, **k: sent.append("sent")
    monkeypatch.setattr(type(cast), "_show_message_box", lambda self, *a: wx.NO, raising=False)
    cast.cmd_ai_image()
    assert offered == [] and fetched == [] and sent == []
    assert cast._podcast_history.ai_picture_consent == []
