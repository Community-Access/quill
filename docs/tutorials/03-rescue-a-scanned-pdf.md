# Tutorial 3: Rescue a scanned PDF

**Goal:** turn a scanned, image-only PDF (or a photo of a page) into real,
editable, searchable text — free, on your own machine, with nothing uploaded.

## Background: the one rule

**Import / Convert Document** routes every file through free, local services
first: the built-in **MarkItDown** converter for born-digital files, then
free on-device **Tesseract OCR** for scans. There is no cloud step, no
account, and no cost. QUILL always asks before running OCR, and never opens
an empty result silently.

## 1. One-time setup: install the OCR engine

1. **Tools > Reading & Dictation > Install Local OCR Engine (Tesseract)...**
2. QUILL states the size (about 48 MB) and exactly what will happen, then
   downloads the official installer from QUILL's own verified release and
   checks it byte-for-byte.
3. The installer opens **visibly** — complete it like any normal install.
   (If Tesseract is already on your machine, or installed via Homebrew on a
   Mac, skip this: QUILL finds it automatically.)

## 2. Convert the document

1. **File > Import > Import / Convert Document (OCR)...** and pick your PDF.
2. If the PDF actually has a text layer, it opens instantly as editable text
   — done, and QUILL announces "Nothing was uploaded."
3. If it is a scan, QUILL says so honestly: *"QUILL could not find readable
   text in this document. It looks scanned or image-based. Run free
   on-device OCR? This stays on your computer and does not upload
   anything."*
4. Choose **Yes**. QUILL recognizes each page ("Recognizing page 3 of 12...")
   and opens the result as a new document, with page boundaries kept as
   searchable `<!-- Page N -->` markers.

Photos work too: point the same command at a `.png` or `.jpg` of a page and
it goes straight to OCR.

## 3. Judge the result

QUILL reports recognition **confidence** out of 100. Above ~80 on a clean
scan, expect near-perfect text. When QUILL warns that confidence is low:

- Re-scan straighter/darker if you can — quality in, quality out.
- Read the result critically; OCR errors cluster around numbers, names, and
  poor contrast regions.
- Run a spell check (`palette > spell`) — OCR errors light up fast.

## 4. Finish the job

- Save as Markdown or plain text, or **File > Export** to Word.
- Run **GLOW Audit Current Document** to catch structural issues in the
  recovered text (see [tutorial 6](06-make-it-accessible-with-glow.md)).
- For a recurring scan pile, aim a **watch folder** at your scanner's output
  directory.

## Where this is honest

**Tools > Reading & Dictation > OCR and Conversion Services...** describes
every service in plain language — what it does, what it costs (nothing),
what stays local (everything) — and shows the engine's install status. A
consent-gated cloud tier for the hardest documents is planned; the free
local tiers always run first.

**Next:** [Turn a document into an audiobook](04-document-to-audiobook.md).
