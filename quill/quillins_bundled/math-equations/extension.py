"""Math Equations - bundled Quillin for inserting LaTeX or MathML at the caret.

UX flow:
1. Strip LaTeX delimiters from the current selection (if any) to pre-fill the
   equation prompt.
2. Prompt for the equation text.
3. If the input starts with '<math', insert it verbatim as MathML.
4. Otherwise show a display-mode choice (Inline / Block) and wrap accordingly.

MathJax rendering in HTML preview and export requires injecting a CDN script
tag into browser_preview.py and io/export.py. That is a separate core change
not part of this Quillin.

Capabilities: ui.prompt, ui.choices, ui.announce, editor.read, editor.write,
              ui.command.
"""

from __future__ import annotations

_INLINE = "Inline  ($...$)"
_BLOCK = "Block  ($$...$$)"


def _strip_delimiters(text: str) -> tuple[str, str]:
    """Return (equation_text, detected_mode) with LaTeX delimiters removed."""
    t = text.strip()
    if t.startswith("$$") and t.endswith("$$") and len(t) > 4:
        return t[2:-2].strip(), "block"
    if t.startswith("$") and t.endswith("$") and len(t) > 2:
        return t[1:-1].strip(), "inline"
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

        snippet = f"\n$$\n{eq}\n$$\n" if chosen == _BLOCK else f"${eq}$"

        if selection:
            ctx.replace_selection(snippet)
        else:
            ctx.insert_text(snippet)
        ctx.announce("Inserted math equation")

    api.register_command("insert_equation", insert_equation)
