# Chapter 9: Writing by voice

Dictation lets you write by talking. Press **Ctrl+F11**, say a sentence, and
pause. When you pause, your words appear in the document at the cursor. You
hear a short, soft tone, and QUILL Lite reads the words back so you know they
came out right. Then it keeps listening, so you can go straight on to the next
sentence. To stop, press **Ctrl+F11** again or say "stop dictation". If you
would rather hold **Ctrl+F11** down while you talk and let go to stop, you can
turn that on; see Holding Ctrl+F11 to talk, below.

You do not have to say punctuation. The speech engines that come with QUILL
Lite put in full stops, commas, question marks and capital letters for you.
When you want a particular mark, just say it, like "comma" or "new paragraph".
What you say always wins.

It all happens on your own computer. Nothing is downloaded, nothing you say is
sent anywhere, and no recording is kept. Your words are recognised, written
into your document, and then forgotten. (If you have your own OpenAI key, or
your own account with one of twelve speech companies, you can choose to have
that company recognise your speech instead. That is off unless you turn it on,
and "OpenAI dictation, with your own key" and "Speech providers: dictation
with your own account" explain exactly what is sent. Larger speech models you
can download stay on your computer too; "Which engine should I choose?" helps
you decide.)

This chapter starts with your first dictation. Then it covers what you can
say, starting and stopping with your voice, making dictation fit you, talking
to the AI, writing down a whole meeting as it happens, dictating into other
programs, turning a recording into text, and what to do when something goes
wrong. Near the end, "Dictating well" gathers the habits that make the
biggest difference, with two short paragraphs to practise on.

## Getting started

### Your first dictation, step by step

1. Put the cursor where you want the words to go. If you select some text
   first, the first thing you say replaces it.
2. Press **Ctrl+F11**. The first time after you open QUILL Lite, it takes a
   second or two to get ready. Then you hear two rising tones and "Dictation
   on".
3. Say a sentence the way you would say it to a friend, and pause.
4. A moment later the sentence is in your document. You hear the soft tone,
   and the words are read back to you.
5. Keep going. You do not need to press anything between sentences.
6. When you are finished, press **Ctrl+F11** or say "stop dictation". You hear
   two falling tones and "Dictation off".

Your words are written once you have been quiet for a little under a second.
That means taking a breath in the middle of a sentence will not cut it in two.
If a pause does split a sentence, and the next part starts with a word like
*and*, *but*, *which* or *to*, QUILL Lite takes out the full stop the pause put
in, and the sentence carries on. The same happens when the first part *ends*
on a word no sentence ends on, like *the* or *very*. If you often stop to
think, you can make the pause longer too; see "Longer pauses, and sentences
you finish later" below.

### Holding Ctrl+F11 to talk

Press **Ctrl+F11** to start dictating and press it again to stop. That is
all most people ever need, and it is how dictation starts out.

If you prefer to hold the key while you talk, like the button on a
walkie-talkie, turn on **Hold the dictation key to talk; a quick press still
turns it on and off** in **More Dictation Settings**. Then:

1. Put the cursor where you want the words.
2. Press and hold **Ctrl+F11**. You hear the two rising tones and "Dictation
   on" straight away.
3. Keep holding the keys, and say what you want to say.
4. Let go. Dictation writes your last phrase, then you hear the two falling
   tones and "Dictation off".

With that turned on, a quick press still works just the same: dictation turns
on and stays on until you press Ctrl+F11 again. QUILL Lite tells the two apart by
how long you hold the keys. Half a second or more is a hold.

Stopping never cuts you off. If you press or let go of Ctrl+F11 while you are
still finishing a sentence, dictation waits for that phrase, writes it, and
then stops.

### What you hear

| When | Tones | Words |
|---|---|---|
| Dictation starts | two rising tones | "Dictation on" |
| A phrase is written | one short, soft tone | the words that were written |
| Dictation stops | two falling tones | "Dictation off" |
| Something goes wrong | a low double tone | what happened, and what to do |
| A phrase takes more than a second (only if you turn it on) | a soft tick once a second | "Still working on that phrase", once a session, after four seconds |

You can change any of these in **Dictation Settings**, and you can change or
silence any tone in **Tools > Sound Scheme**. Two things always speak, though:
a problem, and the answer to a command you gave.

**The tick while a phrase is worked on.** With a large model there can be a few
seconds between your pause and the text. Check **Tick while a phrase is being
worked on** (**Alt+R**) in **More Dictation Settings** and a soft tick plays
once a second while you wait, from the first second until the text arrives or
recognition fails. The first time in a session that a phrase takes four
seconds, you also hear "Still working on that phrase." While a tick plays, the
microphone is not listened to for a moment, as with every QUILL Lite sound, so
the tick is never written as speech. If your sound scheme has no tick sound, you
hear the sentence at four seconds instead, each time. "After each phrase is
written, give me" decides it too: set to nothing, there is no tick and no
sentence; set to words only, there is no tick, and the sentence is said each
time a phrase takes four seconds. It starts unchecked in QUILL Lite and QUILL,
and checked in QUILL Transcribe.

The soft tone plays only once your words are really in the document, so when
you hear it, you know they arrived. If you have the words read back, they come
a quarter of a second after they are written, so your screen reader does not
talk over them.

#### Hearing the punctuation that went in

When your words are read back, the punctuation is read too, by the same names
you would use to dictate it. If you say "hello comma world period", you hear
"Hello comma world period" back, and you know the comma really went in. A
sentence that ends in a question mark ends with "question mark", a quotation
starts with "open quote", and a new paragraph is read as "new paragraph". This
happens whatever punctuation level your screen reader is set to, so a full
stop the engine put in for you is never silently missing or silently there.

A few things stay quiet because they are part of a word or a number. The
apostrophe in *don't*, the hyphen in *well-known*, and the full stop or comma
inside *3.5* or *1,000* are not read out. A web address is read the way you
would say it: *example.com* is "example dot com". When you dictate in Spanish,
the marks are read with their Spanish names, like "coma" and "punto".

Only the read-back says the names. The status bar and a braille display show
the real characters, for example "Dictated: Hello, world." If you would rather
hear the words alone, open **More Dictation Settings** and uncheck **Say
punctuation marks in the read-back** (**Alt+S**). It starts checked.

**Use headphones if you have the read-back on.** Through speakers, the
microphone can hear the read-back and write it down a second time. If you use
speakers, set "After each phrase is written, give me" to a sound only.

### Choosing a speech engine

You choose the engine in **Dictation Settings** (**Alt+Shift+F6**), in the
**Speech engine** list, which has the focus when the window opens. Arrow to
one and press Enter. The first two come with QUILL Lite, inside the program
itself, so dictation works the moment you install, with nothing to download.

| Engine | What it is like |
|---|---|
| **Moonshine** (the one it starts with) | Built in. Quick even on a modest computer, and puts in punctuation for you. For most voices it is the most accurate of the built-in engines. English only: when the dictation language is Spanish, the built-in Whisper does the listening instead. |
| **Whisper** | Built in. Also puts in punctuation for you, and is a little slower. Try it if Moonshine often mishears your voice or your microphone. English and Spanish. |
| **Windows speech recognition** | Windows' own recogniser. It does not add punctuation, so you say every mark, and it often mishears a voice it has not been trained on. It can use any speech language you have installed in Windows. |
| **Windows voice typing (Windows+H)** | Hands you over to Windows' own voice typing panel. Windows does the listening and the typing, so the commands, tones, read-back and wake phrase in this chapter do not apply. |
| **A model you downloaded** | Listed with "(downloaded)" and its tier after the name, once you download it in **Better Accuracy: Speech Models...** (**Alt+B**). Stays on your computer. See "Better accuracy: optional speech models". |
| **OpenAI** (only with your own key) | OpenAI recognises your speech, so it is sent over the internet. Listed only when an OpenAI key is saved, and off unless you choose it; see "OpenAI dictation, with your own key". |
| **A speech provider** (only with your own account) | One of twelve speech companies you already have an account with, once you set it up in **Speech Providers...** (**Alt+V**). Your speech is sent to that company. See "Speech providers: dictation with your own account". |

Every engine puts in punctuation for you except Windows speech recognition.
Each model in the list also says its tier, for example "Moonshine (fast,
punctuates for you), Lightweight". The tiers are explained in the next
section.

### Which engine should I choose?

The short answer: **start with Moonshine, and change only if you have a
reason.** It needs nothing downloaded, it is the quickest, it is kind to your
screen reader, and your voice never leaves the computer. Here is how to think
about the rest.

**What matters to you?**

- **Privacy and working offline.** Moonshine, Whisper, Windows speech
  recognition and every downloaded model work with no internet connection,
  and nothing you say leaves your computer. OpenAI and the speech providers
  send your speech to a company over the internet, so they need a connection,
  and they ask before the first word is sent.
- **Speed.** Moonshine writes your words about a fifth of a second after you
  pause, using very little of the processor. Whisper takes a little longer.
  The large downloads can take a second or more after each pause.
- **Accuracy.** In our tests with real recordings, the built-in Moonshine got
  6.5 percent of words wrong on audiobooks no model had been trained on, and
  NVIDIA Parakeet Unified 0.6B, a free download, got 3.2 percent: about half
  the mistakes. A downloaded model also copes better with accents, fast speech,
  a noisy room, names and long sentences. OpenAI and most speech providers are
  very accurate too, but cost money and send your speech away.
- **Memory and an older computer.** In the same tests, Moonshine used at most
  584 MB of memory, Parakeet Unified 1.2 GB and Nemotron 1.5 GB. On a
  computer with 8 GB, dictation may take up to 1.6 GB beside your screen
  reader; on 4 GB, only the built-in engines and Moonshine base fit.
- **Spanish.** Moonshine only knows English. In Spanish, the built-in Whisper
  is used, and it got about one word in four wrong on real Spanish speech.
  NVIDIA Parakeet TDT 0.6B v3 got 4.4 percent wrong on the same recordings, so
  if you dictate a lot of Spanish and have 8 GB of memory, it is well worth
  the download.

**What the tiers mean.** Every model is labelled with one of three tiers,
wherever you choose one:

- **Lightweight**: keeps up comfortably even on a modest computer. The
  built-in Moonshine and Whisper, Moonshine base, both Parakeet models and
  Whisper base.en.
- **Balanced**: more work than the built-in engines; keeps up on a computer
  with four or more cores. Nemotron and Whisper base.
- **High accuracy**: the fewest mistakes, for the most work; needs a capable
  computer, or patience.

**Let QUILL Lite recommend one.** Dictation Settings has a read-only line,
**Recommended for this computer**, at the top of the right-hand column. Tab
to it to hear which model suits this computer and your dictation language, and
why. For more, press **Better Accuracy: Speech Models...** (**Alt+B**): the
**Recommendation** box (**Alt+C**) explains the choice, **What matters most**
(**Alt+W**) changes it to a balance of speed and accuracy, the quickest
response, or the fewest mistakes, **Show Recommended Model** (**Alt+S**)
moves to that model in the list so you can download it, and **Switch to
Recommended Model** (**Alt+H**) chooses it once it is downloaded; press **OK**
in Dictation Settings to keep it. The recommendation is
only advice: QUILL Lite never changes your engine for you, and it never
recommends OpenAI or a speech provider. Its
figures come from our tests with real recordings, on one computer; yours may
differ. "How we chose: tested on real speech", in
"Better accuracy: optional speech models", has the numbers.

What it suggests depends on the computer, and on how much memory is free when
you ask: it never suggests more than is free, less half a gigabyte kept back
for your screen reader. If little memory is free, it names the built-in
engine. Some examples, for a balance and for the quickest response:

| This computer | A balance | The quickest |
|---|---|---|
| 4 GB of memory, 2 cores | Moonshine | Moonshine |
| 8 GB, 2 cores | Parakeet TDT 0.6B v3 | Moonshine |
| 8 GB or more, 4 cores | Parakeet Unified 0.6B | Moonshine |
| 4 GB, dictating in Spanish | Whisper | Whisper |
| 8 GB, dictating in Spanish | Parakeet TDT 0.6B v3 | Whisper |

**A worked example.** Maria has a laptop with 16 GB of memory and 8 cores. She
dictates long emails, and Moonshine keeps writing "Siobhan" and "Dún
Laoghaire" wrong.

1. She adds both names to **My Words and Phrases** (**Alt+Shift+F10**). That
   alone fixes many names, with any engine.
2. She opens **Dictation Settings** (**Alt+Shift+F6**) and Tabs to
   **Recommended for this computer**. It says something like "NVIDIA Parakeet
   Unified 0.6B, Lightweight: keeps up on this computer's 16 GB and 8 cores,
   about 1.2 seconds after you pause; stays on this computer; a 663 MB
   download."
3. She presses **Better Accuracy: Speech Models...** (**Alt+B**), then **Show
   Recommended Model** (**Alt+S**), then **Download...** (**Alt+D**), and
   answers Yes to the question that names the size and the licence.
4. When she hears that it is downloaded, she presses **Use for Dictation**
   (**Alt+U**), then **OK** in Dictation Settings.
5. She dictates for a day. Each phrase is written when she pauses, with about
   half the mistakes Moonshine made. If her screen reader feels slow, she goes
   back to Moonshine in the Speech engine list; the download stays, ready for
   next time. If she would rather follow her words on braille while she talks,
   she can try Nemotron instead (see "Nemotron or Parakeet: which should I try?").

If Maria had a two-core laptop with 4 GB of memory, the advice would have been
to stay with Moonshine, and perhaps try Moonshine base, a 141 MB download.

**To switch engine at any time,** open Dictation Settings, choose another in
**Speech engine**, and press **OK**. Dictation Status (**Alt+F9**) tells you
which engine and language you are using.

### Speech providers: dictation with your own account

If you already have an account with a speech company, QUILL Lite's dictation
can use it. There are twelve: Microsoft Azure AI Speech, Google Cloud
Speech-to-Text (Chirp 3), Amazon Transcribe, Deepgram, AssemblyAI,
Speechmatics, ElevenLabs Scribe, Gladia, Rev.ai, Groq, Mistral Voxtral and IBM
Watson Speech to Text. The built-in engines stay the default and the
recommendation, and never send anything anywhere. None of this is needed, and
none of it is on until you choose it.

