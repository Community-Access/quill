"""Quill Media Player's AI, in the real window (codex.md Phase 3, 10E.8).

Its own "QUILL Media Player" sign-in, the AI menu on the Window-menu fallback
keys, the two recaps where they always were (Playback, Ctrl+Alt+C and
Ctrl+Alt+R) now on the AI in use, Ask about the book, the AI line and Safe Mode.
The AI is a stand-in on the real service and the transcript is a fake, so
nothing leaves the machine and no audio is touched.
"""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

wx = pytest.importorskip("wx")

#: A real window with its machine-wide doors closed (closed_machine_doors in conftest).
pytestmark = pytest.mark.usefixtures("closed_machine_doors")


class _Account:
    def __init__(self, signed_in: bool = True) -> None:
        self.signed_in = signed_in
        self.model = ""
        self.slug = "quill-media-player"
        self.web_search = False
        self.ended_by_openai = False


@pytest.fixture
def player(quill_data_dir: Path, wx_session_app, monkeypatch: pytest.MonkeyPatch, request):
    from tests.unit.docs._app_menu_bar import real_app_shell

    with real_app_shell(monkeypatch, request, "quill.apps.player", "QuillMediaPlayerFrame") as app:
        app._safe_mode = False
        said: list[str] = []
        app._announce = lambda message, **_kw: said.append(str(message))
        app.said = said
        service = app._ai_service()
        monkeypatch.setattr(type(service), "refresh_limits", lambda self, on_done=None: None)
        app.sent = []

        def ask(feature, prompt, chunks, *, on_done, on_error, language="", requires=("text",)):
            app.sent.append((feature, prompt, requires))
            on_done("The hero reached the city.", None)

        def converse(message, excerpts, history, *, on_done, on_error, requires=("text",)):
            app.sent.append(("converse", message, list(excerpts)))
            on_done("An answer.", None, 0)

        service.ask = ask
        service.converse = converse
        service._chatgpt = _Account(signed_in=True)
        app._ai_host().settings.ai_connection = "chatgpt"
        app.shown = []
        monkeypatch.setattr(app, "_show_ai_window", lambda window: app.shown.append(window))
        app.boxes = []
        monkeypatch.setattr(
            app, "_show_message_box", lambda message, caption, *a, **k: app.boxes.append(message)
        )
        try:
            yield app
        finally:
            for window in [*getattr(app, "_ai_windows", {}).values(), *app.shown]:
                if window:
                    window.Destroy()
            try:
                app._player.shutdown()
            except Exception:  # noqa: BLE001 - no engine to stop
                pass


def _menu(app, name: str):
    bar = app.frame.GetMenuBar()
    return bar.GetMenu(bar.FindMenu(name))


def _open_book(app, monkeypatch, *, book_key: str = r"C:\Books\Treasure Island.mp3") -> None:
    """A book with three chapters, playing in the second, two minutes in."""
    app._book_key = book_key
    app._book_path = Path(book_key) if not book_key.startswith("bard:") else None
    app._chapters = [
        SimpleNamespace(title="The Old Sea-dog", start_ms=0, duration_ms=600_000),
        SimpleNamespace(title="Black Dog Appears", start_ms=600_000, duration_ms=500_000),
        SimpleNamespace(title="The Black Spot", start_ms=1_100_000, duration_ms=400_000),
    ]
    app._chapter_nodes = [(c.title, ("seek", c.start_ms), 1) for c in app._chapters]
    app._now_playing.SetValue("Treasure Island")
    monkeypatch.setattr(app._player, "current_chapter_index", lambda: 1)
    monkeypatch.setattr(app._player, "playhead_ms", lambda: 720_000)
    monkeypatch.setattr(app._player, "length_ms", lambda: 1_500_000)


