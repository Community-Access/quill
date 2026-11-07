"""Outside checkers (quill.core.problems.outside): the frozen allowlist, each
parser against output captured from the real tool, and the runner's contract.

No test here needs a tool installed: the parsers read captured text, and the
runner is driven with a fake ``which`` and a fake ``run``.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

import pytest

from quill.core.problems import check_document, summarize
from quill.core.problems.outside import (
    CHECKER_TOOLS,
    TIMEOUT_SECONDS,
    parse_csc,
    parse_eslint_json,
    parse_gcc,
    parse_gofmt,
    parse_node_check,
    parse_perl_check,
    parse_php_lint,
    parse_ruby_check,
    parse_ruff_json,
    parse_rustc_json,
    parse_shellcheck,
    parse_tsc,
    parse_xmllint,
    run_outside_checkers,
)

# -- the allowlist ---------------------------------------------------------------- #

#: The whole allowlist, frozen. Approved by the user on 2026-11-06. A new
#: executable, or a changed argument, is a deliberate edit here as well as in
#: quill/core/problems/outside.py -- that is the point of this test.
FROZEN = {
    "node": ("node", ("javascript",), ("--check", "{file}")),
    "tsc": ("tsc", ("typescript",), ("--noEmit", "--pretty", "false", "{file}")),
    "eslint": ("eslint", ("javascript", "typescript"), ("--format", "json", "{file}")),
    "ruff": ("ruff", ("python",), ("check", "--output-format", "json", "--no-cache", "{file}")),
    "php": ("php", ("php",), ("-l", "{file}")),
    "ruby": ("ruby", ("ruby",), ("-c", "{file}")),
    "perl": ("perl", ("perl",), ("-c", "{file}")),
    "shellcheck": ("shellcheck", ("shell",), ("-f", "gcc", "{file}")),
    "gcc": ("gcc", ("c", "c++"), ("-fsyntax-only", "{file}")),
    "clang": ("clang", ("c", "c++"), ("-fsyntax-only", "{file}")),
    "gofmt": ("gofmt", ("go",), ("-e", "-l", "{file}")),
    "rustc": (
        "rustc",
        ("rust",),
        ("--error-format=json", "--emit=metadata", "--out-dir", "{out}", "{file}"),
    ),
    "csc": ("csc", ("c#",), ("-nologo", "-target:library", "-out:{out}/check.dll", "{file}")),
    "xmllint": ("xmllint", ("xml",), ("--noout", "{file}")),
}


def test_the_allowlist_is_exactly_the_approved_one() -> None:
    actual = {
        name: (tool.executable, tool.languages, tool.args) for name, tool in CHECKER_TOOLS.items()
    }
    assert actual == FROZEN


def test_the_allowlist_cannot_be_changed_at_run_time() -> None:
    with pytest.raises(TypeError):
        CHECKER_TOOLS["sh"] = CHECKER_TOOLS["node"]  # type: ignore[index]


def test_no_entry_runs_a_shell_or_a_network_tool() -> None:
    for tool in CHECKER_TOOLS.values():
        assert tool.executable not in {"cmd", "powershell", "pwsh", "sh", "bash", "curl", "npx"}
        assert "{file}" in tool.args


def test_the_external_engine_allowlist_was_not_widened_for_this() -> None:
    from quill.core.ai import external_engine

    engines = external_engine._ENGINE_EXECUTABLE_BASENAMES
    for name, tool in CHECKER_TOOLS.items():
        if name != "node":  # node was already there, for the accessibility engines
            assert tool.executable not in engines, name
            assert f"{tool.executable}.exe" not in engines, name


# -- parsers, against captured output ------------------------------------------- #

NODE = r"""C:\Users\me\project\bad.js:1
let x = ;
        ^

SyntaxError: Unexpected token ';'
    at wrapSafe (node:internal/modules/cjs/loader:1637:18)
    at checkSyntax (node:internal/main/check_syntax:78:3)

