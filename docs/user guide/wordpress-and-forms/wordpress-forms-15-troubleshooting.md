# Chapter 15: Troubleshooting

## What this chapter covers

Something did not work, and you want to know why and what to do. QUILL never
answers a problem with a bare error code. Every failure is one sentence that
names the site and says what happened, and usually what to do.

This chapter collects those sentences, grouped by when you meet them, with
the reason behind each and the fix. If you hear something not listed here,
it will still name the site and the cause. The sections below are the ones
people meet most. By the end you should be back at work.

## Before you start: three quick checks

Most problems are one of these:

1. **Is the feature on?** If File > WordPress or File > New Form is missing,
   switch the feature on (Chapter 1, or Chapter 14 for QUILL Lite).
2. **Are you in Safe Mode?** Every WordPress command says "WordPress is off
   in Safe Mode. Start the app normally to use it." Restart QUILL normally.
3. **Is a WordPress page in front of you?** The page commands are dimmed
   otherwise, and from the Command Palette they say, for example, "Insert
   Block works in a WordPress page or post. Open one with File, WordPress."

## Connecting

**"QUILL only connects to WordPress sites over HTTPS, so your password is
never sent in the clear. Check that the address starts with https://."**
The address starts with http. Type it with https. If your site has no HTTPS
at all, ask your host to turn on a free certificate; almost every host
offers one.

**"Community Radio did not accept the application password. Check it
belongs to this account, then reconnect."** The password was made under a
different user, was revoked, or lost a character on the way. Make a new one
with Get Password with My Browser, or in your profile, and connect again.

**"Community Radio did not accept the sign-in. Check the username and
application password, then reconnect."** The same, or the username is
wrong. You can use your email address instead of your username.

**"Community Radio does not know that username."** Check the spelling, or
use your email address.

**"Application passwords are turned off on Community Radio. Ask the site's
administrator to turn them on."** A security plugin, or the host, has
switched application passwords off. The administrator can turn them on in
that plugin's settings.

**"A security setting on Community Radio blocked QUILL. Ask the site's
administrator to allow the WordPress REST API and application passwords."**
A security plugin is blocking the REST API, which QUILL needs. The
administrator can allow it, usually for signed-in users only, which is all
QUILL needs.

**It connects, then everything says the sign-in was not accepted.** Run
**Tools > WordPress > Site Check**. If the authorization header test fails,
your host is stripping the header that carries the password. Site Check
says so; your host can fix it, and many hosts have a help page for exactly
this.

**"Community Radio's security certificate could not be checked, so QUILL
did not connect."** The site's HTTPS certificate has expired or does not
match the address. Waiting will not fix it; tell the site's host. QUILL
never connects past a bad certificate, because that is how a password is
stolen.

**"QUILL could not find Community Radio. Check the address, and that you are
online."** The address has a typo, or you are offline.

**The browser approval page never sends the password back.** Older sites
cannot hand the password back to QUILL. WordPress shows it on the page
instead, with a Copy button: copy it, and paste it into the Paste the
Application Password window QUILL has open. If you closed that window, press
Connect a Site again and paste the password into Application password, with
your username.

**"QUILL stopped waiting for the browser."** You took longer than QUILL
waits. Press Get Password with My Browser again when you are ready.

**WordPress.com.** "WordPress.com sign-in is not available in this build
yet." See Chapter 1: on a plan with plugins, connect with an application
password at your site's own address.

## What your role allows

**"Your account on Community Radio is an Author, which cannot manage
users."** The window needs a higher role. Ask an administrator to do it, or
to change your role.

**"Your account on Community Radio cannot publish this. You can save it as a
draft, or submit it for review."** Contributors cannot publish. Publish or
Update sends the post for review instead. An Author cannot publish pages.

**"Your account on Community Radio can only change items you wrote
yourself."** Authors and Contributors can edit only their own posts.

**"Only an administrator on Community Radio can change site settings."**
Site Settings, Site Logo, plugins, themes and users are for
administrators.

## Opening and sending

**"That address is not on any of your connected sites."** Open by Web
Address only opens pages on sites you have connected. Connect the site
first.

**"QUILL could not find a page or post at that address on Community
Radio."** The address is an archive, a category or the home page listing
posts, which are not single pages.

**"That page or post is no longer on Community Radio. It may have been
deleted."** Someone deleted it, or moved it to the Trash. Look in Open with
`trash` in Find.

**The site's copy changed.** Somebody changed the page after you opened it.
Nothing was sent. Choose Compare the two, Open the site's copy, or Send mine
anyway (Chapter 3).

**"Community Radio took too long to answer."** The site is slow or your
connection dropped. QUILL checks the site before offering Try Again, so
nothing is created twice. If the site cannot be reached at all, your send is
queued and goes through when it answers.

**"Community Radio is asking QUILL to slow down. Wait a minute and try
again."** The host limits how many requests come at once, which a large
Check the Whole Site can reach. Wait, then carry on.

**"Community Radio had a problem of its own (error 500)."** The site itself
failed, often a plugin. Try again in a moment; if it keeps happening, the
site's error log will say why.

