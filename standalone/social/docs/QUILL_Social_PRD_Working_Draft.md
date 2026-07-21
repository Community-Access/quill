# QUILL Social
## Product Requirements Document — Current Specification

**Product family:** QuillVille / QUILL ecosystem  
**Primary platform:** Python 3.12+ with wxPython  
**Initial operating system:** Windows 11  
**Future platforms:** macOS and iOS through a shared service and data architecture  
**Document status:** Current Specification (P0 slice implemented and verified)
**Date:** July 19, 2026  
**Product owner:** Jeff Bishop / QUILL Project  

---

# 1. Executive Summary

QUILL Social is an accessibility-first social communication, reading, publishing, media, community, and collaboration workspace.

It is not intended to be merely another Mastodon or Bluesky timeline client. QUILL Social should combine the speed and predictability of the best screen-reader-oriented social clients with the organization, publishing, scheduling, media, collaboration, and optional artificial intelligence capabilities expected from a modern professional social platform.

The product should allow a person to:

- Read and participate fully on Mastodon and Bluesky.
- Manage multiple social identities without losing track of the active account or network.
- Organize posts, people, conversations, media, searches, GitHub activity, and projects into rich folders and smart collections.
- Compose short posts, long posts, threads, polls, replies, quotes, and media-rich content.
- Schedule content through queues, calendars, campaigns, recurring plans, and approval workflows similar in spirit to Buffer.
- Listen to audio and video embedded in posts through a first-class accessible player.
- Send content between QUILL Social, QUILL, QUILL Radio, QUILL Cast, QUILL Audio Studio, QuilleBeacon, and QuilleSync.
- Use AI, when desired, to summarize, explain, translate, describe, transcribe, organize, compose, shorten, expand, and improve content.
- Participate safely through strong moderation, filtering, privacy, notification, and wellbeing tools.
- Use every important feature without a mouse and without relying on visual-only state.

The primary design center is a blind keyboard and screen-reader user. However, the product must also serve low-vision users, Braille users, people with cognitive and motor disabilities, creators, nonprofit leaders, open-source maintainers, podcasters, broadcasters, and anyone who values a calm, organized, powerful social workspace.

> **North star:** QUILL Social should make complex social spaces understandable, navigable, expressive, safe, and deeply human.

---

# 2. Product Vision

QUILL Social will become the social operating environment for the QUILL ecosystem.

A user should be able to begin with a social post and move naturally into other forms of work:

- Save a post as research.
- Turn feedback into a GitHub issue.
- Turn a thread into a QUILL document.
- Turn a podcast transcript into scheduled social posts.
- Turn an audio clip into a QUILL Cast teaser.
- Add a shared radio stream to QUILL Radio.
- Bookmark an exact post, thread, podcast chapter, or audio time point through QuilleBeacon.
- Schedule a week of posts through an accessible campaign calendar.
- Ask AI to summarize a conversation, then inspect every original source.
- Prepare a long announcement in QUILL and publish it as a thread, a long-form article, or both.

The experience should feel native, fast, deliberate, and trustworthy. The user should always understand:

- Where they are.
- Which account is active.
- Which network an item came from.
- What an action will do.
- Whether content is public, limited, private, scheduled, or local.
- Whether AI is involved.
- What data will leave the device.
- What succeeded, failed, or still requires attention.

---

# 3. Product Promise

QUILL Social makes five promises.

## 3.1 Everything Has a Place

Accounts, feeds, timelines, conversations, bookmarks, favourites, media, drafts, campaigns, scheduled posts, GitHub activity, notes, and research can be organized through workspaces, folders, tags, smart rules, and saved searches.

## 3.2 Everything Can Be Reached

Every core action must be available through:

- Standard controls.
- Keyboard shortcuts.
- Menus.
- Context menus.
- A searchable command center.
- Context-sensitive help.
- Optional global commands.

## 3.3 Important State Is Never Hidden

The product must communicate account, network, privacy, content warning, moderation labels, thread position, media state, scheduling state, upload progress, and failures through accessible text and control state. Color, sound, icons, indentation, or visual location must never be the sole means of communication.

## 3.4 AI Remains an Assistant

AI can propose, summarize, describe, translate, classify, and transform. It must never silently publish, impersonate the user, hide source material, or replace human approval.

## 3.5 The QUILL Ecosystem Works as One

Content should move cleanly among QUILL products without repetitive copying, inaccessible browser workflows, or loss of context.

---

# 4. Product Influences

QUILL Social should learn from several strong products and interaction traditions without becoming a clone.

## 4.1 Leasey Social

Useful patterns include:

- Predictable list navigation.
- Field-by-field reading.
- Command search.
- “Where Am I?”
- Context-sensitive help.
- Configurable speech and sound.
- Local caching.
- Multiple accounts.
- Tight integration with writing and media tools.
- An experience intentionally designed for screen-reader users.

## 4.2 TweeseCake

Useful patterns include:

- Lightweight operation.
- Fast global commands.
- Soundpacks.
- Multi-service thinking.
- Quick access to timelines and actions.
- Optional invisible-interface workflows.

## 4.3 FastSM

Useful patterns include:

- Keyboard-first Mastodon and Bluesky access.
- wxPython implementation lessons.
- Timeline caching.
- Position restoration.
- Gap detection.
- Cross-platform ambitions.
- Media playback.
- AI image-description concepts.
- Sound-driven social workflows.

FastSM is an important design and implementation reference, but QUILL Social should not depend on it as an actively maintained foundation.

## 4.4 Mona

Useful patterns include:

- Deep customization.
- Flexible actions.
- Multi-account workflows.
- Private notes on people.
- Filtering.
- Synchronization.
- User-controlled text presentation.
- Powerful timeline and list configuration.

## 4.5 Buffer

Useful patterns include:

- Queues.
- Custom posting schedules.
- Account/channel groups.
- Drafts.
- Approvals.
- Campaign tags.
- Calendar and agenda views.
- Bulk creation.
- “Next available” scheduling.
- Prioritization.
- Sent and failed states.
- Cross-account planning.
- Reliable recovery and audit history.

## 4.6 Mastodon

Important capabilities include:

- Federation.
- Instance-aware identity.
- Home, local, federated, list, hashtag, and profile timelines.
- Public and limited visibility modes.
- Content warnings.
- Sensitive media.
- Polls.
- Filters.
- Favourites.
- Bookmarks.
- Scheduled posts.
- Conversations.
- Follow requests.
- Blocks, mutes, reports, and domain controls.
- Community moderation.

## 4.7 Bluesky

Important capabilities include:

- Portable identity.
- Decentralized protocol concepts.
- Custom feeds.
- User lists.
- Starter packs.
- Thread and reply controls.
- Stackable moderation.
- Labelers.
- Quote posts.
- Rich embeds.
- Video.
- Extensible AT Protocol records.

## 4.8 GitHub

Useful collaboration patterns include:

- Issues.
- Pull requests.
- Discussions.
- Categories.
- Labels.
- Saved replies.
- Subscriptions.
- Notifications.
- Project tracking.
- Release workflows.
- Converting conversation into accountable action.

---

# 5. Goals

## 5.1 Primary Goals

