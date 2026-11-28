# SwiftLetter Newsletters in QUILL

Product requirements. First drafted 2026-11-21; corrected to SwiftLetter's real API and Michael's answers on 2026-11-22.

Issue: Community-Access/quill#1992, from payown (Michael, SwiftLetter's maintainer). REST contract: `docs/planning/swiftletter-rest-contract.md` (API version 1.x, as built in SwiftLetter 1.1.0-rc.1). Michael's answers, by number, are in section 15.

## 1. Summary

SwiftLetter is a WordPress plugin that builds newsletters from articles, runs an editorial review, and makes a Word document and audio from the result. An article (`swl_article`, REST base `swl-articles`) belongs to one parent newsletter (`swl_newsletter`). Review is one confirmation per article; there is no newsletter state machine. DOCX and audio are made inside the request today. SwiftLetter 1.1.0-rc.1 adds the Phase 1 routes QUILL uses: discovery, the article's edit context and a versioned save.

Jeff wants "a rich Windows UI/UX experience but also inside of WordPress". So SwiftLetter gets a first-class desktop experience in QUILL, and SwiftLetter's own WordPress dashboard stays a full peer. Both edit the same newsletters and articles. SwiftLetter is the source of truth.

QUILL's side is built into QUILL's WordPress support, not a Quillin. It uses the connected site, its application password and QUILL's one WordPress client. It shows only on a self-hosted site whose REST index lists `swiftletter/v1`. WordPress.com connections are out of scope (answer 14).

## 2. Where things stand

