# Math Sample

This document exercises Insert Equation and math reading. It contains two inline
equations, one block equation, and one MathML block, each with a known value so a
tester can confirm what QUILL reads and renders.

Einstein's mass–energy equivalence is \(E = mc^2\), and the Pythagorean theorem is
\(a^2 + b^2 = c^2\). Both are inline equations in QUILL's default `\(...\)`
delimiters.

The block equation below evaluates to one third:

$$\int_0^1 x^2 \, dx = \frac{1}{3}$$

The MathML block below states that x equals one half:

<math xmlns="http://www.w3.org/1998/Math/MathML">
  <mrow>
    <mi>x</mi>
    <mo>=</mo>
    <mfrac><mn>1</mn><mn>2</mn></mfrac>
  </mrow>
</math>