Node.js v22.22.1
"""


def test_node_check() -> None:
    [problem] = parse_node_check(NODE, "bad.js")
    assert (problem.line, problem.column, problem.severity) == (1, 9, "error")
    assert problem.message == "Unexpected token ';'"
    assert parse_node_check("", "bad.js") == []


RUFF = """[
  {"code": "F401", "filename": "C:\\\\p\\\\bad.py", "location": {"column": 8, "row": 1},
   "message": "`os` imported but unused", "severity": "error"},
  {"code": "F821", "filename": "C:\\\\p\\\\bad.py", "location": {"column": 7, "row": 2},
   "message": "Undefined name `y`", "severity": "error"},
  {"code": null, "filename": "C:\\\\p\\\\bad.py", "location": {"column": 5, "row": 3},
   "message": "SyntaxError: Expected an expression"}
]"""


def test_ruff_json() -> None:
    problems = parse_ruff_json(RUFF, "bad.py")
    assert [(p.line, p.column, p.severity) for p in problems] == [
        (1, 8, "warning"),
        (2, 7, "error"),
        (3, 5, "error"),
    ]
    assert problems[1].message == "Undefined name `y` (F821)"
    assert parse_ruff_json("not json", "bad.py") == []


PHP = """
Parse error: syntax error, unexpected token ";" in bad.php on line 2
Errors parsing bad.php
"""


def test_php_lint() -> None:
    [problem] = parse_php_lint(PHP, "bad.php")
    assert (problem.line, problem.severity) == (2, "error")
    assert problem.message == 'syntax error, unexpected token ";"'
    assert parse_php_lint("No syntax errors detected in bad.php", "bad.php") == []


PERL = """syntax error at bad.pl line 1, near "= ;"
bad.pl had compilation errors.
"""


def test_perl_check() -> None:
    [problem] = parse_perl_check(PERL, "bad.pl")
    assert (problem.line, problem.message) == (1, 'syntax error, near "= ;"')
    assert parse_perl_check("bad.pl syntax OK", "bad.pl") == []


GOFMT = """bad.go:4:1: expected operand, found '}'
bad.go:4:3: expected ';', found 'EOF'
"""


def test_gofmt() -> None:
    problems = parse_gofmt(GOFMT, "bad.go")
    assert [(p.line, p.column) for p in problems] == [(4, 1), (4, 3)]
    assert problems[0].message == "expected operand, found '}'"


RUSTC = (
    '{"$message_type":"diagnostic","message":"mismatched types","code":{"code":"E0308",'
    '"explanation":"..."},"level":"error","spans":[{"file_name":"bad.rs","line_start":2,'
    '"column_start":18,"is_primary":true},{"file_name":"bad.rs","line_start":2,'
    '"column_start":12,"is_primary":false}]}\n'
    '{"$message_type":"diagnostic","message":"aborting due to 1 previous error",'
    '"code":null,"level":"error","spans":[]}\n'
)


def test_rustc_json() -> None:
    [problem] = parse_rustc_json(RUSTC, "bad.rs")
    assert (problem.line, problem.column, problem.severity) == (2, 18, "error")
    assert problem.message == "mismatched types (E0308)"


GCC = r"""C:\src\bad.c: In function 'main':
C:\src\bad.c:3:12: error: expected ';' before '}' token
C:\src\bad.c:2:9: warning: unused variable 'x' [-Wunused-variable]
C:\src\other.h:1:1: error: in a header, not this file
"""


def test_gcc_and_clang() -> None:
    problems = parse_gcc(GCC, "bad.c")
    assert [(p.line, p.column, p.severity) for p in problems] == [
        (3, 12, "error"),
        (2, 9, "warning"),
    ]


SHELLCHECK = """bad.sh:3:6: warning: Quote this to prevent word splitting. [SC2046]
bad.sh:5:1: note: Double quote to prevent globbing. [SC2086]
"""


def test_shellcheck_gcc_format() -> None:
    problems = parse_shellcheck(SHELLCHECK, "bad.sh")
    assert [(p.line, p.severity) for p in problems] == [(3, "warning"), (5, "info")]


TSC = "bad.ts(3,7): error TS2322: Type 'string' is not assignable to type 'number'.\n"
CSC = r"C:\src\Bad.cs(4,20): error CS1002: ; expected" + "\n"


def test_tsc_and_csc() -> None:
    [ts] = parse_tsc(TSC, "bad.ts")
    assert (ts.line, ts.column, ts.severity) == (3, 7, "error")
    assert ts.message.endswith("(TS2322)")
    [cs] = parse_csc(CSC, "Bad.cs")
    assert (cs.line, cs.column, cs.message) == (4, 20, "; expected (CS1002)")


ESLINT = (
    '[{"filePath":"C:\\\\p\\\\bad.js","messages":[{"ruleId":"no-undef","severity":2,'
    '"message":"\'y\' is not defined.","line":2,"column":7},{"ruleId":"semi","severity":1,'
    '"message":"Missing semicolon.","line":3,"column":10}],"errorCount":1}]'
)


def test_eslint_json() -> None:
    problems = parse_eslint_json(ESLINT, "bad.js")
    assert [(p.line, p.column, p.severity) for p in problems] == [
        (2, 7, "error"),
        (3, 10, "warning"),
    ]
    assert problems[0].message == "'y' is not defined. (no-undef)"


RUBY_CLASSIC = "bad.rb:3: syntax error, unexpected end-of-input, expecting `end'\n"
RUBY_PRISM = """bad.rb: --> bad.rb
bad.rb:2: syntax errors found (SyntaxError)
  1 | def f
> 2 |   x =
    |       ^ unexpected end-of-input; expected an expression after the operator
"""


def test_ruby_check_both_formats() -> None:
    [classic] = parse_ruby_check(RUBY_CLASSIC, "bad.rb")
    assert (classic.line, classic.severity) == (3, "error")
    [prism] = parse_ruby_check(RUBY_PRISM, "bad.rb")
    assert prism.line == 2
    assert prism.column == 7
    assert prism.message.startswith("unexpected end-of-input")
    assert parse_ruby_check("Syntax OK\n", "bad.rb") == []


XMLLINT = """bad.xml:3: parser error : Opening and ending tag mismatch: b line 2 and a
</a>
    ^
