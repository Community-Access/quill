# Section — Vault (`vault.*`, 22 commands)

QUILL's **Vault** is a **knowledge base**: you point it at a folder of Markdown
notes and QUILL indexes them so you can jump between notes, follow `[[wikilinks]]`,
list backlinks and tags, keep daily notes, insert templates, export the whole thing
as a website, and sync it over your own git remote. It is QUILL's answer to
Obsidian, built to be driven entirely by keyboard and read entirely by ear. Finish
**Part 0** first.

Surface reference (label + shortcut) is
`../../planning/signoff/SIGNOFF-editor.md` → `vault.*`. Read §2–§3 of `README.md` for
the scenario layout and the Pass/Fail/Blocked/N-A + Works/Surface-exact/Accessible
boxes.

> **Read this before you test — what the Vault is, and is *not*.**
> Despite the word "vault," this feature is **not an encrypted store for secrets**.
> There is **no passphrase, no lock/unlock, no idle-lock, and no encryption**. Notes
> are ordinary `.md` text files in a folder you choose; QUILL reads and writes them
> in plain text (that is the point — they must stay readable in any editor). So do
> **not** put real passwords or secrets in a vault, and do **not** expect QUILL to
> ask for a passphrase or to hide note content — if it did, that would be a
> different feature. The one place credentials could be involved is **Sync Vault**
> (VAULT-21), which runs *your own* `git` against *your own* remote; QUILL does not
> collect or store a git password itself. If a scenario below ever surprises you by
> demanding a passphrase or claiming to "encrypt" a note, that is a **surface bug** —
> record it. (This corrects the security framing some earlier drafts assumed.)

**Where to find these commands.** None of the `vault.*` commands has a default
keyboard shortcut — the surface list shows an empty shortcut for every one, and
they are assigned only if you add them yourself in the Keymap editor. Every command
lives under **Tools menu ▸ Vault ▸ …**. To open that submenu by keyboard: press
**Alt**, then **T** (Tools), then **V** (Vault), then the item's underlined letter.
Any command can also be run from the **Command Palette** by its label.

**Common inputs used below.** Make a throwaway vault folder once, before VAULT-01,
so nothing important is touched. Create a folder named **`qa-vault`** (anywhere you
like, e.g. next to `qa-samples`) containing these three plain-text files — type them
exactly:

- `qa-vault/Welcome.md`

  ```
  # Welcome

  This is the QA welcome note. See [[Ideas]] for more. #project
  ```

- `qa-vault/Ideas.md`

  ```
  # Ideas

  A dummy note for testing. The Welcome note is a good starting point. #project

  ![[Welcome]]
  ```

- `qa-vault/Templates/Daily.md`  (put this one inside a `Templates` subfolder)

  ```
  # {{title}}

  Created {{date:YYYY-MM-DD}}.
  ```

None of this is sensitive — it is safe to delete the whole `qa-vault` folder when
you finish the section.

---

## VAULT-01 — Open Vault (`vault.open`, no default shortcut)

*What & why.* Point QUILL at a folder of notes. QUILL scans and indexes it, remembers
it as your active vault, and tells you how big it is. Everything else in this section
needs a vault open first.

**Before you start**
- The **`qa-vault`** folder created above, with its three notes on disk.
- No vault open yet (a fresh QUILL is fine).

**Do this**
1. Open **Tools menu (Alt, T) ▸ Vault (V) ▸ Open Vault…** (mnemonic **O**).
2. In the folder picker ("Choose a vault folder (a folder of notes)"), navigate to
   and select the **`qa-vault`** folder; press **Enter**.

**You should see and hear**
- A keyboard-navigable folder picker, announced. On confirm QUILL scans the folder
  ("Scanning vault…" may flash in the status bar) and then announces the size in
  substance: **"Vault qa-vault: 2 notes, 1 link."** (The `Templates/Daily.md` note
  is counted too if it is inside the vault root — a count of 2 or 3 is fine; the
  load-bearing part is that it names the vault and reports non-zero notes.) Choosing
  **Cancel** instead says **"Open Vault cancelled"** and changes nothing. A folder it
  cannot scan is reported ("Could not open the vault" / "Could not scan the vault: …"),
  never a silent failure.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## VAULT-02 — Vault Explorer (`vault.explorer`, no default shortcut)

