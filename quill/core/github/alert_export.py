"""What Export List may write from a security alert list, and nothing more (GX11).

The Workbench's alert lists (a repository's open and closed alerts, the
organization's Dependabot, code scanning and secret scanning alerts, and
Across Repositories > Security Alerts) never ask GitHub for a secret's value
(``hide_secret=true``) and never put one in a row: a row is built from the
alert's kind, severity, package or rule, state and dates only. Export List
writes the cells the list shows, so the file holds what the row holds.

That is two promises kept by construction. This module adds the third, for
text GitHub itself wrote into an alert: a code scanning message can quote the
hard-coded string it found, and a summary can carry a token someone pasted.
Before a cell of an alert list reaches the file, it passes the same redaction
Change History uses (secrets QUILL holds, then token shapes: ``ghp_``,
``github_pat_``, ``sk-``, AWS keys, JWTs, long hex), and a URL's
``user:password@`` is dropped. A redacted cell says ``[TOKEN]`` where the
value was, so the reader knows something was left out.

wx-free and strict-typed.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence

__all__ = ["ALERT_LISTS", "is_alert_list", "safe_cell", "safe_rows"]

#: The Workbench loaders whose rows are security alerts.
ALERT_LISTS: frozenset[str] = frozenset({
    "explore:security",
    "explore:security_closed",
    "explore:res_org_dependabot_alerts",
    "explore:res_org_secret_alerts",
    "explore:res_org_code_scanning_alerts",
    "across:alerts",
})


def is_alert_list(loader: str) -> bool:
    """Whether *loader*'s rows are security alerts."""
    return loader in ALERT_LISTS


def safe_cell(text: object) -> str:
    """*text* with every secret QUILL holds and every token shape replaced."""
    from quill.stability.redaction import redact_known_secrets, redact_source_tokens

    return redact_source_tokens(redact_known_secrets(str(text)))


def safe_rows(loader: str, rows: Iterable[Sequence[object]]) -> list[list[str]]:
    """The cells Export List writes: an alert list's redacted, any other list's as shown."""
    if not is_alert_list(loader):
        return [[str(cell) for cell in row] for row in rows]
    return [[safe_cell(cell) for cell in row] for row in rows]
