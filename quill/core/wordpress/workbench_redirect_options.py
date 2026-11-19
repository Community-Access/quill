"""Redirection's own options, read and changed from Redirects > Redirect Options (complete.md 2.3).

The Redirection plugin keeps its options behind ``redirection/v1/setting``:
``GET`` answers ``{"settings": {...}, ...}`` and ``POST`` takes the options to
change and answers the same shape. That comes from the plugin's own REST
documentation; the route is **not** in the routes recorded from the test
site, so everything here is defensive:

- the route is used only where the site's REST index lists it (or, with no
  index to go by, where asking does not answer "no route");
- only the options in :data:`KNOWN` are shown, and only when the answer holds
  them with a value QUILL understands; every other option is counted and left
  in Tools > Redirection > Options (:func:`option_rows`);
- a change sends only the options that changed, and the answer is checked
  for each one (:func:`verified`).

Wx-free and network-free; the reads and writes take an injected API.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from quill.core.wordpress.api import WordPressApiError
from quill.core.wordpress.workbench_rows import WbRow
from quill.core.workbench.properties import FieldChange, FieldKind, FieldSpec, PageSpec, SheetSpec

__all__ = [
    "KNOWN",
    "OPTIONS_ROUTE",
    "OPTIONS_SCREEN",
    "body_for",
    "missing_row",
    "option_rows",
    "options_offered",
    "options_preview",
    "options_sheet",
    "read_options",
    "settings_of",
    "undo_body",
    "verified",
]

OPTIONS_ROUTE = "redirection/v1/setting"
OPTIONS_SCREEN = "wp-admin/tools.php?page=redirection.php&sub=options"
_SCREEN_NAME = "Tools > Redirection > Options"
_NEEDS = "manage_options"
_KEEP = ("-1", "0", "1", "7", "30", "60")
_KEEP_WORDS = (
    "Keep for ever",
    "Keep none",
    "Keep a day",
    "Keep a week",
    "Keep a month",
    "Keep two months",
)


@dataclass(frozen=True)
class Known:
    """One Redirection option QUILL shows: its page, field, and whether its choices are numbers."""

    page: str
    spec: FieldSpec
    numbers: bool = False


def _check(key: str, label: str, help: str) -> FieldSpec:  # noqa: A002 - field name
    return FieldSpec(key, label, FieldKind.CHECK, requirement=_NEEDS, help=help)


def _choice(
    key: str,
    label: str,
    help: str,  # noqa: A002 - field name
    choices: tuple[str, ...],
    words: tuple[str, ...],
) -> FieldSpec:
    return FieldSpec(
        key,
        label,
        FieldKind.CHOICE,
        requirement=_NEEDS,
        help=help,
        choices=choices,
        choice_words=words,
    )


KNOWN: tuple[Known, ...] = (
    Known(
        "Matching",
        _check(
            "flag_case",
            "Ignore capital letters",
            "A redirect from /Old/ also catches /old/. New redirects start with this.",
        ),
    ),
    Known(
        "Matching",
        _check(
            "flag_trailing",
            "Ignore a slash at the end",
            "A redirect from /old also catches /old/. New redirects start with this.",
        ),
    ),
    Known(
        "Matching",
        _choice(
            "flag_query",
            "Query parameters",
            "What a redirect does with the part after a question mark. New redirects start "
            "with this.",
            ("exact", "exactorder", "ignore", "pass"),
            (
                "Must match, in any order",
                "Must match, in the same order",
                "Ignored",
                "Ignored, and passed on to the new address",
            ),
        ),
    ),
    Known(
        "Matching",
        _check(
            "flag_regex",
            "New redirects use patterns",
            "New redirects treat their address as a regular expression.",
        ),
    ),
    Known(
        "Logs",
        _choice(
            "expire_redirect",
            "Redirect log",
            "How long Redirection keeps its log of redirects it made.",
            _KEEP,
            _KEEP_WORDS,
        ),
        numbers=True,
    ),
    Known(
        "Logs",
        _choice(
            "expire_404",
            "404 log",
            "How long Redirection keeps its log of addresses not found (Redirects > 404 Log).",
            _KEEP,
            _KEEP_WORDS,
        ),
        numbers=True,
    ),
    Known(
        "Logs",
        _check(
            "track_hits",
            "Count each redirect's hits",
            "Each redirect counts how often it is used, and when last.",
        ),
    ),
    Known(
        "Logs",
        _check(
            "log_external",
            "Log other plugins' redirects",
            "The redirect log also keeps redirects that WordPress and other plugins make.",
        ),
    ),
    Known(
        "Logs",
        _check(
            "log_header",
            "Log each visit's headers",
            "The logs keep what the visitor's browser sent with the address.",
        ),
    ),
    Known(
        "Logs",
        _choice(
            "ip_logging",
            "Visitors' IP addresses",
            "Whether the logs keep the visitor's IP address, which is personal information.",
            ("0", "1", "2"),
            ("Not kept", "Kept in full", "Kept with the end hidden"),
        ),
        numbers=True,
    ),
    Known(
        "Site",
        _check(
            "https",
            "Send every visitor to HTTPS",
            "Redirection sends any address asked for over HTTP to its HTTPS address.",
        ),
    ),
    Known(
        "Site",
        _choice(
            "preferred_domain",
            "www in the address",
            "Redirection sends visitors to the site's address with or without www.",
            ("", "www", "nowww"),
            ("Left as asked", "Always with www", "Always without www"),
        ),
    ),
    Known(
        "Site",
        _choice(
            "redirect_cache",
            "Browsers keep a redirect",
            "How long a visitor's browser may remember a redirect without asking the site again.",
            ("0", "1", "24", "168", "-1"),
            ("Not at all", "An hour", "A day", "A week", "For ever"),
        ),
        numbers=True,
    ),
)
"""The options shown, page by page; anything else the route answers stays in wp-admin."""

_BY_KEY = {known.spec.key: known for known in KNOWN}


def settings_of(answer: Any) -> dict[str, Any] | None:
    """The options in an answer of the route: ``settings`` when nested, or the answer itself."""
    if not isinstance(answer, Mapping):
        return None
    inner = answer.get("settings")
    if isinstance(inner, Mapping):
        return dict(inner)
    return dict(answer) if any(key in answer for key in _BY_KEY) else None


def options_offered(routes: Sequence[str]) -> bool | None:
    """Whether the REST index lists the route: True, False, or None with no routes to go by."""
    if not routes:
        return None
    return f"/{OPTIONS_ROUTE}" in routes


def read_options(api: Any) -> dict[str, Any] | None:
    """The site's Redirection options, or None when the route is not there."""
    try:
        answer = api.get(OPTIONS_ROUTE)
    except WordPressApiError as exc:
        if exc.status == 404 or exc.wp_code == "rest_no_route":
            return None
        raise
    found = settings_of(answer)
    if found is None:
        raise WordPressApiError(
            f"{api.site_name} answered {OPTIONS_ROUTE} without Redirection's options."
        )
    return found


