# SwiftLetter REST Contract for QUILL

Version 1.0, **proposed**. 2026-11-21.

This is the REST contract QUILL needs from SwiftLetter, written for the SwiftLetter maintainers to review. Nothing here exists in SwiftLetter 1.0.9 yet. The maintainers offered to build the contract we document (issue Community-Access/quill#1992), so this is that document. When they agree, or change it, this file is updated and its status moves from proposed to agreed.

Nothing is built in QUILL yet. QUILL's side will be built against a fake server that follows this contract exactly (`tests/unit/core/wordpress/fake_swiftletter.py`), and the contract will be checked against SwiftLetter's code once we can read it. If the real routes differ, only `quill/core/wordpress/swiftletter.py` and `swiftletter_contract.py` will need to change.

The product requirements for both sides are in `docs/planning/swiftletter-prd.md`.

## 1. Principles

- **SwiftLetter is the source of truth.** QUILL and the WordPress dashboard edit the same records. Neither keeps a private copy the other cannot see.
- **No second login.** QUILL signs every request with the WordPress application password the person already connected. SwiftLetter checks capabilities on every request. A hidden button in QUILL is never the permission boundary.
- **Articles are posts.** An article is a REST-enabled custom post type, so QUILL's existing post machinery works on it unchanged: working copies, the `modified_gmt` conflict check, revisions, Trash and Restore, the offline queue and `batch/v1`.
- **Three separate operations.** Saving a draft, marking a revision reviewed and publishing are three different requests. No request does two of them.
- **One article, many newsletters.** An article in several newsletters is one post. Unlinking it from a newsletter never deletes it.
- **Private files stay private.** Exports and audio are downloaded through an authenticated REST route. QUILL never asks for, and SwiftLetter never returns, a public media address for a draft or a generated file.
- **Nothing costly happens by itself.** A request that spends money or calls an outside provider carries an explicit `consent` flag, and SwiftLetter refuses it without one.

## 2. Discovery and versions

### 2.1 Is SwiftLetter there

QUILL reads the site's REST index (`GET /wp-json/`) once when it connects. SwiftLetter is present when the index's `namespaces` list includes `swiftletter/v1`. A site without it behaves exactly as before: no SwiftLetter branch, no SwiftLetter command does anything but say so.

### 2.2 `GET /swiftletter/v1`

WordPress answers this route itself with the namespace index (`namespace`, `routes`). SwiftLetter adds one key, `swiftletter`, through the core `rest_namespace_index` filter, so no new route is needed:

```json
{
  "namespace": "swiftletter/v1",
  "routes": { "...": "..." },
  "swiftletter": {
    "plugin_version": "1.0.9",
    "api_version": "1.0",
    "article_rest_base": "swiftletter_article",
    "capabilities": {
      "read": true,
      "create_newsletters": true,
      "edit_newsletters": true,
      "change_state": false,
      "create_articles": true,
      "edit_articles": true,
      "delete_articles": true,
      "reorder": true,
      "link_articles": true,
      "review": false,
      "export_docx": true,
      "generate_audio": false
    },
    "states": [
      {"slug": "draft", "label": "Draft"},
      {"slug": "in_review", "label": "In review"},
      {"slug": "ready", "label": "Ready"},
      {"slug": "sent", "label": "Sent"}
    ],
    "review_states": [
      {"slug": "not_reviewed", "label": "Not reviewed"},
      {"slug": "reviewed", "label": "Reviewed"},
      {"slug": "changed", "label": "Changed since review"}
    ],
    "generation": {
      "docx": {"paid": false, "provider": ""},
      "audio": {
        "paid": true,
        "provider": "The text-to-speech service set in SwiftLetter's settings",
        "notice": "Audio is made by an outside speech service and may cost money."
      }
    }
  }
}
```

- `capabilities` are **for the signed-in user**, after SwiftLetter's editorial rules. QUILL uses them to say "you are not allowed" before trying, and to dim commands. The server still checks every request.
- `states` and `review_states` carry their own labels, so QUILL speaks SwiftLetter's words and needs no release when a state is added. QUILL treats any slug it does not know as "unknown" and still shows its label.
- `generation` says which exports are paid or use an outside provider. QUILL asks the person before any request where `paid` is true or `provider` is not empty, and shows `notice` in that question.

### 2.3 Versions

- `api_version` is `major.minor`. QUILL 1.0 works with any `1.x`. A minor version may add fields and routes, never remove or rename one.
- A different major version, a missing `swiftletter` key, or an unreadable `api_version` makes QUILL say one sentence and do nothing else: "SwiftLetter on this site speaks version 2.0 of its connection, and this QUILL knows version 1. Update QUILL, or ask the site's administrator." (QUILL-SWIFTLETTER-API-VERSION).

## 3. Articles: `wp/v2/swiftletter_article`

The article post type is registered with `show_in_rest => true`, `rest_base => 'swiftletter_article'`, and `supports` including `title`, `editor`, `author`, `revisions` and `custom-fields`. Every standard `wp/v2` route works on it:

| Request | What QUILL uses it for |
|---|---|
| `GET wp/v2/swiftletter_article/<id>?context=edit` | Open an article as a working copy |
| `POST wp/v2/swiftletter_article/<id>` | Save Article to SwiftLetter (title and content only) |
| `POST wp/v2/swiftletter_article` | New Article |
| `DELETE wp/v2/swiftletter_article/<id>` | Delete (to the Trash) |
| `POST wp/v2/swiftletter_article/<id>` with `status` from the Trash | Restore |
| `GET wp/v2/swiftletter_article/<id>/revisions` | Earlier Versions |
| `batch/v1` | Several saves in one request, when the site allows it |

### 3.1 The `swiftletter` field

SwiftLetter registers one REST field on the type, read-only through `wp/v2`:

```json
"swiftletter": {
  "newsletters": [{"id": 12, "title": "Winter 2026", "position": 3}],
  "review_state": "changed",
  "reviewed_revision": 881,
  "current_revision": 905,
  "modified_by": {"id": 7, "name": "Pat Reyes"}
}
```

- `current_revision` is the id of the newest revision of the article, the one a review would be for.
- `modified_by` is the person who made `current_revision`. For a save QUILL made, that is the WordPress user, and the revision's own record keeps the application password's name (section 9).

### 3.2 Saving

- QUILL sends only `title` and `content`. It never sends `status`, so saving never publishes or unpublishes.
- Saving creates a revision, as WordPress always does.
- If the article was `reviewed`, saving changes its `review_state` to `changed`. A save never marks anything reviewed.
- **Conflicts.** Before saving, QUILL reads `modified_gmt` and compares it with the value it opened the article at, as it does for every post. If they differ, nothing is sent and the person chooses Keep Theirs or Use Mine.
- **Optional stronger check.** If SwiftLetter sends an `ETag` header on `GET`, QUILL sends it back as `If-Match` on the save, and the site answers `412 Precondition Failed` with the current article (section 7) when it no longer matches.

## 4. Newsletters

### 4.1 The newsletter object

```json
{
  "id": 12,
  "title": "Winter 2026",
  "state": "draft",
  "state_label": "Draft",
  "article_count": 8,
  "modified_gmt": "2026-11-20T15:04:00",
  "modified_by": {"id": 7, "name": "Pat Reyes"},
  "version": "n12-41"
}
```

`version` is an opaque token that changes whenever the newsletter's title, state or article order changes.

### 4.2 Routes

| Request | Body or query | Answer |
|---|---|---|
| `GET swiftletter/v1/newsletters` | `page`, `per_page` (up to 100), optional `state` | A list of newsletter objects, with `X-WP-Total` and `X-WP-TotalPages` |
| `GET swiftletter/v1/newsletters/<id>` | | One newsletter object |
| `POST swiftletter/v1/newsletters` | `{"title": "..."}` | `201` and the new newsletter, state `draft` |
| `POST swiftletter/v1/newsletters/<id>` | `{"title": "...", "version": "..."}` | The renamed newsletter |
| `POST swiftletter/v1/newsletters/<id>/state` | `{"state": "ready", "version": "..."}` | The newsletter in its new state |

Rename and state changes carry `version`. A stale version is refused with `409 swiftletter_version_conflict` and the current newsletter (section 7).

## 5. Articles in a newsletter, in order

### 5.1 `GET swiftletter/v1/newsletters/<id>/articles`

```json
{
  "newsletter_id": 12,
  "version": "n12-41",
  "articles": [
    {
      "id": 301,
      "title": "From the chair",
      "position": 1,
      "status": "draft",
      "review_state": "reviewed",
      "review_label": "Reviewed",
      "reviewed_revision": 880,
      "current_revision": 880,
      "modified_gmt": "2026-11-19T10:00:00",
      "modified_by": {"id": 7, "name": "Pat Reyes"},
      "newsletters": [12]
    }
  ]
}
```

`position` starts at 1 and has no gaps. The list is always in newsletter order.

### 5.2 Set the whole order in one request

`PUT swiftletter/v1/newsletters/<id>/articles/order`

```json
{"order": [304, 301, 302, 303], "version": "n12-41"}
```

- `order` must name every article in the newsletter exactly once, or the site answers `400 swiftletter_order_incomplete`.
- A stale `version` is refused with `409 swiftletter_version_conflict`, carrying the current order (section 7), so QUILL can say what changed and offer to apply the person's move again.
- The answer is the same shape as `GET .../articles`, with the new `version`.

### 5.3 Link and unlink

| Request | Body | What happens |
|---|---|---|
| `POST swiftletter/v1/newsletters/<id>/articles` | `{"article_id": 309, "position": 4, "version": "..."}` | Links an existing article; `position` is optional (default: last) |
| `DELETE swiftletter/v1/newsletters/<id>/articles/<article_id>?version=...` | | Unlinks it. **The article is not deleted** and stays in every other newsletter |

Both answer with the newsletter's articles and new `version`. Linking an article already in the newsletter is `409 swiftletter_already_linked`.

## 6. Review, exports and jobs

### 6.1 Mark a revision reviewed

`POST swiftletter/v1/articles/<id>/review`

```json
{"revision": 905, "note": ""}
```

- The site marks **that revision** reviewed. If the article's `current_revision` is no longer 905, it refuses with `409 swiftletter_revision_stale` and the current revision id, so a review can never land on text the reviewer did not read.
- SwiftLetter's editorial rules apply (for example, an author not reviewing their own article): `403 swiftletter_review_not_allowed`, with a `message` QUILL speaks as it is.
- The answer: `{"id": 301, "review_state": "reviewed", "reviewed_revision": 905, "reviewed_by": {"id": 3, "name": "Sam"}, "reviewed_gmt": "..."}`.

### 6.2 Review history

`GET swiftletter/v1/articles/<id>/reviews` answers a list, newest first:

```json
[{"revision": 905, "reviewer": {"id": 3, "name": "Sam"}, "reviewed_gmt": "2026-11-20T09:00:00", "note": ""}]
```

### 6.3 Exports and generation

`POST swiftletter/v1/newsletters/<id>/exports`

```json
{"format": "docx", "consent": false}
```

- `format` is `docx` or `audio`.
- When `generation.<format>.paid` is true or `provider` is set, `consent` must be `true`, or the site answers `428 swiftletter_consent_required`. QUILL sends `true` only after the person said yes in a dialog that showed SwiftLetter's `notice`.
- The answer is `202` and a job: `{"job": "j-77", "state": "queued", "stage": "queued", "stage_label": "Waiting to start"}`.

### 6.4 Jobs

`GET swiftletter/v1/jobs/<job>`

```json
{
  "job": "j-77",
  "newsletter_id": 12,
  "format": "audio",
  "state": "running",
  "stage": "speaking",
  "stage_label": "Making audio, article 3 of 8",
  "error": "",
  "file": null
}
```

- `state` is `queued`, `running`, `done` or `failed`. `stage` and `stage_label` say what is happening now, in SwiftLetter's words.
- QUILL asks every 3 seconds while the Newsletter window is open, at most 20 minutes, and speaks a stage once when it changes.
- When `state` is `done`, `file` is `{"name": "winter-2026.docx", "size": 48213, "content_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document"}`.
- When `state` is `failed`, `error` is one sentence QUILL speaks as it is.

### 6.5 Download

`GET swiftletter/v1/jobs/<job>/file` streams the file with its `Content-Type` and `Content-Disposition`. It checks the same capability as reading the newsletter. It is never a public media address, never cached publicly (`Cache-Control: private, no-store`), and the job's file may be removed by SwiftLetter after a day.

## 7. Errors and concurrency

Every refusal is WordPress's usual error body, with a `swiftletter_` code and the HTTP status in `data.status`:

```json
{"code": "swiftletter_version_conflict", "message": "Someone changed this newsletter.", "data": {"status": 409, "current": {"...": "..."}}}
```

| Code | Status | Meaning | `data.current` |
|---|---|---|---|
| `swiftletter_forbidden` | 403 | Capability or editorial rule says no | |
| `swiftletter_review_not_allowed` | 403 | This person may not review this article | |
| `swiftletter_not_found` | 404 | No such newsletter, article or job | |
| `swiftletter_not_linked` | 404 | The article is not in this newsletter | |
| `swiftletter_already_linked` | 409 | Already in this newsletter | |
| `swiftletter_version_conflict` | 409 | The newsletter changed since `version` | The newsletter, or its articles for an order change |
| `swiftletter_revision_stale` | 409 | The article changed since that revision | `{"current_revision": 912}` |
| `swiftletter_precondition_failed` | 412 | `If-Match` no longer matches | The article |
| `swiftletter_order_incomplete` | 400 | The order does not name every article once | |
| `swiftletter_invalid_state` | 400 | That state change is not allowed from here | |
| `swiftletter_consent_required` | 428 | A paid or provider export without consent | |
| `swiftletter_generation_unavailable` | 503 | Exports are switched off or misconfigured | |

QUILL maps each to one plain sentence and an error code (`QUILL-SWIFTLETTER-*`, in `quill/core/wordpress/swiftletter_contract.py`). The `message` SwiftLetter sends is spoken when QUILL has no better sentence, so a new editorial rule explains itself.

## 8. Permissions

- WordPress capabilities first: the article type maps `edit_posts`-style capabilities (`edit_swiftletter_articles` and friends), so roles can be set with any role plugin.
- SwiftLetter's editorial rules second, applied on the server to every route. The discovery `capabilities` object is a summary of both for the signed-in user.
- A request QUILL makes is never more powerful than the same action in the dashboard.

## 9. Seeing each other's changes

- Edits made through REST create ordinary WordPress revisions. WordPress records which application password made each REST request (`_application_passwords` last used, and the `application_password_used` action), and SwiftLetter's revision list in the dashboard names it: "Pat Reyes, from QUILL (application password 'Pat's laptop')".
- QUILL shows `modified_by` on every article row, so a person in QUILL sees who last changed it in the dashboard.
- Nothing is cached by SwiftLetter for QUILL. A refresh in QUILL (F5) reads the current state.

