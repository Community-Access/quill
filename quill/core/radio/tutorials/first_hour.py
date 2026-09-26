"""Track 1: your first hour with Quill Radio.

Five lessons that assume nothing -- the first four here, the fifth in
:mod:`first_hour_unstuck` (split 2026-09-25 to keep this module under the
600-line cap; ``__init__`` lists the two back to back, so the order holds).
Somebody who works down this track finishes with a station playing, a
favorite kept, the transport in their fingers, and a way out of anywhere they
get stuck. Everything else in the app is optional after this, and is written
as though this track has been done.

The order is not arbitrary. Play something first, because an app that has made
no sound yet is an app you have no reason to trust; keep it second, because
the second launch is where the first one pays off; then the player, because
that is the part that is unlike other radio programs and the part people miss;
then names, so that forgetting a key stops mattering; then getting unstuck,
which is the lesson somebody reads at the moment they need it most and can
least afford a long one.
"""

from __future__ import annotations

from quill.core.tutorials.model import Step, Tutorial

TUTORIALS: tuple[Tutorial, ...] = (
    Tutorial(
        slug="first-station",
        title="Play your first station",
        track="first-hour",
        minutes=5,
        surfaces=("Quill Radio", "Browse Stations"),
        summary=(
            "Open the browse tree, find a station that is on the air right now, "
            "and hear it. This is the loop the whole app is built on: arrow to a "
            "thing, press Enter."
        ),
        steps=(
            Step(
                title="Start where the app puts you",
                body=(
                    "Launch Quill Radio. The very first time, three short welcome "
                    "screens come up -- read them with the arrow keys, or press "
                    "Alt+K to Skip. After that, focus lands in the Favorite "
                    "stations tree, and on a new installation that tree is empty. "
                    "An empty list here is not a fault; it is a list you have not "
                    "filled in yet, and the next few minutes fill it."
                ),
                keys=("Alt+K",),
                hear=(
                    "Welcome to Quill Radio, screen 1 of 3 on a first launch; then Favorite "
                    "stations, tree -- or whatever your screen reader calls an empty tree."
                ),
            ),
            Step(
                title="Open Browse Stations",
                body=(
                    "Browse Stations is one window with one large tree in it. The "
                    "first row is Search All Sources; below it the top-level "
                    "branches are the sources: your favorites, popular stations, "
                    "whole world directories, weather radio, podcasts, audiobooks. "
                    "Nothing has been fetched yet -- these are only the doors."
                ),
                keys=("Ctrl+B",),
                hear="Browse Stations, then the first row of the tree: Search All Sources.",
                check="window:Browse Stations",
            ),
            Step(
                title="Walk the branches before opening one",
                body=(
                    "Press Down arrow half a dozen times and just listen. Each "
                    "press reads one source. This costs nothing and no branch is "
                    "contacted until you open it, so it is the cheapest way to "
                    "learn what this app can reach."
                ),
                keys=("Down arrow",),
                hear=(
                    "One source name per press: Favorites, Popular Stations, Trending Now, "
                    "Recently Added or Changed, By Country, and on down."
                ),
                note=(
                    "More than thirty sources is a lot to arrow past. When you "
                    "know which ones you actually use, Hide This Source on a "
                    "branch's own menu turns the rest off -- the lesson called "
                    "Wander the browse tree shows how."
                ),
            ),
            Step(
                title="Open Popular Stations",
                body=(
                    "Stop on Popular Stations and press Right arrow. This is the "
                    "one branch worth starting with when you have no idea what you "
                    "want: it is ranked by votes cast over years, so it is stations "
                    "that have been worth listening to for a long time rather than "
                    "whatever is loud today."
                ),
                keys=("Right arrow",),
                hear="Loading Popular Stations, then how many arrived: 100 items.",
            ),
            Step(
                title="Play one",
                body=(
                    "Press Down arrow onto a station and press Enter. That is the "
                    "whole gesture, and it is the same gesture on every row in "
                    "every branch of this tree for the rest of your life with the "
                    "app -- a station, a podcast episode, a book chapter, a "
                    "television channel."
                ),
                keys=("Down arrow", "Enter"),
                hear=(
                    "Playing, and the station's name, over a short connecting sound; then the "
                    "station itself."
                ),
                check="playing",
            ),
            Step(
                title="Set the volume without leaving the tree",
                body=(
                    "Press Volume Down twice. The volume moves in steps of ten and "
                    "says the new number every time, in every window -- so you "
                    "never have to guess whether the key landed, and you never have "
                    "to go back to the main window to turn it down."
                ),
                command="radio.volume_down",
                keys=("Ctrl+Down",),
                hear="Volume, and a number, then a number ten lower: Volume 70 percent, say.",
                check="volume-changed",
                note=(
                    "A favorite remembers the volume you set while it plays, and "
                    "gets it back next time. Stations are mastered wildly "
                    "differently, and you should only have to fix that once."
                ),
            ),
            Step(
                title="Stop it, and start it again",
                body=(
                    "Press Enter on the same row again. Enter on the station that "
                    "is already playing stops it, and Enter once more starts it. "
                    "It says which way it went, both times. A toggle that stays "
                    "silent leaves you pressing it twice to find out where you "
                    "are, which is how you end up back where you started."
                ),
                keys=("Enter",),
                hear="Radio stopped. Then Playing, and the station's name.",
                note=(
                    "Ctrl+Period is Stop in every window except the main one, "
                    "where Ctrl+P is Play and Stop on the Playback menu."
                ),
            ),
            Step(
                title="Close the tree, keep the music",
                body=(
                    "Press Escape. Browse Stations closes and focus returns to the "
                    "favorites tree in the main window -- and the station keeps "
                    "playing. Closing a window in Quill Radio never stops the "
                    "audio; only Stop does that."
                ),
                keys=("Escape",),
                hear="Quill Radio, the favorites tree, and the station still playing underneath.",
            ),
        ),
        closing=(
            "You have played a station and you know the gesture. Keep it playing "
            "for the next lesson, which is about not having to find it again."
        ),
        then=("keep-a-station",),
    ),
    Tutorial(
        slug="keep-a-station",
        title="Keep a station, and find it tomorrow",
        track="first-hour",
        minutes=4,
        surfaces=("Quill Radio",),
        summary=(
            "Turn the station you are listening to into a favorite, then reduce "
            "getting back to it to two keystrokes: launch, Enter."
        ),
        steps=(
            Step(
                title="Save what is playing",
                body=(
                    "With a station on, add it to your favorites from the main "
                    "window. You do not have to find the row it came from, and you "
                    "do not have to go back to the window you found it in -- this "
                    "command follows what is playing, not what is selected. It is "
                    "on the Station menu as Add Playing Station to Favorites."
                ),
                command="radio.toggle_playing_favorite",
                hear="Added, the station's name, to favorites.",
                check="favorite-added",
                note=(
                    "The same command removes it again, and the menu item "
                    "relabels itself to say so. It reads what is true now rather "
                    "than offering both, so it can never add a second copy."
                ),
            ),
            Step(
                title="Find it in the tree",
                body=(
                    "Move focus to the favorites tree in the main window and arrow "
                    "down. Your station is there. This tree is the main window's "
                    "whole purpose: it is a list you play from, not a second copy "
                    "of the player."
                ),
                keys=("Down arrow",),
                hear="The station's name, in the favorites tree.",
            ),
            Step(
                title="Play it from the list",
                body=(
                    "Press Enter on it. From now on this is your route to that "
                    "station: open the app, arrow to it, press Enter. Two "
                    "keystrokes and no navigation."
                ),
                keys=("Enter",),
                hear="Playing, and the station's name.",
            ),
            Step(
                title="Give it a name you would actually say",
                body=(
                    "Press F2 on the row and type whatever you call the station. "
                    "Directory names are written by whoever registered the stream, "
                    "so they are full of bitrates, call signs and capital letters. "
                    "Your name is used everywhere in the app from that moment; "
                    "clearing the field puts the directory's name back."
                ),
                keys=("F2",),
                hear=(
                    "Rename Station, an edit box with your name for it; then Station renamed, and "
                    "your new name."
                ),
            ),
            Step(
                title="Make the radio switch itself on",
                body=(
                    "Open the Station menu and tick Resume Last Station on Launch. "
                    "With that on, Quill Radio stops being a program you operate "
                    "and becomes an appliance: you open it, and your station is "
                    "already playing."
                ),
                keys=("Alt+S", "Ctrl+Alt+L"),
                hear="Quill Radio will pick up where you left off at launch.",
                note=(
                    "Pair it with Start Quill Radio with Windows, on the same menu "
                    "(Ctrl+Alt+W), and the radio is simply on when you sit down. "
                    "That entry is for your own account only and needs no "
                    "administrator rights."
                ),
            ),
            Step(
                title="Learn the one-key way back",
                body=(
                    "Play Last Station resumes whatever you had on, with no "
                    "navigation at all. It is the key to reach for when you "
                    "stopped something by accident, or came back to the machine "
                    "after lunch."
                ),
                command="radio.play_last",
                keys=("Ctrl+L",),
                hear="Playing, and the station's name.",
            ),
        ),
        closing=(
            "You have a favorite, under a name you chose, that comes back on its "
            "own. Everything after this is about doing more with less searching."
        ),
        then=("player-follows-you", "do-it-by-name"),
    ),
    Tutorial(
        slug="player-follows-you",
        title="The player follows you",
        track="first-hour",
        minutes=6,
        surfaces=("Quill Radio", "Player", "Browse Stations"),
        summary=(
            "Learn the handful of keys that work in every window, and the window "
            "that holds the whole player. This is the part of Quill Radio that is "
            "unlike other radio programs, and the part worth ten minutes."
        ),
        steps=(
            Step(
                title="Start something and go somewhere else",
                body=(
                    "Play a favorite, then open Browse Stations so that you are "
                    "standing somewhere other than the window you started the "
                    "audio from. Older versions of Quill Radio would have left you "
                    "with half a player here; the whole point of this lesson is "
                    "that they no longer do."
                ),
                keys=("Ctrl+B",),
                hear="Browse Stations, over the top of the station still playing.",
            ),
            Step(
                title="Change the volume from the wrong window",
                body=(
                    "Press Volume Up. It works, and it says the new level -- from "
                    "the browse window. There is one table of transport keys and "
                    "every window installs it, so a key means the same thing and "
                    "moves the same distance wherever you press it."
                ),
                command="radio.volume_up",
                keys=("Ctrl+Up",),
                hear="Volume, and a number ten higher than the last one.",
                check="volume-changed",
            ),
            Step(
                title="Mute, and hear that you muted",
                body=(
                    "Press Mute and then press it again. Silence is what muting is "
                    "for, so without a word there is no way to tell muting apart "
                    "from the stream dropping -- which is exactly why this one "
                    "speaks both ways."
                ),
                keys=("Ctrl+Shift+O",),
                hear="Muted, then the volume you came back to: Volume 70 percent, say.",
                check="muted",
                note=(
                    "Ctrl+Shift+O is Mute in every window but the main one, where "
                    "the Audio menu's Mute/Unmute is Ctrl+M."
                ),
            ),
            Step(
                title="Summon the player",
                body=(
                    "Go to Player opens the Player window -- and if it is already "
                    "open behind something, the same key brings it to the front "
                    "rather than opening a second copy. One key, one player, "
                    "always."
                ),
                command="radio.transport.go_to_player",
                keys=("Ctrl+Shift+G",),
                hear="Player, then the Now playing box.",
                check="window:Player",
            ),
            Step(
                title="Tab through what the player holds",
                body=(
                    "Tab from the top. First a read-only Now playing box saying "
                    "what is on, where you are in it, how fast it is playing and "
                    "how loud; then the buttons in the order people reach for "
                    "them -- Play or Stop, Pause, Skip Back, Skip Forward, Where "
                    "Am I, the three chapter buttons, Slower, Faster, Normal "
                    "Speed, Skip Silence, Volume Down, Volume Up, Mute, and last "
                    "Add to Favorites."
                ),
                keys=("Tab",),
                hear="Each control's name and state, one per press.",
            ),
            Step(
                title="Ask where you are",
                body=(
                    "Press Where Am I. On a recording or an episode it tells you "
                    "the position, the length and the chapter. On live radio it "
                    "tells you that this is live radio, which plays at broadcast "
                    "speed and has no position to move through -- a refusal with a "
                    "reason, rather than a key that quietly does nothing."
                ),
                command="radio.transport.announce_position",
                keys=("Ctrl+Shift+W",),
                hear="Either a position, or the sentence explaining why a live stream has none.",
            ),
            Step(
                title="Leave the player where it is",
                body=(
                    "Press Escape to close it, or leave it open and press Ctrl+Tab "
                    "to move to the next window. The Player is a real window: it "
                    "stands in the Window menu, in the taskbar and in the Ctrl+Tab "
                    "rotation, so you can keep it beside whatever you are doing."
                ),
                keys=("Escape", "Ctrl+Tab"),
                hear="The name of the window you are back in, or of the window you moved to.",
            ),
            Step(
                title="Find the status bar, which Tab never reaches",
                body=(
                    "Press F6 in the main window. Focus lands in the status strip "
                    "along the bottom: Play, Mute, Volume, Record, the sleep timer "
                    "and the time, as buttons you arrow across with Left and "
                    "Right. Tab deliberately never detours through it, so F6 is "
                    "the door -- and a second F6 or Escape is the way back."
                ),
                keys=("F6", "Left arrow", "Right arrow"),
                hear="The cell you land on, then each cell as you arrow across.",
                note=(
                    "Each cell has its own Applications-key menu, and that is "
                    "where the depth is: the Play cell offers your favorites and "
                    "recent stations, Record offers scheduling and the Recordings "
                    "window, Volume offers boost, the output device and Sound "
                    "Enhancements."
                ),
            ),
        ),
        closing=(
            "The transport keys are the same in Browse Stations, Find Stations, "
            "Manage Favorites, the Recordings list, Song History, the chapter "
            "list, Now Playing and the download queue. Learn them once."
        ),
        then=("do-it-by-name",),
    ),
    Tutorial(
        slug="do-it-by-name",
        title="Do anything by name",
        track="first-hour",
        minutes=4,
        surfaces=("Quill Radio", "Browse Stations", "Player"),
        summary=(
            "Three ways to reach anything without remembering a key: the command "
            "palette, the numbered list of places, and the sheet that lists every "
            "key you actually have."
        ),
        steps=(
            Step(
                title="Open the command palette",
                body=(
                    "The palette opens from every window and lists every command "
                    "in the app, including the whole player -- so it can pause "
                    "what is playing, not just change a setting."
                ),
                command="app.command_palette",
                hear="A search box, with the number of commands available.",
            ),
            Step(
                title="Type what you want, not what it is called",
                body=(
                    "Type a few letters -- vol, or record, or chapter -- and the "
                    "list narrows as you type. Arrow to the one you want and press "
                    "Enter; it runs exactly as its key or its menu item would."
                ),
                keys=("Down arrow", "Enter"),
                hear="The matching commands, each read with its own keystroke.",
                note=(
                    "Each entry shows its key, so the palette teaches you the "
                    "shortcut while you use it. That is deliberate: the palette is "
                    "meant to make itself less necessary."
                ),
            ),
            Step(
                title="Open the list of places",
                body=(
                    "Go To is a short numbered list of the ten places in the app. "
                    "Press the number and you are there; Escape puts you back "
                    "exactly where you were, on the same control."
                ),
                command="radio.go_to",
                keys=("Ctrl+G",),
                hear="A numbered list, starting with Favorites.",
            ),
            Step(
                title="Understand why the numbers are worth learning",
                body=(
                    "A place's number never changes on its own. Recordings is 4 "
                    "today and 4 next year, whether or not it is open. That is "
                    "what Ctrl+1 to Ctrl+9 cannot promise -- those reach the "
                    "windows you have open, in the order you opened them, so the "
                    "numbering shifts under you all day."
                ),
                keys=("Escape",),
                hear="Nothing new: this step is a fact, not an action.",
            ),
            Step(
                title="Open the sheet of every key",
                body=(
                    "The Keyboard Shortcuts Sheet lists every key the app answers "
                    "to, filterable. Type what you want to do -- record -- or a "
                    "key you found and cannot place -- Ctrl+B -- and the list "
                    "narrows to it."
                ),
                keys=("Ctrl+Alt+Shift+K",),
                hear="A filter box, then the number of shortcuts listed.",
                note=(
                    "The sheet is built by reading the menu bar in front of you, "
                    "so it shows the keys you actually have. Rebind something and "
                    "the sheet says your key, not the default."
                ),
            ),
            Step(
                title="Ask what the thing under your fingers is",
                body=(
                    "Press F1 anywhere. A window opens with two parts read as one "
                    "pass: what the window you are in is for, then what the "
                    "control under focus does and how to drive it. The text sits "
                    "in a field you can arrow through and copy, and Escape returns "
                    "you exactly where you were."
                ),
                keys=("F1",),
                hear="The window's purpose, then the control's own help.",
            ),
        ),
        closing=(
            "Between the palette, Go To, the sheet and F1, there is no state of "
            "this app you can be in and not have a way out of. That is the point "
            "of all four."
        ),
        then=("getting-unstuck",),
    ),
)
