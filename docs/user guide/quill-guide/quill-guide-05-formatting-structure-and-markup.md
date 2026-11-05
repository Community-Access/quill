# Chapter 5: Formatting, structure and markup

This chapter is about the shape of your writing: headings, lists, bold and
italic, fonts and colours, tables, equations and citations. QUILL keeps your
text plain and easy to read while you work, and still gives you a properly
formatted document when you save it as Word, RTF or HTML. If you write in
Markdown or HTML, or you want a document that other people can navigate by
heading, this is the chapter for you. Near the end you will also find the
tools for tidying pasted text and fixing character encoding problems, and how
QUILL tells you what it has done.

## Format menu

The **Format** menu is where you change how existing text looks and how it is
laid out. Most of it works on the selection, or on the current line when
nothing is selected.

### Case, comments and indentation

The **Change Case** submenu has five commands:

- Upper Case
- Lower Case
- Title Case
- Sentence Case
- Toggle Case (`Ctrl+Alt+Shift+N`)

For code and structured text there are comment and indentation tools:

- Toggle Line Comment (`Ctrl+/`)
- Toggle Block Comment (`Ctrl+Shift+/`)
- Indent (`Ctrl+]`)
- Outdent (`Ctrl+[`)
- **Tab Key Inserts Tab Character** (`Ctrl+Alt+Shift+I`), which Chapter 2
  explains under the Tab key.
- **Describe Indent Depth** (`Ctrl+Alt+Shift+V`), which tells you how deeply
  the line you are on is indented, such as "4 spaces" or "1 tab", without
  moving anything.

### Working with whole lines

These commands are on **Format > Line**, and act on the line your cursor is
on:

- Move Line Up (`Ctrl+Shift+Up`)
- Move Line Down (`Ctrl+Shift+Down`)
- Duplicate Line (`Ctrl+D`)
- Delete Line (`Ctrl+Shift+Delete`)
- Join Lines (`Ctrl+Alt+Shift+J`)
- **Delete to Line Start** (`Ctrl+Shift+Backspace`) and **Delete to Line
  End** (`Ctrl+Alt+Shift+Delete`)
- **Delete to Document Start** and **Delete to Document End**, which remove
  everything from the cursor to the top or the bottom of the document. They
  have no keys at first, because they remove a lot at once. Ctrl+Z puts it
  back, and so does **Edit > Restore Deleted Text...**.
- **Delete Paragraph** (`Ctrl+Alt+Shift+Backspace`)
- **Quote Lines** (`Ctrl+Shift+Q`) and **Unquote Lines** (`Alt+Shift+.`),
  which add or take away the `>` that marks a quoted line in an email or in
  Markdown.

Five line tools have their own keys, so you do not have to walk the menu
each time:

- **Hard-Wrap Lines** (`Alt+Shift+W`)
- **Delete Lines Containing** (`Alt+Shift+X`)
- **Convert Indentation to Spaces** (`Alt+F11`)
- **Convert Indentation to Tabs** (`Alt+F12`)
- **Line Statistics** (`Ctrl+Alt+W`)

The first four use the same keys as QUILL Lite, so your hands work the same
way in both. Line Statistics is on **Tools > Advanced**, and Document
Statistics is on `Ctrl+Shift+G`.

### Sort and Filter, Whitespace, and numbering lines

Three more submenus of the Format menu work on many lines at once. Each one
works on the selected lines, or on the whole document when nothing is
selected.

**Format > Sort and Filter** puts lines in order and weeds them out:

- **Sort Lines A to Z** (`Ctrl+Alt+S`) and **Sort Lines Z to A**
  (`Ctrl+Alt+Shift+S`)
- **Shuffle Lines**, which puts them in a random order, handy for a quiz or a
  draw
- **Sort Lines Numerically**, **Sort Lines by Date** and **Sort Lines by
  Length**, described below
- **Delete Lines Containing...** (`Alt+Shift+X`) and **Delete Lines Not
  Containing...**. Type a word or phrase, and every line with it (or every
  line without it) goes.
- **Reverse Lines** (`Alt+Shift+Z`)
- **Remove Duplicate Lines** (`Ctrl+Alt+D`)

**Format > Whitespace** tidies spaces and blank lines:

- **Trim Trailing Whitespace** (`Ctrl+Alt+R`)
- **Trim Blank Lines at the Ends** (`Ctrl+Shift+Enter`) and **Remove Every
  Blank Line** (`Ctrl+Alt+K`), described next
- **Normalize Whitespace** (`Ctrl+Alt+Shift+T`)
- **Convert Indentation to Spaces** (`Alt+F11`) and **Convert Indentation to
  Tabs** (`Alt+F12`)

**Format > Line** has the numbering tools, **Number Lines...**
(`Alt+Shift+N`) and **Number Lines (Advanced)...**, along with **Hard-Wrap
Lines...** (`Alt+Shift+W`). **Number Lines (Advanced)...** is for the times
the simple version is not enough. You can set a starting number, an
increment, digits or Roman numerals, a zero-padding width, a custom suffix,
and left or right alignment.

### Two ways to remove blank lines

The Format menu has two blank-line commands, and their names tell you which is
which.

- **Trim Blank Lines at the Ends** removes only the blank lines before the
  first line of text and after the last one. Use it before you paste a
  fragment into something else.
- **Remove Every Blank Line** removes all of them, including the ones between
  your paragraphs. Use it on text copied from a web page that arrived
  double-spaced.

A line with nothing but spaces on it counts as blank to both commands. They
used to be called Trim Blank Lines and Remove Blank Lines.

### Sorting lines by number, length or date