@pytest.fixture
def transcripts(monkeypatch):
    """The recap's text, found at once instead of on a worker; records each ask."""
    from quill.core.media import RecapService
    from quill.ui.media import recap_actions

    asked: list[tuple[str, int, int]] = []
    cache: dict[str, str] = {}

    def transcriber(path: str, start_ms: int, duration_ms: int) -> str:
        asked.append((Path(path).name, start_ms, duration_ms))
        return "Jim met a man with a scar at the inn."

    monkeypatch.setattr(
        recap_actions, "recap_service", lambda: RecapService(transcriber=transcriber, cache=cache)
    )

    def gather(service, ctx, on_text, on_error):
        try:
            text = service.text_for(ctx)
        except Exception as error:  # noqa: BLE001 - as the worker reports it
            on_error(str(error))
            return
        on_text(text)

    monkeypatch.setattr(recap_actions, "gather_in_background", gather)
    return asked


def test_the_ai_menu_sits_before_quillville_on_the_fallback_keys(player) -> None:
    bar = player.frame.GetMenuBar()
    titles = [bar.GetMenuLabel(i) for i in range(bar.GetMenuCount())]
    assert titles.index("A&I") == titles.index("&QuillVille") - 1
    labels = [i.GetItemLabel() for i in _menu(player, "AI").GetMenuItems() if not i.IsSeparator()]
    assert labels == [
        "&Ask...\tCtrl+Shift+8",
        "&Which AI Am I Using\tCtrl+F8",
        "&Choose Your AI...\tCtrl+Shift+F8",
        "&Find the Part Where (needs Copilot or Codex)...\tCtrl+F3",
        "Use My C&hatGPT Subscription...\tAlt+F5",
        "Use My &Own AI Key...\tAlt+F2",
        "AI U&sage...\tCtrl+Alt+Shift+F2",
        "&Privacy Agreement...\tCtrl+Alt+Shift+K",
    ]


def test_the_recaps_stay_in_playback_on_their_keys_with_ids(player) -> None:
    labels = [i.GetItemLabel() for i in _menu(player, "Playback").GetMenuItems()]
    assert "Summarize This &Chapter (AI)\tCtrl+Alt+C" in labels
    assert "AI &Recap of Where I Am\tCtrl+Alt+R" in labels
    ai_labels = [i.GetItemLabel() for i in _menu(player, "AI").GetMenuItems()]
    assert not any("Recap" in label or "Summarize" in label for label in ai_labels)
    assert player.commands.get("player.ai_chapter_summary") is not None
    assert player.commands.get("player.ai_recap") is not None


def test_the_player_signs_in_as_itself(player) -> None:
    service = player._ai_service()
    assert service._app.ai_agent_name == "QUILL Media Player"
    del service._chatgpt
    assert service.chatgpt.agent_name == "QUILL Media Player"


def test_the_choice_is_kept_in_the_players_own_file(player) -> None:
    from quill.core.paths import app_data_dir

    player._ai_host().save_settings()
    saved = json.loads((app_data_dir() / "player-ai.json").read_text(encoding="utf-8"))
    assert saved["ai_connection"] == "chatgpt"


def test_chapter_summary_sends_a_local_transcript_to_the_ai_in_use(
    player, monkeypatch, transcripts
) -> None:
    _open_book(player, monkeypatch)
    player.cmd_player_chapter_summary()
    assert transcripts == [("Treasure Island.mp3", 600_000, 500_000)]
    feature, prompt, requires = player.sent[0]
    assert requires == ("text",)
    assert "Summarize this audiobook chapter" in prompt
    assert prompt.endswith("Jim met a man with a scar at the inn.")
    assert "Books" not in prompt  # never the path
    window = player.shown[0]
    assert window.GetTitle() == "Chapter Summary"
    assert window._text == "The hero reached the city."
    assert "Summarizing this chapter. This may take a moment." in player.said


def test_a_second_ask_for_the_same_chapter_sends_nothing(player, monkeypatch, transcripts) -> None:
    _open_book(player, monkeypatch)
    player.cmd_player_chapter_summary()
    player.cmd_player_chapter_summary()
    assert len(player.sent) == 1 and len(transcripts) == 1
    assert player.shown[1]._text == "The hero reached the city."


def test_recap_covers_the_chapter_up_to_the_place(player, monkeypatch, transcripts) -> None:
    _open_book(player, monkeypatch)
    player.cmd_player_recap()
    assert transcripts == [("Treasure Island.mp3", 600_000, 120_000)]
    _feature, prompt, _requires = player.sent[0]
    assert "resume an audiobook" in prompt
    assert player.shown[0].GetTitle() == "Recap"


