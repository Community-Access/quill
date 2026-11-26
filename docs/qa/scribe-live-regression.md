# Scribe for Documents: the one-command check and the live regression run

## The one command

From the repository root:

    python -m quill.tools.scribe_check

Or double-click `scripts\scribe-check.bat`, which runs the same thing and keeps the window open.

It checks Scribe for Documents in every QUILL app, offline: no network, no sign-in, no credit. The first line it says is the result ("Scribe check passed, offline with Pneuma's corpus: all 305 tests passed, 5 skipped."), then the result for each app and each format, then any failure by name.

- **Offline (the default):** our own fixtures and the fake Scribe server (every app's entry point, the F1 to F8 shapes, the sentences), and, when Pneuma's corpus is on this computer at `D:\scribe-corpus\corpus\scribe-test-corpus-2026-11`, its replays and the opens-and-reads table. About 3 minutes.
- **`--live quick` or `--live full`:** a live run first, on Jeff's own Scribe account (below), then the same suite on the files it collected. Uses credit, and asks first.
- **`--replay <run folder>`:** the same suite on an earlier run's files. No network.

## What it tests, and what it does not

It tests QUILL, not Scribe (`scribe-test-plan.md`). Scribe is assumed to convert documents and send them back. The check proves that QUILL:

1. sends each document with the settings asked for, and refuses what Scribe would refuse before uploading;
2. collects every file that comes back, whole, once, with our name, the right extension and folder;
3. can use each file in every app that receives it (the opens-and-reads table below);
4. says each thing once;
5. copes with whatever shape comes back.

It never grades the conversion: not OCR accuracy, braille translation, voices, picture descriptions or epubcheck.

### The opens-and-reads table

`tests/unit/core/scribe/test_scribe_opens_and_reads.py` holds one table: each format, the QUILL products that receive it, and what "reads" means there. Every file of that format in the corpus or run folder goes through every receiver.

| Format | Received by | Reads means |
| --- | --- | --- |
| Accessible HTML | QUILL, QUILL Lite, Beacon | text present, every heading kept; Beacon finds the headings |
| Offline web page | the browser from Next Steps, Beacon | Next Steps can open it, no picture missing (or a zip with a page inside) |
| Word | QUILL, QUILL Lite, Beacon | text present, headings arrive as headings |
| Tagged PDF | QUILL, QUILL Lite | text present (skipped without the PDF extraction pack) |
| EPUB | QUILL | text and chapters |
| MOBI | kept for a Kindle | it is a MOBI book |
| BRF | QUILL's braille view, QUILL Lite | opens at the file's cell width, every form feed a page, every byte kept |
| MP3 | Media Player, Studio | has its length |
| DAISY | Media Player, Studio | unpacks into its own folder, opens from `dtb.ncx`, chapters with their audio |

Each case records its app and format, which is how the summary says pass and fail per app and format.

### Adding a test to the suite

Mark the module with `pytestmark = corpus.needs_corpus` (from `tests/unit/core/scribe/corpus.py`). That marks it `scribe_corpus` and skips it without a corpus; the check runs every test so marked, wherever it lives, with no list to update. Record `scribe_app` and `scribe_format` with `record_property` to have it counted under the right app and format.

## The live regression run

Sign in first: in QUILL, Tools, Scribe for Documents, Sign In. The run uses that stored sign-in and never reads, prints or keeps a token or a password. It never runs in GitHub's checks.

Then:

    python -m quill.tools.scribe_check --live quick

That prints the plan, asks you to type yes, sends the documents, collects everything, deletes the test documents from the account, runs the suite on the files and compares them with the previous run. The same run is also `python -m quill.tools.scribe_live_run --profile quick`, which has more options:

- `--dry-run` prints the plan and sends nothing; add `--list` for every upload.
- `--yes` starts without asking; `--cap N` sends at most N conversions (whole uploads, in plan order).
- `--out DIR` is the runs folder (default `D:\scribe-corpus\runs`); it must be outside the repository.
- `--keep-in-account` leaves the test documents in the account.
- `--resume <run folder>` continues a run that stopped, without uploading anything again.
- `--clean-up <run folder>` deletes a run's documents from the account, if that step failed.
- `--compare-only <run folder>` and `--replay-only <run folder>` redo those steps with no network.

### What it sends

- **Sources:** our own 30 documents in `tests/corpus/scribe_live/` (one for each of the 23 input types Scribe takes, plus a long report, tables, pictures with and without alt text, Spanish, mathematics, a password-protected PDF, a web page QUILL refuses before uploading, and a `.pdf` that is not a PDF), and Pneuma's four sources from their corpus folder when it is on this computer. Pneuma's files are read there and never copied into the repository.
- **Settings:** every upload sends the full set, starting from the account defaults Pneuma recorded and with Scribe's own email off. A setting is varied only against the formats it can change: large print against Word and PDF; braille table, cells, lines and page breaks against BRF; voice and speed against MP3 and DAISY; math, picture descriptions and language against everything.
- **Quick:** Pneuma's four in all nine formats, their large-print and math variants under their names, and eight hard cases: 13 uploads and 52 conversions, about 53 pages.
- **Full:** every source in every format, every math and picture-description combination, and the braille and voice grids: 581 uploads and 2,092 conversions, about 1,433 pages, and at least five and a half hours at Scribe's pace (audio takes longer).

### What it costs

Before anything is sent the plan says the cost both ways, because it is not certain how the company credit is counted: one per uploaded document, or one per format made. It also says the pages the uploads come to (Scribe charges pages once per upload; a second format of the same upload costs no more). After the run it says what was used: documents uploaded, files collected, and the account's pages left before and after.

### Where the files go

`D:\scribe-corpus\runs\<YYYY-MM-DD-HHMM>\`, in the same layout as Pneuma's corpus, so the replay tests read it unchanged:

- `html/`, `offline-html/`, `docx/`, `pdf/`, `epub/`, `mobi/`, `brf/`, `mp3/`, `daisy/` and `sources/`;
- `README.md`: what was sent and with which settings;
- `validation.json`: the facts about each file;
- `run.json`: the plan, each upload's outcome, the credit used and which documents were deleted;
- `comparison.md`: the comparison with the previous run;
- `replay.xml`: the suite's results.

A variant's files carry its settings in their names: `-large-print`, `-math-on`, `-no-descriptions`, `-lang-es`, `-brf-en-ueb-g2-32x20`, `-female-2x`. Nothing from a run is ever committed.

### Reading the comparison

The run is compared with the newest earlier run in the runs folder, or with Pneuma's corpus the first time. The comparison looks only at what could break collecting or using the files:

**Could break** (the run fails on any):
- a planned file that never arrived, or a format missing since last time;
- a different kind of file: a zip that became a single HTML file (as the offline page did once, F1), or the reverse;
- a file QUILL opened last time and cannot open now;
- structure QUILL relies on that is gone: headings in Word or HTML, DAISY's `dtb.ncx` or chapters, BRF form feeds, a different BRF cell width.

**For information only:**
- sizes that changed by more than a quarter;
- language tags;
- pictures embedded or referenced;
- page, chapter and table counts;
- new files.

Write anything that looks like a Scribe quality problem down for Pneuma (`scribe-test-plan.md` section 6) rather than working around it.

### Live protocol observation: time remaining is in milliseconds

On 2026-11-24, a real MP3 conversion produced `estimated_time_remaining`
values in the tens and hundreds of thousands while Scribe was converting.
QUILL interpreted those numbers as seconds, so it could display
"9,191 minutes left" for a normal conversion. Pneuma's official Rust and
Python client accepts the field as an integer but does not document its unit;
the live values and the resulting durations match milliseconds.

QUILL now divides that field by 1,000, uses the output's stage and progress
when the channel's 15-second fallback runs, and clears the estimate at
download or completion. The focused regression tests cover the conversion of
`30,000` milliseconds to 30 seconds, a quiet-channel refresh, and completed
jobs that must not retain an estimate.

Tell Pneuma this, without sending a document, token or document text:

> `/api/documents/{id}/outputs` returns an integer
> `estimated_time_remaining` field. The official Scribe client types it as an
> integer but does not say whether it is seconds or milliseconds. Live
> responses in the 2026-11-24 Windows run behaved as milliseconds and became
> implausibly large when interpreted as seconds. Please confirm the unit and
> document it in the API client and changelog.
