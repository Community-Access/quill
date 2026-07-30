"""Hidden Web Playback engine for Spotify -- an AudioEngine-shaped WebView driver.

Spotify Premium audio is DRM-protected and only Spotify's own **Web Playback
SDK** may play it, inside a browser. QUILL hosts that SDK in a hidden
``wx.html2.WebView`` (Edge/WebView2 on Windows) and drives it exactly like the
other playback engines: this class offers the same method surface the Audio
Studio / Radio player uses from :class:`quill.ui.audio.audio_engine.AudioEngine`
(``play``/``pause``/``stop``/``seek``/``set_volume``/``is_playing``/
``position_ms``/``length_ms``/``close``), so a controller can treat a Spotify URI
like any other source. There is deliberately **no** cross-engine fallback for a
``spotify:`` URI -- only this engine can play one.

Two halves, cleanly separated so the interesting logic is testable without a
real WebView:

* **The page** (:data:`PLAYER_HTML`) loads ``sdk.scdn.co/spotify-player.js``,
  creates a ``Spotify.Player`` whose ``getOAuthToken`` callback asks QUILL for a
  fresh token, and forwards ``player_state_changed`` events back over the
  script-message bridge as JSON. Authored fresh for QUILL, using the
  ``AddScriptMessageHandler`` / ``EVT_WEBVIEW_SCRIPT_MESSAGE_RECEIVED`` handshake
  QUILL's WebViews already use.
* **The engine** (:class:`SpotifyWebEngine`) is a small state machine: it turns
  method calls into queued ``RunScript`` strings and turns the page's
  ``postMessage`` payloads back into a :class:`PlaybackSnapshot`. The WebView is
  injectable, so the whole state machine is unit-tested by feeding it synthetic
  message dicts and asserting the scripts it queued -- no browser, no network, no
  Spotify account.

Network note: the SDK and the ``play`` fetch it performs run **inside** the
WebView2 process and are invisible to the AST egress scanner; that surface is
documented in ``quill/tools/network_egress_audit.py``.
"""

from __future__ import annotations

import http.server
import json
import logging
import threading
from collections.abc import Callable
from dataclasses import dataclass

_log = logging.getLogger(__name__)

#: The script-message channel name the page posts on and QUILL listens to.
HANDLER_NAME = "quillSpotify"

