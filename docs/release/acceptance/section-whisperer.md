# Section — BITS Whisperer (`whisperer.*`, 12 commands) [GATED]

BITS Whisperer is QUILL's phased speech-to-text management surface: it stages
Whisper speech models, checks the local faster-whisper engine, plans transcription
**providers**, and reports readiness and roadmap. In QUILL 1.0 this whole suite is a
**staging / planning** surface — it lets you download and configure models and
choose providers, but runtime provider *routing* is intentionally still gated
("Phase 2"). Finish **Part 0** first.

Surface reference (label + shortcut) is
`../../planning/signoff/SIGNOFF-editor.md` → `whisperer.*`. Read §2–§3 of `README.md`
for the scenario layout and the Pass/Fail/Blocked/N-A +
Works/Surface-exact/Accessible boxes.

> ## This entire section is GATED behind `core.bw_whisperer`
>
> On a **public QUILL 1.0 build these commands do not exist**: the **Tools ▸ BITS
> Whisperer** submenu is absent and the commands do not appear in the Command
> Palette. If you are testing a public build, mark **every** scenario below **N/A**
> and instead confirm the absence in `gated-absence.md`. Do **not** fail a scenario
> for being missing.
>
> **How the flag is turned on (read before you start).** `core.bw_whisperer` is
> **`locked_off`** — it is off in *every* build, including a developer build
> (`QUILL_DEV_BUILD=1` alone does **not** reveal it). The one sanctioned way to
> enable it is a **signature-verified unlock code**: **Help menu ▸ Redeem Unlock
> Code…** (command `help.redeem_unlock_code`), enter a valid BITS Whisperer unlock
> code, then **restart QUILL** if the menu is not yet visible. Once enabled, the
> **Tools ▸ BITS Whisperer** submenu appears with sub-menus **Watch Folder**,
> **Speech Models**, **Providers**, and **Rollout**. All twelve commands are also
> reachable from the **Command Palette**. This section is written so a dev/admin
> who has redeemed the code can sign every command off.
>
> **No keyboard shortcuts.** None of the twelve `whisperer.*` commands ship a
> default accelerator. Reach each one by its menu path or the Command Palette; the
> "Shortcut" in each title below is therefore "no default shortcut". Fail
> **Surface-exact** only if the menu shows a shortcut this book does not list.

**Where each command lives** (after the flag is on), under **Tools ▸ BITS
Whisperer**:

- **Speech Models ▸** Model Manager… · Model Status · Use Recommended Model ·
  Check faster-whisper Engine · Download Queue…
- **Providers ▸** Provider Center… · Provider Status · Use Recommended Provider ·
  Select Provider…
- **Rollout ▸** Readiness Check · Capability Matrix
- **About BITS Whisperer** is **not** in this submenu (it was folded into the About
  Quill dialog); reach it from the **Command Palette**.

---

## WHIS-01 — Speech Model Manager… (`whisperer.model_manager`, no default shortcut) [GATED core.bw_whisperer]

*What & why.* The guided front door for speech models: pick the recommended model,
browse every model, download or remove one, and set your default — all by keyboard,
with the machine's own capability guidance shown up front.

**Before you start**
- `core.bw_whisperer` enabled (Help ▸ Redeem Unlock Code…; see the section note).
- Any document open.

**Do this**
1. Open **Tools menu (Alt, T) ▸ BITS Whisperer ▸ Speech Models ▸ Model Manager…**,
   or Command Palette → "BITS Whisperer Speech Model Manager".
2. Read the first dialog ("BITS Whisperer Speech Setup"). Arrow to **Choose model
   manually** and press **Enter**.
3. In the model list ("BITS Whisperer Speech Models"), arrow through the entries;
   each shows its family and any `[downloaded]` / `[recommended]` markers. Pick one
   and press **Enter**.
4. In the per-model action dialog, read the size and minimum-RAM detail, arrow to
   **Set as default**, and press **Enter**. (Escape at any step cancels.)

**You should see and hear**
- The first dialog opens with the machine-capability guidance line spoken, then a
  four-item list: **Use recommended model**, **Choose model manually**, **Show model
  status**, **Check faster-whisper engine**. It is a single-choice list navigable by
  arrows.
- The model list announces each model name, family, and markers. The action dialog
  announces the model name, description, **Approx size: N.NN GB**, and **Minimum RAM:
  N GB**, offering **Set as default**, **Download model** (or **Remove downloaded
  model** if already present), and **Show status**.
