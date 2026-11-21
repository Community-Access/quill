# Scribe for Documents in the QUILL family

Product requirements, draft for Jeff's review. 2026-11-20. Phase 1 is being built on branch feat/scribe-documents; the CHANGELOG entry of 2026-11-20 says what is built.

This replaces the June draft in `docs/planning/scribe.md`. That draft was written before the API existed and covered only three endpoints. The API that opened today does much more, and this PRD asks for all of it.

## 1. Summary

Pneuma Solutions' Scribe for Documents turns PDFs (password-protected ones too), images, Office files, OpenDocument, RTF, ebooks and plain text into accessible tagged PDF, Word, EPUB, MOBI, HTML, DAISY, MP3 audio and braille (BRF). Since 2026-11-20 any app can use it through a public API, free for the developer. Each person pays Scribe for their own page credits or subscription.

QUILL already converts a great deal on the person's own computer: Pandoc, MarkItDown, Tesseract and Windows OCR, liblouis braille, and local speech. What QUILL cannot do well is the hard case: a scanned or badly made document whose structure has to be rebuilt, with headings, reading order, tables and described images. Scribe fixes exactly that, and it also produces formats QUILL cannot make at all: tagged PDF, MOBI, and DAISY with audio.

The goal is that wherever someone in the QUILL family meets an inaccessible document, Scribe is one clear, consented step away. The result then lands in the tool where they will use it: the editor, the media player, the braille view, or a folder of their choosing. It should speak every step on the way and end by saying what it made and where.

## 2. Where things stand

- **Registration.** Jeff registered QUILL on the developer portal (scribeit.io/developer) on 2026-11-20, for Windows and macOS. Pneuma approved it on 2026-11-21 and issued the client ID, which ships in `quill.core.scribe.CLIENT_ID`.
  - It is a public client using OAuth 2.0 with PKCE, so there is no client secret. The client ID may ship in the source.
  - Registered redirect URIs:
    - `http://127.0.0.1/scribe/callback`
    - `http://[::1]/scribe/callback`
  - Any port is allowed on loopback. QUILL listens on whatever port is free.
- **Exception approved (Mike Calvo, 2026-11-21).** Several files the person chose may be sent strictly one after another: wait for `conversion_complete` or an error before the next upload, back off on `rate_limited`, and pass every status to the person (7.4).
- **Pneuma's answers (2026-11-21).** Mike Calvo answered every question in `email.md`, checked by Matt Campbell against the server code. The answers are folded into this document and summarised in section 16.
- **Nothing is built yet.** The nearest working precedents are Datalab cloud OCR (`quill/core/datalab_ocr.py`, PRD 5.93) for consented cloud conversion, and the Auphonic connection in Converter for an upload, wait, download job with history.

## 3. What Scribe provides (all of it, from the API client source)

There is no published HTTP reference. What follows is read from Pneuma's open-source client library (`github.com/PneumaSolutions/scribe-api-client`, v0.3.1, Apache-2.0 or MIT; the Rust crate is the reference), the user manual (manual.scribeit.io), the announcement, and Pneuma's answers of 2026-11-21. Where the manual disagrees with those answers, the answers win: the manual's FAQ lists are out of date.

### 3.1 Inputs

- **The API accepts 23 types (Pneuma, 2026-11-21):**
  - PDF (password-protected included);
  - images: JPEG, GIF, PNG, TIFF, BMP, DCX, PCX, JPEG 2000, DjVu;
  - text: DOC, DOCX, RTF, ODT, TXT;
  - spreadsheets: XLS, XLSX, ODS;
  - presentations: PPT, PPTX, ODP;
  - ebooks: EPUB, MOBI.
- **HTML is not accepted,** neither as a file nor as a URL that returns a web page; the server answers `not_a_document`. QUILL offers Scribe only for the 23 types and says so before sending anything else ("Scribe for Documents does not take web pages. Save it as Word or PDF first.").
- **A file or a link.** Input is an uploaded file, or a URL that points straight at one of those files. Links behind a sign-in are not supported.
- **Size.** 500 MB per upload. QUILL checks the size before sending and refuses larger files with a sentence naming the limit.
- **Pages.** No page cap; the person's page credits are the limit. When credits are short, the upload still gives a free 2-page preview, and other formats return `needs_purchase`.

### 3.2 Outputs (API format identifiers)

| Identifier | What the person gets |
|---|---|
| `html` | Accessible HTML |
| `html_stream` | HTML streamed in chunks while converting; a preview that is free even with no credits |
| `offline_html` | A downloadable web page |
| `pdf` | Tagged PDF (large print available) |
| `docx` | Word (large print available) |
| `epub` | EPUB |
| `mobi` | MOBI (Kindle) |
| `daisy` | DAISY 3 (Z39.86-2005) text and audio, as a zip |
| `mp3` | MP3 audio |
| `brf` | Braille ready file |

Most formats are made from the `html` output, and `daisy` is assembled from `mp3`.

### 3.3 Settings

Settings can be set per document, or as the account's defaults. **QUILL uses per-document settings and leaves the account defaults alone** unless the person explicitly asks to change their defaults (Pneuma, 2026-11-21). The rules:

- **Read the person's defaults first.** `GET /api/document_settings`, then send the full set with the upload as `document[settings][field]` form fields. A field left out at upload gets Scribe's built-in default, not the person's.
- **HTML-shaping settings go in at upload.** Language, image descriptions, math and large print shape the HTML, and the HTML conversion starts as soon as the upload lands. They cannot be changed afterwards for that document.
- **Later changes** use `PATCH /api/documents/{id}/settings`, and apply only to formats not made yet: a format already made is not remade. When reusing a document from My Scribe Documents (7.5), the dialog says which settings are fixed by the earlier upload, and that formats already made keep their settings.
- **The server does not validate ranges yet.** QUILL offers only the website's values (below).

