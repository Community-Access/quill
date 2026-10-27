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
question 4; memory raised to 8 GB on 2026-10-22, Jeff: "every computer these
days has at least 8 GB of memory, now usable is a different story"): Windows
10, 64-bit, **8 GB of memory**, an older dual-core processor with no graphics
help, NVDA or JAWS running beside a browser or mail program, possibly on
battery. Because *usable* memory is the real limit, a recommendation is capped
by what is **free when it is asked**, not only by the total (section 36).

**The budgets** every default must meet there:

| Budget | Limit | Why |
|---|---|---|
| Speed | 0.25 or less (seconds of computing per second of speech, one thread) | leaves three quarters of a core for the screen reader |
| Memory while dictating | 1.6 GB or less on an 8 GB computer (600 MB on a 4 GB one), and never more than is free less 500 MB | an 8 GB laptop often has two or three GB free with a screen reader and a browser open |
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

**Drafted 2026-10-17, behind the same switch (Jeff: "draft them, gated").** Two
more Spanish forms, in `quill/core/windows_dictation/vocabulary_es.py`, kept
apart from `SPANISH_COMMAND_HELP` because their English twins are matched
outside the vocabulary too (review commands by `REVIEW_COMMANDS`, the answer by
`CorrectionLearningMixin._learn_answer`):

