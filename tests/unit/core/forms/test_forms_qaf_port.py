"""The ports of BAF's PHP lexer, parser and formatter agree with BAF byte for byte.

Three layers:

- the vendored fixtures (``fixtures/*.bfl`` with ``*.baf.json`` made by BAF's
  own PHP) always run, so CI checks the port without BAF;
- every example in BAF's guide and PHP tests, read from BAF at test time,
  when BAF is on the machine;
- and, when PHP is installed too, BAF's PHP is run on those examples and on
  a few hundred mutated ones, and compared live.
"""

from __future__ import annotations

import json
import random
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from quill.core.forms import bfl_lexer as L
from quill.core.forms.qaf_format import php_empty, qaf_format, qaf_minify
from quill.core.forms.qaf_parser import (
    is_safe_custom_attribute,
    qaf_parse,
    sanitize_title,
    split_choice,
)

sys.path.insert(0, str(Path(__file__).parent))
from forms_baf_sources import all_sources, baf_root, php_executable  # noqa: E402

FIXTURES = Path(__file__).parent / "fixtures"
HARNESS = Path(__file__).parent / "baf_php_harness.php"
NO_BAF = "BAF (S:\\code\\baf, or QUILL_BAF_ROOT) is not on this machine; the vendored fixtures still ran."  # noqa: E501


def _normal(value: Any) -> Any:
    """PHP writes an empty array as [] whether it was a list or a map."""
    if isinstance(value, dict):
        return {k: _normal(v) for k, v in value.items()} or []
    if isinstance(value, list):
        return [_normal(v) for v in value]
    return value


VENDORED = sorted(p.stem for p in FIXTURES.glob("*.bfl"))


def test_vendored_set_is_present_and_small() -> None:
    assert 15 <= len(VENDORED) <= 30
    assert (FIXTURES / "SOURCE.txt").is_file()


@pytest.mark.parametrize("name", VENDORED)
def test_vendored_fixture_parse_matches_baf(name: str) -> None:
    source = (FIXTURES / f"{name}.bfl").read_text(encoding="utf-8")
    golden = json.loads((FIXTURES / f"{name}.baf.json").read_text(encoding="utf-8"))
    assert _normal(qaf_parse(source)) == _normal(golden["parse"])


@pytest.mark.parametrize("name", VENDORED)
def test_vendored_fixture_format_matches_baf_byte_for_byte(name: str) -> None:
    source = (FIXTURES / f"{name}.bfl").read_text(encoding="utf-8")
    golden = json.loads((FIXTURES / f"{name}.baf.json").read_text(encoding="utf-8"))
    assert qaf_format(source) == golden["format"]


def _live_sources() -> list[Any]:
    root = baf_root()
    return all_sources(root) if root else []


@pytest.mark.skipif(baf_root() is None, reason=NO_BAF)
def test_baf_examples_are_all_found() -> None:
    sources = _live_sources()
    origins = {s.origin.split(":")[0] for s in sources}
    assert {"guide", "ParserTest.php", "LexerTest.php"} <= origins
    assert len(sources) >= 100


def _run_php(sources: list[str]) -> list[dict[str, Any]]:
    root = baf_root()
    php = php_executable()
    assert root is not None and php is not None
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "sources.json"
        path.write_text(json.dumps(sources), encoding="utf-8")
        done = subprocess.run(  # noqa: S603 - our own harness, read-only
            [php, str(HARNESS), str(root), str(path)],
            capture_output=True,
            check=True,
            timeout=120,
        )
    result: list[dict[str, Any]] = json.loads(done.stdout.decode("utf-8"))
    return result


needs_php = pytest.mark.skipif(
    baf_root() is None or php_executable() is None,
    reason="Needs BAF and PHP on this machine; the vendored goldens still ran.",
)


@needs_php
def test_every_baf_example_parses_and_formats_exactly_like_baf() -> None:
    sources = _live_sources()
    expected = _run_php([s.text for s in sources])
    parse_bad = [
        s.origin
        for s, e in zip(sources, expected, strict=True)
        if _normal(qaf_parse(s.text)) != _normal(e["parse"])
    ]
    format_bad = [
        s.origin
        for s, e in zip(sources, expected, strict=True)
        if qaf_format(s.text) != e["format"]
    ]
    assert parse_bad == []
    assert format_bad == []


