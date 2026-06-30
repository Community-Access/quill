# QUILL Story Studio — Organizing Fiction, Novels, and Long-Form Projects

## Proposed Feature Plan, Accessibility Strategy, and Delivery Phases

**Project:** QUILL
**Feature area:** Long-form / manuscript organization (novels, fiction, non-fiction books, research, worldbuilding)
**Primary target:** Windows 11 with wxPython; macOS where QUILL is supported
**Primary accessibility goal:** A genuinely usable way for a blind keyboard user to organize a book-length project — its chapters, characters, plots, places, and brainstorming — without a visual corkboard or mouse-driven board
**Status:** Proposed plan (community-requested; not yet scheduled)

---

## 1. Where this came from

A beta tester asked a simple, important question: *can QUILL be used to organize fiction and novels — character sheets, plots, brainstorming — and not just edit one file at a time?*

Today the honest answer is "partly." QUILL has strong **pieces** for this but no **structure** that ties them into a single project. This document proposes that structure: a **Story Studio** — a screen-reader-first manuscript organizer built entirely on plain-text files and QUILL's existing primitives, not a re-implementation of a visual tool like Scrivener.

The guiding principle matches the rest of QUILL: **optional, additive, plain-text-first, and quiet.** A writer who never opens Story Studio sees no change. A writer who does gets a binder that a screen reader can navigate as naturally as a heading tree.

---

## 2. What QUILL already gives a long-form writer

Before proposing anything new, the plan must reuse what exists. These ship today:

- **Headings as structure.** A manuscript file already uses `#` / `##` for chapters and scenes, and QUILL's structural navigation (Quick Nav, heading jumps) moves through them. This is the spine of a manuscript.
- **Inline notes** (Alt+Shift+I) — sticky, content-anchored annotations that follow the text as it is edited and return on reopen. Ideal for "check this character's eye color" or a margin note on a plot beat.
- **Persistent per-document bookmarks** and **last-cursor-position memory** — named landmarks that survive restarts, per file.
- **Multiple open documents / tabs** — one project can already be several files open at once (manuscript, outline, a character file).
- **The AI Library (Prompts, Skills, Agents)** and **Ask Quill** — for brainstorming, name generation, continuity questions, and "summarize what I know about this character so far," all reviewable and optional.
- **Atomic JSON sidecars** (`core.storage.write_json_atomic`) — the established, safe persistence pattern that Story Studio metadata should follow.

The gap is not capability. The gap is a **project model** that binds these into one navigable whole and adds first-class **non-manuscript elements** (characters, places, plot threads, brainstorming) with light structured fields.

---

## 3. Goals and non-goals

### Goals

