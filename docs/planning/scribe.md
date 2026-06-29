# Scribe for Documents — QUILL Integration (Draft Spec)

- Status: Draft / Proposed
- Owner: TBD
- Created: 2026-06-29
- Partner: Pneuma Solutions (Matt Campbell, Mike) — **Scribe for Documents**
- Source: Matt Campbell email, 2026-06-29 (proposed REST API + OAuth)

> Purpose: a complete answer to Matt's questions and a concrete, accessible,
> QUILL-native integration design he and Mike can build against quickly. Scribe
> turns inaccessible documents (e.g. image-only PDFs) into accessible formats by
> streaming + converting them; this brings that power into QUILL without leaving
> the editor.

## 1. Matt's proposal (restated)

Three REST endpoints:

1. **Upload a new document** → returns a URL QUILL opens in the user's default
   browser to watch the document stream and request conversions.
2. **List documents** in the user's account → each entry has a Scribe web-UI URL
   (to request more conversions) and the output formats already converted.
3. **Download** an already-converted output format.

Auth: **OAuth** (Pneuma accounts have no passwords; web-UI auth, SSO-ready). Matt
asks whether QUILL already uses OAuth, and what features/UX we want.

## 2. Answers to Matt's questions

### 2.1 "Are you already using OAuth for any of the other services you support?"

**Yes.** QUILL already implements a complete OAuth **authorization-code** flow for
**Mastodon** (`quill/core/mastodon/client.py`): register the app, open the
provider's authorize URL in the user's browser (`webbrowser.open`), and exchange
the returned code for an access token (`POST /oauth/token`). Tokens and client
secrets are stored in the OS credential store, never in a plain file
(`quill/platform/windows/credential_store.py`: env var → DPAPI-encrypted file →
Windows Credential Manager; macOS keychain on Mac). Today that flow uses the
**out-of-band** redirect (`urn:ietf:wg:oauth:2.0:oob` — the site shows a code to
paste back), and we can also run a **loopback redirect** (`http://127.0.0.1:<port>`)
to skip the paste step.

**So OAuth is the right call and we're comfortable with it** — we agree it beats a
pasted API key for UX, and it gives you SSO/headless flexibility later. We'd reuse
our existing pattern; ideally with **PKCE** and a **loopback redirect** for a
no-copy/paste, fully keyboard-and-screen-reader-accessible sign-in.

What we need from you to wire it (see §6 open questions): authorization + token
endpoints, client registration (or a pre-registered QUILL client id), supported
redirect URIs (loopback? OOB?), scopes, PKCE support, and refresh-token behavior.

### 2.2 "Did you have specific ideas about features and how it should work?"

Yes — see §3 (UX), §4 (the three endpoints mapped to QUILL flows), and §5 (the
magical round-trips). In short: **Send to Scribe** from the editor, a **My Scribe
Documents** list that pulls converted outputs **back into QUILL** as editable
documents, and an **"open this inaccessible PDF with Scribe"** offer at the moment
the user hits a document QUILL can't read well. All optional, consent-gated, and
private-by-default (a document only leaves the machine on an explicit action).

## 3. Accessible UX (QUILL-native)

- **Surface:** a small set of actions, e.g. under **File → Convert with Scribe**
  (or the AI/Documents area), plus a context offer when opening a low-text PDF.
- **Sign in once:** "Connect Scribe…" runs the OAuth flow in the browser; on
  return, QUILL stores the token in the OS credential store and announces
  "Connected to Scribe as <account>." Connection state lives next to the other
  service connections.
- **Focus + progress, never la-la-land:** every network step shows an accessible,
  cancelable progress dialog with spoken milestones (reusing QUILL's
  `AIProgressDialog` pattern); focus returns to a sensible place (the new document,
  or the list) when done. No silent waits.
- **Consent:** before any upload, QUILL states plainly that the document will be
  sent to Scribe (Pneuma) for conversion, and asks once (remembered per choice).
  Disabled in **Safe Mode**; audited in the network-egress inventory (GATE-9).

## 4. The three endpoints → QUILL flows

### 4.1 Upload (endpoint 1) — "Send to Scribe"
From the current document/file (or a chosen file), QUILL uploads it, then **opens
the returned streaming URL** in the default browser so the user watches the stream
and picks conversions in Scribe's accessible web UI. QUILL records the returned
document id so it can later list/download results. Large uploads run on a worker
thread with cancelable progress.

