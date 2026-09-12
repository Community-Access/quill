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


def test_the_server_path_is_skipped_when_nothing_can_post_to_it(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Falling back to GitHub is the one thing that must never happen: the
    repository is public and a support message is somebody's own words."""
    import quill.core.feedback_token as feedback_token

    monkeypatch.setattr(feedback_token, "server_transport_available", lambda: False)
    assert (
        support_dialog._server_path(
            _Host(), "Quill Radio 3.0.0", prefill_summary="", prefill_body=""
        )
        is False
    )


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
