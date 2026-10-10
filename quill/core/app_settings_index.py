"""What Quill Converter, the Media Player and Quill Inkwell can be set to do.

The declarative half of *Find a setting* for the three apps that had no
Preferences window until qc.md X-01 (see :mod:`quill.core.settings_finder`).
Every row is a setting that already exists -- nothing here invents one -- with
the exact label a person sees, the words they might use for it instead, and,
when it does not live in Preferences itself, the place it does.

Rows with an empty ``area`` are drawn in the app's Preferences window under
the same ``key``; ``tests/unit/core/test_app_settings_index.py`` holds every
Preferences row and these rows to each other, so a setting cannot be added to
one and forgotten in the other. Rows with an ``area`` live elsewhere, and
choosing one closes Preferences and carries focus there.

No ``wx``: this is data, and a test can read all of it without a window.
"""

from __future__ import annotations

from quill.core.settings_finder import SettingEntry

__all__ = ["CONVERTER_SETTINGS", "INKWELL_SETTINGS", "PLAYER_SETTINGS", "entries_for"]

_MAIN = "the main window"
_ADVANCED = "the main window's Advanced Options"
_EFFECTS = "the Custom Effects window"

CONVERTER_SETTINGS: tuple[SettingEntry, ...] = (
    # --- Preferences itself ----------------------------------------------------
    SettingEntry(
        "converter.open_folder_when_done",
        "Open the output folder when a conversion finishes",
        description="Also Convert > Open Output Folder When Done, Ctrl+Shift+W.",
        aliases=("explorer", "show results", "when done", "finished"),
    ),
    SettingEntry(
        "converter.show_advanced",
        "Show Advanced Options in the main window",
        description="Also View > Advanced Options, Ctrl+Alt+V.",
        aliases=("advanced", "encoder", "more options", "hide"),
    ),
    # --- the main window -------------------------------------------------------
    SettingEntry(
        "converter.format",
        "Convert to",
        _MAIN,
        "The format every queued file becomes.",
        ("format", "output format", "mp3", "wav", "flac", "m4b", "aac", "ogg", "video"),
    ),
    SettingEntry(
        "converter.preset",
        "Preset",
        _MAIN,
        "Quality settings chosen for a purpose.",
        ("quality", "profile", "audiobook", "speech", "music"),
    ),
    SettingEntry(
        "converter.effect",
        "Effects",
        _MAIN,
        "What to do to the sound on the way through.",
        ("recipe", "noise", "hum", "loudness", "podcast", "acx", "clean up", "dialogue"),
    ),
    SettingEntry(
        "converter.chapters",
        "Chapter marks",
        _MAIN,
        "Where the converted files' chapter marks come from.",
        ("chapters", "cue", "pauses", "split"),
    ),
    SettingEntry(
        "converter.dest_dir",
        "Output folder",
        _MAIN,
        "Where the converted files are written.",
        ("destination", "save to", "where", "directory", "location"),
    ),
    # --- Advanced Options ------------------------------------------------------
    SettingEntry(
        "converter.adv_bitrate",
        "Bit rate (size and quality)",
        _ADVANCED,
        "The bit rate for compressed formats.",
        ("bitrate", "kbps", "file size"),
    ),
    SettingEntry(
        "converter.adv_rate",
        "Sample rate",
        _ADVANCED,
        "Resample every file to this rate.",
        ("hz", "khz", "resample", "44100", "48000"),
    ),
    SettingEntry(
        "converter.adv_channels",
        "Channels",
        _ADVANCED,
        "Mono or stereo.",
        ("mono", "stereo"),
    ),
    SettingEntry(
        "converter.adv_depth",
        "Bit depth",
        _ADVANCED,
        "16, 24 or 32-bit float for lossless formats.",
        ("16-bit", "24-bit", "32-bit", "float"),
    ),
    SettingEntry(
        "converter.on_existing",
        "If a file already exists",
        _ADVANCED,
        "Number the new file, skip it, or replace the old one.",
        ("overwrite", "replace", "skip", "rename", "conflict", "collision", "duplicate"),
    ),
    SettingEntry(
        "converter.adv_polish",
        "Broadcast polish",
        _ADVANCED,
        "The OptiLab Core processing engine.",
        ("optilab", "leveler", "limiter", "stream polish"),
    ),
    SettingEntry(
        "converter.recurse",
        "Look in subfolders too",
        _ADVANCED,
        "Convert the files in a queued folder's subfolders as well.",
        ("recursive", "subfolders", "folder layout"),
    ),
    # --- Custom Effects --------------------------------------------------------
    SettingEntry(
        "converter.custom_effects",
        "Custom effects",
        _EFFECTS,
        "Every effect on one page.",
        ("equalizer", "bass", "treble", "de-ess", "compression", "gain", "speed", "fade"),
    ),
    SettingEntry(
        "converter.trim",
        "Keep only part of each file",
        _EFFECTS,
        "Where each converted file starts and ends.",
        ("trim", "cut", "start", "end", "clip"),
    ),
)