| Setting | What it does | How QUILL fills the choices |
|---|---|---|
| `language` | Document language; empty means detect it | List from `/api/settings/languages` (140+) |
| `dialects` | Dialect for each language | List from `/api/settings/dialects` |
| `voices` | Voice for each dialect | List from `/api/settings/voices`; each can have a sample MP3 |
| `tts_gender` | Male, female or neutral, used when the language is detected | Fixed choices |
| `tts_rate` | Speech speed | 0.5, 0.75, 1, 1.5, 2, 3 and 4. 3 and 4 are labelled "(may not be faster than 2)" until Pneuma confirms they are |
| `braille_translation_table` | Grade 1, Grade 2, UEB, computer braille, other languages (30+) | List from `/api/settings/braille_tables` |
| `braille_cells_per_line` | Line length (default 40) | Spin control, 20 to 42 |
| `braille_split_into_pages` | Split into pages | Check box |
| `braille_lines_per_page` | Lines per page | Spin control, 20 to 30 |
| `large_print` | Large print PDF and Word | Check box |
| `add_image_descriptions` | Describe the pictures | Check box |
| `math` | Mathematics as MathML (beta) | Check box |
| `notify_when_complete` | Scribe's own notification | Check box |

### 3.4 Account and documents

The API also covers the person's account and their documents:

- **Account:** who is signed in (name, email, organization), and pages remaining. `GET /api/account_info` returns `organization_name` (null for an individual). For an organization member, `pages_remaining` is the organization's shared pool, and QUILL says so beside the count: "1,240 pages left, using credits from <organization>."
- **Buying:** a purchase link whenever more pages are needed.
- **Documents:** the list of the person's documents with their outputs; rename; trash, recover and permanent delete. The trash deletes after 7 days or the account's retention setting.
- **Retention.** API uploads follow the account's retention setting, the same as the website: 30 days by default, 1 to 30 days by choice, indefinite with an active subscription; organizations must choose 1 to 30 days. The API cannot read or set it today, so QUILL describes the rule and links to the setting (Open My Scribe Account in Browser). The manual's 72-hour figure is out of date.
- **Human review:** "send for human review" with a comment, which is Scribe's paid remediation.
- **Downloads:** downloads support resuming (HTTP Range), and the file name comes from the server.

### 3.5 How a conversion runs

1. **Create.** `POST /api/documents` with a file or a URL (and a password if the PDF needs one). The free `html_stream` preview starts automatically.
2. **Join the channel.** QUILL joins the document's channel: a Phoenix WebSocket at `wss://scribeit.io/socket/websocket`, topic `documents:{id}`, with a heartbeat every 30 seconds.
3. **Start a format.** QUILL sends `start_conversion` with the format. Only one conversion per document runs at a time. If a format is already done, the server says so instead of converting again. Channel details confirmed by Pneuma: socket `/socket/websocket`, `vsn=2.0.0`, topic `documents:<id>`; server pushes are `status`, `chunk`, `conversion_complete`, `error` and `password_required`.
4. **Follow the events.**
   - `status` reports the stage (`queue`, `start`, `convert`, `add_image_descriptions`, `complete`) and the progress.
   - `chunk` delivers the streaming HTML.
   - `conversion_complete` says a format is done.
   - `error` reports a failure, for example `invalid_password`, `needs_purchase` (with a purchase link), `rate_limited` or `conversion_in_progress`.
   - `password_required` arrives when the PDF is locked.
5. **Download.** `GET .../outputs/{format}/download`.

If the connection drops, the conversion carries on. QUILL reconnects and joins again; it never uploads again. There are no webhooks. Polling `GET .../outputs` is the fallback.

**Rate limit (Pneuma, 2026-11-21).** 10 actions per minute per person, in fixed 60-second windows. Uploads, `start_conversion` and password tries share one counter, and the person's own use of the website counts against it too. There is no Retry-After header. QUILL keeps itself to 8 actions a minute across the whole family (the shared queue counts them), and after `rate_limited` waits 60 seconds before the next action.

### 3.6 What the person pays

- **New accounts:** 100 free pages, for 30 days.
- **Packs:** page packs from $10 (200 pages minimum). They never expire.
- **Subscription:** $99 a year for 10,000 pages.
- **Human remediation:** extra.
- **Without credits:** a person still gets the first two pages as a preview.
- **Repeat formats are free.** Pages are charged once, at the first full conversion, which is normally the HTML the upload starts. A second format of the same document costs no pages (Pneuma, 2026-11-21).

QUILL never takes payment. It shows pages remaining and opens Scribe's purchase page.

## 4. Goals

1. **Every format.** Every output format and every setting the API offers is reachable from QUILL, from the keyboard, with speech and braille.
2. **Every inaccessible document.** Scribe is offered at every point where QUILL meets an inaccessible document: opening a scanned PDF, importing, a picture of text, and a document someone has been sent.
3. **The right tool.** The result goes where it is used: the editor, Media Player, the braille view, Studio, or a folder.
4. **Consent every time.** Nothing leaves the computer without the person's say, every time. Safe Mode and the AI-off choice are respected.
5. **One integration.** One sign-in, one queue and one set of choices for the whole family. An app adds only its own entry points.
6. **Pneuma's policy, in full** (section 5).

## 5. Pneuma's policy as requirements

