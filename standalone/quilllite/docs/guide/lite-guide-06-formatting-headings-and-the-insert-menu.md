# Chapter 6: Formatting, headings and the Insert menu

The formatting keys are the ones you know from WordPad, and QUILL Lite makes
each one write the right thing for the kind of document you are in. This
chapter covers bold, lists and headings, how to hear that you are on a heading
or in a list, how to skim a long document by folding it, and how to reshape it
by moving whole sections. Then come links, and the Insert menu: the date,
emoji, special characters, line breaks, and the Markdown and HTML tag
pickers.

## Formatting

The formatting keys are the ones you know from WordPad. Ctrl+B is still bold,
Ctrl+I is still italic. What changes is that QUILL Lite gives you the right
kind of bold for the document you are in.

### One key, the right answer for your document

In a Markdown document, bold is two asterisks. In HTML it is a tag. In rich
text it is real bold. So when you press **Ctrl+B**, QUILL Lite writes whatever
bold means in the document in front of you. Headings work the same way.

| In a | **Ctrl+B** writes | **Ctrl+Alt+2** writes |
|---|---|---|
| Markdown document | `**bold**` | `## Heading` |
| HTML document | `<strong>bold</strong>` | `<h2>Heading</h2>` |
| Rich text document | real bold | a 16-point bold paragraph |
| Plain text document | nothing, and says why | nothing, and says why |

Here is how it feels in practice:

1. Select a word and press **Ctrl+B**. The word is wrapped in bold.
2. Or press **Ctrl+B** with nothing selected. The markup goes in empty, and
   your cursor lands in the middle of it, so you can type the bold words
   straight away.

In Markdown and HTML you hear what was written, for example "Bold in
Markdown". That tells you two asterisks appeared, which is what actually
happened.

In HTML, bold is written as `<strong>` and italic as `<em>`. Screen readers
can treat those as important text, which plain `<b>` and `<i>` do not give
them.

Applying a heading replaces the old one. Press **Ctrl+Alt+2** on a line that
says `### Notes` and you get `## Notes`. If an HTML heading has an `id=`, it
is kept, so links pointing at that heading still work.

Alignment, line spacing and font are for rich text only. If you try one in
another kind of document, QUILL Lite tells you it cannot run there.

### Lists

**Ctrl+Shift+L** works in rich text and in Markdown. It goes round in a
circle, like WordPad's list button: bulleted list, numbered list, no list,
then back to the start. Each stop says its name, so keep pressing until you
hear the one you want.

In rich text, the bullets and numbers are drawn for you and renumber
themselves. In Markdown, QUILL Lite writes `- ` or `1. ` at the start of the
lines you selected, and only those lines.

#### Pressing Enter in a list

In a Markdown document, **Enter** keeps a list going, the way it does in QUILL
and in other Markdown editors. QUILL Lite says what it did, because your screen
reader only hears a new line:

- **Enter** at the end of an item starts the next one with the next marker: a
  hyphen after a hyphen, `3. ` after `2. `, `3) ` after `2) `, and an unchecked
  `- [ ] ` after a task item. A nested item keeps its indentation. You hear
  "Continued list item".
- **Enter** in the middle of an item splits it. In `1. bread milk`, with the
  cursor before `milk`, you get `1. bread` and `2. milk`.
- A new numbered item renumbers the items under it, so adding an item after the
  first of `1. 2. 3.` gives `1. 2. 3. 4.`, and you hear "Continued list item,
  renumbered 2 items below". If your list jumps (from `2.` to `7.`), your own
  numbering from the jump on is left alone.
- **Enter** on an item with nothing after its marker ends the list. The marker
  goes, the empty line stays, and you hear "Exited list".
- **Ctrl+Z** straight afterwards takes the whole thing back in one step: the new
  line, its marker and any renumbering.

This needs the **Markdown and HTML** area switched on in Customize Features,
like everything else that writes Markdown for you.