- Provide rich and durable support for Mastodon and Bluesky.
- Deliver an outstanding social experience for blind desktop users.
- Make multi-account and cross-network participation understandable.
- Provide an exceptional long-form composer and thread publisher.
- Deliver a Buffer-class accessible scheduling and publishing studio.
- Make audio and media consumption a core capability.
- Integrate deeply with the QUILL ecosystem.
- Reduce cognitive load through optional AI.
- Support individuals, creators, nonprofits, teams, and open-source communities.
- Build a capability-driven architecture that can adapt as network APIs evolve.

## 5.2 Secondary Goals

- Support macOS through the same application architecture.
- Prepare for an iOS companion or client.
- Permit custom commands, templates, filters, automations, plugins, and soundpacks.
- Provide team workspaces and approvals in later phases.
- Support additional open networks through adapters.

## 5.3 Initial Non-Goals

- Hosting a new public social network.
- Recreating every visual animation from first-party apps.
- Circumventing network restrictions or API terms.
- Automatically generating engagement or operating autonomous reply bots.
- Requiring AI for basic functionality.
- Requiring a QUILL cloud subscription for local reading and composition.
- Shipping every proposed feature in the first release.

---

# 6. Guiding Principles

## 6.1 Accessibility Before Density

A visually dense screen is not automatically efficient. Every workflow must work in a focused, sequential mode even when a user also chooses a multi-pane layout.

## 6.2 Network Fidelity Before Artificial Uniformity

Mastodon and Bluesky have different concepts. QUILL Social should create a coherent experience without pretending their privacy, moderation, identity, and publishing models are identical.

## 6.3 Capability Detection Before Assumption

The application must detect what each account and server supports. Unsupported commands should be hidden or clearly explained.

## 6.4 User Intent Before Automation

Scheduling, AI, cross-posting, thread splitting, and media conversion must assist the user’s intent. They must not infer permission to publish or share private information.

## 6.5 Textual State Before Visual State

Icons, badges, colors, indentation, and progress bars must always have accessible names, descriptions, relationships, and states.

## 6.6 Local-First and Cloud-Optional

Reading, drafting, saving, organizing, playback, and many AI workflows should work locally. Cloud services should be optional for reliable scheduling, synchronization, collaboration, and hosted long-form publishing.

## 6.7 Graceful Failure

Social APIs, servers, uploads, and network connections fail. QUILL Social must preserve work, explain exactly what happened, and provide a safe recovery path.

---

# 7. Target Users

## 7.1 Fast Social Reader

A blind screen-reader user who wants fast startup, stable focus, configurable speech, sound cues, catch-up tools, media playback, and immediate access to context.

## 7.2 Community Leader

A nonprofit or community leader managing personal and organizational accounts who needs campaigns, approvals, schedules, saved replies, analytics, and clear separation between identities.

## 7.3 Creator and Broadcaster

A podcaster, radio host, audio producer, writer, or educator who needs long-form composition, audio clips, transcripts, chapter links, reusable campaigns, and QUILL media integration.

## 7.4 Open-Source Maintainer

A developer or project manager active on GitHub, Mastodon, and Bluesky who needs issue and discussion views, release announcements, saved technical replies, and AI summaries.

## 7.5 New Social Participant

A person unfamiliar with federation, instances, custom feeds, labelers, content warnings, or thread gates who needs guided setup, plain-language explanations, safe defaults, and previews.

## 7.6 Low-Vision and Cognitive-Accessibility User

A user who benefits from larger text, reduced density, high contrast, predictable location, plain language, saved progress, and reduced notification load.

---

# 8. Product Areas

QUILL Social contains ten major areas:

1. **Social Reader**
2. **Social Composer**
3. **Publishing Studio**
4. **Social Library**
5. **Media Studio**
6. **AI Assistance Layer**
7. **Community and Collaboration Hub**
8. **Discovery and Catch-Up**
9. **Safety, Privacy, and Moderation Center**
10. **QUILL Ecosystem Bridge**

---

# 9. Workspace and Navigation Model

## 9.1 Workspaces

A workspace contains:

- Accounts.
- Account groups.
- Timelines and feeds.
- User folders.
- Smart folders.
- Saved searches.
- Drafts.
- Scheduled content.
- Campaigns.
- Media queues.
- GitHub repositories and views.
- Private notes.
- Notification policies.
- Automation rules.

Example workspaces:

- Personal.
- BITS.
- QUILL Project.
- University Accessibility.
- Podcast Production.
- Open-Source Watch.

## 9.2 Main Navigation Tree

Suggested structure:

- Home
  - Unified Home
  - Mastodon Home
  - Bluesky Home
  - Custom Feeds
- Attention
  - Mentions
  - Replies
  - Direct Messages
  - Follow Requests
  - Notifications
  - Assigned GitHub Items
- Communities
  - Mastodon Lists
  - Bluesky Lists
  - Starter Packs
  - GitHub Repositories
  - GitHub Discussions
- Discover
  - Local Timeline
  - Federated Timeline
  - Trending
  - Custom Feeds
  - Saved Searches
  - Suggested People
- Library
  - Bookmarks
  - Favourites and Likes
  - Saved Threads
  - Media
  - Private Notes
  - Archive
- Publishing
  - Ideas
  - Drafts
  - Awaiting Approval
  - Queue
  - Calendar
  - Failed
  - Sent
  - Campaigns
- Audio
  - Now Playing
  - Play Queue
  - Radio
  - Podcasts
  - Clips
  - Transcripts
- GitHub
  - Notifications
  - Issues
  - Pull Requests
  - Discussions
  - Releases
  - Saved Views
- Custom Folders

Users can hide, rename, reorder, nest, pin, or assign shortcuts to most nodes.

## 9.3 View Modes

- Standard multi-pane mode.
- Focused one-pane-at-a-time mode.
- Compact reader.
- Optional invisible interface.
- Low-vision mode.
- Braille-focused mode.

---

# 10. Core Interaction Model

## 10.1 Default Keyboard Pattern

- Up and Down: previous and next item.
- Left and Right: previous and next configured field.
- Enter: open details or activate the primary action.
- Escape: return to the previous logical context.
- Tab and Shift+Tab: move among controls.
- Applications key or Shift+F10: context menu.
- Control+N: compose.
- Control+R: reply.
- Control+Shift+R: repost or boost.
- Control+Q: quote.
- Control+F: favourite or like.
- Alt+B: bookmark.
- Control+G: open conversation.
- Control+O: open links.
- Control+Enter: play primary media when appropriate.
- Control+Shift+C: command center.
- Control+Shift+I: Where Am I.
- F6 and Shift+F6: next and previous major pane.
- Control+1 through Control+9: configurable primary destinations.

All shortcuts must be remappable.

## 10.2 Command Center

The command center must:

- Search command names and synonyms.
- Show current shortcuts.
- Include recent and favourite commands.
- Explain unavailable actions.
- Permit direct execution.
- Optionally interpret natural phrases.
- Require confirmation before publishing or destructive actions.

## 10.3 Where Am I

Where Am I should announce:

- Workspace.
- Account.
- Network.
- Folder or timeline.
- Item position.
- Unread count.
- Current field.
- Filter and sort state.
- Post type.
- Visibility.
- Media state.
- Moderation state.
- Scheduling state.
- Pending operation or error.

## 10.4 Context-Sensitive Help

