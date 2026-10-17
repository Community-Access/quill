"""Property-based tests for braille: page maps, and translation through the
worker (todo P3).

Translation itself is liblouis's, which this machine and CI may not have
installed (it ships as an optional pack). So the properties are about what
QUILL adds around it, where a slip loses text without any error:

* the **page map** of a braille file covers every character exactly once, in
  order (a form feed is the boundary between two pages), whatever the mix of
  form feeds and line endings -- a gap is text a reader can never reach by
  page, an overlap is a page read twice;
* the **worker pipe** (request as JSON in, result as JSON out) hands back any
  text unchanged, and the **lou_translate route** trims exactly the one line
  ending the tool appends, never a line the translation itself ended with;
* with liblouis present, translating the same text twice gives the same braille.
"""

from __future__ import annotations

import io
import json
import subprocess
from contextlib import redirect_stdout
from pathlib import Path
from types import SimpleNamespace

import pytest

hypothesis = pytest.importorskip("hypothesis")
from hypothesis import given  # noqa: E402
from hypothesis import strategies as st  # noqa: E402

from quill.core import braille_worker  # noqa: E402
from quill.core.brf_document import BRFDocument  # noqa: E402
from quill.core.brf_page_map import build_page_map  # noqa: E402

# --------------------------------------------------------------------------- #
# Page maps
# --------------------------------------------------------------------------- #

#: Braille ASCII lines of any length, joined by any line ending, with form
#: feeds anywhere: the shapes real BRF files from different embossers take.
_brf_line = st.text(alphabet=st.characters(min_codepoint=0x20, max_codepoint=0x5F), max_size=50)
_brf_text = st.lists(
    st.tuples(_brf_line, st.sampled_from(["\n", "\r\n", "\r", "\x0c", "\n\x0c"])),
    max_size=80,
).map(lambda parts: "".join(line + end for line, end in parts))


@given(
    text=_brf_text,
    mode=st.sampled_from(["form_feed", "calculated", "hybrid"]),
    width=st.integers(10, 44),
    height=st.integers(5, 30),
)
def test_the_page_map_covers_every_character_once_in_order(
    text: str, mode: str, width: int, height: int
) -> None:
    doc = BRFDocument(text=text, suffix=".brf", cell_width=width, line_height=height)
    pages = build_page_map(doc, mode=mode).pages  # type: ignore[arg-type]
    assert pages, "even an empty file is one page"
    assert pages[0].start_offset == 0
    assert pages[-1].end_offset == len(text)
    # A form feed ends its page and belongs to neither side (brf_page_map:
    # "the FF is the terminator; exclusive end"), so it is the one character
    # between two pages; every other character is on exactly one page.
    for before, after in zip(pages, pages[1:], strict=False):
        assert after.start_offset == before.end_offset + (1 if before.has_form_feed else 0)
    rebuilt = "".join(
        text[p.start_offset : p.end_offset] + ("" if p.has_form_feed else "") for p in pages
    )
    assert rebuilt == text
    assert [p.index for p in pages] == list(range(len(pages)))


@given(text=_brf_text, mode=st.sampled_from(["form_feed", "calculated", "hybrid"]))
def test_the_page_map_is_the_same_every_time(text: str, mode: str) -> None:
    doc = BRFDocument(text=text, suffix=".brf")
    first = build_page_map(doc, mode=mode)  # type: ignore[arg-type]
    second = build_page_map(doc, mode=mode)  # type: ignore[arg-type]
    assert [(p.start_offset, p.end_offset) for p in first.pages] == [
        (p.start_offset, p.end_offset) for p in second.pages
    ]


# --------------------------------------------------------------------------- #
# The worker
# --------------------------------------------------------------------------- #

_any_text = st.text(alphabet=st.characters(blacklist_categories=("Cs",)), max_size=200)


@given(text=_any_text, backward=st.booleans())
def test_the_worker_pipe_returns_any_text_unchanged(text: str, backward: bool) -> None:
    """Identity translation, real JSON both ways: the pipe adds and loses nothing."""
    original = braille_worker._translate_one
    braille_worker._translate_one = lambda t, _table, *, backward: {"result": t}  # type: ignore[assignment]
    try:
        out = io.StringIO()
        request = {"cmd": "back" if backward else "forward", "text": text, "table": "x"}
        with redirect_stdout(out):
            assert braille_worker.main(json.dumps(request)) == 0
    finally:
        braille_worker._translate_one = original  # type: ignore[assignment]
    assert json.loads(out.getvalue()) == {"result": text}


#: What a translation can produce: text that may itself end in line breaks. No
#: carriage returns -- subprocess reads text mode with universal newlines, so
#: the tool's output never reaches Python with one.
_translated = st.text(
    alphabet=st.characters(blacklist_categories=("Cs",), blacklist_characters="\r"), max_size=120
)


@given(translated=_translated)
def test_the_cli_route_trims_only_the_line_ending_the_tool_adds(translated: str) -> None:
    from quill.core import braille_pack

    def run(*_args: object, **_kwargs: object) -> SimpleNamespace:
        return SimpleNamespace(returncode=0, stdout=translated + "\n", stderr="")

    saved = (braille_pack.find_lou_translate, braille_pack.find_table_file, subprocess.run)
    braille_pack.find_lou_translate = lambda: Path("lou_translate.exe")  # type: ignore[assignment]
    braille_pack.find_table_file = lambda _table: None  # type: ignore[assignment]
    subprocess.run = run  # type: ignore[assignment]
    try:
        import builtins

        real_import = builtins.__import__

        def no_louis(name: str, *args: object, **kwargs: object) -> object:
            if name == "louis":
                raise ImportError(name)
            return real_import(name, *args, **kwargs)  # type: ignore[arg-type]

        builtins.__import__ = no_louis  # type: ignore[assignment]
        try:
            result = braille_worker._translate_one("anything", "en-ueb-g2", backward=False)
        finally:
            builtins.__import__ = real_import
    finally:
        braille_pack.find_lou_translate, braille_pack.find_table_file, subprocess.run = saved
    assert result == {"result": translated}


@given(text=st.text(alphabet=st.characters(min_codepoint=0x20, max_codepoint=0x7E), max_size=80))
def test_translating_twice_gives_the_same_braille(text: str) -> None:
    louis = pytest.importorskip("louis")
    table = braille_worker._table_argument("en-ueb-g1.ctb")
    first = louis.translateString([table], text)
    assert louis.translateString([table], text) == first
