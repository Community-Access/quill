"""The Tools > Dictation rows of QUILL Lite's menu bar.

Split out of :mod:`quill.core.lite.commands` under GATE-11 when Transcribe
Audio File arrived (2026-10-05), and spliced back into ``COMMANDS`` where the
table marks. The shape of every row is the table's (``menu, label, key,
handler, kind``); see that module.

Every command here is shared with QUILL (``quill/ui/windows_dictation_*.py``)
on the same chord (rule 2), and ``tests/unit/ui/test_dictation_parity.py``
fails on any difference.

* **Ctrl+F11**, Dictation On: Word's Alt+grave is a dead key on many layouts,
  and QUILL's Ctrl+F9 is Locked Dictation, another engine (rule 2).
  Checkable: "am I heard?"
* **Alt+Shift+F6**, Dictation Settings.
* **Shift+F11**, Recent Phrases (2026-09-28, dict.md 3.3): the last phrases
  said, on the key dictation runs on.
* **Alt+Shift+F10**, My Words and Phrases (dict.md 5): the window that teaches
  dictation your words, beside Settings' Alt+Shift+F6.
* **Shift+F5**, Transcribe a Recording (2026-10-05): a recording into text, in
  the background, with any engine dictation has. Rule 9 -- an occasional
  command gets *a* key, not a short one. Shift+F5 is free in both editors and
  is nothing either editor does in Word (Go Back), Notepad or WordPad; every
  function-key chord past F9 is taken, and Ctrl+Alt+Shift+F11 is a QuillVille
  launcher row.
* **Ctrl+Shift+F11**, Switch Dictation Language (2026-10-05, dict.md question
  5): beside Ctrl+F11 and Shift+F11, so the dictation keys stay one family.
  Free in QUILL Lite; in QUILL it was Forget External Change Answers, a
  once-a-year command that rule 9 says needs *a* key rather than this one, and
  which moved to Ctrl+Shift+0 (keymap.py says so where it is bound).
* **Ctrl+Alt+Shift+PageDown**, Live Transcript, and **Ctrl+Alt+Shift+PageUp**,
  Dictation Context for This Document (2026-10-05, question 8): rule 9 -- a few
  times a month gets a long chord. Every F-key chord near the others is taken in
  one editor or the other; these two are free across the whole family, carry no
  Word or Windows meaning, and are not AltGr characters on any layout, which
  rules out Ctrl+Alt with a digit or punctuation.
* **Alt+F9**, Dictation Status: QUILL's key for the same question (rule 2).
"""

from __future__ import annotations

DICTATION_ROWS: tuple[tuple[str, str, str, str, str], ...] = (
    ("&Tools|&Dictation", "Dictation &On", "Ctrl+F11", "cmd_toggle_dictation", "check"),
    ("&Tools|&Dictation", "Dictation &Settings...", "Alt+Shift+F6", "cmd_dictation_settings", ""),
    ("&Tools|&Dictation", "Recent &Phrases...", "Shift+F11", "cmd_dictation_recent", ""),
    ("&Tools|&Dictation", "My &Words and Phrases...", "Alt+Shift+F10", "cmd_dictation_words", ""),
    (
        "&Tools|&Dictation",
        "Transcribe a &Recording...",
        "Shift+F5",
        "cmd_transcribe_audio_file",
        "",
    ),
    (
        "&Tools|&Dictation",
        "Switch Dictation &Language",
        "Ctrl+Shift+F11",
        "cmd_switch_dictation_language",
        "",
    ),
    (
        "&Tools|&Dictation",
        "Start or Stop Live &Transcript",
        "Ctrl+Alt+Shift+PageDown",
        "cmd_live_transcript",
        "",
    ),
    (
        "&Tools|&Dictation",
        "Dictation &Context for This Document...",
        "Ctrl+Alt+Shift+PageUp",
        "cmd_dictation_context",
        "",
    ),
    ("&Tools|&Dictation", "Dictation St&atus", "Alt+F9", "cmd_dictation_status", ""),
)
