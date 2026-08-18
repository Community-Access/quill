"""Strip the MSYS2 scaffolding the pyenchant wheel ships as package *data*.

WHY THIS EXISTS
---------------
``pyenchant``'s Windows wheel does not vendor "libenchant and its
dependencies" -- it vendors a slice of an entire MSYS2/mingw64 ``bin``
directory. As shipped it carries Tcl/Tk, a second CPython (``libpython3.10.dll``),
GNU readline + ncurses, the GCC support libraries (``libisl``, ``libgmp``,
``libmpfr``, ``libmpc``, ``libquadmath``), gettext's translation *toolchain*,
a private OpenSSL, SQLite, and 34 MB of ICU -- 67.6 MB of ``bin`` against the
20.2 MB of hunspell dictionaries that are the actual point.

None of it is reachable from libenchant, and none of it can be dropped by a
PyInstaller ``excludes`` entry, because to PyInstaller it is not code at all:
``collect_all("enchant")`` sweeps it in as data files. So every QuillVille
installer ships a second Python interpreter and a Tcl runtime that nothing can
call. Quill Radio -- which has no spell checker at all -- carried the lot.

WHAT IT DOES
------------
Rather than hardcode a delete list (which silently rots the first time
pyenchant rebuilds its wheel against different libraries), this computes the
answer: parse the PE import table of every enchant entry point, walk the import
graph transitively, and keep exactly its closure. Everything else in ``bin`` goes.
A dependency that appears in a future wheel is therefore kept automatically, and
one that disappears stops being copied -- no list to maintain.

Static and import libraries (``*.a``, ``*.dll.a``, ``*.la``) are dropped too:
they exist to *link* against libenchant, and nothing loads them at runtime.

Dictionaries under ``share/enchant/hunspell`` are deliberately NOT touched.
They are the payload, they are what a user's locale resolves against, and
20 MB of them is a fair price for spell checking that works in en_ZA.

Usage::

    python scripts/prune_enchant_payload.py <dist-dir>          # prune in place
    python scripts/prune_enchant_payload.py <dist-dir> --dry-run # report only

*dist-dir* may be the runtime dist (``.../QuillVilleRuntime``), its
``_internal`` directory, or the ``enchant`` package directory itself. Absence of
an enchant payload is a no-op success -- an app bundle built without the
spellcheck extra must not fail this step.

Exits non-zero only on a real error (an unreadable PE file, a missing entry
point), never merely because there was nothing to prune.
"""

from __future__ import annotations

import argparse
import struct
import sys
from pathlib import Path

#: Entry points whose transitive imports define "reachable". libenchant-2.dll is
#: what pyenchant loads; the provider modules under lib/enchant-2 are loaded by
#: libenchant at runtime through gmodule, so the import walk cannot discover
#: them from libenchant itself -- they are roots in their own right.
_ENTRY_DLL = "libenchant-2.dll"
_PROVIDER_DIR = Path("lib") / "enchant-2"

#: Link-time artefacts: never loaded, only linked against.
_LINK_ONLY_SUFFIXES = (".a", ".la")

#: Spelling engines to keep. Every dictionary QuillVille ships is hunspell
#: format, so hunspell is the only provider that can resolve one.
_DEFAULT_PROVIDERS = frozenset({"hunspell"})


class PEError(RuntimeError):
    """A file that should have been a PE image could not be parsed."""


def _read_u16(data: bytes, offset: int) -> int:
    return struct.unpack_from("<H", data, offset)[0]


def _read_u32(data: bytes, offset: int) -> int:
    return struct.unpack_from("<I", data, offset)[0]


def _sections(data: bytes, table_offset: int, count: int) -> list[tuple[int, int, int]]:
    """(virtual_address, raw_size, raw_pointer) for each section header."""
    out = []
    for i in range(count):
        base = table_offset + i * 40
        out.append((
            _read_u32(data, base + 12),
            _read_u32(data, base + 16),
            _read_u32(data, base + 20),
        ))
    return out


def _rva_to_offset(rva: int, sections: list[tuple[int, int, int]]) -> int | None:
    """File offset for a relative virtual address, or None if unmapped."""
    for va, raw_size, raw_ptr in sections:
        if va <= rva < va + raw_size:
            return raw_ptr + (rva - va)
    return None


def imported_dlls(path: Path) -> set[str]:
    """The DLL names in *path*'s import directory, lower-cased.

    A hand-rolled PE reader rather than a dependency (pefile is not in any
    QuillVille requirement set, and a build gate that needs its own pip install
    is a gate that gets skipped). Only the import directory is parsed; delay-load
    imports are read too, since glib's are delay-loaded on some builds.
    """
    data = path.read_bytes()
    if data[:2] != b"MZ":
        raise PEError(f"{path.name}: not a PE image (no MZ header)")
    pe_offset = _read_u32(data, 0x3C)
    if data[pe_offset : pe_offset + 4] != b"PE\0\0":
        raise PEError(f"{path.name}: not a PE image (no PE signature)")

    coff = pe_offset + 4
    section_count = _read_u16(data, coff + 2)
    optional_size = _read_u16(data, coff + 16)
    optional = coff + 20
    magic = _read_u16(data, optional)
    if magic == 0x20B:  # PE32+
        directories = optional + 112
    elif magic == 0x10B:  # PE32
        directories = optional + 96
    else:
        raise PEError(f"{path.name}: unknown optional-header magic 0x{magic:x}")

    sections = _sections(data, optional + optional_size, section_count)

    names: set[str] = set()
    # Directory 1 is the import table; directory 13 is the delay-load table.
    # Their descriptor layouts differ, but the DLL-name RVA sits at a fixed
    # offset in each (12 for import, 4 for delay-load) and that is all we need.
    for index, stride, name_field in ((1, 20, 12), (13, 32, 4)):
        entry = directories + index * 8
        table_rva = _read_u32(data, entry)
        if not table_rva:
            continue
        offset = _rva_to_offset(table_rva, sections)
        if offset is None:
            continue
        while True:
            descriptor = data[offset : offset + stride]
            if len(descriptor) < stride or not any(descriptor):
                break
            name_rva = _read_u32(data, offset + name_field)
            name_offset = _rva_to_offset(name_rva, sections) if name_rva else None
            if name_offset is not None:
                end = data.index(b"\0", name_offset)
                names.add(data[name_offset:end].decode("ascii", "replace").lower())
            offset += stride
    return names


