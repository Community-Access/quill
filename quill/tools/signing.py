"""Ed25519 / minisign-shaped signing primitive for QUILL artifacts.

Sidecar convention: every signed artifact has a ``.minisig`` next to it::

    myartifact.qvp.json
    myartifact.qvp.json.minisig     <-- text, minisign-shaped

Single global publisher key. The bundled public key is the
Community-Access publisher key (``ca-pubkey-2026``); the corresponding
private key is NOT in the repo. The Hub reads its public key from
``quillin-hub/quill-pub.key`` (env override: ``SIGNING_PUBLIC_KEY_PATH``).

Threat model:

- tampered Hub download -> fails signature check
- MITM on the storefront -> fails signature check
- malicious Quillin submission without a signature -> fails signature check

Threat model this does NOT cover:

- author identity (no PKI chain)
- who downloaded what (no privacy layer)
- executable code (covered by the macOS / Windows code-signing runbooks)
"""

from __future__ import annotations

import argparse
import base64
import sys
from dataclasses import dataclass
from pathlib import Path

from nacl import signing as nacl_signing
from nacl.exceptions import BadSignatureError

SIGNATURE_SUFFIX = ".minisig"
KEY_ID = "ca-pubkey-2026"

_DEFAULT_PUBKEY_PATH = Path(__file__).resolve().parent.parent.parent / "quill-pub.key"
_HUB_PUBKEY_PATH = Path(__file__).resolve().parent.parent.parent / "quillin-hub" / "quill-pub.key"


def _read_bundled_public_key() -> str:
    for candidate in (_DEFAULT_PUBKEY_PATH, _HUB_PUBKEY_PATH):
        if candidate.exists():
            return candidate.read_text(encoding="utf-8").strip()
    return ""


PUBLIC_KEY_B64: str = _read_bundled_public_key()


@dataclass(frozen=True)
class SignatureStatus:
    """Result of a signature check. Always returned; never raises."""

    signed: bool
    verified: bool
    signer_key_id: str | None
    error: str | None


