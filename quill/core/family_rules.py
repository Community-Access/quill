"""The eleven rules QUILL and QuillLite are held to, and where they came from.

These were the plan of record for the 2026-09 parity program (`bad.md`, now
closed). They live here because the program is over and the rules are not: code
in `keymap.py` and `lite/parity.py` cites them **by number**, and a rule that
exists only in a planning file somebody deletes is a rule that quietly stops
being one.

The numbers are load-bearing. `keymap.py` says "which rule 6 forbids" and
`lite/parity.py` says "the note keeps the shorter chord (rule 3)", so renumbering
this list silently rewrites those comments into lies. Add at the end; never
renumber. :func:`rule` is how a test or a comment resolves a number to its text,
and ``tests/unit/core/test_family_rules.py`` asserts every citation in the tree
points at a rule that exists.

Lower number wins when two rules conflict.
"""

from __future__ import annotations

from dataclasses import dataclass

__all__ = ["FAMILY_RULES", "FamilyRule", "rule"]


@dataclass(frozen=True, slots=True)
class FamilyRule:
    """One rule: its number, its one-line form, and why it is the rule."""

    number: int
    #: The rule in one sentence, as it is quoted in reviews and commit messages.
    statement: str
    #: What goes wrong without it. Kept because a rule whose reason is lost is a
    #: rule the next person argues with from scratch.
    because: str


FAMILY_RULES: tuple[FamilyRule, ...] = (
    FamilyRule(
        1,
        "Microsoft's key wins where Word, WordPad or Notepad bind one for a "
        "function both editors have.",
        "The keys in somebody's hands were put there by the programs they used "
        "before this one. Exceptions, each because another Microsoft product or "
        "a family habit owns the chord: F3/Shift+F3 find next and previous, F5 "
        "date and time, Ctrl+D duplicate line, Ctrl+] / Ctrl+[ indent and "
        "outdent, Ctrl+Q exit.",
    ),
    FamilyRule(
        2,
        "The command both products have keeps the chord; the product-only command moves.",
        "A chord that means two things across the family is a chord nobody can "
        "learn once, and the person who pays is whoever uses both.",
    ),
    FamilyRule(
        3,
        "Frequency breaks ties: the verb used in the editing loop keeps the shorter chord.",
        "A three-modifier chord is fine once a session and a tax once a minute.",
    ),
    FamilyRule(
        4,
        "Destructive first: a habit that does damage in the other editor is "
        "fixed before one that merely opens the wrong dialog.",
        "A wrong dialog is a moment's confusion. A wrong key that rewrites the "
        "document is work lost by somebody who cannot see that it happened.",
    ),
    FamilyRule(
        5,
        "A chord free in both is adopted as an alias; nothing moves.",
        "The cheapest possible fix. An alias costs one line and breaks nobody's "
        "hands, and a move costs everybody who had learned the old key.",
    ),
    FamilyRule(
        6,
        "Nothing QuillLite reaches on a plain chord lives on QUILL's leader.",
        "The leader is a second keystroke and a thing to be told about. A "
        "command the small editor gives you directly should not be buried in "
        "the big one -- that is the big one being worse at the same job.",
    ),
    FamilyRule(
        7,
        "Editor chords are for the editor.",
        "Media, radio favourites, favourite folders, AI, GitHub and remote-file "
        "commands live on the leader, in the owning app's APP_KEYMAPS, or in a "
        "menu. A text editor whose plain chords are spent on a podcast client "
        "has no room left for text.",
    ),
    FamilyRule(
        8,
        "Every registered editor command has a key or a written reason not to.",
        "Walking a menu to discover there is no shortcut is a cost a "
        "screen-reader user pays on every visit, and a command with no key and "
        "no reason is one nobody decided about.",
    ),
    FamilyRule(
        9,
        "Once-a-year commands need *a* key, not the same key -- the F-keys past "
        "F9 are where they go.",
        "Rule 8 does not mean every command deserves a short chord. It means "
        "every command is reachable, which a three-modifier F-key satisfies.",
    ),
    FamilyRule(
        10,
        "Value flows both ways, violations flow one: a capability may cross in "
        "either direction, but QuillLite is never allowed to be ahead of QUILL.",
        "Nobody opens QUILL and notices the absence of a thing they have only "
        "ever seen elsewhere. A feature the small product has and the big one "
        "does not is invisible and backwards, so it is a bug in the big one.",
    ),
    FamilyRule(
        11,
        "Every remaining divergence is a comment in keymap.py *and* an entry in "
        "the parity gate's exception table.",
        "A divergence with a reason beside it is a decision. A divergence "
        "without one is a bug that has been there long enough to look "
        "deliberate.",
    ),
)

_BY_NUMBER = {item.number: item for item in FAMILY_RULES}


def rule(number: int) -> FamilyRule:
    """The rule with this number.

    Raises ``KeyError`` for a number that does not exist, which is exactly what
    a test citing a rule wants: a comment that has drifted onto a rule nobody
    wrote should fail loudly rather than read plausibly.
    """
    return _BY_NUMBER[int(number)]
