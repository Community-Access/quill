# Chapter 16: WordPress

If you look after a WordPress website, QUILL can write its pages and posts,
open the ones already there, and publish your changes. You work in the same
editor you use for everything else, with Find, spelling, dictation and all
your usual keys. Your site keeps its theme and its look. QUILL works on the
words and pictures inside it, and looks after the site itself in a window of
its own, the WordPress Workbench.

Nothing reaches your site until you choose to send it. Saving with `Ctrl+S`
only ever saves on your computer.

This chapter is the short version: a guided first run, and where to find the
rest. Everything else is in the
[WordPress and Forms manual](../wordpress-and-forms/wordpress-forms-guide.html),
which QUILL and QUILL Lite share.

**Turning it on.** WordPress is on in every feature profile except Essential.
If you do not see **File > WordPress**, choose another profile, or switch on
WordPress by itself, in **Profiles and Features...**.

## Where everything is

| Menu | What is there |
|---|---|
| **File > WordPress** | New, Open, the three saves, Properties, versions, Trash, your sites |
| **Insert** | Blocks, pictures, links to your own pages, Make a Picture |
| **Format > WordPress** | Block Settings, Image Size, Mark Language |
| **View** | WordPress Blocks, Preview Blocks, Play Media Here |
| **Edit > WordPress** | Next Block, Previous Block, Where Am I |
| **Tools > WordPress** | Open WordPress Workbench, checking, the Media Library, comments, menus, settings, and the More Media and Manage submenus |

Every command is also in the Command Palette (`Ctrl+Shift+P`): type
"WordPress", or part of a command's name.

## Your first ten minutes

1. Choose **File > WordPress > Connect a Site...**, type your site's address,
   and press **Get Password with My Browser**. Approve QUILL in your browser.
   You hear, for example, "Connected to Community Radio as Editor."
2. Choose **File > WordPress > New Post...**, type a title, and press
   **Create**. Write a paragraph.
3. Choose **File > WordPress > Save Draft to Site**. Only you and your
   site's editors can see it.
4. Choose **File > WordPress > Publish or Update...**. QUILL checks the page
   and asks first. Choose **Publish**, and the address is on the clipboard.
5. Press the WordPress key, `Ctrl+Alt+Shift+Grave`, then H. The WordPress
   Workbench opens.
6. Press `Ctrl+1` for Needs My Attention, then arrow through what waits on
   your sites.
7. Press `Ctrl+Shift+E` to go back to the editor.

Chapters 1 to 3 of the manual walk through each step in full.

## The WordPress Workbench

You write in the editor, and you look after your sites in the Workbench, one
window for every site you have connected. Open it with **Tools > WordPress >
Open WordPress Workbench**, or with the WordPress key and then H. The site
rows of Tools > WordPress open it too, each at its own place: Comments at the
comments waiting, Media Library at your media, Menus at your menus, Site
Settings at the settings.

The window has a tree that says where you are, a list of what is there, the
details of the row you are on, and a status bar. F6 moves from one to the
next. Enter does a row's main job, such as opening a post in the editor.
Alt+Enter shows its Properties. The Applications key opens its context menu,
with everything else you can do to it.

Nothing that changes a site is sent without your say. A preview names the
site and lists each thing that will change, and nothing goes until you press
the button that names the change. Ctrl+Z puts the last change back.

The tree starts with **Needs My Attention**, which gathers what waits on
every site at once: comments, posts waiting for review, scheduled posts,
drafts, Site Health problems, pictures without alternative text, broken
links, form responses and anything held as spam. Under **Sites**, each site
has its posts and pages, media, comments, people, menus, plugins, settings
and the rest.

The Workbench's own Tools menu has the **Practice Site**, a WordPress site on
your own computer for learning with nothing at stake. **Help > Tutorials**
has lessons that use it.

The manual's [Chapter 2](../wordpress-and-forms/wordpress-forms-02-the-workbench.html)
is a full tour of the Workbench, and
[Chapter 17](../wordpress-and-forms/wordpress-forms-17-workbench-reference.html)
lists every place, menu and key.

