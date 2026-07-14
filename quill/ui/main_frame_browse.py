"""Browse-mode navigation mixin for MainFrame (extracted for CQ-1).

This module holds the browse-mode element-navigation cluster that used to live
inline in ``main_frame.py``. The methods are unchanged; they were moved verbatim
into :class:`BrowseModeMixin`, which ``MainFrame`` inherits, so every call
resolves identically through the method-resolution order. No behavior changed;
this is a pure structural extraction proven by the existing main_frame tests.

The methods reference ``self`` attributes and helpers that live on
``MainFrame`` (``self.editor``, ``self.document``, ``self.settings``,
``self._wx``, ``self._bookmarks``, ``self._quill_feedback``,
``self._move_point``, ``self._location_ring``,
``self._record_location_before_jump``, ``self._parse_list_manager_line`` and the
``self._browse_prewarm_*`` / ``self._browse_cache_build_*`` state). They resolve
at runtime through the concrete ``MainFrame`` instance.
"""

from __future__ import annotations

import re
import threading

from quill.core.browser_preview import guess_preview_kind
from quill.core.links import infer_markup_kind
from quill.core.markdown_sections import parse_heading_blocks
from quill.core.marks import line_column_for_position
from quill.core.selection import line_span


class BrowseModeMixin:
    """Browse-mode element navigation, mixed into :class:`MainFrame`."""

    def _browse_navigation_context(self) -> dict[str, object]:
        text = self.editor.GetValue()
        markup_kind = infer_markup_kind(self.document.path)
        cache = self._browse_navigation_cache
        if (
            cache is not None
            and cache.get("text") == text
            and cache.get("markup_kind") == markup_kind
        ):
            return cache
        bookmarks = {
            name: int(position)
            for name, position in self._bookmarks.items()
            if isinstance(position, int)
        }
        cache = self._build_browse_navigation_cache(text, markup_kind, bookmarks)
        self._browse_navigation_cache = cache
        return cache

    def _build_browse_navigation_cache(
        self,
        text: str,
        markup_kind: str,
        bookmarks_map: dict[str, int],
    ) -> dict[str, object]:
        headings_by_level: dict[int, list[int]] = {level: [] for level in range(1, 7)}
        if markup_kind in {"markdown", "html"}:
            for heading in parse_heading_blocks(text, markup_kind):
                headings_by_level.setdefault(heading.level, []).append(heading.start)
        tables: list[int] = []
        block_quotes: list[int] = []
        code_blocks: list[int] = []
        bookmarks: list[int] = sorted(set(bookmarks_map.values()))
        lists: list[int] = []
        list_items: list[int] = []
        links = self._all_link_positions(text, markup_kind=markup_kind)
        if markup_kind == "html":
            for match in re.finditer(r"<(?:ul|ol)(?:\s+[^>]*)?>", text, flags=re.IGNORECASE):
                lists.append(match.start())
            for match in re.finditer(r"<li(?:\s+[^>]*)?>", text, flags=re.IGNORECASE):
                list_items.append(match.start())
            for match in re.finditer(r"<table(?:\s+[^>]*)?>", text, flags=re.IGNORECASE):
                tables.append(match.start())
            for match in re.finditer(r"<blockquote(?:\s+[^>]*)?>", text, flags=re.IGNORECASE):
                block_quotes.append(match.start())
            for match in re.finditer(r"<(?:pre|code)(?:\s+[^>]*)?>", text, flags=re.IGNORECASE):
                code_blocks.append(match.start())
        else:
            line_start = 0
            previous_line_is_list = False
            previous_line_is_table = False
            previous_line_is_quote = False
            for raw_line in text.splitlines(keepends=True):
                is_list_line = self._parse_list_manager_line(raw_line) is not None
                if is_list_line and not previous_line_is_list:
                    lists.append(line_start)
                if is_list_line:
                    list_items.append(line_start)
                previous_line_is_list = is_list_line
                line_text = raw_line.rstrip("\r\n")
                is_table_line = bool(
                    re.match(r"^\s*\|.+\|\s*$", line_text)
                    or re.match(r"^\s*\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)+\|?\s*$", line_text)
                )
                if is_table_line and not previous_line_is_table:
                    tables.append(line_start)
                previous_line_is_table = is_table_line
                is_quote_line = bool(re.match(r"^\s*>\s*", line_text))
                if is_quote_line and not previous_line_is_quote:
                    block_quotes.append(line_start)
                previous_line_is_quote = is_quote_line
                line_start += len(raw_line)
            for match in re.finditer(r"(?m)^\s*(?:```|~~~)", text):
                code_blocks.append(match.start())
        paragraph_spans = self._all_paragraph_spans(text, markup_kind=markup_kind)
        sentence_spans = self._all_sentence_spans(text)
        cache = {
            "text": text,
            "markup_kind": markup_kind,
            "headings_by_level": headings_by_level,
            "links": links,
            "tables": tables,
            "block_quotes": block_quotes,
            "bookmarks": bookmarks,
            "code_blocks": sorted(set(code_blocks)),
            "lists": lists,
            "list_items": list_items,
            "paragraph_spans": paragraph_spans,
            "sentence_spans": sentence_spans,
        }
        return cache

    def _refresh_browse_navigation_cache_now(self) -> None:
        self._browse_navigation_cache = None
        self._browse_navigation_context()

    def _quick_nav_panel_context(self) -> dict[str, object]:
        """Browse nav context plus the on-demand transient nav types for the
        Quick Nav panel: misspellings and active-search hits (#513).

        These are computed here, not in the prewarmed browse cache, so the
        perf-critical navigation cache stays light -- they only matter when the
        user opens the panel. Failures degrade to "none", never breaking Quick Nav.
        """
        context = dict(self._browse_navigation_context())
        text = str(context.get("text", ""))
        try:
            from quill.core.spellcheck import list_misspellings

            context["misspellings"] = [
                m.start for m in list_misspellings(text, self._spell_dictionary())
            ]
        except Exception:  # noqa: BLE001 - a spell-check hiccup must never break Quick Nav
            context["misspellings"] = []
        query = str(getattr(self, "_last_find_query", "") or "")
        if query:
            try:
                from quill.core.search import find_matches

                options = getattr(self, "_last_search_options", None)
                context["search_hits"] = [s for s, _ in find_matches(text, query, options)]
            except Exception:  # noqa: BLE001 - never let a bad pattern break Quick Nav
                context["search_hits"] = []
        return context
        self._quill_feedback(
            "QUILL browse cache refreshed",
            status_message="QUILL browse cache refreshed",
            sound_kind="move",
        )

    def _schedule_browse_prewarm(self, *, force: bool = False) -> None:
        if not bool(getattr(self.settings, "browse_mode_preload_cache", True)):
            return
        text = self.editor.GetValue()
        if not force and len(text) < self._browse_prewarm_large_document_threshold:
            return
        self._browse_prewarm_request_force = self._browse_prewarm_request_force or force
        wx = self._wx
        existing = self._browse_prewarm_call_later
        stop = getattr(existing, "Stop", None)
        if callable(stop):
            stop()
        call_later = getattr(wx, "CallLater", None)
        if not callable(call_later):
            return
        self._browse_prewarm_call_later = call_later(
            self._browse_prewarm_delay_ms,
            self._run_browse_prewarm,
        )

    def _run_browse_prewarm(self) -> None:
        force = bool(self._browse_prewarm_request_force)
        self._browse_prewarm_request_force = False
        try:
            if not bool(getattr(self.settings, "browse_mode_preload_cache", True)):
                return
            text = self.editor.GetValue()
            if not force and len(text) < self._browse_prewarm_large_document_threshold:
                return
            markup_kind = infer_markup_kind(self.document.path)
            bookmarks = {
                name: int(position)
                for name, position in self._bookmarks.items()
                if isinstance(position, int)
            }
            self._browse_cache_build_generation += 1
            generation = self._browse_cache_build_generation

            old_cancel = getattr(self, "_browse_cache_cancel_event", None)
            if old_cancel is not None:
                old_cancel.set()
            cancel_event = threading.Event()
            self._browse_cache_cancel_event = cancel_event

            def _worker() -> None:
                cache = self._build_browse_navigation_cache(text, markup_kind, bookmarks)
                if cancel_event.is_set():
                    return
                self._wx.CallAfter(
                    self._accept_browse_prewarm_cache,
                    generation,
                    text,
                    markup_kind,
                    cache,
                )

            self._browse_cache_build_thread = threading.Thread(  # GATE-40-OK: browse cache prewarm.
                target=_worker,
                name="quill-browse-cache-prewarm",
                daemon=True,
            )
            self._browse_cache_build_thread.start()
        finally:
            self._browse_prewarm_call_later = None

    def _accept_browse_prewarm_cache(
        self,
        generation: int,
        text_snapshot: str,
        markup_kind_snapshot: str,
        cache: dict[str, object],
    ) -> None:
        if generation != self._browse_cache_build_generation:
            return
        if self.editor.GetValue() != text_snapshot:
            return
        if infer_markup_kind(self.document.path) != markup_kind_snapshot:
            return
        self._browse_navigation_cache = cache

    def _all_link_positions(self, text: str, *, markup_kind: str) -> list[int]:
        positions: list[int] = []
        if markup_kind == "html":
            for match in re.finditer(r"<a\s+[^>]*href\s*=", text, flags=re.IGNORECASE):
                positions.append(match.start())
            return positions
        for match in re.finditer(r"\[[^\]]+\]\([^\)]+\)", text):
            positions.append(match.start())
        for match in re.finditer(r"<https?://[^>]+>", text, flags=re.IGNORECASE):
            positions.append(match.start())
        for match in re.finditer(r"https?://[^\s\)\]\>]+", text, flags=re.IGNORECASE):
            positions.append(match.start())
        return sorted(set(positions))

    def _all_paragraph_spans(self, text: str, *, markup_kind: str) -> list[tuple[int, int]]:
        if markup_kind == "html":
            spans: list[tuple[int, int]] = []
            paragraph_pattern = re.compile(
                r"<(?:p|li|blockquote|pre|h[1-6]|td|th)(?:\s+[^>]*)?>",
                flags=re.IGNORECASE,
            )
            for match in paragraph_pattern.finditer(text):
                spans.append((match.start(), match.start()))
            if spans:
                return spans
        spans: list[tuple[int, int]] = []
        offset = 0
        for chunk in text.split("\n\n"):
            spans.append((offset, offset + len(chunk)))
            offset += len(chunk) + 2
        return spans

    def _all_sentence_spans(self, text: str) -> list[tuple[int, int]]:
        spans: list[tuple[int, int]] = []
        pattern = re.compile(r".+?(?:[.!?](?:[\]\)\"']+)?(?:\s+|$)|$)", re.DOTALL)
        for match in pattern.finditer(text):
            start, end = match.span()
            if start == end:
                continue
            spans.append((start, end))
        return spans

    def _browse_heading_level(self, level: int, *, reverse: bool) -> None:
        context = self._browse_navigation_context()
        markup_kind = context["markup_kind"]
        if markup_kind not in {"markdown", "html"}:
            self._browse_unsupported("heading levels", markup_kind)
            return
        headings = list(context["headings_by_level"].get(level, []))
        if not headings:
            self._browse_not_found(f"heading level {level}", markup_kind)
            return
        self._browse_jump_to_positions(headings, f"heading level {level}", reverse=reverse)

    def _browse_link(self, *, reverse: bool) -> None:
        context = self._browse_navigation_context()
        positions = list(context["links"])
        if not positions:
            self._browse_not_found(
                "links", guess_preview_kind(self.document.path, self.editor.GetValue())
            )
            return
        self._browse_jump_to_positions(positions, "link", reverse=reverse)

    def _browse_list(self, *, reverse: bool) -> None:
        context = self._browse_navigation_context()
        positions = list(context["lists"])
        if not positions:
            self._browse_not_found(
                "lists", guess_preview_kind(self.document.path, self.editor.GetValue())
            )
            return
        self._browse_jump_to_positions(positions, "list", reverse=reverse)

    def _browse_list_item(self, *, reverse: bool) -> None:
        context = self._browse_navigation_context()
        positions = list(context["list_items"])
        if not positions:
            self._browse_not_found(
                "list items", guess_preview_kind(self.document.path, self.editor.GetValue())
            )
            return
        self._browse_jump_to_positions(positions, "list item", reverse=reverse)

    def _browse_table(self, *, reverse: bool) -> None:
        context = self._browse_navigation_context()
        positions = list(context["tables"])
        if not positions:
            self._browse_not_found(
                "tables", guess_preview_kind(self.document.path, self.editor.GetValue())
            )
            return
        self._browse_jump_to_positions(positions, "table", reverse=reverse)

    def _browse_block_quote(self, *, reverse: bool) -> None:
        context = self._browse_navigation_context()
        positions = list(context["block_quotes"])
        if not positions:
            self._browse_not_found(
                "block quotes", guess_preview_kind(self.document.path, self.editor.GetValue())
            )
            return
        self._browse_jump_to_positions(positions, "block quote", reverse=reverse)

    def _browse_bookmark(self, *, reverse: bool) -> None:
        context = self._browse_navigation_context()
        positions = list(context["bookmarks"])
        if not positions:
            self._browse_not_found(
                "bookmarks", guess_preview_kind(self.document.path, self.editor.GetValue())
            )
            return
        self._browse_jump_to_positions(positions, "bookmark", reverse=reverse)

    def _browse_code_block(self, *, reverse: bool) -> None:
        context = self._browse_navigation_context()
        positions = list(context["code_blocks"])
        if not positions:
            self._browse_not_found(
                "code blocks", guess_preview_kind(self.document.path, self.editor.GetValue())
            )
            return
        self._browse_jump_to_positions(positions, "code block", reverse=reverse)

    def _browse_skip_container(self, *, reverse: bool) -> None:
        text = self.editor.GetValue()
        cursor = self.editor.GetInsertionPoint()
        line_start, _line_end = line_span(text, cursor)
        starts: list[int] = [0]
        for index, character in enumerate(text):
            if character == "\n":
                starts.append(index + 1)
        current_index = 0
        for index, start in enumerate(starts):
            if start <= line_start:
                current_index = index
            else:
                break

        def line_text(line_index: int) -> str:
            start = starts[line_index]
            end = starts[line_index + 1] if line_index + 1 < len(starts) else len(text)
            return text[start:end].rstrip("\r\n")

        def container_kind(value: str) -> str | None:
            if self._parse_list_manager_line(value) is not None:
                return "list"
            if bool(
                re.match(r"^\s*\|.+\|\s*$", value)
                or re.match(r"^\s*\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)+\|?\s*$", value)
            ):
                return "table"
            if bool(re.search(r"<li(?:\s+[^>]*)?>|<(?:ul|ol)(?:\s+[^>]*)?>", value, re.IGNORECASE)):
                return "list"
            if bool(re.search(r"<table(?:\s+[^>]*)?>", value, re.IGNORECASE)):
                return "table"
            return None

        kind = container_kind(line_text(current_index))
        if kind is None:
            self._browse_not_found(
                "list or table at cursor", guess_preview_kind(self.document.path, text)
            )
            return

        def is_same_kind(line_index: int) -> bool:
            return container_kind(line_text(line_index)) == kind

        top = current_index
        while top > 0 and is_same_kind(top - 1):
            top -= 1
        bottom = current_index
        while bottom + 1 < len(starts) and is_same_kind(bottom + 1):
            bottom += 1

        if reverse:
            if top == 0:
                self._browse_not_found(
                    "previous line before container", guess_preview_kind(self.document.path, text)
                )
                return
            target = starts[top - 1]
            label = "previous line before"
        else:
            if bottom + 1 >= len(starts):
                self._browse_not_found(
                    "next line after container", guess_preview_kind(self.document.path, text)
                )
                return
            target = starts[bottom + 1]
            label = "next line after"

        self._record_location_before_jump()
        self._move_point(target)
        self.editor.SetFocus()
        self._location_ring.record(target)
        line, column = line_column_for_position(text, target)
        self._browse_feedback_move(f"Moved to {label} {kind}", line, column)

    def _browse_paragraph(self, *, reverse: bool) -> None:
        positions = [start for start, _end in self._browse_navigation_context()["paragraph_spans"]]
        if not positions:
            self._browse_not_found(
                "paragraphs", guess_preview_kind(self.document.path, self.editor.GetValue())
            )
            return
        self._browse_jump_to_positions(positions, "paragraph", reverse=reverse)

    def _browse_sentence(self, *, reverse: bool) -> None:
        positions = [start for start, _end in self._browse_navigation_context()["sentence_spans"]]
        if not positions:
            self._browse_not_found(
                "sentences", guess_preview_kind(self.document.path, self.editor.GetValue())
            )
            return
        self._browse_jump_to_positions(positions, "sentence", reverse=reverse)

    def _browse_jump_to_positions(self, positions: list[int], noun: str, *, reverse: bool) -> None:
        cursor = self.editor.GetInsertionPoint()
        sorted_positions = sorted(pos for pos in positions if pos >= 0)
        if not sorted_positions:
            self._browse_not_found(
                noun, guess_preview_kind(self.document.path, self.editor.GetValue())
            )
            return
        target: int | None = None
        if reverse:
            for candidate in reversed(sorted_positions):
                if candidate < cursor:
                    target = candidate
                    break
            if target is None and bool(getattr(self.settings, "browse_mode_wrap", True)):
                target = sorted_positions[-1]
        else:
            for candidate in sorted_positions:
                if candidate > cursor:
                    target = candidate
                    break
            if target is None and bool(getattr(self.settings, "browse_mode_wrap", True)):
                target = sorted_positions[0]
        if target is None:
            direction = "previous" if reverse else "next"
            self._browse_not_found(
                f"{direction} {noun}",
                guess_preview_kind(self.document.path, self.editor.GetValue()),
            )
            return
        self._record_location_before_jump()
        self._move_point(target)
        self.editor.SetFocus()
        self._location_ring.record(target)
        line, column = line_column_for_position(self.editor.GetValue(), target)
        direction = "previous" if reverse else "next"
        self._browse_feedback_move(f"Moved to {direction} {noun}", line, column)

    def _browse_feedback_move(self, prefix: str, line: int, column: int) -> None:
        detail = str(getattr(self.settings, "browse_mode_move_detail", "position")).strip().lower()
        if detail == "none":
            return
        if detail == "line":
            message = f"{prefix} at line {line}"
        else:
            message = f"{prefix} at line {line}, column {column}"
        self._quill_feedback(message, status_message=message, sound_kind="move")

    def _browse_not_found(self, noun: str, surface: str) -> None:
        detail = self._browse_surface_context(surface)
        self._quill_feedback(
            f"No {noun} found in this {detail}.",
            status_message=f"No {noun} found",
            sound_kind="error",
        )

    def _browse_unsupported(self, noun: str, surface: str) -> None:
        detail = self._browse_surface_context(surface)
        self._quill_feedback(
            f"Browse mode cannot move by {noun} in this {detail}.",
            status_message=f"No {noun} available",
            sound_kind="error",
        )

    def _browse_surface_context(self, surface: str) -> str:
        if surface == "markdown":
            return "Markdown document"
        if surface == "html":
            return "HTML document"
        if surface == "plain":
            return "plain text document"
        return f"{surface} document"
