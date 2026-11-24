# FUX-11: try a sample before a long job

**Date:** 2026-11-24
**Feature:** FUX-11, "Rehearse the real outcome before a long job", from the family UX plan (read it with `git show b7c6a1a04^:complete2.md`). It is held to [family-interaction-contracts.md](family-interaction-contracts.md).
**Out of scope:** Earshot and the macOS apps.

The moment: "I don't want to record an hour before finding the microphone was wrong." Before a long job, the person can make a small sample with exactly the setup the job will use, hear or read it, and get an estimate measured on this computer. The sample is part of the normal task, not another wizard. It never replaces the real result, never changes a setting, and never writes into the job's output folder. It says what it covered and that it does not prove the rest. When a setting changes afterwards, the earlier result is labelled out of date.

## 1. The shared rule

`quill/core/rehearsal.py` (wx-free, strict-typed) holds the honesty that every app's sample shares, so each says the same things in the same words:

- `fingerprint(settings)` digests every setting that shapes the result. A `SampleResult` is current only while the fingerprint of the settings chosen now matches the one it was made with.
- `SampleResult.estimate()` scales what the sample took and made to the whole job, linearly, and refuses to guess from an empty sample or a job of unknown length.
- `estimate_sentence` says what the sample took, then what the whole job should take, play for and weigh "at that pace on this computer", and ends "This is an estimate." It names only the figures the sample measured.
- `limits_sentence` says what the sample checked "only, with your current settings", and that a later part can still fail or sound different.
- `stale_sentence` starts "Out of date:" and asks for another sample.

Each app makes its sample with its own pipeline, because the point is to use the job's own pipeline. The result is written to a read-only text field or the status bar where the app already shows results, and spoken once, briefly. Playback, where there is any, starts after the short spoken line, and the full detail stays in the text.

## 2. Inventory, app by app

"Try small" is what the person could already do to test the real outcome before this work. **Gap** marks a long job with no honest way to try it small, or no estimate.

### QUILL Studio, and Audiobook and Batch Speech in QUILL

Both run the same wizard (`quill/ui/audio_studio`) and the same runner (`batch_speech_runner._run`).

| Long job | Try small before this work | Estimate before this work | Verdict and change |
| --- | --- | --- | --- |
| Narrate documents, one chaptered file each, or a book | **Preview voice** plays a bundled clip or a fixed phrase with the engine and voice only; rate, gaps, sounder, loudness and dictionaries are not applied. **Dry run** writes the spoken text, not audio, as `<doc>.preview.txt` beside each document. **Audition** narrates the *whole* first document into the real output folder, where it can overwrite. | Only a word count ("N documents, about W words"). A size estimate was logged after synthesis had finished. | **Gap, fixed.** The summary page has **Try a Sample** (Alt+P). It speaks the first 80 words, about 30 seconds, of the first document through the run's own pipeline into a temporary folder, plays it, and writes the result to **Sample result**: what was made, what it took, and the whole run's time, length and size at that pace. Pressing again stops a sample being made, replays a current one, or makes a new one when a setting changed. |
| Book build (M4B or MP3) | Audition builds a one-chapter book in the real place | None | Covered by the same sample. The book's size is estimated at 96 kbps, the rate the assembler builds at, and the result says so. |
| Translated editions | None | Cost confirmation only, for cloud translation | Left: a sample would spend metered translation. The sample says that translated editions are not part of it. |
| Combine recordings into a book | Pre-recorded audio is already the outcome; the chapter list is reviewed before the build | None | No gap: nothing is synthesized. The button is not shown in this journey, nor for a dry run. |
| Record a Demonstration | **Test recording** records a few seconds with the real plan into a temporary folder and shows the verification; the Check reports devices and free space ("room for 30 minutes at these settings") | Yes | No gap. This is the model the rest of the family follows. |
| Broadcast live | A stream check before going live | Not applicable | No gap for FUX-11: a broadcast is live, not a long job with an outcome to preview. |

To make sure the sample proves the setup the run uses, the engine spec, the assembly options and the list of audio-shaping settings moved from the runner into `quill/ui/audio_studio/run_setup.py`, which both the runner and the sample call. The list of audio-shaping settings is the one the incremental-rebuild cache already fingerprinted, so a change that makes the run re-synthesize a document is the same change that makes a sample out of date. `synthesize_document_to_chaptered_file` gained `max_words`, which cuts the document's own sections at a word boundary with `first_words`; nothing else in the pipeline differs. A sample never adds a voice to the failure blacklist.

### QUILL (the editor)

