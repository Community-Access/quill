"""The launcher's release-channel slot, in C and in its Python mirror.

``runtime_resolve.c`` reads ``[runtime] slot=`` from the
``quill-app-version.ini`` beside the launcher and resolves
``Runtime\\<slot>``; with no ``slot=`` it uses ``Runtime\\3.14`` exactly as
before, and with a slot it never falls back to Stable's folder. A missing
runtime repairs from the tag named for its slot (``runtime-3.14``,
``runtime-3.14-beta``); a Dev one does not repair itself. The C
is not compiled here (no binaries are built in this repository's tests), so
the contract is pinned twice: a Python mirror of the parser, exercised, and the
C source checked for the same rules.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from quill.core.updater.runtime_slots import is_valid_slot

REPO = Path(__file__).resolve().parents[3]
LAUNCHER = REPO / "quill" / "native" / "launcher"
BASE_URL = (
    "https://github.com/Community-Access/quill/releases/download/runtime-3.14/"
    "QuillVille-Runtime-Setup.exe"
)


def ql_runtime_slot(self_dir: Path) -> str:
    """Mirror of ``ql_runtime_slot`` in runtime_resolve.c."""
    try:
        raw = (self_dir / "quill-app-version.ini").read_bytes()
    except OSError:
        return ""
    in_runtime = False
    for line in raw.splitlines():
        text = line.decode("utf-8", "replace").lstrip("﻿").strip()
        if text.startswith("["):
            in_runtime = text.lower().startswith("[runtime]")
            continue
        if in_runtime and text.lower().startswith("slot="):
            value = text[5:]
            return value if is_valid_slot(value) else ""
    return ""


def ql_runtime_url_for_slot(base: str, slot: str) -> str | None:
    """Mirror of ``ql_runtime_url_for_slot``."""
    if slot.endswith("-dev"):
        return None
    seg = base.find("/runtime-")
    end = base.find("/", seg + 1) if seg >= 0 else -1
    if seg >= 0 and end >= 0 and slot:
        return f"{base[:seg]}/runtime-{slot}{base[end:]}"
    return base


@pytest.mark.parametrize(
    ("ini", "slot"),
    [
        ("[app]\nversion=3.3.0\n", ""),
        ("[runtime]\nslot=3.13-beta\n", "3.13-beta"),
        ("﻿[app]\r\nchannel=dev\r\n[Runtime]\r\nSlot=3.13-dev\r\n", "3.13-dev"),
        ("[runtime]\nslot=..\\..\\Windows\n", ""),
        ("[app]\nslot=3.13-beta\n", ""),
    ],
)
def test_slot_parsing(tmp_path: Path, ini: str, slot: str) -> None:
    (tmp_path / "quill-app-version.ini").write_bytes(ini.encode("utf-8"))
    assert ql_runtime_slot(tmp_path) == slot


def test_self_heal_url_per_slot() -> None:
    from quill.core.updater.runtime_slots import self_heal_tag

    assert ql_runtime_url_for_slot(BASE_URL, "") == BASE_URL
    assert ql_runtime_url_for_slot(BASE_URL, "3.14") == BASE_URL
    for slot in ("3.14-beta", "3.15", "3.15-beta"):
        url = ql_runtime_url_for_slot(BASE_URL, slot)
        assert url == BASE_URL.replace("/runtime-3.14/", f"/{self_heal_tag(slot)}/")
    assert ql_runtime_url_for_slot(BASE_URL, "3.14-dev") is None


def test_the_compiled_default_is_this_pythons_tag_never_a_frozen_one() -> None:
    """runtime-latest and runtime-beta hold 3.13 for the launchers built before
    2026-10-12. A launcher whose default pointed there would repair a 3.14 app
    with a 3.13 runtime it never looks for."""
    from quill.core.updater.runtime_slots import (
        LEGACY_RUNTIME_TAGS,
        PYTHON_MAJOR,
        self_heal_tag,
    )

    want = f"/download/{self_heal_tag(PYTHON_MAJOR)}/QuillVille-Runtime-Setup.exe"
    cmake = (LAUNCHER / "CMakeLists.txt").read_text(encoding="utf-8")
    script = (REPO / "scripts" / "build_native_launcher.py").read_text(encoding="utf-8")
    assert want in cmake
    assert f"/download/{self_heal_tag(PYTHON_MAJOR)}/" in script  # split across two literals
    for frozen in LEGACY_RUNTIME_TAGS:
        assert f"/download/{frozen}/" not in cmake
        assert f"/download/{frozen}/" not in script


def test_the_c_source_keeps_the_same_rules() -> None:
    source = (LAUNCHER / "runtime_resolve.c").read_text(encoding="utf-8")
    header = (LAUNCHER / "runtime_resolve.h").read_text(encoding="utf-8")
    launcher = (LAUNCHER / "launcher.c").read_text(encoding="utf-8")
    assert "char slot[QL_SLOT_MAX];" in header
    assert 'path_join(ini, sizeof(ini), self_dir, "quill-app-version.ini");' in source
    assert 'ql_strnicmp(s, "[runtime]", 9)' in source
    assert 'strcmp(p, "-beta") == 0 || strcmp(p, "-dev") == 0' in source
    assert 'strstr(base_url, "/runtime-")' in source
    assert '"%.*s/runtime-%s%s"' in source
    assert "/runtime-latest/" not in source and "/runtime-beta/" not in source
    # With a slot, never Stable's folder; without one, the Stable path.
    assert "path_join(runtime_dir, sizeof(runtime_dir), base, slot);" in source
    assert "path_join(runtime_dir, sizeof(runtime_dir), base, QL_PYTHON_MAJOR);" in source
    assert "ql_runtime_url_for_slot(PRODUCT_RUNTIME_URL, runtime.slot" in launcher
    assert "Reinstall the Dev build" in launcher


def test_one_python_minor_everywhere() -> None:
    """The launcher, the slot rule, the embeddable pins and every installer agree.

    Moving Python is five kinds of file (the 3.13 -> 3.14 move, 2026-10-11): the
    launcher refuses a runtime whose marker names another minor and looks in
    ``Runtime\\<minor>``, the installers lay the runtime down by
    ``RuntimeVersion``, and the build scripts download ``EMBEDDED_PYTHON_VERSION``.
    Any one of them left behind is an app that cannot find its interpreter.
    """
    import re

    from quill.core.updater.runtime_slots import PYTHON_MAJOR

    source = (LAUNCHER / "runtime_resolve.c").read_text(encoding="utf-8")
    macro = re.search(r'#define QL_PYTHON_MAJOR "([0-9.]+)"', source)
    assert macro is not None
    assert macro.group(1) == PYTHON_MAJOR

    pins = {
        "scripts/build_windows_distribution.py": r'EMBEDDED_PYTHON_VERSION = "([0-9.]+)"',
        "standalone/studio/scripts/build_portable.py": r'EMBEDDED_PYTHON_VERSION = "([0-9.]+)"',
    }
    for iss in sorted((REPO / "standalone").glob("*/installer/*.iss")):
        if "RuntimeVersion" in iss.read_text(encoding="utf-8"):
            pins[iss.relative_to(REPO).as_posix()] = r'#define RuntimeVersion "([0-9.]+)"'
    assert len(pins) > 2, "no installer declares RuntimeVersion any more"
    versions = {}
    for rel, pattern in pins.items():
        found = re.search(pattern, (REPO / rel).read_text(encoding="utf-8"))
        assert found is not None, rel
        versions[rel] = found.group(1)
    assert len(set(versions.values())) == 1, versions
    assert next(iter(versions.values())).startswith(PYTHON_MAJOR + "."), versions
