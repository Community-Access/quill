"""The AI pad offers the service catalogue's extra tools as rows of its own list.

A tool the server describes and this build does not have becomes one more row
at the end of "What do you want done?": its label is the row, its help sentence
is what F1 reads on it, and Send runs it through the same path as every
built-in row. Only on the free service, never twice, and never by crashing on
something the client does not understand. No network: the service is a fake.
"""

from __future__ import annotations

from typing import Any

import pytest

from tests.wx_session import shared_wx_app

wx = pytest.importorskip("wx")

from quill.core.ai.gateway_catalogue import parse_catalogue  # noqa: E402
from quill.core.ai.gateway_client import GatewayLimits  # noqa: E402
from quill.core.ai.writing_tools import ACTIONS  # noqa: E402

_CATALOGUE = [
    {"id": "summarize", "label": "Summarize", "help": "Built in already.", "input": "selection"},
    {
        "id": "find_dates",
        "label": "Find dates",
        "help": "Every date the passage mentions, one per line.",
        "input": "selection",
        "max_input_tokens": 1500,
    },
    {"id": "define", "label": "Define a word", "help": "Type a word.", "input": "prompt"},
    {
        "id": "quote_finder",
        "label": "Find a quotation",
        "help": "Type what it was about.",
        "input": "document",
    },
    {"id": "picture", "label": "Draw it", "help": "Not a kind this build knows.", "input": "image"},
]


def _limits(features: list[dict] | None = None, max_input: int = 3000) -> GatewayLimits:
    return GatewayLimits(
        max_input_tokens=max_input, features=parse_catalogue(features or _CATALOGUE)
    )


@pytest.fixture(scope="module")
def wx_app():
    app = shared_wx_app()
    wx.HelpProvider.Set(wx.SimpleHelpProvider())  # SetHelpText stores nothing without one
    yield app


class _Service:
    own_key_active = False

    def __init__(self, limits: GatewayLimits | None = None, *, direct: bool = False) -> None:
        self.direct = direct
        self.limits = self.free_limits = limits or GatewayLimits(max_input_tokens=3000)
        self.sent: list[tuple[str, str, list[str] | None]] = []

    def unavailable_reason(self, _feature: str = "") -> str:
        return ""

    def ask(self, feature, prompt, chunks, *, on_done, on_error, **_kw) -> None:  # noqa: ANN001
        self.sent.append((feature, prompt, chunks))


_DOCUMENT = "# Diary\n\nThe fair opens on 3 May. Rent is due on 9 June."


def _pad(service: _Service, action: str = "", said: list[str] | None = None) -> Any:
    from quill.ui.hosted_ai_pad import AiPadFrame

    return AiPadFrame(
        None,
        service,
        document_text=_DOCUMENT,
        selection="The fair opens on 3 May.",
        position=0,
        announce=(said if said is not None else []).append,
        on_result=lambda *_args: None,
        initial_action=action,
    )


def _labels(pad: Any) -> list[str]:
    return [pad._actions.GetString(i) for i in range(pad._actions.GetCount())]


def _choose(pad: Any, label: str) -> None:
    pad._actions.SetSelection(_labels(pad).index(label))
    pad._on_action_changed()


def test_a_cached_catalogue_adds_only_what_is_not_built_in(wx_app) -> None:
    pad = _pad(_Service(_limits()))
    try:
        built = [label for _id, label, _help in ACTIONS]
        assert _labels(pad) == [*built, "Find dates", "Define a word", "Find a quotation"]
    finally:
        pad.Destroy()


def test_f1_on_an_extra_row_reads_the_servers_help(wx_app) -> None:
    pad = _pad(_Service(_limits()))
    try:
        _choose(pad, "Find dates")
        assert pad._actions.GetHelpText().startswith(
            "Find dates: Every date the passage mentions, one per line."
        )
    finally:
        pad.Destroy()


def test_a_passage_tool_sends_the_passage_like_summarize(wx_app) -> None:
    service = _Service(_limits())
    pad = _pad(service)
    try:
        _choose(pad, "Find dates")
        assert not pad._question.IsShown()
        pad._on_send(None)
        assert service.sent == [("find_dates", "The fair opens on 3 May.", None)]
    finally:
        pad.Destroy()


def test_a_typed_tool_sends_only_what_was_typed(wx_app) -> None:
    service = _Service(_limits())
    pad = _pad(service)
    try:
        _choose(pad, "Define a word")
        assert pad._question.IsShown()
        assert "Nothing from this document is sent" in pad._summary.GetValue()
        pad._question.SetValue("ephemeral")
        pad._on_send(None)
        assert service.sent == [("define", "ephemeral", None)]
    finally:
        pad.Destroy()


def test_a_document_tool_sends_the_question_and_excerpts(wx_app) -> None:
    service = _Service(_limits())
    pad = _pad(service)
    try:
        _choose(pad, "Find a quotation")
        pad._question.SetValue("rent")
        pad._on_send(None)
        ((feature, prompt, chunks),) = service.sent
        assert (feature, prompt) == ("quote_finder", "rent")
        assert chunks and any("Rent is due" in chunk for chunk in chunks)
    finally:
        pad.Destroy()


def test_rows_that_arrive_later_are_appended_and_the_current_row_stays(wx_app) -> None:
    service = _Service()
    pad = _pad(service, action="rewrite")
    try:
        before = _labels(pad)
        assert before == [label for _id, label, _help in ACTIONS]
        pad.add_catalogue_rows(_limits())
        pad.add_catalogue_rows(_limits())  # a second refresh adds nothing twice
        assert _labels(pad) == [*before, "Find dates", "Define a word", "Find a quotation"]
        assert pad._action_id == "rewrite"
    finally:
        pad.Destroy()


def test_rows_arriving_after_the_pad_closed_are_ignored(wx_app) -> None:
    pad = _pad(_Service())
    pad.Destroy()
    wx_app.Yield()
    pad.add_catalogue_rows(_limits())  # must not raise


def test_no_extras_on_an_own_key_or_plan(wx_app) -> None:
    pad = _pad(_Service(_limits(), direct=True))
    try:
        pad.add_catalogue_rows(_limits())
        assert _labels(pad) == [label for _id, label, _help in ACTIONS]
    finally:
        pad.Destroy()


def test_a_smaller_ceiling_for_one_tool_is_honoured(wx_app) -> None:
    features = [
        {
            "id": "tiny",
            "label": "Tiny tool",
            "help": "Takes very little.",
            "input": "selection",
            "max_input_tokens": 2,
        }
    ]
    service = _Service(_limits(features))
    said: list[str] = []
    pad = _pad(service, said=said)
    try:
        _choose(pad, "Tiny tool")
        assert "will be refused" in pad._summary.GetValue()
        pad._on_send(None)
        assert service.sent == []
        assert any("free limit" in sentence for sentence in said)
    finally:
        pad.Destroy()


def test_try_again_lands_on_the_same_extra_row(wx_app) -> None:
    pad = _pad(_Service(_limits()), action="define")
    try:
        assert pad._action_id == "define"
    finally:
        pad.Destroy()
