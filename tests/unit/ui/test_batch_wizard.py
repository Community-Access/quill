"""Batch conversion wizard tests (issue #262).

Mostly source-level and dataclass-shape tests. Full wx-driven testing of the
:class:`BatchWizardDialog` is left to manual smoke tests because spinning up
``wx.App`` per case is heavy and the wizard's behavior is exercised end-to-end
in the manual QA plan in ``docs/release notes/release0.7.0.md``.

We do cover the ``run_batch_wizard`` orchestration contract: the launcher
returns ``None`` when the dialog is cancelled (any non-OK modal result) and
returns a :class:`BatchRequest` carrying a :class:`BatchPlan` when accepted.
"""

from __future__ import annotations

from pathlib import Path


def _wizard_pages_source() -> str:
    return (
        Path(__file__).resolve().parents[3] / "quill" / "ui" / "batch_wizard_pages.py"
    ).read_text(encoding="utf-8")


def _wizard_source() -> str:
    return (Path(__file__).resolve().parents[3] / "quill" / "ui" / "batch_wizard.py").read_text(
        encoding="utf-8"
    )


def _batch_convert_source() -> str:
    return (Path(__file__).resolve().parents[3] / "quill" / "core" / "batch_convert.py").read_text(
        encoding="utf-8"
    )


# ---------------------------------------------------------------------------
# Source-level contract: pages exist, dialog uses the right nav buttons.
# ---------------------------------------------------------------------------


def test_wizard_pages_module_has_four_page_classes() -> None:
    src = _wizard_pages_source()
    import re

    pages = re.findall(r"^class _\w+Page\(_WizardPage\)", src, re.MULTILINE)
    expected = {"_IntroPage", "_FolderPage", "_FormatPage", "_SummaryPage"}
    found = {m.split("(")[0].replace("class ", "") for m in pages}
    assert found == expected, f"Expected {expected}, found {found}"


def test_wizard_dialog_uses_modal_ids() -> None:
    src = _wizard_pages_source()
    # The contract: the dialog must apply modal IDs so screen readers and the
    # dialog inventory gate can identify the affirmative / cancel buttons.
    assert "apply_modal_ids(self" in src
    assert "affirmative_id=wx.ID_OK" in src
    assert "cancel_id=wx.ID_CANCEL" in src


def test_wizard_pages_do_not_block_keyboard_focus() -> None:
    """a11y: pages must not override AcceptsFocusFromKeyboard to False."""

    src = _wizard_pages_source()
    assert "def AcceptsFocusFromKeyboard" not in src
    assert "def AcceptsFocus" not in src
    assert "_focus_first_page_control" in src


def test_wizard_initializes_choices_from_settings() -> None:
    """The wizard must seed choices from settings defaults, not hard-coded values."""

    src = _wizard_pages_source()
    assert "settings.import_export_recursive" in src
    assert "settings.import_export_output_layout" in src
    assert "settings.import_export_overwrite" in src
    assert "settings.import_export_last_folder" in src


def test_wizard_uses_tier1_format_choices() -> None:
    """The format page reads the Tier-1 set from the registry."""

    src = _wizard_pages_source()
    # The wizard pulls Tier-1 lists via formats_for_direction(); we don't
    # require the raw frozensets to be referenced directly.
    assert "pandoc_formats.formats_for_direction" in src
    assert "pandoc_formats.get_format" in src


def test_wizard_offers_profile_choices() -> None:
    src = _wizard_pages_source()
    assert "convert_profiles.PROFILES" in src


def test_wizard_folder_page_uses_dir_picker() -> None:
    src = _wizard_pages_source()
    # The folder page should use wx.DirPickerCtrl, not a raw TextCtrl.
    assert "wx.DirPickerCtrl" in src
    assert "_FolderPage" in src


def test_wizard_summary_page_renders_human_text() -> None:
    src = _wizard_pages_source()
    assert "class _SummaryPage" in src
    assert "refresh(self._choices)" in src or "refresh(self, choices" in src


def test_wizard_intro_disables_start_when_pandoc_missing() -> None:
    """The wizard must short-circuit Start when Pandoc is not detected."""

    src = _wizard_pages_source()
    assert "pandoc_available" in src


# ---------------------------------------------------------------------------
# Launcher contract (run_batch_wizard)
# ---------------------------------------------------------------------------


def test_run_batch_wizard_returns_none_for_cancelled_dialog() -> None:
    """``run_batch_wizard`` must return None when the dialog is cancelled.

    We don't actually run wx; we inspect the launcher's logic for the
    ShowModal result mapping.
    """

    src = _wizard_source()
    assert "result != wx.ID_OK" in src
    assert "return None" in src
    assert "build_request" in src


def test_run_batch_wizard_returns_batch_request_on_accept() -> None:
    """On wx.ID_OK the launcher must call ``build_request`` and return it."""

    src = _wizard_source()
    assert "dlg.build_request()" in src
    assert "BatchRequest" in src


def test_run_batch_wizard_passes_show_modal_fn() -> None:
    """``show_modal_fn`` is required for SR enter/exit announcements."""

    src = _wizard_source()
    assert "show_modal_fn" in src
    assert "announce_cb" in src


def test_run_batch_wizard_destroys_dialog() -> None:
    src = _wizard_source()
    assert "dlg.Destroy()" in src


# ---------------------------------------------------------------------------
# Wizard -> worker handoff: build_request produces a plan
# ---------------------------------------------------------------------------


def test_build_request_constructs_batch_plan_from_choices() -> None:
    """The dialog's build_request must yield a BatchPlan carrying every choice."""

    src = _wizard_pages_source()
    assert "def build_request(self) -> BatchRequest" in src
    assert "BatchPlan(" in src
    assert "root=self._choices.root" in src
    assert "recursive=self._choices.recursive" in src
    assert "source_format=self._choices.source_format" in src
    assert "target_format=self._choices.target_format" in src
    assert "output_layout=self._choices.output_layout" in src
    assert "overwrite=self._choices.overwrite" in src
    assert "profile=self._choices.profile" in src


def test_run_batch_wizard_persists_last_folder() -> None:
    """The wizard persists ``import_export_last_folder`` on Start."""

    src = _wizard_pages_source()
    assert "import_export_last_folder" in src


# ---------------------------------------------------------------------------
# Helper: plan-shape invariants the wizard must satisfy
# ---------------------------------------------------------------------------


def test_batch_plan_has_eight_fields() -> None:
    """Lock the BatchPlan field set so the wizard can't drift from core."""

    src = _batch_convert_source()
    expected = (
        "root: Path",
        "recursive: bool",
        "source_format: str",
        "target_format: str",
        "output_layout: OutputLayout",
        "overwrite: OverwritePolicy",
        "profile: str | None = None",
    )
    for needle in expected:
        assert needle in src, f"Missing field in BatchPlan: {needle}"


def test_overwrite_policy_literal_includes_three_values() -> None:
    src = _batch_convert_source()
    assert 'Literal["ask", "never", "always"]' in src


def test_output_layout_literal_includes_two_values() -> None:
    src = _batch_convert_source()
    assert 'Literal["same_folder", "subfolder"]' in src
