# Chapter 2: A tour of the WordPress Workbench

## What this chapter covers

You write in the editor. You look after your sites in the WordPress
Workbench. It is one window for every site you have connected, and most of
this manual happens in it, so it is worth ten minutes to learn how it moves.

In this chapter you open the Workbench, find your way round its tree, read a
list, open Properties, use the context menu, and change something safely. You
also meet Needs My Attention, the filter, the status bar and F1.

By the end you will know where everything lives, how QUILL asks before it
changes your site, and how to take a change back.

## Opening the Workbench

There are three ways in:

- Choose **Tools > WordPress > Open WordPress Workbench...**.
- Press the WordPress key, Ctrl+Alt+Shift+Grave, then H.
- Choose any of the site rows of Tools > WordPress, such as **Comments...**,
  **Media Library...**, **Categories and Tags...**, **Menus...**, **Site
  Settings...** or **Site Check**. Each opens the Workbench at its own place.
  The same goes for Users, Application Passwords, Plugins, Themes, Fonts,
  Synced Patterns, Widgets, Site Map and AI Abilities in Tools > WordPress >
  Manage.

Two more start from the page you are writing:

- **File > WordPress > This Post in the Workbench** (the WordPress key, then
  Shift+H) opens the list your post is in, with your post selected.
- **Insert > Picture from the Media Library...** opens your site's Media,
  ready for you to pick a picture. Chapter 5 shows how.

The Workbench is a window of its own. The editor stays open behind it.
**Window > Switch to Editor** (`Ctrl+Shift+E`) brings the editor forward, and
closing the Workbench with Alt+F4 leaves the editor as it was.

## The five panes

The window has five parts, in this order:

1. **The tree**, on the left, says where you are.
2. **The filter box** narrows the list.
3. **The list** shows what is in the place you chose.
4. **The details** say more about the row you are on.
5. **The status bar** says which site and role you are using.

F6 moves to the next part, and Shift+F6 to the one before. **View > Where Am
I** (`Alt+1`) says the place and the filter in effect. **View > Say
Selection** (`Alt+2`) says how many rows you have selected.

## Finding your way round the tree

The tree works like any tree view. Up and Down Arrow move, Right Arrow opens a
branch and Left Arrow closes it. When you arrive on a place, its list loads
by itself.

At the top of the tree:

- **Start Here** says what the Workbench is and how to move round it.
- **Needs My Attention** gathers what waits on you, from every site at once.
- **Sites** has a branch for each site you have connected.
- **Calendar** lists every site's content a day at a time.
- **Across Sites** shows the same tag, plugin, person or setting on all your
  sites together.
- **Search** searches every site at once.
- **Practice Site** is a WordPress site on your own computer, for learning
  with nothing at stake.
- **Help and Learning** has How WordPress Thinks, Words and Keys.

Open a site under Sites and you find its Overview first, then Posts, Pages,
Media, Comments, Categories, Tags, Menus and Navigation, Appearance, Forms,
People, Plugins, Settings, Site Health and more. A site that runs a plugin
QUILL knows, such as WooCommerce, also has that plugin's places. If a site
has its own kinds of content, such as Events, they are under More Content
Types.

**Jumping straight there.** The Go menu takes you to the places you use most:

- **Go > Needs My Attention** (`Ctrl+1`) and **Go > Current Site** (`Ctrl+2`);
- **Go > Posts** (`Ctrl+Shift+1`), **Go > Pages** (`Ctrl+Shift+2`), **Go >
  Media** (`Ctrl+Shift+3`) and **Go > Comments** (`Ctrl+Shift+4`) for the
  site you are on, and so on up to **Go > Site Health** (`Ctrl+Shift+9`);
- **Go > Across Sites** (`Ctrl+0`), **Go > Calendar** (`Ctrl+3`), **Go >
  Watches** (`Ctrl+5`), **Go > Practice Site** (`Ctrl+6`) and **Go > Start
  Here** (`Ctrl+9`);
- **Go > Parent Node** (`Alt+Up`) goes up one level.

**View > Back** (`Alt+Left`, or Backspace) and **View > Forward**
(`Alt+Right`) work like a web browser's.

## Reading a list

Each row of a list is one thing: a post, a picture, a comment, a person. The
columns say the most useful facts about it, and the details pane says the
rest. Arrow to a row and read it, or Tab to the details.

- **Enter** does the row's main job. On a post or page it opens it in the
  editor. On a comment it reads it in full. On a file in Media it opens the
  file in your browser.
- **Shift+Enter** opens the row on the site, in your browser, and
  **Ctrl+Enter** previews it there.
- **Edit > Copy Link** (`Ctrl+Shift+C`) puts its address on the clipboard.

