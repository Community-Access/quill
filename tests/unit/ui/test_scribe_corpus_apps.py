"""Every app's Scribe for Documents entry point, replayed on Pneuma's real corpus.

Each app's own command -- QUILL's Convert, Explorer's Send To, QUILL Lite,
the Media Player's Listen, Converter's batch, Studio's Narration, Cast's and
Social's linked documents -- goes through the real controller, the fake
Scribe server (which hands back the corpus files byte for byte) and the real
queue runner. Then: the files are named after our stem and saved where that
app says; the result sentence is said once and every stage once (GATE-13);
Open Result opens what the app opens (the accessible HTML, never the offline
page, which Next Steps shows in the browser, F2); and
Next Steps offer the app's own commands. Beacon's place is saved from the
real HTML's headings.
"""

# ruff: noqa: F811 - the shared fixture is imported from test_scribe_family_apps and used by name
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest

from quill.core import scribe
from quill.core.scribe import queue as q
from quill.core.scribe.model import ScribeSettings
from tests.unit.apps.test_scribe_family_apps import worktree_quill_social  # noqa: F401
from tests.unit.core.scribe import corpus
from tests.unit.core.scribe.fake_scribe import BASE, FakeClock, FakeScribe, StaticTokens

pytestmark = [*corpus.needs_corpus, pytest.mark.usefixtures("wx_session_app")]

GARDEN = corpus.GARDEN
LINK = f"https://docs.example.org/files/{GARDEN}.docx"


@pytest.fixture(autouse=True)
def _holding() -> Any:
    from quill.ui.scribe_controller import _INSTANCES, ScribeController

    original = ScribeController.__dict__["holding"]
    ScribeController.holding = property(lambda _self: True)  # type: ignore[assignment]
    yield
    ScribeController.holding = original  # type: ignore[assignment]
    _INSTANCES.clear()


@dataclass
class World:
    tmp: Path
    server: FakeScribe
    clock: FakeClock
    chosen: list[list[str]] = field(default_factory=list)
    opened_elsewhere: list[tuple[str, str]] = field(default_factory=list)

    @property
    def source(self) -> Path:
        path = self.tmp / f"{GARDEN}.docx"
        if not path.exists():
            path.write_bytes(b"PK\x03\x04 the Word source")
        return path


