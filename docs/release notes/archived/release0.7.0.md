# QUILL 0.7.0 Release Notes: Meet You Where You Are

QUILL 0.7.0 is a community release in the truest sense of the word.

Yes, it is a major step forward for screen-reader-first writing, editing, AI-assisted authorship, automation, braille, code review, and extension-powered workflows. But the bigger story is not only what changed. The bigger story is **who is helping QUILL become what it is becoming**.

Kelly Ford, Taylor Arndt, Shane Popplestone, Michael Babcock, and so many others are helping lift this project into a new place. Some people are testing. Some are contributing code. Some are filing issues, describing real-world workflows, stress-testing accessibility, challenging assumptions, improving design direction, or simply cheering the project on when the work gets hard. All of that matters. All of it counts.

Whether you are writing code, testing with JAWS or NVDA, trying a build and telling us where it hurts, sharing ideas, building Quillins, improving prompts, creating documentation, or encouraging the team from the sidelines: **thank you**.

> “I started QUILL, but the community is lifting it to levels I could never reach alone. This release is about meeting people where they are, then giving them a path to grow.”  
> — Jeff Bishop

QUILL is being built around a simple promise: a free, cross-platform editor that is usable by all assistive technology, shaped by the people who depend on it, and driven by community need rather than by assumptions about what blind and screen-reader users should want.

The core principle of this release is **Meet You Where You Are**.

That means QUILL should not force every user into the same cockpit. A first-time writer should be able to open a quiet editor and start typing. A braille professional should be able to inspect page, line, and cell position with confidence. A developer should be able to move through code by tokens. A reviewer should be able to compare files without visually scanning a diff. A writer should be able to ask AI for help without leaving the keyboard. A power user should be able to extend the editor through Quillins. Everyone should be able to start at the right level and grow from there.

This release is about speed, confidence, control, and delight. You can type a short trigger and get a full template. You can open a braille file and know exactly where you are by page, line, cell, and progress. You can compare two files without visually scanning a diff. You can move through code by tokens instead of guessing where words begin and end. You can export to Word, inspect encoding problems, generate citations, and shape the sound layer so QUILL confirms what happened without talking over your screen reader. And now you can ask the AI to rewrite a paragraph, surface a better word in context, check your grammar, translate a document, or put a question directly to your own text — all from the keyboard, without leaving the editor.

Under the surface, QUILL 0.7.0 introduces two major architectural expansions. The first is the AI writing layer: a complete, provider-agnostic toolkit covering twelve tasks from spell check to table-of-contents generation, with per-task custom instructions, prompt caching across every supported provider, and support for Anthropic Claude, OpenAI, Google Gemini, OpenRouter, and Ollama. The second is the Quillin extension platform: extensions can now own settings, contribute live preference dialogs, subscribe to document lifecycle events, contribute status-bar cells, declare dependencies, restrict network access, schedule background timers, respond to file-type opens, and initialize or shut down cleanly. Both are designed so you stay in charge and nothing runs silently without your knowledge.

Everything remains keyboard-first and screen-reader-first. Every new view is a real navigable control. Every action is announced, undoable where appropriate, and discoverable. No mouse is required. No visual-only flourish is required. No silent full-file scanning happens behind your back.

If you are upgrading from QUILL 0.5.0, read **What works differently now** near the end. It lists the few places where menus, habits, or installer choices changed.

## The community story in this release

QUILL 0.7.0 is organized around real user experiences instead of technical checklists. Each major area answers a practical question:

- **How do I start without being overwhelmed?** Meet You Where You Are profiles and the redesigned startup wizard.
- **How do I write faster without losing control?** Insert Automation, typed abbreviations, smart triggers, `.LOG` compatibility, append anchors, snippets, citations, and export tools.
- **How do I review and navigate with confidence?** Compare Mode, code-aware editing, dynamic keyboard reference, sound cues, and indentation tones.
- **How do braille professionals work inside the editor?** Braille Mode, page-aware status, BRF tools, and optional liblouis translation.
- **How do contributors extend QUILL safely?** The Quillin platform, lifecycle events, settings pages, status-bar cells, dependencies, network safeguards, and live bundled examples.
- **How does AI help without taking over?** AI Hub, provider choice, custom instructions, prompt caching, grammar, rewrite, translation, Document Q&A, AI Thesaurus, image description, and AI voice.
- **How do we make daily use smoother?** Accessibility fixes, bug-report improvements, startup reliability, macOS setup, safer guides, and update fixes.

> “A feature is not finished when it exists. It is finished when the person using it feels confident, respected, and in control.”  
> — Jeff Bishop

## What the community helped lift up in 0.7.0

This is the fast tour. The detailed notes below keep every important implementation detail, but these are the moments users will feel first.

