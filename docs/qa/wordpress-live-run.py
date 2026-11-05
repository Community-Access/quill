#!/usr/bin/env python
"""Live regression run for QUILL's WordPress and Forms features.

Runs the automatable parts of ``docs/qa/wordpress-regression-testing.md`` (tests
1 to 68) and every wordpress.md 9.15 and 9.16 feature against the real test
site, through the same core functions QUILL's commands call
(``quill/core/wordpress`` and ``quill/core/forms``). Anything that needs a
screen reader, an ear or eyes is recorded as "needs Jeff", never guessed.

Run it from the repository root::

    python docs/qa/wordpress-live-run.py --public     # no sign-in at all
    python docs/qa/wordpress-live-run.py --dry-run    # signed in, writes nothing to the site
    python docs/qa/wordpress-live-run.py              # signed in, the full run

Passwords (signed-in runs only) come, in this order, from:

1. Windows Credential Manager, through ``keyring``: service
   :data:`SERVICE`, user name ``"<login> application"`` (see
   ``docs/qa/wordpress-test-site/store-passwords.py``);
2. the file named by ``QUILL_LIVE_ACCOUNTS``, lines of the form
   ``<login> application password: <password>``;
3. one environment variable per login, ``QUILL_LIVE_APP_PASSWORD_<LOGIN>``
   (``QUILL_LIVE_APP_PASSWORD_QUILL_EDITOR`` for quill-editor).

A password is never printed, logged or written. Every error that is reported
has its Authorization header, and any password, masked.

Everything the run creates has "QUILL live test" in its title, and is trashed
or deleted afterwards; every setting it changes is put back. With
``--dry-run`` nothing is written to the site. The results replace the
"Live run" section of the regression plan, and the plan's HTML and EPUB are
rendered again with pandoc when it is on the PATH.
"""

from __future__ import annotations

import argparse
import base64
import datetime as dt
import io
import json
import os
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import time
import traceback
import zipfile
import zlib
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[2]
DOC = ROOT / "docs" / "qa" / "wordpress-regression-testing.md"

SITE_URL = "https://lp.csedesigns.com/wordpress"
SITE_NAME = "QUILL WordPress Test Site"
TAG = "QUILL live test"
SERVICE = "QUILL WordPress test site (lp.csedesigns.com)"

#: Every login on the test site; the last has a sign-in password only.
LOGINS = ("quilladmin", "quill-editor", "quill-author", "quill-contributor", "quill-subscriber")
#: The logins the harness signs in as, with the role each should have.
ROLES: dict[str, str] = {
    "quilladmin": "Administrator",
    "quill-editor": "Editor",
    "quill-author": "Author",
    "quill-contributor": "Contributor",
}
ADMIN, EDITOR, AUTHOR, CONTRIBUTOR = tuple(ROLES)
KINDS = ("sign-in", "application")

PASS = "pass"
FAIL = "fail"
NEEDS_JEFF = "needs Jeff"
NOT_RUN = "not run"
OUTCOMES = (PASS, FAIL, NEEDS_JEFF, NOT_RUN)
NO_SIGN_IN = "no sign-in"

SECTION_HEADING = "## Live run"
SECTION_BEFORE = "## Looking after the site"

AREAS = (
    "Site and routes",
    "Public content",
    "Connecting (4)",
    "Writing and opening (5.1, 5.2)",
    "Saving and publishing (5.3, 5.4, 9.2)",
    "Properties, versions, Trash (5.5, 5.6)",
    "Checks (7)",
    "Pictures (6)",
    "Comments, categories and tags (9.8, 9.13)",
    "Listen and watch (6.1a)",
    "The site's own kinds (5.2)",
    "More from the API (9.15)",
    "Every route (9.16)",
    "Forms (17a)",
    "Clean-up",
)


# =========================================================================== #
# Pure parts (unit-tested in tests/unit/docs/test_wordpress_live_run.py)


_ACCOUNT_LINE = re.compile(
    r"^\s*(?P<login>[A-Za-z0-9._@-]+)\s+(?P<kind>sign-in|signin|application|app)\s+"
    r"password\s*:\s*(?P<secret>.*?)\s*$",
    re.IGNORECASE,
)


def parse_accounts(text: str) -> dict[tuple[str, str], str]:
    """``(login, kind) -> password`` from the test-accounts format.

    Each line is ``<login> sign-in password: <pw>`` or ``<login> application
    password: <pw>``; *kind* comes back as ``"sign-in"`` or ``"application"``.
    Blank lines, comments and anything else are skipped, and a later line for
    the same entry wins (the server file is appended to when a password is
    remade).
    """
    found: dict[tuple[str, str], str] = {}
    for line in text.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        match = _ACCOUNT_LINE.match(line)
        if match is None or not match.group("secret"):
            continue
        kind = match.group("kind").lower()
        kind = "application" if kind in ("application", "app") else "sign-in"
        found[(match.group("login"), kind)] = match.group("secret")
    return found


def env_name(login: str) -> str:
    """``quill-editor`` -> ``QUILL_LIVE_APP_PASSWORD_QUILL_EDITOR``."""
    return "QUILL_LIVE_APP_PASSWORD_" + re.sub(r"[^A-Za-z0-9]", "_", login).upper()


def secret_forms(username: str, secret: str) -> list[str]:
    """Every spelling of *secret* that could reach an error message.

    The password as given, without its spaces, and the Basic token built from
    either, since that is what an Authorization header carries.
    """
    forms: list[str] = []
    for pw in dict.fromkeys((secret, secret.strip(), secret.replace(" ", ""))):
        if not pw:
            continue
        forms.append(pw)
        if username:
            token = f"{username.strip()}:{pw.strip()}".encode()
            forms.append(base64.b64encode(token).decode("ascii"))
    # Longest first, so a shorter form never leaves part of a longer one behind.
    return sorted(dict.fromkeys(f for f in forms if len(f) >= 4), key=len, reverse=True)


MASK = "***"
_AUTH_HEADER = re.compile(r"(?i)(authorization[\"']?\s*[:=]\s*[\"']?)(basic|bearer)?\s*[^\s\"',}]+")
_AUTH_TOKEN = re.compile(r"(?i)\b(basic|bearer)\s+[A-Za-z0-9+/=._~-]{12,}")


def mask(text: object, secrets: Iterable[str] = ()) -> str:
    """*text* with every Authorization header and every known secret replaced by ``***``."""
    out = str(text)
    for secret in sorted({s for s in secrets if s}, key=len, reverse=True):
        out = out.replace(secret, MASK)
    out = _AUTH_HEADER.sub(lambda m: m.group(1) + ((m.group(2) or "") + " ").lstrip() + MASK, out)
    out = _AUTH_TOKEN.sub(lambda m: f"{m.group(1)} {MASK}", out)
    return out


@dataclass(frozen=True)
class Result:
    area: str
    ref: str  # the plan's test number, or a 9.15 / 9.16 name
    name: str
    outcome: str
    detail: str = ""
    who: str = NO_SIGN_IN


class Results:
    """Every result of one run, in the order they were recorded."""

    def __init__(self) -> None:
        self.rows: list[Result] = []

    def add(
        self, area: str, ref: str, name: str, outcome: str, detail: str = "", who: str = NO_SIGN_IN
    ) -> Result:
        if outcome not in OUTCOMES:
            raise ValueError(f"unknown outcome {outcome!r}")
        row = Result(area, ref, name, outcome, detail, who)
        self.rows.append(row)
        return row

    def counts(self) -> dict[str, int]:
        found = dict.fromkeys(OUTCOMES, 0)
        for row in self.rows:
            found[row.outcome] += 1
        return found

    def by_area(self) -> list[tuple[str, list[Result]]]:
        order = {name: n for n, name in enumerate(AREAS)}
        grouped: dict[str, list[Result]] = {}
        for row in self.rows:
            grouped.setdefault(row.area, []).append(row)
        return sorted(grouped.items(), key=lambda kv: order.get(kv[0], len(order)))

    def failures(self) -> list[Result]:
        return [r for r in self.rows if r.outcome == FAIL]


def cell(text: object, limit: int = 220) -> str:
    """One Markdown table cell: one line, pipes escaped, kept short."""
    words = " ".join(str(text).split()).replace("|", "\\|")
    return words if len(words) <= limit else words[: limit - 3].rstrip() + "..."


def render_section(results: Results, meta: Mapping[str, str]) -> str:
    """The "Live run" section: the facts of the run, then one small table per area."""
    counts = results.counts()
    total = ", ".join(f"{counts[o]} {o}" for o in OUTCOMES)
    lines = [
        SECTION_HEADING,
        "",
        "Written by `docs/qa/wordpress-live-run.py`; run it again rather than editing this",
        f'section by hand. A result marked "{NO_SIGN_IN}" was checked without signing in.',
        "",
    ]
    for key in ("Date", "Build", "Mode", "Site", "Plugins"):
        if meta.get(key):
            lines.append(f"- **{key}:** {meta[key]}")
    lines.append(f"- **Results:** {total}")
    for area, rows in results.by_area():
        lines += [
            "",
            f"### {area}",
            "",
            "| Test | Check | Result | As | Detail |",
            "|---|---|---|---|---|",
        ]
        for row in rows:
            lines.append(
                f"| {cell(row.ref, 24)} | {cell(row.name, 80)} | {row.outcome} | "
                f"{cell(row.who, 24)} | {cell(row.detail)} |"
            )
    return "\n".join(lines) + "\n"


def replace_section(document: str, section: str) -> str:
    """*document* with its "Live run" section replaced, or added before the site's upkeep."""
    newline = "\r\n" if "\r\n" in document else "\n"
    text = document.replace("\r\n", "\n")
    body = section.rstrip("\n") + "\n\n"
    start = _heading_at(text, SECTION_HEADING)
    if start >= 0:
        end = _next_h2(text, start + len(SECTION_HEADING))
        text = text[:start] + body + text[end:] if end >= 0 else text[:start] + body
    else:
        before = _heading_at(text, SECTION_BEFORE)
        if before >= 0:
            text = text[:before] + body + text[before:]
        else:
            text = text.rstrip("\n") + "\n\n" + body
    return text.rstrip("\n").replace("\n", newline) + newline


def _heading_at(text: str, heading: str) -> int:
    match = re.search(rf"(?m)^{re.escape(heading)}[ \t]*$", text)
    return match.start() if match else -1


def _next_h2(text: str, after: int) -> int:
    match = re.compile(r"(?m)^## ").search(text, after)
    return match.start() if match else -1


# =========================================================================== #
# Passwords, at run time only


@dataclass
class Passwords:
    found: dict[str, str] = field(default_factory=dict, repr=False)
    where: dict[str, str] = field(default_factory=dict)
    missing: list[str] = field(default_factory=list)

    def __repr__(self) -> str:  # never the values
        return f"Passwords(found={sorted(self.found)}, missing={self.missing})"


def load_passwords(logins: Iterable[str], environ: Mapping[str, str] | None = None) -> Passwords:
    """Each login's application password, from Credential Manager, the file, or the environment."""
    env = os.environ if environ is None else environ
    out = Passwords()
    wanted = list(logins)
    keyring_get = _keyring_getter()
    file_entries: dict[tuple[str, str], str] = {}
    accounts_path = env.get("QUILL_LIVE_ACCOUNTS", "").strip()
    if accounts_path:
        try:
            file_entries = parse_accounts(Path(accounts_path).read_text(encoding="utf-8"))
        except OSError as exc:
            print(f"QUILL_LIVE_ACCOUNTS could not be read: {exc.strerror or exc}.")
    for login in wanted:
        secret, where = "", ""
        if keyring_get is not None:
            try:
                secret = keyring_get(SERVICE, f"{login} application") or ""
            except Exception:  # noqa: BLE001 - a locked or missing vault is just "not here"
                secret = ""
            where = "Credential Manager" if secret else ""
        if not secret and (login, "application") in file_entries:
            secret, where = file_entries[(login, "application")], "QUILL_LIVE_ACCOUNTS"
        if not secret and env.get(env_name(login)):
            secret, where = env[env_name(login)], env_name(login)
        if secret:
            out.found[login] = secret
            out.where[login] = where
        else:
            out.missing.append(login)
    return out


def _keyring_getter() -> Callable[[str, str], str | None] | None:
    try:
        import keyring
    except ImportError:
        return None
    return keyring.get_password


# =========================================================================== #
# Running checks


class CheckFailed(Exception):
    """The outcome the plan states did not happen."""


class NeedsJeff(Exception):
    """The rest needs a person: a screen reader, an ear or eyes."""


class NotRun(Exception):
    """Could not be tried here (a dry run, or the site lacks what it needs)."""


@dataclass(frozen=True)
class Check:
    area: str
    ref: str
    name: str
    fn: Callable[[Ctx], str]
    who: str = ""  # login it signs in as; "" for no sign-in
    writes: bool = False


CHECKS: list[Check] = []


def check(area: str, ref: str, name: str, *, who: str = "", writes: bool = False):
    def register(fn: Callable[[Ctx], str]) -> Callable[[Ctx], str]:
        CHECKS.append(Check(area, ref, name, fn, who, writes))
        return fn

    return register


