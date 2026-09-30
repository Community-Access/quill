# QUILL Lite 1.1 — What's New

Five things are new in 1.1, and the first is the one to read: AI help now runs
on the ChatGPT plan you already pay for, and with it comes the first time QUILL
Lite can describe a picture or look something up on the web.

- **[AI help on your ChatGPT subscription](#ai-help-on-your-chatgpt-subscription).**
  Press **Alt+F5**, choose Continue with ChatGPT, sign in once in your browser,
  and every AI command runs on your plan -- no key, no limits, no bill. Two
  things arrive with it that QUILL Lite has never had: **pictures, described**
  (**Ctrl+F5**) and **web search**, one checkbox away.
- **[Ten writing tools](#ten-writing-tools).** Shorten, Simplify, Make more
  formal, Make friendlier, Turn into a list, Find action items, Suggest
  headings, Continue writing, Write an email reply, and Translate into twenty
  languages -- all in the same AI pad.
- **[Conversations with AI help](#conversations-with-ai-help).** Talk back and
  forth, and each reply remembers what was said before -- free, inside your
  ordinary allowance, or without limit on your plan or your own key.
- **[AI help with your own OpenAI key](#ai-help-with-your-own-openai-key).**
  Paste a key and every limit on AI help is lifted.
- **[Dictation](#dictation).** Press **Ctrl+F11**, talk, and pause. What you
  said is written at the cursor with the punctuation put in for you, and QUILL
  Lite reads it back so you know it is right.

---

## AI help on your ChatGPT subscription

If you pay for ChatGPT, this is the release where QUILL Lite stops asking you
for anything else. Press **Alt+F5**, choose **Continue with ChatGPT**, sign in
the way you sign in to ChatGPT on the web, allow "QUILL Lite" to use your plan,
and come back. That is the whole of it. From then on the pad, the seventeen
writing tools, Ask About This Document and conversations run on your plan:
no monthly allowance, no size limit, no per-request bill, and nothing passing
through QUILL's servers.

### What it does that nothing else in QUILL Lite could

**Pictures, described.** Press **Ctrl+F5** -- **Ask About an Image** -- choose a
JPEG, PNG, WebP or GIF, and either ask a question or ask nothing. You hear a
description written for a blind reader: what the picture is, what matters most
in it, and every word of any text in it, transcribed exactly. A screenshot a
colleague sent with "see attached". The photo of a letter. A chart in a report.
A menu on a website. A receipt, and "what is the total". The answer opens in
an Image Description window; **Insert Below** puts it into your document under
the paragraph you are in, which is how you caption a picture in something you
are writing, and Ctrl+Z takes it back.

**Web search.** The model may look things up through OpenAI when a question
calls for it -- an event, a price, what a page says today -- in Ask a general
question, in a question about the document, and in conversations. It is off
until you turn it on, because a search is a second thing sent somewhere and
that is yours to allow. Turning it on takes four keystrokes:

1. Press **Alt+F5** (Tools ▸ AI ▸ Use My ChatGPT Subscription). You must be
   signed in; if you are not, press Continue with ChatGPT first.
2. Press **Alt+W**, or Tab to the **Allow web search** checkbox.
3. Press **Space** to check it. QUILL Lite says "Web search is allowed." It is
   saved at once; there is no OK.
4. Press **Escape** to close the window. Your next question may search.

Press Space on the same checkbox again to switch it off; QUILL Lite says "Web
search is off; only what you send is used."

### Dictation, corrected

**Tidy Dictated Text** (**Ctrl+F3**) is the one the dictation users asked for.
Leave the cursor in a paragraph you dictated, or select a stretch of it, press
the key, and the model corrects what the recogniser misheard -- sound-alike
words, a name it had never met, words run together, the comma that should have
been a full stop, every "um" -- and changes nothing else. The **Tidied
Dictation** window opens on the corrected text; **Replace My Selection** puts
it back where the dictated words were and **Ctrl+Z** takes it back as one step.
It runs on your ChatGPT subscription or your own OpenAI key, never on the free
allowance.

### How it is kept, and how it is undone

QUILL Lite registers itself with OpenAI when you first sign in -- there is no
secret hidden in the program -- and keeps only a refresh token, in Windows'
credential store, under its own name. Your ChatGPT password is never seen by
QUILL Lite. **Sign Out** (press it twice) asks OpenAI to revoke the sign-in and
forgets it here; **Forget on This Computer** forgets it here only. Neither
button exists until you are signed in. Each QUILL app -- QUILL Lite, QUILL,
Quill Radio -- signs in as itself and appears as itself under Apps in ChatGPT's
settings, so signing one out leaves the others as they were.

### The model, and the usage

The **Model** list is your plan's own, read from your account as you sign in;
the first is chosen for you and another is saved the moment you arrow to it.
What you use counts toward your plan's usage, which OpenAI enforces and shows
on ChatGPT's own usage page -- **Open ChatGPT Usage** takes you there -- and
when a limit is reached QUILL Lite says so in words. **Usage**
(Ctrl+Alt+Shift+F9) opens the account window on a plan, and **Help ▸ About**
names the account and the model.

### Beside your own key

A saved OpenAI key still works exactly as before. When both exist, the plan is
used, because it is already paid for where a key is billed per request; sign
out of ChatGPT and the key takes over again, at once.

## Ten writing tools

The AI pad (**Ctrl+Alt+G**) goes from seven choices to seventeen. The ten new
ones work on the same passage Summarize does -- your selection, else the
paragraph you are in, else the section -- and each is one request, the same
size as any other, so none of them costs more of your allowance than Summarize.
Press a letter in the list to jump to one.

| Choose | You get |
|---|---|
| **Shorten** | The same passage at about half the length, every important fact kept |
| **Simplify** | Plain, easy-to-read language: short sentences, everyday words, technical terms explained |
| **Make more formal** | The same meaning in a professional tone, for work or official letters |
| **Make friendlier** | The same meaning in a warmer tone, as if to someone you know |
| **Turn into a list** | A bulleted list, or numbered steps when the passage describes a process |
| **Find action items** | Every task, who does it and by when, and every date or deadline, one per line |
| **Suggest headings** | Headings that divide a long passage into sections you can jump between by heading, and where each goes |
| **Continue writing** | A next paragraph in the same voice, for you to keep, change or throw away |
| **Write an email reply** | Select an email you received; get a polite reply to edit, with decisions left in [square brackets] |
| **Translate** | The passage in the language you choose, from twenty, meaning and formatting kept |

A few that are worth knowing about:

- **Suggest headings** is about navigation: headings are what a screen reader
  jumps between, so this is how a long, flat passage becomes one you can move
  through by heading. It suggests; you place the ones you want.
- **Find action items** turns meeting notes or a long thread into the list of
  who does what by when -- and says so plainly when there is nothing to do.
- **Write an email reply** leaves anything only you can decide in [square
  brackets], so nothing is decided for you.
- **Translate** shows a **Translate into** list with twenty languages when you
  choose it; Spanish is chosen until you pick another.

Every result arrives in the answer window with **Replace My Selection**,
**Insert Below**, **Copy**, **Try Again** and **Follow Up** -- so "shorter
still" or "more formal than that" is one button away.

---

## Conversations with AI help

Until now, AI help answered one thing at a time: the next question never
remembered the last. Now you can talk it through.

### Starting one

- In the AI pad (**Ctrl+Alt+G**), choose **Have a conversation**, type your
  first message if you like, and press **Send**. The **AI Conversation**
  window opens.
- Or press **Follow Up** in any answer window to carry on from that answer.
  Following up a question about your document keeps sending the same passages,
  so you can keep asking about them.

### Talking

Focus stays in **Your message**. Type, press **Enter**, and the reply is read
aloud as it arrives and added to the **Conversation** above, which Shift+Tab
reaches for reading again word by word. **Copy Last Reply** and **Insert Last
Reply Below** put the latest reply where you want it -- nothing goes into your
document otherwise, and **Ctrl+Z** takes an insert back. **New Conversation**
starts fresh.

### It stays free

Each message is one request, with a monthly share of its own (40 of your 100).
The conversation so far goes with each message only as far as the ordinary
size limit allows, newest first -- so no message ever costs more than any other
request. The price of a very long conversation is that it gradually forgets
its beginning, and the window **says so the first time that happens**.

### With your own OpenAI key

No limit at all: the whole conversation goes with every message, straight to
OpenAI on your account. A long conversation therefore costs more per reply, and
the window says so. It is only shortened if it outgrows what the model can read
at once, and you are told if that happens.

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
agreement. The seventeen things AI help can do, and what comes back, are
exactly the same -- and a conversation has no limit at all (see *Conversations with AI
help*, above).

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

**My Words and Phrases** (Alt+Shift+F10, or the button in Dictation Settings)
is a window, not a file to edit. It lists everything dictation has been taught,
one line each, with Add Word, Add Phrase, Add Correction, Edit and Remove. A
**word** is a name spelled your way; a **phrase** is something you say that
writes something longer (*my email address*); a **correction** is what the
engine keeps hearing wrong and what to write instead (*quill light* becomes
*QUILL Lite*). Each change is saved the moment you make it and used by the next
phrase. The file behind it, `dictation.md`, is still plain text, and Open the
File opens it for anyone who prefers that.

### Escape cancels, and the microphone can drop

While a phrase is being heard, **Escape** throws it away and says "Cancelled";
nothing is written. If the microphone is unplugged or goes silent, dictation
pauses, says so, and resumes by itself when it is back. If the speech engine
stops answering it is restarted once without a word, and only a second failure
is reported, by name, with the engine to try instead.

### One Ctrl+Z per phrase, one session at a time

Every phrase is one undo step, even one that replaced a selection. Ctrl+F11 in a
second document while dictation runs in the first moves it there and says
"Dictation moved to" the document's name. A read-only document refuses before
the microphone opens.

### Dictate into any box

**Ctrl+F11** in the Find box, either Replace box, or the AI pad's question
dictates into that box, with the same engine and your own words. "New paragraph"
is a space there.

### Recent phrases

**Recent Phrases** (Shift+F11) lists the last twenty phrases of the session,
newest first; Enter writes one again at the cursor, Copy puts it on the
clipboard. The rescue for a "scratch that" that went one too far.

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

## Keys new in 1.1

| Key | What it does |
|---|---|
| **Ctrl+F11** | Dictation On (start or stop); in Find, Replace or the AI question box, dictate there |
| **Escape** | Throw away the phrase being heard |
| **Alt+Shift+F6** | Dictation Settings |
| **Shift+F11** | Recent Phrases |
| **Alt+Shift+F10** | My Words and Phrases |
| **Alt+F2** | Use My Own OpenAI Key |
| **Alt+F5** | Use My ChatGPT Subscription |
| **Ctrl+F5** | Ask About an Image |
| **Ctrl+F3** | Tidy Dictated Text |

## Also in QUILL

All five are in QUILL too, on the same keys: Live Dictation under Tools ▸
Speech, Use My Own OpenAI Key, Use My ChatGPT Subscription and Ask About an
Image in the AI menu, and the writing tools and Have a conversation in the same
AI pad, with Follow Up in the same answer window. Quill Radio has the sign-in
too, as its own agent, behind **Ask QUILL Radio**.