- **Meet People Where They Are** is a complete reimagining of first-run setup. A redesigned startup wizard asks what kind of writing you do and shows a plain-English, screen-reader-readable preview of exactly what you will get. Seven intent profiles replace the old nine technical ones in the wizard. Menus, the Command Palette, and the Go to Anything dialog all reflect your chosen profile instantly - commands for features you have not enabled simply do not appear. Pressing Cancel on first run starts you in the simplest possible editor rather than leaving you with raw defaults.
- **Insert Automation** turns typed abbreviations, smart triggers, `.LOG` files, document directives, and append anchors into one safe automation system.
- **The Quillin Extension Platform** now supports settings pages, searchable preferences, tabs, document events, lifecycle events, status-bar cells, dependencies, network allowlists, command descriptions, developer logging, announcement priority, scaffolding tools, and stronger validation.
- **AI Writing Toolkit** ships a complete, keyboard-first AI writing layer: grammar check, AI Thesaurus (Ctrl+Alt+Shift+H), rewrite, summarize, expand, generate table of contents, Document Q&A, translation, and AI read-aloud. Every feature supports six providers — Anthropic Claude, OpenAI, Google Gemini, OpenRouter, Ollama, and custom endpoints. Custom per-task instructions let you shape how the AI behaves for each task. Prompt caching keeps costs down automatically: Claude marks system prompts as cacheable, OpenAI caches prefixes over 1024 tokens, and local Ollama models cache in-process. No mouse required for any of it.
- **Braille Mode** opens and edits braille text files while preserving bytes, form feeds, line endings, and layout. It adds braille-aware status, page navigation, page tools, and optional liblouis-powered translation through the QUILL Braille Pack.
- **Compare Mode** is now a first-class keyboard-driven workflow with difference navigation, speech announcements, and optional sound cues.
- **Code-aware editing** adds language profiles, token movement, manual language selection, and optional indentation tones.
- **Text encoding tools** help you find non-ASCII characters, jump to them, convert them to HTML entities, and save copies in narrower encodings without silent data loss.
- **Word and RTF export** lets you save documents as `.docx` or rich text through Pandoc, preserving real Word heading structure when the source contains structure.
- **Pandoc Import / Export and Batch Conversion (issue #262)** extends that foundation with a curated Tier-1 format list (Markdown, CommonMark, GFM, HTML, DOCX, ODT, RTF, plain text, CSV/TSV, EPUB, LaTeX, plus PDF export), a four-page batch wizard, and live progress in the Status Page.
- **Citation insertion** formats MLA 9, Chicago 17, and APA 7 citations from a simple labelled form.
- **The Snippet Gallery** (Insert > Snippet Gallery... or QUILL key, Shift+G) collects parameterized templates from all enabled Quillins into one browseable picker. Smart Insert ships three built-in entries.
- **The Vision Prompt Library**, contributed by Kelly Ford, gives Describe Image with AI twelve evaluated prompt styles and a full management dialog.
- **Math Equations**, contributed by Robert Danaraj, adds Insert → Insert Equation... (`Ctrl+Shift+E`) for LaTeX and MathML insertion, with Browser Preview and HTML export rendering via MathJax 3. Delivered as a sandboxed Quillin rather than a core patch.
- **The Dynamic Keyboard Reference** now reflects the active command registry, your current bindings, and QUILL key layers.
- **Sound notifications** and **indentation tones** add optional non-speech feedback without making existing setups noisier.
- **Major accessibility and startup fixes** make bug reporting, JAWS focus, image description, first run, the user guide, update notifications, and macOS setup more reliable.

---

## Experience 1: Meet People Where They Are

This is the heart of the release. QUILL now begins with the person, not the feature list. It asks what kind of work you do, explains what you will get in plain language, and keeps the rest out of your way until you are ready.

> “Meeting people where they are means respecting beginners, professionals, power users, and explorers equally. QUILL should feel welcoming on day one and powerful on day one hundred.”  
> — Jeff Bishop

QUILL has grown into a serious piece of software. That is a good thing. But first-time users who want a reliable plain-text editor should not have to wade through braille menus, AI panels, regex options, a developer console, and a Snippet Gallery before they type a single word.

This release changes that completely. QUILL now starts you at the right level and grows with you.

### The redesigned startup wizard

When you run QUILL for the first time, a short wizard opens. It has six pages (five if you do not enable AI writing assistance on the Extras page) and takes about two minutes.

The most important page asks one question: **What kind of writing do you do?** A list of seven starting points is shown. Arrow up and down through the list. As you move, a large read-only text area below the list updates live to tell you, in plain spoken English, exactly what you will have if you choose that option. There are no feature IDs, no jargon about flags, and no list of what you will not get. Just what you get.

After you choose, a second page offers a few optional extras: AI writing assistance, Braille Mode, and typing automation. Only the extras that are not already part of your base choice are shown. Each extra is a single checkbox. Checking one adds a sentence to the preview so you always know what you are committing to.

If you enable AI, a dedicated page collects your provider and your API key. Supported providers are Anthropic (Claude), OpenAI (GPT), Google Gemini, OpenRouter (many models), and Ollama - which runs models on your own device or connects to an Ollama-compatible cloud host. The key is stored securely in the Windows Credential Manager, not in a settings file. You can skip this and set the key up later.

The final page is a summary in plain text: your profile name, what features are active, which Quillins are enabled, your keyboard pack, and your sound setting. Read it, then press Finish.

**If you press Cancel or close the wizard on first run**, QUILL starts you in the simplest possible editor - Just a Text Editor - rather than leaving you with an overwhelming set of defaults. You can always run the wizard again from Help > Personalise QUILL.

**Alt+Shift+P** opens the quick profile switcher at any time. It shows the same list of profiles with the same rich description pane so you can switch, read what you are switching to, and confirm - all by keyboard.

### The seven starting profiles

#### Just a Text Editor

Open, type, and save. Plain text editing, auto-recovery, find and replace, and recent files. Nothing else runs. No Quillins, no AI, no automation, no abbreviation shortcuts, no snippet packs, no sticky notes. The Search menu has no cross-file options. The system tray has only Show Quill and Exit Quill. Preferences shows only the four settings areas that apply. The command palette shows only the commands you have. This is QUILL at its quietest.

#### Writer

Adds document-writing tools: RTF and Word formatting, Compare Mode for reviewing drafts, abbreviation shortcuts (type a short phrase and expand it automatically), spell check, starter snippet packs for common phrases and templates, sticky notes attached to any document position, Copy Tray with 12 clipboard slots, the Journal Stamp Quillin for date headers and post-save word count announcements, the Document Guardian Quillin that warns you before closing a short or unfinished document, and the Date and Time insert menu. The system tray gains Copy Tray and Sticky Notes. AI and braille are not enabled but can be added any time.

#### Markdown and Web Author

Adds everything in Writer plus Markdown syntax helpers, the HTML encoding and decoding tools, the Insert Character picker for Unicode symbols, Text Tools for case transforms and whitespace cleanup, Line Tools for joining and filtering, and regular expression search. The menus expand to include Format > HTML and Encoding and additional text transformation items.

#### Accessibility Professional

Adds everything in Writer plus Read Aloud at full prominence, Compare Mode, Document Trust and intake workflow, OCR image-to-text, the character inspector, and the Keymap Editor for remapping shortcuts. Designed for document reviewers, accessibility testers, and anyone who needs to read and check content carefully.

#### Braille Professional

Adds everything in Accessibility Professional plus the full Braille Mode: BRF and BRL file support, a braille status bar cell showing your position, Grade 1 and Grade 2 translation via the Braille menu, the BRF Tools Quillin for translation preferences and page handling, and Smart Insert BRF test content. The Braille menu appears in the menu bar.

#### AI-Powered Author

Adds everything in Writer plus Ask Quill (Alt+Q), AI grammar check and rewrite, AI writing prompts, AI writing skills for multi-step tasks, AI image description, the Prompt Library, and Smart Insert typing templates. The AI menu items and the Ask Quill panel are visible. You will be asked to set up a provider and API key during the wizard.

#### Developer and Power User

Turns on everything: regular expression search, macro recorder and playback, shell integration, all text and line transformation tools, Smart Insert, BRF Tools, Markdown Helpers, the Character Picker, GitHub remote file access, the Developer Console, Watch Folder automation, and all other Quillins. The full menu structure is visible.

The wizard's seven starting profiles are a curated front door, not the whole catalog. **Profiles and Features...** (Preferences) exposes the full set underneath, including this release's new **Author or Student** profile — table of contents, footnotes, and citations for papers and theses — alongside **Writer**, which keeps its name; nothing about the feature changed.

### Menus, Command Palette, Go to Anything, and the system tray all respect your profile

When you choose a profile, every surface adjusts immediately. The menus show only items that belong to features you have enabled. The Command Palette and Go to Anything (Ctrl+Shift+`, G) list only commands that are active in your current profile. The system tray right-click menu shows only the tools that apply. There is no visual noise from features you have not asked for, anywhere.

Specific examples of what changes by profile:

- **Just a Text Editor**: the Insert menu has no abbreviation shortcuts. The Search menu has no Search in Files or Replace Across Files. The system tray shows only Show Quill and Exit Quill. Preferences shows only General, Profiles, Status Bar, and Keymap. Install Starter Snippet Packs does not appear because snippets are a writer-level feature.

- **Writer and above**: abbreviation expansion and Manage Abbreviations appear in the Insert menu. The Search menu gains Search in Files and Replace Across Files. The system tray gains Copy Tray and Sticky Notes. Preferences gains AI Connection (when AI is on), Watch Folder, and any other active feature areas.

- **Developer and Power User**: Search in Files and Replace Across Files are always visible. All Insert menu tools are present. The system tray shows all available tools.

As you grow into QUILL and add features from Help > Personalise QUILL, every surface grows with you. Switching from Just a Text Editor to Writer adds abbreviation tools, snippet packs, sticky notes, the Insert menu tools, and the word-count status cell. Switching to Braille Professional adds the Braille menu. Switching to Developer adds everything else.

This is what "meeting people where they are" means in practice: start with what you need, discover the rest when you are ready, and never feel lost in a cockpit before you learn to fly.

### The Alt+Shift+P profile switcher

Press **Alt+Shift+P** at any time to open the quick profile switcher. A list of all profiles is shown on the left. As you arrow through them, a large read-only description pane on the right shows the same plain-English "what you get" text as the wizard. Choose a profile and press Enter to switch. The menus, palette, and status bar update immediately.

Custom profiles you create in Help > Preferences > Profiles and Features also appear in the switcher with the description you wrote when you created them.

### Creating a custom profile

The Profiles and Features dialog (reachable from the Help menu and from Preferences) lets you create custom profiles based on any built-in starting point. The description field is now a full multi-line editor. Write the same kind of plain-English "what you get" summary that the built-in profiles show - it will appear in the Alt+Shift+P switcher description pane so you and others can read it before switching.

### Preferences stay simple too

The Preferences hub shows only the settings areas that matter for your current profile. If AI is not enabled, the AI Connection category does not appear. If Watch Folder Automation is off, that category is gone. If GLOW is off, GLOW Accessibility is not listed. Open Preferences and you see only what applies to the way you have chosen to use QUILL.

As you enable more features - by switching profiles or turning features on individually in Profiles and Features - those areas appear in Preferences automatically. Nothing is permanently hidden; it simply waits until it is relevant.

### Fine-tuning individual features

**Help > Feature Profiles > Manage Individual Features** lets you turn individual capabilities on or off on top of your chosen profile without changing the profile itself. Enabling a feature also enables what it depends on; disabling one turns off the features that depend on it.

The dialog now has a **Show** radio button at the top with two choices: **All features** and **Disabled features only**. Arrow to "Disabled features only" and the list immediately filters down to just the features that are not currently on. You can then tab through that shorter list and turn on exactly what you want, one checkbox at a time, without scrolling past everything that is already running.

When you enable a feature in the filtered view, it disappears from the list immediately because it is no longer disabled, and focus moves to the next disabled item so you can keep going without losing your place.

Below the list, a read-only description area explains the focused feature before you touch its checkbox.

---

## Experience 2: Insert Automation — type a trigger, get magic

Community testers have been clear: speed matters, but surprises are not acceptable. Insert Automation is built for both. It gives you templates, log entries, abbreviations, and smart triggers while keeping every action explicit, announced, and undoable.

> “Delight is not about fireworks. Delight is when the editor does the small helpful thing at exactly the right moment and then gets out of your way.”  
> — Jeff Bishop

Insert Automation is the daily-workflow feature that changes how QUILL feels in practice. It combines typed shortcuts, templates, log files, smart text generation, document directives, and append anchors into one coherent keyboard-first system.

Everything is safe by design. Nothing scans your whole file silently. Nothing runs on a partial match. Nothing changes a read-only file. Every insertion is announced, discoverable, and one undo step.

### Typed abbreviations

Type a short abbreviation, press a delimiter such as space, comma, or period, and QUILL replaces the abbreviation with the full text.

The bundled **Smart Insert** Quillin ships with five abbreviations:

- **qbug** inserts a complete bug-report template with Title, Build, Screen reader, Windows version, Steps to reproduce, Expected result, Actual result, and Notes.
- **qmeet** inserts a meeting-notes template with today's date already filled in, plus Attendees, Purpose, Notes, and Action Items.
- **qlog** inserts today's date and time for a quick timestamped entry.
- **qtodo** inserts a short three-item to-do checklist ready to fill in.
- **qbrf** generates a multi-page BRF test document on the spot, ready to feed to the braille translator.

Your own abbreviations always win when there is a conflict. Quillin-provided abbreviations appear in the Insert Automation Reference and can be disabled individually.

### Smart text triggers

Type a command alone on a line and press Enter. QUILL replaces the whole line with the generated result. Smart triggers begin with `=` so they do not collide with ordinary sentences.

```text
=bug()            -> bug report template
=meeting()        -> meeting notes template
=journal()        -> journal entry with today's date
=todo(5)          -> five-item to-do checklist
=logentry()       -> timestamp at the cursor, formatted your way
=rand(3,4)        -> three paragraphs of four readable sentences each
=brftest()        -> a complete, predictable BRF test document
```

The parser is intentionally strict. A trigger activates only when it is alone on the current line, only accepts the allowed number and type of arguments, and rejects anything it does not recognize. Typing `=bug()` in the middle of a sentence is always safe. If a trigger would create a very large insertion, QUILL asks for confirmation before writing anything.

### `.LOG` file compatibility

Open a file whose first line is `.LOG` and QUILL behaves like Notepad: it finds the correct spot and inserts a fresh timestamp.

If the file contains a `QUILL-LOG-APPEND-HERE` anchor near the bottom, the timestamp lands just before the anchor and the anchor remains in place for the next entry. If the file is read-only, QUILL tells you rather than failing silently.

The timestamp format is configurable in **Preferences -> Smart Insert -> Log Mode**. Available formats include Long date and time, Short, ISO 8601, Date only, Time only, and custom `strftime` patterns.

### Append anchors

Any file can include a `QUILL-APPEND-HERE` marker near the bottom. Generated content lands before that marker instead of being shoved after footer notes, metadata, or other closing content. A stable anchor means generated text always goes exactly where you want it.

### Safety rules

Insert Automation follows clear safety boundaries:

- Abbreviations trigger only after an exact match and a delimiter.
- Smart triggers inspect only the current line and activate only on Enter.
- No file is scanned in full on open.
- Quillin-provided triggers run only while the Quillin is enabled.
- Every result is announced.
- Every insertion is one undo step.
- Read-only files are never modified silently.

---

## Experience 3: The Quillin Extension Platform — community extensions become first-class citizens

This is where the community story gets especially exciting. QUILL is no longer only an editor with built-in features. It is becoming a platform where contributors can build thoughtful, accessible extensions without sacrificing safety, privacy, or screen-reader quality.

> “The future of QUILL is not one person deciding every feature. It is a community of people building the tools they wish existed, with accessibility baked into the foundation.”  
> — Jeff Bishop

QUILL 0.7.0 upgrades Quillins from a command-and-snippet mechanism into a full extension platform.

Quillins can now subscribe to events, own settings, add searchable preference pages, display live status-bar data, declare dependencies, restrict network access, log to a developer console, and initialize or shut down cleanly. The manifest, validator, JSON schema, API surface, and developer tooling have all been expanded so accessibility and safety are enforced at install and load time.

### Quillin settings and Preferences pages

Quillins can contribute their own settings pages. A Quillin declares its preferences as structured manifest data: control type, label, description, default value, validation rules, and related metadata. QUILL renders those settings using accessible, keyboard-navigable stock controls.

The Quillin never touches wxPython directly. QUILL handles layout, tab order, focus, keyboard navigation, and accessibility. StaticText labels are always created before their associated controls in Windows child order so JAWS and other screen readers find the correct label buddy for every field.

Quillins with several groups of settings can declare **tabs** inside their preference page. Tabs are a standard `wx.Notebook` so arrow keys navigate between tabs and the active tab is clearly announced.

All five bundled Quillins ship live preference dialogs in 0.7.0. Open **Preferences** (Ctrl+Comma) and navigate to the Quillin by name:

- **Smart Insert** — five tabs: General, Log Mode, Smart Triggers, Abbreviations, and BRF Testing. Settings include large-insertion confirmation threshold, default to-do list length, custom timestamp format, and per-trigger enable/disable toggles.
- **BRF Tools** — four tabs: Translation, Page Handling, Status Bar, and Advanced. Settings include default translation profile, cells per line, lines per page, status bar verbosity, and diagnostic timeout.
- **Journal Stamp** — three tabs: Date Header, Word Count, and Session Restore. Settings include date format, custom strftime pattern (shown only when Custom is selected), daily word goal, and folder keyword filter.
- **Document Guardian** — three tabs: Close Guard, Save Stamp, and Save Confirmation. Settings include word count threshold, TODO marker text, save-stamp format, and save-confirmation toggle. Threshold and marker are disabled automatically when Close Guard is turned off.
- **Status Scribe** — two tabs: Display and Announce. Settings include count mode (Words, Characters, Sentences), label visibility, announce-on-save toggle, and announcement priority. Priority is disabled automatically when announce-on-save is off.

Quillin settings are stored per Quillin in `%APPDATA%\Quill\quillin_settings\<quillin-id>.json`, written atomically. They survive restarts and are retained when a Quillin is disabled.

Individual settings may include **`search_keywords`**: extra synonyms and technical terms that help users find settings by the words they know. For example, a Date format setting can include `timestamp`, `iso`, and `strftime`.

### Document and lifecycle events

Quillins can subscribe to document lifecycle events and run automatically when important moments occur.

QUILL 0.7.0 supports fourteen events:

| Event | When it fires |
| --- | --- |
| `document.opened` | A file was opened from disk |
| `document.activated` | The user switched to this document tab |
| `document.before_save` | Right before saving; a Quillin can validate or transform |
| `document.after_save` | After a successful save; safe to log, sync, or confirm |
| `document.before_close` | Before a tab closes; safe to warn |
| `document.after_close` | After a tab closes; safe to clean up |
| `document.created` | A new blank document was created |
| `document.loaded_from_session` | A document was restored from a crash or session file |
| `smart_trigger.entered` | Any smart trigger was activated |
| `abbreviation.expanded` | Any abbreviation was expanded |
| `quillin.enabled` | This Quillin was enabled or QUILL started with it active |
| `quillin.disabled` | This Quillin was disabled in Quillin Manager |
| `quill.shutdown` | QUILL is about to exit |
| `settings.changed` | A setting owned by this Quillin was changed by the user |

High-frequency events such as text changed, cursor moved, and key pressed are deliberately not available. They would allow a Quillin to observe keystrokes, which creates both privacy and performance problems.

Lifecycle events give Quillins a clean way to manage themselves. `quillin.enabled` is for initialization, activation announcements, cache building, or registration that requires the API to be live. `quillin.disabled` allows graceful cleanup. `quill.shutdown` allows state flushing before QUILL exits. `settings.changed` fires immediately when a user saves a preference change so the Quillin can hot-reload internal configuration without restarting.

Subscriptions can include `conditions` so they fire only for certain file types, path patterns, or content signatures. A template inserter can limit itself to files under `\journal\`. A `.LOG` handler can require `*.log` files. These filters are pure data, not code.

The capability gate is enforced. A Quillin must declare `document.events` in its capabilities to subscribe to events. Missing that capability, or missing the `main` module required to handle the event, fails validation at install time rather than failing later at runtime.

### Status-bar contributions

Quillins can add live cells to the QUILL status bar. A cell has a handler that QUILL calls on demand, such as after save, on tab switch, or on a timer. The handler's return value becomes the cell text.

Example manifest contribution:

```json
"status_bar": [
  {
    "id": "wordcount",
    "label": "Words: --",
    "handler": "get_word_count",
    "tooltip": "Current document word count",
    "width": 12
  }
]
```

To contribute a status cell, a Quillin declares `ui.status` in its capabilities, provides a `main` module, and describes the cell. The `tooltip` is read to screen-reader users when the cell receives focus, so the status bar remains navigable and informative rather than visual-only.

### Categories in Quillins Manager

Quillins can declare one or more category labels for filtering in Quillins Manager.

Available category labels include:

- `writing`
- `accessibility`
- `braille`
- `productivity`
- `developer`
- `formatting`
- `navigation`
- `ai`
- `integration`
- `education`
- `utilities`

Example:

```json
"categories": ["writing", "productivity"]
```

### Dependencies between Quillins

A Quillin can declare that it requires another Quillin to be installed and enabled.

```json
"requires": [{ "id": "com.quill.journalstamp", "min_version": "1.0.0" }]
```

QUILL verifies dependencies at load time. If a dependency is missing or too old, the dependent Quillin is blocked with a clear message.

### Network host allowlist

Quillins with the `net` capability can restrict which servers they are allowed to contact.

```json
"net_allowed_hosts": ["api.openweathermap.org", "*.example.com"]
```

When the list is non-empty, QUILL blocks connections to any host that is not on the list, even after the user has granted blanket `net` consent. Wildcard patterns such as `*.example.com` are supported.

### Command descriptions and search

Commands can now include a `description` field. This description appears in the keyboard reference and command palette as a one-line explanation that is separate from the menu title.

```json
"description": "Inserts a bug report skeleton with title, steps, expected, and actual fields."
```

### Developer logging with `api.log()`

Quillins with the `ui.log` capability can call `api.log(message)` to write structured log lines to the QUILL Developer Console.

The Developer Console opens from **Tools -> Developer Console** in development builds and can be toggled with `QUILL_DEV_BUILD=1`.

In production, with the console closed, `api.log()` is a no-op. It adds zero normal-use overhead and never writes to files or speaks to the screen reader.

### Announcement priority

`api.announce()` now accepts a `priority` keyword argument.

```python
api.announce("Saved.", priority="quiet")
api.announce("File not writable.", priority="urgent")
```

Valid values are `quiet`, `normal`, and `urgent`. The host maps those values to the screen reader's urgency channel. Use `quiet` for informational messages and `urgent` only for errors that need immediate attention.

### Quillin scaffold tool

A new command-line scaffold tool creates a ready-to-edit Quillin directory:

```text
python -m quill.tools.quillin_new com.example.myquillin "My Quillin"
```

Options include:

- `--layer1` for snippet-only Quillins with no Python.
- `--categories` to add category metadata.
- `--doc-events` to include sample lifecycle handlers.
- `--status-bar` to include a sample status cell.

The tool writes `manifest.json`, `extension.py`, `README.md`, and `LICENSE`, then tells the author the next three steps. Authors should run `quillin_lint` on the output before publishing.

### User control and safety enforcement

The Quillin platform is built around user control.

Open **Tools -> Quillins Manager** to enable or disable any Quillin. Select a Quillin and press **Enable** or **Disable**. The change takes effect immediately; no restart is required. Disabling a Quillin stops all of its commands, event handlers, and status-bar cells. Its preferences are preserved so it picks up where it left off if re-enabled.

Four sensitive capabilities require a confirmation dialog every time a Quillin tries to use them:

| Capability | What it does |
| --- | --- |
| `fs.read` | Read a file from disk |
| `fs.write` | Write a file to disk |
| `net` | Make a network request |
| `settings.core.write` | Change a QUILL-wide setting |

When a Quillin requests one of these actions, QUILL pauses and shows a dialog like this:

```text
A Quillin is requesting the 'fs.read' capability for: read_file(path). Allow this action?
```

Choosing no raises a `ConsentDeniedError` that the Quillin must handle gracefully. This confirmation appears for every individual action, not once at install time. A Quillin that reads files can never read one you have not explicitly approved.

The remaining capabilities are granted once at install time, or pre-granted for bundled Quillins. These include editor access, UI announcements, clipboard, storage, `settings.own.*`, document events, status bar, and developer log.

Each document event subscription includes an `enabled_by_default` field. If it is false, the event starts inactive. Users can change this any time from Quillins Manager: select the Quillin and choose **Configure Events...** to see each event subscription with a checkbox. Turning an event off stops the handler from firing; turning it back on resumes it. Per-event state is persisted in `state.json` alongside enable/disable and capability grants.

Capability declarations are enforced, not advisory. If a Quillin calls an API it did not declare in `capabilities`, QUILL blocks the call with a `CapabilityError` and notifies the Quillin instead of crashing. Declarations are validated by `quillin_lint` at install time and re-validated by the manifest parser at load time.

Third-party Quillins remain locked off for QUILL 1.0. The SEC-8 gate, `core.third_party_plugins`, is `locked_off`. A shipping build never discovers, loads, or executes third-party Quillin code. Quillins Manager still opens and remains fully navigable; it simply reports that third-party Quillins are disabled. This gate will lift when the publishing and review process is ready.

`min_quill_version` is enforced at load time. If a Quillin declares `"min_quill_version": "0.7.0"` and the running QUILL is older, the Quillin is rejected during discovery and listed in the Manager with an explanatory error such as `requires QUILL 0.7.0 (running 0.5.x)`.

`requires` is also enforced at load time. If a Quillin depends on another Quillin that is not installed, or is installed at a version too old to satisfy `min_version`, the dependent Quillin is blocked. The Manager shows the specific dependency error. Circular dependencies are caught during validation.

`net_allowed_hosts` is enforced at every fetch call. If a Quillin declares `"net_allowed_hosts": ["api.example.com"]` and tries to fetch from another host, QUILL blocks the call before it reaches the network, even if the user has granted the `net` capability. Wildcard patterns such as `*.example.com` allow subdomains but not the bare domain. An empty `net_allowed_hosts` list with the `net` capability preserves the current behavior: any host is reachable with user consent.

### Fourteen bundled Quillins

QUILL 0.7.0 ships fourteen bundled Quillins. Five bundled Quillins are new in 0.7.0 (Smart Insert, BRF Tools, Journal Stamp, Document Guardian, Status Scribe). Nine are carryover from prior releases, for a total of fourteen bundled Quillins. Each is both a useful extension and a reference implementation for the framework.

New in 0.7.0:

- **Smart Insert** (`com.quill.smartinsert`) provides typed abbreviations and smart triggers for bug reports, meeting notes, log entries, to-do lists, and BRF test documents. It includes five tabs of configurable preferences, categories `writing`, `productivity`, and `formatting`, plus command `description` fields on every command.
- **BRF Tools** (`com.quill.brftools`) provides preferences for braille translation, page handling, and status-bar display. Its categories are `braille` and `accessibility`.
- **Journal Stamp** (`com.quill.journalstamp`) subscribes to `document.created`, `document.after_save`, `document.loaded_from_session`, `quillin.enabled`, and `settings.changed`. It can insert a date header, announce word count and daily-goal progress after save, announce restored documents, log activation, and hot-reload preferences. Its date-format and daily-goal controls include `search_keywords`. Its categories are `writing` and `productivity`.
- **Document Guardian** (`com.quill.docguardian`) subscribes to `document.before_close`, `document.before_save`, `document.after_save`, `quillin.enabled`, `quillin.disabled`, and `quill.shutdown`. It can warn on unfinished documents, stamp an `Updated:` line, confirm saves with file size, announce and log activation, announce deactivation, and clean up on shutdown. Its categories are `writing` and `productivity`.
- **Status Scribe** (`com.quill.statusscribe`) adds a live word, character, and sentence count to the status bar. It updates after every save and on tab switch. It demonstrates `status_bar` contribution, `ui.log` developer logging, `quillin.enabled`, `quillin.disabled`, `settings.changed`, lifecycle events, and announcement priority. Its categories are `writing`, `productivity`, and `accessibility`.

Carryover from prior releases:

- **Text Tools** (`com.quill.bundled.text-tools`) — advanced text transformations: line numbering, hard-wrap, regex match counting, and block filtering.
- **Insert Tools** (`com.quill.bundled.insert-tools`) — date, time, and date-and-time snippets in the Insert > Date and Time submenu.
- **Line Tools** (`com.quill.bundled.line-tools`) — cursor-aware line operations.
- **Markdown Helpers** (`com.quill.bundled.markdown-helpers`) — syntax assistance for Markdown documents.
- **Insert Character** (`com.quill.bundled.insert-character`) — a searchable character picker for Unicode symbols.
- **Word Count (Node)** (`com.quill.bundled.word-count-node`) — word count via the Node.js Quillin runtime, demonstrating that Quillins can be written in JavaScript as well as Python.
- **AI Writing Prompts** (`com.quill.bundled.ai-writing-prompts`) — additional prompt library entries contributed by the Quillin manifest.
- **AI Writing Skills** (`com.quill.bundled.ai-writing-skills`) — pre-built `.sqp` skill files for rewriting, meeting-notes extraction, and research drafts.
- **Math Equations** (`com.quill.bundled.math-equations`) — `Insert -> Insert Equation...` (`Ctrl+Shift+E`) for LaTeX and MathML insertion, with Browser Preview and HTML export rendering via MathJax 3. See the community contribution spotlight below.

### Five new Quillin capabilities, live in this release

In previous releases, parts of the Quillin platform existed as declarations: events were defined, schedules were documented, preferences were validated — but the runtime never dispatched them. QUILL 0.7.0 makes the whole surface live. Five capabilities that Quillins could not use before can now be used in production, each demonstrated by at least one bundled extension.

- **Timer events** — a Quillin can schedule background work every N seconds (minimum 60, maximum 86400). Timers run on dedicated threads so the editor never blocks. Status Scribe uses this to refresh its word-count status cell every five minutes without a user action.
- **File-type contributions** — a Quillin can declare which file extensions it handles. When a matching file opens, the Quillin's handler fires automatically. BRF Tools announces the braille page count when a `.brf` or `.brl` file opens.
- **Snippet Gallery** — a Quillin can contribute named, parameterized templates to a browseable picker. Open it from **Insert → Snippet Gallery...**, choose a template, fill in any prompts, and the expanded text lands at the cursor. Smart Insert ships three gallery entries: a report header, a meeting invite, and a Markdown bug report.
- **Document lifecycle events** — the 14 declared events (`document.opened`, `document.after_save`, `quill.shutdown`, and the rest) now actually dispatch at runtime. Journal Stamp and Status Scribe are both live.
- **Settings pages** — all five bundled Quillins with `contributes.preferences` declarations now have working settings dialogs in the Preferences hub. The renderer handles boolean, integer, string, and choice controls; conditional `visible_when` and `enabled_when` expressions update controls live; and label-first Z-order throughout means JAWS and NVDA announce the right label for every field.

---

## Experience 4: Braille Mode — professional braille editing inside QUILL

Braille support is not treated as an add-on or a novelty. It is designed around the way braille professionals actually work: page, line, cell, progress, translation choices, preservation of layout, and confidence that the file will not be silently changed.

> “Braille users deserve tools that understand braille workflows, not tools that merely tolerate braille files.”  
> — Jeff Bishop

### Enabling Braille Mode

Braille Mode is not enabled by default. To turn it on:

- During the startup wizard, choose the **Braille Professional** profile.
- At any time, open **Help > Enable Braille Mode...** This shows a brief description of what you get and lets you enable it with one keypress. The menu item only appears when Braille Mode is off; once you enable it the Braille menu appears instead.
- You can also enable it through **Help > Feature Profiles > Manage Individual Features**.

When Braille Mode is enabled and the QUILL Braille Pack is not yet installed, a prompt appears explaining what the pack adds (translation engine, BRF export, braille display support). You can install it, skip it, or choose **Disable Braille Mode** if you do not need braille tools. Choosing Disable Braille Mode turns the feature off and removes the prompt permanently; you can re-enable at any time using Help > Enable Braille Mode.

### What Braille Mode is for

QUILL can now open and edit formatted braille text files. The goal is to let a braille proofreader move through a transcription the way it is actually laid out: by braille pages, lines, cells, hard page breaks, and progress through the document.

### Opening and saving braille files

Open a braille file the same way you open any other file. QUILL reads it as braille text and scans it for any character that is not braille ASCII. Nothing is transformed on the way in; the document reflects the file's bytes.

Saving is byte-for-byte. QUILL does not trim trailing spaces, normalize line endings, or remove form feeds. Hard page breaks are preserved. If the text contains characters outside the braille-ASCII range, QUILL still saves them as-is and gives one non-blocking spoken warning so nothing is silently changed. A round trip of open and save returns an identical file.

### Braille status cell

While a braille file is active, the status bar includes a braille cell that updates as you move:

```text
BRF Pg 12/87 | Ln 14/25 | Cell 31/40 | Print 7
```

That status gives the braille page, line within the page, cell within the line, and print page. Print-page detection runs on every open and on every page-map recalculation, so the print segment is always populated when a print-to-braille anchor is available; on documents without anchors it reads `Print ?`.

### Braille commands

Braille commands now live under **Tools -> Braille**. Key bindings are intentionally left unset so QUILL does not collide with screen-reader keys or existing editor shortcuts. You can assign your own bindings in the keyboard customizer or run the commands from the Command Palette.

The Braille menu is organized into three groups.

**Status** includes:

- Read Braille Status, respecting your status verbosity.
- Read Detailed Braille Status.
- Read Current Line and Cell.
- Read Current Braille Page.
- Read Current Print Page.
- Read Progress Summary, which reports how far through the document you are.

**Navigation** includes:

- Go to Braille Page..., where you type a page number.
- Next Braille Page.
- Previous Braille Page.

Moving past the first or last page tells you there is no more.

**Page Tools** includes:

- Insert Braille Page Break, which inserts a form feed.
- Remove Braille Page Break at the cursor.
- Recalculate Page Map, which rebuilds the page map after edits.
- Normalize Line Endings, currently present as a placeholder.

Every braille status and navigation command is safe to run on a non-braille document. QUILL simply says, `This is not a braille document`, and does nothing else.

### Translation with the optional QUILL Braille Pack

Forward and back translation between print text and braille require the optional **QUILL Braille Pack**, which can be selected during installation.

The pack uses a three-layer architecture:

1. A full technical catalog of every available liblouis table.
2. User-facing profiles that map friendly names to the correct tables.
3. The translation runtime itself.

When the pack is installed, the Translation submenu is organized into three sections.

**UEB (Unified English Braille)** includes:

- Contracted, Grade 2.
- Uncontracted, Grade 1.
- Translate Selection to UEB.
- Back-Translate UEB.

**Standard American English (Legacy)** includes:

- Contracted, Grade 2.
- Uncontracted, Grade 1.

These use the traditional North American English tables.

**More Languages** is populated automatically from the pack's profile catalog. It includes German, French, Spanish, Russian, Korean, and dozens more. Languages with both contracted and uncontracted variants appear as their own sub-group.

When the pack is absent, the Translation submenu is hidden entirely; you do not see disabled items. The Translation submenu is also hidden in Safe Mode.

Forward translation opens the BRF result in a new document and tells you how many braille pages it produced. Back-translation always opens its result as a clearly labelled draft because automatic back-translation is not authoritative. Translation runs entirely out of process, so a liblouis failure cannot take QUILL down.

### Braille Mode Phase 2: print-page detection and proofing navigation

Braille Mode Phase 2 turns the page map into something a proofreader can act on. Two engineering pieces do the work:

#### Print-page and running-head detection (BR-013)

QUILL now reads the print page (and the chapter running head) directly off the BRF, so a braille proofreader no longer has to keep that map in their head. The new `brf_page_detection.py` engine is pure — it imports nothing from `wx` and is exhaustively unit-tested — and walks the page map once to emit confidence-labelled indicators:

- **High confidence** — a print-page-change separator line of five or more hyphens followed by an anchor (`---------#ab`, `---------#12a`, or `---------#1`); *or* a right-margin page number on line 1 that matches the previous detected page and carries a continuation letter.
- **Medium confidence** — a right-aligned number on line 1 with no other anchor; *or* a consistent sequence across several pages.
- **Low confidence** — an ambiguous right-margin number; *or* a short page with multiple candidates.

The detector also produces a `BraillePageMarker` per page (the right-margin number on the last line of each braille page) and a `RunningHead` per page (the leading text of line 1, after stripping the right-margin number). When the detector has no anchor for the caret page, the status bar's print segment still reads `Print ?` so the fallback is visible, not silent.

#### Detailed status and print-page navigation (BR-014)

Six new commands in the Braille menu turn the detector output into something a proofreader can act on:

- **Go to Print Page…** — type a print-page number; QUILL snaps the caret to the start of the braille page that hosts it and announces the result. Default value is the indicator closest to your current caret position.
- **Next Print Page Change** / **Previous Print Page Change** — step the caret to the next / previous print-page boundary in the detector output. If there is none, QUILL tells you rather than looping.
- **Announce Running Head** — reads the running head of the caret page aloud (or "No running head detected for this page." when the line-1 text is empty or absent).
- **Include Running Head in Status** / **Omit Running Head from Status** — toggle the `braille_include_running_head` setting. Detailed status only includes the running head when the setting is on; the menu item is purely a preference, not a one-shot announce.

`Read Detailed Braille Status` now composes the full example string from the spec — print page, continuation letter, running head, proofing state, and detection confidence — pulling live data from the new detector. A typical announcement reads:

> "Braille page 12 of 87. Line 14 of 25. Cell 31 of 40. Print page 7; continuation a; Running head: Chapter 2; Last proofed page: 9; 3 pages marked needs review; detected with high confidence."

`Read Current Print Page` no longer hard-codes "Print page unknown"; it announces the most recent detected print page at or before the caret (or "Print page unknown" when the detector has nothing to report).

Every new command degrades gracefully on non-braille documents — it simply tells you "This is not a braille document" rather than doing anything. Default key bindings are intentionally left unset (matching the Phase 1 convention) so nothing collides with your screen reader or existing editor shortcuts; assign your own in the keyboard customizer, or run the commands from the Command Palette.

#### Where the new code lives

- `quill/core/brf_page_detection.py` — pure detector module; 12 unit tests in `tests/unit/core/test_brf_page_detection.py`, including a real-world corpus test against the 5-page sample at `tests/corpus/braille/one_crazy_night.brf`.
- `quill/ui/main_frame_braille.py` — the new commands, the new menu items, and the `_compose_detailed_status` helper that wires the detector output into `read_detailed_braille_status`. Source-level wiring tests in `tests/unit/ui/test_braille_print_navigation.py`.

Strict-typed; `mypy --strict` is clean for the new module. The wider braille test suite — status strings, page map, position resolver, translation worker — remains green.

#### What is still on the roadmap

- **Phase 3 (Proofing and Progress)** — the sidecar JSON, the restore-on-open behaviour, and the proofing commands (mark proofed / mark needs review / list proofed / etc.). Tracked in issues #238, #239, #240.
- **Phase 4 (Validation)** — warning rules that combine the page map and the detector output to catch ambiguous page boundaries.
- **Phase 6 (Source-to-BRF)** — a workflow that takes a print-text document through the translator and into a clean BRF ready for proofreading.

The detailed design for each of these phases remains in `docs/planning/planning.md` (Feature: Braille Mode), preserved as a reference for the release where they ship.

#### Acknowledgements

Thank you to the screen-reader users and braille proofreaders who filed the issues that drove this phase, and to the maintainers of liblouis and the Universal BRF Pack whose tables make the translation side of Braille Mode possible.

---

## Experience 5: Compare Mode — review differences by keyboard and by ear

Reviewing changes should not require visual scanning. Compare Mode turns file comparison into a spoken, keyboard-driven workflow with optional sound cues for fast orientation.

File comparison is now a first-class keyboard-driven workflow.

Open a comparison and move through it with:

- **F8** for next difference.
- **Shift+F8** for previous difference.
- **Ctrl+F8** to re-announce the current difference.
- **Alt+F8** to hear just the words that changed on the current line.

Differences are presented as a real list, so you can review them one at a time with your screen reader.

If you use a sound pack, Compare Mode also provides distinct cues for opening a comparison, closing a comparison, stepping between differences, and bumping against the first or last difference. The result is a faster review loop: speech tells you what changed, and optional sound tells you where you are in the comparison.

---

## Experience 6: Code-aware editing — move through source files more intelligently

When you open a source file, QUILL loads a language profile from the file extension. Recognized profiles include:

- Python
- JavaScript
- TypeScript
- Kotlin
- Shell
- Markdown
- JSON
- TOML
- SQL

Files with unrecognized extensions use a sensible plain-text fallback.

**Next Token** and **Previous Token**, both in the Navigate menu, move the caret to the next identifier, keyword, operator, or literal. This is more predictable than ordinary word movement when reading code by ear.

**Navigate -> Set Document Language** lets you override the automatic choice. This is useful for unsaved buffers, unusual extensions, or snippets pasted into plain files.

Paired with indentation tones, code-aware editing lets structure come through as pitch while token movement lets you move through meaning.

---

## Experience 7: Sound notifications and indentation tones — optional audio feedback without extra speech

QUILL can now play short non-speech audio cues, called earcons, at meaningful moments such as a file save, a successful search, or opening a comparison. The goal is to let your screen reader remain focused on text while a quick sound confirms that something happened.

### Sound packs

Sounds come from a **sound pack**: either a folder or a single `.qsp` file containing audio clips and a small manifest that maps events to sounds. QUILL ships with a bundled pack called **Ink**, and you can add your own.

### QUILL key confirmation tone

When you press the QUILL key, **Ctrl+Shift+Grave**, to arm the prefix, QUILL now plays a short two-tone ping named `quill_key_pressed`. It is distinct from every other earcon, so you receive instant audio confirmation that the prefix is live without waiting for speech.

This earcon is included in all bundled sound packs and can be toggled individually in **Tools -> Reading & Dictation -> Sound Events...**.

### Per-event control

Open **Tools -> Reading & Dictation -> Sound Events...** to switch individual sound events on or off. Events are grouped into Earcons, Compare, and Indentation tones, so you can keep the cues you like and silence the rest.

**Toggle Sound Notifications** turns all sound notifications on or off at once and plays a short on or off cue so you know where you landed.

Sound is opt-in. Most earcons remain off until you choose a sound pack and enable events, so upgrading does not make your current setup noisier.

### Indentation tones for code

Indentation tones are also opt-in. Pick a musical scale under the **Indentation tones** setting, or leave it Off.

When enabled, QUILL plays a pitch that rises as your caret moves deeper into indented code and falls as you move back out. Blank lines stay silent and hold the last level, so moving through gaps does not chirp. It is a quiet ambient way to feel the shape of code without counting spaces.

---

## Experience 8: Text encoding tools — find, inspect, convert, and save safely

New commands under **Format -> HTML & Encoding** make character and encoding cleanup accessible from inside QUILL.

### Show Non-ASCII Characters

**Show Non-ASCII Characters** opens a read-only report of every character beyond plain ASCII. Each entry includes:

- Line and column.
- Codepoint.
- Character name.
- Whether it converts cleanly to Latin-1.
- Whether it converts cleanly to Windows-1252, also known as MS-ANSI.

This replaces the old command-line ritual of running a file through tools such as `iconv`, inserting a sentinel string, and hunting for what failed.

### Jump between the report and source

While the report is open, move to any character entry row and choose **Format -> HTML & Encoding -> Jump to Source Line**. QUILL switches to the source document and lands on the reported line.

Assign this command a key in the Keymap Editor for faster character-by-character review.

**Jump Back to Non-ASCII Report** returns focus to the report tab so you can continue reviewing the list without using the mouse.

### Convert Non-ASCII to HTML Entities

**Convert Non-ASCII to HTML Entities** rewrites accented letters and symbols as HTML entities, such as `&eacute;`, or numeric entities such as `&#233;` when no named entity exists. Ordinary text and existing markup are left alone.

This is the reliable command when you need to feed text to a tool, such as Pandoc, that refuses high characters.

### Re-encode As...

**Re-encode As...** saves a copy in the encoding you choose:

- UTF-8.
- UTF-8 with a byte-order mark.
- Latin-1.
- Windows-1252.
- ASCII.

Anything that does not fit a narrow target is written as a numeric HTML entity instead of being silently replaced by a question mark. Nothing is quietly lost.

### Decode HTML Entities, and know your minimum encoding

A community request (#256) asked for two things: turn `&eacute;`-style entities back into real characters, and then save in the smallest encoding that still holds everything, instead of always reaching for UTF-8.

**Decode HTML Entities** does the first half — `&eacute;`, `&amp;`, `&#233;`, and `&#xE9;` all become `é` and `&`, while an entity QUILL does not recognize is left exactly as written rather than silently deleted.

Two new commands do the second half:

- **Analyze Encoding Requirements** opens a short report: your current encoding, whether the document still fits it, and — if not — the simplest encoding that would, in the order ASCII, Latin-1, Windows-1252, then UTF-8.
- **Save Using Minimum Required Encoding...** saves a copy using exactly that encoding. A document that has only ever needed Latin-1 stays Latin-1 instead of being upgraded to UTF-8 by default. You can still choose UTF-8 explicitly any time you want it.

Four small text-utility gaps closed alongside this: **Remove Email Quote Markers** (strips leading `>` and `Name>` prefixes from forwarded threads), **Strip Low ASCII Characters**, **Strip High ASCII Characters**, and **Convert to Hex Dump** (a read-only offset/hex/ASCII view of a selection's raw bytes).

---

## Experience 8b: Markdown profiles and a table of contents that doesn't need AI

A second community request (#257) asked for Markdown_py-style extensions such as `toc` and `nl2br`. QUILL already had an AI agent that can write a table of contents (**AI -> Generate Table of Contents**), but that needs a configured AI provider, a network call, and trusts a model to read your headings correctly. This release adds the deterministic alternative.

**Insert -> Table of Contents** parses your document's headings directly and builds a table of contents from them — no model, no network, and the links always match because they come from the same heading text, not a paraphrase of it. Put a `[TOC]` marker on its own line and the table of contents replaces it there; otherwise it lands right after your first heading.

**Format -> Markdown** adds three more commands:

- **Select Markdown Profile...** — choose Standard Markdown, GitHub-Style Markdown, Documentation, Poetry and Lyrics, Accessible Publishing, Technical Writing, PRD and Release Notes, or Custom, and QUILL tells you in plain language what that profile turns on ("Markdown profile: Documentation. 5 extensions enabled.").
- **Preserve Single Line Breaks** — keeps every line break as a line break instead of folding it into a paragraph, for poetry, lyrics, speeches, and scripts where the line matters.
- **Read Markdown Processing Status** — announces your current profile and what it enables, on demand.

Under the hood, this is also the first feature to get its own non-AI feature tag: `core.markdown_profiles` sits in the feature catalog as a sibling of `future.ai`, not underneath it, so turning AI off — Safe Mode, or any profile that keeps `future.ai` quiet — never takes the table of contents with it. The HTML-entity and encoding commands above got the same treatment under a new `core.text_encoding` tag.

---

## Experience 8c: More text-utility power tools — line numbering, codepage fixes, multi-replace, and quick stats

Eight more text-utility commands round out the toolbox started in Experience 8, closing the remaining gaps reported after that release shipped.

### Number Lines (Advanced)

**Format -> Line -> Number Lines (Advanced)...** goes beyond the existing Number Lines command with a small form: starting number, increment, digit or Roman-numeral style, zero-padding width, a custom suffix, and left or right alignment. Blank lines are still skipped, exactly like the simple version.

### Fix DOS and Windows codepage mojibake

Two new commands under **Format -> HTML & Encoding** repair the classic "DOS text shows garbage in Windows" and "Windows text shows garbage in DOS" mismatch:

- **Convert OEM (DOS) to ANSI** reinterprets CP437 bytes as Windows-1252.
- **Convert ANSI to OEM (DOS)** does the reverse.

### Line-drawing characters

Old DOS-art and terminal output sometimes carries Unicode box-drawing characters (─, │, ┌, and friends) that don't render well everywhere. Two more commands handle them:

- **Convert Line-Drawing Characters to ASCII** maps them to plain `-`, `|`, and `+`.
- **Strip Line-Drawing Characters** removes them outright.

### Multi Replace and Count Occurrences

**Search -> Multi Replace...** applies up to four search-and-replace pairs in one pass, with an optional case-insensitive toggle, instead of repeating Find & Replace four times.

**Search -> Count Occurrences...** reports how many times a string appears in the selection or document, read aloud as a simple count rather than requiring a manual tally.

### Line Statistics

**Tools -> Line Statistics** scans the selection or document for one number per line and opens a short report: count, total, average, median, mode, and standard deviation. Lines that aren't plain numbers are skipped rather than causing an error.

---

## Experience 9: Save as Word or RTF

QUILL can now hand your work over as a Word document or rich text file.

Choose **File -> Save As...**, then select **Word Document (`*.docx`)** or **Rich Text** from the type list. QUILL converts the document on the way out, avoiding the copy-paste-into-Word routine.

The conversion is handled through Pandoc with real Word styles. If your source has headings, those become actual Word headings, not bold text that merely looks like a heading. That keeps the exported file navigable for the next person's screen reader.

The result reflects the structure of the source. A richly formatted Markdown or HTML document exports with that structure. A plain-text file exports as a tidy but unadorned document because there was no structure to carry. QUILL tells you that instead of quietly flattening your work.

---

## Experience 9b: Pandoc Import / Export and Batch Conversion (issue #262)

The single-file Word and RTF export added above is a thin slice of a much larger workflow. Community request #262 asked for a real, screen-reader-friendly way to move between QUILL and the documents other people send us — Word, OpenDocument, EPUB, LaTeX, plain text, CSV tables, and the rest of the formats Pandoc understands — without dropping into a shell. This release answers it.

> “Importing and exporting should feel like part of the editor, not a side door you have to leave the keyboard to use.”  
> — Jeff Bishop

### The Tier-1 format set

The new Import and Export menus each show a curated Tier-1 list rather than every format Pandoc supports, because not every format is a good match for a screen-reader-first editor. The list is the same one issue #262 recommended.

**Import (File -> Import):** Markdown, CommonMark, GitHub-Flavored Markdown, HTML, Word documents (`.docx`), OpenDocument Text (`.odt`), Rich Text (`.rtf`), plain text, CSV / TSV tables, EPUB books, LaTeX / TeX.

**Export (File -> Export):** the same set plus PDF (export only). PDF *import* is intentionally not supported; Pandoc cannot do it reliably, and the dedicated braille and DAISY pipelines are the right tools for print-to-braille conversion.

Every entry on the menus is a real, working converter. There is no placeholder that opens a "Coming soon" dialog mid-list. **Pandoc Conversion Center...** under Tools is the only path to the rest of Pandoc's format catalog in this release; it opens a short notice explaining the roadmap.

### Single-file import and export

Pick **File -> Import -> Word Document** to convert a `.docx` into a Markdown buffer in a new tab. Pick **File -> Export -> EPUB Book** to convert the current buffer to a clean `.epub`. Both routes go through Pandoc, with the conversion happening on a background thread so QUILL never freezes.

When the target format is editable in QUILL — Markdown, CommonMark, GFM, HTML, plain text, CSV / TSV — a short post-conversion prompt asks whether to open the new file in a new window. Press **Yes** to open, **No** to keep working where you were. PDF, DOCX, EPUB, ODT, and RTF do not prompt because QUILL cannot edit them directly; a confirmation message tells you where the file landed and the path is on the clipboard so you can paste it into File Explorer.

### The Batch Conversion wizard

**File -> Import -> Batch Conversion...** and **File -> Export -> Batch Conversion...** (or **QUILL key, B**) open a four-page wizard. Each page is keyboard-navigable end to end, every field is labelled in JAWS / NVDA order, and Back / Next / Start / Cancel are stock `wx.Button` controls under the standard modal-id contract.

1. **Introduction.** The first page reads a short summary of what the wizard does, then probes Pandoc. When Pandoc is detected, the version appears live in the page text. When it is not, the page says so and Start stays disabled until Pandoc is installed.
2. **Folder and options.** A folder picker, an *Include subfolders* checkbox, an output-layout radio (Same folder as source, or Output subfolder per source folder), and an overwrite radio (Ask each time, Never, Always). Defaults are read from Settings so the wizard respects your preferences the moment it opens. The last folder you used is remembered for next time.
3. **Format and profile.** A direction radio (Import into QUILL, or Export from QUILL), a source-format list and a target-format list drawn from the Tier-1 set, and a profile picker for the seven built-in conversion profiles.
4. **Review and start.** A human-readable summary of the entire plan. The Start button submits the batch to a background thread and closes the wizard.

Press **Start** and the wizard submits the plan to QUILL's background task pool. The Status Page (Help menu) switches to its Tasks & Downloads tab and starts showing live rows. The first row is labelled `Batch conversion: scanning <folder>`, then one row per file as the conversion runs, with `(file, status, current/total, started, finished)` columns.

### Seven built-in conversion profiles

The wizard's profile picker offers seven profiles curated for common publishing workflows. Each profile is a small set of Pandoc CLI flags plus a plain-language description so the screen reader can read you what you are committing to before you click Start.

- **Clean Word Document** — `--standalone` plus aggressive header/footer stripping. Good for handing Markdown drafts to a Word shop that should not see the scaffolding.
- **Accessible HTML Page** — `--standalone` with the `title-block` and `lang` metadata. Good for an HTML page that is going through a screen-reader or accessibility audit.
- **EPUB Book** — `--standalone --toc` plus the EPUB-3 metadata block. Good for personal publishing.
- **GitHub README** — GitHub-Flavored Markdown with no wrapper. Good for pasting into a repository.
- **Print PDF** — `--pdf-engine=<default>` plus the standard PDF metadata. Pandoc picks the right engine for your platform; you can change it in Preferences.
- **Instructor Handout** — `--standalone` with `geometry: margin=1in` and a top-level numbered section structure. Good for printing on Letter.
- **Plain Text for Screen Readers** — emits plain text with no HTML wrapper, no smart quotes, and a fixed width of 80 columns. The right choice for piping into a TTS engine.

The wizard's summary page reads the profile description aloud so the user knows what they are about to apply before the batch starts.

### Output naming and overwrite behaviour

The issue #262 specification said "keep the originating stem, replace the extension". QUILL does that exactly. `report.docx` becomes `report.md` (or `report.html`, `report.epub`, ...). When you choose **Output subfolder per source folder** (the default) the output lands in a new `Output/` folder inside the source folder, which the batch creates on first write. When you choose **Same folder as source** the output lands next to the input.

The three-way overwrite policy keeps the screen reader out of the per-file prompt loop:

- **Ask each time** — the batch lists every output that would clobber an existing file, asks once with a single yes/no, and skips the rest if you say no.
- **Never** — existing outputs are skipped automatically. The Status Page shows the count under *skipped* so the total still adds up.
- **Always** — existing outputs are overwritten without prompting. Useful for re-running a batch with the same plan.

### Live progress and a single, calm completion announcement

The batch runs on the background task pool. The Status Page shows live counts as the work progresses. When the batch finishes, QUILL speaks a single completion line through the announcement backend you have configured (NVDA, JAWS, SAPI5, or a sound pack). The line names the converted / skipped / failed counts and the elapsed time:

> "Batch conversion complete. 12 of 14 files converted in 4.2 seconds. 2 skipped."

The completion announcement respects the verbosity settings under **Preferences -> Accessibility**; the Status Page row updates regardless so sighted and low-vision users see the same result.

A short report dialog lists every file that produced warnings or failed, with the exact error string. Successful files do not appear in the report, so the dialog stays small and quick to read.

### Settings: defaults the wizard can override

Three new Settings entries let you choose defaults that the wizard uses when it opens:

- **Include subfolders in batch conversion** — boolean, default `True`.
- **Overwrite behaviour for batch conversion** — Ask each time (default), Never, or Always.
- **Default output layout for batch conversion** — Output subfolder per source folder (default) or Same folder as source.

The wizard can override any of them per run. The Preferences dialog is the canonical place to change defaults; the wizard is a one-off override path. The last folder the wizard used is remembered automatically so the next run lands you back where you left off.

### What is not in this release

- **PDF import.** Pandoc cannot do it reliably, so it is not in the menu. The dedicated braille and DAISY pipelines remain the right tools for print-to-braille conversion.
- **Tier 2 / Tier 3 formats.** Every format Pandoc supports that is not in the Tier-1 list is reachable through **Tools -> Pandoc Conversion Center...**, which shows a roadmap note in this release. A follow-up issue will replace the placeholder with the full format picker.
- **MarkItDown.** A follow-up issue; not in this release. MarkItDown is the right tool for some conversions (e.g. PDF and Office formats with embedded images) but its integration belongs in a Quillin so its dependencies stay out of the core.
- **Per-verb verbosity tokens.** The completion announcement routes through the existing `announce()` -> `_announce()` -> `AnnouncementEngine` path. The per-verb token registry from the verbosity rebuild is not in source yet; that work is tracked separately and the existing settings (`announcement_backend`, `verbosity_speech_enabled`) continue to control the spoken result.

---

## Experience 10: Citations without the tears

**Insert -> Insert Citation...** opens a plain labelled form for creating citations.

You choose:

- Source type: book, journal article, or website.
- Style: MLA 9, Chicago 17, or APA 7.
- Output: in-text citation, full bibliography entry, or both.

Then you fill in the facts you know, such as author, title, year, and related fields. QUILL handles the punctuation, ordering, formatting details, and insertion at the cursor.

The point is simple: screen-reader users should not be at a disadvantage because citation formatting is visual, finicky, and easy to get wrong.

If you write in the new **Author or Student** profile (see Experience 1), **Format -> Markdown -> Select Citation Style...** chooses how citations default for you: Markdown footnotes for a lighter-weight paper, or Academic to favor the MLA/Chicago/APA bibliography form above.

---

## Experience 11: Snippet Gallery — parameterized templates in one place

The Snippet Gallery collects reusable, fill-in-the-blank templates contributed by Quillins into a single browseable picker. Open it from **Insert > Snippet Gallery...** or press **QUILL key, Shift+G**.

A gallery dialog opens showing every available snippet, grouped by Quillin. Select one, read the preview, and press **Insert**. If the snippet has parameters — a title, a date, a subject line — QUILL prompts you for each one in sequence, then inserts the completed text at your cursor.

Smart Insert ships three built-in entries:

- **Report Header** — a titled section with an author and date line. Prompts: report title, date.
- **Meeting Invitation** — subject, date, location, and agenda block. Prompts: subject, date/time, location, agenda.
- **Bug Report (Markdown)** — a full Markdown bug-report skeleton with title, environment, steps to reproduce, expected result, and actual result. Prompts: title.

Any Quillin can contribute gallery entries by adding a `snippet_gallery` block to its manifest. No extra capability is required.

---

## Experience 11b: Abbreviation expansion — type `ul>li.item$*3>a[href]{Item $}`, get a list

Three new commands on the **Edit** menu bring Emmet-style abbreviation expansion to QUILL: type a compact shorthand, expand it into full HTML or CSS, and never hand-type a repetitive structure again.

**Expand Abbreviation** expands the current selection — or, with no selection, the run of text immediately before the cursor — in place, as a single undo step. Type `ul>li.item$*3>a[href]{Item $}`, run the command, and get:

```html
<ul>
  <li class="item1">
    <a href>Item 1</a>
  </li>
  <li class="item2">
    <a href>Item 2</a>
  </li>
  <li class="item3">
    <a href>Item 3</a>
  </li>
</ul>
```

**Preview Abbreviation...** prompts for an abbreviation and opens the expansion in a new tab without touching your document — a safe way to experiment. **Explain Abbreviation...** opens a plain-text, indented breakdown of what an abbreviation means (tag, id, classes, attribute names, repetition counts) before you commit to it, which is the fastest way to learn the grammar by ear.

The grammar covers the core Emmet operators: child (`>`), sibling (`+`), climb-up (`^`), grouping (`(...)`), multiplication (`*N`), and numbering (`$`, with `$$` for zero-padded numbers). Numbering resolves against the nearest enclosing repetition, so `ul>li*3>span.label$` numbers the span 1 through 3 by its enclosing `li`, the way real Emmet behaves. Common tags pick up sensible default attributes when you don't specify them — `a` gets an empty `href`, `img` gets `src` and `alt` — and void elements like `br` and `img` never get a closing tag they don't need.

A handful of built-in snippets skip the grammar entirely: `!` for a full HTML5 skeleton, `!a11y` for the same skeleton with a skip link and `header`/`main`/`footer` landmarks already in place, `skiplink` on its own, `form:a11y` for a labeled field inside a fieldset, and `table:a11y` for a table with a caption and properly scoped header cells — accessible structure as the default, not an afterthought.

Open a `.css` file and the same three commands switch to CSS mode, expanding a curated set of common shorthand: `d:f` for `display: flex;`, `pos:a` for `position: absolute;`, `m10-20` for `margin: 10px 20px;`, and around thirty more.

This release ships the core engine and the three commands. Placeholder navigation after expansion, a snippet manager, a Quillin extension API for custom expansion providers, and a Markdown-specific abbreviation pack are on the roadmap, not silently missing — see the PRD for the full list.

---

## Community contribution spotlight: Vision Prompt Library by Kelly Ford

Some contributions change a feature. Some contributions change expectations. Kelly Ford's work on image description prompts does both by making AI image description more intentional, more flexible, and more useful to blind users.

QUILL 0.7.0 includes a Vision Prompt Library for **Describe Image with AI**, contributed by [Kelly Ford](https://github.com/kellylford).

Kelly independently built and evaluated twelve prompt styles drawn from his [Image Description Toolkit](https://github.com/kellylford/Image-Description-Toolkit), an experimental toolkit for accessible image interaction.

Instead of one hardcoded image-description prompt, QUILL now lets you choose from twelve IDT-evaluated styles. Each style targets a specific use case, such as:

- Concise identification.
- Detailed scene description.
- Alt text optimized for web publishing.
- Screen-reader-first narrative.
- Document-context interpretation.
- Additional curated description styles.

These styles are evaluated and curated, not randomly generated.

### How the library works

- **Zero disruption by default.** If you never change a setting, Describe Image behaves exactly as before. The default IDT style is applied silently with no extra clicks.
- **Try a different prompt.** After a description arrives, a **Try a different prompt...** button appears in the review dialog. One click re-runs the description with the next style in the list. No re-uploading, no dialog re-opening, and no extra navigation.
- **Opt-in pre-describe picker.** Enable the style picker in **Settings -> AI** if you want to choose a prompt style before describing an image. Once enabled, QUILL shows a focused keyboard-navigable list of the twelve styles before every description.
- **Edit built-in prompt text.** Open **AI Hub > Instructions > Image Styles** to edit the prompt text for any of Kelly's twelve built-in styles. The original shipped text is always shown in a read-only reference panel below the editor. Press Reset to Default at any time to restore the shipped version. Enable and disable individual styles from the same tab.
- **Manage Image Prompts dialog.** Open **AI Hub > Image Prompt Styles...** to toggle styles on or off and add fully custom prompts. Custom prompts are additive — they appear after the built-in styles in every picker.
- **Settings sync immediately.** A bug where AI Hub changes to vision settings, including picker toggle and default style, did not apply until restart. That is fixed. Changes apply as soon as you save.

Kelly's Image Description Toolkit is worth bookmarking: <https://github.com/kellylford/Image-Description-Toolkit>.

Kelly also maintains several screen-reader-friendly applications:

- [QuickMail](https://github.com/kellylford/QuickMail), an accessible IMAP email client.
- [RSSQuick](https://github.com/kellylford/rssquick), an accessible WPF RSS reader.
- [ChatViewer](https://github.com/kellylford/ChatViewer), a GitHub Copilot Chat viewer.

Thank you, Kelly, for work that consistently puts screen-reader users first. This is exactly the kind of community contribution QUILL is built to welcome: practical, thoughtful, evaluated, and rooted in the lived experience of screen-reader users.

---

## Experience 12: AI Writing Assistant — a complete toolkit that stays under your control

AI in QUILL is not meant to replace the writer. It is meant to support the writer, explain itself, respect provider choice, and keep the keyboard-first workflow intact.

> “AI should help people express what they mean, not flatten their voice. The goal is confidence, clarity, and control.”  
> — Jeff Bishop

QUILL 0.7.0 ships a full AI writing-assistant layer. Every feature in this layer is optional, works with multiple providers, runs entirely on your terms, and is designed so screen-reader users can operate it without a mouse.

### Provider setup: AI Hub

**AI > AI Hub...** opens a five-tab settings dialog that replaces the old single-screen AI Connection dialog.

- **Provider tab.** Choose your AI provider: Anthropic Claude, OpenAI, Google Gemini, OpenRouter (access to many models through one key), or Ollama (on-device or self-hosted). Enter your API key once; it is stored in the Windows Credential Manager and never written to disk. Choose a model, set a custom host for self-hosted deployments, and use Test Connection to verify the key and model before leaving the dialog.
- **On-Device tab.** If you want AI with no cloud traffic at all, point Ollama at a local URL. The tab lists recommended models with size and capability notes so you can choose what fits your hardware.
- **Audio Services tab.** Enter a Deepgram API key for transcription and set the maximum number of simultaneous speakers the transcription engine should track.
- **Instructions tab.** Edit or replace the built-in system prompt for any of the twelve AI tasks. See "Custom Instructions" below.
- **Advanced tab.** View the consent text you agreed to at setup, reset AI settings, and read a note about Safe Mode.

### Grammar and spell checking with AI

**Tools > Check Grammar with AI** sends the document or selection to your configured AI and returns a structured list of grammar issues, each with the original phrasing, a suggested fix, and an explanation. A result dialog presents them as a navigable list. Apply a fix to jump to the location and insert the correction; skip any item you want to keep.

**Tools > Check Spelling with AI** works the same way for spelling. The AI model returns suggestions with context, making it useful for technical documents where a traditional word-list checker produces false positives.

Both checkers fall back gracefully: if AI is not configured, QUILL uses the built-in lexical spell checker.

### Rewrite, Summarize, Expand, and Table of Contents

Four agentic writing tasks operate on your document text and return results through a shared result dialog.

- **AI > Rewrite Selection** (or the full document if nothing is selected) rewrites the text for clarity and flow, preserving meaning and adjusting register.
- **AI > Summarize Selection** condenses the selected text or document into a tight summary.
- **AI > Expand Selection** develops the selected text into fuller, well-structured prose.
- **AI > Generate Table of Contents** analyses the document structure and produces a hierarchical TOC that you can insert at the cursor.

All four commands open a two-part result dialog: a step log at the top (showing what the agent did and any intermediate output) and the final output in a large read-only text area below. From the dialog you can insert the output at the cursor, replace the selection, copy to the clipboard, or re-run the task. Every agent run starts on a background thread; a stop event lets you cancel between steps.

### AI Thesaurus

**Ctrl+Alt+Shift+H** opens the AI Thesaurus. Type a word or use the word already under your cursor; the dialog sends the word and its surrounding sentence to your AI provider and returns a list of synonyms, each with a usage note explaining the register, connotation, or context. Arrow through the list, press Enter or the Replace Word button to substitute the word in your document, or copy a synonym to the clipboard. Double-clicking a synonym replaces it immediately and closes the dialog.

The context sentence is extracted automatically from the line where your cursor rests, giving the AI enough context to distinguish between, for example, "bank" (financial) and "bank" (river).

### Document Q&A

**AI > Document Q&A** opens a multi-turn question-and-answer session grounded in your open document. Ask questions; QUILL sends the document text and your question to the AI and streams an answer into the conversation pane. The pane is a screen-reader-navigable document: each question and answer is a separate section you can jump to by heading. Continue asking follow-up questions; the session retains context for the duration of the dialog.

Document Q&A works on any document up to approximately 80,000 tokens. For longer documents, QUILL trims from the middle to keep the beginning and end within the model's context window.

### Translation

**AI > Translate Document** or **AI > Translate Selection** sends the text to your configured AI and returns a translation into a language you choose. A picker shows the available target languages; the list adjusts based on your provider. The translated text arrives in a result dialog from which you can insert it, replace the selection, or copy it. On-device translation through LibreTranslate is also available when no cloud AI is configured.

### Read Aloud with AI Voice

**Tools > Read Aloud > Read with AI Voice** sends the selected text to the OpenAI TTS API and plays the audio through the system audio output. Choose from six voices in **AI > AI Hub > Audio Services**. The playback can be stopped at any time. You can also export to an MP3 file from the Read Aloud menu for offline listening.

### Custom Instructions

The Instructions tab of AI Hub has two sub-tabs: **Writing Tasks** and **Image Styles**.

**Writing Tasks** lets you replace or supplement the built-in system prompt for any of QUILL's twelve AI writing tasks. Every task ships with a carefully written default; you can edit the user prompt to change tone, language, output format, or any other behaviour. The twelve tasks are: Chat, Spell Check, Grammar Check, Rewrite, Summarize, Expand, Table of Contents, Translate, Thesaurus, Document Q&A, Research, and Accessibility Agent.

**Image Styles** lets you edit the prompt text for any of Kelly Ford's twelve built-in image description styles. The original shipped prompt is shown read-only below the editor so you always have a reference. Enable or disable individual styles from this same tab.

Your customisations are stored in `%APPDATA%\Quill\ai_custom_instructions.json`. The file stores only the fields you have changed; the built-in defaults always live in the application code. This means that when QUILL updates a default in a future release, you automatically pick up the improved version unless you have already customised that task.

To share a custom instruction set, copy the JSON file to another machine or user account.

To reset a single writing task or image style to its default, select it and press Reset to Default. Your override is cleared; the shipped default takes effect immediately.

### Prompt caching: lower cost, same quality

Custom instructions are sent as a separate system message, not merged into the document text. This lets AI providers cache the stable instruction prefix across requests so you are not billed for re-sending the same text on every call.

- **Anthropic Claude.** QUILL marks the system message with `cache_control: ephemeral` and sends the `anthropic-beta: prompt-caching-2024-07-31` header. Claude caches the prefix for five minutes at approximately 10% of the normal input token rate.
- **OpenAI.** Caching is fully automatic. OpenAI caches prompt prefixes over 1024 tokens at approximately 50% of the normal input rate. Because the system message is always the same stable text, it qualifies for caching whenever the threshold is met.
- **Ollama.** Caching is handled internally by the model server. No configuration is needed.
- **Gemini.** System instructions are sent in the dedicated `systemInstruction` field.

No configuration is needed. The caching path is active whenever at least one custom instruction is enabled.

### AI shortcuts at a glance

| Command | Shortcut |
| --- | --- |
| Ask Quill chat | Alt+Q |
| AI Spell Check | Ctrl+Alt+Shift+S |
| AI Spell Check Interactive | Ctrl+Alt+Shift+I |
| AI Grammar and Style | Ctrl+Alt+Shift+G |
| AI Translate Selection | Ctrl+Alt+Shift+T |
| AI Thesaurus | Ctrl+Alt+Shift+H |
| Check Grammar with AI | Tools > Check Grammar with AI |
| Check Spelling with AI | Tools > Check Spelling with AI |
| Rewrite Selection | AI > Rewrite Selection |
| Summarize Selection | AI > Summarize Selection |
| Expand Selection | AI > Expand Selection |
| Generate Table of Contents | AI > Generate Table of Contents |
| Document Q&A | AI > Document Q&A |
| Translate | AI > Translate |
| Read with AI Voice | Tools > Read Aloud > Read with AI Voice |
| AI Hub | AI > AI Hub... |

The previous inline F7/Shift+F7/F8/Shift+F8/Ctrl+Shift+T accelerators on the
AI menu collided with the selection bindings `edit.start_selection`
(F8), `edit.complete_selection` (Shift+F8), and the QUILL-key
chord for `edit.reselect` (Ctrl+F8). The new chord class is
`Ctrl+Alt+Shift+<letter>` and is reserved for AI commands so power users
can find them by feel; the full allowlist is in
`docs/keybinding-standard.md` §10.2.

### What data leaves your machine

Every AI feature that sends text to a cloud provider shows this in the consent text you agreed to at setup. The full table is in the user guide under AI Privacy Reference. In summary:

- Grammar check, spell check, rewrite, summarize, expand, TOC, thesaurus, Document Q&A, and translation all send the relevant document text or selection to your configured AI provider.
- On-device Ollama sends no data outside your machine.
- AI voice synthesis through OpenAI TTS sends the selected text to OpenAI.
- Audio transcription through Deepgram sends audio to Deepgram's servers.
- Custom instructions are stored locally and are never sent to any provider.

If you prefer not to send document content to a cloud provider, use Ollama on-device and a local Deepgram alternative for transcription.

---

## Experience 13: Dynamic Keyboard Reference

The keyboard reference is no longer a static document. It is generated live from the active command registry and your current feature profile.

The reference now:

- Reflects your actual setup. If you rebind a key or switch to a different keyboard pack, the exported HTML reference updates to show exactly what is bound.
- Documents QUILL's layered keyboard model, including QUILL key prefix chords and dedicated browse-mode, also called Quick Nav, shortcuts.
- Exports as clean semantic HTML designed for high-performance screen-reader review.

---

## Experience 14: Quill Eraser — find invisible mechanical problems before you share

This one came directly from the community. Jayson Smith filed issue #258 with a clear observation: screen reader users working primarily with speech can miss mechanical writing problems that are visually obvious to sighted readers. Two spaces between words. A missing space after a period. A sentence that starts with a lowercase letter because a correction went wrong. You would have to read the entire document character by character to catch those — and nobody does that.

Quill Eraser is the answer. It is a deterministic, rule-based mechanical checker. No AI. No network call. The same input always produces the same output. It is a proofreader for the invisible.

Open it from **Tools → Writing & Language → Quill Eraser...**. Quill Eraser scans the document and opens a modeless review dialog — it stays open while you work in the editor. The dialog lists every finding in a navigable list with confidence levels, line numbers, and the exact text involved.

Seven checks ship in the first release:

- **Multiple spaces between words** — catches double and triple spaces where a single space belongs. High confidence.
- **Trailing spaces at end of line** — finds spaces or tabs left after the last word on a line. High confidence.
- **Space before punctuation** — finds a space immediately before a comma, period, exclamation mark, question mark, semicolon, or colon. High confidence.
- **Excessive blank lines** — reports runs of blank lines beyond the configured maximum (default: two). High confidence.
- **Missing space after sentence-ending punctuation** — a period, exclamation mark, or question mark immediately followed by a letter. Medium confidence.
- **Missing space after comma, semicolon, or colon** — one of those punctuation marks immediately followed by a letter. Medium confidence.
- **Sentence or paragraph starts with lowercase** — catches a capital that was accidentally deleted. Medium confidence.

For each finding you can:

- Press **Apply Fix** to accept the suggested correction and move to the next finding in one keystroke.
- Press **Ignore** to skip it for this session without changing anything.
- Press **Go to Issue** to jump to that position in the editor — the offending text is selected — so you can decide yourself.
- Press **Rescan** after you have made manual edits to refresh the list.
- Press **Previous** or **Next** to move through the list.

Every action is announced. Nothing changes in the document without your explicit confirmation.

**Quill Eraser on Selection...** (also in the same submenu) scopes the check to just the text you have selected. If nothing is selected, it offers to check the whole document.

Quill Eraser never flags content that is legitimately correct. URLs, email addresses, file paths, code spans, decimal numbers, and times are all exempt from every check. When the active document is a Markdown file, fenced code blocks, inline code, YAML front matter, and link URLs are also exempt.

If you open Quill Eraser on a code file — Python, JavaScript, HTML, and so on — a prompt appears before scanning. You can run safe trailing-whitespace checks only, or skip the check entirely. Prose-spacing rules that do not belong in code are suppressed.

Four settings in Preferences let you tune the checker for your writing style:

- **Minimum confidence** — set to `medium` or `low` to see more findings, or keep it at `high` to see only the most certain issues.
- **Allow two spaces after period** — for writers who prefer the traditional two-space sentence gap, this exception suppresses the multiple-spaces rule when exactly two spaces follow sentence-ending punctuation.
- **Maximum blank lines** — raise or lower the threshold for the excessive blank lines rule.
- **Disabled rules** — a comma-separated list of rule IDs if you want to turn off a specific check entirely.

Thank you, Jayson, for a report that was specific, practical, and backed by real daily-use frustration. That is exactly what makes this project better.

---

## Community contribution spotlight: Math Equations by Robert Danaraj

Robert Danaraj approached the QUILL team with a working integration of LaTeX and MathML equation support — a fork that added screen-reader-friendly equation insertion, MathJax rendering in browser preview and HTML export, and comprehensive unit tests. The integration was thoughtful and well-tested. Rather than merging it as a direct core patch, the team worked with Robert to redesign it as a proper sandboxed Quillin, which is the right architectural home for optional format-specific tools.

**Insert → Insert Equation...** (keyboard shortcut: `Ctrl+Shift+E`) is now a bundled Quillin (`com.quill.bundled.math-equations`).

The flow is two steps, both keyboard-first:

1. A prompt opens for the equation text. If you already have a LaTeX equation selected, QUILL strips the delimiters and pre-fills the prompt with the bare formula, so you can edit and re-insert without retyping. Type in LaTeX notation (for example `E=mc^2` or `\int_{a}^{b} f(x) \, dx = F(b) - F(a)`) or paste a MathML fragment starting with `<math`.
2. For LaTeX, a display-mode step asks whether the equation should appear inline (`$...$`) or as a block on its own line (`$$...$$`). If your selection was block-delimited, the block choice is listed first. For MathML, this step is skipped and the fragment is inserted verbatim.

Browser Preview (`Ctrl+Shift+V`) and HTML export now include a MathJax 3 script tag so equations render visually in any browser. The document source always contains the raw LaTeX or MathML, which is what your screen reader announces directly.

Ten worked examples spanning algebra and calculus — the quadratic formula, binomial theorem, fundamental theorem of calculus, integration by parts, Euler's identity, and more — are in `docs/math/latex_testing.md`.

Because this lives as a Quillin rather than in the core, it can be disabled from Quillins Manager if you prefer to keep the equations as raw LaTeX in your document without the Insert Equation dialog. The `Ctrl+Shift+E` binding is released when the Quillin is disabled.

Thank you, Robert, for a contribution that went from a working fork all the way to a tested, properly sandboxed extension. This is the community contribution model working exactly as intended.

---

## More community-requested additions worth knowing

Not every contribution becomes a giant headline. Some become the small improvements that make the editor feel more thoughtful every day. This section collects those practical additions.

QUILL 0.7.0 also includes these practical additions:

- From the QUILL key, press **F** to speak the window title, **P** to speak the full file path, or **Q** to speak a short status summary without leaving the editor.
- **Ctrl+Tab** switches to the next document, and **Ctrl+Shift+Tab** switches back. **Ctrl+Shift+F4** closes all other open documents and keeps just the current one. The **Window** menu lists every open document by number directly on the menu - no submenu. Press **Alt+W** then a number key to jump straight to that document. The active document is marked. The list updates when files open or close, and renames itself immediately when you save an untitled document.

- Open and Save As now start in your Documents folder.
- You can set your own default startup folder in Preferences, so QUILL no longer drops you into the install directory.
- `--goto FILE:LINE:COL` opens a file at a specific position from one argument, which is useful when a linter or search result provides a `file:line:column` string.
- `--diff LEFT RIGHT` opens two files directly into Compare Mode.
- **Help -> Report a Bug...** now opens focused on the Summary field, remembers your name and email after the first entry, and asks which screen reader you use. QUILL preselects the screen reader it detects so the team can reproduce reader-specific issues.
- Feature search now finds copy tray, macros, and abbreviations.
- The Open dialog includes more file types, including common developer extensions such as Kotlin, TypeScript, Go, Rust, and more.
- HEIC and HEIF images are now supported for AI image description.
- The About screen now credits every GitHub contributor, including new project owner Kelly Ford and design contributor Ken Perry.

---

## Fixes that change the day-to-day

A community project gets stronger when people report the rough edges and the team treats those reports as product-shaping feedback. These fixes matter because they remove friction from real daily use.

This release fixes a group of problems that directly affected accessibility, startup reliability, image description, reporting, and platform setup.

### Report a Bug accepts typing and no longer freezes QUILL

Under NVDA, the bug-report fields were refusing keyboard input. The dialog has been rebuilt so every field is editable. It also moved to the Help menu, where users expect support-related commands.

Submitting a report no longer freezes the app while contacting the server. That work now happens in the background with a timeout. The impact is simple: reporting a problem is no longer itself a problem.

### JAWS announces Preferences labels correctly (issue #249)

In previous builds, tabbing through General Preferences with JAWS announced combo box and spin field values but not their labels. The cause was Z-order: on Windows, JAWS finds the accessible name for a combo box or text field by looking backward through the parent window's child list for the nearest `StaticText`. Child windows are ordered by creation time, and the code was creating controls before calling a helper that internally creates the `StaticText` label — so the label ended up after the control in Z-order and JAWS could not find it.

The fix is applied throughout General Preferences, the Profiles and Features dialog, the AI Model dialog, and the new Quillin preferences renderer. Every labeled control is now created inside a factory function that runs after the label is created. `wx.CheckBox` and `wx.Button` are exempt because they carry their own label text. Six gating tests in `tests/unit/ui/test_dialog_label_ordering.py` lock in the correct creation order so this class of regression cannot reappear silently.

### JAWS focus is quieter

JAWS no longer says stray phrases such as `splitter window` and `panel` when menus close or the app receives focus. The invisible layout container is no longer exposed to the screen reader, so focus changes are cleaner and quieter.

### Describe Image with AI works again

A small internal error was silently stopping **Describe Image with AI** from running. The feature now completes as intended, restoring an accessibility feature blind users rely on.

### Startup is faster and quieter

Screen-reader detection now runs in the background instead of stalling the first window. A preview warm-up crash is fixed. The title bar no longer flashes `untitled Quill unavailable` before the app is ready. The preview pane no longer hangs for minutes with no way to close it.

Startup announcements are now opt-in instead of automatic. By default, QUILL speaks only the `QUILL Ready` line at startup; the Document Guardian activation cue and the screen-reader detection result are written to the status bar so sighted and low-vision users still see them, but the screen reader stays quiet unless you ask for more. Two new accessibility settings control the speech:

- **Speech channel (verbosity)** in **Preferences → Accessibility** is the master gate. When off, every spoken announcement from built-in startup events and Quillin extensions is suppressed while the status bar keeps the same text.
- **Speak screen-reader detection result at startup**, also under **Accessibility**, speaks the `Detected screen reader: <name>. Adaptive hints enabled.` line when both that setting and the verbosity gate are on. The status bar still receives the result regardless.

Document Guardian gains its own per-Quillin toggle, **Speak activation and deactivation cues**, on the Lifecycle Announcements tab of **Preferences → Document Guardian**. The setting defaults to off so first-run is quiet for screen-reader users; flipping it on gives you the activation / deactivation cue when the Quillin starts and stops. The status bar still records every enable and disable event.

### First run is more reliable

The first window now comes to the foreground so the trust and privacy dialog is reachable. If you skipped the personalization wizard, you can re-open it later. The wizard's startup beep and Cancel-button focus are fixed.

### Personalize Quill wizard is cleaner

Two setup wizard issues are fixed:

- The **Play sounds for mode changes** checkbox on step 2 now reads with its label instead of as an unlabeled control.
- The profile choices on step 3 now wrap when you arrow past the last one instead of dumping focus onto the Back and Next buttons.

### User guide opens safely

The user guide now opens as a read-only page in your browser instead of as an editable Markdown document you could accidentally change. A stray edit can no longer trigger a `0x8007139f` browser error. A glossary of QUILL terms has also been added to the guide.

### Upgrade prompt for the Braille Pack

The QUILL Braille Pack, which provides braille translation, BRF and BRL export, and liblouis integration, is an optional installer component. Some 0.5.0 users may miss it during upgrade.

On first launch of 0.7.0, QUILL now detects when the pack is absent and offers to run the installer again so you can add it without re-downloading. It uses the copy already in your updates folder. Choose **Not Now** and the prompt goes away permanently. You can still add the pack later by re-running the installer and checking the Braille Pack component.

### Skipped-update notifications work again

If you previously used **Skip this update**, Notification Center was silently reporting `no newer version` instead of reminding you that a skipped update was still waiting. That is fixed.

### macOS keeps API keys correctly

Saving an Ask Quill API key on macOS used to crash. Keys and tokens are now stored in the login Keychain, so you set them up once and on-device or cloud AI continues to work.

### macOS builds install cleanly

The notarized macOS build now signs its bundled image libraries and uses hardened-runtime entitlements, so the app installs without security warnings.

### Startup no longer blocks the UI thread in crash recovery, F1 help, or first preview (issue #179)

The recovery offer dialog, the first F1 help lookup, and the first WebView2 preview could each freeze QUILL for tens of seconds on slower or first-time Windows installations. The freezes blocked the UI thread long enough for the `wx` heartbeat watchdog to fire and for screen readers to time out.

- The crash-recovery snapshot read and `mkdir` are now submitted to the background task pool. The dialog still opens on the UI thread, but the I/O that used to block it no longer does. A failing prepare is reported through the same startup-task-failure channel so a corrupt snapshot does not break startup.
- The help topics file is pre-warmed during deferred startup, so the first F1 press is instant.
- WebView2 dialogs (the update-available dialog and F6 preview) are deferred with a short status nudge when the WebView2 warm-up has not yet finished, so they no longer race the first-time subprocess initialisation.

The dialog-inventory snapshot and dialog-button-contract gates were regenerated as part of the fix; both pass. (#179)

### QUILL browse mode speaks reliably, and you control how much it says

Two related bugs in QUILL browse mode (QUILL key, then **N**) are fixed. Browse mode no longer exits after a single navigation keypress — it now stays active until you press Escape, as designed. And entering and exiting browse mode are announced again: a `pyttsx3`/SAPI5 driver quirk meant the engine spoke the very first announcement of a session and then silently produced nothing on every later one, even though no error was raised. The fix drives the speech engine with its external-loop API instead of repeating `runAndWait()`, which keeps the same driver loop alive for the life of the session. The spoken message when you enter browse mode is also shorter now — it no longer reads every key binding aloud, since **?** already opens the full cheat sheet.

Heading navigation (**H**, and **Ctrl+Alt+1** through **6**) and block navigation previously moved the caret correctly but announced nothing, unlike every other browse-mode element (links, lists, tables, paragraphs, and so on). Heading and block moves now speak through the same path as the rest of browse mode.

A new setting, **QUILL browse move detail** (**Preferences -> Navigation**), controls how much a browse-mode move tells you once it completes: *Line and column* (the default, unchanged from previous releases), *Line only*, or *Say nothing*.

---

## What works differently now

Most habits carry forward, but a few items moved or changed so QUILL can stay cleaner, more discoverable, and easier to grow.

### Braille commands moved under Tools

The top-level **Braille** menu is gone. All braille commands now live under **Tools -> Braille**, including status, navigation, page tools, and translation. The commands are still present; they simply live alongside the other authoring tools.

### Translation menu is dynamic

The old flat list of UEB items has been replaced with a structured menu:

- **UEB**.
- **Standard American English (Legacy)**.
- **More Languages**, built from the installed pack's profiles.

If you used to reach a translation item by position, check the new structure the first time you open it.

### No Install Braille Pack item in the menu

The Braille menu no longer includes **Install Braille Pack**. The pack is now selected during the QUILL installer. Check the Braille Pack component in the installer if you want translation. Once installed, the Translation submenu appears automatically.

### Report a Bug moved near Check for Updates

**Report a Bug** now sits immediately before **Check for Updates** in the Help menu, matching where most people look for support and maintenance items.

### Two entity commands now have two different jobs

The older **Encode HTML Entities** command still escapes only the five markup characters: `<`, `>`, `&`, `"`, and `'`.

The new **Convert Non-ASCII to HTML Entities** command handles accents and symbols. If you previously reached for the old command expecting it to fix accented text for Pandoc, use the new command instead.

### Insert Date and Time is now a submenu

The old flat **Date and Time** and **Calculated Date...** items have been replaced by one **Insert -> Date and Time** submenu.

That submenu includes:

- Insert Date.
- Insert Time.
- Insert Date and Time.

The bundled `com.quill.bundled.insert-tools` Quillin owns this submenu. It is now the canonical home for date and time snippets and is the model for migrating other built-in conveniences into Quillins.

### Sound remains opt-in

Most earcons are off until you choose a sound pack and enable events. Existing setups should not get noisier on upgrade. Turn sound on from **Preferences -> Sound** and **Tools -> Reading & Dictation -> Sound Events...**.

### Indentation tones default to Off

Indentation tones do not play until you pick a scale. Code files remain silent unless you ask QUILL for tone feedback.

### Dictation device picker deferred to 0.7.1

The **Choose Dictation Device** menu entry that earlier 0.7.0 drafts planned to ship has been pulled from this release. The infrastructure for choosing a dictation device is already present (`quill.core.dictation.list_dictation_devices` plus the `dictation_device_index` setting), but the menu surface and dialog contract were not finished in time for a quality release. The picker ships in 0.7.1 with a dedicated dialog under **Tools -> Reading & Dictation**. Until then, QUILL uses the system's default dictation input.

### Translations: POT-only ship

QUILL ships the translations template (`quill/locale/quill.pot`) only. No `.po` source translations or compiled `.mo` binaries are bundled. The POT is regenerated for each release so it stays in lockstep with the strings the source actually emits; verify with `pybabel extract -F babel.cfg -k _ -k "ngettext:1,2" -k lazy_gettext --project QUILL --copyright-holder "BITS" -o quill/locale/quill.pot .`. The translation contribution path is documented in `docs/translating.md` and `MAINTAINERS.md`; new language teams open an issue with the `translation` label to onboard.

## Experience 15: EdSharp port — screen-reader-safe heading shortcuts, section-move, list toggle, and a Section status cell

The EdSharp `s:\edsharp.md` review called out two PRs whose accessibility patterns are worth carrying forward: PR #2 (Alt+Shift+Up/Down section-move) and PR #3 (Ctrl+Alt+1..9 heading and list shortcuts). Both shipped in 0.7.0 after a careful revision of QUILL's longstanding screen-reader-safe keybinding rules.

### Move whole sections with `Alt+Shift+Up` and `Alt+Shift+Down`

Pressing `Alt+Shift+Down` while the caret is on a heading moves that heading and its body past the next sibling heading at the same level. Pressing `Alt+Shift+Up` swaps it with the previous sibling. The move announces the heading it swapped with ("Section moved below Meeting Notes") and stays inside the moved section so the caret lands on the same column of the new heading.

Section-move is gated on the active surface. Markdown and HTML documents get the chord. Plain text announces "Section move is only available in Markdown or HTML documents" and the move is skipped. Fenced code blocks are honored: a `# fake` line inside a triple-backtick fence is never promoted to a real sibling, so a fenced code block cannot become an unexpected target.

The chord pair displaced the previous `edit.expand_selection` / `edit.shrink_selection` bindings. Those commands now live on the QUILL-key chord (`Ctrl+Shift+Grave, J` and `Ctrl+Shift+Grave, Shift+J`). Saved user keymaps from older builds are silently routed through `legacy_rebindings` so no one loses muscle memory on upgrade.

### Heading shortcuts at `Ctrl+Alt+1..6`

The six heading shortcuts move from the QUILL-key chord space to `Ctrl+Alt+1` through `Ctrl+Alt+6` — the Office convention called out in EdSharp PR #3. Each chord carries an inline `# §edsharp-ok` justification comment naming the screen-reader binding it overrides (NVDA's switch-to-synth-1..6), and a paired entry in `_CTRL_ALT_DOCUMENTED` in the menu-lint gate.

Users who want both behaviours can keep the QUILL-key chord in their personal keymap; the legacy_rebindings entry rewrites the older `Ctrl+Shift+Grave, 1..6` saved binding to the new `Ctrl+Alt+1..6` automatically on load.

### List toggle at `Ctrl+Alt+7` and `Ctrl+Alt+8`

`Ctrl+Alt+7` toggles a bullet list and `Ctrl+Alt+8` toggles a numbered list. Each chord inspects the caret: if it is on a line that is already a list item, the markers are stripped and the line returns to plain text; otherwise a new list is inserted. The announcements are short and consistent — "Bullet List removed", "Numbered list applied (with numbers)" — so screen-reader users get immediate confirmation without scanning a long status string.

A new setting, `list_auto_fill_numbers`, controls the numbered-list auto-fill behaviour. When the active document is markdown the inserted list always gets `1. `, `2. `, `3. ` … markers (the markdown surface rule). When the setting is on, auto-fill applies in any markup kind. A third path — pressing `Ctrl+Alt+8` once on a document — sets a per-document five-minute arming flag so subsequent insertions keep filling even when the writer navigates away from the chord. All three paths OR together in `should_auto_fill_numbers()`; outside of them, today's behaviour of one marker on the first item is preserved. `Ctrl+Alt+9` for link insertion is intentionally not added because `Ctrl+K` already covers that command.

### A new "Section" cell in the status bar

The status bar gains a `Section` cell that reads `Section: Heading N (ordinal of total)` whenever the caret is inside a heading section in a Markdown or HTML document. The cell is hidden by default so it does not push other useful cells out of the bar for writers who do not work at heading-level granularity; opt in via Preferences -> Status Bar and place the `Section` cell where it helps. The cell is a no-op for plain-text documents and for carets on a non-heading line, and it inherits the same dead-widget guard as the other live-editor cells so a queued caret event after Ctrl+F4 cannot crash the status-bar refresh.

### The revised §10.8 Ctrl+Alt+ policy

The original §10.8 policy banned `Ctrl+Alt+` outright. The 0.7.0 revision relaxes the rule but keeps the gate strict: a `Ctrl+Alt+` binding may enter `DEFAULT_KEYMAP` when it is in the `_CTRL_ALT_DOCUMENTED` allowlist **or** carries an inline `# §edsharp-ok` justification comment naming the screen-reader binding it overrides. Unjustified bindings still fail the gate.

The full audit lives in the new `docs/keybinding-standard.md` document. The escape hatch is per-binding so future one-off exceptions do not need a code change in `menu_lint.py`.

### Copy Tray binding drift guard

A new `quill.tools.check_copy_tray_binding` gate ensures the 12 Copy Tray paste slots (Ctrl+Shift+1..9, Ctrl+Shift+0, Ctrl+Shift+-, Ctrl+Shift+=) keep their default bindings. A future change that reassigned any of those chords would now fail the gate. The gate is automatically delegated from `menu_lint` so a single `python -m quill.tools.menu_lint` invocation covers all keymap and menu structural invariants.

## Experience 16: QUILL Key branding and menu label clarity

The QUILL Key is the editor's signature feature — a `Ctrl+Shift+Grave` prefix that opens the chord language for power-user workflows. In 0.7.0 it gets a brand and a CI guarantee that every menu item shows its keybinding.

### The chord is now `QUILL Key + <key>`

Where 0.6.x showed the raw `Ctrl+Shift+Grave, S` form in menus, the Keyboard Reference page, the QUILL Key Help dialog, the cheat sheet, and the status bar, 0.7.0 shows `QUILL Key + S`. The user-visible string moves; the stored binding does not. `DEFAULT_KEYMAP`, `keymap.json`, the `quill_key_binding` setting, the `legacy_rebindings` comparison table, and any saved `keymap/profile_*.json` still hold the same `Ctrl+Shift+Grave, <key>` grammar. Only the display layer rewrites the prefix, through a single function — `quill.core.keymap_format.format_binding_for_display` — so the entire product speaks the same label.

The constant `QUILL_KEY_LABEL = "QUILL Key"` lives in `quill/branding.py` and is the single source of truth. Status-bar messages, the cheat sheet, the dialog title, the announce message that fires when the prefix is pressed, and the parameter that `build_cheat_sheet` accepts all read from it. Rebrand the product once in `branding.py` and the QUILL Key label follows.

A second helper, `format_quill_key_chord(prefix, second_key)`, composes a chord from a prefix and a second key without inspecting a stored binding string. Power-user status bar code that needs to mention a chord without one in hand can use it directly.

### A 4th `menu_lint` invariant catches binding/label drift

`quill.tools._check_binding_label_consistency` walks the AST of `quill/ui/main_frame_menu.py` and flags three regression classes:

1. **Empty label through `_menu_label`.** `self._menu_label("", "format.bold")` was the kind of line that previously slipped in and produced a menu slot with no readable name. The gate now refuses to allow an empty title literal for any command that has a `DEFAULT_KEYMAP` binding.
2. **Manual-tab literal drift.** Hand-written labels of the form `<name>\t<binding>` (the wx stock items `Cu&t\tCtrl+X`, `&Copy\tCtrl+C`, `&Paste\tCtrl+V`, `Select &All\tCtrl+A` and the editor's `Close &Other Documents\tCtrl+Shift+F4`, `Help on This &Control\tF1`, `&What Can I Do Here?\tShift+F1`, `Open User &Guide\tCtrl+F1`) are now compared against the `DEFAULT_KEYMAP` entry or the wx stock binding. A drift on either side fails the gate.
3. **Tab with no binding.** A label literal that ends in `\t` (or contains `\t` with nothing after it) now fails the gate. The user used to see a menu name with a trailing tab and no accelerator.

The runtime gap-check in `MainFrame._menu_label` (a one-shot `logger.warning` per affected item at first menu build) is the safety net for user-customization drift. A user who renames a label through the Customize dialog still gets a custom label; only the silent "blank menu slot" case is reported.

The new check is wired into `python -m quill.tools.menu_lint` and exposed via 12 new test cases in `tests/unit/tools/test_binding_label_consistency.py`. The gate is run as part of CI and a regression anywhere in the binding/label chain now fails the build.

### One source of truth for the product name and publisher

`tools/generate_build_info.py`, `scripts/generate_update_feed.py`, and `scripts/build_windows_distribution.py` no longer hard-code the strings `QUILL for All` and `Community Access`. They import `APP_DISPLAY_NAME` and `APP_ORGANIZATION` from `quill.branding` so a rebrand touches one file. The TOML path still wins when `build/version.toml` provides a value (the installer and feed can be re-branded per release), but the constant is the safety net for older checkouts and dev builds. The 0.7.0 Beta 1 installer, About dialog, and update feed continue to read from `build/version.toml`; the constant is the fallback so a missing TOML no longer produces a hard-coded fallback string inside the tool.

## Running QUILL 0.7.0 from source

Some readers want to look at the code, run a fresh build before it lands on the update channel, fix a bug, or write a Quillin against the live API. This section is for them. Everything below assumes a working Python 3.12 or newer interpreter and a checkout of the repository. QUILL targets Windows and macOS; the source build runs on both.

> “If you are reading this and thinking about contributing, you already are. Running the code on your own machine is the first step.”  
> — Jeff Bishop

### What you need before you start

- Python 3.12 or newer. Verify with `python --version`.
- Git, with the QUILL repository cloned locally.
- A working C/C++ build toolchain is **not** required for the default install. The wheels pulled in by `[ui,dev]` ship pre-compiled binaries for Windows and macOS.
- About 1.5 GB of free disk space for the virtual environment, downloaded wheels, bundled Quillins, and the dev test dependencies. The default sound pack and bundled Quillins add roughly 100 MB on top of that.
- Windows 10 or 11, or macOS 12 or newer. Linux is not a supported runtime target in 0.7.0.

### Clone and create a virtual environment

```text
git clone https://github.com/community-access/quill.git
cd quill
python -m venv .venv

# Windows (PowerShell)
.venv\Scripts\Activate.ps1

# macOS / Linux
source .venv/bin/activate
```

Always run QUILL inside the activated virtual environment. The `[ui]` extra pulls in `wxPython`, which is a large native wheel that installs in seconds on Windows and macOS; outside a venv it tends to fight with system Python for global package slots.

### Install QUILL in editable mode with the UI and dev extras

```text
python -m pip install --upgrade pip
pip install -e ".[ui,dev]"
```

That command installs QUILL as an editable package (changes to source take effect on the next launch, no reinstall), brings in the wxPython UI layer, the screen-reader bridges (`prismatoid` on Windows, VoiceOver bridge on macOS), the AI on-device runtime, and the full dev toolchain (`pytest`, `pytest-xdist`, `pytest-timeout`, `pytest-cov`, `ruff`, `mypy`, `Babel`).

If you only want to run the editor without the dev extras, use `pip install -e ".[ui]"` instead. If you also write Quillins and want the Quillin scaffold tool, the example showcase, and the lint gates ready to go, `pip install -e ".[ui,dev]"` is the right choice.

Optional extras you may want on top:

- `pip install -e ".[spellcheck]"` for `pyenchant`-backed spell check.
- `pip install -e ".[ssh]"` for editing files over SSH/SFTP.
- `pip install -e ".[ocr]"` for native Windows OCR.
- `pip install -e ".[kokoro]"` for offline neural TTS.
- `pip install -e ".[github]"` for the GitHub remote-file integration.
- `pip install -e ".[glow]"` for the GLOW accessibility engine. This extra is not on PyPI yet; until it is, follow the comment in `pyproject.toml` and install it from `vendor/wheels`.

### Launch the editor

```text
python -m quill
```

That runs the `quill.__main__:main` entry point defined in `pyproject.toml`. The same script is also exposed as `quill` on `PATH` after the editable install, so `quill` from any shell inside the venv launches the editor.

A few useful launch options:

- `python -m quill --safe-mode` starts QUILL with AI, watch folder, and Quillin contributions disabled. Use this when you are chasing a bug you suspect lives in an extension.
- `python -m quill --goto FILE:LINE:COL` opens `FILE` and lands the caret at the given line and column. Handy when a linter, grep result, or stack trace hands you a `path:line:column` string.
- `python -m quill --diff LEFT RIGHT` opens `LEFT` and `RIGHT` directly into Compare Mode.
- `python -m quill FILE1 FILE2 ...` opens each file in its own tab.

### Run the test suite

```text
# Fast: unit tests only, single-process
pytest -q

# Single file
pytest tests/unit/core/test_paths.py -x -q

# Unit + stability
pytest tests/unit/ tests/stability/ -q

# Parallel (uses pytest-xdist, one worker per CPU)
pytest -q -n auto
```

`tests/conftest.py` sets `quill.core.paths._DEV_BUILD = True` for the whole test session. That is what lets tests redirect `QUILL_DATA_DIR` for isolation; do not remove it. Many tests also depend on the dev extras from `pip install -e ".[ui,dev]"`, so a plain `pip install -e .` will leave the suite red on missing modules.

### Lint and type-check

```text
# Lint
ruff check .
ruff format --check .

# Scoped type-check. Always scoped — never run unscoped mypy.
mypy quill/core quill/io
```

The scoped mypy command covers the strictly typed layers (`quill.core` and `quill.io`). The UI layer (`quill.ui`) is excluded by `pyproject.toml`; it is being typed gradually. Running `mypy .` instead will produce a wall of unrelated noise from the untyped UI and is not useful.

### Verify a Quillin before you publish

```text
python -m quill.tools.quillin_lint path/to/your/quillin --strict
```

The strict mode flags every lint warning, not just the ones that block install. Run it on your Quillin directory before you open a pull request.

### Developer-only environment switches

Three environment variables matter when you run from source. They are honoured only when `QUILL_DEV_BUILD=1` is set; in a release build they are silently ignored.

- `QUILL_DATA_DIR` — override the per-user data directory. In a dev build the override must still live under `Path.home()`; the editor rejects paths outside your home directory to avoid corrupting a real install.
- `QUILL_SAFE_MODE=1` — same as `--safe-mode`. Disables AI, watch folder, and Quillin contributions at startup.
- `QUILL_DEV_BUILD=1` — turns on the developer console (`Tools -> Developer Console`), enables `api.log()` writes from Quillins, and lets `QUILL_DATA_DIR` redirect to a non-default location. Without this flag you are running in release-build behaviour even when launched from a checkout.

### Where to look next

- `CLAUDE.md` at the repository root is the developer quick-reference: architecture, invariants, and the test/lint commands in their canonical form.
- `docs/QUILL-PRD.md` is the long-form product requirements document.
- `docs/keybinding-standard.md` documents the keyboard model and the `Ctrl+Alt+` allowlist policy.
- `docs/planning/` carries the detailed design notes for features that have not shipped yet.
- The GitHub issue tracker is the right place to file bugs, ask questions, or propose a Quillin: <https://github.com/community-access/quill/issues>.

If you find something wrong, **Help -> Report a Bug...** from inside the editor is the friendliest path. The dialog lives in the Help menu now, accepts typing in every field, and submits in the background so the editor does not freeze. Include the output of `python -m quill --version` and, if you can, the crash-report bundle referenced in the dialog.

---

## Closing: community-built, screen-reader-first, and ready for what comes next

QUILL 0.7.0 is more than a list of features. It is proof that accessible software can be joyful, powerful, careful, and community-shaped at the same time.

> “We are building something free, cross-platform, assistive-technology friendly, and community-driven. Wait until you see what contributions are coming next.”  
> — Jeff Bishop

QUILL 0.7.0 is more than a feature release. It is a statement about what an accessible editor can be when screen-reader users are treated as the primary audience, not an afterthought.

This release brings practical power to everyday writing through Insert Automation, typed abbreviations, smart triggers, log mode, citations, Word and RTF export, and better encoding tools. It brings confidence to specialized work through Braille Mode, the optional QUILL Braille Pack, professional translation workflows, page-aware BRF navigation, and status information that speaks the way braille readers actually work. It brings speed to review and development through compare mode, code-aware navigation, indentation tones, dynamic keyboard documentation, and command-line launch options for precise workflows.

Underneath those visible improvements, the new Quillin platform gives QUILL a foundation for growth: accessible preferences, document lifecycle events, status bar contributions, settings search, dependency checks, network safeguards, developer logging, bundled reference Quillins, and strict user control over what extensions can do.

Just as important, 0.7.0 fixes the kinds of issues that matter deeply in daily use: bug reporting now accepts typing, JAWS announcements are quieter, Describe Image works again, startup is faster, first-run dialogs are reachable, the user guide opens safely, update notifications are more reliable, and macOS builds install and store keys correctly.

The result is a release that feels faster, quieter, more predictable, and more empowering. QUILL 0.7.0 gives writers, braille users, developers, students, accessibility professionals, and screen-reader users of every kind a stronger place to work — one built around keyboard control, spoken feedback, user choice, and the belief that accessible software can also be powerful, elegant, and joyful to use.

And this is only the beginning. To everyone testing, contributing code, suggesting workflows, challenging the design, sharing feedback, building community, and cheering QUILL on: thank you. The product is better because of you. The next contributions are already raising the bar.
