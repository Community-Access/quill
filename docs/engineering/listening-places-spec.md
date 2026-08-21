---
title: "Listening Places, format listening-places/1"
subtitle: "A file-based interchange format for listening positions"
---

# Listening Places

**Status:** implemented in QUILL Cast, 2026-08-20. Format id `listening-places/1`.

This is the normative description of the file QUILL Cast writes and reads, so a
second implementation has something to conform to rather than a moving target.
It is the format proposed to Earshot (Payown Media) in that project's
`sync.md`; the section numbers below match that proposal, so the two documents
can be read side by side.

The mechanism itself is deliberately dull. What it buys is this: you listen to
forty minutes of an episode on your phone, you sit down at your desk, and the
desktop knows where you got to -- with no account, no server, no signup, and no
company holding anybody's listening history.

## What it is not

- **Not an account system.** No email, no password, no portal.
- **Not audio sync.** The folder carries positions, which are bytes. Whether the
  audio is also in that folder is entirely the user's business.
- **Not real-time.** Propagation takes as long as the cloud client takes. The
  promise is that your place is right when you pick up the other device.
- **Not subscriptions.** Positions and played state only. Subscriptions cannot
  be hashed the way ids are -- the whole point of a feed record is a URL the
  other app can fetch -- so they carry a different exposure and belong behind
  their own switch. Not implemented.
- **Not encrypted.** This is tier A. QUILL's encrypted machine-to-machine sync
  is a separate switch over the same folder (`quill/core/sync/places.py`) and
  the two do not interfere.

## 1. The folder

The user picks one folder, inside whatever they already sync. The apps create:

```
<chosen folder>/
  Listening Places/
    README.txt
    devices/
      1f4c8a2e.json
      9b30d7f1.json
```

**One writer per file.** Every device writes exactly one file and reads
everyone else's. This is the property the whole design rests on: cloud drives
resolve two devices editing one file by leaving `positions (Jeff's conflicted
copy).json` lying around, which is the single worst failure mode available, and
if no two devices ever write the same file that failure cannot happen. It also
scales past two devices for nothing -- phone, laptop and desktop each drop one
file and every device merges across all of them.

The filename is a random device id generated once at setup, **not the device
name**, so a shared folder's listing does not announce "Jeff's iPhone" to
everybody who can see it.

`README.txt` is one paragraph of plain text, so somebody who stumbles on the
folder six months later is not mystified.

A device file is capped at 1,000 records (roughly 250 KB); the oldest fall off.

## 2. The record

```json
{
  "format": "listening-places/1",
  "device": "1f4c8a2e",
  "device_label": "Jeff's iPhone",
  "app": "earshot/1.0.3",
  "written_at": "2026-08-20T14:02:11Z",
  "records": [
    {
      "id": "episode:3f9a1c77b2e40d58",
      "kind": "episode",
      "position_ms": 2412000,
      "duration_ms": 3894000,
      "played": false,
      "updated_at": "2026-08-20T13:58:02Z",
      "label": "Blind Abilities: Episode 214",
      "feed": "https://feeds.example.com/blindabilities"
    },
    {
      "id": "episode:b17c40e9d8a2f36c",
      "deleted": true,
      "updated_at": "2026-08-18T09:12:00Z"
    }
  ]
}
```

- `position_ms` is milliseconds.
- `duration_ms` is 0 when unknown. Plenty of feeds omit `itunes:duration`.
- `played` true with `position_ms` 0 means **finished**. This is how "I finished
  it" is distinguished from "nobody knows where they are", which matters
  because both apps zero the position on completion.
- `updated_at` is RFC 3339 UTC with a trailing `Z`. Written that way, plain
  string comparison sorts correctly, so the merge needs no date parsing.
- `label` is human-readable only and **never part of the identity**. It exists
  so a disagreement can say "you and your phone disagree about Episode 214"
  rather than reading out a hash, and it is the one field that leaks, so it can
  be turned off.
- `feed` is carried for disambiguation and debugging and is **not** part of the
  key.
- `deleted` true is a tombstone and carries no other fields. A record *missing*
  from a device file means "that device has not heard of this", never "delete
  it everywhere".

## 3. Identity

Three namespaces. An app that does not understand a namespace **ignores those
records** rather than choking on them, so the format can grow.

**`episode:`** — `"episode:" + sha256(guid)[0:16]`, where `guid` is the RSS item
GUID verbatim, before any normalisation. With no GUID, `sha256(enclosure_url)`.

Keyed on the GUID *alone*, not on feed URL plus GUID, because two apps disagree
about a feed's URL far more often than one expects: one subscribed through a
FeedBurner redirect and the other through the final host, one has `http` and the
other `https`, one carries a tracking prefix. GUIDs are required to be unique by
the RSS spec and survive all of it.

The hash is not for security. It is so a plain-text file in a shared folder does
not list every podcast somebody follows in readable form, and so ids are
fixed-length and filename-safe.