def _resolve_pubkey_path() -> Path:
    import os

    env_path = os.environ.get("SIGNING_PUBLIC_KEY_PATH")
    if env_path and Path(env_path).exists():
        return Path(env_path)
    repo_root = Path(__file__).resolve().parent.parent.parent
    candidates = [
        repo_root / "quill-pub.key",
        repo_root / "quillin-hub" / "quill-pub.key",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    raise FileNotFoundError(
        "No publisher public key found. Expected quill-pub.key, "
        "quillin-hub/quill-pub.key, or SIGNING_PUBLIC_KEY_PATH."
    )


def load_publisher_public_key() -> nacl_signing.VerifyKey:
    """Load the bundled publisher public key."""
    return load_publisher_public_key_from(_resolve_pubkey_path())


def load_publisher_public_key_from(path: Path) -> nacl_signing.VerifyKey:
    raw = base64.b64decode(path.read_text(encoding="utf-8").strip())
    if len(raw) != 32:
        raise ValueError(f"Public key in {path} is not 32 bytes (got {len(raw)}).")
    return nacl_signing.VerifyKey(raw)


def sidecar_path(artifact_path: Path) -> Path:
    """Return the sidecar path for an artifact."""
    return artifact_path.with_suffix(artifact_path.suffix + SIGNATURE_SUFFIX)


def is_signed(artifact_path: Path) -> bool:
    return sidecar_path(artifact_path).exists()


def read_minisig(sidecar: Path) -> tuple[bytes, str]:
    """Read a minisig-shaped sidecar. Returns (signature_bytes, key_id)."""
    lines = sidecar.read_text(encoding="utf-8").splitlines()
    if (
        len(lines) < 3
        or not lines[0].startswith("untrusted comment:")
        or not lines[1].startswith("key id:")
        or not lines[2].startswith("sig: ")
    ):
        raise ValueError(f"{sidecar} is not a minisig-shaped signature file.")
    key_id = lines[1].split(":", 1)[1].strip()
    sig_b64 = lines[2].split(":", 1)[1].strip()
    return base64.b64decode(sig_b64), key_id


def write_minisig(sidecar: Path, signature: bytes, key_id: str) -> None:
    """Write a minisig-shaped sidecar next to the artifact."""
    if len(signature) != 64:
        raise ValueError(f"Ed25519 signature must be 64 bytes (got {len(signature)}).")
    body = (
        "untrusted comment: quill artifact signature\n"
        f"key id: {key_id}\n"
        f"sig: {base64.b64encode(signature).decode()}\n"
    )
    sidecar.write_text(body, encoding="utf-8")


def sign_artifact(
    artifact_path: Path,
    secret_key: nacl_signing.SigningKey,
    *,
    key_id: str = KEY_ID,
) -> Path:
    """Sign an artifact with a secret key. Returns the sidecar path."""
    data = artifact_path.read_bytes()
    signature = secret_key.sign(data).signature
    sidecar = sidecar_path(artifact_path)
    write_minisig(sidecar, signature, key_id)
    return sidecar


def verify_artifact(
    artifact_path: Path,
    public_key: nacl_signing.VerifyKey | None = None,
    sidecar: Path | None = None,
) -> SignatureStatus:
    """Verify a sidecar signature. Fail-closed: never raises."""
    sidecar_path_resolved = sidecar if sidecar is not None else sidecar_path(artifact_path)
    if not sidecar_path_resolved.exists():
        return SignatureStatus(False, False, None, "no sidecar .minisig")
    try:
        sig, kid = read_minisig(sidecar_path_resolved)
    except (OSError, ValueError) as exc:
        return SignatureStatus(True, False, None, f"unreadable sidecar: {exc}")
    if public_key is None:
        try:
            public_key = load_publisher_public_key()
        except (FileNotFoundError, ValueError) as exc:
            return SignatureStatus(True, False, None, f"public key unavailable: {exc}")
    try:
        public_key.verify(artifact_path.read_bytes(), sig)
    except BadSignatureError:
        return SignatureStatus(True, False, kid, "signature does not match")
    except (OSError, ValueError) as exc:
        return SignatureStatus(True, False, kid, f"verification error: {exc}")
    return SignatureStatus(True, True, kid, None)


def signature_status(artifact_path: Path, sidecar: Path | None = None) -> SignatureStatus:
    """Public alias for ``verify_artifact`` with the default key.

    Resolves the public key at call time: ``SIGNING_PUBLIC_KEY_PATH`` env
    var (Hub deploy + smoke test), else the in-memory ``PUBLIC_KEY_B64``
    (tests that monkeypatched it), else the bundled key file.
    The ``sidecar`` argument lets callers point at an explicitly-uploaded
    sidecar (e.g. when the artifact lives in a different directory after
    Flask saved the upload).
    """
    import os

    env_path = os.environ.get("SIGNING_PUBLIC_KEY_PATH")
    if env_path and Path(env_path).exists():
        try:
            vk = load_publisher_public_key_from(Path(env_path))
        except ValueError as exc:
            return SignatureStatus(True, False, None, f"public key unavailable: {exc}")
        return verify_artifact(artifact_path, public_key=vk, sidecar=sidecar)
    if PUBLIC_KEY_B64:
        try:
            vk = load_publisher_public_key_from_value(PUBLIC_KEY_B64)
        except ValueError as exc:
            return SignatureStatus(True, False, None, f"public key unavailable: {exc}")
        return verify_artifact(artifact_path, public_key=vk, sidecar=sidecar)
    return verify_artifact(artifact_path, public_key=None, sidecar=sidecar)


def load_publisher_public_key_from_value(b64: str) -> nacl_signing.VerifyKey:
    raw = base64.b64decode(b64.strip())
    if len(raw) != 32:
        raise ValueError(f"Public key must be 32 bytes (got {len(raw)}).")
    return nacl_signing.VerifyKey(raw)


def _secret_key_to_b64(sk: nacl_signing.SigningKey) -> str:
    """Serialize a 32-byte seed + 32-byte public key as 64-byte base64."""
    return base64.b64encode(sk.encode() + sk.verify_key.encode()).decode()


def _b64_to_secret_key(b64: str) -> nacl_signing.SigningKey:
    raw = base64.b64decode(b64.strip())
    if len(raw) != 64:
        raise ValueError(f"Secret key must be 64 bytes (32 seed + 32 pub), got {len(raw)}.")
    return nacl_signing.SigningKey(raw[:32])


def _load_secret_key(path: Path) -> nacl_signing.SigningKey:
    return _b64_to_secret_key(path.read_text(encoding="utf-8").strip().splitlines()[-1])


def _cmd_keygen(args: argparse.Namespace) -> int:
    pub_path = Path(args.pub) if args.pub else Path("quill-pub.key")
    priv_path = Path(args.priv) if args.priv else Path("quill-priv.key")
    sk = nacl_signing.SigningKey.generate()
    pub_path.write_text(base64.b64encode(bytes(sk.verify_key)).decode() + "\n", encoding="utf-8")
    priv_path.write_text(
        "untrusted comment: quill signing key - do not commit\n" + _secret_key_to_b64(sk) + "\n",
        encoding="utf-8",
    )
    print(f"Public key  -> {pub_path}")
    print(f"Private key -> {priv_path}")
    print("Add the private key to a password manager. Never commit it.")
    return 0


def _cmd_sign(args: argparse.Namespace) -> int:
    sk = _load_secret_key(Path(args.secret_key))
    sidecar = sign_artifact(Path(args.path), sk, key_id=args.key_id)
    print(f"Wrote {sidecar}")
    return 0


def _cmd_verify(args: argparse.Namespace) -> int:
    artifact = Path(args.path)
    if not artifact.exists():
        print(f"Error: '{artifact}' not found.", file=sys.stderr)
        return 2
    pub = load_publisher_public_key_from(Path(args.public_key)) if args.public_key else None
    status = verify_artifact(artifact, public_key=pub)
    if not status.signed:
        print("unsigned: no sidecar .minisig", file=sys.stderr)
        return 2
    if not status.verified:
        print(f"signature invalid: {status.error}", file=sys.stderr)
        return 1
    print(f"verified: signed by {status.signer_key_id}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m quill.tools.signing",
        description="Ed25519 / minisign-shaped signing for QUILL artifacts.",
    )
    sub = parser.add_subparsers(dest="command", required=True)
    p_keygen = sub.add_parser("keygen", help="Generate a new keypair.")
    p_keygen.add_argument("--pub", help="Public key output path.")
    p_keygen.add_argument("--priv", help="Private key output path.")
    p_sign = sub.add_parser("sign", help="Sign an artifact.")
    p_sign.add_argument("path", help="Artifact to sign.")
    p_sign.add_argument("--secret-key", required=True, help="Path to secret key.")
    p_sign.add_argument("--key-id", default=KEY_ID)
    p_verify = sub.add_parser("verify", help="Verify an artifact signature.")
    p_verify.add_argument("path", help="Artifact to verify.")
    p_verify.add_argument("--public-key", help="Path to public key (default: bundled).")
    args = parser.parse_args(argv)
    if args.command == "keygen":
        return _cmd_keygen(args)
    if args.command == "sign":
        return _cmd_sign(args)
    if args.command == "verify":
        return _cmd_verify(args)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
