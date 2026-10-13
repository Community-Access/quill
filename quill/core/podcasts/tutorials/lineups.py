"""QUILL Cast, track 2: keeping up -- QUILL Lineups, shared with Quill Radio.

One lesson, because a Lineup is one idea with two halves: rules bring episodes
in and say when they go, and your own hands outrank the rules. It sits in the
keeping-up track after Playlists, because a Lineup is what a smart playlist
becomes when it also knows when to let things go and what order you want.

What is Cast's own here is how a Lineup plays: an episode goes to the front of
the Play Queue with the Lineup's later episodes, so the queue carries on by
itself, and anything Cast cannot play is sent to Quill Radio.

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
        track="keeping-up",
        minutes=9,
        surfaces=("QUILL Cast", "Lineups", "Play Queue"),
        summary=(
            "Make a QUILL Lineup: a list of episodes, and anything else Quill Radio "
            "plays, brought in by rules you choose and kept in the order you choose. "
            "Play it through the Play Queue, and save the queue's own order as one."
        ),
        steps=(
            Step(
                title="Open Lineups",
                body=(
                    "Lineups is a window of its own, so it is on the Window menu and "
                    "in the Ctrl+Tab order, and Ctrl+1 takes you back to the main "
                    "window. The first time it is empty, and your cursor is already "
                    "on the New Lineup button."
                ),
                command="podcasts.lineups",
                hear="Lineups, then New Lineup button.",
                note="It is also on the Episode menu, in Go To and in the Command Palette.",
            ),
            Step(
                title="Start from an example",
                body=(
                    "Start from an Example offers ready-made lineups, each showing a "
                    "different way rules keep things. Choose New This Week: unplayed "
                    "episodes from the last seven days, newest first, each one gone "
                    "once you have heard it or after seven days."
                ),
                keys=("Ctrl+Alt+N",),
                hear="Made New This Week. Its rules are running now.",
                note="The examples are yours once made; change their rules as you like.",
            ),
            Step(
                title="Add an episode by hand",
                body=(
                    "Anything you add yourself stays until you remove it, whatever "
                    "the rules say. In the main window, open the menu on an episode "
                    "or a podcast with the Applications key, choose Add to Lineup, "
                    "and then choose New This Week."
                ),
                keys=("Shift+F10",),
                hear="Added to New This Week. Ctrl+Z undoes this.",
                note="The Command Palette has Podcasts: Add to Lineup... for the row you are on.",
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
                hear="Rules for New This Week, then the rule's sentence.",
                note="Try It in Edit Rule shows what a rule finds without saving anything.",
            ),
            Step(
                title="Keep one item, and ask why another is here",
                body=(
                    "In the Items list, Keep This Item holds an episode whatever its "
                    "rule says; press it again to give it back to the rule. Why Is "
                    "This Here names the rule that found an item, or your own hand, "
                    "and how long it will stay."
                ),
                keys=("Ctrl+K", "Alt+Enter"),
                hear="Kept. It stays whatever the rules say.",
                note="Delete puts an item in Removed Items, and no rule brings it back.",
            ),
            Step(
                title="Play from an episode",
                body=(
                    "Enter on an episode plays it, and puts it and the lineup's later "
                    "episodes at the front of your Play Queue, so Cast carries on "
                    "through them by itself. The rest of your queue waits behind. "
                    "Next Item and Previous Item move through the queue."
                ),
                keys=("Enter", "Ctrl+Right"),
                hear="The episode's title, then its audio.",
                note=(
                    "A station, a YouTube item or a file of your own is sent to Quill "
                    "Radio, which opens if it needs to: Sent to Quill Radio to play."
                ),
            ),
            Step(
                title="Save the queue's order as a lineup",
                body=(
                    "On the Play Queue place, the Applications key offers Save Lineup. "
                    "Type a name, such as Tuesday, and the queue's order becomes a "
                    "lineup of episodes you added by hand. Apply Lineup puts its "
                    "unheard episodes back at the front of the queue later."
                ),
                keys=("Applications",),
                hear="Saved lineup Tuesday, then how many episodes, in this order.",
                note="Saving under a name you already have replaces that lineup's episodes.",
            ),
            Step(
                title="Start Quill Cast in it",
                body=(
                    "Start Here makes this lineup open in front of the main window "
                    "each time Quill Cast starts. It is a check item: choose it again "
                    "to start as usual, or on another lineup to move it."
                ),
                keys=("Ctrl+Alt+H",),
                hear="New This Week opens when Quill Cast starts.",
                note="Quill Radio shares your lineups and keeps its own Start Here.",
            ),
        ),
        closing=(
            "You have a lineup that brings itself up to date, keeps what you told it "
            "to keep, lets go of what you have heard, and plays through your Play "
            "Queue in your order. Quill Radio sees the same lineups, so you can edit "
            "them in either app, even with both open."
        ),
        then=("episode-filters",),
    ),
)
