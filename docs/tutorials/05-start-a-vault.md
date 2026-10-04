# Tutorial 5: Start an Accessible Vault

**Goal:** in about twenty minutes, turn an empty folder into a set of notes
that link to each other, with backlinks, tags, daily notes and sync.

A vault is **just a folder of Markdown files**. QUILL keeps a small index to
find things quickly (you can delete it without losing a word). When you want
to know how your notes connect, QUILL tells you in words instead of drawing a
picture.

## 1. Create and open the vault

1. Make a folder, for example `Documents\Notes`.
2. **Tools > Vault > Open Vault...** and pick it. QUILL indexes it and
   announces: "Vault Notes: 0 notes, 0 links."

## 2. Your first three linked notes

1. Create `Projects.md`, write a line, and save it into the vault folder.
2. Create `QUILL.md` and inside it type: `Part of my [[Projects]] work.`
3. Create `Podcast.md` and type: `A [[Projects]] idea that uses [[QUILL]].`
4. In `Podcast.md`, put the caret on `[[QUILL]]` and run **Follow Wikilink**.
   You are taken to `QUILL.md`.
5. Now go to `Projects.md` and run **Show Backlinks**. QUILL answers "2 notes
   link here" and reads each link *with the sentence it lives in*. Enter opens
   the source at the mention.

That is how you find out which notes point to this one, by ear.

## 3. Daily habits

- **Complete Link or Tag at Cursor** finishes a half-typed `[[note` or `#tag`.
  Pick from a short list as you type.
- **Go to Note**: type part of a note's name to jump to it. **Search Vault**
  searches every note and takes you straight to the line it found.
- Add `#project/quill` style tags anywhere; **Show Tags** groups them
  (`#project` also finds `#project/quill`).
- **Open Today's Note** starts a dated journal entry; **Previous Daily Note**
  and **Next Daily Note** move through your journal.
- **Insert Template** fills in `{{date}}` and `{{title}}`, asks you for
  anything marked `{{prompt}}`, and puts the cursor at `{{cursor}}`. Choose
  your Templates folder in **Vault Settings**.

## 4. As your notes grow

- A `[[link]]` to a note that does not exist offers to **create** it. If two
  notes have the same name, QUILL asks you which one you mean instead of
  guessing.
- **Rename Note** renames the file, its main heading, and every link to it.
- **Unlinked Mentions** finds where you wrote a note's name without linking
  it, so you can add the link.
- **Note Neighborhood** lists every note this one links to, and every note
  that links to it.

## 5. Share and sync

- **Export Vault as Website** writes a small accessible website, with one page
  per note and all the links working, ready to put online wherever you like.
- **Sync Vault** keeps your notes in step with **your own Git repository**. If
  the same note changed in two places, it lists it for you to decide, instead
  of overwriting anything.

## 6. Ideas to try

- **Research**: one note per source, links to topic notes; backlinks answer
  "which sources discuss this?"
- **Fiction**: a note per character and place; from a character note,
  backlinks list every scene that mentions them (this works well with Story
  Studio).
- **Work journal**: daily notes and tags. When you need to write your weekly
  report, one search finds it all.

Start small. Ten notes with real links between them are worth more than a big
plan you never finish.

**Next:** [Make a document accessible with GLOW](06-make-it-accessible-with-glow.md).