- **Shipping now (Phase 1, browsing).** The shared client (`quill/core/wordpress/swiftletter.py`, Michael's #1999) and browsing in the WordPress Workbench (#2000, with our review fixes and the follow-ups in section 15): newsletters, their articles in order, review state in words, who changed an article and when, and whether your account can edit it. Nothing in the Workbench writes to the site.
- **In progress, Michael's.** Opening an article in QUILL's editor and Save to SwiftLetter. The client already has the versioned save, its coded refusals, the stored title and content, and Compare with Site's read (section 8).
- **The contract is the real API.** `swiftletter-rest-contract.md` now describes SwiftLetter 1.1.0-rc.1, not a proposal. SwiftLetter's shared contract fixtures (payown/SwiftLetter PR #11) are replayed by QUILL's tests (`tests/fixtures/swiftletter_contract/`).
- **Test site.** We install 1.1.0-rc.1 ourselves from SwiftLetter PR #9 (answer 34).

## 3. Goals

1. A person who uses a screen reader or a braille display can write, order, review and export a newsletter from QUILL as easily as anyone can in the dashboard.
2. Editors who never use QUILL lose nothing. The dashboard sees every QUILL change, and QUILL sees every dashboard change.
3. Nothing is published, reviewed, spent or sent to an AI without a deliberate command.
4. A WordPress site without SwiftLetter behaves exactly as it does today.

## 4. Not doing

- No second login, credential store or HTTP stack. The existing site connection is the only door.
- No change to SwiftLetter's code except through pull requests on our own branches, which Michael reviews (answer 24). Nothing goes to SwiftLetter's `main`, and we merge and release nothing there.
- No offline creation of newsletters. Articles can be written offline as working copies, like any post.
- No AI writing help built for SwiftLetter. QUILL's own AI tools work on an article only when the editor asks, with the provider they chose. Opening, saving, reviewing or exporting never calls an AI. SwiftLetter's own AI tools stay in its dashboard (answer 23).
- No newsletter deletion in QUILL until SwiftLetter moves a newsletter to the Trash and restores it with its articles and order (answer 17).
- No WordPress.com support. A plugin-enabled WordPress.com site may be tested separately later, before any claim of support (answer 14).
- DOCX import improvements are separate from the phases below and are SwiftLetter's to schedule (answers 21 and 25).

## 5. Decisions on the issue's seven questions

1. **Where it lives.** Both: a branch in the WordPress Workbench, a dedicated Newsletter window, and context-aware WordPress editor commands. Articles open in QUILL's normal editor.
2. **Built in, not a Quillin.** It follows the Gravity Forms and Paid Memberships Pro patterns (section 11 names the files).
3. **Working copies.** An article is a post of type `swl_article` (REST base `swl-articles`), so its working copy is keyed by site, kind and id like any post (`quill/core/wordpress/local.py`). The copy also remembers its one parent newsletter and its position, so Return to Newsletter knows where to go.
4. **Keys.** No new chord in the editor's main keymap. The WordPress key layer's D becomes "Save Article to SwiftLetter" on an article. P never publishes or reviews an article; it says so. Return to Newsletter gets the layer's Shift+N.
5. **Accessible conventions.** Sections 7 and 9.
6. **Testing.** Section 12.
7. **Scope.** A design first (this PRD and the contract). Phase 1 is the first build. Nothing merges until the contract is agreed and tried on a real site.

## 6. Phases

In the order Michael set (answer 25). Each SwiftLetter change lands first, with PHPUnit tests and a WordPress integration check; QUILL follows on the same routes as the dashboard.

| Phase | What | Needs from SwiftLetter |
|---|---|---|
| 1 | Detect, browse, open, Save to SwiftLetter, Compare with Site, Return to Newsletter | 1.1.0-rc.1 (shipped), then the 409 lock refusal and the stored title and content in the save answer (answers 2 and 4) |
| 2a | Reorder with Move Up and Move Down; create and copy articles | A newsletter version token on reorder, 409 with the current order, the whole order or none (answer 15) |
| 2b | Mark Reviewed and review history | Revision-based review; history from the audit log (answer 16) |
| 3a | Export DOCX, with progress and download | One export job API (202, Queued, Running, Ready, Failed) and authenticated REST downloads (answers 19 and 20) |
| 3b | Generate Audio | The same job API, audio split by article, consent through the API (answer 18) |
| Later | Scribe "Make Accessible Editions"; Attach to Newsletter | Section 7.7 |

Discovery feature flags gate each phase: QUILL shows a command only when its flag is on, and a missing flag is off (answer 11). Each phase is built against a fake server that follows the contract and SwiftLetter's shared fixtures, then checked on the test site before it merges.

## 7. QUILL desktop experience

### 7.1 Detecting SwiftLetter

- The Workbench reads each site's REST index once. Like every plugin branch, SwiftLetter shows until the index is read, then only when it lists `swiftletter/v1` (`PLUGIN_BRANCHES` in `quill/core/wordpress/workbench_plugin_branches.py`). A WordPress.com connection never shows it; asked for there, it says in one sentence that QUILL offers SwiftLetter only on self-hosted sites.
- The first time the branch is opened, QUILL reads `GET /swiftletter/v1` once per site (kept five minutes, and read again when the site changes) for the API version, `capabilities.read` and the feature flags.
- Any `1.x` API version is accepted. A `2.x` or later, or a missing version, gives one sentence and nothing else, and is not read again until the site changes. A missing feature flag is off.

### 7.2 The Workbench branch (ships now)

Sites > *site* > **SwiftLetter** lists the newsletters, one row each: title, number of articles, and when it changed. Newsletters that share a title get their id.

The list keeps the Workbench's usual three pages of 100, with View > Load More and Load All. When the site sends `X-WP-Total`, the list's summary says once how many remain past those shown, so nobody mistakes a partial list for the full one (answer 12). There is no search or status filter in Phase 1.

Under SwiftLetter, the tree has one node per newsletter, named after it. Selecting it lists its articles in the order of the `articles` array, never re-sorted and never using the stored order values, which can have gaps (answer 9). Each row says:

- the title;
- the review state as words: "Reviewed", "Not reviewed", "Changed since review" (`review_state`, with `changed` the confirmed slug; QUILL falls back to `review_confirmed` for the current test build). Only Reviewed counts toward publication;
- the position, "3 of 8", as the last column.

Reading the row in full (Enter, or the details pane) adds the newsletter and site; who last changed its title or body and when, from `modified_gmt` and `modified_by` ("Editor unknown" when SwiftLetter sends null, never guessed from the byline); and "Your account cannot edit this article." when `can_edit` is false. `can_edit` and `can_review` are hints only; SwiftLetter checks every request.

The Workbench tree keeps to four levels (`MAX_DEPTH` in `quill/core/workbench/tree.py`), so there is no separate Newsletters folder. The SwiftLetter node's own list is the newsletters, and each newsletter is a dynamic child node. This is the Calendar's pattern: loading the parent list caches what it found, then the tree is rebuilt.

On a newsletter row, Enter is **Show Articles**: it selects the newsletter in the tree and lists its articles. "Open Newsletter" is kept for the Newsletter window that comes later. On an article row, Enter reads it in full; opening it in the editor is Michael's editor work. Alt+Enter is Properties, as everywhere. F1 says what the node or row is.

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
| New Art&icle... | Alt+I |
| &Copy Article... | Alt+C |
| &Delete Article... | Alt+D |
| Restore from &Trash... | Alt+T |
| Export D&OCX... | Alt+O |
| &Generate Audio... | Alt+G |
| Open &Result | Alt+R |
| Re&fresh | Alt+F, and F5 |
| Close | Escape |

Copy and Delete are not next to each other in the tab order. There is no Link or Unlink: an article has one parent newsletter.

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
- The window is reached only when SwiftLetter's discovery sends the flag for what it needs; each button shows only when its flag is on (answer 11).

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

**7.3.5 New, Copy, Delete.** Through SwiftLetter's existing create and copy routes (answer 17).

- New Article asks for a title, makes the article in this newsletter at the end, and offers to open it.
- Copy Article makes a separate article, never a link to the original.
- Delete Article asks by name, with the safe button as the default, sends the article to WordPress's Trash, and says "In the Trash. Restore from Trash brings it back." Restore from Trash lists the trashed articles of this newsletter.

**7.3.6 Export DOCX and Generate Audio.**

- Each export is a job on SwiftLetter's export job API (answer 19): starting answers `202` and a job id, and the status is Queued, Running, Ready or Failed with a readable progress message. Retrying a start never makes a second job or a second charge, and a failed job leaves the last good export in place.
- Audio asks first, showing the consent notice SwiftLetter sends through the API (it names OpenAI, says the newsletter text is sent to it, and that it may cost money), and SwiftLetter requires that yes before it starts. Audio is split by article, so progress reads "Article 3 of 8", and the old recording stays until the new one is complete (answer 18). A DOCX export asks nothing more than the command itself.
- The job's stage is shown in the status line, so it can be read at any time.
- While the Newsletter window is the active window, each stage is spoken once when it changes ("Making audio, article 3 of 8."), through the announcer, never on a timer. When the person is elsewhere, for example writing in the editor, only the final result is spoken, so a long job does not interrupt writing.
- The result is said once: "Audio is ready. Open Result plays it." or SwiftLetter's sentence for a failure.
- The window can be closed while a job runs. The job carries on on the site, and QUILL says the result once if it finishes while QUILL is open.

**7.3.7 Open Result.** A DOCX opens in QUILL's editor. Audio opens in the Media Player. The file is downloaded through SwiftLetter's authenticated REST download route (never `?swl_download=`, which an application password does not authenticate, and never a public fallback URL for an unpublished export) into QUILL's data folder, `swiftletter/<site>/<newsletter>/` (answer 20).

**7.3.8 Focus after actions.** When the person comes back from an article, focus is on the same article in the list, by id, even if the order changed meanwhile. After a refresh, a move, a review or a delete, focus stays on the same article, or on the nearest one if it is gone.

### 7.4 Articles in the editor

- Opening an article puts it in QUILL's normal editor as a working copy, in HTML or Markdown as the person chooses, exactly like a post (`open_item` and `_open_as` in `quill/ui/wordpress_open_commands.py`). The working copy's properties also keep its newsletter's id and title and the article's position.
- **Ctrl+S stays local save.** Nothing is sent.
- **D on the WordPress key layer** (Ctrl+Alt+Shift+Grave, then D) and File > WordPress > Save Draft to Site become **Save Article to SwiftLetter** on an article. It sends title and content once to `swiftletter/v1/articles/<id>/save` with the article's `edit_version` as `If-Match`, and never sends a status. Saving leaves the public post and its Word download unchanged until the article is reviewed again (answer 1). When the article had been reviewed, it says "Article saved to SwiftLetter on Example Site. Its review state is now Changed since review."
- **What WordPress kept.** The save answer returns the stored title and content with the new `edit_version` (answer 4; optional, so the 1.1.0-rc.1 answer of `id` and `edit_version` still works). When WordPress changed the text while sanitising it (for example kses storing an image's `"/>` as `" />` on a contributor's save), QUILL tells the editor and offers Compare. The stored text becomes the baseline for the next `If-Match`; the local copy, and anything typed while the save ran, is never silently replaced.
- **Refusals.** SwiftLetter's `message` is said exactly as written, never its code (answer 10). A 412 offers Compare with Site, which reads the current article through the existing authenticated edit route (answer 3). A 409 says who holds WordPress's post lock, in SwiftLetter's sentence (answer 2). Nothing is ever retried automatically, and the local copy stays.
- **P never publishes or reviews an article.** It says: "Articles are published with their newsletter, and reviewed in the Newsletter window. Return to Newsletter is Ctrl+Alt+Shift+Grave, then Shift+N."
- **Return to Newsletter** (File > WordPress, and the layer's Shift+N) brings forward, or opens, the Newsletter window with focus on this article. On a document that is not an article it says so.
- **Markdown or HTML.** An article opens in either; SwiftLetter always receives block markup. QUILL's Markdown converter keeps blocks it cannot convert intact, and before Markdown saves are enabled, a test shows that headings and anchors, links, images and alt text, and nested blocks survive. If something would be lost, the remote save stops and says why; the local draft stays (answer 13).
- **Remote changes.** Previous Versions, Keep Theirs and Use Mine work as they do for posts, because the article is a post.
- **Offline.** A failed save offers Try Again or the offline queue, like any post (`quill/core/wordpress/offline.py`).

### 7.5 Safe Mode and Read Only access

- Safe Mode, and Workbench access set to Read Only for the site, refuse every write in the Newsletter window with one sentence, before anything is sent. The window asks the Workbench's guard (`access_refusal` in `quill/ui/wordpress_workbench_guard.py`).
- Nothing publishes, reviews, calls an AI or starts a paid export without a deliberate command and, for a paid export, a yes.

### 7.6 wp-admin for This Place

The wp-admin map gets a SwiftLetter row (`quill/core/wordpress/workbench_admin_map_plugins.py`), so wp-admin for This Place on the SwiftLetter node or a newsletter opens SwiftLetter's own screen. Its slug is `admin.php?page=swiftletter`.

### 7.7 Accessible editions with Scribe (later)

Not part of SwiftLetter 1.1.0 (answers 31 to 33).

- **Make Accessible Editions with Scribe**, in QUILL, sends the *approved* newsletter DOCX to Scribe for Documents on the person's own Scribe account, only after they confirm. They review and download the BRF, DAISY, MP3 and accessible EPUB from one conversion.
- Nothing is sent back to SwiftLetter by itself. A separate **Attach to Newsletter**, added once the formats are tested, lets the editor choose and verify which editions to keep beside the Word and audio files; they stay private until published.
- Getting articles in through Scribe (a scan, PDF or photo becomes a draft the contributor corrects first) is separate from DOCX import, and nothing is imported, reviewed or published automatically.
- A server-side Scribe provider inside SwiftLetter waits for the export job API and private file handling, and needs SwiftLetter's own registration with Pneuma; QUILL's client ID is for the QUILL apps only.

## 8. Errors (GATE-EC)

Every error class inherits `CodedError` through `WordPressApiError` (`quill/core/wordpress/api.py`), so the existing `failure_sentence` speaks its plain sentence. The classes are in `quill/core/wordpress/swiftletter_errors.py`. SwiftLetter's `message` is written to be read aloud, so QUILL says it exactly as written and never says SwiftLetter's code; the code only picks the class, and so what QUILL offers next (`next_step`: Compare with Site, or reopen). When a refusal has no `message`, QUILL says its own sentence (below). Nothing is retried automatically.

| QUILL code | SwiftLetter code, status | Offers next | QUILL's sentence when SwiftLetter sends none |
|---|---|---|---|
| `QUILL-SWIFTLETTER-API-REQUEST` | Not active, an old SwiftLetter, an unreadable answer, WordPress.com | | The Workbench's own sentence, naming the site |
| `QUILL-SWIFTLETTER-API-VERSION` | `api_version` 2.x or later, or missing | | "SwiftLetter on this site uses version 2.0 of its connection, which needs a newer QUILL." |
| `QUILL-SWIFTLETTER-API-FORBIDDEN` | `swiftletter_forbidden`, 403; or discovery's `read` false | | "Your account is not allowed to edit this article in SwiftLetter." |
| `QUILL-SWIFTLETTER-API-VERSION-REQUIRED` | `swiftletter_version_required`, 428 | Reopen | "SwiftLetter needs the article's version to save it. Reopen it first. Your changes are still in QUILL." |
| `QUILL-SWIFTLETTER-API-INVALID-VERSION` | `swiftletter_invalid_version`, 400 | Reopen | "SwiftLetter could not read the article's version. Reopen it first. Your changes are still in QUILL." |
| `QUILL-SWIFTLETTER-API-INVALID-SAVE` | `swiftletter_invalid_save`, 400 | | "SwiftLetter takes only an article's title and content. Your changes are still in QUILL." |
| `QUILL-SWIFTLETTER-API-ARTICLE-UNAVAILABLE` | `swiftletter_article_unavailable`, 404 | | "This article is no longer available to edit in SwiftLetter. Your changes are still in QUILL." |
| `QUILL-SWIFTLETTER-API-CONFLICT` | `swiftletter_precondition_failed`, 412 | Compare with Site | "Someone changed this article on the site. Your local copy was not sent. Compare it with the current article before trying again." |
| `QUILL-SWIFTLETTER-API-ARTICLE-LOCKED` | `swiftletter_article_locked`, 409 (to be added; answer 2) | | "Someone else is editing this article in WordPress, so it was not saved. Your changes are still in QUILL." |
| `QUILL-SWIFTLETTER-API-SAVE-UNAVAILABLE` | `swiftletter_save_unavailable`, 503 | | "This site could not save the article safely, so nothing changed. Your changes are still in QUILL." |

For the 503 on a site whose posts table is not InnoDB, SwiftLetter will send: "This site can't safely save articles from QUILL. Ask your WordPress administrator to check that the posts table uses InnoDB. Your changes are still in QUILL." A save's 409, 412 and 428 are also recognised by status alone, for a site that sends no code. A WordPress refusal that is not SwiftLetter's (such as `rest_forbidden`) keeps WordPress's sentence. Export codes (consent, a failed job) come with the job API in Phase 3.

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
- The accessible name starts with the visible words, then names the article: `<button>Move Up<span class="screen-reader-text"> From the chair</span></button>`, which is read "Move Up From the chair" (WCAG 2.5.3 Label in Name). The same pattern goes on Delete and Mark Reviewed.
- Moving a row's DOM node drops its focus to the page body. After the row moves, the script calls `focus()` on the same button of the same article.
- Focus stays on that button even when the move makes it first or last.
- A polite live region says the result once, through `wp.a11y.speak( message, 'polite' )`: "From the chair moved to position 1 of 8, now first."
- The first article's Move Up and the last article's Move Down use `aria-disabled="true"`, not `disabled`, so they stay focusable. Activating one speaks "Already first." or "Already last." and does nothing else.
- If the table can be sorted by another column, Move Up and Move Down are disabled while it is, with a sentence saying why.
- The order is saved by the same `POST swiftletter/v1/articles/reorder` route QUILL uses, with the newsletter version token (answer 15), so a dashboard move and a QUILL move cannot silently overwrite each other.
- On a conflict (409), the screen reloads the order, keeps focus on that article's Move button, and announces "Someone changed the order. Their order is shown; your move was not saved."

### 10.2 Review state as text

- The review state is written as text in its own column ("Reviewed", "Not reviewed", "Changed since review"), never as a colour, an icon alone or a strike-through. An icon may sit beside the words with `aria-hidden="true"` (WCAG 1.4.1 Use of Color, 1.1.1 Non-text Content).
- The list is a real table with a caption and `scope="col"` headers (WCAG 1.3.1).
- Text meets 4.5:1 contrast, and icons and control borders 3:1 (WCAG 1.4.3, 1.4.11).

### 10.3 Focus after actions

- After Mark Reviewed, Delete or Restore, focus goes to a predictable place: the same row if it is still there, otherwise the next row, otherwise the list's heading, which has `tabindex="-1"` so `focus()` works. Never to the top of the page (WCAG 2.4.3 Focus Order).
- A confirmation dialog returns focus to the control that opened it.
- Focus is never hidden behind a sticky header or the admin bar (WCAG 2.4.11 Focus Not Obscured), and always visible (WCAG 2.4.7).

### 10.4 Notices

- Every result of an action done without a page load is announced with `wp.a11y.speak()`, once: "Marked reviewed.", "Moved to the Trash." `wp-a11y` is listed as a script dependency.
- After an action that reloads the page, `wp.a11y.speak` is unreliable. Instead focus moves to the notice (which has `tabindex="-1"`) or to the row, one or the other, and the notice is not also spoken.
- Admin notices use WordPress's notice markup (`notice notice-success`, `notice-error`) (WCAG 4.1.3 Status Messages).
- Errors say what happened and what to do, in words, next to the control they belong to (WCAG 3.3.1, 3.3.3).

### 10.5 Labelled controls and page structure

- Every input, select and button has a visible label, or an accessible name that starts with its visible text (WCAG 1.3.1, 2.5.3, 4.1.2).
- Icon-only buttons have an accessible name, and any tooltip on them can be dismissed, hovered and stays until dismissed (WCAG 1.4.13 Content on Hover or Focus).
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
| `swiftletter.py` (built) | Discovery and versions, newsletters with their total, a newsletter's articles, the edit context, Compare with Site's read, the versioned save and what it stored | `api.py` (`request`) |
| `swiftletter_errors.py` (built) | The coded refusals in section 8 | `api.py` (`WordPressApiError`) |
| `workbench_swiftletter.py` (built) | The branch's nodes, loaders and rows | `workbench_rows.py` (`WbRow`), `workbench_listing.py` |
| `workbench_swiftletter_actions.py` (later) | Context-menu rows, their tiers, help, and written reasons for having no chord | `workbench_gravity_actions.py` (`KEYLESS`), `workbench_admin_actions.py`, `workbench_tiers.py` |

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
- GATE-EC: each `QUILL-SWIFTLETTER-*` class in section 8 has its own code (`quill/tools/error_code_audit.py`).
- GATE-13: no announce on focus or title; a move in the focused list is not announced; each job stage once (`check_over_announce.py`).
- GATE-11: every new module under 600 lines (`module_size_budgets.json`). `wordpress_workbench_window.py` is near its ceiling, so the provider's new code goes in the mixin.
- GATE-14: the access-key table in 7.3 (`check_access_keys.py`).
- Menu accelerators and family rule 8: the Return to Newsletter row shows its layer key; each Workbench command has help and a written reason for having no chord (`test_menu_accelerators.py`, `test_wp_workbench_by_name.py`).
- Tiers: every new `do_` handler classified (`test_wp_workbench_tiers.py`).
- GATE-LITE-COVER: `cmd_wp_return_to_newsletter` has a behavioural test (`lite_command_coverage.json`).
- F1: authored help on the window and every control; `docs/f1-help-reference.md` regenerated (`build_help_reference.py`).
- GATE-REACH and the dialog inventory: the window reachable from an entry point (`surface_reachability_audit.py --write`, `dialog_inventory.py`).
- The Workbench reference (`python -m quill.tools.build_workbench_reference --write`), the keyboard reference, and the command catalogue and Command Key fixtures for the new row.
- A CHANGELOG entry, the SwiftLetter sections in `docs/user guide/quill-guide/quill-guide-16-wordpress.md` and the manual's Chapter 10 (written for browsing; they grow with each phase and document only what ships), and HTML and EPUB regenerated for every changed document.
- `python -m quill.tools.platform_report` clean.

### 12.2 Automated tests

- `tests/unit/core/wordpress/test_wp_swiftletter.py` and `test_wp_swiftletter_contract.py`: a fake site behind the WordPress client's opener, and a replay of SwiftLetter's shared contract fixtures (`tests/fixtures/swiftletter_contract/`, contract version 1, from payown/SwiftLetter PR #11), so neither side drifts. SwiftLetter's CI runs the same fixtures against a disposable WordPress on InnoDB (answer 28).
- Core: discovery and versions, every route, every error code, order conflicts, stale revisions, consent, jobs and downloads.
- Workbench: the branch hides on a site without SwiftLetter; rows say title, review, who and position; Enter opens the window or the article.
- Newsletter window: a move from the button announces once and sends one order; a move in the focused list announces nothing; a conflict restores the order and keeps focus; rows update in place; Mark Reviewed previews and reports per article as 7.3.4 says; Copy makes a separate article; Delete trashes; Safe Mode and Read Only refuse; an export asks for consent, speaks each stage once and opens the result.
- Editor: D on an article saves title and content only, with the conflict check; P refuses; Return to Newsletter focuses the article.

### 12.3 By hand, before merging phase 1

- NVDA and JAWS: browse the branch, open an article, save it, return, and hear the same article focused.
- Narrator: the Newsletter window's list and buttons.
- A braille display: the status line and a move result.

## 13. What we read in the SwiftLetter repository

Read on `release/1.1.0-quill-test` (1.1.0-rc.1), and folded into this PRD and the contract:

1. **Post types.** Articles are `swl_article` (REST base `swl-articles`, supporting title, editor and revisions). Newsletters are `swl_newsletter` (REST base `swl-newsletters`). SwiftLetter's own routes are under `swiftletter/v1`.
2. **Membership and order.** Each article has one parent newsletter (`_swl_newsletter_id`) and an order (`_swl_article_order`, which can have gaps). The newsletter detail lists articles sorted by it.
3. **Review.** One confirmation per article (`_swl_review_confirmed`, with who and when). Any title or body change clears it, and publishing refuses until every article is reviewed. There is no newsletter state machine.
4. **Exports.** DOCX and audio are made inside the request today, audio as one OpenAI request. Files live outside the web root; readers of a published newsletter use `?swl_download=`.
5. **Existing routes** QUILL may use later: create, copy, `articles/reorder`, `confirm-review`, versions and restore, the newsletter audit log, audio, and `publish-post`.
6. **Admin screen.** `admin.php?page=swiftletter`.

## 14. Open questions

For Jeff:

1. Is Shift+N on the WordPress layer right for Return to Newsletter, or should it stay unkeyed (reached from File > WordPress)?
2. Should the Newsletter window save each move at once, as Menus > Arrange Items does today, or move locally and save with one Save Order button?

Decided: the phases follow section 6, in Michael's order, each behind its feature flag. The shared code keeps working on macOS now; QUILL's macOS release with VoiceOver testing comes later (answer 35).

## 15. Michael's answers, 2026-11-22

Michael (payown, SwiftLetter's maintainer) answered our questions by number. In short, with what each means for QUILL:

1. A save on a published newsletter's article leaves the public post and its Word download unchanged until review. SwiftLetter's fix.
2. Yes to a 409 when another user holds an active WordPress post lock, with a sentence naming them ("Pat Reyes is editing this article in WordPress. Your changes are still in QUILL."). An expired lock does not block. The version check stays. No automatic retry. QUILL: `SwiftLetterArticleLocked`, with the code `swiftletter_article_locked` until SwiftLetter's branch names it.
3. The 412 stays small. Compare with Site fetches the current article through the existing authenticated edit route, leaves the local copy untouched and never retries the save. QUILL: `current_article`.
4. A successful save returns the stored title and content with the new `edit_version`. If WordPress changed the content while sanitising it, QUILL tells the editor and offers Compare, and uses the stored version as the baseline without silently replacing the local copy or edits made during the save. QUILL: `save_article_stored` and `SavedArticle`. SwiftLetter's CI found one such change already: kses stores an image's `"/>` as `" />` on a contributor's save.
5. A title-only rename requires review. A restore requires it if it changes the title or body. A no-op or metadata-only save keeps the review.
6. `changed` is the slug for Changed since review; the previous reviewer and time are kept as history. Three states, the same words in the dashboard and QUILL; only Reviewed counts toward publication.
7. Each article row gets `modified_gmt` and `modified_by` (the display name of whoever last changed the title or body); `null` when unknown, shown as "Editor unknown".
8. Each article row gets `can_edit`, separate from `can_review`. Both are interface hints; SwiftLetter checks every request.
9. Use the `articles` array's order and say "3 of 8"; never the stored values or a re-sort.
10. `message` is written to be read aloud as it is. Use the code to decide what to offer next; never read the code aloud. The non-InnoDB 503 gets an actionable sentence (section 8).
11. Accept any `1.x`; explain once on a major version QUILL does not support. Minor versions only add fields, routes and flags. Missing flags are off; permissions are checked separately. The next flags: versioned reordering, review history, then export jobs.
12. Keep three pages and More; say how many are shown and how many remain when WordPress gives the total. No `search` or `status` filter in Phase 1.
13. Markdown or HTML in QUILL; SwiftLetter receives block markup. Keep blocks that cannot be converted intact; test headings and anchors, links, images and alt text, and nested blocks before enabling Markdown saves; stop the remote save and explain if something cannot be preserved. Michael's editor work.
14. Phase 1 supports self-hosted WordPress, including managed hosts. WordPress.com connections are out of scope for now.
15. Versioned reorder: one endpoint and newsletter version token for the dashboard and QUILL, every article exactly once, all or nothing, 409 with the current order, focus kept, no automatic retry.
16. Review history from the newsletter audit log; older entries are history, not proof of a revision. Revision-based review records the exact revision. No notes or stages.
17. Use SwiftLetter's create and copy routes; a copy is a separate article. Newsletter deletion stays out of QUILL until the Trash keeps and restores its articles and their order.
18. Split audio by article (long articles at headings or paragraphs), progress "Article 3 of 8", keep the old recording until the new one is complete, run as a job. The consent notice comes through the API, names OpenAI, and says text is sent and may cost money; explicit consent first.
19. One export job API for both: `202` and a job id; Queued, Running, Ready or Failed with a readable message; an authenticated download. DOCX first, then audio. No duplicate job or charge on a retried start; a failure keeps the last good export.
20. QUILL uses an authenticated REST download route (`?swl_download=` does not take application passwords). Permission is checked per newsletter each time, with `Cache-Control: private, no-store`, and no public fallback for an unpublished export.
21. DOCX import should keep lists, tables, safe links and Word's alt text, keep decorative images decorative and flag images needing a description; imported draft images stay private. Separate changes, not holding up Phase 1.
22. Generated alt text only as an editable suggestion a person confirms; never from the attachment title alone; ask before sending an image to a provider.
23. QUILL uses its own AI tools with the provider the editor chose, only when asked. Opening, saving, reviewing or exporting never triggers AI.
24. Test 1.1.0-rc.1 now; the section 1 fixes come before 1.1.0 final, the lock and stored content first. Each change on its own branch with a regression test, based on the Phase 1 save branch; nothing to `main` before verification.
25. Phase order: versioned reorder, then revision-based review and history; then DOCX export jobs and authenticated downloads, then split audio on the same job API. DOCX import separate. The same routes for the dashboard and QUILL, with PHPUnit tests and a WordPress integration check each.
26. WCAG 2.2 AA for the dashboard and the editor sidebar: visible Move Up and Move Down, focus kept, one announcement per action through `wp.a11y.speak`, Restore names its version, Delete returns focus, consent before paid audio; verified by hand on Windows and macOS.
27. `event.code` for modified letter shortcuts on Mac, `event.key` for arrows; test VoiceOver in Safari and a non-US layout; every action also has a labelled button.
28. The Phase 1 REST checks run in CI against a disposable WordPress on InnoDB, with shared contract fixtures for QUILL's fake server (now payown/SwiftLetter PR #11, replayed by QUILL's tests). Synthetic content, temporary credentials, no paid providers.
29. We cover NVDA with Firefox, JAWS with Chrome or Edge, Narrator, and braille, for QUILL and the dashboard; Michael covers VoiceOver in Safari, and QUILL on Mac once there is a build. The same sign-off format.
30. A SwiftLetter chapter in QUILL's guide, matching SwiftLetter's docs; consistent menu names; document only what ships. Browsing is documented now, the rest as it ships.
31. Start with a QUILL command that sends the approved DOCX to Scribe after the editor confirms; no automatic send-back; a separate Attach to Newsletter later; private until then. Not in 1.1.0.
32. Getting articles in through Scribe starts in QUILL; the contributor confirms and corrects before a draft is created; nothing automatic; separate from DOCX import; not in 1.1.0.
33. SwiftLetter's own Scribe integration comes later, with its own registration with Pneuma, after the job API and private files; editors confirm before a DOCX leaves the site.
34. We install 1.1.0-rc.1 ourselves from SwiftLetter PR #9, backing up first. A fictional newsletter, an editor and a contributor with temporary application passwords, and a stale-save test. No real content or paid calls.
35. Michael develops on macOS 27.0.1 on Apple Silicon with Python 3.14.10. Keep the shared code working on Mac now; ship on Windows first after NVDA testing; Mac inside QUILL when there is a tested build.
36. Follow-up commits may go on the existing PR branches (client changes on #1999's, Workbench changes on #2000's), with a note to Michael when they are up. `changed` is confirmed; keep the `review_confirmed` fallback. No pushes to `main` or merges before verification.
37. Not answered yet.
38. Add the GPL-2.0 `LICENSE` file; contributions come under GPL-2.0-or-later.
39. Remove the generated exports from the tree and stop committing release ZIPs; no history rewrite for now.
40. Stop tracking the plugin's `.claude/settings.local.json` without deleting local copies.