A long list loads in pages. **View > Load More** (`Ctrl+Shift+L`) reads three
hundred more rows, and **View > Load All** (`Ctrl+Alt+L`) reads them all.
**View > Columns...** (`Ctrl+Alt+C`) chooses the columns. **View > Group
By...** (`Ctrl+Alt+G`) makes a small branch for each value of a column, such
as one for each author. **View > Refresh** (`F5`) reads the list again from
the site.

You can select several rows at once, the way you would in any Windows list.
Most commands then act on all of them, and tell you how each one went.

## The filter

The filter box sits above the list. **Edit > Filter...** (`Ctrl+E`) takes you
there.

Type words and press Enter to search the whole site, not only the rows you
can see. You can also type qualifiers, such as `status:draft`,
`category:news`, `-tag:old`, `after:2026-01-01` or `modified:>2026-10-01`.
Escape clears the filter.

Some help if you would rather not type them:

- **Edit > Filter Builder...** (`Ctrl+Shift+F`) builds a filter from the
  list's own columns and values.
- **Edit > Show Only Like This...** (`Ctrl+Alt+O`) keeps rows like the one you
  are on, by a column you choose, and **Edit > Hide Like This...**
  (`Ctrl+Alt+H`) hides them.
- **Edit > Only Mine** (`Ctrl+Alt+M`) shows only what you wrote, and pressing
  it again shows everything.

**Searching every site.** Choose **Search** in the tree, then type words in
the filter box and press Enter. Each result names its site and its kind of
content, and Enter opens it in your browser. If one site cannot answer, its
error sits beside the other results, and a big search says when more matches
remain.

A few lists, such as plugins and settings, cannot be searched on the site.
They are filtered here, on the rows already loaded, and the status bar says
so.

## Properties

**Item > Properties...** (`Alt+Enter`) shows everything about the selected
row on one sheet: a post's title, status, author, categories, featured image
and the rest, or a picture's alternative text and caption. Change what you
like and press OK, or Apply to save and keep the sheet open.

Select several rows and Properties changes them all at once. A field where
they differ says "Mixed", and stays as it is unless you change it.

A field you cannot change is still there to read, and F1 on it says why.

When a site's plugins keep extra fields for a category, a person or a
comment, Properties shows them on a **Custom Fields** page. A field that
holds a list or a group is a labelled box of JSON text, and QUILL checks it
before it saves. A field the site does not describe is read only.

Beside a list, such as a schedule's speakers, is an **Edit List...** button.
It opens the list on its own: Add, Edit, Remove, Move Up and Move Down, then
Keep Changes. Beside a group, such as a venue's address, **Edit Group...**
opens it as a form with one box for each part. These are the same windows
the editor's Custom Fields uses. What you keep goes back into the box, and
OK or Apply sends it. Parts of a group the site does not describe are kept
as they were. A list inside a list has no button and stays as JSON.

Field plugins get a page of their own, each only when the site has it:

- **Advanced Custom Fields**, for field groups with Show in REST API on.
- **Meta Box**, through its MB REST API extension. When Meta Box does not
  say what kind of value a field holds, QUILL goes by the value it holds now,
  so a number stays a number. A field whose value says nothing, such as an
  empty list, is read only.
- **Pods**, with the fields the pod shows in REST. A field the pod does not
  let you write over REST is read only, and F1 says so. Relationship and
  file fields are read only too. Pods only tells an administrator which
  fields are its own, so other roles see no Pods page.
- **CMB2**, with every box that applies. Each field is saved on its own and
  read back, so you hear about any the site did not keep. A box the site
  shows for reading only stays read only.

Every one of them is checked before it is sent and checked again after, and
Ctrl+Z puts them all back.

**Site > Site Properties...** (`Alt+Shift+Enter`) is the same sheet for the
whole site.

## The context menu and the Item menu

Every row has a context menu. Press the Applications key, or Shift+F10. It
lists everything you can do to that kind of row, with the main job first and
Properties last. The **Item** menu in the menu bar holds the same commands
that have keys.

A command your role cannot use is dimmed. Choose it by its key anyway and you
hear why, for example "Publishing pages needs the Editor role or higher. You
are an Author on Community Radio." **Site > What Can I Do Here?**
(`Shift+F1`) lists everything on the current place, and what each one needs.

The tree has a context menu too. On any place in a site it has **wp-admin for
This Place...**, which offers the wp-admin screens nearest to that place, for
the jobs WordPress only does there.

## How QUILL asks before it changes your site

Reading never changes anything. Before anything that changes a site, QUILL
shows you a preview: one line for each thing that will change, with the site
named at the top. Nothing goes until you press the button that names the
change, such as **Publish**, **Add** or **Import as Drafts**. Escape, or
Cancel, sends nothing.

