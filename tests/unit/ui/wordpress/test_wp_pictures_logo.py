"""Site Logo in File > WordPress, behaviourally (wordpress.md 6.10)."""

from __future__ import annotations

import io
from pathlib import Path
from typing import Any
from urllib.error import HTTPError

import pytest

from quill.core.wordpress import visual_review as vr
from quill.ui import studio_picture_maker as maker
from quill.ui import wordpress_picture_commands as pcmd

API = "/wp-json/wp/v2"

LOGO = {
    "id": 12,
    "title": {"raw": "Old logo"},
    "media_type": "image",
    "mime_type": "image/png",
    "source_url": "https://radio.example/wp-content/uploads/old-logo.png",
    "alt_text": "Community Radio",
    "media_details": {"width": 600, "height": 200},
}
NEW = {**LOGO, "id": 34, "title": {"raw": "New logo"}, "source_url": "https://radio.example/n.png"}


def _settings(logo: int = 12, icon: int = 0) -> dict[str, Any]:
    return {"title": "Community Radio", "site_logo": logo, "site_icon": icon}


@pytest.fixture
def logo_site(wp_site):
    wp_site.on("GET", f"{API}/settings", _settings()).on("GET", f"{API}/media/12", LOGO)
    wp_site.on("POST", f"{API}/settings", lambda req, _q: _settings(34))
    return wp_site


def test_shows_the_logo_and_the_icon(wp, logo_site, wp_dialogs) -> None:
    wp.cmd_site_logo()
    window = wp_dialogs.window
    assert window["title"] == "Site Logo: Community Radio"
    assert window["rows"][0].startswith("Logo: Old logo, image, 600 by 200")
    assert window["rows"][1] == "Site icon: none set"


def test_without_the_administrator_role_it_says_so(wp, wp_site, wp_dialogs) -> None:
    refused = HTTPError(
        "https://radio.example", 403, "no", {}, io.BytesIO(b'{"code":"rest_forbidden"}')
    )
    wp_site.on("GET", f"{API}/settings", refused)
    wp.cmd_site_logo()
    assert "needs the Administrator role on Community Radio" in wp.host.said
    assert wp_dialogs.list_windows == []


def test_a_theme_without_the_standard_logo_stops(wp, wp_site, wp_dialogs) -> None:
    wp_site.on("GET", f"{API}/settings", {"title": "Community Radio"})
    wp.cmd_site_logo()
    assert "does not use the standard site logo" in wp.host.said
    assert wp_dialogs.list_windows == []


def test_replace_from_the_library_confirms_by_name(wp, logo_site, wp_dialogs) -> None:
    logo_site.on("GET", f"{API}/media", [NEW, LOGO])
    wp_dialogs.answer("ask_choice", 0).answer("confirm", True)
    wp.cmd_site_logo()
    wp_dialogs.press("From the &Library...", 0)
    message = wp_dialogs.asked("confirm")[0]["message"]
    assert "Make New logo the logo on Community Radio?" in message
    sent = logo_site.sent("POST", f"{API}/settings")
    assert [logo_site.body(r) for r in sent] == [{"site_logo": 34}]
    assert wp.host.announced[-1] == "The logo on Community Radio is now New logo."
    history = vr.load_logo_history(wp.local.root, "radio")
    assert history[0]["media_id"] == 12 and history[0]["key"] == "site_logo"


def test_cancelling_the_confirmation_sends_nothing(wp, logo_site, wp_dialogs) -> None:
    logo_site.on("GET", f"{API}/media", [NEW])
    wp_dialogs.answer("ask_choice", 0)
    wp.cmd_site_logo()
    wp_dialogs.press("From the &Library...", 0)
    assert logo_site.sent("POST", f"{API}/settings") == []


def test_an_empty_library_says_so(wp, logo_site, wp_dialogs) -> None:
    logo_site.on("GET", f"{API}/media", [])
    wp.cmd_site_logo()
    wp_dialogs.press("From the &Library...", 0)
    assert "no images in the Media Library" in wp.host.said


def test_a_logo_changed_meanwhile_is_not_overwritten(wp, logo_site, wp_dialogs) -> None:
    reads = iter([_settings(12), _settings(77)])
    logo_site.on("GET", f"{API}/settings", lambda _r, _q: next(reads))
    logo_site.on("GET", f"{API}/media", [NEW])
    wp_dialogs.answer("ask_choice", 0).answer("confirm", True)
    wp.cmd_site_logo()
    wp_dialogs.press("From the &Library...", 0)
    assert logo_site.sent("POST", f"{API}/settings") == []
    assert "Nothing was sent: the logo on Community Radio was changed" in wp.host.said


