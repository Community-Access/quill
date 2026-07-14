from __future__ import annotations

import sys

import pytest

from quill.stability.safe_subprocess import run_subprocess_safely


def test_decodes_utf8_output_regardless_of_locale() -> None:
    # Regression for #954: on a system whose preferred locale encoding is not
    # UTF-8 (Windows commonly defaults to a legacy code page like CP1252),
    # subprocess.run's default text-mode decoding could fail to decode a
    # UTF-8-emitting tool's output (e.g. Pandoc), leaving stdout as None
    # instead of the actual text. Force encoding="utf-8" so this is
    # independent of the host locale. Writes raw UTF-8 bytes directly (via
    # sys.stdout.buffer) rather than sys.stdout.write() so the *child*
    # process's own console-codepage-dependent text encoding can't also fail
    # -- this test is only exercising the parent-side decode in
    # run_subprocess_safely, not the child's stdout encoding.
    result = run_subprocess_safely(
        [
            sys.executable,
            "-c",
            "import sys; sys.stdout.buffer.write('café Zürich 日本語'.encode('utf-8'))",
        ],
    )
    assert result.stdout == "café Zürich 日本語"
    assert result.returncode == 0


def test_non_utf8_bytes_are_replaced_not_fatal() -> None:
    # errors="replace" guarantees stdout is always a decodable string --
    # never None and never a raised UnicodeDecodeError -- even if a tool
    # emits genuinely non-UTF-8 bytes. A visible replacement character is a
    # far better failure mode than a silently empty result (#954).
    result = run_subprocess_safely(
        [
            sys.executable,
            "-c",
            "import sys; sys.stdout.buffer.write(b'before \\xff\\xfe after')",
        ],
    )
    assert result.stdout is not None
    assert "before " in result.stdout
    assert " after" in result.stdout


def test_empty_args_raises_value_error() -> None:
    with pytest.raises(ValueError, match="non-empty"):
        run_subprocess_safely([])


def test_missing_cwd_raises_value_error(tmp_path) -> None:
    with pytest.raises(ValueError, match="existing directory"):
        run_subprocess_safely([sys.executable, "--version"], cwd=str(tmp_path / "nope"))


def test_input_is_piped_to_child_stdin() -> None:
    # A payload delivered on stdin has no OS command-line length limit, unlike
    # an argv entry (Windows' ~32K CreateProcess limit) -- callers with large
    # or unbounded-size payloads (e.g. a whole document's text) must be able
    # to avoid ever building an oversized command line.
    result = run_subprocess_safely(
        [sys.executable, "-c", "import sys; print(sys.stdin.read())"],
        input="hello from stdin",
    )
    assert result.stdout.strip() == "hello from stdin"
    assert result.returncode == 0


def test_large_input_exceeding_argv_limit_still_succeeds() -> None:
    large_payload = "x" * 200_000  # far beyond Windows' ~32K argv limit
    result = run_subprocess_safely(
        [sys.executable, "-c", "import sys; sys.stdout.write(str(len(sys.stdin.read())))"],
        input=large_payload,
    )
    assert result.stdout.strip() == str(len(large_payload))
    assert result.returncode == 0