Besides the plain A to Z sorts, **Format > Sort and Filter** has three more
for structured lists. Each works on the selected lines, or the whole document
if nothing is selected.

- **Sort Lines Numerically** sorts by the first number on each line.
- **Sort Lines by Length** puts the shortest lines first.
- **Sort Lines by Date** sorts by the date on each line.

Sort Lines by Date understands the common ways of writing a date:

- ISO dates, such as `2020-03-05`.
- Slash and dot forms, such as `03/04/2020` and `5.1.2020`.
- English month names, such as `Jan 5, 2020`, `5 January 2020` and
  `March 3rd, 1999`.

When a numeric date could be read two ways, QUILL follows your region. In US
English it reads the month first, so `03/04` is March 4th. Everywhere else it
reads the day first, so `03/04` is 4 March. A date that can only mean one
thing, like `25/12`, is always read correctly. Lines with no date it
recognizes stay together at the bottom, in their original order, so nothing
is lost.

All three sorts have no key by default. You can give them one in the Keymap
Editor.

### Bold, italic and rich formatting

**Bold** and **Italic** are on the Format menu, as you would expect. Beyond
those two, the menu applies real document formatting:

- **Underline**, **Strikethrough**, **Superscript** and **Subscript**
- **Font** (the font family) and **Size** (the point size)
- **Text Colour** and **Highlight**
- paragraph **Alignment** (Left / Centre / Right / Justify)
- line spacing, indent and named styles

QUILL uses what it calls hidden codes for this. The formatting is stored out
of sight, so what you read and edit stays clean plain text with no clutter in
it. When you save or export, the hidden codes become real formatting, and the
document comes out as a properly formatted Word, RTF or HTML file.

Everything else in QUILL works on that same clean text: undo, search, the
outline, word counts, read-aloud and the AI tools all see your prose, not the
markup.

#### Applying formatting

Use the Font, Size, Align, Colour and Highlight items on the Format menu. If
text is selected, the formatting applies to the selection. If nothing is
selected, it applies to what you type next.

Here is what each one offers:

- **Format > Font** has six everyday typefaces: Arial, Calibri, Times New
  Roman, Courier New, Verdana and Georgia.
- **Format > Font Size** has **Grow Font** (`Ctrl+Shift+.`) and **Shrink
  Font** (`Ctrl+Shift+,`), which step the size up or down, and a list of
  sizes from 8 to 72 point.
- **Format > Align** has **Left** (`Ctrl+L`), **Center** (`Ctrl+E`),
  **Right** (`Ctrl+R`) and **Justify** (`Ctrl+J`), the same keys as Word.
- **Format > Text Color** has Black, Red, Green, Blue, Orange and Purple.
- **Format > Highlight** has Yellow, Green, Turquoise, Pink and Gray.
- **Format > Line Spacing** has **Single** (`Ctrl+1`), **One and a Half**
  (`Ctrl+5`) and **Double** (`Ctrl+2`), Word's keys again.
- **Format > Paragraph Spacing** adds 6 or 12 points of space before or after
  the paragraph.
- **Format > Paragraph Indent** indents the paragraph's left edge by 18, 36
  or 54 points, or indents just its first line by 18 or 36 points.
- **Format > Paragraph Style** makes the paragraph a **Quote**, a **Title**, a
  **Subtitle** or a **Caption**.
