"""File > WordPress > Blocks: inserting, moving through and changing blocks (wordpress.md 8).

A mixin of :class:`~quill.ui.wordpress_commands.WordPressCommands`, shared by
QUILL and QUILL Lite; it reaches the editor only through ``self.host``.

All the thinking is in the wx-free core: where blocks are
(:mod:`~quill.core.wordpress.block_spans`), how to change one without
touching the rest (:mod:`~quill.core.wordpress.block_edit`), what can be
inserted (:mod:`~quill.core.wordpress.block_catalog`), settings and colours
(:mod:`~quill.core.wordpress.block_settings`) and the site's preview
(:mod:`~quill.core.wordpress.block_preview`). Every change reaches the editor
as one ``replace_text`` or one ``insert_text``, so one Undo takes it back.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from quill.core.wordpress import block_catalog as bc
from quill.core.wordpress import block_edit as be
from quill.core.wordpress import block_settings as bset
from quill.core.wordpress import block_spans as bs
from quill.core.wordpress.block_preview import PreviewResult, render_preview
from quill.ui import wordpress_block_dialogs as bdlg
from quill.ui import wordpress_dialogs as dlg

NO_BLOCKS = "This document has no blocks yet. Insert one with Insert Block."
_ISLAND = re.compile(r"^:::[ \t]+block[ \t]", re.M)


@dataclass
class _Doc:
    copy: Any
    profile: Any
    text: str
    fmt: str
    islands: dict[str, str]
    spans: list[bs.Span]

    def describe(self, index: int) -> str:
        return bs.describe_span(self.text, self.fmt, self.spans, index, self.islands)


class WordPressBlockCommands:
    host: Any

    # ------------------------------------------------------------------ #
    # plumbing

    def _block_doc(self) -> _Doc | None:
        found = self.current()  # type: ignore[attr-defined]
        if found is None:
            return None
        copy, profile = found
        text = self.host.current_text()
        fmt = "html" if copy.text_format == "html" else "markdown"
        islands = dict(copy.properties.get("islands") or {})
        return _Doc(copy, profile, text, fmt, islands, bs.spans_for(text, fmt))

    def _keep_islands(self, doc: _Doc, added: dict[str, str]) -> None:
        if not added:
            return
        doc.copy.properties["islands"] = {**doc.islands, **added}
        self.local.save(doc.copy)  # type: ignore[attr-defined]

    def _apply(self, doc: _Doc, edit: be.Edit) -> None:
        self.host.replace_text(edit.text)
        self.host.go_to_offset(edit.caret)
        self._keep_islands(doc, edit.islands)

    # ------------------------------------------------------------------ #
    # Insert Block (8.2)

    def cmd_insert_block(self) -> None:
        doc = self._block_doc()
        if doc is None:
            return
        api = self.api(doc.profile)  # type: ignore[attr-defined]

        def show(choices: list[bc.InsertChoice]) -> None:
            current = list(choices)

            def narrow(words: str) -> list[str]:
                current[:] = bc.filter_choices(choices, words)
                return [c.row() for c in current]

            def insert(index: int | None) -> object:
                if index is None or index >= len(current):
                    return None
                return dlg.CLOSE if self._insert_choice(current[index]) else None

            window = dlg.show_list_window(
                self.host.parent,
                self.host.show_modal,
                title="Insert Block",
                purpose=(
                    f"The blocks you can insert on {doc.profile.name}: QUILL's own core blocks "
                    "first, then the site's other blocks, its patterns and its synced patterns."
                ),
                list_label="&Blocks:",
                list_help="Each block's name and what it is for. Press Insert to add it.",
                rows=[c.row() for c in current],
                actions=[
                    dlg.Action(
                        "&Insert",
                        "Add the selected block after the block the caret is in.",
                        insert,
                    )
                ],
                filter_label="&Find:",
                filter_help='Type part of a name and press Enter. "but" finds Button.',
                on_filter=narrow,
            )
            window.Destroy()

        self.background(
            "loading the site's blocks and patterns", lambda: bc.fetch_choices(api), show
        )  # type: ignore[attr-defined]

    def _insert_choice(self, choice: bc.InsertChoice) -> bool:
        fields = bc.fields_for(choice)
        answers: dict[str, Any] = {}
        if fields:
            got = bdlg.ask_fields(
                self.host.parent,
                self.host.show_modal,
                title=f"Insert {choice.title}",
                purpose=f"What the new {choice.title} block needs. Everything else can wait.",
                fields=fields,
                ok_label="Insert",
            )
            if got is None:
                return False
            answers = got
        markup = bc.build_markup(choice, answers)
        if not markup.strip():
            self.host.announce(f"{choice.title} has nothing to insert.")
            return False
        doc = self._block_doc()
        if doc is None:
            return False
        at, inserted, caret, added = be.insert_markup(
            doc.text, doc.fmt, doc.spans, self.host.caret_offset(), markup, doc.islands
        )
        self.host.go_to_offset(at)
        self.host.insert_text(inserted)
        self.host.go_to_offset(caret)
        self._keep_islands(doc, added)
        self.host.announce(f"{choice.title} inserted.")
        return True

    # ------------------------------------------------------------------ #
    # Moving through blocks (8.3)

    def cmd_next_block(self) -> None:
        self._step(1)

    def cmd_previous_block(self) -> None:
        self._step(-1)

    def _step(self, direction: int) -> None:
        doc = self._block_doc()
        if doc is None:
            return
        stops = bs.stops(doc.spans)
        if not stops:
            self.host.announce(NO_BLOCKS)
            return
        caret = self.host.caret_offset()
        if direction > 0:
            index = bs.next_stop(doc.spans, caret)
            if index is None:
                self.host.announce("No more blocks after this one.")
                return
        else:
            index = bs.previous_stop(doc.spans, caret)
            if index is None:
                self.host.announce("No blocks before this one.")
                return
        self.host.go_to_offset(doc.spans[index].start)
        position = stops.index(index) + 1
        self.host.announce(bs.spoken_move(doc.describe(index), position, len(stops)))

    def cmd_where_am_i(self) -> None:
        doc = self._block_doc()
        if doc is None:
            return
        if not doc.spans:
            self.host.announce(NO_BLOCKS)
            return
        self.host.announce(
            bs.where_am_i(doc.text, doc.fmt, doc.spans, self.host.caret_offset(), doc.islands)
        )

    # ------------------------------------------------------------------ #
    # The Blocks window (8.3, 8.5)

    def cmd_blocks_window(self) -> None:
        doc = self._block_doc()
        if doc is None:
            return
        if not bs.stops(doc.spans):
            self.host.announce(NO_BLOCKS)
            return

        def fresh() -> _Doc | None:
            return self._block_doc()

        def rows() -> list[str]:
            now = fresh()
            if now is None:
                return []
            out = []
            for i in bs.stops(now.spans):
                row = now.describe(i)
                parent = now.spans[i].parent
                if parent is not None:
                    row += f", inside {bs.label(now.spans[parent].name)}"
                out.append(row)
            return out

        def chosen(row: int | None) -> tuple[_Doc, int] | None:
            now = fresh()
            if now is None or row is None:
                return None
            stops = bs.stops(now.spans)
            return (now, stops[row]) if row < len(stops) else None

        def done(now: _Doc, result: be.Edit | str, said: str) -> object:
            if isinstance(result, str):
                self.host.announce(result)
                return None
            self._apply(now, result)
            if said:
                self.host.announce(said)
            return rows()

        def go_to(row: int | None) -> object:
            found = chosen(row)
            if found is None:
                return None
            now, index = found
            self.host.go_to_offset(now.spans[index].start)
            return dlg.CLOSE

        def mover(step: int) -> Any:
            def run(row: int | None) -> object:
                found = chosen(row)
                if found is None:
                    return None
                now, index = found
                said = "Moved up." if step < 0 else "Moved down."
                return done(now, be.move(now.text, now.spans, index, step), said)

            return run

        def duplicate(row: int | None) -> object:
            found = chosen(row)
            if found is None:
                return None
            now, index = found
            edit = be.duplicate(now.text, now.fmt, now.spans, index, now.islands)
            return done(now, edit, "Duplicated. The copy is straight after it.")

        def remove(row: int | None) -> object:
            found = chosen(row)
            if found is None:
                return None
            now, index = found
            if not dlg.confirm(
                self.host.parent,
                self.host.show_modal,
                title="Remove Block",
                message=(
                    f"Remove {now.describe(index)} from this document? Undo in the editor "
                    "brings it back. Nothing changes on the site until you send it."
                ),
                yes_label="Remove Block",
            ):
                return None
            return done(now, be.remove(now.text, now.spans, index), "Block removed.")

        def change(row: int | None) -> object:
            found = chosen(row)
            if found is None:
                return None
            now, index = found
            targets = be.change_targets(now.spans[index].name)
            if not targets:
                self.host.announce("QUILL cannot change this kind of block to another.")
                return None
            picked = dlg.ask_choice(
                self.host.parent,
                self.host.show_modal,
                title="Change To",
                prompt="&Kind of block:",
                rows=[t for _key, t in targets],
                help_text="What this block becomes. Its words are kept.",
            )
            if picked is None:
                return None
            key, spoken = targets[picked]
            edit = be.change_to(now.text, now.fmt, now.spans, index, key)
            return done(now, edit, f"Changed to {spoken}.")

        def group(row: int | None) -> object:
            found = chosen(row)
            if found is None:
                return None
            now, index = found
            return done(now, be.group(now.text, now.fmt, now.spans, index), "Grouped.")

        def ungroup(row: int | None) -> object:
            found = chosen(row)
            if found is None:
                return None
            now, index = found
            return done(now, be.ungroup(now.text, now.spans, index), "Ungrouped.")

        window = dlg.show_list_window(
            self.host.parent,
            self.host.show_modal,
            title="Blocks",
            purpose=(
                "Every block in this document, in order. Each change here is one step that "
                "Undo in the editor takes back, and nothing else in the document moves."
            ),
            list_label="&Blocks:",
            list_help="Each block's kind and its first words; nested blocks say what they are in.",
            rows=rows(),
            actions=[
                dlg.Action("&Go To", "Close this window and put the caret on the block.", go_to),
                dlg.Action("Move &Up", "Swap the block with the one before it.", mover(-1)),
                dlg.Action("Move Do&wn", "Swap the block with the one after it.", mover(1)),
                dlg.Action("&Duplicate", "Put a copy of the block straight after it.", duplicate),
                dlg.Action("&Remove...", "Take the block out of the document.", remove),
                dlg.Action("&Change To...", "Make it a heading, a list, paragraphs...", change),
                dlg.Action("Gr&oup", "Put the block inside a new Group block.", group),
                dlg.Action("U&ngroup", "Replace a Group block by what is inside it.", ungroup),
            ],
        )
        window.Destroy()

    # ------------------------------------------------------------------ #
    # Block Settings (8.4, 9.7)

    def _block_at_caret(self, doc: _Doc) -> int | None:
        index = bs.innermost_at(doc.spans, self.host.caret_offset())
        if index is not None and doc.spans[index].name in bs.NOT_A_STOP:
            index = doc.spans[index].parent
        return index

    def cmd_block_settings(self) -> None:
        doc = self._block_doc()
        if doc is None:
            return
        if self._block_at_caret(doc) is None:
            self.host.announce(
                "The caret is not in a block. Move to one with Next Block, then try again."
            )
            return
        api = self.api(doc.profile)  # type: ignore[attr-defined]
        site = doc.profile.name

        def show(presets: bset.ThemePresets | None) -> None:
            now = self._block_doc()
            index = self._block_at_caret(now) if now is not None else None
            if now is None or index is None:
                return
            block = bs.block_at(now.text, now.fmt, now.spans, index, now.islands)
            if block is None:
                self.host.announce("QUILL could not read this block.")
                return
            fields = bset.settings_fields(block, presets)
            if not fields:
                self.host.announce("This block has no settings QUILL can change.")
                return
            no_colours = "" if presets else f" {site} did not share its theme's colours."
            answers = bdlg.ask_fields(
                self.host.parent,
                self.host.show_modal,
                title="Block Settings",
                purpose=f"The settings of this {bs.label(block.name or '')} block.{no_colours}",
                fields=fields,
            )
            if answers is None:
                return
            edit = be.replace_block(
                now.text,
                now.fmt,
                now.spans,
                index,
                lambda b: bset.apply_settings(b, answers),
                now.islands,
            )
            if isinstance(edit, str):
                self.host.announce(edit)
                return
            if (
                now.fmt != "html"
                and self._newly_protected(now, index, edit)
                and not dlg.confirm(
                    self.host.parent,
                    self.host.show_modal,
                    title="Block Settings",
                    message=(
                        "Markdown has no way to write these settings, so this block will "
                        "become one protected line that keeps them exactly. Its words can then "
                        "be changed only through WordPress or an HTML document. Change it?"
                    ),
                    yes_label="Make Protected Block",
                )
            ):
                return
            self._apply(now, edit)
            changed = bs.block_at(
                edit.text,
                now.fmt,
                bs.spans_for(edit.text, now.fmt),
                index,
                {**now.islands, **edit.islands},
            )
            warning = bset.contrast_warning(changed.attrs if changed else {}, presets)
            self.host.announce("Block settings changed." + (f" {warning}" if warning else ""))

        self.background("reading the theme's colours", lambda: bset.fetch_presets(api), show)  # type: ignore[attr-defined]

    @staticmethod
    def _newly_protected(doc: _Doc, index: int, edit: be.Edit) -> bool:
        top = index
        while doc.spans[top].parent is not None:
            top = doc.spans[top].parent  # type: ignore[assignment]
        span = doc.spans[top]
        before = len(_ISLAND.findall(doc.text[span.start : span.end]))
        after_text = edit.text[span.start : len(edit.text) - (len(doc.text) - span.end)]
        return len(_ISLAND.findall(after_text)) > before

    # ------------------------------------------------------------------ #
    # Preview Blocks (8.5)

    def cmd_preview_blocks(self) -> None:
        doc = self._block_doc()
        if doc is None:
            return
        if doc.fmt == "html":
            html = doc.text
        else:
            from quill.core.wordpress.fences import convert_markdown

            html = convert_markdown(doc.text, doc.islands).html
        api = self.api(doc.profile)  # type: ignore[attr-defined]
        site = doc.profile.name

        def show(result: PreviewResult) -> None:
            dlg.show_report(
                self.host.parent,
                self.host.show_modal,
                title="Preview Blocks",
                text=result.readout or "(The page is empty.)",
                help_text=(
                    f"This document as {site} renders its blocks, as plain text in reading "
                    "order. Nothing was saved to make it."
                ),
            )
            if result.failed:
                count = len(result.failed)
                self.host.announce(
                    f"{site} could not show {count} block{'s' if count != 1 else ''}: "
                    f"{result.failed[0]}"
                )

        self.background(
            "rendering the blocks",
            lambda: render_preview(html, api, int(doc.copy.remote_id or 0)),
            show,
        )
