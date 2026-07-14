# Voice Interaction in QUILL

QUILL can be driven by voice — hands-free, on your own device, with nothing
uploaded. This page is the complete reference for what voice can do today, how
each mode works, exactly which spoken commands are understood, and the safety
rules that never change.

Everything here is part of the **Hey QUILL** program. It is off by default,
always off in Safe Mode, and every layer keeps recognition on your machine.

## The one safety rule

**Voice can only run a curated, non-destructive allowlist of commands.** Saying
the wrong thing cannot close a document without saving, send, publish, or
delete anything — those actions are simply not in voice's vocabulary. The same
allowlist bounds the AI agent. If you ask voice something it does not
recognize as a safe command, it tells you what it heard and does nothing.

## Turning voice on

1. Open **Settings** and turn on **Voice commands (push-to-talk)**. This one
   switch enables every voice mode below.
2. Make sure an offline speech model is installed (QUILL offers to download one
   the first time you use voice; it is a one-time on-device download).
3. Optionally assign keyboard shortcuts to the voice commands under
   **Settings → Keyboard**, so you can start them without the menu.

Voice is unavailable in Safe Mode, and needs microphone-capture support (the
optional `sounddevice` component, included in standard installs).

### Choosing the recognition engine

Voice interaction runs on an on-device speech engine, and you can choose which
one under **Settings → Voice recognition engine**:

- **Follow main engine** (default) — uses whatever engine you already use for
  dictation.
- **whisper.cpp** — favors accuracy. A good choice for Voice Command and
  Conversation Mode when you want the most reliable recognition.
- **Vosk** — fast and light, with low idle cost. **Recommended for the
  always-listening "Hey QUILL" wake word**, where a small, quick engine matters
  more than transcription polish.

Whichever you pick, you need a model installed for that engine (download one
from **Tools → Speech → Manage Speech Models**). If the chosen engine or its
model isn't available, QUILL automatically falls back to your main engine, so
voice always works.

## The four ways to use voice

QUILL's voice support was built in four layers. Each one builds on the one
before it, and they share the same on-device recognition and the same safe
allowlist.

### 1. Voice Command (push-to-talk)

**Tools → Speech → Voice Command (Offline).**

The simplest mode. Run the command, speak **one** command, run it again to stop
and act. QUILL recognizes the phrase on your device and runs the matching
command. Say **"cancel"** or **"never mind"** to abort.

Best when you want to fire a single command without touching the keyboard.

### 2. Voice Conversation Mode

**Tools → Speech → Voice Conversation Mode.**

The hands-free version. Run it once and QUILL listens for a command, then keeps
a short **follow-up window** open after acting so you can chain commands —
"next heading", then "read aloud", then "word count" — without arming again
between them. A warm audio cue marks every state:

| Cue | Meaning |
|-----|---------|
| Rising three-note chime | Conversation mode turned on |
| Soft two-note | The microphone is open; speak your command |
| Gentle rise | Your command was recognized (a brief "cancel" window follows) |
| Sparkle | The action finished |
| Quiet tick | QUILL is still working, so the wait is never silent |
| Calm falling tone | Nothing matched |
| Settling tone | Relaxed back to rest |

Run it again, or say **"stop"**, to turn conversation mode off.

Your turn ends **when you stop speaking** — QUILL listens to the microphone's
energy and finishes the turn after your pause, rather than cutting you off at a
fixed time. You can make it more personal, too: set **your name** in Settings
and QUILL uses it in its prompts ("Listening, Jeff."), with wording that varies
naturally and follows the time of day. If you'd like the prompts **spoken
aloud**, turn on *Speak prompts aloud*; QUILL keeps that silent whenever a
screen reader is running, so it never talks over your reader.

**Timing you can tune** (Settings; set any to 0 to switch that part off):

- **Pause before a command ends** — how long a pause finishes what you are
  saying (used by the silence detection above).
- **Cancel window** — the beat after recognition during which "cancel" calls
  it off.
- **Follow-up window** — how long QUILL keeps listening after acting.
- **Still-working tick interval** — how often the "working" tick plays.

The nine cues are ordinary **Sound Events** — retune or replace them in any
sound pack from the Sound Events dialog, exactly like every other QUILL earcon.

