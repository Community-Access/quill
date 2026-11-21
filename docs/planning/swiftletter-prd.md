# SwiftLetter Newsletters in QUILL

Product requirements, draft for Jeff's review. 2026-11-21.

Issue: Community-Access/quill#1992, from payown. REST contract: `docs/planning/swiftletter-rest-contract.md` (version 1.0, proposed).

## 1. Summary

SwiftLetter is a WordPress plugin that builds newsletters from articles, runs an editorial review, and makes a Word document and audio from the result. Its first release candidate is 1.0.9. It is private, and its REST API does not exist yet. Its maintainers offered to build the REST contract we write.

Jeff wants "a rich Windows UI/UX experience but also inside of WordPress". So SwiftLetter gets a first-class desktop experience in QUILL, and SwiftLetter's own WordPress dashboard stays a full peer. Both edit the same newsletters and articles. SwiftLetter is the source of truth.

QUILL's side is built into QUILL's WordPress support, not a Quillin. It uses the connected site, its application password and QUILL's one WordPress client. It shows only on a site whose REST index lists `swiftletter/v1`.

## 2. Where things stand

- **This is a plan.** Nothing is built in QUILL yet. Jeff asked to plan only until we can read the SwiftLetter repository (section 13).
- **The contract is proposed.** It is written and versioned 1.0, and waits for the SwiftLetter maintainers' review.
- **We have asked for access** to the SwiftLetter repository, and for a 1.0.9 build with the routes on our test site.

## 3. Goals

1. A person who uses a screen reader or a braille display can write, order, review and export a newsletter from QUILL as easily as anyone can in the dashboard.
2. Editors who never use QUILL lose nothing. The dashboard sees every QUILL change, and QUILL sees every dashboard change.
3. Nothing is published, reviewed, spent or sent to an AI without a deliberate command.
4. A WordPress site without SwiftLetter behaves exactly as it does today.

## 4. Not doing

- No second login, credential store or HTTP stack. The existing site connection is the only door.
- No change to SwiftLetter's code from our side. For WordPress we write requirements (section 10) and the contract.
- No offline creation of newsletters. Articles can be written offline as working copies, like any post.
- No AI writing help built for SwiftLetter. QUILL's existing AI commands work on an article in the editor like any document, through QUILL's one AI route, and only when the person asks.
- No DOCX import in phases 1 to 3. The issue's phase 3 asks for it. It waits until we have read how SwiftLetter stores an imported document's pictures and alt text (section 13).

## 5. Decisions on the issue's seven questions

1. **Where it lives.** Both: a branch in the WordPress Workbench, a dedicated Newsletter window, and context-aware WordPress editor commands. Articles open in QUILL's normal editor.
2. **Built in, not a Quillin.** It follows the Gravity Forms and Paid Memberships Pro patterns (section 11 names the files).
3. **Working copies.** An article is a post of type `swiftletter_article`, so its working copy is keyed by site, kind and id like any post (`quill/core/wordpress/local.py`). The copy also remembers its newsletter and position, so Return to Newsletter knows where to go.
4. **Keys.** No new chord in the editor's main keymap. The WordPress key layer's D becomes "Save Article to SwiftLetter" on an article. P never publishes or reviews an article; it says so. Return to Newsletter gets the layer's Shift+N.
5. **Accessible conventions.** Sections 7 and 9.
6. **Testing.** Section 12.
7. **Scope.** A design first (this PRD and the contract). Phase 1 is the first build. Nothing merges until the contract is agreed and tried on a real site.

## 6. Phases

The issue's phases, and ours:

| Issue phase | Ours | What |
|---|---|---|
| 1. Read and edit safely | Phase 1 | Detect, browse, open, Save Article, Return to Newsletter, conflicts |
| 2. Editorial organization | Phase 2a | Reorder, link and unlink, new article, delete and restore, new and rename newsletter |
| 2. Editorial organization | Phase 2b | Mark Reviewed (several at once), review history |
| 3. Media and documents | Phase 3 | Export DOCX, Generate Audio, job progress, download, open the result |
| 3. Media and documents | Phase 3b | DOCX import, once we have read their import code |
| 4. Optional advanced | Phase 4 | Writing help (existing AI route), offline sync (existing offline queue), shortcuts. Nothing SwiftLetter-specific |

Each phase is built against a fake server that follows the contract, then checked on the test site before it merges.

## 7. QUILL desktop experience

