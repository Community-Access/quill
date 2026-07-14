"""The Keyboard Manager: a searchable, conflict-aware keymap editor.

Extracted from ``main_frame`` into a focused mixin. ``MainFrame`` inherits
:class:`KeymapEditorMixin`; every method resolves through the MRO and reaches
sibling state (``self.keymap``, ``self.commands``, ``self._show_modal_dialog``,
``self._binding_for``, ``self._parse_keybinding``…) exactly as before.

The experience this mixin delivers, on top of the original flat list:

* **Search that understands both intents.** Type part of a command name to
  filter; type (or *record*) a shortcut like ``ctrl+alt+m`` and the list flips to
  "what is this key bound to?", telling you the command it already touches or
  that it is free. Modifier aliases, order, and case are all forgiven by
  :mod:`quill.core.keymap_query`.
* **Honest conflicts.** Assigning a taken key names the command that owns it (by
  its friendly title) and offers to reassign — moving the key here and freeing it
  there — rather than silently refusing.
* **Diagnostics and self-heal.** A one-click audit reports duplicate bindings,
  orphaned/unknown commands, unparseable bindings, and "assigned but inert" keys
  the accelerator layer cannot fire, then re-applies the keymap to repair the
  dispatch wiring.
"""

from __future__ import annotations

from quill.core.keymap import (
    diagnose_keymap,
    find_keymap_conflicts,
    format_binding_for_display,
    save_keymap,
)
from quill.core.keymap_query import (
    bindings_equivalent,
    canonical_binding,
    parse_binding,
    rewrite_chord_prefixes,
)
from quill.core.platform_nouns import primary_command_chord_label
from quill.ui.dialog_contract import apply_modal_ids

#: Commands that take part in the QUILL Quick Nav single-key browse layer. They
#: are appended to the editable command list even though they are not registry
#: commands, so a user can rebind them too.
_QUICK_NAV_ACTIONS: tuple[tuple[str, str], ...] = (
    ("QUILL Quick Nav: Heading", "quill.quick_nav.heading"),
    ("QUILL Quick Nav: Link", "quill.quick_nav.link"),
    ("QUILL Quick Nav: List", "quill.quick_nav.list"),
    ("QUILL Quick Nav: List Item", "quill.quick_nav.list_item"),
    ("QUILL Quick Nav: Table", "quill.quick_nav.table"),
    ("QUILL Quick Nav: Block Quote", "quill.quick_nav.block_quote"),
    ("QUILL Quick Nav: Bookmark", "quill.quick_nav.bookmark"),
    ("QUILL Quick Nav: Code Block", "quill.quick_nav.code_block"),
    ("QUILL Quick Nav: Table of Contents", "quill.quick_nav.table_of_contents"),
    ("QUILL Quick Nav: Paragraph", "quill.quick_nav.paragraph"),
    ("QUILL Quick Nav: Sentence", "quill.quick_nav.sentence"),
    ("QUILL Quick Nav: Block", "quill.quick_nav.block"),
    ("QUILL Quick Nav: Skip Forward Past Container", "quill.quick_nav.skip_forward"),
    ("QUILL Quick Nav: Skip Backward Past Container", "quill.quick_nav.skip_backward"),
)


