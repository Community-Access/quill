# QUILL Lite 1.1

*Version 1.1.2, released September 30, 2026.*

Welcome to QUILL Lite 1.1. You can now write by talking, and AI help can run
on the ChatGPT plan you already pay for, which also lets QUILL Lite describe a
picture and look something up on the web for the first time.

There are ten new writing tools in the AI pad, and you can now have a real
back-and-forth conversation with AI help. Everything works from the keyboard
and tells you what happened, the way the rest of QUILL Lite does.

## About 1.1.1 and 1.1.2

**1.1.2** fixes the **Install and restart now** button. Before, it closed QUILL
Lite but never ran the installer. Now it installs and restarts as it should.
You need to update to 1.1.2 by hand once: in the update window, choose **Open
folder** and run the installer yourself. After that, the button works.

**1.1.1** was 1.1.0 with a new number. Some computers showed 1.1.0 in **Help
> About** but had no ChatGPT choices under **Tools > AI**, because files shared
by Quill Radio had given Check for Updates the wrong idea of which version you
had. The new number made sure everyone was offered the update.

## Try this first

1. Put the cursor where you want some words, press **Ctrl+F11**, and say a
   sentence. Pause, and QUILL Lite writes it and reads it back. Press
   **Ctrl+F11** again to stop.
2. If you pay for ChatGPT, press **Alt+F5**, choose **Continue with ChatGPT**,
   and sign in once in your browser.
3. Put the cursor in a long paragraph, press **Ctrl+Alt+G**, and choose
   **Shorten**. Press **Insert Below** if you like the result, or Escape if
   you do not.
4. Press **Ctrl+F5**, choose a photo or a screenshot, and hear what is in it.

## Dictating

The speech recognition comes with QUILL Lite. There is nothing to download and
no account to make. Nothing you say leaves your computer, and no recording is
kept anywhere.

### Getting started

1. Put the cursor where you want the words.
2. Press **Ctrl+F11**. You hear two rising tones and "Dictation on".
3. Talk the way you would talk to a person, then pause. Your sentence is
   written, a soft tone tells you it went in, and QUILL Lite reads it back.
4. Keep going. It keeps listening between sentences.
5. To stop, press **Ctrl+F11** again, or say "stop dictation".

You do not need to say punctuation. Full stops, commas, question marks and
capitals go in for you. If you want a particular mark, say it, and your word
wins.

### Fixing things by voice

Say these on their own, after a pause:

- **"scratch that"** takes out the last phrase. Say it again for the one
  before.
- **"select that"** selects the last phrase, so you can fix it with the
  keyboard.
- **"capitalize that"**, **"all caps that"** and **"no caps that"** change its
  capitals.
- **"delete word"** and **"delete sentence"** delete back from the cursor.
- **"undo that"** is the same as Ctrl+Z, and **"read that"** reads the last
  phrase again.
- **"go to end of line"**, **"go to top"** and others like them move the
  cursor.

To spell a name, say **"start spelling"**, then the letters, then **"stop
spelling"**. For example, "capital bravo alpha delta" writes *Bad*.

While dictating, say **"what can I say"** for a list of everything dictation
understands, including your own phrases. The same list is in the
documentation as **Dictation commands**.

### Starting and stopping with your voice

Turn on the **wake phrase** in Dictation Settings. Then say **"Quill
dictate"**, or a phrase of your own, to start without touching the keyboard.
It only listens while QUILL Lite is the window in front, and nothing it hears
is kept unless it starts with the wake phrase. It is off until you turn it on.

Say **"stop dictation"** on its own to stop, or choose your own **stop
phrase**. It only counts when it is all you said, so the same words in the
middle of a sentence are just written down.

### Talking in one long run

Turn on **Just write what I say** in Dictation Settings, and a pause does
nothing: no full stop, no tone, no read-back and no voice commands. Only the
punctuation you say, and your stop phrase, still work. It is good for thinking
out loud or telling a story without being interrupted.

### Your own words and phrases

**My Words and Phrases** (**Alt+Shift+F10**) lists everything you have taught
dictation, with Add Word, Add Phrase, Add Correction, Edit and Remove buttons.

