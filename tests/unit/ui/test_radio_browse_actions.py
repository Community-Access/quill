"""The "Add a Server..." / "Add a Channel..." rows actually do something now.

Before this, ``BrowseNode`` carried an ``is_action`` kind that nothing handled:
both rows appeared in the tree and did nothing at all on Enter, which left My
Servers and YouTube Channels unable to accept their first entry. These pin the
behaviour that replaced it -- including the two refusals that matter more than
the happy path: an address that answers with nothing is **not** stored, and Safe
Mode says so rather than failing quietly.

A stand-in host, like the other ``ui/radio`` helper-module tests: the module
takes a host and touches only that, so a real window would add a wx frame to the
test and prove nothing extra.
"""

from __future__ import annotations

from typing import Any

import pytest

from quill.ui.radio import browse_actions


class _Entry:
    """Stands in for wx.TextEntryDialog."""

    def __init__(self, value: str, ok: bool) -> None:
        self._value = value
        self._ok = ok
        self.destroyed = False

    def ShowModal(self) -> int:  # noqa: N802 - wx's own casing
        return 5100 if self._ok else 5101

    def GetValue(self) -> str:  # noqa: N802
        return self._value

    def Destroy(self) -> None:  # noqa: N802
        self.destroyed = True


class _Clipboard:
    def Open(self) -> bool:  # noqa: N802
        return False

    def GetData(self, _obj: Any) -> bool:  # noqa: N802
        return False

    def Close(self) -> None:  # noqa: N802
        return None


class _Wx:
    ID_OK = 5100
    ID_CANCEL = 5101

    def __init__(self, typed: str = "", ok: bool = True) -> None:
        self.typed = typed
        self.ok = ok
        self.last_entry: _Entry | None = None
        self.TheClipboard = _Clipboard()

    def TextDataObject(self) -> Any:  # noqa: N802
        class _Data:
            def GetText(self) -> str:  # noqa: N802
                return ""

        return _Data()

    def TextEntryDialog(self, _parent: Any, _prompt: str, _title: str, value: str = "") -> _Entry:  # noqa: N802
        self.last_entry = _Entry(self.typed, self.ok)
        return self.last_entry


class _Tasks:
    """Runs submitted work immediately, so a test reads top to bottom."""

    def __init__(self) -> None:
        self.submitted: list[str] = []

    def submit(self, name: str, work: Any, *, on_success: Any = None, on_failure: Any = None):
        self.submitted.append(name)
        try:
            result = work()
        except Exception as exc:  # noqa: BLE001 - mirrors the task manager
            if on_failure is not None:
                on_failure(name, exc)
            return
        if on_success is not None:
            on_success(name, result)


class _Host:
    def __init__(self, *, typed: str = "", ok: bool = True, safe_mode: bool = False) -> None:
        self._wx = _Wx(typed, ok)
        self._win = object()
        self._tree = object()  # truthy: the window is still open
        self._safe_mode = safe_mode
        self._task_manager = _Tasks()
        self.said: list[str] = []
        self.reloaded: list[str] = []

    def _announce(self, message: str) -> None:
        self.said.append(message)

    def _reload_source_branch(self, node_id: str) -> None:
        self.reloaded.append(node_id)


def test_a_known_action_runs_and_an_unknown_one_is_ignored() -> None:
    host = _Host(typed="", ok=False)

    browse_actions.perform(host, "addserver")
    assert host._wx.last_entry is not None  # it asked

    host2 = _Host()
    browse_actions.perform(host2, "no-such-action")
    assert host2.said == []
    assert host2._wx.last_entry is None


def test_is_action_id_knows_both_rows() -> None:
    assert browse_actions.is_action_id("addserver")
    assert browse_actions.is_action_id("addchannel")
    assert not browse_actions.is_action_id("librivox")


