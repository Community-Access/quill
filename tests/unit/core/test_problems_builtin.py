"""Check This File's built-in checkers (quill.core.problems.builtin), bad and good."""

from __future__ import annotations

from pathlib import Path

import pytest

from quill.core.problems import builtin
from quill.core.problems.builtin import (
    check_csv,
    check_html,
    check_ini,
    check_json,
    check_jsonc,
    check_markdown,
    check_python,
    check_toml,
    check_xml,
    strip_jsonc,
)
from quill.core.problems.model import Problem


def _where(problems: list[Problem]) -> list[tuple[int, int, str]]:
    return [(p.line, p.column, p.severity) for p in problems]


def test_json_good_and_bad() -> None:
    assert check_json('{"a": [1, 2], "b": null}') == []
    assert check_json("") == []
    [problem] = check_json('{\n  "a": 1,\n  "b": \n}')
    assert (problem.line, problem.column, problem.severity) == (4, 1, "error")
    assert problem.message == "Expecting value"


def test_jsonc_allows_comments_and_trailing_commas_and_keeps_positions() -> None:
    good = '{\n  // a setting\n  "a": 1, /* why */\n  "b": [1, 2,],\n}\n'
    assert check_jsonc(good) == []
    assert len(strip_jsonc(good)) == len(good)
    assert check_jsonc('{ "url": "http://x//y" }') == []
    [problem] = check_jsonc('{\n  // fine\n  "a": 1\n  "b": 2\n}')
    assert problem.line == 4
    [unclosed] = check_jsonc('{\n  "a": 1 /* never\n}')
    assert (unclosed.line, unclosed.message) == (2, "Comment is never closed")


def test_xml_good_bad_and_entity_attacks_refused() -> None:
    assert check_xml("<a><b/></a>") == []
    [problem] = check_xml("<a>\n  <b>\n</a>")
    assert (problem.line, problem.severity) == (3, "error")
    assert "mismatched tag" in problem.message
    bomb = '<?xml version="1.0"?><!DOCTYPE x [<!ENTITY a "aaaa">]><x>&a;</x>'
    [refused] = check_xml(bomb)
    assert refused.severity == "error"


def test_html_reports_every_problem() -> None:
    text = (
        '<div id="main">\n<p>One<span>open\n</div>\n<img src="a.png">\n'
        '<p id="main">Two</p>\n</section>\n<b>bold'
    )
    problems = check_html(text)
    messages = [p.message for p in problems]
    assert "<span> opened on line 2 is not closed before </div>" in messages
    assert "Image has no alt text" in messages
    assert 'Duplicate id "main", first used on line 1' in messages
    assert "</section> closes nothing: there is no open <section>" in messages
    assert "<b> is never closed" in messages
    assert _where(problems)[0][0] == 2


def test_html_leaves_optional_end_tags_and_void_elements_alone() -> None:
    good = (
        "<!DOCTYPE html>\n<html lang=en><head><meta charset=utf-8><title>t</title>"
        "<body><ul><li>one<li>two</ul><p>para<p>next<br><img src=a alt=''>"
        "<table><tr><td>1<td>2</table></body></html>"
    )
    assert check_html(good) == []


def test_toml_good_and_bad() -> None:
    assert check_toml('[tool]\nname = "x"\n') == []
    [problem] = check_toml("a = 1\nb = \n")
    assert (problem.line, problem.column, problem.severity) == (2, 5, "error")
    assert "line" not in problem.message


@pytest.mark.skipif(not builtin.yaml_available(), reason="no YAML library installed")
def test_yaml_good_and_bad() -> None:
    assert builtin.check_yaml("a: 1\nb: [1, 2]\n---\nc: 3\n") == []
    [problem] = builtin.check_yaml("a: [1,\nb: 2\n")
    assert problem.severity == "error"
    assert problem.line >= 2


def test_python_syntax_error_and_compile_time_errors() -> None:
    assert check_python("def f(x):\n    return x\n") == []
    [problem] = check_python("def f(:\n    pass\n")
    assert (problem.line, problem.severity) == (1, "error")
    [outside] = check_python("x = 1\nreturn x\n")
    assert (outside.line, outside.message) == (2, "'return' outside function")


def test_python_warnings_are_reported_and_nothing_runs(tmp_path: Path) -> None:
    marker = tmp_path / "ran.txt"
    text = f"open({str(marker)!r}, 'w').write('x')\ny = '\\d'\n"
    problems = check_python(text)
    assert [p.severity for p in problems] == ["warning"]
    assert problems[0].line == 2
    assert not marker.exists()


def test_ini_problems() -> None:
    assert check_ini("[a]\nx = 1\n\n[b]\ny = 2\n") == []
    assert check_ini("x = 1\n[a]\n")[0].message == "A setting comes before any [section]"
    assert check_ini("[a]\nx=1\nx=2\n")[0].line == 3
    assert check_ini("[a]\n[a]\n")[0].message == "Section [a] appears twice"
    [bad] = check_ini("[a]\nnot a setting\n")
    assert (bad.line, bad.message) == (2, "Not a setting or a section: not a setting")


def test_csv_ragged_rows_and_quote_errors() -> None:
    assert check_csv("a,b\n1,2\n3,4\n", None) == []
    problems = check_csv('a,b,c\n1,2\n3,4,5\n6,7\n"x"y,1,2\n', None)
    assert _where(problems) == [(2, 1, "warning"), (4, 1, "warning"), (5, 1, "error")]
    assert problems[0].message == "This row has 2 fields; the first row has 3"
    assert check_csv("a\tb\n1\t2\n", Path("x.tsv")) == []


def test_csv_caps_the_ragged_rows() -> None:
    text = "a,b,c\n" + "1,2\n" * (builtin.CSV_ROW_LIMIT + 50)
    assert len(check_csv(text, None)) == builtin.CSV_ROW_LIMIT


def test_markdown_problems(tmp_path: Path) -> None:
    (tmp_path / "there.md").write_text("x", encoding="utf-8")
    doc = tmp_path / "doc.md"
    text = (
        "# Title\n### Skipped\n![](pic.png)\n[](there.md)\n[text]()\n"
        "[fine](there.md#part)\n[gone](missing.md)\n[web](https://example.com)\n"
        "```\n[](inside-code)\n```\n"
    )
    problems = check_markdown(text, doc)
    lines = {(p.line, p.message) for p in problems}
    assert (2, "Heading levels jump by more than one level.") in lines
    assert (3, "Markdown image is missing alternative text.") in lines
    assert (4, "Link has no text") in lines
    assert (5, "Link has no address") in lines
    assert (7, "No file at missing.md") in lines
    assert not any(p.line in {6, 8, 10} for p in problems)


def test_markdown_without_a_path_does_not_check_files() -> None:
    assert check_markdown("# A\n\n[x](nowhere.md)\n", None) == []