**In plain text, only if you ask.** Check **Continue lists in plain text** in
**Tools > Preferences** and the same happens in a `.txt` file or a new untitled
document. It starts off, because in plain text a line that happens to begin
with `1.` is as often a date or a version number as a list. It never happens in
a source code or settings file, whatever the box says, and never in rich text,
where **Ctrl+Shift+L** makes real lists and **Enter** is WordPad's own.

### Keys that only work in rich text

Underneath, every QUILL Lite document uses the same Windows editing box that
WordPad uses. That box has some keys of its own: **Ctrl+U** underlines,
**Ctrl+E**, **Ctrl+L**, **Ctrl+R** and **Ctrl+J** change alignment,
**Ctrl+=** and **Ctrl+Shift+=** raise and lower text, and there are a few
more. In a rich text document they all work as you would expect.

In a Markdown, HTML or plain document, those keys have nothing to do. So
QUILL Lite catches them and tells you, once per key in each document:

> Underline has no meaning in a plain text document.

After that, pressing the same key again stays quiet, so you are not told the
same thing over and over. Your document is never changed behind your back.

### The formatting keys at a glance

| Key | What it does |
|---|---|
| **Ctrl+B**, **Ctrl+I**, **Ctrl+U** | Bold, italic, underline |
| **Ctrl+Shift+.** / **Ctrl+Shift+,** | Bigger / smaller text |
| **Ctrl+L**, **Ctrl+E**, **Ctrl+R**, **Ctrl+J** | Left, centre, right, justify |
| **Ctrl+Shift+L** | Lists: bulleted, numbered, none, round again |
| **Ctrl+1**, **Ctrl+5**, **Ctrl+2** | Single, one-and-a-half, double spacing |
| **Ctrl+Alt+1** to **Ctrl+Alt+6** | Heading 1 to 6 |
| **Ctrl+Alt+0** | Back to ordinary text (removes the heading) |
| **Ctrl+Shift+N** | Normal Text: take *all* formatting off |
| **Ctrl+Shift+D** | Describe the formatting where the cursor is |

The heading keys are also in **Format > Headings**. The number in the menu is
the number you press.

#### How big each heading is

In rich text, a heading is bold text at its own size: 20, 16, 14, 12, 11.5
and 10.5 point for levels 1 to 6. Ordinary text is 11 point. These are the
same sizes QUILL uses, so when somebody opens your document in Word, the
headings still look like headings. Every level has its own size, so QUILL
Lite can always find every heading again.

#### Taking it all off: Normal Text

**Ctrl+Shift+N** is Normal Text. It is the quick way back to plain, ordinary
text when you are not sure what is applied. One press:

- takes off bold, italic, underline and strikethrough,
- puts the size back to ordinary body text,
- clears the colour and the highlight,
- sets the paragraph back to left aligned and single spaced,
- and takes it out of any list.

One **Ctrl+Z** puts it all back if you change your mind. The typeface stays
as it is. To change that, use **Format > Editor Font**. This is the same key
Word uses for the same job.

In a Markdown or HTML document, **Ctrl+Shift+N** takes the heading marks off
the line instead.

#### Asking what is here

**Ctrl+Shift+D** is the key worth remembering. It tells you what you are
standing in, for example "Arial, 16 point, heading 2, bold". When you cannot
see the page, this is how you find out how your text looks.

### Moving between headings

| Key | What it does |
|---|---|
| **Ctrl+Alt+H** / **Ctrl+Alt+Shift+H** | Next / previous heading |
| **Ctrl+Alt+L** | The list of every heading |

These work in every kind of document. In rich text they find the heading
sizes listed above. In Markdown they find lines that start with `#`. In HTML
they find `<h1>` to `<h6>`. A `#` inside a fenced code block is not treated
as a heading.

### Skimming a long document with folding

When a sighted person gets a long document, they scroll and glance to see
what is in it. Folding gives you the same quick overview by ear.

| Key | What it does |
|---|---|
| **Ctrl+Shift+F9** | **Fold or Unfold Section** (the one you are in) |
| **Ctrl+Alt+Shift+Down** | **Next Section** |
| **Ctrl+Alt+Shift+Up** | **Previous Section** |
| **Ctrl+Shift+F10** | **Unfold Everything** |

