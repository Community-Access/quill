"""Rich document mode + the Document Format switcher for ``MainFrame``.

One Editor, Every Format (0.9.0-beta3): every document lives in the one
QuillRichEdit surface, and this mixin gives that surface its two document
modes and the transitions between them.

* **Plain-markup mode** (``editor_mode == "markup"``): byte-for-byte the
  classic behavior — the buffer is canonical QUILL markup, formatting
  commands insert format-native tags.
* **Rich mode** (``"rich"``): an .rtf loaded natively through the Text Object
  Model. Formatting commands apply *real* formatting via TOM; the buffer (and
  ``Document.text``) mirror the plain text, so search / spell / AI /
  read-aloud / braille keep working unchanged. Save writes real RTF via TOM.
* **Converted rich** (``"rich_converted"``): the failsafe floor when the TOM
  is unavailable (macOS, comtypes missing, any COM failure). The buffer holds
  the converted markup — exactly the classic .rtf behavior — and save
  re-serializes through the RTF writer. Never a blank editor.

The **Document Format switcher** (Phase 4) moves a document between Plain
text / Markdown / HTML / Rich Text (RTF) mid-session through the
``RichDocument`` bridge, with honest-fidelity warnings before anything lossy.
It is reachable four ways — Format menu, command palette, the
``format.switch_document_format`` keyboard command, and the interactive
``document_format`` status bar cell — all dispatching one handler.

Mixin over ``MainFrame`` per the decomposition rule (CLAUDE.md): methods
reference instance state via ``self`` and are wired from ``main_frame.py``.
"""

from __future__ import annotations

from pathlib import Path

from quill.io.rtf import markdown_to_rtf, read_rtf_sanitized, rtf_to_markdown
from quill.io.rtf_model import rich_to_rtf, rtf_to_rich, scan_rtf_features

#: The switcher's target formats: value -> (menu label, save suffix).
DOCUMENT_FORMATS: dict[str, tuple[str, str]] = {
    "plain": ("Plain text", ".txt"),
    "markdown": ("Markdown", ".md"),
    "html": ("HTML", ".html"),
    "rtf": ("Rich Text (RTF)", ".rtf"),
    "docx": ("Word (.docx)", ".docx"),
}


