# Chapter 11: Keyboard reference

## What this chapter covers

Every key the workbench answers to, one window at a time. Keys marked as
access keys are the underlined letters of a control, pressed with Alt; they
work while that window has focus. Keys that open the windows themselves are in
Chapter 1. QUILL's GitHub menu commands have no keys out of the box, and you
can give them some in the Keymap Editor.

Throughout, Shift+F10 or the Applications key opens the context menu of
whatever has focus, and Escape closes the window you are in. The Workbench
itself is the exception: Escape never closes it, and `Alt+F4` does.

## The GitHub menu, in workbench mode

GitHub Workbench Mode is **View > GitHub Workbench Mode**: `Alt+V`, then `K`.
While it is on, `Alt+G` opens the GitHub menu, and these letters choose a row
in it. They are the same in both apps; the rows marked QUILL only are not in
QUILL Lite's menu.

| Letter | Row |
| --- | --- |
| `V` | Leave Workbench Mode |
| `W` | Open GitHub Workbench |
| `I` | Inbox |
| `S` | This Repository's Issues |
| `P` | This Repository's Pull Requests |
| `A` | Actions Runs |
| `R` | From This Line submenu (in QUILL Lite, its rows are in the menu itself) |
| `D` | Open GitHub Address... (QUILL only) |
| `C` | Clone Repository... |
| `M` | Commit to GitHub... (QUILL only) |
| `Y` | Sync Folder with GitHub... (QUILL only) |
| `L` | Local Git submenu (QUILL only) |
| `G` | Manage GitHub Accounts... |
| `H` | Open GitHub Guide |

None of these rows, and not the mode itself, has a key out of the box. A key
you give one in the Keymap Editor works in both modes.

### From This Line

The line or lines you are on, on GitHub (Chapter 7). In QUILL it is a submenu
of the GitHub menu (`R`), and of **Tools > Git and GitHub > GitHub** (`L`) when
workbench mode is off; in QUILL Lite its rows are in the GitHub menu itself.

| Letter | Row |
| --- | --- |
| `K` | Copy GitHub Link to This Line |
| `O` | Who Changed This Line? (twice: its pull request) |
| `E` | Open the Pull Request for This Line |
| `U` | Open This Line on GitHub |
| `N` | New Issue from Selection... |
| `F` | Issues Mentioning This File |
| `T` | Comment on This Line in the Open Pull Request... |
| `R` | Open the GitHub Reference at the Cursor |

### Clone Repository

| Key | What it does |
| --- | --- |
| `Alt+R` | Move to Repository (owner/name or address) |
| `Alt+I` | Move to Into this folder |
| `Alt+B` | Browse... for the folder |
| Enter | Clone |
| Escape | Close without cloning |

## The GitHub Workbench window

These are the Workbench's own keys. Chapter 12 explains the places they take
you to. Every one of them can be changed in the Keymap Editor, and the menus
always show the key that is really bound. The old GitHub Items and Explore
GitHub windows are retired; everything they did is here.

### Going places

| Key | What it does |
| --- | --- |
| `F6`, `Shift+F6` | Next or previous pane: tree, filter box, list, details, status bar |
| `Ctrl+1` | Inbox, under Needs My Attention (`Alt+Home` too) |
| `Ctrl+2` | The repository the window opened on |
| `Ctrl+3` | Search |
| `Ctrl+4` | People |
| `Ctrl+5` | Gists |
| `Ctrl+6` | Projects |
| `Ctrl+7` | Watches, not built yet |
| `Ctrl+8` | Saved Searches |
| `Ctrl+9` | Start Here |
| `Ctrl+0` | Across Repositories |
| `Ctrl+Shift+1` to `Ctrl+Shift+0` | The current repository's Issues, Pull Requests, Discussions, Actions Runs, Files, Releases, Projects, Security, Settings and Insights |
| `Alt+Up` | The place above this one |
| `Alt+Left`, `Alt+Right` | Back and Forward |
| `Ctrl+L` | Open GitHub Address: `owner/name`, `#42`, `owner/name#42` or any GitHub link |
| `Ctrl+G` | Go to an issue or pull request by number |
| `Ctrl+Period`, `Ctrl+Shift+Period` | Next or previous unread notification |
| `Ctrl+Shift+E` | Back to the editor that opened the Workbench |

