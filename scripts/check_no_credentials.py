"""Fail a build whose staged output carries the retired bug-report credential.

Until 2026-09-26 every QuillVille build baked a GitHub token into a generated,
gitignored ``quill/_feedback_token.py`` so Report a Bug could file issues through
the ``feedback_hub`` package. The owner retired both: all feedback now goes by
email to support@community-access.org, and no build may ship that token again.

Removing the generator is not enough on its own. The file is gitignored, so a
copy left over from an older build sits invisibly in a developer's checkout,
and every freezer here sweeps the whole ``quill`` package -- PyInstaller's
``collect_all("quill")``, py2app's ``packages=["quill"]``, the portable
builder's copytree. Any of them would quietly ship the stale credential. This
gate is the backstop: it fails the build when one reaches a staged output.

Two entry points:

- ``find_forbidden(root)`` / the CLI walk a directory on disk (a PyInstaller
  onedir, a portable staging tree, a macOS ``.app``) and also look inside every
  ``.zip`` in it, because py2app packs pure-Python packages into
  ``python3XX.zip``.
- ``assert_toc_clean(toc)`` checks a PyInstaller ``Analysis`` TOC (``a.pure``)
  from inside a spec file, since frozen modules live in the PYZ archive where a
  directory walk cannot see them.

Usage::

    python scripts/check_no_credentials.py <staged-dir> [<staged-dir> ...]

Exits 1 naming every offending path.
"""

from __future__ import annotations

import sys
import zipfile
from collections.abc import Iterable
from pathlib import Path, PurePosixPath

#: The retired credential module (source or compiled, any interpreter tag).
_TOKEN_STEM = "_feedback_token"
#: The retired issue-filing package, by import name and distribution name.
_HUB_PACKAGE = "feedback_hub"

#: Module names that must never be frozen into a PyInstaller archive.
FORBIDDEN_MODULE = "quill._feedback_token"


def is_forbidden_part(parts: Iterable[str]) -> bool:
    """True when a relative path (as its components) is a retired artifact."""
    parts = list(parts)
    for part in parts:
        folded = part.casefold()
        if folded == _HUB_PACKAGE or (
            folded.startswith(_HUB_PACKAGE + "-") and folded.endswith(".dist-info")
        ):
            return True
    if not parts:
        return False
    leaf = parts[-1].casefold()
    # _feedback_token.py, _feedback_token.pyc, _feedback_token.cpython-313.pyc
    return leaf.split(".", 1)[0] == _TOKEN_STEM and leaf.endswith((".py", ".pyc"))


def _zip_offenders(archive: Path) -> list[str]:
    try:
        with zipfile.ZipFile(archive) as zf:
            names = zf.namelist()
    except (zipfile.BadZipFile, OSError):
        return []
    return [n for n in names if is_forbidden_part(PurePosixPath(n).parts)]


def find_forbidden(root: Path) -> list[str]:
    """Every retired-credential artifact under ``root``, as display strings."""
    root = Path(root)
    found: list[str] = []
    if not root.exists():
        return found
    for path in sorted(root.rglob("*")):
        rel = path.relative_to(root)
        if is_forbidden_part(rel.parts):
            # Report a package directory once, not every file under it.
            if not any(is_forbidden_part(rel.parts[:i]) for i in range(1, len(rel.parts))):
                found.append(rel.as_posix())
            continue
        if path.is_file() and path.suffix.casefold() == ".zip":
            found.extend(f"{rel.as_posix()}!{name}" for name in _zip_offenders(path))
    return found


def is_forbidden_module(name: str) -> bool:
    """True for the credential module or anything in the feedback_hub package."""
    return name == FORBIDDEN_MODULE or name == _HUB_PACKAGE or name.startswith(_HUB_PACKAGE + ".")


def assert_toc_clean(toc: Iterable[object]) -> None:
    """Raise SystemExit when a PyInstaller TOC would freeze a retired module.

    ``toc`` is ``a.pure`` (entries are ``(name, path, typecode)`` tuples).
    """
    leaked = sorted({
        str(entry[0])  # type: ignore[index]
        for entry in toc
        if is_forbidden_module(str(entry[0]))  # type: ignore[index]
    })
    if leaked:
        raise SystemExit(
            "Refusing to build: the retired bug-report credential would be frozen in: "
            + ", ".join(leaked)
            + ". Delete quill/_feedback_token.py from the checkout and uninstall "
            "feedback-hub from the build environment (feedback is email-only since "
            "2026-09-26)."
        )


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if not args:
        print("usage: check_no_credentials.py <staged-dir> [<staged-dir> ...]", file=sys.stderr)
        return 2
    failed = False
    for arg in args:
        offenders = find_forbidden(Path(arg))
        if offenders:
            failed = True
            print(f"Retired bug-report credential found in {arg}:", file=sys.stderr)
            for item in offenders:
                print(f"  - {item}", file=sys.stderr)
    if failed:
        print(
            "No QuillVille build may ship quill/_feedback_token.py or feedback_hub "
            "(feedback is email-only since 2026-09-26). Delete the stale file from "
            "the checkout and uninstall feedback-hub, then rebuild.",
            file=sys.stderr,
        )
        return 1
    print("No retired bug-report credential in the staged output.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