Every significant control should explain:

- Purpose.
- Current state.
- Relevant shortcuts.
- Consequences.
- Network-specific behavior.
- Link to extended help.

---

# 11. Account and Identity Management

## 11.1 Supported Accounts

Initial:

- Mastodon-compatible accounts.
- Bluesky accounts.
- GitHub accounts.

Later:

- RSS and Atom as read-only social sources.
- Additional ActivityPub services.
- Additional open protocols through plugins.

## 11.2 Multiple Accounts

Users must be able to:

- Add multiple accounts.
- Assign accounts to workspaces.
- Rename accounts locally.
- Create account groups.
- Set default posting identities.
- Perform supported actions from another account.
- Configure speech, sound, filters, schedules, and signatures per account.
- Pause an account without removing it.
- Receive strong warnings before posting from an unexpected identity.

## 11.3 Identity Durability

For Bluesky, local records should use durable identity values such as DIDs rather than relying only on mutable handles.

For Mastodon, identity must include both the account name and instance domain.

## 11.4 Capability Registry

Each account should record:

- Character limit.
- Visibility modes.
- Quote support.
- Edit support.
- Scheduling support.
- Poll support.
- Media limits.
- Alt-text limits.
- Video support.
- List and feed support.
- Search support.
- Filter support.
- Moderation features.
- Rate limits.
- Server or protocol version.

The interface should adapt to this registry.

---

# 12. Timelines, Feeds, and Streams

## 12.1 Mastodon Views

- Home.
- Mentions.
- Notifications.
- Direct conversations.
- Favourites.
- Bookmarks.
- Scheduled posts.
- Local timeline.
- Federated timeline.
- Lists.
- Hashtags.
- Followed hashtags.
- User timelines.
- Pinned posts.
- Search results.
- Trends.
- Follow requests.
- Muted and blocked users.
- Domain blocks.
- Filtered content.

## 12.2 Bluesky Views

- Home.
- Notifications.
- Mentions and replies.
- Direct messages where supported.
- Author feeds.
- Custom feeds.
- Saved and pinned feeds.
- User lists.
- Moderation lists.
- Starter packs.
- Likes.
- Bookmarks where supported.
- Quotes.
- Reposts.
- Search.
- Profiles.
- Threads.
- Labeler and moderation views.
- Video and media views.

## 12.3 Unified Views

- Unified Home.
- Unified Mentions.
- Unified Notifications.
- Unified Messages.
- Unified Saved Items.
- Needs Reply.
- From People I Know.
- Unified Media.
- Unified GitHub and Social Attention.

Every unified row must expose the network and account.

## 12.4 Configurable Row Fields

- Author name.
- Full handle.
- Post text.
- Date.
- Network.
- Account.
- Visibility.
- Reply, quote, or repost state.
- Engagement.
- Media summary.
- Alt-text status.
- Content warning.
- Moderation labels.
- Language.
- Thread position.
- Read state.
- Folder and tag state.
- Private note indicator.
- Scheduling state.

Users can reorder and save field profiles.

## 12.5 Reading Position and Gap Recovery

- Save position per account and feed.
- Restore position after restart.
- Detect missing ranges.
- Offer to load gaps.
- Preserve focus during updates.
- Never jump to the top unexpectedly.
- Support mark-above-read, mark-below-read, and mark-all-read.
- Optionally synchronize reading positions.

## 12.6 Catch-Up Mode

Catch-Up Mode may provide:

- Unread totals.
- Chronological review.
- People-first grouping.
- Conversation grouping.
- Repost collapse.
- Duplicate cross-network collapse.
- Optional AI summary.
- Important-item extraction based on user rules.
- Media-only review.
- “What changed since my last visit?”
- Save and resume.

AI summaries must always lead back to original items.

---

# 13. Folders, Smart Folders, and the Social Library

## 13.1 Manual Folders

Folders may contain:

- Posts.
- Threads.
- Profiles.
- Hashtags.
- Feeds.
- Lists.
- Searches.
- GitHub issues and discussions.
- Audio and video.
- Drafts.
- Campaigns.
- QUILL documents.
- Beacon references.

Folders may be nested.

## 13.2 Smart Folders

Rules can include:

- Network.
- Account.
- Author group.
- Contains audio.
- Missing alt text.
- Has not been replied to.
- Date range.
- GitHub label.
- Engagement threshold.
- Keyword.
- Language.
- Moderation label.
- AI topic classification.

AI must never be the only reason content disappears. Model-driven results should remain inspectable.

## 13.3 Saved Item Types

The product must distinguish:

- Network bookmark.
- Network favourite or like.
- Local save.
- Local archive.
- Private note.
- Follow-up flag.
- Local pin.
- Folder membership.
- Campaign idea.
- Playback queue item.
- QuilleBeacon target.

## 13.4 Private Notes

Users may attach private notes to profiles, posts, threads, feeds, GitHub items, and campaigns.

Notes may contain:

- Free text.
- Alias.
- Relationship context.
- Follow-up date.
- Tags.
- Confidential flag.
- Beacon references.

Private notes must never be posted and must be excluded from AI unless explicitly selected.

## 13.5 Saved Replies and Templates

Templates may contain:

- Plain text.
- Markdown.
- Variables.
- Network-specific variants.
- Account signatures.
- GitHub response templates.
- Accessibility reminders.
- Campaign tags.
- Optional AI transformation instructions.

---

# 14. Post Details and Conversations

## 14.1 Details View

The details view should expose:

- Full author identity.
- Complete post text.
- Expanded URLs.
- Content warning.
- Date and timezone.
- Network and account.
- Visibility.
- Language.
- Parent and thread root.
- Quote and repost source.
- Media.
- Alt text.
- Captions and transcript.
- Poll.
- Engagement counts.
- Moderation labels.
- Editing history where available.
- Local folders, tags, and notes.
- Available actions.

## 14.2 Conversation Views

- Flat chronological list.
- Announced hierarchy.
- Focused branch.
- Root plus direct replies.
- Author-only thread.
- Summary plus originals.
- Unread replies since last visit.

Thread level and reply relationship must be spoken or available through text.

## 14.3 Conversation Tools

- Follow or mute conversation.
- Save thread.
- Export thread.
- Copy as plain text or Markdown.
- Send to QUILL.
- Create a GitHub issue or discussion.
- Create podcast or radio research.
- Summarize with AI.
- Extract decisions, questions, links, and actions.
- Filter by participant.
- Play all media.
- Add private annotations.

---

# 15. Composer

## 15.1 Native Composer

The composer should include:

- Selected accounts.
- Main editor.
- Per-network variants.
- Reply or quote context.
- Content warning.
- Visibility.
- Language.
- Media.
- Alt text and captions.
- Poll.
- Reply permissions and thread gates.
- Sensitive-content labels.
- Thread mode.
- Schedule.
- Campaign.
- Approval.
- Preview.
- Accessibility check.
- Publish, schedule, and save actions.

The active account and privacy state should be announced when focus enters the composer.

## 15.2 Draft Preservation

- Frequent local auto-save.
- Save on close, crash, logout, or token failure.
- Version history.
- Named drafts.
- Restart recovery.
- Optional encrypted synchronization.
- Local-only flag for sensitive drafts.

## 15.3 Character and Capability Feedback

