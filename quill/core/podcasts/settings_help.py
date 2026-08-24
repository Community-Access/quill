"""What every podcast setting does, and the misreading it prevents.

The rule (list.md section 3): **what it does, then the misreading it prevents,
in that order, in one added sentence.** Not a doc page -- a doc page is
something somebody has to decide to go and read, and the moment a setting is
misread is the moment they are standing on it.

Every misread in this area has been about the second half, and they rhyme:

* *does this apply to what I already have, or only to what comes next?*
  (auto-download, auto-trim, delete-after-playing, the download folder)
* *does "keep" mean the episode, or just the file?* (retention, the storage
  cap, the Inbox limit -- three different answers, all of them "just the file",
  and none of them said so)
* *does turning this off mean it never happens, or only that it does not happen
  by itself?* (the metered guard, automatic downloads, the feed check)

Here rather than beside each control for three reasons. The strings are read by
two dialogs -- the shared default and the per-show override -- and a rule that
holds in one and not the other is worse than no rule. They are the file's own
subject, so they can be *checked*: ``test_settings_help.py`` asserts that every
one of them says what it does not do, which is not a thing you can assert about
a literal buried in a sizer. And the dialogs were at their GATE-11 ceilings,
where growing the words meant not growing them.

wx-free, strict-typed, pure data.
"""

from __future__ import annotations

#: Shared defaults, on the Podcast Settings dialog.
HELP: dict[str, str] = {
    "playback_default": (
        "Whether a newly subscribed podcast downloads its episodes or streams "
        "them. It changes new subscriptions only -- podcasts you already follow "
        "keep whatever they are set to, and you can still download or stream "
        "any single episode whatever this says."
    ),
    "retention": (
        "What happens to downloaded *files* as they age. It never removes an "
        "episode from a show's list, unsubscribes you, or forgets where you had "
        "got to: a deleted file downloads again on request, in the same place "
        "in the same list."
    ),
    "keep_last_n": (
        "How many of a show's newest downloads to keep on disk, when retention "
        "is set to keep only the most recent. Older episodes stay listed and "
        "stay playable -- what goes is the file, not the episode."
    ),
    "auto_download": (
        "How many of a show's newest episodes to fetch without being asked, on "
        "subscribe and on every refresh. Newest first, and never backwards: it "
        "does not go and collect a show's back catalogue, which is what Always "
        "Sync is for."
    ),
    "inbox_max": (
        "At most this many episodes in the Inbox per show; 0 means no limit. "
        "Trimming never deletes -- episodes stay unplayed in their show's own "
        "list, and anything played, started or queued is never trimmed."
    ),
    "history_days": (
        "How long QUILL Cast keeps a record of what you listened to and when. "
        "It never leaves this computer either way. Choosing not to keep one "
        "means nothing is written at all, not that it is deleted afterwards."
    ),
    "metered": (
        "With this off, downloads QUILL Cast starts by itself wait until you "
        "are off a metered connection. A download you ask for by name always "
        "happens, metered or not."
    ),
    "volume_boost": (
        "Makes quiet podcasts louder. It is playback gain: nothing on disk "
        "changes and your system volume is untouched. This is the default for "
        "every podcast -- the one that actually matters is the per-podcast "
        "override, because one badly-mastered show is exactly what a single "
        "setting cannot fix."
    ),
    "download_notify": (
        "One desktop notification when the download queue goes quiet, not one "
        "per episode. Off by default. Nothing leaves this computer, and quiet "
        "hours hold it back like any other background news -- the downloads "
        "themselves still run."
    ),
    "streaks": (
        "Whether the Statistics window reports how many days in a row you have "
        "listened. Off unless you ask for it -- a streak is a nudge, and a nudge "
        "nobody asked for is pressure. It changes what Statistics shows and "
        "nothing about what is played, downloaded or kept."
    ),
    "delete_after_days": (
        "Delete a downloaded file once it is this many days old; 0 means never. "
        "Queued and part-played episodes are never deleted, and the episode "
        "itself stays in its list either way."
    ),
    "delete_after_playing": (
        "Remove a downloaded file once you have finished the episode, however "
        "you finish it -- playing it to the end, or marking it played. Not the "
        "age rule above and not the storage cap: it composes with both. It "
        "never touches a running download, and never goes back over episodes "
        "you finished before switching it on."
    ),
    "storage_cap": (
        "A ceiling on total podcast download storage. When it is exceeded, "
        "already-played downloads are removed oldest first; a queued or "
        "part-played episode is never removed, so the cap can be exceeded "
        "rather than take one."
    ),
    "playback_cache": (
        "Save a streamed episode's audio as it plays, so playback continues "
        "through a dropped connection, chapters can be found in it, and keeping "
        "it costs no second download. It is not a download: the audio is "
        "removed automatically, it does not appear in Downloads, and the "
        "episode you are listening to is never the one removed."
    ),
    "playback_cache_cap": (
        "How much room streamed episodes may use between them. The "
        "least-recently-played goes first, and the episode playing now is never "
        "removed -- so this is a target rather than a hard limit."
    ),
    "launch_view": (
        "Which part of the library QUILL Cast opens on. It changes where you "
        "land, nothing else: no episode is played, and Resume Last Episode on "
        "Launch is the separate setting for that."
    ),
    "download_folder": (
        "Where downloaded episodes are saved; blank uses the default podcasts "
        "folder. Changing it applies to downloads from now on -- files already "
        "on disk stay where they are and keep playing from there."
    ),
    "download_folder_button": "Choose a download location",
    "unsubscribe_files": (
        "What to do with a show's downloaded episode files when you unsubscribe "
        "from it. It is asked at the moment you unsubscribe either way; this "
        "only decides what the answer starts as."
    ),
    "download_queued": (
        "An episode you queue is one you mean to play, so fetch it even if it "
        "is older than the automatic download count. It does not queue "
        "anything -- it only downloads what you have already queued yourself."
    ),
    "download_inbox": (
        "Download episodes as they arrive in the Inbox. Off by default: the "
        "Inbox is where episodes wait to be triaged, not a commitment to listen "
        "to them."
    ),
    "inbox_mode": (
        "Which shows the Inbox holds. Choosing every show suits a large library "
        "you triage; choosing only some suits a few shows you follow closely. "
        "Shows the Inbox does not hold are not hidden -- they are exactly where "
        "they were, in the library tree."
    ),
    "continue_queue": (
        "Auto-advance through the Play Queue. On by default -- this is what "
        "QUILL Cast has always done. It plays what is queued and stops there; "
        "it does not carry on into a show's other episodes."
    ),
    "prebuffer": (
        "Fetch the start of the next queued episode before the current one "
        "ends, so there is no pause between them. Off by default because it "
        "uses data speculatively, which matters on a metered connection. It is "
        "not a download and keeps nothing."
    ),
    "continue_group": (
        "Carry on with the show's next unplayed episode once the queue runs "
        "out. It never starts a show you were not already listening to, and "
        "with this and auto-advance both off, playback stops at the end of the "
        "episode you started."
    ),
    "name_first": (
        "In the Inbox, New Episodes and other cross-show lists, put the podcast "
        "name first so rows group by show when you skim by first letter. It "
        "changes how rows read, never what order they are in -- Sort Episodes "
        "is the setting for that."
    ),
    "always_sync": (
        "Backfill and download a show's whole catalogue, not just its new "
        "episodes; works best with retention set to keep all. This is the one "
        "setting that reaches backwards, which is why it is separate from the "
        "automatic download count."
    ),
    "auto_trim": (
        "Trim leading and trailing silence from each finished download. It "
        "rewrites the downloaded file, so it applies to new downloads only and "
        "cannot be undone on one already trimmed -- the episode can always be "
        "downloaded again."
    ),
    "normalize": (
        "Even out volume across downloaded episodes, using the audiobook "
        "builder's loudness pass. Like trimming, it rewrites the file as it "
        "lands: new downloads only, and never what is already on disk."
    ),
    "reconnect": (
        "When the connection drops mid-download, retry automatically instead of "
        "landing in Failed. The partial file resumes from where it stopped "
        "rather than starting again, so a retry costs no second download."
    ),
    "reconnect_attempts": (
        "How many times to try reconnecting before giving up on a download. "
        "Giving up leaves the episode in Failed, where Retry still works -- "
        "nothing is discarded."
    ),
    "reconnect_wait": (
        "How long to wait before each reconnect attempt. Longer suits a "
        "connection that drops for a while; it never delays a download that is "
        "running normally."
    ),
}