**What is sent.** With one of these chosen as the speech engine, each phrase
dictation hears is sent over an encrypted connection to that company, with
your account, and the words come back. Nothing is sent while nobody is
speaking. Where the company can take a list of words to expect, the newest
names and terms from **My Words and Phrases** go with it, up to that company's
limit, so it spells them your way. Nothing goes through QUILL's servers, and
QUILL Lite keeps no copy of your voice. The company's own policies apply to
what it receives. The company bills you, not QUILL; QUILL Lite shows no prices
and counts nothing, so look at your provider's own usage page. None of it works
in Safe Mode.

**Setting one up, step by step:**

1. Open **Dictation Settings** (**Alt+Shift+F6**) and press **Speech
   Providers...** (**Alt+V**). The focus is on the **Providers** list.
2. Arrow to the company. **About this provider** says whether it shows your
   words while you speak, whether it learns your words from My Words and
   Phrases (and how many), where your speech goes, and its usage page.
3. Tab to its fields and fill them in: usually a key, sometimes a region, a
   project or an address. Press **F1** on a field to hear where that company's
   console shows it. A key is never shown again once saved; leaving a key field
   empty keeps the one already saved.
4. Press **Test Connection** (**Alt+T**). QUILL Lite asks the company about
   your account, never with your speech, and says what it answered, such as
   "Azure answered: ready, region westeurope." If something is wrong it says
   which field, such as "The key was refused. Check Key.", and puts you there.
   **Last result** keeps what it said, so you can read it again.
5. Press the Save button (Alt+S). Keys go to **Windows Credential Manager** at
   once, and are never written in QUILL Lite's settings or logs. The other
   details, such as a region, are kept when you press OK in Dictation Settings.
6. Close the page. The company is now in the **Speech engine** list, as, for
   example, "Deepgram (your own account; sends your speech to Deepgram)".
   Choose it, and a question says exactly what will be sent and to whom.
   **No** is the default: if you just press Enter, nothing is sent and you keep
   the engine you had. Choose **Yes** to agree.
7. Press **OK** in Dictation Settings, then **Ctrl+F11**, and talk.

**Remove** (**Alt+M**) forgets everything saved for that company, keys
included. To stop sending your speech, choose another engine in Dictation
Settings.

**Which ones show words while you speak.** Azure, Amazon, Deepgram,
AssemblyAI, Speechmatics, ElevenLabs, Gladia, Rev.ai and IBM Watson show the
words heard so far in the status bar and on braille. Google, Groq and Mistral
send each phrase when you pause, so with them nothing appears until you stop.

**If the connection goes.** A lost phrase is said in one sentence, for example
"Groq could not be reached. Check the internet connection.", and dictation
keeps listening. A refused key or an account with no credit left stops
dictation and says so. QUILL Lite never switches to another engine by itself.

**Limits for now.** The providers are for dictating as you talk: Transcribe a
Recording offers your computer's models and OpenAI, not these. They have not
yet been tried against every company's live accounts, so if one does not
behave, tell us with **Help > Get Help from Support**. Your agreement to each
company is kept by QUILL Lite alone, even when you share dictation settings
with the family.

### The dictation keys

Everything here is also on **Tools > Dictation**, so you can find it by
walking the menu too.

| Key | Command |
|---|---|
| **Ctrl+F11** | Dictation On (press again to stop) |
| **Alt+Shift+F6** | Dictation Settings... |
| **Shift+F11** | Recent Phrases... |
| **Alt+Shift+F10** | My Words and Phrases... |
| **Shift+F5** | Transcribe a Recording... |
| **Ctrl+Shift+F11** | Switch Dictation Language |
| **Ctrl+Alt+Shift+PageDown** | Start or Stop Live Transcript |
| **Ctrl+Alt+Shift+PageUp** | Dictation Context for This Document... |
| **Alt+F9** | Dictation Status |
| **Ctrl+Alt+Shift+Q** | Next Phrase Is a Dictation Command (the next thing you say is a command; twice, command mode) |
| **Shift+F4** | Review Dictation... (read, change and insert the last phrase once) |
| **Ctrl+F3** | Tidy Dictated Text... (in Tools > AI) |

## Saying things

### Punctuation and layout

You can say these anywhere in a sentence:

- **Punctuation:** "period" or "full stop", "comma", "question mark",
  "exclamation point", "colon", "semicolon", "ellipsis", "apostrophe", "open
  quote" and "close quote", "open single quote" and "close single quote".
- **Brackets:** "open parenthesis" and "close parenthesis", "open bracket" and
  "close bracket", "open brace" and "close brace".
- **Joining:** "hyphen", "dash", "slash", "backslash", "underscore".
- **Symbols:** "at sign", "hash sign", "dollar sign", "percent sign",
  "ampersand", "asterisk", "plus sign", "minus sign", "equals sign".
- **Layout:** "new line" ends the line, "new paragraph" leaves a blank line,
  and "tab" or "tab key" types a tab.

QUILL Lite puts the spaces where they belong. There is no space before a
comma, one after a full stop, and none at the start of a line. The first word
of each sentence gets its capital letter. You decide what "dash" writes in
Dictation Settings: an em dash, a spaced en dash, or two hyphens.

Sometimes you want the word itself. Say **"literal"** first: "literal new line"
writes *new line*, and "literal comma" writes *comma*.

There are more marks for Markdown and code, like "backtick", "tilde" and
"vertical bar", and words that start a heading or a list item. They are in
"Letters, numbers and symbols", a little further on.

### Commands

A command works only when it is **the whole phrase**, said on its own after a
pause. If you say "delete that line of text" in the middle of a longer
sentence, it is just written as words.

**Fixing what you just said:**

| Say | What happens |
|---|---|
| "scratch that" or "delete that" | Removes the phrase you dictated last. Say it again to remove the one before. |
| "undo that" or "undo" | The same as Ctrl+Z. |
| "select that" | Selects the last phrase, so you can fix it with the keyboard. The next phrase you say replaces it. |
| "capitalize that" | Gives every word of the last phrase a capital. |
| "all caps that" | Puts the last phrase in capitals. |
| "no caps that" | Puts the last phrase in small letters. |
| "delete word" | Deletes the word before the cursor. |
| "delete sentence" | Deletes the sentence the cursor is at the end of. |
| "delete previous paragraph" | Deletes the paragraph just before the cursor. |
| "replace" the words "with" the new words | Puts the new words in place of the nearest old ones: "replace Tuesday with Wednesday". |
| "change that to" and the new words | Puts the new words in place of the phrase you dictated last. |
| "read that" or "repeat that" | Reads aloud again all of what last went in: a phrase, a whole snippet or clip, or reviewed words. |
| "read last sentence" | Reads the sentence just before the cursor, with its punctuation said. |
| "read last paragraph" or "read this paragraph" | Reads the paragraph the cursor is in. |
| "read selection" | Reads what is selected. |
| "spell that" | Selects the last phrase, and the next thing you say is spelled out letter by letter to replace it. |
| "copy that" | Copies the last phrase to the clipboard. |

**Checking your work by ear.** Say "read last sentence", "read last
paragraph" or "read selection" as a phrase on its own, and QUILL Lite reads that
part of your document aloud with every mark named when **Say punctuation marks
in the read-back** (More Dictation Settings) is on, whatever your screen
reader's punctuation level. For example, after you dictate "First idea. Can
you send it, please?" and pause:

- "read last sentence" says "Can you send it comma please question mark".
- "read last paragraph" says "First idea period Can you send it comma please
  question mark".
- Select "send it" with Shift and the arrow keys, then say "read selection":
  you hear "send it".

Nothing in your document changes and the cursor stays where it was, so a
read-only document can be read back too. If there is nothing to read you hear
"There is no sentence here." (or paragraph), or "Nothing is selected." In
Spanish, say "lee la última frase", "lee el último párrafo" or "lee la
selección"; "leer" works as well as "lee". In another program only "read that"
works, because dictation reads only the words it typed there.

**Moving the cursor:** "go to beginning of line", "go to end of line", "go to
top", "go to end of document", "go to start of paragraph" and "go to end of
paragraph". You can also go to, select or correct any words you can see in
your document; see "Moving and selecting by voice".

**Capitals and spaces:** "caps on" and "caps off", "all caps on" and "all caps
off", "no space on" and "no space off". See "Letters, numbers and symbols".

**Copying, clips and snippets:** "copy all", "show clips", "show snippets",
"paste clip three", "insert snippet" and a name. See "Snippets and clips by
voice".

