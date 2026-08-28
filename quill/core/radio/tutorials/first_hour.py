"""Track 1: your first hour with Quill Radio.

Five lessons that assume nothing. Somebody who works down this track finishes
with a station playing, a favorite kept, the transport in their fingers, and a
way out of anywhere they get stuck. Everything else in the app is optional
after this, and is written as though this track has been done.

The order is not arbitrary. Play something first, because an app that has made
no sound yet is an app you have no reason to trust; keep it second, because
the second launch is where the first one pays off; then the player, because
that is the part that is unlike other radio programs and the part people miss;
then names, so that forgetting a key stops mattering; then getting unstuck,
which is the lesson somebody reads at the moment they need it most and can
least afford a long one.
"""

from __future__ import annotations

from quill.core.radio.tutorials.model import Step, Tutorial

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
                    "Launch Quill Radio and do not press anything yet. Focus is "
                    "already in the Favorite stations tree -- there is nothing to "
                    "Tab past first, and on a new installation that tree is empty. "
                    "An empty list here is not a fault; it is a list you have not "
                    "filled in yet, and the next few minutes fill it."
                ),
                hear=(
                    "Favorite stations, tree -- or whatever your screen reader calls an empty tree."
                ),
            ),
            Step(
                title="Open Browse Stations",
                body=(
                    "Browse Stations is one window with one large tree in it, and "
                    "the tree's top-level branches are the sources: your favorites, "
                    "popular stations, whole world directories, weather radio, "
                    "podcasts, audiobooks. Nothing has been fetched yet -- these "
                    "are only the doors."
                ),
                command="radio.browse",
                hear="Entered Browse Stations, then the first branch of the tree.",
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
                    "One source name per press: Favorites, Popular Stations, Radio Browser by "
                    "Genre, and on down."
                ),
                note=(
                    "Twenty-eight sources is a lot to arrow past. When you know "
                    "which ones you actually use, the lesson called Prune the "
                    "browse tree turns the rest off."
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
                hear="A pause while it loads, then Quill Radio saying the stations have arrived.",
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
                hear="Connecting, then Playing, then the station itself.",
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
                hear="Volume 80 percent, then Volume 70 percent.",
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
                    "Press Play/Stop once to stop and once more to start. It says "
                    "which way the toggle went, both times. A toggle that stays "
                    "silent leaves you pressing it twice to find out where you are, "
                    "which is how you end up back where you started."
                ),
                command="radio.play_pause",
                hear="Stopped. Then Connecting, then Playing.",
            ),
            Step(
                title="Leave the tree open",
                body=(
                    "Press Escape. Browse Stations closes and focus returns to the "
                    "favorites tree in the main window -- and the station keeps "
                    "playing. Closing a window in Quill Radio never stops the "
                    "audio; only Stop does that."
                ),
                keys=("Escape",),
                hear="Exited Browse Stations, and the station still playing underneath.",
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
                    "With a station on, add it to your favorites. You do not have "
                    "to find the row it came from, and you do not have to be in the "
                    "window you found it in -- this command follows what is "
                    "playing, from anywhere."
                ),
                command="radio.toggle_playing_favorite",
                hear="Added, and the station's name.",
                check="favorite-added",
                note=(
                    "The same command removes it again. It reads what is true now "
                    "rather than offering both, so it can never add a second copy."
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
                hear="Connecting, then Playing.",
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
                hear="An edit box with the current name in it, then your new name read back.",
            ),
            Step(
                title="Make the radio switch itself on",
                body=(
                    "Open the Station menu and tick Resume Last Station on Launch. "
                    "With that on, Quill Radio stops being a program you operate "
                    "and becomes an appliance: you open it, and your station is "
                    "already playing."
                ),
                keys=("Alt+S",),
                hear="The menu item read back with its ticked state.",
                note=(
                    "Pair it with Start Quill Radio with Windows, on the same menu, "
                    "and the radio is simply on when you sit down. That entry is "
                    "for your own account only and needs no administrator rights."
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
                hear="Connecting, then Playing, and the station's name.",
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
                command="radio.browse",
                hear="Entered Browse Stations, over the top of the station still playing.",
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
                command="radio.mute_toggle",
                hear="Muted, then Unmuted.",
                check="muted",
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
                hear="Entered Player.",
                check="window:Player",
            ),
            Step(
                title="Tab through what the player holds",
                body=(
                    "Tab from the top. First a read-only Now playing box saying "
                    "what is on, where you are in it, how fast it is playing and "
                    "how loud; then the buttons in the order people reach for "
                    "them -- Play/Pause, Stop, Skip Back, Skip Forward, Where Am "
                    "I, chapters, speed, volume, mute."
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
                hear="Exited Player, or the name of the window you moved to.",
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
                    "recent stations, Record offers scheduling and the recordings "
                    "window, Volume offers boost, output device and enhancements."
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
    Tutorial(
        slug="getting-unstuck",
        title="Getting unstuck",
        track="first-hour",
        minutes=4,
        surfaces=("Quill Radio",),
        summary=(
            "The short list to reach for when something is not where you expected, "
            "you missed what was said, or a menu item will not press. Read it once "
            "now so it is familiar when you need it."
        ),
        steps=(
            Step(
                title="Escape steps back, and says where you landed",
                body=(
                    "Escape closes the window you are in and announces which one "
                    "you left. Ctrl+W, Ctrl+F4, Alt+F4 and the titlebar all close "
                    "a window too -- take your pick. Closing never stops playback "
                    "and never loses anything you have not deliberately deleted."
                ),
                keys=("Escape",),
                hear="Exited, and the name of the window you left.",
            ),
            Step(
                title="Hear the last announcement again",
                body=(
                    "Speech disappears the moment it finishes, which is right "
                    "almost always and wrong the one time the sentence you needed "
                    "went past. Repeat Last Announcement says it again. Find it in "
                    "the command palette by typing repeat."
                ),
                keys=("Ctrl+Shift+P",),
                hear="Whatever Quill Radio last told you, in full.",
            ),
            Step(
                title="Ask what is playing",
                body=(
                    "What's Playing answers in one sentence without opening "
                    "anything: the station, and the track when the stream carries "
                    "one. It is the fastest way to work out what you are listening "
                    "to after coming back to the machine."
                ),
                command="radio.whats_playing",
                keys=("Ctrl+T",),
                hear="The station, and the track if there is one.",
            ),
            Step(
                title="Read the list of what has failed",
                body=(
                    "Recent Problems is a list of what has gone wrong recently -- "
                    "feeds that could not be read, downloads that died, streams "
                    "that dropped -- each with its reason and the time. It exists "
                    "because a spoken failure you missed used to be gone for good."
                ),
                keys=("Ctrl+Alt+Shift+P",),
                hear="A list of problems, newest first, or a statement that there are none.",
                note=(
                    "Copy All takes the list as text, which is what to paste into "
                    "a bug report. It carries addresses and error messages, never "
                    "passwords, and nothing in it leaves this computer."
                ),
            ),
            Step(
                title="Find out why a menu item is dimmed",
                body=(
                    "A greyed item is not a dead end here. Every dimmed item "
                    "carries its own reason -- Analyse Chapters: this episode is "
                    "not downloaded yet, so there is nothing to analyse -- shown "
                    "in the status bar and spoken by readers that voice menu help. "
                    "The palette says the same reason instead of a bare "
                    "unavailable."
                ),
                keys=("Alt+P",),
                hear="The item, the word dimmed, and the sentence saying what would un-dim it.",
            ),
            Step(
                title="Take back the last destructive thing",
                body=(
                    "Undo Last Action brings back the last thing you removed: an "
                    "unsubscribe, a deleted recording, a Mark All as Played. It "
                    "says what it brought back. It is one step and not a stack, on "
                    "purpose -- an undo you have to count presses of is a puzzle."
                ),
                command="app.undo_last",
                keys=("Ctrl+Z",),
                hear="Undid, and what came back -- or Nothing to undo.",
                note=(
                    "Every action that can be undone ends its own announcement "
                    "with Ctrl+Z undoes this, so you never have to remember "
                    "whether this particular verb was one of them."
                ),
            ),
            Step(
                title="Report it rather than working around it",
                body=(
                    "If something does not happen the way a lesson says it should, "
                    "that is worth reporting. Report a Bug files an issue from "
                    "inside the app, stamped with this app's version, with no "
                    "account needed anywhere."
                ),
                keys=("Ctrl+Alt+B",),
                hear="A form with most of it already filled in.",
            ),
        ),
        closing=(
            "That is the first hour. From here the tracks are independent: go to "
            "Finding something to listen to if you want more stations, or to "
            "Recording if you have a show to catch."
        ),
    ),
)
