"""Check This Page, the visitor's way: axe-core on the published page (wordpress.md 9.4).

The browser (:mod:`quill.core.wordpress.cdp`) loads the public page; this
module runs **axe-core** on it, reads the page's accessibility tree, and turns
both into plain words: what is wrong, who it affects, where it is, and whose
it is (the writer's content, or the theme and its plugins).

axe-core is **bundled, never downloaded**. It is looked for at
:data:`AXE_PATH` (``quill/data/axe/axe.min.js``); when it is not there,
:func:`axe_source` raises :class:`AxeMissingError` with a sentence a person
can act on. The check reads the page and sends it nowhere; no AI is involved.

Stdlib only, no wx.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from quill.core.error_codes import CodedError
from quill.core.wordpress import cdp

__all__ = [
    "AXE_PATH",
    "AxeFinding",
    "AxeMissingError",
    "AxeNode",
    "PageAudit",
    "PageShape",
    "audit_url",
    "audit_urls",
    "axe_source",
    "explain",
    "locate_in_source",
    "parse_ax_tree",
    "parse_axe_results",
    "plain_rule",
    "shape_report",
    "summary_line",
    "theme_note",
    "wcag_criteria",
]

#: Where the bundled axe-core lives. Vendored by hand with its licence beside
#: it (MPL-2.0); the build ships ``quill/data`` whole.
AXE_PATH = Path(__file__).resolve().parents[2] / "data" / "axe" / "axe.min.js"

AXE_MISSING = (
    "Check This Page needs axe-core, which is not in this copy of QUILL. Nothing was "
    "checked and nothing was downloaded. Check Before Publishing still checks your own text."
)

_PAGE_TIMEOUT = 45.0
_MAX_NODES = 50

# The script that runs axe and says, for each place, whether it is inside the
# post's content or around it (the theme, its menus, or a plugin).
_RUN_AXE = (
    """(async () => {
  const r = await axe.run(document, {resultTypes: ['violations', 'incomplete']});
  const owner = (sel) => {
    try {
      const el = typeof sel === 'string' ? document.querySelector(sel) : null;
      if (!el) { return 'theme'; }
      return el.closest('.entry-content, .wp-block-post-content, .post-content, '
        + '.page-content, .entry, [class*="post-content"]') ? 'content' : 'theme';
    } catch (e) { return 'theme'; }
  };
  const pick = (list, outcome) => list.map(v => ({
    id: v.id, impact: v.impact || '', help: v.help, description: v.description,
    helpUrl: v.helpUrl, tags: v.tags, outcome: outcome,
    nodes: v.nodes.slice(0, MAX_NODES).map(n => ({
      target: n.target.map(String), html: n.html, summary: n.failureSummary || '',
      owner: owner(n.target[n.target.length - 1])
    }))
  }));
  return JSON.stringify(pick(r.violations, 'violation').concat(pick(r.incomplete, 'incomplete')));
})()"""
).replace("MAX_NODES", str(_MAX_NODES))


class AxeMissingError(CodedError):
    """axe-core is not bundled in this copy."""

    code = "QUILL-WP-AUDIT-NO-AXE"


@dataclass(frozen=True)
class AxeNode:
    """One place on the page where a rule failed."""

    target: tuple[str, ...]
    html: str
    summary: str
    owner: str  # "content" or "theme"


@dataclass(frozen=True)
class AxeFinding:
    """One axe rule that failed (``violation``) or needs a person to look (``incomplete``)."""

    rule: str
    impact: str
    help: str
    description: str
    help_url: str
    tags: tuple[str, ...]
    outcome: str
    nodes: tuple[AxeNode, ...]

    @property
    def owner(self) -> str:
        """``content`` when any place is in the post, else ``theme``."""
        return "content" if any(n.owner == "content" for n in self.nodes) else "theme"


@dataclass(frozen=True)
class PageShape:
    """The page as a screen reader meets it."""

    landmarks: tuple[str, ...] = ()
    headings: tuple[tuple[int, str], ...] = ()
    links: int = 0
    buttons: int = 0


@dataclass(frozen=True)
class PageAudit:
    url: str
    findings: tuple[AxeFinding, ...]
    shape: PageShape = field(default_factory=PageShape)

    @property
    def problems(self) -> int:
        return sum(1 for f in self.findings if f.outcome == "violation")

    @property
    def to_check(self) -> int:
        return sum(1 for f in self.findings if f.outcome != "violation")


# --------------------------------------------------------------------------- #
# The bundled engine


def axe_source(path: Path | None = None) -> str:
    """The text of the bundled axe-core, or :class:`AxeMissingError`."""
    where = path or AXE_PATH
    try:
        text = where.read_text(encoding="utf-8")
    except OSError as exc:
        raise AxeMissingError(AXE_MISSING) from exc
    if "axe" not in text[:4096]:
        raise AxeMissingError(AXE_MISSING)
    return text


def axe_available(path: Path | None = None) -> bool:
    return (path or AXE_PATH).is_file()


# --------------------------------------------------------------------------- #
# Running it


def _audit_one(connection: Any, url: str, axe: str, timeout: float) -> PageAudit:
    target = str(connection.call("Target.createTarget", {"url": "about:blank"}).get("targetId", ""))
    session = str(
        connection.call("Target.attachToTarget", {"targetId": target, "flatten": True}).get(
            "sessionId", ""
        )
    )
    try:
        connection.call("Page.enable", session_id=session)
        navigated = connection.call("Page.navigate", {"url": url}, session_id=session)
        if navigated.get("errorText"):
            raise cdp.CdpError(f"The page would not load: {navigated['errorText']}.")
        connection.wait_event("Page.loadEventFired", session_id=session, timeout=timeout)
        connection.call(
            "Runtime.evaluate", {"expression": axe}, session_id=session, timeout=timeout
        )
        ran = connection.call(
            "Runtime.evaluate",
            {"expression": _RUN_AXE, "awaitPromise": True, "returnByValue": True},
            session_id=session,
            timeout=timeout,
        )
        value = ran.get("result", {}).get("value", "[]") if isinstance(ran, dict) else "[]"
        if ran.get("exceptionDetails"):
            raise cdp.CdpError("axe-core could not run on that page.")
        tree = connection.call("Accessibility.getFullAXTree", session_id=session, timeout=timeout)
        return PageAudit(url, parse_axe_results(value), parse_ax_tree(tree.get("nodes", [])))
    finally:
        try:
            connection.call("Target.closeTarget", {"targetId": target})
        except cdp.CdpError:
            pass


def audit_urls(
    urls: Iterable[str],
    *,
    browser: Path | None = None,
    axe: str | None = None,
    timeout: float = _PAGE_TIMEOUT,
    launcher: Callable[[Path], Any] = cdp.HeadlessBrowser,
) -> list[PageAudit]:
    """Check each public page in one hidden browser. Runs off the UI thread.

    Raises :class:`AxeMissingError` or :class:`~cdp.BrowserMissingError` before
    starting anything when either is missing.
    """
    script = axe if axe is not None else axe_source()
    executable = browser or cdp.find_browser()
    if executable is None:
        raise cdp.BrowserMissingError(
            "Check This Page needs Microsoft Edge or Google Chrome, and neither is on this "
            "computer. QUILL does not download a browser."
        )
    audits: list[PageAudit] = []
    with launcher(executable) as connection:
        for url in urls:
            audits.append(_audit_one(connection, url, script, timeout))
    return audits


def audit_url(url: str, **kwargs: Any) -> PageAudit:
    return audit_urls([url], **kwargs)[0]


# --------------------------------------------------------------------------- #
# Reading what came back


def parse_axe_results(raw: str | list[Any]) -> tuple[AxeFinding, ...]:
    data = json.loads(raw) if isinstance(raw, str) else raw
    findings: list[AxeFinding] = []
    for item in data if isinstance(data, list) else []:
        if not isinstance(item, dict):
            continue
        nodes = tuple(
            AxeNode(
                target=tuple(str(t) for t in n.get("target", []) or []),
                html=str(n.get("html", "")),
                summary=str(n.get("summary", "")),
                owner="content" if n.get("owner") == "content" else "theme",
            )
            for n in item.get("nodes", []) or []
            if isinstance(n, dict)
        )
        findings.append(
            AxeFinding(
                rule=str(item.get("id", "")),
                impact=str(item.get("impact", "") or ""),
                help=str(item.get("help", "")),
                description=str(item.get("description", "")),
                help_url=str(item.get("helpUrl", "")),
                tags=tuple(str(t) for t in item.get("tags", []) or []),
                outcome="violation" if item.get("outcome") == "violation" else "incomplete",
                nodes=nodes,
            )
        )
    return tuple(findings)


_LANDMARKS = {
    "banner": "header",
    "navigation": "navigation",
    "main": "main content",
    "contentinfo": "footer",
    "complementary": "sidebar",
    "search": "search",
    "form": "form",
    "region": "region",
}


def _ax_value(node: dict[str, Any], key: str) -> str:
    value = node.get(key)
    return str(value.get("value", "")) if isinstance(value, dict) else ""


def parse_ax_tree(nodes: list[Any]) -> PageShape:
    """Landmarks, headings and counts from ``Accessibility.getFullAXTree``."""
    landmarks: list[str] = []
    headings: list[tuple[int, str]] = []
    links = buttons = 0
    for node in nodes:
        if not isinstance(node, dict) or node.get("ignored"):
            continue
        role = _ax_value(node, "role")
        name = " ".join(_ax_value(node, "name").split())
        if role in _LANDMARKS:
            landmarks.append(f"{_LANDMARKS[role]}: {name}" if name else _LANDMARKS[role])
        elif role == "heading":
            level = 0
            for prop in node.get("properties", []) or []:
                if isinstance(prop, dict) and prop.get("name") == "level":
                    raw = prop.get("value", {})
                    level = int(raw.get("value", 0) or 0) if isinstance(raw, dict) else 0
            headings.append((level, name))
        elif role == "link":
            links += 1
        elif role == "button":
            buttons += 1
    return PageShape(tuple(landmarks), tuple(headings), links, buttons)


# --------------------------------------------------------------------------- #
# Plain words

#: The rules a WordPress page meets most, in plain words: what is wrong, and
#: who it affects. Anything else falls back to axe's own one-line help.
_RULES: dict[str, tuple[str, str]] = {
    "image-alt": ("Images with no alt text", "people who cannot see the picture"),
    "link-name": ("Links with no name", "screen reader users, who hear only 'link'"),
    "button-name": ("Buttons with no name", "screen reader users, who hear only 'button'"),
    "color-contrast": ("Text too faint against its background", "people with low vision"),
    "heading-order": ("Headings that skip a level", "people who move by headings"),
    "page-has-heading-one": ("No Heading 1 on the page", "people who move by headings"),
    "landmark-one-main": ("No main landmark", "people who jump straight to the content"),
    "region": ("Content outside any landmark", "people who move by landmarks"),
    "html-has-lang": ("The page does not say its language", "screen readers choosing a voice"),
    "document-title": ("The page has no title", "everyone using tabs or a screen reader"),
    "label": ("Form fields with no label", "people who cannot see the field's surroundings"),
    "duplicate-id": ("Repeated element IDs", "assistive technology linking labels to fields"),
    "list": ("Lists built wrongly", "screen reader users, who hear the wrong count"),
    "listitem": ("List items outside a list", "screen reader users"),
    "frame-title": ("Embedded frames with no title", "screen reader users"),
    "video-caption": ("Videos with no captions", "people who are deaf or hard of hearing"),
    "aria-hidden-focus": ("Hidden things that can still be reached by Tab", "keyboard users"),
    "bypass": ("No way to skip past the menus", "keyboard and screen reader users"),
    "empty-heading": ("Empty headings", "people who move by headings"),
    "link-in-text-block": ("Links shown only by colour", "people who cannot tell the colours"),
    "meta-viewport": ("Zooming is turned off", "people who enlarge the page"),
    "target-size": ("Buttons or links too small to tap", "people with limited dexterity"),
}

#: The WCAG success criteria axe's tags name most, by number.
_CRITERIA: dict[str, str] = {
    "1.1.1": "Non-text Content",
    "1.2.2": "Captions (Prerecorded)",
    "1.3.1": "Info and Relationships",
    "1.4.1": "Use of Color",
    "1.4.3": "Contrast (Minimum)",
    "1.4.4": "Resize Text",
    "2.1.1": "Keyboard",
    "2.4.1": "Bypass Blocks",
    "2.4.2": "Page Titled",
    "2.4.4": "Link Purpose (In Context)",
    "2.4.6": "Headings and Labels",
    "2.5.8": "Target Size (Minimum)",
    "3.1.1": "Language of Page",
    "3.1.2": "Language of Parts",
    "3.3.2": "Labels or Instructions",
    "4.1.2": "Name, Role, Value",
}

_WCAG_TAG_RE = re.compile(r"^wcag(\d)(\d)(\d+)$")


def wcag_criteria(tags: Iterable[str]) -> list[str]:
    """``["1.1.1 Non-text Content"]`` from axe's ``wcag111`` tags."""
    found: list[str] = []
    for tag in tags:
        match = _WCAG_TAG_RE.match(tag)
        if match:
            number = ".".join(match.groups())
            label = f"{number} {_CRITERIA[number]}" if number in _CRITERIA else number
            if label not in found:
                found.append(label)
    return found


