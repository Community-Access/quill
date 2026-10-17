"""QUILL Transcribe's five lessons (D-25): start, pause and resume, commands
with the command word, snippets, and review.

Kept beside :mod:`quill.core.tutorials.dictation_lessons` (the editors' six)
rather than inside it, because that module is shared by two editors whose
lessons name editor commands, and these name QUILL Transcribe's: the Practice
window first of all, where dictation types into a field inside QUILL
Transcribe itself, so a first dictation never lands in a real program.

The wording follows :mod:`quill.core.tutorials.model`: one action a step, the
reason as well as the instruction, what you should hear, and no key promised in
prose -- a step names its command and the key renders.

Pure and wx-free.
"""

from __future__ import annotations

from quill.core.tutorials.model import Step, Tutorial

__all__ = ["transcribe_lessons"]

_PRACTICE = "Practice Dictation"


def transcribe_lessons(track: str) -> tuple[Tutorial, ...]:
    """The five lessons, in the order somebody new would take them."""
    surfaces = ("QUILL Transcribe", _PRACTICE)
    return (
        Tutorial(
            slug="transcribe-first-dictation",
            title="Your first dictation, in the Practice window",
            track=track,
            minutes=5,
            surfaces=surfaces,
            summary=(
                "Open the Practice window, dictate a sentence into its own field, and "
                "take the recognition test, without typing into any other program."
            ),
            steps=(
                Step(
                    title="Open the Practice window",
                    body=(
                        "Open Practice Dictation from the Dictation menu. It has a field "
                        "of its own, so nothing you say goes anywhere else while you learn."
                    ),
                    command="transcribe.practice",
                    hear='"Practice Dictation", then "Practice field, edit".',
                ),
                Step(
                    title="Start dictation in the practice field",
                    body=(
                        "With the focus in the practice field, press Start Dictation Here. "
                        "Your own start and stop key does the same while you are in the field."
                    ),
                    command="transcribe.practice_start",
                    hear='A rising tone and "Dictation on".',
                ),
                Step(
                    title="Say a sentence, then pause",
                    body=(
                        "Say: this is my first dictation period. Then stop talking for a "
                        "moment. The pause is what tells dictation the phrase is finished."
                    ),
                    hear="Your words read back, and they are in the practice field.",
                ),
                Step(
                    title="Take the recognition test",
                    body=(
                        "Press Read This Sentence and read the sentence shown above it "
                        "aloud. The field is cleared first, so only the sentence is scored."
                    ),
                    keys=("Alt+T",),
                    hear="How many words were right, and any that were heard differently.",
                    note=(
                        "Below 80 percent, try speaking a little slower, moving closer to "
                        "the microphone, or a larger model in Choose Model."
                    ),
                ),
            ),
            closing=(
                "You have dictated, and you know how well your microphone and model hear "
                "you. Next, dictate into a real program."
            ),
            then=("transcribe-pause-resume",),
        ),
        Tutorial(
            slug="transcribe-pause-resume",
            title="Pause and resume in another program",
            track=track,
            minutes=5,
            surfaces=("QUILL Transcribe",),
            summary=(
                "Dictate into Notepad, move away to see dictation pause and keep your "
                "words, and send them on with Resume."
            ),
            steps=(
                Step(
                    title="Start in a field of your own choosing",
                    body=(
                        "Open Notepad, put the focus in it, and press your start and stop "
                        "key. Dictation writes into that field and only that field."
                    ),
                    command="tools.windows_dictation_toggle",
                    hear='A rising tone and "Dictation on".',
                ),
                Step(
                    title="Move away while you talk",
                    body=(
                        "Switch to another window with Alt+Tab and say a sentence. Nothing "
                        "is typed into the window you moved to; your words are held."
                    ),
                    keys=("Alt+Tab",),
                    hear='"Paused", and how many phrases are held.',
                ),
                Step(
                    title="Resume where you started",
                    body=(
                        "Go back to Notepad and choose Resume. The held words are typed "
                        "into the field you started in, and dictation carries on."
                    ),
                    command="transcribe.resume",
                    hear="The held words, typed into Notepad.",
                    note=(
                        "Resume in This Field sends them to the field you switch to next "
                        "instead; Discard Held Words throws them away."
                    ),
                ),
            ),
            closing="A focus change never sends your words somewhere you did not choose.",
            then=("transcribe-commands",),
        ),
        Tutorial(
            slug="transcribe-commands",
            title="Commands with the command word",
            track=track,
            minutes=5,
            surfaces=surfaces,
            summary=(
                "Say QUILL before a command so it is never typed as words, and use "
                "command mode for several commands in a row."
            ),
            steps=(
                Step(
                    title="Dictate something to correct",
                    body=(
                        "In the practice field, start dictation and say a short sentence, "
                        "then pause, so there is a phrase for a command to act on."
                    ),
                    command="transcribe.practice_start",
                    hear="Your sentence read back.",
                ),
                Step(
                    title="Take it back by voice",
                    body=(
                        "Say: QUILL scratch that. The command word first is what makes it "
                        "a command; scratch that on its own is typed as words here."
                    ),
                    hear='A rising tone, then "Scratched" and your words.',
                ),
                Step(
                    title="Give a command with the key",
                    body=(
                        "Press Speak a Command, then say a command without the command "
                        "word, such as caps on. Pressed twice, it starts command mode."
                    ),
                    command="tools.windows_dictation_command",
                    hear='"Caps on."',
                    note="Say dictation mode, or wait, to go back to dictating.",
                ),
            ),
            closing="Say QUILL what can I say for a short list of what works here.",
            then=("transcribe-snippets",),
        ),
        Tutorial(
            slug="transcribe-snippets",
            title="Snippets and clips by voice",
            track=track,
            minutes=4,
            surfaces=surfaces,
            summary=(
                "Insert a saved snippet or a Copy Tray clip by saying its name, as one "
                "phrase that scratch that takes back."
            ),
            steps=(
                Step(
                    title="Start dictation in the practice field",
                    body=(
                        "Open the Practice window and start dictation there, so the snippet "
                        "goes into a field where it does no harm."
                    ),
                    command="transcribe.practice_start",
                    hear='"Dictation on".',
                ),
                Step(
                    title="Insert a snippet by name",
                    body=(
                        "Say: QUILL insert snippet, then the snippet's name. Snippets are "
                        "the ones you saved in QUILL; the whole snippet is typed at once."
                    ),
                    hear="The snippet's text read back.",
                ),
                Step(
                    title="Paste a clip",
                    body=(
                        "Say: QUILL paste clip one. The first slot of the Copy Tray is "
                        "typed, and QUILL scratch that takes all of it back out."
                    ),
                    hear="The clip's text read back.",
                ),
            ),
            closing="Snippets and clips only insert; they never read the other program's text.",
            then=("transcribe-review",),
        ),
        Tutorial(
            slug="transcribe-review",
            title="Review before it is typed",
            track=track,
            minutes=5,
            surfaces=surfaces,
            summary=(
                "Send what you dictate to Review Dictation first, change it there, and "
                "insert it when it reads right."
            ),
            steps=(
                Step(
                    title="Dictate into the practice field",
                    body=(
                        "Start dictation in the practice field and say two sentences, "
                        "pausing after each, so there is something worth reviewing."
                    ),
                    command="transcribe.practice_start",
                    hear="Each sentence read back.",
                ),
                Step(
                    title="Open the review",
                    body=(
                        "Press Review Dictation. The words wait there, in a field you can "
                        "read and edit, until you choose Insert or Discard."
                    ),
                    command="tools.windows_dictation_review",
                    hear='"Review Dictation", then the review field.',
                ),
                Step(
                    title="Insert when it reads right",
                    body=(
                        "Change anything you like with the keyboard, then choose Insert. "
                        "The words are typed into the field the session is locked to."
                    ),
                    hear="The words, typed into the practice field.",
                ),
            ),
            closing=(
                "Send dictation to review first, in More Dictation Settings, makes every "
                "phrase wait for you this way."
            ),
        ),
    )
