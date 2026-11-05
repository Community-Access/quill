"""Visual Review and Preview and Review, behaviourally (wordpress.md 6.11).

The browser and the AI are faked: ``capture_page`` returns two small
screenshots and measured facts, and the host's picture route records what it
was asked.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from quill.core.wordpress import cdp
from quill.core.wordpress import local as lc
from quill.core.wordpress import page_capture as pc
from quill.core.wordpress import visual_review as vr
from quill.ui import wordpress_item_dialogs as idlg

PAGE = "https://radio.example/our-schedule/"


class OnAi:
    def _ai_switched_on(self) -> bool:
        return True


def _png(path: Path, size: tuple[int, int]) -> Path:
    from PIL import Image

    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", size, (250, 250, 250)).save(path, format="PNG")
    return path


def _fact(**changes: Any) -> pc.ImageFact:
    values: dict[str, Any] = {
        "src": "https://radio.example/wp-content/uploads/mast.jpg",
        "alt": "The mast",
        "width": 640,
        "height": 427,
        "natural_width": 2400,
        "natural_height": 1600,
        "complete": True,
        "overflows": False,
        "heading": "Our Schedule",
        "top": 300,
    }
    values.update(changes)
    return pc.ImageFact(**values)


@pytest.fixture
def captured(monkeypatch) -> list[dict[str, Any]]:
    calls: list[dict[str, Any]] = []

    def fake_capture(url, out_dir, **kwargs):
        calls.append({"url": url, **kwargs})
        views = (
            pc.ViewCapture(
                pc.DESKTOP,
                _png(out_dir / "desktop.png", (137, 90)),
                900,
                900,
                (_fact(),),
                "Our Schedule\nMornings on the hill.",
            ),
            pc.ViewCapture(
                pc.PHONE,
                _png(out_dir / "phone.png", (39, 84)),
                844,
                844,
                (_fact(width=358, height=239, overflows=True),),
            ),
        )
        headers = {"last-modified": "Sun, 01 Nov 2026 10:00:00 GMT"}
        return pc.Capture(url, views, headers, "Microsoft Edge")

    monkeypatch.setattr(pc, "capture_page", fake_capture)
    return calls


@pytest.fixture
def looked(wp) -> list[tuple[Path, str]]:
    asked: list[tuple[Path, str]] = []
    wp.host.ai_editor = lambda: OnAi()

    def describe(path, question, on_done, on_error):
        asked.append((Path(path), question))
        on_done(
            "Overall impression: calm and clear. The mast picture is likely a problem on phones."
        )
        return True

    wp.host.ai_describe_image = describe
    return asked


def _published(wp, wp_dialogs, *, text_format: str = "markdown") -> lc.WorkingCopy:
    wp_dialogs.answer(
        "ask_new_item",
        idlg.NewItemAnswer(
            site_index=0,
            title="Our Schedule",
            slug="our-schedule",
            text_format=text_format,
            category_ids=[],
            tag_ids=[],
        ),
    )
    wp.cmd_new_page()
    copy = wp.local.copy_for_path(wp.host.current_path())
    copy.status = "publish"
    copy.link = PAGE
    copy.remote_id = 41
    copy.base_modified_gmt = "2026-11-03T09:00:00"
    wp.local.save(copy)
    wp.host.text = "![The mast](https://radio.example/wp-content/uploads/mast.jpg)\n"
    wp.host.announced.clear()
    return copy


# --------------------------------------------------------------------------- #
# Visual Review


def test_outside_a_wordpress_document_says_so(wp, captured) -> None:
    wp.cmd_visual_review()
    assert "This is not a WordPress document" in wp.host.said
    assert captured == []


def test_a_draft_is_not_reviewed(wp, wp_dialogs, looked, captured) -> None:
    copy = _published(wp, wp_dialogs)
    copy.status = "draft"
    wp.local.save(copy)
    wp.cmd_visual_review()
    assert "not published on Community Radio yet" in wp.host.said
    assert captured == []


def test_with_ai_switched_off_nothing_is_captured(wp, wp_dialogs, captured) -> None:
    _published(wp, wp_dialogs)

    class Off:
        def _ai_switched_on(self) -> bool:
            return False

    wp.host.ai_editor = lambda: Off()
    wp.cmd_visual_review()
    assert captured == []


def test_review_says_what_it_sends_then_reports(wp, wp_dialogs, looked, captured) -> None:
    _published(wp, wp_dialogs)
    wp_dialogs.answer("confirm", True)
    wp.cmd_visual_review()
    assert captured[0]["url"] == PAGE and captured[0]["style"] == ""
    assert wp.host.announced[0] == f"Capturing the desktop and phone views of {PAGE}."
    consent = wp_dialogs.asked("confirm")[0]
    assert consent["yes_label"] == "Send for Review"
    assert "desktop and phone screenshots" in consent["message"] and "1 image" in consent["message"]
    sheet, question = looked[0]
    assert sheet.name == "both.png" and sheet.exists()
    assert "Image 1, mast.jpg, below 'Our Schedule'" in question
    assert "phone 358 by 239, spills out of the content area" in question
    report = wp_dialogs.reports[-1]
    assert report["title"] == "Visual Review"
    assert "likely a problem on phones" in report["text"]
    assert "Measured by the browser" in report["text"]
    assert "captured with Microsoft Edge" in report["text"]
    saved = wp.local.root / "visual-review" / "radio" / "review.txt"
    assert "calm and clear" in saved.read_text(encoding="utf-8")


def test_saying_no_sends_nothing(wp, wp_dialogs, looked, captured) -> None:
    _published(wp, wp_dialogs)
    wp.cmd_visual_review()
    assert looked == []
    assert "Nothing was sent. The screenshots are in" in wp.host.announced[-1]


def test_an_older_capture_warns_of_a_cached_copy(wp, wp_dialogs, looked, captured) -> None:
    _published(wp, wp_dialogs)
    wp_dialogs.answer("confirm", True)
    wp.cmd_visual_review()
    assert "cached copy" in wp_dialogs.reports[-1]["text"]


def test_unpublished_changes_are_named(wp, wp_dialogs, looked, captured) -> None:
    copy = _published(wp, wp_dialogs)
    wp.local.add_version(copy, lc.REASON_PUBLISHED, text="The published words.")
    wp_dialogs.answer("confirm", True)
    wp.cmd_visual_review()
    assert vr.UNPUBLISHED_NOTE in wp_dialogs.reports[-1]["text"]
    assert "unpublished changes" in looked[0][1]


def test_no_browser_says_so_and_downloads_nothing(wp, wp_dialogs, looked, monkeypatch) -> None:
    _published(wp, wp_dialogs)
    monkeypatch.setattr(cdp, "find_browser", lambda *_a: None)
    wp.cmd_visual_review()
    assert "does not download a browser" in wp.host.said
    assert looked == []


# --------------------------------------------------------------------------- #
# Preview and Review


def test_preview_of_a_draft_explains_why_not(wp, wp_dialogs, looked, captured) -> None:
    copy = _published(wp, wp_dialogs)
    copy.status = "draft"
    wp.local.save(copy)
    wp.cmd_preview_and_review()
    assert wp.host.announced[-1] == vr.PREVIEW_NEEDS_PUBLISHED
    assert captured == []


def test_preview_injects_the_proposed_width(wp, wp_dialogs, looked, captured) -> None:
    _published(wp, wp_dialogs)
    wp_dialogs.answer("ask_choice", 0).answer("ask_text", "480").answer("confirm", True)
    wp.cmd_preview_and_review()
    rows = wp_dialogs.asked("ask_choice")[0]["rows"]
    assert rows == ["The picture mast.jpg", "The site logo"]
    style = captured[0]["style"]
    assert 'img[src*="mast.jpg"]' in style and "480px" in style
    assert "the picture mast.jpg shown 480 pixels wide" in looked[0][1]
    assert wp_dialogs.reports[-1]["title"] == "Preview and Review"
    assert "nothing on the site changed" in wp_dialogs.reports[-1]["text"]


def test_preview_of_the_logo_width(wp, wp_dialogs, looked, captured) -> None:
    _published(wp, wp_dialogs)
    wp_dialogs.answer("ask_choice", 1).answer("ask_text", "200px")
    wp.cmd_preview_and_review()
    assert "custom-logo" in captured[0]["style"] and "200px" in captured[0]["style"]


def test_a_bad_width_is_refused(wp, wp_dialogs, looked, captured) -> None:
    _published(wp, wp_dialogs)
    wp_dialogs.answer("ask_choice", 0).answer("ask_text", "wide")
    wp.cmd_preview_and_review()
    assert "Type a width in pixels" in wp.host.said
    assert captured == []


def test_cancelling_the_choice_captures_nothing(wp, wp_dialogs, looked, captured) -> None:
    _published(wp, wp_dialogs)
    wp.cmd_preview_and_review()
    assert captured == []
