# Dictation benchmark recordings

Ten short recordings of real people reading aloud, kept in the repository so the
dictation benchmark gate (`scripts/dictation_speed_gate.py`) has real speech to
run on wherever it runs: six in English (`en/`, 37.9 seconds) and four in
Spanish (`es/`, 29.2 seconds), each from a different book and a different
reader.

## Where they come from

Every recording is a sentence from a LibriVox audiobook: volunteers reading
public-domain books, released into the public domain. The words they read are
the book's text from Project Gutenberg, also public domain. `ATTRIBUTION.txt` in
each folder names the reader, the LibriVox project and the Gutenberg ebook for
every file.

They were chosen from the held-out sets of the 2026-10-22 real-speech benchmark
(`docs/qa/dictation-real-speech-benchmark-2026-10-22.md`): audiobooks catalogued
on LibriVox after every model's training cutoff, so no model was trained on
them. `speakers.tsv` records, for each file and each model family, whether that
recording is held out for it.

## How they were chosen

The shortest whole sentences of 4.5 to 8 seconds with at least seven words, at
most one per book, so that the set stays small (about 2 MB) and still has
several voices. Sentences with underscores or dashes in the book text were left
out, because the reader cannot say them.

## Format

16 kHz, mono, 16-bit PCM WAV, as dictation hears a microphone, with
`transcripts.txt` giving the file name, a tab, and what was said.

## What they are not

Ten recordings are a smoke test, not a benchmark: they catch a model that has
become much slower or much less accurate, not a small change. The figures QUILL
publishes come from the full sets in the benchmark record.
