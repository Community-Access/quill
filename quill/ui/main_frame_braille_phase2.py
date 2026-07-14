"""Braille Mode Phase 2 commands (BR-013 / BR-014).

A mixin on :class:`~quill.ui.main_frame.MainFrame` holding the Phase 2
print-page detection results, the print-page navigation and running-head
handlers, and the wiring that exposes them through the Braille menu and
the command registry. Kept in its own module so :mod:`main_frame_braille`
stays under the GATE-11 module-size budget.

The mixin relies on attributes/methods provided by MainFrame and its
other mixins: ``_active_brf_resolver``, ``editor``, ``settings``,
``_announce``, ``_set_status``, ``_move_point``, ``_record_location_before_jump``,
``_location_ring``, ``_show_modal_dialog``, ``_show_message_box``, ``_wx``,
``_refresh_statusbar``, ``_braille_position``, ``_announce_not_braille``,
``_say``, ``_menu_label``, ``frame``.

It also reads the ``_braille_status_menu`` and ``_braille_navigation_menu``
attributes that the Phase 1 mixin stashes in :meth:`_build_braille_menu`
so it can append Phase 2 items to the right submenus.

All handlers degrade gracefully when the active document is not a braille
file (``_active_brf_resolver`` returns None) or when there is no editor.
"""

from __future__ import annotations


