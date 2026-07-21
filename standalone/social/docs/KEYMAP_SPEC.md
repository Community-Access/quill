# QUILL Social — Keyboard Map Specification
**The Interface of Intent**

This document defines the global keyboard shortcuts for QUILL Social. The goal is to provide a "magic" experience where the user can navigate, interact, and compose with zero friction and total spatial awareness.

## Design Principles
- **Consistent**: Similar actions use similar keys across all networks (Mastodon, Bluesky, GitHub).
- **A11y-First**: Every shortcut triggers a clear, concise aural confirmation or state announcement.
- **Remappable**: While these are the defaults, every key is configurable via the Command Center.
- **Low Cognitive Load**: High-frequency actions are mapped to keys that minimize hand movement.

---

## 1. Spatial Awareness & System Control
These commands provide the "Where Am I" and "How do I" context.

| Shortcut | Action | Purpose | A11y Announcement / Feedback |
| :--- | :--- | :--- | :--- |
| `Ctrl+Shift+I` | **Where Am I** | Total spatial snapshot | "Workspace: [Name], Account: [User], Network: [Net], Item [X] of [Y], [Field Name]." |
| `Ctrl+Shift+C` | **Command Center** | Search for any action by name | "Command Center open. Type command name or synonym." |
| `F6` | **Next Pane** | Cycle forward through major UI regions | "[Pane Name] focus." |
| `Shift+F6` | **Prev Pane** | Cycle backward through major UI regions | "[Pane Name] focus." |
| `Applications Key` / `Shift+F10` | **Context Menu** | A la-carte actions for current item | "Context menu open. [Number] actions available." |

---

## 2. High-Velocity Navigation
"Magic jumps" to move between feeds, threads, and profiles.

| Shortcut | Action | Purpose | A11y Announcement / Feedback |
| :--- | :--- | :--- | :--- |
| `Ctrl+G` | **Jump to Conversation** | Pivot from a post to its full relational thread | "Opening conversation thread. [X] replies found." |
| `Ctrl+1` $\rightarrow$ `Ctrl+9` | **Primary Destination** | Jump to a pinned feed or workspace | "[Destination Name] active." |
| `Alt+Win+Left` | **Previous Timeline** | Sequential switch to previous feed | "Timeline: [Name]." |
| `Alt+Win+Right` | **Next Timeline** | Sequential switch to next feed | "Timeline: [Name]." |
| `Ctrl+Up` | **Prev Thread Item** | Move to previous post in current conversation | "Post [N] of [Total]." |
| `Ctrl+Down` | **Next Thread Item** | Move to next post in current conversation | "Post [N] of [Total]." |
| `Ctrl+Left` | **Prev Author Post** | Jump to previous post by same author in feed | "Previous post by [Author]." |
| `Ctrl+Right` | **Next Author Post** | Jump to next post by same author in feed | "Next post by [Author]." |

---

## 3. Fluid Social Interaction
Perform core social actions without leaving the reading flow.

| Shortcut | Action | Purpose | A11y Announcement / Feedback |
| :--- | :--- | :--- | :--- |
| `Ctrl+F` | **Like / Favourite** | Mark item as liked | *[Liking Sound]* "Liked." |
| `Alt+B` | **Bookmark** | Save item to the Social Library | *[Saving Sound]* "Bookmarked." |
| `Ctrl+R` | **Rapid Reply** | Jump to composer with context loaded | "Composer open. Replying to [Author]." |
| `Ctrl+Shift+R` | **Repost / Boost** | Share content to followers | *[Boost Sound]* "Reposted." |
| `Ctrl+Q` | **Quote Post** | Share content with a custom comment | "Composer open. Quoting [Author]." |
| `Ctrl+Enter` | **Primary Media Play** | Play audio/video associated with post | *[Playback Start Sound]* "Playing [Media Type]." |

---

## 4. The Power Composer
Tools for professional publishing and long-form content.

| Shortcut | Action | Purpose | A11y Announcement / Feedback |
| :--- | :--- | :--- | :--- |
| `Ctrl+N` | **New Compose** | Open a fresh composer | "New post. Account: [Active Account]." |
| `Enter` | **Activate / Open** | Primary action (Open details/Send) | (Action specific) |
| `Escape` | **Back / Close** | Return to previous logical context | "Returning to [Previous View]." |
| `F7` | **Spell Check** | Trigger accessibility/grammar check | "Spell check running..." |
| `Ctrl+S` | **Save Draft** | Manually commit current draft to DB | "Draft saved." |

---

## 5. GitHub Social Surfaces
Treating developer tools as social experiences.

| Shortcut | Action | Purpose | A11y Announcement / Feedback |
| :--- | :--- | :--- | :--- |
| `Ctrl+G` | **Jump to Discussion** | (Contextual) Jump to full GitHub forum thread | "Opening GitHub Discussion. [X] participants." |
| `Ctrl+R` | **In-Line Comment** | (Contextual) Reply to a specific GitHub comment | "Replying to comment [N] by [Author]." |
| `Alt+B` | **Save to Project** | (Contextual) Save GitHub item to a local folder | "Saved to folder [Folder Name]." |

---

**Philosophy Note:** When a shortcut is triggered, the audio feedback should be immediate. For "High-Velocity" actions (Like, Bookmark, Repost), a short **Earcon (Soundpack)** is preferred over a full spoken sentence to maintain the user's momentum.
