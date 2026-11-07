# Chapter 3: Opening, saving and converting files

This chapter is about getting your words in and out of QUILL. We start with the
everyday things: opening a file, saving it, and what QUILL says when something
about a file changes. Then we look at the kinds of documents QUILL understands,
how to turn one format into another, and how to work with files that live on a
server or on GitHub. Read the first two topics now. Come back to the rest when
you have a Word file to send or a folder of documents to convert.

## Opening files

Most of the time you open a file with **File > Open...** (`Ctrl+O`). The File
menu has a few other ways in, and each one is handy at the right moment:

- **New** creates a blank document.
- **Open...** opens a document from disk.
- **Open Recent** takes you back to files you used lately. At the bottom of
  that list, **Clear Recent Files...** empties it when you want a fresh start.
  It asks first, and pinned files stay. Your files stay where they are; only
  the list goes.
  Just above Clear, **Recent Documents...** (`Alt+Shift+0`) shows the whole
  list in a window of its own. More on that just below.
- **Open from Clipboard** (`Ctrl+Alt+Shift+Enter`) opens whatever you copied: a
  file copied in File Explorer, a file path copied as text, or a web link. More
  on it just below.
- **Open from URL...** downloads a document from the web. Before anything is
  downloaded, QUILL asks you, naming the website and the size of the file.
- **New Document from Clipboard** opens a new document that already holds
  whatever text is on the clipboard. It is on the Edit menu too.
- **Snapshots** saves a group of open documents as one workspace snapshot, so
  you can reopen them all together later. If you know Visual Studio Code, it is
  a little like a lightweight workspace there.

Files on a server or on GitHub have their own commands. They are covered later
in this chapter, under Remote access and GitHub remote files.

**Where the Open dialog starts.** Press `Ctrl+O` and the dialog, the standard
one or the Simple File Open dialog, starts in the folder of the last file you
opened, however you opened it. That includes a file you double-clicked in
File Explorer, one passed to QUILL on the command line, one from Open Recent,
and one you went back to because it was already open in a tab. So if you open
`Minutes.docx` from your Board folder in Explorer, the next `Ctrl+O` is already
in the Board folder, ready for the agenda beside it. Saving with **Save As**
moves it too. Until something has been opened, the dialog starts in your
**Startup folder** from Settings, or in Documents.

### Opening what you copied, a link, or a file you drag in

Documents reach you in all sorts of ways: a file in File Explorer, a path
somebody pasted into a chat, a link in an email. QUILL opens all three without
a trip through the Open dialog. The idea comes from PlanCake, a small reading
app by Andre of Oire Software.

**Open from Clipboard** (`Ctrl+Alt+Shift+Enter`, on the File menu). Copy first,
then press it. QUILL looks at what you copied:

- Files copied in File Explorer open, one after another. If you copied
  several, QUILL tells you how many it opened.
- A file path copied as text opens that file. The quotes File Explorer's
  "Copy as path" puts around it are fine. Several paths, one per line, open in
  turn.
- A web link goes to Open from URL, described next.

If the clipboard holds none of those, QUILL says "The clipboard holds no file,
path or link." and nothing else happens. `Ctrl+V` still pastes, as always.

**Open from URL...** (on the File menu). Type or paste a web address. QUILL
finds out the file's name and size, then asks before downloading anything, for
example "Download plan.md from example.com? It is 12 KB." Say Yes and a small
window shows how the download is going. Its Cancel button stops it. If
something goes wrong, you hear one plain sentence, such as "Nothing was found
at that address on example.com." A link to a file's page on GitHub opens the
file itself rather than the web page around it.

The document opens read-only, with its web address in the tab name. To keep
it, save a copy. QUILL works from a temporary copy of the download and deletes
it when you close the tab.

**Drag and drop.** Drag files from File Explorer onto the QUILL window and
they open, and QUILL says how many. Text you drag into the document is still
inserted where you drop it.

QUILL Lite has all three, on the same key.

### Opening something you worked on recently

QUILL remembers the documents you open, newest first. There are two quick ways
back to one.

**The first eight.** `Alt+Shift+1` reopens the document you opened most
recently, `Alt+Shift+2` the one before that, and so on up to `Alt+Shift+8`.
They are the first eight rows of **File > Open Recent**, where each row says the
file's name first and then its folder.

**The whole list.** Press `Alt+Shift+0`, or choose **File > Open Recent >
Recent Documents...**. Arrow to a document and press Enter to open it. In the same
window you can:

- **Pin** a document you keep coming back to (`Alt+P`). Pinned documents stay at
  the top, however many others you open. On a pinned one, the button says
  **Unpin**.
- **Remove from List** (`Alt+R`, or the Delete key) takes one off the list. The
  file is not touched.
- **Open Containing Folder** (`Alt+F`) shows the file in File Explorer.
- **Clear Unpinned...** (`Alt+L`) empties the list. It asks first, and pressing
  Enter answers No. Pinned documents always stay.
- **Remember up to this many documents** (`Alt+U`) sets the length of the list,
  from 1 to 50. It is the same setting as **Recent files to remember** in
  Settings.
- **Forget missing files when the app starts** (`Alt+M`) is the same setting as
  **Drop missing recent files automatically**, described below.

A file that has moved or been deleted says "not found" in this window, and
Remove from List tidies it away. QUILL Lite has the same window on the same
key; the two apps keep their own lists.

### The Simple File Open dialog

QUILL can open files with either the standard Windows file open dialog or its
own **Simple File Open** dialog. The simple one is a short, keyboard-friendly
window: one list of files, a small filter, your recent files and a switch for
hidden files. Both are reached the same way, with **File > Open...** or
`Ctrl+O`. Which one you get is decided by
**Settings > General > Use simple file open dialog**. It is off to begin with.
Turn it on if you would like a plain picker that is easy to use with a screen
reader.

Here is what is in the Simple File Open dialog:

- A **Path** field at the top shows the folder you are in. Type a path and press
  Enter. A folder opens in the list, and a file opens in QUILL. Press `Ctrl+L`
  from anywhere in the dialog to jump back to this field. You can paste a path
  in whatever form you have it: with the quotes File Explorer's "Copy as path"
  adds, with `%APPDATA%`-style environment variables, as a `file://` link, or
  starting with `~`. QUILL tidies it up for you.
- A **Filter** dropdown chooses which file types are shown. The default,
  **Supported files**, shows plain text, Markdown, HTML and Rich Text. Choose
  **Plain text**, **Markdown**, **HTML** or **Rich Text** to narrow it further,
  or **All files** to see everything.
- A **Files** list shows the folders and files where you are. Folders start with
  `[dir]`. To go up to the parent folder, press Backspace in the list or use the
  **Up** button.
- A **Hidden** toggle shows or hides files whose names start with a dot, or that
  Windows marks as hidden. Press `Ctrl+H` in the path field or the file list to
  flip it. On a Mac, use `Cmd+Shift+.` instead, as the Finder does, because
  `Ctrl+H` there is the system's Hide shortcut.
- A **Recent** button pops up your recently opened files, so you can reopen one
  with a single choice.
- A **Use Windows Dialog** button opens the standard Windows dialog just this
  once. Your setting does not change, so the next `Ctrl+O` brings you back to
  the simple dialog. It is there for the odd case, such as a very long path or a
  custom file association, where you want the Windows picker.
- An **Open** button and a **Cancel** button. Enter opens the selected file and
  Escape cancels.

Under the list, a status line tells you the folder you are in, how many entries
are showing, and any error. If a folder is off limits ("permission denied") or a
path is not a folder, the dialog stays open so you can fix the path and try
again.

> **QUILLBee's tip:** Someone sent you a file path in an e-mail? In the Simple
> File Open dialog, press `Ctrl+L` to jump to the Path field, paste it, and
> press Enter. Quotes and all, QUILL tidies it up.

### When a file is not where it was

Files move. A OneDrive or SharePoint file can be a placeholder whose contents
were never downloaded to this PC. A file on **File > Open Recent** may have been
renamed or deleted since you last used it. A file on a USB stick or a network
share simply is not there when that drive is not connected.

When that happens, QUILL says so in one sentence, in the status bar and out
loud:

> *Bingo3.html is no longer there. It may have been moved, renamed, or deleted,
> or it may live on a drive that is not connected.*

That is all. There is no dialog to close, and QUILL stays exactly where it was,
so you can press `Ctrl+O` and pick something else. If you choose a folder where
QUILL expected a file, it tells you that instead.

Your Recent list keeps the entry. A file that is missing today may be on a USB
stick you plug back in tomorrow, so QUILL does not quietly forget it because one
open failed.

If you would rather lose dead entries, turn on
**Drop missing recent files automatically** in Settings, on the General page
(the setting is `recent_files_auto_clear_missing`, and it is off by default).
Even then, it only removes entries whose file has been deleted from one of this
PC's own fixed drives. Files on USB, removable or network drives are never even
checked, so unplugging a drive never clears its history. "Not connected" is not
the same as "gone".

## Saving files

Saving is three commands on the **File** menu:

- **Save** writes the current document.
- **Save As...** writes it to a new name or place, and converts it to the file
  type you choose in the dialog.
- **Save All** writes every open document that has changes.

**Save As...** really converts. QUILL keeps your text as portable Markdown-style
markup, so choosing **Rich Text Format (\*.rtf)** writes real RTF, **HTML
(\*.html)** writes a standalone web page, and **Text
(\*.txt)** writes your text as a plain file. Choosing **Markdown (\*.md)** keeps
the markup just as it is. The file's extension always decides the format. If you
type a name with no extension, the type you selected supplies one. There is more
on each format under What happens when you save in another format, later in this
chapter.

When Save As changes the format, QUILL can reload the file so the editor matches
it. For example, a freshly saved `.rtf` can reopen in the Rich text editor.
Reloading replaces what is in the editor with the saved file, so by default
QUILL asks first with a Yes or No question. To stop the question, set
**Settings > Editing > Reload after Save As to match the format** to *Reload
automatically* or *Keep current surface*.

**Filename suggestions.** When you save a document that has never been saved,
QUILL fills in the name box from the document's first line. It removes leading
`#` marks, quotes and bullets, and any characters a file name cannot hold. This
is only a suggestion: type over it with anything you like. It never renames a
document that is already saved. It is on by default, and you can turn it off
with **Suggest a filename from the first line** in Preferences.

### Save As Plain Text

**Save As Plain Text...** saves a clean plain-text copy, with the markup taken
out. Plain text has no links, so
**Settings > Editing > Links in plain-text export** decides what happens to a
Markdown link. You can keep the link text and its URL (the default, so you never
lose where a link pointed), the link text only, the URL only, or the original
Markdown link. The same setting applies whenever Save As writes a `.txt` file.
If your document has hidden formatting such as fonts, colours or alignment,
QUILL offers to keep it in an **Illumination**, which comes next.

### Keeping formatting in a plain-text file with Illuminations

A plain `.txt` file has nowhere to store fonts, colours or alignment, so saving
formatted text as plain text normally loses the formatting. QUILL gives you a
choice. It is named after the painted decoration a scribe adds to a manuscript:
an **Illumination** is a small companion file, `yourfile.txt.illumination`, that
keeps the formatting beside the clean text. Your `.txt` stays truly plain, so
Notepad, e-mail and every other program can read it. When you open it again *in
QUILL*, the Illumination puts back every font, colour and alignment exactly.

What happens is set by
**Settings > Editing > Saving formatted text as plain text**:

- **Ask each time** (the default). QUILL asks whether to keep your formatting by
  saving as Markdown, Word or RTF instead, to save the plain `.txt` **plus** an
  Illumination, or to save plain text only and drop the formatting.