class BraillePhase2CommandsMixin:
    """Phase 2 Braille command handlers (print pages, running heads)."""

    # Phase 2 IDs are populated in :meth:`_mint_phase2_braille_ids` and
    # read by the binding/registration helpers below.
    _id_braille_go_to_print_page: object
    _id_braille_next_print_change: object
    _id_braille_prev_print_change: object
    _id_braille_announce_running_head: object
    _id_braille_use_running_head: object
    _id_braille_ignore_running_head: object

    def _mint_phase2_braille_ids(self) -> None:
        """Mint the Phase 2 menu IDs onto ``self``."""
        wx = self._wx
        self._id_braille_go_to_print_page = wx.NewIdRef()
        self._id_braille_next_print_change = wx.NewIdRef()
        self._id_braille_prev_print_change = wx.NewIdRef()
        self._id_braille_announce_running_head = wx.NewIdRef()
        self._id_braille_use_running_head = wx.NewIdRef()
        self._id_braille_ignore_running_head = wx.NewIdRef()

    def _append_phase2_status_items(self, status: object) -> None:
        """Append the Phase 2 status submenu items to ``status``."""
        status.AppendSeparator()
        status.Append(
            self._id_braille_announce_running_head,
            self._menu_label("Announce &Running Head", "braille.announce_running_head"),
        )
        status.Append(
            self._id_braille_use_running_head,
            self._menu_label(
                "&Include Running Head in Status", "braille.use_running_head_in_status"
            ),
        )
        status.Append(
            self._id_braille_ignore_running_head,
            self._menu_label(
                "&Omit Running Head from Status", "braille.ignore_running_head_for_status"
            ),
        )

    def _append_phase2_navigation_items(self, navigation: object) -> None:
        """Append the Phase 2 navigation submenu items to ``navigation``."""
        navigation.AppendSeparator()
        navigation.Append(
            self._id_braille_go_to_print_page,
            self._menu_label("Go to &Print Page...", "braille.go_to_print_page"),
        )
        navigation.Append(
            self._id_braille_next_print_change,
            self._menu_label("&Next Print Page Change", "braille.next_print_page_change"),
        )
        navigation.Append(
            self._id_braille_prev_print_change,
            self._menu_label("&Previous Print Page Change", "braille.previous_print_page_change"),
        )

    def _bind_phase2_braille_items(self) -> None:
        """Bind the Phase 2 menu items to their handlers."""
        wx = self._wx
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.go_to_print_page(),
            id=self._id_braille_go_to_print_page,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.next_print_page_change(),
            id=self._id_braille_next_print_change,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.previous_print_page_change(),
            id=self._id_braille_prev_print_change,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.announce_running_head(),
            id=self._id_braille_announce_running_head,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.use_running_head_in_status(),
            id=self._id_braille_use_running_head,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.ignore_running_head_for_status(),
            id=self._id_braille_ignore_running_head,
        )

    def _phase2_braille_commands(self) -> list[tuple[str, str, object]]:
        """Return the Phase 2 (command_id, label, handler) registry entries."""
        return [
            ("braille.go_to_print_page", "Go to Print Page...", self.go_to_print_page),
            (
                "braille.next_print_page_change",
                "Next Print Page Change",
                self.next_print_page_change,
            ),
            (
                "braille.previous_print_page_change",
                "Previous Print Page Change",
                self.previous_print_page_change,
            ),
            ("braille.announce_running_head", "Announce Running Head", self.announce_running_head),
            (
                "braille.use_running_head_in_status",
                "Include Running Head in Status",
                self.use_running_head_in_status,
            ),
            (
                "braille.ignore_running_head_for_status",
                "Omit Running Head from Status",
                self.ignore_running_head_for_status,
            ),
        ]

    # ------------------------------------------------------------------
    # Wiring overrides (extend Phase 1's menu/bind/register)
    # ------------------------------------------------------------------

    def _build_braille_menu(self) -> object:  # type: ignore[override]
        # Mint the Phase 2 IDs first so the helpers below can reference
        # them when appending to the inner submenus that the Phase 1
        # builder stashes on ``self``.
        self._mint_phase2_braille_ids()
        menu = super()._build_braille_menu()  # type: ignore[misc]
        # Append Phase 2 items to the inner submenus that Phase 1 stashed.
        self._append_phase2_status_items(self._braille_status_menu)
        self._append_phase2_navigation_items(self._braille_navigation_menu)
        return menu

    def _bind_braille_menu(self) -> None:  # type: ignore[override]
        super()._bind_braille_menu()  # type: ignore[misc]
        self._bind_phase2_braille_items()

    def _register_braille_commands(self) -> None:  # type: ignore[override]
        super()._register_braille_commands()  # type: ignore[misc]
        for command_id, label, handler in self._phase2_braille_commands():
            self.commands.register(command_id, label, handler, self._binding_for(command_id))

    # ------------------------------------------------------------------
    # Status helpers (BR-014)
    # ------------------------------------------------------------------

    def _compose_detailed_status(
        self,
        resolver: object,
        position: object,
    ) -> str:
        """Build a :func:`detailed_status` payload from the active BRF.

        Pulls print-page, continuation-letter, running-head, and
        confidence data out of :mod:`quill.core.brf_page_detection` and
        respects the ``braille_include_running_head`` setting.
        """
        from quill.core.braille_status import (
            ConfidenceLevel,
            PrintPageInfo,
            ProofingStatus,
            detailed_status,
        )
        from quill.core.brf_page_detection import (
            detect_continuation_letter,
            detect_print_pages,
            detect_running_head,
        )

        document = getattr(resolver, "document", None)
        text = getattr(document, "text", "")
        page_map = getattr(resolver, "page_map", None)
        page_count = getattr(position, "page_count", 0)
        braille_page = getattr(position, "page", 0)
        confidence_label = "high"
        confidence_score = 1.0
        print_page_number: int | None = None
        continuation: str | None = None
        running_head: str | None = None
        if page_map is not None and text:
            indicators = detect_print_pages(text, page_map)
            # Find the most recent indicator at or before this braille page.
            relevant = [i for i in indicators if i.braille_page <= braille_page]
            if relevant:
                chosen = relevant[-1]
                confidence_label = chosen.confidence
                confidence_score = {
                    "high": 1.0,
                    "medium": 0.6,
                    "low": 0.3,
                }.get(chosen.confidence, 0.5)
                print_page_number = chosen.detected_print_page
                # Continuation letter requires a previous indicator.
                if chosen.braille_page == braille_page and len(relevant) >= 2:
                    continuation = detect_continuation_letter(text, page_map, chosen, relevant[-2])
            heads = detect_running_head(text, page_map)
            for head in heads:
                if head.braille_page == braille_page:
                    running_head = head.text
                    break
        if not getattr(self.settings, "braille_include_running_head", False):
            # Honor the user setting: blank out the running head
            # before it reaches the status string.
            running_head = None
        print_page = PrintPageInfo(
            number=print_page_number,
            is_implied=False,
            continuation=continuation,
            running_head=running_head,
            confidence=ConfidenceLevel(label=confidence_label, score=confidence_score),
        )
        return detailed_status(
            position,
            page_count,
            print_page,
            None,
            None,
            ProofingStatus(),
            print_page.confidence,
            self.settings,
        )

    def read_current_print_page(self) -> None:
        resolved = self._braille_position()
        if resolved is None:
            self._announce_not_braille()
            return
        resolver, position = resolved
        from quill.core.brf_page_detection import detect_print_pages

        indicators = detect_print_pages(resolver.document.text, resolver.page_map)
        relevant = [i for i in indicators if i.braille_page <= position.page]
        if not relevant:
            self._say("Print page unknown.")
            return
        chosen = relevant[-1]
        if chosen.detected_print_page is None:
            self._say("Print page unknown.")
        else:
            self._say(f"Print page {chosen.detected_print_page}.")

    # ------------------------------------------------------------------
    # Navigation handlers (BR-014)
    # ------------------------------------------------------------------

    def go_to_print_page(self) -> None:
        wx = self._wx
        resolver = self._active_brf_resolver()
        editor = getattr(self, "editor", None)
        if resolver is None or editor is None:
            self._announce_not_braille()
            return
        from quill.core.brf_page_detection import detect_print_pages

        indicators = detect_print_pages(resolver.document.text, resolver.page_map)
        if not indicators:
            self._say("No print pages detected. Try recalculating the page map.")
            return
        # Clamp the dialog default to a sensible value: the indicator
        # closest to the caret, or 1 if the caret is on the first page.
        try:
            caret = editor.GetCurrentPos()
        except Exception:  # noqa: BLE001
            caret = 0
        current = resolver.resolve(caret)
        closest = min(
            indicators,
            key=lambda i: abs(i.braille_page - current.page),
        )
        default = str(closest.detected_print_page) if closest.detected_print_page else "1"
        with wx.TextEntryDialog(
            self.frame,
            "Enter a print page number:",
            "Go to Print Page",
            value=default,
        ) as dialog:
            if self._show_modal_dialog(dialog, "Go to Print Page") != wx.ID_OK:
                return
            raw_value = dialog.GetValue().strip()
        try:
            target_print_page = int(raw_value)
        except ValueError:
            self._show_message_box(
                "Print page number must be a number.",
                "Go to Print Page",
                wx.ICON_ERROR | wx.OK,
            )
            return
        # Find the braille page that hosts the chosen print page.
        match = next(
            (
                i
                for i in indicators
                if i.detected_print_page is not None and i.detected_print_page == target_print_page
            ),
            None,
        )
        if match is None:
            self._say(f"Print page {target_print_page} was not detected.")
            return
        # Move the caret to the start of the matching braille page.
        target_page = resolver.page_map.page_index_for(match.braille_page)
        offset = target_page.start_offset
        self._record_location_before_jump()
        self._move_point(offset)
        editor.SetFocus()
        self._location_ring.record(offset)
        position = resolver.resolve(offset)
        self._say(f"Print page {target_print_page} on braille page {position.page}.")

    def next_print_page_change(self) -> None:
        self._step_print_page_change(forward=True)

    def previous_print_page_change(self) -> None:
        self._step_print_page_change(forward=False)

    def _step_print_page_change(self, *, forward: bool) -> None:
        resolver = self._active_brf_resolver()
        editor = getattr(self, "editor", None)
        if resolver is None or editor is None:
            self._announce_not_braille()
            return
        from quill.core.brf_page_detection import detect_print_pages

        try:
            caret = editor.GetCurrentPos()
        except Exception:  # noqa: BLE001
            return
        current = resolver.resolve(caret)
        indicators = detect_print_pages(resolver.document.text, resolver.page_map)
        if forward:
            candidates = [i for i in indicators if i.braille_page > current.page]
        else:
            candidates = [i for i in indicators if i.braille_page < current.page]
        if not candidates:
            self._say("No next print page change." if forward else "No previous print page change.")
            return
        chosen = candidates[0] if forward else candidates[-1]
        target_page = resolver.page_map.page_index_for(chosen.braille_page)
        offset = target_page.start_offset
        self._record_location_before_jump()
        self._move_point(offset)
        editor.SetFocus()
        self._location_ring.record(offset)
        page_label = (
            f"print page {chosen.detected_print_page}"
            if chosen.detected_print_page is not None
            else "an unknown print page"
        )
        self._say(f"Print page change: {page_label} on braille page {chosen.braille_page}.")

    def announce_running_head(self) -> None:
        resolver = self._active_brf_resolver()
        editor = getattr(self, "editor", None)
        if resolver is None or editor is None:
            self._announce_not_braille()
            return
        from quill.core.brf_page_detection import detect_running_head

        try:
            caret = editor.GetCurrentPos()
        except Exception:  # noqa: BLE001
            return
        current = resolver.resolve(caret)
        heads = detect_running_head(resolver.document.text, resolver.page_map)
        for head in heads:
            if head.braille_page == current.page:
                if head.text:
                    self._say(f"Running head: {head.text}.")
                else:
                    self._say("No running head detected for this page.")
                return
        self._say("No running head detected for this page.")

    def use_running_head_in_status(self) -> None:
        self.settings.braille_include_running_head = True
        self._say("Running head will be included in the detailed status.")

    def ignore_running_head_for_status(self) -> None:
        self.settings.braille_include_running_head = False
        self._say("Running head will be omitted from the detailed status.")
