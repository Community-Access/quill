"""Project contributors shown on the About screen.

The list is sourced from the GitHub contributors API for
``Community-Access/quill`` (the same data the contrib.rocks contributor
graphic is built from). We bake it in rather than fetching at runtime so the
About screen renders instantly, works offline, and stays fully accessible: a
plain bullet list of names a screen reader announces cleanly, never an avatar
image. Automated bot accounts (Dependabot, Claude, Copilot) are excluded;
human contributors are listed most-contributions-first.

Refresh the baked list when contributors change by running::

    python -m quill.core.contributors

which prints an updated ``CONTRIBUTORS`` tuple to paste back here (requires the
``gh`` CLI to be authenticated, or set ``GITHUB_TOKEN``).
"""

from __future__ import annotations

# (display name, GitHub profile URL), human contributors only, most
# contributions first. Generated from the GitHub contributors API.
CONTRIBUTORS: tuple[tuple[str, str], ...] = (
    ("accesswatch", "https://github.com/accesswatch"),
    ("taylorarndt", "https://github.com/taylorarndt"),
    ("mbabcock-acb", "https://github.com/mbabcock-acb"),
    ("krperry", "https://github.com/krperry"),
    ("kellylford", "https://github.com/kellylford"),
)


def contributor_bullet_list() -> str:
    """Render the contributors as a Markdown bullet list of profile links."""
    return "\n".join(f"- [{name}]({url})" for name, url in CONTRIBUTORS)


# ---------------------------------------------------------------------------
# Refresh helper (developer tooling, not used at runtime)
# ---------------------------------------------------------------------------

_REPO = "Community-Access/quill"


def _is_bot(login: str, account_type: str) -> bool:
    return account_type == "Bot" or login.endswith("[bot]") or login.endswith("-bot")


def fetch_contributors() -> tuple[tuple[str, str], ...]:
    """Fetch current human contributors from the GitHub contributors API.

    Returns ``(login, profile_url)`` tuples, bots removed, most contributions
    first. Raises on network or auth failure; this is build-time tooling, not a
    runtime dependency of the About screen.
    """
    import json
    import urllib.request

    url = f"https://api.github.com/repos/{_REPO}/contributors?per_page=100&anon=0"
    request = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json"})
    import os

    token = os.environ.get("GITHUB_TOKEN", "").strip()
    if token:
        request.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(request, timeout=15) as response:  # noqa: S310 - fixed GitHub host
        payload = json.loads(response.read().decode("utf-8"))

    contributors: list[tuple[str, str]] = []
    for entry in payload:
        login = str(entry.get("login", "")).strip()
        if not login or _is_bot(login, str(entry.get("type", ""))):
            continue
        contributors.append((login, str(entry.get("html_url", f"https://github.com/{login}"))))
    return tuple(contributors)


def _print_refreshed_tuple() -> None:
    contributors = fetch_contributors()
    print("CONTRIBUTORS: tuple[tuple[str, str], ...] = (")
    for name, url in contributors:
        print(f'    ("{name}", "{url}"),')
    print(")")


if __name__ == "__main__":
    _print_refreshed_tuple()
