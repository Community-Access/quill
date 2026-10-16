"""What every QUILL Transcribe window is *for* -- the F1 help's opening paragraph.

The same shape as every other family app's catalogue (Radio's, Cast's,
Inkwell's): wx-free, keyed by **window title** because the title is what a
window already announces and what a person quotes back, and composed by
:mod:`quill.ui.app_context_help` -- the purpose of the window first, then the
focused control's own help.

Gated (GATE-TRANSCRIBE-HELP, ``quill/tools/transcribe_help_audit.py``): every
window title constructed in ``quill/apps/transcribe*.py`` must resolve here.
The shared windows QUILL Transcribe opens (Dictation Settings, Speech Models,
Transcribe a Recording) are listed too, so F1 in them says what they are for
*here*.

Wording: one to three sentences, to the person, no key-by-key tours.
"""

from __future__ import annotations

#: Surface purposes by exact window title.
PURPOSES: dict[str, str] = {
    # -- the window --------------------------------------------------------------
    "QUILL Transcribe": (
        "QUILL Transcribe types what you say into the program you are using. This "
        "window shows whether dictation is on, which model and microphone it uses, "
        "and what happened last. Start dictation from your start and stop key or the "
        "tray menu; it writes only into the field you started in, and pauses if you "
        "move. Closing this window keeps QUILL Transcribe in the tray."
    ),
    # -- its own dialogs ---------------------------------------------------------
    "Set Up QUILL Transcribe": (
        "Choose your microphone, the speech model and, if you want one, the key "
        "that starts and stops dictation from any program. Finish keeps your "
        "choices; Skip changes nothing. Nothing listens and nothing downloads here."
    ),
    "Choose Model": (
        "Every speech model QUILL knows, each marked as running on this computer or "
        "sending your speech over the internet, with its languages and whether it is "
        "downloaded. The model you choose is used every time until you choose another."
    ),
    "Choose Microphone": (
        "The microphone QUILL Transcribe listens on. The Windows default follows "
        "whatever Windows is set to; a named microphone stays chosen."
    ),
    "Review Transcript": (
        "A finished transcript of a recording, read-only. Copy it, save it as a "
        "text file, or open it in QUILL; nothing is copied or typed anywhere unless "
        "you choose it."
    ),
    "Save Transcript As": ("Choose where to save the transcript as a plain text file."),
    "Start and Stop Key": (
        "Choose the key that starts and stops dictation from any program. It is "
        "Alt+Shift+Backslash unless you change it. Type another, press Record Key "
        "to press it instead, or leave the box empty for no key; a key another "
        "QuillVille app already uses is refused, and you are told whose it is."
    ),
    "Show and Hide Key": (
        "Choose one key that shows and hides the QUILL Transcribe window from any "
        "program, or leave the box empty for no key. A key another QuillVille app "
        "already uses is refused, and you are told whose it is."
    ),
    "Exit QUILL Transcribe": (
        "Dictation is paused with words that were never written. Exit throws them "
        "away and closes QUILL Transcribe; Cancel keeps it running so you can resume."
    ),
    "Practice Dictation": (
        "A field of QUILL Transcribe's own that dictation types into, so you can learn "
        "and test dictation without writing into another program. Start Dictation Here "
        "starts it in the field; Read This Sentence reads a sentence aloud and says how "
        "many words were heard as you said them."
    ),
    "Dictation Profile": (
        "Choose the kind of writing dictation is for: Standard, Email, Document, "
        "Markdown, Chat, Coding or Verbatim. A profile sets the pause, fillers and "
        "punctuation, and how headings, bold and italic are written."
    ),
    "QUILL Transcribe Tutorials": (
        "Five short lessons: a first dictation in the Practice window, pausing and "
        "resuming, commands with the command word, snippets by voice, and review. "
        "Try It runs a step's command for you."
    ),
    "Use OpenAI": (
        "Before your speech goes to OpenAI, this says what is sent and where. No "
        "keeps the model you had; nothing is sent unless you agree."
    ),
    # -- shared windows it opens -------------------------------------------------
    "Dictation Settings": (
        "The dictation settings QUILL Transcribe uses: the model, microphone, "
        "language, punctuation, and what you hear after each phrase. They are the "
        "same settings as dictation in QUILL and QUILL Lite, kept for this app."
    ),
    "More Dictation Settings": (
        "The rest of dictation's settings: pauses, fillers, dashes, wake phrase and "
        "the OpenAI model. Some only matter inside QUILL's own documents."
    ),
    "Speech Providers": (
        "Use a speech service you already have an account with -- Azure, Google, "
        "Amazon, Deepgram and others -- for dictation. Choose one to see what it can "
        "do and what it needs, enter that, test it, and save it; keys go to Windows "
        "Credential Manager. Then choose it as the speech engine in Dictation Settings."
    ),
    "Speech Models": (
        "The Model Library: download, check or remove the optional speech models. "
        "Each download shows its size first, is checked before it is used, and can "
        "be cancelled. A model that did not finish is never marked ready."
    ),
    "Dictation Commands": (
        "Everything dictation understands, to read with the arrow keys. In another "
        "program only the commands that do not need to read its text work."
    ),
    "Review Dictation": (
        "Dictated words wait here before they are inserted. Read them, type or keep "
        "dictating to change them, ask the AI to change them if AI is on, and hear "
        "what changed. Control Enter inserts them where they were going; nothing is "
        "written before that."
    ),
    "Review with AI": (
        "Before the first change is asked for, this says who receives the words "
        "being reviewed and what is sent. No is the default and sends nothing."
    ),
    "Discard These Words": (
        "The AI has changed these words. Yes throws them away and writes nothing; "
        "No keeps the review open."
    ),
    "Transcribe a Recording": (
        "Choose a recording and a model; it is transcribed in the background and "
        "the transcript waits in Notifications for you to review."
    ),
    "My Words and Phrases": (
        "The words, phrases and corrections dictation uses, the same list as QUILL. "
        "Import adds the new entries from a Markdown or CSV file after showing them; "
        "Export saves the list to one."
    ),
    "Import Words": (
        "What the file would add to your list, with the counts. Add Them adds them; "
        "nothing you already have is replaced."
    ),
    "Notifications": (
        "Finished, failed and cancelled transcriptions. Open one to review its transcript."
    ),
    "Send this recording to OpenAI?": (
        "Before a recording goes to OpenAI, this says what is sent. No sends nothing."
    ),
    "Find a Setting or Command": (
        "Every menu command in this app, searchable by name. Type part of a name; "
        "Down moves into the matches; Enter does the highlighted one."
    ),
    "Update downloaded": (
        "A new QUILL Transcribe is on disk and ready. Install and restart applies it "
        "and relaunches -- your settings are kept -- or Open folder shows the installer."
    ),
}

#: Purposes for windows whose titles carry live data, matched by prefix.
PREFIX_PURPOSES: tuple[tuple[str, str], ...] = (
    (
        "Help:",
        "This is the help window itself: the purpose of the window you were in, "
        "then the control you were on. Escape returns you to it.",
    ),
)

GENERIC_PURPOSE = (
    "A QUILL Transcribe window. Tab moves between its controls, Escape closes it, "
    "and F1 on any control explains that control."
)


def purpose_for_title(title: str) -> str:
    """The purpose paragraph for a window titled *title* (never empty)."""
    stripped = title.strip()
    exact = PURPOSES.get(stripped)
    if exact:
        return exact
    for prefix, purpose in PREFIX_PURPOSES:
        if stripped.startswith(prefix):
            return purpose
    return GENERIC_PURPOSE


def is_known_title(title: str) -> bool:
    """True when *title* resolves to an authored purpose (the gate's check)."""
    stripped = title.strip()
    if stripped in PURPOSES:
        return True
    return any(stripped.startswith(prefix) for prefix, _p in PREFIX_PURPOSES)
