# QUILL Lite 1.2

*Version 1.2.0, released October 3, 2026.*

Welcome to QUILL Lite 1.2. This is the release about words. QUILL Lite now has
a thesaurus that finds the word you are really on, a dictionary that works
without AI, and an AI dictionary that reads your word in its own sentence and
tells you whether it is the right one.

It is also the release about knowing what happened. QUILL Lite keeps a list of
everything it has told you, F9 says the last important thing again, and if
something goes wrong while you are busy elsewhere, it waits for you rather
than slipping past.

Everything works from the keyboard and tells you how it went, the way the rest
of QUILL Lite does.

## Coming from 1.1

If you read the QUILL Lite 1.1 notes, you may remember a list of things coming
in 1.2.0. They are all here, and a few more besides. Your settings, recent
files and recovered work come with you exactly as they are, and **Help >
Check for Updates** (**Ctrl+Alt+U**) offers 1.2.0 like any other update.

One key has moved. **Tools > Keyboard Manager** is now
**Ctrl+Alt+Shift+Space**. Its old key, Ctrl+Alt+Shift+R, shows and hides Quill
Radio from anywhere, so while Quill Radio was running the Keyboard Manager
never opened. QUILL moved its Keyboard Manager to the same key, so the two
still match.

## Try this first

1. Put the cursor on a word you are not happy with and press **Shift+F7**.
   Arrow through the meanings, press **Tab** to reach the words, and press
   **Enter** on one you like. It goes into your sentence in the right form.
2. On another word, press the **Applications** key. You find two new
   submenus, **Thesaurus for** that word and **Dictionary for** that word.
3. Press **Alt+F10** for **Look Up Word**. It works without the internet, and
   tells you more if you let it go online.
4. Press **Ctrl+,** for Preferences and type "spelling" in **Find a setting**.
   Press Down, then Enter, and you are on that setting.
5. Press **Shift+F9** for **Activity**, the list of everything QUILL Lite has
   told you since you opened it. Press **F9** any time to hear the last
   important thing again.

## Finding the right word

### The thesaurus

Press **Shift+F7**, the same key as in Word and QUILL, or choose
**Tools > Thesaurus**. It opens on the word you are on.

A thesaurus lists plain forms of words, *run* rather than *running*. QUILL
Lite works your word back for you, so "running" finds "run", "happier" finds
"happy" and "stopped" finds "stop", and it tells you so. Then it puts your
choice back in the form your sentence needs. Choose *sprint* for *running* and
you get *sprinting*. Choose *glad* for *Happier* and you get *More glad*,
capital letter and all.

It is the same thesaurus QUILL uses, and it comes inside QUILL Lite. Nothing
is downloaded and nothing is sent anywhere.

