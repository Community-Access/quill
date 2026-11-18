"""QUILL's own guided tutorials: its tracks, and its lessons assembled.

Sixty-eight lessons in twelve tracks. The engine -- what a step is, how one
renders, where progress is kept -- is shared with Quill Radio, QUILL Cast and
Quill Weather in :mod:`quill.core.tutorials`; this is QUILL's content.

QUILL is by far the largest app in the family, so the set is deliberately not
a tour of everything: it is the first hour, the writing, the reading, how much
the app says, the assistant, the parts you meet in the second week, WordPress,
a new site owner's first week, the Workbench on the Practice Site, Break It on
Purpose, and Forms. The menus and the command
palette cover the rest, and the user guide covers the rest of the rest.
"""

from __future__ import annotations

from quill.core.quill_tutorials import (
    first_hour,
    living_with_it,
    reading,
    voice_and_ai,
    writing,
)
from quill.core.tutorials.coding_lessons import CODING_TRACK, coding_lessons
from quill.core.tutorials.dictation_lessons import dictation_lessons
from quill.core.tutorials.forms_lessons import forms_lessons
from quill.core.tutorials.github_lessons import GITHUB_TRACK, github_lessons
from quill.core.tutorials.model import Track, TutorialSet, build
from quill.core.tutorials.wordpress_break_it_lessons import BREAK_TRACK, break_it_lessons
from quill.core.tutorials.wordpress_first_week import FIRST_WEEK_TRACK, first_week_lessons
from quill.core.tutorials.wordpress_lessons import wordpress_lessons
from quill.core.tutorials.wordpress_practice_lessons import PRACTICE_TRACK, practice_lessons
from quill.core.tutorials.wordpress_practice_more import more_practice_lessons
from quill.core.tutorials.wordpress_practice_sites import site_practice_lessons
from quill.core.tutorials.wordpress_site_care_lessons import site_care_lessons

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
    # A new site owner's first week (WP-R-049), shared with QUILL Lite.
    FIRST_WEEK_TRACK,
    # The Workbench on the Practice Site (2026-11-13), and Break It on Purpose
    # (WP-R-049); QUILL Lite opens the same Workbench and teaches both.
    PRACTICE_TRACK,
    BREAK_TRACK,
    Track(
        "forms",
        "Forms",
        "Start a form from a template, add questions and a rule, check it, "
        "fill it in yourself, save it in large print or braille, and publish it "
        "to your site and read the responses.",
    ),
    # GitHub on the practice repository (GitHub PRD 22.8 and D8, 2026-11-18).
    GITHUB_TRACK,
    # The Developer profile's lesson; shown only while core.developer is on.
    CODING_TRACK,
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
    # One short lesson a day for a new site owner (WP-R-049).
    first_week_lessons(lambda name: f"wordpress.{name}", surfaces=("QUILL",), app="QUILL"),
    # Three Workbench lessons that work only on the Practice Site (2026-11-13).
    practice_lessons(),
    # Looking after a site, on the Practice Site too (9.17, gap 12).
    site_care_lessons(),
    # Menus, people, updates, spam, custom types, staging, Site Sets (WP-R-049).
    more_practice_lessons(),
    site_practice_lessons(),
    # Break It on Purpose: four problems put there on purpose (WP-R-049).
    break_it_lessons(),
    # The seven 2026-11-04 Forms lessons, shared with QUILL Lite.
    forms_lessons(
        lambda name: f"forms.{name}",
        save="file.save",
        track="forms",
        surfaces=("QUILL",),
        app="QUILL",
    ),
    github_lessons(),
    coding_lessons(
        {
            "open_folder": "project.open_folder",
            "task": "tools.hosted_ai_task",
            "undo": "project.undo_turn",
            "stop_label": "the QUILL key, then K",
        },
        surfaces=("QUILL",),
    ),
)