- **Format > Insert Page Break** (`Ctrl+Enter`, Word's key) starts a new page
  at the cursor. In a Word or Rich Text document it is a real page break,
  the same one Word makes, and it is still there when you save and open the
  file again. In a Markdown document it goes on its own line and takes effect
  when you save or export to a format that has pages, such as Word or PDF. In
  a braille file it is a braille page break. With the cursor on a link,
  `Ctrl+Enter` follows the link instead, which is what it did before; in a
  plain text document QUILL tells you a page break needs another kind of
  document.
- **Format > Clear Formatting** (`Ctrl+Shift+N`) is Word's "back to normal
  text". In a rich text document it turns bold, italic, underline and
  strikethrough off, puts the size, colour, highlight, alignment and spacing
  back to normal, and takes the text out of any list, all as one step you can
  undo. In a Markdown document it takes the emphasis codes off the selected
  text, or off the paragraph when nothing is selected. When you are not sure
  what is still applied to some text, this is the way to be certain.

The **Markdown Format Codes...** dialog gathers font family, point size,
colour and highlight in one place. It writes hidden Markdown codes, so it
works only in a Markdown document. It used to be called "More Font
Options...".

The two items above it are the ones most people mean by "font":

- **Font...** changes the editor's own typeface and size.
- **Font for Selection...** changes the font of text in a rich text document.

#### Hearing what is there

Because the codes are hidden, you cannot read them in the text. **Describe
Formatting at Cursor** speaks exactly what is in effect at the cursor, for
example "Arial, 14 point, centred, bold". Its key is `Ctrl+Shift+D`. To hear
formatting changes as you arrow through a document, check **Format > Announce
Formatting on Cursor Move**. It stays on until you uncheck it, even after a
restart.

#### Saving with your formatting

When you use **Save As** (or Export) to **Word (.docx)**, **Rich Text (.rtf)**
or **HTML**, the hidden codes become real formatting: font, size, colour,
highlight, alignment and the rest. Word export uses a built-in writer when the
optional `python-docx` component is installed, and Pandoc otherwise.

If the format you are saving to cannot carry something, QUILL tells you before
you commit, instead of quietly dropping it. Saving to plain text drops the
formatting, and you get the same warning.

## Markdown and HTML awareness

Plenty of people write in plain text and still care a great deal about the
structure of what they export. QUILL helps with that by noticing whether the
document in front of you looks like Markdown, HTML or plain text. It uses that
to guide the insertion helpers and to switch on the commands that make sense
for that kind of document. The heading and list keys below, for example, work
in Markdown and HTML documents. In a plain-text document QUILL says the
command is unavailable and leaves your text alone.

## Headings

Headings are what let you, and anyone you share a document with, jump through
it by section. QUILL's heading tools help you keep that structure tidy, not
just add decoration.

### Setting a heading level (Ctrl+Alt+1 to 6)

Put your cursor on a line and press `Ctrl+Alt+1` through `Ctrl+Alt+6` to make
it a heading of that level. Press the same key again on a heading that is
already that level to turn it back into an ordinary line. This works in
Markdown and HTML documents.

`Alt+Shift+Left` and `Alt+Shift+Right` raise and lower the level of the
heading you are on.

If you use NVDA: these keys take the place of NVDA's own keys for switching
to synthesizer 1 through 6. If you rely on those, rebind QUILL's heading keys
in the Keymap Editor.

### Moving a section

In Markdown and HTML, a section is a heading and everything under it. You can
move whole sections without cutting and pasting.

- `Alt+Shift+Up` and `Alt+Shift+Down` move the section you are in one step,
  swapping it with the section before or after it. This is right for tidying
  two neighbouring sections.
- `Alt+Shift+F5` is **Select Section**. It selects the section and everything
  under it, so ordinary `Ctrl+X` and `Ctrl+V` can put it anywhere: elsewhere
  in this document, in another document, or in another program. QUILL tells
  you how much it selected, for example "Selected Bread and 1 section under
  it, 7 lines", because your screen reader only says the selection changed.
- `Ctrl+Alt+Shift+F5` is **Move Section To...**, which moves a section to a
  place you choose instead of one step at a time. It is described just below.

Your cursor must be on the heading for `Alt+Shift+Up` and `Alt+Shift+Down`.
In a plain-text document QUILL says the key is unavailable and nothing moves.
A line such as `# fake` inside a ``` code fence is never mistaken for a
heading.

When there is no section of the same level in the direction you are moving,
the section trades places with whatever is next to it, the way Word's outline
Move Up and Move Down work on the same keys. A first child section rises above
its parent's heading. A section that runs to the end of the file cannot move
down, and QUILL tells you so and names the key that would promote it to make
it a sibling.

The moved section keeps its level. Moving never renumbers your headings. To
change a level, use `Alt+Shift+Left` and `Alt+Shift+Right`; you can combine
the two.

`Alt+Shift+Up` and `Alt+Shift+Down` used to expand and shrink the selection.
Those commands are now on `Ctrl+Shift+X` and `Ctrl+Alt+Shift+X`, and keymaps
you saved in older versions are moved over automatically.

### Move Section To (Ctrl+Alt+Shift+F5)

Moving a section forty places with `Alt+Shift+Up` means forty announcements
to count. **Move Section To...** asks where you want it to go instead.

1. Put your cursor in the section you want to move and press
   `Ctrl+Alt+Shift+F5`.
2. Choose the heading to move it next to. The list holds every heading in the
   document, and each row reads like "3 of 7, level 2 - Bread", so two
   sections with the same name are still two different rows.
3. Choose **Before**, **After** or **Inside** that heading.

The whole move is a single edit, so one `Ctrl+Z` undoes it.

Only **Inside** changes a level. It makes your section the last one under the
heading you chose, moves everything in it one level deeper, and tells you the
new level.

A few things make the two lists easy to use by ear:

- Focus starts in the search box. Pressing Enter there takes you into the
  results; it does not accept whatever happens to be highlighted.
- The list never reorders itself as you type. It is your outline in document
  order, so you can find things by position.
- A heading inside the section you are moving is still listed, and marked as
  such. If you choose it, QUILL explains, for example: "Sourdough is inside
  Bread, so Bread cannot move into it. Promote Sourdough first if you want
  them side by side."

QUILL also refuses to push a heading past level 6, and tells you why.

Press Escape at either question to cancel. Nothing changes and nothing is
announced.

### Style Headings and the Heading Organizer

To change how headings look, open **Insert > Heading > Style Headings...**.
You can style all heading levels or just the level you are on, and set the
font family, point size and alignment. In a Markdown document, styled
headings are written as HTML heading tags so the formatting is kept.

For bigger reorganising, open **Navigate > Heading Organizer...**
(`Alt+Shift+O`). It lists each heading as its level and title. In it you can:

- promote and demote headings with `Tab` and `Shift+Tab`
- move sections up and down
- rename headings
- check the heading order before you apply your changes. It catches a wrong
  starting level, skipped levels and empty headings.

> **QUILLBee's tip:** Lost track of where you are in a long document? Press
> `Alt+Shift+O` to open the Heading Organizer and hear every heading as a list.

### The Section cell on the status bar

The status bar can show a **Section** cell, which reads
`Section: Heading N (ordinal of total)` whenever your cursor is on a heading
in a Markdown or HTML document. It is hidden by default; turn it on in
**Tools > Customize and Support > Status Bar Layout...**. In a plain-text document, or on a line that is
not a heading, it stays empty.

## Lists

### Bullet and numbered lists (Ctrl+Shift+L)

Press `Ctrl+Shift+L` to start a bullet list, or `Ctrl+Shift+Grave, Shift+L`
for a numbered list. QUILL looks at the line you are on:

- If it is not in a list, a new list starts at the cursor.
- If it is already in a list, the same key turns that list off. Only the list
  you are in changes; every other list in the document is left alone.

When it turns a list off, QUILL tells you how many items it changed, for
example "Bullet list removed, 4 items", since that is the part you cannot
see. `Ctrl+Z` puts the markers back.

Numbered lists follow the `list_auto_fill_numbers` setting, **Settings >
Editing > Auto-fill numbered list markers**. When it is on, every item gets its number,
`1. `, `2. `, `3. ` and so on. When it is off, only the first item does.

These keys always work in Markdown and HTML documents. In a plain-text
document QUILL says the command is unavailable.

### Typing in a list

Markdown lists behave the way they do in other editors, and QUILL tells you
what `Enter` did, because your screen reader only hears a new line:

- `Enter` at the end of an item starts the next one with the next marker: a
  hyphen after a hyphen, `3. ` after `2. `, `3) ` after `2) `, and an unchecked
  `- [ ] ` after any task item. The item's indentation is kept, so a nested
  item continues at its own depth. QUILL says "Continued list item".
- `Enter` in the middle of an item splits it there. In `1. bread milk`, with
  the cursor before `milk`, `Enter` gives `1. bread` and `2. milk`.
- A new numbered item renumbers the items below it while they still count on
  from it, so adding an item after the first of `1. 2. 3.` gives `1. 2. 3. 4.`
  and QUILL says "Continued list item, renumbered 2 items below". A list that
  jumps (from `2.` to `7.`, say) keeps your numbering from the jump on.
- `Enter` on an empty list marker ends the list: the marker goes, the empty
  line stays, and QUILL says "Exited list".
- `Ctrl+Z` straight afterwards takes back the new line, its marker and any
  renumbering in one step.
- On a list item, `Tab` nests it one level deeper and `Shift+Tab` brings it
  back out.

**Plain text** does this only if you ask: turn on **Settings > Editing >
Continue lists in plain text**. It is off to begin with because, in a `.txt`
file or a new untitled note, a line that happens to start with `1.` is as often
a date, a version number or a paragraph you are numbering by hand. Even with
the setting on, QUILL never continues a list in a code or settings file. In a
rich text document (`.rtf`, `.docx`) lists are formatting rather than
characters, and `Ctrl+Shift+L` makes them; `Enter` there is the word
processor's own.

For bigger changes, open **Insert > List > List Manager...**
(`Ctrl+Shift+Grave, L`). It shows your list as a tree, where you can move,
promote, demote, add, edit and delete items.

### Structured List Studio (Ctrl+Alt+Shift+L)

The **Structured List Studio** lets you build a list by its parts (each item's
text, a checked box, a term and its definition) and writes the correct
Markdown or HTML for you. You never have to type `-`, `1.`, `[ ]`, `<ul>` or
`<dl>` yourself.

Press `Ctrl+Alt+Shift+L`, or choose **Insert > List > Structured List
Studio...**.

- With text selected, the studio turns your selection into a list. It makes
  one item per line, or one per paragraph when blank lines separate them, and
  removes any bullets, numbers or task markers already there. With nothing
  selected, it starts a new list.
- Choose the type: **Bulleted**, **Numbered**, **Checklist**, or **Definition
  (or description) list**. Then choose the output format, **Markdown** or
  **HTML**.
- As you work, a read-only **Generated source** field shows exactly what will
  be inserted. The items outline tells you each item's text, its number or
  checked state, and its position.
- Inserting the finished list is a single edit, so one `Ctrl+Z` undoes it.

#### Definition lists

For a definition list, fill in the **Term** and **Definition** fields. For
HTML, QUILL writes valid `<dl>`/`<dt>`/`<dd>` markup. For Markdown, it uses a
Pandoc-compatible syntax. A term can have several synonyms (one per line,
each becoming its own `<dt>`), and a definition can have several paragraphs
(separated by a blank line, each becoming its own `<dd>`).

If you make a Markdown definition list and the document has no profile set,
QUILL asks how you want it written instead of guessing:

- **embedded HTML**, the recommended choice because it works almost
  everywhere
- a specific **Markdown profile**: Pandoc, Markdown Extra or MultiMarkdown
- a plain **"Term: Definition"** list

#### Nesting, reordering and editing a list later

- **Indent**, **Outdent** and **Add child** build nested lists.
- **Move up** and **Move down** carry an item together with all its children.
- To edit a list you already have, put your cursor inside it with nothing
  selected and open the studio. It loads that list, and when you are done it
  rewrites just that block.

#### Converting and importing

- Switching a list to another type carries the content across, and warns you
  before any structure would be lost.
- **Import from clipboard** and **Import from file...** bring text in, with
  the live preview showing how QUILL understood it.
- When you choose OK, the studio checks the generated source. If something is
  wrong, your document is left unchanged and you are told what the problem
  was.

#### List Studio Settings

Open **Insert > List > List Studio Settings...** to set your defaults. You can
pick a ready-made preset, adjust the main options (verbosity, markers,
definition profile and loose lists), and export or import your settings as a
JSON file. Save them **for all documents**, which is what the studio starts
from next time, or **for this document only**, which overrides just the
options you changed. The document's format still chooses the Markdown syntax
for definition lists automatically.

The studio used to open with `F2`, and Insert Special Character used to be on
`Shift+F2`. Today `F2` and `Shift+F2` move between bookmarks, and Insert
Special Character is on `Ctrl+Shift+F2`. You can change any of these keys in
the Keymap Editor.

### Checking off tasks

A task list is a list whose items start with a box: `- [ ]` for something
still to do and `- [x]` for something done. **Insert > List > Task** makes
one, and plans written by AI assistants are usually full of them.

To check a task, put the cursor on its line and press `Ctrl+Alt+Enter` (**Insert
> List > Toggle Task Done**). Press it again to uncheck it. QUILL tells you what
changed and how many tasks in that list are done, for example "Checked: Write
the tests. 3 of 7 tasks complete." Select several lines first to check them all
at once. `Ctrl+Z` takes it back like any other edit. On a line that is not a
task, QUILL says so and changes nothing.

In the preview and in **File > Export > HTML**, a task shows as a real check
box, checked or not, with the task's text as its label.

## Markdown profiles and table of contents

Markdown means different things to different writers. A poet wants every line
break kept, a documentation author wants a table of contents, and someone
contributing on GitHub wants task lists and strikethrough. **Format >
Markdown** lets you say which kind of writing you are doing without learning
the names of Markdown extensions.

- **Insert > Table of Contents** builds a table of contents from your
  document's headings. It uses no AI and makes no network call, and the links
  always match your headings exactly, because they are built from the
  headings themselves. If your document has a `[TOC]` marker on a line of its
  own, the table of contents goes there. Otherwise it goes right after your
  first heading.
- **Select Markdown Profile...** lets you pick a named profile: Standard
  Markdown, GitHub-Style Markdown, Documentation, Poetry and Lyrics,
  Accessible Publishing, Technical Writing, PRD and Release Notes, or Custom.
  QUILL tells you in plain words what the profile turns on, for example
  "Markdown profile: Documentation. 5 extensions enabled."
- **Preserve Single Line Breaks** keeps every line break as a line break,
  instead of letting Markdown join the lines into one paragraph. Turn it on
  for poetry, lyrics, speeches and scripts, where the line is part of the
  meaning.
- **Read Markdown Processing Status** tells you your current profile and what
  it turns on, without opening a dialog.
- **Select Citation Style...** chooses how the Author or Student profile
  writes citations: as Markdown footnotes (light, nothing extra to install),
  or as full Academic bibliography entries through the MLA, Chicago and APA
  form that **Insert > Insert Citation...** opens.

If you would like an outline written in the AI's own words instead, use
**AI > Transform Selection > Generate Table of Contents**. The two commands are
separate, and the AI one appears only when **AI > Use Artificial
Intelligence** is on and **AI > Show advanced AI features** is checked.

## Equations and mathematics

Most editors make maths hard for a screen-reader user. The notation is visual,
and the usual tools give you a mouse and a palette of symbols. QUILL lets you
type an equation as text instead. That works from the keyboard, you can
review it character by character, and screen readers that speak maths
already understand it.

The bundled **Math Equations** Quillin adds a formula gallery, symbol
abbreviations, a way to step through a formula, and export to Word. All of it
is covered below, and also taught from start to finish in
[Tutorial 7: Write math without learning a new language](../../tutorials/07-type-math-like-a-pro.md).

### Insert Equation (Ctrl+Alt+=)

Choose **Insert > Insert Equation...** or press `Ctrl+Alt+=`. (Older versions
of this guide gave `Ctrl+Shift+E`, which now selects the current line.) The
dialog has two fields:

- **Equation**: type **LaTeX**, such as `E = mc^2` or
  `\frac{-b \pm \sqrt{b^2-4ac}}{2a}`, or paste **MathML** (`<math>...</math>`).
- **Display mode**: **Inline** puts the equation inside your sentence.
  **Block** puts it on its own line.

QUILL adds the delimiters for you: `\(...\)` for inline, or `$$...$$` on a
line of its own for a block equation. Those are the marks Browser Preview
and Word export both understand, so the equation shows as maths in the
preview and becomes a real Word equation when you save as `.docx`. MathML
goes in exactly as you typed it, because it already carries its own markup.

To change an equation you already wrote, select it, including its
delimiters, and open Insert Equation again. An equation from an older
version of QUILL, written with single `$` signs, opens the same way, and
inserting it again gives it the new delimiters. The field holds just the maths, with the
delimiters taken off, and the display mode you used is already chosen. Change
it, choose Insert, and the old equation is replaced.

An equation is ordinary text in your file, so nothing in your document
becomes hidden or unreadable. You can always arrow through the raw LaTeX to
check it.

*Insert Equation was contributed by @salorajan.*

#### The Math Equations Quillin's own prompt

The Math Equations Quillin has its own **Insert Equation...** command, a short
prompt instead of a form. It writes exactly the same delimiters as QUILL's own
command, so it does not matter which one you use.

- **LaTeX** is the most common format for typeset maths. Type the formula in
  standard LaTeX and choose a display mode.
  - **Inline** (`\(...\)`) keeps the equation within the surrounding text.
    `E=mc^2` becomes `\(E=mc^2\)`.
  - **Block** (`$$...$$`) gives the equation its own line, with a blank line
    above and below. `\frac{-b \pm \sqrt{b^2 - 4ac}}{2a}` becomes
    `$$\frac{-b \pm \sqrt{b^2 - 4ac}}{2a}$$` on a single line.

  Both are delimiters MathJax recognizes without any setup, and `\(...\)`
  cannot be confused with a dollar amount in your prose the way a bare
  `$...$` could.
- **MathML** is an XML format used in web publishing and accessible
  documents. If what you type starts with `<math`, QUILL inserts it as it is
  and skips the display mode question. Screen readers can read MathML
  directly.
- If you select a LaTeX equation before you run it, QUILL removes the
  delimiters, fills in the bare formula, and puts the display mode it
  detected first in the list, so one keypress confirms it.

#### Seeing equations rendered

Browser Preview (`Ctrl+Shift+Grave, V`) and HTML export add MathJax 3, so
equations appear typeset in any browser. QUILL adds it only for documents
that contain maths. The document itself always keeps the raw LaTeX or MathML,
which is what your screen reader reads.

MathJax is loaded from a public CDN by your browser, so the visual rendering
needs an internet connection. The LaTeX or MathML, and everything your screen
reader says, is always there offline. If you are offline, equations show as
their source instead of typeset maths. Nothing is lost.

### Common Formulas gallery

You do not have to type a common formula at all. **Insert > Snippet
Gallery...** lists ten ready-made formulas from the Math Equations Quillin:

- the Quadratic Formula
- the Pythagorean Theorem
- Slope-Intercept Form
- Point-Slope Form
- the Slope Formula
- the Distance Formula
- the Midpoint Formula
- Difference of Squares
- the Area and Circumference of a Circle

Choose one and it goes in as a correctly formatted `$$...$$` block. To change
it afterwards, select it and open Insert Equation, as with any other
equation.

### Maths symbol abbreviations

Like Word's Math AutoCorrect, you can type a backslash code followed by a
space or punctuation, and QUILL turns it into the symbol. This works anywhere
in ordinary text, but not inside the equation prompt.

- `\alpha ` becomes α
- `\sqrt ` becomes √
- `\ne ` becomes ≠

Case matters where it matters in maths: `\delta ` gives lowercase δ and
`\Delta ` gives uppercase Δ.

There are 88 codes, covering operators, relations, set and logic notation,
number sets, Greek letters, calculus and geometry. They come from the Word
Math AutoCorrect list published by DAISY (daisy.org/MSMathCodes). You will
find them under **Preferences > Editing > Insert Automation**, where you can
turn off any one of them, or the whole set, like any other abbreviation.

### Explore Equation Structure

Hearing a long formula in one breath is hard to follow. **Explore Equation
Structure...** lets you step through it one piece at a time.

1. Select an equation, or select nothing if you want to type a new one.
2. Choose **Insert > Explore Equation Structure...**, or press
   `Ctrl+Shift+Grave, Z`. The menu item comes from the Math Equations
   Quillin that ships with QUILL, so it is missing if you have turned that
   Quillin off or started in Safe Mode.
3. If nothing was selected, a text prompt asks for the LaTeX or MathML.
   Enter accepts it; Escape cancels.
4. QUILL says where you are ("Whole equation" at the top, or the piece's
   name, such as "Fraction", once you have gone deeper) and opens a list.

The list holds the parts of the current piece, such as a fraction's
**Numerator** and **Denominator** or a power's **Base** and **Exponent**,
followed by **Read this part aloud**, **Back up one level** (once you are
below the top) and **Done exploring**.

Use the Up and Down arrows to move, or type a letter to jump to the next item
starting with it. Press Enter, or choose **OK**, to act on the highlighted
item:

- A part takes you into it and lists its own parts.
- **Read this part aloud** reads just the current piece, then reopens the
  same list at the same place so you can carry on.
- **Back up one level** goes to the piece that contains this one.
- **Done exploring** ends and puts you back in the editor.

Escape, or **Cancel**, ends the whole session at once, from any list at any
depth, just like Done exploring. It does not go back one level; **Back up one
level** is the choice for that.

#### Richer maths speech with MathCAT

Stepping through the parts needs nothing extra. It works the moment QUILL is
installed, with no download. **Read this part aloud** can get better: install
the free **MathCAT math speech engine** from **Help > Download Optional
Components... > MathCAT math speech engine** (about 3 MB, MIT-licensed, from
the `daisy/MathCATForC` project). That command then uses the same
natural-language maths speech that NVDA ships, instead of QUILL's simpler
built-in reading. If you skip the download, or MathCAT cannot handle a
particular formula, the command still works with the built-in reading.

Nemeth and UEB maths braille are not available yet. If you use JAWS, its Math
Viewer works once an equation is a native Word equation (see the next
section), and it remains the fuller option, with braille support.

### Word export and round trip

**File > Export > Word Document...** turns every `\(...\)` and `$$...$$`
equation in your document into a genuine Word equation, the same kind Word's
own equation editor makes. It does this through Pandoc, one equation at a
time. In Word, the equation tools work on it, and JAWS reads it as maths, not
as a picture or as literal text. If Pandoc is not available, the equation is
kept as its delimited text, never dropped.

Open that Word file again later with **File > Open...** and the equation comes
back as the same plain, editable `\(...\)` or `$$...$$` text. This works
whichever reader you have chosen in **Settings > Editing > Word document
reading engine**.

### Ask about an equation

The AI Hub's **Math Tutor** agent explains a selected equation in plain
language: what it means, what each symbol is, and its common name if it is a
well-known formula. It does not solve anything or change your document.

Ten worked examples, including the quadratic formula, the binomial theorem,
integration by parts and Euler's identity, are in `docs/math/latex_testing.md`.

## Citations and bibliographies

For research writing, **Insert > Insert Citation...** builds a correctly
formatted citation from the details you type, so you do not have to remember
the punctuation and indentation rules.

1. Choose the **source type**: Book, Journal article, or Website.
2. Choose the **style**: MLA 9, Chicago 17 (author-date), or APA 7.
3. Choose what to **insert**: the in-text citation, the full bibliography
   entry (Works Cited or References), or both.
4. Fill in the details: author or authors, title, year, and the fields for
   that source type. Separate several authors with a semicolon, for example
   `Jane Smith; John Doe`.
5. Choose **Insert**. The citation goes in at your cursor.

QUILL applies each style's rules for you, including author order and
"et al.", initials, italics, and where every comma and full stop goes. You
supply the facts and QUILL handles the formatting.

## Tables, code blocks and tags

QUILL can guide you through inserting tables, code blocks, HTML tags and
Markdown snippets. That helps when you want the structure but do not want to
type every opening and closing marker correctly by hand each time.

## Cleanup and normalization

The cleanup commands under **Format > Whitespace**, **Format > Sort and
Filter** and **Format > HTML and Encoding** are made for pasted material,
transcripts, exports and text moved from another program. Use them to turn
messy text into something steady and readable.

## Character encoding tools

Text for the web often runs into encoding trouble: one tool wants UTF-8 and
the next insists on plain ASCII. **Format > HTML and Encoding** has the tools to
sort that out.

### Finding characters that are not plain ASCII

**Show Non-ASCII Characters** opens a read-only report of every character
beyond plain ASCII. For each one it gives the line and column, the code
point, the Unicode name, and whether it converts cleanly to Latin-1 and to
Windows-1252 (MS-ANSI). It does the job people used to do at the command line
by running a file through `iconv` with a sentinel string and hunting for what
failed.

You can go back and forth between the report and your document:

1. In the report, put your cursor on a character's row. Each row starts with
   `line:column` followed by a tab.
2. Choose **Format > HTML and Encoding > Jump to Source Line**. QUILL switches
   to your document and puts you on that line.
3. When you have looked at the character, choose **Jump Back to Non-ASCII
   Report** to return to the report.

You can give Jump to Source Line a key in the Keymap Editor to go faster.

### HTML tags and entities

- **Strip HTML Tags** takes every tag out of the selection, or the whole
  document, and leaves just the words. It is the quick way to get readable
  text out of a piece of web page source.
- **Convert Non-ASCII to HTML Entities** rewrites every non-ASCII character
  as an HTML entity: a named one such as `&eacute;` where it exists, or a
  numeric one such as `&#233;`. Ordinary ASCII, including `&` and `<`, is left
  alone. This is the reliable way to feed text to a tool, like Pandoc, that
  refuses accented characters.