*What & why.* A keyboard tree of every note in the vault, so you can browse and open
notes without touching the file system.

**Before you start**
- `qa-vault` open (VAULT-01 passed).

**Do this**
1. **Tools ▸ Vault ▸ Vault Explorer…** (mnemonic **x**).
2. Arrow through the tree; land on **Ideas**; press the **Open** button (or Enter).

**You should see and hear**
- A dialog titled **"Vault Explorer"** with an announced tree of notes and standard
  **Open** / **Cancel** buttons. Arrowing reads each note's title. Activating **Open**
  closes the dialog and opens that note in the editor with focus in the text. **Escape**
  cancels and returns focus to the editor. If the vault had no notes, QUILL would say
  **"The vault has no notes yet"** instead of opening an empty dialog.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## VAULT-03 — Go to Note (`vault.quick_switch`, no default shortcut)

*What & why.* A filter-as-you-type switcher: start typing part of a note's title and
jump straight to it. The fastest way around a large vault.

**Before you start**
- `qa-vault` open.

**Do this**
1. **Tools ▸ Vault ▸ Go to Note…** (mnemonic **G**).
2. In the field ("Type part of a note title:"), type **`ide`**.
3. Arrow to the **Ideas** match and press **Enter**.

**You should see and hear**
- A dialog with a labelled text field and a results list that **narrows as you type**;
  the result count is announced (in "matches"). Typing `ide` leaves **Ideas** matched.
  Enter closes the dialog and opens **Ideas.md** with focus in the editor. Escape
  cancels. An empty vault would say **"The vault has no notes yet."**

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## VAULT-04 — Search Vault (`vault.search`, no default shortcut)

*What & why.* Full-text search across **every** note; open a result at its exact
matching line.

**Before you start**
- `qa-vault` open.

**Do this**
1. **Tools ▸ Vault ▸ Search Vault…** (mnemonic **S**).
2. In the field ("Search all notes:"), type **`dummy`**.
3. Tab to the **Regex** and **Whole word** checkboxes — confirm both are present and
   toggle-able; leave them **off**.
4. Arrow to the result and press **Enter**.

**You should see and hear**
- A labelled search field, a live results list, and two option checkboxes named
  **Regex** and **Whole word**. Each result is announced in substance as
  **"Ideas, line 3: …dummy…"** — the note **title**, the **line number**, and a
  match-centred snippet. Activating a result opens that note **at the matching line**
  (the caret lands on that line, announced). An empty query yields no results (not an
  error).

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## VAULT-05 — Show Tags (`vault.tags`, no default shortcut)

*What & why.* Browse the vault by `#tag`: filter the tag list, then list every note
carrying a chosen tag.

**Before you start**
- `qa-vault` open (both sample notes contain **`#project`**).

**Do this**
1. **Tools ▸ Vault ▸ Show Tags…** (mnemonic **T**).
2. In the field ("Filter tags:"), optionally type **`pro`**.
3. Arrow to **#project** and press **Enter**.

**You should see and hear**
- A filterable tag list whose rows read as **"#project — 2 note(s)"** (tag plus a
  note count). Activating a tag announces **"#project: 2 note(s)"** and opens a second
  list titled **"Notes tagged #project"** listing **Welcome** and **Ideas**; activating
  one opens it. A vault with no tags says **"This vault has no tags yet."**

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## VAULT-06 — Insert Link to Note (`vault.insert_link`, no default shortcut)

*What & why.* Pick an existing note by title and drop a `[[Title]]` wikilink at the
caret — no need to remember exact names.

**Before you start**
- `qa-vault` open. Open **Welcome.md**, put the caret on a blank line at the end.

**Do this**
1. **Tools ▸ Vault ▸ Insert Link to Note…** (mnemonic **I**).
2. In the list ("Insert link to note"), arrow to **Ideas** and press **Enter**.

**You should see and hear**
- A labelled list of note titles. Activating **Ideas** inserts the literal text
  **`[[Ideas]]`** at the caret and announces **"Linked to Ideas."** If the vault had
  no notes, QUILL says **"The vault has no notes to link to."**

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## VAULT-07 — Complete Link or Tag at Cursor (`vault.complete`, no default shortcut)

