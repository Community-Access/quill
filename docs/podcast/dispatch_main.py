#!/usr/bin/env python3
"""Dispatch 36 subagents to bring the main renamed episode files up to bar.

The 18 deep-dive episodes (ep05, 12, 14, 16, 20, 24, 27, 29, 31, 37, 38, 43, 44,
47, 48, 51, 53, 54) are already at the 3,500-4,500 word / 7-9 pause bar.

The 36 main renamed episodes are still at the old 600-word / 1-pause digest
length. This script generates briefs and dispatches one subagent per file to
rewrite each at the deep-dive bar.
"""

from pathlib import Path

BRIEFS_DIR = Path("docs/podcast/briefs")
BRIEFS_DIR.mkdir(exist_ok=True)

# (new_num, slug, title, prev_num, next_num, topic_brief, code_refs)
# Covering episodes 1-4, 6-11, 13, 15, 17-19, 21-23, 25-26, 28, 30, 32-36, 39-42, 45-46, 49-50, 52
# That's 36 episodes not covered by the 18 deep-dive files.
MAIN = [
    (1, "welcome-to-quill", "Welcome to QUILL",
     None, 2, "The opening episode: what QUILL is, who it's for, the three design promises (QUILL owns the essentials, everything optional is off by default, nothing leaves your computer without asking), why free matters, and how to follow the course. Set the tone for the whole series.",
     "quill/__main__.py, quill/ui/main_frame.py, README.md, docs/QUILL-PRD.md"),

    (2, "install-and-first-launch", "Install and First Launch",
     1, 3, "The installer, the wizard, feature profiles, self-voicing setup, the three day-one habits (F1, the optional components store, the guaranteed Escape), and the Safety Net story behind the first launch.",
     "quill/ui/main_frame.py (welcome wizard), quill/core/settings.py, quill/stability/safe_mode.py"),

    (3, "your-first-document", "Your First Document",
     2, 4, "Files in and out: new, open, save, recent files that respect removable drives, cursor position memory, the silent crash-recovery net that is protecting you from day one. The base case.",
     "quill/core/recovery.py, quill/core/paths.py, quill/core/storage.py, File menu, recent files"),

    (4, "the-main-window", "The Main Window",
     3, 5, "The menu bar by intent, tabs, the status bar as narrator, the Spoken Echo (Alt+Shift+E), the dialog contract that means you can never be trapped, and why nothing ever steals focus. The main window as a tool you can hear.",
     "quill/ui/main_frame.py, quill/core/verbosity/ (if exists)"),

    (6, "the-command-palette", "The Command Palette",
     5, 7, "Ctrl+Shift+P: reach any of hundreds of commands by typing a fragment. The palette as discovery tool, shortcut tutor, and the end of menu-path memorization. Includes a code-verified walkthrough of how the palette matches fuzzy and how it shows shortcut hints.",
     "quill/ui/command_palette.py if exists, quill/ui/main_frame.py (palette invocation), quill/core/command_registry.py if exists"),

    (7, "what-quill-says", "What QUILL Says",
     6, 8, "The verbosity system: profiles, Quiet and Meeting modes, status queries (Where am I? What changed?), anti-spam machinery, and the Why did QUILL say that? explainer. The whole speech contract, end to end.",
     "quill/core/verbosity/ if exists, quill/ui/main_frame.py (announce channels)"),

    (8, "moving-through-text", "Moving Through Text",
     7, 9, "Navigation as a vocabulary: characters to headings, bookmarks that survive restarts, selection marks, Go To Line, and the QUILL key's Quick Nav and Browse Mode introduced. The full movement toolkit.",
     "quill/ui/main_frame.py (navigation commands), quill/core/keymap/profile_default.json"),

    (9, "the-quill-key", "The QUILL Key",
     8, 10, "The prefix system in full: why chords exist, a tour of what lives behind the QUILL key, Browse Mode as the editor's virtual cursor, and how to adopt chords without memorizing a chart.",
     "quill/core/keymap/ (QUILL key binding), quill/ui/main_frame.py (browse mode)"),

    (10, "make-the-keyboard-yours", "Make the Keyboard Yours",
     9, 11, "The Keymap Editor: two-way search including reverse shortcut lookup, Record Keys, informed one-step conflict swaps, keymap diagnostics with one-click Heal, and shareable keyboard packs. Make every keystroke yours.",
     "quill/ui/keymap_editor_dialog.py if exists, quill/core/keymap/, quill/core/keymap_diagnostics.py if exists"),

    (11, "editing-power-tools", "Editing Power Tools",
     10, 12, "Selection and marks, the undo contract (compound changes are one step), line surgery, section moves, case transforms, and the revived classics: Repeat, Restore Deleted Text, and Describe Character. The everyday editing toolkit.",
     "quill/ui/main_frame.py (edit commands), quill/core/undo.py if exists"),

    (13, "find-replace-navigate", "Find, Replace, Navigate",
     12, 14, "Search with spoken match counts, replace-all as one undo step, a gentle first regular expression, and Search in Files across whole folders. Search as an instrument, not a dialog.",
     "quill/ui/main_frame.py (search dialog), quill/core/search/ if exists"),

    (15, "spelling-and-word-tools", "Spelling and Word Tools",
     14, 16, "Misspelling navigation (Ctrl+F7) as the fair replacement for red squiggles, the spell dialog, custom dictionaries, downloadable languages, and the dictionary and thesaurus. Honest spell check for the screen reader era.",
     "quill/core/spell/, quill/core/thesaurus.py if exists, quill/ui/main_frame.py (spell commands)"),

    (17, "never-lose-work", "Never Lose Work",
     16, 18, "The full safety stack layer by layer: undo, autosave, crash recovery, backups, versions, snapshots, atomic writes, and honest failure reporting. Safety as courage, not paranoia.",
     "quill/core/recovery.py, quill/core/storage.py (atomic write), quill/core/backup.py if exists"),

    (18, "markdown-and-structure", "Markdown and Structure",
     17, 19, "The structure language everything builds on: the core syntax in minutes, why structure is audible here, the live preview, and the style habits that pay off across a dozen later features.",
     "quill/core/markdown/ if exists, quill/core/structure.py if exists, quill/ui/main_frame.py (preview)"),

    (19, "the-text-supply-toolkit", "The Text-Supply Toolkit",
     18, 20, "The twelve-slot Copy Tray, snippets with prompts and cursor markers, auto-expanding abbreviations, and recorded macros. Four tools that bring text to your cursor.",
     "quill/core/copy_tray.py if exists, quill/core/snippets.py, quill/core/macros.py"),

    (21, "rich-formatting-hidden-codes", "Rich Formatting, Hidden Codes",
     20, 22, "Real fonts, colors, and alignment with a clean plain-text buffer: Describe Formatting at Cursor, Reveal Codes, and Illuminations. Formatting that survives inside a plain .txt.",
     "quill/core/illuminations.py if exists, quill/core/format_codes.py if exists, quill/ui/main_frame.py (format commands)"),

    (22, "word-epub-pdf-and-friends", "Word, EPUB, PDF and Friends",
     21, 23, "Other people's formats with dignity: Word round-trips with real heading styles, the EPUB navigator, honest PDF extraction quality, the import/export engine, and batch conversion.",
     "quill/io/, quill/ui/main_frame.py (export submenu)"),

    (23, "document-rescue-ocr", "Document Rescue and OCR",
     22, 24, "Free first, local first, nothing uploaded: MarkItDown for born-digital files, the scanned-PDF escalation prompt, on-device Tesseract OCR with confidence honesty, and the verified engine install.",
     "quill/io/ocr.py, quill/io/markitdown.py if exists, quill/ui/main_frame.py (import)"),

    (25, "files-everywhere", "Files Everywhere",
     24, 26, "FTP, SFTP, WebDAV, and S3 from three commands; GitHub editing with no Git installed; SSH editing with strict host keys; Open from URL. The end of the download-edit-reupload shuffle.",
     "quill/io/remote/ if exists, quill/core/ssh/client.py, quill/ui/main_frame.py (open from URL)"),

    (26, "watch-folders-automation", "Watch Folders and Automation",
     25, 27, "Teach QUILL to work while you're elsewhere: auto-opening inbox folders, watch actions and pipelines, and the safety posture that keeps automation from becoming mystery.",
     "quill/core/watch_folders.py if exists, quill/ui/main_frame.py (automation commands)"),

    (28, "read-aloud-and-voices", "Read Aloud and the Voice Catalog",
     27, 29, "SAPI, eSpeak, DECtalk (hello, Paul), on-device Kokoro neural voices, the optional cloud voice, the browser reader, and the SSML Builder. A voice for every job, and the catalog of all of them.",
     "quill/core/voice_catalog.py, quill/core/speech/ if exists, quill/ui/main_frame_speech.py"),

    (30, "dictation", "Dictation",
     29, 31, "You talk, QUILL types, offline: Whisper-powered hold-to-talk and locked dictation, model choices for real hardware, and the speak-fast-repair-fast workflow. Voice in.",
     "quill/core/speech/dictation.py if exists, quill/ui/main_frame_speech.py, quill/core/whisper.py if exists"),

    (32, "transcription-listening-companion", "Transcription and the Listening Companion",
     31, 33, "Recordings into documents, privately: local transcription with translation and speaker options, Transcript Actions from minutes to follow-up emails, and the no-syntax Action Builder.",
     "quill/core/bits_whisperer.py if exists, quill/ui/main_frame_speech.py, quill/core/transcript_actions.py if exists"),

    (33, "the-audio-studio", "The Audio Studio",
     32, 34, "Documents out to sound, all grown up: the Audio Studio's three journeys - narrate documents into audiobooks, combine recordings into chaptered books, and edit any audiobook in the Chapter Workbench - plus incremental rebuilds, voice casting, AI chapter titles, and publishing to a feed, a server, or Auphonic. DAISY export still closes the arc.",
     "quill/ui/audio_studio/ if exists, quill/ui/audio_studio_dialog.py, quill/io/daisy.py"),

    (34, "setting-up-ai", "Setting Up AI",
     33, 35, "Off by default, reviewable always, free for everyone: the setup wizard's honest choices (local Ollama, free OpenRouter key, paid accounts, or Not Now) and the privacy architecture underneath.",
     "quill/ui/ai_setup_wizard.py if exists, quill/core/ai/, quill/stability/redaction.py"),

    (35, "ask-quill-everyday-ai", "Ask Quill and Everyday AI",
     34, 36, "One conversation that knows your document, the quick-action toolkit, AI spell/grammar/thesaurus above the local engines, custom instructions, and the discipline of rejecting things.",
     "quill/core/ai/sessions.py, quill/core/ai/chat_session.py, quill/ui/main_frame_ai.py if exists"),

    (36, "ai-library-prompts-and-skills", "The AI Library - Prompts and Skills",
     35, 37, "A build-along up the ladder: saving your first prompt with variables, promoting it into a multi-step skill, sharing packs, and curating a bench that fits your actual week.",
     "quill/core/prompt_library.py, quill/core/ai/library.py, quill/core/ai/skills.py if exists"),

    (39, "agents-reviewable-autonomy", "Agents - Reviewable Autonomy",
     38, 40, "Plans you read before they run: the plan-review-execute contract, the Accessibility Tune-Up as flagship, partial approval, and the craft of reviewing plans. Autonomy with a human in the loop.",
     "quill/core/ai/agent.py, quill/core/ai/agents/ directory, quill/core/ai/agent_session.py"),

    (40, "accessible-vault-basics", "The Accessible Vault",
     39, 41, "Linked notes rebuilt for the ear: wikilinks, the spoken what links here, Note Neighborhood, unlinked mentions, fearless rename. The graph view without the graph.",
     "quill/core/vault/ if exists, quill/ui/main_frame_vault.py, quill/core/vault/links.py if exists"),

    (41, "vault-power", "Vault Power",
     40, 42, "Tags that roll up, templates with prompts, daily notes, embeds, exporting your vault as an accessible website, and Git sync on infrastructure you own.",
     "quill/core/vault/ if exists, quill/core/vault/templates.py if exists, quill/ui/main_frame_vault.py"),

    (42, "story-studio", "Story Studio",
     41, 43, "Book-length writing with a keyboard-first binder: structure straight from your headings, character and plot-thread detail forms as front matter, and compile-to-manuscript.",
     "quill/core/story/, quill/ui/main_frame_story_studio.py, quill/ui/story_studio_dialog.py"),

    (45, "glow-audit-and-fix", "GLOW - Audit and Fix",
     44, 46, "Guided confidence, not a compliance dashboard: plain-language audits of the document in front of you, in-place selection fixes, and whole-document fixes with a before/after compare.",
     "quill/core/glow/ if exists, quill/ui/glow_dialog.py if exists, quill/ui/main_frame_glow.py if exists"),

    (46, "glow-for-files", "GLOW for Files",
     45, 47, "Scored, graded audits of Word, PowerPoint, Excel, PDF, and EPUB; non-destructive Fix File that never touches the original; and the signature-verified engine update path.",
     "quill/core/glow/ if exists, quill/ui/glow_files_dialog.py if exists, quill/core/glow/engine.py if exists"),

    (49, "braille-production", "Braille Production",
     48, 50, "BRF, BRL, PEF and UEB workflows; Read Layout Metrics and the longest-line repair loop; trailing-space cleanup; and the honest cell-two display workaround story.",
     "quill/ui/main_frame_braille.py, quill/core/braille/ if exists, quill/stability/brf.py if exists"),

    (50, "quillins-and-the-console", "Quillins and the Developer Console",
     49, 51, "The extension system: worker-process fault isolation, Python and JavaScript Quillins, the deliberately-gated marketplace, and the accessible scripting console that turns users into toolmakers.",
     "quill/core/schemas/extension.json, quill/quillins_bundled/, quill/ui/main_frame_quillins.py, quill/tools/quillin_lint.py"),

    (52, "trust-community-finale", "Trust, Community, and the Road Ahead",
     51, 53, "The rules, the community and its receipts, the public roadmap, and what QUILL proves about designing screen-reader-first. A season checkpoint, not the end.",
     "quill/stability/, docs/QUILL-PRD.md, README.md, community links"),
]

