"""How a Find Stations result row is labelled, filtered and described.

Split out of ``station_browser_dialog`` under GATE-11, along the seam between
*getting* results and *presenting* them. Everything here answers "what does
this row say?" -- which source it names, whether the Source facet keeps it,
what its badge is, and what the details panel reads out when the cursor lands
on it.

That seam is where per-row confidence landed (see
:mod:`quill.core.radio.station_confidence`), because a row that the listing
directory could not play has to say so in the row *and* say more in the panel,
and both of those are presentation.
"""

from __future__ import annotations

from quill.core.list_follow import change_rows
from quill.core.media.list_columns import ColumnDef
from quill.core.radio import station_confidence
from quill.core.radio.directory_search import station_source_labels
from quill.core.radio.models import RadioStation
from quill.ui.list_stay_still import NO_ANCHOR, capture_report, restore_report
from quill.ui.media.list_columns_view import columns_for, fill_row, set_row

#: The Source-facet entry meaning "do not filter". Defined here rather than in
#: the dialog because the filtering that consults it lives here now, and the
#: dialog imports it -- one definition, so the facet list and the filter can
#: never disagree about which label means "everything".
ALL_SOURCES = "All sources"

#: This list's id in Radio's column catalogue. Named here because this is where
#: the row is built, and a fill site that names its own surface is one that
#: cannot fill somebody else's columns.
SURFACE = "radio.station_results"


def station_key(station: RadioStation) -> str:
    """A result row's identity: its stream, or for a library row its own id."""
    return station.stream_url or station.station_uuid or f"{station.source}:{station.name}"


