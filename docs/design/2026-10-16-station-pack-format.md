# The station pack: format, trust and sources

Status: built 2026-10-16 (Jeff's todo P2 #33). The machinery is complete; the
data terms, the production signing secret, the schedule and where packs are
served wait on Jeff (see "Decisions waiting").

This is the design record for the files Quill Radio's **Station Details**
window reads, and for the tool that builds them. The user-facing description
is in the Quill Radio guide ("Station Details: find a station by its call
sign, frequency or slogan") and the requirements are in the Radio PRD,
section 27.

## Why a pack at all

A station's name says little. Searches like "Seahawks", "98.5", "KIRO" or
"public radio Spokane" need what a station says about itself and its official
record: call sign, frequency, slogan, format, city, owner. The approach comes
from Jamal Mazrui's RadioTrail (DbDo, MIT licence), credited here and in the
code: gather those facts once, on the project's side, for everybody. The
alternative, probing every stream and looking up every station from each
listener's computer, would take hours per install, hammer small stations, and
give every listener a slightly different catalog. We port the approach and use
none of his data.

## The three files

| File | What it is |
| --- | --- |
| `station-pack.json.xz` | The pack: canonical JSON (sorted keys, no spaces), UTF-8, xz-compressed (preset 6). |
| `station-pack.json.xz.minisig` | The detached Ed25519 signature over the pack's bytes, in the minisign shape `quill.tools.signing` reads and writes. |
| `station-pack-manifest.json` | A small summary, so a client can tell whether a pack is newer without opening it. |

The same input always produces the same bytes: stations are sorted by key and
the build stamp can be fixed with `--built-at`. Two builds of unchanged data
are therefore identical, which keeps a weekly run from producing a "new" pack
that changes nothing.

### The pack document

```json
{
  "format": "quill-station-pack",
  "version": 1,
  "kind": "full",
  "built_at": "2026-10-16T06:17:00Z",
  "sources": [
    {"id": "community_picks", "title": "QuillVille Community Picks",
     "terms": "...", "attribution": ""}
  ],
  "stations": [
    {"key": "...", "name": "KUOW 94.9", "stream_url": "...",
     "call_sign": "KUOW", "frequency": "94.9 FM",
     "slogan": "...", "description": "...", "genre": "...", "tags": "...",
     "city": "...", "state": "...", "country": "...", "language": "...",
     "owner": "...", "homepage": "...", "summary": "...",
     "attribution": "", "confirmed": "2026-10-01",
     "provenance": {"name": "station_catalog", "description": "community_picks"}}
  ]
}
```

- `key` is the station catalog's canonical key: the source uuid when there is
  one, else the normalized stream URL (`catalog/keys.py`). That is what lets
  the client join a pack record to a station Radio already lists.
- Every fact field is plain text; empty fields are left out.
- `provenance` names, per field, the source that supplied it, so a fact can be
  credited and aged out. `confirmed` is the day its source last confirmed it.
- `attribution` is the credit line a licence requires on that record's text
  (empty for the current sources; required for, say, Wikipedia text).
- Unknown keys are ignored when reading, so a pack can grow fields without a
  version bump. A `version` higher than the build reads is refused.
- `kind` is `full` today. A `delta` kind (changes since the last full pack) is
  reserved and not yet built.

### The manifest

```json
{
  "format": "quill-station-pack", "version": 1, "kind": "full",
  "built_at": "...", "file": "station-pack.json.xz",
  "sha256": "...", "bytes": 964, "stations": 12,
  "sources": ["community_picks"], "signed": true
}
```

The manifest is a convenience, never the trust: the signature covers the
pack's own bytes. A manifest that disagrees with the pack's hash makes the
client refuse the pack.

## Trust

- **Key.** The pack is signed with the project's publisher key, whose public
  half is committed as `quill-pub.key` and bundled with every build (the key
  that already signs Quillins and Community Picks). The build tool refuses any
  other key before signing, because a pack signed with a stranger's key would
  be refused by every listener's app, silently.
- **Secret.** `STATION_PACK_SIGNING_KEY` holds the base64 seed, as a
  repository secret, read from the environment only. It is never written to a
  file in the repository.
- **No key, no signature.** Without the secret the pack is written unsigned and
  any older signature beside it is deleted, so a stale signature can never
  vouch for new bytes. Every build of Quill Radio refuses an unsigned pack.
  `--require-signature` turns the missing key into a build failure instead.
- **Client order.** `pack.open_verified` checks the signature over the file's
  bytes first, then the manifest hash, then decompresses with a 256 MB ceiling,
  then checks the format and version. An untrusted file never reaches the JSON
  parser.
- **All or nothing.** The client replaces its whole fact table inside one
  SQLite transaction, so a refusal or a failure part way leaves the previously
  installed facts exactly as they were.

## Sources

The source interface is `EnrichmentSource` in
`quill/core/radio/enrichment/sources.py`: an `id`, a `title`, the `terms` it is
used under, its `attribution`, and `records()`, which yields `StationFacts`.
Sources are offline: each is handed the files it reads. The builder merges
them in trust order, field by field: a later source only fills what an earlier
one left empty, and a record joins another by key, or by stream URL **and**
name together, never by URL alone (7,135 stream URLs are shared by distinct
stations in Radio Browser).

### Approved sources

| Id | What it reads | Terms |
| --- | --- | --- |
| `community_picks` | `quill/core/data/community_picks.json` (streams only) | The project's own curated data. |
| `station_catalog` | A station catalog generation, as Radio already bundles it in `seed.db.xz` | Only fields the shipped seed already carries; no new facts. |

Call sign and frequency are read out of each station's own name, and only when
certain: a call sign needs a band suffix ("WNYC-FM") or a frequency beside it
("KUOW 94.9"), and words that merely look like one ("KISS FM") are refused. A
near miss stays empty rather than filled in wrong, which is RadioTrail's rule.

The weekly workflow uses `community_picks` only, because building a catalog
generation in CI would mean fetching the directory, which is exactly the kind
of decision that waits on the data terms.

### Pending sources (never read)

Listed in `PENDING_SOURCES` so the gap is visible:

- **Radio Browser, redistributed enriched copy**: its data terms need
  confirming before an enriched copy is redistributed.
- **Wikipedia station articles**: CC BY-SA 4.0; the attribution wording and the
  share-alike obligation for summary text need settling.
- **ICY self-description** (what each stream's headers say): whether probing
  every stream weekly is acceptable, and how often.
- **Station home-page meta description and keywords**: meta tags only, honouring
  robots.txt, if approved.

### Adding a source once its terms are approved

1. Write a class with the `EnrichmentSource` shape in its own module, with tests
   against recorded fixtures (no live network in tests).
2. Record the decision here, under "Approved sources": who approved it, when,
   under which licence, and the credit line it requires (set `attribution`).
3. Add its factory to `APPROVED_SOURCES` and remove it from `PENDING_SOURCES`.
4. A source that fetches needs its entry in `network_egress_audit`, a named
   User-Agent, rate limits, and runs only in the workflow, never on a listener's
   computer.

## The client store

`quill/core/radio/enrichment/store.py`, a SQLite file at
`<machine-local data>/radio-enrichment/stations.db`, separate from the station
catalog. The catalog treats a schema change as "rebuild from seed", and packs
arrive on their own schedule; keeping them apart means neither forces the other
to start over. It is derived data: deleting it loses nothing the listener owns.

- **Tables:** `station_facts` (one row per station, indexed by normalized
  stream URL), `pack_sources`, `pack_meta` (`built_at`, `kind`) and the FTS5
  table `station_facts_fts` over name, identity (call sign and frequency
  tokens), slogan, format, tags, place, description, owner and summary.
- **Migrations:** `MIGRATIONS` is a list of `(user_version, script)` applied
  forward once each, inside a transaction. A store written by a newer build is
  refused and recreated.
- **Search:** bm25 weights 10 (name), 10 (identity), 5 (slogan), 4 (format),
  4 (tags), 3 (place), 2 (description), 2 (owner), 1 (summary). Frequencies are
  indexed as joined tokens (`fm985 freq985`, `am1090 freq1090`) because FTS5
  splits "98.5" at the dot; a query is rewritten the same way, so "98.5",
  "98.5 FM" and "freq985" meet. A home state is an optional tie-break. When the
  index finds nothing, a close-spelling match on names (difflib) runs.
- **Why it matched:** every hit names the first field that matched and its
  value ("matched slogan: Official home of the Seattle Seahawks"), or "close
  spelling of the name" for a fuzzy hit.

## Decisions waiting

1. **The data terms**: which pending sources, if any, are approved, under what
   licence and attribution wording.
2. **The signing secret**: add `STATION_PACK_SIGNING_KEY` (the publisher seed,
   the same as `PICKS_SIGNING_KEY`) to the repository secrets.
3. **The schedule**: weekly on Mondays at 06:17 UTC is the default in the
   workflow; change the cron if another day suits.
4. **Where packs are served** (a release asset, the Pages site) and whether
   release builds bundle one in `quill/data/radio-enrichment/`. Until then the
   workflow keeps each trusted pack as a 90-day workflow artifact only.
5. **Download in the app**: a consent setting (automatic weekly, ask first, or
   off), a "Check for Station Updates" command and an egress-audit entry. Not
   built.
