"""Language-aware Next / Previous Block (quill.core.language_blocks, navigation)."""

from __future__ import annotations

from pathlib import Path

import pytest

from quill.core.language_profile import get_profile_by_name, get_profile_for_path
from quill.core.navigation import (
    block_line_text,
    block_starts,
    language_block_starts,
    next_block_start,
    previous_block_start,
)


def _lines_at(text: str, profile_name: str) -> list[str]:
    profile = get_profile_by_name(profile_name)
    assert profile is not None
    return [
        block_line_text(text, start) for start in language_block_starts(text, profile.block_pattern)
    ]


def test_python_stops_at_defs_classes_and_their_decorators() -> None:
    text = (
        "import os\n\nclass A:\n    x = 1\n\n    def m(self):\n        pass\n\n"
        "@decorator\ndef f():\n    if True:\n        pass\n\nasync def g():\n    pass\n"
    )
    assert _lines_at(text, "Python") == [
        "class A:",
        "def m(self):",
        "@decorator",
        "async def g():",
    ]


def test_csharp_and_java_stop_at_types_and_methods_not_calls() -> None:
    text = (
        "namespace App\n{\n    [Serializable]\n    public class Thing\n    {\n"
        "        private int count;\n        public void Run(int a)\n        {\n"
        "            Helper(a);\n            if (a > 1) { }\n        }\n    }\n}\n"
    )
    assert _lines_at(text, "C#") == [
        "namespace App",
        "public class Thing",
        "public void Run(int a)",
    ]
    java = (
        "public final class Main {\n    static int twice(int x) {\n"
        "        return x * 2;\n    }\n}\n"
    )
    assert _lines_at(java, "Java") == ["public final class Main {", "static int twice(int x) {"]


def test_javascript_and_typescript_stop_at_functions_classes_and_methods() -> None:
    js = (
        "const a = 1;\nfunction one() {}\nexport default class B {\n  run(x) {\n"
        "    if (x) {\n    }\n  }\n}\nconst two = (y) => y;\nexport async function three() {}\n"
    )
    assert _lines_at(js, "JavaScript") == [
        "function one() {}",
        "export default class B {",
        "run(x) {",
        "const two = (y) => y;",
        "export async function three() {}",
    ]
    ts = "export interface Shape {\n  area(): number;\n}\ntype Id = string;\nenum Colour { Red }\n"
    assert _lines_at(ts, "TypeScript") == [
        "export interface Shape {",
        "type Id = string;",
        "enum Colour { Red }",
    ]


def test_ini_and_toml_stop_at_sections() -> None:
    ini = "; comment\n[general]\nname = x\n\n[paths] ; where\nhome = y\n"
    assert _lines_at(ini, "INI") == ["[general]", "[paths] ; where"]
    toml = 'title = "t"\n[tool.ruff]\nline = 1\n[[servers]]\nname = "a"\n'
    assert _lines_at(toml, "TOML") == ["[tool.ruff]", "[[servers]]"]


def test_batch_stops_at_labels_not_double_colon_comments() -> None:
    text = "@echo off\n:: a comment\n:start\necho hi\ngoto :eof\n:done\n"
    assert _lines_at(text, "Batch") == [":start", ":done"]
    assert get_profile_for_path(Path("run.CMD")).name == "Batch"


def test_latex_stops_at_sectioning_commands() -> None:
    text = "\\documentclass{book}\n\\chapter{One}\ntext\n\\section*{Two}\n\\subsection[s]{Three}\n"
    assert _lines_at(text, "LaTeX") == [
        "\\chapter{One}",
        "\\section*{Two}",
        "\\subsection[s]{Three}",
    ]
    assert get_profile_for_path(Path("paper.tex")).name == "LaTeX"


def test_html_stops_at_headings_and_landmarks() -> None:
    text = (
        "<body>\n<header>Top</header>\n<NAV>links</NAV>\n<p>para</p>\n"
        '<div role="search">s</div>\n<main>\n<h2>Title</h2>\n<p>x</p>\n</main>\n'
    )
    assert _lines_at(text, "HTML") == [
        "<header>Top</header>",
        "<NAV>links</NAV>",
        '<div role="search">s</div>',
        "<main>",
        "<h2>Title</h2>",
    ]


def test_next_and_previous_block_use_the_pattern() -> None:
    profile = get_profile_by_name("Python")
    assert profile is not None
    text = "x = 1\n\ndef a():\n    pass\n\n\ndef b():\n    pass\n"
    first, second = text.index("def a"), text.index("def b")
    assert next_block_start(text, 0, profile.block_pattern) == first
    assert next_block_start(text, first, profile.block_pattern) == second
    assert next_block_start(text, second, profile.block_pattern) is None
    assert previous_block_start(text, len(text), profile.block_pattern) == second
    assert previous_block_start(text, second, profile.block_pattern) == first


@pytest.mark.parametrize("pattern", ["", "(unclosed"])
def test_no_pattern_or_a_bad_one_keeps_paragraphs(pattern: str) -> None:
    text = "one\ntwo\n\nthree\n\n\nfour"
    assert block_starts(text, pattern) == [0, text.index("three"), text.index("four")]


def test_a_language_file_with_no_matches_still_moves_by_paragraph() -> None:
    profile = get_profile_by_name("Python")
    assert profile is not None
    text = "x = 1\n\ny = 2\n"
    assert next_block_start(text, 0, profile.block_pattern) == text.index("y")


def test_markdown_and_plain_text_have_no_pattern() -> None:
    assert get_profile_for_path(Path("a.md")).block_pattern == ""
    assert get_profile_for_path(Path("a.txt")).block_pattern == ""


def test_every_pattern_compiles() -> None:
    import re

    from quill.core.language_profile import all_profiles

    for profile in all_profiles():
        if profile.block_pattern:
            re.compile(profile.block_pattern, re.MULTILINE)


def test_block_line_text_is_trimmed_and_shortened() -> None:
    text = "    def f():\n" + "x" * 200
    assert block_line_text(text, 0) == "def f():"
    assert block_line_text(text, text.index("x")).endswith("...")