TEMPLATE = """You are writing episode {n} of The QUILL Cast, a 54-episode audio course on QUILL.
The previous episode is episode {prev} and the next episode is episode {next}.

**Topic:** {title}

**Goal:** Write a 3,500-4,500 word podcast script that walks the listener through this
feature family with the same depth and honesty as the surrounding deep-dive episodes.
The script must include:
- 7-9 [PAUSE] markers for section breaks
- Liam opens, Jessica recaps the previous episode, both set today's frame
  (or Jessica opens, Liam recaps - vary the pattern, don't always make Jessica recap)
- A "do this now" interactive beat before any hands-on segment
  (e.g., "pause the audio, do the step, then come back")
- A code-verified walkthrough of the actual feature
- Honest corrections when docs/code drift apart (we verify against code)
- 4-step homework at the end
- Closing signoff

**Code references to verify claims against:**
{refs}

**File to write:**
S:\\QUILL\\docs\\podcast\\scripts\\ep{n:02d}-{slug}.txt

**Format:** alternating [LIAM] / [JESSICA] / [PAUSE] markers, one turn per block.
The TTS engine will speak each [LIAM]/[JESSICA] block as one voice turn.

After writing, report back the final word count and [PAUSE] count.
"""

for n, slug, title, prev, next_num, topic, refs in MAIN:
    prev_text = f"episode {prev}" if prev else "this is episode 1 of 54"
    next_text = f"episode {next_num}" if next_num else "this is the series finale"
    brief = TEMPLATE.format(
        n=n, prev=prev_text, next=next_text, title=title, slug=slug, refs=refs
    )
    brief_path = BRIEFS_DIR / f"ep{n:02d}-{slug}.txt"
    brief_path.write_text(brief, encoding="utf-8")
    print(f"Wrote brief: {brief_path}")

print(f"Total: {len(MAIN)} briefs")
