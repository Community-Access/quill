"""Capture the public page at a desktop and a phone width, with facts (wordpress.md 6.11).

Visual Review needs two things a blind site owner cannot get alone: a picture
of the page as a sighted visitor sees it, and facts about every image on it --
its displayed size, whether it spills out of the content area, whether it
loaded, the heading above it and its alt text. Both come from the browser
already on the computer, run hidden through :mod:`quill.core.wordpress.cdp`
(Edge, or Chrome when Edge is missing; never downloaded), with a throwaway
profile, so the visit is a plain anonymous visit to the public page.

The facts are measured, not guessed: the AI is told them, and the report
separates "failed to load", "had not finished loading" and "not captured"
instead of calling an image broken.

*style* is a stylesheet injected into the captured page only -- how Preview
and Review shows a proposed image or logo width without changing the site.

Stdlib only, no wx.
"""

from __future__ import annotations

import base64
import json
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any

from quill.core.wordpress import cdp

__all__ = [
    "DESKTOP",
    "PHONE",
    "Capture",
    "ImageFact",
    "ViewCapture",
    "ViewSize",
    "cache_note",
    "capture_page",
    "image_state",
    "parse_measurements",
]

_PAGE_TIMEOUT = 45.0
#: The tallest screenshot taken; a very long page is captured to here and the
#: rest is "not captured", said as such.
MAX_CAPTURE_HEIGHT = 8000


@dataclass(frozen=True)
class ViewSize:
    name: str  # "desktop", "phone"
    width: int
    height: int
    mobile: bool = False


DESKTOP = ViewSize("desktop", 1366, 900)
PHONE = ViewSize("phone", 390, 844, mobile=True)


@dataclass(frozen=True)
class ImageFact:
    src: str
    alt: str | None  # None: no alt attribute at all
    width: int
    height: int
    natural_width: int
    natural_height: int
    complete: bool
    overflows: bool
    heading: str
    top: int

    @property
    def name(self) -> str:
        tail = self.src.split("?", 1)[0].rstrip("/").rsplit("/", 1)[-1]
        return tail or self.src


@dataclass(frozen=True)
class ViewCapture:
    view: ViewSize
    screenshot: Path
    captured_height: int
    page_height: int
    images: tuple[ImageFact, ...]
    text: str = ""
    title: str = ""


@dataclass(frozen=True)
class Capture:
    url: str
    views: tuple[ViewCapture, ...]
    headers: Mapping[str, str] = field(default_factory=dict)
    browser: str = ""


_SETTLE = "new Promise((done) => setTimeout(done, 800))"

_SCROLL = """
new Promise((done) => {
  const height = document.documentElement.scrollHeight;
  let y = 0;
  const step = () => {
    y += window.innerHeight;
    window.scrollTo(0, y);
    if (y < height && y < MAX_HEIGHT) { setTimeout(step, 120); }
    else { window.scrollTo(0, 0); setTimeout(done, 600); }
  };
  step();
})
""".replace("MAX_HEIGHT", str(MAX_CAPTURE_HEIGHT))

_MEASURE = """
(() => {
  const main = document.querySelector('main, article, .entry-content, #content') || document.body;
  const box = main.getBoundingClientRect();
  const viewport = document.documentElement.clientWidth;
  const heads = Array.from(document.querySelectorAll('h1,h2,h3,h4,h5,h6'));
  const images = Array.from(document.querySelectorAll('img')).map((img) => {
    const r = img.getBoundingClientRect();
    let heading = '';
    for (const h of heads) {
      if (h.compareDocumentPosition(img) & Node.DOCUMENT_POSITION_FOLLOWING) {
        heading = (h.innerText || '').trim();
      }
    }
    return {
      src: img.currentSrc || img.src || '',
      alt: img.hasAttribute('alt') ? img.getAttribute('alt') : null,
      width: Math.round(r.width), height: Math.round(r.height),
      naturalWidth: img.naturalWidth, naturalHeight: img.naturalHeight,
      complete: img.complete,
      overflows: r.width > 0 && (r.right > viewport + 1 || r.width > box.width + 1),
      heading: heading.slice(0, 120), top: Math.round(r.top + window.scrollY),
    };
  });
  return JSON.stringify({
    images, title: document.title,
    text: (document.body.innerText || '').slice(0, 20000),
    height: document.documentElement.scrollHeight,
  });
})()
"""


def _inject(style: str) -> str:
    return (
        "(() => { const s = document.createElement('style'); "
        f"s.textContent = {json.dumps(style)}; document.head.appendChild(s); }})()"
    )


def capture_page(
    url: str,
    out_dir: Path,
    *,
    style: str = "",
    views: Sequence[ViewSize] = (DESKTOP, PHONE),
    browser: Path | None = None,
    launcher: Callable[[Path], Any] = cdp.HeadlessBrowser,
    progress: Callable[[str], None] | None = None,
    timeout: float = _PAGE_TIMEOUT,
) -> Capture:
    """Capture *url* at each view in one hidden browser. Runs off the UI thread.

    Raises :class:`~cdp.BrowserMissingError` before starting anything when
    neither Edge nor Chrome is installed.
    """
    executable = browser or cdp.find_browser()
    if executable is None:
        raise cdp.BrowserMissingError(
            "Visual Review needs Microsoft Edge or Google Chrome, and neither is on this "
            "computer. QUILL does not download a browser. Install either one, then try again."
        )
    out_dir.mkdir(parents=True, exist_ok=True)
    captured: list[ViewCapture] = []
    headers: dict[str, str] = {}
    with launcher(executable) as connection:
        for view in views:
            if progress is not None:
                progress(f"Capturing the {view.name} view.")
            shot, found = _capture_one(connection, url, view, out_dir, style, timeout)
            captured.append(shot)
            headers = headers or found
    name = "Microsoft Edge" if executable.name.lower().startswith("msedge") else "Google Chrome"
    return Capture(url, tuple(captured), headers, name)