"""


def test_xmllint() -> None:
    [problem] = parse_xmllint(XMLLINT, "bad.xml")
    assert (problem.line, problem.column, problem.severity) == (3, 5, "error")
    assert problem.message.startswith("Opening and ending tag mismatch")


# -- the runner ------------------------------------------------------------------ #


class _Run:
    def __init__(self, stdout: str = "", stderr: str = "", code: int = 1, raises: Any = None):
        self.calls: list[tuple[list[str], dict[str, Any]]] = []
        self.stdout, self.stderr, self.code, self.raises = stdout, stderr, code, raises
        self.saw_file: str | None = None

    def __call__(self, argv: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        self.calls.append((argv, kwargs))
        target = Path(argv[-1])
        self.saw_file = target.read_text(encoding="utf-8") if target.is_file() else None
        if self.raises is not None:
            raise self.raises
        out = self.stdout.replace("{FILE}", str(target))
        return subprocess.CompletedProcess(argv, self.code, out, self.stderr)


def test_an_unsaved_buffer_is_checked_as_a_temporary_copy(tmp_path: Path) -> None:
    saved = tmp_path / "app.js"
    saved.write_text("old text", encoding="utf-8")
    run = _Run(stderr="")
    run.stdout = "{FILE}:1\nlet x = ;\n        ^\n\nSyntaxError: Unexpected token ';'\n"
    result = run_outside_checkers(
        "let x = ;\n",
        language="javascript",
        path=saved,
        modified=True,
        which=lambda name: f"C:/tools/{name}.exe" if name == "node" else None,
        run=run,
    )
    argv, kwargs = run.calls[0]
    assert argv[0] == "C:/tools/node.exe"
    assert argv[1] == "--check"
    assert Path(argv[2]).name == "app.js" and Path(argv[2]) != saved
    assert run.saw_file == "let x = ;\n"
    assert kwargs == {"timeout_seconds": TIMEOUT_SECONDS, "cwd": str(tmp_path)}
    assert not Path(argv[2]).exists(), "the temporary copy is deleted afterwards"
    assert [(p.line, p.column, p.message) for p in result.problems] == [
        (1, 9, "Unexpected token ';'")
    ]
    assert result.ran == ("node",)


def test_a_saved_unmodified_file_is_checked_where_it_is(tmp_path: Path) -> None:
    saved = tmp_path / "ok.php"
    saved.write_text("<?php echo 1;", encoding="utf-8")
    run = _Run(stdout="No syntax errors detected in {FILE}", code=0)
    run_outside_checkers(
        "<?php echo 1;",
        language="php",
        path=saved,
        modified=False,
        which=lambda name: name,
        run=run,
    )
    assert run.calls[0][0] == ["php", "-l", str(saved)]


def test_only_the_first_compiler_found_runs() -> None:
    run = _Run(code=0)
    result = run_outside_checkers(
        "int main(void) { return 0; }",
        language="c",
        path=None,
        modified=True,
        which=lambda name: name,
        run=run,
    )
    assert [argv[0] for argv, _ in run.calls] == ["gcc"]
    assert result.ran == ("gcc",)


def test_a_timeout_and_a_launch_failure_are_notes_not_crashes() -> None:
    slow = _Run(raises=subprocess.TimeoutExpired(["tsc"], TIMEOUT_SECONDS))
    result = run_outside_checkers(
        "let x: number = 1;",
        language="typescript",
        path=None,
        modified=True,
        which=lambda name: name if name == "tsc" else None,
        run=slow,
    )
    assert result.notes == ("tsc took longer than 15 seconds and was stopped",)
    broken = _Run(raises=OSError("access denied"))
    result = run_outside_checkers(
        "x", language="go", path=None, modified=True, which=lambda name: name, run=broken
    )
    assert result.notes[0].startswith("gofmt could not be run")


def test_missing_tools_say_so_and_the_built_in_check_still_runs() -> None:
    report = check_document("print(1)\n", language="python", which=lambda _n: None)
    assert report.checked_with == ("Python",)
    assert summarize(report) == "No problems found."
    report = check_document("puts 1", language="ruby", which=lambda _n: None)
    assert summarize(report) == "No checker installed for Ruby."
    report = check_document("class A {}", language="c#", which=lambda _n: None)
    assert "needs" not in summarize(report)
    assert "project" in summarize(report)


def test_a_tool_that_fails_without_parsable_output_is_reported() -> None:
    run = _Run(stdout="", stderr="Oops! Something went wrong: no config found\n", code=2)
    result = run_outside_checkers(
        "let a = 1;",
        language="javascript",
        path=None,
        modified=True,
        which=lambda name: name if name == "eslint" else None,
        run=run,
    )
    assert result.problems == ()
    assert result.notes == (
        "eslint could not check this file: Oops! Something went wrong: no config found",
    )