## 10. What QUILL sends, in one list

- The REST index, once per connection.
- `GET swiftletter/v1` once per site per session, and on refresh.
- Reads when the person opens a node, a newsletter or an article.
- Writes only on a deliberate command: Save Article to SwiftLetter, Save Order, Link, Unlink, New, Rename, Delete, Restore, Mark Reviewed, Export DOCX, Generate Audio.
- Job status every 3 seconds while a job the person started is running and its window is open.
- Nothing in Safe Mode or in Workbench Read Only access, except reads.

## 11. Contract tests

The SwiftLetter maintainers offered automated contract tests. QUILL's fake server will be a reference: each route above will have a test in `tests/unit/core/wordpress/test_swiftletter_contract.py`, and a real site's answers can be replayed against those tests.

## 12. Open questions for the SwiftLetter maintainers

1. Is `rest_namespace_index` the way you would like to publish discovery, or would you prefer a separate `swiftletter/v1/about` route? QUILL can read either.
2. Do your newsletter states match `draft`, `in_review`, `ready` and `sent`, and which changes are allowed from which state?
3. Should a newsletter's own text (an introduction, a footer) be an article, or a field on the newsletter?
4. Is audio made per article, per newsletter, or both? The contract assumes per newsletter, with progress per article.
5. How long do you keep a generated file, and can the same job's file be downloaded twice?
6. Can a 1.0.9 build with these routes be put on our test site, so QUILL's tests can be checked against the real thing?