class RichModeMixin:
    # ------------------------------------------------------------------ #
    # Mode state (Phase 2)
    # ------------------------------------------------------------------ #

    def _current_editor_mode(self) -> str:
        """The active tab's editor mode: ``markup`` / ``rich`` / ``rich_converted``."""
        try:
            tab = self._active_tab()
        except (IndexError, AttributeError):
            return "markup"
        return str(getattr(tab, "editor_mode", "markup") or "markup")

    def _active_richedit(self) -> object | None:
        """The active editor's :class:`QuillRichEdit` wrapper, or ``None``."""
        return getattr(getattr(self, "editor", None), "quill_richedit", None)

    def _rich_capable(self) -> bool:
        """True when the active editor can host native rich content (TOM up)."""
        wrapper = self._active_richedit()
        try:
            return wrapper is not None and bool(wrapper.rtf_available())
        except Exception:  # noqa: BLE001 - capability probe must never raise
            return False

    # ------------------------------------------------------------------ #
    # Open / save (Phase 2)
    # ------------------------------------------------------------------ #

    def _enter_rich_mode_for_open(self, path: Path, document: object) -> None:
        """Promote a freshly opened .rtf tab to rich mode where the TOM allows.

        The tab was just created with the *converted* text (the classic
        behavior), so every failure path below simply stays on that content as
        ``rich_converted`` — the document is never blank. On the native path
        the sanitized RTF (rtf_safety runs in front of every ingest) replaces
        the control content via the TOM and ``Document.text`` mirrors the
        control's plain text.
        """
        tab = self._active_tab()
        wrapper = self._active_richedit()
        if wrapper is None or not self._rich_capable():
            tab.editor_mode = "rich_converted"
            self._set_status(f"Opened {path.name} converted; native rich text is unavailable here.")
            self._refresh_statusbar()
            return
        try:
            safety = read_rtf_sanitized(path)
            wrapper.set_rtf(safety.sanitized_rtf.encode("utf-8", errors="replace"))
        except Exception:  # noqa: BLE001 - any failure falls back to converted
            tab.editor_mode = "rich_converted"
            self._set_status(f"Opened {path.name} converted; the rich load failed.")
            self._refresh_statusbar()
            return
        tab.editor_mode = "rich"
        # Mirror the plain text so autosave/metrics/outline/AI need no changes,
        # without marking the freshly opened document dirty.
        document.text = wrapper.get_plain_text()
        document.modified = False
        self._refresh_statusbar()

    def _save_rich_document_natively(self, document: object, target: Path | None) -> bool:
        """Save the active rich tab natively. Returns True when handled.

        Two genuine rich cases: an .rtf destination saves straight through the
        TOM (no conversion, no fidelity loss), and a docx-rich tab saving to
        .docx runs the RichDocument bridge (``rich_to_docx_bytes``) behind the
        one-time backup of a fidelity-flagged original. Everything else
        (markup tabs, rich_converted, Save As to a different format) returns
        False so the classic conversion writer runs.
        """
        if self._current_editor_mode() != "rich":
            return False
        try:
            tab = self._active_tab()
        except (IndexError, AttributeError):
            return False
        if getattr(tab, "document", None) is not document:
            return False
        target_path = target or getattr(document, "path", None)
        if target_path is None:
            return False
        suffix = Path(target_path).suffix.lower()
        wrapper = self._active_richedit()
        if wrapper is None:
            return False
        from quill.ui.richedit_rtf_surface import RichEditRtfError

        if suffix == ".rtf":
            try:
                wrapper.save_rtf(str(target_path))
            except RichEditRtfError as error:
                # Surface through the caller's existing save error handling.
                raise OSError(str(error)) from error
            document.mark_saved(Path(target_path))
            return True
        if suffix == ".docx" and getattr(tab, "docx_rich", False):
            self._save_docx_rich_tab(tab, document, Path(target_path))
            return True
        return False

    def _save_docx_rich_tab(self, tab: object, document: object, target: Path) -> None:
        """Materialize a docx-rich tab back to .docx through the bridge.

        Reconstructive by design (control RTF -> RichDocument ->
        ``rich_to_docx_bytes``), so a fidelity-flagged original gets a
        timestamped backup alongside before its first overwrite — QUILL never
        silently rewrites someone's Word file.
        """
        from quill.io.docx_writer import rich_to_docx_bytes
        from quill.ui.richedit_rtf_surface import RichEditRtfError

        wrapper = self._active_richedit()
        try:
            rtf = bytes(wrapper.get_rtf()).decode("utf-8", errors="replace")
        except RichEditRtfError as error:
            raise OSError(str(error)) from error
        if (
            getattr(tab, "docx_flagged", False)
            and not getattr(tab, "rich_backup_done", False)
            and target.exists()
        ):
            backup = self._backup_original_docx(target)
            tab.rich_backup_done = True
            if backup is not None:
                self._set_status(f"Backed up the original to {backup.name}")
        data = rich_to_docx_bytes(rtf_to_rich(rtf))
        from quill.core.storage import write_bytes_atomic

        write_bytes_atomic(target, data)
        document.mark_saved(target)

    @staticmethod
    def _backup_original_docx(target: Path) -> Path | None:
        """Copy the original .docx to a timestamped sibling (best-effort)."""
        from datetime import UTC, datetime
        from shutil import copy2

        stamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
        backup = target.with_name(f"{target.stem}.backup-{stamp}{target.suffix}")
        try:
            copy2(target, backup)
        except OSError:
            return None
        return backup

    def _enter_docx_rich_mode_for_open(self, path: Path, document: object) -> None:
        """Offer/enter rich editing for a freshly opened .docx (Phase 7).

        The tab already holds the extracted text (the classic floor); every
        failure or decline below simply stays there. A clean file (nothing
        flagged by ``scan_docx_features``) opens rich without a dialog; a
        flagged file gets the three-way choice — rich edit with the listed
        losses, read-extract as today, or edit a copy.
        """
        try:
            from quill.io.docx_reader import (
                python_docx_available,
                read_docx_rich,
                scan_docx_features,
            )
        except Exception:  # noqa: BLE001 - the io layer is a soft boundary here
            return
        if not python_docx_available() or not self._rich_capable():
            return
        findings = scan_docx_features(path)
        choice = "rich"
        if findings:
            choice = self._offer_docx_rich_choice(path, findings)
        if choice == "text":
            return
        open_path = path
        if choice == "copy":
            copied = self._backup_original_docx(path)
            if copied is None:
                self._set_status("Could not create a copy; opened read-extract instead")
                return
            open_path = copied
        tab = self._active_tab()
        wrapper = self._active_richedit()
        try:
            rich = read_docx_rich(open_path)
            wrapper.set_rtf(rich_to_rtf(rich).encode("utf-8", errors="replace"))
        except Exception:  # noqa: BLE001 - any failure stays on read-extract
            self._set_status(f"Opened {path.name} as extracted text; the rich load failed.")
            return
        tab.editor_mode = "rich"
        tab.docx_rich = True
        tab.docx_flagged = bool(findings)
        if choice == "copy":
            document.path = open_path
        document.text = wrapper.get_plain_text()
        document.modified = False
        self._set_status_quiet(f"Opened {Path(open_path).name} as Rich Text (Word)")
        self._announce("Opened as Rich Text. Headings and bold are shown formatted.")
        self._refresh_statusbar()

    def _offer_docx_rich_choice(self, path: Path, findings: list[str]) -> str:
        """The docx honest-fidelity choice: ``rich`` / ``text`` / ``copy``.

        Read-extract is the default (safest) answer; the losses are named
        specifically, never as a vague "some formatting may be lost".
        """
        wx = self._wx
        inventory = ", ".join(findings)
        choices = [
            "Open for reading and plain editing (recommended)",
            f"Edit as Rich Text — these will not survive a save: {inventory}",
            "Edit a copy as Rich Text (the original stays untouched)",
        ]
        dialog = wx.SingleChoiceDialog(
            self.frame,
            f"{path.name} contains features QUILL's rich editor cannot carry: "
            f"{inventory}.\n\nHow should it open?",
            "Open Word document",
            choices,
        )
        try:
            result = self._show_modal_dialog(dialog, "Open Word document")
            if result != wx.ID_OK:
                return "text"
            selection = int(dialog.GetSelection())
        finally:
            dialog.Destroy()
        return ("text", "rich", "copy")[max(0, min(2, selection))]

    def _rich_autosave_payload(self) -> bytes | None:
        """RTF bytes for the rich autosave sidecar, or None off the rich path.

        Rich-mode TOM formatting never changes the plain text, so a text-only
        snapshot would silently lose formatting in a crash. The autosave path
        stores these bytes alongside the plain snapshot; recovery restores them
        through ``set_rtf``.
        """
        if self._current_editor_mode() != "rich":
            return None
        wrapper = self._active_richedit()
        if wrapper is None:
            return None
        try:
            return bytes(wrapper.get_rtf())
        except Exception:  # noqa: BLE001 - autosave is best-effort by contract
            return None

    def _maybe_restore_rich_snapshot(self, text_snapshot: object) -> None:
        """Reload rich formatting from the ``.rtfsnap`` beside a text snapshot.

        Crash recovery restored the plain text already; when the crashed
        session also wrote RTF sidecars for this document (same key prefix in
        the same session folder), the newest one is loaded through ``set_rtf``
        so the recovered document keeps its formatting. Best-effort by the
        recovery contract: any failure leaves the plain-text recovery intact.
        """
        try:
            snap = Path(str(text_snapshot))
            key = snap.name.split("-", 1)[0]
            sidecars = sorted(snap.parent.glob(f"{key}-*.rtfsnap"), reverse=True)
            if not sidecars:
                return
            wrapper = self._active_richedit()
            if wrapper is None or not self._rich_capable():
                return
            wrapper.set_rtf(sidecars[0].read_bytes())
            self._active_tab().editor_mode = "rich"
            self.document.text = wrapper.get_plain_text()
            self.document.modified = True
            self._refresh_statusbar()
        except Exception:  # noqa: BLE001 - never let formatting break recovery
            return

    def _mark_rich_formatting_dirty(self) -> None:
        """Explicit dirty marking for TOM formatting (EVT_TEXT never fires).

        The plain text is unchanged, so ``set_text`` would no-op;
        ``mark_content_changed`` bumps ``modified`` + ``revision`` so autosave
        takes a fresh snapshot (with its RTF sidecar) and the title shows
        dirty, like any text change.
        """
        editor = getattr(self, "editor", None)
        if editor is None:
            return
        self.document.set_text(editor.GetValue())
        self.document.mark_content_changed()
        self._refresh_title()

    # ------------------------------------------------------------------ #
    # Mode-polymorphic formatting (Phase 3)
    # ------------------------------------------------------------------ #

    def _rich_format_command(self, method: str, announce: str, *args: object) -> bool:
        """Run a rich-mode formatting command on the wrapper. True when handled.

        Called first by the format commands; returns False in markup modes so
        the classic tag-insertion path runs. In rich mode the TOM applies the
        real formatting, the tab is marked dirty explicitly (formatting fires
        no EVT_TEXT), and the effect is announced plainly ("Bold") — no markup
        qualifier, because there is no markup.
        """
        if self._current_editor_mode() != "rich":
            return False
        wrapper = self._active_richedit()
        if wrapper is None:
            return False
        from quill.ui.richedit_rtf_surface import RichEditRtfError

        try:
            getattr(wrapper, method)(*args)
        except RichEditRtfError as error:
            self._set_status(f"Could not apply {announce.lower()}: {error}")
            return True
        self._mark_rich_formatting_dirty()
        # One spoken message (#728): the status line stays terse and quiet.
        self._set_status_quiet(f"Applied {announce.lower()}" if announce else "Applied formatting")
        self._announce(announce or "Formatting applied")
        return True

    def _rich_apply_run_attrs(self, attrs: dict[str, str], status: str, label: str) -> bool:
        """Map a hidden-codes run-attribute dict onto the TOM. True when handled.

        The Format menu's font/size/color/highlight commands share one
        vocabulary with the hidden-codes system; in rich mode the same
        attributes drive ``ITextFont`` directly. Unmapped attributes return
        False so the caller can say, honestly, that the command is not
        available in Rich Text yet.
        """
        wrapper = self._active_richedit()
        if wrapper is None:
            return False
        mapping = {
            "font-family": wrapper.set_font_name,
            "font-size": lambda v: wrapper.set_font_size(float(v)),
            "color": wrapper.set_color,
            "highlight": wrapper.set_highlight,
        }
        if len(attrs) != 1:
            return False
        ((key, value),) = attrs.items()
        apply = mapping.get(key)
        if apply is None:
            return False
        from quill.ui.richedit_rtf_surface import RichEditRtfError

        try:
            apply(str(value))
        except RichEditRtfError as error:
            self._set_status(f"Could not apply {label.lower()}: {error}")
            return True
        self._mark_rich_formatting_dirty()
        self._set_status(status)  # speaks once; no separate announce (#728)
        return True

    def _offer_plain_text_formatting_choice(self, command_label: str) -> str | None:
        """The plain-text transition prompt (asked once per document).

        Plain text cannot carry bold — that is the promise of .txt. The first
        formatting command offers: treat as Markdown (pin the markup kind),
        convert to Rich Text, or stay plain (and stop asking). Returns the
        remembered choice ("markdown" / "rich" / "plain") or None when the
        user cancelled outright.
        """
        tab = self._active_tab()
        remembered = str(getattr(tab, "plain_format_choice", "") or "")
        if remembered:
            return remembered
        wx = self._wx
        choices = [
            "Treat this document as Markdown",
            "Convert to Rich Text (RTF)",
            "Stay plain text",
        ]
        dialog = wx.SingleChoiceDialog(
            self.frame,
            f"Plain text cannot carry {command_label.lower()}. What should this document be?",
            "Plain text formatting",
            choices,
        )
        try:
            result = self._show_modal_dialog(dialog, "Plain text formatting")
            if result != wx.ID_OK:
                return None
            selection = dialog.GetSelection()
        finally:
            dialog.Destroy()
        choice = ("markdown", "rich", "plain")[max(0, min(2, int(selection)))]
        tab.plain_format_choice = choice
        if choice == "markdown":
            self._pin_markup_kind_for_tab(tab, "markdown")
            self._set_status("Treating this document as Markdown")
        elif choice == "rich":
            self.set_document_format("rtf")
        else:
            self._set_status("Staying plain text; formatting commands will stay quiet")
        return choice

    def _pin_markup_kind_for_tab(self, tab: object, kind: str) -> None:
        """Pin the tab's markup kind (the Document Language machinery's shape)."""

        class _PinnedProfile:
            markup_kind = kind

        tab._language_profile = _PinnedProfile()
        tab._language_profile_pinned = True

    def describe_caret_formatting_rich(self) -> str | None:
        """Describe Formatting's rich branch: live TOM attributes, or None."""
        if self._current_editor_mode() != "rich":
            return None
        wrapper = self._active_richedit()
        if wrapper is None:
            return None
        from quill.ui.richedit_rtf_surface import RichEditRtfError

        try:
            return str(wrapper.caret_format_description())
        except RichEditRtfError:
            return None

    # ------------------------------------------------------------------ #
    # The Document Format switcher (Phase 4)
    # ------------------------------------------------------------------ #

    def current_document_format(self) -> str:
        """The switcher's notion of the current format: a DOCUMENT_FORMATS key."""
        mode = self._current_editor_mode()
        if mode in {"rich", "rich_converted"}:
            try:
                if getattr(self._active_tab(), "docx_rich", False):
                    return "docx"
            except (IndexError, AttributeError):
                pass
            return "rtf"
        context = self._current_markup_context()
        return context if context in DOCUMENT_FORMATS else "plain"

    def _document_format_status_text(self) -> str:
        label = DOCUMENT_FORMATS[self.current_document_format()][0]
        if self._current_editor_mode() == "rich_converted":
            return f"{label} (converted)"
        return label

    def switch_document_format(self) -> None:
        """Open the Document Format switcher (the one handler behind every entry).

        A native popup menu with radio items — wx popup menus are real menus,
        so screen readers announce the items and the checked state for free.
        Reached from the Format menu, the command palette, the
        Ctrl+Shift+Grave, K chord, and the status bar cell alike.
        """
        wx = self._wx
        current = self.current_document_format()
        menu = wx.Menu()
        ids: dict[int, str] = {}
        for value, (label, _suffix) in DOCUMENT_FORMATS.items():
            item_id = wx.NewIdRef()
            item = menu.AppendRadioItem(item_id, label)
            ids[int(item_id)] = value
            if value == current:
                item.Check(True)

        def _on_pick(event: object) -> None:
            picked = ids.get(int(event.GetId()))
            if picked and picked != current:
                self.set_document_format(picked)
            elif picked:
                self._set_status(f"Already editing as {DOCUMENT_FORMATS[picked][0]}")

        menu.Bind(wx.EVT_MENU, _on_pick)
        try:
            self.frame.PopupMenu(menu)
        finally:
            menu.Destroy()

    def set_document_format(self, target: str) -> None:
        """Move the current document to ``target`` format mid-session.

        Conversions run through the shipped bridge (Markdown <-> RTF via
        ``quill/io/rtf.py`` and the ``RichDocument`` model). Anything lossy
        warns first with the specific inventory (``scan_rtf_features``), and
        the file type is retargeted on the next Save As — never silently
        rewritten in place. Announced plainly per the One Editor UX contract.
        """
        if target not in DOCUMENT_FORMATS:
            self._set_status(f"Unknown document format: {target}")
            return
        tab = self._active_tab()
        mode = self._current_editor_mode()
        label, suffix = DOCUMENT_FORMATS[target]

        if target in {"rtf", "docx"}:
            if mode in {"rich", "rich_converted"}:
                # Within the rich family the switch is a save retarget: the
                # live TOM document is already the truth; only the on-disk
                # serialization (native RTF vs the docx bridge) changes.
                tab.docx_rich = target == "docx"
                self._retarget_format_suffix(tab, suffix)
                self._set_status(f"Now saving as {label}")
                self._refresh_statusbar()
                return
            markup = self.editor.GetValue()
            rtf = markdown_to_rtf(markup)
            wrapper = self._active_richedit()
            if wrapper is not None and self._rich_capable():
                try:
                    wrapper.set_rtf(rtf.encode("utf-8", errors="replace"))
                    tab.editor_mode = "rich"
                    self.document.set_text(wrapper.get_plain_text())
                except Exception:  # noqa: BLE001 - fall back to converted rich
                    tab.editor_mode = "rich_converted"
                    self.document.set_text(self.editor.GetValue())
            else:
                # Converted rich: the buffer stays markup; save re-serializes.
                tab.editor_mode = "rich_converted"
                self.document.set_text(self.editor.GetValue())
            tab.docx_rich = target == "docx" and tab.editor_mode == "rich"
            self._retarget_format_suffix(tab, suffix)
            self._set_status_quiet(f"Now editing as {label}")
            self._announce(f"Now editing as {label}. Headings and bold are shown formatted.")
        else:
            if mode in {"rich", "rich_converted"}:
                # Leaving rich: honest fidelity first — say what markup cannot
                # carry *before* the conversion happens.
                rtf_source = None
                if mode == "rich":
                    wrapper = self._active_richedit()
                    if wrapper is not None:
                        try:
                            rtf_source = bytes(wrapper.get_rtf()).decode("utf-8", errors="replace")
                        except Exception:  # noqa: BLE001
                            rtf_source = None
                else:
                    rtf_source = markdown_to_rtf(self.editor.GetValue())
                if rtf_source is not None:
                    features = scan_rtf_features(rtf_source)
                    if features and not self._confirm_lossy_format_switch(label, features):
                        self._set_status("Format switch cancelled")
                        return
                    markup = rtf_to_markdown(rtf_source)
                else:
                    markup = self.editor.GetValue()
                self.editor.ChangeValue(markup)
                tab.editor_mode = "markup"
                tab.docx_rich = False
                self.document.set_text(markup)
            # Markup-to-markup switches keep the text; the pin decides the tags.
            self._pin_markup_kind_for_tab(tab, target)
            self._retarget_format_suffix(tab, suffix)
            self._set_status_quiet(f"Now editing as {label}")
            if target == "markdown":
                self._announce("Now editing as Markdown. Formatting appears as tags.")
            elif target == "html":
                self._announce("Now editing as HTML. Formatting appears as tags.")
            else:
                self._announce("Now editing as plain text.")
        self._refresh_statusbar()
        self._request_menu_refresh()

    def _confirm_lossy_format_switch(self, target_label: str, features: list[str]) -> bool:
        """The honest-fidelity gate: name what will not survive, then ask."""
        wx = self._wx
        inventory = ", ".join(str(f) for f in features)
        dialog = wx.MessageDialog(
            self.frame,
            f"Switching to {target_label} cannot carry: {inventory}.\n\n"
            "Those features will be dropped from the editing buffer (the file "
            "on disk is untouched until you save). Switch anyway?",
            "Some formatting will not survive",
            wx.YES_NO | wx.NO_DEFAULT | wx.ICON_WARNING,
        )
        if hasattr(dialog, "SetYesNoLabels"):
            dialog.SetYesNoLabels(f"Switch to {target_label}", "Cancel")
        try:
            result = self._show_modal_dialog(dialog, "Some formatting will not survive")
        finally:
            dialog.Destroy()
        return result == wx.ID_YES

    def _retarget_format_suffix(self, tab: object, suffix: str) -> None:
        """Record the switcher's save retargeting; Save proposes, never rewrites.

        A document whose path already matches ``suffix`` needs nothing. For
        everything else the pending suffix makes the next Save route through
        Save As with the renamed name proposed, so a .md switched to Rich never
        silently becomes RTF bytes inside a .md file.
        """
        path = getattr(self.document, "path", None)
        if path is not None and Path(path).suffix.lower() == suffix:
            tab.pending_format_suffix = ""
            return
        tab.pending_format_suffix = suffix
        if path is not None:
            proposed = Path(path).with_suffix(suffix).name
            self._set_status(f"Save will propose {proposed}")

    def _pending_format_redirect(self) -> Path | None:
        """The renamed path Save should propose, or None when Save is direct."""
        try:
            tab = self._active_tab()
        except (IndexError, AttributeError):
            return None
        suffix = str(getattr(tab, "pending_format_suffix", "") or "")
        path = getattr(self.document, "path", None)
        if not suffix or path is None:
            return None
        if Path(path).suffix.lower() == suffix:
            tab.pending_format_suffix = ""
            return None
        return Path(path).with_suffix(suffix)