`Ctrl+3`, `Ctrl+4` and `Ctrl+8` are AI keys in the editors. The Workbench has
no AI menu, so here they belong to the Go row.

### Doing things to the selected row

| Key | What it does |
| --- | --- |
| Enter | The obvious thing: read an issue, review a pull request, a run's jobs, a branch's commits, a release's files |
| `Alt+Enter` | Properties: everything about it, on one sheet |
| `Shift+Enter` | Open it on GitHub, in your browser |
| `Ctrl+Enter` | Open a file in the editor |
| `Ctrl+N` | New here: issue, pull request, gist, saved search, pin, or the repositories for Across Repositories |
| `Ctrl+Shift+N` | New, asking what to make |
| `Ctrl+Shift+M` | Comment |
| `Ctrl+Shift+D` | A pull request's changed files |
| `Ctrl+Shift+Enter` | Merge a pull request |
| `Ctrl+Shift+B` | Compare a branch with another |
| `Ctrl+Shift+A` | Assign an issue to Copilot |
| `Ctrl+Shift+T` | Start an issue or pull request in a local worktree (QUILL only) |
| `Ctrl+Shift+W` | What failed in a run |
| `Ctrl+Shift+F5` | Re-run a run's failed jobs only |
| `Ctrl+Shift+R` | Run a workflow on a branch |
| `Ctrl+Shift+G` | Repository Actions |
| `Ctrl+Q`, `Ctrl+Shift+Q` | Mark a notification read; mark the whole list read |
| `Ctrl+D` | Add to Favorites, or take it out |
| `Ctrl+C`, `Ctrl+Shift+C` | Copy the row; copy its address |
| Delete | The safe removal for the row, asking first when it cannot be undone |
| `Ctrl+Z`, `Ctrl+Y` | Undo or redo your last change on GitHub, in the tree and the list |

### Lists

| Key | What it does |
| --- | --- |
| `Ctrl+E`, `Ctrl+Shift+F` | Move to the filter box |
| `Ctrl+Alt+F` | Filter Builder |
| `Ctrl+Shift+U` | Choose columns |
| `Ctrl+A` | Select every row |
| `F5` | Refresh |
| `Ctrl+F5` | Refresh, reading everything from GitHub again |
| `Alt+Page Down` | Load more |
| `Ctrl+Shift+Page Down` | Load all |
| `Ctrl+Shift+X` | Export List: the list as shown, as Excel, CSV or a Markdown table |
| `Ctrl+Alt+I` | Import Issues from a Spreadsheet |
| `Ctrl+Alt+L` | New Issues from Lines |
| Escape | Clear the filter box, then go back |

### Account and tools

| Key | What it does |
| --- | --- |
| `Ctrl+Shift+P` | GitHub Permissions |
| `Ctrl+Shift+H` | Change History |
| `Ctrl+Shift+K` | Manage GitHub Accounts |
| `Ctrl+Shift+L` | GitHub's remaining hourly allowance |
| `Ctrl+Shift+O` | Workbench Options |
| `Alt+F4` | Close the Workbench |

### Hearing where you are, and help

| Key | What it does |
| --- | --- |
| `Alt+1` to `Alt+9` | Say where you are, the selection, the item, the counts, your access, the allowance, the filter, what is loading, the account |
| `F9`, `Shift+F9` | Say the last result again; explain it |
| `F1` | What this place and control are for |
| `Shift+F1` | What can I do here, with each key |
| `Alt+F1` | What the GitHub word for the row means |
| `Ctrl+F1` | This guide, at the right chapter |
| `Ctrl+Shift+F1` | Search all of help |
| `Alt+Shift+F1` | Every key in the window |

