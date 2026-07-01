# QUILL Accessible Vault — Obsidian Parity, Reimagined for Screen Readers

## A plan to make QUILL a first-class linked-knowledge tool that a blind writer can use better than a sighted one uses Obsidian

**Project:** QUILL
**Feature area:** Personal knowledge management (linked notes, backlinks, vault-wide search, tags, transclusion, templates, daily notes, sync/publish)
**Primary target:** Windows 11 with wxPython; macOS where QUILL is supported
**Primary accessibility goal:** Every capability that Obsidian delivers through a *visual* surface (the graph, the canvas, hover-preview, the sidebar panes) is delivered in QUILL through a *spoken, keyboard-native* surface that is faster and clearer for a screen-reader user — not a lesser fallback, but the primary experience.
**Status:** In progress. **Phases 0–2 are shipped** (a vault you can link and traverse by ear — the single biggest gap closed); Phases 3–7 remain proposed. Builds on and reshapes `quill/core/story` (Story Studio). See §6 for the per-phase status and §10 for what shipped.

---

## 1. Executive summary

Obsidian's power is not its looks. It is a small set of ideas — **every note is a file, every file can link to every other file, and the links are bidirectional and searchable** — wrapped in a visual shell. The visual shell (graph view, canvas, hover-preview) is where sighted users spend attention; it is also where blind users are shut out.

QUILL can own the *ideas* and replace the *shell* with something a screen reader makes effortless. A backlinks graph is, to a screen-reader user, far more useful as a **spoken, navigable "what links here" list** than as a picture. A quick-switcher is more useful **announced and filtered as you type** than as a floating panel. This is the thesis of this plan: **QUILL should not port Obsidian's UI; it should deliver Obsidian's model through accessibility-native affordances that are magical precisely because they are not visual.**

To get there, one reframe is required: QUILL grows from a *document editor* (one file at a time, plus per-project Story Studio binders) into a tool that also understands a **Vault** — a persistent, indexed, always-available body of linked notes. Story Studio's per-book project becomes one *view* over that vault rather than a separate world. Everything else — links, backlinks, search, tags, embeds, templates, daily notes — hangs off the vault and its indexes.

Everything remains **optional, additive, and plain-text-first**. A user who never opens a vault sees the editor they already have. The vault is a folder of ordinary Markdown files with one hidden `.quill/` cache; delete the cache and nothing is lost, delete QUILL and every note still opens in any editor.

---

## 2. The guiding principle: a translation table, not a port

For each Obsidian affordance, we name the accessibility-native equivalent that becomes QUILL's *primary* surface. This table is the north star for every feature below.

| Obsidian (visual) | QUILL (accessible-native, primary) |
| --- | --- |
| Graph view (global picture of links) | **Backlinks list** + **forward-links list** + **"neighborhood" navigator** — spoken, counted, keyboard-walkable. The graph is data, and the data is what matters. |
| Hover-preview of a link | **"Speak linked note"** on a key; **"peek"** the target's first lines in the Spoken Echo without leaving the note. |
| Quick switcher (floating panel) | **Announced fuzzy switcher**: type to filter, result count spoken, arrow + Enter. |
| Search pane with highlighted hits | **Results as an accessible list** of note + line + snippet; Enter opens *at the match*; result count and "search within results" spoken. |
| Tag pane | **Tag index list** with counts; select a tag → notes/blocks list; `#` autocomplete while typing. |
| Live preview / WYSIWYG | Unchanged QUILL philosophy: **plain text with hidden codes**; links stay as `[[text]]` and are *resolved on demand by voice* and in preview/export. |
| Canvas (freeform board) | **Out of scope** as a visual surface; the accessible equivalent (an outline/board of linked notes) is a possible later "Vault Outline," not a canvas. |

The rule: **if a feature only makes sense as a picture, we deliver the underlying relationship as a list and as navigation, and we make that list a joy to move through with a screen reader.**

---

## 3. Architecture and the one refactor

