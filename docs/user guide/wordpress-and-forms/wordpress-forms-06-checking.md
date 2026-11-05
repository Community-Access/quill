# Chapter 6: Checking before you publish

## What this chapter covers

QUILL checks your writing for the things that make a page hard to use,
before visitors find them. This chapter covers the quick check that runs
every time you publish, the deeper check of a published page the way a
visitor gets it, the check of a whole site with fixes you can make in bulk
and undo, colour contrast, reading level, marking another language, and
writing an accessibility statement. None of these checks needs AI, and none
of them ever stops you publishing.

## Check Before Publishing

**Tools > WordPress > Check Before Publishing...** checks the page in front
of you, on this computer, in a moment. It is the same check Publish or
Update runs for you before it asks.

You hear a summary first: "Ready to publish: no problems found", or, for
example, "3 things to look at: 2 problems, 1 to check". A **problem** is
something that gets in a visitor's way. A thing **to check** may be fine, and
needs your judgement.

Then the list opens, one finding a line, each with its reason. Press Enter
or **Go to It** on a finding to put the caret on the line it is about.

### What it looks for

Pictures:

- a picture with no alternative text;
- a picture with empty alternative text that is not marked decorative;
- alternative text that is a file name, such as `IMG_2041.jpg`;
- alternative text that starts by saying it is an image (to check);
- a linked picture with no alternative text, so the link has no name;
- a GIF, which may move (to check);
- a video that plays by itself when the page opens.

Links:

- a link with no text;
- a link whose text is its web address, which a screen reader spells out;
- vague link text such as "click here" or "read more";
- a link that opens a new tab without saying so (to check);
- an emoji or symbol in a link, which a screen reader reads out by name (to
  check).

Headings and structure:

- a Heading 1 in the body, when the theme already shows the title as one;
- a heading that skips a level, such as Heading 2 to Heading 4;
- an emoji or symbol in a heading (to check);
- a table with no header row, so its cells cannot be read with their
  headings;
- a table with no caption (to check);
- words that rely on colour alone, such as "the items in red" (to check).

The page itself:

- a page with no title;
- a block fence QUILL could not understand, named with its line;
- a page going to a site that is not your default (to check), so you never
  publish to the wrong one by accident.

### A walk-through: clearing a page's findings

1. Open the page and choose **Tools > WordPress > Check Before
   Publishing...**. You hear how many things there are to look at.
2. Arrow to the first finding and press Enter. The caret is on the line.
3. Fix it, such as by giving a picture alternative text in Alt Text Review,
   or changing "click here" to the name of the page.
4. Run the check again. One fewer each time, until you hear "Ready to
   publish: no problems found".

The guided lesson Check Before Publishing, in **Help > Tutorials**, uses a
test post with one problem of each kind.

## Check This Page, the way a visitor gets it

Check Before Publishing looks at your words. A visitor gets your words plus
the theme, the menus, the header and the footer around them. **Tools >
WordPress > Check This Page** checks all of that.

QUILL opens the published page in a hidden copy of Microsoft Edge, or
Chrome, and checks it with axe-core, the same checker web developers use. It
is built into QUILL, so nothing is downloaded. No AI is involved. If you
have no WordPress page open, it checks your site's home page. For a draft,
use Check Before Publishing instead, because a draft cannot be opened
without a sign-in.

You hear one line first, such as "Community Radio, Schedule: 3 problems, 1
to check". Then a list opens with one row for each kind of problem. Each row
says how many places have it, whether it is in your content or in the
theme, and who it affects.

- **Explain** gives the WCAG rule by number and name, and why it matters.
- **Go to It** takes you to that place in your document, when the problem
  is in your own writing.
- **Write a Note for the Theme Author** makes a plain report of a theme
  problem, ready to paste into a support forum or an email. A problem in the
  theme is not yours to fix in a page, but it is worth reporting.
- **Page Shape** tells you how a screen reader meets the page: its
  landmarks, every heading including the theme's own, and how many links
  and buttons there are.
- **Dead Links** lists the links in your page that go nowhere. The summary
  line says how many there are.

## Check the Whole Site

**Tools > WordPress > Check the Whole Site...** checks every published page
and post. It asks first whether to check just your content, which is fast,
or the visitor's view as well, which is slower and tells you how far it has
got.

The report groups problems, most common first, such as "Images with no alt
text: 41, on 17 pages". **Pages** lists the pages with that problem, so you
can open one. QUILL remembers each run, so next time it tells you how the
count compares with last time.

### Fix in Bulk

In the report, **Fix in Bulk** is offered for the problems QUILL can fix
without your words:

- links that open a new tab get "(opens in a new tab)";
- videos stop playing by themselves;
- alternative text loses a leading "Image of";
- a Heading 1 in the body becomes a Heading 2.

You see every change first. Then one confirmation names your site and the
number of pages. QUILL keeps a copy of each page as it was, on your
computer, before it changes anything.

### Undo Site Fix

**Tools > WordPress > Undo Site Fix...** lists the bulk fixes you have made,
and puts the pages back. A page someone has changed since is left alone,
and QUILL tells you which, so nobody's later work is lost.

## Site-wide Find and Replace

**Tools > WordPress > Site-wide Find and Replace...** changes words across
every page and post, such as a phone number that changed or a person who
has left.

1. Type what to find and what to replace it with.
2. QUILL lists every match in its sentence. Check the ones to include.
3. One confirmation names the site and the number of pages.

Undo Site Fix can put it all back. Block settings are left alone unless you
choose **Include Block Settings**.

## Colours that pass, and say so

Text needs enough contrast with what it sits on to be read by people with
low vision. WCAG asks for 4.5 to 1 for ordinary text and 3 to 1 for large
text.

- **Tools > WordPress > Palette Report** lists every colour in your theme
  against every background, with its contrast, and whether it is strong
  enough for text.
- **Block Settings** (Chapter 3) and **Site Styles** (Chapter 7) say the
  contrast of every colour as you choose it, such as "Accent (dark green),
  7.4 to 1, passes".

## Reading level

**File > WordPress > Properties...** shows the page's reading level, such as
"about 9th grade, 14 words per sentence". It is worked out on this computer,
and nothing is sent. Long sentences are the commonest reason a page reads
as harder than it needs to.

## Marking another language

**Format > WordPress > Mark Language...** marks the selected words as
another language, such as a French quotation in an English post, so a
visitor's screen reader switches to a French voice for them. Type a name
such as French, or a code such as `fr`. With nothing selected, it marks the
whole page.

Your site's own language matters too, for the same reason. It is in **Site
Settings** (Chapter 7).

## In Short

**Tools > WordPress > In Short...** asks your AI for a two- or
three-sentence summary and puts it at the top of the page as an "In short"
paragraph for you to edit. Readers who find long pages hard, and readers in
a hurry, both thank you for it. Ctrl+Z takes it out.

## An accessibility statement

**Tools > WordPress > Write an Accessibility Statement...** opens a new page
draft saying you aim for WCAG 2.2 AA, when you last checked the site and
what it found, and how to reach you about a problem. It is yours to edit,
and nothing goes to the site until you send it.

## Where to next

- Previous: [Chapter 5: Comments, categories, tags and menus](wordpress-forms-05-comments-categories-menus.html)
- Next: [Chapter 7: Running your site](wordpress-forms-07-running-your-site.html)
- [Contents](wordpress-forms-guide.html)
