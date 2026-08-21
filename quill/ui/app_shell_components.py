"""The on-demand component downloads a standalone app can offer.

Split out of :mod:`quill.ui.app_shell` (2026-08-21) when the mpv downloader
joined the ffmpeg one and the shell went over its GATE-11 budget. They belong
together anyway: one concern -- a media tool this installation does not have,
fetched on an explicit action -- and two methods that are deliberately the same
shape, so a listener who has met one has met both.

Both are announced-milestone, no-dialog-to-babysit: a modal progress box at
launch fights a screen reader for focus the app has not settled yet, and
neither of these is a decision anybody has to make before continuing.
"""

from __future__ import annotations

import wx


class ComponentDownloadsMixin:
    """Help > Get FFmpeg... and Help > Get mpv Playback Engine...

    Mixed into :class:`quill.ui.app_shell.AppShellFrame`, so every standalone
    app that uses the shell gets both and the call sites keep their names.
    Requires the host's ``_safe_mode``, ``_announce``, ``_show_message_box`` and
    ``_task_manager``.
    """

    # -- ffmpeg safety net (Help > Get FFmpeg...) --------------------------------

    def download_ffmpeg_component(self) -> None:
        """Recovery path for a missing ffmpeg: the installer and portable zip
        both bundle it, but if it ever goes missing this fetches QUILL's
        verified official build into the shared %APPDATA%\\Quill\\tools\\ffmpeg
        that every app searches. Announced milestones, no dialog to babysit."""
        from quill.core.speech.ffmpeg import ffmpeg_available
        from quill.core.speech.ffmpeg_install import (
            FFmpegInstallError,
            ffmpeg_install_supported,
            install_ffmpeg,
        )

        if self._safe_mode:
            self._announce("Downloading components is disabled in Safe Mode.")
            return
        if ffmpeg_available():
            self._announce("FFmpeg is already installed and working.")
            return
        if not ffmpeg_install_supported():
            self._announce("Automatic FFmpeg download is Windows-only.")
            return
        self._announce("Downloading FFmpeg (about 90 megabytes)...")
        last_milestone = {"value": -1}

        def _progress(fraction: float, _message: str) -> None:
            percent = int(max(0.0, min(1.0, fraction)) * 100)
            milestone = percent - (percent % 25)
            if milestone > last_milestone["value"] and milestone in (25, 50, 75):
                last_milestone["value"] = milestone
                wx.CallAfter(self._announce, f"FFmpeg download {milestone} percent")

        def _install(**_kw: object) -> object:
            # QuillTaskManager always passes cancellation_token/operation_id/
            # progress_callback; absorb them (same idiom as MainFrame's tasks).
            return install_ffmpeg(_progress)

        def _done(_name: str, _result: object) -> None:
            wx.CallAfter(self._announce, "FFmpeg is installed. Recording is ready to use.")

        def _failed(_name: str, error: BaseException) -> None:
            message = (
                str(error)
                if isinstance(error, FFmpegInstallError)
                else f"FFmpeg could not be downloaded: {error}"
            )
            wx.CallAfter(self._show_message_box, message, "Get FFmpeg", wx.ICON_ERROR | wx.OK)

        self._task_manager.submit(
            "app-ffmpeg-install", _install, on_success=_done, on_failure=_failed
        )

    # -- mpv safety net (Help > Get mpv Playback Engine...) ----------------------

    def download_mpv_component(self) -> None:
        """Fetch libmpv for an installation that has none.

        The twin of :meth:`download_ffmpeg_component`, and it exists for a
        listener the ffmpeg one never had to think about. The full installer and
        the portable zip bundle libmpv, but the thin ``-Lite`` installer
        downloads the *base* shared runtime, which carries no media tools at
        all -- so a Lite listener had a Radio permanently on the Windows Media
        backend and the app's own advice was to reinstall, which could not help.
        The pack has been SHA-pinned on QUILL's ``assets-v1`` release all along
        (the build fetches it from there); this is the route from the running
        app to the same verified zip.

        Announced milestones, no dialog to babysit -- same shape as ffmpeg.
        """
        from quill.core.mpv_install import (
            APPROXIMATE_SIZE_MB,
            MpvInstallError,
            install_mpv,
            mpv_install_supported,
        )
        from quill.ui.audio.mpv_engine import find_libmpv

        if self._safe_mode:
            self._announce("Downloading components is disabled in Safe Mode.")
            return
        if find_libmpv() is not None:
            self._announce("The mpv playback engine is already installed and working.")
            return
        if not mpv_install_supported():
            self._announce("Automatic mpv download is Windows-only.")
            return
        self._announce(
            f"Downloading the mpv playback engine (about {APPROXIMATE_SIZE_MB} megabytes)..."
        )
        last_milestone = {"value": -1}

        def _progress(fraction: float, _message: str) -> None:
            percent = int(max(0.0, min(1.0, fraction)) * 100)
            milestone = percent - (percent % 25)
            if milestone > last_milestone["value"] and milestone in (25, 50, 75):
                last_milestone["value"] = milestone
                wx.CallAfter(self._announce, f"mpv download {milestone} percent")

        def _install(**_kw: object) -> object:
            return install_mpv(_progress)

        def _done(_name: str, _result: object) -> None:
            # Deliberately says a restart is needed. find_libmpv() picks the DLL
            # up immediately, but the engine was already CHOSEN at launch --
            # engine_selection ran when libmpv was absent and built the wx.media
            # backend -- so the station playing right now does not change, and a
            # "ready to use" that is contradicted by the next station is worse
            # than asking for a restart.
            wx.CallAfter(
                self._announce,
                "The mpv playback engine is installed. Restart to start using it.",
            )

        def _failed(_name: str, error: BaseException) -> None:
            message = (
                str(error)
                if isinstance(error, MpvInstallError)
                else f"The mpv engine could not be downloaded: {error}"
            )
            wx.CallAfter(self._show_message_box, message, "Get mpv", wx.ICON_ERROR | wx.OK)

        self._task_manager.submit("app-mpv-install", _install, on_success=_done, on_failure=_failed)
