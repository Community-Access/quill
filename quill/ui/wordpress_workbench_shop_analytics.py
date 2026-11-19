"""Shop Analytics in the Workbench window: Date Range, Interval and the summary (complete.md 2.3).

The Workbench side of :mod:`quill.core.wordpress.workbench_shop_analytics`.
Each site keeps one :class:`~quill.core.wordpress.workbench_shop_analytics_period.Period`
for this sitting, so Revenue, Orders and the rest show the same days while
you move between them; the window's loader asks for it through
:meth:`WorkbenchShopAnalyticsCommands.analytics_params`. A report's sentence
is said once when you arrive, and again after Date Range or Interval change
it; a refresh or a filter does not repeat it (GATE-13: it is the one thing
the screen reader cannot know). Nothing here writes to the site.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from quill.core.wordpress import workbench_shop_analytics_period as wsp
from quill.core.wordpress.workbench_rows import WbRow
from quill.core.wordpress.workbench_shop_analytics import summary_of
from quill.core.wordpress.workbench_shop_analytics_places import LOADER_PREFIX, report_for

__all__ = ["WorkbenchShopAnalyticsCommands"]

_DATES = "Year, month and day, such as 2026-11-01."


class WorkbenchShopAnalyticsCommands:
    """Mixed into the provider beside the other shop commands, whose dialogs it uses."""

    say: Callable[[str], None]
    frame: Any
    site_of: Callable[[Any], str]
    _pl_ask: Callable[..., str | None]
    _pl_choose: Callable[..., int | None]

    def _analytics_periods(self) -> dict[str, wsp.Period]:
        found = self.__dict__.get("_shop_analytics_periods")
        if found is None:
            found = self.__dict__["_shop_analytics_periods"] = {}
        return found

    def analytics_period(self, site: str) -> wsp.Period:
        """The range and interval *site*'s reports show now (Last 7 Days by day at first)."""
        return self._analytics_periods().get(site, wsp.Period())

    def analytics_params(self, ref: Any, node: Any) -> dict[str, str]:
        """What the loader adds for a Shop Analytics node: the site's period, as strings."""
        if not str(getattr(node, "loader", "")).startswith(LOADER_PREFIX):
            return {}
        return self.analytics_period(self.site_of(ref)).as_params()

    # -- the summary, once on arrival ------------------------------------------------

    def say_analytics_summary(self, frame: Any) -> None:
        """After a list fills: a report just opened, or read again for a new range, is said."""
        arrival = getattr(frame, "arrival", -1)
        if arrival < 0 or arrival == self.__dict__.get("_shop_analytics_heard") or frame.loading:
            return
        said = summary_of(list(frame.rows))
        if said:
            self.__dict__["_shop_analytics_heard"] = arrival
            self.say(said)

    def _analytics_reread(self) -> None:
        frame = self.frame
        if frame is not None:
            frame.reload(arrived=True)  # the new sentence is said when the rows arrive

    # -- Date Range and Interval -----------------------------------------------------

    def _analytics_site(self, ref: Any, row: WbRow | None) -> str:
        return row.site if row is not None and row.site else self.site_of(ref)

    def do_analytics_range(self, ref: Any, row: WbRow | None) -> None:
        site = self._analytics_site(ref, row)
        if not site:
            return
        held = self.analytics_period(site)
        keys = [key for key, _label in wsp.RANGES]
        labels = [label for _key, label in wsp.RANGES]
        if held.range == "custom":
            labels[keys.index("custom")] = f"{held.label}..."
        picked = self._pl_choose(
            f"Date Range - {site}",
            "&Range:",
            labels,
            "The days every Shop Analytics report on this site covers. Each report compares "
            "them with the same number of days just before.",
            keys.index(held.range) if held.range in keys else 0,
        )
        if picked is None:
            return
        chosen = keys[picked]
        if chosen == "custom":
            period = self._custom_period(site, held)
            if period is None:
                return
        else:
            period = wsp.Period(chosen, held.interval)
        self._analytics_periods()[site] = period
        report = report_for(str(row.subkind if row is not None else ""))
        if report is not None and not report.dated:
            self.say(
                f"{report.label} is as things are now, so its list stays the same; the other "
                f"reports on {site} show {period.words(_today())}."
            )
            return
        self._analytics_reread()

    def _custom_period(self, site: str, held: wsp.Period) -> wsp.Period | None:
        today = _today()
        start, end = held.dates(today)
        days: list[Any] = []
        for prompt, value in (("&From:", start), ("&To:", end)):
            typed = self._pl_ask(f"Custom Date Range - {site}", prompt, _DATES, value.isoformat())
            if typed is None:
                return None
            day = wsp.parse_day(typed)
            if day is None:
                self.say(f"{typed} is not a date QUILL can read. {_DATES} Nothing changed.")
                return None
            days.append(day)
        first, last = min(days), max(days)
        if last > today:
            self.say(f"The range ends after today. {first.isoformat()} to {today.isoformat()} is "
                     "used instead.")  # fmt: skip
            last = max(first, today)
        return wsp.Period("custom", held.interval, first, last)

    def do_analytics_interval(self, ref: Any, row: WbRow | None) -> None:
        site = self._analytics_site(ref, row)
        if not site:
            return
        held = self.analytics_period(site)
        keys = [key for key, _label in wsp.INTERVALS]
        picked = self._pl_choose(
            f"Interval - {site}",
            "&Rows by:",
            [label for _key, label in wsp.INTERVALS],
            "Revenue, Orders and Downloads list one row per day, week or month of the range.",
            keys.index(held.interval) if held.interval in keys else 0,
        )
        if picked is None:
            return
        period = wsp.Period(held.range, keys[picked], held.start, held.end)
        self._analytics_periods()[site] = period
        report = report_for(str(row.subkind if row is not None else ""))
        if report is not None and not report.by_interval:
            self.say(
                f"{report.label} lists one row per {report.columns[0].replace('_', ' ')}, so "
                f"it stays the same; Revenue, Orders and Downloads on {site} show rows by "
                f"{keys[picked]}."
            )
            return
        self._analytics_reread()


def _today() -> Any:
    """Today as the reports count it (the core module's, which the tests replace)."""
    from quill.core.wordpress import workbench_shop_analytics as wsa

    return wsa.today()
