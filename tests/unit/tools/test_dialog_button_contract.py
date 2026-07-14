"""Dialog escape-button wiring gate (A11Y-4 / DLG-3 reinforcement, #124).

The repo-wide gate fails if any ``hardened_custom`` dialog declares a standard
``escape_id`` that no button carries and that it does not handle via a manual
``WXK_ESCAPE`` key handler -- the exact keyboard trap that shipped as #124
(Prompt Studio could not be closed with Escape). The synthetic tests pin the
audit's own logic so it cannot silently stop detecting the bug class.
"""

from __future__ import annotations

import ast

from quill.tools.dialog_button_contract import (
    _audit_module,
    find_violations,
)


def test_no_dialog_escape_button_traps_in_source() -> None:
    """Every custom dialog's Escape id must be backed by a button or handler."""
    violations = find_violations()
    assert not violations, (
        "Dialog(s) declare an Escape id with neither a matching button nor a "
        "WXK_ESCAPE handler, so Escape cannot close them (keyboard trap, "
        "WCAG 2.1.2, #124):\n" + "\n".join(f"  {v}" for v in violations)
    )


def _violations(source: str) -> list[str]:
    tree = ast.parse(source)
    return [f"{v.scope}:{v.wx_id}" for v in _audit_module("synthetic.py", source, tree)]


def test_audit_flags_escape_id_without_button() -> None:
    # Both affirmative_id and escape_id are now audited (M-24). This dialog has
    # neither a backing button for ID_OK nor for ID_CANCEL, so both are flagged.
    source = """
class TrapDialog:
    def __init__(self):
        self.dialog = wx.Dialog(parent, title="Trap")
        self.use = wx.Button(self.dialog, label="Use")
        apply_modal_ids(self.dialog, affirmative_id=wx.ID_OK, escape_id=wx.ID_CANCEL)
"""
    assert sorted(_violations(source)) == sorted(["TrapDialog:ID_OK", "TrapDialog:ID_CANCEL"])


def test_audit_accepts_matching_cancel_button() -> None:
    # Both affirmative and escape ids must be backed; provide both buttons.
    source = """
class OkDialog:
    def __init__(self):
        self.dialog = wx.Dialog(parent, title="Ok")
        self.ok = wx.Button(self.dialog, id=wx.ID_OK, label="Ok")
        self.close = wx.Button(self.dialog, id=wx.ID_CANCEL, label="Close")
        apply_modal_ids(self.dialog, affirmative_id=wx.ID_OK, escape_id=wx.ID_CANCEL)
"""
    assert _violations(source) == []


def test_audit_accepts_positional_button_id() -> None:
    source = """
class PositionalDialog:
    def __init__(self):
        self.dialog = wx.Dialog(parent, title="Positional")
        self.close = wx.Button(self.dialog, wx.ID_OK, label="Close")
        apply_modal_ids(self.dialog, affirmative_id=wx.ID_OK, escape_id=wx.ID_OK)
"""
    assert _violations(source) == []


def test_audit_accepts_create_button_sizer_flag() -> None:
    source = """
class SizerDialog:
    def __init__(self):
        self.dialog = wx.Dialog(parent, title="Sizer")
        buttons = self.dialog.CreateButtonSizer(wx.OK | wx.CANCEL)
        apply_modal_ids(self.dialog, affirmative_id=wx.ID_OK, escape_id=wx.ID_CANCEL)
"""
    assert _violations(source) == []


def test_audit_accepts_manual_escape_handler() -> None:
    # WXK_ESCAPE handler exempts escape_id; WXK_RETURN exempts affirmative_id.
    # Dialogs with only an escape handler are exempt only for escape_id.
    # Use escape_id only (no affirmative_id) to keep the test focused.
    source = """
class PaletteDialog:
    def __init__(self):
        self.dialog = wx.Dialog(parent, title="Palette")
        self.dialog.Bind(wx.EVT_CHAR_HOOK, self._on_char_hook)
        apply_modal_ids(self.dialog, escape_id=wx.ID_CANCEL)

    def _on_char_hook(self, event):
        if event.GetKeyCode() == wx.WXK_ESCAPE:
            self.dialog.EndModal(wx.ID_CANCEL)
"""
    assert _violations(source) == []


