"""Update checking and delivery for MainFrame (CQ-1 decomposition).

``UpdatesMixin`` owns the QUILL self-update flow -- the startup/manual GitHub
release check, release-notes presentation, the beta-channel offer/confirm
dialogs, skip-version bookkeeping, the consented download of installer or
portable builds, and post-download actions (reveal, launch installer, extract
portable) -- plus the consented GLOW engine update check
(``check_for_glow_updates``). Extracted verbatim from ``main_frame.py``; runs
on ``MainFrame`` (``self``). All outbound network call sites here are covered
by the network egress audit (see ``quill/tools/network_egress_audit.py``).
"""

from __future__ import annotations

import sys
import threading
import webbrowser
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING
from urllib.error import URLError

if TYPE_CHECKING:  # imports kept out of cold-start path
    from quill.core.glow_updates import GlowUpdateCheck
    from quill.core.updates import GitHubRelease, UpdateManifest

from quill import build_info
from quill.core.browser_preview import (
    render_preview_body,
)
from quill.core.paths import app_data_dir
from quill.core.settings import save_settings
from quill.core.text_utils import strip_md_to_plain as _strip_md_to_plain
from quill.ui.dialog_contract import (
    apply_modal_ids,
)


class UpdatesMixin:
    def _update_check_due(self, interval_hours: int = 24) -> bool:
        """True when enough time has passed since the last startup update check.

        Manual checks always run; this only throttles the silent startup check so
        QUILL doesn't hit the network on every single launch.
        """
        last = str(getattr(self.settings, "last_update_check", "") or "").strip()
        if not last:
            return True
        try:
            previous = datetime.fromisoformat(last)
        except ValueError:
            return True
        if previous.tzinfo is None:
            previous = previous.replace(tzinfo=UTC)
        return datetime.now(UTC) - previous >= timedelta(hours=interval_hours)

    def check_for_updates(self, silent_no_update: bool = False) -> None:
        from quill.core.updates import (
            fetch_releases,
            fetch_update_manifest,
            is_newer_version,
            running_portable,
        )

        if getattr(self, "_update_check_in_progress", False):
            if not silent_no_update:
                self._set_status("Update check already in progress")
            return

        wx = self._wx
        current_version = build_info.resolve_running_version(
            override=getattr(getattr(self, "_updates", None), "current_version", "")
        )

        self.settings.last_update_check = datetime.now(UTC).isoformat()
        try:
            save_settings(self.settings)
        except Exception:  # noqa: BLE001
            pass

        if not silent_no_update:
            self._set_status_quiet("Checking for updates...")
            self._announce("Checking for updates")

        beta = bool(getattr(self.settings, "beta_updates", False))
        self._update_check_in_progress = True
        # Portable installs update by replacing the bundle, not by running the
        # installer. The signed manifest feed only carries the installer URL, so
        # for a portable build we skip it and use the GitHub releases path, which
        # exposes every asset and (via _pick_asset) selects the portable .zip.
        portable = running_portable()

        def _run_fetch():
            manifest: UpdateManifest | None = None
            releases: list[GitHubRelease] | None = None
            fetch_error: str | None = None
            try:
                # Always fetch the signed manifest — it carries the feature
                # kill-switch advisories, which must reach (and be lifted on)
                # portable builds too. URL resolves the QUILL_UPDATE_MANIFEST_URL
                # override (default: the production feed) for release rehearsals.
                try:
                    manifest = fetch_update_manifest()
                except (URLError, ValueError, OSError):
                    # Best-effort: a missing/unreachable/invalid feed is not an
                    # error here — we fall back to the GitHub releases path below.
                    pass
                # Portable updates by replacing the bundle, so its download
                # *prompt* uses the releases path (portable .zip), not the
                # manifest's installer URL — but advisories above still apply.
                if (
                    portable
                    or manifest is None
                    or not is_newer_version(current_version, manifest.version)
                ):
                    releases = fetch_releases()
            except (URLError, ValueError, OSError) as exc:
                fetch_error = str(exc)
            except Exception as exc:  # noqa: BLE001
                fetch_error = str(exc)
            return manifest, releases, fetch_error

        call_after = getattr(wx, "CallAfter", None)
        if callable(call_after):
            import threading

            def _bg() -> None:
                m, r, e = _run_fetch()
                call_after(
                    self._on_update_fetch_done,
                    m,
                    r,
                    e,
                    silent_no_update,
                    current_version,
                    beta,
                )

            threading.Thread(  # GATE-40-OK: update-manifest fetcher; one-shot network.
                target=_bg, daemon=True
            ).start()
        else:
            # Synchronous fallback for test environments without wx.CallAfter.
            m, r, e = _run_fetch()
            self._on_update_fetch_done(m, r, e, silent_no_update, current_version, beta)

    def _on_update_fetch_done(
        self,
        manifest: UpdateManifest | None,
        releases: list[GitHubRelease] | None,
        fetch_error: str | None,
        silent_no_update: bool,
        current_version: str,
        beta: bool,
    ) -> None:
        """UI-thread callback once the background update-network fetch finishes."""
        from quill.core.feedback_token import github_token_present
        from quill.core.updates import (
            find_release,
            is_newer_version,
            running_portable,
            select_latest,
        )

        self._update_check_in_progress = False
        wx = self._wx

        # Remote kill switch: apply any signed feature advisories from the manifest
        # for this version (a manifest with none clears prior locks). Always runs,
        # regardless of whether a newer build exists.
        if manifest is not None:
            self._apply_feature_advisories(manifest, current_version)

        # Compatibility path: signed manifest feed. Skipped on portable — its
        # manifest is fetched only for advisories (above); the download prompt
        # uses the releases path so a portable user is offered the .zip, not the
        # installer.
        if (
            manifest is not None
            and not running_portable()
            and is_newer_version(current_version, manifest.version)
        ):
            if silent_no_update:
                self._record_notification(
                    f"Update {manifest.version} found via manifest feed", "update"
                )
                return
            download_now = self._show_message_box(
                f"Update {manifest.version} is available.\n\nOpen the update download now?",
                "Check for Updates",
                wx.ICON_INFORMATION | wx.YES_NO,
            )
            if download_now == wx.YES:
                self._open_update_download_flow(manifest)
            else:
                self._set_status("Update deferred")
                self._record_notification(f"Update {manifest.version} deferred", "update")
            return

        # Network error during GitHub releases fetch.
        if fetch_error is not None:
            if silent_no_update:
                self._record_notification(f"Update check failed: {fetch_error}", "update")
                self._set_status("Update check failed")
                return
            self._html_info(
                "Check for Updates",
                f"# Update check failed\n\nCould not check for updates:\n\n`{fetch_error}`",
            )
            self._set_status("Update check failed")
            self._record_notification("Update check failed", "update")
            return

        releases = releases or []
        latest_any = select_latest(releases, include_prereleases=True)
        latest_stable = select_latest(releases, include_prereleases=False)

        # Auto-enroll in beta channel when running a prerelease build.
        current_match = find_release(releases, current_version)
        if not beta and current_match is not None and current_match.prerelease:
            self.settings.beta_updates = True
            save_settings(self.settings)
            beta = True
            self._record_notification(
                "You're running a beta build, so beta updates are enabled.", "update"
            )

        target = latest_any if beta else latest_stable
        newer = target is not None and is_newer_version(current_version, target.version)
        # #919 self-heal: a build running without its bundled bug-report token
        # can't file in-app issues. Offer the latest release even at the same
        # version, so installing it restores the token. This stops the moment
        # the token is back, and the user can silence it with "Skip this version".
        token_selfheal = target is not None and not github_token_present()
        if target is not None and (newer or token_selfheal):
            if silent_no_update and target.version == getattr(
                self.settings, "skipped_update_version", ""
            ):
                self._record_notification(
                    f"Update {target.version} available (skipped by you)", "update"
                )
                return
            if silent_no_update:
                if newer:
                    self._record_notification(
                        f"Update {target.version} found; downloading", "update"
                    )
                    self._download_update_release(target)
                else:
                    # Self-heal at the same version: don't auto-download in the
                    # background. Surface a notification so the user chooses to
                    # reinstall via Check for Updates.
                    self._record_notification(
                        "A build that restores the bug-report token is available. "
                        "Use Check for Updates to install it.",
                        "update",
                    )
                    self._set_status("Update available (restores bug-report token)")
                return
            action = self._show_update_available_dialog(
                current_version, target, self_heal=token_selfheal and not newer
            )
            if action == "download":
                self._download_update_release(target)
            elif action == "skip":
                self._skip_update_version(target.version)
            else:
                self._set_status("Update deferred")
                self._record_notification(f"Update {target.version} deferred", "update")
            return

        # No update on current channel — check if a prerelease is available on stable.
        prerelease_available = (
            not beta
            and latest_any is not None
            and latest_any.prerelease
            and is_newer_version(current_version, latest_any.version)
        )
        if prerelease_available:
            if silent_no_update:
                self._record_notification(
                    f"A beta build {latest_any.version} is available. "
                    "Enable beta updates to install it.",
                    "update",
                )
                self._set_status("Beta update available")
                return
            self._route_prerelease_to_beta(current_version, latest_any)
            return

        # Genuinely up to date.
        if silent_no_update:
            self._record_notification("Update check found no newer version", "update")
            return
        self._set_status_quiet("No update available")
        self._announce("Quill is up to date")
        self._record_notification("Update check found no newer version", "update")
        if beta:
            self._html_info(
                "Check for Updates",
                "# You're up to date\n\n"
                "You're on the **beta** channel and running the newest build.\n\n"
                f"**Current version:** {current_version}",
            )
        else:
            self._offer_beta_switch(current_version, latest_stable)

    def _route_prerelease_to_beta(self, current_version: str, release: GitHubRelease) -> None:
        """A prerelease is available while on stable — enroll in beta (with the
        consent gate), then offer the prerelease for download."""
        if not self._confirm_beta_channel(release):
            self._set_status("Stayed on the stable channel")
            return
        self.settings.beta_updates = True
        save_settings(self.settings)
        self._set_status_quiet("Switched to the beta update channel")
        self._announce("Beta updates enabled")
        action = self._show_update_available_dialog(current_version, release)
        if action == "download":
            self._download_update_release(release)
        elif action == "skip":
            self._skip_update_version(release.version)

    def _render_html(self, markdown_text: str) -> str:

        return render_preview_body(markdown_text, "markdown")

    def _vendored_glow_wheels_dir(self) -> Path | None:
        """The directory holding QUILL's vendored GLOW wheels (rollback floor)."""
        candidate = Path(__file__).resolve().parents[2] / "vendor" / "wheels"
        if candidate.is_dir():
            return candidate
        # Frozen builds may place vendored wheels beside the interpreter prefix.
        alt = Path(sys.prefix) / "vendor" / "wheels"
        return alt if alt.is_dir() else None

    def check_for_glow_updates(self, silent_no_update: bool = False) -> None:
        """Check for, and optionally apply, a newer GLOW accessibility engine.

        Opt-in and consented (GLOW-8): invoking this command is the explicit
        action that authorizes the network check; a second confirmation gate is
        shown before anything is downloaded or installed. The engine is verified
        (signed manifest, per-wheel SHA-256) and installed offline; a failed
        install rolls back to the vendored wheels. The new engine loads on
        restart.
        """
        from quill.core.glow_updates import check_for_glow_update

        wx = self._wx
        if not self._ensure_glow_enabled():
            return
        self._set_status("Checking for GLOW engine updates...")
        try:
            check: GlowUpdateCheck = check_for_glow_update()
        except (URLError, ValueError, OSError) as error:
            if silent_no_update:
                self._record_notification(f"GLOW update check failed: {error}", "update")
                self._set_status("GLOW update check failed")
                return
            self._html_info(
                "Check for GLOW Updates",
                f"# GLOW update check failed\n\nCould not check for updates:\n\n`{error}`",
            )
            self._set_status("GLOW update check failed")
            return

        if not check.update_available:
            if silent_no_update:
                self._record_notification("GLOW engine is up to date", "update")
                return
            installed = check.installed_version or "not installed"
            self._html_info(
                "Check for GLOW Updates",
                "# GLOW engine is up to date\n\n"
                f"**Installed:** {installed}  \n"
                f"**Latest:** {check.available_version}",
            )
            self._set_status("GLOW engine is up to date")
            return

        if silent_no_update:
            self._record_notification(
                f"GLOW engine {check.available_version} is available", "update"
            )
            self._set_status("GLOW update available")
            return

        manifest = check.manifest
        wheel_list = "\n".join(f"- `{w.filename}`" for w in manifest.wheels)
        notes = manifest.notes or "_(no release notes provided)_"
        proceed = self._show_message_box(
            (
                f"GLOW engine {manifest.version} is available "
                f"(installed: {check.installed_version or 'none'}).\n\n"
                f"{notes}\n\n"
                "This downloads and installs the engine, then QUILL must restart "
                "to apply it. Download and install now?"
            ),
            "Check for GLOW Updates",
            wx.ICON_INFORMATION | wx.YES_NO,
        )
        if proceed != wx.YES:
            self._set_status("GLOW update deferred")
            self._record_notification(f"GLOW update {manifest.version} deferred", "update")
            return

        import tempfile

        from quill.core.glow_updates import apply_glow_update

        staging = Path(tempfile.mkdtemp(prefix="quill-glow-update-"))
        self._set_status(f"Downloading GLOW engine {manifest.version}...")
        result = apply_glow_update(
            manifest,
            staging,
            rollback_dir=self._vendored_glow_wheels_dir(),
        )
        if result.applied:
            self._html_info(
                "GLOW update complete",
                f"# GLOW engine updated to {manifest.version}\n\n"
                f"{wheel_list}\n\n"
                "**Restart QUILL** to load the new accessibility engine.",
            )
            self._set_status_quiet(f"GLOW engine updated to {manifest.version}; restart to apply")
            self._announce(f"GLOW engine updated to {manifest.version}. Restart to apply.")
            self._record_notification(
                f"GLOW engine updated to {manifest.version}; restart to apply", "update"
            )
        else:
            rollback = " The previous engine was restored." if result.rolled_back else ""
            self._html_info(
                "GLOW update failed",
                f"# GLOW update failed\n\n`{result.message}`{rollback}",
            )
            self._set_status_quiet("GLOW update failed")
            self._announce("GLOW update failed." + rollback)
            self._record_notification(f"GLOW update failed: {result.message}", "update")

    def _html_info(self, title: str, markdown_text: str) -> None:
        """Show a plain-text informational message with an OK button."""
        wx = self._wx
        dialog = wx.MessageDialog(
            self.frame, _strip_md_to_plain(markdown_text), title, wx.OK | wx.ICON_INFORMATION
        )
        try:
            self._show_modal_dialog(dialog, title)
        finally:
            dialog.Destroy()

    def _present_release_notes(
        self,
        *,
        title: str,
        header: str,
        notes_plain: str,
        buttons: list[tuple[str, int]],
        affirmative_id: int,
        escape_id: int,
    ) -> int:
        """Show release notes in a read-only multi-line edit (help-text style).

        ``header`` is a short label above the notes; ``notes_plain`` is the
        flattened changelog section shown in a scrollable, screen-reader-friendly
        ``TextCtrl``. Returns the id of the button the user pressed.
        """
        wx = self._wx
        dialog = wx.Dialog(
            self.frame, title=title, style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
        )
        dialog.SetSize((560, 520))
        sizer = wx.BoxSizer(wx.VERTICAL)
        if header:
            heading = wx.StaticText(dialog, label=header)
            sizer.Add(heading, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 12)
        notes_label = wx.StaticText(dialog, label="Release &notes:")
        sizer.Add(notes_label, 0, wx.LEFT | wx.RIGHT | wx.TOP, 12)
        body = wx.TextCtrl(
            dialog,
            value=notes_plain,
            style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_AUTO_URL | wx.TE_RICH2,
            name="release_notes",
        )
        body.SetName("Release notes")
        sizer.Add(body, 1, wx.EXPAND | wx.ALL, 12)
        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        btn_sizer.AddStretchSpacer()
        for label, return_id in buttons:
            button = wx.Button(dialog, return_id, label=label)
            button.Bind(wx.EVT_BUTTON, lambda _e, r=return_id: dialog.EndModal(r))
            if return_id == affirmative_id:
                button.SetDefault()
            btn_sizer.Add(button, 0, wx.RIGHT, 6)
        sizer.Add(btn_sizer, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 12)
        dialog.SetSizer(sizer)
        apply_modal_ids(dialog, affirmative_id=affirmative_id, escape_id=escape_id)
        # Land focus on the notes so screen-reader users enter on the text.
        wx.CallAfter(body.SetFocus)
        try:
            return self._show_modal_dialog(dialog, title)
        finally:
            dialog.Destroy()

    def _show_update_available_dialog(
        self, current_version: str, release: GitHubRelease, *, self_heal: bool = False
    ) -> str:
        """Present an available update. Returns one of ``"download"``,
        ``"skip"`` (don't offer this version again) or ``"later"``.

        When ``self_heal`` is set, the offered release is the *same* version the
        user already runs, reinstalled to restore the bundled bug-report token
        (#919). The dialog says so explicitly so "update to the version you
        already have" is not confusing.
        """
        wx = self._wx
        self._announce(f"Update available: {release.version}")
        channel = "Beta / prerelease" if release.prerelease else "Stable"
        raw = (release.notes or "").strip()
        notes = (
            _strip_md_to_plain(raw) if raw else "(No release notes were provided for this version.)"
        )
        published = f"Published: {release.published_at}\n" if release.published_at else ""
        if self_heal:
            header = (
                f"Restore the bug-report token: {release.version}\n"
                f"Channel: {channel}\n"
                f"{published}"
                f"Current version: {current_version}"
            )
            notes = (
                "Your build is missing its bundled bug-report token, so the in-app "
                "Report a Bug dialog can't file issues. Installing this build (the "
                "same version) restores the token.\n\n" + notes
            )
        else:
            header = (
                f"Update available: {release.version}\n"
                f"Channel: {channel}\n"
                f"{published}"
                f"Current version: {current_version}"
            )
        result = self._present_release_notes(
            title="Check for Updates",
            header=header,
            notes_plain=notes,
            buttons=[
                ("Later", wx.ID_CANCEL),
                ("Skip this version", wx.ID_IGNORE),
                ("Download update", wx.ID_OK),
            ],
            affirmative_id=wx.ID_OK,
            escape_id=wx.ID_CANCEL,
        )
        if result == wx.ID_OK:
            return "download"
        if result == wx.ID_IGNORE:
            return "skip"
        return "later"

    def show_whats_new(self) -> None:
        """Show the running build's abbreviated release notes on demand.

        Lets users see the same notes the Check-for-Updates dialog shows, even
        between updates, so the format is familiar when an update lands.
        """
        from quill import build_info
        from quill.core.release_notes import current_release_notes

        wx = self._wx
        version = build_info.get_short_version()
        notes = current_release_notes()
        if not notes:
            notes = (
                "Release notes are not bundled with this build.\n\n"
                "See the changelog on the project site for what's new."
            )
        self._present_release_notes(
            title="What's New",
            header=f"What's new in QUILL {version}",
            notes_plain=notes,
            buttons=[("Close", wx.ID_CLOSE)],
            affirmative_id=wx.ID_CLOSE,
            escape_id=wx.ID_CLOSE,
        )
        self._set_status("Showed What's New")

    def _skip_update_version(self, version: str) -> None:
        """Remember a version the user chose to skip so we stop offering it."""
        self.settings.skipped_update_version = version
        save_settings(self.settings)
        self._set_status(f"Skipping update {version}")
        self._record_notification(f"Update {version} skipped", "update")
        self._announce(f"Update {version} skipped")

    def _offer_beta_switch(
        self, current_version: str, stable_release: GitHubRelease | None
    ) -> None:
        wx = self._wx
        stable_line = (
            f"the latest stable release is {stable_release.version}"
            if stable_release is not None
            else "no stable release is published yet"
        )
        plain = (
            f"You're on the stable channel (current version {current_version}; "
            f"{stable_line}).\n\n"
            "Want earlier features sooner? The beta channel delivers prerelease "
            "builds as soon as they're published."
        )
        dialog = wx.MessageDialog(
            self.frame, plain, "Check for Updates", wx.YES_NO | wx.NO_DEFAULT | wx.ICON_INFORMATION
        )
        if hasattr(dialog, "SetYesNoLabels"):
            dialog.SetYesNoLabels("Switch to beta...", "Stay on stable")
        try:
            result = self._show_modal_dialog(dialog, "Check for Updates")
        finally:
            dialog.Destroy()
        if result == wx.ID_YES and self._confirm_beta_channel():
            self.settings.beta_updates = True
            save_settings(self.settings)
            self._set_status_quiet("Switched to the beta update channel")
            self._announce("Beta updates enabled")
            # Surface the latest prerelease right away so the user can install it,
            # even if its version matches the current build (they opted into beta).
            self._offer_latest_beta(current_version)

    def _offer_latest_beta(self, current_version: str) -> None:
        from quill.core.updates import fetch_latest_release

        try:
            release = fetch_latest_release(include_prereleases=True)
        except (URLError, ValueError, OSError) as error:
            self._html_info(
                "Check for Updates",
                f"# Update check failed\n\nCould not check beta updates: {error}",
            )
            return
        if release is None:
            self._html_info(
                "Check for Updates",
                "# No beta build yet\n\nNo beta (prerelease) build is available yet.",
            )
            return
        action = self._show_update_available_dialog(current_version, release)
        if action == "download":
            self._download_update_release(release)
        elif action == "skip":
            self._skip_update_version(release.version)

    def _confirm_beta_channel(self, release: GitHubRelease | None = None) -> bool:
        """Consent gate the user must agree to before beta updates turn on."""
        wx = self._wx
        detected = (
            f"A beta build ({release.version}) is available.\n\n" if release is not None else ""
        )
        plain = (
            f"{detected}"
            "Beta updates are prerelease builds. They get new features and fixes "
            "first, but they may be unstable - expect rough edges, and occasional "
            "bugs that could affect your documents.\n\n"
            "- Beta builds are published as GitHub prereleases.\n"
            "- You can switch back to stable anytime in Settings.\n"
            "- Keep backups of important documents.\n\n"
            "Do you understand and want to receive beta updates?"
        )
        dialog = wx.MessageDialog(
            self.frame, plain, "Beta updates", wx.YES_NO | wx.NO_DEFAULT | wx.ICON_WARNING
        )
        if hasattr(dialog, "SetYesNoLabels"):
            dialog.SetYesNoLabels("I understand, enable beta", "Cancel")
        try:
            result = self._show_modal_dialog(dialog, "Beta updates")
        finally:
            dialog.Destroy()
        return result == wx.ID_YES

    def _download_update_release(self, release: GitHubRelease) -> None:
        """Auto-download the release asset to <app data>/updates, off-thread,
        with accessible progress reporting and a post-download install offer.

        If the release has no downloadable asset, open its page instead.
        """

        from quill.core.updates import download_release_asset

        url = release.download_url or ""
        if "/releases/download/" not in url:
            if url and webbrowser.open(url):
                self._set_status(f"Opened download page for {release.version}")
                self._record_notification(f"Opened update page for {release.version}", "update")
            else:
                self._set_status("No downloadable update asset found")
            return

        target_dir = app_data_dir() / "updates"
        target_dir.mkdir(parents=True, exist_ok=True)
        target = target_dir / (url.rsplit("/", 1)[-1] or f"quill-{release.version}")
        self._set_status_quiet(f"Downloading update {release.version}...")
        self._announce(f"Downloading update {release.version}")

        # Announce progress at coarse milestones so screen readers aren't flooded.
        last_milestone = {"value": -1}

        def report(done: int, total: int) -> None:
            if total <= 0:
                return
            percent = int(done * 100 / total)
            milestone = percent - (percent % 25)
            if milestone > last_milestone["value"] and milestone <= 100:
                last_milestone["value"] = milestone
                if milestone in (25, 50, 75):
                    self._wx.CallAfter(self._set_status, f"Downloading update… {milestone}%")
                    self._wx.CallAfter(self._announce, f"Update download {milestone} percent")

        def worker() -> None:
            try:
                download_release_asset(url, target, progress=report)
            except Exception as exc:  # noqa: BLE001
                self._wx.CallAfter(
                    self._record_notification, f"Update download failed: {exc}", "update"
                )
                self._wx.CallAfter(self._set_status, "Update download failed")
                return
            self._wx.CallAfter(
                self._record_notification,
                f"Update {release.version} downloaded to {target}",
                "update",
            )
            self._wx.CallAfter(self._set_status, f"Downloaded update {release.version}")
            self._wx.CallAfter(self._announce, f"Update {release.version} downloaded")
            self._wx.CallAfter(self._offer_post_download_actions, release, target)

        threading.Thread(  # GATE-40-OK: update asset download worker; bounded by size.
            target=worker, daemon=True
        ).start()

    def _offer_post_download_actions(self, release: GitHubRelease, target: Path) -> None:
        """After a successful download, let the user install/extract it now or
        reveal it in the folder. Installer launch is offered only for runnable
        (.exe/.msi) assets; extraction is offered only for a portable (.zip)
        asset -- previously a portable download only ever offered "Open
        folder"/"Close", leaving a portable user to find and extract the ZIP
        themselves with no in-app help at all.
        """
        from quill.ui.dialog_contract import apply_modal_ids

        wx = self._wx
        runnable = target.suffix.lower() in {".exe", ".msi"} and sys.platform.startswith("win")
        extractable = target.suffix.lower() == ".zip"
        if runnable:
            action_line = "Select 'Install now' to close Quill and run the installer, or "
        elif extractable:
            action_line = "Select 'Extract now' to unzip it into a ready-to-run folder, or "
        else:
            action_line = ""
        plain = (
            f"Update {release.version} downloaded.\n\n"
            f"Saved to: {target}\n\n"
            f"{action_line}Select 'Open folder' to find it."
        )
        dialog = wx.Dialog(
            self.frame, title="Update downloaded", style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
        )
        dialog.SetSize((500, 260))
        sizer = wx.BoxSizer(wx.VERTICAL)
        body = wx.TextCtrl(
            dialog,
            value=plain,
            style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_AUTO_URL | wx.TE_RICH2,
            name="update_body",
        )
        sizer.Add(body, 1, wx.EXPAND | wx.ALL, 12)
        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        btn_sizer.AddStretchSpacer()
        close_btn = wx.Button(dialog, wx.ID_CANCEL, label="Close")
        folder_btn = wx.Button(dialog, wx.ID_OPEN, label="Open folder")
        close_btn.Bind(wx.EVT_BUTTON, lambda _e: dialog.EndModal(wx.ID_CANCEL))
        folder_btn.Bind(wx.EVT_BUTTON, lambda _e: dialog.EndModal(wx.ID_OPEN))
        btn_sizer.Add(close_btn, 0, wx.RIGHT, 6)
        btn_sizer.Add(folder_btn, 0, wx.RIGHT, 6)
        if runnable:
            install_btn = wx.Button(dialog, wx.ID_OK, label="Install now...")
            install_btn.Bind(wx.EVT_BUTTON, lambda _e: dialog.EndModal(wx.ID_OK))
            install_btn.SetDefault()
            btn_sizer.Add(install_btn, 0)
        elif extractable:
            extract_btn = wx.Button(dialog, wx.ID_OK, label="Extract now")
            extract_btn.Bind(wx.EVT_BUTTON, lambda _e: dialog.EndModal(wx.ID_OK))
            extract_btn.SetDefault()
            btn_sizer.Add(extract_btn, 0)
        else:
            close_btn.SetDefault()
        sizer.Add(btn_sizer, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 12)
        dialog.SetSizer(sizer)
        affirmative = wx.ID_OK if (runnable or extractable) else wx.ID_OPEN
        apply_modal_ids(dialog, affirmative_id=affirmative, escape_id=wx.ID_CANCEL)
        wx.CallAfter(body.SetFocus)
        try:
            result = self._show_modal_dialog(dialog, "Update downloaded")
        finally:
            dialog.Destroy()
        if result == wx.ID_OPEN:
            self._reveal_in_folder(target)
        elif result == wx.ID_OK and runnable:
            self._launch_installer(target)
        elif result == wx.ID_OK and extractable:
            self._extract_and_reveal_portable_update(release, target)

    def _extract_and_reveal_portable_update(self, release: GitHubRelease, target: Path) -> None:
        """Extract a downloaded portable-update ZIP and reveal the result.

        Extracts to a ready-to-run sibling folder (``<target's dir>/Quill-Portable-<version>``)
        rather than leaving the user to find and unzip the archive themselves.
        Does not attempt to replace the currently-running portable bundle in
        place (its own files may be locked while Quill is running) -- the
        user still copies their ``data`` folder over and swaps folders
        manually, but no longer needs to know how to extract a ZIP first.
        """
        from quill.core.updates import extract_portable_update

        dest = target.parent / f"Quill-Portable-{release.version}"
        self._set_status_quiet(f"Extracting update {release.version}...")
        try:
            extract_portable_update(target, dest)
        except Exception as exc:  # noqa: BLE001
            self._record_notification(f"Update extraction failed: {exc}", "update")
            self._set_status("Update extraction failed")
            return
        self._record_notification(f"Update {release.version} extracted to {dest}", "update")
        self._set_status_quiet(f"Extracted update {release.version}")
        self._announce(f"Update {release.version} extracted, ready to use")
        self._reveal_in_folder(dest)

    def _reveal_in_folder(self, target: Path) -> None:
        """Reveal the downloaded file in the OS file manager."""
        try:
            if sys.platform.startswith("win"):
                import subprocess

                subprocess.Popen(["explorer", "/select,", str(target)])  # noqa: S603, S607
            elif sys.platform == "darwin":
                import subprocess

                subprocess.Popen(["open", "-R", str(target)])  # noqa: S603, S607
            else:
                webbrowser.open(target.parent.as_uri())
            self._set_status(f"Revealed {target.name}")
        except Exception as exc:  # noqa: BLE001
            self._record_notification(f"Could not open folder: {exc}", "update")
            self._set_status("Could not open download folder")

    def _launch_installer(self, target: Path) -> None:
        """Close Quill and launch the downloaded installer (Windows)."""
        if not self._can_close_all_documents():
            self._set_status("Install cancelled")
            self._record_notification("Update install cancelled before closing documents", "update")
            return
        try:
            self._open_with_default_app(target)
        except Exception as exc:  # noqa: BLE001
            self._record_notification(f"Could not launch installer: {exc}", "update")
            self._set_status("Could not launch installer")
            return
        self._record_notification(f"Launching installer {target.name}", "update")
        self._set_status("Closing Quill for installation")
        self.exit_app()

    def _open_update_download_flow(self, manifest: UpdateManifest) -> None:
        wx = self._wx
        close_now = self._show_message_box(
            (
                f"Quill installer update {manifest.version} requires the editor to close.\n\n"
                "Open the download page and close Quill now?"
            ),
            "Install Update",
            wx.ICON_INFORMATION | wx.YES_NO | wx.NO_DEFAULT,
        )
        if close_now != wx.YES:
            opened = webbrowser.open(manifest.download_url)
            if opened:
                self._set_status(f"Opened download page for {manifest.version}")
                self._record_notification(
                    (
                        f"Opened update download for {manifest.version}. "
                        "Close Quill before running installer."
                    ),
                    "update",
                )
                return
            self._set_status("Could not open update download page")
            self._record_notification("Could not open update download page", "update")
            return
        if not self._can_close_all_documents():
            self._set_status("Update cancelled")
            self._record_notification(
                f"Update {manifest.version} cancelled before closing documents",
                "update",
            )
            return
        opened = webbrowser.open(manifest.download_url)
        if not opened:
            self._set_status("Could not open update download page")
            self._record_notification("Could not open update download page", "update")
            return
        self._record_notification(f"Opened update download for {manifest.version}", "update")
        self._set_status(f"Closing Quill for update {manifest.version}")
        self.exit_app()
