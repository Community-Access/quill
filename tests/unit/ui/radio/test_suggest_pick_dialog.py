"""Suggest a Station or Podcast goes to support by email, never to GitHub.

Since 2026-09-26 every piece of feedback from Quill Radio goes to
support@community-access.org, and the suggestion form reuses Get Help from
Support's mail handoff rather than posting a GitHub issue with a bundled token.
Driven against the submit path with fake fields, because what matters is the
behaviour: what the mail program is handed, what is said, and what is *not*
touched -- no GitHub, no token, no network.
"""

from __future__ import annotations

import urllib.request
from urllib.parse import parse_qs, unquote, urlsplit

import pytest

from quill.core.pick_suggestion import Suggestion, support_message
from quill.core.support_message import SUPPORT_EMAIL
from quill.ui import support_dialog
from quill.ui.radio import suggest_pick_dialog


class _Host:
    frame = object()
    _app_version = "3.0.0"

    def __init__(self) -> None:
        self.spoken: list[str] = []
        self.boxes: list[tuple[str, str]] = []
        self.clipboard: list[str] = []

    def _announce(self, text: str) -> None:
        self.spoken.append(text)

    def _show_message_box(self, message: str, caption: str, _style: int) -> int:
        self.boxes.append((message, caption))
        return 0

    def _copy_to_clipboard(self, text: str) -> bool:
        self.clipboard.append(text)
        return True


class _Field:
    def __init__(self, value: str = "") -> None:
        self._value = value

    def GetValue(self) -> str:
        return self._value


class _Kind:
    def __init__(self, index: int) -> None:
        self._index = index

    def GetSelection(self) -> int:
        return self._index


class _FakeWx:
    ID_OK = 5100
    OK = 4
    ICON_INFORMATION = 16


def _dialog(host: _Host, **fields: str) -> suggest_pick_dialog._SuggestDialog:
    dialog = suggest_pick_dialog._SuggestDialog(host, _FakeWx())
    dialog._kind = _Kind(1 if fields.get("kind") == "podcast" else 0)
    dialog._title_ctrl = _Field(fields.get("title", "Radio Nowhere"))
    dialog._url = _Field(fields.get("url", "https://stream.example.org/nowhere"))
    dialog._description = _Field(fields.get("description", "Talk and folk."))
    dialog._language = _Field(fields.get("language", "en"))
    dialog._why = _Field(fields.get("why", "Run by blind volunteers."))
    dialog.ended: list[int] = []
    dialog.dialog = type("D", (), {"EndModal": lambda _self, code: dialog.ended.append(code)})()
    return dialog


@pytest.fixture
def no_network(monkeypatch: pytest.MonkeyPatch) -> None:
    """Any attempt to reach the network -- GitHub or otherwise -- fails the test."""

    def _refuse(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("Suggest must not make a network request")

    monkeypatch.setattr(urllib.request, "urlopen", _refuse)


def _parts(url: str) -> tuple[str, str, str]:
    split = urlsplit(url)
    query = parse_qs(split.query)
    return unquote(split.path), query["subject"][0], query["body"][0]


def test_send_opens_a_support_mail_with_the_suggestion(
    monkeypatch: pytest.MonkeyPatch, no_network: None
) -> None:
    launched: list[str] = []
    monkeypatch.setattr(support_dialog, "_launch", lambda url: launched.append(url) or True)

    host = _Host()
    dialog = _dialog(host)
    dialog._submit()

    assert len(launched) == 1 and launched[0].startswith("mailto:")
    address, subject, body = _parts(launched[0])
    assert address == SUPPORT_EMAIL
    assert subject == "[Quill Radio 3.0.0] Suggestion: Radio Nowhere"
    assert "suggest a radio station for the Community Picks list" in body
    assert "- Address: https://stream.example.org/nowhere" in body
    assert "Talk and folk." in body
    assert "Run by blind volunteers." in body
    assert "github" not in launched[0].lower()
    assert host.spoken == [suggest_pick_dialog.OPENED]
    assert "Press Send there" in host.spoken[0]
    assert dialog.ended == [_FakeWx.ID_OK]


def test_no_mail_program_leaves_the_suggestion_and_the_address(
    monkeypatch: pytest.MonkeyPatch, no_network: None
) -> None:
    monkeypatch.setattr(support_dialog, "_launch", lambda _url: False)

    host = _Host()
    dialog = _dialog(host)
    dialog._submit()

    assert host.clipboard and host.clipboard[0].startswith(f"To: {SUPPORT_EMAIL}")
    assert "Radio Nowhere" in host.clipboard[0]
    message, caption = host.boxes[0]
    assert SUPPORT_EMAIL in message and caption == suggest_pick_dialog.TITLE
    # The window stays open, so what was typed is still there.
    assert dialog.ended == []


def test_a_too_long_suggestion_is_cut_and_the_whole_text_copied(
    monkeypatch: pytest.MonkeyPatch, no_network: None
) -> None:
    monkeypatch.setattr(support_dialog, "_launch", lambda _url: True)

    host = _Host()
    _dialog(host, why="Worth it. " * 400)._submit()

    assert host.clipboard and "Worth it. " * 50 in host.clipboard[0]
    assert "complete text is on your clipboard" in host.spoken[0]


def test_a_duplicate_is_refused_before_any_mail_is_written(
    monkeypatch: pytest.MonkeyPatch, no_network: None
) -> None:
    launched: list[str] = []
    monkeypatch.setattr(support_dialog, "_launch", lambda url: launched.append(url) or True)
    monkeypatch.setattr(
        suggest_pick_dialog, "known_urls", lambda _catalogue: {"stream.example.org/nowhere"}
    )

    host = _Host()
    dialog = _dialog(host)
    dialog._submit()

    assert launched == []
    assert "already in the Community Picks list" in host.spoken[0]
    assert dialog.ended == []


def test_the_dialog_never_reaches_for_github_or_the_token() -> None:
    """Source-level: the token module and the GitHub API are simply not there."""
    from pathlib import Path

    source = Path(suggest_pick_dialog.__file__).read_text(encoding="utf-8")
    code = source.split('"""', 2)[2]  # past the module docstring's history note
    for banned in (
        "feedback_token",
        "api.github.com",
        "github.com",
        "urllib",
        "LaunchDefaultBrowser",
    ):
        assert banned not in code, banned


def test_support_message_names_a_podcast_as_a_podcast() -> None:
    message = support_message(
        Suggestion(type="podcast", title="Blind Abilities", url="https://feed.example.org/rss"),
        product="Quill Radio 3.0.0",
    )
    assert message.summary == "Suggestion: Blind Abilities"
    assert "suggest a podcast" in message.message
    assert message.category == "Station or podcast suggestion"
