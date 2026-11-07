"""Local preview record for GitHub-generated release notes."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class GitHubReleaseNotesDraft:
    """Generated Markdown plus the exact user-selected range that produced it."""

    target_tag: str
    previous_tag: str
    target_commitish: str
    name: str
    body: str

    @property
    def range_text(self) -> str:
        return f"{self.previous_tag} → {self.target_tag}" if self.previous_tag else self.target_tag


__all__ = ["GitHubReleaseNotesDraft"]
