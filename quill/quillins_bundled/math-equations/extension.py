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

Explore Equation Structure walks a formula's structure one piece at a time
(numerator/denominator, base/exponent, a square root's radicand, ...) using
quill.core.math.navigator for the structural walk. "Read this part aloud"
goes through quill.core.math.speech, which uses the real MathCAT engine
(daisy/MathCATForC) when the user has downloaded it (Help > Download
Optional Components...), and navigator's own plain-English template
reading otherwise — never a hard requirement, always a usable reading.

Capabilities: ui.prompt, ui.choices, ui.announce, editor.read, editor.write,
              ui.command.
"""

from __future__ import annotations

from quill.core.math import speech
from quill.core.math.navigator import EquationNavigator, MathNavigatorError, parse_equation

_INLINE = "Inline  (\\(...\\))"
_BLOCK = "Block  ($$...$$)"
_READ_ALOUD = "Read this part aloud"
_BACK_UP = "Back up one level"
_DONE_EXPLORING = "Done exploring"


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

    def explore_equation_structure(ctx):
        selection = ctx.get_selection() or ""
        default_eq, _mode = _strip_delimiters(selection) if selection else ("", "inline")

        raw = ctx.prompt(
            "Explore Equation Structure",
            "LaTeX (e.g. E=mc^2) or MathML (<math ...>):",
            default_eq,
        )
        if raw is None:
            return
        eq = raw.strip()
        if not eq:
            ctx.announce("Explore equation cancelled")
            return

        try:
            root = parse_equation(eq)
        except MathNavigatorError as exc:
            ctx.announce(f"Could not read that as an equation: {exc}")
            return

        nav = EquationNavigator(root)
        while True:
            ctx.announce("Whole equation" if nav.at_root() else nav.label())
            child_options = nav.child_options()
            numbered = [f"{i + 1}. {opt.label}" for i, opt in enumerate(child_options)]
            choices = [*numbered, _READ_ALOUD]
            if not nav.at_root():
                choices.append(_BACK_UP)
            choices.append(_DONE_EXPLORING)

            chosen = ctx.show_choices("Explore Equation Structure", choices)
            if chosen is None or chosen == _DONE_EXPLORING:
                return
            if chosen == _READ_ALOUD:
                ctx.announce(speech.speak(nav.current))
                continue
            if chosen == _BACK_UP:
                nav.ascend()
                continue
            nav.descend(numbered.index(chosen))

    api.register_command("insert_equation", insert_equation)
    api.register_command("explore_equation_structure", explore_equation_structure)