| English | Drafted Spanish | Where it is matched | Why these words |
|---|---|---|---|
| "QUILL polish that" / "polish it" (P3) | "pule eso", "púlelo", "mejora eso" (`SPANISH_REVIEW_HELP`) | `ReviewMixin._review_command`, through `spanish_review_command(words, language)` | *Pulir* is the verb a Spanish writer uses for polishing a text; "púlelo" is the same with the object pronoun; "mejora eso" ("improve that") is the everyday fallback. "Corrige eso" was left out: "corrige" followed by words is already the drafted "correct X". |
| "QUILL yes" / "QUILL no" to "Add a correction: A becomes B?" (D-21, QUILL Transcribe's spoken offer) | "sí" / "no" (`SPANISH_ANSWERS`) | `CorrectionLearningMixin._learn_answer`, through `spanish_answer(words, language)` | "No" is the same word in both languages; "sí" is matched folded, so a recogniser's "si" counts too. |

Both helpers answer only when the dictation language is Spanish **and**
`spanish_commands_enabled()` is true (a development build with
`QUILL_DICTATION_SPANISH_COMMANDS=1`), so nothing changes for anybody until a
native speaker has checked them. The English forms keep working in Spanish
dictation either way, and the spoken offer stays in English ("Say QUILL yes to
add it, or QUILL no."), like the rest of the interface (dict.md 9.6). The
published dictation command reference is unchanged, because it lists the
drafted Spanish commands only when the switch is on. Tests:
`tests/unit/core/test_dictation_spanish_drafts.py` (nothing parses with the
switch off or in a release build; with it on, the phrases parse in Spanish
only; "QUILL sí" adds a correction and "QUILL pule eso" polishes through the
controller, and neither does with the switch off). The questions for the
native speaker are in `docs/qa/screen-reader-checks-2026-10.md`, "Spanish
review".

**The Spanish punctuation design, kept.** Marks are recognised anywhere in a
phrase, and "coma" ("que coma") and "punto" ("el punto es") are ordinary
Spanish words, which is why they count only while automatic punctuation is
off. "colon" is not an English mark in Spanish (Colón). "¿" and "¡" hug the
next word like an opening bracket.

## 10. Not done yet, and what each needs

| Item | Needs |
|---|---|
| **The Spanish measurement** (dict.md 9.7 step 2): accuracy, speed and memory of multilingual Whisper tiny on Spanish against the section 1 budgets, and whether Whisper writes "¿" and "¡" itself | Ten Spanish recordings from a native speaker (instructions below) |
| **Native-speaker review** of the wake and stop phrases, the Spanish punctuation words, the Spanish command table, and the 2026-10-17 drafts ("pule eso", "sí" / "no"), before the commands are switched on; the list of questions is "Spanish review" in `docs/qa/screen-reader-checks-2026-10.md` | A native speaker's time |
| **The real-voice test** for every engine and model (the 2026-10-05 numbers are on a synthetic voice, which flatters every engine) | Recordings of real voices, ideally several |
| **Measurements on the baseline machine** with NVDA and JAWS running: speed, memory high-water mark, screen-reader lag, battery draw over ten minutes, for every offered model; then tightening each model's `cost_factor` (the Distil-Whisper and large-v3 factors are estimates) | A 4 GB dual-core Windows 10 computer and a person to listen |
| **A CI-runnable benchmark gate** (`dictbench.py` baseline mode): every engine offered must meet the speed budget on one thread on recorded speech | Recorded speech checked into a test-asset location, and a CI runner whose speed is stable enough to gate on |
| **Word biasing for the local models** (section 5 B; the plumbing is built and off, section 22, D-28) | A sherpa-onnx that encodes hotwords for mixed-case SentencePiece vocabularies, a hotword-capable Nemotron decoder, or an English Zipformer transducer measured on B-1 |
| **The shared layer's measurements** (section 22): keyword spotting (a false-trigger soak, the detection rate, CPU), hotwords on an English Zipformer, the punctuation and speaker models, and sherpa-onnx TTS against kokoro-onnx (D-30) | B-1, B-3 and the 8 GB machine (B-8) |
| **Per-context word lists switched on** (D-21; section 28): the lists are parsed and kept, but nothing names the active context | The named dictation profiles of D-23 |
| **A Whisper initial prompt for local biasing** (D-21; section 28): sherpa-onnx 1.13.8 has no prompt input for Whisper | A sherpa-onnx release that adds one |
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
the wake phrase is refused, and said once ("The wake phrase is not being
listened for", and who has the microphone) since 2026-10-27: a wake phrase
that silently never listened read as a broken one (QUILLVille report).

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
(Since 2026-10-15 it is empty and Dictation Status is shared: section 24.)

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

D-21 was planned beside these and was built on 2026-10-16; see section 28.

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

**Since done (2026-10-16, section 30).** The list and its two neighbours now
live in the family folder beside `family_dictation.json`, copied there on
first use with the old files left as the backup; QUILL Lite's "Use the shared
word list" points at the new place.

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

## 24. As built, 2026-10-15: the wake phrase and holding the key in QUILL Transcribe (D-9), and feedback where you work (D-6)

(Sections 22 and 23 belong to other items built the same night.)

**What was true.** QUILL Transcribe ran the editors' controller with two
shared settings forced off (`transcribe/parity.py` `PREFERENCES_OFF`: the wake
phrase and hold to talk), because its start and stop key is a `RegisterHotKey`
key, which reports the press and never the release, and because a wake phrase
heard while another program is in front could type into anything. Its preview
went to its own window's status bar, which nobody sees while working in
Outlook; Dictation Status was a parity divergence ("the window is its status");
and Resume, Resume in This Field and Discard Held Words (D-15,
`quill/ui/dictation_field_hold.py`) were window, menu and tray commands only.

**D-9, holding the key** (`quill/apps/transcribe_talk.py`, the wx-free half in
`quill/core/transcribe/talk.py`). The plan offered an optional low-level hook
for the one chosen key; it was not needed, and it was not built. The decision
is the editors' `HoldToTalk`; the host asks `GetAsyncKeyState` about that one
key (`quill/platform/windows/key_state.py`, with the virtual key from
`tray_hotkey.virtual_key`) every 40 ms, only while a press is followed, which
is how the editors already follow Ctrl+F11 with `wx.GetKeyState`. (wx's call
reads the thread's own key state, which does not change while another program
is in front, so it could not be reused.) No hook means nothing sees any other
key the person types, nothing can be timed out by `LowLevelHooksTimeout`, and
the key keeps going through the family picker and its conflict checks, which
require Ctrl or Alt (`show_hide_key_problem`). That requirement is the D-1
note on modifiers made concrete: a held Ctrl or Alt turns typed letters into
shortcuts, and `text_injector` waits two seconds for them and then refuses. So
the recogniser reports through `KeyHeldGate`: a phrase finished while the key
is down waits, and the waiting phrases are typed in order the moment the poll
sees the key up (or before `on_finished`, so a stop never loses one). The press
that stops dictation lets the last phrase through at once. Key repeats are
ignored while a press is followed, with the setting on or off, as in the
editors. Holding a Ctrl chord also silences most screen readers for as long
as it is held, so the guide recommends an Alt chord such as the default
Alt+Shift+Backslash; Insert and Caps Lock, the readers' own keys, cannot be
chosen at all because the picker needs Ctrl or Alt.

**D-9, the wake phrase.** The controller's STANDBY, unchanged. QUILL
Transcribe's window timer (every 800 ms) asks `_keep_wake_standby`: wanted only
when the setting is on, dictation could start at all (`_refusal`: Safe Mode,
the owner lock, the family microphone, the model), and the program in front is
another program that is neither a QUILL window (`window_handles_own_expansion`)
nor on the never-type list. QUILL Transcribe's own window and the editors are
excluded because the editors have their own dictation and wake phrase, and
standing down there lets go of the family microphone (D-11) so Ctrl+F11 works;
a password manager is excluded because a microphone open there is the worry
the plan names. The state line and tray name say "Listening for your wake
phrase", the setting being switched on is said once ("Listening for your wake
phrase whenever another program is in front. Nothing is written until it hears
it."), and a recogniser that will not open is reported once by the controller
and not retried until Dictation Settings is saved again. The shared Dictation
Settings window takes `help_for`, so F1 on the two check boxes describes QUILL
Transcribe's behaviour there (`transcribe_talk.HELP_FOR`). `PREFERENCES_OFF`
is now empty, and the parity test asserts both settings are honoured and both
default off in all three products.

**D-6.** The preview and the unspoken state changes (Command mode, Waiting for
a command, Listening for your wake phrase, and the change back from one of
them) go to braille only, through the announcement engine's braille-only call
(`prism_bridge.braille`), following `announcement_braille`. States that are
always spoken (on, off, paused) are not brailled a second time, so the display
is not overwritten by what the reader has just brailled from speech; the
preview is throttled by `PreviewThrottle` and `braille_output`'s two-second
duplicate rule. "Speak" preview now reaches Transcribe too (`say_quietly`).
Dictation Status moved from `DIVERGENCES` to `SHARED_COMMANDS` on the editors'
Alt+F9 (rule 2), and says one sentence (`talk.status_sentence`): the state, the
program the session is locked to (`foreground.window_process_name` on
`LockedTarget.locked_window()`, never the window title), the model and the
held count. Three optional system-wide keys, `status_hotkey`, `resume_hotkey`
and `discard_hotkey` (hotkey ids 0x51B3 to 0x51B5), are empty by default,
registered only once chosen, chosen in File > Dictation Status Key...
(Ctrl+Alt+Shift+A), Resume Key... (Ctrl+Alt+Shift+U) and Discard Held Words
Key... (Ctrl+Alt+Shift+Y) through `run_system_key_command` with every other
Transcribe key passed as `own`, and they run the window's own commands. What
D-15 already gave (the three commands, arming from the window) was not
rebuilt.

**Tests** (fakes only; no microphone, no key registered, the key's state a
flag): `tests/unit/apps/test_transcribe_talk.py` (holding, a quick press, the
setting off, repeats, the stopping press, words dropped on close, the gate in
front of the recogniser, the wake phrase off by default, standby and its state
line, nothing written before the phrase, back to standby on stop, where it
stands down, braille, Dictation Status, the three keys),
`tests/unit/core/test_transcribe_talk_core.py`, and the parity test.

**Still to check, with a microphone and a braille display.** Holding
Alt+Shift+Backslash in Notepad, Word and Outlook (that the release is seen and
nothing arrives as an Alt shortcut); the wake phrase with each engine in a
noisy room; JAWS and NVDA braille showing "Hearing: ..." in Outlook without
fighting the reader's own flash messages. They join
`docs/qa/screen-reader-checks-2026-10.md`.

## 23. As built, 2026-10-16: cloud dictation providers, your own account (D-31 to D-37)

The owner asked for "all dictation platforms, Microsoft, Google, Azure, etc",
each with the person entering only what that provider needs. Local dictation
stays the default and the recommendation.

**One layer (D-31).** A wx-free package, `quill/core/windows_dictation/cloud/`:

| Module | What it does |
|---|---|
| `types.py` | `CloudProvider` (id, name, company, console and privacy links, hosts, `last_checked`, `consent_version`), `ProviderField` (key, label, kind secret/text/choice/file, required, help, choices, validate), `Capabilities` (streaming, biasing limit and name, punctuation, languages, diarization, timestamps), the `LiveSession` shape |
| `errors.py` | `CloudSpeechError(CodedError)` and `-AUTH`, `-FIELD`, `-NETWORK`, `-QUOTA`, `-UNSUPPORTED`, `-CONSENT`, each carrying the field to check; network errors are not fatal (a phrase is lost, dictation keeps listening) |
| `transport.py` | the two certificate-checked openers (`urlopen`, `create_connection`) and `failure`, which turns any HTTP or socket failure into one sentence naming the field ("The key was refused. Check Key."), never the key or the body; `require_host` for an address that is the person's own resource |
| `ws_base.py` | one streaming session for every WebSocket provider: buffering to the provider's smallest block, keep-alive between phrases, provisional words to the preview, the phrase's final words at QUILL's pause |
| `credentials.py` | secrets in the credential store under `provider_credential_target("speech-<id>-<field>")`, a file field (Google's service account) DPAPI-protected in `speech-providers\` with only its path in settings, every loaded secret handed to `redaction.remember_secret` |
| `consent.py` | the consent question generated from the facts, `consented`, `start_problem` (Safe Mode, a missing part, a missing field, no consent), the "Speech goes to Azure, westeurope." line, `biasing_terms` (newest first, with a count left out) |
| `registry.py` | the list, in the page's order, and the `cloud-<id>` engine ids |
| `recognizer.py` | `CloudDictationRecognizer`, the same shape as `OpenAIDictationRecognizer`: the built-in engines' listening loop, only the recognising sent |

Settings: `windows_dictation_speech_providers` (provider id to its plain
fields; a field whose name looks secret is dropped on load) and
`windows_dictation_speech_provider_consent` (provider id to version), both in
`DictationSettings`, so QUILL, QUILL Lite, QUILL Transcribe and Quill Inkwell
share them. The one registration point outside the package is
`engines._cloud_engine`, which lets `coerce_engine`, `engine_info`,
`cloud_line` and `writes_punctuation` know a `cloud-` engine.

**The page.** `quill/ui/speech_providers_dialog.py`, reached from Dictation
Settings' **Speech Pro&viders...** (`quill/ui/windows_dictation_cloud.py`, a
mixin so the settings dialog stays under its cap) in all four apps: the
provider list (focused on open), About this provider, the fields built from
`fields()` with inline F1, Last result, and Test Connection, Save, Remove and
Close (no access key). A saved secret is never shown; Save stores secrets at
once and the plain fields with Dictation Settings' OK. Choosing a provider in
the engine list asks the generated consent; No is the default and restores the
engine. Test Connection is refused in Safe Mode.

**The providers, and what each takes.** All direct HTTPS or WebSocket; no SDK.

| Gap | Provider | Live | My Words | Test Connection |
|---|---|---|---|---|
| D-32 | Azure AI Speech (`azure.py`) | WebSocket (the Speech SDK's protocol); phrase mode through fast transcription | phrase list, 500 | `sts/v1.0/issueToken` |
| D-33 | Google Speech-to-Text v2, Chirp 3 (`google.py`) | No: REST `recognize` a phrase at a time; gRPC streaming is an optional pack, not built, and `streaming_pack_problem()` says so | adaptation phrases, 1,000 (verify) | list one recognizer |
| D-34 | Amazon Transcribe (`amazon.py`, `amazon_sigv4.py`, `amazon_eventstream.py`) | WebSocket, SigV4-presigned, event-stream frames | a vocabulary named in the person's account | signed `ListVocabularies` |
| D-35 | Deepgram, AssemblyAI, Speechmatics (`streaming_providers.py`); ElevenLabs Scribe, Gladia, Rev.ai (`streaming_more.py`) | WebSocket | keyterm 100; keyterms_prompt 100; additional_vocab; keyterms 50; custom vocabulary 100; Rev.ai a vocabulary ID | an account or list call each |
| D-36 | Groq, Mistral Voxtral (`rest_providers.py`) | No: one WAV per phrase | Whisper prompt; context_bias 100 | list models |
| D-37 | IBM Watson (`ibm.py`) | WebSocket, IAM token | a custom language model ID | list models |

OpenAI is described on the same interface (`openai_provider.py`, for the
list and Test Connection), but `OpenAIDictationRecognizer` still drives OpenAI
dictation and its consent stays `windows_dictation_openai_consent`: no change
in behaviour, which was the condition.

**Egress.** One reviewed entry per provider call site, in
`quill/tools/network_egress_entries_speech.py` (split out under GATE-11), 28 in
all. Every call site is a uniquely named function (`_probe_<id>`,
`_connect_<id>`, `_send_<id>`, `_token_<id>`, `_init_gladia`).

**Acceptance, as tested** (`tests/unit/core/test_dictation_cloud_*.py`,
`tests/unit/ui/test_speech_providers_dialog.py`, all against recorded fakes in
`tests/unit/core/cloud_speech_fakes.py`; nothing touches the network or the
real credential store):

- No secret in settings, logs or crash bundles: planted values, `save` and
  `values_for`, `redact_text_for_bundle`, and `load_fields` dropping
  secret-shaped names. Met.
- Test Connection never sends speech: every provider's test is a GET or an
  account call with no audio. Met.
- With consent declined, or in Safe Mode, no request is made. Met.
- A provider without streaming shows no live preview. Met.
- Losing the network never switches engines. Met.
- The page passes the dialog inventory, access key, F1 and reachability gates;
  it has no menu items, so no menu accelerators. Met.

**Not done, and why.**

- OpenAI's recogniser is not yet rebuilt on `CloudDictationRecognizer`; it is
  listed and tested through the interface only.
- Azure batch transcription for long recordings, and moving `azure_mai` from
  QUILL's file stack into the shared layer, are not built (D-32's file half).
- Google gRPC streaming (the optional pack) is not built.
- The "Speech goes to ..." line names the provider, not yet its region, in the
  tray and status key: `engines.cloud_line` has only the engine id.
  `consent.speech_line` has the region and is ready for that.
- The engine list in QUILL Transcribe's Choose Model window does not list cloud
  providers yet; Dictation Settings does.
- Nothing has been tried against a live account. Every protocol detail marked
  "verify" in the module docstrings needs a real key: Azure's WebSocket message
  shapes and request ids, ElevenLabs' realtime message names, Gladia's
  vocabulary intensity, Speechmatics' `additional_vocab`, Chirp 3's adaptation,
  Amazon's 8443 host signing and silence timeout, IBM's token lifetime on an
  open socket.

## 26. As built, 2026-10-16: the benchmark and test infrastructure (B-1 to B-8)

dict.md section 8 asked for the measurements every model decision waits on,
above all the retirements in its section 10. This builds the tools. It runs
no benchmark that needs a download, and it changes nothing a person using
QUILL sees. Everything is dev-only: in `scripts/` and `tests/`, never shipped,
never run by the app. Section 6's table still stands, and still flatters
every engine.

### B-1: the benchmark set

**B-1b, public datasets on demand.** `scripts/bench_datasets.json` names
every dataset in dict.md's table with its licence (and whether the licence
was verified), attribution, source, size, access, contamination and archive
URLs. `scripts/fetch_bench_audio.py` downloads only when a person runs it and
answers yes, never with `CI` set, and only from the hosts in its docstring (a
test holds the two to each other). Every archive is checked against a pinned
SHA-256 before it is unpacked, with tarfile's `data` filter so nothing lands
outside its folder. No hash is pinned yet: the first person to fetch a set
runs `--pin`, which records the hash for review and commit. Sets behind an
account or an agreement (Common Voice, CHiME, TORGO, the Speech Accessibility
Project and others) are never fetched: the script says where to ask, and
`--local PATH` registers a copy you have. UASpeech is marked not usable.

The cache is **outside the repository** (`QUILL_BENCH_AUDIO`, otherwise
`%LOCALAPPDATA%\QUILL-bench\bench-audio`), not dict.md's `build/bench-audio/`:
a path inside the repository is refused, so no audio can be committed by
accident. Fixed subsets live in `scripts/bench_subsets.json` (a seed, a count,
and a per-speaker cap); `--pin-subset` stores the chosen names once the data
is here.

**dictbench** (`scripts/dictbench.py`) gained `--dataset`, `--subset`,
`--group-by` (speaker, accent, gender, language, group, or `heldout`),
`--parse`, `--latency` and fuller JSON: the contamination flag
(`may_be_in_training_data`) for that model and set, the normalizer used, the
date, the limits sentence, and every group. The scoring is
`scripts/bench_scoring.py`: punctuation is aligned against the reference's own
marks, with precision, recall and F1 for the full stop, comma, question mark
and new paragraph, and the share of sentences starting with a capital. Quote
marks are not scored, and mostly-quoted segments are reported apart.

**B-1a, LibriVox held out.** `scripts/bench_librivox.py` reads the catalogue,
makes a seeded selection balanced across readers from books whose text is on
Project Gutenberg, downloads the chosen audio and texts (by a person), strips
the Gutenberg header, footer and every mention, finds LibriVox's spoken
preamble and closing by their words, and cuts each chapter into 5 to 20 second
utterances whose reference is the book's own text. It uses dict.md's fallback
aligner: an engine not under evaluation transcribes each voice-detected
stretch, and difflib matches its words to the book. Utterances under 0.9 word
match are dropped (words the book does not have count against them too), and
the kept share is reported per book and per reader. The aligner is recorded
in `aligner.txt`, and dictbench refuses to score that engine on the set. The
held-out dates are in `bench_datasets.json`: Whisper 2024-10-01 (an
assumption) and Moonshine 2024-10-21 (the paper); Parakeet, Nemotron, Vosk and
Canary have none yet, so nothing counts as held out for them until someone
fills in the dates dict.md names.

**B-1c, the command script.** `scripts/bench_commands.py` writes a script
from the command table (every whole-phrase command, the layout words, the D-8
inserts, commands after the command word, sentences with spoken punctuation,
and Spanish), reads it to files with Windows' voice, Kokoro or Piper (nothing
is played), and mixes it with MUSAN noise or recorded screen-reader speech at
chosen levels. `dictbench --parse` then reports how many commands parsed and
how many would have been typed. Its word errors are never accuracy.

**B-1d, volunteers.** Not recorded: it needs people, consent and payment.
`bench_datasets.json` has its row, and a recorded folder plugs in with
`--local` and a `speakers.tsv` whose `group` column carries the speech
difference, so `--group-by group` keeps each group apart.

### B-2 to B-8

- **B-2.** The tested-programs harness (section 17) now reads every phrase
  back even when QUILL said Windows did not take all of it, and counts whether
  QUILL's report agreed with what arrived: agreed, a false alarm, or a silent
  miss. A unit test drives that scoring against a fake field.
- **B-3.** `tests/stability/test_dictation_soak.py`, marked `slow`: recorded
  audio at live pace through the real recogniser and controller into the
  shared `ExternalDocument`, whose typing is a fake that never sends a key. It
  runs only with `QUILL_DICTATION_SOAK=1` and a folder of recordings, and is
  skipped whenever `CI` is set. It checks no lost or doubled phrase, no
  command typed, flat memory and a closed microphone. Its machinery
  (`scripts/bench_live.py`) has fast unit tests with a fake engine.
- **B-4.** `dictbench --latency` plays the recordings at live pace through the
  same recogniser and reports, per file and at p95, the time from the first
  speech to the state change and from the last speech to the text (the pause
  included), against the Transcribe targets of 0.5 and 2 seconds.
- **B-5.** `bench_live.correction_efficiency`: utterances spent per error
  corrected. A soak folder with a `corrections.json` reports it; run the same
  session once per correction method to compare before and after D-1, D-10
  and D-19.
- **B-6.** Six moments for QUILL Transcribe (start, stop, pause, refusal,
  command mode, review) on NVDA, JAWS and Narrator, in
  `docs/qa/screen-reader-checks-2026-10.md`.
- **B-7.** `tests/unit/core/test_dictation_privacy_paths.py`: a whole session
  with AI off makes no connection; held words are never on disk as plain text,
  and nothing is left in `recovery/live-dictation` once delivered (ready for
  D-5's Rescue); dictated words are not logged; and only the two download
  scripts of the benchmark import anything that could reach the network.
- **B-8.** `scripts/bench_machine_run.py` runs every model on this computer, each
  in its own process, on the chosen sets, and writes one JSON and one table
  with proposed cost factors and RAM tiers. It never edits the catalogue, and
  screen-reader lag stays a person's note.

**One hook in engine code.** `LocalDictationRecognizer._reader_gate()` is now a
method. The first live run here opened the process's real reader gate, which
captures the running screen reader's audio, and a phrase spoken while JAWS was
talking was silenced, exactly as the gate is meant to do. The benchmark's
recogniser now overrides the method with a gate that captures nothing, and a
test makes sure it never opens the real one.

### First run, 2026-10-16

Moonshine tiny, CPU only, on ten sentences and on the 54-line B-1c script,
read to files by Windows' default voice. Synthetic speech: these numbers check
the tools, not the engine (`docs/qa/dictbench-moonshine-tiny-2026-10-16.json`).

| Run | Result |
|---|---|
| Ten sentences, from files | 0% word errors, full stop, comma and question mark F1 1.0, 0.017 seconds of computing per second of speech, 208 MB, 1.2 s to load |
| The same at live pace | state change p95 0.27 s, text p95 0.92 s (the 0.8 s pause included), all ten phrases heard |
| B-1c command script | 44 of 49 commands parsed; "undo that" heard as "I'll do that." and "show clips" as "Shoe clips." would have been typed; "paste clip three" came back as "paste clip 3" and "insert abbreviation addr" as "address" |

The "paste clip 3" result is worth a look: the engine writes the number as a
digit, so a clip spoken by number may need the parser to accept digits.

### What section 10 can now measure, and what has to be run

Each retirement in dict.md section 10 is gated on B-1a, the relevant B-1b
sets, B-1c and B-8. The tools for all four exist now; the data does not. What
each one needs:

- **Vosk out of dictation** (merged in #1663, before these tools existed): its
  condition, Moonshine tiny measured on B-1a English (a held-out set built
  with Whisper as the aligner), B-1c and the B-8 run with a screen reader, is
  all measurable now, so it can be confirmed after the fact.
- **Duplicate Parakeet and Nemotron providers:** not a benchmark question
  (the same model files); measurable as before.
- **whisper.cpp as the default:** B-1 parity for sherpa-onnx Whisper or
  Parakeet. dictbench measures sherpa-onnx models only; whisper.cpp needs its
  own run through QUILL's Locked Dictation, so this one stays partly manual.
- **English-only Whisper and Distil-Whisper sizes:** measurable on B-1a
  (Whisper's date is set), LibriSpeech and FLEURS (flagged as contaminated
  where they are), B-1c and B-8, once each model is downloaded.
- **Vosk as the chapter engine:** not measured by these tools; it needs the
  reference chapter lists, as before.
- **Parakeet and Nemotron** have no training cutoff in the table, so nothing
  is held out for them until the dates are filled in.

To decide them, someone with the models downloaded runs, in order:
`fetch_bench_audio.py librispeech-test-clean --pin` and `fleurs-en --pin`
(then commits the hashes); `bench_librivox.py catalogue`, `select`, `fetch`
and `build` for English and Spanish; `bench_commands.py script`, `render` and
`mix`; and `bench_machine_run.py` on the 8 GB computer with NVDA or JAWS
running, then writes the results here.

**Still to do:** vendor Whisper's English normalizer under `scripts/` with its
licence (the scoring uses it when the `whisper_normalizer` package is present,
and QUILL's basic one otherwise); pin the first hashes; build and publish the
B-1a subset on assets-v1; record the volunteers (B-1d).

## 27. As built, 2026-10-16: replace, delete by paragraph, a second opinion, kept revisions (D-19), and correcting in other programs (D-10)

Both items were built together, in shared code, so QUILL, QUILL Lite, QUILL
Transcribe and Inkwell's Dictate Anywhere have the same commands with the same
rules. Section 18 left an empty slot (`COMMAND_MODE_PREFIX_HELP`) for these;
they joined the one command table instead (`vocabulary_commands.py`), which is
what makes them work after the command word and, with strict mode off, on
their own, and keeps "What can I say" and the published reference (regenerated
by `scripts/build_dictation_commands.py`) generated from one source. The slot
stays empty, with a comment saying why.

**The grammar.** Three new commands (`Command.REPLACE_WORDS`, `CHANGE_THAT`,
`DELETE_PARAGRAPH`):

| Say | What happens |
|---|---|
| replace X with Y | In QUILL's documents, the nearest X before the cursor (else after it, `targets.find_target`) becomes Y, with X's capital and closing mark; the cursor stays where it was. In another program, only inside the phrase dictated last, retyped from X on. Not found: written as text when said bare (as select does), nothing after the command word. |
| change that to Y | Y in place of the phrase dictated last, keeping its leading space, capital and closing mark; only the characters from the first difference on are retyped. |
| delete previous paragraph, delete last paragraph | From the start of the paragraph before the cursor (blank lines apart, as `select paragraph` counts them) up to the cursor, with the blank line in front of it. |

"delete that" already was a name for scratch that, and stays so.

**Correcting in another program (D-10,
`quill/core/windows_dictation/external_edits.py`).** Correct that and choose 1
to 3, caps that, uppercase that, lowercase that, replace, change that to,
delete last sentence and delete previous paragraph now work in QUILL
Transcribe and Dictate Anywhere (`anywhere.EXTERNAL_COMMANDS`), on the words
the session typed and nothing else: the external document answers from what
it typed (it has no way to read the other program), and each edit is a
backspace-and-retype pair through the same `send_text_checked` and
`send_backspaces_checked` path. Before any of them, and before scratch that,
`edit_problem` is asked, and refuses with one sentence when:

- the focus moved: the field lock (`LockedTarget.edit_problem`) or the
  external document's own focus identity says this is not the field the words
  went into;
- the person typed or clicked since (`OwnWordsGuard`): Windows says *when* it
  last saw a key or the mouse (`GetLastInputInfo`, in the new read-only
  `quill/platform/windows/input_activity.py`), never what it was. Input more
  than 300 ms after dictation's own last key or backspace means the cursor or
  the text may have moved. Mouse movement counts too, and so do the screen
  reader's own reading keys, because an arrow key moves the cursor and the
  guard cannot tell one key from another: refusing is safe, guessing is not;
- the program corrects as you type, for the commands that retype
  (`AUTOCORRECTING_PROGRAMS`: Word and Outlook, by file name). The plan asked
  for D-4 to probe them first; the harness has not had a clean run yet
  (section 17), so the default is the cautious one, and scratch that and the
  delete commands, which only take words away, still work there.

`ExternalDocument` takes the two checks as optional callables
(`last_input`, `program`); `locked_external_document`, which every host uses,
passes the real ones, and a document built without them skips those checks,
as before. The never-type list, the password field and the administrator
refusal are unchanged: they stop words going in at all.

**A second opinion (D-19's local alternates).** A model engine's phrase now
carries its own audio (`RecognizedPhrase.audio`, never compared or shown).
The controller keeps the audio of the last *written* phrase only, so the
"correct that" utterance does not replace it, and drops it at the next phrase
and at stop. "Correct that" with no list from the engine asks the
recogniser's `second_opinion` (`recognizer_worker.py`) to decode it again with
the other built-in engine (Whisper after Moonshine, Moonshine after Whisper or
a downloaded model; none for Spanish, where only multilingual Whisper hears it)
on a thread of its own, says "Listening again with Whisper.", and offers the
answer as choice 2 ("1: what was written. 2: what Whisper heard. Say choose
and the number."). An answer about a phrase that is no longer last is dropped
silently. The same answer is said as such. No disk, no network; the second
model loads on demand and unloads with the first. Windows speech recognition's
own list is used when it gives one, as before.

**Kept revisions.** Choose N, change that to and replace put the text they
replaced into Recent Phrases (Shift+F11) marked "(before correction)", with the
new text in front of it; Insert Again and Copy take the words without the label
(`corrections.phrase_from_entry`, in the one shared `open_recent_phrases`).
Memory only, like the rest of Recent Phrases.

**Where it lives.** `corrections.py` (`CorrectionsMixin`, first in the
controller's bases, so it is asked about every command before the rest) and
`external_edits.py`, both new and wx-free; the controller grew by two lines.

**Tests** (fakes only): `tests/unit/core/test_dictation_corrections.py` --
the grammar, replace before and after the cursor, scratch after a replace,
not-found bare and after the word, strict mode, change that, delete by
paragraph, the second opinion (asked, chosen, stale, the same answer), the
revision labels, and in another program: replace retyping from the words on
and only in the last phrase, caps and change and delete on own words, correct
that and choose retyping only the last phrase (never the words before it),
refusal after the focus moves and after typing with nothing sent, Word and
Outlook refusing choose and caps while scratch and delete last sentence work,
and the field lock's check; and the worker's `second_opinion` itself (its own
thread, the answer posted, a load failure posted as no answer). The external
document there is given only a typist, a backspacer and a focus identity, so
no edit can have read the target -- the spec's "a fake document that cannot be
read" acceptance test. 32 tests.

**How the spec's guard was met.** dict.md asked for edits "only while
`LockedTarget` confirms the same field and the remembered tail is unchanged in
length". Without reading the target the length cannot be measured; what can
change it is the person's own input, so the guard is the last-input time
instead, which is stricter (it also refuses after a mouse move or a reading
key). The memory risk D-19 named (600 MB) is met by decoding only on demand:
the second engine loads when "correct that" first asks and is released with
the rest by the idle unloader (`keep_up.py`).

**What the person sees and hears.** No new window, control or key: every
change is a spoken command, so there is no F1 text to add, and
`docs/f1-help-reference.md` is unchanged. The help line for "correct that" in
the one table now says the other engine listens again, and "change that to"
carries an example; both reach "What can I say", the Dictation Commands window
and the generated `dictation-commands.md` (QUILL and QUILL Lite) and the site's
dictation page. Sentences said: "Replaced X with Y.", "Changed to: ...",
"Deleted the paragraph: ...", "No paragraph before the cursor.", "Listening
again with Whisper.", "1: ... 2: ... Say choose and the number.", "The other
engine heard the same: ...", and the three refusals in `external_edits.py`.

**Documentation.** User guides: QUILL ("Replace and change that", the second
opinion under "Correct that", Recent Phrases), QUILL Lite (the same, plus the
command table), QUILL Transcribe ("Correcting in another program", with the
three refusals quoted) and Quill Inkwell ("Correcting the words dictation
typed"). Changelogs: QUILL (developer), QUILL Lite, QUILL Transcribe and
Inkwell (user). PRDs: QUILL, QUILL Lite, QUILL Transcribe's decision 13 and the
QUILL Transcribe specification's section 7.8. Inkwell has no Recent Phrases
window, so its guide does not mention the "(before correction)" entries.

**Still to check, with a microphone and the real programs.** Replace and
change that in Notepad, Edge and Chrome; whether `GetLastInputInfo` ever
counts dictation's own keys late enough to trip the 300 ms guard; how often
Whisper's second opinion is the better one; and, when D-4's harness has a clean
run, whether Word and Outlook can come off the autocorrecting list.

## 25. As built, 2026-10-16: never lose what was said (D-5), snippet blanks by voice (D-8), reading back more (D-18)

The rest of three items, in shared code. QUILL, QUILL Lite and QUILL Transcribe
have all of it; Quill Inkwell has D-8 and D-18, which are the controller's, and
not D-5's store (see "Not done").

### D-5: rescue, a reviewed transcript into a field, opt-in history

**What was true.** Held words were memory only (`target_hold.py`, 50 at most);
Recent Phrases was memory only (section 14); D-2 kept an open review in
`dictation-review.json` (section 19); QUILL Transcribe's Review Transcript
could copy, save or open a transcript but not type it; there was no history.

**The store** (`quill/core/windows_dictation/rescue.py`, wx-free).
`DictationKeep(data_dir, app)` writes **uncommitted text only** to
`recovery/live-dictation/<app>-<id>.json` under the host's data folder (the
editors: the folder of `dictation.md`, as D-2's review file; QUILL Transcribe:
its data folder, which is QUILL's), one file per entry, `write_json_atomic`,
schema 1, the words sealed with DPAPI (`protect_secret`, entropy
`quill-dictation-rescue`, so a blob from the credential store cannot be
replayed here or the other way). The app's slug is in the file name, so
QUILL and QUILL Transcribe sharing a folder never offer each other's words.
Words that cannot be sealed are not written: they stay in memory, exactly as
before. Nothing in either module logs the words. `keep_for` gives one store
per folder and app for the run.

**What is kept, and when it goes** (`rescue_mixin.py`, `RescueMixin` under
`TargetHoldMixin`, so the controller's base list did not change; the
controller grew by two lines, the `RecentPhrases` import and comment). Two
kinds. *Held*: every change to the held list (`_keep`, scratch while paused, a
resume that pauses again) rewrites one entry for that pause, the text composed
as it would have been written (`held_text`, which D-2's "review that" now uses
too). Resume and Discard Held Words delete it; "review that" deletes it
because the review's own file takes over. Stop, a failure and shut-down keep
it and start a new entry for the next pause; stopping says the plan's sentence
plus "They are kept in Recent Phrases." *Unwritten*: when the controller's
`_apply` raises for a dictated phrase (`command_mode_mixin._dictate`), its
text is kept before the session ends as it always did; QUILL Transcribe's
Insert Again keeps a phrase Windows only partly took. The host hands the store
over through the feedback port's optional `rescue()`, as `library()` and
`review()`.

**The start and the window** (`quill/ui/dictation_kept.py`). The plan named
the History and Review window (`dictation_history_dialog.py`) as the pattern.
What was built reuses **Recent Phrases** itself instead: it already had
Insert Again (into the document, or typed into the field in QUILL Transcribe
after the usual `LockedTarget` checks, waiting for a field from QUILL
Transcribe's own window, as `arming.py` does) and Copy, on Shift+F11 in all
three hosts, so no new command, chord or window was needed, and every F-key
chord free in both editors had a cost (Alt+Shift+F4 and Ctrl+Alt+F4 sit one
missed key from Alt+F4; Shift+F12 is Word's Save). The list is this session's
phrases, then "Not written" entries oldest first, then D-2's unfinished
review read from its own file (not copied: Insert and Discard clear it), then
the history newest first. `RecentPhrasesDialog` gained **Discard** (Alt+D;
says "Discarded.", because the reader announces the next row and not the
deletion) and **Clear History** (Alt+H, only while the history is on, a
No-default question). Insert Again deletes a kept entry only when the host's
`insert_again` returns `True`; QUILL Transcribe returns `None` while waiting
for a field, so a cancelled wait keeps the words. At start, one sentence
(`kept_at_start`): "N dictated phrases were not written last time and are
kept. Recent Phrases, Shift+F11, brings them back.", replacing D-2's notice
when both apply. QUILL Transcribe's exit question about held words is asked
only when they could not be kept (`held_on_disk`).

**A reviewed transcript into a field.** D-2 covers dictated words (Insert in
Review Dictation). For a recording, QUILL Transcribe's Review Transcript has
**Type into a Field** (Alt+F, first in the row): the selection, or all of it,
through `insert_recent_phrase`, so the wait, the field lock, the never-type
list and `send_text_checked` are the dictated phrase's. The editors open a
transcript as a document, where it needs no such button.

**History** (`windows_dictation_history_days`: 0, 1, 7 or 30; 0 by default;
`coerce_history_days`). More Dictation Settings, **Keep a dictation history**
(Alt+Y), in all four hosts' copy of the window. `RecentPhrases` (the
controller's `recent`, a `deque` subclass) tells `_remember` about every
phrase that reaches Recent Phrases, so editor review inserts count too. One
file per app, `dictation-history-<app>.json`, each phrase sealed, pruned to
its days on every write and read, capped at 2000. Off deletes it: at the next
phrase, at start and when Recent Phrases opens, so it also goes when another
copy of the settings turned it off. Text only; audio for replay stays
deferred (plan section 6). QUILL Transcribe's defaults leave it off, as the
editors'.

**Acceptance criteria.** *Killing the process while words are held loses
nothing*: `test_killing_the_process_while_words_are_held_loses_nothing` holds
two phrases and reads them back through a second store on the same folder with
no stop or shut-down. *With history off, nothing remains on disk after
delivery*: `test_with_history_off_nothing_remains_on_disk_after_delivery`
(a phrase written, words held and resumed, dictation stopped, and the folder
empty). *No transcript text in logs or crash bundles*:
`test_no_transcript_text_reaches_the_log_or_a_crash_bundle` captures every log
record at DEBUG through a session that writes, holds and fails, builds a real
diagnostic bundle from that log, and finds the words in neither; the files
themselves hold only sealed text (`test_the_words_on_disk_are_sealed`, and
once with DPAPI itself). Crash bundles carry logs and dumps only, never the
data folder (`crash_report.build_diagnostic_bundle`).

### D-8: spoken prompts for snippet blanks

**What was true.** Section 14's slice: snippets typed as one phrase with each
blank "[name]" and `${cursor}` dropped in other programs.

**What was built** (`quill/core/windows_dictation/snippet_fill.py`). The
libraries gain `snippet_body(name)`: QUILL Transcribe's and Quill Inkwell's
`AnywhereLibrary` (QUILL's `snippets.json`) and the editors' `DictationLibrary`
over the host's `_dictation_snippet_body` (QUILL's own library). QUILL Lite's
snippets are its abbreviations, which have no blanks, so it keeps the old path,
which QUILL also has: QUILL Lite is not ahead. `SnippetFillMixin` sits between
`ReviewMixin` and `VoiceCommandsMixin` and overrides `_insert_named`: one match
with a readable body and at least one `${input:x}` or `${choice:a|b}` starts a
fill. "Snippet Bug Report Template, 3 blanks. Say cancel to stop. Summary?";
a choice is "Choose NVDA, JAWS or Narrator.", answered by an option (the same
name matching as snippets, `match_names`) or "choose two" / "number two"; "Say
one of NVDA, JAWS or Narrator, or choose and a number." otherwise. "skip",
"scratch that" (or "go back") and "cancel" ("Snippet cancelled. Nothing was
typed."). `CommandModeMixin._dictate` hands every utterance to the fill first,
before the command word is looked for, so an answer is never typed and never
taken for a command; the command word is allowed before an answer and is not
part of it. An input answer is the phrase parsed and composed, so spoken
punctuation works in it. The last answer renders the body (`render_snippet`,
so `${date}` and `${time}` come from the local clock in the built path) and
goes through `_insert_text` as one phrase, one undo step and one "scratch
that"; when the field cannot be written it is held like any phrase, so D-5
keeps it. `${cursor}` moves the caret in the editors and is dropped
externally. The D-1 form "QUILL insert snippet X" is the command table's
existing argument form; nothing in the matcher changed. Stopping dictation
ends a fill. The published references say how blanks are asked for.

**Acceptance criteria.** *"QUILL insert snippet bug report" in Edge asks for
each field and types the filled text as one phrase*:
`test_quill_insert_snippet_asks_for_each_blank_and_types_once`, strict mode
on, through `ExternalDocument` whose injector records every keystroke: nothing
typed until the last answer, then one string. *Scratch that removes all of
it*: `test_scratch_that_removes_all_of_the_filled_snippet` (one backspace run
of the whole length).

### D-18: read back more than the last phrase

**What was true.** "read that" spoke `_last_spoken`, set only by a dictated
phrase, so after a snippet, clip or review insert it said the phrase before.

**What was built.** `_insert_text` sets `_last_spoken` to the whole insertion,
marks named when Say Punctuation Marks is on (`VoiceCommandsMixin._heard`);
the editors' review Insert calls `note_inserted`. The per-phrase read-back
still says "Snippet sign off", not three paragraphs. Three commands, editors
only (`Command.READ_SENTENCE`, `READ_PARAGRAPH`, `READ_SELECTION`, in the
command table and its Spanish twin): "read last sentence" (the sentence before
the cursor, back over spaces and line breaks, `targets.unit_bounds`), "read
last paragraph" / "read this paragraph", and "read selection" ("Nothing is
selected."). They are not `EXTERNAL_COMMANDS`, so another program answers with
the usual refusal; "read that" is, and reads only the session's own words.

**Tests** (fakes; no microphone, no real window): `tests/unit/core/test_dictation_rescue.py`,
`tests/unit/core/test_dictation_snippet_fill.py`,
`tests/unit/ui/test_dictation_kept_words.py` (the window, Discard, Clear
History, the start sentence, the setting, Type into a Field), and
`test_kept_words_history_and_snippet_prompts_are_one_thing_in_all_three` in
`tests/unit/ui/test_dictation_parity.py`.

**Not done, and why.** Quill Inkwell's held words stay in memory: it has no
Recent Phrases to offer them in, and writing words nobody can reach is worse
for privacy than not writing them; giving its feedback port a `rescue()` and a
window is the step. QUILL Transcribe's Type into a Field from a review that
waits for a field and is then cancelled does not count as delivered, so a kept
entry stays (by design). Audio retention is deferred. Still to check with a
microphone and a screen reader: the lines under "Dictation: rescue, history,
snippet blanks and reading back" in `docs/qa/screen-reader-checks-2026-10.md`.

## 28. As built, 2026-10-16: self-repair, named styles, learning from corrections, and opt-in polish (D-20, D-21)

dict.md section 4, the "Polish", "Learn" and "Modes" parts. Everything is in
the shared dictation package, so QUILL, QUILL Lite, QUILL Transcribe and Quill
Inkwell get it together (QUILL Lite is never ahead). Automatic AI clean-up of
every phrase stays declined, as section 5 D decided: nothing here sends a
phrase anywhere unless the person asks for that phrase and agrees.

### D-20. Self-repair

**Module.** `quill/core/windows_dictation/self_repair.py`, wx-free. The plan
put the rule in `options.py`; it got its own module because the rule, its word
lists and the style table together would have pushed `options.py` past its
size budget, and because the controller calls it at a different point (after
the My Words rewrite, so a name the engine misheard is corrected before the
repair looks at it).

**The rule.** `self_repair(phrase, names)` scans the recognised words for a
marker: "scratch that word", "no I mean", "I mean", "no", "sorry" (longest
first). It looks at exactly one word before and one word after, skipping
punctuation-only tokens. It repairs only when:

- the word before ends with nothing, a comma or a dash, never a full stop or a
  question mark ("Is it Thursday? No, Friday." is an answer, not a repair);
- the marker's last word does not end a sentence either;
- both words are of one kind: a day (with today, tomorrow, tonight and
  yesterday), a month (May and March only when capitalised, since "may" and
  "march" are verbs), a number (digits, or one number word), or a name from
  My Words' Vocabulary, matched without case.

It keeps the second word, drops the first and the marker, and carries a
capital across when the first word had one. A phrase holds at most eight
repairs (in practice one or two). `repair_text` is the same over plain text.

**False positives, tested** (`LEFT_ALONE` in the test file): "no, I don't think
so"; "Is it Thursday? No, Friday."; "I said no, Friday"; "I may, no, March";
"I mean it"; "sorry, Friday is out"; "Thursday, no"; "send it to Bob, no,
Maria" with Bob not in My Words; "two, no more"; "Friday. No, Saturday works
better".

**Where it runs.** `DictationController.on_phrase`, after fillers and the
rewrite, behind `DictationPreferences.self_repair`
(`windows_dictation_self_repair`, off). The transcript profile forces it off:
a transcript keeps what the speaker said. `profile.with_repair_names` fills
`repair_names` from `dictation.md` when it is on, in the editors
(`windows_dictation_commands.py`), Transcribe (`transcribe_dictation.py`) and
Inkwell (`inkwell_dictation.py`).

**The named styles.** `STYLE_CHOICES`, `STYLE_FIELDS` and `style_of` in the same
module. Each style is only a name for existing fields; nothing new is stored:

| Style | Remove fillers | Self-repair | Polish allowed | Review first |
|---|---|---|---|---|
| Verbatim | off | off | off | (unchanged) |
| Clean | on | on | off | (unchanged) |
| Polished (only with AI on) | on | on | on | on |

Any other mix shows as "Your own mix of the settings below", which changes
nothing when chosen. The chooser (**Dictation style**, Alt+Y) and **Fix it when
I correct myself** (Alt+X) are built by the new
`quill/ui/windows_dictation_style.py` (`DictationStyleMixin`) inside Dictation
Settings; `WindowsDictationDialog(ai_on=...)` decides whether Polished is
listed, and the editors and Transcribe pass `_review_ai_on()` (the review's AI
port reports no reason to refuse). The two Polished fields that live in More
Dictation Settings are held in the dialog's pending `_more` until OK. To keep
the window under 700 pixels on a 768-pixel screen, **After each phrase is
written, give me** moved to the right column, beside the other sounds.

### Polish my dictation (opt-in AI pass)

**What it is.** One fixed request, `review_session.POLISH_INSTRUCTION`: fix
punctuation, capital letters, spelling and obvious grammar slips only; keep
the words, meaning, order and tone; add or remove no ideas. It is sent through
`ReviewConversation.instruct`, so it inherits every D-2 guarantee unchanged:
the review's own consent question (No by default) before the first request,
the AI routes the review already uses (ChatGPT subscription or own key; never
the free allowance; off in Safe Mode), the words treated as data, the
two-sentence diff summary worked out locally, Undo Change, and nothing inserted
until Insert. It adds **no network call site**, so `network_egress_audit` is
unchanged.

**How it is reached.** Only with **Allow polishing my dictation with AI when I
ask** (`windows_dictation_polish`, off; Alt+G in More Dictation Settings):

- "QUILL polish that" / "QUILL polish it" (`Command.REVIEW_POLISH`, in
  `REVIEW_HELP`). With no review open, `ReviewMixin._polish_last` opens the
  last phrase in Review Dictation (as "review that" would) and then asks for
  the polish there; with one open, it polishes the words in it.
- **Polish** (Ctrl+P, access key P) in the Review Dictation window, built only
  when allowed and greyed when the AI is off.

With the setting off, the voice command says `POLISH_OFF` ("Polish my
dictation is off. Turn on Allow polishing my dictation with AI in More
Dictation Settings.") and sends nothing. It is never automatic: Polished as a
style allows it and sends dictation to review first, but each polish is still
asked for.

**Not shown in Quill Inkwell (decided by Jeff, 2026-10-17: "hide it").**
Inkwell types into other programs and has no Review Dictation, so the box did
nothing there. Inkwell's `edit_anywhere_settings` now opens
`WindowsDictationDialog(..., review=False)`, which passes `review=False` on to
`MoreDictationDialog`: the **Allow polishing my dictation with AI** box is not
built (`self.polish` is `None`) and `values()` leaves
`windows_dictation_polish` out, so the saved value, which the family store may
share with QUILL, is untouched. `DictationStyleMixin` follows the same flag:
with `_review` false it neither reads nor writes the polish and review-first
fields, so choosing Verbatim or Clean in Inkwell sets only the two check boxes
and cannot turn polishing off for QUILL. Every other box keeps its access key,
and Alt+G is simply unused in Inkwell's copy (GATE-14 holds in both shapes).
QUILL, QUILL Lite and QUILL Transcribe pass nothing and keep the box. Tests:
`tests/unit/ui/test_dictation_more_dialog.py` (the box is gone, the value is
kept, no access key repeats, Clean leaves polishing alone, Inkwell passes
`review=False`).

**Send dictation to review first, hidden the same way (todo 55, 2026-10-17).**
The review-first box (`windows_dictation_review_first`, Alt+V) did nothing in
Inkwell either: Dictate Anywhere types into the program in front and Inkwell
has no Review Dictation. With `review=False`, `MoreDictationDialog` now builds
neither box (`self.review_first` is `None` too) and `values()` leaves
`windows_dictation_review_first` out, so a True saved by QUILL and shared
through the family store survives Inkwell's OK. The style mixin already left
the field alone with `_review` false. Alt+V is unused in Inkwell's copy; the
editors keep both boxes and both keys. Tests: the same file, plus
`test_inkwell_keeps_a_saved_review_first_choice` (Verbatim and Clean both
leave a saved True alone).

### D-21. Learning from confirmed corrections

**Module.** `quill/core/windows_dictation/correction_learning.py`, wx-free;
`CorrectionLearningMixin` is mixed into the controller through `LiveMixin`.

**What counts.** A voice correction the person confirmed by making it:

- "correct that" then "choose N" (`LiveMixin._choose` calls `_note_correction`
  with the phrase before and after);
- "correct X" then the new words. `voice_commands._land` records X and where
  it starts; `LiveMixin._after_insert` counts the next phrase only if it was
  inserted at that place (`_learn_from_correcting`). Another target in between
  clears the record.

`replaced_span` reduces the change to one replaced span of up to four words a
side; additions, removals, case-only or punctuation-only changes and changes in
two places are not offers. `CorrectionLearner` counts pairs without case, in
memory, for this run only; the second identical pair is offered once, whatever
the answer.

**The offer.** "Add a correction: Ann becomes Anne?"

- **Editors:** `HostFeedback.confirm_correction` shows a Yes/No message box
  titled Add a Correction (No the default) from the new
  `quill/ui/windows_dictation_learn.py`, deferred with `wx.CallAfter` so it is
  not opened inside the recogniser callback. While it is up, the editors'
  "QUILL is no longer the window in front" check stands aside (`asking()`), so
  answering does not stop dictation.
- **QUILL Transcribe:** no window, because one would take the focus from the
  field. The question is spoken with "Say QUILL yes to add it, or QUILL no",
  and `CommandModeMixin` asks `_learn_answer` before any other command. It
  lapses after 30 seconds (`ANSWER_SECONDS`), so a later "yes" answers
  nothing. Since D-10 (section 27) "correct that" and "choose N" work on the
  session's own words in another program, and `CorrectionsMixin._choose` calls
  through to `LiveMixin._choose`, so a choice made there counts the same way;
  "correct X" still works only in QUILL's own documents.
- **A host with no word list** (no `words_path` on its feedback port) is never
  offered anything.

**Yes** adds `heard => written` to Corrections through `words_file`'s model
(`add_learned_correction`), the same model as My Words and Phrases and its
Import and Export (D-12), and says "Added: Ann becomes Anne. It is in My Words
and Phrases." A heard word that already has a correction is not overwritten;
the person is told so.

### D-21. Lists per context

`words_file.parse_words` reads `## Context: <name>` sections (words one a
line, corrections `heard => write`) into `WordsFile.contexts`, and
`render_words` writes them back, so My Words and Phrases' Save keeps them. The
general profile parser ignores those sections, so they never apply anywhere
else. `profile.context_profile(path, name)` and `rewriter(path, context=name)`
apply one context's list on top of the main lists, the context's correction
winning. **Nothing passes a context yet**: the named profiles of D-23 are not
built, so today the lists are stored and round-tripped but unused. When D-23
lands, its active profile name is the argument.

### D-21. Whisper initial prompt through sherpa-onnx: investigated, not possible on 1.13.8

Checked 2026-10-16 against the pinned sherpa-onnx 1.13.8 in the dev venv:
`OfflineRecognizer.from_whisper` takes encoder, decoder, tokens, language,
task, threads, decoding method, provider, tail paddings, timestamps and the
rule and homophone FST paths, and `OfflineWhisperModelConfig` exposes only
`encoder`, `decoder`, `language`, `task`, `tail_paddings` and the two
timestamp switches. There is no initial prompt (and no hotwords for Whisper),
so local biasing through a Whisper prompt cannot be done without a newer
sherpa-onnx or a different runtime. OpenAI dictation keeps using the
transcription `prompt` for the document's context (`contexts.py`). Revisit
when the pin moves.

### Accessibility

- Every new control has a label, an access key unique in its window (GATE-14:
  Alt+Y and Alt+X in Dictation Settings; Alt+G in More Dictation Settings;
  Alt+P on Polish), inline F1 help, and a keyboard route; Polish's Ctrl+P is in
  the window's accelerator table and its label.
- Spoken only what the reader does not say (GATE-13): the polish outcome and
  diff, the offer and its result, "Not added", and the refusals. The style
  chooser following the check boxes is a value change the reader reads when
  the chooser is reached.
- Nothing is changed or stored without the person: self-repair and polish are
  off by default, styles store nothing, and a learned correction needs a yes.

### Tests

`tests/unit/core/test_dictation_self_repair_and_learning.py` (the repair and
false-positive tables, the controller wiring, the transcript exclusion, the
styles, the learner, both offer routes, correct-X counting and its location
check, context lists, polish consent and undo, "polish that" from dictation,
the My Words names), `tests/unit/ui/test_dictation_review_frame.py` (the
Polish button only when allowed, greyed with AI off, by key and by voice) and
`tests/unit/ui/test_dictation_settings_dialog.py` (styles set the boxes,
Polished only with AI, Polished saves polish and review-first, the window fits
a small screen). All use fakes: no microphone, no network, no real window.

### What remains

- D-23 named profiles, which switch the context lists on.
- Spanish phrases for "polish that" and the yes/no answer: **drafted
  2026-10-17**, behind the development switch with the rest of the Spanish
  commands (section 9); waiting for the native-speaker pass. The other review
  commands are English only today, like the rest of D-2.
- Screen-reader passes of the Add a Correction box and the style chooser
  (`docs/qa/screen-reader-checks-2026-10.md`).
## 29. As built, 2026-10-16: named profiles (D-23), and lessons, practice and the recognition test (D-25)

dict.md section 4, "Modes" and "Coach". Both are shared capability: the
profiles are the controller's and work in QUILL, QUILL Lite and QUILL
Transcribe alike; the coaching is QUILL Transcribe's, because the editors
already had lessons and a document to practise in.

### D-23: named profiles and format-aware structure

**The profiles** (`quill/core/windows_dictation/profiles.py`, wx-free) are
Standard, Email, Document, Markdown, Chat, Coding and Verbatim, each a frozen
`NamedProfile`: an overlay of `pause`, `remove_fillers` and
`auto_punctuation` (None means "as Dictation Settings say") plus how it writes
structure, `markdown`, `formatted` or `plain`. **Standard is no overlay at
all**, structure `markdown`, and is the default, so nobody's dictation changed
on upgrade; dict.md named six profiles and this adds Standard as the zero
point, because a person needs a way back to "my settings as they are".

| Profile | Fillers | Punctuation | Pause | Structure |
|---|---|---|---|---|
| Standard | settings | settings | settings | markdown |
| Email | removed | added | settings | formatted |
| Document | settings | settings | settings | formatted |
| Markdown | settings | settings | settings | markdown |
| Chat | removed | settings | settings | plain |
| Coding | removed | off | long | markdown |
| Verbatim | kept | settings | settings | plain |

**With section 28's named styles.** A style (Verbatim, Clean, Polished) is
only a name for existing fields in Dictation Settings; a profile is an overlay
applied after those fields are read. So while a profile other than Standard is
on, its `remove_fillers` wins over the style's (Verbatim profile keeps fillers
under the Clean style; Email, Chat and Coding remove them under the Verbatim
style). No profile touches self-repair, polish or review-first, and Standard
overlays nothing, so the style stands as chosen. The two names Verbatim are
consistent: both keep every word.

`DictationPreferences._writing` applies the overlay after reading the settings
(`_as_set`), and records `named_profile`, `structure` and `profile_locked`.
The "Talking to AI" and live-transcript profiles are applied on top, as before,
so a named profile never changes the AI message box or a transcript. Two
settings, under one name in every app (`settings_fields.py`):
`windows_dictation_profile` (cleaned by `coerce_profile`, unknown values fall
back to Standard) and `windows_dictation_profile_locked`. Both are additive:
`data_format_audit` recorded `quill.settings` and `lite.settings` as additive
and compatible, because an older build's loader ignores names it does not know.

**What a profile does to writing** is `profile_mixin.py`'s `ProfileMixin`,
listed first among the controller's bases so `controller.py` (at its size
ceiling) grew by two lines. It wraps four hooks of the voice-command mixins:

- `_in_mode`: a heading mark at the start of a phrase. `markdown` types
  `## ` as it always has. `formatted` and `plain` turn the mark into a bare
  line start and remember the level.
- `_after_phrase`: for `formatted`, the editor's own heading command over the
  phrase just written (the document port's optional `formatting()` and
  `apply_style(style, start, end)`), or, where there is none, nothing typed
  and `HEADING_REFUSAL` said and shown: "Headings work in QUILL documents or
  the Markdown profile." (dict.md's sentence). `plain` says nothing: the words
  on their own line are what Chat asked for.
- `_voice_command`: "bold that" and "italic that"/"italicize that"
  (`Command.BOLD_THAT`, `ITALIC_THAT`, new in `vocabulary_types.py`) act on the
  selection, or the last intact phrase. `markdown` wraps the words in `**` or
  `*` (keeping surrounding spaces outside the marks) as one replace, and
  updates the history so "scratch that" removes the formatted phrase;
  `formatted` runs the editor's own Bold or Italic; `plain` says
  `PLAIN_REFUSAL`. dict.md said "there are no bold or italic voice commands";
  now there are, because a format-aware profile with no way to format a word
  would have been half a feature.
- `_mode_command`: the seven profile commands ("QUILL email mode", "email
  profile", ...). Refused out loud while Lock Profile is on; otherwise kept
  through the feedback port's optional `set_dictation_profile`, and "Email
  profile." said once. A host without that hook says where to choose one.

**The editors' half.** `EditorDocument.formatting()` and `apply_style()`
(`windows_dictation_ports.py`) select the range and ask the host. QUILL
(`main_frame_windows_dictation.py`) answers `rich` in a rich text document and
the markup surface (`markdown`, `html`) otherwise, and runs
`format.bold`/`format.italic`/`format.heading_N` through its own command
registry; rich text speaks its own outcome, markup does not, so the mixin
says "Heading 2." there. QUILL Lite (`lite_window_dictation.py`) formats only
a rich text document, through its own `cmd_bold`, `cmd_italic` and
`cmd_heading_N`. A live transcript (`background`) is never formatted. The
choice is in More Dictation Settings (`dictation_more_dialog.py`: Dictation
profile, Alt+A; Lock, Alt+B), shared by all three apps.

**QUILL Transcribe's half.** The profile commands and bold and italic are in
`anywhere.EXTERNAL_COMMANDS`, so they work in other programs: Markdown and
Coding retype the session's own last phrase with marks (the same
backspace-and-retype as "capitalize that"; the other program's text is never
read); Document and Email say why nothing was formatted. The choice is also in
Dictation > Dictation Profile... (Ctrl+Shift+F, `ProfileDialog` in
`transcribe_coach.py`), the tray menu (Dictation Pr&ofile...), and Dictation >
Lock Profile (Ctrl+Shift+L, a check item). The profile shows in the window's
Model and microphone field, a third tray read-out, the tray icon's name and
Dictation Status (only when it is not Standard, the last three).

**Not done, on purpose.** Automatic switching per program stays out (dict.md
section 6; PRD 7.6 needs a privacy review first). A word list per profile is
D-21's: `NamedProfile.word_list` and `active_profile_name(settings)` are the
API it will read. QUILL has no separate menu row for the profile: More
Dictation Settings and the voice command are its routes, as for every other
dictation setting.

### D-25: lessons, a practice field and a recognition test

**Practice Dictation** (`quill/apps/transcribe_practice.py`, Dictation >
Practice Dictation..., Ctrl+Shift+P) is a modeless window: the sentence to
read, the **practice field**, the result, and Start Dictation Here (Alt+H),
Read This Sentence (Alt+T), Score the Field (Alt+S), Next Sentence (Alt+N) and
Close (Escape; no access key, GATE-14). Ctrl+F11 in the window starts and stops
dictation in the field. Its F1 purpose is in `core/transcribe/surface_help.py`
and every control has inline help (GATE-TRANSCRIBE-HELP).

**The own-window refusal, and its one exception.** A start from QUILL
Transcribe's own window normally arms and waits for another program. Start
Dictation Here instead runs the same refusals as any start (`_refusal`: Safe
Mode, the owner lock, the family microphone, the model), then points the shared
controller at `PracticeFieldDocument` -- `ReviewBoxDocument`'s editor-style
port over the field, one undo step a phrase, never keystrokes, and
`formatting()` empty so it behaves like Notepad for profiles -- and starts it.
`review_retarget` does the switch, the same seam Review Dictation uses. Any
stop, by any route, goes back to the locked-field document
(`_practice_state_changed`, called from `_dictation_state_changed`); so does
closing the window. A session already running in another program is never
taken over: "Stop it first".

**The recognition test.** `quill/core/transcribe/practice.py` holds eight
plain sentences (a name, a number and a question among them) and `score()`.
The scorer is `quill/core/windows_dictation/word_errors.py`, moved out of
`scripts/dictbench.py`, which now imports it: one word-error count for the
benchmark and the window, so a number means the same in both. Capitals and
punctuation do not count. Read This Sentence clears the field, starts dictation
there if it is off, and scores the **first phrase written** (the feedback
port's `phrase_written`), said once after the read-back and kept in Result;
Score the Field scores the whole field for a sentence said in two breaths.
Below 80 percent it suggests speaking slower, moving closer, or a larger model.

**Five lessons** (`quill/core/tutorials/transcribe_lessons.py`): your first
dictation in the Practice window, pause and resume in another program,
commands with the command word, snippets and clips, and review. They are kept
beside the editors' `dictation_lessons.py`, not in it, because they name QUILL
Transcribe's commands. `quill/core/transcribe/tutorials.py` is the catalogue
and the one small command table (`LOCAL_COMMANDS`: lesson id, frame method,
key) that the menu, Try It and the book all read. Help > Tutorials...
(Ctrl+Alt+F1) opens the family's Tutorials window through a small adapter
(`_LessonHost`) that answers `commands.get/run` and `_binding_for` from that
table, since QUILL Transcribe has no command registry. The book is generated
into `standalone/transcribe/docs/tutorials.md` (GATE-TUTDOC now has six apps).

**Acceptance.** dict.md's criterion, a new user reaching a first successful
dictation from setup without sighted help, is a screen-reader check and is
added to the D-4 passes; it is not claimed here.

### Tests

`tests/unit/core/test_dictation_profiles.py` (overlay, cleaning, structure per
profile, bold and italic, voice switching and the lock, the reference),
`tests/unit/apps/test_transcribe_coach.py` (practice field written directly
and never another program, refusals, restore on stop and on close, the test's
score said once, Score the Field, the profile window and lock, the lesson host,
menu keys against the lesson table, F1 titles and inline help, reachability)
and `tests/unit/ui/test_dictation_formatting_hooks.py` (QUILL's and QUILL
Lite's formatting hooks and the editor port).
## 30. As built, 2026-10-16: one dictation settings store (D-13), the word list's new home, and Dictate Here in Cast and Radio (D-16)

Three pieces, one change: the family's dictation settings are one store that
every program writes and reads; the family's word list moves beside it, in
`%LOCALAPPDATA%\QuillVille\Dictation`; and Quill Cast and Quill Radio can ask
QUILL Transcribe to dictate into the field you are in. Section 20's "Not
done, and where D-13 picks up" is what this closes.

### 30.1 The family folder

`family_dictation_dir()` (`quill/core/windows_dictation/family_store.py`) is
the one answer to "where", for both files:

| Copy | Folder |
|---|---|
| Installed (QUILL, QUILL Lite, QUILL Transcribe, Quill Inkwell) | `%LOCALAPPDATA%\QuillVille\Dictation`, the speech models' folder |
| Portable QUILL or a portable family bundle | the `dictation` folder in the bundle's own `data` folder |
| Portable QUILL Lite | the `dictation` folder beside its own portable data |
| Developer build with `QUILL_DATA_DIR` | `QuillVille\Dictation` inside that folder |

A portable copy never writes to the host and shares only with programs in its
own bundle, the rule D-12 set ("portable keeps its own"). The test suite gives
every test its own folder (`tests/conftest.py`, `_family_dictation_of_its_own`),
so no test reads the developer's words or settings.

### 30.2 One settings store, both directions (D-13)

**Before.** QUILL Transcribe and Quill Inkwell each kept a copy of the
dictation settings, refreshed only when an editor handed its own over
(`anywhere.write_handoff`, Dictate in Other Programs). A model chosen in QUILL
Transcribe never reached QUILL; one chosen in QUILL Lite reached QUILL
Transcribe only through that button.

**Now.** `family_dictation.json` holds every `windows_dictation_*` field in
`SHARED_FIELDS`: all of `DictationSettings` except `FAMILY_LOCAL_FIELDS`
(`settings_fields.py`).

- **Written** when Dictation Settings is saved (OK) in any of the four
  programs, and when Switch Dictation Language or one of QUILL Transcribe's
  Dictation menu toggles saves, by `publish_fields`, through
  `core.storage.write_json_atomic`. The file carries `schema` (1),
  `written_by` and `dictation`; fields a newer build wrote and this one does
  not know are kept on every write.
- **Read** when a program meets the person again: QUILL and QUILL Lite when
  their window is activated (`windows_dictation_commands.py`,
  `_dictation_take_family`); QUILL Transcribe on its 800 ms clock, one `stat`
  each time and a read only when the file's time or size changed
  (`take_family_dictation`, with its own write's stamp remembered so its own
  save is not news); Quill Inkwell, which has no window to activate, whenever
  its settings are used (a start, or Dictation Settings opening). What the
  file holds replaces the program's own values for the shared fields only.
- **Said quietly.** An editor says "Dictation settings updated from the
  family." in the status bar; nothing is announced, because the change is the
  person's own, made in another program a moment ago (GATE-13's spirit).
  QUILL Transcribe and Inkwell take it silently.
- **Not shared** (`FAMILY_LOCAL_FIELDS`): the share choice itself; the working
  tick and strict mode, which QUILL Transcribe sets on deliberately; what you
  hear after each phrase, which Inkwell starts as a tone because the screen
  reader echoes the typing; the one-time transcript sentence; and every
  consent (OpenAI, review, speech providers), because agreeing to send speech
  somewhere from one program is not agreeing for another. Keys, the tray and
  QUILL Transcribe's own options were never dictation settings and stay where
  they are.

**The setting.** "Share dictation settings with every QuillVille program" is a check box in
More Dictation Settings (`dictation_more_dialog.py`, Alt+A, with inline F1
help), stored as `windows_dictation_share_family`. It is a text, `"on"`,
`"off"` or empty, not a bool, because QUILL Lite saves only what differs from
the default and must keep a decision either way.

- **Default.** Empty means undecided, and an undecided program shares only
  while every shared setting is still the default (`shares_by_default`): a
  new install, which has nothing to lose. A program whose settings the person
  had changed loads as `"off"`, so an upgrade never swaps somebody's choices
  for another program's behind their back; they turn it on to join. dict.md
  asked for "on by default for new installs", and this is that, made safe for
  upgrades.
- **Decided before the first change.** `settle_share` fixes the choice just
  before Dictation Settings, Switch Dictation Language or one of QUILL
  Transcribe's own menu toggles changes a shared field. Without it the change
  itself would make the settings non-default and turn an undecided "on" into
  "off" at the moment the person expected it to be shared.
- **A hand-off keeps the choice.** Dictate in Other Programs still hands an
  editor's settings over (`take_handoff`), but the receiving program keeps
  its own `windows_dictation_share_family`.

**Never loses a setting.** The first time a program takes values from the
family, its own shared values are written to `before-sharing-<app>.json` in
the family folder, once, and never overwritten. If that copy cannot be
written, nothing is taken (`adopt_fields` returns `None`).

**Failure to write is reported, not hidden.** `publish_fields` raises
`FamilyDictationError` (`QUILL-DICTATION-FAMILY-WRITE`) with a sentence, and
each program says it after its own save: "Saved here, but the other QuillVille
programs will not see this change: the shared dictation settings could not be
written (Access is denied)." The program's own copy *was* saved, so the
sentence says exactly what did not happen. The editors say it through
`_dictation_say`; QUILL Transcribe and Inkwell through `_announce`.

**Contention.** None to manage: each write is a whole file put in place by an
atomic replace, so two programs saving at once leave one complete file, the
last one saved. The check box's F1 help says so, as dict.md asked.

### 30.3 The word list moves to the family folder (D-12, finished)

`default_profile_path()` (`dictation_profile.py`) now returns
`family_profile_path(app_data_dir())` (`family_words.py`). Every reader keys
off that one function: QUILL's dictation and Locked Dictation, QUILL
Transcribe's rewriter, review and file transcription, Quill Inkwell, the
command-word check, and QUILL Lite's "Use the shared word list". The two
neighbours, `dictation-instructions.md` and `dictation-contexts.json`, follow
the list because they are found beside it.

The migration, in order of what matters:

1. **Copied, never moved.** The first time anything asks for the list, each of
   the three files in QUILL's old data folder (`%APPDATA%\Quill`, the folder
   the person chose, or the portable `data` folder) is copied to the family
   folder if the family folder has none, byte for byte
   (`write_bytes_atomic`, then the old file's times). The old files are left
   exactly as they were: they are the backup, and an older build still finds
   them. Nothing is deleted.
2. **The family list is never overwritten.** If the family folder already has
   a list, the old one is not copied over it.
3. **Words added later in the old place are merged.** Each old file's time
   and size are recorded in `family-words-moved.json`. If the old list
   changes afterwards (an older build still running, or a second copy whose
   data folder is elsewhere), its new entries are added the way Import adds
   them (`words_exchange.plan_merge`, so where the two differ, the family's is
   kept), after the family list is copied to `dictation-before-merge.md`.
   Instructions and contexts are copied only while the family has none.
4. **Read through the old place until the copy exists.** If the copy fails (a
   full disk, a folder the person cannot write), the old file's path is
   returned, so the list never looks empty, and the reason goes to the log;
   the copy is tried again the next time.
5. **Cheap when nothing changed.** The list is asked for on every phrase in
   some hosts, so a call that finds nothing new writes nothing, not even the
   record.

`share_quill_dictation_words` in QUILL Lite is unchanged in meaning ("use the
family's list"); it now points at the new place. It was not retired, because
a QUILL Lite person who never chose the shared list keeps their own list, as
D-12 promised.

**data_format_audit.** `windows_dictation_share_family` is a new field in both
`quill.settings` and `lite.settings`, recorded as additive, compatible: older
builds ignore it, and an older QUILL Lite forgets it when it saves, after
which this build decides it again from the settings. `family_dictation.json`
is not a registered format: it carries its own `schema`, keeps unknown
fields, and an older build simply does not read it.

### 30.4 Dictate Here in Quill Cast and Quill Radio (D-16)

dict.md asked for a "Dictate Here" item in each app's Tools menu. Neither app
has a Tools menu, and both have the shared Edit menu
(`support_menu.insert_edit_menu`), so it is **Edit > Dictate Here**:
dictating is putting text into a field, which is what Edit is for, and adding
a one-item top-level menu to two dense menu bars would cost every listener an
Alt+Right on every visit. One wiring serves both apps.

- **Key:** `app.dictate_here` on **Ctrl+F11** in `APP_KEYMAPS["cast"]` and
  `APP_KEYMAPS["radio"]`, the editors' Start Dictation key, for the same verb
  (family rule 2). It was free on both bars (Radio's plain F11 is Full Screen
  in the video window). The label comes from `_menu_label`, so it follows a
  rebinding. Access key D, free in that menu.
- **The key in a dialog, too.** The search boxes people dictate into most,
  Cast's Add Podcast and Search Everywhere and Radio's Search Stations, are
  modal dialogs, where Windows never consults the main window's menu
  accelerators. So registering the command also installs one
  `wx.EventFilter` (`dictate_here_ui._DialogKeyFilter`) that answers the same
  key, as bound now, in a text field of any *other* window of the app. In the
  main window the accelerator answers and the filter steps aside, so the key
  never fires twice; it is removed when the frame is destroyed.
- **Shown only where QUILL Transcribe may be offered**
  (`dictate_here_ui.dictate_here_available`, `is_app_released("transcribe")`):
  a public build without QUILL Transcribe would otherwise advertise a key whose
  only answer is "not installed".
- **What it does** (`quill/core/windows_dictation/dictate_here.py`, wx-free):
  - QUILL Transcribe owns Dictate Anywhere (it is running): a `start` request
    through `dictation_owner.send_request`, sender `cast` or `radio`.
    `dictation_owner.SENDERS` now admits the two; `APPS`, who may *own*
    Dictate Anywhere, does not. QUILL Transcribe answers within a second, as
    if its own key had been pressed, in the field that has the focus, which is
    the field the person pressed Ctrl+F11 in, since an accelerator never moves
    the focus. Cast and Radio say nothing: QUILL Transcribe says "Dictation on"
    itself, and saying it twice is GATE-13's failure.
  - Quill Inkwell owns it (it is dictating): nothing is sent, and the busy
    sentence names Inkwell.
  - Nobody owns it: QUILL Transcribe is launched with `--tray --dictate-here`
    and the app says "Starting QUILL Transcribe. Dictation starts here when it
    is ready." QUILL Transcribe's `dictate_here_at_launch` then starts, unless
    its window is open (first run, or no tray: then the focused field is its
    own), in Safe Mode, or when Inkwell holds the lock.
  - No QUILL Transcribe to launch: "Dictate Here needs QUILL Transcribe, which
    is not installed with this copy."
- **No engine in Cast or Radio.** The words, commands, never-type list and
  field lock are QUILL Transcribe's, so "the same commands and words work in
  Cast's search box" (D-16's acceptance) holds by construction.
- **F1 and keys.** No new control, so no new help text; the command is in the
  command palette and Keyboard Shortcuts through `try_register`
  (`feature_id="core.app"`), and the keyboard reference is regenerated.

### 30.5 Tests

- `tests/unit/core/test_family_dictation_store.py`: both directions, the local
  fields, sharing off, the upgrade-safe default, `settle_share`, the one-time
  backup and refusing to adopt without it, a failed write raising a coded
  sentence, unknown fields kept, an unreadable file.
- `tests/unit/core/test_family_words_move.py`: the three files copied byte for
  byte with the old ones untouched, no writes on a second ask, the family list
  never overwritten, later words merged with `dictation-before-merge.md`, the
  read-through when the copy fails and the retry, `default_profile_path`.
- `tests/unit/ui/test_family_dictation_hosts.py`: QUILL to QUILL Lite, QUILL
  Transcribe to an editor and back, Transcribe's own write not news, and the
  write failure said in an editor, in QUILL Transcribe and in Inkwell.
- `tests/unit/core/test_dictate_here.py` and
  `tests/unit/ui/test_dictate_here_menu.py`: every outcome with fakes, the
  release gate, the request file's senders, the Edit menu label and key in
  both apps, Quill Radio's real menu bar carrying Ctrl+F11 once in a
  public build (a developer build before 2026-10-16), and QUILL Transcribe's `dictate_here_at_launch` in each
  case. No real window is driven.

### 30.6 Not done

- A screen-reader pass with JAWS and NVDA on Cast's search box and Radio's
  Search Stations box (D-16's acceptance in practice).
- ~~QUILL Transcribe is not yet in `RELEASED_APPS`.~~ Done on 2026-10-16 (Jeff's
  decisions on todo P2 item 19): it is in `RELEASED_APPS` on the branch, with a
  release date of 2026-11-01, so public Cast and Radio builds show Dictate
  Here; it is last in `QUILLVILLE_APP_ORDER` and in the tray list
  (`TRAY_APP_ORDER`), and the companion-install offer covers it. No sixth
  QuillVille launcher key: public menus show at most five rows, and only a
  developer build shows keyless rows past the fifth (`app_keymaps.py`, beside
  `SIBLING_APP_ACCELERATORS`). Nothing has been tagged or published. The
  screen-reader pass in Outlook, Word, Notepad and the browsers is Jeff's and
  is a release blocker (`docs/qa/screen-reader-checks-2026-10.md`).
- A "Restore my settings from before sharing" command over
  `before-sharing-<app>.json`; today that file is restored by hand.

## 31. As built, 2026-10-16: the small items checked, and the streaming contract in use

dict.md section 9 asks what the small items alone would bring. This pass
checked every one against this record and the code, built what was left, and
closed Jeff's todo about `StreamAnnouncer` (dict.md section 4, "Streaming
integration").

### The small items, one by one

| Item | State | Where |
|---|---|---|
| D-6 braille preview and the status, resume and discard keys | Already built | Section 24 |
| D-15 Inkwell pauses when the focus moves | Already built | Section 15 |
| D-16 Dictate Here in Cast and Radio | Built | Section 30 |
| D-18 read last sentence, paragraph, selection | Built in section 25; two additions folded in here | Section 25, and "D-18 additions" below |
| D-22 recommended model and tier labels | Already built | Section 21 |
| D-24 the never-type list and the cloud line in the tray | Already built | Section 15 |
| D-3 opt-in fallback for one program | Waits, as planned | It needs a clean D-4 run on an idle computer (section 17), and none has found a program that drops keys |
| D-4 slice, the tested-programs table | Already built, and more (the harness) | Section 17. The table fills in when someone runs the harness on an idle computer |
| D-12 slice, Import and Export | Already built, and the shared list | Section 20 |
| D-19 slice, replace and delete paragraph | Built | Section 27 |
| D-21 slice, the offer after two corrections | Built | Section 28 |
| D-25 slice, five Transcribe lessons | Built | Section 29 |
| B-6 screen-reader rows for Transcribe | Already built (the rows; the checking is a person's) | Section 26 |
| B-7 privacy tests for the new paths | Already built | Section 26 |
| D-26 S0 benchmarks for candidate models | The tools are built; the runs need the data | Section 26 |
| Streaming partials through the committed-and-tentative contract | **Built here** | Below |
| "paste clip 3" scored as slot three by the benchmark | **Fixed here** | Below |

dict.md section 4's "Listen", "Phrases" and "Privacy" have nothing small left
beyond D-18 and D-24.

### D-18 additions

D-18 itself is section 25's (one implementation; this branch's duplicate was
dropped at the merge). Two things this pass had that section 25 lacked were
folded into that code rather than kept beside it:

- **A read-only document can be read back.** The three reading commands are
  answered in `VoiceCommandsMixin._mode_command`, before the controller's
  writing check, because reading writes nothing; they used to be refused with
  "This document is read-only". In another program they are still refused
  there, with `external_refusal()`. `controller.py` did not grow.
- **"leer" as well as "lee"** in the Spanish forms ("leer la última frase",
  "leer el último párrafo", "leer la selección").

The QUILL user guide gained "More about reading back" beside section 25's
worked example; QUILL Lite's guide, which had the commands only as table rows,
gained a worked example ("Checking your work by ear"). The PRD has a D-18
requirement block.

### The streaming contract, now in use

`quill/core/speech/streaming.py` (2026-08-17) defined `StreamAnnouncer`
"ahead of need": a streaming snapshot is an append-only committed prefix and a
tentative tail, and speech says only newly committed text, exactly once. Then
the streaming engines landed (section 3, Nemotron; OpenAI live; the WebSocket
cloud providers, section 23) and none used it. dict.md D-26 ("Streaming
integration") and D-35 say partial results from any online recogniser go
through `preview.py` and that contract, and that only committed words are ever
spoken or written. The spec keeps the class, so it was wired, not removed.

**What was wrong.** With **Show it, and say new words quietly**,
`PreviewThrottle.to_speak` said again from wherever the engine changed its
mind: "call doctor" then "call Dr. Okonkwo" spoke "Dr. Okonkwo" after
"doctor", the same words twice in different forms, which is exactly the
repainting the contract exists to stop.

**What it does now.** None of the engines hands QUILL a committed and a
tentative part: each sends the whole phrase so far. So
`streaming.WordAgreement` derives the split by local agreement: a word is
committed once two updates in a row agree on it (case and edge punctuation
ignored) and it is not the last word, which may still be half heard. Its
committed text only grows, by construction, so a later rewrite of a word
already said is never said again. `to_speak` feeds each update through
`WordAgreement` and `StreamAnnouncer`, gathers what is newly committed, and
still says it no more often than every two seconds. Everything reaches it the
same way (`recognizer_worker` and the cloud recogniser post `on_partial`;
`LiveMixin.on_partial` decides), so Nemotron, OpenAI and every streaming cloud
provider follow the contract with no change in any engine.

**What stays as it was.** The visual preview, "Hearing: ..." in the status bar
and on a braille display, still shows the whole phrase, tentative tail
included: it is one line replaced in place, not a stream of announcements,
and dict.md D-6 asks for it. The words written at the pause are always the
engine's final ones; the spoken preview never decides what is written.

**The cost.** Speech now lags the engine by one update (a word is said once a
second update confirms it). That is the trade the contract makes: a word late
rather than a word twice.

### "paste clip 3"

The first dictbench run (section 26) reported "paste clip three" heard as
"Paste clip 3" and scored it as a different command. QUILL itself already
accepts a digit there: `targets.number_from` reads "three", "3" and "number
three" alike. The miss was the benchmark's: `bench_scoring.command_outcome`
compared the raw words after the command. It now compares the slot number,
and a controller test pins "Paste clip 3" pasting slot three in another
program. ("insert abbreviation addr" heard as "address" is a different case:
the engine changed the word, and nothing in the parser could know.)

### Documentation

The spoken-preview paragraphs in all three user guides (QUILL, QUILL Lite,
QUILL Transcribe) now say a word is spoken once it is settled and never twice;
the reading-back additions are above. The dictation-commands page (both
copies) and `docs/site/dictation.html` are regenerated from the command table.
No control was added, so F1 help is unchanged.

### Tests

`tests/unit/core/test_dictation_live_controller.py` (the spoken preview
through a rewrite; the user guide's reading example with the cursor and
selection left where they were; a read-only document read back; nothing to
read and the marks setting), `tests/unit/core/test_dictation_hold_and_preview.py`
(`to_speak` under the contract),
`tests/unit/core/speech/test_speech_vad_and_streaming.py` (`WordAgreement`),
`tests/unit/core/test_dictation_external_list.py` and
`tests/unit/scripts/test_bench_scoring.py` (the digit). Section 25's own D-18
tests are in `tests/unit/core/test_dictation_snippet_fill.py`.


## 32. Closing the dictation gaps plan (dict.md, 2026-10-13 to 2026-10-16)

The working plan for the D and B items lived in an untracked `dict.md` from
2026-10-13 until every item that could be built without a person had been
built, documented and merged (2026-10-16). It was then retired. This section
keeps everything in it that is still needed: where each item stands, what
waits on a person, the rules every item followed, what was decided against,
and the verdicts on retiring old speech models. The **as built** sections
above (14 to 31) are the record of what each item does.

### 32.1 Where every item stands

| Item | What | Status | Record |
|---|---|---|---|
| D-1 | A command keyword for directing dictation | Built; live 30-minute soak and the F11-with-dictation-off decision confirmed (keep) 2026-10-16 | Section 18 |
| D-2 | AI review and conversation before inserting | Built; needs a live check with a real AI sign-in | Section 19 |
| D-3 | An insertion fallback for programs that drop keys | Not built, on purpose: only if a clean D-4 run finds such a program | Section 17 |
| D-4 | The tested-programs harness | Built; every row reads Untested until it is run on an idle machine | Section 17 |
| D-5 | Never lose what was said | Built (Recent Phrases holds rescued words; confirmed 2026-10-16) | Section 25 |
| D-6 | Feedback where the person is working | Built | Section 24 |
| D-7 | "What can I say" in Transcribe | Built before this plan | Section 14 |
| D-8 | Spoken prompts for snippet blanks in other programs | Built | Section 25 |
| D-9 | Wake phrase and hold-to-talk in Transcribe | Built | Section 24 |
| D-10 | Correction in other programs, on the session's own words | Built; retyping refused in Word and Outlook until tested there | Section 27 |
| D-11 | One microphone owner | Built before this plan | Section 14 |
| D-12 | One word list for the family, import and export | Built | Section 20 |
| D-13 | One dictation settings store | Built | Section 30 |
| D-14 | The same keys, and the parity gate | Built before this plan | Section 14 |
| D-15 | Inkwell as a client of Transcribe | Built | Section 15 |
| D-16 | Dictate Here in Cast and Radio | Built; public from QUILL Transcribe's release on 2026-11-01 | Section 30 |
| D-17 | The soft working tick | Built before this plan | Section 14 |
| D-18 | Read back more | Built (one implementation) | Sections 25 and 31 |
| D-19 | Replace, delete by paragraph, a second opinion | Built | Section 27 |
| D-20 | Self-repair; Verbatim, Clean and Polished | Built | Section 28 |
| D-21 | Learn from corrections | Built; per-context lists wait on use; no Whisper prompt on sherpa-onnx 1.13.8 | Section 28 |
| D-22 | A recommended model, with reasons, and tier labels | Built | Section 21 |
| D-23 | Named profiles, format-aware structure | Built | Section 29 |
| D-24 | The never-type list, and the cloud indicator | Built | Section 15 |
| D-25 | Lessons, practice and the recognition test | Built | Section 29 |
| D-26 to D-29 | One sherpa-onnx layer; keyword spotting, hotwords, punctuation, diarization | Built and off until measured (B-1, B-3, B-8) | Section 22 |
| D-30 | Speech output through sherpa-onnx | Not built, on purpose: decide after measuring | Section 22 |
| D-31 to D-37 | Cloud providers with the person's own account | Built; each needs a live check with an account (protocol details marked "verify" in the code) | Section 23 |
| B-1 to B-8 | Benchmark and test infrastructure | Tooling built; the runs (B-1a, B-1c, B-8) and volunteers (B-1d) need a person | Section 26 |
| Section 9 | The small items | Built or covered | Section 31 |
| Streaming | `StreamAnnouncer` in the spoken preview | Built | Section 31 |
| Polish | Opt-in "Polish my dictation" AI pass | Built | Section 28 |
| Spanish | Spanish dictation and commands | Gated: needs recordings and a native speaker's review; command drafts stay development-gated | Sections 9 and 10 |

### 32.2 What waits on a person

1. Run the D-4 harness on an idle machine; its result decides D-3, and
   whether retyping corrections may be allowed in Word and Outlook.
2. Benchmarks: pin the dataset hashes, build B-1a, render B-1c, run B-8 on
   the 8 GB machine; B-1d needs volunteers. These decide D-26 to D-29
   adoption, D-30, and the retirements in 32.6.
3. Live checks: D-1 (30 minutes in Notepad, Word and Edge), D-2 with a real
   AI sign-in, D-31 to D-37 with the person's own provider accounts.
4. Spanish: recordings, a native speaker's review of the command tables and
   of the drafted review commands, then lifting the gate.
5. The screen-reader checks listed in `docs/qa/screen-reader-checks-2026-10.md`.

### 32.3 Decisions confirmed by Jeff on 2026-10-16

F11 with dictation off still opens the microphone for one command; the
overnight defaults stand (Speak a Command F11; empty Transcribe global keys
and Command Key; Review before insert on Shift+F4; lyrics in memory only;
sherpa-onnx pinned at 1.13.8 with its extras off); rescued words live in
Recent Phrases; Quill Inkwell keeps no rescued words for now and hides the
polish box; retyping corrections stay refused in Word and Outlook until
tested; the Standard profile keeps today's behaviour; sharing dictation
settings starts on only for unchanged installs; Dictate Here is Edit >
Dictate Here on Ctrl+F11; Spanish review commands are drafted behind the
gate.

### 32.4 The rules every item followed

- **Announce only what the screen reader does not already say (GATE-13).**
  Diffs, outcomes, refusals and background results are spoken. Text that has
  focus, window titles and control names are not. The review surface (D-2)
  announces the diff summary, never the whole text.
- **Keyboard first.** Every voice command has a menu item with its key shown
  (menu accelerators rule). Every global key is empty until the person
  chooses one, except the start and stop key.
- **No surprises.** There is no automatic model, profile or language switch.
  Modes show in the status cell and the tray. Command mode times out with a
  tone.
- **Undo for every change.** In editors, each dictated change is one undo
  step. Externally, only backspace-and-retype on the session's own words,
  refused out loud when unsafe. Originals stay recoverable (D-2, D-5, D-19).
- **Braille parity.** Every state line and preview reaches braille. No
  information is speech-only.
- **F1 everywhere.** New windows set inline `SetHelpText` and get
  `surface_help` entries (GATE-TRANSCRIBE-HELP).
- **Access keys (GATE-14).** OK, Cancel and Close carry no access key, and
  there are no duplicates.

### 32.5 Decided against, or deferred

| Item | Why |
|---|---|
| Automatic AI cleanup of every phrase | Declined on purpose (cost, privacy, latency); D-2 and D-20 cover it on request |
| Automatic language detection per phrase | Declined: wrong-language text written silently is worse than one command (dictation design, section 13 "The gap plan: twelve published capabilities, checked and built" (this record), "Decided against") |
| Automatic per-program profile switching | The PRD puts it out of scope "until a privacy review proves they can be implemented without reading document content" ([QUILL Transcribe PRD, section 7.6 "Dictation settings and profiles"](<../Product Requirement Documents and Specifications/quilltranscribe.md>)); manual profiles (D-23) instead |
| Reading another program's text for context by default | Breaks the Transcribe promise "It never reads the other program"; D-10 works on the session's own words |
| Local hotword biasing on Nemotron and Parakeet | Blocked: on sherpa-onnx 1.13.8, Nemotron's streaming decoder supports greedy search only, and Parakeet's hotword path upper-cases words, so biasing did nothing or produced garbage (measured 2026-10-05; dictation design, section 5 B "Teaching dictation your words" (this record)). D-28 tries Zipformer transducers instead and rechecks NeMo on each upgrade |
| Audio retention and replay | Off; reconsider after D-5 history ships, as a separate opt-in |
| Cloud providers before the provider layer | Every cloud provider waits for D-31 (one interface, the Speech Providers page, safe secrets, per-provider consent), so that none is added as a one-off |
| Windows online speech recognition (WinRT) | It cannot choose the microphone and needs package identity (`quill/platform/windows/sapi_dictation.py`); Windows voice typing is already an engine |
| Creating resources in a person's cloud account (Amazon or Rev.ai vocabularies, Google recognizers) | QUILL only uses what the person names; it never creates or changes their cloud resources |
| Canary in the catalogue before measurement | The API exists in sherpa-onnx 1.13.8 (`from_nemo_canary`) but QUILL has not measured it; S0 of D-26 measures it first |
| Retiring whisper.cpp and Faster Whisper outright | They are kept as optional packs: the initial prompt, GPU speed and the lowest memory for large models (D-26) |
| Browser extensions | The PRD says "The initial release does not require browser extensions" ([QUILL Transcribe PRD, section 12.1 "Initial compatibility matrix"](<../Product Requirement Documents and Specifications/quilltranscribe.md>)) |
| Held-modifier command mode as the default | It conflicts with screen-reader keys (D-1) |
| Replacing keystroke insertion | It is tuned and verified (#1654, #1655); D-3 adds only an opt-in, per-program fallback where the matrix proves a program drops keys |

### 32.6 Retiring legacy models

These verdicts were written on 2026-10-13 against the synthetic-voice
numbers, so every removal waits for the section 26 benchmarks. The Vosk
dictation retirement has since shipped (#1663).

#### Verdict per engine or model family

| Engine or model | What only it provides | What supersedes it, and how well | Maintenance cost in the repo | Download and disk | Risk to people using it today | Verdict |
|---|---|---|---|---|---|---|
| **whisper.cpp** (Locked Dictation default and offline file transcription, QUILL only) | The Whisper **initial prompt** (`--prompt`); tinydiarize speaker turns (`small.en-tdrz`); the lowest memory for large models (GGML used about half the memory of sherpa-onnx Whisper, design section 6) | sherpa-onnx Whisper keeps translation and segment timestamps, and ran 4 to 7 times faster per thread on the same recordings (design section 6). It has **no** initial-prompt parameter (checked in the local `from_whisper` signature). D-29 diarization would replace tinydiarize | `providers/whispercpp.py` (535 lines), `catalog.py` tiers, executable allowlist, the assets-v1 executable (about 8 MB) and GGML models with SHA-256 pins, `model_mirrors.py`, `test_whispercpp.py`; a subprocess path, not Python wheels, so Python 3.14 does not affect it | Models of 75 MB (tiny) to 3.1 GB (large-v3) (`catalog.py`) | High: it is the Locked Dictation default for every QUILL install without Parakeet (`service.preferred_dictation_provider_id`) | **Keep as an optional pack.** Change the default only after D-26 S2 and B-1 |
| **Faster Whisper** (CTranslate2) | **GPU acceleration** (CUDA float16 when present, `fasterwhisper.pick_device_and_compute`); batched inference; initial prompt | sherpa-onnx Whisper on CPU. The Windows sherpa-onnx wheel here has no GPU provider (local observation), so nothing supersedes the GPU speed | `providers/fasterwhisper.py` (349 lines), `engine_install.install_faster_whisper` (about 110 MB of wheels; `ctranslate2` 4.8.2 has a cp314 win_amd64 wheel, 19.5 MB, in `uv.lock`), Hugging Face downloads, `test_fasterwhisper_provider.py` | Models of 75 MB to 3.1 GB, plus about 110 MB of engine | Medium: few users, but they are the ones with GPUs and long recordings | **Keep as an optional pack** (it is already install-on-demand) |
| **Vosk** (Kaldi) | **Podcast chapters in QUILL and QUILL Cast**: it is the bundled chapter engine (`service.CHAPTER_PROVIDER_ID`; `scripts/build_windows_distribution.py`; the Cast spec). On the reference chapter lists it scored 0.372 against Whisper medium's 0.316, and was 4.7 times faster. As a dictation engine it offers only a small English model | For **dictation and voice features** (voice commands, Hey QUILL): the bundled Moonshine tiny (3.4 percent word errors at 0.05 of real time and 210 MB peak, design section 6). For **chapters**: nothing yet; Moonshine tiny plus Silero VAD cue segmentation is the candidate | `providers/vosk.py` (387 lines), `engine_install.install_vosk`, the bundled wheel (about 51 MB with libvosk), models from alphacephei.com checked by **MD5 only**, an egress entry, `test_vosk_provider.py`. The last `vosk` release, 0.3.45, was uploaded on 2022-12-14 (`uv.lock`) | 40 MB (small) or 1.8 GB (large `en-us-0.22`) (`catalog.py`) | Chapters: high, if removed. Dictation: low, because saved settings migrate to Moonshine tiny, which is already installed | **Keep for chapters. Retired as a dictation and voice-features engine: done, #1663 (2026-10-13).** Replace it as the chapter engine only when the Moonshine and Silero candidate beats 0.372 on the same reference set (gated on section 8); Cast would also need sherpa-onnx bundled |
| **Duplicate Parakeet and Nemotron** (Locked Dictation's own providers and folder) | Nothing the shared models do not; the same model files in a second folder | The same models in the shared dictation store (`windows_dictation/model_store.py`), as D-26 S1 plans | Two providers (`nemotron_onnx.py`, 355 lines; `parakeet_onnx.py`, 314 lines), `engine_install.install_nemotron`, a second model folder; dictation design, section 10 (this record) lists "One folder for Parakeet" as deferred | About 632 to 670 MB **twice** when both stacks have downloaded it | None, if the files are moved rather than downloaded again | **Deprecate the duplicate path**: merge into the shared store in D-26 S1 (move or hard-link the files), then delete the second providers in QUILL 1.2. The models stay |
| **Moonshine tiny** (bundled) and **Moonshine base** (download) | The fastest models on a modest computer, punctuated by themselves | Nothing yet. Moonshine v2 is in the sherpa-onnx 1.13.8 API (`from_moonshine_v2`), but its models are unmeasured | Small; shared with every app | 124 MB bundled; 141 MB download | Removing them would break the default | **Keep** (tiny stays the 4 GB default) |
| **Whisper tiny and tiny.en** (bundled) | Tiny is the only bundled Spanish model | Nothing bundled | Small | About 104 MB each | It is the Spanish path | **Keep** |
| **English-only Whisper sizes in the live catalogue** (base.en, small.en, medium.en, Distil-Whisper small.en, medium.en and large-v3) | Nothing measured that Moonshine base, Parakeet or Nemotron lacks in English | Measured multilingual Whisper base (5.1 percent, 0.37), small (5.1 percent, 1.29) and medium (3.4 percent, 3.04, 2.1 GB) against Moonshine base (3.4 percent, 0.08, 365 MB) and Nemotron (2.5 percent, 0.40). The `.en` and Distil variants themselves were **not** in that table, and the Distil cost factors are estimates (design section 10) | Catalogue rows only (`model_catalog_whisper.py`), pinned to a commit and SHA-256 | Hundreds of MB to over 1 GB each | Low, but some voices may suit Whisper better; that is the reason the design note offers Whisper | **Deprecate candidates, pending B-1 and B-8.** Decide per model after measuring; do not remove on the synthetic numbers |
| **Multilingual Whisper sizes** (base, small, medium, large-v3-turbo, large-v3) | The only local models covering **many languages** beyond Parakeet TDT v3's 25; translation to English | Parakeet TDT v3 and Canary (four languages) cover only part of that | Catalogue rows only | 145 MB to 3.1 GB | High for people dictating in other languages | **Keep.** Review large-v3 against large-v3-turbo after B-8 (large-v3-turbo used 1.4 GB in the design table; large-v3 was not measured) |
| **Windows speech recognition (SAPI)** | Real **alternates** for "correct that" (the only engine that gives them, design section 8); offline; no download; Spanish recognizers where Windows has them; any microphone | Nothing | `quill/platform/windows/sapi_dictation.py`, pywin32 already shipped | None | It is someone's preferred engine, and the fallback with no model | **Keep** |
| **Windows voice typing** (Windows+H engine) | Windows' own panel, for people who already know it | Nothing | Small (`engines.py`) | None | Familiarity | **Keep** |
| **Legacy Win+H shim** (`quill/core/dictation.py`) | Nothing the `voice_typing` engine does not; its own docstring says it is "retained only as the OS-panel fallback" | The `voice_typing` engine | A separate module and settings fields described in its docstring as "inert" | None | None, if its callers are pointed at `voice_typing` | **Deprecate**: fold into `voice_typing`, remove in QUILL 1.2 (callers **not yet traced**) |
| **Kokoro TTS** (kokoro-onnx, patched wheel) | Many languages through espeak; checked bit-identical on Python 3.14 (the untracked note `missing.md`) | Possibly sherpa-onnx `OfflineTts`; its Kokoro language list looks narrower (Chinese and English, **unverified**) | A patched wheel and the onnxruntime, phonemizer, espeakng-loader and Babel chain | About 114 MB of voices | High: people's reading voice | **Keep.** Revisit only through D-30 |
| **Piper TTS** (`piper.exe`) | Many small voices | Possibly sherpa-onnx VITS with converted voices (**unverified**) | `piper_install.py`, about a 22 MB zip, SHA-256 | Voices vary | Medium | **Keep.** Revisit only through D-30 |

Nothing in the inventory qualifies for **Remove now**. Every candidate either
has users today with no announced notice, or a replacement that has not yet
been measured on real voices.

#### What happens to people on a retired model

- **Existing installs keep working** for the whole notice period. A
  deprecated engine stays selectable and keeps running exactly as before.
- **Told once, in plain words.** The first time a deprecated engine starts
  after the update, one sentence is spoken and shown in Activity, then never
  repeated. For example: "Faster Whisper is now an optional pack. Your
  recordings still transcribe with it. Choose Switch Engine in Dictation
  Settings to change." There is no tone-only notice and no repeated nag. The
  sticky-model rule holds: **QUILL never switches the engine by itself**,
  not even at removal. The one exception is a migration announced in
  advance, such as Vosk dictation moving to Moonshine tiny (done, #1663): the saved setting migrates once, and a one-time notice says
  so in plain words ("Dictation now uses Moonshine, which is already on this
  computer. Vosk still makes your podcast chapters.").
- **One action to move.** A **Switch to the Recommended Model** button in
  Dictation Settings and in Speech Models uses D-22's recommendation for
  this computer. It changes only the engine and model settings. My Words
  (`dictation.md`), My Dictation Instructions, the dictation context,
  pauses, punctuation and every other setting are untouched, because they
  are engine-independent already (`DictationPreferences`).
- **Downloaded files.** After a successful switch, QUILL offers once: "Delete
  the Whisper medium files to free 1.5 GB?" No is the default. On Yes, the
  freed space is reported in one sentence ("Freed 1.5 GB"), measured, not
  estimated. Shared files are never offered for deletion while another app
  or feature still points at them: a Parakeet folder that QUILL Lite also
  uses, or the Vosk model that podcast chapters still use. On removal, the
  engine pack (for example in `<app data>/engine-packs/`) goes into the same
  offer.

Both tools are built (2026-10-23), as **Switch to Recommended Model** in
Speech Models and the Delete Old Speech Model offer; section 38.1 records
them as built and where they depart from the two bullets above.

#### Deprecation policy

1. **Evidence first.** Nothing is deprecated until its replacement has been
   measured under the public-data benchmark plan in section 8: the LibriVox
   held-out set scored against the Gutenberg text (B-1a, word errors and
   punctuation), the relevant public datasets (B-1b), the dictation-command
   script (B-1c), and the 8 GB machine with a screen reader running (B-8).
   The results are written into the dictation design record.
2. **Notice period: one full feature release.** Deprecate in release N (the
   engine works, with the notice), and remove no earlier than release N+1.
   For an engine that is the default for some installs (whisper.cpp), the
   period is two releases. (Set aside once, on 2026-10-22, for five
   English-only models removed in the release that measured them: section
   37 says why.)
3. **Announced three ways:** a "Deprecated" entry in the CHANGELOG and the
   release notes of release N, naming the replacement and the removal
   release; the one-time spoken notice above; and a line in the user guide's
   model list until removal.
4. **Never silently.** No engine is switched, and no file deleted, without
   the person's answer.
5. **Removal checklist:** delete the provider, its `engine_install` path,
   catalogue rows, egress entries, the wheelhouse and `uv.lock` pins, and its
   tests; regenerate the generated references; and confirm that the network
   egress audit and the settings vocabulary audit both pass.

#### Recommendation: yes, retire a few, and only for clear reasons

**Should we remove support for some models? Yes, but only three things, and
only after a notice period.**
- **Vosk as a dictation and voice-features engine** (in progress, branch
  retire-vosk, PR pending): its dictation model is English only, the library
  has not changed since December 2022, it is checked by MD5 rather than
  SHA-256, and the bundled Moonshine tiny already covers dictation, voice
  commands and Hey QUILL. **Vosk stays as the podcast chapter engine**,
  where it beat Whisper medium (0.372 against 0.316) and was 4.7 times
  faster.
- **The duplicate Parakeet and Nemotron path** inside Locked Dictation: it
  costs a second 650 MB download and two extra providers, for no capability
  of its own.
- **The legacy Win+H shim**, which duplicates the voice typing engine.

**Keep** whisper.cpp and Faster Whisper as optional packs: one is the only
initial-prompt and low-memory option, and the other is the only GPU option.
Keep Vosk for chapters, Moonshine, the bundled Whisper models,
multilingual Whisper, Windows speech recognition, voice typing, Kokoro and
Piper.

**Decide later, on measurements:** the English-only Whisper and
Distil-Whisper sizes (after B-1 and B-8), and the whisper.cpp default
(after D-26 S2).

The reason for removing anything is maintenance and safety, not fashion.
Each removal takes a provider, a download host or a pinned wheel out of the
build, and leaves people with a measured, already-installed alternative.

| Proposed change | Deprecate in | Remove in | Condition |
|---|---|---|---|
| Vosk as a dictation and voice-features engine (it stays for chapters) | Done in #1663 (2026-10-13): settings migrated to Moonshine tiny with a one-time notice | The release that merges it | Moonshine tiny measured on B-1a, B-1c and B-8 |
| Vosk as the chapter engine | Not before the replacement wins | Not scheduled | Moonshine tiny plus Silero VAD cue segmentation beats 0.372 on the same reference chapter lists (section 8), and sherpa-onnx is bundled in Cast |
| Duplicate Parakeet and Nemotron providers and folder | QUILL 1.1 (files merged into the shared store in D-26 S1) | QUILL 1.2 | The migration is verified to move files without downloading them again |
| Legacy Win+H shim (`quill/core/dictation.py`) | QUILL 1.1 | QUILL 1.2 | Its callers are traced and pointed at `voice_typing` (not yet traced) |
| whisper.cpp as the **default** (the engine itself stays as a pack) | After D-26 S2 | Not removed | B-1 parity for sherpa-onnx Whisper or Parakeet |
| English-only Whisper and Distil-Whisper sizes | Only if B-1 and B-8 show they are dominated | One release later | Measured per model, not on synthetic voices |

The release numbers assume that QUILL's next feature releases are 1.1 and
1.2 (the current QUILL changelog's top entry is 1.0.0); rename them to the
real release names when they are scheduled. QUILL Lite and Transcribe are
affected only by the catalogue decision on the Whisper sizes, because
whisper.cpp, Faster Whisper and the duplicate providers are QUILL-only. QUILL
Cast is affected by Vosk only as the chapter engine, which stays.

## 33. Documentation, 2026-10-17: every guide checked against the engines as built

A family-wide pass rebuilt the engine and model story from the code and
corrected every guide, PRD, release note, help topic and the site's dictation
page against it (root CHANGELOG, "Speech engines and models: every guide says
what the code does"). Three findings change what earlier sections imply and
are recorded here:

* **"A fresh install dictates at once" (section 22) holds for Locked
  Dictation's transcription, not its pre-flight.** `_dictation_preflight` asks
  `_speech_provider()`, which falls back to whisper.cpp, and offers the ~8 MB
  whisper.cpp engine when it is missing; only after that does the ladder's
  Moonshine tiny step apply. Dictate (Offline), Transcribe Audio or Video,
  captions and the voice features (with the default Follow main engine) use
  `_speech_provider()` and `_check_installed_speech_models`, so they need a
  model for the chosen engine. Choosing QUILL speech models (`sherpa`) is the
  only way nothing downloads at all. The guides now say exactly this.
* **Dictate in Other Programs goes to QUILL Transcribe first**
  (`windows_dictation_extras._dictation_hand_to_transcribe`), and to Inkwell
  only when QUILL Transcribe is neither running nor released.
* **Quill Inkwell alone cannot run the built-in models, OpenAI or the
  providers**: its installer carries neither `dictation-models` nor
  sherpa-onnx, and OpenAI and the providers still load sherpa-onnx's voice
  detector (`local_recognizer._check_audio_stack`). On an Inkwell-only
  computer only Windows speech recognition works; the Inkwell guide says so
  and points to QUILL Transcribe. Whether Inkwell should ship that part is a
  product decision, not made.

## 34. As built, 2026-10-16: the live preview on a braille display in QUILL Lite

The live preview (section 3) reaches a braille display through
`ScreenReaderVoice.braille`, and every spoken dictation status is mirrored to
the display after it is spoken. In QUILL Lite both went straight to the display,
one write per message, so a preview that changed several times a second
replaced the cells faster than a finger could read them. QUILL never had this:
its announcement service has run braille through `CoalescingBrailleWriter`
(`quill/ui/announce_wiring.py`) since 2026-08.

QUILL Lite now uses the same writer, not a copy. The voice switches the shared
engine's inline braille off when it builds the engine, and sends the speech
mirror and every preview through one coalescer: the first message of a quiet
moment writes at once, and a burst lands as its newest message when the 150 ms
window closes. Speech is not delayed at all. In practice, the display shows the
first words of a phrase as they are heard and the whole phrase a moment after
the speaker pauses, with nothing in between. Tests:
`tests/unit/apps/test_lite_braille_coalescing.py` (fakes only: a fake engine
and a fake timer). User-facing: QUILL Lite's user guide, *On a braille display*.

## 35. Acceptance coverage, 2026-10-17: the automated part (todo D.2)

What this section covers is the behaviour after a phrase is heard: given these
words, does the document end up right, in QUILL and in QUILL Lite? It does
**not** cover how accurately or how quickly any engine hears; that waits on the
benchmarks (todo C.15, section 32.2). Whether a screen reader echoes the
read-back waits on the live checks (todo C.20). Nothing here is a claim about
the quality of recognition.

**How it runs.** `tests/unit/apps/test_dictation_acceptance.py`. Every editor
test runs twice: once in QUILL Lite's real window mixins (`lite_window`), once
through QUILL's real adapter (`WindowsDictationCommandsMixin`) on a stand-in
frame that answers what MainFrame answers, with QUILL's own `copy_all`. Both
start with the editor's own `cmd_toggle_dictation`; from the phrase to the
document everything is shipped code (controller, parser, composer,
`EditorDocument` and `HostFeedback`, each editor's library). The recogniser is
a fake that hands over named words, the text control is the suite's
`FakeControl`, and the focus is patched: no microphone, no real window, no
keystroke. The other-program tests use the shipped `ExternalDocument` with
typing and backspaces faked and the shipped `AnywhereLibrary` reading a test
folder. 182 tests on the day it landed.

| Behaviour | Command names | QUILL | QUILL Lite | Result |
|---|---|---|---|---|
| Insert before a spoken phrase | go to, go before | yes | yes | works |
| Insert after a spoken phrase | go after | yes | yes | works |
| Words not found | go after, select | yes | yes | written as text, said, scratch that removes it |
| Repeated matches | select, select previous, select next, select again | yes | yes | nearest before the cursor first; "None before that." and "No more." at the ends; a far match says its line |
| Selection by words | select, select ... through ..., correct | yes | yes | works; numbers match either way |
| Units | select sentence, select line, select paragraph | yes | yes | works |
| Copy All | copy all, copy everything, copy document | yes | yes | the editor's own Copy All; nothing selected, cursor unmoved, empty document copies nothing |
| Copy the last phrase | copy that | yes | yes | works |
| Removing only the last phrase | scratch that, delete that | yes | yes | newest first, one at a time; typed text never taken; a phrase typed into is left alone and said |
| All twelve clips | paste clip one to twelve, paste slot 1 to 12 | yes | yes | each slot, one phrase, scratch that removes it; empty slot said; slot 13 asks for a number |
| Named text with spaces | insert snippet, insert abbreviation | yes | yes | "sign off" and "home address" found; "sig off" finds sigoff; two matches counted, nothing typed |
| Capitalization modes | caps on/off, capitals on/off, all caps on/off | yes | yes | works; modes end when dictation stops |
| Changing the last phrase's case | capitalize that, cap that, all caps that, uppercase that, no caps that, lowercase that | yes | yes | works |
| Capitals while spelling | capital, all caps, no caps | yes | yes | works |
| Email, character by character | start spelling, stop spelling, spell, at sign, dot | yes | yes | **fixed**: pauses no longer put spaces in; words that are not letters are left out (documented) |
| Markdown line marks | heading one to six, bullet, list item, numbered item, block quote, code fence | yes | yes | works; only at the start of a phrase |
| Markdown inline marks | backtick, back quote, vertical bar, pipe symbol, tilde, caret, greater than sign, less than sign, asterisk, underscore, brackets | yes | yes | **fixed**: a link's "](" no longer gets a space; asterisk and underscore join both sides (documented) |
| Literal | literal | yes | yes | works |
| Insert-only limits in another program | every command above | n/a | n/a | 16 commands that read or select are refused with one sentence; dictating, scratch that, modes, spelling, clips and snippets type; a snippet's cursor mark is dropped |

**What the tests found, and what changed.** Two operations were broken, and
both are fixed in the shared code, so QUILL, QUILL Lite, QUILL Transcribe and
Quill Inkwell's Dictate Anywhere all get them:

* **Spelling across pauses.** Each spelled phrase was composed like a new
  phrase of words, so "juliet", pause, "oscar" wrote "j o". Now a phrase in
  spelling mode joins the letters spelled just before it, with no space, when
  the cursor is still right after them (`VoiceCommandsMixin._spelling_joins`,
  and `DictatedPhrase.spelled` in `history.py`). "space" still writes a space;
  the first spelled phrase after ordinary words still gets one; "spell that"
  and "spell" with letters are unchanged.
* **A Markdown link.** "close bracket open paren" wrote "] (": an opening
  parenthesis takes a space in front like any opening mark. It now hugs a
  closing bracket (`composer.py`), so `[text](page)` can be dictated, within one
  phrase or across two.

**What the guides said that was not true.** The spelling example
"jay dot smith at sign example dot com" wrote `j.@.`: in spelling mode a word
that is not a letter is left out by design (parser `_spell`), and the guides
implied otherwise. The example is now spelled out in the generated command
reference, the site's dictation page and QUILL Lite's guide.

**Documentation.** The generated dictation-commands guides (both editors) have
a new *Worked examples* table and a *Limits* list
(`quill/core/windows_dictation/reference_examples.py`, regenerated with
`scripts/build_dictation_commands.py`); every example there is one these tests
run. The in-app "What can I say?" list shows the same, as plain lines.

**Left for people.** Accuracy and latency (C.15), the live checks (C.16), and
read-back without echo on each screen reader (C.20).

## Appendix A: the dict.md section numbers, and where they live now (the first dict.md, 2026-10-05)

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

## 36. Measured, 2026-10-22: real speech, Spanish, and an 8 GB baseline

The first machine run on real recordings (`scripts/bench_machine_run.py`;
LibriSpeech clean and other, the LibriVox held-out sets, FLEURS Spanish; one
thread; on the development computer, not the baseline machine with a screen
reader, which B-8 still needs).

**Spanish** (percent of words wrong; lower is better):

| Model | FLEURS Spanish | LibriVox Spanish | Peak memory | Speed per thread |
|---|---|---|---|---|
| Whisper tiny (built in) | 30.5 | 27.0 | 521 MB | 0.06 |
| Whisper base | 12.6 | 16.1 | 806 MB | 0.18 |
| Whisper small | 6.0 | 7.8 | 1,435 MB | 0.40 to 0.57 |
| Parakeet TDT v3 | **4.4** | **7.3** | 1,136 MB | 0.07 to 0.11 |
| Nemotron | 6.4 | 8.0 | 1,538 MB | 0.13 to 0.37 |

The bundled Spanish model gets about one word in four wrong; Parakeet about
one in seventeen, at a similar speed. Moonshine has no Spanish model (its
Spanish row is Whisper tiny's).

**What changed in the code** (Jeff, 2026-10-22, all three points agreed):

- **The 8 GB baseline.** `model_types.RAM_TIERS` is 600 MB / 1.6 GB / 4 GB
  (was 600 MB / 1 GB / 2.5 GB), the same as the benchmark driver's tiers.
- **Free memory, not only total.** `bw_speech.available_ram_gb` reads
  `ullAvailPhys`; `SpeedCheck.available_gb` carries it, and
  `model_advice.for_this_computer` re-reads it on every call. A model must fit
  in what is free less 500 MB, and the reason says when free memory, not the
  computer, ruled a model out.
- **Spanish by Spanish.** `Measured.word_errors_es` holds the mean of the two
  Spanish sets; Spanish is ranked by it, and only models with a Spanish figure
  are offered for Spanish. The reason now cites real Spanish speakers instead of
  "measured in English only".
- **Real peaks.** `Measured.peak_mb` is the highest seen on any real set; they
  run 1.5 to 2.8 times the synthetic figures.

**Speed factors and English: done in section 37.** Recorded here as it stood
on the first pass: **Not changed yet, deliberately: the speed factors.** On real speech Parakeet
cost about 1.6 times Moonshine tiny (the catalogue says 6.3), Nemotron 5.5
(8.0) and Parakeet Unified 3.2 (6.1). With the catalogue's factors Parakeet
still reads as needing a second processor thread on a four-core 8 GB computer,
so Spanish there is still Whisper tiny unless "The fewest mistakes" is chosen.
Updating the factors also changes English recommendations and relabels tiers,
so it waits for the English real-voice numbers, to be written in as one
change.

**Found, and since fixed (section 37):** Moonshine base scored 50 to 73
percent wrong on every real English set (3.4 on the synthetic voice), while
Moonshine tiny scored 5.0 to 13.3.

**Also fixed on the way:** dictbench printed transcripts on a cp1252 console
and crashed on "ş", so every FLEURS Spanish run had failed silently (#1679);
the driver then decoded the UTF-8 output as cp1252 (#1681).

## 37. As built, 2026-10-22: real English figures, real speed, five models removed

The English half of the real-speech run, written in as one change so English
recommendations, Spanish recommendations and the tiers moved together. The
full record, with every table and the method, is
`docs/qa/dictation-real-speech-benchmark-2026-10-22.md` and its `.json`.

**Moonshine base, fixed** (#1683). sherpa-onnx 1.13.8's `moonshine_v2`
decoder fails an ONNX broadcast in encoder attention past about 8.5 seconds,
catches it and returns an empty result; every long phrase was lost.
`chunked_offline.ChunkedOffline` cuts a long phrase into pieces of 8 seconds or
less at the quietest moment and joins the words. Re-measured: 4.8 percent
clean, 10.7 other, 5.9 held-out, 15.1 FLEURS.

**English, by the held-out audiobooks** (`Measured.word_errors`; percent
wrong): Parakeet Unified 3.2, Whisper medium.en 3.6, Parakeet TDT v3 3.8,
Whisper small.en 4.3, Distil-Whisper large-v3 4.5, Whisper small 4.7,
Nemotron 5.3, Moonshine base 5.9, Whisper base.en 5.9, Distil-Whisper small.en
5.9, Distil-Whisper medium.en 6.3, Moonshine tiny 6.5, Whisper base 7.4,
Whisper tiny 8.3. Whisper medium and large-v3-turbo were not re-run.

**Speed factors** (catalogue `cost_factor`, from the English FLEURS run where
the models ran back to back, against Moonshine tiny): Parakeet TDT v3 3.2
(was 6.3), Parakeet Unified 3.8 (6.1), Moonshine base 2.2 (1.5), Whisper
base.en 4.3 (6.8), Nemotron 5.8 (8.0), Whisper base 7.0 (6.8), Distil-Whisper
small.en 7.9 (18), Whisper small.en 14.5 (24); the built-in Whisper 2.6 (4.0).
`_LEGACY_SAME_AS` follows. The tiers move with them: Parakeet TDT v3, Parakeet
Unified and Whisper base.en are Lightweight; Nemotron is Balanced.

**What is recommended now** (balanced): 4 GB two cores, Moonshine tiny /
Whisper tiny; 8 GB two cores, Parakeet TDT v3 for both languages when the
two-second check times Moonshine tiny at about 0.07 or less (untimed, a
two-core computer counts as modest and keeps the built-in models); 8 GB four
cores and up, Parakeet Unified for English and Parakeet TDT v3 for Spanish.
"The quickest response" stays Moonshine tiny. Nemotron is not recommended
anywhere on these numbers; it stays for its live preview.

**Removed in this release** (decided by Jeff, 2026-10-22): Distil-Whisper
small.en, Whisper small.en, Distil-Whisper medium.en, Whisper medium.en and
Distil-Whisper large-v3. Each was beaten by Parakeet Unified on the held-out
audiobooks (3.2 percent wrong, against 3.6 to 6.3 for these), on FLEURS where
both ran and on noisy LibriSpeech, faster per thread, in the same or a smaller
memory tier. Kept, on the evidence: Whisper base.en (7.4 FLEURS against
Moonshine base's 15.1, in 820 MB) and every multilingual Whisper size.

**This overrides section 32.6's notice period** (deprecate in release N,
remove no earlier than N+1) for these five, and only these. The reason: a
release of notice would only have kept offering a slower or heavier way to a
worse result, and none of the five is a default anywhere. The policy's other
rules still hold, and the removal kept them: evidence first (section 36 and
the benchmark record); announced in the CHANGELOG and every app's release
notes as "Removed"; and never silently, though a removed model can no longer
be asked about, so the change is said rather than offered:

- `removed_models.REMOVED` records each id, name and folder. The catalogue
  rows are gone, and with them every "Being retired" line, the
  `_with_retiring_notes` pass and the `model_advice` filter.
- `engines.coerce_engine` maps a saved removed id through
  `removed_models.replacement_for`: Parakeet Unified when it is already
  downloaded, else the default engine. Nothing is downloaded.
- The change is recorded in `removed-model-notices.json` beside
  `family_dictation.json` when it is made (`noticed`), not when it is said,
  because the next settings save forgets the old id. The controller says it at
  the next dictation start (`take_notice`), once across the family: "Whisper
  small.en was removed in this release, so dictation uses the built-in model.
  Parakeet Unified, in the model list, is more accurate." (or "... Dictation
  now uses Parakeet Unified, which you already have.").
- No file is deleted: the old folder stays under the dictation models folder
  (`%LOCALAPPDATA%\QuillVille\Dictation\models`), and the release notes say
  so. The removal checklist's other items had nothing to do: these were
  catalogue rows on the existing sherpa-onnx runtime, with no provider,
  install path, egress entry or pin of their own.

**Still for a person:** B-8 on a real 4 GB computer with NVDA or JAWS; ten
native Spanish recordings with questions and exclamations (the opening marks
are now scored, #1684); the native-speaker review of the Spanish commands.

## 38. As built, 2026-10-23: the Spanish tip and Moonshine base's seams

**The Spanish tip** (`spanish_tip.py`, said through `start_notices.py`). The
only Spanish model in the installers is the built-in Whisper tiny: 30.5
percent of words wrong on FLEURS Spanish and 27.0 on the Spanish audiobooks,
about one word in four. Parakeet TDT v3 gets 4.4 and 7.3 (section 36).

- **When.** The first time dictation starts in Spanish on a computer whose own
  Spanish recommendation (`model_advice.for_this_computer("es")`) is a
  download, while the Spanish would otherwise go to the built-in Whisper tiny
  (`engines.model_for`). That is both built-in engines and every English-only
  download, which hand Spanish to Whisper tiny. In practice it is Parakeet TDT
  v3 on a computer with 8 GB of memory and four cores; a 4 GB computer hears
  nothing.
- **What.** One sentence: "For Spanish, NVIDIA Parakeet TDT 0.6B v3 gets about
  6 percent of words wrong, against 29 for the built-in model. It is a 670 MB
  download in the model list." (or "It is already downloaded; choose it in the
  model list."). The figures are the means of the two Spanish sets
  (`Measured.word_errors_es`). Nothing is downloaded and nothing is switched.
- **Once.** Across every QuillVille program, recorded in `spanish-tip.json`
  beside the family's shared dictation settings, written when it is said. It
  runs in QUILL, QUILL Lite and QUILL Transcribe, which share the dictation
  controller.
- **Order.** At most one start sentence is said each time
  (`start_notices.start_notice`): a downloaded model that gave way to the
  built-in one; then a removed model (section 37); then the Spanish tip. A
  once-only notice that waits its turn is said at a later start.

**Decision** (Jeff, 2026-10-23): the tip, not shipping Whisper base in place of
tiny. Base gets 12.6 and 16.1 percent wrong at about 820 MB peak; it would have
made every installer bigger and still left Spanish about three times worse
than the download. A computer that can run the download is told so once; one
that cannot loses nothing it had.

**Moonshine base's seams** (`chunked_offline.py`). Section 37's fix cuts a
phrase over about 8 seconds into pieces, each cut at the quietest moment near
it. A cut that still landed on a word lost that word: the 12-second check
dropped one word at each cut. Each piece now reaches half a second
(`_OVERLAP_SECONDS`) past its cut on both sides, so a word near the cut is
heard twice, and `join_overlapping` drops the repeat, keeping the later
piece's copy, which heard what came after it. Where two pieces agree on
nothing, the words are joined with a space, as before. No word is lost at a
cut.

### 38.1 The retirement policy's tools, as built

Section 32.6 promised two tools for people moving off a model: one action to
move, and an offer to free the old files. Both are built, in the shared Speech
Models window (`dictation_models_dialog.py`), so QUILL, QUILL Lite and QUILL
Transcribe's Model Library get them together.

**Switch to Recommended Model** (Alt+H), beside Show Recommended Model. It
sets the window's `chosen` to D-22's recommendation and closes with OK,
exactly as Use for Dictation does, so it changes the engine and nothing else:
My Words, My Dictation Instructions, pauses and punctuation are untouched.

- **Never a download.** A model not on this computer gets "X is not on this
  computer yet. Download it, then switch." and focus moves to its row, so the
  next key is Download. The sentence comes before the focus move, so the
  message box does not cut off the row being read.
- **Never a silent cancel.** During a download it says "A model is
  downloading. Wait for it, or press Cancel Download first." Closing would
  have stopped the download without a word.
- **Always reachable.** It is enabled whenever there is advice, rather than
  greyed out when the model is missing, so Tab always reaches it and pressing
  it explains itself.
- **Built in Speech Models only**, not also in Dictation Settings as 32.6
  sketched. Dictation Settings reaches it through Better Accuracy: Speech
  Models... (Alt+B).

**The offer** (`offer_to_remove_replaced`, with `will_offer` as its
predicate). After a switch away from a downloaded model still on this computer
is saved, a Yes/No box captioned "Delete Old Speech Model", No by default:
"Now using Y. Delete X to free N MB? QUILL, QUILL Lite and QUILL Transcribe
share its files; any of them still set to X will need it downloaded again."
Yes removes it through `model_store.remove` and says "X deleted. N MB freed.";
a failed delete says "X could not be deleted; something may still be using
it. Remove it in Speech Models later."

- **After the save, not in the window.** In QUILL and QUILL Lite it runs from
  `_dictation_offer_old_model` (`windows_dictation_extras.py`), called by
  `windows_dictation_commands.py` only when Dictation Settings closed with a
  plain OK and the settings are already saved. Speech Models' choice is only
  provisional until that OK: offering inside Speech Models, or before the
  save, would let a person delete the old model and then press Cancel,
  leaving a deleted model as the saved engine. In QUILL Transcribe the choice
  is saved at once by `_use_model` (Choose Model, or the Model Library), so
  the offer follows it there.
- **Not ahead of a window the person asked for.** A Dictation Settings close
  through My Words and Phrases or another window-opening button gets no
  question; the person is on their way somewhere.
- **Not while the old model may be held.** Skipped while dictation is active
  or standing by for the wake phrase (QUILL, QUILL Lite), or active
  (Transcribe): the delete would fail on files in use. Remove in Speech Models
  stays the route later. No question for a built-in engine, a model not on
  this computer, or no change.
- **It stands alone.** The question leads with "Now using Y", because it
  arrives after the window that made the change has closed and is heard with
  nothing before it. Transcribe skips its own "Model: Y." announcement when
  `will_offer` says the box is coming, which would otherwise be cut off by it.
- **Departures from 32.6.** The size is the catalogue's `disk_bytes`, the same
  figure Speech Models shows, not a measurement of the folder. Shared files
  are not withheld from the offer when another program still points at them:
  nothing records which programs use which model, so the question says the
  files are shared and what that costs, and No is the default. There is no
  engine pack to include: every catalogue model runs on the bundled
  sherpa-onnx runtime.

**Accessibility review** (2026-10-23), in the same change:

- Dictation Settings announces "Speech engine: X. Press OK to keep it." when
  Speech Models returned a different model. Focus comes back to the Better
  Accuracy button, not the engine list, so the change was otherwise silent,
  and the reminder that OK keeps it is what makes the save-then-offer order
  above discoverable.
- Remove writes "X was removed. N MB freed." to Progress and returns focus to
  the model list. Remove itself is disabled once the model is gone, and focus
  left on a disabled button falls to nowhere.

Tests: `test_dictation_models_dialog.py`, `test_lite_dictation.py`,
`test_transcribe_app.py`.

## 39. Measured, 2026-10-23: Nemotron live, whisper.cpp, and the benchmark gate

The two measurements section 37 left open, and the gate do.md asked for. The
full record, with every table and the method, is
`docs/qa/dictation-live-and-whispercpp-2026-10-23.md` and its `.json`; the
public summary is the website's `dictation-evidence.html`.

**Nemotron live** (`dictbench --latency`: the real recogniser, voice detector
and `NemotronLive` at real speed). At a normal level, live and phrase scored the
same on FLEURS (10.0 and 10.1 percent) and live was better on the held-out
audiobooks (4.6 against 5.3), in about 1.0 GB rather than 1.5, with text 1.1 to
1.5 seconds after a pause at p95. Phrase mode undersold it, as suspected; and
FLEURS as published (13.7) undersold it further, because many of its recordings
are very quiet and Nemotron is level-sensitive (10.1 levelled). No
recommendation changes: Nemotron stays the model for the live preview.

**Quiet speech in live dictation.** At FLEURS's published levels (-50 to -68
dBFS) the shared Silero voice detector (threshold 0.5) never reported speech for
17 of 200 recordings, nearly all straight after a louder one, reproducibly. Every
engine's live path goes through it. Candidate fixes: level the input before the
detector, or an adaptive threshold for quiet input; either needs testing with
real microphones before it ships. The guides now say a microphone set very low
can make dictation miss speech.

**whisper.cpp base** (Locked Dictation's default, `service.preferred_dictation_provider_id`):
6.9 percent on the held-out audiobooks and 9.2 on FLEURS, against 7.4 and 10.8
for sherpa-onnx Whisper base; about 320 MB against 820; but 0.44 per thread
(twice sherpa-onnx's 0.22) and text 4.7 seconds after a phrase on one thread, 2.7
on four, because it encodes a 30-second window per run. The decision this
section 32.6 deferred ("whisper.cpp as the default ... after B-1") now has its
data; it is not taken here.

**The benchmark gate** (`scripts/dictation_speed_gate.py`, `tests/corpus/dictation`,
`.github/workflows/dictation-benchmark.yml`). Its data half runs on every pull
request; its model half weekly. Its first run on this machine failed Whisper
tiny for Spanish: 5.0 times Moonshine tiny against the catalogue's 2.6, because
Whisper's cost per second rises on short phrases (2.7 on 8.6-second recordings,
4.3 to 4.5 on 6- to 7-second ones). Every cost factor was measured on recordings
of about ten seconds. Re-measuring them all at dictated-sentence length is the
coherent fix and changes at least one recommendation (the quickest Spanish
model), so it is a decision for Jeff, not taken here; until then the weekly run
reports it.
