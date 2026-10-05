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
            "In five minutes you will have a station playing that you picked "
            "yourself. You will open the list of stations, find one that is on "
            "the air, and hear it. Along the way you will learn the one move you "
            "use everywhere in Quill Radio: arrow to something, press Enter."
        ),
        steps=(
            Step(
                title="Start where the app puts you",
                body=(
                    "Open Quill Radio. The very first time, you get three short "
                    "welcome screens. Read them with the arrow keys, or press "
                    "Alt+K to skip them. After that you land in the Favorite "
                    "stations list. On a new install it is empty, and that is "
                    "fine. Nothing is wrong. You are about to fill it."
                ),
                keys=("Alt+K",),
                hear=(
                    "Welcome to Quill Radio, screen 1 of 3 the first time. Then Favorite "
                    "stations, tree, or whatever your screen reader says for an empty tree."
                ),
            ),
            Step(
                title="Open Browse Stations",
                body=(
                    "Browse Stations is one window with one big list in it, laid "
                    "out like a tree. The first row is Search All Sources. Below it "
                    "are the places stations come from: your favorites, popular "
                    "stations, directories from all over the world, weather radio, "
                    "podcasts and audiobooks. Nothing is loaded yet, so take your "
                    "time."
                ),
                keys=("Ctrl+B",),
                hear="Browse Stations, then the first row: Search All Sources.",
                check="window:Browse Stations",
            ),
            Step(
                title="Walk the branches before opening one",
                body=(
                    "Press Down Arrow six or seven times and just listen. Each "
                    "press reads the name of one source. Nothing opens until you "
                    "ask it to, so this is a safe and quick way to get a feel for "
                    "everything Quill Radio can reach."
                ),
                keys=("Down arrow",),
                hear=(
                    "One source name per press: Favorites, Popular Stations, Trending Now, "
                    "Recently Added or Changed, By Country, and so on."
                ),
                note=(
                    "There are more than thirty sources, which is a lot to arrow "
                    "past. Once you know the ones you like, you can hide the rest "
                    "with Hide This Source on a branch's own menu. The lesson "
                    "called Wander the browse tree shows you how."
                ),
            ),
            Step(
                title="Open Popular Stations",
                body=(
                    "Stop on Popular Stations and press Right Arrow. This is a "
                    "great place to start when you have no idea what you want. "
                    "Listeners have voted for these stations over many years, so "
                    "they are ones people keep coming back to."
                ),
                keys=("Right arrow",),
                hear="Loading Popular Stations, then how many arrived: 100 items.",
            ),
            Step(
                title="Play one",
                body=(
                    "Press Down Arrow onto a station and press Enter. That is all "
                    "there is to it. The same move works on every row in this "
                    "list: a station, a podcast episode, a chapter of a book or a "
                    "television channel. Arrow to it, press Enter."
                ),
                keys=("Down arrow", "Enter"),
                hear=(
                    "Playing, and the station's name, over a short connecting sound. Then "
                    "the station itself."
                ),
                check="playing",
            ),
            Step(
                title="Set the volume without leaving the tree",
                body=(
                    "Press Volume Down twice. The volume moves ten steps at a time "
                    "and says the new number each time. This works in every "
                    "window, so you never have to go looking for a volume control "
                    "or wonder whether the key worked."
                ),
                command="radio.volume_down",
                keys=("Ctrl+Down",),
                hear="Volume and a number, then a number ten lower. Volume 70 percent, say.",
                check="volume-changed",
                note=(
                    "Once a station is a favorite, it remembers the volume you "
                    "set while it played and uses it again next time. Some "
                    "stations are much louder than others, and this way you only "
                    "fix that once."
                ),
            ),
            Step(
                title="Stop it, and start it again",
                body=(
                    "Press Enter on the same row again. Enter on the station that "
                    "is playing stops it, and Enter once more starts it again. "
                    "Quill Radio tells you which one happened each time, so you "
                    "always know where you are."
                ),
                keys=("Enter",),
                hear="Radio stopped. Then Playing, and the station's name.",
                note=(
                    "Ctrl+Period is Stop in every window except the main one. In "
                    "the main window, Ctrl+P is Play and Stop on the Playback menu."
                ),
            ),
            Step(
                title="Close the tree, keep the music",
                body=(
                    "Press Escape. Browse Stations closes and you are back in the "
                    "favorites list in the main window, with the station still "
                    "playing. Closing a window in Quill Radio never stops the "
                    "sound. Only Stop does that."
                ),
                keys=("Escape",),
                hear="Quill Radio, the favorites list, and the station still playing.",
            ),
        ),
        closing=(
            "Well done. You found a station and played it, and you know the move "
            "that works everywhere. Leave it playing for the next lesson, which "
            "shows you how to keep it so you never have to search for it again."
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
            "Save the station you are listening to as a favorite. After this, "
            "getting back to it tomorrow takes two keys: open Quill Radio, press "
            "Enter."
        ),
        steps=(
            Step(
                title="Save what is playing",
                body=(
                    "With a station playing, add it to your favorites from the "
                    "main window. You do not need to find the row it came from or "
                    "go back to the window where you found it. This command always "
                    "saves whatever is playing right now. It is on the Station "
                    "menu as Add Playing Station to Favorites."
                ),
                command="radio.toggle_playing_favorite",
                hear="Added, the station's name, to favorites.",
                check="favorite-added",
                note=(
                    "The same command takes it out again, and the menu item "
                    "changes its name to say so. That way you can never end up "
                    "with two copies of the same station."
                ),
            ),
            Step(
                title="Find it in the tree",
                body=(
                    "Move to the favorites list in the main window and arrow "
                    "down. There is your station. This list is what the main "
                    "window is for: the stations you love, ready to play."
                ),
                keys=("Down arrow",),
                hear="The station's name, in the favorites list.",
            ),
            Step(
                title="Play it from the list",
                body=(
                    "Press Enter on it. From now on, this is how you get to that "
                    "station: open Quill Radio, arrow to it, press Enter. No "
                    "searching, no menus."
                ),
                keys=("Enter",),
                hear="Playing, and the station's name.",
            ),
            Step(
                title="Give it a name you would actually say",
                body=(
                    "Press F2 on the row and type the name you use for the "
                    "station. Names in the directories are often full of numbers, "
                    "call letters and capitals. Your name is the one Quill Radio "
                    "uses from now on. If you clear the box, the original name "
                    "comes back."
                ),
                keys=("F2",),
                hear=(
                    "Rename Station, an edit box with the current name. Then Station "
                    "renamed, and your new name."
                ),
            ),
            Step(
                title="Make the radio switch itself on",
                body=(
                    "Open the Station menu and check Resume Last Station on "
                    "Launch. Now when you open Quill Radio, your station is "
                    "already playing, just like turning on a radio in the kitchen."
                ),
                keys=("Alt+S", "Ctrl+Alt+L"),
                hear="Quill Radio will pick up where you left off at launch.",
                note=(
                    "Turn on Start Quill Radio with Windows too, on the same menu "
                    "(Ctrl+Alt+W), and the radio is simply on when you sit down. "
                    "It only affects your own Windows account, and you do not "
                    "need to be an administrator."
                ),
            ),
            Step(
                title="Learn the one-key way back",
                body=(
                    "Play Last Station starts whatever you had on last, with no "
                    "searching at all. Reach for it when you stopped something by "
                    "mistake, or when you come back to the computer after lunch."
                ),
                command="radio.play_last",
                keys=("Ctrl+L",),
                hear="Playing, and the station's name.",
            ),
        ),
        closing=(
            "Now you have a favorite, with a name you chose, and it can even "
            "start on its own. From here on, everything is about finding more "
            "of what you like with less effort."
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
            "Learn the handful of keys that work in every window, and meet the "
            "Player window, which has every control in one place. This is worth "
            "ten minutes of your time, because it is what makes Quill Radio feel "
            "easy."
        ),
        steps=(
            Step(
                title="Start something and go somewhere else",
                body=(
                    "Play one of your favorites, then open Browse Stations. Now "
                    "you are in a different window from the one where you "
                    "started the music. Watch what happens: all the player keys "
                    "still work right here."
                ),
                keys=("Ctrl+B",),
                hear="Browse Stations, with your station still playing.",
            ),
            Step(
                title="Change the volume from the wrong window",
                body=(
                    "Press Volume Up. It works, right here in the browse window, "
                    "and it tells you the new level. The player keys do the same "
                    "thing in every window, so you only have to learn them once."
                ),
                command="radio.volume_up",
                keys=("Ctrl+Up",),
                hear="Volume, and a number ten higher than before.",
                check="volume-changed",
            ),
            Step(
                title="Mute, and hear that you muted",
                body=(
                    "Press Mute, then press it again. Quill Radio says Muted, and "
                    "then says the volume when you come back. That way you can "
                    "always tell a mute apart from a station that has dropped out."
                ),
                keys=("Ctrl+Shift+O",),
                hear="Muted, then the volume you came back to. Volume 70 percent, say.",
                check="muted",
                note=(
                    "Ctrl+Shift+O is Mute in every window except the main one. "
                    "In the main window, Mute/Unmute on the Audio menu is Ctrl+M."
                ),
            ),
            Step(
                title="Summon the player",
                body=(
                    "Go to Player opens the Player window. If it is already open "
                    "behind something else, the same key brings it to the front "
                    "instead of opening a second one. One key, one player, every "
                    "time."
                ),
                command="radio.transport.go_to_player",
                keys=("Ctrl+Shift+G",),
                hear="Player, then the Now playing box.",
                check="window:Player",
            ),
            Step(
                title="Tab through what the player holds",
                body=(
                    "Press Tab from the top. First you reach the Now playing box, "
                    "which tells you what is on, where you are in it, how fast it "
                    "is playing and how loud. Then come the buttons: Play or Stop, "
                    "Pause, Skip Back, Skip Forward, Where Am I, the three chapter "
                    "buttons, Slower, Faster, Normal Speed, Skip Silence, Volume "
                    "Down, Volume Up, Mute, and last of all Add to Favorites."
                ),
                keys=("Tab",),
                hear="Each control's name and state, one per press.",
            ),
            Step(
                title="Ask where you are",
                body=(
                    "Press Where Am I. On a recording or a podcast episode, you "
                    "hear how far in you are, how long it is and which chapter "
                    "you are in. On live radio, Quill Radio tells you it is live, "
                    "so there is no position to move through. Either way, you "
                    "always get an answer."
                ),
                command="radio.transport.announce_position",
                keys=("Ctrl+Shift+W",),
                hear="Either your position, or a sentence saying a live stream has none.",
            ),
            Step(
                title="Leave the player where it is",
                body=(
                    "Press Escape to close it, or leave it open and press "
                    "Ctrl+Tab to move to the next window. The Player is a real "
                    "window. You will find it on the Window menu, on the taskbar "
                    "and in the Ctrl+Tab order, so you can keep it handy beside "
                    "whatever else you are doing."
                ),
                keys=("Escape", "Ctrl+Tab"),
                hear="The name of the window you are back in, or the one you moved to.",
            ),
            Step(
                title="Find the status bar, which Tab never reaches",
                body=(
                    "Go back to the main window and press F6. You land in the "
                    "status bar along the bottom: Play, Mute, Volume, Record, the "
                    "sleep timer and the time. Move across them with Left and "
                    "Right Arrow. Tab never goes there, so F6 is the way in, and "
                    "F6 again or Escape is the way back."
                ),
                keys=("F6", "Left arrow", "Right arrow"),
                hear="The item you land on, then each item as you arrow across.",
                note=(
                    "Each item has its own menu on the Applications key, and "
                    "there is a lot in there. The Play item offers your favorites "
                    "and recent stations. Record offers scheduling and the "
                    "Recordings window. Volume offers boost, the output device "
                    "and Sound Enhancements."
                ),
            ),
        ),
        closing=(
            "Nicely done. The player keys work the same in Browse Stations, Find "
            "Stations, Manage Favorites, the Recordings list, Song History, the "
            "chapter list, Now Playing and the download queue. Learn them once "
            "and they are yours everywhere."
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
            "Forgot a key? No problem. You will learn three ways to reach "
            "anything without remembering a key: the command palette, the "
            "numbered list of places, and a sheet that lists every key you have."
        ),
        steps=(
            Step(
                title="Open the command palette",
                body=(
                    "The command palette opens from any window and lists every "
                    "command in Quill Radio, including all the player controls. "
                    "So you can pause what is playing from here, as well as "
                    "change a setting."
                ),
                command="app.command_palette",
                hear="A search box, and how many commands are available.",
            ),
            Step(
                title="Type what you want, not what it is called",
                body=(
                    "Type a few letters, such as vol, or record, or chapter. The "
                    "list gets shorter as you type. Arrow to the one you want and "
                    "press Enter. It does exactly what its key or menu item "
                    "would do."
                ),
                keys=("Down arrow", "Enter"),
                hear="The matching commands, each read with its own key.",
                note=(
                    "Each command in the list says its key, so you pick up the "
                    "shortcuts just by using the palette. Before long you may "
                    "find you hardly need it."
                ),
            ),
            Step(
                title="Open the list of places",
                body=(
                    "Go To is a short numbered list of the ten main places in "
                    "Quill Radio. Press a number and you are there. Press Escape "
                    "and you are back exactly where you were."
                ),
                command="radio.go_to",
                keys=("Ctrl+G",),
                hear="A numbered list, starting with Favorites.",
            ),
            Step(
                title="Understand why the numbers are worth learning",
                body=(
                    "Each place keeps its number. Recordings is 4 today and it "
                    "will still be 4 next year, whether or not it is open. That "
                    "is different from Ctrl+1 to Ctrl+9, which go to the windows "
                    "you have open in the order you opened them, so those "
                    "numbers change as you work."
                ),
                keys=("Escape",),
                hear="Nothing new. This step is just good to know.",
            ),
            Step(
                title="Open the sheet of every key",
                body=(
                    "The Keyboard Shortcuts Sheet lists every key Quill Radio "
                    "answers to. Type what you want to do, such as record, or a "
                    "key you found and cannot place, such as Ctrl+B, and the list "
                    "shrinks to just that."
                ),
                keys=("Ctrl+Alt+Shift+K",),
                hear="A filter box, then how many shortcuts are listed.",
                note=(
                    "The sheet always shows the keys you really have. If you "
                    "change a key, the sheet shows your key, not the original one."
                ),
            ),
            Step(
                title="Ask what the thing under your fingers is",
                body=(
                    "Press F1 anywhere. A window opens that tells you what the "
                    "window you are in is for, and then what the control you are "
                    "on does and how to use it. You can arrow through the text "
                    "and copy it. Press Escape and you are right back where you "
                    "were."
                ),
                keys=("F1",),
                hear="What the window is for, then help for the control you are on.",
            ),
        ),
        closing=(
            "With the palette, Go To, the sheet and F1, you always have a way to "
            "find what you need, wherever you are in Quill Radio. You never have "
            "to feel stuck."
        ),
        then=("getting-unstuck",),
    ),
)
