# Chapter 19: Scribe for Documents

Some documents are hard to read with a screen reader. A scanned letter is
only a picture of text. A badly made PDF reads its columns in the wrong
order, and its tables come out as a jumble of words. QUILL can fix a lot of
this on your own computer. When it cannot, Scribe for Documents can.

Scribe for Documents is a service from Pneuma Solutions. You send it a
document, and it sends back an accessible one: Word, accessible HTML, tagged
PDF, EPUB, Kindle, DAISY with audio, MP3 audio or braille. It rebuilds the
headings, the reading order and the tables, and it can describe the
pictures. QUILL's Scribe commands are Powered by Scribe for Documents.

Nothing leaves your computer until you say so, every time. Before each
upload QUILL shows you what will be sent, and where, and waits for you to
press **Send and Convert**.

This chapter covers everything: your Scribe account, every command and
window, what you hear at each stage, six walkthroughs, the keys, privacy,
and what each problem means. QUILL Lite has most of it too; its own guide
has a full chapter on Scribe in QUILL Lite.

## Where everything is

| Menu | What is there |
|---|---|
| **Tools > Scribe for Documents** | Convert a File, Convert This Document, Convert from a Link, My Scribe Documents, Conversions, Scribe Status, Repeat Last Scribe Message, Replace with Finished Document (for a tab that is reading a conversion), Sign In, Sign Out, Open My Scribe Account in Browser, Options, About Scribe for Documents |
| **File** | My Scribe Documents |
| **File > Import** | Convert with Scribe for Documents... |
| **File > Export** | With Scribe for Documents... |
| **Tools > Braille** | Translate with Scribe for Documents... |
| **Window** | Scribe Conversions |

