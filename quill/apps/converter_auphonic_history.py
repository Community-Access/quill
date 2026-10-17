"""Quill Converter's Auphonic Production History and Auphonic Account commands.

Post-MVP (``docs/planning/QUILL-Converter-Auphonic-Integration-PRD.md``,
section 14), the base class of :class:`~quill.apps.converter_auphonic.ConverterAuphonicMixin`
so the Converter window's own module does not grow:

* **Convert > Auphonic Production History** (Ctrl+Alt+H) lists every
  production sent, from a file on this computer. Refresh from Auphonic reads
  the account's recent productions; Download Again runs as an ordinary
  Converter job (progress, Stop with Ctrl+Enter, the Conversion Report);
  Open Folder and Remove from List are local.
* **Convert > Auphonic Account** (Ctrl+Alt+Shift+A) shows whether a token is
  stored and, on Check Account, the account, credits and plan; Sign In stores
  a token Auphonic accepted, Sign Out removes it.

Opening either window contacts nobody; every request is a button press, and
each goes through the shared client's one reviewed egress site. The token is
the family's one credential (``quill:publish:auphonic``), read and written by
:func:`quill.apps.converter_auphonic.load_token` and ``save_token``.
Unavailable in Safe Mode, like Process with Auphonic.
"""

from __future__ import annotations

import logging
import os
import threading
from pathlib import Path
from typing import Any

import wx

_SAFE_MODE = "Processing with Auphonic is unavailable in Safe Mode."
_TITLE = "Auphonic Production History"
_log = logging.getLogger(__name__)


class ConverterAuphonicHistoryMixin:
    """Production History and the account view. Mixed into the Converter window."""

    # -- Production History ----------------------------------------------------------

    def show_auphonic_history(self) -> None:
        """Convert > Auphonic Production History (Ctrl+Alt+H): read locally."""
        from quill.core.publish.auphonic_history import history_path, load_history, remove_entry
        from quill.ui.converter_auphonic_history_dialog import ask_history

        if getattr(self, "_safe_mode", False):
            self._show_message_box(_SAFE_MODE, _TITLE)
            return
        store = history_path()

        def remove(entry: Any) -> None:
            remove_entry(store, entry.uuid)

        chosen = ask_history(
            self,
            load_history(store),
            refresh=lambda deliver: start_history_refresh(store, self._history_dest(), deliver),
            open_folder=open_results_folder,
            remove=remove,
        )
        if chosen is not None:
            self._download_again(chosen)

    def _history_dest(self) -> Path:
        """Where a production found only in the account would save its results."""
        try:
            return self._destination()
        except (IndexError, AttributeError):  # an empty queue has no source folder
            return Path.home() / "Downloads" / "Converted"

    def _download_again(self, entry: Any) -> None:
        from quill.apps.converter_auphonic import load_token

        if self._busy:
            self._announce("A job is already running.")
            return
        token = load_token()
        if not token:
            self._show_message_box(
                "Downloading needs your Auphonic API token, and none is stored. Sign in "
                "with Convert > Auphonic Account (Ctrl+Alt+Shift+A), then try again.",
                _TITLE,
            )
            return
        record = entry.as_pending()
        self._auphonic_run(
            token,
            lambda runner: runner.resume([record]),
            f"Downloading {entry.title} again from Auphonic",
            Path(entry.out_dir).parent,
            door="Convert > Auphonic Production History can try again",
        )

    # -- the account ------------------------------------------------------------------

    def show_auphonic_account(self) -> None:
        """Convert > Auphonic Account (Ctrl+Alt+Shift+A): nothing is asked until a button."""
        from quill.apps.converter_auphonic import load_token, save_token
        from quill.ui.converter_auphonic_history_dialog import ACCOUNT_TITLE, show_account

        if getattr(self, "_safe_mode", False):
            self._show_message_box(_SAFE_MODE, ACCOUNT_TITLE)
            return
        show_account(
            self,
            stored_token=load_token,
            check=start_account_details,
            save=save_token,
            forget=forget_token,
        )


# -- wx-free helpers (module level so tests can replace them) ----------------------------


def start_history_refresh(store: Path, dest: Path, deliver: Any) -> None:
    """Read the account's productions off the UI thread; ``deliver(entries, words)`` on it."""
    from quill.apps.converter_auphonic import load_token

    token = load_token()
    if not token:
        deliver(
            None,
            "Refreshing needs your Auphonic API token, and none is stored. Sign in with "
            "Convert > Auphonic Account first.",
        )
        return

    def worker() -> None:
        from quill.core.publish.auphonic_run import said

        try:
            entries, words = refresh_history(store, dest, token)
        except Exception as error:  # noqa: BLE001 - said in words on the UI thread
            wx.CallAfter(deliver, None, f"Could not refresh from Auphonic: {said(error)}")
            return
        wx.CallAfter(deliver, entries, words)

    threading.Thread(target=worker, daemon=True, name="converter-auphonic-history").start()


def refresh_history(store: Path, dest: Path, token: str) -> tuple[list[Any], str]:
    """Merge the account's recent productions into the history file; returns it and words."""
    from quill.core.publish.auphonic_account import list_productions
    from quill.core.publish.auphonic_history import load_history, merge_remote, save_history

    remote = list_productions(token)
    entries = load_history(store)
    updated, added = merge_remote(entries, list(remote), dest)
    if updated or added:
        save_history(store, entries)
    found = f"{len(remote)} recent production{'s' if len(remote) != 1 else ''}"
    return entries, f"Auphonic listed {found}: {updated} brought up to date, {added} added."


def open_results_folder(entry: Any) -> str:
    """Open *entry*'s results folder; ``""``, or why it could not."""
    folder = Path(entry.out_dir) if entry.out_dir else None
    if folder is None or not folder.is_dir():
        return "That folder does not exist yet: nothing has been saved there, or it was moved."
    try:
        os.startfile(str(folder))  # type: ignore[attr-defined]  # Windows only
    except (AttributeError, OSError) as error:
        return f"Could not open the folder: {error}"
    return ""


def account_details(token: str) -> Any:
    """The account view's one request (``user.json``). Never uploads anything."""
    from quill.core.publish.auphonic_account import account_details as fetch

    return fetch(token)


def start_account_details(token: str, deliver: Any) -> None:
    """Run :func:`account_details` off the UI thread; ``deliver(info, error)`` on it."""

    def worker() -> None:
        from quill.core.publish.auphonic_run import said

        try:
            info = account_details(token)
        except Exception as error:  # noqa: BLE001 - said in words on the UI thread
            wx.CallAfter(deliver, None, said(error))
            return
        wx.CallAfter(deliver, info, "")

    threading.Thread(target=worker, daemon=True, name="converter-auphonic-account").start()


def forget_token() -> None:
    """Sign Out: remove the family's stored Auphonic token (never anything else)."""
    try:
        from quill.core.publish.auphonic import CREDENTIAL_TARGET
        from quill.platform.windows.credential_manager import delete_generic_credential

        delete_generic_credential(CREDENTIAL_TARGET)
    except Exception:  # noqa: BLE001 - nothing stored, or no credential store here
        _log.warning("Could not remove the Auphonic token from the credential manager")
