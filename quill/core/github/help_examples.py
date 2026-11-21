"""Help that uses what is in front of you (GitHub PRD D14, GH-R-109).

F1 in the Workbench ends with one example drawn from the person's own data:
the repository they are on, the row they have selected, the account they
are signed in as. "On Community-Access/quill, #42 Crash on start is
selected: Alt+Enter opens everything about it." rather than a made-up
owner/name.

Only what the window has already loaded is used: nothing is read from
GitHub for an example, and nothing is sent anywhere. When the window knows
too little for an example (signed out, nothing selected, no repository),
there is none, rather than a generic one in its place: the rest of help
already has those. wx-free and strict-typed.
"""

from __future__ import annotations

from dataclasses import dataclass

__all__ = ["NODE_EXAMPLES", "ROW_EXAMPLES", "Situation", "example_for"]


@dataclass(frozen=True, slots=True)
class Situation:
    """What the window knows about where the person is."""

    repository: str = ""
    login: str = ""
    #: The selected row's type ("issue", "pull_request", "branch", ...).
    row_kind: str = ""
    #: The selected row as it is named in the list ("#42 Crash on start", "main").
    row: str = ""


#: An example per row type; {repository} and {row} are the person's own.
ROW_EXAMPLES: dict[str, str] = {
    "issue": (
        "On {repository}, {row} is selected: Alt+Enter opens everything about it, "
        "and Labels... on its context menu adds or removes labels in one step."
    ),
    "pull_request": (
        "On {repository}, {row} is selected: Alt+Enter opens its sheet, where the "
        "checks and reviews say whether it can merge."
    ),
    "branch": (
        "On {repository}, Alt+Enter on the branch {row} shows how far it is from the "
        "default branch and whether a rule protects it."
    ),
    "commit": (
        "On {repository}, Alt+Enter on commit {row} shows who made it, the files it "
        "changed and the checks that ran on it."
    ),
    "run": (
        "On {repository}, if the run {row} failed, Re-run Failed Jobs runs only the "
        "jobs that failed, on the same commit."
    ),
    "release": (
        "On {repository}, Alt+Enter on the release {row} shows its notes and files, "
        "and who can download them."
    ),
    "label": (
        "On {repository}, Alt+Enter on the label {row} changes its name, colour and "
        "description everywhere it is used."
    ),
    "workflow": (
        "On {repository}, the workflow {row} can be run by hand with Dispatch "
        "Workflow..., when it allows that."
    ),
}

#: An example when no row is selected, by what the window knows.
NODE_EXAMPLES: dict[str, str] = {
    "repository": (
        "You are on {repository}: Alt+Enter in the tree opens its settings, and "
        "Ctrl+L goes to another repository by name."
    ),
    "login": "You are signed in as {login}: Me in a filter means {login}.",
}


def example_for(situation: Situation) -> str:
    """One example sentence from *situation*, or ``""`` when it knows too little."""
    template = ROW_EXAMPLES.get(situation.row_kind, "")
    if template and situation.row and situation.repository:
        return "For example, here: " + template.format(
            repository=situation.repository, row=situation.row
        )
    if situation.repository:
        return "For example, here: " + NODE_EXAMPLES["repository"].format(
            repository=situation.repository
        )
    if situation.login:
        return "For example, here: " + NODE_EXAMPLES["login"].format(login=situation.login)
    return ""