| Policy | Requirement |
|---|---|
| Say features are powered by Scribe for Documents | **SCR-POL-1.** Every Scribe command, dialog title, progress window and result sentence names "Scribe for Documents". Menus read, for example, "Convert with Scribe for Documents...". The About box and the user guide say "Powered by Scribe for Documents". |
| Open Scribe's sign-in page unchanged, without intercepting what is typed | **SCR-POL-2.** Sign-in opens Scribe's page in the person's default browser. QUILL never embeds it and never reads what is typed. QUILL only receives the redirect on the loopback address. |
| Documents submitted interactively, one at a time | **SCR-POL-3.** Every upload follows a choice the person made. The family-wide queue (7.4) sends one document at a time. Under the exception Pneuma approved on 2026-11-21, several files the person chose go strictly one after another: the next upload waits for `conversion_complete` or an error, `rate_limited` backs off, and every status reaches the person. |
| Pass along every status update | **SCR-POL-4.** Every `status`, `error` and `conversion_complete` reaches the person as text in the progress window. Each change of stage is spoken once. Percentages are shown, and spoken only at milestones (GATE-13). |

## 6. Not doing

- **No credentials in QUILL.** QUILL never handles payment or a Scribe password.
- **No mixing with QUILL's AI choice.** Scribe is not routed through "Choose Your AI" or the AI gateway. It is a document service with its own consent. If the person has turned AI off, the image-description setting is off by default and the consent box says so (see 10.2).
- **No silent uploads.** Nothing is uploaded automatically without a standing, per-profile consent (watch folder, 8.1.6).
- **No resale.** No organization admin, reseller or human-remediation ordering beyond `feedback`.
- **macOS later.** macOS waits on the family's macOS release (backlog). Its client ID is already registered.

## 7. Shared foundation (built once, in `quill/core/scribe/` and `quill/ui/scribe_*`)

### 7.1 Our own client

- **Write it ourselves.** QUILL writes its own small Python client for the REST and channel protocol, using Pneuma's Rust crate as the reference.
- **Why not the official wheel.** The `scribe-client` wheel on PyPI is a compiled Rust module, so GATE-9 (no silent network) could not see its calls. It also lacks rename, feedback, account defaults, billing and account info. Pneuma agreed to our own client on 2026-11-21 (16).
- **Modules.** Each stays under the 600-line cap.
  - `client.py`: REST, with `verified_ssl_context` and errors as `CodedError`.
  - `channel.py`: the Phoenix channel, heartbeat, reconnect and join again.
  - `auth.py`: on `core/auth` PKCE and the loopback listener.
  - `model.py`: formats, stages and settings.
  - `queue.py`: section 7.4.
  - `library.py`: the local record of documents and downloads.
- **WebSocket library.** The channel uses `websockets`, already a QUILL dependency (`pyproject.toml`, used by OpenAI live dictation in `quill/core/windows_dictation/cloud/transport.py`). No new package is needed.
- **Network audit.** Every call has a GATE-9 entry with its reason.

### 7.2 Signing in

- **Where.** Options > Scribe for Documents > Sign In, and the first time any Scribe command runs.
- **How.** QUILL opens a loopback listener on a free port, then opens Scribe's authorize URL in the browser. It says "Your browser is open at Scribe for Documents. Sign in there, then come back to QUILL." Then it waits, with Cancel.
- **Tokens.** Tokens are stored with `SecretsManager` under namespace `scribe`, so one sign-in covers every app in the family. QUILL refreshes 5 minutes before expiry and once on a 401.
- **While waiting.** A small dialog shows that sentence, with a Copy Sign-in Link button (for when the browser does not open, or the person uses another browser) and Cancel. After a time limit it says "Sign-in timed out. Try again?"
- **Signed in.** The same dialog changes to "Signed in to Scribe for Documents as <name>. <n> pages left.", with focus on Continue. That is the one announcement.
  - If a Scribe command started the sign-in, Continue carries on into that command.
  - The browser tab the redirect lands on says "Signed in. You can close this tab and return to QUILL."
- **Sign Out.** Revokes the token and wipes the namespace.
  - With jobs waiting it asks first: "Two conversions are waiting. Signing out stops QUILL waiting for them; they still finish in your Scribe account."
- **Open My Scribe Account in Browser.** Uses `browser_from_oauth` so the browser is already signed in. It reaches settings, retention, purchases and account deletion.

### 7.3 Convert with Scribe for Documents (the one dialog)

One dialog, the same in every app, opened with the file (or files) already chosen. Its parts:

1. **What will be sent.** This is a read-only multi-line text field, the first control in the tab order, and focused when the dialog opens, so the person can read it again at any time. It holds:
   - The text: "Notes.pdf (2.1 MB, 34 pages) will be sent to Scribe for Documents (Pneuma Solutions) and converted in the United States. It stays in your Scribe account under your retention setting (30 days unless you changed it) until you delete it. Pictures may be described by AI. Pneuma does not use documents to train AI. Convert only documents you own, have permission for, or that are out of copyright."
   - Several files are listed with a count.
   - A caution line if a file name looks sensitive, as Datalab has.
   - The privacy lines from 10.1, on the first upload only.
   - When nothing is uploaded (reusing a document from 7.5), the text says instead: "No file is sent. Scribe makes these formats from Notes, already in your account."
2. **What you want back.** A check box for each format: Accessible HTML, Word, Tagged PDF, EPUB, Kindle (MOBI), DAISY (text and audio), MP3 audio, Braille (BRF), Web page for offline reading.
   - The default comes from the app (8.x) and the last choice.
   - Each format the person has already converted for this document says "already made". Another format of a document already in the account says "no pages used": pages are charged once per document.
