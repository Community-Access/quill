"""Properties' field-plugin pages, Edit List and Edit Group, and Copy to QUILL Site Types.

WP-R-033, WP-R-034 and WP-R-038 in the real Workbench: the provider and shared
frame over a fake site that answers Meta Box, Pods and CMB2 as their REST
exposure is documented. Background work runs inline; the sheet is captured
rather than shown; list and group windows are answered by replacing the
helpers the shared editor imports.
"""

from __future__ import annotations

from typing import Any

import pytest

wx = pytest.importorskip("wx")

from quill.core.wordpress import site_taxonomies as tx  # noqa: E402
from quill.core.wordpress.api import WordPressApiError  # noqa: E402
from quill.core.wordpress.site_types_plugin import NAMESPACE as QST  # noqa: E402
from quill.core.wordpress.sites import SiteProfile, SiteStore  # noqa: E402
from quill.core.wordpress.workbench_actions import WORDPRESS_ACTIONS, command  # noqa: E402
from quill.core.wordpress.workbench_admin_actions import KEYLESS  # noqa: E402
from quill.ui import wordpress_block_dialogs as bdlg  # noqa: E402
from quill.ui import wordpress_dialogs as dlg  # noqa: E402
from quill.ui import wordpress_workbench_dialogs as wdlg  # noqa: E402
from quill.ui import wordpress_workbench_window as window  # noqa: E402
from quill.ui.wordpress_workbench_window import WordPressWorkbenchProvider  # noqa: E402
from quill.ui.workbench_frame import NodeRef, WorkbenchFrame  # noqa: E402

SITE = "Community Radio"

SPEAKERS = {
    "type": "array",
    "items": {
        "type": "object",
        "properties": {"name": {"type": "string"}, "minutes": {"type": "integer"}},
    },
}
VENUE = {"type": "object", "properties": {"street": {"type": "string"}, "zip": {"type": "string"}}}


class _Address:
    is_wpcom = False
    wpcom_site = ""
    site_url = "https://radio.example"


class _Auth:
    kind = "app_password"
    username = "jeff"


class Api:
    def __init__(self) -> None:
        self.address, self.auth = _Address(), _Auth()
        self.site_name = SITE
        self.writes: list[tuple[str, str, Any]] = []
        self.namespaces = ["wp/v2", QST, "pods/v1", "cmb2/v1"]
        self.item = {
            "id": 1,
            "title": {"raw": "Alpha", "rendered": "Alpha"},
            "status": "draft",
            "author": 3,
            "type": "post",
            "modified_gmt": "2026-11-01T10:00:00",
            "link": "https://radio.example/?p=1",
            "guest_count": "4",
            "meta": {
                "speakers": [{"name": "Ann", "minutes": 5}, {"name": "Bo", "minutes": 7}],
                "venue": {"street": "1 Main", "zip": "12345", "kept": "yes"},
            },
            "meta_box": {"mood": "calm"},
        }
        self.cmb2 = {"tagline": "Hello"}
        self.taken = False

    def get(self, route: str, **params: Any) -> Any:
        if route == "wp/v2/users/me":
            caps = {
                "edit_posts",
                "publish_posts",
                "delete_posts",
                "manage_options",
                "list_users",
                "edit_users",
                "promote_users",
            }
            return {
                "id": 3,
                "name": "Jeff",
                "username": "jeff",
                "roles": ["administrator"],
                "capabilities": dict.fromkeys(caps, True),
            }
        if route == "":
            return {
                "name": SITE,
                "home": "https://radio.example",
                "namespaces": self.namespaces,
                "routes": {"/wp/v2/posts": {}},
            }
        if route == "wp/v2/types":
            return {
                "post": {"name": "Posts", "rest_base": "posts"},
                "book": {"name": "Books", "rest_base": "book", "labels": {"singular_name": "Book"}},
            }
        if route == "wp/v2/taxonomies":
            return {}
        if route == "wp/v2/posts/1":
            return {**self.item, "meta": dict(self.item["meta"])}
        if route.startswith("wp/v2/users/"):
            return {"id": 3, "name": "Jeff"}
        if route == "pods/v1/pods":
            return {
                "pods": [
                    {
                        "name": "post",
                        "type": "post_type",
                        "label": "Posts",
                        "write_all": "1",
                        "fields": [{"name": "guest_count", "label": "Guests", "type": "number"}],
                    },
                    {"name": "book", "type": "post_type", "label": "Books", "fields": []},
                ]
            }
        if route == "cmb2/v1/boxes":
            return {"post_box": {"id": "post_box", "title": "Extras", "object_types": ["post"]}}
        if route == "cmb2/v1/boxes/post_box/fields":
            return {
                "tagline": {
                    "id": "tagline",
                    "name": "Tagline",
                    "type": "text",
                    "value": self.cmb2["tagline"],
                }
            }
        if route == "cmb2/v1/boxes/post_box/fields/tagline":
            return {"id": "tagline", "value": self.cmb2["tagline"]}
        if route == f"{QST}/types":
            return []
        if route.startswith(QST):
            return []
        return []

    def request(self, method: str, route: str, **kw: Any) -> Any:
        class _R:
            payload: Any = {}
            total = 0

        if method == "OPTIONS" and route == "wp/v2/posts":
            _R.payload = {
                "schema": {
                    "properties": {
                        "meta": {
                            "type": "object",
                            "properties": {"speakers": SPEAKERS, "venue": VENUE},
                        }
                    }
                }
            }
        return _R()

    def iter_collection(self, route: str, params: Any = None, **_kw: Any):
        if route == "wp/v2/posts":
            yield dict(self.item)

    def post(self, route: str, body: Any = None, **_p: Any) -> Any:
        self.writes.append(("POST", route, body))
        if route == f"{QST}/types" and self.taken:
            raise WordPressApiError("taken", status=409)
        if route == "wp/v2/posts/1":
            for key, value in (body or {}).items():
                if key in ("meta", "meta_box"):
                    self.item[key] = {**self.item.get(key, {}), **value}
                else:
                    self.item[key] = value
            return dict(self.item)
        if route == "cmb2/v1/boxes/post_box/fields/tagline":
            self.cmb2["tagline"] = body["value"]
        return dict(body or {})


