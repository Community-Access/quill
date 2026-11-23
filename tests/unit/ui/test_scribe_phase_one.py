"""Scribe for Documents, phase one: every returned file opens where it can be read.

The defects the phase-one audit found (2026-11-23), each pinned:

* the accessible HTML is read as a document in QUILL Lite, never as markup;
* the tagged PDF opens in QUILL or QUILL Lite on the person's command, and
  never by itself;
* an EPUB is never handed to QUILL Lite, which would show its zip bytes: it
  goes to QUILL, or it is saved and the result sentence says once that QUILL
  reads it;
* a failed hand-off names the app it tried;
* Media Player opens the MP3 when the DAISY book did not load, and is never
  handed a DAISY 2.02 book it cannot read;
* QUILL's Media Player hand-off waits for the result sentence;
* a Beacon place opens a document, in the family's app for it.
"""

from __future__ import annotations

import zipfile
from pathlib import Path
from typing import Any

import pytest

from quill.core.scribe import queue as q

pytestmark = pytest.mark.usefixtures("wx_session_app")

_HTML = (
    "<html><body><h1>Garden</h1><ul><li>Water</li><li>Weed</li></ul>"
    '<p>See <a href="https://example.org">the rules</a>.</p></body></html>'
)


@pytest.fixture
def timers(monkeypatch: pytest.MonkeyPatch) -> list[tuple[int, Any]]:
    import wx

    from quill.stability import wx_dispatch

    held: list[tuple[int, Any]] = []
    monkeypatch.setattr(
        wx_dispatch, "call_later_safely", lambda ms, fn, *a, **k: held.append((ms, fn))
    )
    monkeypatch.setattr(wx, "GetActiveWindow", lambda: object())  # the app is in front
    return held


def _fire(timers: list[tuple[int, Any]]) -> None:
    for _ms, fn in list(timers):
        fn()
    timers.clear()


class _LiteWindow:
    def __init__(self) -> None:
        self.said: list[str] = []
        self.committed: list[tuple[str, str]] = []

    def _announce(self, text: str) -> None:
        self.said.append(text)

    def _commit_download(self, prepared: Any, name: str) -> None:
        self.committed.append((prepared.text, name))


def _lite(opened: list[Path]) -> tuple[Any, _LiteWindow]:
    from quill.apps.lite_window_scribe import LiteScribeHost

    window = _LiteWindow()
    new = _LiteWindow()
    app = type(
        "App",
        (),
        {
            "frames": [window],
            "active_frame": window,
            "open_path": lambda _s, p: opened.append(Path(p)),
            "new_window": lambda _s, _mode: new,
        },
    )()
    return LiteScribeHost(app), new


# ------------------------------------------------------------- QUILL Lite


def test_lite_reads_the_accessible_html_as_a_document(
    tmp_path: Path, timers: list[tuple[int, Any]]
) -> None:
    html = tmp_path / "Garden.html"
    html.write_text(_HTML, encoding="utf-8")
    opened: list[Path] = []
    host, new = _lite(opened)
    said = host.scribe_open_result(q.Job(file_name="Garden.pdf"), "html", html)
    assert said == "The accessible HTML is open in QUILL Lite"
    host.scribe_announce(said + ".")
    _fire(timers)
    assert opened == []  # not opened as a file: that would be its markup
    text, name = new.committed[0]
    assert "<h1>" not in text and "<li>" not in text
    assert "Garden" in text and "Water" in text and "the rules" in text
    assert name == "Garden (Scribe)"


def test_lite_opens_the_tagged_pdf_and_hands_an_epub_to_quill(
    tmp_path: Path, timers: list[tuple[int, Any]], monkeypatch: pytest.MonkeyPatch
) -> None:
    from quill.apps import lite_window_scribe
    from quill.core import app_launcher

    launched: list[tuple[str, tuple[str, ...]]] = []
    monkeypatch.setattr(
        app_launcher, "launch_app", lambda app, extra_args=(): launched.append((app, extra_args))
    )
    opened: list[Path] = []
    host, _new = _lite(opened)
    pdf, epub = tmp_path / "N.pdf", tmp_path / "N.epub"
    assert host.scribe_open_result(q.Job(), "pdf", pdf) == "The tagged PDF is open in QUILL Lite"
    _fire(timers)
    assert opened == [pdf]

    monkeypatch.setattr(lite_window_scribe, "_quill_installed", lambda: True)
    assert host.scribe_open_result(q.Job(), "epub", epub) == "The EPUB is open in QUILL"
    _fire(timers)
    assert launched == [("quill", (str(epub),))] and opened == [pdf]  # never opened in Lite
    assert host.scribe_result_note(q.Job(outputs={"epub": str(epub)})) == ""

    monkeypatch.setattr(lite_window_scribe, "_quill_installed", lambda: False)
    assert host.scribe_open_result(q.Job(), "epub", epub) == ""
    assert host.scribe_result_note(q.Job(outputs={"epub": str(epub)})) == (
        "QUILL Lite does not open EPUB books. QUILL does."
    )
    labels = [label for label, _ in host.scribe_next_steps(q.Job(), {"epub": epub, "pdf": pdf})]
    assert labels == ["Open in QUILL Lite (Tagged PDF)"]


# --------------------------------------------------- the controller itself


def test_the_tagged_pdf_opens_on_command_only(tmp_path: Path) -> None:
    from quill.ui.scribe_controller import controller_for

    pdf = tmp_path / "N.pdf"
    pdf.write_bytes(b"%PDF")
    said: list[str] = []
    opened: list[str] = []

    class Host:
        app_name = "QUILL Test"

        def scribe_announce(self, text: str) -> None:
            said.append(text)

        def scribe_open_result(self, job: Any, format_id: str, path: Path) -> str:
            opened.append(format_id)
            return "The tagged PDF is open in QUILL"

    controller = controller_for(Host())  # type: ignore[arg-type]
    job = q.Job(file_name="N.docx", outputs={"pdf": str(pdf)}, folder=str(tmp_path))
    assert controller.open_job_result(job, speak=False) == ""  # by itself: never
    assert opened == []
    assert controller.open_job_result(job) == "The tagged PDF is open in QUILL"
    assert opened == ["pdf"] and said == ["The tagged PDF is open in QUILL."]


# -------------------------------------------------------- the other apps


def test_other_apps_never_hand_an_epub_to_lite_and_name_the_app_they_tried(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from quill.ui import scribe_app_host

    monkeypatch.setattr(scribe_app_host, "editor_name", lambda: "QUILL Lite")
    monkeypatch.setattr(scribe_app_host, "open_in_editor", lambda _p: "")
    epub, pdf = tmp_path / "N.epub", tmp_path / "N.pdf"
    assert scribe_app_host.open_elsewhere("epub", epub) == ""
    job = q.Job(outputs={"epub": str(epub)})
    assert scribe_app_host.epub_note(job) == "QUILL Lite does not open EPUB books. QUILL does."
    said: list[str] = []
    steps = dict(scribe_app_host.elsewhere_steps(job, {"epub": epub, "pdf": pdf}, said.append))
    assert list(steps) == ["Open in QUILL Lite (Tagged PDF)"]
    steps["Open in QUILL Lite (Tagged PDF)"]()
    assert said == ["QUILL Lite could not be opened. N.pdf is saved in its folder."]

    monkeypatch.setattr(scribe_app_host, "editor_name", lambda: "QUILL")
    assert scribe_app_host.epub_note(job) == ""


def test_other_apps_show_the_accessible_html_readable_in_the_browser(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from quill.ui import scribe_app_host, scribe_entry

    shown: list[str] = []
    monkeypatch.setattr(scribe_entry, "open_in_browser", lambda p: shown.append(p.name) or True)
    editor: list[Path] = []
    monkeypatch.setattr(scribe_app_host, "open_in_editor", lambda p: editor.append(p) or "QUILL")
    html = tmp_path / "N.html"
    said = scribe_app_host.open_elsewhere("html", html)
    assert said == "Opening the accessible HTML in your browser" and shown == ["N.html"]
    (tmp_path / "N-offline.html").write_text("<p>x</p>", encoding="utf-8")
    scribe_app_host.open_elsewhere("html", html)
    assert shown[-1] == "N-offline.html" and editor == []  # the one with the pictures


# ------------------------------------------------------------ Media Player


def test_the_player_falls_back_to_the_mp3_when_the_daisy_book_fails(tmp_path: Path) -> None:
    from quill.apps.player_scribe import PlayerScribeHost

    class Owner:
        def _scribe_load(self, format_id: str, path: Path) -> str:
            return "" if format_id == "daisy" else "The MP3 audio is open in Media Player"

    host = PlayerScribeHost(Owner(), "Quill Media Player")
    mp3, daisy = tmp_path / "N.mp3", tmp_path / "N.zip"
    mp3.write_bytes(b"ID3")
    daisy.write_bytes(b"not a zip")
    job = q.Job(outputs={"mp3": str(mp3), "daisy": str(daisy)})
    assert host.scribe_open_result(job, "daisy", daisy) == ""
    assert host.scribe_open_result(job, "mp3", mp3) == "The MP3 audio is open in Media Player"


def test_a_daisy_202_book_is_never_handed_to_the_player(tmp_path: Path) -> None:
    from quill.ui.scribe_entry import player_target

    book = tmp_path / "Old.zip"
    with zipfile.ZipFile(book, "w") as archive:
        archive.writestr("Old/ncc.html", "<html/>")
    assert player_target("daisy", book) is None
    three = tmp_path / "New.zip"
    with zipfile.ZipFile(three, "w") as archive:
        archive.writestr("New/dtb.ncx", "<ncx/>")
    target = player_target("daisy", three)
    assert target is not None and target.name == "dtb.ncx"


def test_quill_sends_audio_to_the_player_after_its_sentence(
    tmp_path: Path, timers: list[tuple[int, Any]], monkeypatch: pytest.MonkeyPatch
) -> None:
    from quill.ui import main_frame_scribe
    from quill.ui.scribe_after_sentence import wait_for_sentence

    sent: list[str] = []
    monkeypatch.setattr(main_frame_scribe, "_send_to_player", lambda f, p: sent.append(f) or True)
    said: list[str] = []
    frame = type("MF", (), {"_announce": lambda _s, text: said.append(text)})()
    host = main_frame_scribe.QuillScribeHost(frame)
    mp3 = tmp_path / "N.mp3"
    phrase = host.scribe_open_result(q.Job(), "mp3", mp3)
    assert phrase == "The MP3 audio is open in Media Player" and sent == []
    sentence = f"Scribe for Documents made N.mp3. {phrase}."
    host.scribe_announce(sentence)
    assert wait_for_sentence(sentence) in [ms for ms, _fn in timers]
    _fire(timers)
    assert sent == ["mp3"] and said == [sentence]


# ----------------------------------------------------------------- Beacon


def test_a_beacon_place_points_at_a_document_not_the_last_download(tmp_path: Path) -> None:
    from quill.core.scribe.results import place_order

    files = [
        ("docx", tmp_path / "N.docx"),
        ("mp3", tmp_path / "N.mp3"),
        ("daisy", tmp_path / "N.zip"),
        ("brf", tmp_path / "N.brf"),
    ]
    assert place_order(files)[0] == ("docx", tmp_path / "N.docx")
    assert place_order(files[1:])[0][0] == "brf"
    assert place_order([("mp3", tmp_path / "a.mp3"), ("daisy", tmp_path / "a.zip")])[0][0] == (
        "daisy"
    )


def test_a_beacon_place_opens_in_the_family_app_for_its_format(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from quill.apps.beacon.scribe_ui import BeaconScribeMixin
    from quill.ui import scribe_app_host

    handed: list[tuple[str, str]] = []
    monkeypatch.setattr(
        scribe_app_host,
        "open_elsewhere",
        lambda f, p: handed.append((f, Path(p).name)) or ("" if f == "brf" else "opened"),
    )
    said: list[str] = []
    recorded: list[str] = []

    class Frame(BeaconScribeMixin):
        announcer = type("A", (), {"say": lambda _s, text: said.append(text)})()
        store = type("S", (), {"record_open": lambda _s, bid: recorded.append(bid)})()

        def _scribe_say(self, text: str) -> None:
            said.append(text)

    docx, brf = tmp_path / "N.docx", tmp_path / "N.brf"
    place = type("B", (), {"beacon_id": "b1", "title": "Notes"})()
    frame = Frame()
    frame._scribe_open_place(place, type("R", (), {"primary_uri": str(docx),
                             "metadata": {"scribe_format": "docx"}})())  # fmt: skip
    assert handed == [("docx", "N.docx")] and said == ["Opened Notes"] and recorded == ["b1"]
    frame._scribe_open_place(place, type("R", (), {"primary_uri": str(brf),
                             "metadata": {"scribe_format": "brf"}})())  # fmt: skip
    assert said[-1] == "Notes could not be opened. N.brf is saved in its folder."


# ------------------------------------------------- the held window itself


def test_a_held_window_waits_for_its_own_sentence_and_for_the_person(
    timers: list[tuple[int, Any]],
) -> None:
    from quill.ui.scribe_after_sentence import UNSAID_WAIT_MS, AfterSentence

    here = [True]
    opened: list[str] = []
    after = AfterSentence(still_here=lambda: here[0])
    after.hold(lambda: opened.append("w"), "Word is open in QUILL Lite")
    after.said("Converting Notes.pdf, page 2 of 3.")  # another sentence: still held
    assert [ms for ms, _fn in timers] == [UNSAID_WAIT_MS]
    after.said("Scribe for Documents made Notes.docx. Word is open in QUILL Lite.")
    assert len(timers) == 2
    here[0] = False  # the person went to another program meanwhile
    _fire(timers)
    assert opened == []  # not over their work; Open Result is still there


# ------------------------------------- Jeff's answers (2026-11-23), follow-up


def test_open_result_holds_the_browser_until_its_sentence_is_said(
    tmp_path: Path, timers: list[tuple[int, Any]], monkeypatch: pytest.MonkeyPatch
) -> None:
    """The browser comes to the front after "Opening ... in your browser.",
    and not at all if the person has gone to another program."""
    import wx

    from quill.ui import scribe_entry
    from quill.ui.scribe_app_host import AppScribeHost
    from quill.ui.scribe_controller import controller_for

    shown: list[str] = []
    monkeypatch.setattr(scribe_entry, "open_in_browser", lambda p: shown.append(p.name) or True)
    page = tmp_path / "N-offline.html"
    page.write_text("<p>x</p>", encoding="utf-8")
    said: list[str] = []
    owner = type("Owner", (), {"_announce": lambda _s, text: said.append(text)})()
    controller = controller_for(AppScribeHost(owner, "QUILL Test App"))
    job = q.Job(file_name="N.pdf", outputs={"offline_html": str(page)}, folder=str(tmp_path))
    assert controller.open_job_result(job) == (
        "Opening the Web page for offline reading in your browser"
    )
    assert said == ["Opening the Web page for offline reading in your browser."]
    assert shown == []  # not under the sentence
    _fire(timers)
    assert shown == ["N-offline.html"]

    controller.open_job_result(job)
    monkeypatch.setattr(wx, "GetActiveWindow", lambda: None)  # gone to another program
    _fire(timers)
    assert shown == ["N-offline.html"]  # not opened over their work


def test_the_accessible_html_browser_waits_in_the_other_apps(
    tmp_path: Path, timers: list[tuple[int, Any]], monkeypatch: pytest.MonkeyPatch
) -> None:
    from quill.ui import scribe_entry
    from quill.ui.scribe_app_host import AppScribeHost

    shown: list[str] = []
    monkeypatch.setattr(scribe_entry, "open_in_browser", lambda p: shown.append(p.name) or True)
    owner = type("Owner", (), {"_announce": lambda _s, text: None})()
    host = AppScribeHost(owner, "QUILL Test App")
    html = tmp_path / "N.html"
    assert host.scribe_open_result(q.Job(), "html", html) == (
        "Opening the accessible HTML in your browser"
    )
    assert shown == []
    host.scribe_announce("Opening the accessible HTML in your browser.")
    _fire(timers)
    assert shown == ["N.html"]


def test_lite_brings_the_converted_html_forward_instead_of_a_second_copy(
    tmp_path: Path, timers: list[tuple[int, Any]]
) -> None:
    from quill.apps.lite_window_scribe import LiteScribeHost

    html = tmp_path / "Garden.html"
    html.write_text(_HTML, encoding="utf-8")
    made: list[_LiteWindow] = []
    focused: list[Any] = []
    window = _LiteWindow()

    def new_window(_app: Any, _mode: str) -> _LiteWindow:
        made.append(_LiteWindow())
        app.frames.append(made[-1])
        return made[-1]

    app = type(
        "App",
        (),
        {
            "frames": [window],
            "active_frame": window,
            "new_window": new_window,
            "focus_frame": lambda _s, frame: focused.append(frame),
        },
    )()
    host = LiteScribeHost(app)
    job = q.Job(file_name="Garden.pdf")
    host.scribe_open_result(job, "html", html)
    _fire(timers)
    assert len(made) == 1
    again = host.scribe_open_result(job, "html", html)
    assert again == "The accessible HTML is already open"
    host.scribe_announce(again + ".")
    _fire(timers)
    assert len(made) == 1 and focused == [made[0]]
    # A Next Step says it once, then brings the window forward.
    window.said.clear()
    host._open_readable(job, html)
    assert window.said == ["The accessible HTML is already open."]
    _fire(timers)
    assert len(made) == 1 and focused == [made[0], made[0]]
    # Closed: a new one is made.
    app.frames.remove(made[0])
    host.scribe_open_result(job, "html", html)
    _fire(timers)
    assert len(made) == 2


def test_quill_goes_to_the_converted_tab_instead_of_a_second_copy(tmp_path: Path) -> None:
    from quill.ui.main_frame_scribe import ALREADY_OPEN, QuillScribeHost, ScribeMixin

    html = tmp_path / "Garden.html"
    html.write_text(_HTML, encoding="utf-8")

    class Tab:
        def __init__(self, document: Any) -> None:
            self.document = document

    class Frame(ScribeMixin):
        def __init__(self) -> None:
            self._document_tabs: list[Tab] = []
            self.selected: list[int] = []
            self.said: list[str] = []

        def _create_document_tab(self, document: Any, select: bool = True) -> int:
            self._document_tabs.append(Tab(document))
            return len(self._document_tabs) - 1

        def _select_tab(self, index: int) -> None:
            self.selected.append(index)

        def _set_tab_page_text(self, index: int, title: str) -> None:
            pass

        def _set_status(self, text: str) -> None:
            pass

        def _announce(self, text: str) -> None:
            self.said.append(text)

    frame = Frame()
    host = QuillScribeHost(frame)
    job = q.Job(file_name="Garden.pdf")
    assert host.scribe_open_result(job, "html", html) == "The accessible HTML is open in a new tab"
    assert host.scribe_open_result(job, "html", html) == ("The accessible HTML is already open")
    assert len(frame._document_tabs) == 1 and frame.selected == [0]
    assert frame._scribe_open_as_import(job, html) == ALREADY_OPEN
    frame._document_tabs.clear()  # the tab was closed
    assert frame._scribe_open_as_import(job, html) == "opened"
    assert len(frame._document_tabs) == 1
