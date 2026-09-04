"""The Tag Editor — every tag an audio file can carry, on five keyboard pages.

The Chapter Workbench's five quick fields cover the audiobook case: title,
author, narrator, genre, year. This is the rest — twenty-six fields and the
cover art — built by iterating
:data:`quill.core.speech.audio_tags_core.TAG_FIELDS`, the table vendored
byte-identical into podHarvest. Adding a tag is a table edit in the core
module and needs no change here, and podHarvest's editor grows the same field
on the same day without anybody copying a label across.

It is a **pure editor**: an :class:`AudioTags` goes in, an edited copy comes
back out of :meth:`TagEditorDialog.result`. It never writes a file. The caller
saves, on the background runner, so a slow write never happens inside a modal.

Three things about the layout are load-bearing rather than incidental:

* **Each page is its own class.** GATE-14 scopes a ``wx.Dialog`` subclass as
  one window but any other class per method, so one panel class per page gives
  each page its own mnemonic namespace -- which is also true of Windows, where
  only the visible notebook page's access keys can fire. Twenty-six fields
  could not hold unique mnemonics in one namespace; in four they fit with room
  left over.
* **The label is created before the control it labels.** Screen readers pair
  them by creation order (which in wxPython is the Windows child z-order), so
  a row helper that took an already-built control would silently mis-name
  every field. That is the shape ``check_dialog_zorder.py`` looks for, and the
  reason :meth:`TagPagePanel._add_field` builds both itself.
* **No ``wx.StaticBox``.** ``IsDialogMessage`` scopes its mnemonic search to
  the enclosing StaticBox, so grouping these fields in boxes would make every
  mnemonic unreachable from a field in a different box. Plain grid rows keep
  the keys working.
"""

from __future__ import annotations

import io
from collections.abc import Callable
from pathlib import Path

import wx

from quill.core.i18n import _
from quill.core.speech.audio_tags import (
    GROUPS,
    AudioTags,
    CoverArt,
    TagField,
    TagReadError,
    cover_extension,
    describe_cover,
    fields_in,
    load_cover,
)
from quill.ui.audio_studio.pages_base import set_accessible_name
from quill.ui.dialog_contract import apply_modal_ids, show_message_box

#: The longest edge of the cover thumbnail, in pixels.
_THUMBNAIL_PX = 160


def _plain(label: str) -> str:
    """A field label as a screen reader should hear it: no ampersand, no colon."""
    return label.replace("&", "").rstrip(": ").strip()


