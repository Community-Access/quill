"""Intent-based onboarding profiles for the QUILL startup wizard.

Seven profiles translate the technical FeatureProfile system into plain-English
starting points. Each profile maps to a technical profile ID in features.py,
a set of bundled Quillins to enable or disable, and optional feature overrides.

The ``preview_text`` for each profile is displayed verbatim in a multiline
read-only TextCtrl inside the wizard. It describes only what the user will have;
it never mentions what is absent or hidden.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class IntentProfile:
    id: str
    name: str
    tagline: str  # short label shown in the ListBox
    preview_text: str  # multi-paragraph text shown in the preview TextCtrl
    technical_profile: str
    quillins_on: tuple[str, ...] = ()
    quillins_off: tuple[str, ...] = ()
    # feature_overrides: keys must exist in FEATURE_DEFINITIONS
    feature_overrides: dict[str, str] = field(default_factory=dict)
    # Which optional extras are already included (suppress the checkbox)
    includes_ai: bool = False
    includes_braille: bool = False
    includes_automation: bool = False


_ALL_BUNDLED: tuple[str, ...] = (
    "com.quill.smartinsert",
    "com.quill.journalstamp",
    "com.quill.docguardian",
    "com.quill.statusscribe",
    "com.quill.brftools",
    "com.quill.bundled.insert-tools",
    "com.quill.bundled.insert-character",
    "com.quill.bundled.markdown-helpers",
    "com.quill.bundled.text-tools",
    "com.quill.bundled.line-tools",
    "com.quill.bundled.ai-writing-prompts",
    "com.quill.bundled.ai-writing-skills",
    "com.quill.bundled.word-count-node",
)

_WRITER_ON: tuple[str, ...] = (
    "com.quill.journalstamp",
    "com.quill.docguardian",
    "com.quill.statusscribe",
    "com.quill.bundled.insert-tools",
)
_WRITER_OFF: tuple[str, ...] = (
    "com.quill.smartinsert",
    "com.quill.brftools",
    "com.quill.bundled.insert-character",
    "com.quill.bundled.markdown-helpers",
    "com.quill.bundled.text-tools",
    "com.quill.bundled.line-tools",
    "com.quill.bundled.ai-writing-prompts",
    "com.quill.bundled.ai-writing-skills",
    "com.quill.bundled.word-count-node",
)

INTENT_PROFILES: list[IntentProfile] = [
    IntentProfile(
        id="text_editor",
        name="Just a Text Editor",
        tagline="Open files, type, save. Nothing extra.",
        preview_text=(
            "Just a Text Editor\n"
            "\n"
            "If you simply want a Notepad-like replacement that works reliably\n"
            "with your screen reader, this is the profile for you.\n"
            "\n"
            "Open files, type, and save. QUILL stays completely out of your way.\n"
            "\n"
            "What you have:\n"
            "  - Plain text editing: undo, cut, copy, paste\n"
            "  - Find and Replace\n"
            "  - Auto-recovery so your work is never lost\n"
            "  - Recent files and session restore\n"
            "  - Fully compatible with NVDA, JAWS, and Narrator\n"
            "\n"
            "You can add more any time from Help > Personalise QUILL."
        ),
        technical_profile="essential",
        quillins_off=_ALL_BUNDLED,
        feature_overrides={
            "future.ai": "off",
            "core.bundled_quillins": "off",
            "core.watch_folder": "off",
            "core.macros": "off",
            "core.abbreviations": "off",
            "core.notes": "off",
            "core.search.regex": "off",
        },
    ),
    IntentProfile(
        id="writer",
        name="Writer",
        tagline="Documents, notes, and journal entries.",
        preview_text=(
            "Writer\n"
            "\n"
            "For writing documents, notes, journal entries, and reports.\n"
            "\n"
            "What you have:\n"
            "  - Full text and RTF editing with formatting tools\n"
            "  - Spell check and live word count\n"
            "  - Compare Mode to review drafts side by side\n"
            "  - Abbreviation shortcuts: type a short phrase and expand it\n"
            "  - Starter snippet packs for common phrases and templates\n"
            "  - Sticky notes attached to any document position\n"
            "  - Journal Stamp: date headers in new journal files,\n"
            "    word count spoken after every save\n"
            "  - Document Guardian: warns before closing a document\n"
            "    that is short or has unresolved notes\n"
            "  - Insert > Date and Time menu\n"
            "  - Copy Tray with 12 clipboard slots\n"
            "  - Auto-recovery so your work is never lost\n"
            "\n"
            "You can add AI, braille, and automation any time from\n"
            "Help > Personalise QUILL."
        ),
        technical_profile="writer",
        quillins_on=_WRITER_ON,
        quillins_off=_WRITER_OFF,
        feature_overrides={"future.ai": "off"},
    ),
    IntentProfile(
        id="web_author",
        name="Markdown and Web Author",
        tagline="Web content, HTML, Markdown, and encoding tools.",
        preview_text=(
            "Markdown and Web Author\n"
            "\n"
            "For writing web content, Markdown files, and HTML documents.\n"
            "\n"
            "What you have:\n"
            "  - Everything in Writer\n"
            "  - Markdown syntax helpers\n"
            "  - HTML encoding and decoding tools\n"
            "  - Insert Character picker for Unicode and special symbols\n"
            "  - Re-encode As for cross-encoding safety\n"
            "  - Text Tools: trim, transform case, shuffle, sort lines\n"
            "  - Line Tools: join, split, filter, and number lines\n"
            "  - Regular expression search\n"
            "  - Status Scribe live word count in the status bar\n"
            "\n"
            "You can add AI and automation any time from\n"
            "Help > Personalise QUILL."
        ),
        technical_profile="developer_power_text",
        quillins_on=(
            "com.quill.journalstamp",
            "com.quill.docguardian",
            "com.quill.statusscribe",
            "com.quill.bundled.insert-tools",
            "com.quill.bundled.insert-character",
            "com.quill.bundled.markdown-helpers",
            "com.quill.bundled.text-tools",
            "com.quill.bundled.line-tools",
        ),
        quillins_off=(
            "com.quill.smartinsert",
            "com.quill.brftools",
            "com.quill.bundled.ai-writing-prompts",
            "com.quill.bundled.ai-writing-skills",
            "com.quill.bundled.word-count-node",
        ),
        feature_overrides={"future.ai": "off"},
    ),
    IntentProfile(
        id="accessibility_pro",
        name="Accessibility Professional",
        tagline="Reading, comparison, inspection, and document testing.",
        preview_text=(
            "Accessibility Professional\n"
            "\n"
            "For accessibility testers, document reviewers, and anyone who\n"
            "needs reading tools, comparison, and trusted document intake.\n"
            "\n"
            "What you have:\n"
            "  - Everything in Writer\n"
            "  - Read Aloud at full prominence\n"
            "  - Compare Mode for reviewing documents side by side\n"
            "  - Document Trust and intake workflow\n"
            "  - OCR image-to-text conversion\n"
            "  - Insert Character picker for non-ASCII inspection\n"
            "  - Text Tools for content cleanup and transform\n"
            "  - Keymap Editor for customizing keyboard shortcuts\n"
            "  - Status Scribe live word count\n"
            "\n"
            "You can add AI and braille tools any time from\n"
            "Help > Personalise QUILL."
        ),
        technical_profile="accessibility_professional",
        quillins_on=(
            "com.quill.journalstamp",
            "com.quill.docguardian",
            "com.quill.statusscribe",
            "com.quill.bundled.insert-tools",
            "com.quill.bundled.insert-character",
            "com.quill.bundled.text-tools",
        ),
        quillins_off=(
            "com.quill.smartinsert",
            "com.quill.brftools",
            "com.quill.bundled.markdown-helpers",
            "com.quill.bundled.line-tools",
            "com.quill.bundled.ai-writing-prompts",
            "com.quill.bundled.ai-writing-skills",
            "com.quill.bundled.word-count-node",
        ),
        feature_overrides={"future.ai": "off"},
    ),
    IntentProfile(
        id="braille_pro",
        name="Braille Professional",
        tagline="BRF, BRL, UEB, and braille translation tools.",
        preview_text=(
            "Braille Professional\n"
            "\n"
            "For braille transcribers, proofreaders, and teachers who work\n"
            "with BRF, BRL, and UEB documents.\n"
            "\n"
            "What you have:\n"
            "  - Everything in Accessibility Professional\n"
            "  - Braille Mode with BRF and BRL file support\n"
            "  - Braille status bar cell with position and line information\n"
            "  - BRF Tools: translation preferences and page handling\n"
            "  - Smart Insert BRF test content (=brftest() trigger)\n"
            "  - Grade 1 and Grade 2 translation via the Braille menu\n"
            "  - QUILL Braille Pack integration when installed\n"
            "\n"
            "You can add AI tools any time from Help > Personalise QUILL."
        ),
        technical_profile="braille_screen_reader_power_user",
        quillins_on=(
            "com.quill.journalstamp",
            "com.quill.docguardian",
            "com.quill.statusscribe",
            "com.quill.bundled.insert-tools",
            "com.quill.bundled.insert-character",
            "com.quill.bundled.text-tools",
            "com.quill.brftools",
            "com.quill.smartinsert",
        ),
        quillins_off=(
            "com.quill.bundled.markdown-helpers",
            "com.quill.bundled.line-tools",
            "com.quill.bundled.ai-writing-prompts",
            "com.quill.bundled.ai-writing-skills",
            "com.quill.bundled.word-count-node",
        ),
        feature_overrides={
            "core.braille": "on",
            "future.ai": "off",
        },
        includes_braille=True,
    ),
    IntentProfile(
        id="ai_author",
        name="AI-Powered Author",
        tagline="Writing with AI assistance, grammar check, and prompts.",
        preview_text=(
            "AI-Powered Author\n"
            "\n"
            "For writers who want AI assistance: rewrite, summarise,\n"
            "check grammar, and continue writing with Ask Quill.\n"
            "\n"
            "What you have:\n"
            "  - Everything in Writer\n"
            "  - Ask Quill AI assistant (Alt+Q)\n"
            "  - AI grammar check and rewrite commands\n"
            "  - AI writing prompts (expand, summarise, explain, and more)\n"
            "  - AI writing skills for multi-step tasks\n"
            "  - AI image description\n"
            "  - Prompt Library to save and reuse your own prompts\n"
            "  - Smart Insert for typed template triggers\n"
            "\n"
            "You will be asked to set up an API key on the next screen.\n"
            "You can also configure this later from Help > Personalise QUILL."
        ),
        technical_profile="writer",
        quillins_on=(
            "com.quill.journalstamp",
            "com.quill.docguardian",
            "com.quill.statusscribe",
            "com.quill.bundled.insert-tools",
            "com.quill.smartinsert",
            "com.quill.bundled.ai-writing-prompts",
            "com.quill.bundled.ai-writing-skills",
        ),
        quillins_off=(
            "com.quill.brftools",
            "com.quill.bundled.insert-character",
            "com.quill.bundled.markdown-helpers",
            "com.quill.bundled.text-tools",
            "com.quill.bundled.line-tools",
            "com.quill.bundled.word-count-node",
        ),
        feature_overrides={"future.ai": "on"},
        includes_ai=True,
    ),
    IntentProfile(
        id="developer",
        name="Developer and Power User",
        tagline="Everything: regex, macros, shell, all tools.",
        preview_text=(
            "Developer and Power User\n"
            "\n"
            "For developers and power users who want every tool available.\n"
            "\n"
            "What you have:\n"
            "  - Everything in QUILL\n"
            "  - Regular expression search\n"
            "  - Macro recorder and playback\n"
            "  - Shell integration\n"
            "  - Smart Insert templates and abbreviation expansion\n"
            "  - Markdown, HTML, text, and line tools\n"
            "  - Character picker and encoding tools\n"
            "  - GitHub remote file access\n"
            "  - Developer Console\n"
            "  - Watch Folder automation\n"
            "  - Keymap Editor and keyboard pack import/export\n"
            "  - Language profiles and token navigation\n"
            "\n"
            "You can add AI and braille tools any time from\n"
            "Help > Personalise QUILL."
        ),
        technical_profile="developer_power_text",
        quillins_on=_ALL_BUNDLED,
        feature_overrides={"future.ai": "off"},
        includes_automation=True,
    ),
]

_PROFILE_MAP: dict[str, IntentProfile] = {p.id: p for p in INTENT_PROFILES}

DEFAULT_INTENT_ID = "text_editor"


def get_intent_profile(profile_id: str) -> IntentProfile:
    return _PROFILE_MAP.get(profile_id, _PROFILE_MAP[DEFAULT_INTENT_ID])


def list_intent_profiles() -> list[IntentProfile]:
    return list(INTENT_PROFILES)
