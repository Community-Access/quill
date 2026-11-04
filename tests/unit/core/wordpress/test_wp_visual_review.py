"""Visual Review and site logo words, directly (wordpress.md 6.10, 6.11)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from quill.core.wordpress import page_capture as pc
from quill.core.wordpress import visual_review as vr


def _png(path: Path, size: tuple[int, int]) -> Path:
    from PIL import Image

    Image.new("RGB", size, (255, 255, 255)).save(path, format="PNG")
    return path


def _fact(**changes: Any) -> pc.ImageFact:
    values: dict[str, Any] = dict(
        src="https://radio.example/up/mast.jpg",
        alt="The mast",
        width=640,
        height=427,
        natural_width=2400,
        natural_height=1600,
        complete=True,
        overflows=False,
        heading="Individual Training",
        top=100,
    )
    values.update(changes)
    return pc.ImageFact(**values)


def _capture(tmp_path: Path, text: str = "Hello") -> pc.Capture:
    return pc.Capture(
        "https://radio.example/",
        (
            pc.ViewCapture(
                pc.DESKTOP,
                _png(tmp_path / "d.png", (100, 60)),
                900,
                900,
                (_fact(), _fact(src="x/divider.png", alt="", heading="")),
                text,
            ),
            pc.ViewCapture(
                pc.PHONE,
                _png(tmp_path / "p.png", (30, 80)),
                844,
                844,
                (
                    _fact(width=358, height=239, overflows=True),
                    _fact(src="x/divider.png", alt=None, complete=False, heading=""),
                ),
            ),
        ),
        {},
        "Google Chrome",
    )


def test_facts_lines_join_the_views(tmp_path) -> None:
    lines = vr.facts_lines(_capture(tmp_path))
    assert lines[0] == (
        "Image 1, mast.jpg, below 'Individual Training': desktop 640 by 427; phone 358 by 239, "
        "spills out of the content area; alt text 'The mast', file is 2400 by 1600."
    )
    assert "above the first heading" in lines[1]
    assert "empty alt text (marked decorative)" in lines[1]
    assert "phone 640 by 427, the image had not finished loading" in lines[1]


def test_instruction_carries_facts_text_and_labels(tmp_path) -> None:
    question = vr.review_instruction(
        _capture(tmp_path, "y" * 9000), proposal="the logo at 200 pixels", unpublished=True
    )
    for words in (
        "likely a problem",
        "a design choice you may want",
        "worth checking",
        "desktop (1366 pixels wide), phone (390 pixels wide)",
        "the logo at 200 pixels",
        "unpublished changes",
        "Image 1, mast.jpg",
        "[The rest of the text was left out.]",
    ):
        assert words in question


def test_consent_and_report(tmp_path) -> None:
    capture = _capture(tmp_path)
    consent = vr.consent_text("Community Radio", capture.url, capture)
    assert "2 images" in consent and "Community Radio" in consent
    report = vr.report_text("Community Radio", capture, "Looks calm.", notes=["", "A note."])
    assert report.startswith(
        "Visual Review of https://radio.example/ on Community Radio, captured with Google Chrome."
    )
    assert "A note.\n\nLooks calm." in report and "Measured by the browser" in report
    assert "no review" in vr.report_text("C", capture, "  ")


def test_combine_screenshots_side_by_side(tmp_path) -> None:
    from PIL import Image

    sheet = vr.combine_screenshots(_capture(tmp_path), tmp_path / "out" / "both.png", max_height=40)
    with Image.open(sheet) as image:
        assert image.height == 40
        assert image.width == round(100 * 40 / 60) + 40 + round(30 * 40 / 80)


def test_styles() -> None:
    style = vr.image_width_style('mast".jpg', 480)
    assert 'img[src*="mast.jpg"]' in style and "480px" in style and "height: auto" in style
    assert ".custom-logo" in vr.logo_width_style(200) and "200px" in vr.logo_width_style(200)


def test_logo_settings() -> None:
    found = vr.logo_settings({"site_logo": "12", "site_icon": None})
    assert found == [
        vr.LogoSetting("site_logo", "Logo", 12, True),
        vr.LogoSetting("site_icon", "Site icon", 0, True),
    ]
    missing = vr.logo_settings({"title": "x", "site_logo": "abc"})
    assert missing[0].media_id == 0 and missing[1].supported is False
    assert vr.logo_settings(None)[0].supported is False


def test_logo_history_round_trip(tmp_path) -> None:
    assert vr.load_logo_history(tmp_path, "a/b") == []
    vr.remember_logo(tmp_path, "a/b", key="site_logo", media_id=4, label="Logo", when="then")
    vr.remember_logo(tmp_path, "a/b", key="site_icon", media_id=0, label="Site icon", when="now")
    rows = vr.load_logo_history(tmp_path, "a/b")
    assert [r["key"] for r in rows] == ["site_icon", "site_logo"]


def test_picture_markup() -> None:
    line = vr.picture_markup("markdown", "https://x/a.png", "A [cat]", 'Say "hi"', 5)
    assert line == '\n![A \\[cat\\]](https://x/a.png "Say \\"hi\\"") {id=5}\n'
    block = vr.picture_markup("html", "https://x/a.png", "A cat", "", 5)
    assert "<!-- wp:image" in block and 'alt="A cat"' in block and "wp-image-5" in block
