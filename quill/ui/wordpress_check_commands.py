"""File > WordPress > Checking: the visitor's-eye checks and site-wide fixes.

Plan: wordpress.md 7, 9.4, 9.5, 9.7, 9.11, 9.12, 10 (In Short).

A mixin of :class:`~quill.ui.wordpress_commands.WordPressCommands`, shared by
QUILL and QUILL Lite; it reaches the editor only through ``self.host``. The
site-wide commands are in its bases: Check the Whole Site and Undo Site Fix in
:mod:`quill.ui.wordpress_site_check_commands`, Site-wide Find and Replace in
:mod:`quill.ui.wordpress_find_replace_commands`.
Check Before Publishing (``cmd_check``) lives with the sends, in
:mod:`quill.ui.wordpress_more_commands`.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from quill.core.wordpress import cdp
from quill.core.wordpress import contrast as con
from quill.core.wordpress import local as lc
from quill.core.wordpress import page_audit as pa
from quill.core.wordpress import readability as rd
from quill.core.wordpress import site as wp
from quill.core.wordpress import site_report as rpt
from quill.core.wordpress.api import WordPressApiError
from quill.ui import wordpress_dialogs as dlg
from quill.ui.wordpress_find_replace_commands import WordPressFindReplaceCommands
from quill.ui.wordpress_site_check_commands import plain

if TYPE_CHECKING:
    from quill.core.wordpress import sites as st

NO_BROWSER = (
    "Check This Page needs Microsoft Edge or Google Chrome, and neither is on this computer. "
    "QUILL does not download a browser. Check Before Publishing still checks your own text."
)

_HTML_RE = re.compile(r"<[A-Za-z!/][^>]*>")
_AI_TEXT_LIMIT = 12000


def reading_level_line(text: str, *, is_html: bool | None = None) -> str:
    """The Properties line: "Reading level: about 9th grade, 14 words per sentence".

    Worked out on this computer; nothing is sent. *is_html* is guessed from
    the text when not given, so a Markdown and an HTML document both work.
    """
    html = bool(_HTML_RE.search(text)) if is_html is None else is_html
    return rd.describe(rd.reading_level(text, is_html=html))


def ask_text_ai(
    editor: Any,
    prompt: str,
    on_done: Callable[[str], None],
    on_error: Callable[[str], None],
) -> bool:
    """One text request to the editor's chosen AI, behind its own gates. False: nothing sent.

    *editor* carries ``HostedAiMixin`` (QUILL's main frame, a QUILL Lite
    window). Its gates say why themselves when they stop: AI switched off,
    the agreement not accepted, a connection that cannot do text.
    """
    ready = getattr(editor, "_ai_ready", None)
    capable = getattr(editor, "_ai_capable", None)
    service_of = getattr(editor, "_ai_service", None)
    if not callable(ready) or not callable(capable) or not callable(service_of):
        on_error("AI help is not available in this window.")
        return False
    if not ready() or not capable("text"):
        return False
    service_of().ask(
        "ask",
        prompt,
        None,
        on_done=lambda text, _quota: on_done(str(text or "").strip()),
        on_error=on_error,
        requires=("text",),
    )
    return True


def active_theme(api: Any) -> tuple[str, str]:
    """``(name, stylesheet)`` of the site's active theme, or blanks when it is not shown."""
    try:
        raw = api.get("wp/v2/themes", status="active", _fields="name,stylesheet")
    except WordPressApiError:
        return "", ""
    first = raw[0] if isinstance(raw, list) and raw and isinstance(raw[0], dict) else {}
    return wp.raw_text(first.get("name")), str(first.get("stylesheet", "") or "")