### New Pull Request

| Key | Control |
| --- | --- |
| `Alt+I` | Merge into |
| `Alt+F` | Merge from |
| `Alt+T` | Title |
| `Alt+D` | Description |
| `Alt+A` | Create as a draft |
| Enter, outside Description | Create Pull Request |
| Escape | Cancel, keeping what you typed for this session |

### An issue form

An issue form's fields are named by the form itself, so they have no access
keys; Tab moves through them in order. Enter, outside a large text box, is
Create Issue, and Escape closes without sending.

## Review pull request

| Key | What it does |
| --- | --- |
| `Ctrl+R` | Reply to the selected thread |
| `Ctrl+Shift+R` | Resolve or reopen the selected thread |
| Enter | Open a file's diff, read a thread, open a check, or open and close a branch |
| Right, Left | Open or close a branch of the outline |
| Tab, Shift+Tab | Into the details and back |

| Key | Control |
| --- | --- |
| `Alt+L` | Changed since my last review |
| `Alt+U` | Next Unresolved |
| `Alt+V` | Next Unvisited |
| `Alt+G` | Open on GitHub |
| `Alt+S` | Copy Review Summary |
| `Alt+T` | Timeline... |
| `Alt+C` | Compose Review... |
| `Alt+R` | Reply to Thread... |

| Key | Control |
| --- | --- |
| `Alt+W` | Request Reviewers... |
| `Alt+M` | Mark Ready, on a draft |
| `Alt+D` | Convert to Draft |
| `Alt+B` | Update Branch... |
| `Alt+A` | Auto-Merge and Queue... |

Check Merge Policy has no access key. Request Copilot Review is on the pull
request's context menu (`Shift+F10` on the outline) and has none either.

### Compose Review

| Key | Control |
| --- | --- |
| `Alt+M` | Review message |
| Escape | Save Draft and Close |

Review action and Submit Review have no access key; reach them with Tab.

## The diff

| Key | What it does |
| --- | --- |
| `Alt+M` | Line marks: words or symbols |
| `Alt+H` | Changed Lines Only |
| `Alt+P` | Patch lines |
| Shift with the arrows | Select a run of patch lines |
| Enter | Comment on the line, or on the selected lines |
| `Alt+L` | Comment on This Line... |
| `Alt+S` | Comment on Lines... |
| `Alt+C` | Copy Diff |
| `Alt+O` | Open Diff in Default App |

### Commenting on a line

| Key | Control |
| --- | --- |
| `Alt+S` | Suggest a change |
| `Alt+C` | Comment |
| `Alt+A` | Add to Review, the default |
| `Alt+P` | Post Now |

## Repository Files

| Key | Control or action |
| --- | --- |
| `Alt+B` | Branch, tag or commit |
| `Alt+G` | Go |
| `Alt+F` | Files, the tree |
| `Alt+C` | Contents |
| `Alt+V` | View File |
| `Alt+E` | Open in Editor |
| `Alt+R` | README |
| `Alt+H` | History... |

| Key | Control or action |
| --- | --- |
| `Alt+L` | Blame... |
| Right, Enter | Open a folder |
| Left | Close a folder |

### History and Blame

| Key | What it does |
| --- | --- |
| `Alt+N`, `Alt+P` | Next or previous row, from anywhere in the window |
| Enter | Open the commit on GitHub |
| `Alt+O` | Open Commit |
| `Alt+D` | Details |
| `Alt+C` | The Commits list, in History |
| `Alt+R` | The Runs list in Blame; Refresh in History |

## Actions windows

### What Failed

| Key | Control |
| --- | --- |
| `Alt+W` | What failed, the text |
| `Alt+C` | Copy All |
| `Alt+R` | Refresh |

### Jobs and Logs