3. **Settings,** grouped under "Language and voice", "Braille", "Print" and "Pictures and maths".
   - **Building the groups.** Each group is a labelled static box, so screen readers say its name on entering it. Every group is created when the dialog is built, in display order, directly after the format check boxes. A group is only shown or hidden to match the chosen formats, followed by Layout(), because wx tab order follows creation order.
   - **Hiding.** Hiding never removes the focused control, and hidden groups keep their values.
   - **Summary line.** After the formats, a read-only summary line ("Settings below: Language and voice, Braille") updates without being spoken.
   - **Choice lists.** Each group's choices come from the server lists, cached for the session.
     - While a list loads, the control says "Loading voices...". If loading fails, it says "Voices could not be loaded" with a Retry button. A combo box is never left empty.
     - Each label is created immediately before its control.
   - **Play Sample** beside the voice plays that voice's sample. While it plays, the button reads Stop Sample, and Escape stops the sample without closing the dialog. Otherwise Escape cancels.
   - **Starting values** are the person's Scribe account defaults, read from `GET /api/document_settings` when the dialog opens, then QUILL's last choice for this app where the person made one. The full set is sent with the upload (3.3).
   - **Account defaults check box:** "Also save as my Scribe account defaults (changes your Scribe website settings too)". Off by default and never remembered on, as Pneuma asked: account defaults change only when the person asks.
   - **Small screens.** If the dialog uses a scrolled panel, the panel scrolls to the focused control.
4. **Password.**
   - **When it is asked.** Only when the file needs one and the person has just pressed the button. If the server says `password_required` after the upload, the job waits in the progress window instead (7.8).
   - **The field.** A password field labelled "Password for Notes.pdf", never pre-filled, never saved or logged, with a "Show password" check box so braille and typing-echo users can check what they typed.
   - **A wrong password.** The text stays selected and QUILL says "Password not accepted. 2 tries left." After the third try: "Notes.pdf was not sent: password not accepted", with Retry on the job.
5. **Pages.** A read-only field reachable by Tab: "This uses about <x> of your <n> pages." It updates silently as formats are checked. Buy Pages opens the purchase page, and the count refreshes silently when the dialog is active again.
6. **Buttons.** Send and Convert (default; the name states what the person agrees to) and Cancel. When nothing is uploaded, the button reads Convert. There is no "don't ask again".

### 7.4 The family queue and progress

- **One queue for the whole family.**
  - It is per Windows user, across every running QUILL app.
  - A lock file and a queue file sit in the shared QUILL data folder. Writes are atomic.
  - Two apps never upload at the same moment.
- **One conversion at a time.**
  - Each document goes in as one job, and each format as one step within it, because the server runs one conversion per document.
  - Formats follow Scribe's dependency order: html, then the formats made from it, with mp3 before daisy.
- **Progress window (Scribe Conversions).**
  - Each app shows its own instance, read from the shared queue file.
  - It is a top-level modeless window with a title and its own key. Escape closes it and returns focus to where it was opened from, and it has an F1 topic.
  - It is reachable from every app: Window > Scribe Conversions, and Tools > Scribe for Documents > Conversions.
  - **The list.** A list in report view (wx.ListCtrl, not a tree or DataViewCtrl), one row per job, with the formats as a column. Enter opens the result, Delete removes the row from the list, and the Applications key or Shift+F10 opens every job command.
  - **Row text** changes only when the stage changes. Percent, estimated time and the full latest message sit in a read-only details field below the list. Each stage change is announced once even when the focused row is the job that changed: an in-place change to a list row is not re-read by NVDA, JAWS or Narrator (accessibility review of the built window, 2026-11-20).
  - It lists each job, its formats, its stage, its percent and its estimated time.
  - Focus stays where the person left it. Rows update in place (FUX-06).
  - Each stage change is spoken once, through the announcement service: "Scribe for Documents: Notes.pdf, adding image descriptions."
  - Errors are spoken with the server's own message, which Scribe already writes for people to read.
- **When a job finishes,** the result is said once (FUX-04): "Scribe for Documents made Notes.docx and Notes.brf in Documents\Scribe for Documents\Notes. Word is open in QUILL."
- **Commands for a job:** Cancel Waiting, Open Result, Open Folder, Retry, Ask for Human Review..., and Remove from List.
  - **Cancel.** A running conversion cannot be stopped on Scribe's side. Cancel stops QUILL waiting and downloading, and says so.
- **Closing an app.**
  - Closing an app does not lose a job.
  - The queue file remembers it, and the next app to start reconnects and downloads.
  - The app that downloads says it once, after its startup messages, combined into one sentence: "Scribe for Documents finished 2 documents while QUILL was closed: Notes and Chapter 2, in Documents\Scribe for Documents."
- **Cancel Waiting** says what it means: "QUILL stopped waiting for Notes.pdf. Scribe will still finish it and may use pages; it stays in My Scribe Documents."
- **Several files (exception approved 2026-11-21).**
  - When the person chooses several files in one Convert dialog, they go one after another without asking again: the next upload starts only after the previous document's `conversion_complete` or error.
  - On `rate_limited`, the queue waits 60 seconds and says so once (QUILL-SCRIBE-BUSY). Every status of every file reaches the person.
  - A file that fails does not stop the rest; the final sentence names what was made and what was not.
  - A watch folder runs the same way, for the files that arrive in a profile where the person turned Scribe on.

### 7.4a Who speaks, and when

- **One announcer.** Only the app holding the queue lock speaks Scribe stages, errors and results. Other running apps show the same state silently. When the lock passes to another app, the speaking passes with it.
- **Background jobs never open a dialog.** A job that needs the person moves to a "Waiting for you" state and says so once, for example: "Notes.pdf needs its password. Open Scribe Conversions to enter it."
  - The action is a command on the job in the progress window: Enter Password..., Sign In..., Open Result.
  - A dialog may open only straight after the person's own command, such as pressing Send and Convert.
