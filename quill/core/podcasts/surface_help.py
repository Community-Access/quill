"""What every QUILL Cast window is *for* -- the F1 help's opening paragraph.

Quill Radio authored this first (:mod:`quill.core.radio.surface_help`,
2026-08-23) and the F1 engine went family-wide the same day, but only Radio
had a catalogue: every Cast window answered F1 with the generic sentence,
which is true and useless. This module is Cast's half -- the wx-free
catalogue of surface purposes keyed by window title, composed by
:mod:`quill.ui.app_context_help` exactly as Radio's is.

Keyed by **window title** for the same reasons Radio is: the title is the one
identity a window already announces, the raise-if-open guards key on it too,
and it is what a person quotes back in a bug report. Cast titles carry live
data far more often than Radio's ("My Notes -- Episode 412"), so most entries
here resolve by prefix.

The catalogue is **gated** (GATE-CAST-HELP,
``quill/tools/cast_help_audit.py``): every ``wx.Frame``/``wx.Dialog`` title
constructed in the podcast UI must resolve here, so a new surface cannot ship
without saying what it is for.

Wording rules, unchanged from Radio's, so the entries stay worth reading:

* One to three sentences. The first says what the window is for; the rest say
  what somebody actually does here or the one fact that saves a support email.
* Address the listener ("your shows"), never the developer.
* No key-by-key tours -- the control section below the purpose covers the
  control under focus, and the Keyboard Shortcuts Sheet covers the rest.
"""

from __future__ import annotations

# Re-exported so Cast's help code and tests need one import, matching Radio.
from quill.core.control_help import (
    compose_control_body as compose_control_body,
)
from quill.core.control_help import (
    role_usage as role_usage,
)