### 3.1 The Vault

A **Vault** is a user-chosen root folder of Markdown/plain-text notes plus a hidden `.quill/` directory holding regenerable indexes and vault settings (mirrors Obsidian's `.obsidian/`, but everything in it is a cache that can be rebuilt from the notes). QUILL remembers the vault(s), can switch between them, opens the vault explorer, and keeps its indexes fresh as notes change.

New wx-free package **`quill/core/vault/`** (strict-typed, IO injected, in `mypy` scope):

- `vault.py` — the Vault model: root path, note enumeration, per-note metadata (title, aliases, out-links, tags, headings, block ids).
- `note.py` — a Note view: resolve its title (front-matter `title`/`aliases`, else H1, else filename), its outgoing links, its tags, its heading and block anchors.
- `links.py` — the **wikilink codec** (parse/serialize `[[Note]]`, `[[Note|alias]]`, `[[Note#Heading]]`, `[[Note#^blockid]]`, and embeds `![[...]]`), coexisting with Markdown `[label](url)` without clobbering it. Dependency-free, tested like the front-matter codec.
- `index.py` — the **indexes**: forward/reverse link adjacency (the backlink graph), tag → notes/blocks, and a title/alias → note resolver (with duplicate-title disambiguation). Incremental: updating one note re-indexes only that note.
- `search.py` — vault-wide full-text search (a ripgrep-backed scan and/or a small inverted index), returning ranked note+line+snippet hits.
- `resolve.py` — link/embed resolution: name → note (case-insensitive, alias-aware, ambiguity-reporting), heading/block anchor → offset, and embed expansion for preview/compile.
- `templates.py` — template store and variable substitution (`{{title}}`, `{{date:FORMAT}}`, `{{time}}`, cursor marker), reusing the Snippet engine's substitution where possible.
- `dailynotes.py` — resolve/create today's (or an arbitrary date's) note from a configurable path pattern and template.
- `storage.py` — persist/refresh the `.quill/` index cache atomically (`write_json_atomic`); tolerant, regenerable, versioned-stamped.

All file reads are injected as callables (as in `quill/core/story`), so the model, indexes, and resolvers are unit-tested without disk or `wx`.

### 3.2 The refactor: Story Studio becomes a view over the vault

Today `quill/core/story` models a *project* (a book) as a folder plus a sidecar. That model is a special case of a vault. The refactor:

- **Generalize** the folder-of-plain-text + advisory-sidecar pattern into `quill/core/vault`. Story Studio's `StoryProject` becomes a **Collection** — a curated, ordered *view* (manuscript spine + character/plot/etc. groups) over notes that live in the vault. A book is "a vault, or a folder within a vault, with a manuscript collection on top."
- The **binder** (`quill/ui/story_studio_dialog.py`) generalizes into (or gains a sibling) **Vault Explorer**: the binder is the *authored* view (chapters, characters); the explorer is the *whole* view (every note, grouped by folder/tag/recency). They share the same `BinderNode`/tree machinery and the same "activate → open at offset" seam.
- Existing Story Studio front-matter fields, compile-to-export, and details form all keep working; they just operate on notes that are now first-class vault citizens with links and backlinks.

This keeps one mental model and one code path, and means links/backlinks/search/tags immediately light up *inside* a manuscript project, not only in a generic notes pile.

### 3.3 Keeping indexes fresh

- Indexing runs on the existing background `stability.task_manager.QuillTaskManager`, never on the UI thread; results are applied via `wx.CallAfter`.
- On note save and on **external change** (QUILL already watches folders and reloads cleanly), re-index only the changed note and patch the adjacency/tag/search structures.
- The `.quill/` cache lets a large vault open instantly; a background re-scan reconciles it. Loss of the cache is harmless (rebuild from notes).
- A visible, cancelable "Indexing vault… N of M" status for first-run of a big vault (disabled in Safe Mode).

---

## 4. Feature designs (each with its screen-reader magic)