Report:

- Current count per network.
- Remaining length.
- Thread segment count.
- Media limits.
- Alt-text completeness.
- Poll limits.
- Unsupported combinations.
- Scheduling eligibility.
- Estimated thread publication time.

## 15.4 Autocomplete

- Mentions.
- Hashtags.
- Custom Mastodon emoji.
- Recent contacts.
- Saved hashtag groups.
- Accessible disambiguation.
- Clear full identity.
- Link preview editing.
- Suspicious Unicode warning.

## 15.5 Language Tools

- F7 spell check.
- Personal dictionaries.
- Multiple languages.
- Ignore URLs, handles, and code.
- Dictionary and thesaurus.
- Grammar and style.
- QUILL editor handoff.

## 15.6 Cross-Network Composition

Users can:

- Write once.
- Create network-specific variants.
- Ask AI to suggest variants.
- Use different media by network.
- Change hashtags and mentions.
- Change visibility and reply controls.
- Preview every destination.
- Detect unmatched mentions.
- Detect unsupported features.
- Choose publication order.
- Decide whether one failure stops all destinations.

---

# 16. Long Posts and Threads

## 16.1 Intelligent Splitting

The splitter should:

- Respect grapheme limits.
- Prefer paragraph boundaries.
- Prefer sentence boundaries next.
- Avoid breaking links, mentions, hashtags, emoji sequences, Markdown links, and code.
- Preserve list structure where practical.
- Support numbering such as `1/5`.
- Recalculate as text changes.
- Expose every segment in an accessible list.
- Allow direct segment editing.
- Permit manual boundary locks.
- Warn when changes create additional segments.

## 16.2 Thread Publishing

Publishing should:

1. Publish the root.
2. Capture the remote identifier.
3. Publish the next segment as a reply.
4. Continue in order.
5. Record every success.
6. Pause after a dependency failure.
7. Offer retry, edit and retry, skip, or stop.
8. Preserve a repair plan.

The user must be told exactly which segments succeeded and failed.

## 16.3 Preview Modes

- Continuous text.
- Segment list.
- Spoken preview.
- Network simulation.
- Media assignment.
- Reply map.
- Schedule sequence.
- Cross-network comparison.

## 16.4 QUILL Longform

Optional QUILL Longform can:

- Publish semantic HTML from QUILL Markdown.
- Support headings, lists, tables, links, images, audio, transcripts, and chapters.
- Create a canonical accessible page.
- Post a summary and link.
- Create a teaser thread.
- Maintain revision history.
- Export to other document formats.
- Support custom domains later.

---

# 17. Polls

## 17.1 Native Polls

Where supported:

- Create polls.
- Add and reorder options.
- Single or multiple choice.
- Set expiration.
- Vote.
- Read current results.
- Receive close notifications.
- Save and export results.

## 17.2 Non-Native Polls

Where a network lacks native polls:

- Do not imitate a native poll.
- Offer a clearly labeled external accessible poll.
- Offer an informal reply-based poll.
- Explain privacy and hosting implications.

## 17.3 Accessible Poll Reading

Announce:

- Question.
- Choice count.
- Single or multiple selection.
- Time remaining.
- Whether the user voted.
- Result visibility.
- Option count and percentage where available.

---

# 18. Publishing and Scheduling Studio

## 18.1 Purpose

Scheduling must be a complete publishing environment, not merely a date field.

It should support:

- Personal and organizational queues.
- Account groups.
- Campaigns.
- Drafts.
- Approvals.
- Recurring plans.
- Bulk creation.
- Calendar and agenda views.
- Cross-network variants.
- Failure recovery.
- Analytics.
- Optional AI planning.

## 18.2 Scheduling Modes

- Publish now.
- Next available slot.
- Prioritize at top of queue.
- Specific date and time.
- Native scheduled post.
- Local scheduler.
- QUILL Cloud Scheduler.
- Save as draft.
- Request approval.
- Add to campaign.

## 18.3 Scheduler Tiers

### Native Network Scheduling

Use server scheduling when available, particularly on Mastodon.

### Local Scheduling

Publish while QUILL Social is running. Clearly state that the job cannot run if the device is asleep or the application is closed.

### QUILL Cloud Scheduling

Optional service for:

- Bluesky scheduling.
- Offline delivery.
- Cross-network campaigns.
- Threads.
- Approvals.
- Recurring content.
- Central retry management.

## 18.4 Queue Schedules

Schedules can be defined by:

- Account.
- Account group.
- Weekday.
- Time.
- Time zone.
- Content type.
- Campaign.
- Blackout window.
- Minimum spacing.
- Daily limit.
- Quiet period.

## 18.5 Accessible Calendar

Views:

- Agenda list.
- Day list.
- Week list.
- Month grid.
- Campaign timeline.
- Account queue.
- Unscheduled backlog.

The agenda list is the accessibility baseline.

Every item must expose:

- Date and time.
- Time zone.
- Account and network.
- Campaign.
- State.
- Content preview.
- Thread and media count.
- Approval state.
- Conflict.
- Failure or retry state.

## 18.6 Campaigns

A campaign includes:

- Name.
- Description.
- Goals.
- Start and end date.
- Accounts.
- Content themes.
- Approved links.
- Hashtag sets.
- Media.
- Templates.
- Team members.
- Schedule rules.
- Accessibility requirements.
- Analytics.
- Notes.

## 18.7 Ideas and Backlog

Ideas may be:

- Unassigned.
- Assigned to a campaign.
- Created from a saved post.
- Imported from QUILL.
- Created from GitHub.
- Generated by AI.
- Created from a transcript.
- Marked evergreen.
- Marked time-sensitive.

## 18.8 Approval States

- Idea.
- Draft.
- Ready for review.
- Changes requested.
- Approved.
- Queued.
- Scheduled.
- Publishing.
- Partially published.
- Published.
- Failed.
- Paused.
- Cancelled.
- Archived.

Roles may include owner, administrator, publisher, approver, contributor, and viewer.

## 18.9 Recurring Content

Support:

- Fixed content.
- Templates.
- Rotating variants.
- RSS-driven posts.
- Event-relative posts.
- Anniversary posts.

Safeguards:

- Expiration date.
- Duplicate-content warning.
- Review after a set number of cycles.
- Pause after repeated failure.
- No AI-created changing facts without current verification.

## 18.10 Bulk Creation

Import from:

- CSV.
- TSV.
- Markdown.
- JSON.
- QUILL documents.
- RSS and Atom.
- Podcast feeds.
- GitHub releases.
- Campaign packages.

Provide validation, accessible preview, dry run, duplicate detection, and time-zone confirmation.

## 18.11 Optimal-Time Suggestions

Optional suggestions may use:

- Historical engagement.
- Audience time zones.
- Content type.
- Day and time.
- Network.
- Frequency.

The system must explain the recommendation and avoid claiming certainty.

## 18.12 Failure Recovery

Delivery records must include:

- Attempt time.
- Network response.
- Rate-limit state.
- Upload state.
- Published identifier.
- Retry count.
- Next retry.
- Dependency state.
- Human-readable error.
- Technical details.

Transient errors may use exponential backoff. Validation, permission, and privacy failures require user review.

---

# 19. Media and Playback

## 19.1 Supported Media

