# Tutorial 7: Write math without learning a new language

**Goal:** get math into a document several different ways — picking a
ready-made formula, typing one from scratch, and exploring one by ear — see
it look right on screen, hand it to Word as a real equation (not a
picture), and get it back again later, still editable. Thirty minutes,
nothing to install. Built for anyone writing algebra — homework, lecture
notes, a lab report — who has never used a "math typing" tool before and
doesn't want a syntax lesson first.

You will not need to memorize anything before you start. The fastest path
needs no typing at all; the next needs only `^` for a power; only the
fancier formulas need a couple of extra words.

## 1. The easiest way in: pick a ready-made formula

QUILL ships ten common algebra and geometry formulas you can insert with no
typing at all:

1. Open a document and type a line of context, like "The quadratic formula
   solves any equation of the form ax squared plus bx plus c equals zero:".
2. **Insert > Snippet Gallery...**
3. Find **Quadratic Formula** in the list and insert it.

Done — a correctly formatted equation lands in your document, nothing
typed, nothing to get wrong. The gallery also has the **Pythagorean
Theorem**, **Slope-Intercept Form**, **Point-Slope Form**, the **Slope**,
**Distance**, and **Midpoint** formulas, **Difference of Squares**, and the
**Area** and **Circumference of a Circle**. If the formula you need is one
of these ten, you are already done with this tutorial — everything past
this point is for formulas the gallery doesn't have, or for understanding
what landed in your document.

## 2. Your first equation from scratch

For anything the gallery doesn't cover, typing one yourself is just as
approachable:

1. Type a line of context, like "The Pythagorean theorem relates the sides
   of a right triangle:".
2. Press **Ctrl+Shift+E** (or **Insert > Insert Equation...**).
3. A box appears asking for the equation, and it even suggests an example
   right in the prompt (`E=mc^2`) so you can see the expected shape. Type:
   ```
   a^2 + b^2 = c^2
   ```
   That's it — `^` just means "to the power of." No backslashes, no codes,
   nothing to look up.
4. QUILL asks whether this should sit on its own line (**Block**) or flow
   inside a sentence (**Inline**). Since this formula deserves its own line,
   pick **Block**.
5. Look at what landed in your document: plain text, wrapped in `$$ $$`.
   Nothing mysterious happened — that's just how QUILL marks "this bit is
   math" so it can be typeset properly later. You can select it and press
   Ctrl+Shift+E again any time you want to change it, the same way you'd
   reopen any dialog.

Try a second one the same way, inline this time: type "the graph of a
straight line follows", press Ctrl+Shift+E, type `y = mx + b`, and choose
**Inline** so it stays in the sentence. Two equations in, and you still
haven't typed anything you wouldn't type on a calculator.

## 3. When a formula needs a fraction or a square root

Some formulas — like the quadratic formula, if you type it yourself instead
of using the gallery — have a fraction stacked over another expression, and
a square root. For just these two, QUILL needs a small hint: put the top of
a fraction in `\frac{...}{...}` and a square root in `\sqrt{...}`. That's
genuinely all you need to learn; everything else stays exactly like before.

Press Ctrl+Shift+E and type:

```
x = \frac{-b \pm \sqrt{b^2 - 4ac}}{2a}
```

`\pm` just means "plus or minus" — read it the same way you'd read it out
loud. Choose **Block**. If you only remember one thing from this section,
remember this: `\frac{top}{bottom}` and `\sqrt{...}`. Nothing else about
plain equations changes.

## 4. A shortcut, once you're comfortable (totally optional)

Once the basics feel normal, here's a convenience worth knowing about: if
you type a few of those backslash words *while writing an ordinary
sentence* — not inside the equation box — QUILL turns them into the actual
symbol right away. Type `\pi ` (with a trailing space) and it becomes `π`.
Type `\ne ` and it becomes `≠`. This is entirely optional — everything in
Sections 1 through 3 works with or without it — but it's a fast way to drop
a single symbol into a sentence without opening the equation box at all. It
lives under **Preferences > Editing > Insert Automation** if you ever want
to turn it off. A fuller list is in the reference section at the end.

## 5. See it look right

**View > Browser Preview...** — your equations show up as real typeset
math: the fraction actually stacked, the square root actually drawn, `^2`
actually raised. You are not expected to picture what `$$...$$` means in
your head; QUILL renders it for you, automatically, every time — this was
checked directly against a real rendered page while writing this tutorial,
not assumed.

## 6. Explore a formula's structure by ear