### 3. "Hey QUILL" wake word

**Tools → Speech → Listen for Hey QUILL.**

Always-listening. QUILL listens continuously, on your device, for the phrase
**"Hey QUILL"**. Two ways to use it:

- **"Hey QUILL, save file"** — the trailing command runs straight away.
- **"Hey QUILL"** on its own — QUILL wakes and listens for your next command.

While it is on, the status bar shows that the microphone is live and plays a
periodic reminder, so an open microphone is never a surprise. Run the command
again, or say **"stop"**, to turn listening off instantly.

**It stays off unless you say otherwise.** Always-listening turns itself off
when QUILL closes; a separate setting — **Keep listening for "Hey QUILL" across
restarts** — lets you have it resume automatically at startup if you want that.

### Checking what voice is doing — Speak Voice Status

**Tools → Speech → Speak Voice Status** tells you, at any moment, exactly what
voice is up to: listening for "Hey QUILL", in conversation mode, capturing a
command, or not listening at all. It is a quick way to confirm the microphone
state — assign it a shortcut for an instant check.

### 4. Ask a question — routed to Ask Quill

When you speak something that is a **question** rather than a command — either
starting with "ask" ("ask what a heading is") or shaped like a question ("how
do I save my document") — voice hands it to **Ask Quill**, QUILL's AI
assistant, with your question **pre-filled and ready to send**.

You press Enter to send it, so a person is always in the loop for anything that
reaches the AI. Ask Quill answers with its own spoken-reply and change-review
tools. This needs AI to be set up; if it is not, Ask Quill offers to set it up
rather than failing. Questions are only routed to AI — voice never sends
anything to a network service on its own.

## What voice can run — the command allowlist

These are the commands voice understands today, with the phrases that select
each. Matching is forgiving: the command's own name works too, and close
phrasings still match.

| Say | Runs |
|-----|------|
| "save", "save file", "save document" | Save |
| "save all", "save everything" | Save All |
| "new", "new document", "new file" | New |
| "undo" | Undo |
| "redo" | Redo |
| "select all" | Select All |
| "bold", "make bold" | Bold |
| "italic", "make italic" | Italic |
| "uppercase", "make uppercase" | Upper Case |
| "lowercase", "make lowercase" | Lower Case |
| "title case" | Title Case |
| "sentence case" | Sentence Case |
| "bullet list", "bulleted list" | Insert Bullet List |
| "numbered list" | Insert Numbered List |
| "word count", "count words" | Word Count |
| "spell check", "check spelling" | Spell Check |
| "read aloud", "start reading", "pause reading" | Read Aloud (start/pause) |
| "stop reading", "stop read aloud" | Stop Read Aloud |
| "next heading" | Next Heading |
| "previous heading", "prior heading" | Previous Heading |
| "outline", "show outline" | Outline Navigator |
| "find", "search", "find text" | Find |
| "soft wrap", "word wrap" | Toggle Soft Wrap |
| "command palette", "commands" | Command Palette |

Anywhere you can speak a command, you can also say **"cancel"**, **"never
mind"**, **"stop"**, or **"dismiss"** to abort.

## Privacy and control at a glance

- **On-device.** All speech recognition uses the offline engine. No audio and
  no transcript leave your computer for any voice mode. (Only Ask Quill, when
  *you* press send on a routed question, contacts the AI you configured — with
  the consent you already granted it.)
- **Off by default.** Every voice mode is off until you enable voice commands,
  and each listening session is something you start.
- **Safe Mode.** All voice modes are disabled in Safe Mode.
- **Instant off.** Running a mode's command again, or saying "stop", ends it
  immediately; always-listening also ends when QUILL closes unless you opt into
  persistence.
- **Perceivable.** Warm audio cues and a visible status keep the state of a
  hands-free session — and a live microphone — always knowable.

## Roadmap

Voice interaction shipped in four phases, and the polish refinements followed:
true silence detection (your turn ends when you stop speaking), personalized
and optionally-spoken prompts with screen-reader parity, and the Speak Voice
Status check are all in place. The one genuinely future item is a dedicated
low-power keyword spotter for the wake word (so always-listening costs even
less than it does today).
