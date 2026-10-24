# Nemotron live, whisper.cpp, and the benchmark gate, 2026-10-23

The second real-speech run, after
[the 2026-10-22 record](dictation-real-speech-benchmark-2026-10-22.md). It
answers two questions that run left open, and adds a gate so the figures the
apps use keep being checked. Every number here is in
`dictation-live-and-whispercpp-2026-10-23.json` beside this page.

## In one minute

- **Nemotron live is as good as Nemotron by phrase, or better.** The first run
  fed Nemotron whole phrases; live dictation feeds it as you speak. At a normal
  microphone level the two scored the same on Google's FLEURS read speech (10.0
  and 10.1 percent of words wrong), and live was better on audiobooks no model
  was trained on (4.6 percent against 5.3). Live also used about a third less
  memory (1.0 GB against 1.5) and had the words written within 1.5 seconds of a
  pause for 95 phrases in 100.
- **Nemotron is sensitive to quiet audio.** The same 200 FLEURS recordings, many
  of them published very quietly, scored 13.7 percent as published and 10.1
  once brought to a normal level. That explains much of the gap between the
  first run's 13.7 and NVIDIA's own 7.9.
- **Live dictation can miss very quiet speech entirely.** At the published
  level, live dictation wrote nothing for 17 of the 200 FLEURS recordings: the
  voice detector that decides when you are speaking, shared by every engine in
  live dictation, never heard them start. They were at -50 to -68 dB below full
  scale -- far quieter than a microphone at a normal setting -- and most came
  straight after louder speech. A microphone whose level is set very low could
  do the same. It is a follow-up, not yet a fix.
- **whisper.cpp base, Locked Dictation's default, is accurate and light but
  slow.** 6.9 percent of words wrong on the held-out audiobooks and 9.2 on
  FLEURS, slightly better than the same Whisper base run by sherpa-onnx (7.4
  and 10.8), in well under half the memory (about 320 MB against 820). But it
  took 0.44 seconds of computing per second of speech on one thread -- twice
  sherpa-onnx's -- and its words came about 4.7 seconds after a phrase on one
  thread, 2.7 seconds on four, because it encodes a full 30-second window for
  every phrase, however short.
- **A benchmark gate now checks the advice.** Ten recordings of real people are
  committed with the code, and a weekly check runs every model the advice can
  recommend on them. Its first run found that the catalogue understates
  Whisper's cost on short phrases (below).

## How it was tested

Everything in [the first record's method](dictation-real-speech-benchmark-2026-10-22.md#how-it-was-tested)
holds: the same computer (Intel Core Ultra 7 265H, 16 cores, 64 GB, Windows 11),
the same harness (`scripts/dictbench.py`), the same seeded subsets (200 FLEURS
English recordings, 101 held-out audiobook recordings), the same scorer, which
ignores capitals and punctuation. What is new:

- **Live mode** (`dictbench --latency`). Each recording is played, at real
  speed, through the same recogniser dictation uses -- the voice detector, the
  pause, Nemotron's live stream that runs across phrases -- with two and a half
  seconds of silence between recordings. Words are scored for the whole session
  as one document as well as per recording, because a phrase that ends late can
  land in the next recording's window; the two agree to a tenth of a point
  except where noted.
- **Levelled audio.** A copy of the 200 FLEURS recordings with each one scaled
  to -26 dB below full scale, about where a microphone at a normal setting puts
  speech and where the audiobooks already are. Nothing else about the audio
  changed. It separates what the voice detector does from what the model does.
- **whisper.cpp** (`dictbench --engine whispercpp:base`, `scripts/bench_whispercpp.py`).
  QUILL's own pinned `whisper-cli` (whisper.cpp v1.9.1, from QUILL's assets-v1
  release) and SHA-256-pinned GGML model, run once per recording through the
  same command QUILL builds, with no initial prompt. Its memory is the program's
  own, measured while it runs. The app passes no thread count, so whisper.cpp
  uses up to four; it was measured at one (the budget's measure) and four.

## The results

### Nemotron: by phrase and live

| Audio | Mode | Words wrong | Words written | Text after a pause (95 in 100 phrases) | Peak memory |
|---|---|---|---|---|---|
| FLEURS, as published | Phrase | 13.7% | 100% | - | 1.5 GB |
| FLEURS, as published | Live | 26.8% | 84% | 3.7 s | 1.1 GB |
| FLEURS, levelled | Phrase | 10.1% | 100% | - | 1.5 GB |
| FLEURS, levelled | **Live** | **10.0%** | 100% | **1.5 s** | 1.1 GB |
| Held-out audiobooks | Phrase (2026-10-22) | 5.3% | - | - | 1.5 GB |
| Held-out audiobooks | **Live** | **4.6%** | 100% | **1.1 s** | 1.0 GB |

Full stops were found as well live as by phrase (F1 0.94 on levelled FLEURS
either way). On the audiobooks the live full-stop score was lower (0.73 against
0.76): a reader's sentence often runs over a pause, and live dictation closes
each phrase as a sentence.

### The quiet recordings

At the published level, 17 FLEURS recordings came back with no text in live
mode, and the same eight of the first 25 did so again on a second run, so it is
not chance. Instrumenting the recogniser showed the voice detector never
reported speech starting for them, so Nemotron was never given them. Most of
the FLEURS recordings are very quiet (about -62 dB below full scale, against
-26 for the audiobooks; the preparation was checked against the published files
and is faithful). The misses were the quiet ones that came straight after a loud
one: the detector is a neural network with memory, and after loud speech it did
not judge very quiet speech to be speech for half a minute or more. The same
recordings, levelled, were all heard.

In phrase mode there is no voice detector -- each recording is handed over
whole -- which is why the first run did not see this.

### whisper.cpp base against sherpa-onnx Whisper base

| Engine | Held-out audiobooks | FLEURS | Speed per thread | Words after a phrase | Peak memory |
|---|---|---|---|---|---|
| whisper.cpp base, 1 thread | 6.9% | 9.2% | 0.44 | 4.7 s | 322 MB |
| whisper.cpp base, 4 threads (the app's default) | 6.9% | - | 0.25 (all four) | 2.7 s | 328 MB |
| sherpa-onnx Whisper base, 1 thread (2026-10-22) | 7.4% | 10.8% | 0.22 | - | 821 MB |
| sherpa-onnx Whisper base.en, 1 thread (2026-10-22) | 5.9% | 7.4% | 0.13 | - | 820 MB |
| Parakeet Unified, 1 thread (2026-10-22) | 3.2% | 6.3% | 0.21 | - | 1.2 GB |

Loading the model and encoding a 30-second window costs whisper.cpp about 3.5
to 4.4 seconds per run on one thread whatever the phrase's length, which is
most of the time it takes on a dictated sentence.

### The benchmark gate's first run

| Model | Language | Cost against Moonshine tiny, this run | Catalogue | Words wrong, 10 recordings | Measured |
|---|---|---|---|---|---|
| Moonshine tiny | English | 1.3 | 1.0 | 8.6% | 6.5% |
| Moonshine base | English | 2.1 | 2.2 | 5.2% | 5.9% |
| Parakeet TDT v3 | English | 4.5 | 3.2 | 4.3% | 3.8% |
| Parakeet TDT v3 | Spanish | 4.0 | 3.2 | 9.2% | 5.9% |
| Parakeet Unified | English | 4.7 | 3.8 | 4.3% | 3.2% |
| Whisper tiny (built in) | Spanish | **5.0** | **2.6** | 20.0% | 28.8% |

The gate fails a model that runs at more than 1.5 times its catalogue cost.
Whisper failed. Measured separately, Whisper tiny's cost against Moonshine tiny
was 2.7 on FLEURS recordings averaging 8.6 seconds and 4.3 to 4.5 on the
committed recordings averaging 6 to 7 seconds: Whisper always encodes a 30-second
window, so the shorter the phrase, the more each second costs, while
Moonshine's cost follows the phrase's length. The catalogue's 2.6 came from the
longer FLEURS recordings; at the length of a dictated sentence it is nearer
4.5. Every model's cost rises somewhat on short phrases, Whisper's most.

**On GitHub's Windows runner** (the weekly workflow's first run, the same day),
the ratios came out differently: Whisper tiny for Spanish 3.8 (within its
tolerance), but Parakeet TDT v3 6.3 in English and 6.8 in Spanish, and Parakeet
Unified 7.0, against catalogue figures of 3.2 and 3.8 -- so both Parakeet
models failed. A model's cost against Moonshine tiny depends on the processor
as well as the phrase: the transducer models are relatively slower on that
runner's processor than on the measuring laptop. The apps scale every model from
Moonshine tiny timed on the person's own computer, so on such a processor they
can underestimate the Parakeet models by about half. That belongs with the
decision on re-measuring the cost factors (below); the gate's tolerance is
unchanged. Applying the higher of the two machines' figures was modelled and
rejected on 2026-10-24: it changed 72 of 432 recommendations, Parakeet ceasing
to be recommended on most 8 GB computers, on the strength of ten clips on a
shared cloud machine. Instead the weekly run is report-only (Jeff's decision):
it writes every figure to the job summary and as warnings, and fails only on
the advice's own budget rules, until the costs are re-measured on a real modest
Windows computer (the B-8 check).

## What changed

- `scripts/bench_whispercpp.py` and `dictbench --engine whispercpp:MODEL`.
- `scripts/dictation_speed_gate.py`, `tests/corpus/dictation` (ten recordings,
  LibriVox, public domain, held out from training; `SOURCE.md` says how they
  were chosen), `tests/unit/scripts/test_dictation_speed_gate.py`, and the
  weekly `.github/workflows/dictation-benchmark.yml`. The part that needs no
  models -- every recommendation keeps to its budget, on 72 kinds of computer,
  in both languages, for every priority -- runs with every pull request.
- No recommendation changed. The two decisions this run raises are below.

## What it leaves open

- **The quiet-speech misses.** Levelling the audio before the voice detector,
  or lowering its threshold for quiet input, would very likely fix them; either
  is a change to every engine's live path and needs its own testing with real
  microphones. Until then the guides say plainly that a microphone set very low
  can make dictation miss speech.
- **Cost on short phrases.** The catalogue's cost factors were measured on
  recordings of about ten seconds. Re-measuring every model at the length of a
  dictated sentence would make the advice truer, and would change at least one
  recommendation (Whisper tiny would no longer be the quickest choice for
  Spanish where Parakeet TDT v3 fits). That is a decision, not a correction, so
  it waits for one.
- **whisper.cpp as Locked Dictation's default.** The data now exists. Against
  whisper.cpp base, Parakeet Unified makes half the mistakes in English, and
  sherpa-onnx's own Whisper base is twice as fast for a similar result; but
  whisper.cpp has the smallest memory footprint and the initial prompt Locked
  Dictation's profiles use. Whether to change the default is a decision for the
  dictation plan (section 39).
- Everything the first record left open (a real 4 GB computer with a screen
  reader running, native Spanish questions) still stands.
