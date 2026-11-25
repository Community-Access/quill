"""FUX-02: Send to Media Player is offered only where Media Player is released.

A public QUILL, QUILL Lite or Converter offered "Send to Media Player (MP3
audio)" for an app the build does not ship; choosing it could only say
"Media Player could not be opened". Open in QUILL already hid itself when no
editor was installed; this is the same rule.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from quill.core import app_launcher
from quill.core.scribe import queue as q


@pytest.fixture(params=[True, False], ids=["released", "public"])
def player_here(request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch) -> bool:
    here = bool(request.param)
    monkeypatch.setattr(app_launcher, "is_app_released", lambda key: here or key != "player")
    monkeypatch.setattr(app_launcher, "build_launch_argv", lambda key: ["x"])
    return here


def _labels(steps: list[tuple[str, object]]) -> list[str]:
    return [label for label, _run in steps]


def test_the_app_hosts_offer_the_player_only_when_released(
    player_here: bool, tmp_path: Path
) -> None:
    from quill.ui import scribe_app_host

    ready = {"mp3": tmp_path / "N.mp3"}
    labels = _labels(scribe_app_host.elsewhere_steps(q.Job(), ready, lambda _s: None))
    assert ("Send to Media Player (MP3 audio)" in labels) is player_here


def test_quill_offers_the_player_only_when_released(player_here: bool, tmp_path: Path) -> None:
    from quill.ui import main_frame_scribe

    frame = type("MF", (), {"_announce": lambda _s, _t: None})()
    host = main_frame_scribe.QuillScribeHost(frame)
    mp3 = tmp_path / "N.mp3"
    labels = _labels(host.scribe_next_steps(q.Job(), {"mp3": mp3}))
    assert ("Send to Media Player (MP3 audio)" in labels) is player_here
    if not player_here:
        assert host.scribe_open_result(q.Job(), "mp3", mp3) == ""
