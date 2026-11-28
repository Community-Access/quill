"""SwiftLetter articles in the editor: open, save as a draft, compare and reopen.

A mixin of :class:`~quill.ui.wordpress_commands.WordPressCommands`, so QUILL and
QUILL Lite reach the same code. The Workbench's Open in Editor on an article row
calls :meth:`open_swiftletter`; File > WordPress > Save Draft to Site and Compare
with Site come here when the document in front is a SwiftLetter article.

What it promises (Michael's answers of 2026-11-22, ``docs/design/wordpress.md``):

- **Opens a working copy** through SwiftLetter's edit-context route, and says
  the title and review state. An account that cannot edit it, or a site that does
  not take saves from QUILL, opens it under the editor's Read-Only Guard and says so.
- **Saves a draft, never publishes**: title and content, with ``If-Match``.
  Nothing retries. When WordPress kept something other than what was sent, it
  says so and keeps the person's copy; the stored text becomes the next baseline.
- **A refusal is SwiftLetter's own sentence.** 412 offers Compare with Site and
  Reopen; a lock (409) names who has the article open; 428 and 400 say their
  message. The local draft is never touched by a refusal.

Wx is reached only through :mod:`quill.ui.wordpress_dialogs` and the host.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from quill.core.wordpress import local as lc
from quill.core.wordpress import swiftletter
from quill.core.wordpress import swiftletter_copy as sc
from quill.ui import wordpress_dialogs as dlg

if TYPE_CHECKING:
    from quill.core.wordpress import sites as st

__all__ = ["WordPressSwiftLetterCommands"]

_FORMATS = (
    "HTML, exactly as SwiftLetter has it",
    "Markdown, easier to read; anything Markdown cannot show is kept exactly",
)

_KEEP = "Keep editing"
_ROWS = {
    sc.COMPARE: "Compare with Site: hear what changed; nothing is sent",
    sc.REOPEN: "Reopen: replace your text with the site's copy; yours stays in Previous Versions",
    _KEEP: _KEEP,
}


def _soon(host: Any, text: str) -> None:
    """Say *text* once the document just opened has focus (``WordPressHost.announce_soon``)."""
    getattr(host, "announce_soon", host.announce)(text)


def _guard(host: Any, path: Path, guarded: bool) -> None:
    guard = getattr(host, "guard_document", None)
    if callable(guard):
        guard(path, guarded)


class WordPressSwiftLetterCommands:
    # Provided by WordPressCommands.
    host: Any
    local: lc.LocalStore

    # -- opening ---------------------------------------------------------------

    def open_swiftletter(
        self,
        profile: st.SiteProfile,
        article_id: int,
        *,
        can_edit: bool | None = None,
        can_save: bool = True,
        newsletter_title: str = "",
    ) -> None:
        """Open an article from the Workbench, or its working copy if one is here already.

        *can_edit* is the article row's hint (None: the site did not say, and
        SwiftLetter decides at save time); *can_save* is discovery's ``article_save``.
        """
        editable = can_edit is not False
        existing = self.local.find(profile.id, sc.KIND, article_id)
        if existing is not None:
            path = self.local.document_path(existing)
            if path.exists():
                # The site's hint can change (a role granted or taken away): follow it.
                allowed = editable and can_save
                if allowed != sc.can_save(existing):
                    sc.set_can_edit(existing, allowed)
                    self.local.save(existing)
                _guard(self.host, path, not allowed)
                self.host.open_path(path)
                self.watch_documents()  # type: ignore[attr-defined]
                _soon(self.host, sc.reopened_words(existing))
                return
        api = self.api(profile)  # type: ignore[attr-defined]

        def opened(article: swiftletter.Article) -> None:
            self._swiftletter_opened(
                profile, article, can_edit=editable, can_save=can_save, title=newsletter_title
            )

        self.background(  # type: ignore[attr-defined]
            f"opening the article from SwiftLetter on {profile.name}",
            lambda: swiftletter.open_article(api, article_id),
            opened,
        )

    def _swiftletter_opened(
        self,
        profile: st.SiteProfile,
        article: swiftletter.Article,
        *,
        can_edit: bool,
        can_save: bool,
        title: str,
    ) -> None:
        problem = sc.markdown_problem(sc.wordpress_void_tags(article.content))
        text_format = "html"
        if not problem:
            choice = dlg.ask_choice(
                self.host.parent,
                self.host.show_modal,
                title=f"Open {article.title or 'Untitled article'}",
                prompt="Open &as:",
                rows=_FORMATS,
                initial=1,
                help_text=(
                    "HTML keeps every block exactly. Markdown shows headings, links, lists and "
                    "picture descriptions plainly, and puts other blocks on short ::: lines; "
                    "SwiftLetter receives WordPress blocks either way."
                ),
            )
            if choice is None:
                return
            text_format = "markdown" if choice == 1 else "html"
        editable = can_edit and can_save
        copy = sc.copy_for(
            profile.id, article, text_format=text_format, can_edit=editable, newsletter_title=title
        )
        path = self.local.write_document(copy)
        self.local.add_version(copy, lc.REASON_OPENED)
        # The editor's own Read-Only Guard, set before the file opens so both editors
        # open it guarded, and cleared for an article the account may now edit.
        _guard(self.host, path, not editable)
        self.host.open_path(path)
        self.watch_documents()  # type: ignore[attr-defined]
        words = sc.opened_words(article, profile.name, can_edit=can_edit, can_save_here=can_save)
        if problem:
            words += f" It opened as HTML, because Markdown would change it. {problem}"
        _soon(self.host, words)

    # -- saving ----------------------------------------------------------------

    def swiftletter_send(
        self, copy: lc.WorkingCopy, profile: st.SiteProfile, *, publish: bool
    ) -> None:
        """Save Draft to Site (and Publish, which is refused) on a SwiftLetter article."""
        if publish:
            self.host.announce(sc.NEVER_PUBLISHES)
            return
        if not sc.can_save(copy):
            self.host.announce(
                f"This article opened read-only, so QUILL did not send it to SwiftLetter. {sc.KEPT}"
            )
            return
        if not self.host.save_current():
            return
        copy = self.local.copy_for_path(self.host.current_path()) or copy
        out = sc.outgoing(copy)
        if out.blocked:
            self.host.announce(out.blocked)
            return
        if sc.nothing_changed(copy, out.html):
            self.host.announce(
                f"Nothing to save: your copy matches the article SwiftLetter has on {profile.name}."
            )
            return
        base = sc.article_of(copy)
        api = self.api(profile)  # type: ignore[attr-defined]
        title, written = copy.title, copy.text

        def done(saved: swiftletter.SavedArticle) -> None:
            # Re-read: only the baseline changes here, and the person's file is never
            # rewritten. A working copy discarded while the save ran stays discarded.
            latest = self.local.find(profile.id, sc.KIND, copy.remote_id)
            words = sc.saved_words(latest or copy, saved, profile.name)
            if latest is not None:
                sc.record_saved(latest, saved)
                self.local.save(latest)
                self.local.add_version(latest, lc.REASON_SAVED, text=written, title=title)
            self.host.announce(words)

        self.host.run_task(
            "WordPress: saving to SwiftLetter",
            lambda: swiftletter.save_article_stored(api, base, title=title, content=out.html),
            done,
            lambda exc: self._swiftletter_refused(copy, profile, exc),
        )

    def _swiftletter_refused(
        self, copy: lc.WorkingCopy, profile: st.SiteProfile, exc: BaseException
    ) -> None:
        """Say SwiftLetter's sentence; after 412 or 428, offer what it names. Never retry."""
        said = sc.refusal(exc, site=profile.name)
        if not said.offers:
            self.host.announce(sc.with_kept(said.words))
            return
        rows = [*said.offers, _KEEP]
        # SwiftLetter's sentence is the dialog's text, not the list's label, so it is
        # read once as the dialog opens rather than on every return of focus.
        choice = dlg.ask_choice(
            self.host.parent,
            self.host.show_modal,
            title="Not Saved to SwiftLetter",
            message=sc.with_kept(said.words),
            prompt="&What now:",
            rows=[_ROWS[row] for row in rows],
            help_text=f"{sc.with_kept(said.words)} Nothing was sent again.",
        )
        picked = rows[choice] if choice is not None else ""
        if picked == sc.COMPARE:
            self.swiftletter_compare(copy, profile)
        elif picked == sc.REOPEN:
            self.swiftletter_reopen(copy, profile)

    # -- Compare with Site and Reopen -------------------------------------------

    def _in_front(self, copy: lc.WorkingCopy) -> lc.WorkingCopy:
        """*copy* with the editor's text when it is the document in front, so unsaved
        edits count in a comparison; otherwise as stored."""
        here = self.local.copy_for_path(self.host.current_path())
        if here is not None and here.key == copy.key:
            here.text = self.host.current_text()
            return here
        return copy

    def swiftletter_compare(self, copy: lc.WorkingCopy, profile: st.SiteProfile) -> None:
        """The site's current article against the person's copy, read through the edit
        route (Michael's answer 3). Read-only: nothing is sent, nothing local changes."""
        from quill.ui.wordpress_commands import compare_text

        copy = self._in_front(copy)
        out = sc.outgoing(copy)
        if out.blocked:
            self.host.announce(out.blocked.replace("Not saved to SwiftLetter", "Cannot compare"))
            return
        api = self.api(profile)  # type: ignore[attr-defined]
        base = sc.article_of(copy)

        def show(site: swiftletter.Article) -> None:
            text = sc.compare_report(
                site,
                copy,
                out.html,
                lambda theirs, ours: compare_text(theirs, ours, site_name=profile.name),
            )
            dlg.show_report(
                self.host.parent,
                self.host.show_modal,
                title="Compare with Site",
                text=text,
                help_text=(
                    "The article on the site against your copy. Nothing was sent; your copy in "
                    "QUILL is unchanged."
                ),
            )

        self.background(  # type: ignore[attr-defined]
            f"reading the article SwiftLetter has on {profile.name}",
            lambda: swiftletter.current_article(api, base),
            show,
        )

    def swiftletter_reopen(self, copy: lc.WorkingCopy, profile: st.SiteProfile) -> None:
        """Load the site's article into this document, as one undoable change.

        The person's text, as it is in the editor, is kept as a Previous Version
        first, and Undo brings it back. The site's version becomes the baseline only
        once the document is saved, so the next save is checked against what they
        have now seen.
        """
        api = self.api(profile)  # type: ignore[attr-defined]
        base = sc.article_of(copy)

        def loaded(site: swiftletter.Article) -> None:
            latest = self.local.copy_for_path(self.host.current_path())
            if latest is None or latest.key != copy.key:
                self.host.announce(
                    f"Switch to {copy.title or 'the article'} first; Reopen replaces its text."
                )
                return
            if not sc.can_save(latest):
                self.host.announce("This article opened read-only, so Reopen changed nothing.")
                return
            self.local.add_version(latest, lc.REASON_BEFORE_REOPEN, text=self.host.current_text())
            fresh = sc.copy_for(profile.id, site, text_format=latest.text_format, can_edit=True)
            sc.adopt_site(latest, fresh)
            self.host.replace_text(fresh.text)
            if not self.host.save_current():
                self.host.announce(
                    "The site's copy is in the document but could not be saved, so the next "
                    "save is still checked against the version you opened."
                )
                return
            self.local.save(latest)
            review = swiftletter.review_words(site.review_state)
            self.host.announce(
                f"Reopened {site.title or 'the article'} from SwiftLetter on {profile.name}. "
                f"{review}. Your text is in Previous Versions, and Undo brings it back."
            )

        self.background(  # type: ignore[attr-defined]
            f"reopening the article from SwiftLetter on {profile.name}",
            lambda: swiftletter.current_article(api, base),
            loaded,
        )
