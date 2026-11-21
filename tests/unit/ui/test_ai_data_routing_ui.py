"""Nothing goes to an AI the person did not choose: the window-side fixes (2026-11).

Each test reproduces one finding of ``docs/qa/ai-and-settings-legibility-2026-11.md``
and pins its fix: the cached assistant following a provider switch, Ask About
an Image naming the real company and asking picture consent, the offline speech
paths staying offline, Review Dictation naming Auto's real pick, and an agent
engine's fall-back asking before a different company is used. Fakes only: no
key is real, no dialog is shown, no network is reached.
"""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
import wx

import quill.core.assistant_ai as aai

# -- 3. The cached assistant follows a provider switch --------------------------- #


class _Assistant:
    built = 0

    def __init__(self) -> None:
        type(self).built += 1
        self.backend = SimpleNamespace(name=f"build-{type(self).built}")

    def set_style_preamble(self, _text: str) -> None:
        pass

    def set_instructions_preamble(self, _text: str) -> None:
        pass


def _write_connection(path: Path, provider: str) -> None:
    path.write_text(
        json.dumps({"provider": provider, "host": "http://localhost:11434", "model": "m"}),
        encoding="utf-8",
    )


def test_the_cached_assistant_is_rebuilt_after_a_provider_switch(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    import quill.ui.main_frame as main_frame

    monkeypatch.setenv("QUILL_DATA_DIR", str(tmp_path))
    connection = tmp_path / "assistant-connection.json"
    monkeypatch.setattr(aai, "assistant_connection_path", lambda: connection)
    monkeypatch.setattr(aai, "_cs_load", lambda _name: "")
    monkeypatch.setattr(main_frame, "Assistant", _Assistant)
    frame = SimpleNamespace(document=SimpleNamespace(path=None))
    frame._apply_style_to_assistant = lambda: None

    _write_connection(connection, "openai")
    first = main_frame.MainFrame._get_assistant(frame)
    assert main_frame.MainFrame._get_assistant(frame) is first  # unchanged: kept

    _write_connection(connection, "ollama")
    second = main_frame.MainFrame._get_assistant(frame)

    assert second is not first


def test_studio_chapter_titles_read_the_provider_at_each_use(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import quill.core.ai.provider_backend as providers
    from quill.apps.studio import StudioAppFrame

    built: list[str] = []

    class _Backend:
        def __init__(self) -> None:
            built.append("built")

        def respond(self, prompt: str) -> str:
            return prompt

    monkeypatch.setattr(providers, "ProviderChatBackend", _Backend)
    host = SimpleNamespace()
    shim = StudioAppFrame._get_assistant(host)
    shim.ask("one")
    shim.ask("two")

    assert len(built) == 2


# -- 4. Ask About an Image -------------------------------------------------------- #


class _ImageService:
    connection = "own_key"
    connection_in_use = "own_key"
    own_key_provider = "gemini"

    def __init__(self) -> None:
        self.sent: list[Any] = []

    def auto_connection(self, _requires: tuple[str, ...]) -> str:
        return "own_key"

    def describe_image(self, path: Any, question: str, **_kwargs: Any) -> None:
        self.sent.append((path, question))


def _image_host(service: _ImageService) -> Any:
    from quill.ui.hosted_ai_chatgpt_commands import ChatGptAiMixin

    class _Host(ChatGptAiMixin):
        def __init__(self) -> None:
            self.said: list[str] = []

        def _ai_switched_on(self) -> bool:
            return True

        def _ai_capable(self, _capability: str) -> bool:
            return True

        def _ai_service(self) -> Any:
            return service

        def _ai_parent(self) -> Any:
            return None

        def _announce(self, text: str) -> None:
            self.said.append(text)

    return _Host()


@pytest.fixture
def image_dialog(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    import quill.ui.dialog_contract as contract
    import quill.ui.hosted_ai_image as image

    seen: dict[str, Any] = {}

    class _Dialog:
        def __init__(self, _parent: Any, **kwargs: Any) -> None:
            seen.update(kwargs)

        def chosen(self) -> tuple[Path, str]:
            return Path("picture.png"), ""

        def Destroy(self) -> None:  # noqa: N802 - wx's name
            pass

    monkeypatch.setattr(image, "AskImageDialog", _Dialog)
    monkeypatch.setattr(contract, "show_modal_dialog", lambda *_a, **_k: wx.ID_OK)
    return seen


def test_ask_about_an_image_asks_picture_consent_first(
    monkeypatch: pytest.MonkeyPatch, image_dialog: dict[str, Any]
) -> None:
    import quill.ui.hosted_ai_picture_consent as consent

    asked: list[str] = []

    def no(_host: Any, connection: str) -> bool:
        asked.append(connection)
        return False

    monkeypatch.setattr(consent, "ask_picture_consent", no)
    service = _ImageService()

    _image_host(service).cmd_ai_image()

    assert asked == ["own_key"]
    assert service.sent == []  # No, the default, sends nothing


def test_ask_about_an_image_names_the_real_company(
    monkeypatch: pytest.MonkeyPatch, image_dialog: dict[str, Any]
) -> None:
    import quill.ui.hosted_ai_picture_consent as consent

    monkeypatch.setattr(consent, "ask_picture_consent", lambda *_a: True)
    service = _ImageService()

    _image_host(service).cmd_ai_image()

    destination = str(image_dialog.get("destination", ""))
    assert "Google" in destination
    assert "OpenAI" not in destination
    assert service.sent  # Yes sends


def test_ask_about_an_image_under_auto_names_autos_pick(
    monkeypatch: pytest.MonkeyPatch, image_dialog: dict[str, Any]
) -> None:
    import quill.ui.hosted_ai_picture_consent as consent

    asked: list[str] = []
    monkeypatch.setattr(consent, "ask_picture_consent", lambda _h, c: asked.append(c) or True)
    service = _ImageService()
    service.connection = "auto"
    service.connection_in_use = "auto"

    _image_host(service).cmd_ai_image()

    assert asked == ["own_key"]  # the connection Auto will use, never "auto"
    assert "Google" in str(image_dialog.get("destination", ""))


def test_the_image_window_says_where_the_picture_goes(wx_session_app: Any) -> None:
    from quill.ui.hosted_ai_image import AskImageDialog

    dialog = AskImageDialog(None, destination="Google, billed to your own key")
    try:
        about = [
            child.GetValue()
            for child in dialog.GetChildren()
            if isinstance(child, wx.TextCtrl) and child.GetValue()
        ]
    finally:
        dialog.Destroy()

    assert any("Google, billed to your own key" in text for text in about)
    assert not any("OpenAI" in text for text in about)


# -- 5. Offline means offline ----------------------------------------------------- #


class _Engine:
    def __init__(self, engine_id: str, *, network: bool) -> None:
        self.id = engine_id
        self.requires_network = network

    def is_available(self) -> bool:
        return True


class _Registry:
    def __init__(self) -> None:
        self.engines = {
            "cloud-transcriber": _Engine("cloud-transcriber", network=True),
        }

    def get(self, engine_id: str) -> Any:
        from quill.core.speech.service import DEFAULT_PROVIDER_ID

        if engine_id == DEFAULT_PROVIDER_ID:
            return _Engine(DEFAULT_PROVIDER_ID, network=False)
        return self.engines.get(engine_id)


def _speech_host() -> Any:
    host = SimpleNamespace(settings=SimpleNamespace(speech_provider="cloud-transcriber"))
    host._speech_registry = _Registry
    return host


def test_quills_offline_speech_never_picks_a_cloud_transcriber() -> None:
    from quill.ui.main_frame_speech import SpeechCommandsMixin

    engine = SpeechCommandsMixin._speech_provider(_speech_host())

    assert not engine.requires_network


def test_studios_generate_captions_offline_never_picks_a_cloud_transcriber() -> None:
    from quill.apps.studio import StudioAppFrame

    engine = StudioAppFrame._speech_provider(_speech_host())

    assert not engine.requires_network


# -- 6. Review Dictation names Auto's real pick ---------------------------------- #


def _review(route: str, *, auto_pick: str = "", provider: str = "openai") -> Any:
    from quill.ui.windows_dictation_review import ServiceReviewAi

    service = SimpleNamespace(
        route=route,
        direct=True,
        own_key_provider=provider,
        auto_connection=lambda _requires: auto_pick,
    )
    return ServiceReviewAi(service, off=lambda: "", consent=lambda: 0, agree=lambda: None)


def test_review_dictation_under_auto_names_copilot_when_auto_picks_it() -> None:
    assert _review("auto", auto_pick="copilot").provider() == "GitHub on your Copilot plan"


def test_review_dictation_under_auto_names_the_chatgpt_plan() -> None:
    assert _review("auto", auto_pick="chatgpt").provider() == "OpenAI on your ChatGPT plan"


def test_review_dictation_under_auto_names_the_own_keys_company() -> None:
    said = _review("auto", auto_pick="own_key", provider="gemini").provider()
    assert said == "Google, billed to your own key"


def test_review_dictation_with_nothing_ready_asks_nothing() -> None:
    from quill.ui.windows_dictation_review import NO_AI_READY

    assert _review("auto", auto_pick="").reason() == NO_AI_READY


def test_review_dictation_under_auto_names_the_free_ai() -> None:
    assert "free AI" in _review("auto", auto_pick="free").provider()


# -- 7. An agent engine's fall-back asks first ------------------------------------ #


class _Backend:
    def __init__(self, provider: str) -> None:
        self.settings = SimpleNamespace(provider=provider)

    def is_available(self) -> tuple[bool, str | None]:
        return True, None

    def respond(self, prompt: str) -> str:  # pragma: no cover - not reached
        return prompt


class _Controller:
    def __init__(self, answer: int) -> None:
        self.answer = answer
        self.asked: list[str] = []
        self.messages: list[str] = []

    def _set_status(self, message: str) -> None:
        self.messages.append(message)

    def _show_message_box(self, message: str, _caption: str, _style: int) -> int:
        self.asked.append(message)
        return self.answer


@pytest.fixture
def unready_pack(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from quill.core.ai.quick_switch import save_preferred_harness_id

    monkeypatch.setenv("QUILL_DATA_DIR", str(tmp_path))
    save_preferred_harness_id("openai_agents")

    class _Pack:
        id = "openai_agents"
        display_name = "OpenAI Agents SDK"

        def is_available(self) -> tuple[bool, str | None]:
            return False, "Not installed."

    monkeypatch.setattr("quill.ai_packs.all_packs", lambda **_kwargs: [_Pack()])


def test_an_engine_fall_back_to_another_company_asks_and_no_sends_nothing(
    unready_pack: None,
) -> None:
    from quill.ui.agent_responder_selection import select_responder

    controller = _Controller(wx.NO)
    responder, said = select_responder(_Backend("claude"), controller)

    assert responder is None
    assert len(controller.asked) == 1
    assert "Anthropic" in controller.asked[0]
    assert "Nothing was sent" in said


def test_an_engine_fall_back_goes_ahead_on_yes(unready_pack: None) -> None:
    from quill.ui.agent_responder_selection import select_responder

    controller = _Controller(wx.YES)
    responder, _name = select_responder(_Backend("claude"), controller)

    assert callable(responder)
    assert len(controller.asked) == 1


def test_an_engine_fall_back_to_this_computer_is_said_not_asked(unready_pack: None) -> None:
    from quill.ui.agent_responder_selection import select_responder

    controller = _Controller(wx.NO)
    responder, _name = select_responder(_Backend("ollama"), controller)

    assert callable(responder)
    assert controller.asked == []
    assert controller.messages  # still said, once
