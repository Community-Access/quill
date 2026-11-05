# Chapter 5: Permissions, the allow list and the bypass

## What this chapter covers

This chapter is the whole permission model in one place: what the agent may
do without asking, what it must ask for, what it can never do, the per-project
allow list, the deliberate bypass, and what QUILL honestly cannot stop on
Windows. It also explains why each rule is the way it is.

## The short version

| What the agent wants | What happens |
|---|---|
| Read, list or search files in the project | Allowed, without asking |
| Change, add, delete or rename a file | Proposed only; you decide in Review Changes |
| Run a command | Asks you in Run This Command?, unless you allowed it |
| Use one of the engine's own tools | Refused unless you checked it; then asks each time |
| Push, publish, force a remote, change system settings | Never, whatever you allow |
| See a secret file | Never; it is hidden from the agent |

## Reading needs no permission

Inside the project folder, reading is free: listing files, reading them,
searching, reading an outline, and reading the git branch and changed files.
That is the same rule Do a Document Task has for the document you have open.
It keeps a task from asking you twenty questions before it has done
anything. The boundary in Chapter 2 is what keeps reading safe: nothing
outside the folder, and no secrets.

## Changes are proposals

When the agent edits a file, makes one, deletes one or renames one, nothing is
written. The change joins the turn's list of proposed changes. Before a
command runs, and when the turn ends, Review Changes shows them, and only what
you accept is written, all at once. Chapter 7 covers the window.

The agent is told the truth about what happened: "Proposed a change to
cli.py. Nothing is written yet", and afterwards exactly which changes you took
and which you left.

## Commands ask

Every command the agent wants to run opens **Run This Command?** first.
Chapter 6 covers that window and running commands in full. Your three answers:

- **Allow once** (Enter): run it now. The next command asks again.
- **Always allow this command here:** run it now, and add it to this
  project's allow list, so next time it runs without asking. Offered only
  when QUILL found no warning.
- **Don't allow** (Escape): do not run it. The agent is told, and carries on
  without it.

## What QUILL never runs for an agent

Some things QUILL keeps for you, whatever you have allowed and even with the
bypass on:

- **pushing to a remote:** any `git ... push`;
- **publishing a package:** `npm publish`, `yarn publish`, `pnpm publish`,
  `twine upload`, `cargo publish`, `gem push` and `nuget push`;
- **changing a remote repository:** `gh release` or `gh repo` with create,
  delete or edit;
- **forcing a remote:** git with `--force`, or `-f` against origin or
  upstream;
- **changing system settings:** `reg add`, `reg delete` and `reg import`,
  `bcdedit`, `diskpart`, `netsh`, `setx`, `schtasks`, `sc`,
  `Set-ExecutionPolicy`, `shutdown`, `Restart-Computer`, `Stop-Computer`, and
  formatting a drive.

The agent is told "The person keeps this step for themselves. Do not try
another way to do it; tell them the exact command, and they will run it if
they want to." So it gives you the command, and you decide.

## The allow list: Commands Allowed in This Project

**Tools > Commands Allowed in This Project...**, or **Allowed Commands...**
(`Alt+W`) in the task window, opens the project's own list of commands that
run without asking.

- **Allowed commands** lists them. Delete removes the selected one, as does
  **Remove**.
- **New command:** type a command or the start of one, then press Enter or
  **Add**.

How a line matches: it allows that exact command, or any command that starts
with it and a space. So `pytest` allows `pytest -q tests`, but not
`pytest-watch`. Spaces are tidied, so two spaces count as one.

What never gets on the list:

- a pattern the AI suggests: only what you type, or what you chose with
  Always allow;
- a command QUILL warns about: those always ask, every time, even if you
  typed them here.

### Why the list lives in QUILL, not in the project

The list is kept in QUILL's own data, for that project only. A project folder
cannot carry its own allow list, so a project you clone or download can never
approve its own commands. If a repository could ship a file saying "rm -rf is
fine here", the first person to open it would have agreed to that without
knowing.

## The bypass: Run commands without asking

The same window has a check box: **Run commands without asking**. It is off
until you check it, and when you check it QUILL asks you to confirm:

> Run commands without asking in this project? The agent will run any command
> it chooses without showing it to you first, except pushing, publishing and
> system changes, which QUILL never runs for an agent. Undo Last Turn still
> puts files back, but it cannot undo what a command did outside the project
> or on the internet.

No is the default. While the bypass is on:

- the task window's status line says "Commands run without asking";
- every command it runs is noted in the conversation: "Ran without asking, as
  this project allows: ...";
- the never list above still applies;
- it is for this project only.

Uncheck it to go back to asking.

## Engine tools ask too

If you checked any of an engine's own tools (Chapter 4), each use asks you in
**Allow This Step?**. It has three answers: **Allow once**, **Allow for this
task** (steps like this one until the task ends; the next task asks afresh),
and **Don't allow**. A tool you did not check is refused without a question.

## What QUILL cannot stop on Windows

Windows gives QUILL no simple way to fence a command in. A real sandbox needs
administrator rights or Windows features many people do not have. So once you
allow a command, it can reach the internet, read files outside the project,
and do anything your own Windows account can do. QUILL cannot prevent that.

Your approval is the safety line. That is why QUILL shows you the exact
command, warns you when it sees a risk, asks every time unless you choose
otherwise, and keeps the never list.

What QUILL does do for every command:

- runs it in your project folder;
- takes your API keys, GitHub and Copilot tokens, and QUILL's own settings
  out of its environment;
- runs it so that Stop ends the whole command, child processes and all;
- keeps its output in a file rather than reading it at you.

## Where to next

- Previous: [Chapter 4: Engines, and choosing one](developer-04-engines.html)
- Next: [Chapter 6: Running commands and reading their output](developer-06-commands.html)
- [Contents](developer-guide.html)
