"""Accessible Vault UI (MainFrame mixin).

Wires the vault commands over ``quill.core.vault``:

* **Open Vault** — choose a folder; QUILL scans and indexes it and remembers it.
* **Follow Link** — with the caret on a ``[[wikilink]]``, open the target note at
  its heading/block; offer to create a missing note; ask (never guess) when a
  name is ambiguous.
* **Show Backlinks** — an accessible list of the notes that link to the current
  note, each read with its linking line; Enter opens the source at the link.
* **Insert Link to Note** — pick a note by title and insert ``[[Title]]``.

The pure helper ``relative_note_path`` is unit-tested; the rest is a wiring layer
over MainFrame (``_wx``, ``frame``, ``editor``, ``document``, ``settings``,
``commands``, ``_binding_for``, ``_show_modal_dialog``, ``open_file``,
``_set_status``, ``_announce``).
"""

from __future__ import annotations

from pathlib import Path


def relative_note_path(vault_root: Path | None, doc_path: Path | None) -> str | None:
    """Return ``doc_path`` relative to ``vault_root`` as POSIX, or None if outside."""
    if vault_root is None or doc_path is None:
        return None
    try:
        return doc_path.resolve().relative_to(vault_root.resolve()).as_posix()
    except (ValueError, OSError):
        return None


