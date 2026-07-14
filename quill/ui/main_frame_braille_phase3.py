"""Braille Mode Phase 3 proofing commands (BR-017, #240).

Adds the **Braille > Proofing** submenu and its eight commands on top of the
Phase 1 Braille mixin, using the same MRO-override pattern as
:class:`~quill.ui.main_frame_braille_phase2.BraillePhase2CommandsMixin`:
``_build_braille_menu`` / ``_bind_braille_menu`` / ``_register_braille_commands``
each call ``super()`` and then add the Phase 3 surface.

Proofing state is read from and written to the per-file sidecar (BR-015,
``quill.core.brf_sidecar``); the proofing logic is pure
(``quill.core.brf_proofing``). The braille file itself is never modified. Every
command degrades gracefully when the active document is not a braille file or has
not been saved yet, announcing what to do rather than failing.
"""

from __future__ import annotations

from pathlib import Path


class BrailleProofingCommandsMixin:
    """Phase 3 Braille proofing command handlers (sidecar-backed)."""

    # Relies on MainFrame / Phase 1 attributes: _wx, frame, editor, document,
    # commands, _binding_for, _menu_label, _show_modal_dialog, _say,
    # _announce_not_braille, _braille_position, _active_brf_resolver,
    # _move_point, _record_location_before_jump, _location_ring.

    def _mint_phase3_braille_ids(self) -> None:
        wx = self._wx
        self._id_braille_mark_proofed = wx.NewIdRef()
        self._id_braille_mark_review = wx.NewIdRef()
        self._id_braille_clear_mark = wx.NewIdRef()
        self._id_braille_add_note = wx.NewIdRef()
        self._id_braille_read_progress_p3 = wx.NewIdRef()
        self._id_braille_list_proofed = wx.NewIdRef()
        self._id_braille_list_review = wx.NewIdRef()
        self._id_braille_export_report = wx.NewIdRef()
        # Validation (BR-019, #242).
        self._id_braille_validate = wx.NewIdRef()
        self._id_braille_next_warning = wx.NewIdRef()
        self._id_braille_prev_warning = wx.NewIdRef()
        self._id_braille_warning_summary = wx.NewIdRef()

    def _append_proofing_submenu(self, menu: object) -> None:
        wx = self._wx
        proofing = wx.Menu()
        proofing.Append(
            self._id_braille_mark_proofed,
            self._menu_label("Mark Current Page &Proofed", "braille.mark_page_proofed"),
        )
        proofing.Append(
            self._id_braille_mark_review,
            self._menu_label("Mark Current Page Needs &Review", "braille.mark_page_needs_review"),
        )
        proofing.Append(
            self._id_braille_clear_mark,
            self._menu_label("&Clear Proofing Mark", "braille.clear_proofing_mark"),
        )
        proofing.Append(
            self._id_braille_add_note,
            self._menu_label("Add Proofing &Note...", "braille.add_proofing_note"),
        )
        proofing.Append(
            self._id_braille_read_progress_p3,
            self._menu_label("Read Progress &Summary", "braille.read_proofing_progress"),
        )
        proofing.Append(
            self._id_braille_list_proofed,
            self._menu_label("List Proofed &Pages...", "braille.list_proofed_pages"),
        )
        proofing.Append(
            self._id_braille_list_review,
            self._menu_label("List Pages Needing Re&view...", "braille.list_pages_needing_review"),
        )
        proofing.Append(
            self._id_braille_export_report,
            self._menu_label("&Export Proofing Report...", "braille.export_proofing_report"),
        )
        menu.AppendSubMenu(proofing, "Proo&fing")

    def _append_validation_submenu(self, menu: object) -> None:
        wx = self._wx
        validation = wx.Menu()
        validation.Append(
            self._id_braille_validate,
            self._menu_label("&Validate BRF Layout...", "braille.validate_layout"),
        )
        validation.Append(
            self._id_braille_next_warning,
            self._menu_label("&Next Warning", "braille.next_warning"),
        )
        validation.Append(
            self._id_braille_prev_warning,
            self._menu_label("&Previous Warning", "braille.previous_warning"),
        )
        validation.Append(
            self._id_braille_warning_summary,
            self._menu_label("Warnings &Summary", "braille.warnings_summary"),
        )
        menu.AppendSubMenu(validation, "Va&lidation")

    def _bind_phase3_braille_items(self) -> None:
        wx = self._wx
        pairs = (
            (self._id_braille_mark_proofed, self.mark_page_proofed),
            (self._id_braille_mark_review, self.mark_page_needs_review),
            (self._id_braille_clear_mark, self.clear_proofing_mark),
            (self._id_braille_add_note, self.add_proofing_note),
            (self._id_braille_read_progress_p3, self.read_proofing_progress),
            (self._id_braille_list_proofed, self.list_proofed_pages),
            (self._id_braille_list_review, self.list_pages_needing_review),
            (self._id_braille_export_report, self.export_proofing_report),
            (self._id_braille_validate, self.validate_braille_file),
            (self._id_braille_next_warning, self.next_validation_warning),
            (self._id_braille_prev_warning, self.previous_validation_warning),
            (self._id_braille_warning_summary, self.read_validation_summary),
        )
        for id_ref, handler in pairs:
            self.frame.Bind(wx.EVT_MENU, lambda _e, h=handler: h(), id=id_ref)

    def _phase3_braille_commands(self) -> list[tuple[str, str, object]]:
        return [
            (
                "braille.mark_page_proofed",
                "Mark Current Braille Page as Proofed",
                self.mark_page_proofed,
            ),
            (
                "braille.mark_page_needs_review",
                "Mark Current Braille Page Needs Review",
                self.mark_page_needs_review,
            ),
            (
                "braille.clear_proofing_mark",
                "Clear Proofing Mark on Current Page",
                self.clear_proofing_mark,
            ),
            (
                "braille.add_proofing_note",
                "Add Proofing Note to Current Page",
                self.add_proofing_note,
            ),
            (
                "braille.read_proofing_progress",
                "Read Proofing Progress Summary",
                self.read_proofing_progress,
            ),
            ("braille.list_proofed_pages", "List Proofed Braille Pages", self.list_proofed_pages),
            (
                "braille.list_pages_needing_review",
                "List Braille Pages Needing Review",
                self.list_pages_needing_review,
            ),
            (
                "braille.export_proofing_report",
                "Export Proofing Report",
                self.export_proofing_report,
            ),
            ("braille.validate_layout", "Validate BRF Layout", self.validate_braille_file),
            ("braille.next_warning", "Next Braille Layout Warning", self.next_validation_warning),
            (
                "braille.previous_warning",
                "Previous Braille Layout Warning",
                self.previous_validation_warning,
            ),
            (
                "braille.warnings_summary",
                "Braille Layout Warnings Summary",
                self.read_validation_summary,
            ),
        ]

    # --- MRO overrides ------------------------------------------------------

    def _build_braille_menu(self) -> object:  # type: ignore[override]
        menu = super()._build_braille_menu()  # type: ignore[misc]
        self._mint_phase3_braille_ids()
        self._append_proofing_submenu(menu)
        self._append_validation_submenu(menu)
        return menu

    def _bind_braille_menu(self) -> None:  # type: ignore[override]
        super()._bind_braille_menu()  # type: ignore[misc]
        self._bind_phase3_braille_items()

    def _register_braille_commands(self) -> None:  # type: ignore[override]
        super()._register_braille_commands()  # type: ignore[misc]
        for command_id, label, handler in self._phase3_braille_commands():
            self.commands.register(command_id, label, handler, self._binding_for(command_id))

    # --- helpers ------------------------------------------------------------

    def _current_braille_page(self) -> int | None:
        """Resolved 1-based braille page at the caret, or None (announced)."""
        resolved = self._braille_position()
        if resolved is None:
            self._announce_not_braille()
            return None
        _resolver, position = resolved
        return position.page

    def _load_active_sidecar(self) -> tuple[Path, object] | None:
        """Return (path, BRFSidecar) for the active braille file, or None.

        A missing or malformed sidecar yields a fresh BRFSidecar so the first
        proofing action starts cleanly. Returns None (with a spoken hint) when
        the document has not been saved to disk yet.
        """
        from quill.core.brf_sidecar import BRFSidecar, BRFSidecarError, read_sidecar

        path = getattr(getattr(self, "document", None), "path", None)
        if path is None:
            self._say("Save the braille file before tracking proofing.")
            return None
        try:
            sidecar = read_sidecar(Path(path))
        except BRFSidecarError:
            sidecar = None
        return Path(path), (sidecar or BRFSidecar())

    def _save_active_sidecar(self, path: Path, sidecar: object) -> None:
        from quill.core.brf_sidecar import write_sidecar

        write_sidecar(path, sidecar)  # type: ignore[arg-type]

    def _apply_proofing_for_page(self, action: object) -> None:
        """Resolve page + sidecar, run ``action(sidecar, page) -> message``, save."""
        page = self._current_braille_page()
        if page is None:
            return
        loaded = self._load_active_sidecar()
        if loaded is None:
            return
        path, sidecar = loaded
        message = action(sidecar, page)  # type: ignore[operator]
        self._save_active_sidecar(path, sidecar)
        self._say(message)

    # --- command handlers ---------------------------------------------------

    def mark_page_proofed(self) -> None:
        from quill.core import brf_proofing

        self._apply_proofing_for_page(brf_proofing.mark_proofed)

    def mark_page_needs_review(self) -> None:
        from quill.core import brf_proofing

        self._apply_proofing_for_page(brf_proofing.mark_needs_review)

    def clear_proofing_mark(self) -> None:
        from quill.core import brf_proofing

        self._apply_proofing_for_page(brf_proofing.clear_proofing_mark)

    def add_proofing_note(self) -> None:
        from quill.core import brf_proofing

        page = self._current_braille_page()
        if page is None:
            return
        loaded = self._load_active_sidecar()
        if loaded is None:
            return
        path, sidecar = loaded
        wx = self._wx
        with wx.TextEntryDialog(
            self.frame, f"Note for braille page {page}:", "Add Proofing Note"
        ) as dialog:
            if self._show_modal_dialog(dialog, "Add Proofing Note") != wx.ID_OK:
                return
            text = dialog.GetValue()
        message = brf_proofing.add_note(sidecar, page, text)
        self._save_active_sidecar(path, sidecar)
        self._say(message)

    def read_proofing_progress(self) -> None:
        from quill.core import brf_proofing

        resolved = self._braille_position()
        if resolved is None:
            self._announce_not_braille()
            return
        _resolver, position = resolved
        loaded = self._load_active_sidecar()
        if loaded is None:
            return
        _path, sidecar = loaded
        message = brf_proofing.progress_summary(
            sidecar,
            page_count=position.page_count,
            current_page=position.page,
            print_page=getattr(sidecar.position, "print_page", ""),
        )
        self._say(message)

    def list_proofed_pages(self) -> None:
        from quill.core import brf_proofing

        self._show_pages_list("Proofed Pages", brf_proofing.proofed_pages)

    def list_pages_needing_review(self) -> None:
        from quill.core import brf_proofing

        self._show_pages_list("Pages Needing Review", brf_proofing.pages_needing_review)

    def _show_pages_list(self, title: str, getter: object) -> None:
        loaded = self._load_active_sidecar()
        if loaded is None:
            return
        _path, sidecar = loaded
        pages = getter(sidecar)  # type: ignore[operator]
        if not pages:
            self._say(f"No {title.lower()}.")
            return
        wx = self._wx
        choices = [f"Braille page {p}" for p in pages]
        with wx.SingleChoiceDialog(
            self.frame, f"{title} ({len(pages)}). Choose a page to go to:", title, choices
        ) as dialog:
            if self._show_modal_dialog(dialog, title) != wx.ID_OK:
                return
            selection = dialog.GetSelection()
        if 0 <= selection < len(pages):
            self._jump_to_braille_page(pages[selection])

    def _jump_to_braille_page(self, page: int) -> None:
        resolver = self._active_brf_resolver()
        editor = getattr(self, "editor", None)
        if resolver is None or editor is None:
            return
        offset = resolver.go_to_page(page)
        self._record_location_before_jump()
        self._move_point(offset)
        editor.SetFocus()
        self._location_ring.record(offset)
        clamped = resolver.resolve(offset)
        self._say(f"Braille page {clamped.page} of {clamped.page_count}.")

    def export_proofing_report(self) -> None:
        from quill.core import brf_proofing

        loaded = self._load_active_sidecar()
        if loaded is None:
            return
        path, sidecar = loaded
        resolved = self._braille_position()
        page_count = resolved[1].page_count if resolved is not None else 0
        report = brf_proofing.export_report(sidecar, document_name=path.name, page_count=page_count)
        wx = self._wx
        with wx.FileDialog(
            self.frame,
            "Export Proofing Report",
            defaultFile=f"{path.stem}-proofing.txt",
            wildcard="Text files (*.txt)|*.txt|All files (*.*)|*.*",
            style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT,
        ) as dialog:
            if self._show_modal_dialog(dialog, "Export Proofing Report") != wx.ID_OK:
                return
            target = Path(dialog.GetPath())
        target.write_text(report, encoding="utf-8", newline="\n")
        self._say(f"Proofing report saved to {target.name}.")

    # --- validation commands (BR-019, #242) ---------------------------------

    def validate_braille_file(self) -> None:
        from quill.core.brf_validator import ValidatorOptions, validate_brf

        resolver = self._active_brf_resolver()
        editor = getattr(self, "editor", None)
        if resolver is None or editor is None:
            self._announce_not_braille()
            return
        settings = getattr(self, "settings", None)
        options = ValidatorOptions(
            cells_per_line=int(getattr(settings, "braille_cells_per_line", 40)),
            lines_per_page=int(getattr(settings, "braille_lines_per_page", 25)),
            use_form_feeds=bool(getattr(settings, "braille_use_form_feeds", True)),
        )
        warnings = validate_brf(editor.GetValue(), options)
        self._brf_validation_warnings = warnings
        self._brf_validation_index = -1
        if not warnings:
            self._say("No braille layout warnings found.")
            return
        self._show_warnings_list(warnings)

    def _show_warnings_list(self, warnings: list[object]) -> None:
        wx = self._wx
        choices = [
            f"Line {w.line}, page {w.page}, {w.severity}: {w.message}"  # type: ignore[attr-defined]
            for w in warnings
        ]
        with wx.SingleChoiceDialog(
            self.frame,
            f"{len(warnings)} layout warning(s). Choose one to go to:",
            "Braille Layout Warnings",
            choices,
        ) as dialog:
            if self._show_modal_dialog(dialog, "Braille Layout Warnings") != wx.ID_OK:
                return
            selection = dialog.GetSelection()
        if 0 <= selection < len(warnings):
            self._brf_validation_index = selection
            self._jump_to_warning(warnings[selection])

    def _jump_to_warning(self, warning: object) -> None:
        editor = getattr(self, "editor", None)
        if editor is None:
            return
        self._record_location_before_jump()
        self._move_point(warning.offset)  # type: ignore[attr-defined]
        editor.SetFocus()
        self._location_ring.record(warning.offset)  # type: ignore[attr-defined]
        total = len(getattr(self, "_brf_validation_warnings", []))
        position = self._brf_validation_index + 1
        self._say(f"Warning {position} of {total}: {warning.message}")  # type: ignore[attr-defined]

    def next_validation_warning(self) -> None:
        self._step_validation_warning(1)

    def previous_validation_warning(self) -> None:
        self._step_validation_warning(-1)

    def _step_validation_warning(self, delta: int) -> None:
        warnings = getattr(self, "_brf_validation_warnings", [])
        if not warnings:
            self._say("No warnings. Run Validate BRF Layout first.")
            return
        index = getattr(self, "_brf_validation_index", -1) + delta
        if index < 0:
            self._say("No previous warning.")
            return
        if index >= len(warnings):
            self._say("No next warning.")
            return
        self._brf_validation_index = index
        self._jump_to_warning(warnings[index])

    def read_validation_summary(self) -> None:
        from collections import Counter

        warnings = getattr(self, "_brf_validation_warnings", None)
        if warnings is None:
            self._say("No validation run yet. Run Validate BRF Layout first.")
            return
        if not warnings:
            self._say("No braille layout warnings found.")
            return
        counts = Counter(w.kind for w in warnings)  # type: ignore[attr-defined]
        top = ", ".join(
            f"{kind.replace('_', ' ')} ({count})" for kind, count in counts.most_common(3)
        )
        plural = "s" if len(warnings) != 1 else ""
        self._say(f"{len(warnings)} layout warning{plural}. Top categories: {top}.")
