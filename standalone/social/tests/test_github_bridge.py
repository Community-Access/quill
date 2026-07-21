"""Tests for the Social <-> GitHub bridge (PRD 24.3, 24.4)."""

from quill_social.adapters.github import GitHubDiscussion, MockGitHub
from quill_social.model import Note, SocialItem
from quill_social.services.github_bridge import (
    IssueDraft,
    discussion_announcement,
    merged_prs_to_whats_new,
    release_to_campaign,
    social_to_issue_draft,
)


def _item():
    return SocialItem(
        item_id="item_1",
        author_handle="@ada@mock.social",
        author_display="Ada Lovelace",
        text="The timeline loses focus on refresh. Please fix.",
        uri="mock://post/seed-001",
    )


def test_issue_draft_preserves_attribution_and_link():
    draft = social_to_issue_draft(_item(), repo="quill/quill-social", template="bug")
    assert isinstance(draft, IssueDraft)
    assert draft.repo == "quill/quill-social"
    assert draft.template == "bug"
    assert draft.source_item_id == "item_1"
    assert draft.source_url == "mock://post/seed-001"
    assert "Ada Lovelace" in draft.body
    assert "@ada@mock.social" in draft.body
    assert "mock://post/seed-001" in draft.body


def test_issue_draft_excludes_private_notes():
    private = Note(target_type="post", target_id="item_1",
                   text="SECRET internal reasoning", confidential=True)
    public = Note(target_type="post", target_id="item_1",
                  text="reproduces on 4.3", confidential=False)
    draft = social_to_issue_draft(
        _item(), repo="o/r", notes=[private, public], exclude_private_notes=True
    )
    assert "SECRET internal reasoning" not in draft.body
    assert "reproduces on 4.3" in draft.body


def test_ai_structure_is_flag_only():
    draft = social_to_issue_draft(_item(), repo="o/r", ai_structure=True)
    assert draft.ai_structure_requested is True


def test_release_to_campaign_fields():
    release = MockGitHub().releases()[0]
    payload = release_to_campaign(release)
    assert payload["name"].startswith("QUILL Social 0.1.0")
    assert payload["tag"] == "v0.1.0"
    assert payload["source_url"] == release.url
    assert payload["source_release_id"] == release.id
    assert "release" in payload["hashtags"]
    assert release.body in payload["description"]


def test_merged_prs_to_whats_new_uses_splitter():
    prs = MockGitHub().pull_requests()
    split = merged_prs_to_whats_new(prs, char_limit=80)
    assert split.count >= 1
    joined = "\n".join(split.texts())
    # Only merged PRs (10, 11) appear; the open one (12) does not.
    assert "#10" in joined
    assert "#11" in joined
    assert "#12" not in joined
    assert "What's New" in joined
    # Every segment respects the limit.
    assert all(seg.length <= 80 for seg in split.segments)


def test_merged_prs_empty_still_produces_thread():
    split = merged_prs_to_whats_new([], char_limit=100)
    assert split.count == 1
    assert "no user-facing changes" in split.texts()[0]


def test_discussion_announcement_includes_title_and_link():
    disc = GitHubDiscussion(number=20, title="How should catch-up work?",
                            url="https://github.com/o/r/discussions/20")
    text = discussion_announcement(disc)
    assert "How should catch-up work?" in text
    assert "discussions/20" in text
