# Chapter 13: Troubleshooting

## What this chapter covers

The sentences QUILL says when a project task cannot do what you asked, what
each one means, and what to do. It also covers a few things that surprise
people the first time. Every sentence here is the one both editors say.

## The commands are not in the menus

The project commands appear only with coding on. In QUILL, choose the
Developer profile or check **Developer Tools** in **Help > Feature Profiles >
Manage Individual Features...** (`Ctrl+Alt+F10`). In QUILL Lite, choose the
Developer profile or check **Coding** in **Tools > Customize Features...**
(`Ctrl+Alt+F10`). Chapter 1 has the details.

## "Project tasks are part of the Developer profile."

The full sentence is "Project tasks are part of the Developer profile. Choose
the Developer profile, or turn on Developer Tools in Customize Features." You
pressed a project command with coding off. Turn it on as above. In QUILL, the
window that turns on Developer Tools on its own is called Manage Individual
Features.

## "AI help is switched off."

- **In QUILL:** "AI help is switched off. Turn it on in the AI menu, Use
  Artificial Intelligence." Check **AI > Use Artificial Intelligence**.
- **In QUILL Lite:** "AI help is switched off. Turn it on in Tools, Customize
  Features." The Developer profile leaves the AI help area off. Check **AI
  help** in Customize Features. With Copilot, Codex or your own key, your text
  does not go to QUILL's servers, whatever the area's name says.

## In QUILL Lite, Ctrl+3 does nothing

`Ctrl+3` and Choose Your AI (`Ctrl+4`) belong to the AI help area. Check AI
help in Customize Features, as above.

## "AI is off in Safe Mode."

The full sentence ends "Nothing can be signed in until QUILL starts normally."
QUILL was started in Safe Mode, which turns all AI off. Start it normally.

## "No project is open. Choose Open Project Folder first."

You chose a project command, such as Do a Project Task or Commands Allowed in
This Project, with no project open. Choose **File > Open Project Folder...**.

## Ctrl+3 opened Do a Document Task

No project is open, so `Ctrl+3` did what it always does. Open a project first.
If one is open and you still get the document task, coding has been turned
off; see the start of this chapter.

## The task will not start, or says your AI cannot run tasks

Project tasks need My GitHub Copilot, Codex, or My own key with Anthropic
Claude or Ollama on this computer. If you hear "Document tasks need My GitHub
Copilot or Codex. Press Ctrl+4 to choose one.", or QUILL offers to switch,
press `Ctrl+4` and choose one of those. QUILL's free AI and the other own-key
providers answer in text only.

When a task cannot start for another reason, such as a sign-in that has
expired, the conversation says why, and so does what you hear.

## With Claude or Ollama, the window says "No engine" or "GitHub Copilot"

In this version, the task window's status line names only GitHub Copilot and
Codex, so with My own key it starts "No engine", and the agent's replies in
the conversation are labelled "GitHub Copilot". The task is still running on
your own key, with the engine you chose in Choose Your AI.

## Engine Tools says "This engine offers no tools of its own here."

The engine you are using has no tools of its own that QUILL can offer. That is
so for Ollama, and in this version for Claude on your own key as well.
QUILL's own project tools still do everything a task needs.

## "A project task is running. Stop it, or let it finish, before closing the project."

You tried to close the project, or open another, while a task was running.
Press **Stop** (`Alt+T`) in the task window, or wait for the turn to end.

## The task is waiting, and nothing has opened

A question opens only while you are in the task window, so it never lands on
top of your typing. Press `Ctrl+3` to bring the task window back, and the
question opens. The Project part of the status bar says ", waiting for you"
while one is waiting.

## A command I expected to run without asking still asks

Check three things:

- the command has a warning line. Commands with a warning always ask, even if
  they are on the list;
- the list entry is not the start of the command followed by a space. `pytest`
  allows `pytest -q`, but `py` does not allow `pytest`;
- the command is on the list for a different project. Each project has its own
  list.

## The agent says I keep this step for myself

It wanted to push, publish, force a remote or change a system setting, and
QUILL never runs those for an agent. It should have told you the exact
command. Run it yourself, in your own terminal, if you want it.

## A command fails at once, but works in my terminal

QUILL runs commands through `cmd`, in the project folder, with tokens, keys
and QUILL's own settings removed from the environment. So:

- a PowerShell command needs `powershell -Command` in front;
- a command that needs a token from an environment variable will not see it.
  Run that one yourself;
- if you hear "The command ... was not found.", the program is not on your
  PATH, or the agent guessed the wrong name.

## A command has been running for a long time

After five minutes QUILL asks whether to keep waiting. Choose No to stop it,
or press Stop at any time.

## The task stopped after 40 steps

A turn that takes more than 40 steps asks "The task stopped after 40 steps.
Continue?" Yes lets it carry on. No ends the turn. Many steps usually means
the instruction was broad; try asking for one part at a time.

## My open file did not update after the task changed it

QUILL leaves an open copy alone when it has unsaved edits, when it is in rich
text, or, in QUILL, when it is a kind of file QUILL does not reload in place
(Chapter 7). You hear that it was left alone. Save or discard your edits, then
close and reopen the file.

## "cli.py has changed since the agent's turn. Undo would lose your edits."

Undo refuses rather than overwrite your own edits. Choose **Yes** to open the
file as it was before the turn, compare, and copy back what you need. Chapter
7 explains.

## "There is no agent turn to undo in this project."

Nothing is left to undo: QUILL keeps the last 10 turns per project, and each
undo uses one up. Turns made in the other editor are kept by that editor.

## Undo did not bring back a big file

Files bigger than 5 MB are not copied for undo, so they cannot be put back.
Keep large files under version control.

## "There is no turn to explain yet."

Explain Last Turn works on the task in the open task window. A new task
window has no turns to explain until it has done something.

## The agent ignored the project's AGENTS.md

You may have answered **Don't Use Them** the first time. QUILL asks once per
project and remembers the answer. In this version there is no command to
change that answer.

## The agent cannot see a file

It may look like a secret, be in a skipped folder, be ignored by
`.gitignore`, be bigger than 2 MB, or be outside the project folder. Chapter 2
lists the rules. The agent is told when files were hidden, and should ask
you. Paste what it needs into Instruction, or tell it where to look.

## The transcript I wanted has gone

Each new task window starts a new transcript for that project, replacing the
last. Save a copy with **Save As** when you want to keep one (Chapter 10).

## Where to next

- Previous: [Chapter 12: QUILL Lite differences](developer-12-quill-lite.html)
- Next: [Chapter 14: Every developer key](developer-14-keys.html)
- [Contents](developer-guide.html)
