"""Accessible "Connect to Spotify" sign-in dialog.

The sign-in orchestration lives in :func:`perform_sign_in`, a plain function
that takes injectable pieces (browser opener, callback-server factory, network
opener, clock) so the whole OAuth round-trip is unit-testable with fakes and no
real browser, socket, or network. :class:`SpotifyConnectDialog` is a thin
wxPython shell that collects the Client ID and runs :func:`perform_sign_in` off
the UI thread, following QUILL's modal-dialog accessibility contract.
"""

from __future__ import annotations

import time
import webbrowser
from collections.abc import Callable
from typing import Any

from quill.core.spotify import auth, consent, token_store
from quill.core.spotify.auth_callback import CallbackServer
from quill.core.spotify.token_store import TokenBundle


def perform_sign_in(
    client_id: str,
    *,
    safe_mode: bool = False,
    opener: object | None = None,
    open_browser: Callable[[str], Any] = webbrowser.open,
    server_factory: Callable[[str], Any] = CallbackServer,
    timeout: float = 300.0,
    clock: Callable[[], float] = time.time,
) -> str:
    """Run the full PKCE sign-in for *client_id*, persisting the result.

    Records one-time consent, binds the loopback callback server, opens the
    browser to Spotify's authorize URL, waits for the redirect, exchanges the
    code, and saves the token bundle and client id. Returns the granted scope
    string (truthy on success). Raises ``SpotifyAuthError`` /
    ``SpotifyCallbackError`` on any failure.
    """
    auth.refuse_in_safe_mode(safe_mode)
    client_id = client_id.strip()
    if not client_id:
        raise auth.SpotifyAuthError("A Spotify Client ID is required to sign in.")
    consent.save_spotify_consent_complete()
    request = auth.build_authorization(client_id)
    server = server_factory(request.state)
    # The server is already bound; open the browser only once wait() signals it
    # is about to serve, so Spotify's redirect can never race an unbound port.
    code = server.wait(timeout, on_ready=lambda: open_browser(request.url))
    response = auth.exchange_code(code, request.code_verifier, client_id, opener=opener)
    bundle = TokenBundle.from_token_response(response, now=clock())
    token_store.save_tokens(bundle)
    token_store.save_client_id(client_id)
    return bundle.scope or "connected"


try:  # pragma: no cover - wx is present in the app, absent in some test envs
    import wx

    from quill.ui.dialog_contract import apply_modal_ids, set_accessible_name

    class SpotifyConnectDialog(wx.Dialog):
        """Collect a Spotify Client ID and run the sign-in, accessibly.

        Pass the host's ``announce`` callable and its ``task_runner`` (the
        ``QuillTaskManager``) so the blocking OAuth round-trip runs off the UI
        thread and the result is marshalled back with ``wx.CallAfter``.
        """

        def __init__(
            self,
            parent: wx.Window,
            *,
            announce: Callable[[str], None],
            task_runner: Any | None = None,
            safe_mode: bool = False,
        ) -> None:
            super().__init__(parent, title="Connect to Spotify")
            self._announce = announce
            self._task_runner = task_runner
            self._safe_mode = safe_mode

            outer = wx.BoxSizer(wx.VERTICAL)
            intro = wx.StaticText(
                self,
                label=(
                    "Enter your Spotify app Client ID, then choose Connect to sign in "
                    "with your browser. Spotify Premium is required to play audio."
                ),
            )
            outer.Add(intro, 0, wx.ALL, 8)

            row = wx.BoxSizer(wx.HORIZONTAL)
            label = wx.StaticText(self, label="Client &ID:")
            self._client_id = wx.TextCtrl(self, value=token_store.load_client_id())
            set_accessible_name(self._client_id, "Spotify Client ID")
            row.Add(label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6)
            row.Add(self._client_id, 1)
            outer.Add(row, 0, wx.EXPAND | wx.ALL, 8)

            self._status = wx.StaticText(self, label="")
            set_accessible_name(self._status, "Sign-in status")
            outer.Add(self._status, 0, wx.ALL, 8)

            buttons = wx.StdDialogButtonSizer()
            connect_id = wx.ID_OK
            self._connect = wx.Button(self, connect_id, "&Connect")
            close_btn = wx.Button(self, wx.ID_CANCEL, "Cl&ose")
            buttons.AddButton(self._connect)
            buttons.AddButton(close_btn)
            buttons.Realize()
            outer.Add(buttons, 0, wx.EXPAND | wx.ALL, 8)

            self.SetSizerAndFit(outer)
            apply_modal_ids(
                self,
                affirmative_id=connect_id,
                affirmative_label="Connect",
                cancel_id=wx.ID_CANCEL,
                cancel_label="Close",
            )
            self._connect.Bind(wx.EVT_BUTTON, self._on_connect)
            self._client_id.SetFocus()

        def _set_status(self, message: str) -> None:
            self._status.SetLabel(message)
            self._announce(message)

        def _on_connect(self, _event: wx.CommandEvent) -> None:
            client_id = self._client_id.GetValue().strip()
            if not client_id:
                self._set_status("A Spotify Client ID is required.")
                self._client_id.SetFocus()
                return
            self._connect.Enable(False)
            self._set_status("Opening your browser to sign in to Spotify...")

            def work() -> str:
                return perform_sign_in(client_id, safe_mode=self._safe_mode)

            def done(scope: str) -> None:
                self._connect.Enable(True)
                self._set_status("Connected to Spotify.")
                self.EndModal(wx.ID_OK)

            def failed(error: BaseException) -> None:
                self._connect.Enable(True)
                self._set_status(f"Could not connect to Spotify: {error}")

            if self._task_runner is not None and hasattr(self._task_runner, "submit"):
                self._task_runner.submit(
                    work,
                    on_success=lambda result: wx.CallAfter(done, result),
                    on_failure=lambda exc: wx.CallAfter(failed, exc),
                    name="spotify-sign-in",
                )
            else:  # no task manager: run inline (used in simple contexts/tests)
                try:
                    done(work())
                except Exception as exc:  # noqa: BLE001 - surfaced to the user
                    failed(exc)

except ImportError:  # pragma: no cover - wx unavailable; perform_sign_in still importable
    pass
