# Chapter 8: Running your site

## What this chapter covers

Beyond the writing, somebody has to look after a site: its health, its
settings, its plugins and themes, its look and its updates. If that is you,
this chapter is for you. Most of it needs the Administrator role, and the
Workbench only offers what your role can use.

You will read your site's overview and health, change its settings, look
after plugins, themes and fonts, change the site's look and its templates,
and see what needs updating. You will also meet the tools for the jobs
WordPress only does in wp-admin.

By the end you will know how your site is, and how to keep it that way.
Everything that changes the site shows you what will change, and asks first.

## QUILL asks the site first

Sites differ. One runs the newest WordPress with a block theme, another an
older version with a classic theme and a security plugin. QUILL reads what
each site offers, once a session, before it offers anything. A command your
site does not have, or your role cannot use, says why in one sentence, such
as "Community Radio does not offer this. It may be turned off, or the site
may need a newer WordPress." Nothing is sent.

## The site at a glance

Each site's **Overview** in the Workbench (`Ctrl+2`) is wp-admin's Dashboard,
in words. It has three places:

- **At a Glance** says the counts as sentences: "Posts: 12 published, 3
  drafts, 1 scheduled", then pages, comments, people, the WordPress version
  and the theme. If the site runs WooCommerce, The Events Calendar, Yoast SEO
  or Paid Memberships Pro, each gets a sentence too, such as orders waiting or
  events coming up. A count your role cannot see is left out, never said as
  zero.
- **Activity** lists what is publishing soon, what was published lately, and
  the newest comments, five of each. Enter on a post opens it in the editor.
- **wp-admin Screens** lists every wp-admin screen, the place in the
  Workbench nearest to it, and whether the Workbench does all of it, part of
  it, or none. Enter says what QUILL cannot do there and opens the screen in
  your browser. **Go to Its Place in the Workbench** takes you to the place.

## Site Health

**Tools > WordPress > Site Check** opens the Workbench at the site's **Site
Health**. It lists what the site says about its own health, critical things
first: the WordPress version, HTTPS, the time zone, readable addresses, and
every Site Health test the site runs, each in one line. **Needs My Attention
> Site Health** gathers the problems from every site, worst first.

If the authorization header test fails, the row explains that application
passwords cannot work on that site until the host fixes it. That one line has
saved many people an afternoon.

WordPress gives each problem a label and not much else. In the Workbench,
Enter on a Site Health row is **Explain**: what the problem means for the
people who visit your site, what usually causes it, and the steps to fix it,
followed by WordPress's own description. The row's context menu has three
more:

- **Fix...** does the fix from here when that is possible. A fixed time
  offset becomes a city time zone, such as Europe/London, after a preview,
  and Ctrl+Z puts it back. When only wp-admin can fix it, such as the address
  style under Permalinks, Fix... says why and opens that wp-admin screen.
  When nothing outside the server can fix it, the command is greyed and says
  what to ask your host.
- **Take Me There** goes to the place in the tree where it is fixed, such as
  Settings or Plugins.
- **Open in Editor** works on a broken link, below.

The same commands work on **Needs My Attention > Broken Links**. There,
**Fix...** asks for the right address, shows how many times the post holds
the old one, and changes it after you say yes; Ctrl+Z puts the old link back.
**Open in Editor** opens the post that holds the link, when you would rather
change the words around it too.

Under Site Health:

- **Information** shows the tests and how much room the site's folders take.
  The rest of wp-admin's Info tab, such as the server and database, has no
  way in from outside, so its last row opens that tab in your browser.
- **Security** asks the site whether XML-RPC, an old way in that QUILL never
  uses, still answers, and warns you if it does.

**Search and Upkeep**, in each site's branch, covers whether search engines
may list the site, its sitemap, scheduled posts that missed their time, the
site's certificate, and who is editing what. Every row ends with where
QUILL's answer came from.

## Site settings

**Tools > WordPress > Site Settings...** opens the Workbench at the site's
**Settings**: the title, tagline, language, time zone, date format, front
page, posts page, site icon and more, each on its own row.

To change one, arrow to it and press Alt+Enter. Change the value and press
OK. QUILL reads the setting again first, and checks afterwards that the site
kept it.

Each row says what the setting does on your site, with your own example:
your posts page by name, what a date looks like in your date format. Below
the settings you can change are the ones WordPress keeps to wp-admin, still
explained with your own site:

- **Permalinks** says what your newest post's address would become under
  each choice (Plain, Day and name, Month and name, Numeric and Post name),
  and which one your site uses now.
