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
- **A timeline that stays still**: When posts arrive in the background, or the scheduler publishes, the list changes around you without moving you. You stay on the same post, on the same line, and it is not marked read again. New posts wait: you hear "3 new posts. Press F5 to show them." once, and they join the list when you press **F5** (**Tools > Refresh**), which then says how many arrived. If the post you were on has gone, you hear "The post by ... is no longer in the list." and you are on the post that took its place. A post you have just read stays where it is in the Unread view until you leave it.

### The "Catch-Up" Experience
Manage social overload with precision:
- **Position Recovery**: The app remembers exactly where you left off in every feed.
- **Catch-Up Mode**: Review unread content chronologically, grouped by person or conversation, with optional AI summaries to get the gist before diving in.
- **Gap Detection**: The system detects if posts were missed during a session and offers to load the missing range.

### Conversations and Threads
- **Thread Navigation**: Move through complex conversations with a clear sense of hierarchy and thread position. A refresh in the background never takes you out of a conversation you have open.
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
- **Send-to-QUILL**: Move a social thread directly into a QUILL document for deeper research. The thread is saved as a Markdown file in the exports folder of QUILL Social's data folder; once it is written, QUILL Social says "Saved the thread for QUILL in exports." and shows the file's full path. If it cannot be written, it says so and shows nothing.
- **Radio & Cast**: Share episodes from QUILL Cast or add streams to QUILL Radio.
- **Audio Studio**: Open social media clips in QUILL Audio Studio for professional trimming and normalization.

---

### Scribe for Documents: a linked document, made accessible
Posts often link a PDF, a document or a picture of text. Scribe for Documents, a service from Pneuma Solutions, can turn it into an accessible document: Word, accessible HTML, tagged PDF, EPUB, DAISY with audio, MP3 audio or braille, with the headings, reading order and tables rebuilt and the pictures described. This part of QUILL Social is Powered by Scribe for Documents. Nothing leaves your computer until you press **Send and Convert** in the Convert dialog, which first says exactly what will be fetched and where it goes.

- **Item > Convert Linked Document with Scribe for Documents...** (Alt+Shift+F6): the focused post's linked documents, from its text, its own link and its pictures and other media.
- **Tools > Scribe Conversions** (Alt+Shift+F7): every Scribe job on this computer, from every QUILL app.
- **Tools > My Scribe Documents** (Alt+Shift+F8): your documents on Scribe, and the Trash.
- **Tools > Scribe Status** (Alt+Shift+F9) and **Tools > Repeat Last Scribe Message** (Alt+Shift+F10).
- **Tools > Scribe for Documents Options...** (Alt+Shift+F11): sign in or out, your account, the download folder and how much is spoken.

The first time you use a Scribe command, your browser opens at Scribe's
own sign-in page, and you hear "Your browser is open at Scribe for
Documents. Sign in there, then come back to QUILL Social." Sign in, come back, and
press **Continue**. One sign-in covers every QUILL app on this computer, and
QUILL Social never sees your Scribe password. You use your own Scribe account and
pay Scribe for your own pages; a new account has 100 free pages.

Step by step:

1. Focus the post in the post list.
2. Choose **Item > Convert Linked Document with Scribe for Documents...**, or press Alt+Shift+F6.
3. QUILL Social looks for links that point straight at a file Scribe takes: a PDF,
   a Word or other text document, a spreadsheet, a presentation, a picture,
   an EPUB or a MOBI.
   - **None:** you hear "This post links no documents Scribe for Documents can convert." Nothing opens.
   - **One:** the Convert dialog opens straight away for that link.
   - **Several:** a list opens first, **Choose a Linked Document**. You hear,
     for example, "Choose a Linked Document dialog, Linked documents in
     this post, 3, Transcript (example.org), 1 of 3". Each row starts with the
     link's own words, then where it goes; a link with no words of its own
     reads as the file and its site, such as "Notes.pdf on example.org".
     Arrow to the one you want and press Enter.
