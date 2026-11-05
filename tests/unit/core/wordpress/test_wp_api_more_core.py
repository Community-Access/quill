"""The wx-free half of 9.15: site features, notes, custom fields, picture edits."""

from __future__ import annotations

import pytest

from quill.core.wordpress import block_notes as bn
from quill.core.wordpress import custom_fields as cf
from quill.core.wordpress import media_edit as me
from quill.core.wordpress import site_features as sf
from quill.core.wordpress.site import Account
from quill.core.wordpress.site_media import media_from_payload

EDITOR = Account(1, "Jeff", "jeff", ("editor",), frozenset({"edit_posts", "upload_files"}))
NOBODY = Account(2, "Sub", "sub", ("subscriber",), frozenset({"read"}))


def index(version: str = "6.9", routes: dict | None = None) -> sf.SiteIndex:
    return sf.SiteIndex(("wp/v2",), routes if routes is not None else {}, version)


# --------------------------------------------------------------------------- #
# site features


def test_versions_compare_and_unknown_is_not_ruled_out() -> None:
    assert sf.at_least("6.9", (6, 9)) and sf.at_least("7.1.2", (6, 9))
    assert not sf.at_least("6.8.3", (6, 9))
    assert sf.at_least("", (6, 9))


def test_notes_need_the_version_the_route_and_the_role() -> None:
    routes = {"/wp/v2/comments": {}}
    assert sf.unavailable("notes", index("6.9", routes), EDITOR, "Radio") == ""
    assert "6.9 or later, and Radio runs 6.8" in sf.unavailable(
        "notes", index("6.8", routes), EDITOR, "Radio"
    )
    assert "6.9" in sf.unavailable("notes", index("", routes), EDITOR, "Radio", known_version="6.7")
    assert "no notes to show" in sf.unavailable("notes", index("6.9", {}), EDITOR, "Radio")
    assert "a Subscriber, which cannot read or write notes" in sf.unavailable(
        "notes", index("6.9", routes), NOBODY, "Radio"
    )


def test_edit_route_and_its_modifiers() -> None:
    plain = index(routes={"/wp/v2/media/(?P<id>[\\d]+)/edit": {}})
    assert sf.unavailable("edit_picture", plain, EDITOR, "Radio") == ""
    assert plain.edit_modifiers() == ("rotate", "crop")
    listed = index(
        routes={
            "/wp/v2/media/(?P<id>[\\d]+)/edit": {
                "endpoints": [
                    {
                        "args": {
                            "modifiers": {
                                "items": {
                                    "oneOf": [
                                        {"properties": {"type": {"enum": ["rotate"]}}},
                                        {"properties": {"type": {"enum": ["flip"]}}},
                                    ]
                                }
                            }
                        }
                    }
                ]
            }
        }
    )
    assert listed.edit_modifiers() == ("rotate", "flip")
    assert "picture editing" in sf.unavailable("edit_picture", index(), EDITOR, "Radio")


def test_introspect_and_library_and_moderation_checks() -> None:
    route = "/wp/v2/users/(?P<user_id>(?:[\\d]+|me))/application-passwords/introspect"
    assert sf.unavailable("which_password", index(routes={route: {}}), NOBODY, "Radio") == ""
    assert "5.9" in sf.unavailable("which_password", index(), EDITOR, "Radio")
    assert "Media Library" in sf.unavailable("library_alt", index(), EDITOR, "Radio")
    assert "moderate comments" in sf.unavailable("bulk_moderation", index(), EDITOR, "Radio")


class _Api:
    def __init__(self, answer: object) -> None:
        self.answer = answer

    def get(self, route: str, **_params: object) -> object:
        if isinstance(self.answer, BaseException):
            raise self.answer
        return self.answer


def test_read_index_keeps_routes_and_version() -> None:
    found = sf.read_index(
        _Api({"namespaces": ["wp/v2"], "routes": {"/batch/v1": {}}, "generator": "x?v=6.9.1"})
    )  # type: ignore[arg-type]
    assert found.wp_version == "6.9.1" and found.supports("batch/v1")
    with pytest.raises(sf.WordPressApiError):
        sf.read_index(_Api([]))  # type: ignore[arg-type]


def test_which_password_and_its_sentence() -> None:
    from quill.core.wordpress.api import WordPressApiError

    found = sf.which_password(_Api({"uuid": "u", "name": "QUILL"}))  # type: ignore[arg-type]
    assert found is not None and found.name == "QUILL"
    assert sf.which_password(_Api({})) is None  # type: ignore[arg-type]
    gone = WordPressApiError("x", status=404)
    assert sf.which_password(_Api(gone)) is None  # type: ignore[arg-type]
    with pytest.raises(WordPressApiError):
        sf.which_password(_Api(WordPressApiError("x", status=500)))  # type: ignore[arg-type]
    assert "with no name" in sf.password_sentence("Radio", sf.AppPassword("u", "", "", ""))


# --------------------------------------------------------------------------- #
# notes


def _note(i: int, parent: int = 0, **extra: object) -> bn.Note:
    fields: dict = {"author_name": "Sam", "date_gmt": f"2026-11-0{i}", "content": f"n{i}"}
    fields.update(extra)
    return bn.Note(i, parent, status=str(fields.pop("status", "approve")), **fields)