- **Always save an Illumination sidecar**. QUILL writes the clean `.txt` and the
  `.illumination` companion every time, with no question.
- **Save plain text and drop the formatting**. The classic save that loses
  formatting. The `.txt` is clean, and any old Illumination beside it is
  removed.

Two things to keep in mind. The Illumination is a *separate file*, so if you
copy or e-mail only the `.txt`, the formatting stays behind. Keep the pair
together. And if you edit the `.txt` in another program, QUILL notices the text
no longer matches its Illumination and opens it as plain text, so formatting
never lands on the wrong words. If you want one file that keeps everything, save
as **Markdown**, which keeps the formatting inline, or **Word/RTF**, which turn
it into real formatting.

### Encoding and line endings (Ctrl+Alt+E)

**File > File Format...** (`Ctrl+Alt+E`) is one window for the two things that
decide exactly how your file is written to disk. QUILL Lite opens the same
window on the same key; on its Tools menu it is called
**File Encoding and Line Endings...**.

- **Encoding.** Choose UTF-8 for anything new. UTF-8 with BOM suits the Windows
  tools that expect one. There is also UTF-16, and Windows-1252 for older `.txt`
  files that use it. A file that arrived in something else, such as UTF-16
  big-endian, shows as a **keep as is** row and stays that way.
- **Line endings.** CRLF is what Windows programs write, and it is what a new
  QUILL document starts with, the same as Notepad, WordPad, Word and QUILL Lite.
  LF is what Unix, macOS and most build tools expect. A file that arrived with
  old-style Mac CR endings keeps them, in its own **keep as is** row.

Nothing changes until you save, and the window tells you so. If the encoding you
chose cannot hold a character in your document, the save names that character
and offers Save As. It never quietly turns it into a question mark.

**When a file is not UTF-8.** Most files today are UTF-8. When QUILL opens one
that is not, such as an older Windows file, it tells you once: "Opened as
Windows-1252, not UTF-8." Nothing about the file has changed. QUILL reads every
byte, and a save puts every byte back as it was.

**Reopen with Encoding...** Now and then an old file's accented letters come
out wrong, because it was written in an encoding nobody can guess from the
file alone, such as Cyrillic Windows-1251. In the File Format window, choose
**Reopen with Encoding...**, pick the encoding the file was written in, and
QUILL reads the same file again from disk that way. If you have unsaved
changes, QUILL asks first, because reopening throws them away. Nothing on disk
changes. If the file is not valid in the encoding you picked, QUILL says so and
leaves your document as it was.

After a reopen, the file saves back in that same encoding, so the next program
that reads it sees what it always saw. To turn it into UTF-8 instead, open File
Format again, choose UTF-8, and save.

### When another program changes the file you are editing

QUILL keeps an eye on the file you have open. When something else writes to it
(Word saving a `.docx`, a build tool regenerating a `.md`, a colleague's sync
client), **QUILL asks** what you want to do. Unless you tell it to, it never
reloads on its own.

You have three answers:

- **Reload from Disk** reads the file again, using the right reader for its
  format, and keeps your cursor where it was.
- **Keep Mine** leaves your tab exactly as it is. The version on disk is ignored
  until you save over it or reload. Escape gives this answer too, because doing
  nothing to your text is the safe choice.
- **Open Disk Version in a New Tab** opens what is on disk as a second,
  read-only tab named `<name> (on disk)`, so you can compare the two and decide.
  Your own tab is not touched.

The question has a checkbox, such as **"Do not ask me again for .docx files."**
Check it and QUILL remembers your answer for every file of that format. That way
a build that rewrites the file you are reading every few seconds is answered
once, not every time. Reload and Keep Mine can be remembered. Opening the disk
version in a new tab is a one-off comparison, so it never is. To take every
remembered answer back, choose **File > Forget Remembered File-Change Answers**
(`Ctrl+Shift+0`). A remembered Reload never throws away unsaved edits; QUILL
asks instead.

If the file changes while you *do* have unsaved edits, the same question spells
out what is at stake: reloading throws away your edits, and keeping yours
overwrites the disk version the next time you save.

**Save looks once more.** Right before Save writes your file, QUILL checks the
file on disk again. If another program changed it since you opened it or last
saved it, even a moment ago, QUILL stops and asks instead of writing over that
change:

- **Save As...** keeps both: yours under a new name, theirs untouched. Enter
  gives this answer.
- **Reload from Disk** shows the version on disk and throws away your unsaved
  edits.
- **Overwrite** saves your version over theirs.
- **Cancel**, or Escape, saves nothing.

This matters most when an AI assistant or a sync tool is rewriting a file
while you read it. If you already answered Keep Mine for that change, Save
does not ask again. QUILL Lite checks the same way, and watches the same way,
with the same four settings in its Preferences.

Two related commands are on the File menu:

- **Reload from Disk** throws away your changes in memory and reads the file
  again, after asking you to confirm.
- **Check for External Changes...** asks the same question whenever you want to
  check.

Four settings on the **General** page of Settings shape all of this:

- **Watch the open file for external changes** is on to begin with. Turn it
  off and QUILL stops noticing when another program changes or deletes your
  file.
- **Reload automatically when you have no unsaved edits** is off to begin
  with. Turn it on and, as long as you have not changed anything yourself,
  QUILL reloads a changed file without asking, in every format, and keeps your
  cursor where it was. An answer you asked QUILL to remember still comes
  first.
- **Ask before discarding unsaved edits on a conflict** is on to begin with.
  It is the question above, when you do have unsaved edits, and the question
  about a file that was deleted. Turn it off and QUILL says nothing in those
  cases and leaves your text exactly as it is.
- **External-change debounce (milliseconds)** is how long QUILL waits after
  it notices a change before it reacts, so a program that writes a file in
  several steps is dealt with once. The default is 750.

## The rest of the File menu

The **File** menu covers the whole life of a document. Besides opening and
saving, you will find these:

- **Restore Backup...** brings back a saved backup version.
- **Page Setup...** and **Print...** handle paper and printing.
- **Print Studio...** goes a step further. It first tells you what the printout
  will be, for example "3 pages, Letter, default margins", which is a print
  preview you can hear. Then you can choose **all, odd, or even pages**,
  **print in reverse order**, or **skip the first page** (handy when page 1 is
  pre-printed letterhead) before it hands you to the same print dialog Print
  uses.
- **Header and Footer...** builds a header and footer for the current document.
  Start from a preset such as **Title left, page number right**,
  **Filename and date** or **Roman numerals for front matter**, or make your own
  from a small set of pieces (title, filename, date, page number) placed left,
  center or right. Turn on **Different first page** to give page 1 its own
  header and footer, and choose **numeric or Roman** page numbers with any
  starting number. It is saved with the document and printed on every page, from
  Print or Print Studio.
- **Run Current File** runs the saved file with the program it belongs to, and
  **Open Target at Cursor** opens the path or link under the cursor.
- **Rename Current File...** and **Delete Current File...** rename or delete the
  file on disk without leaving the editor.
- **Close Document** closes the current tab.
- **Exit** closes QUILL.

Anything on this menu that could cost you work, such as reloading, restoring a
backup or opening a web address, asks before it acts.

## Making QUILL your text editor

Installing QUILL tells Windows that QUILL can open your text files, Markdown,
rich text, HTML, Word documents, EPUB books and a few more. It doesn't take
anything over. QUILL simply shows up when you choose **Open with** on a file,
and in Windows Settings under **Default apps**, which is where you decide which
app opens what.

Both of the next steps live in one place: open **Settings**, go to the
**General** page, and find **Windows and your files**. A line at the top tells
you which program opens in place of Notepad right now.

The **Make QUILL My Text Editor...** button takes you the rest of the way. It
tells you what Windows lets an app do and what is up to you, then opens the
Default apps page for QUILL. Choose **.txt**, pick **QUILL**, and choose
**Set default**. Do the same for any other type you'd like QUILL to open.
Anything you leave alone stays with the app that opens it now, and you can
change your mind on the same page. This works from a portable copy of QUILL too.

Some programs still start Notepad by name, and so does typing "notepad" in the
Run box. If you'd like QUILL to open for those as well, check
**Open QUILL instead of Notepad** and press **OK** or **Apply**. It's off to
begin with. Because it changes Notepad for everyone on the computer, QUILL asks
first and Windows asks for administrator approval. The checkbox always shows
whether it's on right now, and clearing it puts Notepad back. On Windows 11,
QUILL then shows you where to turn off the newer Notepad's app execution alias,
which would otherwise go around the switch. Uninstalling QUILL puts Notepad back
for you.

Only one program can open in place of Notepad. If QUILL Lite, or another
program, already does, QUILL tells you who before it takes over. QUILL Lite has
the same two settings in its Preferences.

## Working with Different Document Types

QUILL is at its best with plain text, Markdown, HTML, RTF, EPUB, and text pulled
out of other documents. It can also bring in PDFs and scanned pages, with tools
to check what came through, and it understands the structure of Office files.
Here is what each kind of file gets.

### Plain text

Plain text stays plain. QUILL never slips hidden formatting into it.

### Markdown

Markdown gets commands that understand its structure: help with lists, headings,
links and code blocks.

### HTML

HTML gets tag insertion, help with editing its structure, and link handling.

### RTF

When an RTF file contains unsafe embedded content, such as OLE objects, QUILL
removes it as the file opens and tells you. Remote fields, which would fetch
something from the internet, are flagged and wait for your consent instead of
being fetched quietly.

Earlier versions had an optional **Rich text lens** for RTF files, switched on
under Settings, Editing (the "Editor surface" choice) and toggled with an
editing-lens shortcut. It has been retired. To move a document between Plain
text, Markdown, HTML, Rich Text and Word, use **Format > Document Format...**
(`Alt+Shift+F`).

### CSV and TSV

When you open a CSV or TSV file, QUILL asks how: in the CSV grid mode, or in the
normal text editor. You can remember your choice as the default and still switch
modes inside the tab at any time. Grid mode is built for the keyboard and for
screen-reader users who want to edit a table cell by cell without leaving QUILL.

### Office files at a glance

QUILL handles Office files in two different ways, and it helps to know which
one you are getting.

- A **Word document** (`.docx`) is a document you can **edit and save as Word**.
  It opens as rich text, with its headings, lists, bold, links and tables, and
  **Ctrl+S** writes a real Word document back.
- **Everything else** from Office or LibreOffice opens as **readable text**, so
  you can read it, search it and copy from it. QUILL never writes back into
  those files. **Ctrl+S** opens **Save As** so you can keep your text as a new
  file, and the original stays as it was.

This works the same in an installed copy of QUILL and in the portable copy:
both carry everything Word editing needs. QUILL Lite treats each of these files
the same way, with the same code; it has no structured Word view.

| File type | What QUILL does | Can you save back to it? |
| --- | --- | --- |
| Word document (`.docx`) | Opens to edit as rich text. QUILL asks first if the document has things a save would drop, such as comments or pictures. You can also choose the read-only structured Word view (see below) | **Yes.** Ctrl+S saves a real Word document. A document you were warned about is backed up first |
| Word document with macros (`.docm`) | Opens as text to read and copy. Macros never run | No. Ctrl+S opens Save As |
| Word 97-2003 document (`.doc`) | Opens as text when LibreOffice is installed. Without LibreOffice, QUILL tells you how to make a `.docx` | No. Ctrl+S opens Save As |
| OpenDocument text (`.odt`) | Opens as text | No. Ctrl+S opens Save As |
| Excel workbook (`.xlsx`, or `.xls` with LibreOffice) | Opens as text: a "Sheet:" heading for each sheet, then its cells as a text table | No. Ctrl+S opens Save As |
| PowerPoint presentation (`.pptx`, or `.ppt` with LibreOffice) | Opens as text: a "Slide" heading for each slide, then its bullets, tables and speaker notes | No. Ctrl+S opens Save As |
| Excel with macros (`.xlsm`), OpenDocument spreadsheet (`.ods`) or presentation (`.odp`) | **File > Open** does not open these. **Import / Convert Document** reads them into a new document | Not applicable. You get a new, unsaved tab |

