"""Tests for bulk draft import (PRD 18.10)."""

from quill_social.services import bulk_import as bi


def test_parse_csv():
    text = (
        "text,targets,visibility,lang\n"
        "Hello world,a1;a2,public,en\n"
        "Second post,a1,unlisted,\n"
    )
    rows = bi.parse(text, "csv")
    assert len(rows) == 2
    assert rows[0].text == "Hello world"
    assert rows[0].targets == ["a1", "a2"]
    assert rows[0].visibility == "public"
    assert rows[0].lang == "en"
    assert rows[1].visibility == "unlisted"
    assert all(r.ok for r in rows)


def test_parse_tsv():
    text = "text\ttargets\nTab post\ta1\n"
    rows = bi.parse(text, "tsv")
    assert rows[0].text == "Tab post"
    assert rows[0].targets == ["a1"]


def test_parse_json():
    text = '[{"text": "J1", "targets": ["a1"]}, {"body": "J2", "visibility": "direct"}]'
    rows = bi.parse(text, "json")
    assert rows[0].text == "J1" and rows[0].targets == ["a1"]
    assert rows[1].text == "J2" and rows[1].visibility == "direct"


def test_parse_json_malformed_does_not_raise():
    rows = bi.parse("{not valid json", "json")
    assert len(rows) == 1
    assert not rows[0].ok
    assert "invalid JSON" in rows[0].errors[0]


def test_parse_markdown_splits_on_rule():
    text = "First post\nwith two lines\n---\nSecond post\n---\n\n"
    rows = bi.parse(text, "markdown")
    assert len(rows) == 2
    assert rows[0].text == "First post\nwith two lines"
    assert rows[1].text == "Second post"


def test_validation_catches_empty_and_bad_visibility():
    text = "text,visibility\n,public\nHi,banana\n"
    rows = bi.parse(text, "csv")
    assert not rows[0].ok
    assert any("empty" in e for e in rows[0].errors)
    assert not rows[1].ok
    assert any("visibility" in e for e in rows[1].errors)
    # Bad visibility is coerced back to a safe default.
    assert rows[1].visibility == "public"


def test_to_drafts_skips_invalid_and_applies_defaults():
    text = "text,targets\nGood,\nAlsoGood,a9\n,\n"
    rows = bi.parse(text, "csv")
    drafts = bi.to_drafts(rows, default_targets=["default1"])
    assert len(drafts) == 2
    assert drafts[0].targets == ["default1"]  # empty targets -> default
    assert drafts[1].targets == ["a9"]
    assert drafts[0].text == "Good"


def test_dry_run_duplicate_detection_and_preview():
    text = (
        "text\n"
        "Same content\n"
        "Different\n"
        "same   CONTENT\n"  # duplicate after normalization
    )
    rows = bi.parse(text, "csv")
    report = bi.dry_run(rows)
    assert report.total == 3
    assert report.valid == 3
    assert report.invalid == 0
    assert report.duplicate_groups == [[0, 2]]
    assert report.duplicate_count == 2
    assert len(report.preview_lines) == 3
    assert report.needs_timezone_confirmation is True


def test_dry_run_counts_invalid():
    # A present-but-empty text field (blank CSV lines are skipped by the reader).
    text = "text,lang\n,en\nOk,en\n"
    rows = bi.parse(text, "csv")
    report = bi.dry_run(rows)
    assert report.invalid == 1
    assert report.valid == 1


def test_unknown_format():
    rows = bi.parse("whatever", "xml")
    assert not rows[0].ok
    assert "unknown format" in rows[0].errors[0]
