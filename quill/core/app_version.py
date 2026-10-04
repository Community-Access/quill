"""Which version of an app is installed -- asked of the installer, not the runtime.

Every QuillVille installer ships the shared QuillVille Runtime, and the runtime
carries one frozen copy of every app's code, version constants included. So the
constant an app is running with says which runtime is on the machine, not which
app installer ran -- and on 2026-09-29 those disagreed: a runtime from Quill
Radio 3.0.3 made an installed QUILL Lite 1.0.0 call itself 1.1.0, and Check for
Updates then never offered the real 1.1.0.

So each installer writes the version it installed into the app's own folder
(``quill-app-version.ini``, section ``[app]``, key ``version``), and this module
reads it back. The installed version is what Check for Updates compares and what
About reports; the runtime's code version is shown beside it only when the two
differ, which is exactly what support needs to see.

**Where the marker actually is** is the whole trick, and the first version of
this module got it wrong (fixed 2026-09-30, before Quill Radio 3.1.1 shipped it).
The installer writes it into ``{app}`` -- ``C:\\Program Files\\Quill Radio``,
beside ``QuillRadio.exe`` -- but ``install_edition.app_root()`` answers
``QUILL_APP_ROOT``, which on a shared-runtime install is the *runtime's* folder
in ``%LOCALAPPDATA%\\QuillVille\\Runtime``. Looking only there found no marker on
any installed copy, so every one of them fell back to the runtime's constant:
precisely the bug this module exists to prevent, shipped inside the fix for it.
So the search is :func:`quill.core.app_folders.app_folders` -- the launcher's own
folder (``QUILL_LAUNCHER_DIR``) first, then the running interpreter's -- and
``app_root()`` last. That is the same lookup ``app_folders`` was written for when
Help > User Guide could not find the documents its installer had put beside the
program.

A portable copy and a source checkout have no marker: they carry their own code,
so the code's constant is the truth there and is what this returns.

**Build numbers (2026-10).** The installer also writes
``[app] version_build=3.2.0+12`` -- a *separate* key, not ``version=3.2.0+12``,
because the marker is read by every runtime on the machine, including older
ones whose reader rejects anything but a plain version and would then fall back
to their own constant: the very bug above. It repeats the version rather than
holding the bare build because Inno's ``[INI]`` never deletes a key an older
installer does not write: reinstalling 3.1.1 over 3.2.0 build 12 leaves
``version_build=3.2.0+12`` behind, and a key that names its own version is one
:func:`read_marker` can see is stale and ignore. Check for Updates compares
``3.2.0+12``; :func:`describe_version` says it the way a person hears it,
``3.2.0 (build 12)``. A marker with no build (every install made before build
numbers) is build 0, never the code's build: the code is the runtime's, not the
installer's.

wx-free and side-effect free: it only reads.
"""

from __future__ import annotations

import configparser
import re
from pathlib import Path

from quill.core.app_folders import app_folders
from quill.core.install_edition import app_root

__all__ = [
    "MARKER_NAME",
    "describe_version",
    "full_version",
    "installed_version",
    "marker_roots",
    "read_marker",
    "read_marker_value",
    "runtime_slot",
]

MARKER_NAME = "quill-app-version.ini"
_VERSION_RE = re.compile(r"^\d+(?:\.\d+){1,3}(?:[-.][0-9A-Za-z.]+)?(?:\+[0-9A-Za-z.]+)?$")


def full_version(version: str, build: int | str | None = 0) -> str:
    """An app's version constant and its build constant as one version:
    ``full_version("3.2.0", 1)`` is ``3.2.0+1``. Build 0 leaves it bare."""
    from quill.core.versioning import with_build

    return with_build(version, build)


def read_marker(root: Path | None) -> str:
    """The version the installer recorded in *root*, with its build
    (``3.2.0+12``), or "" when there is none."""
    if root is None:
        return ""
    path = root / MARKER_NAME
    parser = configparser.ConfigParser()
    try:
        if not parser.read(path, encoding="utf-8"):
            return ""
    except (OSError, configparser.Error, UnicodeDecodeError):
        return ""
    value = parser.get("app", "version", fallback="").strip()
    if not _VERSION_RE.match(value):
        return ""
    built = parser.get("app", "version_build", fallback="").strip()
    number, plus, build = built.partition("+")
    if plus and number == value.partition("+")[0] and build.isdigit():
        return full_version(number, build)
    return value


def read_marker_value(root: Path | None, section: str, key: str) -> str:
    """Any other value the installer recorded: ``[app] channel=``, ``[runtime] slot=``.

    The installer writes the channel the install was made for and the runtime
    slot it put the runtime in (release channels, plan 6.5). "" when absent.
    """
    if root is None:
        return ""
    parser = configparser.ConfigParser()
    try:
        if not parser.read(root / MARKER_NAME, encoding="utf-8"):
            return ""
    except (OSError, configparser.Error, UnicodeDecodeError):
        return ""
    return parser.get(section, key, fallback="").strip()


def runtime_slot(root: Path | None = None) -> str:
    """The shared-runtime slot this install runs from (``3.13``, ``3.13-beta``), or ""."""
    roots = [root] if root is not None else marker_roots()
    for candidate in roots:
        slot = read_marker_value(candidate, "runtime", "slot")
        if slot:
            return slot
    return ""


def marker_roots() -> list[Path]:
    """Every folder the installer's marker could be in, most specific first.

    The launcher's own folder is where an installer puts it; the running
    interpreter's folder covers a portable bundle and a single-app frozen
    build; ``app_root()`` is last, and on a shared-runtime install is the
    runtime's folder, which is exactly the folder the marker is *not* in.
    """
    roots = list(app_folders())
    root = app_root()
    if root is not None and root not in roots:
        roots.append(root)
    return roots


def installed_version(code_version: str, root: Path | None = None, *, build: int = 0) -> str:
    """The installed app's version: the installer's marker, else *code_version*
    (as build *build*, the app's build constant).

    *root* searches that one folder and nothing else (tests, and any caller that
    already knows where to look). Left out, every folder
    :func:`marker_roots` names is tried in order.
    """
    code = full_version(code_version, build)
    if root is not None:
        return read_marker(root) or code
    for candidate in marker_roots():
        marker = read_marker(candidate)
        if marker:
            return marker
    return code


def describe_version(code_version: str, root: Path | None = None, *, build: int = 0) -> str:
    """The version as About shows it -- ``3.2.0 (build 12)`` -- plus the
    runtime's code version when a different installer's runtime is what is
    running.

    A marker with no build (an installer from before build numbers) beside code
    of the same number is not a mismatch worth a sentence: it is the same
    release, and the marker simply predates the build key.
    """
    from quill.core.versioning import ReleaseVersion, display_version

    code = full_version(code_version, build)
    installed = installed_version(code_version, root, build=build)
    if installed == code:
        return display_version(installed)
    mine, theirs = ReleaseVersion.try_parse(installed), ReleaseVersion.try_parse(code)
    if mine is not None and theirs is not None and not mine.build and mine.same_number(theirs):
        return display_version(installed)
    return f"{display_version(installed)} (running shared runtime code {display_version(code)})"