#: Surface purposes by exact window title.
PURPOSES: dict[str, str] = {
    # -- the windows -------------------------------------------------------------
    "Closing QUILL Cast": (
        "What closing the window should do: exit, or keep playing with QUILL "
        "Cast tucked into the system tray. Cancel leaves everything as it "
        "was. Don't ask me again remembers your answer, and Preferences can "
        "set it back to asking."
    ),
    "QUILL Cast": (
        "One window: Find at the top, the Places list -- Inbox, New Episodes, "
        "Continue Listening, Favorites, Personal Audio, the Play Queue, Downloads, "
        "Notifications, Podcasts -- and beside it the place you chose, with its "
        "show notes and the buttons below. The buttons name what they act on, the "
        "View menu reaches each place in one key, and F6 reaches the status bar. "
        "Nothing here needs an account, and nothing you listen to leaves this computer."
    ),
    "Feed Check": (
        "Which of the podcasts you follow need something, worst first: failing "
        "feeds, then quiet ones, then the healthy rest. Opening it checks "
        "nothing; Retry checks the selected feed and Retry All Failed every "
        "failing one. A quiet podcast is not necessarily a failing feed, and Cast "
        "never stops trying a failing one."
    ),
    "QUILL Cast Tutorials": (
        "Guided lessons, one step at a time, that can run the step for you and "
        "notice when you have done it. The contents list is grouped by track and "
        "remembers where you stopped; typing 'here' in the filter box narrows it "
        "to the tutorials about the window you came from. Follow me watches what "
        "the app is doing -- never which key you pressed -- and moves you on by "
        "itself."
    ),
    "Podcasts": (
        "The Podcast Manager: every show you follow, the episodes in each, "
        "and every verb that acts on them -- play, download, mark played, "
        "file into a folder, unsubscribe. One list chooses the show, the "
        "other holds its episodes, and Shift+F10 on any row offers "
        "everything that can be done to it."
    ),
    "Downloads": (
        "The download queue, and everything you can do to it. Finished rows "
        'stay until you clear them so "did that actually download?" always '
        "has an answer, and Enter on a saved row opens the folder it landed "
        "in."
    ),
    "Play Queue": (
        "What plays next, in order. Move a row up or down to change the "
        "order, remove one you have changed your mind about, and Enter plays "
        "the highlighted episode now without losing the rest of the queue."
    ),
    "Listening Statistics": (
        "A report of your listening: which shows, how many episodes, how "
        "long, and when. It reads your own local history and nothing leaves "
        "this computer."
    ),
    "Search Everywhere": (
        "One search across everything Cast knows: your shows, their "
        "episodes, show notes and transcripts. Each result says which show "
        "and which episode it came from, and Enter opens the row it names."
    ),
    # -- the dialogs -------------------------------------------------------------
    "Add Podcast": (
        "Follow a new show. Search the directories by name, or paste a feed "
        "address you already have. What you add lands in your library, and "
        "its episodes appear the first time the feed is read."
    ),
    "Feed Credentials": (
        "The user name and password for a private feed -- a paid "
        "subscription, a members-only show. They are kept for this feed "
        "alone and sent to its own host, never to a directory."
    ),
    "Podcast Index Credentials": (
        "Your own Podcast Index API key and secret, if you have them. Cast "
        "ships with a working key; entering yours here means directory "
        "searches count against your quota rather than the shared one."
    ),
    "Import OPML": (
        "Bring shows in from another podcast app's OPML export. Choose the "
        "file, review what it found, and import; anything you already follow "
        "is left alone rather than added twice."
    ),
    "OPML Import Report": (
        "What the import actually did: how many shows were added, how many "
        "were already followed, and every feed that could not be read, with "
        "its reason. Copy All takes the report with you."
    ),
    "Smart Playlist Rules": (
        "The rules that build a smart playlist: which shows it draws from, "
        "how old an episode may be, whether played episodes count, and how "
        "many it holds. The playlist rebuilds itself from these rules -- you "
        "never add episodes to it by hand."
    ),
    "Podcast Settings": (
        "Every podcast setting in one place: how often feeds are checked, "
        "how many episodes are kept, where downloads land, what happens when "
        "an episode finishes, and how rows are spoken. Each setting applies "
        "the moment you save."
    ),
    "Quiet Hours": (
        "The window in which this app stops speaking on its own: check ticks, "
        "new-episode notices, download notices. Feeds are still checked and "
        "downloads still run -- only the announcements wait -- and anything "
        "you press a key for still answers. The window is shared with the "
        "other Quill listening apps."
    ),
    "Organise My Podcasts": (
        "Folders AI help suggests for your podcasts. Suggestions from AI help, for you to decide. "
        "Each row starts accepted; Space switches it between Accept and Skip, and Accept All and "
        "Skip All change every row. Apply Selected does only the accepted rows; Cancel or Escape "
        "changes nothing."
    ),
    "Build Me a Listening Run": (
        "Episodes AI help chose to fit the time you have, measured by Cast. Suggestions from AI "
        "help, for you to decide. Each row starts accepted; Space switches it between Accept and "
        "Skip, and Accept All and Skip All change every row. Apply Selected does only the accepted"
        " rows; Cancel or Escape changes nothing."
    ),
    "Smart Playlist from a Sentence": (
        "The rules Cast would save for the playlist you described. Apply Selected saves the "
        "playlist; you can change its rules later with Edit Rules. Cancel saves nothing."
    ),
    "Name These Chapters": (
        "New chapter titles AI help wrote from the transcript. Suggestions from AI help, for you "
        "to decide. Each row starts accepted; Space switches it between Accept and Skip, and "
        "Accept All and Skip All change every row. Apply Selected does only the accepted rows; "
        "Cancel or Escape changes nothing."
    ),
    "Tidy the Podcasts I Follow": (
        "Podcasts that look finished, doubled up or broken, each with its reason and an action. "
        "Nothing is sent anywhere for this. Suggestions from AI help, for you to decide. Each row "
        "starts accepted; Space switches it between Accept and Skip, and Accept All and Skip All "
        "change every row. Apply Selected does only the accepted rows; Cancel or Escape changes "
        "nothing."
    ),
    "Undo History": (
        "The last ten things you can take back, newest first, each saying what "
        "undoing it brings back. Undo This One takes back the highlighted step "
        "alone and leaves the rest; Ctrl+Z always takes the newest."
    ),
    "Recent Problems": (
        "Everything that has failed recently, in one list that outlives the "
        "announcement: feeds that could not be read, downloads that died, "
        "streams that dropped -- each with its reason and the time it "
        "happened. Retry tries the highlighted row again; nothing here is "
        "sent anywhere."
    ),
    "Notifications": (
        "What QUILL Cast told you while you were elsewhere, newest first: new "
        "episodes, finished downloads, feeds that keep failing and podcasts that "
        "have gone quiet. Enter goes to what a row was about; on a new episode "
        "the row's menu offers Play Now and Add to Queue. Clearing the list never "
        "touches the episodes it was about."
    ),
    "Watched Folders": (
        "The folders QUILL Cast keeps an eye on. Anything that lands in one -- "
        "from a voice recorder, a download, a shared folder -- arrives in "
        "Personal Audio by itself, once, and is announced. Add Folder chooses a "
        "new one, Folder Settings changes how it behaves, Pause stops watching "
        "for now, and Remove stops for good without touching a single file."
    ),
    "Rearrange Library and Inbox": (
        "How the library and the Inbox are laid out: folders first, folders "
        "only, podcasts without folders or everything together; how podcasts "
        "and folders are ordered; whether folders start open; what the counts "
        "say; and whether the Inbox lists folders first. Each choice takes "
        "effect as you make it, and Close keeps them all."
    ),
    "Watched Folder Settings": (
        "How one watched folder behaves: its name in Personal Audio, whether "
        "Cast copies, moves or plays your files where they are, what a new file "
        "does when it arrives, what you hear, the shortest recording worth "
        "bringing in, its speed, and which kinds of audio file it takes."
    ),
    "Places": (
        "The order of the places in the main window, and which of them it "
        "shows. Up and Down move a place, Hide and Show take it out of the "
        "list or put it back, Rename gives it your own name, and Reset "
        "restores the shipped order. Hiding a place never removes what is in it."
    ),
    "QUILL Cast Preferences": (
        "Everything that is not about one podcast, in nine sections: when Cast "
        "opens, playing, fetching, the Inbox, the library, chapters, telling you, "
        "the window, and data. The shared defaults here are what every podcast follows until "
        "Settings for This Podcast says otherwise. Save writes only what you changed."
    ),
    "Rename Place": (
        "Your own name for a place in the main window. Leave it as shipped, or "
        "blank, to keep the shipped name; nothing in the place changes."
    ),
    "Save Lineup": (
        "A name for the Play Queue's current order, so Apply Lineup can put it "
        "back later. Saving never changes the queue itself."
    ),
    "Mark All as Played": (
        "Confirm marking every episode listed as played. It says how many "
        "rows this touches before it does anything, and it changes only the "
        "played mark -- no file is deleted."
    ),
    "Move to Folder": (
        "Choose the folder to file into, or make a new one. Folders are "
        "yours to invent, and filing changes nothing about what is "
        "downloaded or played."
    ),
    "Year in Review": (
        "Your listening year as a short report: the shows you gave the most "
        "time to, how many episodes you finished, and when you listened. It "
        "is built from your own local history."
    ),
    "Sound Enhancements": (
        "Bass, middle and treble, Even Out Volume and Smart Speed, for the "
        "podcast that is playing or for every podcast. Apply puts them into "
        "effect and the window stays open, so you can listen and adjust again."
    ),
    "About This Episode": (
        "Everything the feed says about one episode -- people, links, "
        "chapters, transcripts, funding -- as reviewable, copyable text. "
        "What is missing here is missing from the feed, not hidden by Cast."
    ),
    "Folder Settings": (
        "Settings that apply to every show in one folder: how it is checked, "
        "how much is kept, and what happens when an episode finishes. A show "
        "with its own answer keeps it; the folder answers for the rest."
    ),
    # -- the first-run screens ---------------------------------------------------
    "Welcome to QUILL Cast": (
        "One screen for a first launch: where you would like to land each time "
        "Cast opens, whether to hear a tip now and then, and Add Your First "
        "Podcast. Nothing here is a setting you can get wrong; Skip, or Escape, "
        "leaves at once, and Preferences changes where you land later."
    ),
    "Episode Filter Rule": (
        "One rule inside a podcast's Episode Filters: a title pattern, a "
        "minimum length, and any more tests -- show notes, people, type, age, "
        "season or number -- with every test or any one having to match. Try It "
        "says what the rule catches among the newest episodes. A "
        "rule is a label plus a test; it decides nothing until the filter "
        "itself is saved, and it never deletes an episode."
    ),
    "Episode Filter Test": (
        "One test inside an Episode Filter rule: what it looks at -- the "
        "title, the show notes, the people on the episode, its type, length, "
        "age, season or number -- how to compare, and the value. Words, "
        "wildcards and regular expressions all work on text."
    ),
}

