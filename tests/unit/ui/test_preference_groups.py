"""Preferences that group what belongs together (list.md 8.1, 8.2).

Both apps' Preferences had grown to twenty-odd controls in one flat run, which
reads as twenty unrelated facts -- and reads that way *especially* to somebody
arrowing through it with a screen reader, who has no visual proximity to infer
from.

Two properties matter, and one of them is the dangerous one:

* **A group is a real ``wx.StaticBox``**, not a heading label, so the grouping
  is announced on entering rather than left to be inferred.
* **The returned values stay in spec order regardless of where a control was
  drawn.** Callers unpack by position -- ``a, b, c = checkbox_values`` -- so a
  layout that reordered its results would silently write the wrong value into
  every setting. That is the test worth having.

Plus the section-3 rule (8.2): every control says what it does *and* what it
does not, in both the accessible name and the F1 help.
"""

from __future__ import annotations

import pytest

wx = pytest.importorskip("wx")

from quill.ui.app_preferences_dialog import (  # noqa: E402
    PreferenceAction,
    PreferenceCheckbox,
    PreferenceChoice,
    PreferencesDialog,
    PreferenceText,
)


@pytest.fixture(scope="module", autouse=True)
def wx_app():
    app = wx.App()
    yield app
    app.Destroy()


@pytest.fixture
def frame():
    window = wx.Frame(None)
    yield window
    window.Destroy()


def _check(name: str, value: bool = False, group: str = "") -> PreferenceCheckbox:
    return PreferenceCheckbox(name, f"{name} does a thing and not another.", value, group=group)


def _choice(name: str, index: int = 0, group: str = "") -> PreferenceChoice:
    return PreferenceChoice(name, f"{name} chooses.", ["One", "Two", "Three"], index, group=group)


def _build(frame, **kwargs) -> PreferencesDialog:
    return PreferencesDialog(frame, app_title="Test", announce_cb=lambda _m: None, **kwargs)


def _boxes(dialog: PreferencesDialog) -> list[str]:
    return [
        child.GetLabel() for child in dialog.dialog.GetChildren() if isinstance(child, wx.StaticBox)
    ]


# -- the results keep their order -------------------------------------------------


def test_grouping_never_reorders_the_returned_values(frame) -> None:
    """The dangerous one. A caller unpacks by position, so a layout that
    reordered results would write every setting into the wrong field."""
    dialog = _build(
        frame,
        checkboxes=[
            _check("first", value=True, group="B"),
            _check("second", value=False),
            _check("third", value=True, group="A"),
        ],
    )

    dialog._capture_result()
    values, _choices, _texts = dialog._result

    assert values == [True, False, True]
    dialog.dialog.Destroy()


def test_choices_keep_their_order_too(frame) -> None:
    dialog = _build(
        frame,
        checkboxes=[],
        choices=[_choice("a", 2, group="Z"), _choice("b", 0), _choice("c", 1, group="Y")],
    )

    dialog._capture_result()
    _values, indices, _texts = dialog._result

    assert indices == [2, 0, 1]
    dialog.dialog.Destroy()


# -- the boxes --------------------------------------------------------------------


def test_naming_no_group_draws_no_box(frame) -> None:
    """An app that never asked for groups gets exactly what it had before."""
    dialog = _build(frame, checkboxes=[_check("one"), _check("two")])

    assert _boxes(dialog) == []
    dialog.dialog.Destroy()


def test_a_named_group_becomes_a_labelled_box(frame) -> None:
    dialog = _build(frame, checkboxes=[_check("one", group="Reminders")])

    assert _boxes(dialog) == ["Reminders"]
    dialog.dialog.Destroy()


def test_groups_come_in_the_order_they_were_written(frame) -> None:
    """The caller's order is a judgement about what somebody looks for first;
    sorting would replace it with the alphabet."""
    dialog = _build(
        frame,
        checkboxes=[_check("z", group="Zebra"), _check("a", group="Apple")],
    )

    assert _boxes(dialog) == ["Zebra", "Apple"]
    dialog.dialog.Destroy()


def test_one_box_per_group_however_many_controls_it_holds(frame) -> None:
    dialog = _build(
        frame,
        checkboxes=[_check("a", group="G"), _check("b", group="G")],
        choices=[_choice("c", group="G")],
    )

    assert _boxes(dialog) == ["G"]
    dialog.dialog.Destroy()


def test_a_grouped_control_is_parented_to_its_box(frame) -> None:
    """wxMSW walks the real parent chain to report grouping, so a control
    parented to the dialog would sit inside a box no screen reader mentions."""
    dialog = _build(frame, checkboxes=[_check("inside", group="G")])

    box = next(c for c in dialog.dialog.GetChildren() if isinstance(c, wx.StaticBox))
    labels = [c.GetLabel() for c in box.GetChildren() if isinstance(c, wx.CheckBox)]

    assert labels == ["inside"]
    dialog.dialog.Destroy()


def test_every_kind_of_control_can_be_grouped(frame) -> None:
    dialog = _build(
        frame,
        checkboxes=[_check("a", group="G")],
        choices=[_choice("b", group="G")],
        texts=[PreferenceText("c", "c does.", "", group="G")],
        actions=[PreferenceAction("d", "d does.", lambda: None, group="G")],
    )

    assert _boxes(dialog) == ["G"]
    dialog.dialog.Destroy()


# -- help text (8.2) --------------------------------------------------------------


def test_every_control_answers_focus_and_f1(frame) -> None:
    """SetName is what focus announces; SetHelpText is what F1 answers. They
    are different mechanisms, and a control with only the first has nothing to
    say when asked.

    The provider has to be installed to read it back at all: without one,
    ``GetHelpText`` answers "" however faithfully ``SetHelpText`` was called --
    which is the whole reason ``app_context_help.ensure_help_provider``
    exists, and is exactly the trap this test would otherwise fall into and
    call a pass."""
    from quill.ui.app_context_help import ensure_help_provider

    ensure_help_provider()
    dialog = _build(
        frame,
        checkboxes=[_check("a", group="G")],
        choices=[_choice("b")],
        texts=[PreferenceText("c", "c does a thing.", "")],
    )

    for control in (
        dialog._checks[0],
        dialog._choice_controls[0],
        dialog._text_controls[0],
    ):
        assert control.GetName().strip()
        assert control.GetHelpText().strip()
    dialog.dialog.Destroy()


# -- the apps' own groups ---------------------------------------------------------


def test_quill_radio_groups_its_podcast_and_reminder_settings() -> None:
    from pathlib import Path

    source = (
        Path(__file__).resolve().parents[3] / "quill" / "apps" / "radio_preferences.py"
    ).read_text(encoding="utf-8")

    assert "group=_PODCASTS" in source
    assert "group=_REMINDERS" in source


def test_quill_cast_groups_its_podcast_settings() -> None:
    from pathlib import Path

    source = (Path(__file__).resolve().parents[3] / "quill" / "apps" / "podcasts.py").read_text(
        encoding="utf-8"
    )

    assert "group=self._PODCASTS" in source
