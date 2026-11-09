# Chapter 12: Your files, updates and QUILL for All

This chapter is about QUILL Lite's place on your computer. You will learn
where it keeps your settings and recovered work, how a portable copy keeps
everything on the stick, and how to get a new version when one comes out.
Then we will look at how QUILL Lite sits beside its bigger sibling, QUILL for
All, and how to share what you have built up between them.

## Where your files are kept

QUILL Lite keeps your settings, your recent files, your copy tray and any
recovered work in a QUILL Lite folder inside your own Windows user folder. To
find out exactly where, open **Help > About QUILL Lite**. It tells you.

This folder is separate from QUILL for All's folder. QUILL Lite and QUILL are two
different programs, so you can install or remove one without touching the other.

When you uninstall QUILL Lite, this folder stays. That way, if there is a
recovered document you have not finished with, it is still there for you.

### The portable copy keeps everything on the stick

The portable QUILL Lite is the `.zip` you unpack instead of installing. If that
is the one you use, everything above works differently: all your settings and
recovered work go into the `data\QuillLite` folder inside the bundle, right next
to `QuillLite.exe`. Nothing at all is written to the computer you are plugged
into. This happens from the very first time you start it. There is nothing to
switch on.

#### If you used a portable copy before version 1.0

Older portable copies did not work this way. They kept their files in
`%LOCALAPPDATA%\QuillLite` on whichever computer you were using, and they did
not tell you. So if you have been carrying a portable QUILL Lite around, and
something you were working on seems to be missing, look in that folder on the
computer you used. Once you have what you need out of it, it is a good idea to
delete that folder, especially if the computer is not yours.

#### Turning a portable copy back into an ordinary one

The `data` folder is what makes a copy portable. Delete the `data` folder from
the bundle, and QUILL Lite goes back to keeping its files in your Windows user
folder on this computer.

## Keeping QUILL Lite up to date

To find out whether there is a newer QUILL Lite, open
**Help > Check for Updates...** (**Ctrl+Alt+U**). Every app in the QUILL family
uses this same key and the same window, so once you know it here, you know it
everywhere.

If you already have the newest version, a small window tells you so. You always
get an answer.

Help > About shows your version with a build number, such as 2.0.0 (build 1). The
build number tells you which build of a version you have: when a fix comes out
without a new version number, it is a newer build, and Check for Updates offers it.

### What changed: Help > What's New

**Help > What's New** (press **Alt+H**, then **W**) opens QUILL Lite's
changelog in your web browser: every change, newest first. It has no shortcut
key, as in QUILL, because you read it once after an update rather than every
day. Every app in the QUILL family has the same item in its Help menu; in the
apps other than the two editors it is on **Ctrl+Shift+F1**.

### The guides: Help > Open User Guide and Open GitHub Guide

**Help > Open User Guide** (**Ctrl+Shift+F1**, the same key as in QUILL) opens
this guide in your web browser, starting at its contents page.

**Help > Open GitHub Guide** (press **Alt+H**, then **I**) opens the GitHub
Guide, the book about doing GitHub work in QUILL Lite with a screen reader. It
has no shortcut key, as in QUILL, because you open a manual to learn rather than
while you write. Pressing **F1** in GitHub Items, Explore GitHub or the review
window offers it too: Tab to **Open GitHub Guide** and press it.

Both guides come with every QUILL Lite download, the portable copy and both
kinds of installation, and the Start menu has a shortcut to each.

### With every document closed

