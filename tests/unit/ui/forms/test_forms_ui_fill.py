"""Fill It In Yourself: the session (what is heard) and the window (what is drawn)."""

from __future__ import annotations

from typing import Any

import pytest

from quill.ui import forms_doc as fd
from quill.ui.forms_fill import FillSession, localize

TWO_PAGES = """bfl 1
form "Club"

text #name "Your name"
  @required
radio #member "Already a member?"
  + Yes
  + No
text #number "Membership number"
  @when #member is "yes"
number #tickets "Tickets"
  @default 2
number #cost "Cost"
  @calculate #tickets * 5

page "Second"

textarea #notes "Anything else?"
"""


def _session(text: str = TWO_PAGES) -> FillSession:
    return FillSession(fd.read(text).model)


def test_a_rule_shows_and_hides_a_question_and_says_so() -> None:
    session = _session()
    assert not session.is_shown({"id": "number"})
    assert session.answer("member", "yes").sentence() == "Membership number appears."
    assert session.answer("member", "no").sentence() == "Membership number is hidden."
    assert session.answer("name", "Jo").sentence() == ""


def test_defaults_start_filled_and_calculations_follow() -> None:
    session = _session()
    assert session.answers["tickets"] == 2
    assert session.worked_out("cost") == "10"
    session.answer("tickets", "3")
    assert session.worked_out("cost") == "15"


def test_next_stops_at_a_missing_answer_and_back_returns() -> None:
    session = _session()
    assert session.heading() == "Page 1 of 2"
    assert session.missing_here() == ["Your name"]
    assert not session.back_possible() and not session.is_last()
    session.answer("name", "Jo")
    assert session.missing_here() == []
    assert session.next() and session.heading() == "Page 2 of 2: Second"
    assert session.is_last() and not session.next()
    assert session.back() and session.page == 0


def test_submit_sends_nothing_and_lists_each_answer() -> None:
    session = _session()
    session.answer("member", "yes")
    summary = session.summary()
    assert summary.startswith("Nothing was sent.")
    assert "Already a member?: Yes" in summary
    assert "Membership number: no answer" in summary
    assert "Cost: 10" in summary
    assert "Still needs an answer: Your name." in summary


def test_each_translation_can_be_tried() -> None:
    model = fd.read(TWO_PAGES).model
    model["translations"] = {
        "fr": {
            "title": "Club",
            "fields": {"name": {"label": "Votre nom"}, "member": {"choices": {"yes": "Oui"}}},
        }
    }
    session = FillSession(model)
    assert session.languages() == ["en", "fr"]
    session.set_language("fr")
    labels = {i["id"]: i.get("label") for _d, i in session.page_items()}
    assert labels["name"] == "Votre nom"
    assert localize(model, "fr")["pages"][0]["items"][1]["choices"][0]["label"] == "Oui"
    assert localize(model, "en") == model


def test_a_hidden_page_is_skipped() -> None:
    text = TWO_PAGES.replace('page "Second"', 'page "Second"\n  @when #member is "yes"')
    session = _session(text)
    session.answer("name", "Jo")
    assert session.is_last()
    session.answer("member", "yes")
    assert not session.is_last()


# -- the window ---------------------------------------------------------------- #


@pytest.fixture
def window(wx_session_app: Any) -> Any:
    import wx

    from quill.ui.forms_fill_window import FillWindow

    said: list[str] = []
    frame = wx.Frame(None)
    win = FillWindow(frame, _session(), announce=said.append, show_modal=lambda d, label: 0)
    win.said = said
    yield win
    win.Destroy()
    frame.Destroy()


def test_the_window_draws_a_native_control_per_question(window: Any) -> None:
    import wx

    assert isinstance(window.first["name"], wx.TextCtrl)
    assert isinstance(window.first["member"], wx.RadioButton)
    assert isinstance(window.worked["cost"], wx.TextCtrl)
    assert window.worked["cost"].GetValue() == "10"
    assert not any(w.IsShown() for w in window.rows["number"])
    assert window.heading.GetLabel() == "Page 1 of 2"
    assert window.submit.IsEnabled() is False and window.next.IsEnabled()


def test_answering_in_the_window_shows_a_question_and_says_so(window: Any) -> None:
    window.answer("member", "yes")
    assert window.said == ["Membership number appears."]
    assert all(w.IsShown() for w in window.rows["number"])


def test_next_with_a_missing_answer_says_which(window: Any) -> None:
    window.go(1)
    assert window.said == ["1 question needs an answer: Your name."]
    assert window.session.page == 0
    window.answer("name", "Jo")
    window.go(1)
    assert window.said[-1] == "Page 2 of 2: Second"
    assert window.submit.IsEnabled()


def test_submit_shows_the_report(window: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    from quill.ui import wordpress_dialogs as dlg

    shown: list[dict[str, Any]] = []
    monkeypatch.setattr(dlg, "show_report", lambda _p, _m, **kw: shown.append(kw))
    window.on_submit()
    assert shown[0]["title"] == "What Would Be Sent"
    assert shown[0]["text"].startswith("Nothing was sent.")
