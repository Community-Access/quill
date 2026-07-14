"""Unit tests for the bundled math-equations Quillin.

Covers:
- manifest.json: validates, resolves to Insert menu, declares Ctrl+Shift+E
  hotkey, declares correct capabilities.
- extension.py handler: inline LaTeX, block LaTeX, MathML passthrough,
  selection pre-fill and replace, empty cancel, prompt cancel, mode cancel.
- Sample corpus: every block equation from docs/math/latex_testing.md is
  correctly stripped, wrapped, and round-tripped by the handler.
- snippet_gallery: the bundled "Common Formulas" entries are well-formed and
  every body is valid, recognized math text.
"""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest

from quill.core.quillins.loader import bundled_extensions_root
from quill.core.quillins.registry import build_registry
from quill.core.quillins.validation import parse_manifest, validate_manifest

_REPO_ROOT = Path(__file__).resolve().parents[3]
_SAMPLES_FILE = _REPO_ROOT / "docs" / "math" / "latex_testing.md"


def _extract_block_equations(path: Path) -> list[str]:
    """Return the bare LaTeX from every $$...$$ block in the file."""
    text = path.read_text(encoding="utf-8")
    return [m.group(1).strip() for m in re.finditer(r"\$\$(.+?)\$\$", text, re.DOTALL)]


_DIR = bundled_extensions_root() / "math-equations"


def _load_manifest():
    raw = json.loads((_DIR / "manifest.json").read_text(encoding="utf-8"))
    assert validate_manifest(raw) == []
    return parse_manifest(raw)


class _FakeApi:
    def __init__(self) -> None:
        self.handlers: dict[str, Callable[[Any], None]] = {}

    def register_command(self, name: str, handler: Callable[[Any], None]) -> None:
        self.handlers[name] = handler


@dataclass
class _FakeCtx:
    selection: str = ""
    prompts: list[str | None] = field(default_factory=list)
    choices: list[str | None] = field(default_factory=list)
    inserted: list[str] = field(default_factory=list)
    replaced: list[str] = field(default_factory=list)
    announced: list[str] = field(default_factory=list)

    def get_selection(self) -> str:
        return self.selection

    def prompt(self, title: str, label: str, default: str = "") -> str | None:
        return self.prompts.pop(0)

    def show_choices(self, title: str, items: list[str]) -> str | None:
        return self.choices.pop(0)

    def insert_text(self, text: str) -> None:
        self.inserted.append(text)

    def replace_selection(self, text: str) -> None:
        self.replaced.append(text)

    def announce(self, message: str) -> None:
        self.announced.append(message)

    def is_verbosity_speech_enabled(self) -> bool:
        return True


def _register_extension() -> _FakeApi:
    sys.path.insert(0, str(_DIR))
    try:
        ns: dict[str, Any] = {}
        exec((_DIR / "extension.py").read_text(encoding="utf-8"), ns)  # noqa: S102
        api = _FakeApi()
        ns["register"](api)
        return api
    finally:
        sys.path.remove(str(_DIR))


# -- manifest -----------------------------------------------------------------


def test_manifest_validates_and_has_correct_id() -> None:
    manifest = _load_manifest()
    assert manifest.id == "com.quill.bundled.math-equations"


def test_manifest_capabilities() -> None:
    manifest = _load_manifest()
    caps = set(manifest.capabilities)
    assert caps >= {"ui.prompt", "ui.choices", "ui.announce", "editor.read", "editor.write"}


def test_manifest_command_under_insert_menu() -> None:
    manifest = _load_manifest()
    registry = build_registry([manifest])
    assert registry.conflicts == ()
    parents = {m.parent for m in registry.menus}
    assert "Insert" in parents


def test_manifest_hotkey_ctrl_shift_e() -> None:
    manifest = _load_manifest()
    bindings = {hk.binding for hk in manifest.contributes.hotkeys}
    assert "Ctrl+Shift+E" in bindings


def test_manifest_hotkey_explore_equation_structure() -> None:
    manifest = _load_manifest()
    by_command = {hk.command: hk.binding for hk in manifest.contributes.hotkeys}
    assert by_command["ext.math.explore_equation_structure"] == "Ctrl+Shift+Grave, F"


# -- handler: LaTeX insertion -------------------------------------------------


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


# -- handler: MathML detection ------------------------------------------------


def test_mathml_inserts_verbatim_without_mode_prompt() -> None:
    api = _register_extension()
    mathml = "<math><mi>x</mi></math>"
    ctx = _FakeCtx(prompts=[mathml])
    api.handlers["insert_equation"](ctx)
    assert ctx.inserted == [mathml]
    assert ctx.choices == []  # show_choices never called
    assert "MathML" in ctx.announced[0]


def test_mathml_with_leading_whitespace_detected() -> None:
    api = _register_extension()
    mathml = "  <math><mi>y</mi></math>"
    ctx = _FakeCtx(prompts=[mathml])
    api.handlers["insert_equation"](ctx)
    assert ctx.inserted[0].startswith("<math")


