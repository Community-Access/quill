"""QUILL Cast, track 2: keeping up.

Five lessons about the part of podcasting that is actually hard: not playing
an episode, but deciding which of the four hundred waiting ones you will
play. The Inbox, the Play Queue, automatic downloads and the rules that keep
all three from becoming a second library.
"""

from __future__ import annotations

from quill.core.tutorials.model import Step, Tutorial

TUTORIALS: tuple[Tutorial, ...] = (
    Tutorial(
        slug="what-is-new",
        title="Find out what is new",
        track="keeping-up",
        minutes=5,
        surfaces=("QUILL Cast", "Podcast Manager"),
        summary=(
            "Check every feed at once, have Cast check on its own, and be told by "
            "name about the shows you never skip -- without being told about the "
            "ones you do."
        ),
        steps=(
            Step(
                title="Ask every show at once",
                body=(
                    "Checking for new episodes asks all your feeds in one go, "
                    "rather than one show at a time. It says what it found, counted "
                    "and named, and says nothing at all when it found nothing -- "
                    "because a check that reports silence has stopped being "
                    "information."
                ),
                keys=("Alt+S",),
                hear="What is new, counted and named -- or nothing.",
            ),
            Step(
                title="Read the New Episodes view",
                body=(
                    "Everything that arrived, across every show, in one list. This "
                    "is the view to live in if you follow a lot of shows: it "
                    "answers what is new without your having to remember which "
                    "shows publish on which day."
                ),
                keys=("Ctrl+M",),
                hear="How many new episodes, and from how many shows.",
            ),
            Step(
                title="Have it check on its own",
                body=(
                    "Cast can check on a schedule and at launch. Both start off, on "
                    "purpose: an app that reaches the network on a schedule nobody "
                    "chose is spending somebody else's data allowance."
                ),
                keys=("Ctrl+,",),
                hear="The settings read back.",
            ),
            Step(
                title="Be told about the shows you never skip",
                body=(
                    "Announce New Episodes, per show, names new episodes out loud "
                    "and in braille when the background check finds them, with a "
                    "tray notification. It is per podcast deliberately: being told "
                    "about every feed is being told about nothing."
                ),
                keys=("Shift+F10",),
                hear="The new episodes, by name, for that show only.",
            ),
            Step(
                title="Send one show's episodes straight to the queue",
                body=(
                    "Auto-Queue New Episodes, also per show, sends new episodes "
                    "into the Play Queue on refresh, skipping the Inbox entirely. "
                    "It is for the show you never triage because you always listen."
                ),
                keys=("Shift+F10",),
                hear="The setting read back for that show.",
            ),
            Step(
                title="Know what happens to a re-published episode",
                body=(
                    "Publishers re-issue episodes -- a corrected file, a re-cut. If "
                    "one had been trimmed out of your Inbox it comes back, "
                    "announced as what it is: Episode 42 was re-published by The "
                    "Daily, so it is back in your Inbox. Anything you have played, "
                    "started, queued or filed by hand is left exactly alone."
                ),
                hear="The re-publication, described as a re-publication.",
            ),
        ),
        closing=(
            "A refresh should never argue with a decision you have already made. "
            "That one rule explains most of this lesson."
        ),
        then=("the-inbox", "the-play-queue"),
    ),
    Tutorial(
        slug="the-inbox",
        title="Triage with the Inbox",
        track="keeping-up",
        minutes=6,
        surfaces=("Podcast Manager",),
        summary=(
            "Route shows into the Inbox, file episodes into folders you invent, "
            "and cap the whole thing so it stays a triage surface rather than "
            "becoming a second library."
        ),
        steps=(
            Step(
                title="Understand what it is for",
                body=(
                    "The Inbox triages **episodes**, where the library organises "
                    "**shows**. Route a show to the Inbox and its new episodes land "
                    "there for you to decide about, rather than sitting inside the "
                    "show waiting to be found."
                ),
                keys=("Ctrl+M",),
                hear="The Inbox, with how many episodes are waiting.",
            ),
            Step(
                title="File an episode where you want it",
                body=(
                    "File episodes into your own nested folders. Your first manual "
                    "filing per show is remembered and applied automatically from "
                    "then on -- and Forget reverts that, so a one-off does not "
                    "become a rule you cannot see."
                ),
                keys=("Shift+F10",),
                hear="The folder it went to, and that the rule was remembered.",
            ),
            Step(
                title="Choose which shows arrive here",
                body=(
                    "Which shows go to the Inbox has two answers: only the shows I "
                    "choose (the default), or every show except the ones I exclude. "
                    "The second suits a large subscription list you triage; the "
                    "first suits a few shows you follow closely."
                ),
                keys=("Alt+S",),
                hear="The setting read back -- and the per-show menu item changing to match.",
                note=(
                    "Switching reuses the same per-show mark and reads it the other "
                    "way round, so the menu item on a show becomes Keep This Show "
                    "Out of the Inbox. Nothing moves unless you change the setting."
                ),
            ),
            Step(
                title="Cap it before it becomes a library",
                body=(
                    "Any podcast can keep at most N episodes in the Inbox and drop "
                    "ones older than six hours up to a fortnight. An Inbox holding "
                    "every unplayed episode of every routed show forever is not a "
                    "triage surface."
                ),
                keys=("Shift+F10",),
                hear="The cap read back for that show.",
            ),
            Step(
                title="Know that trimming never deletes",
                body=(
                    "A trimmed episode leaves the Inbox and stays unplayed in its "
                    "show's own list, downloaded file and all. And three kinds are "
                    "never trimmed and do not even count toward the cap: anything "
                    "you started, anything queued, and anything you filed by hand."
                ),
                hear="Nothing: this is the promise that makes a cap safe to set.",
            ),
        ),
        closing=(
            "The Inbox is where episodes wait for a decision. Everything above is "
            "about making sure the decision is yours and the waiting is bounded."
        ),
        then=("the-play-queue",),
    ),
    Tutorial(
        slug="the-play-queue",
        title="Line up what plays next",
        track="keeping-up",
        minutes=6,
        surfaces=("Play Queue", "Podcast Manager"),
        summary=(
            "The Play Queue, how it advances, how to reorder it from the "
            "keyboard, and what happens to something you queued and never got to."
        ),
        steps=(
            Step(
                title="Queue an episode",
                body=(
                    "Play Next puts an episode at the front; Add to Queue puts it "
                    "at the end. The queue auto-advances, survives a restart, and "
                    "is the thing that decides what plays when the current episode "
                    "finishes."
                ),
                keys=("Shift+F10",),
                hear="Queued, and where in the queue it went.",
            ),
            Step(
                title="Open the queue itself",
                body=(
                    "The Play Queue is one keystroke away from the Episode menu as "
                    "well as living in the Manager's tree. Reorder it with Move Up "
                    "and Move Down, or Mark then Move for a long hop."
                ),
                keys=("Alt+E",),
                hear="The queue, in order, with each episode's show.",
            ),
            Step(
                title="Decide what follows an episode",
                body=(
                    "Two switches in Podcast Settings: play the next episode in the "
                    "Play Queue, and when the queue is empty keep going with the "
                    "same podcast. With both off, playback stops at the end of the "
                    "episode you started."
                ),
                keys=("Alt+S",),
                hear="Each setting read back.",
            ),
            Step(
                title="Expire what you never got to",
                body=(
                    "A queued episode you never played is worse than clutter -- the "
                    "queue decides what plays next, so a stale item takes a turn. "
                    "Expire from the queue, per show, removes one that has waited "
                    "longer than a day, a week, a fortnight, a month."
                ),
                keys=("Shift+F10",),
                hear="The expiry rule read back for that show.",
                note=(
                    "There is deliberately no global setting: a daily news show "
                    "wants two days and a weekly long-form show wants two weeks, "
                    "and one number for everything is a number nobody wants."
                ),
            ),
            Step(
                title="Find what expired",
                body=(
                    "Expiring is not deleting. The episode moves to Recently "
                    "Expired and waits seven days keeping its downloaded file, its "
                    "saved position and its place in its show. Restore to the Play "
                    "Queue puts it back with a fresh clock."
                ),
                keys=("Ctrl+M",),
                hear="Recently Expired, and what is in it.",
            ),
            Step(
                title="Group the queue if it is long",
                body=(
                    "The queue can be grouped so one show's episodes cluster "
                    "together, which is the difference between reading a queue and "
                    "auditing one."
                ),
                hear="The queue, re-read in its new shape.",
            ),
        ),
        closing=(
            "Inbox for undecided, queue for decided. The two rules above -- "
            "expiry, and Recently Expired -- are what keep the second list honest."
        ),
        then=("downloads-and-space",),
    ),
    Tutorial(
        slug="downloads-and-space",
        title="Downloads, and the disk they live on",
        track="keeping-up",
        minutes=6,
        surfaces=("Downloads", "Podcast Manager"),
        summary=(
            "Have episodes arrive ready to play, see what they are costing you, "
            "and set the two rules that clear space without ever taking the thing "
            "you are halfway through."
        ),
        steps=(
            Step(
                title="Have new episodes arrive downloaded",
                body=(
                    "Automatically download -- none, the newest 1, 3, 5, 10, or "
                    "every episode -- is the setting that makes new episodes arrive "
                    "ready to play. Any podcast can set its own, and new episodes "
                    "are fetched on subscribe and on every refresh."
                ),
                keys=("Alt+S",),
                hear="How many episodes it started downloading; nothing happens silently.",
            ),
            Step(
                title="Know the two companion switches",
                body=(
                    "Anything you add to the Play Queue downloads too, whatever its "
                    "age -- an episode you queued is one you meant to play. Anything "
                    "routed to the Inbox does not, because the Inbox is a triage "
                    "surface, not a commitment."
                ),
                hear="Each switch read back.",
            ),
            Step(
                title="See what it is costing",
                body=(
                    "Downloads answers how much disk your podcasts are using: the "
                    "total, a breakdown by podcast largest first, and an Unheard "
                    "only filter that tells you how many already-played downloads "
                    "it hid."
                ),
                command="podcasts.downloads",
                hear="The total, then the biggest shows.",
            ),
            Step(
                title="Set the two automatic rules",
                body=(
                    "Delete downloads after N days (overridable per podcast, so one "
                    "archival show can keep everything) and a total storage cap in "
                    "megabytes, which removes already-played downloads oldest first "
                    "when you go over. Both are off to begin with."
                ),
                keys=("Alt+S",),
                hear="Each rule read back.",
            ),
            Step(
                title="Know what the rules will never take",
                body=(
                    "A queued or part-played episode is never removed by either "
                    "rule. That is what makes an automatic cap safe: disk pressure "
                    "is not a reason to throw away the thing you are halfway "
                    "through. It also means a cap can be unreachable, and Cast says "
                    "so rather than pretending."
                ),
                hear="What it could not free, and why.",
            ),
            Step(
                title="Run the rules now",
                body=(
                    "Free Up Space applies both rules immediately and says how many "
                    "bytes came back. Run Housekeeping Now does the full pass -- "
                    "expire stale queue items, sweep Recently Expired, trim the "
                    "Inbox, apply the storage rules -- and reports it all in one "
                    "sentence."
                ),
                command="podcasts.run_maintenance",
                hear="Everything it did, in one sentence.",
            ),
        ),
        closing=(
            "Housekeeping also runs after every feed refresh, so most of the time "
            "this lesson is about a button you will never need to press."
        ),
        then=("playlists-and-lineups",),
    ),
    Tutorial(
        slug="playlists-and-lineups",
        title="Playlists, smart playlists, and the order you listen in",
        track="keeping-up",
        minutes=5,
        surfaces=("Podcast Manager",),
        summary=(
            "Saved episode lists you build by hand, and rule-based ones that "
            "rebuild themselves every time you open them."
        ),
        steps=(
            Step(
                title="Know how a playlist differs from the queue",
                body=(
                    "The Play Queue is transient -- it empties as you listen. A "
                    "playlist is saved and named, and it stays. The pinned views "
                    "are neither: they are fixed questions the app asks for you."
                ),
                keys=("Ctrl+M",),
                hear="The Playlists node, below the Play Queue.",
            ),
            Step(
                title="Build one by hand",
                body=(
                    "New Playlist makes an empty named list, and Add to Playlist on "
                    "any episode's context menu fills it one episode at a time. "
                    "This is the right shape for a list somebody else will listen "
                    "to, or for a course you are working through."
                ),
                keys=("Shift+F10",),
                hear="The playlist created, then each episode added.",
            ),
            Step(
                title="Or describe one and let it fill itself",
                body=(
                    "New Smart Playlist takes rules instead of episodes: which "
                    "shows, episode status, how recent, how long, and how to sort. "
                    "It is re-resolved live every time you open it, so it is never "
                    "out of date."
                ),
                hear="The rules read back, then how many episodes match right now.",
            ),
            Step(
                title="Edit the rules later",
                body=(
                    "Edit Rules, Rename (F2) and Delete are on each playlist's own "
                    "context menu. A smart playlist that returns nothing is telling "
                    "you something about the rules rather than about the shows."
                ),
                keys=("Shift+F10", "F2"),
                hear="The playlist under its new name, or the new rules.",
            ),
            Step(
                title="Save the order you listen in",
                body=(
                    "A lineup is the order you work through things -- the news, "
                    "then the long one, then the funny one. Saving it means you "
                    "stop rebuilding the same queue every morning."
                ),
                hear="The lineup saved, by name.",
            ),
        ),
        closing=(
            "Hand-built for a list somebody chose; smart for a question that "
            "keeps answering itself."
        ),
    ),
)
