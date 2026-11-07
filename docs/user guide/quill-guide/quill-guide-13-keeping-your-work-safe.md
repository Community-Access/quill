# Chapter 13: Keeping your work safe

This chapter is about the things QUILL does so you do not lose work: saving
snapshots as you type, keeping every earlier save, offering your text back
after a crash, and asking before anything is thrown away. Most of it runs on
its own, and you never have to think about it. Read it once so you know the
safety net is there, and come back when something has gone wrong and you want
to know what your choices are.

## Trust, Recovery, Sessions, and Safety

QUILL takes recovery and your control over your own work seriously. Here is
the short version before the details:

- Autosave snapshots your documents on a timer, and a backup copy is taken
  just before each save.
- Every save also keeps a restore point, so you can bring back any earlier
  version, days or weeks later.
- If QUILL closes unexpectedly, the next launch offers your unsaved work back.
- If your screen reader stops, QUILL saves everything at once and keeps
  running.
- A question that would destroy something always has **No** as its default.
- Safe mode, safety advisories and update notices are there for the rare day
  something is not right.

The rest of this chapter takes these one at a time, everyday things first.

## Autosave and backups

QUILL autosaves at a timed interval and keeps backup snapshots. It skips a
write when nothing has changed since the last one. The autosave is written in
the background, so even a large document is snapshotted without a pause in
your typing.

### When the disk is full

This needs its own explanation, because getting it wrong once cost somebody a
document.

QUILL writes your text in three places: the **file itself** when you save, a
**backup copy** taken just before that save, and an **autosave snapshot** on a
timer. Only the first of those is your document, so QUILL follows four simple
rules:

- **A backup can never stop a save.** The backup is there to protect you from
  a bad save, so a failed backup must not cancel the save. If the backup cannot
  be written, QUILL says "Could not write a backup; saving anyway" and saves
  your file. When it knows why, the reason is in the sentence too, for example
  "Could not write a backup (No space left on device); saving anyway". The
  failure is also written to QUILL's log, with the document's name and the
  reason, so if you later find there is no backup to go back to, the bundle
  from **Help > Save Diagnostics...** has the answer even though the spoken
  message is long gone.
- **A failed save is explained in words you can act on.** You will not hear
  "[Errno 28] No space left on device". You will hear "The disk is full. QUILL
  could not save notes.md. Free some space and try again; your text is still
  open and unsaved." A file or folder that is read-only, or held open by
  another program, gets its own message pointing you at **File > Save As**.
- **A failed save never closes the window.** If you choose **Save** on the
  closing prompt and the save fails, the close is cancelled and QUILL tells you
  why, so you can free some space or save somewhere else. Closing a second time
  goes ahead, so the window can never be trapped open, but you will have been
  told first.
- **Autosave says when it has stopped.** If autosave failed quietly, your
  crash-recovery net would be gone and nothing would tell you. After two
  failures in a row, QUILL says once: "Autosave paused: the disk is full. Your
  work is not being snapshotted." It goes quiet again as soon as autosave
  works.

Backups are written the same way autosave snapshots are: completely or not at
all, so a half-written backup can never be the thing you restore. They are
always written as UTF-8, so a document QUILL opened in a narrower encoding
still backs up after you type an accented character. Backups made by earlier
versions still restore normally.

## Restore points, bring back any earlier save

Every time you save, QUILL quietly keeps a snapshot of the document. To get
one back, choose **File > Restore Previous Version...** (`Ctrl+Alt+Shift+E`).
The list reads in plain language, newest first, for example "Today at 4:12 PM
- 2,341 words".

1. Open **File > Restore Previous Version...**.
2. Arrow to the version you want.
3. Choose one of the two buttons:
   - **Restore** puts that version in the editor in place of your current
     text. Your current text is saved as a restore point first, so you can
     undo a restore the same way. The document is marked modified, so nothing
     touches the disk until you save.
   - **Open as Copy** opens the earlier version as a new untitled document and
     leaves your current one exactly as it is. This is the one to use for
     comparing, or for rescuing a single paragraph.