def _capture_one(
    connection: Any, url: str, view: ViewSize, out_dir: Path, style: str, timeout: float
) -> tuple[ViewCapture, dict[str, str]]:
    target = str(connection.call("Target.createTarget", {"url": "about:blank"}).get("targetId", ""))
    session = str(
        connection.call("Target.attachToTarget", {"targetId": target, "flatten": True}).get(
            "sessionId", ""
        )
    )

    def run(expression: str) -> Any:
        answer = connection.call(
            "Runtime.evaluate",
            {"expression": expression, "awaitPromise": True, "returnByValue": True},
            session_id=session,
            timeout=timeout,
        )
        return answer.get("result", {}).get("value") if isinstance(answer, dict) else None

    try:
        connection.call(
            "Emulation.setDeviceMetricsOverride",
            {
                "width": view.width,
                "height": view.height,
                "deviceScaleFactor": 1,
                "mobile": view.mobile,
            },
            session_id=session,
        )
        connection.call("Page.enable", session_id=session)
        connection.call("Network.enable", session_id=session)
        navigated = connection.call("Page.navigate", {"url": url}, session_id=session)
        if navigated.get("errorText"):
            raise cdp.CdpError(f"The page would not load: {navigated['errorText']}.")
        connection.wait_event("Page.loadEventFired", session_id=session, timeout=timeout)
        if style:
            run(_inject(style))
        run(_SCROLL)  # wakes lazily loaded images, then back to the top
        run(_SETTLE)
        measured = parse_measurements(run(_MEASURE))
        page_height = int(measured.get("height") or view.height)
        height = max(view.height, min(page_height, MAX_CAPTURE_HEIGHT))
        shot = connection.call(
            "Page.captureScreenshot",
            {
                "format": "png",
                "captureBeyondViewport": True,
                "clip": {"x": 0, "y": 0, "width": view.width, "height": height, "scale": 1},
            },
            session_id=session,
            timeout=timeout,
        )
        path = out_dir / f"{view.name}.png"
        path.write_bytes(base64.b64decode(str(shot.get("data", ""))))
        found = _document_headers(connection)
        return (
            ViewCapture(
                view,
                path,
                height,
                page_height,
                tuple(measured.get("images", ())),
                str(measured.get("text", "")),
                str(measured.get("title", "")),
            ),
            found,
        )
    finally:
        try:
            connection.call("Target.closeTarget", {"targetId": target})
        except cdp.CdpError:
            pass


def _document_headers(connection: Any) -> dict[str, str]:
    """The page's own response headers, when the browser reported them."""
    events = getattr(connection, "_events", None) or []
    for event in events:
        if event.get("method") != "Network.responseReceived":
            continue
        params = event.get("params", {})
        if params.get("type") == "Document":
            raw = params.get("response", {}).get("headers", {})
            return {str(k).lower(): str(v) for k, v in raw.items()}
    return {}


def parse_measurements(raw: Any) -> dict[str, Any]:
    """The measuring script's JSON as plain values; ``images`` as :class:`ImageFact`."""
    try:
        data = json.loads(raw) if isinstance(raw, str) else (raw or {})
    except ValueError:
        data = {}
    if not isinstance(data, dict):
        data = {}
    images: list[ImageFact] = []
    for item in data.get("images", []) or []:
        if not isinstance(item, dict):
            continue
        alt = item.get("alt")
        images.append(
            ImageFact(
                src=str(item.get("src", "")),
                alt=None if alt is None else str(alt),
                width=int(item.get("width", 0) or 0),
                height=int(item.get("height", 0) or 0),
                natural_width=int(item.get("naturalWidth", 0) or 0),
                natural_height=int(item.get("naturalHeight", 0) or 0),
                complete=bool(item.get("complete", False)),
                overflows=bool(item.get("overflows", False)),
                heading=str(item.get("heading", "")),
                top=int(item.get("top", 0) or 0),
            )
        )
    data["images"] = tuple(images)
    return data


def image_state(fact: ImageFact, captured_height: int) -> str:
    """Loaded, failed, still loading, hidden, or outside what was captured."""
    if fact.top > captured_height:
        return "this part of the page was not captured"
    if fact.complete and fact.natural_width == 0:
        return "the image failed to load"
    if not fact.complete:
        return "the image had not finished loading"
    if fact.width == 0 or fact.height == 0:
        return "the image is on the page but not shown at this width"
    return "loaded"


def cache_note(
    headers: Mapping[str, str], last_update_gmt: str, *, now: datetime | None = None
) -> str:
    """A sentence when the captured page looks older than the last Update, else ""."""
    if not last_update_gmt:
        return ""
    try:
        updated = datetime.fromisoformat(last_update_gmt.rstrip("Z")).replace(tzinfo=UTC)
    except ValueError:
        return ""
    current = now or datetime.now(UTC)
    older = False
    modified = headers.get("last-modified", "")
    if modified:
        try:
            older = parsedate_to_datetime(modified) < updated
        except (TypeError, ValueError):
            older = False
    age = headers.get("age", "")
    if age.isdigit() and current.timestamp() - int(age) < updated.timestamp():
        older = True
    if not older:
        return ""
    return (
        "The captured page looks older than your last Update, so the site may be serving a "
        "cached copy. Check that the update finished, or clear the site's cache, then choose "
        "Review Again."
    )