class WordPressCheckCommands(WordPressFindReplaceCommands):
    # Provided by WordPressCommands.
    host: Any
    local: lc.LocalStore

    # ------------------------------------------------------------------ #
    # Check This Page (9.4)

    def cmd_check_page(self) -> None:
        copy = self.local.copy_for_path(self.host.current_path())
        if copy is not None:
            found = self.current()  # type: ignore[attr-defined]
            if found is None:
                return
            copy, profile = found
            if copy.status != "publish" or not copy.link:
                self.host.announce(
                    f"Check This Page reads the published page, and this is not published on "
                    f"{profile.name} yet. Check Before Publishing looks at your own text now."
                )
                return
            url, label = copy.link, f"{profile.name}, {copy.title or 'this page'}"
        else:
            store = self.need_site()  # type: ignore[attr-defined]
            if store is None:
                return
            chosen = self.pick_site(store, "Check This Page")  # type: ignore[attr-defined]
            if chosen is None:
                return
            profile = chosen
            url, label = profile.site_url, f"{profile.name} home page"
        if not pa.axe_available():
            self.host.announce(pa.AXE_MISSING)
            return
        browser = cdp.find_browser()
        if browser is None:
            self.host.announce(NO_BROWSER)
            return
        api = self.api(profile)  # type: ignore[attr-defined]

        def work() -> tuple[pa.PageAudit, str] | BaseException:
            try:
                audit = pa.audit_url(url, browser=browser)
            except (cdp.CdpError, cdp.BrowserMissingError, pa.AxeMissingError) as exc:
                return exc
            return audit, active_theme(api)[0]

        def done(result: tuple[pa.PageAudit, str] | BaseException) -> None:
            if isinstance(result, BaseException):
                self.host.announce(f"Check This Page could not check {label}: {plain(result)}")
                return
            self._show_page_audit(label, url, result[0], result[1], copy)

        self.background(f"checking {label}", work, done)  # type: ignore[attr-defined]

    def _show_page_audit(
        self,
        label: str,
        url: str,
        audit: pa.PageAudit,
        theme: str,
        copy: lc.WorkingCopy | None,
    ) -> None:
        summary = pa.summary_line(label, audit)
        self.host.announce(summary)
        findings = list(audit.findings)
        document_path = self.host.current_path()

        def explain(index: int | None) -> object:
            if index is not None:
                dlg.show_report(
                    self.host.parent,
                    self.host.show_modal,
                    title="Explain",
                    text=pa.explain(findings[index]),
                    help_text="What is wrong, the WCAG criterion, who it affects, and each place.",
                )
            return None

        def go(index: int | None) -> object:
            if index is None:
                return None
            finding = findings[index]
            if finding.owner != "content":
                self.host.announce(
                    "That one is in the theme or a plugin, not in your document. Write a Note "
                    "for the Theme Author makes a report you can send them."
                )
                return None
            same = copy is not None and self.host.current_path() == document_path
            if not same:
                self.host.announce(
                    "Open the page in the editor first, then Go to It can take you there."
                )
                return None
            text = self.host.current_text()
            for node in finding.nodes:
                if node.owner != "content":
                    continue
                at = pa.locate_in_source(node.html, text)
                if at >= 0:
                    self.host.go_to_offset(at)
                    return dlg.CLOSE
            self.host.announce(
                "QUILL could not find that place in your document; Explain shows what it looks "
                "like on the page."
            )
            return None

        def note(index: int | None) -> object:
            if index is None:
                return None
            finding = findings[index]
            if finding.owner == "content":
                self.host.announce(
                    "That one is in your own content, so you can fix it yourself; Go to It "
                    "takes you there."
                )
                return None
            dlg.show_report(
                self.host.parent,
                self.host.show_modal,
                title="Note for the Theme Author",
                text=pa.theme_note(finding, page_url=url, theme=theme),
                help_text=(
                    "A plain report of the problem, ready to paste into a support forum or an "
                    "email to the theme or plugin author. Copy All copies it."
                ),
            )
            return None

        def shape(_index: int | None) -> object:
            dlg.show_report(
                self.host.parent,
                self.host.show_modal,
                title="Page Shape",
                text=pa.shape_report(audit.shape),
                help_text=(
                    "The page as a screen reader meets it: its landmarks, its headings "
                    "including the theme's own, and how many links and buttons it has."
                ),
            )
            return None

        window = dlg.show_list_window(
            self.host.parent,
            self.host.show_modal,
            title="Check This Page",
            purpose=summary + ". Checked with axe-core; the page was sent nowhere.",
            list_label="&Findings:",
            list_help=(
                "Each problem axe-core found, in plain words: how many places, whose it is, "
                "and who it affects."
            ),
            rows=[pa.finding_row(f) for f in findings],
            actions=[
                dlg.Action("&Explain...", "The WCAG criterion and why it matters.", explain),
                dlg.Action("&Go to It", "Go to this place in your document.", go),
                dlg.Action(
                    "Write a &Note for the Theme Author...",
                    "A plain report for whoever made the theme or plugin.",
                    note,
                ),
                dlg.Action(
                    "Page &Shape...",
                    "Landmarks, headings, links and buttons, as a screen reader meets them.",
                    shape,
                    needs_row=False,
                ),
            ],
        )
        window.Destroy()

    # ------------------------------------------------------------------ #
    # Write an Accessibility Statement (9.12)

    def cmd_accessibility_statement(self) -> None:
        profile = self._site_for("Write an Accessibility Statement")
        if profile is None:
            return
        api = self.api(profile)  # type: ignore[attr-defined]

        def work() -> str:
            try:
                raw = api.get("wp/v2/settings", _fields="email")
            except WordPressApiError:
                return ""  # only administrators can read it; the person types one
            return str(raw.get("email", "") or "") if isinstance(raw, dict) else ""

        self.background(  # type: ignore[attr-defined]
            f"reading {profile.name}", work, lambda email: self._write_statement(profile, email)
        )

    def _write_statement(self, profile: st.SiteProfile, email: str) -> None:
        contact = dlg.ask_text(
            self.host.parent,
            self.host.show_modal,
            title="Write an Accessibility Statement",
            prompt="&Contact:",
            value=email,
            help_text=(
                "How a visitor reaches you about a problem: an email address, a phone number "
                "or a contact page. The site's admin email is offered when your account can "
                "see it."
            ),
        )
        if contact is None:
            return
        html = getattr(self, "_last_format", "markdown") == "html"
        title, text = rpt.accessibility_statement(
            profile.name,
            contact=contact.strip(),
            last=self._check_history().latest(profile.id),
            html=html,
        )
        copy = lc.WorkingCopy(
            site_id=profile.id,
            kind="page",
            local_id=lc.new_local_id(),
            title=title,
            text=text,
            text_format="html" if html else "markdown",
            properties={"slug": "accessibility"},
        )
        self.host.open_path(self.local.write_document(copy))
        self.host.announce(
            f"Accessibility statement draft for {profile.name} is open. It is yours to edit; "
            "nothing is sent until you choose Save Draft to Site or Publish."
        )

    # ------------------------------------------------------------------ #
    # Palette Report (9.7)

    def cmd_palette_report(self) -> None:
        profile = self._site_for("Palette Report")
        if profile is None:
            return
        api = self.api(profile)  # type: ignore[attr-defined]

        def work() -> tuple[str, list[str]]:
            name, stylesheet = active_theme(api)
            if not stylesheet:
                return name, []
            raw = api.get(f"wp/v2/global-styles/themes/{stylesheet}")
            palette, backgrounds = rpt.palette_from_global_styles(raw)
            return name, con.palette_report(_readable(palette), _readable(backgrounds))

        def done(result: tuple[str, list[str]]) -> None:
            theme, lines = result
            if not lines:
                self.host.announce(
                    f"QUILL could not read a colour palette from {profile.name}'s theme."
                )
                return
            faint = sum(1 for line in lines if not line.endswith(", passes"))
            who = f"{theme} on {profile.name}" if theme else profile.name
            summary = (
                f"{who}: {len(lines)} pairings, {faint} below the WCAG AA minimum for body text."
            )
            self.host.announce(summary)
            dlg.show_report(
                self.host.parent,
                self.host.show_modal,
                title="Palette Report",
                text=summary + "\n\n" + "\n".join(lines),
                help_text=(
                    "Every colour in the theme's palette on every background, with its contrast "
                    "ratio. Body text needs 4.5 to 1; large text 3 to 1."
                ),
            )

        self.background(f"reading {profile.name}'s colours", work, done)  # type: ignore[attr-defined]

    # ------------------------------------------------------------------ #
    # Mark Language and In Short (9.11, 10)

    def cmd_mark_language(self) -> None:
        found = self.current()  # type: ignore[attr-defined]
        if found is None:
            return
        copy, _profile = found
        answer = dlg.ask_text(
            self.host.parent,
            self.host.show_modal,
            title="Mark Language",
            prompt="&Language:",
            value=getattr(self, "_last_language", ""),
            help_text=(
                "The language of the selected words, as a name such as French or a code such "
                "as fr or pt-BR. With nothing selected, the whole page is marked. A visitor's "
                "screen reader switches voice there."
            ),
        )
        if not answer or not answer.strip():
            return
        tag = rpt.valid_language(answer)
        if not tag:
            self.host.announce(
                f"QUILL does not know '{answer.strip()}' as a language. Type a name such as "
                "French, or a code such as fr or pt-BR."
            )
            return
        self._last_language = tag
        html = copy.text_format == "html"
        selected = self.host.selected_text()
        if selected.strip():
            self.host.insert_text(rpt.mark_language(selected, tag, html=html))
            where = "The selection"
        else:
            text = self.host.current_text()
            if not text.strip():
                self.host.announce("There is nothing on the page to mark yet.")
                return
            self.host.replace_text(rpt.mark_language(text, tag, html=html, whole=True))
            where = "The whole page"
        self.host.announce(f"{where} is marked as {rpt.language_name(tag)}.")

    def cmd_in_short(self) -> None:
        found = self.current()  # type: ignore[attr-defined]
        if found is None:
            return
        copy, _profile = found
        opener = getattr(self.host, "ai_editor", None)
        editor = opener() if callable(opener) else None
        if editor is None:
            self.host.announce("AI help is not available in this window.")
            return
        text = self.host.current_text()
        html = copy.text_format == "html"
        words = rd.strip_html(text).text if html else text
        if not words.strip():
            self.host.announce("There is nothing to summarise yet.")
            return
        prompt = rpt.in_short_prompt(copy.title, words[:_AI_TEXT_LIMIT])

        def answered(summary: str) -> None:
            if not summary.strip():
                self.host.announce("The AI sent back nothing to use. Nothing was changed.")
                return
            current = self.host.current_text()
            self.local.add_version(copy, lc.REASON_BEFORE_AI, text=current, title=copy.title)
            self.host.replace_text(rpt.insert_in_short(current, summary, html=html))
            self.host.go_to_offset(0)
            self.host.announce(
                "In Short is at the top of the page. Edit it like any paragraph; Undo takes it out."
            )

        ask_text_ai(editor, prompt, answered, self.host.announce)


def _readable(colours: list[tuple[str, str]]) -> list[tuple[str, str]]:
    """Only the colours QUILL can read; a gradient or a CSS variable is left out."""
    kept = []
    for name, value in colours:
        try:
            con.parse_colour(value)
        except con.ColourParseError:
            continue
        kept.append((name, value))
    return kept


__all__ = ["WordPressCheckCommands", "active_theme", "ask_text_ai", "plain", "reading_level_line"]