def test_the_voice_commands_reach_the_same_recaps(player, monkeypatch, transcripts) -> None:
    _open_book(player, monkeypatch)
    player.voice_summarize()
    player.voice_recap()
    assert [p.split("\n")[0][:12] for _f, p, _r in player.sent] == ["Summarize th", "You are help"]


def test_no_text_is_said_and_nothing_is_sent(player, monkeypatch) -> None:
    from quill.core.media import RecapService
    from quill.ui.media import recap_actions

    _open_book(player, monkeypatch)
    monkeypatch.setattr(recap_actions, "recap_service", lambda: RecapService())
    monkeypatch.setattr(
        recap_actions,
        "gather_in_background",
        lambda service, ctx, on_text, on_error: on_error("No text to summarize."),
    )
    player.cmd_player_recap()
    assert player.sent == [] and player.shown == []
    assert player.said[-1] == "No text to summarize."


def test_protected_bard_content_is_refused(player, monkeypatch, transcripts) -> None:
    _open_book(player, monkeypatch, book_key="bard:DB12345")
    player.cmd_player_chapter_summary()
    assert player.said == ["AI summaries are not available for protected BARD content."]
    assert player.sent == [] and transcripts == []


def test_with_no_book_open_it_says_open_a_book_first(player, transcripts) -> None:
    player.cmd_player_recap()
    assert player.boxes == ["Open a book first."]
    assert player.sent == [] and transcripts == []


def test_ask_sends_the_book_the_place_and_the_chapters(player, monkeypatch) -> None:
    from quill.ui.hosted_ai_app_ask import AppAskFrame

    _open_book(player, monkeypatch)
    player.cmd_ai_chat_key()
    frame = player._ai_windows["ask"]
    assert isinstance(frame, AppAskFrame)
    assert frame._about.GetValue().startswith("Asking My ChatGPT plan about this book.")
    frame._message.SetValue("Who is Black Dog?")
    frame._send()
    facts = player.sent[0][2][0]
    assert "Book: Treasure Island" in facts
    assert "Black Dog Appears (chapter 2 of 3)" in facts
    assert "12:00" in facts
    assert "1. The Old Sea-dog" in facts and "3. The Black Spot" in facts
    assert "Books" not in facts  # the path never goes


def test_ask_with_no_book_says_so(player) -> None:
    facts = player._app_ask_facts("anything", "")
    assert facts.get("Book") == "no book is open"


def test_safe_mode_refuses_every_ai_command(player, monkeypatch, transcripts) -> None:
    _open_book(player, monkeypatch)
    player._safe_mode = True
    for command in (
        lambda p: p.cmd_ai_chat_key(),
        lambda p: p.cmd_ai_which(),
        lambda p: p.cmd_ai_choose(),
        lambda p: p.cmd_ai_usage(),
        lambda p: p.cmd_ai_chatgpt(),
        lambda p: p.cmd_player_chapter_summary(),
        lambda p: p.cmd_player_recap(),
    ):
        player.said.clear()
        command(player)
        assert player.said == ["AI is off in Safe Mode."]
    assert player.sent == [] and transcripts == []


def test_the_ai_line_says_which_ai_and_enter_opens_choose(player, monkeypatch) -> None:
    opened: list[str] = []
    monkeypatch.setattr(type(player), "cmd_ai_choose", lambda self: opened.append("x"))
    assert player._ai_text.GetValue().startswith("AI")
    assert "Choose Your AI" in player._ai_text.GetHelpText()
    event = wx.KeyEvent(wx.wxEVT_KEY_DOWN)
    event.SetKeyCode(wx.WXK_RETURN)
    player._on_ai_line_key(event)
    assert opened == ["x"]


def test_the_adapter_has_no_command_of_its_own() -> None:
    from quill.apps.player_ai import PlayerAiMixin
    from quill.ui.hosted_ai_app_adapter import AppAiHost, AppAiMixin

    for cls in (PlayerAiMixin, AppAiMixin, AppAiHost):
        assert [name for name in vars(cls) if name.startswith("cmd_")] == []
