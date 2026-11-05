# Chapter 7: Reviewing changes, and undoing a turn

## What this chapter covers

Nothing the agent proposes reaches your disk until you accept it, and one
command puts a whole turn back. This chapter covers Review Changes for one
file or many, how each change is read to you, what happens to files you have
open, the checkpoints QUILL keeps under every turn, Undo Last Agent Turn, and
what to do when undo refuses.

## When Review Changes opens

The agent's edits, new files, deletions and renames collect as proposals.
**Review Changes** opens by itself:

- before the agent runs a command, so the command runs against what you
  accepted;
- when a turn ends with changes still waiting.

There is no separate command to open it. If you are in another window when it
is ready, you hear "The project task is waiting for you. Press Ctrl+3 to
answer." once, and it opens when you come back to the task window.

## The file list

Focus starts in **Files** (`Alt+F`): one row per file, as a whole sentence.
The last words say what you have chosen:

- "cli.py, changed, 3 changes, taken"
- "tests/test_cli.py, new file, 24 lines, taken"
- "old_util.py, deleted, taken"
- "util.py, renamed to helpers/util.py, not taken"
- "cli.py, changed, 3 changes, 2 of 3 taken"

Every proposed change starts out taken, so if the agent got it right, Enter on
Apply Accepted Changes is all you need.

The row says its state in words rather than with a check box, because a
check-list box's state is not read as you arrow through it.

- **Space** on a row takes the whole file, or leaves it if it was all taken.
- **Enter** on a row moves you to its changes.

## One change at a time

**Change details** (`Alt+D`) shows the change you are on, as text you read
with the arrow keys. It starts with the file and where the change is:

> cli.py. Change 2 of 3, lines 40 to 44, in function parse_args. Accepted.

Then the change itself, read for code rather than for prose:

- **Every line is led by its line number,** so a braille reader can find a
  line by number.
- **Indentation is said as a count,** once, when it changes: "indent 8".
- **A one-line change says what changed in the line,** token by token: "In
  this line: changed tokn to token." Then the line as it is now, and as it
  was.
- **A longer change** says "New text, 5 lines:" with the new lines, and
  "Replaces 3 lines:" or "Removes 3 lines:" with the old ones.
- **A new file** reads as plain text with line numbers: "New file
  tests/test_cli.py, 24 lines."
- **A deletion** says "Delete old_util.py, 30 lines." and that Undo Last Turn
  brings it back.
- **A rename** says "Rename util.py to helpers/util.py." The text does not
  change, only the name and folder.
- **The agent's reason** comes last, when it gave one.

Where a change sits ("in function parse_args") comes from the file's outline.
Python is read exactly by its own parser; other languages by simple patterns
for their functions and classes.

## The buttons

- **Accept** (`Alt+A`) takes the change shown. You hear "Change 2 accepted."
- **Reject** (`Alt+R`) leaves it out; it is never written.
- **Next Change** (`Alt+N`) shows the next change, and then the first change
  of the next file. At the end you hear "That was the last change."
- **Previous Change** (`Alt+P`) goes back, into the previous file too.
- **Accept All in File** (`Alt+I`) and **Reject All in File** (`Alt+L`) mark
  every change in the file you are on.
- **Why This Change?** (`Alt+W`) says the reason the agent gave: "The agent's
  reason: ..." or "The agent gave no reason for this change to cli.py."
- **Apply Accepted Changes,** the default: Enter writes every accepted change
  at once.
- **Reject All:** Escape writes nothing from this turn.

Closing the window any other way counts as Reject All, so nothing is ever
written by accident.

## Applying

Apply Accepted Changes writes everything you accepted together, and only after
QUILL has kept its copy of the project for Undo Last Turn. If one file cannot
be written partway through, the whole set is rolled back, so you never end up
with half a turn. The agent is then told exactly what you accepted, for
example "Accepted 2 of 3 changes in cli.py".

## Files you have open

When a turn changes a file you have open, QUILL reloads the open copy in
place, with your cursor where it was, and you hear one line, such as "cli.py
was updated by the task." Focus stays where it was.

QUILL leaves the open copy alone, so your typing is never overwritten, when:

- it has edits you have not saved;
- it is open as rich text;
- in QUILL, it is a kind of file QUILL does not reload in place. QUILL reloads
  plain text, Markdown, Python, JavaScript, TypeScript, JSON, TOML and YAML
  files, and files with no extension.

Then you hear, for example, "cli.html has changed on disk and is open with
your own edits or in rich text, so QUILL left the open copy alone. Reload it
to see the task's change." Close and reopen the file when you are ready.

## The checkpoints under every turn

Before a turn first changes anything, by an accepted review or by a command,
QUILL notes every file in the project it can see, and keeps a private copy of
each. After the turn it notes them again. That is what Undo Last Turn uses.

- The copies are in QUILL's own data folder, never in your project and never
  in your git history. QUILL makes no commits, branches or stashes.
- It works the same with or without git.
- Secret files are never copied, because the agent cannot see them.
- QUILL keeps the last 10 turns of each project, and sweeps older copies.
- A file bigger than 5 MB is not copied, so it cannot be undone. A snapshot
  covers up to 5,000 files.
- Nothing is ever sent anywhere.

## Undo Last Agent Turn

One `Ctrl+Z` in one document is not enough for a turn that touched several
files. **Undo Last Turn** puts back every file the last turn changed, across
the whole project, and removes every file it made. You hear, for example,
"Undid turn 2. cli.py and test_cli.py are back as they were; removed
notes.txt."

Three ways to reach it:

- **Undo Last Turn** (`Alt+U`) in the task window;
- **Edit > Agent Work > Undo Last Agent Turn** from anywhere, even after the
  task window is closed;
- in QUILL, `Ctrl+Shift+Grave, U`: press the QUILL key, then U.

Undo again to go back another turn, up to the last 10. The checkpoints are on
disk, so this works after QUILL has been closed and opened again, once you
open the project.

While a turn is still running you hear "Stop the task, or let the turn
finish, before undoing it." With nothing to undo you hear "There is no agent
turn to undo in this project."

### When undo refuses

If you have edited one of those files since the turn, undo refuses rather
than lose your work, and says which file:

> cli.py has changed since the agent's turn. Undo would lose your edits. Open
> the file as it was before the agent's turn, to compare? Your file is not
> changed either way.

**Yes** opens that earlier copy as a separate document, so you can compare
and copy back what you need. **No** leaves everything as it is.

### What undo cannot do

Undo puts files in the project back. It cannot take back what a command did
outside the project or on the internet: a package it installed, a file it
wrote elsewhere, a request it sent.

## Stop Agent

**Stop** (`Alt+T`) in the task window stops the task straight away, and the
command it is running stops with it. Any question still open is answered
"don't allow". From any other window, choose **Edit > Agent Work > Stop
Agent**; in QUILL that is also `Ctrl+Shift+Grave, K`. It stops a Do a
Document Task too. If nothing is running, you hear "No agent task is
running."

Changes already applied stay applied after a stop; Undo Last Turn takes them
back.

## Where to next

- Previous: [Chapter 6: Running commands and reading their output](developer-06-commands.html)
- Next: [Chapter 8: Agent notes in the repository](developer-08-agent-notes.html)
- [Contents](developer-guide.html)
