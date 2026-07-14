# QUILL Native Google Docs Support
## Product Requirements Document

**Document status:** Draft for product and engineering review  
**Product:** QUILL  
**Feature area:** Cloud Documents / Google Docs  
**Document version:** 1.0  
**Date:** June 25, 2026  
**Primary platform:** Windows 11, wxPython, keyboard-first and screen-reader-first  
**Intended audience:** Product, engineering, accessibility, quality assurance, security, documentation, and release teams

---

## 1. Executive Summary

QUILL will add native support for opening, creating, editing, saving, reviewing, and managing Google Docs documents without embedding the Google Docs web editor and without forcing users to edit Markdown.

The feature will preserve QUILL's central promise: a fast, understandable, text-first editing experience that meets people where they are. Ordinary document text will remain ordinary text. Semantic formatting such as headings, lists, links, and emphasis will be retained as document metadata. Structured objects such as tables, images, footnotes, comments, headers, and document tabs will be represented clearly in the main text surface and edited through focused, purpose-built, keyboard-accessible dialogs.

The Google document, not Markdown and not a flattened local string, will remain the authoritative structured document. QUILL will maintain an internal semantic document model that translates between:

1. The Google Docs API document representation.
2. A provider-independent QUILL semantic document model.
3. A text-first accessible projection shown in QUILL.
4. A journal of semantic edit operations that can be synchronized safely back to Google.

Markdown will be available as an optional view, import/export format, clipboard format, and AI-friendly representation. It will not be the canonical editing or persistence format because Markdown cannot faithfully represent many Google Docs features, including comments, suggestions, complex tables, tabs, images, headers, footers, page structure, and advanced formatting.

The implementation will be delivered incrementally. The initial public release will prioritize reliable paragraphs, headings, basic inline formatting, links, lists, simple tables, document tabs, safe synchronization, conflict detection, recovery, and explicit handling of unsupported content. Later releases will expand support for comments, images, footnotes, headers, footers, offline editing, richer tables, and advanced collaboration workflows.

---

## 2. Product Vision

### 2.1 Vision statement

> Enable people to edit Google Docs through QUILL's accessible, efficient, text-first experience while preserving Google Drive storage, permissions, document structure, and collaboration.

### 2.2 Core product promise

A user should be able to:

- Connect a Google account safely.
- Choose or create a Google document.
- Read and edit its ordinary text as naturally as any other QUILL document.
- Understand when structured content is present.
- Open a clear, accessible editor for a table, list, image, footnote, comment, or other object.
- Save changes without understanding Google API concepts.
- Know whether changes are saved, pending, offline, conflicted, or blocked.
- Recover work after a crash, authentication failure, network failure, or synchronization problem.
- Open the same document in Google Docs when QUILL cannot yet perform an operation.
- Trust that QUILL will not silently destroy unsupported document content.

### 2.3 Experience principles

1. **Text first, not markup first.**  
   Users edit prose, not syntax.

2. **Semantics over visual simulation.**  
   QUILL will represent meaning—heading, list item, table cell, link—not attempt to recreate a page canvas.

3. **Structured content receives structured editors.**  
   Two-dimensional or object-based content is not flattened into unreadable punctuation.

4. **No silent data loss.**  
   Unsupported content is preserved, protected, identified, and never discarded without explicit confirmation.

5. **Accessible by construction.**  
   All core operations must work with the keyboard and expose useful names, roles, states, positions, relationships, and status changes to assistive technology.

6. **Local work is durable.**  
   Keystrokes must not depend on immediate network success.

7. **Synchronization is understandable.**  
   QUILL must communicate state using plain language rather than vague cloud icons or unexplained technical errors.

8. **Progressive capability.**  
   A document remains usable even when it contains features QUILL cannot fully edit.

9. **Provider-independent foundations.**  
   Google Docs will be the first cloud document provider, not a one-off implementation that prevents later Microsoft Word/Graph, Nextcloud, or other integrations.

---

## 3. Background and Problem Statement

Google Docs is widely used for education, employment, community work, and collaboration. A web-based editing surface can be complex for users who prefer a native Windows application, predictable keyboard interaction, direct text navigation, a conventional menu system, or a screen-reader-optimized experience.

QUILL currently provides a text-centric environment. Direct Google Docs support introduces several challenges:

- A Google document is structured, not merely a text file.
- Tables are two-dimensional.
- Headings and lists have semantic properties.
- Images, drawings, charts, headers, footers, and footnotes are objects or separate document segments.
- A document can contain multiple top-level and nested tabs.
- Comments and suggestions have collaboration semantics.
- Other collaborators may edit the document while it is open.
- Google API indexes can shift after edits.
- Some Google Docs capabilities cannot be fully controlled through the public API.
- Network and authentication failures must not lose user work.
- A direct conversion to Markdown would lose fidelity and expose unnecessary syntax.

The product must therefore provide a native text-first projection backed by a structured model rather than treating Google Docs as a remote plain-text file.

---

## 4. Goals

### 4.1 Primary goals

- Provide a first-class **Google Docs document provider** in QUILL.
- Preserve QUILL's existing text-editing speed and accessibility.
- Keep Google Docs as the authoritative cloud document.
- Support safe round-trip editing of common document structures.
- Provide purpose-built accessible editors for structured objects.
- Preserve unsupported content without destructive conversion.
- Provide robust autosave, recovery, conflict detection, and offline queuing.
- Make synchronization state clear through speech, status text, and commands.
- Use least-privilege Google authorization wherever practical.
- Establish a reusable Cloud Document Provider architecture.

### 4.2 Secondary goals

- Support optional Markdown projection, import, export, and clipboard workflows.
- Allow users to open documents by Picker, URL, document ID, recent list, or QUILL history.
- Support multiple Google accounts.
- Support personal Drive and shared drives where the authorized file and account permit access.
- Support comments and replies in a dedicated accessible review experience.
- Allow users to switch quickly between QUILL and the Google Docs web editor.
- Provide diagnostics suitable for user support without logging document content by default.

### 4.3 Success outcomes

The feature is successful when:

- A screen-reader user can open, edit, and save a typical Google document without visiting the web editor.
- A user can encounter a table, understand its dimensions and purpose, read it linearly, and edit it cell by cell.
- A temporary network failure does not interrupt typing or lose work.
- External collaborator changes are either merged safely or presented for accessible review.
- Unsupported objects survive unrelated edits unchanged.
- Users can always determine whether their work is saved.
- The implementation does not require broad access to every file in a user's Google Drive for the normal workflow.

---

## 5. Non-Goals

The following are explicitly outside the initial public release unless separately approved:

- Recreating the full visual Google Docs page layout inside QUILL.
- Pixel-perfect pagination, ruler behavior, margins, print preview, or floating object placement.
- Showing live collaborator cursors, selections, or character-by-character presence.
- Creating, accepting, or rejecting Google Docs suggestions through the API.
- Full editing of drawings, embedded charts, equations, smart chips, or third-party add-on objects.
- Exact fidelity for every Google Docs table style or merged-cell layout.
- Replacing Google Drive as a file-management product.
- Providing a general Google Workspace client.
- Running a mandatory QUILL cloud synchronization service in the first release.
- Storing Google passwords.
- Using service accounts to impersonate ordinary users.
- Flattening all documents into Markdown or DOCX for routine editing.
- Silently replacing an original Google document with a converted copy.

---

## 6. Users and Personas

### 6.1 Primary persona: screen-reader-first writer

A blind user who:

- Uses JAWS, NVDA, or Narrator.
- Prefers predictable native controls.
- Navigates by keyboard.
- Wants direct access to document text.
- Needs concise but informative announcements.
- Finds complex browser application modes burdensome.
- Collaborates in Google Docs because an employer, school, nonprofit, or team requires it.

### 6.2 Keyboard-first power user

A user who:

- Wants fast navigation and editing.
- Prefers menus and shortcuts.
- Uses structured commands for headings, lists, links, comments, and tables.
- May use Markdown but does not want it forced on every document.
- Expects local-editor responsiveness even with remote documents.

### 6.3 Occasional Google Docs user

A user who:

- Primarily uses local files.
- Receives a Google Docs link.
- Wants to open and edit it without learning a new interface.
- Needs clear account and permission guidance.

### 6.4 Collaborative reviewer

A user who:

- Reads comments.
- Replies to discussions.
- Reviews externally changed content.
- Needs to understand unresolved suggestions.
- May need to open the web editor for unsupported collaboration operations.

### 6.5 Organization-managed user

A user whose Google Workspace administrator may:

- Restrict OAuth applications.
- Restrict external sharing.
- Restrict Drive access.
- Require application verification or allowlisting.
- Disable some Google services.

---

## 7. Terminology

- **Cloud document:** A document whose authoritative copy is stored by a remote provider.
- **Provider:** An adapter that implements cloud document operations, such as Google Docs.
- **Semantic document model:** QUILL's internal provider-independent representation of paragraphs, runs, headings, lists, tables, objects, tabs, and document segments.
- **Projection:** The editable text-first representation shown in the main QUILL editor.
- **Object marker:** A protected, meaningful representation of a structured object in the projection.
- **Source span:** The provider-side range or element to which a projected range maps.
- **Projection span:** A range in the QUILL text surface that maps to a semantic node.
- **Operation journal:** Durable local records of user edits awaiting synchronization.
- **Shadow snapshot:** A local copy of the last known provider document model and revision metadata.
- **Revision ID:** A Google Docs value used to control how a write applies relative to collaborator changes.
- **Strict write:** A write using `requiredRevisionId`.
- **Collaborative write:** A write using `targetRevisionId`.
- **Unsupported object:** Content QUILL can preserve and identify but cannot fully edit.
- **Structured editor:** A focused dialog or pane for editing a semantic object such as a table.