- Direct audio.
- Direct video.
- Mastodon attachments.
- Bluesky video.
- External media.
- Podcast episodes.
- Radio streams.
- QUILL Cast content.
- QUILL Audio Studio projects.
- GitHub release assets.
- Caption and transcript files.
- Chapters and time points.

## 19.2 Playback Engine

Recommended:

- libmpv for playback.
- FFmpeg and ffprobe for inspection and permitted conversion.
- Native wxPython controls.
- Optional operating-system media-session integration.

## 19.3 Player Features

- Play and pause.
- Stop.
- Seek.
- Configurable skip.
- Speed.
- Volume.
- Mute.
- Output device.
- Loudness normalization.
- Remember position.
- Sleep timer.
- Repeat.
- A-B loop.
- Chapter navigation.
- Transcript synchronization.
- Bookmark time point.
- Playback queue.
- Background playback.
- Return to source post.
- Open in QUILL Audio Studio.
- Send to QUILL Cast.
- Add a stream to QUILL Radio.

## 19.4 Media Information

Expose:

- Media type.
- Duration.
- Title.
- Creator.
- Source.
- Alt text.
- Caption and transcript availability.
- Language.
- Sensitive-content state.
- Current position.
- Chapter.
- Processing progress.

## 19.5 Transcripts

Users may:

- Read supplied transcripts.
- Generate a private transcript.
- Correct it in QUILL.
- Search it.
- Jump playback to text.
- Create clips.
- Quote a time point.
- Export SRT, VTT, TXT, or Markdown.

---

# 20. QUILL Ecosystem Integration

## 20.1 QUILL Editor

- Send selected text to the composer.
- Open a social draft in QUILL.
- Return revisions.
- Create threads from headings.
- Run advanced writing tools.
- Publish QUILL Longform.
- Save a thread as a document.
- Export conversations to Markdown.

## 20.2 QUILL Radio

- Play shared radio streams.
- Add streams to presets.
- Share Now Playing.
- Schedule station announcements.
- Organize listener responses.
- Associate posts with shows and hosts.

## 20.3 QUILL Cast

- Share episodes.
- Share chapters and time points.
- Create release campaigns.
- Generate accessible summaries.
- Create clips and teasers.
- Track episode feedback.
- Turn conversations into future topics.
- Schedule pre-release, release-day, and follow-up posts.

## 20.4 QUILL Audio Studio

- Open attached media.
- Create a clip from a time range.
- Trim, normalize, fade, and export.
- Add transcript and chapter metadata.
- Return media to the composer.
- Preserve attribution.

## 20.5 QuilleBeacon

Beacon targets can include:

- Posts.
- Threads.
- Profiles.
- Feeds.
- GitHub issues and comments.
- Podcast chapters.
- Audio and video time points.
- QUILL headings.
- Campaign items.

## 20.6 QuilleSync

Synchronize, when selected:

- Workspaces.
- Folders.
- Smart rules.
- Local saves.
- Notes.
- Drafts.
- Templates.
- Reading positions.
- Media positions.
- Campaigns.
- Schedules.
- Settings.

Credentials require a separate encrypted strategy.

---

# 21. AI Assistance

## 21.1 Principles

AI is optional, modular, inspectable, and reversible.

AI must not:

- Publish without explicit approval.
- Impersonate the user.
- Hide source material.
- infer sensitive traits for targeting.
- send private data without authorization.
- enforce moderation solely through an opaque model.
- fabricate current facts.

## 21.2 Provider Modes

- Disabled.
- Local model.
- User-provided API key.
- Organization-managed provider.
- QUILL-brokered service.
- Per-feature provider selection.

The product should disclose:

- Data being sent.
- Provider and model.
- Context included.
- Estimated cost where available.
- Redactions.

## 21.3 Understanding Features

- Summarize posts and threads.
- Explain jargon.
- Expand abbreviations.
- Explain emoji and memes.
- Translate.
- Simplify.
- Extract questions.
- Extract decisions and actions.
- Compare threads.
- Create catch-up digests.
- Summarize linked pages.
- Describe images.
- Transcribe audio.
- Summarize transcripts.
- Detect likely duplicates.

## 21.4 Writing Features

- Rewrite for clarity.
- Shorten.
- Expand.
- Change tone.
- Create plain-language versions.
- Suggest replies.
- Turn notes into posts.
- Turn documents into threads.
- Create network variants.
- Suggest content warnings.
- Suggest alt text.
- Suggest captions.
- Suggest hashtags.
- Generate campaign variants.
- Convert GitHub releases into announcements.
- Convert podcast transcripts into teaser posts.

AI output must remain a draft until approved.

## 21.5 Accessibility Assistant

Detect:

- Missing alt text.
- Filename-like descriptions.
- Ambiguous links.
- Emoji-only meaning.
- Unexplained acronyms.
- All-caps passages.
- Audio without transcript.
- Video without captions.
- Images containing substantial text.
- Unclear polls.
- Threads that lose context after splitting.

## 21.6 Safety Assistant

Optional features:

- Warn about harmful or inflammatory wording.
- Detect accidental public disclosure.
- Warn about the wrong account.
- Offer a delay before sending.
- Summarize harassment without reading slurs aloud.
- Group abusive notifications.
- Prepare report evidence.
- Suggest mute, block, and filter actions.
- Hide engagement counts.
- Schedule quiet hours.

## 21.7 Prompt-Injection Defense

Social content is untrusted.

The AI layer must:

- Treat retrieved content as data.
- Separate system instructions from social text.
- Prevent content from invoking tools.
- Require authorization before accessing private context.
- Restrict tools by feature.
- Never expose secrets to model prompts.

---

# 22. Mastodon Requirements

Subject to server capability:

- Public and limited visibility modes.
- Replies.
- Quotes where supported.
- Boosts.
- Favourites.
- Bookmarks.
- Edit and delete.
- Content warnings.
- Sensitive media.
- Languages.
- Media descriptions.
- Polls.
- Native scheduled posts.
- Threads.
- Pinned posts.
- Lists.
- Hashtags.
- Followed hashtags.
- Local and federated timelines.
- Search.
- Trends.
- Follow requests.
- Mutes.
- Blocks.
- Domain blocks.
- Filters.
- Reports.
- Notification filtering.
- Streaming with polling fallback.
- Server capability and version diagnostics.

The application must not assume that every instance behaves like mastodon.social.

---

# 23. Bluesky Requirements

Subject to API availability:

- DID-based identity.
- Handle resolution and change tracking.
- Profile viewing and editing.
- Follow and unfollow.
- Create posts.
- Reply.
- Quote.
- Repost.
- Like.
- Delete.
- Images with alt text.
- Video.
- External cards.
- Rich embeds.
- Languages and facets.
- Threads.
- Thread gates.
- Post and quote controls.
- Labels and self-labels.
- Bookmarks where available.
- Direct messages where available.
- Home timeline.
- Author feeds.
- Custom feeds.
- Feed discovery.
- Pinned feeds.
- User lists.
- Moderation lists.
- Starter packs.
- Labelers.
- Hide, warn, and ignore policies.
- Reports.
- Strong handling of AT URIs, CIDs, DIDs, and deleted records.
- Support for multiple PDS hosts.

---

# 24. GitHub Social Surfaces
GitHub is not treated as a separate utility, but as a primary social network.

