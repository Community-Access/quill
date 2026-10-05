# Tutorial 6: Make a document accessible with GLOW

**Goal:** take a real document from "probably fine" to *checked, graded and
fixed*, using GLOW, QUILL's built-in accessibility checker.

GLOW (Guided Layout and Output Workflow) explains each problem it finds in
plain words, and only makes the fixes you agree to. Everything is under
**Tools > GLOW**.

## 0. Switch it on (GLOW is experimental)

GLOW is still experimental, so it is off until you turn it on:

1. **Preferences > Experimental.**
2. Tick **Enable experimental features**. Until this is on, the other
   experimental choices are greyed out and Tab skips them.
3. Tick **GLOW accessibility review and repair (experimental)**.
4. Apply. The **Tools > GLOW** menu appears right away. You do not need to
   restart.

Experimental means it is still being improved, not that it is unsafe. GLOW
always shows you a change before making it, and never changes your original
file.

## 1. Audit what you are writing

1. Open any Markdown or HTML document you have written.
2. **Tools > GLOW > GLOW Audit Current Document.**
3. The report opens as a normal tab. Arrow through it. Each finding tells you
   what the problem is, how serious it is, where it is, and what to do about
   it. For example: headings that skip a level (H1 straight to H4), links that
   just say "click here", pictures with no description, tables with no header
   cells, or paragraphs too long to listen to comfortably.

For just the section you are working on, use **GLOW Audit Selection /
Paragraph** instead.

## 2. Fix it, and see every change

1. **GLOW Fix Current Document.** QUILL opens the repaired text in a *new
   preview tab* and compares it with your original right away.
2. Go through the differences. If you accept, you know exactly what changed.
   If you reject, nothing changes. GLOW never rewrites anything without
   showing you.
3. To quickly fix one paragraph where it is, use **GLOW Fix Selection /
   Paragraph**. The fixed text stays selected, and `Ctrl+Z` undoes it in one
   step.

Problems GLOW can fix for you are marked `[auto-fix]` in the report. Things
that need your judgment, like link wording or long paragraphs, are left for
you.

## 3. Grade the file you are about to send

GLOW can also check **files on your computer**: Word, PowerPoint, Excel, PDF
and EPUB.

1. Export your document to Word (**File > Export > Word Document...**), or
   pick any existing docx.
2. **Tools > GLOW > GLOW Audit File...** and choose it. The audit runs in the
   background and returns a **score out of 100, a letter grade**, and every
   finding.
3. To fix it, choose **GLOW Fix File...**. GLOW saves a fixed copy *next to*
   the original (`report.docx` becomes `report-accessible.docx`), checks with
   you where to save it, and then shows you a new report so you can see what
   improved. **The original file is never modified.**

## 4. Keep GLOW up to date (only when you ask)

**Help > Check for GLOW Updates...** checks for a newer version of GLOW. It
only checks when you ask, and asks again before it downloads anything.
Downloads are checked to make sure they are safe, and if an update fails, your
old version is put back. A few optional extras go online, such as writing
picture descriptions with AI; they ask you first every time. Everything else
in GLOW stays on your computer.

## 5. A routine to try

1. Write your draft.
2. Run **Audit Current Document**.
3. Fix the things that need your judgment yourself.
4. Run **Fix Current Document** for the rest, and accept the changes you want.
5. Export your file.
6. Run **Audit File** on it one last time.

It takes a couple of minutes, and the people you send it to will thank you.

*Want more ideas than the checker gives? The AI menu's **Accessibility
Tune-Up** suggests a wider plan for improving your document, and you check
every suggestion before anything changes.*
