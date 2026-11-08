# Chapter 11: Keyboard reference

## What this chapter covers

Every key the workbench answers to, one window at a time. Keys marked as
access keys are the underlined letters of a control, pressed with Alt; they
work while that window has focus. Keys that open the windows themselves are in
Chapter 1. QUILL's GitHub menu commands have no keys out of the box, and you
can give them some in the Keymap Editor.

Throughout, Shift+F10 or the Applications key opens the context menu of
whatever has focus, and Escape closes the window you are in.

## GitHub Items

### Anywhere in the window

| Key | What it does |
| --- | --- |
| `Ctrl+R` | Reload the current view |
| `Ctrl+O` | Open the selected row on GitHub, in your browser |
| `Ctrl+G` | Go to an issue or pull request by number |
| `Ctrl+D` | Add the selected row to your favorites |
| `Ctrl+F` | Move to the Search box |
| `Ctrl+Shift+F` | Move to the Quick filter |
| `Alt+N`, `Alt+P` | Next or previous comment in Details |
| `Ctrl+Shift+B` | Compare two branches, in Branches |
| `Ctrl+Shift+W` | What Failed, in Workflow Runs |
| `Ctrl+Shift+L` | GitHub's remaining allowance |

Escape in the Quick filter clears it, when it has text. Otherwise Escape
closes GitHub Items.

### In the list

| Key | What it does |
| --- | --- |
| Enter | Go in: a branch's commits, a release's files, run a workflow; otherwise open on GitHub |
| Backspace | Come back out to Branches or Releases |
| `M` | Switch between Quick and Full rows |
| `R` | Reload, the same as `Ctrl+R` |

### Access keys

| Key | Control |
| --- | --- |
| `Alt+V` | Favorites... |
| `Alt+E` | Explore... |
| `Alt+J` | Projects... |
| `Alt+U` | View Upstream |
| `Alt+F` | Files... |
| `Alt+H` | Search (GitHub syntax) |
| `Alt+Q` | Quick filter |
| `Alt+I` | View |

| Key | Control |
| --- | --- |
| `Alt+S` | Show |
| `Alt+T` | State |
| `Alt+O` | Sort |
| `Alt+L` | List mode |
| `Alt+M` | Columns... |
| `Alt+D` | Diff... |
| `Alt+R` | Review... |
| `Alt+Z` | Summarize |

| Key | Control |
| --- | --- |
| `Alt+C` | Compare... |
| `Alt+B` | Batch... |
| `Alt+A` | Actions... |

Pinned..., Milestones..., Open Link..., Refresh, View More, Open in Browser and
Go To #... have no access key; reach them with Tab.

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

## Explore GitHub

| Key | Control or action |
| --- | --- |
| `Alt+V` | View |
| `Alt+R` | Repository |
| `Alt+P` | Person |
| `Alt+G` | Global search |
| `Alt+S` | Saved Searches... |
| `Alt+L` | Load |
| `Alt+O` | Queue Options... |
| `Ctrl+Shift+L` | GitHub's remaining allowance |

Enter on a result opens it in the best place for it. Save Search, Open on
GitHub and Use Repository have no access key.

### In the notifications view

| Key | Control or action |
| --- | --- |
| `Alt+I` | Include read notifications |
| `Alt+D` | Mark Done |
| Delete | Mark Done, in the list |
| `Alt+U` | Unsubscribe |
| `Alt+A` | Mark All Read |
| Enter | Mark read and open |

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