- A **word** is a name, spelled your way.
- A **phrase** is something short you say that writes something longer, like
  *my email address*.
- A **correction** is something dictation keeps getting wrong, and what to
  write instead. For example, *quill light* becomes *QUILL Lite*.

Each change is used from your next phrase. If you would rather edit the list
as a plain text file, **Open the File** opens it.

### Tidying what you dictated

**Tidy Dictated Text** (**Ctrl+F3**) is the one dictation users asked for.
Leave the cursor in a paragraph you dictated, or select part of it, and press
**Ctrl+F3**. AI help fixes what dictation got wrong: words that sound alike, a
name it had never heard, words run together, a comma that should have been a
full stop, and every "um". It changes nothing else.

The **Tidied Dictation** window opens on the corrected text. **Replace My
Selection** puts it in place, and **Ctrl+Z** takes it back in one step. This
works on your ChatGPT plan or your own OpenAI key, not the free allowance.

### When something goes wrong

- Press **Escape** while a phrase is being heard to throw it away. You hear
  "Cancelled" and nothing is written.
- If the microphone is unplugged or goes quiet, dictation pauses, tells you,
  and starts again by itself when the microphone is back.
- If dictation stops answering, QUILL Lite quietly restarts it once. Only if
  that fails too are you told, with which engine to try instead.
- **Recent Phrases** (**Shift+F11**) lists the last twenty phrases. Press
  Enter on one to write it again, which is how you get a phrase back when
  "scratch that" went one too far.

### More you can do

- **Every phrase is one Ctrl+Z**, even one that replaced a selection.
- **One document at a time.** Press Ctrl+F11 in another document and dictation
  moves there and tells you.
- **A read-only document says no** before the microphone even opens.
- **Dictate into a box.** Press **Ctrl+F11** in the Find box, either Replace
  box, or the AI pad's question box, and you dictate into that box.
- **The status bar has a Dictation part**, which tells you whether dictation is
  off, listening, hearing you, writing, spelling or waiting for the wake
  phrase. **Tools > Dictation > Dictation On** is checked while it is on.

### Dictation Settings

Open **Tools > Dictation > Dictation Settings** (**Alt+Shift+F6**).

- **Speech engine.** **Moonshine** is the one you start with, and it is fast
  even on a modest computer. **Whisper** is a little slower; try it if
  Moonshine often mishears you. Both understand English. **Windows speech
  recognition** can use any speech language installed in Windows, but you say
  the punctuation yourself. **Windows voice typing** hands over to Windows+H.
- **Microphone.** Choose yours by name, or use the Windows default.
- **What you hear** after each phrase: a sound, the words read back, both, or
  neither. If the read-back plays through speakers, the microphone can hear it
  too, so use headphones or choose just the sound.
- **Automatic punctuation** on or off, how long a **pause** ends a phrase,
  **remove filler words** like um and uh, and **stop after silence**.
- **Test Microphone** listens for four seconds and tells you how loud you were
  and what it heard.

## AI help on your ChatGPT plan

If you pay for ChatGPT, QUILL Lite no longer needs anything else from you.

1. Press **Alt+F5** (**Tools > AI > Use My ChatGPT Subscription**).
2. Choose **Continue with ChatGPT**.
3. Sign in the way you sign in to ChatGPT on the web.
4. Allow "QUILL Lite" to use your plan, and come back.

From then on, the AI pad, all the writing tools, Ask About This Document and
conversations run on your plan. There is no key to paste, no free allowance to
count, no size limit from us, and no bill per request. Nothing passes through
our servers.

### Pictures, described

Press **Ctrl+F5** for **Ask About an Image**. Choose a JPEG, PNG, WebP or GIF.
Ask a question about it, or ask nothing at all. You hear a description written
for a blind reader: what the picture is, what matters most in it, and every
word of any text in it, written out exactly.

Some things to try:

- a screenshot a colleague sent with "see attached",
- a photo of a letter,
- a chart in a report,
- a receipt, asking "what is the total".

**Insert Below** puts the description in your document under the paragraph
you are in, which is handy for captioning a picture. **Ctrl+Z** takes it back
out.

