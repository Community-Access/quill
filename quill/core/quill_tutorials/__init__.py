"""QUILL's own guided tutorials: its tracks, and its lessons assembled.

Forty-four lessons in eight tracks. The engine -- what a step is, how one
renders, where progress is kept -- is shared with Quill Radio, QUILL Cast and
Quill Weather in :mod:`quill.core.tutorials`; this is QUILL's content.

QUILL is by far the largest app in the family, so the set is deliberately not
a tour of everything: it is the first hour, the writing, the reading, how much
the app says, the assistant, the parts you meet in the second week, WordPress, and Forms. The
menus and the command palette cover the rest, and the user guide covers the
rest of the rest.
"""

from __future__ import annotations

from quill.core.quill_tutorials import (
    first_hour,
    living_with_it,
    reading,
    voice_and_ai,
    writing,
)
from quill.core.tutorials.dictation_lessons import dictation_lessons
from quill.core.tutorials.forms_lessons import forms_lessons
from quill.core.tutorials.model import Track, TutorialSet, build
from quill.core.tutorials.wordpress_lessons import wordpress_lessons

#: QUILL's tracks, in teaching order.
TRACKS: tuple[Track, ...] = (
    Track(
        "first-hour",
        "Your first hour",
        "Write and save something, learn the four ways of getting anywhere, "
        "meet the QUILL key, and learn what to press when you are lost.",
    ),
    Track(
        "writing",
        "Writing and editing",
        "Selecting and moving text without a mouse, finding and replacing at "
        "every level of ambition, structure and formatting, words, and the one "
        "structure plain caret movement handles badly.",
    ),
    Track(
        "reading",
        "Reading and reviewing",
        "Having the document read to you, seeing the formatting that is "
        "normally hidden, single-letter movement, and inspecting a document "
        "somebody else wrote.",
    ),
    Track(
        "voice",
        "How much QUILL says",
        "Verbosity profiles, the channels that carry an announcement, and the "
        "echo of everything QUILL has just said.",
    ),
    Track(
        "ai",
        "The assistant, if you want one",
        "Optional, explicit, and honest about what it did: setting up a "
        "provider or running on-device, asking a question, and the commands "
        "that work on one selection at a time.",
    ),
    Track(
        "living",
        "Living with it",
        "Shaping the app to the work you actually do, the safety net "
        "underneath it, formats other people send you, braille files, and the "
        "family of apps QUILL sits in.",
    ),
    Track(
        "wordpress",
        "WordPress",
        "Connect your site, write and publish a post, fix a page you found by "
        "its address, pictures with alternative text, the check before you "
        "publish, earlier versions, and comments.",
    ),
    Track(
        "forms",
        "Forms",
        "Start a form from a template, add questions and a rule, check it, "
        "fill it in yourself, save it in large print or braille, and publish it "
        "to your site and read the responses.",
    ),
)

#: Every QUILL lesson, in teaching order.
CATALOGUE: TutorialSet = build(
    "quill",
    TRACKS,
    first_hour.TUTORIALS,
    writing.TUTORIALS,
    reading.TUTORIALS,
    voice_and_ai.TUTORIALS,
    # The five 2026-10-05 dictation lessons and the shared audio-file lesson.
    dictation_lessons(
        {
            "toggle": "tools.windows_dictation_toggle",
            "language": "tools.windows_dictation_switch_language",
            "transcript": "tools.windows_dictation_live_transcript",
            "status": "tools.dictation_status",
            "transcribe": "tools.windows_dictation_transcribe_file",
        },
        track="voice",
        surfaces=("QUILL",),
    ),
    living_with_it.TUTORIALS,
    # The seven 2026-11-04 WordPress lessons, shared with QUILL Lite.
    wordpress_lessons(
        lambda name: f"wordpress.{name}",
        save="file.save",
        track="wordpress",
        surfaces=("QUILL",),
        app="QUILL",
    ),
    # The seven 2026-11-04 Forms lessons, shared with QUILL Lite.
    forms_lessons(
        lambda name: f"forms.{name}",
        save="file.save",
        track="forms",
        surfaces=("QUILL",),
        app="QUILL",
    ),
)
