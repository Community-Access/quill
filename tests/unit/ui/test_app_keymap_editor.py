"""Both companion app frames compose the Keyboard Shortcuts editor and provide
the five external helpers it (and the global-hotkeys layer) resolve via the MRO:
the three shared parsers, _mark_keyboard_pack_custom, and the live-reapply
_reload_shortcuts_from_keymap that now lives on AppShellFrame.
"""

from __future__ import annotations

from quill.apps.podcasts import PodcastsAppFrame
from quill.apps.radio import RadioAppFrame
from quill.ui.app_shell import AppShellFrame
from quill.ui.keymap_editor import KeymapEditorMixin

_APP_FRAMES = (RadioAppFrame, PodcastsAppFrame)

_EXTERNAL_HELPERS = (
    "_parse_keybinding",
    "_parse_chord_second_key",
    "_is_bare_modifier_key",
    "_mark_keyboard_pack_custom",
    "_reload_shortcuts_from_keymap",
)


def test_app_frames_compose_keymap_editor_mixin() -> None:
    for frame_cls in _APP_FRAMES:
        assert issubclass(frame_cls, KeymapEditorMixin)


def test_app_frames_provide_the_five_external_helpers() -> None:
    for frame_cls in _APP_FRAMES:
        for helper in _EXTERNAL_HELPERS:
            assert callable(getattr(frame_cls, helper, None)), (frame_cls.__name__, helper)


def test_reload_shortcuts_from_keymap_lives_on_app_shell() -> None:
    assert callable(getattr(AppShellFrame, "_reload_shortcuts_from_keymap", None))
    # _mark_keyboard_pack_custom / _set_keyboard_pack are supplied by the shell too.
    assert callable(getattr(AppShellFrame, "_mark_keyboard_pack_custom", None))
    assert callable(getattr(AppShellFrame, "_set_keyboard_pack", None))


def test_open_keymap_editor_available_on_app_frames() -> None:
    for frame_cls in _APP_FRAMES:
        assert callable(getattr(frame_cls, "open_keymap_editor", None))
        assert callable(getattr(frame_cls, "open_global_hotkeys_manager", None))