### 7.1 Detecting SwiftLetter

- The Workbench reads each site's REST index once. The SwiftLetter branch shows only when the index lists `swiftletter/v1`. This is one new row in `PLUGIN_BRANCHES` in `quill/core/wordpress/workbench_plugin_branches.py`, which the Workbench's `shows_node` already checks.
- The first time the branch is opened, QUILL reads `GET /swiftletter/v1` for the version and the person's capabilities.
- An API version QUILL does not know gives one sentence in the list, and nothing else (contract 2.3).

### 7.2 The Workbench branch

Sites > *site* > **SwiftLetter** lists the newsletters, one row each: title, state, number of articles, when it changed and who changed it.

Under SwiftLetter, the tree has one node per newsletter, named after it. Selecting it lists its articles in newsletter order. Each row says:

- the title;
- the review state as words ("Reviewed", "Not reviewed", "Changed since review");
- who changed it last, and when;
- the position, "3 of 8", as the last column. The screen reader already gives a list position, so the column is mainly for braille and for reading the row in full.

The Workbench tree keeps to four levels (`MAX_DEPTH` in `quill/core/workbench/tree.py`), so there is no separate Newsletters folder. The SwiftLetter node's own list is the newsletters, and each newsletter is a dynamic child node. This is the Calendar's pattern: loading the parent list caches what it found, then the tree is rebuilt (`day_children` and `_days_changed` in `quill/ui/wordpress_workbench_bold.py`).

On a newsletter row, Enter opens the Newsletter window. On an article row, Enter opens the article in the editor, and the context menu also has Open Newsletter Window. Alt+Enter is Properties, as everywhere. F1 says what the node or row is.

Writes are not in the Workbench list. They are in the Newsletter window, where the order and the review state are in front of the person.

### 7.3 The Newsletter window

One newsletter at a time, modeless, like the other Workbench windows. It has its own F1 topic. Opening it again for the same newsletter brings the open one forward.

**Layout, in tab order, with its access keys.** No two controls share a letter (GATE-14). Close carries none.

| Control | Access key |
|---|---|
| &Status (read-only text, label first) | Alt+S |
| &Articles (the list, label first) | Alt+A |
| Open in &Editor | Alt+E |
| Move &Up | Alt+U |
| Move Do&wn | Alt+W |
| Mar&k Reviewed... | Alt+K |
| Review &History... | Alt+H |
| &Link Existing Article... | Alt+L |
| U&nlink from Newsletter... | Alt+N |
| New Art&icle... | Alt+I |
| &Delete Article... | Alt+D |
| Restore from &Trash... | Alt+T |
| Export D&OCX... | Alt+O |
| &Generate Audio... | Alt+G |
| Open &Result | Alt+R |
| Re&fresh | Alt+F, and F5 |
| Close | Escape |

Unlink and Delete are not next to each other in the tab order.

The window is a `wx.Frame`, so Escape and F5 are added through its accelerator table (a `wx.Frame` does not map Escape to Cancel by itself), and Close is bound with `dialog_contract.bind_close_button`.

The Articles list also has a context menu (the Applications key or Shift+F10) with the same commands, each showing its access key. Sixteen buttons is a long way to Tab.

**7.3.1 The status line.**

- It is a `wx.TextCtrl` with `TE_READONLY`, labelled "&Status" by a label created just before it. A plain static text cannot take focus and is not read when the window opens.
- It says the newsletter's title, state, number of articles, and the current job's stage. An empty newsletter says "No articles yet." here. The list stays empty, with no made-up row.
- It is updated with `ChangeValue`, never `SetValue`, so no change event fires.
- It takes focus only the first time the window opens. Every later return (Return to Newsletter, Refresh, closing a dialog) puts focus on the article in the list.

**7.3.2 The list's mechanics.** Focus restoration depends on these, so they are requirements:

- Rows are updated in place with `SetItem`. A move swaps the two rows' text. A focused list is never cleared with `DeleteAllItems` and rebuilt, because NVDA and JAWS then jump to row 1 or read "list, empty".
- A refresh that changes how many articles there are rebuilds the list only while it does not have focus, or keeps the focused row by id while rows are added or removed around it.
- Restoring focus sets both `LIST_STATE_FOCUSED` and `LIST_STATE_SELECTED` on the row with the right article id, then calls `EnsureVisible`. On refresh, the multi-selection is kept by id.
- Columns, in order: Title, Review, Changed By, Changed, Position.

