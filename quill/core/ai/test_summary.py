"""A command's output, as the one sentence that is spoken (code.md 4.6) -- wx-free.

Finding the one failing test in a terminal means reviewing line by line. So
QUILL reads the output of the common test runners and build tools and says
the result in one sentence -- "Tests: 41 passed, 2 failed: test_parse_date,
test_empty_file." -- and the full output stays a document one key away.

Recognised: pytest, unittest, Jest (and Vitest's matching summary), dotnet
test, cargo test and go test; Python tracebacks, and compiler errors in the
``file(line,col): error`` and ``file:line:col: error`` shapes. Anything else
gets the honest fallback: "The command ended with exit code 1. The last error
line was: ..." A command Windows or the shell could not find gets a plain
question rather than a stack trace.

:func:`trim_for_model` is what the engine reads back: the sentence, the
failure lines, and the end of the output, within a budget.
"""

from __future__ import annotations

import re

__all__ = ["summarize_output", "trim_for_model"]

_ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")
_MAX_NAMES = 3
#: Jest marks a failed test with a cross: U+2715, U+00D7 or U+2717.
_CROSSES = "|".join(chr(code) for code in (0x2715, 0x00D7, 0x2717))
_JEST_FAIL = r"^\s*(?:" + _CROSSES + r")\s+(.+?)(?:\s+\(\d+\s*ms\))?$"


def _clean(text: str) -> str:
    return _ANSI.sub("", text).replace("\r\n", "\n").replace("\r", "\n")


def _names(names: list[str]) -> str:
    unique = list(dict.fromkeys(n for n in names if n))
    if not unique:
        return ""
    shown = ", ".join(unique[:_MAX_NAMES])
    more = len(unique) - _MAX_NAMES
    return f": {shown}" + (f", and {more} more" if more > 0 else "")


def _counts(pairs: list[tuple[int, str]]) -> str:
    """Counts as words, such as 12 passed, 1 error. Only "errors" changes with n."""
    return ", ".join(
        f"{n} {'error' if word == 'errors' and n == 1 else word}" for n, word in pairs if n
    )


def _pytest(text: str) -> str | None:
    lines = [ln for ln in text.splitlines() if re.match(r"^=+ .* =+$", ln.strip())]
    tail = next(
        (ln for ln in reversed(lines) if re.search(r"\b(passed|failed|error|no tests ran)", ln)),
        None,
    )
    if tail is None:
        short = re.search(r"^(\d+ (passed|failed).*?) in [\d.]+s", text, re.M)
        tail = short.group(1) if short else None
    if tail is None:
        return None
    if "no tests ran" in tail:
        return "Tests: no tests ran."
    found = {
        w: int(n) for n, w in re.findall(r"(\d+) (passed|failed|errors?|skipped|xfailed)", tail)
    }
    failed = found.get("failed", 0)
    errors = found.get("error", 0) + found.get("errors", 0)
    names = [m.split("::")[-1] for m in re.findall(r"^(?:FAILED|ERROR) (\S+)", text, re.M)]
    head = _counts([
        (found.get("passed", 0), "passed"),
        (failed, "failed"),
        (errors, "errors"),
        (found.get("skipped", 0), "skipped"),
    ])
    return f"Tests: {head or 'none ran'}{_names(names) if failed or errors else ''}."


def _unittest(text: str) -> str | None:
    ran = re.search(r"^Ran (\d+) tests? in", text, re.M)
    if not ran:
        return None
    total = int(ran.group(1))
    failed = re.search(r"^FAILED \(([^)]*)\)", text, re.M)
    if not failed:
        return f"Tests: {total} passed."
    nums = dict(
        (k, int(v)) for k, v in re.findall(r"(failures|errors|skipped)=(\d+)", failed.group(1))
    )
    bad = nums.get("failures", 0) + nums.get("errors", 0)
    names = re.findall(r"^(?:FAIL|ERROR): (\w+)", text, re.M)
    head = _counts([
        (total - bad - nums.get("skipped", 0), "passed"),
        (nums.get("failures", 0), "failed"),
        (nums.get("errors", 0), "errors"),
    ])
    return f"Tests: {head}{_names(names)}."


def _jest(text: str) -> str | None:
    line = re.search(r"^Tests:\s+(.*\d+ total.*)$", text, re.M)
    if not line:
        return None
    found = {w: int(n) for n, w in re.findall(r"(\d+) (passed|failed|skipped|todo)", line.group(1))}
    names = [n.strip() for n in re.findall(_JEST_FAIL, text, re.M)]
    head = _counts([
        (found.get("passed", 0), "passed"),
        (found.get("failed", 0), "failed"),
        (found.get("skipped", 0), "skipped"),
    ])
    return f"Tests: {head}{_names(names) if found.get('failed') else ''}."


def _dotnet(text: str) -> str | None:
    line = re.search(
        r"(Passed|Failed)!\s+-\s+Failed:\s+(\d+),\s+Passed:\s+(\d+),\s+Skipped:\s+(\d+)", text
    )
    if not line:
        return None
    failed, passed, skipped = int(line.group(2)), int(line.group(3)), int(line.group(4))
    names = re.findall(r"^\s*Failed (\S+) \[", text, re.M)
    head = _counts([(passed, "passed"), (failed, "failed"), (skipped, "skipped")])
    return f"Tests: {head}{_names(names) if failed else ''}."


