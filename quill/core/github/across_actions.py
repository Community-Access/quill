"""The context menus of Across Repositories' rows, and why each command has no chord.

Split from :mod:`quill.core.github.item_actions` (GATE-11), which merges
:data:`ACROSS_ROWS` into the one action table, so menus, Shift+F1 and the
help reference read them like every other row. Five row types:

- ``across_item``: one item in a category list (GX16). Enter opens it in its
  own repository; ``]`` and ``[`` move between repositories.
- ``across_status``: a repository that had nothing to list, had the feature
  off, could not be read or stopped at its page -- the row that keeps it from
  vanishing.
- ``repository_set``: a named set under Repository Sets.
- ``by_name``: a label, milestone, topic or rule set by name across the set.
- ``fleet``: one repository's line in the Fleet.

:data:`KEYLESS` is family rule 8 for these commands: every one has a key in
the Workbench's keymap, a list key (:data:`LIST_KEYS`), or a written reason
here; ``tests/unit/core/test_github_across_sets_and_names.py`` checks it.

wx-free and strict-typed.
"""

from __future__ import annotations

from quill.core.workbench.actions import ActionRow, Tier

__all__ = ["ACROSS_ROWS", "KEYLESS", "LIST_KEYS"]

_P = "github.workbench."
_R, _O, _W, _D = Tier.READ, Tier.ORGANIZE, Tier.WRITE, Tier.DESTRUCTIVE


def _a(verb: str, label: str, tier: Tier, requirement: str, help: str) -> ActionRow:  # noqa: A002
    return ActionRow(f"{_P}{verb}", label, tier, requirement, help)


def _default(verb: str, label: str, help: str) -> ActionRow:  # noqa: A002
    return ActionRow(f"{_P}{verb}", label, _R, "", help, True)


_PROPERTIES = ActionRow(
    f"{_P}properties",
    "Properties...",
    help="Everything about this item on one sheet. Alt+Enter opens it from anywhere.",
)
_OPEN_WEB = _a("open_on_github", "Open on GitHub", _R, "", "Open the item in your browser.")
_COPY_LINK = _a("copy_link", "Copy Link", _R, "", "Copy the item's GitHub address.")
_NEXT = _a(
    "next_repository",
    "Next Repository",
    _R,
    "",
    "The first row of the next repository in the list. ] in the list does the same.",
)
_PREVIOUS = _a(
    "previous_repository",
    "Previous Repository",
    _R,
    "",
    "The first row of the repository before this one. [ in the list does the same.",
)
_MORE = _a(
    "across_view_more",
    "View More from This Repository",
    _R,
    "",
    "Read 30 more from this repository, up to GitHub's 100; the rest keep their place.",
)

