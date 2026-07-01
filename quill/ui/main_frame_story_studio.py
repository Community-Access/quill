"""Story Studio opener (MainFrame mixin).

Wires the ``story.open_studio`` command: choose a project folder, load the
project (``quill.core.story``), and show its binder in
:class:`quill.ui.story_studio_dialog.StoryStudioDialog`. Activating a binder
node opens that file at the heading's offset and closes the binder.

The mixin relies on MainFrame for ``_wx``, ``frame``, ``commands``,
``_binding_for``, ``_show_modal_dialog``, ``open_file``, and ``_set_status``.
The one piece of pure logic (``offset_to_line``) is a module function so it can
be unit-tested without wx.
"""

from __future__ import annotations

from pathlib import Path


def offset_to_line(text: str, offset: int) -> int:
    """1-based line number for a character ``offset`` (clamped to ``text``)."""
    if offset <= 0:
        return 1
    return text[: min(offset, len(text))].count("\n") + 1


class StoryStudioMixin:
    """The ``story.open_studio`` command handler.

    MainFrame provides the attributes/methods used here: ``_wx``, ``frame``,
    ``commands``, ``_binding_for``, ``_show_modal_dialog``, ``open_file``, and
    ``_set_status``.
    """

    def open_story_studio(self) -> None:
        """Choose a project folder and open its binder."""
        wx = self._wx
        picker = wx.DirDialog(
            self.frame,
            "Choose a story project folder",
            style=wx.DD_DEFAULT_STYLE | wx.DD_DIR_MUST_EXIST,
        )
        try:
            if self._show_modal_dialog(picker, "Choose Story Project") != wx.ID_OK:
                self._set_status("Story Studio cancelled")
                return
            folder = Path(picker.GetPath())
        finally:
            picker.Destroy()

        from quill.core.story import load_project
        from quill.ui.dialog_contract import apply_modal_ids
        from quill.ui.story_studio_dialog import StoryStudioDialog

        project = load_project(folder)

        def read_text(rel_path: str) -> str:
            try:
                return (folder / rel_path).read_text(encoding="utf-8")
            except OSError:
                return ""

        studio = StoryStudioDialog(
            wx,
            project=project,
            read_text=read_text,
            on_open=lambda rel, offset: self._open_story_node(folder, rel, offset),
            on_edit_details=lambda rel, kind: self._edit_story_element_details(folder, rel, kind),
        )
        dialog = wx.Dialog(
            self.frame,
            title=f"Story Studio - {project.title}",
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        outer = studio.populate(dialog)
        buttons = dialog.CreateStdDialogButtonSizer(wx.CLOSE)
        outer.Add(buttons, 0, wx.EXPAND | wx.ALL, 10)
        apply_modal_ids(
            dialog,
            affirmative_id=wx.ID_CLOSE,
            affirmative_label="&Close",
            escape_id=wx.ID_CLOSE,
        )
        try:
            self._show_modal_dialog(dialog, "Story Studio")
        finally:
            dialog.Destroy()
        self._set_status(f"Story Studio: {project.title}")

    def _open_story_node(self, folder: Path, rel_path: str, offset: int | None) -> None:
        """Open a binder node's file, positioning at the heading offset."""
        path = folder / rel_path
        line: int | None = None
        if offset is not None:
            try:
                text = path.read_text(encoding="utf-8")
            except OSError:
                text = ""
            line = offset_to_line(text, offset)
        self.open_file(path, line=line)

    def _edit_story_element_details(self, folder: Path, rel_path: str, kind_value: str) -> None:
        """Open the details form for an element file and save on OK."""
        from quill.core.story import split_front_matter
        from quill.core.story.model import ElementKind
        from quill.ui.dialog_contract import apply_modal_ids
        from quill.ui.story_element_form_dialog import StoryElementFormDialog

        wx = self._wx
        path = folder / rel_path
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            text = ""
        fields, body = split_front_matter(text)
        form = StoryElementFormDialog(
            wx,
            kind=ElementKind.coerce(kind_value),
            fields=fields,
            on_save=lambda new_fields: self._write_story_element(path, new_fields, body),
        )
        dialog = wx.Dialog(
            self.frame,
            title=f"Details - {path.stem}",
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        outer = form.populate(dialog)
        buttons = dialog.CreateStdDialogButtonSizer(wx.OK | wx.CANCEL)
        outer.Add(buttons, 0, wx.EXPAND | wx.ALL, 10)
        apply_modal_ids(
            dialog,
            affirmative_id=wx.ID_OK,
            affirmative_label="&Save",
            cancel_id=wx.ID_CANCEL,
            cancel_label="Cancel",
        )
        try:
            if self._show_modal_dialog(dialog, "Element Details") == wx.ID_OK:
                form.commit()
                self._set_status(f"Saved details for {path.name}")
            else:
                self._set_status("Details unchanged")
        finally:
            dialog.Destroy()

    def _write_story_element(self, path: Path, fields: dict, body: str) -> None:
        from quill.core.story import join_front_matter

        try:
            path.write_text(join_front_matter(fields, body), encoding="utf-8")
        except OSError as error:
            self._set_status(f"Could not save details: {error}")

    def _register_story_studio_commands(self) -> None:
        self.commands.try_register(
            "story.open_studio",
            "Story Studio (organize a project)",
            self.open_story_studio,
            self._binding_for("story.open_studio"),
        )
