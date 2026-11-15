# Chapter 9: Moving and copying content

## What this chapter covers

Sooner or later you need your content somewhere else: on a new host, on a
second site, in a spreadsheet, or safe on your own computer before a big
change. Or you need the same change on many pages, or on all your sites.
This chapter is about all of that.

You will export a site as a WordPress export file and import one as drafts,
copy posts and more to another of your sites, compare two sites, and take a
snapshot and put it back. Then you will change a name everywhere it is used,
make your sites agree with each other, and move lists in and out of
spreadsheets.

By the end you can move content between sites with a preview at every step,
and nothing published by surprise.

Everything here is in the WordPress Workbench. Chapter 2 explains how it
moves.

## Exporting a site as a WXR file

A WXR file is WordPress's own export format, the file wp-admin makes under
Tools > Export. Any WordPress site can import it. Use it when you move to a
new host, or want a copy of your writing that is not tied to QUILL.

1. In the Workbench, select the site you want, or anything on it.
2. Choose **Tools > WXR Files > Export Site as WXR...**. The keys are Alt+T,
   then W, then E.
3. Under **Export**, choose what goes in the file:
   - **Everything: posts, pages, patterns, other types, files, menus,
     comments**;
   - **Posts only**;
   - **Pages only**;
   - **Posts and pages in a date range...**, which asks for a **From** and a
     **To** day, written as year-month-day such as `2026-01-31`. Leave From
     empty to start at the first post, or To empty to end today. Both days
     are included;
   - **Posts in one category...**, which lists the site's categories, each
     with how many posts it has.
4. Choose where to save the file. QUILL adds `.xml` if you leave it off.

QUILL reads the site and writes the file on this computer. A part of the site
takes only the people, categories, tags and files its posts use, the same as
WordPress's own exporter. Comments and menus go only with Everything.

When it is done you hear how many of each kind went in, such as posts,
pages, authors, terms and attachments, and whether the finished file passed
its check. QUILL reads the file back to make sure it is a proper WXR file,
such as "community-radio.xml is a well-formed WXR 1.2 file with 181 items."
If it does not pass, the file is kept so you can look at it.

A report then opens. It names the site and what you chose, what went in, the
result of the check, and then what was left out and why. Some things only
WordPress's own exporter can carry, such as custom fields the site keeps
private, comment, term and user details, post passwords, and plugin
settings. Lists and groups in custom fields are written as text.

The file holds the address of each picture and file, not the files
themselves, the same as a WXR from wp-admin. Keep the old site running until
the new one has imported them.

## Importing a WXR file as drafts

This brings content from any WordPress site into one of yours. Everything
arrives as a draft, so nothing is published until you say so.

1. In the Workbench, select the site you are importing into, or anything on
   it.
2. Choose **Tools > WXR Files > Import WXR as Drafts...** (Alt+T, then W, then
   I).
3. Choose the WXR file.

QUILL reads the file on this computer and matches it against your site:

- **People.** Each author in the file is matched to a person on your site by
  their username, then by their email. If some have no match, QUILL asks
  **Give unmatched authors' items to:** and lists your site's people, with
  you chosen. The question names who did not match.
- **Categories, tags and other groupings** are matched by their slug, and
  made where missing. Groupings your site does not have are left out, and
  named.
- **Posts, pages, synced patterns and your site's own kinds** come in, if
  your site has that kind. Menu items, and kinds your site lacks, are left
  out and counted.

The preview opens. It names the file and the site it came from, says that
everything is made as a draft and keeps its original date, and lists every
author match, every new category or tag, and every item, one line each. Then
what is left out. Press **Import as Drafts**.

**Pictures and files.** If the export names files, QUILL asks about them
next, under **Files**:

- **Download the files from** the old site's address **and upload them** to
  yours;
- **Skip the files; the text keeps pointing at the old site**, which is
  chosen for you.

Downloading asks the named site for each file by the address in the export,
over HTTPS, up to 64 MB each, sending no password. It names every host it
will ask. Choose it only if you trust those addresses.

QUILL then makes each item as a draft. It points pictures and files at the
uploaded copies, links between the imported items at their new drafts, and
the old site's address at yours. You hear, for example, "Imported 40 of 42
items from export.xml into Community Radio as drafts, with 18 files." A
report says what happened to each category, file and item.

Changed your mind? Ctrl+Z moves the drafts it made to the Trash. Uploaded
files and new categories and tags stay, and the report says so.

Then open the drafts, read them over, and publish the ones you want.