- **Encode HTML Entities** is the older command. It escapes only the five
  markup characters (`<`, `>`, `&`, `"`, `'`), not accents and symbols.
- **Decode HTML Entities** goes the other way. It turns entities such as
  `&eacute;`, `&amp;`, `&#233;` and `&#xE9;` back into é, &, é and é, using
  the standard HTML entity table. An entity it does not know, such as
  `&madeupword;`, is left as it is.

### Saving in a different encoding

- **Re-encode As...** saves a copy in the encoding you choose: UTF-8, UTF-8
  with a byte-order mark, Latin-1, Windows-1252 or ASCII. A character that
  does not fit a narrower encoding is written as a numeric HTML entity, never
  a question mark, so nothing is lost and you can always convert it back.
- **Analyze Encoding Requirements** tells you the smallest encoding your
  document fits in, without changing anything. Its short report gives your
  current encoding, whether the document still fits it, and if not, the
  simplest encoding that holds every character, checking in this order:
  ASCII, Latin-1 / ISO-8859-1, Windows-1252 / MS-ANSI, UTF-8.
- **Save Using Minimum Required Encoding...** saves a copy in exactly that
  encoding, so a document that only needs Latin-1 is not forced into UTF-8.
  You can still choose UTF-8 yourself whenever you want; QUILL never switches
  you to it without asking.