Reading a long formula start to finish, in one breath, is hard whether you
are listening or looking. **Select an equation** (or type one fresh) and run
**Insert > Explore Equation Structure...** — or press **Ctrl+Shift+Grave,
F** directly from the keyboard, no menu required — to step through it one
piece at a time instead.

**Exactly how the keyboard works, start to finish:**

1. Select `x = \frac{-b \pm \sqrt{b^2 - 4ac}}{2a}` (or any equation) and run
   the command, or press Ctrl+Shift+Grave, F. If nothing is selected, a
   normal text box prompts you to type or paste one instead — Enter accepts
   it, Escape cancels the whole command before it starts.
2. QUILL speaks where you are ("Whole equation" the first time, or the
   current piece's name after that), then opens a standard single-selection
   list dialog with the current piece's contents as choices — for the whole
   equation above, that is `x`, `equals`, and the fraction. This is an
   ordinary Windows list box: **Up/Down arrows** move through the items,
   typing a letter jumps to the next item starting with it, and the list
   always ends with **Read this part aloud**, then **Back up one level**
   (only once you've descended at least one level), then **Done exploring**.
3. **Enter**, or the **OK** button, activates whichever item is highlighted:
   - Choosing a numbered piece (like the fraction) **descends into it** —
     QUILL speaks its name ("Fraction") and the list refreshes to show
     *its* pieces (**Numerator**, **Denominator**).
   - **Read this part aloud** speaks a full reading of exactly the piece
     you're currently on — e.g. "the square root of b squared minus 4 a c"
     — without the rest of the formula around it, then reopens the same
     list so you can keep exploring from where you were.
   - **Back up one level** moves to the parent piece and reopens the list
     there.
   - **Done exploring** closes the explorer and returns you to the editor.
4. **Escape**, or the **Cancel** button, at any point — on any list, at any
   depth — **ends the whole session immediately**, exactly like choosing
   Done exploring. It does not step back one level; **Back up one level**
   is the only way to retrace a step without exiting entirely.

This is a genuinely useful way to make sense of a formula piece by piece,
but it's worth being precise about what it is: **the stepping through
numerator/denominator/base/exponent is always a plain, dependency-free
structural walk** — no download, no setup, works the moment you install
QUILL. **Read this part aloud** is the one piece that can get richer: if
you install the free MathCAT engine (**Help > Download Optional
Components... > MathCAT math speech engine**, about 3 MB, one-time), that
command switches from a template-built reading to the same natural-language
math speech engine NVDA itself ships. Without it — or if MathCAT fails on a
particular formula — the same command keeps working with the simpler
built-in reading; nothing breaks either way. Neither path is
the Nemeth or UEB math braille a dedicated screen-reader math engine
produces on its own display. If you use JAWS, its own Math Viewer (on a
native Word equation, after the export step below) gives you that fuller,
braille-aware experience; QUILL's explorer is the fast, no-extra-software
version for getting your bearings in a formula while you're still writing
it.

## 7. Hand it to Word

**File > Export > Word Document...**, then open the result in Word (or
LibreOffice). Click on the equation — it's a real, editable Word equation,
the same kind you'd get from Word's own equation tools, not a picture and
not stray text. That matters for anyone reading with a screen reader too:
a real equation gets read as math; a picture of one doesn't get read at
all. If you use JAWS, this is also the point where its own Math Viewer
becomes available on the equation.

## 8. Get it back

Reopen that Word file later (**File > Open...**) and the equation comes
back exactly as you typed it — still plain text you can select and edit
with Ctrl+Shift+E, not frozen into anything. Handing a file back and forth
with a professor or study partner who uses Word never loses the formula.

## If something doesn't look right

- **The preview still shows literal `$$...$$` or `\(...\)` text.** Check
  that both delimiters actually surround the formula with nothing missing —
  a stray character inside the equation (an unmatched `{` is the most common
  one) can stop it from being recognized as math. Reopen it with
  Ctrl+Shift+E to see and fix the plain LaTeX.
- **A fraction or square root shows the raw `\frac{}{}` / `\sqrt{}` text
  instead of rendering.** This almost always means a missing closing brace
  `}` — count that every `{` has a matching `}`.
- **The equation looks fine in QUILL but not after exporting to Word.**
  Reopen the exported file in QUILL (File > Open) — if the text comes back
  correctly, the formula itself was fine and the issue is in how the Word
  file is being viewed elsewhere (try a different Word-compatible viewer).

## Quick reference

**The ten gallery formulas** (Insert > Snippet Gallery...): Quadratic
Formula, Pythagorean Theorem, Slope-Intercept Form, Point-Slope Form, Slope
Formula, Distance Formula, Midpoint Formula, Difference of Squares, Area of
a Circle, Circumference of a Circle.

**The typed shortcuts, in full.** Type the code plus a trailing space or
punctuation, anywhere in ordinary prose (not inside the equation box), and
it becomes the symbol immediately. These are seeded from the
DAISY-published Word Math AutoCorrect list (daisy.org/MSMathCodes), so if
you've ever typed math in Word, the codes carry straight over. Every one of
these can be turned off individually — or all at once — from
**Preferences > Editing > Insert Automation**.

*Operators*

| Type this | Get this | Type this | Get this |
|---|---|---|---|
| `\cdot ` | ⋅ | `\times ` | × |
| `\div ` | ÷ | `\pm ` | ± |
| `\mp ` | ∓ | `\sqrt ` | √ |
| `\cbrt ` | ∛ | `\qdrt ` | ∜ |
| `\infty ` | ∞ | `\circ ` | ∘ |

*Relations*

| Type this | Get this | Type this | Get this |
|---|---|---|---|
| `\ne ` / `\neq ` | ≠ | `\le ` / `\leq ` | ≤ |
| `\ge ` / `\geq ` | ≥ | `\approx ` | ≈ |
| `\propto ` | ∝ | `\cong ` | ≅ |
| `\sim ` | ∼ | `\ll ` / `\gg ` | ≪ / ≫ |

*Sets and logic*

| Type this | Get this | Type this | Get this |
|---|---|---|---|
| `\in ` | ∈ | `\notin ` | ∉ |
| `\subset ` | ⊂ | `\subseteq ` | ⊆ |
| `\cup ` / `\cap ` | ∪ / ∩ | `\rightarrow ` / `\to ` | → |
| `\leftrightarrow ` | ↔ | `\wedge ` / `\vee ` | ∧ / ∨ |
| `\neg ` | ¬ | `\forall ` / `\exists ` | ∀ / ∃ |
| `\emptyset ` | ∅ | | |

*Number sets*

| Type this | Get this | Type this | Get this |
|---|---|---|---|
| `\doubleN ` | ℕ | `\doubleZ ` | ℤ |
| `\doubleQ ` | ℚ | `\doubleR ` | ℝ |
| `\doubleC ` | ℂ | | |

*Greek letters*

| Type this | Get this | Type this | Get this |
|---|---|---|---|
| `\alpha ` / `\beta ` | α / β | `\gamma ` / `\delta ` | γ / δ |
| `\Delta ` | Δ | `\theta ` / `\lambda ` | θ / λ |
| `\mu ` / `\pi ` | μ / π | `\rho ` / `\Sigma ` | ρ / Σ |
| `\tau ` / `\phi ` | τ / ϕ | `\chi ` / `\omega ` | χ / ω |

Note that case matters — `\delta ` gives lowercase δ and `\Delta ` gives
uppercase Δ, the same way they're different symbols in math itself.

*Calculus*

| Type this | Get this | Type this | Get this |
|---|---|---|---|
| `\int ` | ∫ | `\iint ` / `\iiint ` | ∬ / ∭ |
| `\partial ` | ∂ | `\sum ` | ∑ |
| `\prod ` | ∏ | `\nabla ` | ∇ |
| `\prime ` | ′ | `\pprime ` | ″ |

*Geometry and vectors*

| Type this | Get this | Type this | Get this |
|---|---|---|---|
| `\vec ` | → | `\angle ` | ∠ |
| `\perp ` | ⊥ | `\parallel ` | ∥ |
| `\degree ` | ° | `\degc ` / `\degf ` | °C / °F |

*Miscellaneous*

| Type this | Get this | Type this | Get this |
|---|---|---|---|
| `\therefore ` | ∴ | `\because ` | ∵ |
| `\cdots ` | ⋯ | `\vdots ` / `\ddots ` | ⋮ / ⋱ |
| `\dots ` / `\ldots ` | … | | |

## The routine worth adopting

Check the **Snippet Gallery** first — it covers more ground than you'd
expect. For anything else, start with equations that only need `^`, `/`,
`+`, and `-`; reach for `\frac{}{}` and `\sqrt{}` only when a formula
genuinely needs them. Use **Explore Equation Structure** when a formula is
hard to hold in your head all at once. Check **Browser Preview** before you
submit anything. Export to Word only when it actually needs to leave QUILL.

*Want an equation explained instead of just typed? Select it and ask the AI
menu's **Math Tutor** agent — it walks through what each part means and
names the formula if it's a well-known one, without solving anything or
changing your document.*

**Next:** [GitHub inside QUILL](08-github-inside-quill.md).
