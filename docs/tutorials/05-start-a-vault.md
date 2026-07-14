# Tutorial 5: Start an Accessible Vault

**Goal:** a working linked-notes vault — backlinks, tags, daily notes, and
sync — from an empty folder, in twenty minutes.

A vault is **just a folder of Markdown files**. QUILL adds an index (a small
cache you can delete without losing a word), and every "graph" question gets
a spoken answer instead of a picture.

## 1. Create and open the vault

1. Make a folder, e.g. `Documents\Notes`.
2. **Tools > Vault > Open Vault...** and pick it. QUILL indexes it and
   announces: "Vault Notes: 0 notes, 0 links."

## 2. The first triangle

1. Create `Projects.md`, write a line, and save it into the vault folder.
2. Create `QUILL.md` and inside it type: `Part of my [[Projects]] work.`
3. Create `Podcast.md` and type: `A [[Projects]] idea that uses [[QUILL]].`
4. In `Podcast.md`, put the caret on `[[QUILL]]` and run **Follow Wikilink**
   — you land in `QUILL.md`.
5. Now the magic: in `Projects.md`, run **Show Backlinks**. QUILL answers
   "2 notes link here" and reads each link *with the sentence it lives in*.
   Enter opens the source at the mention.

That is the graph view, spoken.

## 3. Daily habits

- **Complete Link or Tag at Cursor** finishes a half-typed `[[note` or
  `#tag` from a spoken, filtered list.
- **Go to Note** is a type-to-filter switcher; **Search Vault** searches
  every note (regex and whole-word supported) and opens hits at their line.
- Add `#project/quill` style tags anywhere; **Show Tags** rolls nested tags
  up (`#project` finds `#project/quill`).
- **Open Today's Note** starts a dated journal entry;
  **Previous/Next Daily Note** page through your journal.
- **Insert Template** fills `{{date}}`/`{{title}}`, asks any `{{prompt}}`,
  and drops the caret at `{{cursor}}`. Configure the Templates folder in
  **Vault Settings**.

## 4. Growing safely

- A `[[link]]` to a note that does not exist offers to **create** it; an
  ambiguous name gets a spoken **chooser**, never a guess.
- **Rename Note** updates the file, the H1, and every inbound link.
- **Unlinked Mentions** finds where you wrote a note's name without linking
  it — stitch the web tighter.
- **Note Neighborhood** lists everything one hop away, both directions.

## 5. Share and sync

- **Export Vault as Website** writes a small accessible site — one page per
  note, links and embeds resolved — ready to host anywhere.
- **Sync Vault** commits, pulls, and pushes over **your own Git remote**,
  and lists conflicts for you to decide instead of overwriting.

## 6. Ideas that stick

- **Research**: one note per source, links to topic notes; backlinks answer
  "which sources discuss this?"
- **Fiction**: a note per character and place; from a character note,
  backlinks list every scene that mentions them (pairs beautifully with
  Story Studio).
- **Work journal**: daily notes + tags; the Friday report is one vault
  search away.

Start smaller than feels sensible. Ten notes and honest links beat a
taxonomy you will never finish.

**Next:** [Make a document accessible with GLOW](06-make-it-accessible-with-glow.md).
