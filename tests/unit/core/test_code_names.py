"""Layer 1 of IntelliSense: the names in this file (quill.core.code_names).

A small corpus per language with the caret at a known spot and the expected
suggestions and kinds, the prose rule, and the speed budget from the plan
(the list within 100 ms on a 1 MB file, best of five, never under tracemalloc).
"""

from __future__ import annotations

import time

import pytest

from quill.core.code_names import code_language_for, complete_code_names, is_code_file
from quill.core.intellisense import (
    build_code_suggestions,
    spoken_suggestion,
    suggestions_status,
)

#: (file name, text with "|" at the caret, the names expected first, in order,
#: and the kind of the first).
CORPUS: list[tuple[str, str, list[str], str]] = [
    (
        "tool.py",
        "def count_words(text):\n    return len(text)\n\ncounter = 0\nprint(cou|)\n",
        ["counter", "count_words"],
        "name",
    ),
    (
        "app.js",
        "function renderList(items) {}\nconst renderCount = 2;\nrend|\n",
        ["renderCount", "renderList"],
        "name",
    ),
    (
        "main.c",
        "struct point { int x; };\nint pointer_count;\nvoid f(void) { poin| }\n",
        ["pointer_count", "point"],
        "name",
    ),
    (
        "main.go",
        "package main\nfunc handleRequest() {}\nvar handled int\nfunc main() { hand| }\n",
        ["handled", "handleRequest"],
        "name",
    ),
    (
        "lib.rs",
        "fn parse_line(s: &str) {}\nlet parsed = 1;\npars|\n",
        ["parsed", "parse_line"],
        "name",
    ),
    (
        "build.ps1",
        "function Get-Thing {}\n$ThingCount = 1\nWrite-Host $Thin|\n",
        ["ThingCount"],
        "name",
    ),
]


def _split(marked: str) -> tuple[str, int]:
    caret = marked.index("|")
    return marked.replace("|", "", 1), caret


@pytest.mark.parametrize(("name", "marked", "expected", "first_kind"), CORPUS)
def test_corpus_offers_the_files_names_nearest_first(
    name: str, marked: str, expected: list[str], first_kind: str
) -> None:
    text, caret = _split(marked)
    alias = code_language_for(name)
    assert alias is not None, name
    fragment_start = caret
    while fragment_start and (
        text[fragment_start - 1].isalnum() or text[fragment_start - 1] == "_"
    ):
        fragment_start -= 1
    names = complete_code_names(text, caret, text[fragment_start:caret], alias)
    assert [n.name for n in names][: len(expected)] == expected
    assert names[0].kind == first_kind


def test_a_definition_far_away_is_still_a_function_or_class() -> None:
    text = "class Widget:\n    pass\n\n" + "x = 1\n" * 2000 + "def widen():\n    pass\nWid"
    names = complete_code_names(text, len(text), "Wid", "python")
    kinds = {n.name: n.kind for n in names}
    assert kinds["Widget"] == "class"
    assert kinds["widen"] == "function"
    assert [n.name for n in names][0] == "Widget", "the same case comes first"


def test_keywords_get_their_kind_from_the_lexer() -> None:
    text = "while ready:\n    pass\nwhi"
    names = complete_code_names(text, len(text), "whi", "python")
    assert ("while", "keyword") in [(n.name, n.kind) for n in names]


def test_the_word_being_typed_is_never_offered_to_itself() -> None:
    names = complete_code_names("alpha = 1\nalpha", 15, "alpha", "python")
    assert [n.name for n in names] == []


def test_prose_files_are_not_code() -> None:
    for name in ("notes.txt", "README.md", "draft", "letter.docx", None):
        assert not is_code_file(name), name
    for name in ("a.py", "a.js", "a.html", "a.json", "a.ps1"):
        assert is_code_file(name), name


def test_suggestions_are_spoken_with_their_kind_and_insert_only_the_fragment() -> None:
    text = "def count(): pass\nco"
    context, suggestions = build_code_suggestions(text, len(text), "python")
    assert context is not None and context.fragment == "co"
    assert suggestions[0].label == "count"
    assert spoken_suggestion(suggestions[0]) == "count, function"
    assert suggestions_status(suggestions).startswith(f"{len(suggestions)} suggestion")
    assert suggestions_status(suggestions).endswith("count, function")
    replaced = text[: context.replacement_start] + suggestions[0].inserted_text
    assert replaced == "def count(): pass\ncount"


def test_a_lexer_failure_never_breaks_the_list(monkeypatch: pytest.MonkeyPatch) -> None:
    from quill.core import code_names

    def broken(_alias: str):
        raise RuntimeError("lexer bug")

    monkeypatch.setattr(code_names, "_lexer", broken)
    names = complete_code_names("value = 1\nval", 13, "val", "python")
    assert [n.name for n in names] == ["value"]


@pytest.mark.perf
@pytest.mark.parametrize("fragment", ["s", "se", "_problem", "Wx"])
def test_the_list_is_ready_within_100_ms_on_a_1_mb_file(fragment: str) -> None:
    """Real code at real density: QUILL's own largest module, to a megabyte."""
    from pathlib import Path

    import quill.ui.main_frame as source

    real = Path(source.__file__).read_text(encoding="utf-8")
    text = (real * (1_000_000 // len(real) + 1))[:1_000_000]
    caret = text.index("\n", len(text) // 2)
    complete_code_names(text, caret, fragment, "python")  # warm the lexer cache
    best = min(
        _timed(lambda: complete_code_names(text, caret, fragment, "python")) for _ in range(5)
    )
    assert best < 0.100, f"{fragment!r}: {best * 1000:.0f} ms"


def _timed(call) -> float:  # type: ignore[no-untyped-def]
    start = time.perf_counter()
    call()
    return time.perf_counter() - start