**7.3.3 Reorder.** Move Up and Move Down are the same words and access keys as Menus > Arrange Items (`quill/ui/wordpress_menu_commands.py`, which saves each move as it happens). Each move:

- moves the selected article in the list, keeping it selected and focused;
- is announced only when focus is not in the list. When focus is in the list, the screen reader already reads the moved row in its new place, so QUILL says nothing. When focus is on the Move button, QUILL says "Moved to 2 of 8." once;
- sends the whole order in one request, with the newsletter's version token, as Arrange Items saves each move;
- if a move arrives while the last one is still being sent, QUILL sends the newest order once that one finishes, so the site never gets an order out of turn;
- on a conflict, puts the site's order back, keeps focus on the same article, and then, after the list has settled (`wx.CallAfter`), says "Someone changed the order on the site. QUILL put their order back; your move was not saved."

These are always announced, because nothing focused changes: "Already first.", "Already last.", "Select one article to move." (when several are selected), and the conflict sentence. Nothing is sent for them.

**7.3.4 Mark Reviewed.** On one or more selected articles.

- A preview names each one with the exact revision it would mark: "From the chair, revision 905, changed by Pat Reyes on 20 November." Articles already reviewed at their current revision are listed as "already reviewed" and skipped.
- If every one is marked, QUILL says one sentence ("3 marked reviewed.") and opens nothing.
- If any is refused or skipped, QUILL announces nothing and opens a results dialog. Its first control is a read-only text holding the summary ("2 marked reviewed, 1 refused."), then a list of each article and what happened, including SwiftLetter's own sentence for a refusal.
- The list's Review column updates in place.

**7.3.5 Link, Unlink, New, Delete.**

- Link Existing Article opens a dialog with a labelled "&Filter" box before a list of the site's articles not in this newsletter. The match count is said once, after typing pauses, because the list is not focused. It links the chosen article at the end.
- Unlink is worded "Unlink from Newsletter" everywhere and asks: "Take From the chair out of Winter 2026? The article is not deleted, and stays in every other newsletter." The safe button is the default.
- New Article asks for a title, makes the article on the site, links it at the end, and offers to open it.
- Delete Article asks by name, with the safe button as the default, sends the article to WordPress's Trash, and says "In the Trash. Restore from Trash brings it back." Restore from Trash lists the trashed articles of this newsletter.

**7.3.6 Export DOCX and Generate Audio.**

- Each asks first when SwiftLetter says the export is paid or uses an outside provider, and shows SwiftLetter's own notice. A DOCX export with no provider asks nothing more than the command itself.
- The job's stage is shown in the status line, so it can be read at any time.
- While the Newsletter window is the active window, each stage is spoken once when it changes ("Making audio, article 3 of 8."), through the announcer, never on a timer. When the person is elsewhere, for example writing in the editor, only the final result is spoken, so a long job does not interrupt writing.
- The result is said once: "Audio is ready. Open Result plays it." or SwiftLetter's sentence for a failure.
- The window can be closed while a job runs. The job carries on on the site, and QUILL says the result once if it finishes while QUILL is open.

**7.3.7 Open Result.** A DOCX opens in QUILL's editor. Audio opens in the Media Player. The file is downloaded through the authenticated route into QUILL's data folder, `swiftletter/<site>/<newsletter>/`, and never from a public address.

**7.3.8 Focus after actions.** When the person comes back from an article, focus is on the same article in the list, by id, even if the order changed meanwhile. After a refresh, a move, a review or an unlink, focus stays on the same article, or on the nearest one if it is gone.

### 7.4 Articles in the editor

