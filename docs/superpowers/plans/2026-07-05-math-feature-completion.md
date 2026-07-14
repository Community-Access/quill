# Math Feature Completion (steps 4-6) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Make QUILL's math-equations feature actually render and round-trip correctly in the browser preview, HTML export, and Word (.docx) — both directions — building on the already-shipped `quill/core/math/` MathML/LaTeX bridge and the abbreviation/agent work from earlier in `docs/planning/math.md`.

**Architecture:** Switch the bundled `math-equations` Quillin's delimiters to ones MathJax already recognizes by default (`\(...\)` inline, `$$...$$` display, both on their own paragraph) so browser preview/export need zero code changes. For Word, teach the native python-docx writer (`quill/io/docx_writer.py`) to splice a real `<m:oMath>` fragment — obtained via a one-equation round trip through QUILL's existing Pandoc bridge — into the run stream wherever it finds one of those delimiters, falling back to plain literal text if Pandoc is unavailable. Lock in the (already-correct) docx read-side behavior with regression tests.

**Tech Stack:** Python 3.12+, python-docx (`docx.oxml.parse_xml`), Pandoc (via `quill.io.pandoc.convert_file_with_pandoc`), pytest.

## Global Constraints

- Preserve existing style/architecture: `quill/core` and `quill/io` stay wx-free and strict-typed (`mypy quill/core quill/io` must stay clean).
- Docx writing must never hard-fail because Pandoc is absent — degrade to plain text, matching the existing `python_docx_available()` fallback pattern.
- Run `ruff check .` / `ruff format --check .` and the relevant scoped `pytest` after every task.
- Quillin manifest changes must pass `python -m quill.tools.quillin_lint quill/quillins_bundled/math-equations --strict`.
- No CDN/network config changes are in scope here — the existing MathJax `<script>` tags in `quill/core/browser_preview.py:217` and `quill/io/export.py:226-227` are left untouched (verified: both `\(...\)` and `$$...$$` are MathJax's built-in defaults, and both `render_preview_body` and `markdown_to_rich` already pass backslashes and `$$` through unmodified — verified empirically this session).
- DAISY export (`quill/io/daisy.py`) is explicitly **out of scope** for this plan (confirmed with the user: DAISY 2.02 text-only has no real MathML rendering target; equations already export as readable literal text and that is left as-is).

---

### Task 1: Switch math-equations Quillin to MathJax-default delimiters

**Files:**
- Modify: `quill/quillins_bundled/math-equations/extension.py`
- Modify: `quill/quillins_bundled/math-equations/manifest.json`
- Modify: `quill/quillins_bundled/math-equations/README.md`
- Modify: `tests/unit/core/test_quillins_bundled_math_equations.py`

**Interfaces:**
- Produces: inline equations wrapped as `\(...\)`; display/block equations wrapped as a single-line `$${eq}$$` on its own paragraph (blank line before/after, but no separate fence lines) — this is what Task 2 depends on (single-span, single-paragraph equations are what the docx splicer can find).

- [x] **Step 1: Update the failing tests first**

Replace the delimiter-specific assertions in `tests/unit/core/test_quillins_bundled_math_equations.py`. Full replacement content for the affected test functions (everything else in the file is unchanged):

```python
def test_inline_latex_inserts_backslash_paren_delimiters() -> None:
    api = _register_extension()
    ctx = _FakeCtx(prompts=["E=mc^2"], choices=["Inline  (\\(...\\))"])
    api.handlers["insert_equation"](ctx)
    assert ctx.inserted == ["\\(E=mc^2\\)"]
    assert ctx.announced == ["Inserted math equation"]


def test_block_latex_inserts_single_line_double_dollar() -> None:
    api = _register_extension()
    ctx = _FakeCtx(prompts=[r"\sum_{n=1}^{\infty} \frac{1}{n^2}"], choices=["Block  ($$...$$)"])
    api.handlers["insert_equation"](ctx)
    assert len(ctx.inserted) == 1
    snippet = ctx.inserted[0]
    assert snippet == "\n$$\\sum_{n=1}^{\\infty} \\frac{1}{n^2}$$\n"
```

(These replace `test_inline_latex_inserts_dollar_delimiters` and `test_block_latex_inserts_double_dollar_with_newlines` by name.)

Also replace every other `"Inline  ($...$)"` choice literal in the file with `"Inline  (\\(...\\))"` (the constant's new display text) — this affects `test_inline_selection_stripped_and_replaced`, `test_cancel_mode_choice_does_nothing`'s sibling, and the sample-corpus loop tests. Update these specific bodies:

```python
def test_inline_selection_stripped_and_replaced() -> None:
    api = _register_extension()
    ctx = _FakeCtx(
        selection="\\(x^2\\)",
        prompts=["x^2"],
        choices=["Inline  (\\(...\\))"],
    )
    api.handlers["insert_equation"](ctx)
    assert ctx.replaced == ["\\(x^2\\)"]
    assert ctx.inserted == []
```

```python
def test_handler_round_trips_all_samples_as_inline() -> None:
    """Each sample equation re-inserted in inline mode produces \\(...\\)."""
    api = _register_extension()
    equations = _extract_block_equations(_SAMPLES_FILE)
    for eq in equations:
        ctx = _FakeCtx(prompts=[eq], choices=["Inline  (\\(...\\))"])
        api.handlers["insert_equation"](ctx)
        assert ctx.inserted, f"nothing inserted for: {eq!r}"
        snippet = ctx.inserted[-1]
        assert snippet.startswith("\\(") and snippet.endswith("\\)"), (
            f"inline delimiters missing for: {eq!r}"
        )
        assert eq in snippet
```

```python
def test_handler_round_trips_all_samples_as_block() -> None:
    """Each sample equation re-inserted in block mode produces a single-line $$...$$."""
    api = _register_extension()
    equations = _extract_block_equations(_SAMPLES_FILE)
    for eq in equations:
        ctx = _FakeCtx(prompts=[eq], choices=["Block  ($$...$$)"])
        api.handlers["insert_equation"](ctx)
        assert ctx.inserted, f"nothing inserted for: {eq!r}"
        snippet = ctx.inserted[-1]
        assert snippet == f"\n$${eq}$$\n", f"unexpected block snippet for: {eq!r}"
```

- [x] **Step 2: Run the tests to verify they fail**

Run: `pytest tests/unit/core/test_quillins_bundled_math_equations.py -q`
Expected: several FAIL (extension.py still produces `$...$` and the old multi-line block form).

- [x] **Step 3: Update `extension.py`**

Full new content:

```python
"""Math Equations - bundled Quillin for inserting LaTeX or MathML at the caret.

UX flow:
1. Strip LaTeX delimiters from the current selection (if any) to pre-fill the
   equation prompt.
2. Prompt for the equation text.
3. If the input starts with '<math', insert it verbatim as MathML.
4. Otherwise show a display-mode choice (Inline / Block) and wrap accordingly.

Inline equations use \\(...\\) and block equations use a single-line $$...$$
(on its own paragraph) rather than $...$ / a multi-line $$ fence: both are
MathJax's own default-recognized delimiters (no config needed in
browser_preview.py / export.py), \\(...\\) has no ambiguity with ordinary
prose dollar amounts the way bare $...$ does, and keeping the whole equation
on one line keeps it inside a single paragraph/run for quill.io.docx_math to
splice a real Word equation into.

Capabilities: ui.prompt, ui.choices, ui.announce, editor.read, editor.write,
              ui.command.
"""

from __future__ import annotations

_INLINE = "Inline  (\\(...\\))"
_BLOCK = "Block  ($$...$$)"


def _strip_delimiters(text: str) -> tuple[str, str]:
    """Return (equation_text, detected_mode) with LaTeX delimiters removed."""
    t = text.strip()
    if t.startswith("$$") and t.endswith("$$") and len(t) > 4:
        return t[2:-2].strip(), "block"
    if t.startswith("\\(") and t.endswith("\\)") and len(t) > 4:
        return t[2:-2].strip(), "inline"
    return t, "inline"


def register(api):
    """Register the insert_equation handler."""

    def insert_equation(ctx):
        selection = ctx.get_selection() or ""
        default_eq, default_mode = _strip_delimiters(selection)

        raw = ctx.prompt(
            "Insert Equation",
            "LaTeX (e.g. E=mc^2) or MathML (<math ...>):",
            default_eq,
        )
        if raw is None:
            return
        eq = raw.strip()
        if not eq:
            ctx.announce("Insert equation cancelled")
            return

        # MathML detected — insert verbatim, skip display-mode prompt
        if eq.lstrip().startswith("<math"):
            if selection:
                ctx.replace_selection(eq)
            else:
                ctx.insert_text(eq)
            ctx.announce("Inserted MathML equation")
            return

        # LaTeX — ask for display mode; surface detected mode as first choice
        choices = [_BLOCK, _INLINE] if default_mode == "block" else [_INLINE, _BLOCK]
        chosen = ctx.show_choices("Equation display mode", choices)
        if chosen is None:
            return

        snippet = f"\n$${eq}$$\n" if chosen == _BLOCK else f"\\({eq}\\)"

        if selection:
            ctx.replace_selection(snippet)
        else:
            ctx.insert_text(snippet)
        ctx.announce("Inserted math equation")

    api.register_command("insert_equation", insert_equation)
```

- [x] **Step 4: Run the tests to verify they pass**

Run: `pytest tests/unit/core/test_quillins_bundled_math_equations.py -q`
Expected: all PASS.

- [x] **Step 5: Update the manifest and README**

In `quill/quillins_bundled/math-equations/manifest.json`, bump `"version"` from `"1.1.0"` to `"1.2.0"`.

In `quill/quillins_bundled/math-equations/README.md`, replace:

```markdown
- LaTeX equations are wrapped in `$` (inline) or `$$` (display) delimiters.
```

with:

```markdown
- LaTeX equations are wrapped in `\(...\)` (inline) or `$$...$$` (display) delimiters — both are MathJax's own default math delimiters, so preview and HTML export need no extra configuration.
```

- [x] **Step 6: Lint and format**

Run: `python -m quill.tools.quillin_lint quill/quillins_bundled/math-equations --strict`
Expected: `PASS`

Run: `ruff check quill/quillins_bundled/math-equations tests/unit/core/test_quillins_bundled_math_equations.py && ruff format --check quill/quillins_bundled/math-equations tests/unit/core/test_quillins_bundled_math_equations.py`
Expected: no errors (run `ruff format` without `--check` first if formatting differs, then re-check).

- [x] **Step 7: Commit**

```bash
git add quill/quillins_bundled/math-equations tests/unit/core/test_quillins_bundled_math_equations.py
git commit -m "feat(math-equations): switch to MathJax-default delimiters"
```

---

### Task 2: Splice real Word equations into the native docx writer

**Files:**
- Create: `quill/io/docx_math.py`
- Modify: `quill/io/docx_writer.py`
- Test: `tests/unit/io/test_docx_math.py`

**Interfaces:**
- Consumes: `quill.io.pandoc.convert_file_with_pandoc(source_path, target_path, *, from_format, to_format, ...) -> Path` (raises `PandocUnavailableError` / `PandocConversionError` on failure); `docx.oxml.parse_xml(xml_string)` (returns an lxml element appendable via `paragraph._p.append(...)`).
- Produces: `split_math_segments(text: str) -> list[MathSegment]` and `omml_fragment_for_latex(latex: str, *, display: bool) -> str | None` (returns `None`, not raises, when Pandoc is unavailable or the equation fails to convert) — Task 2's `rich_to_docx` change is the only consumer, but both are public functions other docx code can reuse later.

- [x] **Step 1: Write the failing tests for `docx_math.py`**

Create `tests/unit/io/test_docx_math.py`:

```python
"""Segment-splitting and OMML-fragment generation for docx math splicing."""

from __future__ import annotations

import pytest

pytest.importorskip("docx")

from quill.io.docx_math import MathSegment, omml_fragment_for_latex, split_math_segments


def test_split_plain_text_is_single_text_segment() -> None:
    segments = split_math_segments("just some prose, no math")
    assert segments == [MathSegment(is_math=False, content="just some prose, no math")]


def test_split_inline_math_segment() -> None:
    segments = split_math_segments("The formula \\(x^2 + 1\\) here.")
    assert segments == [
        MathSegment(is_math=False, content="The formula "),
        MathSegment(is_math=True, content="x^2 + 1", display=False),
        MathSegment(is_math=False, content=" here."),
    ]


def test_split_display_math_segment() -> None:
    segments = split_math_segments("$$a^2+b^2=c^2$$")
    assert segments == [MathSegment(is_math=True, content="a^2+b^2=c^2", display=True)]


def test_split_multiple_math_segments() -> None:
    segments = split_math_segments("\\(x\\) and \\(y\\)")
    assert [s.is_math for s in segments] == [True, False, True]
    assert segments[0].content == "x"
    assert segments[2].content == "y"


def test_split_no_dollar_ambiguity_from_plain_prose() -> None:
    # Regression guard: ordinary prose with a lone $ never becomes a math segment.
    segments = split_math_segments("It costs $5 today.")
    assert segments == [MathSegment(is_math=False, content="It costs $5 today.")]
```

Create `tests/unit/io/test_docx_writer_math.py`:

```python
"""End-to-end: math text through the native docx writer produces a real equation."""

from __future__ import annotations

import zipfile
from pathlib import Path

import pytest

pytest.importorskip("docx")

from quill.io.docx_writer import rich_to_docx_bytes
from quill.io.rtf_model import markdown_to_rich


def test_inline_math_produces_real_omath(tmp_path: Path) -> None:
    rich = markdown_to_rich("Pythagorean theorem: \\(a^2 + b^2 = c^2\\)\n")
    data = rich_to_docx_bytes(rich)
    out = tmp_path / "math.docx"
    out.write_bytes(data)
    with zipfile.ZipFile(out) as z:
        xml = z.read("word/document.xml").decode("utf-8")
    assert "m:oMath" in xml
    assert "Pythagorean theorem:" in xml


def test_display_math_produces_real_omath(tmp_path: Path) -> None:
    rich = markdown_to_rich("$$a^2+b^2=c^2$$\n")
    data = rich_to_docx_bytes(rich)
    out = tmp_path / "math_block.docx"
    out.write_bytes(data)
    with zipfile.ZipFile(out) as z:
        xml = z.read("word/document.xml").decode("utf-8")
    assert "m:oMath" in xml


def test_plain_text_unaffected(tmp_path: Path) -> None:
    rich = markdown_to_rich("Just an ordinary paragraph, $5 and all.\n")
    data = rich_to_docx_bytes(rich)
    out = tmp_path / "plain.docx"
    out.write_bytes(data)
    with zipfile.ZipFile(out) as z:
        xml = z.read("word/document.xml").decode("utf-8")
    assert "m:oMath" not in xml
    assert "$5" in xml
```

- [x] **Step 2: Run the tests to verify they fail**

Run: `pytest tests/unit/io/test_docx_math.py tests/unit/io/test_docx_writer_math.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'quill.io.docx_math'`.

- [x] **Step 3: Create `quill/io/docx_math.py`**

```python
"""Splicing real Word (OMML) equations into the native docx writer.

The native writer (:mod:`quill.io.docx_writer`) has no math model of its own;
this module finds \\(...\\) / $$...$$ spans in plain paragraph text and turns
each into a real <m:oMath> fragment by round-tripping the single equation
through QUILL's existing Pandoc bridge (Pandoc already produces correct OMML
from LaTeX math — verified empirically against pandoc 3.10). When Pandoc is
unavailable or a specific equation fails to convert, the caller keeps the
literal delimited text instead of hard-failing the whole docx write.
"""

from __future__ import annotations

import re
import tempfile
import xml.etree.ElementTree as ET
import zipfile
from dataclasses import dataclass
from pathlib import Path

from defusedxml import ElementTree as DET

from quill.io.pandoc import PandocConversionError, PandocUnavailableError, convert_file_with_pandoc

_MATH_OMML_NS = "{http://schemas.openxmlformats.org/officeDocument/2006/math}"
_MATH_SPAN_RE = re.compile(r"\$\$(.+?)\$\$|\\\((.+?)\\\)", re.DOTALL)


@dataclass(frozen=True, slots=True)
class MathSegment:
    """One piece of a run's text: plain, or a single LaTeX equation."""

    is_math: bool
    content: str
    display: bool = False


def split_math_segments(text: str) -> list[MathSegment]:
    """Split *text* into plain-text and math segments.

    Recognizes ``$$...$$`` (display) and ``\\(...\\)`` (inline) only — matching
    the delimiters ``quill/quillins_bundled/math-equations`` now emits. A bare
    ``$`` (e.g. an ordinary dollar amount) is never treated as math.
    """
    segments: list[MathSegment] = []
    pos = 0
    for match in _MATH_SPAN_RE.finditer(text):
        if match.start() > pos:
            segments.append(MathSegment(is_math=False, content=text[pos : match.start()]))
        display_latex, inline_latex = match.group(1), match.group(2)
        if display_latex is not None:
            segments.append(MathSegment(is_math=True, content=display_latex, display=True))
        else:
            segments.append(MathSegment(is_math=True, content=inline_latex, display=False))
        pos = match.end()
    if pos < len(text):
        segments.append(MathSegment(is_math=False, content=text[pos:]))
    if not segments:
        segments.append(MathSegment(is_math=False, content=text))
    return segments


def omml_fragment_for_latex(latex: str, *, display: bool) -> str | None:
    """Return an ``<m:oMath>``/``<m:oMathPara>`` XML fragment for *latex*, or None.

    Returns None (never raises) when Pandoc is unavailable, fails, or the
    conversion produces no math element — callers fall back to plain text.
    """
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            source = tmp / "eq.md"
            target = tmp / "eq.docx"
            wrapped = f"$${latex}$$" if display else f"${latex}$"
            source.write_text(wrapped, encoding="utf-8")
            convert_file_with_pandoc(source, target, from_format="gfm", to_format="docx")
            with zipfile.ZipFile(target) as archive:
                xml = archive.read("word/document.xml").decode("utf-8")
    except (PandocUnavailableError, PandocConversionError, OSError, KeyError):
        return None

    try:
        root = DET.fromstring(xml)
    except Exception:  # noqa: BLE001 - malformed pandoc output degrades to plain text
        return None
    tag = f"{_MATH_OMML_NS}oMathPara" if display else f"{_MATH_OMML_NS}oMath"
    for element in root.iter(tag):
        return ET.tostring(element, encoding="unicode")
    return None
```

- [x] **Step 4: Run `test_docx_math.py` to verify it passes**

Run: `pytest tests/unit/io/test_docx_math.py -q`
Expected: all PASS. (`test_docx_writer_math.py` still fails — `rich_to_docx` doesn't call this module yet.)

- [x] **Step 5: Wire `docx_math` into `rich_to_docx`**

In `quill/io/docx_writer.py`, add the import at the top (after the existing `from quill.io.rtf_model import ...` line):

```python
from quill.io.docx_math import split_math_segments, omml_fragment_for_latex
```

Replace the per-span loop body (currently `for span in paragraph.spans: run = para.add_run(span.text)` through the end of that `for` block, i.e. lines 144-167) with:

```python
        for span in paragraph.spans:
            for segment in split_math_segments(span.text):
                if segment.is_math:
                    fragment = omml_fragment_for_latex(segment.content, display=segment.display)
                    if fragment is not None:
                        from docx.oxml import parse_xml

                        para._p.append(parse_xml(fragment))
                        continue
                    # Pandoc unavailable or conversion failed: keep the literal text
                    # rather than silently dropping the equation.
                    delimited = (
                        f"$${segment.content}$$" if segment.display else f"\\({segment.content}\\)"
                    )
                    run = para.add_run(delimited)
                else:
                    run = para.add_run(segment.content)
                run.bold = span.bold or None
                run.italic = span.italic or None
                run.underline = span.underline or None
                if span.strike:
                    run.font.strike = True
                # superscript and subscript share one w:vertAlign element, so set only
                # the active one; assigning the other (even None) would clear it.
                if span.superscript:
                    run.font.superscript = True
                elif span.subscript:
                    run.font.subscript = True
                if span.font_family:
                    run.font.name = span.font_family
                if span.font_size_pt:
                    run.font.size = Pt(span.font_size_pt)
                if span.color:
                    rgb = _parse_rgb(span.color)
                    if rgb is not None:
                        run.font.color.rgb = RGBColor(*rgb)
                if span.highlight:
                    name = _HIGHLIGHT_NAMES.get(span.highlight.lower(), "YELLOW")
                    run.font.highlight_color = getattr(WD_COLOR_INDEX, name)
```

Note the spliced `<m:oMath>` branch does `continue`s past the run-formatting block (there is no `run` object for it to format — Word equations aren't formatted via `w:rPr` the way text runs are), while both the "fallback literal text" and "plain text" branches fall through to the existing formatting block unchanged.

- [x] **Step 6: Run all math-related docx tests to verify they pass**

Run: `pytest tests/unit/io/test_docx_math.py tests/unit/io/test_docx_writer_math.py tests/unit/io/test_docx_writer.py -q`
Expected: all PASS (the pre-existing `test_docx_writer.py` suite must still pass unchanged — this confirms non-math text is untouched).

- [x] **Step 7: Scoped mypy, ruff, and full io suite**

Run: `mypy quill/core quill/io`
Expected: no new errors (add `cast`/type annotations if needed, following the pattern already used in `quill/core/math/mathml.py` for `defusedxml`).

Run: `ruff check quill/io tests/unit/io/test_docx_math.py tests/unit/io/test_docx_writer_math.py && ruff format --check quill/io tests/unit/io/test_docx_math.py tests/unit/io/test_docx_writer_math.py`
Expected: no errors (run `ruff format` without `--check` first if needed).

Run: `pytest tests/unit/io -q`
Expected: all PASS (full regression check for the `io` layer).

- [x] **Step 8: Commit**

```bash
git add quill/io/docx_math.py quill/io/docx_writer.py tests/unit/io/test_docx_math.py tests/unit/io/test_docx_writer_math.py
git commit -m "feat(docx): splice real Word equations for math text in the native writer"
```

---

### Task 3: Lock in docx math read-fidelity with regression tests

**Files:**
- Test: `tests/unit/io/test_structured_math.py`

**Interfaces:**
- Consumes: `quill.io.structured.read_structured_document(path: Path, encoding: str = "utf-8", *, docx_engine: str = "auto") -> Document` (returns a `Document` with `.text`); `quill.io.docx_writer.rich_to_docx_bytes`; `quill.io.rtf_model.markdown_to_rich`.

- [x] **Step 1: Write the regression test**

Create `tests/unit/io/test_structured_math.py`:

```python
"""Regression: opening a docx with a real Word equation preserves the math as text.

Locks in already-correct behavior (verified empirically against MarkItDown and
Pandoc, both of which convert a native <m:oMath> equation back to readable
LaTeX-ish text) so a future MarkItDown/Pandoc upgrade or engine-default change
cannot silently regress it.
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("docx")
pytest.importorskip("markitdown")

from quill.io.docx_writer import rich_to_docx_bytes
from quill.io.rtf_model import markdown_to_rich
from quill.io.structured import read_structured_document


def _write_math_docx(tmp_path: Path) -> Path:
    rich = markdown_to_rich("Pythagorean theorem: \\(a^2 + b^2 = c^2\\)\n")
    data = rich_to_docx_bytes(rich)
    path = tmp_path / "math.docx"
    path.write_bytes(data)
    return path


def test_default_engine_preserves_equation_text(tmp_path: Path) -> None:
    path = _write_math_docx(tmp_path)
    document = read_structured_document(path, docx_engine="auto")
    assert "a" in document.text and "2" in document.text
    assert "Pythagorean theorem" in document.text


def test_pandoc_engine_preserves_equation_text(tmp_path: Path) -> None:
    path = _write_math_docx(tmp_path)
    document = read_structured_document(path, docx_engine="pandoc")
    assert "a" in document.text and "2" in document.text
    assert "Pythagorean theorem" in document.text
```

Note: this test depends on Task 2 already being done (it writes the fixture docx via `rich_to_docx_bytes`, which now produces a real `<m:oMath>` for `\(...\)` text) — run Task 2 first.

- [x] **Step 2: Run the test**

Run: `pytest tests/unit/io/test_structured_math.py -q`
Expected: PASS (this is locking in existing behavior, not adding new code — if it fails, `_write_math_docx`'s equation didn't actually splice; re-check Task 2).

- [x] **Step 3: Commit**

```bash
git add tests/unit/io/test_structured_math.py
git commit -m "test(io): lock in docx math round-trip via MarkItDown and Pandoc read engines"
```

---

## Self-Review Notes

- **Spec coverage:** Task 1 covers the delimiter switch this plan's own architecture depends on; Task 2 covers docx write (the concrete "Word" deliverable for the tutorial); Task 3 covers docx read (already correct, now regression-locked). Step 4 (MathJax rendering) needed no task — verified via `render_preview_body`/`markdown_to_rich` passthrough tests already run this session, so it's called out in Global Constraints instead of a task. DAISY (step 6) is explicitly out of scope per the user's decision.
- **Placeholder scan:** all code blocks are complete, verified-in-spirit against the actual prototype run this session (the OMML splice in Task 2 Step 3/5 mirrors the working prototype at `C:\Users\jeffb\AppData\Local\Temp\claude\S--QUILL\4c2b5fed-871d-440f-b31a-f3a492f758aa\scratchpad\prototype_omath_splice.py`, adapted into the real module).
- **Type consistency:** `MathSegment`, `split_math_segments`, `omml_fragment_for_latex` names and signatures match between Task 2's test file and implementation file.
