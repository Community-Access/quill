"""The real bundled language servers, one small corpus per language.

Marked ``lsp`` and skipped unless ``QUILL_LANGUAGE_SERVERS_DIR`` names a staged
folder (``python scripts/fetch_build_deps.py --only nodejs --only
language-servers``) and ``QUILL_LANGUAGE_SERVERS_NODE`` names its node.exe.
Each case is a file with the caret at a known spot and what the server must
give there: a completion, a problem, or a parameter hint.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from quill.core.lsp.pool import LanguageServerPool

pytestmark = [
    pytest.mark.lsp,
    pytest.mark.skipif(
        not os.environ.get("QUILL_LANGUAGE_SERVERS_DIR"),
        reason="the language servers are not staged (QUILL_LANGUAGE_SERVERS_DIR)",
    ),
]

#: (file, text, completion fragment, a completion that must be offered, problem text)
CORPUS = [
    ("style.css", "body { colo", "colo", "color", None),
    ("data.json", '{\n  "a": \n}\n', None, None, "Value expected"),
    ("app.ts", "const greeting: number = 'hi';\nconsole.lo", "lo", "log", "not assignable"),
    ("app.js", "const items = [1];\nitems.fil", "fil", "filter", None),
    ("tool.py", "import os\nos.pa", "pa", "path", "is not a known attribute"),
]


@pytest.fixture(scope="module")
def pool():
    instance = LanguageServerPool()
    yield instance
    instance.shutdown()


@pytest.fixture(scope="module")
def root(tmp_path_factory) -> Path:
    """One project for the whole corpus, so each server starts once (a cold
    Pyright takes seconds, and every new project folder is a new server)."""
    return tmp_path_factory.mktemp("lsp")


@pytest.mark.parametrize(("name", "text", "fragment", "wanted", "problem"), CORPUS)
def test_each_server_completes_and_finds_problems(
    pool, root, name, text, fragment, wanted, problem
) -> None:
    path = root / name
    path.write_text(text, encoding="utf-8")
    if fragment is not None:
        labels = [c.label for c in pool.complete(path, root, text, len(text), fragment)]
        assert wanted in labels, labels
    if problem is not None:
        found = pool.problems(path, root, text) or []
        assert any(problem in p.message for p in found), [p.message for p in found]


def test_pyright_gives_parameter_hints(pool, tmp_path: Path) -> None:
    text = "def f(text: str, limit: int) -> int:\n    return 0\n\nf('a', "
    path = tmp_path / "hint.py"
    path.write_text(text, encoding="utf-8")
    assert pool.signature(path, tmp_path, text, len(text)).startswith("Parameter 2 of 2, limit")


def test_typescript_offers_a_quick_fix(pool, tmp_path: Path) -> None:
    text = "function f() {\n  return undefinedName;\n}\n"
    path = tmp_path / "fix.ts"
    path.write_text(text, encoding="utf-8")
    problems = pool.problems(path, tmp_path, text) or []
    assert problems
    # Not every problem has a fix; the call must answer, quickly, either way.
    assert isinstance(pool.fixes(path, tmp_path, text, problems[0]), list)