- **The Discussion rules** say how many of your last hundred comments each
  rule would have held: manual approval, a previously approved comment, two
  or more links, and signed-in visitors only.
- **Search engine visibility** says what that check box really does: it asks
  search engines to leave the site out, and hides nothing from anyone with
  the address.
- **Plugin settings** rows, for WooCommerce, The Events Calendar, Yoast SEO,
  Gravity Forms, Paid Memberships Pro and the others QUILL recognises, say
  which of the plugin's settings the Workbench reaches. **Open Its
  Documentation** opens the plugin's own help.

**Open in Dashboard**, on any of these, opens the wp-admin screen that
changes it.

The site language matters more than it looks. It decides which voice a
visitor's screen reader uses for the whole site. **Language Pack Status...**,
on a setting's context menu, says each site's language and whether
WordPress.org has its translation for that WordPress version. It asks
WordPress.org, so QUILL asks you first, naming the address and what is sent.

## Plugins

**Tools > WordPress > Manage > Plugins...** opens the Workbench at the site's
**Plugins**: every plugin, whether it is active, and its version.

- **Activate or Deactivate** turns the selected plugin on or off, after a
  preview. Before you turn one off, QUILL asks the site what depends on it
  and puts the answer in the question: other plugins that need it, pages and
  posts that use its blocks or shortcodes, and the QUILL features that use
  it. A plugin QUILL itself relies on, such as QUILL Accessible Forms, also
  says what stops working. Ctrl+Z turns it back on.
- **What Depends on It** asks the same question without changing anything.
  Use it before you delete a plugin in wp-admin, too.
- **Find a Plugin on WordPress.org...** searches the plugin directory and
  installs the one you choose, switched off, after a preview.
- **Check on WordPress.org...** reads every plugin on the site from the
  directory: its rating, how many sites use it, when it was last updated, the
  WordPress version it was tested with, and what it needs. A plugin
  WordPress.org has closed, or has not seen updated in over two years, gets a
  warning. Only the plugins' short names are sent, and QUILL asks first.
- **Open in Dashboard** opens wp-admin's Plugins screen in your browser.

**What WordPress cannot do from outside.** WordPress lets apps install,
activate, deactivate and delete plugins, but not update them, and there is
no way to put back an earlier version. If a plugin causes trouble, deactivate
or delete it. An earlier version only comes back from the site's own backup,
or an upload in wp-admin.

## Themes and fonts

**Tools > WordPress > Manage > Themes...** opens **Appearance > Themes**: the
installed themes and what the active one supports. WordPress does not let
apps switch or install themes, so **Activate...** and **Open in Dashboard**
take you to the right wp-admin screen. **Find a Theme on WordPress.org...**
searches the theme directory, after asking.

**Tools > WordPress > Manage > Fonts...** opens **Appearance > Fonts**. Each
font is described in words, such as "serif, suits body text".

## Updates

**Needs My Attention > Updates** lists, for every site, WordPress itself with
its version, every plugin and theme with the version installed, and, where
the site runs it, Site Health's automatic updates test.

WordPress does not tell apps whether a newer version is waiting, so the
Update column says "Not reported over REST" unless the site itself says
otherwise. QUILL never guesses. Enter on any row opens that site's
**Dashboard > Updates** in your browser, where updates are run. The
Workbench never updates anything itself.

**Check for Updates on WordPress.org...**, on a plugin, theme or Updates
row, asks WordPress.org which versions are current, after you agree. For a
plugin with an update waiting, it also reads the plugin's changelog for the
versions you would skip. The row then says how many versions those are, and
says plainly when the changelog mentions security fixes, breaking changes or
a database update. A database update is the one to back up for, because
turning the plugin off afterwards does not undo it. **Read in Full** shows
what the changelog says for each of those versions, as plain text.

To hear about updates as they come, turn on the Watch for them, below.

## The site's look

The look of a block theme lives in **Appearance** in the Workbench. You need
to be an Administrator for all of it, and QUILL tells you before any window
opens if you are not.

**Global Styles** lists the theme's colours and font sizes. Each colour says
how it contrasts with the page text and background. **Change...** previews a
new value, with its contrast, and Ctrl+Z puts it back.

**Templates** and **Template Parts** list the theme's templates, such as
Single Posts, and its parts, such as the header. On one:

- **Edit Block Markup...** opens it as text. When you press OK, the change is
  read back line by line, such as "Line 4 added", before anything is sent.
  From then on the site keeps its own copy. Ctrl+Z puts it back.
