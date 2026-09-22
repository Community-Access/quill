r"""GATE-LITE-FORMAT: a dimmed row would have refused, and a live row would not.

Reported while testing: "if in plain text mode, shouldn't the format menu go
away?" Sixteen of the twenty-one formatting commands could only refuse in a
plain text document, and every row was enabled and advertising a shortcut.

The fix is a table (``quill.core.lite.format_kinds``) and the table is the risk.
A row dimmed when the command would have worked takes a feature away silently; a
row left live when the command can only refuse is the reported bug coming back.
Neither is visible by reading the table -- so this runs **every** classified
command in **every** document kind and checks the table against what the command
actually does.

That is the whole point of it. The gating and the refusals are written in
different modules by different reasoning, and the only thing that can keep them
agreeing is something that asks both.
"""

from __future__ import annotations

import pytest

from quill.core.lite.format_kinds import ALL_KINDS, FORMAT_COMMAND_KINDS, applies_to

#: What a command says when the *document kind* is wrong for it, as opposed to
#: the caret being in the wrong place. Only the first kind is what the table
#: claims to predict.
_KIND_REFUSALS = (
    "has no formatting",
    "is not available in this",
    "needs a Markdown or HTML document",
)

#: Commands whose whole body is a native dialog. They cannot be *run* headless
#: -- wx refuses to build a FontDialog without a real parent -- so the table is
#: checked for them by classification only. Each is ALL_KINDS or rich-only and
#: opens a chooser rather than editing anything, which is the one shape where
#: "does it refuse?" is not a question worth asking.
_DIALOG_ONLY = frozenset({
    "cmd_editor_font",
    "cmd_selection_font",
    "cmd_switch_document_kind",
    "cmd_set_language",
})


def _refused_for_kind(said: list[str]) -> bool:
    last = said[-1] if said else ""
    return any(phrase in last for phrase in _KIND_REFUSALS)


def _run(lite_window, handler: str, kind: str) -> list[str]:
    window = lite_window("Some text\nmore text\n", mode="rich" if kind == "rich" else "plain")
    if kind != "rich":
        window.set_document_language(kind, announce=False)
    window.control.SetInsertionPoint(2)
    before = len(list(window.announcements))
    getattr(window, handler)()
    return list(window.announcements)[before:]


CASES = sorted((handler, kind) for handler in FORMAT_COMMAND_KINDS for kind in sorted(ALL_KINDS))


@pytest.mark.parametrize(("handler", "kind"), CASES, ids=lambda v: v if isinstance(v, str) else v)
def test_the_table_matches_what_the_command_does(lite_window, lite_dialogs, handler, kind):
    if handler in _DIALOG_ONLY:
        pytest.skip("a native dialog; classified rather than run (see _DIALOG_ONLY)")
    said = _run(lite_window, handler, kind)
    refused = _refused_for_kind(said)
    if applies_to(handler, kind):
        assert not refused, (
            f"{handler} is live in a {kind} document and refused anyway: {said!r}. "
            "Either the table is wrong or the command is."
        )
    else:
        assert refused, (
            f"{handler} is dimmed in a {kind} document but did not refuse: {said!r}. "
            "Dimming a row that would have worked takes a feature away silently."
        )


def test_the_way_out_of_a_plain_document_is_never_dimmed():
    """The Format menu stays on the bar *because* of these two rows.

    Dimming everything would leave a menu that says formatting is unavailable
    and offers no way to make it available, which is worse than the noise it
    was meant to remove.
    """
    assert applies_to("cmd_switch_document_kind", "plain")
    assert applies_to("cmd_set_language", "plain")


def test_an_unclassified_command_stays_reachable():
    """The table names what is limited, not what is allowed.

    A command nobody has classified must not vanish from a menu because of it.
    """
    assert applies_to("cmd_something_nobody_has_classified", "plain")
