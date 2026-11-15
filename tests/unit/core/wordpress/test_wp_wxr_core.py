"""Export Site as WXR, reading WXR back, and Import WXR as Drafts, without a site
(quill.core.wordpress.wxr_export, wxr_read and wxr_import)."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

from quill.core.wordpress import wxr_read
from quill.core.wordpress.api import WordPressApiError
from quill.core.wordpress.wxr_export import Scope, export_wxr
from quill.core.wordpress.wxr_import import plan_import, send_import, undo_import
from quill.core.wordpress.wxr_read import WxrError, read_wxr, validate_wxr

OLD = "https://old.example"
NEW = "https://new.example"


class _Address:
    site_url = OLD


class ExportApi:
    """A site with two people, nested categories, a tag, a custom taxonomy and type,
    posts, pages, files, one comment and one menu."""

    def __init__(self) -> None:
        self.address = _Address()
        self.asked: list[tuple[str, dict[str, Any]]] = []
        self.users = [
            {"id": 1, "username": "ann", "email": "ann@old.example", "name": "Ann"},
            {"id": 2, "username": "bob", "email": "bob@old.example", "name": "Bob"},
        ]
        self.terms: dict[str, list[dict[str, Any]]] = {
            "categories": [
                {"id": 5, "slug": "news", "name": "News", "parent": 0},
                {"id": 6, "slug": "local", "name": "Local", "parent": 5},
                {"id": 7, "slug": "sport", "name": "Sport", "parent": 0},
            ],
            "tags": [{"id": 11, "slug": "live", "name": "Live"}],
            "genres": [{"id": 21, "slug": "jazz", "name": "Jazz"}],
        }
        self.posts = [
            {
                "id": 100,
                "title": {"raw": "Morning Show"},
                "content": {"raw": "<p>Hi ]]> there</p>"},
                "excerpt": {"raw": "Hi"},
                "status": "publish",
                "author": 1,
                "date": "2026-01-10T08:00:00",
                "date_gmt": "2026-01-10T08:00:00",
                "slug": "morning-show",
                "link": f"{OLD}/morning-show/",
                "categories": [6],
                "tags": [11],
                "featured_media": 300,
            },
            {
                "id": 101,
                "title": {"raw": "Match Report"},
                "content": {"raw": "<p>Goal</p>"},
                "status": "draft",
                "author": 2,
                "date": "2026-03-05T09:00:00",
                "date_gmt": "2026-03-05T09:00:00",
                "slug": "match-report",
                "link": f"{OLD}/?p=101",
                "categories": [7],
                "tags": [],
            },
        ]
        self.pages = [
            {
                "id": 200,
                "title": {"raw": "About"},
                "content": {"raw": "<p>About us</p>"},
                "status": "publish",
                "author": 1,
                "date": "2026-02-01T10:00:00",
                "link": f"{OLD}/about/",
                "parent": 0,
            },
            {
                "id": 201,
                "title": {"raw": "Team"},
                "content": {"raw": "<p>Team</p>"},
                "status": "publish",
                "author": 1,
                "date": "2026-02-02T10:00:00",
                "link": f"{OLD}/about/team/",
                "parent": 200,
                "menu_order": 2,
            },
        ]
        self.events = [
            {"id": 400, "title": {"raw": "Gig"}, "status": "publish", "author": 2, "genres": [21]}
        ]
        self.media = [
            {
                "id": 300,
                "title": {"raw": "Pic"},
                "author": 1,
                "post": 0,
                "source_url": f"{OLD}/wp-content/uploads/pic.jpg",
                "alt_text": "A microphone",
            },
            {
                "id": 301,
                "title": {"raw": "Ball"},
                "author": 2,
                "post": 101,
                "source_url": f"{OLD}/wp-content/uploads/ball.jpg",
            },
            {
                "id": 302,
                "title": {"raw": "Loose"},
                "author": 2,
                "post": 0,
                "source_url": f"{OLD}/wp-content/uploads/loose.pdf",
            },
        ]

    def get(self, route: str, **params: Any) -> Any:
        if route == "":
            return {
                "name": "Old Radio",
                "description": "Shows",
                "url": OLD,
                "home": OLD,
                "language": "en-GB",
            }
        if route == "wp/v2/taxonomies":
            return {
                "category": {"rest_base": "categories"},
                "post_tag": {"rest_base": "tags"},
                "genre": {"rest_base": "genres", "rest_namespace": "wp/v2"},
                "nav_menu": {"rest_base": "menus"},
            }
        if route == "wp/v2/types":
            return {
                "post": {"rest_base": "posts"},
                "page": {"rest_base": "pages"},
                "attachment": {"rest_base": "media"},
                "event": {"rest_base": "events"},
            }
        if route == "wp/v2/menus":
            return [{"id": 9, "name": "Main", "slug": "main", "description": ""}]
        return None

    def iter_collection(self, route: str, params: Any = None, **_kw: Any) -> Iterator[Any]:
        params = dict(params or {})
        self.asked.append((route, params))
        if route == "wp/v2/users":
            yield from (dict(u) for u in self.users)
        elif route.removeprefix("wp/v2/") in self.terms:
            yield from (dict(t) for t in self.terms[route.removeprefix("wp/v2/")])
        elif route in ("wp/v2/posts", "wp/v2/pages"):
            for row in self.posts if route == "wp/v2/posts" else self.pages:
                if "categories" in params and params["categories"] not in row["categories"]:
                    continue
                if "after" in params and row["date"] < params["after"]:
                    continue
                if "before" in params and row["date"] > params["before"]:
                    continue
                yield dict(row)
        elif route == "wp/v2/events":
            yield from (dict(e) for e in self.events)
        elif route == "wp/v2/media":
            yield from (dict(m) for m in self.media)
        elif route == "wp/v2/comments" and params.get("status") == "approve":
            yield {
                "id": 70,
                "post": 100,
                "author_name": "Listener",
                "content": {"raw": "Great show"},
                "status": "approved",
                "date": "2026-01-11T08:00:00",
            }
        elif route == "wp/v2/menu-items":
            yield {
                "id": 500,
                "title": {"raw": "Home"},
                "menus": 9,
                "type": "custom",
                "url": "/",
                "menu_order": 1,
            }


def _export(tmp_path: Path, scope: Scope | None = None) -> tuple[Any, Any, Path]:
    path = tmp_path / "site.xml"
    report = export_wxr(ExportApi(), path, scope)
    return report, read_wxr(path.read_bytes(), path.name), path


def _items(wxr: Any, post_type: str) -> list[Any]:
    return [i for i in wxr.items if i.post_type == post_type]


# -- export, read back -------------------------------------------------------------------


def test_everything_round_trips_through_read_wxr(tmp_path) -> None:
    report, wxr, path = _export(tmp_path)
    assert (wxr.version, wxr.title, wxr.site_url, wxr.blog_url) == ("1.2", "Old Radio", OLD, OLD)
    assert {a.login for a in wxr.authors} == {"ann", "bob"}
    terms = {(t.taxonomy, t.slug): t for t in wxr.terms}
    assert terms[("category", "local")].parent == "news"
    assert terms[("category", "local")].name == "Local"
    assert ("category", "sport") in terms and ("post_tag", "live") in terms
    assert terms[("genre", "jazz")].name == "Jazz"
    assert terms[("nav_menu", "main")].name == "Main"
    assert {i.post_id for i in _items(wxr, "post")} == {100, 101}
    assert {i.post_id for i in _items(wxr, "page")} == {200, 201}
    assert [i.post_id for i in _items(wxr, "event")] == [400]
    assert {i.post_id for i in _items(wxr, "attachment")} == {300, 301, 302}
    assert [i.title for i in _items(wxr, "nav_menu_item")] == ["Home"]
    morning = next(i for i in wxr.items if i.post_id == 100)
    assert morning.content == "<p>Hi ]]> there</p>"  # a CDATA end survives
    assert morning.creator == "ann" and morning.status == "publish"
    assert ("category", "local", "Local") in morning.terms
    assert ("post_tag", "live", "Live") in morning.terms
    assert morning.meta["_thumbnail_id"] == "300" and morning.comments == 1
    team = next(i for i in wxr.items if i.post_id == 201)
    assert team.parent == 200 and team.menu_order == 2
    pic = next(i for i in wxr.items if i.post_id == 300)
    assert pic.attachment_url == f"{OLD}/wp-content/uploads/pic.jpg"
    assert pic.status == "inherit" and pic.meta["_wp_attachment_image_alt"] == "A microphone"
    assert report.counts["post"] == 2 and report.counts["comments"] == 1
    assert report.counts["attachments"] == 3 and report.counts["menu items"] == 1
    assert report.sentence("site.xml").startswith("Wrote site.xml: 2 post, ")
    assert not list(tmp_path.glob("*.part"))  # temporary files are gone
    assert validate_wxr(path) == (True, "site.xml is a well-formed WXR 1.2 file with 9 items.")


def test_a_category_export_takes_only_the_terms_people_and_files_it_uses(tmp_path) -> None:
    report, wxr, _path = _export(tmp_path, Scope("category", category=6, category_name="Local"))
    assert [i.post_id for i in wxr.items if i.post_type == "post"] == [100]
    assert not _items(wxr, "page") and not _items(wxr, "nav_menu_item")
    assert {(t.taxonomy, t.slug) for t in wxr.terms} == {
        ("category", "local"),
        ("category", "news"),  # the parent goes with its child
        ("post_tag", "live"),
    }
    assert [a.login for a in wxr.authors] == ["ann"]
    assert [i.post_id for i in _items(wxr, "attachment")] == [300]  # the featured image only
    assert next(i for i in wxr.items if i.post_id == 100).comments == 0
    assert "comments and menus: only an Everything export carries them" in report.left_out
    assert Scope("category", category=6, category_name="Local").words() == (
        "posts in the category Local"
    )


def test_a_date_export_asks_for_the_range_and_takes_its_files(tmp_path) -> None:
    api = ExportApi()
    path = tmp_path / "dates.xml"
    scope = Scope("dates", after="2026-02-01", before="2026-03-31")
    export_wxr(api, path, scope)
    wxr = read_wxr(path.read_bytes())
    posts = [p for r, p in api.asked if r == "wp/v2/posts"]
    assert posts[0]["after"] == "2026-02-01T00:00:00"
    assert posts[0]["before"] == "2026-03-31T23:59:59"
    assert {i.post_id for i in wxr.items if i.post_type != "attachment"} == {101, 200, 201}
    assert [i.post_id for i in _items(wxr, "attachment")] == [301]  # attached to post 101
    assert {a.login for a in wxr.authors} == {"ann", "bob"}
    assert scope.words() == "posts and pages from 2026-02-01 to 2026-03-31"


def test_an_unreadable_route_is_named_as_left_out(tmp_path) -> None:
    class NoMedia(ExportApi):
        def iter_collection(self, route: str, params: Any = None, **kw: Any) -> Iterator[Any]:
            if route == "wp/v2/media":
                raise WordPressApiError("Sorry, you are not allowed to do that.")
            yield from super().iter_collection(route, params, **kw)

    path = tmp_path / "site.xml"
    report = export_wxr(NoMedia(), path)
    assert "media files: the account may not read them" in report.left_out
    assert "media files: read in their public form only, without private details" in (
        report.left_out
    )
    assert validate_wxr(path)[0]


# -- validate and refuse -------------------------------------------------------------------


def _wxr(items: str, version: str = "1.2") -> bytes:
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<rss version="2.0" xmlns:wp="http://wordpress.org/export/1.2/" '
        'xmlns:content="http://purl.org/rss/1.0/modules/content/" '
        'xmlns:excerpt="http://wordpress.org/export/1.2/excerpt/" '
        'xmlns:dc="http://purl.org/dc/elements/1.1/">\n'
        f"<channel><title>Old Radio</title><link>{OLD}</link>"
        f"<wp:wxr_version>{version}</wp:wxr_version>"
        f"<wp:base_site_url>{OLD}</wp:base_site_url><wp:base_blog_url>{OLD}</wp:base_blog_url>"
        f"{items}</channel></rss>\n"
    ).encode()


def test_validate_wxr_names_what_is_wrong(tmp_path) -> None:
    good = tmp_path / "good.xml"
    good.write_bytes(
        _wxr("<item><wp:post_id>1</wp:post_id><wp:post_type>post</wp:post_type></item>")
    )
    assert validate_wxr(good) == (True, "good.xml is a well-formed WXR 1.2 file with 1 items.")
    old = tmp_path / "old.xml"
    old.write_bytes(_wxr("", version="1.1"))
    assert validate_wxr(old) == (False, "old.xml does not say it is WXR version 1.2.")
    holes = tmp_path / "holes.xml"
    holes.write_bytes(_wxr("<item><title>x</title></item><item><wp:post_id>2</wp:post_id></item>"))
    assert validate_wxr(holes) == (False, "2 items in holes.xml have no post type or number.")
    broken = tmp_path / "broken.xml"
    broken.write_bytes(b"<rss><channel>")
    good_flag, said = validate_wxr(broken)
    assert not good_flag and said.startswith("broken.xml is not a readable XML file")


def test_entity_declarations_are_refused_not_expanded() -> None:
    bomb = (
        b'<?xml version="1.0"?>\n<!DOCTYPE rss [<!ENTITY a "aaaaaaaaaa">'
        b'<!ENTITY b "&a;&a;&a;&a;&a;">]>\n<rss><channel><title>&b;</title></channel></rss>'
    )
    with pytest.raises(WxrError) as caught:
        read_wxr(bomb, "bomb.xml")
    assert str(caught.value.args[0]).startswith("bomb.xml is not a readable XML file")


def test_an_oversize_file_is_refused_before_parsing(monkeypatch) -> None:
    monkeypatch.setattr(wxr_read, "MAX_FILE_BYTES", 2 * 2**20)
    with pytest.raises(WxrError) as caught:
        read_wxr(b" " * (2 * 2**20 + 1), "huge.xml")
    assert caught.value.args[0].startswith("huge.xml is larger than 2 MB")


def test_a_file_that_is_not_rss_or_has_no_version_is_refused() -> None:
    with pytest.raises(WxrError, match="has no rss channel") as caught:
        read_wxr(b"<feed><channel/></feed>", "atom.xml")
    assert caught.value.plain == (  # the sentence alone, for speaking
        "atom.xml has no rss channel, so it is not a WordPress export file."
    )
    with pytest.raises(WxrError, match="does not say which WXR version"):
        read_wxr(b"<rss><channel><title>x</title></channel></rss>", "plain.xml")


def test_items_past_the_cap_are_counted_not_dropped(monkeypatch) -> None:
    monkeypatch.setattr(wxr_read, "MAX_ITEMS", 2)
    item = "<item><wp:post_id>{0}</wp:post_id><wp:post_type>post</wp:post_type></item>"
    wxr = read_wxr(_wxr("".join(item.format(n) for n in range(5))))
    assert [i.post_id for i in wxr.items] == [0, 1] and wxr.beyond_cap == 3


# -- import ---------------------------------------------------------------------------------

_POST = (
    "<item><title>{title}</title><link>{link}</link><dc:creator>{creator}</dc:creator>"
    "<content:encoded><![CDATA[{content}]]></content:encoded>"
    "<excerpt:encoded><![CDATA[]]></excerpt:encoded>"
    "<wp:post_id>{ident}</wp:post_id><wp:post_date>2026-01-10 08:00:00</wp:post_date>"
    "<wp:post_name>{slug}</wp:post_name><wp:status>{status}</wp:status>"
    "<wp:post_parent>{parent}</wp:post_parent><wp:menu_order>0</wp:menu_order>"
    "<wp:post_type>{kind}</wp:post_type>{extra}</item>"
)


def _item(ident: int, kind: str, title: str, **kw: Any) -> str:
    values = {
        "title": title,
        "link": f"{OLD}/{title.lower()}/",
        "creator": "ann",
        "content": "",
        "ident": ident,
        "slug": title.lower(),
        "status": "publish",
        "parent": 0,
        "kind": kind,
        "extra": "",
    }
    values.update(kw)
    return _POST.format(**values)


_PIC = f"{OLD}/wp-content/uploads/pic.jpg"
_MORNING = (
    f'<!-- wp:image {{"id":300}} --><img src="{OLD}/wp-content/uploads/pic-300x200.jpg" '
    'class="wp-image-300"/><!-- /wp:image -->'
    f'<p><a href="{OLD}/about/">About</a></p>'
)
IMPORT_FILE = _wxr(
    "<wp:author><wp:author_login>ann</wp:author_login>"
    "<wp:author_email>ann@old.example</wp:author_email></wp:author>"
    "<wp:author><wp:author_login>bob</wp:author_login>"
    "<wp:author_email>bob@old.example</wp:author_email></wp:author>"
    "<wp:author><wp:author_login>dave</wp:author_login>"
    "<wp:author_email>dave@old.example</wp:author_email></wp:author>"
    "<wp:category><wp:category_nicename>news</wp:category_nicename>"
    "<wp:cat_name>News</wp:cat_name></wp:category>"
    "<wp:category><wp:category_nicename>local</wp:category_nicename>"
    "<wp:category_parent>news</wp:category_parent><wp:cat_name>Local</wp:cat_name></wp:category>"
    "<wp:term><wp:term_taxonomy>genre</wp:term_taxonomy><wp:term_slug>jazz</wp:term_slug>"
    "<wp:term_name>Jazz</wp:term_name></wp:term>"
    + _item(
        100,
        "post",
        "Morning",
        content=_MORNING,
        extra=(
            '<category domain="category" nicename="local"><![CDATA[Local]]></category>'
            '<category domain="post_tag" nicename="live"><![CDATA[Live]]></category>'
            "<wp:postmeta><wp:meta_key>_thumbnail_id</wp:meta_key>"
            "<wp:meta_value>300</wp:meta_value></wp:postmeta>"
            "<wp:comment><wp:comment_id>1</wp:comment_id></wp:comment>"
        ),
    )
    + _item(200, "page", "About", creator="bob")
    + _item(201, "page", "Team", creator="dave", status="draft", parent=200)
    + _item(400, "event", "Gig")
    + _item(500, "nav_menu_item", "Home")
    + _item(102, "post", "Gone", status="trash")
    + _item(
        300,
        "attachment",
        "Pic",
        status="inherit",
        extra=(
            f"<wp:attachment_url>{_PIC}</wp:attachment_url>"
            "<wp:postmeta><wp:meta_key>_wp_attachment_image_alt</wp:meta_key>"
            "<wp:meta_value>A microphone</wp:meta_value></wp:postmeta>"
        ),
    ),
    version="1.2",
)


class _Got:
    filename = "pic.jpg"
    content = b"jpeg"
    content_type = "image/jpeg"


class ImportApi:
    """This site: Ann by login, Carol is Bob by email, a News category, no genres or events."""

    def __init__(self) -> None:
        self.writes: list[tuple[str, str, Any]] = []
        self.next_id = 1000

    def get(self, route: str, **_params: Any) -> Any:
        if route == "wp/v2/users/me":
            return {"id": 7, "name": "Ann Here"}
        if route == "wp/v2/taxonomies":
            return {"category": {"rest_base": "categories"}, "post_tag": {"rest_base": "tags"}}
        if route == "wp/v2/types":
            return {
                "post": {"rest_base": "posts"},
                "page": {"rest_base": "pages"},
                "attachment": {"rest_base": "media"},
            }
        return None

    def iter_collection(self, route: str, params: Any = None, **_kw: Any) -> Iterator[Any]:
        if route == "wp/v2/users":
            yield {"id": 7, "username": "ann", "name": "Ann Here"}
            yield {"id": 8, "username": "carol", "email": "BOB@old.example", "name": "Carol"}
        elif route == "wp/v2/categories":
            yield {"id": 50, "slug": "news"}

    def post(self, route: str, body: Any = None, **_params: Any) -> Any:
        self.writes.append(("POST", route, body))
        if route in ("wp/v2/posts", "wp/v2/pages", "wp/v2/categories", "wp/v2/tags"):
            self.next_id += 1
            return {"id": self.next_id, "link": f"{NEW}/?p={self.next_id}"}
        return {}

    def upload(self, route: str, filename: str, content: bytes, content_type: str) -> Any:
        self.writes.append(("UPLOAD", route, filename))
        return {"id": 900, "source_url": f"{NEW}/wp-content/uploads/pic.jpg"}

    def delete(self, route: str, **params: Any) -> Any:
        self.writes.append(("DELETE", route, params))
        return {}


def _plan() -> tuple[ImportApi, Any]:
    api = ImportApi()
    return api, plan_import(api, read_wxr(IMPORT_FILE, "old.xml"))


def test_plan_import_matches_people_and_terms_and_names_what_it_leaves(tmp_path) -> None:
    _api, plan = _plan()
    assert plan.authors == {"ann": 7, "bob": 8} and plan.unmatched == ["dave"]
    assert plan.fallback == 7
    assert plan.term_ids[("category", "news")] == 50
    assert [(t.taxonomy, t.slug) for t in plan.create_terms] == [
        ("post_tag", "live"),
        ("category", "local"),  # a child after the terms with no parent
    ]
    assert [i.post_id for i in plan.items] == [100, 200, 201]
    assert [a.post_id for a in plan.attachments] == [300] and plan.hosts == ["old.example"]
    left = "\n".join(plan.left_out)
    assert "1 event items: a type this site does not have" in left
    assert "1 nav_menu_item items: menus are rebuilt in Appearance, Menus" in left
    assert "1 post (trash) items: trashed and automatic drafts are not imported" in left
    assert "1 terms of genre, a taxonomy this site does not have" in left
    assert "1 comments: QUILL imports writing, not conversations" in left
    lines = plan.lines()
    assert lines[1].startswith("Everything is made as a draft; nothing is published.")
    assert "Author bob is Carol here." in lines
    assert "Author dave is not on this site; given to Ann Here." in lines
    assert "New category: Local." in lines and "Page: Team." in lines


def test_send_import_makes_only_drafts_rewrites_files_and_links_and_undo_trashes() -> None:
    api, plan = _plan()
    result = send_import(api, plan, here=NEW, fetch=lambda _address: _Got())
    made = [(r, b) for _m, r, b in api.writes if r in ("wp/v2/posts", "wp/v2/pages")]
    assert [b["title"] for _r, b in made] == ["Morning", "About", "Team"]
    assert {b["status"] for _r, b in made} == {"draft"}
    morning, about, team = (b for _r, b in made)
    assert morning["date"] == "2026-01-10T08:00:00" and morning["featured_media"] == 900
    assert sorted(morning["categories"]) == [1002] and morning["tags"] == [1001]
    assert morning["author"] == 7 and about["author"] == 8 and team["author"] == 7
    assert f'src="{NEW}/wp-content/uploads/pic.jpg"' in morning["content"]
    assert 'class="wp-image-900"' in morning["content"] and '{"id":900}' in morning["content"]
    assert OLD not in morning["content"]
    uploads = [w for w in api.writes if w[0] == "UPLOAD"]
    assert uploads == [("UPLOAD", "wp/v2/media", "pic.jpg")]
    assert ("POST", "wp/v2/media/900", {"title": "Pic", "alt_text": "A microphone"}) in api.writes
    about_id = 1004
    second = {r: b for _m, r, b in api.writes if r.startswith(("wp/v2/posts/", "wp/v2/pages/"))}
    assert second["wp/v2/pages/1005"] == {"parent": about_id}  # Team under About
    assert f'href="{NEW}/?p={about_id}"' in second["wp/v2/posts/1003"]["content"]
    assert result.count == 3 and result.uploaded == 1 and result.terms == 2
    assert "Made post Morning as a draft, number 1003." in result.lines
    assert "Left out:" in result.lines
    said = undo_import(api, result)
    trashed = [r for m, r, _p in api.writes if m == "DELETE"]
    assert trashed == ["wp/v2/pages/1005", "wp/v2/pages/1004", "wp/v2/posts/1003"]
    assert said == (
        "Moved 3 imported drafts to the Trash. The 1 uploaded files and 2 new terms stay; "
        "remove them from Media and the term lists if you do not want them."
    )


def test_skipped_files_keep_pointing_at_the_old_site() -> None:
    api, plan = _plan()
    send_import(api, plan, here=NEW, fetch=None)
    assert not [w for w in api.writes if w[0] == "UPLOAD"]
    morning = next(b for _m, r, b in api.writes if r == "wp/v2/posts")
    assert "featured_media" not in morning
    # the picture is not on this site, so its address must still be the old one
    assert f'src="{OLD}/wp-content/uploads/pic-300x200.jpg"' in morning["content"]
    relinked = next(b for _m, r, b in api.writes if r == "wp/v2/posts/1003")
    assert f'href="{NEW}/?p=1004"' in relinked["content"]  # links between items still move
    assert any("files, skipped as you chose" in line for line in plan.left_out)


def test_a_file_that_fails_to_download_is_one_line_and_keeps_its_old_address() -> None:
    def fetch(_address: str) -> Any:
        raise OSError("timed out")

    api, plan = _plan()
    result = send_import(api, plan, here=NEW, fetch=fetch)
    assert f"Not uploaded: {_PIC}: timed out" in result.lines and result.uploaded == 0
    morning = next(b for _m, r, b in api.writes if r == "wp/v2/posts")
    assert f'src="{OLD}/wp-content/uploads/pic-300x200.jpg"' in morning["content"]


def test_one_failed_draft_is_one_line_and_undo_says_what_it_could_not_move() -> None:
    class Refusing(ImportApi):
        def post(self, route: str, body: Any = None, **params: Any) -> Any:
            if route == "wp/v2/pages" and body["title"] == "About":
                raise WordPressApiError("Sorry, you are not allowed to create pages.")
            return super().post(route, body, **params)

        def delete(self, route: str, **params: Any) -> Any:
            raise WordPressApiError("Gone already.")

    api = Refusing()
    plan = plan_import(api, read_wxr(IMPORT_FILE))
    result = send_import(api, plan, here=NEW)
    assert "Not made: About: Sorry, you are not allowed to create pages." in result.lines
    assert result.count == 2
    said = undo_import(api, result)
    assert said.startswith("Moved 0 imported drafts to the Trash. Not moved: Team (Gone already.)")
