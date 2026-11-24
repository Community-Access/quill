# Scribe for Documents API coverage

Date: 24 November 2026.

This audit lists every endpoint, field and channel message that the Scribe for Documents API offers. For each one it says whether QUILL uses it, and, if QUILL does not, whether people need it from QUILL.

## Sources

There is still no published HTTP reference, so the audit is read from these sources:

- **Pneuma's client library.** `github.com/PneumaSolutions/scribe-api-client`, the Rust crate `crates/scribe-client/src` (`client.rs`, `channel.rs`, `model.rs`, `auth.rs`, `error.rs`). It was read at commit `c74a2dc` of 23 November 2026, "Send state with the authorize request, and carry the documents channel's chunk index". PRD section 7.1 names this crate as the reference.
- **The PRD.** `docs/planning/scribe-for-documents-prd.md`, sections 3, 7 and 16 (Pneuma's answers of 21 November 2026).
- **Pneuma's test corpus README.** `D:\scribe-corpus\corpus\scribe-test-corpus-2026-11\README.md`, for the settings names and default values.
- **QUILL's own client.** `quill/core/scribe/` (`client.py`, `auth.py`, `channel.py`, `model.py`, `runner.py`).

No endpoint is guessed. Anything not in the crate is not listed.

Line numbers below are on branch `feat/scribe-api-coverage`, after this change.

## Summary

- **Used before this audit:** every REST endpoint a desktop app can use, every setting, every output format and every channel event.
- **Built now:** three gaps, in the shared core, so QUILL and QUILL Lite get them together.
  - **Sign-in `state`.** Sign-in sends a random `state` and refuses a redirect that does not bring it back.
  - **Preview chunk replay.** The channel join asks for the preview chunks already streamed (`replay_chunks`), and the chunk `index` stops a chunk being shown twice. Before this change, a preview joined after the upload, or rejoined after a dropped connection, lost the chunks streamed in between.
  - **Rename limits.** Rename refuses a blank title, or one over 255 characters, before sending anything. In the Documents window, a name that is too long is asked for again, with what was typed still there.
  - **A failed sign-in is said when the person comes back.** The sign-in window already waited for the person to come back from the browser before saying a successful sign-in. It now does the same for a failed one, `state` refusals included (`quill/ui/scribe_signin_dialog.py`, `_say_when_seen`).
- **Needed, waiting on #2038.** Two fields: `suggest_buying_pages` on the documents list, and `subscription` on billing. Both belong in the windows and the Scribe Status dialog that #2038 rewrites. They are listed here so that #2038, or a PR after it, picks them up.
- **Not needed.** Push devices, push notification settings, App Store products and transactions, the account-deletion link, and the phone number. All of these serve Apple devices or are website-only actions. The reasons are in the table.

## REST endpoints

| Endpoint | What it does | QUILL | Do people need it from QUILL? |
|---|---|---|---|
| `POST /api/documents` (file or `document[url]`, `document[password]`, `document[settings][...]`) | Upload a document or a link; starts the free `html_stream` preview | Used: `client.py:262` (`create_document`) | (used) |
| `GET /api/documents` (`documents`, `pages_remaining`) | Every document with its outputs | Used: `client.py:275` | (used) |
| `GET /api/documents` field `suggest_buying_pages` | The server's hint to offer a purchase | Not used | **Yes, waiting on #2038.** It is the server's own signal for when to offer "Buy pages". It goes beside the pages count that #2038's Scribe Status dialog and the renamed "Documents in My Scribe Account" window show. |
| `GET /api/documents/trash` (`trashed_at`, `permanently_delete_at`) | Documents in the trash | Used: `client.py:281`; dates shown in `scribe_documents_dialog.py:175` | (used) |
| `POST /api/documents/{id}/trash` | Move to the trash | Used: `client.py:285` | (used) |
| `POST /api/documents/{id}/recover` | Recover from the trash | Used: `client.py:288` | (used) |
| `DELETE /api/documents/{id}` | Delete for good (from the trash) | Used: `client.py:292` | (used) |
| `PATCH /api/documents/{id}` `{"document": {"title"}}` | Rename; a blank title or one over 255 characters is refused | Used: `client.py:294`. **Built now:** both limits are checked before sending | (used) |
| `POST /api/documents/{id}/feedback` `{"comment"}` | Send for human review (paid remediation) | Used: `client.py:313`; Conversions and Documents windows | (used) |
| `GET /api/documents/{id}/outputs` (`outputs`, `is_password_needed`) | A document's outputs | Used: `client.py:317`; the runner's fallback poll | (used) |
| Output fields `format`, `stage`, `progress`, `estimated_time_remaining`, `is_preview`, `downloadable` | Each output's state | Used: `model.py:341`; time remaining goes to the job's `eta_seconds` (`runner.py:414`) | (used) |
| Document fields `id`, `title`, `page_count`, `inserted_at`, `is_password_needed` | Each document | Used: `model.py:375`; pages shown in `scribe_documents_dialog.py:179` | (used) |
| `GET /api/documents/{id}/outputs/{format}/download` | Download, through a redirect to storage, resumable with `Range` | Used: `client.py:427`; the token is never sent to storage; `Range` at `client.py:455` | (used) |
| `GET /api/documents/{id}/settings` | A document's settings | Used: `client.py:326`; reuse from My Scribe Documents | (used) |
| `PATCH /api/documents/{id}/settings` | Change settings for formats not made yet | Used: `client.py:335`; `runner.py:334` | (used) |
| `GET /api/document_settings` | The account's default settings | Used: `client.py:342`; the convert dialog's starting values | (used) |
| `PATCH /api/document_settings` | Change the account's defaults | Used: `client.py:350`; only when the person asks (`runner.py:336`) | (used) |
| `GET /api/settings/languages` | Language list | Used: `client.py:353` | (used) |
| `GET /api/settings/dialects` | Dialects per language | Used: `client.py:356` | (used) |
| `GET /api/settings/voices` (`[name, short_name, has_sample]`) | Voices per dialect | Used: `client.py:360`; #2036 shows every voice | (used) |
| `GET /api/settings/braille_tables` | Braille tables | Used: `client.py:364` | (used) |
| `GET /sounds/tts-samples/{short_name}.mp3` (no token) | A voice's sample | Used: `client.py:366`; Play Sample in voice settings | (used) |
| `GET /api/account_info` (`first_name`, `last_name`, `email`, `organization_name`) | Who is signed in | Used: `client.py:387` | (used) |
| `GET /api/account_info` field `phone_number` | The account's phone number | Not used | **No.** QUILL never shows or needs it, and keeping it out keeps personal data out of memory and logs. |
| `GET /api/billing` field `pages_remaining` | Pages left | Used: `client.py:388` | (used) |
| `GET /api/billing` field `subscription` (`store`, `renews_at`) | The active subscription, if any | Not used | **Yes, waiting on #2038.** "Subscription renews on 3 March 2027" belongs in #2038's Scribe Status dialog, beside the pages count. Account usage is #2038's, so it is not built here. |
| `GET /api/billing` field `app_account_token` | Apple's App Store account token | Not used | **No.** It is for Apple's StoreKit only. |
| `/auth/browser_from_oauth?token=&state={"return_to"}` | Opens a page of the website, already signed in | Used: `client.py:399`; Open My Scribe Account in Browser and Buy Pages | (used) |
| Account deletion page (`/settings/delete_account`, the crate's `delete_account_url`) | The website's account-deletion page, signed in | Not used | **No.** Apple requires in-app account deletion; Windows does not. Deleting the account is a website action, already one step away through Open My Scribe Account in Browser. A delete-account command in a document editor invites an irreversible mistake. |
| `POST /api/devices`, `DELETE /api/devices/{token}` | Register an Apple push (APNs) device token | Not used | **No.** APNs is Apple's push service. Windows has no APNs token, and QUILL says when a conversion finishes on its own. |
| `GET` and `PATCH /api/notification_settings` (`push_notify_when_complete`) | Push notifications for that device | Not used | **No.** This is the same Apple push channel. Scribe's email notice is the `notify_when_complete` setting, which QUILL uses. |
| `GET /api/app_store/products`, `POST /api/app_store/transactions` | Buying pages through Apple's App Store | Not used | **No.** QUILL never takes payment (PRD 3.6). Buying is on Scribe's website, through Buy Pages. |

## Settings (per document, upload and account defaults)

Every field is in `ScribeSettings` (`model.py:215`). It is sent at upload by `to_upload_fields` (`model.py:265`), and later by `to_update` (`model.py:237`). These are the fields:

`language`, `dialects`, `voices`, `tts_gender`, `tts_rate`, `braille_translation_table`, `braille_cells_per_line`, `braille_split_into_pages`, `braille_lines_per_page`, `large_print`, `add_image_descriptions`, `math`, `notify_when_complete`.

All 13 are used. The crate has no setting that QUILL lacks.

## Output formats

QUILL uses all ten: `html`, `html_stream`, `offline_html`, `pdf`, `docx`, `epub`, `mobi`, `daisy`, `mp3` and `brf` (`model.py`, `FORMATS`). The crate has no format that QUILL lacks.

## Sign-in (OAuth with PKCE)

| Piece | QUILL | Do people need it? |
|---|---|---|
| `/auth/logout?next=/oauth/authorize?...` with PKCE S256 | Used: `auth.py:99` | (used) |
| `state` on the authorize request, checked on the redirect (crate, 23 November 2026) | **Built now:** `auth.py:67` (`new_state`), `auth.py:94`, and the check in the listener (`auth.py:131`) | **Yes.** PKCE stops a stolen code being used. It does not stop someone else's code being slipped into QUILL, so a person could end up signed in to an account that is not theirs. A redirect without the right `state` is now refused before its code is exchanged. The person sees the existing sentence: "Scribe for Documents did not sign you in. Try again." |
| `locale` on sign-in | Used: `auth.py:98` | (used) |
| `POST /oauth/token` (code exchange and refresh) | Used: `auth.py:251`, `auth.py:303` | (used) |
| `POST /oauth/revoke` on sign-out | Used: `auth.py:346` | (used) |

## Document channel (Phoenix WebSocket)

| Piece | QUILL | Do people need it? |
|---|---|---|
| `/socket/websocket?vsn=2.0.0&token=&locale=`, topic `documents:{id}` | Used: `channel.py:90` | (used) |
| `phx_join` payload `{"replay_chunks": true}` | **Built now:** `channel.py:231` | **Yes.** Without it, the preview loses the chunks streamed before QUILL joined (the gap between the upload and the join), and every chunk streamed while the connection was down. A person reading the preview as it arrives misses text without knowing it. |
| Push `chunk` with `index` | **Built now:** `ChannelEvent.index` and `ChunkLedger` in `channel.py` | **Yes.** A replay sends again the chunks already shown. The index lets QUILL drop those, so nothing is read twice. Chunks from a server without `index` pass through unchanged. The ledger forgets a document when its preview completes, so a later preview of the same document, whose indexes start at 0 again, is passed on whole. |
| Heartbeat every 30 seconds | Used: `channel.py:256` | (used) |
| `start_conversion` `{format, password}` | Used: `channel.py:324` | (used) |
| Pushes `status`, `conversion_complete`, `error`, `password_required` | Used: `channel.py:parse_event`; the runner says each one (SCR-POL-4) | (used) |
| Channel errors `not_found`, `forbidden`, `conversion_in_progress`, `rate_limited`, `password_required`, `needs_purchase` (with `purchase_url`), `invalid_password` | Used: `errors.py:error_from_server` | (used) |
| A refused handshake is retried once with a fresh token | Used: `channel.py:default_channel_opener` | (used) |

## Rate limits, webhooks and email

- **Rate limit.** 10 actions a minute, with no Retry-After header. Used: the family queue keeps under 8 a minute and waits 60 seconds after `rate_limited` (PRD 3.5).
- **Webhooks.** None exist. The channel, plus polling `GET .../outputs`, is the whole story (PRD 3.5).
- **Email.** The `notify_when_complete` setting is used. Push is Apple-only (see above).
- **Retention.** The API cannot read it (PRD 3.4). QUILL describes the rule and links to the setting.

## What needs a live check with Jeff's account

1. **Sign in once.** Signing in should complete as before. If Scribe's server did not send `state` back, sign-in would now fail with "Scribe for Documents did not sign you in. Try again." Pneuma's own client relies on the server sending it back, so it should work, but this has not been tried against production.
2. **Watch a preview live, then drop the connection.** Convert a several-page PDF with the preview open, and turn Wi-Fi off and on during the preview. The preview should start at the document's first heading, and nothing should be missing or repeated after the reconnect. With the preview tab focused, check with NVDA, JAWS and Narrator that a burst of 20 or more replayed blocks is not spoken and does not move the caret.
3. **Refuse a sign-in while in the browser.** Start a sign-in and close Scribe's page without signing in. On coming back to QUILL, the sign-in window should say "Scribe for Documents did not sign you in. Try again." once, with focus on Try Again.