class ResultsViewMixin:
    """Row presentation for :class:`StationBrowserDialog`."""

    def _selected_key(self) -> str:
        """The identity of the row the reader is on, or "" for none."""
        index = self._results.GetFirstSelected()
        if 0 <= index < len(self._current_results):
            return station_key(self._current_results[index])
        return ""

    def _show_category_for_library_results(self) -> None:
        """Re-render after a library's rows land, without moving the reader.

        Somebody may already be arrowing the station results by the time a
        library answers, or have gone on to Favorites or TuneIn: the rows join
        the search results, and the list on screen changes only when it *is*
        the search results -- and then the reader stays on their station, on
        the same line, whatever the merge did to the order (FUX-06).
        """
        from quill.ui.radio.station_browser_dialog import _CATEGORIES, _SEARCH_RESULTS

        if self._category_list.GetSelection() != _CATEGORIES.index(_SEARCH_RESULTS):
            return
        self._results_keep = self._selected_key()
        self._show_category(_SEARCH_RESULTS)

    def _source_label(self, station: RadioStation) -> str:
        """The Source-column/facet label for *station* (Radio Browser default)."""
        return station.source or "Radio Browser"

    def _apply_source_facet(self, stations: list[RadioStation]) -> list[RadioStation]:
        """Filter *stations* by the current Source facet (All = everything)."""
        choice = self._source_facet.GetStringSelection() or ALL_SOURCES
        if choice == ALL_SOURCES:
            return stations
        # Match against every source that carried the station, not just the
        # winning label, so a station listed by more than one directory can
        # still show under each source facet (directory_search de-dups them).
        return [s for s in stations if choice in station_source_labels(s)]

    def _fill_results(self, stations: list[RadioStation], *, status: str) -> None:
        # Keep the full list so the Source facet can filter without re-searching.
        self._all_results = stations
        self._fill_status = status
        self._render_results()

    def _row_values(self, station: RadioStation) -> dict[str, str]:
        """Every cell this row could show, keyed by column id.

        Built whole rather than per shown column: the values are cheap, and a
        function that only computes what is currently visible is one that has to
        be revisited every time the catalogue grows.
        """
        # Blended non-Radio-Browser sources name themselves in the row so a
        # listener can tell where a station came from (iHeart, TuneIn, ...).
        source = self._source_label(station)
        label = station.display_name
        if source != "Radio Browser":
            label = f"{label} - via {source}"
        # A row found by a team it carries or a tag you gave it says so, since
        # its name may share no word with what was typed (station_lookup).
        if station.match_reason:
            label = f"{label} - {station.match_reason}"
        # A row that the listing directory could not play says so, last, so the
        # station's own name still leads the line a screen reader reads. Rows
        # with nothing to report are untouched -- see
        # quill.core.radio.station_confidence on why silence is the default.
        label = station_confidence.label_with_confidence(label, station)
        bitrate = f"{station.bitrate_kbps}k" if station.bitrate_kbps else ""
        return {
            "name": label,
            "country": station.country,
            "format": " ".join(part for part in (station.codec, bitrate) if part),
            "source": source,
            "language": station.language,
            "tags": ", ".join(station.tags),
            "votes": f"{station.votes:,} votes" if station.votes else "",
            "bitrate": bitrate,
        }

    def _result_columns(self) -> list[ColumnDef]:
        """The columns this list is built from, resolved once per window.

        Read at construction rather than watched: Find Stations is modal and is
        opened from the same menu bar that owns Choose Columns..., so "the next
        time this window opens" is the press after the one that saved.
        """
        columns = getattr(self, "_result_column_defs", None)
        if columns is None:
            columns = columns_for("radio", SURFACE)
            self._result_column_defs = columns
        return columns

    def _render_results(self) -> bool:
        """Fill the list; False when the station to keep is no longer shown.

        A new answer lands the reader on the first row. A re-render of the same
        answer -- a library's rows merged in, the next page, a Source filter --
        keeps them on their station by identity, on the same line of the
        screen, and selects exactly one row (FUX-06): ``_results_keep`` names
        it, and is used once.
        """
        keep = str(getattr(self, "_results_keep", "") or "")
        self._results_keep = ""
        stations = self._apply_source_facet(self._all_results)
        old_keys = [station_key(station) for station in self._current_results]
        keys = [station_key(station) for station in stations]
        self._status.SetLabel(self._fill_status)
        if keep in keys and keep in old_keys:
            # Rows change one by one around the reader's, which stays the same
            # native item: still selected, still focused, nothing to re-read.
            anchor = capture_report(self._results)
            self._change_rows(old_keys, stations, keep)
            restore_report(self._wx, self._results, anchor, keys.index(keep))
            return True
        self._current_results = stations
        columns = self._result_columns()
        self._results.DeleteAllItems()
        for row, station in enumerate(stations):
            fill_row(self._results, row, columns, self._row_values(station))
        self._play_btn.Enable(False)
        self._favorite_btn.Enable(False)
        self._details.SetValue("")
        if stations:
            restore_report(
                self._wx, self._results, NO_ANCHOR, keys.index(keep) if keep in keys else 0
            )
        return not keep or keep in keys

    def _change_rows(self, old_keys: list[str], stations: list[RadioStation], keep: str) -> None:
        """Turn the rows on screen into *stations*, touching only what changed."""
        columns = self._result_columns()
        self._current_results = stations

        def _values(new_index: int) -> dict[str, str]:
            return self._row_values(stations[new_index])

        change_rows(
            old_keys,
            [station_key(station) for station in stations],
            delete=self._results.DeleteItem,
            insert=lambda row, new: fill_row(self._results, row, columns, _values(new)),
            update=lambda row, new: set_row(self._results, row, columns, _values(new)),
            pin=keep,
        )

    def _details_for(self, station: RadioStation) -> str:
        """The details panel's text for *station*, your own tags included."""
        from quill.ui.radio.station_tags_dialog import details_for

        return details_for(self, station)

    def _edit_tags(self, station: RadioStation) -> None:
        """Edit Station Tags... from a result row, then re-read its details."""
        from quill.ui.radio.station_tags_dialog import edit_station_tags

        if edit_station_tags(self, station):
            index = self._results.GetFirstSelected()
            if 0 <= index < len(self._current_results):
                self._details.SetValue(self._details_for(self._current_results[index]))