#: The parts of the plan only a person can judge, recorded as "needs Jeff".
HUMAN: tuple[tuple[str, str, str, str], ...] = (
    ("Connecting (4)", "2", "Connect with the browser", "approving in a browser"),
    ("Connecting (4)", "5, 6", "Many sites, Remove", "the Sites window"),
    (
        "Writing and opening (5.1, 5.2)",
        "7, 8, 12",
        "New Post, New Page, Open Local Draft",
        "local documents in the editor",
    ),
    (
        "Saving and publishing (5.3, 5.4, 9.2)",
        "14",
        "Publish confirmation and clipboard",
        "hearing the confirmation",
    ),
    (
        "Saving and publishing (5.3, 5.4, 9.2)",
        "18",
        "Compare, Open the Site's Copy, Send Mine Anyway",
        "the conflict dialog",
    ),
    ("Saving and publishing (5.3, 5.4, 9.2)", "19", "Closing never publishes", "closing a window"),
    (
        "Properties, versions, Trash (5.5, 5.6)",
        "21, 22",
        "View, Restore, Compare with Site",
        "the versions window",
    ),
    ("Checks (7)", "24", "Go to It reaches each finding", "the caret and a screen reader"),
    (
        "Pictures (6)",
        "26, 27",
        "Insert Picture from the library or this computer",
        "the image dialog",
    ),
    ("Pictures (6)", "28", "Remove from Library keeps a backup", "the Documents folder"),
    ("Listen and watch (6.1a)", "31", "Play on the tone", "an ear: the tone, the keys, Close"),
    (
        "Listen and watch (6.1a)",
        "32",
        "The clip's picture with NVDA and JAWS",
        "eyes and a screen reader",
    ),
    ("Listen and watch (6.1a)", "33", "Nothing is saved", "the Downloads and Documents folders"),
    ("Listen and watch (6.1a)", "35", "Open in Browser, Open in Quill Media Player", "a browser"),
    ("Listen and watch (6.1a)", "37", "QUILL Lite repeats 31, 32, 36", "QUILL Lite"),
    ("Every route (9.16)", "43", "Icons read by label, decorative skipped", "NVDA on the page"),
    ("Every route (9.16)", "44", "The size and 'can take a while' are spoken first", "an ear"),
    ("Every route (9.16)", "45", "The thumbnail shows the edit", "eyes"),
    (
        "Every route (9.16)",
        "47",
        "Bring Back Removed Items, Restore This Version",
        "the Menus window (the run reads the history only)",
    ),
    ("Every route (9.16)", "55", "QUILL Lite repeats 40, 43, 50, 54", "QUILL Lite"),
    ("Forms (17a)", "56-62", "New Form to Not a form", "local; the editors and a screen reader"),
    ("Forms (17a)", "64", "QUILL asks before publishing over the site's change", "the question"),
    ("Forms (17a)", "65", "The form filled in with NVDA on the page", "NVDA in a browser"),
    ("Forms (17a)", "67", "New response count after a restart", "restarting QUILL"),
    ("Forms (17a)", "68", "QUILL Lite, and Safe Mode", "QUILL Lite and Safe Mode"),
)


class Ctx:
    """What every check shares: the clients, the index, the clean-up list, the masking."""

    def __init__(self, args: argparse.Namespace) -> None:
        self.args = args
        self.dry_run: bool = bool(args.dry_run)
        self.results = Results()
        self.secrets: list[str] = []
        self.apis: dict[str, Any] = {}
        self.accounts: dict[str, Any] = {}
        self.cleanups: list[tuple[str, Callable[[], object]]] = []
        self.state: dict[str, Any] = {}
        self.scratch = Path(tempfile.mkdtemp(prefix="quill-live-"))
        self.stamp = dt.datetime.now(dt.UTC).strftime("%Y-%m-%d %H:%M")
        from quill.core.wordpress.api import SiteAddress, SiteAuth, WordPressApi

        self.anon = WordPressApi(SiteAddress(SITE_URL), SiteAuth("none"), site_name=SITE_NAME)
        self.index_raw: dict[str, Any] = {}
        self.index: Any = None

    def mask(self, text: object) -> str:
        return mask(text, self.secrets)

    def api(self, login: str) -> Any:
        if login not in self.apis:
            raise NotRun(f"no application password for {login}")
        return self.apis[login]

    def later(self, what: str, undo: Callable[[], object]) -> None:
        """Put something back after the run (last made, first undone)."""
        self.cleanups.append((what, undo))

    def title(self, words: str) -> str:
        return f"{TAG}: {words} ({self.stamp})"


def run_check(ctx: Ctx, item: Check) -> Result:
    who = item.who or NO_SIGN_IN
    if item.who and item.who not in ctx.apis:
        return ctx.results.add(
            item.area, item.ref, item.name, NOT_RUN, f"no application password for {item.who}", who
        )
    if item.writes and ctx.dry_run:
        return ctx.results.add(
            item.area, item.ref, item.name, NOT_RUN, "dry run: this one writes to the site", who
        )
    try:
        detail = item.fn(ctx) or ""
        outcome = PASS
    except CheckFailed as exc:
        outcome, detail = FAIL, str(exc)
    except NeedsJeff as exc:
        outcome, detail = NEEDS_JEFF, str(exc)
    except NotRun as exc:
        outcome, detail = NOT_RUN, str(exc)
    except Exception as exc:  # noqa: BLE001 - every failure is a row, never a crash
        outcome, detail = FAIL, f"{type(exc).__name__}: {exc}"
        if ctx.args.verbose:
            print(ctx.mask(traceback.format_exc()))
    return ctx.results.add(item.area, item.ref, item.name, outcome, ctx.mask(detail), who)


def expect(condition: object, why: str) -> None:
    if not condition:
        raise CheckFailed(why)


def refused(call: Callable[[], object]) -> Any:
    """The WordPressApiError *call* raises, or CheckFailed when it succeeds."""
    from quill.core.wordpress.api import WordPressApiError

    try:
        call()
    except WordPressApiError as exc:
        return exc
    raise CheckFailed("the site allowed it")


def fetch(
    url: str, *, method: str = "GET", limit: int = 4_000_000
) -> tuple[int, dict[str, str], bytes]:
    """A public address, unsigned: (status, headers, body)."""
    request = Request(url, method=method, headers={"User-Agent": "QUILL live test"})
    try:
        with urlopen(request, timeout=30) as response:
            return response.status, dict(response.headers.items()), response.read(limit)
    except HTTPError as exc:
        return exc.code, dict(exc.headers.items()), exc.read(limit)


def site_url(path: str) -> str:
    return SITE_URL.rstrip("/") + "/" + path.lstrip("/")


def admin_like_account() -> Any:
    from quill.core.wordpress.site import Account

    caps = frozenset({
        "read",
        "edit_posts",
        "upload_files",
        "edit_theme_options",
        "view_site_health_checks",
        "export",
        "manage_options",
        "moderate_comments",
        "publish_posts",
        "publish_pages",
    })
    return Account(0, "", "", ("administrator",), caps)


def forms_site() -> Any:
    """The forms plugin's module: ``qaf_site`` now, ``baf_site`` before the rename."""
    try:
        from quill.core.forms import qaf_site as module
    except ImportError:
        from quill.core.forms import baf_site as module  # type: ignore[no-redef]
    return module


def forms_supported(api: Any) -> bool:
    fs = forms_site()
    probe = getattr(fs, "supports_qaf", None) or fs.supports_baf
    return bool(probe(api))


def forms_prefix(api: Any) -> str:
    fs = forms_site()
    return fs.plugin_prefix(api) if hasattr(fs, "plugin_prefix") else "baf"


def forms_namespace(api: Any) -> str:
    fs = forms_site()
    if hasattr(fs, "site_namespace"):
        return fs.site_namespace(api) or ""
    return "baf/v1" if forms_supported(api) else ""


def with_prefix(fn: Callable[..., Any], *args: Any, prefix: str) -> Any:
    """Call a forms helper that takes the plugin prefix (after the rename) or does not."""
    try:
        return fn(*args, prefix)
    except TypeError:
        return fn(*args)


def tiny_png(width: int = 800, height: int = 600) -> bytes:
    """A plain blue picture, big enough that WordPress makes its smaller sizes."""
    row = b"\x00" + bytes((40, 90, 200)) * width
    raw = zlib.compress(row * height, 9)

    def chunk(kind: bytes, data: bytes) -> bytes:
        body = kind + data
        return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body))

    header = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header) + chunk(b"IDAT", raw) + chunk(b"IEND", b"")


def tiny_wav(seconds: float = 1.0, rate: int = 8000) -> bytes:
    frames = int(seconds * rate)
    import math

    data = b"".join(
        struct.pack("<h", int(8000 * math.sin(2 * math.pi * 440 * n / rate))) for n in range(frames)
    )
    return (
        b"RIFF"
        + struct.pack("<I", 36 + len(data))
        + b"WAVEfmt "
        + struct.pack("<IHHIIHH", 16, 1, 1, rate, rate * 2, 2, 16)
        + b"data"
        + struct.pack("<I", len(data))
        + data
    )


def find_post(ctx: Ctx, login: str, kind: str, title: str, statuses: tuple[str, ...]) -> Any:
    from quill.core.wordpress import site as wp

    for row in wp.list_items(ctx.api(login), kind, statuses=statuses, search=title):
        if row.title == title:
            return row
    raise NotRun(f"'{title}' is not on the site; run reset.sh first")


# =========================================================================== #
# Without signing in


@check("Site and routes", "index", "REST index answers and names the site")
def _index(ctx: Ctx) -> str:
    from quill.core.wordpress.site_features import read_index

    raw = ctx.anon.get("")
    expect(isinstance(raw, dict), "the index is not a JSON object")
    ctx.index_raw = raw
    ctx.index = read_index(ctx.anon)
    expect(raw.get("name") == SITE_NAME, f"the site is called {raw.get('name')!r}")
    wanted = {"wp/v2", "wp-site-health/v1", "wp-block-editor/v1", "wp-abilities/v1", "oembed/1.0"}
    missing = sorted(wanted - set(ctx.index.namespaces))
    expect(not missing, f"namespaces missing: {', '.join(missing)}")
    return f"{len(ctx.index.routes)} routes in {len(ctx.index.namespaces)} namespaces"


@check("Site and routes", "index", "Site version and application passwords (load_site_info)")
def _site_info(ctx: Ctx) -> str:
    from quill.core.wordpress.site import load_site_info
    from quill.core.wordpress.site_features import at_least

    info = load_site_info(ctx.anon)
    ctx.state["wp_version"] = info.wp_version
    expect(info.wp_version, "no WordPress version found (index or feed)")
    expect(at_least(info.wp_version, (7, 0)), f"WordPress {info.wp_version} is older than 7.0")
    expect(info.authorize_url.endswith("authorize-application.php"), "no authorize address")
    return f"WordPress {info.wp_version}; application passwords offered"


@check("Site and routes", "9.15", "Plugins QUILL recognises (site_health.recognised)")
def _recognised(ctx: Ctx) -> str:
    from quill.core.wordpress.site_health import recognised

    names = [name for name, _ in recognised(ctx.index_raw)]
    for wanted in ("The Events Calendar", "WooCommerce", "Yoast SEO", "Abilities for AI"):
        expect(wanted in names, f"{wanted} not recognised")
    return ", ".join(names)


@check("Site and routes", "17a", "Forms plugin namespace (site_namespace)")
def _forms_ns(ctx: Ctx) -> str:
    namespace = forms_namespace(ctx.anon)
    expect(namespace, "neither qaf/v1 nor baf/v1 is in the index")
    routes = [r for r in ctx.index.routes if r.startswith("/" + namespace)]
    module = forms_site().__name__.rsplit(".", 1)[-1]
    return f"{namespace}, {len(routes)} routes; QUILL module {module}"


@check("Site and routes", "17a", "Forms route takes the model QUILL sends")
def _forms_model_arg(ctx: Ctx) -> str:
    namespace = forms_namespace(ctx.anon) or "baf/v1"
    entry = ctx.index.routes.get(f"/{namespace}/forms", {})
    args: set[str] = set()
    for endpoint in entry.get("endpoints", []) if isinstance(entry, dict) else []:
        if "POST" in endpoint.get("methods", []) and isinstance(endpoint.get("args"), dict):
            args |= set(endpoint["args"])
    if "model" not in args:
        raise NeedsJeff(
            f"POST /{namespace}/forms lists {', '.join(sorted(args))} but not model; the "
            "plugin on the site may predate set_model (BAF 045c682). Test 65 shows whether "
            "a published form has its fields"
        )
    return "model is a listed argument"


@check("Site and routes", "9.16", "Every 9.16 route QUILL needs (routes.unavailable)")
def _routes_916(ctx: Ctx) -> str:
    from quill.core.wordpress import routes

    account = admin_like_account()
    gaps = {
        f: why
        for f in routes.FEATURES
        if (why := routes.unavailable(f, ctx.index, account, SITE_NAME))
    }
    expect(not gaps, "; ".join(f"{f}: {w}" for f, w in gaps.items()))
    return f"all {len(routes.FEATURES)} offered: {', '.join(routes.FEATURES)}"