4. The Convert with Scribe for Documents dialog opens on **What will be
   sent**, which names the link: "The file at https://example.org/Notes.pdf
   will be fetched by Scribe for Documents...". Scribe fetches the file
   itself, so its size and pages are known only once Scribe reads it.
5. Press Tab, check the formats you want back (Word is the usual one), and
   press **Send and Convert**. You hear each stage once.
6. When it is done you hear one sentence, for example: "Scribe for
   Documents made Notes.docx in Documents\Scribe for Documents\Notes. Open
   it from Scribe Conversions."
7. Open Scribe Conversions (Alt+Shift+F7), choose the row and press Enter.
   Word, HTML and EPUB open in QUILL, or in QUILL Lite when QUILL is not
   installed; MP3 and DAISY open in Quill Media Player. **Next Steps...**
   lists the same choices by name, such as **Open in QUILL (Word)**.

QUILL Social never opens the result by itself. Another app coming to the front
would cut the result sentence off, so you open it when you are ready.

Only direct links to files work. A link to a web page, or to a file behind a
sign-in, is not offered: Scribe for Documents does not take web pages.

Scribe's sentences and new-post announcements go through the same announcer, so one waits for the other rather than cutting it off.

Inside the Scribe windows:

| Where | Key | What it does |
|---|---|---|
| Scribe Conversions list | Enter | Open Result |
| Scribe Conversions list | Delete | Remove from List |
| Scribe Conversions and My Scribe Documents lists | Applications key or Shift+F10 | Every command for the row |
| Scribe Conversions | Escape | Closes it, back to where you were |
| My Scribe Documents list | Enter | Download Formats |
| Convert dialog, What will be sent | Enter | Send and Convert |
| Convert dialog, while a voice sample plays | Escape | Stops the sample |
| Any Scribe window | F1 | What the window is for, then the control you are on |

These keys are the same in Quill Media Player, Quill Converter, QUILL
Studio, QUILL Cast, Quill Beacon and QUILL Social. QUILL and QUILL Lite are
different: there Alt+Shift with F6 to F11 are editing commands, and the
Scribe commands have no key until you give them one in the Keymap Editor.

When something goes wrong:

When something goes wrong, you hear one sentence that names Scribe for
Documents and the file, and usually Scribe's own reason. QUILL Social adds a code,
such as QUILL-SCRIBE-PAGES, which you never hear. It is in the Details box in
Scribe Conversions and in **Copy Details**, for when you ask for help.

| Code | What you hear | What to do |
|---|---|---|
| QUILL-SCRIBE-SIGNIN | "Your Scribe for Documents sign-in has ended. Conversions are paused until you sign in again." | In Scribe Conversions, press **Sign In...** on the job. It carries on when you are signed in. |
| QUILL-SCRIBE-SIGNIN-LOCAL | That no port could be opened to receive the sign-in, or that the browser could not be opened | Allow QUILL apps in your security software, then **Try Again**. Or press **Copy Sign-in Link** and paste it into any browser. |
| QUILL-SCRIBE-PAGES | "Scribe for Documents could not convert Notes.pdf:", Scribe's message, then "Use Buy Pages in Scribe Conversions, then Retry." | Press **Buy Pages**, buy pages in your browser, then **Retry**. Without pages, Scribe still makes a free preview of the first two pages. |
| QUILL-SCRIBE-PASSWORD | "Notes.pdf needs its password. Open Scribe Conversions to enter it." | Press **Enter Password...** on the job. After three wrong tries, press **Retry** for three more. |
| QUILL-SCRIBE-BUSY | "Scribe for Documents asked QUILL Social to slow down; trying again in a minute." | Nothing. QUILL Social waits a minute and carries on. |
| QUILL-SCRIBE-NOTDOC | "Scribe for Documents cannot convert Data.xml: it takes PDF, pictures, Office, OpenDocument, text, EPUB and MOBI files, not web pages." | Save the file as Word or PDF and send that. |
| QUILL-SCRIBE-TOOBIG | "Video.pdf is 612 MB. Scribe for Documents takes files up to 500 MB." | Split the document, or save a copy with smaller pictures. Nothing was sent. |
| QUILL-SCRIBE-GONE | Scribe's reason; the row says "No longer in your Scribe account" | Press **Remove from List**, and convert the file again if you need it. |
| QUILL-SCRIBE-OFFLINE | "Reconnecting to Scribe for Documents; your conversion is still running there." | Nothing, usually. QUILL Social reconnects by itself without uploading again, and says nothing when it is back. |
| QUILL-SCRIBE-SAVE | That the download folder is not writable or could not be made | Free some space or choose another **Download folder** in Options, then **Retry**. No more pages are used. |
| QUILL-SCRIBE-OFF | "Scribe for Documents is disabled in Safe Mode." | Start QUILL Social normally. Nothing was queued. |
| QUILL-SCRIBE-FAILED | "Scribe for Documents could not convert Notes.pdf:" and Scribe's reason | Press **Retry**. If it fails again, press **Copy Details** and send that to support. |