#: The player page. Self-contained apart from Spotify's own SDK script; it posts
#: JSON messages of the shape :meth:`SpotifyWebEngine.receive_message` parses.
PLAYER_HTML = """<!doctype html>
<html lang="en">
<head><meta charset="utf-8"><title>QUILL Spotify playback</title></head>
<body>
<p>QUILL Spotify playback engine (no visible controls).</p>
<script src="https://sdk.scdn.co/spotify-player.js"></script>
<script>
(function () {
  var player = null, sdkReady = false, token = "", deviceId = "", pendingToken = null;

  function post(type, data) {
    var message = Object.assign({ type: type }, data || {});
    window.quillSpotify.postMessage(JSON.stringify(message));
  }

  function snapshot(state) {
    if (!state) { return null; }
    var track = state.track_window && state.track_window.current_track;
    return {
      is_playing: !state.paused,
      position_ms: state.position,
      duration_ms: state.duration,
      uri: track ? track.uri : "",
      name: track ? track.name : "",
      artist: track && track.artists
        ? track.artists.map(function (a) { return a.name; }).join(", ")
        : ""
    };
  }

  function connect() {
    if (!sdkReady || !token || player) { return; }
    player = new Spotify.Player({
      name: "QUILL",
      volume: 0.8,
      getOAuthToken: function (callback) {
        if (token) { callback(token); }
        else { pendingToken = callback; post("token_request"); }
      }
    });
    player.addListener("ready", function (e) {
      deviceId = e.device_id; post("device_ready", { device_id: e.device_id });
    });
    player.addListener("not_ready", function (e) {
      deviceId = ""; post("device_gone", { device_id: e.device_id });
    });
    player.addListener("player_state_changed", function (state) {
      post("playback", { snapshot: snapshot(state) });
    });
    ["initialization_error", "authentication_error", "account_error", "playback_error"]
      .forEach(function (name) {
        player.addListener(name, function (e) {
          post("error", { source: name, message: e && e.message ? e.message : name });
        });
      });
    player.connect();
  }

  window.quillSpotifyProvideToken = function (value) {
    token = value || "";
    if (pendingToken && token) {
      var callback = pendingToken; pendingToken = null; callback(token);
    }
    connect();
  };

  window.quillSpotifyPlay = function (uri) {
    if (!deviceId || !token) {
      post("error", { source: "play", message: "The Spotify player is not ready yet." });
      return;
    }
    var single = uri.indexOf("spotify:track:") === 0 || uri.indexOf("spotify:episode:") === 0;
    fetch("https://api.spotify.com/v1/me/player/play?device_id=" + encodeURIComponent(deviceId), {
      method: "PUT",
      headers: { "Authorization": "Bearer " + token, "Content-Type": "application/json" },
      body: JSON.stringify(single ? { uris: [uri] } : { context_uri: uri })
    }).catch(function (err) { post("error", { source: "play", message: String(err) }); });
  };

  window.quillSpotifyResume = function () { if (player) { player.resume(); } };
  window.quillSpotifyPause = function () { if (player) { player.pause(); } };
  window.quillSpotifySeek = function (ms) { if (player) { player.seek(Math.max(0, ms)); } };
  window.quillSpotifySetVolume = function (pct) {
    if (player) { player.setVolume(Math.max(0, Math.min(1, pct / 100))); }
  };
  window.quillSpotifyRequestState = function () {
    if (!player) { post("playback", { snapshot: null }); return; }
    player.getCurrentState().then(function (state) {
      post("playback", { snapshot: snapshot(state) });
    });
  };

  window.onSpotifyWebPlaybackSDKReady = function () {
    sdkReady = true; post("sdk_ready"); connect();
  };
  post("page_ready");
})();
</script>
</body>
</html>
"""


@dataclass(frozen=True, slots=True)
class PlaybackSnapshot:
    """The last known playback state, parsed from a page ``playback`` message."""

    is_playing: bool = False
    position_ms: int = 0
    duration_ms: int = 0
    track_uri: str = ""
    track_name: str = ""
    artist: str = ""


def parse_snapshot(raw: object) -> PlaybackSnapshot | None:
    """Turn a page ``snapshot`` object into a :class:`PlaybackSnapshot`.

    Returns ``None`` for a null/absent snapshot (nothing loaded) so callers can
    tell "no state yet" apart from "stopped at position 0".
    """
    if not isinstance(raw, dict):
        return None
    return PlaybackSnapshot(
        is_playing=bool(raw.get("is_playing")),
        position_ms=_coerce_int(raw.get("position_ms")),
        duration_ms=_coerce_int(raw.get("duration_ms")),
        track_uri=str(raw.get("uri", "")),
        track_name=str(raw.get("name", "")),
        artist=str(raw.get("artist", "")),
    )


def _coerce_int(value: object) -> int:
    if isinstance(value, bool):
        return 0
    if isinstance(value, (int, float)):
        return int(value)
    if isinstance(value, str) and value.strip():
        try:
            return int(float(value))
        except ValueError:
            return 0
    return 0


