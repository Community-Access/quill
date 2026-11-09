# Chapter 11: Code editing in the editor itself

## What this chapter covers

Project tasks are one half of QUILL for developers. The other half is the
editor you write code in yourself. This chapter is a tour of the code editing
features in QUILL and QUILL Lite: languages and tokens, folding, comments and
indentation, encodings and line endings, searching a whole folder, Git and
GitHub, editing over SSH, the Developer Console and word prediction. Each
editor's user guide covers these in full; this chapter tells you what exists,
where it lives, and its key.

## One plain editor, on purpose

QUILL edits code in the same text control it uses for everything else, which
is what screen readers handle best. There is no special code surface to learn,
no inline completion and no ghost text. The features below add to that control
rather than replace it.

## Languages, and moving by token

When you open a source file, QUILL picks a language profile from the file's
extension. It knows HTML, Markdown, CSS, Python, JavaScript, TypeScript, C,
C++, C#, PHP, Go, Rust, Kotlin, Shell, YAML, JSON, TOML and SQL.

- **Set Document Language...** (`Ctrl+Alt+F6`) chooses the language yourself,
  for an unsaved file or code pasted into a `.txt`. In QUILL it is on the
  Navigate menu, and **Format > Document Language** is the same choice as a
  list. In QUILL Lite it is **Format > Document Language...**, on the same
  key.
- In QUILL, **Navigate > Next Token** and **Previous Token** move by code
  token rather than by word, landing on the next name, keyword, operator or
  value. **Select Token** (`Ctrl+Alt+Space`) selects the one you are on.

## Folding that never hides text

Folding in QUILL changes only where the jump commands take you. It never
hides lines from the arrow keys, so you can always tell folded text from
deleted text.

In QUILL:

- **Toggle Fold** (`Ctrl+Shift+[`) folds or unfolds the heading section or
  fenced code block around the cursor, and says what happened.
- **Next Fold** (`Alt+Shift+]`) and **Previous Fold** (`Alt+Shift+[`) jump
  between regions, saying each one's name, state and length.
- **List Folds...** (`Ctrl+Shift+]`) lists every region you can fold.

In QUILL Lite, **Navigate > Fold or Unfold Section** (`Ctrl+Shift+F9`).

## Comments, indentation and brackets

| Command | QUILL | QUILL Lite |
|---|---|---|
| Toggle Line Comment | `Ctrl+/` | `Ctrl+/` |
| Toggle Block Comment | `Ctrl+Shift+/` | none |
| Indent | `Ctrl+]` | `Ctrl+]` |
| Outdent | `Ctrl+[` | `Ctrl+[` |
| Describe Indent Depth | `Ctrl+Alt+Shift+V` | `Ctrl+Alt+Shift+V` |
| Convert indentation to spaces | `Alt+F11` | `Alt+F11` |
| Convert indentation to tabs | `Alt+F12` | `Alt+F12` |
| Tab key inserts a tab character, or indents | `Ctrl+Alt+Shift+I` | `Ctrl+Alt+Shift+I` |
| Match Bracket | `Ctrl+Shift+\` | none |

Comments use the language's own style: `#`, `//`, `<!-- -->` or `--`. In
QUILL Lite the indentation commands are under **Tools > Indenting**.

## Finding your way through a file

- **Go To Line** (`Ctrl+G`) in QUILL; **Go To...** on the same key in QUILL
  Lite.
- **Outline Navigator...** (`Ctrl+Shift+O`, or `Ctrl+Alt+L`) in QUILL lists
  the document's structure, to jump to. In QUILL Lite, **List
  Headings...** is on `Ctrl+Alt+L`.

## Abbreviations for HTML and CSS

QUILL's Edit menu has **Expand Abbreviation**, **Preview Abbreviation...** and
**Explain Abbreviation...**, which turn short Emmet-style abbreviations such
as `ul>li*3` into full markup, or CSS shorthand into declarations. Preview
shows the result in a new tab without touching your document; Explain says
what an abbreviation means before you use it.

## Encodings and line endings

A code file has to go back to disk exactly as it came, or the next commit
shows every line changed.

- In QUILL, **File Format** (`Ctrl+Alt+E`) shows and changes the encoding
  and line endings.
- In QUILL Lite, **Tools > File Encoding and Line Endings...** is on the same
  key.

Both keep a file's encoding and line endings when they save, unless you
change them.

## Searching and replacing across a folder

Both editors search a whole folder, which is handy alongside a project task:

- **Search in Files...** (`Ctrl+Alt+Shift+F`) lists every match across a
  folder, to jump to.
- **Replace Across Files...** (`Ctrl+Shift+R`) replaces across a folder.

In QUILL Lite both are on the Edit menu.

## Git, in QUILL

Everything under **Tools > Git and GitHub > Local Git** works on any git
repository on your computer, with no account and no network. It needs the
Developer profile, or Developer Tools checked, and `git`; if you do not have
git, **Help > Download Optional Components** has a portable copy.

- **Uncommitted Changes...:** every changed file, staged and unstaged, with
  each file's changes read the way Compare Documents reads them, and Stage,
  Unstage and Stage All.
- **Switch Branch...,** which warns you about uncommitted changes and never
  quietly throws them away.
- **Stash Changes...** and **Manage Stashes...,** by name rather than
  `stash@{2}`.