class _Host:
    def __init__(self, said: list[str]) -> None:
        self.said, self.parent = said, None

    def announce(self, text: str) -> None:
        self.said.append(text)

    def open_in_browser(self, url: str) -> None:
        pass


class _Commands:
    def __init__(self, said: list[str]) -> None:
        self.host = _Host(said)

    def sites(self) -> SiteStore:
        return SiteStore([SiteProfile("s1", SITE, "https://radio.example", "jeff")], "s1")


def _inline(_name: str, work: Any, done: Any, failed: Any) -> None:
    try:
        result = work()
    except Exception as exc:  # noqa: BLE001
        failed(exc)
        return
    done(result)


@pytest.fixture
def bench(wx_session_app, tmp_path):
    tx.clear_cache()
    said: list[str] = []
    api = Api()
    provider = WordPressWorkbenchProvider(
        _Commands(said), announce=said.append, data_dir=tmp_path, api_for=lambda _p: api
    )
    frame = WorkbenchFrame(provider, announce=said.append, run_background=_inline)
    frame.said, frame.api = said, api  # type: ignore[attr-defined]
    yield frame
    window._OPEN.pop("wordpress", None)
    frame.frame.Destroy()
    tx.clear_cache()


@pytest.fixture
def sheets(monkeypatch):
    from quill.ui import workbench_sheet_editor as editor

    opened: list[Any] = []
    monkeypatch.setattr(editor.WorkbenchSheetEditor, "show", lambda self: opened.append(self) or 0)
    return opened


def _go(frame: WorkbenchFrame, ref: NodeRef) -> None:
    assert frame.select(ref), ref
    if frame.current != ref:
        frame._show_node(ref, remember=True)


def _open_sheet(bench) -> Any:
    _go(bench, NodeRef("site", "posts", SITE))
    index = next(i for i, r in enumerate(bench.rows) if r.title == "Alpha")
    bench.focus_row(index)
    bench.run(command("sheet"))


def _press(button: Any) -> None:
    event = wx.CommandEvent(wx.EVT_BUTTON.typeId, button.GetId())
    event.SetEventObject(button)
    button.GetEventHandler().ProcessEvent(event)