ACROSS_ROWS: dict[str, tuple[ActionRow, ...]] = {
    "across_item": (
        _default(
            "across_open_source",
            "Open in Its Repository",
            "Go to the item in its own repository, where every action for it is. Back "
            "returns to this row, filter and page.",
        ),
        _NEXT,
        _PREVIOUS,
        _MORE,
        _a(
            "across_issue_fields",
            "Read Issue Type and Fields",
            _R,
            "",
            "Read each issue's type and its organization's fields, with the field's type "
            "and whether it is unset, empty, hidden or unreadable.",
        ),
        _a(
            "across_all_releases",
            "Every Release or Latest Only",
            _R,
            "",
            "Releases shows each repository's latest release; this shows every release, or "
            "the latest only again.",
        ),
        _OPEN_WEB,
        _COPY_LINK,
        _PROPERTIES,
    ),
    "across_status": (
        _default("open", "Open", "Read what this repository answered, in the details pane."),
        _NEXT,
        _PREVIOUS,
        _MORE,
        _OPEN_WEB,
        _PROPERTIES,
    ),
    "repository_set": (
        _default(
            "across_use_set",
            "Use This Set",
            "Every Across Repositories list and by-name sheet reads this set from now on.",
        ),
        _a(
            "across_edit_set",
            "Edit Repositories...",
            _O,
            "local",
            "The set's repositories, one per line. Adding one already listed keeps one copy.",
        ),
        _a(
            "across_set_filter",
            "Set Filter...",
            _O,
            "local",
            "Make the set by GitHub's repository search, such as org:name topic:x, each time "
            "it is used.",
        ),
        _a("across_new_set", "New Set...", _O, "local", "Make another set, by hand or by filter."),
        _a("across_rename_set", "Rename Set...", _O, "local", "Give the set another name."),
        _a(
            "across_delete_set",
            "Delete Set...",
            _O,
            "local",
            "Forget the set on this computer, after asking. Nothing on GitHub changes.",
        ),
        _PROPERTIES,
    ),
    "by_name": (
        _default(
            "across_variants",
            "Variants and Missing From",
            "Each variant with the repositories that have it, and those that lack it.",
        ),
        _a(
            "across_make_same",
            "Make Them the Same...",
            _W,
            "push",
            "Choose the winning variant; the preview shows each repository, then each result.",
        ),
        _a(
            "across_add_missing",
            "Add to Missing...",
            _W,
            "push",
            "Create it in the repositories you choose that lack it, after the preview.",
        ),
        _a(
            "across_find_uses",
            "Find Uses",
            _R,
            "",
            "Search every issue and pull request with it, across the set.",
        ),
        _a(
            "across_rename_name",
            "Rename Everywhere...",
            _W,
            "push",
            "Rename the label in every repository; a clash is shown, not merged.",
        ),
        _a(
            "across_merge_label",
            "Merge Into...",
            _D,
            "push",
            "Move every item to another label, then delete this one, after the preview.",
        ),
        _a(
            "across_close_milestone",
            "Close Everywhere...",
            _W,
            "push",
            "Close every open copy of the milestone, after the preview.",
        ),
        _a(
            "across_move_open",
            "Move Open Work To...",
            _W,
            "push",
            "Move each repository's open items to another milestone of its own, after the preview.",
        ),
        _a(
            "across_promote_org",
            "Promote to Organization...",
            _D,
            "admin",
            "One organization ruleset for the set's repositories in that organization, then "
            "their own copies deleted, after the preview.",
        ),
        _a(
            "across_delete_name",
            "Delete Everywhere...",
            _D,
            "push",
            "Delete the label, or remove the topic, in every repository, after the preview.",
        ),
        _PROPERTIES,
    ),
    "fleet": (
        _default(
            "across_open_repository",
            "Open Repository",
            "Select the repository's node in the tree.",
        ),
        _OPEN_WEB,
        _COPY_LINK,
        _PROPERTIES,
    ),
}

#: Keys the list answers only while it has focus (Enter, Backspace, ] and [).
LIST_KEYS: dict[str, str] = {
    f"{_P}next_repository": "]",
    f"{_P}previous_repository": "[",
}

_RARE = "rule 9: a once-in-a-while change across many repositories gets a menu row, not a chord"
_SET = "rule 9: sets are made and changed rarely; Ctrl+N makes one on Repository Sets"
KEYLESS: dict[str, str] = {
    f"{_P}across_open_source": "Enter, the row's default, does it.",
    f"{_P}across_view_more": "Alt+PageDown is the whole list's Load More; one repository's "
    "page is a command on that repository's rows.",
    f"{_P}across_issue_fields": "a read with up to 30 requests per repository, so it is asked "
    "for, not a reflex; a type: or field: filter reads them too.",
    f"{_P}across_all_releases": _RARE,
    f"{_P}across_use_set": "Enter, the row's default, does it.",
    f"{_P}across_edit_set": _SET,
    f"{_P}across_set_filter": _SET,
    f"{_P}across_new_set": "Ctrl+N (New Here) on Repository Sets does it.",
    f"{_P}across_rename_set": _SET,
    f"{_P}across_delete_set": "Delete on the row does it, after asking.",
    f"{_P}across_variants": "Enter, the row's default, does it.",
    f"{_P}across_make_same": _RARE,
    f"{_P}across_add_missing": _RARE,
    f"{_P}across_find_uses": _RARE,
    f"{_P}across_rename_name": _RARE,
    f"{_P}across_merge_label": _RARE,
    f"{_P}across_close_milestone": _RARE,
    f"{_P}across_move_open": _RARE,
    f"{_P}across_promote_org": _RARE,
    f"{_P}across_delete_name": _RARE + "; never Delete, which must not reach many repositories",
    f"{_P}across_open_repository": "Enter, the row's default, does it.",
}
