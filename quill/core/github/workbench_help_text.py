"""The GitHub Workbench's help words for windows, nodes, options and results.

Pure data behind :mod:`quill.core.github.workbench_help` (split out for
GATE-11). Plain, short, what to do before why (Part D9); check, never tick.
"""

from __future__ import annotations

from quill.core.github.workbench_node_help import NODE_HELP

__all__ = [
    "CHOICE_WORDS",
    "NODE_HELP",
    "PREF_HELP",
    "PREF_PAGES",
    "RESULT_EXPLANATIONS",
    "SURFACE_PURPOSES",
]

#: Workbench Options' pages, in order (GitHub PRD 4.1).
PREF_PAGES: tuple[str, ...] = (
    "General",
    "Notifications and Inbox",
    "Lists",
    "Repositories",
    "Privacy",
)

#: Each preference: (its page, its label with an access key, what F1 says).
#: The generated reference prints them all, which is what GATE-SETDOC reads.
PREF_HELP: dict[str, tuple[str, str, str]] = {
    "open_on": (
        "General",
        "&Open the Workbench on:",
        "Where the window opens when no menu row asks for a place: Inbox (Start Here "
        "until you have signed in), Start Here, or wherever you were last time.",
    ),
    "list_mode": (
        "General",
        "&List shows:",
        "Quick lists show a few columns, fast to arrow through; Full lists show every "
        "column GitHub Items knows for that view.",
    ),
    "default_sort": (
        "General",
        "&Sort issues and pull requests by:",
        "The order a list of issues and pull requests opens in. Newest first is the usual choice.",
    ),
    "default_state": (
        "General",
        "Show issues that &are:",
        "Open, closed or all, when a list opens. The filter box can always say "
        "is:open or is:closed for one list.",
    ),
    "poll_interval_minutes": (
        "Notifications and Inbox",
        "Check for new notifications every (&minutes):",
        "How often GitHub is checked for new notifications, from 5 minutes to a day. "
        "GitHub may ask for longer, and then it gets longer.",
    ),
    "poll_audible_tick": (
        "Notifications and Inbox",
        "Play a soun&d on each check",
        "A short sound every time GitHub is checked, so silence means the check "
        "stopped rather than found nothing. Off by default.",
    ),
    "poll_interrupt_speech": (
        "Notifications and Inbox",
        "New notifications &interrupt speech",
        "Say a new notification at once, cutting across what is being said. Off "
        "means it waits its turn.",
    ),
    "include_read_notifications": (
        "Notifications and Inbox",
        "Include &read notifications",
        "Show notifications you have already read, as well as unread ones, in Notifications.",
    ),
    "speak_column_names": (
        "Lists",
        "Say column &names before values",
        "Put each column's name before its value in a list row, as in Number 42, "
        "Title Crash on start. Off keeps rows short.",
    ),
    "health_snapshot_opt_in": (
        "Privacy",
        "Load the repository &Health Snapshot",
        "Insights, Health Snapshot reads extra data from GitHub about a repository's "
        "activity. It loads only when this is checked.",
    ),
    "first_time_help": (
        "Privacy",
        "Show &First time here? help",
        "The first few times you visit a place, its details start with a short "
        "paragraph on what it is for.",
    ),
}

#: How each choice value reads in the dialog.
CHOICE_WORDS: dict[str, str] = {
    "inbox": "Inbox",
    "start": "Start Here",
    "last": "Where I was last time",
    "quick": "Quick (a few columns)",
    "full": "Full (every column)",
    "number_desc": "Number, newest first",
    "number_asc": "Number, oldest first",
    "title_asc": "Title, A to Z",
    "title_desc": "Title, Z to A",
    "updated_desc": "Last updated, newest first",
    "updated_asc": "Last updated, oldest first",
    "comments_desc": "Most comments first",
    "open": "Open",
    "closed": "Closed",
    "all": "All",
}

