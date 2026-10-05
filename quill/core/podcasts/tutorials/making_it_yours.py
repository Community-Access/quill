"""QUILL Cast, track 5: making it yours -- and the last lesson of track 3.

Three lessons. A library that has grown past a screenful; what every row says
and what Enter does, and which parts of Cast you see at all; and the backup,
the move to a new computer and the place that follows you between machines --
which you will be glad of exactly once.

This module also holds listening statistics, the last lesson of track 3
(Listening well), because it is about your own data like the backup is; its
``track`` keeps it in Listening well.
"""

from __future__ import annotations

from quill.core.tutorials.model import Step, Tutorial

TUTORIALS: tuple[Tutorial, ...] = (
    Tutorial(
        slug="organise-the-library",
        title="Arrange a library that has grown",
        track="yours",
        minutes=6,
        surfaces=("Podcasts", "Move to Folder", "QUILL Cast"),
        summary=(
            "Put your podcasts in folders and in your own order, listen from a "
            "whole folder at once, and hide what you have caught up on. You will "
            "also keep favorites close, and let a podcast go when you are done."
        ),
        steps=(
            Step(
                title="Make a folder",
                body=(
                    "Once you follow more than a handful, folders help: News, Comedy, "
                    "Long Drives, whatever suits you. New Folder, on the Podcasts "
                    "menu, asks for a name. Folders live in the Podcasts place."
                ),
                keys=("Ctrl+Shift+F",),
                hear="The new folder, in Podcasts.",
            ),
            Step(
                title="File a podcast into it",
                body=(
                    "Go to a podcast, open its menu and choose Move to Folder, then "
                    "pick the folder. If you delete a folder later, its podcasts just "
                    "move out of it, so you never lose one that way."
                ),
                keys=("Shift+F10", "Enter"),
                hear="The podcast in its new folder.",
            ),
            Step(
                title="Put them in your own order",
                body=(
                    "In the Podcasts place, Alt+Up and Alt+Down move a podcast or a "
                    "folder. The first time you do it, Cast switches Sort Podcasts to "
                    "Custom Order for you, starting from the order you already had, so "
                    "nothing jumps around."
                ),
                keys=("Alt+Up", "Alt+Down"),
                hear="Where it moved.",
            ),
            Step(
                title="Listen from a whole folder",
                body=(
                    "On a folder's menu, Play All Unheard queues the newest unheard "
                    "episode from each podcast in it and starts playing. Add All to "
                    "Queue adds every unheard episode instead."
                ),
                keys=("Shift+F10",),
                hear="The first episode playing, and how many were queued.",
                check="playing",
            ),
            Step(
                title="Hide what you have caught up on",
                body=(
                    "Hide Caught-Up Podcasts, on the View menu, hides the podcasts "
                    "with nothing unheard, so only the ones with something new for you "
                    "are left. Press it again to show them all."
                ),
                keys=("Ctrl+Shift+H",),
                hear="Caught-up podcasts hidden, and how many.",
            ),
            Step(
                title="Keep your favorites close",
                body=(
                    "Add to Favorites, in the main window, works on the podcast that "
                    "is playing. Favorites is a place: Enter on one opens its "
                    "episodes right there, and Delete takes it out of Favorites while "
                    "you still follow it."
                ),
                keys=("Alt+F", "Ctrl+Shift+V"),
                hear="Favorites, then the podcasts in it.",
            ),
            Step(
                title="Let a podcast go",
                body=(
                    "Unfollow, in the main window, or Delete on a podcast in the "
                    "Podcasts place. Cast asks first, and asks separately about any "
                    "downloads. Changed your mind? Ctrl+Z brings it back with its "
                    "episodes and your place in them."
                ),
                keys=("Alt+U", "Ctrl+Z"),
                hear="A question that starts on No; after Ctrl+Z, the podcast back.",
            ),
        ),
        closing=(
            "Your library is yours to arrange however you like. To share one folder "
            "with another computer or a friend, use Export This Folder as OPML on "
            "the folder's menu."
        ),
        then=("rows-and-actions",),
    ),
    Tutorial(
        slug="rows-and-actions",
        title="Decide what a row says, and what Enter does",
        track="yours",
        minutes=6,
        surfaces=("QUILL Cast", "QUILL Cast Preferences"),
        summary=(
            "Your screen reader reads each row in full, and you get to decide what "
            "goes in it. Choose the columns, how an episode row is spoken, what "
            "Enter and Ctrl+1 to Ctrl+9 do, and which parts of Cast you see at all."
        ),
        steps=(
            Step(
                title="Turn on the Advanced rows",
                body=(
                    "Cast starts in Simple mode, with the menus you use week to week. "
                    "Advanced Features adds the rows you go looking for once you know "
                    "they exist, such as Choose Columns and Quick Actions. Press it "
                    "again to switch back."
                ),
                keys=("Ctrl+Alt+Shift+G",),
                hear="Which mode you are now in.",
            ),
            Step(
                title="Choose the columns",
                body=(
                    "In Choose Columns, pick a list in Columns for, then move a column "
                    "up or down, or hide it. A row will read lets you hear what one "
                    "row will sound like before you press OK. Time Left starts hidden "
                    "and is worth a try."
                ),
                keys=("Ctrl+Alt+Shift+C",),
                hear="What one row will sound like.",
            ),
            Step(
                title="Decide how an episode row is spoken",
                body=(
                    "In Preferences, under Telling you, Read each row starting with "
                    "chooses the title, the podcast or the date. Whatever comes first "
                    "is what typing a letter jumps to. Other choices there add the "
                    "length or whether it is downloaded, or leave the description out."
                ),
                keys=("Ctrl+,",),
                hear="The Telling you section, then the first row choice.",
            ),
            Step(
                title="Choose what Enter does",
                body=(
                    "Quick Actions decides what Enter does on a row, what Ctrl+1 to "
                    "Ctrl+9 do, and the order of a row's menu. In Actions for, pick "
                    "episodes, podcasts or the Play Queue. The first action in the "
                    "Order list is what Enter does, and Make Default puts one first."
                ),
                command="podcasts.quick_actions",
                keys=("Ctrl+Alt+Q",),
                hear="Quick Actions, then the actions for episodes.",
            ),
            Step(
                title="Run an action by its number",
                body=(
                    "In any episode list, Ctrl+1 to Ctrl+9 run the first nine Quick "
                    "Actions. Put the action you use most, after Play, second in the "
                    "list, and Ctrl+2 does it from then on. If one cannot run on a "
                    "row, Cast tells you why."
                ),
                keys=("Ctrl+2",),
                hear="What the action did.",
            ),
            Step(
                title="Turn off what you never use",
                body=(
                    "Customize Features lists every feature as a checkbox. Uncheck what "
                    "you do not want, and it leaves the menus, places and Go To. The "
                    "Just Listen profile keeps only the essentials. Do not worry, "
                    "whatever you turn off, you still have a podcast player."
                ),
                keys=("Ctrl+Alt+C",),
                hear="Feature settings saved, and what follows them.",
            ),
        ),
        closing=(
            "Forgot where a feature went? The Command Palette still lists its "
            "commands, and tells you they are switched off in Customize Features."
        ),
        then=("keep-it-safe",),
    ),
    Tutorial(
        slug="keep-it-safe",
        title="Back it up, move it, and keep your place",
        track="yours",
        minutes=6,
        surfaces=("QUILL Cast",),
        summary=(
            "Save your whole library in one file and put it back again. Then move "
            "everything to a new computer, and keep your place in step between "
            "computers, and between Quill Radio and Cast."
        ),
        steps=(
            Step(
                title="Make a backup",
                body=(
                    "Back Up My Podcasts saves your whole library in one file: the "
                    "podcasts you follow, folders, playlists, your place in each "
                    "episode, notes, statistics and bookmarks. It asks whether to "
                    "include downloads, and the answer starts on No. You will find it "
                    "once Advanced Features is on."
                ),
                keys=("Ctrl+Alt+Shift+B",),
                hear="Cast telling you the backup is written.",
            ),
            Step(
                title="Put it back",
                body=(
                    "Restore from a Backup asks for the file. Before it changes "
                    "anything, it tells you when the backup was made and how many "
                    "podcasts it holds. It replaces the library on this computer, and "
                    "you do not need to restart Cast."
                ),
                keys=("Ctrl+Alt+F12",),
                hear="When the backup was made, and how many podcasts it holds.",
            ),
            Step(
                title="Move your setup to a new computer",
                body=(
                    "Export My Setup carries what a backup does not: your settings, "
                    "your Go To and Quick Action order, and any keys you changed. On "
                    "the new computer, Import My Setup tells you what the file holds "
                    "and asks before it changes anything. Passwords are never included."
                ),
                command="app.export_setup",
                keys=("Ctrl+Alt+Shift+X", "Ctrl+Alt+Shift+N"),
                hear="What the file holds, before anything changes.",
            ),
            Step(
                title="Export your data to read",
                body=(
                    "Curious what Cast knows about your listening? Export My Data "
                    "writes it all to one file you can read. Cast cannot restore from "
                    "it, so for a copy you can put back, use Back Up My Podcasts."
                ),
                command="podcasts.export_data",
                keys=("Ctrl+Alt+Shift+E",),
                hear="Where the file was written.",
            ),
            Step(
                title="Carry your place between machines",
                body=(
                    "Listen on more than one computer? Carry My Place Between Machines, "
                    "on the Podcasts menu, keeps your place in step through a folder "
                    "you already sync, such as OneDrive, with no account to make. "
                    "Choose the folder, choose encrypted or a plain file, name this "
                    "computer, and press Sync Now."
                ),
                keys=("Alt+P", "H"),
                hear="Cast saying how the sync went.",
                note=(
                    "If you choose encrypted, write the recovery phrase down. Your "
                    "other computers need it to join."
                ),
            ),
            Step(
                title="Pick up where Quill Radio left off",
                body=(
                    "On the same computer, Quill Radio and Cast remember the same "
                    "place in each episode. Pause an episode in Radio, play it in Cast, "
                    "and it carries on from the same second. An episode you finish in "
                    "either app is finished in both."
                ),
                keys=("Enter",),
                hear="Picking up where you left off in Quill Radio, and the time.",
            ),
        ),
        closing=(
            "Make a backup now, while you think of it, and again whenever you have "
            "spent an evening sorting folders. You will be glad you did."
        ),
    ),
    Tutorial(
        slug="how-much-did-i-listen",
        title="How much did I actually listen?",
        track="listening",
        minutes=4,
        surfaces=("Listening Statistics", "Year in Review"),
        summary=(
            "See how long you have listened, how much time faster playback saved "
            "you, your top podcasts, and the story of your year. It all stays on "
            "your computer."
        ),
        steps=(
            Step(
                title="Open Listening Statistics",
                body=(
                    "Listening Statistics is on the Episode menu. Cast keeps the count "
                    "on your computer and nowhere else, and only for as long as you "
                    "tell it to."
                ),
                command="podcasts.statistics",
                keys=("Ctrl+Alt+Shift+S",),
                hear="Listening Statistics, then the period.",
            ),
            Step(
                title="Choose a period",
                body=(
                    "Period offers this week, this month, this year or all time. The "
                    "report below changes to match as soon as you choose, so arrow "
                    "through the periods and compare."
                ),
                keys=("Alt+P",),
                hear="The period you chose.",
            ),
            Step(
                title="Read the report",
                body=(
                    "Read the Listening report line by line: how long you listened, "
                    "how much time faster playback saved you, how many episodes you "
                    "finished, and your podcasts, most listened first. Times are said "
                    "as words, so they never sound like a time of day."
                ),
                keys=("Alt+R",),
                hear="How long you listened, as words, such as 3 hours, 47 minutes.",
            ),
            Step(
                title="Hear the story of your year",
                body=(
                    "Year in Review tells it in a few friendly sentences: how long you "
                    "listened, your top podcasts and their share of the year, your "
                    "busiest month, and how many days you listened. You can copy it "
                    "or save it."
                ),
                keys=("Alt+Y",),
                hear="Year in Review, then the first sentence of your year.",
            ),
            Step(
                title="Keep it, or clear it",
                body=(
                    "Copy puts the report on the clipboard, and Export CSV saves every "
                    "listening session for a spreadsheet. Clear Statistics deletes "
                    "only the listening record, nothing else. Keep my listening history "
                    "for, in Preferences under Data, decides how much Cast remembers."
                ),
                keys=("Alt+C", "Alt+E", "Alt+S"),
                hear="What Cast copied, saved or cleared.",
                note=(
                    "Show listening streaks in Statistics, in the same section, adds "
                    "your streak to the report and to Year in Review."
                ),
            ),
        ),
        closing="Enjoy the numbers. Nothing in your statistics ever leaves your computer.",
        then=("how-settings-resolve",),
    ),
)
