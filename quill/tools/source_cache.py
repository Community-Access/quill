"""One parse of the source tree, shared for the duration of a single gate run.

``check_banned_patterns.find_violations`` runs nine checks over overlapping file
sets, and each one used to do its own ``read_text`` + ``ast.parse``. Every UI
module was read and parsed up to a dozen times per run -- ``main_frame.py``
(~27,000 lines) included -- which was never wrong, only slow. Slow has a real
cost here: the whole-tree gate tests grew until they brushed pytest's per-test
timeout on a loaded machine and began failing intermittently, and a gate that
times out sometimes is one people learn to re-run rather than believe.

Two things this module is careful about, both learned by getting them wrong:

**Lines are computed on demand, never eagerly.** Most callers want only the AST.
Splitting every file in the package into a tuple of lines that nobody reads cost
more than the parsing it was meant to save -- it turned the egress audit's cold
scan from 7.6s into 19.7s on its own.

**The cache is scoped to a run, not to the process.** Holding every AST in
``quill/`` costs roughly 480 MB. That is affordable for the seconds a gate takes
and absurd for the lifetime of a pytest session, where it would sit behind every
later test. Top-level gate entry points call :func:`clear` in a ``finally``, so
the memory is released even when a check raises. :func:`scope` is the same thing
as a context manager for callers that would rather not write the ``try``.

Keyed on ``(path, mtime_ns, size)`` rather than path alone: the gates' own unit
tests write a module, scan it, and rewrite it under the same ``tmp_path``, and a
path-keyed cache would hand the second scan the first file's tree.

Not thread-safe by design, and it does not need to be: gates run single-threaded
in a build step or a test.
"""

from __future__ import annotations

import ast
from collections.abc import Iterator
from contextlib import contextmanager
from functools import cache
from pathlib import Path

__all__ = ["read", "parsed", "parsed_source", "clear", "clear_all", "scope", "cached_count"]


class _Entry:
    """One file's AST, plus its lines if anyone ever asks for them."""

    __slots__ = ("_source", "tree", "_lines")

    def __init__(self, source: str, tree: ast.Module) -> None:
        self._source = source
        self.tree = tree
        self._lines: tuple[str, ...] | None = None

    @property
    def lines(self) -> tuple[str, ...]:
        if self._lines is None:
            self._lines = tuple(self._source.splitlines())
        return self._lines


@cache
def _read(path: Path, _mtime_ns: int, _size: int) -> str:
    """The source text. Held for the session -- see :func:`read`."""
    return path.read_text(encoding="utf-8")


@cache
def _entry(path: Path, mtime_ns: int, size: int) -> _Entry:
    source = _read(path, mtime_ns, size)
    return _Entry(source, ast.parse(source, filename=str(path)))


def _stamp(path: Path) -> tuple[Path, int, int]:
    stat = path.stat()
    return path, stat.st_mtime_ns, stat.st_size


def _lookup(path: Path) -> _Entry:
    return _entry(*_stamp(path))


def read(path: Path) -> str:
    """The source text of *path*, read from disk at most once per revision.

    Separate from the AST tier, and on a different lifetime, because the two
    have wildly different costs. Measured over ``quill/`` -- 1,308 files --
    reading is 60% of the total and the text is **14 MB**; the ASTs built from
    it are **480 MB**. So the text is worth keeping for the whole session and
    the trees are not.

    That split matters because the I/O is the part that degrades under load.
    Four separate gates walk this tree (the banned-pattern gate, the egress
    audit, and two TLS checks), and in a full pytest session the same scan that
    takes ~16s can exceed 180s -- the page cache has been evicted by everything
    that ran in between, so every read goes back to the disk, through the
    virus scanner, one file at a time. Reading once fixes that for all of them
    at a cost of 14 MB.
    """
    return _read(*_stamp(path))


def parsed(path: Path) -> ast.Module:
    """The AST of *path*, parsed at most once per revision per run."""
    return _lookup(path).tree


def parsed_source(path: Path) -> tuple[tuple[str, ...], ast.Module]:
    """The source lines and AST of *path*.

    Lines come back as a tuple because the value is shared: a caller that
    mutated a list here would corrupt every later caller's view of the file.
    """
    entry = _lookup(path)
    return entry.lines, entry.tree


def cached_count() -> int:
    """How many files are currently held. For tests that assert on lifetime."""
    return _entry.cache_info().currsize


def clear() -> None:
    """Release every held AST, keeping the source text.

    Called when a gate run finishes. The text tier survives deliberately: it is
    14 MB against the trees' 480 MB, and keeping it is what spares the *next*
    gate the disk read that is the expensive half.
    """
    _entry.cache_clear()


def clear_all() -> None:
    """Release the source text as well. For tests that want a cold start."""
    _entry.cache_clear()
    _read.cache_clear()


_depth = 0


@contextmanager
def scope() -> Iterator[None]:
    """Hold parses for the duration of the block, then release them.

    Re-entrant, and it has to be: ``check_banned_patterns.find_violations``
    opens a scope and then calls ``dialog_inventory.scan_dialog_surfaces``,
    which opens one of its own so it is also safe to call directly. Only the
    outermost scope clears -- an inner one that released the cache would pull
    the tree out from under the run that is still using it, turning a shared
    parse back into nine separate ones without anyone noticing.
    """
    global _depth
    _depth += 1
    try:
        yield
    finally:
        _depth -= 1
        if _depth == 0:
            clear()
