"""Generate the family's third-party notices from one catalogue (GATE-NOTICES).

The catalogue is ``quill/data/third_party/components.json`` (with the licence
texts beside it in ``licenses/``); :mod:`quill.core.third_party_notices`
renders it. This tool writes every rendered file and checks them for drift:

* ``docs/legal/THIRD_PARTY_NOTICES.md`` and ``.txt`` -- the family document,
  including the entries that still need review;
* ``docs/legal/THIRD-PARTY-NOTICES-QUILL.txt`` -- the file QUILL's own
  installer and portable zip ship beside ``quill.exe``;
* ``standalone/<app>/THIRD-PARTY-NOTICES.txt`` and ``LICENSE.txt`` -- the files
  each app's installer and portable zip ship beside the program.

``--check`` also fails when a Python distribution named in a committed build
inventory (``standalone/runtime/runtime-inventory.json``,
``standalone/*/portable-inventory.json``) has no catalogue entry: a dependency
that reaches a build without a notice is exactly the gap this exists to close.

``--versions`` compares the catalogue's Python versions with the installed
packages and reports differences. It never fails: the release build, not this
machine, decides what ships, but a long list means the catalogue is stale.

Regenerate::

    python -m quill.tools.build_third_party_notices --write

Check (what the gate runs)::

    python -m quill.tools.build_third_party_notices --check
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from quill.core.third_party_notices import (
    Catalogue,
    load_catalogue,
    render_license_txt,
    render_markdown,
    render_text,
)

_REPO_ROOT = Path(__file__).resolve().parents[2]

FAMILY_MD = _REPO_ROOT / "docs" / "legal" / "THIRD_PARTY_NOTICES.md"
FAMILY_TXT = _REPO_ROOT / "docs" / "legal" / "THIRD_PARTY_NOTICES.txt"
QUILL_TXT = _REPO_ROOT / "docs" / "legal" / "THIRD-PARTY-NOTICES-QUILL.txt"

#: Inventory entries that are not Python distributions: the interpreter's own
#: modules and DLLs (covered by the CPython, OpenSSL, libffi, SQLite and
#: Microsoft runtime entries), QUILL itself, and PyInstaller's archive.
_NOT_A_DISTRIBUTION = {
    "base_library.zip",
    "quill",
    "pywin32.pth",
    "pywin32.version.txt",
    "pywin32.chm",
    "pythoncom",
}
_INTERPRETER = re.compile(
    r"^(_[a-z0-9]+|pyexpat|select|unicodedata|winsound|python3|python314|sqlite3|"
    r"libcrypto-3|libssl-3|libffi-8|vcruntime140|vcruntime140_1|msvcp140|libtommath)"
    r"(\.pyd|\.dll)?$"
)
#: Bundled native libraries that arrive inside a wheel's own folder or beside it,
#: by the stem PyInstaller and delvewheel give them (a content hash follows).
_WHEEL_DLLS = {
    "libde265": "pillow-heif",
    "libheif": "pillow-heif",
    "libx265": "pillow-heif",
    "libgcc-s-seh": "mingw-runtime",
    "libstdc++": "mingw-runtime",
    "libwinpthread": "mingw-runtime",
}
#: Import or folder names that differ from the distribution's name.
_ALIASES = {
    "pil": "pillow",
    "nacl": "pynacl",
    "yaml": "pyyaml",
    "wx": "wxpython",
    "enchant": "pyenchant",
    "docx": "python-docx",
    "pptx": "python-pptx",
    "dateutil": "python-dateutil",
    "prism": "prismatoid",
    "pdfminer": "pdfminer-six",
    "websocket": "websocket-client",
    "win32": "pywin32",
    "win32com": "pywin32",
    "win32comext": "pywin32",
    "pythonwin": "pywin32",
    "pywin32-system32": "pywin32",
    "adodbapi": "pywin32",
    "isapi": "pywin32",
    "winrt": "pywinrt",
    "audioop": "audioop-lts",
    "brotli": "brotli",
    "curl-cffi-libs": "curl-cffi",
    "numpy-libs": "numpy",
    "pypdfium2-raw": "pypdfium2",
    "pypdfium2-cfg": "pypdfium2",
    "pypdfium2-cli": "pypdfium2",
    "pillow-heif": "pillow-heif",
    "sounddevice-data": "sounddevice",
    "soundfile-data": "soundfile",
    "cffi-backend": "cffi",
    "sherpa-onnx-core": "sherpa-onnx",
    "typing-extensions": "typing-extensions",
    "optilabcore-license.txt": "optilab",
    "optilabcore-notice.txt": "optilab",
    "quill-optilab.exe": "optilab",
    "rapidfuzz": "rapidfuzz",
}


def _normalise(name: str) -> str:
    stem = name.lower()
    for suffix in (".py", ".pyd", ".dll"):
        stem = stem.removesuffix(suffix)
    stem = re.sub(r"-[0-9a-f]{32}$", "", stem)
    stem = re.sub(r"[-_.]+", "-", stem).strip("-")
    stem = re.sub(r"-\d+$", "", stem)  # libde265-0, libx265-217, libwinpthread-1
    return stem


def outputs(cat: Catalogue) -> dict[Path, str]:
    """Every generated file and the text it must hold."""
    files: dict[Path, str] = {
        FAMILY_MD: render_markdown(cat),
        FAMILY_TXT: render_text(cat),
        QUILL_TXT: render_text(cat, "quill"),
    }
    for key, meta in cat.products.items():
        folder = meta.get("standalone")
        if not folder:
            continue
        root = _REPO_ROOT / str(folder)
        files[root / "THIRD-PARTY-NOTICES.txt"] = render_text(cat, key)
        files[root / "LICENSE.txt"] = render_license_txt(cat, key)
    return files


def inventory_entries() -> dict[str, set[str]]:
    """Every Python-side entry in the committed build inventories, by file."""
    found: dict[str, set[str]] = {}
    paths = [_REPO_ROOT / "standalone" / "runtime" / "runtime-inventory.json"]
    paths += sorted((_REPO_ROOT / "standalone").glob("*/portable-inventory.json"))
    for path in paths:
        if not path.is_file():
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        entries: set[str] = set()
        for key in ("site-packages", "_internal", "optional"):
            entries |= set(data.get(key, []))
        found[str(path.relative_to(_REPO_ROOT)).replace("\\", "/")] = entries
    return found


def uncatalogued(cat: Catalogue) -> list[str]:
    """Inventory entries with no catalogue entry, as ``file: entry`` lines."""
    known = {item.id for item in cat.components}
    known |= {_normalise(item.pypi) for item in cat.components if item.pypi}
    tool_dirs = {"deno", "ffmpeg", "mpv"}
    missing: list[str] = []
    for source, entries in inventory_entries().items():
        for entry in sorted(entries):
            stem = _normalise(entry)
            if entry.lower() in _NOT_A_DISTRIBUTION or stem in _NOT_A_DISTRIBUTION:
                continue
            if _INTERPRETER.match(entry.lower()) or entry.lower().endswith(".dist-info"):
                continue
            if stem in tool_dirs:
                target = "libmpv" if stem == "mpv" else stem
            elif entry.lower() in _ALIASES:
                target = _ALIASES[entry.lower()]
            elif stem in _ALIASES:
                target = _ALIASES[stem]
            elif stem in _WHEEL_DLLS:
                target = _WHEEL_DLLS[stem]
            elif stem.startswith("winrt-"):
                target = "pywinrt"
            elif stem in ("quill-social",):
                target = "quill-social"
            else:
                target = stem
            if target not in known:
                missing.append(f"{source}: {entry}")
    return missing


def version_drift(cat: Catalogue) -> list[str]:
    """Catalogue versions that differ from the installed package (informational)."""
    import importlib.metadata as metadata

    drift: list[str] = []
    for item in cat.components:
        if not item.pypi:
            continue
        try:
            installed = metadata.version(item.pypi)
        except metadata.PackageNotFoundError:
            drift.append(f"{item.pypi}: catalogue {item.version}, not installed here")
            continue
        if installed != item.version:
            drift.append(f"{item.pypi}: catalogue {item.version}, installed {installed}")
    return drift


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--write", action="store_true", help="regenerate every notices file")
    group.add_argument("--check", action="store_true", help="fail if any file has drifted")
    group.add_argument("--versions", action="store_true", help="report version drift")
    args = parser.parse_args(argv)

    cat = load_catalogue()
    if args.versions:
        drift = version_drift(cat)
        for line in drift:
            print(line)
        print(f"{len(drift)} version difference(s) against this machine's packages.")
        return 0
    files = outputs(cat)
    if args.write:
        for path, text in files.items():
            path.write_text(text, encoding="utf-8", newline="\n")
            print(f"wrote {path.relative_to(_REPO_ROOT)}")
        return 0
    failures: list[str] = []
    for path, text in files.items():
        committed = path.read_text(encoding="utf-8") if path.is_file() else ""
        if committed.replace("\r\n", "\n") != text:
            failures.append(f"drifted: {path.relative_to(_REPO_ROOT)}")
    failures += [f"no catalogue entry: {line}" for line in uncatalogued(cat)]
    if failures:
        for line in failures:
            print(line)
        print(
            "Add any missing component to quill/data/third_party/components.json, then "
            "regenerate with: python -m quill.tools.build_third_party_notices --write"
        )
        return 1
    print(f"Third-party notices match the catalogue ({len(files)} files).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
