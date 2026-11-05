# Chapter 1: Getting started and adding your sites

## What this chapter covers

This chapter gets you from nothing to a connected WordPress site. It explains
what QUILL and QUILL Lite do with WordPress and what they leave alone, how to
turn the feature on, where the commands live, and how to connect a site: with
your browser, by pasting an application password, on WordPress.com, and when
you look after more than one site. It ends with what your role on a site
means, and how to sign out of a site for good.

## What WordPress in QUILL is

If you look after a WordPress website, QUILL can write its pages and posts,
open the ones already there, and publish your changes. You do it in the same
editor you use for everything else, with Find, spelling, dictation, Read
Aloud, bookmarks and all your usual keys. Everything in this manual works the
same way in QUILL Lite.

Three promises run through the whole feature:

- **Nothing reaches your site until you send it.** Saving with Ctrl+S only
  ever saves on your computer. Sending is always a separate command, and
  publishing always asks first.
- **Your site keeps its look.** QUILL works on the words and pictures inside
  your pages. Your theme, its layout and its design stay in WordPress.
- **Nothing is deleted for good without a copy first.** Pages go to
  WordPress's own Trash. The one thing WordPress cannot put in a Trash, a file
  in the Media Library, is copied to your computer before it goes.

QUILL talks to your site through WordPress's own REST API, the same doorway
the block editor uses. You do not need to install a plugin for anything in
this manual except forms, which need the QUILL Accessible Forms plugin on
the site (Chapter 9 explains why).

## Turning it on

WordPress and Forms are two separate features, and each can be switched on
or off on its own.

**In QUILL,** both are on in every feature profile except Essential. If you
do not see **File > WordPress**, choose another profile in **Profiles and
Features...**, or switch on WordPress by itself there. Forms works the same
way.

**In QUILL Lite,** WordPress and Forms are areas. Both are on in the
Recommended, Everything and Developer profiles, and off in WordPad and
Notepad, because neither of those programs ever published to a website or
made a form. To turn one on without changing profile, check it in
**Tools > Customize Features**.

**Safe Mode** turns WordPress off, along with the other features that use
the network. If you started QUILL in Safe Mode, every WordPress command says
"WordPress is off in Safe Mode. Start the app normally to use it." Forms is
partly different: writing, checking, trying out and saving a form to paper
still work in Safe Mode, because they never leave your computer.

## Where everything is

The commands sit where a Word user would look for them. Anything about a
whole page or post, or about your sites, is in **File > WordPress**. What you
do inside a page joins the ordinary menus. Looking after the site itself is
in **Tools > WordPress**.

| Menu | What is there |
|---|---|
| File > WordPress | New, Open, the three saves, Properties, versions, Trash, Send and Copy, your sites |
| Edit > WordPress | Next Block, Previous Block, Where Am I, and two link tools |
| View | WordPress Blocks, Preview Blocks, Block Notes, Play Media Here |
| Insert | Blocks, pictures, links to your own pages, notes, icons, Make a Picture |
| Format > WordPress | Block Settings, Image Size, Mark Language |
| Tools > WordPress | Checking, the Media Library, comments, menus, settings, and five submenus |

The five submenus of Tools > WordPress are More Media, Design, Plugin
Extras, Manage and Your Sites.

**Dimmed rows.** The commands about the page in front of you are dimmed
unless a WordPress page or post is open. If you reach one another way, such
as from the Command Palette, QUILL tells you why it cannot run and how to
open one, for example "Insert Block works in a WordPress page or post. Open
one with File, WordPress." The site-wide commands, such as Comments or the
Media Library, work from anywhere, and ask which site when you have more
than one.

**The Command Palette** (Ctrl+Shift+P) lists every WordPress command. Type
"WordPress", or part of a command's name, and press Enter. It is in the
Tools menu in both editors.

**The WordPress keys.** The everyday commands also have a key each: press
Ctrl+Alt+Shift+Grave, let go, and press one letter. Chapter 12 has the whole
table. You do not need them to get started.

## What you need before you connect

You need three things:

- **Your site's address,** for example `https://example.org`. It must start
  with https. QUILL never sends a password to a site over plain http.
- **Your WordPress username,** or the email address you sign in with.
- **An application password.** This is a separate password WordPress makes
  for one app. It is not the password you sign in with. It is made of 24
  letters and numbers, usually shown in groups of four, and you can take it
  away again at any time from your WordPress profile without changing your
  real password.

You do not need to make the application password yourself if your site is
reasonably new. QUILL can ask your site for one through your browser, and
the site hands it straight back.

## Connecting a self-hosted site with your browser

This is the easy way, and the one to try first.

1. Choose **File > WordPress > Connect a Site...**. The Connect a WordPress
   Site window opens on **Kind of site**.
2. Leave Kind of site on **My own WordPress site (self-hosted)**.
3. Tab to **Site address** and type your site's address, for example
   `https://example.org`.
4. If you like, Tab to **Name for this site** and type a short name, such as
   "Community Radio". QUILL uses it in every list and every confirmation.
   Leave it empty to use the site's own title.
5. Press **Get Password with My Browser**.

Your browser opens your site's own Authorize Application page. Sign in there
if it asks. The page names QUILL as the app asking for a password. Choose
**Approve**.

What happens next depends on how new your site is:

- **On a newer site,** the password comes straight back to QUILL, which
  checks it, saves it and says "Connected to Community Radio as Editor", with
  your own site name and role. You can close the browser tab.
- **On an older site,** WordPress shows you the new password on its own
  page, with a Copy button. Copy it and come back to QUILL, where a small
  window, Paste the Application Password, is waiting with one field. If the
  password is already on your clipboard, QUILL has put it in the field for
  you. Press Connect.