Questions people ask:

**Does QUILL Social send anything without asking?** No. Every upload needs **Send
and Convert** in the Convert dialog, which first says exactly what will be
sent and where. There is no "don't ask again".

**Will a second format cost more pages?** No. Pages are charged once for each
document. Use **Download Formats...** in My Scribe Documents for another
format of a document already in your account.

**Can I use QUILL Social and QUILL at the same time?** Yes. Every QUILL app on this
computer shares one sign-in, one queue and one Options window. Only one
sends at a time, and only the app running the job speaks; the others show
the same rows quietly. If another QUILL app is running the job, the result
sentence ends "Open it from Scribe Conversions."

**Can I stop a conversion?** Scribe cannot be stopped once it starts.
**Cancel Waiting** stops QUILL Social waiting and downloading, and says so.

**What happens if I close QUILL Social during a conversion?** Nothing is lost. The
next QUILL app to start downloads what was made and tells you once.

**Where is the privacy information?** In Scribe for Documents Options, under
**Powered by Scribe for Documents**, and in the QUILL user guide's Scribe for
Documents chapter: where documents go, how long they are kept, and how to
delete them.

F1 in the Scribe windows:

| Window | What F1 tells you |
|---|---|
| Convert with Scribe for Documents | What is sent and where, the formats, the settings, and the pages it uses |
| Scribe Conversions | The jobs, their stages, and every command on a job |
| My Scribe Documents | Your documents and the Trash, and what each button does |
| Scribe for Documents Options | The family's one set of Scribe choices |
| Sign In to Scribe for Documents | Signing in on Scribe's own page, in your browser |
| Password for Notes.pdf | A PDF's password, used once and never saved |
| Choose a Linked Document | The links here that point straight at a file Scribe can take |


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
- **Command Center** (**Ctrl+Shift+C**): search for a command by name. Type part of it, such as `reply`, and press Enter to run it.
- **Where Am I** (**Ctrl+Shift+I**): one announcement of your workspace, account, network, and which post of how many you are on.
- **Keys you can change**: every command's key can be changed by editing `keymap.json` in QUILL Social's data folder while the app is closed. **Help > Keyboard Reference** explains how, with an example. The menus show the key in effect, so after a change the menu, the key and the F1 list all agree.
- **Soundpacks**: Optional audio cues for different events and accounts to provide non-visual awareness.

### Where every command lives
Every command is on a menu, so you can always find it by walking the menu bar with Alt and the arrow keys, and since 2026-10-17 every command also has a key, read beside its name. Every command has its own letter in its menu too: press Alt, the menu's letter, then the command's letter, one key at a time. For example, Alt+S, then D opens Studio > Drafts..., and Alt+I, then K bookmarks the focused post. The menus, left to right:

- **File** (Alt+F): **File > Add Account...** (Ctrl+Shift+A), **File > Preferences...** (Ctrl+Comma) for announcement verbosity, high contrast and what each row speaks, and **File > Exit** (Alt+F4).
- **Compose** (Alt+C): **Compose > New Post** (Ctrl+N), **Compose > Reply** (Ctrl+R) and **Compose > Quote** (Ctrl+Q). Reply and Quote work on the focused post.
- **Item** (Alt+I), for the focused post: **Item > Boost / Repost** (Ctrl+Shift+R), **Item > Favourite** (Ctrl+F), **Item > Bookmark** (Alt+B), **Item > Flag for follow-up** (Ctrl+Shift+G), **Item > Open conversation** (Ctrl+G), **Item > Open links** (Ctrl+O), **Item > Mark read** (Ctrl+K), **Item > Next unread** (Alt+.), **Item > Previous unread** (Alt+,), **Item > Accessibility check** (F7), **Item > Send to QUILL** (Ctrl+Shift+Q), **Item > Play media** (Ctrl+Enter) and **Item > Convert Linked Document with Scribe for Documents...** (Alt+Shift+F6).
- **Feeds** (Alt+D): **Feeds > Add Feed...** (Ctrl+Shift+N), **Feeds > New Folder...** (Ctrl+Alt+F), **Feeds > Feed settings...** (Ctrl+Shift+P), **Feeds > Mark all read** (Ctrl+Shift+K) and **Feeds > Undo mark all read** (Ctrl+Z), then **Feeds > New smart folder...** (Ctrl+Shift+M), **Feeds > Edit smart folder...** (Ctrl+Alt+M), **Feeds > Delete smart folder** (Ctrl+Shift+Delete), **Feeds > Import OPML...** (Ctrl+I), **Feeds > Export OPML...** (Ctrl+E) and **Feeds > Unsubscribe from feed** (Ctrl+Alt+U). Delete smart folder and Unsubscribe ask before they remove anything.
- **Item** (Alt+I), for the focused post: **Item > Boost / Repost** (Ctrl+Shift+R), **Item > Favourite** (Ctrl+F), **Item > Bookmark** (Alt+B), **Item > Flag for follow-up** (Ctrl+Shift+G), **Item > Open conversation** (Ctrl+G), **Item > Open links** (Ctrl+O), **Item > Mark read** (Ctrl+K), **Item > Accessibility check** (F7), **Item > Send to QUILL** (Ctrl+Shift+Q), **Item > Play media** (Ctrl+Enter) and **Item > Convert Linked Document with Scribe for Documents...** (Alt+Shift+F6).
- **Feeds** (Alt+D): **Feeds > Add Feed...** (Ctrl+Shift+N), **Feeds > New Folder...** (Ctrl+Alt+F), **Feeds > Feed settings...** (Ctrl+Shift+P), **Feeds > Mark all read** (Ctrl+Shift+K) and **Feeds > Undo mark all read** (Ctrl+Z), then **Feeds > New smart folder...** (Ctrl+Shift+M), **Feeds > Edit smart folder...** (Ctrl+Alt+M), **Feeds > Delete smart folder** (Ctrl+Shift+Delete), **Feeds > Import OPML...** (Ctrl+I), **Feeds > Export OPML...** (Ctrl+E) and **Feeds > Unsubscribe from feed** (Ctrl+Alt+U). Delete smart folder and Unsubscribe ask before they remove anything. Export OPML says how many feeds went to which file in which folder once the file is written, for example "Exported 12 feeds to quill-social-feeds.opml in Downloads."
- **Listen** (Alt+L): **Listen > Listen to this view** (Ctrl+Shift+L) reads the unread articles in the current view aloud, one after another; **Listen > Play / Pause** (Ctrl+Shift+Space), **Listen > Next article** (Ctrl+Shift+Period), **Listen > Previous article** (Ctrl+Shift+Comma) and **Listen > Stop listening** (Ctrl+Shift+S) control it.
- **Studio** (Alt+S): **Studio > Drafts...** (Ctrl+Shift+D), **Studio > Agenda / Calendar...** (Ctrl+Shift+Y), **Studio > Queue schedule...** (Ctrl+Shift+U) and **Studio > Approvals...** (Ctrl+Shift+W).
- **Tools** (Alt+T): **Tools > Command Center** (Ctrl+Shift+C), **Tools > Where Am I** (Ctrl+Shift+I), **Tools > Search** (Ctrl+L), **Tools > Find Text...** (Ctrl+Shift+F), **Tools > Find Next** (F3), **Tools > Find Previous** (Shift+F3), **Tools > Refresh** (F5), **Tools > Catch Up** (Ctrl+Shift+H), **Tools > Insights / Analytics** (Ctrl+Alt+I), **Tools > Safety Center** (Ctrl+Alt+T), **Tools > Notification policies** (Ctrl+Alt+P), **Tools > Plugins** (Ctrl+Alt+G), **Tools > Outbox** (Ctrl+Shift+B), **Tools > Summarize this feed (AI)** (Ctrl+Alt+R), then the Scribe for Documents rows: **Tools > Scribe Conversions** (Alt+Shift+F7), **Tools > My Scribe Documents** (Alt+Shift+F8), **Tools > Scribe Status** (Alt+Shift+F9), **Tools > Repeat Last Scribe Message** (Alt+Shift+F10) and **Tools > Scribe for Documents Options...** (Alt+Shift+F11).
- **Help** (Alt+H): the documents described below, and **Help > About** (Alt+F1).