class KeymapEditorMixin:
    def _quill_key_prefix(self) -> str:
        return str(getattr(self.settings, "quill_key_binding", "Ctrl+Shift+Grave"))

    def _keymap_editor_entries(self) -> list[tuple[str, str]]:
        """All editable (title, command_id) pairs, registry plus quick-nav."""
        entries: list[tuple[str, str]] = [
            (command.title, command.id)
            for command in self.commands.list()
            if not command.id.startswith("tools.keymap_editor")
        ]
        entries.extend(_QUICK_NAV_ACTIONS)
        return entries

    def _keymap_command_titles(self) -> dict[str, str]:
        """command_id -> friendly title, for naming conflicts in messages."""
        return {command_id: title for title, command_id in self._keymap_editor_entries()}

    def _binding_is_dispatchable(self, binding: str) -> bool:
        """True when the accelerator/chord layer can actually fire ``binding``.

        ``parse_binding`` is generous (it accepts e.g. ``Ctrl+Up``), but the
        dispatch layer only binds the keys ``_parse_keybinding`` /
        ``_parse_chord_second_key`` understand. A binding that parses but is not
        dispatchable would be assigned yet inert — exactly what diagnostics flag.
        """
        text = (binding or "").strip()
        if not text:
            return False
        if ", " in text:
            prefix_part, _, second_part = text.partition(", ")
            second = second_part.strip()
            return (
                self._parse_keybinding(prefix_part) is not None
                and bool(second)
                and self._parse_chord_second_key(second) is not None
            )
        return self._parse_keybinding(text) is not None

    # ----- the editor dialog -------------------------------------------------

    def open_keymap_editor(self) -> None:
        wx = self._wx
        entries = self._keymap_editor_entries()
        if not entries:
            self._set_status("No commands available for keymap editing")
            return
        prefix = self._quill_key_prefix()

        dialog = wx.Dialog(self.frame, title="Keymap Editor", size=(720, 560))
        root = wx.BoxSizer(wx.VERTICAL)
        root.Add(
            wx.StaticText(
                dialog,
                label=(
                    "Search by command name, or type or record a shortcut such as "
                    f"{primary_command_chord_label()}+M to see what it does. You can "
                    "write control, ctrl, or ctl, in any order. Select a command and "
                    "choose Edit to change its key."
                ),
            ),
            0,
            wx.ALL | wx.EXPAND,
            8,
        )
        search_row = wx.BoxSizer(wx.HORIZONTAL)
        search_label = wx.StaticText(dialog, label="&Search:")
        search = wx.TextCtrl(dialog, style=wx.TE_PROCESS_ENTER)
        search.SetName("Search commands or type a shortcut")
        record_button = wx.Button(dialog, label="&Record Keys...")
        search_row.Add(search_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6)
        search_row.Add(search, 1, wx.RIGHT, 6)
        search_row.Add(record_button, 0)
        root.Add(search_row, 0, wx.ALL | wx.EXPAND, 8)

        feedback = wx.StaticText(dialog, label="")
        feedback.SetName("Shortcut status")
        root.Add(feedback, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        listbox = wx.ListBox(dialog, style=wx.LB_SINGLE)
        root.Add(listbox, 1, wx.ALL | wx.EXPAND, 8)

        controls = wx.BoxSizer(wx.HORIZONTAL)
        edit_button = wx.Button(dialog, label="&Edit Keybinding...")
        diagnostics_button = wx.Button(dialog, label="Run &Diagnostics...")
        quill_key_button = wx.Button(dialog, label="Change &QUILL Key...")
        controls.Add(edit_button, 0, wx.RIGHT, 8)
        controls.Add(diagnostics_button, 0, wx.RIGHT, 8)
        controls.Add(quill_key_button, 0, wx.RIGHT, 8)
        root.Add(controls, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        buttons = dialog.CreateButtonSizer(wx.OK)
        if buttons is not None:
            ok_button = dialog.FindWindowById(wx.ID_OK)
            if ok_button is not None:
                ok_button.SetDefault()
            root.Add(buttons, 0, wx.EXPAND | wx.ALL, 8)
        apply_modal_ids(dialog, affirmative_id=wx.ID_OK, escape_id=wx.ID_OK)
        dialog.SetSizer(root)

        state: dict[str, list[tuple[str, str]]] = {"filtered": list(entries)}

        def compute_filtered(query: str) -> list[tuple[str, str]]:
            text = query.strip()
            if not text:
                feedback.SetLabel(f"Showing all {len(entries)} commands.")
                return list(entries)
            parsed = parse_binding(text, quill_key_prefix=prefix)
            if parsed is not None:
                # Typing the QUILL key alone ("quill", "qk", or the bare prefix
                # like "Ctrl+Shift+Grave") used to show nothing: it parses as the
                # bare prefix, which no single command is bound to (real QUILL-key
                # commands use the "prefix, <second-key>" chord). Treat it as
                # "show me everything behind the QUILL key" so the user can see
                # and rebind those chords.
                prefix_canonical = canonical_binding(prefix, quill_key_prefix=prefix)
                if prefix_canonical is not None and parsed.canonical == prefix_canonical:
                    chord_needle = f"{prefix_canonical}, "
                    matches = [
                        (title, command_id)
                        for title, command_id in entries
                        if (
                            canonical_binding(
                                self._binding_for(command_id), quill_key_prefix=prefix
                            )
                            or ""
                        ).startswith(chord_needle)
                    ]
                    display = format_binding_for_display(prefix_canonical, prefix=prefix)
                    feedback.SetLabel(
                        f"{len(matches)} command(s) are behind the QUILL key ({display}). "
                        "Select one and choose Edit to change its chord."
                    )
                    return matches
                matches = [
                    (title, command_id)
                    for title, command_id in entries
                    if bindings_equivalent(
                        self._binding_for(command_id), text, quill_key_prefix=prefix
                    )
                ]
                display = format_binding_for_display(parsed.canonical, prefix=prefix)
                if matches:
                    names = ", ".join(title for title, _ in matches)
                    feedback.SetLabel(f"{display} is assigned to: {names}.")
                else:
                    feedback.SetLabel(f"{display} is unassigned and available.")
                return matches
            lowered = text.lower()
            matches = [
                (title, command_id)
                for title, command_id in entries
                if lowered in title.lower() or lowered in command_id.lower()
            ]
            feedback.SetLabel(f"{len(matches)} command(s) match '{text}'.")
            return matches

        def label_for(title: str, command_id: str) -> str:
            shown = format_binding_for_display(self._binding_for(command_id) or "", prefix=prefix)
            return f"{title} — {shown or 'Unassigned'}"

        def refresh_list(keep: int | None = None) -> None:
            filtered = compute_filtered(search.GetValue())
            state["filtered"] = filtered
            labels = [label_for(title, command_id) for title, command_id in filtered]
            listbox.Set(labels)
            if filtered:
                target = keep if (keep is not None and 0 <= keep < len(filtered)) else 0
                listbox.SetSelection(target)

        def edit_selected(_event: object = None) -> None:
            selected = listbox.GetSelection()
            if selected == wx.NOT_FOUND:
                self._set_status("Select a command to edit")
                return
            title, command_id = state["filtered"][selected]
            current_binding = self._binding_for(command_id) or ""
            with wx.TextEntryDialog(
                dialog,
                f"Enter new keybinding for {title} (example: Ctrl+Shift+K):",
                "Edit Keybinding",
                value=current_binding,
            ) as binding_dialog:
                if self._show_modal_dialog(binding_dialog, "Edit Keybinding") != wx.ID_OK:
                    return
                new_binding = binding_dialog.GetValue().strip()
            if self._apply_keymap_binding(command_id, new_binding, parent=dialog):
                refresh_list(keep=selected)

        def record_keys(_event: object = None) -> None:
            captured = self._capture_keybinding(dialog)
            if captured:
                search.SetValue(captured)
                search.SetInsertionPointEnd()
                refresh_list()

        def run_diagnostics(_event: object = None) -> None:
            self._run_keymap_diagnostics(parent=dialog)
            refresh_list()

        def change_quill_key(_event: object = None) -> None:
            new_prefix = self._rebind_quill_key(parent=dialog)
            if new_prefix:
                # `prefix` is the closures' shared view of the active prefix;
                # rebinding it here makes compute_filtered / label_for follow
                # the new QUILL key without reopening the dialog.
                nonlocal prefix
                prefix = new_prefix
                refresh_list()

        edit_button.Bind(wx.EVT_BUTTON, edit_selected)
        diagnostics_button.Bind(wx.EVT_BUTTON, run_diagnostics)
        quill_key_button.Bind(wx.EVT_BUTTON, change_quill_key)
        record_button.Bind(wx.EVT_BUTTON, record_keys)
        listbox.Bind(wx.EVT_LISTBOX_DCLICK, edit_selected)
        search.Bind(wx.EVT_TEXT, lambda _e: refresh_list())
        search.Bind(wx.EVT_TEXT_ENTER, lambda _e: listbox.SetFocus())
        refresh_list(keep=0)
        call_after = getattr(wx, "CallAfter", None)
        if callable(call_after):
            call_after(search.SetFocus)

        self._show_modal_dialog(dialog, "Keymap Editor")
        dialog.Destroy()

    def _apply_keymap_binding(
        self, command_id: str, new_binding: str, *, parent: object = None
    ) -> bool:
        """Validate, resolve conflicts, normalise, and persist a new keybinding.

        Returns True when applied. Accepts alias/any-order spellings (via
        ``parse_binding``) but rejects keys the dispatch layer cannot fire, so a
        binding is never assigned yet inert. On conflict the user is told which
        command owns the key and offered a reassign.
        """
        wx = self._wx
        if not new_binding:
            self._show_message_box(
                "Keybinding cannot be blank.", "Keymap Editor", wx.ICON_ERROR | wx.OK
            )
            return False
        prefix = self._quill_key_prefix()
        parsed = parse_binding(new_binding, quill_key_prefix=prefix)
        if parsed is None:
            self._show_message_box(
                "Keybinding format is not recognised. Try something like Ctrl+Shift+K, "
                "or a QUILL key chord like Ctrl+Shift+Grave, S.",
                "Keymap Editor",
                wx.ICON_ERROR | wx.OK,
            )
            return False
        canonical = parsed.canonical
        if not self._binding_is_dispatchable(canonical):
            self._show_message_box(
                f"QUILL cannot bind '{format_binding_for_display(canonical, prefix=prefix)}' "
                "as a shortcut yet. Choose a different key.",
                "Keymap Editor",
                wx.ICON_ERROR | wx.OK,
            )
            return False
        if command_id.startswith("quill.quick_nav."):
            if (
                parsed.is_chord
                or parsed.segments[0].modifiers
                or (len(parsed.segments[0].key) != 1 and parsed.segments[0].key != "Tab")
            ):
                self._show_message_box(
                    "QUILL Quick Nav bindings must be a single key or Tab.",
                    "Keymap Editor",
                    wx.ICON_ERROR | wx.OK,
                )
                return False
        conflicts = find_keymap_conflicts(
            self.keymap, command_id, canonical, quill_key_prefix=prefix
        )
        if conflicts:
            titles = self._keymap_command_titles()
            owners = ", ".join(titles.get(other, other) for other in conflicts)
            mine = titles.get(command_id, command_id)
            display = format_binding_for_display(canonical, prefix=prefix)
            answer = self._show_message_box(
                f"{display} is already assigned to {owners}.\n\n"
                f'Reassign it to "{mine}"? The other command'
                f"{'s' if len(conflicts) > 1 else ''} will become unassigned.",
                "Keymap Editor",
                wx.ICON_WARNING | wx.YES_NO | wx.NO_DEFAULT,
            )
            if answer != wx.ID_YES:
                self._set_status("Keymap edit cancelled")
                return False
            for other in conflicts:
                self.keymap[other] = ""
        self.keymap[command_id] = canonical
        save_keymap(self.keymap)
        self._mark_keyboard_pack_custom()
        self._reload_shortcuts_from_keymap()
        self._set_status(f"Updated keybinding for {command_id}")
        return True

    def _rebind_quill_key(self, *, parent: object = None) -> str | None:
        """Rebind the QUILL key prefix and rewrite every chord to follow it.

        Returns the new canonical prefix when applied, or ``None`` when
        cancelled or rejected. The QUILL key is the chord prefix
        (``settings.quill_key_binding``, default ``Ctrl+Shift+Grave``); every
        QUILL-key command is stored as ``"<prefix>, <second-key>"`` and chord
        dispatch (:meth:`_chord_command_for_event`) matches that stored form
        against the live prefix. So changing the prefix requires rewriting
        every stored chord to the new prefix, or those commands go inert
        (pressed prefix enters QUILL-key mode, but no chord matches).
        """
        wx = self._wx
        old_prefix = self._quill_key_prefix()
        old_canonical = canonical_binding(old_prefix, quill_key_prefix=old_prefix) or old_prefix
        with wx.TextEntryDialog(
            parent or self.frame,
            (
                "Enter the new QUILL key prefix (the chord starter), for "
                "example Ctrl+Shift+Grave or Ctrl+Alt+Q. Every QUILL-key "
                "chord will be rewritten to use it."
            ),
            "Change the QUILL Key",
            value=old_prefix,
        ) as entry:
            if self._show_modal_dialog(entry, "Change the QUILL Key") != wx.ID_OK:
                return None
            raw = entry.GetValue().strip()
        if not raw:
            self._set_status("QUILL key change cancelled")
            return None
        parsed = parse_binding(raw, quill_key_prefix=old_prefix)
        if parsed is None or parsed.is_chord or len(parsed.segments) != 1:
            self._show_message_box(
                "That is not a valid QUILL key prefix. It must be a single "
                "key combination such as Ctrl+Shift+Grave or Ctrl+Alt+Q, "
                "not a two-key chord.",
                "Change the QUILL Key",
                wx.ICON_ERROR | wx.OK,
            )
            return None
        new_canonical = parsed.canonical
        if not self._binding_is_dispatchable(new_canonical):
            self._show_message_box(
                f"QUILL cannot bind "
                f"'{format_binding_for_display(new_canonical, prefix=old_prefix)}' "
                "as the QUILL key. Choose a different combination.",
                "Change the QUILL Key",
                wx.ICON_ERROR | wx.OK,
            )
            return None
        if new_canonical == old_canonical:
            self._set_status("QUILL key unchanged")
            return None
        # Another command already uses this combination on its own.
        conflicts = [
            cid
            for cid, binding in self.keymap.items()
            if binding and canonical_binding(binding, quill_key_prefix=old_prefix) == new_canonical
        ]
        if conflicts:
            titles = self._keymap_command_titles()
            owners = ", ".join(titles.get(cid, cid) for cid in conflicts)
            answer = self._show_message_box(
                f"{format_binding_for_display(new_canonical, prefix=old_prefix)} is already "
                f"assigned to {owners}.\n\nUse it as the QUILL key anyway? The other "
                f"command{'s' if len(conflicts) > 1 else ''} will become unassigned.",
                "Change the QUILL Key",
                wx.ICON_WARNING | wx.YES_NO | wx.NO_DEFAULT,
            )
            if answer != wx.ID_YES:
                self._set_status("QUILL key change cancelled")
                return None
            for cid in conflicts:
                self.keymap[cid] = ""
        # Rewrite every stored chord from the old prefix to the new prefix.
        rewritten_map = rewrite_chord_prefixes(
            self.keymap, old_prefix=old_prefix, new_prefix=new_canonical
        )
        rewritten = sum(
            1
            for cid, binding in self.keymap.items()
            if binding and rewritten_map.get(cid) != binding
        )
        self.keymap = rewritten_map
        self.settings.quill_key_binding = new_canonical
        from quill.core.settings import save_settings as _save_settings

        _save_settings(self.settings)
        save_keymap(self.keymap)
        self._mark_keyboard_pack_custom()
        self._reload_shortcuts_from_keymap()
        self._set_status(
            f"QUILL key changed to "
            f"{format_binding_for_display(new_canonical, prefix=new_canonical)} "
            f"({rewritten} chord(s) rewritten)"
        )
        return new_canonical

    # ----- record-keys capture ----------------------------------------------

    def _event_to_binding_string(self, event: object) -> str | None:
        """Convert a key-down event into a binding string, or None for a bare modifier."""
        key_code = event.GetKeyCode()
        if self._is_bare_modifier_key(key_code):
            return None
        parts: list[str] = []
        if event.ControlDown():
            parts.append("Ctrl")
        if event.AltDown():
            parts.append("Alt")
        if event.ShiftDown():
            parts.append("Shift")
        token = self._key_code_to_token(key_code)
        if token is None:
            return None
        parts.append(token)
        return "+".join(parts)

    def _key_code_to_token(self, key_code: int) -> str | None:
        wx = self._wx
        named = {
            getattr(wx, "WXK_RETURN", 13): "Enter",
            getattr(wx, "WXK_TAB", 9): "Tab",
            getattr(wx, "WXK_SPACE", 32): "Space",
            getattr(wx, "WXK_ESCAPE", 27): "Escape",
            getattr(wx, "WXK_DELETE", 127): "Delete",
            getattr(wx, "WXK_BACK", 8): "Backspace",
            getattr(wx, "WXK_HOME", 313): "Home",
            getattr(wx, "WXK_END", 312): "End",
            getattr(wx, "WXK_LEFT", 314): "Left",
            getattr(wx, "WXK_RIGHT", 316): "Right",
            getattr(wx, "WXK_UP", 315): "Up",
            getattr(wx, "WXK_DOWN", 317): "Down",
        }
        for index in range(1, 13):
            named[getattr(wx, f"WXK_F{index}", 339 + index)] = f"F{index}"
        if key_code in named:
            return named[key_code]
        if 32 < key_code < 127:
            return chr(key_code).upper()
        return None

    def _capture_keybinding(self, parent: object) -> str | None:
        """Open a tiny modal that records the next key chord and returns it."""
        wx = self._wx
        dialog = wx.Dialog(parent, title="Record Keys")
        captured: dict[str, str] = {}
        root = wx.BoxSizer(wx.VERTICAL)
        prompt = wx.StaticText(
            dialog,
            label=(
                "Press the key combination you want and it appears in Search. "
                "Press Escape, or choose Cancel, to stop without recording."
            ),
        )
        prompt.SetName("Press a key combination to record")
        root.Add(prompt, 1, wx.ALL | wx.EXPAND, 12)
        cancel_button = wx.Button(dialog, id=wx.ID_CANCEL, label="Cancel")
        buttons = wx.StdDialogButtonSizer()
        buttons.AddButton(cancel_button)
        buttons.Realize()
        root.Add(buttons, 0, wx.ALL | wx.EXPAND, 8)
        dialog.SetSizer(root)
        dialog.SetSize((420, 180))

        def on_key(event: object) -> None:
            key_code = event.GetKeyCode()
            if key_code in {getattr(wx, "WXK_ESCAPE", 27), 27}:
                dialog.EndModal(wx.ID_CANCEL)
                return
            binding = self._event_to_binding_string(event)
            if binding is None:
                return  # bare modifier — keep waiting for the real key
            captured["binding"] = binding
            dialog.EndModal(wx.ID_OK)

        cancel_button.Bind(wx.EVT_BUTTON, lambda _e: dialog.EndModal(wx.ID_CANCEL))
        dialog.Bind(wx.EVT_CHAR_HOOK, on_key)
        # The Cancel button carries both ids: Enter is captured by on_key as the
        # Enter key, and Escape closes via the same button (no keyboard trap).
        apply_modal_ids(dialog, affirmative_id=wx.ID_CANCEL, escape_id=wx.ID_CANCEL)
        result = self._show_modal_dialog(dialog, "Record Keys")
        dialog.Destroy()
        if result == wx.ID_OK:
            return captured.get("binding")
        return None

    # ----- diagnostics + self-heal ------------------------------------------

    def _keymap_dispatchable_commands(self, known: set[str]) -> set[str]:
        return {
            command_id
            for command_id in known
            if self._binding_is_dispatchable(self._binding_for(command_id) or "")
        }

    def _run_keymap_diagnostics(self, *, parent: object = None) -> None:
        wx = self._wx
        prefix = self._quill_key_prefix()
        titles = self._keymap_command_titles()
        known = set(titles)
        dispatchable = self._keymap_dispatchable_commands(known)
        report = diagnose_keymap(
            self.keymap,
            known_commands=known,
            dispatchable_commands=dispatchable,
            quill_key_prefix=prefix,
        )
        lines: list[str] = []
        if report.duplicates:
            lines.append("Duplicate shortcuts (the same key on more than one command):")
            for canonical, ids in report.duplicates.items():
                display = format_binding_for_display(canonical, prefix=prefix)
                names = ", ".join(titles.get(i, i) for i in ids)
                lines.append(f"  {display}: {names}")
            lines.append("")
        if report.invalid:
            lines.append("Unreadable bindings (will be removed by Heal):")
            for command_id, binding in report.invalid.items():
                lines.append(f"  {titles.get(command_id, command_id)}: '{binding}'")
            lines.append("")
        if report.unknown_commands:
            lines.append("Bindings for commands that no longer exist (removed by Heal):")
            for command_id in report.unknown_commands:
                lines.append(f"  {command_id}")
            lines.append("")
        if report.missing_dispatch:
            lines.append("Assigned but inert (the key cannot fire; reassign these):")
            for command_id in report.missing_dispatch:
                binding = self._binding_for(command_id) or ""
                display = format_binding_for_display(binding, prefix=prefix)
                lines.append(f"  {titles.get(command_id, command_id)}: {display}")
            lines.append("")

        if report.ok:
            self._show_message_box(
                "No keyboard problems found. Every shortcut is unique, readable, and wired up.",
                "Keymap Diagnostics",
                wx.ICON_INFORMATION | wx.OK,
            )
            self._set_status("Keymap diagnostics: all clear")
            return

        repairable = bool(report.invalid or report.unknown_commands)
        summary = f"Found {report.issue_count} kind(s) of issue.\n\n" + "\n".join(lines).rstrip()
        if repairable:
            summary += (
                "\n\nHeal now? This removes unreadable and orphaned bindings and "
                "re-applies the keymap so menus and shortcuts match. Duplicates and "
                "inert keys are listed for you to fix by hand."
            )
            answer = self._show_message_box(
                summary, "Keymap Diagnostics", wx.ICON_WARNING | wx.YES_NO | wx.NO_DEFAULT
            )
            if answer == wx.ID_YES:
                self._heal_keymap(report.invalid, report.unknown_commands)
        else:
            self._show_message_box(summary, "Keymap Diagnostics", wx.ICON_WARNING | wx.OK)
            self._set_status("Keymap diagnostics: review the report")

    def _heal_keymap(self, invalid: dict[str, str], unknown: list[str]) -> None:
        removed = 0
        for command_id in list(invalid) + list(unknown):
            if command_id in self.keymap:
                del self.keymap[command_id]
                removed += 1
        save_keymap(self.keymap)
        self._mark_keyboard_pack_custom()
        self._reload_shortcuts_from_keymap()
        self._set_status(
            f"Healed keymap: removed {removed} bad entr{'y' if removed == 1 else 'ies'} "
            "and re-applied shortcuts"
        )
