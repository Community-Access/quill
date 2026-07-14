"""The "Train Writing Style" dialog.

Lets the user teach Quill their writing voice: add samples (paste, or learn
from the current document), then build a style guide with the on-device model.
When enabled, the assistant writes in that style. Stored locally.
"""

from __future__ import annotations

import threading

from quill.core.ai.style import add_sample, build_guide, load_style, save_style
from quill.ui.dialog_contract import apply_modal_ids, show_modal_dialog


class TrainStyleDialog:
    def __init__(self, parent: object, assistant: object, *, get_document, announce=None) -> None:
        import wx

        self._wx = wx
        self._assistant = assistant
        self._get_document = get_document
        self._announce = announce or (lambda _m: None)
        self._profile = load_style()

        self.dialog = wx.Dialog(
            parent, title="Train Writing Style", style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
        )
        self.dialog.SetSize((640, 620))
        outer = wx.BoxSizer(wx.VERTICAL)

        self.enabled = wx.CheckBox(self.dialog, label="Write in my style when Quill generates text")
        self.enabled.SetValue(self._profile.enabled)
        outer.Add(self.enabled, 0, wx.ALL, 14)

        outer.Add(
            wx.StaticText(self.dialog, label="Add a writing sample"),
            0,
            wx.LEFT | wx.RIGHT,
            14,
        )
        self.sample = wx.TextCtrl(self.dialog, style=wx.TE_MULTILINE)
        self.sample.SetName("Writing sample")
        self.sample.SetMinSize((-1, 110))
        outer.Add(self.sample, 0, wx.EXPAND | wx.ALL, 14)

        sample_row = wx.BoxSizer(wx.HORIZONTAL)
        self.add_button = wx.Button(self.dialog, label="Add Sample")
        self.learn_doc_button = wx.Button(self.dialog, label="Learn from Current Document")
        sample_row.Add(self.add_button, 0, wx.RIGHT, 8)
        sample_row.Add(self.learn_doc_button, 0)
        outer.Add(sample_row, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 14)

        self.count_label = wx.StaticText(self.dialog, label="")
        outer.Add(self.count_label, 0, wx.LEFT | wx.RIGHT, 14)

        self.build_button = wx.Button(self.dialog, label="Build / Update My Style")
        outer.Add(self.build_button, 0, wx.ALL, 14)

        outer.Add(wx.StaticText(self.dialog, label="My style guide"), 0, wx.LEFT | wx.RIGHT, 14)
        self.guide = wx.TextCtrl(self.dialog, style=wx.TE_MULTILINE | wx.TE_READONLY)
        self.guide.SetName("Style guide")
        outer.Add(self.guide, 1, wx.EXPAND | wx.ALL, 14)

        footer = wx.BoxSizer(wx.HORIZONTAL)
        self.clear_button = wx.Button(self.dialog, label="Clear Style")
        footer.Add(self.clear_button, 0, wx.RIGHT, 8)
        footer.AddStretchSpacer()
        footer.Add(wx.Button(self.dialog, wx.ID_OK, label="Save"), 0, wx.RIGHT, 8)
        footer.Add(wx.Button(self.dialog, wx.ID_CANCEL, label="Cancel"), 0)
        outer.Add(footer, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 14)
        self.dialog.SetSizer(outer)

        self.guide.SetValue(self._profile.guide)
        self._refresh_count()

        self.add_button.Bind(wx.EVT_BUTTON, self._on_add)
        self.learn_doc_button.Bind(wx.EVT_BUTTON, self._on_learn_doc)
        self.build_button.Bind(wx.EVT_BUTTON, self._on_build)
        self.clear_button.Bind(wx.EVT_BUTTON, self._on_clear)

        def _check_avail() -> None:
            avail, reason = assistant.is_available()
            self._wx.CallAfter(self._on_ai_availability_checked, avail, reason)

        threading.Thread(  # GATE-40-OK: AI availability probe.
            target=_check_avail, daemon=True
        ).start()

    def _on_ai_availability_checked(self, available: bool, reason: str | None) -> None:
        if not available:
            self.build_button.Enable(False)
            self._announce(f"AI unavailable: {reason}")

    def _refresh_count(self) -> None:
        n = len(self._profile.samples)
        self.count_label.SetLabel(f"Samples collected: {n}")

    def _on_add(self, _event: object) -> None:
        text = self.sample.GetValue().strip()
        if not text:
            self._announce("Paste a writing sample first")
            return
        add_sample(self._profile, text)
        self.sample.SetValue("")
        self._refresh_count()
        self._announce("Sample added")
        self._start_build()

    def _on_learn_doc(self, _event: object) -> None:
        text = self._get_document().strip()
        if not text:
            self._announce("The current document is empty")
            return
        add_sample(self._profile, text)
        self._refresh_count()
        self._announce("Learned from the current document")
        self._start_build()

    def _on_build(self, _event: object) -> None:
        # If nothing has been added yet, fall back to the sample field, then the
        # current document, so "Build" just works.
        if not self._profile.samples:
            pasted = self.sample.GetValue().strip()
            if pasted:
                add_sample(self._profile, pasted)
                self.sample.SetValue("")
            elif self._get_document().strip():
                add_sample(self._profile, self._get_document())
            else:
                self._announce("Add a writing sample or open a document first")
                return
            self._refresh_count()
        self._start_build()

    def _start_build(self) -> None:
        available, _reason = self._assistant.is_available()
        if not available or not self._profile.samples:
            return
        self.build_button.Enable(False)
        self.guide.SetValue("Analyzing your samples…")
        self._announce("Analyzing your writing")

        def worker() -> None:
            try:
                guide = build_guide(self._assistant, self._profile)
            except Exception as exc:  # noqa: BLE001
                guide = f"Error: {exc}"
            self._wx.CallAfter(self._deliver_guide, guide)

        threading.Thread(  # GATE-40-OK: style-guide build worker.
            target=worker, daemon=True
        ).start()

    def _deliver_guide(self, guide: str) -> None:
        self.guide.SetValue(guide)
        self.build_button.Enable(True)
        if guide and not guide.startswith("Error:"):
            self.enabled.SetValue(True)  # so the style is actually used
            self._announce("Style guide ready and enabled")
        else:
            self._announce("Could not build style guide")

    def _on_clear(self, _event: object) -> None:
        self._profile.samples = []
        self._profile.guide = ""
        self._profile.enabled = False
        self.guide.SetValue("")
        self.enabled.SetValue(False)
        self._refresh_count()
        save_style(self._profile)  # remove immediately, even without pressing Save
        self._announce("Writing style removed")

    def show(self) -> None:
        wx = self._wx
        self.dialog.CentreOnParent()
        apply_modal_ids(self.dialog, affirmative_id=wx.ID_OK, escape_id=wx.ID_CANCEL)
        try:
            if show_modal_dialog(self.dialog, "Train Writing Style") == wx.ID_OK:
                self._profile.enabled = self.enabled.GetValue()
                save_style(self._profile)
                self._announce("Saved writing style")
        finally:
            self.dialog.Destroy()