- Let a writer group the files of one book into a single **project** with a navigable **binder**.
- Provide first-class **element types** beyond prose: Character, Location, Plot/Thread, Research note, Brainstorm.
- Give each element a small set of optional **structured fields** (e.g. a character's goal, motivation, arc) without forcing a rigid template.
- Keep every word the writer types in **plain, portable text** — no proprietary database that locks the manuscript in.
- Make the entire experience **keyboard- and screen-reader-first**: a tree, lists, and forms, never a spatial corkboard as the only way in.
- Reuse inline notes, bookmarks, and the AI Library rather than re-inventing them.

### Non-goals

- Not a pixel-faithful Scrivener clone; no visual corkboard/freeform board as a required surface.
- No DRM, no closed project format. The project is a folder of readable files plus a small JSON sidecar.
- No forced templates. Structure is offered, never required; a project can be pure prose files with a thin index.
- No new always-on background processing. Story Studio is inert until opened.

---

## 4. Proposed design

### 4.1 The project is a folder

A **Story project** is an ordinary folder containing:

- The writer's **manuscript and element files** as plain `.md`/`.txt` (e.g. `manuscript.md`, `characters/elena.md`, `plots/the-betrayal.md`).
- One **`project.quillstory.json`** sidecar that records the binder order, element types, and structured fields. It references files by **relative path** and never duplicates their prose — the file on disk stays the single source of truth.

Because the project is just files, it works with Dropbox/OneDrive/git, opens in any editor, and survives QUILL entirely. The sidecar is advisory: delete it and you still have all your writing.

### 4.2 The Binder (primary surface)

A **tree view** (native `wx.TreeCtrl`, fully keyboard navigable, each node an announced item) is the home of a project:

```
The Novel (project)
+-- Manuscript
|   +-- Part One
|   |   +-- Chapter 1  (-> manuscript.md#chapter-1)
|   |   +-- Chapter 2
|   +-- Part Two
+-- Characters
|   +-- Elena  (protagonist)
|   +-- Marcus (antagonist)
+-- Places
|   +-- The Old Harbor
+-- Plot threads
|   +-- The Betrayal  (status: unresolved)
+-- Brainstorm
    +-- Possible endings
```

- Manuscript chapters/scenes are **derived from the headings** of the manuscript file(s), so the binder and the prose never drift. Selecting a chapter opens the file at that heading (reusing the existing anchor logic in `browser_preview.preview_anchor_for_text` / `navigation`).
- Character/Place/Plot/Brainstorm nodes open their backing file in the editor.
- The tree is the screen-reader entry point: arrow keys to move, Enter to open, a context menu (and command-palette commands) for add/rename/reorder/delete. **No spatial board is required to use any of it.**

### 4.3 Element types and light structured fields

Each non-manuscript element has an **optional** front-matter block at the top of its plain-text file (YAML-style, human-readable), surfaced in an accessible **details form**:

```markdown
---
type: character
role: protagonist
goal: Reclaim her family's name
motivation: Guilt over her father's exile
arc: From cautious to defiant
tags: [pov, act-one]
---

Elena is ...
```

- The form is a normal stack of labelled fields (each control with an accessible name, errors associated with their field — per QUILL's accessibility rules). Edit in the form **or** in the file; they are the same bytes.
- Field sets per type are a small built-in default the writer can extend. Unknown fields are preserved, never dropped.
- A **"What do I know about X?"** action gathers an element's fields plus inline notes and (optionally) asks the AI for a continuity summary — reviewable, never automatic.

### 4.4 Integration, not reinvention

- **Brainstorming** = a Brainstorm element file plus the existing AI Library. A built-in "Brainstorm" Skill can seed ideas into that file as an accept/reject preview.
- **Annotations** = existing inline notes, now also listed per element in the details form.
- **Landmarks** = existing bookmarks.
- **Compile/Export** = walk the binder order and concatenate manuscript files through the existing export path (`quill/io/export.py`) to produce a single `.md`/`.docx`/`.html`/DAISY output. No new export engine.

### 4.5 Persistence and safety

- `project.quillstory.json` is written with `write_json_atomic` (temp + `os.replace`), schema-validated, and tolerant of a missing/corrupt sidecar (fall back to "folder of files," never lose prose).
- Relative paths only; the project is portable and never stores machine-specific absolute paths.
- Pure model code (a new `quill/core/story/` package, wx-free, strict-typed) with the wx binder/forms in `quill/ui/`. Respects the layered import boundaries in CLAUDE.md.

---

## 5. Accessibility strategy

- **Tree + lists + forms**, never a required visual board. Every node and field has an accessible name; the tree exposes role/level/position.
- **Heading-derived manuscript structure** means the writer navigates the book the same way they already navigate a document — no new mental model.
- **Quiet by default** (consistent with the dialog-announcement and preview-refresh work): the binder does not chatter on every selection beyond the node label; bulk actions summarize once.
- **Keyboard-complete:** add/move/rename/delete/open all reachable from the keyboard and the command palette, with discoverable shortcuts.
- **No motion, no surprise focus jumps;** opening an element moves focus deliberately to the editor or the form, announced once.

---

## 6. Phased delivery

1. **Phase 1 — Project model + Binder (read-mostly).** `quill/core/story/` model, `project.quillstory.json`, a TreeCtrl binder that groups existing files and derives manuscript structure from headings. Open-on-select. No new element types yet.
2. **Phase 2 — Element types + details form.** Character/Location/Plot/Brainstorm with optional front-matter fields and an accessible form. Add/rename/reorder/delete from the binder.
3. **Phase 3 — Compile/Export across the binder** using the existing export pipeline (single-file `.md`/`.docx`/`.html`/DAISY).
4. **Phase 4 — AI integrations.** Built-in Brainstorm Skill and "What do I know about X?" continuity summaries, all reviewable, all opt-in.
5. **Phase 5 (optional) — Saved views / filters** (e.g. "all POV-Elena scenes," "unresolved threads") built on tags and fields.

Each phase is independently shippable and additive.

---

## 7. Risks and open questions

- **Scope creep toward a full IDE-for-novels.** Mitigation: every phase must justify itself against "could the writer already do this with files + headings + notes?" If yes, only build the binding, not a new subsystem.
- **Heading-derived structure vs. manual reordering.** If chapters live as headings in one file, "reorder chapters" means moving text. Decide early whether Phase 1 reorders within a file, across files, or only reflects file/heading order. Recommendation: reflect order in Phase 1; offer move operations in Phase 2.
- **Front-matter collision** with other tools that use YAML front matter (e.g. static-site generators). Mitigation: namespace QUILL-specific keys and preserve unknown keys verbatim.
- **Where the binder lives in the UI** (a side panel, a dedicated view, or a dialog). Needs a small accessibility spike before Phase 1.

---

## 8. Summary

Story Studio turns QUILL's existing strengths — heading structure, inline notes, bookmarks, multiple documents, and the AI Library — into a coherent, screen-reader-first way to organize a book. It adds a project model and a navigable binder with optional structured elements, while keeping every word in plain, portable text. It is optional, additive, and quiet, in keeping with the rest of QUILL. The recommended first step is a thin Phase 1 (project model + binder over existing files) that proves the navigation model before any new element types are built.