def _cargo(text: str) -> str | None:
    results = re.findall(
        r"test result: (?:ok|FAILED)\. (\d+) passed; (\d+) failed; (\d+) ignored", text
    )
    if not results:
        return None
    passed = sum(int(r[0]) for r in results)
    failed = sum(int(r[1]) for r in results)
    ignored = sum(int(r[2]) for r in results)
    names = [n.split("::")[-1] for n in re.findall(r"^test (\S+) \.\.\. FAILED", text, re.M)]
    head = _counts([(passed, "passed"), (failed, "failed"), (ignored, "ignored")])
    return f"Tests: {head or 'none ran'}{_names(names) if failed else ''}."


def _go(text: str) -> str | None:
    fails = re.findall(r"^\s*--- FAIL: (\S+)", text, re.M)
    passes = re.findall(r"^\s*--- PASS: (\S+)", text, re.M)
    ok_pkgs = re.findall(r"^ok\s+\S+", text, re.M)
    bad_pkgs = re.findall(r"^FAIL\s+\S+", text, re.M)
    if not (fails or passes or ok_pkgs or bad_pkgs):
        return None
    if passes or fails:
        head = _counts([(len(passes), "passed"), (len(fails), "failed")])
    else:
        head = _counts([(len(ok_pkgs), "packages passed"), (len(bad_pkgs), "packages failed")])
    return f"Tests: {head}{_names(fails)}."


def _python_error(text: str) -> str | None:
    if "Traceback (most recent call last)" not in text:
        return None
    frames = re.findall(r'File "([^"]+)", line (\d+)', text)
    last = [ln for ln in text.strip().splitlines() if re.match(r"^\w*(Error|Exception)\b", ln)]
    if not last:
        return None
    where = ""
    if frames:
        path, line = frames[-1]
        where = f" in {re.split(r'[\\/]', path)[-1]} line {line}"
    return f"The program stopped with an error{where}: {last[-1].strip()}"


def _compiler(text: str) -> str | None:
    shapes = (
        r"^(?P<file>[^\s(:][^(:\n]*)\((?P<line>\d+),\d+\): error \w*:? ?(?P<msg>.+)$",
        r"^(?P<file>[^\s:][^:\n]*):(?P<line>\d+):\d+: (?:fatal )?error:? (?P<msg>.+)$",
        r"^error(?:\[\w+\])?: (?P<msg>.+)\n\s+--> (?P<file>[^:\n]+):(?P<line>\d+)",
    )
    for shape in shapes:
        errors = list(re.finditer(shape, text, re.M))
        if errors:
            first = errors[0]
            name = re.split(r"[\\/]", first.group("file").strip())[-1]
            count = len(errors)
            return (
                f"Build failed: {count} error{'s' if count != 1 else ''}. The first is in "
                f"{name} line {first.group('line')}: {first.group('msg').strip()}"
            )
    return None


def _not_found(text: str, command: str) -> str | None:
    match = re.search(r"'([^']+)' is not recognized as an internal or external command", text)
    if not match:
        match = re.search(r"(?:sh: \d+: |^)(\S+): (?:command )?not found", text, re.M)
    if not match:
        return None
    name = match.group(1)
    hint = {
        "pytest": " Is pytest installed in this project's Python?",
        "python": " Is Python installed and on the PATH?",
        "py": " Is the Python launcher installed?",
        "npm": " Is Node.js installed?",
        "node": " Is Node.js installed?",
        "dotnet": " Is the .NET SDK installed?",
        "cargo": " Is Rust installed?",
        "go": " Is Go installed?",
    }.get(name.lower(), " Is it installed, and is it on the PATH?")
    return f"The command {name} was not found.{hint}"


def summarize_output(output: str, exit_code: int | None, command: str = "") -> str:
    """One sentence for what a command did."""
    text = _clean(output)
    for reader in (_pytest, _unittest, _jest, _dotnet, _cargo, _go):
        said = reader(text)
        if said:
            return said
    if exit_code not in (0, None):
        for reader2 in (_compiler, _python_error):
            said = reader2(text)
            if said:
                return said
        missing = _not_found(text, command)
        if missing:
            return missing
        lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
        error_lines = [ln for ln in lines if re.search(r"error|fail|exception|denied", ln, re.I)]
        last = (error_lines or lines or [""])[-1][:240]
        if last:
            return f"The command ended with exit code {exit_code}. The last error line was: {last}"
        return f"The command ended with exit code {exit_code}, and printed nothing."
    if exit_code is None:
        return "The command was stopped before it finished."
    return "The command finished without errors."


def trim_for_model(output: str, sentence: str, limit: int = 6000) -> str:
    """What the engine reads back: the sentence, failure lines, and the tail."""
    text = _clean(output)
    wanted = [
        ln
        for ln in text.splitlines()
        if re.match(r"^(FAILED|ERROR|FAIL:|E  |\s*--- FAIL|test .* FAILED|\s*Failed )", ln)
        or re.search(r"\berror\b", ln, re.I)
    ][:40]
    head = f"Result: {sentence}\n"
    if wanted:
        head += "Failure lines:\n" + "\n".join(wanted)[: limit // 3] + "\n"
    room = max(500, limit - len(head))
    tail = text[-room:]
    if len(text) > room:
        tail = "...\n" + tail
    return f"{head}Output (end):\n{tail}"
