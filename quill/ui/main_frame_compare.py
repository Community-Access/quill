"""Document compare for MainFrame (#193/#194, CQ-1 decomposition).

``CompareMixin`` owns keyboard-first diff work: the compare-with-file and
compare-open-documents entry points, the difference navigation and
announcement commands, the difference-list dialog, ignore-whitespace and
synchronization toggles, the summary-report tab, and the session model
(``_CompareSession`` / ``_CompareDifferenceGroup`` / ``_CompareLineBlock``).
Extracted verbatim from ``main_frame.py``; runs on ``MainFrame`` (``self``).
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path

from quill.core.diffing import build_unified_diff
from quill.core.document import Document
from quill.io.text import read_text_document


@dataclass(slots=True)
class _CompareLineBlock:
    document_name: str
    start_line: int | None
    end_line: int | None
    text: list[str]


@dataclass(slots=True)
class _CompareDifferenceGroup:
    index: int
    kind: str
    blocks: list[_CompareLineBlock]


@dataclass(slots=True)
class _CompareSession:
    source_documents: list[tuple[str, str]]
    groups: list[_CompareDifferenceGroup]
    current_index: int = 0
    synchronized_navigation: bool = True


class CompareMixin:
    def compare_start_with_file(self, path: object = None) -> None:
        from quill.core.compare_service import CompareOptions, CompareService
        from quill.ui.compare_dialog import CompareDialog

        wx = self._wx
        right_path: Path | None = path if isinstance(path, Path) else None
        if right_path is None:
            with wx.FileDialog(
                self.frame,
                "Compare with file",
                wildcard="All files (*.*)|*.*",
                style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
            ) as dlg:
                if self._show_modal_dialog(dlg, "Compare with file") != wx.ID_OK:
                    return
                right_path = Path(dlg.GetPath())
        left_text = self.editor.GetValue()
        try:
            right_text = right_path.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            self._set_status(f"Cannot read {right_path.name}: {exc}")
            return
        svc = CompareService()
        opts = getattr(self, "_compare_options", CompareOptions())
        left_label = self.document.name or "Left"
        right_label = right_path.name
        groups = svc.compare(
            left_text,
            right_text,
            left_label=left_label,
            right_label=right_label,
            left_path=self.document.path,
            right_path=right_path,
            options=opts,
        )
        self._compare_service = svc
        self._compare_left_text = left_text
        self._compare_right_text = right_text
        if not groups:
            msg = "No differences found."
            if opts.ignore_all_whitespace or opts.ignore_trailing_whitespace:
                msg += " (whitespace ignored)"
            self._announce(msg)
            self._set_status(msg)
            return
        dlg = CompareDialog(self.frame, svc)
        self._show_modal_dialog(dlg, "Compare")
        dlg.Destroy()
        self._compare_service = None

    def compare_dialog_next(self) -> None:
        svc = getattr(self, "_compare_service", None)
        if svc is None:
            self._announce("Not in compare mode")
            return
        g = svc.next()
        if g is None:
            self._announce("No differences")
            return
        self._announce(g.summary_verbose)
        self._set_status(g.summary_short)

    def compare_dialog_previous(self) -> None:
        svc = getattr(self, "_compare_service", None)
        if svc is None:
            self._announce("Not in compare mode")
            return
        g = svc.previous()
        if g is None:
            self._announce("No differences")
            return
        self._announce(g.summary_verbose)
        self._set_status(g.summary_short)

    def compare_current_summary(self) -> None:
        svc = getattr(self, "_compare_service", None)
        if svc is None:
            self._announce("Not in compare mode")
            return
        g = svc.current()
        if g is None:
            self._announce("No current difference — press F8 to navigate")
            return
        self._announce(g.summary_verbose)
        self._set_status(g.summary_short)

    def compare_toggle_ignore_whitespace(self) -> None:
        from quill.core.compare_service import CompareOptions

        opts = getattr(self, "_compare_options", CompareOptions())
        if opts.ignore_all_whitespace:
            self._compare_options = CompareOptions(ignore_all_whitespace=False)
            msg = "Whitespace comparison: exact"
        elif opts.ignore_trailing_whitespace:
            self._compare_options = CompareOptions(ignore_all_whitespace=True)
            msg = "Whitespace comparison: ignore all"
        else:
            self._compare_options = CompareOptions(ignore_trailing_whitespace=True)
            msg = "Whitespace comparison: ignore trailing"
        self._announce(msg)
        self._set_status(msg)

    def compare_generate_report(self) -> None:
        svc = getattr(self, "_compare_service", None)
        if svc is None:
            self._set_status("No active comparison")
            return
        from quill.core.document import Document

        lines: list[str] = [
            f"# Compare Report: {svc.left_label} vs {svc.right_label}",
            f"{svc.group_count} difference(s) found.",
            "",
        ]
        for g in svc._groups:
            lines.append(g.summary_verbose)
            lines.append("")
        text = "\n".join(lines)
        doc = Document(name="Compare Report.md", text=text)
        self._create_document_tab(doc, select=True)
        self._set_status("Compare report opened in new tab")

    def compare_with_file(self) -> None:
        wx = self._wx
        with wx.FileDialog(
            self.frame,
            "Compare with file",
            wildcard=(
                "Text files (*.txt;*.md;*.html;*.htm;*.xhtml)|*.txt;*.md;*.html;*.htm;*.xhtml|"
                "All files (*.*)|*.*"
            ),
            style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
        ) as dialog:
            if self._show_modal_dialog(dialog, "Compare with file") != wx.ID_OK:
                return
            target = Path(dialog.GetPath())
        other_document = read_text_document(target)
        source_documents = [
            (self.document.name, self.editor.GetValue()),
            (target.name, other_document.text),
        ]
        if not self._start_compare_session(source_documents):
            self._set_status(f"No differences from {target.name}")
            return
        current_name = self.document.name
        diff_text = build_unified_diff(
            self.editor.GetValue(),
            other_document.text,
            current_name,
            target.name,
        )
        max_chars = 12000
        if len(diff_text) > max_chars:
            diff_text = diff_text[:max_chars] + "\n... (truncated)\n"
        self._show_message_box(diff_text, "Compare with File", wx.ICON_INFORMATION | wx.OK)
        self._set_status(f"Compared with {target.name}")

    def compare_open_documents(self) -> None:
        if len(self._document_tabs) < 2:
            self._set_status("Open at least two documents to compare")
            return
        source_documents = [
            (tab.document.name, tab.editor.GetValue()) for tab in self._document_tabs
        ]
        if not self._start_compare_session(source_documents):
            self._set_status("No differences across open documents")
            return
        self._set_status(
            f"Compare session started. {len(source_documents)} documents. "
            f"{len(self._compare_session.groups)} differing line groups found."
        )

    def compare_next_difference(self) -> None:
        session = self._compare_session
        if session is None or not session.groups:
            self._set_status("No active compare session")
            return
        from quill.ui import sound_manager

        if len(session.groups) < 2:
            sound_manager.post_sound("compare_no_more_differences")
        else:
            sound_manager.post_sound("compare_next_difference")
        session.current_index = (session.current_index + 1) % len(session.groups)
        self.compare_announce_difference()

    def compare_previous_difference(self) -> None:
        session = self._compare_session
        if session is None or not session.groups:
            self._set_status("No active compare session")
            return
        from quill.ui import sound_manager

        if len(session.groups) < 2:
            sound_manager.post_sound("compare_no_more_differences")
        else:
            sound_manager.post_sound("compare_previous_difference")
        session.current_index = (session.current_index - 1) % len(session.groups)
        self.compare_announce_difference()

    def compare_announce_difference(self) -> None:
        session = self._compare_session
        if session is None or not session.groups:
            self._set_status("No active compare session")
            return
        group = session.groups[session.current_index]
        if session.synchronized_navigation:
            self._focus_active_document_on_difference(group)
        self._set_status(self._render_compare_group(group, len(session.groups)))

    def open_compare_difference_list(self) -> None:
        session = self._compare_session
        if session is None or not session.groups:
            self._set_status("No active compare session")
            return
        wx = self._wx
        choices = [self._render_compare_choice(group) for group in session.groups]
        with wx.SingleChoiceDialog(
            self.frame,
            "Select a difference:",
            "Difference List",
            choices=choices,
        ) as dialog:
            dialog.SetSelection(session.current_index)
            if self._show_modal_dialog(dialog, "Difference List") != wx.ID_OK:
                return
            selection = dialog.GetSelection()
        if selection == wx.NOT_FOUND:
            return
        session.current_index = selection
        self.compare_announce_difference()

    def toggle_compare_synchronization(self) -> None:
        session = self._compare_session
        if session is None:
            self._set_status("No active compare session")
            return
        session.synchronized_navigation = not session.synchronized_navigation
        state = "on" if session.synchronized_navigation else "off"
        self._set_status(f"Synchronized compare navigation {state}")

    def open_compare_options(self) -> None:
        wx = self._wx
        trailing = (
            self._show_message_box(
                "Ignore trailing spaces while comparing?",
                "Compare Options",
                wx.ICON_QUESTION | wx.YES_NO | wx.NO_DEFAULT,
            )
            == wx.YES
        )
        endings = (
            self._show_message_box(
                "Ignore line-ending differences (CRLF vs LF)?",
                "Compare Options",
                wx.ICON_QUESTION | wx.YES_NO | wx.NO_DEFAULT,
            )
            == wx.YES
        )
        self._compare_ignore_trailing_spaces = trailing
        self._compare_ignore_line_endings = endings
        session = self._compare_session
        if session is not None:
            self._start_compare_session(session.source_documents)
        self._set_status("Updated compare options")

    def create_compare_summary_document(self) -> None:
        session = self._compare_session
        if session is None or not session.groups:
            self._set_status("No active compare session")
            return
        summary = self._build_compare_summary_text(session)
        self._create_document_tab(
            Document(text=summary, path=None, modified=False),
            select=True,
        )
        self._set_status("Opened compare summary document")

    def copy_current_difference(self) -> None:
        session = self._compare_session
        if session is None or not session.groups:
            self._set_status("No active compare session")
            return
        group = session.groups[session.current_index]
        text = self._render_compare_group(group, len(session.groups))
        if not self._copy_to_clipboard(text):
            self._set_status("Could not copy current difference")
            return
        self._set_status("Copied current difference")

    def copy_all_differences(self) -> None:
        session = self._compare_session
        if session is None or not session.groups:
            self._set_status("No active compare session")
            return
        text = self._build_compare_summary_text(session)
        if not self._copy_to_clipboard(text):
            self._set_status("Could not copy all differences")
            return
        self._set_status("Copied all differences")

    def _start_compare_session(self, source_documents: list[tuple[str, str]]) -> bool:
        groups = self._build_compare_groups(source_documents)
        if not groups:
            self._compare_session = None
            return False
        self._compare_session = _CompareSession(source_documents=source_documents, groups=groups)
        from quill.ui import sound_manager

        sound_manager.post_sound("compare_enter_mode")
        self._set_status(
            f"Compare session started. {len(source_documents)} documents. "
            f"{len(groups)} differing line groups found. "
            "Press F8 for next difference, Shift+F8 for previous difference, "
            "Ctrl+F8 for current difference."
        )
        self.compare_announce_difference()
        return True

    def _build_compare_groups(
        self, source_documents: list[tuple[str, str]]
    ) -> list[_CompareDifferenceGroup]:
        if len(source_documents) < 2:
            return []
        split_lines = [text.splitlines() for _name, text in source_documents]
        max_lines = max((len(lines) for lines in split_lines), default=0)
        groups: list[_CompareDifferenceGroup] = []
        start_line: int | None = None

        def flush(end_line_exclusive: int) -> None:
            nonlocal start_line
            if start_line is None:
                return
            block_end = end_line_exclusive - 1
            groups.append(
                self._build_compare_group(
                    source_documents, split_lines, start_line, block_end, len(groups) + 1
                )
            )
            start_line = None

        for line_index in range(max_lines):
            normalized = [
                self._normalize_compare_line(lines[line_index]) if line_index < len(lines) else None
                for lines in split_lines
            ]
            baseline = normalized[0]
            same = all(value == baseline for value in normalized[1:])
            if same:
                flush(line_index)
                continue
            if start_line is None:
                start_line = line_index
        flush(max_lines)
        return groups

    def _build_compare_group(
        self,
        source_documents: list[tuple[str, str]],
        split_lines: list[list[str]],
        start_line: int,
        end_line: int,
        group_index: int,
    ) -> _CompareDifferenceGroup:
        blocks: list[_CompareLineBlock] = []
        for doc_index, (doc_name, _text) in enumerate(source_documents):
            lines = split_lines[doc_index]
            if start_line >= len(lines):
                blocks.append(_CompareLineBlock(doc_name, None, None, []))
                continue
            chunk = lines[start_line : min(end_line + 1, len(lines))]
            start = start_line + 1
            finish = start + len(chunk) - 1
            blocks.append(_CompareLineBlock(doc_name, start, finish, chunk))
        kind = self._classify_difference_kind(blocks)
        return _CompareDifferenceGroup(index=group_index, kind=kind, blocks=blocks)

    def _normalize_compare_line(self, line: str) -> str:
        normalized = line
        if self._compare_ignore_line_endings:
            normalized = normalized.rstrip("\r\n")
        if self._compare_ignore_trailing_spaces:
            normalized = normalized.rstrip()
        return normalized

    def _classify_difference_kind(self, blocks: list[_CompareLineBlock]) -> str:
        if len(blocks) != 2:
            return "changed"
        left_text = "\n".join(blocks[0].text)
        right_text = "\n".join(blocks[1].text)
        if not blocks[0].text and blocks[1].text:
            return "added"
        if blocks[0].text and not blocks[1].text:
            return "removed"
        if left_text == right_text:
            return "changed"
        if left_text.lower() == right_text.lower():
            return "case-only"
        left_compact = re.sub(r"\s+", "", left_text)
        right_compact = re.sub(r"\s+", "", right_text)
        if left_compact == right_compact:
            return "whitespace-only"
        left_punct = re.sub(r"[^\w\s]", "", left_text)
        right_punct = re.sub(r"[^\w\s]", "", right_text)
        if left_punct == right_punct:
            return "punctuation-only"
        if unicodedata.normalize("NFKC", left_text) == unicodedata.normalize("NFKC", right_text):
            return "unicode-only"
        return "changed"

    def _focus_active_document_on_difference(self, group: _CompareDifferenceGroup) -> None:
        active_name = self.document.name
        for block in group.blocks:
            if block.document_name != active_name or block.start_line is None:
                continue
            self._move_caret_to_line(block.start_line)
            return

    def _move_caret_to_line(self, line_number: int) -> None:
        if line_number < 1:
            return
        text = self.editor.GetValue()
        starts = [0]
        for line in text.splitlines(keepends=True):
            starts.append(starts[-1] + len(line))
        if line_number >= len(starts):
            position = starts[-1]
        else:
            position = starts[line_number - 1]
        self.editor.SetInsertionPoint(position)
        self.editor.SetSelection(position, position)

    def _render_compare_choice(self, group: _CompareDifferenceGroup) -> str:
        first = group.blocks[0]
        line_label = "line ?"
        if first.start_line is not None:
            line_label = f"line {first.start_line}"
        preview = ""
        if first.text:
            preview = first.text[0].strip()
        if preview:
            preview = f" {preview[:60]}"
        return f"Difference {group.index}: {group.kind} at {line_label}.{preview}"

    def _render_compare_group(self, group: _CompareDifferenceGroup, total: int) -> str:
        parts = [f"Difference {group.index} of {total}. {group.kind}."]
        for block in group.blocks:
            if block.start_line is None:
                parts.append(f"{block.document_name}: no corresponding lines.")
                continue
            if block.start_line == block.end_line:
                location = f"line {block.start_line}"
            else:
                location = f"lines {block.start_line}-{block.end_line}"
            preview = " ".join(block.text[:2]).strip()[:140] if block.text else "(empty)"
            parts.append(f"{block.document_name} {location}: {preview}")
        return " ".join(parts)

    def _build_compare_summary_text(self, session: _CompareSession) -> str:
        lines = [
            "Compare Summary",
            f"Documents: {', '.join(name for name, _text in session.source_documents)}",
            (
                "Options: "
                + (
                    "ignored trailing spaces"
                    if self._compare_ignore_trailing_spaces
                    else "kept trailing spaces"
                )
                + ", "
                + (
                    "ignored line endings"
                    if self._compare_ignore_line_endings
                    else "kept line endings"
                )
            ),
            "",
            f"{len(session.groups)} differences found.",
            "",
        ]
        for group in session.groups:
            lines.append(f"Difference {group.index}: {group.kind}")
            for block in group.blocks:
                if block.start_line is None:
                    lines.append(f"- {block.document_name}: no corresponding lines")
                    continue
                if block.start_line == block.end_line:
                    location = f"line {block.start_line}"
                else:
                    location = f"lines {block.start_line}-{block.end_line}"
                text = " | ".join(block.text[:3]).strip()
                lines.append(f"- {block.document_name} {location}: {text}")
            lines.append("")
        return "\n".join(lines).rstrip() + "\n"
