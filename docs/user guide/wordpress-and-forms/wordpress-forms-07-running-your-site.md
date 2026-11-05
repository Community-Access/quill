# Chapter 7: Running your site

## What this chapter covers

Beyond writing, someone has to look after a site: its health, its settings,
its people, its plugins and its look. This chapter covers everything QUILL
offers for that, in **Tools > WordPress** and its Manage, Design, Plugin
Extras and Your Sites submenus. Most of it needs the Administrator role; the
windows only show what your role can use. Everything that changes the site
says what it will change, and asks first.

## QUILL asks the site first

Sites differ. One runs the newest WordPress with a block theme, another an
older version with a classic theme and a security plugin. QUILL reads what
each site offers, once a session, before it offers anything. A command your
site does not have, or your role cannot use, says why in one sentence, such
as "Community Radio does not offer this. It may be turned off, or the site
may need a newer WordPress." Nothing is sent.

## Site Check

**Tools > WordPress > Site Check** lists what the site says about its own
health, critical things first: the WordPress version, HTTPS, the time zone,
readable addresses, and every Site Health test the site lists, each read as
one line.

Site Check also names the plugins QUILL recognises, such as The Events
Calendar, WooCommerce, Yoast SEO, Rank Math and QUILL Accessible Forms.

If the authorization header test fails, Site Check explains that application
passwords cannot work on that site until the host fixes it. That one line
has saved many people an afternoon.

## Site Settings

**Tools > WordPress > Site Settings...** shows the site's title, tagline,
language, time zone, date format, front page, posts page, site icon and
more. Choose one and press **Change**. QUILL tells you the old value and the
new one, and asks before it saves.

The site language matters more than it looks: it decides which voice a
visitor's screen reader uses for the whole site.

## Users and passwords

These are in **Tools > WordPress > Manage**:

- **Users...** lists everyone with an account and their role.
  Administrators can add a user, edit one, change a role and delete one.
  QUILL makes a strong password for a new user and never shows it; they
  choose their own with "Lost your password?" on the sign-in page. Deleting
  asks who gets the person's posts first, so no writing is lost. **My
  Profile** changes your own name, biography and website.
- **Application Passwords...** lists every app and computer signed in to the
  site with an application password, and marks this computer's. **Revoke**
  shuts off an old laptop or an app you no longer use.
- **Sign Out This Site...** revokes QUILL's own password on the site, as
  Chapter 1 describes.

## Plugins, themes and fonts

Also in **Tools > WordPress > Manage**:

- **Plugins...** lists what is installed and whether each is active, and
  says what the well-known accessibility plugins do. You can activate,
  deactivate, install and delete plugins. A new plugin is installed by its
  WordPress.org name, and switched off at first, so it cannot surprise you.
- **Themes...** lists the themes and what the active one supports.
  WordPress does not let apps switch themes, so **Open in Dashboard** takes
  you to the right page in your browser.
- **Fonts...** describes each font in words, such as "serif, suits body
  text", and installs more from the site's font collections.

## Patterns, widgets and the shape of the site

Also in **Tools > WordPress > Manage**:

- **Synced Patterns...** lists the site's reusable patterns and where each
  one is used. You can edit, rename, unsync (each use becomes ordinary
  blocks), delete an unused one, or make a new one from your selection. When
  your site sorts its patterns into categories, it asks which category to
  show first.
- **Widgets...** lists every widget by the area the theme shows it in, such
  as the sidebar or the footer. **Add Text...**, **Edit...**, **Move to
  Area...**, or **Remove...**, which sends it to Inactive Widgets rather than
  deleting it.
- **Site Map...** answers "where does this page live?": every page under its
  parent, then every post under its categories, with the menus that link to
  each.
- **Template Outline** lists a block theme's templates and their blocks,
  starting with the one your open page uses. It explains the things on a
  page that are not in the page, such as a sign-up box the theme adds to
  every post.

## Changing many pages at once

Also in **Tools > WordPress > Manage**:

- **Bulk Edit...** lists your posts or pages. Select the ones you want, then
  change their status, author, comments setting or parent page, or add a
  category or tag. QUILL asks once, naming how many and which site, and
  **Undo Bulk Edit** puts them back.
- **Page Order...** shows your pages as a tree. Moving one sets its parent
  and its place, which is how a site's page structure is built.

## The site's look

These are in **Tools > WordPress > Design**, for sites with a block theme.
Everything else about the look stays in WordPress's Site Editor.

- **Style Variations...** lists the ready-made looks your theme comes with.
  Each one is listed by name with how many of its colour pairings are too
  faint for body text, and **Details** reads out its whole Palette Report.
  **Apply** makes one the site's look. QUILL keeps the look you had, on this
  computer, first, so **Put Back the Previous Look** brings it back.
- **Site Styles...** lists your site's colours and font sizes, by name. Each
  colour says how it reads on the page background, such as "Accent (dark
  green), #1a4d2e, 7.2 to 1 on the page background, passes". Choose
  **Change**, type the new colour or size, and QUILL tells you the new
  contrast before anything is saved.

And in **Tools > WordPress > Manage**:

- **Previous Looks...** lists your site's earlier styles, dated, each with
  its colours. **Go Back to This Look...** restores one, and the look you
  had is kept, so you can change your mind.
- **Download a Copy of the Site's Design...** saves a zip of your block
  theme with your changes, a good thing to have before you try something
  new. On a classic theme it says only a block theme can.
- **Space Used** says how much room your uploads, themes, plugins, WordPress
  itself and the database take, in plain words.

## Plugins QUILL works with

QUILL needs no plugin for anything but forms. But where your site has one of
these, QUILL makes use of it. The commands are in **Tools > WordPress >
Plugin Extras**, and the fields are in Properties and **File > WordPress >
Plugin Fields...**.

- **The Events Calendar.** **Events Coming Up...** lists every event from
  today, with when and where. **New Event...** makes a draft event and opens
  it. An event's start, end and venue show in Properties and can be changed
  in Plugin Fields.
- **WooCommerce.** A product's price and stock show in Properties and can be
  changed in Plugin Fields; a price change asks first. **Shop Orders...**
  lists the newest orders, to read. QUILL never changes an order, and copies
  one only after asking, because it holds the customer's name and address.
- **Yoast SEO and Rank Math.** The SEO title and description show in
  Properties with their length, and in Plugin Fields a line under each keeps
  the count, telling you when the text goes over what search engines show.

## AI Abilities and Ask the Site

WordPress 6.9 lets a site offer actions to AI, called abilities, such as
"list upcoming events" or "create a draft".

- **Tools > WordPress > Manage > AI Abilities...** lists each ability your
  site offers, by name. Every ability is off until you turn it on, one by
  one, for that site.
- **Tools > WordPress > Manage > Ask the Site...** sends your question to
  the AI you chose in Choose Your AI. If the AI wants to use an ability,
  QUILL asks you first, every time, and says exactly what it will be given.
  The answer ends by saying what ran on your site.

## Across all your sites

These are in **Tools > WordPress > Your Sites**, and look at every site you
have connected:

- **Coming Up...** lists everything scheduled on all your sites, soonest
  first.
- **What Changed on My Sites...** lists new comments, posts other people
  published, and health warnings since you last looked, across every site.
  It only appears when you ask; QUILL never interrupts you with it. Run it
  again and it says nothing is new.

## Where to next

- Previous: [Chapter 6: Checking before you publish](wordpress-forms-06-checking.html)
- Next: [Chapter 8: Writing a form](wordpress-forms-08-writing-forms.html)
- [Contents](wordpress-forms-guide.html)
