"""Folder scan + filtering for batch document-to-speech.

wx-free, strict-typed. Separated from ``batch_export`` (the synthesis pipeline)
so discovery — which files under a folder are converted, narrowed by extension,
include/exclude globs, and a size cap — is one small, independently testable
concern. :func:`quill.core.speech.batch_export.discover_files` re-exports
:func:`discover_files` from here for callers and ``__all__``.
"""

from __future__ import annotations

import fnmatch
from pathlib import Path


def _split_globs(patterns: str) -> list[str]:
    """Split a ``;``/``,``-separated glob list into individual patterns."""
    return [p.strip() for p in patterns.replace(",", ";").split(";") if p.strip()]


def _matches_any(source: Path, source_root: Path, patterns: list[str]) -> bool:
    """True when *source* matches any glob, tested against name and relative path."""
    try:
        rel = source.relative_to(source_root).as_posix()
    except ValueError:
        rel = source.name
    name = source.name
    return any(fnmatch.fnmatch(name, pat) or fnmatch.fnmatch(rel, pat) for pat in patterns)


def discover_files(
    folder: Path,
    extensions: list[str],
    recursive: bool,
    *,
    include_glob: str = "",
    exclude_glob: str = "",
    max_file_bytes: int = 0,
) -> list[Path]:
    """Return source files matching *extensions* under *folder*.

    Optional filters narrow the set: ``include_glob`` keeps only matching files
    (empty keeps all), ``exclude_glob`` drops matching files (wins over include),
    and ``max_file_bytes`` (>0) drops files larger than the cap. Globs are
    ``;``/``,``-separated and matched against both the file name and its path
    relative to *folder*.
    """
    exts = {e.lower() for e in extensions}
    glob = "**/*" if recursive else "*"
    found: set[Path] = set()
    for ext in exts:
        found.update(folder.glob(f"{glob}{ext}"))

    includes = _split_globs(include_glob)
    excludes = _split_globs(exclude_glob)
    cap = max(0, int(max_file_bytes))

    kept: list[Path] = []
    for path in found:
        if includes and not _matches_any(path, folder, includes):
            continue
        if excludes and _matches_any(path, folder, excludes):
            continue
        if cap:
            try:
                if path.stat().st_size > cap:
                    continue
            except OSError:
                continue
        kept.append(path)
    kept.sort()
    return kept