---

## 8. Product Scope and Release Levels

### 8.1 Level A: core editable content

Required for the first public release:

- Document metadata and title.
- Document tabs and nested tab navigation.
- Paragraphs.
- Named paragraph styles, especially title, subtitle, and headings.
- Plain text and paragraph breaks.
- Bold, italic, underline, strikethrough, and basic text links.
- Numbered and bulleted lists.
- Simple tables.
- Page breaks and section markers represented safely.
- Basic inline images as preserved objects with accessible metadata.
- Read-only preservation of unsupported objects.
- Autosave, recovery, retry, and conflict handling.
- Open in Google Docs.
- Account connection and disconnection.
- Picker-based file authorization.
- Open by pasted Google Docs URL.
- Creation of new Google documents.

### 8.2 Level B: collaboration and richer structure

Targeted for the next release:

- Comments and replies.
- Comment resolution where permitted.
- Footnotes.
- Headers and footers.
- Image alternative text and description editing where supported.
- Improved table properties and header-row behavior.
- Shared drive workflows.
- Offline editing with robust rebase and conflict review.
- Document outline and structured navigation.
- Enhanced import/export.

### 8.3 Level C: advanced fidelity

Longer-term:

- Merged-cell tables.
- Advanced table style preservation and editing.
- Named ranges and bookmarks.
- Rich links and person/date smart elements where APIs permit.
- Equations as accessible objects.
- Embedded charts and drawings as protected objects with richer metadata.
- Revision comparison.
- Optional event-driven remote change notifications.
- Organization deployment guidance and policy controls.
- Additional cloud providers using the same framework.

---

## 9. User Experience Overview

### 9.1 File menu commands

QUILL will add:

- **File → Open from Google Drive…**
- **File → Open Google Document from Link…**
- **File → New Google Document…**
- **File → Save a Copy to Google Drive…**
- **File → Recent Google Documents**
- **File → Google Account**
  - Connect account…
  - Switch account…
  - Manage connected accounts…
  - Disconnect current account…
- **File → Open Current Document in Google Docs**
- **File → Google Document Properties…**

Commands must be available through menus, keyboard access keys, command palette, and configurable shortcuts.

### 9.2 Document menu commands

- **Document → Google Docs Status**
- **Document → Synchronize Now**
- **Document → Refresh from Google Docs**
- **Document → Review External Changes**
- **Document → Comments**
- **Document → Suggestions**
- **Document → Document Tabs**
- **Document → Structured Objects**
- **Document → Unsupported Content Report**
- **Document → Export Projection**
- **Document → Repair Synchronization…**

### 9.3 Status presentation

The title bar should contain concise state, for example:

- `Project Plan — Google Docs — Saved`
- `Project Plan — Google Docs — Saving`
- `Project Plan — Google Docs — Offline, 3 changes pending`
- `Project Plan — Google Docs — Conflict requires review`
- `Project Plan — Google Docs — Read only`

A detailed status command should report:

- Account.
- Document title.
- Current tab.
- Permission level.
- Save state.
- Last successful synchronization time.
- Number of pending local operations.
- Number of unresolved comments.
- Number of unresolved suggestions.
- Whether unsupported content is present.
- Whether external changes have been detected.

Routine autosave should not produce repetitive speech. State transitions, failures, conflicts, and completed explicit saves should be announced.

### 9.4 Opening a document

Supported entry points:

1. Google Picker in the default browser.
2. Paste a Google Docs URL.
3. Paste a document ID.
4. Recent Google documents previously authorized for QUILL.
5. A `.gdoc` shortcut file, where practical.
6. A future Drive “Open with QUILL” integration.
7. Command-line open using a Google Docs URL.

When a URL is pasted, QUILL will:

- Validate the URL.
- Extract the document ID.
- Determine whether the current account can access it.
- If the file has not been authorized under the chosen scope, launch the authorization/Picker path.
- Open read-only if the user lacks edit permission.
- Explain account mismatch or organization restrictions in plain language.

### 9.5 Creating a document

The New Google Document dialog will request:

- Title.
- Google account.
- Destination, where supported.
- Optional template in a future release.
- Initial tab title, if desired.

After creation, focus moves to the empty editable document body and QUILL announces:

> Google document created. Blank document. Changes will save automatically.

---

## 10. Main Editing Surface

### 10.1 Design decision

The main editing surface will be a **text-first projection** of the semantic document model.

It will not be:

- Raw Google Docs JSON.
- HTML.
- Markdown by default.
- A converted DOCX file.
- A browser-embedded Google Docs canvas.
- A plain-text extraction that discards structure.

### 10.2 Ordinary text

Paragraph text is displayed directly. Paragraph boundaries remain normal line or paragraph boundaries according to QUILL's editor behavior.

Example:

```text
Project Proposal

Introduction

This proposal describes the next phase of the project.
```

Internally:

- `Project Proposal` may be `TITLE`.
- `Introduction` may be `HEADING_1`.
- The final paragraph may be `NORMAL_TEXT`.

Users do not need to see `#`, `**`, HTML tags, or field codes.

### 10.3 Semantic formatting announcements

When entering or querying a paragraph, QUILL can announce:

- Heading level.
- List level and position.
- Quote style.
- Alignment when relevant.
- Link presence.
- Character formatting at the caret.
- Comment or suggestion presence.
- Current document tab.

Announcements must be configurable:

- Minimal.
- Balanced.
- Verbose.
- Custom.

### 10.4 Object markers

Structured objects appear as protected markers, such as:

```text
[Table 1: Project schedule. 4 rows by 3 columns. Press F2 to edit.]

[Image 2: QUILL logo. Alternative text available. Press F2 for details.]

[Footnote 1: Press F2 to read or edit.]

[Unsupported drawing: Preserved. Press Enter for details or open in Google Docs.]
```

Object marker requirements:

- The marker must have a stable semantic node ID.
- The marker text must be localized.
- The marker must not be editable as ordinary text.
- Backspace/Delete on a marker must invoke a confirmation workflow rather than corrupt the marker.
- Copying the marker should offer semantic copy options.
- Screen readers must receive a useful role/name/state.
- Markers must remain discoverable through object navigation.
- Users may configure compact or descriptive marker wording.

### 10.5 Caret and selection behavior

- Left/Right treats a protected object marker as one semantic unit when possible.
- Ctrl+Left/Ctrl+Right moves by text rules without landing inside marker internals.
- Enter on an object opens its default read/review action.
- F2 opens its structured editor.
- Applications/Shift+F10 opens object commands.
- Delete asks whether to remove the object from the Google document.
- Selection across objects is allowed only if the resulting operation can be translated safely.
- Destructive bulk edits crossing unsupported objects require an explicit preservation choice.

### 10.6 Bulk selection safety

When a user selects text containing protected or unsupported objects and presses Delete, Cut, or Paste, QUILL must present a clear dialog:

> The selection contains 2 tables and 1 drawing. Deleting the selection will remove those objects from the Google document.  
> Remove selected text and objects  
> Remove text but preserve structured objects  
> Cancel

The default must be the safest non-destructive action.

---

## 11. Semantic Document Model

### 11.1 Architecture

```text
Google Docs API representation
            ↓
GoogleDocsImporter / Parser
            ↓
QUILL Semantic Document Model
            ↓
Projection Builder
            ↓
QUILL text surface + protected object markers
            ↓
Semantic edit operations
            ↓
GoogleDocsOperationTranslator
            ↓
Google Docs batchUpdate requests
```

### 11.2 Provider-independent node hierarchy

Illustrative model:

```text
CloudDocument
  metadata
  provider_state
  tabs[]
    DocumentTab
      title
      tab_id
      parent_tab_id
      body
        BlockNode[]
      headers[]
      footers[]
      footnotes[]
      unsupported_segments[]
```

Block nodes:

- ParagraphNode
- HeadingNode
- ListItemNode
- TableNode
- ImageNode
- PageBreakNode
- SectionBreakNode
- HorizontalRuleNode, if applicable
- UnsupportedBlockNode

Inline nodes:

- TextRunNode
- LinkNode
- InlineImageNode
- FootnoteReferenceNode
- CommentAnchorNode
- SuggestionAnnotationNode
- UnsupportedInlineNode

### 11.3 Required node properties

Every semantic node must include:

- Stable local UUID.
- Provider-specific identity or source path where available.
- Node type.
- Parent ID.
- Child IDs.
- Current semantic properties.
- Provider source range or location.
- Projection range, when projected.
- Editability level:
  - Fully editable.
  - Partially editable.
  - Read-only preserved.
  - Unsupported protected.
- Dirty state.
- Local version counter.
- Last synchronized hash.
- Diagnostics metadata excluding sensitive content by default.

### 11.4 Document tabs

Google Docs supports top-level and nested tabs. The model must:

- Preserve tab IDs.
- Preserve titles.
- Preserve parent/child relationships.
- Specify `tabId` on applicable update requests.
- Never assume the first tab is the only tab.
- Allow a tab to be loaded lazily if performance requires it.
- Maintain independent projection and cursor state per tab.

### 11.5 Segment support

The model must distinguish:

- Main body.
- Header segments.
- Footer segments.
- Footnotes.
- Other API-exposed segments.

Indexes must never be treated as globally interchangeable across tabs or segments.

---

## 12. Projection Engine

### 12.1 Responsibilities

