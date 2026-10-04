"""The text an inserted equation becomes, shared by every Insert Equation.

QUILL had two Insert Equation commands that disagreed about delimiters: the
built-in one (Insert > Insert Equation..., ``Ctrl+Alt+=``) wrapped inline LaTeX
in ``$...$`` and block LaTeX in a three-line ``$$`` fence, while the bundled Math
Equations Quillin used ``\\(...\\)`` and a one-line ``$$...$$``. Only the second
pair is understood downstream:

* the preview's MathJax runs with its default delimiters, which are ``\\(``,
  ``\\[`` and ``$$`` -- not a bare ``$`` (``core/browser_preview.py``);
* Word export (:mod:`quill.io.docx_math`) turns ``\\(...\\)`` and ``$$...$$``
  into real Word equations, and deliberately ignores a bare ``$`` because
  ordinary prose is full of dollar amounts; and it works one paragraph at a
  time, so a ``$$`` fence spread over three lines was never seen as one span.

So an equation inserted with the built-in command rendered nowhere and exported
as literal dollar signs. Both commands now build their text here (2026-10-03).
wx-free, so the Quillin and the editor import the same two functions.
"""

from __future__ import annotations

__all__ = ["equation_snippet", "split_existing_equation"]


def equation_snippet(equation: str, display_mode: str) -> str:
    """The text to insert for *equation* in *display_mode* (``inline``/``block``).

    MathML (anything starting with ``<``) is returned untouched: it is already
    a complete element. LaTeX is wrapped in ``\\(...\\)`` inline, or a
    single-line ``$$...$$`` on a line of its own for a block equation -- one
    line, so the whole equation stays inside one paragraph for Word export.
    """
    text = (equation or "").strip()
    if not text:
        return ""
    if text.startswith("<"):
        return text
    if display_mode == "block":
        return f"\n$${text}$$\n"
    return f"\\({text}\\)"


def split_existing_equation(selection: str) -> tuple[str, str]:
    """Split a selected equation into ``(equation, display_mode)``.

    Lets the command act as "edit this equation": the delimiters come off so
    the field holds only the math, and the mode that was used is preselected.
    Reads every form either command has ever written -- ``$$...$$``,
    ``\\[...\\]``, ``\\(...\\)`` and the older built-in ``$...$`` -- so
    reopening an old equation and inserting it again upgrades its delimiters.
    A selection that is not an equation comes back unchanged, as inline.
    """
    text = (selection or "").strip()
    if text.startswith("$$") and text.endswith("$$") and len(text) > 4:
        return text[2:-2].strip(), "block"
    if text.startswith("\\[") and text.endswith("\\]") and len(text) > 4:
        return text[2:-2].strip(), "block"
    if text.startswith("\\(") and text.endswith("\\)") and len(text) > 4:
        return text[2:-2].strip(), "inline"
    if text.startswith("$") and text.endswith("$") and len(text) > 2:
        return text[1:-1].strip(), "inline"
    return selection or "", "inline"