- **Earlier Versions...** lists the versions the site kept, and restores the
  one you pick after the same preview.
- **Reset to the Theme's Version...** removes the site's copy, so the theme's
  own is used again. A template the theme never had is deleted instead, and
  the preview says so. Ctrl+Z brings your copy back.
- **New Template...** asks for a name such as `single-post-news` or
  `page-about`, and starts from the template WordPress would use for it
  today.
- **Open in the Site Editor** opens it in wp-admin, for laying it out by
  sight.

**Additional CSS** has one row. On a block theme, **Edit Additional CSS...**
opens the CSS as text, warns that it changes every page, and reads the change
back before saving. CSS with tags in it, or braces that do not pair up, is
refused before anything is sent. A classic theme keeps its CSS in the
Customizer, so its row opens that in your browser.

**Patterns** lists the synced patterns, the blocks you reuse and change in
one place. **Tools > WordPress > Manage > Synced Patterns...** opens it.

**Widgets and Sidebars** lists a classic theme's widget areas, such as the
sidebar or the footer. **Tools > WordPress > Manage > Widgets...** opens it.
On an area:

- **Add a Widget...** offers every kind of widget the site has. A Block widget
  asks for its words. Any other kind, such as Search or Recent Posts, opens on
  its own settings, labelled as WordPress labels them.
- **Change a Widget...**, **Move a Widget...** and **Remove a Widget...** work
  on one of the area's widgets. A removed widget goes to Inactive Widgets,
  where WordPress keeps it.
- **Preview Widgets** reads the whole area as a visitor hears it.

Each one is previewed, Ctrl+Z undoes it, and a widget somebody changed in the
meantime is never overwritten.

### The look, from the editor

These are in **Tools > WordPress > Design** and **Manage**, for sites with a
block theme:

- **Style Variations...** lists the ready-made looks your theme comes with,
  each with how many of its colour pairings are too faint for body text.
  **Details** reads out its whole Palette Report, and **Apply** makes one the
  site's look. QUILL keeps the look you had first, so **Put Back the Previous
  Look** brings it back.
- **Site Styles...** lists your site's colours and font sizes by name, each
  with how it reads on the page background, such as "Accent (dark green),
  #1a4d2e, 7.2 to 1 on the page background, passes".
- **Previous Looks...** lists your site's earlier styles, dated. **Go Back to
  This Look...** restores one, and keeps the look you had.
- **Download a Copy of the Site's Design...** saves a zip of your block theme
  with your changes, a good thing to have before you try something new.
- **Template Outline** lists a block theme's templates and their blocks,
  starting with the one your open page uses. It explains the things on a page
  that are not in the page, such as a sign-up box the theme adds to every
  post.

## The shape of the site

- **Tools > WordPress > Manage > Site Map...** opens the Workbench at
  **Pages**, shown as a tree, each page under its parent.
- **Tools > WordPress > Manage > Page Order...** shows your pages as a tree.
  Moving one sets its parent and its place.
- **Tools > WordPress > Manage > Bulk Edit...** lists your posts or pages.
  Select the ones you want, then change their status, author, comments or
  parent, or add a category or tag. **Undo Bulk Edit** puts them back. The
  Workbench does the same with Alt+Enter on several rows (Chapter 3).
- **Tools > WordPress > Manage > Space Used** says how much room your uploads,
  themes, plugins, WordPress itself and the database take, in plain words.

**Content Model**, in each site's branch, lists every kind of content and
every way of grouping the site has, with who added it, such as Gravity Forms
or The Events Calendar. These are defined in a plugin's or theme's code, so
they are read only here. Their items are still edited in their own lists.

## Jobs only wp-admin does

Some of WordPress has no way in from outside: updates, switching themes,
privacy requests, most of Site Health's Info tab. QUILL says so on the row
where it matters, before you act, and takes you to the right screen.

- On any place in a site's tree, the context menu has **wp-admin for This
  Place...**, which offers the screens nearest to it.
- **Privacy Requests** has a row for each of WordPress's export and erase
  screens. Enter opens it in your browser. QUILL cannot see whether a request
  was done there, and never says it was.
- **Administration Areas** lists every part of running a site, such as
  backups, security, caching, translation, email, newsletters, courses,
  events, analytics and sharing, and says for each what QUILL does and where
  the rest is.
- **More from This Site** lists the other ways in the site's plugins offer,
  grouped by plugin, with each one's routes.

