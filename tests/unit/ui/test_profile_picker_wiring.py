"""Source-contract wiring for the profile picker + startup hooks (issue #138).

wxPython is headless-unfriendly, so this pins the integration points in source:
the Alt+Shift+P switch delegates to the new picker, the open path applies the
extension mapping, and deferred startup can prompt for a profile.
"""

from __future__ import annotations

from pathlib import Path


def _main_frame_source() -> str:
    return Path("quill/ui/main_frame.py").read_text(encoding="utf-8")


def test_main_frame_mixes_in_the_profile_picker() -> None:
    source = _main_frame_source()
    assert "from quill.ui.main_frame_profile_picker import ProfilePickerMixin" in source
    assert "    ProfilePickerMixin,\n" in source


def test_switch_feature_profile_delegates_to_the_picker() -> None:
    source = _main_frame_source()
    start = source.index("def switch_feature_profile")
    body = source[start : start + 400]
    assert "self.open_profile_picker()" in body
    # The old SingleChoiceDialog flow is gone.
    assert "wx.SingleChoiceDialog(" not in body


def test_open_applies_extension_profile_mapping() -> None:
    source = _main_frame_source()
    assert "self.maybe_switch_profile_for_open(selected_path)" in source


def test_deferred_startup_can_prompt_for_a_profile() -> None:
    source = _main_frame_source()
    assert '("startup profile prompt", self.run_startup_profile_prompt)' in source


def test_picker_dialog_has_a_cancel_button() -> None:
    source = Path("quill/ui/profile_picker.py").read_text(encoding="utf-8")
    assert "wx.ID_CANCEL" in source
    assert "wx.ID_OK" in source


def test_picker_listbox_and_description_coerce_lazy_strings() -> None:
    # Same bug class as #261: ProfileDefinition.name/description can be a
    # _LazyString from lazy_gettext(...). wxPython's strict ListBox/TextCtrl
    # overload checker on Windows rejects that directly, surfacing as
    # 'Startup task failed: startup profile prompt' whenever the picker
    # opened with an unconverted name/description. Coerce to str at the use
    # site, same as the wizard pages fix.
    source = Path("quill/ui/profile_picker.py").read_text(encoding="utf-8")
    assert "choices=[str(name) for _k, _i, name, _d in entries]" in source
    assert "self.description.SetValue(str(self._entries[index][3]))" in source