Either way, the password never passes through anything but your browser,
your site and your own computer. It is kept in Windows' own Credential
Manager, never in a settings file.

**If the site has application passwords turned off,** usually by a security
plugin, QUILL says so in one sentence: "Application passwords are turned off
on Community Radio. Ask the site's administrator to turn them on."

## Connecting by pasting an application password

Use this when the browser route does not suit you, or when your site's
administrator gave you a password.

1. In your browser, sign in to your site and open your profile. In the
   WordPress dashboard that is **Users > Profile**.
2. Find the **Application Passwords** section near the bottom. Type a name
   such as "QUILL on my laptop" and press **Add New Application Password**.
3. WordPress shows the new password once. Copy it.
4. In QUILL, choose **File > WordPress > Connect a Site...**.
5. Type the site's address, then your **Username**, then paste the password
   into **Application password**.
6. Press **Connect**.

QUILL checks the connection before it saves anything. It asks the site who
you are and what the site is called, so a wrong password is caught here, in
words, and not the first time you try to publish. When it works you hear
"Connected to" the site's name, "as" and your role.

If it does not work, the Connect window opens again with a **Problem** field
at the top saying what went wrong, and everything you typed is still there.
The commonest sentences are:

- "Community Radio did not accept the application password. Check it belongs
  to this account, then reconnect." The password was made under a different
  user, or a character was lost when you copied it.
- "Community Radio does not know that username. Check it and reconnect."
- "QUILL only connects to WordPress sites over HTTPS, so your password is
  never sent in the clear. Check that the address starts with https://."
- "A security setting on Community Radio blocked QUILL. Ask the site's
  administrator to allow the WordPress REST API and application passwords."

Chapter 11 has the rest, with what to do about each one.

## WordPress.com sites

The Connect window offers a second kind of site, **A WordPress.com site**.
Choosing it greys out the username and password fields, because a
WordPress.com site is meant to be connected by signing in to WordPress.com
in your browser, on every plan, the free one included, with nothing to
install.

That sign-in needs QUILL's own WordPress.com app registration, and this
build does not have it yet. If you choose A WordPress.com site and press
Connect, QUILL says: "WordPress.com sign-in is not available in this build
yet. If your WordPress.com plan allows plugins, connect with an application
password at your site's own address instead."

So, for now:

- **On a WordPress.com plan that allows plugins,** your site accepts an
  application password at its own address. Choose My own WordPress site,
  type your site's address, and connect with the browser or by pasting, as
  above. Everything in this manual then works.
- **On a plan without plugins,** wait for the build that brings WordPress.com
  sign-in. When it comes, you will choose A WordPress.com site, press Get
  Password with My Browser, approve QUILL on WordPress.com, and sign in once.
  QUILL will keep you signed in from then on.

## Looking after more than one site

Connect each site the same way. There is no limit, and you can connect the
same site twice with two different accounts, for example as yourself and as
a test author.

**File > WordPress > Sites...** lists every site you have connected. Each
row gives the site's name, its address and your role there. From the list
you can:

- **Rename** a site, which changes only what QUILL calls it;
- **Verify** it, which checks the password still works and says "Community
  Radio accepts QUILL. You are Editor there.";
- **Make Default**, so New and Open start there;
- **Remove** it, which forgets the connection on this computer. Nothing on
  the site changes, and your local drafts for it stay.

The list also names the application password QUILL is using on each site,
so you can match it to the one in your WordPress profile.

**File > WordPress > Switch Site...** is the quick way to change your
default site. It opens a short list, and you hear "Default site:" and the
name you chose.

**A document always stays with the site it came from.** Switching the
default never moves an open page to another site. Every confirmation names
the site as well as the page, for example "Publish 'Spring Workshop' to
Community Radio?", which matters most when two of your sites have pages with
the same title. And if you publish a page to a site that is not your
default, Check Before Publishing reminds you: "This goes to Community Radio,
not your default site, Home Blog."

## What your role on a site means

WordPress gives every account a role: Administrator, Editor, Author,
Contributor or Subscriber. QUILL asks the site what your account may do
before it opens a window.

- **If your role cannot use a window at all,** you hear one sentence, such
  as "Your account on Community Radio is an Author, which cannot manage
  users", and nothing opens.
- **If it can use part of a window,** you only get the buttons that will
  work.
- **If you are a Contributor,** you cannot publish yourself. Publish or
  Update sends your post for review instead, and says so. An Editor or
  Administrator then publishes it.
- **If the site refuses something anyway,** you hear why in words, such as
  "Your account on Community Radio can only change items you wrote
  yourself."

## Signing out of a site

Removing a site from Sites only forgets it on this computer. The application
password still exists on the site.

**Tools > WordPress > Manage > Sign Out This Site...** goes further. It
revokes the exact application password QUILL is using on that site, so it
stops working everywhere, and forgets it on this computer. It asks whether
to remove the site from QUILL as well, or keep it so you can connect again
later. Your local drafts stay either way.

Use it when you give away a computer, or when you stop looking after a site.

## If you used Publish in QUILL before

Older versions of QUILL had a Publish submenu in the File menu. It is gone,
and File > WordPress does everything it did. Your saved connections are not
lost: QUILL brings them in the first time WordPress loads, with the same
saved passwords, and documents you opened from a site stay linked to it.

## Learn it with a guided lesson

**Help > Tutorials** has a WordPress track in both editors, seven lessons
that use a real test site. The first, Connect your WordPress site, walks
through everything in this chapter step by step and tells you what you
should hear at each step.

## Where to next

- Next: [Chapter 2: Writing and publishing posts and pages](wordpress-forms-02-writing-and-publishing.html)
- [Contents](wordpress-forms-guide.html)