### 4.1 The persistent vault and its explorer

**What.** Choose a vault folder once; QUILL remembers it and reopens it. Support multiple vaults and switching between them. A **Vault Explorer** tree lists every note (by folder, and optionally regrouped by tag or recency).

**The magic (SR experience).** Opening a vault announces "Vault <name>: 312 notes, 480 links." The explorer is a `wx.TreeCtrl` where every node is an announced item; "Recent," "Untagged," and per-tag groups are togglable. A **"Go to note…"** command (the quick switcher, §4.4) is the fast path; the explorer is the browse path. No visual sidebar required — it is a first-class window/pane reachable by key and returned from by Escape/F6, exactly like today's preview and binder.

**Model/impl.** `quill/core/vault/vault.py` + a `Vault Explorer` that reuses the Story Studio binder tree. Settings hold the vault list and the active vault. Reuses external-change watching and `_show_modal_dialog`.

### 4.2 Bidirectional links — wikilinks that a blind writer inserts and follows effortlessly

**What.** `[[Note]]`, `[[Note|alias shown]]`, `[[Note#Heading]]`, `[[Note#^blockid]]`. Follow a link to open its target; insert a link with autocomplete.

**The magic (SR experience).**
- **Insert:** type `[[` and an **accessible autocomplete** opens — a real listbox that filters as you type note titles/aliases, announces the highlighted match and the remaining count, and inserts `[[Match]]` on Enter with a spoken "Linked to <note>." Or run **"Insert link to note…"** (a quick-switcher-style picker) from the palette/key. Heading and block targets appear after you type `#`.
- **Follow:** with the caret on a link, press **Follow Link** (a dedicated key) → the target opens at the linked heading/block and QUILL announces "Opened <note>" (or, on ambiguity, an accessible chooser: "3 notes named Draft — choose one"). New-tab and same-tab variants.
- **Create-on-follow:** following a link to a note that does not exist offers "Create <note>?" and makes it (optionally from a template) — the Obsidian "just start linking" flow, spoken.
- **Rename propagation:** renaming a note offers "Update 12 inbound links?" with an accessible summary and one-undo application.

**Model/impl.** `links.py` (parser) + `resolve.py` (name→note, anchors, ambiguity). Editor gestures wire to Follow Link and to the autocomplete popup (reuse the intellisense popup machinery already in `main_frame_intellisense.py`). Links render as real anchors in preview/export via the existing `browser_preview` renderer, extended to resolve `[[...]]`.

### 4.3 Backlinks and unlinked mentions — the graph, spoken

