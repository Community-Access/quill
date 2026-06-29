"""Static data tables for the settings registry (extracted for GATE-11).

These dataclasses and the ``SETTING_GROUPS`` / ``SETTING_SPECS`` tables were
lifted out of :mod:`quill.core.settings_registry` to keep that module under its
GATE-11 module-size budget. The registry re-exports every name defined here, so
the public import surface is unchanged. No ``wx`` imports; pure data.
"""

from __future__ import annotations

from dataclasses import dataclass

#: Bump when the exported document shape changes in a backward-incompatible way.
SCHEMA_VERSION = 1


@dataclass(frozen=True, slots=True)
class SettingSpec:
    """One tunable setting, mapped to a :class:`Settings` attribute."""

    key: str
    label: str
    group: str
    kind: str  # "bool" | "choice" | "int" | "float" | "text"
    description: str = ""
    choices: tuple[tuple[str, str], ...] = ()  # (stored value, human label)
    minimum: float | None = None
    maximum: float | None = None
    feature_id: str = ""
    keywords: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class SettingGroup:
    """A labelled cluster of settings, surfaced as one tab."""

    id: str
    title: str
    description: str = ""


def _ai_tts_voice_choices() -> tuple[tuple[str, str], ...]:
    """Build the AI Voice choice list (provider-prefixed) from the TTS catalogs.

    Falls back to a minimal pair if the optional AI modules cannot be imported,
    so the settings table never fails to load.
    """
    choices: list[tuple[str, str]] = [("", "Provider default")]
    try:
        from quill.core.ai.cloud_tts import provider_label, voices_for

        for provider in ("openai", "gemini", "elevenlabs"):
            label = provider_label(provider)
            for voice_id, voice_name in voices_for(provider):
                choices.append((voice_id, f"{label}: {voice_name}"))
    except Exception:  # noqa: BLE001 - keep settings loadable without the AI modules
        choices.extend([("nova", "OpenAI: Nova"), ("Kore", "Gemini: Kore")])
    return tuple(choices)


SETTING_GROUPS: tuple[SettingGroup, ...] = (
    SettingGroup("general", "General", "Appearance, window, and startup behavior."),
    SettingGroup("editing", "Editing", "How the editor behaves while you write."),
    SettingGroup(
        "navigation",
        "Navigation and QUILL Key",
        "Structural movement, browse mode, and the QUILL key.",
    ),
    SettingGroup(
        "accessibility",
        "Accessibility and Announcements",
        "Screen-reader announcements and accessibility behavior.",
    ),
    SettingGroup("read_aloud", "Read Aloud", "Spoken playback engine and voice tuning."),
    SettingGroup("ai", "AI and Assistant", "Writing assistant tone and behavior."),
    SettingGroup(
        "transcription",
        "Transcription",
        "Offline speech-model and provider behavior.",
    ),
    SettingGroup(
        "watch",
        "Watch Folders",
        "Default behavior for watched-folder automation.",
    ),
    SettingGroup(
        "integration",
        "Integration and Context Menu",
        "File-manager right-click verbs and how QUILL is offered on files.",
    ),
    SettingGroup(
        "admin",
        "Administration",
        "Updates, security, developer tools, and settings management.",
    ),
    SettingGroup(
        "braille",
        "Braille Mode",
        "Page geometry, page-break heuristic, sidecar, and announcements for braille.",
    ),
    SettingGroup(
        "spelling",
        "Spelling Review",
        "Behavior of the F7 guided spelling review dialog.",
    ),
    SettingGroup(
        "experimental",
        "Experimental",
        (
            "Opt-in, for-testing options that change how the editor is built. "
            "Restart QUILL after changing anything here so it applies everywhere."
        ),
    ),
)

_GROUP_IDS = {group.id for group in SETTING_GROUPS}


