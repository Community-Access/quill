"""Social <-> GitHub bridge (PRD 24.3, 24.4).

Turns saved social conversations into GitHub issue drafts, and turns GitHub
activity (releases, merged pull requests, discussions) back into social
material. Pure and wx-free: it produces drafts and payloads the UI reviews and
the user confirms; it never talks to GitHub itself (that is the adapter's job).

Two privacy-critical rules from the PRD are enforced here:

- Social-to-GitHub always carries source attribution and a link, and EXCLUDES
  private local notes (PRD 24.3 steps 4 and 5). Private notes must never leak
  into a public issue.
- The AI-structuring step is a *flag only* (PRD 24.3 step 6): this module marks
  that structuring was requested and never submits anything to an AI provider.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# The GitHub dataclasses are a typing convenience; importing them keeps the
# bridge honest about the shapes it consumes.
from quill_social.adapters.github import GitHubDiscussion, GitHubPullRequest, GitHubRelease
from quill_social.model import Note, SocialItem
from quill_social.services.thread_splitter import ThreadSplit, split_thread


@dataclass
class IssueDraft:
    """A GitHub issue prepared locally for review before creation (PRD 24.3)."""

    repo: str = ""
    title: str = ""
    body: str = ""
    labels: list[str] = field(default_factory=list)
    template: str = ""
    source_item_id: str = ""
    source_url: str = ""
    ai_structure_requested: bool = False  # flag only; no AI call happens here

    def to_dict(self) -> dict:
        return {
            "repo": self.repo,
            "title": self.title,
            "body": self.body,
            "labels": list(self.labels),
            "template": self.template,
            "source_item_id": self.source_item_id,
            "source_url": self.source_url,
            "ai_structure_requested": self.ai_structure_requested,
        }

    @classmethod
    def from_dict(cls, d: dict) -> IssueDraft:
        return cls(
            repo=d.get("repo", ""),
            title=d.get("title", ""),
            body=d.get("body", ""),
            labels=list(d.get("labels", [])),
            template=d.get("template", ""),
            source_item_id=d.get("source_item_id", ""),
            source_url=d.get("source_url", ""),
            ai_structure_requested=bool(d.get("ai_structure_requested", False)),
        )


def _as_items(item_or_thread: SocialItem | list[SocialItem]) -> list[SocialItem]:
    if isinstance(item_or_thread, SocialItem):
        return [item_or_thread]
    return list(item_or_thread)


def _title_from(text: str, *, limit: int = 72) -> str:
    """First line/sentence of ``text``, trimmed to a reasonable issue title."""
    line = (text or "").strip().splitlines()[0] if text.strip() else ""
    if len(line) > limit:
        line = line[: limit - 1].rstrip() + "…"
    return line or "Social feedback"


def social_to_issue_draft(
    item_or_thread: SocialItem | list[SocialItem],
    repo: str,
    template: str = "",
    *,
    notes: list[Note] | None = None,
    exclude_private_notes: bool = True,
    ai_structure: bool = False,
) -> IssueDraft:
    """Build a GitHub issue draft from a saved social item or thread (PRD 24.3).

    Includes source attribution and a link (step 4). Private local notes are
    excluded when ``exclude_private_notes`` is set (step 5): a note is private
    when ``Note.confidential`` is true. ``ai_structure`` only records that
    structuring was requested (step 6) -- no AI provider is contacted here.
    """
    items = _as_items(item_or_thread)
    if not items:
        return IssueDraft(repo=repo, template=template, ai_structure_requested=ai_structure)

    first = items[0]
    parts: list[str] = []
    for it in items:
        attribution = it.author_display or it.author_handle or "unknown author"
        handle = f" ({it.author_handle})" if it.author_handle else ""
        link = it.uri or ""
        block = it.text.strip()
        cite = f"Source: {attribution}{handle}"
        if link:
            cite += f" -- {link}"
        parts.append(f"> {block}\n\n{cite}" if block else cite)

    # Notes: keep non-confidential context; drop private notes entirely when the
    # exclude flag is set so they can never leak into a public issue (PRD 24.3).
    kept_notes: list[Note] = []
    for note in notes or []:
        if exclude_private_notes and note.confidential:
            continue
        if note.text.strip():
            kept_notes.append(note)
    if kept_notes:
        rendered = "\n".join(f"- {n.text.strip()}" for n in kept_notes)
        parts.append(f"Context notes:\n{rendered}")

    body = "\n\n---\n\n".join(parts)
    return IssueDraft(
        repo=repo,
        title=_title_from(first.text),
        body=body,
        labels=[],
        template=template,
        source_item_id=first.item_id,
        source_url=first.uri,
        ai_structure_requested=ai_structure,
    )


def release_to_campaign(release: GitHubRelease) -> dict:
    """Turn a release into a campaign-shaped payload (PRD 24.4).

    Returns a plain dict shaped like ``quill_social.model.Campaign`` fields plus
    the originating release, so the UI can seed a campaign the user then edits.
    """
    name = release.title or release.tag or "Release"
    tag = release.tag or release.title
    hashtags = ["release"]
    if tag:
        hashtags.append(tag.lstrip("v").replace(".", ""))
    return {
        "name": f"{name} launch",
        "description": release.body,
        "hashtags": hashtags,
        "source_url": release.url,
        "source_release_id": release.id,
        "repo": release.repo,
        "tag": tag,
    }


def merged_prs_to_whats_new(
    prs: list[GitHubPullRequest],
    char_limit: int,
    *,
    heading: str = "What's New",
    numbering: bool = True,
) -> ThreadSplit:
    """Summarize merged pull requests into a "What's New" thread (PRD 24.4).

    Only merged PRs contribute. The teaser is built as one body and split into
    an ordered, limit-respecting thread via ``services.thread_splitter`` so the
    same boundary rules (no broken links/mentions) apply.
    """
    merged = [p for p in prs if p.merged]
    lines = [f"{heading}:", ""]
    for pr in merged:
        lines.append(f"- {pr.title} (#{pr.number})")
    if not merged:
        lines.append("- no user-facing changes this cycle")
    body = "\n".join(lines)
    return split_thread(body, char_limit, numbering=numbering)


def discussion_announcement(discussion: GitHubDiscussion, *, cta: str = "") -> str:
    """Compose a social announcement for a discussion (PRD 24.4).

    Returns post text with the discussion title, an optional call to action, and
    the link; the caller decides which accounts publish it.
    """
    call = cta or "Join the discussion"
    link = discussion.url or ""
    text = f"{call}: {discussion.title}".strip()
    if link:
        text = f"{text}\n\n{link}"
    return text
