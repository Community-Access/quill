"""QUILL, track 6: living with it.

Five lessons for after the first week: shaping the app to the work you
actually do, the safety net underneath it, formats other people send you,
braille files, and the family of apps QUILL sits in.
"""

from __future__ import annotations

from quill.core.tutorials.model import Step, Tutorial

TUTORIALS: tuple[Tutorial, ...] = (
    Tutorial(
        slug="profiles-and-keys",
        title="Make QUILL the size you need",
        track="living",
        minutes=6,
        surfaces=("QUILL",),
        summary=(
            "Feature profiles, per-feature control, keyboard packs, and the "
            "keymap editor that tells you what a key is already doing."
        ),
        steps=(
            Step(
                title="Understand what a profile is",
                body=(
                    "A profile decides which feature clusters are on, quiet or "
                    "off. It keeps QUILL calm for somebody new without stripping "
                    "power from somebody advanced -- and it is a starting point "
                    "rather than a cage."
                ),
                hear="The profile you are on, and what it covers.",
            ),
            Step(
                title="Pick the one that matches your work",
                body=(
                    "Essential is the calmest possible editor. Writer, Author or "
                    "Student, Reader and Student, Office and Admin, Developer and "
                    "Power Text, Low Vision, Braille and Screen Reader Power User, "
                    "Accessibility Professional, and Full Quill each surface a "
                    "different set."
                ),
                hear="Each profile with a plain-English preview of what you get.",
            ),
            Step(
                title="Switch profiles from anywhere",
                body=(
                    "Quick-switch is one chord away, and Undo the last profile "
                    "change is there when a switch was not what you wanted. You "
                    "can compare two profiles before choosing."
                ),
                command="help.switch_feature_profile",
                hear="The profile you switched to.",
            ),
            Step(
                title="Turn one feature on without changing profile",
                body=(
                    "Manage Individual Features is per-feature control on top of "
                    "your profile. Its Disabled features only view is the useful "
                    "one: scan what is off and switch on the two things you "
                    "actually miss."
                ),
                hear="Each feature with a description of what it does and what it depends on.",
                note=(
                    "Enabling a feature enables its dependencies; disabling one "
                    "turns off what depends on it, and QUILL says what changed."
                ),
            ),
            Step(
                title="Start from a keyboard you already know",
                body=(
                    "Keyboard packs make QUILL feel familiar from day one: Quill "
                    "Default, Writer, Navigation and Review, plus Windows Notepad, "
                    "Notepad++, VS Code and Microsoft Word. Hand-edit anything "
                    "afterwards and the label becomes Custom."
                ),
                hear="The pack you chose, applied.",
            ),
            Step(
                title="Ask what a key is already doing",
                body=(
                    "In the Keymap Editor, type a *shortcut* rather than a command "
                    "name and it flips to reverse lookup: it tells you which "
                    "command owns that key, or that it is unassigned and "
                    "available. You never have to guess whether a key is free."
                ),
                hear="The command that owns the key, by its friendly title.",
            ),
            Step(
                title="Let it check itself",
                body=(
                    "Run Diagnostics audits the whole keymap -- duplicates, "
                    "bindings for commands that no longer exist, unreadable "
                    "bindings, keys that are assigned but inert -- and offers to "
                    "heal the repairable ones in one step."
                ),
                hear="What it found, and what it can fix.",
            ),
        ),
        closing=(
            "A profile for the shape, individual features for the exceptions, a "
            "pack for the keyboard, and diagnostics when it all gets away from "
            "you."
        ),
        then=("the-safety-net",),
    ),
    Tutorial(
        slug="the-safety-net",
        title="The safety net",
        track="living",
        minutes=5,
        surfaces=("QUILL",),
        summary=(
            "What QUILL does about crashes, autosave, a screen reader that "
            "vanishes, and every question that could destroy something."
        ),
        steps=(
            Step(
                title="Know the rule",
                body=(
                    "Anything that closes or degrades QUILL without your asking "
                    "persists your work first. Everything in this lesson is that "
                    "one rule, applied in different places."
                ),
                hear="Nothing: this is the sentence the rest follows from.",
            ),
            Step(
                title="Recover after a crash",
                body=(
                    "If QUILL notices an earlier crash or an autosave state, the "
                    "next launch offers recovery rather than hoping you forgot. "
                    "The autosave cell in the status bar tells you when the last "
                    "one happened."
                ),
                keys=("F6",),
                hear="The autosave cell, with its timing.",
            ),
            Step(
                title="Know what happens if your screen reader stops",
                body=(
                    "QUILL watches the reader it detected at startup. One missed "
                    "check is ignored -- restarting JAWS or NVDA must never set "
                    "off alarms -- but a confirmed disappearance makes QUILL "
                    "snapshot every open document to autosave and then explain "
                    "through whatever can still speak."
                ),
                hear="The explanation, through another reader or QUILL's own voice.",
                note=(
                    "QUILL does not shut down when this happens. Restart your "
                    "reader when you are ready; QUILL announces when it sees it "
                    "again, and the event is in Notifications either way."
                ),
            ),
            Step(
                title="Trust the default answer",
                body=(
                    "Every confirmation that would destroy something has No as its "
                    "default button, and a build check keeps it that way for every "
                    "future dialog. Pressing Enter reflexively can never cost you "
                    "data."
                ),
                hear="The question, with No as the default.",
            ),
            Step(
                title="Go back to an earlier version",
                body=(
                    "Restore Previous Version brings back an earlier save of the "
                    "document you are in. It is the one to remember when a "
                    "well-meant edit went wrong two hours ago."
                ),
                command="file.restore_previous_version",
                hear="The versions available, with their times.",
            ),
            Step(
                title="Read an error properly",
                body=(
                    "Messages carrying a support code end with the concrete next "
                    "step -- install this, check that setting, switch to a local "
                    "model. The code identifies the exact failure branch, so "
                    "include it when you report a problem."
                ),
                hear="The failure, the reason, and what to do about it.",
            ),
        ),
        closing=(
            "Autosave, recovery, a watchdog on your screen reader, and No as the "
            "default answer. None of it asks you to be careful."
        ),
        then=("any-format",),
    ),
    Tutorial(
        slug="any-format",
        title="Open anything, save as anything",
        track="living",
        minutes=5,
        surfaces=("QUILL",),
        summary=(
            "One editor for every format, what QUILL does about a document it "
            "had to extract, and converting a file without hunting for a "
            "converter."
        ),
        steps=(
            Step(
                title="Open what somebody sent you",
                body=(
                    "Every document opens in the one QUILL editor -- the same "
                    "control, whatever the format. The rule to hold onto is that "
                    "bold means bold: QUILL speaks your document's own language "
                    "rather than flattening it."
                ),
                command="file.open",
                hear="The document, and what kind it is.",
            ),
            Step(
                title="Save it as something else",
                body=(
                    "Save As chooses the format as well as the name: Markdown, "
                    "HTML, Word, plain text and the rest. A document is not locked "
                    "into the format it arrived in."
                ),
                command="file.save_as",
                hear="The format list, then the file written.",
            ),
            Step(
                title="Convert without opening",
                body=(
                    "Convert File takes a source and an output format directly, "
                    "which is the right shape when you have twenty files or when "
                    "you do not want to read the thing at all. Batch Conversion "
                    "does a folder."
                ),
                command="file.batch_conversion",
                hear="What it converted, and where it put the result.",
            ),
            Step(
                title="Check what the extraction actually got",
                body=(
                    "When text has been extracted -- from a PDF, from a scan -- "
                    "the intake report says how it went. Reading it is how you "
                    "decide whether to trust what you are reading, which is a "
                    "question a sighted reader answers by glancing at the page."
                ),
                command="tools.document_intake_report",
                hear="The report, as an ordinary tab.",
            ),
            Step(
                title="Switch the document's own format",
                body=(
                    "Switch Document Format changes how QUILL treats what is "
                    "already open -- so a plain-text file you have decided is "
                    "Markdown starts behaving like Markdown, headings and all."
                ),
                command="format.switch_document_format",
                hear="The new format, and the structure it now sees.",
            ),
        ),
        closing=(
            "One editor, every format, and a report whenever the text had to be "
            "extracted rather than read."
        ),
        then=("braille-files",),
    ),
    Tutorial(
        slug="braille-files",
        title="Braille files, page by page",
        track="living",
        minutes=6,
        surfaces=("QUILL",),
        summary=(
            "Opening a BRF as braille rather than as text, moving by braille "
            "page and cell, proofing without touching the file, and translating "
            "when the pack is installed."
        ),
        steps=(
            Step(
                title="Open a braille file",
                body=(
                    "QUILL opens .brf, .brl, .pef and .ueb as plain braille ASCII "
                    "-- nothing is transformed on the way in. The point is to let "
                    "a proofreader move through a transcription the way it is "
                    "actually laid out, in pages and cells."
                ),
                command="file.open",
                hear="BRF file opened, 87 braille pages detected -- and your last position.",
            ),
            Step(
                title="Read the braille status cell",
                body=(
                    "While a braille file is active the status bar carries a "
                    "braille cell: BRF Pg 12/87, Ln 14/25, Cell 31/40, Print 7. "
                    "That is the braille page, the line within it, the cell within "
                    "the line, and the print page."
                ),
                keys=("F6",),
                hear="The whole cell, read as one line.",
            ),
            Step(
                title="Move by braille page",
                body=(
                    "The Braille menu holds Go to Braille Page, Next and Previous "
                    "Braille Page, and the same three for print pages. Stepping "
                    "past the first or last says so rather than doing nothing."
                ),
                hear="The page you landed on, with its number.",
                note=(
                    "Braille bindings ship deliberately unset so nothing collides "
                    "with your screen reader; assign your own, or run them from "
                    "the command palette."
                ),
            ),
            Step(
                title="Proof without changing the file",
                body=(
                    "Mark the current page Proofed or Needs Review, add a note, "
                    "list either set, and export a proofing report. Progress is "
                    "kept in a small companion file beside the braille file, which "
                    "is never modified."
                ),
                hear="The page marked, and how far through you are.",
            ),
            Step(
                title="Validate the layout",
                body=(
                    "Validate BRF Layout scans for ten kinds of problem -- lines "
                    "or pages too long, missing page breaks, mixed line endings, "
                    "characters that are not braille ASCII, malformed page "
                    "indicators -- and opens a warnings list you can step through."
                ),
                hear="Warning 3 of 11, and what it says.",
            ),
            Step(
                title="Repair the two that stop it embossing",
                body=(
                    "Read Layout Metrics speaks the diagnostic numbers in one "
                    "pass; Go to Longest Line and Go to Longest Page take you to "
                    "the worst offender; and Remove Trailing Spaces clears the "
                    "cause of most page-width problems while keeping every line "
                    "ending and form feed intact."
                ),
                hear="The metrics, then the line or page that broke the limit.",
            ),
            Step(
                title="Translate, when the pack is installed",
                body=(
                    "Back-Translate with Auto-Detect Code is the magical path: "
                    "QUILL scores the document through every candidate code and "
                    "says what it found -- Detected UEB Grade 2 (contracted) -- so "
                    "you learn what your file is instead of being asked."
                ),
                hear="The code it detected, then the draft it opened.",
                note=(
                    "Back-translation always opens as a clearly labelled draft, "
                    "because no automatic back-translation is authoritative. The "
                    "Translation submenu is hidden entirely when the pack is not "
                    "installed, so you never meet a disabled item."
                ),
            ),
        ),
        closing=(
            "Byte-for-byte on save, a companion file for your progress, and a "
            "detector that tells you what code your file is in."
        ),
        then=("the-family",),
    ),
    Tutorial(
        slug="the-family",
        title="QUILL and the apps around it",
        track="living",
        minutes=4,
        surfaces=("QUILL",),
        summary=(
            "The radio, the podcasts, the weather and the rest -- what lives "
            "inside QUILL, what is its own app, and what they share."
        ),
        steps=(
            Step(
                title="Play the radio without leaving",
                body=(
                    "QUILL carries the same radio code Quill Radio does: browse "
                    "stations, favorites, recording and scheduling, all from "
                    "inside the editor. Your favorites are the same favorites in "
                    "both."
                ),
                command="radio.browse",
                hear="The browse tree, in QUILL.",
            ),
            Step(
                title="Know what has its own app, and why",
                body=(
                    "Quill Radio, QUILL Cast, Quill Weather and the rest exist so "
                    "somebody who wants a radio does not have to install an "
                    "editor. They share one data store, so nothing you set up in "
                    "one is stranded from the others."
                ),
                hear="Nothing: this is the shape of the family.",
            ),
            Step(
                title="Reach the weather",
                body=(
                    "Weather Now and Quick Weather are here as well, backed by the "
                    "same code the standalone app runs. The alert watch, though, "
                    "belongs to Quill Weather -- an app whose whole job is to keep "
                    "running."
                ),
                command="weather.quick",
                hear="The one-line summary for your primary place.",
            ),
            Step(
                title="Carry your place between them",
                body=(
                    "Your position in an episode, your bookmarks and your "
                    "favorites are shared on this computer. Pause an episode in "
                    "QUILL and open it in Cast and it picks up where you left "
                    "off -- the later decision wins, not the furthest through."
                ),
                hear="Picking up where you left off, and the time.",
            ),
            Step(
                title="Take your setup with you",
                body=(
                    "Export My Setup writes one file with your settings, keys and "
                    "arrangement; Import My Setup puts them on another machine. "
                    "Passwords stay behind, and the confirmation says so before it "
                    "writes anything."
                ),
                command="app.export_setup",
                hear="What the file holds, named, before anything is written.",
            ),
        ),
        closing=(
            "One editor that can do everything, and four small apps for the days "
            "you want one thing. They share their data and never fight over it."
        ),
    ),
)