def test_mathml_with_selection_replaces_not_inserts() -> None:
    api = _register_extension()
    mathml = "<math><mi>z</mi></math>"
    ctx = _FakeCtx(selection="old text", prompts=[mathml])
    api.handlers["insert_equation"](ctx)
    assert ctx.replaced == [mathml]
    assert ctx.inserted == []


# -- handler: selection pre-fill ----------------------------------------------


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


def test_block_selection_surfaces_block_mode_first() -> None:
    # When the selection is block-delimited, the choice list should start with
    # Block so the user can confirm with one keypress.
    api = _register_extension()
    ctx = _FakeCtx(
        selection="$$x^2$$",
        prompts=["x^2"],
        choices=["Block  ($$...$$)"],
    )
    api.handlers["insert_equation"](ctx)
    assert ctx.replaced
    assert "$$" in ctx.replaced[0]


# -- handler: cancel paths ----------------------------------------------------


def test_cancel_prompt_does_nothing() -> None:
    api = _register_extension()
    ctx = _FakeCtx(prompts=[None])
    api.handlers["insert_equation"](ctx)
    assert ctx.inserted == []
    assert ctx.replaced == []
    assert ctx.announced == []


def test_empty_equation_announces_cancel() -> None:
    api = _register_extension()
    ctx = _FakeCtx(prompts=["   "])
    api.handlers["insert_equation"](ctx)
    assert ctx.inserted == []
    assert ctx.announced and "cancelled" in ctx.announced[0].lower()


def test_cancel_mode_choice_does_nothing() -> None:
    api = _register_extension()
    ctx = _FakeCtx(prompts=["E=mc^2"], choices=[None])
    api.handlers["insert_equation"](ctx)
    assert ctx.inserted == []
    assert ctx.announced == []


# -- sample corpus from docs/math/latex_testing.md ----------------------------


def test_sample_file_exists_and_has_equations() -> None:
    assert _SAMPLES_FILE.exists(), f"sample file not found: {_SAMPLES_FILE}"
    equations = _extract_block_equations(_SAMPLES_FILE)
    assert len(equations) == 10, f"expected 10 block equations, got {len(equations)}"


def test_strip_delimiters_on_all_samples() -> None:
    """Every $$ block in the sample file must be detected as block mode."""
    ns: dict[str, Any] = {}
    exec((_DIR / "extension.py").read_text(encoding="utf-8"), ns)  # noqa: S102
    strip = ns["_strip_delimiters"]
    for eq in _extract_block_equations(_SAMPLES_FILE):
        wrapped = f"$${eq}$$"
        bare, mode = strip(wrapped)
        assert mode == "block", f"expected block mode for: {wrapped!r}"
        assert bare == eq.strip(), f"stripping changed content: {bare!r} != {eq.strip()!r}"


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


def test_selection_prefill_preserves_all_sample_content() -> None:
    """Selecting a $$ block and re-inserting it produces an identical snippet."""
    api = _register_extension()
    equations = _extract_block_equations(_SAMPLES_FILE)
    for eq in equations:
        selection = f"$${eq}$$"
        ctx = _FakeCtx(
            selection=selection,
            prompts=[eq.strip()],
            choices=["Block  ($$...$$)"],
        )
        api.handlers["insert_equation"](ctx)
        assert ctx.replaced, f"replace_selection not called for: {eq!r}"
        snippet = ctx.replaced[-1]
        assert eq.strip() in snippet, f"content lost in round-trip for: {eq!r}"


# -- snippet gallery: bundled common formulas ---------------------------------


def test_snippet_gallery_has_ten_common_formulas() -> None:
    manifest = _load_manifest()
    assert len(manifest.contributes.snippet_gallery) == 10


def test_snippet_gallery_entries_are_unique_and_named() -> None:
    manifest = _load_manifest()
    ids = [entry.id for entry in manifest.contributes.snippet_gallery]
    assert len(ids) == len(set(ids)), "duplicate snippet_gallery id"
    for entry in manifest.contributes.snippet_gallery:
        assert entry.name
        assert entry.description
        assert entry.category in {"Algebra", "Geometry"}


def test_snippet_gallery_bodies_are_single_display_math_segments() -> None:
    """Every gallery formula is exactly one $$...$$ block — nothing else."""
    from quill.io.docx_math import split_math_segments

    manifest = _load_manifest()
    for entry in manifest.contributes.snippet_gallery:
        segments = split_math_segments(entry.body)
        assert len(segments) == 1, f"{entry.id}: expected one segment, got {segments!r}"
        assert segments[0].is_math and segments[0].display, f"{entry.id}: not display math"


def test_snippet_gallery_bodies_have_no_declared_params() -> None:
    """No gallery formula declares {param} placeholders, so LaTeX's own { } braces

    (e.g. \\frac{a}{b}) are never mistaken for substitution templates."""
    manifest = _load_manifest()
    for entry in manifest.contributes.snippet_gallery:
        assert entry.params == (), f"{entry.id}: unexpected params {entry.params!r}"