**Dictation itself:** "start spelling" and "stop spelling" (see "Spelling a
word"), "switch to Spanish" (see "Switching between English and Spanish"),
"dictation context" and a name (see "Dictation Context for This Document"),
"what can I say" (opens the full list), and "stop dictation".

The commands that change your last phrase only work while it is still exactly
as it was written. If you have typed into it since, QUILL Lite leaves it alone
and tells you, so your own typing is never changed by mistake.

### Correct that: choosing another guess

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
(**Shift+F11**, **Tools > Dictation > Recent Phrases...**) marked "(before correction)", just after the corrected
words, so you can put it back with Insert Again or copy it.

To fix a word further back, say **"correct"** and the word itself, like
"correct Ann". The word is selected, and what you say next takes its place.
"Moving and selecting by voice" explains how.

### Replace and change that: fixing words without retyping them

Two commands put new words in place of old ones, so you do not have to
select anything first. Say each one at the start of a phrase.

**"replace" the words "with" the new words.** Say "replace Tuesday with
Wednesday" and the nearest "Tuesday" before the cursor becomes "Wednesday";
if there is none before the cursor, QUILL Lite looks after it. The new words take
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

### Spelling a word

Some names the engine will never get right. For those, say **"start
spelling"**. Until you say **"stop spelling"**, everything you say is written
as letters:

- Say letters by name, like "bee" or "see". The phonetic alphabet works much
  better, though: alpha, bravo, charlie, delta, echo, foxtrot, golf, hotel,
  india, juliet, kilo, lima, mike, november, oscar, papa, quebec, romeo,
  sierra, tango, uniform, victor, whiskey, x-ray, yankee, zulu.
- Say "capital" before a letter for a capital, and "space" for a space.
- Numbers are written as digits: "one", "two" and so on.

For example, say "start spelling", then "capital bravo alpha delta", then
"stop spelling", and you get *Bad*. Each letter is read back as it is written,
so you hear a wrong one straight away. Say "scratch that" to take back the
last run of letters.

### Letters, numbers and symbols

Some things are not words at all: an email address, a file name, a heading
mark, a shout in capitals. This section is about writing exactly the
characters you want.

#### Spelling an email address or a web address

While you are spelling, punctuation goes in with no spaces around it, so an
address comes out whole. Say "start spelling", then "juliet alpha yankee dot
sierra mike india tango hotel at sign echo x-ray alpha mike papa lima echo dot
charlie oscar mike", then "stop spelling", and you get *jay.smith@example.com*.
Plain letter names work too ("jay", "bee", "see"), but every part must be
letters: a whole word such as "smith" is not a letter and is left out, so
"jay dot smith" writes only *j.*. Spell the word instead.

You do not have to say the address in one breath. While spelling, each phrase
joins the letters you spelled just before it, with no space: "juliet oscar", a
pause, "at sign echo x-ray", a pause, "dot charlie oscar" writes *jo@ex.co*.
Say "space" when you want a space. If you move the cursor between phrases, the
next letters start fresh, with a space in front as usual.

While you are spelling, "dot" and "point" both mean a full stop. Outside
spelling they are just words, so "the main point" stays as you said it.

Say **"all caps"** while spelling, and the letters after it are capitals until
you say **"no caps"** or the phrase ends. "All caps november alpha sierra
alpha" writes *NASA*.

#### Spelling one word, without spelling mode

For a single word, you do not need to start and stop spelling mode. Say
**"spell"** and the letters, all in one breath: "spell bravo alpha delta"
writes *bad*, and dictation carries straight on in words. This only happens
when "spell" is the first word of the phrase and the rest is letters. A
sentence like "spell it out for me" is written as words.

#### Spelling over what was just written

When the engine has just written a name wrong, say **"spell that"**. The last
phrase is selected, and the next thing you say is spelled out letter by letter
and put in its place. It works for that one next phrase only, then dictation
goes back to words. For example, you say "my friend Siobhan", it comes out
*my friend Shivon*, you say "spell that", and then "capital sierra india oscar
bravo hotel alpha november".

#### Capitals and spaces that stay on

These last until you turn them off, or until dictation stops. The Dictation
part of the status bar shows which are on, and Dictation Status (**Alt+F9**)
tells you too.

| Say | What happens |
|---|---|
| "caps on" (or "capitals on") | Every word starts with a capital: handy for a title or a name. "Caps off" stops it. |
| "all caps on" | Everything is written in capitals. "All caps off" stops it. |
| "no space on" | Words are joined with no spaces, and no automatic capitals: handy for a web address or a file name. "No space off" stops it. |

For example: say "no space on", then "my summer notes", then "no space off",
and you get *mysummernotes*. Outside spelling, "dot" is a word, so for the full
stop in a file name or an address, spell that part: "spell dot tango x-ray
tango" writes *.txt*. For a whole address, spelling mode is usually quickest.

#### Marks for Markdown and code

You can say these anywhere in a phrase:

| Say | Writes |
|---|---|
| "backtick" or "back quote" | a backtick. The first on a line opens, the next one closes, so the spaces come out right. |
| "triple backtick" or "code fence" | three backticks on a line of their own, to start or end a block of code |
| "tilde" | `~` |
| "vertical bar" or "pipe symbol" | the vertical bar, used between table columns |
| "caret" | `^` |
| "greater than sign" | `>` |
| "less than sign" | `<` |

#### Starting a heading or a list item

These count only as the **first words** of a phrase. If the cursor is not at
the start of a line, a new line comes first.

| Say first | Writes |
|---|---|
| "bullet" or "list item" | a dash and a space, starting a bulleted item |
| "numbered item" | 1, a full stop and a space |
| "block quote" | `>` and a space |
| "heading one" to "heading six" (or "heading 1" to "heading 6") | one to six # marks and a space |

So "heading two Our plans for spring" starts a level two heading, and
"bullet buy more coffee" starts a list item. In the middle of a sentence they
are ordinary words: "the heading two lines down" is written just as you said
it.

### Moving and selecting by voice

You can move around your document by saying the words you want to get to.
These work with every engine, and they are said at the **start** of a phrase,
followed by words that are already in your document.

| Say | What happens |
|---|---|
| "select" and some words | Those words are selected. What you say next replaces them. |
| "select" some words "through" some more words | Everything from the first words to the last is selected. |
| "go to" (or "go before") and some words | The cursor goes just before those words. |
| "go after" and some words | The cursor goes just after them. |
| "correct" and some words | The words are selected, and you hear "Correcting" and the words, then "Say the new words". What you say next takes their place. |
| "select again" or "select next" | The next place the same words appear. |
| "select previous" | The place before. |

And these, said on their own: "select sentence" (or "select this sentence"),
"select line", "select paragraph", "go to start of paragraph" and "go to end
of paragraph".

**Where it looks.** QUILL Lite looks first in the text before the cursor,
nearest first, because that is usually what you have just said and want to
change. If the words are not there, it looks after the cursor.

**How it matches.** Capitals, punctuation and accents do not matter, and
numbers match both ways, so "select two cats" finds *2 cats*. Your corrections
in My Words and Phrases are applied first, so a word the engine always mishears
is still found.

**What you hear.** One short sentence: "Selected: the cat", "Before the cat"
or "After the cat". If the place is three lines or more from where you were,
the line is added, like "Selected: the cat, line 40", so you know you have
travelled.

**If the words are not there.** What you said is written as ordinary text, and
you hear "Not found, written as text." Say "scratch that" to take it away. That
way a sentence that happens to start with "select" or "correct" is never lost.

The exact commands still come first: "select that" selects your last phrase,
and "go to top" goes to the top, as before.

**A small example.** You dictate "The meeting is on Tuesday at ten." Then you
remember it moved. Say "correct Tuesday", hear "Correcting Tuesday. Say the new
words", and say "Thursday". The sentence now reads *The meeting is on Thursday
at ten.*

### Snippets and clips by voice

The things you keep for reuse can be reached by voice too: the twelve Copy
Tray slots, your snippets (the abbreviations in the **Snippets** gallery,
**Ctrl+Alt+Shift+Home**), and copying.

Said on their own:

| Say | What happens |
|---|---|
| "copy all", "copy everything" or "copy document" | Copies the whole document, the same as Copy All on the Edit menu. |
| "copy that" | Copies the phrase you dictated last. |
| "show clips", "open copy tray" or "show copy tray" | Opens **Paste from Tray** (**Ctrl+Alt+V**), so you can choose a slot. |
| "show snippets" | Opens **Snippets** (**Ctrl+Alt+Shift+Home**). |

Said at the start of a phrase, with words after:

| Say | What happens |
|---|---|
| "paste clip three" or "paste slot three" | Writes Copy Tray slot 3. Any slot from one to twelve. If the slot is empty you are told, and nothing is written. |
| "insert snippet" and a name | Writes that snippet. |
| "insert abbreviation" or "expand abbreviation" and an abbreviation | Writes what that abbreviation expands to. |

**Finding the snippet you mean.** You do not need the name exactly. Capitals,
punctuation and spaces do not matter. An exact name wins first, then a name
that starts with what you said, then a name containing your words. If several
match, you hear how many and the Snippets gallery opens so you can choose. If
none match, you hear "No snippet called" and what you said, and nothing is
written. In QUILL Lite, "insert snippet" and "insert abbreviation" both reach
the same library, so use whichever comes to mind.

**One phrase, one undo.** A snippet or a slot goes in as one dictated phrase.
**Ctrl+Z** or "scratch that" takes the whole thing back. The read-back keeps
it short: you hear "Snippet sign off" or "Pasted slot 3", not the whole text
read out.

These are commands, so they do not work while **Just write what I say** is
on.

### The full list of what you can say

While you are dictating, say **"what can I say"**. You can also press
**Dictation Commands...** in Dictation Settings. A window opens with every
phrase dictation understands, including your own phrases and your wake phrase.
Read it with the arrow keys, and press Escape to close it.

The same list is also its own document, the
**Dictation commands** file (dictation-commands.md), next to this guide. It is made
from the very table dictation reads, so it always matches what QUILL Lite
understands. It has every way of saying each thing, the Spanish punctuation
words, and the spelling alphabet in one place, and it is a good page to keep
open beside you for the first week or two.

Near its end are **Worked examples**: what you have, what you say, and what you
get. They show going before and after words ("go to Friday", then "next"),
picking the second of three matches ("select the cat", then "select
previous"), Copy All, scratch that, all twelve clips, snippets with spaces in
their names, every capitals command, an email address spelled with pauses, and
a Markdown link ("open bracket the guide close bracket open paren page close
paren" writes `[the guide](page)` with no space in the middle). After them come
the **Limits**, including what cannot work when you dictate into another
program. Every example is checked by automated tests in both QUILL Lite and
QUILL. How accurately and how quickly each engine hears you has not been
measured yet; that waits on the dictation benchmarks.

### The command word: "QUILL scratch that"

Commands work when you say them on their own, after a pause. To be sure a
command is taken as a command and never written, say the command word first:
**"QUILL scratch that"**, **"QUILL select the cat"**, **"QUILL caps on"**.
Every command in the list works this way.

- QUILL counts only as the first word after a pause, so "I told Quill about
  it" is written as words.
- If what follows is not a command, nothing is written. You hear the error
  sound and "Not a command. Say it again, or say QUILL type that to write it."
  **"QUILL type that"** writes those words after all, once.
- To write the word itself, say **"literal QUILL"**.
- Say **"QUILL"** on its own and pause, and the next thing you say is a
  command. A short rising tone tells you it was heard.
- **"QUILL command mode"** takes commands without the word: you hear the tone
  and "Command mode", and the Dictation cell in the status bar says Command
  mode. Say **"dictation mode"** to go back. If you give no command for eight
  seconds, it ends by itself with a falling tone, and what you say next is
  written.
- **Next Phrase Is a Dictation Command** (**Ctrl+Alt+Shift+Q**, Q for QUILL)
  does the same from the keyboard: press it, then say the command. Press it
  twice for command mode, and once more to leave. If dictation is off, it
  starts dictation first. It used to be Speak a Command on F11; F11 is now Say
  or Type a Command, which is for QUILL Lite's own commands.

More Dictation Settings has three choices for it: the **Command word**
(**Alt+C**; leave it empty to give commands with F11 only), **Commands only
after the command word (strict mode)** (**Alt+E**), and **Seconds command mode
waits for a command** (**Alt+D**, 5 to 30). With strict mode on, "scratch that"
on its own is written as words, and only the stop phrase works without the
word. Strict mode is off in QUILL Lite, so the commands you know keep working.
A common word, or one of your own words in My Words and Phrases, cannot be the
command word; you are told why.

### Dictation profiles: the kind of writing you are doing

A dictation profile changes dictation for one kind of writing in one step,
instead of changing several settings each time. There are seven:

| Profile | What it changes |
|---|---|
| Standard | Nothing: your Dictation Settings as they are. Headings are written as Markdown marks, as before. Everybody starts here. |
| Email | Removes filler words and adds punctuation. Headings, bold and italic use QUILL Lite's own formatting. |
| Document | Headings, bold and italic use QUILL Lite's own formatting. |
| Markdown | Headings, bold and italic are written as Markdown marks. |
| Chat | Removes filler words; plain text, with no heading marks. |
| Coding | Removes filler words, adds no punctuation of its own (you say every mark), and waits longer for a pause. Markdown marks. |
| Verbatim | Keeps every word you say, fillers too; plain text. |

**Choosing one.** Open Dictation Settings (**Alt+Shift+F6**), press **More Dictation
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
- **Document** and **Email**: In a rich text document, QUILL Lite's own Heading, Bold and Italic
commands apply the style, as if you had pressed their keys. In a plain text document nothing is
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

### Review before inserting

When you want to check what you said before it goes into the document, review
it first. Your words wait in the **Review Dictation** window, and nothing goes
into the document until you insert them.

- **Say "QUILL review that"**, or press **Review Dictation** (**Shift+F4**, in
  **Tools > Dictation**), while dictating. The last phrase is taken back out of
  the document and opened in the window. Press Shift+F4 with dictation off and
  the window opens empty.
- **Read the words** with the arrow keys. They are in an ordinary text box, so
  your screen reader reads them by line, word and character, and a braille
  display shows them. Type to change them, or keep talking: while the window is
  open, what you dictate is written into it, not into the document.
- **Ask the AI to change them.** Type an instruction such as "make it shorter"
  in **Ask the AI to change it** (**Alt+K**) and press Enter, or say it after
  the command word: **"QUILL make it shorter"**, **"QUILL more formal"**,
  **"QUILL fix the grammar only"**. You hear "Working", then what changed, in
  two sentences at most, such as "Changed next Thursday to Friday. Removed um,
  so." QUILL Lite works that out by comparing the words itself, never from the
  AI's own account, and says "Large change" when more than half the words
  changed. **Talk about it** (**Alt+A**) makes everything you say an
  instruction, without the command word.
- **Insert** (**Ctrl+Enter**, or say **"QUILL insert it"**) puts the words
  where they came from, as one step that Ctrl+Z takes back. The words as you
  said them and as they went in both go into Recent Phrases.

| Key | What it does | Say, after the command word |
|---|---|---|
| **Ctrl+Enter** | Insert the words | "insert it" |
| **Ctrl+R** | Read all the words aloud | "read it back" |
| **Ctrl+D** | Say again what the last change did | "what changed" |
| **Ctrl+Z** | Undo the AI's last change; with none, undo your typing | "undo that change" |
| **Ctrl+Shift+Z** | Back to the words exactly as you said them | "back to what I said" |
| **Escape** | Stop a request on its way; otherwise discard the words, asking first if the AI changed them | "discard it" |

Changing words with AI needs AI help switched on in Customize Features and an
AI other than the free one, as Tidy Dictated Text does; it never
uses the free service's allowance, and each change you ask for is one request.
The first time, QUILL Lite asks before anything is sent and names who receives
it; No is the default and sends nothing. Only the words in the window and your
instruction are sent, with My Dictation Instructions if you wrote any; this
document's dictation context goes too only if you check **Include this
document's dictation context with requests** (**Alt+O**). With AI off, "QUILL
review that" says "AI is off. Your words were written as you said them." and
leaves them where they were, and Shift+F4 still opens the window to edit and
insert by hand.

If you close the window with Close, or QUILL Lite closes or stops unexpectedly,
your words are kept: the next time it starts it says so, and Review Dictation
brings them back. Discard throws them away. To send everything you dictate to
the window first, turn on **Send dictation to review first** (**Alt+V**) in More
Dictation Settings.

### Polishing your dictation with AI, only when you ask

**Polish** tidies punctuation, capitals and small slips without rewording
anything. It is one request you ask for each time, it is off until you turn it
on, and it never runs by itself.

1. Open **Dictation Settings** (**Alt+Shift+F6**), press **More Dictation
   Settings...** (**Alt+A**), and check **Allow polishing my dictation with AI
   when I ask** (**Alt+G**). Press OK in both windows.
2. Dictate as usual. When you want a phrase polished, say **"QUILL polish
   that"** or "QUILL polish it". The last phrase is taken back out and opened in
   Review Dictation, and the polish request is made there. If Review Dictation
   is already open, the words in it are polished.
3. In the Review Dictation window you can also press **Polish** (**Ctrl+P**).
   The button is there only while polishing is allowed.
4. You hear "Polishing", then what changed. Read the words, then press
   **Insert** (**Ctrl+Enter**), or take the change back with **Undo Change**
   (**Ctrl+Z**).

The AI is asked to fix punctuation, capital letters, spelling and obvious
grammar slips only, and to keep your words, meaning, order and tone. Polish
uses the same AI, account and first-time question as the rest of Review
Dictation: nothing is sent until you say yes, and only the words in the window
are sent. With AI off the Polish button is greyed out, and with polishing not
allowed "QUILL polish that" says "Polish my dictation is off" and sends nothing.

### Correcting yourself as you talk

With **Fix it when I correct myself, like Thursday, no, Friday** (**Alt+X**)
checked in Dictation Settings, QUILL Lite writes only what you meant when you
correct yourself mid-sentence:

| You say | QUILL Lite writes |
|---|---|
| meet on Thursday, no, Friday at noon | meet on Friday at noon |
| in June, no I mean July | in July |
| I have two no three cats | I have three cats |
| call me at 5, sorry, 6 | call me at 6 |
| send it to Ana, sorry, Maria (both names in My Words) | send it to Maria |

The marking words are "no", "I mean", "no I mean", "sorry" and "scratch that
word", and a correction is made only between two days, two months, two numbers
or two names from the Vocabulary list in My Words and Phrases. Anything else is
written as you said it: "no, I don't think so" and "Is it Thursday? No,
Friday." stay exactly as they are. It works on this computer with no AI, it is
off until you turn it on, and live transcripts never use it.

**Dictation style** (**Alt+Y**) sets these choices together: **Verbatim**
(every word as you say it), **Clean** (no filler words, and your corrections
fixed) or, only when AI help is on, **Polished** (Clean, plus Send dictation to
review first and Allow polishing my dictation with AI). Choosing Polished sends
nothing by itself. Change a check box yourself and the style shows **Your own
mix of the settings below**.

### Learning from your corrections

When you correct the same word the same way twice, by "correct that" and then
"choose two", or by "correct Ann" and then the new words, a window called **Add
a Correction** asks, for example, "Add a correction: Ann becomes Anne?" **No**
is the default. **Yes** adds it to the Corrections list in My Words and Phrases
(**Alt+Shift+F10**), where you can change or remove it, and the next phrase
uses it. Each pair is asked about once each time QUILL Lite runs, only words
and short phrases of up to four words are offered, and nothing is saved unless
you say yes.

## Starting and stopping with your voice

### The wake phrase

If you would rather not reach for the keyboard, you can start dictation by
voice. In Dictation Settings, turn on **Listen for the wake phrase while
dictation is off**. Then say the wake phrase to start. It is **"Quill
dictate"** unless you choose something else.

- Say the wake phrase, pause, and start talking. Or say it and carry straight
  on: "Quill dictate, dear Sam, thank you for your letter" starts dictation and
  writes *Dear Sam, thank you for your letter.*
- "Stop dictation" (or Ctrl+F11) stops writing and goes back to waiting for the
  wake phrase.
- The wake phrase only counts at the start of what you say. If you say "I told
  Quill to dictate this" while chatting, nothing starts.
- It forgives a near miss. "Quil dictate" still works.

**Choosing your own wake phrase.** Type any phrase in the **Wake phrase** box.
It needs at least two words. Pick something you would not say in passing; a
name and a verb works well. QUILL Lite will not accept a single word, so
dictation does not start by accident.

**What happens with your microphone.** While the wake phrase is on, the
microphone is open whenever QUILL Lite is the window in front. Anything it
hears that does not start with the wake phrase is dropped straight away. It is
never written, kept or sent anywhere. When you switch to another program, the
microphone closes, and dictation stops if it was running. When you come back
to QUILL Lite, it listens for the wake phrase again. It never listens while
QUILL Lite is in the background, so it will not pull you away from whatever
else you are doing. The wake phrase is off until you turn it on.

The wake phrase works with Moonshine, Whisper and Windows speech recognition.
It does not work with Windows voice typing, because Windows runs that itself.

### The stop phrase

Say **"stop dictation"** on its own, after a pause, and dictation stops. You
can add your own words too. Type them in the **Stop phrase** box in Dictation
Settings, and saying them stops dictation just the same. "Stop dictation"
keeps working either way.

- The stop phrase counts only when it is **everything you said** in that
  breath. If you say "I will stop dictation for today" in the middle of a
  paragraph, it is written down, not obeyed.
- Like the wake phrase, it forgives a near miss, and it needs at least two
  words so ordinary talk does not stop you by accident.
- With the wake phrase on, stopping takes you back to listening for the wake
  phrase. That way you can start and stop without touching the keyboard at
  all.

## Making dictation fit you

### Your own words and phrases

You can teach dictation the words you use. Press **Alt+Shift+F10**
(**Tools > Dictation > My Words and Phrases...**), or press the **My Words and
Phrases...** button in Dictation Settings. A window lists everything you have
taught it, one line each. Whatever you change is used from your very next
phrase. There are three kinds:

- **Words.** Names, jargon and acronyms, spelled the way you want them. When
  the engine writes something that sounds or looks close, it is fixed to your
  spelling. Add *Tucson*, and "tuxon" becomes *Tucson*. **Add Word...** asks
  for the word.
- **Phrases.** Something short you say that writes something longer. **Add
  Phrase...** asks what you will say (*my email address*) and what it should
  write (your address). Press Enter in the second box for a new line, so a
  signature can be two lines.
- **Corrections.** Something the engine keeps getting wrong, and what to write
  instead. **Add Correction...** asks what it writes now (*quill light*) and
  what it should write (*QUILL Lite*). Corrections work on every phrase, with
  any capitals, on every engine.

**Edit...** (or Enter on a line) changes the one you are on, and **Remove**
takes it out. Each change is saved straight away and read back to you. If you
like working in a file, **Open the File...** opens the same list as a plain
text file called `dictation.md`.

### Moving and sharing your word list

**Export...** in My Words and Phrases saves your whole list to a file you name.
Choose **Word list in Markdown** for the same kind of file as `dictation.md`, or
**Spreadsheet, say and write columns** for a CSV file with three columns: `say`,
`write` and `kind` (word, phrase or correction). You hear how many were saved,
such as "Exported 15 entries to my-dictation-words.md."

**Import...** reads a Markdown word list or a CSV file and adds what is new. A
CSV file needs a `say` column; `write` and `kind` are optional. Before anything
changes, a window shows how many entries will be added and how many are already
in your list, with the new ones listed. Press **Add Them** to add them, or
**Cancel** to change nothing. Then you hear, for example, "Imported 12 words, 3
already there." Import never replaces anything: where the file has a word or
phrase you already have, written differently, yours is kept. Your list as it was
is saved first, as `dictation-before-import.md` beside `dictation.md`. To undo
an import, copy that file over `dictation.md`.

**Use the shared word list** is the check box at the top of the window. QUILL,
QUILL Transcribe and Quill Inkwell share one list on this computer. QUILL Lite
keeps its own until you check this box. When you check it, a window first shows
which of your words will be added to the shared list; press **Use the Shared
List** to go ahead. From then on, a word you add here is used by all of them
from their next phrase. Uncheck the box to go back to QUILL Lite's own list,
which is just as you left it. The box is not shown in a portable copy, which
always keeps its own list. Your dictation instructions and dictation contexts
are kept beside the list, so they come with whichever list you use.

**Where the shared list lives.** Since this version the shared list is in the
family's own dictation folder: `%LOCALAPPDATA%\QuillVille\Dictation` (press
Windows+R, type that and press Enter to open it). The first time a QuillVille
program needs it after the update, it is copied there from QUILL's data folder,
with the instructions and contexts beside it. It is copied, never moved: the old
files stay as they were, as a backup, and a list already in the new folder is
never replaced. If the copy cannot be made, the old file is read instead, and the
copy is tried again next time. QUILL Lite's own list, the one you use while the
box is unchecked, stays in QUILL Lite's own data folder and is not touched.

Your own phrases show up in the "what can I say" list along with everything
else.

### Choosing the microphone

**Dictation Settings** lists every microphone by name. The first choice uses
whatever Windows is using as the default recording device. Choose a named
microphone if you always want that one, whatever the default becomes. If the
microphone you chose is unplugged, QUILL Lite tells you when you start
dictation. It never quietly listens on a different one.

### Talking in one long run: Just write what I say

Some people think out loud in one long run and pause wherever the thought
pauses. Normally, each pause ends a phrase: it gets a full stop, a tone plays,
and the words are read back. If that gets in your way, turn on **Just write
what I say: nothing happens at a pause** in Dictation Settings. Then a pause
does nothing at all:

- **No full stop just because you paused.** Your words carry on as one
  sentence until you say "period", "question mark" or another mark. Moonshine
  and Whisper still put in marks inside what you say.
- **No tone and no read-back** after each phrase, so nothing talks over you.
- **No voice commands.** "Scratch that" or "select that" said on its own is
  written as words. Punctuation and layout you say, like "comma" or "new
  paragraph", still work. So does the **stop phrase**, so you can always stop
  by voice.

Your words are still written as you go, and **Ctrl+Z** still takes back one
phrase at a time. Turn it off again when you want the commands back.

### The finer choices

- **Automatic punctuation (Moonshine and Whisper).** When it is on, the engine
  puts in full stops, commas and question marks for you. When it is off, it
  adds none, and you say every mark, just as with Windows speech recognition.
- **Pause before a phrase is written.** Short (half a second), Normal (under a
  second), Long (about a second and a half), Longer (2 seconds) or Longest (3
  seconds). If dictation cuts you off while you are still thinking, choose
  Long, and go further if you need to; see "Longer pauses, and sentences you
  finish later" just below. Windows speech recognition uses the same length.
- **Remove filler words like um and uh.** Hesitations like um, uh, erm and hmm
  are left out. Real words are never removed.
- **Dictation style** (**Alt+Y**). Verbatim, Clean or, with AI on, Polished:
  a quick way to set the next two choices together. See "Correcting yourself
  as you talk".
- **Fix it when I correct myself, like Thursday, no, Friday** (**Alt+X**).
  "Thursday, no, Friday" writes Friday. Off at first.
- **Stop dictation after silence.** Never, or after 1, 5 or 10 minutes of
  hearing nothing, so dictation is not left writing in an empty room. With the
  wake phrase on, it goes back to waiting for the wake phrase instead. You hear
  why it stopped, for example "Dictation off after 5 minutes of silence."
- **Test Microphone.** This button is beside the microphone list. Press it,
  wait for "Speak now", and talk for four seconds. You hear how loud the
  microphone was (almost nothing, quiet, working, or very loud). With Moonshine
  or Whisper, you also hear exactly what the engine understood. Nothing is
  kept. The result stays in the box beside the button, so you can read it
  again.

### Longer pauses, and sentences you finish later

Everybody stops to think sometimes. If dictation keeps writing half a sentence
while you are still looking for the next word, give yourself more time. In
Dictation Settings (**Alt+Shift+F6**), set **Pause before a phrase is
written** to one of the two longest choices:

- **Longer (2 seconds; words appear later)**
- **Longest (3 seconds; words appear later still)**

Every phrase then waits that long after you stop talking before it is
written. That is the trade: more room to think, and a little longer to wait
before you hear your words back. Start with Longer. Move to Longest only if
Longer still cuts you off.

Even on the usual setting, QUILL Lite tries not to break a sentence you have
not finished. If a phrase ends on a word that no sentence ends on, the full
stop the engine put there is taken back, and your next phrase joins on. These
are words like *a*, *an*, *the*, *of*, *to*, *in*, *on*, *at*, *by*, *for*,
*with*, *from*, *into*, *about*, *and*, *but*, *or*, *my*, *your*, *his*,
*her*, *its*, *our*, *their*, *very*, *really* and *so*. Say "this is a very",
stop to think, then say "good test", and you get one sentence: *This is a
very good test.*

A full stop you **said** is never taken back. If you say "period", you meant
it.

### Dictation Context for This Document

Some engines do better when they know what you are writing. A letter to your
bank, a note to a friend and a page of computer instructions use very
different words. **Dictation Context for This Document...**
(**Ctrl+Alt+Shift+PageUp**, in **Tools > Dictation**) lets you tell it, in a
sentence.

The window has:

- **This document is:** a box where you describe it in your own words, like
  "A letter to my landlord about the boiler" or "Notes from the Tuesday book
  club".
- **Start from a saved context:** a list of contexts to start from. Yours come
  first, then five starters: Formal letter, Note to a friend, Technical
  writing, Meeting notes and Story.
- **Also save it as a context named:** type a name here to keep this one for
  other documents.
- **Who uses it:** a read-only line that tells you which parts of QUILL Lite
  will use what you wrote.

The context is remembered for this document, so next time you open it, it is
already there. An untitled document keeps its context until you close QUILL
Lite.

**Who uses it.** OpenAI dictation, with your own key, uses it to understand
you better. **Tidy Dictated Text** (**Ctrl+F3**) uses it too, alongside your
My Dictation Instructions, so a tidied letter sounds like a letter. The
engines on your own computer cannot use a context, and the window tells you
so when one of them is chosen. It costs nothing to write one anyway, ready for
when you tidy.

**By voice.** Say **"dictation context"** and the name of a saved one, like
"dictation context meeting notes", and that context is used for this
document.

**Privacy.** The context only goes where your speech or your text is already
going: to OpenAI when you use OpenAI dictation, and to the AI when you use
Tidy Dictated Text. It never goes anywhere on its own.

### Dictation Settings, every option

Open **Tools > Dictation > Dictation Settings...** (**Alt+Shift+F6**). The
window has two columns. The left side is about what is heard and written. The
right side is about starting and stopping.

| Option | What it does | Starts as |
|---|---|---|
| Speech engine | Moonshine, Whisper, Windows speech recognition, Windows voice typing, any model you downloaded, OpenAI with your own key, or a speech provider you set up; see "Which engine should I choose?" | Moonshine |
| Dictation language | English, or Spanish (see "Dictating in Spanish"). Ctrl+Shift+F11 switches it without opening this window. | English |
| Automatic punctuation (Moonshine and Whisper) | The engine puts in the marks you do not say | On |
| Language for Windows speech recognition | Which installed Windows speech language to use; the other engines follow the dictation language | Windows default |
| Microphone | Which microphone to listen on | Windows default |
| Test Microphone (button) | Four seconds of listening: how loud, and what was heard | (a button) |
| After each phrase is written, give me | A sound, speech (the words read back), both, or neither | Both |
| Saying "dash" writes | Em dash, spaced en dash, or two hyphens | Em dash |
| Pause before a phrase is written | Short, Normal, Long, Longer (2 seconds) or Longest (3 seconds) | Normal |
| Remove filler words like um and uh | Leave hesitations out | Off |
| Dictation style (Alt+Y) | Verbatim, Clean, or Polished when AI is on; sets the choices below | Verbatim |
| Fix it when I correct myself, like Thursday, no, Friday (Alt+X) | Writes only the second of two days, months, numbers or names from My Words | Off |
| Just write what I say: nothing happens at a pause | No full stop, sound, read-back or command at a pause | Off |
| Play sounds when dictation starts, stops or fails | The start, stop and error tones | On |
| Say "Dictation on" and "Dictation off" | The words that go with those tones | On |
| Listen for the wake phrase while dictation is off | Start dictation by voice | Off |
| Wake phrase | The words that start it | Quill dictate |
| Stop phrase | The words that stop it, said on their own | stop dictation |
| Stop dictation after silence | Never, or after 1, 5 or 10 minutes | Never |
| Better Accuracy: Speech Models (button, Alt+B) | Optional larger models to download, remove or choose (see "Better accuracy: optional speech models") | (a button) |
| Speech Providers (button, Alt+V) | Set up a speech company you have your own account with (see "Speech providers: dictation with your own account") | (a button) |
| Recommended for this computer | The model that suits this computer and why, in one line to read; only advice | (read-only) |

Three buttons sit below the options. **Dictation Commands...** opens the full
list of what you can say. **My Words and Phrases...** saves your settings and
opens the window described in "Your own words and phrases" above. **More
Dictation Settings...** (**Alt+A**) opens the window below.

### More Dictation Settings, every option

Press **More Dictation Settings...** (**Alt+A**) in Dictation Settings. What
you change here is saved when you press OK in Dictation Settings.

| Option | What it does | Starts as |
|---|---|---|
| Hold the dictation key to talk; a quick press still turns it on and off | Also lets you hold Ctrl+F11 while you talk and let go to stop | Off |
| While you speak, the words heard so far | Show them in the status bar and on braille, also say new words quietly, or do not show them | Show them |
| Say punctuation marks in the read-back (Alt+S) | The read-back says "comma", "period" and the rest by name, so you hear what went in | Checked |
| Tick while a phrase is being worked on (Alt+R) | A soft tick once a second while a phrase takes more than a second to turn into text | Unchecked (checked in QUILL Transcribe) |
| Time stamps in live transcripts (Alt+T) | Each new paragraph of a live transcript starts with the time, like [10:42] | Unchecked |
| Send a dictated message to the AI | When I pause, or When I press Enter | When I pause |
| Pause before the message is written | Short, Normal or Long, when talking to the AI | Long |
| Remove filler words when talking to the AI | Leave um and uh out of what you say to the AI | On |
| Automatic punctuation when talking to the AI | Let the engine punctuate what you say to the AI | On |
| Let OpenAI dictation send my speech to OpenAI | Your agreement, which you can take back here | Off |
| OpenAI speech model | The model OpenAI dictation uses, from OpenAI's own list | The newest |
| Add or Change OpenAI Key (button, Alt+K) | Saves your settings and opens Use My Own AI Key | (a button) |
| My Dictation Instructions (button, Alt+I) | Opens the file Tidy Dictated Text follows | (a button) |
| Dictate in Other Programs (button, Alt+O) | Saves your settings and hands them to QUILL Transcribe if it is installed, otherwise to Quill Inkwell, and starts it; see "Dictating into other programs" | (a button) |
| Programs Dictation Never Types Into (button, Alt+N) | The programs dictation never types into from Quill Inkwell or QUILL Transcribe, such as your password manager; see "Programs dictation never types into" | The common password managers and the Windows sign-in prompts |
| Command word (Alt+C) | The word you say before a command, like QUILL scratch that; empty for none; see "The command word" | QUILL |
| Commands only after the command word (strict mode) (Alt+E) | A command said on its own is written as words; the stop phrase always works | Unchecked (checked in QUILL Transcribe) |
| Seconds command mode waits for a command (Alt+D) | How long command mode lasts with no command, from 5 to 30 | 8 |
| Send dictation to review first (Alt+V) | What you dictate goes into Review Dictation instead, to insert once; see "Review before inserting" | Unchecked |
| Allow polishing my dictation with AI when I ask (Alt+G) | "QUILL polish that" and the Polish button in Review Dictation ask the AI to fix punctuation and small slips, keeping your words | Unchecked |
| Keep a dictation history (Alt+Y) | Off, One day, Seven days or Thirty days of the text you dictate, never the sound, listed in Recent Phrases; turning it off deletes it; see "Recent phrases" | Off |
| Dictation profile, for the kind of writing (Alt+A) | Standard, Email, Document, Markdown, Chat, Coding or Verbatim; see "Dictation profiles" | Standard |
| Lock the profile so it cannot be switched by voice (Alt+B) | A spoken profile name does not switch profiles | Unchecked |
| Share dictation settings with every QuillVille program (Alt+Q) | Your dictation settings are the same in QUILL Lite, QUILL, QUILL Transcribe and Quill Inkwell; see "Sharing dictation settings with the family" | Checked for a new install; unchecked if you had changed your settings before |

### Sharing dictation settings with the family

**Share dictation settings with every QuillVille program** (Alt+Q) is a check box in More
Dictation Settings. When it is on, the dictation settings you save are the same
in QUILL, QUILL Lite, QUILL Transcribe and Quill Inkwell on this computer.

- **What is shared:** the engine and model, the language, the microphone,
  automatic punctuation, the pause that ends a phrase, filler words, the wake
  phrase, the command word, review first, the never-type list and the other
  dictation choices.
- **What QUILL Lite keeps to itself:** its keys, the working tick, strict mode,
  what you hear after each phrase, and every permission to send your speech to
  a company.
- **When it arrives:** what you save with OK in Dictation Settings is there for
  the others at once. When you come back to QUILL Lite after saving something
  in another program, the status bar says "Dictation settings updated from the
  family."
- **To begin with** it is checked for a new install. If you had changed your
  dictation settings before this update, it starts unchecked, so nothing you
  chose is replaced; check it when you want to join in.
- **Nothing is lost:** the first time QUILL Lite takes settings from the
  family, its own are saved first as `before-sharing-lite.json` in
  `%LOCALAPPDATA%\QuillVille\Dictation`.
- If two programs save at once, the last one saved wins; the file is never
  half written. If the shared copy cannot be saved, you hear why, for example
  "Saved here, but the other QuillVille programs will not see this change: the
  shared dictation settings could not be written (Access is denied)." QUILL
  Lite's own copy is saved either way.
- A portable copy shares only with the programs in its own folder.

For example: choose Spanish in QUILL Transcribe with Ctrl+Shift+F11, switch to
QUILL Lite, and Ctrl+F11 dictates in Spanish.

### Dictating in Spanish

You can dictate in Spanish. It's new, so think of it as something to try, and
let us know how it goes.

**To switch it on**, open Dictation Settings (**Alt+Shift+F6**), move to
**Dictation language**, choose **Spanish**, and press Enter. To go back,
choose English the same way. There is a quicker way too, described next.

#### Switching between English and Spanish

If you write in both languages, you do not need the settings window at all.

- **By key:** press **Ctrl+Shift+F11** (**Switch Dictation Language**, in
  **Tools > Dictation**). Each press switches between English and Spanish, and
  you hear "Español." or "English."
- **By voice, in English:** say "switch to Spanish" or "Spanish dictation".
- **By voice, in Spanish:** say "cambiar a inglés" or "dictado en inglés". You
  can leave the accent off; "cambiar a ingles" works just as well.

You can switch while dictation is running. The engine starts again in the new
language, which can take a moment the first time. The very first switch to
Spanish while you are using Moonshine takes a little longer, because Whisper
has to get ready. After that, both stay ready until you close QUILL Lite, so
switching back and forth is quick.

The language you choose is saved, so the next time you dictate, you start in
the language you used last. QUILL Lite never guesses the language from what
you say; it is always your choice. Dictation Status (**Alt+F9**) tells you
which language you are in.

#### What works in Spanish

**What works now:**

- **Your words come out in Spanish**, accents and all. QUILL Lite uses
  Whisper's multilingual speech model for this. It comes with QUILL Lite, so
  there is nothing to download. Moonshine only knows English, so in Spanish
  you get Whisper whichever of the two you chose.
- **A better Spanish model, said once.** The built-in Whisper gets about one
  word in four wrong in Spanish. If your computer can run NVIDIA Parakeet TDT
  0.6B v3 (in practice, 8 GB of memory and four cores), the first time you
  dictate in Spanish you hear one sentence saying so, for example: "For
  Spanish, NVIDIA Parakeet TDT 0.6B v3 gets about 6 percent of words wrong,
  against 29 for the built-in model. It is a 670 MB download in the model
  list." Nothing is downloaded or changed; the choice is yours. You hear it
  once, in whichever QuillVille program you dictate in first. A computer with
  4 GB hears nothing, because the built-in model is the right one there.
- **Windows speech recognition** needs Spanish installed in Windows: add
  Spanish (Spain or Mexico) in Windows Settings, Time and language, Speech. If
  it isn't there, dictation tells you when you start.
- **The wake and stop phrases** become "Quill dicta" and "deja de dictar".
  If you typed your own, yours stay.

**Commands stay in English for now.** "Scratch that", "select that", "new
paragraph" and the others work just as they do in English. The one exception
is switching back: "cambiar a inglés" and "dictado en inglés" work in Spanish.
More Spanish commands will come once a native speaker has checked them.

**Punctuation.** With automatic punctuation on (the usual setting), Whisper
adds the commas, full stops and question marks for you, so just talk. The
Spanish punctuation words only work when automatic punctuation is off, or
with Windows speech recognition. That's because "coma" and "punto" are
everyday words too, and nobody wants "que coma" turned into a comma. When
they are on, you can say:

- "coma" for a comma, "punto" (or "punto y seguido") for a full stop, and
  "punto y aparte" for a full stop and a new paragraph
- "punto y coma", "dos puntos" and "puntos suspensivos"
- "abrir interrogación" and "cerrar interrogación" for the question marks at
  each end, and "abrir exclamación" and "cerrar exclamación" the same way
- "abrir paréntesis", "cerrar paréntesis", "abrir comillas", "cerrar comillas"
- "guion", "guion largo" and "arroba"
- "nueva línea", "nuevo párrafo" and "tabulador"

Say "literal" first to write the word itself: "literal coma" writes *coma*.
Say "what can I say" while dictating to see the full list.

**It's new, and your feedback helps.** If a word keeps coming out wrong, or
something doesn't work the way you expect, use **Help > Get Help from
Support** and tell us what you said and what was written.

### Better accuracy: optional speech models

Dictation works the moment you install. If you want more accuracy, you can
download a larger model. In our tests with real recordings, the best English
download, NVIDIA Parakeet Unified 0.6B, made about half the mistakes of the
built-in Moonshine (3.2 percent of words wrong against 6.5), and the best
Spanish one, NVIDIA Parakeet TDT 0.6B v3, got 4.4 percent wrong on Google's
FLEURS Spanish where the built-in Whisper got 30.5.

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
   carries on from there, even after you close QUILL Lite.
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
**Recommended for this computer** box at the top of its right-hand column.

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

What it names, in short:

- **English, 8 GB of memory and four cores or more:** NVIDIA Parakeet Unified
  0.6B.
- **English, 8 GB and two cores:** NVIDIA Parakeet TDT 0.6B v3.
- **Spanish, 8 GB:** NVIDIA Parakeet TDT 0.6B v3.
- **4 GB, or little memory free:** the built-in Moonshine for English and the
  built-in Whisper for Spanish. A computer with 4 GB has room for only about
  600 MB of dictation beside a screen reader, and the larger models need
  twice that or more.
- **The quickest response:** the built-in Moonshine.

On a computer with 8 GB, dictation may take up to 1.6 GB of memory beside your
screen reader, and never more than is free when you ask, less half a
gigabyte.

The recommendation is only advice. QUILL Lite never changes your engine by
itself; you choose. Its figures come from our tests with real recordings, on
one computer; yours may differ. A graphics card makes no
difference: every dictation model runs on the processor.

**Tiers.** Every model is labelled with one of three tiers, wherever you
choose one: the Speech engine list, Speech Models and Transcribe a Recording.
What each tier means is in "Which engine should I choose?" above. The tiers
follow the speeds we measured on real speech. Which models are in which:

- **Lightweight**: the built-in Moonshine and Whisper, Moonshine base, NVIDIA
  Parakeet TDT 0.6B v3, NVIDIA Parakeet Unified 0.6B and Whisper base.en.
- **Balanced**: NVIDIA Nemotron and Whisper base.
- **High accuracy**: Whisper small, medium, large-v3-turbo and large-v3.

**Five models were removed in this release.** Distil-Whisper small.en,
Whisper small.en, Distil-Whisper medium.en, Whisper medium.en and
Distil-Whisper large-v3 are no longer in the list. They were all English
only. On the held-out audiobooks, NVIDIA Parakeet Unified 0.6B got 3.2
percent of words wrong, against 3.6 to 6.3 for these five. It was also faster
on one thread, in the same or a smaller memory tier. Whisper base.en and every
many-language Whisper size stay.

If you were using one, dictation switches to Parakeet Unified when you update,
if you have already downloaded it. Otherwise dictation uses the built-in
model. Nothing is downloaded for you. The next time dictation starts, you hear
one sentence saying so, once across every QuillVille program, not once in
each. For example: "Whisper small.en was removed in this release. Dictation
now uses Parakeet Unified, which you already have." Or: "Whisper small.en was
removed in this release, so dictation uses the built-in model. Parakeet
Unified, in the model list, is more accurate." To use Parakeet Unified, choose
it in Speech Models, press **Download...** (**Alt+D**), then **Use for
Dictation** (**Alt+U**).

Your downloaded files are not deleted. They stay in the models folder (see
"Where the models go" below), in folders named whisper-small.en-int8,
whisper-distil-small.en-int8, whisper-medium.en-int8,
whisper-distil-medium.en-int8 and whisper-distil-large-v3-int8. Delete a
folder to free its space.

**Where the models go.** One folder for QUILL, QUILL Lite, QUILL Transcribe
and Quill Inkwell on the same computer, so a model downloaded in one is there
for the others and is never downloaded twice:
`%LOCALAPPDATA%\QuillVille\Dictation\models`. In a portable copy, models are
saved inside the portable folder, so everything travels together
(`data\dictation\models` in the portable folder). Before a download starts,
QUILL Lite checks there is room on that drive and tells you if there is not.
The built-in Moonshine and Whisper are not in that folder: they come inside
QUILL Lite itself.

**To remove one**, choose it in Speech Models and press **Remove**
(**Alt+R**). It frees the space for every program that shares the folder. If
dictation is using it, choose another engine first. The **Progress** box then
says how much space was freed, and focus goes back to the list of models.

**When you switch away from a downloaded model**, QUILL Lite offers to delete
it. After you choose another engine and press a plain **OK** in Dictation
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

#### The list, in our suggested order

The order is our suggestion, not a measurement: VS Code's own models first,
then the rest of Whisper, smallest first. For what we measured, see "How we
chose: tested on real speech" below; the Recommendation box follows those
measurements, not this order.

| Model | Good for | Download | Languages |
|---|---|---|---|
| NVIDIA Nemotron 3.5 ASR Streaming 0.6B | Suggested download. Excellent for live dictation; VS Code's default | 682 MB | English, Spanish |
| NVIDIA Parakeet Unified 0.6B | May give slightly better final text in some conditions | 663 MB | English |
| NVIDIA Parakeet TDT 0.6B v3 | Excellent recognition of each finished phrase | 670 MB | English, Spanish |
| Whisper small | A VS Code alternative: good | 375 MB | English, Spanish |
| Whisper base | A VS Code alternative: moderate | 161 MB | English, Spanish |
| Whisper tiny | Built in already. Fastest and lightest, weakest accuracy | (built in) | English, Spanish |
| Whisper base.en | Light and quick, a little better in English than base | 161 MB | English |
| Whisper medium | Best for accuracy when you can wait | 946 MB | English, Spanish |
| Whisper large-v3-turbo | Large-v3 quality, much faster than large-v3 | 1.0 GB | English, Spanish |
| Whisper large-v3 | The most accurate Whisper; very slow on most computers | 1.8 GB | English, Spanish |
| Moonshine base | A light step up from the built-in Moonshine | 141 MB | English |

**English only, or many languages?** Whisper base.en only knows English, and
is a little more accurate in English than the many-language base. The many-language ones also
dictate Spanish. If you only dictate English, NVIDIA Parakeet Unified 0.6B
made the fewest mistakes of any model we tested that keeps up; of the Whisper
models, base.en is the English-only one that stays.

#### How we chose: tested on real speech

On 22 October 2026 we tested every dictation model on recordings of real
people, never a computer voice: public-domain audiobooks catalogued after
every model was trained, so no model can have learned them, plus Google's
FLEURS read sentences and the LibriSpeech audiobook test sets. Each model
heard one phrase at a time on one processor thread, the way dictation hears
you. The advice in Speech Models and Dictation Settings comes from these
results. QUILL, QUILL Lite and QUILL Transcribe share these models and this
advice.

**English.** Percent of words wrong (lower is better), speed per thread (0.25
is dictation's budget, leaving the rest of the processor for your screen
reader) and the most memory used.

| Model | Held-out audiobooks | FLEURS | Speed per thread | Peak memory | Decision |
|---|---|---|---|---|---|
| NVIDIA Parakeet Unified 0.6B | 3.2% | 6.3% | 0.21 | 1.2 GB | Recommended on 8 GB with four cores |
| Whisper medium.en | 3.6% | - | 1.55 | 3.0 GB | Removed |
| NVIDIA Parakeet TDT 0.6B v3 | 3.8% | 9.0% | 0.11 | 1.1 GB | Kept; recommended on 8 GB with two cores |
| Whisper small.en | 4.3% | 6.3% | 0.43 | 1.4 GB | Removed |
| Distil-Whisper large-v3 | 4.5% | - | 0.82 | 2.0 GB | Removed |
| Whisper small | 4.7% | - | 0.55 | 1.4 GB | Kept; many languages, needs two threads |
| NVIDIA Nemotron 3.5 Streaming 0.6B | 5.3% | 13.7% | 0.37 | 1.5 GB | Kept; streams words while you speak |
| Moonshine base | 5.9% | 15.1% | 0.05 | 378 MB | Kept; fixed for long phrases |
| Whisper base.en | 5.9% | 7.4% | 0.13 | 820 MB | Kept; light, good on varied voices |
| Distil-Whisper small.en | 5.9% | 7.6% | 0.22 | 1.0 GB | Removed |
| Distil-Whisper medium.en | 6.3% | - | 0.47 | 1.6 GB | Removed |
| Moonshine tiny (built in) | 6.5% | 13.2% | 0.06 | 584 MB | Kept; the default, and the pick on 4 GB |
| Whisper base | 7.4% | 10.8% | 0.22 | 821 MB | Kept; many languages |
| Whisper tiny (built in) | 8.3% | 11.7% | 0.07 | 521 MB | Kept; built in |

A dash means that model was not run on that set.

**Spanish.**

| Model | FLEURS Spanish | Held-out Spanish audiobooks | Speed per thread | Peak memory | Decision |
|---|---|---|---|---|---|
| NVIDIA Parakeet TDT 0.6B v3 | 4.4% | 7.3% | 0.12 | 1.1 GB | Recommended on 8 GB |
| Whisper small | 6.0% | 7.8% | 0.57 | 1.4 GB | Kept; needs two threads |
| NVIDIA Nemotron 3.5 Streaming 0.6B | 6.4% | 8.0% | 0.50 | 1.5 GB | Kept |
| Whisper base | 12.6% | 16.1% | 0.18 | 821 MB | Kept; lighter |
| Whisper tiny (built in) | 30.5% | 27.0% | 0.10 | 521 MB | Kept; built in, the pick on 4 GB |

**What we found along the way.** Moonshine base wrote nothing at all for any
phrase longer than about eight and a half seconds. That is fixed: it now
hears a long phrase in pieces and joins them, and scored 5.9 percent on the
audiobooks. The pieces overlap by half a second, so a word that falls where
two pieces meet is not lost.

**The limits.** This was one fast computer on one day, so speeds are judged
against the built-in Moonshine's, which Speech Models times on your own
computer in its two-second check. A real 4 GB computer with a screen reader
running has not been measured yet. Whisper medium and large-v3-turbo were too
slow to re-run and keep their earlier figures. The full record, with every
set and every number, is the page "Dictation speech models tested on real
speech, 2026-10-22" in QUILL's documentation.

#### How accurate are they?

These are the figures each model's makers publish, on their own test sets.
Our own results on real speech are in the section above. A word error rate is
the share of words a model gets wrong on a recorded test set; lower is better.
Test sets differ, so compare numbers only within one line.

- **Nemotron 3.5 ASR Streaming:** 7.91 percent on FLEURS English and 4.11
  percent on FLEURS Spanish, at the chunk size this download uses (NVIDIA's
  model card, huggingface.co/nvidia/nemotron-3.5-asr-streaming-0.6b).
- **Parakeet Unified:** 1.63 percent on LibriSpeech test-clean and 3.11 percent
  on test-other (huggingface.co/nvidia/parakeet-unified-en-0.6b).
- **Parakeet TDT v3:** 4.85 percent on FLEURS English, 3.45 percent on FLEURS
  Spanish (huggingface.co/nvidia/parakeet-tdt-0.6b-v3).
- **Whisper**, on LibriSpeech test-clean (OpenAI's Whisper paper, Appendix D,
  arxiv.org/abs/2212.04356): tiny 7.6, base 5.0, small 3.4, medium 2.9
  percent; English-only tiny.en 5.6, base.en 4.2, small.en 3.1, medium.en 3.1.
  On Spanish (Common Voice 9): tiny 30.3, base 19.6, small 10.3, medium 6.9
  percent. That Spanish column is the biggest reason to choose a larger Whisper
  if you dictate Spanish.
- **Distil-Whisper and large-v3**, average over short recordings the models
  were not trained on (the Distil-Whisper model card,
  huggingface.co/distil-whisper/distil-small.en): large-v3 8.4, distil-large-v3
  9.7, distil-medium.en 11.1, distil-small.en 12.1 percent. OpenAI publishes no
  figure for large-v3-turbo; it describes it as much faster than large-v3 with
  a small drop in quality.
- **Moonshine:** base 10.07 percent against tiny's 12.66, averaged over the
  Open ASR Leaderboard's English test sets (Moonshine AI,
  github.com/moonshine-ai/moonshine).

**What each is better at**, in plain words: the bigger models cope better with
accents, fast speech, a noisy room, names and long sentences; all of them put
in punctuation and capitals for you. For Spanish, any of the many-language
models beats the built-in tiny by a wide margin.

**When the built-in model is still the better choice:** on a computer with
4 GB of memory, when little memory is free, on battery, or when your screen
reader must never slow down. In our tests Moonshine tiny used 0.06 seconds of
computing per second of speech and at most 584 MB of memory; Parakeet Unified
used about four times the computing and twice the memory.

#### Nemotron or Parakeet: which should I try?

**For the fewest mistakes, try Parakeet.** On real speech it made fewer
mistakes than Nemotron, ran faster and used less memory, in English and in
Spanish. Nemotron is still the one to choose if you want to follow your words
while you speak.

Both are NVIDIA models of about 0.6 billion parameters, both are free, and
both run here on the processor alone, with your voice staying on your
computer. The difference is when they listen.

- **Parakeet** recognises each finished phrase after you pause. Nothing
  appears until you stop, and then the whole phrase is written at once. It
  writes punctuation and capitals itself, including question marks.
  - **Parakeet Unified 0.6B** is English only, and the model QUILL Lite
    recommends for English on a computer with 8 GB of memory and four cores.
    About 663 MB to download.
  - **Parakeet TDT 0.6B v3** knows English, Spanish and 23 other European
    languages. It is the recommendation for Spanish on 8 GB, and for English
    on 8 GB with two cores. About 670 MB.
- **Nemotron 3.5 ASR Streaming** recognises while you speak, in short slices.
  Its words appear in the status bar and on braille while you talk, and each
  phrase is written when you pause. It writes punctuation and capitals itself,
  and knows English and Spanish. It decides whether a sentence was a question
  once it hears the next one, so a full stop it wrote can turn into a question
  mark a moment later. About 682 MB.

What we measured on real speech (lower is better for every number):

| Model | Words wrong, English audiobooks | Words wrong, FLEURS English | Words wrong, FLEURS Spanish | Speed per thread | Peak memory |
|---|---|---|---|---|---|
| NVIDIA Parakeet Unified 0.6B | 3.2% | 6.3% | - | 0.21 | 1.2 GB |
| NVIDIA Parakeet TDT 0.6B v3 | 3.8% | 9.0% | 4.4% | 0.11 | 1.1 GB |
| NVIDIA Nemotron 3.5 Streaming 0.6B | 5.3% | 13.7% | 6.4% | 0.37 | 1.5 GB |

Parakeet Unified is English only, so it has no Spanish figure. Nemotron's
0.37 is over dictation's budget of 0.25 on one thread, which is why it is
Balanced and needs a computer with four or more cores.

**Rule of thumb:** for the fewest mistakes, try Parakeet; to follow your words
on braille or in the status bar while you talk, try Nemotron.

#### How to tell which is more accurate for you

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
the words), and run `python scripts/dictbench.py <folder> --model nemotron` in
a copy of QUILL's source. It prints the share of words wrong, which marks were
written, the speed, the memory and how long the model took to load.