## AI Abilities and Ask the Site

WordPress 6.9 lets a site offer actions to AI, called abilities, such as
"list upcoming events" or "create a draft".

- **Tools > WordPress > Manage > AI Abilities...** opens the Workbench at the
  site's **Abilities**, each by name. **Run...** asks for what it needs, shows
  a preview, then runs it. **Offer to Ask the Site**, on the same context
  menu, turns an ability on or off for Ask the Site. An ability that can
  change the site asks you first. Your choice is kept on this computer.
- **Tools > WordPress > Manage > Ask the Site...** sends your question to the
  AI you chose in Choose Your AI. It only offers the AI the abilities you have
  turned on for that site, each one separately, and says so if none is on. If
  the AI wants to use one, QUILL asks you first, every time, and says exactly
  what it will be given. The answer ends by saying what ran on your site.

## Watches

Watches tell you when something happens on your sites while QUILL is open.
They are all off until you turn them on.

1. In the Workbench, choose **Tools > Workbench Options...**
   (`Ctrl+Shift+O`).
2. Check the Watches you want, and press OK.

You can watch for new comments waiting, new form responses, plugin updates
available, scheduled posts going live, a site not answering and answering
again, items with a reviewer leaving the queue, Site Health status changes,
and form spam questions, once a week. Site Health stays silent for an
account that is not an administrator.

A few more are there for the things that are easy to miss:

- **New shop orders** and **products running low on stock**, on a site with
  WooCommerce. Low means at or under the product's own low-stock amount, or
  the shop's if the product has none.
- **A security certificate running out within 30 days.** Once a day, QUILL
  reads the certificate your site's own address presents, and nothing else.
  You hear once when it is 30 days away or less, once if browsers stop
  trusting it, and once more when it is renewed. Sites on WordPress.com are
  left out, because WordPress.com renews theirs.
- **Plugins that may be abandoned.** Once a week, QUILL asks WordPress.org
  about each plugin on the site, by its short name only. You hear about one
  that WordPress.org has closed, or that has not been updated there for over
  two years.
- **An accessibility statement whose facts have changed.** When Check the
  Whole Site finds something different from the last time, and your
  published Accessibility page was saved before that check, you hear that
  the statement is out of date. **Write an Accessibility Statement** drafts
  it again with the new facts (Chapter 7).
- **A weekly sentence about each whole site**: comments waiting, plugin
  updates, Site Health tests that are critical, plugins that may be
  abandoned, low stock and when the certificate runs out, said together once
  a week.

Each site is checked no more often than every fifteen minutes. The first
check is silent, so you only hear about what changes after it. **Go >
Watches** (`Ctrl+5`) says when the last round ran and whether each site is
answering.

## The REST Console

For anything a site offers that has no command of its own, **Tools > REST
Console...** (`Ctrl+Shift+T`) in the Workbench sends a request to any route
the site has. It completes route names as you type, the **Accepts** box lists
what a request takes, and **What It Returns** says what comes back. A change
is previewed first, with any missing or unknown arguments named, and goes in
Change History.

**Save Request** keeps a request you use often. **Tools > Saved Requests**
lists them, numbered 1 to 9, and **Tools > Run a Saved Request...**
(`Ctrl+Alt+Q`) opens the console with one. **Tools > Forget a Saved
Request...** (`Ctrl+Alt+Shift+F`) removes one.

## Before a big change

Take a snapshot first. **Site > Take a Snapshot...** (`Ctrl+Alt+S`) saves the
site's content on this computer, and **Site > Put Back from a Snapshot...**
(`Ctrl+Alt+Shift+S`) sets it back. Chapter 9 shows how.

## Signing out of a site

**Tools > WordPress > Manage > Sign Out This Site...** revokes QUILL's own
application password on the site, as Chapter 1 describes.

## Across all your sites

These are in **Tools > WordPress > Your Sites**, and look at every site you
have connected:

- **Coming Up...** lists everything scheduled on all your sites, soonest
  first.
- **What Changed on My Sites...** lists new comments, posts other people
  published, and health warnings since you last looked. It only appears when
  you ask. Run it again and it says nothing is new.

The Workbench's **Across Sites** and **Fleet** do much more, and Chapter 9
covers them.

## Where to next

- Previous: [Chapter 7: Checking before you publish](wordpress-forms-07-checking.html)
- Next: [Chapter 9: Moving and copying content](wordpress-forms-09-moving-and-copying.html)
- [Contents](wordpress-forms-guide.html)