**"N lines could not be turned into blocks; Check Before Publishing lists
them."** A `:::` fence has a typo. Check Before Publishing names each line.

**The page looks unchanged after an update.** Your site or your host may be
showing a cached copy. Wait a minute, or clear the cache in your caching
plugin.

## Pictures and media

**"That file is bigger than Community Radio accepts."** Make a Smaller Copy
for a picture. For a long recording or a video, the limit is your host's:
ask them to raise it, or make the file smaller. WordPress cannot take a file
in pieces, so there is no way round the limit from QUILL.

**"Community Radio has no room left for uploads."** The site or your plan is
full. Space Used (Tools > WordPress > Manage) shows what takes the room.

**An upload was not confirmed.** QUILL checks the Media Library for the file
before offering to upload again, and asks whether to use the copy already
there, so you do not end up with two.

**Video plays with no picture.** The playback engine cannot show a picture on
this computer. The player says so once; Open in Browser shows it.

**Visual Review or Check This Page says it cannot run.** They need Microsoft
Edge or Google Chrome installed in its usual place. QUILL never downloads a
browser. They also work only on published pages.

## Commands a site does not offer

QUILL asks each site what it offers before it tries anything. A feature
that needs a newer WordPress, a block theme, or a route a security plugin
has hidden says so in one sentence, and nothing is sent. Appendix A lists
every feature, what it needs, and what you hear when a site lacks it. The
usual fixes are to update WordPress, or ask the administrator whether a
security plugin is hiding part of the REST API.

## In the Workbench

**A command is dimmed.** Your role on the site cannot use it, or your
Workbench access for the site is Read Only or Organize. Press Shift+F1 for
What Can I Do Here?, which says what each command needs. **Site > Workbench
Access...** changes your access. Safe Mode and View As Role make every site
read only.

**"Nothing was sent", because somebody changed it.** Before every change,
QUILL reads the item again. If it changed on the site since your list loaded,
perhaps in wp-admin, QUILL sends nothing and says what changed. Press F5 and
try again.

**Delete or Ctrl+Z did nothing.** They act on the list only. In the filter box
or any other box you type in, they edit your text. Tab or F6 back to the list
first.

**A list seems short.** Long lists load three hundred rows at a time. Press
Ctrl+Shift+L for more, or Ctrl+Alt+L for all of them. The status bar says
how many are shown.

**"Not reported over REST", in Updates.** WordPress does not tell apps
whether an update is waiting. Enter on the row opens the site's Dashboard,
Updates, where it does.

**Replace File gave the file a new address.** The site has no way to swap a
file in place, so QUILL uploaded the new file and pointed every page at it.
Links from other websites and old emails still go to the old address. If the
site has the Redirection plugin, add a redirect from the old address to the
new one in Redirects (Chapter 10). If not, keep the old file in the library
so those links still work.

**"No redirect was added: the Redirection plugin has no group to keep it
in."** The plugin is installed but has not been set up. Open its screen in
wp-admin once, under Tools, Redirection, and finish its setup.

**A WXR file "did not pass its check".** The file was written, but did not
read back as a proper WordPress export. It is kept, so you can look at it.
Try again with a smaller part of the site, such as Posts only, and tell us if
it happens again.

**"has nothing Community Radio can take as a draft."** The WXR file holds no
posts, pages or kinds of content your site has. A WXR made of only menus or
media looks like this.

**Imported drafts still show the old site's pictures.** You chose to skip the
files. Press Ctrl+Z to move those drafts to the Trash, then import again and
choose to download the files.

**The Practice Site will not start.** If QUILL says port 9400 is in use,
something else on this computer is using it. Close it, or restart Windows,
and try again.

## Forms

**"Check This Form works in a form document, a .qaf file."** The document in
front is not a form. Open a `.qaf` file, or start one with File > New Form.

**"Publish Form needs QUILL Accessible Forms on Community Radio, and the site
does not offer it."** Install and activate the plugin (Chapter 12), or use
Save As Web Page.

**"Publish Form stopped: this form has 2 problems to fix first."** Run Check
This Form; the problems QUILL could not read are listed first.

**A rule never fires.** Check the rule's sentence in Form Rules. If it
compares with an answer, make sure it matches one of the question's choices.

**Fill It In Yourself shows no choices for a question.** The question names
a choice library the form does not have. Check This Form names it.

**"Publish Form is off in Safe Mode."** Restart normally. Writing, checking
and saving to paper still work in Safe Mode.

## Still stuck

- Press F1 on any control for what it is for.
- **Help > Tutorials** has guided WordPress and Forms lessons on a test site,
  which tell you what you should hear at every step.
- Write to support@community-access.org with what you did and what you heard, word for word.
  That one sentence is usually all anyone needs.

## Where to next

- Previous: [Chapter 14: QUILL Lite](wordpress-forms-14-quill-lite.html)
- Next: [Chapter 16: Every WordPress and Forms key](wordpress-forms-16-keys.html)
- [Contents](wordpress-forms-guide.html)