## What you can do there

A taste of what the Workbench does, with the manual chapter that shows how:

- **Replace a file** that pages already use, such as a new menu PDF. On a
  file in Media, choose **Replace File...** from the context menu. QUILL keeps
  the address where the site can, and otherwise points every page at the new
  file, with an offer of a redirect. ([Chapter 5](../wordpress-and-forms/wordpress-forms-05-pictures-and-media.html))
- **Add a menu item.** On a menu in Menus and Navigation, press Ctrl+N and
  choose a new item, then the page, post, category or link, and where it
  goes. **Add New Pages Automatically...** makes WordPress add each new
  top-level page by itself. ([Chapter 6](../wordpress-and-forms/wordpress-forms-06-comments-people-and-menus.html))
- **Moderate comments and look after people**, from approving a comment to
  inviting a team from a spreadsheet. ([Chapter 6](../wordpress-and-forms/wordpress-forms-06-comments-people-and-menus.html))
- **Move a site.** The Workbench's Tools menu has WXR Files, which exports a
  site as a WordPress export file any WordPress can import, and imports one
  as drafts. Copy to Site, snapshots and Across Sites work between your own
  sites. ([Chapter 9](../wordpress-and-forms/wordpress-forms-09-moving-and-copying.html))
- **Run the site**: its health, settings, plugins, themes, templates and
  updates. Where WordPress cannot do something from outside, such as update a
  plugin, the row says so and **Open in Dashboard** takes you to the right
  wp-admin screen. ([Chapter 8](../wordpress-and-forms/wordpress-forms-08-running-your-site.html))
- **A shop, events, SEO, memberships and redirects**, on sites with
  WooCommerce, The Events Calendar, Yoast SEO, Paid Memberships Pro or
  Redirection. ([Chapter 10](../wordpress-and-forms/wordpress-forms-10-shop-events-seo-memberships.html))

## From the page you are writing

- **File > WordPress > This Post in the Workbench** (the WordPress key, then
  Shift+H) opens the Workbench on the list your post is in, with your post
  selected.
- **Insert > Picture from the Media Library...** opens the Workbench on the
  site's media. Move to a picture and press Enter, and you are back in your
  page with the picture window open.
- **Insert Block** has **Install a Missing Block...** when the site lets you
  add block plugins.
- **Download My Writing** saves your writing as Markdown or Word, and **Send a
  Folder as Drafts** takes Word documents too.

## The keys you will use every day

The WordPress commands share one key, `Ctrl+Alt+Shift+Grave`: the key below
Escape, with Ctrl, Alt and Shift held down. Press it and let go, and QUILL
says "WordPress keys". Then press one letter:

| Letter | Command |
|---|---|
| O | Open Page or Post |
| P | Publish or Update |
| D | Save Draft to Site |
| W | Open by Web Address |
| M | Media Library |
| S | Switch Site |
| N | New Post |
| G | New Page |
| K | Check Before Publishing |
| H | Open WordPress Workbench |
| Shift+H | This Post in the Workbench |

**Escape** after the WordPress key leaves it again. The menus show every
command's letter beside its row, and the manual has the full table. QUILL and
QUILL Lite use the same letters, so moving between them costs you nothing.

QUILL finds the grave key by where it sits, the key above Tab, not by what it
types. So the WordPress key works on a German, French, Nordic or any other
layout, where that key types `^`, `²` or `§` instead of a backtick. The QUILL
key works the same way. Chapter 2 has the details.

## Forms and payments

Payment forms use this same WordPress connection. Tools > Forms sets up
Stripe and PayPal payments and checks the site is ready. The QUILL Accessible
Forms plugin on your site must support payments, and the payment keys and
checkout stay on the site. See [Forms](quill-guide-17-forms.html) for setup
and testing.

---

- Previous: [Chapter 15: Help, updates and support](quill-guide-15-help-updates-and-support.html)
- Next: [Chapter 17: Forms](quill-guide-17-forms.html)
- [Contents](../userguide.html)
