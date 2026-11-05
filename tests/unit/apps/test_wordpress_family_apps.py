"""QUILL Cast, QUILL Studio and Quill Converter reach WordPress through one shared door.

Each app's adapter only turns what it knows into the shared shape and calls
:mod:`quill.ui.wordpress_family`; these tests hold them to that, with the
shared commands and the file pickers replaced.
"""

from __future__ import annotations

import ast
from pathlib import Path
from types import SimpleNamespace

import pytest

from quill.apps import converter_wordpress as cw
from quill.apps import podcasts_wordpress as pw
from quill.apps import studio_wordpress as sw
from quill.core.podcasts.chapters import PodcastChapter
from quill.core.wordpress.episode import Chapter
from quill.ui import wordpress_family as fam
from quill.ui import wordpress_listen_dialogs as ldlg

_APPS = Path(__file__).resolve().parents[3] / "quill" / "apps"


class FakeApp:
    def __init__(self) -> None:
        self.frame = object()
        self.said: list[str] = []
        self._safe_mode = False
        self.posted: list[object] = []
        self.uploaded: list[object] = []
        self._wordpress_family_commands = SimpleNamespace(
            post_episode=self.posted.append, upload_files=self.uploaded.append
        )

    def _announce(self, text: str) -> None:
        self.said.append(text)

    def _show_modal_dialog(self, _dialog: object, _label: str) -> int:
        return 0


@pytest.fixture
def app() -> FakeApp:
    return FakeApp()


# --------------------------------------------------------------------------- #
# QUILL Cast


def _cast_episode(path: str = "", description: str = "") -> SimpleNamespace:
    return SimpleNamespace(
        guid="g1",
        title="Episode 12",
        downloaded_path=path,
        description=description,
        duration_seconds=600,
        audio_url="https://feed.example/12.mp3",
    )


def test_cast_episode_carries_file_notes_chapters_and_cached_transcript(
    monkeypatch, tmp_path
) -> None:
    from quill.core.podcasts import chapter_sources, transcripts

    audio = tmp_path / "12.mp3"
    audio.write_bytes(b"ID3")
    monkeypatch.setattr(
        chapter_sources, "read_file_chapters", lambda _p: [PodcastChapter(90_000, "News")]
    )
    monkeypatch.setattr(transcripts, "load_cached_transcript", lambda show, guid: f"{show}/{guid}")
    show = SimpleNamespace(id="s1", title="Morning Show")
    episode = pw.cast_episode(show, _cast_episode(str(audio), "<p>Notes</p>"))
    assert episode.title == "Episode 12" and episode.audio_path == audio
    assert episode.show_notes == "<p>Notes</p>"
    assert episode.chapters == (Chapter(90.0, "News"),)
    assert episode.transcript == "s1/g1"
    assert episode.podcast == "Morning Show"


def test_cast_episode_without_a_download_reads_chapters_from_the_notes(monkeypatch) -> None:
    from quill.core.podcasts import chapter_sources

    seen: dict[str, object] = {}

    def from_notes(notes: str, *, total_ms: int = 0) -> list[PodcastChapter]:
        seen["args"] = (notes, total_ms)
        return [PodcastChapter(0, "Intro")]

    monkeypatch.setattr(chapter_sources, "parse_show_notes_chapters", from_notes)
    episode = pw.cast_episode(SimpleNamespace(id="s", title=""), _cast_episode("", "0:00 Intro"))
    assert episode.audio_path is None
    assert episode.chapters == (Chapter(0.0, "Intro"),)
    assert seen["args"] == ("0:00 Intro", 600_000)


def test_cast_posts_the_selected_episode(app, monkeypatch) -> None:
    show = SimpleNamespace(id="s", title="Show")
    app._selected_episode = lambda: (show, _cast_episode())
    pw.post_selected_episode(app)
    assert [e.title for e in app.posted] == ["Episode 12"]


def test_cast_with_nothing_selected_says_so(app) -> None:
    app._selected_episode = lambda: None
    pw.post_selected_episode(app)
    assert app.said == ["Choose an episode first, then Post This Episode."]
    assert app.posted == []


def test_cast_menu_row_has_its_key() -> None:
    source = (_APPS / "podcasts_menu.py").read_text(encoding="utf-8")
    assert '"Post This Episode to WordPress...\\tCtrl+Alt+P"' in source
    assert "post_selected_episode(self)" in source


# --------------------------------------------------------------------------- #
# QUILL Studio


