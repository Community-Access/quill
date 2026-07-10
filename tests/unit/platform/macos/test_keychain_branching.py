"""Cross-platform tests for the macOS Keychain backend selection (SEC-17 / #1).

The real round-trip lives in ``test_keychain.py`` and is darwin-gated (it
touches the live login Keychain). These tests run on *every* platform because
they pin the security-critical branching logic that the round-trip does not:

- When pyobjc's ``Security`` framework is available, ``set_secret`` MUST route
  through ``SecItemAdd`` with the secret in the ``kSecValueData`` dictionary
  entry, and MUST NOT spawn the ``security`` CLI (which would put the secret in
  the child's argv, visible via ``ps -ww``).
- When pyobjc is unavailable, ``set_secret`` falls back to the ``security`` CLI
  and emits a one-time ``RuntimeWarning`` naming the leak.

They monkeypatch the cached binding and ``subprocess.run`` rather than needing
a Mac, so a regression that re-introduces the argv leak fails on Windows/Linux
CI too, not only on the macOS runner.
"""

from __future__ import annotations

import subprocess
import warnings
from types import SimpleNamespace

import pytest

from quill.platform.macos import keychain


class _FakeSecurity:
    """Stand-in for the pyobjc ``Security`` module recording every call.

    Mirrors the pyobjc return convention the real module relies on: each
    ``SecItem*`` call returns ``(out_param, osstatus)``.
    """

    # Constant stand-ins (the real module's are opaque objects; only identity
    # as dict keys matters here).
    kSecClass = "kSecClass"
    kSecClassGenericPassword = "kSecClassGenericPassword"
    kSecAttrService = "kSecAttrService"
    kSecAttrAccount = "kSecAttrAccount"
    kSecValueData = "kSecValueData"
    kSecReturnData = "kSecReturnData"
    kSecMatchLimit = "kSecMatchLimit"
    kSecMatchLimitOne = "kSecMatchLimitOne"

    def __init__(self) -> None:
        self.items: dict[tuple[str, str], bytes] = {}
        self.add_calls: list[dict] = []
        self.update_calls: list[tuple[dict, dict]] = []
        self.delete_calls: list[dict] = []
        self.copy_calls: list[dict] = []

    @staticmethod
    def _key(query: dict) -> tuple[str, str]:
        return (query["kSecAttrService"], query["kSecAttrAccount"])

    def SecItemAdd(self, query: dict, result: object) -> tuple[object, int]:
        self.add_calls.append(query)
        key = self._key(query)
        if key in self.items:
            return None, keychain._ERR_SEC_DUPLICATE_ITEM
        self.items[key] = query["kSecValueData"]
        return None, keychain._ERR_SEC_SUCCESS

    def SecItemUpdate(self, query: dict, update: dict) -> tuple[object, int]:
        self.update_calls.append((query, update))
        self.items[self._key(query)] = update["kSecValueData"]
        return None, keychain._ERR_SEC_SUCCESS

    def SecItemCopyMatching(self, query: dict, result: object) -> tuple[object, int]:
        self.copy_calls.append(query)
        key = self._key(query)
        if key not in self.items:
            return None, keychain._ERR_SEC_ITEM_NOT_FOUND
        return self.items[key], keychain._ERR_SEC_SUCCESS

    def SecItemDelete(self, query: dict) -> tuple[object, int]:
        self.delete_calls.append(query)
        self.items.pop(self._key(query), None)
        return None, keychain._ERR_SEC_SUCCESS


@pytest.fixture
def no_cli(monkeypatch):
    """Fail the test if any subprocess is spawned -- the pyobjc path must not shell out."""
    calls: list[list[str]] = []

    def _fake_run(argv, **_kwargs):
        calls.append(list(argv))
        raise AssertionError(f"subprocess.run unexpectedly called with argv={argv}")

    monkeypatch.setattr(subprocess, "run", _fake_run)
    return calls


@pytest.fixture
def reset_binding(monkeypatch):
    """Reset the cached pyobjc probe + the one-time CLI-leak warning flag."""
    monkeypatch.setattr(keychain, "_SECURITY_BINDING", None)
    monkeypatch.setattr(keychain, "_CLI_LEAK_WARNED", False)


def test_set_secret_uses_secitemadd_and_never_shells_out(no_cli, reset_binding, monkeypatch):
    """#1: with pyobjc present the secret goes into kSecValueData, never argv."""
    fake = _FakeSecurity()
    monkeypatch.setattr(keychain, "_SECURITY_BINDING", (fake, True))

    keychain.set_secret("acct-1", "hunter2", service="Quill-Test")

    assert len(fake.add_calls) == 1
    call = fake.add_calls[0]
    assert call[fake.kSecValueData] == b"hunter2"
    assert call[fake.kSecAttrAccount] == "acct-1"
    assert call[fake.kSecAttrService] == "Quill-Test"
    # The leak-free guarantee: no subprocess was spawned, so the secret is in
    # no child's argv.
    assert no_cli == []


