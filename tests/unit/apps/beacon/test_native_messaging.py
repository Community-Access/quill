"""Tests for the native messaging host (PRD 46 capture-bridge fallback).

Protocol framing, message dispatch, the serve loop, manifest building, and
cross-platform registration. Windows registration uses an in-memory fake winreg
(no real registry); POSIX registration writes to a temp dir.
"""

from __future__ import annotations

import io
import json
import os
import struct
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from quill.apps.beacon import native_messaging as nm

# -- fake winreg -------------------------------------------------------------


class _FakeKey:
    def __init__(self, path):
        self.path = path

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class FakeWinreg:
    HKEY_CURRENT_USER = "HKCU"
    KEY_WRITE = 0
    KEY_READ = 0
    REG_SZ = 1
    tree: dict[str, dict] = {}

    @classmethod
    def reset(cls):
        cls.tree = {}

    @staticmethod
    def CreateKeyEx(root, subkey, reserved, access):
        parts = subkey.split("\\")
        for i in range(1, len(parts) + 1):
            FakeWinreg.tree.setdefault("\\".join(parts[:i]), {})
        return _FakeKey(subkey)

    @staticmethod
    def SetValueEx(key, name, reserved, type_, value):
        FakeWinreg.tree[key.path][name if name is not None else ""] = value

    @staticmethod
    def OpenKeyEx(root, subkey, reserved, access):
        if subkey not in FakeWinreg.tree:
            raise FileNotFoundError(subkey)
        return _FakeKey(subkey)

    @staticmethod
    def QueryValueEx(key, name):
        name = name if name is not None else ""
        if name not in FakeWinreg.tree.get(key.path, {}):
            raise FileNotFoundError(name)
        return FakeWinreg.tree[key.path][name], FakeWinreg.REG_SZ

    @staticmethod
    def DeleteValue(key, name):
        name = name if name is not None else ""
        FakeWinreg.tree.get(key.path, {}).pop(name, None)

    @staticmethod
    def DeleteKey(root, subkey):
        FakeWinreg.tree.pop(subkey, None)

    @staticmethod
    def CloseKey(key):
        pass


@pytest.fixture
def fake_winreg(monkeypatch):
    FakeWinreg.reset()
    monkeypatch.setitem(sys.modules, "winreg", FakeWinreg)
    monkeypatch.setattr(sys, "platform", "win32")
    yield


# -- protocol ----------------------------------------------------------------


def test_round_trip():
    buf = io.BytesIO()
    nm.write_message(buf, {"ok": True, "beacon_id": "x"})
    buf.seek(0)
    assert nm.read_message(buf) == {"ok": True, "beacon_id": "x"}


def test_framing_uses_4_byte_le_length():
    buf = io.BytesIO()
    nm.write_message(buf, {"a": 1})
    raw = buf.getvalue()
    (length,) = struct.unpack("<I", raw[:4])
    assert length == len(raw) - 4
    assert json.loads(raw[4:].decode("utf-8")) == {"a": 1}


def test_read_message_eof_returns_none():
    assert nm.read_message(io.BytesIO(b"")) is None
    assert nm.read_message(io.BytesIO(b"\x01\x02\x03")) is None  # short header


def test_read_message_oversize_returns_none():
    buf = io.BytesIO(struct.pack("<I", nm.MAX_MESSAGE + 1) + b"{}")
    assert nm.read_message(buf) is None


def test_read_message_invalid_json_flagged():
    body = b"not json"
    buf = io.BytesIO(struct.pack("<I", len(body)) + body)
    msg = nm.read_message(buf)
    assert msg == {"__invalid__": True}


# -- dispatch ----------------------------------------------------------------


class FakeBridge:
    def __init__(self):
        self.captured = []
        self.batched = []

    def handle_capture(self, payload):
        self.captured.append(payload)
        return {"ok": True, "beacon_id": "b1"}

    def handle_batch(self, payload):
        self.batched.append(payload)
        return {"ok": True, "count": 1, "results": []}


def test_handle_capture_dispatch():
    b = FakeBridge()
    res = nm.handle_message({"type": "capture", "url": "https://x"}, b)
    assert res == {"ok": True, "beacon_id": "b1"}
    assert b.captured == [{"type": "capture", "url": "https://x"}]


def test_handle_batch_dispatch():
    b = FakeBridge()
    res = nm.handle_message({"type": "capture-batch", "tabs": [{"url": "u"}]}, b)
    assert res["ok"] and res["count"] == 1
    assert b.batched[0]["tabs"] == [{"url": "u"}]


def test_handle_ping():
    res = nm.handle_message({"type": "ping"}, FakeBridge())
    assert res["ok"] and res["service"] == "QuillBeacon"


def test_handle_unknown_type():
    res = nm.handle_message({"type": "bogus"}, FakeBridge())
    assert res["ok"] is False and "unknown type" in res["error"]


