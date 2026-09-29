# Dictation plan, revised: reliable, magical, and kind to modest computers

For QUILL Lite 1.1 and after, and QUILL through the shared code. This supersedes
`dict.md`: everything in it is here, plus speech models and "teaching" dictation
your words. Other speech languages are deliberately left out.

Written 2026-09-28. Nothing here is built yet.

Sources: VS Code's public repository and documentation (built-in dictation,
1.131, July 2026), QUILL Lite 1.1's own dictation (`quill/core/windows_dictation/`),
and our engine measurements
(`docs/design/dictation for windows only/engine-comparison.md`, 2026-09-25).

---

## 1. The rule that decides everything: it must run on a modest computer

QUILL Lite is for people who often have the computer they were given, not the
one they would choose -- and who are running a screen reader at the same time,
which has to stay instantly responsive. So:

**The baseline machine** (what every default must run well on):

- Windows 10, 64-bit, 4 GB of memory.
- A low-end, several-years-old dual-core CPU (the class of the machine the
  2026-09-25 comparison ran on), no GPU help assumed.
- NVDA or JAWS running, plus a browser or mail program open.
- Possibly on battery.

**The budgets every engine and feature must meet on that machine:**

| Budget | Limit | Why |
|---|---|---|
| Speed | 0.25 or less (seconds of computing per second of speech, one CPU thread) | leaves three quarters of a core for the screen reader and everything else |
| Memory while dictating | 600 MB or less in total for dictation | 4 GB machines are already paging with a browser open |
| Screen-reader delay | no audible lag in speech or braille while dictating | the reader is the user's whole interface |
| Idle cost | nothing when dictation is off | no model loaded, no microphone open, no thread spinning |
| First word written | within 1.5 seconds of the pause | the pause is the "enter key"; waiting longer feels broken |

**How we hold ourselves to it:**

- **A benchmark gate.** The comparison tool (`dictbench.py`) grows a
  "baseline machine" mode and a CI-runnable check on recorded speech: every
  engine we ship or offer must meet the speed budget on one thread, and its
  memory high-water mark is recorded. An engine that fails is not offered.
- **A two-second check on the user's own computer.** The first time dictation
  starts (and after any engine change), QUILL Lite times one short built-in
  clip on this machine. If an engine cannot keep up here, it is not offered
  here, and the settings say why in plain words.
- **A live keep-up watchdog.** If phrases start queueing faster than the engine
  clears them (the machine is busy, or on battery saver), dictation says "This
  computer is busy; switching to the faster speech engine" and moves to
  Moonshine tiny, rather than falling further and further behind.
- **Everything off when dictation is off.** Models load on the first Ctrl+F11
  and unload after a few idle minutes.

Today's engines already fit: Moonshine tiny runs at 0.04 (a twenty-fifth of real
time) and Whisper tiny.en at 0.15. Anything new has to fit the same box.

---

## 2. Phase 1 -- reliability (recommended for 1.1)

### 2.1 Hold-to-talk on Ctrl+F11

