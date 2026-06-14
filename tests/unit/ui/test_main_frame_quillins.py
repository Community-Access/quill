"""Source-contract tests for the Quillins UI wiring in main_frame_quillins.py.

Live wx construction of the full MainFrame is impractical in this environment, so
(as with the EDS and A11Y-4 dialog-contract guards) these assert the wiring via
source text: the Manager command is registered, the Tools > Quillins submenu is
attached, the runtime honours the SEC-8 gate, and the Manager dialog obeys the
hardened-dialog contract (stock controls, explicit default, modal-id routing,
lifecycle Destroy, focus return).
"""

from __future__ import annotations

from pathlib import Path

import quill.ui.main_frame as main_frame_module
import quill.ui.main_frame_menu as main_frame_menu_module
import quill.ui.main_frame_quillins as quillins_module

_QUILLINS = Path(quillins_module.__file__).read_text(encoding="utf-8")
_MENU = Path(main_frame_menu_module.__file__).read_text(encoding="utf-8")
_MAIN = Path(main_frame_module.__file__).read_text(encoding="utf-8")


def test_mixin_is_a_main_frame_base() -> None:
    bases = _MAIN.split("class MainFrame(")[1].split(")")[0]
    assert "QuillinsMenuMixin" in bases


def test_manager_command_is_registered() -> None:
    assert "self._register_quillins_commands()" in _MAIN
    register = _QUILLINS[_QUILLINS.index("def _register_quillins_commands") :][:500]
    assert "self.commands.register(" in register
    assert "_QUILLINS_MANAGER_COMMAND" in register
    assert "self._binding_for(_QUILLINS_MANAGER_COMMAND)" in register


def test_quillins_submenu_is_attached_to_tools() -> None:
    assert 'AppendSubMenu(self._build_quillins_menu(), "&Quillins")' in _MENU


def test_runtime_gates_bundled_and_third_party_separately() -> None:
    # Registration loads bundled (Tier C) behind core.bundled_quillins and
    # third-party behind the SEC-8 flag — they are merged into one registry.
    reg = _QUILLINS[_QUILLINS.index("def _register_quillin_contributions") :][:900]
    assert "load_enabled_bundled_manifests(self.features)" in reg
    assert "load_enabled_manifests(self.features)" in reg
    enabled = _QUILLINS[_QUILLINS.index("def _quillins_enabled") :][:400]
    assert "THIRD_PARTY_PLUGINS_FEATURE" in enabled


def test_run_command_runs_bundled_but_refuses_disabled_third_party() -> None:
    run = _QUILLINS[_QUILLINS.index("def run_quillin_command") :][:900]
    # Bundled commands run regardless of the SEC-8 flag; third-party do not.
    assert "self._bundled_command_ids" in run
    assert "not self._quillins_enabled()" in run
    assert "disabled" in run


def test_snippet_and_handler_paths_both_exist() -> None:
    run = _QUILLINS[_QUILLINS.index("def run_quillin_command") :][:1200]
    assert "_run_quillin_snippet" in run
    assert "_run_quillin_handler" in run
    # Handler path goes through the out-of-process host.
    handler = _QUILLINS[_QUILLINS.index("def _run_quillin_handler") :][:600]
    assert "ExtensionHost(" in handler
    assert "consent=self._quillin_consent" in handler


def test_consent_prompt_is_a_native_yes_no_dialog() -> None:
    consent = _QUILLINS[_QUILLINS.index("def _quillin_consent") :]
    assert "wx.MessageDialog(" in consent
    assert "wx.YES_NO" in consent
    assert "NO_DEFAULT" in consent  # default is deny
    assert "dialog.Destroy()" in consent


def test_consent_prompt_routes_through_dialog_contract() -> None:
    """H-3-ui: the Quillin consent prompt must go through show_modal_dialog.

    Direct ``.ShowModal()`` would skip the region tracker, the
    screen-reader entry/exit announcement, and the editor focus
    return — exactly the regression the dialog contract prevents.
    """
    consent = _QUILLINS[_QUILLINS.index("def _quillin_consent") :]
    assert "self._show_modal_dialog(dialog" in consent
    assert "apply_modal_ids(dialog" in consent
    # And: the direct ShowModal() call must be gone from the consent path.
    assert "dialog.ShowModal()" not in consent


def test_remove_quillin_confirm_routes_through_dialog_contract() -> None:
    """H-4-ui: the destructive Remove Quillin confirm must go through
    the shared modal helper so the focus-return and region
    announcement apply."""
    on_remove = _QUILLINS[
        _QUILLINS.index("def on_remove") : _QUILLINS.index("def on_remove") + 2200
    ]
    assert "self._show_modal_dialog(confirm" in on_remove
    assert "apply_modal_ids(confirm" in on_remove
    assert "confirm.Destroy()" in on_remove
    # And: no direct ShowModal() on the confirm dialog.
    assert "confirm.ShowModal()" not in on_remove


def test_manager_dialog_uses_stock_controls() -> None:
    manager = _QUILLINS[_QUILLINS.index("def open_quillins_manager") :]
    assert "wx.ListBox(" in manager
    assert "wx.TE_MULTILINE | wx.TE_READONLY" in manager
    # No bespoke/custom-drawn controls.
    assert "wx.Dialog(" in manager


def test_manager_dialog_obeys_hardened_contract() -> None:
    manager = _QUILLINS[_QUILLINS.index("def open_quillins_manager") :]
    assert "close_button.SetDefault()" in manager
    assert "apply_modal_ids(dialog" in manager
    assert "self._show_modal_dialog(dialog" in manager
    assert "dialog.Destroy()" in manager
    # Focus returns to the launching control on close.
    assert "launcher.SetFocus()" in manager
    # Button sizer expands rather than right-aligning.
    assert "button_sizer" in manager
    assert "wx.ALIGN_RIGHT" not in manager


def test_modal_ids_route_through_dialog_contract() -> None:
    manager = _QUILLINS[_QUILLINS.index("def open_quillins_manager") :]
    # The Manager applies the shared modal-id contract inline (DLG-3 hardening
    # guard requires the literal apply_modal_ids call within the dialog scope).
    # Escape maps to the single Close button (wx.ID_OK), the only non-destructive
    # dismiss, so Escape can always close the dialog without a keyboard trap
    # (WCAG 2.1.2; enforced by the dialog button-contract gate).
    assert "from quill.ui.dialog_contract import apply_modal_ids" in manager
    assert "apply_modal_ids(dialog, affirmative_id=wx.ID_OK, escape_id=wx.ID_OK)" in manager


def test_controls_parented_directly_on_dialog() -> None:
    # Controls must be parented directly on the dialog (not on an inner panel)
    # so NVDA users do not have to navigate into a group before reaching controls.
    manager = _QUILLINS[_QUILLINS.index("def open_quillins_manager") :]
    assert "panel = wx.Panel(dialog)" not in manager
    assert "wx.StaticText(dialog," in manager
    assert "wx.ListBox(dialog," in manager
    assert "wx.Button(dialog," in manager
    assert "dialog.SetSizerAndFit(body)" in manager


def test_host_services_never_imports_wx_into_core() -> None:
    # The wx-using adapter lives in the UI module; core stays wx-free.
    assert "import wx" not in _QUILLINS  # wx is reached via self._wx, never imported here
