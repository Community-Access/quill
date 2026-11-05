# Chapter 2: Writing and publishing posts and pages

## What this chapter covers

This chapter is the everyday work: starting a post or a page, opening one
that is already on your site, saving it on your computer, sending it as a
draft, publishing it, and scheduling it for later. It also covers what QUILL
does when someone else changed the page while you were working, what
happens when the connection drops, and how to get an earlier version back.
It ends with the Send and Copy commands, which move writing between
documents and sites.

## Posts and pages

WordPress has two kinds of writing, and QUILL keeps them apart the way
WordPress does:

- **A post** is dated. It goes in your blog or news list, newest first, and
  can have categories and tags. A weekly news item is a post.
- **A page** stays put. It is not dated and has no categories. About,
  Contact and Opening Hours are pages. Pages can sit under other pages, which
  is how a site builds its structure.

Many sites have their own kinds as well, such as events or recipes, added by
a plugin or the theme. QUILL's Open window lists those beside Posts and
Pages.

## Writing something new

1. Choose **File > WordPress > New Post...** or **File > WordPress > New
   Page...**. The window opens on **Site**, with your default site chosen.
2. Tab to **Title** and type it. The title is what visitors see at the top
   of the page and in lists.
3. Tab to **Slug**. It has filled itself in from the title as you typed: the
   slug is the last part of the page's web address, so "Spring Workshop"
   becomes `spring-workshop`. Leave it alone to keep it, or type your own.
4. Choose **Markdown** or **HTML** under **Write in**.
5. For a post, check the **Categories** and **Tags** it belongs to. Space
   checks or unchecks each one.
6. Press **Create**.

You hear "New post for" your site's name, and that nothing is sent until you
choose Save Draft to Site or Publish. The new document opens, empty, ready
for your first paragraph.

**Markdown or HTML?** Markdown is the easier one to write by ear. Two number
signs and a space start a heading, a dash and a space start a bullet, and
QUILL turns it into what WordPress needs when you send it. HTML gives you
exact control, and is right if you already think in tags. You cannot switch
a document between the two later. That is deliberate: a document that
started as Markdown is never quietly read as HTML, so nothing on your page
is ever reinterpreted. QUILL remembers your last choice for next time.

**Do not repeat the title as a heading.** Your theme already shows the title
at the top of the page as its main heading. Start straight in with your
first paragraph, and use Heading 2 for the sections inside. Check Before
Publishing points it out if you forget.

**Everything else is in Properties.** The excerpt, the featured image,
whether comments are open and the rest are not asked up front. They are in
**File > WordPress > Properties...**, described later in this chapter.

## Opening what is already there

**File > WordPress > Open Page or Post...** asks which site, then which kind:
Posts, Pages, or any kind your site adds, such as Events. Then the Open
window lists everything of that kind, newest change first. Each row says the
title, its status (published, draft, pending review, scheduled, private or
in the Trash) and when it last changed, for example "Opening Hours,
published, yesterday".

- **Find by title or status** narrows the list. Type part of a title and
  press Enter. Type a status, such as `draft`, `pending`, `private` or
  `trash`, to see only those.
- **Enter**, or the **Open** button, opens the row you are on.
- **Move to Trash...** and **Restore from Trash** are in the same window.

When you open a page, QUILL asks how you want to see it:

- **HTML** shows it exactly as the site has it, block markers and all.
- **Markdown** is easier to read and edit. Ordinary paragraphs, headings,
  lists and pictures become plain Markdown, other blocks become short `:::`
  lines, and anything Markdown cannot show, such as a plugin's contact form,
  sits on one short protected line. Chapter 3 explains these.

Either way, nothing on the site changes by being opened. A block you did not
touch goes back exactly as it came, byte for byte.

You hear "Opened Opening Hours from Community Radio." If you already had a
working copy of that page on this computer, QUILL opens your copy rather
than a second one.

**An unsaved version.** If the page has an autosave newer than the copy on
the site, from a browser or from QUILL, QUILL asks first: "There is an
unsaved version from yesterday, 4:12 PM. Open that instead?" Choose which
one you want.

### Opening a page from its web address

**File > WordPress > Open by Web Address...** is the quickest route when
someone sends you a link to the page that needs fixing.

1. Copy the page's address, from an email or from your browser's address
   bar.
2. Choose Open by Web Address. QUILL has already picked the address up from
   the clipboard.
3. Press Enter.

QUILL works out which of your sites the address belongs to, even if it is
not your default. It understands an ordinary address such as
`https://example.org/opening-hours/`, and the short forms WordPress uses,
such as `?p=42` and `?page_id=7`. If the page is already open, QUILL takes
you to it instead of opening a second copy.

