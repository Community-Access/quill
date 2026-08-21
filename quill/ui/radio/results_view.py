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

from quill.core.media.list_columns import ColumnDef
from quill.core.radio import station_confidence
from quill.core.radio.directory_search import station_source_labels
from quill.core.radio.models import RadioStation
from quill.ui.media.list_columns_view import columns_for, fill_row

#: The Source-facet entry meaning "do not filter". Defined here rather than in
#: the dialog because the filtering that consults it lives here now, and the
#: dialog imports it -- one definition, so the facet list and the filter can
#: never disagree about which label means "everything".
ALL_SOURCES = "All sources"

#: This list's id in Radio's column catalogue. Named here because this is where
#: the row is built, and a fill site that names its own surface is one that
#: cannot fill somebody else's columns.
SURFACE = "radio.station_results"


class ResultsViewMixin:
    """Row presentation for :class:`StationBrowserDialog`."""

    def _source_label(self, station: RadioStation) -> str:
        """The Source-column/facet label for *station* (Radio Browser default)."""
        return station.source or "Radio Browser"

    def _apply_source_facet(self, stations: list[RadioStation]) -> list[RadioStation]:
        """Filter *stations* by the current Source facet (All = everything)."""
        choice = self._source_facet.GetStringSelection() or ALL_SOURCES
        if choice == ALL_SOURCES:
            return stations
        # Match against every source that carried the station, not just the
        # winning label, so a SomaFM channel RadioBrowser also lists still
        # shows under the SomaFM facet (directory_search de-dups the two).
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

    def _render_results(self) -> None:
        stations = self._apply_source_facet(self._all_results)
        self._current_results = stations
        columns = self._result_columns()
        self._results.DeleteAllItems()
        for row, station in enumerate(stations):
            fill_row(self._results, row, columns, self._row_values(station))
        self._status.SetLabel(self._fill_status)
        self._play_btn.Enable(False)
        self._favorite_btn.Enable(False)
        self._details.SetValue("")
        if stations:
            self._results.Select(0)
            self._results.Focus(0)
