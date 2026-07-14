"""Web research provider seam (Companion Phase 5).

QUILL never reaches the network silently. Web search/fetch is gated by the
``WEB`` permission and audited like every other tool; this module defines the
provider contract the gateway calls and a Null default that is inert until a real
backend is wired in. The intended backend is the selected engine's native web
tool (with a configured search API as fallback); wiring one also requires a
``network_egress_audit`` entry, since that is where the actual outbound call
lives. Keeping the default Null means no egress happens by simply having the
tools present.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

__all__ = [
    "WebResult",
    "WebResearchProvider",
    "NullWebResearchProvider",
    "WebResearchUnavailable",
    "format_results",
]


class WebResearchUnavailable(RuntimeError):
    """Raised when web research is requested but no backend is configured."""


@dataclass(frozen=True, slots=True)
class WebResult:
    """One search hit: a title, its URL, and a short snippet."""

    title: str
    url: str
    snippet: str = ""


@runtime_checkable
class WebResearchProvider(Protocol):
    """A backend that can search the web and fetch a page as text."""

    def available(self) -> bool: ...
    def search(self, query: str, *, max_results: int = 5) -> list[WebResult]: ...
    def fetch(self, url: str) -> str: ...


class NullWebResearchProvider:
    """The default: web research is not configured, so every call is refused."""

    def available(self) -> bool:
        return False

    def search(self, query: str, *, max_results: int = 5) -> list[WebResult]:
        raise WebResearchUnavailable(
            "Web research is not configured. Enable a web-capable engine or a "
            "search provider in AI settings."
        )

    def fetch(self, url: str) -> str:
        raise WebResearchUnavailable(
            "Web research is not configured. Enable a web-capable engine or a "
            "search provider in AI settings."
        )


def format_results(query: str, results: list[WebResult]) -> str:
    """Render search results as a compact, screen-reader-friendly block."""
    if not results:
        return f"No web results for {query!r}."
    lines = [f"Web results for {query!r}:"]
    for i, result in enumerate(results, start=1):
        lines.append(f"{i}. {result.title} — {result.url}")
        if result.snippet:
            lines.append(f"   {result.snippet}")
    return "\n".join(lines)