The Projection Engine will:

- Build editable text from semantic nodes.
- Insert protected object markers.
- Maintain bidirectional mappings between projection spans and semantic nodes.
- Translate text edits into semantic operations.
- Rebuild minimal affected regions after structured changes.
- Restore caret and selection after a rebuild.
- Expose formatting and structure at the caret.
- Reject operations that cannot be represented safely.
- Provide plain-text, Markdown, and diagnostic projections as separate modes.

### 12.2 Mapping model

Each projected span will record:

```text
projection_start
projection_end
semantic_node_id
semantic_offset_start
semantic_offset_end
provider_tab_id
provider_segment_id
edit_policy
```

The system must not depend solely on provider character indexes remaining stable. Google indexes are refreshed or transformed after each applied operation batch.

### 12.3 Edit capture

The editor integration layer will convert UI events into operations such as:

- InsertText
- DeleteTextRange
- SplitParagraph
- MergeParagraphs
- ApplyTextStyle
- ApplyParagraphStyle
- CreateList
- RemoveList
- ChangeListLevel
- InsertTable
- EditTableCell
- InsertTableRow
- DeleteTableRow
- InsertObject
- DeleteObject
- ChangeLink
- ChangeTab
- RenameTab

Operations should describe intent, not low-level offsets alone.

### 12.4 Incremental rebuild

For performance and focus stability:

- Plain text changes should update only the affected paragraph or run mapping.
- List operations should update the affected list region.
- Table edits should update the marker summary and table model.
- Full projection rebuilds should be reserved for external refresh, major conflicts, or model repair.
- A full rebuild must restore the nearest semantic caret position.

### 12.5 Projection integrity checks

In debug and test builds, QUILL will verify:

- Projection spans do not overlap incorrectly.
- Every editable projected character maps to a semantic node.
- Protected markers cannot be partially edited.
- Node parent/child relationships are valid.
- Provider tab and segment IDs are present where required.
- Operation journal entries reference valid semantic nodes.
- Round-trip serialization preserves unsupported nodes.

On integrity failure:

- Stop remote writes.
- Preserve local text and journal.
- Create a recovery snapshot.
- Present a repair workflow.
- Never discard user edits automatically.

---

## 13. Markdown and Other Alternate Views

### 13.1 Markdown position in the product

Markdown is optional and secondary.

Supported commands:

- View → Document View.
- View → Markdown Projection.
- View → Plain Text Extraction.
- Copy as Markdown.
- Paste Markdown into Document.
- Export as Markdown.
- Import Markdown as New Google Document.

### 13.2 Markdown projection warnings

The Markdown projection must identify lossy elements:

```markdown
<!-- QUILL: Complex table preserved but not representable in standard Markdown. -->
[Complex table: 14 rows by 7 columns]
```

Switching to Markdown Projection must not silently make it the source of truth. Direct editing in Markdown Projection may be:

- Disabled initially.
- Enabled only for representable regions.
- Later implemented through a controlled parse-and-merge workflow.

### 13.3 Plain-text extraction

Plain-text extraction is read-only by default and intended for:

- Copying.
- Search.
- AI context preparation.
- Reading without structural markers.
- Export.

It must not be used to overwrite the source document.

---

## 14. Structured Editors

### 14.1 Common structured-editor requirements

Every structured editor must:

- Be fully keyboard operable.
- Use standard native controls where practical.
- Place focus predictably.
- Announce object type and context on entry.
- Provide a clear Save/Apply and Cancel path.
- Preserve changes locally if remote saving fails.
- Report row, column, item, object, or segment position.
- Avoid keyboard traps.
- Support configurable shortcuts.
- Expose validation errors inline and through an error summary.
- Return focus to the originating object marker or semantic position.
- Support Help for the current dialog.
- Avoid relying on color, pointer position, or visual layout alone.
- Be testable with JAWS, NVDA, and Narrator.

### 14.2 F2 behavior

F2 is the default command to edit the semantic object at the caret.

- On ordinary text: open paragraph/style properties or existing QUILL F2 behavior according to context.
- On a table marker: open Table Editor.
- On a list item: open Structured List Editor.
- On an image: open Image Details.
- On a link: open Link Editor.
- On a footnote reference: open Footnote Editor.
- On a comment anchor: open Comment Discussion.
- On unsupported content: open Object Details with safe available actions.

F2 behavior must be discoverable from object announcements and context menus.

---

## 15. Table Experience

### 15.1 Table representation in the document

A table appears as:

```text
[Table 1: Project schedule. 4 rows by 3 columns. Press Enter to read or F2 to edit.]
```

The summary should use, in priority order:

1. Explicit table description or caption.
2. Inferred header text.
3. Nearby paragraph context.
4. Generic numbered label.

Inference must never be saved back as authored content without confirmation.

### 15.2 Table reading mode

Enter on the marker opens a read-only multiline table reader.

Default row-oriented output:

```text
Table: Project schedule
4 rows, 3 columns

Row 1, column headings
Phase
Owner
Date

Row 2
Phase: Design
Owner: Jeff
Date: August
```

Reader options:

- Read by row.
- Read by column.
- Read current cell.
- Include coordinates.
- Include row and column headings.
- Copy as tab-separated values.
- Copy as CSV.
- Copy as Markdown.
- Open Table Editor.
- Open in Google Docs.

### 15.3 Table Editor layout

Recommended controls:

1. Table name/description.
2. Position and dimension status.
3. Current cell context.
4. Multiline cell editor.
5. Navigation controls.
6. Row/column commands.
7. Table properties.
8. Apply and Cancel.

The primary cell editor should be a standard multiline edit control so users can navigate cell content naturally.

### 15.4 Table navigation

Default configurable commands:

- Tab: next cell.
- Shift+Tab: previous cell.
- Ctrl+Right: next column.
- Ctrl+Left: previous column.
- Ctrl+Down: next row.
- Ctrl+Up: previous row.
- Ctrl+Home: first cell.
- Ctrl+End: last cell.
- Alt+Home: first cell in row.
- Alt+End: last cell in row.
- Alt+Page Up: first cell in column.
- Alt+Page Down: last cell in column.
- Ctrl+Insert: insert row after.
- Ctrl+Shift+Insert: insert column after.
- Applications/Shift+F10: table commands.
- Escape: close after save/discard decision.

### 15.5 Cell announcement

On movement:

> Row 3 of 4, column 2 of 3, Owner. Taylor Arndt.

Configurable components:

- Coordinates.
- Row heading.
- Column heading.
- Cell content.
- Blank state.
- Span/merged state.
- Formatting state.

### 15.6 Simple-table definition for initial release

Fully editable when:

- No nested tables.
- No unsupported embedded objects in cells.
- No merged cells, unless read-only preservation is implemented safely.
- Cell content is composed of supported paragraphs, text runs, links, and simple lists.
- The table belongs to a supported segment.

### 15.7 Complex tables

Complex tables are:

- Readable through a linear representation where possible.
- Preserved unchanged.
- Partially editable only when the operation can be isolated safely.
- Clearly labeled with limitations.
- Openable in Google Docs.

Example:

> Complex table, 14 rows by 7 columns, merged cells present. QUILL can read this table but cannot safely change its structure. Cell text editing is available only in unmerged cells.

### 15.8 Table structural operations

Supported API translation includes:

- Insert table.
- Insert row.
- Delete row.
- Insert column.
- Delete column.
- Insert cell content.
- Delete cell content.
- Modify supported row or column properties.
- Pin header rows where supported and implemented.

Each structural operation must use strict revision control unless engineering proves collaborative application safe.

---

## 16. Lists

### 16.1 Normal editing

Lists appear naturally:

```text
1. Improved accessibility
2. Faster document preparation
3. Better collaboration
```

The visible marker may be rendered by QUILL, but list identity and nesting are semantic.

### 16.2 Editing behavior

- Enter creates the next list item.
- Enter on an empty item exits the list.
- Tab and Shift+Tab change nesting only when safe and configured.
- Backspace at the start of an item changes level or removes list formatting with predictable rules.
- Numbering is recalculated semantically.
- Users do not type or manage raw Google bullet IDs.

### 16.3 Structured List Editor

F2 opens an accessible list editor supporting:

- Ordered/unordered style.
- Item navigation.
- Add, remove, duplicate, and reorder.
- Nest and unnest.
- Paste lines as items.
- Convert selected paragraphs to a list.
- Convert list to paragraphs.
- Task-list-like presentation where supported by QUILL, even if represented through a provider-compatible format.

### 16.4 List fidelity

The initial release should support common presets. Unrecognized bullet glyphs or numbering schemes must be preserved and described, not normalized silently.

---

## 17. Headings, Paragraphs, and Inline Formatting

### 17.1 Named paragraph styles

Support:

- Normal text.
- Title.
- Subtitle.
- Heading 1 through Heading 6 where available.
- Quote styles where safely mapped.
- Other styles preserved as custom/unsupported style metadata.

Commands should include:

- Ctrl+Alt+1 through Ctrl+Alt+6 for headings.
- Ctrl+0 or configurable command for normal text.
- Paragraph Style menu.
- Announce current style.

### 17.2 Inline formatting

Support:

- Bold.
- Italic.
- Underline.
- Strikethrough.
- Foreground/background color as semantic properties, with accessible names where feasible.
- Font family and size preservation.
- Link.
- Baseline offset/superscript/subscript where supported.
- Clear formatting.

The default interface should not over-announce visual formatting. Users can query it or enable verbose announcements.

### 17.3 Unsupported formatting

