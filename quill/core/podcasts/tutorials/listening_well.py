"""QUILL Cast, track 3: listening well.

Five lessons about the hour itself rather than the library: skipping the parts
you did not come for, shaping the sound, keeping a moment, reading what the
feed published, and finding out how much of your life this has taken.
"""

from __future__ import annotations

from quill.core.tutorials.model import Step, Tutorial

TUTORIALS: tuple[Tutorial, ...] = (
    Tutorial(
        slug="chapters-and-skipping",
        title="Chapters, and skipping the parts you did not come for",
        track="listening",
        minutes=6,
        surfaces=("Chapters", "QUILL Cast"),
        summary=(
            "Where chapters come from, why the list says which, and how to make "
            "an advert break disappear for good."
        ),
        steps=(
            Step(
                title="Open the chapter list",
                body=(
                    "Cast looks for chapters in three places, cheapest first: the "
                    "feed's own chapters document, markers inside the downloaded "
                    "file, and the timestamps published in the show notes -- the "
                    "familiar 00:12:34 Topic lines."
                ),
                keys=("Alt+E",),
                hear="The chapters, and the line saying where they came from.",
            ),
            Step(
                title="Notice which kind you have",
                body=(
                    "The list says which of the three it used, so marks worked out "
                    "from show notes are never presented as the publisher's own. "
                    "That distinction matters the moment a mark is a few seconds "
                    "off and you want to know whether to trust it."
                ),
                hear="From the feed, from the file, or from the show notes.",
            ),
            Step(
                title="Mark a chapter to skip",
                body=(
                    "Skip This Chapter marks the advert break, the sponsor read, "
                    "the outro. Playback jumps past it and says Skipping chapter, "
                    "and its name -- so it is never mysterious silence."
                ),
                hear="Skipping chapter: Sponsors.",
            ),
            Step(
                title="Know how consecutive marks behave",
                body=(
                    "Consecutive marked chapters are stepped over together, and "
                    "marking everything to the end simply finishes the episode "
                    "normally -- so auto-advance and delete-after-play still fire, "
                    "rather than leaving the episode dangling."
                ),
                hear="One jump, then the next chapter you kept.",
            ),
            Step(
                title="Skip the intro and outro automatically",
                body=(
                    "Skip Settings holds auto-skip intro and auto-skip outro, per "
                    "show, in seconds. Intro-skip jumps forward on a fresh start "
                    "and never when resuming your saved position; outro-skip ends "
                    "the episode early, exactly as if it had finished naturally."
                ),
                keys=("Alt+E",),
                hear="Each number read back for that show.",
            ),
            Step(
                title="Clear the marks when a show changes",
                body=(
                    "Skip Nothing clears every mark. Worth knowing about when a "
                    "show reorganises its chapters and your old marks start "
                    "skipping the wrong minutes."
                ),
                hear="Every mark cleared.",
            ),
        ),
        closing=(
            "Chapter marks are the difference between a show you tolerate and a "
            "show you enjoy. This is the lesson worth doing on the podcast that "
            "annoys you most."
        ),
        then=("shape-the-sound",),
    ),
    Tutorial(
        slug="shape-the-sound",
        title="Shape the sound",
        track="listening",
        minutes=6,
        surfaces=("Sound Enhancements", "QUILL Cast"),
        summary=(
            "The equalizer, the compressor, Smart Speed and volume boost -- all "
            "live, all per podcast, and all keeping your exact place."
        ),
        steps=(
            Step(
                title="Open Sound Enhancements",
                body=(
                    "A three-band equalizer (bass, mid, treble, each -12 to +12 "
                    "dB), a quick preset that sets all three at once -- Flat, Bass "
                    "Boost, Voice Clarity, Podcast -- a compressor that evens out "
                    "volume, and Smart Speed."
                ),
                keys=("Alt+E",),
                hear="Entered Sound Enhancements.",
            ),
            Step(
                title="Fix the quiet podcast",
                body=(
                    "Voice Clarity plus the compressor is the answer to the show "
                    "recorded in somebody's kitchen. It applies live, on top of "
                    "whatever is playing, so you can hear the change while you make "
                    "it rather than guessing."
                ),
                hear="The audio changing as you apply it.",
            ),
            Step(
                title="Know that it is per podcast",
                body=(
                    "Open it while an episode is playing and you are setting that "
                    "show's own sound; open it with nothing playing and you are "
                    "setting the shared default every other show follows. One badly "
                    "mastered podcast should not cost you the sound of the rest."
                ),
                hear="Whose settings you are editing, said as you open it.",
            ),
            Step(
                title="Trim the silence as it plays",
                body=(
                    "Smart Speed trims the silence between words and sentences "
                    "while playing. It is reversible and live, on any episode, any "
                    "time -- distinct from the one-time trim Downloads can do to a "
                    "saved file."
                ),
                hear="Smart Speed on, and the pauses shortening.",
            ),
            Step(
                title="Understand the brief reconnect",
                body=(
                    "Turning enhancement on or off restarts the filter at your "
                    "exact position, so you never lose your place. Pausing and "
                    "resuming work normally throughout, and the seek bar still "
                    "works while enhanced."
                ),
                hear="A moment's gap, then the same words you were on.",
                note=(
                    "All of this needs FFmpeg. Without it, playback continues "
                    "unfiltered and Cast tells you why rather than silently doing "
                    "nothing -- see Help > Media Tools."
                ),
            ),
        ),
        closing=(
            "The volume boost respects the Sleep Timer's restore volume, which is "
            "the kind of detail you only notice when it is missing."
        ),
        then=("keep-a-moment",),
    ),
    Tutorial(
        slug="keep-a-moment",
        title="Keep a moment, and take notes",
        track="listening",
        minutes=5,
        surfaces=("Bookmarks", "QUILL Cast"),
        summary=(
            "Notes that jump you back to the second they were written, bookmarks "
            "shared with Quill Radio, and a way to hand somebody the exact moment "
            "you mean."
        ),
        steps=(
            Step(
                title="Write a note at the moment it happens",
                body=(
                    "Add Episode Note timestamps the playing moment. Enter on a "
                    "note in the list jumps playback back to it, which is what "
                    "makes a note different from something you wrote in a text "
                    "file."
                ),
                keys=("Alt+E",),
                hear="The note saved, with its time.",
            ),
            Step(
                title="Bookmark where you are",
                body=(
                    "Bookmark This Moment marks your place in one keystroke, with "
                    "no note required -- I was here is the commonest kind of "
                    "bookmark, and having to type a sentence for it is how a "
                    "bookmark does not get made."
                ),
                command="app.bookmark_moment",
                hear="Bookmarked, and what it was in.",
            ),
            Step(
                title="Find them again",
                body=(
                    "The Bookmarks list holds them all, with Edit Note, Share, "
                    "Delete and Export. The list is shared with Quill Radio: a "
                    "bookmark made in either app is in the other, with no account "
                    "and no sync service."
                ),
                command="app.bookmarks",
                hear="Entered Bookmarks, then the list.",
            ),
            Step(
                title="Hand somebody the exact moment",
                body=(
                    "Sharing where you are copies the place, the episode and the "
                    "show together -- the note on its own is a fragment nobody can "
                    "act on. It is what to paste into a message that says listen "
                    "to this bit."
                ),
                keys=("Shift+F10",),
                hear="Copied, and what went with it.",
            ),
            Step(
                title="Carry your place to another device",
                body=(
                    "Your position in an episode is shared with Quill Radio on this "
                    "computer, and Cast can hand a place to another device. The "
                    "later decision wins rather than the furthest through: if you "
                    "skipped to the outro and went back, the middle is where you "
                    "are."
                ),
                hear="Picking up where you left off, and the time.",
            ),
        ),
        closing=(
            "Notes for what you thought, bookmarks for where you were. Both "
            "outlive the episode, which is the point."
        ),
        then=("what-the-feed-published",),
    ),
    Tutorial(
        slug="what-the-feed-published",
        title="Read what the feed published",
        track="listening",
        minutes=4,
        surfaces=("QUILL Cast", "Podcast Manager"),
        summary=(
            "Transcripts, show notes, links and everything else a publisher sends "
            "along with the audio -- reachable without playing anything."
        ),
        steps=(
            Step(
                title="Open a transcript when there is one",
                body=(
                    "When a feed provides a transcript (Podcasting 2.0, in VTT, SRT "
                    "or JSON), Cast can open it or save it to a file, and caches it "
                    "so reopening is instant. Reading is often faster than "
                    "listening when you are looking for one fact."
                ),
                keys=("Shift+F10",),
                hear="The transcript window, with the episode named.",
            ),
            Step(
                title="Choose between several",
                body=(
                    "Some feeds publish more than one -- a machine transcript and a "
                    "corrected one, or several languages. Cast offers the choice "
                    "rather than picking for you, because which is better depends "
                    "on what you are doing with it."
                ),
                hear="The transcripts on offer, described.",
            ),
            Step(
                title="Read the episode's own notes",
                body=(
                    "About This Episode holds what the publisher wrote: the "
                    "summary, the links, the guest names, and often the timestamps "
                    "the chapter list was worked out from."
                ),
                keys=("Alt+E",),
                hear="The notes, as text you can arrow through and copy.",
            ),
            Step(
                title="Look at a show before subscribing",
                body=(
                    "You can open a podcast and read its episodes without "
                    "following it. That is how you decide -- a description and a "
                    "star rating tell you much less than three episode titles do."
                ),
                hear="The show's episodes, without a subscription.",
            ),
            Step(
                title="Know what Cast will not do",
                body=(
                    "Cast never generates a transcript from audio. That stays in "
                    "full QUILL, which has the speech engines for it. What you get "
                    "here is what the publisher published."
                ),
                hear="Nothing: this is the fact that saves you looking for a button.",
            ),
        ),
        closing=(
            "Everything here is the publisher's own work, offered as text. None "
            "of it needs the episode to be playing."
        ),
        then=("how-much-did-i-listen",),
    ),
    Tutorial(
        slug="how-much-did-i-listen",
        title="How much did I actually listen?",
        track="listening",
        minutes=4,
        surfaces=("Listening Statistics",),
        summary=(
            "Time listened, what faster playback bought you, a year in review, "
            "and the numbers deliberately left out."
        ),
        steps=(
            Step(
                title="Open the statistics",
                body=(
                    "This week, this month, this year or all time: how long you "
                    "listened, how much extra content faster playback bought you, "
                    "how many episodes you finished, and a breakdown by podcast, "
                    "most-listened first."
                ),
                command="podcasts.statistics",
                hear="Entered Listening Statistics, then the totals.",
            ),
            Step(
                title="Notice how the durations read",
                body=(
                    "Three hours, 47 minutes -- as language, never as a clock face, "
                    "because a screen reader reads 3:47:00 as a time of day. The "
                    "whole readout is a text field you arrow through and can copy."
                ),
                hear="Durations spoken as hours and minutes.",
            ),
            Step(
                title="Read a year in a few sentences",
                body=(
                    "Year in Review is prose rather than a dashboard: how long, "
                    "what you listened to most and what share of the year each show "
                    "was, your busiest month, and how many days you listened on. A "
                    "table read aloud is a list of numbers with their meanings "
                    "three columns away."
                ),
                hear="A few sentences you can arrow through, copy or save.",
            ),
            Step(
                title="Decide whether streaks exist",
                body=(
                    "Listening streaks are off unless you ask for them. A streak is "
                    "a nudge, and a nudge nobody asked for is pressure. When they "
                    "are on, a run that ended yesterday is still current -- your "
                    "streak is never reported as broken before you have had a "
                    "chance to listen today."
                ),
                keys=("Alt+S",),
                hear="The setting read back.",
            ),
            Step(
                title="Decide how long the log lives",
                body=(
                    "Do not keep one, 30 days, 90 days (the default), a year, or "
                    "forever. Choosing not to keep one stops the writing rather "
                    "than deleting afterwards, which is what somebody choosing it "
                    "asked for. The log never leaves this computer either way."
                ),
                hear="The retention read back.",
            ),
            Step(
                title="Take it away, or delete it",
                body=(
                    "Export CSV saves every session for a spreadsheet. Clear "
                    "Statistics deletes the log and nothing else -- not your "
                    "positions, not your subscriptions."
                ),
                hear="The file written, or the log cleared.",
            ),
        ),
        closing=(
            "One number is deliberately absent: time saved by Smart Speed. The "
            "silence-trimming path cannot honestly report how much it dropped, "
            "and an invented figure would be worse than none."
        ),
    ),
)
