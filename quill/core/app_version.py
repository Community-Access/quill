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

A portable copy and a source checkout have no marker: they carry their own code,
so the code's constant is the truth there and is what this returns.

wx-free and side-effect free: it only reads.
"""

from __future__ import annotations

import configparser
import re
from pathlib import Path

from quill.core.install_edition import app_root

__all__ = ["MARKER_NAME", "describe_version", "installed_version", "read_marker"]

MARKER_NAME = "quill-app-version.ini"
_VERSION_RE = re.compile(r"^\d+(?:\.\d+){1,3}(?:[-.][0-9A-Za-z.]+)?$")


def read_marker(root: Path | None) -> str:
    """The version the installer recorded in *root*, or "" when there is none."""
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
    return value if _VERSION_RE.match(value) else ""


def installed_version(code_version: str, root: Path | None = None) -> str:
    """The installed app's version: the installer's marker, else *code_version*."""
    marker = read_marker(root if root is not None else app_root())
    return marker or code_version


def describe_version(code_version: str, root: Path | None = None) -> str:
    """The version as About shows it: the installed one, plus the runtime's code
    version when a different installer's runtime is what is running."""
    installed = installed_version(code_version, root)
    if installed == code_version:
        return installed
    return f"{installed} (running shared runtime code {code_version})"