- Choosing **Set as default** confirms aloud: "Manual mode active. Default speech
  model set to <name>" and updates the status bar. **Download model** first refuses
  with a spoken warning if there is not enough disk space; otherwise it starts a
  background download (see WHIS-05). Nothing happens without your Enter.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## WHIS-02 — Speech Model Status (`whisperer.model_status`, no default shortcut) [GATED core.bw_whisperer]

*What & why.* A read-only snapshot of your speech-model setup: which mode is active,
which model is the default, what's recommended right now, how many models are
installed, and whether the engine is ready.

**Before you start**
- `core.bw_whisperer` enabled.

**Do this**
1. Open **Tools ▸ BITS Whisperer ▸ Speech Models ▸ Model Status**, or Command
   Palette → "BITS Whisperer Speech Model Status".
2. Read the whole dialog with your screen reader's review cursor; press **Enter** or
   **Escape** on OK to close.

**You should see and hear**
- A message dialog titled **BITS Whisperer Speech Models** whose text begins "BITS
  Whisperer Speech Model Status" and lists, in order: the machine-capability
  guidance, **Selection mode:** (recommended/manual), **Configured default:**
  <model>, **Recommended now:** <model>, **Installed models: N of M**, and
  **faster-whisper engine: Ready / Not installed** with an engine detail line. It
  ends with a note that this is a phased rollout.
- Closing returns focus to where you were. Status bar: "BITS Whisperer speech model
  status shown".

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## WHIS-03 — Use Recommended Speech Model (`whisperer.model_recommend`, no default shortcut) [GATED core.bw_whisperer]

*What & why.* One-tap "just pick the best model for this machine." Switches you to
recommended mode and selects the model QUILL recommends for your hardware.

**Before you start**
- `core.bw_whisperer` enabled. Optionally set a manual default first (WHIS-01) so the
  switch back to recommended is observable.

**Do this**
1. Open **Tools ▸ BITS Whisperer ▸ Speech Models ▸ Use Recommended Model**, or
   Command Palette → "BITS Whisperer Use Recommended Speech Model".

**You should see and hear**
- No dialog. The selection mode flips to **recommended** and the default model is set
  to the recommended id; the change is saved. Spoken/status: "Recommended mode
  active. Selected speech model: <model id>". Re-running WHIS-02 now shows
  **Selection mode: recommended** and the configured default equal to the
  recommended model.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## WHIS-04 — Check faster-whisper Engine (`whisperer.check_faster_whisper`, no default shortcut) [GATED core.bw_whisperer]

*What & why.* Tells you whether the local **faster-whisper** transcription engine is
installed and usable, so you know before you rely on offline speech.

**Before you start**
- `core.bw_whisperer` enabled.

**Do this**
1. Open **Tools ▸ BITS Whisperer ▸ Speech Models ▸ Check faster-whisper Engine**, or
   Command Palette → "BITS Whisperer Check faster-whisper Engine".
2. Read the dialog; close with OK.

**You should see and hear**
- A message dialog titled **faster-whisper Engine** containing a plain status detail
  line. When the engine is present it uses an information icon and the status bar
  says "faster-whisper engine ready"; when absent it uses a **warning** icon and the
  status bar says "faster-whisper not installed" — never a silent result and never a
  crash when the engine is missing.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## WHIS-05 — Download Queue… (`whisperer.download_queue`, no default shortcut) [GATED core.bw_whisperer]

*What & why.* Manage in-flight and past model downloads: jump to the live status
page, retry a failed download, or clear finished history. Model downloads are
user-initiated and covered by the network egress audit.

**Before you start**
- `core.bw_whisperer` enabled. To exercise **Retry**, first trigger a download that
  fails (e.g. start a model download from WHIS-01 with the network off), so a failed
  entry exists.
- Note: if the **Safe Mode Lock** badge is showing in the Speech Models menu,
  downloads and retries are intentionally blocked (see the projected outcome).

**Do this**
1. Open **Tools ▸ BITS Whisperer ▸ Speech Models ▸ Download Queue…**, or Command
   Palette → "BITS Whisperer Download Queue".
2. In the "BITS Whisperer Download Queue" list, arrow through **Open live status
   page**, **Retry failed download**, **Clear completed and failed download
   history**. Choose **Open live status page** and press **Enter**.
3. Repeat and choose **Retry failed download**; in the follow-up list pick a failed
   model and press **Enter**.
4. Repeat and choose **Clear completed and failed download history**.