Unknown or advanced style attributes must remain attached to the semantic run and survive unrelated edits.

When editing inside a run with unsupported styling:

- Preserve inherited styling where possible.
- Warn only when the requested operation would discard unsupported properties.
- Offer “preserve existing formatting” as the default.

---

## 18. Links

### 18.1 Link interaction

- Ctrl+K opens Link Editor.
- Enter or a configurable command follows the link after confirmation/preferences.
- F2 on linked text opens Link Editor.
- A command announces link text and destination.

### 18.2 Link Editor fields

- Display text.
- Address.
- Accessible description, if QUILL maintains one locally or the provider supports it.
- Open link.
- Remove link.
- Apply/Cancel.

### 18.3 Safety

- Identify suspicious schemes.
- Never execute unsupported URI schemes without confirmation.
- Announce when display text and destination domain differ significantly.
- Preserve provider rich-link data as an unsupported or partially supported object when it is not a standard URL link.

---

## 19. Images and Embedded Objects

### 19.1 Main-surface representation

Example:

```text
[Image 2: QUILL logo. Alternative text: Blue quill beside the word QUILL. Press F2 for details.]
```

### 19.2 Image Details dialog

Where provider data permits:

- Alternative text.
- Description.
- Caption.
- Source or link.
- Dimensions.
- Replace image.
- Download image.
- Remove image.
- Open in Google Docs.

### 19.3 Initial edit policy

- Preserve all images.
- Allow metadata edits only after round-trip verification.
- Support image insertion later or in a controlled first-release scope.
- Treat floating/positioned images conservatively.
- Never change image position merely because surrounding text changed.

### 19.4 Drawings, charts, equations, and rich embeds

Represent as protected objects:

```text
[Embedded Google drawing: Preserved. Editing requires Google Docs.]
```

Available actions:

- Read metadata.
- Copy accessible description.
- Open in Google Docs.
- Delete with confirmation.
- Replace when implementation is safe.
- Include in unsupported-content report.

---

## 20. Footnotes, Headers, Footers, Sections, and Page Breaks

### 20.1 Footnotes

A reference appears as:

```text
The project began in 2025.[Footnote 1]
```

Enter reads the footnote. F2 edits it in a multiline field.

Requirements:

- Preserve source segment ID.
- Maintain reference-to-footnote relationship.
- Support insert, edit, and delete after API round-trip testing.
- Return focus to the reference.
- Include footnotes in search when configured.

### 20.2 Headers and footers

Access through:

- Document → Headers and Footers.
- Object navigation.
- A dedicated segment selector.

Edit in a normal multiline semantic surface, not inside the main body projection.

### 20.3 Page breaks

Represent with a concise protected marker:

```text
[Page break]
```

Allow insertion and deletion.

### 20.4 Section breaks

Represent:

```text
[Section break: next page]
```

Advanced section properties may be preserved but not fully editable initially.

---

## 21. Document Tabs

### 21.1 Navigation

- Ctrl+Page Down: next document tab.
- Ctrl+Page Up: previous document tab.
- Document → Tabs opens a tree for nested tabs.
- A command announces current tab and position.

Example:

> Tab 2 of 4, Implementation, child of Product Plan.

### 21.2 Tab Manager

Tree-based dialog:

- Search/filter.
- Open selected tab.
- Add tab.
- Rename tab.
- Move/reparent tab when supported.
- Delete tab with content-impact confirmation.
- Open tab in Google Docs.

### 21.3 Focus persistence

QUILL stores:

- Last caret semantic position per tab.
- Last selection per tab.
- Fold/navigation state per tab.
- Last structured object opened per tab when useful.

### 21.4 API rules

Every applicable update must specify the intended `tabId`. The implementation must never rely on Google defaulting to the first tab.

---

## 22. Comments and Discussions

### 22.1 Comments Center

A dedicated accessible dialog will list discussions with:

- Status: open/resolved.
- Author.
- Date.
- Quoted/anchored text where available.
- Comment text.
- Replies.
- Assignment information where available.
- Current tab/context.

### 22.2 Commands

- Next/previous comment.
- Filter open/resolved/all.
- Filter mentions/assigned.
- Reply.
- Edit own comment where permitted.
- Resolve/reopen where API and permissions permit.
- Delete own comment with confirmation.
- Go to anchor.
- Open in Google Docs.
- Copy discussion.

### 22.3 Main-surface presentation

Configurable:

- Hidden, accessible through Comments Center.
- Compact marker.
- Inline expanded marker.
- Announce on caret entry only.

Default should avoid clutter while still announcing that a paragraph or range has comments.

### 22.4 Anchor limitations

Google Drive comment anchors may not provide a complete, stable editable mapping for every Google Docs scenario. QUILL must:

- Use quoted content and anchor metadata where available.
- Treat uncertain anchors as approximate.
- Never jump to a misleading location without saying the match is approximate.
- Offer search for quoted text.
- Open the discussion in Google Docs when precise placement cannot be determined.

---

## 23. Suggestions

### 23.1 API limitation

The Google Docs API can expose suggestions but does not allow applications to create, accept, or reject them programmatically.

### 23.2 QUILL behavior

QUILL will:

- Retrieve documents using an appropriate suggestions view mode.
- Preserve suggestion metadata.
- Provide a Suggestions Review dialog.
- Identify suggested insertions, deletions, and style changes.
- Read a preview with suggestions included, accepted, or rejected.
- Navigate to affected content.
- Open the document in Google Docs to accept or reject suggestions.

### 23.3 Editing around suggestions

Because suggestion view modes affect indexes:

- Synchronization reads must use `SUGGESTIONS_INLINE` when indexes will be used for subsequent updates.
- Editing directly inside unresolved suggested ranges may be restricted in the initial release.
- QUILL must explain the restriction and offer:
  - Edit surrounding text.
  - Open suggestion in Google Docs.
  - View accepted/rejected preview.
- No suggestion metadata may be silently stripped.

---

## 24. Authentication and Account Management

### 24.1 OAuth model

Use Google's OAuth 2.0 installed/desktop application flow.

Requirements:

- Authorization occurs in the user's default browser.
- QUILL never requests or stores the Google password.
- Use Authorization Code flow with PKCE where supported by the selected library and Google configuration.
- Use a loopback receiver or approved HTTPS redirect bridge according to current Google requirements.
- Validate `state`.
- Use exact redirect URI registration.
- Handle user cancellation.
- Support account selection.
- Request offline access only when durable synchronization requires it.

### 24.2 Scope strategy

Default to:

```text
https://www.googleapis.com/auth/drive.file
```

Rationale:

- Per-file access.
- User chooses files.
- Works with Google Docs batch updates.
- Avoids broad access to all Drive files.
- Simplifies trust and verification compared with restricted all-Drive scopes.

The product must not request broader Drive scopes merely to implement a convenient custom global file browser.

### 24.3 Picker workflow

For desktop Picker integration:

- Launch the Google Picker in the default browser.
- Filter to Google Docs MIME type where appropriate.
- Return selected file IDs through the approved callback.
- Exchange the authorization code securely.
- Store authorized file metadata locally for Recent Google Documents.

The Picker flow and account connection flow may need to be coordinated carefully because current Picker desktop guidance imposes scope constraints. Engineering must implement against current Google documentation and automated integration tests.

### 24.4 Credential storage

- Store refresh tokens through Windows Credential Manager via a vetted keyring abstraction.
- Never store tokens in plaintext configuration files.
- Do not include tokens in logs, crash reports, clipboard data, or diagnostics bundles.
- Store access tokens in memory only where practical.
- Clear tokens from memory references on disconnect.
- Support token revocation and local credential removal.
- Distinguish multiple Google accounts by stable account identifier and display email.

### 24.5 Account Manager

Display:

- Account email.
- Connection state.
- Last authorization date.
- Number of documents authorized in QUILL's local history.
- Reauthorize.
- Disconnect.
- Remove local recent-document history.
- Open Google account permissions page.

### 24.6 Organization restrictions

Error guidance must distinguish:

- User denied access.
- Workspace administrator blocked the app.
- File belongs to another account.
- User has view/comment-only access.
- File has been deleted or moved.
- App lacks file authorization.
- OAuth consent is incomplete or unverified.
- Sharing policy prohibits an action.

---

## 25. Google Cloud Project and Distribution Requirements

Before public release:

- Create a production Google Cloud project owned by the appropriate QUILL organization.
- Enable Google Docs API, Google Drive API, and Google Picker API as required.
- Configure OAuth branding and consent.
- Register production desktop client credentials.
- Configure authorized redirect flow.
- Publish privacy policy and terms links.
- Complete required OAuth verification.
- Prepare screen recordings and reviewer instructions if requested.
- Document data use and retention.
- Rotate/revoke compromised credentials.
- Separate development, test, and production Cloud projects.
- Restrict project administration to authorized maintainers.
- Enable audit and budget alerts.
- Track changes in Google API policies and quotas.

Desktop OAuth client identifiers are distributed with the application and must not be treated as confidential secrets. No privileged server secret may be embedded in QUILL.

---

## 26. Cloud Document Provider Architecture

### 26.1 Interface

Illustrative Python protocol:

```python
class CloudDocumentProvider(Protocol):
    provider_id: str

    async def connect_account(self) -> AccountInfo: ...
    async def disconnect_account(self, account_id: str) -> None: ...
    async def choose_document(self, account_id: str) -> DocumentReference: ...
    async def open_document(self, ref: DocumentReference) -> CloudDocumentSnapshot: ...
    async def create_document(self, request: CreateDocumentRequest) -> CloudDocumentSnapshot: ...
    async def apply_operations(
        self,
        session: CloudDocumentSession,
        operations: list[SemanticOperation],
        policy: WritePolicy,
    ) -> ApplyResult: ...
    async def refresh_document(self, session: CloudDocumentSession) -> RefreshResult: ...
    async def get_comments(self, session: CloudDocumentSession) -> list[Discussion]: ...
    async def open_in_provider(self, session: CloudDocumentSession) -> None: ...
    async def get_permissions(self, session: CloudDocumentSession) -> PermissionInfo: ...
```

### 26.2 Google-specific modules

Suggested package structure:

```text
quill/
  cloud/
    contracts.py
    models.py
    operation_journal.py
    recovery.py
    sync_coordinator.py
    conflict_engine.py
    status.py
    providers/
      google_docs/
        provider.py
        auth.py
        picker.py
        docs_client.py
        drive_client.py
        parser.py
        serializer.py
        operation_translator.py
        revision_control.py
        comments.py
        permissions.py
        error_mapping.py
        capabilities.py
  document_model/
    nodes.py
    styles.py
    projection.py
    mappings.py
    operations.py
    validators.py
  ui/
    cloud_documents/
    structured_editors/
```

### 26.3 Dependency direction

- UI depends on provider-independent contracts.
- Semantic model never imports Google client types.
- Google provider translates JSON/resources into internal models.
- Synchronization coordinator operates on semantic operations.
- Provider-specific exceptions are mapped to QUILL error categories.
- No Google-specific conditionals should be scattered through the main editor.

---

## 27. Google API Client Layer

### 27.1 Recommended libraries

Use maintained Google Python libraries where suitable:

- `google-api-python-client`
- `google-auth`
- `google-auth-oauthlib`
- `google-auth-httplib2` or a maintained supported transport
- A vetted keyring package for Windows Credential Manager integration

Pin compatible versions in the release build and run dependency vulnerability scanning.

### 27.2 Threading and async behavior

No network request may block the wxPython UI thread.

Requirements:

- All API work runs in a controlled worker/executor or asynchronous service layer.
- UI updates return through `wx.CallAfter` or the project's approved event mechanism.
- Cancellation tokens stop obsolete refresh/open operations.
- Closing a document flushes or journals pending operations without hanging the UI.
- Worker exceptions are captured and mapped.
- A hung network request has a timeout.
- Retries are bounded and cancellable.

### 27.3 Request fields and performance

- Request only needed fields from Drive.
- Use `includeTabsContent=True` when retrieving full tab content.
- Use `SUGGESTIONS_INLINE` when indexes are needed for updates.
- Batch related Docs updates.
- Avoid a network write for each keystroke.
- Cache immutable metadata cautiously.
- Invalidate cache on external change or permission change.

---

## 28. Synchronization Model

### 28.1 Local-first editing

Typing updates the local semantic model immediately. Network failure must not block the editor.

Pipeline:

```text
User edit
  → semantic operation
  → apply locally
  → append durable journal entry
  → mark pending
  → debounce/coalesce
  → translate to Google requests
  → apply with revision control
  → refresh affected model/revision metadata
  → mark journal entries committed
```

### 28.2 Autosave policy

Recommended defaults:

- Debounce for 2 seconds after typing stops.
- Maximum unsent interval of 10 seconds during continuous editing.
- Flush before:
  - Closing the document.
  - Switching accounts.
  - Explicit refresh.
  - Structural editor close.
  - Opening in Google Docs, when practical.
  - Application shutdown.
- Combine compatible operations.
- Send structural operations promptly after the structured editor applies them.
- Respect API quotas.

These values must be configurable internally and may later be user configurable.

### 28.3 Operation coalescing

Examples:

- Consecutive inserts in the same run become one insert.
- Insert followed by delete of the same unsent text cancels.
- Repeated style toggles collapse to final state.
- Multiple cell edits may batch if no structural dependency exists.
- Operations must not reorder across semantic dependencies.

### 28.4 Durable operation journal

Use a local transactional store, preferably SQLite, with:

- Document ID.
- Account ID.
- Provider ID.
- Base revision ID.
- Local sequence number.
- Operation type and payload.
- Created time.
- Commit state.
- Retry count.
- Last error category.
- Content encryption policy.
- Recovery snapshot reference.

SQLite should use transactions and safe journaling settings appropriate to the application.

### 28.5 Shadow snapshot

Store:

- Last successfully loaded semantic model.
- Provider revision ID.
- Tab metadata.
- Node hashes.
- Unsupported object payloads or sufficient provider representation.
- Permission state.
- Last sync time.

Sensitive document cache behavior must be configurable and documented. Users must be able to clear local cloud-document data.

---

## 29. Revision and Conflict Strategy

### 29.1 Google write controls

Google Docs supports:

- `requiredRevisionId`: fail if the specified revision is not current.
- `targetRevisionId`: apply changes against newer collaborator changes when possible.

### 29.2 Policy

Use **collaborative write** with `targetRevisionId` for carefully bounded text/style operations where:

- The base revision is recent.
- The semantic source span remains valid.
- The operation does not cross unsupported objects.
- The translator can express exact intent.
- Automated tests cover the operation.

Use **strict write** with `requiredRevisionId` for:

- Table structural changes.
- Tab deletion/reparenting.
- Bulk deletion across objects.
- Header/footer/footnote structural changes.
- Unsupported-object-adjacent edits.
- Operations whose safe transformation is uncertain.
- Any operation marked high risk.

### 29.3 Preflight refresh

Refresh before a strict structural write when:

- Base revision is older than a configured threshold.
- A remote-change signal is present.
- The document is actively shared.
- The previous write reported a stale revision.
- The local operation touches a range modified remotely.

### 29.4 Conflict categories

- No conflict: apply normally.
- Auto-merge safe: provider applies against remote changes.
- Text overlap: both sides changed the same semantic range.
- Structural overlap: table/list/tab structure changed.
- Object deletion conflict: one side deleted an object edited by the other.
- Permission conflict: edit rights changed.
- Stale revision: target no longer valid.
- Projection integrity conflict: local mapping cannot be trusted.
- Unsupported-content risk: requested operation may destroy unknown data.

### 29.5 Conflict Review dialog

Must be screen-reader friendly and avoid a purely visual diff.

For each conflict:

- Context before.
- Local version.
- Google version.
- Optional combined proposal.
- Semantic location: tab, heading path, paragraph, table cell.
- Actions:
  - Keep local.
  - Keep Google.
  - Use combined.
  - Edit result.
  - Save local work as a copy.
  - Defer.
  - Open in Google Docs.

Use multiline read-only/edit fields so users can arrow through content.

### 29.6 No-conflict data preservation

Unrelated remote changes must be retained. QUILL must never resolve a conflict by replacing the entire Google document body with its local projection.

---

## 30. Remote Change Detection

### 30.1 Initial approach

The first release will use polling and lifecycle checks:

- Before applying a save batch when needed.
- When the QUILL window regains focus after a meaningful interval.
- On explicit Refresh.
- At a low-frequency interval while a document is open.
- Before high-risk structural operations.

### 30.2 Polling behavior

- Poll metadata/revision indicators, not full content, when possible.
- Back off when the document is idle.
- Stop polling when no Google document is open.
- Do not poll more frequently than necessary.
- Respect metered/offline state when detectable.

### 30.3 Future push notifications

Drive change watches or Google Workspace Events may be considered later. A desktop app may require a public HTTPS receiver or relay service. This is not required for initial release and must undergo privacy, cost, operations, and security review.

### 30.4 User notifications

- Do not interrupt for every remote save.
- Announce when remote changes are incorporated.
- Announce when review is required.
- Provide a count and summary.
- Allow automatic refresh preferences for non-conflicting changes.

---

## 31. Offline and Network Failure Behavior

### 31.1 Offline state

When connectivity is unavailable:

- Editing continues.
- Operations are journaled.
- Title/status says `Offline, N changes pending`.
- Explicit Save says changes are safely stored locally but not yet on Google.
- Structured editors continue to work against the local model when safe.
- Operations requiring a provider fetch are disabled with an explanation.

### 31.2 Reconnection

On reconnect:

1. Refresh remote metadata/revision.
2. Retrieve current document if necessary.
3. Rebase pending operations.
4. Apply automatically if safe.
5. Open conflict review if not safe.
6. Update status and announce outcome.

### 31.3 Authentication expiration

If refresh fails:

- Keep editing locally.
- Mark `Sign-in required, N changes pending`.
- Prompt at a non-destructive moment.
- After reauthorization, resume synchronization.
- Never discard the journal because a token is invalid.

### 31.4 Save as copy fallback

At all times, users can:

- Save pending content as a local QUILL recovery document.
- Export as Markdown.
- Export as plain text.
- Create a new Google document after reauthorization.
- Copy all local text.
- Generate a conflict package for support without credentials.

---

## 32. Permissions and Read-Only Modes

### 32.1 Permission states

- Owner/editor.
- Commenter.
- Viewer.
- Unknown/revoked.
- Organization blocked.

### 32.2 Viewer behavior

- Text and objects are readable.
- Editing commands are disabled.
- Copy/export remains available according to policy and API.
- Status clearly says read-only.
- Open in Google Docs remains available.

### 32.3 Commenter behavior

- Document content is read-only.
- Comment and reply actions are available where permitted.
- Suggestions cannot be created through the Docs API; QUILL must not pretend otherwise.

### 32.4 Permission changes while open