def _mutations(sources: list[str], count: int) -> list[str]:
    rng = random.Random(1747)
    pieces = [
        "\n", "  ", "\t", "{", "}", "[", "]", "begin", "end", "@required", "@min 3",
        '"x"', "#id", "+ A|b", "+ C:2", "if #a is \"b\"", "columns 2", "column", "//c",
        "/* b */", "page", "section", "-4.5", "@attr data-x \"1\"", "countries", "\\\"",
    ]  # fmt: skip
    out = []
    for _ in range(count):
        text = list(rng.choice(sources))
        for _edit in range(rng.randint(1, 6)):
            at = rng.randint(0, len(text))
            if text and rng.random() < 0.3:
                del text[min(at, len(text) - 1)]
            else:
                text[at:at] = list(rng.choice(pieces))
        out.append("".join(text))
    return out


@needs_php
def test_mutated_examples_still_match_baf() -> None:
    sources = [s.text for s in _live_sources()]
    mutated = _mutations(sources, 300)
    expected = _run_php(mutated)
    for text, e in zip(mutated, expected, strict=True):
        assert _normal(qaf_parse(text)) == _normal(e["parse"]), text
        assert qaf_format(text) == e["format"], text


# -- unit checks on the port's pieces ------------------------------------------------


def test_lexer_tokens_and_offsets() -> None:
    toks = L.tokenize('form "T"\n  text #a "A" @required\n  + X|Y')
    kinds = [t.type for t in toks]
    assert kinds[:3] == [L.KEYWORD, L.STRING, L.NEWLINE]
    indent = toks[3]
    assert indent.type == L.INDENT and indent.level == 2
    choice = [t for t in toks if t.type == L.CHOICE][0]
    assert choice.value == "X|Y"
    for t in toks[:-1]:
        assert t.end > t.pos


def test_lexer_escapes_numbers_and_tabs() -> None:
    toks = L.tokenize('"a\\"b\\n" -3.25 \tx')
    assert toks[0].value == 'a"b\n'
    assert toks[1].type == L.NUMBER and toks[1].value == "-3.25"
    assert L.tokenize("\tx")[0].level == 4


def test_lexer_keeps_unknown_words_as_strings() -> None:
    toks = L.tokenize("toggle Text")
    assert (toks[0].type, toks[0].value) == (L.STRING, "toggle")
    assert (toks[1].type, toks[1].value) == (L.KEYWORD, "text")


@pytest.mark.parametrize(
    ("text", "slug"),
    [
        ("Sales", "sales"),
        ("Credit Card", "credit-card"),
        ("T-Shirt (large)", "t-shirt-large"),
        ("Café au lait", "cafe-au-lait"),
        ("a.b", "a-b"),
        ("100% sure", "100-sure"),
        ("  --x--  ", "x"),
    ],
)
def test_sanitize_title(text: str, slug: str) -> None:
    assert sanitize_title(text) == slug


def test_split_choice_forms() -> None:
    assert split_choice("card|Credit Card") == {"value": "card", "label": "Credit Card"}
    assert split_choice("Small:10") == {"value": "small", "label": "Small", "price": "10"}
    assert split_choice("Plain") == {"value": "plain", "label": "Plain"}


def test_custom_attribute_safety() -> None:
    assert is_safe_custom_attribute("data-x")
    assert is_safe_custom_attribute("aria-label")
    assert not is_safe_custom_attribute("onclick")
    assert not is_safe_custom_attribute("style")
    assert not is_safe_custom_attribute("anything")


def test_baf_drops_the_first_indented_choice() -> None:
    """A documented BAF bug the port keeps, so Check This Form can warn about it."""
    result = qaf_parse('select "D"\n  + A\n  + B')
    assert [c["label"] for c in result["form"]["fields"][0]["choices"]] == ["B"]


def test_minify_and_php_empty() -> None:
    assert qaf_minify('form "x"\n\n  // c\n  text "a"\n0\n') == 'form "x"\ntext "a"'
    assert php_empty("0") and php_empty([]) and not php_empty("0.0")