# Release channels: the shared windows (quill/ui/updates) take their titles and
# purposes from one place, so a title can never ship without its F1 paragraph.
from quill.core.updater.wording import window_titles as _channel_windows  # noqa: E402

PURPOSES.update(_channel_windows("QUILL Cast"))

#: Purposes for windows whose titles carry live data, matched by prefix.
PREFIX_PURPOSES: tuple[tuple[str, str], ...] = (
    (
        "About ",
        "What AI help said, read only, to review at your own pace. Copy puts it on the clipboard. "
        "AI can be wrong, so check anything that matters.",
    ),
    (
        "Is ",
        "What AI help said, read only, to review at your own pace. Copy puts it on the clipboard. "
        "AI can be wrong, so check anything that matters.",
    ),
    (
        "Summary of ",
        "What AI help said, read only, to review at your own pace. Copy puts it on the clipboard. "
        "AI can be wrong, so check anything that matters.",
    ),
    (
        "Schedule for",
        "When this podcast -- or every podcast -- is looked at for new episodes: "
        "manually only, every so often, at set times, around when it usually "
        "publishes, or on the publisher's own hint. Checking never downloads "
        "audio by itself, and Save says the schedule back in one sentence.",
    ),
    (
        "Tidy Episode Titles",
        "Patterns removed from this podcast's episode titles when they are "
        "shown and spoken -- a repeated 'Ep. 412 -' that starts every row and "
        "ruins skimming by first letter. Preview shows exactly which of the 50 "
        "newest titles would change. The feed's own titles are never altered "
        "and no episode is renamed.",
    ),
    (
        "Skip Chapters",
        "Chapter titles this podcast should jump over as it plays -- an advert "
        "break or sponsor read the publisher marked. Exact, where skipping a "
        "number of seconds is a guess. Nothing is removed from the episode.",
    ),
    (
        "Labels",
        "Your own words for this podcast, as many as you like. A folder is one "
        "home and a label is not a home at all: labelling never moves a "
        "podcast, and a smart playlist can ask for a label the way it asks for "
        "a folder.",
    ),
    (
        # Titled "Episode Filters -- <Show>". Ahead of the settings editors
        # only for readability; the prefixes do not overlap, and the rule
        # editor's own title ("Episode Filter Rule", no plural) is answered
        # exactly in PURPOSES above rather than by this prefix.
        "Episode Filters",
        "The rules that decide where this podcast's new episodes go: keep "
        "everything except what a rule matches, or keep only what one "
        "matches. Preview tries the rules against the 50 newest episodes you "
        "already have and changes nothing. A filtered episode is never "
        "deleted -- it stays in this podcast's episode list, played mark, "
        "position and download intact; it simply does not reach your Inbox "
        "or the Play Queue by itself.",
    ),
    (
        # The three single-setting editors are titled "<Setting> -- <Show>",
        # so they are matched by prefix; each carries its own sentence on the
        # control itself (single_settings.SingleSetting.help).
        "Episodes to Keep",
        "How many downloaded episodes of this one podcast to keep before the "
        "oldest are deleted. Zero keeps all of them, and it is the downloaded "
        "audio only -- nothing leaves the episode list.",
    ),
    (
        "Queue Expiry",
        "How long this one podcast's episodes wait in the Play Queue before "
        "they drop out. Zero means they wait indefinitely. Dropping out of "
        "the queue does not delete an episode or mark it played.",
    ),
    (
        "Playback Speed",
        "How fast this one podcast plays, remembered between its episodes, so "
        "a host who talks slowly stays sped up without setting it each time.",
    ),
    (
        "Review Chapters",
        "The chapters Cast worked out for this episode, before they are "
        "kept: rename one, drop one that is wrong, and save. Chapters the "
        "feed supplied are never guessed at -- this window appears only for "
        "episodes that arrived without them.",
    ),
    (
        "Chapters",
        "The chapter list of this episode. Enter jumps straight to the "
        "highlighted chapter; the player keeps playing from there.",
    ),
    (
        "My Notes",
        "Your own notes on this episode, each anchored to the moment you "
        "wrote it. Enter jumps playback to a note's position, and a note can "
        "be shared as text with its timestamp.",
    ),
    (
        "Now Playing",
        "The episode that is playing, as a console you can stay in: the "
        "position as a slider, the transport buttons, speed, volume and the "
        "sleep timer, the chapters with the playing one marked, the show notes "
        "you can read by heading and link, and a note of your own. Ctrl+1 "
        "returns to the library; Ctrl+2 comes back here.",
    ),
    (
        "Links in These Notes",
        "Every link in the notes, in order, each row its title and then where "
        "it goes. Enter opens one in your browser; the buttons copy an address, "
        "a title with its address, or every address at once.",
    ),
    (
        "Find",
        "Type what to find in the notes; the number of matches is said and the "
        "first is selected. F3 finds the next.",
    ),
    (
        "Transcript",
        "The episode's transcript, a line per caption, to read along. Enter on "
        "a line plays from there while this episode is playing; Ctrl+F finds; "
        "Links lists every address in it. Escape returns to where you were.",
    ),
    (
        "Show Notes",
        "The notes the show published with this episode, as reviewable, "
        "copyable text -- links, guests, timestamps. A timestamp here is "
        "live: Enter on one moves playback to it.",
    ),
    (
        "Preview",
        "This show before you follow it: what it is about, and its most "
        "recent episodes. Nothing joins your library until you say so, and "
        "you can play an episode from here to try it first.",
    ),
    (
        "Settings for",
        "Settings for this show alone: how often it is checked, how many "
        "episodes are kept, whether new ones download by themselves, the "
        "speed it plays at, and what to skip at the start and end. Anything "
        "left alone follows your general Podcast Settings.",
    ),
    (
        "About This Episode",
        "Everything the feed says about one episode -- people, links, "
        "chapters, transcripts, funding -- as reviewable, copyable text.",
    ),
    (
        "Folder Settings",
        "Settings that apply to every show in this folder. A show with its "
        "own answer keeps it; the folder answers for the rest.",
    ),
    (
        "Move",
        "Choose the folder to file into, or make a new one. Folders are "
        "yours to invent, and filing changes nothing about what is "
        "downloaded or played.",
    ),
    (
        "File",
        "Choose the Inbox folder to file into, or make a new one. Filing "
        "moves the row out of the Inbox list; it deletes nothing.",
    ),
    (
        "Help:",
        "This is the help window itself: the purpose of the window you were "
        "in, then the control you were on. Escape returns you to it.",
    ),
)

#: The honest fallback for a surface the catalogue does not know. The gate
#: keeps this from being reachable from any surface in the podcast tree; it
#: exists so a Quillin-contributed or brand-new window still answers F1 with
#: something true rather than nothing.
GENERIC_PURPOSE = (
    "A QUILL Cast window. Tab moves between its controls, Escape closes it, "
    "and F1 on any control explains that control."
)


def purpose_for_title(title: str) -> str:
    """The purpose paragraph for a window titled *title* (never empty)."""
    stripped = title.strip()
    exact = PURPOSES.get(stripped)
    if exact:
        return exact
    for prefix, purpose in PREFIX_PURPOSES:
        if stripped.startswith(prefix):
            return purpose
    return GENERIC_PURPOSE


def is_known_title(title: str) -> bool:
    """True when *title* resolves to an authored purpose (the gate's check)."""
    stripped = title.strip()
    if stripped in PURPOSES:
        return True
    return any(stripped.startswith(prefix) for prefix, _p in PREFIX_PURPOSES)
