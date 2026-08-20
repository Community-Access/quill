"""The enchant prune: keep libenchant's real import closure, drop the MSYS2 rest.

pyenchant's Windows wheel vendors a slice of an MSYS2 bin\\ directory as package
*data* -- Tcl/Tk, a second CPython, GNU readline, the GCC support libraries,
gettext's toolchain, 34 MB of ICU -- which PyInstaller ``excludes`` cannot touch
because to PyInstaller it is not code. These tests pin the pruner that can: that
it keeps what libenchant and its kept providers import, transitively; that it
drops an unreachable library however large; that dropping a provider drops that
provider's private dependencies with it; that dictionaries survive; and that an
absent payload is a no-op success rather than a build failure.

The PE fixtures are synthesised, not sampled: a real DLL would make the test
depend on whichever pyenchant wheel this machine happens to have.
"""

from __future__ import annotations

import importlib.util
import struct
from pathlib import Path

import pytest

_SCRIPT = Path(__file__).resolve().parents[3] / "scripts" / "prune_enchant_payload.py"
_spec = importlib.util.spec_from_file_location("prune_enchant_payload", _SCRIPT)
assert _spec is not None and _spec.loader is not None
pruner = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(pruner)


def _pe_with_imports(names: list[str], padding: int = 0) -> bytes:
    """A minimal but genuinely parseable PE32+ image importing *names*.

    One section, mapped 1:1 (virtual address == raw pointer) so the RVA
    arithmetic under test is exercised rather than bypassed.
    """
    header_size = 0x400
    body = bytearray()
    # Lay out the name strings first; their offsets become RVAs.
    name_rvas: list[int] = []
    strings = bytearray()
    for name in names:
        name_rvas.append(header_size + 0x200 + len(strings))
        strings += name.encode("ascii") + b"\0"

    # Import descriptors: 20 bytes each, DLL-name RVA at offset 12, then a
    # null terminator descriptor.
    descriptors = bytearray()
    for rva in name_rvas:
        descriptors += struct.pack("<IIIII", 0, 0, 0, rva, 0)
    descriptors += b"\0" * 20
    import_rva = header_size

    body += descriptors
    body += b"\0" * ((header_size + 0x200) - (header_size + len(descriptors)))
    body += strings
    body += b"\0" * padding

    data = bytearray(header_size + len(body))
    data[0:2] = b"MZ"
    pe_offset = 0x80
    struct.pack_into("<I", data, 0x3C, pe_offset)
    data[pe_offset : pe_offset + 4] = b"PE\0\0"

    coff = pe_offset + 4
    optional_size = 240
    struct.pack_into("<H", data, coff + 2, 1)  # one section
    struct.pack_into("<H", data, coff + 16, optional_size)

    optional = coff + 20
    struct.pack_into("<H", data, optional, 0x20B)  # PE32+
    directories = optional + 112
    struct.pack_into("<II", data, directories + 1 * 8, import_rva, len(descriptors))

    section = optional + optional_size
    data[section : section + 8] = b".text\0\0\0"
    struct.pack_into("<I", data, section + 12, header_size)  # virtual address
    struct.pack_into("<I", data, section + 16, len(body))  # raw size
    struct.pack_into("<I", data, section + 20, header_size)  # raw pointer

    data[header_size:] = body
    return bytes(data)