def test_unbacked_affirmative_id_flagged() -> None:
    # An unbacked affirmative_id with no WXK_RETURN handler means Enter is
    # silently ignored for blind and keyboard users (M-24).
    source = """
class EnterDialog:
    def __init__(self):
        self.dialog = wx.Dialog(parent, title="Enter")
        self.close = wx.Button(self.dialog, id=wx.ID_CANCEL, label="Close")
        apply_modal_ids(self.dialog, affirmative_id=wx.ID_OK, escape_id=wx.ID_CANCEL)
"""
    assert _violations(source) == ["EnterDialog:ID_OK"]


def test_audit_accepts_enter_handler_for_affirmative_id() -> None:
    # A WXK_RETURN handler exempts the affirmative_id from the backing-button
    # requirement, just as WXK_ESCAPE exempts escape_id.
    source = """
class EnterDialog:
    def __init__(self):
        self.dialog = wx.Dialog(parent, title="Enter")
        self.close = wx.Button(self.dialog, id=wx.ID_CANCEL, label="Close")
        apply_modal_ids(self.dialog, affirmative_id=wx.ID_OK, escape_id=wx.ID_CANCEL)
        self.dialog.Bind(wx.EVT_CHAR_HOOK, self._on_char_hook)

    def _on_char_hook(self, event):
        if event.GetKeyCode() == wx.WXK_RETURN:
            self.dialog.EndModal(wx.ID_OK)
"""
    assert _violations(source) == []


def test_audit_skips_non_standard_escape_ids() -> None:
    # Custom ids (self.ID_DISCARD) cannot be resolved to a button statically, so
    # they are skipped rather than flagged as false positives.
    source = """
class CustomIdDialog:
    def __init__(self):
        self.dialog = wx.Dialog(parent, title="Custom")
        apply_modal_ids(self.dialog, affirmative_id=self.ID_INSERT, escape_id=self.ID_DISCARD)
"""
    assert _violations(source) == []


def test_audit_respects_dialog_button_contract_pragma() -> None:
    # A trailing ``dialog_button_contract: exempt`` opt-out exempts a single
    # ``apply_modal_ids`` call from the static audit. This is the documented
    # escape hatch for stock wx dialogs whose YES/NO buttons are synthesised
    # at runtime (the static walk cannot see them); the pragma forces a
    # conscious reviewer decision and keeps the no-pragma path strict.
    source = """
class StockDialog:
    def __init__(self):
        self.dialog = wx.MessageDialog(parent, "msg", "title", wx.YES_NO | wx.NO_DEFAULT)
        apply_modal_ids(  # dialog_button_contract: exempt
            self.dialog, affirmative_id=wx.ID_YES, escape_id=wx.ID_NO)
"""
    assert _violations(source) == []


def test_audit_respects_legacy_noqa_pragma_spelling() -> None:
    # The legacy ``noqa: dialog_button_contract`` spelling is still accepted
    # for back-compat even though the canonical marker no longer uses noqa.
    source = (
        "class StockDialog:\n"
        "    def __init__(self):\n"
        '        self.dialog = wx.MessageDialog(parent, "m", "t", wx.YES_NO | wx.NO_DEFAULT)\n'
        "        apply_modal_ids(  # n" + "oqa: dialog_button_contract\n"
        "            self.dialog, affirmative_id=wx.ID_YES, escape_id=wx.ID_NO)\n"
    )
    assert _violations(source) == []


def test_audit_still_flags_pragma_omitted_stock_dialog() -> None:
    # A raw ``wx.Dialog`` with no real buttons for either declared id and no
    # pragma must be flagged for both -- this is the original WCAG 2.1.2 (#124)
    # keyboard trap pattern plus the M-24 affirmative_id extension.
    source = """
class RawDialog:
    def __init__(self):
        self.dialog = wx.Dialog(parent, title="Raw")
        self.use = wx.Button(self.dialog, label="Use")
        apply_modal_ids(self.dialog, affirmative_id=wx.ID_OK, escape_id=wx.ID_NO)
"""
    assert sorted(_violations(source)) == sorted(["RawDialog:ID_OK", "RawDialog:ID_NO"])
