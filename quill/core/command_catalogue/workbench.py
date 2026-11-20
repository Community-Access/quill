"""The GitHub and WordPress Workbench windows' catalogue rows (command-key.md 13.12).

Each Workbench is its own window, with its own menu bar and keys, so each is
its own app here: ``github_workbench`` and ``wordpress_workbench``. The rows
are the commands a sentence may reach in that window: going to a place,
asking what is here, opening a window (the API or REST Console, Permissions,
the tutorials), New Here and the Plain-Language Batch, whose own preview asks before
anything is sent. A command that changes GitHub or a site by itself is not
here, so no sentence can reach it; it stays on its menu and its key.

The ids are the windows' own menu ids, so the Workbench's dispatcher runs
them, through its write gate, exactly as the menu would. A row whose command
the window does not have is simply not offered there; a test holds every row
to its window's bar.

Both editors open the same Workbench windows, so QUILL and QUILL Lite reach
these rows together; neither can be ahead of the other.
"""

from __future__ import annotations

from quill.core.command_catalogue.spec import CommandSpec, Kind, Risk

__all__ = ["GITHUB_WORKBENCH_APP", "WORDPRESS_WORKBENCH_APP", "WORKBENCH_ROWS"]

GITHUB_WORKBENCH_APP = "github_workbench"
WORDPRESS_WORKBENCH_APP = "wordpress_workbench"
_G = "github.workbench."
_W = "wordpress.workbench."


def _gh(
    verb: str,
    title: str,
    description: str,
    examples: tuple[str, ...],
    *,
    group: str,
    aliases: tuple[str, ...] = (),
    kind: Kind = Kind.ACTION,
    speaks: bool = True,
) -> CommandSpec:
    return CommandSpec(
        id=_G + verb,
        title=title,
        description=description,
        aliases=aliases,
        examples=examples,
        risk=Risk.SAFE,
        kind=kind,
        group=group,
        announces_itself=speaks,
        apps=(GITHUB_WORKBENCH_APP,),
    )


def _wp(
    verb: str,
    title: str,
    description: str,
    examples: tuple[str, ...],
    *,
    group: str,
    aliases: tuple[str, ...] = (),
    kind: Kind = Kind.ACTION,
    speaks: bool = True,
) -> CommandSpec:
    return CommandSpec(
        id=_W + verb,
        title=title,
        description=description,
        aliases=aliases,
        examples=examples,
        risk=Risk.SAFE,
        kind=kind,
        group=group,
        announces_itself=speaks,
        apps=(WORDPRESS_WORKBENCH_APP,),
    )


#: Every row says its own outcome: a Go row moves focus, which the screen reader
#: says (GATE-13), a readout speaks, a dialog opens, and Refresh and Dry Run say
#: what happened. So the Command Key adds nothing after any of them.
_D = Kind.OPENS_DIALOG
_R = Kind.READOUT