### Stripping and repairing characters

- **Remove Email Quote Markers** removes the `>` quote markers at the start of
  lines in forwarded email, including `Name>` style prefixes.
- **Strip Low ASCII Characters** removes control characters.
- **Strip High ASCII Characters** removes non-ASCII characters.
- **Convert to Hex Dump** opens a read-only view of the selection, or the
  whole document, as offset, hex and ASCII columns, so you can check exactly
  which bytes are there.
- **Convert OEM (DOS) to ANSI** and **Convert ANSI to OEM (DOS)** fix text
  from the DOS era that shows up as garbage in Windows, or the other way
  round, by converting between code page 437 (CP437) and Windows-1252.
- **Convert Line-Drawing Characters to ASCII** and **Strip Line-Drawing
  Characters** deal with box-drawing characters (`─`, `│`, `┌` and the rest
  of the U+2500 to U+257F block) left over from old DOS art or terminal
  output. The first turns them into plain `-`, `|` and `+`. The second removes
  them.

## More search and analysis tools

- **Multi Replace...**, on **Edit > Search Tools**, makes up to four find and
  replace swaps in one pass, with an option to ignore case. You do not have to
  run Find & Replace four times.
- **Count Occurrences...** (`Ctrl+Alt+Shift+F3`), also on **Edit > Search
  Tools**, tells you how many times some text appears in the selection or the
  whole document.
