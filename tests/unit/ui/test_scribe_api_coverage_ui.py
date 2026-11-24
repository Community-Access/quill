"""The Scribe windows' side of the API coverage audit (docs/design/scribe-api-coverage.md).

* A sign-in that fails while the person is still in the browser is said
  when they come back to the sign-in window, not into the background.
* Rename with a name over Scribe's 255-character limit asks again, with the
  typed name kept, and nothing is sent until the name fits.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from quill.core.scribe.client import TITLE_LIMIT
from quill.core.scribe.model import DocumentSummary

pytestmark = pytest.mark.usefixtures("wx_session_app")


def _now(fn: Any, *args: Any) -> None:
    fn(*args)


def _later(_ms: int, fn: Any, *args: Any) -> None:
    fn(*args)


def _signin_stub(active: bool) -> Any:
    said: list[str] = []
    stub = SimpleNamespace(
        IsActive=lambda: active,
        RequestUserAttention=lambda: said.append("<attention>"),
        _controller=SimpleNamespace(host=SimpleNamespace(scribe_announce=said.append)),
        _pending_sentence="",
        _heard_in_background=False,
    )
    stub.said = said
    return stub


def _activate(active: bool = True) -> Any:
    return SimpleNamespace(GetActive=lambda: active, Skip=lambda: None)


def test_a_sign_in_refused_in_the_background_is_said_on_coming_back(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from quill.ui import scribe_signin_dialog as module

    monkeypatch.setattr(module.wx, "CallLater", _later)
    stub = _signin_stub(active=False)
    sentence = "Scribe for Documents did not sign you in. Try again."
    module.ScribeSignInDialog._say_when_seen(stub, sentence)
    assert stub.said == ["<attention>"]
    module.ScribeSignInDialog._on_activate(stub, _activate())
    module.ScribeSignInDialog._on_activate(stub, _activate())  # said once, not on every return
    assert stub.said == ["<attention>", sentence]


def test_a_sign_in_refused_in_front_is_said_at_once(monkeypatch: pytest.MonkeyPatch) -> None:
    from quill.ui import scribe_signin_dialog as module

    monkeypatch.setattr(module.wx, "CallLater", _later)
    stub = _signin_stub(active=True)
    module.ScribeSignInDialog._say_when_seen(stub, "Sign-in timed out. Try again?")
    module.ScribeSignInDialog._on_activate(stub, _activate())
    assert stub.said == ["Sign-in timed out. Try again?"]


class _Entry:
    """wx.TextEntryDialog, answering with the next of *answers*."""

    answers: list[str] = []
    asked: list[tuple[str, str]] = []

    def __init__(self, _parent: Any, prompt: str, _title: str, value: str) -> None:
        _Entry.asked.append((prompt, value))

    def GetValue(self) -> str:  # noqa: N802 - wx API
        return _Entry.answers.pop(0)

    def Destroy(self) -> None:  # noqa: N802 - wx API
        pass


def test_rename_over_the_limit_asks_again_with_the_name_kept(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import wx

    from quill.ui import scribe_documents_dialog as module

    too_long = "x" * (TITLE_LIMIT + 45)
    _Entry.answers = [too_long, "Garden handbook"]
    _Entry.asked = []
    monkeypatch.setattr(module.wx, "TextEntryDialog", _Entry)
    monkeypatch.setattr(module.wx, "CallAfter", _now)
    monkeypatch.setattr(module, "show_modal_dialog", lambda *_a: wx.ID_OK)
    monkeypatch.setattr(module, "_select_all", lambda _d: None)
    acted: list[str] = []
    said: list[str] = []
    stub = SimpleNamespace(
        _act=lambda _doc, _call, sentence: acted.append(sentence),
        _controller=SimpleNamespace(host=SimpleNamespace(scribe_announce=said.append)),
    )
    stub._rename = lambda doc, typed=None: module.ScribeDocumentsDialog._rename(stub, doc, typed)
    doc = DocumentSummary(id="d1", title="Notes.pdf")
    stub._rename(doc)
    assert _Entry.asked[0] == ("&New name:", doc.display_title)
    assert _Entry.asked[1] == (
        f"This name has {TITLE_LIMIT + 45} characters, and a name can have at most "
        f"{TITLE_LIMIT}. &New name:",
        too_long,
    )
    assert acted == ["Renamed to Garden handbook."] and said == []