- **How much is spoken.**
  - "Speak each stage" defaults to "Only while a QUILL app is in front". Start, finish and errors are always spoken.
  - Percentages are spoken at 25, 50 and 75 percent of the whole job (not per format), and only when stage speech is on.
  - Intermediate stages may drop the "Scribe for Documents:" prefix ("Notes.pdf, adding image descriptions"). Start, result and error sentences always name Scribe for Documents (section 5).
- **Errors** carry their context: "Scribe for Documents could not convert Notes.pdf: <server message>". The text stays in the job's details field so it can be read again. The QUILL error code appears in Copy Details and is not spoken.
- **Scribe Status (keyed)** says the current job once without opening anything: "Notes.pdf: adding image descriptions, 40 percent, about 2 minutes."
- **Repeat Last Scribe Message (keyed)** says the last Scribe sentence again.
- **Opening results.**
  - A result opens on its own only in the app that started the job, and only if that app is in front and the person has not typed in the last few seconds.
  - Otherwise the result sentence ends: "Open it from Scribe Conversions."
  - The result sentence names the final file name, after any "(2)".

### 7.5 My Scribe Documents

- **Where.** File > My Scribe Documents in QUILL and Lite, and in the progress window.
- **What it is.** A modal dialog with a Refresh button. It is not a live list.
- **What it lists.** Every document in the person's Scribe account (including those made on the web or iPhone): title, pages, date, and formats ready.
  - A "Show: Documents / Trash" choice sits above the list.
  - When there is nothing to list, a focusable line says "No documents in your Scribe account."
- **Commands:**
  - Download formats (any, already made or new: the same dialog as 7.3, without the upload).
  - Open in QUILL.
  - Rename.
  - Move to Trash, with a separate Trash view offering Recover and Delete Forever. Delete Forever is confirmed, says it cannot be undone, and gives the server's deletion date.
  - Ask for Human Review.
  - Copy Details.
- **How the commands behave.**
  - **Rename** is a small dialog with the current name selected. There is no editing in the list itself, which is unreliable with JAWS.
  - **Delete Forever's** confirmation has Cancel as its default button.
  - **After Move to Trash, Recover or Delete,** focus moves to the next row (or the previous one if it was the last), and QUILL says once, for example "Notes moved to Trash." The person caused this change, so it is said, unlike the rows FUX-06 covers.
- **Pages left.** It shows pages left and the Buy Pages button.

### 7.6 Where downloads go

