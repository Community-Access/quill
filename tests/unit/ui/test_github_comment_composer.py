"""The Workbench's comment composer: inserts, preview, the check, and posting."""

from __future__ import annotations

from typing import Any

import pytest
import wx

from quill.ui.github_comment_composer import CommentComposer, compose_comment
from tests.unit.core.github_workbench.test_comment_compose import FakeApi
from tests.wx_session import shared_wx_app


class _Host:
    """What the Workbench gives the composer: dialogs answered, background run at once."""

    def __init__(self, answers: list[Any] | None = None) -> None:
        self.answers = list(answers or [])
        self.shown: list[str] = []
        self.said: list[str] = []

    def show_modal(self, dialog: Any, title: str) -> int:
        self.shown.append(title)
        answer = self.answers.pop(0) if self.answers else wx.ID_OK
        if isinstance(answer, tuple):
            answer, value = answer
            dialog.SetValue(value)
        return int(answer)

    def background(self, _name: str, work: Any, done: Any) -> None:
        done(work())


@pytest.fixture
def frame():
    shared_wx_app()
    window = wx.Frame(None)
    yield window
    window.Destroy()


def _composer(frame: wx.Frame, host: _Host, api: Any = None, text: str = "") -> CommentComposer:
    return CommentComposer(
        frame,
        title="Comment on #7",
        api=api or FakeApi(),
        repository="o/r",
        people=["jeff"],
        text=text,
        background=host.background,
        show_modal=host.show_modal,
        say=host.said.append,
    )


def test_a_mention_is_chosen_from_the_conversation_first(frame: wx.Frame) -> None:
    host = _Host()
    api = FakeApi(rest={"/repos/o/r/assignees": [{"login": "ada"}]})
    composer = _composer(frame, host, api, text="Thanks")
    composer.box.SetInsertionPointEnd()
    composer.insert_mention()
    assert composer.text() == "Thanks @jeff"
    assert host.said == ["Inserted @jeff."]
    composer.Destroy()


def test_a_reference_is_found_by_words_and_inserted(frame: wx.Frame) -> None:
    host = _Host([(wx.ID_OK, "parser"), wx.ID_OK])
    api = FakeApi(
        rest={"/search/issues": {"items": [{"number": 4, "title": "Parser", "state": "open"}]}}
    )
    composer = _composer(frame, host, api)
    composer.insert_reference()
    assert composer.text() == "#4"
    assert host.shown == ["Insert Reference", "Insert Reference"]
    composer.Destroy()


def test_no_saved_replies_says_where_to_make_them(frame: wx.Frame) -> None:
    host = _Host()
    composer = _composer(frame, host, FakeApi(graphql={"viewer": {"savedReplies": {"nodes": []}}}))
    composer.insert_saved_reply()
    assert "Saved replies" in host.said[0] and composer.text() == ""
    composer.Destroy()


def test_attach_files_says_why_it_cannot(frame: wx.Frame) -> None:
    host = _Host()
    composer = _composer(frame, host)
    composer.attach_files()
    assert host.said and host.said[0].startswith("GitHub has no way")
    composer.Destroy()


def test_preview_reads_the_comment_into_its_box(frame: wx.Frame) -> None:
    composer = _composer(frame, _Host(), text="## Plan\n- [ ] Run it")
    composer.preview()
    assert composer.preview_box.GetValue() == "Heading 2: Plan\nNot done: Run it"
    composer.Destroy()


def test_the_check_asks_and_no_keeps_you_writing(frame: wx.Frame) -> None:
    host = _Host([wx.ID_NO])
    composer = _composer(frame, host, text="![](shot.png)")
    composer.post()
    assert host.shown == ["Check Before Posting"]
    assert composer.IsModal() is False and composer.GetReturnCode() != wx.ID_OK
    composer.Destroy()


def test_the_check_can_be_turned_off(frame: wx.Frame) -> None:
    host = _Host()
    composer = _composer(frame, host, text="![](shot.png)")
    composer.check.SetValue(False)
    ended: list[int] = []
    composer.EndModal = ended.append  # type: ignore[method-assign]
    composer.post()
    assert ended == [wx.ID_OK] and host.shown == []
    composer.Destroy()


def test_an_empty_comment_is_never_posted(frame: wx.Frame) -> None:
    host = _Host()
    composer = _composer(frame, host, text="   ")
    ended: list[int] = []
    composer.EndModal = ended.append  # type: ignore[method-assign]
    composer.post()
    assert ended == [] and host.said == ["Write a comment first."]
    composer.Destroy()


def test_compose_returns_the_text_or_nothing_on_cancel(frame: wx.Frame) -> None:
    for answer, wanted in ((wx.ID_CANCEL, ""), (wx.ID_OK, "")):
        host = _Host([answer])
        said = compose_comment(
            frame,
            host.show_modal,
            title="Comment on #7",
            api=FakeApi(),
            repository="o/r",
            background=host.background,
            say=host.said.append,
        )
        assert said == wanted


def test_every_control_has_help_and_no_access_key_is_used_twice(frame: wx.Frame) -> None:
    from quill.ui.app_context_help import ensure_help_provider

    ensure_help_provider()
    composer = _composer(frame, _Host())
    letters = []
    for child in composer.GetChildren():
        label = child.GetLabel() if hasattr(child, "GetLabel") else ""
        if "&" in label:
            letters.append(label[label.index("&") + 1].lower())
        if isinstance(child, (wx.Button, wx.TextCtrl, wx.CheckBox)):
            assert child.GetHelpText(), label or child.GetName()
    assert len(letters) == len(set(letters)), letters
    composer.Destroy()