## 24.1 Views (Socialized)
- **Discussion Forums**: Presented as social feeds with thread navigation.
- **Issues as Threads**: Issues are rendered as social conversations; comments are treated as thread replies.
- **Notifications**: Unified with social mentions.
- **Releases**: Integrated into the campaign and publishing studio.
- **Repositories**: Browsed as a list of community hubs.

## 24.2 Actions (In-Line)
- **Socialized Replying**: Users can reply to a GitHub issue or discussion comment in-line, using the same composer and keyboard patterns as Mastodon/Bluesky.
- **Comment-Level Interaction**: Ability to target a specific comment for a reply within a a11y-first thread view.
- **Cross-Pollination**:
    - Create a GitHub issue from a saved social item.
    - Promote a GitHub discussion to a social announcement.
    - Link a social post to a specific GitHub comment for attribution.

## 24.3 Social-to-GitHub
Example:
...

Example:

1. Save accessibility feedback.
2. Place it in a project folder.
3. Select Create GitHub Issue Draft.
4. Include source attribution and link.
5. Exclude private notes.
6. Optionally ask AI to structure the issue.
7. Edit in QUILL.
8. Select repository and template.
9. Confirm creation.
10. Link the source and issue locally.

## 24.4 GitHub-to-Social

- Turn a release into a campaign.
- Summarize merged pull requests.
- Create a What’s New thread.
- Share issues requesting feedback.
- Announce discussions.
- Schedule countdowns.
- Attach community responses back to project folders.

---

# 25. Notifications and Attention Management

## 25.1 Notification Categories

- Mentions.
- Replies.
- Quotes.
- Reposts.
- Favourites and likes.
- Follows.
- Follow requests.
- Poll completion.
- Direct messages.
- Moderation notices.
- Scheduled delivery.
- Delivery failure.
- Approval request.
- GitHub assignment.
- GitHub mention.
- Review request.
- Discussion response.
- Release.
- Media processing completion.

## 25.2 Policies

Per account and category:

- Speak immediately.
- Show in Braille.
- Play sound.
- Show desktop notification.
- Add silently.
- Include in digest.
- Suppress during quiet hours.
- Notify only for selected people.
- Group duplicates.
- Escalate after time.
- Route to a folder.

## 25.3 Soundpacks

- Optional.
- Text-equivalent states.
- Event and account configuration.
- Volume and output control.
- Preview.
- Community-created packs.
- Never the sole indication of danger, privacy, or failure.

## 25.4 Focus Modes

- Mute selected accounts.
- Mute sounds.
- Mute speech.
- Quiet all noncritical notifications.
- Focus for a duration.
- Meeting mode.
- Reading mode.
- Audio mode.
- Scheduled quiet hours.

---

# 26. Search and Discovery

## 26.1 Search Types

- Find in current list.
- Network search.
- Local full-text search.
- Cross-network search.
- Profile search.
- Hashtag search.
- Domain search.
- Media search.
- Folder and tag search.
- GitHub search.
- Transcript search.
- Command search.

## 26.2 Search Clarity

The product must show:

- Search scope.
- Network coverage.
- Cached versus live results.
- Private-content inclusion.
- Search history settings.

## 26.3 Saved Searches

Saved searches can become:

- Navigation nodes.
- Smart folders.
- Notification sources.
- Digests.
- Campaign research feeds.
- Custom local feeds.

---

# 27. Moderation, Trust, and Safety

## 27.1 Unified Safety Center

- Muted users.
- Blocked users.
- Blocked domains.
- Mastodon filters.
- Bluesky labelers.
- Moderation lists.
- Local filters.
- Hidden posts.
- Reports.
- Notification requests.
- Temporary mutes.
- Conversation mutes.

## 27.2 Local Filters

Criteria may include:

- Text.
- Regular expressions.
- Author.
- Domain.
- Network.
- Post type.
- Media.
- Language.
- Folder.
- Moderation label.
- Time range.

Actions may include:

- Hide.
- Warn.
- Collapse.
- Remove from speech but keep visible.
- Suppress sound.
- Move to folder.
- Digest only.
- Replace slurs with a spoken placeholder.
- Require reveal.

## 27.3 Reporting

The workflow should:

- Explain what will be sent.
- Permit selecting evidence.
- Exclude private notes.
- Confirm account and network.
- Show success or failure.
- Offer local mute, block, and filter separately.

## 27.4 Anti-Abuse

- Respect rate limits.
- Prevent duplicate campaigns.
- Detect recurring loops.
- Limit automated replies.
- Require review for AI-generated outreach.
- Support cooldowns.
- Clearly label automation where required.

---

# 28. Accessibility Requirements

## 28.1 Windows Assistive Technology

Test with:

- JAWS.
- NVDA.
- Narrator.
- Refreshable Braille.
- Windows Magnifier.
- Contrast themes.
- Keyboard only.
- Speech-disabled Braille workflows.

## 28.2 Native Controls

- Prefer standard wxPython and native controls.
- Avoid canvas-only core controls.
- Avoid web views for essential workflows.
- Implement accessibility for custom controls.
- Provide useful names, roles, values, descriptions, and states.
- Avoid redundant panel announcements.
- Preserve native text selection and editing.
- Expose list position and hierarchy.

## 28.3 Focus

- Focus never disappears.
- New content does not steal focus.
- Refresh does not reset selection.
- Dialogs return focus correctly.
- Errors move to the relevant control.
- Long operations do not trap the keyboard.
- Pane changes are announced once.

## 28.4 Keyboard Completeness

Every pointer action must have a keyboard and menu equivalent. Drag and drop must have move, cut and paste, or choose-destination alternatives.

## 28.5 Speech Configuration

Users can control:

- Fields spoken.
- Field order.
- Punctuation.
- Emoji names.
- Link verbosity.
- Date style.
- Engagement counts.
- Repost context.
- Network prefix.
- Moderation labels.
- Content-warning behavior.
- Repeated-author suppression.
- Interruption policy.

## 28.6 Braille

- Concise row templates.
- Stable status cells.
- Full text in details.
- Configurable abbreviations.
- Predictable routing.
- Privacy indicators.
- Media, poll, and thread indicators.

## 28.7 Low Vision

- Strong scaling.
- Resizable text.
- Contrast-theme support.
- No color-only meaning.
- Adjustable spacing.
- Large focus indicator.
- Reduced-density mode.
- Reduced motion.
- No clipped labels.

## 28.8 Cognitive Accessibility

- Plain-language mode.
- Consistent labels.
- Preview before important actions.
- Undo where possible.
- Step-by-step complex workflows.
- Reduced-notification mode.
- Clear progress.
- Save and resume.
- No unexplained timeout.

## 28.9 Accessibility Completion Gate

A feature is not complete unless:

- It works by keyboard.
- It exposes state to JAWS, NVDA, and Narrator.
- It works at high zoom and in contrast themes.
- It has context help.
- It avoids critical focus loss.
- Errors are announced.
- It does not rely on color, sound, hover, or pointer alone.
- It has documented accessibility tests.

---

# 29. wxPython Architecture

## 29.1 Layers

