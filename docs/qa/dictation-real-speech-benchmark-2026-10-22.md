# Dictation speech models tested on real speech, 2026-10-22

This is the record behind QUILL's dictation model advice: which models QUILL,
QUILL Lite and QUILL Transcribe recommend, which are being retired, and why.
Every number on the help pages, in the release notes and in the apps' own
recommendation comes from this run. Until this run, the advice rested on ten
recordings of a synthetic voice, which flattered every engine.

## In one minute

- **English:** NVIDIA Parakeet Unified 0.6B made the fewest mistakes of every
  model that keeps up on one processor thread: 3.2 percent of words wrong on
  audiobook recordings no model had ever been trained on, and 6.3 percent on
  Google's FLEURS read speech. It is now the model QUILL recommends for English
  on a computer with 8 GB of memory and four cores.
- **Spanish:** NVIDIA Parakeet TDT 0.6B v3 got 4.4 percent of words wrong on
  FLEURS Spanish and 7.3 percent on Spanish audiobooks. The built-in Whisper
  tiny got 30.5 and 27.0, about one word in four. Parakeet is now the
  recommendation for Spanish on an 8 GB computer.
- **Modest computers:** on 4 GB, or with little memory free, the built-in
  Moonshine (English) and Whisper (Spanish) are still recommended. They are
  the only models that fit beside a screen reader there.
- **Five English-only models are being retired:** Distil-Whisper small.en,
  Whisper small.en, Distil-Whisper medium.en, Whisper medium.en and
  Distil-Whisper large-v3. Parakeet Unified beat each of them on accuracy and
  speed, in the same memory or less. They keep working until the next feature
  release, and nobody's model is changed for them.
