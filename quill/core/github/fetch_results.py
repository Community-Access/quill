"""Completeness metadata for bounded GitHub collection reads."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class GitHubFetchResult[ItemT]:
    """Loaded rows plus an explicit signal when a collection was incomplete."""

    items: tuple[ItemT, ...]
    complete: bool = True
    truncated: bool = False
    warning: str = ""


__all__ = ["GitHubFetchResult"]