**`file:`** — `"file:" + size + "-" + digest`, where `digest` is the first 32 hex
characters of a SHA-256 over the ASCII decimal size, then the first 64 KB of the
file, then the last 64 KB (the last chunk is skipped for files under 128 KB).
That is `media_identity()` in `quill/core/media/positions.py`, in production
since before this format existed.

This is the namespace that makes the cloud-file case work: the same MP3 in
`Dropbox/Audiobooks/` produces the same id on iOS and on Windows regardless of
where each platform mounts it and what either called it.

**`stream:`** — `"stream:" + sha256(lowercased url)[0:16]`. Reserved for Quill
Radio recordings. Listed so the namespace cannot be claimed for something else.

## 4. Reading and merging

On sync, an app:

1. Lists `devices/*.json` and reads every file that is **not its own**.
2. Builds the remote view: for each id, the record with the greatest
   `updated_at` across all device files.
3. Merges the remote winner against the local record. **Last write wins on
   `updated_at`.** Ties and missing timestamps resolve to the remote, which
   keeps behaviour predictable when data is incomplete.
4. Applies wins to its own database.
5. Rewrites its own device file from its own now-current state.

**Last write, not furthest position.** If you deliberately jumped back twenty
minutes to re-hear something and then opened the episode on the laptop, the
furthest position is precisely the wrong answer.

A disagreement is worth telling the user about only when the two positions are
at least **five minutes** apart. Finding the position eight seconds off is not
news; "these two devices disagree by an hour" is.

**Do not rewrite the device file when nothing changed.** Hash the records you
are about to write and compare against the last hash you wrote. Without that
check a machine left open all day re-uploads an identical file over and over,
which costs bandwidth, drains a battery, burns a metered connection, and makes
the folder's modification times useless to anybody reading them.

## 5. Clock skew

Two devices with clocks a few minutes apart make bad merge decisions. Vector
clocks are overkill for a listening position. One cheap guard fixes the case
people actually notice: **when writing a record, never write an `updated_at`
earlier than the newest `updated_at` you have ever seen for that id, plus one
second.** A device with a slow clock therefore cannot repeatedly lose to its own
stale data.

A known, bounded limitation rather than a solved problem. Positions are not
money.

## 6. When each half runs

Never on a playback path, and never as a blocking operation.

**Writing follows activity:** on pause or stop, on completion, on marking
something played or unplayed; during continuous playback, debounced.

**Reading happens at two moments only: app launch, and an explicit Sync Now.**
Not on a timer, not on window focus, not on a file-change notification.

That asymmetry is a decision, not an implementation shortcut. If a read lands
mid-session and finds that another device moved you to 52 minutes in the episode
you are listening to at 40, every available behaviour is bad: moving the playhead
under somebody is unacceptable, and worse for a screen reader user who gets no
visual cue that anything happened; queuing it silently is confusing; asking
mid-episode is an interruption nobody wants. At launch nothing is playing, so
there is nothing to disturb.

The cost is that a change made elsewhere while the app is already open does not
appear until the next launch or the next Sync Now. That is the correct trade.

**A read always reports its result, and says nothing happened when nothing did.**
"Sync finished" after a sync that moved nothing is the message that teaches
people to ignore the message.

## 7. Privacy

What a third party with access to the folder learns from a tier A file: how many
things are listened to, roughly how long each is, when, the device labels, and
the `label` field if it is left on. Not the feed URLs and not the GUIDs, because
those are hashed. For most people syncing through their own Dropbox that is
less than the OPML file they already export by hand.

`label` is a separate switch for the people it is not fine for.

## 8. Where this lives in QUILL

| Piece | Module |
|---|---|
| Format, identity, device files, merge, clock-skew guard | `quill/core/sync/listening_places.py` |
| Cast's episode-position adapter | `quill/core/podcasts/position_sync.py` |
| One sync pass over the folder | `quill/core/sync/places_interchange.py` |
| Settings, device id, the three switches | `quill/core/sync/places_config.py` |
| The window, and Sync Now | `quill/ui/sync_places_dialog.py` |
| Launch read, background read, one-sentence report | `quill/ui/sync_places_command.py` |
| Conformance fixtures | `tests/unit/core/sync/fixtures/` |

The per-episode timestamp this all rests on is
`PodcastEpisode.position_updated_at`. Every site that moves a position goes
through `position_sync.remember_position` / `mark_played` rather than assigning
`position_ms` directly, because one site that forgets the timestamp is a device
whose place silently stops travelling.

## 9. Conformance fixtures

`tests/unit/core/sync/fixtures/` holds a device file and the expected merged
result. `test_conformance.py` reads them. The usual fate of an informal
interchange format is that two implementations drift until somebody's data is
wrong; a fixture in both repositories means a change that breaks the other app
fails a test rather than a user.

Adding a case is adding a JSON pair. Please do, in either repository.