def plain_rule(finding: AxeFinding) -> tuple[str, str]:
    """What is wrong, and who it affects."""
    if finding.rule in _RULES:
        return _RULES[finding.rule]
    return finding.help.rstrip(".") or finding.rule, "some visitors"


def _where(owner: str) -> str:
    return "in your content" if owner == "content" else "in the theme or a plugin"


def finding_row(finding: AxeFinding) -> str:
    """One list row: "Images with no alt text: 3 places, in your content, affects ..."."""
    what, who = plain_rule(finding)
    places = len(finding.nodes)
    count = f"{places} place" if places == 1 else f"{places} places"
    status = "" if finding.outcome == "violation" else ", to check"
    return f"{what}: {count}, {_where(finding.owner)}{status}. Affects {who}"


def explain(finding: AxeFinding) -> str:
    """Explain: the WCAG criterion by number and name, why it matters, and each place."""
    what, who = plain_rule(finding)
    criteria = wcag_criteria(finding.tags)
    lines = [what + ".", ""]
    if criteria:
        lines.append("WCAG: " + "; ".join(criteria) + ".")
    lines.append(f"Who it affects: {who}.")
    if finding.description:
        lines.append(f"Why it matters: {finding.description.rstrip('.')}.")
    if finding.outcome != "violation":
        lines.append("axe-core could not decide this one by itself; it needs a person to look.")
    lines.append("")
    for number, node in enumerate(finding.nodes, 1):
        where = _where(node.owner)
        lines.append(f"Place {number}, {where}: {' '.join(node.html.split())[:200]}")
        if node.summary:
            lines.append("  " + " ".join(node.summary.split()))
    if finding.help_url:
        lines += ["", f"More: {finding.help_url}"]
    return "\n".join(lines)


