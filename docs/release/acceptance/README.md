# QUILL 1.0.0 — Acceptance Test Book (hand-held, exhaustive)

This book exists to answer one question before we ship: **does every feature in
QUILL actually work, for a real person, by keyboard and by ear?**

It is written for a tester **who has never used QUILL**. You do not need to know
the app, the menus, or the shortcuts in advance. Every scenario tells you exactly
what to set up, exactly which keys to press or menu to open, exactly what you
should see and hear, and gives you one box to sign when it happened. If a step
assumes knowledge you do not have, that is a bug in this book — report it.

Where the machine-generated inventories in `../../planning/signoff/` list *that* a
command exists (one line each, 718 of them), this book proves *that each one
works*, in plain language, step by step. The two are companions: the inventory is
the map, this book is the guided walk.

---

## 1. Who runs this, and what you need

You do not need to be a developer. You need:

- A **real, packaged QUILL 1.0.0 build** installed on the machine — either the
  **system installer** (`Quill-Setup-*.exe`) or the **portable ZIP** (a folder you
  unzip and run). Both are tested; they are separate runs (see the environment
  matrix in the master plan, `../../planning/signoff/QUILL-1.0.0-SIGNOFF.md` §A).
- A **screen reader** you can hear: **NVDA** (free, nvaccess.org) or **JAWS** on
  Windows; **Narrator** and **VoiceOver** where a scenario says so. QUILL is built
  for screen-reader users first, so most outcomes are things you *hear*, not just
  see.
- Headphones or speakers, and about a day per environment. Take breaks — an alert
  tester catches what a tired one misses.
- The **sample documents** in `../qa-samples/`. Copy that whole folder onto the
  test machine before you start and read its `README.md` once, so you know what
  each sample is *supposed* to contain. Scenarios that open a sample name it
  exactly; do not substitute your own file.

Keep a notebook (paper or a second document) for the **actual spoken text** and
anything surprising. "It said something" is not a pass; "it said the right thing"
is.

---

## 2. How to read a scenario

Every feature is written as one **scenario** with the same five parts, always in
this order. Here is the anatomy, with what each part is for:

> ### FILE-07 — Save your work (`file.save`, Ctrl+S)
> *What & why.* One or two plain sentences: what this feature is for, and why a
> real user cares. No jargon.
>
> **Before you start**
> - The exact starting state (what is open, what is selected, which settings).
> - The exact **inputs** you will type or choose, spelled out. If a sample file is
>   used, it is named here.
>
> **Do this**
> 1. Numbered, literal actions. Every keystroke *and* the menu path are given, e.g.
>    "Press **Ctrl+S**, or open **File menu ▸ Save**." Never "just save."
> 2. One action per step. If a dialog opens, the next steps walk its fields in Tab
>    order.
>
> **You should see and hear**
> - The **projected outcome**: the announcement (what the screen reader says), where
>    focus lands, what the title bar / status bar shows, and — if a file is written —
>    what the file should contain. Exact wording varies by screen reader; the
>    **field name, role, state, and load-bearing values** (counts, names, format
>    labels) must be present and correct.
>
> **Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
> `[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

The three small boxes are the same three axes the whole release is judged on:

- **Works** — the action does what it says; no error, no crash.
- **Surface-exact** — the label, the menu path, and the shortcut match what this
  book prints. If the menu says something different, the surface is wrong even if
  the action works — fail **Surface-exact** and write down what it actually said.
- **Accessible** — you could do the whole thing **by keyboard alone**, focus went
  where it should, and the outcome was **announced out loud** (and in braille where
  a display is attached). A silent success is an accessibility failure.

**What counts as a fail (any one of these):** focus is lost or lands somewhere
senseless · a value is wrong · the outcome is silent · an error happens with no
spoken message · the file written does not match the projected structure · you had
to reach for the mouse to complete a step.

Mark **Blocked** if you could not run it (a prerequisite app or provider was
missing) and say why. Mark **N/A** if the item is gated out of the build you are
testing (see §5).

---

## 3. The universal keyboard contract (true in every scenario)

You should be able to assume these everywhere. If any scenario breaks one, that is
a fail even if the feature "worked":

- **Tab** / **Shift+Tab** move forward/back through controls in a sensible order.
- **Escape** cancels a dialog and returns focus to where you were.
- **Enter** activates the default button.
- **Alt** opens the menu bar; underlined letters are mnemonics.
- Closing a dialog returns focus to the control that opened it.
- **No destructive action** (overwrite, delete, discard unsaved work) happens
  without a confirmation you can hear and cancel.

Run each UI scenario **twice**: once **with the mouse physically unplugged**
(keyboard only), then again reading with your screen reader's review / virtual
cursor. Both must pass.

---

## 4. The order to run this book

1. **Part 0 — Getting Started** (`00-getting-started.md`). Do this first, once per
   machine. It installs, launches, sets up the screen reader, orients you to the
   window, and walks your very first document. Everything else assumes you have
   finished Part 0.
2. **The feature sections** (`section-*.md`), in any order, but File → Edit →
   Navigate → Format → View first is the gentlest path for a newcomer.
3. **The public companion apps** — Quill Radio (`app-radio.md`) and Quill Weather
   (`app-weather.md`).
4. **Gated-absence** (`gated-absence.md`) — prove the not-for-1.0 apps and features
   are truly gone from a public build.
5. **The required companion plans** already in the repo — the core-journey plan
   (`../qa-core-journeys.md`), the screen-reader plan
   (`../screen-reader-test-plan.md`), and the UAT/regression runbooks. This book
   does not replace them; it surrounds them.

---

## 5. Gated features — what you will and will not see

QUILL 1.0.0 ships the **editor** plus the standalone **Quill Radio** and **Quill
Weather** apps. Several things are **gated off** for the public 1.0 release and must
**not** appear in a public build: the editor-embedded **Internet Radio**,
**Podcasts**, and **Book Library**, and the **Cast / Studio / Converter / Beacon**
companion apps and the **Media Player**.

- In a normal (public) build these are **absent**; scenarios for them are marked
  **N/A** and you instead confirm their absence in `gated-absence.md`.
- A scenario tagged **[GATED]** only appears if a feature flag is on (a dev/admin
  build, e.g. `QUILL_DEV_BUILD=1`). If you are on a public build, mark it **N/A**;
  do not fail it for being missing.

---

## 6. Coverage index (every surface this book must touch)

A section is **Drafted** when its scenarios exist to the standard above, and
**Signed off** only when every scenario in it passes on every applicable
environment. Keep this table current — it is the book's own completeness gate.

| Section | Surface | Scenarios | Drafted | Signed off |
|---|---|---|---|---|
| `00-getting-started.md` | Install, launch, SR setup, first document | 10 | ✅ | ☐ |
| `section-file.md` | `file.*` — File menu | 29 | ✅ | ☐ |
| `section-edit.md` | `edit.*` — Edit / insert / find (incl. 12-slot Copy Tray) | 86 | ✅ | ☐ |
| `section-navigate.md` | `navigate.*` — movement & bookmarks | 28 | ✅ | ☐ |
| `section-format.md` | `format.*` — formatting | 56 | ✅ | ☐ |
| `section-view.md` | `view.*` `window.*` `verbosity.*` — view/window/speech verbosity | 38 | ✅ | ☐ |
| `section-table.md` | `table.*` `reveal.*` `notes.*` + `document/sync/ai/media` | 22 | ✅ | ☐ |
| `section-editor-behaviors.md` | Editor/document behaviors that aren't single commands (autosave, recovery, tabs, status bar, live spell-check, watch folder, encoding/line-ending detection) | 24 | ✅ | ☐ |
| `section-tools-ai.md` | `tools.*` — AI writing/analysis tools | 31 | ✅ | ☐ |
| `section-tools-speech.md` | `tools.*` — dictation, OCR, read-aloud, speech, dictionary | 38 | ✅ | ☐ |
| `section-tools-misc.md` | `tools.*` — compare, keymap, macros, utilities, GLOW | 63 | ✅ | ☐ |
| `section-power.md` | `power.*` — power-user commands | 75 | ✅ | ☐ |
| `section-braille.md` | `braille.*` — braille display & tables | 45 | ✅ | ☐ |
| `section-vault.md` | `vault.*` — knowledge-base **note vault** (wikilinks, backlinks, daily notes, git sync) — *not* an encrypted secrets store | 22 | ✅ | ☐ |
| `section-help.md` | `help.*` — help, about, updates | 21 | ✅ | ☐ |
| `section-github.md` | `github.*` `localgit.*` `publishing.*` — VCS & publishing | 40 | ✅ | ☐ |
| `section-settings.md` | Settings / Preferences — every pane | 23 | ✅ | ☐ |
| `section-quillins.md` | Quillins (extension) system + bundled Quillins | 19 | ✅ | ☐ |
| `section-whisperer.md` | `whisperer.*` — BITS Whisperer [GATED] | 12 | ✅ | ☐ |
| `section-app-adp.md` | `app.*` `adp.*` — app launcher & ADP | 12 | ✅ | ☐ |
| `section-accessibility.md` | Cross-cutting accessibility contract (master §F) | 13 | ✅ | ☐ |
| `app-radio.md` | Quill Radio (public standalone app) | 41 | ✅ | ☐ |
| `app-weather.md` | Quill Weather (public standalone app) | 27 | ✅ | ☐ |
| `gated-absence.md` | Non-public apps/features absent from public build | 7 | ✅ | ☐ |
| `dialogs.md` | Dialog contract, every dialog checkbox by area | 647 | ✅ | ☐ |
| `install-matrix.md` | Portable vs system, secrets, updates, migration | 9 (×E1–E6) | ✅ | ☐ |

Namespace counts come from `../../planning/signoff/SIGNOFF-editor.md`; that file is
the authoritative surface list (command id, label, shortcut) each section is
written against. **Command coverage is verified:** every one of the 645 core-editor
command ids in that inventory has a hand-held scenario with a sign-off box here (the
three `section-tools-*` files together cover all 159 `tools.*` commands). The
remaining 73 of QUILL's 718 commands belong to the companion apps and gated
features, covered in `app-radio.md`, `app-weather.md`, and `gated-absence.md`.

---

## 7. Section sign-off footer (copy into each section)

Every section ends with this block so a partial run is never mistaken for a full
one:

```
### Section sign-off
- Tester:
- Screen reader(s) + version(s):
- Build / commit tested:
- Environment (E1–E6):
- Date:
- Scenarios passed / total:
- Release blockers found (must be zero to ship):
- Result: Pass / Pass-with-notes / Fail
- Notes:
```
