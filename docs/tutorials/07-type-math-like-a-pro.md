# Tutorial 7: Write math without learning a new language

**Goal:** put math into a document in a few different ways: pick a ready-made
formula, type one yourself, and explore one by ear. Then check that it looks
right, send it to Word as a real equation (not a picture), and open it again
later, still editable. It takes about thirty minutes and there is nothing to
install. This is for anyone writing algebra, such as homework, lecture notes
or a lab report, who has never used a "math typing" tool and does not want a
lesson in codes first.

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

That is it. A correctly formatted equation is now in your document, and you
did not have to type it. The gallery also has the **Pythagorean Theorem**,
**Slope-Intercept Form**, **Point-Slope Form**, the **Slope**, **Distance**,
and **Midpoint** formulas, **Difference of Squares**, and the **Area** and
**Circumference of a Circle**. If the formula you need is one of these ten,
you are already done with this tutorial. The rest is for formulas the gallery
does not have, or for understanding what is now in your document.

## 2. Your first equation from scratch

For anything the gallery does not have, typing one yourself is just as easy:

1. Type a line of context, like "The Pythagorean theorem relates the sides
   of a right triangle:".
2. Press **Ctrl+Shift+E** (or **Insert > Insert Equation...**).
3. A box appears asking for the equation, and it even suggests an example
   right in the prompt (`E=mc^2`) so you can see the expected shape. Type:
   ```
   a^2 + b^2 = c^2
   ```
   That is all. `^` just means "to the power of." No codes, nothing to look
   up.
4. QUILL asks whether this should sit on its own line (**Block**) or flow
   inside a sentence (**Inline**). Since this formula deserves its own line,
   pick **Block**.
5. Look at what is now in your document: plain text, wrapped in `$$ $$`.
   That is just how QUILL marks "this bit is math" so it can show it
   properly later. You can select it and press
   Ctrl+Shift+E again any time you want to change it, the same way you'd
   reopen any dialog.

Try a second one the same way, inline this time: type "the graph of a
straight line follows", press Ctrl+Shift+E, type `y = mx + b`, and choose
**Inline** so it stays in the sentence. Two equations in, and you still
haven't typed anything you wouldn't type on a calculator.

## 3. When a formula needs a fraction or a square root

Some formulas, like the quadratic formula if you type it yourself, have a
fraction and a square root. For just these two, QUILL needs a small hint: put
the top of a fraction in `\frac{...}{...}` and a square root in `\sqrt{...}`.
That is all you need to learn; everything else stays the same as before.

Press Ctrl+Shift+E and type:

```
x = \frac{-b \pm \sqrt{b^2 - 4ac}}{2a}
```

`\pm` just means "plus or minus". Choose **Block**. If you only remember one
thing from this section, remember this: `\frac{top}{bottom}` and `\sqrt{...}`.
Nothing else about plain equations changes.

## 4. A shortcut, once you're comfortable (totally optional)

Once the basics feel normal, here's a convenience worth knowing about: if you
type a few of those backslash words *while writing an ordinary sentence*, not
inside the equation box, QUILL turns them into the real symbol right away.
Type `\pi ` (with a trailing space) and it becomes `π`. Type `\ne ` and it
becomes `≠`. You do not have to use this. Everything in sections 1 to 3 works
without it. It is just a quick way to put one symbol into a sentence without
opening the equation box. It lives under **Preferences > Editing > Insert
Automation** if you ever want to turn it off. A fuller list is in the
reference section at the end.

## 5. See it look right

Choose **View > Browser Preview...**. Your equations show up as real math: the
fraction stacked, the square root drawn, and `^2` raised. You do not have to
picture what `$$...$$` means; QUILL shows it properly for you every time.

## 6. Explore a formula's structure by ear

Reading a long formula start to finish, in one breath, is hard whether you are
listening or looking. **Select an equation** (or type one fresh) and run
**Insert > Explore Equation Structure...**, or press **Ctrl+Shift+Grave, F**,
to step through it one piece at a time.

**How it works from the keyboard:**