```text
wxPython Presentation
        |
Commands and View Models
        |
Domain Services and Event Bus
        |
Mastodon | Bluesky | GitHub | RSS | QUILL Adapters
        |
Database | Search | Media | Scheduler | Sync | AI
        |
OS Credential Store | Optional QUILL Cloud
```

## 29.2 Suggested Modules

```text
quill_social/
  app/
  ui/
  domain/
  adapters/
    mastodon/
    bluesky/
    github/
    rss/
  services/
    cache.py
    search.py
    scheduler.py
    thread_publisher.py
    media_engine.py
    transcription.py
    ai_gateway.py
    sync.py
    notifications.py
  persistence/
  security/
  plugins/
  tests/
```

## 29.3 Asynchronous Work

- Keep wxPython UI operations on the main thread.
- Use a dedicated asyncio service thread.
- Use typed command and event queues.
- Use `wx.CallAfter` for UI updates.
- Support cancellation.
- Bound concurrency by account and service.
- Never block the UI in event handlers.
- Batch list updates.
- Preserve selection and suppress excessive screen-reader announcements.

## 29.4 Accessible Item List

The list abstraction should provide:

- Native list semantics.
- Stable IDs.
- Configurable fields.
- Left and right field reading.
- Read state.
- Hierarchy level.
- Update suppression during navigation.
- Position restore.
- Type-ahead find.
- Context actions.
- Screen-reader regression tests.

---

# 30. Data Model

Core entities:

- Workspace.
- Account.
- Social item.
- Feed.
- Folder.
- Library entry.
- Private note.
- Draft.
- Draft version.
- Publication plan.
- Delivery attempt.
- Campaign.
- Media asset.
- Moderation rule.
- Saved search.
- Reading position.
- Sync record.

Recommended persistence:

- SQLite.
- WAL mode.
- Foreign keys.
- FTS5.
- Migrations.
- Separate durable user data from disposable cache.
- Encryption for sensitive data where appropriate.

Cache eviction must never remove drafts, notes, schedules, folders, campaign records, or delivery audit history.

---

# 31. Security and Privacy

## 31.1 Credentials

- Windows Credential Manager.
- macOS Keychain.
- Database stores references, not raw tokens.
- Redact secrets from logs.
- Use least-privilege scopes.
- Support session revocation.

## 31.2 Cloud Scheduler

Preferred protections:

- Encrypted credentials.
- Per-tenant data keys.
- Managed key protection.
- Isolated credential vault.
- Short-lived access tokens.
- Rotation.
- Signed jobs.
- Tamper-evident audit logs.
- No administrator plaintext access.
- User-visible session management.
- Immediate revoke and delete.
- Local/native-only alternative.

## 31.3 Privacy Boundaries

Clearly distinguish:

- Public post.
- Followers-limited post.
- Private message.
- Local note.
- Local draft.
- Synced encrypted draft.
- Team-shared draft.
- AI-submitted content.
- Hosted long-form article.

## 31.4 Diagnostics

Diagnostic bundles should:

- Exclude credentials and private content by default.
- Show included files.
- Offer redaction.
- Include versions, capabilities, and error codes.
- Open in QUILL before sending.

---

# 32. Offline and Resilience

## 32.1 Offline Reading

Users should be able to:

- Open cached feeds.
- Search cached content.
- Read saved items.
- Read and edit drafts.
- Play cached media.
- Review schedules.
- Create outbox items.
- See that data is stale.

## 32.2 Outbox

Outbox items include:

- Account.
- Network.
- Created time.
- Privacy.
- Thread dependency.
- Media readiness.
- Send mode.
- Expiration.
- Validation status.

On reconnection:

- Revalidate capabilities.
- Warn about changed limits.
- Refresh reply references.
- Warn about expired timing.
- Preserve order.

## 32.3 Service Failure

- Circuit breakers.
- Backoff.
- Clear status.
- Continue unaffected accounts.
- Preserve local work.
- Detect moved accounts and changed handles.
- Avoid repeated login prompts during outages.

---

# 33. Analytics

## 33.1 Available Metrics

- Posts sent.
- Replies received.
- Engagement by account and network.
- Campaign results.
- Media plays where available.
- Topic performance.
- Accessibility completion.
- Response workload.
- Posting frequency.
- Schedule reliability.

## 33.2 Accessible Presentation

- Data tables first.
- Plain-language insights.
- Sortable columns.
- CSV and Markdown export.
- Optional described charts.
- Period comparison.
- Missing-data explanation.

## 33.3 Ethics

- No covert tracking pixels by default.
- No inferred sensitive traits.
- No purchased personal data.
- Separate measured data from AI interpretation.
- Permit full disablement and deletion.

---

# 34. Extensibility

Possible plugins:

- Network adapters.
- Import and export.
- AI providers.
- Media resolvers.
- Soundpacks.
- Composer tools.
- Folder rules.
- Automation actions.
- Project connectors.
- Accessibility enhancements.

Plugins should declare permissions, avoid direct credential access by default, support safe mode, isolate crashes, and provide accessible settings.

---

# 35. Performance Targets

- Cold start to cached timeline in under five seconds.
- Warm start under three seconds.
- Local navigation under 100 milliseconds.
- Composer opens in under half a second.
- Search first results in under one second for a large local cache.
- Background refresh never blocks typing.
- Memory use controlled across several accounts.
- Crash-free sessions of at least 99.5 percent before stable release.
- Zero normal-case draft loss.

Performance tests must run with screen readers active.

---

# 36. Product Priorities

## P0 — Foundational Release

- Accessible wxPython shell.
- Mastodon and Bluesky.
- Multiple accounts.
- Core timelines.
- Threads and profiles.
- Compose, reply, quote, repost, like, and bookmark.
- Media and alt text.
- Content warnings and visibility.
- Polls where native.
- Thread splitting.
- Embedded playback.
- Search.
- Local folders and saves.
- Drafts.
- Native and local scheduling.
- Command center.
- Where Am I.
- Context help.
- JAWS, NVDA, and Narrator.
- Secure credentials.

## P1 — Power Release

- QUILL Cloud Scheduler.
- Full campaigns and queues.
- Approvals.
- Cross-network variants.
- Smart folders.
- AI.
- Transcription.
- Full moderation center.
- GitHub.
- QUILL ecosystem integration.
- Analytics.
- macOS beta.

## P2 — Community and Scale

- Team workspaces.
- Shared media.
- Web or mobile approval companion.
- QUILL Longform hosting.
- Advanced automation.
- Local feed builder.
- Moderator module.
- Plugin marketplace.
- iOS.
- Additional open networks.

---

# 37. Implementation Roadmap

## Phase 0: Foundations

- Interaction prototype.
- Screen-reader testing.
- Adapter contracts.
- Threat model.
- Scheduler decision.
- Accessible control proof of concept.
- Media proof of concept.

## Phase 1: Reader

- Accounts.
- Timelines.
- Notifications.
- Caching.
- Reading positions.
- Details.
- Threads.
- Basic media.
- Commands and help.

## Phase 2: Composer

- Media.
- Alt text.
- Polls.
- Content warnings.
- Visibility.
- Thread gates.
- Thread splitting.
- Editing and deletion.
- Capability validation.

## Phase 3: Organization

- Folders.
- Smart folders.
- Saves.
- Notes.
- Templates.
- Search.
- Catch-up.

## Phase 4: Publishing Studio

