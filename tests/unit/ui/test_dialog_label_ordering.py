"""Gating tests for JAWS label-buddy Z-order correctness in dialogs.

On Windows, JAWS associates a label with a combo box or text field by finding
the immediately-preceding wx.StaticText sibling in the parent window's child
list.  Child windows are ordered by creation time.  If a control is created
before its StaticText label, the label ends up AFTER the control in Z-order
and JAWS announces the wrong text (or nothing).

These tests read source as text to lock in the patterns that keep labels
before their controls in the child-creation order (issue #249).
"""

from pathlib import Path

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _slice_function(source: str, fn_sig: str, stop_sig: str = "\n    def ") -> str:
    start = source.index(fn_sig)
    end = source.index(stop_sig, start + 1)
    return source[start:end]


def _main_frame_source() -> str:
    return Path("quill/ui/main_frame.py").read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# open_general_preferences / _make_control
# ---------------------------------------------------------------------------


def test_general_preferences_no_prelabeled_controls() -> None:
    source = _main_frame_source()
    start = source.index("def _make_control(parent_panel, sizer, spec, page_index: int)")
    end = source.index("\n            page_index = 0", start)
    body = source[start:end]

    # Before the fix these exact strings were present: a pre-created control
    # passed directly to _add_field_row, which creates StaticText inside —
    # making the label appear AFTER the control in Z-order.
    assert "_add_field_row(parent_panel, sizer, spec.label, choice, reset_btn)" not in body
    assert "_add_field_row(parent_panel, sizer, spec.label, spin, reset_btn)" not in body
    assert "_add_field_row(parent_panel, sizer, spec.label, text, reset_btn)" not in body
    assert "_add_field_row(parent_panel, sizer, spec.label, folder_row, reset_btn)" not in body
    assert "_add_field_row(parent_panel, sizer, spec.label, file_row, reset_btn)" not in body


def test_general_preferences_factory_functions_present() -> None:
    source = _main_frame_source()
    start = source.index("def _make_control(parent_panel, sizer, spec, page_index: int)")
    end = source.index("\n            page_index = 0", start)
    body = source[start:end]

    # Each labeled control kind must be created via a named factory so
    # _add_field_row creates the StaticText label first.
    assert "_make_browser_choice" in body
    assert "_make_folder_row" in body
    assert "_make_sound_file_row" in body
    assert "_make_choice" in body
    assert "_make_spin_int" in body
    assert "_make_spin_float" in body
    assert "_make_text" in body


def test_general_preferences_int_spin_names_its_inner_textctrl() -> None:
    """support#69: VoiceOver reads a SpinCtrl's inner TextCtrl child, not the
    outer control's Name. The "float" kind (SpinCtrlDouble) already named its
    inner TextCtrl; the "int" kind (SpinCtrl) -- used for Read Aloud
    rate/volume/pitch and every other integer setting -- did not, so those
    controls were announced with no label on macOS."""
    source = _main_frame_source()
    start = source.index("def _make_spin_int(")
    end = source.index("\n\n", start)
    body = source[start:end]

    assert "GetChildren()" in body, (
        "_make_spin_int must walk its children to name the inner TextCtrl, "
        "matching _make_spin_float's fix"
    )
    assert "isinstance(_child, wx.TextCtrl)" in body
    assert "_child.SetName(_spec.label)" in body


# ---------------------------------------------------------------------------
# open_profiles_and_features_settings — keyboard_pack_choice
# ---------------------------------------------------------------------------


def test_profiles_dialog_keyboard_pack_label_before_choice() -> None:
    source = _main_frame_source()
    body = _slice_function(source, "def open_profiles_and_features_settings(self)")

    # "Keyboard pack:" StaticText must be created before the Choice so JAWS
    # finds the right label buddy.
    label_pos = body.index('label="Keyboard pack:"')
    choice_pos = body.index("keyboard_pack_choice = wx.Choice(")
    assert label_pos < choice_pos, (
        "StaticText 'Keyboard pack:' must appear before keyboard_pack_choice creation"
    )


def test_profiles_dialog_keyboard_pack_choice_not_created_early() -> None:
    source = _main_frame_source()
    body = _slice_function(source, "def open_profiles_and_features_settings(self)")

    # keyboard_pack_choice must NOT be created before the closures section
    # (i.e., before the layout section).  We verify it appears after the
    # "Keyboard experience" description text in source order.
    description_pos = body.index('"Keyboard experience: choose a golden pack')
    choice_pos = body.index("keyboard_pack_choice = wx.Choice(")
    assert description_pos < choice_pos, (
        "keyboard_pack_choice must be created in the layout section, after the description text"
    )


# ---------------------------------------------------------------------------
# ai_model_panel — tier_choice
# ---------------------------------------------------------------------------


def test_ai_model_panel_tier_choice_preceded_by_label() -> None:
    source = Path("quill/ui/ai_model_panel.py").read_text(encoding="utf-8")
    start = source.index("def _build_tier_section(self, root")
    end = source.index("\n    def ", start + 1)
    body = source[start:end]

    tier_choice_pos = body.index("self.tier_choice = wx.Choice(")
    text_before = body[:tier_choice_pos]

    # The immediately-preceding StaticText creation should be a concise label,
    # not the long intro paragraph.
    last_static = text_before.rindex("wx.StaticText(")
    label_fragment = text_before[last_static:tier_choice_pos]
    assert "Active speed tier" in label_fragment, (
        "A concise 'Active speed tier' label must immediately precede tier_choice creation"
    )


def test_ai_model_panel_tier_model_pickers_already_correct() -> None:
    source = Path("quill/ui/ai_model_panel.py").read_text(encoding="utf-8")
    start = source.index("def _build_tier_section(self, root")
    end = source.index("\n    def ", start + 1)
    body = source[start:end]

    # The per-tier model pickers in the loop use the pattern:
    #   root.Add(wx.StaticText(...))  <- label first
    #   picker = wx.Choice(...)       <- control after
    # Verify the StaticText add appears before the picker creation.
    label_pos = body.index("tier.label} tier model")
    picker_pos = body.index("picker = wx.Choice(")
    assert label_pos < picker_pos
