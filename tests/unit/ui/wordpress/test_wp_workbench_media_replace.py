"""Media row > Replace File... in the real Workbench frame on a fake site: in place, new file
and uses repointed (with Ctrl+Z and the redirect offer), Enable Media Replace, and each cancel."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

wx = pytest.importorskip("wx")

from quill.core.wordpress import media_replace as mr  # noqa: E402
from quill.core.wordpress import site_taxonomies as tx  # noqa: E402
from quill.core.wordpress.workbench_actions import WORDPRESS_ACTIONS  # noqa: E402
from quill.core.wordpress.workbench_rows import WbRow  # noqa: E402
from quill.core.wordpress.workbench_site_files_actions import KEYLESS, MEDIA_ROWS  # noqa: E402
from quill.ui import wordpress_dialogs as dlg  # noqa: E402
from quill.ui import wordpress_workbench_dialogs as wdlg  # noqa: E402
from quill.ui.wordpress_workbench_window import WordPressWorkbenchProvider  # noqa: E402
from quill.ui.workbench_frame import WorkbenchFrame  # noqa: E402
from tests.unit.ui.wordpress.test_wp_workbench_window import (  # noqa: E402
    SITE,
    FakeApi,
    _Commands,
    _inline,
)

OLD = "https://radio.example/wp-content/uploads/mic.jpg"
NEW = "https://radio.example/wp-content/uploads/mic-1.png"
ROUTE = "/emr/v1/media/(?P<id>\\d+)/replace"


class MediaApi(FakeApi):
    """FakeApi with a media file used by post 1, a configurable REST index and plugins."""

    def __init__(self) -> None:
        super().__init__()
        self.routes: dict[str, Any] = {"/wp/v2/posts": {}}
        self.namespaces = ["wp/v2"]
        self.plugins: list[dict[str, Any]] = []
        self.after = OLD  # the address read back once the file is replaced in place
        self.replaced = False
        self.uploads: list[tuple[str, str]] = []
        self.posts[0]["content"] = {"raw": f'<img src="{OLD}" class="wp-image-300"/>'}

    def get(self, route: str, **params: Any) -> Any:
        if route == "":
            return {"name": SITE, "namespaces": self.namespaces, "routes": self.routes}
        if route == "wp/v2/plugins":
            return self.plugins
        if route == "wp/v2/media/300":
            return {
                "id": 300,
                "source_url": self.after if self.replaced else OLD,
                "mime_type": "image/jpeg",
                "media_details": {"filesize": 2048},
            }
        if route == "redirection/v1/group":
            return {"items": [{"id": 4, "name": "Redirections"}], "total": 1}
        return super().get(route, **params)

    def iter_collection(self, route: str, params: Any = None, **kw: Any) -> Iterator[Any]:
        if route == "wp/v2/posts":
            yield from (dict(p) for p in self.posts)
        elif route in ("wp/v2/pages", "wp/v2/blocks"):
            yield from ()
        else:
            yield from super().iter_collection(route, params, **kw)

    def upload(self, route: str, filename: str, content: bytes, content_type: str) -> Any:
        self.uploads.append((route, filename))
        self.replaced = route != "wp/v2/media"
        return {"id": 301, "source_url": NEW}


@pytest.fixture
def bench(wx_session_app, tmp_path):
    tx.clear_cache()
    said: list[str] = []
    api = MediaApi()
    commands = _Commands(said)
    provider = WordPressWorkbenchProvider(
        commands, announce=said.append, data_dir=tmp_path, api_for=lambda _p: api
    )
    frame = WorkbenchFrame(provider, announce=said.append, run_background=_inline)
    frame.said = said  # type: ignore[attr-defined]
    frame.api = api  # type: ignore[attr-defined]
    frame.commands = commands  # type: ignore[attr-defined]
    yield frame
    frame.frame.Destroy()
    tx.clear_cache()


@pytest.fixture
def new_file(bench, monkeypatch, tmp_path) -> Path:
    path = tmp_path / "mic.png"
    path.write_bytes(b"png")
    monkeypatch.setattr(bench.provider, "_file", lambda *_a, **_k: path)
    return path


def _media() -> WbRow:
    return WbRow(
        "media",
        SITE,
        "300",
        {"title": "Mic"},
        "",
        route="wp/v2/media/300",
        link=OLD,
        raw={"id": 300, "source_url": OLD},
    )


def _answers(monkeypatch: Any, choices: list[int | None]) -> list[Any]:
    asked: list[Any] = []

    def choose(*_a: Any, **k: Any) -> int | None:
        asked.append((k["prompt"], list(k["rows"])))
        return choices.pop(0)

    monkeypatch.setattr(dlg, "ask_choice", choose)
    return asked


def _previews(monkeypatch: Any, answer: bool = True) -> list[Any]:
    seen: list[Any] = []
    monkeypatch.setattr(
        wdlg, "ask_preview", lambda *_a, **k: seen.append((k["summary"], k["lines"])) or answer
    )
    return seen


def _confirms(monkeypatch: Any, answer: bool) -> list[str]:
    seen: list[str] = []
    monkeypatch.setattr(dlg, "confirm", lambda *_a, **k: seen.append(k["message"]) or answer)
    return seen


def _content(api: MediaApi) -> Any:
    return api.posts[0]["content"]


# -- refusals and cancels --------------------------------------------------------------------


def test_a_row_that_is_not_media_is_refused(bench, monkeypatch) -> None:
    picked: list[Any] = []
    monkeypatch.setattr(bench.provider, "_file", lambda *a, **_k: picked.append(a))
    bench.provider.do_replace_file(None, WbRow("item", SITE, "1", {"title": "Hello"}, ""))
    bench.provider.do_replace_file(None, None)
    assert picked == []
    assert bench.said == ["Replace File works on a file in the Media Library."] * 2


def test_cancelling_the_file_picker_reads_nothing(bench, monkeypatch) -> None:
    monkeypatch.setattr(bench.provider, "_file", lambda *_a, **_k: None)
    asked = _answers(monkeypatch, [])
    bench.provider.do_replace_file(None, _media())
    assert not asked and bench.said == [] and not bench.api.uploads


def test_a_file_type_the_library_does_not_take_is_refused(bench, monkeypatch, tmp_path) -> None:
    path = tmp_path / "notes.qzx"
    path.write_bytes(b"?")
    monkeypatch.setattr(bench.provider, "_file", lambda *_a, **_k: path)
    bench.provider.do_replace_file(None, _media())
    assert bench.said[-1] == (
        "notes.qzx is a application/octet-stream, which a WordPress Media Library does not take."
    )


# -- in place -------------------------------------------------------------------------------


def test_in_place_previews_sends_reads_back_and_records_a_step_with_no_undo(
    bench, new_file, monkeypatch
) -> None:
    bench.api.routes[ROUTE] = {"methods": ["POST"]}
    previews = _previews(monkeypatch)
    bench.provider.do_replace_file(None, _media())
    summary, lines = previews[0]
    assert summary == f"Replace Mic on {SITE} with mic.png?"
    assert f"The address stays the same: {OLD}" in lines
    assert any(line.startswith("Sent to emr/v1/media/300/replace") for line in lines)
    assert bench.api.uploads == [("emr/v1/media/300/replace", "mic.png")]
    assert bench.said[-1].startswith(f"Replaced. The address is the same, {OLD},")
    assert bench.said[-1].endswith("Its sizes were remade.")
    assert ("POST", "wp/v2/media/300/post-process", {"action": "create-image-subsizes"}) in (
        bench.api.writes
    )
    assert not bench.provider.history.can_undo()
    bench.provider.do_undo(None, None)
    assert bench.said[-1].endswith("This cannot be undone.")


def test_in_place_says_when_the_address_did_not_stay(bench, new_file, monkeypatch) -> None:
    bench.api.routes[ROUTE] = {"methods": ["POST"]}
    bench.api.after = NEW
    _previews(monkeypatch)
    bench.provider.do_replace_file(None, _media())
    assert bench.said[-1].startswith(f"The site took the file, but its address is now {NEW}")


def test_in_place_cancelled_at_the_preview_sends_nothing(bench, new_file, monkeypatch) -> None:
    bench.api.routes[ROUTE] = {"methods": ["POST"]}
    _previews(monkeypatch, answer=False)
    bench.provider.do_replace_file(None, _media())
    assert not bench.api.uploads and not bench.provider.history.entries


# -- a new file, uses repointed -----------------------------------------------------------


def test_repoint_uploads_points_every_use_at_the_new_file_and_ctrl_z_puts_them_back(
    bench, new_file, monkeypatch
) -> None:
    asked = _answers(monkeypatch, [0, 0])  # upload and repoint; keep the old file
    previews = _previews(monkeypatch)
    confirms = _confirms(monkeypatch, True)
    before = _content(bench.api)
    bench.provider.do_replace_file(None, _media())
    assert asked[0][1] == [
        "Upload it as a new file and point every use at it (the address changes)"
    ]  # no Enable Media Replace row: the plugin is not active
    assert asked[1][0] == "&Old file:"
    assert "Post Hello: its text" in previews[0][1]
    assert not confirms  # no Redirection plugin, so no redirect offer
    assert bench.api.uploads == [("wp/v2/media", "mic.png")]
    assert _content(bench.api) == f'<img src="{NEW}" class="wp-image-301"/>'
    assert not [w for w in bench.api.writes if w[0] == "DELETE"]  # the old file is kept
    assert bench.said[-1] == (
        "The file's address changes; QUILL updated 1 places that used it. Links from other "
        "websites to the old address will break unless a redirect is added. The old file is "
        "still in the library."
    )
    bench.provider.do_undo(None, None)
    assert _content(bench.api) == before["raw"]
    assert bench.said[-1] == "Put 1 back as they were. The new file stays in the library."


def test_repoint_can_delete_the_old_file_once_every_use_moved(bench, new_file, monkeypatch) -> None:
    _answers(monkeypatch, [0, 1])
    _previews(monkeypatch)
    bench.provider.do_replace_file(None, _media())
    assert ("DELETE", "wp/v2/media/300", {"force": True}) in bench.api.writes
    assert bench.said[-1].endswith("The old file was deleted.")


def test_repoint_offers_a_redirect_where_the_site_has_redirection(
    bench, new_file, monkeypatch
) -> None:
    bench.api.namespaces.append("redirection/v1")
    _answers(monkeypatch, [0, 0])
    _previews(monkeypatch)
    confirms = _confirms(monkeypatch, True)
    bench.provider.do_replace_file(None, _media())
    assert confirms and OLD in confirms[0]
    sent = next(b for m, r, b in bench.api.writes if r == "redirection/v1/redirect")
    assert sent == mr.redirect_for(OLD, NEW, 4)
    assert "A redirect now sends the old address to the new one." in bench.said[-1]


def test_a_declined_redirect_is_not_added_and_breakage_is_said(
    bench, new_file, monkeypatch
) -> None:
    bench.api.namespaces.append("redirection/v1")
    _answers(monkeypatch, [0, 0])
    _previews(monkeypatch)
    _confirms(monkeypatch, False)
    bench.provider.do_replace_file(None, _media())
    assert not [w for w in bench.api.writes if w[1] == "redirection/v1/redirect"]
    assert "will break unless a redirect is added" in bench.said[-1]


@pytest.mark.parametrize(
    ("choices", "preview"),
    [
        ([None], True),  # cancelled at How
        ([0], False),  # cancelled at the preview
        ([0, None], True),  # cancelled at the old file's fate
    ],
)
def test_repoint_cancelled_at_any_question_sends_nothing(
    bench, new_file, monkeypatch, choices, preview
) -> None:
    _answers(monkeypatch, choices)
    _previews(monkeypatch, answer=preview)
    before = _content(bench.api)
    bench.provider.do_replace_file(None, _media())
    assert not bench.api.uploads and _content(bench.api) == before
    assert not bench.provider.history.entries


def test_enable_media_replace_opens_its_box_in_wp_admin(bench, new_file, monkeypatch) -> None:
    bench.api.plugins = [{"plugin": mr.EMR_PLUGIN, "status": "active"}]
    asked = _answers(monkeypatch, [1])
    bench.provider.do_replace_file(None, _media())
    assert len(asked[0][1]) == 2 and "Enable Media Replace" in asked[0][1][1]
    assert bench.commands.host.opened == [
        "https://radio.example/wp-admin/post.php?post=300&action=edit"
    ]
    assert bench.said[-1].startswith("Opening Mic's edit screen")
    assert not bench.api.uploads


def test_replace_file_is_on_a_media_rows_context_menu_with_help_and_a_reason() -> None:
    (row,) = MEDIA_ROWS
    assert row.label == "Replace File..." and row.help and KEYLESS[row.command_id]
    assert row.command_id in {r.command_id for r in WORDPRESS_ACTIONS.rows_for("media")}