def test_adding_a_server_probes_first_and_stores_it(monkeypatch: pytest.MonkeyPatch) -> None:
    from quill.core.radio import my_servers

    added: list[str] = []
    monkeypatch.setattr(my_servers, "probe", lambda root, safe_mode=False: (root, 4))
    monkeypatch.setattr(my_servers.ServerStore, "add", lambda self, url, name="": added.append(url))

    host = _Host(typed="http://stream.example.org:8000")
    browse_actions.perform(host, "addserver")

    assert added == ["http://stream.example.org:8000"]
    # The count is spoken, because "added" alone does not tell you it works.
    assert any("4 stations" in m for m in host.said)
    assert host.reloaded == ["myservers"]


def test_a_server_with_nothing_on_it_is_not_stored(monkeypatch: pytest.MonkeyPatch) -> None:
    # A branch that is empty the day it is added is almost always a wrong
    # address, and storing it means keeping a row that will never do anything.
    from quill.core.radio import my_servers

    added: list[str] = []
    monkeypatch.setattr(my_servers, "probe", lambda root, safe_mode=False: (root, 0))
    monkeypatch.setattr(my_servers.ServerStore, "add", lambda self, url, name="": added.append(url))

    host = _Host(typed="http://stream.example.org:8000")
    browse_actions.perform(host, "addserver")

    assert added == []
    assert any("Nothing answered" in m for m in host.said)
    assert host.reloaded == []


def test_a_server_address_that_is_not_one_is_refused_before_the_network() -> None:
    host = _Host(typed="not an address")
    browse_actions.perform(host, "addserver")

    assert host._task_manager.submitted == []  # nothing was fetched
    assert any("does not look like a server address" in m for m in host.said)


def test_cancelling_the_prompt_does_nothing_at_all() -> None:
    host = _Host(typed="http://stream.example.org:8000", ok=False)
    browse_actions.perform(host, "addserver")

    assert host.said == []
    assert host._task_manager.submitted == []
    assert host._wx.last_entry is not None and host._wx.last_entry.destroyed


def test_safe_mode_refuses_out_loud_before_asking_anything() -> None:
    host = _Host(typed="http://stream.example.org:8000", safe_mode=True)
    browse_actions.perform(host, "addserver")

    assert host._wx.last_entry is None  # never even prompted
    assert any("Safe Mode" in m for m in host.said)


def test_a_failed_probe_is_reported_rather_than_swallowed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from quill.core.radio import my_servers

    def _boom(root: str, safe_mode: bool = False):
        raise my_servers.MyServersError("the server refused the connection")

    monkeypatch.setattr(my_servers, "probe", _boom)

    host = _Host(typed="http://stream.example.org:8000")
    browse_actions.perform(host, "addserver")

    assert any("Could not reach" in m for m in host.said)


def test_adding_a_channel_checks_it_reads_before_storing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from quill.core.radio import youtube_channels as yt

    added: list[str] = []
    monkeypatch.setattr(yt, "videos", lambda url, page=1, safe_mode=False: (["a video"], False))
    monkeypatch.setattr(
        yt.ChannelStore,
        "add",
        lambda self, url, name="": added.append(url) or yt.Channel(url=url, name=""),
    )

    host = _Host(typed="https://www.youtube.com/@example")
    browse_actions.perform(host, "addchannel")

    assert added and "example" in added[0]
    assert host.reloaded == ["youtube"]


def test_a_channel_that_reads_as_empty_is_not_stored(monkeypatch: pytest.MonkeyPatch) -> None:
    from quill.core.radio import youtube_channels as yt

    added: list[str] = []
    monkeypatch.setattr(yt, "videos", lambda url, page=1, safe_mode=False: ([], False))
    monkeypatch.setattr(yt.ChannelStore, "add", lambda self, url, name="": added.append(url))

    host = _Host(typed="https://www.youtube.com/@example")
    browse_actions.perform(host, "addchannel")

    assert added == []
    assert any("Nothing was found" in m for m in host.said)


def test_a_channel_address_that_is_not_one_is_refused_before_the_network() -> None:
    host = _Host(typed="hello")
    browse_actions.perform(host, "addchannel")

    assert host._task_manager.submitted == []
    assert any("does not look like a channel address" in m for m in host.said)
