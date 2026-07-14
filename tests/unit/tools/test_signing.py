"""Ed25519 / minisign-shaped signing primitive."""

from __future__ import annotations

import base64
import subprocess
import sys
from pathlib import Path

import pytest

# PyNaCl ships in the optional [signing] extra; CI runners without it skip
# these tests instead of failing collection.
pytest.importorskip("nacl", reason="PyNaCl (the [signing] extra) is not installed")
from nacl import signing as nacl_signing  # noqa: E402

from quill.tools import signing
from quill.tools.signing import (
    KEY_ID,
    SIGNATURE_SUFFIX,
    sign_artifact,
    signature_status,
    verify_artifact,
    write_minisig,
)


@pytest.fixture
def keypair() -> tuple[nacl_signing.SigningKey, nacl_signing.VerifyKey]:
    sk = nacl_signing.SigningKey.generate()
    return sk, sk.verify_key


@pytest.fixture
def artifact(tmp_path: Path) -> Path:
    p = tmp_path / "thing.qvp.json"
    p.write_text('{"k":"v"}', encoding="utf-8")
    return p


def test_sign_artifact_creates_sidecar(keypair, artifact: Path) -> None:
    sk, _vk = keypair
    sidecar = sign_artifact(artifact, sk)
    assert sidecar == artifact.with_suffix(artifact.suffix + SIGNATURE_SUFFIX)
    assert sidecar.exists()
    lines = sidecar.read_text(encoding="utf-8").splitlines()
    assert lines[0] == "untrusted comment: quill artifact signature"
    assert lines[1] == f"key id: {KEY_ID}"
    assert lines[2].startswith("sig: ")
    sig = base64.b64decode(lines[2][5:])
    assert len(sig) == 64


def test_verify_artifact_round_trip(keypair, artifact: Path) -> None:
    sk, vk = keypair
    sign_artifact(artifact, sk)
    status = verify_artifact(artifact, public_key=vk)
    assert status.signed is True
    assert status.verified is True
    assert status.signer_key_id == KEY_ID
    assert status.error is None


def test_verify_artifact_tampered_returns_invalid(keypair, artifact: Path) -> None:
    sk, vk = keypair
    sign_artifact(artifact, sk)
    artifact.write_text('{"k":"tampered"}', encoding="utf-8")
    status = verify_artifact(artifact, public_key=vk)
    assert status.signed is True
    assert status.verified is False
    assert "signature" in (status.error or "").lower()


def test_verify_artifact_wrong_key_returns_invalid(keypair, artifact: Path) -> None:
    sk, _vk = keypair
    other_vk = nacl_signing.SigningKey.generate().verify_key
    sign_artifact(artifact, sk)
    status = verify_artifact(artifact, public_key=other_vk)
    assert status.signed is True
    assert status.verified is False
    assert status.error is not None


def test_verify_artifact_missing_sidecar_returns_unsigned(artifact: Path) -> None:
    status = verify_artifact(artifact)
    assert status.signed is False
    assert status.verified is False
    assert "no sidecar" in (status.error or "").lower()


def test_signature_status_uses_bundled_key(
    keypair, artifact: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    sk, vk = keypair
    # Re-route the bundled key so signature_status() resolves to our keypair.
    monkeypatch.setattr(
        "quill.tools.signing.PUBLIC_KEY_B64",
        base64.b64encode(bytes(vk)).decode(),
        raising=False,
    )
    sign_artifact(artifact, sk)
    assert signature_status(artifact) == verify_artifact(artifact, public_key=vk)


def test_keygen_produces_valid_keypair(tmp_path: Path) -> None:
    pub = tmp_path / "kp.pub"
    priv = tmp_path / "kp.priv"
    sk = nacl_signing.SigningKey.generate()
    pub.write_text(
        base64.b64encode(bytes(sk.verify_key)).decode() + "\n",
        encoding="utf-8",
    )
    priv_b64 = base64.b64encode(sk.encode() + sk.verify_key.encode()).decode()
    priv.write_text(
        "untrusted comment: quill signing key - do not commit\n" + priv_b64 + "\n",
        encoding="utf-8",
    )
    loaded = base64.b64decode(pub.read_text(encoding="utf-8").strip())
    assert len(loaded) == 32
    priv_text = priv.read_text(encoding="utf-8")
    assert "do not commit" in priv_text
    raw = base64.b64decode(priv_text.splitlines()[-1])
    assert len(raw) == 64


def test_cli_sign_and_verify(tmp_path: Path) -> None:
    artifact = tmp_path / "thing.qvp.json"
    artifact.write_text('{"k":"v"}', encoding="utf-8")
    sk = nacl_signing.SigningKey.generate()
    priv = tmp_path / "priv.key"
    priv_b64 = base64.b64encode(sk.encode() + sk.verify_key.encode()).decode()
    priv.write_text(priv_b64, encoding="utf-8")
    sign_proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "quill.tools.signing",
            "sign",
            str(artifact),
            "--secret-key",
            str(priv),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    assert sign_proc.returncode == 0
    pub = tmp_path / "pub.key"
    pub.write_text(base64.b64encode(bytes(sk.verify_key)).decode(), encoding="utf-8")
    verify_proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "quill.tools.signing",
            "verify",
            str(artifact),
            "--public-key",
            str(pub),
        ],
        capture_output=True,
        text=True,
    )
    assert verify_proc.returncode == 0
    assert "verified" in verify_proc.stdout.lower()


def test_cli_verify_unsigned_exits_2(tmp_path: Path) -> None:
    artifact = tmp_path / "thing.qvp.json"
    artifact.write_text('{"k":"v"}', encoding="utf-8")
    pub = tmp_path / "pub.key"
    sk = nacl_signing.SigningKey.generate()
    pub.write_text(base64.b64encode(bytes(sk.verify_key)).decode(), encoding="utf-8")
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "quill.tools.signing",
            "verify",
            str(artifact),
            "--public-key",
            str(pub),
        ],
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 2
    assert "unsigned" in (proc.stdout + proc.stderr).lower()


def test_write_minisig_round_trip(tmp_path: Path) -> None:
    sidecar = tmp_path / "x.minisig"
    sig = b"\x00" * 64
    write_minisig(sidecar, sig, KEY_ID)
    raw_sig, kid = signing.read_minisig(sidecar)
    assert raw_sig == sig
    assert kid == KEY_ID
