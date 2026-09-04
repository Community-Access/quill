"""QUILL Cast, track 5: one podcast at a time.

Five lessons about the thing that turned out to be the whole problem: **one
podcast is not like the others.** Keep the newest three ready is right for a
daily news show and wrong for a weekly three-hour interview. Check hourly is
right for the news show and wasteful for an archive that stopped publishing in
2019. Say the podcast's name in every row is right for a mixed list and noise
inside that podcast's own.

The order is the order somebody meets the problem in. First how settings
actually resolve, because everything else depends on knowing that a folder is a
real level and that leaving a control alone means something. Then what arrives
and when. Then the two that only matter if you listen rather than look -- what
a row says, and how a title reads. Then the rules for the episodes you did not
want at all.

Track 4 (Making it yours) is about arranging a library. This one is about
teaching one podcast in it to behave differently from the rest.
"""

from __future__ import annotations

from quill.core.tutorials.model import Step, Tutorial

TUTORIALS: tuple[Tutorial, ...] = (
    Tutorial(
        slug="how-settings-resolve",
        title="Shared defaults, folders, and one podcast",
        track="per-podcast",
        minutes=7,
        surfaces=("Podcast Settings", "Podcasts"),
        summary=(
            "How a setting is decided: your shared default, then the folder, "
            "then the podcast -- and why leaving a control alone is a real "
            "answer rather than an absence of one."
        ),
        steps=(
            Step(
                title="Start where everything starts",
                body=(
                    "Podcast Settings holds the shared defaults every podcast "
                    "follows until something nearer disagrees. Speed, retention, "
                    "automatic downloads, the Inbox rules, where downloads land. "
                    "Set the answer that is right for most of your library here "
                    "and you will rarely need the other two levels."
                ),
                keys=("Alt+S",),
                hear="Entered Podcast Settings.",
            ),
            Step(
                title="Learn the chain",
                body=(
                    "A setting is decided by the nearest level that has an "
                    "opinion: your shared default, then any folder the podcast is "
                    "in, outermost first, then the podcast itself. Each level "
                    "stores only the settings it actually has an opinion about, "
                    "so the levels above it reach through everything else."
                ),
                hear="Nothing yet -- this one is a fact to carry into the next step.",
                note=(
                    "Earlier versions could not do this. Giving one podcast its "
                    "own answer to one setting quietly copied every other setting "
                    "it had, frozen at that day's defaults -- so changing a shared "
                    "default later reached every podcast except the ones you had "
                    "bothered to adjust. Your library is converted on first "
                    "launch, keeping only the values that genuinely differed."
                ),
            ),
            Step(
                title="Set a whole folder at once",
                body=(
                    "Folder Settings, on a folder's context menu in the Podcast "
                    "Manager, sets values for everything filed under it. It is a "
                    "real level now, not a bulk edit: a podcast you move into the "
                    "folder next year inherits it, and one you move out stops."
                ),
                keys=("Shift+F10",),
                hear="The folder named, and how many podcasts it covers.",
            ),
            Step(
                title="Open one podcast's own settings",
                body=(
                    "Settings for This Podcast, on any show's context menu, holds "
                    "about seventy settings for that one show. It shows them one "
                    "category at a time -- Arrival, Playback, Storage, "
                    "Announcements, Curation -- because seventy controls in a "
                    "single list is not a list anybody can work through by ear."
                ),
                keys=("Shift+F10",),
                hear="The podcast named, then the category chooser.",
            ),
            Step(
                title="Ask any control where its value came from",
                body=(
                    "Every control shows the value actually in force, inherited or "
                    "not. Press F1 on one and the help ends with where it came "
                    "from: every 60 minutes, from the folder News. That sentence "
                    "is the difference between reading a number and understanding "
                    "it."
                ),
                keys=("F1",),
                hear="What the setting does, then the level that decided it.",
            ),
            Step(
                title="Change one thing, and only one thing",
                body=(
                    "Change a single control and press OK. Only what you changed "
                    "becomes this podcast's own answer; everything you left alone "
                    "keeps following its folder and your shared defaults. Cast "
                    "says how many settings it saved."
                ),
                check="settings-changed",
                hear="Saved 1 setting, and the value read back in words.",
            ),
            Step(
                title="Find out what you have changed",
                body=(
                    "What Have I Changed? lists only the settings this podcast "
                    "answers for itself, out of all of them. It is the fastest way "
                    "to find out why one podcast behaves differently from the "
                    "rest, and it changes nothing by being opened."
                ),
                hear="A count, then one line per setting with the level that set it.",
            ),
            Step(
                title="Put one back, or all of them",
                body=(
                    "Where a podcast has an answer of its own, a Follow button sits "
                    "beside that control; pressing it drops that one answer so the "
                    "podcast inherits again. Follow the Shared Defaults drops every "
                    "one of them at once, and says how many it dropped."
                ),
                hear="The setting following the folder or the shared default again.",
            ),
        ),
        closing=(
            "Most people set three things globally, one or two on a folder, and "
            "one on a single podcast, forever. The point of the chain is that you "
            "can change your mind about the first without hunting down the rest."
        ),
        then=("what-arrives-when",),
    ),
    Tutorial(
        slug="what-arrives-when",
        title="Decide what arrives, and when",
        track="per-podcast",
        minutes=6,
        surfaces=("Podcasts",),
        summary=(
            "A daily briefing and a weekly three-hour interview want opposite "
            "answers about checking, downloading and queueing. Give them "
            "opposite answers."
        ),
        steps=(
            Step(
                title="Give one podcast its own cadence",
                body=(
                    "Check subscribed feeds every, under Arrival, is per podcast. "
                    "A daily news show can check hourly while a weekly show checks "
                    "daily and a dormant archive is never checked at all. One "
                    "cadence for three hundred podcasts is either wasteful or "
                    "late."
                ),
                hear="The cadence read back in words, and where it came from.",
                note=(
                    "Quill Radio shares the work rather than the setting: whichever "
                    "app checks a feed says so, and the other stays quiet inside "
                    "the same interval. Two apps, one job, never two requests."
                ),
            ),
            Step(
                title="Collect a back catalogue once",
                body=(
                    "When I subscribe, also fetch answers a different question from "
                    "the automatic download count, which only ever looks forward. "
                    "Nothing, the newest few, the last few months, or everything -- "
                    "and it happens once, at the moment you subscribe."
                ),
                hear="The choice read back, and how many episodes it queued.",
            ),
            Step(
                title="Move the bytes when it suits you",
                body=(
                    "Only download automatically after and before set an off-peak "
                    "window, on a 24-hour clock, and it wraps midnight so 22 to 6 "
                    "means what you would expect. It never delays a download you "
                    "asked for by name, and leaving both hours the same means "
                    "there is no window at all."
                ),
                hear="The window read back, or that there is none.",
            ),
            Step(
                title="Start a series at the beginning",
                body=(
                    "Auto-Queue takes the sets which end of the catalogue "
                    "Auto-Queue works from. Newest episode is the news-show "
                    "assumption; oldest unplayed episode is how you work through a "
                    "finished series in the order it was meant to be heard."
                ),
                check="queue-grew",
                hear="The episode queued, by name.",
            ),
            Step(
                title="Keep transcripts for the shows worth searching",
                body=(
                    "Fetch transcripts, under Arrival, decides when a podcast's "
                    "transcripts are collected. A cached transcript is what lets "
                    "Search Everywhere find a sentence rather than a title -- "
                    "worth it for a talk show, pointless for a music show."
                ),
                hear="The policy read back.",
                note=(
                    "The last choice will also transcribe an episode itself when "
                    "the feed carries none. That is minutes of work per episode, "
                    "which is exactly why it is per podcast and off by default."
                ),
            ),
            Step(
                title="Run the maintenance and hear the result",
                body=(
                    "Run Maintenance Now applies the ageing rules, the caps and "
                    "the expiry immediately rather than waiting for the next "
                    "refresh, and says exactly what it did. It is the fastest way "
                    "to see whether the rules you just set say what you meant."
                ),
                command="podcasts.run_maintenance",
                hear="What was trimmed, expired or deleted, counted.",
            ),
        ),
        closing=(
            "Arrival is four questions -- how often, how much, when, and in which "
            "order -- and every one of them has a different right answer for a "
            "daily briefing than for a weekly interview."
        ),
        then=("what-a-row-says",),
    ),
    Tutorial(
        slug="what-a-row-says",
        title="Decide what every row tells you",
        track="per-podcast",
        minutes=6,
        surfaces=("Podcasts", "Podcast Settings"),
        summary=(
            "A screen reader reads every row of every list out loud, in full. "
            "Which parts of a row are worth hearing is yours to decide -- and it "
            "is not the same for every podcast."
        ),
        steps=(
            Step(
                title="Hear what a row says now",
                body=(
                    "Arrow down an episode list and listen to a whole row. By "
                    "default it reads the title, the date, the length and whether "
                    "it is downloaded. Notice which of those you already knew "
                    "before it was said."
                ),
                keys=("Down arrow",),
                hear="Title, date, length, and downloaded or streaming.",
            ),
            Step(
                title="Choose what comes first",
                body=(
                    "Read each row starting with offers the episode title, the "
                    "podcast's name, or the date. Whichever comes first is what "
                    "you can skim by first letter, and which one that should be "
                    "depends entirely on how you look for things."
                ),
                hear="The order read back.",
                note=(
                    "The podcast's name is never added inside that podcast's own "
                    "episode list, whatever the switch says. The name is the "
                    "window you are already standing in."
                ),
            ),
            Step(
                title="Turn off what you already know",
                body=(
                    "Say when it was published is worth switching off for a show "
                    "that puts the date in every title -- otherwise you hear it "
                    "twice on every row. It changes what a row says, never the "
                    "order the list is in."
                ),
                hear="Rows without the date, and shorter for it.",
            ),
            Step(
                title="Ask for time remaining instead of length",
                body=(
                    "Say how long it is offers the whole length or how much is "
                    "left. When you are choosing what to play in the twenty "
                    "minutes you have, how much is left is the more useful of the "
                    "two by a wide margin."
                ),
                hear="12 minutes left, on an episode you have started.",
            ),
            Step(
                title="Add the things Cast knew and never said",
                body=(
                    "Say when it has chapters or a transcript is off by default "
                    "and worth turning on for a podcast you skip around in. Say "
                    "the season and episode number is worth it for a serial. "
                    "Neither fetches anything to find out."
                ),
                hear="Rows ending with chapters and transcript, where there are any.",
            ),
            Step(
                title="Read the description, carefully",
                body=(
                    "Read the episode's description offers off, a sentence of it, "
                    "or all of it. Off is the default for a reason: a description "
                    "in every row is the one setting that can make a forty-row "
                    "list unreadable. A sentence is often exactly right."
                ),
                hear="Each row ending with a sentence of its show notes.",
            ),
            Step(
                title="Set it differently for one podcast",
                body=(
                    "All of it is per podcast as well as global, under "
                    "Announcements in Settings for This Podcast. The interview "
                    "show whose titles are just guest names wants the description; "
                    "the daily briefing wants nothing but the date."
                ),
                check="settings-changed",
                hear="Saved, and the setting read back in words.",
            ),
        ),
        closing=(
            "There is no right answer here, which is exactly why it is a setting. "
            "The wrong answer is the one where every row says the same three "
            "things you already knew."
        ),
        then=("read-it-your-way",),
    ),
    Tutorial(
        slug="read-it-your-way",
        title="Fix a podcast that reads badly",
        track="per-podcast",
        minutes=6,
        surfaces=("Podcasts",),
        summary=(
            "Two settings for the two ways a podcast can be exhausting to listen "
            "to a list of: a repeated prefix on every title, and a name your "
            "speech engine cannot say."
        ),
        steps=(
            Step(
                title="Notice the prefix",
                body=(
                    "Arrow down a podcast that numbers its episodes in the title "
                    "-- Ep. 412 -, MyShow Presents:, [Bonus]. Every row starts "
                    "with the same words, so jumping by first letter finds "
                    "nothing: the part that differs is never where the reader "
                    "starts."
                ),
                keys=("Down arrow",),
                hear="The same opening words on every row.",
            ),
            Step(
                title="Open the title tidier",
                body=(
                    "Tidy episode titles, under Announcements in Settings for This "
                    "Podcast, opens a list of patterns to remove. Add one with the "
                    "same wildcards Episode Filters uses: a star is any run of "
                    "text and a question mark is one character."
                ),
                keys=("Shift+F10",),
                hear="The list, and what it does not do -- no episode is renamed.",
            ),
            Step(
                title="Write a pattern and preview it",
                body=(
                    "For Ep. 412 - the pattern is Ep. * - at the start. Preview "
                    "tries it against the 50 newest titles and lists only the ones "
                    "that would change, before and after. Nothing is altered by "
                    "pressing it."
                ),
                hear="How many of the 50 newest titles would change.",
                note=(
                    "A rule can never empty a title. If a pattern would remove "
                    "everything, the title is left exactly as the feed published "
                    "it -- a row that reads as nothing at all is worse than one "
                    "that reads as noise."
                ),
            ),
            Step(
                title="Save it and listen again",
                body=(
                    "Save, and arrow the list again. The rows now begin with the "
                    "part that differs, so first-letter navigation works. The "
                    "feed's own titles are untouched, and Rename is still a "
                    "separate verb that really does rename."
                ),
                check="settings-changed",
                hear="Rows starting with the subject rather than the number.",
            ),
            Step(
                title="Fix a name your speech engine mangles",
                body=(
                    "Say this podcast's name as takes one spelling used only when "
                    "the name is spoken -- for an initialism, a word from another "
                    "language, or a run of punctuation. Write it the way it should "
                    "sound, not the way it is spelled."
                ),
                hear="The podcast named the way you wrote it.",
            ),
            Step(
                title="Check where it changed and where it did not",
                body=(
                    "The spoken name is used wherever Cast says the podcast out "
                    "loud. Everywhere it is written -- the tree, the window title, "
                    "an export -- the podcast keeps its own name, because that is "
                    "what the publisher called it."
                ),
                hear="The spoken form when an episode arrives; the real name in the tree.",
            ),
        ),
        closing=(
            "Both of these are small, and both of them are worth minutes a day to "
            "somebody who hears every row. Neither changes a single thing about "
            "what is downloaded, played or kept."
        ),
        then=("episode-filters",),
    ),
    Tutorial(
        slug="tell-me-your-way",
        title="Be told about a podcast on your terms",
        track="per-podcast",
        minutes=6,
        surfaces=("Podcasts", "Quiet Hours"),
        summary=(
            "Which podcasts may interrupt you, which are merely counted, which "
            "say nothing at all -- and what happens when one goes quiet or its "
            "feed starts failing."
        ),
        steps=(
            Step(
                title="Choose how loudly one podcast speaks",
                body=(
                    "New episodes of this podcast are offers urgent, normal or "
                    "quiet. Urgent names the episodes and interrupts; normal is "
                    "counted in the shared summary; quiet says nothing at all. A "
                    "quiet podcast still downloads, queues and files exactly as it "
                    "would."
                ),
                check="settings-changed",
                hear="The choice read back.",
                note=(
                    "Being told about every feed is being told about nothing. Two "
                    "or three urgent podcasts is a useful setting; twenty is a "
                    "library that talks over you."
                ),
            ),
            Step(
                title="Cap how much Cast may say",
                body=(
                    "At most this many spoken announcements an hour, in Podcast "
                    "Settings, is the ceiling. Anything above it is folded into "
                    "the shared summary rather than dropped -- nothing is lost, it "
                    "is said once instead of twenty times."
                ),
                hear="The ceiling read back, or that there is none.",
            ),
            Step(
                title="Let one podcast through quiet hours",
                body=(
                    "Quiet Hours stops the app speaking on its own between the "
                    "times you set. May speak during quiet hours, on one podcast, "
                    "is the exception for a live or news feed you asked to be told "
                    "about. It affects that announcement and nothing else."
                ),
                command="app.quiet_hours",
                hear="The quiet window read back.",
            ),
            Step(
                title="Give a podcast its own sound",
                body=(
                    "Play this sound when it publishes takes an event from your "
                    "active sound pack. It is played instead of the shared "
                    "new-episode sound, not as well, so one podcast becomes "
                    "distinguishable rather than merely louder."
                ),
                hear="That podcast's own sound when an episode arrives.",
            ),
            Step(
                title="Be told when a podcast stops",
                body=(
                    "Tell me if this podcast goes quiet for says something when a "
                    "podcast you follow publishes nothing for that many weeks. A "
                    "podcast that ends does so silently, and the absence is "
                    "exactly the thing nobody notices."
                ),
                hear="The podcast named, and how long it has been silent.",
                note=(
                    "It never unsubscribes you and never stops checking. It is "
                    "said once, and again only if the podcast comes back and then "
                    "stops again."
                ),
            ),
            Step(
                title="Be told when a feed is failing",
                body=(
                    "Tell me after this many failed checks speaks up after a run "
                    "of failures. Cast keeps trying either way, and the sentence "
                    "says so, because a feed that has failed reads as one Cast has "
                    "given up on."
                ),
                command="app.recent_problems",
                hear="The failures listed, with their reasons.",
            ),
        ),
        closing=(
            "Attention is the scarce thing. Three urgent podcasts, a ceiling on "
            "the rest, and a notice when something goes quiet is a library that "
            "tells you what you need and then stops talking."
        ),
        then=("episode-filters",),
    ),
)
