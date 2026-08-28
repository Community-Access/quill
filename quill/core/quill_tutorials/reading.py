"""QUILL, track 3: reading, reviewing, and inspecting.

Four lessons. Have the document read to you, see the formatting that is
normally hidden, inspect a character that is not what it looks like, and move
through a document the way a screen-reader user moves through a web page.
"""

from __future__ import annotations

from quill.core.tutorials.model import Step, Tutorial

TUTORIALS: tuple[Tutorial, ...] = (
    Tutorial(
        slug="read-aloud",
        title="Have it read to you",
        track="reading",
        minutes=6,
        surfaces=("QUILL",),
        summary=(
            "Start, pause and stop Read Aloud, choose a voice worth listening to, "
            "and know which voices are on your machine and which are a download."
        ),
        steps=(
            Step(
                title="Start reading",
                body=(
                    "Read Aloud starts from the cursor and pauses on the same key. "
                    "It is a different thing from your screen reader: it reads the "
                    "document as a document, at a pace you set, while your reader "
                    "keeps doing its own job."
                ),
                command="tools.read_aloud_start_pause",
                hear="The document, from where you were.",
            ),
            Step(
                title="Stop it",
                body=(
                    "Stop ends the pass rather than pausing it. Pause keeps your "
                    "place, which is what you want when somebody speaks to you; "
                    "Stop is what you want when you are done."
                ),
                command="tools.read_aloud_stop",
                hear="Silence, and the status bar's read-aloud cell going quiet.",
            ),
            Step(
                title="Know which voices you already have",
                body=(
                    "The Windows system voice runs on SAPI 5 and is always there, "
                    "offline, with no download -- it is the floor that keeps Read "
                    "Aloud working immediately. DECtalk, eSpeak NG, Piper and "
                    "Kokoro are explicit downloads, so a base install stays small."
                ),
                hear="The voice list, with each engine named.",
            ),
            Step(
                title="Audition one before you commit",
                body=(
                    "Preview in Manage Voices synthesises the phrase with the real "
                    "voice when it is installed, and plays a short pre-recorded "
                    "sample when it is not -- so you can hear a neural voice before "
                    "deciding to download 120 MB of it."
                ),
                hear="The sample, and a note when it is a recording rather than the real thing.",
                note=(
                    "Rate, volume and pitch apply to real synthesis, so they stay "
                    "dimmed until the voice is downloaded. Nothing pretends to work."
                ),
            ),
            Step(
                title="Read a document that is not in English",
                body=(
                    "The Windows engine lists every voice installed on your PC in "
                    "any language, and the Kokoro pack includes Spanish, French, "
                    "Hindi, Italian and Brazilian Portuguese. Pick the voice whose "
                    "language matches the document."
                ),
                hear="The document, pronounced correctly rather than phonetically.",
            ),
            Step(
                title="Turn a document into audio",
                body=(
                    "The Audiobook and Batch Speech wizard converts a folder of "
                    "documents to speech audio, or builds a chaptered audiobook. It "
                    "asks one thing at a time -- what to read, who reads it, how "
                    "chapters work, and where the output goes."
                ),
                command="tools.speech_batch_export",
                hear="The wizard, one question per page.",
            ),
        ),
        closing=(
            "The system voice is always there; everything else is an explicit "
            "choice you can audition first."
        ),
        then=("see-the-hidden-codes",),
    ),
    Tutorial(
        slug="see-the-hidden-codes",
        title="See the formatting that is normally hidden",
        track="reading",
        minutes=6,
        surfaces=("QUILL",),
        summary=(
            "Reveal Codes -- the WordPerfect feature rebuilt for a screen reader "
            "-- and the character inspector that tells a smart quote from a "
            "straight one."
        ),
        steps=(
            Step(
                title="Open Reveal Codes",
                body=(
                    "A pane below the editor shows your document as an ordered "
                    "stream of bracketed codes and text: Bold On, Font, Heading 2, "
                    "Tab, Hard Return, No-Break Space. The editor itself does not "
                    "change -- this is a window onto the scaffolding."
                ),
                command="view.reveal_codes_toggle",
                keys=("Alt+F3",),
                hear="The pane, and the code or text at your position.",
            ),
            Step(
                title="Move between the two panes",
                body=(
                    "F6 cycles Editor, Reveal Codes, Status Bar, and the two "
                    "carets stay in sync however you move -- arrows, word jumps, "
                    "Home and End, or a jump from Find. Sit in whichever one you "
                    "like; your place tracks along."
                ),
                keys=("F6", "Shift+F6"),
                hear="The region you entered, then your position in it.",
            ),
            Step(
                title="Walk the codes",
                body=(
                    "Left and Right step over a whole code as a single unit -- one "
                    "press crosses Bold On and your reader says bold on, never "
                    "spelled out. An opening code also tells you how far its "
                    "formatting reaches: bold on, 12 characters."
                ),
                keys=("Left arrow", "Right arrow", "Ctrl+Left", "Ctrl+Right"),
                hear="Each code named as a unit, with its reach.",
            ),
            Step(
                title="Edit a formatted run in place",
                body=(
                    "Land on text between a pair of codes and press F2: the pane "
                    "restricts you to that region, Enter applies your change and "
                    "Escape cancels. The surrounding codes are left exactly as they "
                    "were, and a nested code comes along with the run."
                ),
                keys=("F2", "Enter", "Escape"),
                hear="The region you are editing, then the change applied.",
            ),
            Step(
                title="Choose how it reads",
                body=(
                    "Flowed renders the codes inline within the running text and is "
                    "the closest match to the classic view; Structured lists one "
                    "item per code for scanning. Verbosity chooses quiet, balanced "
                    "or detailed -- the last adds Unicode notes for invisibles."
                ),
                hear="The view and verbosity you chose, remembered between sessions.",
            ),
            Step(
                title="Inspect a single character",
                body=(
                    "Describe Character at Cursor names what is actually under the "
                    "cursor: a curly quote against a straight one, a no-break space, "
                    "an invisible zero-width space that quietly breaks a search. It "
                    "gives the name, the code point, the category and a note for the "
                    "invisibles."
                ),
                hear="The character's name, code point and category, in one pass.",
                note=(
                    "It ships without a shortcut; assign one in the Keymap Editor "
                    "if you inspect text often. Search for Describe Character."
                ),
            ),
        ),
        closing=(
            "Reveal Codes costs nothing until you open it, and it is the answer "
            "to why does this line behave differently."
        ),
        then=("quick-nav",),
    ),
    Tutorial(
        slug="quick-nav",
        title="Quick Nav: single-letter movement",
        track="reading",
        minutes=4,
        surfaces=("QUILL",),
        summary=(
            "Browse mode, where single letters move by structure -- the habit "
            "every screen-reader user already has from the web, brought into a "
            "text editor."
        ),
        steps=(
            Step(
                title="Turn it on",
                body=(
                    "Press the QUILL key twice and Quick Nav locks on. This is the "
                    "most common path: the first press arms the prefix, the second "
                    "locks browse mode. It stays until Escape."
                ),
                keys=("Ctrl+Shift+Grave", "Ctrl+Shift+Grave"),
                hear="Browse mode on.",
            ),
            Step(
                title="Move by heading",
                body=(
                    "H moves to the next heading, exactly as it does on a web "
                    "page. That is the point of the whole mode: the movement you "
                    "already know, in a document you are writing."
                ),
                keys=("H",),
                hear="The heading, with its level.",
            ),
            Step(
                title="Move by paragraph and sentence",
                body=(
                    "P moves by paragraph, S by sentence. Reading a draft this way "
                    "-- sentence by sentence rather than line by line -- is how "
                    "you hear a sentence that runs on."
                ),
                keys=("P", "S"),
                hear="Each paragraph or sentence as you land on it.",
            ),
            Step(
                title="Leave",
                body=(
                    "Escape leaves browse mode and you are typing again. If you "
                    "would rather the mode expired on its own, the sticky setting "
                    "controls that -- and QUILL Key + N arms it for one action "
                    "only."
                ),
                keys=("Escape",),
                hear="Browse mode off.",
            ),
            Step(
                title="Rebind what the letters do",
                body=(
                    "Quick Nav actions appear in the Keymap Editor as their own "
                    "entries, so the letters are yours to change. Nothing in QUILL "
                    "asks you to accept a key you would not have chosen."
                ),
                hear="The editor, with the Quick Nav entries listed.",
            ),
        ),
        closing=(
            "One mode, the letters you already know, and Escape to leave. It is "
            "the fastest way to read a long draft you wrote yourself."
        ),
        then=("inspect-and-compare",),
    ),
    Tutorial(
        slug="inspect-and-compare",
        title="Inspect a document you did not write",
        track="reading",
        minutes=5,
        surfaces=("QUILL",),
        summary=(
            "Summaries, folds, compare, and the report tabs that make somebody "
            "else's file readable rather than mysterious."
        ),
        steps=(
            Step(
                title="Ask what this document is",
                body=(
                    "Document Summary is the one-shot answer: what it is, how "
                    "long, and how it is shaped. It is the right first key on a "
                    "file somebody has just sent you."
                ),
                command="document.summary",
                hear="The summary, in one pass.",
            ),
            Step(
                title="Collapse what you are not reading",
                body=(
                    "Toggle Fold collapses a section; List Folds shows what is "
                    "folded; Next Fold and Previous Fold move between them. In a "
                    "long structured document, folding is how you make the shape "
                    "audible."
                ),
                command="edit.toggle_fold",
                hear="Folded, and how many lines went away.",
            ),
            Step(
                title="Compare two versions",
                body=(
                    "The compare tools open their summary as an ordinary document "
                    "tab -- artifacts stay close to the work that made them -- and "
                    "Next Difference, Previous Difference and Announce Difference "
                    "walk it by ear."
                ),
                command="tools.compare_next_difference",
                hear="Each difference, described rather than shown.",
            ),
            Step(
                title="Read the extraction report",
                body=(
                    "When QUILL brings text in from a PDF or a scanned document, "
                    "the intake report says how it went -- what it was confident "
                    "about and what it was not. Reading it is how you know whether "
                    "to trust the text."
                ),
                command="tools.document_intake_report",
                hear="The report, as an ordinary tab you can arrow through.",
            ),
            Step(
                title="Find the characters that do not belong",
                body=(
                    "The non-ASCII report lists what is unusual in the document, "
                    "and jumping between the report and the source takes you "
                    "straight to each one. It is how a stray byte-order mark or a "
                    "curly quote stops being a mystery."
                ),
                command="power.non_ascii_jump_to_report",
                hear="The report, then each occurrence as you jump to it.",
            ),
        ),
        closing=(
            "Summary first, folds for shape, compare for change, and the reports "
            "for what the file will not tell you itself."
        ),
    ),
)
