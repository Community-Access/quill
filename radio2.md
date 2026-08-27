# radio2.md — StreamTuner, read and mined, and what Quill Radio should build from it

Research notes and an implementation plan. Started 2026-08-26. **Reading and
probing only — no code was changed, nothing was installed.**

The ask: read [StreamTuner-ng](https://github.com/IronWolve/StreamTuner-ng) and
the older [StreamTuner2](https://github.com/leigh123linux/streamtuner2), work out
what Quill Radio can learn or use, and write the plan.

Both repositories were read where it matters: StreamTuner-ng's `PLUGINS.md`, its
plugin contract (`plugins/base.py`, `host.py`, `loader.py`, `result.py`), its
HTTP layer, its icon cache, its config/cache store, and every channel plugin;
StreamTuner2's `channels/shoutcast.py`, `channels/tunein.py`,
`channels/__init__.py`, `action.py` and `ahttp.py`. Then Quill Radio's own
directory stack was read against them — `browse_sources.py`, `browse_nodes.py`,
`directory_cache.py`, `browse_failure.py`, `models.py`, `xiph.py`, `iheart.py`,
`live365.py`, `my_servers.py`, `station_status.py`, `icy.py`, `networks.py`,
`playlist_formats.py`, `tunein.py`, `search_sources.py`, `directory_search.py`,
`station_confidence.py` — so that every recommendation below lands on a named
function rather than on a wish.

Finally, **every interesting claim was tested against the live services**. A
directory integration that worked in 2014 is worth nothing; one that answers
today is worth a fortnight. Appendix A has the requests and the results.

**The verdict:** two of these are sizeable capabilities Quill Radio does not
have and can ship almost entirely with machinery it already owns; three more are
small, high-quality wins; two are architecture worth borrowing; and a fair
amount of what StreamTuner does, Quill Radio already does better.

---

## Status: what shipped, 2026-08-26

Every part of this plan (I-IX) is now **implemented, tested and documented** in the
working tree. What follows is the record of what landed, so this file can be
read as a report rather than as a proposal.

| Item | Status | Where it lives |
| --- | --- | --- |
| 1. SHOUTcast directory + Top 500 | **Shipped** | `quill/core/radio/shoutcast.py` (363 lines), browse ids `shoutcast`, `shoutcast:<genre>`, `shoutcasttop` |
| 2. Live365 from the public sitemap | **Shipped** | the directory half of `quill/core/radio/live365.py`, ids `live365`, `live365:<letter>` |
| 3. Live listeners as a first-class field | **Shipped** | `RadioStation.listeners` (transient, `compare=False`), read in `details_text`, sorted on by SHOUTcast |
| 4. Radio Paradise, every channel × every quality | **Shipped** | `quill/core/radio/radio_paradise.py` (302 lines), id `radioparadise` |
| 5. Per-source health with a failure count | **Shipped**, without the auto-disable | `quill/core/radio/source_health.py`, `browse_sources.repeat_failure_note`, `browse_feedback.empty_row_text(note=…)` |
| 6. Bounded fetch budget in the federated paths | **Shipped**, in both shapes | The fan-out is bounded by wall-clock (`federated_browse.SEARCH_DEADLINE_SECONDS`, stragglers named); the crawl is bounded by request count exactly as StreamTuner does it (`browse_find.FIND_MAX_FETCHES` + depth + result caps, with the honest `capped` flag) |
| 7. Tokenized locators for keyed sources | **Shipped and load-bearing** | Quillin browse rows may carry a `key` instead of a URL and resolve only at play time (`extdirstation`), so an expiring or tokenized address never lands in favourites or exports; `SecretOption` carries the credential shape for the first keyed built-in |
| 8. Source-declared options | **Shipped** (2026-08-26, without waiting for 9) | `quill/core/radio/source_options.py` declarations + `quill/ui/radio/source_options_menu.py` rendering; Radio Paradise quality and SHOUTcast live-only are the first two |
| 9. Quillin-contributed browse sources | **Shipped** (2026-08-27) | The browse trio on `directory_providers` (schema+validation+app_host+registry), the Quillin Sources branch, one row validator, play-time resolve for keyed rows; the bundled sample demonstrates it. The declared-egress half already existed as `net_allowed_hosts` |
| 10. Playlist long tail + disagreement report | **Shipped** | `playlist_formats.parse_shortcut/parse_b4s/parse_wpl`, `disagreements()` |

### Six faults found by running it, the same day

0. **A SHOUTcast station is a playlist, not a stream.** The single most
   important thing this plan got wrong: it recorded that the tune-in `.pls`
   "needs no resolve step" because mpv can read a playlist. Most stations
   therefore did not play. Rows are now resolved on activation, exactly as
   TuneIn's are; search resolves its top rows up front because it has no second
   chance. Verified against the station that was reported.


Jeff ran the build within the hour, and every one of these is something no test
here would have caught. They are recorded in full in `fixes.md`; in short:

1. **A new source reaches nobody who has ever opened the chooser.** A stored
   selection cannot name a source added later. Browse sources had the fix
   (`INTRODUCED_BY_EPOCH`); it needed an entry. **Search sources had the same
   hole and no fix at all** -- now they have both. *This is the item to copy
   forward: any future source needs its epoch entry in the same change, or it
   ships to nobody.*
2. **Writing a setting is half the change.** An open Browse Stations window kept
   the roots it was built with. `apply_visible_sources` closes that seam.
3. **`ACB Media 1, 10, 2`.** `natural_order.py`, applied to every list of names
   a person reads -- and no name zero-padded to make it sort.
4. **One SHOUTcast root, not two.** The Top 500 is a pinned folder inside the
   directory branch.
5. **Search All Sources was slow and silent.** One wave instead of three, a
   twelve-second deadline with the stragglers *named*, and a repeating progress
   notice.

**Search as well as browse.** All three new sources are also Find Stations
sources (`search_sources.SEARCH_SOURCES`), each behind its own toggle, so a
listener who turns one off stops its requests happening rather than having its
results filtered away afterwards.

### Decisions taken during implementation that this plan did not anticipate

- **No browser User-Agent, confirmed twice.** The plan flagged it as a possible
  policy exception; the probe settled it, and the shipped code sends QUILL's
  ordinary descriptive UA to SHOUTcast like every other source.
- **`shoutcasttop` is a root branch, not a child of `shoutcast`.** "What is most
  listened to right now" is a destination, not a subfolder, and burying it one
  level down would have cost the one keystroke that makes it worth having.
- **The SHOUTcast genre sort lives in the parser, not the UI.** `parse_stations`
  returns rows sorted by live listeners. That is testable without a window, it
  needs no per-source branch in the tree dialog, and it delivers the whole value
  of part III.4 without the declarative-sort machinery that idea came wrapped in.
- **Live365 browses by letter.** 5,493 rows in one node is not a list anybody
  can work with by ear; both levels read the same day-old cache, so a letter
  costs no request.
- **`source_health` never disables anything.** StreamTuner-ng trips a plugin off
  after three strikes. Here the count changes what is *said* and never what is
  done -- a source that vanished from the tree would be a worse failure than the
  outage it was hiding -- and the record is in-process only, so a restart starts
  clean and no settings file can be corrupted by it.
- **`playlist_formats` still has no runtime caller.** That was true before this
  change and is unchanged by it: the module is a tested toolkit that nothing in
  the app imports yet. The long-tail parsers and `disagreements()` are ready for
  Add Custom Station and the bad-station report to use; wiring them is a
  behaviour change to the paste-a-URL path and is the obvious next step, not
  part of this one.

### What was deliberately left

- **No "All Stations" branch for SHOUTcast** (part V's reasoning): the directory
  has no such endpoint and synthesising one costs 313 requests behind a node
  that looks like every other node.
- **No fetch-budget plumbing in `federated_browse` / `federated_search`** (part
  V): worth doing, touches the fan-out both apps share, and nothing shipped here
  depends on it.
- **No "Live now" filter in the tree** (part III.5): the sources' own ordering
  delivers most of the value; a filter is a new control, a new keystroke and a
  menu accelerator, which is a plan rather than a patch.
- **Parts VII-VIII** in full: they change the Quillin provider interface.

### Gates run

`pytest tests/unit/core/radio` (1,298 + 47 new, green), the egress audit,
GATE-11 module budgets (three rebaselines, each with its note), the error-code
audit, `ruff check`, `ruff format`, and `mypy` over the four changed core
modules.

---

## Executive summary

| # | What | New to Quill Radio? | Value | Size |
| --- | --- | --- | --- | --- |
| 1 | **SHOUTcast directory** — 60k+ stations, keyless, **true live listener counts**, Top 500, 313 genres | **Entirely new** | High | ~300-line core module + ~10 lines of wiring |
| 2 | **Live365 full directory from the public sitemap** — 5,493 stations | **New** (the URL rewriter exists; the directory does not) | High | ~150-line addition to an existing module |
| 3 | **Live listeners as a first-class, sortable, spoken dimension** | New (votes ≠ listeners) | High | Model field + 3 call sites |
| 4 | **Radio Paradise as a real source** — every channel × every quality, incl. FLAC | Upgrade (today it is a Radio Browser name query) | Medium-high | ~120-line core module |
| 5 | **Per-source health with a crash budget** | Half-new (failure is recorded; the *source* is not scored) | Medium-high | ~150 lines + dialog column |
| 6 | **A bounded fetch budget per user action** | New as an explicit discipline | Medium | ~40 lines, reused |
| 7 | **Tokenized locators so a credential never enters a row** | New | Medium (safety) | A rule + one hook |
| 8 | **Source-declared options rendered by the host** | New | Medium | Depends on #9 |
| 9 | **Quillin-contributed *browse* sources** (their plugin model, made safe) | New — providers are search-only and network-free today | High, strategic | Its own project |
| 10 | StreamTuner2's playlist probing + assorted hardening | Mostly known | Low-medium | Small each |

Everything in parts I-VI below is independently shippable and independently
revertible. Parts VII-IX are proposals that change an interface and should not
be smuggled in behind a source addition.

---

# Part I — The two directories

## 1. SHOUTcast

### Why this is the real gap

Quill Radio knows what a SHOUTcast *server* is: `my_servers.py` parses v2
`/stat` and v1 `/7.html`, `station_status.py` reads `/stats?json=1` for
what's-playing, `icy.py` reads stream titles. What it has never had is
SHOUTcast's **directory** — the ~60,000-station index at
`directory.shoutcast.com`. There is no `shoutcast` node in `browse_sources.py`'s
grammar and no SHOUTcast entry in `search_sources.py`.

StreamTuner2 wrote in 2014 that the Winamp "yellow pages" API had been
deprecated after the Radionomy acquisition, that nobody would answer whether an
open-source desktop app could have an auth hash, and that the website's own AJAX
interface returned JSON anyway. StreamTuner-ng, a decade and another change of
ownership later, calls **the same endpoints**. That is about as strong a
stability signal as an undocumented endpoint can give.

### The protocol, as verified today

All of it is keyless. All of it answered on 2026-08-26 (Appendix A).

```
POST https://directory.shoutcast.com/Home/BrowseByGenre
     Content-Type: application/x-www-form-urlencoded
     genrename=<genre>
  -> 200, JSON array, EXACTLY 500 rows (a per-genre cap, not the whole genre)

POST https://directory.shoutcast.com/Home/Top          (empty body)
  -> 200, JSON array, 500 rows, ALL with Listeners > 0, max 8,281 when probed
     This is the live-listener leaderboard: "what the world is listening to
     right now", and there is nothing like it anywhere else in the browse tree.

POST https://directory.shoutcast.com/Search/UpdateSearch
     query=<text>
  -> 200, JSON array, same row shape

GET  https://directory.shoutcast.com/Genre
  -> 302 to /Search, and the landing page still carries 313 distinct
     href="/Genre?name=<urlencoded>" links. Follow the redirect.

GET  https://yp.shoutcast.com/sbin/tunein-station.pls?id=<ID>
  -> 200, a [playlist] with File1=<real stream URL>
```

The row shape, taken from a live response rather than from either repository:

```json
{"ID": 99623166, "Name": "[EN] HUBU.FM | MUSIC RADIO STATION | AD FREE",
 "Format": "audio/mpeg", "Bitrate": 128, "Genre": "Misc",
 "CurrentTrack": "02:48 - Hubu.FM Live", "Listeners": 8281,
 "IsRadionomy": false, "IceUrl": "", "StreamUrl": null,
 "AACEnabled": 0, "IsPlaying": false, "IsAACEnabled": false}
```

Five facts from the probe that change the design, none of which are in either
repository's code:

1. **A genre page is capped at 500 rows.** It is a slice, not the genre. Say so
   in the node label rather than implying completeness.
2. **`Listeners` is sparse on genre pages and universal on Top.** In the Jazz
   page, **39 of 500** rows had any listeners at all. On `/Home/Top`, all 500
   did. So the listener count is both the most valuable field here and the one
   that separates a live station from a parked mount — see Part III.
3. **`StreamUrl` is always `null` and `IceUrl` is nearly always empty** (5 of
   500). The tune-in `.pls` is the only reliable route to audio. Do not build a
   fallback on either field.
4. **Names collide, IDs do not.** 25 duplicate names in one genre page, 500
   unique IDs. Dedupe on `ID`.
5. **The response is UTF-8 and will break a locale-default decode.** Reading
   `/Home/Top` with Python's default Windows codec raised
   `UnicodeDecodeError: 'charmap' codec can't decode byte 0x8d`. Quill Radio's
   `_fetch` pattern already does `payload.decode("utf-8", errors="replace")`,
   which is correct — keep it, and add a test with a non-ASCII station name.

### The User-Agent question, settled by measurement

StreamTuner-ng's plugin sends a spoofed Chrome UA plus `Referer` and
`X-Requested-With`, commenting that a plain UA gets a 405. **That is not true
today.** `BrowseByGenre` answered 200 with a plain, honest
`QuillRadio/3.0 (+https://quillville.org)` User-Agent, no `Referer` and no
`X-Requested-With` — and the response was **byte-identical in size** (115,921)
to the browser-UA one.

This matters because every existing Quill Radio source sends a descriptive UA
(`iheart.py`, `xiph.py`, `gutendex.py`, `internet_archive.py`, `m3u_catalog.py`
all call a `_user_agent()`), and adopting SHOUTcast would otherwise have meant
either breaking that policy or arguing for an exception. Neither is needed. If
the endpoint ever starts refusing an honest UA, that is a decision to bring back
to Jeff, not a thing to quietly work around.

### Module design — `quill/core/radio/shoutcast.py`

New, wx-free, strict-typed, ~300 lines (well under the 600-line default budget).
Modelled directly on `xiph.py`, which is the closest existing shape: a keyless
public directory, a genre index, a station list per genre, cached.

```python
"""SHOUTcast's public directory (directory.shoutcast.com): browse ~60,000
stations by genre, by live listeners, or by search. Keyless.

The Winamp yellow-pages API was retired after the 2014 Radionomy acquisition and
no key has been obtainable since; the directory's own site calls a small set of
form-POST endpoints that answer JSON, and those are what this reads...  One
HTTPS request per action to a single reviewed egress site (:func:`_request`),
HTTPS-only over a verified TLS context with a bounded timeout and size cap,
disabled in Safe Mode via :func:`refuse_in_safe_mode`. wx-free, strict-typed.
"""

class ShoutcastError(CodedError):
    """A SHOUTcast directory request failed (network, or Safe Mode refusal)."""
    code = "QUILL-RADIO-SHOUTCAST-REQUEST"      # GATE-EC: unique, declared here

def refuse_in_safe_mode(safe_mode: bool) -> None: ...

# --- pure parsers (unit-testable with no network) --------------------------
def parse_stations(payload: str) -> list[RadioStation]: ...
def parse_genres(html: str) -> list[str]: ...

# --- the shared genre protocol (see browse_sources._GENRE_MODULES) ---------
def fetch_genres(*, safe_mode: bool = False, refresh: bool = False) -> list[str]: ...
def genre_display(name: str) -> str: ...
def fetch_genre_stations(genre: str, *, safe_mode: bool = False) -> list[RadioStation]: ...

# --- this source's own two extras ------------------------------------------
def top_stations(*, safe_mode: bool = False) -> list[RadioStation]: ...
def search_stations(query: str, *, safe_mode: bool = False) -> list[RadioStation]: ...

CATEGORY_LABEL = "SHOUTcast"
CATALOG_CREDIT = "the SHOUTcast directory, most-listened first"
```

**The one piece of genuinely new plumbing** is that every existing source is a
GET and these are form POSTs. `xiph._fetch` is the template; the delta is three
lines:

```python
def _request(url: str, fields: dict[str, str] | None = None) -> str:
    """One HTTPS request to the SHOUTcast directory -- the reviewed egress site.

    A POST when *fields* is given (the directory's browse/search endpoints are
    form posts), otherwise a GET. Reads one byte past the cap so an over-long
    reply is DETECTED rather than handed to a tolerant parser as a truncated
    document -- the failure mode xiph.py already paid for.
    """
    if not url.startswith("https://"):
        raise ShoutcastError("Only https:// URLs can be fetched.")
    data = urllib.parse.urlencode(fields or {}).encode("ascii") if fields is not None else None
    headers = {"User-Agent": _user_agent(), "Accept": "application/json, */*"}
    if data is not None:
        headers["Content-Type"] = "application/x-www-form-urlencoded"
    request = urllib.request.Request(url, data=data, headers=headers)
    context = ssl.create_default_context()
    try:
        with urllib.request.urlopen(request, timeout=_TIMEOUT_SECONDS, context=context) as resp:
            payload: bytes = resp.read(_MAX_BYTES + 1)
    except (urllib.error.URLError, TimeoutError, ssl.SSLError, OSError) as error:
        raise ShoutcastError(f"Could not reach the SHOUTcast directory: {error}") from error
    if len(payload) > _MAX_BYTES:
        raise ShoutcastError(...)
    return payload.decode("utf-8", errors="replace")
```

Size caps from the measurements: a genre page is ~116 KB and Top is ~133 KB, so
`_MAX_BYTES = 2_000_000` is roomy; the genre landing page is ~101 KB.

**Row mapping**, with two hazards worth naming:

| SHOUTcast | `RadioStation` | Note |
| --- | --- | --- |
| `Name` | `name` | Left verbatim. These are shouty (`[EN] … \| … \| AD FREE`) but a broadcaster's name is theirs; tidying it would make the station unfindable by the name its listeners know. |
| `ID` | — | Used for the tune-in URL and for dedupe. **Not** `station_uuid`. |
| — | `stream_url` | `https://yp.shoutcast.com/sbin/tunein-station.pls?id=<ID>` — a `.pls`, which `playlist_formats.parse_pls` already reads and mpv plays directly. No resolve step. |
| `Genre` | `tags=(genre,)` | |
| `Bitrate` | `bitrate_kbps` | 128 in 487 of 500 Jazz rows. |
| `Format` | `codec` | `audio/mpeg` → `MP3`, `audio/aacp` → `AAC+`. |
| `Listeners` | **`listeners`** | New field — Part III. |
| `CurrentTrack` | `notes` (transient) | Already the "describes a row, does not identify it" field, `compare=False`. Do **not** put it in `name`. |
| — | `source="SHOUTcast"` | Drives the Find Stations badge and the Source facet. |
| — | `station_uuid=""` | **Hazard.** `radio_browser.register_click(station_uuid)` POSTs that value to Radio Browser's click endpoint. A foreign id in that field would be sent to another directory. Leave it empty; favourites de-duplicate on `stream_url`. |

**Caching.** Via `directory_cache.resolve`, which already implements
fresh → live → stale with the age surfaced:

| Key | Contents | `max_age_seconds` | Why |
| --- | --- | --- | --- |
| `shoutcast:genres` | the 313 genre names | 7 days | Changes about never; it is a scrape, so a stale list beats a broken page. |
| `shoutcast:top` | Top 500 | 5 minutes | It is a *live* leaderboard; caching it for hours would misrepresent it. Better: do not cache at all, and let a failure fall back to nothing rather than to a stale "right now". |
| `shoutcast:genre:<name>` | one genre page | 1 hour | Bounded and cheap to refetch on Refresh. |

Search is never cached. A search is a fresh question every time — the rule
`directory_cache`'s own docstring opens with.

### Wiring — the exact edits

`browse_sources.py` is the registry every source answers through, and it sits at
**894 lines against a tracked budget of 908** -- fourteen lines of headroom --
with a recorded decomposition point at ~1000. The thin-wiring pattern documented in the budget file
(`_rebaseline_2026_08_16_audiopub`: "one root tuple, two dispatch lines, one
id-scheme docstring line, two import lines") is what this must follow.

1. **Node grammar**, in the module docstring:
   ```
   shoutcast | shoutcast:<genre>   SHOUTcast directory, by genre
   shoutcasttop                    ...its live Top 500
   ```
2. **`ROOT_SOURCES`**: `("shoutcast", "SHOUTcast Directory")` and
   `("shoutcasttop", "SHOUTcast Top 500 (live)")`. Two roots rather than one
   nested node, because "what is most listened to right now" is a destination,
   not a subfolder.
3. **`_GENRE_MODULES`**: add `"shoutcast": shoutcast`. That single dict entry
   buys the entire genre browse — `_browse_genre_source` already renders
   `fetch_genres` as folders and `fetch_genre_stations` as leaves. This is why
   the module must expose exactly `fetch_genres` / `genre_display` /
   `fetch_genre_stations` and not some prettier local shape.
4. **`_FLAT`**: `"shoutcasttop": lambda safe: shoutcast.top_stations(safe_mode=safe)`.
5. **Not** in `LOCAL_SOURCES` — it is entirely network.
6. **Search**: a `SearchSource("shoutcast", "SHOUTcast", "The SHOUTcast
   directory's own station index.")` in `search_sources.py`, and a
   `shoutcast_search_stations(query, *, safe_mode=False)` in
   `directory_search.py` beside `tunein_search_stations` and
   `iheart_search_stations`, following their exact shape (catch the source's own
   error type, return `[]`, never raise into the fan-out). Because a source that
   is off is never contacted, this also means the egress follows the toggle.
7. **Egress**: one entry in `quill/tools/network_egress_entries_radio.py` keyed
   `"core/radio/shoutcast.py::_request"`. The entry *is* the review, so it says
   what is sent (a genre name or a search string, nothing else — no account, no
   identifier), what comes back, what triggers it (an explicit browse, search or
   refresh), and that Safe Mode refuses it. Then a
   `_rebaseline_<date>_shoutcast_egress` line in `module_size_budgets.json`,
   exactly as the m3u/xiph and iheart/tunein entries did before it.
8. **Menus**: nothing new is needed — the source appears in the browse tree. If
   a menu item is ever added, the accelerator rule applies (every enabled item
   shows a keyboard route, no duplicate keys, `self._menu_label(...)`).

### Tests — `tests/unit/core/radio/test_shoutcast.py`

The parsers are pure, which is the point of splitting them out:

- `parse_stations` over a captured 500-row fixture: 500 rows, unique IDs, the
  duplicate-name case survives, `listeners` populated, `codec` mapped,
  `stream_url` is the tune-in `.pls`, `station_uuid` is `""`.
- `parse_stations` over `[]`, over `{}`, over `"not json"`, over a row missing
  `ID` — every one yields `[]` or skips the row, never raises.
- **A non-ASCII station name round-trips** (the `charmap` failure above).
- `parse_genres` over a captured genre page: 313 names, URL-decoded (`Hip%20Hop`
  → `Hip Hop`), sorted, with the junk names filtered the way `xiph._NOT_A_GENRE`
  does.
- `refuse_in_safe_mode(True)` raises `ShoutcastError`; every public entry point
  calls it first.
- Genre-page cap: a fixture of exactly 500 asserts the "this is a slice" label.
- In `test_browse_sources.py`: `browse("shoutcast")` returns folders,
  `browse("shoutcast:Jazz")` returns leaves, `browse("shoutcasttop")` returns
  leaves, and a raising client leaves `last_error_was_network()` true rather
  than silently empty (`test_empty_versus_broken.py` is the existing home for
  that assertion).

Network is never touched in unit tests; fixtures go in
`tests/unit/core/radio/fixtures/` beside the ones already there.

### Risks, and what to do about them

| Risk | Mitigation |
| --- | --- |
| Undocumented endpoints, no contract | The parsers are tolerant and the errors are typed; a shape change degrades to "no rows", and Part V makes that visible instead of mysterious. Ten years of continuity is the evidence it is not casually changed. |
| A genre is capped at 500 | Label it. Never imply the whole genre. |
| No "all stations" endpoint | **Do not build one.** StreamTuner-ng synthesises it by sweeping 313 genres with ten threads; see Part VI. |
| Dead mounts dominate a genre page | Part III: sort by live listeners, and offer "With listeners" as the honest default view. |
| Terms of use | The directory's own site calls these endpoints with no key and no account; this reads public listings and links to the broadcaster's own tune-in file, which is what that file is for. It is the same posture already reviewed and accepted for TuneIn on 2026-07-17. Record it in the egress entry rather than leaving it implicit. |

---

## 2. Live365 — the directory Quill Radio decided it could not have

### The premise that turned out to have a hole

`quill/core/radio/live365.py` says it plainly: it is a **pure string transform**
from any Live365 link to `https://streaming.live365.com/<id>`, and "resolving a
bare station *slug* with no id would need Live365's auth-gated API, which we
deliberately do not use". The judgement about the API is right and should not
change. But there is a second public surface:

**Live365 publishes its entire station list in its sitemap**, and every URL is
`/station/<Name-Slug>-a<id>` — the id is right there in the path, which is the
one thing `live365.py` needs.

Verified today with an honest UA:

- `https://live365.com/sitemap-main.xml` → **200, 923,198 bytes, 5,556 `<loc>`
  entries, 5,493 station URLs**.
- `https://live365.com/robots.txt` → **advertises the sitemap**; disallows only
  some `/blog/` paths. A sitemap exists to be read; this is sanctioned, not
  scraped.
- `https://streaming.live365.com/a43216` → **302** to a CDN edge, then
  `Content-Type: audio/mpeg`, `icy-name: AIFM Pop`, `icy-br: 192`. The whole
  chain works end to end.

And the clinching precedent: **`iheart.py` already does exactly this.** Its
docstring explains that iHeart's public sitemap is used because robots permits
it and no key exists. Live365 is the same argument about the same kind of file.

### Design — extend `quill/core/radio/live365.py`

Keep the existing pure transform untouched; add the directory beside it, ~150
lines:

```python
_SITEMAP = "https://live365.com/sitemap-main.xml"
_STATION_RE = re.compile(r"/station/(?P<slug>[^/<]+?)-(?P<id>a\d+)/?$")
_LOC_RE = re.compile(r"<loc>\s*([^<\s]+)\s*</loc>")

class Live365Error(CodedError):
    code = "QUILL-RADIO-LIVE365-DIRECTORY"

def parse_sitemap(xml: str) -> list[RadioStation]:   # pure
    """Every station in the sitemap: name from the slug, stream from the id."""

def fetch_stations(*, safe_mode: bool = False, refresh: bool = False) -> list[RadioStation]
def search_stations(query: str, *, safe_mode: bool = False) -> list[RadioStation]
def letters() -> list[str]           # A-Z + "#", for a browsable tree
def fetch_letter(letter: str, *, safe_mode: bool = False) -> list[RadioStation]
```

- **Name from the slug**: `AIFM-Pop-a43216` → `AIFM Pop`. Serviceable, and
  honest — do not invent capitalisation beyond replacing hyphens and collapsing
  whitespace.
- **Cache the parsed list**, key `live365:stations`, `max_age_seconds` 24 hours.
  It is 923 KB over the wire and yields 5,493 rows; refetching it per browse
  would be rude and slow. `_MAX_BYTES` needs to be ~4 MB here, not the default.
- **Browse by letter, not as one 5,493-row list.** The tree grammar becomes
  `live365 | live365:<letter>`, mirroring `iheartletter`. A five-thousand-row
  node is not a list a screen-reader user can work with, and the existing
  paging/prefetch code should not have to rescue a design decision.
- **Richer metadata lazily, never in bulk.** Genre, real name and bitrate come
  from ICY headers (`icy-name`, `icy-genre`, `icy-br`), which means one request
  *per station*. Do it on focus in the details pane or at play time — never for
  5,493 rows. StreamTuner-ng probes ICY only for the ~dozen "Featured" stations
  it scrapes off the homepage, and that restraint is the right instinct.
  `icy.py` already has the reading half of this.
- **The 302 is expected.** `streaming.live365.com/<id>` redirects to a CDN edge;
  `urllib` follows it and so does mpv. Do not "fix" it by storing the resolved
  edge URL — that is a load-balancer decision with a short life.

Wiring is the same eight steps as SHOUTcast, minus the genre protocol:
`ROOT_SOURCES` gets `("live365", "Live365")`, `_HANDLERS` gets a
`_browse_live365` for the letters, `search_sources.py` gets an entry,
`directory_search.py` gets `live365_search_stations`, and the egress entry is
keyed `core/radio/live365.py::_fetch`.

Tests: `parse_sitemap` over a trimmed fixture (a dozen `<loc>` entries including
one non-station URL and one malformed one), the slug-to-name transform, the
letter buckets including `#` for names starting with a digit, and the existing
URL-transform tests left alone.

---

# Part II — Radio Paradise, properly

Today Radio Paradise is one line in `networks.py` — a Radio Browser name query,
which returns whatever somebody happened to register there, at whatever quality.

`https://api.radioparadise.com/api/list_chan?list_type=json` answers **200, 8,430
bytes**, with every channel, its slug, and `current_listeners` (6,768 on the Main
Mix when probed). The stream naming is a fixed pattern:

```
https://stream.radioparadise.com/<path>

Main Mix (chan 0):  aac-32 | aac-64 | aac-128 | mp3-192 | aac-320 | flacm
Other channels:     <slug>-32 | -64 | -128 | -192 | -320 | -flacm
Serenity:           "serenity" (64k AAC+ only) | "serenity-flac"
Radio 2050:         slug "radio2050", absent from list_chan -- add it explicitly
```

So a proper source is one GET, a handful of channels, and a row per channel ×
quality — **including lossless FLAC**, which nothing else in the browse tree
offers, and 32k AAC+, which matters just as much to someone on a metered
connection.

`quill/core/radio/radio_paradise.py`, ~120 lines: one fetch, one pure
`parse_channels(json) -> list[RadioStation]`, `CATEGORY_LABEL`, cached 6 hours
(`radioparadise:channels`). Rows are `"The Main Mix — 320k AAC"` with
`codec`/`bitrate_kbps` filled in and `listeners` from `current_listeners`.
`ROOT_SOURCES` gets `("radioparadise", "Radio Paradise")`; `_FLAT` gets the
lambda; the `networks.py` entry is then removed so the same station does not
appear twice under two different mechanisms with different quality.

This is the best quality-per-hour item in the file, and it exercises the
"one source, many quality rows" shape before anything larger depends on it.

---

# Part III — Live listeners as a dimension

## Why this is not just another column

Radio Browser gives `votes` and `clickcount`: popularity, historical, and
gameable. SHOUTcast and Radio Paradise give **concurrent listeners right now**.
That is a different fact and a better one for the only question a browsing
listener actually has, which is *what is on the air and worth hearing*.

The probe makes the case better than any argument: in the SHOUTcast Jazz page,
**39 of 500 stations had any listeners at all**. A directory browsed without
this field is 92% parked mounts, and the listener finds out one Enter key at a
time. That is exactly the failure `station_confidence.py` was written to end for
Radio Browser, whose `lastcheckok` it finally reads — and `Listeners > 0` is the
same signal from a directory that publishes no checker.

## The change

1. **`quill/core/radio/models.py`** — one field on `RadioStation`:

   ```python
   #: Live concurrent listeners, as reported by a directory that measures them
   #: (SHOUTcast, Radio Paradise). Distinct from ``votes``, which is community
   #: popularity and historical: a station with 4,000 votes and 0 listeners is
   #: well-liked and off the air. 0 means "not reported", not "nobody" -- most
   #: directories publish nothing here. Transient and excluded from equality,
   #: exactly like ``last_check_ok``: it describes how a row is doing, not which
   #: row it is, and a station whose audience changes must not become a
   #: different station to the favourites de-duplicator.
   listeners: int = field(default=0, compare=False)
   ```

   `compare=False` is load-bearing. Without it, every refresh would make every
   station a new station to `favorites.py`.

2. **`details_text`** gains a line next to the existing `Community votes:` one —
   `Live listeners: 8,281` — grouped with the *machine facts* at the bottom,
   where the property's docstring says they belong.

3. **The row label stays clean.** Do not append "(8,281 listeners)" to every
   name: a screen reader then reads a number on every row of a 500-row list.
   Put it in details, in sort order, and in a filter.

4. **Sorting.** SHOUTcast lists arrive already ordered by listeners; keep that
   order and do not re-sort alphabetically. Borrow StreamTuner-ng's declarative
   idea rather than its implementation: a source may state its own opening
   order, so `shoutcast` opens most-listened-first and `live365` opens A-Z. One
   attribute, read by the tree, no per-source branch in the UI.

5. **"With listeners" as a filter, not a category.** StreamTuner-ng injects a
   pseudo-category. Quill Radio already has a better place: the existing
   filtering in the browse tree and Find Stations facets. A "Live now" toggle
   that keeps rows with `listeners > 0` (falling back to `last_check_ok` where
   listeners are unknown) is one predicate that improves every source at once
   rather than one source's tree.

6. **Say it out loud once.** When a filtered view is entered, the spoken
   summary should say what was dropped — "39 of 500 stations have listeners
   now" — because silently showing 39 rows where a directory has 500 is the
   kind of helpfulness that reads as a bug.

---

# Part IV — Source health and a crash budget

## What StreamTuner-ng has

Every plugin call goes through `PluginHost.call`: a daemon thread, a wall-clock
timeout, `except BaseException`, and a `Result` carrying one of six statuses —
`LOADING / OK / EMPTY / ERROR / TIMEOUT / DISABLED`. Per-plugin health keeps
consecutive errors, totals, and a 25-line log; **three consecutive failures
auto-disable the plugin**, persisted, cleared when the user re-arms it. A
coloured dot shows the state.

## What Quill Radio already has, and what it is missing

It has the harder half, and arguably the smarter half: `browse_failure.py`
distinguishes *empty* from *broken* and keeps the reason **per thread**, so one
branch's failure cannot describe another branch's empty folder — a subtlety
StreamTuner-ng does not have. `browse()` clears the marker on entry and only
clears it again when a listing actually arrives, which is a bug they have not
had to fix yet.

What is missing is **bookkeeping over time**. A source that failed the last three
times is still offered, still costs a full timeout on every open, and still says
only "nothing here" in the moment.

## The proposal — `quill/core/radio/source_health.py`

```python
@dataclass(frozen=True, slots=True)
class SourceHealth:
    source_id: str
    status: str          # "ok" | "empty" | "error" | "off"
    message: str = ""
    consecutive_errors: int = 0
    last_ok_epoch: float = 0.0
    auto_disabled: bool = False

def record(source_id: str, status: str, message: str = "") -> SourceHealth
def health(source_id: str) -> SourceHealth
def rearm(source_id: str) -> None
```

- **One call site**, in `browse_sources.browse()` where `_remember_failure` and
  the `LAST_FAILURE.pop` already are. Nothing else changes.
- **Persisted** beside the existing `browse_visibility` state, so it survives a
  restart — which is the whole point, since the alternative is re-learning that
  a directory is down on every launch.
- **Auto-disable after 3 consecutive failures, and say so.** A source that
  silently vanishes is worse than the failure. The announcement is: "TuneIn has
  failed three times and has been switched off. Browse Sources... to turn it
  back on." Turning it back on clears the counter, exactly as StreamTuner-ng
  does.
- **Text, never colour.** The Browse Sources dialog gains a status column that
  reads `OK`, `Empty`, `Failed 3 times`, `Off` — a coloured dot is precisely the
  accessibility mistake this project exists to avoid, and it is also the only
  part of their design that cannot be spoken.
- **The six-state vocabulary is the real import.** "Empty" and "Error" being
  different states, with *reachable but returned nothing* treated as degraded
  rather than broken, is the distinction `browse_failure` already preserves for
  one call; this makes it durable.

---

# Part V — Bounded fan-out, and the honest cost of "everything"

StreamTuner-ng's TuneIn plugin threads a mutable one-element `budget[0]` counter
through its OPML crawl, decrementing on each fetch, so **one click can never
cost more than N requests** however deep the tree or however many "More
Stations" links appear. It also refuses to re-fetch a URL already seen in the
same crawl, which kills loops. Their SHOUTcast does the opposite kind of clever:
a ten-thread sweep of all 313 genres, deduped by URL, streamed to the UI in
chunks so the count climbs instead of stalling.

Both are worth knowing and they pull in opposite directions. The lesson for
Quill Radio:

- **A synthetic "everything" view is a hundreds-of-request operation and must be
  labelled as one.** If SHOUTcast lands, "All Stations" should simply not exist.
  313 POSTs to a third party behind a tree node that looks like every other tree
  node is not a feature, it is an incident.
- **A per-action fetch budget belongs in `federated_browse.py` and
  `federated_search.py`**, where fan-out across sources is already the model. A
  small explicit ceiling ("this click will make at most N requests"), decremented
  through the call, with the overflow reported rather than silently truncated —
  the "no silent caps" rule this project already applies elsewhere.
- **Where a sweep is genuinely wanted** (a catalogue rebuild, say), it is a
  background job with spoken progress and a cancel, not a browse node.

---

# Part VI — A credential never enters a row

The AudioAddict plugin is the most interesting engineering in StreamTuner-ng,
and the service is the least interesting part of it.

Its rows carry `audioaddict://<domain>/<channel>` — a fake scheme. The real URL
(`http://prem1.<domain>/<channel>_hi?<listen_key>`) is built **only in
`resolve_url`, at play time**. The comment states the reason exactly: so the key
is never written into disk caches, favourites, history, CSV exports, or the
status bar.

Quill Radio has all of those hazards and more — `favorites.py`,
`recordings_index.py`, `playlist_export.py`, `backup.py`, the catalogue, the
status bar — and a `RadioStation` moves between them freely. There is no keyed
source today, so nothing leaks today. The moment there is one (AudioAddict, a
paid feed, a listener's own authenticated server), the rule needs to already
exist:

> **A credential never appears in a `RadioStation`.** A keyed source stores an
> opaque locator in `stream_url` and applies the credential in `resolve()`,
> immediately before playback, and nowhere else.

Mechanically this is free: `browse_sources.resolve(node_id)` already exists for
lazily-resolved leaves (TuneIn and iHeart use it), so a keyed source is one more
`needs_resolve` case in a path that is already there. Worth adding a test that
asserts a resolved URL never reaches `favorites.save` — the kind of test that
looks pointless until the day it earns its keep.

**AudioAddict itself is probably a no.** StreamTuner-ng's own docstring records
that the free public cluster is decommissioned (`pubN.*` hosts are NXDOMAIN), so
without a paid subscriber key there is nothing playable at all.

---

# Part VII — Source-declared options

`options_spec` is a list of dicts on the plugin class. Two kinds: `choice`
(rendered as a radio submenu — the bitrate picker) and `secret` (a masked
dialog — the listen key). The host renders them, stores the value under the
plugin's config key, and the plugin reads it back. **No UI code in the plugin.**

Quill Radio's analogue is the Quillin manifest plus the settings schema, which
today does not let a contributed source declare its own settings. If Part VIII
is ever taken, this is the piece that stops every new source needing a dialog of
its own. The accessible version renders the declaration into the existing
settings surface with proper labels, associations and a keyboard route — not
into a right-click menu, which is a mouse idiom the keymap would have to grow a
route to anyway.

---

# Part VIII — Quillin-contributed browse sources

## The contrast

StreamTuner-ng's entire contract is two methods —

```python
update_categories() -> list[str]
update_streams(category, search=None) -> list[row]
```

— plus optional `resolve_url(row)` and a handful of declarative class attributes
(`has_search`, `needs_resolve`, `page_size`, `group`, `priority`,
`all_category`, `category_pins`, `default_sort`). Drop a `.py` file in the user
plugins folder, restart, and a new directory appears. A file that will not
import is skipped and reported, never fatal.

Quill Radio's `directory_registry.py` is deliberately far smaller: a Quillin
contributes `(query) -> list[dict]`, **search only**, and the docstring is
explicit that the handler "makes no network call of its own... so consulting the
registry never introduces a new egress site."

That constraint is correct and is the reason the egress audit means anything. It
also means a Quillin can never contribute a *browse* source — and the long tail
in StreamTuner-ng (FIP, Jamendo, LITT, Nightride.FM, AudioAddict) is exactly the
sort of thing that should be community-contributed rather than shipped.

## The shape that squares it

1. Extend the provider contract to mirror theirs:
   `categories()` / `stations(category, search)` / `resolve(row)`.
2. **Make egress declared rather than absent.** A provider names the hosts it
   will contact in its manifest, and the HTTP layer enforces that list at call
   time. That is strictly better than today's all-or-nothing, and it is the
   question StreamTuner-ng has no answer to at all — their plugins can reach
   anything.
3. Run every call through Part IV's health record with a timeout, so a bad
   contributed source degrades to a text status instead of hanging the tree.
4. Rows come back as dicts and are coerced through one validator into
   `RadioStation`, with unknown keys dropped — StreamTuner-ng's `make_row` is
   the right instinct (schema in one place, two required keys, sane defaults)
   and `models.py` is where it belongs here.

This is the largest item in the file and the only one that changes an interface.
It deserves its own plan, not a paragraph inside a source addition.

---

# Part IX — StreamTuner2's playlist knowledge, and small hardening

`action.py` is the historical treasure and mostly a museum piece for us:
`playlist_formats.py` already parses PLS, XSPF, ASX and M3U, and does something
StreamTuner2 never did — `classify_m3u` tells an HLS media playlist from a
playlist of stream URLs, which is the modern failure that actually bites. Two
ideas in it are still live:

1. **Disagreement as a signal.** StreamTuner2 collects four independent opinions
   about what a URL is — the source's declared `listformat`, the HTTP
   `Content-Type`, a content regex, and the URL extension — and logs a warning
   when they disagree rather than silently trusting one. That is a good input to
   `bad_station_report.py` and to Add Custom Station, where "this says it is a
   playlist but serves audio" is precisely the diagnosis a listener cannot make
   for themselves.
2. **ICY-response detection.** `http_probe_get` treats *a response with no HTTP
   headers at all* as "this is a streaming server, stop analysing it", because a
   SHOUTcast server answers `ICY 200 OK`, not `HTTP/1.1 200 OK`. Old, ugly, and
   still true.

Its long tail of formats — `b4s`, `wpl`, `qtl`, `asf` `[Reference]`,
`[InternetShortcut]`, `.desktop` `Link=` — is a cheap robustness win for pasted
links and is no more than a lookup table plus four small parsers.

Three operational lessons, one line each:

- **Charset.** StreamTuner-ng overrides `requests`' Latin-1 default when a
  server omits the charset, because otherwise TuneIn's "Rádio" arrives as
  "RÃ¡dio". Quill Radio uses `urllib` and decodes UTF-8 explicitly, which is
  right — and the SHOUTcast probe proved the hazard is real (a default-codec
  read of `/Home/Top` raised `UnicodeDecodeError`). Add the non-ASCII fixture.
- **Byte-capped downloads.** Their `get_bytes(max_bytes=…)` streams and aborts
  when a resource declares or exceeds a cap. Quill Radio's `_fetch` pattern does
  the same and even reads one byte past the cap to *detect* truncation. Apply it
  to any new source, including the 923 KB Live365 sitemap.
- **Negative caching.** They write a `.miss` marker so a lookup that found
  nothing runs once rather than every session. `directory_cache.py` has no
  negative entry today; the same trick fits any "is there artwork / a homepage /
  a status endpoint" probe — including the lazy ICY enrichment in Part I.2.

---

# Part X — What not to take

- **The browser User-Agent.** Measured, not assumed: an honest UA got identical
  bytes from the one endpoint that supposedly requires a browser.
- **The favicon pipeline.** 346 lines of Qt image decoding, apple-touch-icon
  ranking and ICY-derived homepage discovery, in service of an icon nobody
  hears. The *derivation trick* — find a broadcaster's real homepage from the
  stream's `icy-url` when the directory has none — is worth keeping for the
  **details pane**, where "Station website" is genuinely useful. The imaging is
  not.
- **The chrome.** Discord Rich Presence, spectrogram, VU meter, wallpaper
  engine, synthwave theme.
- **Their category model wholesale.** Quill Radio's node grammar is richer than
  a flat category list and covers things StreamTuner has no concept of (a
  podcast's episodes, a book's sections, a state's weather stations). Take the
  declarative attributes, not the structure.
- **Their plugin sandbox story**, which is that there isn't one. Part VIII takes
  the ergonomics and adds the thing they left out.

---

# Where Quill Radio is already ahead

Worth stating plainly so this file is not read as a list of deficiencies.
StreamTuner-ng is a good radio browser and nothing more. Quill Radio already
has: podcasts including unsubscribed browsing and Podcast Index; audiobooks
(LibriVox, Gutenberg); the Internet Archive nested to any depth; YouTube; NOAA
Weather Radio; an ACB media calendar; recording with scheduling, resume and
liveness checks; a signed community catalogue; HLS disambiguation; DVR; device
routing; a keyless iHeart integration built on exactly the sitemap logic
recommended above for Live365; per-thread empty-versus-broken diagnosis;
stale-cache tiering with the age surfaced and spoken; station confidence read
from the directory's own checker; and an accessibility contract none of the
borrowed code has any concept of.

The gap is narrow and specific: **two directories, one metric, one source done
properly, and an argument about who may contribute a source.**

---

# Part XI — Sequencing

Each step is independently useful, independently revertible, and sized.

| Order | Item | Why here | Rough size |
| --- | --- | --- | --- |
| 1 | **Radio Paradise** (Part II) | Smallest; proves the "many quality rows" shape; immediate audible win (FLAC). | 1 module (~120 lines), 2 wiring lines, 1 test file |
| 2 | **`listeners` on `RadioStation`** (Part III) | Radio Paradise supplies it, so the field lands with a real user before SHOUTcast depends on it. | ~10 lines + details line + tests |
| 3 | **Live365 directory** (Part I.2) | Reuses the existing id→stream transform and the iHeart sitemap precedent; ~5,500 stations for one GET. | ~150 lines added, 1 handler, 1 egress entry |
| 4 | **SHOUTcast browse + Top 500 + search** (Part I.1) | The big one. Deliberately no "All Stations". | ~300-line module, ~10 wiring lines, 1 egress entry, ~15 tests |
| 5 | **"Live now" filter + source-declared opening order** (Part III.4-6) | Only worth building once two sources report listeners honestly. | UI predicate + one attribute |
| 6 | **Source health + crash budget** (Part IV) | Pays for itself the moment there are two more third-party directories to go wrong. | ~150 lines + a dialog column |
| 7 | **Fetch budget in the federated paths** (Part V) | Independent; do it whenever fan-out is next touched. | ~40 lines |
| 8 | **Playlist disagreement + odd formats** (Part IX) | Into Add Custom Station and the bad-station report. | Small, self-contained |
| 9 | **Credential discipline** (Part VI) | A rule and a test now; the source that needs it later. | Documentation + 1 test |
| 10 | **Contributed browse sources** (Parts VII-VIII) | Its own plan, its own review. | Project |

**The gate checklist every one of steps 1, 3 and 4 must tick**, because this is
the project's own contract and skipping any of it fails the build rather than
the review:

- A new `CodedError` subclass with a **unique** `code = "QUILL-RADIO-<X>-<Y>"`
  (GATE-EC, `error_code_audit.py`).
- A `refuse_in_safe_mode(safe_mode)` guard called first in every public entry
  point.
- One reviewed entry in `quill/tools/network_egress_entries_radio.py`, keyed
  `core/radio/<module>.py::<fetch fn>`, saying what is sent, what returns, what
  triggers it and what Safe Mode does — plus the matching
  `_rebaseline_<date>_<name>_egress` note in `module_size_budgets.json`, since
  that gate file grows by design.
- `directory_cache.resolve` for anything that changes slowly; nothing cached
  that claims to be live.
- A node in `browse_sources.py`'s docstring grammar, an entry in `ROOT_SOURCES`,
  and either a `_GENRE_MODULES` / `_FLAT` line or one `_HANDLERS` entry —
  **thin wiring only**: the module is at 894 lines against its 908 budget, so the
  three sources below share fourteen lines of headroom -- past that it needs a
  rebaseline note of its own, or the extraction the budget entry already names.
- Pure parsers split from the fetch, with fixtures under
  `tests/unit/core/radio/fixtures/`, and no unit test that touches the network.
- The empty-versus-broken assertion in `test_empty_versus_broken.py` for the new
  source.
- wx-free, strict-typed (`mypy quill\core`), `ruff` clean.

---

# Appendix A — What was probed, and what answered

Run 2026-08-26 from this machine with `curl`, sending
`QuillRadio/3.0 (+https://quillville.org)` as the User-Agent unless noted.
Read-only requests to public endpoints; no project data left the machine.

| Endpoint | Method | Result |
| --- | --- | --- |
| `directory.shoutcast.com/Home/BrowseByGenre` (`genrename=Jazz`) | POST | **200**, 115,921 bytes. 500 rows, 500 unique IDs, 25 duplicate names, 39 rows with `Listeners > 0`, bitrates 128 (×487) / 64 / 320 / 256 / 192, formats `audio/mpeg` (×497) and `audio/aacp` (×3). |
| …the same with a spoofed Chrome UA + `Referer` + `X-Requested-With` | POST | **200**, byte-identical size. **The browser UA buys nothing.** |
| `directory.shoutcast.com/Home/Top` | POST | **200**, 132,768 bytes, 500 rows, **all** with listeners, max **8,281**. |
| `directory.shoutcast.com/Search/UpdateSearch` (`query=bluegrass`) | POST | **200**, 21,140 bytes, relevant hits (first row: "HPR4: Bluegrass Gospel from Heartland Public Radio"). |
| `directory.shoutcast.com/Genre` | GET | **302 → `/Search`**; the landing page carries **313** distinct `/Genre?name=…` links and 317 `loadStationsByGenre(` calls — the same markers StreamTuner2's 2014 regex matched. |
| `yp.shoutcast.com/sbin/tunein-station.pls?id=1528122` | GET | **200**, valid `[playlist]`, `File1=http://streams.radiomast.io:80/…`, title carrying the listener count. |
| Decoding `/Home/Top` with the platform default codec | — | **`UnicodeDecodeError: 'charmap' codec can't decode byte 0x8d`.** Decode UTF-8 explicitly. |
| `live365.com/sitemap-main.xml` | GET | **200**, 923,198 bytes, 5,556 `<loc>` entries, **5,493** station URLs with `a#####` ids. |
| `live365.com/robots.txt` | GET | **200**, advertises the sitemap, disallows only `/blog/` paths. |
| `streaming.live365.com/a43216` | GET | **302 → `das-edge63-live365-dal03.cdnstream.com/a43216`**, then `Content-Type: audio/mpeg`, `icy-name: AIFM Pop`, `icy-br: 192`, `icy-metaint: 8192`. |
| `api.radioparadise.com/api/list_chan?list_type=json` | GET | **200**, 8,430 bytes; channels with `slug`, `chan`, `title`, `current_listeners` (Main Mix: 6,768). |

Not probed and therefore not claimed: AudioAddict's premium hosts (they need a
paid key), iHeart's content API (already integrated), TuneIn's OPML (already
integrated).

# Appendix B — What was read

**StreamTuner-ng** (Apache-2.0, PySide6/Qt6 + libmpv, ~20 channels):
`PLUGINS.md`, `plugins/base.py`, `plugins/host.py`, `plugins/loader.py`,
`plugins/result.py`, `net/http.py`, `favicons.py`, `config.py`, and the
`shoutcast`, `tunein`, `radiobrowser`, `iheart`, `live365`, `audioaddict`,
`radioparadise`, `nightride`, `somafm`, `fip`, `litt`, `jamendo`, `bookmarks`
and `local` channels.

**StreamTuner2** (Public Domain, GTK, 987 commits): `channels/shoutcast.py`,
`channels/tunein.py`, `channels/__init__.py`, `action.py`, `ahttp.py`, and the
channel inventory — including the `contrib/disabled/` graveyard, which is its
own useful document: Dirble, Radionomy, Reciva, Streema, vTuner, Live365's old
API, iCast, iTunes. Every source in this file is a dependency on somebody else's
business decision, and that folder is what that looks like ten years on. It is
the strongest argument for Part IV: when a directory dies, the app should say so
and carry on, not quietly return nothing forever.

**Quill Radio**, for comparison: `browse_sources.py`, `browse_nodes.py`,
`directory_cache.py`, `directory_registry.py`, `directory_search.py`,
`browse_failure.py`, `models.py`, `search_sources.py`, `federated_search.py`,
`station_confidence.py`, `xiph.py`, `iheart.py`, `live365.py`, `my_servers.py`,
`station_status.py`, `icy.py`, `networks.py`, `playlist_formats.py`,
`tunein.py`, plus `quill/tools/network_egress_entries_radio.py` and
`module_size_budgets.json`.

# Appendix C — Licences, and how the code may be used

- **StreamTuner-ng is Apache-2.0** (`NOTICE`: "Copyright 2026 IronWolve"), and
  its own notice records that it is a from-scratch port using no StreamTuner2
  code.
- **StreamTuner2 is Public Domain** (`PKG-INFO: License: Public Domain`) — no
  obligation at all.

Neither is a reason to paste. What is being taken here is **protocol
knowledge**: which endpoint answers, what it wants, what comes back, and which
of them still work. That is a fact about SHOUTcast and Live365, not an
expression owned by either project — and this file verified all of it
independently, which is why the design decisions above (the 500-row cap, the
sparse listener field, the null `StreamUrl`, the honest User-Agent, the UTF-8
trap) differ from what either repository's code assumes. Implement in Quill
Radio's own idiom, the way `iheart.py` and `xiph.py` already read. If any
non-trivial block is ever lifted verbatim from StreamTuner-ng, Apache-2.0 wants
the attribution, which is one line in a docstring.
