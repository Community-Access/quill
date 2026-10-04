"""Use my YouTube sign-in: only a browser name or a file path, and off by default."""

from __future__ import annotations

import json

import pytest

from quill.core.radio import youtube_signin as ys


def test_off_by_default_and_nothing_is_passed(quill_data_dir) -> None:
    assert ys.load() == ys.SignInSettings()
    assert ys.cookie_options() == {}


def test_a_browser_is_passed_by_name_only(quill_data_dir) -> None:
    ys.save(ys.SignInSettings(enabled=True, source="edge"))
    assert ys.cookie_options() == {"cookiesfrombrowser": ("edge",)}


def test_a_cookies_file_is_passed_by_path_only(quill_data_dir, tmp_path) -> None:
    path = str(tmp_path / "cookies.txt")
    ys.save(ys.SignInSettings(enabled=True, source=ys.FILE_SOURCE, cookies_file=path))
    assert ys.cookie_options() == {"cookiefile": path}


def test_file_source_without_a_file_is_off(quill_data_dir) -> None:
    ys.save(ys.SignInSettings(enabled=True, source=ys.FILE_SOURCE))
    assert ys.cookie_options() == {}


def test_safe_mode_never_signs_in(quill_data_dir) -> None:
    ys.save(ys.SignInSettings(enabled=True, source="firefox"))
    assert ys.cookie_options(safe_mode=True) == {}


def test_the_stored_file_holds_no_cookie_values(quill_data_dir) -> None:
    ys.save(ys.SignInSettings(enabled=True, source="firefox", cookies_file="C:/x/cookies.txt"))
    stored = json.loads((quill_data_dir / "radio-youtube-signin.json").read_text("utf-8"))
    assert set(stored) == {"enabled", "source", "cookies_file"}


def test_every_offered_browser_is_one_yt_dlp_supports() -> None:
    cookies = pytest.importorskip("yt_dlp.cookies")
    assert {name for name, _l in ys.BROWSERS} <= cookies.SUPPORTED_BROWSERS


def test_choice_rows_round_trip() -> None:
    labels = ys.choice_labels()
    assert labels[-1].startswith("A cookies.txt file")
    for index in range(len(labels)):
        source = ys.source_from_index(index)
        assert ys.source_index(ys.SignInSettings(source=source)) == index


@pytest.mark.parametrize(
    ("error", "expect"),
    [
        ("Could not copy Chrome cookie database. See https://...", "Close it"),
        ("Failed to decrypt with DPAPI. See https://...", "only Microsoft Edge itself"),
        ('could not find edge cookies database in "C:/..."', "could not find"),
        ("Sign in to confirm you're not a bot", "Turn on Use my YouTube sign-in"),
        ("HTTP Error 404", ""),
    ],
)
def test_cookie_failures_become_one_plain_sentence(error, expect) -> None:
    said = ys.describe_failure(error, ys.SignInSettings(enabled=True, source="edge"))
    assert (expect in said) if expect else said == ""


def test_the_privacy_paragraph_is_honest_about_the_trade() -> None:
    assert "never copies, saves or logs" in ys.PRIVACY_NOTE
    assert "Anyone who can use your Windows account" in ys.PRIVACY_NOTE
    assert "Turn it off any time" in ys.PRIVACY_NOTE


def test_redaction_drops_cookie_lines_from_bundles() -> None:
    from quill.stability.redaction import redact_text_for_bundle

    text = (
        "kept\n"
        ".youtube.com\tTRUE\t/\tTRUE\t1790000000\tSAPISID\tsecretvalue\n"
        "Cookie: __Secure-3PSID=secretvalue\n"
        "SID=secretvalue\n"
        "also kept\n"
    )
    out = redact_text_for_bundle(text)
    assert "secretvalue" not in out
    assert "kept" in out and "also kept" in out


def test_preferences_apply_saves_the_choice_and_says_where_my_youtube_is(quill_data_dir) -> None:
    pytest.importorskip("wx")
    from quill.apps import radio_youtube_signin_prefs as prefs

    firefox = [name for name, _l in ys.BROWSERS].index("firefox")
    said = prefs.apply(True, firefox)
    assert ys.load() == ys.SignInSettings(enabled=True, source="firefox")
    assert "My YouTube" in said
    assert prefs.apply(False, firefox) == "YouTube sign-in is off."
    assert ys.cookie_options() == {}


def test_preferences_rows_take_letters_no_other_setting_uses(quill_data_dir) -> None:
    import re
    from pathlib import Path

    pytest.importorskip("wx")
    from quill.apps import radio_preferences
    from quill.apps import radio_youtube_signin_prefs as prefs

    check, choice, action = prefs.rows(object())
    mine = [re.search(r"&(.)", row.name).group(1).lower() for row in (check, choice, action)]
    source = Path(radio_preferences.__file__).read_text(encoding="utf-8")
    theirs = {m.group(1).lower() for m in re.finditer(r'"[^"\n]*&([^&"\n])', source)}
    assert len(set(mine)) == 3 and not set(mine) & theirs
    assert ys.PRIVACY_NOTE in check.help_text
