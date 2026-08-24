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
    assert browse_actions.is_action_id("addpodcasturl")
    assert browse_actions.is_action_id("importpodcastsopml")
    assert browse_actions.is_action_id("searchpodcasts")
    assert not browse_actions.is_action_id("librivox")


def test_the_empty_subscriptions_actions_dispatch_to_their_own_helpers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from quill.ui.radio import browse_podcast_actions

    host = _Host()
    called: list[tuple[str, object]] = []
    monkeypatch.setattr(
        browse_podcast_actions,
        "add_podcast_by_url_prompt",
        lambda supplied_host: called.append(("add", supplied_host)),
    )
    monkeypatch.setattr(
        browse_podcast_actions,
        "import_opml",
        lambda supplied_host: called.append(("import", supplied_host)),
    )

    browse_actions.perform(host, "addpodcasturl")
    browse_actions.perform(host, "importpodcastsopml")

    assert called == [("add", host), ("import", host)]


def test_both_search_rows_answer_inside_the_tree(monkeypatch: pytest.MonkeyPatch) -> None:
    """Neither search row leaves the browse window any more.

    Both used to call ``open_internet_radio``, which swapped the tree for the
    Find Stations dialog -- "search all sources is taking me somewhere else"
    (2026-08-18). They now run the same in-tree search, one of them narrowed
    to the podcast directories.
    """
    from quill.core.radio import federated_browse
    from quill.ui.radio import browse_search_all

    runs: list[tuple[object, tuple[str, ...] | None]] = []
    monkeypatch.setattr(
        browse_search_all,
        "run",
        lambda host, *, targets=None, **_kwargs: runs.append((
            host,
            tuple(t.label for t in targets) if targets is not None else None,
        )),
    )
    host = _Host()

    browse_actions.perform(host, "searchall")
    browse_actions.perform(host, "searchpodcasts")

    assert [supplied for supplied, _targets in runs] == [host, host]
    # Search All asks everything; Search for a Podcast asks the podcast
    # directories only -- derived from the source table, never a second list.
    assert runs[0][1] is None
    assert runs[1][1] == tuple(t.label for t in federated_browse.targets_of_type("Podcast"))
    assert runs[1][1]  # the narrowing is not an empty tuple that asks nothing


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


# --- a saved video is a *video*, not an address --------------------------------


def test_adding_a_video_stores_it_then_names_it(monkeypatch: pytest.MonkeyPatch) -> None:
    """The row is saved first and described second, and the title is spoken.

    Reported 2026-08-23: "when you add a video by url it doesn't show the name
    of the video in the app". It showed the address, which for a screen reader
    is eleven characters of video id read one at a time.
    """
    from quill.core.radio import youtube_saved

    added: list[tuple[str, str]] = []
    described: list[youtube_saved.SavedItem] = []
    monkeypatch.setattr(
        youtube_saved.SavedStore,
        "add",
        lambda self, kind, url, name="": (
            added.append((kind, url)) or youtube_saved.SavedItem(kind=kind, url=url)
        ),
    )
    monkeypatch.setattr(
        youtube_saved.SavedStore, "describe", lambda self, details: described.append(details)
    )
    monkeypatch.setattr(
        youtube_saved,
        "fetch_video_details",
        lambda url, resolver=None: youtube_saved.SavedItem(
            kind=youtube_saved.VIDEO,
            url=url,
            name="Do schools kill creativity?",
            uploader="TED",
            duration_ms=1_203_000,
            description="Sir Ken Robinson makes an entertaining case...",
        ),
    )

    host = _Host(typed="https://www.youtube.com/watch?v=iG9CE55wbtY")
    browse_actions.perform(host, "addvideo")

    assert added == [(youtube_saved.VIDEO, "https://www.youtube.com/watch?v=iG9CE55wbtY")]
    assert described and described[0].name == "Do schools kill creativity?"
    # The name AND the facts worth knowing before pressing Enter.
    assert any("Do schools kill creativity?" in m for m in host.said)
    assert any("TED" in m and "20 minutes" in m for m in host.said)
    # The branch is refreshed twice: once so the row appears at all, once so it
    # appears with its name.
    assert host.reloaded == ["youtube", "youtube"]