_AUDIO_TAB = "the Audio tab of the main window"
_TRANSPORT = "the player controls in the main window"
_OUTPUT = "the Audio Output Device window"

PLAYER_SETTINGS: tuple[SettingEntry, ...] = (
    # --- Preferences itself: this session only ----------------------------------
    SettingEntry(
        "player.compact",
        "Compact mode",
        description="Hide everything but the player controls. Also View, Ctrl+Alt+K.",
        aliases=("small", "minimal", "hide"),
    ),
    SettingEntry(
        "player.magical",
        "Magical mode",
        description="Also View, Ctrl+Shift+G.",
        aliases=("magic",),
    ),
    SettingEntry(
        "player.on_top",
        "Always on top",
        description="Keep the window above others. Also View, Ctrl+Shift+T.",
        aliases=("stay on top", "float", "topmost"),
    ),
    SettingEntry(
        "player.sleep",
        "Sleep timer",
        description="Pause after a while, or at the end of the chapter. Also Playback.",
        aliases=("sleep", "stop after", "bedtime", "end of chapter"),
    ),
    # --- Preferences itself: saved -----------------------------------------------
    SettingEntry(
        "player.output_device",
        "Audio Output Device",
        description="Which sound card the book plays out of. Also Playback, Ctrl+Shift+K.",
        aliases=("speakers", "headphones", "sound card", "device"),
    ),
    # --- the main window ---------------------------------------------------------
    SettingEntry(
        "player.speed",
        "Playback speed",
        _TRANSPORT,
        "How fast the book plays.",
        ("speed", "rate", "faster", "slower", "tempo"),
    ),
    SettingEntry(
        "player.volume",
        "Volume",
        _TRANSPORT,
        "How loud the book plays.",
        ("loud", "quiet", "level"),
    ),
    SettingEntry(
        "player.eq_preset",
        "Equalizer preset",
        _AUDIO_TAB,
        "A ready-made shape for the ten band sliders.",
        ("equalizer", "eq", "voice", "bass", "treble", "night", "podcast"),
    ),
    SettingEntry(
        "player.eq_bands",
        "Equalizer bands",
        _AUDIO_TAB,
        "Ten sliders, each a band's gain in decibels.",
        ("hz", "khz", "decibels", "gain", "sliders"),
    ),
    SettingEntry(
        "player.boost",
        "Volume boost",
        _AUDIO_TAB,
        "Extra gain for a quiet recording.",
        ("louder", "gain", "quiet recording", "db"),
    ),
    SettingEntry(
        "player.normalize",
        "Normalize loudness",
        _AUDIO_TAB,
        "Even out loud and quiet parts.",
        ("loudness", "level", "even out"),
    ),
    SettingEntry(
        "player.skip_silence",
        "Skip silence",
        _AUDIO_TAB,
        "Pass over long pauses.",
        ("silence", "pauses", "gaps"),
    ),
)

INKWELL_SETTINGS: tuple[SettingEntry, ...] = (
    SettingEntry(
        "inkwell.expansion_enabled",
        "Expand in other applications",
        description="The master switch. Also Abbreviations, Ctrl+Shift+E.",
        aliases=("pause", "on", "off", "enable", "disable", "system-wide"),
    ),
    SettingEntry(
        "inkwell.start_with_windows",
        "Start Quill Inkwell with Windows",
        description="Also Options, Ctrl+Alt+W.",
        aliases=("startup", "login", "sign in", "boot", "launch"),
    ),
    SettingEntry(
        "inkwell.start_in_tray",
        "Start minimized to the tray",
        description="Also Options, Ctrl+Alt+M.",
        aliases=("tray", "hidden", "minimized", "notification area"),
    ),
    SettingEntry(
        "inkwell.close_to_tray",
        "Close button keeps expanding",
        description="Closing the window leaves expansion running. Also Options, Ctrl+Alt+C.",
        aliases=("close", "tray", "exit", "keep running"),
    ),
    SettingEntry(
        "inkwell.paste",
        "Insert by pasting (for apps that drop typed text)",
        description="Borrow the clipboard to insert. Also Options, Ctrl+Alt+P.",
        aliases=("paste", "clipboard", "typing", "injection", "keystrokes"),
    ),
    SettingEntry(
        "inkwell.announce_expansions",
        "Announce every expansion",
        description="Speak a short confirmation. Also Options, Ctrl+Alt+A.",
        aliases=("speak", "speech", "confirm", "say"),
    ),
    SettingEntry(
        "inkwell.excluded_processes",
        "Excluded Applications",
        description="Programs where expansion never runs. Also Options, Ctrl+Alt+X.",
        aliases=("exclude", "block", "never", "programs", "password"),
    ),
)

_BY_APP = {
    "converter": CONVERTER_SETTINGS,
    "player": PLAYER_SETTINGS,
    "inkwell": INKWELL_SETTINGS,
}


def entries_for(app_key: str) -> tuple[SettingEntry, ...]:
    """The declared settings of *app_key* (``converter``, ``player``, ``inkwell``)."""
    return _BY_APP[app_key]