### Your local drafts

**File > WordPress > Open Local Draft...** lists everything you have written
for any of your sites that is saved on this computer, with the site each one
belongs to. It is where a new post you started yesterday is waiting, and
where QUILL Cast, QUILL Studio and Quill Converter leave the drafts they make
for you (Chapter 4).

## The three ways to save

There are three kinds of save, and they are deliberately separate:

| Command | What happens |
|---|---|
| Ctrl+S | Saves on this computer. Nothing is sent. |
| Save Draft to Site | Sends an unpublished draft. Visitors cannot see it. |
| Publish or Update... | Publishes it, or updates the published page, after you confirm. |

Both of the last two are in **File > WordPress**. Closing a WordPress
document never publishes it, and never sends anything.

### Save Draft to Site

Save Draft to Site puts your writing on the site where only you and the
site's editors can see it. It is the safe way to try it in the site's own
preview before anybody else reads it. You hear "Draft saved to Community
Radio. It is not public."

If you put pictures in from your computer, they are uploaded now, and their
addresses are swapped into your page.

### Publish or Update

1. Choose **File > WordPress > Publish or Update...**.
2. QUILL runs Check Before Publishing on the page, then asks. The question
   names the title and the site, such as "Publish on Community Radio:
   Spring Workshop", and says what the check found: "Ready to publish: no
   problems found", or, for example, "2 things to look at: 1 problem, 1 to
   check".
3. Read the findings if there are any. None of them stop you. Choose
   **Publish**, or **Publish Anyway** when there are findings, or Escape to
   go back and fix them.

You hear "Published on Community Radio. The address is on the clipboard."
The page's web address is ready to paste into an email.

A page that is already published says Update rather than Publish. A private
or scheduled page keeps that status when you update it.

**Open on Site** (in File > WordPress) opens the page in your browser, so
you can hear it the way a visitor will. **Copy Address** puts its address on
the clipboard again later. A draft's address only opens for someone signed
in to WordPress, and QUILL says so when it copies one: "Draft address
copied. It needs a WordPress sign-in to open."

**A new page is not in your menus yet.** WordPress does not add a new page
to the site's navigation by itself. The first time a page is published,
QUILL asks "Add it to a menu?" with three answers: **Yes, open Menus**, which
opens the Menus window with the page added at the end; **Not this time**;
and **No, and stop asking** for that site.

**If you are a Contributor,** the command is called Submit for Review, and
your post goes to the site as pending review for an Editor to publish.

## When someone else changed it first

Before every update, QUILL asks the site when the page last changed. If
someone changed it after you opened it, perhaps a colleague in the block
editor, QUILL will not overwrite their work. Nothing is sent. Instead you
hear who changed it and when, and get three choices:

- **Compare the two** shows the lines that differ, each starting "Site:" for
  the site's copy or "Yours:" for yours.
- **Open the site's copy** opens their version, so you can copy your change
  into it.
- **Send mine anyway** replaces their version with yours. It asks once more
  before it does, and the site's copy is kept in Previous Versions first, so
  even then nothing is lost.

## Scheduling a post

To publish later, open the page or post and choose **File > WordPress >
Schedule Publish...**.

1. Type the date, such as `2026-11-20`.
2. Type the time, such as `16:15` or `4:15 PM`.
3. Pick the time zone. Your site's own time zone is at the top of the list.
4. Press OK.

QUILL reads the date and time back to you with the site's name before
anything is sent. If the time is in the past, or is not one QUILL can read,
the window opens again with the problem at the top.

The page then shows as scheduled in Open. To move it, or publish it straight
away, open it and choose Schedule Publish again. You get two choices:
**Change the schedule** or **Publish now**.

**Tools > WordPress > Your Sites > Coming Up...** lists everything scheduled
on all your sites, soonest first.

## Autosaves, and when the connection drops

**Autosaves.** While a WordPress document is open, QUILL keeps an autosave
every two minutes whenever the text has changed: on this computer, and, once
the page is on the site, as your account's autosave there too. It is the
same autosave the WordPress editor keeps, so if your computer dies, the
words are safe on the site. You hear nothing when it works. If it stops
working, QUILL tells you once.

**When a send gets no answer.** Your copy stays on this computer, and QUILL
asks the site what happened before doing anything else, so nothing is ever
created twice. If the page did arrive, you hear the usual result. If it did
not, QUILL offers **Try Again**.

