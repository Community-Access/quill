# Dictation in QUILL and QUILL Lite: plan, status and what is left

*Written 2026-10-05. This note replaces the working plan that lived in a
gitignored `dict.md` at the repository root from 2026-09-28 to 2026-10-05. It
keeps that plan's design history, records what was built, and holds everything
that could not be built yet, so nothing in it is lost when `dict.md` goes.*

Dictation is one feature in two editors. Everything below lives in shared code
(`quill/core/windows_dictation/`, `quill/ui/windows_dictation_*.py`,
`quill/ui/dictation_*_dialog.py`), so QUILL and QUILL Lite have the same
commands, keys, settings and windows. `tests/unit/ui/test_dictation_parity.py`
fails on any difference. QUILL's Locked Dictation (F9, Ctrl+F9) is a separate,
older engine that records first and transcribes afterwards; it is QUILL's own
and outside this note.

Code comments, tests and older documents cite the retired plan by section
("dict.md 2.4", "dict.md section 1"). Appendix A maps every one of those
numbers to where its content lives now.

Companion documents: `docs/design/dictation for windows only/engine-comparison.md`
(the 2026-09-25 engine measurements), `quill-lite-dictation-prd.md` and
`implementation.md` in the same folder.

## 1. The rule that decides everything: a modest computer

QUILL Lite is often used on the computer somebody was given, not the one they
would choose, with a screen reader running that must stay instantly
responsive.

**The baseline machine** (decided 2026-10-05, Jeff's answer to dict.md
question 4): Windows 10, 64-bit, 4 GB of memory, an older dual-core processor
with no graphics help, NVDA or JAWS running beside a browser or mail program,
possibly on battery.

**The budgets** every default must meet there:

| Budget | Limit | Why |
|---|---|---|
| Speed | 0.25 or less (seconds of computing per second of speech, one thread) | leaves three quarters of a core for the screen reader |
| Memory while dictating | 600 MB or less for dictation | a 4 GB machine already pages with a browser open |
| Screen-reader delay | no audible lag in speech or braille | the reader is the person's whole interface |
| Idle cost | nothing when dictation is off | no model loaded, no microphone open, no thread spinning |
| First word written | within 1.5 seconds of the pause | the pause is the Enter key; longer feels broken |

**The safeguards, all built:**

- **The two-second check** (`speed_check.py`, 2026-10-05): Speech Models times
  Moonshine tiny on this computer and says, for each optional model, whether
  it should keep up.