- **Default folder:** `Documents\Scribe for Documents\<document title>\`.
  - It can be changed in Options.
  - The server's file name is used and made safe.
  - An existing file is never overwritten: QUILL adds "(2)".
- **Resuming.** Downloads resume with Range after a drop.
- **Local record.** `library.py` keeps which document ID made which file, so My Scribe Documents can say "downloaded to ..." and Beacon can find it.

### 7.7 Options > Scribe for Documents

This page is shared and mirrored in each app's options. Its controls:

- **Sign in / out:** shows who is signed in and pages left.
- **Default formats** and default settings: local defaults, kept separately from Scribe's account defaults.
- **Download folder.**
- **Open each result when it is ready:** Yes / Offer / No. "Offer" adds Open Result to the job and to the result sentence, never as a dialog (7.4a).
- **Offer Scribe when a PDF has little or no text:** on by default.
- **Watch folders** can use Scribe only in profiles where you have turned it on.
- **Speak each stage:** "Only while a QUILL app is in front" by default, with Always and Never. Percentages as in 7.4a.
- **Powered by Scribe for Documents:** the policy text, privacy notes (10), and links to Scribe's terms, privacy policy and manual.

Every field is in the settings vocabulary gate and the settings documentation gate. Tokens never go in settings.

## 8. Per app

### 8.1 QUILL

1. **File > Import / Convert Document (OCR).**
   - Scribe becomes a tier after the free ones: QUILL's own reader, MarkItDown, Tesseract and Windows OCR.
   - It is offered when the free tiers produced little or nothing, or when the person chooses it outright with "Convert with Scribe for Documents...".
   - The result (Word by default, opened as rich text) opens in a new tab, unsaved, named "<stem> (Scribe)".
   - `ConversionOutcome` gains `TIER_SCRIBE`, and `import_convert.opened_sentence` gets its sentence.
2. **Opening a PDF with little or no text** (`text_layer_looks_empty`).
   - The existing OCR offer adds "Convert with Scribe for Documents (rebuilds headings, tables and picture descriptions; uses about <n> pages of your Scribe credit)".
3. **Read while it converts.**
   - With the HTML format chosen, QUILL can open a read-only tab that fills from `html_stream` chunks as they arrive.
   - **Adding text.** Only complete blocks are added (whole paragraphs, headings and list items), never raw chunks, so a half-built line never changes under the caret or the braille line. New text is added at the end without moving the caret, and is never announced (FUX-06).
   - **The tab's name** says whether more is coming: "<stem> (Scribe, converting)", then "(Scribe, complete)" or "(Scribe, incomplete)". Scribe Status works inside it.
   - **When it is finished.** File > Replace with Finished Document (keyed) swaps in the finished document and keeps the reading position at the same block. Its completion is part of the one result sentence (7.4a), not a second message.
   - **If it fails partway,** the partial text stays, the tab is renamed "(Scribe, incomplete)", and one message is said.
4. **File > Export > With Scribe for Documents...**
   - Sends the current document (saved first as DOCX, the richest input QUILL writes and one Scribe certainly takes) for any output format.
   - This is how QUILL gains tagged PDF, MOBI, DAISY with audio, and large print, none of which it makes itself.
   - QUILL's own export of EPUB, Word, BRF and text-only DAISY stays. This is added, not a replacement, and the menu says which is which.
5. **Braille.**
   - The Braille menu gets "Translate with Scribe for Documents..." (BRF with Scribe's table and page settings).
   - The result opens in QUILL's braille view through `brf_document.py`, where the proofing and validation tools work on it as on any BRF.
6. **Watch folder.**
   - A new action, "Convert with Scribe for Documents", with `requires_consent` per profile, like `CloudTranscribeAction`.
   - The profile names the formats and settings.
   - It goes through the family queue, strictly one at a time, under the approved exception (7.4). Only the 23 types Scribe takes are sent; other files are left for the profile's other actions.
   - The watch folder's results are said as every other watch result is.
7. **After conversion, chained actions.** Each one is a separate, chosen command, never automatic:
   - Read Aloud, using QUILL's voices.
   - Summarize and the other AI commands, through the person's chosen AI (Choose Your AI), with that route's own consent.
   - Send to Media Player (the MP3 or DAISY).
   - Save a Beacon place (8.7).
8. **Menus.** Tools > Scribe for Documents holds:
   - Convert a File...
   - Convert This Document...
   - Convert from a Link...
   - My Scribe Documents
   - Conversions
   - Sign In / Sign Out
   - Open My Scribe Account in Browser
   - Options
   - About Scribe for Documents

   Keys are deliberately few, with written reasons for those left without, as `file.import_convert` has.

### 8.2 QUILL Lite

Under family rule 10, Lite gets nothing QUILL does not have. Every Lite command below uses the shared code, and QUILL gets it in the same change.

- **Feature area.**
  - A new area, "Scribe for Documents", is off by default in the Lite profiles that keep things simple, and offered on first need.
  - It has its own versioned agreement, like Lite's hosted AI, because Lite promises nothing leaves the computer unless the person turns it on.
- **File > Import / Convert Document (OCR).**
  - Gains the Scribe tier.
  - Results open in a new window, as Lite does now.
  - The default format is Word, opened as rich text, or HTML if the person prefers.
- **File > Convert with Scribe for Documents...**
- **File > My Scribe Documents.**
- **File > Export > With Scribe for Documents...**
  - Lite then reaches every Scribe format, although its own export is HTML only.
- **The progress window** is the shared one.
- **Not in Lite:** watch folder, streaming read, chained AI.
- **Coverage gate.** Each new `cmd_*` gets a behavioural test (GATE-LITE-COVER) and a row in `parity.py`.

### 8.3 Quill Media Player

- **Opens Scribe's MP3 and DAISY** with chapters from the DAISY navigation, plus resume and bookmarks.
  - Scribe writes DAISY 3 (Z39.86-2005), text and audio, as a zip. The player already opens DAISY 3 from its `.ncx`, with multi-level heading chapters (`quill/apps/player.py`, `_on_open_daisy`), so no NCC reader is needed. QUILL unpacks the zip next to it and opens the `.ncx` straight away, without a file picker.
- **File > Listen to a Document with Scribe for Documents...**
  - Picks a document, converts it to MP3 or DAISY with the person's chosen voice and speed, and plays it when ready.
  - Uses the shared dialog with the audio formats checked.

### 8.4 Quill Converter

- Converter is audio and video today. It gains a **Documents** source type that uses Scribe as its engine.
  - The queue window shows document jobs beside audio jobs.
  - Effect recipes do not apply.
  - The output folder rules are Converter's own.
- **The batch exception covers this** (approved 2026-11-21): the document queue runs strictly one file after another (7.4).
- **Audio formats** (MP3 or DAISY's audio) can go on through Converter's normal audio steps, such as loudness or another format, as a second, chosen step.

### 8.5 QUILL Studio

- **File > Import > Narration from Scribe for Documents...** converts a document to MP3 and opens it as a Studio project, with chapter markers from the document's headings where the DAISY navigation gives them.
- The person can then edit, run the loudness check, and export M4B.

### 8.6 QUILL Cast

- **Episode attachments.** When an episode's show notes link a PDF or document, the episode menu offers "Convert Linked Document with Scribe for Documents...", using URL input (direct file links only). The result opens in QUILL or Lite, whichever is installed.

### 8.7 QuillBeacon

- **Places.**
  - A Beacon place can point into a Scribe result (a heading or passage in the HTML or Word) and remembers the Scribe document ID.
  - If the local file is gone, Beacon offers to download it again from My Scribe Documents.
- **Scribe Documents source.** Beacon's sources list gains "Scribe Documents", showing the person's Scribe library as places.

### 8.8 QUILL Social

- **Linked documents.** When a post links a PDF or document, the post menu offers "Convert Linked Document with Scribe for Documents...", as in Cast.

### 8.9 Apps that do not get Scribe, and why

- **Radio and Weather:** they do not handle documents.
- **Transcribe and Inkwell:** they type into other programs and do not open documents. If Pneuma later accepts audio input, Transcribe should be looked at again.
- **Radio for macOS and Weather for iOS:** out of this release.

### 8.10 Outside the apps

- **Explorer.** An optional "Convert with Scribe for Documents" item in Explorer's Send To menu. The family runtime installer adds a shortcut that starts QUILL (or Lite) with the file and opens the shared dialog. It is opt-in in the installer.

## 9. What happens to each output

| Format | Default action when ready | Also offered |
|---|---|---|
| HTML | Open in QUILL (rich) or Lite | Open in browser, Save |
| Offline web page | Save | Open in browser |
| Word | Open in QUILL or Lite as rich text | Open in Word, Save |
| Tagged PDF | Save | Open in the default PDF reader; open in QUILL (text) |
| EPUB | Save | Open in QUILL; open in the default ebook reader |
| MOBI | Save | Send to Kindle is not offered; QUILL says where the file is |
| DAISY | Open in Media Player | Save, Open folder |
| MP3 | Open in Media Player | Open in Studio, Save |
| BRF | Open in QUILL's braille view | Save, emboss, send to a display through the existing braille commands |

Each app's "Open each result when it is ready" choice decides whether the default action runs or is only offered.

## 10. Privacy, consent and safety

### 10.1 Consent and blocks

1. **Consent for every upload.** It is part of the convert dialog's wording, and has no "don't ask again". The only standing consent is a watch-folder profile's, given per profile, shown in the profile, and revocable.
2. **What the person is told before the first upload,** in Options and in the first consent:
   - Pneuma Solutions processes the document in the United States: on AWS in Ohio, with Microsoft Azure (East US) for speech and text recognition, Mathpix for maths, and Google Gemini through OpenRouter for picture descriptions.
   - Pneuma never uses documents to train AI.
   - The document is kept in their Scribe account under their retention setting: 30 days unless they changed it, 1 to 30 days by choice, as long as they like with a subscription; an organization sets 1 to 30 days.
   - Pictures can be described by AI. Pneuma is reviewing the picture-description provider and makes no promise yet about how long that provider keeps data; QUILL says exactly that, and nothing more, until Pneuma updates it.
   - Here is how to delete it: My Scribe Documents, Move to Trash, Delete Forever.
3. **Safe Mode** turns every Scribe command off with the family's usual message. So does running without network.
4. **AI turned off.** If the person has turned AI off in QUILL, "Describe the pictures" defaults to off, and the dialog says why. The person may still check it, because it is Scribe's processing, not QUILL's AI route.

### 10.2 Secrets and logging

5. **Logging.** Only state changes, document IDs and page counts are logged. Never document text, chunks, titles of files marked sensitive, tokens or passwords. Every log line goes through `redaction.py`. Tokens live only in the secrets vault.
6. **PDF passwords** are used for the one upload and are never stored.
7. **Outputs belong to the person.** QUILL saves them locally and the person may share them however they like. QUILL never caches or shares one person's outputs with another: the download folder and the queue are per Windows user, and nothing from Scribe goes into a shared or family-wide cache.

### 10.3 Copyright

8. **The manual's notice,** shown once, with the convert dialog: convert only documents you own, have permission for, or that are out of copyright.

## 11. Errors (GATE-EC codes)

| Server | QUILL code | What the person hears and can do |
|---|---|---|
| `unauthenticated`, `invalid_grant`, refresh failed mid-job | QUILL-SCRIBE-SIGNIN | "Your Scribe for Documents sign-in has ended. Conversions are paused until you sign in again." Sign In... is a command on the job; it is a dialog only when the person is acting. |
| `needs_purchase` | QUILL-SCRIBE-PAGES | The server's message, then Buy Pages (opens the purchase link) or Cancel, and how to get the free two-page preview: "You can still read the first two pages: Open Preview." |
| `password_required`, `invalid_password` | QUILL-SCRIBE-PASSWORD | In the dialog, up to three tries (7.3). After the upload, the job waits in the "Needs password" state (7.4a). |
| `conversion_in_progress` | (none) | Queued; QUILL waits for the current format. Never shown as an error. |
| `rate_limited` | QUILL-SCRIBE-BUSY | Said once per job: "Scribe for Documents asked <app> to slow down; trying again in a minute." QUILL waits 60 seconds (no Retry-After is sent); the countdown shows silently in the job. |
| `not_a_document` | QUILL-SCRIBE-NOTDOC | "Scribe for Documents cannot convert <name>: it takes PDF, pictures, Office, OpenDocument, text, EPUB and MOBI files, not web pages." Normally caught before upload. |
| File over 500 MB | QUILL-SCRIBE-TOOBIG | Before upload: "<name> is <size>. Scribe for Documents takes files up to 500 MB." Nothing is sent. |
| `not_found`, `forbidden` | QUILL-SCRIBE-GONE | The job stays, as "No longer in your Scribe account", until the person removes it. |
| Network drop | QUILL-SCRIBE-OFFLINE | Said once per outage, after it has lasted a few seconds; recovery is silent. During a conversion: "Reconnecting to Scribe for Documents; your conversion is still running there." During an upload: "Upload of Notes.pdf was interrupted; <app> will resume it." |
| Browser did not open, or the loopback port is blocked | QUILL-SCRIBE-SIGNIN-LOCAL | Copy Sign-in Link, and what to check. |
| Download failed, disk full, or folder not writable | QUILL-SCRIBE-SAVE | Names the folder, offers Choose Another Folder and Retry; the output stays on Scribe. |
| Safe Mode or no network when a command is chosen | QUILL-SCRIBE-OFF | The family's usual Safe Mode or offline message. Nothing is queued. |
| `server_error`, other | QUILL-SCRIBE-FAILED | "Scribe for Documents could not convert Notes.pdf: <server message>", plus Retry and Copy Details. |

All messages use the running app's own name (QUILL, QUILL Lite, Converter), never a fixed "QUILL".

## 12. Accessibility

- **Keyboard and names.** Every dialog follows the family's dialog contract: `_show_modal_dialog`, a Close button, accessible names, the first control focused, and an F1 topic for every control.
- **Announcements.**
  - Stage announcements go through the announcement service, once each, with no double speech with the screen reader (GATE-13 and GATE-BRAILLE).
  - Percentages are shown always and spoken only at 25, 50 and 75 percent.
- **Live lists** (progress window, My Scribe Documents) hold focus and position while rows change (FUX-06).
- **Results.** The result sentence names the file and folder and is said once (FUX-04).
- **The streaming tab** never moves the caret or speaks arriving text.
- **Voice samples** play through the app's audio output, stopped as 7.3 says.
- **Modeless windows.** Scribe Conversions follows a modeless-window contract: a title, Escape returns focus to where it was opened from, an F1 topic, and no focus stealing when it updates. The family's `_show_modal_dialog` contract covers only modal dialogs, so this contract is new.
- **Options page.** Account and pages are shown in read-only text fields that Tab reaches. Links to Scribe's terms, privacy policy and manual are buttons ("Open Scribe Terms in Browser"), as elsewhere in the family.
- **Testing with screen readers.** Every new surface is tested on NVDA, JAWS and Narrator. That includes braille flash messages for stage and result sentences, and the case where two apps are running and only one may speak.
- **Review.** The accessibility-lead reviewed this design on 2026-11-20 and its findings are in sections 7.2 to 7.5, 7.4a, 8.1, 11 and 12. It reviews every new dialog again before it merges.

## 13. Gates and tests

- **GATE-9:** every REST and WebSocket call has an entry.
- **GATE-11:** each module is under 600 lines. The UI is in mixins, not `main_frame.py`.
- **GATE-EC:** codes in section 11.
- **Menus:** GATE-DOCMENU and GATE-DOCKEY in QUILL, Lite, Player, Converter and Studio; the menu accelerators gate, with keyless reasons.
- **Settings:** the settings vocabulary and settings documentation gates.
- **Help:** GATE-HELPREF and GATE-CATALOGUE.
- **Lite:** GATE-LITE-COVER and parity rows.
- **Tests:**
  - **A fake Scribe server in tests:** REST plus a scripted Phoenix channel, replaying stages, chunks, errors, drops and `password_required`.
  - **Behavioural tests** for:
    - The queue: one at a time across two app processes, and survival over a restart.
    - Consent: no upload without it.
    - Safe Mode.
    - Redaction: a password never reaches a log.
    - Every error row.
    - Each per-app entry point.
- **A live test script** (people, on Jeff's Scribe account), with each format once from each entry point, added to the live testing list.

## 14. Documentation

- **QUILL-PRD:** a new numbered section (next to 5.93 Datalab).
- **QUILL Lite PRD** and the PRDs of Player, Converter, Studio, Cast, Beacon and Social: their parts.
- **User guide:** chapter 3 (opening, saving and converting), a new "Scribe for Documents" chapter, and F1 help topics.
- **Release notes, What's New and CHANGELOG,** in Jeff's plain style.
- **Retire `docs/planning/scribe.md`** with a pointer here.

## 15. Phases

1. **Foundation and QUILL.** Client, channel, sign-in, the convert dialog, the queue and progress, My Scribe Documents, options; QUILL's Import tier, low-text PDF offer, Export with Scribe, braille. The client ID arrived on 2026-11-21 and is in the build; tested against the fake server, live testing still to do.
2. **Lite and Media Player.** Lite's area and commands (with QUILL already having them); Player's Listen command and DAISY audio reading.
3. **Converter, Studio, Beacon, Cast, Social.** Their entry points; the watch-folder action; the streaming read tab; the Explorer Send To item.
4. **Batch.** The exception is approved (2026-11-21): several chosen files and the watch folder run one after another, from phase 1 on.

## 16. Pneuma's answers (2026-11-21)

Mike Calvo answered `email.md` on 2026-11-21; Matt Campbell checked the answers against the server code.

1. **Inputs:** 23 types, no HTML (3.1).
2. **Limits:** 500 MB per upload; no page cap beyond credits (3.1).
3. **Rate limit:** 10 actions a minute per person, fixed windows, shared with the website; QUILL stays under 8 and backs off 60 seconds (3.5).
4. **Ranges:** speeds 0.5 to 4 (3 and 4 unverified), 20 to 42 cells, 20 to 30 lines (3.3). The server will add its own checks.
5. **Retention:** the account's setting, not readable through the API (3.4).
6. **Processing:** United States; AWS Ohio, Azure East US, Mathpix, Gemini through OpenRouter; no training on documents (10.1). Pneuma will say more about the picture-description provider later.
7. **Terms:** the portal policy is all of it. Outputs belong to the person; never cached or shared across people (10.2).
8. **Account defaults:** per-document settings, read the defaults first, HTML-shaping settings at upload (3.3, 7.3).
9. **Own client:** fine. The Rust crate is the reference, the server stays backward compatible, and a changelog will start in `scribe-api-client` (7.1).
10. **Organizations:** nothing special; show "using credits from <organization>" (3.4).

Also settled: a second format costs no pages (3.6), and DAISY is DAISY 3 as a zip (8.3). The batch exception is approved (7.4).

Still open:

- **3x and 4x speech.** Whether they really come out faster than 2x. Labelled in the dialog until Pneuma confirms.
- **The picture-description provider's retention.** Pneuma will tell us when its review settles; the privacy text then changes.
- **Watch `scribe-api-client`'s changelog** for protocol changes.

## 17. Done means

- A person can sign in once and use Scribe from QUILL, Lite, Player, Converter, Studio, Cast, Beacon and Social.
- Every format and setting the API offers is reachable from the keyboard, with speech and braille.
- Nothing is uploaded without consent, and Safe Mode blocks it all.
- Every status reaches the person. Every job ends with one sentence naming what was made and where, and the result opens in the right tool.
- One document at a time across the whole family, and jobs survive closing the app.
- All gates green. The live script has passed once for every format and every entry point.
- Pneuma has approved the app and the batch exception (2026-11-21), and the branding is in every place in section 5.