### 4.2 List (endpoint 2) — "My Scribe Documents"
An accessible list (native list control) of the account's documents, each row
showing title/date, **already-converted formats**, and an **"Open in Scribe"** link
(the per-document web-UI URL) for requesting more. Selecting a converted format
offers **Download into QUILL** (§4.3).

### 4.3 Download (endpoint 3) — "Open the converted file in QUILL"
QUILL downloads a chosen converted output and **opens it as a new document**
(Markdown/HTML/RTF/DOCX/text all already supported by QUILL's readers), so the user
goes straight from "inaccessible source" to "editable, accessible text" without
leaving QUILL. Downloads are verified (size/type) and land in the user data dir or
a chosen path.

## 5. Magical possibilities (where this gets amazing)

- **Inaccessible-PDF rescue, in place:** when the user opens a PDF QUILL detects as
  image-only / low-text, QUILL offers **"Send to Scribe to make this readable"** —
  the exact moment the value is highest.
- **Round-trip editing:** inaccessible source → Scribe → accessible Markdown/DOCX →
  open + edit in QUILL → export. The conversion becomes a normal step in a writing
  workflow, not a detour.
- **Watch-folder auto-convert:** drop files in a watched folder; QUILL sends them to
  Scribe and opens the converted result when ready (mirrors the existing
  transcription watch-folder).
- **"Convert and read aloud"/"convert and summarize":** chain a Scribe conversion
  into QUILL's Read Aloud or AI summary in one action.
- **Pick-up where you left off:** the document list means a conversion requested on
  the web later is one click to pull into QUILL.

## 6. Open questions for Pneuma (to finalize the build)

1. **OAuth endpoints + client:** authorization URL, token URL, and either a way for
   QUILL to register a client or a pre-issued client id for "QUILL".
2. **Redirect URIs:** can you allow a **loopback** redirect (`http://127.0.0.1:<random port>`)
   for a no-paste flow? Is **OOB** (paste-the-code) also available as a fallback?
3. **PKCE:** supported? (We'd prefer PKCE for a public desktop client.)
4. **Scopes:** what scopes gate upload / list / download?
5. **Tokens:** access-token lifetime and **refresh-token** flow (so users don't
   re-auth constantly); revocation.
6. **Upload API:** content type / multipart vs presigned URL; max size; supported
   input formats; how the streaming URL and a stable **document id** are returned.
7. **List API:** shape of each entry (id, title, created, available formats, web-UI
   URL); pagination.
8. **Download API:** how a format is addressed (id + format), content type, and
   whether links are time-limited.
9. **Rate limits / errors:** limits and error shapes so QUILL can message them
   accessibly and back off.
10. **Account display:** is there a "who am I" call so QUILL can show the connected
    account name?

## 7. QUILL integration points (for our side)

- Auth/flow: reuse the OAuth pattern in `quill/core/mastodon/client.py` (generalize
  to a small `scribe` client); tokens via `platform/windows/credential_store.py`
  (DPAPI/Credential Manager; macOS keychain).
- Network: a new `quill/core/scribe/` client; **every** call added to the
  `network_egress_audit` inventory (GATE-9); **Safe Mode** disables it.
- Browser hand-off: `webbrowser.open` (already used).
- UI: stock accessible dialogs + `AIProgressDialog` (cancelable, spoken progress);
  the dialog contract (`_show_modal_dialog`). Open converted outputs through
  QUILL's existing document readers.
- Privacy: opt-in, consent-gated upload (a document leaves the machine only on an
  explicit action), connection state surfaced and revocable.

## 8. Phased plan

- **Phase 1 — Connect + Send + Open result.** OAuth connect, "Send to Scribe"
  (upload + open streaming URL), "My Scribe Documents" list, download-into-QUILL.
- **Phase 2 — In-context rescue.** Offer Scribe when opening an inaccessible PDF;
  "convert and read aloud / summarize" chaining.
- **Phase 3 — Automation.** Watch-folder auto-convert; remembered preferences.

## 9. Privacy & scope

Optional and off until connected; documents are uploaded only on an explicit,
consented action; disabled in Safe Mode; all egress audited. Windows-primary,
macOS-supported (the OAuth + credential patterns already work on both).