def test_handle_invalid_message():
    res = nm.handle_message({"__invalid__": True}, FakeBridge())
    assert res["ok"] is False


# -- serve loop --------------------------------------------------------------


def _framed(messages):
    buf = io.BytesIO()
    for m in messages:
        nm.write_message(buf, m)
    buf.seek(0)
    return buf


def test_serve_handles_messages_until_eof():
    bridge = FakeBridge()
    sin = _framed([
        {"type": "ping"},
        {"type": "capture", "url": "https://a"},
    ])
    sout = io.BytesIO()
    rc = nm.serve(bridge, stream_in=sin, stream_out=sout)
    assert rc == 0
    sout.seek(0)
    r1 = nm.read_message(sout)
    r2 = nm.read_message(sout)
    assert r1["ok"] and r1["service"] == "QuillBeacon"
    assert r2 == {"ok": True, "beacon_id": "b1"}
    assert nm.read_message(sout) is None  # no more replies


def test_serve_handler_error_does_not_kill_host():
    class Boom:
        def handle_capture(self, p):
            raise RuntimeError("boom")

        def handle_batch(self, p):
            return {"ok": True}

    sin = _framed([{"type": "capture", "url": "u"}])
    sout = io.BytesIO()
    rc = nm.serve(Boom(), stream_in=sin, stream_out=sout)
    assert rc == 0
    sout.seek(0)
    rep = nm.read_message(sout)
    assert rep["ok"] is False and "boom" in rep["error"]


# -- manifest ----------------------------------------------------------------


def test_build_manifest_chrome_uses_allowed_origins(tmp_path):
    m = nm.build_manifest(tmp_path / "wrap", browser="chrome")
    assert m["name"] == nm.HOST_NAME
    assert m["type"] == "stdio"
    assert "allowed_origins" in m and "allowed_extensions" not in m


def test_build_manifest_firefox_uses_allowed_extensions(tmp_path):
    m = nm.build_manifest(tmp_path / "wrap", browser="firefox")
    assert "allowed_extensions" in m and "allowed_origins" not in m


def test_build_manifest_custom_ids(tmp_path):
    m = nm.build_manifest(
        tmp_path / "wrap", browser="chrome", extension_ids=["chrome-extension://abc/"]
    )
    assert m["allowed_origins"] == ["chrome-extension://abc/"]


# -- POSIX registration ------------------------------------------------------


@pytest.fixture
def posix_data(monkeypatch, tmp_path):
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setattr(nm, "data_dir", lambda: tmp_path)
    dirs = {b: tmp_path / b for b in nm.BROWSERS}
    monkeypatch.setattr(nm, "_posix_manifest_dir", lambda browser: dirs[browser])
    return dirs


def test_posix_register_writes_manifest(posix_data):
    res = nm.register("chrome")
    assert res["ok"], res
    mf = posix_data["chrome"] / nm._manifest_filename()
    assert mf.exists()
    data = json.loads(mf.read_text())
    assert data["name"] == nm.HOST_NAME
    assert "allowed_origins" in data
    assert data["path"].endswith(".sh") or data["path"].endswith(".cmd")


def test_posix_status_and_unregister(posix_data):
    assert nm.status("chrome")["results"][0]["registered"] is False
    nm.register("chrome")
    assert nm.status("chrome")["results"][0]["registered"] is True
    assert nm.unregister("chrome")["ok"]
    assert nm.status("chrome")["results"][0]["registered"] is False
    # Second unregister reports not registered.
    assert "error" in nm.unregister("chrome")["results"][0]


def test_posix_register_all_browsers(posix_data):
    res = nm.register("all")
    assert res["ok"], res
    for b in nm.BROWSERS:
        assert (posix_data[b] / nm._manifest_filename()).exists()


# -- Windows registration ----------------------------------------------------


def test_win_register_writes_registry(fake_winreg, monkeypatch, tmp_path):
    monkeypatch.setattr(nm, "data_dir", lambda: tmp_path)
    res = nm.register("chrome")
    assert res["ok"], res
    key = nm._win_reg_path("chrome")
    with FakeWinreg.OpenKeyEx(FakeWinreg.HKEY_CURRENT_USER, key, 0, FakeWinreg.KEY_READ) as k:
        val, _t = FakeWinreg.QueryValueEx(k, nm.HOST_NAME)
    assert val.endswith("chrome.json") and nm.HOST_NAME in val


def test_win_status_and_unregister(fake_winreg, monkeypatch, tmp_path):
    monkeypatch.setattr(nm, "data_dir", lambda: tmp_path)
    assert nm.status("chrome")["results"][0]["registered"] is False
    nm.register("chrome")
    assert nm.status("chrome")["results"][0]["registered"] is True
    assert nm.unregister("chrome")["ok"]
    assert nm.status("chrome")["results"][0]["registered"] is False


def test_register_unknown_browser(posix_data):
    res = nm.register("netscape")
    assert "error" in res