Then:

- **QUILL reads it again first.** If somebody changed the item on the site
  since your list loaded, nothing is sent, and you are told what changed.
  Press F5 and try again.
- **QUILL checks afterwards.** It reads the item back, and tells you if the
  site did not keep something.
- **A permanent change says so.** Deleting for good, a refund, or a change
  WordPress keeps no copy of, says in its preview that it cannot be undone,
  and Delete Permanently asks you to confirm by name. These previews start
  on Cancel, so pressing Enter by habit does nothing. Tab to the action
  button to go ahead.

**New Here.** **File > New Here...** (`Ctrl+N`) makes a new thing of the kind
you are looking at: a post in Posts, a category in Categories, a person in
Users, a coupon in Coupons. It asks what it needs, then shows the preview.

## Taking a change back

**Edit > Undo WordPress Change** (`Ctrl+Z`) puts back the last change you made
in the Workbench, wherever putting the old values back really restores it.
Press it again for the change before. Each one says what it put back.

Some changes cannot be taken back, such as a reply that has already gone or
a trash that was emptied. When Ctrl+Z reaches one, it says so and steps past
it. Press Ctrl+Z again to undo the change before it.

**Edit > Change History...** (`Ctrl+Shift+H`) lists every change you made in
this window, newest first, including the ones that cannot be undone. It marks
the one Ctrl+Z will undo next.

**Item > Move to Trash** (`Delete`) sends posts, pages and comments to
WordPress's own Trash, and **Item > Restore from Trash** (`Ctrl+Shift+R`)
brings them back. The Media Library has no Trash in WordPress, so a picture
or a file is deleted for good with **Item > Delete Permanently...**
(`Shift+Delete`). If you want a copy first, use **Download...** on its
context menu.

Delete, Shift+Delete and Ctrl+Z only act on the list. In the filter box, or
in any other box you type in, they edit your text as usual.

## Needs My Attention

**Needs My Attention** (`Ctrl+1`) is the place to start the day. It gathers
from every site:

- **Inbox**: everything below, newest first;
- **Comments Waiting**: comments held for you to approve;
- **Pending Review**: posts from people who cannot publish, waiting for an
  editor;
- **Scheduled**: what will publish itself, with its date;
- **Drafts**: your own drafts on every site;
- **Updates**: the version of WordPress, every plugin and every theme;
- **Site Health**: problems the sites report, worst first;
- **Accessibility**: pictures with no alternative text;
- **Broken Links**: dead links in a sample of each site's pages;
- **Held as Spam**: comments and form responses a site doubted;
- **Form Responses**: new responses to your forms;
- **Membership Orders**: orders waiting on a person, on sites with Paid
  Memberships Pro;
- **Watches**: what you asked the Workbench to keep an eye on.

Each row names its site. Act on it right there, as you would in the site's
own list.

## The status bar

The status bar has seven parts: the **Site** and **Your role** you are
working as, how many **Items** are shown, the **Filter** in effect, whether a
list is **Loading**, what is **Waiting**, and your **Workbench access** for
that site. F6 reaches it. Arrow along it, and press Enter on a part for the
action that goes with it, such as Clear Filter or Refresh.

**Workbench access** is a choice you make for each site, with **Site >
Workbench Access...** (`Ctrl+Alt+A`):

- **Full**, the default, lets you do everything your role allows;
- **Organize** allows reading, and the changes that are easy to undo, such as
  moderating comments and moving things to the Trash;
- **Read Only** allows reading only.

**Site > View As Role...** (`Ctrl+Alt+V`) shows the site as an Author, say,
would see it, and is read only while it is on. Safe Mode makes every site
read only too. The choice covers every command in the window: the context
menu, the menu bar, New Here, the imports, the REST Console, and Delete on
people and passwords. Commands it does not allow are dimmed, or say why
when you try them. Whatever you choose, WordPress still checks your own
account before it accepts anything.

The application password QUILL signs in with is never revoked from the
Workbench, at any level. Use Sign Out This Site for that.

## F1, and help for every place

**Help > Help for This View** (`F1`) says what the place or row under focus
is, and what you can do with it. Press it on the tree, the list, or any field
of Properties. **Site > Roles and What They May Do** (`Ctrl+Alt+R`) explains
each role on the site in plain words.

The Help menu has the rest of the help, each on its own key:

- **What Is This?** (`Alt+F1`) explains the WordPress word for the selected
  row, such as slug, sticky or synced pattern, with an example from your own
  site once the Workbench has read one.
- **WordPress Guide** (`Ctrl+F1`) opens this guide in your browser at the
  chapter for where you are.
