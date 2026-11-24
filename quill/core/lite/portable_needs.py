"""What QUILL Lite's portable zip must carry, feature by feature (2026-11-23).

QUILL Lite ships two ways. The installer runs it on the shared QuillVille
runtime, which carries every optional dependency group in pyproject's
``runtime`` extra and the tools ``standalone/runtime/stage_runtime_tools.ps1``
stages. The portable zip carries its own Python and only what
``standalone/studio/scripts/build_portable.py`` installs for product
``quilllite``. Until 2026-11-23 that list was written for "an editor and
nothing else", and the editor had grown: the portable copy offered the GitHub
Workbench, spell check, AI help, the Developer profile and the WordPress
Practice Site, and could not run any of them (Jeff, 2026-11-23: the portable
must carry everything QUILL Lite offers, the same as its installer).

This module is the audit, as data, so it cannot quietly go stale:

* :data:`MENU_NEEDS` classifies **every menu** in QUILL Lite's command table
  (:data:`quill.core.lite.commands.COMMANDS`) by the groups and tools its
  commands need. A new menu fails ``test_lite_portable_needs.py`` until it is
  classified here.
* :data:`ALWAYS_NEEDS` is the same for what no single menu owns: opening a
  PDF, the sounds, check-as-you-type.
* :data:`EXCLUDED_GROUPS` and :data:`EXCLUDED_TOOLS` give the reason for every
  group and tool the shared runtime carries that QUILL Lite does not use. Every
  runtime group and tool is either needed or excluded with a reason, so a group
  added to the runtime fails the test until somebody decides.
* The test holds the ``quilllite`` product's ``dep_groups`` and
  ``runtime_tools`` equal to :func:`bundled_groups` and :func:`bundled_tools`:
  exactly these, nothing missing and nothing extra.

Wx-free and import-free: data only.
"""

from __future__ import annotations

from dataclasses import dataclass

__all__ = [
    "ALWAYS_NEEDS",
    "BASE_GROUPS",
    "EXCLUDED_GROUPS",
    "EXCLUDED_TOOLS",
    "GROUP_IMPORTS",
    "MENU_NEEDS",
    "Need",
    "bundled_groups",
    "bundled_tools",
]


@dataclass(frozen=True)
class Need:
    """What one feature needs beyond the editor itself, and why."""

    groups: tuple[str, ...] = ()
    tools: tuple[str, ...] = ()
    why: str = ""


#: Groups every copy carries whatever is switched on: the window, the screen
#: reader bridges and the Word stack QUILL Lite edits with.
BASE_GROUPS: tuple[str, ...] = ("ui", "docx")

_NOTHING = Need(why="QUILL's own code and its base dependencies only.")
_GITHUB = Need(("github",), why="The GitHub Workbench and Open from GitHub talk through PyGithub.")
_WORDPRESS = Need(
    tools=("nodejs", "wp-playground-cli"),
    why="Tools > WordPress > Your Sites > Practice Site runs WordPress Playground on "
    "the bundled Node.js (quill/core/wordpress/workbench_practice.py).",
)
_AI = Need(
    ("ai-copilot",),
    ("copilot", "codex"),
    "Choose Your AI offers My GitHub Copilot (the Copilot SDK and its runtime.node) "
    "and ChatGPT through Codex (codex-app-server.exe); the hosted free AI needs "
    "nothing more than requests.",
)

