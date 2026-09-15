# Where QuillLite's model is worse than QUILL's

**Status: first pass complete, 2026-09-15.** Written as I read, so the order is
the order I found things, and the summary is at the bottom. **Completed items
are deleted from this file** — the summary's "Done" table is the record of what
landed, which is why the section numbers have gaps.

## What this is

QuillLite and QUILL implement the same user-facing behaviours twice. Sometimes
that is deliberate and right (QuillLite keeps its own data folder; it reads
`.txt` and `.rtf` only). Sometimes it is an accident of two people solving the
same problem on different days, and then one of them is worse. This is a hunt
for the second kind, in the places a person actually *feels* — how a command
behaves, what it says, and what it does when it cannot do the thing.

It is not a command-by-command diff. Most rows would say "same", and the
interesting divergences are in the **model**, not the presence or absence of a
verb.

## Method

For each behaviour both editors have:

1. Read both implementations.
2. Write down the *model* each one uses — not the code, the promise it makes.
3. Where they differ, decide which is better **for a listener**, and why.
4. Record it below with the evidence, so the decision can be argued with.

Severity is about the person, not the code:

| | |
| --- | --- |
| **Broken** | The feature does not do what it says, or cannot be used as designed. |
| **Worse** | Both work; QuillLite's costs the listener more keystrokes, more uncertainty, or more silence. |
| **Divergent** | Different on purpose, or harmlessly different. Recorded so nobody re-litigates it. |

---

## 2. Find and replace otherwise: **aligned**

Recorded so nobody goes looking again. The two implementations already share:

* the wrap setting (`settings.wrap_find`), honoured in both directions -- a
  previous parity fix, noted in QuillLite's own source as "QUILL's setting,
  honoured here too. QuillLite always wrapped, in both directions, with no way
  to say otherwise";
* the **two different sentences for two different misses**, which is the subtle
  part: wrapping on gives "Not found: X" (change what you are looking for),
  wrapping off gives "No more matches. Reached the end of the document, and
  wrapping is off" (go to the other end and press again). A listener told the
  first when the second is true stops searching for a word that is in the
  document;
* the feedback channel (`settings.find_not_found_feedback`), resolved through
  the one shared rule in `quill.core.action_feedback` so the two cannot answer
  differently.

The dialogs differ -- QUILL uses the native `wx.FindReplaceDialog`, QuillLite
its own modeless one -- but that is presentation, not model.

---

## 3. The two editors disagree about 67 chords, and a few of the disagreements bite (**Worse**)

This is the biggest thing in the audit and the least like a bug, so it needs
care. QUILL has far more commands than QuillLite and a leader-key layer
(`Ctrl+Shift+Grave, X`) that QuillLite does not, so *some* divergence is
structural and fine. CLAUDE.md already sets the rule: "Where the two must
diverge on a key, the reason is a comment in `keymap.py`."

Sixty-seven chords are bound to genuinely different actions in the two editors.
Most are harmless -- QUILL binds something QuillLite has never heard of. Two
groups are not.

### 3a. Muscle memory that does damage in the other editor

These are the ones where a habit from one app does something *destructive or
surprising* in the other, rather than nothing:

| Chord | QUILL | QuillLite |
| --- | --- | --- |
| `Ctrl+Shift+1` .. `Ctrl+Shift+9` | **Paste from tray slot N** | **Set bookmark N** |
| `Ctrl+Shift+V` | **Preview** | **Paste as Plain Text** |
| `Ctrl+Alt+V` | **Paste as Plain Text** | **Paste from Tray** |
| `Ctrl+Shift+H` | **Replace All** | **Select Paragraph** |
| `Ctrl+Alt+K` | **Insert Link** | **Remove Blank Lines** |
| `Ctrl+Alt+T` | **Insert Table** | **Trim Trailing Space** |

The tray/bookmark row is the worst of these and it is nine chords wide. A
QuillLite user who has learned "`Ctrl+Shift+3` marks my place" presses it in
QUILL and **pastes the contents of tray slot 3 into the document**. Nothing
warns them; it is a normal, valid paste. The reverse direction is harmless (a
bookmark is set), which is exactly why it could ship without anyone noticing.

