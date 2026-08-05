"""Media-player configuration defaults (``player.md`` Section 10).

The source of truth for every ``media_*`` setting and its default. Kept as a
plain, dependency-free mapping so it is unit-testable and can later be registered
into the searchable global settings registry (``quill/core/settings_specs.py``)
without changing these values. ``resolve`` merges a user settings mapping over the
defaults, ignoring anything that is not a known ``media_*`` key.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

#: Every player setting key -> its default value (see player.md Section 10.2).
MEDIA_DEFAULTS: dict[str, Any] = {
    # Playback
    "media_skip_back_seconds": 15,
    "media_skip_forward_seconds": 30,
    "media_default_speed": 1.0,
    "media_remember_speed_per_book": True,
    "media_smart_rewind": True,
    "media_resume_last_on_launch": False,
    "media_stop_at_end_of_chapter": False,
    "media_bookmark_on_pause": False,
    "media_gapless": True,
    "media_crossfade_seconds": 0,
    # Audio & DSP
    "media_backend": "auto",
    "media_default_eq_preset": "flat",
    "media_eq_scope": "global",
    "media_volume_boost_db": 0,
    "media_normalize": False,
    "media_skip_silence": False,
    # Chapters & navigation
    "media_announce_chapter": True,
    "media_chapter_chime": True,
    "media_daisy_default_level": "heading",
    "media_where_am_i_detail": "full",
    # Bookmarks
    "media_auto_bookmark_on_sleep": True,
    "media_send_bookmark_target": "document",
    "media_bookmark_export_format": "markdown",
    # Library
    "media_library_default_view": "in_progress",
    "media_auto_add_inbox": True,
    "media_mark_finished_threshold": 95,
    "media_series_autoadvance": False,
    # Announcements & sound
    "media_verbosity": "normal",
    "media_self_voicing": False,
    "media_announce_value_changes": True,
    "media_position_ticks": False,
    "media_earcon_pack": "classic",
    "media_braille_status": True,
    # Voice control
    "media_voice_control": False,
    # Sleep timer
    "media_sleep_default_minutes": 30,
    "media_sleep_fade_seconds": 5,
    "media_still_awake_prompt": True,
    # Now Playing & OS integration
    "media_smtc": True,
    "media_global_media_keys": True,
    "media_mini_player_home": "docked",
    "media_always_on_top": False,
    "media_show_album_art": True,
    "media_show_waveform": True,
    # Magical Mode
    "media_magical_mode": False,
    # Appearance
    "media_theme": "system",
    "media_reduced_motion": "follow_os",
    # Downloads & storage
    "media_keep_offline": True,
    # Privacy & network
    "media_position_sync": False,
}


def default_config() -> dict[str, Any]:
    """Return a fresh copy of the default player configuration."""
    return dict(MEDIA_DEFAULTS)


def resolve(settings: Mapping[str, Any]) -> dict[str, Any]:
    """Return the effective config: defaults overlaid with known ``media_*`` keys."""
    config = default_config()
    for key, value in settings.items():
        if key in MEDIA_DEFAULTS:
            config[key] = value
    return config


__all__ = ["MEDIA_DEFAULTS", "default_config", "resolve"]