def test_studio_posts_a_chosen_file_with_its_chapters(app, monkeypatch, tmp_path) -> None:
    from quill.core.podcasts import chapter_sources

    audio = tmp_path / "chapter_one-final.mp3"
    audio.write_bytes(b"ID3")
    monkeypatch.setattr(ldlg, "pick_file", lambda *_a, **_k: audio)
    monkeypatch.setattr(
        chapter_sources, "read_file_chapters", lambda _p: [PodcastChapter(0, "Opening")]
    )
    sw.post_an_episode(app)
    [episode] = app.posted
    assert episode.title == "Chapter one final"
    assert episode.audio_path == audio
    assert episode.chapters == (Chapter(0.0, "Opening"),)


def test_studio_cancel_posts_nothing(app, monkeypatch) -> None:
    monkeypatch.setattr(ldlg, "pick_file", lambda *_a, **_k: None)
    sw.post_an_episode(app)
    assert app.posted == [] and app.said == []


def test_studio_is_off_in_safe_mode(app, monkeypatch) -> None:
    app._safe_mode = True
    monkeypatch.setattr(ldlg, "pick_file", lambda *_a, **_k: pytest.fail("asked"))
    sw.post_an_episode(app)
    assert app.said == [fam.SAFE_MODE_SENTENCE]


def test_studio_menu_has_one_row_with_a_key(app, monkeypatch) -> None:
    appended: list[tuple[object, str]] = []

    class Menu:
        def Append(self, item_id, label):  # noqa: N802 - wx's name
            appended.append((item_id, label))

    fake_wx = SimpleNamespace(Menu=Menu, NewIdRef=lambda: "id-1")
    menu, bindings = sw.build_wordpress_menu(app, fake_wx)
    assert isinstance(menu, Menu)
    assert appended == [("id-1", sw.POST_LABEL)]
    assert sw.POST_LABEL.endswith("\tCtrl+Shift+W")
    monkeypatch.setattr(ldlg, "pick_file", lambda *_a, **_k: None)
    [(item_id, handler)] = bindings
    handler()
    assert item_id == "id-1"
    source = (_APPS / "studio_capture.py").read_text(encoding="utf-8")
    assert 'menu_bar.Append(wordpress, "&WordPress")' in source


# --------------------------------------------------------------------------- #
# Quill Converter


def test_converter_uploads_from_the_last_output_folder(app, monkeypatch, tmp_path) -> None:
    app._last_output = tmp_path
    chosen = [tmp_path / "a.mp3", tmp_path / "b.mp3"]
    asked: dict[str, object] = {}

    def pick(*_a, **kwargs):
        asked.update(kwargs)
        return chosen

    monkeypatch.setattr(ldlg, "pick_files", pick)
    cw.upload_outputs(app)
    assert asked["folder"] == tmp_path
    assert app.uploaded == [chosen]


def test_converter_falls_back_to_its_destination(app) -> None:
    app._last_output = None
    app._destination = lambda: Path("C:/out")
    assert cw.output_folder(app) == Path("C:/out")
    app._destination = lambda: (_ for _ in ()).throw(RuntimeError("none"))
    assert cw.output_folder(app) is None


def test_converter_cancel_uploads_nothing(app, monkeypatch) -> None:
    app._last_output = None
    app._destination = lambda: Path(".")
    monkeypatch.setattr(ldlg, "pick_files", lambda *_a, **_k: [])
    cw.upload_outputs(app)
    assert app.uploaded == [] and app.said == []


def test_converter_is_off_in_safe_mode(app) -> None:
    app._safe_mode = True
    cw.upload_outputs(app)
    assert app.said == [fam.SAFE_MODE_SENTENCE]


def test_converter_menu_row_has_its_key() -> None:
    source = (_APPS / "converter_menu.py").read_text(encoding="utf-8")
    assert '"Upload to &WordPress...\\tCtrl+Alt+W"' in source


# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "module", ["podcasts_wordpress.py", "studio_wordpress.py", "converter_wordpress.py"]
)
def test_the_adapters_have_no_wordpress_code_of_their_own(module: str) -> None:
    """No site calls, no upload: a second implementation is how the family drifts."""
    tree = ast.parse((_APPS / module).read_text(encoding="utf-8"))
    imported = {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module is not None
    } | {
        f"{node.module}.{alias.name}"
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module is not None
        for alias in node.names
    }
    assert not any(
        name.startswith(("quill.core.wordpress.api", "quill.core.wordpress.site"))
        for name in imported
    )
    assert "quill.ui.wordpress_family" in imported or "quill.ui" in imported