def test_meta_box_pods_and_cmb2_each_get_a_page_and_save_their_own_way(bench, sheets) -> None:
    _open_sheet(bench)
    sheet = sheets[-1]
    titles = [p.title for p in sheet.sheet.pages]
    assert {"Meta", "Meta Box", "Pods (Posts)", "CMB2"} <= set(titles)
    assert sheet.controls["meta_box.mood"].GetValue() == "calm"
    assert sheet.controls["pods.guest_count"].GetValue() == "4"
    assert sheet.controls["cmb2.post_box.tagline"].GetValue() == "Hello"
    sheet.controls["meta_box.mood"].ChangeValue("lively")
    sheet.controls["pods.guest_count"].ChangeValue("6")
    sheet.controls["cmb2.post_box.tagline"].ChangeValue("Welcome")
    sheet.collect()
    sheet._on_save(sheet.state)
    posted = [w for w in bench.api.writes if w[1] == "wp/v2/posts/1"][-1][2]
    assert posted == {"meta_box": {"mood": "lively"}, "guest_count": 6.0}
    assert bench.api.writes[-1] == (
        "POST",
        "cmb2/v1/boxes/post_box/fields/tagline",
        {"object_id": 1, "object_type": "post", "value": "Welcome"},
    )
    assert bench.said[-1].startswith("Saved 3 changes to Alpha")
    bench.run(command("undo"))  # every plugin's value goes back
    assert bench.api.cmb2["tagline"] == "Hello" and bench.api.item["meta_box"]["mood"] == "calm"


def test_edit_group_opens_the_shared_form_and_keeps_keys_it_does_not_name(
    bench, sheets, monkeypatch
) -> None:
    asked: list[Any] = []

    def fields(*_a: Any, **kw: Any) -> dict[str, Any]:
        asked.append(kw)
        return {"street": "2 Elm"}

    monkeypatch.setattr(bdlg, "ask_fields", fields)
    _open_sheet(bench)
    sheet = sheets[-1]
    (button,) = sheet.buttons["meta.venue"]
    assert button.GetLabel() == "Edit Group..."
    _press(button)
    assert [f.key for f in asked[-1]["fields"]] == ["street", "zip"]
    assert '"street": "2 Elm"' in sheet.controls["meta.venue"].GetValue()
    assert bench.said[-1] == "venue changed. OK or Apply sends it to the site."
    sheet.collect()
    sheet._on_save(sheet.state)
    sent = [w for w in bench.api.writes if w[1] == "wp/v2/posts/1"][-1][2]
    assert sent == {"meta": {"venue": {"street": "2 Elm", "zip": "12345", "kept": "yes"}}}


def test_edit_list_reorders_in_the_shared_list_window(bench, sheets, monkeypatch) -> None:
    def list_window(_parent: Any, _modal: Any, **kw: Any) -> Any:
        actions = {a.label: a for a in kw["actions"]}
        actions["Move &Down"].run(0)
        actions["&Keep Changes"].run(None)

        class _W:
            def Destroy(self) -> None:  # noqa: N802 - wx's name
                pass

        return _W()

    monkeypatch.setattr(dlg, "show_list_window", list_window)
    _open_sheet(bench)
    sheet = sheets[-1]
    (button,) = sheet.buttons["meta.speakers"]
    assert button.GetLabel() == "Edit List..."
    _press(button)
    sheet.collect()
    sheet._on_save(sheet.state)
    sent = [w for w in bench.api.writes if w[1] == "wp/v2/posts/1"][-1][2]
    assert [s["name"] for s in sent["meta"]["speakers"]] == ["Bo", "Ann"]


def test_a_box_that_is_not_valid_json_is_said_and_left_alone(bench, sheets) -> None:
    _open_sheet(bench)
    sheet = sheets[-1]
    sheet.controls["meta.venue"].ChangeValue("{ not json")
    _press(sheet.buttons["meta.venue"][0])
    assert "does not hold a valid JSON object" in bench.said[-1]
    assert sheet.controls["meta.venue"].GetValue() == "{ not json"


def test_copy_to_site_types_previews_a_copy_and_says_why_when_refused(bench, monkeypatch) -> None:
    previews: list[Any] = []
    monkeypatch.setattr(wdlg, "ask_preview", lambda *a, **kw: previews.append(kw) or True)
    offered = [a.command_id for a in WORDPRESS_ACTIONS.rows_for("model")]
    assert command("move_to_site_types") in offered and KEYLESS[command("move_to_site_types")]
    _go(bench, NodeRef("site", "content_model", SITE))
    rows = {r.key: r for r in bench.rows}
    assert rows["book"].cell("registered_by") == "Pods"
    bench.provider.do_move_to_site_types(None, rows["book"])
    assert "Nothing is removed from Pods" in previews[-1]["summary"]
    assert bench.api.writes[-1][1] == f"{QST}/types"
    assert bench.api.writes[-1][2]["slug"] == "book"
    assert bench.said[-1].startswith("Copied Books into QUILL Site Types")
    bench.api.taken = True
    bench.provider.do_move_to_site_types(None, rows["book"])
    assert "Pods still registers it" in bench.said[-1]
    bench.provider.do_move_to_site_types(None, rows["post"])
    assert "cannot be copied" in bench.said[-1]