- Drafts.
- Queues.
- Agenda and calendar.
- Local and native scheduling.
- Cloud scheduling.
- Campaigns.
- Approvals.
- Retries.
- Analytics foundation.

## Phase 5: Media and Ecosystem

- Full player.
- Transcripts.
- Chapters.
- QUILL Radio.
- QUILL Cast.
- QUILL Audio Studio.
- QuilleBeacon.
- QuilleSync.
- Longform.

## Phase 6: AI

- Provider gateway.
- Writing tools.
- Summaries.
- Descriptions.
- Transcription orchestration.
- Accessibility checks.
- Smart organization.
- Prompt-injection defenses.

## Phase 7: GitHub and Teams

- GitHub views.
- Issue and discussion workflows.
- Release campaigns.
- Shared workspaces.
- Approvals.

## Phase 8: Cross-Platform

- macOS stabilization.
- Mobile companion.
- iOS.
- Plugins.
- Organization deployment.

---

# 38. Testing Strategy

## 38.1 Automated

- Domain tests.
- Adapter contract tests.
- API fixture tests.
- Pagination and gap tests.
- Thread dependency tests.
- Scheduler state-machine tests.
- Database migrations.
- Encryption and redaction.
- Media metadata.
- Import validation.
- AI prompt-boundary tests.

## 38.2 Manual Accessibility

Test critical workflows with:

- JAWS.
- NVDA.
- Narrator.
- Keyboard only.
- Braille.
- High Contrast.
- 200 and 400 percent scaling.
- Magnifier.

Critical workflows include:

- Add account.
- Read a timeline.
- Read a thread.
- Reply.
- Compose with media.
- Create and vote in a poll.
- Schedule.
- Approve.
- Recover a failure.
- Block and report.
- Play media.
- Search.
- Organize folders.
- Review AI output.
- Reauthenticate.
- Restore after restart.

## 38.3 Failure Tests

- Disconnect during a thread.
- Token revoked.
- Rate limiting.
- Upload succeeds but post fails.
- Root succeeds and child fails.
- Crash during auto-save.
- Application closes before local schedule.
- Daylight-saving transition.
- Duplicate delivery request.
- Sync conflict.
- Corrupted cache.
- Missing media.
- AI timeout.
- Screen reader starts or stops while running.

---

# 39. Key Acceptance Scenarios

## 39.1 Read and Reply

A blind user can move through a timeline, hear configured fields, inspect details, open a reply composer with context, publish, and return focus to the correct item.

## 39.2 Long Thread

A long QUILL document can be transformed into valid Mastodon and Bluesky threads without splitting links or mentions. Every segment is editable and the thread publishes in order.

## 39.3 Scheduled Campaign

A campaign can schedule variants across several accounts. A failure on one destination does not duplicate successful content elsewhere and appears in an accessible Failed view.

## 39.4 Media

A user can begin playback without losing timeline focus, seek, change speed, read a transcript, create a time-point Beacon, and return to the source post.

## 39.5 Moderation Label

A Bluesky moderation label is announced with its source and current policy. The user can reveal, hide, or inspect without content being read automatically.

## 39.6 GitHub Feedback

A saved social thread can become a GitHub issue draft with attribution, private notes excluded, optional AI structuring, and explicit confirmation before creation.

## 39.7 Offline Draft

A post created offline is preserved, revalidated when connectivity returns, and not silently published after its intended time has passed.

---

# 40. Risks and Mitigation

## Scope

**Risk:** The product is extremely broad.  
**Mitigation:** Use P0, P1, and P2 priorities, vertical slices, feature flags, and adapter boundaries.

## Evolving APIs

**Risk:** Mastodon and Bluesky capabilities change.  
**Mitigation:** Capability detection, adapter isolation, contract tests, diagnostics, and feature flags.

## wxPython Accessibility

**Risk:** Some controls behave differently across screen readers.  
**Mitigation:** Early prototypes, native controls, UI Automation support, manual gates, and focused-mode fallbacks.

## Cloud Credentials

**Risk:** Reliable offline scheduling may require protected posting credentials.  
**Mitigation:** Native scheduling first, local-only mode, OAuth, isolated vaults, encryption, revocation, and independent review.

## AI Trust

**Risk:** AI may make mistakes or damage user trust.  
**Mitigation:** Optional use, source links, draft-only output, clear data disclosure, local models, and no autonomous engagement.

## Partial Thread Publication

**Risk:** A multi-segment thread may fail midway.  
**Mitigation:** Dependency tracking, delivery records, pause-on-failure, idempotency, and repair workflows.

## Notification Overload

**Risk:** Users may become overwhelmed.  
**Mitigation:** Digests, quiet hours, grouping, category policies, focus modes, and needs-attention folders.

---

# 41. Success Measures

## Accessibility

- All P0 workflows keyboard complete.
- No known critical focus-loss defect at launch.
- Strong completion rates in moderated screen-reader testing.
- Context help available throughout the composer and scheduler.
- No critical workflow requires an inaccessible browser fallback.

## Reliability

- At least 99.5 percent crash-free sessions.
- No duplicate delivery under tested retry conditions.
- No confirmed auto-saved draft loss.
- Safe recovery from partial threads.

## Usability

- A new user can add an account and publish through guided setup.
- Experienced users can reach primary actions quickly.
- Account, network, privacy, and schedule state are always available.
- Users report easier organization and catch-up than in prior tools.

## Ecosystem

- QUILL-to-Social handoff.
- Social-to-QUILL export.
- Media integration.
- Podcast chapter sharing.
- Beacon creation.
- QuilleSync support.

---

# 42. Recommended MVP

The first complete release should include:

- Windows wxPython application.
- Mastodon and Bluesky multi-account support.
- Home, mentions, notifications, threads, profiles, search, bookmarks, likes, and core moderation.
- Fast accessible list navigation with configurable fields.
- Details and conversation views.
- Native composer with media descriptions, content warnings, visibility, replies, quotes, and threads.
- Intelligent long-post splitting.
- Embedded audio and video playback.
- Local drafts and recovery.
- Folders, local saves, private notes, and local search.
- Mastodon native scheduling and local scheduling.
- Command center, Where Am I, help, remappable keys, and soundpacks.
- QUILL editor handoff.
- JAWS, NVDA, and Narrator completion gate.
- Architecture hooks for cloud scheduling, AI, GitHub, QuilleSync, and the wider media ecosystem.

The MVP must demonstrate the defining QUILL Social experience: fast access, powerful organization, expressive composition, safe thread publishing, strong media, and uncompromising accessibility.

---

# 43. Working Tagline

> **QUILL Social — Every conversation within reach.**

---

# 44. Final Product Direction

QUILL Social should be built as a **social operating environment for communication, organization, publishing, listening, creation, and community participation**.

Its defining advantage is not one isolated feature. It is the combination of:

- Deep accessibility.
- Full network participation.
- Rich organization.
- Reliable scheduling.
- Thoughtful media.
- Optional AI.
- GitHub collaboration.
- QUILL ecosystem integration.
- Clear privacy.
- Human control.

This working PRD is intentionally broad. It captures the product vision and major requirements available for review now. Later revisions can convert each major area into implementation epics, detailed user stories, API contracts, database schemas, interaction specifications, and test plans.
