# Tutorial 3: Rescue a scanned PDF

**Goal:** turn a scanned, image-only PDF (or a photo of a page) into real text
you can edit and search. It is free, it happens on your own computer, and
nothing is uploaded.

## Before you start

**Import / Convert Document** uses free tools on your own computer. Files that
already contain text are converted by the built-in **MarkItDown** converter.
Scanned pages are read by **Tesseract OCR**, which recognizes the text in a
picture. There is no account and no cost. QUILL always asks before it runs
OCR, and tells you if it finds nothing.

## 1. One-time setup: install the OCR engine

1. **Tools > Reading & Dictation > Install Local OCR Engine (Tesseract)...**
2. QUILL tells you the size (about 48 MB) and what will happen, then downloads
   the installer and checks that it arrived safely.
3. The Tesseract installer opens. Go through it like any other install. (If
   Tesseract is already on your machine, or installed via Homebrew on a Mac,
   skip this: QUILL finds it automatically.)

## 2. Convert the document

1. **File > Import > Import / Convert Document (OCR)...** and pick your PDF.
2. If the PDF actually has a text layer, it opens instantly as editable text.
   You are done, and QUILL tells you "Nothing was uploaded."
3. If it is a scan, QUILL tells you: *"QUILL could not find readable text in
   this document. It looks scanned or image-based. Run free on-device OCR?
   This stays on your computer and does not upload anything."*
4. Choose **Yes**. QUILL recognizes each page ("Recognizing page 3 of 12...")
   and opens the result as a new document, with page boundaries kept as
   searchable `<!-- Page N -->` markers.

Photos work too: point the same command at a `.png` or `.jpg` of a page and
it goes straight to OCR.

## 3. Judge the result

QUILL reports recognition **confidence** out of 100. Above about 80 on a clean
scan, expect nearly perfect text. When QUILL warns that confidence is low:

- Scan the page again, straighter or darker, if you can. A better scan gives
  better text.
- Read the result critically; OCR errors cluster around numbers, names, and
  poor contrast regions.
- Run a spell check (`palette > spell`). It finds OCR mistakes quickly.

## 4. Finish the job

- Save as Markdown or plain text, or **File > Export** to Word.
- Run **GLOW Audit Current Document** to catch structural issues in the
  recovered text (see [tutorial 6](06-make-it-accessible-with-glow.md)).
- For a recurring scan pile, aim a **watch folder** at your scanner's output
  directory.

## What each service does

**Tools > Reading & Dictation > OCR and Conversion Services...** explains each
service in plain words: what it does, what it costs (nothing) and what stays
on your computer (everything). It also tells you whether the OCR engine is
installed.

**Next:** [Turn a document into an audiobook](04-document-to-audiobook.md).