- Opening an article puts it in QUILL's normal editor as a working copy, in HTML or Markdown as the person chooses, exactly like a post (`open_item` and `_open_as` in `quill/ui/wordpress_open_commands.py`). The working copy's properties also keep its newsletter's id and title and the article's position.
- **Ctrl+S stays local save.** Nothing is sent.
- **D on the WordPress key layer** (Ctrl+Alt+Shift+Grave, then D) and File > WordPress > Save Draft to Site become **Save Article to SwiftLetter** on an article. It saves title and content as a new revision, with the same `modified_gmt` conflict check as posts (`send_work` in `quill/ui/wordpress_more_commands.py`), and never sends a status. When the article had been reviewed, it says "Article saved to SwiftLetter on Example Site. Its review state is now Changed since review."
- **P never publishes or reviews an article.** It says: "Articles are published with their newsletter, and reviewed in the Newsletter window. Return to Newsletter is Ctrl+Alt+Shift+Grave, then Shift+N."
- **Return to Newsletter** (File > WordPress, and the layer's Shift+N) brings forward, or opens, the Newsletter window with focus on this article. On a document that is not an article it says so.
- **Remote changes.** Compare with Site, Previous Versions, Keep Theirs and Use Mine work as they do for posts, because the article is a post.
- **Offline.** A failed save offers Try Again or the offline queue, like any post (`quill/core/wordpress/offline.py`).

### 7.5 Safe Mode and Read Only access

- Safe Mode, and Workbench access set to Read Only for the site, refuse every write in the Newsletter window with one sentence, before anything is sent. The window asks the Workbench's guard (`access_refusal` in `quill/ui/wordpress_workbench_guard.py`).
- Nothing publishes, reviews, calls an AI or starts a paid export without a deliberate command and, for a paid export, a yes.

### 7.6 wp-admin for This Place

The wp-admin map gets a SwiftLetter row (`quill/core/wordpress/workbench_admin_map_plugins.py`), so wp-admin for This Place on the SwiftLetter node or a newsletter opens SwiftLetter's own screen. Its `admin.php?page=` slug is read from their code once we have access.

## 8. Errors (GATE-EC)

Every error class inherits `CodedError` through `WordPressApiError` (`quill/core/wordpress/api.py`), so the existing `failure_sentence` speaks its plain sentence.

| Code | When | What the person hears |
|---|---|---|
| `QUILL-SWIFTLETTER-API-REQUEST` | Any refusal not listed below | SwiftLetter's own sentence, or the WordPress one |
| `QUILL-SWIFTLETTER-API-VERSION` | An API version QUILL does not know | "SwiftLetter on this site speaks version 2.0 of its connection, and this QUILL knows version 1. Update QUILL, or ask the site's administrator." |
| `QUILL-SWIFTLETTER-API-CONFLICT` | 409 or 412 | "Someone changed this on the site..." and what QUILL did about it |
| `QUILL-SWIFTLETTER-API-FORBIDDEN` | 403 | SwiftLetter's sentence, or "Your account on Example Site is not allowed to do that in SwiftLetter." |
| `QUILL-SWIFTLETTER-EXPORT-CONSENT` | 428 | "SwiftLetter needs your yes before this export. Choose the command again to be asked." |
| `QUILL-SWIFTLETTER-EXPORT-FAILED` | A job ends failed, or runs out of time | SwiftLetter's sentence, or "The export did not finish in 20 minutes. It may still finish on the site." |

A disconnected site, a wrong password and a site that is down use the existing WordPress sentences (`plain_error` in `api.py`).

## 9. Accessibility

- Every list is a native `wx.ListCtrl` in report view, so the screen reader reads row and column without help.
- Every control has a label created just before it, so its name is its label. Buttons carry their own names.
- Nothing is announced on focus, on opening, or for a selection change (GATE-13). The announcer speaks only results QUILL alone knows: a move's new position when focus is on the button, a job's stage change, a review's outcome, a refusal.
- What is spoken is also brailled (GATE-BRAILLE), because everything goes through the announcement service.
- F1 answers with the window's purpose and then the focused control's own help, written inline with `SetHelpText` at each control (`quill/ui/app_context_help.py`).
- No colour carries meaning: the review state is words.
- Every command is reachable by keyboard: buttons, the context menu, and the Workbench's menus. No drag and drop.
- Screen reader checks with NVDA, JAWS and Narrator are in section 12.3, recorded in `docs/qa/screen-reader-checks-2026-10.md` once run.

## 10. In WordPress: what the SwiftLetter dashboard needs so both work together

These are requirements for SwiftLetter's own admin screens, for the maintainers. They are WCAG 2.2 AA, and they are what lets a QUILL user and a dashboard user work on the same newsletter.

### 10.1 Reorder without drag

- Every article in a newsletter's list has plain **Move Up** and **Move Down** buttons. Drag and drop may stay, but it must never be the only way (WCAG 2.5.7 Dragging Movements). Use plain buttons, not a menu button.
- The accessible name starts with the visible words, then names the article: `<button>Move Up<span class="screen-reader-text"> From the chair</span></button>`, which is read "Move Up From the chair" (WCAG 2.5.3 Label in Name). The same pattern goes on Unlink, Delete and Mark Reviewed.
- Moving a row's DOM node drops its focus to the page body. After the row moves, the script calls `focus()` on the same button of the same article.
- Focus stays on that button even when the move makes it first or last.
- A polite live region says the result once, through `wp.a11y.speak( message, 'polite' )`: "From the chair moved to position 1 of 8, now first."
- The first article's Move Up and the last article's Move Down use `aria-disabled="true"`, not `disabled`, so they stay focusable. Activating one speaks "Already first." or "Already last." and does nothing else.
- If the table can be sorted by another column, Move Up and Move Down are disabled while it is, with a sentence saying why.
- The order is saved by the same `PUT .../articles/order` route QUILL uses, with the version token, so a dashboard move and a QUILL move cannot silently overwrite each other.
- On a conflict (409), the screen reloads the order, keeps focus on that article's Move button, and announces "Someone changed the order. Their order is shown; your move was not saved."

### 10.2 Review state as text

- The review state is written as text in its own column ("Reviewed", "Not reviewed", "Changed since review"), never as a colour, an icon alone or a strike-through. An icon may sit beside the words with `aria-hidden="true"` (WCAG 1.4.1 Use of Color, 1.1.1 Non-text Content).
- The list is a real table with a caption and `scope="col"` headers (WCAG 1.3.1).
- Text meets 4.5:1 contrast, and icons and control borders 3:1 (WCAG 1.4.3, 1.4.11).

### 10.3 Focus after actions

- After Mark Reviewed, Unlink, Delete or Restore, focus goes to a predictable place: the same row if it is still there, otherwise the next row, otherwise the list's heading, which has `tabindex="-1"` so `focus()` works. Never to the top of the page (WCAG 2.4.3 Focus Order).
- A confirmation dialog returns focus to the control that opened it.
- Focus is never hidden behind a sticky header or the admin bar (WCAG 2.4.11 Focus Not Obscured), and always visible (WCAG 2.4.7).

### 10.4 Notices

- Every result of an action done without a page load is announced with `wp.a11y.speak()`, once: "Marked reviewed.", "Unlinked. The article was not deleted." `wp-a11y` is listed as a script dependency.
- After an action that reloads the page, `wp.a11y.speak` is unreliable. Instead focus moves to the notice (which has `tabindex="-1"`) or to the row, one or the other, and the notice is not also spoken.
- Admin notices use WordPress's notice markup (`notice notice-success`, `notice-error`) (WCAG 4.1.3 Status Messages).
- Errors say what happened and what to do, in words, next to the control they belong to (WCAG 3.3.1, 3.3.3).

### 10.5 Labelled controls and page structure

- Every input, select and button has a visible label, or an accessible name that starts with its visible text (WCAG 1.3.1, 2.5.3, 4.1.2).
- Icon-only buttons have an accessible name, and any tooltip on them can be dismissed, hovered and stays until dismissed (WCAG 1.4.13 Content on Hover or Focus).
- Unlink and Delete are worded differently and never sit side by side without words. Unlink says it does not delete.
- Repeated buttons on each row say which article they act on (WCAG 2.4.6).
- No `<select>` acts on change. A state or position chosen from a list needs a button to apply it (WCAG 3.2.2 On Input).
- The page's `<title>` names the newsletter (WCAG 2.4.2), and the page has one H1 naming it (WCAG 2.4.6).
- Row buttons are at least 24 by 24 CSS pixels, or spaced as WCAG allows (WCAG 2.5.8 Target Size Minimum).
- The table with its row buttons works at 400 percent zoom and 320 CSS pixels wide without scrolling in two directions, and with text resized to 200 percent (WCAG 1.4.10 Reflow, 1.4.4 Resize Text).

### 10.6 Job progress

- DOCX and audio generation show progress in text: the stage and, for audio, "article 3 of 8".
- A `role="status"` region is updated when the stage changes, not on a timer, so a screen reader hears each stage once.
- If a `<progress>` element is used, it has a label and its value is also given as text.
- The finished file is offered as a link with its name, type and size ("winter-2026.docx, Word document, 47 KB").
- A paid or provider export asks before it starts, in a dialog with a heading, the notice, and two clearly named buttons ("Generate Audio", "Cancel"), then returns focus. Delete asks first, or can be undone through Restore (WCAG 3.3.4 Error Prevention).
- Nothing times out without warning (WCAG 2.2.1 Timing Adjustable).

### 10.7 Seeing QUILL's edits

- Revisions authored through REST show in the article's revision list with the person's name and, where WordPress recorded it, the application password's name: "Pat Reyes, from QUILL (application password 'Pat's laptop')".
- The newsletter's article list shows who changed each article last and when, as text: the same `modified_by` QUILL shows.
- A dashboard screen that is open while QUILL saves shows the change on reload. The article editor respects WordPress's post lock, so a dashboard edit and a QUILL save cannot both win silently.
- To test (core WordPress behaviour, not the plugin's): with an article open in the block editor while QUILL saves it, check that the "This post has been updated" notice can be reached by keyboard and is announced.

### 10.8 Testing on their side

- Keyboard only: every action above without a mouse.
- NVDA with Firefox and JAWS with Chrome on the newsletter list, reorder, review and export.
- axe or Accessibility Insights on each SwiftLetter admin screen with zero WCAG A or AA violations, as well as the manual checks above.

## 11. Where it goes in QUILL

Each part, and the existing QUILL file or pattern it builds on.

### 11.1 Wx-free core (`quill/core/wordpress/`)

| New module | What | Built on |
|---|---|---|
| `swiftletter_contract.py` | Routes, version check, the newsletter, article, review and job shapes, error mapping to `QUILL-SWIFTLETTER-*` | `api.py` (`WordPressApiError`, `plain_error`) |
| `swiftletter.py` | One function per route, through the site's `WordPressApi` | `api.py` (`request`, `iter_collection`, `batch`); `workbench_pmpro_rest.py` |
| `workbench_swiftletter.py` | The branch's nodes, loaders and rows | `workbench_pmpro_tree.py`, `workbench_pmpro.py`, `workbench_rows.py` (`WbRow`) |
| `workbench_swiftletter_actions.py` | Context-menu rows, their tiers, help, and written reasons for having no chord | `workbench_gravity_actions.py` (`KEYLESS`), `workbench_admin_actions.py`, `workbench_tiers.py` |

One small change to `api.py`: a `download` method that returns bytes and headers through the same signed opener, for the job file. It is the same door, so no new egress call site.

Changes to existing modules: one row in `workbench_plugin_branches.PLUGIN_BRANCHES`; the nodes spliced into `workbench_tree.py`; the loader family in `workbench_load.py`; node and row help in `workbench_node_help.py`; the row types in `workbench_actions.py`; one row in `workbench_admin_map_plugins.py`; the Return to Newsletter row and its Shift+N in `menu.py` (`WORDPRESS_ROWS`, `LAYER_KEYS`, `DOCUMENT_ONLY`).

### 11.2 Windows (`quill/ui/`)

| New module | What | Built on |
|---|---|---|
| `wordpress_workbench_swiftletter.py` | Provider mixin: dynamic newsletter nodes, Enter on a row, open the window or the article | `wordpress_workbench_membership_commands.py`, `wordpress_workbench_discovered.py` (`namespace_children`), `wordpress_workbench_bold.py` (Calendar's dynamic nodes) |
| `swiftletter_window.py` | The Newsletter window: status line, list, buttons, focus by id | `workbench_frame.py` (modeless frame), `dialog_contract.bind_close_button` |
| `swiftletter_window_actions.py` | Move, review, link, unlink, new, delete, restore, export, jobs, open result | `wordpress_menu_commands.py` (Arrange Items' movers); `wordpress_workbench_guard.py` (tier checks) |
| `wordpress_swiftletter_commands.py` | Editor mixin on `WordPressCommands`: context-aware D and P, Return to Newsletter, open an article with its newsletter | `wordpress_more_commands.py` (`cmd_save_draft`, `send_work`, `_conflict`), `wordpress_open_commands.py` |

QUILL Lite gets `cmd_wp_return_to_newsletter` in `quill/apps/lite_window_wordpress.py`, because File > WordPress is shared and QUILL Lite may never be ahead or behind on a shared row. QUILL Lite gets no Workbench, so its Return to Newsletter opens the newsletter in QUILL's Workbench when QUILL is running, or says where to find it.

### 11.3 Where a result opens

- DOCX: the editor's `open_path`, as any document.
- Audio: the Media Player, as `wordpress_player_commands.py` does for site audio.

## 12. Gates and tests

### 12.1 Gates

- GATE-9: the SwiftLetter routes named in the reviewed WordPress egress entry (`quill/tools/network_egress_entries_wordpress.py`, `send_to_site`).
- GATE-EC: the six `QUILL-SWIFTLETTER-*` codes (`quill/tools/error_code_audit.py`).
- GATE-13: no announce on focus or title; a move in the focused list is not announced; each job stage once (`check_over_announce.py`).
- GATE-11: every new module under 600 lines (`module_size_budgets.json`). `wordpress_workbench_window.py` is near its ceiling, so the provider's new code goes in the mixin.
- GATE-14: the access-key table in 7.3 (`check_access_keys.py`).
- Menu accelerators and family rule 8: the Return to Newsletter row shows its layer key; each Workbench command has help and a written reason for having no chord (`test_menu_accelerators.py`, `test_wp_workbench_by_name.py`).
- Tiers: every new `do_` handler classified (`test_wp_workbench_tiers.py`).
- GATE-LITE-COVER: `cmd_wp_return_to_newsletter` has a behavioural test (`lite_command_coverage.json`).
- F1: authored help on the window and every control; `docs/f1-help-reference.md` regenerated (`build_help_reference.py`).
- GATE-REACH and the dialog inventory: the window reachable from an entry point (`surface_reachability_audit.py --write`, `dialog_inventory.py`).
- The Workbench reference (`python -m quill.tools.build_workbench_reference --write`), the keyboard reference, and the command catalogue and Command Key fixtures for the new row.
- A CHANGELOG entry, a SwiftLetter section in `docs/user guide/quill-guide/quill-guide-16-wordpress.md`, and HTML and EPUB regenerated for every changed document.
- `python -m quill.tools.platform_report` clean.

### 12.2 Automated tests

- `tests/unit/core/wordpress/fake_swiftletter.py`: the contract as a fake server behind the WordPress client's opener, like the fake site in `tests/unit/ui/wordpress/test_wp_workbench_window.py`.
- Core: discovery and versions, every route, every error code, order conflicts, stale revisions, consent, jobs and downloads.
- Workbench: the branch hides on a site without SwiftLetter; rows say title, review, who and position; Enter opens the window or the article.
- Newsletter window: a move from the button announces once and sends one order; a move in the focused list announces nothing; a conflict restores the order and keeps focus; rows update in place; Mark Reviewed previews and reports per article as 7.3.4 says; Unlink never deletes; Delete trashes; Safe Mode and Read Only refuse; an export asks for consent, speaks each stage once and opens the result.
- Editor: D on an article saves title and content only, with the conflict check; P refuses; Return to Newsletter focuses the article.

### 12.3 By hand, before merging phase 1

- NVDA and JAWS: browse the branch, open an article, save it, return, and hear the same article focused.
- Narrator: the Newsletter window's list and buttons.
- A braille display: the status line and a move result.

## 13. What we need from the SwiftLetter repository

When we have access, we will read their code for these, and change this PRD and the contract to match:

1. **Post types.** The article type's name, `rest_base`, `show_in_rest`, `supports` (revisions, custom fields), statuses, and whether newsletters are a post type, a taxonomy or their own table.
2. **Capabilities.** The capabilities they register or map, how they are given to roles, and the editorial rules on top (who may edit, review, reorder, export).
3. **Review model.** What "reviewed" is stored against (a revision, a hash, a date), what resets it, whether review has stages or notes, and where review history lives.
4. **Ordering and membership.** How an article's place in a newsletter is stored, and whether one article can be in several newsletters.
5. **Export jobs.** How DOCX and audio are made (cron, Action Scheduler, a request), the stages, where the provider and its key are configured, what is paid, and how failures are recorded.
6. **Private files.** Where generated files are written, whether they are in the media library, how access is checked, and how long they are kept.
7. **Admin screens.** The `admin.php?page=` slugs, and how the current screens reorder and show review state, so section 10 can name exactly what changes.
8. **DOCX import.** How an imported document's title, headings, pictures and alt text are stored (phase 3b).
9. **Their tests.** What they already test, so the contract tests fit beside them.

## 14. Open questions

For Jeff:

1. Is Shift+N on the WordPress layer right for Return to Newsletter, or should it stay unkeyed (reached from File > WordPress)?
2. Should the Newsletter window save each move at once, as Menus > Arrange Items does today, or move locally and save with one Save Order button?
3. Should phases 2 and 3 merge together with phase 1, or wait behind it until the real API has been tried?

For the SwiftLetter maintainers: the open questions in the contract (section 12), and section 13 above.
