"""Fix in Bulk's safe fixes, Find and Replace matching, and the undo records (wordpress.md 9.5)."""

from __future__ import annotations

import pytest

from quill.core.wordpress import checks as chk
from quill.core.wordpress import site_fixes as sf


def _kinds(html: str) -> set[str]:
    return {f.kind for f in chk.check_content(html, title="T")}


def test_new_tab_links_say_so_and_the_check_then_passes() -> None:
    html = '<p>See <a href="https://x.example" target="_blank">the schedule</a>.</p>'
    fixed, count = sf.apply_fix("link-new-tab-unsaid", html)
    assert count == 1
    assert "the schedule (opens in a new tab)</a>" in fixed
    assert "link-new-tab-unsaid" not in _kinds(fixed)
    assert sf.apply_fix("link-new-tab-unsaid", fixed) == (fixed, 0)


def test_a_new_tab_link_with_an_aria_label_is_left_for_the_writer() -> None:
    html = '<a href="/x" target="_blank" aria-label="Schedule">Schedule</a>'
    assert sf.apply_fix("link-new-tab-unsaid", html) == (html, 0)


def test_autoplay_comes_off_the_video_and_nothing_else_changes() -> None:
    html = '<figure><video controls autoplay src="a.mp4"></video></figure><p>autoplay</p>'
    fixed, count = sf.apply_fix("video-autoplay", html)
    assert count == 1
    assert fixed == '<figure><video controls src="a.mp4"></video></figure><p>autoplay</p>'


def test_alt_text_loses_image_of_and_keeps_a_capital() -> None:
    html = '<img src="a.jpg" alt="Image of the studio desk"/>'
    fixed, count = sf.apply_fix("alt-says-image", html)
    assert count == 1
    assert 'alt="The studio desk"' in fixed


def test_heading_one_becomes_two_and_its_block_setting_goes() -> None:
    html = (
        '<!-- wp:heading {"level":1} -->\n<h1 class="wp-block-heading">Hi</h1>\n'
        "<!-- /wp:heading -->\n"
        '<!-- wp:heading {"textAlign":"center","level":1} -->\n<h1>Two</h1>\n<!-- /wp:heading -->'
    )
    fixed, count = sf.apply_fix("heading-1-in-body", html)
    assert count == 2
    assert "<!-- wp:heading -->\n<h2" in fixed
    assert '<!-- wp:heading {"textAlign":"center"} -->' in fixed
    assert "<h1" not in fixed and "</h1>" not in fixed


def test_an_unknown_kind_is_never_fixed() -> None:
    assert sf.apply_fix("image-no-alt", "<img src=a>") == ("<img src=a>", 0)


def test_find_leaves_block_settings_alone_unless_asked() -> None:
    html = '<!-- wp:paragraph {"className":"phone"} -->\n<p>Call the phone line.</p>'
    found, hidden = sf.find_matches(html, sf.FindOptions("phone", "telephone"))
    assert len(found) == 1 and hidden == 1
    assert "[phone]" in found[0].context
    found, hidden = sf.find_matches(
        html, sf.FindOptions("phone", "telephone", include_block_settings=True)
    )
    assert len(found) == 2 and hidden == 0


def test_find_case_and_patterns() -> None:
    html = "<p>Call 555-0100 or 555-0199. CALL now.</p>"
    assert len(sf.find_matches(html, sf.FindOptions("call", "x"))[0]) == 2
    assert len(sf.find_matches(html, sf.FindOptions("call", "x", match_case=True))[0]) == 0
    found, _ = sf.find_matches(html, sf.FindOptions(r"555-(\d+)", r"556-\1", regex=True))
    assert [m.replacement for m in found] == ["556-0100", "556-0199"]
    assert sf.apply_matches(html, found[:1]) == "<p>Call 556-0100 or 555-0199. CALL now.</p>"


def test_a_bad_pattern_is_a_plain_error() -> None:
    with pytest.raises(sf.PatternError):
        sf.FindOptions("(", "", regex=True).compiled()


def test_fix_records_round_trip_and_mark_undone(tmp_path) -> None:
    store = sf.FixRecordStore(tmp_path)
    fix = sf.SiteFix(
        "f1",
        "radio",
        "2026-11-04T10:00:00",
        "Label",
        [sf.FixedItem("page", 3, "Home", "<p>old</p>", "2026-11-04T10:00:01")],
    )
    store.add(fix)
    loaded = store.load("radio")
    assert loaded[0].items[0].before == "<p>old</p>"
    assert "Label, 1 page" in loaded[0].spoken()
    store.mark_undone("radio", "f1")
    assert store.load("radio")[0].undone
    assert "put back" in store.load("radio")[0].spoken()
    assert store.load("other") == []


def test_batch_requests_and_outcomes() -> None:
    requests = sf.update_requests([("page", 3, "<p>x</p>"), ("post", 9, "y")])
    assert requests[0] == {
        "method": "POST",
        "path": "/wp/v2/pages/3",
        "body": {"content": "<p>x</p>"},
    }
    assert requests[1]["path"] == "/wp/v2/posts/9"
    answers = [{"status": 200, "body": {"modified_gmt": "S"}}, {"status": 403, "body": {}}]
    assert sf.batch_outcomes(answers, 3) == ["S", "", ""]
