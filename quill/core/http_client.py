"""The one User-Agent every QUILL family app sends.

Every podcast host, radio directory, weather service and stream server QUILL
talks to sees the same honest shape: ``<product>/<version> (+<project site>)``,
and podcast requests say what they are as well:
``QUILL Cast/2.0.0 (podcast app; +https://www.quillforall.org)``.
The product is whichever app is running -- QUILL, QUILL Cast, Quill Radio,
Quill Weather -- because each standalone app calls :func:`set_product_identity`
once at startup, so a host owner reading their logs sees the app and release
that actually asked (quill-radio #6). It never pretends to be a browser.

Why one module and not a constant per client. About forty modules used to
carry their own copy, all pointing at the GitHub repository, and that cost
real listeners: CBC's servers quietly stalled that User-Agent, so every CBC
podcast timed out in Cast while working in a browser (check.md bug 1,
2026-10-04). A copy per module meant the fix had to
be made forty times; now it is made here.

What CBC actually does turned out to be broader than "GitHub", and it is why
podcast requests carry a role (:func:`podcast_user_agent`). Probed against
three CBC feeds the same afternoon: every User-Agent of the crawler shape
``Name/1.0 (+https://some.site)`` stalled until the timeout -- the project
site, ``Windows;``, ``QuillVille;`` and ``Community Access;`` in the brackets
all stalled -- while the same string with ``podcast app;`` in the brackets was
answered in half a second, even with the GitHub address in it. So a podcast
request says it is a podcast app, which is simply true, and a host that lets
podcast apps through lets Cast through.

Read at request time (:func:`user_agent` is a call, not a constant) so a
module imported before the app set its identity still sends the right name.

wx-free, strict-typed.
"""

from __future__ import annotations

from quill import __version__

#: The project's own website. Not the source repository: some hosts treat a
#: User-Agent that mentions a code-hosting site as a scraper and stall it.
PROJECT_URL = "https://www.quillforall.org"

# Module-global identity. Defaults identify QUILL itself; each standalone app
# overrides these once, at startup, via set_product_identity.
_DEFAULT_NAME = "QUILL"
_product_name = _DEFAULT_NAME
_product_version = __version__


def set_product_identity(name: str, version: str) -> None:
    """Override the product name/version reported in the User-Agent.

    Each standalone app calls this at startup with its own title and version
    so its requests are not misreported as the embedded
    :data:`quill.__version__`. Blank arguments are ignored, so a caller can
    override just one field.
    """
    global _product_name, _product_version
    if name.strip():
        _product_name = name.strip()
    if version.strip():
        _product_version = version.strip()


def user_agent(role: str = "") -> str:
    """The User-Agent for every outbound request: ``<product>/<version> (+site)``.

    *role*, when given, goes in front of the site: ``(podcast app; +site)``.
    """
    detail = f"{role}; +{PROJECT_URL}" if role else f"+{PROJECT_URL}"
    return f"{_product_name}/{_product_version} ({detail})"


#: What a podcast request says it is. See the module docstring for why.
PODCAST_ROLE = "podcast app"


def podcast_user_agent() -> str:
    """The User-Agent for feeds, episodes, chapters, transcripts and directories."""
    return user_agent(PODCAST_ROLE)
