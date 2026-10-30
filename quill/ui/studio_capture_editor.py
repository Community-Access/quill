"""Native screenshot edit/object list; all geometry also has named portions."""

from __future__ import annotations

import json
from pathlib import Path

import wx
from wx.lib.scrolledpanel import ScrolledPanel

from quill.core.screenshot_project import ScreenshotProject, compare_screenshots
from quill.core.studio_capture import verify_capture
from quill.stability.task_manager import UiLifetimeToken
from quill.ui.dialog_contract import apply_modal_ids, set_accessible_name
from quill.ui.dpi import dip_size

PORTIONS = {
    "Whole image": (0, 0, 100, 100),
    "Top half": (0, 0, 100, 50),
    "Bottom half": (0, 50, 100, 50),
    "Left half": (0, 0, 50, 100),
    "Right half": (50, 0, 50, 100),
    "Middle section": (25, 25, 50, 50),
    "Top left quarter": (0, 0, 50, 50),
    "Top right quarter": (50, 0, 50, 50),
    "Bottom left quarter": (0, 50, 50, 50),
    "Bottom right quarter": (50, 50, 50, 50),
}
ACTIONS = ("crop", "redact", "rectangle", "arrow", "highlight", "spotlight", "text")
ACTION_LABELS = (
    "Keep only this area",
    "Hide private information",
    "Add a numbered box",
    "Point with an arrow",
    "Highlight an area",
    "Spotlight an area",
    "Add a note",
)


