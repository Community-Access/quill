"""Search Everything in the WordPress Workbench: one phrase, every connected site.

A mixin on :class:`quill.ui.wordpress_workbench_window.WordPressWorkbenchProvider`:
the Search node's rows, read from each site's own ``wp/v2/search`` route (at
most three pages a site), each row keeping the site it came from. A site that
fails says so in its own row; the others still answer. Off the UI thread.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from quill.core.wordpress.api import WordPressApiError
from quill.core.wordpress.workbench_rows import WbRow, fact_rows
from quill.core.workbench.filters import Query

__all__ = ["WorkbenchSearchCommands"]


class WorkbenchSearchCommands:
    """The Search node: words searched on every connected site at once."""

    _profiles: dict[str, Any]
    ctx: Callable[[str], Any]

    def _search_all_sites(self, query: Query) -> list[WbRow]:
        """Search each connected site's REST endpoint and retain source-site context."""
        terms = list(query.words)
        unsupported = []
        for condition in query.conditions:
            if condition.attribute in ("search", "words") and condition.operator.value == "is":
                terms.append(condition.value)
            else:
                unsupported.append(condition.attribute)
        if unsupported:
            return fact_rows(
                "",
                [
                    (
                        "Search",
                        "Across-site search accepts words only. Remove the other filter rows.",
                    )
                ],
            )
        search = " ".join(part.strip() for part in terms if part.strip())
        if not search:
            return fact_rows(
                "", [("Search", "Type words in the Filter box to search every connected site.")]
            )
        if not self._profiles:
            return fact_rows(
                "", [("Search", "Connect a site first, then search all connected sites.")]
            )

        rows: list[WbRow] = []
        total_matches = 0
        for name in self._profiles:
            api = self.ctx(name).api
            try:
                first = api.request(
                    "GET",
                    "wp/v2/search",
                    params={"search": search, "per_page": 100, "page": 1},
                )
            except WordPressApiError as exc:
                message = exc.plain or "The site did not return search results."
                rows.append(
                    WbRow(
                        "problem",
                        name,
                        f"search-error:{name}",
                        {"test": "Search", "status": "Unavailable", "says": message},
                        f"Search on {name} failed: {message}",
                        raw={"search": search},
                    )
                )
                continue

            results = list(first.payload) if isinstance(first.payload, list) else []
            total = first.total
            page_count = max(1, (total + 99) // 100) if total is not None else 1
            page_error = ""
            for page in range(2, min(page_count, 3) + 1):
                try:
                    response = api.request(
                        "GET",
                        "wp/v2/search",
                        params={"search": search, "per_page": 100, "page": page},
                    )
                except WordPressApiError as exc:
                    page_error = exc.plain or "The site stopped returning search results."
                    break
                if isinstance(response.payload, list):
                    results.extend(response.payload)

            for result in results:
                if not isinstance(result, dict):
                    continue
                title_value = result.get("title")
                if isinstance(title_value, dict):
                    title = str(title_value.get("rendered") or title_value.get("raw") or "")
                else:
                    title = str(title_value or "")
                title = title or "(untitled)"
                subtype = str(result.get("subtype") or result.get("type") or "content")
                address = str(result.get("url") or "")
                identifier = str(result.get("id") or address or len(rows) + 1)
                rows.append(
                    WbRow(
                        "search_result",
                        name,
                        f"{name}:{identifier}",
                        {
                            "title": title,
                            "type": subtype.replace("_", " ").title(),
                            "site": name,
                            "address": address,
                        },
                        f"{title}, {subtype.replace('_', ' ')} on {name}. "
                        + (f"{address}." if address else "No site address was returned."),
                        link=address,
                        subkind=subtype,
                        raw=dict(result),
                    )
                )
            total_matches += total if total is not None else len(results)
            if page_error:
                rows.append(
                    WbRow(
                        "problem",
                        name,
                        f"search-page-error:{name}",
                        {"test": "Search", "status": "Partial", "says": page_error},
                        f"Search on {name} stopped early: {page_error}",
                        raw={"search": search},
                    )
                )
            elif total is not None and total > len(results):
                rows.extend(
                    fact_rows(
                        name,
                        [
                            (
                                "More matches",
                                f"{total - len(results)} more search results; "
                                "refine the phrase to narrow them.",
                            )
                        ],
                    )
                )
            elif total is None and len(results) >= 100:
                rows.extend(
                    fact_rows(
                        name,
                        [
                            (
                                "More matches",
                                "Showing the first 100 results; the site did not report "
                                "whether more are available.",
                            )
                        ],
                    )
                )
        if total_matches == 0 and not rows:
            return fact_rows("", [("Search", f"No matches for {search} on the connected sites.")])
        return rows
