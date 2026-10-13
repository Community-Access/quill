"""Track 5: QUILL Lineups -- lists that fill themselves, in an order you chose.

One lesson, because a Lineup is one idea with two halves: rules bring things
in and say when they go, and your own hands outrank the rules. It builds
Morning from a ready-made example, adds a station by hand, keeps one item,
asks why another is there, and plays the whole list through.

The keys inside the Lineups window are the window's own (``quill/ui/lineups/
menus.py``), not app commands, so those steps name them literally; the step
that opens the window names its command, so a rebound key renders.
"""

from __future__ import annotations

from quill.core.tutorials.model import Step, Tutorial

TUTORIALS: tuple[Tutorial, ...] = (
    Tutorial(
        slug="lineups",
        title="Build a lineup that fills itself",
        track="beyond",
        minutes=9,
        surfaces=("Quill Radio", "Lineups", "Browse Stations"),
        summary=(
            "Make a QUILL Lineup: a list of stations, episodes, videos and your own "
            "files, brought in by rules you choose, kept in the order you choose, "
            "and played straight through."
        ),
        steps=(
            Step(
                title="Open Lineups",
                body=(
                    "Lineups is a window of its own, like Local Media, so it is on "
                    "the Window menu and in the Ctrl+Tab order. The first time it "
                    "is empty, and your cursor is already on the New Lineup button."
                ),
                command="radio.lineups",
                hear="Lineups, then New Lineup button.",
                note="It is also on every window's Station menu and in the Go To list.",
            ),
            Step(
                title="Start from an example",
                body=(
                    "Start from an Example offers ready-made lineups, each showing a "
                    "different way rules keep things. Choose Morning: your Morning "
                    "stations, always, then today's unplayed news, each episode gone "
                    "once you have heard it."
                ),
                keys=("Ctrl+Alt+N",),
                hear="Made Morning. Its rules are running now.",
                note="A rule naming a folder you do not have finds nothing and says so.",
            ),
            Step(
                title="Add something by hand",
                body=(
                    "Anything you add yourself stays until you remove it, whatever "
                    "the rules say. In Browse Stations, open the menu on a station "
                    "with the Applications key and choose Add to Lineup, then choose "
                    "Morning."
                ),
                keys=("Shift+F10",),
                hear="Added to Morning.",
                note="The same choice is on your favorites, in Search Stations and in Local Media.",
            ),
            Step(
                title="Read the rules, and how long things stay",
                body=(
                    "Back in Lineups, Edit Rules shows each rule as one sentence: "
                    "what it brings in, how long its items stay, and how many it "
                    "finds now. Edit a rule to change its Keep choice: while it "
                    "matches, until finished, for some days, or always."
                ),
                keys=("Ctrl+Alt+R",),
                hear="Rules for Morning, then the first rule's sentence.",
                note="Try It in Edit Rule shows what a rule finds without saving anything.",
            ),
            Step(
                title="Keep one item, and ask why another is here",
                body=(
                    "In the Items list, Keep This Item holds an item whatever its "
                    "rule says; press it again to give it back to the rule. Why Is "
                    "This Here names the rule that found an item, or your own hand, "
                    "and how long it will stay."
                ),
                keys=("Ctrl+K", "Alt+Enter"),
                hear="Kept. It stays whatever the rules say.",
                note="Delete puts an item in Removed Items, and no rule brings it back.",
            ),
            Step(
                title="Put it in your own order",
                body=(
                    "Alt+Shift+Up and Alt+Shift+Down move the selected items, and "
                    "Quill Radio says where they landed. Moving changes the order, "
                    "never how long an item stays, and a refresh never moves "
                    "anything you placed."
                ),
                keys=("Alt+Shift+Up", "Alt+Shift+Down"),
                hear="Moved to 2 of 9.",
                note="Ctrl+Z takes back the last change.",
            ),
            Step(
                title="Play the whole lineup",
                body=(
                    "Play This Lineup plays from the top, one item after another, "
                    "any kind. A live station never ends by itself, so the first one "
                    "tells you how to move on; anything that cannot play is named "
                    "and skipped."
                ),
                keys=("Ctrl+Alt+P", "Ctrl+Right"),
                hear="Playing, and the first item's name.",
                note="From any window, the Next Chapter key moves to the next item too, "
                "even on a live station. Enter on a lineup in the Lineups list plays it.",
            ),
            Step(
                title="Start Quill Radio in it",
                body=(
                    "Start Here makes this lineup open in front of the main window "
                    "each time Quill Radio starts. It is a check item: choose it "
                    "again to start as usual, or on another lineup to move it."
                ),
                keys=("Ctrl+Alt+H",),
                hear="Morning opens when Quill Radio starts.",
                note="QUILL Cast shares your lineups and keeps its own Start Here.",
            ),
        ),
        closing=(
            "You have a lineup that brings itself up to date, keeps what you told it "
            "to keep, lets go of what you have heard, and plays in your order. QUILL "
            "Cast sees the same lineups, so you can edit them in either app."
        ),
    ),
)