class TagPagePanel(wx.Panel):
    """One notebook page: every field of one group, as label-then-control rows.

    Its own class rather than a method on the dialog, for two reasons. The
    access-key gate scopes a non-dialog class per method, so each page's
    mnemonics live in their own namespace. And a page that owns its controls
    can be seeded, collected and tested without the dialog around it.
    """

    def __init__(self, parent: wx.Window, group: str) -> None:
        super().__init__(parent, name=f"audio_studio.tag_editor.{group}")
        self.controls: dict[str, wx.Window] = {}
        self.totals: dict[str, wx.TextCtrl] = {}
        self._fields = fields_in(group)

        grid = wx.FlexGridSizer(cols=2, vgap=6, hgap=8)
        grid.AddGrowableCol(1, 1)
        for tag_field in self._fields:
            self._add_field(grid, tag_field)
        root = wx.BoxSizer(wx.VERTICAL)
        root.Add(grid, 1, wx.EXPAND | wx.ALL, 10)
        self.SetSizer(root)

    def _add_field(self, grid: wx.FlexGridSizer, tag_field: TagField) -> None:
        """Add one row: the label first, then the control. Order is the point."""
        if tag_field.kind == "bool":
            # A checkbox carries its own label, so there is no StaticText to
            # order against; the empty cell keeps the two-column grid aligned.
            grid.Add(wx.StaticText(self, label=""), 0)
            check = wx.CheckBox(self, label=tag_field.label)
            check.SetHelpText(tag_field.help)
            set_accessible_name(check, _plain(tag_field.label))
            grid.Add(check, 0, wx.EXPAND)
            self.controls[tag_field.key] = check
            return

        grid.Add(wx.StaticText(self, label=tag_field.label), 0, wx.ALIGN_CENTER_VERTICAL)
        if tag_field.kind == "pair":
            row = wx.BoxSizer(wx.HORIZONTAL)
            number = wx.TextCtrl(self, size=wx.Size(70, -1))
            number.SetHelpText(tag_field.help)
            set_accessible_name(number, f"{_plain(tag_field.label)}, number")
            row.Add(number, 0, wx.RIGHT, 6)
            row.Add(
                wx.StaticText(self, label=_("of")),
                0,
                wx.ALIGN_CENTER_VERTICAL | wx.RIGHT,
                6,
            )
            total = wx.TextCtrl(self, size=wx.Size(70, -1))
            total.SetHelpText(tag_field.help)
            set_accessible_name(total, f"{_plain(tag_field.label)}, total")
            row.Add(total, 0)
            grid.Add(row, 0, wx.EXPAND)
            self.controls[tag_field.key] = number
            self.totals[tag_field.key] = total
            return

        style = wx.TE_MULTILINE if tag_field.kind == "multiline" else 0
        size = wx.Size(-1, 90) if tag_field.kind == "multiline" else wx.DefaultSize
        ctrl = wx.TextCtrl(self, style=style, size=size)
        ctrl.SetHelpText(tag_field.help)
        set_accessible_name(ctrl, _plain(tag_field.label))
        grid.Add(ctrl, 0, wx.EXPAND)
        self.controls[tag_field.key] = ctrl

    def seed(self, tags: AudioTags) -> None:
        """Fill every control on this page from *tags*."""
        for tag_field in self._fields:
            value = tags.get(tag_field.key)
            ctrl = self.controls[tag_field.key]
            if tag_field.kind == "bool":
                ctrl.SetValue(bool(value))
            elif tag_field.kind == "pair":
                number, _sep, total = value.partition("/")
                ctrl.SetValue(number)
                self.totals[tag_field.key].SetValue(total)
            else:
                ctrl.SetValue(value)

    def collect(self, tags: AudioTags) -> None:
        """Write every control on this page back into *tags*."""
        for tag_field in self._fields:
            ctrl = self.controls[tag_field.key]
            if tag_field.kind == "bool":
                tags.set(tag_field.key, "1" if ctrl.GetValue() else "")
            elif tag_field.kind == "pair":
                number = ctrl.GetValue().strip()
                total = self.totals[tag_field.key].GetValue().strip()
                tags.set(tag_field.key, f"{number}/{total}" if total else number)
            else:
                tags.set(tag_field.key, ctrl.GetValue())


