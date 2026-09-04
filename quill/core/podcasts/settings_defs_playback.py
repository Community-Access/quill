"""Catalogue entries for the settings that decide how a podcast *plays*.

The settings themselves are not new -- every one of these is a field of
:class:`~quill.core.podcasts.models_settings.PodcastSettings` that Cast has
shipped for releases. What is new is that they are *described*: a label, the
house-rule help, the levels they may be set at, and the words their value reads
back as. That description is what makes them searchable (*Find a Setting*),
reportable ("what have I changed?"), and resolvable through the folder level
they never had.

Split from the rest of the catalogue under GATE-11 and along the line the
categories already draw: this file is Playback, its sibling is everything about
a library. Both are pure data read by
:mod:`quill.core.podcasts.settings_catalog`.

wx-free, strict-typed, pure data.
"""

from __future__ import annotations

from collections.abc import Callable

from quill.core.podcasts import settings_help
from quill.core.podcasts.settings_types import (
    CATEGORY_PLAYBACK,
    KIND_CHOICE,
    KIND_FLOAT,
    KIND_INT,
    LEVEL_GLOBAL,
    LEVEL_SHOW,
    SettingDef,
    choices,
    define,
)


def _speed(value: object) -> str:
    from quill.core.podcasts.single_settings import describe_speed

    return describe_speed(float(value))  # type: ignore[arg-type]


def _seconds(noun: str) -> Callable[[object], str]:
    """ "Skip forward: 30 seconds", and "off" rather than "0 seconds"."""

    def describe(value: object) -> str:
        count = int(value)  # type: ignore[arg-type]
        if count <= 0:
            return f"{noun}: off."
        return f"{noun}: {count} second{'' if count == 1 else 's'}."

    return describe