### OpenAI dictation, with your own key

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

**What you need:** your own OpenAI key, saved in **Use My Own AI Key** (see
the AI help chapter). QUILL's free AI is never used for dictation. OpenAI
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
   model**. QUILL Lite asks OpenAI which speech models your key can use and lists
   them, newest first. The newest is already chosen.
5. Press **Enter** to close More Dictation Settings, and **Enter** again to
   save Dictation Settings.
6. Press **Ctrl+F11** and talk, just as before.

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

## While you dictate

### Knowing what dictation is doing

- **The status bar** has a **Dictation** part. It says Off, Listening, Hearing
  you, Writing, Spelling, or Waiting for wake phrase. With Nemotron or OpenAI
  it says Hearing and the words so far. Press F6 to reach the status bar and
  arrow to it. Press Enter there to start or stop dictation.
- **Tools > Dictation > Dictation On** is checked while dictation is writing.
- **The tones and the words** tell you when it starts and stops.
- **Dictation Status** (**Alt+F9**) tells you everything at once, in one
  sentence. See the next section.

### Dictation Status

Press **Alt+F9** (**Tools > Dictation > Dictation Status**) any time, whether
dictation is on or off, and QUILL Lite tells you in one sentence what
dictation is doing. Nothing changes; it only answers. For example:

- "Dictation is off. Moonshine, in English." when it is off, so you know what
  you will get when you press Ctrl+F11.
- "Dictation on, Whisper, in Spanish." while you are dictating. If capitals
  or no-space are switched on, or you are spelling, that is added, so you
  always know why your words are coming out the way they are. In command
  mode, it ends "Command mode.", so a braille display can show it too.
- "Waiting for the wake phrase, Quill dictate." when the wake phrase is
  listening.
- "Live transcript: 12 minutes, 1,840 words." while a live transcript is
  running.

It is the quickest answer to "is it still listening?" and "which language am
I in?", and it never moves your cursor.

### Seeing the words while you speak

With most engines, your words appear when you pause. With **Nemotron** (an
optional download, see "Better accuracy: optional speech models") or **OpenAI
dictation**, QUILL Lite knows the words while you are still saying them, and shows
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

### Where the words go

Your words go into the document you started dictation in, at the cursor. Each
phrase, with its punctuation and capitals, is one step for **Ctrl+Z**. So
"scratch that" and Ctrl+Z always take back the same thing, even when the
phrase replaced a selection. With the wake phrase, the words go into whichever
document is in front when you say it.

Your words go where you were when you started speaking. If you move the
cursor, or even switch to another window, while a phrase is still being
recognised, it is still written where you were speaking. Your cursor is put
back where you moved it, and you hear "Written where you started", with the
document's name if you were somewhere else by then. If that spot has changed
in the meantime, the words go at the cursor in that document instead, and you
are told.

