"""Writing the Site Editor's templates, parts and Additional CSS (wordpress.md 9.18, package 7).

What REST allows, checked against WordPress's own controllers:

- **Templates and template parts** (``wp/v2/templates`` and
  ``wp/v2/template-parts``, Administrator, ``edit_theme_options``): a GET
  with ``context=edit`` gives the block markup (``content.raw``); a POST to
  the item saves it, and for a template that came from the theme's files
  that POST makes the site's own customized copy. A DELETE with
  ``force=true`` removes the customized copy, so the theme's file applies
  again (**Reset to the Theme's Version**); on a template the theme never
  had, the same DELETE removes it for good. ``?source=theme`` reads the
  theme's own version for the preview. ``.../revisions`` lists earlier
  versions of a customized one (6.4 and later), and ``templates/lookup``
  says which template WordPress would use for a slug, which is where a
  **New Template** starts.
- **Additional CSS** in a block theme is ``styles.css`` in the site's own
  global styles (``wp/v2/global-styles/{id}``, 6.2 and later, ``edit_css``).
  The POST replaces the whole ``styles`` object, so the current styles are
  sent back with only ``css`` changed. WordPress keeps each save as a
  global styles revision, which is Previous Looks. A classic theme keeps
  its CSS in the Customizer (``custom_css``), which no REST route reaches;
  that row opens Appearance > Customize > Additional CSS instead.

Every write here re-reads first and refuses with :class:`EditConflict` when
the site changed since the text was loaded (:func:`check_template`,
:func:`check_css`); each returns what the undo needs. :func:`change_lines`
says a change line by line for the preview. Wx-free; runs off the UI thread.
"""

from __future__ import annotations

import difflib
import re
from collections.abc import Mapping
from dataclasses import dataclass, replace
from typing import Any

from quill.core.wordpress.api import WordPressApi, WordPressApiError
from quill.core.wordpress.site import friendly_date, raw_text, rendered
from quill.core.wordpress.workbench_edit import EditConflict, EditRefused
from quill.core.wordpress.workbench_rows import WbRow

__all__ = [
    "CSS_LINK",
    "CssText",
    "Revision",
    "TEMPLATE_ROUTES",
    "TemplateText",
    "change_lines",
    "check_css",
    "check_template",
    "css_problem",
    "css_rows",
    "create_template",
    "load_css",
    "load_template",
    "lookup_template",
    "reset_template",
    "restore_template",
    "save_css",
    "save_template",
    "template_revisions",
    "theme_version",
]

TEMPLATE_ROUTES: Mapping[str, str] = {
    "wp_template": "wp/v2/templates",
    "wp_template_part": "wp/v2/template-parts",
}
CSS_LINK = "wp-admin/customize.php?autofocus%5Bsection%5D=custom_css"
"""Where a classic theme's Additional CSS is (the Customizer has no REST route)."""

_MARKUP = re.compile(r"</?[A-Za-z][^>]*>")
_SLUG = re.compile(r"^[a-z0-9][a-z0-9-]*$")
_PREVIEW_LINES = 40


@dataclass(frozen=True)
class TemplateText:
    """One template or part as it was read, with what the undo and conflict check need."""

    route: str
    id: str
    slug: str
    title: str
    content: str
    source: str
    has_theme_file: bool
    kind: str  # wp_template or wp_template_part
    area: str = ""
    modified: str = ""

    @property
    def noun(self) -> str:
        return "template" if self.kind == "wp_template" else "template part"

    @property
    def customized(self) -> bool:
        return self.source == "custom"

    @property
    def collection(self) -> str:
        return TEMPLATE_ROUTES[self.kind]


def _template(route: str, raw: Mapping[str, Any]) -> TemplateText:
    kind = str(raw.get("type", "") or "")
    if kind not in TEMPLATE_ROUTES:
        kind = "wp_template_part" if "template-parts" in route else "wp_template"
    return TemplateText(
        route=route,
        id=str(raw.get("id", "") or ""),
        slug=str(raw.get("slug", "") or ""),
        title=rendered(raw.get("title")) or raw_text(raw.get("title")) or str(raw.get("slug", "")),
        content=raw_text(raw.get("content")),
        source=str(raw.get("source", "") or ""),
        has_theme_file=bool(raw.get("has_theme_file")),
        kind=kind,
        area=str(raw.get("area", "") or ""),
        modified=str(raw.get("modified", "") or ""),
    )