@check("Site and routes", "9.15", "Every 9.15 route QUILL needs (site_features.unavailable)")
def _routes_915(ctx: Ctx) -> str:
    from quill.core.wordpress import site_features as sf

    account = admin_like_account()
    features = ("notes", "edit_picture", "which_password", "library_alt", "bulk_moderation")
    gaps = {
        f: why
        for f in features
        if (
            why := sf.unavailable(
                f, ctx.index, account, SITE_NAME, known_version=ctx.state.get("wp_version", "")
            )
        )
    }
    expect(not gaps, "; ".join(f"{f}: {w}" for f, w in gaps.items()))
    return f"all offered: {', '.join(features)}"


@check("Site and routes", "9.15", "Picture edits the site takes (edit_modifiers)")
def _modifiers(ctx: Ctx) -> str:
    found = set(ctx.index.edit_modifiers())
    expect({"rotate", "crop", "flip"} <= found, f"the site lists {sorted(found)}")
    return ", ".join(sorted(found))


def _route_args(ctx: Ctx, pattern: str) -> dict[str, Any]:
    rx = re.compile(pattern)
    for route, entry in ctx.index.routes.items():
        if rx.search(route) and isinstance(entry, dict):
            for endpoint in entry.get("endpoints", []):
                if "POST" in endpoint.get("methods", []) and isinstance(endpoint.get("args"), dict):
                    return endpoint["args"]
    return {}


@check("Site and routes", "44", "Upload a Large File uses the plain media route, not sideload")
def _pieces_shape(ctx: Ctx) -> str:
    # WordPress's media/{id}/sideload takes a picture's sub-size (image_size is
    # required), never a piece of a file; QUILL once sent pieces there. This
    # keeps it from coming back.
    from quill.core.wordpress import media_pieces as mpc

    expect(not hasattr(mpc, "PieceUpload"), "QUILL still has the piece upload")
    expect(_route_args(ctx, r"^/wp/v2/media$"), "the site takes no uploads at wp/v2/media")
    sideload = _route_args(ctx, r"^/wp/v2/media/[^/]+/sideload$")
    required = sorted(k for k, v in sideload.items() if isinstance(v, dict) and v.get("required"))
    note = f"; sideload here requires {', '.join(required)}" if required else ""
    return f"one upload to wp/v2/media{note}"


@check("Site and routes", "45", "Regenerate Sizes action is the site's (post-process)")
def _post_process(ctx: Ctx) -> str:
    args = _route_args(ctx, r"^/wp/v2/media/[^/]+/post-process$")
    enum = (args.get("action") or {}).get("enum", [])
    expect("create-image-subsizes" in enum, f"post-process actions: {enum}")
    return "action create-image-subsizes"


@check("Site and routes", "9.15", "Every Site Health test listed (health_test_names)")
def _health_names(ctx: Ctx) -> str:
    from quill.core.wordpress.site_health import FALLBACK_TESTS, health_lines, health_test_names

    names = health_test_names(ctx.index_raw)
    expect(set(FALLBACK_TESTS) <= set(names), f"tests listed: {names}")
    lines = health_lines(ctx.anon, ctx.index_raw)
    expect(
        len(lines) == 1 and "administrator" in lines[0].text,
        f"signed out, Site Check said: {[line.text for line in lines]}",
    )
    return f"{len(names)} tests: {', '.join(names)}; signed out it says only an administrator can"


@check("Site and routes", "9.16", "Batch route found and sized (SiteInfo.supports)")
def _batch(ctx: Ctx) -> str:
    from quill.core.wordpress.site import load_site_info

    info = load_site_info(ctx.anon)
    expect(info.supports("batch/v1"), "SiteInfo.supports('batch/v1') is False")
    expect("batch/v1" not in info.namespaces, "batch/v1 is a namespace now; the note is stale")
    args = _route_args(ctx, r"^/batch/v1$")
    limit = (args.get("requests") or {}).get("maxItems")
    expect(limit == 25, f"the site takes {limit} per batch; WordPressApi.batch sends 25")
    methods = ((args.get("requests") or {}).get("items") or {}).get("properties", {})
    allowed = (methods.get("method") or {}).get("enum", [])
    return f"in routes, not namespaces; 25 per batch; methods {', '.join(allowed)}"


@check("Connecting (4)", "4", "HTTP address is refused, explaining HTTPS")
def _http(ctx: Ctx) -> str:
    from quill.core.wordpress.api import SiteAddress, SiteAuth, WordPressApi, WordPressPolicyError

    try:
        WordPressApi(SiteAddress("http://lp.csedesigns.com/wordpress"), SiteAuth("none"))
    except WordPressPolicyError as exc:
        expect("HTTPS" in str(exc), f"the refusal does not say HTTPS: {exc}")
        return str(exc.args[0] if exc.args else exc)[:160]
    raise CheckFailed("an http:// address was accepted")


SEEDED_POSTS = {
    "welcome": "Welcome to the test site",
    "sticky-news": "Pinned news",
    "locked": "Password protected",
    "classic": "Classic content",
    "by-author": "Written by the author",
}
UNPUBLISHED = (
    "Things to check before publishing",
    "Waiting for review",
    "Scheduled for next month",
    "A private post",
    "In the Trash",
    "A Draft Page",
)


@check("Public content", "seed", "Published posts are public, the rest are not")
def _public_posts(ctx: Ctx) -> str:
    rows = ctx.anon.get("wp/v2/posts", per_page=100, _fields="id,slug,title,sticky,link")
    by_slug = {r["slug"]: r for r in rows}
    missing = [s for s in SEEDED_POSTS if s not in by_slug]
    expect(not missing, f"missing: {missing}")
    expect(by_slug["sticky-news"]["sticky"], "Pinned news is not sticky")
    titles = {r["title"]["rendered"] for r in rows}
    leaked = [t for t in UNPUBLISHED if t in titles]
    expect(not leaked, f"public but should not be: {leaked}")
    ctx.state["welcome_id"] = by_slug["welcome"]["id"]
    return f"{len(rows)} public posts; Pinned news sticky; no draft, pending, private or trash"


@check("Public content", "seed", "Pages and the page parent")
def _public_pages(ctx: Ctx) -> str:
    rows = ctx.anon.get("wp/v2/pages", per_page=100, _fields="id,slug,title,parent,link")
    by_slug = {r["slug"]: r for r in rows}
    for slug in ("about", "contact", "team", "every-block", "listen-and-watch"):
        expect(slug in by_slug, f"no page {slug}")
    expect(by_slug["team"]["parent"] == by_slug["about"]["id"], "Meet the Team is not under About")
    ctx.state["pages"] = by_slug
    return f"{len(rows)} public pages; Meet the Team is a child of About Us"


@check("Public content", "38", "Events type and Open Day are public")
def _public_events(ctx: Ctx) -> str:
    rows = ctx.anon.get("wp/v2/events", _fields="id,slug,title,link,type")
    open_day = next((r for r in rows if r["slug"] == "open-day"), None)
    expect(open_day, "no Open Day")
    ctx.state["open_day"] = open_day
    return f"Open Day, id {open_day['id']}, {open_day['link']}"


@check("The site's own kinds (5.2)", "38", "An opened Event goes back to its own route")
def _event_kind(ctx: Ctx) -> str:
    from quill.core.wordpress import site as wp

    open_day = ctx.state.get("open_day") or {}
    expect(open_day, "Open Day was not found")
    raw = ctx.anon.get(f"wp/v2/events/{open_day['id']}")
    item = wp.item_from_payload(raw, "events")
    route = wp.kind_route(item.kind)
    expect(
        ctx.index.has_route(rf"^/{re.escape(route)}$"),
        f"load_item keeps the post type ('{item.kind}') as the kind, so Save Draft to Site "
        f"would send to /{route}, which the site does not have (the route is /wp/v2/events)",
    )
    return f"kind {item.kind} -> /{route}"


@check("Public content", "9.15", "Properties' custom fields for an ordinary post")
def _custom_fields_public(ctx: Ctx) -> str:
    from quill.core.wordpress import custom_fields as cf
    from quill.core.wordpress.plugin_shop_seo import SEO_FIELDS

    schema = cf.meta_schema(ctx.anon, "post")
    expect(schema, "the posts schema lists no meta")
    seo = [k for k in SEO_FIELDS if k in schema]
    expect(
        "_yoast_wpseo_title" in seo and "_yoast_wpseo_metadesc" in seo,
        f"Yoast's fields are not in the schema (found {seo})",
    )
    form = cf.build_form(schema, {}, {})
    events = [f.key for f in form.fields if f.key.startswith(("_Event", "_Venue", "_Organizer"))]
    if events:
        raise NeedsJeff(
            f"Properties would show {len(form.fields)} fields on every post, {len(events)} of "
            "them The Events Calendar's event, venue and organizer fields; Yoast's title and "
            "description are among the rest. Decide whether to hide another plugin's fields"
        )
    return f"{len(form.fields)} fields, including Yoast's"


OPEN_BY_ADDRESS = (
    ("welcome/", ("post", "welcome")),
    ("about/", ("page", "about")),
    ("about/team/", ("page", "team")),
    ("?p={welcome}", ("post", "welcome")),
)
# The Events Calendar owns the event/ slug, so the test type lives at quill-event/;
# a good case anyway: QUILL must open an item by its real permalink, whatever its slug.
EVENT_ADDRESS = (
    ("quill-event/open-day/", ("events", "open-day")),
    ("?event=open-day", ("events", "open-day")),
)


class _PublicView:
    """A signed-out stand-in for the client, for Open by Web Address's own lookup.

    ``find_by_address`` asks ``status=any`` in edit mode, which needs a sign-in;
    signed out, the same slug lookup is asked without them.
    """

    def __init__(self, api: Any) -> None:
        self._api = api

    def get(self, route: str, **params: object) -> Any:
        params = {k: v for k, v in params.items() if k not in ("status", "context")}
        return self._api.get(route, **params)


def _find_by_address() -> Callable[[Any, str], tuple[str, int] | None]:
    try:
        from quill.ui.wordpress_open_commands import find_by_address
    except Exception as exc:  # noqa: BLE001 - wx missing: the UI module cannot load
        raise NotRun(f"quill.ui.wordpress_open_commands would not import: {exc}") from exc
    return find_by_address


def _address_ids(ctx: Ctx) -> dict[str, Any]:
    pages = ctx.state.get("pages") or {}
    return {
        "welcome": ctx.state.get("welcome_id", 0),
        "about": pages.get("about", {}).get("id"),
        "team": pages.get("team", {}).get("id"),
        "open-day": (ctx.state.get("open_day") or {}).get("id"),
    }


def _open_by_address(ctx: Ctx, api: Any, addresses: tuple[tuple[str, tuple[str, str]], ...]) -> str:
    find = _find_by_address()
    ids = _address_ids(ctx)
    said, wrong = [], []
    for path, (kind, slug) in addresses:
        shown = path.format(welcome=ids["welcome"])
        url = site_url(shown)
        status, _h, _b = fetch(url)
        found = find(api, url)
        (said if found == (kind, ids[slug]) else wrong).append(
            f"{shown} (page {status}) -> {found}"
        )
    expect(not wrong, "not found as expected: " + "; ".join(wrong))
    return "; ".join(said)


@check("Writing and opening (5.1, 5.2)", "11", "Open by Web Address finds each address")
def _address_public(ctx: Ctx) -> str:
    return _open_by_address(ctx, _PublicView(ctx.anon), OPEN_BY_ADDRESS)


@check("The site's own kinds (5.2)", "11, 38", "Open by Web Address finds an Event")
def _address_event(ctx: Ctx) -> str:
    try:
        return _open_by_address(ctx, _PublicView(ctx.anon), EVENT_ADDRESS)
    except CheckFailed as exc:
        raise CheckFailed(f"{exc}. find_by_address did not find the site's own type") from exc


@check("Public content", "38", "Open Day's own address answers")
def _event_permalink(ctx: Ctx) -> str:
    open_day = ctx.state.get("open_day") or {}
    expect(open_day, "Open Day was not found")
    status, _h, _b = fetch(open_day["link"])
    plain, _h2, _b2 = fetch(site_url(f"?event={open_day.get('slug', 'open-day')}"))
    expect(
        status == 200,
        f"{open_day['link']} answers {status} while ?event=open-day answers {plain}: the "
        "site's rewrite rules were not flushed after the Events type was registered, or "
        "another plugin owns its slug (setup.sh gives it quill-event and flushes); a site "
        "problem, not QUILL's",
    )
    return f"{open_day['link']} 200"


@check("Public content", "9.6", "oEmbed for /welcome/, and the proxy needs a sign-in")
def _oembed(ctx: Ctx) -> str:
    raw = ctx.anon.get("oembed/1.0/embed", url=site_url("welcome/"))
    expect(
        isinstance(raw, dict) and str(raw.get("title", "")).startswith(SEEDED_POSTS["welcome"]),
        f"oEmbed said {raw!r:.120}",
    )
    error = refused(lambda: ctx.anon.get("oembed/1.0/proxy", url=site_url("welcome/")))
    expect(error.status == 401, f"the proxy answered {error.status} signed out")
    return f"embed: {raw.get('type')}, '{raw.get('title')}'; proxy 401 signed out"