After that, dictation stops by itself if you close that document, switch it
between plain and rich text, or speak while another program or a dialog is in
front. QUILL Lite tells you why it stopped.

There is only one microphone. So if dictation is running in one document and
you press **Ctrl+F11** in a second document, dictation moves there and tells
you: "Dictation moved to Letter.txt".

Dictation will not start in a document you cannot change, such as the
read-only copy Compare opens. You hear "This document is read-only, so
dictation cannot write here." and the microphone stays closed.

### Cancelling a phrase with Escape

While a phrase is being heard (the Dictation part of the status bar says
"hearing you"), press **Escape** to throw it away. Nothing is written, the
words heard so far go too, and you hear "Cancelled". Ctrl+F11 still stops
dictation and keeps what you said. When nothing is being heard, Escape does
what it always does.

### Dictating into Find, Replace and the AI question box

You can dictate into more than your document. Press **Ctrl+F11** in the Find
box, either Replace box, the question box of the AI pad, or the message box of
the AI Conversation window, and you dictate into that box. It uses the same engine and the same words, and Escape still
cancels a phrase. "New line" and "new paragraph" become a space in a one-line
box, and commands that move around a document do nothing there. Press Ctrl+F11
again to stop.

### Recent phrases

Press **Shift+F11** (**Tools > Dictation > Recent Phrases...**) to see the last
twenty phrases you dictated, newest first. Arrow to one and press **Enter**
(Insert Again) to write it at the cursor as one undo step, or press **Copy** to
put it on the clipboard. This is your rescue if "scratch that" took away one
phrase too many. When "choose", "replace" or "change that to" changed a
phrase, the words it had before are in the list too, marked "(before
correction)"; Insert Again and Copy leave that label out. This session's
phrases last only until you close QUILL Lite.

After them come words kept from before, so nothing you said is lost:

- **Not written**: a phrase that could not be written, or words held while
  dictation was paused. They stay on this computer, even through a crash,
  until you write or discard them, and QUILL Lite says once at start how many
  are waiting.
- **Review not finished**: the words of a review you closed without inserting.
- **Earlier**: with **Keep a dictation history** on in More Dictation Settings,
  the phrases from earlier days, newest first.

**Insert Again** writes one at the cursor and deletes it from the computer;
**Discard** (**Alt+D**) deletes it without writing it; **Clear History**
(**Alt+H**) deletes the whole history after asking, with No as the answer
unless you choose Yes. Kept words and the history are sealed for your Windows
account, never kept as sound, and never written to the log.

