"""The catalogue signature has to be readable by the thing that reads it.

This exists because of a bug that no amount of care in the signer would have
caught: ``scripts/sign_community_picks.py`` hand-rolled a two-line sidecar
(comment, then base64) while ``quill.tools.signing.read_minisig`` requires three
lines with a ``key id:`` between them. The Ed25519 signature was perfectly
good and the app rejected the *file* as unreadable -- and rejecting fails
closed, falling back to the bundled catalogue, which is indistinguishable from
working software.

So the whole failure mode was: set the secret, watch CI sign and publish
successfully, and have the fetched catalogue silently never used. The test that
would have caught it is the one that signs and then verifies with the app's own
verifier, rather than checking either half alone.
"""

from __future__ import annotations

import base64
import importlib.util
import json
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[3]
_SCRIPT = _ROOT / "scripts" / "sign_community_picks.py"

pytest.importorskip("nacl", reason="PyNaCl is needed to sign or verify anything")


def _load_script(monkeypatch, target: Path):
    """Import the signer with its TARGET pointed at a temporary file."""
    spec = importlib.util.spec_from_file_location("_sign_picks_under_test", _SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    monkeypatch.setattr(module, "TARGET", target)
    monkeypatch.setattr(module, "SIDECAR", target.with_suffix(".json.minisig"))
    return module


@pytest.fixture
def catalogue(tmp_path: Path) -> Path:
    path = tmp_path / "picks.json"
    path.write_text(json.dumps({"format": 1, "picks": []}), encoding="utf-8")
    return path


@pytest.fixture
def publisher(tmp_path: Path, monkeypatch):
    """A throwaway publisher keypair, installed as the one the app trusts."""
    from nacl import signing

    key = signing.SigningKey(bytes(range(32)))
    pub = tmp_path / "quill-pub.key"
    pub.write_text(base64.b64encode(key.verify_key.encode()).decode(), encoding="utf-8")
    monkeypatch.setenv("SIGNING_PUBLIC_KEY_PATH", str(pub))
    return key


def test_the_signature_verifies_with_the_apps_own_verifier(catalogue, publisher, monkeypatch):
    """The whole point. Signing and verifying are checked together, because
    each half was individually correct while the pair did not work."""
    from quill.tools.signing import load_publisher_public_key, verify_artifact

    module = _load_script(monkeypatch, catalogue)
    sidecar = module.sign(base64.b64encode(publisher.encode()).decode())

    status = verify_artifact(catalogue, load_publisher_public_key(), sidecar)
    assert status.verified, status.error


def test_the_sidecar_is_minisig_shaped(catalogue, publisher, monkeypatch):
    """Three lines, with a key id. read_minisig refuses anything else, and
    'unreadable sidecar' is reported the same way a forged one would be."""
    from quill.tools.signing import read_minisig

    module = _load_script(monkeypatch, catalogue)
    sidecar = module.sign(base64.b64encode(publisher.encode()).decode())

    lines = sidecar.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 3
    assert lines[0].startswith("untrusted comment:")
    assert lines[1].startswith("key id:")
    assert lines[2].startswith("sig: ")

    signature, key_id = read_minisig(sidecar)
    assert len(signature) == 64
    assert key_id


def test_it_sits_beside_the_file_it_signs(catalogue, publisher, monkeypatch):
    """The app fetches the sidecar from a fixed URL next to picks.json; a
    signature written anywhere else is a signature nobody fetches."""
    module = _load_script(monkeypatch, catalogue)
    sidecar = module.sign(base64.b64encode(publisher.encode()).decode())

    assert sidecar.name == "picks.json.minisig"
    assert sidecar.parent == catalogue.parent


def test_a_foreign_key_is_refused_before_anything_is_written(catalogue, publisher, monkeypatch):
    """Signing with a key no shipped build trusts publishes a catalogue every
    listener silently refuses -- which looks exactly like working software,
    because falling back to the bundled copy is what it is supposed to do."""
    from nacl import signing

    module = _load_script(monkeypatch, catalogue)
    stranger = signing.SigningKey(bytes(reversed(range(32))))

    with pytest.raises(SystemExit) as exit_info:
        module.sign(base64.b64encode(stranger.encode()).decode())

    assert "quill-pub.key" in str(exit_info.value)
    assert not catalogue.with_suffix(".json.minisig").exists()


def test_a_seed_plus_public_key_export_is_accepted(catalogue, publisher, monkeypatch):
    """Some tools export the 32-byte seed and the 32-byte public key joined.
    Taking the first half is right; signing with the wrong 32 bytes would
    produce a signature that verifies against nothing."""
    from quill.tools.signing import load_publisher_public_key, verify_artifact

    module = _load_script(monkeypatch, catalogue)
    joined = publisher.encode() + publisher.verify_key.encode()
    sidecar = module.sign(base64.b64encode(joined).decode())

    status = verify_artifact(catalogue, load_publisher_public_key(), sidecar)
    assert status.verified, status.error


@pytest.mark.parametrize(
    "secret, fragment",
    [
        ("not base64 at all !!", "base64"),
        (base64.b64encode(b"too short").decode(), "32"),
    ],
)
def test_a_malformed_secret_says_which_way_it_is_wrong(
    catalogue, publisher, monkeypatch, secret, fragment
):
    """A signing step that fails should say whether the secret is the wrong
    encoding or the wrong length. Both look identical in a CI log otherwise."""
    module = _load_script(monkeypatch, catalogue)

    with pytest.raises(SystemExit) as exit_info:
        module.sign(secret)

    assert fragment in str(exit_info.value)


def test_no_secret_leaves_the_existing_signature_alone(catalogue, monkeypatch, capsys):
    """A fork's run, or a local dry run, must not replace a good signature with
    nothing. Exiting 0 having done nothing is the correct behaviour."""
    module = _load_script(monkeypatch, catalogue)
    sidecar = catalogue.with_suffix(".json.minisig")
    sidecar.write_text("untrusted comment: x\nkey id: y\nsig: z\n", encoding="utf-8")
    monkeypatch.delenv(module.ENV_KEY, raising=False)
    monkeypatch.setattr(sys, "argv", ["sign_community_picks.py"])

    assert module.main() == 0
    assert sidecar.read_text(encoding="utf-8").startswith("untrusted comment: x")
    assert module.ENV_KEY in capsys.readouterr().out
