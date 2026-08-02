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
  shortcut on an existing ``$E = mc^2$`` reopens it as ``E = mc^2`` to edit
  rather than making the author retype it (and the display mode is inferred
  from which delimiters were there).
* MathML is inserted verbatim -- it is already a complete element and must not
  be wrapped in ``$``.

The rendering half already exists: ``core/browser_preview.py`` loads MathJax for
a document that actually contains math, so an inserted equation shows up
rendered in the live preview and in exported HTML with nothing else to set up.
"""

from __future__ import annotations

from typing import Any

#: The dialog's explanation line. Says what the two formats do rather than
#: assuming the author already knows the difference.
INTRO = (
    "Type an equation as LaTeX or paste MathML. LaTeX is wrapped in $ for an "
    "inline equation or $$ for a block equation on its own line. MathML "
    "(<math>...</math>) is inserted exactly as typed, since it already carries "
    "its own markup."
)


def equation_snippet(equation: str, display_mode: str) -> str:
    """The text to insert for *equation* in *display_mode*.

    MathML is returned untouched. LaTeX is wrapped: ``$...$`` inline, or
    ``$$`` on its own lines for a block equation, which is what Markdown
    renderers (and MathJax in QUILL's preview) expect.
    """
    text = (equation or "").strip()
    if not text:
        return ""
    if text.startswith("<"):
        return text
    if display_mode == "block":
        return f"$$\n{text}\n$$"
    return f"${text}$"


def split_existing_equation(selection: str) -> tuple[str, str]:
    """Split a selected equation into ``(equation, display_mode)``.

    Lets the shortcut act as "edit this equation" when the author selects one
    they already wrote: the delimiters come off so the field holds just the
    math, and the mode they used is preselected. A selection that is not an
    equation comes back unchanged as inline.
    """
    text = (selection or "").strip()
    if text.startswith("$$") and text.endswith("$$") and len(text) > 4:
        return text[2:-2].strip(), "block"
    if text.startswith("$") and text.endswith("$") and len(text) > 2:
        return text[1:-1].strip(), "inline"
    return selection or "", "inline"


class EquationsMixin:
    """Insert > Insert Equation... (Ctrl+Shift+E)."""

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
