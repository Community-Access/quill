"""Importing and exporting List Speech Templates, and the WordPress media and users lists."""

from __future__ import annotations

import json
from types import SimpleNamespace

from quill.core.list_speech import exchange as ex
from quill.core.list_speech import library as lib
from quill.core.list_speech.speak import speak_row
from quill.core.list_speech.template import Template


def _t(name: str, list_type: str = "github_issues", fields=("number", "title")) -> Template:
    return Template(list_type, name, tuple(fields), ", ", False, True, "")


def _library(*templates: Template) -> lib.Library:
    out = lib.Library()
    for template in templates:
        out = lib.add_template(out, template)
    return out


def test_export_then_import_round_trips() -> None:
    library = _library(_t("Mine"), _t("Quick", "wordpress_users", ("name", "role")))
    incoming = ex.read_import(ex.export_templates(library))
    assert not incoming.error and not incoming.notes
    assert {t.name for t in incoming.templates} == {"Mine", "Quick"}


def test_export_leaves_out_which_list_uses_what() -> None:
    library = lib.assign(_library(_t("Mine")), "github_issues", "user:Mine")
    assert "assignments" not in json.loads(ex.export_templates(library))


def test_not_a_template_file_changes_nothing_and_says_so() -> None:
    for text in ("not json", "[]", '{"templates": 3}', '{"format": "other", "templates": []}'):
        assert ex.read_import(text).error == "That file is not a List Speech Templates file."


def test_newer_file_is_refused_and_older_one_is_read() -> None:
    newer = ex.read_import('{"version": 99, "templates": []}')
    assert "newer QUILL" in newer.error
    body = [{"name": "Old", "list_type": "github_issues", "fields": ["title"]}]
    older = ex.read_import(json.dumps({"templates": body}))
    assert not older.error and older.templates[0].name == "Old"
    assert older.notes == ("That file has no version, so it was read as an older export.",)


def test_skipped_templates_are_counted_in_plain_words() -> None:
    body = [
        {"name": "Ok", "list_type": "github_issues", "fields": ["title"]},
        {"name": "Ok", "list_type": "github_issues", "fields": ["title"]},
        {"name": "Brief", "list_type": "github_issues", "fields": ["title"]},
        {"name": "Far", "list_type": "no_such_list", "fields": ["title"]},
        {"list_type": "github_issues"},
        "junk",
    ]
    incoming = ex.read_import(json.dumps({"version": 1, "templates": body}))
    assert [t.name for t in incoming.templates] == ["Ok"]
    text = " ".join(incoming.notes)
    assert "2 templates had no name or list" in text
    assert "does not have and was skipped" in text
    assert "built-in" in text and "repeated" in text


def test_file_with_nothing_usable_is_an_error() -> None:
    incoming = ex.read_import('{"version": 1, "templates": []}')
    assert incoming.error == "That file has no templates to import."


def test_a_saved_name_is_replaced_only_when_asked() -> None:
    saved = _library(_t("Mine", fields=("title",)))
    new = _t("mine", fields=("number", "title", "state"))
    assert ex.conflicts(saved, [new]) == (new,)
    kept, message = ex.apply_import(saved, [new])
    assert (
        kept.templates[0].fields == ("title",)
        and message == "Nothing was imported. 1 kept as it was."
    )
    replaced, message = ex.apply_import(saved, [new], frozenset({ex.template_key(new)}))
    assert replaced.templates[0].fields == ("number", "title", "state")
    assert message == "Imported: 1 replaced."


def test_new_names_are_added() -> None:
    library, message = ex.apply_import(lib.Library(), [_t("A"), _t("B")])
    assert len(library.templates) == 2 and message == "Imported: 2 added."


def test_wordpress_media_and_users_are_spoken_under_a_template() -> None:
    media = SimpleNamespace(
        kind="media",
        subkind="picture",
        cells={"title": "Team photo", "type": "picture", "alt_text": "none", "uploaded": "today"},
    )
    user = SimpleNamespace(
        kind="user",
        subkind="user",
        cells={"name": "Pat", "username": "pat", "role": "Editor", "email": "p@x.org"},
    )
    library = lib.assign(lib.Library(), "wordpress_media", "builtin:brief")
    library = lib.assign(library, "wordpress_users", "builtin:detailed")
    assert speak_row(media, library) == "Team photo, picture"
    assert speak_row(user, library) == "Pat, username pat, Editor, email p@x.org"
    assert speak_row(media, lib.Library()) is None


def test_a_version_that_makes_no_sense_is_refused() -> None:
    for version in ('"2"', "0", "true", "1.5"):
        text = f'{{"version": {version}, "templates": []}}'
        assert "does not understand" in ex.read_import(text).error


def _work_row(source: str = "Review requested"):
    from quill.core.github.explore_models import _issue_row

    raw = SimpleNamespace(
        repository=SimpleNamespace(full_name="Community-Access/quill"),
        number=7,
        title="Fix the thing",
        html_url="https://github.com/Community-Access/quill/pull/7",
        pull_request=object(),
        state="open",
        updated_at="2026-11-27",
    )
    return _issue_row(raw, source)


def test_assigned_and_review_requested_rows_speak_under_a_template() -> None:
    row = _work_row()
    assert speak_row(row, lib.Library()) is None  # usual wording by default
    brief = lib.assign(lib.Library(), "github_work", "builtin:brief")
    assert speak_row(row, brief) == "pull request, Fix the thing, review requested"
    detailed = lib.assign(lib.Library(), "github_work", "builtin:detailed")
    text = speak_row(row, detailed) or ""
    assert "in Community-Access/quill" in text and "number 7" in text


def test_a_row_found_two_ways_says_both_reasons() -> None:
    from dataclasses import replace

    from quill.core.github.explore import _why_added

    row = _work_row("Assigned")
    merged = replace(row, fields=_why_added(row.fields, "Review requested"))
    assert dict(merged.fields)["why"] == "review requested; assigned"