MEDIA_FILES = {
    "quill-test-tone": ("audio/wav", "audio/x-wav", "audio/wave", "audio/vnd.wave"),
    "quill-test-clip": ("video/mp4",),
    "quill-test-clip-en": ("text/vtt",),
}


def _public_media(ctx: Ctx) -> list[Any]:
    if "media" not in ctx.state:
        from quill.core.wordpress.site_media import media_from_payload

        rows = ctx.anon.get("wp/v2/media", per_page=100)
        ctx.state["media"] = [media_from_payload(r) for r in rows]
        ctx.state["media_slugs"] = {r["slug"]: r["id"] for r in rows}
    return ctx.state["media"]


def _media_by_slug(ctx: Ctx, slug: str) -> Any:
    items = _public_media(ctx)
    wanted = ctx.state["media_slugs"].get(slug)
    found = next((m for m in items if m.id == wanted), None)
    if found is None:
        raise NotRun(f"{slug} is not in the Media Library; run setup.sh")
    return found


@check("Listen and watch (6.1a)", "31-32", "Tone, clip and captions: public address and type")
def _media_urls(ctx: Ctx) -> str:
    said = []
    for slug, types in MEDIA_FILES.items():
        item = _media_by_slug(ctx, slug)
        status, headers, body = fetch(item.source_url)
        kind = next((v for k, v in headers.items() if k.lower() == "content-type"), "")
        expect(status == 200, f"{slug}: {item.source_url} answered {status}")
        expect(kind.split(";")[0].strip().lower() in types, f"{slug}: served as {kind}")
        said.append(f"{slug} 200 {kind.split(';')[0]} {len(body)} bytes")
    return "; ".join(said)


@check("Listen and watch (6.1a)", "32", "Captions found and read (from_library, fetch_captions)")
def _captions(ctx: Ctx) -> str:
    from quill.core.wordpress import media_play as mp

    clip = _media_by_slug(ctx, "quill-test-clip")
    playable = mp.from_library(clip, _public_media(ctx))
    expect(playable and playable.kind == "video", "the clip is not playable as video")
    expect(playable.captions, "no captions track found for the clip")
    cues = mp.fetch_captions(ctx.anon, playable.captions[0], SITE_URL)
    at_one = mp.caption_at(cues, 1000)
    expect(at_one == "This is the QUILL test clip.", f"at 1 s: {at_one!r}")
    expect(mp.caption_at(cues, 5500) == "", "a caption shows after five seconds")
    return f"{len(cues)} cues ({playable.captions[0].label}); 1 s: '{at_one}'; 5.5 s: none"


@check("Listen and watch (6.1a)", "34", "A picture is not playable (from_library)")
def _not_playable(ctx: Ctx) -> str:
    from quill.core.wordpress import media_play as mp

    photo = _media_by_slug(ctx, "photo-volunteers")
    expect(mp.from_library(photo, _public_media(ctx)) is None, "the photo is playable")
    tone = mp.from_library(_media_by_slug(ctx, "quill-test-tone"))
    expect(tone and tone.kind == "audio", "the tone is not playable as audio")
    return "photo-volunteers: not playable; the tone: audio"


def _play_media_here(content: str, fmt: str) -> str:
    from quill.core.wordpress import media_play as mp

    said = []
    for marker, kind in (("<audio", "audio"), ("<video", "video")):
        caret = content.find(marker)
        expect(caret >= 0, f"no {kind} in the page")
        found = mp.media_at(content, fmt, caret + 1)
        expect(found and found.kind == kind, f"caret on the {kind} found {found}")
        said.append(f"{kind}: {found.title}")
    caret = content.find("Play Media Here")
    expect(caret >= 0, "no paragraph")
    expect(mp.media_at(content, fmt, caret) is None, "the paragraph counts as media")
    said.append("paragraph: none")
    return "; ".join(said)


@check("Listen and watch (6.1a)", "36", "Play Media Here on the rendered Listen and Watch page")
def _play_here_public(ctx: Ctx) -> str:
    rows = ctx.anon.get("wp/v2/pages", slug="listen-and-watch")
    expect(rows, "no Listen and Watch page")
    return _play_media_here(rows[0]["content"]["rendered"], "html") + " (rendered HTML)"


@check("More from the API (9.15)", "TEC", "Events Coming Up, signed out (plugin_events.coming_up)")
def _tec_public(ctx: Ctx) -> str:
    from quill.core.wordpress import plugin_events as pe

    events = pe.coming_up(ctx.anon)
    return f"{len(events)} upcoming events listed" + (
        f"; first: {events[0].spoken()}" if events else ""
    )


# =========================================================================== #
# Signed in: connecting


def _role_check(login: str) -> Callable[[Ctx], str]:
    def run(ctx: Ctx) -> str:
        from quill.core.wordpress.site import load_account, load_site_info

        api = ctx.api(login)
        info = load_site_info(api)
        account = load_account(api)
        ctx.accounts[login] = account
        expect(account.role_name == ROLES[login], f"role is {account.role_name}")
        sentence = f"Connected to {info.name} as {account.role_name}."
        expect(info.name == SITE_NAME, sentence)
        return sentence

    return run


for _login in ROLES:
    check("Connecting (4)", "1", f"Connect by hand as {_login}", who=_login)(_role_check(_login))


@check("Connecting (4)", "3", "Wrong password: a plain sentence naming the site", who=EDITOR)
def _wrong_password(ctx: Ctx) -> str:
    from quill.core.wordpress.api import SiteAddress, SiteAuth, WordPressApi
    from quill.core.wordpress.site import load_account

    made_up = "abcd efgh ijkl mnop qrst uvwx"
    api = WordPressApi(
        SiteAddress(SITE_URL), SiteAuth("app_password", EDITOR, made_up), site_name=SITE_NAME
    )
    error = refused(lambda: load_account(api))
    expect(SITE_NAME in error.plain, f"does not name the site: {error.plain}")
    expect("HTTP" not in error.plain and "rest_" not in error.plain, error.plain)
    return f"{error.status} {error.wp_code}: {error.plain}"


# =========================================================================== #
# Writing and opening


@check("Writing and opening (5.1, 5.2)", "7", "Categories and tags are listed", who=EDITOR)
def _terms_listed(ctx: Ctx) -> str:
    from quill.core.wordpress import site as wp

    cats = {t.name for t in wp.list_terms(ctx.api(EDITOR), "category")}
    tags = {t.name for t in wp.list_terms(ctx.api(EDITOR), "post_tag")}
    for name in ("News", "Training", "JAWS Training", "Empty Category"):
        expect(name in cats, f"no category {name}")
    for name in ("JAWS", "Braille", "Unused Tag"):
        expect(name in tags, f"no tag {name}")
    return f"{len(cats)} categories, {len(tags)} tags"


@check("Writing and opening (5.1, 5.2)", "9", "Open lists drafts and the Trash", who=EDITOR)
def _open_lists(ctx: Ctx) -> str:
    from quill.core.wordpress import site as wp

    api = ctx.api(EDITOR)
    drafts = list(wp.list_items(api, "post", statuses=("draft",)))
    trash = list(wp.list_items(api, "post", statuses=("trash",)))
    expect(any(d.title == "Things to check before publishing" for d in drafts), "no seeded draft")
    expect(any(t.title == "In the Trash" for t in trash), "nothing seeded in the Trash")
    row = next(d for d in drafts if d.title == "Things to check before publishing").spoken()
    expect("Draft" in row and "last changed" in row, f"row reads: {row}")
    return f"{len(drafts)} drafts, {len(trash)} in Trash; row: {row}"


@check(
    "Writing and opening (5.1, 5.2)", "10", "Every Block round trip, Markdown and HTML", who=EDITOR
)
def _round_trip(ctx: Ctx) -> str:
    from quill.core.wordpress import blocks, fences
    from quill.core.wordpress import site as wp

    row = find_post(ctx, EDITOR, "page", "Every Block", ("publish",))
    item = wp.load_item(ctx.api(EDITOR), "page", row.id)
    markdown, islands = fences.post_to_markdown(item.content)
    back = fences.markdown_to_blocks(markdown, islands)

    def norm(text: str) -> str:
        return re.sub(r"\n\s*\n+", "\n\n", text.replace("\r\n", "\n")).strip()

    for label, result in (
        ("Markdown", back),
        ("HTML", blocks.serialize(blocks.parse(item.content))),
    ):
        a, b = norm(item.content), norm(result)
        if a != b:
            at = next(
                (n for n, (x, y) in enumerate(zip(a, b, strict=False)) if x != y),
                min(len(a), len(b)),
            )
            raise CheckFailed(
                f"{label} differs at character {at}: site {a[at : at + 50]!r}, "
                f"QUILL {b[at : at + 50]!r}"
            )
    return f"{len(blocks.parse(item.content))} blocks; byte for byte apart from blank lines"


@check("Writing and opening (5.1, 5.2)", "11", "Open by Web Address, signed in", who=EDITOR)
def _address_signed(ctx: Ctx) -> str:
    return _open_by_address(ctx, ctx.api(EDITOR), OPEN_BY_ADDRESS)


# =========================================================================== #
# Saving and publishing


def _new_post(
    ctx: Ctx,
    login: str,
    words: str,
    *,
    status: str = "draft",
    kind: str = "post",
    content: str = "",
) -> Any:
    from quill.core.wordpress import site as wp

    api = ctx.api(login)
    body = (
        content
        or f"<!-- wp:paragraph --><p>{TAG}. Made by the regression harness.</p>"
        "<!-- /wp:paragraph -->"
    )
    made = wp.create_item(api, wp.Item(0, kind, ctx.title(words), body, status))

    def undo() -> None:
        try:
            wp.trash_item(api, kind, made.id)
        except Exception:  # noqa: BLE001 - the author may not delete; the admin can
            wp.trash_item(ctx.api(ADMIN), kind, made.id)

    ctx.later(f"trash {kind} {made.id}", undo)
    return made


@check(
    "Saving and publishing (5.3, 5.4, 9.2)",
    "13",
    "Save Draft to Site: a draft, not public",
    who=EDITOR,
    writes=True,
)
def _save_draft(ctx: Ctx) -> str:
    made = _new_post(ctx, EDITOR, "draft")
    expect(made.status == "draft", f"status {made.status}")
    error = refused(lambda: ctx.anon.get(f"wp/v2/posts/{made.id}"))
    expect(error.status in (401, 403, 404), f"signed out it answered {error.status}")
    ctx.state["draft"] = made
    return f"draft {made.id}; signed out: {error.status}"


@check(
    "Saving and publishing (5.3, 5.4, 9.2)",
    "14",
    "Publish or Update makes it public",
    who=EDITOR,
    writes=True,
)
def _publish(ctx: Ctx) -> str:
    from quill.core.wordpress import site as wp

    made = ctx.state.get("draft") or _new_post(ctx, EDITOR, "draft")
    made.status = "publish"
    done = wp.update_item(ctx.api(EDITOR), made)
    expect(done.status == "publish", f"status {done.status}")
    status, _h, _b = fetch(done.link)
    expect(status == 200, f"{done.link} answered {status}")
    return f"published {done.id}; {done.link} 200"


@check(
    "Saving and publishing (5.3, 5.4, 9.2)",
    "15",
    "Contributor: Submit for Review, Pending",
    who=CONTRIBUTOR,
    writes=True,
)
def _contributor(ctx: Ctx) -> str:
    from quill.core.wordpress import site as wp
    from quill.core.wordpress.site import load_account

    api = ctx.api(CONTRIBUTOR)
    account = ctx.accounts.get(CONTRIBUTOR) or load_account(api)
    label = account.publish_label("post")
    expect(label == "Submit for Review", f"Publish reads {label}")
    made = _new_post(ctx, CONTRIBUTOR, "for review", status="pending")
    expect(made.status == "pending", f"arrived as {made.status}")
    error = refused(
        lambda: wp.create_item(api, wp.Item(0, "post", ctx.title("refused"), "x", "publish"))
    )
    expect(error.wp_code == "rest_cannot_publish", f"{error.wp_code}: {error.plain}")
    return f"'{label}'; arrived Pending; publishing says: {error.plain}"


@check(
    "Saving and publishing (5.3, 5.4, 9.2)",
    "16",
    "Author cannot publish a page",
    who=AUTHOR,
    writes=True,
)
def _author_page(ctx: Ctx) -> str:
    from quill.core.wordpress import site as wp
    from quill.core.wordpress.site import load_account

    api = ctx.api(AUTHOR)
    account = ctx.accounts.get(AUTHOR) or load_account(api)
    expect(not account.can_publish_pages, "the author may publish pages")
    try:
        made = wp.create_item(api, wp.Item(0, "page", ctx.title("author page"), "x", "publish"))
    except Exception as exc:  # noqa: BLE001
        plain = getattr(exc, "plain", str(exc))
        expect("HTTP" not in plain and "rest_" not in plain, plain)
        return f"refused: {plain}"
    ctx.later(f"trash page {made.id}", lambda: wp.trash_item(ctx.api(ADMIN), "page", made.id))
    raise CheckFailed("the author published a page")