Example: to plan the week's posts, press Ctrl+Shift+Y for Studio > Agenda / Calendar... and read what is scheduled, then Ctrl+Shift+D for your drafts. Without chords, the same two are Alt+S, then A, and Alt+S, then D. Limits: the keys work in the main window, not inside the composer or another dialog, which have their own buttons and access keys. Rarely used commands have longer keys on purpose. On keyboard layouts where the right Alt key types accented letters, a Ctrl+Alt key may run its command instead of typing the letter while the search box has focus; the menu always works.

**Finding text in a list.** **Tools > Find Text...** (Ctrl+Shift+F) asks for a word or phrase and a direction (Forward or Backward), then moves to the first row of the current list that contains it and tells you where it is, such as "3 of 20". **Tools > Find Next** (F3) and **Tools > Find Previous** (Shift+F3) repeat the search; if you have not searched yet, they open Find Text first. Example: in Unified Home, press Ctrl+Shift+F, type `release`, and press Enter to land on the first post that mentions a release; press F3 for the next. Find searches the rows of the list you are looking at, in any kind of view, and wraps around at the end. It does not search other views; for that, use **Tools > Search** (Ctrl+L). Find Text was on Ctrl+F until 2026-10-17, but Ctrl+F is Favourite, which always answered first.

### Help and Documentation
Everything below is installed alongside QUILL Social, so it works with no internet connection. All four open in your browser, where your screen reader already gives you heading, link, and find-in-page navigation.
- **Help > User Guide** (Ctrl+F1): this document.
- **Help > Keyboard Reference** (Ctrl+Shift+F1): every key QUILL Social ships with, grouped by task, with the menu each command lives on and how to change a key.
- **Help > Product Requirements** (Alt+Shift+F1): what QUILL Social is meant to be, for the curious.
- **Help > What's New** (Ctrl+Alt+F1): the changelog, newest changes first.
- **Help > Keyboard Guide (shortcuts)** (`F1`): the quick in-app list of the shortcuts currently in effect, including any you have remapped. This is the one that reflects *your* keymap rather than the shipped defaults.

---

**QUILL Social — Every conversation within reach.**
