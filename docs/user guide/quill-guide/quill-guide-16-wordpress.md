# Chapter 16: WordPress

Payment forms use this same WordPress connection. Tools > Forms configures
Stripe/PayPal payments and reads provider/webhook readiness; the QAF plugin
must implement payment contract version 1. Provider credentials and checkout
stay on the site. See [Forms](quill-guide-17-forms.html) for setup and testing.

If you look after a WordPress website, QUILL can write its pages and posts,
open the ones already there, and publish your changes. You work in the same
editor you use for everything else, with Find, spelling, dictation and all
your usual keys. Your site keeps its theme and its look; QUILL works on the
words and pictures inside it, and can help you look after the site itself.
Nothing reaches your site until you choose to send it. Saving with `Ctrl+S`
only ever saves on your computer.

**Turning it on.** WordPress is on in every feature profile except Essential. If you do
not see **File > WordPress**, choose another profile, or switch on
WordPress by itself, in **Profiles and Features...**.

This chapter is the short version. Connecting a site, blocks, pictures and the
Media Library, scheduling, checking a page before you publish, comments, menus
and running the site are all in the
[WordPress and Forms manual](../wordpress-and-forms/wordpress-forms-guide.html), which QUILL and QUILL Lite share.

## Where everything is

| Menu | What is there |
|---|---|
| **File > WordPress** | New, Open, the three saves, Properties, versions, Trash, your sites |
| **Insert** | Blocks, pictures, links to your own pages, Make a Picture |
| **Format > WordPress** | Block Settings, Image Size, Mark Language |
| **View** | WordPress Blocks, Preview Blocks, Play Media Here |
| **Edit > WordPress** | Next Block, Previous Block, Where Am I |
| **Tools > WordPress** | The WordPress Workbench, checking, the Media Library, comments, menus, settings, and the More Media and Manage submenus |

To get started, choose **File > WordPress > Connect a Site...**, type your
site's address, and press **Get Password with My Browser**. Every command is
also in the Command Palette (`Ctrl+Shift+P`): type "WordPress", or part of a
command's name.

## The WordPress Workbench

Writing happens in the editor; looking after your sites happens in the
WordPress Workbench, one window for every site you have connected. Open it
with **Tools > WordPress > Open WordPress Workbench**, or with the WordPress
key and then H. The other rows of Tools > WordPress open it too, each at its
own place: Comments opens it at the comments waiting, Media Library at your
media, Site Settings at the settings.

The window has a tree on the left that says where you are, a list of what is
there, and the details of the one you have selected, with a status bar after
them; F6 moves from one to the next. The tree starts with **Needs My
Attention**, which gathers what waits on every site at once: comments waiting,
posts waiting for review, scheduled posts, your drafts, Site Health problems,
form responses and anything held as spam. Under **Sites**, each site has its
posts and pages, its media, comments, people, plugins, settings and the rest.
**Calendar** lists every site's scheduled and published posts a day at a time,
and **Across Sites** shows the same tag, plugin, person or setting on all your
sites at once, with where they differ and which sites are missing it.

Enter on a post or page opens it here in the editor. Alt+Enter shows the
Properties of anything, the same sheet File > WordPress > Properties shows
for the post you are writing. Delete moves to the Trash, and the Edit menu's
Undo WordPress Change puts the last change back. Every command says what it
needs: if your role on a site does not allow something, the menu says which
role would, rather than leaving you to find out.

Nothing that changes a site is sent without your say. Changing many items at
once, copying to another site, importing from a spreadsheet and making
settings the same across sites all show a preview first, one line for each
thing that will change, and nothing goes until you press the button that
names the change.

The Workbench's own Tools menu has the **REST Console**, for anything the
site's API offers, the **Practice Site**, a WordPress site on your own
computer for learning with nothing at stake (in builds that include it), and
**Workbench Options**. There you can turn on **Watches**, which tell you about
new comments, form responses, updates and scheduled posts going live while
QUILL is open, checked at most every fifteen minutes. For this release,
Workbench Options also has **Use the classic WordPress windows**: check it
and the rows of Tools > WordPress open their old windows again. Open
WordPress Workbench always opens the Workbench.

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

**Escape** after the WordPress key leaves it again. The menus show every
command's letter beside its row, and the manual has the full table. QUILL and
QUILL Lite use the same letters, so moving between them costs you nothing.

QUILL finds the grave key by where it sits, the key above Tab, not by what it
types. So the WordPress key works on a German, French, Nordic or any other
layout, where that key types `^`, `²` or `§` rather than a backtick. The
QUILL key works the same way; Chapter 2 has the details.

---

- Previous: [Chapter 15: Help, updates and support](quill-guide-15-help-updates-and-support.html)
- Next: [Chapter 17: Forms](quill-guide-17-forms.html)
- [Contents](../userguide.html)
