"""wp-admin parity on Posts, Pages and Media in the real Workbench frame (wordpress.md 9.18).

Counts by Status, per-item outcomes for Trash, Restore and Delete Permanently,
Duplicate as Draft, Empty Trash, Edit Picture (a shape and by numbers),
Regenerate Sizes, Attach, Detach, Download, Open in wp-admin, and Author and
Template as choices in Properties. Reuses the fake site of
``test_wp_workbench_window``; work runs inline and every dialog is answered here.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

wx = pytest.importorskip("wx")

from quill.core.wordpress import media_tools as mt  # noqa: E402
from quill.core.wordpress import site_taxonomies as tx  # noqa: E402
from quill.core.wordpress.api import WordPressApiError  # noqa: E402
from quill.core.wordpress.workbench_rows import WbRow, item_row, media_row  # noqa: E402
from quill.ui import wordpress_dialogs as dlg  # noqa: E402
from quill.ui import wordpress_workbench_dialogs as wdlg  # noqa: E402
from quill.ui import wordpress_workbench_parity as wbp  # noqa: E402
from quill.ui.wordpress_workbench_window import WordPressWorkbenchProvider  # noqa: E402
from quill.ui.workbench_frame import NodeRef, WorkbenchFrame  # noqa: E402
from tests.unit.ui.wordpress.test_wp_workbench_window import (  # noqa: E402
    SITE,
    FakeApi,
    _Commands,
    _inline,
)

PICTURE = {
    "id": 9,
    "title": {"rendered": "Sky"},
    "mime_type": "image/jpeg",
    "source_url": "https://radio.example/wp-content/uploads/sky.jpg",
    "media_details": {"width": 800, "height": 600},
    "post": 2,
    "modified_gmt": "2026-11-01T10:00:00",
}


class _Total:
    def __init__(self, total: int) -> None:
        self.total = total
        self.payload: list[Any] = []


class ParityApi(FakeApi):
    def __init__(self) -> None:
        super().__init__()
        self.counted: list[dict[str, Any]] = []
        self.refuse: set[str] = set()
        self.media = dict(PICTURE)
        self.posts.append({
            "id": 3,
            "title": {"raw": "Old", "rendered": "Old"},
            "status": "trash",
            "author": 3,
            "modified_gmt": "2026-10-01T10:00:00",
            "type": "post",
        })

    def request(self, method: str, route: str, **kw: Any) -> Any:
        if method == "GET":
            params = dict(kw.get("params") or {})
            self.counted.append({"route": route, **params})
            status = params.get("status")
            total = sum(1 for p in self.posts if status == "any" and p["status"] != "trash")
            total = total or sum(1 for p in self.posts if p["status"] == status)
            return _Total(total)
        return super().request(method, route, **kw)

    def get(self, route: str, **params: Any) -> Any:
        if route == "":
            return {"namespaces": ["wp/v2"], "routes": {"/wp/v2/media/(?P<id>[\\d]+)/edit": {}}}
        if route == "wp/v2/media/9":
            return dict(self.media)
        if route == "wp/v2/search":
            return [{"id": 2, "title": "News", "subtype": "post"}]
        if route == "wp/v2/users" and params.get("who") == "authors":
            return [{"id": 3, "name": "Jeff"}, {"id": 4, "name": "Ann"}]
        return super().get(route, **params)

    def post(self, route: str, body: Any = None, **params: Any) -> Any:
        if route == "wp/v2/posts":
            self.writes.append(("POST", route, body))
            return {"id": 50, **body, "title": {"raw": body["title"]}, "type": "post"}
        if route == "wp/v2/media/9/edit":
            self.writes.append(("POST", route, body))
            return {"id": 10, "title": {"rendered": "Sky-edited"}}
        if route == "wp/v2/media/9/post-process":
            self.writes.append(("POST", route, body))
            return {}
        if route == "wp/v2/media/9":
            self.writes.append(("POST", route, body))
            self.media.update(body)
            return dict(self.media)
        return super().post(route, body, **params)

    def iter_collection(self, route: str, params: Any = None, **kw: Any):
        if route == "wp/v2/media":
            assert dict(params or {}).get("media_type") == "image"
            yield dict(self.media)
            yield {**PICTURE, "id": 11, "title": {"rendered": "Sea"}, "alt_text": "Waves"}
            return
        yield from super().iter_collection(route, params, **kw)

    def delete(self, route: str, **params: Any) -> Any:
        if route in self.refuse:
            raise WordPressApiError("Sorry, you are not allowed to delete this post.", status=403)
        if route == "wp/v2/posts/50":
            self.writes.append(("DELETE", route, params))
            return {"id": 50, "status": "trash"}
        return super().delete(route, **params)


@pytest.fixture
def bench(wx_session_app, tmp_path):
    tx.clear_cache()
    said: list[str] = []
    api = ParityApi()
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


def _posts(bench: Any) -> list[WbRow]:
    return [item_row(p, "post", SITE) for p in bench.api.posts]


def _picture(bench: Any) -> WbRow:
    return media_row(bench.api.media, SITE)


def _yes(monkeypatch: Any, asked: list[str] | None = None) -> None:
    def confirm(*_a: Any, **k: Any) -> bool:
        if asked is not None:
            asked.append(k["message"])
        return True

    monkeypatch.setattr(dlg, "confirm", confirm)


# -- package 1: lists ------------------------------------------------------------------


def test_counts_by_status_says_every_view_in_one_sentence(bench) -> None:
    ref = NodeRef("site", "posts", SITE)
    bench.provider.do_status_counts(ref, _posts(bench)[0])
    said = bench.said[-1]
    assert said.startswith(f"Posts on {SITE}: All 2, Mine 2, Published 1, Drafts 1")
    assert "Trash 1" in said
    assert any(c.get("author") == 3 for c in bench.api.counted)
    bench.provider.do_status_counts(ref, _picture(bench))
    assert bench.said[-1].startswith(f"Media on {SITE}: All")


def test_bulk_trash_gives_each_item_its_own_outcome_and_undo_restores_only_those(
    bench, monkeypatch
) -> None:
    _yes(monkeypatch)
    rows = _posts(bench)[:2]
    bench.api.refuse.add("wp/v2/posts/2")
    monkeypatch.setattr(bench.provider, "selected_rows", lambda: rows)
    bench.provider.do_trash(NodeRef("site", "posts", SITE), rows[0])
    said = bench.said[-1]
    assert said.startswith(f"Moved 1 of 2 items to the Trash on {SITE}. Not done: News: Sorry")
    assert said.endswith("Ctrl+Z puts them back.")
    bench.provider.do_undo(None, None)
    restores = [w for w in bench.api.writes if w[0] == "POST" and w[1] == "wp/v2/posts/1"]
    assert restores and restores[-1][2] == {"status": "draft"}
    assert not [w for w in bench.api.writes if w[1] == "wp/v2/posts/2" and w[0] == "POST"]


def test_delete_permanently_says_what_was_not_deleted_and_cannot_be_undone(
    bench, monkeypatch
) -> None:
    _yes(monkeypatch)
    rows = _posts(bench)
    bench.api.refuse.add("wp/v2/posts/2")
    monkeypatch.setattr(bench.provider, "selected_rows", lambda: rows)
    bench.provider.do_delete_permanently(NodeRef("site", "posts", SITE), rows[0])
    assert bench.said[-1].startswith(f"Deleted 2 of 3 items permanently on {SITE}. Not done")
    assert bench.said[-1].endswith("This cannot be undone.")
    bench.provider.do_undo(None, None)
    assert "cannot be undone" in bench.said[-1]


def test_restore_reports_each_and_undo_trashes_them_again(bench) -> None:
    trashed = _posts(bench)[2]
    bench.provider.do_restore(NodeRef("site", "posts_trash", SITE), trashed)
    assert bench.said[-1] == f"Restored 1 item from the Trash, as drafts or waiting on {SITE}."
    bench.provider.do_undo(None, None)
    assert ("DELETE", "wp/v2/posts/3", {}) in bench.api.writes


def test_duplicate_makes_a_draft_copy_and_ctrl_z_trashes_it(bench, monkeypatch) -> None:
    asked: list[str] = []
    _yes(monkeypatch, asked)
    bench.provider.do_duplicate(NodeRef("site", "posts", SITE), _posts(bench)[1])
    assert "News (copy)" in asked[-1]
    created = [w for w in bench.api.writes if w[1] == "wp/v2/posts"][-1][2]
    assert created["status"] == "draft" and created["title"] == "News (copy)"
    assert bench.said[-1].startswith(f"News (copy) is a new draft on {SITE}.")
    bench.provider.do_undo(None, None)
    assert ("DELETE", "wp/v2/posts/50", {}) in bench.api.writes


def test_empty_trash_previews_names_then_deletes_each_for_good(bench, monkeypatch) -> None:
    previews: list[list[str]] = []
    monkeypatch.setattr(wdlg, "ask_preview", lambda *_a, **k: previews.append(k["lines"]) or True)
    monkeypatch.setattr(
        bench.api,
        "iter_collection",
        lambda route, params=None, **_k: iter([
            p for p in bench.api.posts if p["status"] == "trash"
        ]),
    )
    bench.provider.do_empty_trash(NodeRef("site", "posts_trash", SITE), None)
    assert previews == [["Old"]]
    assert ("DELETE", "wp/v2/posts/3", {"force": True}) in bench.api.writes
    assert bench.said[-1] == f"Deleted 1 item from the Trash permanently on {SITE}."


def test_dashboard_screen_names_what_rest_cannot_do_then_opens_wp_admin(bench) -> None:
    bench.provider.do_dashboard_screen(None, _posts(bench)[0])
    assert bench.commands.host.opened == [
        "https://radio.example/wp-admin/post.php?post=1&action=edit"
    ]
    assert "edit lock" in bench.said[-1]


# -- package 2: Properties --------------------------------------------------------------


def test_properties_offers_authors_and_says_the_default_template_in_words(bench) -> None:
    row = _posts(bench)[0]
    bench.api.posts[0]["template"] = ""
    sheet, values, *_rest = bench.provider._load_sheet(row)
    assert sheet.field("author").choices == ("Jeff (3)", "Ann (4)")
    assert values["author"] == "Jeff (3)"


# -- package 3: media --------------------------------------------------------------------


def test_edit_picture_crops_by_numbers_after_a_preview_in_words(bench, monkeypatch) -> None:
    labels: list[list[str]] = []

    def choose(*_a: Any, **k: Any) -> int:
        labels.append(list(k["rows"]))
        return k["rows"].index(wbp._CROP_BY_NUMBERS)

    previews: list[list[str]] = []
    monkeypatch.setattr(dlg, "ask_choice", choose)
    monkeypatch.setattr(dlg, "ask_text", lambda *_a, **_k: "10, 0, 80, 100")
    monkeypatch.setattr(wdlg, "ask_preview", lambda *_a, **k: previews.append(k["lines"]) or True)
    bench.provider.do_edit_picture(None, _picture(bench))
    assert "Turn a quarter to the right" in labels[0] and wbp._SCALE in labels[0]
    assert "keeps 80 percent of the width" in previews[0][0]
    sent = [w for w in bench.api.writes if w[1] == "wp/v2/media/9/edit"][-1][2]
    assert sent["modifiers"] == [
        {"type": "crop", "args": {"left": 10.0, "top": 0.0, "width": 80.0, "height": 100.0}}
    ]
    assert "The original is unchanged" in bench.said[-1]


def test_edit_picture_scale_opens_wp_admin_and_sends_nothing(bench, monkeypatch) -> None:
    monkeypatch.setattr(dlg, "ask_choice", lambda *_a, **k: k["rows"].index(wbp._SCALE))
    bench.provider.do_edit_picture(None, _picture(bench))
    assert bench.commands.host.opened == [
        "https://radio.example/wp-admin/post.php?post=9&action=edit"
    ]
    assert not [w for w in bench.api.writes if w[1].endswith("/edit")]


def test_regenerate_sizes_asks_the_site_to_remake_them(bench) -> None:
    bench.provider.do_regenerate_sizes(None, _picture(bench))
    assert ("POST", "wp/v2/media/9/post-process", {"action": "create-image-subsizes"}) in (
        bench.api.writes
    )
    assert bench.said[-1].startswith("Sizes remade for Sky")


def test_detach_then_undo_attaches_it_again(bench, monkeypatch) -> None:
    _yes(monkeypatch)
    bench.provider.do_detach(None, _picture(bench))
    assert ("POST", "wp/v2/media/9", {"post": 0}) in bench.api.writes
    assert bench.said[-1].startswith("Sky is attached to nothing.")
    bench.provider.do_undo(None, None)
    assert bench.api.writes[-1] == ("POST", "wp/v2/media/9", {"post": 2})


def test_attach_finds_by_words_and_saves_the_post(bench, monkeypatch) -> None:
    _yes(monkeypatch)
    bench.api.media["post"] = 0
    monkeypatch.setattr(dlg, "ask_text", lambda *_a, **_k: "news")
    bench.provider.do_attach(None, _picture(bench))
    assert ("POST", "wp/v2/media/9", {"post": 2}) in bench.api.writes
    assert "attached to News (post)" in bench.said[-1]


def test_download_saves_the_file_where_chosen(bench, monkeypatch, tmp_path) -> None:
    target = tmp_path / "sky.jpg"
    monkeypatch.setattr(wbp, "choose_save_path", lambda *_a, **_k: target)

    class _Got:
        content = b"jpeg bytes"

    seen: dict[str, Any] = {}

    def fetch(_opener: Any, address: str, **kw: Any) -> _Got:
        seen.update(address=address, **kw)
        return _Got()

    monkeypatch.setattr(mt, "download_file", fetch)
    bench.api._opener = None
    bench.api.timeout = 5.0
    bench.provider.do_download(None, _picture(bench))
    assert Path(target).read_bytes() == b"jpeg bytes"
    assert seen["address"].endswith("sky.jpg") and seen["any_type"] is True
    assert bench.said[-1] == f"Saved Sky to {target}."


# -- the featured image, chosen from the library ------------------------------------------


def _press(button: Any) -> None:
    event = wx.CommandEvent(wx.wxEVT_BUTTON, button.GetId())
    event.SetEventObject(button)
    button.GetEventHandler().ProcessEvent(event)


def test_properties_names_the_featured_image_by_title(bench) -> None:
    bench.api.posts[0]["featured_media"] = 9
    sheet, values, *_rest = bench.provider._load_sheet(_posts(bench)[0])
    assert sheet.field("featured_media").label == "Featured image"
    assert values["featured_media"] == "Sky (9)"


def test_choose_from_library_lists_pictures_with_alt_text_and_sets_the_field(
    bench, monkeypatch
) -> None:
    from quill.core.wordpress.workbench_edit import body_for
    from quill.ui.workbench_sheet_editor import WorkbenchSheetEditor

    offered: list[list[str]] = []

    def choose(*_a: Any, **k: Any) -> int:
        offered.append(list(k["rows"]))
        return 1

    monkeypatch.setattr(dlg, "ask_choice", choose)
    row = _posts(bench)[0]
    bench.api.posts[0]["featured_media"] = 9
    sheet, values, *_rest = bench.provider._load_sheet(row)
    editor = WorkbenchSheetEditor(
        bench.frame,
        sheet,
        values,
        title="Hello Properties",
        copy_text=lambda _t: None,
        on_save=lambda _s: True,
        field_buttons=bench.provider._featured(row),
    )
    try:
        choose_button, remove_button = editor.buttons["featured_media"]
        _press(choose_button)
        assert offered == [["Sky, no alt text", "Sea, alt text: Waves"]]
        state = editor.collect()
        assert [(c.key, c.after) for c in state.pending()] == [("featured_media", "Sea (11)")]
        assert body_for(sheet, row, state.pending()) == {"featured_media": 11}
        _press(remove_button)
        state = editor.collect()
        assert body_for(sheet, row, state.pending()) == {"featured_media": 0}
    finally:
        editor.dialog.Destroy()


def test_the_batch_sheet_sends_the_chosen_picture_by_number(bench) -> None:
    from quill.ui.wordpress_workbench_sheets import BATCH_SHEETS

    assert BATCH_SHEETS["item"].field("featured_media").label == "Featured image"
    rows = _posts(bench)[:2]
    bodies = bench.provider._bodies(rows, {"featured_media": "Sea (11)"})
    assert bodies == [{"featured_media": 11}, {"featured_media": 11}]
    assert bench.provider._featured(_picture(bench)) == {}
