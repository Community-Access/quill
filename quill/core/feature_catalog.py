"""Feature definition catalogue (extracted from ``features.py`` for GATE-11).

Contains :class:`FeatureDefinition`, :data:`FEATURE_DEFINITIONS`, and
:data:`FEATURE_ALIASES`. Extracted verbatim from ``features.py`` to keep
that module under its GATE-11 module-size budget; the definitions and their
semantics are unchanged.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class FeatureDefinition:
    id: str
    name: str
    description: str = ""
    aliases: tuple[str, ...] = ()
    dependencies: tuple[str, ...] = ()
    maturity: str = "stable"
    privacy: str = "local only"
    locked_on: bool = False
    locked_off: bool = False
    category: str = ""


FEATURE_DEFINITIONS: dict[str, FeatureDefinition] = {
    "core.app": FeatureDefinition("core.app", "App Shell", category="core"),
    "core.editor": FeatureDefinition(
        "core.editor", "Editor Core", category="core", dependencies=("core.app",)
    ),
    "core.file": FeatureDefinition(
        "core.file", "File Commands", category="core", dependencies=("core.app",)
    ),
    "core.edit": FeatureDefinition(
        "core.edit",
        "Editing Commands",
        aliases=(
            "copy tray",
            "tray",
            "clipboard tray",
            "abbreviations",
            "abbreviation",
            "text expansion",
            "expand",
            "snippet",
            "snippets",
            "shorthand",
        ),
        description=(
            "Core editing commands including the Copy Tray (multi-slot clipboard), "
            "abbreviation expansion, and text transformation tools."
        ),
        category="core",
        dependencies=("core.app",),
    ),
    "core.search": FeatureDefinition(
        "core.search", "Search", category="core", dependencies=("core.editor",)
    ),
    "core.search.regex": FeatureDefinition(
        "core.search.regex",
        "Regular Expression Search",
        aliases=("regex", "regular expression", "find regex"),
        dependencies=("core.search",),
        category="power text",
    ),
    "core.format": FeatureDefinition(
        "core.format", "Format Commands", category="core", dependencies=("core.editor",)
    ),
    "core.macros": FeatureDefinition(
        "core.macros",
        "Macros",
        aliases=("macro", "record macro", "playback", "keystroke recording", "replay"),
        description="Record and replay sequences of commands as named macros.",
        category="power text",
        dependencies=("core.editor",),
    ),
    "core.links": FeatureDefinition(
        "core.links", "Link Tools", category="core", dependencies=("core.editor",)
    ),
    "core.navigate": FeatureDefinition(
        "core.navigate", "Navigation", category="core", dependencies=("core.editor",)
    ),
    "core.window": FeatureDefinition(
        "core.window", "Window Switching", category="core", dependencies=("core.app",)
    ),
    "core.view": FeatureDefinition(
        "core.view", "View Toggles", category="core", dependencies=("core.app",)
    ),
    "core.spellcheck": FeatureDefinition(
        "core.spellcheck", "Spell Check", category="core", dependencies=("core.editor",)
    ),
    "core.dictionary": FeatureDefinition(
        "core.dictionary",
        "Dictionary and Thesaurus",
        aliases=("dictionary", "thesaurus", "look up", "lexical"),
        description="Definitions, synonyms, and the Look Up surface (DICT-1/DICT-2).",
        category="core",
        dependencies=("core.editor",),
    ),
    "core.intellisense": FeatureDefinition(
        "core.intellisense",
        "Word Prediction",
        aliases=("intellisense", "autocomplete", "word prediction"),
        category="core",
        dependencies=("core.editor",),
    ),
    "core.read_aloud": FeatureDefinition(
        "core.read_aloud", "Read Aloud", category="accessibility", dependencies=("core.editor",)
    ),
    "core.dictation": FeatureDefinition(
        "core.dictation",
        "Dictation",
        description="Launches Windows dictation in the active editor.",
        category="accessibility",
        dependencies=("core.editor",),
    ),
    "core.voice_commands": FeatureDefinition(
        "core.voice_commands",
        "Voice Commands",
        description="Interprets Windows dictation phrases as Quill commands.",
        category="accessibility",
        dependencies=("core.dictation",),
    ),
    "core.rich_text_lens": FeatureDefinition(
        "core.rich_text_lens",
        "Rich Text Lens",
        description=(
            "Native wxPython rich-text editing surface for .rtf files. Locked off "
            "pending fuller screen-reader testing; RTF files continue to open as "
            "plain text in the meantime. Remove locked_off to re-enable."
        ),
        category="editor",
        locked_off=True,
    ),
    "core.bw_whisperer": FeatureDefinition(
        "core.bw_whisperer",
        "BITS Whisperer",
        description=(
            "Master flag for the BITS Whisperer transcription suite. Disabled for "
            "QUILL 1.0 (deferred to 2.0) until it reaches feature parity; gating "
            "this off hides the entire BITS Whisperer menu and its sub-features."
        ),
        category="accessibility",
        dependencies=("core.dictation",),
        locked_off=True,
    ),
    "core.bw_transcription": FeatureDefinition(
        "core.bw_transcription",
        "BITS Whisperer Transcription Rollout",
        description="Phased BITS Whisperer speech-model and dictation rollout surface.",
        category="accessibility",
        dependencies=("core.dictation", "core.bw_whisperer"),
    ),
    "core.bw_parakeet": FeatureDefinition(
        "core.bw_parakeet",
        "BITS Whisperer Parakeet Models",
        description="Controls visibility for phased Parakeet model options.",
        category="accessibility",
        dependencies=("core.bw_transcription",),
    ),
    "core.bw_providers": FeatureDefinition(
        "core.bw_providers",
        "BITS Whisperer Provider Onboarding",
        description="Guided provider planning and readiness checks for phased rollout.",
        category="accessibility",
        dependencies=("core.bw_transcription",),
    ),
    "core.bw_insights": FeatureDefinition(
        "core.bw_insights",
        "BITS Whisperer Rollout Insights",
        description="Readiness checks, capability matrix, and rollout diagnostics surfaces.",
        category="accessibility",
        dependencies=("core.bw_transcription",),
    ),
    "core.watch_folder": FeatureDefinition(
        "core.watch_folder",
        "Watch Folder Automation",
        aliases=("watch folder", "watch", "inbox folder", "auto open", "folder monitor"),
        description="Monitors a folder and opens newly detected supported files.",
        category="accessibility",
        dependencies=("core.file",),
    ),
    "core.analysis": FeatureDefinition(
        "core.analysis", "Document Analysis", category="core", dependencies=("core.editor",)
    ),
    "core.glow": FeatureDefinition(
        "core.glow",
        "GLOW Accessibility",
        category="accessibility",
        dependencies=("core.editor",),
        locked_off=True,
        description=(
            "GLOW document accessibility audit, fix, and engine updates. Hidden "
            "for now while the feature is finished; remove locked_off to re-enable. "
            "Does not affect Report a Bug or diagnostics, which read the GLOW "
            "engine version independently."
        ),
    ),
    "core.trust": FeatureDefinition(
        "core.trust", "Trust and Intake", category="safety", dependencies=("core.file",)
    ),
    "core.accessibility": FeatureDefinition(
        "core.accessibility",
        "Accessibility Tools",
        category="accessibility",
        dependencies=("core.editor",),
    ),
    "core.notifications": FeatureDefinition(
        "core.notifications",
        "Notifications",
        category="core",
        dependencies=("core.app",),
    ),
    "core.updates": FeatureDefinition(
        "core.updates", "Update Checks", category="safety", dependencies=("core.app",)
    ),
    "core.shell": FeatureDefinition(
        "core.shell", "Shell Integration", category="system", dependencies=("core.app",)
    ),
    "core.keymap": FeatureDefinition(
        "core.keymap", "Keymap Management", category="core", dependencies=("core.app",)
    ),
    "core.help": FeatureDefinition(
        "core.help", "Help and Guides", category="core", dependencies=("core.app",)
    ),
    "core.palette": FeatureDefinition(
        "core.palette", "Command Palette", category="core", dependencies=("core.app",)
    ),
    "core.profile": FeatureDefinition(
        "core.profile",
        "Feature Profiles",
        description="Profile switching, previews, and recovery.",
        dependencies=("core.app",),
        category="core",
        locked_on=True,
    ),
    "core.recovery": FeatureDefinition(
        "core.recovery",
        "Recovery Paths",
        description="Safe mode, restore prompts, and emergency reset.",
        dependencies=("core.app",),
        category="safety",
        locked_on=True,
    ),
    "core.notes": FeatureDefinition(
        "core.notes",
        "Sticky Notes",
        aliases=("notes", "sticky", "sticky notes"),
        description="Inline sticky notes attached to document positions.",
        dependencies=("core.editor",),
        category="core",
    ),
    "core.notebook": FeatureDefinition(
        "core.notebook",
        "Notebook (Workspace)",
        aliases=("notebook", "workspace", "entries"),
        description="Multi-document workspace with entries, goals, and snapshots (§10.4).",
        dependencies=("core.file",),
        category="core",
    ),
    "core.remote": FeatureDefinition(
        "core.remote",
        "Remote Access",
        aliases=("remote", "ftp", "sftp", "webdav", "s3", "remote sites"),
        description=(
            "Open, save, and manage files over FTP, SFTP, WebDAV, and S3 "
            "remote sites (issues #154-#157). Disabling this hides the "
            "remote-sites file menu and the Manage Remote Sites dialog."
        ),
        category="core",
        dependencies=("core.file",),
    ),
    "core.github_remote": FeatureDefinition(
        "core.github_remote",
        "GitHub Remote Access",
        aliases=("github", "github remote", "open from github"),
        description=(
            "Browse GitHub repositories, open remote files, and commit changes "
            "back to GitHub (File > Open Remote > GitHub). Requires PyGithub "
            "(pip install quill[github]). Disabling this hides the GitHub items "
            "in the Open from Remote submenu."
        ),
        category="core",
        privacy="network after confirmation",
        dependencies=("core.remote",),
    ),
    "core.developer_console": FeatureDefinition(
        "core.developer_console",
        "Developer Console",
        aliases=("developer console", "qdc", "scripting", "python console", "automation"),
        description=(
            "Embedded Python and TypeScript consoles for developers, power users, "
            "and accessibility professionals. Exposes the q scripting API. "
            "Gated by profile; hidden for Essential and Writer profiles."
        ),
        category="developer",
        dependencies=("core.app",),
    ),
    "core.developer_console.typescript": FeatureDefinition(
        "core.developer_console.typescript",
        "Developer Console TypeScript",
        aliases=("typescript console", "ts console"),
        description=(
            "TypeScript console via a Node.js subprocess bridge. Requires Node.js on PATH."
        ),
        category="developer",
        dependencies=("core.developer_console",),
    ),
    "core.ocr": FeatureDefinition(
        "core.ocr", "OCR", category="accessibility", dependencies=("core.file",)
    ),
    "future.character_inspector": FeatureDefinition(
        "future.character_inspector",
        "Character Inspector",
        aliases=("character inspector", "inspect character"),
        maturity="advanced",
        category="power text",
    ),
    "future.cleanup": FeatureDefinition(
        "future.cleanup",
        "Unicode Cleanup",
        aliases=("cleanup", "unicode cleanup"),
        maturity="advanced",
        category="power text",
    ),
    "future.regex_library": FeatureDefinition(
        "future.regex_library",
        "Regular Expression Library",
        aliases=("regex library", "regex recipes"),
        maturity="advanced",
        category="power text",
    ),
    "future.ai": FeatureDefinition(
        "future.ai",
        "AI Assistance",
        aliases=("ai", "assistant", "agent", "llm", "chat", "ask quill"),
        maturity="advanced",
        privacy="network after confirmation",
        category="future",
    ),
    "core.third_party_plugins": FeatureDefinition(
        "core.third_party_plugins",
        "Third-Party Plugins",
        aliases=("plugins", "third party plugins", "plugin loader"),
        description=(
            "SEC-8: experimental loader for third-party plugins. Disabled for "
            "QUILL 1.0 — a default build never loads third-party plugin code. "
            "Locked off until the plugin sandbox, signing, and review process "
            "ship; gating this off keeps untrusted plugin code out of the "
            "process entirely."
        ),
        maturity="experimental",
        privacy="local only",
        category="future",
        dependencies=("core.app",),
        locked_off=True,
    ),
    "core.bundled_quillins": FeatureDefinition(
        "core.bundled_quillins",
        "Bundled Quillins",
        aliases=("bundled quillins", "first-party quillins", "built-in quillins"),
        description=(
            "Tier C: QUILL's own features shipped as sandboxed Quillins inside "
            "the install tree (quill/quillins_bundled). These are trusted-author, "
            "run through the same out-of-process, capability- and consent-gated "
            "path as third-party Quillins, and ship enabled — wholly independent "
            "of the SEC-8 core.third_party_plugins lock, which stays off. Turning "
            "this off hides the bundled Quillins' commands."
        ),
        maturity="stable",
        privacy="local only",
        category="core",
        dependencies=("core.app",),
        locked_on=True,
    ),
}


FEATURE_ALIASES: dict[str, str] = {}
for _feature in FEATURE_DEFINITIONS.values():
    FEATURE_ALIASES[_feature.id.lower()] = _feature.id
    FEATURE_ALIASES[_feature.name.lower()] = _feature.id
    for _alias in _feature.aliases:
        FEATURE_ALIASES[_alias.lower()] = _feature.id