*What & why.* While typing a `[[note` or a `#tag`, complete it from a spoken, filtered
list without leaving the flow.

**Before you start**
- `qa-vault` open, **Welcome.md** in focus. Type **`[[Id`** (two open brackets, then
  `Id`) at the end of the note, leaving the caret right after the `d`.

**Do this**
1. **Tools ▸ Vault ▸ Complete Link or Tag…** (mnemonic **C**).
2. In the completer ("Complete Link", prompt "Note:"), arrow to **Ideas**; press
   **Enter**.

**You should see and hear**
- Because the caret sits inside a `[[…` trigger, a completer titled **"Complete Link"**
  opens filtered to matching note titles. Choosing **Ideas** rewrites the partial link
  into a full **`[[Ideas]]`** and announces **"Inserted Ideas."** If you instead had a
  `#pro` fragment, the completer would be **"Complete Tag"** (prompt "Tag:") over tag
  names. With the caret **not** on a `[[` or `#` fragment, QUILL says **"Type [[ for a
  note or # for a tag, then complete."** No matches says **"No matching notes/tags."**

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## VAULT-08 — Follow Wikilink (`vault.follow_link`, no default shortcut)

*What & why.* With the caret inside a `[[wikilink]]`, jump to the note it names — and
if the note does not exist, offer to create it.

**Before you start**
- `qa-vault` open. Open **Welcome.md** and put the caret **inside** the `[[Ideas]]`
  link (between the brackets).

**Do this**
1. **Tools ▸ Vault ▸ Follow Wikilink** (mnemonic **F**).
2. Then test the *missing-note* path: type a new link **`[[Nowhere]]`**, caret inside
   it, run **Follow Wikilink** again, and answer the prompt.

**You should see and hear**
- With the caret on `[[Ideas]]`, **Ideas.md** opens in the editor (at the target
  heading/block if the link named one). For **`[[Nowhere]]`**, a spoken confirmation
  **"No note named \"Nowhere\". Create it?"** appears (Yes/No); **No** does nothing
  ("No note created"), **Yes** creates `Nowhere.md` (seeded with a `# Nowhere` heading),
  opens it, and says **"Created and opened Nowhere."** If a name is ambiguous (two notes
  share it), QUILL **asks** which to open — it never guesses. Caret not on a link →
  **"No wikilink at the cursor."** No vault open → **"Open a vault first (Tools >
  Vault > Open Vault)."**

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## VAULT-09 — Show Backlinks (`vault.backlinks`, no default shortcut)

*What & why.* List every note that links **to** the current note, each read with the
line it links from — so you can see what points here.

**Before you start**
- `qa-vault` open. Open **Ideas.md** (Welcome links to it via `[[Ideas]]`).

**Do this**
1. **Tools ▸ Vault ▸ Show Backlinks** (mnemonic **B**).
2. Arrow the list; press **Enter** on the **Welcome** entry.

**You should see and hear**
- QUILL announces **"1 notes link here."** and opens a list titled **"Backlinks to
  Ideas"** whose row reads **"Welcome: …See [[Ideas]] for more…"** (the linking note's
  title plus the linking line). Enter opens **Welcome.md** at that link. A note nothing
  links to says **"No backlinks: no other note links here yet."** A note not saved
  inside the vault says **"Save this note inside the vault to see its backlinks."**

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## VAULT-10 — Note Neighborhood (`vault.neighborhood`, no default shortcut)

*What & why.* One list of this note's **outgoing** links and its **incoming**
backlinks together, so you can traverse the graph by ear.

**Before you start**
- `qa-vault` open. Open **Welcome.md** (it links out to Ideas; Ideas embeds it back).

**Do this**
1. **Tools ▸ Vault ▸ Note Neighborhood** (mnemonic **N**).
2. Arrow the combined list; press **Enter** on an entry to jump to it.

