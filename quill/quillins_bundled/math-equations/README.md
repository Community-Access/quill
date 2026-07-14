# Math Equations

Bundled Quillin that inserts LaTeX or MathML equations at the caret.

- LaTeX equations are wrapped in `\(...\)` (inline) or `$$...$$` (display) delimiters — both are MathJax's own default math delimiters, so preview and HTML export need no extra configuration.
- MathML is inserted verbatim.

Contributed via the Insert menu and the keyboard shortcut Ctrl+Shift+E.

## Math AutoCorrect-style abbreviations

Typing a backslash code followed by a space or punctuation (matching Word's
Math AutoCorrect behavior) expands it to the corresponding symbol — e.g.
`\alpha ` becomes `α`, `\sqrt ` becomes `√`, `\ne ` becomes `≠`. Codes are
seeded from the DAISY-published Word Math AutoCorrect list (daisy.org/MSMathCodes)
and cover Greek letters, relations, set/logic notation, calculus notation, and
geometry symbols. Disable individual entries or the whole set from the Insert
Automation preferences page like any other contributed abbreviation.

## Common Formulas gallery

Ten ready-made algebra and geometry formulas (quadratic formula, Pythagorean
theorem, slope-intercept and point-slope forms, slope/distance/midpoint
formulas, difference of squares, area and circumference of a circle) are
available from **Insert > Snippet Gallery...** — pick one and it inserts
correctly formatted, with nothing to type. Each is a plain `$$...$$` block,
so it can be selected and re-edited with Ctrl+Shift+E like any other
equation.

## Explore Equation Structure

Select an equation (or type/paste one) and run **Insert > Explore Equation
Structure...**, or press **Ctrl+Shift+Grave, F**, to step through it piece
by piece instead of reading it start to finish in one breath.

**Keyboard interaction, precisely:**

- If nothing is selected, an ordinary text prompt asks for LaTeX or MathML
  first (Enter accepts, Escape cancels the command before it starts).
- Each step: QUILL **announces** the current piece (speech only — "Whole
  equation" at the top, or the piece's name once you've descended), then
  opens a standard `wx.SingleChoiceDialog` (a normal Windows single-select
  list) with that piece's children as choices, always followed by **Read
  this part aloud**, then **Back up one level** (once you're below the
  root), then **Done exploring**.
- Inside that list: **Up/Down arrows** move the highlight, typing a letter
  jumps to the next matching item, and **Enter** (or **OK**) activates the
  highlighted choice:
  - a numbered child **descends** into it and reopens the list for its
    children (e.g. a fraction's **Numerator** and **Denominator**);
  - **Read this part aloud** speaks a full reading of only the current
    piece, then **reopens the same list at the same position**;
  - **Back up one level** moves to the parent and reopens the list there;
  - **Done exploring** ends the session and returns focus to the editor.
- **Escape** (or **Cancel**), at any list, at any depth, **ends the whole
  session immediately** — the same as Done exploring. It is *not* "go back
  one level"; **Back up one level** is the dedicated choice for that.

Structural navigation itself (the numerator/denominator/base/exponent
stepping above) is always the lightweight, dependency-free
`quill.core.math.navigator` walker — no download, no setup. **Read this
part aloud** is the one part that upgrades: install the free MathCAT engine
(**Help > Download Optional Components... > MathCAT math speech engine**,
~3 MB, MIT-licensed, daisy/MathCATForC) and that command switches to the
same natural-language math speech engine NVDA itself ships; without it, or
if MathCAT fails on a given formula, the same command keeps working with
navigator's simpler template-based reading — nothing breaks either way. See
`quill.core.math.speech` and `quill.core.math.mathcat_engine`, and
`docs/planning/math.md` for the full architecture writeup.
