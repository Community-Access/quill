"""Scribe for Documents in each app, through the adapters (PRD 8.3 to 8.8).

Media Player: the DAISY book wins over the MP3 and opens quietly with a
sentence that says how to play; a DAISY ``.ncx`` or zip on the command line
opens as a book. Converter: documents added to the audio queue are named in
one sentence; Add to the Converter Queue says it once. Studio: the chapter
markers are the result sentence's note, and a narration never opens by
itself. Cast and Social: the linked documents of the selected episode or
post. Beacon: the count sentence, and the Scribe Documents destination.
"""

from __future__ import annotations

import sys
import zipfile
from pathlib import Path
from typing import Any

import pytest

from quill.core.scribe import queue as q

pytestmark = pytest.mark.usefixtures("wx_session_app")

SOCIAL = Path(__file__).resolve().parents[3] / "standalone" / "social"


@pytest.fixture
def worktree_quill_social(monkeypatch: pytest.MonkeyPatch):  # type: ignore[no-untyped-def]
    """Import ``quill_social`` from this tree, and restore whatever was there."""
    saved = {n: m for n, m in sys.modules.items() if n.split(".")[0] == "quill_social"}
    for name in saved:
        del sys.modules[name]
    monkeypatch.syspath_prepend(str(SOCIAL))
    try:
        yield
    finally:
        for name in [n for n in sys.modules if n.split(".")[0] == "quill_social"]:
            del sys.modules[name]
        sys.modules.update(saved)


def _daisy_zip(folder: Path) -> Path:
    path = folder / "Notes.zip"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("Notes/book.ncx", "<ncx/>")
        archive.writestr("Notes/book.mp3", b"ID3")
    return path


# ------------------------------------------------------------ Media Player


class _Player:
    """Stands in for the Player frame: what the adapter calls on it."""

    def __init__(self) -> None:
        self.loaded: list[tuple[str, Path, bool]] = []
        self.said: list[str] = []
        self._book_key = ""
        self._chapter_nodes: list[Any] = []

    def _load_daisy(self, ncx: Path, *, quiet: bool = False) -> None:
        self.loaded.append(("daisy", ncx, quiet))
        self._book_key = str(ncx)
        self._chapter_nodes = [1, 2, 3]

    def _load_book(self, path: Path) -> None:
        self.loaded.append(("mp3", path, False))
        self._book_key = str(path)

    def _announce(self, text: str) -> None:
        self.said.append(text)

    def _show_message_box(self, text: str, _title: str) -> None:
        self.said.append(text)


def test_the_daisy_book_wins_and_opens_quietly_with_how_to_play(tmp_path: Path) -> None:
    from quill.apps.player_scribe import PlayerScribeHost, PlayerScribeMixin

    class Frame(_Player, PlayerScribeMixin):
        pass

    frame = Frame()
    host = PlayerScribeHost(frame, "Quill Media Player")
    assert host.scribe_opens_on_its_own is True
    mp3 = tmp_path / "Notes.mp3"
    mp3.write_bytes(b"ID3")
    daisy = _daisy_zip(tmp_path)
    job = q.Job(outputs={"mp3": str(mp3), "daisy": str(daisy)})
    said = host.scribe_open_result(job, "daisy", daisy)
    assert said == (
        "The DAISY book is open in Media Player, 3 headings, at the start. Press Alt+A to play"
    )
    assert frame.loaded[-1][0] == "daisy" and frame.loaded[-1][2] is True  # quiet
    only_mp3 = q.Job(outputs={"mp3": str(mp3)})
    assert host.scribe_open_result(only_mp3, "mp3", mp3).startswith("The MP3 audio is open")
    assert host.scribe_open_result(job, "docx", tmp_path / "N.docx") == ""
    labels = [label for label, _run in host.scribe_next_steps(job, {"daisy": daisy, "mp3": mp3})]
    assert labels[:2] == [
        "Play in Media Player (DAISY (text and audio))",
        "Play in Media Player (MP3 audio)",
    ]


def test_listen_to_a_document_checks_both_audio_formats(monkeypatch: pytest.MonkeyPatch) -> None:
    from quill.apps.player_scribe import PlayerScribeMixin

    calls: list[Any] = []
    controller = type(
        "C",
        (),
        {
            "check_available": lambda _s: True,
            "convert_files": lambda _s, paths, **k: calls.append((paths, k)),
        },
    )()

    class Frame(_Player, PlayerScribeMixin):
        def _scribe(self) -> Any:
            return controller

        def _scribe_pick(self, *, multiple: bool) -> list[Path]:
            assert multiple is False
            return [Path("Book.pdf")]

    Frame().scribe_listen()
    assert calls == [([Path("Book.pdf")], {"app_formats": ["mp3", "daisy"], "open_as": "listen"})]