SETTING_SPECS: tuple[SettingSpec, ...] = (
    # --- General -----------------------------------------------------------
    SettingSpec(
        "theme",
        "Theme",
        "general",
        "choice",
        "Overall light or dark appearance.",
        choices=(("system", "System"), ("light", "Light"), ("dark", "Dark")),
        keywords=("dark mode", "light", "appearance", "color"),
    ),
    SettingSpec(
        "title_bar_path_mode",
        "Title bar path",
        "general",
        "choice",
        "Show just the file name or the full path in the title bar.",
        choices=(("name", "File name only"), ("full_path", "Full path")),
        keywords=("title", "path", "filename"),
    ),
    SettingSpec(
        "dirty_title_style",
        "Unsaved-change title style",
        "general",
        "choice",
        "How the title bar marks a document with unsaved changes.",
        choices=(
            ("text", "Text"),
            ("asterisk", "Asterisk"),
            ("asterisk_text", "Asterisk and text"),
        ),
        keywords=("modified", "dirty", "asterisk", "unsaved"),
    ),
    SettingSpec(
        "tray_enabled",
        "Enable system tray mode",
        "general",
        "bool",
        "Keep QUILL available from the system tray.",
        keywords=("tray", "notification area", "minimize"),
    ),
    SettingSpec(
        "show_tab_control",
        "Show tab control",
        "general",
        "bool",
        "Show a tab strip for open documents.",
        keywords=("tabs", "documents"),
    ),
    SettingSpec(
        "start_with_no_document_open",
        "Start with no document open",
        "general",
        "bool",
        "Open to an empty workspace instead of restoring a document.",
        keywords=("startup", "blank", "empty"),
    ),
    SettingSpec(
        "preview_browser",
        "Preview browser",
        "general",
        "text",
        "Which browser opens HTML previews.",
        keywords=("preview", "browser", "html"),
    ),
    SettingSpec(
        "auto_side_preview",
        "Open preview beside the editor",
        "general",
        "bool",
        "Show HTML previews in a side pane instead of a separate window.",
        keywords=("preview", "side", "pane", "html"),
    ),
    SettingSpec(
        "recent_files_limit",
        "Recent files to remember",
        "general",
        "int",
        "How many entries the Recent Files list keeps (1 to 50).",
        minimum=1,
        maximum=50,
        keywords=("recent", "history", "files"),
    ),
    SettingSpec(
        "recent_files_auto_clear_missing",
        "Drop missing recent files automatically",
        "general",
        "bool",
        "Remove Recent Files entries whose file no longer exists, but only on "
        "fixed internal drives -- never on removable, USB, or network drives "
        "(where a missing file usually means the drive is disconnected).",
        keywords=("recent", "history", "files", "missing", "clean up"),
    ),
    SettingSpec(
        "first_line_as_title",
        "Suggest a filename from the first line",
        "general",
        "bool",
        "When you save an untitled document, pre-fill the Save dialog with a name "
        "taken from the document's first line. Works across formats and strips "
        "leading markup (a Markdown heading, a quote, or a list bullet).",
        keywords=("title", "filename", "first line", "save", "name", "heading"),
    ),
    SettingSpec(
        "language",
        "Interface language",
        "general",
        "text",
        "BCP 47 language tag for the UI (e.g. 'en', 'fr', 'es'). "
        "Leave blank to use the operating-system language.",
        keywords=("language", "locale", "translation", "interface"),
    ),
    SettingSpec(
        "confirm_destructive_actions",
        "Confirm destructive actions",
        "general",
        "bool",
        "Ask before actions that discard work, such as clearing or overwriting.",
        keywords=("confirm", "prompt", "destructive", "safety"),
    ),
    SettingSpec(
        "startup_folder",
        "Default file-open folder",
        "general",
        "text",
        "Initial folder for Open and Save As dialogs. Leave blank to use the Documents folder.",
        keywords=("startup folder", "default folder", "open folder", "file dialog", "start folder"),
    ),
    SettingSpec(
        "use_simple_file_dialog",
        "Use simple file open dialog",
        "general",
        "bool",
        "When enabled, File > Open... opens a keyboard-friendly file picker "
        "with a small filter, recent locations, and a hidden-files toggle, "
        "instead of the standard Windows file open dialog. The simple "
        "dialog includes a Use Windows Dialog button for edge cases.",
        keywords=(
            "simple",
            "open",
            "dialog",
            "file",
            "screen reader",
            "accessibility",
            "keyboard",
        ),
    ),
    SettingSpec(
        "default_new_document_format",
        "Default new-document format",
        "general",
        "choice",
        "The format a brand-new document starts in.",
        choices=(
            ("markdown", "Markdown"),
            ("text", "Plain text"),
            ("html", "HTML"),
        ),
        keywords=("new document", "format", "default"),
    ),
    SettingSpec(
        "default_export_preset",
        "Default export preset",
        "general",
        "choice",
        "The format pre-selected in the export dialog.",
        choices=(
            ("html", "HTML"),
            ("markdown", "Markdown"),
            ("pdf", "PDF"),
            ("docx", "Word"),
            ("epub", "EPUB"),
            ("text", "Plain text"),
        ),
        keywords=("export", "preset", "default", "format"),
    ),
    # --- Editing -----------------------------------------------------------
    SettingSpec(
        "soft_wrap",
        "Enable soft wrap",
        "editing",
        "bool",
        "Wrap long lines to the window width.",
        keywords=("wrap", "word wrap", "lines"),
    ),
    SettingSpec(
        "plain_text_with_formatting",
        "Saving formatted text as plain text",
        "editing",
        "choice",
        (
            "What QUILL does when a document that carries hidden formatting (fonts, "
            "colours, alignment) is saved as plain text. An Illumination is a small "
            "<name>.illumination sidecar that keeps the formatting so the clean .txt "
            "round-trips it in QUILL, while staying plain for every other tool."
        ),
        choices=(
            ("ask", "Ask each time (keep formatting, illuminate, or save plain)"),
            ("illuminate", "Always save an Illumination sidecar"),
            ("plain", "Save plain text and drop the formatting"),
        ),
        keywords=("plain text", "illumination", "formatting", "sidecar", "preserve"),
    ),
    SettingSpec(
        "language_detection_mode",
        "Auto-detect document language",
        "editing",
        "choice",
        (
            "Detect the programming or markup language when you paste or type code "
            "into a plain text or untitled document, so you get that language's "
            "editing characteristics. Never overrides a real file extension or a "
            "language you set yourself."
        ),
        choices=(
            ("off", "Off"),
            ("hint", "Hint in the status bar only"),
            ("prompt", "Suggest and announce, you confirm"),
            ("auto", "Switch automatically"),
        ),
        keywords=(
            "language",
            "detect",
            "auto",
            "syntax",
            "paste",
            "html",
            "markdown",
            "code",
            "profile",
        ),
    ),
    SettingSpec(
        "wrap_find",
        "Wrap find searches",
        "editing",
        "bool",
        "Continue a search from the top after reaching the end.",
        keywords=("find", "search", "wrap"),
    ),
    SettingSpec(
        "indent_with_tabs",
        "Indent with tabs",
        "editing",
        "bool",
        "Insert tab characters instead of spaces when indenting.",
        keywords=("tab", "indent", "spaces"),
    ),
    SettingSpec(
        "indent_size",
        "Indent size",
        "editing",
        "int",
        "Number of spaces per indent level (1 to 8).",
        minimum=1,
        maximum=8,
        keywords=("indent", "spaces", "width"),
    ),
    SettingSpec(
        "spellcheck_as_you_type",
        "Spell check as you type",
        "editing",
        "bool",
        "Flag misspellings while you write.",
        feature_id="core.spellcheck",
        keywords=("spelling", "spell check", "typos"),
    ),
    SettingSpec(
        "spell_check_before_save",
        "Spell check a document before saving",
        "editing",
        "bool",
        "Open the spelling review (F7) when you save, so you can correct "
        "misspellings before the file is written. Off by default.",
        feature_id="core.spellcheck",
        keywords=("spelling", "spell check", "save", "proofread", "before saving"),
    ),
    SettingSpec(
        "intellisense_as_you_type",
        "Word prediction and tag IntelliSense",
        "editing",
        "bool",
        "Suggest words and tags while you type.",
        feature_id="core.intellisense",
        keywords=("autocomplete", "prediction", "intellisense"),
    ),
    SettingSpec(
        "snippet_trigger_expansion",
        "Expand snippet triggers while typing",
        "editing",
        "bool",
        "Expand a snippet trigger when you type its delimiter.",
        keywords=("snippet", "expand", "template"),
    ),
    SettingSpec(
        "abbreviation_expansion",
        "Abbreviation expansion",
        "editing",
        "bool",
        "Automatically expand abbreviations as you type (e.g. 'btw ' becomes 'by the way ').",
        keywords=("abbreviation", "shorthand", "textexpander", "autocorrect", "expand"),
    ),
    SettingSpec(
        "abbreviation_expansion_sound",
        "Play sound on abbreviation expansion",
        "editing",
        "bool",
        "Play a sound each time an abbreviation is expanded.",
        keywords=("abbreviation", "sound", "audio", "beep"),
    ),
    SettingSpec(
        "abbreviation_expansion_sound_file",
        "Abbreviation expansion sound file",
        "editing",
        "text",
        "Path to a .wav file played on expansion. Leave blank for the default system sound.",
        keywords=("abbreviation", "sound", "wav", "audio"),
    ),
    SettingSpec(
        "list_auto_fill_numbers",
        "Auto-fill numbered list markers",
        "editing",
        "bool",
        "When inserting a Markdown numbered list, fill in the leading "
        "'1. ', '2. ', '3. ' markers for each item instead of leaving the "
        "first marker only. Auto-fill is also enabled automatically while "
        "the caret is in a Markdown document, or for 5 minutes after you "
        "toggle a numbered list on the active document.",
        keywords=("list", "numbered", "auto", "fill", "markdown"),
        feature_id="core.format",
    ),
    SettingSpec(
        "abbreviation_backspace_behavior",
        "Backspace after expansion",
        "editing",
        "choice",
        "What to do when you press Backspace immediately after an abbreviation expands.",
        choices=(
            ("delete", "Delete the expanded text"),
            ("revert", "Revert to the typed abbreviation"),
        ),
        keywords=("abbreviation", "backspace", "undo", "delete", "revert"),
    ),
    SettingSpec(
        "persistent_undo",
        "Enable persistent undo",
        "editing",
        "bool",
        "Keep undo history across sessions.",
        keywords=("undo", "history", "persistent"),
    ),
    SettingSpec(
        "markdown_clipboard_format",
        "Markdown clipboard format",
        "editing",
        "choice",
        "Format used when copying Markdown with source.",
        choices=(("html", "HTML"), ("rtf", "Rich text")),
        keywords=("clipboard", "copy", "markdown", "format"),
    ),
    SettingSpec(
        "csv_open_mode",
        "How to open CSV files",
        "editing",
        "choice",
        "Open CSV files as plain text, as a grid, or ask each time.",
        choices=(("prompt", "Ask each time"), ("text", "Plain text"), ("grid", "Grid")),
        keywords=("csv", "open", "grid", "table"),
    ),
    SettingSpec(
        "word_open_mode",
        "How to open Word files",
        "editing",
        "choice",
        "Open Word files as plain text, as structured content, or ask each time.",
        choices=(
            ("prompt", "Ask each time"),
            ("text", "Plain text"),
            ("structured", "Structured"),
        ),
        keywords=("word", "docx", "open", "structured"),
    ),
    # editor_surface spec intentionally omitted while core.rich_text_lens is
    # locked_off — re-add choices=(..., ("rich", "Rich text lens")) when ready.
    SettingSpec(
        "save_as_surface_sync",
        "Reload after Save As to match the format",
        "editing",
        "choice",
        "After Save As changes the file type, optionally reload the file so the "
        "editing surface (Rich text or plain text) matches the new format. "
        "Reloading replaces the editor contents with the saved file.",
        choices=(
            ("prompt", "Ask each time"),
            ("always", "Reload automatically"),
            ("never", "Keep current surface"),
        ),
        keywords=("save as", "convert", "rtf", "reload", "surface", "format"),
    ),
    SettingSpec(
        "plain_text_link_style",
        "Links in plain-text export",
        "editing",
        "choice",
        "How Markdown links are written when you save or export as plain text. "
        "Keeping the URL avoids losing where a link pointed.",
        choices=(
            ("text", "Link text only"),
            ("text_url", "Link text and URL"),
            ("url", "URL only"),
            ("markdown", "Keep Markdown link"),
        ),
        keywords=("link", "url", "plain text", "export", "convert"),
    ),
    SettingSpec(
        "autosave_interval_seconds",
        "Autosave interval (seconds)",
        "editing",
        "int",
        "How often the editor autosaves the open document (5 to 600).",
        minimum=5,
        maximum=600,
        keywords=("autosave", "interval", "timing", "save"),
    ),
    SettingSpec(
        "autoformat_smart_quotes",
        "Autoformat straight quotes to curly",
        "editing",
        "bool",
        "Convert straight quotes to typographic quotes while you type.",
        keywords=("autoformat", "quotes", "typography", "smart quotes"),
    ),
    SettingSpec(
        "autoformat_dashes",
        "Autoformat double hyphen to dash",
        "editing",
        "bool",
        "Convert a double hyphen to an en or em dash while you type.",
        keywords=("autoformat", "dash", "hyphen", "typography"),
    ),
    # #262: Pandoc Import / Export batch conversion defaults. These show in
    # Preferences -> Editing; the wizard reads them as starting values and
    # lets the user override per batch. ``import_export_last_folder`` is
    # intentionally not exposed in Preferences (it is a session memory for
    # the folder picker, not a user-tunable policy).
    SettingSpec(
        "import_export_recursive",
        "Include subfolders in batch conversion",
        "editing",
        "bool",
        "When the Batch Conversion wizard runs over a folder, descend into subfolders.",
        keywords=("pandoc", "batch", "import", "export", "convert", "recursive", "subfolders"),
    ),
    SettingSpec(
        "import_export_overwrite",
        "Overwrite behaviour for batch conversion",
        "editing",
        "choice",
        "What to do when an output file already exists during a batch run.",
        choices=(
            ("ask", "Ask each time"),
            ("never", "Never overwrite"),
            ("always", "Always overwrite"),
        ),
        keywords=("pandoc", "batch", "import", "export", "convert", "overwrite"),
    ),
    SettingSpec(
        "import_export_output_layout",
        "Default output layout for batch conversion",
        "editing",
        "choice",
        "Where the wizard puts converted files by default.",
        choices=(
            ("subfolder", "Output subfolder per source folder"),
            ("same_folder", "Same folder as source"),
        ),
        keywords=("pandoc", "batch", "import", "export", "convert", "output", "layout"),
    ),
    # --- Navigation and QUILL key -----------------------------------------
    SettingSpec(
        "browse_mode_wrap",
        "Wrap QUILL browse navigation",
        "navigation",
        "bool",
        "Wrap to the other end at document boundaries while browsing.",
        feature_id="core.navigate",
        keywords=("browse", "wrap", "navigation"),
    ),
    SettingSpec(
        "browse_mode_feedback",
        "QUILL browse feedback",
        "navigation",
        "choice",
        "How browse-mode movement is signalled.",
        choices=(
            ("speech", "Speech only"),
            ("sound", "Sound only"),
            ("both", "Speech and sound"),
            ("none", "Silent"),
        ),
        feature_id="core.navigate",
        keywords=("browse", "feedback", "sound", "speech"),
    ),
    SettingSpec(
        "browse_mode_move_detail",
        "QUILL browse move detail",
        "navigation",
        "choice",
        "How much detail is spoken after a browse-mode move completes.",
        choices=(
            ("position", "Line and column"),
            ("line", "Line only"),
            ("none", "Say nothing"),
        ),
        feature_id="core.navigate",
        keywords=("browse", "move", "detail", "line", "position", "announcement"),
    ),
    SettingSpec(
        "browse_mode_preload_cache",
        "Preload QUILL browse cache in background",
        "navigation",
        "bool",
        "Build the navigation cache ahead of first use.",
        feature_id="core.navigate",
        keywords=("browse", "cache", "preload", "quick nav"),
    ),
    SettingSpec(
        "quill_key_timeout_seconds",
        "QUILL key prefix timeout (seconds)",
        "navigation",
        "float",
        (
            "How long the QUILL key prefix waits for a follow-on key before "
            "expiring. 0 means no timeout."
        ),
        minimum=0.0,
        maximum=60.0,
        keywords=("quill key", "timeout", "prefix"),
    ),
    SettingSpec(
        "browse_mode_followon_timeout",
        "Browse mode follow-on timeout",
        "navigation",
        "choice",
        (
            "How long browse mode stays active between follow-on keypresses "
            "after entering with N. Pick a preset or choose Custom to set "
            "your own value in milliseconds."
        ),
        choices=(
            ("instant", "Instant (0 ms)"),
            ("fast", "Fast (1500 ms)"),
            ("normal", "Normal (4000 ms)"),
            ("slow", "Slow (8000 ms)"),
            ("custom", "Custom..."),
            ("unlimited", "Unlimited (no timeout)"),
        ),
        feature_id="core.navigate",
        keywords=("quill key", "browse", "timeout", "follow-on"),
    ),
    SettingSpec(
        "browse_mode_followon_custom_ms",
        "Browse mode follow-on timeout — custom value (milliseconds)",
        "navigation",
        "int",
        ("Used when 'Browse mode follow-on timeout' is set to Custom. 0 means no timeout."),
        minimum=0,
        maximum=60000,
        feature_id="core.navigate",
        keywords=("quill key", "browse", "timeout", "custom", "milliseconds"),
    ),
    # --- Accessibility -----------------------------------------------------
    # --- External file-change watch and safe reload (FEAT-19) --------------
    SettingSpec(
        "external_change_watch_enabled",
        "Watch the open file for external changes",
        "general",
        "bool",
        "Notice when another program changes or deletes the file you are editing "
        "and react safely instead of silently losing or overwriting your work.",
        keywords=("watch", "external", "reload", "file change", "conflict"),
    ),
    SettingSpec(
        "external_change_auto_reload_when_clean",
        "Reload automatically when you have no unsaved edits",
        "general",
        "bool",
        "When the file changes on disk and your buffer is unmodified, reload in "
        "place without moving the cursor. Turn off to be prompted instead.",
        keywords=("reload", "auto", "external", "clean"),
    ),
    SettingSpec(
        "external_change_prompt_on_conflict",
        "Ask before discarding unsaved edits on a conflict",
        "general",
        "bool",
        "When the file changes on disk while you have unsaved edits, offer reload, "
        "keep-mine, or compare. Your text is never overwritten silently.",
        keywords=("conflict", "prompt", "unsaved", "external", "reload"),
    ),
    SettingSpec(
        "external_change_debounce_ms",
        "External-change debounce (milliseconds)",
        "general",
        "int",
        "How long to wait after a change is seen before reacting, so a program "
        "writing a file in several steps is handled once (0 to 10000).",
        minimum=0,
        maximum=10000,
        keywords=("debounce", "external", "timing", "watch"),
    ),
    SettingSpec(
        "quick_nav_debounce_ms",
        "Quick Nav debounce (milliseconds)",
        "navigation",
        "int",
        "How long Quick Nav waits between keystrokes before searching (0 to 2000).",
        minimum=0,
        maximum=2000,
        feature_id="core.navigate",
        keywords=("quick nav", "debounce", "timing"),
    ),
    SettingSpec(
        "quick_nav_min_chars",
        "Quick Nav minimum characters",
        "navigation",
        "int",
        "How many characters Quick Nav needs before it starts matching (1 to 5).",
        minimum=1,
        maximum=5,
        feature_id="core.navigate",
        keywords=("quick nav", "threshold", "characters"),
    ),
    SettingSpec(
        "browse_mode_sticky",
        "Sticky browse mode",
        "navigation",
        "bool",
        "Keep browse mode active after moving instead of returning to editing.",
        feature_id="core.navigate",
        keywords=("browse", "sticky", "navigation"),
    ),
    SettingSpec(
        "quill_key_sound_enter",
        "Custom sound for browse mode entry (WAV file)",
        "navigation",
        "text",
        "WAV file played when entering QUILL browse mode. Blank for default beep.",
        keywords=("quill key", "sound", "earcon", "browse", "enter"),
    ),
    SettingSpec(
        "quill_key_sound_exit",
        "Custom sound for browse mode exit (WAV file)",
        "navigation",
        "text",
        "WAV file played when exiting QUILL browse mode. Blank for default beep.",
        keywords=("quill key", "sound", "earcon", "browse", "exit"),
    ),
    SettingSpec(
        "quill_key_sound_move",
        "Custom sound for browse navigation (WAV file)",
        "navigation",
        "text",
        "WAV file played on each QUILL browse move. Blank for default beep.",
        keywords=("quill key", "sound", "earcon", "browse", "move"),
    ),
    SettingSpec(
        "quill_key_sound_error",
        "Custom sound for browse not-found (WAV file)",
        "navigation",
        "text",
        "WAV file played when a QUILL browse target is not found. Blank for beep.",
        keywords=("quill key", "sound", "earcon", "browse", "error"),
    ),
    SettingSpec(
        "quick_nav_include_headings",
        "Include headings in Quick Nav",
        "navigation",
        "bool",
        "Offer headings as Quick Nav targets.",
        feature_id="core.navigate",
        keywords=("quick nav", "headings", "elements"),
    ),
    SettingSpec(
        "quick_nav_include_links",
        "Include links in Quick Nav",
        "navigation",
        "bool",
        "Offer links as Quick Nav targets.",
        feature_id="core.navigate",
        keywords=("quick nav", "links", "elements"),
    ),
    SettingSpec(
        "quick_nav_include_lists",
        "Include lists in Quick Nav",
        "navigation",
        "bool",
        "Offer lists as Quick Nav targets.",
        feature_id="core.navigate",
        keywords=("quick nav", "lists", "elements"),
    ),
    # --- Accessibility -----------------------------------------------------
    SettingSpec(
        "announcement_backend",
        "Announcement backend",
        "accessibility",
        "choice",
        "How spoken status announcements are delivered.",
        choices=(
            ("auto", "Automatic"),
            ("prism", "PRISM bridge"),
            ("status_only", "Status bar only"),
        ),
        feature_id="core.accessibility",
        keywords=("announcement", "screen reader", "speech"),
    ),
    SettingSpec(
        "announce_dialog_transitions",
        "Announce entering and leaving dialogs",
        "accessibility",
        "bool",
        'Speak "Entered"/"Exited" when a dialog box opens and closes. '
        "Turn off if your screen reader already announces dialogs.",
        feature_id="core.accessibility",
        keywords=("dialog", "announcement", "entered", "exited", "leaving"),
    ),
    SettingSpec(
        "announce_indent_depth",
        "Announce indentation depth on Tab",
        "accessibility",
        "bool",
        'Speak the new indent depth ("4 spaces" or "1 tab") when Tab or Shift+Tab '
        'indents, instead of just "Indented lines".',
        feature_id="core.accessibility",
        keywords=("indent", "tab", "spaces", "announcement", "depth"),
    ),
    SettingSpec(
        "spoken_echo_on_double_press",
        "Double-press to show the Spoken Echo",
        "accessibility",
        "bool",
        "Double-press an informational command (Describe Formatting, Document "
        "Summary, Context Help, Announce Contrast) to open the Spoken Echo review "
        "dialog instead of re-speaking. The dedicated Echo key always works.",
        feature_id="core.accessibility",
        keywords=("echo", "double-press", "review", "announcement", "virtualize"),
    ),
    SettingSpec(
        "editor_control_kind",
        "Editor control type (braille)",
        "accessibility",
        "choice",
        (
            "Which native control backs the editor. RichEdit is the default; some "
            "braille displays show the first character of every line in cell two "
            "with a rich control (the long-standing Microsoft Word quirk). "
            "'Plain edit, like Notepad' uses a simple control that avoids the "
            "offset and still reads correctly. Takes effect for documents opened "
            "after the change (restart to apply everywhere). Windows only."
        ),
        choices=(
            ("rich2", "RichEdit 3.0 (default)"),
            ("rich", "RichEdit 2.0 (older engine)"),
            ("plain", "Plain edit, like Notepad (best for braille)"),
        ),
        keywords=("braille", "richedit", "notepad", "plain", "jaws", "cell", "display"),
    ),
    SettingSpec(
        "announcement_trace_enabled",
        "Record announcement trace",
        "accessibility",
        "bool",
        "Log announcements for diagnostics (no document content is captured).",
        feature_id="core.accessibility",
        keywords=("trace", "diagnostics", "announcement"),
    ),
    SettingSpec(
        "announcement_startup_tips_enabled",
        "Speak startup readiness and theme contrast announcements",
        "accessibility",
        "bool",
        "When enabled, QUILL speaks the 'Ready' tip after startup and the "
        "contrast ratio after each theme change. Off by default to keep "
        "startup quiet; the announcements still appear in the status bar.",
        feature_id="core.accessibility",
        keywords=("announcement", "startup", "speech", "contrast"),
    ),
    SettingSpec(
        "verbosity_speech_enabled",
        "Speech channel (verbosity)",
        "accessibility",
        "bool",
        "Master gate for the speech output channel. When off, spoken "
        "announcements from built-in startup events and Quillin extensions "
        "are suppressed. The status bar still receives the same text so "
        "sighted and low-vision users see the information. Used as the "
        "shim for the 0.7.1 verbosity rebuild.",
        feature_id="core.accessibility",
        keywords=("speech", "verbosity", "channel", "announcement", "quiet"),
    ),
    SettingSpec(
        "announce_screen_reader_detected",
        "Speak screen-reader detection result at startup",
        "accessibility",
        "bool",
        "When enabled, speaks 'Detected screen reader: <name>. Adaptive "
        "hints enabled.' after the screen-reader probe finishes. Off by "
        "default to keep startup quiet; the result is still placed in the "
        "status bar.",
        feature_id="core.accessibility",
        keywords=("screen reader", "detection", "JAWS", "NVDA", "Narrator"),
    ),
    # --- Sound notifications (QSP) ----------------------------------------
    SettingSpec(
        "sound_enabled",
        "Enable sound notifications",
        "accessibility",
        "bool",
        "Play short earcon sounds for editing events (abbreviation expansion, save, search, etc.).",
        keywords=("sound", "audio", "earcon", "notification", "beep"),
    ),
    SettingSpec(
        "sound_pack_path",
        "Sound pack path",
        "accessibility",
        "text",
        "Path to a .qsp file or folder. Leave blank to use the bundled Ink pack.",
        keywords=("sound", "pack", "qsp", "earcon", "theme"),
    ),
    SettingSpec(
        "sound_volume",
        "Sound notification volume",
        "accessibility",
        "int",
        "Volume for earcon sounds (0 = silent, 100 = full).",
        minimum=0,
        maximum=100,
        keywords=("sound", "volume", "audio", "earcon"),
    ),
    SettingSpec(
        "sound_events_disabled",
        "Silenced sound events",
        "accessibility",
        "text",
        "Comma-separated list of sound event IDs to silence, e.g. transcription_word_inserted.",
        keywords=("sound", "disable", "mute", "earcon", "events"),
    ),
    SettingSpec(
        "verbosity_collapse_repeats",
        "Collapse repeated announcements",
        "accessibility",
        "bool",
        "Skip speaking the same announcement again when it repeats within a moment "
        "(for example, holding a key at a boundary). The status bar still updates.",
        keywords=("verbosity", "announcement", "repeat", "collapse", "spam", "duplicate"),
    ),
    SettingSpec(
        "verbosity_max_announcements_per_window",
        "Announcement budget (per 5 seconds)",
        "accessibility",
        "int",
        "Cap how many announcements are spoken in a 5-second window to avoid floods "
        "(0 means no cap). Suppressed announcements still appear on the status bar.",
        minimum=0,
        maximum=1000,
        keywords=("verbosity", "announcement", "budget", "limit", "flood", "throttle"),
    ),
    SettingSpec(
        "indent_tone_scale",
        "Indentation tones",
        "accessibility",
        "choice",
        "Play a pitched tone as the caret moves across indent levels. The tone rises "
        "as you go deeper and falls as you come back out. Choose the musical scale, or "
        "Off to disable.",
        choices=(
            ("", "Off"),
            ("pentatonic", "Pentatonic (no dissonance)"),
            ("whole_tone", "Whole tone (even steps)"),
            ("diatonic", "Diatonic C major (familiar)"),
            ("chromatic", "Chromatic (one semitone per level)"),
        ),
        keywords=("sound", "indent", "indentation", "tone", "pitch", "code", "earcon"),
    ),
    # --- Read Aloud --------------------------------------------------------
    SettingSpec(
        "announcement_verbosity",
        "Announcement verbosity",
        "accessibility",
        "choice",
        "Overall chattiness of spoken status announcements.",
        choices=(
            ("minimal", "Minimal"),
            ("normal", "Normal"),
            ("verbose", "Verbose"),
        ),
        feature_id="core.accessibility",
        keywords=("verbosity", "announcements", "chatty", "speech"),
    ),
    SettingSpec(
        "announce_wrap",
        "Announce search and navigation wrap",
        "accessibility",
        "bool",
        "Speak a notice when a search or navigation wraps around.",
        feature_id="core.accessibility",
        keywords=("announce", "wrap", "navigation"),
    ),
    SettingSpec(
        "announce_counts",
        "Announce word and character counts",
        "accessibility",
        "bool",
        "Speak word and character counts when they are requested.",
        feature_id="core.accessibility",
        keywords=("announce", "counts", "words"),
    ),
    SettingSpec(
        "announce_mode_changes",
        "Announce mode entry and expiry",
        "accessibility",
        "bool",
        "Speak when a mode such as browse or the QUILL key is entered or expires.",
        feature_id="core.accessibility",
        keywords=("announce", "mode", "browse", "quill key"),
    ),
    SettingSpec(
        "announce_spelling",
        "Announce spelling results",
        "accessibility",
        "bool",
        "Speak spelling feedback such as misspelling counts.",
        feature_id="core.accessibility",
        keywords=("announce", "spelling", "spell check"),
    ),
    SettingSpec(
        "announce_punctuation_level",
        "Spoken punctuation level",
        "accessibility",
        "choice",
        "How much punctuation announcements include.",
        choices=(
            ("none", "None"),
            ("some", "Some"),
            ("most", "Most"),
            ("all", "All"),
        ),
        feature_id="core.accessibility",
        keywords=("punctuation", "announce", "speech"),
    ),
    SettingSpec(
        "announcement_throttle_ms",
        "Announcement throttle (milliseconds)",
        "accessibility",
        "int",
        "Minimum gap between spoken announcements; 0 means no throttle (0 to 2000).",
        minimum=0,
        maximum=2000,
        feature_id="core.accessibility",
        keywords=("throttle", "announcements", "timing"),
    ),
    # --- Read Aloud --------------------------------------------------------
    SettingSpec(
        "read_aloud_engine",
        "Read Aloud engine",
        "read_aloud",
        "choice",
        "Speech engine used for read aloud.",
        choices=(
            ("sapi5", "Windows (SAPI 5)"),
            ("dectalk", "DECtalk"),
            ("piper", "Piper"),
            ("kokoro", "Kokoro"),
            ("espeak", "eSpeak"),
        ),
        feature_id="core.read_aloud",
        keywords=("read aloud", "tts", "voice", "engine"),
    ),
    SettingSpec(
        "ai_tts_provider",
        "AI Voice provider",
        "read_aloud",
        "choice",
        "Cloud provider for the AI Voice read-aloud and audio export actions. "
        "ElevenLabs is audio-export only and needs the optional elevenlabs extra.",
        choices=(
            ("openai", "OpenAI"),
            ("gemini", "Google Gemini"),
            ("elevenlabs", "ElevenLabs (export only)"),
        ),
        feature_id="core.read_aloud",
        keywords=("ai voice", "cloud tts", "openai", "gemini", "elevenlabs", "provider"),
    ),
    SettingSpec(
        "ai_tts_model",
        "AI Voice model",
        "read_aloud",
        "choice",
        "Model used by the selected AI Voice provider (blank uses the provider default).",
        choices=(
            ("", "Provider default"),
            ("tts-1", "OpenAI: tts-1 (fast)"),
            ("tts-1-hd", "OpenAI: tts-1-hd (higher quality)"),
            ("gemini-2.5-flash-preview-tts", "Gemini: 2.5 Flash (fast)"),
            ("gemini-2.5-pro-preview-tts", "Gemini: 2.5 Pro (higher quality)"),
            ("eleven_multilingual_v2", "ElevenLabs: Multilingual v2 (high quality)"),
            ("eleven_turbo_v2_5", "ElevenLabs: Turbo v2.5 (fast)"),
        ),
        feature_id="core.read_aloud",
        keywords=("ai voice", "cloud tts", "model"),
    ),
    SettingSpec(
        "ai_tts_voice",
        "AI Voice",
        "read_aloud",
        "choice",
        "Voice for the AI Voice provider (blank uses the provider default). "
        "Pick a voice that matches the selected provider.",
        choices=_ai_tts_voice_choices(),
        feature_id="core.read_aloud",
        keywords=("ai voice", "cloud tts", "voice"),
    ),
    SettingSpec(
        "read_aloud_rate",
        "Read Aloud rate",
        "read_aloud",
        "int",
        "Words per minute for the system engine (80 to 450).",
        minimum=80,
        maximum=450,
        feature_id="core.read_aloud",
        keywords=("read aloud", "rate", "speed"),
    ),
    SettingSpec(
        "read_aloud_volume",
        "Read Aloud volume",
        "read_aloud",
        "int",
        "Playback volume percentage (0 to 100).",
        minimum=0,
        maximum=100,
        feature_id="core.read_aloud",
        keywords=("read aloud", "volume"),
    ),
    SettingSpec(
        "read_aloud_pitch",
        "Read Aloud pitch",
        "read_aloud",
        "int",
        "Voice pitch (0 to 100).",
        minimum=0,
        maximum=100,
        feature_id="core.read_aloud",
        keywords=("read aloud", "pitch"),
    ),
    SettingSpec(
        "read_aloud_sentence_pause_ms",
        "Read Aloud sentence pause (milliseconds)",
        "read_aloud",
        "int",
        "Extra pause inserted between sentences during read aloud (0 to 2000).",
        minimum=0,
        maximum=2000,
        feature_id="core.read_aloud",
        keywords=("read aloud", "pause", "pacing", "timing"),
    ),
    SettingSpec(
        "read_aloud_follow_cursor",
        "Move cursor to follow Read Aloud",
        "read_aloud",
        "bool",
        "Select each sentence in the editor as it is spoken so you can follow "
        "along. Off by default, because with a screen reader running this makes "
        "it announce the selection over the Read Aloud voice. Turn it on if you "
        "want the cursor to track what is being read.",
        feature_id="core.read_aloud",
        keywords=("read aloud", "follow", "cursor", "highlight", "selection", "screen reader"),
    ),
    # --- AI and assistant --------------------------------------------------
    SettingSpec(
        "assistant_enabled",
        "Enable writing assistant",
        "ai",
        "bool",
        "Turn the local writing assistant on.",
        feature_id="future.ai",
        keywords=("assistant", "ai", "writing"),
    ),
    SettingSpec(
        "assistant_prompt_style",
        "Assistant prompt style",
        "ai",
        "choice",
        "The tone the assistant uses.",
        choices=(
            ("balanced", "Balanced"),
            ("concise", "Concise"),
            ("gentle", "Gentle"),
            ("technical", "Technical"),
        ),
        feature_id="future.ai",
        keywords=("assistant", "tone", "style", "prompt"),
    ),
    SettingSpec(
        "ai_chat_default_provider",
        "Ask AI default provider",
        "ai",
        "choice",
        "Default provider selected when the Ask AI dialog opens.",
        choices=(
            ("", "First available provider"),
            ("ollama", "Ollama (local)"),
            ("openai", "OpenAI"),
            ("claude", "Claude (Anthropic)"),
            ("openrouter", "OpenRouter"),
            ("gemini", "Google Gemini"),
            ("custom", "Custom endpoint"),
        ),
        keywords=("ai", "chat", "provider", "ollama", "openai", "claude", "openrouter", "gemini"),
    ),
    SettingSpec(
        "ai_chat_default_model",
        "Ask AI default model",
        "ai",
        "text",
        "Default model ID selected when the Ask AI dialog opens."
        " Leave blank to use the first model in the list.",
        keywords=("ai", "chat", "model"),
    ),
    SettingSpec(
        "ollama_base_url",
        "Ollama base URL",
        "ai",
        "text",
        "Base URL for the Ollama server. Default: http://localhost:11434",
        keywords=("ollama", "ai", "local", "url"),
    ),
    SettingSpec(
        "ai_prompt_default_model",
        "AI prompt default model",
        "ai",
        "text",
        "Default model ID used when running prompt-library prompts."
        " Leave blank to fall back to the Ask AI default model.",
        keywords=("ai", "prompt", "model", "prompt library", "grammar"),
    ),
    SettingSpec(
        "vision_default_prompt_style",
        "Default image description style",
        "ai",
        "text",
        "The prompt style used when describing images with AI. Defaults to 'accessibility'.",
        keywords=("vision", "image", "description", "prompt", "style", "accessibility"),
    ),
    SettingSpec(
        "vision_prompt_picker_enabled",
        "Show style picker before image description",
        "ai",
        "bool",
        "When enabled, a style picker appears before each image description"
        " so you can choose a different prompt style each time.",
        keywords=("vision", "image", "description", "picker", "style"),
    ),
    SettingSpec(
        "vision_disabled_builtin_styles",
        "Disabled built-in image prompt styles",
        "ai",
        "text",
        "List of built-in style IDs to hide from the style picker.",
        keywords=("vision", "image", "description", "disabled", "hidden"),
    ),
    SettingSpec(
        "vision_custom_prompts",
        "Custom image prompt styles",
        "ai",
        "text",
        "User-defined image description prompt styles.",
        keywords=("vision", "image", "description", "custom", "prompt"),
    ),
    # --- Bug reporting --------------------------------------------------------
    SettingSpec(
        "bug_reporter_name",
        "Bug reporter name",
        "general",
        "text",
        "Your name, pre-filled in the Report a Bug dialog for convenience.",
        keywords=("name", "bug", "report", "contact"),
    ),
    SettingSpec(
        "bug_reporter_email",
        "Bug reporter email",
        "general",
        "text",
        "Your contact email, pre-filled in the Report a Bug dialog for convenience.",
        keywords=("email", "bug", "report", "contact"),
    ),
    # #618: open the Report a Bug dialog in a separate, non-modal
    # window by default so users can alt-tab between the form and
    # the editor to document exact reproduction steps.
    SettingSpec(
        "report_bug_separate_window",
        "Open Report a Bug in a separate window",
        "general",
        "bool",
        "Open the Report a Bug dialog in its own non-modal window so you "
        "can alt-tab between the form and the editor to document exact "
        "reproduction steps. The editor stays interactive while the form "
        "is open. Turn this off to use the 0.5.0 modal-dialog behaviour.",
        keywords=("bug", "report", "dialog", "window", "modal", "modeless"),
    ),
    # #618: when the user submits a bug report, copy the report to
    # the clipboard and stop. The 0.5.0 default also opened a
    # browser to the GitHub "New Issue" page; that step is now
    # opt-in via this setting.
    SettingSpec(
        "report_bug_auto_open_browser",
        "Auto-open support form in browser after submit",
        "general",
        "bool",
        "After you submit a bug report from inside Quill, automatically "
        "open the support form in your default browser. The report is "
        "always copied to the clipboard; enable this if you would like "
        "Quill to also pop the GitHub 'New Issue' page with the report "
        "pre-filled. Disabled by default in 0.7.0 because the report is "
        "already on the clipboard and many users do not want a browser "
        "window opened on their behalf.",
        keywords=("bug", "report", "browser", "support", "github", "auto"),
    ),
    # #622: when an unhandled exception crashes QUILL, offer a dialog
    # that lets the user review a redacted preview and choose whether
    # to send the report to the developers. When disabled the local
    # crash file is still saved to app_data_dir()/crash-reports; the
    # dialog is the only opt-in here.
    SettingSpec(
        "auto_ask_crash_submit",
        "Offer to send crash reports automatically",
        "general",
        "bool",
        "When an unhandled exception closes Quill, show a dialog that "
        "lets you review a redacted summary (recent commands, "
        "environment, last frames of the traceback) and choose whether "
        "to send it to the developers. Your personal data is scrubbed "
        "before it leaves the machine, and nothing is sent unless you "
        "explicitly choose Send. The local crash file is always saved "
        "even when this option is off. Enabled by default during the "
        "beta phase so the team can hear about crashes without you "
        "having to opt in every time.",
        keywords=("crash", "report", "submit", "send", "diagnostics", "beta"),
    ),
    # --- Transcription -----------------------------------------------------
    SettingSpec(
        "bw_provider_mode",
        "Transcription provider preference",
        "transcription",
        "choice",
        "Prefer on-device or cloud transcription providers.",
        choices=(("local_first", "Local first"), ("cloud_first", "Cloud first")),
        feature_id="core.bw_providers",
        keywords=("transcription", "whisper", "provider", "cloud", "local"),
    ),
    SettingSpec(
        "bw_show_cloud_providers",
        "Show cloud transcription providers",
        "transcription",
        "bool",
        "List cloud providers alongside on-device ones.",
        feature_id="core.bw_providers",
        keywords=("transcription", "cloud", "providers"),
    ),
    SettingSpec(
        "bw_auto_open_status_page_on_download_start",
        "Auto-open Status Page on model download",
        "transcription",
        "bool",
        "Open the Status Page when a speech-model download starts.",
        feature_id="core.bw_transcription",
        keywords=("transcription", "status page", "download"),
    ),
    SettingSpec(
        "status_page_refresh_announcement_cadence",
        "Status page refresh announcements",
        "transcription",
        "choice",
        "How often the Status Page speaks refresh updates.",
        choices=(
            ("quiet", "Quiet"),
            ("normal", "Normal"),
            ("verbose", "Verbose"),
        ),
        feature_id="core.bw_transcription",
        keywords=("status page", "announcements", "cadence"),
    ),
    SettingSpec(
        "bw_safe_mode_lock",
        "BITS Whisperer safe mode lock",
        "transcription",
        "bool",
        "Block download and retry actions while keeping status surfaces.",
        feature_id="core.bw_transcription",
        keywords=("transcription", "safe mode", "lock"),
    ),
    SettingSpec(
        "voice_commands_enabled",
        "Hey QUILL voice commands",
        "transcription",
        "bool",
        "Enable Hey QUILL voice commands during dictation (e.g., 'Hey QUILL save file').",
        feature_id="core.voice_commands",
        keywords=("voice commands", "hey quill", "dictation", "speech"),
    ),
    # --- Watch Folders -----------------------------------------------------
    SettingSpec(
        "watch_folder_enabled",
        "Enable folder watching by default",
        "watch",
        "bool",
        "Turn watched-folder automation on when QUILL starts.",
        feature_id="core.watch",
        keywords=("watch", "folder", "automation", "monitor"),
    ),
    SettingSpec(
        "watch_folder_path",
        "Default watch folder",
        "watch",
        "text",
        "Folder to watch for new files when watching is enabled.",
        feature_id="core.watch",
        keywords=("watch", "folder", "path", "directory"),
    ),
    SettingSpec(
        "watch_folder_include_subfolders",
        "Include subfolders",
        "watch",
        "bool",
        "Also watch files inside nested subfolders.",
        feature_id="core.watch",
        keywords=("watch", "subfolders", "recursive"),
    ),
    SettingSpec(
        "watch_folder_process_existing",
        "Process existing files on start",
        "watch",
        "bool",
        "Run actions against files already present when watching begins.",
        feature_id="core.watch",
        keywords=("watch", "existing", "backlog"),
    ),
    SettingSpec(
        "watch_folder_auto_start",
        "Start watching automatically",
        "watch",
        "bool",
        "Begin watching the default folder as soon as QUILL launches.",
        feature_id="core.watch",
        keywords=("watch", "auto start", "startup"),
    ),
    SettingSpec(
        "watch_folder_poll_interval_seconds",
        "Poll interval (seconds)",
        "watch",
        "int",
        "How often the watched folder is checked for changes (2 to 300).",
        feature_id="core.watch",
        minimum=2,
        maximum=300,
        keywords=("watch", "poll", "interval", "seconds"),
    ),
    # --- Updates -----------------------------------------------------------
    SettingSpec(
        "auto_check_updates",
        "Check for updates on startup",
        "admin",
        "bool",
        "Look for a newer release each time QUILL starts.",
        feature_id="core.updates",
        keywords=("updates", "startup", "check"),
    ),
    SettingSpec(
        "beta_updates",
        "Get beta updates",
        "admin",
        "bool",
        "Receive pre-release builds, which may be unstable.",
        feature_id="core.updates",
        keywords=("updates", "beta", "channel", "prerelease"),
    ),
    # --- Integration and Context Menu --------------------------------------
    SettingSpec(
        "shell_integration_enabled",
        "Show QUILL in the file-manager right-click menu",
        "integration",
        "bool",
        "Add QUILL's enabled verbs to the file manager context menu.",
        keywords=("context menu", "right click", "explorer", "send to", "shell"),
    ),
    SettingSpec(
        "shell_file_types",
        "File types offered to QUILL",
        "integration",
        "choice",
        "Which kinds of files show QUILL verbs in the context menu.",
        choices=(
            ("images", "Images only"),
            ("images_pdf", "Images and PDF"),
            ("images_pdf_docs", "Images, PDF, and text documents"),
        ),
        keywords=("file types", "images", "pdf", "documents"),
    ),
    SettingSpec(
        "shell_verb_open",
        "Offer \u201cOpen in QUILL\u201d",
        "integration",
        "bool",
        "Add an \u201cOpen in QUILL\u201d verb for supported text documents.",
        keywords=("open", "context menu", "verb"),
    ),
    SettingSpec(
        "shell_verb_ocr",
        "Offer \u201cOCR with QUILL\u201d",
        "integration",
        "bool",
        "Add an OCR-to-text verb for images and PDF files.",
        feature_id="core.ocr",
        keywords=("ocr", "image", "pdf", "context menu", "verb"),
    ),
    SettingSpec(
        "shell_verb_ocr_structured",
        "Offer \u201cOCR with QUILL (structured Markdown)\u201d",
        "integration",
        "bool",
        "Add an AI-assisted OCR verb that returns structured Markdown.",
        feature_id="core.ocr",
        keywords=("ocr", "markdown", "structured", "ai", "context menu"),
    ),
    SettingSpec(
        "shell_verb_read",
        "Offer \u201cRead aloud in QUILL\u201d",
        "integration",
        "bool",
        "Add a verb that opens a file and starts reading it aloud.",
        feature_id="read_aloud",
        keywords=("read aloud", "speech", "context menu", "verb"),
    ),
    # --- Multi-press -------------------------------------------------------
    SettingSpec(
        "multi_press_window_ms",
        "Multi-press time window (ms)",
        "editing",
        "int",
        "How long QUILL waits for a second or third keypress before treating "
        "the first as a single press. Applies to Copy Tray and Command Palette "
        "multi-press actions. 300 ms suits fast typists; 500 ms helps users "
        "with motor control differences. Default: 400.",
        keywords=("multi press", "double press", "copy tray", "keyboard", "timer"),
    ),
    # --- Administration: developer tools, security, updates, and settings management ---
    SettingSpec(
        "console_enabled",
        "Enable Developer Console",
        "admin",
        "bool",
        "When on, the Python and TypeScript developer consoles are available "
        "under Tools > Advanced > Developer Console. Off by default for "
        "Essential and Writer profiles.",
        keywords=("developer console", "qdc", "scripting", "python", "automation"),
        feature_id="core.developer_console",
    ),
    SettingSpec(
        "console_python_timeout",
        "Python console execution timeout (seconds)",
        "admin",
        "int",
        "Maximum seconds a Python console command may run before QUILL interrupts it. Default: 30.",
        minimum=5,
        maximum=300,
        keywords=("developer console", "python", "timeout"),
        feature_id="core.developer_console",
    ),
    SettingSpec(
        "console_typescript_timeout",
        "TypeScript console execution timeout (seconds)",
        "admin",
        "int",
        "Maximum seconds a TypeScript console command may run before the "
        "Node worker is restarted. Default: 30.",
        minimum=5,
        maximum=300,
        keywords=("developer console", "typescript", "node", "timeout"),
        feature_id="core.developer_console.typescript",
    ),
    SettingSpec(
        "ssh_trust_first_use",
        "Trust SSH hosts on first connection",
        "admin",
        "bool",
        "When on, QUILL remembers a host key the first time it is seen "
        "(paramiko AutoAddPolicy). When off, the safer default, an "
        "unknown host key rejects the connection so you notice the "
        "mismatch. Off unless you have a specific reason to change it.",
        keywords=("ssh", "host key", "trust", "paramiko", "security"),
    ),
    # --- Braille Mode (BR-008) ---------------------------------------------
    SettingSpec(
        "braille_cells_per_line",
        "Cells per line",
        "braille",
        "int",
        "How many characters a single braille line holds. NABCC literature "
        "ranges from 28 (jumbo) to 42 (wide). 40 matches BANA and is the default.",
        minimum=28,
        maximum=42,
        keywords=("braille", "cells", "line width", "page width", "brf"),
        feature_id="core.braille",
    ),
    SettingSpec(
        "braille_lines_per_page",
        "Lines per page",
        "braille",
        "int",
        "How many lines fit on one braille page. BANA hard copy is 25, "
        "Braille Blaster sized embosser paper is 20-30.",
        minimum=20,
        maximum=30,
        keywords=("braille", "lines", "page height", "brf"),
        feature_id="core.braille",
    ),
    SettingSpec(
        "braille_use_form_feeds",
        "Use form feeds for page breaks",
        "braille",
        "bool",
        "When on (the historical default), form-feed characters (0x0C) in a "
        "BRF file are treated as authoritative page breaks. Turn off only "
        "if the source never used form feeds.",
        keywords=("braille", "form feed", "page break", "brf"),
        feature_id="core.braille",
    ),
    SettingSpec(
        "braille_calculate_pages",
        "Calculate pages from geometry",
        "braille",
        "bool",
        "When on and no form feeds are present, derive page boundaries from "
        "the cells-per-line / lines-per-page setting. Off by default only "
        "when both heuristics disagree; QUILL falls back to a hybrid mode.",
        keywords=("braille", "calculate", "geometry", "page break", "brf"),
        feature_id="core.braille",
    ),
    SettingSpec(
        "braille_save_sidecar",
        "Write sidecar on save",
        "braille",
        "bool",
        "When on, saving a BRF file also writes a matching .brf.json sidecar "
        "stamping the profile, line-ending report, and BOM presence so other "
        "tools can recover the reading context.",
        keywords=("braille", "sidecar", "json", "save", "brf"),
        feature_id="core.braille",
    ),
    SettingSpec(
        "braille_status_verbosity",
        "Status verbosity",
        "braille",
        "choice",
        "How much of the braille position to announce and display. "
        "'brief' is page + line + cell; 'normal' adds print page; "
        "'detailed' adds continuation, running head, and proofing status.",
        choices=(
            ("brief", "Brief"),
            ("normal", "Normal"),
            ("detailed", "Detailed"),
        ),
        keywords=("braille", "status", "verbosity", "announce", "speech"),
        feature_id="core.braille",
    ),
    SettingSpec(
        "braille_auto_announce_page_changes",
        "Announce page changes automatically",
        "braille",
        "bool",
        "When on, QUILL speaks the new page number whenever the caret "
        "crosses a page boundary. Off by default to avoid speech churn.",
        keywords=("braille", "announce", "page", "speech"),
        feature_id="core.braille",
    ),
    SettingSpec(
        "braille_auto_announce_print_page_changes",
        "Announce print page changes",
        "braille",
        "bool",
        "When on, QUILL speaks when the implied print page changes "
        "(requires a print page map; otherwise the announcement is skipped).",
        keywords=("braille", "announce", "print page", "speech"),
        feature_id="core.braille",
    ),
    SettingSpec(
        "braille_auto_announce_line_overflow",
        "Announce line overflow",
        "braille",
        "bool",
        "When on, QUILL warns when a source line exceeds the cells-per-line "
        "budget. Off by default to keep read-aloud uninterrupted.",
        keywords=("braille", "announce", "overflow", "line", "speech"),
        feature_id="core.braille",
    ),
    SettingSpec(
        "braille_include_proofing_status",
        "Include proofing status in status string",
        "braille",
        "bool",
        "When on, the detailed status string includes the last proofed "
        "page and the number of pages that still need review.",
        keywords=("braille", "proofing", "status", "review"),
        feature_id="core.braille",
    ),
    SettingSpec(
        "braille_include_running_head",
        "Include running head in status string",
        "braille",
        "bool",
        "When on, the detailed status string includes the current running "
        "head (page header) when one is present in the sidecar.",
        keywords=("braille", "running head", "header", "status"),
        feature_id="core.braille",
    ),
    SettingSpec(
        "braille_include_continuation",
        "Include continuation in status string",
        "braille",
        "bool",
        "When on, the detailed status string announces the continuation "
        "letter (a, b, c) when a page overflows onto a continuation page.",
        keywords=("braille", "continuation", "status", "speech"),
        feature_id="core.braille",
    ),
    # --- Spelling Review (F7) ---------------------------------------------
    SettingSpec(
        "spell_review_verbosity",
        "Spelling review announcement verbosity",
        "spelling",
        "choice",
        "How much information is spoken during the F7 spelling review. "
        "Concise gives progress only. Balanced includes the issue type and word. "
        "Detailed adds scope reminders and keyboard hints.",
        choices=(
            ("concise", "Concise"),
            ("balanced", "Balanced"),
            ("detailed", "Detailed"),
        ),
        keywords=("spelling", "review", "verbosity", "speech", "announcement", "f7"),
    ),
    SettingSpec(
        "spell_review_spell_word",
        "Spell out the misspelled word letter by letter",
        "spelling",
        "bool",
        "After announcing each misspelled word, spell it out letter by letter "
        "after a short pause. Useful when the word is hard to parse from speech alone.",
        keywords=("spelling", "spell out", "letters", "review", "f7"),
    ),
    SettingSpec(
        "spell_review_spell_word_pause_ms",
        "Pause before spelling the word (milliseconds)",
        "spelling",
        "int",
        "How long to wait after announcing the misspelled word before spelling it "
        "out letter by letter (100 to 3000). Default is 800.",
        minimum=100,
        maximum=3000,
        keywords=("spelling", "pause", "spell out", "timing", "review", "f7"),
    ),
    SettingSpec(
        "spell_review_wrap_to_beginning",
        "Wrap spelling review to the beginning",
        "spelling",
        "bool",
        "When spelling review reaches the end of the document, offer to continue "
        "checking from the beginning back to the original caret position.",
        keywords=("spelling", "wrap", "review", "f7"),
    ),
    SettingSpec(
        "spell_review_context_mode",
        "Spelling review context display mode",
        "spelling",
        "choice",
        "How much surrounding text is shown in the Context field of the F7 spelling review dialog.",
        choices=(
            ("sentence", "Sentence with adjacent sentences"),
            ("paragraph", "Full paragraph"),
        ),
        keywords=("spelling", "context", "review", "f7", "sentence", "paragraph"),
    ),
    # --- Administration: upgrade and migration behavior --------------------
    SettingSpec(
        "apply_recommended_keymap_updates",
        "Apply recommended keyboard-shortcut updates",
        "admin",
        "bool",
        "Let QUILL apply important shortcut corrections once on upgrade (for "
        "example, restoring Find to Ctrl+F). Each fix is applied a single time, "
        "so you can always rebind it afterward. Turn this off to keep your "
        "shortcuts exactly as you set them.",
        keywords=("upgrade", "shortcut", "keymap", "recommended", "find", "ctrl+f", "migration"),
    ),
    SettingSpec(
        "migration_notice",
        "Upgrade notice",
        "admin",
        "choice",
        "How QUILL tells you when it has migrated your settings or shortcuts "
        "after an update. A backup is always saved first regardless of this "
        "choice.",
        choices=(
            ("silent", "Silent"),
            ("announce", "Brief announcement"),
            ("prompt", "Summary with Undo"),
        ),
        keywords=("upgrade", "migration", "notice", "announce", "undo", "settings"),
    ),
    # --- Experimental (for-testing editor surfaces) ------------------------
    SettingSpec(
        "experimental_acknowledged",
        "I understand features may degrade based on the control selected",
        "experimental",
        "bool",
        (
            "Required safety gate. The experimental editor-surface and hide-border "
            "options below are IGNORED until this is ticked, so an accidental change "
            "can never affect your editor. Tick it only if you accept that a "
            "non-default surface is for testing and that some features may not work."
        ),
        keywords=("experimental", "acknowledge", "understand", "risk", "degrade", "testing"),
    ),
    SettingSpec(
        "experimental_editor_surface",
        "Editor surface (for testing)",
        "experimental",
        "choice",
        (
            "Which control backs the editor, for testing different surfaces. "
            "'Default' follows the braille Editor control type (Accessibility). "
            "RichEdit 3.0/2.0 are the native Windows rich controls; 'Notepad' is a "
            "plain EDIT control; 'Rich text' is an experimental wx.RichTextCtrl. "
            "RESTART QUILL after changing this so every document uses the new surface."
        ),
        choices=(
            ("default", "Default (follow Accessibility setting)"),
            ("rich2", "RichEdit 3.0"),
            ("rich", "RichEdit 2.0"),
            ("plain", "Notepad (plain edit control)"),
            ("rtf", "Rich text (wx.RichTextCtrl, experimental)"),
            ("win32", "Native Win32 EDIT (pywin32 spike, Windows only)"),
        ),
        keywords=(
            "experimental",
            "editor",
            "surface",
            "richedit",
            "notepad",
            "rtf",
            "win32",
            "native",
            "testing",
        ),
    ),
    SettingSpec(
        "editor_hide_border",
        "Hide editor border",
        "experimental",
        "bool",
        (
            "Draw the editor with no border for a cleaner, Notepad-like frame. "
            "RESTART QUILL after changing this."
        ),
        keywords=("experimental", "border", "margin", "notepad", "frame", "chrome"),
    ),
)