**You should see and hear**
- QUILL announces the shape, e.g. **"1 out, 1 in,"** and opens a list titled
  **"Neighborhood of Welcome."** Outgoing entries are prefixed **`→`** (e.g. "→ Ideas")
  and incoming ones **`←`** (e.g. "← Ideas: …"). Activating any entry opens that note.
  A note with no links either way says **"This note has no links in or out yet."**

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## VAULT-11 — Unlinked Mentions (`vault.unlinked_mentions`, no default shortcut)

*What & why.* Find places where **other notes mention this note's name in plain text**
but have not yet linked it — candidates to turn into `[[links]]`.

**Before you start**
- `qa-vault` open. Open **Welcome.md** (Ideas.md says "The **Welcome** note…" without
  linking it).

**Do this**
1. **Tools ▸ Vault ▸ Unlinked Mentions** (mnemonic **U**).
2. Arrow the list; press **Enter** on a mention to open it at that spot.

**You should see and hear**
- QUILL announces **"1 unlinked mention(s)"** and opens a list titled **"Unlinked
  mentions of Welcome"** whose row reads **"Ideas: …The Welcome note is a good starting
  point…"**. Activating it opens Ideas.md at that mention. If every mention is already
  a link, QUILL says **"No unlinked mentions: every mention of this note is already a
  link."**

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## VAULT-12 — Speak Embed at Cursor (`vault.speak_embed`, no default shortcut)

*What & why.* Read aloud the content that an `![[embed]]` points to **without
changing your text** — a peek at the embedded note.

**Before you start**
- `qa-vault` open. Open **Ideas.md** and put the caret **inside** its `![[Welcome]]`
  embed (note the leading `!`).

**Do this**
1. **Tools ▸ Vault ▸ Speak Embed at Cursor** (mnemonic **k**).

**You should see and hear**
- QUILL speaks the embedded note's content in substance: **"Embedded from Welcome: …This
  is the QA welcome note…"** — and your document text is **unchanged**. Two guard cases
  to confirm: with the caret on a plain `[[Welcome]]` (no `!`), QUILL says **"That is a
  link, not an embed. To embed the note, add an exclamation mark before it:
  ![[Welcome]]"**; with the caret on no embed at all, **"No embed (![[...]]) at the
  cursor."**

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## VAULT-13 — Resolve Embed Inline (`vault.resolve_embed`, no default shortcut)

*What & why.* Replace an `![[embed]]` in place with the embedded note's actual text,
as **one undoable edit** — bake the transclusion into this note.

**Before you start**
- `qa-vault` open. Open **Ideas.md**, caret inside the `![[Welcome]]` embed.

**Do this**
1. **Tools ▸ Vault ▸ Resolve Embed Inline** (mnemonic **R**).
2. Then press **Ctrl+Z** to confirm it is a single undo.

**You should see and hear**
- The `![[Welcome]]` marker is replaced by Welcome's content and QUILL announces
  **"Resolved embed inline."** A single **Ctrl+Z** restores the `![[Welcome]]` marker
  (one undo step). The same not-an-embed / no-embed guards as VAULT-12 apply.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## VAULT-14 — Insert Template (`vault.insert_template`, no default shortcut)

*What & why.* Insert a reusable note skeleton from the vault's **Templates** folder,
filling in date/title and prompting for any `{{placeholders}}`.

**Before you start**
- `qa-vault` open, with the **`Templates/Daily.md`** file created above. Open (or
  create) any note and place the caret where the template should go.

**Do this**
1. **Tools ▸ Vault ▸ Insert Template…** (mnemonic **T**).
2. In the list ("Insert Template"), arrow to **Daily** and press **Enter**.
3. Answer any prompt the template raises; press **Enter**.

**You should see and hear**
- A list of template names (from the `Templates` folder). Activating **Daily** inserts
  its rendered text at the caret — `{{date:YYYY-MM-DD}}` becomes today's date and
  `{{title}}` becomes the note's title — and announces **"Template inserted."** If the
  template contains a free `{{prompt}}`, a labelled text box asks for it first; Cancel
  says **"Template cancelled."** With no templates present, QUILL says **"No templates:
  add .md files to a 'Templates' folder in the vault."**

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## VAULT-15 — Open Today's Note (`vault.today`, no default shortcut)

*What & why.* Open today's **daily note**, creating it from the daily-note pattern if
it does not exist. The backbone of a journaling / daily-log workflow.

