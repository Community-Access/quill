"""Site Health > Information and Site Health > Security (complete.md 10B.3).

**Information.** WordPress's Site Health screen has two tabs. Its Status tab
is a set of tests, and each test is a REST route under ``wp-site-health/v1``
(the Site Health node runs them). Its **Info** tab -- the server, PHP, the
database, the constants, everything a host asks for -- has **no REST route**.
So this list says what the REST API does cover (the tests, by name, and the
directory sizes, read here) and gives one row that opens Tools > Site Health
> Info in wp-admin, where "Copy site info to clipboard" gives a host the
whole report. Nothing here pretends to be the Info tab.

**Security.** XML-RPC (``xmlrpc.php``) is the older remote interface that
REST replaced. QUILL **deliberately never uses it**: it accepts a password
per call, it lets one request try hundreds of passwords (``system.multicall``),
it carries pingbacks that are used to aim traffic at other sites, and every
job QUILL does has a REST route. :func:`xmlrpc_check` asks the site's own
``xmlrpc.php`` for its method list, unsigned (no password is ever sent), and
says whether it still answers. It never tries a sign-in, so whether a plugin
has turned off only XML-RPC sign-in cannot be told and is said so.

Wx-free; requests go through the site's own client and its one door
(:func:`quill.core.wordpress.api.send_to_site`).
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any
from urllib.error import HTTPError, URLError
from urllib.request import Request

from quill.core.wordpress import api as wpapi
from quill.core.wordpress.api import WordPressApiError
from quill.core.wordpress.site_health import FALLBACK_TESTS, TEST_NAMES
from quill.core.wordpress.site_space import read_space
from quill.core.wordpress.workbench_no_rest import ADMIN_SCREENS, admin_link
from quill.core.wordpress.workbench_rows import WbRow

if TYPE_CHECKING:
    from quill.core.wordpress.api import WordPressApi
    from quill.core.wordpress.workbench_load import SiteContext

__all__ = [
    "XMLRPC_DISPOSITION",
    "XmlRpcState",
    "info_rows",
    "security_rows",
    "xmlrpc_check",
]

XMLRPC_DISPOSITION = (
    "QUILL never uses XML-RPC: every job it does has a REST route, and XML-RPC takes a "
    "password on every call, lets one request try many passwords, and carries pingbacks "
    "that can be aimed at other sites."
)

_LIST_METHODS = (
    b'<?xml version="1.0"?><methodCall><methodName>system.listMethods</methodName>'
    b"<params></params></methodCall>"
)
_METHOD = re.compile(rb"<string>([A-Za-z0-9_.]+)</string>")
_SIGN_IN_METHODS = ("wp.getUsersBlogs", "wp.getProfile", "metaWeblog.newPost")


class XmlRpcState:
    """What :func:`xmlrpc_check` found: ``answers``, ``blocked`` or ``unknown``."""

    def __init__(self, state: str, methods: tuple[str, ...] = (), said: str = "") -> None:
        self.state = state
        self.methods = methods
        self.said = said

    @property
    def sentence(self) -> str:
        if self.state == "answers":
            count = len(self.methods)
            more = []
            if "pingback.ping" in self.methods:
                more.append("pingbacks")
            if any(m in self.methods for m in _SIGN_IN_METHODS):
                more.append("methods that take a password")
            listed = f", including {' and '.join(more)}" if more else ""
            return (
                f"XML-RPC is on: xmlrpc.php answers and lists {count} methods{listed}. "
                "If nothing you use needs it (the Jetpack app and some old phone apps do), "
                "turn it off with a security plugin or at the web server. Whether a plugin "
                "has turned off only its sign-in cannot be told without trying a password, "
                "which QUILL never does."
            )
        if self.state == "blocked":
            return (
                f"XML-RPC is off: xmlrpc.php does not answer ({self.said}). Nothing in QUILL "
                "needs it."
            )
        return f"XML-RPC: QUILL could not tell whether xmlrpc.php answers ({self.said})."


def xmlrpc_check(api: WordPressApi) -> XmlRpcState:
    """Ask ``xmlrpc.php`` for its method list, unsigned; never a sign-in."""
    if api.address.is_wpcom:
        return XmlRpcState("unknown", said="WordPress.com runs XML-RPC for its own apps")
    url = f"{api.address.site_url.rstrip('/')}/xmlrpc.php"
    request = Request(
        url,
        data=_LIST_METHODS,
        headers={"Content-Type": "text/xml", "Accept": "text/xml"},
        method="POST",
    )
    try:
        with api._opener(request, timeout=api.timeout, context=wpapi._context(url)) as response:
            body = response.read(256 * 1024)
    except HTTPError as exc:
        if exc.code in (401, 403, 404, 405, 410, 444):
            return XmlRpcState("blocked", said=f"the server answers {exc.code}")
        return XmlRpcState("unknown", said=f"the server answered {exc.code}")
    except (URLError, TimeoutError, OSError) as exc:
        return XmlRpcState("unknown", said=str(getattr(exc, "reason", "") or exc) or "no answer")
    if b"<methodResponse" not in body:
        return XmlRpcState("blocked", said="the answer is not XML-RPC")
    methods = tuple(m.decode("ascii") for m in _METHOD.findall(body))
    if b"<fault>" in body and not methods:
        return XmlRpcState("blocked", said="it answers every call with an error")
    return XmlRpcState("answers", methods)


def _row(
    ctx: SiteContext,
    key: str,
    test: str,
    status: str,
    says: str,
    *,
    kind: str = "problem",
    link: str = "",
    raw: dict[str, Any] | None = None,
) -> WbRow:
    words = {"good": "Good", "recommended": "Should be improved", "critical": "Critical"}
    return WbRow(
        kind,
        ctx.name,
        key,
        {
            "test": test,
            "problem": test,
            "status": words.get(status, "Information"),
            "says": says,
            "site": ctx.name,
        },
        says,
        link=link,
        status=status,
        raw=dict(raw or {}),
    )


def info_rows(ctx: SiteContext) -> list[WbRow]:
    """What REST covers of Site Health's Info tab, and the row that opens the rest."""
    screen = ADMIN_SCREENS["site_health_info"]
    link = admin_link(ctx.url, "site_health_info")
    where = " Enter opens it in your browser." if link else ""
    rows = [
        _row(
            ctx,
            "info-tab",
            "Server, database and constants",
            "info",
            f"{screen.why} {screen.name} in wp-admin has it, and its Copy Site Info to "
            f"Clipboard button gives your host the whole report.{where}",
            kind="dashboard",
            link=link,
        )
    ]
    routes = ctx.info.routes if ctx.info is not None else ()
    tests = [
        r.rsplit("/", 1)[-1] for r in routes if r.startswith("/wp-site-health/v1/tests/")
    ] or list(FALLBACK_TESTS)
    named = ", ".join(TEST_NAMES.get(t, t.replace("-", " ")) for t in tests)
    rows.append(
        _row(
            ctx,
            "tests",
            "Tests on REST",
            "info",
            f"The tests this site offers over REST, run in the Site Health node: {named}.",
        )
    )
    try:
        space = read_space(ctx.api)
    except WordPressApiError as exc:
        why = (
            "only an administrator can read them"
            if exc.status in (401, 403)
            else exc.plain or "the site did not say"
        )
        rows.append(_row(ctx, "sizes", "Directory sizes", "info", f"Directory sizes: {why}."))
        return rows
    for index, line in enumerate(space.lines()):
        name, _sep, value = line.partition(": ")
        rows.append(_row(ctx, f"size:{index}", name, "info", line, raw={"value": value}))
    return rows


def security_rows(ctx: SiteContext) -> list[WbRow]:
    """The XML-RPC check, with QUILL's own disposition beside it."""
    found = xmlrpc_check(ctx.api)
    status = {"answers": "recommended", "blocked": "good"}.get(found.state, "info")
    return [
        _row(
            ctx,
            "xmlrpc",
            "XML-RPC",
            status,
            found.sentence,
            raw={"state": found.state, "methods": list(found.methods)},
        ),
        _row(ctx, "xmlrpc-quill", "QUILL and XML-RPC", "info", XMLRPC_DISPOSITION),
    ]