class SpotifyWebEngine:
    """Drives the hidden Web Playback WebView with an AudioEngine-shaped surface.

    Construct in production with a real ``parent`` window; the WebView, its
    script-message bridge, and a localhost page host are created for you.
    Construct in tests with an injected ``view`` (any object exposing
    ``RunScriptAsync(str)``) or a ``run_script`` callable and no parent -- then no
    wx object is touched and the state machine can be driven with
    :meth:`receive_message`.

    ``token_provider`` returns a currently-valid Spotify access token (the page
    asks for one on load and whenever the SDK needs to refresh); the callbacks
    fire as the device becomes ready, playback state changes, or an error occurs.
    """

    def __init__(
        self,
        parent: object | None = None,
        *,
        token_provider: Callable[[], str],
        on_ready: Callable[[str], None] | None = None,
        on_error: Callable[[str], None] | None = None,
        on_playback: Callable[[PlaybackSnapshot], None] | None = None,
        view: object | None = None,
        run_script: Callable[[str], None] | None = None,
    ) -> None:
        self._token_provider = token_provider
        self._on_ready = on_ready or (lambda _device_id: None)
        self._on_error = on_error or (lambda _message: None)
        self._on_playback = on_playback or (lambda _snapshot: None)
        self._view = view
        self._run_script = run_script
        self._device_id = ""
        self._pending_uri = ""
        self._snapshot = PlaybackSnapshot()
        self._closed = False
        self._page_host: _PageHost | None = None
        if view is None and run_script is None and parent is not None:
            self._create_webview(parent)

    # -- observable state -------------------------------------------------------

    @property
    def device_id(self) -> str:
        """The SDK player's Spotify Connect device id ("" until ready)."""
        return self._device_id

    @property
    def snapshot(self) -> PlaybackSnapshot:
        """The most recent playback snapshot the page reported."""
        return self._snapshot

    # -- AudioEngine-shaped surface --------------------------------------------

    def load(self, path: str) -> bool:
        """Begin playing a ``spotify:`` URI (the engine's notion of "load")."""
        self.play(path)
        return True

    def play(self, uri: str | None = None) -> None:
        """Play *uri* (start a new track/context) or, with no argument, resume.

        Starting a URI needs the SDK device to be ready; if it is not yet, the
        URI is remembered and played the moment ``device_ready`` arrives.
        """
        if uri:
            self._pending_uri = uri
            if self._device_id:
                self._start_pending()
        else:
            self._exec("window.quillSpotifyResume();")

    def pause(self) -> None:
        self._exec("window.quillSpotifyPause();")

    def stop(self) -> None:
        """No stop in the SDK; pause is the closest, matching the wx.media engine."""
        self._pending_uri = ""
        self._exec("window.quillSpotifyPause();")

    def seek(self, ms: int, *, resume: bool | None = None) -> None:
        self._exec(f"window.quillSpotifySeek({max(0, int(ms))});")
        if resume is True:
            self.play()
        elif resume is False:
            self.pause()

    def set_volume(self, percent: int) -> None:
        self._exec(f"window.quillSpotifySetVolume({max(0, min(100, int(percent)))});")

    def set_rate(self, rate: float) -> None:
        """Spotify plays at broadcast speed; no rate control is exposed."""

    def request_state(self) -> None:
        """Ask the page to post a fresh ``playback`` snapshot."""
        self._exec("window.quillSpotifyRequestState();")

    def position_ms(self) -> int:
        return self._snapshot.position_ms

    def length_ms(self) -> int:
        return self._snapshot.duration_ms

    def is_playing(self) -> bool:
        return self._snapshot.is_playing and not self._closed

    def close(self) -> None:
        """Tear down the WebView and page host (idempotent)."""
        self._closed = True
        self._pending_uri = ""
        view = self._view
        if view is not None and hasattr(view, "Destroy"):
            try:
                view.Destroy()
            except Exception:  # noqa: BLE001 - teardown must never raise
                _log.exception("Spotify WebView destroy failed")
        self._view = None
        if self._page_host is not None:
            self._page_host.close()
            self._page_host = None

    # -- inbound messages -------------------------------------------------------

    def receive_message(self, message: dict[str, object]) -> None:
        """Handle one decoded page message (the test + real-event entry point)."""
        message_type = str(message.get("type", ""))
        if message_type in {"page_ready", "sdk_ready", "token_request"}:
            self._provide_token()
        elif message_type == "device_ready":
            self._device_id = str(message.get("device_id", ""))
            self._on_ready(self._device_id)
            if self._pending_uri:
                self._start_pending()
        elif message_type == "device_gone":
            self._device_id = ""
        elif message_type == "playback":
            parsed = parse_snapshot(message.get("snapshot"))
            if parsed is not None:
                self._snapshot = parsed
                self._on_playback(parsed)
        elif message_type == "error":
            self._on_error(str(message.get("message") or "Spotify playback error."))

    # -- internals --------------------------------------------------------------

    def _start_pending(self) -> None:
        uri = self._pending_uri
        self._pending_uri = ""
        self._exec(f"window.quillSpotifyPlay({json.dumps(uri)});")

    def _provide_token(self) -> None:
        token = self._token_provider() or ""
        if token:
            self._exec(f"window.quillSpotifyProvideToken({json.dumps(token)});")
        else:
            self._on_error("QUILL is not signed in to Spotify.")

    def _exec(self, script: str) -> None:
        if self._closed:
            return
        if self._run_script is not None:
            self._run_script(script)
            return
        view = self._view
        if view is not None:
            view.RunScriptAsync(script)

    def _create_webview(self, parent: object) -> None:
        """Real path: host the page locally and load it in a hidden WebView."""
        import wx  # noqa: PLC0415 - kept out of the wx-free test path
        import wx.html2  # noqa: PLC0415

        backend = (
            wx.html2.WebViewBackendEdge
            if wx.Platform == "__WXMSW__"
            else wx.html2.WebViewBackendDefault
        )
        if not wx.html2.WebView.IsBackendAvailable(backend):
            raise RuntimeError("A WebView2 runtime is required to play Spotify.")
        self._page_host = _PageHost()
        self._page_host.start()
        webview = wx.html2.WebView.New(parent, size=(0, 0), backend=backend)
        webview.SetPosition((-10000, -10000))
        webview.AddScriptMessageHandler(HANDLER_NAME)
        webview.Bind(wx.html2.EVT_WEBVIEW_SCRIPT_MESSAGE_RECEIVED, self._on_script_message)
        webview.LoadURL(self._page_host.url)
        self._view = webview

    def _on_script_message(self, event: object) -> None:
        try:
            message = json.loads(event.GetString())
        except (ValueError, TypeError):
            _log.warning("Ignoring a malformed Spotify player message")
            return
        if isinstance(message, dict):
            self.receive_message(message)


