"""Replace File's three paths, without a site (quill.core.wordpress.media_replace)."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from quill.core.wordpress import media_replace as mr
from quill.core.wordpress.api import WordPressApiError

SITE = "Community Radio"
OLD = "https://radio.example/wp-content/uploads/2026/11/mic.jpg"
NEW = "https://radio.example/wp-content/uploads/2026/11/mic-new.jpg"


# -- which path ------------------------------------------------------------------------


def test_replace_route_takes_only_a_plugin_route_shaped_for_replacing_that_takes_post() -> None:
    routes = {
        "/wp/v2/media/(?P<id>[\\d]+)": {"methods": ["GET", "POST"]},
        "/wp/v2/media/(?P<id>[\\d]+)/replace": {"methods": ["POST"]},  # core has none
        "/emr/v1/media/(?P<id>\\d+)/replace": {"methods": ["POST"]},
    }
    assert mr.replace_route(routes, 42) == "emr/v1/media/42/replace"
    assert mr.replace_route({"/swap/v1/replace-media/(?P<id>\\d+)": {}}, 7) == (
        "swap/v1/replace-media/7"
    )
    assert mr.replace_route({"/emr/v1/media/(?P<id>\\d+)/replace": {"methods": ["GET"]}}, 1) == ""
    assert mr.replace_route({"/wp/v2/media/(?P<id>\\d+)/replace": {"methods": ["POST"]}}, 1) == ""
    assert mr.replace_route({"/emr/v1/media/(?P<id>\\d+)": {"methods": ["POST"]}}, 1) == ""


def test_emr_active_needs_the_plugin_and_active() -> None:
    assert mr.emr_active([{"plugin": mr.EMR_PLUGIN, "status": "active"}])
    assert not mr.emr_active([{"plugin": mr.EMR_PLUGIN, "status": "inactive"}])
    assert not mr.emr_active([{"plugin": "akismet/akismet", "status": "active"}])
    assert not mr.emr_active([])
    assert mr.emr_screen("https://radio.example/", 42) == (
        "https://radio.example/wp-admin/post.php?post=42&action=edit"
    )


def test_file_facts_and_the_preview_say_the_address_and_any_type_change() -> None:
    old = mr.file_facts({
        "source_url": OLD,
        "mime_type": "image/jpeg",
        "media_details": {"filesize": 2048},
    })
    assert old == mr.FileFacts("mic.jpg", 2048, "image/jpeg")
    assert old.words() == "mic.jpg, 2 KB, image/jpeg"
    bare = mr.file_facts({"title": {"rendered": "Mic"}})
    assert bare.words() == "Mic, size not given, type not given"
    new = mr.FileFacts("mic.png", 10, "image/png")
    kept = mr.preview_lines(old, new, OLD, in_place=True)
    assert kept[:3] == [
        "Now: mic.jpg, 2 KB, image/jpeg.",
        "New: mic.png, 10 bytes, image/png.",
        f"The address stays the same: {OLD}",
    ]
    assert kept[-1] == "The type changes from image/jpeg to image/png."
    moved = mr.preview_lines(old, mr.FileFacts("a.jpg", 1, "image/jpeg"), OLD, in_place=False)
    assert moved[2].startswith(f"The address changes. The old one is {OLD};")
    assert len(moved) == 3  # no type change line


# -- rewriting uses ----------------------------------------------------------------------


def test_rewrite_uses_moves_the_address_its_sizes_and_escaped_form() -> None:
    sized = OLD.replace(".jpg", "-300x200.jpg")
    scaled = OLD.replace(".jpg", "-scaled.jpg")
    escaped = OLD.replace("/", "\\/")
    text = f'<img src="{sized}"> <a href="{OLD}">full</a> {scaled} {escaped} mic-other.jpg'
    new_escaped = NEW.replace("/", "\\/")
    out = mr.rewrite_uses(text, 5, OLD, 9, NEW)
    assert out == f'<img src="{NEW}"> <a href="{NEW}">full</a> {NEW} {new_escaped} mic-other.jpg'
    other = OLD.replace("mic.jpg", "mic-other.jpg")
    assert mr.rewrite_uses(other, 5, OLD, 9, NEW) == other  # a different file is left alone


def test_rewrite_uses_moves_the_block_id_and_the_image_class_and_no_other_number() -> None:
    text = (
        '<!-- wp:image {"id":5,"sizeSlug":"large"} --><img class="wp-image-5"/>'
        '<!-- wp:media-text {"mediaId":5} --><!-- wp:cover {"url":"x","id":5} -->'
        '<img class="wp-image-50"/><!-- wp:image {"id":55} --><!-- wp:query {"id":5} -->'
    )
    out = mr.rewrite_uses(text, 5, "", 9, "")
    assert out == (
        '<!-- wp:image {"id":9,"sizeSlug":"large"} --><img class="wp-image-9"/>'
        '<!-- wp:media-text {"mediaId":9} --><!-- wp:cover {"url":"x","id":9} -->'
        '<img class="wp-image-50"/><!-- wp:image {"id":55} --><!-- wp:query {"id":5} -->'
    )
    assert mr.rewrite_uses("", 5, OLD, 9, NEW) == ""


class ScanApi:
    """Posts, pages and patterns; one list can be refused."""

    def __init__(self, *, refuse: str = "") -> None:
        self.refuse = refuse
        self.asked: list[tuple[str, dict[str, Any]]] = []
        self.rows = {
            "wp/v2/posts": [
                {
                    "id": 1,
                    "type": "post",
                    "title": {"raw": "Show"},
                    "content": {"raw": f'<!-- wp:image {{"id":5}} --><img src="{OLD}"/>'},
                    "featured_media": 0,
                    "modified_gmt": "2026-11-01T10:00:00",
                },
                {
                    "id": 2,
                    "type": "post",
                    "title": {"raw": "Unrelated"},
                    "content": {"raw": "<p>No pictures</p>"},
                    "featured_media": 6,
                    "meta": {"hero_id": 5, "flag": True},
                },
            ],
            "wp/v2/pages": [
                {
                    "id": 3,
                    "type": "page",
                    "title": {"raw": "About"},
                    "content": {"raw": "<p>About</p>"},
                    "featured_media": 5,
                    "modified_gmt": "2026-11-02T10:00:00",
                }
            ],
            "wp/v2/blocks": [
                {
                    "id": 4,
                    "type": "wp_block",
                    "title": {"raw": "Banner"},
                    "content": {"raw": ""},
                    "meta": {"banner_url": f"see {OLD}"},
                    "modified_gmt": "2026-11-03T10:00:00",
                }
            ],
        }

    def iter_collection(self, route: str, params: Any = None, **_kw: Any) -> Iterator[Any]:
        self.asked.append((route, dict(params or {})))
        if route == self.refuse:
            raise WordPressApiError("Sorry, you are not allowed to list these.")
        yield from (dict(r) for r in self.rows.get(route, []))


def _old() -> dict[str, Any]:
    return {"id": 5, "source_url": OLD}


def test_plan_repoint_finds_text_featured_images_and_fields_and_names_numbers() -> None:
    api = ScanApi()
    plan = mr.plan_repoint(api, SITE, _old())
    assert [r["id"] for r in plan.items] == [1, 3, 4]
    assert [r for r, _p in api.asked] == ["wp/v2/posts", "wp/v2/pages", "wp/v2/blocks"]
    assert api.asked[0][1]["status"] == "publish,future,draft,pending,private"
    assert plan.lines() == [
        "Post Show: its text",
        "Page About: its featured image",
        "Pattern Banner: the custom field banner_url",
        "Not changed: Unrelated: the custom field hero_id holds 5, which may be this file's "
        "number; QUILL leaves numbers alone",
    ]
    assert not plan.unread


def test_plan_repoint_names_a_list_it_could_not_read() -> None:
    plan = mr.plan_repoint(ScanApi(refuse="wp/v2/pages"), SITE, _old())
    assert [r["id"] for r in plan.items] == [1, 4]
    assert plan.unread == ["pages (Sorry, you are not allowed to list these.)"]
    assert plan.lines()[-1] == (
        "Not read, so not changed: pages (Sorry, you are not allowed to list these.)"
    )


def test_repoint_edits_are_conflict_checked_and_carry_what_was_there() -> None:
    plan = mr.plan_repoint(ScanApi(), SITE, _old())
    show, about, banner = mr.repoint_edits(plan, 9, NEW)
    assert show.route == "wp/v2/posts/1" and show.stamp_field == "modified_gmt"
    assert show.stamp == "2026-11-01T10:00:00"
    assert show.body["content"] == f'<!-- wp:image {{"id":9}} --><img src="{NEW}"/>'
    assert show.before["content"].startswith('<!-- wp:image {"id":5}')
    assert about.route == "wp/v2/pages/3"
    assert about.body == {"featured_media": 9} and about.before == {"featured_media": 5}
    assert banner.route == "wp/v2/blocks/4"
    assert banner.body == {"meta": {"banner_url": f"see {NEW}"}}
    assert banner.before == {"meta": {"banner_url": f"see {OLD}"}}
    assert show.line == f"{SITE}: Show: uses the new file"


def test_said_after_repoint_says_the_address_changed_and_what_breaks() -> None:
    assert mr.said_after_repoint(3, [], redirect="", old_kept=True) == (
        "The file's address changes; QUILL updated 3 places that used it. Links from other "
        "websites to the old address will break unless a redirect is added. The old file is "
        "still in the library."
    )
    said = mr.said_after_repoint(
        1, ["About: changed on the site"], redirect="A redirect now sends it.", old_kept=False
    )
    assert said == (
        "The file's address changes; QUILL updated 1 places that used it. 1 were not changed: "
        "About: changed on the site. A redirect now sends it. The old file was deleted."
    )


def test_redirect_for_is_a_301_from_the_old_path() -> None:
    body = mr.redirect_for(OLD, NEW, 4)
    assert body["url"] == "/wp-content/uploads/2026/11/mic.jpg"
    assert body["action_data"] == {"url": NEW} and body["action_code"] == 301
    assert body["group_id"] == 4
    assert body["title"] == "Made by QUILL when a media file was replaced"


# -- in place -----------------------------------------------------------------------------


class InPlaceApi:
    def __init__(self, after: str, mime: str = "image/jpeg", sizes_fail: bool = False) -> None:
        self.after = after
        self.mime = mime
        self.sizes_fail = sizes_fail
        self.calls: list[tuple[str, str, Any]] = []

    def upload(self, route: str, filename: str, content: bytes, content_type: str) -> Any:
        self.calls.append(("UPLOAD", route, (filename, content, content_type)))
        return {}

    def get(self, route: str, **params: Any) -> Any:
        self.calls.append(("GET", route, params))
        return {
            "source_url": self.after,
            "mime_type": self.mime,
            "media_details": {"filesize": 4096},
        }

    def post(self, route: str, body: Any = None, **_params: Any) -> Any:
        self.calls.append(("POST", route, body))
        if self.sizes_fail:
            raise WordPressApiError("The image could not be processed.")
        return {}


def test_replace_in_place_reads_back_and_remakes_sizes_when_the_address_stayed() -> None:
    api = InPlaceApi(OLD + "?ver=2")
    kept, said = mr.replace_in_place(
        api, "emr/v1/media/5/replace", 5, "mic.jpg", b"jpg", "image/jpeg", OLD
    )
    assert kept
    assert said == (
        f"Replaced. The address is the same, {OLD}, and the site now has mic.jpg?ver=2, 4 KB, "
        "image/jpeg. Its sizes were remade."
    )
    assert api.calls[0] == ("UPLOAD", "emr/v1/media/5/replace", ("mic.jpg", b"jpg", "image/jpeg"))
    assert api.calls[1] == ("GET", "wp/v2/media/5", {"context": "edit"})
    assert api.calls[2] == (
        "POST",
        "wp/v2/media/5/post-process",
        {"action": "create-image-subsizes"},
    )


def test_replace_in_place_says_when_the_address_did_not_stay() -> None:
    api = InPlaceApi(NEW)
    kept, said = mr.replace_in_place(api, "emr/v1/media/5/replace", 5, "m.jpg", b"", "", OLD)
    assert not kept
    assert said == (
        f"The site took the file, but its address is now {NEW}, not {OLD}. Links to the old "
        "address may break."
    )
    assert [c[0] for c in api.calls] == ["UPLOAD", "GET"]  # no sizes for a moved file


def test_replace_in_place_says_when_sizes_were_not_remade_and_skips_them_for_a_pdf() -> None:
    kept, said = mr.replace_in_place(
        InPlaceApi(OLD, sizes_fail=True), "r/v1/replace/5", 5, "m.jpg", b"", "", OLD
    )
    assert kept and said.endswith("Its sizes were not remade: The image could not be processed.")
    pdf = InPlaceApi(OLD, mime="application/pdf")
    kept, said = mr.replace_in_place(pdf, "r/v1/replace/5", 5, "m.pdf", b"", "", OLD)
    assert kept and "sizes" not in said and [c[0] for c in pdf.calls] == ["UPLOAD", "GET"]
