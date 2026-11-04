"""Command output as one spoken sentence (code.md 4.6, Phase 3 fixtures)."""

from __future__ import annotations

import pytest

from quill.core.ai.test_summary import summarize_output, trim_for_model

PYTEST_FAIL = """\
============================= test session starts =============================
collected 13 items

tests/test_cli.py ............F                                          [100%]

=================================== FAILURES ===================================
FAILED tests/test_cli.py::test_verbose_prints_names - AssertionError: assert 'a.txt' in ''
======================== 1 failed, 12 passed in 0.42s =========================
"""

PYTEST_PASS = "============================== 13 passed in 0.40s ==============================\n"

UNITTEST_FAIL = """\
F..E
======================================================================
FAIL: test_parse_date (test_dates.DateTests)
----------------------------------------------------------------------
ERROR: test_empty_file (test_files.FileTests)
----------------------------------------------------------------------
Ran 4 tests in 0.003s

FAILED (failures=1, errors=1)
"""

JEST_FAIL = """\
 FAIL  src/sum.test.js
  \u2715 adds negative numbers (3 ms)
  \u2713 adds 1 + 2 (1 ms)

Tests:       1 failed, 12 passed, 13 total
"""

DOTNET_FAIL = """\
  Failed Calc.Tests.Adds [12 ms]
Failed!  - Failed:     1, Passed:    12, Skipped:     0, Total:    13, Duration: 1 s
"""

CARGO_FAIL = """\
test tests::adds ... ok
test tests::parses_dates ... FAILED

test result: FAILED. 12 passed; 1 failed; 0 ignored; 0 measured; 0 filtered out
"""

GO_FAIL = """\
--- FAIL: TestParse (0.00s)
    parse_test.go:12: got 1 want 2
--- PASS: TestAdd (0.00s)
FAIL
FAIL\texample.com/calc\t0.01s
"""

TRACEBACK = """\
Traceback (most recent call last):
  File "C:\\proj\\parser.py", line 88, in <module>
    print(tokn)
NameError: name 'tokn' is not defined
"""

COMPILER = """\
Program.cs(88,5): error CS0103: The name 'tokn' does not exist in the current context
Program.cs(90,1): error CS1002: ; expected
Util.cs(3,1): error CS0246: The type 'Foo' could not be found
"""


@pytest.mark.parametrize(
    ("output", "code", "expected"),
    [
        (PYTEST_FAIL, 1, "Tests: 12 passed, 1 failed: test_verbose_prints_names."),
        (PYTEST_PASS, 0, "Tests: 13 passed."),
        (
            UNITTEST_FAIL,
            1,
            ("Tests: 2 passed, 1 failed, 1 error: test_parse_date, test_empty_file."),
        ),
        (JEST_FAIL, 1, "Tests: 12 passed, 1 failed: adds negative numbers."),
        (DOTNET_FAIL, 1, "Tests: 12 passed, 1 failed: Calc.Tests.Adds."),
        (CARGO_FAIL, 101, "Tests: 12 passed, 1 failed: parses_dates."),
        (GO_FAIL, 1, "Tests: 1 passed, 1 failed: TestParse."),
        (
            TRACEBACK,
            1,
            "The program stopped with an error in parser.py line 88: NameError: name 'tokn' is "
            "not defined",
        ),
        (
            COMPILER,
            1,
            "Build failed: 3 errors. The first is in Program.cs line 88: The name 'tokn' does "
            "not exist in the current context",
        ),
    ],
)
def test_runners(output: str, code: int, expected: str) -> None:
    assert summarize_output(output, code) == expected


def test_unknown_runner_fallback() -> None:
    said = summarize_output("working...\nsomething broke: disk error\n", 2)
    assert said == (
        "The command ended with exit code 2. The last error line was: something broke: disk error"
    )
    assert summarize_output("all good\n", 0) == "The command finished without errors."


def test_command_not_found_is_a_plain_question() -> None:
    out = (
        "'pytest' is not recognized as an internal or external command,\n"
        "operable program or batch file.\n"
    )
    assert summarize_output(out, 1) == (
        "The command pytest was not found. Is pytest installed in this project's Python?"
    )


def test_colour_codes_are_ignored() -> None:
    coloured = "\x1b[32m======== 3 passed in 0.1s ========\x1b[0m\n"
    assert summarize_output(coloured, 0) == "Tests: 3 passed."


def test_trim_for_model_keeps_failures_and_the_tail() -> None:
    big = "noise\n" * 5000 + PYTEST_FAIL
    text = trim_for_model(big, "Tests: 12 passed, 1 failed: test_verbose_prints_names.")
    assert text.startswith("Result: Tests: 12 passed")
    assert "FAILED tests/test_cli.py::test_verbose_prints_names" in text
    assert len(text) < 8000