#: Per-show overrides, on the Show Settings dialog. Separate because every one
#: of them has the same extra thing to say: *this show only*, and clearing it
#: goes back to the shared default rather than to off.
SHOW_HELP: dict[str, str] = {
    "auto_download": (
        "How many of this show's newest episodes to download automatically, "
        "instead of the shared setting. Newest first: it does not fetch this "
        "show's back catalogue."
    ),
    "auto_queue": (
        "A new episode of this show joins the Play Queue on refresh, skipping "
        "the Inbox. Only episodes found from now on -- it does not queue what "
        "is already sitting in the Inbox."
    ),
    "notify": (
        "Speak and braille this show's new episode titles when the background "
        "check finds them, and show a tray notification. It reports; it "
        "downloads nothing and queues nothing on its own."
    ),
    "queue_expiry": (
        "Remove this show's episodes from the Play Queue once they have waited "
        "this long. They go to Recently Expired and can be restored -- nothing "
        "is deleted, and a downloaded file is untouched."
    ),
    "inbox_max": (
        "At most this many of this show's episodes in the Inbox; 0 means no "
        "limit. Trimming never deletes: episodes stay unplayed in the show's "
        "own list."
    ),
    "inbox_age": (
        "Drop this show's episodes out of the Inbox once they are older than "
        "this. Out of the Inbox, not out of the library -- they stay in the "
        "show's own list, unplayed."
    ),
    "delete_after_days": (
        "Delete this show's downloaded files once they are this many days old; "
        "0 means never. Queued and part-played episodes are never deleted, and "
        "the episodes themselves stay listed."
    ),
    "playback_cache": (
        "Save this podcast's streamed audio as it plays, so playback continues "
        "through a dropped connection and chapters can be found in it. It is "
        "not a download and keeps nothing permanently."
    ),
    "volume_boost": (
        "Makes this podcast louder, and only this one. It is playback gain: "
        "nothing on disk changes, your system volume is untouched, and no "
        "other show is affected. This is the setting that fixes one "
        "badly-mastered show without making everything else too loud."
    ),
    "reset": (
        "Drop every override for this podcast so it follows Podcast Settings "
        "again. It changes settings only -- no episode, download or queue entry "
        "is touched."
    ),
}


def describe(key: str, *, per_show: bool = False) -> str:
    """The help text for *key*, or an empty string if there is none.

    Empty rather than a placeholder: a control with no help says nothing, and
    a control that says "no description available" says nothing twice.
    """
    table = SHOW_HELP if per_show else HELP
    return table.get(key, "")


__all__ = ["HELP", "SHOW_HELP", "describe"]
