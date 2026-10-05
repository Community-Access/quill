"""Reading a YouTube live chat on its own thread, with chat-downloader.

Split from :mod:`quill.core.radio.youtube_live_chat` (GATE-11). :class:`ChatReader`
reads chat-downloader's message generator into a queue the Live Chat window
drains, reconnects politely (a few tries, growing waits), says a failure once,
and stops cleanly when the window closes.

wx-free, strict-typed. The single network call is chat-downloader's own
``get_chat`` inside :func:`open_chat` -- the reviewed egress site.
"""

from __future__ import annotations

import queue
import threading
from collections.abc import Callable, Iterable, Iterator

from quill.core.radio.youtube_live_chat import ChatMessage, LiveChatError, parse_message

# -- reading the chat -------------------------------------------------------------

#: ``(url) -> (messages, closer)``. What tests inject instead of the network.
ChatOpener = Callable[[str], "tuple[Iterable[dict[str, object]], Callable[[], None]]"]

#: chat-downloader's exceptions that trying again cannot fix.
_FINAL = (
    "NoChatReplay",
    "ChatDisabled",
    "VideoUnavailable",
    "VideoNotFound",
    "LoginRequired",
    "VideoUnplayable",
    "InvalidURL",
    "SiteNotSupported",
)


def speakable(error: BaseException) -> str:
    """One plain sentence for a chat failure (pure)."""
    name = type(error).__name__
    if name == "NoChatReplay":
        return "This video has no chat replay. YouTube keeps one only for some finished streams."
    if name == "ChatDisabled":
        return "Chat is turned off for this video."
    if name in ("VideoUnavailable", "VideoNotFound", "VideoUnplayable"):
        return "YouTube says this video is not available, so its chat cannot be read."
    if name == "LoginRequired":
        return (
            "This chat is for members or signed-in viewers only. Choose a cookies.txt "
            "file under Use my YouTube sign-in in Preferences to read it."
        )
    if name in ("InvalidURL", "SiteNotSupported", "URLNotProvided"):
        return "That is not a YouTube video address, so it has no chat."
    if isinstance(error, LiveChatError) and error.args:
        return str(error.args[0])
    text = str(error).lower()
    if "timed out" in text or "connection" in text or "network" in text:
        return "YouTube could not be reached. Check your connection."
    return "YouTube stopped answering the chat."


def open_chat(url: str) -> tuple[Iterable[dict[str, object]], Callable[[], None]]:
    """Open *url*'s chat with chat-downloader -- the reviewed egress site.

    Carries the listener's YouTube sign-in only when it is on *and* comes from
    a cookies.txt file: chat-downloader reads a file and cannot read a
    browser's cookie store. Refused in Safe Mode before anything is imported.
    """
    import os

    if os.environ.get("QUILL_SAFE_MODE") == "1":
        raise LiveChatError("YouTube is not available in Safe Mode.")
    try:
        import chat_downloader  # type: ignore[import-untyped,import-not-found,unused-ignore]

        ChatDownloader = chat_downloader.ChatDownloader
    except ImportError as error:
        raise LiveChatError(
            "Live chat support is not installed in this copy of Quill Radio."
        ) from error
    from quill.core.radio.youtube_signin import cookie_options

    cookies = cookie_options().get("cookiefile")
    downloader = ChatDownloader(cookies=str(cookies) if cookies else None)
    chat = downloader.get_chat(
        url,
        message_groups=["messages", "superchat"],
        max_attempts=3,
        interruptible_retry=True,
    )
    return chat, downloader.close


class ChatReader:
    """Reads a chat on a daemon thread into a queue the window drains.

    *on_error* is called once, from the reader thread, with a sentence when
    the chat cannot be read or has failed for good; *on_end* when a live
    stream's chat ends normally. Both are expected to hop to the UI thread.
    """

    def __init__(
        self,
        url: str,
        *,
        opener: ChatOpener | None = None,
        on_error: Callable[[str], None] = lambda _m: None,
        on_end: Callable[[], None] = lambda: None,
        retry_waits: tuple[float, ...] = (5.0, 15.0, 45.0),
    ) -> None:
        self.url = url
        self.messages: queue.Queue[ChatMessage] = queue.Queue()
        self._opener = opener or open_chat
        self._on_error = on_error
        self._on_end = on_end
        self._waits = retry_waits
        self._stop = threading.Event()
        self._closer: Callable[[], None] | None = None
        self._thread: threading.Thread | None = None
        self.failed = False

    @property
    def running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def start(self) -> None:
        if self.running:
            return
        self._stop.clear()
        self._thread = threading.Thread(
            target=self.run, name="radio-youtube-live-chat", daemon=True
        )
        self._thread.start()

    def stop(self, timeout: float = 2.0) -> None:
        """Ask the reader to finish and close its connection. Never raises."""
        self._stop.set()
        closer, self._closer = self._closer, None
        if closer is not None:
            try:
                closer()
            except Exception:  # noqa: BLE001 - closing a dead session is fine
                pass
        thread = self._thread
        if thread is not None and thread is not threading.current_thread():
            thread.join(timeout)

    def drain(self, limit: int = 500) -> list[ChatMessage]:
        """Everything waiting, up to *limit*, without blocking."""
        out: list[ChatMessage] = []
        while len(out) < limit:
            try:
                out.append(self.messages.get_nowait())
            except queue.Empty:
                break
        return out

    def run(self) -> None:
        """The thread body; public so tests can run it inline."""
        attempt = 0
        while not self._stop.is_set():
            try:
                stream, self._closer = self._opener(self.url)
                for raw in _iterate(stream):
                    if self._stop.is_set():
                        return
                    attempt = 0  # a message proves the connection is good
                    message = parse_message(raw)
                    if message is not None:
                        self.messages.put(message)
            except Exception as error:  # noqa: BLE001 - every failure is spoken once
                if self._stop.is_set():
                    return
                final = type(error).__name__ in _FINAL or isinstance(error, LiveChatError)
                if final or attempt >= len(self._waits):
                    self.failed = True
                    self._on_error(speakable(error))
                    return
                if self._stop.wait(self._waits[attempt]):
                    return
                attempt += 1
                continue
            if not self._stop.is_set():
                self._on_end()
            return


def _iterate(stream: Iterable[dict[str, object]]) -> Iterator[dict[str, object]]:
    yield from stream


__all__ = ["ChatOpener", "ChatReader", "open_chat", "speakable"]
