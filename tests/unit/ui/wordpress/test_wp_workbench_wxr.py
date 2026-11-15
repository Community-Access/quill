"""Tools > WXR Files in the real Workbench frame on a fake site: Export Site as WXR
(each scope, each cancel) and Import WXR as Drafts (each question, each cancel, Ctrl+Z)."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

wx = pytest.importorskip("wx")

from quill.core.wordpress import media_tools as mt  # noqa: E402
from quill.core.wordpress import site_taxonomies as tx  # noqa: E402
from quill.core.wordpress.workbench_site_files_actions import KEYLESS, WXR_SUB  # noqa: E402
from quill.core.wordpress.wxr_read import read_wxr  # noqa: E402
from quill.ui import wordpress_dialogs as dlg  # noqa: E402
from quill.ui import wordpress_workbench_dialogs as wdlg  # noqa: E402
from quill.ui.wordpress_workbench_window import WordPressWorkbenchProvider  # noqa: E402
from quill.ui.workbench_frame import WorkbenchFrame  # noqa: E402
from tests.unit.core.wordpress.test_wp_wxr_core import _item, _wxr  # noqa: E402
from tests.unit.ui.wordpress.test_wp_workbench_window import (  # noqa: E402
    SITE,
    FakeApi,
    _Commands,
    _inline,
)

PIC = "https://old.example/wp-content/uploads/pic.jpg"


class WxrApi(FakeApi):
    """FakeApi with every post listed for an export, a category, and drafts that get numbers."""

    def __init__(self) -> None:
        super().__init__()
        self.asked: list[tuple[str, dict[str, Any]]] = []
        self.next_id = 1000
        self.uploads: list[str] = []
        self._opener = object()
        self.timeout = 10.0

    def iter_collection(self, route: str, params: Any = None, **kw: Any) -> Iterator[Any]:
        params = dict(params or {})
        self.asked.append((route, params))
        if route == "wp/v2/posts" and "," in str(params.get("status", "")):
            for post in self.posts:
                if params.get("categories") in (None, *post["categories"]):
                    yield dict(post)
        elif route == "wp/v2/categories":
            yield {"id": 5, "name": "Shows", "slug": "shows", "count": 1}
        else:
            yield from super().iter_collection(route, params, **kw)

    def post(self, route: str, body: Any = None, **params: Any) -> Any:
        if route in ("wp/v2/posts", "wp/v2/pages"):
            self.writes.append(("POST", route, body))
            self.next_id += 1
            return {"id": self.next_id, "link": f"https://radio.example/?p={self.next_id}"}
        return super().post(route, body, **params)

    def upload(self, route: str, filename: str, content: bytes, content_type: str) -> Any:
        self.uploads.append(filename)
        return {"id": 900, "source_url": "https://radio.example/wp-content/uploads/pic.jpg"}

    def delete(self, route: str, **params: Any) -> Any:
        if int(route.rsplit("/", 1)[1]) > 1000:
            self.writes.append(("DELETE", route, params))
            return {}
        return super().delete(route, **params)


@pytest.fixture
def bench(wx_session_app, tmp_path):
    tx.clear_cache()
    said: list[str] = []
    api = WxrApi()
    provider = WordPressWorkbenchProvider(
        _Commands(said), announce=said.append, data_dir=tmp_path, api_for=lambda _p: api
    )
    frame = WorkbenchFrame(provider, announce=said.append, run_background=_inline)
    frame.said = said  # type: ignore[attr-defined]
    frame.api = api  # type: ignore[attr-defined]
    yield frame
    frame.frame.Destroy()
    tx.clear_cache()


@pytest.fixture
def site(bench, monkeypatch):
    monkeypatch.setattr(bench.provider, "site_of", lambda _ref: SITE)


def _answers(monkeypatch: Any, choices: list[int | None], texts: list[str | None]) -> list[Any]:
    asked: list[Any] = []

    def choose(*_a: Any, **k: Any) -> int | None:
        asked.append((k["prompt"], list(k["rows"])))
        return choices.pop(0)

    monkeypatch.setattr(dlg, "ask_choice", choose)
    monkeypatch.setattr(dlg, "ask_text", lambda *_a, **_k: texts.pop(0))
    return asked


def _reports(monkeypatch: Any) -> list[str]:
    reports: list[str] = []
    monkeypatch.setattr(dlg, "show_report", lambda *_a, **k: reports.append(k["text"]))
    return reports


def _previews(monkeypatch: Any, answer: bool = True) -> list[Any]:
    seen: list[Any] = []
    monkeypatch.setattr(
        wdlg, "ask_preview", lambda *_a, **k: seen.append((k["summary"], k["lines"])) or answer
    )
    return seen


def _pick(monkeypatch: Any, bench: Any, path: Path | None) -> list[tuple[str, bool]]:
    asked: list[tuple[str, bool]] = []

    def chosen(title: str, _wildcard: str, *, save: bool) -> Path | None:
        asked.append((title, save))
        return path

    monkeypatch.setattr(bench.provider, "_file", chosen)
    return asked


def _posts_asked(api: WxrApi) -> list[dict[str, Any]]:
    return [p for r, p in api.asked if r == "wp/v2/posts" and "," in str(p.get("status", ""))]


# -- export -------------------------------------------------------------------------------


def test_export_everything_writes_a_checked_file_and_reports_what_was_left_out(
    bench, site, monkeypatch, tmp_path
) -> None:
    asked = _answers(monkeypatch, [0], [])
    reports = _reports(monkeypatch)
    files = _pick(monkeypatch, bench, tmp_path / "radio")
    bench.provider.do_export_wxr(None, None)
    assert asked[0][0] == "&Export:" and len(asked[0][1]) == 5
    assert files == [("Export Site as WXR", True)]
    written = tmp_path / "radio.xml"  # the extension is added
    assert {i.title for i in read_wxr(written.read_bytes()).items} == {"Hello", "News"}
    assert bench.said[-1].startswith("Wrote radio.xml: 2 post, ")
    assert bench.said[-1].endswith("radio.xml is a well-formed WXR 1.2 file with 2 items.")
    assert reports[0].startswith(f"{SITE}: everything.")
    assert "\nLeft out:\n" in reports[0]


def test_export_cancelled_at_the_scope_or_the_file_writes_nothing(
    bench, site, monkeypatch, tmp_path
) -> None:
    _answers(monkeypatch, [None, 1], [])
    files = _pick(monkeypatch, bench, None)
    bench.provider.do_export_wxr(None, None)
    assert files == [] and bench.said == []
    bench.provider.do_export_wxr(None, None)  # Posts only, then the file picker cancelled
    assert files == [("Export Site as WXR", True)]
    assert not list(tmp_path.glob("*.xml")) and bench.said == []


def test_export_a_date_range_asks_both_days_and_sends_them(
    bench, site, monkeypatch, tmp_path
) -> None:
    reports = _reports(monkeypatch)
    _answers(monkeypatch, [3], ["2026-01-01", ""])
    _pick(monkeypatch, bench, tmp_path / "dates.xml")
    bench.provider.do_export_wxr(None, None)
    assert _posts_asked(bench.api)[0]["after"] == "2026-01-01T00:00:00"
    assert "before" not in _posts_asked(bench.api)[0]
    assert reports[0].startswith(f"{SITE}: posts and pages from 2026-01-01 to today.")


def test_export_a_date_range_refuses_a_bad_day_and_stops_on_cancel(
    bench, site, monkeypatch
) -> None:
    files = _pick(monkeypatch, bench, None)
    _answers(monkeypatch, [3, 3], ["January", "2026-01-01", None])
    bench.provider.do_export_wxr(None, None)
    assert bench.said[-1] == ("January is not a day written as year-month-day, such as 2026-01-31.")
    bench.provider.do_export_wxr(None, None)  # From answered, To cancelled
    assert files == [] and not _posts_asked(bench.api)


def test_export_one_category_takes_its_posts(bench, site, monkeypatch, tmp_path) -> None:
    reports = _reports(monkeypatch)
    asked = _answers(monkeypatch, [4, 0], [])
    _pick(monkeypatch, bench, tmp_path / "shows.xml")
    bench.provider.do_export_wxr(None, None)
    assert asked[1] == ("&Category:", ["Shows (1 posts)"])
    assert _posts_asked(bench.api)[0]["categories"] == 5
    titles = [i.title for i in read_wxr((tmp_path / "shows.xml").read_bytes()).items]
    assert titles == ["Hello"]
    assert reports[0].startswith(f"{SITE}: posts in the category Shows.")


def test_export_one_category_cancelled_at_the_category(bench, site, monkeypatch) -> None:
    files = _pick(monkeypatch, bench, None)
    _answers(monkeypatch, [4, None], [])
    bench.provider.do_export_wxr(None, None)
    assert files == [] and bench.said == []


def test_export_with_no_site_asks_to_connect_one(bench, monkeypatch) -> None:
    monkeypatch.setattr(bench.provider, "site_of", lambda _ref: "")
    monkeypatch.setattr(bench.provider, "current_site", lambda: "")
    asked = _answers(monkeypatch, [], [])
    bench.provider.do_export_wxr(None, None)
    bench.provider.do_import_wxr(None, None)
    assert not asked and bench.said[-1].startswith("Connect a site first")


# -- import -------------------------------------------------------------------------------


def _import_file(tmp_path: Path, *, with_file: bool = True) -> Path:
    attachment = _item(
        300,
        "attachment",
        "Pic",
        status="inherit",
        extra=f"<wp:attachment_url>{PIC}</wp:attachment_url>",
    )
    body = (
        "<wp:author><wp:author_login>dave</wp:author_login></wp:author>"
        + _item(
            100,
            "post",
            "Morning",
            creator="dave",
            content=f'<img src="{PIC}" class="wp-image-300"/>',
            extra="<wp:postmeta><wp:meta_key>_thumbnail_id</wp:meta_key>"
            "<wp:meta_value>300</wp:meta_value></wp:postmeta>",
        )
        + (attachment if with_file else "")
    )
    path = tmp_path / "old.xml"
    path.write_bytes(_wxr(body))
    return path


def _drafts(api: WxrApi) -> list[dict[str, Any]]:
    return [b for m, r, b in api.writes if m == "POST" and r == "wp/v2/posts"]


def test_import_asks_the_author_previews_skips_files_and_ctrl_z_trashes(
    bench, site, monkeypatch, tmp_path
) -> None:
    reports = _reports(monkeypatch)
    previews = _previews(monkeypatch)
    asked = _answers(monkeypatch, [1, 1], [])  # unmatched authors to Ann; skip the files
    files = _pick(monkeypatch, bench, _import_file(tmp_path))
    bench.provider.do_import_wxr(None, None)
    assert files == [("Import WXR as Drafts", False)]
    assert asked[0] == ("&Give unmatched authors' items to:", ["Jeff", "Ann"])
    assert asked[1][0] == "&Files:" and "old.example" in asked[1][1][0]
    assert previews[0][0].startswith("Make 1 items from old.xml on Community Radio")
    assert "Author dave is not on this site; given to Ann." in previews[0][1]  # as chosen
    (draft,) = _drafts(bench.api)
    assert draft["status"] == "draft" and draft["author"] == 4 and draft["title"] == "Morning"
    assert PIC in draft["content"] and "featured_media" not in draft
    assert not bench.api.uploads
    assert bench.said[-1] == (
        "Imported 1 of 1 items from old.xml into Community Radio as drafts, with 0 files. "
        "Ctrl+Z moves the drafts to the Trash."
    )
    assert "Made post Morning as a draft, number 1001." in reports[0]
    assert bench.provider.history.can_undo()
    bench.provider.do_undo(None, None)
    assert ("DELETE", "wp/v2/posts/1001", {}) in bench.api.writes
    assert bench.said[-1] == "Moved 1 imported drafts to the Trash."


def test_import_downloads_the_files_when_chosen(bench, site, monkeypatch, tmp_path) -> None:
    class Got:
        filename = "pic.jpg"
        content = b"jpg"
        content_type = "image/jpeg"

    fetched: list[str] = []
    monkeypatch.setattr(
        mt, "download_file", lambda _opener, address, **_k: fetched.append(address) or Got()
    )
    _reports(monkeypatch)
    _previews(monkeypatch)
    _answers(monkeypatch, [0, 0], [])  # unmatched authors to Jeff; download
    _pick(monkeypatch, bench, _import_file(tmp_path))
    bench.provider.do_import_wxr(None, None)
    assert fetched == [PIC] and bench.api.uploads == ["pic.jpg"]
    (draft,) = _drafts(bench.api)
    assert draft["author"] == 3 and draft["featured_media"] == 900
    assert 'class="wp-image-900"' in draft["content"]
    assert "with 1 files" in bench.said[-1]


@pytest.mark.parametrize(
    ("choices", "preview"),
    [
        ([None], True),  # cancelled at the author
        ([0], False),  # cancelled at the preview
        ([0, None], True),  # cancelled at the files question
    ],
)
def test_import_cancelled_at_any_question_makes_nothing(
    bench, site, monkeypatch, tmp_path, choices, preview
) -> None:
    _reports(monkeypatch)
    _previews(monkeypatch, answer=preview)
    _answers(monkeypatch, choices, [])
    _pick(monkeypatch, bench, _import_file(tmp_path))
    bench.provider.do_import_wxr(None, None)
    assert not _drafts(bench.api) and not bench.provider.history.entries


def test_import_cancelled_at_the_file_picker_reads_nothing(bench, site, monkeypatch) -> None:
    asked = _answers(monkeypatch, [], [])
    _pick(monkeypatch, bench, None)
    bench.provider.do_import_wxr(None, None)
    assert not asked and not bench.api.asked and bench.said == []


def test_import_of_a_file_that_is_not_wxr_says_so(bench, site, monkeypatch, tmp_path) -> None:
    path = tmp_path / "feed.xml"
    path.write_bytes(b"<feed><channel/></feed>")
    _pick(monkeypatch, bench, path)
    bench.provider.do_import_wxr(None, None)
    assert bench.said[-1] == "feed.xml has no rss channel, so it is not a WordPress export file."


def test_import_with_nothing_to_take_says_so(bench, site, monkeypatch, tmp_path) -> None:
    path = tmp_path / "menus.xml"
    path.write_bytes(_wxr(_item(500, "nav_menu_item", "Home")))
    asked = _answers(monkeypatch, [], [])
    _pick(monkeypatch, bench, path)
    bench.provider.do_import_wxr(None, None)
    assert not asked and bench.said[-1] == (
        "menus.xml has nothing Community Radio can take as a draft."
    )


def test_both_commands_are_in_tools_wxr_files_with_help_and_a_reason() -> None:
    labels = [row.label for row in WXR_SUB.rows]
    assert labels == ["&Export Site as WXR...", "&Import WXR as Drafts..."]
    for row in WXR_SUB.rows:
        assert row.help and KEYLESS[row.command_id]
