"""Tiers 2 and 3: checkers the user already has installed.

**The allowlist is** :data:`CHECKER_TOOLS` **and nothing else.** Each entry is a
fixed executable name, the fixed arguments it is run with, and the parser that
reads what it says. Approved by the user on 2026-11-06; a new executable is a
deliberate change here *and* in ``tests/unit/core/test_problems_outside.py``,
which freezes the table. This is not the external-engine allowlist
(``quill/core/ai/external_engine.py``), which answers a different question and
is not widened for this.

The security model, in full (docs/design/syntax-checking.md says the same):

* found with :func:`shutil.which` only -- never downloaded, never installed;
* run through :func:`quill.stability.safe_subprocess.run_subprocess_safely`:
  an argv list, no shell, a 15-second timeout, the environment unchanged;
* the working directory is the file's own folder, so the tool finds the
  project's own configuration as it would from a terminal;
* an unsaved or modified document is checked as a temporary copy with the same
  name, in a fresh temporary folder that is deleted afterwards, and the copy's
  path is mapped back to the document's in every message;
* local processes only. Nothing here opens a network connection, which is why
  the network egress audit has no row for it.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import tempfile
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType

from quill.core.problems.model import Problem, normalize_severity

#: Seconds a tool gets before it is stopped.
TIMEOUT_SECONDS = 15.0

Parser = Callable[[str, str], list[Problem]]
Runner = Callable[..., "subprocess.CompletedProcess[str]"]


# -- parsers: (combined output, the checked file's name) -> problems ----------- #

_GCC_LINE = re.compile(
    r"^(?P<file>.+?):(?P<line>\d+):(?:(?P<col>\d+):)?\s*"
    r"(?:(?P<sev>fatal error|error|warning|note|info|style)\s*:)?\s*(?P<msg>.*)$"
)


def _same_file(reported: str, name: str) -> bool:
    reported = reported.strip().strip('"')
    return Path(reported).name.lower() == name.lower() or reported in {"-", "<stdin>"}


def parse_gcc_style(
    output: str, name: str, *, source: str = "", default: str = "error"
) -> list[Problem]:
    """``file:line:column: severity: message`` -- gcc, clang, shellcheck -f gcc,
    gofmt -e and ruby -c all speak this, with or without the column."""
    problems: list[Problem] = []
    for raw in output.splitlines():
        match = _GCC_LINE.match(raw.strip())
        if match is None or not _same_file(match.group("file"), name):
            continue
        message = match.group("msg").strip()
        if not message:
            continue
        problems.append(
            Problem(
                int(match.group("line")),
                int(match.group("col") or 1),
                normalize_severity(match.group("sev") or default),
                message,
                source,
            )
        )
    return problems


def parse_gcc(output: str, name: str) -> list[Problem]:
    return parse_gcc_style(output, name, source="compiler")


def parse_shellcheck(output: str, name: str) -> list[Problem]:
    return parse_gcc_style(output, name, source="shellcheck", default="warning")


def parse_gofmt(output: str, name: str) -> list[Problem]:
    return parse_gcc_style(output, name, source="gofmt")


_MSBUILD_LINE = re.compile(
    r"^(?P<file>.+?)\((?P<line>\d+),(?P<col>\d+)\):\s*(?P<sev>error|warning|info)\s+"
    r"(?P<code>[A-Z]+\d+)\s*:\s*(?P<msg>.*)$"
)


def parse_msbuild_style(output: str, name: str, *, source: str) -> list[Problem]:
    """``file(line,column): error CODE: message`` -- tsc and csc."""
    problems: list[Problem] = []
    for raw in output.splitlines():
        match = _MSBUILD_LINE.match(raw.strip())
        if match is None or not _same_file(match.group("file"), name):
            continue
        problems.append(
            Problem(
                int(match.group("line")),
                int(match.group("col")),
                normalize_severity(match.group("sev")),
                f"{match.group('msg').strip()} ({match.group('code')})",
                source,
            )
        )
    return problems


def parse_tsc(output: str, name: str) -> list[Problem]:
    return parse_msbuild_style(output, name, source="tsc")


def parse_csc(output: str, name: str) -> list[Problem]:
    return parse_msbuild_style(output, name, source="csc")


_NODE_HEAD = re.compile(r"^(?P<file>.+?):(?P<line>\d+)$")
_NODE_ERROR = re.compile(r"^(?P<kind>\w*Error): (?P<msg>.*)$")


def parse_node_check(output: str, name: str) -> list[Problem]:
    """``node --check``: a ``file:line`` header, the source line, a caret under
    the column, a blank line, then ``SyntaxError: message``."""
    lines = output.splitlines()
    line_number = column = None
    for index, raw in enumerate(lines):
        head = _NODE_HEAD.match(raw.strip())
        if head is not None and _same_file(head.group("file"), name):
            line_number = int(head.group("line"))
            if index + 2 < len(lines) and "^" in lines[index + 2]:
                column = lines[index + 2].index("^") + 1
            continue
        error = _NODE_ERROR.match(raw.strip())
        if error is not None and line_number is not None:
            message = error.group("msg").strip()
            return [Problem(line_number, column or 1, "error", message, "node")]
    return []


def parse_eslint_json(output: str, name: str) -> list[Problem]:
    try:
        results = json.loads(output[output.find("[") :] if "[" in output else output)
    except (json.JSONDecodeError, ValueError):
        return []
    problems: list[Problem] = []
    for result in results if isinstance(results, list) else []:
        if not _same_file(str(result.get("filePath", name)), name):
            continue
        for message in result.get("messages", []):
            rule = message.get("ruleId")
            text = str(message.get("message", "")).strip() + (f" ({rule})" if rule else "")
            problems.append(
                Problem(
                    int(message.get("line") or 1),
                    int(message.get("column") or 1),
                    "error" if int(message.get("severity") or 2) >= 2 else "warning",
                    text,
                    "eslint",
                )
            )
    return problems


def parse_ruff_json(output: str, name: str) -> list[Problem]:
    try:
        results = json.loads(output[output.find("[") :] if "[" in output else output)
    except (json.JSONDecodeError, ValueError):
        return []
    problems: list[Problem] = []
    for item in results if isinstance(results, list) else []:
        if not _same_file(str(item.get("filename", name)), name):
            continue
        location = item.get("location") or {}
        code = item.get("code")
        problems.append(
            Problem(
                int(location.get("row") or 1),
                int(location.get("column") or 1),
                "error"
                if not code or str(code).startswith(("E9", "F63", "F7", "F82"))
                else "warning",
                str(item.get("message", "")).strip() + (f" ({code})" if code else ""),
                "ruff",
            )
        )
    return problems


_PHP_LINE = re.compile(
    r"(?:PHP )?(?P<sev>Parse error|Fatal error|Warning|Deprecated|Notice):\s*(?P<msg>.*?)"
    r" in (?P<file>.+?) on line (?P<line>\d+)"
)


def parse_php_lint(output: str, name: str) -> list[Problem]:
    problems: list[Problem] = []
    for raw in output.splitlines():
        match = _PHP_LINE.search(raw)
        if match is None or not _same_file(match.group("file"), name):
            continue
        severity = (
            "warning" if match.group("sev") in {"Warning", "Deprecated", "Notice"} else "error"
        )
        problems.append(
            Problem(int(match.group("line")), 1, severity, match.group("msg").strip(), "php")
        )
    return problems


_RUBY_CODE = re.compile(r"^\s*>?\s*(?P<line>\d+)\s*\|")
_RUBY_CARET = re.compile(r"^(?P<lead>\s*\|\s*?)(?P<caret>\^+)\s*(?P<msg>.*)$")


def parse_ruby_check(output: str, name: str) -> list[Problem]:
    """``ruby -c``: the classic ``file:line: message``, or Prism's (Ruby 3.4)
    framed source with ``> N |`` on the line and carets under the column."""
    problems: list[Problem] = []
    pointed: int | None = None
    code_start = 0
    for raw in output.splitlines():
        code = _RUBY_CODE.match(raw)
        if code is not None:
            if raw.lstrip().startswith(">"):
                pointed = int(code.group("line"))
            code_start = raw.index("|") + 2
            continue
        caret = _RUBY_CARET.match(raw)
        if caret is not None and pointed is not None:
            column = max(1, raw.index("^") - code_start + 1)
            problems.append(Problem(pointed, column, "error", caret.group("msg").strip(), "ruby"))
    if problems:
        return problems
    found = parse_gcc_style(output, name, source="ruby")
    return [p for p in found if p.message.lower() != "syntax ok"]


_PERL_LINE = re.compile(r"^(?P<msg>.*?) at (?P<file>.+?) line (?P<line>\d+)(?P<rest>[,.].*)?$")


def parse_perl_check(output: str, name: str) -> list[Problem]:
    problems: list[Problem] = []
    for raw in output.splitlines():
        match = _PERL_LINE.match(raw.strip())
        if match is None or not _same_file(match.group("file"), name):
            continue
        rest = (match.group("rest") or "").strip(" ,.")
        message = match.group("msg").strip() + (f", {rest}" if rest else "")
        problems.append(Problem(int(match.group("line")), 1, "error", message, "perl"))
    return problems


def parse_rustc_json(output: str, name: str) -> list[Problem]:
    problems: list[Problem] = []
    for raw in output.splitlines():
        raw = raw.strip()
        if not raw.startswith("{"):
            continue
        try:
            item = json.loads(raw)
        except json.JSONDecodeError:
            continue
        spans = [s for s in item.get("spans", []) if s.get("is_primary")]
        if not spans or not _same_file(str(spans[0].get("file_name", "")), name):
            continue
        code = (item.get("code") or {}).get("code")
        problems.append(
            Problem(
                int(spans[0].get("line_start") or 1),
                int(spans[0].get("column_start") or 1),
                normalize_severity(item.get("level")),
                str(item.get("message", "")).strip() + (f" ({code})" if code else ""),
                "rustc",
            )
        )
    return problems


_XMLLINT_LINE = re.compile(
    r"^(?P<file>.+?):(?P<line>\d+):\s*(?P<kind>[\w ]*?)\s*(?P<sev>error|warning)\s*:\s*(?P<msg>.*)$"
)


def parse_xmllint(output: str, name: str) -> list[Problem]:
    lines = output.splitlines()
    problems: list[Problem] = []
    for index, raw in enumerate(lines):
        match = _XMLLINT_LINE.match(raw.strip())
        if match is None or not _same_file(match.group("file"), name):
            continue
        column = 1
        if index + 2 < len(lines) and lines[index + 2].strip() == "^":
            column = lines[index + 2].index("^") + 1
        problems.append(
            Problem(
                int(match.group("line")),
                column,
                normalize_severity(match.group("sev")),
                match.group("msg").strip(),
                "xmllint",
            )
        )
    return problems


# -- the allowlist ------------------------------------------------------------- #


@dataclass(frozen=True, slots=True)
class CheckerTool:
    """One allowed outside checker. ``args`` are fixed; ``{file}`` is the file
    checked and ``{out}`` a throwaway folder for anything it insists on writing."""

    executable: str
    languages: tuple[str, ...]
    args: tuple[str, ...]
    parser: Parser
    #: Said in the design note and the guide: what running it does beyond reading.
    caveat: str = ""


CHECKER_TOOLS: Mapping[str, CheckerTool] = MappingProxyType({
    "node": CheckerTool("node", ("javascript",), ("--check", "{file}"), parse_node_check),
    "tsc": CheckerTool(
        "tsc", ("typescript",), ("--noEmit", "--pretty", "false", "{file}"), parse_tsc
    ),
    "eslint": CheckerTool(
        "eslint",
        ("javascript", "typescript"),
        ("--format", "json", "{file}"),
        parse_eslint_json,
        caveat="loads the project's own eslint configuration, which is JavaScript",
    ),
    "ruff": CheckerTool(
        "ruff",
        ("python",),
        ("check", "--output-format", "json", "--no-cache", "{file}"),
        parse_ruff_json,
    ),
    "php": CheckerTool("php", ("php",), ("-l", "{file}"), parse_php_lint),
    "ruby": CheckerTool("ruby", ("ruby",), ("-c", "{file}"), parse_ruby_check),
    "perl": CheckerTool(
        "perl",
        ("perl",),
        ("-c", "{file}"),
        parse_perl_check,
        caveat="runs the file's BEGIN blocks and use statements, as perl -c always does",
    ),
    "shellcheck": CheckerTool("shellcheck", ("shell",), ("-f", "gcc", "{file}"), parse_shellcheck),
    "gcc": CheckerTool("gcc", ("c", "c++"), ("-fsyntax-only", "{file}"), parse_gcc),
    "clang": CheckerTool("clang", ("c", "c++"), ("-fsyntax-only", "{file}"), parse_gcc),
    "gofmt": CheckerTool("gofmt", ("go",), ("-e", "-l", "{file}"), parse_gofmt),
    "rustc": CheckerTool(
        "rustc",
        ("rust",),
        ("--error-format=json", "--emit=metadata", "--out-dir", "{out}", "{file}"),
        parse_rustc_json,
    ),
    "csc": CheckerTool(
        "csc",
        ("c#",),
        ("-nologo", "-target:library", "-out:{out}/check.dll", "{file}"),
        parse_csc,
    ),
    "xmllint": CheckerTool("xmllint", ("xml",), ("--noout", "{file}"), parse_xmllint),
})

#: Languages where only one of several tools needs to run: the first found wins.
FIRST_FOUND: Mapping[str, tuple[str, ...]] = MappingProxyType({
    "c": ("gcc", "clang"),
    "c++": ("gcc", "clang"),
})

#: Said instead of running anything, because a single-file check is not
#: something the tool can do.
NEEDS_A_PROJECT: Mapping[str, str] = MappingProxyType({
    "c#": "dotnet build checks C# only as part of a project; csc checks a single file"
})


def tools_for(language: str) -> tuple[str, ...]:
    """The allowlisted tools that check *language*, in the order they run."""
    return tuple(name for name, tool in CHECKER_TOOLS.items() if language in tool.languages)


@dataclass(frozen=True, slots=True)
class OutsideResult:
    problems: tuple[Problem, ...]
    ran: tuple[str, ...]
    notes: tuple[str, ...]


def is_batch_shim(executable: str) -> bool:
    """True for a ``.cmd`` or ``.bat`` file, which Windows runs through cmd.exe."""
    return Path(executable).suffix.lower() in {".cmd", ".bat"}


def run_outside_checkers(
    text: str,
    *,
    language: str,
    path: Path | None,
    modified: bool,
    which: Callable[[str], str | None] = shutil.which,
    run: Runner | None = None,
) -> OutsideResult:
    """Every allowlisted tool for *language* that :func:`shutil.which` finds."""
    names = tools_for(language)
    if not names:
        return OutsideResult((), (), ())
    found: list[tuple[str, str]] = []
    skipped: list[str] = []
    for name in names:
        executable = which(CHECKER_TOOLS[name].executable)
        if executable and is_batch_shim(executable):
            # npm installs eslint and tsc as .cmd shims. Windows runs those
            # through cmd.exe, which reads & | ^ % in the file name as
            # commands, and Python cannot quote them safely ("BatBadBut").
            # A shim is never started; the note says why it was skipped.
            skipped.append(name)
            continue
        if executable:
            found.append((name, executable))
    if language in FIRST_FOUND:
        found = found[:1]
    shim_notes = tuple(
        f"{name} is installed as a batch file, which QUILL does not run" for name in skipped
    )
    if not found:
        return OutsideResult((), (), shim_notes)
    if run is None:
        from quill.stability.safe_subprocess import run_subprocess_safely

        run = run_subprocess_safely
    problems: list[Problem] = []
    ran: list[str] = []
    notes: list[str] = list(shim_notes)
    file_name = path.name if path is not None else f"untitled{_extension_for(language)}"
    # ignore_cleanup_errors: antivirus or a tool's leftover child can hold the
    # folder for a moment, and that must not throw away what was found.
    with tempfile.TemporaryDirectory(prefix="quill-check-", ignore_cleanup_errors=True) as scratch:
        scratch_dir = Path(scratch)
        if path is not None and not modified and path.is_file():
            target = path
        else:
            copy_dir = scratch_dir / "copy"
            copy_dir.mkdir()
            target = copy_dir / file_name
            target.write_text(text, encoding="utf-8", newline="")
        cwd = path.parent if path is not None and path.parent.is_dir() else target.parent
        out_dir = scratch_dir / "out"
        out_dir.mkdir()
        for name, executable in found:
            tool = CHECKER_TOOLS[name]
            argv = [executable] + [
                arg.replace("{file}", str(target)).replace("{out}", str(out_dir))
                for arg in tool.args
            ]
            try:
                completed = run(argv, timeout_seconds=TIMEOUT_SECONDS, cwd=str(cwd))
            except subprocess.TimeoutExpired:
                notes.append(
                    f"{name} took longer than {int(TIMEOUT_SECONDS)} seconds and was stopped"
                )
                continue
            except (OSError, ValueError) as error:
                notes.append(f"{name} could not be run: {error}")
                continue
            ran.append(name)
            output = "\n".join(part for part in (completed.stdout, completed.stderr) if part)
            output = output.replace(str(target), file_name)
            found_here = tool.parser(output, file_name)
            if not found_here and completed.returncode not in (0, None) and name not in {"gofmt"}:
                first = next((ln.strip() for ln in output.splitlines() if ln.strip()), "")
                if first:
                    notes.append(f"{name} could not check this file: {first[:160]}")
            problems.extend(found_here)
    return OutsideResult(tuple(problems), tuple(ran), tuple(notes))


_EXTENSIONS = {
    "javascript": ".js",
    "typescript": ".ts",
    "python": ".py",
    "php": ".php",
    "ruby": ".rb",
    "perl": ".pl",
    "shell": ".sh",
    "c": ".c",
    "c++": ".cpp",
    "go": ".go",
    "rust": ".rs",
    "c#": ".cs",
    "xml": ".xml",
}


def _extension_for(language: str) -> str:
    return _EXTENSIONS.get(language, ".txt")
