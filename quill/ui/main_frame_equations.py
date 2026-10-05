"""Insert > Insert Equation...: type math as LaTeX or MathML (#1197).

Contributed by @salorajan as part of PR #1197 and split out here so the
equation dialog could land on its own; the rest of that PR (environment-variable
API keys, an ungated MathJax CDN include, a top-level install.bat, a parallel
manual) is being reviewed separately.

Writing math is one of the least accessible things a screen-reader user can be
asked to do in a normal editor: the notation is visual, and the usual tools
expect a mouse and a palette of symbols. Typing it as **LaTeX** (``E = mc^2``)
or pasting **MathML** is keyboard-only, reviewable character by character, and
already understood by every screen reader that speaks math -- so the dialog
takes text, wraps it in the right delimiters, and gets out of the way.

Two conveniences do the fiddly part:

* A selection is pre-filled and its delimiters are stripped, so pressing the
  shortcut on an existing equation reopens it as ``E = mc^2`` to edit rather
  than making the author retype it (and the display mode is inferred from
  which delimiters were there).
* MathML is inserted verbatim -- it is already a complete element and must not
  be wrapped.

The text itself is built by :mod:`quill.core.math.equation_text`, the one place
both this command and the bundled Math Equations Quillin get it from:
``\\(...\\)`` inline and a one-line ``$$...$$`` block, the delimiters the
preview's MathJax and Word export both understand. This command wrote ``$...$``
until 2026-10-03, which neither of them did.
"""

from __future__ import annotations

from typing import Any

from quill.core.math.equation_text import equation_snippet, split_existing_equation

__all__ = ["INTRO", "EquationsMixin", "equation_snippet", "split_existing_equation"]

#: The dialog's explanation line. Says what the two formats do rather than
#: assuming the author already knows the difference.
INTRO = (
    "Type an equation as LaTeX or paste MathML. LaTeX is wrapped in \\( and \\) "
    "for an inline equation, or in $$ on a line of its own for a block equation. "
    "MathML (<math>...</math>) is inserted exactly as typed, since it already "
    "carries its own markup."
)


class EquationsMixin:
    """Insert > Insert Equation... (Ctrl+Alt+= by default)."""

    def insert_equation(self) -> None:
        """Ask for an equation and insert it at the caret."""
        from quill.core.tagging import InsertionResult
        from quill.ui.web_form import show_web_form

        default_equation, default_mode = split_existing_equation(self.editor.GetStringSelection())
        values: Any = show_web_form(
            self.frame,
            self._wx,
            title="Insert Equation",
            intro=INTRO,
            save_label="Insert",
            fields=[
                {
                    "name": "equation",
                    "label": "Equation (LaTeX or MathML)",
                    "type": "textarea",
                    "value": default_equation,
                    "rows": 6,
                },
                {
                    "name": "display_mode",
                    "label": "Display mode",
                    "type": "select",
                    "value": default_mode,
                    "options": [
                        ("inline", "Inline (within the sentence)"),
                        ("block", "Block (on its own line)"),
                    ],
                },
            ],
        )
        if values is None:
            self._set_status("Insert equation cancelled")
            return
        snippet = equation_snippet(
            str(values.get("equation", "")), str(values.get("display_mode", "inline"))
        )
        if not snippet:
            self._set_status("Insert equation cancelled")
            return
        self._apply_insertion_result(
            InsertionResult(inserted_text=snippet, caret_offset=len(snippet))
        )
        self._set_status("Inserted equation")