def test_snippet_gallery_bodies_insert_as_block_equations() -> None:
    """Selecting a gallery formula and re-editing it detects block mode correctly."""
    manifest = _load_manifest()
    api = _register_extension()
    for entry in manifest.contributes.snippet_gallery:
        bare = entry.body[2:-2]  # strip the $$ ... $$ this test file adds back
        ctx = _FakeCtx(selection=entry.body, prompts=[bare], choices=["Block  ($$...$$)"])
        api.handlers["insert_equation"](ctx)
        assert ctx.replaced, f"{entry.id}: replace_selection not called"
        assert bare in ctx.replaced[-1], f"{entry.id}: content lost on round-trip"


# -- explore_equation_structure ------------------------------------------------


def _latex2mathml_available() -> bool:
    try:
        import latex2mathml.converter  # noqa: F401
    except ImportError:
        return False
    return True


_needs_latex2mathml = pytest.mark.skipif(
    not _latex2mathml_available(), reason="latex2mathml not installed"
)


def test_explore_manifest_command_and_menu() -> None:
    manifest = _load_manifest()
    ids = {c.id for c in manifest.contributes.commands}
    assert "ext.math.explore_equation_structure" in ids
    registry = build_registry([manifest])
    assert registry.conflicts == ()
    parents = {
        m.parent for m in registry.menus if m.command_id == "ext.math.explore_equation_structure"
    }
    assert parents == {"Insert"}


def test_explore_cancel_at_prompt_does_nothing() -> None:
    api = _register_extension()
    ctx = _FakeCtx(prompts=[None])
    api.handlers["explore_equation_structure"](ctx)
    assert ctx.announced == []


def test_explore_empty_input_announces_cancel() -> None:
    api = _register_extension()
    ctx = _FakeCtx(prompts=["   "])
    api.handlers["explore_equation_structure"](ctx)
    assert ctx.announced and "cancelled" in ctx.announced[0].lower()


def test_explore_malformed_equation_announces_error() -> None:
    api = _register_extension()
    ctx = _FakeCtx(prompts=["}{"])
    api.handlers["explore_equation_structure"](ctx)
    assert ctx.announced and "could not read" in ctx.announced[0].lower()


@_needs_latex2mathml
def test_explore_walks_into_a_child_and_announces_its_label() -> None:
    api = _register_extension()
    ctx = _FakeCtx(
        prompts=["a^2 + b^2 = c^2"],
        choices=["1. a squared", "Done exploring"],
    )
    api.handlers["explore_equation_structure"](ctx)
    assert ctx.announced == ["Whole equation", "a squared"]


@_needs_latex2mathml
def test_explore_read_aloud_announces_full_reading(monkeypatch) -> None:
    # Pin the template reading: on a machine where the optional MathCAT engine
    # is downloaded, speech.speak would route through it and phrase things in
    # MathCAT's own vocabulary ("eigh squared ... is equal to"), making this
    # flow test environment-dependent. The engine has its own coverage; this
    # test is about the explore flow.
    from quill.core.math import speech

    monkeypatch.setattr(speech, "mathcat_available", lambda: False)
    api = _register_extension()
    ctx = _FakeCtx(
        prompts=["a^2 + b^2 = c^2"],
        choices=["Read this part aloud", "Done exploring"],
    )
    api.handlers["explore_equation_structure"](ctx)
    assert ctx.announced == [
        "Whole equation",
        "a squared plus b squared equals c squared",
        "Whole equation",
    ]


@_needs_latex2mathml
def test_explore_back_up_returns_to_parent() -> None:
    api = _register_extension()
    ctx = _FakeCtx(
        prompts=["a^2 + b^2 = c^2"],
        choices=["1. a squared", "Back up one level", "Done exploring"],
    )
    api.handlers["explore_equation_structure"](ctx)
    assert ctx.announced == ["Whole equation", "a squared", "Whole equation"]


@_needs_latex2mathml
def test_explore_none_from_show_choices_ends_the_session() -> None:
    api = _register_extension()
    ctx = _FakeCtx(prompts=["a^2 + b^2 = c^2"], choices=[None])
    api.handlers["explore_equation_structure"](ctx)
    assert ctx.announced == ["Whole equation"]


@_needs_latex2mathml
def test_explore_descends_into_a_fraction_for_numerator_and_denominator(monkeypatch) -> None:
    # Template reading pinned for the same reason as the read-aloud test above.
    from quill.core.math import speech

    monkeypatch.setattr(speech, "mathcat_available", lambda: False)
    api = _register_extension()
    ctx = _FakeCtx(
        prompts=[r"x = \frac{-b \pm \sqrt{b^2 - 4ac}}{2a}"],
        choices=[
            "3. Fraction",
            "1. Numerator: Group",
            "Read this part aloud",
            "Done exploring",
        ],
    )
    api.handlers["explore_equation_structure"](ctx)
    assert ctx.announced[0] == "Whole equation"
    assert ctx.announced[1] == "Fraction"
    assert ctx.announced[2] == "Group"
    assert "minus b plus or minus" in ctx.announced[3]
