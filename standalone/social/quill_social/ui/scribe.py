"""Scribe for Documents in QUILL Social: a post's linked documents (PRD 8.8).

**Item > Convert Linked Document with Scribe for Documents...** finds the
links in the selected post -- its text, its own link and its media -- that
point straight at a file Scribe takes, and sends the one the person chooses
by its address, as QUILL Cast does for an episode (8.6). None: one sentence;
one: the shared Convert dialog at once; several: "Choose a Linked Document".

**Tools** gains the family's shared rows -- Scribe Conversions, My Scribe
Documents, Scribe Status, Repeat Last Scribe Message and Scribe for Documents
Options -- on the keys they have in every app (``keymap.DEFAULT_BINDINGS``).

Everything else is the shared code in ``quill.ui`` and ``quill.core.scribe``:
one sign-in, one queue, one set of windows for the whole family. A result
opens in QUILL (or QUILL Lite) from Open Result or Next Steps, never by itself,
so the result sentence is not cut off by the editor coming to the front.
Social speaks through its own announcer, so a Scribe sentence and a new-post
announcement queue rather than interrupt each other.
"""

from __future__ import annotations

from typing import Any

from quill.ui.scribe_app_host import AppScribeHost, AppScribeMixin

__all__ = ["ITEM_ROW", "SocialScribeHost", "SocialScribeMixin", "TOOLS_ROWS"]

_TITLE = "QUILL Social"

#: The Item menu's row, and the Tools menu's, as ``(label, command id)``.
ITEM_ROW = ("Convert Linked Document with &Scribe for Documents...", "scribe_convert_linked")
TOOLS_ROWS = (
    ("Scri&be Conversions", "scribe_conversions"),
    ("My Scribe &Documents", "scribe_my_documents"),
    ("Scribe St&atus", "scribe_status"),
    ("Repeat Last Scribe &Message", "scribe_repeat"),
    ("Scrib&e for Documents Options...", "scribe_options"),
)

#: Command Center names, by command id.
_NAMES = {
    "scribe_convert_linked": "Convert linked document with Scribe for Documents",
    "scribe_conversions": "Scribe Conversions",
    "scribe_my_documents": "My Scribe Documents",
    "scribe_status": "Scribe status",
    "scribe_repeat": "Repeat last Scribe message",
    "scribe_options": "Scribe for Documents options",
}


def scribe_purpose(title: str) -> str:
    """F1 in a Scribe window opened from Social: the family's own words."""
    from quill.core.scribe.surface_help import SCRIBE_PREFIX_PURPOSES, SCRIBE_PURPOSES

    stripped = title.strip()
    if stripped in SCRIBE_PURPOSES:
        return SCRIBE_PURPOSES[stripped]
    for prefix, purpose in SCRIBE_PREFIX_PURPOSES:
        if stripped.startswith(prefix):
            return purpose
    return (
        "A QUILL Social window. Tab moves between its controls, Escape closes it, and "
        "F1 on any control explains that control."
    )


def _activate_scribe_help() -> None:
    """F1 on the shared Scribe windows, which open through the dialog contract.
    Social's own F1 (the Keyboard Guide, from its main window) is untouched."""
    try:
        from quill.ui import app_context_help

        app_context_help.activate(scribe_purpose)
    except Exception:  # noqa: BLE001 - help must never stop the window opening
        pass


class SocialScribeHost(AppScribeHost):
    """Social's side: its announcer, and results opened elsewhere."""

    def scribe_parent(self) -> Any:
        import wx

        return wx.GetActiveWindow() or self._owner

    def scribe_announce(self, text: str) -> None:
        self._owner.announcer.say(text, "normal")


class SocialScribeMixin(AppScribeMixin):
    """The Scribe commands on the Social window (a plain ``wx.Frame``)."""

    scribe_app_name = _TITLE

    def _scribe_make_host(self) -> Any:
        return SocialScribeHost(self, _TITLE)

    def _scribe_frame(self) -> Any:
        return self

    def _scribe_modal(self, dialog: Any, title: str) -> int:
        from quill.ui.dialog_contract import show_modal_dialog

        return int(show_modal_dialog(dialog, title))

    def _scribe_say(self, text: str) -> None:
        self.announcer.say(text, "normal")  # type: ignore[attr-defined]

    def _scribe_handlers(self) -> dict[str, Any]:
        """Command id -> handler, for the menu and the key hook."""
        self._scribe_menu_ready()  # once: pick up jobs another app left (7.4)
        _activate_scribe_help()
        return {
            "scribe_convert_linked": self.cmd_scribe_convert_linked,
            "scribe_conversions": self.scribe_conversions,
            "scribe_my_documents": self.scribe_my_documents,
            "scribe_status": self.scribe_status,
            "scribe_repeat": self.scribe_repeat,
            "scribe_options": self.scribe_options,
        }

    def _scribe_commands(self, keymap: Any, command: Any) -> list[Any]:
        """The Command Center rows, each with its key."""
        handlers = self._scribe_handlers()
        return [
            command(cid, name, handlers[cid], synonyms=["scribe"], shortcut=keymap.chord_for(cid))
            for cid, name in _NAMES.items()
        ]

    def cmd_scribe_convert_linked(self) -> None:
        from quill.core.scribe.links import documents_in_text
        from quill.ui.scribe_link_choice import convert_linked

        item = self._current_item()  # type: ignore[attr-defined]
        if item is None:
            self.announcer.error("Select a post first.")  # type: ignore[attr-defined]
            return
        extra = [str(getattr(item, "uri", "") or "")]
        extra += [str(getattr(media, "uri", "") or "") for media in getattr(item, "media", [])]
        documents = documents_in_text(str(getattr(item, "text", "") or ""), *extra)
        convert_linked(
            self._scribe(),
            documents,
            parent=self,
            where="this post",
            subject="this post",
            verb="links",
            say=self._scribe_say,
            modal=self._scribe_modal,
        )