@pytest.fixture
def payload(tmp_path: Path) -> Path:
    """An enchant payload shaped like the real wheel's, with fake PE files."""
    root = tmp_path / "enchant" / "data" / "mingw64"
    bin_dir = root / "bin"
    providers = root / "lib" / "enchant-2"
    dictionaries = root / "share" / "enchant" / "hunspell"
    for directory in (bin_dir, providers, dictionaries):
        directory.mkdir(parents=True)

    # libenchant -> glib; hunspell provider -> libhunspell; nuspell provider ->
    # libicuuc -> libicudt. Exactly the shape that makes ICU 34 MB of dead
    # weight once nuspell goes.
    (bin_dir / "libenchant-2.dll").write_bytes(
        _pe_with_imports(["libglib-2.0-0.dll", "kernel32.dll"])
    )
    (bin_dir / "libglib-2.0-0.dll").write_bytes(_pe_with_imports(["kernel32.dll"]))
    (bin_dir / "libhunspell-1.7-0.dll").write_bytes(_pe_with_imports(["kernel32.dll"]))
    (bin_dir / "libicuuc72.dll").write_bytes(_pe_with_imports(["libicudt72.dll"]))
    (bin_dir / "libicudt72.dll").write_bytes(_pe_with_imports([], padding=4096))
    (bin_dir / "tcl86.dll").write_bytes(_pe_with_imports([], padding=2048))
    (bin_dir / "libpython3.10.dll").write_bytes(_pe_with_imports([], padding=2048))

    (providers / "enchant_hunspell.dll").write_bytes(_pe_with_imports(["libhunspell-1.7-0.dll"]))
    (providers / "enchant_nuspell.dll").write_bytes(_pe_with_imports(["libicuuc72.dll"]))
    (providers / "enchant_hunspell.dll.a").write_bytes(b"link only")
    (providers / "enchant_nuspell.la").write_bytes(b"link only")

    (dictionaries / "en_US.dic").write_bytes(b"words")
    (dictionaries / "en_US.aff").write_bytes(b"affixes")
    return tmp_path / "enchant"


def _bin_names(payload: Path) -> set[str]:
    return {p.name for p in (payload / "data" / "mingw64" / "bin").iterdir()}


def test_keeps_the_transitive_closure_of_libenchant_and_hunspell(payload: Path) -> None:
    pruner.prune(payload)

    kept = _bin_names(payload)
    assert "libenchant-2.dll" in kept
    assert "libglib-2.0-0.dll" in kept, "reached transitively through libenchant"
    assert "libhunspell-1.7-0.dll" in kept, "reached through the hunspell provider"


def test_drops_unreachable_libraries_however_large(payload: Path) -> None:
    pruner.prune(payload)

    kept = _bin_names(payload)
    assert "tcl86.dll" not in kept
    assert "libpython3.10.dll" not in kept


def test_dropping_nuspell_drops_the_icu_it_alone_pulled(payload: Path) -> None:
    pruner.prune(payload)

    providers = payload / "data" / "mingw64" / "lib" / "enchant-2"
    assert not (providers / "enchant_nuspell.dll").exists()
    kept = _bin_names(payload)
    assert "libicuuc72.dll" not in kept
    assert "libicudt72.dll" not in kept, "34 MB of locale data reachable only from nuspell"


def test_keeping_nuspell_keeps_icu(payload: Path) -> None:
    pruner.prune(payload, providers=frozenset({"hunspell", "nuspell"}))

    kept = _bin_names(payload)
    assert "libicuuc72.dll" in kept
    assert "libicudt72.dll" in kept


def test_dictionaries_are_never_touched(payload: Path) -> None:
    pruner.prune(payload)

    dictionaries = payload / "data" / "mingw64" / "share" / "enchant" / "hunspell"
    assert (dictionaries / "en_US.dic").exists()
    assert (dictionaries / "en_US.aff").exists()


def test_link_only_artefacts_go(payload: Path) -> None:
    pruner.prune(payload)

    providers = payload / "data" / "mingw64" / "lib" / "enchant-2"
    assert not (providers / "enchant_hunspell.dll.a").exists()
    assert not (providers / "enchant_nuspell.la").exists()
    assert (providers / "enchant_hunspell.dll").exists()


def test_dry_run_changes_nothing(payload: Path) -> None:
    before = _bin_names(payload)

    removed = pruner.prune(payload, dry_run=True)

    assert removed > 0
    assert _bin_names(payload) == before


def test_no_enchant_payload_is_a_no_op_success(tmp_path: Path) -> None:
    """An app bundle built without the spellcheck extra must not fail the build."""
    assert pruner.prune(tmp_path) == 0


def test_a_payload_without_libenchant_is_an_error(payload: Path) -> None:
    (payload / "data" / "mingw64" / "bin" / "libenchant-2.dll").unlink()

    with pytest.raises(pruner.PEError):
        pruner.prune(payload)