def _keeps_status(ctx: Ctx, title: str, status: str) -> str:
    from quill.core.wordpress import site as wp

    api = ctx.api(ADMIN)
    row = find_post(ctx, ADMIN, "post", title, (status,))
    item = wp.load_item(api, "post", row.id)
    original, date = item.content, item.date_gmt
    ctx.later(f"put back '{title}'", lambda: wp.update_item(api, _with(item, content=original)))
    done = wp.update_item(api, _with(item, content=original + f"\n<!-- {TAG} -->"))
    expect(done.status == status, f"became {done.status}")
    expect(done.date_gmt == date, f"date moved from {date} to {done.date_gmt}")
    return f"{title}: still {status}, date kept"


def _with(item: Any, **changes: Any) -> Any:
    from dataclasses import replace

    return replace(item, **changes)


@check(
    "Saving and publishing (5.3, 5.4, 9.2)",
    "17",
    "Private and Scheduled keep their status",
    who=ADMIN,
    writes=True,
)
def _statuses(ctx: Ctx) -> str:
    return "; ".join((
        _keeps_status(ctx, "A private post", "private"),
        _keeps_status(ctx, "Scheduled for next month", "future"),
    ))


@check(
    "Saving and publishing (5.3, 5.4, 9.2)",
    "18",
    "Conflict: a change on the site is found",
    who=ADMIN,
    writes=True,
)
def _conflict(ctx: Ctx) -> str:
    from quill.core.wordpress import local as lc
    from quill.core.wordpress import site as wp

    api = ctx.api(ADMIN)
    welcome = wp.load_item(
        api,
        "post",
        ctx.state.get("welcome_id")
        or find_post(ctx, ADMIN, "post", SEEDED_POSTS["welcome"], ("publish",)).id,
    )
    base, original = welcome.modified_gmt, welcome.content
    time.sleep(1.2)
    ctx.later("put back Welcome", lambda: wp.update_item(api, _with(welcome, content=original)))
    wp.update_item(api, _with(welcome, content=original + f"\n<!-- {TAG} -->"))
    now = wp.modified_gmt(api, "post", welcome.id)
    conflict = lc.conflict_between(base, now)
    expect(conflict is not None, f"no conflict between {base} and {now}")
    said = conflict.spoken(SITE_NAME)
    expect("Nothing was sent" in said, said)
    return said


# =========================================================================== #
# Properties, versions, Trash


@check(
    "Properties, versions, Trash (5.5, 5.6)",
    "20",
    "Properties on Pinned news go to the site",
    who=EDITOR,
    writes=True,
)
def _properties(ctx: Ctx) -> str:
    from quill.core.wordpress import site as wp

    api = ctx.api(EDITOR)
    row = find_post(ctx, EDITOR, "post", "Pinned news", ("publish",))
    item = wp.load_item(api, "post", row.id)
    ctx.later("put back Pinned news", lambda: wp.update_item(api, item))
    changed = _with(item, excerpt=f"{TAG} excerpt", sticky=not item.sticky)
    wp.update_item(api, changed)
    back = wp.load_item(api, "post", row.id)
    expect(back.excerpt.strip() == f"{TAG} excerpt", f"excerpt is {back.excerpt!r}")
    expect(back.sticky == (not item.sticky), "Keep at the top did not change")
    return "excerpt and Keep at the top changed and read back"


@check(
    "Properties, versions, Trash (5.5, 5.6)", "21", "Welcome has its 3 site revisions", who=EDITOR
)
def _revisions(ctx: Ctx) -> str:
    from quill.core.wordpress import site as wp

    row = find_post(ctx, EDITOR, "post", SEEDED_POSTS["welcome"], ("publish",))
    revisions = [r for r in wp.list_revisions(ctx.api(EDITOR), "post", row.id) if not r.autosave]
    expect(len(revisions) >= 3, f"{len(revisions)} revisions")
    return f"{len(revisions)} revisions, newest {revisions[0].date_gmt}"


@check(
    "Properties, versions, Trash (5.5, 5.6)",
    "23",
    "Move to Trash, listed, restored",
    who=EDITOR,
    writes=True,
)
def _trash(ctx: Ctx) -> str:
    from quill.core.wordpress import site as wp

    api = ctx.api(EDITOR)
    made = _new_post(ctx, EDITOR, "trash")
    gone = wp.trash_item(api, "post", made.id)
    expect(gone.status == "trash", f"status {gone.status}")
    listed = [r.id for r in wp.list_items(api, "post", statuses=("trash",), search=TAG)]
    expect(made.id in listed, "not under Trash in Open")
    back = wp.restore_from_trash(api, "post", made.id)
    expect(back.status == "draft", f"restored as {back.status}")
    return f"{made.id}: trashed, listed under Trash, restored as a draft"


# =========================================================================== #
# Checks


@check("Checks (7)", "24", "Check Before Publishing finds every seeded problem", who=EDITOR)
def _checks(ctx: Ctx) -> str:
    from quill.core.wordpress import checks
    from quill.core.wordpress import site as wp

    row = find_post(ctx, EDITOR, "post", "Things to check before publishing", ("draft",))
    item = wp.load_item(ctx.api(EDITOR), "post", row.id)
    found = checks.check_content(item.content, title=item.title)
    kinds = {f.kind for f in found}
    wanted = {
        "heading-1-in-body": "a heading 1",
        "heading-skips-level": "a skipped level",
        "link-vague-text": "click here",
        "link-text-is-address": "address as text",
        "link-new-tab-unsaid": "new tab not said",
        "colour-alone": "colour alone",
        "table-no-header": "no header row",
    }
    missing = [w for k, w in wanted.items() if k not in kinds]
    if not kinds & {"image-no-alt", "image-empty-alt"}:
        missing.append("no alternative text")
    expect(not missing, f"not found: {', '.join(missing)}; found {sorted(kinds)}")
    return f"{len(found)} findings: {checks.summary_line(found)}"


# =========================================================================== #
# Pictures


@check("Pictures (6)", "25", "Media Library rows and Find: banner", who=EDITOR)
def _library(ctx: Ctx) -> str:
    from quill.core.wordpress import site_media as sm

    api = ctx.api(EDITOR)
    items = list(sm.list_media(api))
    expect(items, "the library is empty")
    found = list(sm.list_media(api, search="banner"))
    expect(any("banner" in (m.title + m.filename).lower() for m in found), "banner not found")
    row = found[0].spoken()
    for part in ("image", "alt text", "uploaded"):
        expect(part in row, f"row reads: {row}")
    ctx.state["banner"] = found[0]
    return f"{len(items)} items; banner: {row}"


@check("Pictures (6)", "25", "Edit Alternative Text on wide-banner", who=EDITOR, writes=True)
def _alt_text(ctx: Ctx) -> str:
    from quill.core.wordpress import site_media as sm

    api = ctx.api(EDITOR)
    banner = ctx.state.get("banner") or next(iter(sm.list_media(api, search="banner")))
    ctx.later(
        "put back wide-banner's alt text",
        lambda: sm.update_media(api, banner.id, alt_text=banner.alt_text),
    )
    done = sm.update_media(api, banner.id, alt_text=f"{TAG} banner")
    expect(done.alt_text == f"{TAG} banner", f"alt text is {done.alt_text!r}")
    return "written and read back; put back afterwards"


@check("More from the API (9.15)", "sizes", "Picture sizes offered by name and width", who=EDITOR)
def _sizes(ctx: Ctx) -> str:
    from quill.core.wordpress import media_edit as me
    from quill.core.wordpress import site_media as sm

    photo = next(iter(sm.list_media(ctx.api(EDITOR), search="photo-volunteers")), None)
    expect(photo, "photo-volunteers not found")
    rows = me.dialog_sizes(photo)
    expect(rows and "wide" in rows[0][0], f"sizes: {rows}")
    return "; ".join(r[0] for r in rows)


@check(
    "More from the API (9.15)", "library alt", "Pictures with no alt text, library-wide", who=EDITOR
)
def _library_alt(ctx: Ctx) -> str:
    from quill.core.wordpress import media_edit as me

    names = {m.filename or m.title for m in me.pictures_without_alt(ctx.api(EDITOR))}
    expect(any("divider" in n for n in names), f"found {sorted(names)}")
    return f"{len(names)} pictures: {', '.join(sorted(names))}"


@check("Pictures (6)", "27", "Upload a picture", who=EDITOR, writes=True)
def _upload(ctx: Ctx) -> str:
    from quill.core.wordpress import site_media as sm

    api = ctx.api(EDITOR)
    made = sm.upload_media(
        api,
        "quill-live-test.png",
        tiny_png(),
        "image/png",
        title=ctx.title("picture"),
        alt_text=f"{TAG} picture",
    )
    ctx.later(f"delete media {made.id}", lambda: sm.delete_media(ctx.api(ADMIN), made.id))
    ctx.state["picture"] = made
    expect(made.width == 800 and made.height == 600, f"{made.width} by {made.height}")
    status, _h, _b = fetch(made.source_url)
    expect(status == 200, f"{made.source_url} answered {status}")
    return f"media {made.id}, {len(made.sizes)} sizes made"


@check(
    "More from the API (9.15)",
    "media edit",
    "Edit a Picture on the Site: rotate",
    who=EDITOR,
    writes=True,
)
def _edit_picture(ctx: Ctx) -> str:
    from quill.core.wordpress import media_edit as me
    from quill.core.wordpress import site_media as sm

    picture = ctx.state.get("picture")
    expect(picture, "no uploaded picture to edit")
    edits = me.offered(ctx.index.edit_modifiers(), picture)
    rotate = next((e for e in edits if e.needs == "rotate"), None)
    expect(rotate, f"offered: {[e.label for e in edits]}")
    edited = me.edit_on_site(ctx.api(EDITOR), picture, rotate)
    ctx.later(f"delete media {edited.id}", lambda: sm.delete_media(ctx.api(ADMIN), edited.id))
    expect(edited.id != picture.id, "the original was changed, not copied")
    ctx.state["edited"] = edited
    return f"'{rotate.label}': new item {edited.id}, {edited.width} by {edited.height}"


@check("Every route (9.16)", "45", "Regenerate Sizes after the edit", who=EDITOR, writes=True)
def _regenerate(ctx: Ctx) -> str:
    from quill.core.wordpress import media_pieces as mpc

    edited = ctx.state.get("edited")
    expect(edited, "no edited picture")
    again = mpc.regenerate_sizes(ctx.api(EDITOR), edited.id)
    expect(again.sizes, "no sizes after regenerating")
    return f"{len(again.sizes)} sizes: {', '.join(s[0] for s in again.sizes)}"


@check("Pictures (6)", "28", "Remove from Library", who=ADMIN, writes=True)
def _remove(ctx: Ctx) -> str:
    from quill.core.wordpress import site_media as sm

    api = ctx.api(ADMIN)
    made = sm.upload_media(
        api,
        "quill-live-test-remove.png",
        tiny_png(200, 200),
        "image/png",
        title=ctx.title("remove me"),
    )
    sm.delete_media(api, made.id)
    error = refused(lambda: api.get(f"wp/v2/media/{made.id}", context="edit"))
    expect(error.status == 404, f"after removing it answered {error.status}")
    return f"media {made.id} removed for good"


# =========================================================================== #
# Comments, categories and tags


@check(
    "Comments, categories and tags (9.8, 9.13)",
    "29",
    "Approve, reply, spam, many at once",
    who=ADMIN,
    writes=True,
)
def _comments(ctx: Ctx) -> str:
    from quill.core.wordpress import comments as cm

    api = ctx.api(ADMIN)
    waiting = [
        c for c in cm.list_comments(api, "hold") if c.post == ctx.state.get("welcome_id", c.post)
    ]
    expect(waiting, "no waiting comment on Welcome")
    target = waiting[0]
    ctx.later("put the waiting comment back", lambda: cm.set_status(api, target.id, "hold"))
    approved = cm.set_status(api, target.id, "approve")
    expect(approved.status == "approved", f"status {approved.status}")
    answer = cm.reply(api, approved, f"{TAG} reply")
    ctx.later(
        f"delete comment {answer.id}", lambda: api.delete(f"wp/v2/comments/{answer.id}", force=True)
    )
    spam = cm.set_status(api, answer.id, "spam")
    expect(spam.status == "spam", f"spam status {spam.status}")
    expect(cm.set_many(api, [answer.id], "hold") == 1, "Do with Marked did not count one")
    return f"approved {target.id}, replied {answer.id}, spam, then held as one of many"


