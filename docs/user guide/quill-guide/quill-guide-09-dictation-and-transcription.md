# Chapter 9: Dictation and transcription

This chapter is about turning speech into text. You will learn to talk
straight into a document, to turn a recording into a transcript, and to have
QUILL make meeting minutes or notes out of that transcript for you. Most of it
runs entirely on your own computer, with no account and nothing uploaded. If
you would rather speak than type, or you have a pile of recordings to get
through, this chapter is for you. The first section is a map of QUILL's
speech engines, to help you choose one. The parts about speech models,
optional downloads and memory come last, for when you want to tune things.

## Which speech engine? A guide to choosing

QUILL can turn your voice into text in several ways, and you can choose the
speech engine that does the listening. This section is the map. It tells you
which setting matters for what you are doing, what each engine costs you in
privacy, speed, accuracy and memory, how to switch, and where the full details
are. You do not need to read it before you start: everything works the moment
QUILL is installed.

### The short answer

- **You do not have to choose anything.** Live Dictation (`Ctrl+F11`) starts
  with **Moonshine**, which comes with QUILL. It is fast, puts in punctuation
  for you, and keeps everything on your computer. The offline tools (Locked
  Dictation, `Ctrl+F9`, and the others below) start on **Whisper.cpp**, whose
  small engine (about 8 MB) QUILL offers to fetch the first time you need it.
  If you would rather download nothing at all, choose **QUILL speech models**
  as their engine: it includes the same built-in Moonshine.
- **If you want fewer mistakes and your speech to stay on your computer**,
  download a larger speech model. It takes a few minutes, and the worked
  example below walks you through it.
- **If you want the very best accuracy** and you are happy for your speech to
  go to a company you already pay, choose OpenAI or a speech provider with
  your own account. Nothing is ever sent until you choose one and say Yes.

### Two speech systems, one shared set of models

QUILL has two sets of speech tools. Each has its own engine setting, and
changing one never changes the other.

1. **Live Dictation and its family.** Live Dictation (`Ctrl+F11`), live
   transcripts, talking to the AI, and **Transcribe a Recording...**
   (`Shift+F5`). This is the same dictation QUILL Lite, QUILL Transcribe and
   Quill Inkwell have, on the same keys. You choose its engine in the **Speech
   engine** list in **Dictation Settings** (`Alt+Shift+F6`).
2. **The offline speech tools, which only QUILL has.** Locked Dictation
   (`Ctrl+F9`), **Dictate (Offline)**, **Transcribe Audio or Video
   (Offline)...**, **Generate Captions (Offline)...** and watch folders. You
   choose their engine in Manage Speech Models (**Tools > Speech > Speech and
   Dictation...**), or in the guided setup: **Help > Download Optional
   Components...**, row **Dictation (offline speech)**.

| What you are doing | Which engine setting it uses | Where you change it |
|---|---|---|
| Dictating as you talk (`Ctrl+F11`) | Live Dictation's | Dictation Settings, **Speech engine** |
| Transcribing a recording with `Shift+F5` | Live Dictation's models, chosen in the window each time | The **Speech model** list in Transcribe a Recording |
| Locked Dictation (`Ctrl+F9`) or Dictate (Offline) | The offline tools' | Manage Speech Models |
| Transcribe Audio or Video (Offline), captions, watch folders | The offline tools' | Manage Speech Models |
| Voice Command, Voice Conversation Mode, Hey QUILL | Their own small setting | **Voice recognition engine**, on the Transcription page in Settings |
| Dictate Here in Quill Cast or Quill Radio | QUILL Transcribe's, which follows QUILL's while dictation settings are shared | QUILL Transcribe's Dictation Settings; see "Dictating into other programs" |

**The two systems share their models.** A model you download in Speech Models
for Live Dictation, such as Nemotron or Parakeet, goes in the same folder the
offline tools' **QUILL speech models** engine reads, and QUILL Lite and QUILL
Transcribe use that folder too. Nothing is ever downloaded twice.

### Live Dictation's engines

You choose these in the **Speech engine** list in Dictation Settings
(`Alt+Shift+F6`). Each row says what the engine is like and its tier, for
example "Moonshine (fast, punctuates for you), Lightweight".

| Engine | Where your speech goes | Speed and memory | Accuracy and languages |
|---|---|---|---|
| **Moonshine** (built in, the default) | Stays on your computer | The fastest: about a twentieth of a second of work per second of speech, at most about 580 MB of memory, words about 0.2 seconds after you pause | Good with a clear voice and a decent microphone. English only; in Spanish, QUILL uses Whisper instead |
| **Whisper** (built in) | Stays on your computer | A little slower, at most about 520 MB | Try it if Moonshine often mishears you. English and Spanish |
| **A model you downloaded** | Stays on your computer | Depends on its tier; the NVIDIA models use 1.1 to 1.5 GB at most | Fewer mistakes with names, accents, fast speech and noise. Languages depend on the model |
| **Windows speech recognition** | Recognised by Windows on your computer | Light | Puts in no punctuation, so you say every mark, and often mishears a voice it has not been trained on. Any speech language installed in Windows |
| **Windows voice typing** (`Windows+H`) | Handled by Windows' own panel | Windows' own | None of dictation's commands, tones, read-back or wake phrase apply |
| **OpenAI** (your own key) | Sent to OpenAI | Depends on your connection | Very accurate, good with names. gpt-live-transcribe shows your words as you speak |
| **A speech provider** (your own account) | Sent to that company | Depends on your connection | Twelve companies; most show your words as you speak |

Every engine except Windows speech recognition puts in punctuation and
capitals for you. Moonshine and Whisper come inside QUILL's installer and
portable copy, so nothing downloads for them. This built-in Whisper is not the
whisper.cpp engine the offline tools use.

**To switch:** press `Alt+Shift+F6`, move to **Speech engine**, arrow to the
engine you want, and press `Enter` to save. Models you downloaded are listed
with "(downloaded)" after the name. The next time you press `Ctrl+F11`, the
new engine listens. **Test Microphone**, in the same window, records four
seconds and tells you what the engine heard.

**The tiers** tell you how hard an engine works:

- **Lightweight**: keeps up comfortably even on a modest computer. The
  built-in Moonshine and Whisper, Moonshine base, Whisper base.en, and both
  Parakeet models (Parakeet TDT 0.6B v3 and Parakeet Unified 0.6B).
- **Balanced**: more work than the built-in engines; keeps up on a computer
  with four or more cores. Nemotron and Whisper base.
- **High accuracy**: the fewest mistakes, for the most work; needs a capable
  computer, or patience. Whisper small and larger.