1.  Select `x = \frac{-b \pm \sqrt{b^2 - 4ac}}{2a}` (or any equation) and run the command, or press Ctrl+Shift+Grave, F. If nothing is selected, a text box asks you to type or paste one. Enter accepts it, and Escape cancels.
2.  QUILL speaks where you are ("Whole equation" the first time, or the current piece's name after that), then opens a list of the parts of the current piece. For the whole equation above, that is `x`, `equals`, and the fraction. It is an ordinary Windows list: **Up/Down arrows** move through the items, typing a letter jumps to the next item starting with it, and the list always ends with **Read this part aloud**, then **Back up one level** (only once you've descended at least one level), then **Done exploring**.
3.  **Enter**, or the **OK** button, activates whichever item is highlighted:
    - Choosing a numbered piece (like the fraction) **goes into it**. QUILL says its name ("Fraction") and the list now shows *its* pieces (**Numerator**, **Denominator**).
    - **Read this part aloud** reads just the piece you are on, for example "the square root of b squared minus 4 a c", and then brings the list back so you can keep exploring.
    - **Back up one level** moves to the parent piece and reopens the list there.
    - **Done exploring** closes the explorer and returns you to the editor.
4.  **Escape**, or the **Cancel** button, at any point, **closes the explorer straight away**, just like Done exploring. It does not go back one level; use **Back up one level** for that.

Stepping through the parts works as soon as you install QUILL, with nothing to
download. **Read this part aloud** can sound more natural if you install the
free MathCAT engine (**Help > Download Optional Components... > MathCAT math
speech engine**, about 3 MB). It is the same math speech NVDA uses. Without
it, QUILL uses its own simpler reading, which still works. Neither one gives
you Nemeth or UEB math braille. If you use JAWS, its own Math Viewer works on
the equation once it is in Word (see the next step) and gives you that fuller
experience. QUILL's explorer is a quick way to find your way around a formula
while you are still writing it.

## 7. Hand it to Word

**File > Export > Word Document...**, then open the result in Word (or
LibreOffice). Move to the equation. It is a real Word equation you can edit,
the same kind Word makes itself, not a picture. That matters for anyone using
a screen reader: a real equation is read as math, and a picture of one is not
read at all. If you use JAWS, this is also the point where its own Math Viewer
becomes available on the equation.

## 8. Get it back

Reopen that Word file later (**File > Open...**) and the equation comes back
exactly as you typed it, as plain text you can select and change with
Ctrl+Shift+E. You can pass a file back and forth with a teacher or study
partner who uses Word and never lose the formula.

## If something doesn't look right

- **The preview still shows literal `$$...$$` or `\(...\)` text.** Check that
  both delimiters actually surround the formula. A stray character inside the
  equation (a `{` with no matching `}` is the most common one) can stop it
  from being recognized as math. Reopen it with Ctrl+Shift+E to see and fix
  the plain LaTeX.
- **A fraction or square root shows the raw `\frac{}{}` / `\sqrt{}` text
  instead of showing properly.** This almost always means a missing closing
  brace `}`. Check that every `{` has a matching `}`.
- **The equation looks fine in QUILL but not after exporting to Word.** Open
  the exported file in QUILL (File > Open). If the formula comes back
  correctly, it is fine, and the problem is with the program you opened it in
  elsewhere. Try a different one.

## Quick reference

**The ten gallery formulas** (Insert > Snippet Gallery...): Quadratic
Formula, Pythagorean Theorem, Slope-Intercept Form, Point-Slope Form, Slope
Formula, Distance Formula, Midpoint Formula, Difference of Squares, Area of
a Circle, Circumference of a Circle.

**The typed shortcuts, in full.** Type the code plus a trailing space or
punctuation, anywhere in ordinary prose (not inside the equation box), and it
becomes the symbol straight away. These come from the Word Math AutoCorrect
list published by DAISY (daisy.org/MSMathCodes), so if you have typed math in
Word, you already know them. You can turn any of them off, or all of them, in
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

Capital letters matter: `\delta ` gives lowercase δ and `\Delta ` gives
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

## A routine to try

Check the **Snippet Gallery** first. It has more than you might expect. For
anything else, start with equations that only need `^`, `/`, `+`, and `-`;
reach for `\frac{}{}` and `\sqrt{}` only when a formula needs them. Use
**Explore Equation Structure** when a formula is hard to hold in your head all
at once. Check **Browser Preview** before you submit anything. Export to Word
only when it actually needs to leave QUILL.

*Want an equation explained instead of just typed? Select it and ask the AI
menu's **Math Tutor**. It explains what each part means and tells you the
formula's name if it is a well-known one. It does not solve anything or change
your document.*

**Next:** [GitHub inside QUILL](08-github-inside-quill.md).