- **Who Wrote This Line...,** git blame for the line you are on.
- **Start Bisect...** and **End Bisect,** as plain questions: "Is this
  version good or bad?"
- **Resolve Conflicts...,** one conflict at a time: "Conflict 1 of 3: your
  version says X, their version says Y."
- **Interactive Rebase...** as a real list, and **Abort Rebase.**
- **Worktrees...** and **New Worktree...:** a second folder on another
  branch, so the file under your cursor is never rewritten by a branch
  switch.

None of these has a default key; every letter after the QUILL key is taken.
Give any of them one in the Keymap Editor, or find them in the Command
Palette (`Ctrl+Shift+P`), where they start "Local Git:".

Project tasks never commit, branch, stash or push for you. The agent can read
the branch and the changed files, and a commit happens only if you ask for one
in words and allow the command; pushing is never run (Chapter 5).

## GitHub, in QUILL

With **GitHub Remote Access** on (it needs Developer Tools):

- **File > Open from Remote** has Open Remote GitHub Repository..., Open
  Remote GitHub File URL..., Save to GitHub..., Manage GitHub Accounts... and
  Open GitHub Items..., the accessible viewer for issues, pull requests,
  branches and workflows. Pull request diffs read as a file list with QUILL's
  spoken compare.
- **Tools > Git and GitHub > GitHub** has the repository commands: create,
  fork, rename and change visibility; the default branch and branch
  protection; delete a branch; Commit Multiple Files...; Browse Organization
  Repositories...; Create Release...; Dispatch Workflow...; Notifications...;
  Security Alerts...; and **Codespaces...** and **Create Codespace...**, which
  use the GitHub CLI, `gh`. Creating a Codespace may cost money, and QUILL
  says so and asks first.

The **GitHub Items...** viewer accepts an `owner/repo`, a GitHub repository
address, or a `git@github.com:` remote. If the current document is in a clone
with a GitHub origin, QUILL fills in the repository. **Issues & PRs** is the
combined inbox for the loaded repository; Search queries GitHub with its own
qualifiers, while Quick Filter narrows only the rows already loaded. Branches,
commits, tags, releases, workflow definitions, and workflow runs have their
own views. Compare Branches and the PR Diff reader use QUILL's spoken difference
navigation.

On any Items row or its details field, **Shift+F10** or the Applications key
opens a contextual action menu. PRs offer Review and Diff, branches Compare,
and runs their artifacts. Each selected item offers its GitHub link, a copyable
link and details, and a favorite action; signed-in sessions add the relevant
write actions. This menu is shared with QUILL Lite.

Select a PR and press **Review...** to read merge readiness, the latest review
decision, check runs, and each line comment with its replies. The native PR
outline expands from PR to changed files, review threads, and checks. Arrow to
an item, then Tab into its readable details; Shift+Tab returns. Ctrl+R replies
to the selected thread, and Shift+F10 opens actions for the selected PR, file,
thread, or check. Enter on a file opens its differences; Enter on a check opens
its GitHub job. A signed-in account can submit a review, reply to
the selected review thread, request reviewers, mark a PR draft or ready, and
update its branch. Closed PRs cannot take those review actions. Public PRs can
be read without a token. QUILL identifies outdated review hunks, but it does
not yet show resolved thread state or resolve and reopen threads. The
[GitHub tutorial](../../tutorials/08-github-inside-quill.md) walks through
these controls, while the [workbench plan](../../planning/github-workbench.md)
tracks the remaining GHManage-inspired features.

QUILL Lite opens this same Items viewer and PR review outline from **Tools >
GitHub Workbench...** (**Ctrl+Alt+Shift+F6**). Its menu offers the same actions
because both apps instantiate the same viewer.

## Editing over SSH, in QUILL

**File > Open over SSH > Quick Connect...** and **Site Manager...** open and
save files on a server as if they were on your computer. Unknown host keys
are refused unless you choose to trust a host the first time you connect.

## The Developer Console, in QUILL

**Tools > Advanced > Developer Console** has **Open Python Console...** and
**Open TypeScript Console...**, scripting windows that look inside the running
editor and drive it from code, plus Copy Diagnostic Summary and Restart
TypeScript Worker. The TypeScript console needs Node.js. The console also
needs **Enable Developer Console** on the Administration page of Settings.
Appendix A of the QUILL user guide covers it fully.

## Word prediction, in both editors

**Word Prediction...** (`Ctrl+.`) offers words and tags as a list you choose
from, never as ghost text, and only when you press the key. It works in
every profile, and in QUILL Lite on the same key.

## Shell integration, in QUILL

**Tools > Advanced > Install Shell Integration...** adds QUILL to the Windows
Explorer right-click menu, and **Remove Shell Integration** takes it out
again.

## Validate Agents, in QUILL

If you write agents for QUILL, **Validate Agents** checks agent files against
QUILL's authoring standards, the same rules the build enforces. Open it with
**Validate** on an agent in the AI Library, then check the built-in agents or
browse to a file or folder of your own.

## Where to next

- Previous: [Chapter 10: The transcript, and what QUILL keeps](developer-10-transcript.html)
- Next: [Chapter 12: QUILL Lite differences](developer-12-quill-lite.html)
- [Contents](developer-guide.html)