class VaultMixin:
    """The ``vault.*`` command handlers."""

    def open_vault(self) -> None:
        """Choose a vault folder, scan + index it, and remember it."""
        wx = self._wx
        picker = wx.DirDialog(
            self.frame,
            "Choose a vault folder (a folder of notes)",
            style=wx.DD_DEFAULT_STYLE | wx.DD_DIR_MUST_EXIST,
        )
        try:
            if self._show_modal_dialog(picker, "Open Vault") != wx.ID_OK:
                self._set_status("Open Vault cancelled")
                return
            folder = picker.GetPath()
        finally:
            picker.Destroy()
        self.settings.vault_root = folder
        from quill.core.settings import save_settings

        save_settings(self.settings)
        self._vault = None  # force a reload
        if self._ensure_vault() is None:
            self._set_status("Could not open the vault")
            return
        notes = len(self._vault.notes)
        links = sum(len(targets) for targets in self._vault_index.forward.values())
        self._announce(f"Vault {Path(folder).name}: {notes} notes, {links} links.")

    def _ensure_vault(self):
        """Load and index the active vault on demand; cache it. Returns the Vault."""
        if getattr(self, "_vault", None) is not None:
            return self._vault
        root = str(getattr(self.settings, "vault_root", "") or "").strip()
        if not root or not Path(root).is_dir():
            return None
        from quill.core.vault import build_index, build_resolver, scan_vault

        self._set_status("Scanning vault...")
        self._vault = scan_vault(Path(root))
        self._vault_resolver = build_resolver(self._vault)
        self._vault_index = build_index(self._vault, self._vault_resolver)
        return self._vault

    def _vault_root_path(self) -> Path | None:
        root = str(getattr(self.settings, "vault_root", "") or "").strip()
        return Path(root) if root and Path(root).is_dir() else None

    def follow_wikilink(self) -> None:
        """Open the note the caret's ``[[link]]`` points to (Follow Link)."""
        from quill.core.vault import link_at_offset, resolve_link

        if self._ensure_vault() is None:
            self._set_status("Open a vault first (Tools > Vault > Open Vault)")
            return
        link = link_at_offset(self.editor.GetValue(), self.editor.GetInsertionPoint())
        if link is None:
            self._set_status("No wikilink at the cursor")
            return
        source_rel = relative_note_path(self._vault_root_path(), self._document_path())
        target = resolve_link(self._vault, self._vault_resolver, link, source_rel or "")
        if target is None:
            self._offer_create_note(link.target)
            return
        if target.ambiguous:
            chosen = self._choose_ambiguous(link.target, target.candidates)
            if chosen is None:
                return
            self._open_vault_note(chosen, target.offset)
            return
        self._open_vault_note(target.path, target.offset)

    def show_backlinks(self) -> None:
        """List the notes that link to the current note (Backlinks)."""
        from quill.core.vault import backlinks

        if self._ensure_vault() is None:
            self._set_status("Open a vault first (Tools > Vault > Open Vault)")
            return
        rel = relative_note_path(self._vault_root_path(), self._document_path())
        if rel is None or rel not in self._vault.notes:
            self._set_status("Save this note inside the vault to see its backlinks")
            return
        links = backlinks(self._vault_index, rel)
        if not links:
            self._set_status("No backlinks: no other note links here yet")
            return
        items = [
            (
                f"{self._vault.notes[bl.source_path].title}: {bl.context}",
                (bl.source_path, bl.offset),
            )
            for bl in links
        ]
        self._announce(f"{len(links)} notes link here.")
        self._show_vault_list(f"Backlinks to {self._vault.notes[rel].title}", items)

    def insert_wikilink(self) -> None:
        """Pick a note and insert a ``[[Title]]`` link at the cursor."""
        if self._ensure_vault() is None:
            self._set_status("Open a vault first (Tools > Vault > Open Vault)")
            return
        titles = sorted({info.title for info in self._vault.notes.values()})
        if not titles:
            self._set_status("The vault has no notes to link to")
            return
        items = [(title, title) for title in titles]
        self._show_vault_list("Insert link to note", items, on_activate=self._insert_link_text)

    # --- helpers ----------------------------------------------------------

    def _document_path(self) -> Path | None:
        document = getattr(self, "document", None)
        path = getattr(document, "path", None)
        return path if isinstance(path, Path) else None

    def _open_vault_note(self, rel_path: str, offset: int) -> None:
        from quill.ui.main_frame_story_studio import offset_to_line

        root = self._vault_root_path()
        if root is None:
            return
        path = root / rel_path
        line: int | None = None
        if offset:
            try:
                text = path.read_text(encoding="utf-8")
            except OSError:
                text = ""
            line = offset_to_line(text, offset)
        self.open_file(path, line=line)

    def _insert_link_text(self, title: str) -> None:
        self.editor.WriteText(f"[[{title}]]")
        self._announce(f"Linked to {title}")

    def _offer_create_note(self, name: str) -> None:
        wx = self._wx
        root = self._vault_root_path()
        clean = name.strip()
        if root is None or not clean:
            self._set_status("No note to follow")
            return
        if (
            self._show_message_box(
                f'No note named "{clean}". Create it?',
                "Follow Link",
                wx.YES_NO | wx.ICON_QUESTION,
            )
            != wx.ID_YES
        ):
            self._set_status("No note created")
            return
        safe = "".join(ch for ch in clean if ch not in '<>:"/\\|?*').strip() or "Untitled"
        path = root / f"{safe}.md"
        try:
            if not path.exists():
                path.write_text(f"# {clean}\n", encoding="utf-8")
        except OSError as error:
            self._set_status(f"Could not create note: {error}")
            return
        self._vault = None  # re-index to include the new note
        self._ensure_vault()
        self.open_file(path)
        self._announce(f"Created and opened {clean}")

    def _choose_ambiguous(self, name: str, candidates: tuple[str, ...]) -> str | None:
        wx = self._wx
        dialog = wx.SingleChoiceDialog(
            self.frame,
            f'Several notes are named "{name}". Open which?',
            "Follow Link",
            list(candidates),
        )
        try:
            if self._show_modal_dialog(dialog, "Follow Link") != wx.ID_OK:
                return None
            index = dialog.GetSelection()
        finally:
            dialog.Destroy()
        return candidates[index] if 0 <= index < len(candidates) else None

    def _show_vault_list(self, heading: str, items, on_activate=None) -> None:
        from quill.ui.dialog_contract import apply_modal_ids
        from quill.ui.vault_dialogs import VaultListDialog

        wx = self._wx
        activate = on_activate or (lambda payload: self._open_vault_note(payload[0], payload[1]))
        view = VaultListDialog(wx, heading=heading, items=items, on_activate=activate)
        dialog = wx.Dialog(
            self.frame, title=heading, style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
        )
        outer = view.populate(dialog)
        buttons = dialog.CreateStdDialogButtonSizer(wx.OK | wx.CANCEL)
        outer.Add(buttons, 0, wx.EXPAND | wx.ALL, 10)
        apply_modal_ids(
            dialog, affirmative_id=wx.ID_OK, affirmative_label="&Open", cancel_id=wx.ID_CANCEL
        )
        try:
            self._show_modal_dialog(dialog, heading)
        finally:
            dialog.Destroy()

    def _register_vault_commands(self) -> None:
        self.commands.try_register(
            "vault.open", "Open Vault", self.open_vault, self._binding_for("vault.open")
        )
        self.commands.try_register(
            "vault.follow_link",
            "Follow Wikilink",
            self.follow_wikilink,
            self._binding_for("vault.follow_link"),
        )
        self.commands.try_register(
            "vault.backlinks",
            "Show Backlinks",
            self.show_backlinks,
            self._binding_for("vault.backlinks"),
        )
        self.commands.try_register(
            "vault.insert_link",
            "Insert Link to Note",
            self.insert_wikilink,
            self._binding_for("vault.insert_link"),
        )