@check(
    "Comments, categories and tags (9.8, 9.13)",
    "30",
    "Add, rename and delete a tag; merge",
    who=ADMIN,
    writes=True,
)
def _terms(ctx: Ctx) -> str:
    from quill.core.wordpress import site as wp

    api = ctx.api(ADMIN)
    tag = wp.create_term(api, "post_tag", f"{TAG} tag {ctx.stamp}")
    ctx.later(
        f"delete tag {tag.id}", lambda: _quiet(lambda: wp.delete_term(api, "post_tag", tag.id))
    )
    renamed = wp.update_term(api, _with(tag, name=f"{TAG} renamed {ctx.stamp}"))
    expect(renamed.name.startswith(f"{TAG} renamed"), f"renamed to {renamed.name}")
    source = wp.create_term(api, "category", f"{TAG} merge from {ctx.stamp}")
    target = wp.create_term(api, "category", f"{TAG} merge into {ctx.stamp}")
    ctx.later(
        f"delete category {source.id}",
        lambda: _quiet(lambda: wp.delete_term(api, "category", source.id)),
    )
    ctx.later(
        f"delete category {target.id}",
        lambda: _quiet(lambda: wp.delete_term(api, "category", target.id)),
    )
    post = _new_post(ctx, ADMIN, "merge")
    wp.update_item(api, _with(post, categories=[source.id]))
    moved = wp.merge_terms(api, "category", source.id, target.id)
    expect(moved == 1, f"{moved} posts moved")
    left = {t.id for t in wp.list_terms(api, "category", search=TAG)}
    expect(source.id not in left, "the merged category is still there")
    wp.delete_term(api, "post_tag", tag.id)
    return "tag added, renamed and deleted; 1 post merged and the empty category deleted"


def _quiet(call: Callable[[], object]) -> None:
    from quill.core.wordpress.api import WordPressApiError

    try:
        call()
    except WordPressApiError as exc:
        if exc.status != 404 and exc.wp_code not in ("rest_term_invalid", "rest_post_invalid_id"):
            raise


# =========================================================================== #
# Listen and watch, signed in


@check("Listen and watch (6.1a)", "36", "Play Media Here on the page's blocks", who=EDITOR)
def _play_here(ctx: Ctx) -> str:
    from quill.core.wordpress import site as wp

    row = find_post(ctx, EDITOR, "page", "Listen and Watch", ("publish",))
    item = wp.load_item(ctx.api(EDITOR), "page", row.id)
    return _play_media_here(item.content, "html") + " (raw blocks)"


# =========================================================================== #
# The site's own kinds


@check("The site's own kinds (5.2)", "38", "Open lists Events with Open Day", who=ADMIN)
def _kinds(ctx: Ctx) -> str:
    from quill.core.wordpress import site as wp

    kinds = wp.list_content_types(ctx.api(ADMIN))
    expect(("events", "Events") in kinds, f"kinds: {kinds}")
    rows = list(wp.list_items(ctx.api(ADMIN), "events"))
    expect(any(r.title == "Open Day" for r in rows), "no Open Day")
    return f"kinds: {', '.join(k[1] for k in kinds)}; Open Day listed"


@check(
    "The site's own kinds (5.2)",
    "38",
    "Open Day: change, send, Trash and restore",
    who=ADMIN,
    writes=True,
)
def _event_edit(ctx: Ctx) -> str:
    from quill.core.wordpress import site as wp

    api = ctx.api(ADMIN)
    row = next(r for r in wp.list_items(api, "events") if r.title == "Open Day")
    item = wp.load_item(api, "events", row.id)
    original = _with(item, kind="events")
    ctx.later("put back Open Day", lambda: wp.update_item(api, _with(original, status="publish")))
    edited = _with(item, content=item.content + f"\n<!-- {TAG} -->")
    try:
        wp.update_item(api, edited)  # the kind exactly as Open hands it on
    except Exception as exc:  # noqa: BLE001
        raise CheckFailed(
            f"sending the opened event failed (kind '{item.kind}'): {getattr(exc, 'plain', exc)}"
        ) from exc
    gone = wp.trash_item(api, "events", row.id)
    expect(gone.status == "trash", f"trashed as {gone.status}")
    back = wp.restore_from_trash(api, "events", row.id)
    expect(back.status == "draft", f"restored as {back.status}")
    return "sent, trashed and restored (put back as published)"


@check(
    "The site's own kinds (5.2)", "39", "Contributor still gets Posts and Pages", who=CONTRIBUTOR
)
def _contributor_kinds(ctx: Ctx) -> str:
    from quill.core.wordpress import site as wp

    kinds = wp.list_content_types(ctx.api(CONTRIBUTOR))
    expect(kinds[:2] == [("post", "Posts"), ("page", "Pages")], f"kinds: {kinds}")
    return ", ".join(k[1] for k in kinds)


# =========================================================================== #
# More from the API (9.15)


@check(
    "More from the API (9.15)",
    "notes",
    "Notes on blocks: add, reply, resolve",
    who=EDITOR,
    writes=True,
)
def _notes(ctx: Ctx) -> str:
    from quill.core.wordpress import block_notes as bn

    api = ctx.api(EDITOR)
    post = _new_post(ctx, EDITOR, "notes")
    note = bn.add_note(api, post.id, f"{TAG} note: tighten this")
    ctx.later(
        "delete the notes",
        lambda: [
            _quiet(lambda n=n: ctx.api(ADMIN).delete(f"wp/v2/comments/{n.id}", force=True))
            for n in bn.list_notes(ctx.api(ADMIN), post.id)
        ],
    )
    found = bn.threads(bn.list_notes(api, post.id))
    expect(len(found) == 1 and found[0].root.id == note.id, f"{len(found)} threads")
    bn.reply(api, post.id, found[0], f"{TAG} reply")
    bn.set_resolved(api, post.id, found[0], True)
    again = bn.threads(bn.list_notes(api, post.id))
    expect(again[0].resolved, "the thread is not resolved")
    expect(again[0].spoken_replies, "the reply is missing")
    return f"note {note.id}: replied and resolved"


def _introspect(login: str) -> Callable[[Ctx], str]:
    def run(ctx: Ctx) -> str:
        from quill.core.wordpress import site_features as sf

        found = sf.which_password(ctx.api(login))
        expect(found is not None, "the site did not say which password")
        return sf.password_sentence(SITE_NAME, found)

    return run


for _login in ROLES:
    check(
        "More from the API (9.15)",
        "introspect",
        f"Which application password, {_login}",
        who=_login,
    )(_introspect(_login))


@check("More from the API (9.15)", "custom fields", "Custom fields on Welcome", who=EDITOR)
def _custom_fields(ctx: Ctx) -> str:
    from quill.core.wordpress import custom_fields as cf

    api = ctx.api(EDITOR)
    welcome = ctx.state.get("welcome_id") or 0
    form = cf.build_form(cf.meta_schema(api, "post"), cf.site_values(api, "post", welcome), {})
    expect(form.fields, "no custom fields")
    return f"{len(form.fields)} fields, {form.left_alone} left alone"


@check(
    "More from the API (9.15)",
    "styles",
    "Style variations, each with its Palette Report",
    who=ADMIN,
)
def _variations(ctx: Ctx) -> str:
    from quill.core.wordpress import site_styles as ss

    api = ctx.api(ADMIN)
    theme = ss.active_theme(api)
    expect(theme.block_theme, f"{theme.name} is not a block theme")
    base = ss.theme_styles(api, theme.stylesheet)
    variations = ss.list_variations(api, theme.stylesheet)
    expect(variations, f"{theme.name} lists no variations")
    reports = [ss.report_summary(ss.variation_report(v, base)) for v in variations]
    ctx.state["theme"] = (theme, base)
    return f"{theme.name}: {len(variations)} variations; first: {variations[0].title}, {reports[0]}"


@check(
    "More from the API (9.15)", "Site Styles", "Site Styles: colours and sizes by name", who=ADMIN
)
def _site_styles(ctx: Ctx) -> str:
    from quill.core.wordpress import site_styles as ss

    api = ctx.api(ADMIN)
    theme, base = ctx.state.get("theme") or (ss.active_theme(api), None)
    base = base or ss.theme_styles(api, theme.stylesheet)
    expect(theme.styles_id, "no global-styles record")
    user = ss.load_user_styles(api, theme.styles_id)
    entries = ss.entries(base, user)
    colours = [e for e in entries if e.kind == "colour"]
    expect(colours, "no colours")
    background, text = ss.page_colours(base, user)
    row = ss.entry_row(colours[0], background, text)
    return f"{len(colours)} colours, {len(entries) - len(colours)} sizes; {row}"


@check(
    "More from the API (9.15)",
    "patterns",
    "Pattern Directory search, described in words",
    who=EDITOR,
)
def _pattern_directory(ctx: Ctx) -> str:
    from quill.core.wordpress import pattern_directory as pd

    found = pd.search(ctx.api(EDITOR), "contact", per_page=5)
    expect(found, "nothing found for 'contact'")
    said = pd.describe(found[0])
    expect(said.strip(), "no description")
    return f"{len(found)} patterns; {cell(said, 120)}"


@check(
    "More from the API (9.15)",
    "pattern categories",
    "Pattern categories for synced patterns",
    who=ADMIN,
)
def _pattern_categories(ctx: Ctx) -> str:
    from quill.core.wordpress import pattern_directory as pd

    cats = pd.load_categories(ctx.api(ADMIN))
    expect(cats.membership, "no synced patterns read (Event announcement is seeded)")
    return f"{len(cats.names)} categories, {len(cats.membership)} synced patterns read"


@check("More from the API (9.15)", "TEC", "The Events Calendar: venues and Coming Up", who=ADMIN)
def _tec(ctx: Ctx) -> str:
    from quill.core.wordpress import plugin_events as pe

    events = pe.coming_up(ctx.api(ADMIN))
    venues = pe.list_venues(ctx.api(ADMIN))
    return f"{len(events)} upcoming, {len(venues)} venues"


@check(
    "More from the API (9.15)", "TEC", "New Event as a draft, then changed", who=ADMIN, writes=True
)
def _tec_new(ctx: Ctx) -> str:
    from quill.core.wordpress import plugin_events as pe

    api = ctx.api(ADMIN)
    made = pe.create_event(api, ctx.title("event"), "2027-01-15 10:00:00", "2027-01-15 11:00:00")
    ctx.later(f"trash event {made.id}", lambda: api.delete(f"{pe.NAMESPACE}/events/{made.id}"))
    expect(made.status == "draft", f"status {made.status}")
    pe.update_event(api, made.id, "2027-01-15 12:00:00", "2027-01-15 13:00:00")
    back = pe.load_event(api, made.id)
    expect("12:00" in back.start, f"start is {back.start}")
    return f"event {made.id}: {back.when()}"


@check(
    "More from the API (9.15)", "WooCommerce", "Products in Properties, orders read only", who=ADMIN
)
def _woo(ctx: Ctx) -> str:
    from quill.core.wordpress import plugin_shop_seo as shop

    api = ctx.api(ADMIN)
    rows = api.get("wc/v3/products", per_page=5)
    orders = shop.recent_orders(api, per_page=5)
    if not rows:
        raise NotRun(f"no products on the site; {len(orders)} orders read")
    product = shop.load_product(api, int(rows[0]["id"]))
    ctx.state["product"] = product
    return f"{product.name}: {product.price}, {product.stock_words()}; {len(orders)} orders read"


@check(
    "More from the API (9.15)",
    "WooCommerce",
    "Light edit: price, then put back",
    who=ADMIN,
    writes=True,
)
def _woo_edit(ctx: Ctx) -> str:
    from quill.core.wordpress import plugin_shop_seo as shop

    api = ctx.api(ADMIN)
    product = ctx.state.get("product")
    if product is None:
        raise NotRun("no product to edit")
    ctx.later(
        "put back the product's price",
        lambda: shop.update_product(
            api,
            product.id,
            regular_price=product.regular_price,
            sale_price=product.sale_price,
            stock_quantity=product.stock_quantity,
        ),
    )
    price = shop.check_price("12.34", label="Regular price")
    done = shop.update_product(
        api,
        product.id,
        regular_price=price,
        sale_price=product.sale_price,
        stock_quantity=product.stock_quantity,
    )
    expect(done.regular_price == "12.34", f"price is {done.regular_price}")
    return "price changed and read back; put back afterwards"


@check(
    "More from the API (9.15)",
    "Yoast",
    "SEO title and description with lengths",
    who=ADMIN,
    writes=True,
)
def _yoast(ctx: Ctx) -> str:
    from quill.core.wordpress import plugin_shop_seo as shop

    api = ctx.api(ADMIN)
    post = _new_post(ctx, ADMIN, "SEO")
    fields = shop.seo_fields(shop.load_meta(api, "post", post.id))
    expect(len(fields) >= 2, f"SEO fields in edit mode: {fields}")
    shop.save_meta(api, "post", post.id, {"_yoast_wpseo_title": f"{TAG} SEO title"})
    back = dict((k, v) for k, _l, _n, v in shop.seo_fields(shop.load_meta(api, "post", post.id)))
    expect(back.get("_yoast_wpseo_title") == f"{TAG} SEO title", f"read back {back}")
    return shop.seo_facts(shop.load_meta(api, "post", post.id)).replace("\n", " ")


@check("More from the API (9.15)", "Abilities", "Abilities listed; a read-only one run", who=ADMIN)
def _abilities(ctx: Ctx) -> str:
    from quill.core.wordpress import abilities as ab

    api = ctx.api(ADMIN)
    found = ab.list_abilities(api)
    expect(found, "no abilities listed")
    safe = next((a for a in found if a.readonly and not a.input_schema.get("required")), None)
    if safe is None:
        raise NeedsJeff(f"{len(found)} abilities, none read-only without input to try")
    result = ab.run_ability(api, safe, {})
    return f"{len(found)} abilities; ran {safe.name}: {cell(ab.result_text(result), 80)}"