Hold Ctrl+F11 for about half a second and dictation runs until you let go; a
quick press still toggles, as today. (VS Code's hold mode.) Reuse QUILL's
existing push-to-talk key handling (`quill/ui/media/voice_capture.py`,
`main_frame_speech_voice.py`) rather than writing a second one. Start tones on
hold, stop tone on release, no extra speech. Setting "Hold Ctrl+F11 to talk", on
by default; off makes it a pure toggle for people for whom holding a key is
hard. *Low-end cost:* none.

### 2.4 Words go where you started speaking

The insertion point is captured when a phrase starts. If you move the caret or
switch documents while it is still being recognised, the words still go there,
and you hear "Written where you started, in <document>". If that spot no longer
exists, they go at the caret and you are told. The existing phrase history
(`history.py`) already refuses to scratch a phrase whose text has changed; this
applies the same care on the way in. *Low-end cost:* none -- and on a slow
machine, where recognition takes longer, it matters most.

**Phase 1 docs:** user guide Dictation chapter, 1.1 release notes, changelog,
the Dictation commands page, F1 help for each new setting. **Tests:** each
behaviour against a fake engine and a fake capture stream; the command coverage
gate stays at zero `shape_only`.

---

## 3. Phase 2 -- talk to your writing tools (1.1 if time allows, else 1.2)

### 3.2 Talk to the AI

In the AI Conversation window, a dictated message is sent after your pause, and
the reply is read aloud (VS Code's voice chat with auto-synthesize). A setting
chooses: send after the pause, or wait for Enter. One request per message, as
now. *Low-end note:* while the reply is read, dictation mutes the microphone so
the speech is not heard back as input -- cheaper and more reliable than echo
cancellation.

---

## 4. Speech models: what to add, and what a modest computer can carry

### 4.1 What VS Code uses

VS Code's built-in dictation downloads NVIDIA's **Nemotron 3.5 ASR Streaming
0.6B** on first use: a 600-million-parameter model that runs on the device,
never sends audio anywhere, recognises in small chunks *while* you speak, and
punctuates and capitalises by itself. Community builds exist for sherpa-onnx --
the runtime QUILL Lite already uses -- including a 4-bit build of about 683 MB
(2.5 GB at full precision). Licence: NVIDIA OpenMDW-1.1, which must be read
before we redistribute anything.

### 4.2 What that means on the baseline machine

Honestly, it does not fit the defaults:

- **Size.** About 680 MB even at 4 bits -- more than five times Moonshine tiny.
  The same size class as Parakeet 3 (670 MB), which we measured and rejected on
  exactly this ground.
- **Speed.** Parakeet 3, the nearest measured relative, ran at 0.21 on one
  thread: inside the 0.25 budget, but with little room, where Moonshine tiny
  sits at 0.04.
- **Streaming costs continuously.** A streaming model does work every half
  second the whole time you talk, not once per pause. On a dual-core machine that
  is a steady load competing with the screen reader and draining a battery, where
  today's engines are idle between phrases.
- **Memory.** A 0.6B model plus the runtime is likely to exceed the 600 MB
  budget on its own; this must be measured, not assumed.

What it would buy: near-instant writing and a true live preview (4.4), on a
computer strong enough to carry it.

### 4.3 The options

1. **Keep Moonshine tiny and Whisper tiny.en as the only engines for now**
   (recommended as the default decision). They already meet every budget with
   room to spare. The reliability work in Phase 1 does more for everyday
   dictation than a bigger model would.
2. **A separate, signed "QUILL Speech Pack" installer with Nemotron** (recommended
   as the upgrade path). It keeps the "no downloads inside the app" rule: the
   main installer and portable zip stay as they are, and the pack is its own
   download a person chooses. QUILL Lite offers the engine only when the pack is
   installed **and** the two-second check (section 1) says this machine can keep
   up; on a machine that cannot, the pack says so at install time rather than
   giving a slow engine. On a modest-but-capable machine it runs with the longest
   chunk (1120 ms) to halve the work; a fast one can use shorter chunks.
3. **Download on first use from Dictation Settings, like VS Code.** Simplest for
   people, but it breaks the standing rule that nothing downloads, and it puts a
   700 MB download in front of people on slow or metered connections.
4. **Prototype first, decide after.** Measure Nemotron with `dictbench.py` on the
   baseline machine -- speed, memory high-water mark, screen-reader lag with NVDA
   and JAWS running, battery draw over ten minutes -- against Moonshine and
   Whisper. Decide between 1 and 2 on the numbers.

**Recommendation:** 1 now, 4 next, then 2 only if the prototype meets every
budget on a capable machine and degrades gracefully (refuses, not stutters) on
the baseline one.

### 4.4 A live preview for the ears (needs a streaming engine)

While you speak, the status bar Dictation part -- and a braille display -- shows
"Hearing: <words so far>", updated quietly; the final words are announced once,
as now. The accessible version of VS Code's grey preview text: it lets you catch
a mishearing before it lands. Never spoken (it would talk over you), so braille
is where it earns its keep. Only offered with a streaming engine; with Moonshine
the status says "Hearing you" as today. *Low-end:* status and braille updates are
throttled to a few a second.

---

## 5. Teaching dictation your words

### 5.1 What VS Code does

VS Code does not train its model. It has **dictation instructions**: a user file
(`~/.copilot/dictation.md`) and a per-project file (`.github/dictation.md`, read
only in trusted workspaces), created by "Voice: Configure Dictation
Instructions". With `dictation.experimental.llmCleanup` on (the default), each
transcript's **text, not audio,** is sent to a Copilot language model that
removes fillers, adds formatting and applies your preferred terms, guided by
those files on top of built-in rules (keep the meaning, prefer numerals).

### 5.3 The options

Option A (corrections in the words file) shipped 2026-09-28 as My Words and
Phrases, a window with Add Correction rather than a file to edit. Remaining:

- **B. Word biasing from the same file** (recommended, with the Speech Pack).
  Streaming transducer models run by sherpa-onnx accept a list of words to
  favour ("hotwords"). Your names and jargon come out right the first time --
  the closest real thing to training, with no cloud and no cost. Only with an
  engine that supports it; Moonshine and Whisper do not, so A covers them.
  *Low-end cost:* small; the list is capped (a few hundred entries) and checked
  against the speed budget.
- **C. "Clean up my dictation"** as an eleventh AI writing tool (recommended,
  1.1 or 1.2). Run it on a paragraph or selection when you choose; it follows a
  **My dictation instructions** file you edit in the same way (preferred terms,
  "write numbers as digits", "British spelling"). It uses the AI help rules
  already in place: the privacy agreement, one request per clean-up (not per
  phrase), and no limits with your own OpenAI key. *Low-end cost:* none on the
  computer -- the work is done by the service.
- **D. Clean up every phrase automatically, own OpenAI key only.** VS Code's
  behaviour. Not recommended: every phrase goes to the internet, costs the user
  money on every sentence, and adds a network round trip before each phrase is
  written -- slowest exactly on the modest machines and connections this plan is
  for. Free-service users could never have it anyway: 100 requests a month is
  gone in a morning of dictation.

---

## 6. Phase 3 -- magic (1.2)

- **"Correct that"**: dictation reads the two or three other things it thought
  you said, numbered; say or press the number to swap. Needs an engine that
  returns alternatives (Whisper can; Moonshine may not, and the command says
  so). *Low-end cost:* alternatives cost extra decoding, so only when asked.
- **Dictation profiles**: "Writing" and "Talking to AI", each with its own pause
  length, punctuation and filler settings; the conversation window switches to
  "Talking to AI" by itself while it has focus.
- **The live preview** (4.4), if the Speech Pack ships.

---

## 7. Recommendation, in order

Shipped 2026-09-28 (QUILL Lite 1.1, shared with QUILL): Escape to cancel, the
microphone watchdog, one Ctrl+Z per phrase, the read-only refusal, the
self-healing engine, one session at a time, dictate into any text field, recent
phrases, and the words window with corrections (5.3 A). What remains:

1. **Phase 1, the rest**: hold-to-talk (2.1) and words where you started (2.4).
2. **The low-end safeguards in section 1**: the two-second check, the keep-up
   watchdog, and unloading models when idle.
3. **Talk to the AI** (3.2) and **Clean up my dictation (5.3 C)**, 1.1 if time
   allows, else 1.2.
4. **Prototype Nemotron (4.3 option 4)**; ship it only as the separate Speech
   Pack (option 2), with word biasing (5.3 B) and the live preview (4.4), and only
   if it meets every budget on a capable machine and refuses gracefully on the
   baseline one.

## 8. Questions for Jeff

1. Hold-to-talk on by default, or off until switched on?
2. Talk to the AI: send after the pause by default, or wait for Enter?
3. Phase 2 in 1.1, or held for 1.2?
4. The baseline machine: is "Windows 10, 4 GB, older dual-core, screen reader
   running" the right floor, or should it be lower?
5. The Speech Pack: worth prototyping, or leave speech models where they are for
   now?

## Sources

- VS Code voice documentation: code.visualstudio.com/docs/configure/accessibility/voice
  (`dictation.model`, `dictation.experimental.llmCleanup`, `~/.copilot/dictation.md`,
  `.github/dictation.md`, `accessibility.voice.speechTimeout`).
- VS Code 1.131 release notes (built-in dictation, July 2026).
- VS Code source: `src/vs/workbench/contrib/codeEditor/browser/dictation/editorDictation.ts`
  (hold mode at 500 ms, preview decorations, stop and cancel, read-only refusal);
  `src/vs/workbench/contrib/accessibility/browser/accessibilityConfiguration.ts`
  (voice settings and start/stop signals); `src/vs/workbench/contrib/speech/browser/speechService.ts`
  (sessions, cancellation, keyword activation paused when the window loses focus).
- NVIDIA Nemotron 3.5 ASR Streaming 0.6B model card (huggingface.co/nvidia/nemotron-3.5-asr-streaming-0.6b),
  the onnx-community 4-bit build, and sherpa-onnx issue #3664.
- QUILL: `docs/design/dictation for windows only/engine-comparison.md`,
  `quill/core/windows_dictation/engines.py`, `history.py`, `vocabulary.py`, and the
  QUILL Lite 1.1 release notes' Dictation section.