- Preserve unsent local changes.
- Stop writes.
- Explain that access changed.
- Offer save as copy/export.
- Refresh permission state after user action.

---

## 33. Error Handling

### 33.1 Error categories

Map provider failures into stable QUILL categories:

- Authentication required.
- Authorization denied.
- Permission denied.
- File not found.
- File deleted/trashed.
- File not authorized for QUILL.
- Invalid document type.
- Quota/rate limit.
- Temporary Google service failure.
- Network unavailable.
- Timeout.
- Stale revision.
- Invalid operation.
- Unsupported document structure.
- Local cache/journal failure.
- Internal mapping error.

### 33.2 User-facing messages

Messages must answer:

1. What happened?
2. Is the user's work safe?
3. What will QUILL do automatically?
4. What action is available?

Example:

> Google could not save this change because the document changed elsewhere. Your work is safe on this computer. QUILL will refresh the document and ask you to review any overlapping changes.

### 33.3 Retry policy

For 429 and transient 5xx responses:

- Use truncated exponential backoff with jitter.
- Honor provider retry guidance and headers where available.
- Bound retries for foreground commands.
- Continue background retry for journaled work without blocking editing.
- Allow the user to retry now.
- Avoid synchronized retry storms.

Do not automatically retry:

- Permission denial.
- Invalid request caused by a translation bug.
- User cancellation.
- Confirmed file deletion.
- Persistent malformed structure.

### 33.4 Diagnostics

Diagnostic records may include:

- Operation type.
- Provider endpoint category.
- HTTP status.
- Error reason.
- Document ID hashed or redacted by default.
- Revision age.
- Retry count.
- Mapping node type.
- Timing.

Do not log:

- OAuth tokens.
- Authorization codes.
- Full document text.
- Comment text.
- File titles unless the user opts in to a support bundle.
- Email addresses unless explicitly included with consent.

---

## 34. Quota and Performance Requirements

### 34.1 Current Google Docs API considerations

As of this PRD's verification date, Google documents quotas include per-user and per-project read/write limits. The design must not assume unlimited requests.

### 34.2 Performance targets

On a typical supported Windows system:

- Local keystroke response: indistinguishable from a local QUILL document.
- Open progress indication begins within 250 ms.
- First readable content for ordinary documents should appear as early as practical.
- Switching an already loaded tab should feel immediate.
- Structured editor navigation should not make network calls.
- Autosave occurs in the background.
- Closing QUILL should not hang indefinitely on a network operation.

### 34.3 Large documents

For large documents:

- Parse in a worker.
- Provide progress by tab/section.
- Consider lazy projection by tab.
- Avoid quadratic mapping updates.
- Use interval trees, piece tables, ropes, or another suitable span structure rather than repeatedly shifting every later offset.
- Defer expensive unsupported-object analysis.
- Warn before operations that require a full rebuild.

### 34.4 API batching

- Batch compatible edits.
- Keep batches small enough to diagnose and recover.
- Preserve operation ordering.
- Split very large batches.
- On partial design: remember `batchUpdate` validates requests and fails the entire batch if any request is invalid.
- Reconcile returned replies to operation IDs.

---

## 35. Security and Privacy Requirements

### 35.1 Least privilege

- Use `drive.file` by default.
- Do not request broad Drive access for convenience.
- Separate optional capabilities that would require broader scopes.
- Explain scope changes before authorization.

### 35.2 Local data protection

- Credentials in Windows Credential Manager.
- Local cache stored in the user's profile with restrictive permissions.
- Consider encryption at rest for cached content and journals.
- Never place recovery content in a shared temporary directory.
- Securely delete local cache entries where practical when the user chooses Clear Data.
- Do not upload document content to QUILL-operated services by default.

### 35.3 Network security

- HTTPS only.
- Validate TLS normally; no certificate bypass.
- Validate OAuth `state`.
- Use short-lived authorization codes.
- Do not accept callback data from arbitrary origins.
- Avoid exposing a long-lived local callback listener.
- Sanitize provider errors before display/logging.

### 35.4 Content safety

- Treat document content as untrusted.
- Do not execute embedded scripts or macros.
- Sanitize HTML from comments before rendering in rich controls.
- Open links through safe system mechanisms.
- Do not auto-download or open attachments/embedded resources.
- Prevent path traversal in exports/downloads.

### 35.5 Privacy documentation

Publish:

- What data QUILL accesses.
- Why it accesses it.
- Where tokens are stored.
- Whether document content is cached.
- How to clear data.
- How to revoke access.
- Whether diagnostics include content.
- Whether any QUILL server is involved.
- Retention behavior.

---

## 36. Accessibility Requirements

### 36.1 Standards and principles

The implementation should align with:

- WCAG 2.2 AA principles where applicable to any web/callback surfaces.
- Microsoft Active Accessibility/UI Automation expectations for native controls.
- Accessible name, role, value, state, and relationship exposure.
- Keyboard-only operation.
- Predictable focus.
- No dependence on color or visual position.
- Clear error identification and recovery.

### 36.2 Screen-reader support matrix

Required testing:

- JAWS on supported Windows releases.
- NVDA current stable.
- Windows Narrator current stable.
- At least one high-contrast configuration.
- 200% and higher text/display scaling where applicable.

### 36.3 Speech behavior

Use speech/status announcements for:

- Document opened and permission state.
- Current tab on tab switch.
- Save state transitions when important.
- Offline/reconnected.
- Conflict detected/resolved.
- Structured editor entry/exit.
- Table coordinates and headings.
- Unsupported object limitations.
- Errors and recovery safety.

Avoid:

- Speaking every autosave.
- Repeating title/status on every keystroke.
- Dumping raw error codes unless details are requested.
- Emoji-dependent status.

### 36.4 Braille

- Keep status text concise.
- Avoid decorative Unicode.
- Ensure object markers are understandable in braille.
- Expose table coordinates.
- Provide compact marker mode.
- Ensure focus does not jump during background sync.

### 36.5 Focus requirements

- Opening a document places focus at the restored semantic caret or document start.
- Background refresh must not steal focus.
- Applying a structured edit returns to the object marker or logical next position.
- Error dialogs focus the summary.
- Picker browser flow returns focus to QUILL and announces success/cancellation.
- Switching tabs restores tab-specific caret.

### 36.6 Accessibility acceptance gate

No feature may be considered complete until:

- All operations are possible without a mouse.
- Controls have correct accessible names.
- Focus order is logical.
- Screen-reader announcements are useful but not noisy.
- Dialogs are free of keyboard traps.
- Error and conflict workflows are tested.
- Automated accessibility checks and manual testing both pass.

---

## 37. Search, Navigation, and Document Intelligence

### 37.1 Search

Search should operate across:

- Current tab by default.
- All loaded tabs.
- Optional headers, footers, and footnotes.
- Optional comments.
- Object alternative text.
- Unsupported-object descriptions.

Results identify semantic context:

> Tab Implementation, Heading 2 Synchronization, paragraph 4.

### 37.2 Navigation

Add commands/panes for:

- Headings.
- Lists.
- Tables.
- Images.
- Links.
- Comments.
- Suggestions.
- Footnotes.
- Unsupported objects.
- Document tabs.

### 37.3 Document outline

Build from semantic headings per tab. Selecting a heading moves the caret without changing content.

---

## 38. Clipboard, Import, and Export

### 38.1 Copy

Default copy returns human-readable text. Context options:

- Copy.
- Copy with formatting.
- Copy as Markdown.
- Copy as HTML.
- Copy table as TSV.
- Copy table as CSV.
- Copy object description.

### 38.2 Paste

Support:

- Plain text.
- Rich text converted to supported semantics.
- Markdown conversion when explicitly selected.
- Lines to list.
- TSV/CSV to table.
- Google Docs URL to link or open prompt.

Pasting must not import active content.

### 38.3 Export

- Markdown.
- Plain text.
- HTML where supported.
- Local QUILL recovery package.
- Future DOCX/PDF through established export paths, not as the canonical sync path.

Export warnings must list unsupported/lossy content.

---

## 39. Recovery and Crash Safety

### 39.1 Recovery guarantees

Every locally applied semantic operation must be durable within a short bounded interval, independent of Google synchronization.

### 39.2 Startup recovery

On startup:

- Detect uncommitted Google document sessions.
- Show document title/account safely.
- Report pending operations.
- Offer:
  - Reopen and synchronize.
  - Open offline.
  - Export recovery copy.
  - Discard after confirmation.
- Never auto-discard based only on age.

### 39.3 Corrupted cache

If the snapshot is corrupted but journal is intact:

- Retrieve fresh remote document.
- Attempt journal replay.
- If replay cannot map safely, create conflict/recovery document.
- Preserve raw recovery data for support with user consent.

### 39.4 Application shutdown

- Attempt a short flush.
- Do not wait indefinitely.
- Ensure pending operations are committed to local journal.
- State on next launch that changes remain pending.

---

## 40. Settings

### 40.1 Google Docs settings

- Default Google account.
- Autosave enabled.
- Save debounce policy, advanced only.
- Remote change check frequency.
- Automatically apply non-conflicting remote changes.
- Announce save state: minimal/balanced/verbose.
- Object marker detail: compact/standard/detailed.
- Include comments in projection.
- Include suggestion markers.
- Table announcement detail.
- Cache documents for offline use.
- Clear local cloud document cache.
- Open Google links in QUILL when possible.
- Default alternate view.
- Confirm object deletion.
- Confirm bulk edits crossing structured objects.
- Use Google Docs web editor for unsupported actions.

### 40.2 Managed settings