**To edit a file that opens as text, make a `.docx` of it.** You can do this
in either of two ways.

- In Word or LibreOffice Writer, choose **File > Save As**, pick **Word
  Document (.docx)**, and open the new file in QUILL.
- In QUILL, open the file, then choose **File > Save As...** with **Word
  Document (\*.docx)** as the type and a new name. QUILL writes a new Word
  document from what you see, and the original is not touched.

A `.docm` saved as `.docx` loses its macros, which is why QUILL never edits one
in place.

**File > Open or Import / Convert Document?** **File > Open** (`Ctrl+O`) opens
the file itself: the tab takes the file's name, and a Word document saves back
to it. **File > Import > Import / Convert Document (OCR)...** always makes a
new, unsaved tab from what it reads, and never points back at the file. Use it
when you want a copy of the text to work on, or for a file File > Open cannot
read, such as a `.xlsm`, an `.ods` or a picture of a page. See *Import /
Convert Document (OCR)* later in this chapter.

### Word (.docx and .doc)

When you open a Word document, QUILL first asks how you want to see it: in the
**structured Word view** or in the **normal text editor**. Check **Remember this
choice for Word files** to stop the question. To change your answer later, use
**How to open Word files** in Settings, on the Editing page: **Ask each time**,
**Plain text** (the normal text editor, where a `.docx` is still edited as rich
text) or **Structured**.

- The **normal text editor** is the one to choose when you want to change the
  document. A `.docx` opens there as rich text that you can edit and save back
  as Word. If the file holds things QUILL's editor cannot keep, such as
  pictures, comments, tracked changes, headers and footers, QUILL names them
  and asks again. For the details, see *Editing Word documents (.docx)* under
  *One Editor, Every Format*: the three choices, the backup, tables and the
  limits. A `.doc` opens there as text, when LibreOffice is installed.
- The **structured Word view** is for reading, and you cannot type in it. It
  reads tables in a straight line, headers and then rows, which is easier to
  follow with a screen reader.

For example, open `agenda.docx` and choose **Open in normal text editor**. You
hear "Opened as Rich Text. Headings and bold are shown formatted." Press
`Ctrl+End`, type a line, and press `Ctrl+S`. The file opens in Word with its
headings still headings and your line at the end.

**Saving to Word.** You can save any document *as* Word. In
**File > Save As...**, choose **Word Document (\*.docx)** (or **Rich Text Format
(\*.rtf)**) in the file type list, and QUILL converts the current content as it
saves. Markdown and HTML structure (headings, lists, emphasis, links, simple
tables) becomes real Word styles, so you can move around the result in Word by
heading, not just look at it. Saving plain text this way gives you a correct but
unformatted document, because plain text has no structure to carry.

**How long opening takes.** The first Word, PowerPoint or Excel file you open
after starting QUILL takes longest, because QUILL loads its document converter
then; later ones in the same session open in under a second for an ordinary
document. Old-style Word files (`.doc`, from Word 97 to 2003) are converted by
LibreOffice when it is installed. When it is not, QUILL now tells you so
straight away, instead of first spending ten seconds or more loading a
converter that cannot read `.doc` at all. Install LibreOffice, or save the file
as `.docx` from Word, and open it again. A PDF's time grows with its number of
pages, because every page is read for its text.

### EPUB

EPUB books get the navigator and reading chapter by chapter.

### PowerPoint (.pptx and .ppt)

QUILL keeps a presentation's structure when it brings it in. Every slide starts
with its own heading, "Slide 3: Quarterly results" (just "Slide 3" when the
slide has no title), so **Next Heading** (`Ctrl+Alt+H`) moves one slide at a
time and you hear the slide number before the title. Under each heading:

- the slide's bullets, as list items indented by their level;
- any tables, under a **Tables** heading, as text tables you can Tab through;
- the description of each picture, as "[Image: ...]", when the author wrote one;
- the speaker notes, under a **Notes** heading.

Slides arrive in the order the presentation shows them, even when they were
rearranged in PowerPoint. A hidden slide is included and says "(hidden slide)"
after its title, because its words are still the author's.

### Excel-style spreadsheets (.xlsx and .xls)

Spreadsheets come in as text, with their structure kept. Each sheet starts with
its own heading, "Sheet: Budget", so **Next Heading** (`Ctrl+Alt+H`) moves
sheet by sheet. The cells follow as a text table whose first row is the header
row. Numbers read the way you would say them (950, not 950.0), true and false
as TRUE and FALSE, and dates as dates (2026-11-01, not the number Excel stores).
A formula shows the result Excel last calculated. Blank rows are left out.

So that a huge workbook cannot freeze QUILL, each sheet is read up to 2,000
rows and 50 columns. When a sheet is bigger, QUILL opens what fits and says so
as the file opens ("part of it was too large and was cut short"), and the
**Document Intake Report** names the sheet.

### Office files QUILL reads by itself

QUILL reads Word, Excel, PowerPoint and OpenDocument files with its own
built-in readers. Nothing has to be downloaded first, and nothing is uploaded.
QUILL's own reader is always the **first** choice, in every place a file comes
in: **File > Open**, **Import / Convert Document**, Recent Documents, a file
opened from File Explorer, and QUILL Lite. The optional MarkItDown converter is
asked only when QUILL's own reader cannot read a file, or finds no text in it,
and MarkItDown can read that format. You never need to install anything.

These readers make the **text** you get from a file that opens as text (see
*Office files at a glance*): Excel, PowerPoint, OpenDocument, `.docm`, a `.docx`
you open for reading only, and everything Import / Convert Document reads. A
`.docx` you open to edit goes through QUILL's Word editing instead, described
in *Word (.docx and .doc)* above.

**Why it matters: speed.** MarkItDown takes a long time to start: on a test
computer, the first Word file after starting QUILL from source took 12 to 17
seconds to open when MarkItDown read it, almost all of that spent loading
MarkItDown itself. QUILL's own Word reader opens the same file in about a
second, and later opens in about half a second. A spreadsheet or a slide show
opens in a fraction of a second.