#: Explain That (Shift+F9, D13): the start of a result -> what it means and what next.
RESULT_EXPLANATIONS: tuple[tuple[str, str], ...] = (
    (
        "Comment posted",
        "Your comment is on GitHub now, and everyone watching the item is told. Enter "
        "on the item reads it with its comments; F5 loads the list again.",
    ),
    (
        "Created issue",
        "The issue is on GitHub now, open, with you as its author. It is at the top of "
        "Issues after F5; Alt+Enter on it shows everything about it.",
    ),
    (
        "Closed",
        "The item is closed on GitHub. Nothing was deleted: the same command reopens it, "
        "and its comments and history stay.",
    ),
    (
        "Reopened",
        "The item is open again on GitHub, as it was before it was closed.",
    ),
    (
        "Re-running",
        "GitHub is running the workflow again from the start, on the same commit. Its "
        "new run appears in Actions Runs; F5 refreshes the list.",
    ),
    (
        "Marked read",
        "GitHub now shows the notification as read. It stays in Notifications until it "
        "is marked done; Delete marks it done.",
    ),
    (
        "Marked done",
        "The notification left your inbox on GitHub. A new comment on the same thread "
        "brings it back.",
    ),
    (
        "Unsubscribed",
        "GitHub stops telling you about that thread, unless somebody mentions you in it.",
    ),
    (
        "Starred",
        "The repository is in your stars on GitHub, under Repositories, Starred.",
    ),
    (
        "Unstarred",
        "The repository left your stars. Nothing else about it changed.",
    ),
    (
        "Added to Favorites",
        "It is kept on this computer under Repositories, Favorites. GitHub is not told.",
    ),
    (
        "Removed from Favorites",
        "It is no longer under Repositories, Favorites. GitHub was never told either way.",
    ),
    (
        "Pinned",
        "The repository is kept on this computer under Repositories, Pinned.",
    ),
    (
        "Unpinned",
        "The repository is no longer under Repositories, Pinned.",
    ),
    (
        "Saved the search",
        "The search is kept on this computer under Search, Saved Searches (Ctrl+8). "
        "Enter on it runs it again.",
    ),
    (
        "Copied",
        "It is on the clipboard. Paste it anywhere with Ctrl+V.",
    ),
    (
        "Could not",
        "GitHub refused, or could not be reached. The words after Could not say why. F5 "
        "tries the view again, and Account, GitHub API Rate Limit (Ctrl+Shift+L) says "
        "whether you have used up your requests for now.",
    ),
    (
        "Sign in",
        "This needs a GitHub account. Account, Manage GitHub Accounts (Ctrl+Shift+K) "
        "adds one; reading public repositories works without one.",
    ),
)

