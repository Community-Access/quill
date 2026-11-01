"""Tell me when this changes, on a window: the timer, the worker and the words.

The rules live in :mod:`quill.core.ai.change_watch` (local first, at most one
ask a minute and 30 a watch, Safe Mode, nothing after close). This is the wx
side that QUILL Studio and Quill Radio share (codex.md decision 25, 10B.6):

* one watch per window, ticked by a ``wx.Timer`` every :data:`TICK_MS`;
* each tick's grab, OCR and any ask run on a worker, never two at once, and
  the result comes back with ``wx.CallAfter``;
* Start and Stop are spoken through the app's ``_announce`` (the announcement
  service, so they are brailled too -- GATE-BRAILLE), and a report only when
  something changed, in one sentence;
* the window closing ends the watch (``window_closed``), so nothing is grabbed
  or sent after it.

The ask sends before and after as **one** picture, labelled Before and After,
fitted to the connection (:func:`~quill.core.ai.picture_prep.fit_image`), on the
same ``service.describe_image`` route Describe a Picture and Describe the Video
use. That route counts each request where the connection is counted: on this
computer for the ChatGPT plan, by GitHub for Copilot, from the company's own
answer for an own key. The 10B.4 picture consent is asked by
:meth:`ChangeWatchController.request_start` before the watch starts.
"""

from __future__ import annotations

import io
import shutil
import tempfile
import threading
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

__all__ = [
    "ASK_TIMEOUT_S",
    "TICK_MS",
    "ChangeWatchController",
    "before_after_picture",
    "controller_for",
]

#: How often the watch looks, in milliseconds.
TICK_MS = 4000
#: How long one ask may take before the watch gives up on it.
ASK_TIMEOUT_S = 90.0

_ONE_PICTURE = (
    " Both are in one picture: the left half, labelled Before, and the right half, labelled After."
)
_CONNECTION_CHANGED = (
    "Stopped watching: the AI in use changed, and pictures were agreed for the one "
    "before. Start again to watch with this one."
)

Submit = Callable[..., Any]