def _value(known: Known, raw: Any) -> Any:
    """*raw* as the field holds it, or None when QUILL does not understand it."""
    spec = known.spec
    if spec.kind is FieldKind.CHECK:
        if isinstance(raw, bool):
            return raw
        if isinstance(raw, (int, str)) and str(raw).strip().lower() in ("0", "1", "true", "false"):
            return str(raw).strip().lower() in ("1", "true")
        return None
    if isinstance(raw, bool) or not isinstance(raw, (int, str)):
        return None
    text = str(raw).strip()
    return text if text in spec.choices else None


def _shown(settings: Mapping[str, Any]) -> list[tuple[Known, Any]]:
    present = [known for known in KNOWN if known.spec.key in settings]
    found = [(known, _value(known, settings[known.spec.key])) for known in present]
    return [(known, value) for known, value in found if value is not None]


def missing_row(site: str, site_url: str, why: str) -> WbRow:
    """The one row of a site whose Redirection offers no options route: why, and Enter opens."""
    link = f"{site_url.rstrip('/')}/{OPTIONS_SCREEN}" if site_url else ""
    return WbRow(
        "admin_screen",
        site,
        "redirection_options",
        {"option": "Redirection's options", "value": "Only in wp-admin"},
        f"{why} Its options are changed in {_SCREEN_NAME}; Enter opens it in your browser.",
        link=link,
        raw={"node": "redirects", "why": why, "name": _SCREEN_NAME},
    )


