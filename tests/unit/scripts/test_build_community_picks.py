"""Approved suggestions become catalogue entries, and bad ones do not.

The pipeline behind Community Picks: `docs/picks-source.json` for bulk
curation plus every issue labelled `pick:approved`, merged into one document
and validated against the schema before it can be published.

This is the step where public text becomes something Radio will act on, so the
tests are mostly about what it refuses.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Any

import pytest

_ROOT = Path(__file__).resolve().parents[3]
_SCRIPT = _ROOT / "scripts" / "build_community_picks.py"


def _module() -> Any:
    spec = importlib.util.spec_from_file_location("build_community_picks", _SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _issue(number: int, body: str, closed: str = "2026-08-25T12:00:00Z") -> dict[str, Any]:
    return {"number": number, "body": body, "closed_at": closed, "updated_at": closed}


def _suggestion_body(**over: Any) -> str:
    from quill.core.pick_suggestion import Suggestion, issue_body

    fields = {
        "type": "podcast",
        "title": "A Brand New Show",
        "url": "https://example.org/feed",
        "description": "Something worth hearing.",
        "language": "en",
    }
    fields.update(over)
    return issue_body(Suggestion(**fields))


# -- the happy path ------------------------------------------------------------


def test_the_source_alone_builds_and_validates() -> None:
    module = _module()
    document = module.build([])
    module.validate(document)

    assert document["format"] == "quillville-picks"
    assert sum(len(c["items"]) for c in document["collections"]) >= 40


def test_an_approved_issue_becomes_a_catalogue_entry() -> None:
    module = _module()

    document = module.build([_issue(1, _suggestion_body())])
    module.validate(document)

    titles = [item["title"] for c in document["collections"] for item in c["items"]]
    assert "A Brand New Show" in titles


def test_a_suggested_collection_is_created_when_it_is_new() -> None:
    module = _module()

    document = module.build([_issue(1, _suggestion_body(collection="Reading Services"))])

    assert "Reading Services" in [c["title"] for c in document["collections"]]


def test_the_added_date_comes_from_the_issue_not_from_now() -> None:
    """So a rebuild does not make every entry look new again, which would
    make "new since you last looked" useless the first time it mattered."""
    module = _module()

    document = module.build([_issue(1, _suggestion_body(), closed="2026-01-02T03:04:05Z")])
    item = next(
        i for c in document["collections"] for i in c["items"] if i["title"] == "A Brand New Show"
    )

    assert item["added"] == "2026-01-02"


# -- what it refuses -----------------------------------------------------------


def test_an_issue_with_no_pick_block_is_skipped() -> None:
    """Somebody labelling a conversation `pick:approved` must not publish it."""
    module = _module()
    before = module.build([])

    after = module.build([_issue(1, "Looks good to me, let's add it!")])

    assert len(after["collections"]) == len(before["collections"])


def test_a_plain_http_address_never_reaches_the_catalogue() -> None:
    """Rejected in the dialog, in the schema, and here: the one place public
    text turns into something the app will fetch."""
    module = _module()

    document = module.build([_issue(1, _suggestion_body(url="http://example.org/feed"))])

    titles = [item["title"] for c in document["collections"] for item in c["items"]]
    assert "A Brand New Show" not in titles


def test_a_duplicate_address_is_skipped_rather_than_listed_twice() -> None:
    module = _module()
    body = _suggestion_body()

    document = module.build([_issue(1, body), _issue(2, body)])

    titles = [item["title"] for c in document["collections"] for item in c["items"]]
    assert titles.count("A Brand New Show") == 1


def test_two_shows_with_the_same_name_get_different_ids() -> None:
    """ids are identity -- a clash would make two picks look like one, and
    "already added" would then hide the second forever."""
    module = _module()

    document = module.build([
        _issue(1, _suggestion_body(url="https://example.org/one")),
        _issue(2, _suggestion_body(url="https://example.org/two")),
    ])

    ids = [item["id"] for c in document["collections"] for item in c["items"]]
    assert len(ids) == len(set(ids))


def test_the_built_catalogue_always_validates() -> None:
    """The publish step refuses anything the schema does not accept, so a bad
    suggestion cannot reach an app even if it survived everything else."""
    pytest.importorskip("jsonschema")
    module = _module()

    document = module.build([
        _issue(1, _suggestion_body(title="Podcasts en Español de la ACB", url="https://e.org/es")),
        _issue(2, _suggestion_body(url="https://example.org/two")),
    ])

    module.validate(document)


# -- ids ------------------------------------------------------------------------


def test_ids_are_ascii_even_when_the_title_is_not() -> None:
    """str.isalnum() is true for "n with tilde"; the schema caught this the
    first time the catalogue was generated."""
    module = _module()

    assert module.slug("Podcasts en Español de la ACB") == "podcasts-en-espanol-de-la-acb"
    assert module.slug("ACB Media 1").isascii()


# -- the two outputs -------------------------------------------------------------


def test_the_shipped_and_served_copies_are_written_from_one_document() -> None:
    """They cannot disagree: one build, two writes of the same text."""
    source = _SCRIPT.read_text(encoding="utf-8")

    assert "for target in (SITE, BUNDLED)" in source
    assert "docs" in source and "site" in source


def test_the_workflow_publishes_approved_issues_whether_open_or_closed() -> None:
    """An approved issue left open must still publish, or a pick silently
    depends on somebody remembering to close it."""
    workflow = (_ROOT / ".github" / "workflows" / "picks-build.yml").read_text(encoding="utf-8")

    assert '--label "pick:approved"' in workflow
    assert "--state all" in workflow


def test_the_workflow_validates_before_it_commits() -> None:
    workflow = (_ROOT / ".github" / "workflows" / "picks-build.yml").read_text(encoding="utf-8")
    build_at = workflow.index("build_community_picks.py")
    commit_at = workflow.index("git commit")

    assert build_at < commit_at
    assert "jsonschema" in workflow


def test_the_source_file_validates_as_written() -> None:
    """Jeff edits this by hand for bulk work, so a typo here is worth catching
    in the test suite rather than in a workflow run."""
    pytest.importorskip("jsonschema")
    module = _module()
    source = json.loads((_ROOT / "docs" / "picks-source.json").read_text(encoding="utf-8"))

    module.validate({
        "format": "quillville-picks",
        "version": 1,
        "collections": source["collections"],
    })