def load_template(api: WordPressApi, route: str) -> TemplateText:
    """The template at *route* (``wp/v2/templates/theme//single``), with its block markup."""
    raw = api.get(route, context="edit")
    if not isinstance(raw, dict):
        raise WordPressApiError("The site did not send the template.")
    return _template(route, raw)


def theme_version(api: WordPressApi, template: TemplateText) -> str:
    """The theme's own markup for *template* ("" when the theme has none or will not say)."""
    if not template.has_theme_file:
        return ""
    try:
        raw = api.get(template.route, context="edit", source="theme")
    except WordPressApiError:
        return ""
    return raw_text(raw.get("content")) if isinstance(raw, dict) else ""


def check_template(api: WordPressApi, loaded: TemplateText) -> TemplateText:
    """Read it again; refuse when its markup changed on the site since it was loaded."""
    now = load_template(api, loaded.route)
    if now.content != loaded.content or now.source != loaded.source:
        raise EditConflict(
            f"{loaded.title} was changed on the site after QUILL read it. Nothing was sent; "
            "read it again and make the change there."
        )
    return now


def save_template(api: WordPressApi, loaded: TemplateText, content: str) -> TemplateText:
    """Conflict-checked save of *content*; a theme template becomes the site's own copy."""
    check_template(api, loaded)
    answer = api.post(loaded.route, {"content": content}, context="edit")
    saved = _template(loaded.route, answer) if isinstance(answer, dict) else loaded
    if saved.content and saved.content != content:
        raise EditRefused(f"The site kept a different version of {loaded.title}.")
    return replace(saved, content=content)


def restore_template(api: WordPressApi, template: TemplateText, content: str) -> TemplateText:
    """Put *content* back (the undo of a save, a reset or a revision restore)."""
    try:
        answer = api.post(template.route, {"content": content}, context="edit")
    except WordPressApiError as exc:
        if exc.status != 404:
            raise
        body: dict[str, Any] = {"slug": template.slug, "title": template.title, "content": content}
        if template.kind == "wp_template_part" and template.area:
            body["area"] = template.area
        answer = api.post(template.collection, body, context="edit")
    return _template(template.route, answer) if isinstance(answer, dict) else template


def reset_template(api: WordPressApi, loaded: TemplateText) -> TemplateText:
    """Remove the customized copy (conflict-checked), so the theme's file applies again."""
    if not loaded.customized:
        raise EditRefused(f"{loaded.title} already is the theme's version.")
    check_template(api, loaded)
    api.delete(loaded.route, force=True)
    return loaded


@dataclass(frozen=True)
class Revision:
    id: int
    date_gmt: str
    content: str

    @property
    def when(self) -> str:
        return friendly_date(self.date_gmt) if self.date_gmt else "a date not said"


def template_revisions(api: WordPressApi, template: TemplateText) -> list[Revision]:
    """Earlier versions of a customized template, newest first (none for a theme's own)."""
    got = api.get(f"{template.route}/revisions", context="edit")
    found = [
        Revision(
            int(raw.get("id", 0) or 0),
            str(raw.get("modified_gmt") or raw.get("date_gmt") or ""),
            raw_text(raw.get("content")),
        )
        for raw in (got if isinstance(got, list) else [])
        if isinstance(raw, dict)
    ]
    return sorted(found, key=lambda r: r.date_gmt, reverse=True)


def lookup_template(api: WordPressApi, slug: str) -> TemplateText | None:
    """The template WordPress would use today for *slug* (``single-post-news``)."""
    raw = api.get("wp/v2/templates/lookup", slug=slug, context="edit")
    if not isinstance(raw, dict) or not raw.get("id"):
        return None
    return _template(f"wp/v2/templates/{raw.get('id')}", raw)


def create_template(
    api: WordPressApi, kind: str, slug: str, title: str, content: str
) -> TemplateText:
    """A new template or part (the slug checked first); its DELETE is the undo."""
    clean = slug.strip().lower()
    if not _SLUG.match(clean):
        raise EditRefused(
            f"{slug} cannot be a template's name: use lowercase letters, numbers and hyphens."
        )
    route = TEMPLATE_ROUTES[kind]
    body = {"slug": clean, "title": title.strip() or clean, "content": content}
    answer = api.post(route, body, context="edit")
    if not isinstance(answer, dict) or not answer.get("id"):
        raise WordPressApiError(f"The site did not make the {clean} template.")
    return _template(f"{route}/{answer['id']}", answer)