Every command is also in the Command Palette (`Ctrl+Shift+P`). Type
"Scribe", and each one is listed as "Scribe for Documents:" and its name.
None of them has a key of its own; you can give any of them one in the
Keymap Editor. The table in [Keys and commands](#keys-and-commands) lists
them all.

**More Preferences** has a page called **Scribe for Documents**, with an
**Open Scribe for Documents...** button. It opens the same Options window as
the menu. Press the QUILL key and then `O` to open More Preferences.

## What Scribe for Documents is

Scribe for Documents reads a document, works out its structure, and writes
it out again in the format you ask for. It runs on Pneuma Solutions'
computers, not yours. So it can do work that is too heavy for a laptop: it
reads scanned pages, rebuilds tables, writes picture descriptions with AI,
and records an audio book with a natural voice.

You use your own Scribe account and pay Scribe for your own pages. QUILL
never takes payment, and it never sees your Scribe password. What Scribe
makes is yours. QUILL saves it in your own folders.

### When to use Scribe, and when QUILL is enough

QUILL already converts a great deal for free, on your own computer, with
nothing uploaded. Try that first.

| You have | Try first, free and local | Use Scribe when |
|---|---|---|
| A Word file, an EPUB or a PDF with real text | **File > Open**, or **File > Import > Import / Convert Document (OCR)...** | The result has its headings, tables or reading order wrong |
| A scanned PDF or a photo of a page | The free OCR QUILL offers, on your computer | The OCR text is a mess, or you need the tables and headings back |
| A document you need as DAISY with audio, MP3, tagged PDF or Kindle | QUILL makes EPUB, Word, braille and text DAISY itself | You want a format QUILL cannot make |
| A document for braille | QUILL's own braille translation | You want Scribe's braille tables and page layout |

Scribe costs pages, and the document goes to the United States. QUILL's own
tools cost nothing and keep everything on your computer. That is why QUILL
always offers the free way first.

## Getting started

You need a Scribe account and an internet connection. QUILL does the rest.

### Your Scribe account and what it costs

These are Pneuma's prices for Scribe accounts. Scribe sets them, and may
change them.

| What | What you get |
|---|---|
| A new account | 100 free pages, to use within 30 days |
| A page pack | From $10 for 200 pages. Packs never run out of date |
| A subscription | $99 a year for 10,000 pages |
| Human review | Scribe's people fix a document by hand. It costs extra |
| No pages left | Scribe still makes a free preview of the first two pages |

A page is charged once for each document. You pay when the document is
first converted. After that, **another format of the same document uses no
pages**. Convert a book to Word today, and you can have it as DAISY audio
tomorrow for nothing.

QUILL shows how many pages you have left in the Convert dialog, in My Scribe
Documents and in Options. **Buy Pages** opens Scribe's purchase page in your
browser.

### Signing in to Scribe

You sign in on Scribe's own page, in your own web browser. QUILL never shows
that page inside itself, and it never sees what you type there.

1. Choose **Tools > Scribe for Documents > Sign In...**. You do not have to
   do this first: any Scribe command that needs you signed in starts the
   sign-in for you.
2. Your browser opens at Scribe for Documents, and QUILL says "Your browser
   is open at Scribe for Documents. Sign in there, then come back to QUILL."
3. Sign in, or make a new account, in the browser. The browser tab then
   says "Signed in. You can close this tab and return to QUILL."
4. Come back to QUILL. The small window now says, for example, "Signed in to
   Scribe for Documents as Sam Lee. 100 pages left." Focus is on
   **Continue**.
5. Press **Continue**. If a command started the sign-in, it carries on.

The sign-in window has four buttons, though you see only the ones that make
sense at the time:

- **Copy Sign-in Link** copies Scribe's sign-in address. Use it when the
  browser did not open, or when you want to sign in with a different
  browser. Paste it there.
- **Try Again** starts again, after the sign-in timed out ("Sign-in timed
  out. Try again?") or failed.
- **Continue** closes the window once you are signed in.
- **Cancel** stops waiting. You are not signed in.

One sign-in covers every QUILL app on this computer, QUILL Lite included.
It is kept in Windows' secure store, never in a settings file.

**Sign Out** (**Tools > Scribe for Documents > Sign Out**) forgets the
sign-in for every QUILL app on this computer. If conversions are still
waiting, QUILL asks first, for example: "Two conversions are waiting.
Signing out stops QUILL waiting for them; they still finish in your Scribe
account." Answer **Yes** to sign out anyway.

### If your organization pays

If you belong to an organization on Scribe, such as a college or an
employer, your pages may come from the organization's shared credits.
QUILL says so beside the count, for example "1,240 pages left, using
credits from Northside College." In the Convert dialog the line reads
"This uses about 34 of the 1,240 pages left in Northside College's
credits."

Your organization also sets how long your documents are kept, from 1 to 30
days.

## What you can send

Scribe takes 23 kinds of file:

| Kind | File types |
|---|---|
| PDF | PDF, password-protected ones too |
| Pictures | JPEG, GIF, PNG, TIFF, BMP, DCX, PCX, JPEG 2000 and DjVu |
| Text documents | DOC, DOCX, RTF, ODT and TXT |
| Spreadsheets | XLS, XLSX and ODS |
| Presentations | PPT, PPTX and ODP |
| Ebooks | EPUB and MOBI |

A few rules:

- **No web pages.** Scribe does not take HTML, as a file or as a link. QUILL
  says so before anything is sent: "page.html: Scribe for Documents does not
  take web pages. Save it as Word or PDF first."
- **Up to 500 MB a file.** QUILL checks the size first, so a file that is too
  big is never sent.
- **A link must point straight at a file**, such as an address ending in
  `.pdf`. A page behind a sign-in will not work.
- **There is no page limit** except the pages you have.

The file picker in Convert a File shows only the files Scribe takes. Its
**Files of type** list can narrow it to PDF, Pictures, Text documents,
Spreadsheets, Presentations or Ebooks.

## What you can get back

Each format has a check box in the Convert dialog. You can choose several at
once.

| Format | Good for | What QUILL does with it |
|---|---|---|
| Accessible HTML | Reading in QUILL or a browser, with real headings | Opens it in QUILL |
| Word | Reading and editing in QUILL or Word. Can be large print | Opens it in QUILL |
| Tagged PDF | Sharing a PDF that screen readers can read. Can be large print | Saves it, and says where |
| EPUB | Ebook readers and QUILL's own EPUB reading | Opens it in QUILL |
| Kindle (MOBI) | Older Kindle devices and apps | Saves it, and says where |
| DAISY (text and audio) | Talking-book players, and Quill Media Player with chapters | Opens it in Quill Media Player |
| MP3 audio | Any audio player, or your phone | Opens it in Quill Media Player |
| Braille (BRF) | Braille displays, embossers and braille notetakers | Opens it in QUILL's braille view |
| Web page for offline reading | A web page you can read without the internet, as a zip | Saves it, and says where |

DAISY is DAISY 3, with text and audio together, in a zip file. When you send
it to Quill Media Player, QUILL unpacks the zip into a folder beside it and
opens the book there.

Results are saved in **Documents\Scribe for Documents**, in a folder named
after the document. You can choose another folder in Options. QUILL never
writes over a file that is already there: it adds "(2)" to the new name.

**Options** decides whether results open by themselves. See
[Scribe for Documents Options](#scribe-for-documents-options).

## The Convert dialog, control by control

Every way of converting opens one dialog, **Convert with Scribe for
Documents**. It is the same in QUILL and QUILL Lite. Here it is in Tab
order.

### What will be sent

The first control is a read-only text box, and focus starts there. Read it
line by line with the arrow keys. It says exactly what is about to happen,
for example:

"Notes.pdf (2.1 MB, 34 pages) will be sent to Scribe for Documents (Pneuma
Solutions) and converted in the United States. It stays in your Scribe
account under your retention setting (30 days unless you changed it) until
you delete it. Pictures may be described by AI. Pneuma does not use
documents to train AI."

It can also say:

- For several files, how many and which, and that they go one after
  another without asking again.
- A caution when a file's name suggests private, medical, legal or
  financial papers, such as "tax-return.pdf".
- Which of the files you chose cannot be sent, and why, after "Not sent:".
- Before your very first upload, the privacy notes from
  [Privacy, retention and deleting](#privacy-retention-and-deleting).
- For a document already in your account: "No file is sent. Scribe makes
  these formats from Notes, already in your account."

It always ends with the copyright line: "Convert only documents you own,
have permission for, or that are out of copyright."

Pressing Enter in this box is the same as pressing **Send and Convert**.

### What you want back

A group of nine check boxes, one for each format in
[What you can get back](#what-you-can-get-back). A command made for one
format starts with it checked: Word for Import, Tagged PDF for Export, and
Braille (BRF) for Translate. The other commands start with the formats you
chose last time, or your Default formats the very first time.

For a document already in your account, a format you have already made says
", already made", and the others say ", no pages used".

### Read while it converts

**Read while it converts, in a new tab (adds Accessible HTML)** opens a
read-only tab that fills with the text while Scribe works. Checking it checks
Accessible HTML too. It is there only when you convert one file, not for a
link or several files. See
[Reading while it converts](#reading-while-it-converts).

### Settings shown

A read-only line that says which groups of settings follow, for example
"Settings below: Language and voice, Braille". It changes as you check
formats, without saying anything.

The settings start as your Scribe account's own defaults, the ones on the
Scribe website. Anything you changed last time in QUILL is put on top.
Hidden groups keep their values.

### The Language and voice settings

Always shown.

| Setting | Choices |
|---|---|
| Language | Detect automatically, or one of more than 140 languages |
| Dialect | Scribe's default, or a dialect of the chosen language |
| Voice | Scribe's default, or a voice for that dialect. Used for MP3 and DAISY |
| Play Sample | Plays the chosen voice. While it plays, the button says **Stop Sample**, and Escape stops it without closing the dialog |
| Gender of the voice when the language is detected | No preference, Female, Male or Neutral |
| Speed | 0.5 times, 0.75 times, Normal, 1.5 times, 2 times, 3 times and 4 times |

The lists come from Scribe. While one loads, it says, for example,
"Loading voices...". If loading fails, it says "Voices could not be loaded",
and a **Retry Loading** button appears after the language. Scribe may not
yet read faster at 3 or 4 times than at 2 times, so those two say "(may not
be faster than 2 times)".

### The Braille settings

Shown when Braille (BRF) is checked.

| Setting | Choices |
|---|---|
| Braille table | Scribe's default, or one of more than 30: Grade 1, Grade 2, UEB, computer braille and other languages |
| Cells per line | 20 to 42. The usual is 40 |
| Split into pages | On to start with |
| Lines per page | 20 to 30, when split into pages. Starts at 25 |

### The Print setting

Shown when Word or Tagged PDF is checked. **Large print** makes the Word and
tagged PDF in large print.

### The Pictures and maths settings

Always shown.

- **Describe the pictures**: Scribe's AI writes a description of each
  picture. If you have turned AI off in QUILL, this starts unchecked and
  says why. You may still check it, because it is Scribe's own work, not
  QUILL's AI.
- **Mathematics as MathML (beta)**: writes maths in a form screen readers
  can read.
- **Email me when it is finished (Scribe's own email)**: Scribe sends you
  its own email when the work is done.

Language, picture descriptions, maths and large print shape the document
from the start. So they are fixed when it is uploaded. When you make
another format of a document already in your account, those four are hidden
and a read-only line, **Fixed when Notes was uploaded**, lists their values
instead. The other settings apply to formats not made yet. Formats already
made keep their own settings.

### Account defaults

**Also save as my Scribe account defaults (changes your Scribe website
settings too)** is off every time the dialog opens. Leave it off, and your
settings are used for this conversion and remembered in QUILL. Check it, and
Scribe's own defaults change too.

### Password

Shown only when a PDF needs a password. When QUILL can tell, it asks the
moment you press **Send and Convert**: "Notes.pdf needs its password. Type
it, then press Send and Convert." The field is labelled **Password for
Notes.pdf**.

**Show password** shows what you typed as plain text, so you can check it
with braille or typing echo. The password is used for this one upload. It is
never saved, and never written to a log.

### Pages and Buy Pages

A read-only line, for example "This uses about 34 of your 100 pages." It
updates as you check formats, without saying anything. For a file whose page
count QUILL cannot read, it says only how many pages you have. For another
format of a document already in your account it says "No pages used: this
document is already in your Scribe account."

**Buy Pages** opens Scribe's purchase page in your browser. When you come
back to the dialog, the count is read again.

### Send and Convert

**Send and Convert** sends the file and starts the work. Pressing it is
your consent. For a document already in your account the button says
**Convert**, because nothing is uploaded. **Cancel** closes the dialog, and
nothing is sent.

If no format is checked, QUILL says "Choose at least one format to get back."
and puts you on the Word check box.

## The Scribe for Documents commands

### Convert a File

**Tools > Scribe for Documents > Convert a File...** opens a file picker
that shows only the files Scribe takes. You can choose several at once.
Then the Convert dialog opens.

### Convert This Document

**Tools > Scribe for Documents > Convert This Document...** sends the
document you are working on. If it has changes, or was never saved, QUILL
saves it first and asks for a name if it needs one. A Word, PDF or other
file that Scribe takes is sent as it is. A Markdown or HTML document is sent
as Word, made with Pandoc, or as plain text when Pandoc is not installed.

### Convert from a Link

**Tools > Scribe for Documents > Convert from a Link...** asks for "The
address of a file (a PDF or a document, not a web page or a page behind a
sign-in)". Type or paste an address that starts with `https://` or
`http://`, and press OK. Scribe fetches the file itself. Anything else is
refused with "That is not a web address. Nothing was sent."

### Convert with Scribe from Import

**File > Import > Convert with Scribe for Documents...** is the Scribe step
of Import. It converts one file, and the result opens as a new, unsaved tab
named after the file, such as "Notes (Scribe)". The result sentence ends
"Word is open in a new tab.", and the status bar says, for example, "Opened
Notes.pdf from Scribe for Documents, which rebuilt it; with your consent it
was uploaded and stays in your Scribe account."

### Export with Scribe

**File > Export > With Scribe for Documents...** sends the document you are
working on, saved first, as in Convert This Document. It is how QUILL gives
you tagged PDF, Kindle, DAISY with audio and large print, which QUILL cannot
make itself. QUILL's own exports of EPUB, Word, braille and text-only DAISY
are still in the Export menu, and they stay on your computer.

### Translate with Scribe

**Tools > Braille > Translate with Scribe for Documents...** sends the
document you are working on for braille, with Scribe's tables and page
settings. The braille opens in QUILL's braille view, where the proofing
and checking tools work on it like any braille file.

### Scribe Status and Repeat Last Scribe Message

**Tools > Scribe for Documents > Scribe Status** says what the conversion
running now is doing, once, without opening anything: "Notes.pdf, adding
image descriptions, 40 percent, about 2 minutes." With nothing running it
says "No Scribe for Documents conversions are running."

**Tools > Scribe for Documents > Repeat Last Scribe Message** says the last
thing Scribe for Documents said again. Before anything has been said, you
hear "Nothing from Scribe for Documents yet."

Both are good commands to give a key of your own in the Keymap Editor.

### Open My Scribe Account in Browser

**Tools > Scribe for Documents > Open My Scribe Account in Browser** opens
your account on the Scribe website, already signed in. Go there to change
how long documents are kept, buy pages, change your account defaults, or
delete your account.

### About Scribe for Documents

**Tools > Scribe for Documents > About Scribe for Documents** shows what
Scribe is, who makes it, and the privacy notes.

## When a PDF looks scanned

When you open a PDF that has little or no readable text, QUILL offers to
read it. The same happens when **Import / Convert Document (OCR)** finds no
text. With Scribe available, the question has three choices:

- **Run free OCR on this computer (nothing is uploaded)**
- **Convert with Scribe for Documents (rebuilds headings, tables and
  picture descriptions; uses about 12 pages of your Scribe pages)**
- **Open the text there is**

The free choice is first. The Scribe choice opens the Convert dialog, so you
still see what will be sent before anything goes. To leave Scribe out of
this question, uncheck **Offer Scribe when a PDF has little or no text** in
Options.

## Scribe Conversions

**Window > Scribe Conversions**, or **Tools > Scribe for Documents >
Conversions**, opens a window that lists every Scribe job on this computer,
from every QUILL app. It stays open beside your document. Jobs carry on
when you close it, and when you close QUILL.

The window has:

- **Conversions**, a list with three columns: File, Formats and Stage. Each
  row's Stage changes only when the stage changes, and the rows never move
  under you. When there is nothing to list, a line says "No Scribe for
  Documents conversions."
- **Details**, a read-only box with everything about the job you are on: its
  stage, formats, percent, time left, Scribe's latest message, the files
  made, the folder, and an error code if there was a problem.
- A row of buttons for the job you are on, then **Close**.

In the list, **Enter** opens the result, **Delete** removes the row, and the
Applications key or **Shift+F10** opens a menu with every command. **Escape**
closes the window and takes you back to where you were.

### The job commands

| Button | What it does |
|---|---|
| **Open Result** | Opens what was made, in the tool where it is used |
| **Next Steps...** | A menu of what you can do with what was made. See [Next Steps](#next-steps) |
| **Open Folder** | Opens the folder the results were saved in |
| **Cancel Waiting** | Stops QUILL waiting for the job. Scribe still finishes it and may use pages |
| **Retry** | Tries again, without uploading again when Scribe already has the file |
| **Buy Pages** | Opens Scribe's purchase page |
| **Enter Password...** | For a file waiting for its password |
| **Sign In...** | Signs in again, then carries on with the job |
| **Ask for Human Review...** | Asks Scribe's people to fix the document by hand, with your comment. This is paid |
| **Copy Details** | Copies the Details box, with the error code, to the clipboard |
| **Remove from List** | Takes the row off this list. Nothing is deleted from your Scribe account |

Every button can always be reached with Tab. When one cannot act on the job
you are on, it says why, for example "Notes.pdf has no result to open
yet."

### The stages

What the Stage column says:

| Stage | What it means |
|---|---|
| Queued | Waiting its turn on this computer |
| Uploading | Being sent to Scribe |
| Waiting in Scribe's queue, then Starting, Converting or Adding image descriptions | Scribe is working, followed by the format, such as "Converting: Word" |
| Downloading | The result is coming back |
| Waiting: Scribe asked to slow down | Scribe asked for a pause. QUILL tries again in a minute |
| Waiting for you: needs its password | Use Enter Password... |
| Waiting for you: sign in again | Use Sign In... |
| Done | Finished. Use Open Result or Next Steps |
| Failed | It did not work. Details says why |
| No longer in your Scribe account | The document was deleted on Scribe |
| Stopped waiting | You used Cancel Waiting, or signed out |

### What you hear at each stage

QUILL says each step once. You never hear a step twice, and you never hear
a percent between the milestones.

| When | What you hear |
|---|---|
| A file is sent | "Scribe for Documents: sending Notes.pdf, for Word." |
| Another format of a document in your account | "Scribe for Documents is making EPUB from Notes." |
| Each change of stage | "Notes.pdf, uploading." Then, for example, "Notes.pdf, converting to Word." and "Notes.pdf, adding image descriptions." |
| A quarter, half and three quarters of the way | "Notes.pdf, 50 percent." |
| It is finished | "Scribe for Documents made Notes.docx in Documents\Scribe for Documents\Notes. Word is open in QUILL." |
| It is finished, and nothing opened | The same, ending "Open it from Scribe Conversions." |
| It failed | "Scribe for Documents could not convert Notes.pdf:" and Scribe's own reason |

Stages and the milestones follow **Speak each stage** in Options. The
start, the result and any problem are always said. Only one QUILL app says
these things, the one that is running the job; the others show the same
rows quietly.

### Several files, one after another

Choose several files in **Convert a File**, and they go in one Convert
dialog, with one consent. They are sent one after another, each starting
only when the one before has finished or failed. You are not asked again.
Pneuma agreed to this way of working.

Each file's start, result or problem is said as it happens. A file that
fails does not stop the rest. When the last one is done you hear one
sentence for them all, for example "Scribe for Documents finished 3 files.
Made: Notes.pdf and Map.png. Not made: Old.doc; Scribe Conversions has the
details."

If Scribe asks QUILL to slow down, QUILL waits a minute and says so once:
"Scribe for Documents asked QUILL to slow down; trying again in a minute."
The Details box shows the time it will try again.

### Closing QUILL while a job runs

Closing QUILL does not lose a job. Scribe carries on, and the job stays on
the list. The next time a QUILL app starts, it picks the job up and
downloads what was made. Then it says, once, for example "Scribe for
Documents finished 2 documents while QUILL was closed: Notes and Chapter 2,
in Documents\Scribe for Documents."

## Next Steps

When a job has made something, **Next Steps...** in Scribe Conversions
lists what you can do with it. Nothing runs until you choose it, and each
one is a separate choice.

| What was made | Next Steps offers |
|---|---|
| Word, Accessible HTML or EPUB | **Read Aloud with QUILL's Voices**, **Check Accessibility (GLOW Audit)** and **Summarize with Your AI...** |
| Braille (BRF) | **Open in the Braille View** |
| MP3 audio or DAISY | **Send to Media Player** |

Each one opens the file in QUILL first, or goes to its tab if it is already
open, and then runs the command. When a job made more than one of Word,
HTML and EPUB, each step names its format, such as "Read Aloud with QUILL's
Voices (Word)". Read Aloud always starts from the top of the document.
Summarize uses the AI you chose in Choose Your AI, which asks first as it
always does, and is not offered when AI is turned off. Scribe is not
involved in that step. If the Media Player cannot be opened, QUILL says so
and the file stays in its folder.

## My Scribe Documents

**File > My Scribe Documents**, or **Tools > Scribe for Documents > My
Scribe Documents**, lists every document in your Scribe account. That
includes those you made on the Scribe website or on an iPhone. It is read
when it opens; press **Refresh** to read it again.

In Tab order:

- **Show**: Documents or Trash.
- **Pages**: how many pages you have left, and whose they are.
- **Buy Pages**.
- **Documents**, the list. Its columns are Title, Pages, Date and Formats
  ready. In the Trash they are Title, Trashed, and Deleted forever on.
  With nothing to list, a line says "No documents in your Scribe account."
  or "Nothing in your Scribe trash."
- The buttons, then **Close**.

| Button | What it does |
|---|---|
| **Download Formats...** | The Convert dialog for this document, with nothing uploaded. Download a format already made, or make a new one |
| **Open in QUILL** | Opens a file you already downloaded from this document |
| **Rename...** | Changes the document's title in your Scribe account |
| **Move to Trash** | Moves it to the Trash. Scribe deletes it after 7 days |
| **Recover** | In the Trash: takes it out again |
| **Delete Forever...** | In the Trash: deletes it now |
| **Ask for Human Review...** | Scribe's paid fixing by hand, with your comment |
| **Copy Details** | Copies the title, Scribe's ID for it, the pages, the date and the formats |
| **Refresh** | Reads the list again |

In the list, **Enter** is Download Formats, and **Delete** is Move to Trash
(Delete Forever in the Trash). The Applications key opens a menu of the
buttons.

**Delete Forever** asks first, and **Cancel** is the default: "Delete Notes
forever? This cannot be undone. Scribe would delete it on its own on
2026-12-01." Choose **Delete Forever** to go ahead.

After Move to Trash, Recover or Delete Forever, you move to the next row and
hear one short sentence, such as "Notes moved to Trash."

### Another format, with no pages used

Because pages are charged once for each document, **Download Formats...** is
the cheap way to get a new format. The Convert dialog opens with "No file is
sent", each format you already have says ", already made", and the rest say
", no pages used". Press **Convert**. The steps are in the walkthrough
[Another format of a document in your account](#another-format-of-a-document-in-your-account).

## Scribe for Documents Options

**Tools > Scribe for Documents > Options...** opens one window for the whole
QUILL family. QUILL and QUILL Lite share it, and a change in one is a change
in both. Press **OK** to save; **Cancel** leaves things as they were.

In Tab order:

| Control | What it does |
|---|---|
| **Account** | Who is signed in and how many pages are left, or "Not signed in to Scribe for Documents." |
| **Sign In...** or **Sign Out** | Signs in, or out, for every QUILL app on this computer |
| **Open My Scribe Account in Browser** | Your account on the Scribe website: retention, purchases, account deletion |
| **Default formats** | Nine check boxes. Convert a File, Convert This Document and Convert from a Link check them until you have chosen formats yourself; after that, your last choice wins |
| **Download folder** and **Browse...** | Where results are saved, one folder for each document. To start with, Documents\Scribe for Documents |
| **Open each result when it is ready** | **Open it** (the default), **Ask me first**, or **Don't open** |
| **Offer Scribe when a PDF has little or no text** | Adds Scribe to the scanned-PDF question. On to start with |
| **Speak each stage** | **Only while a QUILL app is in front** (the default), **Always**, or **Never** |
| **About** | What Scribe is, and the privacy notes, under the heading **Powered by Scribe for Documents** |
| **Open Scribe Terms in Browser**, **Open Scribe Privacy Policy in Browser**, **Open Scribe Manual in Browser** | Scribe's own pages |

**Open each result when it is ready** works like this. With **Open it**, a
result opens by itself, but only in the app that asked for it, and only if
that app is in front. With **Ask me first**, nothing opens, and the result
sentence ends "Open it from Scribe Conversions." With **Don't open**, the
result is only saved. You can always open it later with **Open Result**.

## Reading while it converts

Scribe makes the HTML first, and sends it to QUILL a piece at a time. Check
**Read while it converts, in a new tab** in the Convert dialog, and you can
start reading at once.

- A new tab opens, named, for example, "Notes (Scribe, converting)". It is
  read-only.
- Text is added only a whole paragraph, heading or list item at a time, at
  the end. Your place does not move, the braille line does not change under
  you, and nothing new is spoken.
- When the text is all there, the tab is named "Notes (Scribe, complete)".
  If the conversion fails partway, it is named "Notes (Scribe, incomplete)"
  and keeps what arrived.
- The result sentence says it: "Notes is complete in its tab; Replace with
  Finished Document, in Tools, swaps in the finished one".

### Replace with Finished Document

The streamed text is a quick first look. The finished Word or HTML can have
more, such as a title and picture descriptions. **Tools > Scribe for
Documents > Replace with Finished Document** swaps the finished document into the tab, and keeps
your place at the same paragraph. You hear "Replaced with the finished
document." The tab is then named "Notes (Scribe)", and you can edit and
save it like any new document.

If the finished document is not ready, you hear "The finished document is
not ready yet." In any other tab, you hear that the command works in a tab
that is reading a Scribe for Documents conversion.

## The watch folder

A watch folder can send every document that lands in it to Scribe. This is
the only standing consent Scribe has in QUILL, and you give it one profile
at a time. Watch folders are part of QUILL's feature profiles; if **Tools >
Watch Folder** is missing, choose a fuller profile in **Profiles and
Features**.

1. Choose **Tools > Watch Folder > Watch Folder Profiles...** and press
   **Add...**.
2. Give the profile a name and choose its **Watch folder**.
3. In **Action**, choose **Convert with Scribe for Documents**.
4. In the group **Scribe for Documents makes**, check the formats you want.
5. Read **Scribe for Documents consent details**. It says that every
   document that arrives is sent with nobody at the computer, and uses
   pages from your account.
6. Check **I agree to send this folder's files to Scribe for Documents
   (Pneuma Solutions)**, and press **OK**.

Things to know:

- **One at a time.** Files go through the same queue as everything else,
  one after another, and they show in Scribe Conversions.
- **Only what Scribe takes.** Any other file is left alone for the
  profile's other work.
- **What you hear** is the watch folder's usual result, such as "Scribe for
  Documents made Notes.docx in Documents\Scribe for Documents\Notes".
  Nothing is said twice, and nothing opens by itself.
- **Sign in first.** If you are not signed in, you hear once for the
  profile, not once a file: "Watch profile needs you to sign in to Scribe
  for Documents before it can send files. Choose Tools, Scribe for
  Documents, Sign In."
- **No dialogs.** A file that needs a password waits in Scribe Conversions.
- **Settings.** The profile chooses the formats. The other settings, such
  as language and voice, are your Scribe account's defaults, read when each
  file is sent, with any you set in Scribe for Documents Options on top.
- **Retries.** If the watch folder tries a file again, QUILL reports the
  job Scribe already has rather than sending the file a second time.
- **Stopping.** Uncheck the consent box, or disable the profile, and nothing
  more is sent.

**Preview (dry run)** in the profile says what would happen to a file
without sending it.

## Walkthroughs

Each walkthrough says what to press and what you hear. Your file names and
numbers will be different.

### A scanned PDF to Word

1. Choose **File > Open** and open the scanned PDF, here "Letter.pdf".
2. QUILL finds little text and asks. Choose **Convert with Scribe for
   Documents (rebuilds headings, tables and picture descriptions; uses
   about 3 pages of your Scribe pages)**, and press OK.
3. If you are not signed in, your browser opens. Sign in, come back, and
   press **Continue**.
4. The Convert dialog opens on **What will be sent**. Read it with the arrow
   keys.
5. Press Tab. Check that **Word** is checked.
6. Press **Send and Convert**. You hear "Scribe for Documents: sending
   Letter.pdf, for Word."
7. You hear the stages: "Letter.pdf, uploading.", "Letter.pdf,
   converting.", and perhaps "Letter.pdf, adding image descriptions."
8. When it is done: "Scribe for Documents made Letter.docx in
   Documents\Scribe for Documents\Letter. Word is open in a new tab."
   The new tab is called "Letter (Scribe)".
9. Read it. Press `Ctrl+S` to save it where you like.

### A textbook to DAISY audio for the Media Player

1. Choose **Tools > Scribe for Documents > Convert a File...** and choose
   the textbook, here "Biology.pdf".
2. In the Convert dialog, uncheck **Word** and check **DAISY (text and
   audio)**.
3. Tab to **Voice**. Choose a voice and press **Play Sample** to hear it.
   Press Escape to stop the sample.
4. Choose a **Speed**, such as 1.5 times.
5. Tab to **Pages** and check you have enough. Then press **Send and
   Convert**.
6. You hear "Scribe for Documents: sending Biology.pdf, for DAISY (text and
   audio)." A long book takes a while. Press **Window > Scribe Conversions**
   to watch it, or use **Scribe Status** at any time.
7. You hear each stage, and each quarter of the way.
8. When it is done, QUILL opens the book in Quill Media Player, with its
   chapters: "Scribe for Documents made Biology.zip in Documents\Scribe for
   Documents\Biology. The DAISY book is open in Media Player."
9. If it did not open, choose the row in Scribe Conversions, press **Next
   Steps...** and choose **Send to Media Player (DAISY (text and audio))**.

### A PDF to braille, proofed in the braille view

1. Open the PDF in QUILL, here "Menu.pdf".
2. Choose **Tools > Braille > Translate with Scribe for Documents...**.
3. In the Convert dialog, check that **Braille (BRF)** is checked. The
   Braille group appears.
4. Choose a **Braille table**, such as UEB, and set **Cells per line** and
   **Lines per page** for your display or embosser.
5. Press **Send and Convert**. You hear "Scribe for Documents: sending
   Menu.pdf, for Braille (BRF)."
6. When it is done: "Scribe for Documents made Menu.brf in Documents\Scribe
   for Documents\Menu. The braille is open in QUILL."
7. The braille is in QUILL's braille view. Use the braille tools there to
   proof it, then emboss it or send it to your display as you would any
   braille file.

### A password-protected PDF

1. Choose **Tools > Scribe for Documents > Convert a File...** and choose
   the PDF, here "Statement.pdf".
2. Choose your formats and press **Send and Convert**.
3. QUILL sees the PDF is locked and says "Statement.pdf needs its password.
   Type it, then press Send and Convert." You are in **Password for
   Statement.pdf**.
4. Type the password. To read back what you typed, check **Show password**
   and read it with braille or the arrow keys.
5. Press **Send and Convert** again.
6. If the password was wrong, you hear "Statement.pdf needs its password.
   Open Scribe Conversions to enter it."
7. Open **Window > Scribe Conversions**. The row says "Waiting for you:
   needs its password". Press **Enter Password...**. The window says
   "Password not accepted. 2 tries left."
8. Type the right password and press OK. The job carries on.

After three wrong passwords the job stops, with "Statement.pdf was not
sent: password not accepted". Press **Retry** to start again with three
more tries.

### Another format of a document in your account

This uses no pages.

1. Choose **File > My Scribe Documents**.
2. Arrow to the document, here "Notes". The Formats ready column says what
   you already have, such as "Word".
3. Press Enter, or **Download Formats...**.
4. The Convert dialog says "No file is sent. Scribe makes these formats
   from Notes, already in your account." Word says ", already made" and the
   others say ", no pages used".
5. Check **EPUB** and press **Convert**.
6. You hear "Scribe for Documents is making EPUB from Notes.", and then the
   result.

### A folder of files through the watch folder

1. Make a folder, such as "Documents\To Scribe".
2. Set up a profile on that folder, as in [The watch folder](#the-watch-folder),
   with the action **Convert with Scribe for Documents**, **Word** checked,
   and the consent box checked.
3. Make sure you are signed in: **Tools > Scribe for Documents > Sign
   In...**.
4. Copy three scanned PDFs into the folder.
5. The watch folder sends them one after another. Each shows in Scribe
   Conversions.
6. As each finishes, you hear the watch folder's result, such as "Scribe
   for Documents made Scan1.docx in Documents\Scribe for Documents\Scan1".
7. Find the Word files in your download folder, or use **Open Folder** in
   Scribe Conversions.

## Keys and commands

No Scribe command has a key to start with. They are used now and then, so
they are reached from their menus and the Command Palette. Give any of them
a key in the Keymap Editor, in More Preferences.

| Command | Menu | Key | What it does |
|---|---|---|---|
| Convert a File | Tools > Scribe for Documents | None; assign one in the Keymap Editor | Sends one or more files you choose |
| Convert This Document | Tools > Scribe for Documents | None; assign one in the Keymap Editor | Sends the document you are working on |
| Convert from a Link | Tools > Scribe for Documents | None; assign one in the Keymap Editor | Scribe fetches a file from its address |
| My Scribe Documents | Tools > Scribe for Documents, and File | None; assign one in the Keymap Editor | Your documents on Scribe, and the Trash |
| Conversions | Tools > Scribe for Documents | None; assign one in the Keymap Editor | Opens Scribe Conversions |
| Scribe Conversions | Window | None; assign one in the Keymap Editor | Opens Scribe Conversions |
| Scribe Status | Tools > Scribe for Documents | None; assign one in the Keymap Editor | Says what the running job is doing |
| Repeat Last Scribe Message | Tools > Scribe for Documents | None; assign one in the Keymap Editor | Says the last Scribe message again |
| Sign In | Tools > Scribe for Documents | None; assign one in the Keymap Editor | Signs in through your browser |
| Sign Out | Tools > Scribe for Documents | None; assign one in the Keymap Editor | Signs out every QUILL app |
| Open My Scribe Account in Browser | Tools > Scribe for Documents | None; assign one in the Keymap Editor | Your account on the Scribe website |
| Options | Tools > Scribe for Documents | None; assign one in the Keymap Editor | Scribe for Documents Options |
| About Scribe for Documents | Tools > Scribe for Documents | None; assign one in the Keymap Editor | What Scribe is, and the privacy notes |
| Replace with Finished Document | Tools > Scribe for Documents | None; assign one in the Keymap Editor | Swaps the finished document into a reading tab |
| Convert with Scribe for Documents | File > Import | None; assign one in the Keymap Editor | Converts one file into a new tab |
| With Scribe for Documents | File > Export | None; assign one in the Keymap Editor | Exports the document as any Scribe format |
| Translate with Scribe for Documents | Tools > Braille | None; assign one in the Keymap Editor | Braille, opened in the braille view |

Inside the Scribe windows:

| Where | Key | What it does |
|---|---|---|
| Scribe Conversions list | Enter | Open Result |
| Scribe Conversions list | Delete | Remove from List |
| Scribe Conversions and My Scribe Documents lists | Applications key or Shift+F10 | Every command for the row |
| Scribe Conversions | Escape | Closes it, back to where you were |
| My Scribe Documents list | Enter | Download Formats |
| My Scribe Documents list | Delete | Move to Trash, or Delete Forever in the Trash |
| Convert dialog, What will be sent | Enter | Send and Convert |
| Convert dialog, while a sample plays | Escape | Stops the sample |
| Any Scribe window | F1 | Help on the control you are on |

## Privacy, retention and deleting

This is what QUILL tells you before your first upload, and what is in
**About** in Options.

- **Where it goes.** Pneuma Solutions processes the document in the United
  States: on AWS in Ohio, with Microsoft Azure (East US) for speech and text
  recognition, Mathpix for mathematics, and Google Gemini through
  OpenRouter for picture descriptions.
- **No training.** Pneuma never uses documents to train AI.
- **How long it is kept.** Your document stays in your Scribe account under
  your retention setting: 30 days unless you changed it, 1 to 30 days by
  choice, or as long as you like with a subscription. An organization sets
  1 to 30 days. QUILL cannot read or change this setting. Change it on the
  Scribe website with **Open My Scribe Account in Browser**.
- **Picture descriptions.** Pictures can be described by AI. Pneuma is
  reviewing its picture-description provider, and makes no promise yet
  about how long that provider keeps data.
- **Deleting.** Open My Scribe Documents, choose **Move to Trash**, then in
  the Trash choose **Delete Forever**. Something left in the Trash is
  deleted after 7 days.

And on your own computer:

- **Your password stays with Scribe.** You sign in on Scribe's own page in
  your browser. QUILL keeps only the sign-in, in Windows' secure store.
- **A PDF password is used once.** It is never saved or written to a log.
- **The log is bare.** QUILL's log holds only what stage a job reached, its
  document ID and its page count. Never your document's text, its title
  when the name looks private, your sign-in or a password.
- **Your results are yours.** QUILL saves them in your own folders. The
  queue and the downloads belong to your Windows account, and are never
  shared with anyone else who uses this computer.
- **Consent every time.** Each upload needs **Send and Convert**. There is
  no "don't ask again". The one standing consent is a watch folder
  profile's, which you give, can see in the profile, and can take back.

### Copyright

Convert only documents you own, have permission for, or that are out of
copyright. The Convert dialog says so every time.

### Safe Mode

Safe Mode turns every Scribe command off. Choose one and you hear "Scribe
for Documents is disabled in Safe Mode. Restart QUILL without --safe-mode to
use network features." Nothing is queued, and the scanned-PDF question does
not offer Scribe. Jobs already sent carry on at Scribe, and the next normal
start picks them up.

## Troubleshooting

When something goes wrong, you hear one sentence that names Scribe for
Documents and the file, and usually Scribe's own reason. Scribe writes its
messages for people to read. QUILL adds a code, such as QUILL-SCRIBE-PAGES,
which you never hear. It is in the Details box and in **Copy Details**, for
when you ask for help.

### Sign-in has ended (QUILL-SCRIBE-SIGNIN)

**You hear:** "Your Scribe for Documents sign-in has ended. Conversions are
paused until you sign in again."

**Why:** your sign-in ran out, or was taken back on the Scribe website.

**What to do:** in Scribe Conversions, press **Sign In...** on the job. Once
you are signed in again, the job carries on.

### Sign-in could not reach QUILL (QUILL-SCRIBE-SIGNIN-LOCAL)

**You hear:** "No port could be opened on this computer to receive the
sign-in. Check that security software allows QUILL apps to listen on
127.0.0.1."
Or, when the browser did not open, that QUILL could not open your browser.

**Why:** QUILL waits for Scribe's answer on this computer only, at
127.0.0.1. Security software blocked that, or no browser opened.

**What to do:** allow QUILL in your security software, then **Try Again**.
If the browser did not open, press **Copy Sign-in Link**, paste it into any
browser, and sign in there. QUILL is still waiting.

### Not enough pages (QUILL-SCRIBE-PAGES)

**You hear:** "Scribe for Documents could not convert Notes.pdf:" then
Scribe's message, then "Use Buy Pages in Scribe Conversions, then Retry."

**Why:** your account does not have enough pages.

**What to do:** press **Buy Pages**, buy pages in your browser, come back
and press **Retry**. Without pages, Scribe still makes a free preview of the
first two pages; you can read it in your account on the Scribe website.

### PDF needs its password (QUILL-SCRIBE-PASSWORD)

**You hear:** "Notes.pdf needs its password. Open Scribe Conversions to
enter it." After three wrong tries: "Scribe for Documents could not convert
Notes.pdf: Notes.pdf was not sent: password not accepted".

**Why:** the PDF is locked, and the password was missing or wrong.

**What to do:** press **Enter Password...** on the job, as in
[A password-protected PDF](#a-password-protected-pdf). After three tries,
press **Retry** to start again.

### Scribe asked QUILL to slow down (QUILL-SCRIBE-BUSY)

**You hear:** "Scribe for Documents asked QUILL to slow down; trying again
in a minute."

**Why:** Scribe allows each person only so many actions a minute, and your
own use of the Scribe website counts too.

**What to do:** nothing. QUILL waits a minute and carries on. The Details
box says when it will try again.

### Not a file Scribe takes (QUILL-SCRIBE-NOTDOC)

**You hear:** "Scribe for Documents cannot convert Data.xml: it takes PDF,
pictures, Office, OpenDocument, text, EPUB and MOBI files, not web pages."
For a web page: "page.html: Scribe for Documents does not take web pages.
Save it as Word or PDF first."

**Why:** Scribe takes only the 23 kinds of file in
[What you can send](#what-you-can-send).

**What to do:** save the file as Word or PDF, and send that. For a page you
are working on in QUILL, use **Convert This Document**, which sends it as
Word.

### File over 500 MB (QUILL-SCRIBE-TOOBIG)

**You hear:** "Video.pdf is 612 MB. Scribe for Documents takes files up to
500 MB."

**Why:** the file is bigger than Scribe takes. Nothing was sent.

**What to do:** split the document into parts, or save a smaller copy with
smaller pictures.

### No longer in your Scribe account (QUILL-SCRIBE-GONE)

**You hear:** "Scribe for Documents could not convert Notes.pdf:" and
Scribe's reason. The row says "No longer in your Scribe account".

**Why:** the document was deleted on Scribe, perhaps on the website or
because its time ran out.

**What to do:** press **Remove from List**. To have it again, start a new
conversion from the file.

### Connection lost (QUILL-SCRIBE-OFFLINE)

**You hear:** after a few seconds without a connection, "Reconnecting to
Scribe for Documents; your conversion is still running there." During an
upload: "Upload of Notes.pdf was interrupted; QUILL will resume it."

**Why:** your internet connection dropped, or Scribe could not be reached.

**What to do:** nothing, usually. The conversion carries on at Scribe, and
QUILL reconnects by itself without uploading again. You hear nothing when it
comes back. If you were signing in or loading a list, you may hear
"Couldn't connect to Scribe. Check your connection and try again."

### Could not save the result (QUILL-SCRIBE-SAVE)

**You hear:** "Scribe for Documents could not convert Notes.pdf:" then, for
example, that the folder is not writable or could not be created.

**Why:** the download folder is full, read-only, or missing.

**What to do:** free some space, or choose another **Download folder** in
Options, then press **Retry**. What Scribe made is still in your Scribe
account, so nothing is lost and no more pages are used.

### Off in Safe Mode (QUILL-SCRIBE-OFF)

**You hear:** "Scribe for Documents is disabled in Safe Mode. Restart QUILL
without --safe-mode to use network features."

**Why:** QUILL is running in Safe Mode.

**What to do:** restart QUILL normally.

### Conversion failed (QUILL-SCRIBE-FAILED)

**You hear:** "Scribe for Documents could not convert Notes.pdf:" and
Scribe's reason, or "Something went wrong. Please try again."

**Why:** Scribe could not finish the work, or answered in a way QUILL did
not expect.

**What to do:** press **Retry**. If it fails again, press **Copy Details**
and send that to support with **Help > Get Help from Support**.

### Codes you will not hear

QUILL-SCRIBE-IN-PROGRESS, QUILL-SCRIBE-NOT-COMPLETE and
QUILL-SCRIBE-CANCELLED are used inside QUILL. Scribe runs one format of a
document at a time, so QUILL simply waits; and Cancel Waiting says its own
sentence instead.

## Questions people ask

### Does QUILL send my document anywhere without asking?

No. Every upload
needs **Send and Convert**. The only exception is a watch folder profile
where you checked the consent box yourself.

### Can I stop a conversion?

Scribe cannot be stopped once it has started.
**Cancel Waiting** stops QUILL waiting and downloading, and says so: "QUILL
stopped waiting for Notes.pdf. Scribe will still finish it and may use
pages; it stays in My Scribe Documents."

### Will a second format cost more pages?

No. Pages are charged once for each
document. Use **Download Formats...** in My Scribe Documents.

### Is Scribe the same as QUILL's AI?

No. Scribe is a document service with
its own consent. It does not go through Choose Your AI. Turning AI off in
QUILL only changes whether **Describe the pictures** starts checked.

### Where are my files?

In Documents\Scribe for Documents, in a folder for
each document, unless you chose another folder in Options. **Open Folder**
in Scribe Conversions takes you there.

### Can I use QUILL Lite at the same time?

Yes. They share one sign-in, one
queue and one Options window. Only one sends at a time, and only the one
running the job speaks.

### Why did nothing open?

A result opens by itself only when Options says
**Open it**, and the app that asked is in front. Tagged PDF, Kindle and the
offline web page are only saved. Use **Open Result** or **Next Steps...**.

### What happens if QUILL closes during a conversion?

Nothing is lost. The
next time QUILL starts, it downloads what was made and tells you.

---

- Previous: [Chapter 18: Taking payments with your forms](quill-guide-18-taking-payments.html)
- Next: [A last word](quill-guide-a-last-word.html)
- [Contents](../userguide.html)
