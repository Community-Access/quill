"""Scribe for Documents in Quill Beacon (PRD 8.7), and opening a place.

* **Scribe Documents** in the Destinations list shows every place that points
  into a Scribe result (:mod:`quill.apps.beacon.scribe_places`), in Beacon's
  own results list and details.
* **Tools > Scribe for Documents > Add My Scribe Documents as Places** reads
  the person's Scribe library (on their command, off the UI thread) and makes
  a place for each document that is not one yet, then says one sentence: "Added
  5 Scribe documents as places; 2 were already there." The submenu also holds
  the family's shared rows (:mod:`quill.ui.scribe_app_host`).
* **Opening a place whose file is gone.** If the Scribe library has the file
  again (downloaded since), the place follows it. Otherwise Beacon checks the
  account first, then asks "Download Again from Scribe for Documents" only
  when the document is still there (Yes is the default: the Convert dialog
  that follows uploads nothing and is itself the confirmation); a document no
  longer in the account gets one message with OK, and offline or signed out is
  said, not asked (accessibility review, 2026-11-21).

``_open_beacon`` moved here from :mod:`quill.apps.beacon.app` under GATE-11
(extract, never rebaseline): opening a place is where the Scribe part hooks in.
"""

from __future__ import annotations

import os
import sys
import webbrowser
from pathlib import Path
from typing import Any

import wx

from quill.apps.beacon.model import HEALTH_BROKEN
from quill.apps.beacon.scribe_places import add_library, document_id_of, is_scribe, scribe_places
from quill.core.scribe import PRODUCT_NAME
from quill.ui.scribe_app_host import (
    COMMON_ROWS,
    ENTRY_KEY,
    AppScribeHost,
    AppScribeMixin,
    append_scribe_submenu,
)

__all__ = ["SCOPE", "BeaconScribeHost", "BeaconScribeMixin"]

_TITLE = "Quill Beacon"
SCOPE = "scribe"
ASK_TITLE = "Download Again from Scribe for Documents"
EMPTY = (
    "No Scribe places yet. Use Tools, Scribe for Documents, Add My Scribe Documents "
    f"as Places, {ENTRY_KEY}."
)


class BeaconScribeHost(AppScribeHost):
    """Beacon's side: its announcer; results open elsewhere, on command."""

    def scribe_parent(self) -> Any:
        return wx.GetActiveWindow() or self._owner

    def scribe_announce(self, text: str) -> None:
        self._owner.announcer.say(text)


class BeaconScribeMixin(AppScribeMixin):
    """The destination, the Tools submenu and opening a place (8.7)."""

    scribe_app_name = _TITLE

    def _scribe_make_host(self) -> Any:
        return BeaconScribeHost(self, _TITLE)

    def _scribe_frame(self) -> Any:
        return self

    def _scribe_modal(self, dialog: Any, title: str) -> int:
        from quill.ui.dialog_contract import show_modal_dialog

        return int(show_modal_dialog(dialog, title))

    def _scribe_say(self, text: str) -> None:
        self.announcer.say(text)  # type: ignore[attr-defined]

    # -- the menu ----------------------------------------------------------

    def _append_scribe_menu(self, tools: Any) -> None:
        append_scribe_submenu(
            self,
            tools,
            wx,
            title="Scribe for &Documents",
            first=("&Add My Scribe Documents as Places", self.scribe_add_places),
        )

    def _scribe_palette(self, command: Any) -> list[Any]:
        """The Command Palette's rows for the submenu, with their keys."""
        rows = [("Add My Scribe Documents as Places", ENTRY_KEY, self.scribe_add_places)]
        rows += [
            (label.replace("&", "").removesuffix("..."), key, getattr(self, handler))
            for _command_id, label, handler, key in COMMON_ROWS
        ]
        return [command(name, key, lambda _e, run=run: run()) for name, key, run in rows]

    # -- the destination -----------------------------------------------------

    def _scribe_scope_results(self, say_count: bool = True) -> bool:
        """Fill the results with Scribe places when that destination is chosen."""
        if self.current_scope != SCOPE:  # type: ignore[attr-defined]
            return False
        if not say_count:  # a refill the reader did not ask for (FUX-06)
            self._scribe_refresh_quietly()
            return True
        places, query = self._scribe_listed()
        self._results_cache = places  # type: ignore[attr-defined]
        self.results.SetItemCount(len(places))  # type: ignore[attr-defined]
        if not places and query:
            self.announcer.announce_count(0, filtered=True)  # type: ignore[attr-defined]
            return True
        if not places:
            self.announcer.say(EMPTY)  # type: ignore[attr-defined]
            return True
        self.results.RefreshItem(0)  # type: ignore[attr-defined]
        self.announcer.announce_count(len(places), filtered=bool(query))  # type: ignore[attr-defined]
        self._show_details(places[0])  # type: ignore[attr-defined]
        return True

    def _scribe_listed(self) -> tuple[list[Any], str]:
        """The Scribe places the search box lets through, and the search."""
        places = scribe_places(self.store)  # type: ignore[attr-defined]
        query = (self.last_query or "").strip().lower()  # type: ignore[attr-defined]
        if query:
            places = [b for b in places if query in b.title.lower()]
        return places, query

    def _scribe_refresh_quietly(self) -> None:
        """The Scribe destination after new places: no count spoken, the search
        kept, and the reader left on the same place, wherever it now is (FUX-06)."""
        if self.current_scope != SCOPE:  # type: ignore[attr-defined]
            return
        results = self.results  # type: ignore[attr-defined]
        old = list(getattr(self, "_results_cache", []))
        focused = results.GetFocusedItem() if hasattr(results, "GetFocusedItem") else -1
        keep = old[focused].beacon_id if 0 <= focused < len(old) else ""
        places, _query = self._scribe_listed()
        self._results_cache = places  # type: ignore[attr-defined]
        results.SetItemCount(len(places))
        index = next((i for i, b in enumerate(places) if b.beacon_id == keep), -1)
        if index >= 0:
            both = wx.LIST_STATE_FOCUSED | wx.LIST_STATE_SELECTED
            results.SetItemState(index, both, both)
            results.EnsureVisible(index)
        results.Refresh()

    # -- Add My Scribe Documents as Places ----------------------------------

    def scribe_add_places(self) -> None:
        controller = self._scribe()
        if not controller.check_available() or not controller.ensure_signed_in():
            return
        if self.__dict__.get("_scribe_adding"):
            self._scribe_say("Already reading your Scribe documents.")
            return
        self.__dict__["_scribe_adding"] = True

        def slow() -> None:
            if self.__dict__.get("_scribe_adding"):
                self._scribe_say("Reading your Scribe documents...")

        wx.CallLater(1000, slow)

        def read() -> Any:
            return controller.client().list_documents()[0]

        def done(documents: Any) -> None:
            self.__dict__["_scribe_adding"] = False
            from quill.core.scribe.library import Library

            library = Library()
            files: dict[str, tuple[str, Path]] = {}
            for document in documents:
                found = library.files_for(document.id)
                if found:
                    files[document.id] = found[-1]
            # Our own name where we uploaded it, not Scribe's title from inside (F6).
            pairs = [(d.id, library.title_for(d.id) or d.display_title) for d in documents]
            added, already = add_library(self.store, pairs, files)  # type: ignore[attr-defined]
            self._scribe_refresh_quietly()
            self._scribe_say(_added_sentence(added, already))

        def failed(error: BaseException) -> None:
            self.__dict__["_scribe_adding"] = False
            controller._failed(error)

        controller._background(read, done, failed)

    # -- opening a place -----------------------------------------------------

    def _open_beacon(self, b: Any) -> None:
        res = self.store.get_resource(b.resource_id) if b.resource_id else None  # type: ignore[attr-defined]
        if is_scribe(res) and not _exists(res.primary_uri):
            if not self._scribe_follow_library(res):
                self._scribe_offer_download(b, res)
                return
        if not res or not res.primary_uri:
            self.announcer.say("No openable address for this bookmark")  # type: ignore[attr-defined]
            return
        uri = res.primary_uri
        if res.type in ("file", "folder", "document") and not uri.startswith(("http:", "https:")):
            if not Path(uri).exists():
                self.announcer.say("File or folder not found. Marked as broken.")  # type: ignore[attr-defined]
                self.store.conn.execute(  # type: ignore[attr-defined]
                    "UPDATE beacons SET health=? WHERE beacon_id=?", (HEALTH_BROKEN, b.beacon_id)
                )
                self.store.conn.commit()  # type: ignore[attr-defined]
                self._refresh_results()  # type: ignore[attr-defined]
                return
            if sys.platform.startswith("win"):
                os.startfile(uri)  # noqa: S606 (local user file)
            else:
                import subprocess

                subprocess.Popen(["open", uri] if sys.platform == "darwin" else ["xdg-open", uri])
        else:
            webbrowser.open(uri)
        self.store.record_open(b.beacon_id)  # type: ignore[attr-defined]
        self.announcer.say(f"Opened {b.title}")  # type: ignore[attr-defined]

    def _scribe_follow_library(self, res: Any) -> bool:
        """The file was downloaded again since: point the place at it."""
        from quill.core.scribe.library import Library

        found = Library().files_for(document_id_of(res))
        if not found:
            return False
        format_id, path = found[-1]
        res.primary_uri = str(path)
        res.metadata = {**res.metadata, "scribe_format": format_id}
        self.store.put_resource(res)  # type: ignore[attr-defined]
        return True

    def _scribe_offer_download(self, b: Any, res: Any) -> None:
        """B5: check the account, then ask only when there is something to get."""
        controller = self._scribe()
        if not controller.check_available():
            return
        if not controller.session.is_signed_in():
            self._scribe_say(
                f"{b.title} is not on this computer. Sign in to {PRODUCT_NAME} from Tools, "
                "Scribe for Documents, Options, to download it again."
            )
            return
        if self.__dict__.get("_scribe_checking"):
            self._scribe_say("Already checking your Scribe account.")
            return
        self.__dict__["_scribe_checking"] = True
        document_id = document_id_of(res)
        never = not res.primary_uri
        where = "is not on this computer" if never else "is no longer on this computer"

        def slow() -> None:
            if self.__dict__.get("_scribe_checking"):
                self._scribe_say("Checking your Scribe account...")

        wx.CallLater(1000, slow)

        def find() -> Any:
            documents = controller.client().list_documents()[0]
            return next((d for d in documents if d.id == document_id), None)

        def failed(error: BaseException) -> None:
            self.__dict__["_scribe_checking"] = False
            controller._failed(error)

        def found(document: Any) -> None:
            from quill.ui.dialog_contract import show_message_box

            self.__dict__["_scribe_checking"] = False
            if document is None:
                self._scribe_say(  # said, not a box: there is nothing to choose
                    f"{b.title} {where} or in your Scribe account. Delete removes the place."
                )
                return
            if not self._scribe_still_here(b):
                self._scribe_say(f"{b.title} can be downloaded again. Press Enter on it to choose.")
                return
            answer = show_message_box(
                f"{b.title} {where}. Download it again from My Scribe Documents? Nothing is "
                "uploaded and no pages are used.",
                ASK_TITLE,
                wx.YES_NO | wx.ICON_QUESTION,
                self,
            )
            if answer == wx.YES:
                controller.convert_existing(document)

        controller._background(find, found, failed)

    def _scribe_still_here(self, b: Any) -> bool:
        """The person is still in Beacon, on the same place, with nothing open over it."""
        if not self.IsActive() or not self.IsEnabled():  # type: ignore[attr-defined]
            return False
        results = self.results  # type: ignore[attr-defined]
        index = results.GetFirstSelected()
        cache = getattr(self, "_results_cache", [])
        return 0 <= index < len(cache) and cache[index].beacon_id == b.beacon_id


def _exists(uri: str) -> bool:
    return bool(uri) and Path(uri).exists()


def _added_sentence(added: int, already: int) -> str:
    noun = "document" if added == 1 else "documents"
    text = f"Added {added} Scribe {noun} as places"
    if already:
        text += f"; {already} {'was' if already == 1 else 'were'} already there"
    return text + "."
