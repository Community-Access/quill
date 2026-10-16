"""The station pack builder: signed with the publisher key, or not at all.

A run without ``STATION_PACK_SIGNING_KEY`` writes an unsigned pack that the
app refuses; a key that is not the publisher's is refused before anything is
signed. The real publisher key is never used here: a test key stands in for it.
"""

from __future__ import annotations

import base64
import importlib.util
import json
from pathlib import Path
from typing import Any

import pytest
from nacl import signing

from quill.core.radio.enrichment import PackRefusedError
from quill.core.radio.enrichment.pack import MANIFEST_NAME, PACK_NAME, open_verified

_ROOT = Path(__file__).resolve().parents[3]
_SCRIPT = _ROOT / "scripts" / "build_station_pack.py"
_WORKFLOW = _ROOT / ".github" / "workflows" / "station-pack.yml"


def _module() -> Any:
    spec = importlib.util.spec_from_file_location("build_station_pack", _SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _picks(tmp: Path) -> Path:
    document = {
        "updated": "2026-10-01T00:00:00Z",
        "collections": [
            {
                "title": "Community Radio",
                "items": [
                    {
                        "type": "stream",
                        "title": "KUOW 94.9",
                        "stream_url": "https://k.example/live",
                        "description": "News for the Sound.",
                    }
                ],
            }
        ],
    }
    path = tmp / "picks.json"
    path.write_text(json.dumps(document), encoding="utf-8")
    return path


def test_a_no_key_run_writes_an_unsigned_pack_the_app_refuses(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.delenv("STATION_PACK_SIGNING_KEY", raising=False)
    out = tmp_path / "out"
    assert _module().main(["--out", str(out), "--picks", str(_picks(tmp_path))]) == 0
    assert "UNSIGNED" in capsys.readouterr().out
    assert (out / PACK_NAME).is_file()
    assert not (out / (PACK_NAME + ".minisig")).exists()
    assert json.loads((out / MANIFEST_NAME).read_text())["signed"] is False
    with pytest.raises(PackRefusedError, match="not signed"):
        open_verified(out / PACK_NAME)  # the bundled publisher key, as the app does
    assert _module().main(["--verify", str(out)]) == 1


def test_require_signature_fails_without_a_key(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("STATION_PACK_SIGNING_KEY", raising=False)
    out = tmp_path / "out"
    assert _module().main(["--out", str(out), "--require-signature"]) == 1
    assert not out.exists()


def test_a_stranger_key_is_refused_before_signing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    stranger = signing.SigningKey.generate()
    monkeypatch.setenv("STATION_PACK_SIGNING_KEY", base64.b64encode(bytes(stranger)).decode())
    out = tmp_path / "out"
    with pytest.raises(SystemExit, match="not the seed for the publisher key"):
        _module().main(["--out", str(out)])
    assert not out.exists()


def test_a_bad_secret_says_what_is_wrong(monkeypatch: pytest.MonkeyPatch) -> None:
    with pytest.raises(SystemExit, match="not valid base64"):
        _module().signing_key_from("%%%")
    with pytest.raises(SystemExit, match="decodes to 3 bytes"):
        _module().signing_key_from(base64.b64encode(b"abc").decode())


def test_a_signed_build_verifies_with_the_matching_key(tmp_path: Path) -> None:
    key = signing.SigningKey.generate()
    module = _module()
    module.refuse_a_stranger(key, expected=key.verify_key)  # the publisher check passes
    summary = module.build(
        tmp_path / "out", picks=_picks(tmp_path), signing_key=key, built_at="2026-10-16T00:00:00Z"
    )
    assert summary["signature"] is not None and summary["stations"] == 1
    pack = open_verified(summary["pack"], public_key=key.verify_key)
    assert pack.stations[0].call_sign == "KUOW"
    assert pack.stations[0].provenance["description"] == "community_picks"


def test_two_builds_of_the_same_data_are_byte_identical(tmp_path: Path) -> None:
    module = _module()
    picks = _picks(tmp_path)
    a = module.build(tmp_path / "a", picks=picks, built_at="2026-10-16T00:00:00Z")
    b = module.build(tmp_path / "b", picks=picks, built_at="2026-10-16T00:00:00Z")
    assert a["pack"].read_bytes() == b["pack"].read_bytes()


def test_the_weekly_workflow_names_its_secret_and_publishes_nothing() -> None:
    text = _WORKFLOW.read_text(encoding="utf-8")
    assert "secrets.STATION_PACK_SIGNING_KEY" in text
    assert "schedule:" in text and "cron:" in text
    assert "contents: read" in text
    for outward in ("gh release", "git push", "gh pr create"):
        assert outward not in text
