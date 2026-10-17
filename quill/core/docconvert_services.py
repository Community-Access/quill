"""The "OCR and Conversion Services" page Import / Convert Document opens.

Plain Markdown, rendered into a tab by
:meth:`quill.ui.main_frame_docconvert.DocConvertMixin.show_ocr_services_overview`.
Moved out of that mixin (2026-10-16) when the page gained QUILL's own
document readers, so the mixin stays under the module-size cap. wx-free.
"""

from __future__ import annotations

__all__ = ["SERVICES_OVERVIEW_MARKDOWN"]

SERVICES_OVERVIEW_MARKDOWN = """# OCR and Document Conversion Services

QUILL's Import / Convert Document tool turns documents that are hard to read
— scanned PDFs, photos of pages, locked-down Office files — into editable
text. It always tries the **free, private, on-device** services first, and it
never uploads anything.

## QUILL's Own Document Readers — built in

- **What they do:** read the text that born-digital files already contain —
  Word (.docx), Excel (.xlsx), PowerPoint (.pptx), OpenDocument (.odt, .ods,
  .odp), HTML, EPUB, CSV, and PDFs that carry a text layer — and open it as
  clean, editable Markdown. Headings, lists and tables come through; each
  sheet and each slide starts with its own heading; speaker notes are kept.
- **MarkItDown:** where the optional MarkItDown converter can run, QUILL uses
  it first for Word, Excel, PowerPoint, HTML, EPUB and CSV. Where it cannot,
  QUILL's own reader does the job and says so. You never need it.
- **Older formats:** .doc, .xls and .ppt (Office 97-2003) are read through
  LibreOffice when it is installed. Without it, QUILL tells you how to save
  the file in the newer format.
- **Best for:** files that were *made* on a computer.
- **Local or cloud?** Local. Nothing is uploaded. No account, no API key.
- **Cost:** free, always.
- **Limits:** they are not OCR — a scanned or photographed page comes back
  empty. When that happens QUILL offers the next service automatically.

## Local OCR Engine (Tesseract) — free download, runs on your computer

- **What it does:** real optical character recognition for scanned PDFs,
  photos, and images, running entirely on your machine (CPU-only — no
  special hardware).
- **Best for:** scanned letters, handouts, forms, and photographed pages.
- **Local or cloud?** Local. Your document never leaves this computer.
- **Cost:** free. The engine is a one-time download of about 48 MB.
- **Setup:** Tools > OCR and Document Conversion > Install Local OCR Engine.
  QUILL downloads the official installer, verifies it byte-for-byte, and
  opens it for you to complete. If Tesseract is already installed on this
  computer, QUILL finds and uses it — no download needed.
- **Honesty note:** on-device OCR is very good on clean scans and weaker on
  complex tables, handwriting, and poor photocopies. QUILL tells you when a
  result's confidence is low so you know to review it.

## Windows OCR — already on your computer

- **What it does:** the same job as Tesseract, by the OCR engine built into
  Windows 10 and 11. QUILL uses it when Tesseract is not installed, so a
  scanned PDF can be read with no download at all.
- **Local or cloud?** Local. Nothing is uploaded.
- **Cost:** free. It reads the languages you have in Windows Settings.
- **Honesty note:** Windows OCR does not report how confident it is, so QUILL
  cannot flag weak lines. Check the text yourself.

## Datalab Chandra OCR Service — cloud, optional, consent-gated

- **What it does:** the accuracy escalation for the hardest documents —
  complex tables, forms, handwriting, math, dense multi-column layouts, and
  poor scans. Returns clean Markdown (or HTML/JSON) with strong layout
  understanding.
- **Best for:** documents the free local tiers could not rescue well. QUILL
  offers it only after local OCR comes back weak — never as the first stop.
- **Local or cloud?** Cloud. Converting a document sends the file to
  Datalab. QUILL asks for your explicit consent before every single upload,
  and warns again when a filename suggests sensitive content. Datalab states
  that results are deleted from its servers about an hour after processing;
  QUILL retrieves promptly and keeps the result only in the opened document.
- **Cost:** paid, per page, on your own Datalab account (bring your own API
  key; new accounts include a monthly free allowance). QUILL never sees your
  billing — check Datalab's pricing page for current rates.
- **Setup:** AI Hub > Services — enable the service, paste your API key
  (stored in the Windows credential vault, never in settings files), choose
  a default mode, and press Test Connection.

## The one rule

Free first, local first, and nothing is ever uploaded without asking you.
The cloud tier exists for the documents that genuinely need it — and it
always asks first.
"""
