"""Quill Radio as a Windows media player: its types, its keys, and nothing taken over.

The registration plan is the editors' (:mod:`quill.core.windows_editor`); these
tests hold Quill Radio's profile to what Quill Radio really plays and check the
keys it writes, with a dict standing in for the registry.
"""

from __future__ import annotations

from quill.core import windows_editor as editor
from quill.core.radio.local_media import MEDIA_SUFFIXES, VIDEO_SUFFIXES
from quill.core.radio.local_media_files import IMPORT_WILDCARD
from quill.core.windows_media import (
    AUDIO_TYPES,
    ENQUEUE_FLAG,
    OPEN_WITH_TYPES,
    PLAYLIST_TYPES,
    RADIO,
    VIDEO_TYPES,
)

LAUNCHER = r"C:\Program Files\Quill Radio\QuillRadio.exe"
ICON = r"C:\Program Files\Quill Radio\quill-radio.ico"


class _Writer:
    def __init__(self) -> None:
        self.values: dict[tuple[str, str], str] = {}

    def set_value(self, path: str, name: str, data: str, kind: str) -> None:
        self.values[(path, name)] = data


def test_every_type_offered_is_one_quill_radio_plays_or_imports() -> None:
    """Offering to open a type the player cannot play is worse than not offering."""
    for ext in (*AUDIO_TYPES, *VIDEO_TYPES):
        assert ext in MEDIA_SUFFIXES, ext
    for ext in VIDEO_TYPES:
        assert ext in VIDEO_SUFFIXES, ext
    for ext in PLAYLIST_TYPES:
        assert f"*{ext}" in IMPORT_WILDCARD, ext
    assert len(set(OPEN_WITH_TYPES)) == len(OPEN_WITH_TYPES)


def test_the_types_asked_for_are_all_there() -> None:
    wanted = (
        ".mp3 .m4a .m4b .aac .ogg .oga .opus .flac .wav .wma .aiff .mka "
        ".m3u .m3u8 .pls .mp4 .mkv .webm .mov"
    ).split()
    assert set(wanted) <= set(RADIO.extensions)


def test_radio_is_a_media_player_and_never_owns_the_notepad_hook() -> None:
    assert RADIO.role == "Media Player"
    assert RADIO not in editor.FAMILY
    assert editor.AppProfile is editor.EditorProfile


def test_the_plan_registers_radio_without_taking_anything_over() -> None:
    writer = _Writer()
    plan = editor.registration_plan(RADIO, [LAUNCHER], ICON)
    editor.write_plan(plan, writer)
    values = writer.values
    command = rf"Software\Classes\{RADIO.progid}\shell\open\command"
    assert values[(command, "")] == f'"{LAUNCHER}" "%1"'
    assert values[(rf"Software\Classes\{RADIO.progid}", "")] == "Quill Radio Media"
    assert values[(r"Software\RegisteredApplications", "Quill Radio")] == RADIO.capabilities_key
    for ext in RADIO.extensions:
        assert (rf"Software\Classes\{ext}\OpenWithProgids", RADIO.progid) in values
        assert (r"Software\Classes\Applications\QuillRadio.exe\SupportedTypes", ext) in values
        assert values[(rf"{RADIO.capabilities_key}\FileAssociations", ext)] == RADIO.progid
    for path, _name in values:
        assert "UserChoice" not in path
        # Never a type's own default: only its OpenWithProgids list is touched.
        assert not any(path == rf"Software\Classes\{ext}" for ext in RADIO.extensions), path


def test_the_right_click_verbs_play_or_add() -> None:
    writer = _Writer()
    editor.write_plan(editor.registration_plan(RADIO, [LAUNCHER], ICON), writer)
    base = r"Software\Classes\SystemFileAssociations\.mp3\shell"
    values = writer.values
    assert values[(rf"{base}\QuillRadio.Play", "")] == "Play with Quill Radio"
    assert values[(rf"{base}\QuillRadio.Play\command", "")] == f'"{LAUNCHER}" "%1"'
    assert values[(rf"{base}\QuillRadio.Enqueue", "")] == "Add to Quill Radio Playlist"
    assert values[(rf"{base}\QuillRadio.Enqueue\command", "")] == (
        f'"{LAUNCHER}" {ENQUEUE_FLAG} "%1"'
    )


def test_the_editors_plans_have_no_verbs_and_keep_their_names() -> None:
    for profile in editor.FAMILY:
        plan = editor.registration_plan(profile, [r"C:\x.exe"], r"C:\x.exe,0")
        assert not any("SystemFileAssociations" in key.path for key in plan)
        assert plan[0].values[0].data == f"{profile.app_name} Document"


def test_settings_opens_quill_radios_own_default_apps_page() -> None:
    assert editor.default_apps_uri(RADIO, 22631) == (
        "ms-settings:defaultapps?registeredAppUser=Quill%20Radio"
    )
    assert editor.default_apps_uri(RADIO, 19045) == "ms-settings:defaultapps"
