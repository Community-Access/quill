"""The three per-podcast settings whose value is a list, not a value.

Most settings are a number, a switch or one of a few choices, and the settings
panel can draw them from the catalogue without knowing what they mean. Three
cannot be drawn that way, because their value is a **list somebody edits**:

* **Tidy episode titles** -- patterns removed when a title is shown and spoken,
  with a preview of what would change.
* **Skip chapters named** -- chapter titles to jump over as an episode plays.
* **Labels** -- this podcast's own words, usable as a smart-playlist rule.

One window serves all three, because they are the same window: a list, Add,
Edit, Remove, and a sentence saying what the list does *not* do. Three
near-identical dialogs would have been three places to fix the next bug in.

Two rules the shape follows:

* **The list rows are sentences.** ``Remove 'Ep. *: ' at the start. Currently
  on.`` -- not a bare pattern. A row you have to open to understand is a row
  that costs a keystroke every time you pass it.
* **Nothing here deletes an episode.** Every one of these three changes how
  something reads or plays, never what exists; the window says so, once, at the
  top, where it is read on entry.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from quill.core.podcasts import title_cleanup
from quill.core.podcasts.settings_resolver import LEVEL_SHOW, set_value, value_of
from quill.core.podcasts.settings_types import SettingDef
from quill.ui.dialog_contract import apply_modal_ids, show_modal_dialog

TITLE = "Edit List"

#: What each list-shaped setting is called, what one row of it is called, and
#: the sentence that says what it does not do.
_SUBJECTS: dict[str, tuple[str, str, str]] = {
    "title_cleanup": (
        "Tidy Episode Titles",
        "pattern",
        "Patterns are removed when a title is shown and spoken. The feed's own "
        "titles are never changed and no episode is renamed.",
    ),
    "chapter_skip": (
        "Skip Chapters",
        "chapter title",
        "Matching chapters are jumped over as an episode plays. Nothing is "
        "removed from the episode and the chapters stay in its chapter list.",
    ),
    "labels": (
        "Labels",
        "label",
        "Labels are your own words for this podcast. Labelling never moves a "
        "podcast out of its folder and never changes what is downloaded.",
    ),
}


def edit_opaque_setting(
    parent: Any,
    *,
    library: Any,
    show: Any,
    definition: SettingDef,
    announce: Callable[[str], None] | None = None,
) -> bool:
    """Edit one list-shaped setting; True when it changed."""
    dialog = ListSettingDialog(
        parent, library=library, show=show, definition=definition, announce_cb=announce
    )
    return dialog.show()


class ListSettingDialog:
    """A list, its verbs, and a preview where a preview makes sense."""

    def __init__(
        self,
        parent: object,
        *,
        library: Any,
        show: Any,
        definition: SettingDef,
        announce_cb: Callable[[str], None] | None = None,
    ) -> None:
        import wx

        self._wx = wx
        self._library = library
        self._show = show
        self._definition = definition
        self._announce = announce_cb or (lambda _m: None)
        self._changed = False
        self._kind = definition.editor or definition.id
        subject, noun, caveat = _SUBJECTS.get(
            self._kind, (definition.label_text().rstrip("."), "entry", definition.help)
        )
        self._noun = noun
        self._title = f"{subject} -- {show.title}"
        self._entries: list[Any] = _load(library, show, definition, self._kind)

        self.dialog = wx.Dialog(
            parent, title=self._title, style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
        )
        self.dialog.SetMinSize((560, 460))
        root = wx.BoxSizer(wx.VERTICAL)

        intro = wx.StaticText(self.dialog, label=caveat)
        intro.Wrap(520)
        root.Add(intro, 0, wx.EXPAND | wx.ALL, 10)

        root.Add(wx.StaticText(self.dialog, label="&List:"), 0, wx.LEFT | wx.RIGHT, 10)
        self._list = wx.ListBox(self.dialog, choices=[], style=wx.LB_SINGLE)
        self._list.SetName("Entries")
        self._list.SetHelpText(definition.help)
        root.Add(self._list, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        verbs = wx.BoxSizer(wx.HORIZONTAL)
        self._add_btn = wx.Button(self.dialog, label="&Add...")
        self._add_btn.SetHelpText(f"Adds one {noun}. Nothing is applied until you save.")
        self._edit_btn = wx.Button(self.dialog, label="&Edit...")
        self._edit_btn.SetHelpText(f"Changes the highlighted {noun}; it deletes nothing.")
        self._remove_btn = wx.Button(self.dialog, label="&Remove")
        self._remove_btn.SetHelpText(
            f"Removes the highlighted {noun} from the list. It removes the "
            f"{noun} only -- no episode is affected."
        )
        for button in (self._add_btn, self._edit_btn, self._remove_btn):
            verbs.Add(button, 0, wx.RIGHT, 6)
        root.Add(verbs, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        self._preview_btn = None
        self._preview_list = None
        if self._kind == "title_cleanup":
            self._preview_btn = wx.Button(self.dialog, label="Pre&view")
            self._preview_btn.SetHelpText(
                "Shows which of the 50 newest titles these patterns would change, "
                "and how. It is a dry run: no title is altered by pressing it."
            )
            root.Add(self._preview_btn, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)
            root.Add(
                wx.StaticText(self.dialog, label="Preview res&ults:"), 0, wx.LEFT | wx.RIGHT, 10
            )
            self._preview_list = wx.ListBox(self.dialog, choices=[], style=wx.LB_SINGLE)
            self._preview_list.SetName("Preview results")
            self._preview_list.SetHelpText(
                "Each title these patterns would change, before and after. It "
                "reports; it has changed nothing."
            )
            root.Add(self._preview_list, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)
            self._preview_btn.Bind(wx.EVT_BUTTON, self._on_preview)

        row = wx.BoxSizer(wx.HORIZONTAL)
        row.AddStretchSpacer()
        ok_btn = wx.Button(self.dialog, wx.ID_OK, "Save")
        ok_btn.SetHelpText("Saves this list for this podcast only.")
        cancel_btn = wx.Button(self.dialog, wx.ID_CANCEL, "Cancel")
        cancel_btn.SetHelpText("Leaves the list exactly as it was.")
        row.Add(ok_btn, 0, wx.RIGHT, 6)
        row.Add(cancel_btn)
        root.Add(row, 0, wx.EXPAND | wx.ALL, 10)

        self.dialog.SetSizer(root)
        self._add_btn.Bind(wx.EVT_BUTTON, self._on_add)
        self._edit_btn.Bind(wx.EVT_BUTTON, self._on_edit)
        self._remove_btn.Bind(wx.EVT_BUTTON, self._on_remove)
        ok_btn.Bind(wx.EVT_BUTTON, self._on_ok)
        self._fill()

    # -- the list ------------------------------------------------------------

    def _fill(self, *, select: int = -1) -> None:
        wanted = select if select >= 0 else self._list.GetSelection()
        self._list.Set([_describe(entry, self._kind) for entry in self._entries])
        if self._entries:
            self._list.SetSelection(
                max(0, min(wanted if wanted >= 0 else 0, len(self._entries) - 1))
            )
        for button in (self._edit_btn, self._remove_btn):
            button.Enable(bool(self._entries))

    def _selected(self) -> int:
        index = self._list.GetSelection()
        return index if 0 <= index < len(self._entries) else -1

    def _ask(self, current: str = "") -> str:
        """One line of text, asked for plainly.

        A text prompt rather than a form: every one of these three is a single
        string, and a window with one field in it is a window with one field in
        it, however many settings share the code.
        """
        wx = self._wx
        prompt = wx.TextEntryDialog(
            self.dialog,
            f"{self._definition.help}\n\nThe {self._noun}:",
            self._title,
            current,
        )
        try:
            if prompt.ShowModal() != wx.ID_OK:
                return ""
            return prompt.GetValue().strip()
        finally:
            prompt.Destroy()

    def _on_add(self, _event: object) -> None:
        text = self._ask()
        if not text:
            return
        self._entries.append(_make(text, self._kind))
        self._fill(select=len(self._entries) - 1)
        self._announce(f"{len(self._entries)} {self._noun}s. Nothing saved yet.")

    def _on_edit(self, _event: object) -> None:
        index = self._selected()
        if index < 0:
            return
        text = self._ask(_text_of(self._entries[index], self._kind))
        if not text:
            return
        self._entries[index] = _make(text, self._kind)
        self._fill(select=index)
        self._announce("Entry updated. Nothing saved yet.")

    def _on_remove(self, _event: object) -> None:
        index = self._selected()
        if index < 0:
            return
        del self._entries[index]
        self._fill(select=min(index, len(self._entries) - 1))
        self._announce(f"Removed. {len(self._entries)} left. Nothing saved yet.")

    def _on_preview(self, _event: object) -> None:
        from quill.core.podcasts.episode_filters import newest_episodes

        titles = [episode.title for episode in newest_episodes(self._show.episodes)]
        rows = title_cleanup.preview(titles, self._entries)
        if self._preview_list is not None:
            self._preview_list.Set(rows)
            if rows:
                self._preview_list.SetSelection(0)
        self._announce(title_cleanup.preview_summary(titles, self._entries))

    def _on_ok(self, _event: object) -> None:
        _store(self._library, self._show, self._definition, self._kind, self._entries)
        self._changed = True
        self._announce(
            f"Saved {len(self._entries)} {self._noun}"
            f"{'' if len(self._entries) == 1 else 's'} for {self._show.title}."
        )
        self._close_ok()

    def _close_ok(self) -> None:
        """Dismiss with OK, if this window is running a modal loop.

        Guarded because ``EndModal`` on a window that was never shown modally
        is a hard wxWidgets assertion rather than a no-op, and this handler is
        reachable without a loop -- from a test, and from a caller that built
        the window to read it rather than to show it.
        """
        if self.dialog.IsModal():
            self.dialog.EndModal(self._wx.ID_OK)

    def show(self) -> bool:
        wx = self._wx
        self.dialog.CentreOnParent()
        apply_modal_ids(
            self.dialog,
            affirmative_id=wx.ID_OK,
            affirmative_label="Save",
            cancel_id=wx.ID_CANCEL,
            escape_id=wx.ID_CANCEL,
        )
        try:
            show_modal_dialog(self.dialog, self._title, announce=self._announce)
            return self._changed
        finally:
            self.dialog.Destroy()


# -- the three shapes, in one place ------------------------------------------


def _load(library: Any, show: Any, definition: SettingDef, kind: str) -> list[Any]:
    if kind == "labels":
        return list(library.labels_for(show.id))
    stored = value_of(library, definition, show=show)
    if kind == "title_cleanup":
        return list(title_cleanup.rules_from_stored(stored))
    return [str(entry) for entry in (stored or ()) if str(entry).strip()]


def _store(library: Any, show: Any, definition: SettingDef, kind: str, entries: list[Any]) -> None:
    if kind == "labels":
        cleaned = [str(entry).strip() for entry in entries if str(entry).strip()]
        if cleaned:
            library.show_labels[show.id] = cleaned
        else:
            library.show_labels.pop(show.id, None)
        return
    if kind == "title_cleanup":
        set_value(
            library,
            definition,
            title_cleanup.rules_to_stored(entries),
            level=LEVEL_SHOW,
            scope_id=show.id,
        )
        return
    set_value(
        library,
        definition,
        [str(entry) for entry in entries],
        level=LEVEL_SHOW,
        scope_id=show.id,
    )


def _make(text: str, kind: str) -> Any:
    return title_cleanup.TitleRule(pattern=text) if kind == "title_cleanup" else text


def _text_of(entry: Any, kind: str) -> str:
    return entry.pattern if kind == "title_cleanup" else str(entry)


def _describe(entry: Any, kind: str) -> str:
    if kind == "title_cleanup":
        return entry.describe()
    if kind == "chapter_skip":
        return f"Skip chapters named {entry!r}."
    return str(entry)


__all__ = ["ListSettingDialog", "edit_opaque_setting"]
