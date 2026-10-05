"""QUILL Cast, track 4: one podcast at a time -- and two lessons of track 2.

Two lessons about the thing that turns out to be most of the problem: **one
podcast is not like the others.** Keep the newest three is right for a daily
news show and wrong for a weekly interview; a name your speech engine mangles
is fine everywhere except the one podcast it belongs to. The first is how a
setting is decided -- Preferences holds the shared defaults, and Settings for
This Podcast holds only what one podcast answers for itself. The second is the
handful of per-podcast settings that solve the problems people meet in their
first month.

This module also holds the last two lessons of track 2 (Keeping up): Episode
Filters and schedules. Both are rules you set for one podcast, so they read
best here; their ``track`` keeps them in Keeping up, after its other lessons.
"""

from __future__ import annotations

from quill.core.tutorials.model import Step, Tutorial

TUTORIALS: tuple[Tutorial, ...] = (
    Tutorial(
        slug="how-settings-resolve",
        title="Preferences, and one podcast's own settings",
        track="per-podcast",
        minutes=8,
        surfaces=("QUILL Cast Preferences", "Settings for"),
        summary=(
            "Preferences holds the choices every podcast follows, and Settings for "
            "This Podcast lets one podcast be different. You will change one thing, "
            "find out what you have changed, and put it back."
        ),
        steps=(
            Step(
                title="Open Preferences",
                body=(
                    "You start in the Section list. There are eight sections: When "
                    "Cast opens, Playing, Fetching, The Inbox, Chapters, Telling you, "
                    "The window and Data. Arrow to one, then Tab into its settings."
                ),
                keys=("Ctrl+,",),
                hear="QUILL Cast Preferences, then the Section list.",
            ),
            Step(
                title="Move between sections before you save",
                body=(
                    "You can change things in several sections before you save. Cast "
                    "holds on to them as you move around. Alt+S takes you back to the "
                    "Section list from a long section. Save tells you what changed, "
                    "and Escape leaves without changing anything."
                ),
                keys=("Down Arrow", "Tab", "Alt+S"),
                hear="Preferences saved, and what changed.",
            ),
            Step(
                title="Know what a shared default is",
                body=(
                    "Most of Preferences is shared defaults. Every podcast follows "
                    "them until you give that podcast its own. Change the skip "
                    "distance here, and every podcast skips that far, except one you "
                    "have set differently."
                ),
                hear="Nothing yet. Just keep this in mind for the next step.",
            ),
            Step(
                title="Open one podcast's settings",
                body=(
                    "Select a podcast in any list and open Settings for This Podcast. "
                    "You start in the Category list: Arrival, Playback, Storage, "
                    "Announcements and Curation. Every control shows what this podcast "
                    "is using right now."
                ),
                keys=("Ctrl+Alt+,",),
                hear="Settings for, the podcast's name, then the Category list.",
            ),
            Step(
                title="Ask a control what it does",
                body=(
                    "There are a lot of settings, and you do not need to learn them "
                    "from a list. Put focus on any control and press F1 to hear what "
                    "it does before you change it."
                ),
                keys=("F1",),
                hear="What the setting does.",
            ),
            Step(
                title="Change one thing",
                body=(
                    "Change just one control and press OK. Only that becomes this "
                    "podcast's own. Everything you left alone keeps following "
                    "Preferences, so a change you make there next month still reaches "
                    "this podcast."
                ),
                hear="Saved settings for the podcast, and what changed.",
                check="settings-changed",
            ),
            Step(
                title="Find out what you have changed",
                body=(
                    "What Have I Changed lists only the settings you changed for this "
                    "podcast. When one podcast behaves differently from the rest, this "
                    "is the quickest way to find out why. Opening it changes nothing."
                ),
                keys=("Alt+H",),
                hear="Only the settings this podcast has changed.",
            ),
            Step(
                title="Put one back, or all of them",
                body=(
                    "Wherever the podcast has its own setting, a button sits beside "
                    "it, such as Use shared default for Playback speed. Use Shared "
                    "Defaults puts all of this podcast's settings back at once, and "
                    "tells you how many it changed."
                ),
                keys=("Alt+D",),
                hear="How many settings it dropped.",
            ),
            Step(
                title="Change the common three in one keystroke",
                body=(
                    "Episodes to Keep, Queue Expiry and Playback Speed each have their "
                    "own row on a podcast's menu. Each opens a small window with the "
                    "cursor already in its one control, and Cast tells you in words "
                    "what you chose."
                ),
                keys=("Shift+F10",),
                hear="Something like Keeping the 5 newest downloaded episodes.",
                check="settings-changed",
            ),
        ),
        closing=(
            "Most people set a few things in Preferences and one or two on a single "
            "podcast, and then never think about it again. That is how it should be."
        ),
        then=("settings-worth-finding",),
    ),
    Tutorial(
        slug="settings-worth-finding",
        title="Podcast settings you will be glad you found",
        track="per-podcast",
        minutes=6,
        surfaces=("Settings for",),
        summary=(
            "Tidy titles that all start the same way, fix a name your speech engine "
            "gets wrong, decide who may interrupt you, hear when a podcast goes "
            "quiet, and give a podcast labels and an order of its own."
        ),
        steps=(
            Step(
                title="Tidy titles that all start the same",
                body=(
                    "Plenty of podcasts start every title with the same words. You "
                    "hear them on every row, and typing a first letter to jump stops "
                    "working. Under Announcements, Tidy episode titles leaves those "
                    "words out. Preview shows you which titles would change."
                ),
                keys=("Ctrl+Alt+,",),
                hear="Which titles would change, before you keep it.",
                check="settings-changed",
            ),
            Step(
                title="Say a name the way it sounds",
                body=(
                    "Does your speech engine always say a podcast's name wrong? Type "
                    "a spelling that sounds right in Say this podcast's name as. Cast "
                    "uses it whenever the name is spoken, and the written name stays "
                    "as it is."
                ),
                hear="The podcast's name, spoken your way, from then on.",
            ),
            Step(
                title="Decide who may interrupt you",
                body=(
                    "Under New episodes of this podcast are, Urgent tells you about "
                    "each one straight away. Normal counts it in a "
                    "summary. Quiet says nothing, but the episodes still arrive. May "
                    "speak during quiet hours lets one podcast through at night."
                ),
                hear="The choice you made, read back when you save.",
            ),
            Step(
                title="Hear when a podcast goes quiet",
                body=(
                    "Podcasts sometimes end without saying goodbye. Tell me if this "
                    "podcast goes quiet takes a number of weeks. If nothing new arrives "
                    "in that time, Cast tells you once. It never unfollows anything."
                ),
                hear="Nothing now; one sentence, once, if the podcast stops.",
            ),
            Step(
                title="Show fewer episodes, in the right order",
                body=(
                    "Under Curation, Show at most this many episodes keeps a podcast "
                    "with thousands of episodes to a list you can manage. Nothing is "
                    "deleted, and Find still finds everything. Sort by season and "
                    "episode number suits stories told in order, and audiobooks."
                ),
                hear="The podcast's list, shorter or in story order.",
            ),
            Step(
                title="Give a podcast labels",
                body=(
                    "A podcast lives in one folder, but it can have as many labels as "
                    "you like, under Curation. Labels are your own words for it, such "
                    "as Walking or Kids. A smart playlist can then gather episodes by "
                    "label."
                ),
                hear="Your settings saved, with the label.",
                check="labels-grew",
            ),
            Step(
                title="Protect one podcast's downloads",
                body=(
                    "Never delete this podcast's downloads, under Storage, keeps a "
                    "podcast you treasure safe from every automatic cleanup. The rest "
                    "of your downloads are tidied as usual."
                ),
                hear="Your settings saved for that podcast.",
            ),
        ),
        closing=(
            "None of these deletes an episode or marks anything played. Each one "
            "changes how a single podcast behaves, and nothing else, so try them "
            "freely."
        ),
        then=("organise-the-library",),
    ),
    Tutorial(
        slug="episode-filters",
        title="Stop the parts of a podcast you did not want",
        track="keeping-up",
        minutes=9,
        surfaces=("Episode Filters", "Episode Filter Rule", "Episode Filter Test"),
        summary=(
            "Episode Filters keep trailers, reruns or a daily segment out of your "
            "way, without deleting anything. Start from an episode you do not want, "
            "try the rule before you keep it, and get any episode back whenever "
            "you like."
        ),
        steps=(
            Step(
                title="Know what a filter does, and does not",
                body=(
                    "A filter is a set of rules for one podcast, and it never deletes "
                    "anything. A filtered episode keeps its played mark, your place, "
                    "its download, notes and bookmarks. A filter only changes where an "
                    "episode shows up. It can let in everything except what a rule "
                    "matches, or only what a rule matches."
                ),
                hear="Nothing yet. This is just good to know before you start.",
            ),
            Step(
                title="Start from an episode you do not want",
                body=(
                    "This is the easy way in. Go to an episode you would rather not "
                    "see, such as a trailer, open its menu and choose Filter Episodes "
                    "Like This. Episode Filters opens with a rule already written for "
                    "you. Its first line says why Cast chose it and how many recent "
                    "episodes it catches."
                ),
                keys=("Shift+F10",),
                hear="Episode Filters, then why Cast chose the rule and what it catches.",
            ),
            Step(
                title="Preview before you keep it",
                body=(
                    "Preview lists every recent episode in Preview results. Each row "
                    "starts with what would happen to it, then its title and length. "
                    "Nothing changes while you try, so adjust and try again as often "
                    "as you like."
                ),
                keys=("Alt+V", "Alt+L"),
                hear="What would happen to each recent episode, then its title.",
            ),
            Step(
                title="Adjust the rule",
                body=(
                    "Edit Rule opens the rule. Title match can use a star as a "
                    "wildcard, so Trailer star catches every title starting with "
                    "Trailer. It can also take a regular expression, if you know them. "
                    "Try It on Recent Episodes tries the rule on the podcast's 50 "
                    "newest episodes."
                ),
                keys=("Alt+E", "Alt+T", "Alt+P", "Alt+Y"),
                hear="Matches, a number, of the 50 newest episodes, and the first titles.",
            ),
            Step(
                title="Add more tests when the title is not enough",
                body=(
                    "Under More tests, Add Test can look at the show notes, the "
                    "people on the episode, its type, length, age, season or episode "
                    "number. Match when decides whether every test has to match, or "
                    "whether any one is enough."
                ),
                keys=("Alt+S", "Alt+A", "Alt+W"),
                hear="The rule read back as a sentence.",
            ),
            Step(
                title="Decide where the filter applies",
                body=(
                    "Where this applies has eight checkboxes. The first four start "
                    "checked. They keep matching episodes out of the Inbox, and never "
                    "queue, download or announce them for you. The other four hide "
                    "them from lists, and start unchecked."
                ),
                keys=("Alt+H",),
                hear="Each checkbox, and whether it is checked.",
            ),
            Step(
                title="Save it",
                body=(
                    "Press Save, and the filter works straight away, on episodes you "
                    "already have as well as new ones. You built the Play Queue by "
                    "hand, so Cast asks about it separately: clear matching episodes "
                    "from it, or leave it alone."
                ),
                hear="Cast asking about the Play Queue, then the filter in force.",
                check="filter-saved",
            ),
            Step(
                title="Get a filtered episode back",
                body=(
                    "Changed your mind about one episode? Choose Always Keep This "
                    "Episode (Ignore the Filter) from its menu, and the filter leaves "
                    "it alone. Or uncheck a box under Where this applies, or switch a "
                    "rule off, and its episodes come back at once."
                ),
                keys=("Shift+F10",),
                hear="Cast confirming the episode is kept.",
            ),
        ),
        closing=(
            "Most filters are just one rule, and Filter Episodes Like This writes "
            "most of them for you."
        ),
        then=("when-cast-checks",),
    ),
    Tutorial(
        slug="when-cast-checks",
        title="When Cast looks for new episodes",
        track="keeping-up",
        minutes=6,
        surfaces=("Feed Check", "Quiet Hours", "QUILL Cast Preferences"),
        summary=(
            "Check one podcast now, give your podcasts a schedule so you never have "
            "to, rest one between seasons, find the podcasts that have gone quiet, "
            "and decide who may speak up when something new arrives."
        ),
        steps=(
            Step(
                title="Check one podcast now",
                body=(
                    "Refresh Feed, on a podcast's menu, asks just that podcast for "
                    "anything new, and Refresh All Now asks every podcast. Checking "
                    "only looks at the list of episodes. It downloads nothing unless "
                    "you turned on automatic downloads."
                ),
                keys=("Shift+F10", "F5"),
                hear="Checking, the podcast's name, then what it found.",
            ),
            Step(
                title="Give everything a schedule",
                body=(
                    "In Preferences, under Fetching, Change Schedule sets when Cast "
                    "looks on its own: manually only, every so often, at set times, "
                    "around when the podcast usually publishes, or following the "
                    "podcast's own hint. Around when it usually publishes gets better "
                    "as it learns."
                ),
                keys=("Ctrl+,",),
                hear="The schedule read back in a sentence when you save.",
            ),
            Step(
                title="Give one podcast its own schedule",
                body=(
                    "Change Schedule on a podcast's menu gives that one its own. A "
                    "daily news podcast can check at six in the morning, while an old "
                    "favorite checks once a week. When you save, Cast reads the "
                    "schedule back to you."
                ),
                keys=("Shift+F10",),
                hear="Something like The Daily now checks: at 06:00 and 18:00, weekdays.",
            ),
            Step(
                title="Rest a podcast between seasons",
                body=(
                    "A podcast taking a break between seasons? Pause Updates for This "
                    "Podcast stops Cast checking and downloading it on its own, and "
                    "everything you already have stays. Refresh All Now and Refresh Feed "
                    "still check it when you ask. Resume Updates wakes it up again."
                ),
                keys=("Shift+F10",),
                hear="Cast confirming the podcast is paused.",
            ),
            Step(
                title="Find the feeds that have gone quiet",
                body=(
                    "Feed Check lists your podcasts, the ones in trouble first: "
                    "failing, then quiet, then healthy. Read from the top, and stop "
                    "when the rows turn healthy. Retry tries a failing one again, and "
                    "Retry All Failed tries them all."
                ),
                command="podcasts.feed_check",
                keys=("Ctrl+Shift+C",),
                hear="Feed Check, then the podcast in the most trouble.",
            ),
            Step(
                title="Hear about a podcast you care about",
                body=(
                    "Announce New Episodes, on a podcast's menu, has Cast tell you, "
                    "in speech and braille, about that podcast's new episodes when a "
                    "scheduled check finds them. For everything else, When new "
                    "episodes arrive, in Preferences under Telling you, chooses how "
                    "much Cast says."
                ),
                keys=("Shift+F10",),
                hear="Cast confirming it will announce that podcast.",
            ),
            Step(
                title="Keep the night quiet",
                body=(
                    "Quiet Hours sets a time, such as overnight, when Cast does not "
                    "speak up on its own. Downloads still run and nothing is lost. "
                    "News waits in Notifications for the morning. Anything you press "
                    "a key for still answers, and Cast always tells you when something "
                    "fails."
                ),
                command="app.quiet_hours",
                keys=("Ctrl+Alt+Shift+Z",),
                hear="Quiet Hours, then when it starts and ends.",
            ),
        ),
        closing=(
            "Give your daily podcasts a schedule and you can stop pressing F5. "
            "Quiet Hours are shared with the other Quill listening apps, so you only "
            "set them once."
        ),
        then=("how-settings-resolve",),
    ),
)
