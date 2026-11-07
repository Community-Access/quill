"""Check This File: syntax problems in the document, found without leaving it.

The shape is a Problems list: every problem a checker can find, each with a
line, a column, a severity and a message, and Next Problem / Previous Problem
to walk them with the caret. Three tiers of checker feed it:

* **built in** (:mod:`.builtin`): JSON, JSONC, XML, HTML, TOML, YAML, Python,
  INI, CSV and Markdown, with nothing but the standard library and packages
  QUILL already ships;
* **Node.js** for JavaScript (``node --check``), when node is on the PATH;
* **outside tools the user already has** (:mod:`.outside`): php, ruby, perl,
  tsc, eslint, ruff, shellcheck, gcc, clang, gofmt, rustc, csc and xmllint,
  each found on the PATH, never downloaded, and named in one frozen allowlist.

:func:`check_document` is the one entry point both editors call. Pure, no
``wx``; the outside tools run through :mod:`quill.stability.safe_subprocess`.
"""

from __future__ import annotations

from quill.core.problems.model import (
    CheckReport,
    Problem,
    describe_problem,
    offset_for,
    problem_after,
    summarize,
)
from quill.core.problems.registry import (
    builtin_languages,
    check_document,
    language_key,
    language_label,
)

__all__ = [
    "CheckReport",
    "Problem",
    "builtin_languages",
    "check_document",
    "describe_problem",
    "language_key",
    "language_label",
    "offset_for",
    "problem_after",
    "summarize",
]