### Web search

When a question needs it, AI help can look things up for you: an event, a
price, what a web page says today. This works when you ask a general question,
a question about your document, and in conversations.

It is off until you turn it on, because a search sends something to one more
place, and that is your call:

1. Press **Alt+F5**. Sign in first if you have not.
2. Press **Alt+W** to reach **Allow web search**.
3. Press **Space**. You hear "Web search is allowed." It is saved straight
   away.
4. Press **Escape** to close the window.

To turn it off, press Space on the same checkbox. You hear "Web search is off;
only what you send is used."

### Your model, your usage, and signing out

The **Model** list comes from your own plan, and the first one is chosen for
you. What you use counts toward your plan's own usage, which OpenAI sets.
**Open ChatGPT Usage** takes you to it, and if you reach a limit, QUILL Lite
tells you in plain words. **Usage** (**Ctrl+Alt+Shift+F9**) shows your
account, and **Help > About** names the account and the model.

QUILL Lite never sees your ChatGPT password. **Sign Out** (press it twice)
signs you out with OpenAI and on this computer. **Forget on This Computer**
forgets the sign-in here only. QUILL Lite, QUILL and Quill Radio each sign in
on their own, so signing one out leaves the others alone.

If you also have your own OpenAI key saved, your plan is used, since you have
already paid for it. Sign out and your key takes over again straight away.

## Ten new writing tools

The AI pad (**Ctrl+Alt+G**) now has seventeen choices instead of seven. The
new ones work on your selection if you have one, otherwise the paragraph you
are in. Each counts as one request, the same as Summarize. Press a letter in
the list to jump to a choice.

- **Shorten**: the same passage at about half the length, with every
  important fact kept.
- **Simplify**: short sentences, everyday words, and technical terms
  explained.
- **Make more formal**: the same meaning in a professional tone.
- **Make friendlier**: the same meaning in a warmer tone.
- **Turn into a list**: a bulleted list, or numbered steps for a process.
- **Find action items**: every task, who does it and by when, one per line. If
  there is nothing to do, it says so.
- **Suggest headings**: headings for a long passage, and where each one goes,
  so your screen reader can jump between sections. You place the ones you
  want.
- **Continue writing**: a next paragraph in the same voice, to keep, change or
  throw away.
- **Write an email reply**: select an email and get a polite reply, with
  anything only you can decide left in [square brackets].
- **Translate**: into one of twenty languages, with the meaning and formatting
  kept. Spanish is chosen until you pick another.

Every result opens with **Replace My Selection**, **Insert Below**, **Copy**,
**Try Again** and **Follow Up**. So if you want it "shorter still", it is one
button away.

## Conversations with AI help

Until now, AI help answered one question at a time. Now you can talk it
through.

- In the AI pad (**Ctrl+Alt+G**), choose **Have a conversation**, type your
  first message if you like, and press **Send**.
- Or press **Follow Up** in any answer window to carry on from that answer.

Your focus stays in **Your message**. Type, and press **Enter**. The reply is
read aloud as it arrives and added to the **Conversation** box above. Press
Shift+Tab to read it again word by word.

Nothing goes into your document unless you ask. **Copy Last Reply** and
**Insert Last Reply Below** put the latest reply where you want it, and
**Ctrl+Z** takes an insert back out. **New Conversation** starts again.

On the free service, each message is one request, and conversations can use up
to 40 of your 100 a month. A very long conversation slowly forgets how it
began, and the window tells you the first time that happens. With your own key
or your ChatGPT plan, there is no such limit. With your own key, the whole
conversation goes with every message, so a long one costs more per reply, and
the window tells you so.

## AI help with your own OpenAI key

Choose **Tools > AI > Use My Own OpenAI Key** (**Alt+F2**), paste an OpenAI
key, and press OK. Every limit on AI help is gone. Your text goes straight
from this computer to OpenAI, on your account, and OpenAI bills you for each
request.

- The **Model** list shows every model your account can use, with Luna 6
  first. Each row shows an estimated cost per 100 requests, to help you
  compare. They are estimates, not OpenAI's prices.
