"""The shared parse cache: fast, and never stale.

Three gates walk the whole ``quill/`` tree -- the banned-pattern gate, the
dialog inventory, and the egress audit -- and they now share one parse. That is
worth having (a pytest session parsed the package three times over, and
``check_banned_patterns`` alone parsed every UI module up to a dozen times), but
a cache is only worth having if it cannot lie.

The dangerous case is not the obvious one. Keying on path alone looks fine
against the real tree, where files do not change mid-run -- and then quietly
breaks the gates' own unit tests, which write a module under ``tmp_path``, scan
it, rewrite the *same path* with different content, and scan again. A path-keyed
cache hands the second scan the first file's tree, and the test passes or fails
for reasons unrelated to what it is testing. Hence the mtime+size key, and hence
the first test below.
"""

from __future__ import annotations

import ast
import time
from pathlib import Path

from quill.tools.source_cache import clear, parsed, parsed_source

# -- correctness: a cache that cannot serve a stale tree ---------------------


def test_rewriting_the_same_path_is_reparsed(tmp_path: Path) -> None:
    """The case a path-keyed cache would get wrong, and the gates' own tests
    rely on: same filename, new content."""
    module = tmp_path / "m.py"
    module.write_text("x = 1\n", encoding="utf-8")
    first = parsed(module)
    assert isinstance(first.body[0], ast.Assign)

    # Sleep past filesystem timestamp granularity so mtime genuinely moves;
    # the size differs here too, but a test that leaned on that would not be
    # testing the mtime half of the key.
    time.sleep(0.01)
    module.write_text("def f():\n    return 2\n", encoding="utf-8")

    second = parsed(module)
    assert isinstance(second.body[0], ast.FunctionDef), "served a stale tree"


def test_same_content_and_stamp_is_served_from_cache(tmp_path: Path) -> None:
    """The point of the thing: an unchanged file is parsed once."""
    module = tmp_path / "m.py"
    module.write_text("x = 1\n", encoding="utf-8")
    assert parsed(module) is parsed(module)


def test_source_lines_match_the_file(tmp_path: Path) -> None:
    module = tmp_path / "m.py"
    module.write_text("a = 1\nb = 2\nc = 3\n", encoding="utf-8")
    lines, _tree = parsed_source(module)
    assert lines == ("a = 1", "b = 2", "c = 3")


def test_lines_come_back_immutable(tmp_path: Path) -> None:
    """The value is shared between callers, so a list would let one gate
    corrupt another's view of the file."""
    module = tmp_path / "m.py"
    module.write_text("a = 1\n", encoding="utf-8")
    lines, _tree = parsed_source(module)
    assert isinstance(lines, tuple)


def test_line_numbers_survive_the_cache(tmp_path: Path) -> None:
    """Every gate reports ``path:line``, and several slice the source around a
    node's ``lineno`` to look for an exemption comment. An off-by-one here
    would misreport every violation in the repository."""
    module = tmp_path / "m.py"
    module.write_text("# c\n\nimport os\n\nx = os\n", encoding="utf-8")
    lines, tree = parsed_source(module)
    node = next(n for n in ast.walk(tree) if isinstance(n, ast.Import))
    assert node.lineno == 3
    assert lines[node.lineno - 1] == "import os"


def test_clear_forces_a_reparse(tmp_path: Path) -> None:
    module = tmp_path / "m.py"
    module.write_text("x = 1\n", encoding="utf-8")
    first = parsed(module)
    clear()
    assert parsed(module) is not first


# -- the shape the gates depend on ------------------------------------------


def test_parsed_and_parsed_source_agree(tmp_path: Path) -> None:
    module = tmp_path / "m.py"
    module.write_text("x = 1\n", encoding="utf-8")
    assert parsed(module) is parsed_source(module)[1]


def test_a_real_package_module_parses(tmp_path: Path) -> None:
    """Not a synthetic file: the tree the gates actually walk."""
    real = Path(__file__).resolve().parents[3] / "quill" / "tools" / "source_cache.py"
    lines, tree = parsed_source(real)
    assert isinstance(tree, ast.Module)
    assert lines, "a real module should have source lines"