def find_enchant_root(target: Path) -> Path | None:
    """The ``enchant/data/mingw64`` directory under *target*, if there is one."""
    for candidate in (
        target / "data" / "mingw64",
        target / "enchant" / "data" / "mingw64",
        target / "_internal" / "enchant" / "data" / "mingw64",
        target / "Lib" / "site-packages" / "enchant" / "data" / "mingw64",
    ):
        if candidate.is_dir():
            return candidate
    return None


def reachable(bin_dir: Path, roots: list[Path]) -> set[str]:
    """Lower-cased names of every DLL in *bin_dir* reachable from *roots*.

    Imports naming a DLL that is not in *bin_dir* are system DLLs (kernel32,
    msvcrt, the api-ms-win-* set) resolved from Windows itself; they are simply
    not our business and drop out of the walk.
    """
    present = {p.name.lower(): p for p in bin_dir.iterdir() if p.is_file()}
    keep: set[str] = set()
    queue = list(roots)
    while queue:
        current = queue.pop()
        for name in imported_dlls(current):
            if name in present and name not in keep:
                keep.add(name)
                queue.append(present[name])
    return keep


def prune(
    target: Path, *, providers: frozenset[str] = _DEFAULT_PROVIDERS, dry_run: bool = False
) -> int:
    """Prune the enchant payload under *target*; return bytes removed."""
    root = find_enchant_root(target)
    if root is None:
        print("No enchant payload here; nothing to prune.")
        return 0

    bin_dir = root / "bin"
    provider_dir = root / _PROVIDER_DIR
    entry = bin_dir / _ENTRY_DLL
    if not entry.is_file():
        raise PEError(f"enchant payload at {root} has no {_ENTRY_DLL}")

    dropped_providers: list[tuple[str, int]] = []

    # Providers we keep. Everything shipped under share/enchant/hunspell is in
    # hunspell format and that is the provider QUILL's dictionaries resolve
    # through, so nuspell is a second, unused spelling engine -- and an
    # expensive one: it is the only thing in the payload that pulls ICU, whose
    # libicudt72.dll alone is 29.8 MB of locale data. Dropping the provider
    # drops ICU with it, because the walk below then never reaches it.
    kept_providers: list[Path] = []
    if provider_dir.is_dir():
        for candidate in sorted(provider_dir.iterdir()):
            if candidate.suffix.lower() != ".dll":
                continue
            name = candidate.stem.replace("enchant_", "")
            if name in providers:
                kept_providers.append(candidate)
            else:
                dropped_providers.append((
                    f"{_PROVIDER_DIR}/{candidate.name}",
                    candidate.stat().st_size,
                ))
    roots = [entry, *kept_providers]

    keep = reachable(bin_dir, roots)
    keep.add(_ENTRY_DLL.lower())

    removed = 0
    dropped: list[tuple[str, int]] = []
    for name, size in dropped_providers:
        dropped.append((name, size))
        removed += size
        if not dry_run:
            (root / name).unlink()
    for item in sorted(bin_dir.iterdir()):
        if not item.is_file() or item.name.lower() in keep:
            continue
        dropped.append((item.name, item.stat().st_size))
        removed += item.stat().st_size
        if not dry_run:
            item.unlink()

    # Link-only artefacts beside the providers: *.a, *.dll.a, *.la.
    if provider_dir.is_dir():
        for item in sorted(provider_dir.iterdir()):
            if item.is_file() and item.name.endswith(_LINK_ONLY_SUFFIXES):
                dropped.append((f"{_PROVIDER_DIR}/{item.name}", item.stat().st_size))
                removed += item.stat().st_size
                if not dry_run:
                    item.unlink()

    verb = "would remove" if dry_run else "removed"
    print(f"enchant payload at {root}")
    print(f"  kept {len(keep)} reachable libraries from {_ENTRY_DLL} and its providers")
    for name, size in sorted(dropped, key=lambda pair: -pair[1])[:10]:
        print(f"    {verb}: {name} ({size / 1024 / 1024:.1f} MB)")
    if len(dropped) > 10:
        print(f"    ... and {len(dropped) - 10} more")
    print(f"  {verb} {len(dropped)} files, {removed / 1024 / 1024:.1f} MB")
    return removed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    parser.add_argument(
        "target", type=Path, help="a dist dir, its _internal, or the enchant package"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="report what would go; change nothing"
    )
    parser.add_argument(
        "--providers",
        default=",".join(sorted(_DEFAULT_PROVIDERS)),
        help="comma-separated spelling engines to keep (default: %(default)s)",
    )
    args = parser.parse_args()

    providers = frozenset(p.strip() for p in args.providers.split(",") if p.strip())
    try:
        prune(args.target.resolve(), providers=providers, dry_run=args.dry_run)
    except (PEError, OSError) as error:
        print(f"enchant prune failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
