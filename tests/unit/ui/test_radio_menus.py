"""Three menus, one question each.

One Playback menu held 39 items covering what the transport is doing, how the
audio sounds, and what to do with video. The video, chapter, transcript and
speed items were not a submenu -- ``radio_video_menu`` appended them flat into
the same menu -- which is why it grew past the point of being arrowable.
"""

from __future__ import annotations

from pathlib import Path

_APPS = Path(__file__).resolve().parents[3] / "quill" / "apps"
_RADIO = (_APPS / "radio.py").read_text(encoding="utf-8")
_VIDEO = (_APPS / "radio_video_menu.py").read_text(encoding="utf-8")


def test_playback_audio_and_video_are_three_top_level_menus() -> None:
    assert 'menu_bar.Append(playback_menu, "&Playback")' in _RADIO
    assert 'menu_bar.Append(audio_menu, "&Audio")' in _RADIO
    assert 'menu_bar.Append(video_menu, "Vi&deo")' in _RADIO


def test_video_is_always_present_rather_than_appearing_and_disappearing() -> None:
    """A menu that comes and goes changes the shape of a bar navigated by
    position, which is far more disorienting than a menu that says 'not now'."""
    appended = _RADIO[_RADIO.index("menu_bar.Append(video_menu") :]
    # Unconditional: not inside an if, not guarded by a feature flag.
    assert appended.startswith('menu_bar.Append(video_menu, "Vi&deo")')


def test_chapters_and_transcript_stay_with_playback_not_video() -> None:
    """A recording and a podcast episode have chapters too. Filing them under
    Video would hide them from most of what this app actually plays."""
    assert 'playback_menu.Append(chapters_id, "C&hapters...' in _VIDEO
    assert 'playback_menu.Append(transcript_id, "&Transcript...' in _VIDEO


def test_described_audio_is_an_audio_item_not_a_video_one() -> None:
    """For a blind listener described audio is the main track, not an
    accessibility extra bolted onto video."""
    assert "audio_target.Append(audio_tracks_id" in _VIDEO
    assert "audio_target.Append(described_id" in _VIDEO


def test_the_picture_items_are_the_video_menu() -> None:
    for ident in ("show_video_id", "captions_id", "video_info_id", "full_screen_id"):
        assert f"video_target.Append({ident}" in _VIDEO, ident
    assert "video_target.AppendSubMenu(size_menu" in _VIDEO


def test_the_builders_fall_back_to_one_menu_when_a_caller_has_not_split() -> None:
    """So a surface that hands in a single menu keeps working unchanged."""
    assert "audio_target = audio_menu if audio_menu is not None else playback_menu" in _VIDEO
    assert "video_target = video_menu if video_menu is not None else playback_menu" in _VIDEO


def test_listening_statistics_is_a_report_and_lives_in_view() -> None:
    """It reports past listening; it does not control present listening."""
    extras = (_APPS / "radio_playback_extras.py").read_text(encoding="utf-8")
    assert "stats_home = view_menu if view_menu is not None else menu" in extras
    assert 'stats_home.Append(stats_id, "Listening Stati&stics...' in extras


def test_edit_sits_directly_after_the_app_menu_rather_than_at_the_end() -> None:
    """Alt+E is hunted for at the front of the bar, not between Community and
    QuillVille -- which is where ``position=menu_bar.GetMenuCount()`` put it."""
    support = (Path(__file__).resolve().parents[3] / "quill" / "ui" / "support_menu.py").read_text(
        encoding="utf-8"
    )

    # No ``position=`` argument: the default is 1, immediately after the
    # app's own first menu. It used to be passed GetMenuCount().
    assert "\n    insert_edit_menu(host, menu_bar, wx)\n" in support
    assert "position: int = 1" in support
    # View is built late (its Text Size radio items need the font scale), so it
    # inserts *after* Edit has already taken index 1: Station, Edit, View.
    assert 'menu_bar.Insert(2, view_menu, "&View")' in _RADIO


def test_the_community_menu_does_not_advertise_a_chord_that_is_someone_elses() -> None:
    """Its title carried "Ctrl+Alt+A" -- which is Bookmark This Moment.

    Left over from when the menu was the Audio Description Project's. A
    top-level menu is opened by its mnemonic (Alt+C here), and no other menu on
    this bar puts a chord in its title.
    """
    assert 'menu_bar.Append(adp_menu, "&Community")' in _RADIO
    titles = [line for line in _RADIO.splitlines() if "menu_bar.Append(" in line]
    assert not [line for line in titles if "Ctrl+" in line], titles