A few details worth knowing:

- Saving unchanged text stores nothing extra. Snapshots are based on content,
  so identical saves cost nothing.
- Keeping a snapshot can never be the reason a save fails. If the disk is
  full, your save still completes; QUILL just logs that the snapshot was
  skipped.
- History thins as it ages: everything from the last week is kept, then one
  version per day for a month, then one per week. The newest five versions are
  never removed.
- **Restore point disk limit (MB)** in Preferences caps how much space one
  document's history can use: 200 MB by default.
- **Keep restore points when saving** turns the feature off entirely.
- You can change the key in the Keymap Editor, where the command is listed as
  Restore Previous Version (`file.restore_previous_version`).

How the safety nets fit together: **undo** (and persistent undo) covers the
current editing session, **backups** keep a copy of what was on disk just
before each save, and **restore points** are the long-term history, any
earlier save, across restarts. You never have to choose between them. They
all run at once.

## Persistent undo

When persistent undo is turned on (**Enable persistent undo**, on the
**Editing** page of Settings), QUILL keeps the undo history of saved files
from one session to the next, so you can still undo yesterday's change after
reopening the file. QUILL spaces out those writes so the feature stays
practical on large documents.

## Recovery

If QUILL closes unexpectedly, it can offer your work back as a recovery
snapshot the next time you start it.

Two settings shape what it offers. Both are shared with QUILL Lite, so the
answer is the same in either editor.

- **Offer untitled unsaved work** (`recover_untitled_documents`) is on by
  default. A window that never had a file is where a lot of real work starts,
  so it is offered back like any other. Turn it off and only documents that had
  a file are offered; the copies of untitled ones are deleted, not kept, since
  nothing would ever offer them to you. The setting's own description says so.
- **Days of unsaved work to keep** (`recovery_keep_days`) is 30 by default.
  Only the previous session's work can ever be offered back, so an older copy
  can never be reached and just takes up space. One real install had
  eighty-six days of them. Set it to 0 to keep everything for ever.

Identical copies are folded into one before you are asked anything. That is
how "unsaved work from 69 documents", sixty-seven of which were the same few
characters left behind by repeated crashes, becomes a list of three you can
actually read.

Two windows can appear at startup: one about unsaved work and one about last
session's documents. Both have a read-only **What this would do** field. Tab
to it and read it with the arrow keys. It names every row, says how much text
it holds and when it was written, and then says exactly what each button
would do with the boxes checked as they are right now, including which rows
would be left alone. It is rewritten every time you check or uncheck a row, so
it always describes the window as it is.

### After an unclean exit, Crash Recovery and Email Support