`Ctrl+Shift+H` is the same shape: Select Paragraph in QuillLite, Replace All in
QUILL.

### 3b. The structural selection family, where nothing transfers

Six commands both editors have, under the same names, on six different chords:

| Command | QUILL | QuillLite |
| --- | --- | --- |
| Select Word | `Ctrl+Alt+W` | `Ctrl+Shift+W` |
| Select Line | `Ctrl+Alt+E` | `Ctrl+Shift+E` |
| Select Paragraph | `Ctrl+Alt+Shift+P` | `Ctrl+Shift+H` |
| Select Block | `Ctrl+Shift+B` | `Ctrl+Alt+Shift+B` |
| Expand Selection | `Ctrl+Shift+Grave, J` | `Ctrl+Shift+X` |
| Shrink Selection | `Ctrl+Shift+Grave, Shift+J` | `Ctrl+Alt+Shift+X` |

This is a coherent feature family a listener uses constantly -- it is the
answer to "selecting by shift+arrow is a miserable way to take four paragraphs"
-- and **not one of the six keys is the same in both editors**. Somebody who
learns structural selection in QuillLite has learned nothing transferable, and
`Ctrl+Shift+W` in QUILL gives them a word count instead.

Three more in the same shape: Exchange Point and Mark (`Ctrl+Shift+X` /
`Ctrl+Alt+X`), Insert Special Character (`Shift+F2` / `Ctrl+Shift+F2`), List
Bookmarks (`Alt+Shift+B` / `Alt+Shift+G`), Duplicate Selection
(`Ctrl+Alt+Shift+Q` / `Ctrl+Alt+Q`), Set Mark (`Ctrl+Shift+M` /
`Ctrl+Alt+Shift+K`).

### 3c. Where QuillLite is simply right and QUILL should follow

Three commands QuillLite puts on a plain chord and QUILL buries on the
two-stroke leader chord: **Insert HTML Tag** (`Ctrl+Alt+O` in QuillLite),
**Go To Anything**, and **Manage Abbreviations**. Same shape as F1 was.

### Why this matters more than it looks

The apps are marketed as a family, share a runtime, and are explicitly aimed at
people who cannot glance at a menu to check. A key that does the wrong thing is
worse than a key that does nothing, and the tray/bookmark overlap is nine
chords of exactly that.

**What I would not do:** mass-rebind either editor. Every one of these keys is
somebody's habit today, and churn has its own cost. The proposal is narrower:

1. Fix the **destructive** overlaps first (3a), starting with tray/bookmark.
2. Align the **structural selection family** (3b), since it is one coherent
   decision rather than nine separate ones.
3. Take the free wins (3c) -- F1 especially.
4. Write the remaining deliberate divergences down as comments in the keymaps,
   which is what CLAUDE.md already asks for and what would have caught this.

---

## 4. The copy tray is two different features wearing one name (**Worse**, both ways)

Both editors ship a twelve-slot persistent clipboard built on the same
`quill.core.copy_tray.CopyTray`. The engine is shared. Everything a person
touches is different.

**Copying into it.**

* QUILL: twelve commands, `Ctrl+Shift+Grave, Shift+1` .. `Shift+=`. **You choose
  the slot.**
* QuillLite: one command, `Ctrl+Alt+Y`, which walks the slots and takes **the
  first empty one**, falling back to slot 1 when all twelve are full.

QuillLite's own module docstring argues for QUILL's model, which is what makes
this worth writing down:

> Twelve *numbered* slots that survive a restart. Copy to slot 3, paste from
> slot 3 an hour later. The same shape as the bookmarks, for the same reason:
> **a number is a handle a person can hold.**

You cannot copy to slot 3 in QuillLite. The number is assigned to you, and
announced after the fact. And the comparison to bookmarks is exactly backwards
in its own app: QuillLite's bookmarks *are* chosen by number (`Ctrl+Shift+3`
sets bookmark 3) while its tray slots are not.