- **The keep-up watchdog** (`keep_up.KeepUpWatchdog`, wired into
  `recognizer_worker.py`): when audio waits four seconds or more, or two
  phrases in a row take more than one and a half times their length to
  recognise, a downloaded model gives way to Moonshine for the rest of the
  session and the person hears why, once. The saved choice is not changed.
  Built-in engines are not watched (they are the fast ones); OpenAI is not
  watched (its speed is the network's).
- **Nothing loaded when dictation is off** (`keep_up.IdleUnloader`): models
  load on the first start, stay loaded while dictation is in use, and are
  unloaded five minutes after the last session ends.

Measured: Moonshine tiny 0.04 to 0.05 and Whisper tiny.en 0.15 to 0.20; every
optional model except Moonshine base is over 0.25 on one thread (section 6).

## 2. What VS Code does, and what QUILL took

VS Code's dictation was studied from its public MIT-licensed source and its
documentation on 2026-10-05: `src/vs/workbench/contrib/codeEditor/browser/dictation/editorDictation.ts`,
`src/vs/workbench/contrib/chat/browser/speechToText/dictationSession.ts` and
`chatSpeechToTextService.ts`, `src/vs/workbench/contrib/speech/browser/speechService.ts`,
`src/vs/workbench/contrib/accessibility/browser/accessibilityConfiguration.ts`,
and code.visualstudio.com/docs/configure/accessibility/voice. Thanks to the VS
Code team: several of the best ideas below are theirs. No VS Code code was
copied; QUILL's version is written in its own code and words.

| VS Code behaviour | What QUILL does |
|---|---|
| **Hold mode.** The start key starts dictation; if the key is still held 500 ms later, letting go stops it. A quick press toggles. | Taken. `hold.py`, `windows_dictation_hold.py`. Hold Ctrl+F11 (whatever the key is bound to) for half a second and talk; let go to stop. A quick press still toggles. Key repeats while held are ignored. Setting **Hold the dictation key to talk**, off by default (owner, 2026-10-05; dict.md question 1 first answered on, then reversed before any release): one press starts, the next stops. |
| **Toggle on the same key.** Pressing the start key while dictating stops it. | Already QUILL's behaviour. |
| **Stop applies the final transcript.** | Taken. Stopping while a phrase is being heard now waits for it (`LiveMixin.finish`, the worker's `finish`), so letting go of the key never loses the last phrase. A timer stops anyway after four seconds. |
| **Interim text in grey, replaced by the final segment.** | Taken, accessibly. Provisional words never enter the document or the undo history; they show as "Hearing: ..." in the status bar's Dictation part and on a braille display, throttled to a few updates a second, and the final words replace them. Spoken only if the person chooses **Show it, and say new words quietly** (new words only, no more than every two seconds). GATE-13 holds: nothing the screen reader already says is repeated. |
| **Start and stop signals** (`voiceRecordingStarted`, `voiceRecordingStopped`). | Already QUILL's (tones and words, each switchable). |
| **Read-only refusal** (the start command is disabled in a read-only editor). | Already QUILL's: it refuses with a sentence and the microphone stays closed. |
| **Dictation into any text input** (chat, terminal, editor). | Already QUILL's (Find, Replace, the AI pad); the AI Conversation window's message box joined it (section 4). |
| **Cancel removes the session's text.** | Considered and not taken as is. For a screen-reader user, Escape removing a whole session of dictation is too destructive. QUILL's Escape throws away the phrase being heard and its preview; nothing written moves. "Scratch that" and Ctrl+Z take back written phrases one at a time. |
| **Keyword activation ("Hey Code") paused when the window loses focus.** | Already QUILL's wake phrase rule: it listens only while QUILL is the window in front. |
| **Speech timeout** (`accessibility.voice.speechTimeout`). | Already QUILL's **Stop dictation after silence**. |
| **Auto-synthesize: read the reply aloud when voice was used.** | Taken for the AI Conversation window (section 4), with the microphone muted while it is read. |
| **20-minute maximum session.** | Not taken: QUILL's silence timeout and microphone watchdog cover the same risk without cutting off somebody who is still talking. |
| **LLM cleanup of every transcript** (`dictation.experimental.llmCleanup`, default on, 4000-character cap, 5-second timeout). | Not taken (dict.md 5.3 D): every phrase would go to the internet and cost money. QUILL tidies only when asked (Tidy Dictated Text, section 5). |
| **Dictation instructions** (`~/.copilot/dictation.md`, `.github/dictation.md`) and a cleanup prompt that treats the transcript as data, never a request. | Taken: **My Dictation Instructions** (`dictation-instructions.md` beside My Words and Phrases), sent with Tidy Dictated Text as a marked part; the tidy instruction says the text is data and must not be answered. |
| **On-device Nemotron 3.5 ASR Streaming**, downloaded on first use. | Offered as an optional download since 2026-10-05 (section 6), never the default. Now run live (section 3). |
| **A cloud model option** (MAI, web only). | QUILL's equivalent is OpenAI with the person's own key (section 7): optional, off by default, with consent. |

## 3. Live streaming with Nemotron (dict.md 4.4)

Built 2026-10-05: `streaming.NemotronLive`, fed by `recognizer_worker.py`.

- While the voice detector hears speech, the audio goes to Nemotron as it
  arrives; its provisional words are posted to the controller's `on_partial`
  only when they change, and the controller decides what to show and say.
- At the pause the final words go through the normaliser and the command
  processor exactly as any engine's do, so a preview can never run a command.
- **One stream per session, not per phrase.** Measured on Nemotron with
  recorded speech (Windows' Zira voice, 16 kHz): given each phrase on its own,
  Nemotron left the end open ("Can you send me the report by Friday" with no
  mark). Kept running into the next phrase, it wrote the right mark at the
  start of what it heard next ("?  The meeting moved to Thursday"), with the
  question mark, full stop and exclamation mark right on all five test
  sentences. So each phrase is written at the pause, closed with a question
  mark when it opens like one ("Can you", "Where did") and a full stop
  otherwise (`preview.close_sentence`, deliberately narrow: "Do the dishes" and
  "When I get home" stay statements), and the mark Nemotron gives the next
  phrase corrects it in place (`LiveMixin._revise_mark`). A mark Nemotron
  confirms is final, so a next phrase opening with "where" or "and" does not
  undo it.
- **Only a little quiet is decoded.** After speech, 0.6 seconds of quiet is
  fed, then nothing until the next speech (with its 0.4-second lead-in).
  Measured: 0.6 seconds of quiet plus the lead-in keeps the punctuation; 1.2
  seconds made Nemotron start afresh, unpunctuated. A silent room costs
  nothing.
- **End to end** (real Silero voice detector, real worker and controller, 22.5
  seconds of recorded speech fed at live pace, 12-core test machine): the
  document read "Can you send me the report by Friday? The meeting moved to
  Thursday afternoon. Where did you put the keys? What a wonderful surprise! Is
  the meeting still at three o'clock?", ten previews were shown, and the worker
  kept up with no backlog.
- The question that ended with a full stop (dict.md 4.5) is fixed.

## 4. Talk to the AI, and dictation profiles (dict.md 3.2 and 6)

Built 2026-10-05 in `hosted_ai_chat.py` (`_talk_to_it`) and the shared mixins.

- Ctrl+F11 in the AI Conversation window's message box dictates there.
- The box carries the **Talking to AI** profile, which switches on by itself
  while it is dictation's target: its own pause (Long by default), filler
  removal (on), automatic punctuation (on), and no "just write what I say".
- **Send after the pause** is the default (dict.md question 2); **When I press
  Enter** is the alternative.
- The reply is read aloud, as it always was, and the microphone is muted while
  it is read, for an estimate of its length at a brisk screen-reader rate plus
  a second (`windows_dictation_hold.reply_seconds`). Escape listens at once.
- Text said or typed while waiting for a reply stays in the box.

## 5. Teaching dictation your words (dict.md 5)

- **A. Corrections in the words file**: shipped 2026-09-28 (My Words and
  Phrases).
- **B. Word biasing.** Built where an engine supports it: OpenAI dictation
  sends your My Words vocabulary as `keywords` (live check: "Doctor Okonkwo"
  and "Kubernetes", which every local model misheard as "Akonko" and "Cuba
  Ernets", came back right). For the local transducers it is **not buildable
  today**, measured 2026-10-05 with sherpa-onnx 1.13.8: Nemotron's streaming
  NeMo decoder supports greedy search only ("Unsupported decoding method:
  modified_beam_search"), and Parakeet's offline NeMo hotwords path
  upper-cases the words for icefall's upper-case BPE, so biasing either did
  nothing or wrote capital-letter garbage ("DOCO OKONKWOT"). Revisit when
  sherpa-onnx encodes hotwords for mixed-case SentencePiece vocabularies.
- **C. Clean up my dictation**: built as **Tidy Dictated Text** (Ctrl+F3,
  2026-09-29) plus **My Dictation Instructions** (2026-10-05). One request when
  asked, on a ChatGPT plan or the person's own key, nothing replaced until
  Replace My Selection. The free hosted AI is not used for it (an allowance
  would be gone in a morning of dictation).
- **D. Clean up every phrase automatically**: not built, by decision (cost,
  privacy, latency on modest connections).

## 6. Optional speech models (dict.md 4.5)

Built 2026-10-05 and unchanged here except that Nemotron now runs live.
Moonshine tiny and Whisper tiny stay bundled in every installer and portable
copy and stay the default; nothing downloads unless the person chooses it.

**The catalogue** (`model_catalog.py`, every file pinned to a Hugging Face
commit and SHA-256): Nemotron 3.5 ASR Streaming 0.6B (682 MB, en, es, NVIDIA
OpenMDW-1.1), Parakeet Unified 0.6B (663 MB, en), Parakeet TDT 0.6B v3 (670
MB, en, es and 23 more, CC BY 4.0), Whisper small, base, base.en, small.en,
medium.en, medium, large-v3-turbo, large-v3, Distil-Whisper small.en, medium.en
and large-v3 (MIT), and Moonshine base (141 MB, en). Not offered: Moonshine
"small" (no sherpa-onnx build), non-English Moonshine (non-commercial
licence), Nemotron at full precision (2.6 GB), the onnx-community 4-bit
Nemotron (onnxruntime-genai only), large-v2 and distil-large-v2 (superseded).

**Licences.** The person's own computer downloads each model from the
publisher at their request after a question that names the licence: use, not
redistribution. If QUILL ever mirrors or bundles one, its licence and notices
must travel with it.

**The runtime is sherpa-onnx for everything.** Whisper through sherpa-onnx int8
ran four to seven times faster per thread than whisper.cpp v1.9.1 q5 on the
same recordings; whisper.cpp loaded faster and used about half the memory, but
would have been a second native runtime and a process per phrase.
parakeet.cpp was not adopted (no Python binding).

**What dictbench measured** (ten recordings, one thread, 2026-10-05):

| Model | Word errors | Computing per second of speech | Text after the pause | Most memory | Load |
|---|---|---|---|---|---|
| Moonshine tiny (built in) | 3.4% | 0.05 | 0.2 s | 210 MB | 2.2 s |
| Whisper tiny.en (built in) | 3.4% | 0.20 | 0.7 s | 303 MB | 1.3 s |
| Moonshine base | 3.4% | 0.08 | 0.3 s | 365 MB | 2.0 s |
| Whisper base | 5.1% | 0.37 | 1.4 s | 417 MB | 1.5 s |
| Parakeet Unified 0.6B | 3.4% | 0.33 | 1.2 s | 844 MB | 5.2 s |
| Parakeet TDT 0.6B v3 | 4.2% | 0.34 | 1.2 s | 805 MB | 5.1 s |
| Nemotron 3.5 ASR Streaming | 2.5% | 0.40 | 1.5 s | about 790 MB | 3.2 s |
| Whisper small | 5.1% | 1.29 | 4.7 s | 859 MB | 4.4 s |
| Whisper medium | 3.4% | 3.04 | 11.2 s | 2.1 GB | 9.6 s |
| Whisper large-v3-turbo | 3.4% | 4.20 | 15.4 s | 1.4 GB | 5.3 s |

**Storage.** Installed copies: `%LOCALAPPDATA%\QuillVille\Dictation\models`,
shared by both editors. Portable copies: `<portable folder>\data\dictation\models`.
`QUILL_DICTATION_DOWNLOADS` overrides both, for tests.

**Never a silent switch.** A downloaded model that is missing or will not load
gives way to the built-in engine with one sentence; the keep-up watchdog does
the same and says so.

## 7. OpenAI dictation, own key only

Built 2026-10-05. The rules are the owner's.

- **Only with the person's own OpenAI key**, saved in Use My Own AI Key (the
  same store QUILL's AI help uses). QUILL's free hosted AI never carries audio.
  The engine is listed only where a key is saved; Safe Mode refuses it.
- **Off by default, with consent.** Choosing OpenAI in Dictation Settings shows
  a plain question (`openai_models.CONSENT_TEXT`): what is sent, to whom, who
  pays, that QUILL keeps no copy, OpenAI's own retention, and that the
  built-in engines send nothing. No is the default. The agreement can be taken
  back in More Dictation Settings. Local dictation stays the default.
- **The model list is read live** from `/v1/models` when More Dictation
  Settings opens, filtered to transcription models (`transcribe` in the id, or
  a Whisper id; speaker-labelling "diarize" models left out) and without the
  models OpenAI is retiring. OpenAI's API does not mark deprecation, so the
  retiring list is copied from OpenAI's deprecations page, read 2026-10-05:
  whisper-1, gpt-4o-transcribe, gpt-4o-mini-transcribe and
  gpt-4o-transcribe-diarize shut down on 2027-02-26, replaced by
  gpt-live-transcribe and gpt-transcribe. It is a list of what to leave out,
  never of what to offer. Newest first; the newest is pre-selected when nothing
  was chosen.
- **If the chosen model disappears**, More Dictation Settings says so once and
  leaves the choice empty until the person picks again; dictation that meets a
  missing model stops with a sentence. It never moves to another model.
- **The newest API.** OpenAI's speech-to-text guide (read 2026-10-05)
  recommends Realtime transcription for live microphone audio, with
  `gpt-live-transcribe`, turn detection off (QUILL's own voice detector finds
  the pause, and only speech is sent). That is the live path: one WebSocket per
  session (`wss://api.openai.com/v1/realtime?intent=transcription`, through the
  `websockets` package already in the shared runtime), audio appended while
  you speak (the live preview comes from its deltas), committed at the pause.
  Other models use `/v1/audio/transcriptions` with `stream=true`, one short
  WAV per phrase. Both send the dictation language and your words as
  `keywords`.
- **The key** travels only in the Authorization header over verified TLS, is
  never logged or put in a sentence, and `quill.stability.redaction` scrubs
  `sk-` keys from any bundle. Three reviewed entries in
  `quill/tools/network_egress_entries.py`; the privacy statement
  (`docs/legal/PRIVACY.md`) says what is sent.

**Live check, 2026-10-05** (the owner's key read at run time into an
environment variable for a scratchpad script only; never written anywhere):
the account's list offered exactly `gpt-live-transcribe` and `gpt-transcribe`.
Both paths, through the real voice detector, worker and controller, wrote
"Can you send me the report by Friday? The meeting moved to Thursday
afternoon. Please call Dr. Okonkwo about the Kubernetes cluster." and the
exclamation (gpt-transcribe wrote "!", gpt-live-transcribe "."); the live path
showed 18 previews while speaking and answered each phrase about 0.6 seconds
after the pause.

## 8. The rest of the reliability and magic work

| dict.md item | Status |
|---|---|
| 2.1 Hold-to-talk | Built 2026-10-05 (section 2). Off by default (owner, 2026-10-05). |
| 2.2 Escape cancels the phrase | Shipped 2026-09-28; now also throws away the preview, and listens at once while an AI reply is read. |
| 2.3 Microphone watchdog | Shipped 2026-09-28. |
| 2.4 Words go where you started | Built 2026-10-05 (`LiveMixin`, `EditorDocument.anchor`): the caret is remembered when speech starts; if it moves, or the focus goes to another window, before the phrase is written, the words still go there, the person's caret is put back (moved along), and they hear "Written where you started" (with the document's name when it was another window). If that spot changed, the words go at the cursor and they are told. |
| 2.5 One Ctrl+Z per phrase | Shipped. A late mark correction (section 3) is its own undo step. |
| 2.7 Self-healing engine | Shipped. |
| 2.8 One session at a time | Shipped. |
| 3.1 Dictate into any text field | Shipped; the AI Conversation window joined it. |
| 3.2 Talk to the AI | Built (section 4). |
| 3.3 Recent phrases | Shipped. |
| 4.4 Live preview | Built (section 3), with OpenAI's live model too. |
| 4.5 Optional models | Built (section 6). |
| 5.3 A, B, C, D | Section 5. |
| 6 "Correct that" | Built: "correct that" reads up to three other guesses where the engine offers them, numbered, and "choose one" to "choose three" swaps the last phrase. Windows speech recognition offers them (SAPI `Alternates`); Moonshine, Whisper, the downloaded models and OpenAI give one answer, and the command says so. |
| 6 Profiles | Built: "Writing" (Dictation Settings) and "Talking to AI" (More Dictation Settings), switching by itself in the AI window. |
| Section 1 safeguards | Built (section 1). |
| Transcribing a file (owner, 2026-10-05) | Built (section 12): Transcribe a Recording, Shift+F5, in both editors. |
| 8 Questions | Answered 2026-10-05: hold-to-talk off by default (first answered on, reversed the same day); send after the pause; the AI pieces ship in QUILL Lite 1.2 and QUILL 1.0; the baseline machine as in section 1; speech models as optional downloads (section 6). |

**Parity gaps closed on 2026-10-05.** QUILL's menu row was "Start or Stop
Dictation" with no check mark, where QUILL Lite's is the checkable "Dictation
On": QUILL now has "Dictation On", checked while dictation writes. QUILL had no
status-bar trace of dictation's state; it now shows the state, and the live
preview, quietly. The 24 `windows_dictation_*` settings were declared twice;
they are now one `DictationSettings` dataclass both editors' `Settings`
inherit. The live dictation commands had no F1 topics in `topics.json`; they
have them now. The parity test fails on any new difference.

## 9. Spanish (dict.md 9)

**Built 2026-10-04** (the cheaper first step: Spanish text, English commands),
in both editors: the **Dictation language** setting (Alt+G); Whisper tiny
multilingual bundled (about 104 MB; tiny, not base, because base.en already
measured 0.28 against the 0.25 budget); `language="es"` everywhere it matters;
Spanish filler removal ("este" left out, being the word "this"); Windows speech
asked for a Spanish recogniser; "Quill dicta" and "deja de dictar" as the
default wake and stop phrases; Spanish punctuation words (coma, punto, punto y
aparte, abrir interrogación and the rest) counted only while the engine is not
punctuating (option 1 of the "coma" problem, decided 2026-10-03), matched
without accents; the three text bugs fixed (accents cut by the parser, no
capital after "¿", "¿" and "¡" not stripped). The drafted Spanish commands
(`SPANISH_COMMAND_HELP`) are off unless `QUILL_DEV_BUILD=1` and
`QUILL_DICTATION_SPANISH_COMMANDS=1`. Nemotron and Parakeet TDT dictate Spanish
too, as downloads.

**The Spanish punctuation design, kept.** Marks are recognised anywhere in a
phrase, and "coma" ("que coma") and "punto" ("el punto es") are ordinary
Spanish words, which is why they count only while automatic punctuation is
off. "colon" is not an English mark in Spanish (Colón). "¿" and "¡" hug the
next word like an opening bracket.

## 10. Not done yet, and what each needs

| Item | Needs |
|---|---|
| **The Spanish measurement** (dict.md 9.7 step 2): accuracy, speed and memory of multilingual Whisper tiny on Spanish against the section 1 budgets, and whether Whisper writes "¿" and "¡" itself | Ten Spanish recordings from a native speaker (instructions below) |
| **Native-speaker review** of the wake and stop phrases, the Spanish punctuation words, and the Spanish command table, before the commands are switched on | A native speaker's time |
| **The real-voice test** for every engine and model (the 2026-10-05 numbers are on a synthetic voice, which flatters every engine) | Recordings of real voices, ideally several |
| **Measurements on the baseline machine** with NVDA and JAWS running: speed, memory high-water mark, screen-reader lag, battery draw over ten minutes, for every offered model; then tightening each model's `cost_factor` (the Distil-Whisper and large-v3 factors are estimates) | A 4 GB dual-core Windows 10 computer and a person to listen |
| **A CI-runnable benchmark gate** (`dictbench.py` baseline mode): every engine offered must meet the speed budget on one thread on recorded speech | Recorded speech checked into a test-asset location, and a CI runner whose speed is stable enough to gate on |
| **Word biasing for the local models** (section 5 B; the plumbing is built and off, section 22, D-28) | A sherpa-onnx that encodes hotwords for mixed-case SentencePiece vocabularies, a hotword-capable Nemotron decoder, or an English Zipformer transducer measured on B-1 |
| **The shared layer's measurements** (section 22): keyword spotting (a false-trigger soak, the detection rate, CPU), hotwords on an English Zipformer, the punctuation and speaker models, and sherpa-onnx TTS against kokoro-onnx (D-30) | B-1, B-3 and the 8 GB machine (B-8) |
| **Interface translation** (menus and spoken replies in Spanish) | Its own decision (dict.md 9.6) |
| Held for Jeff, untouched: removing the bundled models from the installers, and Nemotron as the first-run default | Jeff |

### Recording the Spanish test set (from dict.md 9.10)

For the native speaker. Ten sentences, ten files, one text file:

1. **Ten sentences** of ordinary written Spanish, the kind of thing somebody
   dictates: a short email, a note, a question or two (so "¿" appears), one
   exclamation, a few names and numbers, a few accented words (está,
   información, mañana), and one longer sentence of 20 words or so.
2. **Record each one as its own WAV file: 16 kHz, mono, 16-bit.** In
   Audacity: Project Rate 16000, record in mono, File > Export > Export as
   WAV, "Signed 16-bit PCM". Name them `01.wav` to `10.wav`. Speak naturally,
   at normal speed, in a normal room, on an ordinary headset or laptop
   microphone. Do not say the punctuation.
3. **`transcripts.txt`** in the same folder, UTF-8, one line per file: the
   name, a tab, and exactly what was said, written properly, with accents,
   capitals and punctuation, for example `01.wav`, a tab, then
   `Hola, Ana. ¿Puedes enviarme el informe mañana?`

Then the benchmark is one command each:

    python scripts/dictbench.py "path\to\folder" --language es --json es-tiny.json
    python scripts/dictbench.py "path\to\folder" --engine whisper --json en-check.json

It prints, per file and overall, word errors (and again ignoring accents),
which marks were written (including "¿" and "¡"), speed per thread against the
0.25 budget, and peak memory when `psutil` is installed.

## 11. Design history worth keeping

- **Why the default stays local and small.** Moonshine tiny and Whisper tiny
  meet every budget with room to spare on the baseline machine; every larger
  model is over the speed budget on one thread. The reliability work (Escape,
  the watchdog, one Ctrl+Z per phrase, words where you started, finishing the
  last phrase) does more for everyday dictation than a bigger model.
- **Why downloads after all.** dict.md 4.3 recommended a separate signed
  "Speech Pack" installer to keep "nothing downloads inside the app". Jeff
  asked on 2026-10-05 for VS Code's models "as on demand offerings", which
  overrides that rule for the optional models only; the bundled engines and
  the no-download default are unchanged.
- **Why streaming costs.** A streaming model works continuously while you
  talk, competing with the screen reader on two cores and draining a battery.
  Feeding only speech plus 0.6 seconds of quiet (section 3) is how live
  dictation keeps that cost to the speaking itself.
- **Why OpenAI dictation is opt-in and own-key only.** Audio is the most
  personal thing QUILL handles. It leaves the computer only when the person
  chose the engine, agreed in plain words, and pays for it themselves; the
  free hosted AI has an allowance that a morning of dictation would exhaust
  and is not built to carry audio.
- **Why not clean every phrase.** Cost, privacy and a network round trip
  before each phrase is written, slowest exactly where QUILL's users are.

## 12. Transcribe a Recording: a file through dictation's engines

Built 2026-10-05 at the owner's request ("we do need a way to pass a mp3 and
get it transcribed in the background as a part of the dictation logic and
they should be able to select a model for this"), in both editors on
**Shift+F5**, shipping in QUILL Lite 1.2 and QUILL 1.0.

**Shared, like the rest of dictation.** One command
(`cmd_transcribe_audio_file`, `tools.windows_dictation_transcribe_file`) on
`DictationTranscribeMixin` (`quill/ui/windows_dictation_transcribe.py`),
which `WindowsDictationMixin` inherits; QUILL's adapter answers two hooks (its
task manager, a new tab) and owns no command. One window
(`quill/ui/dictation_transcribe_dialog.py`). The parity test checks the row,
the key, the handler and the help topic in both.

**Why a second way into transcription is not a second stack.** QUILL already
had two: Tools > Speech > Transcribe Audio or Video (Offline) (whisper.cpp or
Faster Whisper, ffmpeg, captions, speaker labels) and AI > Transcribe Audio
File (cloud Whisper, Transcript Actions). Neither can ship in QUILL Lite (no
ffmpeg, no engine packs), and neither uses the dictation models people now
download. This command uses only dictation's own pieces: its engines and
loaded-model cache (`local_recognizer._load`, `transcribe`), its Silero
voice detector (`_vad`), its OpenAI path (`openai_transcribe.transcribe_phrase`,
the same `/v1/audio/transcriptions` endpoint, so no new egress entry), and its
text tidying (`options.clean_phrase`, `parser`, `composer`, the continuation
words from `editing.py`). The visible name is "Transcribe a Recording", not
"Transcribe Audio File", because QUILL's AI menu already has that name.

**Decoding without ffmpeg** (`audio_file.py`, `media_foundation.py`). The
shared runtime already carries libsndfile 1.2.2 (`soundfile`), which reads
WAV, FLAC, Ogg Vorbis, Opus and MP3; Windows Media Foundation, on every
Windows, reads MP3, M4A, AAC, MP4 sound, WMA, WAV and FLAC through its Source
Reader, called with `ctypes` (no COM package). Media Foundation goes first for
M4A, AAC, MP4 and WMA, libsndfile first for the rest, and ffmpeg is tried last
only where the program has it. Checked 2026-10-05 on Windows 11 with one
recording encoded seven ways: every format decoded to the same 20.3 seconds;
Media Foundation refused Ogg and Opus (unsupported byte stream, 0xC00D36C4),
which libsndfile reads. So QUILL Lite has no format it must
refuse. Sound is mixed to one channel and resampled to 16 kHz a second at a
time (a windowed-sinc low-pass, then linear interpolation, state kept across
blocks), so an hour of stereo MP3 never sits in memory.

**The model list** (`file_models.py`) is every engine this computer has for
the chosen language: Moonshine tiny and Whisper tiny, every downloaded model,
and OpenAI's models (read live, less the live-only `gpt-live-transcribe`)
where a key is saved and Safe Mode is off. Windows speech and voice typing are
not offered: both listen to a microphone. The suggestion is the most accurate
local model by the catalogue's published figures, preferring models that hear
a whole phrase: Parakeet TDT 0.6B v3, Parakeet Unified, Nemotron, the Whisper
family large to small, Moonshine base, then the built-in two. OpenAI is never
suggested.

**The estimate** is Moonshine tiny's speed on this computer's class (the
two-second check's hardware fallback, 0.12 on a modest computer, 0.05 on a
capable one; no model is run to work it out) times the model's measured
`cost_factor`, over 1.6 for the two threads used, plus 0.02 for decoding and
voice detection. For an hour on the baseline machine: Moonshine tiny 6
minutes, Whisper tiny 19, Parakeet TDT 30, Nemotron 37, Whisper small 1 hour
49, large-v3-turbo about 6 hours.

**What the person hears (GATE-13).** One sentence at the start, the
percentage quietly at 25, 50 and 75 (`activity.ProgressAnnouncer`), every
percent only in the status bar, one sentence at the end with the length,
words, time taken and where the text went, the error tone and the reason on
failure. Every result is kept in Activity. Shift+F5 while one runs shows its
progress and Stop Transcribing; several files queue.

**End to end, 2026-10-05** (no interface; real decoders, real Silero, real
models; recordings made with Windows' Zira voice, development machine, two
threads):

| Recording | Model | Result |
|---|---|---|
| 20 s, seven formats | Moonshine tiny | all seven read; 41 words, two paragraphs split at the 3-second pause, timestamps 00:00:00 and 00:00:08 |
| 20 s MP3 | Whisper tiny, Parakeet TDT, Nemotron | the same text; Nemotron heard "Drive Smith" for "Doctor Smith" |
| 171 s MP3 | Moonshine tiny | 10.5 s (0.06 of the recording's length), 380 words, 3 paragraphs |
| 171 s MP3 | Whisper tiny | 20.0 s (0.12), 374 words |
| 171 s MP3 | Parakeet TDT 0.6B v3 | 24.6 s (0.14) after a 4.5 s load, 368 words |

Parakeet glues a currency sign to the word before it (`about$12,000`); the
writer puts the space back after a lower-case letter, leaving `US$` alone.

**File-command regression, 2026-10-05.** The background runner was checking
`CancellationToken.is_cancelled` as a value rather than calling the method,
so every real task token looked cancelled and no transcript was delivered,
regardless of the selected model. The runner now calls `is_cancelled()`;
command tests pass real active and cancelled tokens and make the fake
transcriber honour cancellation. The duration estimate also tries Windows
Media Foundation metadata when mutagen and libsndfile cannot report a length,
without decoding the recording. An unknown length does not prevent transcription.
Checked after the fix with the owner's 254-second MP3, local Whisper tiny,
the real task manager and a real wx text control: 638 words delivered on the
UI thread in 38 seconds, with no network. libsndfile reported malformed MP3
frames but decoded the recording through to the end; those warnings did not
prevent the transcript from being delivered.

**Not built, and what each needs:**

| Item | Needs |
|---|---|
| Speaker labels ("Speaker 1:") | A diarization model in sherpa-onnx's set, measured on the baseline machine; QUILL's offline transcription already labels speakers with its own engine |
| Open with, from File Explorer, straight into this window | A shell verb in both installers; the window already takes a dropped file and the command takes paths |
| The real-voice check | The same recordings section 10 asks for, read as files |
| Translation to English while transcribing | Whisper's translate task through sherpa-onnx, and a decision on whether it belongs here |

## 13. The gap plan: twelve published capabilities, checked and built

Later on 2026-10-05 a second working note (also called `dict.md`, gitignored,
now retired) checked both editors against twelve capabilities another product
announced for its dictation, and planned every gap. Jeff approved all of it,
taking the recommendation on all eleven questions. Everything below is built,
in shared code, in both editors on the same keys, held equal by
`tests/unit/ui/test_dictation_parity.py`.

| # | Capability | Status | Where |
|---|---|---|---|
| 1 | Automatic and spoken punctuation | Was already there | `vocabulary.py`, `options.py` |
| 2 | Live transcript mode | Built: Start or Stop Live Transcript, Ctrl+Alt+Shift+PageDown; new document, no commands but the stop phrase, nothing said per phrase, a paragraph at a four-second pause, optional time stamps, keeps writing while you work elsewhere | `transcript.py`, `windows_dictation_extras.py` |
| 3 | Marks spoken in the read-back | Built: Say punctuation marks in the read-back, on by default (question 1); braille and the status bar keep the characters | `readback.py` |
| 4 | Adjustable pause | Built: Longer (2 s) and Longest (3 s), labelled with the cost; a phrase ending on "a", "the", "very" and kin runs on into the next | `options.py`, `editing.py` |
| 5 | Go to, select and correct words | Built: select, go to, go before, go after, correct, "through" ranges, select next and previous, sentence, line and paragraph units; not found is written as text (question 3) | `targets.py`, `voice_commands.py` |
| 6 | Characters, caps, spelling, Markdown | Built: punctuation and all caps in spelling, spell one word, spell that, caps on, all caps on, no space on, backtick, code fence, tilde, pipe, caret, the comparison signs, and bullet, numbered item, block quote and heading one to six at the start of a phrase only (question 4) | `vocabulary.py`, `parser.py`, `composer.py` |
| 7 | Snippets, clips and Copy All by voice | Built: copy all, copy that, show clips, show snippets, paste clip one to twelve, insert snippet, insert or expand abbreviation, each through the editor's own feature | `voice_commands.py`, `windows_dictation_library.py` |
| 8 | Dictation beyond one window | Built: Dictate Anywhere in Quill Inkwell (question 9), with a key chosen by the person, the shared controller and `ExternalDocument`; started from either editor's More Dictation Settings | `anywhere.py`, `windows_dictation_external.py`, `apps/inkwell_dictation.py` |
| 9 | Per-document context | Built: Dictation Context for This Document, Ctrl+Alt+Shift+PageUp, per document by path with saved contexts (question 10); OpenAI's prompt and Tidy Dictated Text | `contexts.py`, `dictation_context_dialog.py` |
| 10 | Instant language switch | Built: Switch Dictation Language, Ctrl+Shift+F11 in both (question 5; QUILL's Forget External Change Answers moved to Ctrl+Shift+0 under rule 9), and by voice both ways | `voice_commands.py`, `windows_dictation_extras.py` |
| 11 | An online option | Was already there | `openai_*.py` |
| 12 | Guide and tutorials | Built: "Dictating well" in both guides, a section per feature, five new lessons in both editors | `quill/core/tutorials/dictation_lessons.py` |

Also built: **Dictation Status** in QUILL Lite on Alt+F9, the key QUILL's
Locked Dictation status already had, which now answers for live dictation
whenever Locked Dictation is idle.

**Decided against, on purpose.** Automatic language detection per phrase
(question 6: wrong-language text written silently is worse than one command).
Bare "expand <word>", "next one" and "previous one" as voice commands: each is
also ordinary English said on its own ("Expand the budget."), so "insert
abbreviation", "expand abbreviation", "select next" and "select previous" stand
in for them.

**Still to do.**

| Item | Needs |
|---|---|
| The longer pauses measured with a slow real speaker (question 11) | A recording or a session with somebody who speaks slowly |
| Memory with Moonshine and multilingual Whisper both loaded after a language switch, against the 600 MB budget | The baseline machine (section 10) |
| Live transcripts of the computer's own sound (an online meeting) | WASAPI loopback capture; question 7 says after the microphone version has been used for a while |
| Native-speaker review of the drafted Spanish twins of the new commands (`vocabulary_es.SPANISH_COMMAND_HELP`, `SPANISH_PREFIX_HELP`), still behind the development flag; only "cambiar a inglés" and its kin are on in every build | A native speaker, with the rest of section 10's review |
| NVDA and JAWS checks of every new spoken line | `docs/qa/screen-reader-checks-2026-10.md` |
| Dictate Anywhere reads only what it typed itself, so select and correct stay inside QUILL; reading another program's text would need UI Automation text patterns per program | A decision whether it is worth it |
| Inkwell keeps its own copy of the dictation settings, refreshed only when an editor hands them over | A shared settings store across the family, if one is ever wanted |

## 14. As built, 2026-10-13: one microphone, the same keys, the working tick, and three slices

Items of the October follow-up plan Jeff approved, numbered there D-11, D-14
and D-17, then slices of D-5, D-7 and D-8, and an accessibility review's changes
to the sentences and the tick. Each is in shared code; QUILL and QUILL Lite get the same thing
through the one implementation they both run.

### D-11. One microphone owner across QUILL, QUILL Lite and QUILL Transcribe

**What the plan assumed, and what was true.** The plan said `dictation_owner.py`
arbitrated between QUILL Transcribe and Inkwell only, that the editors' Ctrl+F11
never consulted it, and that only QUILL's main frame claimed its window. All
three were true. The plan's remedy, that the editors take the same owner lock
while they dictate, would not have worked: QUILL Transcribe holds the owner lock
for as long as it runs, so the editors could never have dictated while it sat
in the tray.

**What was built.** A second lock of the same kind, `MicrophoneLock`, in
`quill/core/dictation_owner.py`: an operating-system file lock in the family's
data folder, held by whichever of QUILL, QUILL Lite, QUILL Transcribe and Inkwell
has the microphone open, for exactly as long as it is open. The controller takes
it in `_open`, before the recogniser starts, and lets go in `_close_recognizer`,
which every path out of a session goes through (stop, an error, the one silent
restart, a language switch, the window closing, `shut_down`); the kernel lets go
when the program exits. The gate is a constructor argument, so a controller in a
test has none (`quill/core/windows_dictation/microphone_owner.py`). Opening for
the wake phrase is refused silently, because nobody asked for anything.

The sentences (`busy_sentence`) name the program and the key that stops it, as
that program has it bound: each holder writes its live key into the lock's note
when it takes the lock (the editors' Ctrl+F11 binding, QUILL Transcribe's saved
start and stop key, Locked Dictation's Ctrl+F9), spelled as the guides spell
keys (`spoken_key`: the backslash key is "Backslash"). Every sentence ends
"then try again":

- "QUILL Lite is dictating. Press Ctrl+F11 in QUILL Lite to stop it, then try
  again." (and "QUILL is dictating. Press Ctrl+F11 in QUILL ...")
- "QUILL Lite is dictating in another window. Press Ctrl+F11 there to stop it,
  then try again." (a second copy of the same app)
- "QUILL is already dictating. Press Ctrl+F9 to stop it, then try again." (the
  same process: Locked Dictation and Ctrl+F11)
- "QUILL Transcribe is listening. Press Alt+Shift+Backslash to stop it, then try
  again.", or with no key chosen, "QUILL Transcribe is listening. Stop it from its
  tray icon, then try again."
- "Quill Inkwell is dictating. Stop it there, then try again." and "Another
  program is dictating. Stop it there, then try again." (no key to name). QUILL
  Transcribe's own refusal while Inkwell dictates is the same sentence.

QUILL Lite's MDI shell now calls `claim_own_expansion`, so QUILL Transcribe
and Inkwell refuse it with "This is a QUILL window: press Ctrl+F11 to dictate
here." (and Inkwell's abbreviations keep out of a window that expands its own).
Cast and Radio are not claimed. The suite gives every test its own lock folder
(`tests/conftest.py`, `_family_locks_of_its_own`), or parallel workers would
refuse each other.

Tests: `tests/unit/core/test_dictation_microphone_and_tick.py` (two controllers,
one recogniser; every sentence; release on stop, error, failed start and shut
down) and `tests/unit/apps/test_transcribe_app.py` (a real QUILL Lite window and
QUILL Transcribe meeting the one lock, both ways round).

**Locked Dictation too.** QUILL's Locked Dictation and Hold to Dictate
(`quill/core/speech/dictation/controller.py`, F9 and Ctrl+F9) record first and
transcribe afterwards. They take the same `MicrophoneLock("quill")` before
capture starts and let go the moment capture ends (stopped, discarded, failed
to start, a failed session), so the lock is never held through transcription;
the frame's destroy event lets go too (`main_frame_dictation_hotkeys.py`). A
refusal goes through the services' `microphone_busy`, which plays the error tone
and says the sentence. Tests: `tests/unit/core/test_locked_dictation_microphone.py`.

### D-14. The same dictation keys in QUILL Transcribe, and a parity gate

**What was true.** As the plan said: Ctrl+D and Ctrl+, against Ctrl+F11 and
Alt+Shift+F6, no Recent Phrases, My Words or language switch, and no row for any
of it. The plan missed one: Transcribe a Recording is Shift+F5 in the editors and
was Ctrl+O here.

**What was built.** `quill/core/transcribe/parity.py`: `SHARED_COMMANDS` (the
editor command and the method its chord runs here), `ALIASES` (the 1.0 keys,
kept as second keys in the frame's accelerator table, rule 5) and `DIVERGENCES`
(each editor dictation command QUILL Transcribe does not have, with its reason,
rule 11). The menu reads the chords from `DEFAULT_KEYMAP`: Ctrl+F11,
Alt+Shift+F6, Alt+Shift+F10 (My Words and Phrases, the editors' window over the
same `dictation.md`), Ctrl+Shift+F11 (Switch Dictation Language, which also makes
"switch to Spanish" work here) and Shift+F5. Live Transcript, Dictation Context,
Dictation Status and Tidy Dictated Text are divergences. Recent Phrases was one,
until the D-5 slice below put it on Shift+F11. `PREFERENCES_OFF` names the two shared settings QUILL
Transcribe always runs off (the wake phrase, hold to talk), with reasons.

Tests: `tests/unit/ui/test_transcribe_dictation_parity.py` builds the real menu:
every editor dictation command is shared or a divergence; the menu shows the
editors' chord; no key is claimed twice, the 1.0 keys included; the settings are
the editors' fields with only `PREFERENCES_OFF` differing; every command in
`EXTERNAL_COMMANDS` is in "What can I say" (now the external list, D-7).

### D-17. A soft tick while a phrase is still being worked on

**What was true.** The cues were on, phrase, off and error. There was no
end-of-speech event to time from: the worker posts `on_speech_started` and then
`on_phrase`, and RECOGNIZING spans the whole time somebody talks, so timing from
it would tick through a long sentence.

**What was built.** The worker posts `on_phrase_decoding` when it hands a
finished segment to the engine (`recognizer_worker.py`), and
`quill/core/windows_dictation/working_tick.py` times from there: nothing for a
second, a tick every second after that, and "Still working on that phrase."
when a wait reaches four seconds (how often: see the review below). The text arriving
(`_receive`), a failure, stopping or closing ends the wait and stops the pending
callback. Timing is the host's `call_later` (`wx.CallLater`, one-shot, stopped
when the wait ends; a late one for a finished wait does nothing). The setting is `windows_dictation_working_tick` in the shared
`DictationSettings`, off in both editors, on in QUILL Transcribe through
`TRANSCRIBE_DICTATION_DEFAULTS`; More Dictation Settings shows it as "Tick while
a phrase is being worked on" (Alt+R). The clip, `windows_dictation_working.wav`,
is generated with the other four and is the shortest (70 ms) and quietest of
them. The screen-reader gate already captures QUILL's own process, so the tick
is never heard as speech; the cost, said in the guides, is a moment each tick in
which the microphone is not listened to.

Tests: `tests/unit/core/test_dictation_microphone_and_tick.py` (no tick under a
second, ticks after, the sentence once a session, stopped by the text, by a stop
and by a failure, silence when off, speech when the pack has no clip),
`test_dictation_streaming_worker.py` (decoding is posted before the text), and
QUILL Lite's window ticking through the shared code (`test_lite_dictation.py`).

**The accessibility review (same day).** *What you hear after each phrase*
(`phrase_feedback`) is now the cap on the tick, because somebody who chose words
only, or nothing, did not choose a sound once a second: `silent` (or the setting
off) is no tick and no sentence; `speech` is no tick and the sentence at four
seconds, once per wait; `sound` and `both` tick, with the sentence once a
session. A pack without the clip falls through to words (`resolve`): the
sentence at four seconds, once per wait, never a word a second. The sentence is
only said from the timer callback while its wait is still open, so a phrase
that arrives first means it is never said; and the read-back is spoken with
interrupt in every host (QUILL's and Transcribe's `force=True`, QUILL Lite's
`interrupt=True`), so it cuts a sentence said a moment before short rather than
queuing behind it. The screen reader's own speech is never cancelled. A manual
check is in `docs/qa/screen-reader-checks-2026-10.md`.

### D-5 slice. Recent Phrases in QUILL Transcribe

**What was built.** Shift+F11, the editors' chord, opens the editors' window
through the editors' code, now one function both use
(`quill/ui/windows_dictation_tools.open_recent_phrases`, with `copy_phrase` and
`NOTHING_RECENT`). The list is the shared controller's `recent`: the last 20
phrases of this run, newest first, in memory only. **Insert Again** types the
phrase into the program the person goes back to (`quill/apps/transcribe_recent.py`):
from QUILL Transcribe's own window it waits for another program to come forward,
as starting dictation from the window does ("Switch to the field you want. The
phrase is typed there."; "Cancelled; nothing was typed."; "No other program came
forward, so nothing was typed."), then types through the shared external
document's checked keystrokes inside a one-shot `LockedTarget`, so the target
checks a dictated phrase gets apply. Success says nothing (the reader echoes the
typing; the status line says "Typed: ..."); a refusal is spoken with the error
tone; Windows taking only part of it says "Windows did not take all of that
phrase, so part of it may be missing. Check the field." **Copy** says "Copied:"
and the phrase. Not built: keeping the list on disk, the rest of D-5.

Tests: `tests/unit/apps/test_transcribe_app.py` (empty list, newest first, typed
into the program in front, waits from the window, refused in a password field,
Copy) and the parity gate, which no longer has a Recent Phrases row.

### D-8 slice. Snippets, abbreviations and clips by voice in any program

**What was built.** `INSERT_SNIPPET`, `EXPAND` ("insert abbreviation") and
`PASTE_SLOT` ("paste clip") joined `anywhere.EXTERNAL_COMMANDS`: they only
insert and never read the target. QUILL Transcribe's and Inkwell's feedback
ports now answer `library()` with `AnywhereLibrary`
(`quill/ui/windows_dictation_anywhere_library.py`), which reads the family's
own files: QUILL's snippet library, the shared abbreviation library and QUILL's
copy-tray slots. The controller types the text through the external document as
one phrase (`voice_commands._insert_text`), so "scratch that" takes all of it
back. Blanks are written "[name]" with no prompts, and `${cursor}` is dropped
(the cursor cannot be moved inside another program's text without reading it);
both are said in the guides. "copy that", "copy all", "show clips" and "show
snippets" stay refused. Not built: prompted fields, the rest of D-8.

Tests: `tests/unit/core/test_dictation_external_list.py` (each command typed in
a fake Notepad, "scratch that" erasing a whole snippet, reading commands still
refused, the family library dropping the cursor and keeping blanks).

### D-7. "What can I say" in QUILL Transcribe lists exactly what works there

**What was true.** As the plan said: `show_dictation_commands` called
`commands_reference()` with no arguments, so the list included commands refused
in other programs and left out the person's own phrases, and the spoken "what
can I say" opened a modal window, which took the focus and so paused dictation.

**What was built.** `commands_reference(external=True)` lists only
`EXTERNAL_COMMANDS` (now with the D-8 commands), drops the wake phrase and
"spell that", and adds the two inserting limits; the editors' default list is
unchanged. QUILL Transcribe's Dictation Commands window (Ctrl+Shift+C) passes
`external=True`, the person's own phrases from `dictation.md`, the dash, the stop
phrase and the language; Inkwell's window passes `external=True` too. Said while
dictating, "what can I say" no longer opens anything: QUILL Transcribe says
"In another program, you can say scratch that, new line, start spelling, insert
snippet and its name, or stop dictation. For the full list, open Dictation
Commands from the Dictation menu, Ctrl+Shift+C." The key is read from the menu
item as it is now (`spoken_commands_summary`). No command word (D-1) was listed
then: it was not built. It is now (section 18), and with strict mode on the
spoken answer puts QUILL before each command and the window has a "The command
word" section.

Tests: `tests/unit/core/test_dictation_external_list.py` (every listed phrase
parses to a command allowed in another program; no refused command is listed;
own phrases appear; the editors' list is still complete; the summary's five
work there), and `test_transcribe_app.py` (the spoken answer opens nothing; the
window's list carries the person's phrases).

## 15. As built, 2026-10-15: the never-type list (D-24) and Inkwell's field lock (D-15)

**The never-type list.** A fourth refusal beside the password field, the
elevated program and QUILL's own windows, and the only one the person
chooses: `windows_dictation_never_type`, program file names, checked in
`foreground_problem`. It starts as the list Inkwell's expansion already
refuses, so the two features agree about which programs hold secrets. Matched
by file name only, because a window title is whatever a program says it is.
Edited in its own window from More Dictation Settings (Alt+N).

**One field, in both hosts.** Inkwell's Dictate Anywhere now dictates through
the same `LockedTarget` as QUILL Transcribe (`locked_external_document`), and
the three paused commands and arming live once, in
`quill/ui/dictation_field_hold.py`.

**Speech goes to OpenAI.** A cloud engine names who receives the speech
(`EngineInfo.cloud_provider`); Transcribe's state line says so while it does.

D-21 was planned beside these but was not built; it stays in section 10.

## 16. As built 2026-10-13: Vosk leaves dictation and the voice features

Vosk had three roles. One stays and two end.

**Chapters stay.** Vosk is bundled in QUILL and Cast to transcribe a podcast
episode for chapters (`service.CHAPTER_PROVIDER_ID`). On hand-built chapter
lists it scored 0.372 against Whisper medium's 0.316, from a 40 MB model, with
no download, because its cues break at natural pauses. Nothing in that path
changed: the provider, the bundled wheel and model, `_stage_vosk_model`,
`scripts/stage_vosk_model.py` and Cast's build all stay.

**Dictation and the voice features end.** For them Vosk is English only, its
last release (0.3.45) was in December 2022, its models are checked by MD5 only
where every other download uses SHA-256, and its accuracy was never measured
here. Moonshine tiny, already bundled, measured 3.4 percent word errors at 0.05
seconds of computing per second of speech (section 6).

* **Voice Command, Conversation Mode and Hey QUILL.** The Voice recognition
  engine choices are now Follow main engine, whisper.cpp (accurate) and
  Moonshine tiny (fast, light). `quill/core/speech/providers/moonshine_tiny.py`
  adapts the bundled model to the provider shape the voice paths use; it calls
  `local_recognizer.transcribe("moonshine", ...)`, so it shares this stack's
  recogniser cache, idle unloader and model folder, and nothing downloads.
  `MainFrame._voice_provider` builds it directly, because it is not a
  dictation choice and so is not in the registry. With the bundled model or
  sherpa-onnx missing it reports unavailable, and voice falls back to the main
  engine as before. A recording longer than 20 seconds is decoded in 20-second
  pieces, the same cut live dictation makes.
* **Dictation pickers.** The guided picker, the Manage Speech Models engine
  radio, the dictation ladder and the media voice-capture fallback no longer
  offer Vosk (`service.CHAPTER_ONLY_PROVIDER_IDS`, `dictation_providers`).
  `download_vosk` is gone; `engine_install.install_vosk` and its pinned wheel
  remain beside the Offline Edition wheelhouse, with no menu path to them.
* **Saved settings.** `quill/core/speech/vosk_retirement.py` migrates on load: a
  voice engine of `vosk` becomes `moonshine_tiny`, a dictation engine of `vosk`
  becomes the default ladder. `vosk_retirement_notice` holds the sentence that
  is owed, and `quill/ui/vosk_retirement_notice.py` says it once after the main
  window is up, in the status bar and through announce: "Vosk is no longer used
  for voice commands or dictation. Voice commands and Hey QUILL now use
  Moonshine tiny, which is already installed. Podcast chapters still use Vosk."
  When only the dictation engine was Vosk: "Vosk is no longer a dictation
  engine. Dictation now uses your default engine." No model is offered for
  deletion, because chapters still use it.

Still to check: the wake word's false-start rate on Moonshine tiny against the
old Vosk numbers was not measured, because Vosk's never were; the NVDA and
JAWS check of the new sentence joins `docs/qa/screen-reader-checks-2026-10.md`.

## 17. As built 2026-10-15: the tested-programs harness (D-4)

**The harness.** `tests/integration/test_transcribe_targets.py` types twelve
recorded phrases (no microphone, no recogniser) through the shared
`ExternalDocument` -- the real `send_text_checked` keystroke path, hush tap
included -- into Notepad, WordPad, Word, Outlook, Edge, Chrome, Firefox and
VS Code, and reads each phrase back through UI Automation (TextPattern, with
ValuePattern and LegacyIAccessible as fallbacks the result names). A phrase is
exact when the field grew by exactly that phrase; line ends and Word's curly
quotes are not counted. Results go to `docs/qa/transcribe-targets.json`, and
`scripts/build_transcribe_compatibility.py` renders them into the Transcribe
user guide between `compatibility:start` and `compatibility:end`
(drift-gated by `tests/unit/scripts/test_transcribe_compatibility.py`).
Supported is the D-4 bar, 95 percent exact; best effort is half; a program
not installed, skipped for safety or interrupted is untested, never
unsupported. Each row has a review-by date 90 days after its check.

**Why it is fenced so tightly.** It types into real programs on a real
desktop, so it is opt-in (`QUILL_TRANSCRIBE_TARGETS=1`), never runs in CI, and
types only into a window it launched: a new process, a title carrying a random
marker, an empty focused field, and before every phrase the same window in
front, the UI Automation focus inside its process, and no keyboard or mouse
input from anyone else since its own last key (`GetLastInputInfo`). Browsers
and VS Code get throwaway profiles; Notepad is skipped when already open,
Outlook when already running (and needs a second opt-in). It closes without
saving and ends only processes whose command line names its own profile.

**The first run, and what it taught.** Run on 2026-10-15 against Notepad
11.2607.14.0, twice, before the idle check existed. Both runs were spoiled by
input that was not the test's: Ctrl held for about 130 ms every few seconds,
most likely by a person at the keyboard (JAWS was running), which turned typed letters
into Notepad shortcuts (a Ctrl+D became a control character, whole words
vanished) and once brought an Edge window to the front, at which point the
guard stopped typing. Nothing about Notepad can be concluded from them, so
the committed results mark Notepad untested and the other programs installed
but not run. That run is why the harness now refuses to start unless the
computer has been idle for 30 seconds, and stops the moment anyone else
touches a key. One more thing it showed: Windows 11 Notepad keeps a closed
window's tabs in its session, so an interrupted run's tab can reappear; the
harness now closes its own tab (Ctrl+W, Don't save) before the window and
records `tab_kept_by_notepad` when it could not.

D-3 still waits: it needs a clean run on an idle computer.

## 18. As built, 2026-10-15: the command word (D-1)

(Section 17 is D-4's, built the same day in a separate change.)

The owner's question was whether to add a keyword that puts dictation into
command and control. It was built as the plan designed it, in shared code, so
QUILL, QUILL Lite, QUILL Transcribe and Inkwell have the same thing.

**What was true.** Commands counted only as a whole phrase, "literal" escaped a
command word, and the wake phrase matcher was forgiving at the start of an
utterance. There was no command prefix, command mode, timeout or earcon, as the
plan said.

**The grammar** (`quill/core/windows_dictation/command_mode.py`, wx-free).
`split_prefix(lexical_words, prefix)` and `split_phrase` reuse
`wake.match_wake` (the same word, the same Soundex, or one edit) on the first
word of the utterance only; the utterance is the voice detector's phrase, so
"first word after a pause" needs nothing new. "Kill" and "will" are two edits
from "quill" and do not match; "quil", "Quill," and "quills" do. What follows is
parsed against the one command table, so every existing command, with its
argument forms (select X, go to X, insert snippet X, paste clip N), works after
the word, and the published reference and "What can I say" stay generated from
one source. Three commands count only after the word (`COMMAND_MODE_HELP`):
"type that" (or "write that"), "command mode" and "dictation mode".
`COMMAND_MODE_PREFIX_HELP` is the empty slot where D-10's "replace X with Y"
goes; D-19, D-2 and D-23 add their phrases to either table and work after the
word with no change to the matcher. Of the plan's grammar table, what exists
bare today works now (scratch, undo, correct, choose, spell that, select and go
to, delete that and delete last sentence, read that, caps and uppercase that,
the library, spelling, stop dictation, what can I say); "delete previous
paragraph", "pause dictation", "resume", "email mode", the AI phrases and the
format words wait for their items and are refused as not a command until then
(the AI phrases are D-2's, built the same day: section 19).
A one-word command word is allowed; `command_prefix_problem` refuses common
English words, every command and mark word, and the person's My Words
vocabulary, and empty means no spoken word. `escape_literal_prefix` makes
"literal QUILL" write the word as it is set; it is done on the recognised
phrase before parsing, which extends the parser's `literal` without giving the
parser a setting to read.

**Never typed** (`command_mode_mixin.py`). `CommandModeMixin` sits over
`VoiceCommandsMixin` in the controller, and the controller calls its `_dictate`
where it used to call `_apply(_parse(...))`, after the echo guard and the stop
phrase and before `compose`. A command utterance goes to `_command_utterance`
and nowhere else: not a command is the error cue and "Not a command. Say it
again, or say QUILL type that to write it."; a command that finds nothing
("select the elephant") says "Not found." instead of writing the words, which is
what it does without the word. While paused for its field
(`target_hold._paused_parse`), a command utterance is answered ("Dictation is
paused. Resume it first.", or the paused commands it already had) and is never
held, so it cannot be typed on Resume. The controller grew by two lines.

**Strict mode** (`windows_dictation_command_prefix_required`): a bare command is
written as words, except STOP (the stop phrase and "stop dictation") and "stop
spelling" while spelling, which is the only way out of spelling mode. Off in
both editors, on in QUILL Transcribe through `TRANSCRIBE_DICTATION_DEFAULTS`.
Transcribe's spoken "what can I say" puts the word before each command while it
is on. Continuous mode ("just write what I say") still writes bare commands as
words; the command word works there, because saying it is explicit. Live
transcripts take no commands, with or without the word.

**One command, command mode, the timeout.** The word alone, or the Command Key,
arms one command: the next utterance is a command with or without the word. A
second press before it, or "QUILL command mode", is command mode; a press in
command mode, or "dictation mode", leaves at once. The timeout
(`windows_dictation_command_timeout`, 8 seconds, 5 to 30) runs on the feedback
port's `call_later`, restarted by each utterance in command mode, and the clock
is also checked when the next phrase arrives, so a host with no timer still
leaves on time. Sounds: `windows_dictation_command_on` (880 then 1175 Hz, 142
ms) when the word or the key is taken and on entering command mode, with no
words except "Command mode." once on entry; `windows_dictation_command_off`
(the same pair falling) when command mode ends, with no words on a timeout. With
the tones off or missing from the pack, the words "Say a command." and
"Dictation mode." stand in, unless the person turned both tones and words off.
`command_mode_text` ("Command mode", "Waiting for a command") is the editors'
status cell (QUILL Lite's Dictation cell, QUILL's status bar) and QUILL
Transcribe's state line and tray name; it is shown, not spoken again.

**Keys.** Speak a Command, `tools.windows_dictation_command`, is **F11** in both
editors (rule 2: free in both, beside Ctrl+F11, Shift+F11 and Ctrl+Shift+F11;
Word's F11 is Next Field, which neither editor has), one handler in
`quill/ui/windows_dictation_command_key.py`, a `COMMAND_EQUIVALENTS` row, and
the same chord in QUILL Transcribe's window (`transcribe/parity.py`
`SHARED_COMMANDS`). Off, it starts dictation in that document and arms one
command. QUILL Transcribe's system-wide **Command Key** (`command_hotkey`,
hotkey id 0x51B2) is empty by default, offered in setup beside Record Key
(Alt+O, Record Command Key Alt+N), and chosen in File > Command Key...
(Ctrl+Alt+Shift+K) through the family picker; pressed with dictation off, it
starts dictation in the field in front and arms one command.

**Settings UI.** More Dictation Settings has a Commands group in all four hosts:
the command word (Alt+C), strict mode (Alt+E) and the seconds (Alt+D), each with
F1 help. OK is refused, with the sentence `command_prefix_problem` gives, while
the word would not do.

**Tests** (with fakes; no microphone): `tests/unit/core/test_dictation_command_mode.py`
drives the shared controller with an editor-like document and with
`ExternalDocument` whose injector fails the test if a command is typed (eleven
command utterances, command mode in Notepad, "QUILL scratch that" sending only
backspaces), and covers strict mode, type that, literal, the name mid-phrase,
the timeout with and without a timer, the keys, and the paused session.
`test_transcribe_app.py` (setup, the key at launch and through the picker, the
key starting dictation, F11 from the window), `test_lite_dictation.py` (F11 and
the word through QUILL Lite's real window), `test_dictation_parity.py` (one
handler, one chord in all three, the same settings) and
`test_dictation_more_dialog.py`.

**Still to check, with a microphone and the real programs.** "QUILL scratch
that" in Notepad, Word and Edge with strict mode on; how often each engine
hears "QUILL" as something else (the plan's risk: "quil" and "kill"; Moonshine
and Whisper were not measured, and no engine-specific vocabulary entry was
added); the B-3 30-minute soak; and the NVDA and JAWS check that the tone and
"Command mode" are heard once and the state line is not re-read. They join
`docs/qa/screen-reader-checks-2026-10.md`.

## 20. As built, 2026-10-15: one word list for the family, with Import and Export (D-12)

**Import and Export.** My Words and Phrases has **Import...** (Alt+I) and
**Export...** (Alt+X) in every host that opens it: QUILL, QUILL Lite and QUILL
Transcribe. Quill Inkwell has no My Words window; it reads QUILL's list, so an
import done anywhere reaches it. Two formats, chosen by extension: the same
Markdown `dictation.md` is, and CSV with `say,write,kind` columns (`kind` is
optional on import; without it an empty `write` is a word and anything else a
phrase). The model is `quill/core/windows_dictation/words_exchange.py`; the
flows and the preview are `quill/ui/dictation_words_exchange.py`.

**Merge rules.** Import never replaces. Each entry is new (added at the end of
its list), already there (same kind, same text), or different from yours (the
same word or spoken phrase, other spelling or other text), and yours is kept.
A file that repeats itself counts the repeat once. Words compare without case
for the key but with case for "same", so `nvda` against `NVDA` is a
difference, reported, not a silent second spelling. A `## Commands` section is
adopted only when the list has none.

**Nothing changes before a yes.** A preview window lists the new entries, with
the counts as the list's label so the reader says them as the list takes focus
(GATE-13: no announcement). **Add Them** first copies the list to
`dictation-before-import.md` beside it, the undo for one import, and then
says the outcome: "Imported 12 words, 3 already there." A file with nothing
new opens no preview and says so. A file that is not a word list is refused in
a sentence (`WordsImportError`, `QUILL-DICTATION-WORDS-IMPORT`).

**Round trip.** Export then import into an empty list writes the same bytes, in
both formats (CSV carries the three lists, not Commands). That is the D-12
acceptance test, `test_export_then_import_round_trips_the_file_exactly`.

**One list for the family, as far as this goes.** QUILL, QUILL Transcribe and
Quill Inkwell already read one file, QUILL's `app_data_dir()/dictation.md`
(`default_profile_path`). QUILL Lite was the odd one out. It now has "Use the
shared word list" (Alt+U) at the top of its My Words and Phrases, stored as
`share_quill_dictation_words` (off, beside `share_quill_dictionary`, for the
same reason: a machine without QUILL should not grow a Quill folder unasked).
Checking it shows the same preview of which of QUILL Lite's words will be added
to the shared list, merges them, and from then on
`DocumentDictationMixin._dictation_profile_path` returns the shared file, so a
word added in QUILL Lite is used by Transcribe on its next phrase (its
`rewriter(default_profile_path())` re-reads the file when its time changes).
Unchecking goes back to QUILL Lite's own file, untouched. A portable QUILL Lite
is never offered the box. The instructions and contexts files live beside the
list and follow it.

**Not done, and where D-13 picks up.** dict.md D-12 places the family list in
the shared family folder (`%LOCALAPPDATA%\QuillVille\Dictation`, the model
store's), with a read-through on each app's old path until it migrates. That
move was not made: QUILL's Locked Dictation, the instructions file and the
contexts file all key off `default_profile_path()`, and moving them is a
migration of three files across installed, custom-folder and portable copies.
D-13 creates `family_dictation.json` in that same folder; it should move
`dictation.md` (and its two neighbours) there in the same change, with
`default_profile_path()` reading the old path until the first write, and
retire `share_quill_dictation_words` by pointing QUILL Lite's "shared" at the
new file. The box is first in the window's tab order but focus still opens on
the list, so the choice is offered on every open rather than asked once.

## 19. As built, 2026-10-15: review before inserting (D-2)

The owner asked for accessible output before rendering: compose by talking,
hear and read the proposal, ask what changed, insert once. Built in shared
code for QUILL, QUILL Lite and QUILL Transcribe; Quill Inkwell has no review
and says "Review is not available here."

**What was true.** As the plan said: Tidy Dictated Text worked on inserted
text, on a direct route, in the editors only; the AI pad and the conversation
window existed; `diffing.py` was line-based only; there was no staging surface
and no AI at all in QUILL Transcribe. D-1 (section 18) had left "review that",
"make it shorter", "what changed" and "insert it" answering "Not a command".

**The state** (`quill/core/windows_dictation/review_session.py`, wx-free).
`ReviewSession` holds `original`, `revisions` as `(instruction, before,
after)`, `current` and `target`, with `revise`, `undo_revision`,
`restore_original` and `diff`. One refinement over the plan: "what I said" is
the text as it stood before the first change was asked for, because with
**Send dictation to review first** the review opens empty and the words are
dictated into it; after the first revision `original` never changes. The
spoken diff is `quill/core/diffing.py`'s `spoken_changes`: word-level
`SequenceMatcher` over words compared without case or punctuation, phrased for
listening ("Changed next Thursday to Friday. Removed um, so."), at most two
sentences ("And 3 more changes." when there are more), "Changed punctuation or
capitals only." when that is all, and "Large change: N percent of the words are
different. Read it before you insert it." over 50 percent. It is always computed
from the two texts, never from the model.

**The conversation** (`review_conversation.py`). Every sentence the review says
and every request it makes, against a port (the window and its host) and an AI
route, so it is tested with fakes. One instruction is one request: "Working."
once and the Status line, no repeated speech; Escape cancels and a late reply is
dropped; a reply that arrives after the person edited the words is not used. The
summary, and "Read it", go through the screen reader (`_announce`), never a
second voice, and the microphone is muted for `reply_seconds` meanwhile (the
reader gate in the controller still applies). Undo Change says "Change undone."
and What Changed holds what it undid.

**The voice half** (`review_mixin.py`, under `CommandModeMixin`; `controller.py`
did not grow). After the command word, `REVIEW_COMMANDS` is asked before the
command table: "review that" takes the words held while paused for the field,
else the last phrase out of the document the way "scratch that" does (so in
another program it is backspaced), and opens the review; with AI off it says
"AI is off. Your words were written as you said them." and leaves it. While a
review is open, "insert it", "what changed", "read it back", "undo that change",
"back to what I said" and "discard it" act on it, and anything after the word
that is not a dictation command is an instruction for the AI ("make it
shorter"); dictation commands still work on the review's text. **Talk About It**
(a check box in the window) makes every utterance a review command or an
instruction, with no word. The review is the feedback port's optional
`review()`, as the library is `library()`. While paused for the field, "review
that" is answered rather than refused, because the held words are exactly what
it takes.

**Nothing reaches the target before Insert.** The review window's text is a
document port (`ReviewBoxDocument`), and the host points the controller at it
while the window is open (`review_retarget`), so dictation there is one undo
step a phrase in a `wx.TextCtrl` and never SendInput. That is also how QUILL
Transcribe's expected pause is done: the plan's new `TargetHold` reason
"reviewing" was not needed, because the locked field is not asked at all while
the review is the document, so no "Dictation paused" is said and nothing is
held. The editors' activation handler no longer stops dictation when the review
window, rather than another program, takes the focus. **Insert** in the editors
is one `replace_as_one_undo` at the place the words came from (the selection
when the review opened); in QUILL Transcribe the locked field's window is
brought forward (`LockedTarget.locked_window`, `force_foreground_window`) and
after 400 ms the words go through `insert_reviewed`: the same `LockedTarget`
checks, never-type list and `send_text_checked` as a phrase, pushed to the
session's history so "QUILL scratch that" takes them back. A refusal types
nothing, is said with the error tone, and the words stay in Recent Phrases for
Insert Again. In every host the words as said and as inserted both go into
Recent Phrases.

**The AI.** A direct-only `revise_dictation` template in
`own_key.INSTRUCTIONS` (the words in `<dictated-text>` as data, the request in
`<request>`, My Dictation Instructions in `<dictation-instructions>`), through
the existing `AiService.ask`: a ChatGPT subscription or an own key, as Tidy
Dictated Text, never the free gateway, whose template would need a deploy.
QUILL Transcribe reads the family's: QUILL's ChatGPT sign-in (same data folder,
the `quill` slug, the credential store reachable from another process of the
same user) and the own key in the Windows credential store, with the provider
and model read from QUILL's settings file and never written. No new call site,
so no `network_egress_audit` entry. AI is off when the area is switched off
(the editors), in Safe Mode, or with no direct route. The consent is
`windows_dictation_review_consent`, a version (`CONSENT_VERSION` 1), asked once
before the first request with No as the default; declining sends nothing.
Context is none by default; this document's dictation context goes only while
the window's **Include this document's dictation context with requests**
(`windows_dictation_review_context`) is checked, editors only.

**The window** (`quill/ui/dictation_review_frame.py`, title "Review Dictation").
A modeless `wx.Frame`: the editable multiline text (Alt+T), What Changed
(read-only), Ask the AI to change it (Alt+K) with Send to the AI (Alt+N), Talk
About It (Alt+A), the context box (Alt+O), Status, and Insert (Ctrl+Enter),
Read It (Ctrl+R), What Changed (Ctrl+D), Undo Change (Ctrl+Z; with no AI change,
the text's own undo), Back to What I Said (Ctrl+Shift+Z), Discard (Escape,
asking only when the AI changed the words; with a request on its way Escape
cancels it instead), and Close, bound with `bind_close_button`, no access key.
Every control has inline `SetHelpText`; F1 purposes are in the QUILL Lite and
QUILL Transcribe catalogues and the window is in the Lite help audit's glob.
Nothing is said on opening (GATE-13). The editors' Ctrl+F11 dictates into the
text through `bind_field_dictation`.

**Keys.** Review Dictation, `tools.windows_dictation_review`, is **Shift+F4**
in both editors and QUILL Transcribe's window (rule 2). Every F11 chord is
taken, Ctrl+Alt+Shift+F11 is a QuillVille launcher row (`SIBLING_APP_ACCELERATORS`),
Ctrl+Alt+F4 was passed over before for being one missed Control from Alt+F4,
and F4 alone is unbound in both, so a missed Shift does nothing. It takes the
last phrase while dictating, else opens empty (or with the kept words).

**Rescue.** An open review is written atomically to `dictation-review.json` in
the editor's data folder (QUILL Transcribe: `transcribe-dictation-review.json`,
because it shares QUILL's folder) on every change, and deleted on Insert or
Discard; Close and the app ending keep it. The next start says once, "A
dictation review did not finish last time. Review Dictation, in the Dictation
menu, brings the words back.", and an empty Review Dictation opens with them.
D-5's own Rescue buffer is still not built; this file is the review's part.

**Settings.** `windows_dictation_review_first` (More Dictation Settings,
"Send dictation to review first", Alt+V, off), `windows_dictation_review_consent`
(0) and `windows_dictation_review_context` (off), in the shared
`DictationSettings`.

**Tests** (fakes; no microphone, no network, no real window touched):
`tests/unit/core/test_dictation_review.py` (the diff, the session, the request,
the rescue, the conversation with consent declined and AI off, and the
controller: review that, AI off, the review commands, instructions after the
word, Talk About It, held words, a host without a review, and Notepad through
`ExternalDocument` whose injector fails the test if anything is typed before
Insert), `tests/unit/ui/test_dictation_review_frame.py` (the real window),
`tests/unit/apps/test_lite_dictation_review.py` (QUILL Lite's window: review,
an instruction, a muted summary, insert as one undo step) and
`tests/unit/apps/test_transcribe_review.py` (nothing typed while reviewing, one
typed insert into the locked field, a refusal when the field moved).

**Still to check, with a microphone, a screen reader and an AI account.** Every
line in `docs/qa/screen-reader-checks-2026-10.md` under "Dictation: review
before inserting"; latency on a modest connection; how the model's replies
compare with the 50 percent flag in practice; and whether two processes
refreshing the same ChatGPT sign-in (QUILL and QUILL Transcribe) ever race.

## 21. As built 2026-10-15: a recommended model, with reasons, and tier labels (D-22)

Until now only Transcribe a Recording suggested a model (`file_models.py`,
for files). Live dictation had the two-second check (section 1) and a verdict
per model, but nothing said which one to pick.

**The recommendation** is `quill/core/windows_dictation/model_advice.py`,
wx-free, and `speed_check.recommend(check, language, privacy="local")` calls
it, as dict.md placed it. It returns one model and a sentence, for example
"Moonshine base, Lightweight: keeps up on this computer's 8 GB and 4 cores,
about 0.3 seconds after you pause; stays on this computer; a 141 MB
download.", and the reasons behind it. The rule:

* **Candidates** are the built-in Moonshine and Whisper and every catalogue
  model with a measurement in section 6, that knows the dictation language.
  An unmeasured model is never recommended, because a reason needs a number.
* **It must keep up.** Moonshine tiny's timed speed here (or the cores and
  memory fallback) times the model's cost factor must be inside the 0.25
  budget. Two threads (up to 0.5) are allowed when the person chooses "The
  fewest mistakes", or on a computer with 16 GB and four cores, which matches
  D-26's tier table (Nemotron the default at 16 GB).
* **It must fit beside the screen reader**: 600 MB of peak memory under 7 GB
  (section 1's budget), 1 GB under 15 GB, 2.5 GB above.
* **Then the fewest word errors win.** Ties go to the bigger model of the
  pair (Moonshine base over tiny), except on a modest computer (under four
  cores or 7 GB), where the built-in model wins a tie: a download measured no
  better is not worth having there. "The quickest response" takes the
  lightest.
* **When nothing keeps up**, the lightest built-in model for the language is
  named, saying it may lag.
* **A graphics card changes nothing**: every dictation model runs on the
  processor, and the reasons say so when one is found. The timed check now
  asks `service.detect_has_gpu`; its memory comes from
  `service.detect_total_ram_gb`, the detector Manage Speech Models uses.
* **Privacy**: every candidate keeps the speech on this computer. OpenAI is
  never recommended; it needs the person's own key and consent.

Every answer ends "These figures are estimates from a synthetic voice" and
"QUILL never changes your model by itself", until B-1 measures real voices.
There is no automatic mode: the sticky-model rule holds.

| Computer | Balance | Quickest | Fewest mistakes |
|---|---|---|---|
| 4 GB, two cores (the baseline) | Moonshine (built in) | Moonshine | Moonshine base |
| 8 GB, four cores | Moonshine base | Moonshine | Nemotron (two threads) |
| 16 GB, eight cores | Nemotron (two threads) | Moonshine | Nemotron |
| Spanish, 8 GB, four cores | Whisper (built in) | Whisper | Nemotron |

`tests/unit/core/test_dictation_model_advice.py` pins these and more as a
table of machine profiles.

**Tiers** (`model_types.tier_for`): a cost factor up to 5 (inside the budget
on the measuring machine) is **Lightweight**; up to 10 (two threads) is
**Balanced**, unless its measured word errors are 2.5 percent or fewer, which
makes it **High accuracy**; above 10 is **High accuracy**. So Moonshine tiny,
Whisper tiny and Moonshine base are Lightweight; both Parakeets and Whisper
base are Balanced; Nemotron and Whisper small and up are High accuracy.
`legacy_tier` gives QUILL's whisper.cpp and Faster Whisper catalogue the same
words (200 MB or less Lightweight, "high" or "highest" accuracy High
accuracy, the rest Balanced), and its Nemotron and Parakeet take the live
models' tiers, so one model never has two.

**Where it shows.** Speech Models (shared by QUILL, QUILL Lite and
Transcribe's Model Library): What matters most (Alt+W), the read-only
Recommendation (Alt+C), Show Recommended Model (Alt+S), and the tier on every
row and in Details. Dictation Settings, in all hosts: a read-only Recommended
for this computer line, and the tier in the Speech engine list. Transcribe's
Choose Model and Set Up: the same line, and the tier in each row. Transcribe a
Recording: the tier in each row. QUILL's Manage Speech Models and guided
offline-speech setup: the tier, and the reason after "Recommended for your
computer" (`service.recommendation_reason`). Windows that open without a
timed check use `speed_check.latest()`: this session's timed check if Speech
Models has run one, otherwise cores and memory, and the reasons say "not
timed". Changing What matters most is the only spoken outcome
("Recommended: Moonshine base."): the focus stays on the choice, so the new
advice is news (GATE-13); the check finishing rewrites the text silently.

Not built here: the "Switch to the Recommended Model" button of dict.md
section 10 (it belongs to retiring legacy models). D-26's `ram_tier`
catalogue field followed in section 22.

## 22. As built, 2026-10-16: one sherpa-onnx layer for every local model (D-26 to D-30)

dict.md's "Smart engine, part 2" asked what it would take to put every local
model on sherpa-onnx. Live dictation, QUILL Lite and QUILL Transcribe were
already there. This pass brought QUILL's Locked Dictation and offline Transcribe
Audio or Video onto the same layer, built the plumbing for keyword spotting,
hotwords, punctuation and speaker labels, and settled the two-runtime question.
What needs a measurement is built but switched off, and says so.

### D-26. One catalogue, one store, one provider

**One catalogue.** `model_types.DownloadableModel` gained the fields dict.md
named, derived rather than typed per model so a new entry gets them for free:
`streaming` (Nemotron), `ram_tier` (4, 8 or 16 GB: the smallest computer whose
memory budget holds the model's measured peak, or an estimate from its download
when it was not measured), `tasks` (every model transcribes and gets phrase
timestamps; multilingual Whisper also translates into English; hotwords only
for a measured model, of which there are none yet), and `source_url` (the
pinned repository page), beside the `licence` it already had. The memory
budgets (600 MB on a 4 GB computer, 1 GB on 8 GB, 2.5 GB above) now live once,
in `model_types.RAM_TIERS`, and D-22's recommendation reads them from there.
`core/speech/catalog.py` keeps only its whisper.cpp, Faster Whisper and Vosk
rows; its Nemotron and Parakeet rows are gone.

**One provider.** `quill/core/speech/providers/sherpa_shared.py`,
`SherpaSharedProvider`, id `sherpa`, replaced the two QUILL-only engines
(`providers/nemotron_onnx.py` and `providers/parakeet_onnx.py`, deleted with
their tests). It lists the built-in Moonshine and Whisper and every model in the
family store, most accurate first, and transcribes through Transcribe a
Recording's own pipeline (`file_transcribe.FileTranscriber`): decoding, Silero
voice detection, the engine a phrase at a time, and dictation's tidying. So
Locked Dictation and Transcribe a Recording give identical text for the same
file and model by construction (a test runs both paths on one fake engine).
`translate_to_english` goes to multilingual Whisper with `task="translate"`
(threaded through `model_loader.build`, `local_recognizer._load` and
`FileJob.translate`); any other model refuses in one sentence. An
`initial_prompt` is reported as one warning sentence, never dropped silently.
Speaker labels are a warning until D-29's model is adopted.

**Errors.** `model_loader.SherpaLoadError` (`QUILL-SPEECH-SHERPA-LOAD`),
`SherpaUnsupportedError` (`QUILL-SPEECH-SHERPA-UNSUPPORTED`) and
`SherpaRuntimeError` (`QUILL-SPEECH-SHERPA-RUNTIME`), all `SpeechError`s, so
every caller that catches speech failures catches them.

**One store, and the migration.** `quill/core/speech/sherpa_migration.py`:

* A saved `speech_provider` of `nemotron` or `parakeet` loads as `sherpa`, and
  the old model ids load as the catalogue's (`parakeet-tdt-0.6b-v3` is
  `parakeet`). Only `nemotron` was ever saved: the settings validation never
  accepted `parakeet`, which the ladder chose instead.
* A Parakeet downloaded the old way (`<app data>/speech-models/parakeet/...`) is
  hard-linked into the store, or moved when the folders are on different
  drives, the first time the shared provider lists its models. All files at
  their pinned sizes or nothing; never downloaded twice. This closes section
  10's "One folder for Parakeet".
* The older Nemotron (80 mel features) is a different model from the
  catalogue's Nemotron 3.5 (128), so it is not adopted. Somebody who had chosen
  it now dictates with the most accurate model they have until they download
  Nemotron 3.5; its old folder is no longer used.

**The ladder** (`service.preferred_dictation_provider_id`): an explicit choice
wins; an installed Parakeet promotes the shared provider (as it promoted the
old Parakeet engine); whisper.cpp stays the default when it has a model; and
when whisper.cpp has none, the shared provider's built-in Moonshine tiny is
used. So removing whisper.cpp's models leaves offline dictation working, and a
fresh install dictates at once. whisper.cpp and Faster Whisper are otherwise
untouched and selectable: the switch of defaults waits for B-1, as dict.md
says.

**Where it shows in QUILL.** The guided offline-speech setup offers "QUILL
speech models (Parakeet, Nemotron and more)" second, after Whisper.cpp, in
place of the two separate engines, with the family catalogue as its models,
D-22's recommendation and reason, and each model's tier. Manage Speech Models
shows the same tiers and capability sentences. The voice features (Voice
Command, the Media Player's Listen for a Command) fall back to the shared
provider and prefer Moonshine tiny there. The Silero voice detector of Locked
Dictation's silence pre-pass is now the bundled one
(`speech_vad.silero_model_path` asks `engines.vad_model_path` first): one copy,
not two.

**Parity.** Transcribe a Recording in QUILL, QUILL Lite and QUILL Transcribe has
**Translate into English** (Alt+E): available for a recording in another
language with a model that translates (the built-in Whisper, or a downloaded
multilingual Whisper), and unavailable otherwise. `test_dictation_parity.py`
asserts translation and timestamps on the shared dialog and job.

**Packaging.** `sherpa-onnx==1.13.8` is pinned exactly in `pyproject.toml`
(both extras), `uv.lock`'s requirement metadata, and the engine pack's
requirements (`engine_install`), because a hotword or decoder change breaks
behaviour, not just the API. The Offline Edition build stages a `nemotron`
wheelhouse (`sherpa-onnx` and `sherpa-onnx-core`), the name `install_nemotron`
already asked `_bundled_wheelhouse_dir` for.

**Not done, and why:**

* Defaults are unchanged: Locked Dictation and offline transcription move to
  the shared layer by default only once B-1 shows parity, and whisper.cpp and
  Faster Whisper become optional packs a release after that (dict.md S5).
* "Word errors on B-1 no worse than whisper.cpp" needs B-1, and "removing
  whisper.cpp leaves every shipped feature working" needs an end-to-end run.
  The ladder change above covers dictation; podcast chapters stay on Vosk.
* Mirroring catalogue models to assets-v1 (`model_mirrors.py`) is a release
  task, done as each model is adopted.
* Downloads report progress through each window's own progress dialog, as
  before; the 25, 50 and 75 percent announcements through
  `activity.ProgressAnnouncer` were not added to the guided setup.

### D-27. Keyword spotting for the command word: built, off

`quill/core/windows_dictation/kws_keywords.py`. The keywords are written from
the command word (with "hey quill" beside a one-word one), the wake phrase and
the stop phrase, tokenised with sherpa-onnx's `text2token`, each with a
boosting score and a trigger threshold. `KeywordGate` runs a `KeywordSpotter`
on the same 16 kHz blocks the voice detector gets, after the reader gate
(`recognizer_worker._spot`), and marks each phrase with
`RecognizedPhrase.keyword_heard`. **Both must agree**: in
`command_mode_mixin._command_split` a phrase whose text opens with the command
word is still dictated when the spotter ran and did not hear it. With no
spotter the field is `None` and the text matcher decides alone, as before.
`_make_recognizer` gives every local recogniser `keyword_gate_for(preferences)`.

It is off (`KWS_ADOPTED = False`, so `keyword_gate_for` returns `None`) until
dict.md's acceptance criteria are measured: under one false trigger an hour on
a 60-minute B-3 soak that mentions "Quill" in sentences, 95 percent detection
after a pause, and under 0.02 of one thread. The gigaspeech 3.3M model's size
and licence are unverified, so it is not in the catalogue. Standby without the
full model (D-9) waits for it.

### D-28. Hotwords for My Words: plumbing behind a flag, off

dict.md says to evaluate first, so `quill/core/windows_dictation/hotwords.py` is
the plumbing behind `HOTWORDS_ENABLED = False`: the hotwords file in the
model's case, the transducer's `modified_beam_search` options and `bpe.vocab`
(`decoder_options`, which `model_loader.build` and `online` accept), and
putting My Words' own spelling back afterwards with the corrector every engine
already uses. `model_types.HOTWORD_MODELS` is empty: a model joins when 20
names are recognised 50 percent better than without hotwords and B-1's word
errors are no worse. **A measurement is needed**, on an English Zipformer
transducer, which is not in the catalogue yet; Nemotron (greedy only) and
Parakeet (garbled NeMo hotwords, section 5 B) were measured not to work.
Passing My Words to the loader at load time is the last wiring step, done with
the first qualifying model.

### D-29. Punctuation and speaker labels: built, off

`quill/core/windows_dictation/post_passes.py` builds sherpa-onnx's
`OfflinePunctuation` (a post-pass that never loses words when it fails) and
`OfflineSpeakerDiarization` (pyannote segmentation, a speaker embedding, fast
clustering), and matches voices to a transcript's paragraphs by overlap,
numbered "Speaker 1", "Speaker 2" in the order they are first heard. Both are
off (`PUNCTUATION_ADOPTED`, `SPEAKERS_ADOPTED`) and no model is catalogued:
the punctuation model's English quality is unverified (gate on B-1), and the
speaker models' sizes, licences and memory on the 8 GB machine are unmeasured.
Every model dictation offers today punctuates by itself, so nothing waits on
the first. The shared provider says a speaker-label request cannot be met yet.

### D-30. Text to speech through sherpa-onnx: not built

dict.md says to decide after measuring: prototype `OfflineTts` Kokoro and VITS
voices, compare audio, language coverage, load time and memory against
kokoro-onnx, and adopt only if every shipped Kokoro voice and language is
covered. None of that measurement has been made, so nothing was built.

### The two runtimes, resolved

* **They coexist, and a test says so.**
  `tests/unit/core/test_onnxruntime_coexistence.py` starts a fresh interpreter
  for each import order, runs a sherpa-onnx voice detector and a Python
  onnxruntime session on the bundled `silero_vad.onnx`, and asserts exactly one
  `onnxruntime.dll` is mapped, sherpa-onnx's. Both orders passed here on
  2026-10-16 (sherpa-onnx 1.13.8, onnxruntime 1.31.0). It skips where the
  bundled model or either runtime is absent, and downloads nothing.
* **Threads are explicit on both sides.** sherpa-onnx recognisers already take
  `num_threads`. Kokoro's onnxruntime session is now built with
  `intra_op_num_threads` set to half the cores, between one and four, and one
  inter-op thread (`quill/core/onnx_threads.py`, used by
  `read_aloud._get_cached_kokoro_onnx` through `Kokoro.from_session`), so
  Kokoro speaking while dictation listens no longer takes every core of a
  two-core computer.

## Appendix A: the dict.md section numbers, and where they live now

| dict.md | What it was | Here |
|---|---|---|
| section 1 | The modest-computer rule: baseline machine, budgets, two-second check, keep-up watchdog, unloading when idle | Section 1 |
| 2.1 | Hold-to-talk on Ctrl+F11 | Sections 2 and 8 |
| 2.2 | Escape cancels the phrase being heard | Section 8 |
| 2.3 | The microphone watchdog | Section 8 |
| 2.4 | Words go where you started speaking | Section 8 |
| 2.5 | One Ctrl+Z per phrase | Section 8 |
| 2.6 | The read-only refusal | Sections 2 and 8 (shipped 2026-09-28) |
| 2.7 | The self-healing engine | Section 8 |
| 2.8 | One session at a time | Section 8 |
| 3.1 | Dictate into any text field | Section 8 |
| 3.2 | Talk to the AI | Section 4 |
| 3.3 | Recent phrases | Section 8 |
| 4.1 to 4.3 | What VS Code uses, what it means on the baseline machine, the options | Sections 6 and 11 |
| 4.4 | The live preview | Section 3 |
| 4.5 | Optional speech models, as built | Section 6 |
| 5, 5.1, 5.3 A to D | Teaching dictation your words | Section 5 |
| 6 | "Correct that", dictation profiles, the live preview | Sections 3, 4 and 8 |
| 7, 8 | The recommendation order and the questions for Jeff | Section 8 |
| 9, 9.1 to 9.10 | Spanish dictation | Sections 9 and 10 |

## Sources

- VS Code (MIT): the files named in section 2, read from
  github.com/microsoft/vscode on 2026-10-05; code.visualstudio.com/docs/configure/accessibility/voice.
- OpenAI: developers.openai.com/api/docs/guides/speech-to-text,
  /guides/realtime-transcription, /guides/realtime-websocket and /deprecations,
  read 2026-10-05.
- NVIDIA Nemotron 3.5 ASR Streaming 0.6B model card; sherpa-onnx 1.13.8.
- QUILL: `docs/design/dictation for windows only/engine-comparison.md`,
  `quill/core/windows_dictation/`, `scripts/dictbench.py`.
