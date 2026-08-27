"""Tests for the SSH client policy path (SEC-9, H-3-core).

These tests cover the *policy* chosen for unknown host keys without ever
opening a real network connection. The :class:`paramiko.SSHClient` is
stubbed at the module boundary so the connect function can be exercised
deterministically in CI on every platform.
"""

from __future__ import annotations

from typing import Any

import pytest


class _StubSSHClient:
    """Minimal paramiko.SSHClient stand-in recording the policy choice."""

    def __init__(self) -> None:
        self.loaded_system_keys = False
        self.chosen_policy_cls: type | None = None
        self.connect_called = False
        self.connected: dict[str, Any] = {}

    def load_system_host_keys(self) -> None:
        self.loaded_system_keys = True

    def set_missing_host_key_policy(self, policy: object) -> None:
        self.chosen_policy_cls = type(policy)

    def connect(self, **kwargs: Any) -> None:
        self.connect_called = True
        self.connected = dict(kwargs)

    def open_sftp(self) -> object:
        return object()


class _StubParamiko:
    """Drop-in for the ``paramiko`` module the connect function imports."""

    def __init__(self) -> None:
        self.client = _StubSSHClient()
        # Each "policy" is just a class; the connect function never inspects
        # the instance, only ``set_missing_host_key_policy(policy)`` is
        # called. We tag the chosen class on the recorded client instead.
        self._AutoAddPolicy = type("AutoAddPolicy", (), {})
        self._RejectPolicy = type("RejectPolicy", (), {})
        self._WarningPolicy = type("WarningPolicy", (), {})

    @property
    def AutoAddPolicy(self):  # noqa: N802 - paramiko API
        return self._AutoAddPolicy

    @property
    def RejectPolicy(self):  # noqa: N802 - paramiko API
        return self._RejectPolicy

    @property
    def WarningPolicy(self):  # noqa: N802 - paramiko API
        return self._WarningPolicy

    @property
    def SSHClient(self):  # noqa: N802 - paramiko API
        client = self.client

        def factory() -> _StubSSHClient:
            return client

        return factory


@pytest.fixture
def stub_paramiko(monkeypatch: pytest.MonkeyPatch) -> _StubParamiko:
    from quill.core.ssh import client as client_mod

    stub = _StubParamiko()
    monkeypatch.setattr(client_mod, "_import_paramiko", lambda: stub)
    return stub


def test_default_rejects_unknown_host_keys(
    stub_paramiko: _StubParamiko, monkeypatch: pytest.MonkeyPatch
) -> None:
    """H-3-core: with the default (settings) value, RejectPolicy is used."""
    from quill.core.ssh import client as client_mod

    # Default trust_first_use value is False; ensure settings default agrees.
    monkeypatch.setattr(
        "quill.core.settings.load_settings",
        lambda: type("S", (), {"ssh_trust_first_use": False})(),
    )
    client_mod.connect("example.com", username="alice", auth="password", password="x")
    assert stub_paramiko.client.chosen_policy_cls is stub_paramiko.RejectPolicy


def test_trust_first_use_overrides_to_auto_add(
    stub_paramiko: _StubParamiko,
) -> None:
    """H-3-core: explicit trust_first_use=True is the only way to opt into AutoAddPolicy."""
    from quill.core.ssh import client as client_mod

    client_mod.connect(
        "example.com", username="alice", auth="password", password="x", trust_first_use=True
    )
    assert stub_paramiko.client.chosen_policy_cls is stub_paramiko.AutoAddPolicy


def test_setting_ssh_trust_first_use_drives_policy(
    stub_paramiko: _StubParamiko, monkeypatch: pytest.MonkeyPatch
) -> None:
    """H-3-core: a Settings value of True is honored when not overridden."""
    from quill.core.ssh import client as client_mod

    monkeypatch.setattr(
        "quill.core.settings.load_settings",
        lambda: type("S", (), {"ssh_trust_first_use": True})(),
    )
    client_mod.connect("example.com", username="alice", auth="password", password="x")
    assert stub_paramiko.client.chosen_policy_cls is stub_paramiko.AutoAddPolicy


def test_load_system_host_keys_always_runs(stub_paramiko: _StubParamiko) -> None:
    """H-3-core: known_hosts are always loaded; the policy only governs unknowns."""
    from quill.core.ssh import client as client_mod

    client_mod.connect("example.com", username="alice", auth="password", password="x")
    assert stub_paramiko.client.loaded_system_keys is True


# --- the install hint that works (#1443) --------------------------------------


def test_a_missing_paramiko_names_quills_own_interpreter(monkeypatch):
    """'pip install paramiko' sent a real user in a circle: it lands in the
    system Python, and QUILL runs its own. The hint must name this
    interpreter and say to restart."""
    import builtins
    import sys

    from quill.core.ssh import client

    real_import = builtins.__import__

    def _no_paramiko(name, *args, **kwargs):
        if name == "paramiko":
            raise ModuleNotFoundError("No module named 'paramiko'")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", _no_paramiko)
    with pytest.raises(client.SshDependencyError) as caught:
        client._import_paramiko()
    text = str(caught.value)
    assert sys.executable in text
    assert "-m pip install paramiko" in text
    assert "restart QUILL" in text


def test_a_broken_paramiko_reports_the_real_failure(monkeypatch):
    """Present-but-broken is a different fact from absent; telling somebody to
    install a package they installed is how #1443 went in a circle."""
    import builtins

    from quill.core.ssh import client

    real_import = builtins.__import__

    def _broken_paramiko(name, *args, **kwargs):
        if name == "paramiko":
            raise ImportError("DLL load failed while importing _cffi_backend")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", _broken_paramiko)
    with pytest.raises(client.SshDependencyError) as caught:
        client._import_paramiko()
    text = str(caught.value)
    assert "installed but could not be loaded" in text
    assert "_cffi_backend" in text
    assert "pip install paramiko" not in text