| Long job | Try small before this work | Estimate | Verdict |
| --- | --- | --- | --- |
| Export to Speech Audio | Select a passage first: only the selection is exported | None | No gap that needs new work: the selection is the sample, made with the same Read Aloud settings. |
| Audiobook and Batch Speech | As Studio above | As Studio | Fixed with Studio. |
| Make a Listening Version (WordPress) | None: it records the whole page and uploads it straight away | "This can take a few minutes." | **Left.** A sample would be spoken by `listen_engines.speak` with no upload. The command sits in the WordPress work's files, which have their own plan (`docs/design/wordpress.md`); it is listed there as the follow-up. |
| File > Export to DAISY | Text-only DAISY is quick | Not needed | No gap. |
| Scribe conversions (audio DAISY, MP3, BRF) | **Play Sample** plays the chosen voice only | Pages: "This uses about X of your N pages" | **Left.** A content sample would spend Scribe pages on Scribe's server; the pages estimate is the honest figure Scribe can give before it starts. |

### Quill Converter and QUILL Transcribe

| Long job | Try small before this work | Estimate before this work | Verdict |
| --- | --- | --- | --- |
| Converter: Convert Now (Ctrl+Enter) | **Preview with Your Settings** (Ctrl+P) encodes 15 seconds with the real command and plays it | None before starting; "about N minutes left" only while the batch runs | **Gap**, fixed in the Converter and Transcribe pull request: the preview also measures its own encode and says what the whole queue should take and make at that pace. |
| Converter: Join, Split by Chapters | The same 15-second preview of one file's sound | None | Covered by the preview's estimate where the settings apply; the join itself is a copy of what the preview checks. |
| Converter: Process with Auphonic | None | Credit hours left on the account | **Left:** a sample would upload and spend Auphonic credit. |
| Transcribe a Recording (Shift+F5, and QUILL Transcribe) | None | `estimate_sentence`: a static model of the chosen model's speed on this kind of computer | **Gap**, fixed in the Converter and Transcribe pull request: **Try the First Minute** transcribes the first minute with the chosen model, language and options, shows the words, and replaces the static estimate with one measured on this recording. |

### Quill Radio and QUILL Cast

| Long job | Try small before this work | Estimate before this work | Verdict |
| --- | --- | --- | --- |
| Radio: Record Now, Record Station, scheduled recordings | None. Record Station's shortest length is one minute, and the recorder rounds anything shorter up to a minute | None: the bit rate is chosen with no size per hour | **Gap**, fixed in the Radio pull request: Recording Settings says what an hour weighs at the chosen quality where the format fixes it, and a short test recording with the same station and settings, into a temporary folder, says what it actually measured. |
| Radio: Download, Download Book | None | Counted only as it runs | Left: a download's size is the source's, not a setting's, so there is nothing to rehearse. |
| Cast: Download Episode, Download All Episodes | None | None; the feed seldom gives sizes | Left: a download has no settings to rehearse. A free-space check before Download All needs enclosure sizes that episodes do not store. |

### Quill Beacon, Media Player, Inkwell, Weather, QUILL Lite, Social

| App | Long jobs found | Verdict |
| --- | --- | --- |
| Beacon | Import (Ctrl+I) and Sync Now (F9) | Left. A "would import N, skip M duplicates" preview fits Import, but Beacon is not released and `app.py` is over its size budget. Sync already takes a snapshot first and can be rolled back from Sync History. |
| Media Player | Listen to a Document with Scribe | As Scribe in QUILL: left. |
| Inkwell | Dictate Anywhere is live input, not a long job | No gap. |
| Weather | None | No gap. |
| QUILL Lite | Import or Convert Document (OCR); Scribe conversions; Make a Listening Version | OCR runs in the background and can be closed; Scribe and Make a Listening Version are left for the reasons above. |
| Social | Scheduled posts are the person's own work, not a job with an outcome to preview | No gap. |

## 3. Acceptance, from the proposal

- **A sample does not replace the full result or alter the source.** Samples are made in temporary folders, removed when the window closes, and never written beside the documents or into the output folder. No setting changes.
- **Devices, formats and settings match the eventual job.** Studio's sample uses `run_setup`, which the runner itself uses. The Converter preview uses the real conversion command. Transcribe's first minute uses the same job the queue would run. Radio's test records with the station, format, quality and filters the recording would use.
- **Sample limits are explicit.** Every result says what it covered "only", and that the rest is not proved.
- **Changed setup is labelled stale.** Every kept result carries the fingerprint of its settings and starts "Out of date:" when they no longer match.
- **A nonvisual inspection path.** Every result is text in a read-only field or the status bar, and is reachable after the sound has finished.

## 4. Left for later

- Make a Listening Version: a sample spoken with `listen_engines.speak` and played without uploading. Listed in `docs/design/wordpress.md`.
- Beacon Import: a dry run that counts what would be imported and skipped, once Beacon's `app.py` has been split.
- Scribe and Auphonic: both spend a metered allowance on someone else's server, so a sample is not free. Their existing estimates (pages, credit hours) stay the honest figure.
- To be checked by hand with a screen reader: Studio's Try a Sample with Kokoro and with SAPI 5, in QUILL and in Studio; that the spoken "Sample ready" does not talk over the start of the sample on a slow computer; and the Out of date label after going Back and changing the voice.
