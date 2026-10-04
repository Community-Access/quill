"""Update checking and delivery for MainFrame (CQ-1 decomposition).

``UpdatesMixin`` owns the QUILL self-update flow -- the startup/manual GitHub
release check (filtered by the release channel, ``quill.core.updater``),
release-notes presentation, skip-version bookkeeping, the consented download of installer or
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
        if current_version == build_info.get_short_version():
            # A Dev build carries its build stamp, so two Dev builds differ.
            current_version = build_info.feed_version()

        self.settings.last_update_check = datetime.now(UTC).isoformat()
        try:
            save_settings(self.settings)
        except Exception:  # noqa: BLE001
            pass

        if not silent_no_update:
            self._set_status_quiet("Checking for updates...")
            self._announce("Checking for updates")

        # The release channel (Help > Release Channel) decides; QUILL's old "Get
        # beta updates" box counts only until a channel has been stored.
        from quill.core.updater.channels import includes_prereleases, load_channels

        channels = load_channels()
        beta = (
            includes_prereleases(channels.state("quill"))
            if channels.has("quill")
            else bool(getattr(self.settings, "beta_updates", False))
        )
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
                # The signed v2 list decides when one is published; until then
                # the GitHub path, exactly as before (release channels, Phase 2).
                from quill.core.updater.feed_fetch import (
                    FeedCheckFailed,
                    fetch_feed,
                    offers_from_feed,
                )

                listed = fetch_feed("quill")
                if listed.status != "missing":
                    if not listed.usable or listed.feed is None:
                        raise FeedCheckFailed(listed.reason)
                    releases = list(offers_from_feed(listed.feed, portable=portable))
                elif (
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
        from quill.core.updates import (
            is_newer_version,
            running_portable,
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
        # The v1 manifest has no channel, so a pre-release in it is offered only
        # to somebody on Beta or Dev (release channels, Phase 0).
        from quill.core.versioning import ReleaseVersion

        manifest_version = ReleaseVersion.try_parse(manifest.version) if manifest else None
        manifest_ok = beta or (manifest_version is not None and not manifest_version.is_prerelease)
        # A client reading the v2 list ignores the v1 manifest for offers; it
        # still applies the manifest's advisories above (plan 9.5).
        if releases and all(hasattr(r, "channels") for r in releases):
            manifest_ok = False
        if (
            manifest is not None
            and manifest_ok
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
        # The release channel decides what may be offered (Stable never sees a
        # pre-release). A build that finds itself a pre-release with no channel
        # stored is set to its own channel once, and says so -- this replaced a
        # silent auto-enrol (release channels, plan 2.1).
        from quill.core.updater.check import evaluate, up_to_date_text

        result = evaluate(
            "quill",
            current_version,
            releases,
            legacy_beta=bool(getattr(self.settings, "beta_updates", False)),
        )
        for notice in result.notices:
            self._record_notification(notice, "update")
            self._announce(notice)
        self._mirror_release_channel(result.state)
        target = result.target
        newer = target is not None and is_newer_version(current_version, target.version)
        # #919's same-version "self-heal" offer is gone (2026-09-26): it existed
        # to restore a bundled GitHub token, and no build carries one any more --
        # support messages and crash reports go by email.
        if target is not None and newer:
            if silent_no_update and target.version == getattr(
                self.settings, "skipped_update_version", ""
            ):
                self._record_notification(
                    f"Update {target.version} available (skipped by you)", "update"
                )
                return
            if silent_no_update:
                if self._hold_background_update(target, result.state):
                    return
                self._record_notification(f"Update {target.version} found; downloading", "update")
                self._download_update_release(target)
                return
            action = self._show_update_available_dialog(current_version, target)
            if action == "download":
                self._download_update_release(target)
            elif action == "skip":
                self._skip_update_version(target.version)
            else:
                self._set_status("Update deferred")
                self._record_notification(f"Update {target.version} deferred", "update")
            return

        # Genuinely up to date. No offer to "switch to beta" any more: an
        # up-to-date answer should not try to sell a riskier channel.
        if silent_no_update:
            self._record_notification("Update check found no newer version", "update")
            return
        self._set_status_quiet("No update available")
        self._announce("Quill is up to date")
        self._record_notification("Update check found no newer version", "update")
        self._html_info(
            "Check for Updates",
            "# You're up to date\n\n" + up_to_date_text(current_version, result.state),
        )

    def _hold_background_update(self, target: object, state: object) -> bool:
        """Beta and Dev: the automatic download waits on a metered connection, in
        Quiet Hours, or while Quill Radio records; Stable is unchanged."""
        from quill.core.updater import history
        from quill.core.updater.background import background_gate, read_conditions

        gate = background_gate(state, read_conditions())  # type: ignore[arg-type]
        if not gate.reason:
            return False
        version = str(getattr(target, "version", ""))
        history.record("quill", "held_back", to_version=version, detail=gate.reason)
        self._record_notification(f"Update {version} found. {gate.reason}", "update")
        return True

    def _mirror_release_channel(self, state: object) -> None:
        """Keep the old ``beta_updates`` flag in step with the channel, for one
        release cycle, so a QUILL taken back to 0.9.x still behaves (plan 9.4)."""
        wanted = getattr(state, "channel", "stable") != "stable"
        if bool(getattr(self.settings, "beta_updates", False)) != wanted:
            self.settings.beta_updates = wanted
            try:
                save_settings(self.settings)
            except Exception:  # noqa: BLE001 - a mirror is a courtesy
                pass

    # -- release channels (Help > Release Channel..., plan 7) ---------------

    def _install_release_channel_item(self, help_menu: object) -> None:
        """Help > Release Channel..., beside Check for Updates.

        Registered here rather than in the command table so the whole feature
        is one mixin: the command, its menu row and its binding.
        """
        from quill.core.i18n import _

        wx = self._wx
        self.commands.try_register(
            "help.release_channel",
            "Release Channel...",
            self.open_release_channel,
            self._binding_for("help.release_channel"),
        )
        item_id = getattr(self, "_id_release_channel", None) or wx.NewIdRef()
        self._id_release_channel = item_id
        label = self._menu_label(_("Release &Channel..."), "help.release_channel")
        help_menu.Append(item_id, label)  # type: ignore[attr-defined]
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.open_release_channel(), id=item_id)
        # Built once at start-up: once the window is up, tell the update helper
        # this version started (release channels, Phase 4). Once per session.
        if not getattr(self, "_update_start_confirmed", False):
            self._update_start_confirmed = True
            call_later = getattr(wx, "CallLater", None)
            if callable(call_later):
                call_later(1500, self._confirm_update_started)

    def _confirm_update_started(self) -> None:
        from quill import build_info
        from quill.core.paths import app_data_dir
        from quill.ui.updates.started import confirm_after_start

        confirm_after_start(
            app_key="quill",
            app_name="QUILL",
            version=build_info.feed_version(),
            updates_dir=app_data_dir() / "updates",
            announce=self._announce,
        )

    def _add_release_channel_row(self, panel: object, sizer: object) -> object:
        """Preferences: "Release channel: Stable" and a button that changes it.

        No access key on the button: the Preferences pages are dense, and a
        duplicate letter is worse than none (GATE-14). Tab reaches it.
        """
        from quill.core.updater.channels import shown_channel, state_for

        wx = self._wx
        row = wx.BoxSizer(wx.HORIZONTAL)
        status = wx.StaticText(panel, label=f"Release channel: {shown_channel(state_for('quill'))}")
        button = wx.Button(panel, label="Change release channel...")
        button.SetHelpText(
            "Choose Stable, Beta or Dev for QUILL. Opens the Release Channel window, "
            "the same one as Help, Release Channel."
        )

        def _change(_event: object) -> None:
            self.open_release_channel()
            status.SetLabel(f"Release channel: {shown_channel(state_for('quill'))}")

        button.Bind(wx.EVT_BUTTON, _change)
        row.Add(status, 1, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 8)
        row.Add(button, 0)
        sizer.Add(row, 0, wx.EXPAND | wx.ALL, 6)  # type: ignore[attr-defined]
        return button

    def _release_channel_is_prerelease(self) -> bool:
        from quill.core.updater.channels import state_for

        return state_for("quill").channel != "stable"

    def open_release_channel(self) -> None:
        """Choose Stable, Beta or Dev for QUILL (the shared Release Channel window)."""
        from quill.ui.updates.flow import open_release_channel

        current = build_info.resolve_running_version(
            override=getattr(getattr(self, "_updates", None), "current_version", "")
        )
        open_release_channel(
            self.frame,
            app_key="quill",
            installed_version=current,
            show_modal=self._show_modal_dialog,
            announce=self._announce,
            on_changed=self._mirror_release_channel,
            check_now=lambda: self.check_for_updates(),
            install_release=self._download_update_release,
        )

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

        The dialog itself lives in :mod:`quill.ui.update_notice`, which is where
        the eight companion apps and QUILL Lite get exactly the same one. This
        stays as the name the rest of the mixin calls.
        """
        from quill.ui.update_notice import present_release_notes

        return present_release_notes(
            self.frame,
            title=title,
            header=header,
            notes_plain=notes_plain,
            buttons=buttons,
            affirmative_id=affirmative_id,
            escape_id=escape_id,
            show_modal_dialog=self._show_modal_dialog,
            wx_module=self._wx,
        )

    def _show_update_available_dialog(self, current_version: str, release: GitHubRelease) -> str:
        """Present an available update. Returns one of ``"download"``,
        ``"skip"`` (don't offer this version again) or ``"later"``.
        """
        from quill.ui.update_notice import show_update_available, update_header

        header = update_header(
            "QUILL",
            current_version,
            release.version,
            prerelease=release.prerelease,
            published_at=release.published_at,
        )
        choice = show_update_available(
            self.frame,
            app_name="QUILL",
            current_version=current_version,
            release=release,
            show_modal_dialog=self._show_modal_dialog,
            announce=self._announce,
            # QUILL is the only app with a settings field to remember a skipped
            # version in, so it is the only one that offers the third button.
            allow_skip=True,
            header=header,
            wx_module=self._wx,
        )
        if choice == "update":
            return "download"
        if choice == "skip":
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
                download_release_asset(
                    url,
                    target,
                    progress=report,
                    expected_sha256=getattr(release, "download_digest", ""),
                )
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
        # On Windows, any real asset can be applied and relaunched in one click
        # (installed => silent installer; portable => copy-over helper). Non-Windows
        # keeps the older reveal/extract behavior.
        applyable = sys.platform.startswith("win") and target.suffix.lower() in {
            ".exe",
            ".msi",
            ".zip",
        }
        if applyable:
            action_line = (
                "Select 'Install and restart now' to update and relaunch "
                "automatically -- your settings and data are kept -- or "
            )
        elif runnable:
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
        if applyable:
            apply_btn = wx.Button(dialog, wx.ID_OK, label="Install and restart now")
            apply_btn.Bind(wx.EVT_BUTTON, lambda _e: dialog.EndModal(wx.ID_OK))
            apply_btn.SetDefault()
            btn_sizer.Add(apply_btn, 0)
        elif runnable:
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
        affirmative = wx.ID_OK if (applyable or runnable or extractable) else wx.ID_OPEN
        apply_modal_ids(dialog, affirmative_id=affirmative, escape_id=wx.ID_CANCEL)
        wx.CallAfter(body.SetFocus)
        try:
            result = self._show_modal_dialog(dialog, "Update downloaded")
        finally:
            dialog.Destroy()
        if result == wx.ID_OPEN:
            self._reveal_in_folder(target)
        elif result == wx.ID_OK and applyable:
            self._apply_update_and_restart(release, target)
        elif result == wx.ID_OK and runnable:
            self._launch_installer(target)
        elif result == wx.ID_OK and extractable:
            self._extract_and_reveal_portable_update(release, target)

    def _apply_update_and_restart(self, release: object, target: Path) -> None:
        """One-click apply + relaunch on Windows; leaves Quill open on failure."""
        from quill.core.paths import app_data_dir
        from quill.core.updates import running_portable
        from quill.ui.update_apply import apply_update_and_restart

        if apply_update_and_restart(
            target=target,
            portable=running_portable(),
            version=str(getattr(release, "version", "")),
            app_data_dir=app_data_dir(),
            announce=self._announce,
            show_error=lambda msg: self._show_message_box(
                msg, "Update", self._wx.ICON_ERROR | self._wx.OK
            ),
        ):
            self.frame.Close()

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