def option_rows(site: str, site_url: str, settings: Mapping[str, Any]) -> list[WbRow]:
    """A row an option shown, then one naming how many more stay in wp-admin."""
    rows: list[WbRow] = []
    for known, value in _shown(settings):
        spec = known.spec
        word = spec.word_for(value)
        rows.append(
            WbRow(
                "redirect_option",
                site,
                spec.key,
                {"option": spec.label, "value": word, "title": "Redirection Options"},
                f"{spec.label}: {word}. {spec.help} Alt+Enter changes Redirection's options, "
                "after a preview.",
                raw={"key": spec.key, "page": known.page},
            )
        )
    shown = {row.key for row in rows}
    rest = sorted(key for key in settings if key not in shown)
    if rest:
        why = (
            f"Redirection on {site} has {len(rest)} more options that QUILL does not show, "
            "such as its REST API, site aliases and permalink changes."
        )
        row = missing_row(site, site_url, why)
        rows.append(
            WbRow(
                row.kind,
                site,
                "redirection_more_options",
                {"option": "More options", "value": f"{len(rest)} in wp-admin"},
                row.detail,
                link=row.link,
                raw=row.raw,
            )
        )
    return rows


def options_sheet(site: str, settings: Mapping[str, Any]) -> tuple[SheetSpec, dict[str, Any]]:
    """The Properties sheet of the options shown, and their values; refuses when none are."""
    shown = _shown(settings)
    if not shown:
        raise WordPressApiError(
            f"Redirection on {site} answered with none of the options QUILL knows, so they "
            f"stay in {_SCREEN_NAME}."
        )
    titles: list[str] = []
    fields: dict[str, list[FieldSpec]] = {}
    for known, _value_shown in shown:
        if known.page not in fields:
            titles.append(known.page)
            fields[known.page] = []
        fields[known.page].append(known.spec)
    pages = tuple(
        PageSpec("general" if index == 0 else title.lower(), title, tuple(fields[title]))
        for index, title in enumerate(titles)
    )
    sheet = SheetSpec("redirect_options", "Redirection Options", pages)
    return sheet, {known.spec.key: value for known, value in shown}


def _sent(key: str, value: Any) -> Any:
    known = _BY_KEY[key]
    if known.spec.kind is FieldKind.CHECK:
        return bool(value)
    return int(str(value)) if known.numbers else str(value)


def body_for(pending: Sequence[FieldChange]) -> dict[str, Any]:
    """What the POST sends: only the known options that changed, as the plugin stores them."""
    known = [change for change in pending if change.key in _BY_KEY]
    return {change.key: _sent(change.key, change.after) for change in known}


def undo_body(pending: Sequence[FieldChange]) -> dict[str, Any]:
    """The same options as they were before, for Ctrl+Z."""
    return {
        change.key: _sent(change.key, change.before)
        for change in pending
        if change.key in _BY_KEY and change.before is not None
    }


def options_preview(pending: Sequence[FieldChange], site: str) -> list[str]:
    """One line an option: what it is, and what it becomes."""
    lines = [f"Change {len(pending)} of Redirection's options on {site}."]
    for change in pending:
        spec = _BY_KEY[change.key].spec
        lines.append(
            f"{spec.label}: {spec.word_for(change.before)} becomes {spec.word_for(change.after)}."
        )
    return lines


def verified(site: str, body: Mapping[str, Any], answer: Any) -> str:
    """The outcome in one sentence, checked against what the site answered."""
    said = f"Changed {len(body)} of Redirection's options on {site}."
    settings = settings_of(answer)
    if settings is None:
        return said + " The site did not send the options back, so the change is not checked."
    kept = [
        _BY_KEY[key].spec.label
        for key, value in body.items()
        if key in settings and _value(_BY_KEY[key], settings[key]) != _value(_BY_KEY[key], value)
    ]
    if kept:
        return (
            f"Redirection on {site} did not take every change. Still as before: {', '.join(kept)}."
        )
    return said