## Moving in from Blogger, Medium, Substack or Squarespace

If your writing lives on another platform, ask it for its export first:

- **Blogger:** Settings, then Back up content, or Google Takeout. You get an
  `.xml` or `.atom` file.
- **Medium:** Settings, then Download your information. You get a `.zip`.
- **Substack:** Settings, then Export. You get a `.zip`.
- **Squarespace:** Settings, then Export, then WordPress. You get an `.xml`
  file.

Then, in the Workbench:

1. Select the site you are moving into, or anything on it.
2. Choose **Tools > WXR Files > Import from Blogger, Medium, Substack or
   Squarespace...** (Alt+T, then W, then B).
3. Choose the export file. You do not have to say which platform it came
   from; QUILL can tell.

QUILL reads the file on this computer and nothing else. From there it works
just like importing a WXR file: the same question about authors who have no
match, the same preview, everything made as a draft, and Ctrl+Z to move the
drafts to the Trash.

The preview starts with what QUILL found in the export:

- **Blogger:** posts and pages come in, and labels become tags. Posts that
  were drafts on Blogger are said to be drafts. Comments, settings and the
  template are left out and counted.
- **Medium:** each story comes in with its subtitle as the excerpt, and its
  author and date. Stories that were drafts on Medium are said to be.
  Responses and claps are not in Medium's export.
- **Substack:** each post comes in with its subtitle as the excerpt. A
  podcast episode gets a player for its audio at the top. Posts for paying
  subscribers come in as drafts like the rest, and the preview says how many
  there were. Threads are left out, and so is your subscriber list.
- **Squarespace:** its export is nearly a WordPress export, but it leaves
  out a few things WordPress expects, and writes many links starting from the
  site's root, such as "/menu". QUILL fills those in with your Squarespace
  address, and the import then points links between the imported pages at
  your new site. Squarespace's own layout markup is kept as it is.

**Pictures.** Blogger, Medium and Substack do not put pictures in their
exports, so the drafts keep showing each picture from where it is now. The
preview names those places, such as `substackcdn.com`, and nothing is
downloaded. If you plan to close the old account, move the pictures into
your Media Library first. A Squarespace export may name its files; if it
does, you get the same Files question as a WXR import.

If QUILL cannot tell what the file is, it says so, and nothing is sent.

## Keeping a static copy for an archive

A WXR file is for moving a site to another WordPress. When you want a copy
anyone can open in a browser years from now, with no WordPress at all, use
**Tools > WXR Files > Archive a Static Copy...** (Alt+T, then W, then S).

1. Select the site in the tree.
2. Choose **Archive a Static Copy...**.
3. Choose an empty folder. If the folder you pick already has files in it,
   QUILL makes a new folder inside it, named after the site, and uses that.

QUILL reads every published page and post and writes each one as its own
plain web page, with its title as the heading and, for a post, the day it
was published. A file called index.html lists them all, pages first, then
posts, newest first. Open that file in your browser to start.

Pictures, sounds, videos and documents the pages use are copied into a
folder called media, and the pages point at those copies, so the archive
works with no internet connection. Links from one page to another point at
the copied pages too. QUILL only fetches files from your own site. A picture
shown from somewhere else, such as a video service or another website, is
left pointing where it was, and the report at the end names each one.

Drafts and private posts are never part of the archive. Nothing on the site
changes. The report says how many pages, posts and files went in, then lists
anything left out and why.

## Copying to another of your sites

**Item > Copy to Site...** (`Ctrl+Shift+Y`) copies what you have selected to
another of your sites: posts, pages, media, menus, categories and tags,
synced patterns and forms.

1. Select what to copy in any list.
2. Press Ctrl+Shift+Y and choose the site to copy to.
3. Read the preview. It says what will be made and what replaced, each
   picture to upload, and anything left out.
4. Press **Copy**.

QUILL matches authors, categories, tags and menus by name, uploads the
pictures a post needs or reuses ones already there, and rewrites links that
point at the first site. New items are drafts on the other site. If anything
did not copy, a report says what and why.

In the editor, **File > WordPress > Send and Copy > Publish to Another
Site...** does the same for the page you are writing (Chapter 3).

## Comparing two sites

**Site > Compare Sites...** (`Ctrl+Alt+K`) asks for another of your sites,
then reports what differs between the two: posts, pages, synced patterns,
categories, tags and menus, each by its slug. It also says what it does not
compare. Nothing is changed.

## Snapshots

A snapshot is a copy of a site's content on this computer. Take one before
a big change, and you can set things back if it goes wrong.

