"""Find BITS Accessible Forms' own BFL examples, read-only, for conformance tests.

BAF (``S:\\code\\baf`` on Jeff's machine; set ``QUILL_BAF_ROOT`` to point
elsewhere) keeps its BFL examples in two places: the fenced ``bfl`` blocks of
``docs/user-guide/bfl-language-guide.md`` and the ``$bfl = '...'`` literals of
``tests/unit/BFL/*.php``. This module only reads those files.

A PHP literal built by concatenation (the operator and alias loops in
ParserTest.php) is expanded for each value of its loop, so every case BAF
tests is a case QUILL tests.
"""

from __future__ import annotations

import os
import re
import shutil
from dataclasses import dataclass
from pathlib import Path

DEFAULT_BAF_ROOT = Path(r"S:\code\baf")


@dataclass(frozen=True)
class BafSource:
    """One BFL example from BAF, with where it came from."""

    origin: str  # e.g. "guide:12" or "ParserTest.php:test_parse_columns_with_braces"
    text: str


def baf_root() -> Path | None:
    """BAF's folder, or None when it is not on this machine (CI)."""
    root = Path(os.environ.get("QUILL_BAF_ROOT", str(DEFAULT_BAF_ROOT)))
    if (root / "includes" / "bfl" / "class-baf-bfl-parser.php").is_file():
        return root
    return None


def php_executable() -> str | None:
    return shutil.which("php")


def _php_single(body: str) -> str:
    # PHP single quotes: only \\ and \' are escapes.
    return re.sub(r"\\([\\'])", r"\1", body)


def _php_double(body: str) -> str:
    table = {"n": "\n", "t": "\t", "\\": "\\", '"': '"', "$": "$", "r": "\r"}
    return re.sub(r"\\(.)", lambda m: table.get(m.group(1), "\\" + m.group(1)), body)


_SINGLE = r"'((?:[^'\\]|\\.)*)'"
_DOUBLE = r'"((?:[^"\\]|\\.)*)"'


def guide_sources(root: Path) -> list[BafSource]:
    path = root / "docs" / "user-guide" / "bfl-language-guide.md"
    text = path.read_text(encoding="utf-8")
    out: list[BafSource] = []
    for number, match in enumerate(re.finditer(r"```bfl\n(.*?)```", text, re.S), 1):
        out.append(BafSource(f"guide:{number}", match.group(1)))
    return out


def _loop_values(method_body: str) -> tuple[str, list[str]] | None:
    """The (variable, values) of a ``foreach ( $x as $k => $v )`` loop."""
    keys = re.findall(r"'([a-z_]+)'\s*=>", method_body)
    loop = re.search(r"foreach\s*\(\s*\$\w+\s+as\s+\$(\w+)\s*=>", method_body)
    if not loop or not keys:
        return None
    return loop.group(1), keys


def php_test_sources(root: Path) -> list[BafSource]:
    out: list[BafSource] = []
    for path in sorted((root / "tests" / "unit" / "BFL").glob("*.php")):
        text = path.read_text(encoding="utf-8")
        methods = re.split(r"\n\s*public function ", text)
        for method in methods[1:]:
            name = method.split("(", 1)[0].strip()
            for n, (single, double) in enumerate(
                re.findall(r"\$bfl\s*=\s*(?:" + _SINGLE + "|" + _DOUBLE + ")", method)
            ):
                origin = f"{path.name}:{name}" + (f"#{n + 1}" if n else "")
                if double:
                    out.append(BafSource(origin, _php_double(double)))
                    continue
                concat = re.search(
                    r"\$bfl\s*=\s*" + _SINGLE + r"\s*\.\s*\$(\w+)\s*\.\s*" + _SINGLE, method
                )
                loop = _loop_values(method)
                if concat and loop and concat.group(1) == single:
                    head, var, tail = concat.group(1), concat.group(2), concat.group(3)
                    if var == loop[0]:
                        for value in loop[1]:
                            out.append(
                                BafSource(
                                    f"{origin}[{value}]",
                                    _php_single(head) + value + _php_single(tail),
                                )
                            )
                        continue
                out.append(BafSource(origin, _php_single(single)))
    return out


def all_sources(root: Path) -> list[BafSource]:
    return guide_sources(root) + php_test_sources(root)