**What you get is the same or better.** On QUILL's own test files, QUILL's
readers keep everything MarkItDown kept and add some things it did not: the
document's title as a heading, a pipe character inside a table cell kept in
its cell, the first row of a Word table as the table's header row, a heading
for every sheet ("Sheet: Budget") and every slide ("Slide 2: Figures"), nested
bullets on slides, true and false shown as TRUE and FALSE instead of 1.0 and
0.0, and an empty spreadsheet cell left empty instead of the word NaN.
Two things MarkItDown did better have been fixed in QUILL's reader: numbered
lists are now numbered 1, 2, 3 in the text itself (they used to read "1, 1,
1"), and **equations** in a Word document now come through as text, written
the way QUILL's own **Insert Equation** writes them, for example
`\(a^{2}+b^{2}=c^{2}\)`. One difference remains on purpose: a line break inside
a Word paragraph (Shift+Enter) ends in a backslash, which is how Markdown
writes a hard line break you can hear and find; MarkItDown left no mark.

If you prefer MarkItDown for Word files anyway, set **Word document reading
engine** to **MarkItDown first** (see "Choosing a conversion engine").

| Format | How to open it | What comes through |
| --- | --- | --- |
| Word (.docx, .docm) | **File > Open** (`Ctrl+O`) or **Import / Convert Document** | Headings, bulleted and numbered lists with their levels, tables, line breaks, picture descriptions, equations (as LaTeX text) |
| OpenDocument text (.odt) | **File > Open** or **Import / Convert Document** | Headings, nested lists, tables, line breaks |
| Excel (.xlsx) | **File > Open** or **Import / Convert Document** | One heading per sheet; each sheet as a table |
| Excel with macros (.xlsm), OpenDocument spreadsheet (.ods) | **Import / Convert Document** | The same |
| PowerPoint (.pptx) | **File > Open** or **Import / Convert Document** | One heading per slide; bullets, tables, picture descriptions, speaker notes |
| OpenDocument presentation (.odp) | **Import / Convert Document** | The same |
| Word, Excel or PowerPoint 97-2003 (.doc, .xls, .ppt) | Either, when LibreOffice is installed | Whatever LibreOffice carries into the newer format, then as above |

What does not come through: bold, italic, fonts and colours; headers and
footers; footnotes and comments; charts and SmartArt; and pictures themselves
(only the descriptions their authors wrote). A macro is never run.

**An example.** Press `Ctrl+O` and open `Budget.xlsx`. QUILL says it opened the
file, "read by QUILL's own Excel reader", and that it has 2 sheets. The
document starts at "Sheet: Budget". Press `Ctrl+Alt+H` and you are on
"Sheet: Notes". Open the same file with **File > Import > Import / Convert
Document (OCR)...** instead and it opens in a new, unsaved tab, and QUILL says
"Opened Budget.xlsx as editable text, read by QUILL's own Excel reader.
2 sheets. Nothing was uploaded."

**Older Office files (.doc, .xls, .ppt).** QUILL has no reader of its own for
the Office 97-2003 formats. When LibreOffice (free, from libreoffice.org) is
installed, QUILL asks it to make a temporary copy in the newer format and reads
that; your file is not changed. When LibreOffice is not installed, QUILL tells
you what to do instead: open the file in Word, Excel or PowerPoint (or in
LibreOffice), choose **File > Save As**, pick the newer type (for example
"Word Document (.docx)"), and open that copy.

**Files QUILL cannot read.** A password-protected Word, Excel or PowerPoint file
is named as password-protected, with the fix: remove the password in the
program that made it (in Word, the Info page of its File menu), save, and try again. A damaged file is
named as damaged, with the advice to open it in the program that made it and
save it again.

### PDF and OCR-derived text

PDFs and scanned pages are where QUILL's tools for checking extracted text
matter most. Treat them as a proofreading step, not an extra. The next topics
cover opening PDFs, OCR and those checks.

## What happens when you save in another format

**File > Save As** truly converts your document to the format you pick in the
"Save as type" list. It never just renames the file. QUILL's editor holds your
text in one clean form, and Save As writes that text out in the format you
chose. Here is what each choice does:

- **Markdown (.md)**: your text is written exactly as it is in the editor.
  Markdown is QUILL's own format, so nothing is converted or lost.
- **Text (.txt)**: also written exactly as it is, Markdown markup included, so a
  plain-text file comes back just as it went out. If you want the markup
  *stripped*, with headings and emphasis turned into plain words, use
  **File > Save As Plain Text** instead. That command also offers to keep your
  formatting in an Illumination. A third route is
  **Format > Document Format...** with Plain text chosen, which *asks* which of the two
  you want. Save As leaves your file byte for byte as it was, so a .txt you
  opened comes back unchanged.
- **HTML (.html)**: converted to a complete web page with your document's title,
  ready for a browser.
- **Rich Text (.rtf)**: converted with all its formatting. Fonts, sizes, colors,
  highlights and alignment all carry over.
- **Word (.docx)**: converted to a real Word document. Headings become Word
  heading styles, so Word and screen readers can move by them. Each line in the
  editor becomes one Word paragraph, so your line breaks stay exactly where they
  were. Hidden-codes formatting (font, size, color, highlight, alignment)
  becomes real Word formatting.
- **An extension QUILL cannot write**, for example typing `notes.pdf` in the
  name box: QUILL refuses rather than writing a broken file. For PDF, ODT and
  EPUB it offers to open **File > Export**, which makes them properly with
  Pandoc.

**You keep editing QUILL text.** After a Save As that converts, the file on disk
is Word (or HTML, or RTF), but the editor still holds QUILL's clean text, and
every `Ctrl+S` after that converts it again. QUILL tells you this after the
save: "Saved as report.docx, Word format. You are still editing QUILL text; each
save converts it to Word." The window title and tab title change to the new name
straight away, and from then on `Ctrl+S` saves quietly to the same file.

**Your originals are protected.** If you opened a PDF, EPUB, spreadsheet or
presentation, what you are editing is text taken out of it, and the original
file cannot hold your changes. Pressing `Ctrl+S` on one of these never
overwrites the original. QUILL explains why and opens Save As, so your edits go
into a new file in a format that can hold them.

### The name you type decides: a worked example

The ending you type always wins over the **Save as type** list, and capitals do
not matter. Suppose you have an untitled document of meeting minutes with a
heading, some bold and a short list:

1. Press `Ctrl+Shift+S` (**File > Save As...**).
2. Type `Minutes.DOCX` in the name box. The type list can show anything; it is
   the name that counts.
3. Press Enter. QUILL writes a real Word document: Word opens it, the heading
   is a Word heading you can move to by heading, the bold is bold, and the list
   is a list. You hear "Saved as Minutes.DOCX, Word format. You are still
   editing QUILL text; each save converts it to Word."

The same document saved under other names:

| You type | What is written |
|---|---|
| `minutes.txt` or `MINUTES.TXT` | Your text exactly as it is, markup included |
| `minutes.md` | Your text exactly as it is |
| `minutes.html` | A complete web page, with the heading, bold and list as HTML |
| `minutes.rtf` | Rich text with its formatting |
| `minutes.docx` | A real Word document, as above |
| `minutes` with **Word Document** selected | `minutes.docx`, a Word document |
| `minutes.txt` with **Word Document** selected | `minutes.txt`, plain text: the typed ending wins, and no `minutes.txt.docx` is made |
| `minutes.pdf`, `.odt` or `.epub` | Nothing yet: QUILL offers **File > Export**, which makes these properly |
| `budget.xlsx` or another format QUILL only reads | Nothing: QUILL says it cannot save that format |

**Cancel** or **Escape** in the Save As window writes nothing and leaves the
document as it was.

QUILL Lite has no Word writer. Typing a `.docx` name there gets a short message
saying so and naming Rich Text (`.rtf`), which Word opens; nothing is written.
Use QUILL when you need a `.docx`.

### What carries over between formats

QUILL converts everything through one clean form inside, so what survives a Save
As or a conversion depends on the feature, not on the pair of formats. This
table is what QUILL's own tests check. **Yes** means it carries over as that
format's own structure. **Partly** means it carries over, but as text or as
QUILL's portable markup rather than a real object in that format. **No** means
it is not kept. The numbers point to the notes after the table.

| Feature | Markdown | HTML | Word (.docx) | Rich Text (.rtf) | Plain text (.txt) |
| --- | :---: | :---: | :---: | :---: | :---: |
| Headings (1 to 6) | Yes | Yes | Yes | Yes | No |
| **Bold**, *italic* | Yes | Yes | Yes | Yes | No |
| Underline | Partly (1) | Yes | Yes | Yes | No |
| Strikethrough | Partly (1) | Yes | Yes | Yes | No |
| Superscript / subscript | Partly (1) | Yes | Yes | Yes | No |
| Text colour / highlight | Partly (1) | Yes | Yes | Yes | No |
| Font family / size | Partly (1) | Yes | Yes | Yes | No |
| Links | Yes | Yes | Yes | Yes | No |
| Bullet lists | Yes | Yes | Yes | Yes | No |
| Numbered lists | Yes | Yes | Yes | Yes | No |
| Blockquotes | Yes | Yes | Partly (2) | Partly (2) | No |
| Code blocks | Yes | Yes | Partly (2) | Partly (2) | No |
| Horizontal rule | Yes | Yes | Partly (2) | Partly (2) | No |
| Tables | Yes | Yes | Yes | Partly (3) | No |
| Images | Partly (4) | Yes | No (4) | No | No |
| Paragraph alignment | Partly (1) | Yes | Yes | No | No |
| Page breaks | Partly (1) | Yes | No | No | No |

Notes:

1. **In Markdown**, underline, strikethrough, superscript and subscript, colour,
   highlight, font, alignment and page breaks are kept in QUILL's *hidden-codes*
   markup. You don't see it while you edit, and it turns into real formatting
   when you export to HTML, Word or RTF. Markdown itself has no standard way to
   write these, so another Markdown app shows QUILL's `[text]{...}` codes
   instead of the effect.
2. **Blockquotes, code blocks and horizontal rules** belong to Markdown and show
   properly in HTML. In Word and RTF they appear as their Markdown markers (`>`,
   ` ``` `, `---`) rather than a Word quote or code style.
3. **Tables** travel as real tables between Markdown, HTML and Word. A Word
   table you *open* in QUILL becomes a clean Markdown (GFM) table that you can
   edit and move around in. Markdown and HTML tables stay as they are. A table
   you *save to* Word becomes a real, editable Word table with a header row that
   repeats, so a screen reader announces the column headers. In rich text, and
   in an `.rtf` file, a table is a real table with its header row marked.
4. **Images**: an image *reference* (`![alt](path)`) survives a trip through
   Markdown and becomes `<img>` in HTML. QUILL does not put image files inside
   Word documents, and images inside a Word document you open are not brought
   into the text.

**Plain text (.txt)** never carries formatting. That is what plain text is for.
Use **Save As Plain Text** when you want the markup flattened on purpose, with
the option to keep your formatting in an Illumination.

### Choosing a conversion engine

More than one converter can handle a Word document, and each gives a slightly
different result. QUILL lets you choose, and describes what each choice gives
you in plain words. The defaults suit almost everyone. The choices are there for
when they don't.

- **Word document reading engine** (**Settings > Editing**) decides how a
  `.docx` becomes editable text when you open it. **Auto (QUILL's own reader
  first)** is the default: QUILL's own Word reader reads the file in about a
  second, keeping headings, numbered and bulleted lists, tables, line breaks,
  picture descriptions and equations, and MarkItDown is asked only if that
  reader fails. **MarkItDown first** asks MarkItDown before QUILL's own reader.
  It keeps the same headings, lists and tables in its own style, but the first
  Word file you open after starting QUILL waits 10 to 20 seconds while
  MarkItDown loads; when MarkItDown cannot run, QUILL's own reader steps in.
  Neither keeps images, comments or fonts. **Pandoc** keeps more of the
  structure, so footnotes and complex tables come through better. It needs
  Pandoc installed. If Pandoc is missing, this setting quietly acts as Auto, so
  your file still opens. This setting is only about Word files: spreadsheets
  and slide shows are always read by QUILL's own reader first.

  For example: you open a 40-page Word report each morning and want it to
  appear at once. Leave the setting on **Auto**. If one particular document
  comes in with a table you think MarkItDown handles better, choose
  **MarkItDown first**, open it, and set it back afterwards.
- **Word document saving engine** (**Settings > Editing**) decides how your
  text becomes a `.docx` when you save. **Auto** (the default) uses the native
  writer. **Native** keeps QUILL's formatting codes (fonts, sizes, colors,
  highlights, alignment) and makes each line in the editor one Word paragraph.
  It is the best choice for documents written in QUILL. **Pandoc** turns
  structure into Word styles (headings, lists, tables, links and footnotes) but
  drops font, size and color codes.
- In the **Convert File dialog**, the **Conversion engine** choice (Auto, Pandoc
  or MarkItDown) applies to one conversion at a time. As you arrow through it, a
  description under the choice changes, so you hear what each engine will do
  before you convert. MarkItDown only works when the source is Word, PowerPoint,
  Excel or PDF and the result is Markdown or plain text. If you choose it for
  anything else, QUILL says so and offers Pandoc. It never swaps in an engine
  you did not pick. If MarkItDown itself cannot run on this computer, QUILL's
  own reader converts the file instead and the announcement says so, for
  example "Converted to report.md. MarkItDown could not run here, so QUILL's
  own Word reader read the file instead."

## Import and Export

QUILL can convert between the formats the people around you use, without you
leaving the editor. **File > Import** brings a document from another program
into QUILL as a new tab. **File > Export** saves the current document as a
different file type. Both use Pandoc and work in the background, so the editor
never freezes. Exports keep your line breaks exactly: one line in the editor is
one paragraph in the exported document, in every format.

**Import (File > Import)** reads Markdown, CommonMark, GitHub-Flavored Markdown,
HTML, Word documents (`.docx`), OpenDocument Text (`.odt`), Rich Text (`.rtf`),
plain text, CSV and TSV tables, EPUB books, and LaTeX or TeX.

**Export (File > Export)** writes the same set, plus PDF and a
**DAISY Talking Book**, which are export only.

A few examples cover most of what people do:

- Choose **File > Import > Word Document**, pick a `.docx`, and a new Markdown
  tab opens with the document ready to edit.
- Choose **File > Export > EPUB Book**, pick a folder, and QUILL writes an EPUB
  next to your current file.
- Choose **File > Export > PDF** to publish a finished document.

**A web page you can share.** **File > Export > HTML...** (`Ctrl+Alt+Shift+End`)
saves a copy of your document as one web page: its styles are inside it, it has
no scripts, and it says what language it is in, so you can email it or put it on
a website as it is. Task lists show as check boxes and ~~struck-out~~ text is
struck out. The document you are editing stays the document you are editing.
If notes are written into the file, QUILL asks whether to include them in the
page, marked as notes; No is the default, so a note never ends up in a page by
accident.

Equations are written into the page as MathML, so the page needs no script and
nothing from the internet to show them, and NVDA and JAWS read them as maths.
When Pandoc is installed it writes the page from a Markdown document, and
pictures come with it: a picture with a relative path, such as
`![Floor plan](images/plan.png)`, is found beside your document, and with
Pandoc 2 or 3 the picture itself is put inside the page, so it still shows
when you email the page or move it on its own. Save the document first, so
QUILL knows which folder its pictures are in. A picture from the web, such as
`![Logo](https://example.com/logo.png)`, stays a link to the web, because
exporting never downloads anything.

**Getting there by keyboard.** `File > Import` and `File > Export` are ordinary
menus: open the menu, arrow down and press Enter. There is no single key for the
whole list, because choosing the format is the point of the command. The
quickest way is the Command Palette (`Ctrl+Shift+P`): type `import` or `export`
and pick the format from the list.

**After the conversion.** When the new file is one QUILL can edit (Markdown,
CommonMark, GFM, HTML, plain text, CSV or TSV), QUILL asks whether to open it in
a new window. Press **Yes** to open it, or **No** to carry on where you were.
PDF, DOCX, EPUB, ODT and RTF don't ask, because QUILL cannot edit those
directly. Instead a message tells you where the file was saved and copies the
path to the clipboard, so you can paste it into File Explorer.

**Exporting over an earlier file is safe.** Say you exported `report.docx`
yesterday and export again today to the same name. Pandoc builds the new file
under a temporary hidden name in the same folder, and only when it has
finished successfully does QUILL swap it in over yesterday's. If the export
fails, times out or you cancel it, yesterday's `report.docx` is exactly as it
was, no half-written file is left behind, and you hear "Pandoc export failed"
with the reason. The same holds for every conversion that writes a file
through Pandoc: Convert File, batch conversion, braille and review exports.

**Other formats.** Both menus end with **Other Pandoc Format...**. It shows a
list of every other format Pandoc can read (on Import) or write (on Export),
such as CommonMark and GitHub-Flavored Markdown. Arrow to the one you want and
press Enter, and the conversion runs just like the named ones above. On
Export, the list opens on your **Default export preset** (Settings > General;
HTML unless you change it), so if you nearly always export the same way,
Enter alone does it.

**What it does not do.** Importing a PDF this way is not supported, because
Pandoc cannot do it reliably. Use Import / Convert Document, described below,
and for print-to-braille work, the braille and DAISY tools.

### DAISY Talking Book export

**File > Export > DAISY Talking Book** saves the current document as a DAISY
2.02 text-only talking book. DAISY is the accessible book format read by DAISY
software and by players such as the Victor Reader Stream, Plextalk and APH
units. A DAISY book is a *folder*, not a single file, so the name you choose
becomes a folder holding `ncc.html`, `content.html` and `book.smil`. Your
headings become the player's navigation points, and Markdown styling is
flattened into clean, readable text. The book has no audio, so a player reads it
with its own text-to-speech. You can also open the folder in APH Book Wizard
Producer to record or synthesize a full text-and-audio book. The export reads
what is on screen, so you do not have to save first.

### Batch Conversion

When you have a whole folder of documents to convert, opening them one at a time
is slow going. **File > Import > Batch Conversion...** (or
**File > Export > Batch Conversion...**, which opens the same wizard) converts a
whole folder in the background. The key is the QUILL key, then `B`
(`Ctrl+Shift+Grave` then `B`).

Use the single-file Import and Export menus for one document. Use the wizard
when you have a folder of documents, when every file needs the same treatment,
and when you are happy to let it run while you keep writing.

#### The wizard, page by page

1. **Introduction.** A short summary, then a check for Pandoc and its version.
   If Pandoc is not installed, the page says so, and Start stays unavailable
   until you install Pandoc 3.x from <https://pandoc.org>.
2. **Folder and options.** A folder picker, an **Include subfolders** checkbox,
   an **Output layout** choice (Same folder as source, or Output subfolder per
   source folder), and an **Overwrite** choice (Ask each time, Never, Always).
   These start from your Settings, and the last folder you used is remembered
   for next time.
3. **Format and profile.** A **Direction** choice (Import into QUILL, or Export
   from QUILL), a list of source formats and a list of target formats from the
   main Import and Export set, and a picker for the seven built-in conversion
   profiles.
4. **Review and start.** A plain-text summary of the whole plan. Press **Start**
   to begin the batch and close the wizard.

QUILL keeps each file's name and changes only the extension: `report.docx`
becomes `report.md` (or `report.html`, `report.epub`, and so on). With
**Output subfolder per source folder** (the default), the results go into a new
`Output/` folder inside the source folder. With **Same folder as source**, they
go next to the originals.

#### Profiles

The profile picker offers seven ready-made profiles. Each one comes with a plain
description that your screen reader reads before you press Start.

- **Clean Word Document**: `report.md` becomes a polished Word document, with no
  Markdown left showing.
- **Accessible HTML Page**: a single HTML page with a title block and `lang`
  metadata, ready for an accessibility check.
- **EPUB Book**: an EPUB ready for publishing yourself, with a table of contents
  and EPUB-3 metadata.
- **GitHub README**: GitHub-Flavored Markdown with no wrapper, ready to paste
  into a repository.
- **Print PDF**: a PDF with standard PDF metadata. Pandoc picks the right engine
  for your computer.
- **Instructor Handout**: a print-ready PDF with 1-inch margins and numbered
  top-level sections.
- **Plain Text for Screen Readers**: plain text with no HTML wrapper, no smart
  quotes and a fixed 80-column width. The right choice for feeding a
  text-to-speech engine.

#### Overwriting existing files

The three overwrite choices save you from answering a question for every file:

- **Ask each time**: QUILL lists every result that would replace an existing
  file and asks once, with a single Yes or No. If you say No, those files are
  skipped.
- **Never**: existing files are skipped automatically. The Status Page counts
  them under *skipped*, so the totals still add up.
- **Always**: existing files are replaced without asking. Useful when you run
  the same batch again.

#### Following progress

To watch the batch, open the Status Page (**Help > Status Page**). The Tasks &
Downloads tab shows a row for it as it works. The first row is
`Batch conversion: scanning <folder>`, followed by one row per file.

When the batch is done, QUILL says one line, through the announcement backend
you have set up, with the converted, skipped and failed counts and how long it
took:

> "Batch conversion complete. 12 of 14 files converted in 4.2 seconds. 2
> skipped."

That line follows your verbosity settings under **Settings > Accessibility and Announcements**.
The Status Page row updates either way, so sighted and low-vision users see the
same result. A short report then lists every file that gave a warning or failed,
with the exact error.

#### Batch settings

Three Settings choose what the wizard starts with:

- **Include subfolders in batch conversion**: on or off, on by default (`True`).
- **Overwrite behaviour for batch conversion**: Ask each time (the default),
  Never or Always.
- **Default output layout for batch conversion**: Output subfolder per source
  folder (the default) or Same folder as source.

You can change any of them in the wizard for one run. To change what it starts
with every time, use Preferences.

## Import / Convert Document (OCR)

**File > Import > Import / Convert Document (OCR)...** (also on
**Tools > Reading and Dictation > OCR and Document Conversion**) is QUILL's rescue tool for documents that are
hard to read: locked-down Office files, EPUBs, scanned PDFs and photos of pages.
It follows one rule: **free first, local first, and nothing is ever uploaded**
without your say-so.

Here is how a conversion goes:

1. **The file's own text is read first.** Word, Excel, PowerPoint,
   OpenDocument, HTML, EPUB, CSV, and PDFs that already contain text convert
   straight away on your computer and open as clean, editable text in a new
   tab. No account, no key, no upload, no cost, and nothing to download: QUILL
   has its own reader for every one of these (see "Office files QUILL reads by
   itself"). For Word, Excel, PowerPoint and OpenDocument files QUILL's own
   reader goes first, and the optional MarkItDown converter is asked only if it
   cannot read the file; for HTML, EPUB, CSV and Excel 97-2003 (.xls),
   MarkItDown goes first where it can run, and QUILL's own reader steps in
   where it cannot. Either way QUILL says
   who read the file and what it found, for example "Opened Budget.xlsx as
   editable text, read by QUILL's own Excel reader. 2 sheets. Nothing was
   uploaded." **Review Last OCR Result...** lists the same facts afterwards.
   A PDF is read by the same PDF reader **File > Open** uses, so its pages come
   through with their page breaks, and QUILL tells you how many pages it read.
2. **A scanned document is noticed, not dumped on you.** If a PDF comes back
   nearly empty, QUILL says "It looks scanned or image-based" and *asks* whether
   to run free OCR on your computer. Yes runs it. No opens the empty result
   anyway. Cancel imports nothing. QUILL never opens a blank result without
   telling you, and never runs OCR without asking.
3. **OCR on your computer rescues the scan.** The local Tesseract engine reads
   each page on your own computer (it uses only the processor and works
   offline). It marks where each page begins with a searchable `<!-- Page N -->`
   marker and tells you how it is going ("Recognizing page 3 of 12..."). When it
   is not confident about what it read, QUILL tells you plainly, so you know to
   check the result.
   **No Tesseract? Windows OCR does it instead,** with no download and no
   question: it is the OCR built into Windows 10 and 11, and it reads the
   languages you have in Windows Settings. It cannot say how confident it is, so
   check the text yourself. When Tesseract is installed, QUILL uses Tesseract.
   **A picture of a page works the same way** (since 2026-10-17): a `.png`,
   `.jpg`, `.tif` or other image goes straight to OCR, with Tesseract when it is
   installed and Windows OCR when it is not. Before, a picture needed
   Tesseract, and without it the conversion stopped with a message about
   installing it. For example, choose a photo of a letter, `letter.jpg`, and
   you hear "Opened letter.jpg from Windows OCR on this computer. Nothing was
   uploaded. Check the text; OCR makes mistakes."

QUILL Lite has the same command, on its File menu, with the same readers and
the same sentences (since 2026-10-17). It never offers to download Tesseract
and has no cloud OCR, and its result opens in a window rather than a tab.

Other problems get their own clear message instead of the scanned-PDF question.
A file that is really corrupt is reported as *damaged*, with a note that OCR
won't help (repair it or export it again from where it came from). A PDF on a
computer with no text extractor points you to
**Help > Download Optional Components...** (the "PDF and Office text
extraction" item in its list) instead of claiming it is scanned. The installed apps come with a PDF reader, so
this only happens with a pip or source install. A *password-protected* PDF is
handled separately, as described next: Import / Convert Document tells you to
open it with **File > Open**, which asks for the password.

Office files get the same kind of plain message. A password-protected Word,
Excel or PowerPoint file is named as password-protected, with the fix. An Office
97-2003 file (.doc, .xls or .ppt) is read through LibreOffice when it is
installed; when it is not, QUILL tells you to save it in the newer format from
Word, Excel, PowerPoint or LibreOffice and import that copy. Earlier versions
said "MarkItDown is not installed" for every Office file in the installed app,
and the download it pointed to could not fix it. That message is gone.

### Opening a scanned PDF with File > Open

You don't have to go to Import / Convert Document to read a scanned PDF. When
you open one with **File > Open**, QUILL notices there is no text in it (or
very little) and asks whether to read it with OCR on this computer. Nothing is
uploaded, and the PDF is not changed.

- **Yes** reads the pages, with Tesseract if it is installed and Windows OCR
  if not. The status bar counts the pages as it goes. The text then replaces
  the note in the PDF's tab, with its pages, and the tab counts as unsaved work
  because that text is not saved anywhere yet. If you typed in the tab while it
  was reading, the text opens in a new tab instead, so nothing you wrote is
  lost.
- **No** leaves the PDF open as it was.

QUILL Lite asks the same question in the same words.

### Opening a password-protected PDF

When you open a PDF that is locked with a password, QUILL asks for the password
and reads the document. You don't need to remove the password in another program
first. Type the password and the PDF opens. If it is wrong, QUILL tells you and
lets you try again. Press **Cancel** to stop opening it.

**The password is used only to open that one file for reading.** QUILL
**never stores, logs or remembers it**, so if you close the file and open it
again, it asks again. PDFs that are technically locked but open with an empty
password (they only restrict permissions) open with no question, as before.

### A PDF's bookmarks come across

If a PDF has an outline, the chapters and sections you would see in Adobe
Reader's bookmarks pane, QUILL adds those entries to its own
bookmark list (**List Named Bookmarks...**, `Alt+Shift+G`) when you open the file, as it does for
Word and EPUB structure. Each bookmark takes you to its title on its page: if
"Chapter 2" starts halfway down page 14, the bookmark lands on "Chapter 2", not
on the top of the page. When QUILL cannot find the title at the start of a line
on that page, the bookmark goes to the top of the page instead. Two entries
with the same title, such as a "Summary" in every chapter, stay two bookmarks
("Summary" and "Summary (2)"), each at its own place. This happens once, the
first time you open the PDF. If you already have bookmarks in the file, or you
later rename or delete some of those bookmarks, opening the file again will not
change them, bring them back or make duplicates. A PDF with no outline opens as
usual.

The outline is also in **Go To** (`Ctrl+G`), as its own **Outline** choice.
Each entry says its title and its page, such as "Chapter 2, page 14". An entry
that sits inside another says its level too, such as "Summary, level 3, page
15", so you can hear the outline's shape. The level is only a description: it
does not turn the line into a heading. An entry always takes you to its title
on that page, even after you have edited the text above it.

### How QUILL chooses the text of each page

A PDF can be read more than one way, and the ways do not always agree. One
reader may spell a widely spaced line out a letter at a time ("W i d e l e t t
e r s"), while another reads it as words; one may run two columns together line
by line, while another reads down the first column and then the second. QUILL
does not simply take the first answer it gets. It decides **page by page**:

1. **The usual reader goes first.** For most pages its text is clean, and QUILL
   keeps it straight away, so an ordinary PDF opens as quickly as it always did.
2. **A doubtful page gets a second and third look.** If the first reading has
   signs of trouble (letters one at a time, words run together, characters that
   cannot be read, a line of text per word), or the page looks as if it is set
   in two columns, QUILL reads that page again in two other ways and keeps
   whichever reads best.
3. **"Reads best" means fewest problems, not most text.** QUILL counts what a
   listener would trip over: characters it could not read, words broken into
   single letters, words glued together, one word per line, part of the page
   missing, and columns read across instead of down. A short title page, a page
   of figures, or a page in Greek or Japanese is not marked down for being
   short or for not being English.

The repairs described below run on every reading, and QUILL compares the
readings both before and after repair, so a repair that would make a page worse
is not used on it.

**What you hear when a page is doubtful.** When the PDF opens, QUILL names the
pages that may still read poorly, for example: "Opened report.pdf. 12 pages.
extracted by pdfplumber + pypdf. quality 81/100. Pages 3 and 7 may read
poorly." A page is named when it still reads badly in
every way QUILL tried, when it holds characters QUILL could not read, or when it
is only a picture (a scanned page inside an otherwise ordinary PDF). A blank
page is never named: there is nothing on it to miss. The **Document Intake
Report** lists those pages with the reason for each, such as "Page 7: 2
characters could not be read", and says which reader's text each page uses.

**What QUILL does not do.** It does not guess. A character that the PDF's own
font gave no meaning to is left in the text, rather than deleted or swapped for
a letter that might be wrong; the page is named instead, so you know to check
it. QUILL does not turn anything into headings, tables or other structure: a
heading stays a line of text, and a row of a table stays a line with its numbers
in order. Nothing is uploaded, and OCR never runs unless you say yes (see
"Opening a scanned PDF with File > Open", above).
The optional MarkItDown converter, if you have it, is only asked about a PDF
that still reads poorly, and its text is used for a page only when it keeps the
PDF's pages and reads clearly better. The PDF itself is never changed.

**Limits.** QUILL reads the first 200 pages of a very long PDF and says so.
Columns are only put in order when the gap between them is clear; a page with
three columns, or columns that run around pictures, can still come out mixed.
Tables come through as lines of text, and pictures do not come through at all.
The same rules apply in File > Open, Import / Convert Document, Document Q&A,
and in QUILL Lite.

### The text from a PDF is repaired before you read it

A PDF does not store sentences. It stores where each letter was printed on the
page. So what comes out is a picture of the page rather than the words the
author typed, and read aloud that can be rough going. QUILL fixes four things as
it opens the file, page by page:

- **Words split across lines are joined again.** Print layout breaks long words
  with a hyphen at the end of a line, so "inter-" on one line and "national" on
  the next would be read as two words, and a search for "international" found
  nothing. QUILL joins them. A hyphen that belongs to the word stays:
  **Anglo-Saxon**, **2018-2019** and an identifier such as **ISBN-** are left
  exactly as written, and a word that is always hyphenated, such as "self-" at
  the end of one line and "aware" on the next, becomes **self-aware**.
- **Paragraphs are put back together.** Every printed line arrives as its own
  line of text, so speech would stop at the edge of the page instead of the end
  of the sentence, and moving to the next paragraph moved one printed line.
  QUILL joins lines that were only broken because the page ran out of room.
  Blank lines, list items (including "a)" and "iv." items), headings, short
  deliberate lines and finished sentences keep their breaks, so lists stay lists
  and paragraphs stay separate. A heading such as "CHAPTER TWO" or "2.1
  Methods" under a long line of text stays on its own line instead of being
  swallowed into the paragraph, and so do address lines, rows set out in
  columns, and rows of figures, so two long rows of a table stay two rows.
- **Spaced-out headings are closed up.** A designer's letter-spaced title comes
  through as "C H A P T E R  O N E", which a screen reader spells one letter at
  a time and a search never matches. It becomes "CHAPTER ONE". Ordinary text is
  left alone: a line such as "A B testing" is not a heading and is not touched,
  and a whole sentence spaced out with no gaps between its words is not closed
  up into one long word (QUILL looks for a better reading of that page
  instead).
- **Missing joined letters are restored.** The joined "fi", "fl" and "ff" shapes
  a typesetter uses are often stored as characters that mean nothing outside the
  document's own font, so a screen reader reads *nothing* where they were, and
  "office" is announced as "o ce". QUILL turns them back into letters where
  they sit inside a word. Any other character with no meaning is **kept**, not
  deleted: deleting it could quietly change what the page says (a font that
  stored its "x" that way would turn "next box" into "net bo"). Instead QUILL
  names the page as one that may read poorly, so you know to check it.

These repairs are careful. When a case could go either way, QUILL leaves the
text as it found it, and a PDF whose text is already clean comes through
unchanged. They never cross from one page to the next, so **Go To Page** and the
page count stay exact.

### Installing the OCR engine

The OCR engine is a free, one-time download of about 48 MB:
**Tools > Reading and Dictation > OCR and Document Conversion > Install Local
OCR Engine (Tesseract)...**. QUILL
fetches the official installer from its own verified release, checks it byte for
byte, and opens it for you to finish. It never installs anything silently. If
Tesseract is already on your computer (or installed with Homebrew on a Mac),
QUILL finds it and uses it.

### The optional Datalab Chandra OCR cloud service

Some documents are too hard even for OCR on your computer: complex tables,
forms, handwriting, crowded columns, very poor scans. For those, QUILL supports
an optional paid cloud service, Datalab Chandra OCR, using your own key. QUILL
only offers it *after* the OCR on your computer comes back weak (or when you
turn down installing the free engine).
**Every single upload requires your explicit consent** in a window that names
the service, reminds you to think about private, medical, legal or financial
content, and notes that Datalab deletes results from its servers about an hour
after processing. A file whose name suggests sensitive content (tax, medical,
legal and similar) gets an extra CAUTION line. QUILL decides that from the name
only and never looks inside the file to decide. There is no "don't ask again".

To set it up, choose
**Tools > Reading and Dictation > OCR and Document Conversion > OCR Service Settings...**.
This opens the **AI Hub Services tab**. Turn the service on, paste your Datalab
API key (it is kept in the Windows credential vault, never in a settings file),
choose the default mode (Fast, Balanced or Accurate) and output (Markdown is
recommended), and press **Test Connection**. The test checks your key and the
address and uploads no document. Other buttons open the provider's website, key
page, pricing, privacy documents, API documents and list of supported file types
in your browser, and **Copy Service Summary** copies a description with no
secrets in it, for support requests.

### Checking and tidying up after OCR

**Review Last OCR Result...** opens a checklist for your most recent conversion:
which service made it, the page count, how confident the recognition was, and,
for OCR on your computer, every line it was unsure of, listed as
`Page N: [confidence] text`. Arrow through the flagged lines, then search the
converted document for the page marker (for example `<!-- Page 3 -->`) to jump
to the trouble spot. That way you check by ear exactly where it is needed,
instead of proofreading everything again.

**Delete OCR Temporary Files** clears any leftover job files from QUILL's data
folder and tells you what it removed. The local tools normally clean up after
themselves. Converted results live only in the open, unsaved document until you
choose to save.

**OCR and Conversion Services...** explains each service in plain words: the
free local converter, the local OCR engine and the optional Datalab cloud
service. For each it tells you what it does, what it is best at, whether it runs
on your computer or in the cloud, what it costs and how it is set up right now.

Two settings are there for unusual setups: the OCR recognition language
(`ocr_language`, English by default) and a path to the engine if QUILL cannot
find it (`tesseract_path`). The cloud service's other options, apart from the
key, are on the Services tab.

## Remote access

QUILL can open files from a server, save to it, and copy to it, much as it works
with files on your own computer. You can use FTP, SFTP, HTTPS, WebDAV, and
Amazon S3 (or any S3-compatible service). Every remote action is something you
choose, QUILL tells you what is happening, and nothing is written to disk before
you confirm. The commands are on **File > Open from Remote**:

- **Open from Remote...** lists every site you have saved, lets you look around
  a folder on the server, and downloads the file you choose. QUILL tells you the
  host and the expected size, saves the download to a temporary file, and opens
  it in a normal tab whose title ends with `(from site:path)`. The document is
  **read-only** until you save it back with **Save Copy to Remote...** or copy
  it to your own computer.
- **Save to Remote** writes the current document to a path you choose on one of
  your saved sites, and keeps a tilde backup next to the original.
- **Save Copy to Remote...** writes a copy to the server and leaves your local
  file as it is.
- **Manage Remote Sites...** adds, edits and deletes saved sites for all five
  kinds of server. Each site's password goes into **Windows Credential Manager**
  when it is available, or otherwise into a file protected by Windows (DPAPI).
  On a Mac, the Keychain is used.

All remote traffic uses a **verified TLS context**, a checked and encrypted
connection. Cloud addresses (S3, HTTPS, and WebDAV over HTTPS) must use HTTPS.
FTP is allowed because you chose it, usually for a computer on your own network
or an older server. Every remote connection is listed in QUILL's record of the
places it connects to, and file listings from S3 and WebDAV servers are read in
a way that a booby-trapped listing cannot take advantage of.

These commands have no keys of their own out of the box. Reach them from the
menu or the Command Palette (`Ctrl+Shift+P`), or give them keys in the Keymap
Editor.

### Editing a file over SSH

If you look after a Linux server, a Raspberry Pi or a web host, you can edit
its files over SSH as though they were on your own computer. The commands are
on **File > Open over SSH**.

1. Choose **File > Open over SSH > Quick Connect...**. The **Connect to SSH
   Server** window opens.
2. Fill in **Host or IP address**, **Port** (22 unless your server says
   otherwise) and **Username**.
3. Choose how you sign in under **Authentication**: **Password**, **Private
   key file** or **SSH agent**. For a password, type it in **Password / key
   passphrase**. For a key, type its path, or press **Browse...** to find it.
   OpenSSH, PEM and PuTTY (`.ppk`) keys all work. If your key has a
   passphrase, type that in the same box.
4. Press **Connect**. QUILL says "Connecting to" and the server's name, and
   then opens the **Open Remote File** window on your home folder.
5. Arrow through the list. Folders say "dir" in front of their names.
   Press Enter on a folder to go into it, or on **.. (parent directory)** to go
   back up. Press Enter on the file you want, or choose **Open**.

The file opens in a normal tab, and the status bar says that saving uploads it
back. Press `Ctrl+S` as usual, and QUILL sends your changes to the server,
keeps a backup copy of the old version next to it with a tilde on the end of
its name, and keeps the line endings the file already had.

If you connect to the same server often, save it once in **File > Open over
SSH > Site Manager...**. The **SSH Site Manager** window lists your **Saved
sites**, with **New**, **Edit** and **Delete** buttons beside the list. Pick a
site and press **Connect**. A saved site never keeps your password: QUILL asks
for it each time you connect.

QUILL is careful about which servers it trusts. It only connects to a server
whose identity your computer already knows, from the same list OpenSSH uses,
or one you have already told QUILL to trust. A server it has never seen is
turned away, so a server pretending to be yours cannot slip in. If you really
do want QUILL to accept a new server the first time it sees it, turn on
**Trust SSH hosts on first connection** on the **Administration** page of
Settings. Leave it off unless you have a reason.

## GitHub remote files

QUILL can browse GitHub repositories, open files from them and save your changes
back, without Git, the GitHub CLI or GitHub Desktop installed.

### Getting started with GitHub

The first time you use a GitHub feature, QUILL asks you to confirm that it may
connect to GitHub. You are asked once, and QUILL remembers your answer.

You do not need a GitHub account to browse public repositories. For private
repositories, and for anything that changes GitHub, you need a Personal Access
Token (PAT).

#### Creating a Personal Access Token

1. Go to github.com and sign in.
2. Open Settings > Developer settings > Personal access tokens > Tokens
   (classic).
3. Choose Generate new token.
4. Give it a name such as "QUILL" and select the `repo` scope (or `public_repo`
   if you only need public repositories).
5. Copy the token. You will only see it once.

QUILL keeps your token safely in **Windows Credential Manager**. It is never
saved in a text file.

#### Managing your GitHub account

Use **File > Open from Remote > Manage GitHub Accounts...** to:

- See which GitHub account you are signed in as.
- Add or replace a token.
- Sign out and clear your stored token.

#### If the GitHub commands are missing

GitHub access is the feature called GitHub Remote Access (`core.github_remote`).
If you can't find it, open **File > Open from Remote** and check whether the
GitHub items are there. If PyGithub is not installed, QUILL shows a message
explaining how to install it: `pip install "quill[github]"`. The GitHub commands
are also unavailable in Safe Mode.

### Opening and saving GitHub files

#### The repository browser

Open **File > Open from Remote > GitHub Repository...**. The browser has these
parts:

- **Account** shows your GitHub username, or "Anonymous" if no token is stored.
- **Repository**: type an owner/repo name such as `microsoft/vscode` and press
  Enter or choose Load.
- **Branch or tag** chooses which version of the repository to browse. It starts
  on the repository's default branch.
- **Current path** shows where you are in the folder tree.
- **File list** lists folders and files, folders first.
- **Status** shows progress messages and item counts.

To move around:

- Press Enter on a folder to open it.
- Press Enter on a file to open it (the same as choosing Open File).
- Press Backspace to go up one level.
- Press `F5` to refresh the current folder.
- Tab through the buttons: **Open File**, **Go Up**, **Refresh**, **Copy URL**,
  **Cancel**.

#### Opening a file from its address

If you have the web address of a file on GitHub, perhaps from a colleague, use
**File > Open from Remote > GitHub File URL...**. Paste an address like
`https://github.com/owner/repo/blob/branch/path/to/file` and press Enter. QUILL
fetches the file directly.

GitHub's file service only handles files up to 1 MB. A larger file has to be
downloaded by hand from github.com.

#### Saving back to GitHub

When you have opened a file from GitHub and made changes, use
**File > Open from Remote > Save to GitHub...**. QUILL asks for a commit
message. Type a short description of your changes and press Enter. QUILL commits
your changes to the same repository, branch and file path.

- You need a token with permission to write (`repo` scope).
- If the file changed on GitHub after you opened it, QUILL tells you to refresh
  and try again.
- Pressing Save never does this for you. You choose Save to GitHub each time.

### The GitHub Items viewer

**File > Open from Remote > GitHub Items...** opens a viewer for a repository's
issues, pull requests, branches, commits, tags, releases, workflows and workflow
runs. It is the same kind of overview the GitHub website gives you, made for the
keyboard and a screen reader. It owes a great deal to
[GHManage](https://github.com/kellylford/GHManage), Kelly Ford's open-source
GitHub browser for screen-reader users, which QUILL has followed from the start.
QUILL adds its own touches: pull request and branch differences are read through
the same engine as Compare Documents instead of as a raw patch, and the Quick
filter stays quiet while you type.

You can browse without signing in. Signing in adds the **Batch...** menu and the
**Actions...** menu, for things like new issues and pull requests, merging,
deleting branches, running workflows and replying to comments. Your pins,
favorites and column choices are saved on your own computer only.

#### Loading a repository

Type a repository as `owner/repo`, paste a `github.com` address, or paste a
`git@github.com:` remote, and press **Load**. QUILL turns any of those into
`owner/repo` for you. If the document you are editing came from GitHub, or lives
in a git folder whose `origin` remote points at GitHub, the repository is
already filled in.

- **Pinned...** opens a menu of your pinned repositories. Choose one to load it
  straight away, or pin or unpin the repository you have loaded. It is your own
  short list for the few repositories you really work in. It is separate from
  anything GitHub keeps and never synced anywhere.
- **Favorites.** Press `Ctrl+D` on any row (an issue, a pull request, a branch,
  a release) to bookmark it. The **Favorites...** button lists every bookmark
  across every repository. Choose one to open it in your browser. Favorites are
  kept between sessions.
- **View Upstream.** When the repository you load is a fork, the
  **View Upstream** button becomes available. Press it to load the repository it
  was forked from, just as if you had typed its name. The button stays
  unavailable for a repository that is not a fork, or, rarely, for a fork whose
  parent GitHub cannot find.

#### Views and the list

Pick a **View**: Issues & PRs (issues and pull requests together), Branches,
Commits, Tags, Releases, Workflows or Workflow Runs. The list shows one row per
item, and the **Details** box below shows the full text of the selected row. In
Issues & PRs you can also filter by **Show** (Both, Issues, PRs) and **State**
(Open, Closed, All), and **Sort** by number, title, last updated or number of
comments.

- **List mode.** There are two ways to read the list. **Quick** shows short
  cells as they appear in the columns. **Full** says each cell as `field: value`
  (for example `number: 208, type: ISSUE, state: OPEN, title: Fix the thing`),
  so your screen reader reads a line that explains itself instead of bare
  values. Switch with the **List mode** choice, or press `M` in the list.
- **Columns...** lists every field for the current view as a checkbox. Uncheck
  the ones you don't need (at least one always stays). Your choice is remembered
  for each view.
- **View More** loads the next page of results.

#### Searching and filtering

- **Search with GitHub's own syntax.** Press `Ctrl+F` (or Tab to the Search
  box), type any GitHub search, such as `label:bug is:open crash`,
  `author:alice is:pr` or `created:>2026-01-01 no:assignee`, and press Enter.
  The results replace the Issues & PRs list, limited to the loaded repository.
  Clear the box and press Enter to get the normal list back. Loading another
  repository also clears the search.
- **Quick filter.** `Ctrl+Shift+F` moves to the **Quick filter** box, next to
  Search. Instead of asking GitHub, it narrows the list you already have, as you
  type. Nothing goes over the network, so it is instant even on a slow
  connection. It never moves your focus while you type, and it doesn't announce
  a count after every letter, which would talk over your screen reader's own
  typing echo. QUILL only says the count when a real fetch finishes. Press
  Escape in the box to clear it. Switching views or loading another repository
  clears it too.

#### Reading issues, pull requests and comments

When you select an issue or pull request, the details show its text and then
load the comments. Press `Alt+N` for the next comment and `Alt+P` for the
previous one. QUILL selects and scrolls to each and says "Comment N of M" (and
"first" or "last" at either end).

**AI thread summaries.** Select an issue or pull request and press
**Summarize**. QUILL's AI boils the whole discussion, text and comments, down to
a short summary in plain prose: what it is about, where it stands, open
questions and the next step. It goes at the top of the details and is read out.
It uses the same AI connection and consent questions as every other AI feature
in QUILL. If AI is not set up, Summarize offers to set it up instead of failing
quietly.

#### Pull request diffs and branch comparisons

- **Pull request diffs.** Select a pull request and press **Diff...**. A list of
  its changed files opens, each row reading `status: filename +added -removed`.
  Select a file to hear its changes through the same engine as
  **Compare Documents**, for example "Difference 2 of 5. Text changed at line
  41", with both sides labeled (`main:` and `this PR:`) and the changed words
  described. A new file reads as its content, a deleted file says so plainly,
  and a binary or very large file falls back to its change counts and GitHub's
  patch text.
- **Compare two branches.** In the **Branches** view, select a branch and press
  **Compare...** or `Ctrl+Shift+B`. QUILL asks for the base branch, then the
  branch to compare with it (the row you selected fills in the second question).
  It tells you how far ahead and behind the two branches are and lists every
  commit between them. The **Changed Files** tab walks each file's differences
  the same way **Diff...** does. Comparing only reads, so it works without
  signing in.

#### Workflows

Switch to the **Workflows** view to see the repository's workflow definitions,
the `.yml` files themselves. The **Workflow Runs** view below them shows run
history. Select a workflow and press Enter, or use
**Actions... > Run "name" on Branch...**, to run it: QUILL asks for a branch,
confirms, and tells you whether GitHub accepted the run. You need to be signed
in. If the workflow does not accept manual runs, QUILL shows GitHub's own
explanation.

#### What failed in a workflow run

When a run fails, the question is nearly always "what broke?", and on GitHub
the answer is spread over collapsed log groups and a side panel of annotations.
Select the run in **Workflow Runs** and press `Ctrl+Shift+W`, or choose
**What Failed...** from the **Actions...** button or the row's context menu
(`Shift+F10`). It is also a button, **What Failed...** (`Alt+F`), in
**Jobs and Logs**.

You get one read-only text you can arrow through and copy. It lists each failed
job, then the steps in it that failed, then GitHub's annotations with the file
and line, then the last 40 lines of each failed step's log. QUILL takes out the
timestamps and colour codes, and drops blank lines and debug chatter, so what
is left is what a person would read. If one job's log or annotations can't be
fetched, the text says so for that job and carries on with the others.
**Copy All** copies the lot, ready to paste into an issue or a message.

#### Workflow run actions

Select one run in **Workflow Runs**. The **Actions...** button and the context
menu offer:

- **Re-run Failed Jobs Only**, which starts again just the jobs that failed,
  not the whole run.
- **Cancel Run...**. GitHub accepts a cancel and finishes it in the background,
  so QUILL says it is stopping the run, not that it has stopped. Refresh to check.
- **Delete Run...**. The question names the run, its branch and its result, and
  says its logs and artifacts go with it. This cannot be undone.
- **Approve Run from a Fork...** for a pull request from someone outside the
  repository, whose run waits for a maintainer. Only approve code you have read:
  it runs with your repository's workflow permissions.
- **Review Pending Deployments...** when a run waits for a reviewer before it
  deploys to a protected environment. The window lists the environments, with
  the ones you may approve already checked. Write a comment (GitHub requires
  one), then press **Approve** or **Reject**. QUILL names the environments
  GitHub confirmed.
- **Combined Check Status** reads the run's commit and says one line, such as
  "3 of 4 checks pass; failing: test."

In **Jobs and Logs**, **Re-request Check** (`Alt+C`) asks GitHub to run the
selected job's check again. Everything that changes something on GitHub asks
first, needs you to be signed in, and reports only what GitHub confirmed. When
GitHub refuses, QUILL says why and what to do, for example that your token
lacks permission or that the run has already finished.

#### Auto-merge and the merge queue

In a pull request's **Review** window, the **Auto-Merge and Queue...** button
(`Alt+A`) and the pull request's context menu in the outline offer:

- **Enable Auto-Merge...**, which asks for the merge method (a merge commit,
  squash or rebase). GitHub then merges the pull request by itself once its
  required reviews and checks pass.
- **Disable Auto-Merge...**.
- **Add to Merge Queue...** and **Remove from Merge Queue...** for a branch that
  uses a merge queue. When it joins, QUILL tells you its place in the queue.
- **Combined Check Status**, which counts only the required checks once you
  have pressed **Check Merge Policy**, for example "3 of 4 required checks pass;
  not reported yet: deploy."

QUILL says the outcome in plain words. When GitHub refuses, for example because
auto-merge is turned off for the repository, QUILL says that and where to turn
it on.

#### Batch operations

The list lets you select several rows: hold Shift or Ctrl to select issues or
pull requests, then press **Batch...** and choose Close, Reopen or Add label.
You must be signed in, because browsing without an account only ever reads. A
confirmation names the exact action and the exact item numbers, and nothing
changes on GitHub until you confirm. If some items fail, QUILL tells you which,
and the rest still go through.

#### Keys in the Items viewer

- Enter on a row opens it in your browser. On a **Branch** row, Enter shows that
  branch's commits. On a **Workflow** row, Enter runs it on a branch you choose.
- Backspace in the Commits view (reached with Enter on a branch) goes back to
  the branch list.
- `Ctrl+R` refreshes the current view. `Ctrl+O` opens the selected item in your
  browser. `Ctrl+G` goes to an issue or pull request by number (in the Issues &
  PRs view).
- `Ctrl+F` moves to the GitHub search box, and `Ctrl+Shift+F` to the Quick
  filter box. `Ctrl+Shift+B` compares two branches (Branches view). `Ctrl+D`
  adds the selected row to your favorites.

The Items viewer follows the same rules as the other GitHub commands: it is off
in Safe Mode, asks for your consent the first time, and works without an account
for public repositories (GitHub allows fewer requests then) or with your stored
token for private ones.

#### Doing more from the Items viewer

When you are signed in, the **Actions...** button opens a menu that changes with
what you are looking at:

- In **Issues & PRs**: **New Issue...** and **New Pull Request...** ask for a
  title (and, for a pull request, the head and base branches) and an optional
  description. If exactly one unmerged pull request is selected,
  **Merge Pull Request #N...** appears too. Merging changes the target branch
  for everyone, so you confirm it by typing the pull request number again, not
  just by pressing Yes.
- With comments loaded: **Reply to Thread...** posts a new comment. (GitHub's
  comments are not threaded, so a reply is simply another comment in the same
  conversation.) Once you have used `Alt+N` or `Alt+P` to land on a comment,
  **Edit This Comment...** and **Delete This Comment...** appear as well. GitHub
  only lets you edit or delete your own comments, so trying it on someone else's
  brings back GitHub's permission error. To delete, you type "delete" to
  confirm.
- In **Branches**: select one branch and **Delete Branch 'name'...** appears.
  Type the branch name again to confirm. It cannot be undone from QUILL.
  **Compare...** is here too, and needs no sign-in.
- In **Workflows**: select one workflow and **Run "name" on Branch...** appears,
  the same as pressing Enter.
- In **Workflow Runs**: select one run and **Re-run Workflow**,
  **View Jobs and Logs...**, **View Artifacts...**, **What Failed...** and the
  run actions described under Workflow run actions appear.

All of these need you to be signed in. Without an account, the viewer only
reads.

#### Downloading workflow run artifacts

Select a workflow run and choose **Actions... > View Artifacts...** to see that
run's build artifacts, each with its size and whether GitHub has already let it
expire (an expired artifact can't be downloaded). From there:

- **Download Selected...** downloads the highlighted artifact, and
  **Download All...** downloads every artifact in the run. Both ask you to
  choose a folder first.
- If a file with that name is already in the folder, QUILL asks before replacing
  it.
- A progress window with a **Cancel** button follows the download. Cancelling
  stops after the artifact that is downloading at the moment.
- **Refresh** fetches the list again, which helps while a run is still producing
  artifacts, and **Open Run in Browser** takes you to the run's page on GitHub.

A note on your token: GitHub hands the actual download to a different,
short-lived address (usually on Azure Blob Storage). QUILL makes that second
request without your token, so your token is only ever sent to github.com.

### Managing repositories

These commands are on **Tools > Git and GitHub > GitHub**. They let you do
things you would otherwise open a browser for. All of them need you to be signed
in. If you are not, QUILL offers to sign you in right there.

#### Repository administration

- **Create Repository...** asks for a name, a description, private or public,
  and an optional organization. Right after creating it, QUILL offers to set up
  a local folder synced to the new repository in one step, using the same folder
  sync as **Sync Folder with GitHub** (QUILL Sync). Starting a new project never
  means leaving QUILL.
- **Fork Repository...** forks into your account or an organization you choose,
  and offers to sync it locally afterwards in the same way.
- **Rename Repository...** renames it. GitHub sends the old address on to the
  new one, but anything elsewhere that has the old name written into it will
  need updating. You confirm by typing the repository's current `owner/repo`
  name again.
- **Change Visibility...** switches a repository between private and
  public. QUILL tells you which it is now before asking. Making a repository
  public adds a warning line, because its whole history becomes visible. You
  confirm by typing the repository name again.
- **Change Default Branch...** loads the branches and lets you pick the new
  default from a simple list.
- **Configure Branch Protection...** is a short wizard. Pick a branch, then set
  the required approving reviews, required status checks, and whether the rules
  apply to administrators too. Or check "Remove all protection from this branch
  instead" to clear the rules.
- **Delete Branch...** lists the branches (never the default branch, so you
  cannot delete the one everything depends on by accident), then asks you to
  type the branch name again to confirm. It can't be undone from inside QUILL.
- **Commit Multiple Files...** lets you pick one or more files on your computer,
  choose the branch and write a commit message. QUILL commits them all to GitHub
  together in one commit. This is different from **Save to GitHub**, which only
  commits the document you have open. Only plain text (UTF-8) files are
  supported.

The four riskiest actions, renaming, changing visibility, deleting a branch and
(in the Items viewer) merging a pull request, all ask you to type the exact name
or number instead of answering Yes or No. A stray press of Enter on one of these
is much harder to put right than most things in QUILL.

All eight are in the Command Palette (`Ctrl+Shift+P`). They have no keys out of
the box. You can give any of them one in the Keymap Editor (**Tools > Customize and Support > Keymap Editor...**).

#### Organizations, releases, notifications and security alerts

Five more commands on **Tools > Git and GitHub > GitHub**:

- **Browse Organization Repositories...** lists the organizations your account
  belongs to, then that organization's repositories. Choose one to open it in
  the GitHub Items viewer. This is for browsing only. QUILL does not manage
  organization teams or their permissions.
- **Create Release...** asks for a tag and an optional title, then either your
  own release notes or GitHub's automatic notes (a summary of pull requests
  merged since the last release), and whether to save it as a draft or publish
  it straight away.
- **Dispatch Workflow...** runs a GitHub Actions workflow on a branch or tag you
  choose, the same as "Run workflow" on github.com. It is useful for workflows
  set up to be started by hand.
- **Notifications...** opens your notifications inbox in Explore GitHub,
  described under GitHub notifications below.
- **Security Alerts...** lists a repository's open Dependabot alerts (severity,
  the package affected and a summary), so you can see what needs attention
  without opening a browser.

#### GitHub notifications

**Tools > Git and GitHub > GitHub > Notifications...**, or the
**GitHub notifications** view in **Explore...** in the GitHub Items viewer,
is your whole GitHub inbox, across every repository. When it loads, QUILL says
the unread count once, such as "12 unread". Each row starts with whether it is
read, then why you got it in words ("review requested", "you were mentioned",
"you are watching the repository"), then the repository and title.

- **Enter** marks the notification read and opens it in QUILL when QUILL has a
  view for it: a pull request opens in **Review**, an issue in the GitHub Items
  viewer at that issue. Anything else opens in your browser.
- **Mark Done** (`Alt+D`, or Delete in the list) takes it off your inbox, as
  the Done button on github.com does. **Unsubscribe** (`Alt+U`) stops that
  thread notifying you until you comment or are mentioned. Either way the row
  leaves the list and you land on the next one, so you keep your place.
- **Mark All Read** (`Alt+A`) asks first, then marks everything read up to the
  moment the list was loaded. Anything that arrived since stays unread.
- **Include read notifications** (`Alt+I`) adds the ones you have already read.

GitHub asks apps not to check notifications more often than it says, usually
once a minute. If you refresh sooner, QUILL keeps the list it has and tells you
how many seconds to wait.

#### Codespaces

Two more commands on **Tools > Git and GitHub > GitHub** use the `gh`
command-line tool installed on your own computer, instead of QUILL's usual
GitHub connection. If you don't have `gh` yet, see Downloading git and the
GitHub CLI elsewhere in this guide.

- **Codespaces...** lists your active Codespaces (name, repository and state).
  Select one for a menu to **Stop** or **Delete** it.
- **Create Codespace...** asks for a repository and an optional branch, then
  creates a Codespace.
  **Codespaces use GitHub compute and storage minutes and may cost money.** This
  is the one GitHub command in QUILL that says so, and it asks you to confirm,
  naming the cost, before it does anything.

These two are new. They have been tested with a stand-in for `gh`, but not yet
with a real Codespaces repository. If something looks
wrong, please tell us through **Help > Get Help from Support**.

## Command-line launching

You can start QUILL from a command line, a script or a shortcut, and tell it
which file to open and where to put the cursor. Most people never need this. It
is handy when another tool, such as a search or a list of errors, hands you a
file name and line number.

The command is `quill.exe`, the launcher that comes with both the installed and
the portable copy. During setup, the installer offers an "Add Quill to PATH"
option. Turn it on and `quill` works from any Command Prompt or PowerShell
window without the full path. If you skipped that option, use the full path
instead (usually `"%LOCALAPPDATA%\Programs\Quill for All\quill.exe"` for an
install just for you). From a source checkout, the command is `python -m quill`.

These are the options:

- `--help`: show the command help and exit.
- `--version`: print QUILL's version and exit without opening the window.
- `--safe-mode`: start with optional features switched off.
- `--reset-profile`: reset the feature profile store before starting.
- `--diagnostics`: start with diagnostics tracing on.
- `--dump-stacks`: write a thread-stack dump and exit.
- `--line N`: the line (counting from 1) for the first file you open.
- `--column M`: the column (counting from 1) for the first file you open.
- `--goto FILE[:LINE[:COL]]`: open a file at a line and column in one argument
  (both optional, counting from 1). It is the short form of `--line` and
  `--column`, handy when a linter, a search result or a build error gives you a
  `file:line:column` string. Example: `--goto main.kt:27:5`.
- `--diff LEFT RIGHT`: open two files straight into compare mode, on the first
  difference, without opening each one by hand.
- `--new-window`: start a new copy of QUILL instead of handing the file to the
  one already running.
- `--wait`: when handing the file to a QUILL that is already running, wait until
  that QUILL closes.

Some examples:

- `quill --version`
- `quill notes.md --line 40 --column 5`
- `quill --goto main.kt:27:5`
- `quill --diff old-draft.md new-draft.md`
- `quill --new-window notes.md`

## What you learned, and where to go next

You can now open files, including ones that have moved, and save them in the
format you need. You know what each kind of document gets in QUILL, what carries
over when you convert, and how to convert one file or a whole folder. You can
rescue a scanned PDF, work with files on a server or on GitHub, and start QUILL
from a command line.

To practise with QUILL open, choose **Help > Tutorials...** (`Ctrl+Alt+F1`) and
try "Write and save your first document" and "Open anything, save as anything".
On the website, [Rescue a scanned
PDF](https://www.quillforall.org/tutorials/03-rescue-a-scanned-pdf.html), [From
document to published
audiobook](https://www.quillforall.org/tutorials/04-document-to-audiobook.html)
and [GitHub inside
QUILL](https://www.quillforall.org/tutorials/08-github-inside-quill.html) walk
through the longer jobs.

Next, Chapter 4, Writing and editing, is where you start shaping the words
themselves.

---

- Previous: [Chapter 2: Finding your way around](quill-guide-02-finding-your-way-around.html)
- Next: [Chapter 4: Writing and editing](quill-guide-04-writing-and-editing.html)
- [Contents](../userguide.html)
