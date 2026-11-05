# Chapter 3: Blocks made plain

## What this chapter covers

WordPress keeps most page layout in blocks. This chapter explains how QUILL
shows blocks as plain text you can read line by line, how to insert one,
move between them, rearrange them, change their settings, and hear what the
site will make of them before you publish. It also covers patterns, the
notes people leave on blocks, and the tools for links and icons that live
inside a page.

## What a block is

In the WordPress block editor, a page is a stack of blocks: a paragraph, a
heading, a picture, a button, two columns side by side, an embedded video, a
pattern your designer made. In a browser it is a canvas full of floating
toolbars, and it is one of the hardest parts of WordPress to use with a
screen reader.

In QUILL a block is just a piece of your document with a name. Every action
on it is a command, a list or a form. Nothing floats and nothing is dragged.

## How blocks look in a Markdown document

**Ordinary writing stays ordinary.** A paragraph, heading, list, quote,
picture, table, separator or code block is plain Markdown. QUILL adds and
removes WordPress's hidden block markers itself, when it opens and when it
sends. You never see or type one.

**Other blocks are fences.** A fence is a line starting with three colons.
A button is one line:

```
::: button "Book a session" https://example.org/book
```

Blocks that hold other blocks open and close:

```
::: columns
::: column
Morning sessions run from nine.
::: column
Evening sessions run from six.
::: end columns

::: details "What does it cost?"
The first session is free.
::: end details
```

QUILL writes fences for buttons, columns, groups, details (the fold-away
kind), embeds, spacers and preformatted text.

**Anything else is an island.** A block QUILL has no Markdown for, such as a
plugin's contact form or a complicated gallery, shows as one protected line,
for example:

```
::: block jetpack/contact-form island-3
```

The block's real content waits in the background and goes back to your
site exactly as it came. Leave the line where it is, or move it with the
rest of the text, and the block stays whole.

**Nothing is converted on trust.** When QUILL opens a page, it turns each
block into Markdown and straight back again, and compares the result with
the original. If one byte differs, such as an extra colour or a setting
Markdown cannot say, that block becomes an island instead. So opening a
page and sending it back never changes a block you did not edit.

## How blocks look in an HTML document

An HTML document shows the page exactly as the site keeps it, with
WordPress's block markers as HTML comments, such as
`<!-- wp:paragraph -->`. Leave them where they are. Every command in this
chapter works in an HTML document too, and keeps the markers right for you.

## Inserting a block

1. Put the caret in the block you want the new one to follow.
2. Choose **Insert > WordPress Block...**.
3. The list holds every block you can add: the everyday ones first, then the
   rest of your site's blocks, its patterns and its synced patterns. Each row
   says the block's name and what it is for.
4. Type part of a name in **Find** and press Enter to narrow the list. "but"
   finds Button and Buttons.
5. Choose **Insert**. A short form asks only what that block needs: a button
   asks for its text and link, columns ask how many, details asks for its
   summary line, an embed asks for the address.
6. Press OK. The block goes in after the block you were in, and you hear
   its name and "inserted".

**Patterns** are the easiest blocks of all. A site owner, or their designer,
builds "Event announcement" or "Staff profile" once in the block editor.
From then on, anyone can insert it by name and fill in the words.

**Patterns from WordPress.org.** In the same window, choose **WordPress.org
Patterns** to search the free Pattern Directory. Before a pattern goes in,
QUILL tells you what it is for, the blocks it holds in order, and how many
of its pictures have no alternative text, so you know what you are adding.
Undo takes it out again.

## Moving through blocks

These are in **Edit > WordPress**:

- **Next Block** and **Previous Block** move the caret from block to block
  and say what each one is, where it is and how it starts, for example
  "Image block, 4 of 12: Volunteers at the spring fair". At either end you
  hear "No more blocks after this one" or "No blocks before this one".
- **Where Am I** says the block you are in and what it sits inside, for
  example "Paragraph block: Morning sessions, inside column 1 of Columns".
  Between blocks it says "Not in a block" and names the next one.

## The Blocks window

**View > WordPress Blocks...** opens a list of every block in the document,
with blocks inside other blocks listed under them. From it you can:

- **Go To** the block: the window closes and the caret is on it;
- **Move Up** and **Move Down**, which swap it with its neighbour;
- **Duplicate**, which puts a copy straight after it;
- **Remove**, after a question;
- **Change To**, which makes a paragraph a heading, a list into paragraphs,
  and so on;
- **Group**, which puts the block inside a new Group block, and **Ungroup**,
  which takes it out again.

Each change is one step, so Ctrl+Z in the document takes it back, and
nothing else in your document moves. Every byte outside the block you
changed stays exactly as it was.

## Block settings

**Format > WordPress > Block Settings...** opens a form for the block the
caret is in: its alignment, its width (wide or full, where the theme allows
it), its colours, its font size and any other setting it has. A plugin's
block gets a usable form too, built from what the block says about itself.

**Colours and sizes come from your theme, by name.** You choose "Accent
(dark green)" and "Large", never a code such as `#2f5d50`. Every colour says
how well it reads against what it sits on, for example "Accent (dark green),
7.4 to 1, passes". You can still choose a faint one; QUILL tells you it is
hard to read.

In a Markdown document, a setting Markdown cannot write turns the block into
a protected island line. QUILL asks before it does that.

When the settings are saved you hear "Block settings changed", with a
warning added if a colour you chose is too faint.

## Hearing what the site will show

**View > Preview Blocks** asks your site to draw its blocks, without saving
anything, and reads the result as plain text. Use it to hear what a list of
latest posts, a query loop or a plugin's block will really say before you
publish. Some blocks are drawn fresh by the site every time a visitor comes,
and this is the only way to hear them from QUILL.

**View > Play Media Here** plays the sound or video block the caret is in,
streamed from your site, with the same player keys as the Media Library's
Play (Chapter 4). Nothing is downloaded. On any other block you hear "There
is no audio or video block at the caret."

## Notes on blocks

WordPress 6.9 and later lets people leave notes on blocks in the block
editor, the way you might leave a comment in a Word document.

- **View > Block Notes...** lists them, each read as a sentence, such as
  "Sam on the second paragraph: tighten this". **Go to It** takes you to the
  block. **Reply** answers the note, and **Resolve** marks it done.
- **Insert > Note on This Block...** leaves a note of your own on the block
  the caret is in.

On a site older than 6.9 these commands say the site does not offer notes.
In a Markdown document, a block with a note becomes a protected line, and
QUILL asks before adding one.

## Links inside a page

- **Insert > Link to a Page on This Site...** lists your site's published
  pages and posts. Choose one and the link goes in at the caret, worded with
  the text you selected, or the page's title when nothing is selected. It is
  written as a Markdown or HTML link to match your document.
- **Edit > WordPress > Hear Where a Link Goes.** With the caret on a link,
  QUILL asks your site to look at the page and reads you its title and
  description. With no link there, type an address: QUILL tells you what is
  there, so a typo is caught before the link goes in, and offers to insert
  it with the page's own title as the words.
- **Edit > WordPress > Fix Link Text...** lists every "click here" or "read
  more" link in the page, with the title of the page it goes to. Choose
  **Use the Page's Title** for one, or **Use All Titles**, and the links say
  where they go.

## Icons

**Insert > WordPress Icon...** lists your site's icons by name, on WordPress
7.0 and later. Give the icon a label that says what it means, such as "Phone
us", or insert it as decorative so screen readers skip it. An icon is never
left unnamed: an empty label inserts nothing.

## A walk-through: adding a booking button under a paragraph

1. Open the page in Markdown and put the caret in the paragraph the button
   should follow.
2. Choose **Insert > WordPress Block...**, type `button` in Find and press
   Enter.
3. Choose Button and press Insert.
4. Type the button's text, "Book a session", and its link. Press OK.
5. You hear "Button inserted." Arrow down and you read
   `::: button "Book a session" https://example.org/book`.
6. Choose **Edit > WordPress > Where Am I** to confirm where it landed.
7. Choose **View > Preview Blocks** to hear the site draw it, then **Save
   Draft to Site**.

## Where to next

- Previous: [Chapter 2: Writing and publishing posts and pages](wordpress-forms-02-writing-and-publishing.html)
- Next: [Chapter 4: Pictures and the Media Library](wordpress-forms-04-pictures-and-media.html)
- [Contents](wordpress-forms-guide.html)