| Key | Control |
| --- | --- |
| `Alt+A` | Attempt |
| `Alt+L` | Load Log |
| `Alt+N` | Load Annotations |
| `Alt+J` | Open Job on GitHub |
| `Alt+R` | Open Run on GitHub |
| `Alt+F` | What Failed... |
| `Alt+C` | Re-request Check |
| `Alt+W` | Follow This Job |
| `Alt+8` | How far along the selected job is |
| Enter | Load the selected job's log |

### Pending Deployments

| Key | Control |
| --- | --- |
| `Alt+E` | Environments waiting for review |
| `Alt+C` | Comment |
| `Alt+A` | Approve |
| `Alt+R` | Reject |

### Artifacts

| Key | Control |
| --- | --- |
| `Alt+S` | Download Selected... |
| `Alt+A` | Download All... |
| `Alt+R` | Refresh |
| `Alt+B` | Open Run in Browser |

## Issue windows

### New Issue

| Key | Control |
| --- | --- |
| `Alt+T` | Title |
| `Alt+B` | Body |
| `Alt+L` | Labels |
| `Alt+A` | Assignees |

### Milestones

| Key | Control |
| --- | --- |
| `Alt+S` | Show |
| `Alt+M` | Milestones, the list |
| `Alt+D` | Details |
| `Alt+N` | New... |
| `Alt+E` | Edit... |
| `Alt+L` | Close Milestone... or Reopen Milestone... |
| `Alt+O` | Open on GitHub |
| `Alt+R` | Refresh |

### Projects and Dependencies

| Key | Control |
| --- | --- |
| `Alt+L` | Load Projects |
| `Alt+P` | Project |
| `Alt+N` | Next Unblocked |
| `Alt+A` | Actions... |

### Smaller windows

| Window | Key | Control |
| --- | --- | --- |
| Timeline | `Alt+H` | History, oldest first |
| Timeline | `Alt+A` | Copy All |
| Reorder Sub-issues | `Alt+U` | Move Up |
| Reorder Sub-issues | `Alt+D` | Move Down |
| Edit Release | `Alt+N` | Release name |
| Edit Release | `Alt+O` | Release notes |
| Edit Release | `Alt+D` | Draft (not published yet) |
| Edit Release | `Alt+P` | Pre-release |
| Commit Comments | `Alt+C` | Comments |
| Commit Comments | `Alt+M` | Selected comment |
| Commit Comments | `Alt+N` | New comment |
| Commit Comments | `Alt+F`, `Alt+L` | File, optional; Line, optional |
| Commit Comments | `Alt+P` | Post Comment |
| Commit Comments | `Alt+R` | Refresh |
| New Gist, Edit Gist | `Alt+D` | Description |
| New Gist | `Alt+B` | Public gist |
| New Gist, Edit Gist | `Alt+F` | Files |
| New Gist, Edit Gist | `Alt+T` | File text |
| New Gist, Edit Gist | `Alt+A` | Add File... |
| New Gist, Edit Gist | `Alt+N` | Rename File... |
| New Gist, Edit Gist | `Alt+L` | Delete File... |

## Discussion windows

| Window | Key | Control |
| --- | --- | --- |
| Discussion thread | `Alt+T` | Thread |
| Discussion thread | `Alt+X` | Text |
| Discussion thread | `Alt+R` | Reply... |
| Discussion thread | `Alt+M` | Mark as Answer... or Unmark Answer... |
| Discussion thread | `Alt+O` | Open on GitHub |
| Discussion thread | `Alt+F` | Refresh |
| New Discussion | `Alt+C` | Category |
| New Discussion | `Alt+T`, `Alt+B` | Title, Body |

## Compare branches

| Key | Control |
| --- | --- |
| `Alt+G` | Open on GitHub |
| `Ctrl+Tab` | Switch between the Commits and Changed Files tabs |

---

- Previous: [Chapter 10: Troubleshooting, privacy and help](github-guide-10-troubleshooting.html)
- [Contents](github-guide.html)
- Next: [Chapter 12: The GitHub Workbench, place by place](github-guide-12-the-workbench.html)