- **Count Regular Expression Matches...** and **Extract Regular Expression
  Matches...**, on the same submenu, ask for a regular expression. The first
  tells you how many matches there are. The second opens every match in a new
  document, one to a line, so you can pull all the email addresses or dates
  out of a long file. If regular expressions are new to you, **Tools >
  Advanced > Regular Expression Helper...** builds one for you.
- **Lines in First Block Only** and **Lines Common to Both Blocks**, on the
  same submenu, compare two lists in one document. Paste one list, then the
  other below it, and put your cursor on the first line of the second list.
  QUILL treats everything above the cursor as the first block and everything
  from the cursor down as the second, and gives you the lines only the first
  block has, or the lines both blocks have.
- **Line Statistics**, on **Tools > Advanced** (`Ctrl+Alt+W`), looks for lines
  that hold exactly one number and opens a short report: count, total,
  average, median, mode and standard deviation. Lines that are not plain
  numbers are skipped, so they cause no error.

### The Calculator

**Tools > Calculator...** is a calculator you can use without leaving your
writing, and it can work on numbers that are already in your document.

1. If the numbers you care about are in the document, select them first: a
   few figures, a column, some comma-separated lines or a whole table. QUILL
   puts them in the calculator for you.
2. Choose **Tools > Calculator...**. Your cursor is in the box labelled
   **Enter a calculation, or paste numbers, a column, or a table**.