@check(
    "More from the API (9.15)", "Site Health", "Every Site Health test, one line each", who=ADMIN
)
def _health(ctx: Ctx) -> str:
    from quill.core.wordpress.site_health import health_lines, health_test_names

    lines = health_lines(ctx.api(ADMIN), ctx.index_raw)
    names = health_test_names(ctx.index_raw)
    expect(len(lines) >= len(names), f"{len(lines)} lines for {len(names)} tests")
    header = [line for line in lines if "authorization" in line.text.lower()]
    return (
        f"{len(lines)} lines; "
        + "; ".join(f"{line.status}: {line.text}" for line in lines[:6])[:400]
        + ("" if header else " (no authorization-header line)")
    )


@check(
    "More from the API (9.15)",
    "Site Health",
    "An editor hears it is for administrators",
    who=EDITOR,
)
def _health_editor(ctx: Ctx) -> str:
    from quill.core.wordpress.site_health import health_lines

    lines = health_lines(ctx.api(EDITOR), ctx.index_raw)
    expect(len(lines) == 1 and "administrator" in lines[0].text, [line.text for line in lines])
    return lines[0].text


# =========================================================================== #
# Every route (9.16)


@check("Every route (9.16)", "40", "Hear Where a Link Goes, and a typo", who=EDITOR)
def _url_details(ctx: Ctx) -> str:
    from quill.core.wordpress import link_targets as lt

    about = lt.read_target(ctx.api(EDITOR), site_url("about/"))
    expect(about.reachable and "About" in about.title, about.spoken())
    typo = lt.read_target(ctx.api(EDITOR), site_url("abuot-us-typo/"))
    expect(not typo.reachable, f"the typo reads: {typo.spoken()}")
    return f"{about.spoken()} Typo: {typo.spoken()}"


@check("Every route (9.16)", "41", "Fix Link Text uses the page's title", who=EDITOR)
def _fix_link(ctx: Ctx) -> str:
    from quill.core.wordpress import link_targets as lt

    text = (
        f'<!-- wp:paragraph --><p>Read <a href="{site_url("about/")}">click here</a>.</p>'
        "<!-- /wp:paragraph -->"
    )
    link = lt.links_in(text, "html")[0]
    target = lt.read_target(ctx.api(EDITOR), link.url)
    fixed = lt.fixed_text(text, link, target.title)
    expect(f">{target.title}</a>" in fixed, f"fixed: {fixed}")
    return f"'click here' became '{target.title}'"


@check("Every route (9.16)", "42", "Dead links named", who=EDITOR)
def _dead_links(ctx: Ctx) -> str:
    from quill.core.wordpress import link_targets as lt

    urls = [site_url("no-such-page/"), site_url("about/")]
    dead = lt.dead_links(ctx.api(EDITOR), urls)
    expect(len(dead) == 1 and "no-such-page" in dead[0].url, [d.url for d in dead])
    return lt.dead_link_sentence(dead, len(urls))


@check("Every route (9.16)", "43", "Insert Icon: labelled, decorative, never unnamed", who=EDITOR)
def _icons(ctx: Ctx) -> str:
    from quill.core.wordpress import icons

    found = icons.list_icons(ctx.api(EDITOR))
    expect(found, "no icons")
    icon = found[0]
    named = icons.icon_markup(icon, label="Telephone")
    plain = icons.icon_markup(icon, decorative=True)
    expect('aria-label="Telephone"' in named and 'role="img"' in named, named[:200])
    expect('aria-hidden="true"' in plain, plain[:200])
    try:
        icons.icon_markup(icon, label="  ")
    except icons.IconLabelError:
        return f"{len(found)} icons, first {icon.spoken()}; an empty label inserts nothing"
    raise CheckFailed("an empty label made an unnamed icon")


@check("Every route (9.16)", "44", "Upload a Large File, whole", who=EDITOR, writes=True)
def _pieces(ctx: Ctx) -> str:
    from quill.core.wordpress import site_media as sm

    content = tiny_wav(2.0)
    try:
        made = sm.upload_media(
            ctx.api(EDITOR),
            "quill-live-test-large.wav",
            content,
            "audio/wav",
            title=ctx.title("large"),
        )
    except Exception as exc:  # noqa: BLE001
        raise CheckFailed(f"the upload was refused: {getattr(exc, 'plain', exc)}") from exc
    ctx.later("delete the large upload", lambda: sm.delete_media(ctx.api(ADMIN), made.id))
    status, _h, body = fetch(made.source_url)
    expect(
        status == 200 and len(body) == len(content),
        f"the library file is {len(body)} bytes, {len(content)} were sent",
    )
    return f"{len(content)} bytes in one upload, whole file on the site"


@check(
    "Every route (9.16)", "46", "Previous Looks: change a colour, go back", who=ADMIN, writes=True
)
def _looks(ctx: Ctx) -> str:
    from quill.core.wordpress import looks_history as lh
    from quill.core.wordpress import site_styles as ss

    api = ctx.api(ADMIN)
    styles = lh.styles_id(api)
    expect(styles, "no global-styles record")
    theme = ss.active_theme(api)
    base = ss.theme_styles(api, theme.stylesheet)
    user = ss.load_user_styles(api, styles)
    ctx.later(
        "put back the site styles",
        lambda: ss.save_user_styles(
            api, styles, {"settings": user["settings"], "styles": user["styles"]}
        ),
    )
    colour = next(e for e in ss.entries(base, user) if e.kind == "colour")
    before = len(lh.list_looks(api, styles))
    ss.save_user_styles(
        api,
        styles,
        {"settings": ss.changed_settings(base, user, colour, "#123456"), "styles": user["styles"]},
    )
    looks = lh.list_looks(api, styles)
    expect(len(looks) > before, f"{before} looks before, {len(looks)} after")
    want = json.dumps(user["settings"], sort_keys=True)
    earlier = next(
        (lk for lk in looks if json.dumps(lk.settings, sort_keys=True) == want),
        looks[1] if len(looks) > 1 else None,
    )
    expect(earlier, "the earlier look is not listed")
    lh.restore_look(api, styles, earlier)
    now = ss.load_user_styles(api, styles)
    expect(json.dumps(now["settings"], sort_keys=True) == want, "Go Back did not restore it")
    return f"{len(looks)} looks; {earlier.spoken()} restored"


@check("Every route (9.16)", "47", "Menu History: menus and Navigation revisions read", who=ADMIN)
def _menus(ctx: Ctx) -> str:
    from quill.core.wordpress import looks_history as lh
    from quill.core.wordpress import navigation as nav

    menus = nav.load_menus(ctx.api(ADMIN))
    blocks = [m for m in menus if m.source == "navigation"]
    versions = sum(len(lh.navigation_versions(ctx.api(ADMIN), m)) for m in blocks)
    return f"{len(menus)} menus ({len(blocks)} Navigation blocks), {versions} revisions"


@check("Every route (9.16)", "48", "Space Used in words; an editor cannot", who=ADMIN)
def _space(ctx: Ctx) -> str:
    from quill.core.wordpress import routes, site_space
    from quill.core.wordpress.site import load_account

    lines = site_space.read_space(ctx.api(ADMIN)).lines()
    expect(any(line.startswith("Uploads:") for line in lines), lines)
    said = ""
    if EDITOR in ctx.apis:
        editor = ctx.accounts.get(EDITOR) or load_account(ctx.api(EDITOR))
        said = routes.unavailable("directory_sizes", ctx.index, editor, SITE_NAME)
        expect(said, "the editor would be offered Space Used")
    return " ".join(lines) + (f" Editor: {said}" if said else "")


@check("Every route (9.16)", "49", "Download a Copy of the Site's Design", who=ADMIN)
def _export(ctx: Ctx) -> str:
    from quill.core.wordpress import site_space

    body, name = site_space.export_design(ctx.api(ADMIN))
    names = zipfile.ZipFile(io.BytesIO(body)).namelist()
    expect(any(n.endswith(("theme.json", "style.css")) for n in names), names[:10])
    return f"{name}, {len(body)} bytes, {len(names)} files (kept in memory, not saved)"


@check("Every route (9.16)", "50", "Send This Document to WordPress", who=EDITOR, writes=True)
def _send_document(ctx: Ctx) -> str:
    from quill.core.wordpress import cross_site as cs
    from quill.core.wordpress import fences
    from quill.core.wordpress import site as wp

    text = f"# {ctx.title('sent document')}\n\nA paragraph from the regression harness.\n"
    title, body = cs.title_and_body(text, "markdown", "Untitled")
    expect(title == ctx.title("sent document"), f"title is {title}")
    made = _new_post(ctx, EDITOR, "x", content=fences.markdown_to_blocks(body))
    made = wp.update_item(ctx.api(EDITOR), _with(made, title=title))
    expect(made.status == "draft" and "wp:paragraph" in made.content, made.content[:120])
    raise NeedsJeff(
        f"draft {made.id} titled from the heading; the picture beside the file needs the command"
    )


@check("Every route (9.16)", "51", "Duplicate makes a '(copy)' draft", who=ADMIN, writes=True)
def _duplicate(ctx: Ctx) -> str:
    from quill.core.wordpress import cross_site as cs
    from quill.core.wordpress import site as wp

    api = ctx.api(ADMIN)
    welcome = wp.load_item(api, "post", ctx.state.get("welcome_id") or 0)
    copy = cs.as_new_draft(welcome, same_site=True)
    expect(copy.title.endswith("(copy)") and copy.status == "draft" and not copy.id, copy.title)
    made = wp.create_item(api, _with(copy, title=ctx.title(copy.title)))
    ctx.later(f"trash post {made.id}", lambda: wp.trash_item(api, "post", made.id))
    expect(made.categories == welcome.categories, "categories not kept")
    return f"'{copy.title}' as draft {made.id} (sent with the live-test tag)"


@check("Every route (9.16)", "52", "Download My Writing, then up to date", who=EDITOR)
def _archive(ctx: Ctx) -> str:
    from quill.core.wordpress import writing_archive as wa

    folder = ctx.scratch / "archive"
    first = wa.download_writing(ctx.api(EDITOR), folder, SITE_URL)
    expect(first.saved and (folder / "index.md").is_file(), f"saved {first.saved}")
    second = wa.download_writing(ctx.api(EDITOR), folder, SITE_URL)
    expect(second.saved == 0, f"the second run saved {second.saved} again")
    return (
        f"{first.saved} files, {first.pictures} pictures; again: "
        f"{wa.archive_sentence(SITE_NAME, folder, second)}"
    )


@check("Every route (9.16)", "53", "Send a Folder as Drafts", who=EDITOR, writes=True)
def _folder(ctx: Ctx) -> str:
    from quill.core.wordpress import site as wp
    from quill.core.wordpress import writing_archive as wa

    folder = ctx.scratch / "folder"
    folder.mkdir(parents=True, exist_ok=True)
    for n in (1, 2, 3):
        link = " See [click here](https://example.org/)." if n == 2 else ""
        (folder / f"draft-{n}.md").write_text(
            f"# {ctx.title(f'folder {n}')}\n\nParagraph {n}.{link}\n", encoding="utf-8"
        )
    files = wa.read_folder(folder, site_name=SITE_NAME)
    flagged = [f for f in files if f.findings]
    expect(len(files) == 3 and len(flagged) == 1, f"{len(files)} files, {len(flagged)} flagged")
    sentence = wa.folder_sentence(files, SITE_NAME)
    made, failed = wa.send_folder(ctx.api(EDITOR), files)
    for item in made:
        ctx.later(
            f"trash post {item.id}", lambda i=item: wp.trash_item(ctx.api(EDITOR), i.kind, i.id)
        )
    expect(len(made) == 3 and not failed, f"{len(made)} sent, failed {failed}")
    expect(all(i.status == "draft" for i in made), "not all drafts")
    return f"{sentence} Three drafts arrived."


@check("Every route (9.16)", "54", "Coming Up lists the scheduled post", who=ADMIN)
def _coming_up(ctx: Ctx) -> str:
    from quill.core.wordpress import across_sites as xs

    items, failed = xs.coming_up([("test", SITE_NAME, lambda: ctx.api(ADMIN))])
    expect(any(i.title == "Scheduled for next month" for i in items), [i.title for i in items])
    return xs.coming_up_sentence(items, failed, 1)


@check(
    "Every route (9.16)",
    "54",
    "What Changed lists a new comment once",
    who=CONTRIBUTOR,
    writes=True,
)
def _what_changed(ctx: Ctx) -> str:
    from quill.core.wordpress import across_sites as xs

    looked = xs.LastLooked(ctx.scratch / "looked")
    sites = [("test", SITE_NAME, lambda: ctx.api(ADMIN))]
    looked.mark(["test"], xs.utc_now() - dt.timedelta(seconds=5))
    raw = ctx.api(CONTRIBUTOR).post(
        "wp/v2/comments", {"post": ctx.state.get("welcome_id"), "content": f"{TAG} comment"}
    )
    ctx.later(
        f"delete comment {raw.get('id')}",
        lambda: ctx.api(ADMIN).delete(f"wp/v2/comments/{raw.get('id')}", force=True),
    )
    time.sleep(1.2)
    changes, _failed = xs.what_changed(sites, looked, xs.utc_now())
    comments = [c for c in changes if c.kind == "comment"]
    expect(comments, f"no comment change: {[c.spoken() for c in changes]}")
    looked.mark(["test"], xs.utc_now())
    again, _f = xs.what_changed(sites, looked, xs.utc_now())
    expect(not [c for c in again if c.kind == "comment"], "the comment is listed again")
    return f"{comments[0].spoken()}; then nothing new"