#: Every menu path in QUILL Lite's command table, and what its commands need.
MENU_NEEDS: dict[str, Need] = {
    "&Edit": _NOTHING,
    "&Edit|&Lines": _NOTHING,
    "&Edit|&Matches": _NOTHING,
    "&Edit|Agent Wor&k": Need(
        ("ai-copilot",), ("copilot", "codex"), "Agent work runs on the AI engines."
    ),
    "&Edit|Clip&board": _NOTHING,
    "&Edit|Replace &Jobs": _NOTHING,
    "&Edit|Selectio&n": _NOTHING,
    "&Edit|WordPress": _WORDPRESS,
    "&File": Need(
        ("office-text", "ocr", "math", "github"),
        why="Open reads PDF, Excel and scanned pages (pdfplumber, pypdf, pypdfium2, "
        "openpyxl, Windows OCR); Export as HTML writes equations as MathML "
        "(latex2mathml, lite guide chapter 3); GitHub Workbench, Clone Repository "
        "and Manage GitHub Accounts are here too.",
    ),
    "&File|&WordPress": _WORDPRESS,
    "&File|&WordPress|Send and &Copy": _NOTHING,
    "&File|Scri&be for Documents": Need(
        ("live-dictation",),
        why="Scribe's progress channel is a websocket (websockets, which ships in live-dictation).",
    ),
    "&GitHub": _GITHUB,
    "&Help": _NOTHING,
    "&Insert": _NOTHING,
    "&Navigate": _NOTHING,
    "&Navigate|&Bookmarks": _NOTHING,
    "&Navigate|&Code": Need(
        tools=("nodejs", "language-servers"),
        why="Navigate > Code > Language Servers runs the bundled servers on the "
        "bundled Node.js (quill/core/lsp/servers.py).",
    ),
    "&Navigate|&Highlighted Passages": _NOTHING,
    "&Navigate|&Table": _NOTHING,
    "&Tools": Need(
        ("audio", "windows-media"),
        why="Sound Scheme and App Sounds: sound_lib mixes the sounds and sets their "
        "volume (winsound can do neither), and App Sounds Play On lists the sound "
        "cards through Windows Media (quill/ui/audio/output_routing.py).",
    ),
    "&Tools|&AI": _AI,
    "&Tools|&AI|Accounts and &Usage": _AI,
    "&Tools|&Change Case": _NOTHING,
    "&Tools|&Dictation": Need(
        ("live-dictation", "audio-files"),
        why="Moonshine and Whisper run in sherpa-onnx with numpy and sounddevice; "
        "Transcribe a Recording reads Ogg and Opus with soundfile, which Windows "
        "Media Foundation cannot (quill/core/windows_dictation/audio_file.py).",
    ),
    "&Tools|&Spelling": Need(
        ("spellcheck",),
        why="pyenchant with Hunspell; without it spell check falls back to a word "
        "list and offers no other languages (quill/core/spellcheck.py).",
    ),
    "&Tools|Dictionar&y": _NOTHING,
    "&Tools|Forms": Need(
        ("office-text",), why="XLSForm import and export read and write Excel (openpyxl)."
    ),
    "&Tools|Indentin&g": _NOTHING,
    "&Tools|Inline &Notes": _NOTHING,
    "&Tools|WordPress": _WORDPRESS,
    "&Tools|WordPress|&Design": _NOTHING,
    "&Tools|WordPress|&Manage": _NOTHING,
    "&Tools|WordPress|&Plugin Extras": _NOTHING,
    "&Tools|WordPress|&Your Sites": _WORDPRESS,
    "&Tools|WordPress|M&ore Media": Need(
        ("live-dictation", "audio-files"),
        why="Captions for Video and Transcript for Audio read the recording and "
        "transcribe it with dictation's engines. Make a Listening Version also "
        "needs ffmpeg, which neither QUILL Lite download carries.",
    ),
    "&View": Need(
        ("windows-media", "github"),
        why="Play Media Here plays through the modern Windows Media engine (winrt); "
        "GitHub Workbench Mode is here too.",
    ),
    "&View|&Problems": _NOTHING,
    "&Window": _NOTHING,
    "F&ormat": _NOTHING,
    "F&ormat|&Headings": _NOTHING,
    "F&ormat|Line Spacin&g": _NOTHING,
    "F&ormat|Structur&e": _NOTHING,
    "F&ormat|Word&Press": _NOTHING,
}

#: What no single menu owns.
ALWAYS_NEEDS: dict[str, Need] = {
    "Opening a PDF, a spreadsheet or a scanned page (Ctrl+O, drag and drop)": Need(
        ("office-text", "ocr"),
        why="quill/core/lite/open_prepare.py reads them on open.",
    ),
    "Check spelling as you type": Need(("spellcheck",), why="As Tools > Spelling."),
    "Sounds for what just happened": Need(
        ("audio", "windows-media"), why="As Tools > Sound Scheme."
    ),
}

#: Runtime groups QUILL Lite does not use, and why.
EXCLUDED_GROUPS: dict[str, str] = {
    "speech": "Its one package, sounddevice, already arrives with live-dictation.",
    "dictation": "SpeechRecognition: nothing in QUILL imports it any more.",
    "mp3": "mutagen tags and cover art: Audio Studio, Converter and Cast.",
    "glow": "The GLOW structured-document engine: QUILL's Check Accessibility. QUILL "
    "Lite's Markdown checks use the built-in text audit, which needs no package.",
    "social-app": "Quill Social only.",
    "pdf-ocr": "MarkItDown cannot start in the installed copy either (its file "
    "sniffer needs onnxruntime, which the runtime leaves out), so QUILL's own "
    "readers do this work in both (quill/io/office_text.py).",
    "tts-phonon": "Read Aloud voices; QUILL Lite has no Read Aloud.",
    "youtube": "Quill Radio and Quill Converter only.",
    "fasterwhisper": "An Audio Studio transcription engine; Lite's dictation uses sherpa-onnx.",
    "vosk": "As fasterwhisper.",
    "kokoro": "Read Aloud and Audio Studio voices; QUILL Lite has no Read Aloud.",
}

#: Runtime tools QUILL Lite does not use, and why.
EXCLUDED_TOOLS: dict[str, str] = {
    "ripgrep": "Nothing calls rg.exe yet: the project name index still walks the "
    "folder in Python (docs/design/intellisense.md, open item).",
}

#: A module from each group the portable build imports to prove it works
#: (build_portable.py ``must_import``). A native piece is named where there is
#: one, so a missing DLL fails the build rather than the first person to need it.
GROUP_IMPORTS: dict[str, str] = {
    "live-dictation": "sherpa_onnx",
    "office-text": "pdfplumber",
    "ocr": "winrt.windows.media.ocr",
    "docx": "docx",
    "spellcheck": "enchant",
    "audio": "sound_lib.output",
    "windows-media": "winrt.windows.media.playback",
    "math": "latex2mathml.converter",
    "audio-files": "soundfile",
    "github": "github",
    "ai-copilot": "copilot",
}


def _all_needs() -> list[Need]:
    return [*MENU_NEEDS.values(), *ALWAYS_NEEDS.values()]


def bundled_groups() -> tuple[str, ...]:
    """The optional-dependency groups QUILL Lite's portable must install."""
    found = {group for need in _all_needs() for group in need.groups}
    rest = sorted(found - set(BASE_GROUPS))
    return (*BASE_GROUPS, *rest)


def bundled_tools() -> tuple[str, ...]:
    """The runtime tools QUILL Lite's portable must carry in its tools folder."""
    return tuple(sorted({tool for need in _all_needs() for tool in need.tools}))
