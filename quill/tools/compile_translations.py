"""Compile QUILL's ``.po`` catalogs into ``.mo`` files.

Translators submit ``.po`` files; the app loads compiled ``.mo`` files (and the
display-language switcher only offers languages that have one). This tool turns
every ``quill/locale/<lang>/LC_MESSAGES/quill.po`` into a sibling ``quill.mo``
using Babel (already a dev dependency), so neither contributors nor the build
need the ``pybabel`` CLI on PATH.

Run::

    python -m quill.tools.compile_translations          # compile in place
    python -m quill.tools.compile_translations --check   # list, do not write

Exit code 0 = success (or nothing to do); 1 = a catalog failed to parse.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_LOCALE_DIR = Path(__file__).resolve().parents[1] / "locale"
_DOMAIN = "quill"


def po_files() -> list[Path]:
    """Return every translation catalog under ``quill/locale``, sorted."""
    if not _LOCALE_DIR.is_dir():
        return []
    return sorted(_LOCALE_DIR.glob(f"*/LC_MESSAGES/{_DOMAIN}.po"))


def compile_all(check: bool = False) -> int:
    from babel.messages.mofile import write_mo
    from babel.messages.pofile import read_po

    catalogs = po_files()
    if not catalogs:
        print("compile_translations: no .po catalogs found (nothing to compile)")
        return 0

    errors = 0
    for po_path in catalogs:
        lang = po_path.parent.parent.name
        mo_path = po_path.with_suffix(".mo")
        try:
            with po_path.open("rb") as handle:
                catalog = read_po(handle)
        except Exception as exc:  # malformed .po
            print(f"  ERROR {lang}: {po_path} failed to parse: {exc}")
            errors += 1
            continue
        if check:
            print(f"  would compile {lang}: {po_path} -> {mo_path.name}")
            continue
        with mo_path.open("wb") as handle:
            write_mo(handle, catalog)
        print(f"  compiled {lang}: {mo_path}")

    if errors:
        print(f"compile_translations: {errors} catalog(s) failed")
        return 1
    print(f"compile_translations: {len(catalogs)} catalog(s) processed")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Compile QUILL .po catalogs into .mo files.")
    parser.add_argument(
        "--check",
        action="store_true",
        help="List catalogs that would be compiled without writing .mo files.",
    )
    args = parser.parse_args()
    sys.exit(compile_all(check=args.check))


if __name__ == "__main__":
    main()