**You should see and hear**
- The three-item action list is arrow-navigable. **Open live status page** opens the
  Help ▸ Status Page (live download/speech status). **Retry failed download** opens a
  second list of failed models and restarts the chosen one as a background download;
  if there are none it says "No failed BITS Whisperer downloads to retry". **Clear…**
  removes completed/failed entries (keeping any still running) and says "Cleared
  completed and failed BITS Whisperer download history".
- If the **safe mode lock** is enabled, Retry is refused with a spoken message
  pointing you to **Preferences ▸ General**, and status "BITS Whisperer safe mode
  lock blocked download retry" — it does not silently do nothing.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## WHIS-06 — Provider Center… (`whisperer.provider_center`, no default shortcut) [GATED core.bw_whisperer]

*What & why.* A guided hub for transcription **providers** (the local or cloud
service that would do the speech-to-text): pick the recommended one, choose manually,
see status, switch local-first / cloud-first, or toggle whether cloud providers are
even visible.

**Before you start**
- `core.bw_whisperer` enabled.

**Do this**
1. Open **Tools ▸ BITS Whisperer ▸ Providers ▸ Provider Center…**, or Command
   Palette → "BITS Whisperer Provider Center".
2. Arrow through the six actions: **Use recommended provider**, **Select provider
   manually**, **Show provider status**, **Switch to local-first mode**, **Switch to
   cloud-first mode**, **Toggle cloud provider visibility**. Pick **Switch to
   local-first mode** and press **Enter**.
3. Re-open and try **Toggle cloud provider visibility**.

**You should see and hear**
- A single-choice dialog titled **BITS Whisperer Provider Center** with the six
  actions, arrow-navigable. Each action either delegates (recommended → WHIS-08,
  manual → WHIS-09, status → WHIS-07) or applies and announces a setting:
  "Provider mode set to local-first" / "…cloud-first", and "Cloud provider visibility
  enabled/disabled". Each choice is saved. Escape cancels with no change.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## WHIS-07 — Provider Status (`whisperer.provider_status`, no default shortcut) [GATED core.bw_whisperer]

*What & why.* A read-only readout of the provider plan: current mode, which provider
is configured vs recommended, whether it is ready, and the concrete next steps to
make it ready.

**Before you start**
- `core.bw_whisperer` enabled.

**Do this**
1. Open **Tools ▸ BITS Whisperer ▸ Providers ▸ Provider Status**, or Command Palette
   → "BITS Whisperer Provider Status".
2. Read the whole dialog; close with OK.

**You should see and hear**
- A message dialog titled **BITS Whisperer Providers** beginning "BITS Whisperer
  Provider Status" and listing: mode guidance, **Provider mode: Local-first /
  Cloud-first**, **Cloud providers visible: Yes/No**, **Configured provider:** and
  **Recommended provider:** by name, a **Readiness: Ready / Needs setup** line with a
  summary, and a bulleted **Next steps:** list. It ends noting that runtime provider
  routing remains gated in this phase. Status bar: "BITS Whisperer provider status
  shown".

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## WHIS-08 — Use Recommended Provider (`whisperer.provider_recommend`, no default shortcut) [GATED core.bw_whisperer]

*What & why.* One-tap "pick the best provider for me," honoring your local-first /
cloud-first preference.

**Before you start**
- `core.bw_whisperer` enabled.

**Do this**
1. Open **Tools ▸ BITS Whisperer ▸ Providers ▸ Use Recommended Provider**, or
   Command Palette → "BITS Whisperer Use Recommended Provider".

**You should see and hear**
- No dialog. The recommended provider (computed from your local-first/cloud-first
  mode) is selected and saved; spoken/status: "Recommended provider selected:
  <provider name>". Re-running WHIS-07 shows that provider as the configured one.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## WHIS-09 — Select Provider… (`whisperer.provider_select`, no default shortcut) [GATED core.bw_whisperer]

*What & why.* Manually choose which provider to stage for upcoming phases, from the
providers currently visible (local only, or local + cloud, per your visibility
setting).

**Before you start**
- `core.bw_whisperer` enabled. If you want cloud options to appear, enable cloud
  provider visibility first (WHIS-06 ▸ Toggle cloud provider visibility).

**Do this**
1. Open **Tools ▸ BITS Whisperer ▸ Providers ▸ Select Provider…**, or Command
   Palette → "BITS Whisperer Select Provider".
2. Arrow the provider list; each entry shows the provider name and its type. Pick one
   and press **Enter**.