**When the site cannot be reached at all,** the send waits in a queue. You
hear, for example, "Community Radio cannot be reached, so 'Hours' is
queued." QUILL tries again every two minutes and tells you when it goes
through: "Back online: 2 drafts sent to Community Radio." A queued publish
is never sent over somebody else's newer change: QUILL checks first, and if
the site's copy changed, it tells you and sends nothing.

A schedule is never queued. It is a time you chose, and sending it late
could be worse than not sending it, so QUILL tells you it failed instead.

## Properties

**File > WordPress > Properties...** holds everything about the page apart
from its words:

- **About:** the site, the address, the author and when it last changed, to
  read;
- **Title**, **Slug** and **Status**;
- **Excerpt:** the short summary some themes show in lists;
- **Categories** and **Tags**, for a post, as separate check boxes;
- **Allow comments**;
- **Keep at the top of the blog**, for a post;
- **Password to read it**, optional: visitors must type it to read the page;
- the reading level, such as "about 9th grade, 14 words per sentence",
  worked out on this computer;
- any custom fields your site keeps for the page, and the fields of the
  plugins QUILL recognises (Chapter 7).

Changes are kept with your copy and go to the site the next time you send
it.

**File > WordPress > Custom Fields...** shows just the extra fields your
site's plugins and theme keep for a page, such as an SEO title or an event
date. **File > WordPress > Plugin Fields...** changes the fields of The
Events Calendar, WooCommerce, Yoast SEO and Rank Math, where your site has
them.

## Previous versions, and comparing

**File > WordPress > Previous Versions...** lists earlier versions, newest
first. Each row says when it was kept and why, such as "Opened from site",
"Saved", "Site copy before update" or "Before restore". The site's own
history is in the same list, marked "On the site", so this is a true
history, not just what QUILL happened to keep.

- **View...** shows a whole version, title first, in a window you can read
  and copy from, so you can take back one paragraph without the rest.
- **Restore** puts that version in the editor. It never publishes by
  itself. You hear "Version put in the editor. Nothing was sent; your text
  before is in Previous Versions."

**File > WordPress > Compare with Site** shows the lines that differ between
your copy and the site's, starting with a count such as "3 lines only on
Community Radio, 1 only in yours."

## The Trash

**File > WordPress > Move to Trash...** moves the page to WordPress's Trash,
after naming it and the site. It is not deleted, and a copy stays on your
computer.

**To bring one back,** choose **File > WordPress > Open Page or Post...**,
type `trash` in Find, press Enter, and press **Restore from Trash** on the
row. You hear "'Hours' is back on Community Radio as a draft. Open it to
publish it again."

## Send and Copy

**File > WordPress > Send and Copy** moves writing between your documents
and your sites:

- **Send This Document to WordPress...** turns any document open in QUILL
  into a new draft. Its first heading becomes the title, its headings stay
  headings, and its pictures go to the Media Library.
- **Publish to Another Site...** copies the page you are editing to another
  of your sites, as a draft there. Pictures are uploaded again. Categories
  and tags are matched by name, and QUILL asks before creating any that are
  missing.
- **Duplicate...** makes a new draft from any page or post, on the same site
  or another, with everything but the date and status. On the same site, the
  copy's title ends "(copy)".
- **Send a Folder as Drafts...** turns a folder of Markdown or text files
  into drafts in one go. Each file is checked first, and one question tells
  you how many are going and how many have something to look at.
- **Download My Writing...** saves every page and post to a folder as
  Markdown, with the pictures and a contents page called `index.md`. Run it
  again later and only what changed is fetched.

## A walk-through: fixing one sentence someone sent you

A volunteer emails you a link: the opening hours on your site are wrong.

1. Copy the link from the email.
2. Choose **File > WordPress > Open by Web Address...** and press Enter.
3. QUILL asks Open as. Choose Markdown. You hear "Opened Opening Hours from
   Community Radio."
4. Use Find to get to the wrong sentence, and fix it.
5. Choose **File > WordPress > Publish or Update...**. You hear "Update on
   Community Radio" and what the check found.
6. Choose Publish. You hear "Published on Community Radio. The address is on
   the clipboard."
7. Paste the address into your reply to the volunteer.

The guided lesson Open a page by its address and fix a sentence, in **Help >
Tutorials**, walks through the same thing on a test site.

## Where to next

- Previous: [Chapter 1: Getting started and adding your sites](wordpress-forms-01-getting-started.html)
- Next: [Chapter 3: Blocks made plain](wordpress-forms-03-blocks.html)
- [Contents](wordpress-forms-guide.html)