**Before you start**
- `qa-vault` open. (The default daily pattern uses `{{date:YYYY-MM-DD}}`; see
  VAULT-19 to change it.)

**Do this**
1. **Tools ▸ Vault ▸ Open Today's Note** (mnemonic **y**).

**You should see and hear**
- If today's note does not exist yet, QUILL creates it (seeded with a
  `# 2026-08-06`-style date heading), opens it, and announces **"2026-08-06: created"**
  (today's date). Run it again and it announces **"…: opened"** for the existing note.
  Focus lands in the editor. This also sets the "daily cursor" to today for VAULT-16/17.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## VAULT-16 — Previous Daily Note (`vault.prev_daily`, no default shortcut)

*What & why.* Step the daily cursor **back one day** and open (creating if needed)
that day's note — flip back through your journal.

**Before you start**
- `qa-vault` open and VAULT-15 just run (the daily cursor is on today).

**Do this**
1. **Tools ▸ Vault ▸ Previous Daily Note** (mnemonic **P**).

**You should see and hear**
- Yesterday's daily note opens; QUILL announces its date with **"created"** (first time)
  or **"opened"** (if it already exists). Running it again steps another day back. Focus
  lands in the editor each time. No vault open → **"Open a vault first (Tools > Vault >
  Open Vault)."**

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## VAULT-17 — Next Daily Note (`vault.next_daily`, no default shortcut)

*What & why.* Step the daily cursor **forward one day** and open that day's note — the
mirror of VAULT-16.

**Before you start**
- `qa-vault` open; the daily cursor sitting on a past day (run VAULT-16 first).

**Do this**
1. **Tools ▸ Vault ▸ Next Daily Note** (mnemonic **N**).

**You should see and hear**
- The next day's daily note opens with its date announced ("opened"/"created"); repeated
  presses walk forward day by day back toward today. Focus lands in the editor.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## VAULT-18 — Rename Note (`vault.rename`, no default shortcut)

*What & why.* Rename the current note **and rewrite every inbound `[[link]]`** that
named it, so no link breaks. A confirmed, count-aware refactor.

**Before you start**
- `qa-vault` open. Open **Ideas.md** (Welcome links to it as `[[Ideas]]`). New name:
  **`Concepts`**.

**Do this**
1. **Tools ▸ Vault ▸ Rename Note…** (mnemonic **R**).
2. In the "New name for this note:" box, replace the text with **`Concepts`**; press
   **Enter**.
3. Read the confirmation and choose **Yes**.

**You should see and hear**
- A prompt pre-filled with the old title. On confirm, a spoken confirmation names the
  change and its blast radius: **"Rename \"Ideas\" to \"Concepts\" and update 1 link(s)
  in 1 note(s)?"** (Yes/No). **Yes** renames `Ideas.md` to `Concepts.md`, rewrites
  Welcome's `[[Ideas]]` to `[[Concepts]]`, retitles the heading, reopens the renamed
  note, and announces **"Renamed to Concepts. Updated 1 link(s) in 1 note(s)."** **No**
  or **Escape** → **"Rename cancelled."** A name that collides with an existing note is
  refused clearly (**"A note named \"Concepts\" already exists"**), and an unusable
  file name is rejected. *(Optional: rename it back to `Ideas` so later re-runs match.)*

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## VAULT-19 — Vault Settings (`vault.settings`, no default shortcut)

*What & why.* Set the vault's **Templates folder** and its **daily-note path pattern**,
persisted for next time.

**Before you start**
- `qa-vault` open.

**Do this**
1. **Tools ▸ Vault ▸ Vault Settings…** (mnemonic **t**).
2. First prompt, "Templates folder (relative to the vault):" — leave **`Templates`**;
   press **Enter**.
3. Second prompt, "Daily-note path pattern (use {{date:YYYY-MM-DD}}):" — leave the
   default (or type **`{{date:YYYY-MM-DD}}`**); press **Enter**.

**You should see and hear**
- Two labelled text prompts in order (templates folder, then daily pattern), each
  pre-filled with the current value. On confirm QUILL announces **"Vault settings
  saved,"** and the values persist (re-open the dialog to confirm). Cancelling either
  prompt says **"Vault settings unchanged"** and changes nothing.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## VAULT-20 — Export Vault as Website (`vault.export_site`, no default shortcut)

