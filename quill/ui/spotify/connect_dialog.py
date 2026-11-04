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
from quill.core.spotify.diagnostics import SignInTrace, diagnostic_report, plain_failure
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
    trace: SignInTrace | None = None,
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
    # Every step is recorded, so "nothing happened" can be answered with how
    # far it got (quill.core.spotify.diagnostics). No secret is ever recorded.
    trace = trace or SignInTrace(clock=clock)
    try:
        trace.step(f"Client ID entered, ending in {client_id[-4:]}.")
        consent.save_spotify_consent_complete()
        request = auth.build_authorization(client_id)
        server = server_factory(request.state)
        trace.step(f"Listening for the browser on {auth.DEFAULT_REDIRECT_URI}.")

        def _open() -> None:
            opened = open_browser(request.url)
            trace.step(
                "Browser opened at Spotify's sign-in page."
                if opened is not False
                else "Windows did not open a browser. The sign-in page could not be shown."
            )

        # The server is already bound; open the browser only once wait() signals
        # it is about to serve, so Spotify's redirect can never race an unbound port.
        code = server.wait(timeout, on_ready=_open)
        trace.step("Spotify sent the browser back to QUILL with a sign-in code.")
        response = auth.exchange_code(code, request.code_verifier, client_id, opener=opener)
        trace.step("Spotify accepted the code and issued access.")
        bundle = TokenBundle.from_token_response(response, now=clock())
        token_store.save_tokens(bundle)
        token_store.save_client_id(client_id)
        trace.finish("Connected.")
        return bundle.scope or "connected"
    except BaseException as exc:
        trace.finish(plain_failure(exc))
        raise