Try it like this:

1. Open a long Markdown document.
2. Press **Ctrl+Alt+Shift+Down** to move from section to section.
3. Each time, you hear the heading, whether it is folded, and how many lines
   are under it, for example "Installing, expanded, 34 lines".

Folding never hides your text. A folded section reads exactly the same when
you arrow through it, and Find still finds things inside it. Think of a fold
as a note to yourself that says "I have dealt with this part". You hear it as
you pass by.

Folding works in Markdown documents, where a heading line starting with `#`
marks where each section begins.

If you would like to practise this with the app guiding you, the tutorial
*Skimming something long* walks through it step by step.

### Hearing that you are on a heading

When you arrow onto a heading, QUILL Lite says the level, for example
**"Heading 2"**.

Your screen reader cannot tell you this in an editor, because Windows editing
boxes have no way to mark a paragraph as a heading. So QUILL Lite says it for
you, and keeps it short:

- **Just the level.** Your screen reader is already reading the line, so you
  do not hear the words twice.
- **Once, when you arrive.** Moving around inside the heading says nothing
  more. Leave and come back, and you hear it again.
- **In rich text and in Markdown alike.**

When you apply a heading yourself, you hear that once, not twice. And opening
a document whose first line is its title does not greet you with
"Heading 1".

#### Turning heading announcements off

Sometimes you just want to read a document as text. Press **Ctrl+Alt+F3**
(**View > Announce Headings**) to turn the heading cue off, and press it again
to turn it back on. You hear which way it went: "Headings will not be
announced", or "Headings announced on arrival". QUILL Lite remembers your
choice, but it is meant to be flipped whenever you need it.

#### When a # is not a heading

In a `.md` or `.txt` file, or a new document you have not named yet, a line
starting with `#` is a heading. In a `.py`, `.sh`, `.ini`, `.yml` or `.conf`
file, a `#` starts a comment, so QUILL Lite says nothing and lists nothing.
In an HTML document, headings are `<h1>` to `<h6>`, and those are the ones
QUILL Lite reads and writes.

### Hearing that you are in a list

When you arrow into a list, QUILL Lite says something like **"Bulleted list,
5 items"**. Go a level deeper and you hear **"Level 2, 3 items"**. Arrow out
and you hear **"Out of list"**.

On a web page, your screen reader tells you about lists. In an editor, a list
is just lines of text, so without this a nested outline would sound like a
run of lines starting with a dash. You would be left counting spaces by ear
to know the level.

It works in Markdown and in HTML, for all three kinds of list:

| | Markdown | HTML |
|---|---|---|
| **Bulleted list** | `-`, `*`, `+` | `<ul>` |
| **Numbered list** | `1.`, `1)` | `<ol>` |
| **Definition list** | a line, then `: the definition` under it | `<dl>` |

In a definition list you also hear **"Term"** and **"Definition"** as you move
between them, so you always know which part you are in.

Items are counted at your own level, inside your own list. Say a list has
three items and the second one has four sub-items. You hear "3 items" at
level one and "4 items" at level two, never "7". Two sub-lists under two
different bullets count as two separate lists.

#### What it never says

- **Nothing as you move down a list.** Your screen reader is already reading
  each item.
- **Nothing about `- - -` or `***`.** Those are dividing lines, not lists.
- **Nothing inside a fenced code block.** A `- ` in a code sample is part of
  the sample.
- **Nothing in a plain text document.** Ordinary writing is full of hyphens,
  and you do not want to hear about every one.

#### Turning list announcements off

Press **Ctrl+Alt+F5** (**View > Announce Lists**). It has its own switch,
separate from headings. When you are reorganising an outline, the levels
help. When you are proof-reading, you may prefer quiet. You hear which way it
went: "Lists will not be announced", or "Lists announced as you enter them".

#### Which item you are on

