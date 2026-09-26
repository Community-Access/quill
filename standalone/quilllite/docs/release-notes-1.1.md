# QUILL Lite 1.1 — What's New

Two things are new in 1.1:

- **[Dictation](#dictation).** Press **Ctrl+F11**, talk, and pause. What you
  said is written at the cursor with the punctuation put in for you, and QUILL
  Lite reads it back so you know it is right.
- **[AI help with your own OpenAI key](#ai-help-with-your-own-openai-key).**
  Paste a key and every limit on AI help is lifted.

---

## Dictation

The speech recognition comes with QUILL Lite. There is nothing to download, no
account to make, and nothing you say leaves your computer. No recording is kept
anywhere.

### Getting started

1. Put the cursor where you want the words.
2. Press **Ctrl+F11**. You hear two rising tones and "Dictation on".
3. Talk the way you would talk to a person, and pause. The sentence is written,
   a soft tone says it went in, and QUILL Lite reads it back to you.
4. Keep going. It keeps listening between sentences.
5. Press **Ctrl+F11** again, or say "stop dictation", to stop.

### Punctuation goes in by itself

You do not need to say punctuation: full stops, commas, question marks and
capitals go in by themselves. Say a mark whenever you want a particular one,
and your word wins.

### Fixing things by voice

Say these on their own, after a pause:

- **"scratch that"** takes out the last phrase. Say it again for the one before.
- **"select that"** selects the last phrase, so you can fix it with the keyboard.
- **"capitalize that"**, **"all caps that"**, **"no caps that"** change its capitals.
- **"delete word"** and **"delete sentence"** delete back from the cursor.
- **"undo that"** is Ctrl+Z; **"read that"** reads the last phrase again.
- **"go to end of line"**, **"go to top"** and their friends move the cursor.

### Spelling a name

Say **"start spelling"**, then the letters -- "capital bravo alpha delta" writes
*Bad* -- then **"stop spelling"**.

### Starting with your voice

Switch on the **wake phrase** in Dictation Settings and say **"Quill dictate"**
to start without touching the keyboard -- or choose a phrase of your own. It
listens only while QUILL Lite is the window in front, and nothing it hears is
kept unless it starts with the wake phrase. It is off until you turn it on.

### Stopping with your voice

Say **"stop dictation"** on its own to stop -- or choose your own **stop phrase**
in Dictation Settings. It counts only when it is all you said, so the same words
inside a sentence are simply written.

### Talking in one long run

Switch on **Just write what I say** in Dictation Settings and a pause does
nothing: no full stop because you paused, no tone, no read-back, and no voice
commands -- only the punctuation you say and your stop phrase. For thinking out
loud, telling a story, or a good rant, without being interrupted.

### Fine-tuning

Dictation Settings also has **automatic punctuation** on or off, how long a
**pause** ends a phrase (short, normal or long), **remove filler words** like um
and uh, **stop after silence** (1, 5 or 10 minutes), and **Test Microphone**,
which listens for four seconds and tells you how loud you were and what it
heard.

### Your own words and phrases

**Edit My Words and Phrases** in Dictation Settings opens a small file where you
list names dictation should spell your way, and phrases of your own: say *my
email address* and it writes your address.

### Every command, in one place

Say **"what can I say"** while dictating, and a window lists everything
dictation understands, your own phrases included. The same list is its own page
in the documentation, **Dictation commands**.

### Settings: engine, microphone, and what you hear

**Tools ▸ Dictation ▸ Dictation Settings...** (**Alt+Shift+F6**):

- **Speech engine.** **Moonshine** is the one it starts with: fast even on a
  modest computer. **Whisper** is a little slower; try it if Moonshine often
  mishears you. Both are built in and understand English. **Windows speech
  recognition** can use any speech language installed in Windows, but you say
  the punctuation yourself. **Windows voice typing** hands over to Windows+H.
- **Microphone**, by name, or the Windows default.
- **What you hear** after each phrase: a sound, the words read back, both, or
  neither.

If the read-back comes out of speakers, the microphone can hear it too. Use
headphones, or choose a sound only.

### Knowing what it is doing

The status bar has a new **Dictation** part -- off, listening, hearing you,
writing, spelling, or waiting for the wake phrase -- and **Tools ▸ Dictation ▸
Dictation On** is checked while it writes.

---

## AI help with your own OpenAI key

**Tools ▸ AI ▸ Use My Own OpenAI Key** (**Alt+F2**). Paste an OpenAI key, press
OK, and every limit on AI help is lifted — no monthly, daily or hourly
allowance, and no size ceiling.

### Choosing the model

Once the key is checked, the **Model** list holds every model your account can
use for text, **Luna 6 first, then the other GPT-6 models**. Each row carries an
estimated cost per 100 requests, and the **Cost estimate** box below says what a
typical request might cost. They are estimates to help you compare, not
OpenAI's prices. With a key saved, the list fills as the window opens, so you
can change the model at any time with **Alt+F2**.

### What changes

Your text goes straight from this computer to OpenAI on your account, and
nothing passes through QUILL's servers. OpenAI bills your account for each
request. You do not need to connect this computer or accept the free service's
agreement. The five things AI help can do, and what comes back, are exactly the
same.

### Usage and About

**Usage** (**Ctrl+Alt+Shift+F9**) shows a different window with your own key:
the model answering, that no allowance applies, and **Open My OpenAI Usage**,
which opens your OpenAI account's usage page, where your requests and charges
are. **Help ▸ About** shows the model and that page instead of the free
allowance.

### Going back to the free service

**Remove the Saved Key**, in the same window. AI help is back on the free
service, with its free allowance, at once. There is no other switch to find:
while a key is saved it is used, and when it is gone it is not.

### Where the key is kept

In Windows' credential store, never in a settings file, and it is never shown
again once saved. A portable copy keeps it in an encrypted file. QUILL uses the
same key: saving or removing it in either program does it for both.

---

## Keys new in 1.1

| Key | What it does |
|---|---|
| **Ctrl+F11** | Dictation On (start or stop) |
| **Alt+Shift+F6** | Dictation Settings |
| **Alt+F2** | Use My Own OpenAI Key |

## Also in QUILL

Both features are in QUILL too, on the same keys: Live Dictation under Tools ▸
Speech, and Use My Own OpenAI Key in the AI menu.
