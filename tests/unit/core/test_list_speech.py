"""List Speech Templates: the model, the renderer, the library and the file."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

import pytest

from quill.core.list_speech import library as lib
from quill.core.list_speech import store
from quill.core.list_speech.catalog import LIST_TYPES, get_list_type
from quill.core.list_speech.render import render_row
from quill.core.list_speech.row_fields import (
    explore_row_fields,
    github_item_fields,
    spoken_age,
    wordpress_row_fields,
)
from quill.core.list_speech.speak import speak_row
from quill.core.list_speech.template import (
    Template,
    from_preset,
    move_field,
    template_from_dict,
    template_to_dict,
    unavailable_fields,
)

ISSUES = get_list_type("github_issues")
assert ISSUES is not None
TODAY = date(2026, 11, 27)


def _t(**kw: object) -> Template:
    base: dict[str, object] = {
        "list_type": "github_issues",
        "name": "Mine",
        "fields": ("title", "state"),
    }
    base.update(kw)
    return Template(**base)  # type: ignore[arg-type]


def test_every_list_type_is_consistent() -> None:
    for kind in LIST_TYPES:
        ids = kind.field_ids()
        assert len(set(ids)) == len(ids)
        assert [p.id for p in kind.presets] == ["brief", "balanced", "detailed"]
        for preset in kind.presets:
            assert set(preset.fields) <= set(ids), (kind.id, preset.id)
        used = {f for p in kind.presets for f in p.fields} - {"date"}
        assert used <= set(kind.sample), kind.id


def test_render_orders_and_separates() -> None:
    template = _t(fields=("state", "title"), separator=" / ")
    out = render_row(template, ISSUES, {"title": "A", "state": "open"})
    assert out.text == "open / A"


def test_labels_only_where_a_field_has_one() -> None:
    row = {"author": "jeff", "state": "open"}
    out = render_row(_t(fields=("state", "author"), labels=True), ISSUES, row)
    assert out.text == "open, by jeff"


def test_empty_fields_are_omitted_by_default() -> None:
    template = _t(fields=("title", "labels", "state"))
    out = render_row(template, ISSUES, {"title": "A", "labels": "", "state": "open"})
    assert out.text == "A, open" and out.empty == ("labels",)


def test_empty_field_speaks_fallback_when_not_omitted() -> None:
    template = _t(fields=("title", "labels"), omit_empty=False, fallback="none", labels=True)
    out = render_row(template, ISSUES, {"title": "A", "labels": ""})
    assert out.text == "A, labels none"


def test_no_fallback_never_speaks_a_bare_label() -> None:
    template = _t(fields=("title", "labels"), omit_empty=False, labels=True)
    assert render_row(template, ISSUES, {"title": "A", "labels": ""}).text == "A"


def test_removed_field_is_reported_not_spoken() -> None:
    template = _t(fields=("title", "reactions", "state"))
    out = render_row(template, ISSUES, {"title": "A", "state": "open"})
    assert out.text == "A, open"
    assert out.unavailable == ("reactions",)
    assert unavailable_fields(template, ISSUES) == ("reactions",)


def test_field_missing_from_a_row_is_reported() -> None:
    out = render_row(_t(fields=("title", "assignees")), ISSUES, {"title": "A"})
    assert out.text == "A" and out.missing == ("assignees",)


def test_nothing_to_say_is_empty_text() -> None:
    assert render_row(_t(fields=()), ISSUES, {"title": "A"}).text == ""


def test_move_field() -> None:
    assert move_field(("a", "b", "c"), 1, -1) == (("b", "a", "c"), 0)
    assert move_field(("a", "b", "c"), 0, -1) == (("a", "b", "c"), 0)
    assert move_field(("a", "b", "c"), 2, 1) == (("a", "b", "c"), 2)
    assert move_field((), 0, 1) == ((), 0)


def test_dict_round_trip_and_coercion() -> None:
    template = _t(separator=" / ", labels=True, omit_empty=False, fallback="n/a")
    assert template_from_dict(template_to_dict(template)) == template
    bad = template_from_dict({
        "name": "X",
        "list_type": "github_issues",
        "fields": "nope",
        "labels": 3,
    })
    assert bad is not None and bad.fields == () and bad.labels is False and bad.omit_empty
    assert template_from_dict({"name": "", "list_type": "x"}) is None
    dup = template_from_dict({"name": "X", "list_type": "y", "fields": ["a", "a", 3, "b"]})
    assert dup is not None and dup.fields == ("a", "b")


def test_presets_become_templates() -> None:
    detailed = from_preset(ISSUES, ISSUES.presets[2])
    assert detailed.labels and detailed.fields[0] == "number"
    sample = render_row(detailed, ISSUES, ISSUES.sample).text
    assert "by octocat" in sample and "3 comments" in sample


def test_library_save_replace_rename_delete() -> None:
    library = lib.add_template(lib.Library(), _t(name="Quick"))
    library = lib.assign(library, "github_issues", "user:Quick")
    library = lib.rename_template(library, "github_issues", "Quick", "Fast")
    assert library.assignments["github_issues"] == "user:Fast"
    assert lib.resolve(library, "github_issues").template is not None
    library = lib.delete_template(library, "github_issues", "Fast")
    assert library.templates == () and "github_issues" not in library.assignments
    assert lib.resolve(library, "github_issues").template is None


@pytest.mark.parametrize("name", ["Brief", "default", "  ", "DETAILED"])
def test_reserved_and_blank_names_refused(name: str) -> None:
    with pytest.raises(ValueError):
        lib.add_template(lib.Library(), _t(name=name))


def test_rename_refuses_a_clash() -> None:
    library = lib.add_template(lib.add_template(lib.Library(), _t(name="A")), _t(name="B"))
    with pytest.raises(ValueError):
        lib.rename_template(library, "github_issues", "A", "b")


def test_lost_template_reads_as_default_with_a_note() -> None:
    library = lib.assign(lib.Library(), "github_issues", "user:Gone")
    resolved = lib.resolve(library, "github_issues")
    assert resolved.template is None and "gone" in resolved.note


def test_assign_family_copies_where_fields_fit() -> None:
    result, skipped = lib.assign_family(lib.Library(), "github_pulls", "builtin:brief")
    assert result.assignments["github_issues"] == "builtin:brief"
    assert skipped == ()
    wide = lib.add_template(
        lib.Library(), _t(list_type="github_pulls", name="W", fields=("title", "branches"))
    )
    result, skipped = lib.assign_family(wide, "github_pulls", "user:W")
    assert skipped == ("GitHub issues",) and "github_issues" not in result.assignments


def test_store_round_trip(tmp_path) -> None:
    path = tmp_path / "t.json"
    library = lib.assign(lib.add_template(lib.Library(), _t()), "github_issues", "user:Mine")
    store.save_library(library, path)
    loaded, notice = store.load_library(path)
    assert loaded == library and notice == ""
    assert store.import_text(store.export_text(library)) == library
    assert store.import_text("not json") is None


def test_missing_file_is_empty(tmp_path) -> None:
    assert store.load_library(tmp_path / "none.json") == (lib.Library(), "")


def test_damaged_file_is_kept_aside_not_replaced(tmp_path, monkeypatch) -> None:
    kept: list[tuple[str, bytes]] = []
    monkeypatch.setattr(
        store, "backup_corrupt_file", lambda name, p: kept.append((name, p.read_bytes()))
    )
    path = tmp_path / "t.json"
    path.write_bytes(b"{ broken")
    library, notice = store.load_library(path)
    assert library == lib.Library() and notice == store.DAMAGED_NOTICE
    assert kept == [("list_speech_templates", b"{ broken")]
    assert path.read_bytes() == b"{ broken"  # loading never rewrites it


def test_entries_of_the_wrong_shape_are_dropped_individually(tmp_path) -> None:
    path = tmp_path / "t.json"
    path.write_text(
        '{"templates":[5,{"name":"Ok","list_type":"github_issues","fields":["title"]}],'
        '"assignments":{"a":1,"b":"user:Ok"}}',
        encoding="utf-8",
    )
    loaded, _ = store.load_library(path)
    assert [t.name for t in loaded.templates] == ["Ok"]
    assert dict(loaded.assignments) == {"b": "user:Ok"}


def test_cache_follows_the_file(tmp_path) -> None:
    path = tmp_path / "t.json"
    assert store.load_cached(path) == lib.Library()
    store.save_library(lib.add_template(lib.Library(), _t()), path)
    assert len(store.load_cached(path).templates) == 1


def test_spoken_age() -> None:
    assert spoken_age("2026-11-27T01:00:00Z", TODAY) == "today"
    assert spoken_age("2026-11-26T23:00:00Z", TODAY) == "yesterday"
    assert spoken_age("2026-11-24", TODAY) == "3 days ago"
    assert spoken_age("2026-10-01", TODAY) == "8 weeks ago"
    assert spoken_age("2020-01-01", TODAY) == "2020-01-01"
    assert spoken_age("", TODAY) == ""
    assert spoken_age("garbage", TODAY) == "garbage"


@dataclass(frozen=True)
class Item:
    number: int = 7
    title: str = "Crash"
    state_display: str = "OPEN"
    is_pr: bool = False
    is_draft: bool = False
    author: str = "jeff"
    updated_at: str = "2026-11-26T10:00:00Z"
    labels: tuple[str, ...] = ("bug",)
    assignees: tuple[str, ...] = ()
    comments: int = 0
    head_branch: str = "feat"
    base_branch: str = "main"
    review_status: str = "CHANGES_REQUESTED"


def test_item_fields_for_issue_and_pull() -> None:
    kind, values = github_item_fields(Item(), TODAY)
    assert kind == "github_issues" and values["comments"] == "no comments"
    assert values["updated_ago"] == "yesterday" and "branches" not in values
    kind, values = github_item_fields(Item(is_pr=True, is_draft=True, comments=1), TODAY)
    assert kind == "github_pulls" and values["state"] == "draft"
    assert values["branches"] == "feat into main" and values["review"] == "changes requested"
    assert values["comments"] == "1 comment"


def test_speak_row_defaults_to_none_until_opted_in() -> None:
    assert speak_row(Item(), lib.Library(), TODAY) is None
    library = lib.assign(lib.Library(), "github_issues", "builtin:balanced")
    assert speak_row(Item(), library, TODAY) == "number 7, Crash, open, yesterday, no comments"


def test_speak_row_none_when_nothing_can_be_said() -> None:
    library = lib.assign(
        lib.add_template(lib.Library(), _t(fields=("assignees",))), "github_issues", "user:Mine"
    )
    assert speak_row(Item(), library, TODAY) is None


@dataclass(frozen=True)
class Explore:
    kind: str = "notification"
    fields: tuple[tuple[str, str], ...] = (
        ("status", "Unread"),
        ("title", "Fix"),
        ("updated", "2026-11-27"),
    )


def test_explore_rows() -> None:
    found = explore_row_fields(Explore())
    assert found is not None and found[0] == "github_notifications" and found[1]["updated_ago"]
    assert explore_row_fields(Explore(kind="event")) is None
    assert explore_row_fields(Explore(fields=())) is None


@dataclass(frozen=True)
class Wb:
    kind: str
    subkind: str
    cells: dict[str, str] = field(default_factory=dict)
    raw: dict[str, object] = field(default_factory=dict)


def test_wordpress_rows() -> None:
    post = Wb("item", "post", {"title": "Hi", "status": "Draft", "author": "Jeff"})
    found = wordpress_row_fields(post)
    assert found is not None and found[0] == "wordpress_posts" and found[1]["title"] == "Hi"
    library = lib.assign(lib.Library(), "wordpress_posts", "builtin:balanced")
    assert speak_row(post, library) == "Draft, Hi, Jeff"
    comment = Wb(
        "comment", "comment", {"author": "Pat"}, {"content": {"rendered": "<p>One two three</p>"}}
    )
    found = wordpress_row_fields(comment)
    assert found is not None and found[0] == "wordpress_comments"
    assert found[1]["excerpt"] == "One two three"
    assert wordpress_row_fields(Wb("item", "attachment")) is None
