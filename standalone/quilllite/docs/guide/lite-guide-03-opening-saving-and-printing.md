# Chapter 3: Opening, saving and printing

QUILL Lite makes you one promise: open a file, change nothing, save it, and
you get exactly the file you started with. This chapter is about that promise
and everything around it. You will meet the four kinds of document and learn
how to tell QUILL Lite which one you mean. Then you will see what happens when
you save, how your work is kept safe if the computer stops, and how to get an
earlier version back. Last come the documents QUILL Lite offers you when it
starts, and printing.

## Four kinds of document

Every document is one of four kinds. The title bar names the first two, and
the status bar's **Format** cell names all four.

**Plain text** is like Notepad. One font, no formatting, no markup. Anything
you paste in arrives as plain text. Program files, settings files and logs are
plain text, and plain text is what you want when another program is going to
read the file.

**Markdown** is plain text with a few simple marks that mean something: `#`
starts a heading, `-` starts a bullet, and `**` makes a word bold. QUILL Lite
types those marks for you (see [Formatting](lite-guide-06-formatting-headings-and-the-insert-menu.html#formatting),
in Chapter 6) and reads them back,
so as you move around it can tell you that you have arrived at a Heading 2 or
walked into a list of five items.

**HTML** is the same idea written as tags: `<h2>`, `<ul>`, `<strong>`.
Everything you can do in Markdown, you can do in HTML, in HTML's own spelling.

**Rich text** is like WordPad. Bold, italic, headings, alignment, bullet points
and line spacing. It saves as a Rich Text file, which Word and WordPad both
open.

QUILL Lite picks the kind from the file's name. That is only a first guess, and
you can change it:

| The file is called | You get |
|---|---|
| `notes.rtf` | Rich text |
| `notes.md`, `.markdown`, `.mdx`, and `.txt` | Markdown |
| `page.html`, `.htm`, `.xhtml` | HTML |
| `build.py`, `nginx.conf`, `app.log`, anything else | Plain text |
| nothing yet: a new, unsaved document | Markdown |

A `.txt` file and a brand-new document start as Markdown, because if you type
`## Notes` into one, you almost certainly mean a heading. A program file like
`.py` or a settings file like `.conf` starts as plain text, because there a `#`
starts a comment and a `-` is an option. You would not want every other line
announced as "Heading 1".

### Saying otherwise

You can always change the guess. Writing HTML in a scratch `.txt` file is a
perfectly normal thing to do. There are three ways to choose:

- **Alt+Shift+F** steps through all four kinds: plain text, Markdown, HTML,
  rich text, and round again. Each one says its name, so keep pressing until
  you hear the one you want. This is the quickest way.
- **Ctrl+Alt+F6** (**Format > Document Language**) lets you pick one from a
  list, and tells you what each choice will do before you choose.
- **Enter on the status bar's Format cell** steps on to the next kind, just
  like Alt+Shift+F. The status bar is often where you notice the kind is
  wrong, so you can fix it right there.

Switching between plain text, Markdown and HTML changes **nothing in your
document**. It only changes what the formatting keys type from now on.
Switching to or from rich text really converts your document, so QUILL Lite
asks you first.

Your choice lasts as long as the window is open. It describes what you are
typing, not the file itself.

The tutorial *Four kinds of document, and how to say which* lets you try each
of these with the app guiding you.

### What the conversion keeps

When you go **out of rich text**, your formatting is turned into Markdown, so
you do not lose it. A Heading 2 becomes `## `, a bold word becomes `**bold**`,
and a bullet list becomes lines that start with `- `. The **Format** cell then
says Markdown, and heading navigation, the headings list and the outline still
find everything they found a moment ago. If your document holds something
Markdown cannot show, such as a table, a picture or a footnote, QUILL Lite
names it before it asks.

When you go **into rich text**, it works the other way. A Markdown document's
`## Title` becomes a real Heading 1, `**bold**` becomes truly bold, and an HTML
document comes across too. A **plain text** document is left exactly as it is.
The asterisks in a shopping list are not meant as bold, so QUILL Lite does not
guess.

#### What comes with you, both ways

Headings, bold, italic, underline, strikethrough, superscript and subscript,
font and size, text colour and highlight, bullet and numbered lists, links,
code, block quotes, alignment, line spacing, indents, spacing before and after,
named styles, page breaks, tables, pictures and horizontal lines.

#### Opening your rich text in Word

A rich text file from QUILL Lite opens properly in Word. Headings use Word's
own heading styles, and Quote, Title, Subtitle and Caption use the names Word
knows. So Word's style box says Quote, instead of just showing text that looks
indented and italic.

#### Your file's name

Your file keeps its name. But rich text cannot be saved into a `.txt` file, so
the next time you press **Ctrl+S**, QUILL Lite offers `notes.rtf` instead of
`notes.txt`, with the name already filled in. Just press Enter to accept it.
That way the name always matches what is inside.

## Opening a PDF

QUILL Lite opens PDFs. Press **Ctrl+O** and choose one, the same as any other
file. You can also drag one onto the window, or open it from Recent Documents.

A PDF opens as its **text**. You can read it, search it, select and copy from
it, and change it. What you cannot do is turn it back into a PDF: QUILL Lite
never writes to a PDF. The PDF you opened stays exactly as it was.

When it opens, QUILL Lite tells you how many pages it has, whether it has an
outline, and which pages, if any, may read poorly.

### What comes through, and what does not

The words come through, in order, with the lines joined back into paragraphs.
Each page stays a page, blank pages included, so page 3 is always the third
page. Headings, lists and tables come through as ordinary lines of text: a
heading keeps its own line, a list item keeps its own line, and each row of a
table stays one line with its numbers in order. Pictures do not come through at
all. A page set in two clear columns is read down the first column and then the
second; a page with three columns, or columns wrapped around pictures, can still
come out mixed. Those are the limits of reading a PDF's text, and QUILL has the
same ones.

QUILL Lite reads the first 200 pages of a very long PDF, and tells you when it
stopped early.

### How the text of each page is chosen

A PDF can be read more than one way, and the ways do not always agree: one may
spell a widely spaced line out a letter at a time, or run two columns together
line by line, where another reads it properly. QUILL Lite decides page by page.
A page whose first reading is clean is kept at once. A page that shows signs of
trouble, or looks as if it is set in two columns, is read two more ways, and
the reading with the fewest problems wins: fewest characters that cannot be
read, words broken into letters, words glued together, and missing text. A short
title page, a page of figures, or a page in another language is not marked
down for being short.

Nothing is uploaded, nothing is guessed, and the PDF is never changed. A
character the PDF gave no meaning to is left in the text rather than deleted,
and the page is named so you know to check it.

### When a page may read poorly

When the PDF opens, QUILL Lite names any page that still reads poorly, for
example: "Opened as text, 12 pages. Pages 3 and 7 may read poorly." A page is
named when every reading of it was poor, when it holds characters that could
not be read, or when it is only a picture, like one scanned page in an
otherwise ordinary PDF. Blank pages are never named. Go to the page with
**Ctrl+G** and check it; for a picture page, OCR (below) can read it.

### Pages

A PDF keeps its pages:

- The status bar gets a **Page** part, which says something like
  "Page 3 of 12". Press **Enter** on it to go to a page.
- **Ctrl+G** (Go To) has a **Page** choice. Arrow to it and pick a page from the
  list.

### Page breaks, and what you hear

Between one page and the next, the text holds a single **page break**
character (a "form feed"). It is what the Page part and Go To's Page list
count, so it stays in the text, and it is saved with the text if you save it.
The last words of one page and the first words of the next sit on either side
of it.

What QUILL Lite itself says never includes it. When a message quotes text
across a page break, such as the first words of a selection that starts at the
bottom of one page, the page break is read as a pause, the same as a new line, and
the status bar shows it the same way. **Ctrl+Shift+C** on it says "Page
break", where it used to say "Unnamed character".

What your screen reader says as you arrow onto it is up to the screen reader:
some say nothing, some say "page break", and some may say "form feed". If
yours reads the last line of a page and the first line of the next as one
line, use **Ctrl+G**, **Page**, to land at the top of a page instead.

### The PDF's own outline

Many PDFs come with an outline: a list of chapters and sections, which other
programs call bookmarks. When the PDF you open has one, **Ctrl+G** has an
**Outline** choice. Each entry says its title and its page, for example
"Chapter 2, page 14". An entry inside another also says its level, for example
"Summary, level 3, page 15". Choose one and press **Enter** to go there: you
land on the title itself, even when it is halfway down the page, or on the top
of the page when the title cannot be found there. The level only describes the
outline; it does not make anything a heading.

### A PDF with a password

If the PDF is locked, QUILL Lite asks for its password. Type it and press
**Enter**. If it is wrong, QUILL Lite says so and asks again. Press **Escape**
to give up, and nothing opens.

QUILL Lite uses the password once, to open that file, and never saves it.

### A scanned PDF

Some PDFs are only pictures of pages: a scanned letter, or a photocopy saved as
a PDF. There is no text in them to read. When QUILL Lite opens one, it says it
looks scanned and asks whether to read it with OCR on this computer. OCR means
recognizing the letters in the picture.

- **Yes** reads every page. QUILL Lite says when it starts, and the status bar
  counts the pages as it goes. When it finishes, the text opens with its pages,
  and QUILL Lite counts it as unsaved work, because that text is not saved
  anywhere yet.
- **No** opens whatever little text the PDF has, or nothing at all if it has
  none.

Nothing is uploaded. The reading happens on your computer, with the OCR that
comes with Windows. It reads the languages you have installed in Windows
Settings. If QUILL's own OCR engine, Tesseract, is installed, QUILL Lite uses
that instead, because it can say how sure it is. OCR makes mistakes, so check
the text, and spell check helps.

If this computer has no OCR at all, QUILL Lite says so and opens nothing.

### Saving

Press **Ctrl+S** on a PDF and QUILL Lite tells you it will not write over the
PDF, then opens **Save As** with the same name ending in `.txt`. Choose text,
Markdown or rich text, and press **Enter**. From then on you are working on the
new file. If you type a name ending in `.pdf`, QUILL Lite says it cannot save
that kind of file, and asks you to choose another.

To make a real PDF, print to **Microsoft Print to PDF** instead (see
[Printing](#printing)).

## Office files at a glance

QUILL Lite handles Office files in two different ways, and it helps to know
which one you are getting before you start.

- A **Word document** (`.docx`) is a document you can **edit and save as Word**.
  It opens as rich text, with its headings, lists, bold, links and tables, and
  **Ctrl+S** writes a real Word document back. See *Word documents* below.
- **Everything else** from Office or LibreOffice opens as **readable text**, so
  you can read it, search it and copy from it. QUILL Lite never writes back into
  those files. **Ctrl+S** explains why, then opens **Save As** so you can keep
  your text as a new file.

This works the same in an installed copy of QUILL Lite and in the portable
copy. Both carry everything Word editing needs, and nothing is downloaded or
uploaded.

| File type | What QUILL Lite does | Can you save back to it? |
| --- | --- | --- |
| Word document (`.docx`) | Opens to edit as rich text. Asks first if the document has things a save would drop, such as comments or pictures | **Yes.** Ctrl+S saves a real Word document. A document you were warned about is backed up first |
| Word document with macros (`.docm`) | Opens as text to read and copy. Macros never run | No. Ctrl+S opens Save As |
| Word 97-2003 document (`.doc`) | Opens as text when LibreOffice is installed. Without LibreOffice, QUILL Lite tells you how to make a `.docx` | No. Ctrl+S opens Save As |
| OpenDocument text (`.odt`) | Opens as text | No. Ctrl+S opens Save As |
| Excel workbook (`.xlsx`, or `.xls` with LibreOffice) | Opens as text: a "Sheet:" heading for each sheet, then its cells as a text table | No. Ctrl+S opens Save As |
| PowerPoint presentation (`.pptx`, or `.ppt` with LibreOffice) | Opens as text: a "Slide" heading for each slide, then its bullets, tables and speaker notes | No. Ctrl+S opens Save As |
| Excel with macros (`.xlsm`), OpenDocument spreadsheet (`.ods`) or presentation (`.odp`) | **Ctrl+O** does not open these. **File > Import / Convert Document** reads them into a new document | Not applicable. You get a new, untitled document |

**To edit a file that opens as text, make it a `.docx` first.** For example,
to edit a `.docm`, a `.doc` or an `.odt` in full:

1. Open it in Word, or in LibreOffice Writer.
2. Choose **File > Save As**.
3. Pick **Word Document (.docx)** and save.
4. Open the new `.docx` in QUILL Lite.

A `.docm` saved this way loses its macros, which is why QUILL Lite never edits
one directly. To keep the text without leaving QUILL Lite, open the file, switch
the window to rich text with **Switch Document Mode** (**Alt+Shift+F**), and save it with **Ctrl+Shift+S**
under a new name ending in `.docx`. You get a new Word document, and the
original is left untouched.

**Open or Import / Convert?** **Ctrl+O** opens the file itself: the window
takes the file's name, and a Word document saves back to that file.
**File > Import / Convert Document** always makes a new, untitled document from
what it reads, named after the file with "(converted)" on the end. Use Import /
Convert when you want a copy of the text to work on, or for a file Ctrl+O
cannot open, such as a `.xlsm`, an e-book or a picture of a page. See
*Importing and converting a document* below.

## Opening Word, Excel and PowerPoint files

QUILL Lite opens Excel and PowerPoint files, Word files with macros, older Word
files and OpenDocument text as their **text**, the same way it opens a PDF. A
Word `.docx` is different: it opens to edit, as rich text, and saves as Word
(see *Word documents* below). Press **Ctrl+O**, and in the file type list
choose "Older Word, Excel and PowerPoint, opened as text", or just pick the
file from "All supported files". You can also drag one onto the window, or
open it from Recent Documents. Nothing is downloaded first, and nothing is
uploaded: QUILL Lite uses the same readers as QUILL.

These are QUILL's own readers, and they are always used first, in the same
order QUILL uses. They open a Word file in about a second, and a slide show in
less, even the first time after you start QUILL Lite. Only if QUILL's own reader cannot read
a file, or finds no text in it, does QUILL Lite try a second reader
(MarkItDown) where one is installed; QUILL Lite's own installer does not
include it, so for most people that second try never happens and the sentence
you hear explains what was wrong with the file.

It opens these kinds of file:

- Word documents with macros, `.docm` (a macro is never run), and a `.docx`
  you chose to open "for reading and plain editing" (see *Word documents*)
- Excel workbooks: `.xlsx`
- PowerPoint presentations: `.pptx`
- OpenDocument text, from LibreOffice Writer: `.odt`
- The older Office 97-2003 files, `.doc`, `.xls` and `.ppt`, when LibreOffice
  is installed (see below)

### Finding the highlighted passages in a Word document

A Word file opened as text (a `.docm`, or a `.docx` you chose to open for
reading) comes through without its formatting, but its highlights are not lost: QUILL Lite reads them from the file itself (`.docx`
and `.docm`) and takes you to them. They are on **Navigate > Highlighted
Passages**, on the same keys as in QUILL:

- **Next Highlighted Passage** (**Alt+PageDown**) puts the cursor at the start
  of the next highlighted passage and says its colour, where it is in the count
  and its words: "Yellow highlight, 2 of 5: sign and date here". After the last
  one it goes round to the first.
- **Previous Highlighted Passage** (**Alt+PageUp**) goes the other way.
- **List Highlighted Passages...** (**Ctrl+F2**) lists them all, in order. Each
  row is the passage's words, its colour, and the paragraph it is in, so a row
  makes sense on its own. Enter goes to the passage; Escape closes the list and
  leaves the cursor where it was. **Alt+Left** goes back after either.

For example, a tenancy agreement whose landlord highlighted "deposit" in
yellow and "two forms of ID" in pink: open it, press **Ctrl+F2**, and you hear
"deposit, yellow highlight, in: Pay the deposit by Friday." as the first row.

The same keys work in a rich text document you have open in QUILL Lite, where
the highlights are in the document itself. If you edit the text of a Word file
after opening it, a passage whose words you changed is left out rather than
guessed at. Highlights in headers, footers, footnotes and text boxes are not
listed, because that text is not in the editor; nor is paragraph shading.

### What comes through, and what does not

- **Word and OpenDocument text:** each heading keeps its own line, marked
  with `#` signs the way Markdown marks one (`##` for a level 2 heading); bulleted and numbered lists keep their levels; tables
  become text tables; a line break inside a paragraph stays a line break; a
  picture comes through as its description, "[Image: ...]", when the author
  wrote one. Numbered items are numbered 1, 2, 3 in the text itself, so you
  hear the right number on each line. An equation comes through as text, the
  way an equation is written in Markdown: "Pythagorean theorem:
  \(a^{2}+b^{2}=c^{2}\)", where `^{2}` means "squared" and `\(` and `\)` mark
  where the equation starts and ends. (Before October 2026 equations were
  left out without a word.)
- **Excel:** each sheet starts with a heading, "Sheet: Budget", and its cells
  follow as a text table whose first row is the header row. Dates read as
  dates and numbers as you would say them. A very large sheet is read up to
  2,000 rows and 50 columns.
- **PowerPoint:** each slide starts with a heading, "Slide 2: Figures", in the
  order the presentation shows them. The bullets come next, then any tables,
  then the speaker notes under "Notes".

Bold, italic, fonts and colours do not come through, and nor do headers,
footers, footnotes, comments, charts or the pictures themselves.

For example, open `Budget.xlsx`. The document starts at "Sheet: Budget", with
the budget's rows under it, and the next sheet's heading, "Sheet: Notes",
follows the last row.

### Older files and files that will not open

QUILL Lite cannot read the Office 97-2003 formats by itself. If LibreOffice
(free, from libreoffice.org) is installed, QUILL Lite has it make a temporary
copy in the newer format and opens that; your file is not changed. If it is
not installed, QUILL Lite says it could not open the file and tells you what to
do: open it in Word, Excel or PowerPoint (or LibreOffice), choose
**File > Save As**, pick the newer type, such as "Word Document (.docx)", and
open that copy.

A password-protected file is named as password-protected: remove the password
in the program that made it, save, and open it again. A damaged file is named
as damaged.

### Saving

A file opened as text is never saved over: the text is not the file. Press
**Ctrl+S** and QUILL Lite tells you why, then opens **Save As** with the same
name ending in `.txt`. Choose text, Markdown or rich text and press **Enter**.
A Word `.docx` opened **to edit** is different, and saves as Word; see *Word
documents*, next.

## Word documents

Since October 2026 QUILL Lite **edits** Word documents. Open a `.docx` and it
arrives as rich text, with its headings, lists, bold and links shown formatted;
change it; press **Ctrl+S**; and what is written is a real Word document that
Word, and anyone you send it to, opens as one. QUILL Lite does this with
QUILL's own Word code, the same code QUILL's File > Open and Save use, so the
two programs open, ask, back up and save a Word document in exactly the same
way.

This section covers what opens, what is kept, the question you are sometimes
asked, the backup, tables, saving, and the limits. A worked example is at the
end.

### What opens as a Word document

- A `.docx` file opens as a Word document to edit. Press **Ctrl+O**, choose
  "Word documents (*.docx)" in the file type list (or "All supported files"),
  and press **Enter**. Dragging the file onto the window, Recent Documents and
  opening it from File Explorer all do the same.
- A `.docm` (a Word file with macros), a `.doc` from Word 97-2003 and an
  OpenDocument `.odt` still open as **text**, read only, as described in
  *Opening Word, Excel and PowerPoint files* above. A `.docm` is not edited
  because saving it would drop its macros, and Word refuses a `.docm` without
  them.
- The file is read in the background, so the window keeps answering. You hear
  "Opening report.docx", and when it is ready, "Opened as Rich Text. Headings
  and bold are shown formatted."

Word editing works in every copy of QUILL Lite, installed or portable, since
the builds of 17 October 2026. Earlier test builds of the *installed* copy
were missing a part Word editing needs, so they opened every `.docx` as text;
the portable copy was not affected. If a copy were ever to lose that part
again, a `.docx` would open as text, as described above, and **Ctrl+S** would
offer Save As, so nothing would be lost. QUILL Lite's build checks for exactly
this and refuses to finish, so it should never happen to you.

### What is kept

Everything QUILL Lite can show in rich text comes in, and goes back out when
you save:

- headings, Heading 1 to Heading 6, as Word's own heading styles, so Word's
  navigation pane and your screen reader's heading keys find them;
- bulleted and numbered lists;
- bold, italic, underline, strikethrough, superscript and subscript;
- fonts, sizes, text colours and highlights;
- links;
- paragraph alignment, line spacing, spacing before and after, and indents;
- the Title, Subtitle, Quote and Caption styles;
- tables, as tables (see *Tables* below).

Some things in a Word document cannot be shown in QUILL Lite's editor, so a
save cannot carry them: pictures, comments, tracked changes, headers and
footers, footnotes and endnotes, more than one section, and a table's own
formatting, such as merged cells, borders and shading. QUILL Lite looks for
these before it opens the file, and if it finds any it asks you first.

### The question, when a document has things a save would drop

When the document has any of those things, QUILL Lite names them and asks how
to open it, in a window titled **Open Word document**. For example: "team.docx
contains features QUILL Lite's rich editor cannot carry: tables (1), comments.
How should it open?" Use **Up Arrow** and **Down Arrow** to choose, then
**Enter**:

1. **Open for reading and plain editing (recommended).** The document opens as
   text, as it would without Word editing. Nothing about the file can change:
   **Ctrl+S** tells you so and offers Save As. This is the row you start on,
   and **Escape** gives the same answer, because it is the one that cannot
   hurt the file.
2. **Edit as Rich Text, these will not survive a save: ...** The row names the
   same things again. The document opens to edit, and the first time you save,
   the original is backed up first (see *The backup*).
3. **Edit a copy as Rich Text (the original stays untouched).** QUILL Lite
   makes a dated copy beside the original, `team.backup-20261017-143005.docx`,
   and opens the copy to edit, saying "Editing a copy,
   team.backup-20261017-143005.docx. The original is untouched." Your saves go
   to the copy; the original is never written.

A document with none of those things opens to edit with no question.

Press **F1** in the window for a summary of the three answers.

### The backup

The first time you save a document you chose to edit with its losses named,
QUILL Lite copies the original beside itself before writing anything, and says
so: "Backed up the original to team.backup-20261017-143005.docx". The name is
the original's, then `backup-`, then the date and time (in Coordinated
Universal Time), then `.docx`. It happens once each time you open the file,
not on every save. If you want the pictures or comments back, they are all in
that copy; open it in Word.

A document that opened with no question is not backed up: there was nothing in
it a save would drop. QUILL Lite's own dated copies (**File > Earlier Versions**) are kept as
well, as for any file.

### Tables

A Word document you edit as rich text keeps its tables as **real tables**: a
grid on screen, which your screen reader sees as a table. The arrow keys,
**Tab** and **Navigate > Table** read and change them one cell at a time (see
"Moving through a table" and "Editing a table"). When you save, each one is a
real Word table again, its first row marked as the header row. Add a row with
**Tab** in the last cell or **Navigate > Table > Insert Row Below**, and a
column with **Insert Column Right**.

A Word document opened for reading and plain editing is text, so there a table
arrives as rows of cells divided by `|`, with a row of dashes under the header
row:

```
| Name | Role |
| --- | --- |
| Ann | Lead |
```

The same table keys read it cell by cell.

To read a table cell by cell, use **Navigate > Table** (see *Moving through a
table* in Chapter 4). For example, with the cursor on "Name", **Ctrl+Alt+Down**
says "Row 2: Ann".

### Saving

- **Ctrl+S** writes the Word document. A long document can take a moment, so
  the save runs in the background: the status bar says "Saving report.docx",
  and you hear "Saved report.docx" when it is written. If you press **Ctrl+S**
  again before then, you hear "Still saving report.docx" and nothing else
  happens; QUILL Lite never starts a second save over the first. Closing the
  window in that moment waits too: answer the question again once you have
  heard "Saved".
- If you type while a save is running, what you typed is not in the file yet,
  so the document still counts as changed. Press **Ctrl+S** again afterwards.
- **Ctrl+Shift+S** (Save As) opens on the **Word document (*.docx)** row with
  the same name proposed. Type a new name ending in `.docx` to keep a second
  Word copy, or choose Rich Text, Text or Markdown to save in another form.
- Dark mode never reaches the file. While a Word document is being saved,
  QUILL Lite takes the screen's text colour off the document and puts it back
  afterwards, so somebody opening your file in Word sees ordinary black text, not grey.
- Any rich text document can become a Word document: press **Ctrl+Shift+S**
  and type a name ending in `.docx`, or choose **Word document (*.docx)**.
- A plain text window cannot save a `.docx`. Switch it to rich text first with
  **Alt+Shift+F** (Switch Document Mode), or choose another kind of file.

### Limits

- Pictures, comments, tracked changes, headers, footers, footnotes, endnotes,
  extra sections and table formatting are not kept by a save. You are always
  told before you start (see *The question*).
- Styles other than the headings and the four named above become normal
  paragraphs with the formatting you can see.
- A `.docm`, `.dotx` or `.dotm` cannot be saved; QUILL Lite says so and writes
  nothing.
- A password-protected or damaged `.docx` does not open, and QUILL Lite says
  which.

### Worked example: a meeting agenda

1. Press **Ctrl+O**, choose `agenda.docx`, and press **Enter**. You hear
   "Opening agenda.docx", then "Opened as Rich Text. Headings and bold are shown
   formatted."
2. Press **Ctrl+Alt+H** to move to the next heading. You hear "Heading 2:
   Actions".
3. Press **Ctrl+End** to go to the end of the agenda, press **Enter**, and type
   "Book the room by Friday."
4. Press **Ctrl+S**. You hear "Saved agenda.docx".
5. Open `agenda.docx` in Word. "Actions" is still a Heading 2 in the
   navigation pane, and "Book the room by Friday." is the last paragraph.

The same document with a comment in it would first have asked the question
above. Choosing **Edit as Rich Text** and saving would have said "Backed up the
original to agenda.backup-...docx" before "Saved agenda.docx", and the comment
would still be in that copy.

## Importing and converting a document

**File > Import / Convert Document (OCR)...** turns a document, or a picture
of a page, into new text you can edit. It is QUILL's command, with QUILL's
readers and QUILL's words, on QUILL Lite's File menu. It has no shortcut key,
as in QUILL: press **Alt+F**, then **I**. It is also in the command palette.

It reads:

- **Word, Excel, PowerPoint and OpenDocument files** (`.docx`, `.doc`, `.xlsx`,
  `.xls`, `.pptx`, `.ppt`, `.odt`, `.ods`, `.odp`), with QUILL's own readers,
  the same ones Ctrl+O uses;
- **web pages, e-books and CSV files** (`.html`, `.htm`, `.epub`, `.csv`), which
  Ctrl+O would open as their raw markup or as a table of commas;
- **PDFs**, from their own text, the same way Ctrl+O reads them;
- **pictures of pages** (`.png`, `.jpg`, `.jpeg`, `.tif`, `.tiff`, `.bmp`,
  `.gif`, `.webp`), such as a photo of a letter, with OCR on this computer.

### How it differs from Open

**Ctrl+O** opens the file itself: the window takes the file's name, Recent
Documents remembers it, and Save offers to save it again (or, for a PDF or an
Office file, asks for a new name). **Import / Convert** makes a **new, untitled
document** from what it reads, named after the file with "(converted)" on the
end, for example "report (converted)". Nothing remembers or points back at the
original, and the original is never changed. Use it when you want text to work
with rather than the file you started from, or when Ctrl+O cannot open the
file at all: a picture, a web page you want as words, or an e-book.

### Step by step

1. Press **Alt+F**, then **I**. The Import / Convert Document box opens on the
   folder of the document you are in.
2. Choose the file and press **Enter**. The type list starts on "All convertible
   documents"; you can narrow it to Documents or Images.
3. QUILL Lite says "Converting report.docx". You can keep working; the status
   bar's message part shows how far it has got.
4. When the text arrives, it opens in this window if the window is empty, or
   in a new window if it is not, so nothing you were writing is replaced. You
   hear what happened, for example "Opened report.docx as editable text, read
   by QUILL's own Word reader. Nothing was uploaded."

The new document counts as unsaved, because its text exists nowhere else yet.
Press **Ctrl+S** to save it as text, Markdown or rich text.

### When the file has no text: OCR

A scanned PDF, or a PDF that is only pictures of pages, has no text to read.
QUILL Lite then asks: "QUILL Lite could not find readable text in scan.pdf. It
looks scanned or image-based. Run free on-device OCR?"

- **Yes** reads the pictures with OCR on this computer. The status bar counts
  the pages as it goes, for example "Recognizing page 3 of 12", and you hear
  when it is done.
- **No** opens whatever little text the file has, which may be nothing.
- **Cancel**, or **Escape**, stops, and nothing opens.

A picture file goes straight to OCR, without the question, because a picture
has no text of its own.

Nothing is uploaded and nothing is downloaded. The OCR is the one Windows
already has, which reads the languages installed in Windows Settings; if
QUILL's own OCR engine, Tesseract, is installed, QUILL Lite uses that instead,
because it can say how sure it is ("Confidence 84 out of 100"). OCR makes
mistakes: check the text, and spell check helps. If this computer has no OCR at
all, QUILL Lite says so and opens nothing. Unlike QUILL, QUILL Lite never
offers to download an OCR engine and has no cloud OCR.

In the result, each page starts with a marker line such as
`<!-- Page 2 -->`, as in QUILL, so **Ctrl+F** for "Page 2" finds it. When you
want a scanned PDF with real pages instead, so the Page part and Go To's Page
list work, open it with **Ctrl+O**: it asks the same OCR question.

### If it does not work

- A **password-protected PDF** cannot be imported. QUILL Lite says so; open it
  with **Ctrl+O**, which asks for the password and never stores it.
- A **damaged file** is named as damaged. OCR does not help a damaged file.
- A **very long PDF**: the first 200 pages are read, and QUILL Lite says so
  when it stopped early, for example "Only the first 200 of 340 pages were
  read."
- If you **close the window** while a conversion is still running, the
  conversion stops, and nothing opens.

Any failure is a box you must dismiss, with the reason in it, because it cost
you the thing you asked for.

## Saving

**Ctrl+S** saves. **Ctrl+Shift+S** saves under a new name.

QUILL Lite makes you one promise: **open a file, change nothing, save it, and
you get exactly the file you started with.** Nothing gets quietly tidied up
behind your back.

To keep that promise, it remembers three things about every file it opens, and
puts them back the same way:

- **How the text is stored.** Different files store letters and accents in
  different ways. QUILL Lite keeps whichever way yours already used.
- **How the lines end.** Files made on Windows and files made on other systems
  mark the end of a line differently. QUILL Lite keeps yours.
- **Whether the file ended with a blank line.** If it did not, it will not
  suddenly start.

You can hear the first two in the status bar (**F6**). When you really do want
to change them, for instance when somebody needs a copy of an old file in a
newer format, use **Tools > File Encoding and Line Endings** (**Ctrl+Alt+E**).
The change takes effect the next time you save.

The tutorial *Open a file, and give it back unchanged* lets you see this
promise for yourself, with the app guiding you.

When a file is not UTF-8, which many older Windows files are not, QUILL Lite
tells you once as it opens: "Opened as Windows-1252, not UTF-8." That is all it
does. Every byte of the file is read, and a save puts every byte back.

### When another program changes your file

QUILL Lite keeps an eye on every file you have open. When something else
writes to one, such as Word saving a document, a sync tool bringing down a
newer copy, or an AI assistant rewriting a plan while you read it, QUILL Lite
notices within a second or so.

If you have not changed the document yourself, and you have turned on
**Reload automatically when you have no unsaved edits**, it simply reads the
file again. Your cursor stays on the same line, and you hear once: "Reloaded
plan.md: changed by another program."

Otherwise it asks you, once for each change:

- **Keep Mine** leaves your document exactly as it is. Enter and Escape both
  give this answer, because doing nothing to your text is the safe choice. The
  next time you save, your version replaces the one on disk, without another
  question.
- **Reload from Disk** reads the file again and keeps your cursor on the same
  line. If you had unsaved changes, they are replaced.
- **Save As...** saves your version under a new name and leaves theirs alone.

The question has a checkbox, such as **Do not ask me again for .md files**.
Check it and QUILL Lite remembers your answer, Reload or Keep Mine, for every
file of that kind. That is handy when a tool rewrites the same file every few
seconds. To take every remembered answer back, open Preferences and press
**Forget remembered file-change answers**, then OK. A remembered Reload never
throws away unsaved edits; QUILL Lite asks instead.

If you are looking at a different document when the change happens, QUILL Lite
waits and asks when you come back to that one. It also waits while any other
window, such as Preferences or a Save question, is open.

If the file is deleted or moved away, QUILL Lite tells you once, keeps your
text, and marks the document as not saved, so you can use **Save As** to keep
it somewhere.

You can change all of this in Preferences, under **When another program changes
the file**:

- **Watch the open file for external changes** is on to begin with. Turn it
  off and QUILL Lite only checks when you save.
- **Reload automatically when you have no unsaved edits** is off to begin
  with. Turn it on and an unchanged document is reloaded without asking. An
  answer you asked QUILL Lite to remember still comes first.
- **Ask before discarding unsaved edits on a conflict** is on to begin with.
  Turn it off and QUILL Lite says nothing when a file you have changed is
  changed or deleted on disk, and leaves your text exactly as it is.
- **External-change debounce (milliseconds)** is how often QUILL Lite looks,
  so a program that writes a file in several steps is dealt with once. The
  default is 750.

These are QUILL's settings too, with the same names, and QUILL asks the same
question.

### Save checks once more

Right before **Ctrl+S** writes your file, QUILL Lite checks the file on disk
once more. If another program changed it since you opened it or last saved it,
an AI assistant rewriting a plan while you read it, say, QUILL Lite stops and
asks instead of writing over that change:

- **Save As...** keeps both: yours under a new name, theirs untouched. Enter
  gives this answer.
- **Reload from Disk** shows the version on disk and throws away your unsaved
  edits.
- **Overwrite** saves your version over theirs.
- **Cancel**, or Escape, saves nothing.

QUILL asks the same question.

### How this file is written: encoding and line endings

**Tools > File Encoding and Line Endings...** (**Ctrl+Alt+E**) is one window
for both of those things. It is the same window QUILL opens from **File > File
Format...**. Nothing in it is applied until you save, and the window tells you
so.

#### Encoding

This is how the letters are stored. You can choose:

- UTF-8, for anything new.
- UTF-8 with BOM, for the Windows tools that expect it.
- UTF-16.
- Windows-1252, which many older `.txt` files use.

#### Line endings

You can choose:

- CRLF, which Windows programs write. A new QUILL Lite document starts with
  this.
- LF, which Unix, macOS and most programming tools expect.

#### A file that is something else

Some files use a way of storing text that neither list offers, such as a UTF-16
big-endian file, or a file whose lines end the way old Macs did. Such a file
keeps what it has. You see a **keep as is** row at the top of the list, and it
is already chosen. So if you open this window and just press Enter, nothing in
the file changes.

#### Reopen with Encoding

Now and then an old file's accented letters come out wrong, because it was
written in an encoding nobody can guess from the file alone, such as Cyrillic
Windows-1251. Press **Reopen with Encoding...** in this window, pick the
encoding the file was written in, and QUILL Lite reads the same file again from
disk that way. If you have unsaved changes it asks first, because reopening
throws them away. Nothing on disk changes, and if the file is not valid in the
encoding you picked, QUILL Lite says so and leaves your document alone.

After a reopen the file saves back in that same encoding. To turn it into UTF-8
instead, open this window again, choose UTF-8, and save. The button is there for
a plain text file you opened from disk; QUILL has the same one.

### When a character will not fit

Older files can only store a limited set of letters. If you type an em dash, a
curly quote or an emoji into a file that cannot hold it, QUILL Lite asks you
before it saves:

> 3 characters cannot be saved as Windows-1252. Save as UTF-8 instead?

- **Yes** saves the file as UTF-8 and keeps every character. The **Encoding**
  cell in the status bar changes to UTF-8, because from now on that is what the
  file is.
- **No** saves it the way it already was, and those characters become question
  marks. Sometimes that is what you want, for instance when another program
  has to read the file.
- **Cancel** stops, and nothing is saved.

### Saving an HTML page as Markdown

When you press **Ctrl+Shift+S**, the list of types includes **Markdown
(*.md)**. If the document you are saving is **HTML**, choosing Markdown really
converts it as it saves:

- A heading becomes `#`.
- Bold becomes `**bold**`.
- A list becomes lines that start with `-`.
- Links keep both their words and their address.

QUILL Lite says **"Converted HTML to Markdown"**, and the document in front of
you changes to match the file you just saved.

Tags that Markdown cannot show are dropped, but their words stay, so nothing
you typed disappears. If the conversion would leave nothing at all, for
example a page that is only a comment, QUILL Lite keeps your text exactly as it
was and tells you, instead of saving an empty file.

If the save fails, say because the file is locked or the disk is full, the
document in front of you is left alone. It is still HTML, and Ctrl+Z still
works as before. The same is true when you turn a rich text document into
plain text: QUILL Lite asks, saves the plain file, and only then removes the
formatting from the window.

Saving a plain text or Markdown document as `.md` changes nothing at all. A
**rich text** document is not offered Markdown, because QUILL Lite would have
to guess which bold lines you meant as headings. Save it as plain text first
(QUILL Lite asks before it removes the formatting), and then the Markdown
choice is there.

### Which kind of file you get: the name you type decides

When you save with **Ctrl+Shift+S**, the ending you type on the name decides
what kind of file is written, whatever the **Save as type** list happens to
show. Capitals do not matter: `NOTES.TXT` is a text file and `Report.RTF` is
rich text.

| You type | What QUILL Lite writes |
|---|---|
| `notes.txt`, `notes.log`, or any other text ending | Your text, exactly as it stands |
| `notes.md` | Your text as it stands; an HTML document is converted to Markdown (see above) |
| `notes.rtf` | Rich text, with its formatting. A plain document becomes a rich one |
| `page.html` | Your text as it stands. QUILL Lite treats HTML as something you write by hand, the way Notepad does |
| `minutes.docx` | A Word document, from a rich text window. From plain text, nothing: QUILL Lite says so (see below) |
| `minutes.docm`, `letter.dotx` | Nothing. QUILL Lite says so (see below) |
| `budget.xlsx`, `minutes.pdf`, `old.doc` | Nothing. These are formats QUILL Lite can only read or not open at all |

If you type a name with no ending at all, Windows adds the ending of the row
selected in **Save as type**, so `notes` with **Markdown (*.md)** selected is
saved as `notes.md`.

**Word documents.** A rich text window saves a real Word document: type
`minutes.docx`, or choose **Word document (*.docx)** in Save as type (see
*Word documents*, above). Until October 2026 a name ending in `.docx` got
plain text written under it, which made a file Word refuses to open, so a
plain text window is still refused, and so is every other Word ending
(`.docm`, `.dotx`, `.dotm`). QUILL Lite shows a short message instead and
writes nothing:

> QUILL Lite saves Word documents from rich text, so minutes.docx was not
> written from this plain text window. Switch Document Mode (Alt Shift F) to
> rich text first, or choose Rich Text (.rtf), Text or Markdown in the Save as
> type list.

Press **Enter** to close the message; Save As is over, and your document is
exactly as it was. For example, to send a plain letter to someone who uses
Word, press **Alt+Shift+F** until you hear "Rich text mode", then save it as
`letter.docx`.

The message comes before anything else. A rich text document is never asked
whether to remove its formatting for a save to `.docx`: nothing is removed.

Pressing **Escape** or **Cancel** in the Save As window writes nothing, as
always.

### If something goes wrong

While a document has changes you have not saved, QUILL Lite keeps a spare copy
of it about every thirty seconds. That copy is kept **beside** your file,
never on top of it.

If QUILL Lite or your computer stops unexpectedly, your work is offered back
the next time you start, in its own document. It comes back **the way it
was**. A file stored in an older encoding, or with Unix line endings, is still
that same kind of file after it is recovered.

If a spare copy cannot be read, for example because of a damaged disk or
another program holding the file, QUILL Lite tells you and leaves it where it
is. It is offered again next time, because it is still the only copy of that
work.

When you save, or close normally, the spare copy is deleted. So you are only
ever offered work you actually need.

#### If your screen reader stops

QUILL Lite checks every thirty seconds that your screen reader is still
running. One missed check is ignored, so restarting NVDA or JAWS never sets
anything off. When two checks in a row find it gone, QUILL Lite does two
things, in this order:

1. Every document with unsaved changes writes its spare copy **straight
   away**, without waiting for the next thirty-second copy. These are the same
   copies described above, offered back the next time you start if QUILL Lite
   never closes normally.
2. It explains what happened, for example: "NVDA appears to have stopped. Your
   work is safe: 2 documents snapshotted to autosave. QUILL Lite keeps running;
   restart your screen reader when ready."

QUILL Lite has no voice of its own, so that sentence is spoken only if another
screen reader is still running. It is always written to the status bar of the
document you were in, so when your reader is back, **F6** reads it.

QUILL Lite does not close, and nothing in your documents changes. Restart your
screen reader when you are ready; within half a minute QUILL Lite says, for
example, "NVDA is running again."

QUILL has had this protection for some time; QUILL Lite now uses the same
code, so the two behave the same. There is nothing to turn on: it only ever
writes spare copies, which a normal close throws away, and it says nothing
unless a screen reader has really stopped.

#### What you are offered, and what is tidied away

Before the recovery window opens, QUILL Lite clears out three kinds of copy,
and tells you it did:

- Copies that are identical to each other. A crash can save the same work
  several times, and that is still just one document.
- Copies nobody has come back for in **thirty days**.
- Untitled documents, if you have turned those off in Preferences.

If everything it found was one of those, no window opens. Instead you hear
"Tidied up unsaved work from last time", so you know nothing was lost.

#### The recovery window

The window lists what is left, one row each, with a checkbox. Each row quotes
the first few words of the document, like `begins "Dear Margaret, thank you
for the lovely..."`, so you can tell two untitled windows from the same
afternoon apart. There is also a
read-only **What this would do** field you can arrow through. There are six
buttons:

- **Restore Checked** brings back the ones you have checked.
- **Restore All** brings back everything.
- **Not Now** changes nothing, and offers the same list next time.
- **Discard Checked** throws away the ones you have checked.
- **Discard Everything** throws away everything.
- **Never Offer Untitled** is for you if you use QUILL Lite as a scratchpad
  and do not want yesterday's throwaway notes back.

You can change your mind about that last one later. In Preferences, turn on
**Offer untitled unsaved work back after a crash**.

### Text looks blurry, or a window is the wrong size

QUILL Lite scales itself for each monitor. Text stays sharp at 125, 150 or 200
percent, and when you move a window to a monitor with different scaling;
windows and list columns keep their proportions. If a window looks wrong at
your scaling, you can turn this off to see whether it is the cause. Search
Windows for "Edit environment variables for your account", add a variable
named `QUILL_DPI_UNAWARE` with the value `1`, and start QUILL Lite again.
Windows then stretches it the old way, so text is blurrier. Delete the
variable to put scaling back, and tell support what you saw.

### Going back to an earlier version

There is also a **timestamped backups** option, in **Tools > Customize
Features**. When it is on, QUILL Lite keeps a dated copy every time you save.
This is for getting back the paragraph you deleted an hour ago, not for
crashes. It starts switched off, because it does fill up a folder over time.

Once it is on, **File > Earlier Versions...** (**Ctrl+Alt+Shift+E**) lists
your saved copies, newest first, like "Today at 4:12 PM, 2,341 words". Up to
twenty are kept for each document. After that, the oldest go.

The word count helps you tell copies apart. Two saves a minute apart sound
almost the same, but a version that is suddenly two thousand words shorter is
usually the one you are looking for.

You can bring one back in two ways:

- **Restore** puts that version into the window you are in. It does **not**
  save, so your file is untouched until you decide. **Ctrl+Z** undoes it, so
  a mistake costs you one keystroke.
- **Open a Copy** puts the old version in a new untitled window, and leaves
  the document you are working on alone. Use this when you just want to see
  what it said yesterday.

If you had backups switched on before version 1.0, those older copies are in
the list too.

### A web page you can share

**File > Export as HTML...** (**Ctrl+Alt+Shift+End**) saves a copy of your
document as a single web page. Its styles are inside it, it has no scripts, and
it says which language it is in, so you can email it or put it on a website as
it is. Headings, lists and tables come out as real headings, lists and tables,
task lists show as check boxes, and ~~struck-out~~ text is struck out. Your
document stays as it was; only the copy is a web page.

If the document has notes written into the file, QUILL Lite asks whether to
include them in the page, marked as notes. No is the default, so a note never
ends up in a page by accident. QUILL has the same command on the same key.

## Opening what you copied, a link, or a file you drag in

Documents reach you in all sorts of ways: a file in File Explorer, a path
somebody pasted into a chat, a link in an email. QUILL Lite opens all three
without a trip through the Open dialog. The idea comes from PlanCake, a small
reading app by Andre of Oire Software.

**Open from Clipboard** (**Ctrl+Alt+Shift+Enter**, on the File menu). Copy
first, then press it:

- Files copied in File Explorer open, each in its own window. If you copied
  several, QUILL Lite tells you how many it opened.
- A file path copied as text opens that file, quotes and all. Several paths,
  one per line, open in turn.
- A web link goes to Open from URL, below.

If the clipboard holds none of those, you hear "The clipboard holds no file,
path or link." **Ctrl+V** still pastes.

**Open from URL...** (**Alt+F, F**). Type or paste a web address. QUILL Lite
finds out the file's name and size and asks before downloading anything, for
example "Download plan.md from example.com? It is 12 KB." Say Yes and a small
window shows how the download is going; its Cancel button stops it. If
something goes wrong, you hear one plain sentence instead of an error. A link
to a file's page on GitHub opens the file itself.

The download opens as a new, unsaved document named after the file. Save it
wherever you like. The temporary copy is deleted as soon as it is read.

**Drag and drop.** Drag files from File Explorer onto the QUILL Lite window
and they open. Text you drag into a document is still inserted where you drop
it.

QUILL has the same three, on the same key.

## Opening something you worked on recently

QUILL Lite remembers the documents you open, newest first, so getting back to
one never means hunting through folders.

**The quick way.** Press **Alt+Shift+1** to reopen the document you opened most
recently, **Alt+Shift+2** for the one before that, and so on up to
**Alt+Shift+8**. The same list is on the File menu, under **Open Recent**: press
**Alt+F**, then **T**. Each row says the file's name first and then the folder
it is in, so two files called "notes" are easy to tell apart.

**The whole list.** Press **Alt+Shift+0**, or choose
**File > Recent Documents...**. A window opens with every document QUILL Lite remembers. Arrow
to one and press **Enter** to open it. In the same window you can:

- **Pin** a document you come back to often (**Alt+P**). Pinned documents stay
  at the top of the list, however many others you open after them. On a pinned
  document the same button says **Unpin**.
- **Remove from List** (**Alt+R**, or the **Delete** key) takes a document off
  the list. The file itself is not touched.
- **Open Containing Folder** (**Alt+F**) shows the file in File Explorer, in its
  folder.
- **Clear Unpinned...** (**Alt+L**) empties the list. It asks first, and **No**
  is the answer if you just press Enter. Pinned documents always stay.
- **Remember up to this many documents** (**Alt+U**) sets how long the list is,
  from 1 to 50. Ten is where it starts.
- **Forget missing files when the app starts** (**Alt+M**) tidies away files
  that have been deleted from this computer. A file on a USB drive or a network
  share is kept, because it is usually just unplugged.

If a file has been moved or deleted, its row says "not found". It stays in the
window so you know what happened, and Remove from List tidies it away. The Open
Recent menu leaves it out, so the quick keys only ever open something that is
there.

QUILL has the same window on the same key. The two apps keep separate lists,
so what you open in one does not show up in the other.

## Reopening what you had open

When you start QUILL Lite, it can offer you back the saved documents you had
open last time.

### When it asks, and when it just opens them

If you only had one or two documents open, it simply opens them again. If there
were more, or a file has moved, it asks you first. That way you are not faced
with a pile of windows to sort through before you can start.

| Last time you had | What happens |
|---|---|
| one or two documents, both still there | they open, as before |
| three or more | you are asked |
| any document whose file has moved or gone | you are asked |

### The Reopen Last Session window

The window lists what you had open, one row each, with a checkbox. Everything
that can be opened starts checked. So pressing **Enter** opens all of it, and
unchecking two means "all except those two". If a file has gone, its row says so
and you cannot check it.

#### The buttons

- **Open Checked** opens the checked rows and leaves the list as it is.
- **Open All** opens everything that is still on your computer, checked or not.
- **Not Now** opens nothing and changes nothing. You will be offered the same
  documents next time. Escape does the same.
- **Forget Checked** takes the checked rows off the list, so you are not offered
  them again. **Clear the List** does that for all of them. **Neither one
  touches your files.** Forgetting only changes what QUILL Lite offers you, and
  a line under the buttons reminds you of that.
- **Never Ask Again** opens the checked documents and stops asking from now on.
- **Ask Me Next Time** undoes Never Ask Again. You will be asked again, just like
  a new install: when there are several documents, or one whose file has moved.
  The checked documents open too.

#### Turning the question back on

**Only one of Never Ask Again and Ask Me Next Time can be pressed at a time.**
The other is greyed out, not hidden, so when you land on it you can tell which
way the setting is now.

If you pressed Never Ask Again and want the question back, open the window
yourself with **File > Reopen Last Session...** (**Alt+Shift+F12**) and press
**Ask Me Next Time**. That is the only place this setting lives. It is not in
Preferences.

#### What you hear afterwards

QUILL Lite tells you what happened, for example: "Reopened all 3 documents",
"Reopened 1 of 2", or "Forgot 2 documents. 1 still remembered. The files
themselves are untouched."

#### Opening it whenever you like

**File > Reopen Last Session...** (**Alt+Shift+F12**) opens the same window any
time, not just at startup. So Not Now is always safe to press: you can come back
to the list later, and tidy it without restarting. QUILL has the same window on
the same key.

## Printing

Press **Ctrl+P** to print. Press **Ctrl+Alt+P** for Page Setup. What you set
there (paper size, orientation and all four margins) is remembered for next
time.

Long lines are wrapped to fit the page, whatever your Word Wrap setting says, so
nothing runs off the edge of the paper.

**Rich text prints as rich text.** A heading comes out as a heading, and a bold
word comes out bold.

A plain text or Markdown document prints just as it reads. A Markdown heading
prints with its `#` in front, the same as you hear it.

### Print Preview (Ctrl+Alt+Shift+P)

Most print previews are a picture of the page, which is no help if you cannot
see it. QUILL Lite's Print Preview tells you what you actually want to know.

It tells you **how many pages** there will be, on what paper, and with what
margins. Then it goes page by page and tells you what is at the top of each one.
"Page 3 of 7: Installing" tells you where that section starts, without printing
anything.

The page count is worked out for your real printer, so the number you hear is
the number of pages you will get.

## What you learned, and where to go next

Every document is plain text, Markdown, HTML or rich text. QUILL Lite guesses
from the file's name, and **Alt+Shift+F** or **Ctrl+Alt+F6** let you change
it. Only rich text really converts your document, and it asks first.

**Ctrl+S** saves your file back exactly the way it came in, with its encoding,
line endings and ending kept, and **Ctrl+Alt+E** changes those on purpose. You
know what happens when a character will not fit, how a spare copy keeps your
work safe after a crash, and how **File > Earlier Versions...** brings back an
older copy once backups are on. **Alt+Shift+1** to **Alt+Shift+8** reopen your
recent documents, and **Alt+Shift+0** shows the whole list, where you can pin
the ones you keep coming back to. QUILL Lite offers your last documents back,
only asks when there are several or something has moved, and
**Alt+Shift+F12** brings that window back whenever you want it. **Ctrl+P**
prints, **Ctrl+Alt+P** sets up the page, and **Ctrl+Alt+Shift+P** tells you
how many pages you will get and what starts each one.

The tutorials *Open a file, and give it back unchanged* and *Four kinds of
document, and how to say which* let you try all of this with the app guiding
you.

Next, Chapter 4, Moving around a document, shows you how to search, and how
to jump straight to the place you want.

---

- Previous: [Chapter 2: Finding your way around](lite-guide-02-finding-your-way-around.html)
- Next: [Chapter 4: Moving around a document](lite-guide-04-moving-around-a-document.html)
- [Contents](../userguide.html)