**What.** For the current note: **Linked mentions** ("what links here," with the linking sentence) and **Unlinked mentions** (notes that name this note's title/alias without linking, offering one-key "link it").

**The magic (SR experience).** **Show Backlinks** (a key) opens a pane/dialog: "5 notes link here." Each entry is an announced item reading "<Source note> — …the sentence containing the link…"; Enter opens the source *at that mention*. Unlinked mentions list the same way with a "Link this mention" action. This is the accessible replacement for the graph view and the backlinks pane in one: a walkable, counted, contextual list. A **"neighborhood"** command reads forward-links and backlinks together so you can traverse the web of notes purely by keyboard and ear.

**Model/impl.** Reverse adjacency from `index.py`; the "linking sentence" comes from the source note's text around the link offset (reuse the sentence-context logic already used by the F7 review and inline notes). Unlinked mentions = title/alias string search from `search.py` minus existing links.

### 4.4 Vault-wide search and the quick switcher

**What.** Instant full-text search across every note, and a name-jump quick switcher.

**The magic (SR experience).**
- **Quick switcher** (a prominent key, e.g. a reimagined Go-To-Note): a modal that filters note titles/aliases as you type, **announces the result count** ("7 matches"), arrow to move (each announced), Enter to open. Fuzzy and forgiving.
- **Search:** a vault search that returns an **accessible results list** — note title, line number, and a snippet with the match — where Enter opens the note *at the matching line*. "Search as you type" announces the running count; "search within results" refines; recent searches are remembered. Regex and whole-word options are checkboxes with labels.

**Model/impl.** `search.py` — a `ripgrep`-backed scan when available (fast, no index to maintain) with a small in-process fallback; results ranked (title hits > body hits, recency tiebreak). The quick switcher uses the title/alias resolver. Both surfaces are dialogs through `_show_modal_dialog` with `apply_modal_ids`.

### 4.5 Global tags — a spoken tag pane

**What.** Inline `#tag` and front-matter `tags:`, including nested `#area/subarea`, indexed vault-wide.

**The magic (SR experience).** **Show Tags** opens a list of every tag with counts ("#project — 24 notes; #idea — 51"); selecting a tag lists the notes/blocks carrying it (Enter opens at the tag). Typing `#` offers **tag autocomplete** (existing tags first, announced). A tag can be renamed vault-wide with inbound-count confirmation, like link rename.

**Model/impl.** `index.py` tag map (tag → note/block occurrences), nested-tag aware. Autocomplete reuses the same popup as wikilinks. Ties into Story Studio element tags so a character's `#pov` shows in the vault tag index.

### 4.6 Transclusion, embeds, and block references

**What.** `![[Note]]` embeds a whole note; `![[Note#Heading]]` a section; `![[Note#^blockid]]` a single block. Assign a block id with `^blockid` at a paragraph's end.

**The magic (SR experience).** Because QUILL is plain text, an embed stays as `![[...]]` in the buffer (no silent expansion). But:
- **In preview and on compile/export**, embeds are **expanded** with a spoken/announced "embedded from <note>" boundary, so a compiled manuscript or a shared HTML page contains the real content.
- **"Speak embed at cursor"** reads the transcluded content aloud on demand without altering the buffer.
- **"Resolve embed inline"** pulls the target's text into the document as one undo step, for when you want it materialized.
- **Block references:** an **"Add block reference"** command mints a `^blockid` and copies a `[[Note#^blockid]]` link to the clipboard, announced — so quoting a specific paragraph elsewhere is one gesture.

**Model/impl.** `resolve.py` embed expansion (with cycle detection) feeds the `browser_preview` renderer and `compile_manuscript`. Block ids are parsed by `note.py`.

### 4.7 Templates and daily notes

**What.** Reusable note templates with variables; date-stamped daily notes.

**The magic (SR experience).**
- **Insert template…** — a picker of templates; on insert, any prompts (`{{prompt:Question}}`) are spoken and answered inline; `{{date}}`, `{{time}}`, `{{title}}`, and a cursor marker resolve automatically; focus lands where the cursor marker was, announced.
- **New note from template…** — creates a note (name prompted or derived) pre-filled.
- **Open today's note** — opens (creating from the daily template if absent) the note at the configured pattern (`Journal/{{date:YYYY-MM-DD}}.md`); **Previous/Next daily note** walk the calendar by key, announcing the date and whether it exists.

**Model/impl.** `templates.py` + `dailynotes.py`, extending the existing Snippet Gallery substitution rather than inventing a second engine. Settings hold the templates folder, daily-note folder, date format, and default templates.

### 4.8 Sync and publish

**What.** Obsidian sells hosted Sync and Publish. QUILL keeps files yours and adds accessible helpers.

**The magic (SR experience).**
- **Sync:** QUILL does not host sync; the vault is plain files, so any sync (OneDrive, Dropbox, git) already works, and QUILL's external-change watch reloads safely. We add an optional **Vault Git Sync**: "Sync vault" runs commit/pull/push with an **accessible conflict resolver** (a spoken, itemized "these 3 notes changed both places — keep mine / keep theirs / merge") instead of a diff view. Reuses the existing SSH/remote and safe-subprocess machinery.
- **Publish:** extend the publishing framework two ways — **Publish note** (push a note to the existing WordPress connection, resolving `[[links]]` and embeds to real HTML), and **Export vault as a linked site** (a static HTML site with working links and a generated index, via the existing export/`browser_preview` path). Both announce what will be sent and ask first (network-egress-audited).

**Model/impl.** Git sync via a thin wx-free `vault/sync.py` over `safe_subprocess`; publish via the existing publishing providers + link/embed resolution.

---

## 5. Accessibility standards (the consolidated "magic")

These apply to every feature and are non-negotiable acceptance criteria:

- **Keyboard-complete and palette-discoverable.** Insert link, follow link, backlinks, quick switcher, search, tags, insert template, daily note, sync, publish — each is a registered command with a friendly title, listed in the command palette (PRD principle 8) and assignable in the keymap editor. No mouse-only paths.
- **Spoken counts and outcomes.** "7 matches," "5 notes link here," "#idea, 51 notes," "Linked to <note>," "Opened <note> at Chapter 3." The user never has to *look* to know the result.
- **Contextual, not just positional.** Backlinks and search read the *sentence* around a hit, so the list is meaningful without opening each note.
- **Ambiguity is a spoken choice, never a guess.** Duplicate titles → an accessible chooser; a broken link → "no note named X — create it?"
- **Quiet by default.** Indexing, link updates, and previews never chatter; they announce on explicit action and summarize bulk operations once (consistent with the dialog-transitions and preview-refresh work).
- **Focus is deliberate.** Every new pane/dialog lands focus on its content, returns via Escape/F6, and manages focus per the accessibility rules; the Spoken Echo captures any fleeting announcement.
- **Plain text stays sacred.** The buffer is never silently rewritten; links and embeds live as text and are resolved by voice/preview/export, preserving QUILL's core invariant.

---

## 6. Phased delivery

Each phase is independently shippable, additive, and accessible on its own.

1. **Phase 0 — Vault model + indexing engine. SHIPPED (core).** `quill/core/vault` (model, note parsing, resolver, link index). *Deferred within this phase:* a background/incremental indexer (v1 scans on open), a dedicated Vault Explorer window, and the full Story-Studio-as-collection refactor (the two packages already share the front-matter/heading machinery).
2. **Phase 1 — Wikilinks. SHIPPED.** Parser, Follow Link (open at heading/block), create-on-follow, and an ambiguity chooser. *Deferred:* `[[` autocomplete and preview/export link resolution.
3. **Phase 2 — Backlinks. SHIPPED.** Reverse index + a spoken "What links here" list with linking-line context. *Deferred:* an unlinked-mentions UI (the core `unlinked_mentions` exists), neighborhood navigation, and rename-with-link-update.
4. **Phase 3 — Vault-wide search & quick switcher.** ripgrep-backed search results list + fuzzy name switcher.
5. **Phase 4 — Global tags.** Tag index + tag pane + `#` autocomplete + tag rename.
6. **Phase 5 — Transclusion/embeds/block refs.** Expansion in preview/compile + speak/resolve-inline + block ids.
7. **Phase 6 — Templates & daily notes.** Template engine (extending Snippets) + daily-note navigation.
8. **Phase 7 — Sync & publish.** Vault Git Sync with accessible conflict resolution + Publish note / Export vault as a linked site.

A natural first release milestone is **Phases 0–2** (a vault you can link and traverse by ear) — that alone is the "single biggest missing piece."

---

## 7. Risks and open questions

- **Link resolution ambiguity.** Title-based links break with duplicate titles; path-based links break on move. Recommendation: resolve by title/alias with a deterministic disambiguation (folder proximity, then a spoken chooser), and offer link-update on rename/move. Decide the default early.
- **Index scale and performance.** Large vaults (10k+ notes) need incremental, cached, background indexing; prefer `ripgrep` for search to avoid maintaining a heavy inverted index. Benchmark before Phase 3.
- **Coexistence with the per-document world.** The editor, tabs, bookmarks, and inline notes must keep working unchanged when no vault is open. The vault is additive; guard every entry point behind "a vault is active."
- **Philosophy tension.** We deliberately do **not** adopt live-preview/WYSIWYG; links stay as `[[text]]`. Confirm this is the intended stance (it is what keeps QUILL's plain-text invariant and screen-reader clarity).
- **Wikilink vs Markdown coexistence.** The parser must not mangle `[label](url)`, code spans, or math; needs the same care as the front-matter and thematic-break work.
- **Rename/move propagation** touches many files at once — must be atomic-ish, undoable, and clearly summarized.
- **Migration.** Existing Story Studio projects must open unchanged as vaults/collections; write a one-time, non-destructive adoption path.

---

## 8. Non-goals

- **Graph view and Canvas as visual surfaces.** We deliver the link *relationships* as accessible lists and navigation; we do not build a rendered graph or an infinite visual canvas.
- **A hosted, paid sync/publish service.** QUILL keeps files yours; we add helpers over the user's own sync and the existing publishing framework, not a subscription backend.
- **A second editing paradigm.** No WYSIWYG/live-preview mode; the plain-text, hidden-codes editor remains the one editor.
- **A plugin marketplace rivaling Obsidian's.** Extensibility rides the existing Quillin system; we are not building a new marketplace here.

---

## 9. Summary

Obsidian's magic is a model — files, links, backlinks, search — presented visually. QUILL can take that model and present it **by voice and keyboard**, which for a screen-reader user is not a compromise but an upgrade: a backlinks *list* beats a backlinks *picture*, an *announced* switcher beats a floating one, a *spoken* result count beats a highlighted page. The one real prerequisite is a **Vault** — a persistent, indexed body of linked notes — into which Story Studio folds as a curated view. Build the vault and its indexes first (Phase 0), then links and backlinks (Phases 1–2), and QUILL already closes the single biggest gap; the remaining phases (search, tags, embeds, templates, daily notes, sync/publish) each extend the same backbone. The result is not "Obsidian with a screen reader bolted on," but a linked-knowledge tool designed, from the first keystroke, to be **magical without a screen**.

---

## 10. What shipped so far (Phases 0–2, 2026-06-30)

The first milestone — a vault you can link and traverse by ear — is complete and documented. It is captured for users in **CHANGELOG.md**, the **release notes** (Accessible Vault), the **user guide** (Tools → Vault), and **PRD §5.89d**.

**Core (`quill/core/vault`, wx-free, strict-typed, TDD).**

- `links.py` — the wikilink codec (`[[Note]]`, `[[Note|alias]]`, `[[Note#Heading]]`, `[[Note#^block]]`, `![[embed]]`), code-span/fence aware, plus `link_at_offset` (caret → link).
- `note.py` — `parse_note` → title (front matter / H1 / stem), aliases, tags (front matter + inline `#tag`), headings, block ids, and outgoing links, with file-relative offsets.
- `vault.py` — `scan_vault` walks a folder into `NoteInfo` + raw texts, skipping the `.quill` cache.
- `resolve.py` — name/anchor resolution reporting **unresolved** (→ create-on-follow) and **ambiguous** (→ a spoken chooser, never a guess).
- `index.py` — forward/reverse adjacency, `backlinks()` with linking-line context, and `unlinked_mentions()`.

**UI (`quill/ui/main_frame_vault.py`, `quill/ui/vault_dialogs.py`).** `Tools → Vault`: **Open Vault...**, **Follow Wikilink**, **Show Backlinks** (accessible list, spoken count + context), **Insert Link to Note...**. Commands are palette-reachable and assignable; `Settings.vault_root` remembers the active vault.

**Deferred to later phases** (tracked in §6): `[[` autocomplete, preview/export link resolution, an unlinked-mentions UI, neighborhood navigation, rename-with-link-update, a Vault Explorer window, background/incremental indexing, and the full Story-Studio-as-collection refactor — then Phases 3–7 (search + quick switcher, tags, embeds, templates + daily notes, sync/publish).
