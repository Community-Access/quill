# QUILL for Developers

This is the developer's manual for QUILL and QUILL Lite. It covers coding
with an AI in your own project folder, which both editors share from the same
code, and the code editing features of the editor itself. It is a book of its
own, beside each editor's user guide, because nobody who does not write code
needs any of it.

Everything here lives behind one choice, the **Developer** profile. Until you
choose it, none of it appears: not in the menus, not in the Command Palette,
not in the tutorials.

## How to read this manual

- **New to project tasks?** Read Chapters 1, 2 and 3, in that order. They
  take you from turning the tools on to a finished, undone task in a practice
  folder. Then dip into the rest as you need it.
- **Want to know what the AI may and may not do?** Chapters 2 and 5 are the
  whole answer: the project boundary, and the permissions.
- **Learning to code?** Read Chapter 9, on coach mode, after Chapter 3.
- **Using QUILL Lite?** Everything applies; Chapter 12 has the few
  differences, and Chapter 1 the one extra check box.
- **Looking something up?** Chapter 14 has every key and Chapter 15 every
  window, control by control.
- **Something went wrong?** Chapter 13 has the sentences QUILL says, and what
  to do about each.

Every chapter starts with a short "what this chapter covers" and ends with
links to the chapters either side and back to these contents. Headings are
real headings, so your screen reader's heading keys move through each chapter.
Throughout, "cli-tool" stands for your own project folder's name, which QUILL
says in its place.

## Keys at a glance

- **Ctrl+3** opens Do a Project Task while a project is open, and Do a
  Document Task when none is. One key, in both editors.
- **Ctrl+4** opens Choose Your AI, where you pick the engine.
- **In the task window:** Alt+I Instruction, Alt+P the plan, Alt+H the
  changes, Alt+O the last command's output, Alt+R the transcript, Alt+U Undo
  Last Turn, Alt+X Explain Last Turn, Alt+A Coach mode, Alt+T Stop.
- **In QUILL,** the QUILL key (Ctrl+Shift+Grave, Grave being the key below
  Escape) then K stops the agent from any window, and then U undoes the last
  agent turn. In QUILL Lite these are Edit > Agent Work.
- **In Review Changes:** Space takes or leaves a file, Enter moves to its
  changes, Alt+A and Alt+R accept and reject, Alt+N and Alt+P move, and Enter
  on Apply Accepted Changes writes what you accepted. Escape writes nothing.
- **In Run This Command?:** Enter allows once, Escape does not allow.
- **Ctrl+Shift+P**, the Command Palette, finds every developer command by
  name.
- **F1** on any control says what it is for.

[Chapter 14](developer-14-keys.html) has every key.

## Contents

### [Chapter 1: Turning on the Developer profile](developer-01-the-developer-profile.html)

How to turn the coding tools on in each editor, what the Developer profile
changes area by area, the one extra check box QUILL Lite needs, and turning it
all off again.

