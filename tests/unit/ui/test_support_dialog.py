"""Get Help from Support: what the surface actually does when you press Send.

Driven against the submit path rather than a real wx dialog, because what
matters here is the behaviour nobody sees until it is wrong: that a bad form
says which field to fix, that the mail handoff is described honestly ("nothing
is sent until you send it there"), and that a machine with no mail program
still ends up holding the message and the address instead of nothing.
"""

from __future__ import annotations

import pytest

from quill.core.support_message import SUPPORT_EMAIL
from quill.ui import support_dialog


class _Host:
    """The smallest host the flow needs. Every app shape reduces to this."""

    def __init__(self) -> None:
        self.frame = object()
        self.spoken: list[str] = []
        self.boxes: list[str] = []
        self.clipboard: list[str] = []

    def _announce(self, text: str) -> None:
        self.spoken.append(text)

    def _show_message_box(self, message: str, _caption: str, _style: int) -> None:
        self.boxes.append(message)

    def _copy_to_clipboard(self, text: str) -> bool:
        self.clipboard.append(text)
        return True


class _Field:
    def __init__(self, value: str = "") -> None:
        self._value = value

    def GetValue(self) -> str:
        return self._value

    def SetValue(self, value: str) -> None:
        self._value = value


class _Choice:
    def __init__(self, value: str) -> None:
        self._value = value

    def GetStringSelection(self) -> str:
        return self._value


class _FakeWx:
    ID_OK = 5100
    OK = 4
    ICON_INFORMATION = 16


def _dialog(host: _Host, **fields: str) -> support_dialog._SupportDialog:
    dialog = support_dialog._SupportDialog.__new__(support_dialog._SupportDialog)
    dialog._host = host
    dialog._wx = _FakeWx()
    dialog._product = "Quill Radio 3.0.0"
    dialog._summary = _Field(fields.get("summary", "Stream stops"))
    dialog._message = _Field(fields.get("message", "It stops after a second."))
    dialog._expected = _Field(fields.get("expected", ""))
    dialog._steps = _Field(fields.get("steps", ""))
    dialog._email = _Field(fields.get("email", "reader@example.com"))
    dialog._kind = _Choice(fields.get("kind", "Something is broken"))
    dialog._reader = _Choice(fields.get("reader", "JAWS"))
    dialog.ended: list[int] = []
    dialog.dialog = type("D", (), {"EndModal": lambda _self, code: dialog.ended.append(code)})()
    return dialog


def test_an_incomplete_form_names_the_field_to_fix(monkeypatch: pytest.MonkeyPatch) -> None:
    """Spoken first, shown in full second: a list of problems read out at once
    is a list nobody retains."""
    launched: list[str] = []
    monkeypatch.setattr(support_dialog, "_launch", lambda url: launched.append(url) or True)

    host = _Host()
    _dialog(host, summary="", message="")._submit()

    assert launched == []
    assert "subject" in host.spoken[0]
    assert host.boxes and "Describe what happened" in host.boxes[0]


def test_sending_hands_the_message_to_the_mail_program_and_says_it_is_not_sent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    launched: list[str] = []
    monkeypatch.setattr(support_dialog, "_launch", lambda url: launched.append(url) or True)

    host = _Host()
    dialog = _dialog(host)
    dialog._submit()

    assert launched and launched[0].startswith("mailto:")
    assert SUPPORT_EMAIL in launched[0]
    spoken = " ".join(host.spoken)
    assert "Nothing is sent until you send it there" in spoken
    assert dialog.ended == [_FakeWx.ID_OK]


def test_send_includes_selected_reader_version_in_the_mail_body(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from quill.core import support_screen_reader

    monkeypatch.setattr(
        support_screen_reader,
        "screen_reader_support_facts",
        lambda selected: (
            {"Screen reader version": "2026.2608.25.400"} if selected == "JAWS" else {}
        ),
    )
    launched: list[str] = []
    monkeypatch.setattr(support_dialog, "_launch", lambda url: launched.append(url) or True)

    _dialog(_Host())._submit()

    from urllib.parse import parse_qs, urlparse

    body = parse_qs(urlparse(launched[0]).query)["body"][0]
    assert "Screen reader: JAWS" in body
    assert "Screen reader version: 2026.2608.25.400" in body


def test_no_mail_program_still_leaves_the_message_and_the_address(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Webmail-only machines are the reason this branch exists. Ending with
    "nothing happened" would be the one outcome worse than the old form."""
    monkeypatch.setattr(support_dialog, "_launch", lambda _url: False)

    host = _Host()
    dialog = _dialog(host)
    dialog._submit()

    assert host.clipboard and SUPPORT_EMAIL in host.clipboard[0]
    assert "It stops after a second." in host.clipboard[0]
    assert host.boxes and SUPPORT_EMAIL in host.boxes[0]
    assert dialog.ended == []


def test_an_app_with_an_announcer_instead_of_a_shell_still_speaks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """QuillBeacon speaks through an Announcer, not through _announce.

    Without the fallback its support form would show every message and say none
    of them -- silent in exactly the place the app is telling you something the
    screen reader cannot know.
    """
    monkeypatch.setattr(support_dialog, "_launch", lambda _url: True)

    said: list[tuple[str, str]] = []

    class _Beaconish:
        announcer = type(
            "A", (), {"say": staticmethod(lambda text, level: said.append((text, level)))}
        )()

    dialog = _dialog(_Host())
    dialog._host = _Beaconish()
    dialog._submit()

    assert said and "Nothing is sent until you send it there" in said[0][0]


def test_support_never_goes_through_feedback_hub() -> None:
    """2026-09-26: every message goes to support@ by email. The feedback-hub
    dialog (and its GitHub token) is not a transport any more."""
    import inspect

    source = inspect.getsource(support_dialog)
    assert "feedback_hub" not in source
    assert "github_token" not in source
    assert not hasattr(support_dialog, "_server_path")