GITHUB_WORKBENCH_ROWS: tuple[CommandSpec, ...] = (
    _gh(
        "go_inbox",
        "Inbox",
        "See everything waiting on me across GitHub",
        ("show my inbox", "what needs my attention", "what is waiting for me"),
        group="Go",
        aliases=("needs my attention", "my inbox"),
    ),
    _gh(
        "go_repository",
        "Current Repository",
        "Go to the repository I am working in",
        ("go to the repository", "back to this repository", "show the repository"),
        group="Go",
    ),
    _gh(
        "go_issues",
        "Issues",
        "List this repository's issues",
        ("show the issues", "list the open issues", "go to issues"),
        group="Go",
    ),
    _gh(
        "go_pulls",
        "Pull Requests",
        "List this repository's pull requests",
        ("show the pull requests", "list pull requests", "go to pull requests"),
        group="Go",
        aliases=("prs",),
    ),
    _gh(
        "go_runs",
        "Actions Runs",
        "List this repository's workflow runs",
        ("show the workflow runs", "list the actions runs", "go to runs"),
        group="Go",
        aliases=("workflow runs", "builds"),
    ),
    _gh(
        "go_projects",
        "Projects",
        "List my project boards",
        ("show my projects", "go to projects", "list my project boards"),
        group="Go",
    ),
    _gh(
        "go_search",
        "Search",
        "Search all of GitHub",
        ("search github", "go to search", "look for something on github"),
        group="Go",
    ),
    _gh(
        "refresh",
        "Refresh",
        "Get the latest from GitHub for this list",
        ("refresh", "reload this list", "get the latest"),
        group="View",
    ),
    _gh(
        "where_am_i",
        "Where Am I",
        "Hear where I am in the Workbench",
        ("where am i", "say where i am", "what place is this"),
        group="View",
        kind=_R,
    ),
    _gh(
        "say_counts",
        "Say Counts",
        "Hear how many rows this list has",
        ("how many are there", "say the counts", "count the rows"),
        group="View",
        kind=_R,
    ),
    _gh(
        "rate_limit",
        "GitHub API Rate Limit",
        "Hear how many GitHub requests I have left",
        ("how much rate limit is left", "say the rate limit", "am i near the api limit"),
        group="Account",
        kind=_R,
    ),
    _gh(
        "what_failed",
        "What Failed",
        "Read why the selected run failed",
        ("what failed", "why did the run fail", "show me the failure"),
        group="Item",
        kind=_D,
    ),
    _gh(
        "new_here",
        "New Here",
        "Make something new where I am, such as an issue in Issues; nothing is sent until "
        "I press OK",
        ("new issue", "file a bug", "make something new here"),
        group="File",
        kind=_D,
    ),
    _gh(
        "plain_batch",
        "Plain-Language Batch",
        "Change many issues or pull requests by saying it in words, checked before it is sent",
        (
            "plain language batch",
            "change many issues in words",
            "do a batch change by sentence",
        ),
        group="Tools",
        aliases=("batch in words",),
        kind=_D,
    ),
    _gh(
        "dry_run",
        "Dry Run",
        "Practise a change without sending it to GitHub",
        ("turn dry run on or off", "practice without sending", "toggle dry run"),
        group="Tools",
        kind=Kind.TOGGLE,
    ),
    _gh(
        "api_console",
        "GitHub API Console",
        "Ask GitHub anything it has an API for",
        ("open the api console", "make an api request", "github api console"),
        group="Tools",
        kind=_D,
    ),
    _gh(
        "permissions",
        "GitHub Permissions",
        "See what my GitHub sign-in may do",
        ("what permissions do i have", "show my token scopes", "github permissions"),
        group="Account",
        kind=_D,
    ),
    _gh(
        "change_history",
        "Change History",
        "See every change I made from the Workbench",
        ("show change history", "what did i change", "list my changes"),
        group="Account",
        kind=_D,
    ),
    _gh(
        "help_tutorials",
        "Tutorials",
        "Learn GitHub with a short lesson",
        ("open the tutorials", "show me the lessons", "teach me github"),
        group="Help",
    ),
    _gh(
        "switch_to_editor",
        "Switch to Editor",
        "Go back to my document",
        ("back to the editor", "switch to my document", "go to the editor"),
        group="Window",
    ),
)

WORDPRESS_WORKBENCH_ROWS: tuple[CommandSpec, ...] = (
    _wp(
        "go_inbox",
        "Needs My Attention",
        "See what waits on every connected site",
        ("what needs my attention", "show what is waiting", "go to needs my attention"),
        group="Go",
        aliases=("my inbox",),
    ),
    _wp(
        "go_site",
        "Current Site",
        "Go to the site I am working on",
        ("go to the site", "back to this site", "show the site"),
        group="Go",
    ),
    _wp(
        "go_posts",
        "Posts",
        "List this site's posts",
        ("show the posts", "list posts", "go to posts"),
        group="Go",
    ),
    _wp(
        "go_pages",
        "Pages",
        "List this site's pages",
        ("show the pages", "list pages", "go to pages"),
        group="Go",
    ),
    _wp(
        "go_comments",
        "Comments",
        "List this site's comments",
        ("show the comments", "list comments", "go to comments"),
        group="Go",
    ),
    _wp(
        "go_media",
        "Media",
        "List this site's pictures and files",
        ("show the media", "list the pictures", "go to media"),
        group="Go",
    ),
    _wp(
        "go_health",
        "Site Health",
        "See what is wrong with this site",
        ("show site health", "is the site healthy", "go to site health"),
        group="Go",
    ),
    _wp(
        "refresh",
        "Refresh",
        "Get the latest from the site for this list",
        ("refresh", "reload this list", "get the latest"),
        group="View",
    ),
    _wp(
        "where_am_i",
        "Where Am I",
        "Hear where I am in the Workbench",
        ("where am i", "say where i am", "what place is this"),
        group="View",
        kind=_R,
    ),
    _wp(
        "plain_batch",
        "Plain-Language Batch",
        "Change many posts or comments by saying it in words, checked before it is sent",
        (
            "plain language batch",
            "change many posts in words",
            "do a batch change by sentence",
        ),
        group="Tools",
        aliases=("batch in words",),
        kind=_D,
    ),
    _wp(
        "rest_console",
        "REST Console",
        "Ask the site anything its REST API answers",
        ("open the rest console", "make a rest request", "wordpress rest console"),
        group="Tools",
        kind=_D,
    ),
    _wp(
        "history",
        "Change History",
        "See every change I made from the Workbench",
        ("show change history", "what did i change", "list my changes"),
        group="Edit",
        kind=_D,
    ),
    _wp(
        "switch_to_editor",
        "Switch to Editor",
        "Go back to my document",
        ("back to the editor", "switch to my document", "go to the editor"),
        group="Window",
    ),
)

WORKBENCH_ROWS: tuple[CommandSpec, ...] = GITHUB_WORKBENCH_ROWS + WORDPRESS_WORKBENCH_ROWS
