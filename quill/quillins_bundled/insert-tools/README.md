# Insert Tools (bundled Quillin)

A first-party, **bundled** Quillin (Tier C) that ships enabled inside QUILL. It
is a pure **Layer 1** snippet pack: three commands that insert the current date,
time, or both at the caret.

## Commands

| Command | Home | Inserts |
| --- | --- | --- |
| Insert Date | Insert > Date and Time | `${date}` - today's date in your configured format. |
| Insert Time | Insert > Date and Time | `${time}` - the current time in your configured format. |
| Insert Date and Time | Insert > Date and Time | `${date} ${time}`. |

## Capabilities

**None.** Layer 1 snippet expansion needs no capabilities, so this Quillin can
never read or write files, reach the network, or touch the clipboard. It is the
smallest possible illustration of a safe, additive contribution.

## Relationship to the built-in Insert Date/Time

QUILL's previous built-in **Insert Date/Time** command (and the **Calculated
Date...** dialog) were removed from the Insert menu and consolidated into this
Quillin. The new **Insert > Date and Time** submenu is the single home for all
three date/time snippet variants: Insert Date, Insert Time, and Insert Date and
Time. This Quillin is the canonical home for these snippets, in keeping with
the Quillin migration that gives bundled extensions first-class menu real
estate. Authors can copy this manifest as a starting point for their own
date/time format snippets.