**Taking a snapshot.**

1. Select the site, or anything on it.
2. Choose **Site > Take a Snapshot...** (`Ctrl+Alt+S`).
3. Under **Save**, choose **Everything but the media files**, or
   **Everything, with the media files too**.

It saves every post, page, synced pattern, category, tag, menu, setting and
media record. People, passwords, plugins, themes, revisions and comments are
never saved. You hear what was saved, where, and what was left out.

**Putting a site back.**

1. Choose **Site > Put Back from a Snapshot...** (`Ctrl+Alt+Shift+S`).
2. Under **Snapshot**, choose one. The newest is first.
3. The preview lists every change. Press **Put Back**.

Posts, pages, synced patterns, categories and tags changed since the snapshot
are set back to it. WordPress keeps a revision of each post and page it
changes, so even this can be undone from Previous Versions. Ones deleted
since are made again as drafts, at new addresses. Menus, settings, people,
plugins and media files are not put back.

If the snapshot came from the Practice Site and you are putting it on a real
site, QUILL asks you by name first.

A snapshot is QUILL's own format. For a copy any WordPress can read, export a
WXR file instead.

## Changing a name everywhere it is used: By Name

Each site's **By Name** branch lists the values your content uses, a place
for each kind:

- **Every Term**: every category, tag and other grouping;
- **Field Values**: the values in custom fields;
- **Authors**;
- **Media Usage**: every file, and where it is used;
- **Patterns Used**;
- **Links**: every address your pages link to;
- **Blocks and Shortcodes**;
- **Forms Used**;
- **Template Parts**.

Enter on a row says **Where It Is Used**. The context menu also has:

- **Rename Everywhere...**: a new name or value, wherever it is used;
- **Split...**: move the items you choose to a new term, value or person,
  and leave the rest;
- **Merge Into...**: move every item to another term or value, and delete the
  merged term;
- **Reassign...**: move every item to another term or person, and keep this
  one;
- **Replace Everywhere...**: another file, pattern, link, shortcode or form,
  in every page that uses this one;
- **Find Items Missing This Field**, on a custom field: the posts and pages
  with no value;
- **Convert to Block...**, on a shortcode in Blocks and Shortcodes: turns
  gallery, caption, audio, video and embed shortcodes into the blocks
  WordPress's own editor would make of them, on the items you check. A
  gallery needs its pictures in the Media Library, and an audio or video
  shortcode needs a file address; any one that cannot be converted cleanly
  stays as it was, and the preview says which and why. Playlist has no
  WordPress block, so it stays a shortcode;
- **Update Pattern Everywhere...**, on a synced pattern in Patterns Used:
  change its blocks once, and every page that places it shows the change;
- **Detach Copies...**, on a synced pattern: the pages you check get the
  pattern's own blocks in its place, as Detach does in the block editor.
  Editing the pattern afterwards no longer changes those pages;
- **Pages Using Its Blocks**, on a block from a plugin (or on the plugin's
  own row under Plugins): every page using any block from that plugin. Look
  here before you remove a plugin, because its blocks stop showing once it
  is gone.

Each is previewed item by item. Every item is read again before it is sent,
and one that changed since the list was made is left alone. You hear how each
item went, and each goes in Change History. Ctrl+Z undoes it where putting
the old value back truly restores it. A merge deletes a term, so it says it
is final.

A template part's title can be renamed here, but not its slug, because
templates find a part by its slug.

## Across Sites

**Go > Across Sites** (`Ctrl+0`) shows things your sites share, side by side:
**Tags and Categories**, **Plugins**, **Themes**, **People**, **Settings**,
**Menus**, **Synced Patterns**, **Application Passwords**, **Starter
Pages**, **Forms**, **Content Types**, **Pages with a Role**, **Redirects**
and **Spam Senders**. Each row says the versions in use and which sites are
missing it. A site that does not run the plugin a list needs, such as
Redirection for Redirects or QUILL Accessible Forms for Forms, is named as
not read rather than missing, so nothing is ever made there by mistake.

A few of these are for comparing only. Starter pages and content types are
set up by each site's theme and plugins, and WordPress cannot copy them from
outside, so their rows show where they differ and stop there.

Pages with a Role means the front page and the privacy policy page.
WordPress does not say from outside which page is the privacy policy, so
QUILL uses the page at its usual address, privacy-policy, and says so on the
row.

**Site > Across Sites Scope...** (`Ctrl+Alt+Y`) chooses every site, or one
Site Set. **Site > Site Sets...** (`Ctrl+Alt+T`) names a set of your sites,
such as "Branch sites".