# =========================================================================== #
# Forms (17a)


FORM_BFL = """bfl 1
form "{title}"
  @description "Made by the QUILL live regression harness, and removed after it."

page #p1 "Page 1"
  text #name "Your name"
    @required
  email #email "Your email"
    @required
    @autocomplete "email"
  textarea #message "Your message"
  radio #reply "Best way to reply"
    + email|Email
    + phone|Phone
  phone #phone "Phone number"
    @autocomplete "tel"
    @when #reply is "phone"
"""


@check("Forms (17a)", "63", "Publish Form as Live, then Update", who=ADMIN, writes=True)
def _publish_form(ctx: Ctx) -> str:
    from quill.core.forms import bfl_document as bd

    fs = forms_site()
    api = ctx.api(ADMIN)
    expect(forms_supported(api), "the site does not offer the forms plugin")
    source = FORM_BFL.format(title=ctx.title("Ask us anything"))
    model = bd.read_form(source)
    made = fs.create_form(api, fs.publish_body(model, source, status="active"))
    namespace = forms_namespace(api)
    ctx.later(f"delete form {made.id}", lambda: api.delete(f"{namespace}/forms/{made.id}"))
    expect(made.id and made.live, f"form {made.id}, status {made.status}")
    again = fs.update_form(
        api, made.id, fs.publish_body(model, source, status="active", existing=made)
    )
    expect(again.id == made.id, "Publish again made a second form")
    site_copy = fs.get_form(api, made.id)
    labels = site_copy.question_labels()
    expect("Phone number" in labels.values(), f"the site's copy has {labels}")
    ctx.state["form"] = (site_copy, model, source)
    return f"Published {made.title}, form {made.id}, live; updated in place; 5 questions kept"


@check(
    "Forms (17a)", "64", "A change on the site is seen before publishing", who=ADMIN, writes=True
)
def _form_changed(ctx: Ctx) -> str:
    fs = forms_site()
    api = ctx.api(ADMIN)
    form, model, source = ctx.state.get("form") or (None, None, None)
    expect(form, "no published form")
    time.sleep(1.2)
    body = fs.publish_body(model, source, status="active", existing=form)
    body["title"] = form.title + " (changed on the site)"
    fs.update_form(api, form.id, body)
    now = fs.get_form(api, form.id)
    expect(
        now.updated_at and now.updated_at != form.updated_at,
        f"updated_at {form.updated_at!r} -> {now.updated_at!r}",
    )
    return f"the site's copy changed at {now.updated_at}; the title is new"


@check(
    "Forms (17a)", "65", "Insert Form Into Page: the page shows the form", who=ADMIN, writes=True
)
def _form_page(ctx: Ctx) -> str:
    fs = forms_site()
    api = ctx.api(ADMIN)
    form, _m, _s = ctx.state.get("form") or (None, None, None)
    expect(form, "no published form")
    text, what = with_prefix(fs.placement, form.id, "html", prefix=forms_prefix(api))
    content = f"<!-- wp:paragraph --><p>{TAG} form page.</p><!-- /wp:paragraph -->{text}"
    page = _new_post(ctx, ADMIN, "form page", kind="page", status="publish", content=content)
    showing = fs.pages_showing(api, form.id)
    expect(any(link == page.link for _t, link, _s in showing), f"pages showing it: {showing}")
    status, _h, html = fetch(page.link)
    shown = html.decode("utf-8", "replace")
    expect(status == 200 and "<form" in shown, f"{page.link}: {status}, no <form>")
    expect("Your name" in shown, "the page shows the form without its questions")
    return f"{what} placed; {page.link} shows the form with its questions"


@check(
    "Forms (17a)",
    "66",
    "Responses: two sent, listed newest first, exported, deleted",
    who=ADMIN,
    writes=True,
)
def _responses(ctx: Ctx) -> str:
    from quill.core.forms import responses as rs

    fs = forms_site()
    api = ctx.api(ADMIN)
    form, _m, _s = ctx.state.get("form") or (None, None, None)
    expect(form, "no published form")
    namespace = forms_namespace(api)
    for n in (1, 2):
        answers = {
            "name": f"{TAG} {n}",
            "email": f"quill-live-{n}@example.invalid",
            "message": f"{TAG} message {n}",
            "reply": "email",
        }
        try:
            ctx.anon.post(f"{namespace}/submit/{form.id}", {"fields": answers, **answers})
        except Exception as exc:  # noqa: BLE001
            raise NeedsJeff(
                f"the submit route refused a scripted answer "
                f"({getattr(exc, 'plain', exc)}); send two from the page"
            ) from exc
        time.sleep(1.1)
    got = fs.list_responses(api, form.id)
    ctx.later("delete the responses", lambda: fs.delete_responses(api, [r.id for r in got]))
    expect(len(got) >= 2, f"{len(got)} responses")
    expect(got[0].created_at >= got[-1].created_at, "not newest first")
    labels = form.question_labels()
    rows = rs.list_rows(got, labels, form.title)
    csv = rs.csv_text(got, labels)
    expect("Your name" in csv.splitlines()[0], f"CSV header: {csv.splitlines()[0]}")
    expect(rs.find(got, "message 1"), "Find did not find 'message 1'")
    gone = fs.delete_responses(api, [got[-1].id])
    expect(gone == 1, f"{gone} deleted")
    return f"{len(got)} responses; first row: {cell(rows[0].text, 90)}"


# =========================================================================== #
# Clean-up and the record


def run_cleanups(ctx: Ctx) -> None:
    done, failed = 0, []
    while ctx.cleanups:
        what, undo = ctx.cleanups.pop()
        try:
            undo()
            done += 1
        except Exception as exc:  # noqa: BLE001 - keep going: the rest still need putting back
            failed.append(f"{what}: {getattr(exc, 'plain', exc)}")
    if done or failed:
        ctx.results.add(
            "Clean-up",
            "-",
            "Put back what the run changed",
            FAIL if failed else PASS,
            ctx.mask("; ".join(failed) if failed else f"{done} steps"),
            "quilladmin",
        )


def sweep(ctx: Ctx) -> None:
    """What the run left behind, outside the Trash: there should be nothing."""
    if ADMIN not in ctx.apis or ctx.dry_run:
        return
    from quill.core.wordpress import site as wp
    from quill.core.wordpress import site_media as sm

    api = ctx.api(ADMIN)
    left: list[str] = []
    for kind in ("post", "page"):
        left += [f"{kind} {r.id}" for r in wp.list_items(api, kind, search=TAG) if TAG in r.title]
    left += [f"media {m.id}" for m in sm.list_media(api, search=TAG) if TAG in m.title]
    for taxonomy in ("category", "post_tag"):
        left += [f"{taxonomy} {t.id}" for t in wp.list_terms(api, taxonomy, search=TAG)]
    ctx.results.add(
        "Clean-up",
        "-",
        f"Nothing titled '{TAG}' left outside the Trash",
        FAIL if left else PASS,
        ", ".join(left) or "none",
        ADMIN,
    )


def build_meta(ctx: Ctx, mode: str) -> dict[str, str]:
    def git(*args: str) -> str:
        try:
            return subprocess.run(
                ["git", *args], cwd=ROOT, capture_output=True, text=True, check=True
            ).stdout.strip()
        except (OSError, subprocess.CalledProcessError):
            return "unknown"

    version = ctx.state.get("wp_version", "")
    namespaces = set(ctx.index.namespaces) if ctx.index else set()
    plugins = _plugin_versions(ctx, namespaces)
    return {
        "Date": f"{ctx.stamp} UTC",
        "Build": f"{git('rev-parse', '--short', 'HEAD')} "
        f"({git('rev-parse', '--abbrev-ref', 'HEAD')})",
        "Mode": mode,
        "Site": f"{SITE_NAME} ({SITE_URL}), WordPress {version or 'unknown'}",
        "Plugins": plugins,
    }


def _plugin_versions(ctx: Ctx, namespaces: set[str]) -> str:
    known = {
        "wc/v3": "WooCommerce",
        "yoast/v1": "Yoast SEO",
        "tribe/events/v1": "The Events Calendar",
        "baf/v1": "BITS Accessible Forms",
        "qaf/v1": "QUILL Accessible Forms",
        "wp-abilities/v1": "Abilities",
    }
    versions: dict[str, str] = {}
    if ADMIN in ctx.apis:
        try:
            for raw in ctx.api(ADMIN).get("wp/v2/plugins", context="edit"):
                versions[str(raw.get("name", ""))] = str(raw.get("version", ""))
        except Exception:  # noqa: BLE001 - the versions are a nicety
            pass
    try:
        _s, _h, body = fetch(SITE_URL + "/")
        page = body.decode("utf-8", "replace")
        for name, rx in (
            ("WooCommerce", r'content="WooCommerce ([\d.]+)"'),
            ("Yoast SEO", r"Yoast SEO plugin v([\d.]+)"),
        ):
            if (m := re.search(rx, page)) and name not in versions:
                versions[name] = m.group(1)
    except (OSError, URLError):
        pass
    out = []
    for namespace, name in known.items():
        if namespace in namespaces:
            version = next((v for k, v in versions.items() if k.startswith(name)), "")
            out.append(f"{name} {version or '(version not shown)'} (`{namespace}`)")
    return "; ".join(out)


def write_doc(ctx: Ctx, meta: Mapping[str, str], *, render: bool) -> None:
    text = DOC.read_text(encoding="utf-8")
    DOC.write_bytes(replace_section(text, render_section(ctx.results, meta)).encode("utf-8"))
    print(f"Wrote the Live run section of {DOC.relative_to(ROOT)}.")
    pandoc = shutil.which("pandoc")
    if not render:
        return
    if pandoc is None:
        print("pandoc is not on the PATH; render the .html and .epub before committing.")
        return
    for target, fmt in ((".html", "html5"), (".epub", "epub3")):
        args = [pandoc, str(DOC), "-f", "gfm", "-t", fmt]
        if fmt == "html5":
            args.append("-s")
        subprocess.run([*args, "-o", str(DOC.with_suffix(target))], check=True, cwd=ROOT)
    print("Rendered the HTML and EPUB.")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--public", action="store_true", help="only what needs no sign-in")
    parser.add_argument(
        "--dry-run", action="store_true", help="sign in, but write nothing to the site"
    )
    parser.add_argument("--no-doc", action="store_true", help="do not write the Live run section")
    parser.add_argument("--no-render", action="store_true", help="do not run pandoc afterwards")
    parser.add_argument("--verbose", action="store_true", help="masked tracebacks for failures")
    args = parser.parse_args(argv)
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    ctx = Ctx(args)
    try:
        mode = "without signing in (`--public`)"
        if not args.public:
            passwords = load_passwords(ROLES)
            for login in passwords.missing:
                print(
                    f"{login}: no application password found (Credential Manager, "
                    f"QUILL_LIVE_ACCOUNTS, {env_name(login)}); its checks are not run."
                )
            print("quill-subscriber: sign-in password only; the harness does not use it.")
            from quill.core.wordpress.api import SiteAddress, SiteAuth, WordPressApi

            for login, secret in passwords.found.items():
                ctx.secrets += secret_forms(login, secret)
                ctx.apis[login] = WordPressApi(
                    SiteAddress(SITE_URL),
                    SiteAuth("app_password", login, secret),
                    site_name=SITE_NAME,
                )
            del passwords
            signed = ", ".join(ctx.apis) or "nobody (no passwords found)"
            mode = f"{'dry run, ' if args.dry_run else ''}signed in as {signed}"
        for item in CHECKS:
            if args.public and item.who:
                continue
            row = run_check(ctx, item)
            if row.outcome == FAIL or args.verbose:
                print(f"[{row.outcome}] {row.area} {row.ref} {row.name}: {row.detail}")
            if item.fn is _index and row.outcome != PASS:
                print("The REST index could not be read; nothing else can run.")
                break
        if not args.public:
            for area, ref, name, why in HUMAN:
                ctx.results.add(area, ref, name, NEEDS_JEFF, why, "-")
    finally:
        run_cleanups(ctx)
        try:
            sweep(ctx)
        except Exception as exc:  # noqa: BLE001
            ctx.results.add("Clean-up", "-", "Sweep", FAIL, ctx.mask(exc), ADMIN)
        shutil.rmtree(ctx.scratch, ignore_errors=True)
    counts = ctx.results.counts()
    print(", ".join(f"{counts[o]} {o}" for o in OUTCOMES))
    if not args.no_doc:
        write_doc(ctx, build_meta(ctx, mode), render=not args.no_render)
    return 1 if counts[FAIL] else 0


if __name__ == "__main__":
    raise SystemExit(main())
