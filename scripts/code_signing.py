"""Authenticode code signing for QUILL Windows builds (Azure Trusted Signing).

This is *operating-system code signing* -- the Authenticode signature Windows
checks on an .exe/.dll and on the installer's SmartScreen prompt. It is a
DIFFERENT thing from ``quill/tools/signing.py``, which is Ed25519 *provenance*
signing (minisign sidecars) for Quillins and other Hub artifacts. Neither
replaces the other; see ``docs/code-signing.md``.

Signing is done through **Azure Trusted Signing** (formerly Azure Code
Signing). There is no PFX or private key on disk: ``signtool.exe`` calls a
Microsoft-supplied signing dlib (``Azure.CodeSigning.Dlib.dll``) that submits a
digest to the account's ``wus2.codesigning.azure.net`` endpoint and gets back a
short-lived certificate. Authentication is the ambient Azure credential -- an
``az login`` session on a dev box, or a workload identity / service principal in
CI (``DefaultAzureCredential``). The account + certificate profile live in a
small ``metadata.json``::

    {
      "Endpoint": "https://wus2.codesigning.azure.net/",
      "CodeSigningAccountName": "JeffBishopSigningCert",
      "CertificateProfileName": "QUILL"
    }

Design rules:

* **Opt-in.** A build signs only when ``QUILL_SIGN=1`` (or ``--require`` / an
  explicit ``sign_paths(...)`` call). A plain build is byte-for-byte unchanged,
  so CI, offline builds, and contributor clones never need the cert.
* **Fail-open by default, fail-closed on request.** When signing *is* requested
  but the toolchain or credential is unavailable, the build logs a warning and
  continues -- UNLESS ``QUILL_SIGN_REQUIRED=1``, which turns any signing failure
  into a hard error (use this in the release pipeline).
* **No shell.** ``signtool`` is always invoked with an argv list via
  ``subprocess``. Passing ``/fd``-style switches through a shell (notably Git
  Bash / MSYS) mangles them into paths and yields the misleading "No file digest
  algorithm specified" error.

CLI::

    python scripts/code_signing.py doctor                 # check the toolchain
    python scripts/code_signing.py ensure-dlib            # stage the signing dlib
    python scripts/code_signing.py sign a.exe b.dll       # sign specific files
    python scripts/code_signing.py sign-tree dist\\portable   # sign every exe/dll under a tree
    python scripts/code_signing.py verify a.exe           # verify an Authenticode signature
"""

from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import subprocess
import sys
import urllib.request
import zipfile
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent

# The signing account + certificate profile. The repo ships a metadata.json at
# its root; a build may point elsewhere with QUILL_SIGN_METADATA.
DEFAULT_METADATA_PATH = _REPO_ROOT / "metadata.json"

# Microsoft's public timestamp authority for Trusted Signing. Timestamping means
# a signature stays valid after the short-lived signing certificate expires.
DEFAULT_TIMESTAMP_URL = "http://timestamp.acs.microsoft.com"

# Pinned Microsoft.Trusted.Signing.Client NuGet package. It carries the
# Azure.CodeSigning.Dlib.dll that signtool loads via /dlib. Pinned + SHA-256
# verified exactly like every other build dependency (fetch_build_deps.py): the
# build fails loudly rather than loading an unverified signing shim.
TRUSTED_SIGNING_CLIENT_VERSION = "1.0.95"
TRUSTED_SIGNING_CLIENT_URL = (
    "https://api.nuget.org/v3-flatcontainer/microsoft.trusted.signing.client/"
    f"{TRUSTED_SIGNING_CLIENT_VERSION}/"
    f"microsoft.trusted.signing.client.{TRUSTED_SIGNING_CLIENT_VERSION}.nupkg"
)
TRUSTED_SIGNING_CLIENT_SHA256 = "3bfcf1e0a3cb42af1692f0a8ed45c15de070c2de86f28a59b2795d904d8a920f"

# File types worth signing when signing a whole tree. Authenticode applies to PE
# binaries; catalogs and scripts are out of scope here.
DEFAULT_SIGN_PATTERNS = ("*.exe", "*.dll")

# A verification is over the embedded Authenticode signature only. signtool's
# /pa uses the Default Authentication Policy, which is what SmartScreen and the
# UAC prompt evaluate.


class SigningError(RuntimeError):
    """A signing or verification step failed."""


