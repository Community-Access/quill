"""Error-code completeness gate (GATE-EC, #873 follow-up sweep).

Every custom top-level exception class in ``quill/core``, ``quill/io``, and
``quill/stability`` (i.e. every ``class X(Exception):`` or, once migrated,
``class X(CodedError):``) must carry a stable, greppable
:class:`quill.core.error_codes.CodedError` code, so a pasted error message
alone tells support which failure branch fired. This gate walks the AST for
every such class and fails if it does not also list ``CodedError`` among its
bases, define its own ``code = "..."`` class attribute in the
``QUILL-<DOMAIN>-<SUBSYSTEM>-<REASON>`` shape, and use a code no other class
already uses.

Note the migrated shape is ``class X(CodedError):``, NOT
``class X(Exception, CodedError):`` -- since ``CodedError`` itself already
inherits ``Exception``, listing both explicitly (in that order) is an
unresolvable MRO and raises ``TypeError`` at class-definition time. Because
``CodedError`` already IS-A ``Exception``, ``class X(CodedError):`` alone is
sufficient and is the only valid migrated shape.

A subclass of an already-migrated custom error (e.g.
``SpeechCancelledError(SpeechError)``) is not itself a direct
``Exception``/``CodedError`` subclass, so it is not required to redeclare a
code -- it inherits its parent's ``__str__`` behavior and code unless it
chooses to override them.
"""

from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

_PACKAGE_ROOT = Path(__file__).resolve().parents[1]
_SCAN_DIRS = ("core", "io", "stability")

#: Files whose exception classes deliberately carry no code, keyed by
#: repo-relative path with the reason. Keep this list as short as it can be:
#: an exemption is a hole in the gate, and the only defensible one is a file
#: that *cannot* import ``CodedError`` at all. Both entries here are vendored
#: byte-identical into podHarvest, which is exactly why they cannot -- an
#: import of anything from ``quill`` would end the byte-identity a drift test
#: in each repo depends on.
VENDORED_EXEMPT: dict[str, str] = {
    "quill/core/speech/audio_tags_core.py": (
        "Vendored byte-identical into podHarvest (see "
        "docs/superpowers/specs/ALIGNMENT-audio-tags-and-chapters.md). It "
        "imports nothing from quill -- that is what makes byte-identity "
        "possible -- so it cannot reach CodedError. Its plain AudioTagError, "
        "TagReadError, TagWriteError and ChapterEditError are retranslated "
        "into coded twins at QUILL's adapter boundary in "
        "quill/core/speech/audio_tags.py and quill/core/speech/chapters.py, "
        "so every error a caller in this repo actually sees still carries a "
        "code. Enforced by TestAdapter in "
        "tests/unit/core/speech/test_audio_tags.py."
    ),
    "quill/core/podcasts/reuse_core.py": (
        "The second vendored module, shared byte-identical with podHarvest "
        "(podharvest/reuse_core.py, with a SHA-256 drift test in each repo). "
        "Like audio_tags_core it imports nothing from quill, so its "
        "TranscriptParseError cannot inherit CodedError. Callers in this repo "
        "reach it through quill/core/podcasts/transcript_choice.py and "
        "transcripts.py, which is where the coded error a caller actually "
        "sees is raised."
    ),
    "quill/core/speech/reuse_core.py": (
        "Same module, whichever path it is vendored at. Listed twice rather "
        "than matched by name so an exemption can never widen to a file that "
        "merely shares a filename."
    ),
}

_CODE_RE = re.compile(r"^QUILL-[A-Z0-9]+(-[A-Z0-9]+){1,4}$")

#: Builtin exception base names that, when subclassed directly, make a class a
#: GATE-EC candidate just as ``Exception`` does. Matching only the literal
#: ``Exception``/``CodedError`` names let an uncoded ``class X(ValueError):``
#: (or ``RuntimeError``/``OSError``/...) slip past the gate entirely. A class
#: that instead derives from an *already-coded custom* error (e.g.
#: ``SpeechCancelledError(SpeechError)``) inherits its parent's code and is
#: intentionally NOT a candidate -- those base names are not builtins, so they
#: are absent here.
_BUILTIN_EXCEPTION_BASES: frozenset[str] = frozenset({
    "BaseException",
    "Exception",
    "ArithmeticError",
    "OverflowError",
    "AssertionError",
    "AttributeError",
    "BufferError",
    "EOFError",
    "ImportError",
    "ModuleNotFoundError",
    "LookupError",
    "IndexError",
    "KeyError",
    "MemoryError",
    "NameError",
    "NotImplementedError",
    "OSError",
    "IOError",
    "EnvironmentError",
    "BlockingIOError",
    "ChildProcessError",
    "ConnectionError",
    "BrokenPipeError",
    "ConnectionAbortedError",
    "ConnectionRefusedError",
    "ConnectionResetError",
    "FileExistsError",
    "FileNotFoundError",
    "InterruptedError",
    "IsADirectoryError",
    "NotADirectoryError",
    "PermissionError",
    "ProcessLookupError",
    "TimeoutError",
    "ReferenceError",
    "RuntimeError",
    "RecursionError",
    "StopIteration",
    "SyntaxError",
    "SystemError",
    "TypeError",
    "UnboundLocalError",
    "UnicodeError",
    "UnicodeDecodeError",
    "UnicodeEncodeError",
    "ValueError",
})