def test_get_secret_round_trips_through_secitemcopymatching(no_cli, reset_binding, monkeypatch):
    fake = _FakeSecurity()
    monkeypatch.setattr(keychain, "_SECURITY_BINDING", (fake, True))

    keychain.set_secret("acct-2", "super-secret")
    assert keychain.get_secret("acct-2") == "super-secret"
    assert keychain.get_secret("missing-acct") is None
    assert no_cli == []


def test_delete_secret_uses_secitemdelete(no_cli, reset_binding, monkeypatch):
    fake = _FakeSecurity()
    monkeypatch.setattr(keychain, "_SECURITY_BINDING", (fake, True))

    keychain.set_secret("acct-3", "value")
    keychain.delete_secret("acct-3")
    assert keychain.get_secret("acct-3") is None
    assert len(fake.delete_calls) == 1
    assert no_cli == []


def test_set_secret_updates_existing_item_instead_of_failing(no_cli, reset_binding, monkeypatch):
    """SecItemAdd returns errSecDuplicateItem -> SecItemUpdate replaces the data."""
    fake = _FakeSecurity()
    monkeypatch.setattr(keychain, "_SECURITY_BINDING", (fake, True))

    keychain.set_secret("acct-4", "first")
    keychain.set_secret("acct-4", "second")
    assert keychain.get_secret("acct-4") == "second"
    # The second write attempts SecItemAdd (which reports the duplicate), then
    # falls through to SecItemUpdate to replace the data.
    assert len(fake.add_calls) == 2
    assert len(fake.update_calls) == 1
    assert fake.update_calls[0][1][fake.kSecValueData] == b"second"


def test_set_secret_falls_back_to_cli_and_warns_when_pyobjc_missing(reset_binding, monkeypatch):
    """Without pyobjc, set_secret shells out (leaking via argv) and warns once."""
    monkeypatch.setattr(keychain, "_SECURITY_BINDING", "unavailable")

    captured: list[list[str]] = []

    def _fake_run(argv, **_kwargs):
        captured.append(list(argv))
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", _fake_run)

    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        keychain.set_secret("acct-5", "leaky-secret", service="Quill-Test")
        keychain.set_secret("acct-6", "second-secret", service="Quill-Test")  # should NOT re-warn

    # The CLI was used for both writes...
    assert len(captured) == 2
    assert captured[0][0] == "security"
    assert "leaky-secret" in captured[0]  # documenting the leak the warning names
    # ...and the warning fired exactly once, naming the argv leak.
    leak_warnings = [
        x for x in w if issubclass(x.category, RuntimeWarning) and "argv" in str(x.message)
    ]
    assert len(leak_warnings) == 1


def test_get_secret_falls_back_to_cli_without_warning_when_pyobjc_missing(
    reset_binding, monkeypatch
):
    """The read CLI path does not leak (``-w`` selects stdout, not an argument), so no warning."""
    monkeypatch.setattr(keychain, "_SECURITY_BINDING", "unavailable")

    def _fake_run(argv, **_kwargs):
        # ``security find-generic-password -s <svc> -a <acct> -w`` -> the secret
        # is NOT in argv; it would be printed to stdout.
        assert "find-generic-password" in argv
        assert "secret-value" not in argv
        return SimpleNamespace(returncode=0, stdout="secret-value\n", stderr="")

    monkeypatch.setattr(subprocess, "run", _fake_run)

    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        assert keychain.get_secret("acct-7") == "secret-value"

    assert not [x for x in w if issubclass(x.category, RuntimeWarning)]


def test_sec_call_normalizes_both_pyobjc_return_conventions():
    """The status-int disambiguation must accept either tuple ordering."""
    # (out_param, status) -- the documented pyobjc convention.
    assert keychain._sec_call((b"data", 0)) == (b"data", 0)
    assert keychain._sec_call((None, keychain._ERR_SEC_ITEM_NOT_FOUND)) == (
        None,
        keychain._ERR_SEC_ITEM_NOT_FOUND,
    )
    # A bare OSStatus (no out-param), as SecItemDelete may return.
    assert keychain._sec_call(0) == (None, 0)
    assert keychain._sec_call(keychain._ERR_SEC_ITEM_NOT_FOUND) == (
        None,
        keychain._ERR_SEC_ITEM_NOT_FOUND,
    )
