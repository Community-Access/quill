# Chapter 15: Window reference

## What this chapter covers

Every developer window, with every control by the name your screen reader
says, in Tab order, and what each one does. The windows are the same in QUILL
and QUILL Lite. Press `F1` on any control for its own help sentence; each
window's F1 help starts with what the window is for.

## Open Project Folder

Opened by **File > Open Project Folder...**. "Choose a folder to work on as a
project."

- **Recent projects** (list): folders you have opened as projects, newest
  first, each as its name and full path. Enter or Space opens the one
  selected. Before you have any it says "No recent projects yet." and is
  unavailable.
- **Browse for a Folder...** (button): the Windows folder picker, to choose
  any folder. Choosing one opens it at once.
- **Open** (button, the default when there are recent projects): opens the
  selected recent project.
- **Cancel** (button): closes without opening a project. Escape does the
  same.

## Use This Project's Agent Notes?

Opened by itself the first time a task starts in a project that has notes for
AI agents. Chapter 8.

- **Question** (read-only text): which files hold the notes, and what using
  them means. Focus starts here.
- **Notes** (read-only text): empty until you press Read Them First; then the
  notes' text, as it would be sent.
- **Read Them First** (button): shows the notes in Notes and moves you there.
- **Use Them** (button, the default): sends the notes with every task in this
  project, marked as data.
- **Don't Use Them** (button): leaves them out. Escape does the same.

## Do a Project Task

Opened by `Ctrl+3` with a project open, or **Do a Project Task...** in the AI
menu (QUILL) or Tools > AI (QUILL Lite). A window of its own, not a dialog, so
you can switch to your documents and back. The title is "Do a Project Task";
the project's name is in the status line. Chapters 3, 7 and 9.

- **Conversation** (read-only text): everything said in this task, filled in
  quietly.
- **Status** (read-only text): which AI is working, the project, and the
  state: Working, Waiting for you, Stopping, Coach mode, Commands run without
  asking. For example, "Using GitHub Copilot. Project cli-tool. Working."
- **Instruction** (edit field): where you type. Focus starts here. Enter
  sends.
- **Coach mode** (check box): the agent teaches and points; you type.
- **Plan** (button): the cursor to the latest plan in the conversation.
- **Changes** (button): the cursor to the latest list of changes.
- **Output** (button): the last command's full output, as a document.
- **Transcript** (button): the whole task as a document, one heading per turn.
- **Undo Last Turn** (button): puts back every file the last turn changed.
- **Explain Last Turn** (button): asks what the last turn changed and why.
- **Allowed Commands...** (button): Commands Allowed in This Project.
- **Engine Tools...** (button): Engine Tools for This Project.
- **Send** (button): starts a turn with what you typed, or sends it to the
  running one.
- **Stop** (button): stops the task now, with any command it is running.
  Unavailable while nothing runs.
- **Close** (button): closes the window, stopping a task that is still
  running.

## Review Changes

Opened by itself when a turn has changes, before a command runs and when the
turn ends. Chapter 7.

- **Files** (list): one row per file, as a sentence ending taken, not taken,
  or how many are taken. Focus starts here. Space takes or leaves the whole
  file; Enter moves to Change details.
- **Change details** (read-only text): the change shown, with where it is,
  each line led by its line number, indentation as a count, and the agent's
  reason.
- **Accept** (button): takes the change shown.
- **Reject** (button): leaves it out.
- **Next Change** (button): the next change, then the next file's.
- **Previous Change** (button): the change before.
- **Accept All in File** (button): takes every change in this file.
- **Reject All in File** (button): leaves every change in this file out.
- **Why This Change?** (button): says the agent's reason.
- **Apply Accepted Changes** (button, the default): writes every accepted
  change at once, after QUILL has kept its copy for undo.
- **Reject All** (button): writes nothing. Escape, or closing the window,
  does the same.

## Run This Command?

Opened when the agent asks to run a command. Chapter 6.

- **What will run** (read-only text): one sentence on what, where and why.
  Focus starts here.
- **Command** (read-only text): the exact command.
- **Warning** (read-only text): only when QUILL found a risk.
- **Allow once** (button, the default): runs it now.
- **Always allow this command here** (button): only when there is no
  warning. Runs it and adds it to the project's list.
- **Don't allow** (button): does not run it. Escape does the same.

## Keep Waiting?

A Yes or No question when a command has run for five minutes, and every five
minutes after: "The command has run for 5 minutes. Keep waiting? Choose No to
stop it."

## Continue?

A Yes or No question when a turn reaches 40 steps: "The task stopped after 40
steps. Continue?"

## Commands Allowed in This Project

Opened by **Tools > Commands Allowed in This Project...**, or Allowed
Commands... in the task window. Chapter 5.

- **About this list** (read-only text): what the list does, and what it never
  does.
- **Allowed commands** (list): the commands that run without asking. Focus
  starts here. Delete removes the selected one.
- **New command** (edit field): a command or the start of one. Enter adds it.
- **Add** (button): adds what you typed.
- **Remove** (button): removes the selected command.
- **Run commands without asking** (check box): the bypass. Checking it asks
  you to confirm first.
- **Close** (button): closes the window. Escape does the same. Every change is
  saved as you make it.

## Run Commands Without Asking?

A Yes or No question when you check the bypass, with No the default. It says
what the bypass does, that pushing, publishing and system changes are still
never run, and that Undo Last Turn cannot undo what a command did outside the
project or on the internet.

## Engine Tools for This Project

Opened by **Engine Tools for This Project...** in the AI menu (QUILL) or Tools
> AI (QUILL Lite), or Engine Tools... in the task window. Chapter 4.

- **About these tools** (read-only text): what turning on an engine's own
  tools means.
- One **check box** per tool, under a heading naming the engine, such as
  "GitHub Copilot's own tools". Each is off until you check it. Focus starts
  on the first.
- **OK** (button): keeps what you checked, for this project.
- **Cancel** (button): closes without changing anything. Escape does the
  same.

## Allow This Step?

Opened when an engine wants to use one of its own tools that you checked.

- **What will happen** (read-only text): "The engine's own shell tool:" and
  what it wants to do.
- **Allow once** (button, the default): lets this one step happen.
- **Allow for this task** (button): lets steps like this one happen until the
  task ends. The next task asks afresh.
- **Don't allow** (button): stops this step. Escape does the same.

## Undo Last Agent Turn (when undo refuses)

A Yes or No question when Undo Last Turn would overwrite your own edits. It
names the file and asks whether to open the file as it was before the agent's
turn, to compare. Yes opens that copy as a separate document, named like
"cli.py before turn 2.py". Your own file is not changed either way.

## The Project part of the status bar

Not a window, but you reach it like one. It says "Project cli-tool, main",
and adds ", waiting for you" when the task has a question you have not seen.
Enter on it opens Do a Project Task.

## Where to next

- Previous: [Chapter 14: Every developer key](developer-14-keys.html)
- Next: [Contents](developer-guide.html)
- [Contents](developer-guide.html)
