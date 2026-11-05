# Chapter 14: Every developer key

## What this chapter covers

Every key this manual teaches, in one place: the editor-wide keys, then each
developer window's keys, then the code editing keys. Grave is the key below
Escape, and the QUILL key is `Ctrl+Shift+Grave`. All of these can be changed
in the Keymap Editor, and the Command Palette (`Ctrl+Shift+P`) finds every
command by name, key or none.

## Editor-wide keys

| Key | QUILL | QUILL Lite |
|---|---|---|
| `Ctrl+3` | Do a Project Task with a project open; Do a Document Task without | the same |
| `Ctrl+4` | Choose Your AI | the same |
| `Ctrl+Shift+Grave, K` | Stop Agent | none |
| `Ctrl+Shift+Grave, U` | Undo Last Agent Turn | none |
| `Ctrl+Shift+P` | Command Palette | the same |
| `Ctrl+Alt+F1` | Tutorials | the same |
| `Alt+Shift+P` | Switch Profile | none |
| `Ctrl+Alt+F10` | Manage Individual Features | Customize Features |
| `F1` | Help for the focused control | the same |

These have no key of their own in either editor, by default: Open Project
Folder, Close Project, Do a Project Task (use `Ctrl+3`), Explain Last Turn,
Agent Task Transcript, Agent Command Output, Commands Allowed in This Project
and Engine Tools for This Project. In QUILL Lite, Stop Agent and Undo Last
Agent Turn have none either. Every one is in the Command Palette, and each
menu row has an access letter.

## Do a Project Task

| Key | What it does |
|---|---|
| `Alt+I` | Instruction, where you type; focus starts here |
| Enter, or `Alt+S` | Send: start a turn, or send a follow-up to the running one |
| `Alt+C` | Conversation, read with the arrow keys |
| `Alt+P` | Plan: the cursor to the latest plan |
| `Alt+H` | Changes: the cursor to the latest list of changes |
| `Alt+O` | Output: the last command's full output, as a document |
| `Alt+R` | Transcript: the whole task, as a document |
| `Alt+U` | Undo Last Turn |
| `Alt+X` | Explain Last Turn |
| `Alt+A` | Coach mode, a check box |
| `Alt+W` | Allowed Commands... |
| `Alt+L` | Engine Tools... |
| `Alt+T` | Stop |

## Review Changes

| Key | What it does |
|---|---|
| `Alt+F` | Files |
| Space, in Files | Take the whole file, or leave it |
| Enter, in Files | Move to the file's changes |
| `Alt+D` | Change details |
| `Alt+A` | Accept the change shown |
| `Alt+R` | Reject the change shown |
| `Alt+N` | Next Change, then the next file's |
| `Alt+P` | Previous Change |
| `Alt+I` | Accept All in File |
| `Alt+L` | Reject All in File |
| `Alt+W` | Why This Change? |
| Enter | Apply Accepted Changes |
| Escape | Reject All: write nothing |

## Run This Command?

| Key | What it does |
|---|---|
| `Alt+C` | Command, the exact text |
| `Alt+W` | Warning, when there is one |
| Enter, or `Alt+O` | Allow once |
| `Alt+A` | Always allow this command here, when offered |
| Escape, or `Alt+D` | Don't allow |

The long-command question, Keep Waiting?, is Yes or No: No stops the command.

## Commands Allowed in This Project

| Key | What it does |
|---|---|
| `Alt+A` | Allowed commands |
| Delete, in the list | Remove the selected command |
| `Alt+N` | New command; Enter adds it |
| `Alt+D` | Add |
| `Alt+R` | Remove |
| `Alt+W` | Run commands without asking, a check box |
| Escape | Close; every change is already saved |

## Open Project Folder

| Key | What it does |
|---|---|
| `Alt+R` | Recent projects |
| Enter or Space, in the list | Open the selected project |
| `Alt+B` | Browse for a Folder... |
| Escape | Cancel |

## Use This Project's Agent Notes?

| Key | What it does |
|---|---|
| `Alt+R` | Read Them First |
| `Alt+N` | Notes, after Read Them First |
| Enter, or `Alt+U` | Use Them |
| Escape, or `Alt+D` | Don't Use Them |

## Engine Tools for This Project

Tab through the check boxes, one per tool, and Space checks or unchecks one.
Enter is OK, which keeps what you checked; Escape is Cancel.

## Allow This Step?

Used for an engine's own tools, when you have checked any.

| Key | What it does |
|---|---|
| Enter, or `Alt+O` | Allow once |
| `Alt+T` | Allow for this task |
| Escape, or `Alt+D` | Don't allow |

## Code editing keys

| Command | QUILL | QUILL Lite |
|---|---|---|
| Set Document Language / Document Language | `Ctrl+Alt+F6` | `Ctrl+Alt+F6` |
| Select Token | `Ctrl+Alt+Space` | none |
| Toggle Fold / Fold or Unfold Section | `Ctrl+Shift+[` | `Ctrl+Shift+F9` |
| Next Fold | `Alt+Shift+]` | none |
| Previous Fold | `Alt+Shift+[` | none |
| List Folds | `Ctrl+Shift+]` | none |
| Toggle Line Comment | `Ctrl+/` | `Ctrl+/` |
| Toggle Block Comment | `Ctrl+Shift+/` | none |
| Indent | `Ctrl+]` | `Ctrl+]` |
| Outdent | `Ctrl+[` | `Ctrl+[` |
| Describe Indent Depth | `Ctrl+Alt+Shift+V` | `Ctrl+Alt+Shift+V` |
| Convert indentation to spaces | `Alt+F11` | `Alt+F11` |
| Convert indentation to tabs | `Alt+F12` | `Alt+F12` |
| Tab key mode | `Ctrl+Alt+Shift+I` | `Ctrl+Alt+Shift+I` |
| Match Bracket | `Ctrl+Shift+\` | none |
| Go To Line / Go To | `Ctrl+G` | `Ctrl+G` |
| Outline Navigator / List Headings | `Ctrl+Shift+O` or `Ctrl+Alt+L` | `Ctrl+Alt+L` |
| File Format / File Encoding and Line Endings | `Ctrl+Alt+E` | `Ctrl+Alt+E` |
| Search in Files | `Ctrl+Alt+Shift+F` | `Ctrl+Alt+Shift+F` |
| Replace Across Files | `Ctrl+Shift+R` | `Ctrl+Shift+R` |
| Word Prediction | `Ctrl+.` | none |

The Local Git, GitHub, SSH and Developer Console commands have no default
keys; Chapter 11 says where each one is.

## Where to next

- Previous: [Chapter 13: Troubleshooting](developer-13-troubleshooting.html)
- Next: [Chapter 15: Window reference](developer-15-window-reference.html)
- [Contents](developer-guide.html)
