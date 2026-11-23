# Scribe live-run test documents

These are the documents the Scribe for Documents live regression run sends
(`python -m quill.tools.scribe_live_run`, see `docs/qa/scribe-live-regression.md`).

**We made every one of them.** The text is written for these files (the
Riverbend Community Tool Library, its people and its numbers are invented),
the pictures are drawn by `build_scribe_live_sources.py`, and the files are
dedicated to the public domain (CC0 1.0). Nothing here comes from Pneuma's
corpus or from Scribe: Pneuma's files and everything Scribe returns are kept
outside the repository.

Remake them with:

    python tests/corpus/scribe_live/build_scribe_live_sources.py

The DOC, ODT, XLS, ODS, PPT and ODP files are our own DOCX, XLSX and PPTX
saved by Microsoft Office over COM; the script skips them, and says so, on a
computer without Office.

One file for each of the 23 input types Scribe takes, plus the hard cases:
a long document (`q24`), tables with merged cells and two header rows
(`q25`), pictures with and without alt text (`q01`), Spanish (`q26`),
mathematics (`q27`), a password-protected PDF (`q28`, its test password is
in `quill/tools/scribe_live/sources.py`), a web page QUILL refuses before
uploading (`q29`) and a `.pdf` that is not a PDF, which Scribe should refuse
(`q30`). The table of them, with what each is for and how many pages it
should cost, is `OUR_SOURCES` in `quill/tools/scribe_live/sources.py`.
