"""The recogniser the settings choose is actually returned.

Every dictation test replaces ``_make_recognizer`` with a fake, so nothing ever
called the real one. When the cloud providers (D-31) and the keyword spotter
(D-27) were merged on 2026-10-16, the local path briefly built its recogniser
and returned ``None`` -- local dictation would not have started at all, and
every gate stayed green. This calls the real function with stand-ins.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

pytest.importorskip("wx")

from quill.ui import windows_dictation_commands as commands  # noqa: E402


class _FakeLocal:
    def __init__(self, controller: Any, engine: str, **kwargs: Any) -> None:
        self.controller = controller
        self.engine = engine
        self.kwargs = kwargs
        self.keyword_gate: Any = "unset"


def _preferences(engine: str) -> Any:
    return SimpleNamespace(
        engine=engine,
        pause_seconds=1.0,
        speech_language="en",
        cloud_fields={},
        cloud_consent={},
        keywords=[],
    )


def test_a_local_engine_returns_its_recogniser_with_the_keyword_gate(monkeypatch) -> None:
    import quill.core.windows_dictation.kws_keywords as kws
    import quill.core.windows_dictation.local_recognizer as local

    monkeypatch.setattr(local, "LocalDictationRecognizer", _FakeLocal)
    monkeypatch.setattr(kws, "keyword_gate_for", lambda _preferences: None)
    controller = object()
    recognizer = commands._make_recognizer(controller, _preferences("moonshine"))
    assert isinstance(recognizer, _FakeLocal)
    assert recognizer.controller is controller and recognizer.engine == "moonshine"
    assert recognizer.keyword_gate is None  # set by the D-27 wiring, not left alone


def test_a_cloud_engine_goes_to_the_cloud_path(monkeypatch) -> None:
    seen: list[str] = []

    def fake_cloud(_controller: Any, preferences: Any) -> str:
        seen.append(preferences.engine)
        return "cloud recogniser"

    monkeypatch.setattr(commands, "_cloud_recognizer", fake_cloud)
    assert commands._make_recognizer(object(), _preferences("cloud-deepgram")) == "cloud recogniser"
    assert seen == ["cloud-deepgram"]
