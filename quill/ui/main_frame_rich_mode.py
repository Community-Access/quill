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

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from quill.core.format_transitions import (
    PlainStyle,
    TransitionPlan,
    convert_text,
    plan_transition,
)
from quill.core.html_to_markdown import contains_html_markup, html_to_markdown
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

    @contextmanager
    def _theme_colour_off(self, wrapper: object) -> Iterator[None]:
        """Take the theme's colour off the story for the duration of a save.

        A dark theme calls ``SetForegroundColour`` on the rich control, and
        wxMSW applies that as an ``SCF_ALL`` character colour -- so it is not a
        view setting at all, it is **on every run in the document**, and the TOM
        writes it into the file. Confirmed live on 2026-09-17
        (``scripts/probe_rich_edits.py``): the saved ``.rtf`` carried a
        ``\\colortbl`` with the theme grey in it, so anybody working in dark mode
        had been sending grey-on-white documents to everybody they shared with,
        and would never see it themselves (bad.md R4).

        ``tomAutoColor`` for the save, the theme back afterwards, and the
        restore in a ``finally`` -- because a save that raises must not leave
        the window unreadable, which is the one failure worse than the bug.
        QuillLite has guarded both directions since it shipped
        (``lite_window_file._write_rtf``); this is QUILL catching up.
        """
        restore = False
        try:
            wrapper.set_document_color(None)
            restore = True
        except Exception:  # noqa: BLE001 - no TOM means no colour to strip
            restore = False
        try:
            yield
        finally:
            if restore:
                try:
                    self._apply_rich_theme_colour()
                except Exception:  # noqa: BLE001 - never leave a save half-failed
                    pass

    def _apply_rich_theme_colour(self) -> None:
        """Put the theme's text colour back on the story after a save."""
        wrapper = self._active_richedit()
        if wrapper is None:
            return
        colour = self.editor.GetForegroundColour()
        wrapper.set_document_color((colour.Red(), colour.Green(), colour.Blue()))

    def _save_rich_document_natively(self, document: object, target: Path | None) -> bool:
        """Save the active rich tab natively. Returns True when handled.

        Rich cases, each converting the *formatted* content rather than the
        plain-text mirror that ``document.text`` holds in rich mode:

        * ``.rtf`` saves straight through the TOM (no conversion, no loss).
        * ``.docx`` (docx-rich tab) runs the RichDocument bridge
          (``rich_to_docx_bytes``) behind a one-time backup of a
          fidelity-flagged original.
        * ``.md`` / ``.html`` reconstruct the RichDocument from the control's
          RTF and render it with ``rich_to_markdown`` (headings, lists, bold,
          italic, links as native Markdown; underline/color/etc. as QUILL's
          hidden-codes spans) -- previously these fell through to the classic
          writer, which serialized the flattened plain-text mirror and lost all
          formatting.

        Everything else (markup tabs, plain text) returns False so the classic
        conversion writer runs.
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
                with self._theme_colour_off(wrapper):
                    wrapper.save_rtf(str(target_path))
            except RichEditRtfError as error:
                # Surface through the caller's existing save error handling.
                raise OSError(str(error)) from error
            document.mark_saved(Path(target_path))
            return True
        if suffix == ".docx" and getattr(tab, "docx_rich", False):
            self._save_docx_rich_tab(tab, document, Path(target_path))
            return True
        if suffix in {".md", ".markdown", ".html", ".htm", ".xhtml"}:
            return self._save_rich_as_markup(document, Path(target_path), suffix, wrapper)
        return False

    def _save_rich_as_markup(
        self, document: object, target: Path, suffix: str, wrapper: object
    ) -> bool:
        """Save a rich tab to Markdown or HTML with its formatting intact.

        Reconstructs the RichDocument from the control's RTF (the same bridge
        the docx-rich save uses) and renders it -- so a Word document opened in
        rich mode and Saved As .md/.html keeps its headings, lists, bold,
        italic, and links instead of collapsing to the plain-text mirror.
        """
        from quill.core.storage import write_text_atomic
        from quill.io.rtf_model import rich_to_markdown, rtf_to_rich
        from quill.ui.richedit_rtf_surface import RichEditRtfError

        try:
            rtf = bytes(wrapper.get_rtf()).decode("utf-8", errors="replace")
        except RichEditRtfError as error:
            raise OSError(str(error)) from error
        markdown = rich_to_markdown(rtf_to_rich(rtf))
        # The document's own encoding and line endings, not UTF-8 and LF (bad.md
        # F4). A Word document opened in rich mode and saved as .md used to come
        # out re-encoded with its CRLFs flattened, which is a different file from
        # the one the person thought they were saving -- and on Windows a .md
        # with LF endings is a file every other tool here will re-save as CRLF,
        # so the diff belongs to QUILL rather than to the author.
        from quill.io.text import _normalize_line_endings

        encoding = str(getattr(document, "encoding", "") or "utf-8")
        line_ending = str(getattr(document, "line_ending", "") or "\r\n")
        if suffix in {".html", ".htm", ".xhtml"}:
            from quill.io.export import markdown_to_html

            content = markdown_to_html(markdown, target.stem, charset=encoding)
        else:
            content = markdown
        content = _normalize_line_endings(content, line_ending)
        try:
            content.encode(encoding)
        except (UnicodeEncodeError, LookupError):
            from quill.io.text import _emit_save_warning

            _emit_save_warning(
                f"{target.name} was written as UTF-8: its text cannot be expressed in {encoding}."
            )
            encoding = "utf-8"
            if suffix in {".html", ".htm", ".xhtml"}:
                from quill.io.export import markdown_to_html

                content = _normalize_line_endings(
                    markdown_to_html(markdown, target.stem, charset=encoding), line_ending
                )
        write_text_atomic(target, content, encoding=encoding, newline="")
        document.mark_saved(target)
        return True

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

    #: The three run attributes whose command is a *toggle*, so the sentence
    #: has to say which way it went (bad.md R8).
    _TOGGLING_RUN_ATTRS = {
        "apply_bold": "Bold",
        "apply_italic": "Italic",
        "apply_underline": "Underline",
    }

    def _rich_toggle_run_attr(self, method: str) -> bool:
        """Toggle bold/italic/underline in rich mode and say the STATE. True when handled.

        "Bold" is what QUILL said for both directions, so the one thing the
        keystroke decided -- on or off -- was the one thing it did not say, and
        a listener with no visual feedback had to type a character to find out.
        The shared surface has answered this since it shipped
        (``toggle_font_attr`` returns the state the control ended in) and
        QuillLite has said "Bold on" all along (bad.md R8, P1.17).
        """
        label = self._TOGGLING_RUN_ATTRS[method]
        if self._current_editor_mode() != "rich":
            return False
        wrapper = self._active_richedit()
        if wrapper is None:
            return False
        toggle = getattr(wrapper, "toggle_font_attr", None)
        if not callable(toggle):
            return self._rich_format_command(method, label)
        from quill.ui.richedit_rtf_surface import RichEditRtfError

        try:
            state = bool(toggle(label))
        except RichEditRtfError as error:
            self._set_status(f"Could not apply {label.lower()}: {error}")
            return True
        self._mark_rich_formatting_dirty()
        said = f"{label} {'on' if state else 'off'}"
        self._set_status_quiet(said)
        self._announce(said)
        return True

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
        """Pin the tab's markup kind via the shared Document Language machinery.

        Stores a real :class:`LanguageProfile` (not a bare stub) because the same
        ``tab._language_profile`` slot is read by the language-profile consumers
        (status bar Language cell, token classification, auto-indent), which
        expect ``name``/``keywords``/``indent_unit``/``uses_tabs`` — a stub with
        only ``markup_kind`` would crash them now that ``_current_tab`` resolves.
        """
        from quill.core.language_profile import LanguageProfile

        label = {"markdown": "Markdown", "html": "HTML"}.get(kind, "Plain text")
        tab._language_profile = LanguageProfile(name=label, extensions=(), markup_kind=kind)
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
    # Starting a document in a kind (bad.md P1.13, 3.7)
    # ------------------------------------------------------------------ #

    def new_document_in_format(self, target: str) -> None:
        """Open a new document already in *target*, a DOCUMENT_FORMATS key.

        QUILL had no seam for this: ``new_file`` made a document in whatever
        ``default_new_document_format`` said, and the only way to another kind
        was the switcher afterwards. ``--rich`` / ``--plain`` (bad.md P2.16)
        wants the same seam, so it is one method rather than two handlers.

        A document that already arrives in the wanted kind is left alone: the
        switcher would run the bridge and say "Already editing as Markdown",
        which is noise on a command meant not to make you think about it.
        """
        if target not in DOCUMENT_FORMATS:
            return
        self.new_file()
        if self.current_document_format() != target:
            self.set_document_format(target, announce=False)
        self._set_status(f"New {DOCUMENT_FORMATS[target][0]} document")

    def new_rich_document(self) -> None:
        """QuillLite's Ctrl+Shift+N: start a rich text document."""
        self.new_document_in_format("rtf")

    def new_plain_text_document(self) -> None:
        """QuillLite's Ctrl+Alt+N: start a plain text document."""
        self.new_document_in_format("plain")

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

    def set_document_format(self, target: str, *, announce: bool = True) -> None:
        """Move the current document to ``target`` format mid-session.

        *announce* is False only when the caller is about to say something
        better: ``new_document_in_format`` opens a document that has never been
        in another format, and "Now editing as Rich Text" describes a change
        that did not happen to the person who just pressed New (bad.md P1.13).

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
                if announce:
                    self._set_status(f"Now saving as {label}")
                self._refresh_statusbar()
                return
            markup = self.editor.GetValue()
            # An HTML document becomes Markdown first, which QuillLite has done
            # since it learned the switch and QUILL never had: markdown_to_rtf
            # reads ``<h1>`` as four characters, so switching an HTML page to
            # Rich Text used to put the tags on the page as literal text beside
            # the words they were supposed to be formatting. Guarded on the
            # content rather than the label, because the label travels without
            # the text -- see quill.core.html_to_markdown.contains_html_markup.
            if self._current_markup_context() == "html" and contains_html_markup(markup):
                converted = html_to_markdown(markup)
                if converted.strip():
                    markup = converted
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
            if announce:
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
                # Leaving rich always lands in Markdown -- that is what
                # rtf_to_markdown produces -- so the *real* target is reached by
                # converting again below, from markdown. Saying so here is what
                # stops "markdown, relabelled" from passing as HTML or plain.
                converted = self._convert_buffer_format("markdown", target, markup)
                if converted is None:
                    self._set_status("Format switch cancelled")
                    return
                self.editor.ChangeValue(converted)
                tab.editor_mode = "markup"
                tab.docx_rich = False
                self.document.set_text(converted)
            else:
                # Markup to markup. This used to keep the text and let the pin
                # decide the tags, which is how Markdown became "HTML" without
                # a single tag being written, and how a plain-text document kept
                # its hashes. The words are kept; the markup is rewritten.
                source_kind = self._current_markup_context()
                converted = self._convert_buffer_format(source_kind, target, self.editor.GetValue())
                if converted is None:
                    self._set_status("Format switch cancelled")
                    return
                if converted != self.editor.GetValue():
                    self.editor.ChangeValue(converted)
                    self.document.set_text(converted)
            self._pin_markup_kind_for_tab(tab, target)
            self._retarget_format_suffix(tab, suffix)
            self._set_status_quiet(f"Now editing as {label}")
            if announce and target == "markdown":
                self._announce("Now editing as Markdown. Formatting appears as tags.")
            elif announce and target == "html":
                self._announce("Now editing as HTML. Formatting appears as tags.")
            elif announce:
                self._announce("Now editing as plain text.")
        self._refresh_statusbar()
        self._request_menu_refresh()

    def _convert_buffer_format(self, source: str, target: str, text: str) -> str | None:
        """Rewrite *text* from *source* markup to *target*, asking when it matters.

        ``None`` means the person cancelled and nothing should change -- which
        is why the caller must check it rather than treating a falsy answer as
        empty text.

        The only question with two honest answers is plain text: ``# Heading``
        can stay as the ordinary characters a .txt file is entitled to hold, or
        come off so the file is strictly plain. Both are things people actually
        want, so this asks instead of choosing, and only when there is Markdown
        in the buffer to ask about.
        """
        plan = plan_transition(text, source, target)
        plain_style = PlainStyle.STRIP
        if plan.asks_plain_style:
            answer = self._ask_plain_text_style(plan)
            if answer is None:
                return None
            plain_style = answer
        return convert_text(
            text,
            source,
            target,
            plain_style=plain_style,
            title=self.document.name or "Document",
            charset=getattr(self.document, "encoding", None) or "utf-8",
        )

    def _ask_plain_text_style(self, plan: TransitionPlan) -> PlainStyle | None:
        """Keep the Markdown characters, or take them off? ``None`` to cancel.

        Three buttons rather than a yes/no, because "no" is not an answer to
        this question: both outcomes are a conversion, and only Cancel means
        "leave my document alone".
        """
        wx = self._wx
        dialog = wx.MessageDialog(
            self.frame,
            f"{plan.summary}\n\n"
            "Keep the Markdown characters (# and **) as ordinary text, or "
            "remove them so the document is strictly plain?",
            "Converting to plain text",
            # NO_DEFAULT, so Enter answers "keep them". Of the two conversions
            # only one can lose something -- removing the markers -- and a
            # reflexive Enter must not be the thing that loses it. Keeping them
            # is reversible by pressing the same command again and answering the
            # other way; removing them is not.
            wx.YES_NO | wx.CANCEL | wx.ICON_QUESTION | wx.NO_DEFAULT,
        )
        if hasattr(dialog, "SetYesNoCancelLabels"):
            dialog.SetYesNoCancelLabels("Remove the markers", "Keep them as text", "Cancel")
        try:
            result = self._show_modal_dialog(dialog, "Converting to plain text")
        finally:
            dialog.Destroy()
        if result == wx.ID_YES:
            return PlainStyle.STRIP
        if result == wx.ID_NO:
            return PlainStyle.KEEP
        return None

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