- [Why there is a profile at all](developer-01-the-developer-profile.html#why-there-is-a-profile-at-all)
- [Turning it on in QUILL](developer-01-the-developer-profile.html#turning-it-on-in-quill)
- [Turning it on in QUILL Lite](developer-01-the-developer-profile.html#turning-it-on-in-quill-lite)
- [In QUILL, Use Artificial Intelligence must be on](developer-01-the-developer-profile.html#in-quill-use-artificial-intelligence-must-be-on)
- [What the Developer profile changes, area by area](developer-01-the-developer-profile.html#what-the-developer-profile-changes-area-by-area)
- [Turning it off again](developer-01-the-developer-profile.html#turning-it-off-again)
- [Safe Mode](developer-01-the-developer-profile.html#safe-mode)

### [Chapter 2: Opening a project, and the project boundary](developer-02-projects.html)

A project is a folder. Opening and closing one, the Project part of the status
bar, what Ctrl+3 does while a project is open, and exactly what the agent may
and may not see.

- [A project is just a folder](developer-02-projects.html#a-project-is-just-a-folder)
- [Opening one](developer-02-projects.html#opening-one)
- [The Project part of the status bar](developer-02-projects.html#the-project-part-of-the-status-bar)
- [What changes about Ctrl+3](developer-02-projects.html#what-changes-about-ctrl3)
- [Closing a project](developer-02-projects.html#closing-a-project)
- [The project boundary](developer-02-projects.html#the-project-boundary)

### [Chapter 3: Your first project task](developer-03-first-project-task.html)

One whole task, step by step, from a practice folder to an undone turn, with
what you hear at each step.

- [Before you start](developer-03-first-project-task.html#before-you-start)
- [Step 1: make a practice folder](developer-03-first-project-task.html#step-1-make-a-practice-folder)
- [Step 2: open the folder as a project](developer-03-first-project-task.html#step-2-open-the-folder-as-a-project)
- [Step 3: open the task window and ask](developer-03-first-project-task.html#step-3-open-the-task-window-and-ask)
- [Step 4: read the plan](developer-03-first-project-task.html#step-4-read-the-plan)
- [Step 5: review the change](developer-03-first-project-task.html#step-5-review-the-change)
- [Step 6: allow the test command](developer-03-first-project-task.html#step-6-allow-the-test-command)
- [Step 7: hear the closing summary](developer-03-first-project-task.html#step-7-hear-the-closing-summary)
- [Step 8: undo the whole turn](developer-03-first-project-task.html#step-8-undo-the-whole-turn)
- [Step 9: try coach mode](developer-03-first-project-task.html#step-9-try-coach-mode)
- [Stopping at any point](developer-03-first-project-task.html#stopping-at-any-point)
- [If you are elsewhere when the task needs you](developer-03-first-project-task.html#if-you-are-elsewhere-when-the-task-needs-you)
- [That is the whole loop](developer-03-first-project-task.html#that-is-the-whole-loop)

### [Chapter 4: Engines, and choosing one](developer-04-engines.html)

The four AIs that can run a project task, how to choose one, why they all
behave the same in front of you, and the engine's own tools, only if you turn
them on.

- [Which AI can run a project task](developer-04-engines.html#which-ai-can-run-a-project-task)
- [Choosing](developer-04-engines.html#choosing)
- [Every engine behaves the same in front of you](developer-04-engines.html#every-engine-behaves-the-same-in-front-of-you)
- [How each engine is held](developer-04-engines.html#how-each-engine-is-held)
- [Engine tools, only if you choose](developer-04-engines.html#engine-tools-only-if-you-choose)
- [What is never available, whatever you choose](developer-04-engines.html#what-is-never-available-whatever-you-choose)

### [Chapter 5: Permissions, the allow list and the bypass](developer-05-permissions.html)

The whole permission model: what needs no permission, what asks, what is never
run, the per-project allow list, the bypass, and what QUILL cannot stop on
Windows.

- [The short version](developer-05-permissions.html#the-short-version)
- [Reading needs no permission](developer-05-permissions.html#reading-needs-no-permission)
- [Changes are proposals](developer-05-permissions.html#changes-are-proposals)
- [Commands ask](developer-05-permissions.html#commands-ask)
- [What QUILL never runs for an agent](developer-05-permissions.html#what-quill-never-runs-for-an-agent)
- [The allow list: Commands Allowed in This Project](developer-05-permissions.html#the-allow-list-commands-allowed-in-this-project)
- [The bypass: Run commands without asking](developer-05-permissions.html#the-bypass-run-commands-without-asking)
- [Engine tools ask too](developer-05-permissions.html#engine-tools-ask-too)
- [What QUILL cannot stop on Windows](developer-05-permissions.html#what-quill-cannot-stop-on-windows)

### [Chapter 6: Running commands and reading their output](developer-06-commands.html)

Run This Command?, the three warnings, how a command runs, the one-sentence
result, and the full output as a document.

- [Run This Command?](developer-06-commands.html#run-this-command)
- [The three warnings](developer-06-commands.html#the-three-warnings)
- [How a command runs](developer-06-commands.html#how-a-command-runs)
- [The result, in one sentence](developer-06-commands.html#the-result-in-one-sentence)
- [The full output](developer-06-commands.html#the-full-output)
- [Commands and Undo Last Turn](developer-06-commands.html#commands-and-undo-last-turn)

### [Chapter 7: Reviewing changes, and undoing a turn](developer-07-review-and-undo.html)

Review Changes for one file or many, how each change is read, files you have
open, the checkpoints under every turn, Undo Last Agent Turn and Stop Agent.

- [When Review Changes opens](developer-07-review-and-undo.html#when-review-changes-opens)
- [The file list](developer-07-review-and-undo.html#the-file-list)
- [One change at a time](developer-07-review-and-undo.html#one-change-at-a-time)
- [The buttons](developer-07-review-and-undo.html#the-buttons)
- [Applying](developer-07-review-and-undo.html#applying)
- [Files you have open](developer-07-review-and-undo.html#files-you-have-open)
- [The checkpoints under every turn](developer-07-review-and-undo.html#the-checkpoints-under-every-turn)
- [Undo Last Agent Turn](developer-07-review-and-undo.html#undo-last-agent-turn)
- [Stop Agent](developer-07-review-and-undo.html#stop-agent)

### [Chapter 8: Agent notes in the repository](developer-08-agent-notes.html)

AGENTS.md and every other agent instruction file QUILL recognises, the one
question it asks per project, and why nothing in them can approve anything.

- [The files QUILL finds](developer-08-agent-notes.html#the-files-quill-finds)
- [The question, asked once per project](developer-08-agent-notes.html#the-question-asked-once-per-project)
- [How the notes reach the engine](developer-08-agent-notes.html#how-the-notes-reach-the-engine)
- [Notes are data, never instructions](developer-08-agent-notes.html#notes-are-data-never-instructions)
- [Writing notes for your own project](developer-08-agent-notes.html#writing-notes-for-your-own-project)

### [Chapter 9: Coach mode and explanations](developer-09-coach-mode.html)

Coach mode, where the agent teaches and you type; Explain Last Turn; Why This
Change?; and the agent's questions to you.

- [Coach mode](developer-09-coach-mode.html#coach-mode)
- [Explain Last Turn](developer-09-coach-mode.html#explain-last-turn)
- [Why This Change?](developer-09-coach-mode.html#why-this-change)
- [Errors in plain words](developer-09-coach-mode.html#errors-in-plain-words)
- [A question from the agent](developer-09-coach-mode.html#a-question-from-the-agent)
- [A suggested way to learn](developer-09-coach-mode.html#a-suggested-way-to-learn)

### [Chapter 10: The transcript, and what QUILL keeps](developer-10-transcript.html)

The conversation, the transcript as a document with a heading per turn,
keeping a copy, and everything QUILL keeps about a project.

- [The conversation](developer-10-transcript.html#the-conversation)
- [The transcript](developer-10-transcript.html#the-transcript)
- [The command output](developer-10-transcript.html#the-command-output)
- [What QUILL keeps, and where](developer-10-transcript.html#what-quill-keeps-and-where)

### [Chapter 11: Code editing in the editor itself](developer-11-code-editing.html)

The code features of the editor itself: languages and tokens, folding,
comments and indentation, encodings, folder search, Git, GitHub, SSH, the
Developer Console and more.

- [One plain editor, on purpose](developer-11-code-editing.html#one-plain-editor-on-purpose)
- [Languages, and moving by token](developer-11-code-editing.html#languages-and-moving-by-token)
- [Folding that never hides text](developer-11-code-editing.html#folding-that-never-hides-text)
- [Comments, indentation and brackets](developer-11-code-editing.html#comments-indentation-and-brackets)
- [Finding your way through a file](developer-11-code-editing.html#finding-your-way-through-a-file)
- [Abbreviations for HTML and CSS](developer-11-code-editing.html#abbreviations-for-html-and-css)
- [Encodings and line endings](developer-11-code-editing.html#encodings-and-line-endings)
- [Searching and replacing across a folder](developer-11-code-editing.html#searching-and-replacing-across-a-folder)
- [Git, in QUILL](developer-11-code-editing.html#git-in-quill)
- [GitHub, in QUILL](developer-11-code-editing.html#github-in-quill)
- [Editing over SSH, in QUILL](developer-11-code-editing.html#editing-over-ssh-in-quill)
- [The Developer Console, in QUILL](developer-11-code-editing.html#the-developer-console-in-quill)
- [Word prediction, in QUILL](developer-11-code-editing.html#word-prediction-in-quill)
- [Shell integration, in QUILL](developer-11-code-editing.html#shell-integration-in-quill)
- [Validate Agents, in QUILL](developer-11-code-editing.html#validate-agents-in-quill)

### [Chapter 12: QUILL Lite differences](developer-12-quill-lite.html)

Where QUILL Lite differs from QUILL: turning it on, the menus, keys, the
status bar, and the tools only QUILL has.

- [The same in both](developer-12-quill-lite.html#the-same-in-both)
- [Turning it on](developer-12-quill-lite.html#turning-it-on)
- [Where the commands are](developer-12-quill-lite.html#where-the-commands-are)
- [Keys](developer-12-quill-lite.html#keys)
- [The Project part of the status bar](developer-12-quill-lite.html#the-project-part-of-the-status-bar)
- [Files you have open](developer-12-quill-lite.html#files-you-have-open)
- [What QUILL Lite does not have](developer-12-quill-lite.html#what-quill-lite-does-not-have)

### [Chapter 13: Troubleshooting](developer-13-troubleshooting.html)

The sentences you hear when something does not work, what each means, and what
to do.

- [The commands are not in the menus](developer-13-troubleshooting.html#the-commands-are-not-in-the-menus)
- ["Project tasks are part of the Developer profile."](developer-13-troubleshooting.html#project-tasks-are-part-of-the-developer-profile)
- ["AI help is switched off."](developer-13-troubleshooting.html#ai-help-is-switched-off)
- [In QUILL Lite, Ctrl+3 does nothing](developer-13-troubleshooting.html#in-quill-lite-ctrl3-does-nothing)
- ["AI is off in Safe Mode."](developer-13-troubleshooting.html#ai-is-off-in-safe-mode)
- ["No project is open. Choose Open Project Folder first."](developer-13-troubleshooting.html#no-project-is-open-choose-open-project-folder-first)
- [Ctrl+3 opened Do a Document Task](developer-13-troubleshooting.html#ctrl3-opened-do-a-document-task)
- [The task will not start, or says your AI cannot run tasks](developer-13-troubleshooting.html#the-task-will-not-start-or-says-your-ai-cannot-run-tasks)
- [With Claude or Ollama, the window says "No engine" or "GitHub Copilot"](developer-13-troubleshooting.html#with-claude-or-ollama-the-window-says-no-engine-or-github-copilot)
- [Engine Tools says "This engine offers no tools of its own here."](developer-13-troubleshooting.html#engine-tools-says-this-engine-offers-no-tools-of-its-own-here)
- ["A project task is running. Stop it, or let it finish, before closing the project."](developer-13-troubleshooting.html#a-project-task-is-running-stop-it-or-let-it-finish-before-closing-the-project)
- [The task is waiting, and nothing has opened](developer-13-troubleshooting.html#the-task-is-waiting-and-nothing-has-opened)
- [A command I expected to run without asking still asks](developer-13-troubleshooting.html#a-command-i-expected-to-run-without-asking-still-asks)
- [The agent says I keep this step for myself](developer-13-troubleshooting.html#the-agent-says-i-keep-this-step-for-myself)
- [A command fails at once, but works in my terminal](developer-13-troubleshooting.html#a-command-fails-at-once-but-works-in-my-terminal)
- [A command has been running for a long time](developer-13-troubleshooting.html#a-command-has-been-running-for-a-long-time)
- [The task stopped after 40 steps](developer-13-troubleshooting.html#the-task-stopped-after-40-steps)
- [My open file did not update after the task changed it](developer-13-troubleshooting.html#my-open-file-did-not-update-after-the-task-changed-it)
- ["cli.py has changed since the agent's turn. Undo would lose your edits."](developer-13-troubleshooting.html#clipy-has-changed-since-the-agents-turn-undo-would-lose-your-edits)
- ["There is no agent turn to undo in this project."](developer-13-troubleshooting.html#there-is-no-agent-turn-to-undo-in-this-project)
- [Undo did not bring back a big file](developer-13-troubleshooting.html#undo-did-not-bring-back-a-big-file)
- ["There is no turn to explain yet."](developer-13-troubleshooting.html#there-is-no-turn-to-explain-yet)
- [The agent ignored the project's AGENTS.md](developer-13-troubleshooting.html#the-agent-ignored-the-projects-agentsmd)
- [The agent cannot see a file](developer-13-troubleshooting.html#the-agent-cannot-see-a-file)
- [The transcript I wanted has gone](developer-13-troubleshooting.html#the-transcript-i-wanted-has-gone)

### [Chapter 14: Every developer key](developer-14-keys.html)

Every key in this manual: editor-wide, in each developer window, and for
editing code, in both editors.

- [Editor-wide keys](developer-14-keys.html#editor-wide-keys)
- [Do a Project Task](developer-14-keys.html#do-a-project-task)
- [Review Changes](developer-14-keys.html#review-changes)
- [Run This Command?](developer-14-keys.html#run-this-command)
- [Commands Allowed in This Project](developer-14-keys.html#commands-allowed-in-this-project)
- [Open Project Folder](developer-14-keys.html#open-project-folder)
- [Use This Project's Agent Notes?](developer-14-keys.html#use-this-projects-agent-notes)
- [Engine Tools for This Project](developer-14-keys.html#engine-tools-for-this-project)
- [Allow This Step?](developer-14-keys.html#allow-this-step)
- [Code editing keys](developer-14-keys.html#code-editing-keys)

### [Chapter 15: Window reference](developer-15-window-reference.html)

Every developer window, with every control by the name your screen reader
says, in Tab order.

- [Open Project Folder](developer-15-window-reference.html#open-project-folder)
- [Use This Project's Agent Notes?](developer-15-window-reference.html#use-this-projects-agent-notes)
- [Do a Project Task](developer-15-window-reference.html#do-a-project-task)
- [Review Changes](developer-15-window-reference.html#review-changes)
- [Run This Command?](developer-15-window-reference.html#run-this-command)
- [Keep Waiting?](developer-15-window-reference.html#keep-waiting)
- [Continue?](developer-15-window-reference.html#continue)
- [Commands Allowed in This Project](developer-15-window-reference.html#commands-allowed-in-this-project)
- [Run Commands Without Asking?](developer-15-window-reference.html#run-commands-without-asking)
- [Engine Tools for This Project](developer-15-window-reference.html#engine-tools-for-this-project)
- [Allow This Step?](developer-15-window-reference.html#allow-this-step)
- [Undo Last Agent Turn (when undo refuses)](developer-15-window-reference.html#undo-last-agent-turn-when-undo-refuses)
- [The Project part of the status bar](developer-15-window-reference.html#the-project-part-of-the-status-bar)

## About this manual

This manual describes the Developer profile as it ships in the current QUILL
and QUILL Lite. The plan of record for the coding features is
`docs/design/code.md` in QUILL's source. If something here does not match what
you hear, tell us through **Help > Get Help from Support**.
# GitHub Workbench update

QUILL and QUILL Lite share the GitHub Items, Explore, diff, and PR review
surfaces. The review reader is a native tree: expand a PR, arrow to a file and
thread, then Tab to read its detail. Ctrl+R replies and Ctrl+Shift+R resolves or
reopens when permitted. Global search, My Work, activity, repository and people
views, Pages, labels, notifications, and workflow job logs live in Explore or
Items. See the [complete keyboard and screen reader reference](../../github/workbench-reference.md)
and [Tutorial 8](../../tutorials/08-github-inside-quill.md). Separate repository
administration and Local Git commands are currently available in QUILL.
