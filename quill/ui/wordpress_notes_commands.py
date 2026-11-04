"""Notes on blocks: the Notes window and Add Note (wordpress.md 9.15, WordPress 6.9+).

A mixin of :class:`~quill.ui.wordpress_commands.WordPressCommands`. Editorial
notes people leave on a block in the block editor are comments of type
``note``; here they are a list that reads "Sam on the second paragraph:
tighten this", with Go to It, Reply and Resolve, and Add Note puts a new one
on the block at the caret. The thinking is in
:mod:`quill.core.wordpress.block_notes`.
"""

from __future__ import annotations

from dataclasses import replace
from typing import Any

from quill.core.wordpress import block_edit as be
from quill.core.wordpress import block_notes as bn
from quill.ui import wordpress_dialogs as dlg
from quill.ui.wordpress_api_base import WordPressApiBase

NOT_ON_SITE = (
    "This is not on {site} yet, so it has no notes. Save Draft to Site first, then notes can "
    "be read and added."
)


class WordPressNotesCommands(WordPressApiBase):
    def _note_doc(self) -> Any:
        doc = self._block_doc()  # type: ignore[attr-defined]
        if doc is None:
            return None
        if not doc.copy.remote_id:
            self.host.announce(NOT_ON_SITE.format(site=doc.profile.name))
            return None
        return doc

    # ------------------------------------------------------------------ #
    # the Notes window

    def cmd_notes(self) -> None:
        doc = self._note_doc()
        if doc is None:
            return
        post_id = int(doc.copy.remote_id)
        self.with_feature(
            doc.profile,
            "notes",
            f"reading notes on {doc.profile.name}",
            lambda api, _index, _account: (api, bn.threads(bn.list_notes(api, post_id))),
            lambda found: self._show_notes(doc, post_id, *found),
        )

    def _show_notes(self, doc: Any, post_id: int, api: Any, threads: list[bn.Thread]) -> None:
        site = doc.profile.name
        if not threads:
            self.host.announce(
                f"No notes on this {doc.copy.kind} on {site}. Add Note puts one on the block "
                "at the caret."
            )
            return
        bn.locate(self.host.current_text(), doc.fmt, threads, doc.islands)

        def rows() -> list[str]:
            return [t.spoken() for t in threads]

        def at(index: int | None) -> bn.Thread | None:
            return threads[index] if index is not None and index < len(threads) else None

        def go(index: int | None) -> object:
            thread = at(index)
            if thread is None:
                return None
            fresh = self._block_doc()  # type: ignore[attr-defined]
            if fresh is not None:
                bn.locate(fresh.text, fresh.fmt, [thread], fresh.islands)
            if thread.span is None or fresh is None:
                self.host.announce(
                    "That note's block is not in your copy. It may have been removed here, or "
                    "the note is on a newer version on the site."
                )
                return None
            self.host.go_to_offset(fresh.spans[thread.span].start)
            return dlg.CLOSE

        def reply(index: int | None) -> object:
            thread = at(index)
            if thread is None:
                return None
            text = dlg.ask_text(
                self.host.parent,
                self.host.show_modal,
                title=f"Reply to {thread.root.author_name}",
                prompt="&Reply:",
                multiline=True,
                help_text=(
                    "Your reply to this note. Notes are for the people editing the site; "
                    "visitors never see them."
                ),
            )
            if not text or not text.strip():
                return None
            words = text.strip()
            self.site_job(  # type: ignore[attr-defined]
                "replying to a note",
                lambda: bn.reply(api, post_id, thread, words),
                lambda _r: f"Reply to {thread.root.author_name}'s note saved on {site}.",
            )
            thread.replies.append(bn.Note(0, thread.root.id, "You", "", words, "approve"))
            return rows()

        def resolve(index: int | None) -> object:
            thread = at(index)
            if thread is None:
                return None
            resolving = not thread.resolved
            self.site_job(  # type: ignore[attr-defined]
                "resolving a note" if resolving else "reopening a note",
                lambda: bn.set_resolved(api, post_id, thread, resolving),
                lambda _r: (
                    f"{thread.root.author_name}'s note {'resolved' if resolving else 'reopened'}"
                    f" on {site}."
                ),
            )
            marker = "resolved" if resolving else "reopen"
            thread.root = replace(thread.root, status="hold" if resolving else "approve")
            thread.replies.append(bn.Note(0, thread.root.id, "You", "", "", "approve", marker))
            return rows()

        def add(_index: int | None) -> object:
            self.after_close(self.cmd_add_note)  # type: ignore[attr-defined]
            return dlg.CLOSE

        open_count = sum(1 for t in threads if not t.resolved)
        window = dlg.show_list_window(
            self.host.parent,
            self.host.show_modal,
            title=f"Notes, {site}",
            purpose=(
                f"The block editor's notes on this {doc.copy.kind}: {len(threads)}, {open_count} "
                "open. Each says who wrote it, on which block, and what it says. Visitors never "
                "see notes."
            ),
            list_label="&Notes:",
            list_help=(
                "Each note's author, the block it is on, its words, how many replies, and "
                "whether it is resolved. Enter goes to the block."
            ),
            rows=rows(),
            details=lambda i: threads[i].details(),
            on_enter=go,
            actions=[
                dlg.Action("&Go to It", "Close this with the caret on the note's block.", go),
                dlg.Action("&Reply...", "Answer the selected note.", reply),
                dlg.Action(
                    "Re&solve or Reopen",
                    "Mark the selected note resolved, or open it again if it already is.",
                    resolve,
                ),
                dlg.Action(
                    "&Add Note...",
                    "Close this and add a note on the block at the caret.",
                    add,
                    needs_row=False,
                ),
            ],
        )
        window.Destroy()

    # ------------------------------------------------------------------ #
    # Add Note

    def cmd_add_note(self) -> None:
        doc = self._note_doc()
        if doc is None:
            return
        index = self._block_at_caret(doc)  # type: ignore[attr-defined]
        if index is None:
            self.host.announce(
                "The caret is not in a block. Move to one with Next Block, then add the note."
            )
            return
        site = doc.profile.name
        place = bn.place_words(doc.spans, index)
        trial = be.replace_block(
            doc.text, doc.fmt, doc.spans, index, lambda b: bn.set_note_id(b, 1), doc.islands
        )
        if isinstance(trial, str):
            self.host.announce(trial)
            return
        if (
            doc.fmt != "html"
            and self._newly_protected(doc, index, trial)  # type: ignore[attr-defined]
            and not dlg.confirm(
                self.host.parent,
                self.host.show_modal,
                title="Add Note",
                message=(
                    "Markdown has no way to write which note belongs to a block, so this block "
                    "will become one protected line that keeps the note's link exactly. Its "
                    "words can then be changed only through WordPress or an HTML document. "
                    "Add the note?"
                ),
                yes_label="Add Note",
            )
        ):
            return
        text = dlg.ask_text(
            self.host.parent,
            self.host.show_modal,
            title=f"Add Note on {place.capitalize()}",
            prompt="&Note:",
            multiline=True,
            help_text=(
                f"A note on {place}, for the people editing {site}. Visitors never see it; "
                "people in the block editor see it beside the block."
            ),
        )
        if not text or not text.strip():
            return
        words = text.strip()
        post_id = int(doc.copy.remote_id)
        name = doc.spans[index].name

        def tie(note: bn.Note) -> None:
            now = self._block_doc()  # type: ignore[attr-defined]
            if now is None or index >= len(now.spans) or now.spans[index].name != name:
                self.host.announce(
                    f"Note added on {site}, but the block moved while it was sent, so it is not "
                    "tied to a block yet."
                )
                return
            edit = be.replace_block(
                now.text,
                now.fmt,
                now.spans,
                index,
                lambda b: bn.set_note_id(b, note.id),
                now.islands,
            )
            if isinstance(edit, str):
                self.host.announce(edit)
                return
            self._apply(now, edit)  # type: ignore[attr-defined]
            self.host.announce(
                f"Note added on {place} on {site}. Save Draft to Site or Publish to tie it to "
                "the block there."
            )

        self.with_feature(
            doc.profile,
            "notes",
            f"adding a note on {site}",
            lambda api, _index, _account: bn.add_note(api, post_id, words),
            tie,
        )