Want the short version without a window? **Say Word Summary**
(**Ctrl+Alt+Shift+[**) tells you what the thesaurus knows about a word: how
many meanings it has, the first few replacements, and its opposites.

### Look Up, the dictionary without AI

Press **Alt+F10**, or choose **Tools > Look Up Word**. Offline, you get
synonyms, opposites and related words from the word list inside QUILL Lite.

Tick **Use online sources** and you also get definitions with examples, more
words, rhymes and a short Wikipedia summary. Only the word is sent, never your
sentence or your document, and only after you tick the box. QUILL Lite
remembers your choice.

Press **Enter** on a word to put it in place of yours. **Add to Dictionary**
teaches a word to your spell checker.

### The AI dictionary

A thesaurus knows every meaning of *bank*. It cannot tell which one your
sentence means. **Tools > Dictionary** can, because it sends the word and the
sentence it is in (never the rest of your document) and answers in plain words
written to be listened to.

There are twelve questions to ask, each with a key of its own:

- **Define in Context** (**Ctrl+Alt+Shift+'**) says what the word means here.
- **Synonyms That Fit**, **Simpler Word**, **More Formal Word** and **More
  Vivid Word** offer replacements that suit this sentence.
- **Is This the Right Word?** settles affect or effect, complement or
  compliment.
- **Opposites**, **Use It in a Sentence**, **Where It Comes From**, **How to
  Say It** and **Rhymes** do just what they say.
- **Word Explorer** (**Ctrl+F10**) does them all at once.
- **Find the Word For** (**Ctrl+Alt+Shift+]**) is the other way round: you
  describe the meaning, and it suggests the word you are reaching for.

When an answer offers words, Tab to **Choices** and press Enter, or choose
**Use This Word**. It goes into your document as one step, and one Ctrl+Z
takes it back.

The AI dictionary needs your ChatGPT subscription or your own AI key. It does
not use QUILL's free AI service, because a dictionary gets asked many times a
day and would use up the free allowance quickly.

### Checking your word lists

**Tools > Spelling > Dictionary Status** (**Alt+Shift+;**) tells you how many
words your personal dictionary and this document's own list hold, where each
file is kept, and whether the thesaurus is there.

If you would rather not have any of this, turn off **Dictionary and
thesaurus** in **Tools > Customize Features** (**Ctrl+Alt+F10**). It is on to begin with, and off
in the WordPad and Notepad profiles.

## AI help with a Google Gemini key

**Use My Own AI Key** (**Alt+F2**), which used to be called Use My Own OpenAI
Key, now opens on a **Provider** list: OpenAI or Google Gemini. Choose one,
paste that company's key, and everything follows your choice: where your text
goes, which models you can pick, and what they cost. QUILL Lite never guesses
from the key or the model name.

You can keep both keys saved and switch with the Provider list. With a Gemini
key, **Ask About an Image** (**Ctrl+F5**) works too, and so do the AI
dictionary and Tidy Dictated Text.

If you use your ChatGPT plan in more than one Quill app, each app now keeps
its own sign-in. Signing out of one leaves the others signed in, and **Use My
ChatGPT Subscription** (**Alt+F5**) tells you when another app on this
computer is already signed in, so signing in here is one Allow in your
browser.

## Knowing what happened

### Activity and Repeat Last Result

**Help > Activity** (**Shift+F9**) lists everything QUILL Lite has told you
since you opened it, newest first. Each row offers what you can do about it:

- **Retry** tries the same thing again.
- **Open Folder** shows you the file in File Explorer.
- **Copy Details** copies the row, ready to paste into a message to support.

If work finishes after you closed the window that started it, the result
lands here instead of being lost. A large file you opened while you were busy
elsewhere is here too, as Opened or Could not open.

**Help > Repeat Last Result** (**F9**) says the last important thing again.
That is QUILL Lite's own last message, not the last thing your screen reader
read. Both keys do the same in QUILL, Quill Radio and QUILL Cast.

### When your settings cannot be saved

Sometimes Windows will not let QUILL Lite save your settings, perhaps because
the disk is full. Now you are told once, with the reason. Your choices keep
working for the rest of the session, the warning stays in the status bar's
Message cell, and Activity offers Retry. When a later save works, you hear
that too. Preferences no longer says "saved" when it was not.

## Finding a setting

Preferences (**Ctrl+,**) has a **Find a setting** box at the top. Type a word,
press **Down** to reach the matches, and press **Enter** on one to go straight
to it. **Ctrl+F** takes you back to the box. Searching never changes a
setting, and OK and Cancel work just as before. Quill Radio and QUILL Cast
have the same box in their Preferences.

## Making QUILL Lite your text editor

Every QUILL Lite install now tells Windows that QUILL Lite can open text,
Markdown, rich text, HTML and CSV files. It takes nothing over. QUILL Lite
simply shows up in **Open with**, and in Windows Settings under Default apps,
where you choose which app opens what. The Custom install's checkbox for
opening .txt and .rtf files is gone, because there is nothing left to ask.

Open Preferences (**Ctrl+,**) and look under **Windows and your files**. A
line there tells you what opens in place of Notepad right now.

The **Make QUILL Lite My Text Editor...** button takes you the rest of the way.
It explains what Windows lets an app do and what you choose, then opens the
Default apps page for QUILL Lite. Choose .txt, pick QUILL Lite, and choose Set
default. It works from a portable copy too.

Some programs still open Notepad by name. If you would like QUILL Lite to open
for those as well, check **Open QUILL Lite instead of Notepad** and press OK. It
is off to begin with. It changes Notepad for everyone on the computer, so
Windows asks for administrator approval, and clearing the box puts Notepad
back. On Windows 11, QUILL Lite also shows you where to turn off the newer
Notepad's app execution alias. Uninstalling QUILL Lite puts Notepad back for
you.

QUILL for All has both of these too, in its own Settings. Only one program can
open in place of Notepad, so if QUILL already does, QUILL Lite tells you before
it takes over, and QUILL does the same.

## Choose Stable, Beta or Dev

New in this version: **Release Channel...**, on the Help menu. Every copy
stays on **Stable**, the version we check with JAWS and NVDA, unless you choose
otherwise. **Beta** gets new features a few weeks early; **Dev** is the work in
progress, for testers.

Arrowing through the three only explains them. If you choose Beta or Dev, a
short warning says plainly what could go wrong and how to come back, and
nothing moves until you tick **I understand** and choose **Move**. Before it
moves, QUILL Lite saves a copy of your settings, keys and recent files list. Your documents are not copied, and updates don't change them.

Coming back to Stable is safe. If Stable can read everything you have saved,
QUILL Lite offers to go straight back. If it can't yet, QUILL Lite says so plainly and
lets you either wait for Stable to catch up (it moves you across by itself), or
go back to the copy of your settings saved when you joined. A copy of how things
are right now is saved first, so nothing is thrown away.

On Beta and Dev, QUILL Lite downloads new versions in the background so they are
ready when you are, and never installs one without asking. It waits on a
metered connection, during Quiet Hours, and while Quill Radio is recording.

Quill Radio and QUILL Cast share one engine with QUILL Lite on your computer. When one of you moves
to Beta or Dev, it gets its own copy of the engine, so the apps you leave on
Stable are never touched. That copy uses about 335 MB of disk space until your
last app comes back to Stable.

If an update ever fails to start, it undoes itself, puts back the version you
had, and tells you so the next time QUILL Lite opens. The window's **Update
History** button shows everything the updater has done.

Help > About now shows a build number after the version: this release is
1.2.0 (build 1). If a fix comes out without a new version number, it is a
newer build, and Check for Updates offers it to you.

## Dictating in Spanish

New, and ready for you to try: you can dictate in Spanish. Open Dictation
Settings (**Alt+Shift+F6**), choose **Spanish** under **Dictation language**,
and press Enter.

- Your words come out in Spanish, accents and all, using Whisper's
  multilingual speech model. It comes with QUILL Lite, so nothing is
  downloaded.
- The commands stay in English for now. "Scratch that", "new paragraph" and
  the rest work as they always have. Spanish commands come next, once a native
  speaker has checked them.
- With automatic punctuation on, Whisper punctuates for you. Turn it off and
  you can say the Spanish words instead: "coma", "punto", "punto y coma",
  "dos puntos", "abrir interrogación", "cerrar interrogación" and more.
- The wake and stop phrases become "Quill dicta" and "deja de dictar".

QUILL has the same thing, in the same place. The user guide's "Dictating in
Spanish" has the whole list. If something comes out wrong, tell us through
**Help > Get Help from Support**. We're keen to hear how it goes.

## Better accuracy: optional speech models

Dictation works the moment you install. If you want more accuracy, you can
now download a larger model: the same local models VS Code offers for its own
dictation, plus the rest of the Whisper family.

Open Dictation Settings (**Alt+Shift+F6**) and press **Better Accuracy:
Speech Models...** (**Alt+B**). The list starts with our suggestion, NVIDIA's
**Nemotron 3.5 ASR Streaming** (VS Code's default), then NVIDIA's two
**Parakeet** models, **Whisper** small, base and tiny, the rest of Whisper from
base.en to large-v3, and a lighter **Moonshine base**. Each one says what it is
good for, how big it is, which languages it knows, which computers suit it and
whether yours should keep up.

- Nothing downloads until you press **Download...** and say yes to a question
  that names where it comes from, its size, its licence and where it will be
  saved. On a metered connection you are asked first.
- They are free and run on your computer's processor; no graphics card
  needed. Your voice never leaves the computer.
- A download you cancel carries on later from where it stopped, every file is
  checked before it is used, and **Remove** frees the space.
- QUILL and QUILL Lite share the models on the same computer. In a portable
  copy, models are saved inside the portable folder, so everything travels
  together.
- Moonshine stays the engine until you choose another. If a downloaded model
  goes missing, dictation tells you in one sentence and uses the built-in one.

The user guide's "Better accuracy: optional speech models" has every model's
published accuracy, what we measured, and "Nemotron or Parakeet: which should
I try?".

## Dictation that keeps up with you

Dictation learned a lot this time, much of it from studying how VS Code does
it. Everything here is in QUILL too, on the same keys.

- **Hold Ctrl+F11 to talk.** Hold the keys down, say what you want, and let
  go: your last phrase is written and dictation turns off. A quick press still
  turns it on and leaves it on. If holding keys is hard for you, turn it off in
  **More Dictation Settings**.
- **Stopping never cuts you off.** Press or let go of Ctrl+F11 while you are
  still finishing a sentence, and that phrase is written before dictation
  stops.
- **See your words while you speak.** With Nemotron or OpenAI, the words heard
  so far show in the status bar and on a braille display as you talk, and the
  final words go in when you pause. Nothing is spoken unless you ask for it,
  so nothing talks over you. Nemotron's questions now end with a question
  mark.
- **Your words go where you started.** Move the cursor, or even switch
  windows, while a phrase is being recognised, and it still goes where you
  were speaking. You hear "Written where you started".
- **"Correct that."** With Windows speech recognition, say "correct that" to
  hear its other guesses, then "choose two" to swap one in.
- **Talk to the AI.** Press Ctrl+F11 in the AI Conversation window and ask
  out loud. Your message is sent when you pause, the reply is read aloud, and
  the microphone waits until the reading is done. Dictation uses its own
  Talking to AI settings there by itself.
- **OpenAI dictation, with your own key.** If you have your own OpenAI key,
  you can choose OpenAI as the speech engine. It is off until you choose it,
  it asks you first in plain words, and it says exactly what is sent: your
  speech goes to OpenAI and is billed to your account. You pick the model from
  OpenAI's own current list. Your computer's own engines stay the default.
- **My Dictation Instructions** tell Tidy Dictated Text (**Ctrl+F3**) how you
  like your writing: "write numbers as digits", "British spelling".
- **Kinder to an older computer.** Speech models are put away a few minutes
  after you stop dictating, giving their memory back, and an optional model
  that cannot keep up hands over to the built-in engine and tells you why.

**More Dictation Settings...** (**Alt+A** in Dictation Settings) holds the new
choices. The user guide's chapter on writing by voice has a section for each,
and there is a new lesson, "Write by talking", in **Help > Tutorials...**.

## Your recent documents, one key away

New: press **Alt+Shift+0** (or choose **File > Recent Documents...**) to see
every document you opened recently, newest first, and press Enter on the one
you want. The list was always there, under **File > Open Recent**, but it was
easy to miss. Now it has a key and a window of its own.

- **Pin** the documents you come back to, and they stay at the top however many
  others you open.
- **Remove from List** takes one off. The file is not touched.
- **Open Containing Folder** shows the file in File Explorer.
- **Clear Unpinned...** empties the list after asking. Pinned documents stay.
- Choose how many documents to remember, from 1 to 50, and whether files
  deleted from this computer drop off by themselves.

**Alt+Shift+1** to **Alt+Shift+9** still reopen the first nine straight away,
and pinned documents now come first there too. QUILL has the same window on
the same key, and the same quick keys on its Open Recent menu. The user
guide's "Opening something you worked on recently" has the details.

## Notes on your document

QUILL Lite now has **inline notes**, the same ones QUILL has, on the same keys.
A note is a comment on a line or a selection: a question, a reminder, or what
you think of a plan somebody sent you. They are on **Tools > Inline Notes**.

- **Alt+Shift+I** adds a note. The window shows the start of the text it is on,
  so you know you are in the right place.
- **Alt+Shift+J** and **Alt+Shift+K** move to the next and previous note, and
  **Alt+Shift+H** reads the one you are on (twice to change it).
- **Alt+Shift+Delete** deletes a note, after asking.
- **Alt+Shift+Enter** lists every note in the document. From there you can go
  to one, change or delete it, remove them all, copy them all, or save them as
  a Markdown or JSON file.

Notes are private unless you say otherwise. In a Markdown or HTML document you
can write a note **into the file** instead, as a hidden comment that anyone who
opens the file can read, including an AI assistant. That makes QUILL Lite a
good way to review a plan an AI wrote: leave your notes in it and hand the file
back. A script can then list or clear them with `QuillLite.exe --notes`.

**Snippets** moved to **Ctrl+Alt+Shift+Home** to make room for the notes on
the same keys as QUILL. Alt+Shift+I is now Add Inline Note.

## Ticking off tasks

Put the cursor on a task line, such as `- [ ] Write the tests`, and press
**Ctrl+Alt+Enter** (**Format > Toggle Task Done**). The box is ticked and you
hear how many tasks in the list are done. Press it again to untick, or select
several tasks to tick them together. **Ctrl+Z** takes it back.

## A web page you can share

**File > Export as HTML...** (**Ctrl+Alt+Shift+End**) saves a copy of your
document as one web page, ready to email or put on a website. Task lists
show as check boxes. Your document stays as it was.

## Opening a document however it arrives

Copy a file in File Explorer, a path from a chat or a link from an email, then
press **Ctrl+Alt+Shift+Enter** (**File > Open from Clipboard**). QUILL Lite
opens it. **File > Open from URL...** asks before it downloads anything,
naming the website and the size, and shows you how the download is going. You
can also drag files onto the window to open them.

## Careful with your files

- An older file that is not UTF-8 now keeps every byte when you save it. Before
  1.2, five rare characters in such a file could be lost. QUILL Lite also tells
  you, once, when a file is not UTF-8.
- If an old file's letters come out wrong, **Reopen with Encoding...** in the
  File Encoding and Line Endings window (**Ctrl+Alt+E**) reads it again in the
  encoding you choose.
- If another program changed your file since you opened it, **Ctrl+S** asks
  before writing over that change.
- QUILL Lite now notices that change as it happens, not only when you save.
  If you have not touched the document, it can reload it for you, keeping
  your cursor on the same line, and tell you once. Otherwise it asks: **Keep
  Mine**, **Reload from Disk** or **Save As...**, with Keep Mine on Enter. A
  file deleted or moved away is said once, and your text stays. The settings
  are in Preferences under **When another program changes the file**, the same
  ones QUILL has. A remembered Reload never throws away unsaved edits; QUILL
  Lite asks instead.

These ideas come from **PlanCake**, a small app by Andre of Oire Software for
reviewing AI-written plans. Thank you, Andre.

## Things that work better now

- Portable copies now start from a folder whose name has a space in it.
- **Coming back with Alt+Tab** puts your focus in your document, even when
  Windows is slow about it. It leaves the Find box and menus alone.
- **Big files and network drives no longer freeze the window.** You hear
  "Opening" and the file's name, the document is read-only until the text
  arrives, and closing the window cancels it. If it cannot be read, you are
  offered Try Again.
- **Two copies at once** no longer undo each other's preferences. Each keeps
  the changes you made in it.
- **Remove Quote Marks has a key that works.** It is now **Alt+Shift+.**
  (Alt, Shift and the period), under **Edit > Lines**. Its old key was also
  the key that shows and hides QUILL from anywhere in Windows, so whenever
  QUILL was running, QUILL Lite never heard it. QUILL's Unquote Lines moved to
  the same new key.
- **Closing QUILL Lite is tidier.** Documents sent to it while it closes are
  opened next time, an update check never starts on the way out, and an error
  message some people saw while exiting is gone.
- **Insert > Markdown Tag appears only in Markdown documents.** In a plain or
  rich text document it used to sit on the menu greyed out, which told you
  nothing. Now it is not there at all, and if you press **Ctrl+Alt+I** in one
  of those documents, QUILL Lite says "Markdown tags are for Markdown
  documents." QUILL does the same.
- **Next and Previous Heading say the heading once.** In a rich document you
  used to hear it twice, "Heading 1: Two" and then "Heading 1, Two" a moment
  later. Now you hear it once. QUILL had the same echo and is fixed too.

## Keys new in 1.2

| Key | What it does |
|---|---|
| **Shift+F7** | Thesaurus |
| **Ctrl+Alt+Shift+[** | Say Word Summary |
| **Alt+F10** | Look Up Word |
| **Ctrl+F10** | Word Explorer |
| **Ctrl+Alt+Shift+'** | Define in Context |
| **Ctrl+Alt+Shift+]** | Find the Word For |
| **Alt+Shift+;** | Dictionary Status |
| **Alt+Shift+.** | Remove Quote Marks, on its new key |
| **Alt+Shift+0** | Recent Documents |
| **Shift+F9** | Activity |
| **F9** | Repeat Last Result |
| **Alt+Shift+I** | Add Inline Note |
| **Alt+Shift+J** / **Alt+Shift+K** | Next and Previous Inline Note |
| **Alt+Shift+H** | Speak Inline Note |
| **Alt+Shift+Delete** | Delete Inline Note |
| **Alt+Shift+Enter** | List Inline Notes |
| **Ctrl+Alt+Shift+Home** | Snippets, on its new key |
| **Ctrl+Alt+Enter** | Toggle Task Done |
| **Ctrl+Alt+Shift+End** | Export as HTML |
| **Ctrl+Alt+Shift+Enter** | Open from Clipboard |
| **Ctrl+Alt+Shift+Space** | Keyboard Manager, on its new key |

The rest of the AI dictionary's keys are in the user guide. All of these are in
QUILL too, on the same keys.

## Where to learn more

The QUILL Lite User Guide, in the Start menu beside QUILL Lite, covers
everything here in thirteen chapters:

- Chapter 7, Checking your writing, for the thesaurus, Look Up and the AI
  dictionary.
- Chapter 8, What you hear, for Activity and Repeat Last Result.
- Chapter 9, Writing by voice, for holding Ctrl+F11, the live preview,
  talking to the AI and OpenAI dictation.
- Chapter 10, AI help, for a Google Gemini key and your ChatGPT plan.
- Chapter 11, Making QUILL Lite yours, for Find a setting and for making
  QUILL Lite your text editor.
- Chapter 12, Your files, updates and QUILL for All, for keeping QUILL Lite
  up to date.

**Help > Tutorials** (**Ctrl+Alt+F1**) has nine short lessons, if you would
like a guided start.

If you get stuck, choose **Help > Get Help from Support** (**Ctrl+Alt+F2**),
or write to support@community-access.org. A person at Community Access reads
every message.