The spoken cue does not tell you which item you are on, because hearing that
on every arrow press would be too much. The status bar's List cell does. It
says something like "Bulleted list, 4 of 9, level 2", and you can check it
whenever you like. Press **Enter** on that cell to turn the spoken list cue
off and on.

### All of them at once: the Heading Organizer

**Alt+Shift+O** opens **Heading Organizer...**: every heading in your
document in one list. It is the easiest way to see and change the shape of a
document, because the list reads the shape back to you as you work.

1. Arrow through the list. Each row says its level and its text, for example
   "Heading 2: Installing".
2. Press **Tab** to demote the heading you are on, or **Shift+Tab** to
   promote it.
3. Use **Move Up** and **Move Down** to move a heading, together with
   everything under it, past its neighbour.
4. Use **Rename** to change a heading's words without moving it.
5. Use **Validate** to check the result. It makes sure the document starts at
   Heading 1 and never skips a level on the way down, which is what screen
   readers rely on.
6. Press **Apply** when you are happy.

Beside the list there is a preview of the section under the heading you are
on, which helps when two headings have similar names.

Nothing changes in your document until you press **Apply**. Everything you
did counts as one change, so one **Ctrl+Z** puts it all back. QUILL has the
same window.

The Heading Organizer works in Markdown, HTML and rich text documents. In rich
text it moves each heading with its formatting, so bold and sizes come along.

### Rearranging headings one at a time (Format > Structure)

| Key | What it does |
|---|---|
| **Alt+Shift+Left** | Promote heading: one level shallower |
| **Alt+Shift+Right** | Demote heading: one level deeper |
| **Alt+Shift+Up** | Move this whole section up, past whatever is above it |
| **Alt+Shift+Down** | Move this whole section down, past whatever is below it |
| **Alt+Shift+F5** | Select this section, subsections and all |
| **Ctrl+Alt+Shift+F5** | Move Section To...: pick a destination instead of a direction |

These keys save you from cutting and pasting to reorganise a document.
Selecting a section by hand means finding exactly where it ends by ear, which
is easy to get wrong. **Alt+Shift+Up** moves the whole section in one press
and tells you what happened.

A "section" is the heading you are in plus everything under it, down to the
next heading at the same level or higher. So moving a Heading 2 brings its
Heading 3s along with it.

#### Where a moved section lands

The move keys always move. If there is no heading at the same level next to
yours, the section simply trades places with whatever is next to it, the
same way Word's outline view does on these keys. The first section inside a
parent moves up above the parent's own heading.

A moved section keeps its level. Press the other key and you are back exactly
where you started. To change a level, use **Alt+Shift+Left** and
**Alt+Shift+Right**. You can move a section and then promote it.

You hear where the section ended up, for example *"Section moved below Soup.
Now 2 of 3 at this level."* That tells you where it sits in the outline, which
your screen reader cannot tell you.

Sometimes a section has nowhere to go. In a document where every heading sits
inside the one before it, everything below you is inside your own section.
QUILL Lite tells you so and suggests what to do: *"Bottom of Heading 1.
Everything below is inside this section. Alt+Shift+Left promotes Heading 3 to
make it a sibling."* The key it names is your own, so it is still right if
you have changed it.

#### Select Section (Alt+Shift+F5)

**Alt+Shift+F5** selects the section you are in, with every subsection,
stopping just before the blank line that separates it from the next one.
Then press **Ctrl+X** and **Ctrl+V** to put it anywhere you like: elsewhere
in this document, in another document, or in another program.

You hear how much you selected, for example *"Selected Bread and 1 section
under it, 7 lines"*, or *"Selected Bread, 4 lines"* when nothing is nested
inside. That answers the question "did it take the sub-headings too?"

#### Move Section To... (Ctrl+Alt+Shift+F5)

Pressing **Alt+Shift+Up** forty times is no way to move a section across a
long document. **Ctrl+Alt+Shift+F5** asks where you want it to go instead.
It asks two questions, each answered from a list you can type into.