If you close the last document, QUILL Lite's window stays open with a full
menu bar of what works without a document: **File** (New, New Rich Text
Document, New Plain Text Document, Open, Recent Documents, Reopen Last Session
and Exit), **Tools** (Preferences, the Keyboard Manager, the Sound Scheme and
backing up or restoring your settings) and **Help** (Help for This Window,
Tutorials, Keyboard Shortcuts, Open User Guide, Open GitHub Guide, Get Help
from Support, Check for Updates, Release Channel, What's New and About). The
keys are the same ones the document windows use, including any you have
changed, and a feature you switched off in Customize Features is off here too.
Activity and Repeat Last Result need a document window.

### Opening QUILL Studio

When Studio is available in your build, **Tools > Open QUILL Studio**
(**Alt+T**, then **Q**) opens it in its own window. This also works with every
document closed. It does not send your document to Studio, start recording, or
download anything. If Studio cannot be opened, QUILL Lite tells you; your
document stays unchanged. You can assign a personal shortcut in Keyboard
Manager. Studio is currently limited to developer builds, not public releases.

### When there is a new version

If there is something newer, the window opens on the release notes for that
version, so you can read what changed. They are in a read-only box you can
arrow through like a document. Press **Tab** to reach two buttons:

- **Update** downloads the new version and then offers to install it. Your
  settings, recent files and recovered work are kept whichever you choose:
  - **Install and restart now** (Enter) closes QUILL Lite, installs the update
    and opens QUILL Lite again.
  - **Install when I close** (Alt+C) lets you keep writing. The update goes in
    the next time you close QUILL Lite, and the next time you open it, you have
    the new version.

  A portable copy updates itself where it is. The new version takes the old
  folder's place and your `data` folder moves across untouched; the old
  version is kept beside it, in a folder ending in `.previous`, until the new
  one has started three times or for a week. The installer updates quietly and
  doesn't ask for administrator permission, because QUILL Lite is installed
  for you alone.
- **Close** leaves everything as it is. Nothing is downloaded until you press
  Update.

While it downloads, you hear when it is a quarter done, half done and three
quarters done, and then when it has finished.

### The daily check

QUILL Lite also looks for a new version once a day, when it starts. It stays
quiet while it looks, quiet if there is nothing new, and quiet if you are not
online. You only hear from it when there really is a new version, and even then
it just offers. Nothing changes until you say so.

If you would rather it did not look at all, turn off "Look for updates when
QUILL Lite starts" in **Settings**. **Ctrl+Alt+U** still works whenever you
want to check yourself.

## Release channels

QUILL Lite comes in three flavours, and you choose which one your copy follows.
They are called release channels.

- **Stable** is the version we recommend. It has been checked with JAWS and
  NVDA, and it is what most people use. Every copy starts here.
- **Beta** gets new features a few weeks early. It is mostly finished, but some
  things may not work right yet.
- **Dev** is the work in progress, sometimes several builds a week. Things will
  break. Only choose it if a developer asked you to, or you enjoy testing.

### Choosing a channel

Open the **Help** menu, then choose **Release Channel...** (press **Alt+H**,
then **C**). You can also get there
from **Settings**, with the **Change release channel...** button under "Look
for updates when QUILL Lite starts".

Arrow through Stable, Beta and Dev. As you move, the box below tells you what
each one means and what choosing it would do. Nothing changes yet. Press
**Switch** to move, or **Close** (Escape) to leave everything as it was.

If you choose Beta or Dev, a short warning comes first: what could go wrong,
how your settings are protected, and how to come back. Read it, check the **I
understand** box, then choose **Move to Beta** (or **Move to Dev**). **Stay on
Stable**, or Escape, changes nothing.

Beta and Dev versions aren't signed, so when you install one, Windows
SmartScreen may warn that it comes from an unknown publisher; that's expected,
and choosing **More info**, then **Run anyway**, installs it.

Before it moves, QUILL Lite saves a copy of your settings, keys and recent
files list. If it cannot, it stays where it is and tells you why. Your
documents are not copied, and updates do not change them. Then it checks for
updates on the new channel straight away, and offers you the newest version
there if there is one. Nothing is installed unless you say so.

### When Quill Radio or QUILL Cast is installed too

QUILL Lite, Quill Radio and QUILL Cast run on one shared engine on your
computer. When an app moves to Beta or Dev, it gets its own copy of that
engine, so the apps you leave on Stable are never touched. You can still move
several at once: check them under "Also move my other QuillVille apps on this
computer" and choose **Switch**.

That second copy of the engine takes about 335 MB of disk space. It goes away
by itself when your last app comes back to Stable. A portable copy carries its
own engine, so it needs no extra space.

### Updates on Beta and Dev

On Beta and Dev, QUILL Lite downloads a new version quietly when its daily check
finds one, so it is ready when you are. It never installs anything without
asking: when the download is done, it says so and shows you what's new, and you
choose when to install.

It waits instead of downloading on a metered connection, during Quiet Hours,
and while Quill Radio is recording. Update History tells you why it waited. On Stable nothing
changes.

### If an update doesn't start

After an update, QUILL Lite checks that the new version really opens. If it doesn't
open within two minutes, the update undoes itself and puts back the version you
had. If the new version is still running but stuck, it is closed first. The next
time QUILL Lite starts, it tells you so. Nothing of yours is changed, and Update
History has the details.

If the installer itself doesn't finish, nothing is changed at all: QUILL Lite
opens again straight away as the version you had, and tells you the update could
not be installed.

To make this possible, QUILL Lite keeps a copy of the installer for the version you
have: on Beta and Dev for as long as you have that version, and on Stable for a
week or three starts after each update. That copy takes about 200 MB of disk
space, which Stable gives back once the week or the three starts are up. After
an update, the previous installer is kept until the new version has started
three times, or for a week, and then it is deleted.

### Coming back to Stable

Open **Release Channel** again and choose **Stable**.

- If the version you have is already a Stable one, you're back straight away,
  and nothing is installed.
- If you have a newer Beta or Dev version, QUILL Lite checks whether Stable can read
  everything you have saved. If it can, choose **Go back to** (the Stable
  version) **now**, and QUILL Lite downloads Stable and offers to install it. Your
  settings come with you. If a few settings were only in Beta, they go back to their usual values,
  and the window tells you which.
- If Stable can't read something yet, QUILL Lite says so and gives you two safe
  choices. **Wait for Stable** keeps the version you have, stops test versions,
  and moves you to Stable by itself as soon as Stable catches up. It tells you
  when that happens. **Use the copy from** (the day you joined) puts back the
  copy of your settings saved when you joined, then installs Stable.
  Anything you changed since then won't be in it, but a copy of how things are
  right now is saved first, so nothing is thrown away.
- If there's no saved copy, waiting is the only choice, and the window says so.

The **Update History** button in the same window shows what the updater has
done for QUILL Lite. And switching sends nothing about you: the only thing QUILL
Lite ever sends when it checks for updates is a request for the list of
versions.

## What QUILL Lite is not

QUILL Lite is a companion to **QUILL for All**. It is not meant to replace it.

If you want to convert documents, compare two documents, publish, or use braille
tools, those are in QUILL. QUILL Lite stays a small, focused text editor on
purpose.

### Dictation

QUILL Lite has
[dictation](lite-guide-09-writing-by-voice.html#chapter-9-writing-by-voice):
built-in speech recognition that writes each phrase when you pause. QUILL has
the very same feature on the same keys, under Tools > Speech > Live Dictation.
QUILL's offline Locked Dictation, which records a passage and then transcribes
it with a model you download, is only in QUILL.

### AI

QUILL Lite has AI (artificial intelligence) help, described in
[Chapter 10, AI help](lite-guide-10-ai-help.html#chapter-10-ai-help). It can summarize,
rewrite, proofread and explain, answer a question about the document you have
open, and a few more things that chapter walks you through. It is there so you
can get through a long document, or check your writing, without having to read
every line yourself.

Some of QUILL's AI stays in QUILL: running a model on your own computer, the
agents, and the picture description work. If you want those, QUILL has them.

Both programs are free, both are made for people who use a screen reader, and
you can install them side by side.

### Sharing what you have built up between them

QUILL Lite keeps its own settings, separate from QUILL's. That way it starts
small and simple, and removing it never takes anything away from QUILL. But the
things you collect over time, like abbreviations and words you have taught the
spell checker, are nice to have in both. So you can choose to share them:

- In Preferences, **Share QUILL's abbreviations** and **Share QUILL's personal
  dictionary** make QUILL Lite use QUILL's copies. A short form you add, or a
  word you teach, in either editor is then there in both.
- In QUILL, **Tools > Customize and Support > Bring My QUILL Lite Settings...**
  does it all in one step. It adds your QUILL Lite abbreviations, dictionary,
  copy tray, clip library and bookmarks into QUILL, turns those sharing
  switches on for you, and copies your preferences and any keys you changed
  across once. Nothing already in QUILL is replaced, and nothing is removed
  from QUILL Lite.

### A QUILL that feels like QUILL Lite

QUILL also has a **QUILL Lite profile** (in QUILL, Preferences > Profiles and
Features). It makes QUILL show just these nine menus, and makes Ctrl+N create a
plain text document, the way QUILL Lite does. It is there for the day you want
one of QUILL's extra tools but would like everything to still feel familiar.

## What you learned, and where to go next

Your settings and recovered work live in your own user folder, and **Help >
About QUILL Lite** tells you where. A portable copy keeps everything on the
stick instead. **Ctrl+Alt+U** checks for a new version, shows you what
changed, and lets you install now or when you close. QUILL Lite also checks
quietly once a day, and you can turn that off in Preferences.

QUILL Lite is the small editor, and QUILL for All is the big one. They work
side by side, and you can share your abbreviations, dictionary and more
between them. If you are setting up a new computer, *Taking your settings
with you*, in Chapter 11, shows you how to bring your settings along.

Next, Chapter 13, When you need a hand, tells you what to do when you are
stuck.

---

- Previous: [Chapter 11: Making QUILL Lite yours](lite-guide-11-making-quill-lite-yours.html)
- Next: [Chapter 13: When you need a hand](lite-guide-13-when-you-need-a-hand.html)
- [Contents](../userguide.html)
