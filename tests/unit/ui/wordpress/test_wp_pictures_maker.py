"""The Picture Maker in File > WordPress, behaviourally (wordpress.md 6.9).

The window is faked (its callbacks are what QUILL and QUILL Lite hand it), the
provider and the chosen AI are faked, and the site is the shared FakeSite.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from quill.core.ai import picture_maker as pm
from quill.ui import studio_picture_maker as maker
from quill.ui import wordpress_item_dialogs as idlg
from quill.ui import wordpress_picture_commands as pcmd

API = "/wp-json/wp/v2"


class FakeService:
    own_key_active = True
    own_key_provider = "openai"
    connection_in_use = "own_key"

    def __init__(self) -> None:
        self.conversed: list[str] = []
        self.answer = (
            "Description: A radio mast at dawn, warm colours, flat illustration.\n"
            "Shape: landscape\nBackground: solid navy\nWhy: The page is about the station."
        )

    def converse(self, prompt, chunks, history, *, on_done, on_error, requires=("text",)):
        self.requires = requires
        self.conversed.append(prompt)
        on_done(self.answer, None, 0)


class FakeAi:
    def __init__(self) -> None:
        self.service = FakeService()
        self.ready = True
        self.on = True
        self.safe = False

    def _ai_ready(self) -> bool:
        return self.ready

    def _ai_switched_on(self) -> bool:
        return self.on

    def _ai_safe_mode(self) -> bool:
        return self.safe

    def _ai_capable(self, _capability: str) -> bool:
        return True

    def _ai_service(self) -> FakeService:
        return self.service


@pytest.fixture
def ai(wp) -> FakeAi:
    fake = FakeAi()
    wp.host.ai_editor = lambda: fake
    wp.host.looked = []

    def describe(path, question, on_done, on_error):
        wp.host.looked.append((Path(path), question))
        on_done("A radio mast against an orange sky.")
        return True

    wp.host.ai_describe_image = describe
    return fake


@pytest.fixture
def window(monkeypatch) -> dict[str, Any]:
    opened: dict[str, Any] = {}

    def fake_open(_parent, _show_modal, **kwargs):
        opened.update(kwargs)

    monkeypatch.setattr(maker, "open_picture_maker", fake_open)
    return opened


@pytest.fixture
def openai(monkeypatch) -> list[dict[str, Any]]:
    asked: list[dict[str, Any]] = []

    def connection(*, own_key_provider: str = ""):
        asked.append({"own_key_provider": own_key_provider})
        return pm.PictureConnection("OpenAI", "openai", "sk-test")

    monkeypatch.setattr(pm, "picture_connection", connection)
    return asked


@pytest.fixture
def made(monkeypatch, tmp_path) -> list[dict[str, Any]]:
    calls: list[dict[str, Any]] = []

    def fake_make(connection, turns, size, folder, **kwargs):
        calls.append({"turns": list(turns), "size": size, **kwargs})
        path = tmp_path / f"Picture {len(calls)}.png"
        _png(path)
        return pm.MadePicture(path, " ".join(turns))

    monkeypatch.setattr(pm, "make_picture", fake_make)
    return calls


def _png(path: Path, size: tuple[int, int] = (64, 32)) -> Path:
    from PIL import Image

    Image.new("RGB", size, (200, 80, 20)).save(path, format="PNG")
    return path


def _request(window, turns, **kwargs):
    done: list[tuple[Path, str]] = []
    failed: list[str] = []
    window["request"](turns, "landscape", lambda p, d: done.append((p, d)), failed.append, **kwargs)
    return done, failed


# --------------------------------------------------------------------------- #
# opening


def test_no_ai_in_this_window_says_so(wp, window) -> None:
    wp.cmd_picture_maker()
    assert "AI help is not available" in wp.host.said
    assert window == {}


def test_safe_mode_opens_nothing(wp, ai, window) -> None:
    ai.safe = True
    wp.cmd_picture_maker()
    assert "Safe Mode" in wp.host.said
    assert window == {}


def test_a_provider_that_cannot_draw_is_named(wp, ai, window, monkeypatch) -> None:
    monkeypatch.setattr(
        pm,
        "picture_connection",
        lambda **_k: "Your AI provider (anthropic) does not make pictures.",
    )
    wp.cmd_picture_maker()
    assert "does not make pictures" in wp.host.said
    assert window == {}


def test_opens_the_shared_window_with_the_page_extras(wp, ai, window, openai) -> None:
    wp.cmd_picture_maker()
    assert openai == [{"own_key_provider": "openai"}]
    assert window["title"] == "Picture Maker"
    assert window["make_video"] is None
    assert window["page"].transparent is True
    assert window["page"].insert_label == "Inse&rt into Document..."


def test_gemini_offers_no_transparent_background(wp, ai, window, monkeypatch) -> None:
    monkeypatch.setattr(
        pm,
        "picture_connection",
        lambda **_k: pm.PictureConnection("Google Gemini", "gemini", "g-key"),
    )
    wp.cmd_picture_maker()
    assert window["page"].transparent is False


def test_no_own_key_in_use_asks_for_the_set_up_provider(wp, ai, window, openai) -> None:
    ai.service.own_key_active = False
    wp.cmd_picture_maker()
    assert openai == [{"own_key_provider": ""}]


# --------------------------------------------------------------------------- #
# making


def test_declining_the_approval_sends_nothing(wp, ai, window, openai, made, wp_dialogs) -> None:
    wp.cmd_picture_maker()
    done, failed = _request(window, ["A radio mast"])
    assert failed == ["Nothing was sent."]
    assert made == [] and done == []
    message = wp_dialogs.asked("confirm")[0]["message"]
    assert "OpenAI" in message and "gpt-image-1" in message


def test_making_a_picture_saves_it_and_describes_it(
    wp, ai, window, openai, made, wp_dialogs
) -> None:
    wp_dialogs.answer("confirm", True)
    wp.cmd_picture_maker()
    done, failed = _request(window, ["A radio mast"], background="solid", colour="navy")
    assert failed == []
    assert made[0]["background"] == "solid" and made[0]["colour"] == "navy"
    assert done[0][0].name == "Picture 1.png"
    assert "Making the picture" in wp.host.said
    assert wp.host.looked[0][0] == done[0][0]
    assert wp_dialogs.reports[-1]["text"] == "A radio mast against an orange sky."


def test_a_screenshot_request_is_warned_about_once(
    wp, ai, window, openai, made, wp_dialogs
) -> None:
    wp.cmd_picture_maker()
    _done, failed = _request(window, ["A screenshot of the Settings dialog"])
    assert failed == [pm.SCREENSHOT_NOTE]
    assert wp_dialogs.asked("confirm") == []
    wp_dialogs.answer("confirm", True)
    done, failed = _request(window, ["A screenshot of the Settings dialog"])
    assert failed == [] and len(done) == 1


def test_a_failed_picture_says_why(wp, ai, window, openai, wp_dialogs, monkeypatch) -> None:
    def broken(*_a, **_k):
        from quill.core.ai.image_generation import ImageGenerationError

        raise ImageGenerationError("The provider refused the request (400).")

    monkeypatch.setattr(pm, "make_picture", broken)
    wp_dialogs.answer("confirm", True)
    wp.cmd_picture_maker()
    done, failed = _request(window, ["A radio mast"])
    assert done == []
    assert failed[0].startswith("No picture was made:")
    assert "refused the request" in failed[0]


# --------------------------------------------------------------------------- #
# suggest from page content


def test_suggest_fills_the_fields_from_the_page(wp, ai, window, openai) -> None:
    wp.host.text = "Community Radio broadcasts from the hill every morning."
    wp.cmd_picture_maker()
    filled: list[pm.PictureSuggestion] = []
    window["page"].suggest(filled.append)
    assert "broadcasts from the hill" in ai.service.conversed[0]
    assert filled[0].description.startswith("A radio mast at dawn")
    assert filled[0].background == "solid" and filled[0].colour == "navy"
    assert "Sending the page's text" in wp.host.said
    assert wp.host.announced[-1] == "Suggestion ready. The page is about the station."


def test_suggest_sends_only_the_selection_when_there_is_one(wp, ai, window, openai) -> None:
    wp.host.text = "Secret draft notes. Our new studio opens in May."
    wp.host.selection = (20, len(wp.host.text))
    wp.cmd_picture_maker()
    window["page"].suggest(lambda _s: None)
    assert "Our new studio" in ai.service.conversed[0]
    assert "Secret draft" not in ai.service.conversed[0]
    assert "Sending the selection" in wp.host.said


def test_suggest_on_an_empty_page_sends_nothing(wp, ai, window, openai) -> None:
    wp.cmd_picture_maker()
    window["page"].suggest(lambda _s: None)
    assert ai.service.conversed == []
    assert "no text on the page" in wp.host.said


def test_suggest_with_no_description_changes_nothing(wp, ai, window, openai) -> None:
    wp.host.text = "Hello."
    ai.service.answer = "I would rather not."
    wp.cmd_picture_maker()
    filled: list[Any] = []
    window["page"].suggest(filled.append)
    assert filled == []
    assert "nothing was changed" in wp.host.said


def test_suggest_without_the_agreement_sends_nothing(wp, ai, window, openai) -> None:
    wp.host.text = "Hello."
    wp.cmd_picture_maker()
    ai.ready = False
    window["page"].suggest(lambda _s: None)
    assert ai.service.conversed == []


# --------------------------------------------------------------------------- #
# on a chosen version


def test_describe_image_looks_at_the_file(wp, ai, window, openai, tmp_path, wp_dialogs) -> None:
    wp.cmd_picture_maker()
    picture = _png(tmp_path / "chosen.png")
    window["page"].describe(picture)
    assert wp.host.looked[0][0] == picture
    assert "problems" in wp.host.looked[0][1]
    assert wp_dialogs.reports[-1]["title"] == "Describe Image: chosen.png"


def test_open_in_image_viewer(wp, ai, window, openai, tmp_path, monkeypatch) -> None:
    opened: list[Path] = []
    monkeypatch.setattr(pcmd, "open_in_viewer", opened.append)
    wp.cmd_picture_maker()
    picture = _png(tmp_path / "chosen.png")
    window["page"].open_viewer(picture)
    assert opened == [picture]


def test_save_as_copies_the_picture(wp, ai, window, openai, tmp_path, monkeypatch) -> None:
    target = tmp_path / "out" / "mine.png"
    target.parent.mkdir()
    answers = [target, None]
    monkeypatch.setattr(pcmd, "ask_save_picture", lambda _host, _path: answers.pop(0))
    wp.cmd_picture_maker()
    picture = _png(tmp_path / "chosen.png")
    window["page"].save_as(picture)
    assert target.read_bytes() == picture.read_bytes()
    assert wp.host.announced[-1] == "Saved a copy as mine.png."
    window["page"].save_as(picture)  # cancelled: nothing more said
    assert wp.host.announced[-1] == "Saved a copy as mine.png."


def _wordpress_document(wp, wp_dialogs, text_format="markdown"):
    wp_dialogs.answer(
        "ask_new_item",
        idlg.NewItemAnswer(
            site_index=0,
            title="Our Schedule",
            slug="our-schedule",
            text_format=text_format,
            category_ids=[],
            tag_ids=[],
        ),
    )
    wp.cmd_new_page()
    wp.host.announced.clear()


MEDIA = {
    "id": 90,
    "title": {"raw": "Mast"},
    "media_type": "image",
    "mime_type": "image/png",
    "source_url": "https://radio.example/wp-content/uploads/mast.png",
    "alt_text": "A radio mast at dawn",
    "media_details": {"width": 64, "height": 32},
}


def test_insert_outside_a_wordpress_document_says_so(wp, ai, window, openai, tmp_path) -> None:
    wp.cmd_picture_maker()
    window["page"].insert(_png(tmp_path / "chosen.png"))
    assert "This is not a WordPress document" in wp.host.said


def test_insert_cancelled_uploads_nothing(
    wp, ai, window, openai, tmp_path, wp_dialogs, wp_site
) -> None:
    _wordpress_document(wp, wp_dialogs)
    wp.cmd_picture_maker()
    window["page"].insert(_png(tmp_path / "chosen.png"))
    assert wp_dialogs.asked("ask_image")[0]["size_text"] == "Image is 64 by 32"
    assert wp_site.requests == []


def test_insert_uploads_on_insert_and_writes_the_picture(
    wp, ai, window, openai, tmp_path, wp_dialogs, wp_site
) -> None:
    _wordpress_document(wp, wp_dialogs)
    wp_site.on("POST", f"{API}/media", MEDIA).on("POST", f"{API}/media/90", MEDIA)
    wp_dialogs.answer(
        "ask_image",
        idlg.ImageAnswer(
            alt="A radio mast at dawn",
            decorative=False,
            caption="",
            width=0,
            featured=True,
            link="",
        ),
    )
    wp.cmd_picture_maker()
    window["page"].insert(_png(tmp_path / "chosen.png"))
    assert len(wp_site.sent("POST", f"{API}/media")) == 1
    assert wp_site.body(wp_site.sent("POST", f"{API}/media/90")[0])["alt_text"] == (
        "A radio mast at dawn"
    )
    assert "![A radio mast at dawn](https://radio.example/wp-content/uploads/mast.png)" in (
        wp.host.text
    )
    assert wp.host.announced[-1] == "Picture uploaded to Community Radio and inserted."
    copy = wp.local.copy_for_path(wp.host.current_path())
    assert copy.properties["featured_media"] == 90


# --------------------------------------------------------------------------- #
# the shared window itself


def test_the_window_carries_the_page_extras(wx_session_app, tmp_path) -> None:
    import wx

    frame = wx.Frame(None)
    requests: list[tuple[list[str], str, dict[str, Any]]] = []

    def request(turns, size, done, failed, **kwargs):
        requests.append((list(turns), size, kwargs))
        done(_png(tmp_path / "v1.png"), "Asked for: a mast")

    inserted: list[Path] = []
    page = maker.PageExtras(transparent=False, insert=inserted.append)
    dialog = maker.PictureMakerDialog(
        frame, request=request, make_video=None, announce=lambda _t: None, page=page
    )
    try:
        labels = [dialog.background.GetString(i) for i in range(dialog.background.GetCount())]
        assert labels == ["Normal", "Solid colour"]  # no Transparent for this provider
        assert not dialog.video.IsShown()
        dialog.fill(pm.PictureSuggestion("A mast", "square", "solid", "navy", "why"))
        assert dialog.words.GetValue() == "A mast"
        assert dialog.background_choice() == ("solid", "navy")
        dialog._on_make(None)
        assert requests == [(["A mast"], "square", {"background": "solid", "colour": "navy"})]
        dialog.page_buttons[0].Command(wx.CommandEvent(wx.wxEVT_BUTTON))
        assert inserted == [tmp_path / "v1.png"]
    finally:
        dialog.Destroy()
        frame.Destroy()
