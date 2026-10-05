"""qc.md X-08 (PR #1618): MathML, EPUB entities and the regex fallback, at the real boundary."""

from __future__ import annotations

import sys


def test_an_escaped_less_than_in_epub_mathml_is_spoken_not_lost() -> None:
    from quill.core.epub import _convert_mathml_to_speech

    mathml = (
        '<math xmlns="http://www.w3.org/1998/Math/MathML"><mi>x</mi><mo>&lt;</mo><mn>3</mn></math>'
    )
    spoken = _convert_mathml_to_speech(mathml)
    assert "x" in spoken and "3" in spoken
    assert "less" in spoken.lower(), spoken


def test_html_named_entities_still_parse() -> None:
    from quill.core.epub import _convert_mathml_to_speech

    mathml = "<math><mi>a</mi><mo>&InvisibleTimes;</mo><mi>b</mi><mo>&lt;</mo><mn>2</mn></math>"
    spoken = _convert_mathml_to_speech(mathml)
    assert "less" in spoken.lower(), spoken


_BLOCK = """
import builtins, sys
real = builtins.__import__
def blocked(name, *a, **k):
    if name.split(".")[0] == {name!r}:
        raise ImportError(name)
    return real(name, *a, **k)
builtins.__import__ = blocked
"""


def _run_without(module: str, body: str) -> str:
    """Run *body* in a fresh interpreter where *module* cannot be imported, so
    nothing in this process is left half-reloaded for the tests after it."""
    import subprocess
    import textwrap

    code = _BLOCK.format(name=module) + textwrap.dedent(body)
    done = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, timeout=120, check=False
    )
    assert done.returncode == 0, done.stderr
    return done.stdout.strip()


def test_mathml_parses_without_defusedxml() -> None:
    out = _run_without(
        "defusedxml",
        """
        from quill.core.math import mathml
        assert mathml.parse_mathml("<math><mi>x</mi></math>").tag == "math"
        try:
            mathml.parse_mathml('<!DOCTYPE m [<!ENTITY a "aaaa">]><math>&a;</math>')
        except mathml.MathMLError:
            print("refused")
        """,
    )
    assert out == "refused"


def test_safe_regex_falls_back_to_the_standard_library() -> None:
    out = _run_without(
        "regex",
        """
        from quill.stability import safe_regex
        assert safe_regex._HAVE_REGEX is False
        found = [m.group(0) for m in safe_regex.safe_finditer(r"\d+", "a1b22")]
        print(found, safe_regex.safe_subn(r"\d", "#", "a1b2"))
        """,
    )
    assert out == "['1', '22'] ('a#b#', 2)"