def before_after_picture(before: bytes, after: bytes) -> bytes:
    """*before* and *after* side by side, each labelled, as PNG bytes."""
    from PIL import Image, ImageDraw, ImageFont

    with Image.open(io.BytesIO(before)) as a_open, Image.open(io.BytesIO(after)) as b_open:
        a = a_open.convert("RGB")
        b = b_open.convert("RGB")
    if b.size != a.size:
        b = b.resize(a.size)
    label_size = max(18, min(64, a.width // 24))
    try:
        font: Any = ImageFont.load_default(size=label_size)
    except TypeError:  # pragma: no cover - Pillow before 10.1
        font = ImageFont.load_default()
    band = label_size + 16
    gap = max(8, a.width // 100)
    sheet = Image.new("RGB", (a.width * 2 + gap, a.height + band), "black")
    draw = ImageDraw.Draw(sheet)
    for index, (name, picture) in enumerate((("Before", a), ("After", b))):
        left = index * (a.width + gap)
        draw.text((left + 10, 8), name, fill="white", font=font)
        sheet.paste(picture, (left, band))
    out = io.BytesIO()
    sheet.save(out, format="PNG")
    return out.getvalue()


def _default_ocr(data: bytes) -> str:
    """Windows OCR (then Tesseract) on this computer; "" when there is none."""
    from quill.core.ai.picture_prep import read_locally

    return read_locally(data, "").text


def controller_for(host: Any) -> ChangeWatchController:
    """*host*'s one controller, made on first use."""
    controller = getattr(host, "_change_watch_controller", None)
    if controller is None:
        controller = ChangeWatchController(host)
        host._change_watch_controller = controller
    return controller


class ChangeWatchController:
    """One window's watch: Start, Stop, the timer and the worker.

    *host* is the app frame (a ``HostedAiMixin``): ``_announce``,
    ``_ai_service``, ``_ai_capable``, ``_ai_ready``, ``_ai_switched_on``,
    ``_safe_mode`` and ``frame``. *submit*, *call_after*, *clock* and *ocr* are
    injected for tests; by default a worker thread, ``wx.CallAfter``,
    ``time.monotonic`` and OCR on this computer.
    """

    def __init__(
        self,
        host: Any,
        *,
        submit: Submit | None = None,
        call_after: Callable[..., Any] | None = None,
        clock: Callable[[], float] = time.monotonic,
        ocr: Callable[[bytes], str] | None = None,
        interval_ms: int = TICK_MS,
        ask_timeout: float = ASK_TIMEOUT_S,
    ) -> None:
        self._host = host
        self._submit = submit
        self._call_after = call_after
        self._clock = clock
        self._ocr = ocr if ocr is not None else _default_ocr
        self._interval_ms = interval_ms
        self._ask_timeout = ask_timeout
        self._watch: Any = None
        self._timer: Any = None
        self._busy = False
        self._generation = 0
        self._connection = ""
        self._available: Callable[[], str] | None = None
        self._on_end: Callable[[], None] | None = None
        self._bound = False
        self._window_gone = False
        #: Asks this window has made (each is also counted by the connection).
        self.asks_sent = 0

    # -- state ---------------------------------------------------------------- #

    @property
    def watching(self) -> bool:
        return bool(self._watch is not None and self._watch.watching)

    @property
    def subject(self) -> str:
        return str(getattr(self._watch, "subject", "") or "")

    def _say(self, sentence: str) -> None:
        if sentence:
            self._host._announce(sentence)

    # -- start ----------------------------------------------------------------- #

    def request_start(
        self,
        *,
        subject: str,
        grab: Callable[[], bytes | None],
        refusal: Callable[[], str] | None = None,
        available: Callable[[], str] | None = None,
        on_start: Callable[[], None] | None = None,
        on_end: Callable[[], None] | None = None,
        stop_key: str = "",
    ) -> bool:
        """The Start command: every gate, the consent, then the watch. True if started.

        *refusal* says, before anything is asked, why there is nothing to watch
        ("" when there is). *available* is asked on the UI thread before each
        look; a sentence there ends the watch with that sentence.
        """
        host = self._host
        if self.watching:
            key = f" {stop_key} stops it." if stop_key else ""
            self._say(f"Already watching {self.subject}.{key}")
            return False
        if not host._ai_switched_on():
            return False  # Safe Mode or the family's AI Off: said already
        reason = refusal() if refusal is not None else ""
        if reason:
            self._say(reason)
            return False
        if not host._ai_capable("pictures") or not host._ai_ready():
            return False  # nothing sent; the switch was offered (codex.md 10A.8)
        connection = str(getattr(host._ai_service(), "connection_in_use", "") or "")
        from quill.ui.hosted_ai_picture_consent import ask_picture_consent

        if not ask_picture_consent(host, connection):
            self._say("Nothing is being watched: pictures were not agreed for this AI.")
            return False
        return self.begin(
            subject=subject,
            grab=grab,
            connection=connection,
            available=available,
            on_start=on_start,
            on_end=on_end,
        )

    def begin(
        self,
        *,
        subject: str,
        grab: Callable[[], bytes | None],
        connection: str,
        available: Callable[[], str] | None = None,
        on_start: Callable[[], None] | None = None,
        on_end: Callable[[], None] | None = None,
    ) -> bool:
        """Start the watch itself, after the gates; the start is spoken."""
        from quill.core.ai.change_watch import ChangeWatch, WatchRefused

        if self._window_gone:
            self._say("This window has closed, so there is nothing to watch.")
            return False
        watch = ChangeWatch(
            grab=grab,
            ask=self._ask,
            subject=subject,
            ocr=self._ocr,
            count_ask=self._count_ask,
            clock=self._clock,
            safe_mode=bool(getattr(self._host, "_safe_mode", False)),
        )
        try:
            sentence = watch.start()
        except WatchRefused as refused:
            self._say(str(refused.args[0]))
            return False
        self._generation += 1
        self._watch = watch
        self._connection = connection
        self._available = available
        self._on_end = on_end
        self._busy = False
        self._bind_close()
        if on_start is not None:
            try:
                on_start()
            except Exception:  # noqa: BLE001 - a helper is never worth the watch
                pass
        self._start_timer()
        self._say(sentence)
        return True

    # -- stop ------------------------------------------------------------------ #

    def stop(self) -> None:
        """The Stop command: the watch ends and says so."""
        watch = self._watch
        if watch is None or not watch.watching:
            self._say("Nothing was being watched.")
            return
        self._end(watch.stop())

    def _end(self, sentence: str = "") -> None:
        """End the watch: no more ticks, nothing late spoken, the helper undone."""
        self._generation += 1
        self._stop_timer()
        watch = self._watch
        if watch is not None and watch.watching:
            watch.stop()
        on_end, self._on_end = self._on_end, None
        if on_end is not None:
            try:
                on_end()
            except Exception:  # noqa: BLE001 - a helper is never worth a crash
                pass
        self._say(sentence)

    def window_closed(self) -> None:
        """The window went: the watch ends silently and nothing more is grabbed."""
        self._window_gone = True
        watch = self._watch
        if watch is not None:
            watch.window_closed()
        self._end()

    def _bind_close(self) -> None:
        if self._bound:
            return
        frame = getattr(self._host, "frame", None)
        if frame is None or not hasattr(frame, "Bind"):
            return
        import wx

        def closing(event: Any) -> None:
            self.window_closed()
            event.Skip()

        def destroyed(event: Any) -> None:
            if event.GetEventObject() is frame:
                self.window_closed()
            event.Skip()

        frame.Bind(wx.EVT_CLOSE, closing)
        frame.Bind(wx.EVT_WINDOW_DESTROY, destroyed)
        self._bound = True

    # -- the timer ------------------------------------------------------------- #

    def _start_timer(self) -> None:
        if self._timer is None:
            try:
                import wx

                timer = wx.Timer()
                timer.Bind(wx.EVT_TIMER, lambda _e: self.tick())
                self._timer = timer
            except Exception:  # noqa: BLE001 - no timer: the watch still answers ticks
                return
        self._timer.Start(self._interval_ms)

    def _stop_timer(self) -> None:
        timer = self._timer
        if timer is not None:
            try:
                timer.Stop()
            except Exception:  # noqa: BLE001 - a timer on a dying window
                pass

    # -- one tick (UI thread), its work (worker) and the result (UI thread) ---- #

    def tick(self) -> None:
        """One look, unless one is still running. Called by the timer."""
        watch = self._watch
        if watch is None or not watch.watching or self._busy or self._window_gone:
            return
        reason = self._available() if self._available is not None else ""
        if reason:
            self._end(reason)
            return
        now_using = str(getattr(self._host._ai_service(), "connection_in_use", "") or "")
        if now_using != self._connection:
            self._end(_CONNECTION_CHANGED)
            return
        self._busy = True
        generation = self._generation

        def work(**_kwargs: Any) -> Any:
            return watch.tick()

        def done(_name: Any, report: Any) -> None:
            self._later(self._deliver, generation, report, None)

        def failed(_name: Any, error: BaseException) -> None:
            self._later(self._deliver, generation, None, error)

        submit = self._submit
        if submit is None:
            from quill.ui.update_download import thread_submit

            submit = thread_submit
        submit("Watch for changes", work, on_success=done, on_failure=failed)

    def _later(self, fn: Callable[..., Any], *args: Any) -> None:
        if self._call_after is not None:
            self._call_after(fn, *args)
            return
        import wx

        wx.CallAfter(fn, *args)

    def _deliver(self, generation: int, report: Any, error: BaseException | None) -> None:
        if generation != self._generation:
            return  # stopped, closed or restarted while it looked: say nothing
        self._busy = False
        watch = self._watch
        if error is not None:
            message = str(error.args[0]) if error.args else str(error)
            self._end(f"Stopped watching: {message.rstrip('.')}.")
            return
        if report is None:
            return
        if watch is not None and not watch.watching:
            self._end(report.sentence)  # the watch ended itself (30 asks, a failure)
            return
        self._say(report.sentence)

    # -- the ask (worker thread; the send itself on the UI thread) ------------- #

    def _count_ask(self) -> None:
        self.asks_sent += 1

    def _ask(self, before: bytes, after: bytes, prompt: str) -> str:
        from quill.core.ai.picture_prep import fit_image, longest_side_for

        connection = self._connection
        generation = self._generation
        prepared = fit_image(before_after_picture(before, after), longest_side_for(connection))
        scratch = Path(tempfile.mkdtemp(prefix="quill-change-watch-"))
        target = scratch / ("watch.png" if prepared.mime == "image/png" else "watch.jpg")
        target.write_bytes(prepared.data)
        finished = threading.Event()
        result: dict[str, str] = {}

        def done(text: str) -> None:
            result["text"] = str(text or "")
            finished.set()

        def failed(sentence: str) -> None:
            result["error"] = str(sentence or "the request failed")
            finished.set()

        def send() -> None:
            watch = self._watch
            if (
                generation != self._generation
                or self._window_gone
                or watch is None
                or not watch.watching
            ):
                failed("the watch ended, so nothing was sent")
                return
            service = self._host._ai_service()
            if str(getattr(service, "connection_in_use", "") or "") != connection:
                failed("the AI in use changed, so nothing was sent")
                return
            try:
                service.describe_image(
                    target,
                    prompt + _ONE_PICTURE,
                    on_done=done,
                    on_error=failed,
                    requires=("text", "pictures"),
                )
            except Exception as error:  # noqa: BLE001 - said as the watch's end
                failed(str(error))

        try:
            self._later(send)
            if not finished.wait(self._ask_timeout):
                raise TimeoutError("no answer came in time")
            if "error" in result:
                raise RuntimeError(result["error"].rstrip("."))
            return result.get("text", "")
        finally:
            shutil.rmtree(scratch, ignore_errors=True)
