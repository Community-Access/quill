"""The GitHub Workbench's authored help, as one catalogue (GitHub PRD section 7, Part D).

Every help string the Workbench says is written once, here, and read
everywhere it appears (D19): F1, Shift+F1, Explain That, Search Help, the
Words node, the generated reference. wx-free and strict-typed.
"""

from __future__ import annotations

__all__ = ["CHOICE_WORDS", "PREF_HELP", "PREF_PAGES", "RESULT_EXPLANATIONS", "explain_result"]

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
        "Play a &tick on each check",
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
    "use_classic_windows": (
        "Privacy",
        "Use the &classic GitHub windows",
        "Open GitHub Items and Explore GitHub, as before the Workbench, from the "
        "editor's GitHub doors. Kept for one release, then retired.",
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


def explain_result(text: str) -> str:
    """What the result *text* means and what you might do next (Shift+F9)."""
    said = (text or "").strip()
    for start, explanation in RESULT_EXPLANATIONS:
        if said.startswith(start):
            return explanation
    if not said:
        return ""
    return (
        f"The Workbench last said: {said} Shift+F1 lists what you can do with the "
        "selection, and F1 says what this view is for."
    )
