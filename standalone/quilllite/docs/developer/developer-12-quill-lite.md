# Chapter 12: QUILL Lite differences

## What this chapter covers

Project tasks in QUILL Lite are the same feature as in QUILL, built from the
same code: the same windows, the same words, the same rules. This chapter
lists the few places the two editors differ, so you can move between them
without surprises.

## The same in both

- Every window in Chapter 15, with the same controls and the same access
  keys.
- Every sentence you hear: QUILL and QUILL Lite cannot word the same moment
  two ways, because both read their sentences from one place.
- The engines, the project boundary, the permissions, the never list, the
  allow list and the bypass, the checkpoints and Undo Last Turn, the agent
  notes question, coach mode, the transcript and the command output.
- `Ctrl+3` opens Do a Project Task while a project is open, and `Ctrl+4` is
  Choose Your AI.
- The tutorial lesson, **Your first project task**, in **Help >
  Tutorials...** (`Ctrl+Alt+F1`).

Each editor keeps its own records for a project, in its own data folder. So
if you work on one project in both, its allowed commands, your answer about
its agent notes and the engine tools you checked are set in each editor
separately, and Undo Last Turn undoes the turns made in that editor.

## Turning it on

| | QUILL | QUILL Lite |
|---|---|---|
| The profile | Developer, in Switch Profile (`Alt+Shift+P`) or Profiles and Features | Developer, in Customize Features (`Ctrl+Alt+F10`) |
| On its own | Developer Tools, in Manage Individual Features (`Ctrl+Alt+F10`) | Coding: project tasks with an AI, in Customize Features |
| The AI switch | AI > Use Artificial Intelligence | The AI help area, in Customize Features; the Developer profile leaves it off |

The last row is the one that catches people. Chapter 1 explains it.

## Where the commands are

The commands sit in the same menus in both editors, with one exception: QUILL
has a top-level AI menu, and QUILL Lite keeps its AI commands in **Tools >
AI**.

| Menu | QUILL | QUILL Lite |
|---|---|---|
| File | Open Project Folder..., Close Project | the same |
| Edit > Agent Work | Undo Last Agent Turn, Stop Agent | the same |
| View | Agent Task Transcript, Agent Command Output | the same |
| Tools | Commands Allowed in This Project... | the same |
| AI | Do a Project Task..., Explain Last Turn, Engine Tools for This Project... | in Tools > AI |

## Keys

- **In QUILL,** Stop Agent and Undo Last Agent Turn are on the QUILL key:
  `Ctrl+Shift+Grave, K` and `Ctrl+Shift+Grave, U`.
- **In QUILL Lite,** none of the project commands has a key of its own. No
  chord was free in both editors. You rarely need one: `Ctrl+3` opens the
  task whenever a project is open, and the task window has a key for
  everything in it. Each menu row has an access letter, and the Command
  Palette (`Ctrl+Shift+P`) finds them all by name.

In either editor, you can give any of the commands a key of your own.

## The Project part of the status bar

- **QUILL:** a status bar part that is hidden until you first open a
  project; then QUILL shows it for you.
- **QUILL Lite:** a part shown only while a project is open.

Both say the same thing and both open the task on Enter.

## Files you have open

Both editors reload a file the task changed, with your cursor kept, and leave
it alone when it has unsaved edits or is in rich text. QUILL reloads only
plain text, Markdown, Python, JavaScript, TypeScript, JSON, TOML and YAML
files in place; QUILL Lite reloads any plain text window.

## What QUILL Lite does not have

QUILL Lite is the editor-only sibling, so the developer tools that are not
about editing are QUILL's alone: Local Git and worktrees, GitHub and
Codespaces, editing over SSH, the Developer Console, Word Prediction, shell
integration and Validate Agents. QUILL Lite has the folder search, encodings
and line endings, document language, folding, line comments and the
indentation tools (Chapter 11).

QUILL Lite is never ahead of QUILL: anything it gains for coding, QUILL gains
in the same change.

## Where to next

- Previous: [Chapter 11: Code editing in the editor itself](developer-11-code-editing.html)
- Next: [Chapter 13: Troubleshooting](developer-13-troubleshooting.html)
- [Contents](developer-guide.html)