@pytest.fixture
def world(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> World:
    import wx

    import quill.ui.dialog_contract as contract
    import quill.ui.scribe_convert_dialog as convert
    from quill.ui import main_frame_scribe, scribe_app_host, scribe_entry

    monkeypatch.setenv("QUILL_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.delenv("QUILL_SAFE_MODE", raising=False)
    monkeypatch.setattr(scribe, "CLIENT_ID", "test-client")
    server = FakeScribe()
    server.serve_files(corpus.outputs(GARDEN))
    made = World(tmp_path, server, FakeClock())

    class Choice:
        def __init__(self, formats: list[str]) -> None:
            self.formats = formats
            self.settings = ScribeSettings()
            self.save_as_defaults = False
            self.password = ""

    class Dialog:  # the person accepts what the app's command checked
        def __init__(self, *_a: Any, **kw: Any) -> None:
            self.formats = list(made.chosen.pop(0) if made.chosen else kw["formats"])

        def result(self) -> Choice:
            return Choice(self.formats)

        def Destroy(self) -> None:  # noqa: N802 - wx API
            pass

    monkeypatch.setattr(convert, "ScribeConvertDialog", Dialog)
    monkeypatch.setattr(contract, "show_modal_dialog", lambda *_a, **_k: wx.ID_OK)
    monkeypatch.setattr(wx, "GetActiveWindow", lambda: object())  # an app in front
    monkeypatch.setattr(wx, "GetTopLevelParent", lambda window: window)

    def elsewhere(kind: str) -> Any:
        return lambda *args: made.opened_elsewhere.append((kind, Path(args[-1]).name)) or True

    to_editor = elsewhere("editor")
    monkeypatch.setattr(scribe_app_host, "open_in_editor", lambda p: to_editor(p) and "QUILL")
    monkeypatch.setattr(scribe_app_host, "send_to_player", elsewhere("player"))
    monkeypatch.setattr(main_frame_scribe, "_send_to_player", elsewhere("player"))
    monkeypatch.setattr(scribe_entry, "open_in_browser", elsewhere("browser"))
    return made


def _wire(controller: Any, world: World) -> Any:
    """The app's real controller, on the fake server and a queue in tmp."""
    from quill.core.scribe.client import ScribeClient

    world.server.clock = world.clock
    controller._queue = q.FamilyQueue(world.tmp / "data" / "scribe", now=world.clock)
    server = world.server
    controller._session = type(
        "Session",
        (),
        {
            "base_url": BASE,
            "is_signed_in": lambda _s: True,
            "access_token": lambda _s: server.access_token,
            "force_refresh": lambda _s: server.access_token,
        },
    )()
    controller.client = lambda: ScribeClient(
        StaticTokens(server), base_url=BASE, transport=server.transport, sleep=lambda _s: None
    )
    controller.ensure_service = lambda: None
    controller.wake = lambda: None

    def now(work: Any, done: Any, failed: Any = None) -> None:
        try:
            result = work()
        except Exception as error:  # noqa: BLE001
            (failed or controller._failed)(error)
            return
        done(result)

    controller._background = now
    return controller


def _run(controller: Any, world: World) -> q.Job:
    from quill.core.scribe.runner import QueueService, default_channel_opener

    service = QueueService(
        controller.app_name,
        queue=controller.queue,
        client_factory=controller.client,
        channel_opener=default_channel_opener(world.server.connector),
        download_root=lambda: str(world.tmp / "out"),
        listener=controller._on_event,
        sleep=world.clock.sleep,
        clock=world.clock,
    )
    assert service.tick()
    job = controller.queue.jobs()[-1]
    assert job.state == q.DONE, job.message
    return job


def _check_speech(said: list[str], job: q.Job) -> str:
    """One start, one result sentence, and no sentence twice (GATE-13)."""
    results = [s for s in said if s.startswith("Scribe for Documents made")]
    assert len(results) == 1, said
    assert sum(s.startswith("Scribe for Documents: sending") for s in said) == 1
    assert len(said) == len(set(said)), said
    assert "Touch" not in results[0]
    for path in job.outputs.values():
        assert Path(path).name in results[0]
    return results[0]


# ---------------------------------------------------------------- QUILL


class _QuillFrame:
    def __init__(self) -> None:
        self.said: list[str] = []
        self.opened: list[Path] = []
        self.settings = None
        self.frame = None

    def _announce(self, text: str) -> None:
        self.said.append(text)

    def open_file(self, path: Path) -> None:
        self.opened.append(Path(path))

    def read_all(self) -> None:  # Read Aloud's command, run after the open
        pass

    def _scribe_open_as_import(self, job: Any, path: Path) -> None:
        """QUILL's converted tab: what it would show, recorded."""
        from quill.io.docconvert import convert_document

        self.opened.append(Path(path))
        self.readable = str(convert_document(path).text)


def test_quill_opens_the_accessible_html_and_offers_the_offline_page(world: World) -> None:
    from quill.ui.main_frame_scribe import QuillScribeHost
    from quill.ui.scribe_controller import controller_for

    mf = _QuillFrame()
    controller = _wire(controller_for(QuillScribeHost(mf)), world)
    formats = list(corpus.outputs(GARDEN))
    world.chosen.append(formats)
    controller.convert_files([world.source])
    job = _run(controller, world)
    assert Path(job.folder) == world.tmp / "out" / GARDEN
    names = {f: Path(p).name for f, p in job.outputs.items()}
    assert names["offline_html"] == f"{GARDEN}-offline.html" and names["docx"] == f"{GARDEN}.docx"
    result = _check_speech(mf.said, job)
    # The accessible HTML opens, as a readable document, never its markup;
    # the offline page is saved and offered (F2).
    assert mf.opened == [Path(job.outputs["html"])]
    assert "<h1" not in mf.readable and "# 1. Getting a plot" in mf.readable
    assert (
        "The accessible HTML is open in a new tab. Its pictures are in the Web page for offline "
        "reading; Next Steps opens that in your browser. A Kindle (MOBI) book" in result
    )
    steps = dict(controller.next_steps(job))
    assert "Read Aloud with QUILL's Voices (Accessible HTML)" in steps
    assert "Open in the Braille View" in steps
    steps["Open in Your Browser (Web page for offline reading)"]()
    assert world.opened_elsewhere == [("browser", f"{GARDEN}-offline.html")]
    # Every editor step works on the accessible HTML, not the offline page.
    mf.opened.clear()
    steps["Read Aloud with QUILL's Voices (Accessible HTML)"]()
    assert mf.opened == [Path(job.outputs["html"])]
    # Open Result, the person's own command, says it once more on purpose.
    mf.said.clear()
    controller.open_job_result(job)
    assert mf.said == ["The accessible HTML is open in a new tab."]


def test_quill_html_without_the_offline_page_says_where_the_pictures_are(world: World) -> None:
    from quill.ui.main_frame_scribe import QuillScribeHost
    from quill.ui.scribe_controller import controller_for

    mf = _QuillFrame()
    controller = _wire(controller_for(QuillScribeHost(mf)), world)
    world.chosen.append(["html", "brf"])
    controller.convert_files([world.source])
    job = _run(controller, world)
    result = _check_speech(mf.said, job)
    assert result.endswith(
        "The accessible HTML is open in a new tab. "
        "The accessible HTML came without its pictures; Download Formats in My Scribe "
        "Documents can add the Web page for offline reading, which has them."
    )
    assert mf.opened == [Path(job.outputs["html"])]
    labels = [label for label, _run in controller.next_steps(job)]
    assert not any("Browser" in label for label in labels)


def test_send_to_gathers_the_files_into_one_job_batch(world: World, monkeypatch: Any) -> None:
    import wx

    from quill.ui.main_frame_scribe import QuillScribeHost, ScribeMixin
    from quill.ui.scribe_controller import controller_for

    later: list[Any] = []
    monkeypatch.setattr(wx, "CallLater", lambda _ms, fn, *a: later.append(fn))
    mf = _QuillFrame()
    controller = _wire(controller_for(QuillScribeHost(mf)), world)

    class Frame(ScribeMixin):
        def __init__(self) -> None:
            self.frame = type(
                "F", (), {"IsIconized": lambda s: False, "Show": lambda s: None,
                          "Raise": lambda s: None, "IsEnabled": lambda s: True},
            )()  # fmt: skip

        def _announce(self, text: str) -> None:
            mf.said.append(text)

        def _scribe(self) -> Any:
            return controller

    frame = Frame()
    world.chosen.append(["docx"])
    frame._scribe_shell_request(world.source)
    later[0]()
    job = _run(controller, world)
    assert Path(job.outputs["docx"]).read_bytes() == corpus.output("docx", GARDEN).read_bytes()
    _check_speech(mf.said, job)


# ----------------------------------------------------------------- Lite


def test_lite_opens_word_html_and_braille_in_its_own_window(
    world: World, monkeypatch: pytest.MonkeyPatch
) -> None:
    from quill.apps.lite_window_scribe import LiteScribeHost, wait_for_sentence
    from quill.stability import wx_dispatch
    from quill.ui.scribe_controller import controller_for

    timers: list[tuple[int, Any]] = []
    monkeypatch.setattr(
        wx_dispatch, "call_later_safely", lambda ms, fn, *a, **k: timers.append((ms, fn))
    )
    window = _QuillFrame()
    opened: list[Path] = []
    app = type("App", (), {"frames": [window], "active_frame": window,
                           "open_path": lambda _s, p: opened.append(Path(p))})()  # fmt: skip
    controller = _wire(controller_for(LiteScribeHost(app)), world)
    world.chosen.append(["brf", "pdf"])
    controller.convert_files([world.source])
    job = _run(controller, world)
    result = _check_speech(window.said, job)
    assert result.endswith("The braille is open in QUILL Lite.")
    # The new window would cut the sentence off: it opens after it, once.
    assert opened == []
    waits = [ms for ms, _fn in timers]
    assert wait_for_sentence(result) in waits
    for _ms, fn in timers:
        fn()
    assert opened == [Path(job.outputs["brf"])]  # the PDF is only saved


# -------------------------------------------- the apps that are not editors


class _AppFrame:
    def __init__(self) -> None:
        self.said: list[str] = []
        self.frame = None

    def _announce(self, text: str) -> None:
        self.said.append(text)

    def _show_message_box(self, text: str, _title: str) -> None:
        self.said.append(text)

    def _scribe_pick(self, *, multiple: bool) -> list[Path]:
        return [self.source]


def test_the_media_player_listens_to_a_document(world: World) -> None:
    from quill.apps.player_scribe import PlayerScribeMixin

    loaded: list[Path] = []

    class Frame(_AppFrame, PlayerScribeMixin):
        _chapter_nodes: list[Any] = []

        def _load_daisy(self, ncx: Path, *, quiet: bool = False) -> None:
            from quill.core.media import parse_ncx

            loaded.append(ncx)
            self._chapter_nodes = parse_ncx(ncx.read_text(encoding="utf-8"))
            self._book_key = str(ncx)

    frame = Frame()
    frame.source = world.source
    controller = _wire(frame._scribe(), world)
    frame.scribe_listen()
    assert controller.queue.jobs()[-1].formats == ["daisy", "mp3"]  # what Listen checks
    job = _run(controller, world)
    assert job.open_as == "listen"
    _check_speech(frame.said, job)
    if corpus.full_corpus() is not None:  # the real DAISY book, from its dtb.ncx (F3)
        frame.said.clear()
        controller.open_job_result(job)
        assert [p.name for p in loaded] == ["dtb.ncx"]
        assert frame.said[0].startswith("The DAISY book is open in Media Player, 6 headings")


def test_converter_saves_beside_its_own_destination(world: World) -> None:
    from quill.apps.converter_scribe import ConverterScribeMixin

    destination = world.tmp / "converted"

    class Frame(_AppFrame, ConverterScribeMixin):
        _entries: list[Any] = []
        _dest = type("Dest", (), {"GetValue": lambda _s: str(destination)})()

    frame = Frame()
    frame.source = world.source
    controller = _wire(frame._scribe(), world)
    world.chosen.append(["mobi", "epub"])
    frame.scribe_convert_documents()
    job = _run(controller, world)
    assert {Path(p).parent for p in job.outputs.values()} == {destination}
    result = _check_speech(frame.said, job)
    assert "Open it from Scribe Conversions. A Kindle (MOBI) book" in result  # on command
    assert world.opened_elsewhere == []
    controller.open_job_result(job)
    assert world.opened_elsewhere == [("editor", f"{GARDEN}.epub")]


def test_studio_narration_never_opens_by_itself(world: World) -> None:
    from quill.apps.studio_scribe import StudioScribeMixin

    class Frame(_AppFrame, StudioScribeMixin):
        pass

    frame = Frame()
    frame.source = world.source
    controller = _wire(frame._scribe(), world)
    world.chosen.append(["docx"])  # the MP3 and DAISY bytes need the full corpus
    frame.scribe_narration()
    job = _run(controller, world)
    assert job.open_as == "narration"
    result = _check_speech(frame.said, job)
    assert result.endswith("Open it from Scribe Conversions.")
    labels = [label for label, _run in controller.next_steps(job)]
    assert labels == ["Open in QUILL (Word)"]


def test_studio_opens_the_workbench_at_once_and_only_once(wx_call_after: Any) -> None:
    from quill.apps import studio_scribe

    queued: list[Any] = []
    wx_call_after(lambda fn, *a, **k: queued.append(fn))
    opened: list[Path] = []

    class Frame(studio_scribe.StudioScribeMixin):
        frame = None

        def open_book(self, path: Path) -> None:
            opened.append(path)

    frame = Frame()
    said = frame._scribe_open_workbench(q.Job(), Path("N.mp3"))
    assert said == studio_scribe.OPENS_SENTENCE == "Opening the Chapter Workbench"
    assert len(queued) == 1  # straight after the sentence, no timer
    # A second request while it is on its way (or open) is ignored.
    assert frame._scribe_open_workbench(q.Job(), Path("N.mp3")) == (
        "The Chapter Workbench is already opening"
    )
    assert len(queued) == 1
    queued[0]()
    assert opened == [Path("N.mp3")]
    frame._scribe_open_workbench(q.Job(), Path("N.mp3"))
    assert len(queued) == 2  # once it has closed, it opens again


def test_the_workbench_title_names_the_book() -> None:
    from quill.core.audio_studio.surface_help import PURPOSES, purpose_for_title

    assert purpose_for_title("Chapter Workbench: Lecture Notes") == PURPOSES["Chapter Workbench"]


def test_cast_converts_an_episodes_linked_document(world: World) -> None:
    from quill.apps.podcasts_scribe import CastScribeMixin

    class Frame(_AppFrame, CastScribeMixin):
        def _selected_episode(self) -> Any:
            notes = f'<p>Handout: <a href="{LINK}">the garden handbook</a></p>'
            return ("show", type("Episode", (), {"description": notes})())

    frame = Frame()
    controller = _wire(frame._scribe(), world)
    world.chosen.append(["docx", "brf"])
    frame.scribe_convert_linked_episode()
    job = _run(controller, world)
    assert job.source_url == LINK and not job.source_path
    assert {Path(p).stem for p in job.outputs.values()} == {GARDEN}
    _check_speech(frame.said, job)


@pytest.mark.usefixtures("worktree_quill_social")
def test_social_converts_a_posts_linked_document(world: World) -> None:
    from quill_social.ui.scribe import SocialScribeMixin

    said: list[str] = []

    class Frame(SocialScribeMixin):
        announcer = type("A", (), {"say": lambda _s, text, _level="normal": said.append(text),
                                   "error": lambda _s, text: said.append(text)})()  # fmt: skip

        def _current_item(self) -> Any:
            return type("Post", (), {"text": f"Our handbook: {LINK}", "uri": "", "media": []})()

    frame = Frame()
    controller = _wire(frame._scribe(), world)
    world.chosen.append(["html", "offline_html"])
    frame.cmd_scribe_convert_linked()
    job = _run(controller, world)
    _check_speech(said, job)
    controller.open_job_result(job)
    # Handed to an editor on its command line, the accessible HTML would be
    # markup: it opens readable in the browser, as the offline page beside it,
    # which has the pictures (phase-one audit, gap 1).
    assert world.opened_elsewhere == [("browser", f"{GARDEN}-offline.html")]
    assert said[-1] == "Opening the accessible HTML in your browser."
    steps = dict(controller.next_steps(job))
    assert not any(label.startswith("Open in QUILL") for label in steps)
    steps["Open in Your Browser (Web page for offline reading)"]()
    assert world.opened_elsewhere[-1] == ("browser", f"{GARDEN}-offline.html")


def test_a_beacon_place_is_saved_from_the_real_headings(
    world: World, monkeypatch: pytest.MonkeyPatch
) -> None:
    import wx

    from quill.apps.beacon.scribe_places import open_store, scribe_places
    from quill.ui.scribe_beacon_place import save_beacon_place

    monkeypatch.setenv("QUILLBEACON_DATA", str(world.tmp / "beacon"))
    html = world.tmp / f"{GARDEN}-offline.html"
    html.write_bytes(corpus.output("offline_html", GARDEN).read_bytes())
    rows: list[str] = []

    def modal(dialog: Any, _title: str) -> int:
        box = next(c for c in dialog.GetChildren() if isinstance(c, wx.ListBox))
        rows.extend(box.GetString(i) for i in range(box.GetCount()))
        dialog.SetSelection(rows.index("2.1 Watering schedule, heading level 2"))
        return wx.ID_OK

    said: list[str] = []
    job = q.Job(file_name=f"{GARDEN}.docx", title=GARDEN, document_id="doc1")
    save_beacon_place(job, "html", html, parent=None, say=said.append, modal=modal)
    assert "1. Getting a plot, heading level 1" in rows
    assert said == [f"Saved a Beacon place: {GARDEN}, at 2.1 Watering schedule."]
    store = open_store()
    try:
        assert [p.title for p in scribe_places(store)][0].startswith(GARDEN)
    finally:
        store.close()


def test_the_player_builds_chapters_from_the_real_daisy_book(tmp_path: Path) -> None:
    import shutil

    folder = corpus.require_full()
    from quill.apps.player import QuillMediaPlayerFrame
    from quill.core.media import parse_ncx, resolve_heading_times
    from quill.core.scribe.results import daisy_entry

    book = tmp_path / f"{GARDEN}.zip"
    shutil.copyfile(folder / "daisy" / f"{GARDEN}-daisy3.zip", book)
    ncx = daisy_entry(book)
    assert ncx is not None
    headings = parse_ncx(ncx.read_text(encoding="utf-8"))

    def smil(name: str) -> str | None:
        found = ncx.parent / name
        return found.read_text(encoding="utf-8") if found.is_file() else None

    build = QuillMediaPlayerFrame._daisy_build
    chapters, nodes, audio = build(resolve_heading_times(headings, smil), ncx.parent)
    assert audio is not None and audio.is_file()
    assert len(nodes) == len(headings) and chapters
    assert all(kind == "track" for _title, (kind, _payload), _depth in nodes)