@dataclass(frozen=True)
class SigningConfig:
    """Everything a signtool invocation needs, resolved once per build."""

    signtool: Path
    dlib: Path
    metadata: Path
    timestamp_url: str = DEFAULT_TIMESTAMP_URL
    extra_args: tuple[str, ...] = field(default_factory=tuple)


def signing_requested() -> bool:
    """True when the environment asks builds to sign (``QUILL_SIGN=1``)."""
    return _env_flag("QUILL_SIGN")


def signing_required() -> bool:
    """True when a signing failure must abort the build (``QUILL_SIGN_REQUIRED=1``)."""
    return _env_flag("QUILL_SIGN_REQUIRED")


def _env_flag(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in {"1", "true", "yes", "on"}


def metadata_path() -> Path:
    override = os.environ.get("QUILL_SIGN_METADATA", "").strip()
    return Path(override) if override else DEFAULT_METADATA_PATH


def deps_root() -> Path:
    """Cache dir for staged signing tooling, shared with fetch_build_deps.py."""
    override = os.environ.get("QUILL_BUILD_DEPS_DIR", "").strip()
    root = Path(override) if override else _REPO_ROOT / "build" / "deps"
    return root / "trusted-signing"


def default_patterns() -> tuple[str, ...]:
    """File globs a tree-sign covers, overridable with ``QUILL_SIGN_PATTERNS``.

    ``QUILL_SIGN_PATTERNS`` is a comma/semicolon-separated list, e.g.
    ``*.exe,*.dll,*.pyd``. Widening it to every PE (including CPython extension
    modules) is thorough but costs one remote signing round-trip per file, so the
    default stays ``*.exe, *.dll``.
    """
    raw = os.environ.get("QUILL_SIGN_PATTERNS", "").strip()
    if not raw:
        return DEFAULT_SIGN_PATTERNS
    parts = [p.strip() for p in raw.replace(";", ",").split(",") if p.strip()]
    return tuple(parts) or DEFAULT_SIGN_PATTERNS


# -- toolchain discovery ------------------------------------------------------


def _windows_kits_roots() -> list[Path]:
    roots: list[Path] = []
    for var in ("ProgramFiles(x86)", "ProgramFiles", "ProgramW6432"):
        value = os.environ.get(var, "").strip()
        if value:
            roots.append(Path(value) / "Windows Kits" / "10" / "bin")
    roots.append(Path(r"C:\Program Files (x86)\Windows Kits\10\bin"))
    roots.append(Path(r"C:\Program Files\Windows Kits\10\bin"))
    seen: set[str] = set()
    unique: list[Path] = []
    for root in roots:
        key = str(root).lower()
        if key not in seen:
            seen.add(key)
            unique.append(root)
    return unique


def find_signtool() -> Path | None:
    """Locate signtool.exe -- newest Windows SDK build first, then PATH.

    The Windows Kits layout is ``bin\\<sdk-version>\\x64\\signtool.exe``; there
    can be several SDK versions installed side by side, so prefer the highest.
    """
    best: tuple[tuple[int, ...], Path] | None = None
    for kits_bin in _windows_kits_roots():
        if not kits_bin.is_dir():
            continue
        for version_dir in kits_bin.iterdir():
            candidate = version_dir / "x64" / "signtool.exe"
            if candidate.is_file():
                key = _version_key(version_dir.name)
                if best is None or key > best[0]:
                    best = (key, candidate)
    if best is not None:
        return best[1]
    discovered = shutil.which("signtool") or shutil.which("signtool.exe")
    return Path(discovered) if discovered else None


def _version_key(name: str) -> tuple[int, ...]:
    parts: list[int] = []
    for chunk in name.split("."):
        try:
            parts.append(int(chunk))
        except ValueError:
            parts.append(0)
    return tuple(parts)


def _download_verified(url: str, dest: Path, *, sha256: str) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    hasher = hashlib.sha256()
    tmp = dest.with_suffix(dest.suffix + ".part")
    # Trusted host (api.nuget.org); this mirrors scripts/build_windows_distribution.py
    # and scripts/fetch_build_deps.py, and is build-time only (never shipped).
    with urllib.request.urlopen(url) as response, tmp.open("wb") as handle:  # noqa: S310
        while True:
            block = response.read(1 << 16)
            if not block:
                break
            hasher.update(block)
            handle.write(block)
    actual = hasher.hexdigest()
    if actual != sha256:
        tmp.unlink(missing_ok=True)
        raise SigningError(f"SHA-256 mismatch for {url}\n  expected {sha256}\n  got      {actual}")
    tmp.replace(dest)


def _dlib_path() -> Path:
    """Expected on-disk path of the extracted x64 signing dlib."""
    return (
        deps_root() / TRUSTED_SIGNING_CLIENT_VERSION / "bin" / "x64" / "Azure.CodeSigning.Dlib.dll"
    )


def ensure_dlib(*, force: bool = False) -> Path:
    """Return the path to Azure.CodeSigning.Dlib.dll, staging it if needed.

    Downloads and SHA-256-verifies the pinned Microsoft.Trusted.Signing.Client
    NuGet package (a zip) into ``build/deps/trusted-signing/`` and extracts the
    x64 dlib. Re-running is cheap: an already-extracted dlib is reused.
    """
    cache = deps_root()
    dlib = _dlib_path()
    if dlib.is_file() and not force:
        return dlib
    nupkg = cache / f"microsoft.trusted.signing.client.{TRUSTED_SIGNING_CLIENT_VERSION}.nupkg"
    _download_verified(TRUSTED_SIGNING_CLIENT_URL, nupkg, sha256=TRUSTED_SIGNING_CLIENT_SHA256)
    extract_root = cache / TRUSTED_SIGNING_CLIENT_VERSION
    if extract_root.exists():
        shutil.rmtree(extract_root)
    with zipfile.ZipFile(nupkg) as archive:
        # Extract only the bin/ tree we need (the package also carries nuspec,
        # docs, and other-arch dlls we do not load).
        for member in archive.namelist():
            normalized = member.replace("\\", "/")
            if normalized.startswith("bin/") and not normalized.endswith("/"):
                archive.extract(member, extract_root)
    if not dlib.is_file():
        raise SigningError(f"Azure.CodeSigning.Dlib.dll not found in {nupkg} after extraction.")
    return dlib


def azure_credential_available() -> bool:
    """Best-effort check that an Azure credential is present (``az account show``).

    Not authoritative -- CI may use a workload identity that ``az`` cannot see --
    so it never blocks on its own; it only sharpens the ``doctor`` report and the
    warning message when signing is skipped.
    """
    az = shutil.which("az")
    if not az:
        return False
    try:
        result = subprocess.run(
            [az, "account", "show", "--output", "none"],
            capture_output=True,
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return result.returncode == 0


# -- configuration ------------------------------------------------------------


def resolve_config(
    *,
    metadata: Path | None = None,
    timestamp_url: str = DEFAULT_TIMESTAMP_URL,
    stage_dlib: bool = True,
) -> SigningConfig:
    """Build a :class:`SigningConfig`, staging the dlib and locating signtool.

    Raises :class:`SigningError` with an actionable message when a prerequisite
    is missing; callers that want fail-open behaviour use :func:`sign_paths`,
    which catches this.
    """
    signtool = find_signtool()
    if signtool is None:
        raise SigningError(
            "signtool.exe not found. Install the Windows 10/11 SDK "
            "(Windows Kits\\10\\bin\\<version>\\x64\\signtool.exe) or put it on PATH."
        )
    meta = metadata or metadata_path()
    if not meta.is_file():
        raise SigningError(
            f"Signing metadata not found at {meta}. Create metadata.json with the "
            "Trusted Signing Endpoint, CodeSigningAccountName, and "
            "CertificateProfileName, or set QUILL_SIGN_METADATA."
        )
    dlib = ensure_dlib() if stage_dlib else _dlib_path()
    if not dlib.is_file():
        raise SigningError(
            "Azure.CodeSigning.Dlib.dll is not staged. Run "
            "`python scripts/code_signing.py ensure-dlib`."
        )
    return SigningConfig(signtool=signtool, dlib=dlib, metadata=meta, timestamp_url=timestamp_url)


# -- signing + verification ---------------------------------------------------


def _sign_command(config: SigningConfig, files: Sequence[Path]) -> list[str]:
    return [
        str(config.signtool),
        "sign",
        "/v",
        "/fd",
        "SHA256",
        "/tr",
        config.timestamp_url,
        "/td",
        "SHA256",
        "/dlib",
        str(config.dlib),
        "/dmdf",
        str(config.metadata),
        *config.extra_args,
        *(str(f) for f in files),
    ]


def sign_files(files: Iterable[Path], config: SigningConfig, *, batch: int = 50) -> list[Path]:
    """Authenticode-sign each file. Returns the list actually signed.

    signtool accepts many files per call; batching keeps one huge command line
    from overflowing while still amortising process startup. Each file still
    gets its own remote digest submission inside the dlib.
    """
    resolved = [Path(f) for f in files]
    missing = [f for f in resolved if not f.is_file()]
    if missing:
        raise SigningError(f"Cannot sign missing files: {', '.join(map(str, missing))}")
    if not resolved:
        return []
    for start in range(0, len(resolved), batch):
        chunk = resolved[start : start + batch]
        command = _sign_command(config, chunk)
        result = subprocess.run(command, capture_output=True, text=True, check=False)
        if result.returncode != 0:
            raise SigningError(
                "signtool sign failed (exit "
                f"{result.returncode}).\n{_tail(result.stdout)}\n{_tail(result.stderr)}"
            )
    return resolved


def collect_files(root: Path, patterns: Sequence[str] = DEFAULT_SIGN_PATTERNS) -> list[Path]:
    """Every file under *root* matching any of *patterns* (recursive, sorted)."""
    found: set[Path] = set()
    for pattern in patterns:
        found.update(p for p in root.rglob(pattern) if p.is_file())
    return sorted(found)


def sign_tree(
    root: Path, config: SigningConfig, *, patterns: Sequence[str] = DEFAULT_SIGN_PATTERNS
) -> list[Path]:
    """Sign every matching binary under *root*."""
    files = collect_files(root, patterns)
    return sign_files(files, config)


def verify_file(path: Path) -> bool:
    """True when *path* carries a valid embedded Authenticode signature."""
    signtool = find_signtool()
    if signtool is None:
        raise SigningError("signtool.exe not found; cannot verify.")
    result = subprocess.run(
        [str(signtool), "verify", "/pa", str(path)],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.returncode == 0


def _tail(text: str, lines: int = 12) -> str:
    return "\n".join((text or "").strip().splitlines()[-lines:])


# -- build-facing convenience -------------------------------------------------


def sign_paths(
    paths: Iterable[Path],
    *,
    label: str = "artifacts",
    patterns: Sequence[str] | None = None,
    require: bool | None = None,
) -> list[Path]:
    """Sign files and/or trees, honouring the opt-in / fail-open contract.

    This is the function build scripts call. Behaviour:

    * When signing is not requested (``QUILL_SIGN`` unset and ``require`` not
      True), do nothing and return ``[]`` -- a plain build is unchanged.
    * When requested, sign every path (directories are walked with *patterns*).
    * On any failure, re-raise if signing is required (``require=True`` or
      ``QUILL_SIGN_REQUIRED=1``); otherwise log a warning and return what was
      signed so far.

    Passing ``require=True`` forces signing on even without ``QUILL_SIGN`` -- the
    CLI's ``--require`` and an explicit release step use this.
    """
    force = bool(require)
    if not force and not signing_requested():
        print(f"[sign] skipped ({label}): set QUILL_SIGN=1 to enable code signing.")
        return []
    effective_patterns = tuple(patterns) if patterns is not None else default_patterns()
    must_succeed = force or signing_required()
    try:
        config = resolve_config()
    except SigningError as exc:
        return _handle_failure(exc, must_succeed, label)

    targets: list[Path] = []
    for path in paths:
        path = Path(path)
        if path.is_dir():
            targets.extend(collect_files(path, effective_patterns))
        elif path.is_file():
            targets.append(path)
        else:
            msg = SigningError(f"Nothing to sign at {path}")
            if must_succeed:
                raise msg
            print(f"[sign] warning ({label}): {msg}")
    targets = sorted(set(targets))
    if not targets:
        print(f"[sign] nothing to sign ({label}).")
        return []
    try:
        signed = sign_files(targets, config)
    except SigningError as exc:
        return _handle_failure(exc, must_succeed, label)
    print(f"[sign] signed {len(signed)} file(s) ({label}).")
    return signed


def _handle_failure(exc: SigningError, must_succeed: bool, label: str) -> list[Path]:
    if must_succeed:
        raise exc
    hint = ""
    if not azure_credential_available():
        hint = " (no Azure credential found -- run `az login`)"
    print(f"[sign] warning ({label}): signing skipped -- {exc}{hint}")
    return []


# -- CLI ----------------------------------------------------------------------


def _cmd_doctor(_: argparse.Namespace) -> int:
    signtool = find_signtool()
    meta = metadata_path()
    dlib = _dlib_path()
    az_state = "present" if azure_credential_available() else "not found (az login)"
    print("Authenticode signing toolchain:")
    print(f"  signtool.exe   : {signtool or 'NOT FOUND (install the Windows SDK)'}")
    print(f"  metadata.json  : {meta} {'OK' if meta.is_file() else 'MISSING'}")
    print(f"  signing dlib   : {dlib if dlib.is_file() else 'not staged (run ensure-dlib)'}")
    print(f"  az credential  : {az_state}")
    print(f"  QUILL_SIGN     : {'on' if signing_requested() else 'off'}")
    print(f"  QUILL_SIGN_REQUIRED: {'on' if signing_required() else 'off'}")
    ready = bool(signtool) and meta.is_file()
    print("Ready to sign." if ready else "Not ready -- resolve the items marked above.")
    return 0 if ready else 1


def _cmd_ensure_dlib(args: argparse.Namespace) -> int:
    dlib = ensure_dlib(force=args.force)
    print(dlib)
    return 0


def _cmd_sign(args: argparse.Namespace) -> int:
    config = resolve_config()
    signed = sign_files([Path(p) for p in args.paths], config)
    for path in signed:
        print(f"signed: {path}")
    return 0


def _cmd_sign_tree(args: argparse.Namespace) -> int:
    config = resolve_config()
    patterns = tuple(args.pattern) if args.pattern else default_patterns()
    signed = sign_tree(Path(args.root), config, patterns=patterns)
    print(f"signed {len(signed)} file(s) under {args.root}")
    for path in signed:
        print(f"  {path}")
    return 0


def _cmd_sign_build(args: argparse.Namespace) -> int:
    """Opt-in / fail-open signing for build scripts.

    Unlike ``sign`` / ``sign-tree`` (which fail closed), this honours the
    ``QUILL_SIGN`` opt-in and the ``QUILL_SIGN_REQUIRED`` / ``--require``
    fail-closed switch, so a release script can call it unconditionally: it is a
    no-op on a plain build and only aborts when signing was demanded and failed.
    Accepts files and directories (directories are walked with the default
    patterns / ``QUILL_SIGN_PATTERNS``).
    """
    sign_paths(
        [Path(p) for p in args.paths],
        label=args.label,
        require=args.require or None,
    )
    return 0


def _cmd_verify(args: argparse.Namespace) -> int:
    ok = True
    for raw in args.paths:
        path = Path(raw)
        good = verify_file(path)
        ok = ok and good
        print(f"{'valid  ' if good else 'INVALID'}: {path}")
    return 0 if ok else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python scripts/code_signing.py",
        description="Authenticode code signing via Azure Trusted Signing.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("doctor", help="Report toolchain/credential readiness.")

    p_dlib = sub.add_parser("ensure-dlib", help="Download + stage the signing dlib.")
    p_dlib.add_argument("--force", action="store_true", help="Re-download even if present.")

    p_sign = sub.add_parser("sign", help="Sign specific files.")
    p_sign.add_argument("paths", nargs="+", help="Files to sign.")

    p_tree = sub.add_parser("sign-tree", help="Sign every matching binary under a directory.")
    p_tree.add_argument("root", help="Directory to walk.")
    p_tree.add_argument(
        "--pattern", action="append", help="Glob to sign (repeatable; default *.exe, *.dll)."
    )

    p_build = sub.add_parser(
        "sign-build", help="Opt-in/fail-open signing of files+dirs for build scripts."
    )
    p_build.add_argument("paths", nargs="+", help="Files or directories to sign.")
    p_build.add_argument("--label", default="build", help="Label used in log lines.")
    p_build.add_argument(
        "--require",
        action="store_true",
        help="Force signing on and fail the build if it cannot sign.",
    )

    p_verify = sub.add_parser("verify", help="Verify an Authenticode signature.")
    p_verify.add_argument("paths", nargs="+", help="Files to verify.")

    args = parser.parse_args(argv)
    handlers = {
        "doctor": _cmd_doctor,
        "ensure-dlib": _cmd_ensure_dlib,
        "sign": _cmd_sign,
        "sign-tree": _cmd_sign_tree,
        "sign-build": _cmd_sign_build,
        "verify": _cmd_verify,
    }
    try:
        return handlers[args.command](args)
    except SigningError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
