"""Visitor Words for Forms, from the WordPress Workbench (PRD D5, 13a; WP-R-050).

A mixin taken in through :class:`quill.ui.wordpress_workbench_forms_site.WorkbenchPluginCommands`,
which supplies the asking, preview and report helpers (``_pl_*``). On a
site's context menu: the words QUILL Accessible Forms shows visitors after
sending, around a text challenge and when a form is held for a person to
read, in each language the site offers. Choose one, type its new words (or
nothing, for the plugin's own), check the preview, and the save reads the
words again, sends, and reads them back. The routes and words are wx-free in
:mod:`quill.core.wordpress.workbench_qaf_visitor_words`. The same Workbench
is QUILL's and QUILL Lite's, so both editors have this.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from quill.core.wordpress import workbench_qaf_visitor_words as vw
from quill.core.wordpress.workbench_qaf_spam import spam_namespace

__all__ = ["WorkbenchQafWordsCommands"]

_WRITE = "qaf/v1"


class WorkbenchQafWordsCommands:
    """Visitor Words for Forms."""

    say: Callable[[str], None]
    background: Callable[..., None]
    ctx: Callable[[str], Any]
    ensure: Callable[[Any], Any]
    site_of: Callable[[Any], str]
    current_site: Callable[[], str]

    def do_visitor_words(self, ref: Any, _row: Any) -> None:
        site = self.site_of(ref) or self.current_site()
        if not site:
            self.say("Connect a site first.")
            return
        api = self.ctx(site).api
        where: dict[str, str] = {}

        def read() -> vw.VisitorWords | None:
            where["namespace"] = namespace = spam_namespace(self.ensure(self.ctx(site)))
            return vw.read_words(api, namespace) if namespace == _WRITE else None

        def chosen(held: vw.VisitorWords | None) -> None:
            namespace = where.get("namespace", "")
            if not namespace:
                self.say("This site has no QUILL Accessible Forms, so there are no form words.")
            elif held is None:
                self.say(vw.no_route_sentence())
            elif len(held.languages) > 1:
                self._pick_language(site, api, held)
            else:
                self._pick_word(site, api, held)

        self.background(f"reading {site}'s visitor words", read, chosen)

    def _pick_language(self, site: str, api: Any, held: vw.VisitorWords) -> None:
        languages = list(held.languages)
        picked = self._pl_choose(  # type: ignore[attr-defined]
            f"Visitor Words for Forms - {site}",
            "&Language:",
            languages,
            "The languages this site offers its visitors. Each has its own words.",
        )
        if picked is None:
            return
        language = languages[picked]
        if language == held.language:
            self._pick_word(site, api, held)
            return
        self.background(
            f"reading {site}'s visitor words in {language}",
            lambda: vw.read_words(api, _WRITE, language),
            lambda found: (
                self._pick_word(site, api, found) if found else self.say(vw.no_route_sentence())
            ),
        )

    def _pick_word(self, site: str, api: Any, held: vw.VisitorWords) -> None:
        if not held.can_edit:
            self.say(
                "Changing the visitor words needs the site's Manage Options capability, or "
                "QUILL Accessible Forms' own Manage Settings."
            )
            return
        rows = [vw.word_line(held, w.key) for w in vw.WORDS]
        picked = self._pl_choose(  # type: ignore[attr-defined]
            f"Visitor Words for Forms - {site}",
            "&Words (Enter on one changes it):",
            rows,
            "What visitors read on this site's forms, as the site holds it now. Words the "
            "plugin still chooses say so.",
        )
        if picked is None:
            return
        word = vw.WORDS[picked]
        typed = self._pl_ask(  # type: ignore[attr-defined]
            f"Visitor Words for Forms - {site}",
            f"&{word.label}:",
            "Plain words, up to 300 characters. Leave it empty to use the plugin's own words. "
            f"QUILL suggests: {word.suggestion}",
            held.text(word.key),
        )
        if typed is None:
            return
        text = " ".join(typed.split())
        problem = vw.check_text(text)
        if problem:
            self.say(f"{problem} Nothing was changed.")
            return
        if text == held.text(word.key) or (not text and not held.changed(word.key)):
            self.say("That is how it is already. Nothing was changed.")
            return
        if not self._pl_preview(  # type: ignore[attr-defined]
            "Change Visitor Words",
            f"Change what visitors read on {site}'s forms.",
            vw.words_preview(held, word.key, text, site),
            "Save Words",
        ):
            return
        # A refusal or a conflict is said by the window's own failure handler.
        self.background(
            f"saving {site}'s visitor words",
            lambda: vw.save_words(api, _WRITE, held, word.key, text),
            self.say,
        )