On a row:

- **Make Them the Same...** asks which version wins, previews every site's
  change, and says how each went. It covers categories and tags, plugins
  (on or off), settings, people's roles, synced patterns, menus and themes.
  WordPress cannot switch a theme from outside, so for a theme it opens each
  site's Themes screen in your browser. A copied menu is final. It also
  covers forms (a site without the form gets a draft, so you can check who
  its notifications go to there; a site with it keeps its own settings and
  responses), pages with a role (the text of the one you choose goes to the
  others, which is how you bring stale privacy pages up to date), redirects
  (made where missing, in that site's usual group) and spam senders (blocked
  on the sites that do not block them yet).
- **Merge Everywhere...**, on a tag or category: name the term to merge it
  into, and on every site that has both, each post moves across and the old
  term is deleted. A site without a term of that name is left alone and
  named in the preview. It is final.
- **Remove Everywhere...**, on a tag or category, a redirect or a spam
  sender: deleted on every site that has it, after a preview that starts on
  Cancel. The preview gives each site's post count for a term. It cannot be
  undone.
- **Install on Sites Missing It...** installs a plugin from WordPress.org on
  every site that lacks it, after a preview. For a theme, it opens each of
  those sites' Add New screen.
- **Promote to Network...** activates a plugin for every site of a multisite
  network. It is only offered where the site says the plugin can be, and
  WordPress refuses it unless you are a super admin.
- **Revoke Everywhere...**, on an application password, revokes it on every
  site that has it, after a preview. It cannot be undone.
- **Compare Global Styles** shows each site's colours and font sizes, and
  which differ.

On Plugins, the rows also carry what WordPress.org says of each plugin, such
as its rating and a warning for one that is closed or abandoned, once you
have agreed to ask WordPress.org in that window.

**Fleet**, under Across Sites, has a row for each site, with columns for its
health, backups, security and updates. Each one says known, unknown,
unavailable or stale. If a site stops answering, its last answer stays, with
when it came. The Fleet only reads.

## Lists in and out

- **Edit > Export List...** (`Ctrl+Shift+X`) saves the list you are in as an
  Excel file, a CSV file or a Markdown table.
- **Edit > Import Posts from a Spreadsheet...** (`Ctrl+Shift+I`) makes posts
  or pages from an Excel or CSV file. It matches the columns to WordPress's
  fields and shows you the match first. Rows marked published or scheduled
  come in as drafts, and you hear how each row went.
- **Edit > Import a Folder of Documents...** (`Ctrl+Alt+Shift+I`) makes a
  draft from each Markdown, text or Word file in a folder, previewed file by
  file.
- **Tools > Plain-Language Batch...** (`Ctrl+Alt+B`) lets you write a change in
  words, such as `move all drafts by Sam to pending on Radio`, `add tag 2026
  to posts in category Events on every site`, or `remove tag Old from all
  published posts by Ann`. QUILL finds the exact items you meant. A name that
  matches nothing is said, never guessed. Then it gives you a checklist of the
  items. Uncheck anything that should not change, then send. It does not use
  AI.

  Any of these can say how old: `older than a year`, `older than six months`,
  `newer than two weeks`, `before March 2024` or `after 2023`, all by the
  date of the post or page. To clear things out, say `move every draft older
  than a year to Trash` or `trash all drafts before March 2024`. You get the
  same checklist first, and `Ctrl+Z` puts everything back with the status it
  had. To ask instead of change, start with "how many": `how many drafts are
  older than six months?` or `how many pages are pending on every site?`
  QUILL says the count for each site and changes nothing.

In the editor, **File > WordPress > Send and Copy > Download My Writing...**
saves every page and post to a folder as Markdown or Word, and **Send a
Folder as Drafts...** does the reverse (Chapter 3).

## Reading a whole site as one document

**Site > Read Site as Document** (`Ctrl+Alt+D`) opens the site's published
pages in the editor as one document: the whole site, one menu or one
category. It starts with the site's address, what was read and when. It keeps
headings, lists, links and alternative text, leaves out password-protected
pages and counts them, and stops at 500 items, saying so. From there you can
read it, search it, or save it in any format the editor writes.

## Where to next

- Previous: [Chapter 8: Running your site](wordpress-forms-08-running-your-site.html)
- Next: [Chapter 10: Shop, events, SEO, memberships and redirects](wordpress-forms-10-shop-events-seo-memberships.html)
- [Contents](wordpress-forms-guide.html)
