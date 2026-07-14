# QUILL Next Generation: Pocket, Sync, and the Platform

Vision document, 2026-07-04. Nothing here is committed work. It sketches the
three big moves after 0.9.0: an iOS companion app, a GitHub-style sync layer,
and where QUILL goes as a platform.

## 1. QUILL Pocket (iOS)

### Why the phone, and why now

For a large share of blind and low-vision users, the iPhone is the primary
computer. VoiceOver is arguably the most-used screen reader on earth, iOS
braille display support is first-class and built into the OS, and the phone is
always within reach. QUILL today lives where the serious writing happens - the
desktop - but the ideas, the mail, the meeting, the walk where the chapter
finally makes sense all happen away from the desk.

QUILL Pocket is not "QUILL, but small." The desktop is the writing desk; the
phone is the capture device, the reader, and the voice. That division of labor
is the whole design.

### The magical core: capture that lands where it belongs

The single feature that would feel like magic:

- Open Pocket (or invoke it from the Action Button / Shortcuts / share sheet).
- Talk. Whisper-quality transcription runs on-device or via the user's own
  AI key (same free-first rules as desktop QUILL).
- The note lands in the Vault inbox, already transcribed, already tagged with
  time and optional context ("captured during Tuesday standup"), and it is
  sitting in desktop QUILL the next time the user opens it.

No app-switching, no "which folder", no cleanup session later. Speak, done,
trust. For a writer who is blind, this collapses the distance between having
an idea and owning it in their manuscript.

Capture is more than voice:

- Camera OCR: point the phone at printed mail, a book page, a whiteboard, a
  package label. On-device recognition reads it aloud immediately and files
  the text into the Vault. This is Seeing AI-class utility, but the output
  goes somewhere durable instead of evaporating.
- Share sheet everywhere: any web page, email, or text selection on iOS can
  be sent to a QUILL notebook or a specific manuscript's research folder.
- Audio memos kept alongside their transcripts, so the original voice is
  never lost (mirrors the Listening Companion model on desktop).

### The reader: your books, your voice, your commute

- Read Aloud on the go: manuscripts, Vault notes, and imported documents
  with the same high-quality voices as desktop (Kokoro-class neural TTS),
  with per-document position sync. Stop reading chapter 12 on the couch,
  resume in the car.
- DAISY playback: QUILL already exports DAISY talking books; Pocket plays
  them natively with proper navigation by level, phrase, and page.
- Braille: full support for iOS-connected braille displays, so Pocket is
  usable eyes-free and ears-free. Reading in braille on the train, with the
  same document that opens on the desktop at home.

### Hey QUILL in your pocket

The Hey QUILL voice-interaction plan (desktop) extends naturally: "Hey QUILL,
what did I capture yesterday about the villain's backstory?" or "read me my
draft of chapter three" or "add a task to fix the timeline in act two."
Same allowlist-only safety law as desktop: voice can navigate, read, capture,
and annotate; it cannot destroy.

### Light editing, honest scope

Pocket gets a clean, VoiceOver-native editor for notes and small revisions -
not the full command surface. Trying to replicate 27k lines of desktop
main_frame on a phone would produce a bad phone app and a worse writing tool.
Fix a typo, reorder a scene list, answer a comment; save the ten-hour
drafting session for the desk.

### What makes it "meet people where they are"

- VoiceOver-first, not VoiceOver-compatible: rotor actions for every list,
  custom actions instead of buried buttons, headings and landmarks that make
  a screen navigable in three swipes, haptics as a secondary channel.
- Works offline; sync is opportunistic.
- Free tier is genuinely useful (capture + read + sync via BYO storage),
  consistent with the "free AI for everyone" ethos.

## 2. QUILL Sync: GitHub-like sync for your whole setup

### The model: your configuration is a repository

QUILL already stores everything as schema-validated, atomically-written JSON
(settings, keymaps, abbreviations, Quillin manifests) and Vault content as
files. That is exactly the shape git was built for. So the sync layer borrows
git's ideas rather than inventing a database:

- Versioned: every settings change is a commit with a human-readable message
  ("Changed default voice to Kokoro it_IT", auto-generated). History is
  browsable and speakable.
- Diffable: "what changed between my setup today and last Tuesday?" is a
  first-class, screen-reader-friendly question with a first-class answer.
- Rollback: one command restores any prior state of any synced scope. A bad
  keymap experiment is never a disaster again.
- Branch-like profiles: a "work" profile and a "home" profile share a common
  base with per-machine overlays (different audio devices, different braille
  displays, same abbreviations and AI setup).

### Transport: bring your own, or use ours

Three tiers, cheapest first, matching QUILL's $0-to-Jeff philosophy:

1. BYO git remote: point QUILL Sync at a private GitHub/GitLab/Gitea repo.
   QUILL manages the plumbing (the user never sees a merge conflict marker);
   the user pays nothing and owns everything. The existing SSH client work
   (paramiko, key management) is directly reusable here.
2. BYO folder: any synced folder (iCloud Drive, OneDrive, Dropbox, Syncthing)
   as the remote, using the same commit format on files. Zero accounts.
3. Hosted QUILL Sync (later, optional): a small service for people who do not
   want to think about any of the above. This is the only tier that costs
   money to run, so it ships last and never becomes required.

### Security is non-negotiable

- End-to-end encryption before anything leaves the machine. Sensitive
  settings are already DPAPI-protected locally; the sync payload is encrypted
  with a user passphrase-derived key, so a compromised remote leaks nothing.
- Secrets never sync in plaintext, and some (Windows credential-manager
  entries) never sync at all - the sync manifest explicitly marks scopes as
  syncable, encrypted-syncable, or local-only.
- Every outbound call goes through the existing network egress audit; sync is
  off until the user turns it on, per the consent-first rule.

### Sync scopes, smallest first

1. Preferences, keymap, abbreviations, voice/verbosity settings, Quillin
   install list (manifests re-fetched, not blobs). Small, low-conflict,
   immediately valuable - "sit down at any machine and it is your QUILL."
2. Vault content: notes, links, tags. Text merges are handled with a
   CRDT-or-three-way strategy tuned for prose, and conflicts surface as an
   accessible "two versions" review flow, never as inline markers.
3. Opt-in extras: AI conversation history, reading positions, Story Studio
   binder state.

Scope 1 alone justifies the feature; scopes 2-3 are what make Pocket sing.

## 3. The next generation: QUILL as a platform

Where this all points:

- One Companion, every surface. The desktop Companion agent, Hey QUILL
  voice, and Pocket are the same assistant with the same memory, reachable
  by keyboard, speech, or phone. Context follows the person, not the device.
- Accessible collaboration. Real-time co-editing in mainstream tools remains
  a screen-reader minefield. A QUILL-to-QUILL collaborative mode - built on
  the sync layer's merge machinery, with spoken presence cues ("Sarah is
  editing chapter two") and braille-aware change tracking - would be the
  first co-writing experience designed blind-first. This is the moonshot.
- Quillin exchange. Sync already carries the user's Quillin list; the next
  step is a browsable, curated directory so extensions travel between users,
  not just between one user's machines. Sandboxing and manifest validation
  are already in place.
- Publishing pipeline. Draft in QUILL, capture on Pocket, and publish out:
  DAISY, EPUB, WordPress, and podcast-style audio (QUILL Cast) from one
  manuscript. The read-side WordPress work is the seed.
- Local-first AI everywhere. The free-model catalog and local-engine work
  extend to Pocket via on-device models, so the whole loop - capture,
  transcribe, summarize, read back - can run with no cloud at all.

## Sequencing sketch

1. Sync scope 1 (settings-as-a-repo, BYO remote). Pure desktop work, builds
   on existing storage and SSH code, valuable on day one.
2. Vault sync (scope 2). Hard merge problems solved on desktop first, where
   debugging is easier.
3. Pocket v1: capture + read + Vault browse, riding the now-proven sync.
4. Pocket v2: camera OCR, DAISY playback, Hey QUILL voice.
5. Platform bets: collaboration, Quillin exchange, hosted sync - in whatever
   order real users pull hardest.