3. To work something out, type it, for example `sqrt(264)`, `10 percent of
   500` or `2^10 + 5!`, and press **Calculate expression**.
4. To sum up a set of numbers, choose a **Data operation**: Sum, Average,
   Minimum, Maximum, Count, Product, Median, Range or Standard Deviation. Then
   choose what it is **applied to**: All numbers, Down each column, Across
   each row, or a Full summary. Press **Apply**.
5. The answer is in the **Result** box. **Copy Result** puts it on the
   clipboard, and **Insert Result at Cursor** types it into your document.
6. Press Escape, or **Close**, when you are done.

## The four announcement channels

Everything QUILL tells you travels on four channels, and you choose which ones
you want:

- **Speech**: through your screen reader, or QUILL's own voice when no screen
  reader is running.
- **Braille**: the same message on a connected display. See the next section.
- **Sound**: short sounds for things that happen often, so you can stop
  listening to confirmations you already expect.
- **Status**: the status bar, which always shows the message.

**QUILL, Quill Radio and Quill Weather** all send announcements the same way,
so they behave alike wherever you are.

### Three commands worth knowing

All three are in the command palette. Give them keys in the Keymap Editor if
you use them often.

- **Repeat Last Announcement** says the last message again. Speech is gone
  the moment it ends, so this helps when you were reading something else as a
  message went by.
