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
| **Word biasing for the local models** (section 5 B) | A sherpa-onnx that encodes hotwords for mixed-case SentencePiece vocabularies, or a hotword-capable Nemotron decoder |
| **One folder for Parakeet** shared by QUILL's Locked Dictation (`quill/core/speech/providers/parakeet_onnx.py`) and live dictation, so it is not downloaded twice | A small migration; deferred |
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
