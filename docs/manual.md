# Quill Mathematics & Scientific Equation Manual

Quill provides first-class support for inserting, editing, and rendering mathematical and scientific equations. You can write equations using either **LaTeX** (a standard typesetting language for math) or **MathML** (an XML-based format that is highly accessible to screen readers).

---

## 1. How to Insert an Equation

There are two ways to open the **Insert Equation** dialog in Quill:

1. **Keyboard Shortcut**: Press `Ctrl + Shift + E` inside the editor.
2. **Menu Bar**: Navigate to **Insert** > **Insert Equation...**

### The Insert Equation Dialog

The dialog is built as an accessible HTML-based web form, fully optimized for keyboard navigation and screen readers:

* **Equation Field**: A text area where you type or paste your LaTeX or MathML code.
* **Display Mode**: A dropdown selection between:
  * **Inline**: The equation will be embedded directly within the sentence (e.g., `$E = mc^2$`).
  * **Block**: The equation will be placed on its own line, centered, and given vertical spacing (e.g., inside `$$ ... $$` delimiters).
* **Automatic selection detection**: If you select a formula in your editor text before pressing `Ctrl + Shift + E`, the formula will automatically pre-populate the dialog and strip existing delimiters (like `$` or `$$`), allowing you to edit it quickly.

---

## 2. LaTeX Equation Examples

LaTeX is the most common way to write equations. Here are several examples you can copy and paste into the editor.

### 2.1 Basic Operations & Algebra
* **Inline Math**: `$a^2 + b^2 = c^2$`
* **Quadratic Formula (Block display)**:
  ```latex
  x = \frac{-b \pm \sqrt{b^2 - 4ac}}{2a}
  ```
* **Systems of Equations**:
  ```latex
  \begin{cases}
  2x + 3y = 8 \\
  x - y = -1
  \end{cases}
  ```

### 2.2 Calculus
* **Limits**: `$\lim_{x \to \infty} \frac{1}{x} = 0$`
* **Derivatives**: `$\frac{df}{dx} = \lim_{h \to 0} \frac{f(x+h) - f(x)}{h}$`
* **Definite Integral (Block display)**:
  ```latex
  \int_{a}^{b} x^2 \, dx = \left[ \frac{x^3}{3} \right]_{a}^{b}
  ```

### 2.3 Linear Algebra & Matrices
* **Matrix (Block display)**:
  ```latex
  A = \begin{pmatrix}
  a & b \\
  c & d
  \end{pmatrix}
  ```
* **Determinant**:
  ```latex
  |A| = ad - bc
  ```

### 2.4 Statistics & Probability
* **Normal Distribution Formula (Block display)**:
  ```latex
  f(x) = \frac{1}{\sigma \sqrt{2\pi}} e^{-\frac{1}{2} \left(\frac{x - \mu}{\sigma}\right)^2}
  ```

---

## 3. MathML Equation Examples

MathML is raw XML. If your input starts with `<math` or `<`, Quill automatically recognizes it as MathML and inserts it directly into the document without adding LaTeX delimiters.

* **Fractions in MathML**:
  ```xml
  <math xmlns="http://www.w3.org/1999/xhtml">
    <mfrac>
      <mi>x</mi>
      <mi>y</mi>
    </mfrac>
  </math>
  ```
* **Super/Subscripts in MathML**:
  ```xml
  <math xmlns="http://www.w3.org/1999/xhtml">
    <msubsup>
      <mi>x</mi>
      <mn>2</mn>
      <mn>3</mn>
    </msubsup>
  </math>
  ```

---

## 4. How Equations are Rendered

Quill integrates **MathJax 3** (`tex-mml-chtml.js`) to render mathematical content beautifully.

* **Live Browser Preview (`Ctrl + Shift + V` / Split Preview)**: When you view the browser preview of your document, all LaTeX (`$ ... $` and `$$ ... $$`) and MathML nodes are automatically compiled into high-resolution, accessible SVG math elements.
* **HTML Export**: Saving the document as HTML (**File** > **Save As** > **HTML**) will embed the MathJax libraries directly into the output document so that it renders math in any standard browser.

---

## 5. Screen-Reader Accessibility Tips

Quill is designed screen-reader-first. Visually impaired users can utilize the following workflow to read math:

1. **Typing math**: Standard screen readers (NVDA, JAWS, and Narrator) will echo characters and words as they are typed into the accessible input form.
2. **Reviewing math**: Open the HTML preview pane (`Ctrl + Shift + V`). When the preview gains focus, screen readers natively interact with MathML nodes:
   * **NVDA** (with the MathPlayer plugin, or natively in Chromium) will speak the equation semantically (e.g., reading `\frac{1}{2}` as "one half" rather than "backslash frac left brace one right brace...").
   * **JAWS** handles MathML content inside the preview pane by allowing you to browse equations using standard reading commands.
3. **Narration Feedback**: Upon submitting the equation dialogue, the status bar announces `"Inserted math equation"` to confirm the insert.

---

## 6. AI-Assisted Mathematics & Equation Synthesis

Users can leverage Quill's built-in **AI Writing Assistant** (**AI** > **Ask Quill Chat...** or via the **Prompt Library**) to simplify the creation, description, and validation of mathematical equations:

* **Natural Language to LaTeX/MathML**: If you do not know LaTeX syntax, open the AI chat and ask the assistant (e.g., *"Write a LaTeX formula for the standard deviation of a sample"*). The assistant will generate the correct markup (e.g., `$\sigma = \sqrt{\frac{1}{N-1} \sum_{i=1}^{N} (x_i - \bar{x})^2}$`) which you can easily copy or insert into your document.
* **Equation Verbalization**: Screen-reader users can select a complex equation in the document and choose the **Explain Math Formula** prompt. The AI will explain the equation in clear, conversational English (e.g., *"A fraction with a numerator of negative b plus or minus the square root of..."*), making it easy to comprehend without parsing raw syntax characters.
* **Syntax Auditing**: If an equation fails to render correctly in the live preview, ask the assistant to check it for syntax errors. The agent will analyze the formula and identify issues like mismatched braces `{}`, missing backslashes, or unclosed XML elements in MathML.
* **Format Conversion**: The assistant can translate raw MathML code into clean LaTeX, or vice versa, ensuring consistent formatting styles across your documents.