Worse, when all twelve slots are full the fallback is **slot 1**, silently
overwriting the oldest handle somebody was holding. It announces which slot it
used, so it is not invisible -- but "Copied to tray slot 1" after eleven
successful copies reads like success rather than a wrap.

**Pasting out of it.**

* QUILL: twelve direct chords, each routed through a multi-press dispatcher --
  **single press pastes, double press peeks** (announces the slot's contents
  *without* pasting), triple press opens the dialog.
* QuillLite: one chord, which opens a chooser listing every non-empty slot with
  a preview.

Neither is strictly worse and they solve different halves. QUILL's is the fast
path for a slot you know; QuillLite's is the overview for one you do not.
QUILL has both, because triple-press reaches the same dialog. QuillLite has
only the overview -- there is no way to say "slot 3, now".

The peek is the part I would not want to lose in either. For a listener,
"what is in slot 3?" without modifying the document is the difference between
checking and gambling.

**Fix shape:** give QuillLite chosen-slot copying (its own rationale asks for
it), and decide deliberately whether the fast paste path is worth twelve chords
in a small product. It may honestly not be -- but "no fast path" should be a
decision, not what fell out of having one command.

---

## 5. Recovery: **divergent, and defensibly so**

Two separate implementations (`quill/core/recovery.py`, `quill/core/lite/recovery.py`)
for the same job, and QuillLite's has to be separate because it keeps its own
data folder. Both hold the two decisions that matter, and hold them the same
way:

* the original file is never touched -- a slot is a copy beside it, so a crash
  mid-save cannot leave a truncated original *and* no recovery;
* an empty slot is not a slot, so a window that was modified and then emptied
  is not offered back over a real document.

No finding. Recorded so nobody re-opens it.

## Summary, in the order I would fix them

Nothing here is changed in code. This is the recommendation.

| # | Finding | Severity | Cost to fix |
| --- | --- | --- | --- |
**Still open:**

| # | Finding | Severity | Cost to fix |
| --- | --- | --- | --- |
| 3a | `Ctrl+Shift+1`-`9` pastes in QUILL, bookmarks in QuillLite (+5 more overlaps) | **Worse**, one direction destructive | Medium -- it is a keymap decision, not code |
| 3b | Structural selection family: six commands, six different chords | **Worse** | Medium -- one coherent decision |
| 4 | Copy tray: QuillLite cannot choose a slot; no peek | **Worse**, both ways | Small-medium |
| 3c | Insert HTML Tag, Go To Anything, Manage Abbreviations on leader chords in QUILL | **Worse**, small | Small |

**Done:**

| # | Finding | Landed |
| --- | --- | --- |
| 0 | F8 started a mode that fought the caret | `d20fabe` |
| 1 | Replace All took N undos in QuillLite | 2026-09-15 |
| 3c | F1 was unbound in QUILL | 2026-09-15 |
| 5a | Autosave 60s in QuillLite, 30s in QUILL | 2026-09-15 |

**No action needed:** find and replace otherwise (aligned); recovery
(divergent, defensibly).

### The one that worries me most

**3a, the tray/bookmark overlap.** It is nine chords wide, it is silent, and the
damage runs one way: a QuillLite habit pastes text into a QUILL document. The
reverse is harmless, which is precisely why it survived -- whoever tested it was
going in the safe direction.

### What would have caught all of this

CLAUDE.md already says: *"Where the two must diverge on a key, the reason is a
comment in `keymap.py`."* That rule is not enforced by anything. A gate that
compares the two keymaps for same-named commands and requires a written reason
for each difference would have caught 3b and 3c on the day they landed, and
would have made 3a a deliberate decision rather than an accident.

---

*Audit complete for the interaction-model pass. Areas read: selection, find and
replace, undo granularity, keymaps, clipboard/copy tray, recovery, autosave.
Not covered: spelling, printing, themes, the status bar's cell model -- say the
word and I will keep going.*