If QUILL closed without an error report, after a freeze, a power cut or a
forced close, the next launch shows **Crash Recovery**, which offers your
unsaved work back. Its **Email Support** button (it used to say "Send Bug
Report") writes a message to support for this kind of exit too. The first
sentence also quotes how the document begins, so you know which work it is
before you read the preview:

1. Press **Email Support** in Crash Recovery.
2. Your mail program opens with a message to **support@community-access.org**.
   It contains QUILL's version, platform and screen reader, your last
   commands, any "the UI stopped answering" lines from the log (listed first),
   the saved crash traceback when there is one, and a short, redacted tail of
   the newest log.
3. Read it, add a sentence about what you were doing, and send it from your
   mail program.

Crash Recovery closes once the mail program has opened. If no mail program
answers, the report is on your clipboard and Crash Recovery stays open so you
can still restore your work.

### When QUILL crashes, emailing a crash report

When an error stops QUILL, it first saves a local crash file, then offers to
email a redacted report to support.

1. A dialog titled **Report Crash** appears. Focus starts in the first text
   field.
2. The **Report preview** is a read-only panel showing exactly what the report
   says: QUILL's version, whether it is portable, your screen reader, the
   active document's name and encoding (never its text or folder), the last
   ten commands you ran, and the last frames of the error. Personal data, file
   paths and anything shaped like a password or key are removed before the
   preview is built.
3. Fill in any of the three optional fields: **What were you doing when this
   happened?**, **What command do you think triggered it?** and **Expected
   behaviour**. Each is cleaned the same way before it is added, so something
   you paste by accident does not leave your machine.
4. Choose one of the three buttons:
   - **Email support** (`Alt+E`) opens your own mail program with the report
     written and addressed to **support@community-access.org**, the subject
     starting "Crash report". Nothing is sent until you press Send there. With
     no mail program, the report goes to your clipboard and QUILL tells you
     the address to write to.
   - **Copy to clipboard** (`Alt+C`) puts the same redacted report on the
     clipboard so you can paste it into an email yourself.
   - **Don't send** (`Alt+D`, or Escape) closes the dialog and sends nothing.

Whichever button you choose, the local crash file is kept in the
`crash-reports` folder of QUILL's data folder. **Tools > Customize and Support
> Open Diagnostics Folder** takes you near it.

If you do not want the dialog at all, turn off **Settings > General >
Offer to email crash reports to support**. The local crash file is still
saved.

## If your screen reader stops, your work is already safe

QUILL keeps an eye on the screen reader it found at startup and notices if it
disappears while you work. One missed check is ignored, so restarting JAWS or
NVDA never sets off an alarm. When the reader is confirmed gone, QUILL
straight away saves a snapshot of every open document to autosave, then
explains what happened through whatever can still speak: another running
screen reader, or QUILL's own built-in voice. The event is also recorded in
Notifications, so if you heard nothing at the time, the explanation is waiting
for you.

QUILL does not shut down when this happens. Your documents, your unsaved work
and the application itself all keep running. Restart your screen reader
whenever you are ready, and QUILL announces when it hears from it again.

The same rule holds everywhere in QUILL: anything that closes QUILL or cuts
back what it can do, without you asking, must save your work first.

QUILL Lite has the same protection, through the same code: the same two
missed checks, the same snapshot first, and the same sentence, ending "QUILL
Lite keeps running". Its user guide explains the parts that differ, since QUILL
Lite has no voice of its own.

## The default answer to a destructive question is No

Every question in QUILL that would destroy something (delete a recording,
clear all copy tray slots, remove a component, reset settings) has **No** as
its default button. Pressing Enter out of habit can never cost you data.
Choosing Yes is always something you do on purpose, with Tab or `Alt+Y`.
QUILL's build checks every new dialog for this, so it stays that way.

## Closing every tab but this one

**Window > Close Other Documents** (`Ctrl+Shift+F4`) keeps the tab you are in
and closes the rest. QUILL Lite has the same command on the same key.

When one of those tabs has unsaved changes, you are asked about it. The
question has five answers:

- **Save** and **Don't Save** apply only to the tab in front of you.
- **Save All** and **Don't Save Any** settle every remaining tab at once.
- **Cancel** stops the whole thing and tells you how many tabs closed before
  you stopped it.

The question also says how many more tabs are waiting, so you know at the
first prompt whether this is one more keystroke or sixty-seven.

Enter answers Save, never one of the two that lose work. If a save fails, the
closing stops there; a failed save is never taken as permission to throw the
document away. After that, "Save All" no longer applies until you choose it
again.

## Errors that tell you what to do

A sighted person can glance at the failing file or dialog and see the problem.
Without sight, the error message has to carry the whole story, and the next
step too. QUILL's messages are being written to that standard. Messages that
carry a support code (the `[QUILL-...]` prefix) increasingly end with what to
do, for example:

- "Install Pandoc from Help > Download Optional Components to convert this
  format."
- "Check the address, credentials, and connection under File > Open from
  Remote > Manage Remote Sites."
- "Check your AI provider and key in the AI Hub, or switch to a local model."

When you report a problem, include the code. It tells us exactly which failure
you hit, with no back-and-forth.

The same goes for things QUILL declines or trims:

- The command palette says why a command is unavailable, and a menu item
  turned off by a safety advisory carries the same reason in its help text.
- AI features tell you when they worked from less than you gave them. If your
  document had to be trimmed to fit the model, Ask Quill and Document Q&A say
  exactly how much of it the answer used.
- QUILL never quietly changes which AI engine answers you. If your provider
  could not be reached and the chat started on the on-device model instead, it
  says so the moment the chat opens. If a call fails and the other kind of
  engine could take it, QUILL offers the switch. It never makes the switch for
  you, and it always says when a switch would send your text to the cloud.

## Sessions

Sessions are best thought of as workspace snapshots. A session remembers the documents you have
open and which tab is active, so you can reopen that exact set later. If you
know VS Code workspaces, a QUILL session is a simpler, document-focused
version of the same idea. You can:

- save your current workspace,
- reopen it from Recent Snapshots,
- switch quickly among the open documents in the current workspace group.

Sessions help when one writing job spans notes, references, drafts and
generated reports.

## Marks vs bookmarks (and the ring)

QUILL has two ways to jump back to a place, and each has its job:

- **Bookmarks** are named jump points. They are easy to list, and best for
  places you will come back to by name, again and again.
- **Marks** are temporary jump points kept in a **ring**: a rolling stack of
  your recent mark locations, for fast back-and-forth while you edit.

Use bookmarks for places you want to keep. Use marks while you are moving
around and reshaping text. Chapter 6, Moving around and finding things, has
the keys for both.

## Trusted locations

Trusted locations cut down on repeated prompts when you often work from the
same folders. They help most in document review and in workplaces where many
files come from the same shared places.

## Safe mode

Safe mode opens QUILL with optional extras turned off: AI, the watch folder
and Quillin contributions. If a session has gone wrong or QUILL is behaving
strangely at startup, safe mode is a good first step. To use it, start QUILL
with the `--safe-mode` flag, or set the environment variable
`QUILL_SAFE_MODE=1` before launching.

## The Experimental tab

**Settings > Experimental** holds features that work but are still
growing up. Each one has its own switch, and they all sit behind one master
switch. Controls that are turned off leave the Tab order completely, so until
you change anything the tab is a single checkbox and nothing else.

- **Enable experimental features (the master switch for everything on this
  tab)** is the first control on the tab. It governs everything below it. Until it is checked, QUILL ignores
  every experimental option and its control is disabled (Tab skips it), so an
  accidental change can never affect the editor.
- **GLOW accessibility review and repair (experimental)** turns on the
  GLOW rows of **Tools > Writing and Language** (see "[GLOW Workflows Inside
  QUILL](quill-guide-11-accessibility-speech-and-braille.html#glow-workflows-inside-quill)"). It takes effect when you press Apply,
  with no restart.
- **WordPress publishing connections (experimental)** turns on the read-only
  publishing tools in the **File** menu: save a WordPress connection, verify
  it, browse your site's posts and pages, and open a remote item in the
  editor. It only brings things in. The send and publish half stays locked
  while it is reviewed, so nothing can be published from QUILL whatever this
  switch says.
- **Read the document aloud in your browser (experimental)** turns on the
  browser reader page described under [Read Aloud](quill-guide-08-reading-reviewing-and-listening.html#read-aloud).
- **Table Studio, accessible table and CSV editing (experimental)** turns on
  **Table Studio** and **Open CSV in Table Studio** in the **Tools** menu. It
  takes effect when you press Apply, with no restart.

The pattern to remember: one master switch for the tab, and one switch for
each experiment, so nothing changes by accident.

The editor experiments that used to live on this tab have graduated.
QuillRichEdit is now QUILL's one editor, and the braille fix it carried moved
to **Settings > Braille Mode**, where it is on by default. See "One Editor,
Every Format" in [Working with different document
types](quill-guide-03-opening-saving-and-converting-files.html#working-with-different-document-types).

## Notifications and updates

QUILL keeps a notification center for update and workflow events, so a
message you missed is still there later. Before offering a download, an
update check verifies that the update information is signed.

### Safety advisories, temporarily turning off a feature

Very rarely, if a serious problem is found in a feature after release, QUILL
can temporarily disable just that feature, without waiting for a new version.

- The advisory travels inside the same signed update information that Check
  for Updates already verifies. Nothing new is sent from your computer.
- It can only ever turn a feature off. It can never turn anything on or run
  anything.
- The affected command is dimmed everywhere it appears. The menu, the command
  palette and its keyboard shortcut all stop it, and a plain notice tells you
  it was turned off by a safety update and why.
- If other features build on the one that was turned off, they are turned off
  too, so you never get a half-working tool.
- Everything comes back on its own once a fix is published.
- The lock is remembered on your computer, so it still applies when you are
  offline, and it reaches portable copies as well.

If you are an administrator who must use a feature an advisory turned off, you
can override all such locks for one session: set the environment variable
`QUILL_IGNORE_FEATURE_LOCKS=1` before launching QUILL.

### Your settings across updates

QUILL remembers only the choices you have actually changed. When you update,
your customizations are kept, brand-new options start at a sensible default,
and an improved default reaches you automatically unless you had changed that
option yourself. The first launch after an update tidies your old settings
file once, and writes a backup to a `migration-backups` folder first, so the
change can always be undone. Your documents, autosaves and recovery data are
never touched.

The **Upgrade notice** setting (in Administration) chooses how QUILL tells you
this happened:

- **Brief announcement**, the default: a short spoken and status-bar message.
- **Summary with Undo**: a small dialog listing what changed, with a one-click
  Undo for any shortcut correction.
- **Silent**.

A backup is saved whichever you choose. You can also undo a recent shortcut
change at any time during the session with the **Undo Recent Shortcut Change**
command.

### A clean start after an update

The first time you launch a freshly updated QUILL, it clears out old log files
and crash reports from earlier runs, so you start with a clean slate. This
happens once, on its own, and never removes your documents or settings.

## Application Status page

**Help > Status Page** opens a window you can leave open in the background
while you keep working. It has four tabs:

- **Status**: an Overview (version, active profile, how many background tasks
  are running, queued notifications), plus detail rows for QUILL Whisperer and
  the Read Aloud engine and voice settings when those features are turned on.
- **Tasks & Downloads**: one live row per background job, with its name,
  status, progress, start time and finish time. Batch conversions, model
  downloads and other long jobs report their progress here.
- **Features**: every feature ID QUILL knows about, its display name, its
  category, and whether it is on right now.
- **Actions**: a plain-text log of recent actions QUILL has taken.

The three list tabs are ordinary lists. Arrow up and down between rows, use
Left and Right to move between columns, and Tab to reach the **Refresh** and
**Close** buttons. The page refreshes itself every two seconds, so downloads
and tasks stay current without you pressing Refresh, and the automatic
refresh leaves your place alone: the row you arrowed to stays focused.

> **QUILLBee's tip:** Something running and you want to know how far along it
> is? Leave **Help > Status Page** open and switch to it with `Alt+Tab`
> whenever you like.

## What you learned, and where to go next

You now know that autosave, backups and restore points run together, that
**File > Restore Previous Version...** brings back any earlier save, and that
QUILL offers your unsaved work back after a crash or a lost screen reader. You
know that a destructive question defaults to No, how to close every tab but
one, where safe mode and the Experimental tab fit, and what a safety advisory
does. The Status Page shows what QUILL is doing in the background.

For a guided version, open **Help > Tutorials...** (`Ctrl+Alt+F1`) and take
"The safety net" in the Living with it track.

Next, Chapter 14, Projects, notes and the QuillVille family, covers the
bigger places your writing can live.

---

- Previous: [Chapter 12: Making QUILL yours](quill-guide-12-making-quill-yours.html)
- Next: [Chapter 14: Projects, notes and the QuillVille family](quill-guide-14-projects-notes-and-the-quillville-family.html)
- [Contents](../userguide.html)
