# Tutorial 6: Make a document accessible with GLOW

**Goal:** take a real document from "probably fine" to *verified, graded,
and repaired* — using GLOW, QUILL's built-in accessibility review system.

GLOW (Guided Layout and Output Workflow) is guided confidence, not a
compliance dashboard: it explains each finding in plain language and only
applies fixes you approve. Everything is under **Tools > GLOW**.

## 0. Switch it on (GLOW is experimental)

GLOW ships as an experimental feature, off by default while it matures:

1. **Preferences > Experimental.**
2. Tick **Enable experimental features** (the master switch — until it is on,
   every experimental control is disabled and skipped in the tab order).
3. Tick **GLOW accessibility review and repair (experimental)**.
4. Apply. The **Tools > GLOW** menu appears immediately — no restart.

Experimental means still maturing, not unsafe: every GLOW action below keeps
the review-first, never-touch-the-original contract.

## 1. Audit what you are writing

1. Open any Markdown or HTML document you have written.
2. **Tools > GLOW > GLOW Audit Current Document.**
3. The report opens as a normal tab. Arrow through it. Each finding gives:
   the rule, the severity, the location, and a plain-language suggestion —
   e.g. heading levels that jump (H1 straight to H4), links that just say
   "click here", images without alt text, HTML missing `lang`, tables
   without header cells, paragraphs too dense to listen to.

For just the section you are working on, use **GLOW Audit Selection /
Paragraph** instead.

## 2. Fix — with your eyes open

1. **GLOW Fix Current Document.** QUILL opens the repaired text as a *named
   preview tab* and immediately starts a **compare session** against your
   original.
2. Walk the differences. Accept knowing exactly what changed; reject and
   nothing happened. Never a silent rewrite.
3. For quick in-place cleanup of one block, **GLOW Fix Selection /
   Paragraph** — the replacement stays selected so `Ctrl+Z` is one step
   away.

Fixable findings (heading-marker spacing, missing `lang`, missing alt
attributes, trailing whitespace) are marked `[auto-fix]` in the audit;
judgment calls (link text, dense paragraphs) stay yours.

## 3. Grade the file you are about to send

The headline capability: GLOW audits **structured files on disk** — Word,
PowerPoint, Excel, PDF, EPUB.

1. Export your document to Word (**File > Export > Word Document...**), or
   pick any existing docx.
2. **Tools > GLOW > GLOW Audit File...** and choose it. The audit runs in
   the background and returns a **score out of 100, a letter grade**, and
   every finding.
3. To repair: **GLOW Fix File...**. GLOW writes a fixed copy *next to* the
   original (`report.docx` → `report-accessible.docx`), confirms the
   destination first, and opens the post-fix audit so you can verify the
   improvement. **The original file is never modified.**

## 4. Keep the engine fresh (only when you ask)

**Help > Check for GLOW Updates...** checks for a newer accessibility
engine. The check runs only on your command, the download is confirmed
separately, every wheel is signature- and checksum-verified, and a failed
install rolls back automatically. The engine's optional networked helpers
(AI alt-text, PII redaction) are off until you explicitly consent, per use —
the default GLOW workflow is entirely on-device.

## 5. The routine worth adopting

Draft → **Audit Current Document** → fix the judgment calls yourself →
**Fix Current Document** for the mechanical ones (accept from the compare) →
export → **Audit File** as the final gate. Two minutes, and you are shipping
documents more accessible than most sighted authors produce.

*Want an ambitious pass beyond the deterministic rules? The AI menu's
**Accessibility Tune-Up** agent drafts a broader improvement plan — 
reviewable like everything else.*
