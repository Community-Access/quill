# QUILL Social — User Guide
**Every conversation within reach.**

QUILL Social is not just a social media client; it is a professional social operating environment. Designed from the ground up for screen-reader users and those who value a calm, organized, and powerful workspace, QUILL Social brings Mastodon, Bluesky, and GitHub together into a single, accessibility-first experience.

---

## 1. Getting Started

### The Accessibility-First Experience
QUILL Social is built for the blind and low-vision community. It prioritizes keyboard navigation, semantic structure, and clear textual state over visual cues.
- **Screen Reader Support**: Fully optimized for JAWS, NVDA, and Narrator.
- **Textual State**: No critical information is conveyed by color or icons alone.
- **Focus Management**: Focus is stable and predictable; it never "disappears" or jumps unexpectedly.

### Account Management
Connect to multiple identities across different networks:
- **Supported Networks**: Mastodon (federated), Bluesky (AT Protocol), and GitHub.
- **Secure Storage**: Credentials are stored in the Windows Credential Manager (keyring). The application database stores only references, ensuring your tokens never sit in plain text.
- **Multi-Account Workspaces**: Group accounts into Workspaces (e.g., "Personal", "Professional", "Project") to keep your digital identities separate and organized.

---

## 2. The Social Reader

### Timelines and Unified Views
Navigate your social world without switching apps:
- **Unified Home**: A single, accessible stream of content from all your connected accounts.
- **Network-Specific Views**: Access Home, Local, Federated, and Hashtag timelines for Mastodon, or Custom Feeds and Starter Packs for Bluesky.
- **Unified Attention**: One place for all Mentions, Replies, and Notifications across all networks.
- **Customizable Rows**: Configure exactly which fields are spoken or displayed (e.g., Author, Network, Visibility, Engagement) and save these profiles.

### The "Catch-Up" Experience
Manage social overload with precision:
- **Position Recovery**: The app remembers exactly where you left off in every feed.
- **Catch-Up Mode**: Review unread content chronologically, grouped by person or conversation, with optional AI summaries to get the gist before diving in.
- **Gap Detection**: The system detects if posts were missed during a session and offers to load the missing range.

### Conversations and Threads
- **Thread Navigation**: Move through complex conversations with a clear sense of hierarchy and thread position.
- **Conversation Tools**: Save entire threads to your library, export them as Markdown, or turn a conversation into a GitHub issue.

---

## 3. The Social Composer

### Expressive Composition
Write with power and precision:
- **Intelligent Thread Splitting**: Write long-form content in one go. The "Intelligent Splitter" automatically breaks text into valid network segments, respecting paragraph boundaries and avoiding the breaking of links or mentions.
- **Cross-Network Variants**: Write a post once and create tailored versions for Mastodon and Bluesky, adjusting hashtags, mentions, and media for each network.
- **Native Composer Features**: Support for content warnings, visibility settings (Public, Limited, Private), polls, and thread gates.
- **Accessibility Check**: Use the built-in check to ensure your post has alt text and a clear structure before publishing.

### Drafts and Preservation
- **Auto-Save**: Frequent local saves ensure you never lose a thought, even during a crash or network failure.
- **Version History**: Track changes to your drafts and restore previous versions.

---

## 4. The Publishing Studio

### Buffer-Class Scheduling
Move from "posting" to "publishing" with a professional studio:
- **Queues and Calendars**: Organize content into queues and view your upcoming posts in an accessible agenda or calendar.
- **Campaigns**: Group posts into themed campaigns with specific goals, hashtags, and media sets.
- **Scheduling Tiers**:
    - **Native**: Use the server's own scheduling (where available).
    - **Local**: QUILL Social publishes the post for you while the app is running.
    - **Cloud**: (Optional) Reliable offline delivery and recurring post management.
- **Optimal-Time Suggestions**: Receive data-driven suggestions on the best time to post for maximum engagement.

### Approval Workflows
For professional and team use:
- **Approval States**: Move content from `Idea` -> `Draft` -> `Awaiting Approval` -> `Scheduled`.
- **Role-Based Access**: Define who can contribute, review, and publish.

---

## 5. The Social Library & Organization

