"""Shared fixtures and a controllable fake adapter for the QUILL Social tests."""

from __future__ import annotations

import pytest

from quill_social.adapters.base import (
    AdapterError,
    NetworkAdapter,
    PublishRequest,
    PublishResult,
)
from quill_social.capabilities import default_for
from quill_social.db import SocialStore


@pytest.fixture(autouse=True)
def _no_blocking_dialogs(monkeypatch):
    """Stop native modal alerts from blocking headless test runs.

    Dialogs legitimately confirm actions with ``wx.MessageBox`` for real users,
    but a test that drives a handler directly has no one to dismiss the modal.
    Patch the blocking alert calls to non-blocking no-ops for the whole suite.
    """
    try:
        import wx
    except Exception:
        return
    monkeypatch.setattr(wx, "MessageBox", lambda *a, **k: wx.OK, raising=False)


@pytest.fixture
def store():
    s = SocialStore(":memory:")
    yield s
    s.close()


class ScriptedAdapter(NetworkAdapter):
    """A NetworkAdapter whose publish outcomes are scripted for tests.

    ``script`` is a list where each entry is either the string ``"ok"`` or an
    ``AdapterError`` to raise on that call. After the script is exhausted every
    publish succeeds.
    """

    name = "mock"

    def __init__(self, script: list | None = None) -> None:
        self.script = list(script or [])
        self.calls: list[PublishRequest] = []
        self._seq = 0

    def capabilities(self):
        return default_for("mock")

    def home_timeline(self, *, limit: int = 40, since_id: str = ""):
        return []

    def notifications(self, *, limit: int = 40):
        return []

    def thread(self, item):
        return []

    def publish(self, request: PublishRequest) -> PublishResult:
        self.calls.append(request)
        outcome = self.script.pop(0) if self.script else "ok"
        if isinstance(outcome, AdapterError):
            raise outcome
        self._seq += 1
        return PublishResult(remote_id=f"r{self._seq}", uri=f"mock://{self._seq}")
