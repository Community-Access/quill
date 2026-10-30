# Quill Beacon -- not opened from QUILL 1.0

> **Not opened from QUILL 1.0.** Quill Beacon is one of the companion apps
> outside `RELEASED_APPS` (`quill/core/app_launcher.py`), so QUILL 1.0.0 does not
> offer it. Since this note was first written it has moved into this repository
> (`quill/apps/beacon/`, packaged by `standalone/beacon/`) and has an installer
> of its own; its user-facing documents are in `standalone/beacon/docs/`,
> including the 0.1.0 release notes. The paragraphs below record what was
> relocated out of QUILL's public documents, and are kept as history.
>
> QuillBeacon had no chapter in the user guide and no section of its own in the
> PRD -- only passing mentions inside otherwise public prose about the shared
> announcement service and the shared sound events. Those sentences were
> rewritten to drop the mention during the 1.0.0 documentation consolidation, and
> the removed material is preserved here. Nothing was deleted.

**Where each part came from**

| Relocated from | Source section |
|---|---|
| `docs/user guide/userguide.md` | "The four announcement channels" -- the family list |
| `docs/user guide/userguide.md` | "Sound notifications and earcons" -- the Beacon clause |
| `QUILL-PRD.md` | "Shell adoption of the announcement service" -- the `Announcer.say` paragraph |
| `QUILL-PRD.md` | `§35.1 The apps` -- the QUILL Beacon family entry |

---

## Relocated material

### The announcement service reaches Beacon too

_From the user guide's "The four announcement channels" section, which now names
only the publicly released apps._

The same announcement service carries all four channels -- speech, braille,
sound, and status -- in QuillBeacon as well as in QUILL, Quill Radio and Quill
Weather, so an announcement behaves the same wherever you are.

### Beacon's sound events

_From the user guide's "The companion apps have their own voice" bullet under
sound notifications and earcons, which stays public for Quill Radio and Quill
Weather._

Beacon marks an item captured and a sync finishing. Each is a **Sound Event** you
can turn off individually, and each fires on a real change of state.

### PRD: Beacon's adoption of the announcement service

_From the PRD's "Shell adoption of the announcement service (#1298-#1307)"
passage, which stays in the PRD for QUILL itself and the shared `AppShellFrame`._

`Announcer.say` in QuillBeacon keeps its signature (~40 call sites untouched)
while gaining speech, braille and cues -- Beacon previously had **no
screen-reader speech at all**, writing the status bar or the window title, which
no reader announces on its own.

Beacon was also one of the shells covered by the destructive-default gate sweep
recorded in the PRD's trust-and-verification section: 27 pre-existing Yes/No
confirmation sites across QUILL, Radio, Cast, and Beacon were given
`wx.NO_DEFAULT` in the same pass.

### PRD 35.1 The QUILL Beacon family entry

_Moved from `## 35. The QuillVille family` / `### 35.1 The apps`, whose inventory
now lists only the publicly released apps and points here for the gated ones._

- **QUILL Beacon** -- location beacons and QuillSync. Currently an independent
  repo (`quille-beacon`, own SQLite store); converges to `quill/apps/beacon.py`
  on the shared shell once its data-integrity and security fixes land (staged;
  not before its Tier-1 fixes). Not part of the public QUILL 1.0.0 release.

Beacon's convergence is step 6 of the consolidation roadmap that stays in the
PRD (`§35.5`): after Beacon's data-loss and security fixes, fold it into
`quill/apps/beacon.py` on the shared shell, at which point QuillSync becomes the
family handshake (adapter order: Beacon, then radio favorites, then
settings/keymaps).
