"""GATE-GROUP: every check box or radio button in a static box says its group.

The scan is :mod:`quill.tools.group_caption_audit`; this test holds its scope
to zero findings and proves the scan sees the shapes it is meant to see, so a
quiet scan is evidence and not an accident.
"""

from __future__ import annotations

import textwrap

from quill.tools import group_caption_audit as gate


def _scan(source: str) -> list[str]:
    return [f.problem for f in gate.scan_source(textwrap.dedent(source), "quill/ui/x.py")]


def test_every_scribe_group_goes_through_the_helper() -> None:
    findings = gate.audit(gate.SCOPE)
    assert not findings, "\n".join(f"{f.path}:{f.line}: {f.problem}" for f in findings)


def test_the_scope_is_not_empty() -> None:
    names = {path.name for path in gate.module_paths(gate.SCOPE)}
    assert {"scribe_options_dialog.py", "scribe_convert_dialog.py"} <= names


def test_allowed_entries_have_reasons() -> None:
    assert all(reason.strip() for reason in gate.ALLOWED.values())


def test_a_check_box_in_a_static_box_must_be_described() -> None:
    assert _scan(
        """
        def build(self):
            box = wx.StaticBoxSizer(wx.VERTICAL, self, "Default formats")
            check = wx.CheckBox(box.GetStaticBox(), label="Word")
        """
    ) == ["wx.CheckBox check in a static box is not passed to describe_group"]
    assert not _scan(
        """
        def build(self):
            box = wx.StaticBoxSizer(wx.VERTICAL, self, "Default formats")
            check = wx.CheckBox(box.GetStaticBox(), label="Word")
            describe_group(box, check)
        """
    )


def test_a_name_bound_to_the_box_counts_as_the_box() -> None:
    assert _scan(
        """
        def build(self):
            parent = box.GetStaticBox()
            self.radio = wx.RadioButton(parent=parent, label="On")
        """
    ) == ["wx.RadioButton self.radio in a static box is not passed to describe_group"]


def test_the_older_layout_added_to_a_static_box_sizer_counts() -> None:
    assert _scan(
        """
        def build(self):
            box = wx.StaticBoxSizer(wx.VERTICAL, self, "Options")
            check = wx.CheckBox(self, label="Wrap")
            box.Add(check)
            box.Add(wx.CheckBox(self, label="Spell"))
        """
    ) == [
        "wx.CheckBox check in a static box is not passed to describe_group",
        "wx.CheckBox in a static box is not bound to a name",
    ]


def test_a_check_box_outside_any_group_is_left_alone() -> None:
    assert not _scan(
        """
        def build(self):
            check = wx.CheckBox(self, label="Offer Scribe")
            sizer.Add(check)
        """
    )


def test_a_radio_box_is_always_a_finding() -> None:
    assert _scan(
        """
        def build(self):
            self.mode = wx.RadioBox(self, label="Mode", choices=["a", "b"])
        """
    ) == ["wx.RadioBox: use GroupedRadioBox"]