class ScreenshotEditorDialog(wx.Dialog):
    def __init__(self, host, evidence):
        super().__init__(
            host.frame,
            title="Screenshot editing and evidence",
            size=dip_size(host.frame, 850, 780),
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        self.host = host
        self.project = ScreenshotProject(evidence)
        self.lifetime = UiLifetimeToken()
        self.task = None
        self.busy = False
        self.last_export = None
        self.anchors = dict(PORTIONS)
        panel = ScrolledPanel(self)
        body = wx.BoxSizer(wx.VERTICAL)
        advanced_panel = wx.Panel(panel)
        advanced_body = wx.BoxSizer(wx.VERTICAL)

        def field(label, make, help_text, parent):
            # The label first, then the control (make): a screen reader pairs
            # them by creation order (check_dialog_zorder.py, A11Y-Z-ORDER).
            container = advanced_body if parent is advanced_panel else body
            container.Add(wx.StaticText(parent, label=label), 0, wx.TOP, 6)
            control = make()
            set_accessible_name(control, label.replace("&", ""))
            control.SetHelpText(help_text)
            container.Add(control, 0, wx.EXPAND | wx.BOTTOM, 4)
            return control

        self.plan = field(
            "Edit &plan and results",
            lambda: wx.TextCtrl(
                panel,
                value=self.project.describe(simple=True),
                style=wx.TE_MULTILINE | wx.TE_READONLY,
                size=dip_size(panel, -1, 130),
            ),
            "Read the original identity, edits and measured results. "
            "This is the text alternative to the visual preview.",
            panel,
        )
        self.objects = field(
            "&Objects and edit order",
            lambda: wx.ListBox(advanced_panel),
            "Each operation is listed in render order. Select one to remove or move it. "
            "Numbered annotations are identified by text as well as colour.",
            advanced_panel,
        )
        self.action = field(
            "What would you like to &do?",
            lambda: wx.Choice(panel, choices=list(ACTION_LABELS)),
            "Crop, redact with solid black, or add a numbered annotation. "
            "The original is never overwritten. A redaction export does not include the original.",
            panel,
        )
        self.action.SetSelection(0)
        self.region = field(
            "&Area to change",
            lambda: wx.Choice(panel, choices=list(self.anchors)),
            "Start with a named area. Find text to select adds recognized text locations. "
            "Choose an anchor before adding an operation. OCR can be wrong; review before sharing.",
            panel,
        )
        self.region.SetSelection(0)
        self.caption = field(
            "&Label or callout text",
            lambda: wx.TextCtrl(panel),
            "Optional text for an annotation. A visible number is added automatically.",
            panel,
        )
        self.position = field(
            "E&xact percentages: left, top, width, height",
            lambda: wx.TextCtrl(advanced_panel),
            "Optional four comma-separated percentages, for example 0, 0, 100, 50. "
            "Leave blank to use the named region. No pixel knowledge is needed.",
            advanced_panel,
        )
        self.size = field(
            "Resize as percentage of current &size",
            lambda: wx.SpinCtrl(advanced_panel, min=10, max=400, initial=100),
            "Resize proportionally from 10 through 400 percent. "
            "Dimensions are verified after export. Enlarging does not restore missing detail.",
            advanced_panel,
        )
        self.zoom = field(
            "Visual preview &zoom",
            lambda: wx.Choice(advanced_panel, choices=["25%", "50%", "100%", "200%", "400%"]),
            "Optional visual magnification. The text plan remains available without sight.",
            advanced_panel,
        )
        self.zoom.SetSelection(2)
        self.goal = field(
            "Intended &use and description",
            lambda: wx.TextCtrl(panel),
            "Describe why you need this screenshot. Included in your evidence bundle.",
            panel,
        )
        self.steps = field(
            "Steps to &reproduce",
            lambda: wx.TextCtrl(
                advanced_panel, style=wx.TE_MULTILINE, size=dip_size(advanced_panel, -1, 60)
            ),
            "Type the actions that produced the screen. Review this text for secrets.",
            advanced_panel,
        )
        self.privacy = wx.CheckBox(
            advanced_panel, label="I reviewed the rendered export for private information"
        )
        self.privacy.SetHelpText(
            "Human review acknowledgment, not automatic privacy certification. "
            "Any later edit resets it."
        )
        advanced_body.Add(self.privacy, 0, wx.TOP, 8)
        self.content_review = wx.CheckBox(
            advanced_panel, label="I reviewed the rendered export for intended content"
        )
        self.content_review.SetHelpText("Acknowledge content review. Any later edit resets it.")
        advanced_body.Add(self.content_review, 0, wx.TOP, 8)
        self.strict = wx.CheckBox(
            advanced_panel, label="Strict evidence export: require both reviews"
        )
        self.strict.SetHelpText(
            "Block bundle export until both reviews are acknowledged or a waiver is recorded."
        )
        advanced_body.Add(self.strict, 0, wx.TOP, 8)
        self.waiver = field(
            "Review &waiver and reason",
            lambda: wx.TextCtrl(advanced_panel),
            "Optional conscious exception to strict review. The reason is included in the bundle.",
            advanced_panel,
        )
        buttons = wx.WrapSizer(wx.HORIZONTAL)
        simple_buttons = wx.WrapSizer(wx.HORIZONTAL)
        actions = (
            ("Add edit", self._add),
            ("Undo", lambda e: self._history(False)),
            ("Redo", lambda e: self._history(True)),
            ("Remove selected", self._remove),
            ("Move left 1%", lambda e: self._move(-1, 0)),
            ("Move right 1%", lambda e: self._move(1, 0)),
            ("Move up 1%", lambda e: self._move(0, -1)),
            ("Move down 1%", lambda e: self._move(0, 1)),
            ("Grow 1%", lambda e: self._move(0, 0, 1)),
            ("Shrink 1%", lambda e: self._move(0, 0, -1)),
            ("Resize proportionally", self._resize),
            ("Find text to select", self._ocr),
            ("Visual preview", self._preview),
            ("Add a spoken note", self._dictate),
            ("Compare saved image", self._compare),
            ("Save layered project", lambda e: self._project_file(False)),
            ("Open layered project", lambda e: self._project_file(True)),
            ("Save image", lambda e: self._export("PNG")),
            ("Export JPEG", lambda e: self._export("JPEG")),
            ("Export WEBP", lambda e: self._export("WEBP")),
            ("Export evidence bundle", self._bundle),
            ("Review edited screenshot", self._inspect),
        )
        for label, handler in actions:
            simple = label in {
                "Add edit",
                "Undo",
                "Redo",
                "Save image",
                "Review edited screenshot",
                "Visual preview",
                "Find text to select",
                "Add a spoken note",
            }
            button = wx.Button(panel if simple else advanced_panel, label=label)
            button.SetHelpText(
                label + ". Applies to this screenshot project; reports are selectable above."
            )
            button.Bind(wx.EVT_BUTTON, handler)
            (simple_buttons if simple else buttons).Add(button, 0, wx.ALL, 3)
        body.Add(simple_buttons, 0, wx.EXPAND | wx.TOP, 8)
        advanced_body.Add(buttons, 0, wx.EXPAND | wx.TOP, 8)
        advanced_panel.SetSizer(advanced_body)
        advanced_panel.Hide()
        advanced = wx.CheckBox(panel, label="More options (Ad&vanced)")
        advanced.SetHelpText(
            "Show exact positions, edit layers, resizing, comparison, "
            "project files and specialist evidence exports. Optional."
        )

        def toggle(event):
            advanced_panel.Show(advanced.GetValue())
            panel.Layout()
            panel.FitInside()
            self._say(
                "Advanced options shown." if advanced.GetValue() else "Advanced options hidden."
            )

        advanced.Bind(wx.EVT_CHECKBOX, toggle)
        body.Add(advanced, 0, wx.TOP | wx.BOTTOM, 8)
        body.Add(advanced_panel, 0, wx.EXPAND)
        panel.SetSizer(body)
        panel.SetupScrolling(scroll_x=False)
        outer = wx.BoxSizer(wx.VERTICAL)
        outer.Add(panel, 1, wx.EXPAND | wx.ALL, 8)
        self.status = wx.StaticText(
            self, label="Ready. Original preserved; review edits before sharing."
        )
        outer.Add(self.status, 0, wx.ALL, 8)
        outer.Add(self.CreateButtonSizer(wx.CANCEL), 0, wx.EXPAND | wx.ALL, 8)
        apply_modal_ids(self, cancel_id=wx.ID_CANCEL, cancel_label="Close")
        self.SetSizer(outer)
        area = wx.GetClientDisplayRect()
        self.SetSize((min(850, area.width), min(780, area.height)))
        self.plan.SetFocus()
        # a11y: needs manual verification — all screen readers, focus order, scaling and braille.

    def _say(self, message):
        self.status.SetLabel(message)
        self.host._announce(message)

    def _run(self, name, work, ready=None):
        if self.busy:
            self._say("An operation is running. Wait before starting another; focus stays here.")
            return
        self.busy = True

        def success(task, result):
            self.busy = False
            try:
                if ready:
                    ready(result)
                self._say(name + " completed. Review the plan and results.")
            except Exception as error:
                self._say(f"Could not show the result: {error}. Your original is retained.")

        def failed(task, error):
            self.busy = False
            self._say(f"{name} failed: {error}. Original retained.")

        self.task = self.host._task_manager.submit(
            name, work, on_success=success, on_failure=failed, ui_lifetime=self.lifetime
        )

    def _refresh(self):
        self.plan.ChangeValue(self.project.describe(simple=True))
        self.objects.SetItems([
            f"{i}. {item['kind']}: {item.get('text', '')} {item.get('box', '')}"
            for i, item in enumerate(self.project.operations, 1)
        ])
        if self.project.operations:
            self.objects.SetSelection(len(self.project.operations) - 1)
        self.privacy.SetValue(False)
        self.content_review.SetValue(False)
        self.last_export = None

    def _edit(self, method):
        self._run("Edit screenshot", lambda **kwargs: method(), lambda result: self._refresh())

    def _add(self, event):
        try:
            box = (
                tuple(float(v.strip()) for v in self.position.GetValue().split(","))
                if self.position.GetValue().strip()
                else self.anchors[self.region.GetStringSelection()]
            )
            kind, text = ACTIONS[self.action.GetSelection()], self.caption.GetValue()
        except Exception as error:
            self._say(f"Choose a named region or enter four percentages: {error}")
            self.position.SetFocus()
            return
        self._edit(lambda: self.project.add(kind, box=box, text=text))

    def _history(self, redo):
        self._edit(self.project.redo if redo else self.project.undo)

    def _remove(self, event):
        index = self.objects.GetSelection()
        self._edit(lambda: self.project.remove(index))

    def _move(self, dx, dy, grow=0):
        index = self.objects.GetSelection()
        self._edit(lambda: self.project.move(index, dx, dy, grow))

    def _resize(self, event):
        scale = self.size.GetValue() / 100

        def work():
            image = self.project.render()
            self.project.add(
                "resize",
                width=max(1, round(image.width * scale)),
                height=max(1, round(image.height * scale)),
            )

        self._edit(work)

    def _ocr(self, event):
        if self.project.operations:
            self._say(
                "Find text to select before editing, or undo to the original. Anchors refer to it."
            )
            return

        def work(**kwargs):
            from quill.io.ocr import ocr_image

            return ocr_image(Path(self.project.evidence.path))

        def ready(result):
            evidence = self.project.evidence
            rows = []
            for i, line in enumerate(result.lines, 1):
                rows.append(
                    f"{i}. {line.text}; confidence: "
                    + (f"{line.confidence}%" if line.confidence >= 0 else "not reported")
                )
                if line.bounds:
                    left, top, right, bottom = line.bounds
                    self.anchors[f"Text {i}: {line.text[:80]}"] = (
                        100 * left / evidence.width,
                        100 * top / evidence.height,
                        100 * (right - left) / evidence.width,
                        100 * (bottom - top) / evidence.height,
                    )
            self.region.SetItems(list(self.anchors))
            self.region.SetSelection(0)
            self.plan.AppendText(
                "\n\nOCR in engine reading order (recognition may be wrong):\n" + "\n".join(rows)
            )

        self._run("Find text to select", work, ready)

    def _path(self, title, wildcard, save=False):
        dialog = wx.FileDialog(
            self,
            title,
            wildcard=wildcard,
            style=(wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT)
            if save
            else (wx.FD_OPEN | wx.FD_FILE_MUST_EXIST),
        )
        try:
            return (
                Path(dialog.GetPath())
                if self.host._show_modal_dialog(dialog, title) == wx.ID_OK
                else None
            )
        finally:
            dialog.Destroy()

    def _project_file(self, opening):
        path = self._path(
            "Open screenshot project" if opening else "Save screenshot project",
            "Screenshot project|*.screenshot.json",
            save=not opening,
        )
        if path is None:
            return
        if opening:

            def ready(project):
                self.project = project
                self.anchors = dict(PORTIONS)
                self.region.SetItems(list(self.anchors))
                self.region.SetSelection(0)
                self.goal.ChangeValue(project.goal)
                self.steps.ChangeValue(project.steps)
                self._refresh()

            self._run("Open project", lambda **kw: ScreenshotProject.load(path), ready)
        else:
            self._metadata()
            self._run("Save project", lambda **kw: self.project.save(path))

    def _metadata(self):
        if self.busy:
            self._say("Please wait for the current edit to finish.")
            return False
        self.project.goal, self.project.steps = self.goal.GetValue(), self.steps.GetValue()
        self.project.review = {
            "privacy": "reviewed" if self.privacy.GetValue() else "Not verified",
            "content": "reviewed" if self.content_review.GetValue() else "Not verified",
        }
        return True

    def _export(self, image_format):
        if not self._metadata():
            return

        def ready(evidence):
            self.last_export = evidence
            self.plan.AppendText(f"\n\nSaved image: {evidence.path}\nOriginal kept unchanged.")

        self._run(
            "Export " + image_format,
            lambda **kw: self.project.export(Path(self.project.evidence.path).parent, image_format),
            ready,
        )

    def _bundle(self, event):
        if not self._metadata():
            return
        strict, waiver = self.strict.GetValue(), self.waiver.GetValue()
        self._run(
            "Export evidence bundle",
            lambda **kw: self.project.bundle(
                Path(self.project.evidence.path).parent, strict=strict, waiver=waiver
            ),
            lambda path: self.plan.AppendText(f"\nEvidence ZIP: {path}\nOriginal excluded.\n"),
        )

    def _compare(self, event):
        path = self._path("Compare screenshot", "Images|*.png;*.jpg;*.jpeg;*.webp")
        if path is None:
            return
        self._run(
            "Compare screenshots",
            lambda **kw: compare_screenshots(
                self.project.evidence, verify_capture(path, "Comparison image")
            ),
            lambda result: self.plan.AppendText(
                "\nPixel comparison against ORIGINAL:\n" + json.dumps(result, indent=2)
            ),
        )

    def _preview(self, event):
        from quill.ui.studio_capture_preview import show_screenshot_preview

        scale = (0.25, 0.5, 1, 2, 4)[self.zoom.GetSelection()]
        self._run(
            "Render preview",
            lambda **kw: self.project.render(),
            lambda image: show_screenshot_preview(self.host, self, image, scale),
        )

    def _inspect(self, event):
        if self.busy:
            self._say("Please wait for the current edit to finish.")
            return
        self._metadata()
        self._run(
            "Prepare edited screenshot",
            lambda **kw: self.project.export(Path(self.project.evidence.path).parent),
            lambda evidence: self.host._review_capture(
                evidence, "Edited screenshot. Inspect the rendered image; edit history is excluded."
            ),
        )

    def stop(self):
        self.lifetime.invalidate()
        if self.task is not None:
            self.task.cancellation_token.cancel()

    def _dictate(self, event):
        if self.busy:
            self._say("Wait for the current edit before recording a note.")
            return
        from quill.ui.studio_capture_note import ScreenshotNoteDialog

        dialog = ScreenshotNoteDialog(self.host, self.project.evidence)
        try:
            if self.host._show_modal_dialog(dialog, "Add a spoken screenshot note") == wx.ID_OK:
                self.goal.ChangeValue(dialog.text.GetValue().strip())
                self._say("Reviewed note added. Save it with the image's evidence bundle.")
        finally:
            dialog.stop()
            dialog.Destroy()
