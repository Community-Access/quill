"""Regression tests for #919: quill.tools.signing must not crash a routine
UI action (viewing a Quillin's details in the Quillins Manager) on a build
that never bundles PyNaCl (a dev/CI-only dependency, not a shipping one).

Deliberately does NOT ``pytest.importorskip("nacl")`` like test_signing.py --
these tests exist specifically to prove behavior when nacl is unavailable,
so they must run regardless of whether this environment happens to have it
installed. ``sys.modules["nacl"] = None`` is the standard trick to make any
subsequent ``import nacl`` (or ``from nacl import ...``) raise
``ModuleNotFoundError``, exactly as it would on a build that never installed
the package at all.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def _block_nacl(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in list(sys.modules):
        if name == "nacl" or name.startswith("nacl."):
            monkeypatch.delitem(sys.modules, name, raising=False)
    monkeypatch.setitem(sys.modules, "nacl", None)


def test_module_imports_without_nacl_installed() -> None:
    """The #919 crash: `from quill.tools.signing import signature_status`
    itself raised ModuleNotFoundError, before any function even ran, because
    the old code imported nacl unconditionally at module level."""
    import importlib

    import quill.tools.signing as signing_module

    importlib.reload(signing_module)
    assert hasattr(signing_module, "signature_status")


def test_signature_status_degrades_gracefully_without_nacl(tmp_path: Path) -> None:
    import importlib

    import quill.tools.signing as signing_module

    importlib.reload(signing_module)

    artifact = tmp_path / "thing.qvp.json"
    artifact.write_text("{}", encoding="utf-8")
    sidecar = artifact.with_suffix(artifact.suffix + signing_module.SIGNATURE_SUFFIX)
    sidecar.write_text(
        "untrusted comment: quill artifact signature\n"
        "key id: ca-pubkey-2026\n"
        "sig: " + "A" * 88 + "\n",
        encoding="utf-8",
    )

    status = signing_module.signature_status(artifact)
    assert status.verified is False
    assert status.error is not None


def test_verify_artifact_unsigned_needs_no_nacl_at_all(tmp_path: Path) -> None:
    """An unsigned artifact (the common case -- most Quillins carry no
    sidecar) never even touches nacl, signed or not."""
    import importlib

    import quill.tools.signing as signing_module

    importlib.reload(signing_module)

    artifact = tmp_path / "thing.qvp.json"
    artifact.write_text("{}", encoding="utf-8")

    status = signing_module.verify_artifact(artifact)
    assert status.signed is False
    assert status.verified is False


def test_quillin_signature_detail_text_does_not_crash_without_nacl(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The exact #919 call site: main_frame_quillins.py's signature-status
    block must degrade to a status line, never raise, when nacl is absent."""
    import importlib

    import quill.tools.signing as signing_module

    importlib.reload(signing_module)

    lines: list[str] = []
    try:
        from quill.tools.signing import signature_status

        sig = signature_status(tmp_path / "manifest.json")
        if sig.verified:
            lines.append(f"Signature: verified, signed by {sig.signer_key_id}.")
        elif sig.signed:
            lines.append(f"Signature: invalid ({sig.error or 'does not match publisher key'}).")
        else:
            lines.append("Signature: unsigned. This Quillin is not publisher-attested.")
    except (OSError, ValueError, ImportError) as exc:
        lines.append(f"Signature: check failed ({exc}).")

    assert lines
    assert "crash" not in lines[0].lower()