def summary_line(label: str, audit: PageAudit) -> str:
    """ "Community Radio home page: 3 problems, 2 to check"."""
    if not audit.findings:
        return f"{label}: no problems found by axe-core"
    parts = []
    if audit.problems:
        parts.append(f"{audit.problems} problem" + ("" if audit.problems == 1 else "s"))
    if audit.to_check:
        parts.append(f"{audit.to_check} to check")
    return f"{label}: {', '.join(parts)}"


def shape_report(shape: PageShape) -> str:
    """The page's shape, as a screen reader meets it."""
    lines = ["Landmarks, in order:"]
    lines += [f"- {mark}" for mark in shape.landmarks] or ["- none"]
    lines += ["", "Headings, in order:"]
    lines += [f"- Heading {level}: {text or '(empty)'}" for level, text in shape.headings] or [
        "- none"
    ]
    ones = sum(1 for level, _text in shape.headings if level == 1)
    if ones > 1:
        lines.append(
            f"There are {ones} Heading 1s. Often the theme puts the site title in one and the "
            "page title in another."
        )
    lines += ["", f"Links: {shape.links}. Buttons: {shape.buttons}."]
    return "\n".join(lines)


def theme_note(finding: AxeFinding, *, page_url: str, theme: str = "") -> str:
    """A plain-text report for the theme or plugin author, ready to paste."""
    what, who = plain_rule(finding)
    criteria = wcag_criteria(finding.tags)
    lines = [
        f"Hello. I found an accessibility problem in {theme or 'the theme'} on this page:",
        page_url,
        "",
        f"Problem: {what}. It affects {who}.",
    ]
    if criteria:
        lines.append("WCAG 2.2: " + "; ".join(criteria) + ".")
    lines.append(
        f"axe-core rule: {finding.rule}" + (f" ({finding.help_url})" if finding.help_url else "")
    )
    lines += ["", "Where it is:"]
    for node in finding.nodes[:10]:
        lines.append(f"- {' > '.join(node.target)}: {' '.join(node.html.split())[:200]}")
    lines += ["", "Found with QUILL's Check This Page, which runs axe-core. Thank you."]
    return "\n".join(lines)


_ATTR_RE = re.compile(r"""\b(src|href)\s*=\s*["']([^"']+)["']""", re.IGNORECASE)
_TAG_RE = re.compile(r"<[^>]+>")


def locate_in_source(node_html: str, source: str) -> int:
    """Where a place axe found is in the writer's document, or -1.

    The rendered page is not the source, so this looks for what survives
    rendering: an image or link address first, then the visible text.
    """
    for _name, value in _ATTR_RE.findall(node_html):
        address = value.split("#", 1)[0].split("?", 1)[0]
        tail = address.rsplit("/", 1)[-1]
        for needle in (address, tail):
            if needle and (at := source.find(needle)) >= 0:
                return at
    text = " ".join(_TAG_RE.sub(" ", node_html).split())
    if len(text) >= 3:
        return source.find(text[:60])
    return -1
