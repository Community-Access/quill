"""Tests for the shared Piper voice download (mirror-first, upstream fallback)."""

from __future__ import annotations

import pytest

from quill.core.speech import model_mirrors, piper_install
from quill.core.speech.model_mirrors import MirrorAsset
from quill.core.speech.piper_install import PiperInstallError, download_piper_voice


def test_prefers_the_assets_v1_mirror(monkeypatch, tmp_path) -> None:
    asset = MirrorAsset(
        "piper-voice-en_US-amy-low.zip", "a" * 64, archive_member="en_US-amy-low.onnx"
    )
    monkeypatch.setattr(model_mirrors, "mirror_for", lambda _p, _m: asset)
    used = {"mirror": False}

    def _fetch(_asset, target, **_kwargs):
        used["mirror"] = True
        return target

    monkeypatch.setattr(model_mirrors, "fetch_mirror_archive", _fetch)
    # If the upstream fallback were reached it would try the network; fail loudly.
    monkeypatch.setattr(
        piper_install,
        "_download_piper_voice_files",
        lambda *_a, **_k: pytest.fail("fallback should not run when a mirror exists"),
    )
    download_piper_voice("en_US-amy-low", tmp_path)
    assert used["mirror"] is True


def test_falls_back_to_upstream_when_not_mirrored(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(model_mirrors, "mirror_for", lambda _p, _m: None)

    class _Resp:
        def __init__(self, payload: bytes) -> None:
            self._p = payload
            self.headers = {"Content-Length": str(len(payload))}

        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

        def read(self, n: int = -1) -> bytes:
            chunk, self._p = self._p, b""
            return chunk

    monkeypatch.setattr(
        piper_install.urllib.request, "urlopen", lambda *_a, **_k: _Resp(b"VOICE-BYTES")
    )
    download_piper_voice("en_US-amy-low", tmp_path)
    assert (tmp_path / "en_US-amy-low.onnx").read_bytes() == b"VOICE-BYTES"
    assert (tmp_path / "en_US-amy-low.onnx.json").read_bytes() == b"VOICE-BYTES"


def test_unknown_voice_id_raises(tmp_path) -> None:
    with pytest.raises(PiperInstallError, match="download URL"):
        download_piper_voice("not-a-valid-voice", tmp_path)


def test_fallback_refuses_non_https(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(model_mirrors, "mirror_for", lambda _p, _m: None)
    # piper_voice_download_urls is imported inside download_piper_voice from
    # voice_catalog; patch it there so the http URLs actually reach the guard.
    import quill.core.voice_catalog as vc

    monkeypatch.setattr(
        vc, "piper_voice_download_urls", lambda _v: ("http://x/a.onnx", "http://x/a.onnx.json")
    )
    with pytest.raises(PiperInstallError, match="HTTPS"):
        download_piper_voice("en_US-amy-low", tmp_path)


def test_all_39_piper_voices_are_mirrored() -> None:
    from quill.core.voice_catalog import PIPER_VOICES

    for item in PIPER_VOICES:
        vid = item[0] if isinstance(item, tuple) else item
        assert model_mirrors.mirror_for("piper", vid) is not None, vid
