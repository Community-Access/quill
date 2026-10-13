"""F1 for every Lineups surface, written once for both apps.

Quill Radio's and Quill Cast's help catalogues (``quill/core/radio/surface_help``
and ``quill/core/podcasts/surface_help``) both take these, because the window is
one module and its help must not say one thing in one app and another in the
other. Keyed by the exact window title, as the catalogues are.
"""

from __future__ import annotations

LINEUP_PURPOSES: dict[str, str] = {
    "Lineups": (
        "QUILL Lineups: lists of anything to play, built by rules you write and "
        "arranged by hand. Your lineups are on the left and the selected one's "
        "items on the right. Rules add items, and each rule says when its items "
        "go: when they stop matching, once finished, after some days, or never. "
        "Moving an item changes the order but not how long it stays; Keep "
        "(Ctrl+K) holds it whatever the rules say; Delete puts it in Removed "
        "Items, and no rule brings it back. Enter plays; Alt+Enter says why an "
        "item is here, or edits a lineup's rules."
    ),
    "Rules": (
        "The rules of one lineup, each as a sentence: what it brings in, how "
        "long its items stay, and what it finds now. Anything any rule finds is "
        "in the lineup. Below them, where new items go, a play-through budget, "
        "and whether live items are skipped when the lineup plays through."
    ),
    "Edit Rule": (
        "One rule, in the order its sentence reads: what it looks for, where to "
        "look, the tests an item must pass, the order and how many, and when its "
        "items go. Try It shows what it finds right now without saving anything."
    ),
    "Test": (
        "One test of a rule: a field, a comparison and a value. A number test "
        "never matches an item that does not say, so a podcast with no length "
        "is never 'at most 10 minutes'."
    ),
    "Removed Items": (
        "What you removed from this lineup. No rule brings these back; Bring "
        "Back returns them as kept items, which stay whatever the rules say."
    ),
    "Recently Left": (
        "What the rules let go from this lineup, newest first, each with why: "
        "finished, its days passed, it no longer matched. Bring Back returns an "
        "item as kept."
    ),
    "Why Is This Here": (
        "Why one item is in the lineup -- the rule that found it, or your own "
        "hand -- and how long it will stay."
    ),
    "Add to Lineup": (
        "Choose the lineup to add to, or New Lineup to make one. Items you add "
        "stay until you remove them, whatever the rules say."
    ),
    "New Lineup": "Type a name for the new lineup. Names are unique, ignoring capitals.",
    "Rename Lineup": (
        "Type the lineup's new name. Names are unique, ignoring capitals, so Go to a "
        "Lineup always means one thing."
    ),
    "New from an Example": (
        "Ready-made lineups, each showing a different way rules keep items. "
        "The one you choose becomes yours; change its rules as you like."
    ),
    "Go to a Lineup": (
        "Choose a lineup by name to open it in the Lineups window: quicker than "
        "arrowing when you have many."
    ),
    "Delete Lineup": (
        "Deleting a lineup removes its rules and its order, never the stations, "
        "episodes or files in it. Undo brings it back."
    ),
    "Move to Position": (
        "Type the position to move to, counting from 1. The new position is said "
        "once the item is there."
    ),
    "Export Rules": "Save this lineup's rules to a file, to share or to use on another computer.",
    "Import Rules": "Open a lineup rules file; a new lineup with those rules is made.",
    "Removed Rules": (
        "Rules you removed had brought items in. Keep them as kept items, or let "
        "them go to Recently Left."
    ),
    "Change the Rules": "The change lets some items go. They will be in Recently Left.",
    "Change What It Looks For": (
        "Looking for a different kind of thing clears the rule's tests and "
        "places, because they belong to the old kind."
    ),
}

#: Titles with live data in them ("Rules for Morning").
LINEUP_PREFIX_PURPOSES: tuple[tuple[str, str], ...] = (("Rules for ", LINEUP_PURPOSES["Rules"]),)


__all__ = ["LINEUP_PREFIX_PURPOSES", "LINEUP_PURPOSES"]
