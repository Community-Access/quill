# Section — Gated-absence (prove the non-1.0 features are gone)

Some things in the codebase are **deliberately not shipped** in QUILL 1.0.0. The
editor-embedded **Internet Radio**, **Podcasts**, and **Book Library**, the
companion apps **Cast / Studio / Converter / Beacon**, the **Media Player**, and a
few experimental features are **gated off** for the public release. This section
does the opposite of the rest of the book: instead of proving a feature works, you
prove a feature is **absent** — invisible and unreachable — in a normal public
build.

Why it matters: a half-hidden feature (missing from the menu but still in the
command palette, or still firing a background check) is a leak. A public user must
have **no path** to a gated feature.

**Before you start (whole section).** Use a **public build** — the default
installer/portable, with **no** developer flag set. If you are unsure, this section
also includes a final scenario that flips `QUILL_DEV_BUILD=1` to prove the features
*reappear* — which is what tells you the gating is a live switch, not just an empty
menu. Standalone **Quill Radio** and **Quill Weather** are *public* apps and must
stay reachable — do **not** flag them here.

Read §5 of `README.md` for the gated-feature rules and §2–§3 for the scenario/box
layout.

---

## GATE-01 — QuillVille app switcher lists only the public apps

*What & why.* The QuillVille switcher is how a user launches sibling apps. In a
public build it must offer only the three that ship.

**Before you start**
- Public build, QUILL open.

**Do this**
1. Open the **QuillVille menu** (from the menu bar, **Alt** then across to
   **QuillVille**), or run the app switcher command from the Command Palette
   (**Ctrl+Shift+P**, type "QuillVille").
2. Read every entry with your screen reader.

**You should see and hear**
- The list contains **only**: Open QUILL, Quill Radio, Quill Weather. **Cast,
  Studio, Converter, and Beacon are absent** (per the `RELEASED_APPS` allowlist).
  Nothing hints at a hidden app.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## GATE-02 — Media Player is not present

*What & why.* The embedded Media Player (`app.open_media_player`) is gated.

**Before you start**
- Public build, QUILL open.

**Do this**
1. Look under **Tools ▸ Media** (if that submenu exists at all — see GATE-05).
2. In the Command Palette, type **`Media Player`**.

**You should see and hear**
- There is **no Media Player** menu item and **no** command-palette result for it.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## GATE-03 — The standalone Audio Studio launcher is gated (but batch speech stays)

*What & why.* The standalone **Quill Audio Studio** app is gated. Do not confuse it
with the editor-embedded **Audiobook & Batch Speech…** wizard
(`tools.speech_batch_export`), which is a *different* feature that **does** ship
(it was renamed to remove the name clash).

**Before you start**
- Public build, QUILL open.

**Do this**
1. In the QuillVille switcher (GATE-01), confirm no **Studio** launcher.
2. Under **Tools ▸ Speech**, find **Audiobook & Batch Speech…** and confirm it
   **is** present and opens.

**You should see and hear**
- No standalone Audio Studio launcher anywhere; **Audiobook & Batch Speech…** is
  present and works (its full test lives in the speech-tools section).

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## GATE-04 — Cast / Converter / Beacon are unreachable everywhere

*What & why.* These companion apps are gated across every entry point, including the
Windows Explorer shell integration.

**Before you start**
- Public build. Have a document file visible in File Explorer.

**Do this**
1. Confirm no Cast / Converter / Beacon in the QuillVille switcher (GATE-01).
2. In the Command Palette, type **`Cast`**, then **`Converter`**, then **`Beacon`**.
3. In File Explorer, right-click a document and read the context menu.

**You should see and hear**
- No launcher, **no command-palette commands**, and **no "Convert with Quill"**
  (or similar) shell verb in the Explorer menu. None of these apps are installed as
  a build product in a public install.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## GATE-05 — Podcasts, Internet Radio, and Book Library are absent — and the whole Media submenu is gone

*What & why.* All three editor-embedded media features are gated. With every child
gated, the **`Tools ▸ Media` submenu is omitted entirely** — a good single tell.

**Before you start**
- Public build, QUILL open.

**Do this**
1. Open the **Tools** menu and look for a **Media** submenu.
2. In the Command Palette, type each of: **`Podcasts`**, **`Internet Radio`**,
   **`Book Library`**, and the raw prefixes **`podcasts.`**, **`radio.`**,
   **`library.`**.
3. Read the **status bar** end to end (no Radio mini-player, no Podcasts cell).
4. Open the system **tray** icon menu and read it (no radio controls, no Podcasts
   section).
5. Open **Tools ▸ Global Hotkeys** and **Tools ▸ Manage Individual Features** and
   scan for any Podcasts / Radio / Book Library rows.
6. Enter QUILL-key mode (**Ctrl+Shift+Grave**) and press **?** to read the chord
   cheat sheet.

**You should see and hear**
- **No `Tools ▸ Media` submenu at all.** No palette results for any of the three
  (and none for the `podcasts.`/`radio.`/`library.` prefixes). No status-bar cell,
  no tray controls, no Global-Hotkeys entries, no Manage-Individual-Features rows,
  and **no Podcasts/Radio/Book-Library chords** on the cheat sheet. The background
  new-episode check never runs.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## GATE-06 — Other already-gated features stay gated

*What & why.* A grab-bag of experimental/optional features must remain off (or in
their documented default) for 1.0.

**Before you start**
- Public build, QUILL open.

**Do this**
1. In the Command Palette, search for **`Spotify`**, **`GLOW`**, and
   **`BITS Whisperer`** (or `whisperer.`).
2. Note the state of **ADP** (`future.adp_assistant`, currently default ON — a
   product decision for 1.0; record whether it is present).
3. Note the **Publishing** send half (`future.publishing`) — the compose/preview may
   exist but the send step should be gated.

**You should see and hear**
- **Spotify** absent (`future.spotify`); **GLOW** absent (`core.glow`); **BITS
  Whisperer** absent (`core.bw_whisperer`). Third-party Quillins are locked (bundled
  ones still load). Record ADP and Publishing states for the release decision.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## GATE-07 — Dev flag restores everything (proves gating is a live switch)

*What & why.* The gated features are hidden by a flag, not deleted. Flipping the
developer flag must bring them all back — that is what proves the gate works.

**Before you start**
- A build you can relaunch with an environment variable set. Set
  **`QUILL_DEV_BUILD=1`** and launch QUILL. (This is the only scenario in this
  section that is **not** run on a plain public build.)

**Do this**
1. Relaunch with `QUILL_DEV_BUILD=1`.
2. Re-check GATE-01, GATE-02, and GATE-05: the QuillVille switcher, the Media
   Player, and the `Tools ▸ Media` submenu with Podcasts / Internet Radio / Book
   Library.

**You should see and hear**
- With the flag on, the gated apps and the `Tools ▸ Media` submenu **reappear** and
  are reachable. Quitting and relaunching **without** the flag hides them again.
  This confirms 1.0 gating is a runtime switch, and the public build genuinely has
  the flag off.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

### Section sign-off
- Tester:
- Screen reader(s) + version(s):
- Build / commit tested:
- Environment (E1–E6):
- Date:
- Scenarios passed / total: ___ / 7
- Release blockers found (must be zero to ship):
- Result: Pass / Pass-with-notes / Fail
- Notes:
