"""The searches Find Stations has already run, as the name field's dropdown.

Split out of ``station_browser_dialog`` under GATE-11: that module is the
largest surface in the radio UI and the rule is to extract rather than grow it.
The split is along a real seam, not an arbitrary line count -- everything here
is about *remembered* searches, and the dialog it mixes into knows only that
its name field is a combo.

The model is pure and lives in :mod:`quill.core.radio.search_history`; this is
the wx half: filling the dropdown, translating a picked row back into the query
it describes, and deciding which searches are worth remembering.
"""

from __future__ import annotations

from quill.core.radio import search_history
from quill.core.radio.search_history import SearchQuery


class RecentSearchesMixin:
    """Recent-search behaviour for :class:`StationBrowserDialog`.

    Expects the host to provide ``_name_ctrl`` (a combo), ``_tag_ctrl``,
    ``_country_ctrl``, ``_recent_searches``, ``_on_recent_searches_changed``,
    ``_announce`` and ``_on_search``.
    """

    def _fill_recent_searches(self) -> None:
        """Put the remembered searches in the name field's dropdown.

        Each row is the *whole* query spelled out -- "jazz, tagged blues, in
        France" -- rather than the bare name, because the three fields compose
        and two searches that differ only by country would otherwise read as
        the same row twice.
        """
        try:
            self._name_ctrl.Set([query.label() for query in self._recent_searches])
        except RuntimeError:  # the dialog is being torn down
            pass

    def _on_recent_search_picked(self, event: object) -> None:
        """Restore a remembered search into all three fields, then run it.

        The dropdown holds labels, not names, so the picked row has to be
        translated back into the query it describes -- otherwise the name box
        would be left holding the sentence "jazz, tagged blues, in France",
        which is not a station name and finds nothing.
        """
        index = int(getattr(event, "GetSelection", lambda: -1)() or -1)
        if not (0 <= index < len(self._recent_searches)):
            return
        query = self._recent_searches[index]
        self._name_ctrl.SetValue(query.name)
        self._tag_ctrl.SetValue(query.tag)
        self._select_country(query.country)
        self._announce(f"Searching again for {query.label()}.")
        # Deliberately NOT `self._on_search(event)`. That would hand `_on_search`
        # an EVT_COMBOBOX, which it reads as "somebody is arrowing a dropdown"
        # and answers by leaving focus where it is and skipping the history.
        # Picking a remembered search is the opposite of that -- it is a commit,
        # so it lands on the results and moves the search back to the top of the
        # list. Passing None gives it an event type it does not recognise, which
        # is exactly the commit path the Search button takes.
        self._on_search(None)

    def _select_country(self, country: str) -> None:
        """Point the Country choice at *country*, or at Any when it is not there.

        A remembered country can outlive the list it came from: the dropdown is
        filled from RadioBrowser's own country list, which arrives off-thread
        and can be empty when the dialog has only just opened. Falling back to
        Any is the honest answer -- re-running the search without a country
        filter finds more than the listener asked for, never less, and the
        Country field visibly says so.
        """
        target = country.strip()
        if not target:
            self._country_ctrl.SetSelection(0)
            return
        for index in range(self._country_ctrl.GetCount()):
            if self._country_ctrl.GetString(index).strip().casefold() == target.casefold():
                self._country_ctrl.SetSelection(index)
                return
        self._country_ctrl.SetSelection(0)

    def _remember_search(self, name: str, tag: str, country: str) -> None:
        """Record a search the listener actually committed to.

        Called from the commit path only. Every keystroke through the Tag combo
        or the Country choice fires a search of its own, and remembering those
        would fill the list with the half-formed queries somebody passed
        through on the way to the one they meant.
        """
        query = SearchQuery(name=name, tag=tag, country=country)
        if query.is_empty:
            return
        updated = search_history.remember(self._recent_searches, query)
        if updated == self._recent_searches:
            return
        self._recent_searches = updated
        self._fill_recent_searches()
        # Re-filling the dropdown clears the text on wxMSW, so put back what the
        # listener typed -- a search box that empties itself the moment you press
        # Search is indistinguishable from one that lost the query.
        if self._name_ctrl.GetValue() != name:
            self._name_ctrl.SetValue(name)
        if self._on_recent_searches_changed is not None:
            self._on_recent_searches_changed(updated)