**You should see and hear**
- A single-choice dialog titled **BITS Whisperer Provider Selection** listing each
  provider as "<name> (<type>)". On confirm the choice is saved and spoken/status:
  "Selected provider: <name>". If no providers are visible for the current
  visibility settings, it says so ("No providers available for current provider
  visibility settings") instead of opening an empty dialog. Escape cancels with no
  change.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## WHIS-10 — Readiness Check (`whisperer.readiness_check`, no default shortcut) [GATED core.bw_whisperer]

*What & why.* One combined diagnostic across providers **and** speech models: mode,
configured vs recommended provider, provider readiness, speech mode and model, safe
mode lock, installed model count, engine state, and next steps.

**Before you start**
- `core.bw_whisperer` enabled.

**Do this**
1. Open **Tools ▸ BITS Whisperer ▸ Rollout ▸ Readiness Check**, or Command Palette →
   "BITS Whisperer Readiness Check".
2. Read the whole dialog; close with OK.

**You should see and hear**
- A message dialog titled **BITS Whisperer Readiness** beginning "BITS Whisperer
  Readiness Check" and listing, in order: machine guidance, **Provider mode**,
  **Configured provider**, **Recommended provider**, **Provider readiness: Ready /
  Needs setup** with summary, **Speech mode**, **Configured speech model**, **Safe
  mode lock: Enabled/Disabled**, **Downloaded whisper models: N of M**,
  **faster-whisper engine: Ready / Not installed** with detail, then a bulleted
  **Next steps:** list. Status bar: "BITS Whisperer readiness check complete".

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## WHIS-11 — Capability Matrix (`whisperer.capability_matrix`, no default shortcut) [GATED core.bw_whisperer]

*What & why.* A table of which BITS Whisperer capabilities are live now vs gated for
a later phase, so a tester can see at a glance what is expected to work in 1.0.

**Before you start**
- `core.bw_whisperer` enabled.

**Do this**
1. Open **Tools ▸ BITS Whisperer ▸ Rollout ▸ Capability Matrix**, or Command Palette
   → "BITS Whisperer Capability Matrix".
2. Tab to the table and arrow through its rows; then read the snapshot text below it.
   Close with **Close** (OK) or **Escape**.

**You should see and hear**
- A resizable dialog titled **BITS Whisperer Capability Matrix** with a real
  ListCtrl (report view) whose columns are **Capability**, **Phase**, **Status**,
  **Notes**. Rows include **Whisper model acquisition** (Phase 1), **Provider
  onboarding** (Phase 1), **Dynamic status monitoring** (Phase 1, Ready), and
  **Runtime provider routing** (Phase 2, **Gated**). Below the table a read-only
  snapshot shows provider mode, configured provider, speech-model mode, configured
  speech model, and downloaded-model count. Focus lands in the table; every column is
  announced by the screen reader. Status bar: "Opened BITS Whisperer capability
  matrix".

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## WHIS-12 — About BITS Whisperer (`whisperer.about`, no default shortcut) [GATED core.bw_whisperer]

*What & why.* The roadmap/orientation page: what BITS Whisperer is, the phased plan
for absorbing its patterns into QUILL, and the guiding principles. It is **not** in
the BITS Whisperer submenu — it lives in the Command Palette (its content was also
folded into the About Quill dialog).

**Before you start**
- `core.bw_whisperer` enabled.

**Do this**
1. Open the **Command Palette** (see Part 0 for its shortcut), type **About BITS
   Whisperer**, and press **Enter**.
2. Tab across the three tabs (**Overview**, **Roadmap**, **Principles**); read the
   Roadmap and Principles tables with your review cursor. Close with **Close** (OK)
   or **Escape**.

**You should see and hear**
- A resizable tabbed dialog titled **About BITS Whisperer** with a notebook named
  "About sections" and three tabs. **Overview** is a read-only multi-line text
  describing the phased plan and three next steps. **Roadmap** is a ListCtrl with
  columns **Capability**, **Whisperer Source**, **Phase**, **Quill Plan** (five
  rows across Phases 1–3). **Principles** is a ListCtrl with columns **Principle**,
  **How it applies** (Accessibility first, Offline-friendly, Safe rollout,
  Transparent status). Focus lands on the first control of the visible tab, not the
  tab strip; tab order and the Close button honor the keyboard contract. Status bar:
  "Opened About BITS Whisperer".

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

### Section sign-off
- Tester:
- Screen reader(s) + version(s):
- Build / commit tested:
- Environment (E1–E6):
- Date:
- Scenarios passed / total: ___ / 12
- Release blockers found (must be zero to ship):
- Result: Pass / Pass-with-notes / Fail
- Notes:
