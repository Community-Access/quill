"""What a Site Health problem or a broken link means, and what to do about it (PRD D3, WP-R-048).

WordPress's Site Health labels a test ("Page cache is not detected") and
leaves the rest to you. :func:`problem_help` says, for each row the
Workbench lists under Site Health and Needs My Attention > Broken Links:

- what it means for the people who visit the site;
- what usually causes it;
- the steps, in order;
- where Take Me There goes (a node of the site in the tree, or a wp-admin
  screen when only wp-admin can do it);
- whether Fix... can do it from here (``fix``): ``"link"`` changes a broken
  link in the post that holds it, ``"timezone"`` sets a city time zone, and
  ``"screen"`` opens the wp-admin screen that fixes it, saying why first.

The test a row came from is in its ``raw["test"]`` (WordPress's own test
name, such as ``page-cache``, or QUILL's own check, such as ``permalinks``);
rows from older loads are matched by the words they start with. Wx-free.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from quill.core.wordpress.workbench_rows import WbRow

__all__ = ["BROKEN_LINK", "ProblemHelp", "explanation", "problem_help", "check_of"]


@dataclass(frozen=True)
class ProblemHelp:
    """One kind of problem, explained."""

    title: str
    means: str
    causes: str
    steps: str
    there: str = ""  # a node key under the site, for Take Me There
    screen: str = ""  # an ADMIN_SCREENS key, when only wp-admin fixes it
    fix: str = ""  # "link", "timezone" or "screen"; "" when nothing here can fix it


_HEALTH = ProblemHelp(
    "Site Health",
    "WordPress checked how the site is set up and found something to look at.",
    "Each check has its own causes; WordPress's own words follow below.",
    "Read WordPress's description below, then Take Me There opens Tools > Site Health in "
    "wp-admin, which links to the fix.",
    there="site_health",
    screen="site_health",
    fix="screen",
)

BROKEN_LINK = ProblemHelp(
    "Broken link",
    "A visitor who follows this link lands on an error page instead of what you meant, and a "
    "screen reader user hears the link's words with no way to tell it is broken until it fails.",
    "The page it points to moved or was deleted, the address was typed wrong, or the other "
    "site is down for now.",
    "1. Open the address in your browser to see whether it is really gone. 2. Find where it "
    "moved, or a page that says the same. 3. Fix... changes the link in the post that holds "
    "it, after a preview, or Open in Editor lets you change the words around it too.",
    there="by_name_links",
    fix="link",
)

#: Site Health's own tests, and QUILL's checks, by test name.
_TESTS: Mapping[str, ProblemHelp] = {
    "https-status": ProblemHelp(
        "HTTPS",
        "Without HTTPS, browsers call the site not secure, and anything a visitor types, "
        "such as a form or a password, can be read on the way.",
        "The host has no certificate for the address, or WordPress's own address still starts "
        "with http.",
        "1. Ask the host to turn on a free certificate, such as Let's Encrypt. 2. Then, in "
        "Settings > General in wp-admin, change both addresses to start with https.",
        there="settings",
        screen="general",
        fix="screen",
    ),
    "background-updates": ProblemHelp(
        "Background updates",
        "Security releases of WordPress cannot install themselves, so the site can stay "
        "exposed to a known problem until someone updates it by hand.",
        "A setting in wp-config.php turns them off, the files are not writable by the web "
        "server, or the site is under version control.",
        "1. Ask whoever runs the server whether updates are turned off on purpose. 2. If not, "
        "they can make the files writable or remove the setting. 3. Meanwhile, Dashboard > "
        "Updates installs each release.",
        there="updates",
        screen="updates",
        fix="screen",
    ),
    "loopback-requests": ProblemHelp(
        "Loopback requests",
        "The site cannot call itself, so scheduled posts can miss their time and the theme "
        "and plugin editors cannot check a change before saving it.",
        "A firewall or security plugin blocks the server from reaching its own address, or the "
        "host's address setup is wrong.",
        "1. Turn off security plugins one at a time and check again. 2. If none is the cause, "
        "ask the host to let the server reach its own address.",
        there="plugins",
        screen="site_health",
        fix="screen",
    ),
    "dotorg-communication": ProblemHelp(
        "Reaching WordPress.org",
        "The site cannot ask WordPress.org for updates, so plugins and WordPress itself are "
        "not offered their security fixes.",
        "The host blocks outgoing connections, or WordPress.org could not be reached when the "
        "check ran.",
        "1. Run the check again later. 2. If it still fails, ask the host to allow outgoing "
        "connections to api.wordpress.org.",
        there="updates",
        screen="site_health",
        fix="screen",
    ),
    "authorization-header": ProblemHelp(
        "The authorization header",
        "Visitors are not affected, but application passwords cannot work: every request QUILL "
        "or another app signs arrives looking signed out.",
        "The web server drops the Authorization header before WordPress sees it, common on "
        "some shared hosts.",
        "1. Ask the host or the site's administrator to pass the Authorization header through, "
        "usually one line in the site's .htaccess file. 2. Connect the site again in QUILL.",
        there="app_passwords",
        screen="site_health",
    ),
    "page-cache": ProblemHelp(
        "Page cache",
        "Every visit builds the page from scratch, so pages open more slowly, worst on a busy "
        "day or a slow phone connection.",
        "No caching plugin is on, and the host does not cache pages for you.",
        "1. Ask the host whether they offer page caching. 2. If not, a caching plugin such as "
        "WP Super Cache does it; Find a Plugin on WordPress.org, on Plugins, finds one.",
        there="plugins",
        screen="site_health",
        fix="screen",
    ),
    "permalinks": ProblemHelp(
        "Permalinks",
        "Addresses read like ?p=123, which say nothing to a visitor who hears or reads them, "
        "and search engines rank them lower.",
        "Settings > Permalinks is still on Plain, the first setting a new site has.",
        "1. Read Settings in the Workbench: Permalinks says what your newest post's address "
        "would become under each choice. 2. Choose Post name in Settings > Permalinks in "
        "wp-admin; WordPress sends the old addresses on to the new ones.",
        there="settings",
        screen="permalinks",
        fix="screen",
    ),
    "timezone": ProblemHelp(
        "Time zone",
        "With a fixed offset, scheduled posts go out an hour early or late for half the year, "
        "because the clock does not follow daylight saving.",
        "The time zone was set as UTC plus a number of hours rather than as a city.",
        "1. Fix... asks for a city, such as Europe/London or America/Chicago, and sets it. "
        "2. Check a scheduled post's time afterwards.",
        there="settings",
        fix="timezone",
    ),
    "wordpress-version": ProblemHelp(
        "WordPress version",
        "Which WordPress the site runs. An old version can lack security fixes visitors rely on.",
        "WordPress was not updated, or updates are held back on purpose.",
        "Check for Updates on WordPress.org, on a plugin's row, says whether a newer one waits; "
        "Dashboard > Updates installs it.",
        there="updates",
        screen="updates",
        fix="screen",
    ),
    "search-visibility": ProblemHelp(
        "Search engine visibility",
        "When it is on, search engines are asked to leave the site out, so new visitors cannot "
        "find it by searching. It asks: it does not hide the site from anyone who has the "
        "address.",
        "It is checked while a site is being built, and often left on at launch.",
        "1. Open Settings > Reading in wp-admin. 2. Uncheck Discourage search engines from "
        "indexing this site, once the site is ready.",
        there="settings",
        screen="reading",
        fix="screen",
    ),
}

#: Rows from QUILL's own checks, matched by the words they start with.
_PREFIXES: tuple[tuple[str, str], ...] = (
    ("HTTPS", "https-status"),
    ("Permalinks", "permalinks"),
    ("Time zone", "timezone"),
    ("WordPress version", "wordpress-version"),
    ("Search engine visibility", "search-visibility"),
    ("Background updates", "background-updates"),
    ("Loopback", "loopback-requests"),
    ("The authorization header", "authorization-header"),
    ("Page cache", "page-cache"),
)


def check_of(row: WbRow) -> str:
    """The test a problem row came from ("" when it cannot be told)."""
    named = str(row.raw.get("test", "") or "")
    if named:
        return named
    said = row.detail or row.cell("says")
    return next((test for prefix, test in _PREFIXES if said.startswith(prefix)), "")


def problem_help(row: WbRow) -> ProblemHelp:
    """What *row*'s problem means and what can be done; Site Health's own words otherwise."""
    if row.key.startswith("broken:") or row.cell("problem") == "Broken link":
        return BROKEN_LINK
    return _TESTS.get(check_of(row), _HEALTH)


def explanation(row: WbRow) -> str:
    """Explain on a problem row: the meaning, the causes, the steps, and WordPress's words."""
    found = problem_help(row)
    passed = row.status == "good"
    lines = [f"{found.title}: {row.detail or row.cell('says')}".rstrip()]
    if passed:
        lines.append(f"This check passed. What it watches for: {found.means}")
    else:
        lines += [
            f"What it means for visitors: {found.means}",
            f"What usually causes it: {found.causes}",
            f"What to do: {found.steps}",
        ]
    wordpress = str(row.raw.get("description", "") or "")
    if wordpress:
        lines.append(f"WordPress says: {wordpress}")
    if found is BROKEN_LINK:
        target = row.raw.get("target_url") or row.cell("target")
        holder = row.cell("test")
        if target:
            lines.append(f"The link: {target}" + (f", in {holder}." if holder else "."))
    return "\n\n".join(lines)