- **A bug found and fixed:** Moonshine base wrote nothing at all for any
  phrase longer than about eight and a half seconds. It now hears long phrases
  in pieces (PR #1683), and scores 5.9 percent on the audiobooks.

## How it was tested

**The recordings.** Real people, never a synthetic voice:

| Set | What it is | Recordings | Licence |
|---|---|---|---|
| LibriVox held-out, English | Public-domain audiobooks catalogued on LibriVox after every model's training cutoff, scored against the Project Gutenberg text. No model can have trained on them, so this is the fairest test. | 101 | Public domain |
| LibriVox held-out, Spanish | The same, in Spanish | 82 | Public domain |
| LibriSpeech test-clean | Read audiobook speech, clear recordings | 200 | CC BY 4.0 |
| LibriSpeech test-other | Read audiobook speech, harder voices and recordings | 200 | CC BY 4.0 |
| FLEURS English (US) | Google's read Wikipedia sentences, many speakers and accents | 200 | CC BY 4.0 |
| FLEURS Spanish | The same, in Spanish | 200 | CC BY 4.0 |

LibriSpeech and FLEURS are public, so some models may have trained on them;
those results are shown, but the decisions lean on the held-out audiobooks.

**The harness.** `scripts/dictbench.py`, run by `scripts/bench_machine_run.py`,
feeds each recording to a model the way dictation does: one phrase at a time,
on **one processor thread** (the speed budget is per thread, because the
screen reader needs the rest), on the processor only. Each model runs in its
own process, so its memory figure is its own. Word errors ignore capitals and
punctuation; for Spanish they also ignore accents.

**The measures.**

- **Words wrong:** the percentage of the reference's words the model got
  wrong (substituted, left out or added). Lower is better.
- **Speed per thread:** seconds of computing per second of speech on one
  thread. Dictation's budget is 0.25: a quarter of a core, leaving the rest for
  the screen reader. The apps compare a model's cost with the bundled Moonshine
  tiny's, measured on your own computer by the two-second check, so the
  advice scales to your machine.
- **Peak memory:** the most memory the model used on any set, because a model
  has to fit the worst minute, not the average one.

**The computer.** An Intel Core Ultra 7 265H laptop (16 cores, 64 GB),
Windows 11, Python 3.14.8, sherpa-onnx 1.13.8, ONNX Runtime 1.31.0. It is much
faster than the computers the advice is written for, which is why speed is
judged as a multiple of Moonshine tiny's rather than in raw seconds.

**The limits.** One computer, one day. Other work was running during some of
the sets, so the absolute speeds vary from set to set; the speed factors in the
catalogue come from the English FLEURS run, where eight models ran back to
back under the same conditions. Screen-reader lag, battery draw and a real
4 GB computer with NVDA or JAWS running were not measured here; that check
(B-8 in the dictation plan) still needs a person. Whisper medium and
large-v3-turbo were too slow to re-run and keep their earlier figures.

## The results

### English

Percent of words wrong (lower is better), speed per thread (0.25 is dictation's budget) and the most memory used.

| Model | Held-out audiobooks | FLEURS | LibriSpeech clean | LibriSpeech other | Speed per thread | Peak memory | Decision |
|---|---|---|---|---|---|---|---|
| NVIDIA Parakeet Unified 0.6B | 3.2% | 6.3% | 1.8% | 3.2% | 0.21 | 1.2 GB | **Recommended** on 8 GB with four cores |
| Whisper medium.en | 3.6% | - | - | - | 1.55 | 3.0 GB | Being retired |
| NVIDIA Parakeet TDT 0.6B v3 | 3.8% | 9.0% | 2.5% | 5.2% | 0.11 | 1.1 GB | Kept; recommended on 8 GB with two cores |
| Whisper small.en | 4.3% | 6.3% | 3.4% | 7.8% | 0.43 | 1.4 GB | Being retired |
| Distil-Whisper large-v3 | 4.5% | - | - | - | 0.82 | 2.0 GB | Being retired |
| Whisper small | 4.7% | 7.0% | 4.2% | 8.5% | 0.55 | 1.4 GB | Kept; many languages, needs two threads |
| NVIDIA Nemotron 3.5 Streaming 0.6B | 5.3% | 13.7% | 3.7% | 7.3% | 0.37 | 1.5 GB | Kept; streams words while you speak |
| Moonshine base | 5.9% | 15.1% | 4.8% | 10.7% | 0.05 | 378 MB | Kept; fixed for long phrases |
| Whisper base.en | 5.9% | 7.4% | 5.6% | 11.6% | 0.13 | 820 MB | Kept; light, good on varied voices |
| Distil-Whisper small.en | 5.9% | 7.6% | 4.6% | 9.2% | 0.22 | 1.0 GB | Being retired |
| Distil-Whisper medium.en | 6.3% | - | 4.2% | - | 0.47 | 1.6 GB | Being retired |
| Moonshine tiny (built in) | 6.5% | 13.2% | 5.0% | 13.3% | 0.06 | 584 MB | Kept; the default, and the pick on 4 GB |
| Whisper base | 7.4% | 10.8% | - | - | 0.22 | 821 MB | Kept; many languages |
| Whisper tiny (built in) | 8.3% | 11.7% | 6.7% | 13.9% | 0.07 | 521 MB | Kept; built in |

### Spanish

| Model | FLEURS Spanish | Held-out Spanish audiobooks | Speed per thread | Peak memory | Decision |
|---|---|---|---|---|---|
| NVIDIA Parakeet TDT 0.6B v3 | 4.4% | 7.3% | 0.12 | 1.1 GB | **Recommended** on 8 GB |
| Whisper small | 6.0% | 7.8% | 0.57 | 1.4 GB | Kept; needs two threads |
| NVIDIA Nemotron 3.5 Streaming 0.6B | 6.4% | 8.0% | 0.50 | 1.5 GB | Kept |
| Whisper base | 12.6% | 16.1% | 0.18 | 821 MB | Kept; lighter |
| Whisper tiny (built in) | 30.5% | 27.0% | 0.10 | 521 MB | Kept; built in, the pick on 4 GB |

The speed column is each model's middle value across the sets it ran; other
work was running during some sets, so these run a little slow. The speed
factors the apps use come from the English FLEURS run, where the models ran
back to back: against Moonshine tiny, Parakeet TDT v3 costs 3.2 times as much,
Parakeet Unified 3.8, Whisper base.en 4.3, Nemotron 5.8, Distil-Whisper small.en
7.9 and Whisper small.en 14.5.

## What changed in the apps

QUILL, QUILL Lite and QUILL Transcribe share one dictation engine and one
catalogue, so all three changed together.

- **The recommendation uses these numbers.** English is ranked by the held-out
  audiobooks, Spanish by the mean of its two sets, and only models measured in
  Spanish are offered for Spanish. Speed factors and memory peaks are the real
  ones. The recommendation now says its figures come from real recordings.
  - 4 GB, two cores: Moonshine tiny for English, Whisper tiny for Spanish.
  - 8 GB, two cores: Parakeet TDT v3 for English and Spanish once the
    two-second check shows the computer is quick enough (about 0.07 seconds a
    second or less for Moonshine tiny); a slower or busier two-core computer
    keeps the built-in models.
  - 8 GB or more, four cores: Parakeet Unified for English, Parakeet TDT v3 for
    Spanish.
  - "The quickest response" still names Moonshine tiny.
- **An 8 GB baseline, and free memory counts.** A computer with 8 GB may give
  dictation 1.6 GB beside the screen reader (it was 1 GB), and never more than
  is free when you ask, less half a gigabyte.
- **Tiers follow real speed.** Parakeet TDT v3, Parakeet Unified and Whisper
  base.en are now Lightweight: they keep up on a modest computer. Nemotron is
  Balanced.
- **Five models are being retired.** Each one's line in the model list starts
  "Being retired: use NVIDIA Parakeet Unified 0.6B instead." The first time
  dictation starts on one, QUILL says so once, in every QuillVille program
  together, with the measured reason, and says it keeps working until the next
  feature release. Nothing is switched and nothing is deleted. They are never
  recommended.
- **Moonshine base hears long phrases.** Its decoder failed on anything over
  about 8.5 seconds and wrote nothing; long phrases are now heard in pieces of
  8 seconds or less, cut at the quietest moment, and joined.

## What this run could not settle

- **Does Whisper write the opening "¿" and "¡" itself?** The scorer now counts
  them (PR #1684), but FLEURS and the audiobooks have almost no questions.
  Ten recordings from a native Spanish speaker, with questions and
  exclamations, would answer it.
- **A real modest computer with a screen reader running.** Speed, memory,
  screen-reader lag and battery on a 4 GB Windows 10 computer with NVDA or
  JAWS (B-8) still need a person.
- **Whisper medium and large-v3-turbo** were too slow to re-run here.

## The data

Every row above is in `dictation-real-speech-benchmark-2026-10-22.json` beside
this page: model, set, dataset, words wrong, speed, peak memory, punctuation
scores and the number of recordings. The harness is in `scripts/` and the datasets,
with their licences and checksums, are listed in `scripts/bench_datasets.json`.
The full engineering record is section 36 of the dictation plan
(`docs/design/2026-10-05-dictation-plan-and-status.md`).