try:  # pragma: no cover - wx is present in the app, absent in some test envs
    import wx

    from quill.ui.dialog_contract import apply_modal_ids, set_accessible_name
    from quill.ui.dpi import dip_size

    class SpotifyConnectDialog(wx.Dialog):
        """Collect a Spotify Client ID and run the sign-in, accessibly.

        Pass the host's ``announce`` callable and its ``task_runner`` (the
        ``QuillTaskManager``) so the blocking OAuth round-trip runs off the UI
        thread; the manager delivers its callbacks on the UI thread.

        2026-11-04: the task was submitted with the wrong signature (the name
        both as a keyword and positionally), so Connect said it was opening the
        browser and then nothing happened -- the call raised before the
        browser could open. The dialog now also shows the exact redirect
        address the Spotify app must list, with a Copy button, and a Show
        Diagnostics report (quill.core.spotify.diagnostics).
        """

        def __init__(
            self,
            parent: wx.Window,
            *,
            announce: Callable[[str], None],
            task_runner: Any | None = None,
            safe_mode: bool = False,
        ) -> None:
            super().__init__(
                parent, title="Connect to Spotify", style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
            )
            self.SetHelpText(
                "Connect Quill Radio and QUILL Cast to your Spotify account. You need a "
                "free Spotify app of your own, from the Spotify for Developers dashboard, "
                "and Spotify Premium to play audio."
            )
            self._announce = announce
            self._task_runner = task_runner
            self._safe_mode = safe_mode

            outer = wx.BoxSizer(wx.VERTICAL)
            intro = wx.StaticText(
                self,
                label=(
                    "Enter your Spotify app's Client ID, then choose Connect to sign in "
                    "with your browser. Your Spotify app must list the redirect address "
                    "below, exactly. Spotify Premium is required to play audio."
                ),
            )
            outer.Add(intro, 0, wx.ALL, 8)

            row = wx.BoxSizer(wx.HORIZONTAL)
            label = wx.StaticText(self, label="Client &ID:")
            self._client_id = wx.TextCtrl(self, value=token_store.load_client_id())
            set_accessible_name(self._client_id, "Spotify Client ID")
            self._client_id.SetHelpText(
                "The Client ID from your Spotify app's Basic Information page. It is "
                "not a password."
            )
            row.Add(label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6)
            row.Add(self._client_id, 1)
            outer.Add(row, 0, wx.EXPAND | wx.ALL, 8)

            redirect_row = wx.BoxSizer(wx.HORIZONTAL)
            redirect_label = wx.StaticText(self, label="&Redirect address:")
            self._redirect = wx.TextCtrl(
                self, value=auth.DEFAULT_REDIRECT_URI, style=wx.TE_READONLY
            )
            set_accessible_name(self._redirect, "Redirect address for your Spotify app")
            self._redirect.SetHelpText(
                "Add this address, exactly, under Redirect URIs in your Spotify app's "
                "settings: http, not https, and 127.0.0.1, not localhost. Without it "
                "Spotify will not send the browser back to QUILL."
            )
            copy_redirect = wx.Button(self, label="Cop&y Address")
            copy_redirect.SetHelpText("Copy the redirect address to the clipboard.")
            copy_redirect.Bind(
                wx.EVT_BUTTON,
                lambda _e: self._copy(auth.DEFAULT_REDIRECT_URI, "Redirect address copied."),
            )
            redirect_row.Add(redirect_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6)
            redirect_row.Add(self._redirect, 1, wx.RIGHT, 6)
            redirect_row.Add(copy_redirect, 0)
            outer.Add(redirect_row, 0, wx.EXPAND | wx.ALL, 8)

            self._status = wx.StaticText(self, label="")
            set_accessible_name(self._status, "Sign-in status")
            outer.Add(self._status, 0, wx.ALL, 8)

            self._report = wx.TextCtrl(
                self, value="", style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_RICH2
            )
            set_accessible_name(self._report, "Spotify diagnostics")
            self._report.SetHelpText(
                "What QUILL knows about your Spotify setup: the redirect address, "
                "whether a Client ID is saved, whether you are signed in and with which "
                "permissions, your account type, and every step of the last sign-in "
                "attempt. It never shows a password or token. Copy it into an email to "
                "support if you need help."
            )
            self._report.SetMinSize(dip_size(self, 520, 160))
            self._report.Hide()
            outer.Add(self._report, 1, wx.EXPAND | wx.ALL, 8)

            tools = wx.BoxSizer(wx.HORIZONTAL)
            self._diagnose = wx.Button(self, label="Show &Diagnostics")
            self._diagnose.SetHelpText(
                "Check your Spotify setup and show what QUILL found, including how far "
                "the last sign-in got."
            )
            self._diagnose.Bind(wx.EVT_BUTTON, self._on_diagnose)
            self._copy_report = wx.Button(self, label="Copy Diagnostics")
            self._copy_report.SetHelpText("Copy the diagnostics report to the clipboard.")
            self._copy_report.Bind(
                wx.EVT_BUTTON,
                lambda _e: self._copy(self._report.GetValue(), "Diagnostics copied."),
            )
            self._copy_report.Enable(False)
            tools.Add(self._diagnose, 0, wx.RIGHT, 6)
            tools.Add(self._copy_report, 0)
            outer.Add(tools, 0, wx.ALL, 8)

            buttons = wx.StdDialogButtonSizer()
            connect_id = wx.ID_OK
            self._connect = wx.Button(self, connect_id, "&Connect")
            self._connect.SetHelpText(
                "Open Spotify's sign-in page in your browser. Approve QUILL there, and "
                "the browser comes back to QUILL by itself."
            )
            close_btn = wx.Button(self, wx.ID_CANCEL, "Close")
            close_btn.SetHelpText("Close this window. Escape does the same.")
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

        def _copy(self, text: str, said: str) -> None:
            if wx.TheClipboard.Open():
                try:
                    wx.TheClipboard.SetData(wx.TextDataObject(text))
                finally:
                    wx.TheClipboard.Close()
                self._announce(said)

        def _run(
            self,
            name: str,
            work: Callable[[], Any],
            done: Callable[[Any], None],
            failed: Callable[[BaseException], None],
        ) -> None:
            """Run *work* off the UI thread with QuillTaskManager's real signature."""
            runner = self._task_runner
            if runner is not None and hasattr(runner, "submit"):
                runner.submit(
                    name,
                    lambda **_kw: work(),
                    on_success=lambda _op, result: done(result),
                    on_failure=lambda _op, exc: failed(exc),
                )
                return
            try:  # no task manager: run inline (simple contexts and tests)
                done(work())
            except Exception as exc:  # noqa: BLE001 - surfaced to the user
                failed(exc)

        def _on_connect(self, _event: wx.CommandEvent) -> None:
            client_id = self._client_id.GetValue().strip()
            if not client_id:
                self._set_status("A Spotify Client ID is required.")
                self._client_id.SetFocus()
                return
            self._connect.Enable(False)
            self._set_status(
                "Opening your browser to sign in to Spotify. Approve QUILL there; this "
                "window waits up to five minutes."
            )

            def done(_scope: str) -> None:
                self._connect.Enable(True)
                self._set_status("Connected to Spotify.")
                self.EndModal(wx.ID_OK)

            def failed(error: BaseException) -> None:
                self._connect.Enable(True)
                self._set_status(plain_failure(error))

            self._run(
                "spotify-sign-in",
                lambda: perform_sign_in(client_id, safe_mode=self._safe_mode),
                done,
                failed,
            )

        def _on_diagnose(self, _event: wx.CommandEvent) -> None:
            self._set_status("Checking your Spotify setup.")

            def account() -> dict[str, Any]:
                from quill.core.spotify.client import SpotifyClient

                client = SpotifyClient(
                    token_store.load_tokens(),
                    token_store.load_client_id(),
                    on_tokens_refreshed=token_store.save_tokens,
                )
                return dict(client.get_me())

            signed_in = not token_store.load_tokens().is_empty and not self._safe_mode
            playback = _webview_available()

            def done(report: str) -> None:
                self._report.SetValue(report)
                self._report.Show()
                self._copy_report.Enable(True)
                self.Layout()
                self.Fit()
                self._report.SetFocus()
                self._report.SetInsertionPoint(0)
                self._set_status("Diagnostics ready.")

            self._run(
                "spotify-diagnostics",
                lambda: diagnostic_report(
                    account_lookup=account if signed_in else None,
                    playback_available=lambda: playback,
                ),
                done,
                lambda exc: self._set_status(plain_failure(exc)),
            )

    def _webview_available() -> bool:
        try:
            import wx.html2

            backend = (
                wx.html2.WebViewBackendEdge
                if wx.Platform == "__WXMSW__"
                else wx.html2.WebViewBackendDefault
            )
            return bool(wx.html2.WebView.IsBackendAvailable(backend))
        except Exception:  # noqa: BLE001 - no WebView module means no playback
            return False

except ImportError:  # pragma: no cover - wx unavailable; perform_sign_in still importable
    pass