Future organization policies may:

- Disable offline cache.
- Disable account connection.
- Restrict accounts to a domain.
- Disable exports.
- Require explicit save.
- Disable diagnostics content.
- Specify OAuth client/project for managed builds, subject to product/security approval.

---

## 41. Telemetry and Product Analytics

Telemetry must be opt-in or follow QUILL's established privacy policy.

Allowed aggregate events might include:

- Google document opened.
- Document created.
- Structured editor type opened.
- Save succeeded/failed by category.
- Conflict workflow opened.
- Unsupported object type encountered.
- Picker cancelled.
- Recovery restored.

Never collect:

- Document text.
- File title.
- Comment content.
- URLs.
- Email addresses.
- OAuth data.
- Table cell content.

All telemetry names and payloads must be documented and reviewable.

---

## 42. Testing Strategy

### 42.1 Unit tests

- Google JSON to semantic model parsing.
- Semantic model to projection.
- Projection mapping.
- Edit-to-operation translation.
- Operation coalescing.
- Google request generation.
- Revision policy selection.
- Error mapping.
- Object marker protection.
- Markdown/plain-text projections.
- Local journal transactions.
- Recovery replay.
- Tab and segment identity.
- Suggestions index handling.

### 42.2 Golden fixture tests

Maintain anonymized/synthetic Google document fixtures for:

- Plain paragraphs.
- Mixed styles.
- Nested lists.
- Simple tables.
- Complex tables.
- Images.
- Footnotes.
- Headers/footers.
- Multiple nested tabs.
- Comments.
- Suggestions.
- Unsupported elements.
- Right-to-left text.
- Unicode and emoji.
- Very large documents.

Round-trip tests compare:

- Supported semantics.
- Unsupported payload preservation.
- Expected API requests.
- Projection text.
- Mapping integrity.

### 42.3 Mock API tests

Simulate:

- 401 token expiration.
- 403 permission denial.
- 404 deleted document.
- 429 rate limit.
- 5xx service failures.
- Network timeout.
- Stale revision.
- Collaborator edits.
- Permission downgrade.
- Invalid batch request.
- Picker cancellation.
- Account mismatch.

### 42.4 Live integration tests

Use a dedicated Google Workspace test environment with:

- Multiple test accounts.
- Viewer/commenter/editor permissions.
- Shared drive.
- Simultaneous edits.
- Organization policy restrictions.
- Revoked tokens.
- Trashed/restored files.

Live tests must not run against personal user documents.

### 42.5 Accessibility tests

For each workflow:

- Keyboard-only completion.
- JAWS.
- NVDA.
- Narrator.
- Braille display spot checks.
- High contrast.
- Scaling.
- Focus after browser OAuth/Picker return.
- Conflict dialog.
- Recovery dialog.
- Table editor.
- Comments center.
- Tab tree.
- Error states.

### 42.6 Fuzz/property tests

- Random valid semantic trees.
- Random edit sequences.
- Insert/delete around object boundaries.
- Unicode combining characters.
- Surrogate pairs and emoji.
- Bidirectional text.
- Large nested lists.
- Random collaborator edits.
- Journal replay after arbitrary interruption.

Properties:

- No unsupported object disappears unless explicitly deleted.
- Projection-to-model mapping remains valid.
- Applying and replaying operations is deterministic.
- A failed remote write does not alter committed remote assumptions.
- Local user content remains recoverable.

### 42.7 Performance tests

- 10-page ordinary document.
- 100-page document.
- 1,000-paragraph document.
- Hundreds of comments.
- Many tabs.
- Large tables.
- Continuous typing for 30 minutes.
- Repeated network loss/reconnect.
- Slow API responses.
- Memory use across multiple open documents.

---

## 43. Quality Gates and Acceptance Criteria

### 43.1 Core opening

- User can connect an account without entering credentials into QUILL.
- User can select a Google Doc through Picker.
- User can paste a Google Docs link.
- Unauthorized files trigger the correct authorization path.
- View-only documents open read-only.
- Multiple tabs are discovered and navigable.

### 43.2 Editing

- Paragraph edits round-trip correctly.
- Heading changes round-trip correctly.
- Supported character formatting round-trips.
- Links round-trip.
- Lists round-trip.
- Simple table cell text and supported structural edits round-trip.
- Unsupported objects remain unchanged after nearby text edits.
- Main-surface object markers cannot be accidentally corrupted.

### 43.3 Synchronization

- Typing remains responsive without network.
- Pending operations survive a crash.
- Autosave is batched.
- Explicit Sync reports success/failure.
- Stale revisions are handled.
- Non-overlapping collaborator edits are retained.
- Overlapping changes open accessible conflict review.
- No full-document destructive replacement is used as routine conflict resolution.

### 43.4 Accessibility

- Every core workflow completes with keyboard only.
- Focus returns correctly after OAuth/Picker.
- Table editor announces coordinates and headings.
- Status changes are available to screen readers.
- Background sync does not steal focus.
- Object markers are understandable in speech and braille.
- No critical defect remains for JAWS, NVDA, or Narrator.

### 43.5 Security

- Tokens are not stored in plaintext.
- Logs contain no tokens or document content by default.
- OAuth state is validated.
- Broad Drive scopes are not requested in the default workflow.
- Disconnect revokes/removes local credentials as designed.
- Local cache clear works.

### 43.6 Reliability

- Recovery works after forced termination.
- 429 and transient failures back off.
- Invalid provider data fails safely.
- Journal corruption does not silently lose content.
- API errors do not crash QUILL.
- UI thread is never blocked by network calls.

---

## 44. Implementation Plan

### Phase 0: feasibility spike

Deliverables:

- Production-like OAuth desktop proof of concept.
- Picker return flow.
- Open document by ID.
- Parse tabs and ordinary paragraphs.
- Apply a text insertion using revision control.
- Table fixture parse.
- Token storage proof.
- Accessibility review of browser return behavior.
- Written findings on API limitations.

Exit criteria:

- End-to-end text round trip succeeds.
- No broad Drive scope required.
- Clear redirect strategy.
- Confirmed packaging dependencies.
- Confirmed Google verification path.

### Phase 1: semantic foundation

Deliverables:

- Provider-independent semantic model.
- Google parser.
- Projection engine.
- Protected object markers.
- Mapping/integrity validation.
- Operation model.
- Local shadow snapshots.
- Unit/golden tests.

Exit criteria:

- Complex fixtures parse without dropping unknown nodes.
- Projection supports paragraphs, headings, lists, simple tables, images as markers, tabs.
- Unsupported content preservation is demonstrated.

### Phase 2: account, Picker, and open/create workflows

Deliverables:

- Account Manager.
- Secure token store.
- Picker.
- Open by URL.
- Recent authorized documents.
- New Google Document.
- Read-only permissions.
- Open in Google Docs.

Exit criteria:

- Tested with personal and managed Workspace accounts.
- Cancellation and blocked-app errors are accessible.
- Multiple accounts work.

### Phase 3: text editing and synchronization

Deliverables:

- Text/paragraph/style/link/list operations.
- Autosave coordinator.
- Batch translation.
- Revision control.
- Retry/backoff.
- Durable journal.
- Status announcements.
- Crash recovery.

Exit criteria:

- Continuous typing test passes.
- Offline journal survives restart.
- Collaborator non-overlap test passes.
- No UI blocking.

### Phase 4: tables and structured objects

Deliverables:

- Table reader.
- Table Editor.
- Simple structural operations.
- List Editor integration.
- Image details.
- Footnote support as approved.
- Unsupported Content Report.

Exit criteria:

- Table workflows pass screen-reader testing.
- Complex tables are preserved.
- Object boundary deletion is safe.

### Phase 5: conflict and external change workflows

Deliverables:

- Polling/refresh.
- Rebase engine.
- Conflict classification.
- Accessible Conflict Review.
- Save-as-copy fallback.
- Permission-change handling.

Exit criteria:

- Simultaneous edit scenarios pass.
- No data loss across forced conflicts.
- Conflict dialog passes accessibility review.

### Phase 6: comments, suggestions, and richer navigation

Deliverables:

- Comments Center.
- Reply/resolve operations where supported.
- Suggestions Review.
- Outline and object navigation.
- Headers/footers/footnotes as approved.
- Search across tabs/segments.

Exit criteria:

- Collaboration limitations are accurately communicated.
- Comments and suggestions remain preserved.

### Phase 7: hardening and public beta

Deliverables:

- OAuth verification complete.
- Privacy documentation.
- Security review.
- Large-document tuning.
- Full accessibility matrix.
- User documentation.
- Diagnostics bundle.
- Feature flag and rollback controls.
- Beta feedback workflow.

Exit criteria:

- All release-blocking acceptance criteria pass.
- Recovery and downgrade path documented.
- No known data-loss defect.
- No critical accessibility defect.

---

## 45. Feature Flags and Rollback

Feature flags:

- `google_docs_provider_enabled`
- `google_docs_editing_enabled`
- `google_docs_tables_enabled`
- `google_docs_offline_enabled`
- `google_docs_comments_enabled`
- `google_docs_conflict_merge_enabled`
- `google_docs_structural_writes_enabled`

Flags must allow:

- Read-only emergency mode.
- Disabling a faulty operation translator.
- Preserving access to recovery/export.
- Rolling back without deleting journals.
- Targeting beta users.

A rollback must never strand unsent local operations. Older versions should detect newer journal formats and offer export rather than corrupting them.

---

## 46. Documentation and Onboarding

### 46.1 First-run onboarding

Explain:

- QUILL opens chosen Google files only.
- Sign-in occurs in the browser.
- The Google document stays in Google Drive.
- Ordinary text edits normally.
- Press F2 on tables and objects.
- Changes save automatically.
- QUILL preserves unsupported content.
- Some actions still require Google Docs.

### 46.2 Help topics

- Connect a Google account.
- Open a Google document.
- Open from a link.
- Create a document.
- Understand save status.
- Work offline.
- Edit a table.
- Navigate document tabs.
- Review comments.
- Review suggestions.
- Resolve conflicts.
- Handle organization restrictions.
- Clear local data.
- Revoke QUILL access.
- Export a recovery copy.
- Report a problem safely.

### 46.3 In-product teaching

Use short contextual hints, not repeated tutorials:

> Table, 4 rows by 3 columns. Press Enter to read or F2 to edit.

Hints must be dismissible and configurable.

---

## 47. Support and Diagnostics

### 47.1 Google Docs Diagnostics dialog

Show:

- Provider connection state.
- Account, partially redacted.
- Document ID, partially redacted.
- Permission.
- Revision age.
- Pending operation count.
- Last sync result.
- API retry state.
- Local cache path with Open Folder.
- Mapping integrity state.
- Unsupported node counts.
- Copy diagnostics.
- Export support bundle.

### 47.2 Support bundle

Default bundle contains:

- App version.
- OS version.
- Screen reader information if user agrees.
- Dependency versions.
- Redacted logs.
- Error categories.
- Operation types without content.
- Integrity reports.
- Feature flags.

Optional content inclusion must require explicit informed consent and preview.

---

## 48. Open Questions Requiring Product or Engineering Decision

1. Which QUILL text control/editor component will host protected object markers most reliably?
2. Can existing QUILL document abstractions be extended, or is a new semantic document engine required?
3. Should the initial public release allow fully offline editing or only durable pending saves during temporary outages?
4. What local encryption approach should protect cached document content?
5. Should comments be hidden by default or represented with compact markers?
6. How should mixed formatting be announced at the caret?
7. Which simple table properties are essential for release one?
8. Should complex-table cell text editing be allowed when structure is read-only?
9. How should external changes be surfaced when the user is actively typing?
10. What is the preferred OAuth callback architecture for packaged portable and installed builds?
11. Does portable QUILL support secure token storage, or should Google Docs require installed mode initially?
12. Which Google account identity fields can be retrieved without adding unnecessary scopes?
13. Should local recent-document history be encrypted?
14. Should account disconnect revoke the token remotely by default or only remove local credentials?
15. How will QUILL handle documents larger than practical full-model memory limits?
16. Should a cloud document occupy one QUILL editor tab with internal Google document tabs, or map each Google document tab to a QUILL workspace tab?
17. Can the existing QUILL list editor be reused directly?
18. Should alternate Markdown projection be editable in the first release?
19. Which unsupported objects should be launch blockers versus protected placeholders?
20. What privacy and legal entity will own the Google Cloud project and OAuth consent publication?

Recommended defaults:

- Use one QUILL document tab with internal Google tab navigation.
- Make Markdown projection read-only initially.
- Require installed mode for Google Docs if portable credential security cannot be guaranteed.
- Hide comments from the main projection by default but announce their presence.
- Allow complex-table reading, but restrict structural edits.
- Revoke access only after a clear disconnect confirmation.
- Treat any known data-loss path as a release blocker.

---

## 49. Risks and Mitigations

### Risk: semantic model complexity

**Mitigation:** Build provider-independent nodes, operation tests, golden fixtures, and incremental release gates before enabling writes broadly.

### Risk: unsupported content loss

**Mitigation:** Preserve unknown provider payloads, protect markers, use surgical API operations, and prohibit full-document replacement.

### Risk: collaborator conflicts

**Mitigation:** Revision-aware writes, preflight refresh, durable journal, conflict classification, save-as-copy fallback.

### Risk: Google API or policy changes

**Mitigation:** Isolate provider code, monitor release notes, pin/test dependencies, feature flags, annual OAuth review.

### Risk: inaccessible Picker/browser return

**Mitigation:** Test major browsers and screen readers, provide paste-link fallback, announce return state, document the flow.

### Risk: rate limits

**Mitigation:** Debounce, batch, cache, poll conservatively, exponential backoff.

### Risk: token theft

**Mitigation:** OS credential store, no plaintext logs, least privilege, secure callbacks, dependency review.

### Risk: editor focus instability during projection rebuild

**Mitigation:** Semantic caret anchors, minimal rebuilds, focus regression tests, no background focus stealing.

### Risk: portable-build credential security

**Mitigation:** Disable or limit persistent account support until secure storage is proven; provide explicit installed-mode requirement.

### Risk: scope expansion pressure

**Mitigation:** Preserve Picker/per-file authorization as the default; treat broader scopes as a separate reviewed capability.

### Risk: user assumes full Google Docs parity

**Mitigation:** Clear capability report, unsupported markers, onboarding, and “Open in Google Docs” escape hatch.

---

## 50. Definition of Done

The complete implementation is done when:

- The Cloud Document Provider framework is stable and documented.
- Google OAuth and Picker flows are verified and production-ready.
- Google documents can be opened, created, edited, and synchronized.
- The semantic model covers all provider content by supported nodes or preserved unsupported nodes.
- Paragraphs, headings, formatting, links, lists, tables, tabs, and approved structured elements round-trip.
- Autosave, offline journaling, recovery, retries, and conflicts are reliable.
- All unsupported content is protected from accidental loss.
- Core collaboration review workflows are available within API limits.
- Accessibility acceptance tests pass with JAWS, NVDA, and Narrator.
- Security and privacy reviews pass.
- OAuth verification is complete.
- Documentation, onboarding, diagnostics, and support procedures are complete.
- No known critical data-loss, security, crash, or accessibility defect remains.
- Feature flags permit safe disablement and rollback.

---

## 51. Recommended First Public Release Boundary

To avoid an endless implementation while still delivering a meaningful feature, the recommended first public beta should include:

- Secure account connection.
- Picker and paste-link open.
- Create document.
- Multiple Google document tabs.
- Paragraphs and named headings.
- Basic inline formatting.
- Links.
- Numbered and bulleted lists.
- Simple tables with reader and editor.
- Images and advanced objects preserved as markers.
- Suggestions preserved and reviewable, with web handoff.
- Read-only permission support.
- Local operation journal.
- Autosave and manual Sync.
- Temporary offline editing.
- Revision-aware conflict detection.
- Accessible conflict review for text.
- Open in Google Docs.
- Recovery/export.
- Full keyboard and screen-reader support.

Defer from first public beta:

- Advanced table styling and merged-cell structural edits.
- Full comments authoring if anchor behavior is not sufficiently reliable.
- Header/footer structural editing.
- Push notification relay.
- Editable Markdown projection.
- Rich chips, drawings, charts, and equations.
- Full offline rebase for every structural operation.
- Broad Drive browsing that requires broader scopes.

---

## 52. Technical Source Notes

The following official Google documentation informed this PRD. Engineering must re-check current documentation during implementation because APIs, policies, quotas, and OAuth requirements can change.

1. Google Docs API overview  
   https://developers.google.com/workspace/docs/api/reference/rest

2. Google Docs document structure  
   https://developers.google.com/workspace/docs/api/concepts/structure

3. Google Docs document model and methods  
   https://developers.google.com/workspace/docs/api/concepts/document

4. Google Docs `documents.batchUpdate` and `WriteControl`  
   https://developers.google.com/workspace/docs/api/reference/rest/v1/documents/batchUpdate

5. Google Docs request types  
   https://developers.google.com/workspace/docs/api/reference/rest/v1/documents/request

6. Working with Google Docs tables  
   https://developers.google.com/workspace/docs/api/how-tos/tables

7. Working with Google Docs lists  
   https://developers.google.com/workspace/docs/api/how-tos/lists

8. Working with Google Docs tabs  
   https://developers.google.com/workspace/docs/api/how-tos/tabs

9. Working with Google Docs suggestions  
   https://developers.google.com/workspace/docs/api/how-tos/suggestions

10. Google Docs API usage limits  
    https://developers.google.com/workspace/docs/api/limits

11. OAuth 2.0 for desktop applications  
    https://developers.google.com/identity/protocols/oauth2/native-app

12. Google Drive API scope guidance  
    https://developers.google.com/workspace/drive/api/guides/api-specific-auth

13. Google Picker overview  
    https://developers.google.com/workspace/drive/picker/guides/overview

14. Google Picker for desktop and mobile apps  
    https://developers.google.com/workspace/drive/picker/guides/desktop-mobile-picker

15. Google Drive comments and replies  
    https://developers.google.com/workspace/drive/api/guides/manage-comments

16. Google Drive comments resource  
    https://developers.google.com/workspace/drive/api/reference/rest/v3/comments

17. Google Drive changes and revisions  
    https://developers.google.com/workspace/drive/api/guides/change-overview

18. Google Drive API error handling  
    https://developers.google.com/workspace/drive/api/guides/handle-errors

**Source verification date:** June 25, 2026

---

## 53. Final Product Decision

QUILL will not make Markdown the mandatory editing surface for Google Docs.

The implementation will use:

```text
Google Docs structured document
            ↓
QUILL semantic document model
            ↓
Text-first accessible projection
            ↓
Focused structured editors
```

This architecture preserves the simplicity of a text editor without pretending that tables and other document objects are merely strings. It also creates the foundation for QUILL to become an accessible native front end for additional cloud document platforms in the future.
