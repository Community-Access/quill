# SwiftLetter REST Contract for QUILL

API version 1.x, as built in SwiftLetter 1.1.0-rc.1 (branch `release/1.1.0-quill-test`, SwiftLetter PR #9). Corrected to the real API on 2026-11-22, replacing the proposal of 2026-11-21.

This is the REST API QUILL uses, as SwiftLetter's maintainer, Michael (payown), built it for issue Community-Access/quill#1992, with the changes he agreed on 2026-11-22. Sections 1 to 6 are what 1.1.0-rc.1 does today. Section 7 is what is agreed and not yet built, in the order it will be built. The product requirements, including Michael's answers by number, are in `docs/planning/swiftletter-prd.md` (section 15).

QUILL's client is `quill/core/wordpress/swiftletter.py`, with its errors in `swiftletter_errors.py`. SwiftLetter's shared contract fixtures (payown/SwiftLetter PR #11, `tests/contract/fixtures/`, `"contract_version": 1`) are run by SwiftLetter's CI against a disposable WordPress on InnoDB, and replayed by QUILL's `tests/unit/core/wordpress/test_wp_swiftletter_contract.py` from its copy in `tests/fixtures/swiftletter_contract/`.

## 1. Principles

- **SwiftLetter is the source of truth.** QUILL and the WordPress dashboard edit the same records, through the same routes.
- **No second login.** QUILL signs every request with the application password the person already connected. SwiftLetter checks permissions on every request; a flag or hint in a response is never the permission boundary.
- **Self-hosted only.** Phase 1 supports self-hosted WordPress, including managed hosts where SwiftLetter can be installed. QUILL never looks for SwiftLetter on a WordPress.com connection.
- **Saving is not reviewing or publishing.** A save sends title and content only. It never publishes, never marks anything reviewed, and leaves a published newsletter's public post and Word download unchanged until review.
- **Nothing is retried automatically.** A refused save stays refused until the person acts; their local copy stays in QUILL.
- **Nothing costly, and no AI, by itself.** QUILL's own AI runs only when the editor asks. A paid export (audio) needs the person's explicit consent, through SwiftLetter's notice.

## 2. The data model

- **Newsletters** are the post type `swl_newsletter` (REST base `swl-newsletters`, supports `title`).
- **Articles** are the post type `swl_article` (REST base `swl-articles`, supports `title`, `editor` and `revisions`). Content is block markup.
- **One parent newsletter.** Each article belongs to one newsletter (`_swl_newsletter_id`). There is no linking one article into several newsletters. A copy is a separate article.
- **Order.** Each article has `_swl_article_order`. The values can have gaps; the newsletter detail returns its `articles` array sorted by them. QUILL shows that array's order and says each article's position as "3 of 8", never the stored value, and never re-sorts.
- **Review.** One confirmation per article (`_swl_review_confirmed`, with who and when). Any change to the title or body clears it; a no-op or metadata-only save does not. Publishing refuses until every article is reviewed.
- **No state machine.** A newsletter is a draft or published WordPress post. There are no `in_review`, `ready` or `sent` states.
- **Exports are made inside the request today.** DOCX and audio (one OpenAI request for an article or a newsletter, with a 120-second timeout). Files are stored outside the web root.

## 3. Discovery: `GET /swiftletter/v1`

QUILL reads the site's REST index (`GET /wp-json/`) once. SwiftLetter is present when its `namespaces` list includes `swiftletter/v1` (slashes ignored). Then QUILL reads the namespace index, to which SwiftLetter adds one key:

```json
{
  "namespace": "swiftletter/v1",
  "routes": { "...": "..." },
  "swiftletter": {
    "plugin_version": "1.1.0-rc.1",
    "api_version": "1.0",
    "article_rest_base": "swl-articles",
    "capabilities": { "read": true },
    "features": { "browse": true, "article_context": true, "article_save": true }
  }
}
```

- The answer is `Cache-Control: no-store`. An anonymous caller gets `"read": false`.
- `capabilities.read` is for the signed-in user. QUILL browses only when it and `features.browse` are true.
- **Versions.** QUILL accepts any `1.x` (`1`, `1.2`, `1.2.3`). A minor version may add fields, routes and feature flags, never remove one or change what it means. A `2.x` or later, or a missing `api_version`, is refused in one sentence, said once ("SwiftLetter on this site uses version 2.0 of its connection, which needs a newer QUILL.", `QUILL-SWIFTLETTER-API-VERSION`).
- **Feature flags.** A missing flag is off. QUILL shows each command only when its flag is on: `browse` (the Workbench branch), `article_context` (open an article), `article_save` (Save to SwiftLetter). The next flags expected are for versioned reordering and review history, then export jobs.
- A namespace index without the `swiftletter` key is a SwiftLetter too old for QUILL; the Workbench says to update it.
- QUILL reads discovery once per site, keeps it five minutes, and reads it again when the site changes.

## 4. Browsing newsletters

### 4.1 `GET /swiftletter/v1/newsletters`

`page` and `per_page` (up to 100). The answer is a list of newsletter objects, with `X-WP-Total` and `X-WP-TotalPages`:

```json
{ "id": 9, "title": "December", "article_count": 2, "modified_gmt": "2026-11-20T15:04:00" }
```

QUILL reads the Workbench's usual three pages, with Load More and Load All. When `X-WP-Total` is sent, the list says how many newsletters remain past those shown. A contributor's list leaves out newsletters they may not edit. There is no `search` or `status` filter in Phase 1.

### 4.2 `GET /swiftletter/v1/newsletters/<id>`

One newsletter with its `articles`, in newsletter order. Each article row today:

```json
{ "id": 4, "title": "From the chair", "order": 0, "review_confirmed": false,
  "can_review": true, "has_audio": false, "edit_url": "https://example.org/wp-admin/post.php?post=4&action=edit" }
```

Agreed additions to each row (answers 6 to 8), which QUILL already reads when present:

| Field | Meaning | QUILL shows |
|---|---|---|
| `review_state` | `reviewed`, `not_reviewed` or `changed` | Reviewed, Not reviewed, Changed since review. Without it, QUILL falls back to `review_confirmed` |
| `modified_gmt` | When the title or body last changed | "Last changed 20 November 2026, 3:04 PM" |
| `modified_by` | That person's WordPress display name, or `null` when it cannot be verified | Their name, or "Editor unknown"; never guessed from the byline |
| `can_edit` | Whether this person may open and edit it | "Your account cannot edit this article." when false |
| `can_review` | Whether this person may confirm its review (separate from `can_edit`) | Kept for Mark Reviewed |

`can_edit` and `can_review` are interface hints; SwiftLetter still checks every request. A contributor gets `403` on a newsletter they may not edit.

## 5. Opening an article: `GET /wp/v2/swl-articles/<id>?context=edit`

WordPress's own route, with one read-only field SwiftLetter adds in the edit context only:

```json
{
  "id": 4,
  "title": { "raw": "From the chair" },
  "content": { "raw": "<!-- wp:paragraph --><p>...</p><!-- /wp:paragraph -->" },
  "swiftletter": {
    "newsletters": [{ "id": 9, "title": "December" }],
    "review_state": "not_reviewed",
    "edit_version": "\"<64 hex digits>\""
  }
}
```

- `newsletters` holds the one parent, when this person may edit it (an author may open their own article without access to its newsletter; the list is then empty).
- `edit_version` is a quoted SHA-256 of the stored title and content, the same snapshot as `title.raw` and `content.raw`. Reopening an unchanged article gives the same version. The answer is `Cache-Control: private, no-store`.
- The `view` context does not carry the `swiftletter` field. Anonymous callers get `401`.
- **Compare with Site** reads this same route again: the latest title and content at the moment of comparing, with the local copy untouched (answer 3).

## 6. Saving an article: `POST /swiftletter/v1/articles/<id>/save`

```http
If-Match: "<edit_version>"
Content-Type: application/json

{"title": "From the chair", "content": "<!-- wp:paragraph --><p>...</p><!-- /wp:paragraph -->"}
```

- The body is exactly `title` and `content`; anything else (such as `status`) is refused.
- The route takes a row lock, compares the version in constant time, and writes through `wp_update_post`, so sanitisation, revisions and the review reset still run. When nothing changed, nothing is written.
- The answer today: `200`, `{"id": 4, "edit_version": "\"...\""}`, with `ETag` set to the new version and `Cache-Control: private, no-store`.
- **Agreed (answer 4):** the answer also returns the `title` and `content` WordPress stored. QUILL reads them when present (as text or as `{"raw": ...}`), and treats any difference from what it sent as WordPress having changed it, for example kses storing an image's `"/>` as `" />` on a contributor's save. QUILL then tells the person and offers Compare, and uses the stored text as the baseline for the next `If-Match`, without silently replacing the local copy.
- QUILL sends a save once and never retries it.

### 6.1 Refusals

Each is WordPress's usual error body, `{"code", "message", "data": {"status"}}`. SwiftLetter's `message` is written to be read aloud, and QUILL says it exactly as written, never the code. The code decides what QUILL offers next.

| Code | Status | Message today | QUILL |
|---|---|---|---|
| `swiftletter_version_required` | 428 | "Refresh the article before saving." | `QUILL-SWIFTLETTER-API-VERSION-REQUIRED`; offers to reopen |
| `swiftletter_invalid_version` | 400 | "The article version is invalid. Refresh the article and try again." | `QUILL-SWIFTLETTER-API-INVALID-VERSION`; offers to reopen |
| `swiftletter_invalid_save` | 400 | "Send the article title and content only." | `QUILL-SWIFTLETTER-API-INVALID-SAVE` |
| `swiftletter_article_unavailable` | 404 | "This article is no longer available to edit." | `QUILL-SWIFTLETTER-API-ARTICLE-UNAVAILABLE` |
| `swiftletter_forbidden` | 403 | "You cannot edit this article." | `QUILL-SWIFTLETTER-API-FORBIDDEN` |
| `swiftletter_precondition_failed` | 412 | "This article changed on the site. Refresh it before saving." | `QUILL-SWIFTLETTER-API-CONFLICT`; offers Compare with Site |
| `swiftletter_save_unavailable` | 503 | "The site could not verify the save. Refresh the article before trying again." | `QUILL-SWIFTLETTER-API-SAVE-UNAVAILABLE` |
| `swiftletter_article_locked` (agreed, answer 2) | 409 | "Pat Reyes is editing this article in WordPress. Your changes are still in QUILL." | `QUILL-SWIFTLETTER-API-ARTICLE-LOCKED` |

- The 412 stays small: no current article in the body (answer 3).
- The 409 is sent when another user holds an active WordPress post lock; an expired lock does not block. The version check stays as well.
- For a 503 caused by a posts table that is not InnoDB, SwiftLetter will say: "This site can't safely save articles from QUILL. Ask your WordPress administrator to check that the posts table uses InnoDB. Your changes are still in QUILL."
- When a refusal has no `message`, QUILL says its own sentence (PRD section 8). A refusal that is WordPress's rather than SwiftLetter's (such as `rest_forbidden`) keeps WordPress's sentence.

## 7. Agreed next, in order

Each change lands in SwiftLetter first, on its own branch with PHPUnit tests and a WordPress integration check, behind a discovery feature flag. The dashboard and QUILL use the same routes.

1. **Phase 1 fixes before 1.1.0 final.** The 409 post-lock refusal and the stored title and content in the save answer first. Then review resets only when the title or body changes, and a save leaves a published newsletter's public post and Word download unchanged until review.
2. **Versioned reorder.** `POST /swiftletter/v1/articles/reorder` gains a newsletter version token. The request names every current article exactly once; the server saves the whole order or none of it; a stale version gets `409` with the current order. Both editors keep focus on the same article and let the person try again; no automatic retry.
3. **Revision-based review and history.** QUILL reads `GET /swiftletter/v1/newsletters/<id>/audit-log` for who confirmed a review, when, and when it was reset. Older entries are history, not proof that a revision was reviewed; new entries record the exact revision approved. No review notes or stages.
4. **DOCX export jobs and authenticated downloads.** Starting an export answers `202` and a job id. Its status is Queued, Running, Ready or Failed, with a readable progress message. A retried start never makes a second job or a second charge, and a failed job keeps the last good export. The result is downloaded through an authenticated REST route that checks the editor's permission on that newsletter each time and streams with `Cache-Control: private, no-store`; QUILL never uses `?swl_download=`, which application passwords do not authenticate, and never gets a public fallback URL for an unpublished export. Readers' links for published newsletters stay as they are.
5. **Split audio, on the same job API.** By article, and long articles at headings or paragraph boundaries, with progress "Article 3 of 8". The existing recording stays until the new one is complete. SwiftLetter provides the consent notice through the API, so QUILL and the dashboard show the same words: it names OpenAI, says the newsletter text is sent to it, and that the request may cost money. SwiftLetter requires explicit consent before starting.

Also agreed, outside that order:

- **Create and copy articles** through SwiftLetter's existing routes. A copy is a separate article.
- **Newsletter deletion stays out of QUILL** until deleting moves a newsletter to the Trash and restoring brings back its articles in their order, in both QUILL and the dashboard.
- **DOCX import** improvements (lists, tables, safe links, Word's alt text, private draft images) are separate changes and do not hold up Phase 1.
- **Generated alt text** is only an editable suggestion a person confirms, never written from the attachment title alone.
- **Scribe for Documents.** Later, QUILL's "Make Accessible Editions with Scribe" sends the approved newsletter DOCX to Scribe after the editor confirms. Editions are not sent back to SwiftLetter automatically; a separate Attach to Newsletter comes once the formats are tested. Not part of 1.1.0.

## 8. What QUILL sends, in one list

- The REST index, once per connection.
- `GET /swiftletter/v1` once per site, again after five minutes or when the site changes.
- `GET /swiftletter/v1/newsletters` (up to three pages, more on Load More) and `GET /swiftletter/v1/newsletters/<id>` when the person opens the branch or a newsletter.
- `GET /wp/v2/swl-articles/<id>?context=edit` when the person opens an article or chooses Compare with Site.
- `POST /swiftletter/v1/articles/<id>/save` only on Save to SwiftLetter, once, with `If-Match`.
- Nothing on a WordPress.com connection. Nothing that publishes, reviews, calls an AI or a paid provider. Nothing in Safe Mode or Workbench Read Only access except reads.