SETTINGS: tuple[SettingDef, ...] = (
    define(
        "speed",
        "Playback &speed:",
        "How fast a podcast plays, from half speed to five times. It is "
        "remembered between episodes and never changes the audio on disk -- a "
        "downloaded file is the same file whatever this says.",
        kind=KIND_FLOAT,
        category=CATEGORY_PLAYBACK,
        default=1.0,
        minimum=0.5,
        maximum=5.0,
        settings_field="speed",
        aliases=("rate", "faster", "slower", "tempo"),
        describe=_speed,
    ),
    define(
        "playback_mode",
        "Default playback &mode:",
        settings_help.HELP["playback_default"],
        kind=KIND_CHOICE,
        category=CATEGORY_PLAYBACK,
        default="download",
        choices=choices(("download", "Download episodes"), ("stream", "Stream episodes")),
        settings_field="playback_mode",
        aliases=("stream", "download", "offline"),
    ),
    define(
        "channel_mode",
        "Send the audio to:",
        "Which ears the audio comes out of: both, mixed to mono, or one side "
        "only. An accessibility setting before a sound one -- mono keeps "
        "hard-panned content audible to somebody listening with one ear, and it "
        "never alters the file, only what is played.",
        kind=KIND_CHOICE,
        category=CATEGORY_PLAYBACK,
        default="stereo",
        choices=choices(
            ("stereo", "Both ears"),
            ("mono", "Mono, mixed to both"),
            ("left", "Left ear only"),
            ("right", "Right ear only"),
        ),
        settings_field="channel_mode",
        aliases=("mono", "stereo", "one ear", "balance"),
    ),
    define(
        "volume_boost",
        "Volume &Boost:",
        settings_help.HELP["volume_boost"],
        kind=KIND_CHOICE,
        category=CATEGORY_PLAYBACK,
        default="off",
        choices=choices(("off", "Off"), ("low", "Low"), ("medium", "Medium"), ("high", "High")),
        settings_field="volume_boost",
        aliases=("louder", "gain", "quiet podcast"),
    ),
    define(
        "eq_bass_db",
        "Bass, in decibels:",
        "Lifts or cuts the low end of everything played. It is applied as it "
        "plays -- nothing on disk is rewritten, and turning it back to zero "
        "restores the original sound exactly.",
        kind=KIND_FLOAT,
        category=CATEGORY_PLAYBACK,
        default=0.0,
        minimum=-12.0,
        maximum=12.0,
        settings_field="eq_bass_db",
        aliases=("equalizer", "eq", "low"),
    ),
    define(
        "eq_mid_db",
        "Middle, in decibels:",
        "Lifts or cuts the middle of everything played, which is where speech "
        "sits. Applied as it plays; the downloaded file is untouched.",
        kind=KIND_FLOAT,
        category=CATEGORY_PLAYBACK,
        default=0.0,
        minimum=-12.0,
        maximum=12.0,
        settings_field="eq_mid_db",
        aliases=("equalizer", "eq", "voice"),
    ),
    define(
        "eq_treble_db",
        "Treble, in decibels:",
        "Lifts or cuts the high end of everything played. Applied as it plays; "
        "it does not rewrite the audio and it cannot damage a download.",
        kind=KIND_FLOAT,
        category=CATEGORY_PLAYBACK,
        default=0.0,
        minimum=-12.0,
        maximum=12.0,
        settings_field="eq_treble_db",
        aliases=("equalizer", "eq", "high"),
    ),
    define(
        "compressor_enabled",
        "&Even out volume",
        "Narrows the gap between the quiet and loud parts, so a whisper and a "
        "laugh sit closer together. It is playback only -- nothing is written "
        "to the file, and your system volume is untouched.",
        category=CATEGORY_PLAYBACK,
        default=False,
        settings_field="compressor_enabled",
        aliases=("compressor", "dynamic range", "loudness"),
    ),
    define(
        "smart_speed_enabled",
        "&Shorten silences",
        "Trims the pauses between words as it plays, which shortens an episode "
        "without speeding anybody up. It never removes audio from the file and "
        "never changes the pitch.",
        category=CATEGORY_PLAYBACK,
        default=False,
        settings_field="smart_speed_enabled",
        aliases=("smart speed", "trim silence", "gaps"),
    ),
    define(
        "skip_forward_seconds",
        "Skip &forward by:",
        "How far Skip Forward jumps. It changes the size of one jump, not how "
        "many you may make, and it never alters the episode.",
        kind=KIND_INT,
        category=CATEGORY_PLAYBACK,
        default=30,
        minimum=1,
        maximum=600,
        settings_field="skip_forward_seconds",
        aliases=("jump", "seek", "forward"),
        describe=_seconds("Skip forward"),
    ),
    define(
        "skip_back_seconds",
        "Skip &back by:",
        "How far Skip Back jumps. Usually shorter than Skip Forward, because "
        "going back is about hearing something again rather than getting past "
        "it. It never alters the episode.",
        kind=KIND_INT,
        category=CATEGORY_PLAYBACK,
        default=15,
        minimum=1,
        maximum=600,
        settings_field="skip_back_seconds",
        aliases=("jump", "seek", "rewind", "back"),
        describe=_seconds("Skip back"),
    ),
    define(
        "auto_skip_intro_seconds",
        "Skip the first:",
        "Jumps this far into an episode when it starts fresh. Never on resume, "
        "so a saved position is never lost under it, and zero means it does not "
        "happen at all.",
        kind=KIND_INT,
        category=CATEGORY_PLAYBACK,
        levels=(LEVEL_GLOBAL, LEVEL_SHOW),
        default=0,
        minimum=0,
        maximum=3600,
        settings_field="auto_skip_intro_seconds",
        aliases=("intro", "theme tune", "advert"),
        describe=_seconds("Skipping the intro"),
    ),
    define(
        "auto_skip_outro_seconds",
        "Stop this far before the end:",
        "Ends an episode early, treated exactly as if it had finished -- so "
        "auto-advance and delete-after-playing still happen. Zero means it does "
        "not happen at all.",
        kind=KIND_INT,
        category=CATEGORY_PLAYBACK,
        levels=(LEVEL_GLOBAL, LEVEL_SHOW),
        default=0,
        minimum=0,
        maximum=3600,
        settings_field="auto_skip_outro_seconds",
        aliases=("outro", "credits", "trailer"),
        describe=_seconds("Stopping before the end"),
    ),
    define(
        "continue_after_queue",
        "&Play the next episode in the Play Queue",
        settings_help.HELP["continue_queue"],
        category=CATEGORY_PLAYBACK,
        default=True,
        settings_field="continue_after_queue",
        aliases=("auto advance", "keep playing", "next"),
    ),
    define(
        "continue_after_group",
        "When the queue is empty, keep going with the same podcast",
        settings_help.HELP["continue_group"],
        category=CATEGORY_PLAYBACK,
        default=False,
        settings_field="continue_after_group",
        aliases=("binge", "auto advance", "keep playing"),
    ),
    define(
        "prebuffer_next",
        "Start loading the ne&xt episode before this one ends",
        settings_help.HELP["prebuffer"],
        category=CATEGORY_PLAYBACK,
        default=False,
        settings_field="prebuffer_next",
        aliases=("gapless", "buffer", "preload"),
    ),
    define(
        "playback_cache",
        "Keep streamed episodes ready while they play",
        settings_help.HELP["playback_cache"],
        category=CATEGORY_PLAYBACK,
        default=True,
        settings_field="playback_cache",
        aliases=("stream", "buffer", "dropped connection"),
    ),
    define(
        "chapters_auto",
        "Work out chapters:",
        "When Cast should try to find chapters an episode did not publish. It "
        "never touches an episode that came with its own, and switching it off "
        "entirely means the subject is never raised again.",
        kind=KIND_CHOICE,
        category=CATEGORY_PLAYBACK,
        default="when_downloaded",
        choices=choices(
            ("off", "Never"),
            ("when_downloaded", "When I download an episode"),
            ("always", "Always"),
        ),
        settings_field="chapters_auto",
        aliases=("chapters", "sections", "inference"),
    ),
    define(
        "chapters_effort",
        "How long to spend looking:",
        "How long a chapter scan may take. Everything else about the scan "
        "derives from this one choice rather than from a page of knobs -- it "
        "does not decide whether to scan at all, which is the setting above.",
        kind=KIND_CHOICE,
        category=CATEGORY_PLAYBACK,
        default="thorough",
        choices=choices(
            ("quick", "Not long"), ("thorough", "A while"), ("deep", "As long as it takes")
        ),
        settings_field="chapters_effort",
        aliases=("chapters", "budget", "scan"),
    ),
    define(
        "chapters_use_show_notes",
        "Look for chapters in the show notes",
        "Reads timestamps out of the episode's own notes, which costs nothing "
        "and is usually right. Switching it off disables that source rather "
        "than merely preferring another.",
        category=CATEGORY_PLAYBACK,
        default=True,
        settings_field="chapters_use_show_notes",
        aliases=("chapters", "show notes"),
    ),
    define(
        "chapters_use_transcript",
        "Look for chapters in the transcript",
        "Uses a transcript when one is available. It never fetches audio and "
        "never transcribes anything itself -- that is the setting below.",
        category=CATEGORY_PLAYBACK,
        default=True,
        settings_field="chapters_use_transcript",
        aliases=("chapters", "transcript"),
    ),
    define(
        "chapters_scan_audio",
        "Listen to the audio to find chapters",
        "Lets a chapter scan transcribe the audio when nothing else worked. "
        "This is the expensive one: switching it off means it never happens, "
        "not that it happens later.",
        category=CATEGORY_PLAYBACK,
        default=True,
        settings_field="chapters_scan_audio",
        aliases=("chapters", "transcribe", "whisper"),
    ),
    define(
        "chapters_name_sections",
        "Give worked-out chapters names",
        "Asks a model to name the sections it found. It sends text only, never "
        "audio, and it is off until asked for.",
        category=CATEGORY_PLAYBACK,
        default=False,
        settings_field="chapters_name_sections",
        aliases=("chapters", "ai", "titles"),
    ),
    define(
        "chapters_announce",
        "Say when a chapter scan finishes",
        "One announcement when a scan is done. It never interrupts playback, "
        "and it says nothing at all when a scan found nothing.",
        category=CATEGORY_PLAYBACK,
        default=True,
        settings_field="chapters_announce",
        aliases=("chapters", "announce"),
    ),
    define(
        "chapters_preview_seconds",
        "Chapter preview length:",
        "How much either side of a chapter mark Preview plays. It only affects "
        "the preview -- jumping to a chapter always starts exactly at the mark.",
        kind=KIND_INT,
        category=CATEGORY_PLAYBACK,
        default=10,
        minimum=3,
        maximum=60,
        settings_field="chapters_preview_seconds",
        aliases=("chapters", "preview"),
        describe=_seconds("Chapter preview"),
    ),
)

__all__ = ["SETTINGS"]
