"""Onboarding on QUILL's main window: the first-run wizard, the profile
onboarding, the trust and consent screen (and the re-consent that lists what
changed), and the BITS Whisperer welcome.

Moved whole out of ``MainFrame`` under qc.md F-08 (2026-10-03); the host
contract is unchanged.
"""

from __future__ import annotations

import sys

from quill.core.document import Document
from quill.core.onboarding import (
    load_trust_consent_status,
    mark_trust_consent_complete,
    trust_consent_change_log,
)
from quill.core.paths import app_data_dir
from quill.core.settings import save_settings


class OnboardingFlowMixin:
    """First-run, consent and welcome screens; mixed into ``MainFrame``."""

    def _show_trust_consent_onboarding(self, force: bool) -> bool:
        wx = self._wx
        status = getattr(self, "_trust_consent_status", None)
        reconsent = bool(status is not None and status.accepted and status.needs_reconsent)
        if sys.platform == "darwin":
            _key_storage_clause = "API keys are stored in the macOS Keychain."
        else:
            _key_storage_clause = (
                "API keys are stored in Windows Credential Manager when available, "
                "with DPAPI-encrypted fallback storage."
            )
        message = (
            "By selecting I accept, you confirm that:\n\n"
            "1. You are responsible for how AI outputs are used, reviewed, and shared.\n"
            "2. Cloud AI requests are user-initiated and subject to provider terms.\n"
            "3. Quill does not persist chat session transcripts from AI interactions.\n"
            f"4. {_key_storage_clause}\n\n"
            "Do you accept and want to continue?"
        )
        if reconsent:
            deltas = self._format_reconsent_deltas(status.loaded_version)
            message = (
                "Your prior trust, privacy, and responsible-AI disclosure is out of "
                "date.  Please review the changes below before continuing.\n\n"
                f"Changes since your prior consent:\n\n{deltas}\n\n" + message
            )
        title = (
            "Trust and Privacy Consent" if reconsent else "Trust, Privacy, and Responsible AI Use"
        )
        dialog = wx.MessageDialog(
            self.frame,
            message,
            "Trust, Privacy, and Responsible AI Use",
            wx.YES_NO | wx.ICON_INFORMATION,
        )
        if hasattr(dialog, "SetYesNoLabels"):
            dialog.SetYesNoLabels("I accept", "I do not accept")
        try:
            accepted = self._show_modal_dialog(dialog, title) == wx.ID_YES
        finally:
            dialog.Destroy()
        if accepted:
            mark_trust_consent_complete()
            self._trust_consent_status = load_trust_consent_status()
            return True
        return False

    @staticmethod
    def _format_reconsent_deltas(loaded_version: int) -> str:
        """Render the per-version change log as numbered bullet points (#305).

        Returns the deltas for every version strictly greater than
        ``loaded_version``, in version order.  Empty string when no deltas
        are recorded (e.g. the change log was wiped in a future cleanup).
        """
        lines: list[str] = []
        for version, delta in sorted(trust_consent_change_log().items()):
            if version <= loaded_version:
                continue
            if not delta:
                continue
            lines.append(f"- (version {version}) {delta}")
        return "\n".join(lines)

    def _show_bw_onboarding(self, force: bool) -> None:
        wx = self._wx
        response = self._show_message_box(
            "Configure QUILL Whisperer rollout defaults now?\n\n"
            "This step safely stages provider/model setup and status preferences without enabling "
            "runtime routing changes.",
            "QUILL Whisperer Setup",
            wx.ICON_QUESTION | wx.YES_NO,
        )
        if response != wx.YES:
            if force:
                self._set_status("QUILL Whisperer setup skipped")
            return
        self.apply_bw_recommended_provider()
        self.apply_bw_recommended_model()
        if not bool(getattr(self.settings, "bw_auto_open_status_page_on_download_start", False)):
            auto_open = self._show_message_box(
                "Auto-open Help > Status Page when QUILL Whisperer model downloads start?",
                "QUILL Whisperer Setup",
                wx.ICON_QUESTION | wx.YES_NO,
            )
            self.settings.bw_auto_open_status_page_on_download_start = auto_open == wx.YES
            save_settings(self.settings)
        self._set_status("QUILL Whisperer rollout defaults configured")

    def run_profile_onboarding(self) -> None:
        # Backward-compatible alias for older command IDs and automation scripts.
        self.run_startup_wizard()

    def _maybe_run_first_run_onboarding(self) -> None:
        from quill.core.paths import new_install_marker_path
        from quill.core.settings import save_settings as _save_settings
        from quill.core.storage import read_json, write_json_atomic

        # Consume the new-install marker dropped by the installer.  The marker
        # is written to {app} on every install (including upgrades) so that
        # setup_wizard_completed in %APPDATA% — which survives reinstalls — does
        # not silently suppress the first-run wizard after a fresh install.
        #
        # Deleting the marker can fail (#44) when Quill was installed elevated
        # into a directory the running user cannot write to — e.g. Program
        # Files after accepting a UAC prompt at install time. If the delete is
        # silently swallowed without recording that this marker was already
        # consumed, every subsequent launch re-enters this branch and force-
        # resets setup_wizard_completed, reopening the wizard forever.
        #
        # The sentinel under app_data_dir() (always writable per-user) records
        # the marker's resolved path so a marker we have already consumed is
        # recognized even when it could not be deleted (#647). The marker's
        # mtime alone is not a reliable identity — antivirus tools, filesystem
        # mtime drift, or other processes touching the file can change it
        # between launches, which caused the wizard to keep re-opening. The
        # path is stable for a given install, so a marker at a path the
        # sentinel already knows is treated as already consumed regardless of
        # mtime. A marker at a different path is a genuinely new install
        # (portable bundle moved, custom install location, etc.) and resets
        # the wizard as before.
        marker = new_install_marker_path()
        if marker is not None and marker.exists():
            try:
                marker_resolved = str(marker.resolve())
            except OSError:
                # The marker is visible to .exists() but not resolvable —
                # treat the current path as the identity so we still record
                # a sentinel and don't reopen the wizard on every launch.
                marker_resolved = str(marker)
            marker_mtime = marker.stat().st_mtime
            consumed_marker_path = app_data_dir() / "new-install-marker-consumed.json"
            consumed = read_json(consumed_marker_path, {})
            already_consumed = consumed.get("path") == marker_resolved
            if not already_consumed:
                if getattr(self.settings, "setup_wizard_completed", False):
                    self.settings.setup_wizard_completed = False
                    _save_settings(self.settings)
                write_json_atomic(
                    consumed_marker_path,
                    {"path": marker_resolved, "mtime": marker_mtime},
                )
            try:
                marker.unlink()
            except OSError:
                pass

        def _focus_editor() -> None:
            editor = getattr(self, "editor", None)
            if editor is not None and hasattr(editor, "SetFocus"):
                self._wx.CallAfter(editor.SetFocus)

        # Surface the result of a data move/import that an earlier launch
        # queued (e.g. the legacy-install import below, applied on restart).
        self._surface_data_migration_notice()

        # Before the first-run wizard, offer to import data stranded in a
        # previous install's location (portable<->installed switch, or a lost
        # storage-mode marker). If the user accepts, QUILL relaunches to apply
        # the import before Settings are read, so stop onboarding here.
        if not getattr(self.settings, "setup_wizard_completed", True):
            if self._maybe_offer_legacy_data_import():
                return

        # New unified first-run wizard: run when setup_wizard_completed is False
        # (i.e., a fresh install that has not seen the wizard yet). This is the
        # only onboarding surface shown on first run; once it completes,
        # run_setup_wizard() sets setup_wizard_completed=True and we never
        # re-prompt. The legacy "Startup Wizard overview" and per-feature
        # prompts that used to fire on later launches were removed (#700) -- the
        # unified wizard subsumes them, and each feature remains set up from its
        # own menu/button.
        if not getattr(self.settings, "setup_wizard_completed", True):
            try:
                self.run_startup_wizard(first_run=True)
            except Exception:
                self._report_startup_task_failure("first-run setup wizard")
            # #606: if the default "Untitled" tab was deferred at __init__
            # time, create it now that the wizard has closed. The
            # wizard's modal grabbed focus while the notebook was
            # empty; now we hand the user a fresh document.
            if getattr(self, "_first_run_wizard_pending", False):
                self._first_run_wizard_pending = False
                try:
                    self._create_document_tab(Document())
                except Exception:
                    self._report_startup_task_failure("first-run document tab")
                # Re-run the editor-dependent init steps that __init__
                # skipped for this branch. _create_document_tab() already
                # wired the tab + editor; these restore the location ring,
                # accessibility region, and soft-wrap style for the new document
                # (the _bind_events() call in __init__ no-opped soft wrap because
                # the editor did not exist yet).
                try:
                    self._location_ring.record(0)
                    self._region_tracker.enter("Editor")
                    self._apply_soft_wrap(self.settings.soft_wrap)
                except Exception:
                    pass
            _focus_editor()
            # _build_menu() in __init__ deferred its contextual refresh
            # because self.editor was not yet created. Now that the tab
            # has been added and self.editor is wired, flush the pending
            # refresh so contextual menu items (markup mode, document
            # name, etc.) reflect the active document.
            self._request_menu_refresh()
            return

        _focus_editor()