#: Window title (or its start) -> what the window is for, said first by F1.
SURFACE_PURPOSES: dict[str, str] = {
    "Filter Builder": (
        "Build a filter one condition at a time: an attribute, an operator and a value "
        "from the repository. The query appears as you go, in GitHub's own syntax; OK "
        "puts it in the filter box, Save as Search also keeps it."
    ),
    "GitHub Permissions": (
        "Every permission the Workbench can use, what it unlocks and whether you have "
        "it. Add Permissions asks for every missing one in one sign-in; Copy Command, "
        "the classic token page and the fine-grained steps are the other ways."
    ),
    "Change History": (
        "Every change the Workbench made on GitHub, newest first: what, when, before and "
        "after, and whether GitHub confirmed it. Undo This Change reverses one where "
        "GitHub allows it. Kept on this device for 90 days; secret values never appear."
    ),
    "Preview": (
        "What is about to change on GitHub, in words. Enter goes ahead; Escape changes nothing."
    ),
    "Changed on GitHub": (
        "Somebody changed this field on GitHub since you opened the sheet. Keep Theirs "
        "leaves their value; Use Mine saves yours over it."
    ),
    "Type to Confirm": (
        "This change is hard to reverse, so it waits for the name typed exactly. "
        "Anything else changes nothing."
    ),
    "Columns": "Choose which columns this list shows. Space checks or clears one.",
    "GitHub API Console": (
        "Send any GitHub REST request or GraphQL query. Down Arrow in Path lists the "
        "operations that match; What it does says the risk and what it needs before you "
        "send. A read goes at once; a write needs Full access and the method typed to "
        "confirm. The answer is a tree: Copy Value, Copy Path and Export JSON work on it."
    ),
    "Confirm GitHub API Write": (
        "This request changes something on GitHub. Type the method shown, or MUTATION "
        "for GraphQL, to send it; anything else sends nothing."
    ),
    "Save Command": "A name for this console request, kept for this account on this device.",
    "Saved Commands": "Console requests you saved. Enter fills the console with one.",
    "Export JSON": "Where to save GitHub's answer as a JSON file.",
    "Add Watch": (
        "What to watch for: a run finishing, a review, a release or a comment. Then "
        "you name the repository, or the issue or pull request."
    ),
    "Watch": (
        "The repository as owner/name, or the issue or pull request as owner/name#42. "
        "For runs, a branch after a space watches only that branch."
    ),
    "Read as Document": (
        "The whole thread as one document, a heading per post with its author and "
        "date: open it in the editor, or save it as Markdown or HTML."
    ),
    "Save Thread As": "Where to save the thread document.",
    "Properties of": (
        "One sheet for several objects. A field the same on all shows its value; one "
        "that differs says Mixed and is left alone unless you change it; a check box on "
        "some of them is in its third state."
    ),
    "GitHub Workbench": (
        "One window for GitHub. The tree on the left says where you are, the list "
        "says what is there, and the details say what the selected one is. F6 moves "
        "between them, Enter does the obvious thing, Shift+F1 lists everything you "
        "can do, and Alt+Enter shows everything about the selection."
    ),
    "Workbench Options": (
        "The GitHub Workbench's own preferences: where it opens, how lists start, "
        "how often notifications are checked, your pinned repositories and "
        "favorites, and privacy. OK saves, Cancel changes nothing."
    ),
    "What Can I Do Here": (
        "Every action for what is selected, in the order of its context menu, with "
        "its key. Enter runs the action; a greyed one says why it is greyed."
    ),
    "Search Help": (
        "Type a few words to find a help topic, a place, a command or a GitHub "
        "word. Enter goes there, runs it or reads it."
    ),
    "What Is This": "A GitHub word, explained in plain language, with where you meet it.",
    "GitHub Workbench Keys": "Every key in the GitHub Workbench, grouped by what it does.",
    "Artifacts": "The files a workflow run kept: download one or all of them.",
    "Discussion #": "One discussion thread: read it, and reply if you are signed in.",
    "New Discussion": "Start a discussion in the repository: a category, a title and what to say.",
    "Pending Deployments": "Deployments waiting on you: approve or reject each one.",
    "What Failed": "The failing steps of a run and their log lines, in one place.",
    "Jobs for": "A run's jobs and steps, with each job's log and annotations.",
    "Clone Repository": (
        "Copy a GitHub repository to a folder on this computer: which repository, "
        "which folder, then OK. The copy runs in the background and you hear once "
        "how it went."
    ),
    "GitHub Access": (
        "Asked once, before anything talks to GitHub: what connecting does and how "
        "to take it back. Continue allows it; Cancel leaves GitHub alone."
    ),
    "Manage GitHub Accounts": (
        "The GitHub accounts kept on this computer: switch to one, add another, or "
        "remove one and forget its token."
    ),
    "Add GitHub Token": (
        "Paste a personal access token you made yourself, such as one limited to a "
        "few repositories, or go on without signing in. Sign In with GitHub is the "
        "easier road for most people."
    ),
    "New Issue from a Form": (
        "Fill in a repository's issue form, one field at a time, with the required "
        "ones marked. Nothing reaches GitHub until you press Create Issue."
    ),
    "New Discussion from a Form": (
        "Fill in a discussion category's form, one field at a time, with the required "
        "ones marked. Nothing reaches GitHub until you press Start Discussion."
    ),
    "Preview Form": (
        "A template's form as people will meet it. Show Body shows what GitHub would "
        "write; nothing is sent anywhere."
    ),
    "Template:": (
        "Build or edit a template: its keys, its fields as a list, its source and a "
        "preview, with the problems GitHub would report listed before Save."
    ),
    "Template Chooser": (
        "Whether blank issues are allowed, the contact links, and the order the "
        "templates appear in. Nothing reaches GitHub until you save and confirm."
    ),
    "Sponsor Platforms (FUNDING.yml)": (
        "Where people can sponsor the project: one box per platform GitHub knows."
    ),
    "How to Cite (CITATION.cff)": (
        "How people should cite the project: title, version, DOI and the authors."
    ),
    "Code Owners (CODEOWNERS)": (
        "Who reviews changes to which paths, and a lookup for who owns a path."
    ),
    "Form Field:": (
        "One field of a form: its label, id, description and, for its kind, "
        "placeholder, options, default and whether it is required."
    ),
    "New Pull Request": (
        "Propose merging one branch into another: the two branches, a title, a "
        "description and whether it is a draft. Nothing reaches GitHub until you "
        "press Create Pull Request."
    ),
    "New Issue": (
        "Write an issue before it goes anywhere: title, what to say, labels and who "
        "it is for. Nothing reaches GitHub until you press Create Issue."
    ),
    "Milestones": (
        "A repository's milestones, one line each with how far along it is and when "
        "it is due. New, Edit, and Close or Reopen change them on GitHub."
    ),
    "Review pull request": (
        "Read a pull request the way a reviewer does: its outline and threads, the "
        "review summary and the checks, with buttons to jump to the next unresolved "
        "thread, reply, request reviewers or write your review."
    ),
    "GitHub Projects and Dependencies": (
        "Load a repository's Projects, pick one, and walk its items as a list. The "
        "details say what each item is blocked by and what it blocks; Next Unblocked "
        "finds something you can start."
    ),
    "Edit Release": (
        "Change a release's name, notes, and whether it is a draft or a prerelease. "
        "Nothing is sent until Save; publishing a draft asks first, because watchers "
        "are told."
    ),
    "Draft Release Notes": (
        "Write release notes from the changes between two points, then edit and copy "
        "them. This only drafts: no release is made on GitHub."
    ),
    "Configure Branch Protection": (
        "Pick a branch, then protect it with the rules you choose, or clear the "
        "protection it already has."
    ),
    "Create GitHub Repository": (
        "Make a new repository on GitHub: its name, a description, public or "
        "private, and optionally the organization it belongs to."
    ),
    "Repository Files": (
        "Walk a repository's folders and files at any branch, tag or commit. Enter "
        "reads a file here; Open in Editor, README, History and Blame go further."
    ),
    "GitHub Repository Browser": (
        "Choose a repository, a branch or tag, and a file in it to open in the editor."
    ),
    "Review Pull Request": (
        "Write your review of a pull request: approve, ask for changes or just "
        "comment, with a message. The draft is kept on this computer until you press "
        "Submit Review."
    ),
    "Reorder Sub-issues": (
        "A parent issue's sub-issues in the order GitHub holds. Move Up and Move "
        "Down change that order on GitHub, and you hear where it landed."
    ),
    "Repositories in": (
        "Choose the repositories in this Repository Set: one check box per repository, "
        "by owner and name. Space checks or unchecks one; Add puts in one you type; "
        "Enter saves."
    ),
}