*What & why.* Turn the whole vault into a static, cross-linked **HTML site** you can
host or share — runs in the background so the editor stays responsive.

**Before you start**
- `qa-vault` open. Pick (or make) an **empty output folder**, e.g. `qa-vault-site`.

**Do this**
1. **Tools ▸ Vault ▸ Export Vault as Website…** (mnemonic **E**).
2. In the folder picker ("Choose an output folder for the website"), select
   **`qa-vault-site`**; press **Enter**.
3. Wait for completion, then open the resulting `index`/note pages in a browser.

**You should see and hear**
- A folder picker (Cancel says **"Export cancelled"**). On confirm, a background task
  runs ("Exporting vault as a website") and, on finish, announces **"Exported N pages
  to <folder>."** The output folder then contains one HTML page per note with the
  `[[wikilinks]]` turned into working `<a>` links between pages. The editor stays usable
  throughout.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## VAULT-21 — Sync Vault (`vault.sync`, no default shortcut)

*What & why.* Commit, pull, and push the vault over **your own git remote** — back it
up or share it across machines. QUILL runs `git`; it is not a QUILL-hosted service.

**Before you start**
- **Precondition:** the vault folder is a **git repository with a configured remote**
  you can push to, and `git` is on PATH. If not, mark **Blocked** and note why.
- QUILL must **not** be in Safe Mode (Safe Mode disables sync).
- Security note: QUILL does not collect or store a git password; authentication is
  whatever your git setup already uses (credential helper, SSH key). Confirm no
  passphrase or secret is ever echoed in an announcement or the status bar.

**Do this**
1. **Tools ▸ Vault ▸ Sync Vault** (mnemonic **y**).
2. Wait for the background sync to finish; read the spoken result.

**You should see and hear**
- A background task ("Syncing vault") that commits local changes, pulls, and pushes,
  then announces its **result message** (what happened). If there are merge
  **conflicts**, QUILL opens a list titled **"Sync conflicts — resolve, then sync
  again"** naming the conflicting files rather than silently overwriting anything. In
  **Safe Mode**, running it says **"Vault sync is disabled in Safe Mode."** No vault
  open → **"Open a vault first (Tools > Vault > Open Vault)."** Nothing sensitive should
  appear in any spoken/status text.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## VAULT-22 — Publish Note (`vault.publish_note`, no default shortcut) [GATED `future.publishing`]

*What & why.* Prepare the current note to be published (the "send it out" path). This
command is **gated behind the `future.publishing` flag** and is **locked off** in the
public 1.0 build — it is hidden from both the Vault menu and the Command Palette until
the flag is unlocked.

**Before you start**
- `qa-vault` open, a saved note in focus.
- **Public build:** this command is **absent** — there is no "Publish Note" item in
  **Tools ▸ Vault** and none in the Command Palette. That absence is the expected
  result; mark **N/A** and confirm it in `gated-absence.md`.
- **Dev/admin build with `future.publishing` enabled:** proceed with the steps.

**Do this**
1. Confirm there is **no** "Publish Note" entry in the Vault menu or Command Palette on
   a public build (this is the pass on public builds).
2. *(Gated build only)* Run **Publish Note** from the Command Palette; observe the
   result.

**You should see and hear**
- **Public build:** the command does not appear anywhere — QUILL never offers to
  "publish" a note in 1.0. If it *does* appear, that is a gating failure — **Fail** and
  record it. **N/A** otherwise.
- **Gated build:** with the flag on, QUILL prepares the note and announces **"Prepared
  '<title>' to publish."**; if the flag is still effectively off it says **"Publishing
  notes is not enabled yet."** A note not saved inside the vault → **"Save this note
  inside the vault first."**

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

### Section sign-off
- Tester:
- Screen reader(s) + version(s):
- Build / commit tested:
- Environment (E1–E6):
- Date:
- Scenarios passed / total: ___ / 22
- Release blockers found (must be zero to ship):
- Result: Pass / Pass-with-notes / Fail
- Notes:
