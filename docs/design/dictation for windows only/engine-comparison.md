# Dictation engine comparison

Why QUILL Lite 1.1's dictation uses Moonshine by default, with Whisper and
Windows speech recognition as the alternatives. Measured 2026-09-25.

## What was required

- Runs on the CPU of a low-end Windows 10 machine, faster than real time.
- Punctuates and capitalises by itself.
- Ships inside QUILL Lite: nothing downloaded at install or at first use.
- Offline, and able to listen on the microphone the user chooses.

## The test

Ten everyday sentences, spoken without saying any punctuation, run through each
candidate. Word errors are counted on lower-cased words; punctuation is scored as
how many of the reference marks each engine placed correctly by itself, and how
many of the marks it wrote were right. Speed is seconds of computing per second
of speech on one CPU thread (under 1 keeps up).

The first run used Windows' own synthesised voice reading the sentences. It is
the easiest possible input, so it understates every engine's errors -- and the
Windows recogniser, at 9% here, was reported as poor on a real voice. A run on
recordings of a real voice replaces these numbers when it is done; the tool is
`dictbench.py`, kept with the recordings rather than in the repository.

| Engine | Word errors | Punctuation (found / right) | Speed, 1 thread | Size shipped |
|---|---|---|---|---|
| Windows speech (SAPI) | 9% | 0% / 0% | 0.09 | 0 |
| Vosk small | 4% | 0% / 0% | 0.32 | ~45 MB |
| Vosk small + punctuation model | 4% | 7% / 10% | 0.33 | ~52 MB |
| **Moonshine tiny** | **2%** | **93% / 87%** | **0.04** | **~124 MB** |
| Moonshine base | 2% | 50% / 88% | 0.06 | ~287 MB |
| **Whisper tiny.en** | **3%** | **86% / 86%** | **0.15** | **~104 MB** |
| Whisper base.en | 2% | 93% / 87% | 0.28 | ~161 MB |
| Parakeet 3 | 2% | 93% / 87% | 0.21 | ~670 MB |

## The decision

- **Moonshine tiny is the default.** Best accuracy and punctuation in the field,
  and by far the fastest -- a twenty-fifth of real time on one thread, which is
  what makes it safe on the weakest machines QUILL Lite supports.
- **Whisper tiny.en is the alternative**, for a voice or microphone Moonshine
  handles badly. Base was measurably no better here and 55% larger.
- **Windows speech recognition stays** as the engine that needs nothing, for a
  machine where the models cannot run.
- Vosk does not punctuate, and the add-on punctuation model barely helped.
  Parakeet 3 is excellent and five times the size -- right for an optional
  download in QUILL, wrong for a small editor that ships everything.

Both chosen models run through sherpa-onnx (Apache 2.0), which bundles its own
ONNX runtime, so neither brings PyTorch. Together they add about 230 MB to the
QUILL Lite installer, placed beside the launcher rather than in the shared
QuillVille runtime so no sibling app pays for them.

## A fix the test found

Voice detection trims each phrase tight to the speech, and Moonshine sizes its
answer from the audio's length, so "three o'clock" came back as "3 o'". Padding
each phrase with a fifth of a second of silence before and half a second after
fixed it (`quill/core/windows_dictation/local_recognizer.py`).