### A Place for Everything
Stop relying on network bookmarks and start building a personal knowledge base:
- **Manual Folders**: Organize posts, threads, profiles, and GitHub issues into nested folders.
- **Smart Folders**: Create automatic collections based on rules (e.g., "All posts with audio," "Unreplied mentions," or "AI-classified as Research").
- **Private Notes**: Attach personal, private annotations to any profile or post. These are local-only and never posted to the network.
- **Saved Replies & Templates**: Store frequently used responses and templates with support for variables and network-specific signatures.

---

## 6. Media and The QUILL Ecosystem

### Integrated Media Player
- **First-Class Playback**: Powered by libmpv for high-performance audio and video.
- **Accessible Transcripts**: Read supplied transcripts or generate private ones. Jump playback directly to a specific line of text.
- **Time-Point Beacons**: Mark exact moments in an audio clip or video and save them as "Beacons" for instant retrieval.

### The QUILL Bridge
QUILL Social is a hub for the wider QUILL ecosystem:
- **Send-to-QUILL**: Move a social thread directly into a QUILL document for deeper research.
- **Radio & Cast**: Share episodes from QUILL Cast or add streams to QUILL Radio.
- **Audio Studio**: Open social media clips in QUILL Audio Studio for professional trimming and normalization.

---

## 7. AI Assistance

### A Helper, Not a Replacement
AI is optional, modular, and always under your control:
- **Understanding**: Summarize long threads, explain jargon, translate text, or describe images.
- **Writing**: Rewrite drafts for clarity, shorten content to fit limits, or generate network-specific variants.
- **Accessibility Assistant**: Automatically detect missing alt text or ambiguous links and suggest improvements.
- **Safety Assistant**: Detect accidental public disclosures or warn you if you are about to post from the wrong account.

---

## 8. GitHub as a Social Surface

Stop treating GitHub as a separate "work" tool and start experiencing it as part of your social flow. QUILL Social treats GitHub repositories as living communities.

### Socialized Issues & Discussions
- **Discussion Forums as Feeds**: Browse GitHub Discussions just like a social timeline. Follow the conversation flow, jump between participants, and stay updated on community sentiment.
- **In-Line Social Replies**: Reply to a GitHub discussion or an issue directly from your social view. No need to jump to a browser or a heavy IDE—just use the composer and send your response.
- **Issue-to-Social Flow**: 
    - Browse an issue's comments as a chronological thread.
    - Reply to a specific comment in a "social-style" interaction.
    - Pivot from a community discussion to a formal issue in a single stroke.
- **Unified Attention**: GitHub mentions, assigned items, and review requests are woven into your Unified Notifications, treating your project contributions with the same immediacy as a social mention.

### The "Developer's Social" Workflow
- **Release Campaigns**: Turn a GitHub release into a social campaign. Automatically generate announcement threads across Mastodon and Bluesky based on the release notes.
- **Feedback Loop**: Save social feedback into a project folder and "promote" it to a GitHub issue draft, preserving the original social context and attribution.

---

## 9. Safety, Privacy, and Moderation

### The Safety Center
A unified hub for maintaining your digital boundaries:
- **Global Moderation**: Manage mutes, blocks, and domain filters across all networks in one place.
- **Local Filters**: Create powerful local rules to hide, warn, or collapse content based on text, regex, or AI classification.
- **Privacy Boundaries**: Clear, announced distinctions between Public, Limited, and Private content.

---

## 10. The "Accessible OS" Interface

### Command Center and Navigation
Operate the app at the speed of thought:
- **Command Center**: `Ctrl+Shift+C` to search for any command or action by name.
- **"Where Am I"**: `Ctrl+Shift+I` for a comprehensive announcement of your current workspace, account, network, and position.
- **Remappable Keys**: Every single action has a keyboard shortcut, all of which can be customized to fit your workflow.
- **Soundpacks**: Optional audio cues for different events and accounts to provide non-visual awareness.

### Help and Documentation
Everything below is installed alongside QUILL Social, so it works with no internet connection. All three open in your browser, where your screen reader already gives you heading, link, and find-in-page navigation.
- **Help > User Guide**: this document.
- **Help > Keyboard Reference**: the full keymap specification, every action and its default shortcut.
- **Help > Product Requirements**: what QUILL Social is meant to be, for the curious.
- **Help > Keyboard Guide (shortcuts)** (`F1`): the quick in-app list of the shortcuts currently in effect, including any you have remapped. This is the one that reflects *your* keymap rather than the shipped defaults.

---

**QUILL Social — Every conversation within reach.**