- **Search Help...** (`Ctrl+Shift+F1`) finds places, commands, WordPress
  words and jobs from a few words you type. Enter goes there, runs it or
  reads it.
- **Workbench Keys** (`Alt+Shift+F1`) lists every key in the window.
- **Say Last Result Again** (`F9`) repeats what the Workbench last said, and
  **Explain That** (`Shift+F9`) says what it means and what you might do
  next.

**Help and Learning**, at the bottom of the tree, holds How WordPress Thinks,
Words (every WordPress word, each explained), Keys, and four more:

- **Do Something** lists common jobs in plain words, such as updating plugins
  safely or fixing a broken link. Enter reads the steps, and **Take Me There**
  goes to the place where the job is done.
- **The Guide** lists this guide's chapters. Enter opens one.
- **What Changed** says what is new in the Workbench.
- **Ask a Person** starts a message to support in your own email. The
  Workbench sends nothing and puts nothing of yours in it, so leave your
  passwords out of what you write too.

## A walk-through: your first five minutes

1. Press Ctrl+Alt+Shift+Grave, then H. The Workbench opens.
2. Press Ctrl+1 for Needs My Attention, then Down Arrow to Comments Waiting.
3. Tab to the list and arrow through the comments. Each row names the site.
4. On one you want to publish, press Ctrl+Shift+A to approve it.
5. Changed your mind? Press Ctrl+Z. It is waiting again.
6. Press Ctrl+2 for your site's Overview, then Right Arrow and Down Arrow to
   At a Glance, which says your site's counts in words.
7. Press Alt+F4. The editor is where you left it.

## Practising on a site of your own

The Practice Site is a real WordPress site that runs on your own computer,
so you can try anything here with nothing at stake. It comes with QUILL, and
needs no download.

1. Choose **Tools > Practice Site...** (`Ctrl+Alt+P`) in the Workbench, or
   press Ctrl+6 to go to its place in the tree.
2. Choose **Start the Practice Site**. The first start takes two or three
   minutes, while it unpacks WordPress and makes a welcome page, a sample
   post and a draft. Later starts take under a minute.
3. Choose Practice Site again, then **Connect It as Practice Site**. It joins
   your sites under Sites.

It answers only on this computer, at `http://127.0.0.1:9400`. That is the one
address QUILL will use without HTTPS. If something else on your computer is
using that port, QUILL says so before it starts anything.

When you are done, choose **Stop the Practice Site**. Closing the Workbench
stops it too.

**Reset the Practice Site**, offered while it is stopped, wipes it clean:
every post, page, upload, comment, person, plugin and setting on it is
deleted for good, and its connection is forgotten. It asks first. Your real sites are not touched. The
next start builds a fresh site.

If a command would change the Practice Site and a real site in one step,
such as Revoke Everywhere, QUILL asks you by name first, and the answer
starts on No.

### Lesson material, and Break It on Purpose

Once the Practice Site has been started, Practice Site also offers **Set Up
the Lesson Material**. It shows you everything it will add before it adds any
of it, and adds it to the Practice Site only: a picture with no alt text, a
post with a link to a page that is not there, two plugins that fight over the
same shortcode, a Contact Us page with a misspelt address, a spam comment and
a real one waiting, a menu, and a Practice Events content type with an Event
date field. **Take Away the Lesson Material** removes exactly those again,
even if you changed them, and leaves everything else. Setting it up goes into
Change History, so undoing it there takes it away too.

### The Practice Site lessons

**Help > Tutorials** has these lessons in both QUILL and QUILL Lite, because
both open the same Workbench. They all work on the Practice Site and never send
anything to a real site.

The WordPress Workbench, on the Practice Site:

- Start the Practice Site
- Change a practice post, then undo it
- Reset the Practice Site
- Look after a site
- Change a menu, then put it back
- Add a person and choose their role
- Update plugins safely
- Spam, real comments, and challenges
- Custom types and their fields
- From staging to live, without surprises
- Across sites with a Site Set

Break It on Purpose, on the Practice Site:

- Set up the broken Practice Site
- Fix a picture with no alt text
- Fix a broken link
- Fix a plugin conflict
- Fix a wrong address

In QUILL, a lesson notices when you have made the fix, because it watches the
Workbench for a change on the Practice Site, and moves you on. In QUILL Lite
you move on yourself.

Start Here, at the top of the Workbench's tree, points to these and to Your
first week with a site, the seven short lessons for a new site owner.

## Where to next

- Previous: [Chapter 1: Getting started and adding your sites](wordpress-forms-01-getting-started.html)
- Next: [Chapter 3: Writing and publishing posts and pages](wordpress-forms-03-writing-and-publishing.html)
- [Contents](wordpress-forms-guide.html)
