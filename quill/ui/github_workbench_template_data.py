"""The GitHub Workbench Templates commands' starters and context reads.

Split from :mod:`quill.ui.github_workbench_templates` (GATE-11), which
re-exports ``COMMUNITY_STARTERS``: the first text of a missing community file,
New Template's kinds and starters, the community files with a sheet of their
own, and what a template window needs beside the file. wx-free.
"""

from __future__ import annotations

from typing import Any

__all__ = ["COMMUNITY_STARTERS"]

#: A missing community file's first text, by file name.
COMMUNITY_STARTERS: dict[str, str] = {
    "CODE_OF_CONDUCT.md": (
        "# Code of Conduct\n\nWe want everyone to feel welcome here. Be kind, be patient, "
        "and assume good intent.\n\n## Reporting\n\nTell the maintainers at: (address)\n"
    ),
    "CONTRIBUTING.md": (
        "# Contributing\n\nThank you for helping.\n\n## Reporting a problem\n\n"
        "Open an issue and choose the template that fits.\n\n## Changing the code\n\n"
        "Fork the repository, make your change on a branch, and open a pull request.\n"
    ),
    "SECURITY.md": (
        "# Security Policy\n\nPlease do not report security problems in public issues. "
        "Use GitHub's private vulnerability reporting on the Security tab instead.\n"
    ),
    "SUPPORT.md": "# Getting Help\n\nAsk in Discussions, or open an issue.\n",
    "GOVERNANCE.md": "# Governance\n\nWho decides what, and how.\n",
    "FUNDING.yml": "# Sponsor platforms and names, one per line.\ngithub: []\n",
    "CITATION.cff": (
        "cff-version: 1.2.0\nmessage: If you use this, please cite it.\ntitle: \nauthors:\n"
        "  - name: \n"
    ),
    "CODEOWNERS": "# Path patterns and their owners, one per line.\n# * @owner\n",
}

#: New Template's kinds: (label, kind, folder).
_NEW_KINDS: tuple[tuple[str, str, str], ...] = (
    ("Issue form", "issue_form", ".github/ISSUE_TEMPLATE"),
    ("Discussion category form", "discussion_form", ".github/DISCUSSION_TEMPLATE"),
    ("Pull request template", "pull_request_template", ".github"),
    ("Template chooser (config.yml)", "chooser", ".github/ISSUE_TEMPLATE"),
)
_PR_TEMPLATE = "## What this changes\n\n\n## Why\n\n\n## How it was checked\n\n- [ ] Tests pass\n"
_CHOOSER = "blank_issues_enabled: true\ncontact_links: []\n"


#: Community files with a sheet of their own -> the sheet's class.
_SHEETS = {
    "FUNDING.yml": "FundingDialog",
    "CITATION.cff": "CitationDialog",
    "CODEOWNERS": "CodeownersDialog",
}


def _context(repo: Any, kind: str, path: str) -> dict[str, Any]:
    """What a window needs beside the file: labels and assignees for a form, the
    template file names for the chooser. A read that fails leaves its key out."""
    from itertools import islice

    found: dict[str, Any] = {}
    if kind in ("issue_form", "discussion_form", "issue_template"):
        try:
            found["labels"] = [str(x.name) for x in islice(repo.get_labels(), 200)]
        except Exception:  # noqa: BLE001 - the picker is a convenience, not a gate
            pass
        try:
            found["assignees"] = [str(x.login) for x in islice(repo.get_assignees(), 200)]
        except Exception:  # noqa: BLE001
            pass
    if kind == "chooser":
        folder = path.rsplit("/", 1)[0]
        try:
            found["filenames"] = sorted(
                str(entry.name)
                for entry in repo.get_contents(folder)
                if str(getattr(entry, "type", "")) == "file"
                and not str(entry.name).casefold().startswith("config.")
            )
        except Exception:  # noqa: BLE001
            found["filenames"] = []
    return found