- **Announcement Self-Test...** sends a test phrase on every channel, then
  shows a report you can copy, saying which channels delivered it and which
  screen reader or display handled each one. If something is not reaching
  you, this is the quickest way to tell whether the trouble is QUILL, your
  screen reader, or a display that is not connected.
- **Report Editor Surface** tells you, in one keystroke, which editor is
  active, its window class, whether the braille fix (system-edit emulation)
  is on, whether the editor border is hidden, and whether braille output is
  working and through which route. Nothing from your document is included. If
  you report a braille or speech problem, run this first and include what it
  says, so the problem can be looked at straight away.

### Announcement settings

These are in **Settings > Accessibility and Announcements**, and you can search for them:

- **Show announcements in braille**: on by default.
- **Braille announcement style**: the same wording as speech, or a short form
  with the position first (`p7/87 l14 c3`).
- **Hold errors on the braille display**: keeps an error under your fingers
  instead of letting the next message replace it.
- **Sound cues in the companion apps**: sounds in Quill Radio and Quill
  Weather.
- **Confirm with a sound in Quiet Mode**: hear that something worked without
  QUILL speaking.
- **Keep an announcement history**: on by default. QUILL keeps a short list
  of what it has said, for the Spoken Echo and Repeat Last Announcement. Turn
  it off and nothing is kept, and the list is cleared straight away; Repeat
  Last Announcement can then only repeat the message still on the status bar.
- **Interrupt speech for**: which messages cut across whatever your screen
  reader is saying. **Warnings and errors** is the default: problems, and the
  answer to something you just asked for, cut in. **Errors only** lets
  everything except a failure wait its turn. **Never interrupt** lets every
  message wait. The change takes effect as soon as you press OK.

Quiet Mode and Meeting Mode silence braille along with speech: nothing is
said and nothing is flashed to the display. The status bar keeps updating,
so you can still read the latest message there.

### Announcements on a braille display

Everything QUILL announces, such as "Saved", "Now playing: ...", "Weather
updated", or a recording starting and stopping, goes to a connected **braille
display** as well as to speech, in QUILL and Quill Radio alike. It works
through whichever screen reader you use: JAWS and NVDA both accept a flash
message, and Narrator brailles the notifications QUILL already sends.

Four things are worth knowing:

- **Braille never costs you speech.** If the display is unplugged partway
  through, or the screen reader refuses the message, you still hear it.
- **Nothing is cut short.** A long message is sent whole so you can pan
  across it. Cutting it to the width of the display would lose the end of a
  track title, which is usually the part you wanted.
- **The same message is not flashed twice in a row.** A flash replaces what
  is under your fingers, so an identical message within a couple of seconds
  (a stream repeating the same title, for instance) is skipped.
- **A burst of messages settles instead of flickering.** When several
  different messages arrive quickly, the first is shown at once and the rest
  are replaced a moment later by the newest one, so the display is never a
  blur. Errors are the exception: an error is always shown straight away.

QUILL Lite now settles bursts in exactly the same way, using the same code, so
dictation's live preview no longer flickers on the display there either.

To keep the display on your document, turn off **Show announcements in
braille** in **Settings > Accessibility and Announcements**. Quiet Mode and Meeting Mode
silence braille along with speech.

## What you learned, and where to go next

You can now change case and tidy lines, apply rich formatting that stays out
of your way until you save, and build headings, sections and lists by
keyboard. You know how to write equations and citations, fix encoding
problems, and choose how QUILL's announcements reach you.

To practise, open **Help > Tutorials...** (`Ctrl+Alt+F1`) and try "Structure
and formatting" and "Tables, by ear" in the Writing and editing track. For
maths, work through
[Write math without learning a new language](https://www.quillforall.org/tutorials/07-type-math-like-a-pro.html)
on the website.

Next, Chapter 6, Moving around and finding things, shows you how to get
around all that structure quickly.

---

- Previous: [Chapter 4: Writing and editing](quill-guide-04-writing-and-editing.html)
- Next: [Chapter 6: Moving around and finding things](quill-guide-06-moving-around-and-finding-things.html)
- [Contents](../userguide.html)
