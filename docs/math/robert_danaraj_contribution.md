

From: Rms Danaraj <salorajan@gmail.com> 
Sent: Tuesday, June 16, 2026 7:49 AM
To: Jeff Bishop <jeff@jeffbishop.com>
Subject: Re: [BITS-Development] feedback heard and valued ...

Subject: Update: LaTeX/MathML Equation Support Integration in Quill & Testing Request

Hi  Jeff and BITS Team,

I'm pleased to report humbly that we have successfully integrated first-class mathematical equation typesetting and rendering support (LaTeX and MathML) into the Quill editor.

Our new add-on enhances Quill with the following capabilities:
1. Accessible Input Dialog: A screen-reader friendly dialog form (triggered via Ctrl+Shift+E or the Insert menu) with automatic formula detection, stripping existing delimiters for quick editing.
2. High-Resolution rendering: Real-time math compiling using MathJax 3 in browser previews (Ctrl+Shift+V) and HTML document exports.
3. Native Integration: Secure keybindings, menu-bar actions, and comprehensive unit tests ensuring stability.

Using Quill's native Document IO pipeline, we programmatically generated a test suite named "latex_testing" in three formats to verify the outputs:
* latex_testing.md (Markdown): Quill's canonical editing format containing raw LaTeX blocks.
* latex_testing.html (HTML Preview): Visual mathematical displays compiled via MathJax 3, fully readable by screen readers in any browser.
* latex_testing.docx (Word Document): Formatted via Pandoc into native OMML equations, which open in Word or Google Docs as fully editable and accessible formulas.

Please help us test this new feature, particularly regarding screen-reader navigation of the input forms and equations, and let us know if you have any guidance for further improvements.
I am waiting for your answer to push my quill branch with math equations to GitHub. Actually I am critically testing.

Best regards,
Robert Danaraj
