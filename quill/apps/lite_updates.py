"""QuillLite checks for its own updates, like every other app in the family.

It shipped without this. Eight QuillVille apps answer Ctrl+Alt+U with "here is
what is new, do you want it", and the ninth -- the one most likely to be
somebody's only Quill product, installed because they wanted Notepad and got a
screen-reader-first editor instead -- had no way to learn that a new version
existed at all. A user who never opens GitHub would have stayed on 1.0.0
forever, and would have had no way to know that was happening.

Nothing here is a second implementation. The offer dialog is
:mod:`quill.ui.update_notice`, shared with QUILL and the companion apps; the
download, the spoken milestones and the Install-and-restart dialog are
:mod:`quill.ui.update_download`, likewise. What is QuillLite's own is the small
amount that genuinely differs:

* it has no ``TaskManager``, so the background work runs on
  ``update_download.thread_submit`` -- one daemon thread for one download;
* the silent launch check is throttled to once a day through QuillLite's own
  settings file, because QuillLite must never adopt QUILL's;
* the dialog's parent is the *document window*, not a top-level app frame,
  since QuillLite is MDI and the active document is where the user is;
* and the asset is chosen **without** the four-edition machinery. QuillLite
  publishes two downloads, an installer and a portable zip, so the question is
  "portable, or not" and nothing else. The four-way chooser exists because the
  other apps ship four non-interchangeable assets; pointed at two it can only
  add a way to be wrong, and it nearly did -- an installed app resolves
  ``QUILL_APP_ROOT`` to the shared runtime's folder, where ``detect()`` finds
  no marker and answers "companion". QuillLite came out right anyway, because
  it publishes no Companion zip and fell through to the installer. Right for
  the wrong reason is not something to leave holding a download link.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import wx

from quill.core.lite import APP_NAME, APP_VERSION, RELEASE_ASSET_PREFIX, RELEASE_REPO
from quill.ui.dialog_contract import show_message_box, show_modal_dialog

__all__ = [
    "DocumentUpdatesMixin",
    "check_at_launch",
    "check_for_updates",
    "update_check_due",
]

#: Hours between silent launch checks. A manual Ctrl+Alt+U always runs.
CHECK_INTERVAL_HOURS = 24


def update_check_due(last_check: str, *, interval_hours: int = CHECK_INTERVAL_HOURS) -> bool:
    """True when enough time has passed since the last silent launch check.

    Unparseable or missing means due: a settings file somebody has hand-edited
    into nonsense should not be able to switch update checking off silently.
    """
    last = (last_check or "").strip()
    if not last:
        return True
    try:
        previous = datetime.fromisoformat(last)
    except ValueError:
        return True
    if previous.tzinfo is None:
        previous = previous.replace(tzinfo=UTC)
    return datetime.now(UTC) - previous >= timedelta(hours=interval_hours)


def _running_portable_build() -> bool:
    """True when this is the extracted portable bundle, not an install.

    Asked of the *app's* folder rather than of ``sys.executable`` -- on the
    shared runtime that is QuillVilleRuntime.exe in %LOCALAPPDATA%, which has
    no uninstaller beside it, so every installed user would otherwise be
    offered the portable .zip on every update (#1100).
    """
    from quill.core.install_edition import PORTABLE, detect

    return detect() == PORTABLE


def check_for_updates(window: Any, *, silent_no_update: bool = False) -> None:
    """Check QuillLite's own releases and offer what is newer, with its notes.

    *window* is the document window the dialog belongs to. ``silent_no_update``
    is the launch check: "checking", "up to date" and a failed check all stay
    quiet, because a launch is not the place to announce that nothing happened.
    A genuine available update still shows the same dialog either way -- there
    is no notification centre in QuillLite to defer it to.
    """
    from quill.core.updates import fetch_app_releases, is_newer_version

    announce = getattr(window, "_announce", lambda _msg: None)
    api_url = f"https://api.github.com/repos/{RELEASE_REPO}/releases"
    prefer_portable = _running_portable_build()
    if not silent_no_update:
        announce("Checking for updates")

    def _fetch(**_kw: object) -> object:
        return fetch_app_releases(
            RELEASE_ASSET_PREFIX,
            api_url,
            prefer_portable=prefer_portable,
            # Two assets, one question. See this module's docstring.
            match_edition=False,
        )

    def _show(releases: Any) -> None:
        if window is None:  # nothing to parent the dialog to
            return
        stable = [r for r in releases if not r.prerelease]
        newest = stable[0] if stable else None
        if newest is None or not is_newer_version(APP_VERSION, newest.version):
            if not silent_no_update:
                # A manual check deserves a real dialog: an announcement alone
                # is easy to miss, and "I pressed the key and nothing happened"
                # is indistinguishable from a key that is not bound.
                show_message_box(
                    f"You are up to date ({APP_VERSION}).",
                    "Check for Updates",
                    wx.ICON_INFORMATION | wx.OK,
                    window,
                )
            return
        from quill.ui.update_notice import show_update_available

        choice = show_update_available(
            window,
            app_name=APP_NAME,
            current_version=APP_VERSION,
            release=newest,
            show_modal_dialog=show_modal_dialog,
            announce=announce,
        )
        if choice == "update":
            _download(window, newest, announce)

    def _report(_name: str, releases: object) -> None:
        wx.CallAfter(_show, releases)

    def _failed(_name: str, error: BaseException) -> None:
        if silent_no_update:
            return
        wx.CallAfter(
            show_message_box,
            f"Could not check for updates: {error}",
            "Check for Updates",
            wx.ICON_ERROR | wx.OK,
            window,
        )

    from quill.ui.update_download import thread_submit

    thread_submit("app-update-check", _fetch, on_success=_report, on_failure=_failed)


def _download(window: Any, release: Any, announce: Any) -> None:
    from quill.core.lite.paths import data_dir
    from quill.ui.update_download import download_and_offer_install, thread_submit

    download_and_offer_install(
        window,
        release=release,
        # QuillLite's own folder (%LOCALAPPDATA%\QuillLite), never QUILL's:
        # a user who removes QuillLite must not leave a download behind in
        # another product's data directory.
        target_dir=data_dir() / "updates",
        portable=_running_portable_build(),
        announce=announce,
        show_message_box=lambda message, caption, style: show_message_box(
            message, caption, style, window
        ),
        show_modal_dialog=show_modal_dialog,
        submit=thread_submit,
        # The MDI shell, not the document the dialog is parented to: closing
        # one document would leave the app running while the installer waited
        # for it to exit.
        close_app=lambda: wx.GetTopLevelParent(window).Close(),
    )


class DocumentUpdatesMixin:
    """``cmd_check_updates``, mixed into the QuillLite document window."""

    def cmd_check_updates(self) -> None:
        """Help > Check for Updates... -- the family key, Ctrl+Alt+U."""
        self.app.settings.last_update_check = datetime.now(UTC).isoformat()
        self.app.save_settings()
        check_for_updates(self)


def check_at_launch(app: Any) -> None:
    """The quiet once-a-day check QuillLite runs when it opens.

    Silent in every direction but one: nothing while it runs, nothing when
    there is nothing, and nothing when the network is down -- a launch is not
    the place to report that. Only a genuine newer version speaks, and even
    then it only offers.

    Deferred onto the event loop so a slow or blocked DNS lookup can never sit
    between the double-click and the first window, and parented to the active
    document because that is where the user is.
    """
    if not getattr(app.settings, "check_updates_on_launch", True):
        return
    if not update_check_due(str(getattr(app.settings, "last_update_check", "") or "")):
        return
    app.settings.last_update_check = datetime.now(UTC).isoformat()
    app.save_settings()

    def _run() -> None:
        shell = getattr(app, "shell", None)
        window = shell.GetActiveChild() if shell is not None else None
        check_for_updates(window or shell, silent_no_update=True)

    wx.CallAfter(_run)