def test_a_daisy_book_on_the_command_line_opens_as_a_book(tmp_path: Path) -> None:
    from quill.apps.player_address import PlayerAddressMixin

    class Frame(_Player, PlayerAddressMixin):
        pass

    frame = Frame()
    ncx = tmp_path / "book.ncx"
    ncx.write_text("<ncx/>", encoding="utf-8")
    assert frame._open_launch_arguments([str(ncx)]) is True
    assert frame.loaded[-1][:2] == ("daisy", ncx) and frame.loaded[-1][2] is False
    assert frame._open_launch_arguments([str(_daisy_zip(tmp_path))]) is True
    assert frame.loaded[-1][1].name == "book.ncx"
    other = tmp_path / "photos.zip"
    with zipfile.ZipFile(other, "w") as archive:
        archive.writestr("a.jpg", b"x")
    assert frame._open_launch_arguments([str(other)]) is False
    assert frame.said[-1] == "photos.zip is not a DAISY book."
    assert not (tmp_path / "photos").exists()  # nothing unpacked


# --------------------------------------------------------------- Converter


def test_documents_left_out_of_the_audio_queue_are_named_in_one_sentence() -> None:
    from quill.apps.converter_scribe import left_out_note

    assert left_out_note([]) == ""
    assert left_out_note([Path("a.xyz")]) == " 1 not a media file, left out."
    one = left_out_note([Path("Notes.pdf")])
    assert one == (
        " Notes.pdf is a document. To convert it, use File, Convert Documents with "
        "Scribe for Documents."
    )
    several = left_out_note([Path("A.pdf"), Path("B.docx"), Path("c.xyz")])
    assert several.startswith(
        " 1 not a media file, left out. 2 files are documents: A.pdf, B.docx."
    )


def test_add_to_the_converter_queue_says_it_once(tmp_path: Path) -> None:
    from quill.apps.converter_scribe import ConverterScribeHost, ConverterScribeMixin

    class Frame(ConverterScribeMixin):
        def __init__(self) -> None:
            self._entries: list[Any] = [("x", None)]
            self.said: list[str] = []

        def add_paths(self, paths: list[Path], *, announce: bool = True) -> None:
            assert announce is False
            self._entries += [(p, None) for p in paths if (p, None) not in self._entries]

        def _announce(self, text: str) -> None:
            self.said.append(text)

    frame = Frame()
    mp3 = tmp_path / "Notes.mp3"
    mp3.write_bytes(b"ID3")
    steps = ConverterScribeHost(frame, "Quill Converter").scribe_next_steps(
        q.Job(file_name="Notes.pdf"), {"mp3": mp3}
    )
    assert steps[0][0] == "Add to the Converter Queue (MP3 audio)"
    steps[0][1]()
    assert frame.said == ["Notes.mp3 added to the Converter queue, 2 in all."]
    steps[0][1]()
    assert frame.said[-1] == "Notes.mp3 is already in the Converter queue."


# ------------------------------------------------------------------ Studio


def test_a_narration_carries_its_markers_and_never_opens_by_itself(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from quill.apps import studio_scribe

    host = studio_scribe.StudioScribeHost(object(), "QUILL Studio")
    assert host.scribe_opens_on_its_own is False
    monkeypatch.setattr(studio_scribe, "narration_markers", lambda job: "with 4 chapter markers")
    assert host.scribe_finish_job(q.Job(open_as="narration")) == "with 4 chapter markers"
    assert host.scribe_finish_job(q.Job(open_as="")) == ""
    mp3 = tmp_path / "N.mp3"
    labels = [label for label, _r in host.scribe_next_steps(q.Job(), {"mp3": mp3})]
    assert labels[0] == "Open in the Chapter Workbench"


def test_no_daisy_book_means_no_markers_said_plainly(tmp_path: Path) -> None:
    from quill.apps.studio_scribe import narration_markers

    mp3 = tmp_path / "N.mp3"
    mp3.write_bytes(b"ID3")
    assert narration_markers(q.Job(outputs={"mp3": str(mp3)})) == (
        "with no chapter markers, because there was no DAISY book to take them from"
    )
    assert narration_markers(q.Job(outputs={})) == ""


# -------------------------------------------------------------- Cast, Social


class _LinkController:
    def __init__(self) -> None:
        self.urls: list[str] = []

    def check_available(self) -> bool:
        return True

    def convert_url(self, url: str, *, open_as: str = "") -> list[str]:
        self.urls.append(url)
        return []


def test_cast_converts_the_episodes_linked_document() -> None:
    from quill.apps.podcasts_scribe import CastScribeMixin

    controller = _LinkController()
    episode = type("E", (), {"description": '<a href="https://a.org/Notes.pdf">Notes</a>'})()

    class Frame(CastScribeMixin):
        frame = None
        said: list[str] = []
        selected: Any = None

        def _selected_episode(self) -> Any:
            return self.selected

        def _announce(self, text: str) -> None:
            self.said.append(text)

        def _scribe(self) -> Any:
            return controller

    frame = Frame()
    frame.scribe_convert_linked_episode()
    assert frame.said == ["Choose an episode first."]
    frame.selected = ("show", type("E", (), {"description": "<p>No links</p>"})())
    frame.scribe_convert_linked_episode()
    assert frame.said[-1] == (
        "This episode's show notes link no documents Scribe for Documents can convert."
    )
    frame.selected = ("show", episode)
    frame.scribe_convert_linked_episode()
    assert controller.urls == ["https://a.org/Notes.pdf"]


@pytest.mark.usefixtures("worktree_quill_social")
def test_social_converts_a_posts_linked_document() -> None:
    from quill_social.ui.scribe import ITEM_ROW, TOOLS_ROWS, SocialScribeMixin

    controller = _LinkController()

    class Announcer:
        def __init__(self) -> None:
            self.said: list[str] = []

        def say(self, text: str, _level: str = "normal") -> None:
            self.said.append(text)

        def error(self, text: str) -> None:
            self.said.append(text)

    class Frame(SocialScribeMixin):
        item: Any = None

        def __init__(self) -> None:
            self.announcer = Announcer()

        def _current_item(self) -> Any:
            return self.item

        def _scribe(self) -> Any:
            return controller

    frame = Frame()
    frame.cmd_scribe_convert_linked()
    assert frame.announcer.said == ["Select a post first."]
    media = type("M", (), {"uri": "https://m.org/scan.png"})()
    frame.item = type("I", (), {"text": "No links here", "uri": "", "media": [media]})()
    frame.cmd_scribe_convert_linked()
    assert controller.urls == ["https://m.org/scan.png"]
    letters = [label.split("&")[1][0] for label, _cid in (ITEM_ROW, *TOOLS_ROWS)]
    assert len(set(letters)) == len(letters)


@pytest.mark.usefixtures("worktree_quill_social")
def test_socials_keymap_gives_every_scribe_row_the_family_key() -> None:
    from quill_social.keymap import DEFAULT_BINDINGS
    from quill_social.ui.scribe import ITEM_ROW, TOOLS_ROWS

    from quill.ui.scribe_app_host import COMMON_ROWS, ENTRY_KEY

    assert DEFAULT_BINDINGS[ITEM_ROW[1]] == ENTRY_KEY
    family = [key for *_rest, key in COMMON_ROWS]
    assert [DEFAULT_BINDINGS[cid] for _label, cid in TOOLS_ROWS] == family


# ------------------------------------------------------------------ Beacon


def test_beacons_count_sentence() -> None:
    from quill.apps.beacon.scribe_ui import _added_sentence

    assert _added_sentence(5, 2) == "Added 5 Scribe documents as places; 2 were already there."
    assert _added_sentence(1, 0) == "Added 1 Scribe document as places."
    assert _added_sentence(0, 1) == "Added 0 Scribe documents as places; 1 was already there."


def test_the_scribe_documents_destination_lists_scribe_places(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("QUILLBEACON_DATA", str(tmp_path / "beacon"))
    from quill.apps.beacon.scribe_places import open_store, save_place
    from quill.apps.beacon.scribe_ui import EMPTY, SCOPE, BeaconScribeMixin

    class Results:
        def __init__(self) -> None:
            self.count = -1

        def SetItemCount(self, n: int) -> None:  # noqa: N802 - wx shape
            self.count = n

        def RefreshItem(self, _i: int) -> None:  # noqa: N802 - wx shape
            pass

    class Announcer:
        def __init__(self) -> None:
            self.said: list[Any] = []

        def say(self, text: str) -> None:
            self.said.append(text)

        def announce_count(self, n: int, *, filtered: bool) -> None:
            self.said.append(("count", n))

    store = open_store()
    try:

        class Frame(BeaconScribeMixin):
            current_scope = SCOPE
            last_query = ""

            def __init__(self) -> None:
                self.store = store
                self.results = Results()
                self.announcer = Announcer()
                self.details: list[Any] = []

            def _show_details(self, beacon: Any) -> None:
                self.details.append(beacon)

        frame = Frame()
        assert frame._scribe_scope_results() is True
        assert frame.results.count == 0 and frame.announcer.said == [EMPTY]
        path = tmp_path / "N.docx"
        path.write_bytes(b"docx")
        save_place(store, document_id="d", title="Notes", path=path, format_id="docx")
        frame._scribe_scope_results()
        assert frame.results.count == 1 and frame.announcer.said[-1] == ("count", 1)
        frame.current_scope = "all"
        assert frame._scribe_scope_results() is False
    finally:
        store.close()