1. **Which heading?** Every heading in the document, in order, one per row,
   for example `3 of 7, level 2 - Bread`. The position comes first, so two
   sections both called "Notes" are easy to tell apart. Type to narrow the
   list; the order stays the same as you type. You start in the search box,
   and **Enter** there takes you into the results.
2. **Before it, after it, or inside it?** Pick one of three rows. Note that
   **After it** puts your section below that heading *and everything under
   it*.

The whole move is one change, so one **Ctrl+Z** undoes it. You hear where the
section landed: *"Moved Salad before Bread. Now 1 of 3 at this level."*

**Inside it** is the only choice that changes levels. Your section becomes
the last one under the heading you picked, and it and everything under it go
one level deeper. You hear the new level: *"Moved Bread inside Soup, now
Heading 3. Now 1 of 2 at this level."*

There are two things it will not do, and it tells you why:

- **A section cannot move inside itself.** If you pick a heading that sits
  under the one you are moving, you hear *"Sourdough is inside Bread, so Bread
  cannot move into it. Promote Sourdough first if you want them side by
  side."* Those headings stay in the list, so you are never left wondering
  where one went.
- **Nothing goes deeper than Heading 6**, because Markdown has no deeper
  level. It tells you so and offers **After it** instead.

Press **Escape** at either question to change nothing. Nothing is announced,
because nothing happened.

#### Good to know about all six keys

- **Promoting a Heading 1 leaves it a Heading 1.** It never turns into
  ordinary text.
- **Moving and selecting sections need a Markdown or HTML document**, where
  the heading is written in the text. In rich text a heading is a font size,
  so there is nothing to move, and QUILL Lite tells you so. Promoting and
  demoting work in both.
- **These keys are the same in QUILL.** Learn them once and they work in both
  editors, and you hear the same words in each.

The tutorial *Skimming something long* ends with rearranging a document, if
you would like to try these keys with some guidance.

### Checking off tasks

A task list is a list whose items start with a box: `- [ ]` for something to do
and `- [x]` for something done. Plans written by AI (artificial intelligence) are full of them, and
**Ctrl+Alt+I** (**Markdown Tag...**) can insert one.

Put the cursor on a task and press **Ctrl+Alt+Enter** (**Format > Toggle Task
Done**) to check it. Press it again to uncheck it. You hear what changed and how
many tasks in that list are done, for example "Checked: Write the tests. 3 of 7
tasks complete." Select several tasks first to check them all at once.
**Ctrl+Z** takes it back. On a line that is not a task, QUILL Lite says so and
changes nothing. This is the same key as in QUILL.

## Links

To add a link, press **Ctrl+K**. A box opens asking for the address and the
words to show.

- If you select some words first, they are already filled in for you.
- If you leave the words empty, the address itself is shown as the link.

QUILL Lite writes the link the right way for your document: `[text](address)`
in Markdown, and `<a href="address">text</a>` in HTML. In a rich text document,
the link becomes a real link in the text, with no brackets to see.

## The Insert menu

The Insert menu is for anything you put into your document other than typing.

| Key | What it does |
|---|---|
| **F5** | Today's date and the time |
| **Ctrl+Shift+F2** | Special Character: 357 of them, in 15 groups, searchable by name or code point |
| **Alt+.** | Emoji: search or browse, with a description of each one |
| **Shift+Enter** | A line break that does not start a new paragraph |
| **Ctrl+Enter** | Page Break: the rest starts on a new page (Word, Rich Text and Markdown documents) |
| **Ctrl+Alt+T** | Table: the columns and rows you ask for, a real table in rich text (see "Making a table") |
| **Ctrl+Alt+I** | Markdown Tag: everything Markdown can write (Markdown documents only) |
| **Ctrl+Alt+O** | HTML Tag: 111 tags and 20 whole form fields, searchable by what they do |

Insert sits just before Format on the menu bar, the same as in Word. You put
something in, then you format it.

### Emoji (Alt+.)

Press **Alt+.** to open the emoji picker. You can search by name, by keyword,
by what it looks like, or by a typed smiley: `:)` finds the smiling face and
`<3` finds the heart. Or you can browse by category, starting with
**Favourites** and **Recent**.

Every emoji has a written description of what it shows. You arrow through a
list, and the description sits in a pane beside it, so you know exactly what
you are about to send.

When you insert one, QUILL Lite says its name. Screen readers do not all read
emoji the same way, and some say nothing at all, so this is how you know it
went in.

Emoji work in every kind of document, rich text included.

### The two tag pickers

There are two tag pickers, one for Markdown and one for HTML.

Markdown Tag appears only in Markdown documents. In a plain or rich text
document it is not on the Insert menu at all, and if you press **Ctrl+Alt+I**
there, QUILL Lite just says "Markdown tags are for Markdown documents."

HTML Tag stays on the menu in every document, but it is greyed out unless the
document is HTML, and your screen reader tells you so when you arrive on it. If
you press **Ctrl+Alt+O** anyway, QUILL Lite tells you what kind of document you
are in and that **Ctrl+Alt+F6** is how to change it.

In both pickers, if you have text selected, the tags go around it. If you do
not, the cursor lands between the opening and closing tags, ready for you to
type.

#### Markdown Tag (Ctrl+Alt+I)

This offers bold, italic, inline code, a fenced code block, the six heading
levels, bullet, numbered and task lists, blockquote, link, image, table and
footnote. Type a few letters to narrow the list. If you choose Link or Image,
it asks you for the address next. An image then asks for its alt text: a short
sentence saying what the picture shows and why it is there. Anything you had
selected is already in the box. Leave it empty only for a decorative image; QUILL
Lite then tells you that **Tools > AI > Propose Alt Text** can draft it.

#### HTML Tag (Ctrl+Alt+O)

This offers 111 tags and 20 whole form fields. You can search by what a tag
does as well as by its name. Type "dropdown" and you find both a finished,
labelled dropdown and the bare `select` tag. Type "glossary" and you find
`<dl>`. Type "acronym" and you find `<abbr>`. Type "subtitles" and you find
`<track>`.

When you choose a bare tag, QUILL Lite asks if you want to add attributes, for
example `class=note; id=summary; aria-label=Summary`. If you do not need any,
just press **Enter** on the empty box to skip it.

#### Whole form fields, wired up

The first rows in the HTML picker are not single tags. They are finished form
controls. Choose **Form field: dropdown** and you get the label, a `for` that
matches the field's `id`, the `<select>`, and three `<option>`s, all at once.

This saves you the fiddly part. The connections between a label and its field
are invisible on the page. A missing `for`, a radio group without a shared
`name`, or two fields with the same `id` all look fine until somebody tries to
use the form. These fields arrive with all of that already done.

| Choose | You get |
|---|---|
| **text**, **email**, **password**, **telephone**, **web address**, **number**, **date**, **search**, **file upload** | a labelled input of that type, with `autocomplete` where the browser can help |
| **long answer (textarea)** | a labelled, five-row text area |
| **dropdown (select)** | label, select, and an empty first option, so nobody can send an answer they did not choose |
| **dropdown with groups** | the same, with two `<optgroup>`s |
| **checkbox** | the box first, then its label, so the label can be pressed too |
| **checkbox group** | a `<fieldset>`, a `<legend>`, and boxes sharing one `name` |
| **radio group** | the same, with three radio buttons, one shared `name`, and exactly one chosen to start with |
| **autocomplete (input + datalist)** | an input joined to its own list of suggestions |
| **required, with hint and error** | a hint and an empty error, both named by `aria-describedby`, plus `aria-invalid` and `role="alert"` |
| **submit button** | a `<button type="submit">` with real text, not an `<input value="">` |
| **whole form** | a contact form: fieldset, legend, three labelled fields, and a submit button |
| **grouped fields (fieldset)** | an empty fieldset with a legend, for grouping fields you already have |

Two things make this even easier:

- **Select a word first and it becomes the label.** The `id` is made from the
  same word, so the two match. Select "Postcode", choose **Form field: text**,
  and you get a Postcode field with `id="postcode"` and `for="postcode"`.