class _PageHost:
    """Serves :data:`PLAYER_HTML` on ``127.0.0.1`` so the SDK has a real origin.

    The Web Playback SDK needs a genuine http(s) origin (not ``about:blank``), so
    the page is served from an ephemeral loopback port -- the same shape as the
    local relays elsewhere in QUILL. Local only; never a remote surface.
    """

    def __init__(self) -> None:
        body = PLAYER_HTML.encode("utf-8")

        class _Handler(http.server.BaseHTTPRequestHandler):
            def do_GET(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler contract
                if self.path not in ("/", "/player"):
                    self.send_error(404)
                    return
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Cache-Control", "no-store")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, format: str, *args: object) -> None:  # noqa: A002
                return

        self._server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
        self._thread = threading.Thread(
            target=self._server.serve_forever, name="QuillSpotifyPlayerHost", daemon=True
        )

    @property
    def url(self) -> str:
        return f"http://127.0.0.1:{self._server.server_address[1]}/player"

    def start(self) -> None:
        self._thread.start()

    def close(self) -> None:
        try:
            self._server.shutdown()
            self._server.server_close()
        except Exception:  # noqa: BLE001 - teardown must never raise
            _log.exception("Spotify page host shutdown failed")


__all__ = [
    "HANDLER_NAME",
    "PLAYER_HTML",
    "PlaybackSnapshot",
    "SpotifyWebEngine",
    "parse_snapshot",
]