def test_replace_from_a_file_uploads_then_sets(
    wp, logo_site, wp_dialogs, tmp_path, monkeypatch
) -> None:
    picture = tmp_path / "fresh-logo.png"
    picture.write_bytes(b"\x89PNG fake")
    monkeypatch.setattr(pcmd, "ask_open_picture", lambda _host: picture)
    logo_site.on("POST", f"{API}/media", NEW).on("POST", f"{API}/media/34", NEW)
    wp_dialogs.answer("confirm", True)
    wp.cmd_site_logo()
    wp_dialogs.press("From a &File...", 0)
    assert len(logo_site.sent("POST", f"{API}/media")) == 1
    assert logo_site.body(logo_site.sent("POST", f"{API}/settings")[0]) == {"site_logo": 34}
    assert wp.host.announced[-1] == "The logo on Community Radio is now fresh-logo.png."


def test_choosing_no_file_does_nothing(wp, logo_site, wp_dialogs, monkeypatch) -> None:
    monkeypatch.setattr(pcmd, "ask_open_picture", lambda _host: None)
    wp.cmd_site_logo()
    wp_dialogs.press("From a &File...", 0)
    assert wp_dialogs.asked("confirm") == []


def test_the_icon_row_replaces_the_icon(wp, logo_site, wp_dialogs) -> None:
    logo_site.on("GET", f"{API}/media", [NEW])
    wp_dialogs.answer("ask_choice", 0).answer("confirm", True)
    wp.cmd_site_logo()
    wp_dialogs.press("From the &Library...", 1)
    assert logo_site.body(logo_site.sent("POST", f"{API}/settings")[0]) == {"site_icon": 34}


def test_from_the_picture_maker_uses_the_chosen_version(
    wp, logo_site, wp_dialogs, tmp_path, monkeypatch
) -> None:
    from quill.core.ai import picture_maker as pm

    opened: dict[str, Any] = {}
    monkeypatch.setattr(maker, "open_picture_maker", lambda _p, _s, **kw: opened.update(kw))
    monkeypatch.setattr(
        pm, "picture_connection", lambda **_k: pm.PictureConnection("OpenAI", "openai", "k")
    )
    wp.host.ai_editor = lambda: object()
    logo_site.on("POST", f"{API}/media", NEW).on("POST", f"{API}/media/34", NEW)
    wp_dialogs.answer("confirm", True)
    wp.cmd_site_logo()
    wp_dialogs.press("From the &Picture Maker...", 0)
    assert opened["page"].insert_label == "&Use as Logo..."
    made = tmp_path / "Picture - mast.png"
    made.write_bytes(b"\x89PNG fake")
    opened["page"].insert(made)
    assert logo_site.body(logo_site.sent("POST", f"{API}/settings")[0]) == {"site_logo": 34}


def test_preview_a_width_reviews_the_home_page(wp, logo_site, wp_dialogs, monkeypatch) -> None:
    reviewed: list[tuple[str, dict[str, Any]]] = []
    monkeypatch.setattr(wp, "review", lambda _p, url, **kw: reviewed.append((url, kw)))
    wp_dialogs.answer("ask_text", "240")
    wp.cmd_site_logo()
    wp_dialogs.press("Pre&view a Width...", 0)
    url, kwargs = reviewed[0]
    assert url == "https://radio.example"
    assert "240px" in kwargs["style"] and "custom-logo" in kwargs["style"]


def test_restore_earlier_with_nothing_replaced(wp, logo_site, wp_dialogs) -> None:
    wp.cmd_site_logo()
    wp_dialogs.press("&Restore Earlier...", 0)
    assert "has not replaced a logo or icon on Community Radio" in wp.host.said


def test_restore_earlier_puts_the_old_logo_back(wp, logo_site, wp_dialogs) -> None:
    vr.remember_logo(
        wp.local.root, "radio", key="site_logo", media_id=5, label="Logo", when="2026-11-01"
    )
    wp_dialogs.answer("ask_choice", 0).answer("confirm", True)
    wp.cmd_site_logo()
    wp_dialogs.press("&Restore Earlier...", 0)
    assert logo_site.body(logo_site.sent("POST", f"{API}/settings")[0]) == {"site_logo": 5}


def test_picture_size_text_reads_the_file(tmp_path: Path) -> None:
    from PIL import Image

    path = tmp_path / "a.png"
    Image.new("RGB", (30, 20)).save(path)
    assert pcmd.picture_size_text(path) == "Image is 30 by 20"
    assert pcmd.picture_size_text(tmp_path / "missing.png") == "Image size unknown"