def test_threads_group_replies_under_their_top_note() -> None:
    found = bn.threads([_note(1), _note(2, 1), _note(3, 2), _note(4)])
    assert [t.root.id for t in found] == [1, 4]
    assert [r.id for r in found[0].replies] == [2, 3]


def test_resolved_follows_the_latest_marker_then_the_status() -> None:
    thread = bn.Thread(_note(1))
    assert not thread.resolved
    thread.root = _note(1, status="hold")
    assert thread.resolved
    thread.replies.append(_note(2, 1, content="", marker="reopen"))
    assert not thread.resolved
    assert "reopened it" in thread.details()
    assert thread.spoken() == "Sam on a block not in your copy: n1"


def test_payload_reads_the_marker_meta() -> None:
    note = bn.note_from_payload({
        "id": 5,
        "content": {"raw": ""},
        "meta": {"_wp_note_status": "resolved"},
    })
    assert note.marker == "resolved" and note.author_name == "Someone"


def test_locate_reads_the_note_id_in_markdown_islands() -> None:
    islands = {
        "island-1": (
            '<!-- wp:paragraph {"metadata":{"blockCommentId":12}} -->\n<p>Hi</p>\n'
            "<!-- /wp:paragraph -->"
        )
    }
    text = "Welcome.\n\n## Times\n\n::: block core/paragraph island-1\n"
    thread = bn.Thread(_note(12))
    bn.locate(text, "markdown", [thread], islands)
    assert thread.place == "the second paragraph"
    assert thread.span is not None


def test_ordinals() -> None:
    assert bn.ordinal(3) == "third" and bn.ordinal(14) == "number 14"


# --------------------------------------------------------------------------- #
# custom fields


SCHEMA = {
    "seo_title": {"type": "string", "title": "SEO title"},
    "long_note": {"type": "string"},
    "count": {"type": ["integer", "null"]},
    "price": {"type": "number"},
    "mood": {"type": "string", "enum": ["calm", "busy"]},
    "footnotes": {"type": "string"},
    "list": {"type": "array"},
}


def test_form_from_schema_with_kept_values_winning() -> None:
    form = cf.build_form(
        SCHEMA, {"seo_title": "Old", "long_note": "x" * 90, "count": 2}, {"seo_title": "Kept"}
    )
    kinds = {f.key: f.kind for f in form.fields}
    assert kinds == {
        "seo_title": "text",
        "long_note": "multiline",
        "count": "text",
        "price": "text",
        "mood": "choice",
    }
    assert form.fields[0].value == "Kept" and form.left_alone == 1
    assert len({f.label.lower().split("&")[1][0] for f in form.fields}) == len(form.fields)


def test_changes_type_numbers_and_skip_the_unchanged() -> None:
    form = cf.build_form(SCHEMA, {"seo_title": "Old", "count": 2, "price": 1.5}, {})
    answers = {"seo_title": "Old", "count": "3", "price": "", "mood": "busy", "long_note": ""}
    assert cf.changes(form, answers) == {"count": 3, "price": None, "mood": "busy"}
    with pytest.raises(cf.FieldValueError, match="Price"):
        cf.changes(form, {"price": "lots"})


# --------------------------------------------------------------------------- #
# pictures


def test_centred_crops() -> None:
    assert me.centred_crop(1600, 1200, 1, 1) == {
        "left": 12.5,
        "top": 0.0,
        "width": 75.0,
        "height": 100.0,
    }
    tall = me.centred_crop(1000, 1000, 16, 9)
    assert tall["left"] == 0.0 and tall["height"] == 56.25 and tall["top"] == 21.875
    assert me.centred_crop(0, 10, 1, 1)["width"] == 100.0


def test_edits_offered_and_their_result_sizes() -> None:
    item = media_from_payload({"id": 1, "media_details": {"width": 1600, "height": 1200}})
    no_size = media_from_payload({"id": 2})
    assert [e.needs for e in me.offered(["rotate"], item)] == ["rotate"] * 3
    assert all(e.needs != "crop" for e in me.offered(["crop", "rotate"], no_size))
    turn, square = me.EDITS[0], me.EDITS[5]
    assert me.result_size(turn, 1600, 1200) == (1200, 1600)
    assert me.result_size(square, 1600, 1200) == (1200, 1200)
    flip = me.EDITS[3].modifiers(1, 1)
    assert flip == [{"type": "flip", "args": {"flip": {"horizontal": True, "vertical": False}}}]


def test_save_alt_texts_falls_back_when_the_batch_answers_nothing() -> None:
    sent: list[str] = []

    class Api:
        def batch(self, _requests: list) -> list:
            return []

        def post(self, route: str, _body: object) -> None:
            sent.append(route)

    saved = me.save_alt_texts(Api(), {3: "a", 1: "b"}, can_batch=True)  # type: ignore[arg-type]
    assert saved == [1, 3] and sent == ["wp/v2/media/1", "wp/v2/media/3"]
    assert me.save_alt_texts(Api(), {}, can_batch=True) == []  # type: ignore[arg-type]