def test_a_video_whose_details_cannot_be_read_is_still_saved(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from quill.core.radio import youtube_saved
    from quill.core.radio.youtube import YouTubeError

    added: list[str] = []
    monkeypatch.setattr(
        youtube_saved.SavedStore,
        "add",
        lambda self, kind, url, name="": (
            added.append(url) or youtube_saved.SavedItem(kind=kind, url=url)
        ),
    )

    def _boom(url: str, resolver: object = None) -> None:
        raise YouTubeError("that video is private")

    monkeypatch.setattr(youtube_saved, "fetch_video_details", _boom)

    host = _Host(typed="https://www.youtube.com/watch?v=iG9CE55wbtY")
    browse_actions.perform(host, "addvideo")

    # Saved anyway: a failed lookup must never lose the link somebody pasted.
    assert added == ["https://www.youtube.com/watch?v=iG9CE55wbtY"]
    assert any("private" in m for m in host.said)


def test_adding_a_playlist_reads_its_name(monkeypatch: pytest.MonkeyPatch) -> None:
    from quill.core.radio import youtube_saved

    monkeypatch.setattr(
        youtube_saved.SavedStore,
        "add",
        lambda self, kind, url, name="": youtube_saved.SavedItem(kind=kind, url=url),
    )
    monkeypatch.setattr(youtube_saved.SavedStore, "describe", lambda self, details: details)
    monkeypatch.setattr(
        youtube_saved,
        "fetch_playlist_details",
        lambda url, resolver=None: youtube_saved.SavedItem(
            kind=youtube_saved.PLAYLIST, url=url, name="Best of TED", item_count=42
        ),
    )

    host = _Host(typed="https://www.youtube.com/playlist?list=PL123")
    browse_actions.perform(host, "addplaylist")

    assert any("Best of TED" in m and "42 videos" in m for m in host.said)


def test_the_youtube_adds_ask_for_consent_first(monkeypatch: pytest.MonkeyPatch) -> None:
    """Nothing is stored behind a consent the listener declined.

    The tree used to store the link without ever asking, so the refusal landed
    at play time instead -- "add it again from Add Custom Station", for a row
    that looked perfectly ordinary (reported 2026-08-23).
    """
    from quill.core.radio import youtube_saved
    from quill.ui.radio import youtube_ui

    class _Frame:
        _radio_history = object()

        def _show_message_box(self, *_args: Any, **_kwargs: Any) -> int:
            return 0

    added: list[str] = []
    monkeypatch.setattr(
        youtube_saved.SavedStore, "add", lambda self, kind, url, name="": added.append(url)
    )
    monkeypatch.setattr(youtube_ui, "ask_youtube_consent", lambda _frame: False)

    host = _Host(typed="https://www.youtube.com/watch?v=iG9CE55wbtY")
    host._download_host = _Frame()
    browse_actions.perform(host, "addvideo")

    assert added == []
    assert host._task_manager.submitted == []


def test_the_podcast_index_search_row_asks_that_one_directory(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Search the Podcast Index...: answered inside the tree, narrowed to it."""
    from quill.core.radio import federated_browse
    from quill.ui.radio import browse_search_all

    runs: list[tuple[str, tuple[str, ...]]] = []
    monkeypatch.setattr(
        browse_search_all,
        "run",
        lambda host, *, what="", targets=(), **_kwargs: runs.append((
            what,
            tuple(t.label for t in targets),
        )),
    )
    host = _Host()

    assert browse_actions.is_action_id("searchpodcastindex")
    browse_actions.perform(host, "searchpodcastindex")

    assert runs == [("the Podcast Index", ("Podcast Index",))]
    # Derived from the source table rather than a second list to keep in step.
    assert any(t.seed_id == "podcastindex" for t in federated_browse.TARGETS)