The tiers come from our tests with real recordings (see "How we chose: tested
on real speech"). Every downloaded model runs on the processor. A graphics card makes no
difference to Live Dictation. The full list of models, their sizes and their
measured speed is in "Better accuracy: optional speech models".

### The offline speech tools' engines

Locked Dictation, Dictate (Offline), Transcribe Audio or Video (Offline),
captions and watch folders use one of three engines. The guided setup on
**Help > Download Optional Components...** offers them in this order:

1. **Whisper.cpp**, the default: "light and fast, works on any computer". The
   engine itself is about 8 MB and is not in the installer; QUILL offers to
   fetch it from QUILL's own verified release the first time you need it. Then
   you choose a model in Manage Speech Models: **Tiny** (75 MB), **Base** (145
   MB), **Small** (465 MB, the recommended starting point), **Small English
   with speaker detection** (465 MB), **Medium** (about 1.5 GB) or **Large
   (v3)** (about 3.1 GB). Choose Whisper.cpp when you are not sure, and
   whenever you want a transcript that marks Speaker 1, Speaker 2 and so on:
   only its speaker-detection model does that.
2. **QUILL speech models (Parakeet, Nemotron and more)**: the very models Live
   Dictation, QUILL Lite and QUILL Transcribe use, from the same folder.
   Choose this when you already downloaded Parakeet or Nemotron for Live
   Dictation, or when you want Parakeet's great strength: it never invents
   words from silence (see "Parakeet 3 and silence"). It runs on the
   processor.
3. **Faster Whisper**: "most accurate; larger and can use your graphics card".
   It is the only engine in QUILL that uses a graphics card. It installs when
   you choose it, in a copy of QUILL that can install it; where it cannot, it
   is not offered. It has its own models (Tiny to Large v3, and an English
   Distil-Large v3). Choose it for long recordings on a capable computer,
   especially one with a graphics card. It does not label speakers.

**Which engine is used when you have not chosen.** Your own choice always
wins. Otherwise, an installed Parakeet model means the QUILL speech models
engine; then Whisper.cpp, once it has a model; and otherwise the built-in
Moonshine through the QUILL speech models engine. That last step is why
Locked Dictation needs no model: once the small Whisper.cpp engine is here,
the built-in Moonshine transcribes until Whisper.cpp has a model of its own.
Dictate (Offline), Transcribe Audio or Video (Offline) and captions do not
fall back like that: they use the engine you chose and ask you for one of its
models if it has none. With **QUILL speech models** chosen, every one of them
works with nothing downloaded, because the built-in Moonshine and Whisper
count as its models. Whisper.cpp stays the default for now.

**If you used Nemotron or Parakeet in an earlier QUILL.** Locked Dictation
used to have its own Nemotron and Parakeet engines, with their own copy of the
models. They are now one engine, QUILL speech models, and your choice moved
with it; a Parakeet you had was moved, not downloaded again. QUILL tells you
once, a moment after it starts, and never over an open dialog. You hear:
"Locked Dictation's Nemotron and Parakeet engines are now one engine, QUILL
speech models..." If the older Nemotron model's files are still on your
computer, nothing uses them any more, so the same message asks a question
instead: "Delete the older files to free 650 MB? No keeps them." No is the
default, so pressing Enter keeps them. Choose **Yes** and QUILL deletes only
those old folders and tells you how much space it actually freed, for example
"Freed 650 MB." Either way you are not asked again. To dictate with Nemotron
after that, download Nemotron 3.5 in **Manage Speech Models**.

**To switch:** open **Tools > Speech > Speech and Dictation...**. On the
**Dictation (Offline)** tab, choose the **Speech Engine**, choose a model, and
press **Set as Default**. Or use the guided setup, which takes you through
engine, model and a test one step at a time; see "Setting up offline
dictation". The details are in "Manage Speech Models" and "Choosing a speech
engine", later in this chapter.

### Privacy at a glance

- **Nothing leaves your computer** with Moonshine, Whisper, any model you
  downloaded, Windows speech recognition, Whisper.cpp, the QUILL speech models
  or Faster Whisper. The only thing that comes over the internet is a model or
  engine file, once, when you ask for it and answer a question about it.
  Every file is checked against a fingerprint, and a damaged one
  is never used.
- **Your speech is sent to a company** only with OpenAI or a speech provider,
  and only after you choose one and answer Yes.
- **QUILL's free AI never carries your voice.** It is not used for dictation
  at all.
- **AI > Transcribe Audio > Transcribe Audio File...** and the cloud
  providers on the **Dictation (Online)** tab are separate: they upload a
  recording only when you ask them to transcribe it. See "Transcribe Audio
  File" and "Cloud transcription providers".

### Cloud engines: OpenAI and the twelve speech providers

You may already pay for a speech service. Live Dictation can use **OpenAI**,
with your own OpenAI key, or one of twelve **speech providers**, with your own
account: Microsoft Azure AI Speech, Google Cloud Speech-to-Text, Amazon
Transcribe, Deepgram, AssemblyAI, Speechmatics, ElevenLabs Scribe, Gladia,
Rev.ai, Groq, Mistral Voxtral and IBM Watson Speech to Text.

- **Your own account.** The company bills you, not QUILL. QUILL shows no
  prices and counts nothing, so check the company's own usage page.
- **What is sent.** Each phrase dictation hears, over an encrypted connection,
  and the words come back. Silence is never sent. Names from My Words and
  Phrases go with it as words to expect, where the company supports that.
  Nothing passes through QUILL's servers, and QUILL keeps no copy of your
  voice.
- **Your agreement.** Choosing one in the **Speech engine** list asks a
  question that says exactly what is sent and to whom. **No** is the default:
  if you just press `Enter`, nothing is sent.
- **Your keys.** An OpenAI key is saved in **Use My Own AI Key** (`Alt+F2`).
  A provider's details are saved in **Speech Providers...** (`Alt+V`) in
  Dictation Settings, where **Test Connection** (`Alt+T`) checks your account
  without sending speech. Keys go straight to Windows Credential Manager and
  are never written in QUILL's settings or logs.
- **Safe Mode** turns every cloud engine off.
- **If the connection drops**, that phrase is lost, you hear one sentence, and
  dictation keeps listening. QUILL never switches to another engine by itself.

Setting them up is explained step by step in "OpenAI dictation, with your own
key" and "Speech providers: dictation with your own account at another
company".

### Worked example: fewer mistakes on an 8 GB laptop

Sam has a laptop with four processor cores and 8 GB of memory. Moonshine is
quick, but it keeps getting colleagues' names and fast sentences wrong. Sam
wants fewer mistakes, and wants the speech to stay on the laptop.

1. Press `Alt+Shift+F6` to open Dictation Settings. The read-only
   **Recommended for this computer** line already names a model and says why.
2. Press **Better Accuracy: Speech Models...** (`Alt+B`).
3. Press `Alt+W` to reach **What matters most**, and choose **The fewest
   mistakes**.
4. Press `Alt+C` to read the **Recommendation** box. On this laptop it names
   **NVIDIA Parakeet Unified 0.6B**, and says whether it keeps up here, about
   how soon words appear after a pause, that the speech stays on this
   computer, and that the download is 663 MB. In our tests with real
   recordings it got 3.2 percent of words wrong, the fewest of any model that
   keeps up on one processor thread.
5. Press **Show Recommended Model** (`Alt+S`) to move to it in the list, and
   **Details** (`Alt+T`) to read about it.
6. Press **Download...** (`Alt+D`). A question names where it comes from, its
   size, its licence and the folder it goes in. Answer Yes. You hear
   "Downloading", then every quarter of the way. **Cancel Download** (`Alt+L`)
   stops it, and pressing Download again later carries on from where it
   stopped.
7. When it says the model is downloaded, press **Use for Dictation**
   (`Alt+U`), or **Switch to Recommended Model** (`Alt+H`), then **OK** in
   Dictation Settings. If Sam had downloaded another model before, a question
   offers to delete it to free its space. No is the default.
8. Press `Ctrl+F11` and talk. Parakeet Unified writes each phrase when you
   pause.

Sam would like Locked Dictation to use it too. In **Tools > Speech > Speech
and Dictation...**, Sam chooses **QUILL speech models** as the speech engine,
chooses Parakeet Unified, and presses **Set as Default**. Nothing downloads
again.

If Sam would rather see the words while speaking, **NVIDIA Nemotron 3.5 ASR
Streaming 0.6B** does that, at the price of more mistakes (5.3 percent of
words wrong where Parakeet Unified got 3.2). The advice depends on the
computer, for example:

| Computer | A balance | The quickest response | The fewest mistakes |
|---|---|---|---|
| 4 GB, 2 cores | Moonshine | Moonshine | Moonshine base |
| 8 GB, 2 cores | Parakeet TDT 0.6B v3 | Moonshine | Parakeet Unified, on two threads |
| 8 GB, 4 cores | Parakeet Unified | Moonshine | Parakeet Unified |
| 16 GB, 8 cores | Parakeet Unified | Moonshine | Parakeet Unified |
| 4 GB, 2 cores, dictating in Spanish | Whisper | Whisper | Whisper |
| 8 GB, 4 cores, dictating in Spanish | Parakeet TDT 0.6B v3 | Whisper | Parakeet TDT 0.6B v3 |

When little memory is free at the moment you ask, the advice names a lighter
model on any computer, usually the built-in Moonshine (English) or Whisper
(Spanish).

The recommendation is only advice. It never changes your engine, it never
suggests a cloud engine, and its figures come from our tests with real
recordings, on one computer; yours may differ. Your own voice is the real test: use a model for a day, and keep the
one that needs fewer fixes (see "How to tell which is more accurate for you").

### What is not available yet

- **Speech providers are for Live Dictation only.** They are not offered in
  Transcribe a Recording, Transcribe Audio or Video (Offline), captions or
  watch folders. OpenAI, with your own key, is offered in Transcribe a
  Recording.
- **Google, Groq and Mistral show no words while you speak.** Each phrase is
  written when you pause.
- **Spanish commands.** You can dictate Spanish text now, but commands such as
  "scratch that" stay in English for now. See "Dictating in Spanish".
- **A graphics card** helps only Faster Whisper. Every other engine runs on
  the processor.
- A few further speech features, such as a small listener just for the
  command word, are built but not switched on yet.

## Dictating into a document

QUILL gives you three ways to dictate. **Live Dictation** writes each phrase
as you pause, which suits most people most of the time. **Locked Dictation**
records a whole passage and writes it when you finish. **Dictate (Offline)**
is the simple start-and-stop toggle on the Speech menu. All three put the
words at your cursor, and all three work without an internet connection.

> **QUILLBee's tip:** Can't remember what you are allowed to say? While Live
> Dictation is running (`Ctrl+F11`), just say "what can I say" and the whole
> list opens in a window.

### Live Dictation (Ctrl+F11)

This is the dictation QUILL Lite has, in QUILL too, on the same keys. It lives
at **Tools > Speech > Live Dictation**.

1. Put your cursor where you want the words.
2. Press `Ctrl+F11`.
3. Talk, then pause. Each phrase is written at the cursor when you pause. A
   soft tone tells you it arrived, and the words are read back to you.
4. When you are done, press `Ctrl+F11` again, or say "stop dictation".

If you would rather hold `Ctrl+F11` down while you talk and let go to stop,
you can turn that on; see Holding Ctrl+F11 to talk, below.
**Dictation On**, the first row of the submenu, is checked while dictation is
writing, and the status bar says what dictation is doing.

Nothing leaves your computer, nothing is downloaded, and no recording is kept,
unless you choose OpenAI dictation with your own key, or a speech provider
with your own account (see "Which speech engine? A guide to choosing" above). Unlike **Locked Dictation**, which records a
passage and transcribes it afterwards, Live Dictation writes as you go.

The same submenu has more windows:

- **Recent Phrases...** (`Shift+F11`) lists the last twenty phrases of the
  session, with Insert Again and Copy. Words a correction replaced are there
  too, marked "(before correction)", so nothing a correction changed is lost.
  After them come any words kept from before. See "Words that were not
  written, and dictation history".
- **My Words and Phrases...** (`Alt+Shift+F10`) is a window with Add Word, Add
  Phrase, Add Correction, Edit and Remove. It edits your `dictation.md` file for
  you. **Import...** and **Export...** move the list to another computer or
  another copy. See "Importing and exporting your words".
- **Switch Dictation Language** (`Ctrl+Shift+F11`) swaps between English and
  Spanish. See "Switching between English and Spanish".
- **Start or Stop Live Transcript** (`Ctrl+Alt+Shift+PageDown`) writes
  everything you say into a new document of its own. See "Live transcripts".
- **Dictation Context for This Document...** (`Ctrl+Alt+Shift+PageUp`) tells
  QUILL what this document is, in a sentence. See "Dictation Context for This
  Document".
- **Speak a Command** (`F11`) makes the next thing you say a command, as if you
  had said QUILL first. Press it twice for command mode. See "The command word".
- **Review Dictation...** (`Shift+F4`) holds the last phrase in a window to
  read, change and insert once. See "Review before inserting".

Here are the dictation keys in one place:

| Command | Key |
|---|---|
| Start or stop Live Dictation | `Ctrl+F11` |
| Recent Phrases | `Shift+F11` |
| Switch Dictation Language | `Ctrl+Shift+F11` |
| Start or Stop Live Transcript | `Ctrl+Alt+Shift+PageDown` |
| Dictation Context for This Document | `Ctrl+Alt+Shift+PageUp` |
| Dictation Status | `Alt+F9` |
| My Words and Phrases | `Alt+Shift+F10` |
| Dictation Settings | `Alt+Shift+F6` |
| Tidy Dictated Text | `Ctrl+F3` |
| Speak a Command | `F11` |
| Review Dictation | `Shift+F4` |

A few things that are good to know while you talk:

- **Escape** throws away the phrase being heard, and the words heard so far.
- Your words go where you were when you started speaking, even if you move
  the cursor while they are being recognised (see "Where the words go").
- Pressing `Ctrl+F11` in a second document moves dictation there.
- If your microphone goes away, dictation pauses, and it picks up again when
  the device is back.
- If the engine has a problem, QUILL quietly restarts it once before it tells
  you about a failure.

The full list of everything Live Dictation understands is its own page,
**[Dictation commands](../dictation-commands.html)**, built from the same table
QUILL itself reads. While dictating, say **"what can I say"** to open that list
in a window. Near its end are **Worked examples** (what you have, what you
say, what you get: going before and after words, picking the second of three
matches, Copy All, scratch that, all twelve clips, snippets with spaces in
their names, every capitals command, an email address spelled with pauses, and
Markdown) and **Limits**, including what cannot work when dictating into
another program. Every example there is checked by QUILL's automated tests in
both QUILL and QUILL Lite. How accurately and how quickly each engine hears you
has not been measured yet; that waits on the dictation benchmarks.

#### The command word

Commands such as "scratch that" work when you say them on their own, after a
pause. To be sure a command is taken as a command and never written, say the
command word first: **"QUILL scratch that"**, **"QUILL select the cat"**,
**"QUILL caps on"**. Every command in the list works this way.

- **QUILL counts only as the first word after a pause.** "I told Quill about
  it" is written as words.
- **If what follows is not a command, nothing is written.** You hear the
  error sound and "Not a command. Say it again, or say QUILL type that to write
  it." Say **"QUILL type that"** and the words are written after all, once.
- **To write the word itself**, say **"literal QUILL"**.
- **Say "QUILL" on its own**, then pause, and the next thing you say is a
  command. A short rising tone tells you QUILL heard it.
- **Command mode**: say **"QUILL command mode"**. You hear the tone and
  "Command mode", and everything you say is a command, without the word,
  until you say **"dictation mode"**. If you give no command for eight seconds,
  command mode ends by itself with a falling tone, and what you say next is
  written again. The status bar says "Command mode" while it lasts.
- **Speak a Command** (`F11`) does the same from the keyboard. Press it and
  the next thing you say is a command. Press it twice for command mode, and
  once more to go back to dictation. If dictation is off, it starts dictation
  first.

Three choices in **More Dictation Settings** go with it: the command word
itself (`Alt+C`; empty means no spoken command word, so only `F11` gives
commands), **Commands only after the command word (strict mode)** (`Alt+E`),
and how many seconds command mode waits (`Alt+D`, 5 to 30). With strict mode
on, "scratch that" on its own is written as words; the stop phrase always
works. Strict mode is off in QUILL and QUILL Lite, so the commands you know keep
working, and on in QUILL Transcribe. A common word, or a word from your own My
Words and Phrases, is refused as the command word, with the reason.

#### Dictation profiles: the kind of writing you are doing

A dictation profile changes dictation for one kind of writing in one step,
instead of changing several settings each time. There are seven:

| Profile | What it changes |
|---|---|
| Standard | Nothing: your Dictation Settings as they are. Headings are written as Markdown marks, as before. Everybody starts here. |
| Email | Removes filler words and adds punctuation. Headings, bold and italic use QUILL's own formatting. |
| Document | Headings, bold and italic use QUILL's own formatting. |
| Markdown | Headings, bold and italic are written as Markdown marks. |
| Chat | Removes filler words; plain text, with no heading marks. |
| Coding | Removes filler words, adds no punctuation of its own (you say every mark), and waits longer for a pause. Markdown marks. |
| Verbatim | Keeps every word you say, fillers too; plain text. |

**Choosing one.** Open Dictation Settings (`Alt+Shift+F6`), press **More Dictation
Settings...**, and choose in **Dictation profile, for the kind of writing**
(**Alt+A**). Or, while dictating, say the profile's name after the command
word: "QUILL email mode", "QUILL markdown mode", "QUILL standard mode" ("email
profile" works too). You hear "Email profile." and the choice is kept for next
time. The status bar shows a profile other than Standard beside the dictation
modes, so a braille display shows it too.

**Lock the profile so it cannot be switched by voice** (**Alt+B**, in More
Dictation Settings) stops a spoken profile name from switching: you hear "Lock
Profile is on, so the profile stays Email." Nothing ever switches profiles on
its own.

**Profiles and the Dictation style.** While a profile other than Standard is
on, its own choice about filler words wins over the **Dictation style** in
Dictation Settings: Verbatim keeps fillers even if the style is Clean, and
Email, Chat and Coding remove them even if the style is Verbatim. A profile
never changes **Fix it when I correct myself** or polishing. Standard leaves
your style exactly as it is.

**Headings, bold and italic by voice.** "heading one" to "heading six" at the
start of a phrase, and "QUILL bold that" and "QUILL italic that" (or
"italicize that"), act on the selection, or on the phrase you dictated last.
What happens depends on the profile:

- **Markdown** and **Coding**, and **Standard** for headings: the marks are
  written. "bold that" puts two asterisks either side, "italic that" one; one
  Ctrl+Z takes it back.
- **Document** and **Email**: In a rich text document, QUILL's own Heading and Bold commands apply the
style. In a Markdown or HTML document, QUILL's own commands write the marks
or tags, and you hear "Heading 2." or "Bold." In a plain text document nothing is
  typed for the heading, and you hear "Headings work in QUILL documents or the
  Markdown profile." Bold and italic say the same about themselves.
- **Chat** and **Verbatim**: "heading two" starts a new line with your words
  and nothing else, and bold and italic say "This profile writes plain text, so
  nothing was formatted."

**Example.** In a letter written as a rich text document, choose the Document
profile, then say "heading two dear Sam" and pause. "Dear Sam" goes on a line
of its own with the Heading 2 style. Select a word, say "QUILL bold that", and
it is bold.

The settings are `windows_dictation_profile` and
`windows_dictation_profile_locked`, under the same names in QUILL, QUILL Lite
and QUILL Transcribe.

#### Importing and exporting your words

**Export...** saves your whole list to a file you name. Choose **Word list in
Markdown** for the same kind of file as `dictation.md`, or **Spreadsheet, say
and write columns** for a CSV file with three columns: `say`, `write` and
`kind` (word, phrase or correction). QUILL then says how many it saved, such as
"Exported 15 entries to my-dictation-words.md."

**Import...** reads a Markdown word list or a CSV file and adds what is new.
A CSV file needs a `say` column; `write` and `kind` are optional. A row with
nothing to write is a word, and any other row is a phrase unless `kind` says
correction. Before anything changes, a window shows how many entries will be
added and how many are already in your list, with the new ones listed. Press
**Add Them** to add them, or **Cancel** to change nothing. Then you hear, for
example, "Imported 12 words, 3 already there."

Import never replaces anything. If the file has a word or phrase you already
have, but spelled or written differently, yours is kept, and QUILL tells you
how many differed. Your list as it was is saved first, as
`dictation-before-import.md` beside `dictation.md`. To undo an import, copy
that file over `dictation.md`. Export a list and import it into an empty list on another
computer, and you get the same file back.

QUILL, QUILL Transcribe and Quill Inkwell all use this one list. QUILL Lite
keeps its own unless you choose **Use the shared word list** in its My Words and
Phrases window.

#### Where your word list lives

Your word list is one file, `dictation.md`, shared by QUILL, QUILL Transcribe,
Quill Inkwell and (when you choose it) QUILL Lite. Since this version it lives
in the family's own dictation folder, with your dictation instructions
(`dictation-instructions.md`) and your dictation contexts
(`dictation-contexts.json`) beside it:

- **On an installed copy:** `%LOCALAPPDATA%\QuillVille\Dictation`. To open it,
  press `Windows+R`, type `%LOCALAPPDATA%\QuillVille\Dictation` and press
  `Enter`. The speech models you download live there too.
- **On a portable copy:** the `dictation` folder inside the portable copy's own
  `data` folder. A portable copy never writes to the computer it runs on, and
  shares only with the programs in its own folder.

**How your words got there.** The first time any QuillVille program needs your
list after the update, it copies `dictation.md` and its two companions from
QUILL's data folder (`%APPDATA%\Quill`, or the data folder you chose) into the
new folder. It copies; it never moves or deletes. Your old files stay exactly as
they were, as a backup, and you do not have to do anything.

- If the new folder already has a list, it is never replaced by the old one.
- If you go on adding words in a program that still uses the old file (an older
  copy of QUILL, say), the new words are added to the shared list the next time
  you dictate, the way Import adds them: where the two lists spell something
  differently, the shared list's spelling is kept. The shared list as it was
  just before is saved as `dictation-before-merge.md` in the same folder.
- If the copy cannot be made, for example because the disk is full, QUILL goes
  on reading your old file, so your list never looks empty, and tries the copy
  again the next time.

**An example.** You taught QUILL the name "Okonkwo" last month. After the
update, open My Words and Phrases (`Alt+Shift+F10`): "Okonkwo" is still there,
now read from `%LOCALAPPDATA%\QuillVille\Dictation\dictation.md`. Add
"Tucson" in QUILL Transcribe, and the next phrase you dictate in QUILL spells
it right too.

#### Sharing dictation settings with the family

**Share dictation settings with every QuillVille program** (`Alt+Q`) is a check box in More
Dictation Settings. When it is on, the dictation settings you save in QUILL
are used by QUILL Lite, QUILL Transcribe and Quill Inkwell on this computer
too, and what you save in any of them reaches QUILL.

- **What is shared:** the speech engine and model, the language, the
  microphone, automatic punctuation, the pause that ends a phrase, filler
  words, the wake phrase, the command word, the live preview, review first, the
  never-type list and the rest of the dictation choices.
- **What each program keeps to itself:** its keys and tray, the working tick
  and strict mode (on in QUILL Transcribe on purpose), what you hear after each
  phrase (Inkwell starts with a tone, because your screen reader already reads
  what is typed), and every permission to send your speech to a company. Saying
  yes to OpenAI in QUILL is not saying yes in QUILL Transcribe.
- **When it arrives:** the moment you save Dictation Settings with OK, the
  others can see it. QUILL picks up what another program saved when you switch
  back to its window, and the status bar says "Dictation settings updated from
  the family." QUILL Transcribe picks it up within a second. Quill Inkwell picks
  it up the next time it starts Dictate Anywhere or opens Dictation Settings.
- **On or off to begin with:** on for a new install, where nothing has been
  changed yet. If you had already changed your dictation settings before this
  update, it starts off, so nothing you chose is replaced behind your back;
  check the box when you want to join in.
- **Nothing is lost.** The first time a program takes settings from the
  family, its own are saved first as `before-sharing-` and the program's name,
  for example `before-sharing-quill.json`, in the family's dictation folder.
- **Two programs saving at once:** the last one saved wins. Each save writes
  the whole file at once, so it is never half written.
- **If it cannot be saved for the others,** you hear why, for example "Saved
  here, but the other QuillVille programs will not see this change: the shared
  dictation settings could not be written (Access is denied)." QUILL's own
  copy is saved either way.

**An example.** In QUILL Transcribe, choose Spanish with Switch Dictation
Language (`Ctrl+Shift+F11`). Switch back to QUILL. The status bar says
"Dictation settings updated from the family.", and `Ctrl+F11` now dictates in
Spanish.

#### Review before inserting

When you want to check what you said before it goes into the document, review
it first. Your words wait in the **Review Dictation** window, and nothing goes
into the document until you insert them.

- **Say "QUILL review that"**, or press **Review Dictation** (`Shift+F4`),
  while dictating. The last phrase is taken back out of the document and opened
  in the window. If dictation was paused with words held, those are what you
  get. Press `Shift+F4` with dictation off and the window opens empty.
- **Read the words** with the arrow keys. They are in an ordinary text box, so
  your screen reader reads them by line, word and character, and a braille
  display shows them. Type to change them, or keep talking: while the window is
  open, what you dictate is written into it, not into the document.
- **Ask the AI to change them.** Type an instruction such as "make it shorter"
  in **Ask the AI to change it** (`Alt+K`) and press Enter, or say it after the
  command word: **"QUILL make it shorter"**, **"QUILL more formal"**, **"QUILL
  fix the grammar only"**. You hear "Working", then what changed, in two
  sentences at most, such as "Changed next Thursday to Friday. Removed um, so."
  QUILL works out what changed by comparing the words itself; it never repeats
  the AI's own account. When more than half the words change you hear "Large
  change" and a reminder to read it. While that is said, the microphone does
  not listen, so your screen reader is never taken for your next instruction.
  **Talk about it** (`Alt+A`) makes everything you say an instruction, without
  the command word.
- **Insert** (`Ctrl+Enter`, or say **"QUILL insert it"**) puts the words where
  they came from, as one step that `Ctrl+Z` takes back. The words as you said
  them and as they went in both go into Recent Phrases.

The window's keys, and what to say instead:

| Key | What it does | Say, after the command word |
|---|---|---|
| `Ctrl+Enter` | Insert the words | "insert it" |
| `Ctrl+R` | Read all the words aloud | "read it back" |
| `Ctrl+D` | Say again what the last change did | "what changed" |
| `Ctrl+Z` | Undo the AI's last change; with none, undo your typing | "undo that change" |
| `Ctrl+Shift+Z` | Back to the words exactly as you said them | "back to what I said" |
| `Escape` | Stop a request on its way; otherwise discard the words, asking first if the AI changed them | "discard it" |

The AI, and what is sent:

- Changing words with AI needs AI help switched on and your ChatGPT
  subscription or your own AI key, as Tidy Dictated Text does; it never uses
  the free service's allowance. Each change you ask for is one request, and the
  window's Status line says so.
- The first time, QUILL asks before anything is sent, and names who receives
  it. No is the default, and No sends nothing. Only the words in the window and
  your instruction are sent, with My Dictation Instructions if you wrote any.
  This document's dictation context goes too only if you check **Include this
  document's dictation context with requests** (`Alt+O`).
- With AI off, or in Safe Mode, "QUILL review that" says "AI is off. Your
  words were written as you said them." and leaves them where they were. The
  window still opens from `Shift+F4`, to edit and insert by hand.
- If you close the window with Close, or QUILL closes or stops unexpectedly,
  your words are kept. The next time QUILL starts it says so, and Review
  Dictation brings them back. Discard throws them away.

To send everything you dictate to the window first, turn on **Send dictation
to review first** (`Alt+V`) in More Dictation Settings. The first thing you say
opens the window, and nothing reaches the document until you insert it.

#### Polishing your dictation with AI, only when you ask

Sometimes you want the punctuation and capitals tidied without rewording
anything. **Polish** does exactly that, as one request you ask for each time.
It is off until you turn it on, and it never runs by itself.

1. Open Dictation Settings (`Alt+Shift+F6`), press **More Dictation
   Settings...** (`Alt+A`), and check **Allow polishing my dictation with AI
   when I ask** (`Alt+G`). Press OK in both windows.
2. Dictate as usual. When you want a phrase polished, say **"QUILL polish
   that"** (or "QUILL polish it"). The last phrase is taken back out of the
   document and opened in Review Dictation, then the polish request is made
   there. If Review Dictation is already open, the words in it are polished.
3. In the Review Dictation window you can also press **Polish** (`Ctrl+P`).
   That button is there only while polishing is allowed.
4. You hear "Polishing", then what changed, in two sentences at most, worked
   out by QUILL comparing the words itself. Read the words, then **Insert** (`Ctrl+Enter`)
   or take the change back with **Undo Change** (`Ctrl+Z`).

What the AI is asked: to fix punctuation, capital letters, spelling and obvious
grammar slips only, and to keep your words, your meaning, your order and your
tone. It is the same request every time.

What is sent, and when: polish uses the same AI, the same account and the same
question as the rest of Review Dictation. The first time, QUILL asks before
anything is sent and names who receives it; No is the default and sends
nothing. Only the words in the window are sent. With AI off or in Safe Mode
the Polish button is greyed out. With polishing not allowed, "QUILL polish
that" says "Polish my dictation is off" and sends nothing.

#### Correcting yourself as you talk, and dictation styles

People correct themselves mid-sentence: "meet on Thursday, no, Friday". With
**Fix it when I correct myself, like Thursday, no, Friday** (`Alt+X`) checked
in Dictation Settings, QUILL writes only what you meant:

| You say | QUILL writes |
|---|---|
| meet on Thursday, no, Friday at noon | meet on Friday at noon |
| in June, no I mean July | in July |
| I have two no three cats | I have three cats |
| call me at 5, sorry, 6 | call me at 6 |
| send it to Ana, I mean Maria (with Maria and Ana in My Words) | send it to Maria |
| Monday scratch that word Tuesday | Tuesday |

The words that mark a correction are "no", "I mean", "no I mean", "sorry" and
"scratch that word". A correction is made only between two things of the same
kind: two days (including today, tomorrow, tonight and yesterday), two months,
two numbers, or two names from the Vocabulary list in My Words and Phrases.
Everything else is written exactly as you said it, so these are left alone:

- "no, I don't think so" (nothing before the "no");
- "Is it Thursday? No, Friday." (a question and its answer);
- "I said no, Friday" (a word that is not a day before the "no");
- "I may, no, March" ("may" is a verb unless you say it as the month May).

It all happens on this computer, with no AI and no internet. It is off until
you turn it on, and a live transcript never uses it, because a transcript
keeps what the speaker said.

**Dictation style** (`Alt+Y`), just above, is a quick way to set these choices
together:

- **Verbatim: every word as I say it.** No filler removal, no correction.
- **Clean: no filler words, and my corrections fixed.** Turns on **Remove
  filler words** and **Fix it when I correct myself**.
- **Polished: Clean, then review, and polish with AI when I ask.** Clean,
  plus **Send dictation to review first** and **Allow polishing my dictation
  with AI when I ask**. It is offered only when AI help is on. Choosing it
  sends nothing: you still say "QUILL polish that" or press Polish each time.

If you change a check box yourself, the style shows **Your own mix of the
settings below**, and choosing that changes nothing.

#### Learning from your corrections

When you correct the same word the same way twice, QUILL offers to remember it,
so you do not have to correct it a third time. A correction counts when you say
"QUILL correct that" and then "choose 2", or when you say "QUILL correct Ann"
and then say the new words.

The second time, a window called **Add a Correction** asks, for example,
"Add a correction: Ann becomes Anne? It goes into My Words and Phrases, under
Corrections." **No** is the default. Press **Yes** to add it, or No
or Escape to leave it. Dictation keeps going while you answer.

On Yes the correction goes into the Corrections list of My Words and Phrases
(`Alt+Shift+F10`), the same list you can edit by hand, and the next phrase uses
it. You hear "Added: Ann becomes Anne. It is in My Words and Phrases."

Limits: each pair is offered once each time QUILL runs, whatever you answer.
Only a single word or a short phrase of up to four words is offered, never a
sentence. Nothing about your corrections is saved anywhere until you say yes.

**Words for one kind of writing.** My Words and Phrases' file can hold a
section headed, for example, `## Context: email`, with words (one a line) and
corrections (`heard => write`) meant only for that kind of writing. QUILL keeps
these sections when it saves the file. They are ready for named dictation
profiles, which are not in this version, so for now they are not used.
#### Words that were not written, and dictation history

Dictation never throws away words it could not write. If dictation pauses
because its field moved, or Windows stops typing a phrase part-way through, the
words are kept on this computer until you deal with them, even if QUILL is
closed, crashes or the computer sleeps. Stopping dictation while words are held
says so: "1 phrase held while paused was not written. They are kept in Recent
Phrases." The next time QUILL starts, it says once how many are waiting.

They are in **Recent Phrases** (`Shift+F11`), after this session's phrases,
labelled "Not written" with the time. So is a review that did not finish,
labelled "Review not finished". Choose one and:

- **Insert Again** (`Alt+I`, or `Enter`) writes it at the cursor, and then it
  is deleted from this computer;
- **Copy** (`Alt+C`) puts it on the clipboard and keeps it;
- **Discard** (`Alt+D`) deletes it without writing it.

Only words that were never written are kept, and they are sealed for your
Windows account, so another account on the same computer cannot read them.
Nothing you dictate is kept as sound.

**Dictation history** is off unless you turn it on. In More Dictation
Settings, **Keep a dictation history** (`Alt+Y`) can be Off, One day, Seven
days or Thirty days. While it is on, the text of each phrase you dictate is
kept for that long, sealed the same way, and Recent Phrases lists the earlier
ones after the words not written, newest first, labelled "Earlier" with the
time. **Clear History** (`Alt+H`) in Recent Phrases deletes all of it, after a
question whose answer is No unless you choose Yes. Turning the history off
deletes it too. Neither the kept words nor the history ever go into QUILL's
log or a diagnostic report.

#### Holding Ctrl+F11 to talk

Press `Ctrl+F11` to start dictating and press it again to stop. That is
all most people ever need, and it is how dictation starts out.

If you prefer to hold the key while you talk, like the button on a
walkie-talkie, turn on **Hold the dictation key to talk; a quick press still
turns it on and off** in **More Dictation Settings**. Then:

1. Put the cursor where you want the words.
2. Press and hold `Ctrl+F11`. You hear the two rising tones and "Dictation
   on" straight away.
3. Keep holding the keys, and say what you want to say.
4. Let go. Dictation writes your last phrase, then you hear the two falling
   tones and "Dictation off".

With that turned on, a quick press still works just the same: dictation turns
on and stays on until you press Ctrl+F11 again. QUILL tells the two apart by
how long you hold the keys. Half a second or more is a hold.

Stopping never cuts you off. If you press or let go of Ctrl+F11 while you are
still finishing a sentence, dictation waits for that phrase, writes it, and
then stops.

#### Seeing the words while you speak

With most engines, your words appear when you pause. With **Nemotron** (an
optional download, see "Better accuracy: optional speech models") or **OpenAI
dictation**, QUILL knows the words while you are still saying them, and shows
them to you:

- The status bar shows the words so far after the word **Hearing**, for
  example "Hearing: Can you send me the".
- If you use a braille display, the same words appear on it as they arrive.
- They are not in your document yet, because the engine may still change its
  mind as it hears more. When you pause, the final words go into the
  document, and the preview goes away.

You do not hear these words spoken, so nothing talks over you while you talk.
If you would like to hear them, open **More Dictation Settings** and set
**While you speak, the words heard so far** to **Show it, and say new words
quietly**. You then hear new words every couple of seconds, each one once,
and only once the engine has settled on it: a word it is still changing its
mind about is not spoken until it stops changing, and a word you have already
heard is not said again if the engine corrects it later (the words that go into
your document are always the final ones). Choose **Do not show it** to turn the
preview off.

Nemotron also gets its punctuation right at the end of a sentence now. It
decides whether a sentence was a question once it hears the next one, so a
full stop it wrote at your pause can turn into a question mark a moment later,
when you carry on talking.

#### Punctuation

**You do not need to say punctuation.** The built-in engines add full stops,
commas, question marks and capitals by themselves. When you want a particular
mark, say it ("comma", "new paragraph") and your word wins. If a pause splits a
sentence and the next part begins with a word like *and* or *which*, the full
stop the pause put in is taken back out.

**Punctuation and layout, anywhere in a phrase.** You can say "period",
"comma", "question mark", "open quote" and "close quote", brackets, "hyphen",
"dash", "slash", symbols like "at sign" and "percent sign", "new line", "new
paragraph" and "tab". Say "literal" first to write one of them as a word.

#### What you hear

After each phrase you hear a soft tone and the words read back to you, so you
know what landed without reading the line. The read-back says the punctuation
too, by the same names you would use to dictate it. You say "Hello, world." and
you hear "Hello comma world period". A new paragraph is read as "new
paragraph", a quotation mark as "open quote", and so on. That happens whatever
punctuation level your screen reader is set to, so you always know whether the
comma went in.

A few things are left quiet because saying them would only get in the way: an
apostrophe or a hyphen inside a word ("don't", "well-known"), and the point or
comma inside a number ("3.5", "1,000"). A web address reads the way you would
say it: "example.com" is "example dot com". In Spanish you hear the Spanish
names, "coma" and "punto".

The status bar and a braille display show the real characters, for example
"Dictated: Hello, world.", so on braille you read exactly what was written.

If you would rather hear just the words, turn off **Say punctuation marks in
the read-back** in **More Dictation Settings**. To choose a tone only, the
words only, both or neither, use **What you hear after each phrase** in
Dictation Settings.

**While a phrase is still being worked on.** With a large model, such as one of
the bigger Whisper models, there can be a few seconds between your pause and
the text. Turn on **Tick while a phrase is being worked on** in **More
Dictation Settings** and a soft tick plays once a second while you wait. There
is no tick for a phrase that arrives within a second. The first time in a
session that a phrase takes four seconds, you also hear "Still working on that
phrase." The ticks stop as soon as the text arrives, or if recognition fails.
While a tick plays, the microphone is not listened to for a moment, as with
every QUILL sound, so the tick is never written as speech. If your sound scheme
has no tick sound, you hear the sentence at four seconds instead, each time.
**What you hear after each phrase** decides it too: set to nothing, there is no
tick and no sentence; set to words only, there is no tick, and the sentence is
said each time a phrase takes four seconds. It is off by default in QUILL and
QUILL Lite, and on in QUILL Transcribe.

#### Letters, numbers and symbols

Most of the time you just talk and the engine writes words. For the moments
when you need something exact, an email address, a file name, a heading in a
Markdown file, here is what you can say.

**Spelling a whole run.** Say "start spelling", then the letters, then "stop
spelling". The phonetic alphabet (alpha, bravo, charlie...) is the reliable
way. Say "capital" before a capital letter and "space" for a space. While you
are spelling, punctuation goes in with no spaces around it, and "dot" (or
"point") writes a full stop. So "start spelling, juliet dot sierra mike india
tango hotel at sign echo x-ray alpha mike papa lima echo dot charlie oscar
mike, stop spelling" writes `j.smith@example.com`. Say "all caps" and every
letter after it is a capital, until you say "no caps" or the phrase ends.

**Spelling with pauses.** You do not have to say an address in one breath.
While spelling, each phrase joins the letters you spelled just before it, with
no space, so "juliet oscar", a pause, "at sign echo x-ray", a pause, "dot
charlie oscar" writes `jo@ex.co`. Say "space" when you want a space. Two
limits: only letters, digits and punctuation are written, so a whole word such
as "smith" is left out (spell it instead), and if you move the cursor between
phrases the next letters start fresh, with a space in front as usual.

**Spelling one word.** Say "spell" and the letters, all in one phrase: "spell
bravo alpha delta" writes *bad*. You do not need to start and stop spelling
for that. A sentence that only happens to begin with the word "spell" ("spell
it out for me") stays words.

**Spell that.** If a name came out wrong, say "spell that". The last phrase is
selected, and the very next phrase you say is spelled and takes its place.
After that one phrase you are back to ordinary dictation.

**Capitals and spacing that stay on.** These last until you turn them off, or
until dictation stops, and the status bar shows you which are on:

- "caps on" and "caps off" (or "capitals on" and "capitals off"): every word
  starts with a capital, handy for titles and names.
- "all caps on" and "all caps off": everything in capitals.
- "no space on" and "no space off": the words are joined with no spaces and
  no automatic capitals, for web addresses and file names.

**Marks for Markdown and code.** These can go anywhere in a phrase:

| Say | Writes |
|---|---|
| "backtick" or "back quote" | a backtick, the mark under Escape on most keyboards. QUILL counts the ones on the line, so the next one opens or closes |
| "triple backtick" or "code fence" | three backticks on a line of their own |
| "tilde" | a tilde |
| "vertical bar" or "pipe symbol" | a vertical bar |
| "caret" | a caret |
| "greater than sign" | a greater-than sign |
| "less than sign" | a less-than sign |

**Starting a line.** These only work as the first words of a phrase. If the
cursor is not at the start of a line, QUILL starts a new one first:

| Say | Writes |
|---|---|
| "bullet" or "list item" | a hyphen and a space, a bullet in Markdown |
| "numbered item" | 1, a full stop and a space |
| "block quote" | a greater-than sign and a space |
| "heading one" to "heading six" (or "heading 1" to "heading 6") | one to six number signs and a space |

Because they only count at the start, "the heading two lines down" in the
middle of a sentence is written as words, just as you meant it.

**A Markdown link, by voice.** Say "open bracket the guide close bracket open
paren page close paren" and QUILL writes `[the guide](page)`, with no space
between the closing bracket and the opening parenthesis, which is what makes
it a link. It works across two phrases too, if you pause after "close
bracket". An asterisk and an underscore join the words on both sides
(`two*three`, `snake_case`), so for bold text say "bold that" with the
Markdown profile rather than saying the asterisks.

#### Voice commands

**Commands, as a whole phrase after a pause:**

- "scratch that" removes the last phrase
- "undo that"
- "select that"
- "capitalize that", "all caps that", "no caps that"
- "delete word", "delete sentence", "delete previous paragraph"
- "read that" reads all of what last went in, a whole snippet included
- "read last sentence", "read last paragraph", "read selection"
- "go to beginning of line", "go to end of line", "go to top", "go to end of
  document"
- "select sentence", "select line", "select paragraph"
- "go to start of paragraph", "go to end of paragraph"
- "spell that", "caps on", "no space on" and the others in "Letters, numbers
  and symbols"
- "copy that", "copy all", "show clips", "show snippets"
- "stop dictation"

**Reading back, a worked example.** You have dictated "Thanks for the notes
comma I will send the draft on Friday period" and want to check it by ear.
Say "read last sentence": you hear "Thanks for the notes comma I will send the
draft on Friday period", with the marks named when **Say punctuation marks in
the read-back** (More Dictation Settings) is
on, so a missing comma is easy to catch. "read last paragraph" (or "read this
paragraph") reads the whole paragraph the cursor is in, and "read selection"
reads what you selected ("Nothing is selected." when nothing is). "read that"
reads all of what last went in, so after "insert snippet sign off" it reads the
whole snippet, not only its name. Reading never moves the cursor or changes
the text. In another program only "read that" works, because QUILL reads only
the words it typed there.

**Commands with words after them**, said at the start of a phrase:

- "select" and some words, "go to", "go before" or "go after" and some words,
  "correct" and some words (see "Moving and selecting by voice")
- "replace" some words "with" new words, and "change that to" and new words
  (see "Replace and change that")
- "paste clip three", "insert snippet" and a name, "insert abbreviation" and a
  trigger (see "Snippets and clips by voice")
- "switch to Spanish" (see "Switching between English and Spanish")
- "dictation context" and a name (see "Dictation Context for This Document")

If you have typed into the last phrase since you said it, the commands that
change it leave it alone, and tell you so.

That is the everyday set. Every command and every mark, in English and
Spanish, is on the **[Dictation commands](../dictation-commands.html)** page, and
"what can I say" opens the same list while you dictate.

**More about reading back.** Reading back also works in a document that is
read-only, because it changes nothing. If there is nothing before the cursor
you hear "There is no sentence here." (or paragraph). To hear the words
without the mark names, clear **Say punctuation marks in the read-back**. In
Spanish, say "lee la última frase", "lee el último párrafo" (or "lee este
párrafo") or "lee la selección"; "leer" works as well as "lee".

#### Moving and selecting by voice

You can move around and pick out words by saying them, without reaching for
the keyboard. Say these at the start of a phrase:

- **"select" and the words**, for example "select the blue car". QUILL looks
  back from the cursor for the nearest place those words appear, and if they
  are not behind you, it looks ahead. Whatever you say next replaces them.
- **"select" one set of words "through" another**, for example "select dear
  Sam through regards". Everything from the first to the last is selected.
- **"go to" or "go before" and the words** puts the cursor just before them.
  **"go after"** puts it just after.
- **"correct" and the words** selects them and tells you "Correcting the blue
  car. Say the new words". Say the right words and they take the place of the
  wrong ones.
- **"select again"** or **"select next"** moves on to the next place the same
  words appear, and **"select previous"** goes back to the one before.

And these as a whole phrase: "select sentence" (or "select this sentence"),
"select line", "select paragraph", "go to start of paragraph" (or "go to
beginning of paragraph") and "go to end of paragraph".

You do not have to be exact. Capitals, punctuation and accents do not matter,
and numbers match either way, so "select two cats" finds "2 cats". Your
corrections from My Words and Phrases are applied first, so the words are
found the way you taught QUILL to spell them.

You hear the outcome once: "Selected: the blue car", "Before the blue car" or
"After the blue car". If the place is three or more lines away from where you
were, the line number is added, like "Selected: the blue car, line 40".

If the words are not in the document, nothing moves. Your phrase is written as
ordinary text instead, and you hear "Not found, written as text." Say "scratch
that" to take it back out. This works with every speech engine, and the short
exact commands, like "select that" and "go to top", still do what they always
did.

#### Snippets and clips by voice

The Copy Tray, your snippets and your abbreviations all answer to your voice
too.

As a whole phrase, on its own:

- **"copy all"** (or "copy everything" or "copy document") copies the whole
  document, just as Copy All does.
- **"copy that"** copies the phrase you just said.
- **"show clips"** (or "open copy tray" or "show copy tray") opens the Copy
  Tray dialog.
- **"show snippets"** opens the list from Insert Snippet.

With words after them, at the start of a phrase:

- **"paste clip three"** (or "paste slot three") writes what is in Copy Tray
  slot 3. Any slot from 1 to 12 works. If the slot is empty, you are told so
  and nothing is written.
- **"insert snippet" and its name**, for example "insert snippet sign off".
  You do not need the exact name: QUILL ignores capitals, punctuation and
  spaces, tries the whole name first, then a name that starts with what you
  said, then one that contains your words. If several snippets match, you hear
  how many and the list opens so you can choose. If none do, you hear "No
  snippet called sign off" and nothing is written.
- **"insert abbreviation"** (or "expand abbreviation") **and its trigger**
  writes what that abbreviation stands for.

A snippet with blanks to fill in asks for each blank by voice before anything
is written. With the starter Bug Report Template, "insert snippet bug report"
says "Snippet Bug Report Template, 3 blanks. Say cancel to stop. Summary?". What
you say next is the answer, with spoken punctuation obeyed. For a choice, such
as `${choice:NVDA|JAWS|Narrator}`, you hear "Choose NVDA, JAWS or Narrator.":
say one of them, or "choose two". Say **skip** to leave a blank empty,
**scratch that** to answer the one before again, or **cancel** to write
nothing. `${date}` and `${time}` come from this computer's clock, and
`${cursor}` puts the cursor where the snippet says.

Whatever goes in, it goes in as one phrase: one `Ctrl+Z` takes it out, and so
does "scratch that". The read-back keeps it short, "Snippet sign off" or
"Pasted slot 3", rather than reading the whole thing to you; say "read that"
to hear all of it. These commands do
not work while **Just write what I say** is on, because commands are off then.

#### Correct that: choosing another guess

Sometimes the engine was not sure what you said, and had a second idea. Say
**"correct that"** straight after the phrase, and you hear up to three other
guesses, numbered, for example: "1: right to Ann. 2: write two Ann. Say choose
and the number." Then say **"choose one"**, **"choose two"** or **"choose
three"**, and that guess takes the place of what was written. You hear
"Changed to:" and the new words.

**Windows speech recognition** keeps its own other guesses. Moonshine,
Whisper and the optional models give one answer each, so with them "correct
that" asks for a **second opinion** instead: the other built-in engine listens
to your last phrase again. You hear "Listening again with Whisper." (or
Moonshine), and a moment later both answers: "1: the whether is nice. 2: the
weather is nice. Say choose and the number." Say **"choose two"** to take the
second. If both engines heard the same words, you are told so, and nothing
changes. Whisper listens again after Moonshine, and Moonshine after Whisper or
a downloaded model.

The second opinion uses only the sound of your last phrase, kept in memory
until you say the next one: nothing is saved to disk and nothing goes over the
internet. It is not offered in Spanish, where only Whisper understands you, or
with OpenAI or a speech company. Then "correct that" tells you there is nothing
to choose from: say "scratch that" and say it again, or add a correction in
**My Words and Phrases** so it comes out right next time.

Whatever a correction replaced is not lost. It goes into **Recent Phrases**
(`Shift+F11`, in the Live Dictation submenu) marked "(before correction)", just after the corrected
words, so you can put it back with Insert Again or copy it.

With any engine you can also say **"correct" and the words** that came out
wrong, then say the right ones (see "Moving and selecting by voice"), or **"spell
that"** to spell the last phrase out (see "Letters, numbers and symbols").

#### Replace and change that: fixing words without retyping them

Two commands put new words in place of old ones, so you do not have to
select anything first. Say each one at the start of a phrase.

**"replace" the words "with" the new words.** Say "replace Tuesday with
Wednesday" and the nearest "Tuesday" before the cursor becomes "Wednesday";
if there is none before the cursor, QUILL looks after it. The new words take
the capital and the closing full stop of the old ones, and the cursor stays
where it was, so you can carry on dictating. You hear "Replaced Tuesday with
Wednesday." If the words are not there, what you said is written as ordinary
text, as with "select" (you hear "Not found, written as text."; say "scratch
that" to take it away). After the command word, "QUILL replace Tuesday with
Wednesday", nothing is written when the words are not found.

**"change that to" and the new words** replaces the whole phrase you dictated
last. You said "see you Thursday." and meant Friday: say "change that to see
you Friday", and you hear "Changed to: See you Friday." The leading space, the
capital and the closing full stop stay as they were.

**"delete previous paragraph"** (or "delete last paragraph") deletes the
paragraph just before the cursor, from its start up to the cursor, with the
blank line in front of it. Say it again to delete the one before. If text is
selected, the selection is deleted instead.

Replace and change that keep what they replaced in Recent Phrases, marked
"(before correction)". "Scratch that" straight after a replace inside your last
phrase takes away the whole corrected phrase.

#### Speech engines for Live Dictation

**Speech engines.** The **Speech engine** list in Dictation Settings
(`Alt+Shift+F6`) offers these:

- **Moonshine**, the default. It is fast even on a modest computer, and puts
  in punctuation for you. It is built in, and English only.
- **Whisper**, a little slower. Try it if Moonshine often mishears you. It is
  built in too, and knows English and Spanish; in Spanish it is used even
  when Moonshine is chosen. This Whisper comes with QUILL; it is not the
  whisper.cpp engine that Locked Dictation and transcription use, which
  downloads the first time you need it.
- **Every model you downloaded** for better accuracy, such as Nemotron or
  Parakeet, listed with "(downloaded)" and its tier. See "Better accuracy:
  optional speech models" below.
- **Windows speech recognition** works in any speech language installed in
  Windows, but adds no punctuation of its own.
- **Windows voice typing** hands over to `Windows+H`, where none of the
  commands apply.
- **OpenAI**, only with your own OpenAI key and only if you choose it. Your
  speech is sent to OpenAI; see "OpenAI dictation, with your own key" below.
- **Speech providers**, only with your own account at that company and only
  once you set it up in **Speech Providers...** (`Alt+V`). Your speech is sent
  to that company; see "Speech providers: dictation with your own account at
  another company" below.

To weigh them up side by side, see "Which speech engine? A guide to
choosing" at the start of this chapter.

#### The wake phrase

**The wake phrase.** Switch on **Listen for the wake phrase while dictation is
off** in Dictation Settings, then say **"Quill dictate"** (or a phrase of your
own, at least two words) to start without touching the keyboard. Anything you
say after it in the same breath is written.

While the wake phrase is on, the microphone is open whenever QUILL is the
window in front. Nothing it hears is written, kept or sent unless it begins
with the wake phrase, and the microphone closes when another program comes to
the front. It never listens in the background.

#### Your own words and phrases

**Your own words and phrases.** **Edit My Words and Phrases...** in Dictation
Settings opens your `dictation.md`, the same file Locked Dictation reads.
**Vocabulary** entries correct near misses to your spelling. **Replacements**
(`say => write`, with `\n` for a new line) are spoken phrases of your own.
In that file `\t` is a tab and `\\` is one backslash, so a phrase that
writes the folder `C:\new` is saved as `my folder => C:\\new`. My Words and
Phrases writes it that way for you; it matters only when you edit the file
by hand. A single backslash before any other letter is kept as you typed it.

#### Dictation Settings (Alt+Shift+F6)

**Dictation Settings -- Alt+Shift+F6** (press `Alt+Shift+F6`) is where Live
Dictation is set up. Each choice is listed here with its setting name in
brackets:

- The **speech engine** (`windows_dictation_engine`).
- The **dictation language** (`windows_dictation_speech_language`): English,
  or Spanish. See "Dictating in Spanish" below.
- The **language** for Windows speech recognition
  (`windows_dictation_language`).
- The **microphone** (`windows_dictation_microphone`, saved by name).
- **What you hear after each phrase** (`windows_dictation_phrase_feedback`): a
  sound, the words read back, both (the default), or neither.
- What **"dash"** writes (`windows_dictation_dash`): em dash, spaced en dash,
  or two hyphens.
- The **start, stop and error tones** (`windows_dictation_cue_sounds`).
- **Saying "Dictation on" and "Dictation off"** (`windows_dictation_announce`).
- The **wake phrase** (`windows_dictation_wake_enabled`,
  `windows_dictation_wake_phrase`).
- The **stop phrase** (`windows_dictation_stop_phrase`). It is "stop
  dictation" until you choose your own words, said on their own after a pause.
  "stop dictation" always works too.

Six finer choices, and a style that sets two of them, sit beside them:

- **Automatic punctuation** for Moonshine and Whisper
  (`windows_dictation_auto_punctuation`). Turn it off and you say every mark.
- The **pause before a phrase is written** (`windows_dictation_pause`): Short
  (half a second), Normal (under a second), Long (about a second and a half),
  Longer (2 seconds) or Longest (3 seconds). The two longest are for when you
  like to take your time between words. The cost is that every phrase waits
  that long before it is written.
- **Remove filler words** such as um and uh
  (`windows_dictation_remove_fillers`).
- **Dictation style** (`Alt+Y`): Verbatim, Clean or, with AI on, Polished;
  see "Correcting yourself as you talk, and dictation styles". It is a name
  for the settings it changes and is not saved by itself.
- **Fix it when I correct myself** (`windows_dictation_self_repair`, `Alt+X`):
  "Thursday, no, Friday" writes Friday. Off at first.
- **Stop dictation after silence** (`windows_dictation_silence_minutes`):
  never, 1, 5 or 10 minutes.
- **Just write what I say** (`windows_dictation_continuous`), for talking in
  one long run. A pause then puts in no full stop, plays nothing and reads
  nothing back, and voice commands are written as words. Only spoken marks and
  the stop phrase are still obeyed.

**When you stop in the middle of a thought.** Sometimes you pause to think
halfway through a sentence, and the engine puts a full stop there. If the
phrase ends on a word no sentence ends on, such as "a", "the", "of", "to",
"and", "but", "my", "very" or "really", QUILL takes that full stop back out and
joins the next phrase on. So "this is a very" [pause] "good test" comes out as
one sentence: "This is a very good test." A full stop you said yourself is
never taken back.

**Test Microphone** records four seconds and tells you how loud it was and what
the engine heard. **Better Accuracy: Speech Models...** (`Alt+B`) opens the
optional models described in "Better accuracy: optional speech models" below.
Below it, **Recommended for this computer** is a read-only line naming the
model that suits this computer and why; it is only advice.
**More Dictation Settings...** (`Alt+A`) opens the window described next.

#### More Dictation Settings, every option

Press **More Dictation Settings...** (`Alt+A`) in Dictation Settings. What
you change here is saved when you press OK in Dictation Settings.

| Option | What it does | Starts as |
|---|---|---|
| Hold the dictation key to talk; a quick press still turns it on and off | Also lets you hold Ctrl+F11 while you talk and let go to stop | Off |
| While you speak, the words heard so far | Show them in the status bar and on braille, also say new words quietly, or do not show them | Show them |
| Send a dictated message to the AI | When I pause, or When I press Enter | When I pause |
| Pause before the message is written | Short, Normal or Long, when talking to the AI | Long |
| Remove filler words when talking to the AI | Leave um and uh out of what you say to the AI | On |
| Automatic punctuation when talking to the AI | Let the engine punctuate what you say to the AI | On |
| Let OpenAI dictation send my speech to OpenAI | Your agreement, which you can take back here | Off |
| OpenAI speech model | The model OpenAI dictation uses, from OpenAI's own list | The newest |
| My Dictation Instructions (button) | Opens the file Tidy Dictated Text follows | (a button) |
| Say punctuation marks in the read-back (`Alt+S`) | Reads "comma", "period" and the other marks by name after each phrase; see "What you hear" | On |
| Tick while a phrase is being worked on (`Alt+R`) | A soft tick once a second while a phrase takes more than a second to turn into text; see "What you hear" | Off (on in QUILL Transcribe) |
| Time stamps in live transcripts (`Alt+T`) | Starts each paragraph of a live transcript with the time, like [10:42]; see "Live transcripts" | Off |
| Dictate in Other Programs... (button, `Alt+O`) | Saves your settings and hands them to QUILL Transcribe when it is running or installed, otherwise to Quill Inkwell, and starts it; see "Dictating into other programs" | (a button) |
| Programs Dictation Never Types Into... (button, `Alt+N`) | The programs dictation never types into from QUILL Transcribe or Quill Inkwell, such as your password manager; see "Programs dictation never types into" | The common password managers and the Windows sign-in prompts |
| Command word (`Alt+C`) | The word you say before a command, like QUILL scratch that; empty for none; see "The command word" | QUILL |
| Commands only after the command word (strict mode) (`Alt+E`) | A command said on its own is written as words; the stop phrase always works | Off (on in QUILL Transcribe) |
| Seconds command mode waits for a command (`Alt+D`) | How long command mode lasts with no command, from 5 to 30 | 8 |
| Send dictation to review first (`Alt+V`) | What you dictate goes into Review Dictation instead, to insert once; see "Review before inserting" | Off |
| Allow polishing my dictation with AI when I ask (`Alt+G`) | "QUILL polish that" and the Polish button in Review Dictation ask the AI to fix punctuation and small slips, keeping your words; see "Polishing your dictation with AI, only when you ask" | Off |
| Keep a dictation history (`Alt+Y`) | Off, One day, Seven days or Thirty days of the text you dictate, never the sound, listed in Recent Phrases; turning it off deletes it; see "Words that were not written, and dictation history" | Off |
| Dictation profile, for the kind of writing (`Alt+A`) | Standard, Email, Document, Markdown, Chat, Coding or Verbatim; see "Dictation profiles" | Standard |
| Lock the profile so it cannot be switched by voice (`Alt+B`) | A spoken profile name does not switch profiles | Off |
| Share dictation settings with every QuillVille program (`Alt+Q`) | Your dictation settings are the same in QUILL, QUILL Lite, QUILL Transcribe and Quill Inkwell; see "Sharing dictation settings with the family" | On for a new install; off if you had changed your settings before |

In settings files these are `windows_dictation_hold_to_talk`,
`windows_dictation_preview`, `windows_dictation_ai_send`,
`windows_dictation_ai_pause`, `windows_dictation_ai_remove_fillers`,
`windows_dictation_ai_auto_punctuation`, `windows_dictation_openai_consent`,
`windows_dictation_openai_model`, `windows_dictation_readback_marks`,
`windows_dictation_working_tick`, `windows_dictation_transcript_timestamps`,
`windows_dictation_never_type`, `windows_dictation_command_prefix`,
`windows_dictation_command_prefix_required`,
`windows_dictation_command_timeout`, `windows_dictation_review_first`,
`windows_dictation_polish`, `windows_dictation_history_days` (0 for off,
or 1, 7 or 30), `windows_dictation_profile` and
`windows_dictation_profile_locked` and
`windows_dictation_share_family` (`on` or `off`; empty until decided). The
review window also keeps `windows_dictation_review_context` (its context check
box) and `windows_dictation_review_consent` (your answer to its question).

A failure is always spoken, whatever these settings say. If the read-back
plays through speakers, the microphone can hear it, so use headphones or choose
a sound only.

#### Dictating in Spanish

You can dictate in Spanish. This is new, so treat it as something to try, and
tell us how it goes.

**To switch it on**, open Dictation Settings (`Alt+Shift+F6`), move to
**Dictation language**, choose **Spanish**, and press Enter. That's
all. To go back, choose English the same way. There is a quicker way too,
with one key or by voice; see "Switching between English and Spanish" below.

**What works now:**

- **Your words come out in Spanish**, accents and all. With Moonshine or
  Whisper, QUILL uses Whisper's multilingual speech model, which comes with
  QUILL, so there is nothing to download. Moonshine only knows English, so in
  Spanish you get Whisper either way.
- **A better Spanish model, said once.** The built-in Whisper gets about one
  word in four wrong in Spanish. If your computer can run NVIDIA Parakeet TDT
  0.6B v3 (in practice, 8 GB of memory and four cores), the first time you
  dictate in Spanish you hear one sentence saying so, for example: "For
  Spanish, NVIDIA Parakeet TDT 0.6B v3 gets about 6 percent of words wrong,
  against 29 for the built-in model. It is a 670 MB download in the model
  list." Nothing is downloaded or changed; the choice is yours. You hear it
  once, in whichever QuillVille program you dictate in first. A computer with
  4 GB hears nothing, because the built-in model is the right one there.
- **With Windows speech recognition**, Windows needs Spanish installed: add
  Spanish (Spain or Mexico) in Windows Settings, Time and language, Speech. If
  it isn't there, dictation tells you so when you start.
- **The wake and stop phrases** become "Quill dicta" and "deja de dictar". If
  you have typed your own, yours are kept.

**Commands stay in English for now.** "Scratch that", "select that", "new
paragraph" and the rest work exactly as they do in English. Spanish commands
are on the way, once a native speaker has checked them.

**Punctuation.** With automatic punctuation on (the usual setting), Whisper
puts in the commas, full stops and question marks for you, so just speak.
Spanish punctuation words only work when automatic punctuation is off, or with
Windows speech recognition. That's because "coma" and "punto" are everyday
words too, and we don't want "que coma" turned into a comma. When they are
on, you can say:

- "coma" for a comma, "punto" (or "punto y seguido") for a full stop, and
  "punto y aparte" for a full stop and a new paragraph
- "punto y coma", "dos puntos" and "puntos suspensivos"
- "abrir interrogación" and "cerrar interrogación" for the question marks at
  each end, and "abrir exclamación" and "cerrar exclamación" the same way
- "abrir paréntesis", "cerrar paréntesis", "abrir comillas", "cerrar comillas"
- "guion", "guion largo" and "arroba"
- "nueva línea", "nuevo párrafo" and "tabulador"

Say "literal" first to write the word itself: "literal coma" writes *coma*.
Say "what can I say" while dictating to see the whole list.

**This is new, and we'd love to hear from you.** If a word keeps coming out
wrong, or something doesn't work the way you expect, use Help > Get Help from
Support and tell us what you said and what was written.

#### Switching between English and Spanish

If you write in both languages, you do not need to open Dictation Settings
each time. Any of these switches you over, even in the middle of dictating:

- Press **Switch Dictation Language** (`Ctrl+Shift+F11`). Press it again to go
  back.
- In English, say "switch to Spanish" or "Spanish dictation".
- In Spanish, say "cambiar a inglés" or "dictado en inglés". The accent on
  "inglés" is optional, so it works however the engine writes it.

You hear "Español." or "English." so you know where you are. QUILL remembers
the choice, so next time you start dictating it is in the language you last
used.

The first time you switch to Spanish in a session it can take a few seconds,
because the speech engine is getting ready for the new language (with
Moonshine, which only knows English, that means loading Whisper). After that,
switching back and forth is quick, because both stay ready until you close
QUILL.

QUILL does not guess the language phrase by phrase. You choose it, and it
stays that way until you switch again. That means a Spanish name in the middle
of an English sentence will be heard as English; for those, add the name to My
Words and Phrases, or say "spell that" and spell it.

#### Better accuracy: optional speech models

Dictation works the moment you install. If you want more accuracy, you can
download a larger model.

These are the same local models VS Code offers for its own dictation, plus
the rest of the Whisper family. They are free, they are optional, and they run
on your computer's processor; no graphics card needed. Your voice never leaves
the computer: the only thing that comes over the internet is the model itself,
once, when you ask for it. Nothing downloads on its own, and the built-in
Moonshine stays your engine until you choose another.

**To download one:**

1. Open **Dictation Settings** (**Alt+Shift+F6**) and press **Better Accuracy:
   Speech Models...** (**Alt+B**).
2. Arrow through the list. Each row says what the model is good for, how big
   it is, and whether it is already here. **Details** (**Alt+T**) says more:
   what it is better at, its languages, its download and disk size, which
   computers suit it, whether this computer should keep up, its published
   accuracy, its licence, and the folder it will be saved in.
3. Press **Download...** (**Alt+D**). A question tells you where the model
   comes from, how big it is, its licence and where it will be saved. Answer
   Yes to start. On a metered connection you are asked about that first.
4. You hear "Downloading", then every quarter of the way. **Cancel Download**
   (**Alt+L**) stops it. What has arrived is kept, so pressing Download again
   carries on from there, even after you close QUILL.
5. When it says the model is downloaded, press **Use for Dictation**
   (**Alt+U**), then **OK** in Dictation Settings. Or choose the model in the
   **Speech engine** list yourself: downloaded models are listed there with
   "(downloaded)" and the model's tier after the name.

Every file is checked against a fingerprint (a checksum) we recorded when we
added the model. If a file does not match, it is deleted and you are told, so
a damaged or changed download can never be used.

**Which model should I use?** Speech Models recommends one. Near the top of
the window, the read-only **Recommendation** box (**Alt+C**) names the model
that suits this computer and your dictation language, and says why: whether
it keeps up here, about how soon your words appear after you pause, whether
your speech stays on this computer (it always does), and how big the download
is, or that it is already installed. The lines after it say more, for
example a model that makes fewer mistakes but would slow your screen reader
here. **What matters most** (**Alt+W**) changes the advice: a balance of speed
and accuracy (the usual choice), the quickest response, or the fewest
mistakes this computer can keep up with. **Show Recommended Model**
(**Alt+S**) moves to that model in the list, so you can read its details and
download it. Dictation Settings shows the same advice in one line, in the
**Recommended for this computer** box under the Better Accuracy button.

**Switch to Recommended Model** (**Alt+H**), beside it, chooses the
recommended model as your speech engine and changes nothing else: your words,
instructions, pauses and punctuation stay as they are. Speech Models closes,
and Dictation Settings says "Speech engine:" and the model's name, then "Press
OK to keep it." Press **OK** there to keep it, or Cancel to keep the engine
you had. It never downloads anything. If the model is not on this computer
yet, you hear that it is not here yet ("Download it, then switch."), and you
are taken to its row in the list, so you can press **Download...**
(**Alt+D**). While a model is downloading, it asks you to wait for the
download or press **Cancel Download** first.

The recommendation is only advice. QUILL never changes your engine by itself;
you choose. Its figures come from our tests with real recordings, on one
computer, and it says so: yours may differ. A graphics
card makes no difference: every dictation model runs on the processor.

**What it usually names:**

| Your computer | English | Spanish |
|---|---|---|
| 4 GB of memory, or little memory free | Moonshine (built in) | Whisper (built in) |
| 8 GB, two cores | NVIDIA Parakeet TDT 0.6B v3 | NVIDIA Parakeet TDT 0.6B v3 |
| 8 GB or more, four cores | NVIDIA Parakeet Unified 0.6B | NVIDIA Parakeet TDT 0.6B v3 |

**How much memory dictation may take.** The advice leaves room for your
screen reader. On a computer with 4 GB, dictation may take about 600 MB; with
8 GB, 1.6 GB; with 16 GB or more, 4 GB. It never takes more than is free when
you ask, less half a gigabyte kept back. So a model can be left out on a busy
computer that would fit on the same computer at a quieter moment, and the
Recommendation box says so.

**Tiers.** Every model is labelled with one of three tiers, wherever you
choose one: the Speech engine list, Speech Models, Transcribe a Recording,
and Manage Speech Models.

- **Lightweight**: keeps up comfortably even on a modest computer. The
  built-in Moonshine and Whisper, Moonshine base, Whisper base.en, and both
  Parakeet models.
- **Balanced**: more work than the built-in engines; keeps up on a computer
  with four or more cores. Nemotron and Whisper base.
- **High accuracy**: the fewest mistakes, for the most work; needs a capable
  computer, or patience. Whisper small and larger.

The tiers follow the speeds we measured on real speech, so a model's tier may
differ from earlier versions of QUILL: both Parakeet models were Balanced and
Nemotron was High accuracy.

**Where the models go.** One folder for QUILL, QUILL Lite and QUILL
Transcribe on the same computer, so a model downloaded in one is there for the
others, and for the **QUILL speech models** engine that Locked Dictation and
offline transcription can use:
`%LOCALAPPDATA%\QuillVille\Dictation\models`. In a portable copy, models are
saved inside the portable folder, so everything travels together
(`data\dictation\models` in the portable folder). Before a download starts,
QUILL checks there is room on that drive and tells you if there is not.

**To remove one**, choose it in Speech Models and press **Remove**
(**Alt+R**). It frees the space for every program that shares it. If dictation is using it,
choose another engine first. The **Progress** box then says how much space
was freed, and focus goes back to the list of models.

**When you switch away from a downloaded model**, QUILL offers to delete it.
After you choose another engine and press a plain **OK** in Dictation
Settings, a question titled **Delete Old Speech Model** says, for example:
"Now using NVIDIA Parakeet Unified 0.6B. Delete Whisper medium to free 946
MB?" It adds that QUILL, QUILL Lite and QUILL Transcribe share the model's
files, so any of them still set to it will need it downloaded again. No is
the default, so pressing Enter keeps the files. Yes deletes them, and you
hear the model's name, "deleted", and the space freed. If it cannot be
deleted, you are told that something may still be using it, and to remove it
in Speech Models later.

The question is not asked while dictation is running or waiting for the wake
phrase (remove the old model later in Speech Models), when the old engine was
a built-in one with nothing to delete, or when you left Dictation Settings
with **My Words and Phrases...** or another button that opens a window.

**Will my computer keep up?** When Speech Models opens, it spends about two
seconds timing the built-in Moonshine on this computer, then works out how
each model should do here. The details then say one of three things: it
should keep up comfortably; it should keep up but uses more of the processor,
so your screen reader may answer a little more slowly while you dictate; or it
"may lag behind your speech on this computer". You can still download any of
them. Large models on a dual-core computer with 8 GB of memory are only for
when you can wait.

**If a downloaded model goes missing** (you removed it, or the drive with a
portable copy is not there), dictation does not stop and does not change
engine silently. It says, in one sentence, that it is using the built-in
engine instead, and carries on.

**Nemotron shows your words as you speak.** It recognises while you talk, so
the words heard so far appear in the status bar and on a braille display, and
each phrase goes into the document when you pause. See "Seeing the words while
you speak". The other models write each phrase when you pause.

##### The list of models

The list keeps the order of earlier versions: VS Code's own models first, then
the rest of Whisper, smallest first. The order is not a ranking; for that, see
"How we chose: tested on real speech" below.

| Model | Good for | Download | Languages |
|---|---|---|---|
| NVIDIA Nemotron 3.5 ASR Streaming 0.6B | Shows your words while you speak; VS Code's default | 682 MB | English, Spanish |
| NVIDIA Parakeet Unified 0.6B | The fewest mistakes in English in our tests; recommended on 8 GB with four cores | 663 MB | English |
| NVIDIA Parakeet TDT 0.6B v3 | The fewest mistakes in Spanish in our tests; recommended on 8 GB with two cores | 670 MB | English, Spanish |
| Whisper small | Many languages; needs two processor threads | 375 MB | English, Spanish |
| Whisper base | Many languages, lighter | 161 MB | English, Spanish |
| Whisper tiny | Built in already. Fastest and lightest, weakest accuracy | (built in) | English, Spanish |
| Whisper base.en | Light and quick, good on varied voices | 161 MB | English |
| Whisper medium | Many languages, when you can wait | 946 MB | English, Spanish |
| Whisper large-v3-turbo | Large-v3 quality, much faster than large-v3 | 1.0 GB | English, Spanish |
| Whisper large-v3 | The most accurate Whisper; very slow on most computers | 1.8 GB | English, Spanish |
| Moonshine base | A light step up from the built-in Moonshine | 141 MB | English |

**English only, or many languages?** The Whisper model ending in ".en" only
knows English. The many-language ones also dictate
Spanish. If you only dictate English, NVIDIA Parakeet Unified 0.6B made fewer
mistakes than any of them in our tests.

##### Models removed in this release

**Five English-only models were removed in this release:** Distil-Whisper
small.en, Whisper small.en, Distil-Whisper medium.en, Whisper medium.en and
Distil-Whisper large-v3. In our tests with real recordings, NVIDIA Parakeet
Unified 0.6B got 3.2 percent of words wrong on the held-out audiobooks, against
3.6 to 6.3 percent for these five. It also ran faster on one thread, in the
same or a smaller memory tier. Whisper base.en and every many-language Whisper stay.

- **If you were using one**, dictation moves for you when you update. If
  Parakeet Unified is already downloaded, dictation switches to it.
  Otherwise dictation uses the built-in model. Nothing is downloaded.
- **The next time dictation starts**, you hear one sentence, for example
  "Whisper small.en was removed in this release. Dictation now uses Parakeet
  Unified, which you already have." or "Whisper small.en was removed in this
  release, so dictation uses the built-in model. Parakeet Unified, in the
  model list, is more accurate." It is said once across every QuillVille
  program on this computer, not once in each.
- **Your downloaded files are not deleted.** They stay in
  `%LOCALAPPDATA%\QuillVille\Dictation\models` (in a portable copy,
  `data\dictation\models` inside the portable folder), in folders named
  whisper-small.en-int8, whisper-distil-small.en-int8, whisper-medium.en-int8,
  whisper-distil-medium.en-int8 and whisper-distil-large-v3-int8. Delete the
  folder to free the space.

**To choose Parakeet Unified instead:** open Dictation Settings
(**Alt+Shift+F6**), press **Better Accuracy: Speech Models...** (**Alt+B**),
choose NVIDIA Parakeet Unified 0.6B (or press **Show Recommended Model**,
**Alt+S**), press **Download...** (**Alt+D**), then **Use for Dictation**
(**Alt+U**) and **OK**.

##### How accurate are they?

Our own tests on real speech, which the advice uses, are in "How we chose:
tested on real speech" below. These are the figures each model's makers
publish. A word error rate is the share of words a model gets wrong on a
recorded test set; lower is better. Test sets differ, so compare numbers only
within one line.

- **Nemotron 3.5 ASR Streaming:** 7.91 percent on FLEURS English and 4.11
  percent on FLEURS Spanish, at the chunk size this download uses (NVIDIA's
  model card, huggingface.co/nvidia/nemotron-3.5-asr-streaming-0.6b).
- **Parakeet Unified:** 1.63 percent on LibriSpeech test-clean and 3.11 percent
  on test-other (huggingface.co/nvidia/parakeet-unified-en-0.6b).
- **Parakeet TDT v3:** 4.85 percent on FLEURS English, 3.45 percent on FLEURS
  Spanish (huggingface.co/nvidia/parakeet-tdt-0.6b-v3).
- **Whisper**, on LibriSpeech test-clean (OpenAI's Whisper paper, Appendix D,
  arxiv.org/abs/2212.04356): tiny 7.6, base 5.0, small 3.4, medium 2.9
  percent; English-only tiny.en 5.6, base.en 4.2.
  On Spanish (Common Voice 9): tiny 30.3, base 19.6, small 10.3, medium 6.9
  percent. That Spanish column is the biggest reason to choose a larger Whisper
  if you dictate Spanish.
- **Whisper large-v3**, average over short recordings the model was not
  trained on (the Distil-Whisper model card,
  huggingface.co/distil-whisper/distil-small.en): 8.4 percent. OpenAI
  publishes no figure for large-v3-turbo; it describes it as much faster than
  large-v3 with a small drop in quality.
- **Moonshine:** base 10.07 percent against tiny's 12.66, averaged over the
  Open ASR Leaderboard's English test sets (Moonshine AI,
  github.com/moonshine-ai/moonshine).

**What each is better at**, in plain words: the bigger models cope better with
accents, fast speech, a noisy room, names and long sentences; all of them put
in punctuation and capitals for you. For Spanish, any of the many-language
models beats the built-in tiny by a wide margin.

##### How we chose: tested on real speech

**QUILL's advice comes from our own tests with real people's recordings**, run
on 22 October 2026. Before that, it rested on ten recordings of a synthetic
voice, which made every model look about the same.

We fed each model recordings the way dictation does, one phrase at a time, on
one processor thread, because the screen reader needs the rest. The fairest
test is public-domain audiobooks recorded after every model was trained, so
no model can have learned them; we also used Google's FLEURS read sentences.
Everything ran on one laptop on one day, so your speeds will differ a little.
The figures are the percentage of words wrong (lower is better) and the most
memory each model used.

**English:**

| Model | Held-out audiobooks | FLEURS | Most memory | What QUILL does with it |
|---|---|---|---|---|
| NVIDIA Parakeet Unified 0.6B | 3.2% | 6.3% | 1.2 GB | Recommended on 8 GB with four cores |
| Whisper medium.en | 3.6% | not run | 3.0 GB | Removed |
| NVIDIA Parakeet TDT 0.6B v3 | 3.8% | 9.0% | 1.1 GB | Kept; recommended on 8 GB with two cores |
| Whisper small.en | 4.3% | 6.3% | 1.4 GB | Removed |
| Distil-Whisper large-v3 | 4.5% | not run | 2.0 GB | Removed |
| Whisper small | 4.7% | not run | 1.4 GB | Kept; many languages, needs two threads |
| NVIDIA Nemotron 3.5 Streaming 0.6B | 5.3% | 13.7% | 1.5 GB | Kept; shows words while you speak |
| Moonshine base | 5.9% | 15.1% | 378 MB | Kept; fixed for long phrases |
| Whisper base.en | 5.9% | 7.4% | 820 MB | Kept; light, good on varied voices |
| Distil-Whisper small.en | 5.9% | 7.6% | 1.0 GB | Removed |
| Distil-Whisper medium.en | 6.3% | not run | 1.6 GB | Removed |
| Moonshine tiny (built in) | 6.5% | 13.2% | 584 MB | Kept; the default, and the pick on 4 GB |
| Whisper base | 7.4% | 10.8% | 821 MB | Kept; many languages |
| Whisper tiny (built in) | 8.3% | 11.7% | 521 MB | Kept; built in |

**Spanish:**

| Model | FLEURS Spanish | Held-out Spanish audiobooks | Most memory | What QUILL does with it |
|---|---|---|---|---|
| NVIDIA Parakeet TDT 0.6B v3 | 4.4% | 7.3% | 1.1 GB | Recommended on 8 GB |
| Whisper small | 6.0% | 7.8% | 1.4 GB | Kept; needs two threads |
| NVIDIA Nemotron 3.5 Streaming 0.6B | 6.4% | 8.0% | 1.5 GB | Kept |
| Whisper base | 12.6% | 16.1% | 821 MB | Kept; lighter |
| Whisper tiny (built in) | 30.5% | 27.0% | 521 MB | Kept; built in, the pick on 4 GB |

**Speed.** Against the built-in Moonshine tiny, Parakeet TDT v3 needs 3.2 times
as much computing, Parakeet Unified 3.8, Whisper base.en 4.3 and Nemotron 5.8.
Speech Models times Moonshine tiny on your own computer and scales these
figures to it.

**Moonshine base hears long phrases now.** It used to write nothing at all for
a phrase longer than about eight and a half seconds. It now hears a long
phrase in pieces of 8 seconds or less, cut at the quietest moment, and joins
them. The pieces overlap by half a second, so a word that falls on a cut is
not lost.

The full record is in QUILL's source, in
`docs/qa/dictation-real-speech-benchmark-2026-10-22.md`.

**When the built-in model is still the better choice:** on a 4 GB or older
computer, on battery, when little memory is free, or when your screen reader
must never slow down. Moonshine tiny uses about a twentieth of a second of
computing per second of speech and at most about 580 MB of memory; the
Parakeet models need three to four times the computing and about twice the
memory.

##### Nemotron or Parakeet: which should I try?

**For the fewest mistakes, choose Parakeet.** On real recordings, Parakeet
Unified got 3.2 percent of words wrong on the held-out audiobooks and
Nemotron 5.3 percent; on FLEURS English, 6.3 against 13.7. In Spanish,
Parakeet TDT v3 got 4.4 percent wrong on FLEURS and Nemotron 6.4. Parakeet is
also lighter: on one processor thread, Parakeet Unified needed 0.21 seconds of
computing per second of speech, Parakeet TDT v3 0.11 and Nemotron 0.37, where
dictation's budget is 0.25. Nemotron used the most memory of the three, about
1.5 GB.

**Nemotron is still the one that shows your words while you speak.** If you
write as you go and want to hear or feel each word arrive, that is worth more
than a few extra corrections.

All three are free NVIDIA models of about 0.6 billion parameters, and run
here on the processor alone, with your voice staying on your computer. All
three write punctuation and capitals themselves.

- **Parakeet** recognises each finished phrase after you pause. Nothing
  appears until you stop.
  - **Parakeet Unified 0.6B** is English only, and what QUILL recommends for
    English on a computer with 8 GB and four cores. NVIDIA trained it to work
    both while you speak and on a finished phrase; QUILL uses it on the
    finished phrase. About 663 MB.
  - **Parakeet TDT 0.6B v3** knows English, Spanish and 23 other European
    languages. QUILL recommends it for Spanish on 8 GB, and for English on
    8 GB with two cores. About 670 MB.
- **Nemotron 3.5 ASR Streaming** recognises while you speak, in short slices.
  Its words appear in the status bar and on braille while you talk, and each
  phrase is written when you pause. It decides whether a sentence was a
  question once it hears the next one, so a full stop it wrote can turn into
  a question mark a moment later. It knows English and Spanish. About 682 MB.

**Rule of thumb:** for the fewest mistakes, choose Parakeet; to see your words
as you speak, choose Nemotron.

##### How to tell which is more accurate for you

The published figures come from other people's voices. Yours is the one that
matters.

1. Download one model, choose it, and dictate the way you normally do for a
   day.
2. Each time a phrase comes out wrong, note it. **Recent Phrases**
   (**Shift+F11**) shows what was written, so you can compare.
3. Switch to another model in the Speech engine list and do the same.
4. Keep the one that made fewer mistakes, and remove the other to free the
   space.

If you like a more exact answer, QUILL's benchmark measures any model on your
own recordings. Record ten sentences as 16 kHz mono WAV files, write what you
said in a `transcripts.txt` beside them (one line per file: the name, a tab,
the words), and run `python scripts/dictbench.py <folder> --model parakeet_unified` in
a copy of QUILL's source. It prints the share of words wrong, which marks were
written, the speed, the memory and how long the model took to load.

#### OpenAI dictation, with your own key

If you have your own OpenAI key, you can have OpenAI recognise your speech
instead of your computer. It is very accurate, punctuates well, gets names
right that it has never met, and can show your words while you speak. It is
off unless you choose it, and your computer's own engines stay the default.

**Before you choose it, please know this: what you say is sent to OpenAI.**
While dictation is on with this engine, each phrase you speak goes over an
encrypted connection to OpenAI, with your own key, and the words come back.
OpenAI bills your account for it. Nothing goes through QUILL's servers, and
QUILL keeps no copy of your voice. OpenAI's own policies apply to what it
receives; read them at openai.com/policies. Silence is never sent, only the
speech dictation heard. The built-in engines never send anything anywhere.

**What you need:** your own OpenAI key, saved in **Use My Own AI Key** (see the AI chapter). QUILL's free AI is never used for dictation. OpenAI
dictation does not work in Safe Mode.

**Adding your key from here.** You don't have to go looking for it: in
Dictation Settings (Alt+Shift+F6), choose **More Dictation Settings...**, and
under "OpenAI, with your own key" press **Add or Change OpenAI Key...**
(Alt+K). Your settings are saved, Use My Own AI Key opens, and once you paste
your key, OpenAI appears in the speech engine list. You can also open Use My
Own AI Key any time with Alt+F2.

**Setting it up, step by step:**

1. Open **Dictation Settings** (**Alt+Shift+F6**).
2. In **Speech engine**, choose **OpenAI (your own key; sends your speech to
   OpenAI)**. It is only in the list on a computer where an OpenAI key is
   saved.
3. A question says exactly what is sent. Read it, then choose **Yes** to
   agree, or **No** to keep the engine you had. If you just press Enter, the
   answer is No, and nothing is sent.
4. **More Dictation Settings** opens with the cursor on **OpenAI speech
   model**. QUILL asks OpenAI which speech models your key can use and lists
   them, newest first. The newest is already chosen.
5. Press `Enter` to close More Dictation Settings, and `Enter` again to
   save Dictation Settings.
6. Press `Ctrl+F11` and talk, just as before.

**Which model?** The list comes from OpenAI, so it is always current, and
models OpenAI is retiring are left out. On the day this was written it held
two:

- **gpt-live-transcribe** writes as you speak. The words heard so far appear
  in the status bar and on braille, and each phrase arrives very soon after
  you pause.
- **gpt-transcribe** sends each phrase when you pause, and the words arrive a
  moment later.

**If your model goes away.** If OpenAI stops offering the model you chose,
More Dictation Settings tells you once, and leaves the choice empty so you can
pick another. If you are dictating when it happens, dictation stops and tells
you. It never moves to a different model on its own.

**Your words help.** The names and terms in **My Words and Phrases** are sent
with your speech as words to expect, so they come out spelled your way.

**To stop sending your speech,** choose another engine in Dictation Settings,
or turn off **Let OpenAI dictation send my speech to OpenAI** in More
Dictation Settings.

**What it costs.** OpenAI charges your account by the minute of speech. QUILL
keeps no count; your OpenAI account's usage page has the real figures.

**What you might hear:**

- "OpenAI dictation needs your own OpenAI key. Save one in Use My Own AI Key,
  in the AI menu, first."
- "OpenAI dictation is not switched on." Choose OpenAI in Dictation Settings
  and agree to the question.
- "OpenAI could not be reached. Check the internet connection." That phrase
  is lost, and dictation keeps listening.
- "OpenAI did not accept the saved key." Check your key in Use My Own AI Key.
- "The OpenAI model ... is no longer available to your key." Choose another in
  More Dictation Settings.

#### Speech providers: dictation with your own account at another company

If you already have an account with a speech company, dictation can use it.
QUILL knows twelve: Microsoft Azure AI Speech, Google Cloud Speech-to-Text, Amazon Transcribe, Deepgram, AssemblyAI, Speechmatics, ElevenLabs Scribe, Gladia, Rev.ai, Groq, Mistral Voxtral and IBM Watson Speech to Text. Your computer's own engines stay the default
and the recommendation; none of this is needed, and none of it is on until you
choose it.

**What is sent.** With one of these chosen as the speech engine, each phrase
dictation hears is sent over an encrypted connection to that company, with
your account, and the words come back. Nothing is sent while nobody is
speaking. The company bills you, not QUILL; QUILL shows no prices and counts
nothing, so look at your provider's own usage page. Nothing goes through
QUILL's servers and QUILL keeps no copy of your voice. None of it works in Safe
Mode.

**Setting one up:**

1. Open **Dictation Settings** (**Alt+Shift+F6**) and choose **Speech
   Providers...** (**Alt+V**).
2. In **Providers**, arrow to the company. **About this provider** says
   whether it shows your words while you speak, whether it learns your words
   from My Words and Phrases (and how many), where your speech goes and its
   usage page.
3. Tab to its fields and fill them in: usually a key, sometimes a region, a
   project or an address. Each field's F1 says where to find it in that
   company's console. A key is never shown again once saved; leaving a key
   field empty keeps the one already saved.
4. Press **Test Connection** (**Alt+T**). QUILL asks the company about your
   account, never with your speech, and says what it answered, such as "Azure
   answered: ready, region westeurope." If something is wrong it says which
   field, such as "The key was refused. Check Key.", and puts you there.
5. Press the Save button (Alt+S). Keys go to Windows Credential Manager at once
   and are never written in QUILL's settings or logs. The other details are
   kept when you choose OK in Dictation Settings.
6. Close the page. The company is now in the **Speech engine** list. Choose
   it, and a question says exactly what will be sent and to whom. **No** is
   the default; nothing is sent unless you choose Yes.

**Remove** (**Alt+M**) forgets everything saved for that company, keys
included.

**Which ones show words while you speak.** Azure, Amazon, Deepgram,
AssemblyAI, Speechmatics, ElevenLabs, Gladia, Rev.ai and IBM Watson do. Google,
Groq and Mistral send each phrase when you pause, so there is no live preview
with them.

**If the connection goes.** A lost phrase is said in one sentence ("Groq could
not be reached. Check the internet connection.") and dictation keeps
listening; a refused key or an empty account stops dictation and says so.
QUILL never switches to another engine by itself.

**Where they work.** Speech providers are for Live Dictation, here and in
QUILL Lite, QUILL Transcribe and Quill Inkwell, which have the same Speech
Providers page. They are not offered in Transcribe a Recording (`Shift+F5`),
Transcribe Audio or Video (Offline), captions or watch folders, and they are
never recommended; the recommendation only ever names a model on your
computer.

In settings files, each company's other details are kept in
`windows_dictation_speech_providers` and your answers to the consent
questions in `windows_dictation_speech_provider_consent`. Keys are never
there.

#### Talking to the AI

You can have a spoken conversation with AI help. Open the **AI Conversation**
window (see the AI chapter). The cursor is
already in **Your message**.

1. Press `Ctrl+F11` and ask your question.
2. Pause. Your message is sent, and you hear "Working."
3. The reply is read aloud. While it is being read, the microphone does not
   listen, so the reply is never taken as your next message.
4. When the reply has been read, just carry on talking. If you want to speak
   before it has finished, press `Escape`: you hear "Listening." and you can
   talk straight away.
5. Press `Ctrl+F11` again when you are done.

While you are in that box, dictation uses its **Talking to AI** settings, and
it goes back to your usual ones by itself when you leave:

- **A longer pause** (about a second and a half), so a breath does not send
  half a question.
- **Filler words removed**, because the AI does not need them.
- **Automatic punctuation on.**
- "Just write what I say" does not apply here, because the pause is what
  sends your message.

All four are in **More Dictation Settings**, under **Talking to the AI**. If
you would rather check each message before it goes, set **Send a dictated
message to the AI** to **When I press Enter**. Then pause as often as you
like, and press Enter when the message is right.

Each message costs the same as a typed one: one request on QUILL's free AI,
or nothing extra beyond your own key or plan.

#### Where the words go

**Where the words go.** Into the document you started in, replacing any
selection. Each phrase is one step for `Ctrl+Z`.

Your words go where you were when you started speaking. If you move the
cursor, or switch to another tab or window, while a phrase is still being
recognised, it is still written where you were speaking. Your cursor is put
back where you moved it, and you hear "Written where you started", with the
document's name if you were somewhere else by then. If that spot has changed
in the meantime, the words go at the cursor in that document instead, and you
are told.

After that, if you speak while another tab, window, program or dialog is in
front, nothing is written: dictation stops and tells you why. Closing the
document stops it too. A live transcript is the one exception, and the next
section explains it.

#### Live transcripts

A live transcript is for when you want everything written down and you do not
want to steer: a meeting, a lecture, a long think out loud. Press **Start or
Stop Live Transcript** (`Ctrl+Alt+Shift+PageDown`). QUILL opens a new, untitled
document, never the one you were working in, and writes everything it hears
into it.

It behaves differently from ordinary dictation, on purpose:

- **It just writes.** Voice commands are written as words; only the stop
  phrase is obeyed. There is no tone and no read-back after each phrase, no
  wake phrase, and it never stops because the room went quiet.
- **It tidies as it goes.** Filler words like um and uh are left out, and
  automatic punctuation is on.
- **A long pause starts a new paragraph.** Four seconds or more of quiet, and
  the next words begin a fresh paragraph. If you turn on **Time stamps in live
  transcripts** in More Dictation Settings, each paragraph starts with the
  time in square brackets, like [10:42].
- **The words always go at the end.** You can switch to another document, or
  another program altogether, and the transcript carries on writing at its own
  end. If you go back into the transcript to read or fix something, your place
  is kept and new words still arrive at the bottom.

The status bar keeps a count, for example "Live transcript: 12 minutes, 1,840
words", and Dictation Status (`Alt+F9`) tells you the same.

To stop, press `Ctrl+Alt+Shift+PageDown` again, or `Ctrl+F11`. You hear "Live
transcript stopped, 1,840 words." The document stays open and is not saved
yet, so save it when you are ready. Until then QUILL's recovery protects it,
the same as any unsaved document.

The very first time you start one, you hear: "Please record other people only
when they have agreed." It is said once, and that is the only reminder.

A live transcript listens to your microphone. It does not hear sound playing
on the computer itself, so for an online meeting it picks up what reaches the
microphone, not the other people's voices through your headphones. When it is
done, you can turn it into minutes or notes with a Transcript Action (see
"Transcript Actions" later in this chapter).

#### Dictating into other programs

Dictation does not have to stay inside QUILL. **Dictate Anywhere** lets you
dictate into your email, a web form, a chat window, almost anything with a
place to type. It is run by Quill Inkwell, QUILL's free companion app for
abbreviations, so Inkwell needs to be on your computer (QUILL's **Open Quill
Inkwell**, `Ctrl+Alt+Shift+F11`, offers to fetch it if it is not).

**Setting it up the easy way:**

1. In QUILL, open Dictation Settings (`Alt+Shift+F6`), then **More Dictation
   Settings...** (`Alt+A`).
2. Press **Dictate in Other Programs...** (`Alt+O`). Your dictation settings
   are saved and handed over. If QUILL Transcribe is running or installed, it
   gets them and starts, and you hear "QUILL Transcribe has your dictation
   settings. Use its start and stop key, or its tray menu, in the program you
   want to dictate into." Its start and stop key is the one you chose when
   you set up QUILL Transcribe. Otherwise Inkwell gets them and starts.
3. With Inkwell, if you have not chosen a key for it yet, Inkwell asks you for
   one now. Pick a key you do not use for anything else.

You can also choose the key yourself in Inkwell: on Inkwell's own File menu,
choose **Dictate Anywhere Key...**. There is no key until you choose one.

**Using it:**

1. Go to the other program and put the cursor where you want the words.
2. Press your Dictate Anywhere key.
3. Speak, then pause. Each phrase is typed in where the cursor is.
4. Press the key again, or say "stop dictation", when you are done.

The same engines, your own words, and most of the commands work just as they
do in QUILL: punctuation, spelling, "spell that", "caps on", "no space on",
switching to Spanish, and "scratch that". "Scratch that" works by pressing
Backspace for you, so it only works while the same window still has the focus.

Your snippets, abbreviations and clips work there too, because they only
insert: "insert snippet" and its name, "insert abbreviation" and its name, and
"paste clip" and a number. Each is typed as one phrase, so "scratch that" takes
all of it back. A snippet's blanks are asked for by voice first, as in a
document (see "Snippets and clips by voice"), and the cursor stays at the end.
"read that" reads what dictation typed there; "read last sentence" and the
other commands that read the text cannot, because nothing in the other program
is read.

Anything that needs to read what is already in the other program cannot work
there: "select", "go to", "correct", "copy all" and "show clips". If you say
one of those, you are told "That works in QUILL's own documents" and nothing
happens. "What can I say" there lists only what works in another program.

The command word works there too, and it matters more there: **"QUILL scratch
that"** is always a command, and whatever follows "QUILL" is never typed into
the other program, even when it is not a command (see "The command word").

Out of respect for your privacy and your other programs, Dictate Anywhere
will not type into a password box, into a program running as administrator
(unless Inkwell is too), into Inkwell's own window, or into QUILL itself. In
QUILL, just use `Ctrl+F11`. Each time, you are told why in a sentence.

**It stays in the field you started in.** If the focus moves to another field
or another program while you dictate, Inkwell pauses and holds what you said
instead of typing it in the wrong place. Inkwell's **Dictation** menu then has
**Resume** (`Ctrl+R`) to go back to the first field, **Resume in This Field**
(`Ctrl+Shift+R`) to write the held words where you are now, and **Discard Held
Words** (`Ctrl+Shift+D`). They are greyed out until something is held. While
dictation is paused, Inkwell's tray menu has the same three. Chosen from
Inkwell's own window or tray, Resume in This Field waits for you to switch to
another program and resumes there; choose it again to cancel.

**Programs dictation never types into.** Some programs should never receive
dictation, whatever field is in front: your password manager, for one.
**Programs Dictation Never Types Into...** (`Alt+N`) in More Dictation
Settings keeps that list. It starts with the common password managers and the
Windows sign-in, lock and administrator prompts. If you dictate into a listed
program from Quill Inkwell, QUILL Transcribe or Insert Again, you hear, for
example, "Dictation does not type into KeePass. Move to another program.", and
nothing is typed; words already held stay held. Programs are matched by their
file name, like keepass.exe, never by a window title. In the window:

- The list shows each program; `Delete` removes the chosen one, as does
  **Remove**.
- **Add Front Program** adds the program you were using just before you opened
  dictation's settings, and its button names it, for example "Add Front
  Program: KeePass (keepass.exe)". Switch to that program, come back, open the
  settings, then press it.
- Type a file name in **Program file name** and press `Enter` or **Add by
  Name**. A name without .exe gets it, so "KeePass" adds keepass.exe. A name
  you typed but did not add is kept when you press OK.

The list is saved when you press OK in Dictation Settings.

Inside other programs the read-back starts as a tone only, because your
screen reader already echoes what is typed. Inkwell keeps its own copy of the
dictation settings, which follows QUILL's while **Share dictation settings with
every QuillVille program** is on (see "Sharing dictation settings with the family"): in Inkwell, **Dictation > Dictation Settings...**
(`Ctrl+Alt+D`) opens the same window you know from QUILL, and **Dictation >
Dictate Anywhere** (`Ctrl+D`) turns it on and off from the menu. Inkwell uses
the same My Words and Phrases file as QUILL, so the names you taught QUILL come
out right everywhere. Dictate Anywhere is off in Safe Mode.

**From Quill Cast and Quill Radio.** Both have **Edit > Dictate Here**
(`Ctrl+F11`, the same key as Start Dictation in QUILL). Put the cursor in a
search box, such as Cast's podcast search, press `Ctrl+F11`, and QUILL
Transcribe dictates into it with your words and commands. If QUILL Transcribe
is not running, it starts in the tray and begins dictating when it is ready.
Neither app has a speech engine of its own. Dictate Here appears once
QUILL Transcribe is part of your copy of the family: in every public build from
QUILL Transcribe's release on 1 November 2026.

**One microphone at a time.** QUILL, QUILL Lite, QUILL Transcribe and Quill
Inkwell never listen at once, so the same words are never written twice. The
microphone belongs to whichever started dictating first, until it stops. If
QUILL Transcribe is listening when you press `Ctrl+F11`, QUILL does not open a
second microphone and names its key, for example "QUILL Transcribe is
listening. Press Alt+Shift+Backslash to stop it, then try again." If QUILL Lite
is dictating, you hear "QUILL Lite is dictating. Press Ctrl+F11 in QUILL Lite
to stop it, then try again." The other programs say the same about QUILL, with
the key that stops it. Locked Dictation (`Ctrl+F9`) shares the microphone too:
it is refused the same way while another program listens, and while it records,
`Ctrl+F11` says "QUILL is already dictating. Press Ctrl+F9 to stop it, then try
again." QUILL Transcribe waiting
in the tray does not hold the microphone, so `Ctrl+F11` works as usual. The
microphone is let go when dictation stops, when it stops because something went
wrong, when you close QUILL and if QUILL ever closes unexpectedly.

#### Dictation Context for This Document

You can tell QUILL, in a sentence, what the document in front of you is: "A
formal letter to my landlord about the boiler", or "Notes from the Tuesday
book club". Some engines use that to choose words and style better.

Press **Dictation Context for This Document...** (`Ctrl+Alt+Shift+PageUp`).
The window has:

- **This document is:** a box for your sentence.
- **Start from a saved context:** a list of contexts you saved before, then a
  few starters: Formal letter, Note to a friend, Technical writing, Meeting
  notes and Story. Choose one to fill the box, then change it as you like.
- **Also save it as a context named:** give it a name if you will want it
  again.
- **Who uses it:** a line you can read but not change, saying which of your
  settings will use the context.

QUILL remembers the context for that document, by where it is saved, so it is
there next time you open it. For an untitled document it lasts until you
close QUILL. You can also pick a saved one by voice: say "dictation context"
and its name, for example "dictation context meeting notes".

**Who uses it.** OpenAI dictation sends it along with your speech, so names
and words fit the subject. **Tidy Dictated Text** (`Ctrl+F3`) uses it beside
your My Dictation Instructions. The engines on your own computer cannot use it,
and the window tells you so. Your context only goes where your speech or text
is already going; it is never sent anywhere new.

#### Dictation Status

Not sure whether dictation is listening, or in which language? Press
**Dictation Status** (`Alt+F9`). You hear what dictation is doing right now,
including the engine and the language, whether you are in command mode, and
during a live transcript, how long it has run and how many words it has
written.

`Alt+F9` is also Locked Dictation's status key. When Locked Dictation is
recording or paused, it tells you about that; the rest of the time it answers
for Live Dictation.

#### On a modest computer

Dictation is built to be kind to an older computer, so your screen reader
stays quick:

- **Nothing runs while dictation is off.** The speech model is loaded the
  first time you start dictation, kept ready while you use it, and put away a
  few minutes after you stop, which gives its memory back.
- **If the computer cannot keep up.** If an optional model you downloaded
  falls behind your voice, because the computer is busy or on battery saver,
  you hear "This computer is busy, so dictation switched to the faster
  built-in engine for now. Your choice in Dictation Settings is unchanged."
  Dictation carries on with Moonshine. Next time you start, it tries your
  model again.


If dictation will not start, it tells you why: no microphone, microphone
access turned off for desktop apps in Windows Settings, Privacy and security,
Microphone, or (for Windows speech recognition) no speech language installed.

Live Dictation and Locked Dictation each keep their own microphone choice.

### Dictating well

Dictation gets much better with a few habits, and none of them are hard. This
is what is worth knowing before you sit down to dictate for the first time.

#### Your microphone

Any microphone works, but the closer it is to your mouth and the further from
everything else, the better your words come out.

- **A headset is best.** A USB or Bluetooth headset with a boom microphone
  stays the same distance from your mouth however you move your head. That
  steadiness matters more than price.
- **Place it just off to the side.** About two fingers from the corner of
  your mouth, not straight in front, so your breath does not puff into it.
- **A laptop's own microphone will do** in a quiet room, but it also hears the
  keyboard, the fan and your screen reader. If words keep coming out wrong,
  a headset is the first thing to try.
- **Check it.** **Test Microphone** in Dictation Settings (`Alt+Shift+F6`)
  records four seconds and tells you how loud you were and what the engine
  heard. If it says you are quiet, move the microphone closer before you turn
  anything up.
- **Too quiet, and it may not hear you at all.** If the microphone's level is
  set very low, or you speak very softly or far from it, dictation can miss a
  whole sentence, especially just after something louder. In our tests with
  very quiet recordings it missed some entirely. Move closer, or raise the
  level in Windows' sound settings.

#### The room

A quiet room helps more than any setting. A television, a radio or a
conversation across the room gets heard as words. Close a door if you can.
Hard, bare rooms echo; a room with soft furnishings sounds better to a
microphone than a kitchen does.

#### Speaking in phrases

Talk in phrases, the way you would read a sentence aloud to someone, and pause
at the natural places. Each pause sends a phrase to be written, so a phrase is
also the size of thing "scratch that" takes back.

- **Speak at your normal pace.** Slowing down to one word at a time actually
  makes it harder for the engine, because it uses the words around each word
  to work out what you meant.
- **Finish the thought before you pause** where you can. If you do stop
  halfway, on a word like "the" or "and", QUILL joins the two halves for you
  (see "When you stop in the middle of a thought").
- **If you are a thoughtful speaker** who often pauses between words, and
  dictation keeps writing your sentence in pieces, choose a longer **Pause
  before a phrase is written** in Dictation Settings. **Longer** waits two
  seconds and **Longest** three. Your words will appear a little later after
  each pause, but they will come out whole. If you talk quickly and want your
  words fast, **Short** is for you.

#### Punctuation: say it or let it be

With Moonshine, Whisper and the downloaded models, automatic punctuation is
on, and for ordinary writing the easiest thing is to just talk and let the
engine put in full stops, commas and question marks.

Say a mark when you want something particular: "new paragraph" to start one,
"colon" before a list, "open quote" and "close quote" around a quotation, or a
comma the engine would not have guessed. Your spoken mark always wins. If you
would rather say every mark yourself, turn **Automatic punctuation** off, and
the engine will write only what you say.

Two habits that help: say "new paragraph" as a phrase of its own, and say
"period" at the end of a sentence you want to be sure is finished. The
read-back says each mark by name, so you always hear whether it went in.

#### Fixing mistakes as you go

Every engine gets a word wrong now and then. Fixing it by voice soon becomes a
quick loop:

1. **"scratch that"** takes back the whole last phrase. Say it again, a little
   more clearly.
2. **"correct" and the wrong words** (for example "correct red rocks") selects
   them. Say the right words and they replace the wrong ones.
3. **"select" and some words** does the same for anything further back.
4. **"spell that"** is for a name or a word the engine has never heard. Spell
   it with the phonetic alphabet in your next phrase.
5. **Recent Phrases** (`Shift+F11`) shows what was written for your last twenty
   phrases, so you can see what went wrong, and any words that were never
   written. Say "read last sentence" to hear a sentence back with its
   punctuation.
6. When you are done, **Tidy Dictated Text** (`Ctrl+F3`) can fix sound-alike
   words, names and punctuation in a paragraph or a selection with AI, if you
   have a ChatGPT subscription or your own OpenAI key (see "Tidy Dictated
   Text" later in this chapter).

If the same word comes out wrong again and again, add it to **My Words and
Phrases** (`Alt+Shift+F10`). That fixes it for good, in every engine.

#### Dictating with a screen reader running

QUILL was built for this. Two things make it smooth:

- **Wear headphones.** If the read-back and your screen reader come out of
  speakers, the microphone hears them, and they can end up in your document.
  With headphones, the microphone only hears you.
- **Choose what you hear.** After each phrase QUILL plays a soft tone and reads
  the phrase back, marks and all, so you can check it without moving the
  cursor. If that is more than you want, set **What you hear after each
  phrase** in Dictation Settings to a sound only, and read the line with your
  screen reader when you choose to. If you would like to hear the words but not
  the marks, turn off **Say punctuation marks in the read-back** in More
  Dictation Settings.

While dictation is listening, QUILL keeps the speech engine light enough that
your screen reader stays quick. If you find it slowing down, see "On a modest
computer" and the choices below.

#### Choosing a speech engine

- **Moonshine** (built in) is the place to start. It is quick on any computer
  and good with a clear voice and a decent microphone.
- **Whisper** (built in) is a little slower and sometimes better with accents
  or a busier room. It is also what QUILL uses for Spanish.
- **A downloaded model**, such as Parakeet or Nemotron, is more accurate,
  especially with names, accents and fast speech, and still runs entirely on
  your computer. On a computer with 8 GB of memory and four cores, QUILL
  recommends NVIDIA Parakeet Unified 0.6B for English; on 8 GB, NVIDIA
  Parakeet TDT 0.6B v3 for Spanish; see "Better accuracy: optional speech models".
- **OpenAI, with your own key**, is very accurate and very good with names,
  but your speech is sent to OpenAI and they charge you for it. See "OpenAI
  dictation, with your own key".
- **A speech provider, with your own account**, such as Azure, Deepgram or
  AssemblyAI, is the same idea with another company: very accurate, sent to
  that company, billed by them. See "Speech providers: dictation with your own
  account at another company".
- **Windows speech recognition** is there for a language the others do not
  know, but it puts in no punctuation and mishears an untrained voice often.

Speech Models can suggest a model for this computer: open Dictation Settings
(`Alt+Shift+F6`), press **Better Accuracy: Speech Models...** (`Alt+B`),
choose what matters most to you (`Alt+W`) and read the **Recommendation** (`Alt+C`).
"Which speech engine? A guide to choosing", at the start of this chapter,
walks through it with an example.

Try one for a day before you judge it. Everyone's voice suits a different
engine.

#### Spanish

Everything here holds for Spanish too. Use Whisper or a many-language
downloaded model; the larger ones are much better in Spanish than the built-in
one. Let automatic punctuation do the marks, and switch languages with
`Ctrl+Shift+F11` or by saying "switch to Spanish" (see "Switching between
English and Spanish").

#### On an older or slower computer

Stay with the built-in Moonshine; it uses very little. Choose **Normal** or a
longer pause rather than **Short**, close programs you are not using, and keep
the laptop plugged in while you dictate, because battery saver slows
everything down.

#### Practice: try these

Here are two short paragraphs to read aloud. Start Live Dictation with
`Ctrl+F11` in a new document, read each line as one phrase, and pause at the
end of each. Then compare what you got with what should come out.

**Practice one: let the engine punctuate.** Just read these naturally, with
no marks:

> Dear Sam [pause]
> thank you for the lovely flowers they arrived this morning [pause]
> I will see you on Saturday at the market [pause]

What should come out, more or less:

```text
Dear Sam. Thank you for the lovely flowers, they arrived this morning. I will
see you on Saturday at the market.
```

If "Dear Sam" came out with a full stop you do not want, say "scratch that"
and try "Dear Sam comma new paragraph" instead.

**Practice two: say the marks.** Read these exactly as written, marks and
all:

> heading two shopping list [pause]
> bullet milk comma eggs and bread [pause]
> bullet ask Sam about the party question mark [pause]

What should come out:

```text
## Shopping list
- Milk, eggs and bread
- Ask Sam about the party?
```

Then try "correct eggs", say "butter", and listen to it change. If "Sam" came
out as some other word, say "correct" and that word, then "Sam" again.

To practise with QUILL leading you step by step, see the dictation lessons in
the Tutorials, described at the end of this chapter.

### Locked Dictation (Ctrl+F9)

Locked Dictation is a keyboard-only way to dictate a longer passage without
opening a dialog or leaving the editor. It uses the same offline engine and
microphone as **Dictate (Offline)**, so nothing is uploaded: Whisper.cpp, the
QUILL speech models or Faster Whisper, whichever you chose in Manage Speech
Models. It needs no speech model to start: until your engine has one, it
uses the Moonshine tiny model that comes with QUILL. See "The offline speech
tools' engines".

1. Put your cursor where the text should go.
2. Press `Ctrl+F9`. QUILL says "Locked dictation on."
3. Speak as long as you like, across sentences and paragraphs.
4. Press `Ctrl+F9` again to finish. QUILL transcribes what you said and
   inserts it at the cursor as one undoable edit.

There used to be a press-and-hold `F9` mode. It was removed, because a held
key repeats and announces itself endlessly under a screen reader.

#### Stopping, pausing and checking

- **Stopping safely.** While recording, `Escape` stops and keeps your speech
  for transcription. `Shift+Escape` cancels and throws it away. A session also
  stops by itself after five minutes, and it stops and keeps your audio if
  QUILL loses focus.
- **Pause and status.** `Ctrl+Shift+F9` pauses or resumes the session.
  `Alt+F9` speaks the current state without changing anything. When Locked
  Dictation is not recording, the same key answers for Live Dictation instead
  (see "Dictation Status").
- **Distinct sound, one-time hint.** Locked Dictation plays its own sounds, and
  the very first time you dictate, QUILL speaks a short hint about the keys.
- **Remappable.** `Ctrl+F9` and the rest are only the defaults. Change them in
  the Keymap Editor (**Tools > Customize and Support > Keymap Editor...**).

Locked Dictation needs no model: with no other model ready, it uses the
built-in Moonshine tiny. With Whisper.cpp as the engine (the default), the
first press of `Ctrl+F9` offers the small Whisper.cpp engine itself (about
8 MB, verified); answer Yes, and dictation is ready when it finishes. With
**QUILL speech models** as the engine, nothing is downloaded at all. For
fewer mistakes, choose a larger model in
Manage Speech Models (**Tools > Speech > Speech and Dictation...**). It also
needs microphone-capture support, which standard installs include; if it is
missing, QUILL tells you. In Safe Mode, dictation is turned off.

#### Nothing is lost

**Nothing is lost.** Your audio is saved to a recovery folder before
transcription starts, and a transcript that cannot be safely inserted is kept
for you to review.

**Dictation History & Review.** **Tools > Speech > Locked Dictation >
Dictation History & Review...** lists every recording whose transcript was
never inserted: ones left behind by a crash, and ones that could not be placed
safely. For each you can **insert** it at the cursor, **copy** it, or
**discard** it. `Enter` inserts the selected row. If anything is waiting for
review when QUILL starts, QUILL tells you and points you here, so dictated
speech is never silently lost.

#### Locked Dictation settings

**Dictation Settings.** **Tools > Speech > Locked Dictation > Dictation
Settings...** holds the choices the dictation engine reads:

- the session time limit
- stop and keep speech when QUILL loses focus
- intelligent insertion spacing
- a reset that brings back the one-time first-use hint

#### Parakeet 3 and silence

**Parakeet 3: the most reliable dictation engine, and QUILL prefers it once
you install it.** Whisper has a well-known flaw for dictation. Give it silence
(a pause while you think, a breath before you stop) and it sometimes invents
text, most famously a phantom "thank you". Parakeet 3 only writes words when it
actually hears them, so silence produces nothing.

Parakeet 3 is an NVIDIA model. It knows 25 languages, detects the language by
itself, runs on the CPU only, and is about a 670 MB download, listed as
**NVIDIA Parakeet TDT 0.6B v3** among **QUILL speech models** in **Manage
Speech Models** and in Dictation Settings, Speech Models. It is the same
download live dictation, QUILL Lite and QUILL Transcribe use, so a model you
already downloaded in any of them is used here too, and nothing is downloaded
twice. If you downloaded Parakeet 3 in an earlier version of QUILL, it is moved
across by itself when its files are the same as today's download; if they are
not, it is listed as not downloaded, and downloading it once more fixes that.
Once its model is installed, dictation switches to it
automatically. If you have chosen an engine yourself, that choice is always
respected, and removing the model simply returns you to Whisper.cpp, or to
the built-in Moonshine tiny if Whisper.cpp has no model. Nothing else
changes: same keys, same review, same recovery.

**Locked Dictation works before you download a model.** If Whisper.cpp has no model
yet, Locked Dictation uses the Moonshine tiny model that comes with QUILL, the
same one live dictation starts with. If you had chosen the older Nemotron
engine, QUILL now uses the most accurate model you have; download **NVIDIA
Nemotron 3.5 ASR Streaming 0.6B** from the same list to have Nemotron again.
None of these models takes an initial prompt; your words in `dictation.md` and
My Words and Phrases still correct the text afterwards.

**Silence is trimmed before transcription.** QUILL removes the quiet lead-in
and tail from each dictation take before the engine hears it. A recording with
no speech in it at all gets the "no speech" sound, so no engine gets the chance
to make something up. This applies to every engine, Whisper included, and
there is nothing to set.

#### Teach dictation your words

**Teach dictation your words.** A small file called **`dictation.md`** in the
family's dictation folder (see "Where your word list lives") holds your own vocabulary (so names and jargon come back
spelled right), spoken-to-written replacements (such as "new line" becoming a
real line break), and spoken command phrases of your own. It applies to Locked
Dictation and the Dictate (Offline) toggle.

Your vocabulary is used twice. Engines that accept a hint, such as Whisper, are
steered toward your words before they transcribe. Then every engine, including
Parakeet 3, which takes no hints, gets a **fuzzy correction pass afterwards**.
It recognises near misses by spelling and by sound, so "charge b" comes back as
"ChargeBee" exactly as you wrote it, capitals and all. Names split in two,
words run together, and "R&D" heard as "r and d" are all repaired. Ordinary
words are left alone.

The **Voice Interaction** guide ([voice-interaction.md](../voice-interaction.md)),
in its section "Teaching dictation your words," explains the file format and
how to choose a speech engine for these offline tools (Whisper.cpp, the QUILL
speech models such as Parakeet 3 and Nemotron, or Faster Whisper).

#### Filler words

**Filler words can be removed, but only if you ask.** This option is off by
default. Turn it on with the `dictation_remove_fillers` setting, and
hesitations like "uh" and "hmm" are taken out of your transcripts. It pays
attention to language: "um" is only removed when your dictation language says
that is safe, because in Portuguese "um" means "a" or "an", and in German it
means "at" or "around". When QUILL cannot tell the language, it only removes
sounds that are fillers in every language.

### Dictate (Offline)

**Dictate (Offline)** on **Tools > Speech** is a simple toggle that speaks
straight into your document.

1. Choose it, or press the QUILL key (`Ctrl+Shift+Grave`) then `Shift+D`.
   QUILL plays a start tone and the status bar shows "Dictation listening".
2. Speak.
3. Choose it again to stop. QUILL plays a stop tone, transcribes what you said
   in the background, and inserts the text at your cursor as one undoable edit.
   The status bar shows the word count.

**Dictation Microphone...** on the same menu chooses which microphone this
dictation uses, or the system default.

Dictate (Offline) listens with the same offline engine as Locked Dictation,
but it needs one of that engine's models: with Whisper.cpp and no model yet,
QUILL offers to open Manage Speech Models so you can download one. With
**QUILL speech models** as the engine, the built-in Moonshine and Whisper are
its models, so nothing needs downloading. To change the engine or the model,
see "The offline speech tools' engines".

## Transcribing a recording

When you have a recording rather than a live voice, QUILL can turn it into
text in three ways: with Live Dictation's speech engines (**Shift+F5**), with
the offline engine from **Tools > Speech**, or with a cloud service from the
**AI** menu. Whichever you use, you get a draft to read and correct, because
automatic transcription is never perfect.

### Transcribing an audio file

Sometimes the words you want are already in a recording: a voice note from
your phone, an interview, a lecture, a meeting somebody recorded for you.
**Transcribe a Recording** listens to it and writes down what was said, using
the same speech engines as Live Dictation: the two built in, any you
downloaded, or OpenAI with your own key. It works in the background, so you
can keep writing while it listens, and it tells you when it is done. It is
the same command, with the same window and the same key, in QUILL Lite.

How it differs from the other two ways in this section: it needs nothing
downloaded and no ffmpeg, because it uses the models dictation already has
and reads recordings with parts of Windows; it can use any speech model you
downloaded for dictation; and it writes paragraphs, with times if you want
them, straight into a document. Transcribe Audio or Video (Offline) is the
one for video files, captions and speaker labels, and AI > Transcribe Audio >
Transcribe Audio File is the one for Transcript Actions such as meeting minutes.

#### Your first transcription, step by step

1. Press **Shift+F5**, or choose **Tools > Speech > Live Dictation >
   Transcribe a Recording...**. The Transcribe a Recording window opens with
   the cursor in **Recording**.
2. Type the full path of the file, or press **Browse...** (Alt+B) and choose
   it. You can also drag a file from File Explorer and drop it on the window.
3. Check **Language spoken in the recording** (Alt+L): English or Spanish.
4. Check **Speech model** (Alt+M). The most accurate model on your computer is
   already chosen for you. Just below it, **About this model and this
   recording** says what the model is good for, how long the recording is, and
   about how long it should take on your computer, for example "The recording
   is 12 minutes long. With NVIDIA Parakeet TDT 0.6B v3, transcribing it should
   take about 6 minutes on this computer."
5. The transcript is not inserted into the document you are editing. When it
   is ready, its completion notice appears in **Notifications**; activate that
   notice when you are ready to open the privately saved transcript.
6. Press **Enter**. You hear "Transcribing meeting.mp3 in the background."
7. Carry on with whatever you were doing. The status bar shows how far it has
   got, and every quarter of the way you hear it quietly: "meeting.mp3: 25
   percent". When it is done you hear one sentence, such as "Transcribed
   meeting.mp3: 12 minutes, 1,804 words, in 6 minutes." The completion notice
   stays in Notifications so you can open the result later.

That is all there is to it. The rest of this section explains the choices.

#### What the text looks like

The text is written the way dictation writes it: full stops, commas, question
marks and capital letters put in by the speech engine, with the spacing tidied
between sentences. A few more things happen on the way:

- **Paragraphs.** A new paragraph starts wherever the recording goes quiet for
  two seconds or more. If somebody talks for more than two minutes without a
  long pause, the next pause of any length starts a new paragraph, so you never
  get one enormous block.
- **Timestamps, if you want them.** Timestamps are off unless you turn them
  on. Check **Add timestamps** (Alt+T) and every paragraph begins with the
  hours, minutes and seconds where it was said, like this:

      [00:01:23] The budget for the spring term is nearly final.

  It makes it easy to find a passage again in the recording.
- **Your own words.** The corrections in **My Words and Phrases** are used, so
  a name the engine always mishears comes out your way.
- **Filler words.** If you have **Remove filler words** turned on in
  Dictation Settings, the ums and ahs are left out here too.
- **Spoken punctuation.** In a recording, somebody who says "new paragraph" or
  "comma" usually means the words, so they are written as words. If you
  recorded yourself dictating on purpose, check **Obey spoken punctuation and
  commands** (Alt+O): then "comma", "period", "new line", "new paragraph" and
  "scratch that" work just as they do when you dictate. Commands that move the
  cursor are ignored, because there is no cursor in a recording.
- **Translation into English.** For a recording in Spanish, check **Translate
  into English** (Alt+E) and the transcript is written in English instead of
  Spanish. It needs a model that translates: the built-in Whisper, or a
  multilingual Whisper you downloaded (not the ones marked English). With any
  other model, or for an English recording, the box is unavailable. Off
  unless you check it.

#### Which model for which recording

The **Speech model** list shows every model on your computer, most accurate
first: the two that come with QUILL, and any you downloaded in Dictation
Settings, Speech Models (see "Better accuracy: optional speech models"
earlier in this chapter), each with its tier. With your own OpenAI key,
OpenAI's file models are at the end (see below). Speech providers are not in
this list; they are for live dictation only. Here is how to choose:

- **Voice notes and dictated letters.** One clear voice, close to the
  microphone. **Moonshine tiny** is built in, is the fastest by far, and does
  this well. Whisper tiny is the one to try if Moonshine mishears an accent.
- **Interviews and meetings.** Several voices, people interrupting, someone
  further from the microphone. A downloaded model is worth it here. In
  English, **Parakeet Unified 0.6B** is our first choice: in our tests with
  real recordings it made the fewest mistakes (3.2 percent of words wrong on
  audiobooks no model was trained on) and it is quick. **Parakeet TDT 0.6B
  v3** is close behind (3.8 percent) and quicker still; both Parakeet models
  never invent words in a silence. Nemotron (5.3 percent) and Whisper small or
  medium work too, but make more mistakes or are slower.
- **Lectures and talks.** One voice, a long time, and plenty of special words.
  Parakeet again, or a Whisper model. Before you start, add the speaker's
  names and terms to My Words and Phrases, and you will spend less time
  correcting.
- **Noisy rooms.** A café, a car, a hall with an echo. On the harder, noisier
  recordings we tested, Parakeet Unified got 3.2 percent of words wrong,
  Parakeet TDT v3 5.2 and Nemotron 7.3; the two tiny models got more than 13.
  OpenAI is very good with noise too, if you use your own key (see below).
- **Spanish.** Choose Spanish as the language first. **Parakeet TDT 0.6B v3**
  is our first choice: 4.4 percent of words wrong on FLEURS Spanish, where the
  built-in Whisper tiny got 30.5. Nemotron and the multilingual Whisper models
  know Spanish too. The list shows only the models that know the language you
  chose.

A model that is too slow for live dictation is fine for a recording: nobody is
waiting at the end of each sentence. The estimate tells you the wait before you
start.

#### How long it takes

How long depends on the model and on your computer. These are our estimates
for a one-hour recording, worked out from the speeds we measured for each
model on real recordings in October 2026, on a modest computer (two processor cores, 4 GB of memory) and on a
more capable one (four or more cores, 8 GB or more):

| Model | Modest computer | Capable computer |
|---|---|---|
| Moonshine tiny (built in) | 6 minutes | 3 minutes |
| Whisper tiny (built in) | 12 minutes | 6 minutes |
| Parakeet TDT 0.6B v3 | 15 minutes | 7 minutes |
| Parakeet Unified 0.6B | 18 minutes | 8 minutes |
| Nemotron | 27 minutes | 12 minutes |
| Whisper small | 1 hour 49 minutes | 46 minutes |
| Whisper large-v3-turbo | about 6 hours | about 2 and a half hours |

For a real example: a three-minute recording took 10 seconds with Moonshine
tiny, 20 seconds with Whisper tiny and 25 seconds with Parakeet on the computer
QUILL is developed on, plus a few seconds the first time while the model
loads.

Transcribing uses two of your processor's cores, the same as dictation, so
your screen reader stays quick. The model is put away a few minutes after the
last transcription finishes, which gives its memory back.

#### Where the text goes

- **The document in front stays untouched.** There is no destination picker,
  and the transcript is not inserted into the text you were editing.
- **Open it when you are ready.** QUILL saves the transcript privately and
  adds a completion notice to **Notifications**. Activate that notice to open
  the transcript in the editor. Save the document with **Ctrl+S** if you want
  a separate file in a location you choose.

#### Several recordings, checking on it, and stopping

- **Several at once.** In Browse, hold **Ctrl** and choose more than one file.
  They are transcribed one after another with the same choices, and each
  completed recording gets its own notice in **Notifications**. Activate a
  notice to open that transcript. If one is already running when you start
  another, you hear "Added to the queue".
- **How far has it got?** Press **Shift+F5** again. At the top of the window,
  **Transcribing now** says which recording it is on, how far it has got, and
  how many are waiting. Press **Escape** to close the window and let it carry
  on.
- **Stopping.** In that same window, press **Stop Transcribing** (Alt+S). The
  recording being transcribed stops, any waiting ones are forgotten, and
  nothing is written into a document.
- **If you missed what it said.** Open **Notifications** to find and reopen a
  completed transcript. **Shift+F9** opens Activity, which keeps every
  transcription this session, finished or failed, with the reason when
  something went wrong.

#### Which files it can read

MP3, M4A, AAC, WAV, Ogg, Opus, FLAC and WMA, and also the sound in an MP4 file
and AIFF. QUILL reads all of them itself, using parts of Windows that are
already on your computer, so there is nothing extra to download and no other
program to install. Files with copy protection, such as some bought audiobooks,
cannot be read.

#### Privacy, and OpenAI with your own key

With the models on your computer, **nothing leaves your computer**. The
recording is read, not copied, and nothing is kept afterwards except the text.

If you have your own OpenAI key saved in Use My Own AI Key, OpenAI's speech
models appear at the bottom of the list a moment after the window opens. OpenAI
is very accurate, especially with several voices, accents and noise, but
**it sends your recording to OpenAI**, so it is never chosen for you, and it is
never offered in Safe Mode. When you choose it and press Enter, a question says
exactly what will be sent. The answer is No unless you choose Yes, every time.
If you agree:

- the speech in the recording is sent over an encrypted connection to OpenAI,
  about a minute at a time, with your own key, and the words come back;
- OpenAI bills your account by the minute of audio;
- the names in My Words and Phrases are sent as words to expect;
- nothing goes through QUILL's servers, and QUILL keeps no copy;
- OpenAI's own policies apply to what it receives; you can read them at
  openai.com/policies.

Please only send recordings you have the right to share, and that the people
speaking in them have agreed to. The live model, gpt-live-transcribe, is not
in this list: it is made for a microphone, not a file.

#### Messages you might hear

- **"meeting.mp3 was not found."** The file was moved or renamed. Choose it
  again with Browse.
- **"meeting.mp3 could not be read as a recording."** It is not one of the
  formats above, or it is damaged or protected.
- **"meeting.mp3 was read to the end, but no speech was found in it."** The
  recording is silent, or very quiet. Nothing is written.
- **"... could not be loaded, so this used the built-in engine."** A
  downloaded model would not load, so Moonshine did the work instead.
  Removing and downloading the model again in Speech Models may help.
- **"Stopped transcribing meeting.mp3."** You pressed Stop Transcribing.
- **"Could not transcribe meeting.mp3"**, followed by the reason, for
  anything else. You hear the error tone, and the reason stays in Activity.

### Transcribe on your computer

QUILL can transcribe **entirely on your computer**, with no cloud account and
without uploading your audio. **No AI account or key is required**, and you
do not need to turn on Artificial Intelligence to use it.

1. Choose **Tools > Speech > Transcribe Audio or Video (Offline)...**.
2. Pick an audio or video file.
3. Choose a transcript format: **plain text, Markdown, or HTML**.
4. Keep working while it runs in the background. QUILL tells you when it is
   done and how many words it produced, and opens the result as a draft
   document you can edit.

This uses the offline speech tools' engine: Whisper.cpp, the QUILL speech
models or Faster Whisper, whichever you chose in Manage Speech Models, and
the built-in Moonshine tiny when none of them is ready. The first time, QUILL
may offer to fetch the Whisper.cpp engine and a model for you; nothing
downloads unless you agree. "The offline speech tools' engines", at the start
of this chapter, says which to choose, and the Speech section later in this
chapter explains models and engines in full.

#### Supported formats and FFmpeg

**Supported formats.** You can pick MP3, M4A, AAC, FLAC, OGG, Opus, WMA, WAV,
MP4, M4V, MOV, MKV, WebM, or AVI.

If **ffmpeg** is installed, QUILL converts the file for you before
transcribing, so you never have to make a WAV yourself. QUILL does not ship
ffmpeg, but it can fetch it:

- The **Download FFmpeg...** button, on the Dictation (Offline) tab of **Tools >
  Speech > Speech and Dictation...**, downloads the official build (about 110
  MB, with a progress bar you can cancel) and sets it up. It is also
  "Download FFmpeg" in the Command Palette (`Ctrl+Shift+P`).
- Or install it yourself once (for example, `winget install Gyan.FFmpeg`) and
  QUILL finds it on your PATH.

ffmpeg is open source (GPL/LGPL) and comes straight from the official builder.
QUILL never bundles or redistributes it. Without ffmpeg, the whisper.cpp engine
needs a 16 kHz mono WAV, while the Faster Whisper engine can handle the other
formats by itself.

#### Captions and speaker labels

- **Generate Captions (Offline)...** on **Tools > Speech** transcribes a file
  with timestamps and saves the result as **SRT** or **VTT** caption files.
- **Speaker attribution.** If you download the "Small English with speaker
  detection" model (in Manage Speech Models), QUILL marks **who is speaking
  when**. Each turn is labelled "Speaker 1", "Speaker 2", and so on in the
  transcript, in bold in Markdown and HTML. It tells the turns apart; it does
  not name the people.

### Transcribe Audio File

If you have AI set up, **AI > Transcribe Audio > Transcribe Audio File...**
sends a recording to OpenAI Whisper in the cloud. The Transcribe Audio submenu
is one of the longer AI commands: it appears once **AI > Use Artificial
Intelligence** is on and **AI > Show advanced AI features** is checked
(Chapter 10 explains both).

1. Choose **AI > Transcribe Audio > Transcribe Audio File...**. A file picker
   opens.
2. Pick the audio file. Supported formats: MP3, MP4, M4A, WAV, WEBM, OGG, FLAC
   (maximum 25 MB).
3. Choose your options:
   - **Language**: detect it automatically, or pick a language for better
     accuracy.
   - **Speaker diarization** (uses Deepgram): works out who is speaking when.
     Each turn is labelled Speaker 1, Speaker 2, and so on, with timestamps.
     This needs a Deepgram API key set up in AI Hub.
   - **Translate to English**: transcribes audio in any language and gives you
     an English translation in one step (Whisper translation mode).

When the transcript is ready, QUILL asks **"What would you like me to make of
this?"** and offers a short list of **Transcript Actions**, chosen to suit the
recording. Pick one and QUILL turns the transcript into a finished document,
such as meeting minutes, action items, study notes or a clean draft, and opens
it for you to review and edit. Or choose **"Just keep the transcript"** to go
to the viewer, where you can copy it, insert it at the cursor, or open it as a
new document. If AI is turned off, you go straight to the viewer.

To get an English translation of a recording, use the **Translate to English**
option in the step above. Earlier versions also had a separate Translate Audio
File to English command; it is no longer on any menu.

### Transcript Actions

A transcript is rarely what you actually need. You want the minutes, the
action items, or a clean draft. **Transcript Actions** make that last step one
choice away. You can reach them in two places:

- **Right after transcription**, in the "What would you like me to make of
  this?" chooser described above.
- **Any time**, on text you already have, with **AI > Transcribe Audio >
  Transcript Actions...**. Paste in a transcript or notes (or select part of
  your document) and pick an action.

The built-in actions are:

- **Meeting Minutes**: attendees, decisions, action items with owners,
  follow-ups.
- **Action Items**: every task and commitment as a numbered list you can act
  on.
- **Executive Summary**: a short briefing for leadership.
- **Interview Notes**: questions, answers, strengths, concerns and an
  assessment.
- **Study Notes**: a lecture or talk turned into organized notes.
- **Q&A Extraction**: every question and its answer in clean Q&A format.
- **Clean Up & Draft**: spoken rambling turned into a clean, readable draft.
- **Follow-Up Email**: a warm, ready-to-send recap with next steps.
- **Key Quotes**: the most notable quotes, word for word, with who said them.
- **Decisions Log**: just the decisions made, each with its reason and owner.

QUILL puts the most likely ones first for the recording in front of you. A
meeting with several speakers starts with Minutes and Action Items; a single
voice starts with Clean Up & Draft. Every action is always there, though. The
finished document opens in a new window, so your original transcript is never
overwritten. Transcript Actions use whichever AI provider you have set up in
the AI Hub.

## Automate transcription with watch folders

A watch folder lets you set a rule once: drop a file in this folder, and QUILL
deals with it. You will find the commands on **Tools > Watch Folder**.

### The Watch Folder menu

- **Watch Folder Monitoring (in Settings)...** turns on or off the automatic
  opening of supported files dropped into a folder you have chosen.
- **Watch Folder Profiles...** sets the folder path, whether subfolders count,
  what happens at startup, and how often the folder is checked.
- **Watch Folder Queue...** shows what is happening right now and the settings
  in use.

Watch folders are good for "drop and open" work: copy supported files into one
folder and let QUILL open them in the background. They respect Do Not Disturb
and run quietly.

### Transcribing arriving audio

Each watch profile runs one action on every file it picks up. As well as
opening, moving, copying, converting, running a macro or a sandboxed
transform, and OCR, a profile can **transcribe arriving audio**. Any audio or
video file dropped into the folder is transcribed on your machine with the
offline speech engine, and a transcript is written next to it. Nothing is
uploaded.

Choose the **Transcript format** in the profile:

- plain **Text** (`.txt`)
- **SubRip captions** (`.srt`)
- **WebVTT captions** (`.vtt`)
- **Markdown** (`.md`)

The caption formats carry timestamps. If the engine returns no timed parts,
they fall back to plain text, so you never get an empty caption file. This
needs no consent. If no speech model is installed yet, the profile tells you to
download one from Manage Speech Models (**Tools > Speech > Speech and
Dictation...**).

There is also a separate **Transcribe audio (OpenAI Whisper)** action for
cloud transcription, once you have turned on AI and set up a key.

### Making minutes automatically

A transcribe profile can also **chain an AI Action onto each recording**:

1. In **Tools > Watch Folder > Watch Folder Profiles...**, point a profile at a
   folder (for example, *Meetings*).
2. Choose a transcribe action (offline or OpenAI Whisper).
3. Under **Then make**, pick a Transcript Action, such as *Meeting Minutes*.

From then on, every recording that lands in that folder is transcribed, and the
minutes document is written next to it, with a name like
`standup-meeting-minutes.md`. If AI is off or no provider is set up, you still
get the transcript. The action step is skipped with a note, never an error.

### The Watch Folders page in Settings

- **Enable folder watching by default** starts watching your enabled
  profiles each time QUILL starts. It is off to begin with. **Watch Folder
  Monitoring (in Settings)...** brings you to Settings so you can turn it on.
- **Default watch folder**: if you just want one folder where anything you
  drop gets opened, you don't need a profile. Put the folder here, and QUILL
  opens each new supported file that lands in it. Blank to begin with.
- **Start watching automatically** is the switch that watches your default
  folder, from the moment QUILL opens and for as long as it runs. It works on
  its own, so you can watch the default folder without turning on Enable
  folder watching by default, which starts your profiles. Safe Mode turns
  both off. Off to begin with.
- **Include subfolders**: turn this on and files in folders inside your
  default folder count too. Off to begin with.
- **Process existing files on start**: normally QUILL only opens files that
  arrive after it starts watching. Turn this on to have it open what's
  already waiting in the default folder as well. Off to begin with.

Your profiles each have their own folder and their own Include subfolders,
existing files and startup choices; these four only decide for the default
folder.
- **Poll interval (seconds)** is how often a watched folder is checked, from
  2 to 300 seconds. The default is 5.
- **Watch folder: play a sound on each check** plays a short tick every time
  the folder is checked, so silence means the watcher has stopped rather than
  found nothing. Off to begin with.
- **Watch folder: let results interrupt speech** announces a newly opened
  file straight away, cutting across whatever is being said. Off means the
  notice waits its turn.

## Speech

**Tools > Speech** is where QUILL keeps its on-device speech tools: the
transcription and dictation commands you have already met, and the speech
models and engines that make them work. You do not have to understand any of
this to dictate. Come here when you want a more accurate model, a lighter one
for an older computer, or a different engine.

### Manage Speech Models

**Tools > Speech > Speech and Dictation...** opens Manage Speech Models (the
command keeps that name in the Command Palette). It lists local speech models
with their download size,
accuracy and speed, and helps you pick one that will run well on your computer.

- The dialog opens with a one-line summary of your machine: its RAM, and
  whether a GPU was found.
- Each model shows roughly how much memory it needs. A model too big for your
  RAM is flagged.
- Each model names its tier: **Lightweight**, **Balanced** or **High
  accuracy**, the same three words dictation uses.
- The best fit for your computer is marked **"Recommended for your
  computer"**, followed by why, in the row itself: your memory and graphics
  card, and what that allows. The guided offline-speech setup shows the same
  reason below the engine's description.
- A larger model warns you when there is no GPU, because it will be slow on
  the CPU.
- With **QUILL speech models** chosen as the engine, five English-only models
  are no longer in the list: Distil-Whisper small.en, Whisper small.en,
  Distil-Whisper medium.en, Whisper medium.en and Distil-Whisper large-v3.
  They were removed in this release. See "Models removed in this release".

The tiers of the QUILL speech models come from our tests on real recordings;
see "How we chose: tested on real speech".

**Choosing what to do.** Pick a model, then choose an action: **Download this
model** if it is not installed, or **Remove this model from my computer** if it
is. Before a download starts, QUILL warns you if there is not enough free disk
space.

**Downloads run in the background and show progress.** You can keep working.
A progress window shows a **percentage** and has a **Cancel** button you can
press at any time, and QUILL announces progress as it goes. Cancelling cleans
up the partial file. Models come over a secure connection from the Hugging Face
Hub and are stored on your computer. Downloading is turned off in Safe Mode.

**Manage Speech Models** is the **Dictation (Offline)** tab of the Speech
Settings dialog. When more than one local engine is available, it asks which
**Speech Engine** to use. A **Set as Default** button (or a right-click option)
chooses which downloaded model QUILL uses without switching engines. QUILL
remembers your choice and uses it for transcription, captions and dictation.

### Choosing a speech engine

**Choosing a speech engine.** This choice is for the offline speech tools:
Locked Dictation, Dictate (Offline), Transcribe Audio or Video (Offline),
captions and watch folders. Live Dictation has its own engine setting, in
Dictation Settings (`Alt+Shift+F6`). All three engines run **entirely on your
computer**:

- **Whisper.cpp**, the default: light and fast, and works on any computer.
  The engine is a small download (about 8 MB) the first time you need it; see
  "Getting the offline engine". Its models download in Manage Speech Models,
  from **Tiny** (75 MB) to **Large (v3)** (about 3.1 GB); **Small** (465 MB)
  is the recommended starting point. Only Whisper.cpp has the **Small English
  with speaker detection** model, which labels who is speaking. Choose it when
  you are not sure.
- **QUILL speech models (Parakeet, Nemotron and more)**: the same models Live
  Dictation, QUILL Lite and QUILL Transcribe use, in the same folder, so a
  model you already downloaded for Live Dictation is ready here with nothing
  more to fetch. It includes the built-in Moonshine tiny, so it works with
  nothing downloaded. Choose it for **Parakeet Unified 0.6B**, which made the
  fewest mistakes in English in our tests, **Parakeet 3**, which did best in
  Spanish and never invents words from silence, or **Nemotron**, which knows
  English and Spanish. Once
  Parakeet 3 is installed, QUILL uses this engine by itself unless you chose
  one yourself. It replaces the separate Parakeet and Nemotron engines of
  earlier versions.
- **Faster Whisper**: the most accurate, a larger download, more memory, and
  the only engine that can use your **graphics card**. It installs when you
  choose it, where your copy of QUILL can install it; otherwise it is not
  offered. It has its own models. It does not label speakers.

Whisper.cpp and Faster Whisper each have their own models, so download a model
after switching to one of them. To switch, choose the **Speech Engine** on the
Dictation (Offline) tab, or run the guided setup described in "Setting up
offline dictation". For a side-by-side comparison with Live Dictation's
engines, see "Which speech engine? A guide to choosing" at the start of this
chapter.

**Vosk is no longer a dictation engine.** Since October 2026, Vosk is used
only to work out **podcast chapters**. It ships with QUILL for that job,
because it scored best at it: 0.372 against 0.316 for Whisper medium on
hand-made chapter lists, from a 40 MB model, with no download. For dictation
and voice commands it was the wrong choice: it knows only English, its last
release was in 2022, and its models are checked by MD5 only, where every
other download QUILL makes is checked by SHA-256. The built-in **Moonshine
tiny** is faster and more accurate, and needs no download. If you had chosen
Vosk for dictation, QUILL now uses your default engine; if you had chosen it
for voice commands, QUILL now uses Moonshine tiny. QUILL tells you this once,
the first time it starts after the change.

### Getting the offline engine

The private, on-device speech engine (whisper.cpp) is not bundled in the
installer. The first time you use offline dictation or transcription, QUILL
**offers to download it for you**: about 8 MB, checksum-verified, with a
progress bar you can cancel. It is turned off in Safe Mode. If you said no
then, fetch it any time from the all-in-one **Help > Download Optional
Components...** list described below. There is no separate menu item for it.
You need the engine, but not yet a model, for Locked Dictation: until
Whisper.cpp has a model, Locked Dictation uses the built-in Moonshine tiny.
Dictate (Offline) and Transcribe Audio or Video need a Whisper.cpp model. To
skip all of this, choose **QUILL speech models** as the engine instead. If you are **upgrading** from a version
that bundled the engine, your existing copy is kept and keeps working, with
nothing to download.

The installer does not include it and has no option to add it. In a
portable copy you can also place the executable under
`tools\speech\whispercpp` yourself. You do not need to install anything else or change
your PATH. Then download a model from Manage Speech Models.

Offline **dictation** also needs microphone-capture support (the optional
`sounddevice` package). If it is missing, QUILL tells you, and you can still
use Windows dictation.

### Hugging Face Token

**Hugging Face Token...** on **Tools > Speech** is optional. QUILL's speech
models are open source (MIT) and need **no Hugging Face account** to download.
If you fetch a lot of models and run into Hugging Face's rate limits, a free
access token raises them.

The first time you open it, QUILL explains the steps: sign in or sign up at
huggingface.co, open **Settings > Access Tokens**, and create a token with the
**Read** role. It offers to open the token page in your browser, and then you
paste the token in. The box hides what you type, and the token is stored in
Windows Credential Manager, never in a settings file. Leave the box blank to
remove a saved token.

### Cloud transcription providers

The offline engines keep everything on your machine. If you also want a cloud
provider, for example **OpenAI Whisper** for its accuracy, install the
**OpenAI Whisper Transcription** Quillin (a bundled extension) and set up an
OpenAI API key in AI Hub. It then shows up as a provider on the **Dictation
(Online)** tab of Speech Settings. That tab is kept apart from the offline
engines, so local engines (install once) and cloud ones (API key, paid per use)
are never mixed in one list. If no cloud provider is installed, the tab tells
you how to add one.

Cloud providers are **opt-in and never silent**:

- Audio is uploaded only when you choose to transcribe a file with that
  provider. Never offline, and never in Safe Mode.
- The watch folder's offline transcription always uses the on-device engines,
  so a cloud provider can never upload your audio automatically.
- An extension that adds a provider contains no code and asks for no network
  permission. QUILL does the upload itself, through its own checked network
  path, so the extension never sees your audio or your key.

Developers can read more in the Quillin guide, "Transcription providers".

### The Transcription page in Settings

- **Transcription provider preference** is **Local first** (the default) or
  **Cloud first**, for when you have both kinds of provider.
- **Show cloud transcription providers** lists cloud providers beside the
  ones on your computer. On to begin with.
- **Auto-open Status Page on model download** opens the Status Page whenever
  a speech model starts downloading. Off to begin with.
- **Status page refresh announcements** is how often the Status Page speaks
  its updates: **Quiet** (the default) says nothing on its own, **Normal**
  speaks about every thirty seconds, and **Verbose** about every ten.
- **QUILL Whisperer safe mode lock** stops speech-model downloads and retries
  while leaving the status pages working.
- **Voice commands (push-to-talk)** and **Voice conversation mode** turn on
  the voice commands described in Chapter 8.
- **Voice recognition engine** chooses what listens for voice commands:
  **Follow main engine**, **whisper.cpp (accurate)** or **Moonshine tiny
  (fast, light)**, which is built in and suits always-listening best.
- Four settings pace conversation mode, all in milliseconds, and 0 switches
  each part off: **Conversation: pause before a command ends (ms)** (2000 to
  begin with; 0 uses the engine's own pause), **Conversation: cancel window
  before acting (ms)** (900), **Conversation: keep listening after a command
  (ms)** (3000) and **Conversation: 'still working' tick interval (ms)**
  (2000).
- **Conversation: your name (optional)** lets QUILL use your name in its
  prompts, as in "Listening, Sam." Leave it blank for plain prompts.
- **Conversation: speak prompts aloud** speaks the welcome and follow-up
  prompts with your Read Aloud voice. It is off to begin with, so QUILL does
  not talk over your screen reader; the sounds and the status bar still tell
  you what is happening.

## Download Optional Components (Help menu)

To keep the installer small, QUILL fetches several large or optional pieces
only when you want them. **Help > Download Optional Components...** is the one
place to see, get, test and remove them all.

Everything here is optional. The base app, and the SAPI 5 voices built into
Windows, work without any of it, so download only what you need. In **portable
mode**, components install into your portable data folder, so your whole setup
travels with you on the drive.

### What is in the list

The list puts the most important first:

- **Pandoc**: document conversion for Word, ODT, EPUB and RTF.
- **PDF and Office text extraction** (MarkItDown, pdfplumber and pypdf): an
  optional second reader for Word, PowerPoint, Excel and PDF documents. You do
  not need it: QUILL reads all of these with its own readers, and for Word,
  Excel, PowerPoint and OpenDocument files QUILL's own reader goes first, so
  MarkItDown is asked only when that reader cannot read a file (or when you
  choose **MarkItDown first** for Word files). It still goes first for Excel
  97-2003 (.xls) files, which QUILL cannot read by itself without LibreOffice.
  In some builds it cannot run at all (it needs a part the installer leaves
  out), and then QUILL's own readers do the work and nothing asks you to
  download it.
  Scanned or image-only PDFs still need **File > Import > Import / Convert Document (OCR)...** either way.
- The **braille translation pack**: liblouis tables and BRF profiles for the
  Translation submenu and for BRF and embossing export.
- **Dictation (offline speech)**: a guided setup covering Whisper.cpp, QUILL
  speech models (Parakeet, Nemotron and more) and Faster Whisper, described
  below.
- **Kokoro** and **Piper** neural voices, and **eSpeak NG** voices. DECtalk
  is listed too, but says "Install separately": QUILL does not distribute it.
- **Audio: export, playback & chapters**: FFmpeg for exporting compressed
  audio, the mpv playback engine, and MP3 audiobook chapter markers, all in one
  place. Each piece is fetched only when its feature is first used.
- The **MathCAT** math-speech engine.
- **Git** and the **GitHub CLI**: portable fallback copies for **Tools > Git
  and GitHub > Local Git** and the Codespaces commands on **Tools >
  Git and GitHub**. The section "Downloading git and the GitHub CLI", where this guide
  covers Git and GitHub, has more.
- The **Node.js** runtime, for Node Quillins and the Developer Console's
  TypeScript interface. It comes last, as the extra people use least.
- Any non-English **spell-check dictionaries**.

Each row shows whether it is **Installed** or **Available to download**, and
its size. Selecting a row shows a plain description of what it gives you and
what it costs.

### Download, Test, Remove and Set as Default

- **Download** fetches a component you do not have yet, checksum-verified,
  with its own progress.
- **Test** proves an installed component works, so you can trust it before
  you rely on it. A voice speaks a short sample so you actually hear it. The
  offline speech engine transcribes a spoken phrase and tells you what it
  heard. Tools report their version. If a component just needs one more piece,
  Test takes you straight to it: the guided engine-and-model picker for offline
  speech, or Manage Voices for a voice engine with no voice yet. An unfinished
  setup is not treated as an error, and QUILL only offers to send a bug report
  when a test really fails.
- **Remove** deletes QUILL's downloaded copy of a component and turns its
  features back off. Removing a voice engine you were using, for example,
  switches Read Aloud back to the system voice. It only ever removes copies
  QUILL downloaded, never a system tool or a shared install.
- **Set as Default:** for a voice engine (Kokoro, Piper and the other Read
  Aloud engines), the **Set as Default** button here makes that engine, and a
  voice you pick from it, your Read Aloud default without opening another
  speech dialog. The button is only available for a component that can be a
  Read Aloud default, and only once it is installed. The same **Set as
  Default** is also in Manage Speech Models and Manage Voices (with a
  right-click option on the list), for the offline dictation model and for
  voices. Downloading a model or voice engine makes it the default
  automatically; use these when you want to switch back to one you already
  have. Voice previews stop cleanly when you move to another before the first
  one finishes.

### Setting up offline dictation

The **Dictation (offline speech)** row opens a guided setup instead of a plain
download. It takes you one step at a time, and a banner at the top always says
which step you are on and the one thing to do next:

1. Pick and install an engine: **Whisper.cpp** (light and fast), **QUILL
   speech models** (the models QUILL Lite and QUILL Transcribe use: Parakeet 3,
   the most reliable for dictation and described earlier in this chapter,
   Nemotron, Whisper and Moonshine), or **Faster Whisper** (can use a graphics
   card).
2. Download a model. The best fit for your computer is already selected.
3. Choose **Test dictation** to make sure it works, then set it as your
   default.

QUILL remembers the engine you chose, so the setup reopens where you left off
instead of going back to the built-in engine.

### Pandoc on demand

**Pandoc downloads itself when you need it.** You do not have to visit this
dialog first. The moment you **Import** or **Export** a Word, ODT, EPUB or RTF
document (or run **Convert File**) without Pandoc, QUILL offers to download the
official, pinned build right there: about 45 MB, verified, with a progress bar.
The conversion is ready as soon as it finishes. Plain text and Markdown never
need Pandoc, which is why it is not bundled.

### On a Mac

**On macOS, several of these come from Homebrew rather than a QUILL download.**

- The braille translation pack download contains a Windows `lou_translate`
  program, so on macOS QUILL points you to `brew install liblouis` instead.
  QUILL finds a Homebrew liblouis by itself, so no download is needed.
- Pandoc and Tesseract work the same way. Install them with Homebrew (`brew
  install pandoc`, `brew install tesseract`) and QUILL finds them.
- LibreOffice, used to import older Office formats and Apple Pages, is found
  automatically at its standard `/Applications/LibreOffice.app` location on
  macOS (it is never on PATH there). Install it from libreoffice.org or with
  `brew install --cask libreoffice` if you need those imports.

## Performance and Memory

QUILL is built to run all of its AI and speech features on a modest computer
with no graphics card and not much memory. It does that by being careful with
memory, never by switching features off. Two settings under **Settings >
Performance and Memory** control it:

- **Unload idle models after (minutes)** frees the memory used by an AI,
  read-aloud or dictation model you have stopped using. The next time you need
  it, QUILL loads it again by itself. Set it to **0** to keep models loaded
  until you close QUILL.
- **Low-resource mode (one model at a time)** keeps only **one** model loaded
  at a time and prefers
  the smallest model that fits. It never turns off AI or speech. It loads them
  one at a time, so you wait a moment for a reload in exchange for using much
  less memory. On a machine with very little memory it turns on
  **automatically** and tells you once, out loud, so it never takes you by
  surprise.

You do not have to touch either of these. QUILL picks sensible defaults for
your machine, but they are there if you want to tune how much memory it uses.

## What you learned, and where to go next

You can now dictate with Live Dictation (`Ctrl+F11`), pressing it to start and
again to stop, or holding it while you talk once you turn that on, with Locked Dictation (`Ctrl+F9`) or with Dictate
(Offline), and teach QUILL your own words in `dictation.md`. You know that
your words go where you started speaking, how to see them while you talk with
Nemotron or OpenAI, how to say "correct that", how to talk to the AI out loud,
and what OpenAI dictation sends and how to turn it on or off. You can spell,
select, correct and move by voice, put in snippets and Copy Tray slots, switch
between English and Spanish with `Ctrl+Shift+F11`, keep a live transcript
with `Ctrl+Alt+Shift+PageDown`, and dictate into other programs through Quill
Inkwell. You can transcribe a recording on your own computer or with
**AI > Transcribe Audio > Transcribe Audio File...**, turn it into minutes or notes with
Transcript Actions, and set a watch folder to do all of that for you. You know
which speech engine each of these uses, how to choose one for privacy, speed
or accuracy, and what a cloud engine sends. You also know where speech models,
optional components and the memory settings live.

To practise with QUILL beside you, open **Help > Tutorials...**
(`Ctrl+Alt+F1`) and try "Write by talking". The same track, "How much QUILL
says", also has five short dictation lessons: "Punctuation and symbols by voice", "Fix a word by
voice", "Snippets and clips by voice", "Switch to Spanish and back" and "Make
a live transcript". Each takes a few minutes, with QUILL telling you what to
say. The
**[Dictation commands](../dictation-commands.html)** page and the Voice
Interaction guide are the best companions to this chapter.

Next, Chapter 10, AI, when you want it, shows what the assistant can do with
your writing, including the AI behind Transcript Actions.

---

- Previous: [Chapter 8: Reading, reviewing and listening](quill-guide-08-reading-reviewing-and-listening.html)
- Next: [Chapter 10: AI, when you want it](quill-guide-10-ai-when-you-want-it.html)
- [Contents](../userguide.html)
