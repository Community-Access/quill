# Introducing QUILL 0.5.0 Beta

## A screen-reader-first writing environment built for real work

QUILL 0.5.0 Beta is now available, and it represents a major step forward in accessible writing, editing, reviewing, and document-centered productivity on Windows.

QUILL stands for **Quality, Usable, Inclusive, Lightweight, and Literate**.

It is built for people who live in text: blind writers, screen-reader users, keyboard users, students, researchers, accessibility professionals, developers, and anyone who wants to focus on their words instead of fighting their editor.

QUILL is not a traditional editor with accessibility added at the end. QUILL begins with accessibility as a design requirement, a development standard, and a promise to the community.

## Why QUILL matters

Most writing tools ask blind and keyboard-only users to adapt to the software.

QUILL is different.

QUILL is designed around the way people actually work with screen readers, structured documents, long-form writing, keyboard navigation, document review, automation, and assistive technology. It aims to be calm, predictable, powerful, and respectful of the user’s time and attention.

This beta is already capable enough for serious daily work, while still being honest about its beta status. Some areas will continue to grow, but the foundation is here: a complete writing environment shaped by accessibility from the first line of code.

## Download QUILL 0.5.0 Beta

QUILL 0.5.0 Beta is available now for Windows.

- [Download the QUILL 0.5.0 Installer (Windows)](https://github.com/Community-Access/quill/releases/download/v0.5.0/Quill-Setup-0.5.0.exe) — Full installer, approximately 70 MB. Includes embedded Python runtime and all dependencies. No separate Python installation required.
- [View the full release on GitHub](https://github.com/Community-Access/quill/releases/tag/v0.5.0) — Release notes, source code, and all release assets.

The installer requires Windows 10 or later, 64-bit. Run the installer and follow the prompts. QUILL will be available in your Start menu when complete.

## What is new in QUILL 0.5.0 Beta

QUILL 0.5.0 Beta brings together a broad set of features into one accessible writing environment.

### A complete multi-document workspace

QUILL includes a full editing shell with tabbed documents, recent files, save and save-all workflows, backup recovery, page setup, printing, URL opening with safety checks, session restore patterns, and workspace snapshots.

The workspace is designed to support quick notes, daily writing, long-form projects, structured markup, technical authoring, research, document review, and revision-heavy editing.

### A familiar and discoverable menu system

The menu bar follows a familiar Windows and Office-style structure: File, Edit, View, Insert, Format, Navigate, Search, Tools, Window, and Help.

If QUILL can do something, the goal is for that feature to have a clear and discoverable home.

Menus are not decorative. They are part of the accessibility model. Commands are organized, discoverable, and explainable so users do not have to memorize hidden behavior to be productive.

### A powerful command palette

QUILL includes a command palette for quickly finding and running commands, opening settings, accessing help topics, and discovering features.

The command palette is designed for speed, but also for learning. It helps users find what QUILL can do without forcing them to remember where every command lives.

### An interactive status bar

The status bar in QUILL is an action hub, not just a line of information.

It can show document status, word count, selection details, file information, spelling state, autosave state, background tasks, notifications, read-aloud status, copy tray information, and the detected screen reader.

Many status bar items can also be activated directly, giving users fast access to related tools and settings without disrupting their workflow.

### Customization for different users and skill levels

QUILL is not one-size-fits-all.

Users can choose feature profiles such as Essential, Writer, Developer and Power Text, Accessibility Professional, and Full QUILL. These profiles help shape the editor around the user’s needs.

Someone who wants a clean writing experience can keep QUILL simple. Someone who wants automation, scripting, advanced navigation, AI, remote files, and extension support can turn those capabilities on.

Customization also includes keyboard management, menu customization, status bar layout control, feature toggles, and profile-aware behavior throughout the application.

## Designed for screen-reader productivity

Accessibility in QUILL is not limited to whether a screen reader can technically read the interface. QUILL is built to support productive, efficient, real-world screen-reader use.

### Predictable focus and announcements

QUILL is designed to reduce noise, avoid duplicate announcements, expose meaningful control names and roles, and provide clear feedback when something changes.

The goal is not simply to make the interface speak. The goal is to make it understandable.

### Selection workflows that make sense

QUILL includes structured selection tools designed for screen-reader users who need confidence when selecting text.

Users can start a selection, extend it, complete it, return to the start, reselect previous text, and expand or shrink selections by meaningful units such as word, sentence, line, paragraph, or block.

This makes selection more deliberate, reviewable, and less dependent on visual feedback.

### Long-document navigation

QUILL includes document navigation tools for headings, paragraphs, blocks, links, lists, tables, bookmarks, code blocks, search results, and other structure.

The Outline Navigator gives users a clear view of the current document’s structure, including headings, bookmarks, sticky notes, and search matches.

For long documents, this is essential. Users should be able to understand where they are, move efficiently, and review structure without rereading the entire file.

## Writing and editing tools

QUILL includes the expected everyday editing features: undo, redo, cut, copy, paste, select all, insert and overwrite modes, bookmarks, line operations, indentation, commenting, cleanup tools, and structured editing commands.

It also includes authoring support for plain text, Markdown, HTML, headings, lists, links, tables, code blocks, case conversion, tag assistance, and heading organization.

QUILL is built for practical writing, but it is also built for structured writing.

## Reusable content and writing acceleration

QUILL is designed to help users write faster, more consistently, and with less repetitive effort.

### Snippets and prediction

QUILL includes word prediction, tag assistance, and a snippet system for reusable text.

Snippets can include placeholders, choices, date and time values, cursor placement, and trigger-word expansion. Users can create, edit, import, export, and organize snippet packs for writing, coding, accessibility notes, documentation, and other recurring workflows.

This gives users a way to build their own writing toolkit directly into the editor.

### Abbreviations that turn short text into serious productivity

QUILL includes a powerful abbreviation system for users who repeatedly type the same words, phrases, signatures, code patterns, accessibility notes, document structures, or standard responses.

Abbreviations let users define short triggers that expand into longer text. This can save time, reduce typing fatigue, improve consistency, and make repetitive writing much faster.

The feature is especially useful for:

* Common phrases and boilerplate text
* Email responses and signatures
* Accessibility review notes
* Technical documentation patterns
* Markdown and HTML structures
* Frequently used names, links, and organizational language
* Personal writing shortcuts

Abbreviation expansion can be turned on or off, managed from within QUILL, and used alongside snippets, the Copy Tray, and the command palette. This gives users both quick automatic expansion and more deliberate reusable-content workflows.

For screen-reader users and keyboard-first writers, abbreviations are more than a convenience. They are a speed, consistency, and energy-saving tool that helps QUILL adapt to the way each person writes.

## Search, replace, and review

QUILL includes simple and advanced search workflows, including find, replace, wildcard search, regular expression search, search history, and find-all reporting.

The Regular Expression Helper is designed to make advanced search more approachable, with presets, plain-language explanations, sample text preview, and copy-ready patterns.

QUILL also includes compare tools for reviewing a document against another file or against clipboard content. Difference review is designed to be keyboard-friendly, screen-reader-friendly, and practical for editing and quality assurance.

## Reading, preview, and document review

QUILL includes in-app preview, side-by-side preview, and focused preview workflows using an accessible preview surface.

Read Aloud is integrated into the editor so users can review content through spoken playback without leaving their writing environment.

QUILL also supports EPUB navigation and rendering, plus an in-editor thesaurus when thesaurus data is available.

## AI assistance that keeps the user in control

AI in QUILL is optional.

If AI is turned off, AI features are hidden or disabled. If AI is turned on, QUILL supports local and cloud-based providers, including local model workflows, Ollama, Ollama Cloud, OpenAI, Claude, OpenRouter, Google Gemini, and custom OpenAI-compatible endpoints.

### Ask Quill

Ask Quill is the conversational AI surface inside the editor.

Users can ask for help writing, editing, summarizing, restructuring, or working with selected text. When an AI operation would change the document, QUILL uses a review-first model. The proposed change is shown to the user and must be approved before it is applied.

QUILL’s AI design is based on trust:

* No silent document changes
* No hidden automation
* No surprise network behavior
* Clear provider and model information
* User approval before edits are applied

AI should support the writer, not take control away from the writer.

## Tools for capturing, organizing, and returning to work

QUILL includes several features designed for real writing sessions, not just quick editing.

### Sticky Notes

Sticky Notes let users capture thoughts without losing their place. Notes are timestamped, searchable, and exportable through the Note Vault.

### Notebooks

Notebooks support long-form projects by organizing a folder of files into a single working environment with entries, headings, bookmarks, sticky notes, snapshots, and optional writing goals.

### Macros

Macros let users record repeated command sequences and replay them later. They are useful for repetitive editing, formatting, cleanup, and workflow automation.

### Workspace Snapshots

Workspace Snapshots let users save the current editing environment and return to it later. Open documents, tabs, notebooks, and session state can be restored as a working set.

For long-form writing and multi-document projects, this turns QUILL into a dependable workspace, not just a file editor.

## Remote files and document intake

QUILL can optionally support remote open and save workflows for services such as FTP, SFTP, WebDAV, S3, HTTPS, and GitHub.

These features can be enabled or disabled depending on the user’s needs, keeping the interface simpler for users who do not work with remote files.

QUILL also supports a broad range of document intake and review workflows, including plain text, Markdown, HTML, CSV and TSV, Word documents, EPUB, PowerPoint files, spreadsheets, PDF, OCR-assisted paths, and Pages extraction where available.

Pandoc integration can support broader conversion workflows when available, and document intake reporting helps users understand the confidence and quality of complex extractions.

## Quillins: extending QUILL safely

Quillins are QUILL extensions.

They can add commands, snippets, menu entries, workflow helpers, and other capabilities. Quillins follow a capability-and-consent model. Each Quillin declares what it needs, such as reading text, writing text, using the clipboard, or fetching a URL.

QUILL uses those declarations to enforce boundaries.

Some Quillins are declarative and contain no code. Others can run Python or Node.js handlers out of process behind a capability gate.

Third-party Quillins are disabled by default, and users can review, enable, disable, reload, or remove them through the Quillins Manager.

The goal is to make QUILL extensible without making it unsafe or unpredictable.

## Developer and power-user tools

For developers, accessibility professionals, and advanced users, QUILL includes an optional Developer Console for inspecting and automating the running editor.

These tools are profile-gated, so users who want a simpler writing environment do not have to see developer-focused features unless they choose to enable them.

## Reliability is a feature

QUILL is designed around a simple principle:

**Your work should never be silently lost.**

QUILL 0.5.0 Beta includes autosave, backup recovery, persistent undo, workspace snapshots, safe mode, diagnostics, and crash report bundle creation.

Crash report bundles are designed to include useful diagnostic information such as logs, redacted settings, environment information, and related technical details without including document content.

For QUILL, reliability is not just engineering infrastructure. It is part of accessibility. Users need to trust that the editor will protect their work.

## What is still beta

QUILL 0.5.0 is a beta release.

That means some workflows are more complete than others. Some integrations depend on optional local tools. Some behavior will continue to be refined based on real-world use with screen readers, different document types, and different writing workflows.

The QUILL team is especially interested in feedback on:

* Screen-reader behavior
* Navigation and document structure
* Long-form writing workflows
* Document intake and extraction quality
* AI setup and review-first editing
* Customization and feature profiles
* Quillins and extension ideas
* Anything that feels confusing, noisy, incomplete, or harder than it should be

The path to version 1.0 depends on real-world use and honest feedback.

## How to provide feedback

All feedback, bug reports, and rough-edge reports should be submitted from within QUILL by using the **Help, Report a Bug** dialog.

This is the best way to make sure the team receives the details needed to reproduce, understand, and prioritize issues.

Please use this path for bugs, accessibility issues, confusing workflows, feature requests, screen-reader behavior reports, and general feedback.

## QUILL Office Hours

QUILL Office Hours will be held on **Saturday, June 20, 2026, from 1:00 PM to 3:00 PM Eastern**.

This live Q&A session is open to new users, experienced users, accessibility advocates, developers, power users, and anyone curious about QUILL.

Office Hours will be a chance to:

* Meet the QUILL team
* See the product in action
* Ask questions
* Discuss workflows
* Share feedback
* Learn what is coming next
* Help shape the road to QUILL 1.0

[Register for QUILL Office Hours on Zoom](https://us06web.zoom.us/meeting/register/m7oKZPRKSD-0SBWsHd0YRA)

Registration is free. A confirmation with the meeting link will be sent to your email after you register.

## A community-built editor for the road ahead

QUILL 0.5.0 Beta is already a serious writing environment.

It is also a promise: that blind users, screen-reader users, keyboard users, developers, writers, students, researchers, and accessibility professionals deserve software that begins with them in mind.

QUILL is community-built and community-shaped.

The fastest way to influence QUILL 1.0 is to use QUILL 0.5.0 Beta for real work. Write with it. Review with it. Customize it. Push it. Try it in your daily workflow.

Then tell us what works, what breaks, and what needs to be better by using **Help, Report a Bug**.

QUILL is not just another editor.

It is an accessible writing environment built around the people who have too often been treated as an afterthought.

With QUILL, accessibility is not the finish line.

Accessibility is where we begin.