- **It never repeats an `id`.** QUILL Lite checks your document first. If you
  insert a second email field, its `id` is `email-2`, so the two fields never
  get mixed up.

The bare tags are all still in the list, just below the form fields, for when
a single tag is what you want.

### Typing things there is no key for

**Insert > Special Character...** (**Ctrl+Shift+F2**) opens a picker with 357
characters that your keyboard has no key for. There are two ways to find one.

#### Search for it

The window opens in the search box. Type part of a name, such as `dash`,
`euro`, `acute`, `arrow` or `apostrophe`. Everyday words work too, even when
they are not the official name: `gbp`, `sterling`, `copyright`, `eszett`,
`micro`. Press **Enter** to move into the results.

You can also type a code point. `2014`, `U+2014` or `d8212` all bring up the
em dash first. This works for any character at all, even one that is not in
the 357.

#### Browse a group

Clear the search box and you can browse fifteen groups: Whitespace, Dashes and
hyphens, Quotes, Invisible and control, Typography, Legal and reference marks,
Currency, Maths and units, Fractions, Superscripts and ordinals, Arrows,
Accented letters (small and capital, listed separately), Greek letters, and
Punctuation from other languages.

#### Choosing and inserting

The results list has three columns: the character, its name and its code
point. As you arrow, the **Description** pane below shows the same detail
**Character Details...** gives for a character already in your document. The
code point is handy when two names sound alike: "Thin space" is U+2009 and
"Hair space" is U+200A.

Press **Enter** to insert the character you are on. QUILL Lite then tells you
what it put in, for example "Inserted, U+2014 Em dash". Many of these
characters are invisible on the page, so hearing it is how you know it worked.

QUILL has the same picker, on the same key.

### Starting a new page

**Insert > Page Break** (**Ctrl+Enter**, the same key as in Word) starts a
new page at the cursor. In a Word or Rich Text document it is a real page
break, the same one Word makes, and it is still there when you save the
file and open it again. In a Markdown document QUILL Lite puts the line
`::: pagebreak` on its own line, and the break takes effect when you export
to a format that has pages, such as Word or PDF. A plain text document has
no pages, so QUILL Lite tells you that instead of doing nothing.

### Ending a line without starting a paragraph

**Insert > Line Break** (**Shift+Enter**, the same key as in Word) ends the
line you are on and starts a new one, without starting a new paragraph.

This matters mostly in Markdown. A blank line between two lines makes two
paragraphs, usually with a gap between them. A line break keeps them in the
same paragraph, one under the other. That is what you want for an address, a
poem, or a few short lines that belong together.

QUILL Lite writes the break the way the **Markdown line break style** setting
says, and tells you which one it used. The standard choice is a backslash at
the end of the line. The other choice is two spaces at the end of the line,
which you cannot see or hear, and which some programs remove when they save.
If you have ever added two spaces to the end of a line and nothing happened,
that is probably why.

QUILL has the same command on the same key.

## What you learned, and where to go next

The formatting keys write the right thing for each kind of document.
**Ctrl+Shift+N** takes all formatting off, and **Ctrl+Shift+D** tells you
what formatting you are standing in. You can move between headings, hear when
you arrive on a heading or walk into a list, skim with folding, and reshape a
document with the Heading Organizer and the Structure keys. **Ctrl+K** adds a
link written the right way for your document. The Insert menu puts in the
date, emoji, special characters, line breaks and Markdown or HTML tags, and
tells you what went in each time.

For a guided walk through headings, folding and rearranging, try the tutorial
*Skimming something long*. To see how the kind of document changes what these
keys write, try *Four kinds of document, and how to say which*.

Next, Chapter 7, Checking your writing, covers spelling, the thesaurus and the
dictionary.

---

- Previous: [Chapter 5: Selecting, copying and changing text](lite-guide-05-selecting-copying-and-changing-text.html)
- Next: [Chapter 7: Checking your writing](lite-guide-07-checking-your-writing.html)
- [Contents](../userguide.html)