For example: you are dictating into a document, step away, and dictation
pauses with two phrases held because the window lost focus. Then the
computer restarts for an update. The next time QUILL Lite starts it says "2
dictated phrases were not written last time and are kept. Recent Phrases,
Shift+F11, brings them back." Press **Shift+F11**, arrow past this session's
phrases to the first "Not written" entry, and press **Enter**: it is written at
the cursor and deleted from the computer. Do the same for the second, or press
**Alt+D** to discard it.

Limits: only text is kept, never sound; the history keeps at most 2000
phrases; and a kept entry is deleted only when it is written, discarded or
cleared, never by copying it.

## Talking to the AI

You can have a spoken conversation with AI help. Open the **AI Conversation**
window (see "Having a conversation" in the AI help chapter). The cursor is
already in **Your message**.

1. Press **Ctrl+F11** and ask your question.
2. Pause. Your message is sent, and you hear "Working."
3. The reply is read aloud. While it is being read, the microphone does not
   listen, so the reply is never taken as your next message.
4. When the reply has been read, just carry on talking. If you want to speak
   before it has finished, press **Escape**: you hear "Listening." and you can
   talk straight away.
5. Press **Ctrl+F11** again when you are done.

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

## Live transcripts

Ordinary dictation is for writing: you speak, pause, hear your words, and
carry on. A live transcript is for **listening**: a lecture, a meeting, a
talk, a long voice memo you are speaking out loud. You start it, and QUILL
Lite writes down everything it hears until you stop it.

### Starting and stopping a live transcript

1. Press **Ctrl+Alt+Shift+PageDown** (**Tools > Dictation > Start or Stop Live
   Transcript**).
2. A new, untitled document opens, and the transcript is written into it.
   It never writes into the document you were working on.
3. Let it run. You can go back to your own document, or to another program
   altogether, and the transcript carries on.
4. To stop, press **Ctrl+Alt+Shift+PageDown** again, or **Ctrl+F11**. You hear
   how much was written, for example "Live transcript stopped, 1,840 words."

The very first time, you hear one sentence: "Please record other people only
when they have agreed." It is said once, and never again.

### How a transcript differs from dictation

A transcript is built to stay out of your way for an hour or more:

- **No commands.** Everything heard is written down as words. If the speaker
  says "scratch that", that is what goes in the transcript. The one thing
  that still works is your stop phrase.
- **No tone and no read-back** for each phrase, so nothing talks over the
  speaker or over you.
- **No wake phrase**, and it **never stops on silence**, so a quiet stretch in
  a meeting does not end it.
- **Filler words are left out**, and **automatic punctuation is on**, whatever
  you chose for dictation.
- **Paragraphs come from pauses.** When the speaker stops for four seconds or
  more, the next words start a new paragraph.
- **Time stamps, if you like.** Check **Time stamps in live transcripts** in
  More Dictation Settings, and each paragraph starts with the time in square
  brackets, like this:

      [10:42] Thank you all for coming. The first thing on the list is the budget.

### Working while it runs

The new words always go at the **end** of the transcript, wherever you are.
So you can go back into the transcript, read what was said a few minutes ago,
even add a note of your own in the middle, and your cursor stays where you put
it while the new words keep arriving at the bottom.

To check on it, look at the Dictation part of the status bar, which says
something like "Live transcript: 12 minutes, 1,840 words", or press **Alt+F9**
for Dictation Status, which says the same thing aloud.

### Keeping it

When you stop, the transcript stays open, untitled and not yet saved. Press
**Ctrl+S** to save it wherever you like. Until you do, QUILL Lite's usual
recovery protects it the same way it protects any document you have not saved
yet, so a power cut does not lose the meeting.

A live transcript listens to your microphone only. It cannot yet hear sound
your computer is playing, such as the other side of a video call coming
through your speakers; for a recording you already have, use "Transcribing an
audio file", below.

## Dictating into other programs

You can dictate into almost any program on your computer: an email, a web
form, a chat window, another word processor. This is called **Dictate
Anywhere**. It is done by another QuillVille program: **QUILL Transcribe**,
the family app made for exactly this, released on 1 November 2026, or **Quill
Inkwell**, the small program that also expands your abbreviations everywhere.

### What you need first

**QUILL Transcribe or Quill Inkwell must be installed.** Both are separate,
free members of the QuillVille family. When you press **Dictate in Other
Programs...**, QUILL Lite hands your settings to QUILL Transcribe if it is
running, or starts it if it is installed. Otherwise it hands them to Quill
Inkwell. If neither is on your computer, QUILL Lite tells you so: "Quill
Inkwell is not installed with this copy." Install one, then come back to these
steps.

**With QUILL Transcribe,** you hear "QUILL Transcribe has your dictation
settings. Use its start and stop key, or its tray menu, in the program you
want to dictate into." From then on, QUILL Transcribe's own user guide is the
one to read: it has its own keys, models and settings. The steps below are
for Quill Inkwell.

### Setting it up, step by step

1. In QUILL Lite, open **Dictation Settings** (**Alt+Shift+F6**) and set it up
   the way you like it: engine, microphone, language, pause and so on.
2. Press **More Dictation Settings...** (**Alt+A**).
3. Press **Dictate in Other Programs...** (**Alt+O**). Your settings are
   saved and handed over. If QUILL Transcribe is running or installed, it gets
   them and starts, and you hear "QUILL Transcribe has your dictation
   settings. Use its start and stop key, or its tray menu, in the program you
   want to dictate into." Otherwise Quill Inkwell gets them and starts, and you
   hear "Quill Inkwell is starting with your dictation settings. Choose the
   Dictate Anywhere key in its File menu."
4. If you have not chosen a key yet, Inkwell opens its key chooser for you.
   Choose a key you will remember and that no other program uses. You can
   change it later in Inkwell with **File > Dictate Anywhere Key...**.

Until you choose a key, there is none. Inkwell never takes a key on your
computer without asking.

### Using it

1. Go to the other program and put the cursor where you want the words.
2. Press your Dictate Anywhere key, speak, and pause. Each phrase is typed
   where the cursor is, just as if you had typed it.
3. Press the key again, or say "stop dictation", to stop.

You can also turn it on and off from Inkwell's own **Dictation** menu, with
**Dictate Anywhere**.

### What works there, and what does not

The engines, your own words and phrases, and most of what you can say all work
the same way they do in QUILL Lite:

- Punctuation and layout, like "comma" and "new paragraph".
- Spelling, "spell" and a word, capitals and no-space.
- Switching between English and Spanish.
- "Scratch that", which takes your last phrase back with Backspace, as long as
  you are still in the same window.

- Snippets, abbreviations and clips, from the lists QUILL and Inkwell share
  (QUILL's snippets, the shared abbreviation library, and QUILL's clips):
  "insert snippet" and its name, "insert abbreviation" and its name, and
  "paste clip" and a number. They are typed as one phrase, so "scratch that" takes all of it back. A snippet's
  blanks are asked for by voice first: you hear each blank's name, like
  "Title?", and say the answer; for a choice, say an option or "choose two".
  Say skip, scratch that to go back one, or cancel to type nothing. The
  cursor stays at the end.

Some commands need to read the text of the document, and Inkwell cannot read
another program's text. So "select", "go to", "correct", "select sentence",
"copy all" and "show clips" are answered with a sentence that starts "That
works in QUILL's own documents", and nothing is typed.

For your safety, Dictate Anywhere will not type into a password box. It also
will not type into a program running as administrator when Inkwell is not,
into QUILL Lite's or QUILL's own windows (use **Ctrl+F11** there, which does
much more), or into Inkwell's own window. Each time, you hear a sentence
saying why.

### It stays in the field you started in

Dictate Anywhere writes only into the field where you started. If the focus
moves to another field or another program while you are dictating, Inkwell
pauses and holds what you said, rather than typing it in the wrong place. You
then have three choices, in Inkwell's **Dictation** menu and, while dictation
is paused, in Inkwell's tray menu:

- **Resume** goes back to the field you started in.
- **Resume in This Field** writes the held words where you are now.
- **Discard Held Words** throws the held words away.

If you choose Resume in This Field from Inkwell's own window or tray menu,
Inkwell waits for you to switch to another program and resumes there. Choose
it again to cancel.

### Programs dictation never types into

Some programs should never receive dictation at all, such as your password
manager. Press **Programs Dictation Never Types Into...** (**Alt+N**) in More
Dictation Settings to see and change that list. It starts with the common
password managers and the Windows sign-in, lock and administrator prompts. If
you dictate into one of them, you hear something like "Dictation does not
type into KeePass. Move to another program." and nothing is typed. Programs
are matched by their file name, like keepass.exe, never by the title of a
window.

- To remove a program, choose it in the list and press **Delete**, or press
  **Remove**.
- To add the program you were just using, go to it, come back to QUILL Lite,
  open the settings again, and press **Add Front Program**. The button says
  which program it will add.
- To add a program by name, type its file name in **Program file name** and
  press **Enter**, or **Add by Name**. You can leave off .exe: "KeePass" adds
  keepass.exe. A name you typed but did not add is kept when you press OK.

The list is saved when you press OK in Dictation Settings.

### What you hear

In other programs, your screen reader already says each character as it is
typed, so Inkwell starts with a **tone only** after each phrase, rather than
reading the words back as well. You can change that.

Inkwell keeps its own copy of your dictation settings. To change them, open
Inkwell's **Dictation** menu and choose **Dictation Settings...**. It is the
same window you know from QUILL Lite. Or set things up in QUILL Lite and press
**Dictate in Other Programs...** again to hand them over once more.

Inkwell uses the **My Words and Phrases** list that the full QUILL editor
keeps, so if you also use QUILL, a name you taught it there comes out right in
your email too. Check **Use the shared word list** in My Words and Phrases, and
the words you teach QUILL Lite are used there as well. Dictate Anywhere is off in Safe Mode.

### One microphone at a time

QUILL Lite, QUILL, QUILL Transcribe and Quill Inkwell never listen at once, so
the same words are never written twice. The microphone belongs to whichever
started dictating first, until it stops.

- If QUILL Transcribe is listening when you press **Ctrl+F11**, QUILL Lite does
  not open a second microphone. You hear its key, for example "QUILL
  Transcribe is listening. Press Alt+Shift+Backslash to stop it, then try
  again."
- If QUILL is dictating, you hear "QUILL is dictating. Press Ctrl+F11 in QUILL
  to stop it, then try again."
- If you press QUILL Transcribe's key while QUILL Lite is dictating, QUILL
  Transcribe says "QUILL Lite is dictating. Press Ctrl+F11 in QUILL Lite to
  stop it, then try again."

QUILL Transcribe waiting in the tray does not hold the microphone, so
**Ctrl+F11** works as usual. The microphone is let go when dictation stops,
when it stops because something went wrong, when you close QUILL Lite, and if
QUILL Lite ever closes unexpectedly.

QUILL Transcribe and Quill Inkwell do not type into QUILL Lite's window. If you
press their key there, you hear "This is a QUILL window: press Ctrl+F11 to
dictate here."

## Transcribing an audio file

Sometimes the words you want are already in a recording: a voice note from
your phone, an interview, a lecture, a meeting somebody recorded for you. QUILL
Lite can listen to the recording and write down what was said, using the same
speech engines you dictate with. It works in the background, so you can keep
writing while it listens, and it tells you when it is done.

### Your first transcription, step by step

1. Press **Shift+F5**, or choose **Tools > Dictation >
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
5. There is no output-location choice. QUILL Lite saves the finished transcript
   privately. Activate its completion notice in **Notifications** to open it in
   a new document; it does not insert text into the document you were editing.
6. Press **Enter**. You hear "Transcribing meeting.mp3 in the background."
7. Carry on with whatever you were doing. The status bar shows how far it has
   got, and every quarter of the way you hear it quietly: "meeting.mp3: 25
   percent". When it is done you hear one sentence, such as "Transcribed
   meeting.mp3: 12 minutes, 1,804 words, in 6 minutes, in a new document."

That is all there is to it. The rest of this section explains the choices.

### What the text looks like

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

### Which model for which recording

The **Speech model** list shows every model on your computer, most accurate
first: the two that come with QUILL Lite, and any you downloaded in Dictation
Settings, Speech Models (see "Better accuracy: optional speech models"
earlier in this chapter). Here is how to choose:

- **Voice notes and dictated letters.** One clear voice, close to the
  microphone. **Moonshine tiny** is built in, is the fastest by far, and does
  this well. Whisper tiny is the one to try if Moonshine mishears an accent.
- **Interviews and meetings.** Several voices, people interrupting, someone
  further from the microphone. A downloaded model is worth it here. In
  English, **NVIDIA Parakeet Unified 0.6B** is our first choice: in our tests
  on real recordings it made the fewest mistakes of any model that keeps up,
  3.2 percent of words wrong where the built-in Moonshine got 6.5. **Parakeet
  TDT 0.6B v3** is close behind and quicker still. Whisper small is good too,
  just slower.
- **Lectures and talks.** One voice, a long time, and plenty of special words.
  Parakeet again. Before you start, add the speaker's names and terms to My
  Words and Phrases, and you will spend less time correcting.
- **Noisy rooms and harder voices.** A café, a car, a hall with an echo. On
  the harder LibriSpeech recordings, Parakeet Unified got 3.2 percent of words
  wrong, Parakeet TDT 0.6B v3 5.2, and the two built-in tiny models over 13.
  OpenAI is very good with noise too, if you use your own key (see below).
- **Spanish.** Choose Spanish as the language first. **Parakeet TDT 0.6B v3**
  made the fewest mistakes in Spanish, 4.4 percent of words on FLEURS Spanish
  where the built-in Whisper tiny got 30.5. Whisper small and Nemotron were
  next. The list shows only the models that know the language you chose.
- **Models removed in this release.** Distil-Whisper small.en, Whisper
  small.en, Distil-Whisper medium.en, Whisper medium.en and Distil-Whisper
  large-v3 are no longer in the list. Parakeet Unified did better than each
  of them.

A model that is too slow for live dictation is fine for a recording: nobody is
waiting at the end of each sentence. The estimate tells you the wait before you
start.

### How long it takes

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
QUILL Lite is developed on, plus a few seconds the first time while the model
loads.

