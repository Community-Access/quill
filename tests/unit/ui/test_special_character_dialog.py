"""The Insert Special Character picker, built for real.

Every other test of this feature answers the modal with a recorder, which is the
right shape for asserting what the command does with a character -- and is
exactly why the picker could ship in both editors without ever opening.
Constructing it raised a wx assertion (``CreateStdDialogButtonSizer`` parents its
buttons on the dialog, while every other control here is on a panel whose sizer
then refuses them), so the command was a keystroke that did nothing.

So this one builds the real thing, and the assertion is that construction
survives at all. The rest -- that the list fills, that a code point search
reaches the character, that the buttons carry the ids ``apply_modal_ids`` looks
up -- is what a picker that opens is expected to have on screen once it does.
"""

from __future__ import annotations

import contextlib

import pytest

wx = pytest.importorskip("wx")

from quill.ui.dialog_contract import apply_modal_ids  # noqa: E402
from quill.ui.special_character_dialog import TITLE, SpecialCharacterDialog  # noqa: E402

EM_DASH = "—"


@pytest.fixture(scope="module")
def wx_app():
    app = wx.App()
    yield app
    app.Destroy()


@pytest.fixture()
def parent(wx_app):
    frame = wx.Frame(None)
    yield frame
    frame.Destroy()
    wx_app.Yield()


@contextlib.contextmanager
def _picker(parent):
    said: list[str] = []
    dialog = SpecialCharacterDialog(parent, announce_cb=said.append)
    try:
        yield dialog, said
    finally:
        dialog.dialog.Destroy()


def test_the_picker_can_be_built(parent) -> None:
    """The regression: this raised ``wxAssertionError`` before the buttons moved
    onto the panel, and nothing ever appeared."""
    with _picker(parent) as (dialog, _said):
        assert dialog.dialog.GetTitle() == TITLE


def test_it_opens_on_a_group_with_characters_in_it(parent) -> None:
    with _picker(parent) as (dialog, _said):
        assert dialog._results.GetItemCount() > 0
        assert dialog._selected_char() is not None


def test_a_code_point_search_reaches_the_character(parent) -> None:
    with _picker(parent) as (dialog, _said):
        dialog._search.SetValue("2014")
        dialog._on_search(None)
        assert dialog._selected_char() == EM_DASH


def test_the_buttons_are_the_ones_the_modal_contract_looks_up(parent) -> None:
    """``apply_modal_ids`` relabels by id, and ``FindWindowById`` walks the whole
    tree -- so the buttons living on the panel rather than on the dialog must not
    cost the contract its handles."""
    with _picker(parent) as (dialog, _said):
        apply_modal_ids(
            dialog.dialog,
            affirmative_id=wx.ID_OK,
            affirmative_label="Insert",
            cancel_id=wx.ID_CANCEL,
        )
        ok = dialog.dialog.FindWindowById(wx.ID_OK)
        cancel = dialog.dialog.FindWindowById(wx.ID_CANCEL)
        assert ok is not None and ok.GetLabel() == "Insert"
        assert cancel is not None
