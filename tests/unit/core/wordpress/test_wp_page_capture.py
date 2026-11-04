"""Capturing the public page with a faked DevTools connection (wordpress.md 6.11)."""

from __future__ import annotations

import base64
import io
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from quill.core.wordpress import cdp
from quill.core.wordpress import page_capture as pc


def _png() -> str:
    from PIL import Image

    out = io.BytesIO()
    Image.new("RGB", (4, 4)).save(out, format="PNG")
    return base64.b64encode(out.getvalue()).decode("ascii")


MEASURED = {
    "images": [
        {
            "src": "https://radio.example/up/mast.jpg?ver=2",
            "alt": None,
            "width": 640,
            "height": 427,
            "naturalWidth": 2400,
            "naturalHeight": 1600,
            "complete": True,
            "overflows": False,
            "heading": "Our Schedule",
            "top": 200,
        },
        "not an image",
    ],
    "title": "Our Schedule",
    "text": "Our Schedule\nMornings.",
    "height": 2400,
}


class FakeConnection:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []
        self._events = [
            {
                "method": "Network.responseReceived",
                "params": {"type": "Document", "response": {"headers": {"Age": "30"}}},
            }
        ]

    def call(self, method, params=None, *, session_id="", timeout=30.0):
        self.calls.append((method, params or {}))
        if method == "Target.createTarget":
            return {"targetId": "t1"}
        if method == "Target.attachToTarget":
            return {"sessionId": "s1"}
        if method == "Runtime.evaluate":
            expression = params["expression"]
            if "JSON.stringify" in expression:
                return {"result": {"value": json.dumps(MEASURED)}}
            return {"result": {}}
        if method == "Page.captureScreenshot":
            return {"data": _png()}
        return {}

    def wait_event(self, method, *, session_id="", timeout=30.0):
        self.calls.append((method, {}))


class Launcher:
    def __init__(self, connection: FakeConnection) -> None:
        self.connection = connection
        self.started: list[Path] = []

    def __call__(self, executable: Path) -> Launcher:
        self.started.append(executable)
        return self

    def __enter__(self) -> FakeConnection:
        return self.connection

    def __exit__(self, *_exc: object) -> None:
        return None


def test_captures_both_views_with_facts(tmp_path) -> None:
    connection = FakeConnection()
    launcher = Launcher(connection)
    said: list[str] = []
    capture = pc.capture_page(
        "https://radio.example/our-schedule/",
        tmp_path,
        style="img { width: 10px }",
        browser=Path("C:/Edge/msedge.exe"),
        launcher=launcher,
        progress=said.append,
    )
    assert said == ["Capturing the desktop view.", "Capturing the phone view."]
    assert capture.browser == "Microsoft Edge"
    assert [v.view.name for v in capture.views] == ["desktop", "phone"]
    desktop = capture.views[0]
    assert desktop.screenshot.read_bytes().startswith(b"\x89PNG")
    assert desktop.captured_height == 2400 and desktop.title == "Our Schedule"
    fact = desktop.images[0]
    assert fact.alt is None and fact.name == "mast.jpg" and fact.natural_width == 2400
    assert capture.headers == {"age": "30"}
    metrics = [p for m, p in connection.calls if m == "Emulation.setDeviceMetricsOverride"]
    assert metrics[1]["width"] == 390 and metrics[1]["mobile"] is True
    injected = [p["expression"] for m, p in connection.calls if m == "Runtime.evaluate"]
    assert any("img { width: 10px }" in e for e in injected)
    assert ("Target.closeTarget", {"targetId": "t1"}) in connection.calls


def test_no_browser_raises_before_starting_anything(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(cdp, "find_browser", lambda *_a: None)
    launcher = Launcher(FakeConnection())
    with pytest.raises(cdp.BrowserMissingError, match="does not download a browser"):
        pc.capture_page("https://radio.example/", tmp_path / "x", launcher=launcher)
    assert launcher.started == []
    assert not (tmp_path / "x").exists()


def test_a_page_that_will_not_load(tmp_path) -> None:
    connection = FakeConnection()
    original = connection.call

    def call(method, params=None, **kw):
        if method == "Page.navigate":
            return {"errorText": "net::ERR_NAME_NOT_RESOLVED"}
        return original(method, params, **kw)

    connection.call = call  # type: ignore[method-assign]
    with pytest.raises(cdp.CdpError, match="would not load"):
        pc.capture_page(
            "https://nowhere.example/",
            tmp_path,
            browser=Path("chrome.exe"),
            launcher=Launcher(connection),
        )


def test_parse_measurements_tolerates_rubbish() -> None:
    assert pc.parse_measurements("not json")["images"] == ()
    assert pc.parse_measurements(None)["images"] == ()
    assert pc.parse_measurements("[1]")["images"] == ()


def _fact(**changes: Any) -> pc.ImageFact:
    values: dict[str, Any] = dict(
        src="a.png",
        alt="",
        width=10,
        height=10,
        natural_width=10,
        natural_height=10,
        complete=True,
        overflows=False,
        heading="",
        top=0,
    )
    values.update(changes)
    return pc.ImageFact(**values)


def test_image_states_are_kept_apart() -> None:
    assert pc.image_state(_fact(), 900) == "loaded"
    assert pc.image_state(_fact(natural_width=0), 900) == "the image failed to load"
    assert pc.image_state(_fact(complete=False), 900) == "the image had not finished loading"
    assert pc.image_state(_fact(top=5000), 900) == "this part of the page was not captured"
    assert "not shown at this width" in pc.image_state(_fact(width=0), 900)


def test_cache_note() -> None:
    now = datetime(2026, 11, 4, 12, 0, tzinfo=UTC)
    old = {"last-modified": "Sun, 01 Nov 2026 10:00:00 GMT"}
    assert "cached copy" in pc.cache_note(old, "2026-11-03T09:00:00", now=now)
    assert pc.cache_note(old, "2026-10-30T09:00:00", now=now) == ""
    assert "cached copy" in pc.cache_note({"age": "86400"}, "2026-11-04T00:00:00", now=now)
    assert pc.cache_note({"age": "60"}, "2026-11-04T00:00:00", now=now) == ""
    assert pc.cache_note(old, "", now=now) == ""
    assert pc.cache_note(old, "not a date", now=now) == ""