- **Usage** (**Ctrl+Alt+Shift+F9**) names the model and opens your OpenAI
  usage page.
- **Remove the Saved Key** goes back to the free service straight away.
- Your key is kept safely by Windows, never in a settings file, and never
  shown again. A portable copy keeps it in an encrypted file. QUILL uses the
  same key, so saving or removing it in one does it for both.

## Keys new in 1.1

| Key | What it does |
|---|---|
| **Ctrl+F11** | Start or stop dictation |
| **Alt+Shift+F6** | Dictation Settings |
| **Shift+F11** | Recent Phrases |
| **Alt+Shift+F10** | My Words and Phrases |
| **Ctrl+F3** | Tidy Dictated Text |
| **Alt+F5** | Use My ChatGPT Subscription |
| **Ctrl+F5** | Ask About an Image |
| **Alt+F2** | Use My Own OpenAI Key |

All of these are in QUILL too, on the same keys. Quill Radio has the ChatGPT
sign-in as well, behind Ask QUILL Radio.

## Coming next, in 1.2.0

These are on their way in the next release.

### Words: a thesaurus, a dictionary and Look Up

- **Thesaurus** (**Shift+F7**) finds the word you are really on, so "running"
  finds "run", and puts your choice back in the form your sentence needs.
- Press the Applications key on any word for two new submenus, **Thesaurus
  for** that word and **Dictionary for** that word.
- **Look Up Word** (**Alt+F10**) works offline. Check **Use online sources** for
  definitions and a short Wikipedia summary too; only the word is sent, and
  only after you check the box. **Add to Dictionary** teaches the word to your
  spell checker.
- **Tools > Dictionary** asks AI help about a word as it is used in your
  sentence: define it, synonyms that fit, a simpler, more formal or more vivid
  word, opposites, is this the right word, use it in a sentence, where it
  comes from, how to say it, rhymes, or the **Word Explorer**, which does them
  all. **Find the Word For** suggests the word you are reaching for from a
  description. **Use This Word** puts your choice in as one step you can undo.
  These need your ChatGPT plan or your own key.
- **Dictionary Status**, under **Tools > Spelling**, tells you how many words
  your dictionaries hold and where they are kept.

### Your own key can be a Google Gemini key

**Use My Own AI Key** (Alt+F2), the new name for Use My Own OpenAI Key, opens
on a **Provider** list: OpenAI or Google Gemini. Everything follows your
choice, and QUILL Lite never guesses. Ask About an Image works with Gemini too.

### Knowing what happened

**Help > Activity** (**Shift+F9**) lists everything QUILL Lite told you since
you opened it, newest first, with what you can do about each one: Retry, Open
Folder or Copy Details. If background work finishes after you closed its
window, the result lands here instead of being lost. **F9** says the last
important result again. The same keys work in QUILL, Quill Radio and QUILL
Cast.

### Things that will work better

- **Coming back with Alt+Tab** puts your focus where it should be, even when
  Windows is slow. It leaves Find boxes and menus alone.
- **If your settings cannot be saved, you are told**, with the reason. Your
  choices still work for the rest of the session, a message stays in the
  status bar, and Preferences no longer says "saved" when it was not.
- **Big files and network drives no longer freeze the window.** You hear
  "Opening" and the file's name, and closing the window cancels it.
- **Closing QUILL Lite is tidier.** Documents sent to it while it closes are
  opened next time, an update check never starts on the way out, and an error
  message some people saw while exiting is gone.
- **Two copies at once** no longer undo each other's preferences.

## Where to learn more

The QUILL Lite User Guide, in the Start menu beside QUILL Lite, has chapters
on everything here, including Dictation, AI help, Thesaurus, Dictionary, Activity and Repeat Last
Result, and Keeping QUILL Lite up to date.

**Help > Tutorials** (**Ctrl+Alt+F1**) has nine short lessons. For AI help,
try Asking a question about a document.

If you get stuck, choose **Help > Get Help from Support** (**Ctrl+Alt+F2**),
or write to support@community-access.org. A person at Community Access reads
every message.