def change_lines(old: str, new: str, *, limit: int = _PREVIEW_LINES) -> list[str]:
    """A change line by line, in words, for a preview: "Line 4 added: ..."."""
    before, after = old.splitlines(), new.splitlines()
    said: list[str] = []
    matcher = difflib.SequenceMatcher(a=before, b=after, autojunk=False)
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag in ("delete", "replace"):
            said += [
                f"Line {i + 1} removed: {before[i].strip() or '(blank)'}" for i in range(i1, i2)
            ]
        if tag in ("insert", "replace"):
            said += [f"Line {j + 1} added: {after[j].strip() or '(blank)'}" for j in range(j1, j2)]
    if not said:
        return ["No line changes."]
    if len(said) > limit:
        more = len(said) - limit
        said = [*said[:limit], f"And {more} more line change{'' if more == 1 else 's'}."]
    return said


# -- Additional CSS ----------------------------------------------------------------


@dataclass(frozen=True)
class CssText:
    """The site's Additional CSS as read, with the rest of its styles kept for the save."""

    styles_id: int
    css: str
    styles: Mapping[str, Any]


def load_css(api: WordPressApi, styles_id: int) -> CssText:
    raw = api.get(f"wp/v2/global-styles/{styles_id}", context="edit")
    if not isinstance(raw, dict):
        raise WordPressApiError("The site did not send its styles.")
    found = raw.get("styles")
    styles: dict[str, Any] = dict(found) if isinstance(found, dict) else {}
    return CssText(styles_id, str(styles.get("css", "") or ""), styles)


def check_css(api: WordPressApi, loaded: CssText) -> CssText:
    now = load_css(api, loaded.styles_id)
    if now.css != loaded.css:
        raise EditConflict(
            "The site's Additional CSS was changed after QUILL read it. Nothing was sent; "
            "read it again and make the change there."
        )
    return now


def css_problem(css: str) -> str:
    """Why WordPress would refuse *css*, or "" (it refuses markup; braces must pair)."""
    if _MARKUP.search(css):
        return "WordPress refuses markup such as <style> in CSS; take the tags out."
    depth = 0
    for char in re.sub(r"/\*.*?\*/", "", css, flags=re.DOTALL):
        depth += 1 if char == "{" else -1 if char == "}" else 0
        if depth < 0:
            return "A closing brace comes before its opening one."
    return "" if depth == 0 else f"{depth} opening brace{'' if depth == 1 else 's'} never closed."


def save_css(api: WordPressApi, loaded: CssText, css: str) -> CssText:
    """Conflict-checked save of *css*, with every other style sent back unchanged."""
    problem = css_problem(css)
    if problem:
        raise EditRefused(problem)
    now = check_css(api, loaded)
    styles = {**now.styles, "css": css}
    api.post(f"wp/v2/global-styles/{loaded.styles_id}", {"styles": styles})
    return CssText(loaded.styles_id, css, styles)


def css_rows(site: str, site_url: str, api: WordPressApi) -> list[WbRow]:
    """The Additional CSS node: one row to edit, or one that opens the Customizer."""
    from quill.core.wordpress.site_styles import active_theme

    theme = active_theme(api)
    if not theme.block_theme or not theme.styles_id:
        link = f"{site_url.rstrip('/')}/{CSS_LINK}" if site_url else ""
        return [
            WbRow(
                "admin_screen",
                site,
                "custom_css",
                {"screen": "Additional CSS", "reach": "Only in wp-admin"},
                f"{theme.name or 'The active theme'} is a classic theme, which keeps its "
                "Additional CSS in the Customizer; no REST route reaches it. Enter opens "
                "Appearance > Customize > Additional CSS in your browser.",
                link=link,
                status="dashboard",
                raw={"node": "additional_css", "name": "Appearance > Customize > Additional CSS"},
            )
        ]
    loaded = load_css(api, theme.styles_id)
    lines = [line for line in loaded.css.splitlines() if line.strip()]
    said = (
        f"{len(lines)} line{'' if len(lines) == 1 else 's'} of Additional CSS"
        if lines
        else "No Additional CSS yet"
    )
    first = f" It begins: {lines[0].strip()}" if lines else ""
    return [
        WbRow(
            "custom_css",
            site,
            str(theme.styles_id),
            {"screen": "Additional CSS", "reach": said},
            f"{said} in {theme.name or 'the active theme'}'s site styles.{first} Edit "
            "Additional CSS changes it; each save is kept in Previous Looks.",
            route=f"wp/v2/global-styles/{theme.styles_id}",
            raw={"styles_id": theme.styles_id, "css": loaded.css},
        )
    ]