class CoverPagePanel(wx.Panel):
    """The embedded cover image: what it is, and how to change it.

    The description is a text readout first and a thumbnail second, in that
    order, because a picture tells a sighted person everything about the art
    and a screen-reader user nothing at all. Its own class, like the tag
    pages, so its three buttons hold their own mnemonic namespace.
    """

    def __init__(
        self,
        parent: wx.Window,
        cover: CoverArt | None,
        *,
        announce: Callable[[str], None] | None = None,
    ) -> None:
        super().__init__(parent, name="audio_studio.tag_editor.cover")
        self.cover = cover
        self._announce_fn = announce

        root = wx.BoxSizer(wx.VERTICAL)
        root.Add(wx.StaticText(self, label=_("Current cover art:")), 0, wx.LEFT | wx.TOP, 10)
        self.summary = wx.StaticText(
            self,
            label=describe_cover(cover),
            name="audio_studio.tag_editor.cover_summary",
        )
        root.Add(self.summary, 0, wx.EXPAND | wx.ALL, 10)

        self.thumbnail = wx.StaticBitmap(self, name="audio_studio.tag_editor.cover_image")
        root.Add(self.thumbnail, 0, wx.LEFT | wx.BOTTOM, 10)

        row = wx.BoxSizer(wx.HORIZONTAL)
        load_btn = wx.Button(self, label=_("&Load image..."))
        load_btn.SetHelpText(
            "Chooses a JPEG or PNG image to embed as this file's cover art, "
            "replacing whatever is there now. The file is checked by its real "
            "contents rather than its name, and images over 8 MB are refused."
        )
        load_btn.Bind(wx.EVT_BUTTON, lambda _e: self._on_load())
        row.Add(load_btn, 0, wx.RIGHT, 6)

        save_btn = wx.Button(self, label=_("&Save image as..."))
        save_btn.SetHelpText(
            "Writes the embedded cover art out to a picture file of its own, "
            "leaving the audio file untouched."
        )
        save_btn.Bind(wx.EVT_BUTTON, lambda _e: self._on_save())
        row.Add(save_btn, 0, wx.RIGHT, 6)

        remove_btn = wx.Button(self, label=_("&Remove image"))
        remove_btn.SetHelpText(
            "Takes the cover art off this file. Like every other edit here, it "
            "happens when you save, not before."
        )
        remove_btn.Bind(wx.EVT_BUTTON, lambda _e: self.remove_cover())
        row.Add(remove_btn, 0)
        root.Add(row, 0, wx.LEFT | wx.BOTTOM, 10)

        self.SetSizer(root)
        self.refresh()

    def _announce(self, text: str) -> None:
        if self._announce_fn is not None:
            self._announce_fn(text)

    def refresh(self) -> None:
        """Re-read the summary label and the thumbnail from ``self.cover``."""
        self.summary.SetLabel(describe_cover(self.cover))
        bitmap = self._thumbnail_of(self.cover)
        if bitmap is None:
            # Hiding beats handing SetBitmap a null one, which asserts, and an
            # empty placeholder is noise on a page that already says in words
            # what the art is.
            self.thumbnail.Hide()
        else:
            self.thumbnail.SetBitmap(bitmap)
            self.thumbnail.Show()
        self.Layout()

    @staticmethod
    def _thumbnail_of(cover: CoverArt | None) -> wx.Bitmap | None:
        """A scaled bitmap of *cover*, or None when it cannot be decoded.

        The decode runs under ``wx.LogNull``. wx reports an image it cannot
        read by *logging an error*, which surfaces as a modal "Unknown image
        data format" box -- not as an exception, so a ``try``/``except`` does
        not stop it. A cover written by another tagger in a format this build
        has no handler for is a thing to shrug at, not a dialog to interrupt
        somebody with.
        """
        if cover is None:
            return None
        no_log = wx.LogNull()
        try:
            image = wx.Image(io.BytesIO(cover.data))
            if not image.IsOk():
                return None
            longest = max(image.GetWidth(), image.GetHeight(), 1)
            scale = min(1.0, _THUMBNAIL_PX / longest)
            return image.Scale(
                max(1, int(image.GetWidth() * scale)),
                max(1, int(image.GetHeight() * scale)),
                wx.IMAGE_QUALITY_HIGH,
            ).ConvertToBitmap()
        except Exception:  # noqa: BLE001 - an undecodable image is not fatal
            return None
        finally:
            del no_log

    def set_cover(self, cover: CoverArt) -> None:
        """Replace the art and say so -- a change on a control that has no focus."""
        self.cover = cover
        self.refresh()
        self._announce(str(_("Cover art loaded. {summary}")).format(summary=describe_cover(cover)))

    def remove_cover(self) -> None:
        """Drop the art and say so."""
        if self.cover is None:
            self._announce(str(_("There is no cover art to remove.")))
            return
        self.cover = None
        self.refresh()
        self._announce(str(_("Cover art removed.")))

    def _on_load(self) -> None:
        with wx.FileDialog(
            self,
            str(_("Choose a cover image")),
            wildcard=str(_("Images (*.jpg;*.jpeg;*.png)|*.jpg;*.jpeg;*.png")),
            style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
        ) as dlg:
            if dlg.ShowModal() != wx.ID_OK:  # GATE-42-OK: native file picker
                return
            chosen = Path(dlg.GetPath())
        try:
            self.set_cover(load_cover(chosen))
        except TagReadError as exc:
            show_message_box(str(exc), str(_("Tag Editor")), wx.OK | wx.ICON_ERROR, self)

    def _on_save(self) -> None:
        if self.cover is None:
            self._announce(str(_("There is no cover art to save.")))
            return
        suffix = cover_extension(self.cover)
        with wx.FileDialog(
            self,
            str(_("Save the cover image as")),
            defaultFile=f"cover{suffix}",
            wildcard=f"*{suffix}|*{suffix}",
            style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT,
        ) as dlg:
            if dlg.ShowModal() != wx.ID_OK:  # GATE-42-OK: native file picker
                return
            out = Path(dlg.GetPath())
        try:
            out.write_bytes(self.cover.data)
        except OSError as exc:
            show_message_box(
                str(_("Could not save the image: {error}")).format(error=exc),
                str(_("Tag Editor")),
                wx.OK | wx.ICON_ERROR,
                self,
            )
            return
        self._announce(str(_("Saved {name}")).format(name=out.name))


