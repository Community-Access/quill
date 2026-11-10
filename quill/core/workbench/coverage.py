"""Which of a service's operations the Workbench has a home for, and which not yet.

"Absolutely everything" has to be counted to be believed (GitHub PRD
section 19). A provider lists the service's operations once as
:class:`CoverageRow`: built (with the node or command that does it),
planned (with where it will go), or left to the service's own site because
no API exists (with why). The gate built on this fails on any operation
with no row, and the generated reference prints the planned rows as
"coming later". Pure data; GitHub's rows come from its API description,
WordPress's from each site's REST index.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from enum import StrEnum

from quill.core.workbench import WorkbenchSpecError

__all__ = ["CoverageRow", "CoverageStatus", "CoverageTable"]


class CoverageStatus(StrEnum):
    BUILT = "built"
    PLANNED = "planned"
    SITE_ONLY = "site_only"


@dataclass(frozen=True)
class CoverageRow:
    """One operation, or one feature, and its home.

    *home* is the node key or command id that does it (built) or will
    (planned); for ``SITE_ONLY`` it is the reason the service offers no API.
    *reference* is an outside id when there is one (a roadmap wave).
    """

    operation: str
    status: CoverageStatus
    home: str
    reference: str = ""
    feature: str = ""


class CoverageTable:
    def __init__(self, rows: Sequence[CoverageRow]) -> None:
        seen: set[str] = set()
        for row in rows:
            if row.operation in seen:
                raise WorkbenchSpecError(f"Operation {row.operation!r} is listed twice.")
            if not row.home:
                raise WorkbenchSpecError(f"Operation {row.operation!r} has no home or reason.")
            seen.add(row.operation)
        self._rows = tuple(rows)

    @property
    def rows(self) -> tuple[CoverageRow, ...]:
        return self._rows

    def with_status(self, status: CoverageStatus) -> tuple[CoverageRow, ...]:
        return tuple(row for row in self._rows if row.status is status)

    def missing(self, operations: Iterable[str]) -> tuple[str, ...]:
        """Operations the service has that no row accounts for."""
        listed = {row.operation for row in self._rows}
        return tuple(op for op in operations if op not in listed)

    def summary(self) -> str:
        """Counts by status, for the scorecard: 12 built, 30 planned, 2 on the site only."""
        counts = Counter(row.status for row in self._rows)
        return (
            f"{counts[CoverageStatus.BUILT]} built, {counts[CoverageStatus.PLANNED]} planned, "
            f"{counts[CoverageStatus.SITE_ONLY]} on the site only"
        )