Transcribing uses two of your processor's cores, the same as dictation, so
your screen reader stays quick. The model is put away a few minutes after the
last transcription finishes, which gives its memory back.

### Where the text goes

- **Saved privately until you open it.** When transcription finishes, the
  transcript is saved without changing the document you were editing. Activate
  the completion notice in **Notifications** to open it in a new document; the
  Transcribe a Recording window has no destination picker.

### Several recordings, checking on it, and stopping

- **Several at once.** In Browse, hold **Ctrl** and choose more than one file.
  They are transcribed one after another with the same choices, and each one
  is saved with its own completion notice in **Notifications** when it
  finishes. If one is already running
  when you start another, you hear "Added to the queue".
- **How far has it got?** Press **Shift+F5** again. At the top of the window,
  **Transcribing now** says which recording it is on, how far it has got, and
  how many are waiting. Press **Escape** to close the window and let it carry
  on.
- **Stopping.** In that same window, press **Stop Transcribing** (Alt+S). The
  recording being transcribed stops, any waiting ones are forgotten, and
  nothing is written into a document.
- **If you missed the result sentence.** **Shift+F9** opens Activity, which
  keeps the transcription outcome and any failure reason for this session.
  To open the saved transcript, activate its completion notice in
  **Notifications**.

### Which files it can read

MP3, M4A, AAC, WAV, Ogg, Opus, FLAC and WMA, and also the sound in an MP4 file
and AIFF. QUILL Lite reads all of them itself, using parts of Windows that are
already on your computer, so there is nothing extra to download and no other
program to install. Files with copy protection, such as some bought audiobooks,
cannot be read.

### Privacy, and OpenAI with your own key

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

### Messages you might hear

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

## When something goes wrong

### If the microphone drops

If the microphone is unplugged, a Bluetooth headset drops out, or the sound
goes completely silent for a few seconds, you hear "The microphone stopped.
Dictation is paused and will resume when it comes back." Dictation stays on,
writes nothing, and waits for the microphone. When it comes back you hear
"Microphone back. Listening." and you carry on. Meanwhile, the Dictation part
of the status bar says "paused, microphone lost".

If the speech engine itself stops answering, QUILL Lite quietly restarts it
once, and you will not notice. If it fails again, dictation stops and tells
you, for example "Moonshine stopped working. Try Whisper in Dictation
Settings."

### On a modest computer

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

### Messages you might hear

Dictation always tells you what happened and what to do. These are the usual
ones:

- **No microphone was found.** Connect one and press Ctrl+F11 again.
- **The microphone you chose is not connected.** Plug it in, or choose another
  one in Dictation Settings.
- **The microphone could not be opened.** In Windows Settings, go to Privacy
  and security, then Microphone, and make sure desktop apps are allowed to use
  it.
- **A speech engine is not included in this copy.** Choose another engine in
  Dictation Settings. Reinstalling QUILL Lite puts the missing one back.
- **With Windows speech recognition: no speech recogniser is installed.** Add
  a speech language in Windows Settings, under Time and language, then Speech.
- **"This document is read-only, so dictation cannot write here."** Dictate
  into a document you can type in.
- **"Moonshine stopped working. Try Whisper in Dictation Settings."** The
  engine failed twice in one session. The first time, QUILL Lite restarted it
  for you without a word. Choose the other engine, and if it keeps happening,
  write to support.
- **"Written where you started."** You moved while a phrase was being
  recognised, and it went where you were speaking. Nothing is wrong.
- **"This computer is busy, so dictation switched to the faster built-in
  engine for now."** See "On a modest computer" above.
- **OpenAI's messages** are listed in "OpenAI dictation, with your own key".

### If it keeps mishearing you

- Try Whisper instead of Moonshine, or the other way round.
- Try a downloaded model; see "Which engine should I choose?".
- Use a headset microphone instead of a laptop's built-in one.
- If you are using speakers, set the read-back to a sound only.
- Add names you use often to **My Words and Phrases**.

### Turning dictation off completely

Dictation is on in every profile except WordPad and Notepad. You can switch it
off in **Customize Features** like any other area. That removes the menu, the
keys and the wake phrase.

## Dictating well

Dictation gets much better with a few good habits. None of this is hard, and
most of it you only set up once.

### Your microphone and your room

- **A headset microphone beats anything else.** A microphone that sits a
  finger's width from the corner of your mouth hears you clearly and hears the
  room hardly at all. A laptop's built-in microphone hears the fan, the
  keyboard and the television.
- **Keep it in the same place.** Too close and your breath pops; too far and
  you sound thin. Find a spot and leave it there.
- **Use Test Microphone** in Dictation Settings once, when you first set up.
  If it says "quiet", move the microphone closer or turn up its level in
  Windows. If it says "very loud", the other way.
- **Too quiet, and it may not hear you at all.** With the level set very low,
  or speaking very softly or far away, dictation can miss a whole sentence,
  especially just after something louder. In our tests with very quiet
  recordings it missed some entirely.
- **Quieten the room if you can.** Close a window, turn off music, move away
  from a humming fridge. Bigger models cope better with noise, but nothing
  copes as well as quiet.

### How to speak

- **Speak the way you would to a friend across the table**: a normal pace and
  a normal voice. Shouting and slowing right down both make recognition worse,
  not better.
- **Say a whole thought, then pause.** A sentence or two at a time works best.
  The engine uses the words around a word to work out what you meant, so a
  full sentence comes out better than one word at a time.
- **Think first, then speak.** If you need to stop and think in the middle,
  that is fine, but it helps to know roughly what you will say before you
  start.

### Choosing the pause

The pause is how long you have to be quiet before a phrase is written.

- **Normal** suits most people.
- If dictation keeps writing half your sentence while you are still thinking,
  choose **Long**.
- If you take long breaks in the middle of a sentence, or you are still
  getting used to dictating, try **Longer (2 seconds)**.
- Choose **Longest (3 seconds)** only if Longer still cuts you off. Your words
  arrive a little later, but you have plenty of room.
- If you are quick and fluent and the wait feels slow, try **Short**.

Remember that a phrase ending on a word like *the* or *very* waits for the
rest of the sentence anyway; see "Longer pauses, and sentences you finish
later".

### Punctuation habits

- **Let the engine do the ordinary marks.** Moonshine, Whisper and the
  optional models put in full stops, commas and question marks for you. Talk
  naturally, and pause at the end of a sentence.
- **Say a mark when it matters.** A comma in a list, a colon before a list, a
  question mark on a question that does not sound like one. What you say
  always wins.
- **Say "new paragraph" between paragraphs.** A pause alone never starts one.
- **Listen to the read-back.** With **Say punctuation marks in the read-back**
  checked, you hear "comma" and "period" where they went in, so you know
  straight away whether your sentence is punctuated the way you wanted.

### Fixing mistakes: the correction loop

You do not have to reach for the keyboard to fix most mistakes. Work through
these from the top, and stop at the first one that does the job:

1. **"Scratch that"** takes back the phrase you just said. Then say it again,
   a little more clearly. This is the quickest fix of all.
2. **"Correct" and the wrong word** fixes something further back: "correct
   Tuesday", then "Thursday". Or **"select"** and the words, then say what
   should be there instead. See "Moving and selecting by voice".
3. **"Spell that"** is for a name the engine will never get: the last phrase
   is selected and you spell it out. See "Letters, numbers and symbols".
4. **Recent Phrases** (**Shift+F11**) is your rescue if you scratched one
   phrase too many. Arrow to the phrase and press Enter to put it back.
5. **Tidy Dictated Text** (**Ctrl+F3**) is for the end, not the middle. When
   you have dictated a long passage, select it and let the AI tidy the small
   slips all at once. Your My Dictation Instructions, and your Dictation
   Context for This Document, tell it how you like your writing.

And when the same word goes wrong again and again, stop fixing it and teach
it: add it in **My Words and Phrases** (**Alt+Shift+F10**), and it comes out
right from then on.

### With your screen reader running

Two voices can tell you about your words: QUILL Lite's read-back, and your
screen reader.

- **QUILL Lite's read-back** says the whole phrase once it is written, with
  its punctuation. It waits a quarter of a second so your screen reader can
  finish first. This is usually the most useful.
- **Your screen reader** may also say the words as they appear, if it is set
  to echo typed text or to read new text in the document. If you hear
  everything twice, turn one off. Many people keep QUILL Lite's read-back and
  turn the screen reader's typing echo down while dictating; others set
  "After each phrase is written, give me" to a sound only and listen to the
  screen reader instead.

**Use headphones.** Through speakers, the microphone can hear the read-back,
or your screen reader, and write it down a second time. If you must use
speakers, set the read-back to a sound only, and keep the screen reader's
voice down while you dictate.

### Choosing a model

- **Start with Moonshine**, the one QUILL Lite comes with. For most voices it
  is quick and accurate.
- **If it mishears your accent or your microphone**, try **Whisper**, which
  also comes with QUILL Lite.
- **For more accuracy**, download one of the optional models (see "Better
  accuracy: optional speech models"). The **Recommended for this computer**
  line in Dictation Settings names the one that suits your computer. On real
  speech, Parakeet made the fewest mistakes; try Nemotron if you want to
  follow your words on braille while you talk.
- **If your model was removed in this release**, dictation now uses Parakeet
  Unified if you had already downloaded it, or the built-in model if not. To
  choose Parakeet Unified, see "Better accuracy: optional speech models".
- **Judge with your own voice.** Use one model for a day, then another, and
  keep the one that needed fewer fixes.

### Dictating in Spanish

- In Spanish, the built-in choice is Whisper, and a larger model makes a big
  difference: on real Spanish speech the built-in Whisper got 30.5 percent of
  words wrong and Parakeet TDT 0.6B v3 got 4.4. If you dictate a lot of
  Spanish and have 8 GB of memory, Parakeet TDT 0.6B v3 is well worth the
  download.
- Let automatic punctuation do the marks. The Spanish punctuation words only
  work when it is off, or with Windows speech recognition.
- Switch with **Ctrl+Shift+F11**, or say "switch to Spanish" and "cambiar a
  inglés". Dictation Status (**Alt+F9**) tells you which you are in.

### On a modest computer

- **Moonshine is the kindest** to an older computer, and it is what you start
  with. It uses very little of the processor, so your screen reader stays
  quick. On 4 GB of memory, the built-in Moonshine and Whisper are the ones
  QUILL Lite recommends, because the larger downloads do not fit beside a
  screen reader there.
- **Close what you are not using** while you dictate, especially a web browser
  with many pages open.
- **Leave the big models for recordings.** A model too slow for live
  dictation is fine for Transcribe a Recording (**Shift+F5**), where nobody is
  waiting at the end of each sentence.
- If an optional model falls behind, QUILL Lite moves to Moonshine for now
  and tells you. Nothing is lost.

### Two short paragraphs to practise on

Put the cursor in a new, empty document, press **Ctrl+F11**, and try these.
Pause where you see a full stop. Say the marks in quotation marks as words.

**Practice one: punctuation.** Say:

> The book club meets on Thursday "comma" in the library "period" Please bring
> your copy "comma" your questions "comma" and a friend "period" "new
> paragraph"

What should come out:

> The book club meets on Thursday, in the library. Please bring your copy,
> your questions, and a friend.

You should hear the read-back say the commas and full stops, and the new
paragraph. If a comma is missing, say "scratch that" and say that phrase
again.

**Practice two: fixing a name.** Say:

> My neighbour Siobhan grows tomatoes and beans "period"

Listen to the read-back. The engine may well write the name some other way,
say *Shivon*. If it does, say "correct Shivon" (whatever you heard), then
"spell capital sierra india oscar bravo hotel alpha november". What should
come out:

> My neighbour Siobhan grows tomatoes and beans.

Now add Siobhan in **My Words and Phrases**, scratch the sentence, and say it
again. This time the name should come out right first time.

### More practice: the tutorials

Help > Tutorials (**Ctrl+Alt+F1**) has five short dictation lessons in the
*Working in a document* track, beside *Write by talking*. Each takes a few
minutes and tells you what you should hear when you got it right:

- *Punctuation and symbols by voice*: saying marks, starting a heading and a
  list, and spelling a web address.
- *Fix a word by voice*: selecting and correcting a word you said, and
  spelling a name.
- *Snippets and clips by voice*: copying, pasting a Copy Tray slot, and
  putting in a snippet.
- *Switch to Spanish and back*: the language key and the voice commands.
- *Make a live transcript*: starting one, asking how it is going, and
  stopping and saving it.

## What you learned, and where to go next

You can now dictate with **Ctrl+F11**, pressing it to start and again to
stop, or holding it while you talk once you turn that on. You can fix what you said with "scratch that" or "correct that",
spell a hard name, and start and stop by voice with the wake and stop phrases.
You know that your words go where you started speaking, how to see them while
you talk with Nemotron or OpenAI, and how to talk to the AI out loud. You also
know where to teach dictation your own words, what OpenAI dictation sends and
how to turn it on or off, and what to do when the microphone or the engine has
trouble. And with **Shift+F5** you can turn a recording into text in the
background, with whichever model suits it.

You can also hear the punctuation that went in, spell an address and type
Markdown marks by voice, select, go to and correct any words you can see, and
reach your clips and snippets without the keyboard. You can switch between
English and Spanish with **Ctrl+Shift+F11**, give yourself a longer pause,
tell dictation what a document is with **Ctrl+Alt+Shift+PageUp**, and ask
what it is doing with **Alt+F9**. A live transcript
(**Ctrl+Alt+Shift+PageDown**) writes down a whole meeting, and Quill Inkwell
lets you dictate into other programs.

To practise with QUILL Lite beside you, open **Help > Tutorials...**
(**Ctrl+Alt+F1**) and choose "Write by talking", and then the five newer
dictation lessons listed in "More practice: the tutorials". Keep the **Dictation commands** file (dictation-commands.md)
document handy too, or say "what can I say" while you dictate. To change the
tones you hear, see *Sounds* in Chapter 8.

Next, Chapter 10, AI help, covers the AI pad, including Tidy Dictated Text,
which cleans up a long dictated passage, and My Dictation Instructions, which
tell it how you like your writing.

---

- Previous: [Chapter 8: What you hear](lite-guide-08-what-you-hear.html)
- Next: [Chapter 10: AI help](lite-guide-10-ai-help.html)
- [Contents](../userguide.html)