def _base_names(node: ast.ClassDef) -> set[str]:
    return {b.id for b in node.bases if isinstance(b, ast.Name)}


def _own_code_value(node: ast.ClassDef) -> str | None:
    for stmt in node.body:
        target: ast.expr | None = None
        value: ast.expr | None = None
        if isinstance(stmt, ast.Assign) and len(stmt.targets) == 1:
            target, value = stmt.targets[0], stmt.value
        elif isinstance(stmt, ast.AnnAssign):
            target, value = stmt.target, stmt.value
        if (
            isinstance(target, ast.Name)
            and target.id == "code"
            and isinstance(value, ast.Constant)
            and isinstance(value.value, str)
        ):
            return value.value
    return None


def _classes_with_exception_base(source: str, filename: str) -> dict[str, ast.ClassDef]:
    """Return {"<filename>::<ClassName>": node} for every class whose bases
    include a builtin exception name -- ``Exception`` or any concrete builtin
    like ``ValueError``/``RuntimeError``/``OSError`` (not yet migrated) -- or
    ``CodedError`` (already migrated -- re-checked so a future edit can't
    silently drop the mixin or the code). See ``_BUILTIN_EXCEPTION_BASES``.

    Excludes ``CodedError`` itself (defined in ``core/error_codes.py``): it is
    the generic base every other class here is required to mix in, with an
    intentionally empty default ``code`` for subclasses to override -- it is
    not itself a failure mode that needs a code.
    """
    found: dict[str, ast.ClassDef] = {}
    tree = ast.parse(source, filename=filename)
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        if node.name == "CodedError" and filename.endswith("core/error_codes.py"):
            continue
        bases = _base_names(node)
        if bases & _BUILTIN_EXCEPTION_BASES or "CodedError" in bases:
            found[f"{filename}::{node.name}"] = node
    return found


def _check_classes(classes: dict[str, ast.ClassDef]) -> list[str]:
    errors: list[str] = []
    seen_codes: dict[str, str] = {}
    for site, node in sorted(classes.items()):
        bases = _base_names(node)
        if "CodedError" not in bases:
            errors.append(f"{site}: does not inherit CodedError")
            continue
        code = _own_code_value(node)
        if not code:
            errors.append(f'{site}: inherits CodedError but has no own code = "..." attribute')
            continue
        if not _CODE_RE.match(code):
            errors.append(
                f"{site}: code {code!r} does not match QUILL-<DOMAIN>-<SUBSYSTEM>-<REASON>"
            )
            continue
        if code in seen_codes:
            errors.append(f"{site}: code {code!r} duplicates {seen_codes[code]}")
            continue
        seen_codes[code] = site
    return errors


def find_violations_in_source(source: str, filename: str) -> list[str]:
    """Return violation strings for a single in-memory source string."""
    return _check_classes(_classes_with_exception_base(source, filename))


def discover_exception_classes() -> dict[str, ast.ClassDef]:
    """Return every not-yet-migrated or already-migrated candidate class
    (``class X(Exception):`` or ``class X(CodedError):``) across the scanned
    dirs."""
    found: dict[str, ast.ClassDef] = {}
    for scan_dir in _SCAN_DIRS:
        root = _PACKAGE_ROOT / scan_dir
        if not root.is_dir():
            continue
        for path in sorted(root.rglob("*.py")):
            rel = path.relative_to(_PACKAGE_ROOT.parent).as_posix()
            if rel in VENDORED_EXEMPT:
                continue
            source = path.read_text(encoding="utf-8")
            found.update(_classes_with_exception_base(source, rel))
    return found


def find_violations() -> list[str]:
    """Return violation strings for the live tree; empty means the gate passes."""
    return _check_classes(discover_exception_classes())


def main() -> int:
    errors = find_violations()
    if errors:
        print("error_code_audit: FAIL", file=sys.stderr)
        for line in errors:
            print(f"  - {line}", file=sys.stderr)
        return 1
    print(f"error_code_audit: OK ({len(discover_exception_classes())} classes checked)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