class TagEditorDialog(wx.Dialog):
    """Edit every tag of one audio file. Returns the edit; never writes it."""

    def __init__(
        self,
        parent: wx.Window,
        tags: AudioTags,
        *,
        filename: str,
        announce: Callable[[str], None] | None = None,
    ) -> None:
        super().__init__(
            parent,
            title=str(_("Tag Editor")),
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
            name="audio_studio.tag_editor",
        )
        self._tags = tags.copy()
        self._announce_fn = announce
        self.pages: dict[str, wx.Panel] = {}
        self.controls: dict[str, wx.Window] = {}
        self.totals: dict[str, wx.TextCtrl] = {}

        root = wx.BoxSizer(wx.VERTICAL)
        heading = wx.StaticText(
            self,
            label=_("Tags for {name}").format(name=filename),
            name="audio_studio.tag_editor_heading",
        )
        heading.SetFont(heading.GetFont().Scaled(1.2).Bold())
        root.Add(heading, 0, wx.ALL, 10)

        notebook = wx.Notebook(self, name="audio_studio.tag_editor_pages")
        notebook.SetHelpText(
            "The tags are grouped over five pages. Control+Tab moves to the "
            "next page and Control+Shift+Tab to the previous one; Tab moves "
            "between the fields of the page you are on. Nothing is written to "
            "the file until you press OK and then save."
        )
        set_accessible_name(notebook, str(_("Tag pages")))
        for group, label in GROUPS:
            page = TagPagePanel(notebook, group)
            page.seed(self._tags)
            notebook.AddPage(page, str(_(label)))
            self.pages[group] = page
            self.controls.update(page.controls)
            self.totals.update(page.totals)
        self.cover_page = CoverPagePanel(notebook, self._tags.cover, announce=announce)
        notebook.AddPage(self.cover_page, str(_("Cover art")))
        self.pages["cover"] = self.cover_page
        root.Add(notebook, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)

        buttons = wx.BoxSizer(wx.HORIZONTAL)
        ok_btn = wx.Button(self, wx.ID_OK, label=_("OK"))
        ok_btn.SetHelpText(
            "Keeps these tag edits and closes this window. They are written to "
            "the file when you save in the window behind."
        )
        cancel_btn = wx.Button(self, wx.ID_CANCEL, label=_("Cancel"))
        cancel_btn.SetHelpText("Discards every tag edit made in this window.")
        buttons.AddStretchSpacer()
        buttons.Add(ok_btn, 0, wx.RIGHT, 6)
        buttons.Add(cancel_btn, 0)
        root.Add(buttons, 0, wx.EXPAND | wx.ALL, 10)

        apply_modal_ids(
            self,
            affirmative_id=wx.ID_OK,
            affirmative_label=str(_("OK")),
            cancel_id=wx.ID_CANCEL,
            cancel_label=str(_("Cancel")),
        )
        self.SetSizer(root)
        self.SetMinSize(wx.Size(640, 560))
        self.Fit()
        self.CentreOnParent()

    def result(self) -> AudioTags:
        """The edited tags. The ``AudioTags`` passed in is never mutated."""
        edited = self._tags.copy()
        for group, _label in GROUPS:
            page = self.pages[group]
            assert isinstance(page, TagPagePanel)
            page.collect(edited)
        edited.cover = self.cover_page.cover
        return edited


def open_tags_in_editor(frame: object, path: object) -> None:
    """Open *path* in the Tag Editor alone, with no Workbench around it.

    The standalone route, for when the job is "fix the tags on this file" and
    not "reshape this book". A surface reachable only from inside another
    dialog is a surface nobody finds -- GATE-REACH exists because Cast once
    shipped a first-run dialog that way for two releases, with passing tests
    and a user guide describing it.
    """
    from quill.core.speech.audio_tags import AudioTags as _AudioTags
    from quill.core.speech.audio_tags import read_tags, write_tags

    target = Path(str(path))
    announce = getattr(frame, "_announce", None)
    try:
        tags = read_tags(target)
    except Exception as exc:  # noqa: BLE001 - an untagged file is still editable
        if announce is not None:
            announce(str(_("Could not read the existing tags: {error}")).format(error=exc))
        tags = _AudioTags()
    dlg = TagEditorDialog(
        getattr(frame, "frame", frame),
        tags,
        filename=target.name,
        announce=announce,
    )
    try:
        code = frame._show_modal_dialog(dlg, str(_("Tag Editor")))
        edited = dlg.result() if code == wx.ID_OK else None
    finally:
        dlg.Destroy()
    if edited is None:
        return
    try:
        write_tags(target, edited)
    except Exception as exc:  # noqa: BLE001 - surfaced, never raised through wx
        show_message_box(str(exc), str(_("Tag Editor")), wx.OK | wx.ICON_ERROR, None)
        return
    if announce is not None:
        announce(str(_("Saved tags to {name}")).format(name=target.name))
