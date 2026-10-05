"""QUILL Cast, track 1: your first hour.

Five lessons. Follow something and play it; learn the one window -- the Places
list, Find, the status bar -- and the Now Playing window beside it; and know
what to do the first time something goes wrong. That last one is here rather
than at the end on purpose: F9, Ctrl+Z and Recent Problems are worth most to
somebody who has only just started.
"""

from __future__ import annotations

from quill.core.tutorials.model import Step, Tutorial

TUTORIALS: tuple[Tutorial, ...] = (
    Tutorial(
        slug="first-hour",
        title="The first hour",
        track="first-hour",
        minutes=12,
        surfaces=("Welcome to QUILL Cast", "Add Podcast", "QUILL Cast"),
        summary=(
            "Follow your first podcast, play one of its episodes, pause it, skip "
            "around in it and line up something for later. Take your time. By the "
            "end you will know the handful of keys that do most of the work."
        ),
        steps=(
            Step(
                title="Answer the welcome, or skip it",
                body=(
                    "The first time you open Cast, a short welcome window says hello. "
                    "It asks one question: where you would like to land each time "
                    "Cast opens. If you are not sure, leave it on What is new. Add "
                    "Your First Podcast takes you straight to finding one, and Skip "
                    "closes the welcome without changing anything."
                ),
                keys=("Alt+W", "Alt+A", "Escape"),
                hear="The welcome words, then the question about where to land.",
                note=(
                    "If you already have podcasts, from a backup or another Quill "
                    "app, the welcome does not appear at all."
                ),
            ),
            Step(
                title="Find a podcast by name",
                body=(
                    "Think of a podcast you have heard about. Add Podcast opens with "
                    "your cursor in the Podcast name box. Type a few words of its "
                    "name and press Enter. You do not need its web address. The name "
                    "is enough."
                ),
                keys=("Ctrl+N", "Enter"),
                hear="How many podcasts it found, and where they came from.",
            ),
            Step(
                title="Follow the one you want",
                body=(
                    "Move to the Results list and arrow through it. When you hear the "
                    "one you want, press Follow. Not sure it is the right one? Press "
                    "Enter on it instead, and Cast lets you hear about it and its "
                    "recent episodes before you decide. Press Escape when you are done."
                ),
                keys=("Alt+R", "Alt+O"),
                hear="Now following, the podcast's name, and how many episodes it has.",
                check="subscriptions-grew",
                note=(
                    "Follow ACB Media Podcasts on the Podcasts menu follows ACB "
                    "Media's whole directory in one step, and Import OPML in the Add "
                    "Podcast window brings your list across from another app."
                ),
            ),
            Step(
                title="Play its next unheard episode",
                body=(
                    "Now for the good part. Go to Podcasts, your library, with one "
                    "row for each podcast you follow. Arrow to the one you just "
                    "followed and press Enter. Cast plays its next unheard episode. "
                    "Want a particular one? Right Arrow opens the podcast so you can "
                    "pick from its episodes, newest first."
                ),
                keys=("Ctrl+Shift+S", "Enter", "Right Arrow"),
                hear="The episode Cast is playing, then the audio.",
                check="playing",
            ),
            Step(
                title="Pause, skip and turn it up",
                body=(
                    "Let it play for a moment, then try each of these. They work from "
                    "anywhere in Cast. Press pause, then press it again to carry on "
                    "from the same spot. Skip forward jumps 30 seconds and skip back "
                    "jumps 15. The volume keys tell you the new volume."
                ),
                keys=("Ctrl+P", "Ctrl+Right", "Ctrl+Left", "Ctrl+Up", "Ctrl+Down"),
                hear="Paused, then where you landed after each skip, and the new volume.",
                check="paused",
            ),
            Step(
                title="Ask what is playing",
                body=(
                    "Lost track of what is on? This key works from anywhere in Cast "
                    "and tells you the episode, the podcast and how far in you are. "
                    "Nothing opens and nothing changes, so press it as often as you "
                    "like."
                ),
                keys=("Ctrl+T",),
                hear="The episode, its podcast, and how far in you are.",
            ),
            Step(
                title="Line up something for later",
                body=(
                    "The Play Queue is your listening list for later. When one "
                    "episode finishes, the next one in the queue plays. Open a "
                    "podcast's episodes, arrow to one you would like to hear later, "
                    "and press Space. That is all it takes."
                ),
                keys=("Space",),
                hear="Added to the Play Queue.",
                check="queue-grew",
            ),
            Step(
                title="Stop, and know your place is kept",
                body=(
                    "Stop when you are done. Do not worry about losing your place. "
                    "Cast remembers it, so the episode picks up from the same spot "
                    "today or next month. If you would like Cast to start playing the "
                    "moment it opens, turn on Resume Last Episode on Launch, on the "
                    "Podcasts menu."
                ),
                keys=("Ctrl+.", "Ctrl+Alt+Shift+L"),
                hear="Stopped. Later, the episode carrying on from where you left it.",
            ),
        ),
        closing=(
            "Well done. You have followed a podcast, heard it, paused it, skipped "
            "through it and lined up something for later. That is a real first "
            "session. Next, let's find our way around the rest of the window."
        ),
        then=("places", "when-something-breaks"),
    ),
    Tutorial(
        slug="places",
        title="Places",
        track="first-hour",
        minutes=8,
        surfaces=("QUILL Cast", "Places"),
        summary=(
            "Everything in Cast happens in one window, and the Places list is its "
            "map. You will step into a place and back out, jump to one with its "
            "own key, put them in your order, and read everything at once in the "
            "status bar."
        ),
        steps=(
            Step(
                title="Go to the Places list",
                body=(
                    "Each row is a place with a count beside it: Inbox, New Episodes, "
                    "Continue Listening, Favorites, Playlists, Personal Audio, Play "
                    "Queue, Downloads, Notifications and Podcasts. Think of each "
                    "place as a list with one job. The count tells you how much is "
                    "waiting there."
                ),
                keys=("Alt+L",),
                hear="Places, then the place you are on with its count.",
            ),
            Step(
                title="Peek, then step in and back out",
                body=(
                    "Arrow up and down the list and the area beside it changes as you "
                    "go, so you can peek into a place without going in. Enter or Right "
                    "Arrow steps into the place you are on. Backspace, or Left Arrow "
                    "on the first row, steps back out to the Places list."
                ),
                keys=("Down Arrow", "Enter", "Backspace"),
                hear="Each place with its count, then the first row inside it.",
                note=(
                    "Walk into an empty place and Cast tells you, once, what fills "
                    "it -- in an empty Play Queue, that Space on any episode adds it."
                ),
            ),
            Step(
                title="Jump straight to a place",
                body=(
                    "Every place has its own key that works from anywhere in the "
                    "window. Try the Inbox, the Play Queue, Continue Listening, "
                    "Podcasts and Downloads. You do not have to memorise them: they "
                    "are all on the View menu, each with its key."
                ),
                command="podcasts.inbox",
                keys=("Ctrl+Shift+I", "Ctrl+Shift+Q", "Ctrl+Shift+L", "Ctrl+Shift+S", "Ctrl+D"),
                hear="The place, with focus on its first row.",
            ),
            Step(
                title="Get home from anywhere",
                body=(
                    "Wherever you have wandered, this takes you back to the place Cast "
                    "opens on, with the cursor on its first row. In a text box, such "
                    "as the show notes or Find, it does its usual job instead and "
                    "moves to the top of the text."
                ),
                keys=("Ctrl+Home",),
                hear="The place Cast opens on, and its first row.",
            ),
            Step(
                title="Put the places in your order",
                body=(
                    "On the Places list, move a place up or down and Cast says where "
                    "it went. Delete hides a place you never use; its key still works "
                    "and Ctrl+Z brings it back. F2 gives a place your own name -- call "
                    "the Inbox Morning pile if you like."
                ),
                keys=("Alt+Shift+Up", "Alt+Shift+Down", "Delete", "F2"),
                hear="Where it went, such as Continue Listening moved to first.",
            ),
            Step(
                title="Arrange them all at once",
                body=(
                    "View, Places opens a window where you can move, hide, show and "
                    "rename every place, and Reset to Default puts it all back. This "
                    "is also where you show Recently Expired, which starts hidden."
                ),
                keys=("Ctrl+Shift+G",),
                hear="The Places window, with your places in order.",
            ),
            Step(
                title="Ask what a whole place can do",
                body=(
                    "On the Places list, the Applications key opens a menu of what the "
                    "whole place can do: Clear Entire Queue on the Play Queue, Mark "
                    "All as Played on the Inbox. The same menu has Rename, Hide, Move "
                    "Up and Move Down, in case you forget the keys."
                ),
                keys=("Applications", "Shift+F10"),
                hear="A menu of the place's own actions.",
            ),
            Step(
                title="Read everything at once in the status bar",
                body=(
                    "Tab does not stop on the status bar, so press F6 to step into "
                    "it. Left and Right Arrow move from cell to cell: what is playing, "
                    "volume, speed, the Queue, Inbox and Downloads counts, the sleep "
                    "timer and the clock. Enter uses a cell, and F6 or Escape steps "
                    "out."
                ),
                keys=("F6", "Right Arrow", "Enter", "Escape"),
                hear="Each cell in turn, such as the speed and whose it is.",
            ),
            Step(
                title="Reach anywhere with Go To",
                body=(
                    "Go To is one key that reaches everything. It opens a short "
                    "numbered list of places, and the numbers never change, so your "
                    "fingers soon learn them. Press a number to go there, or Escape "
                    "to stay put. Each row also tells you the place's own key."
                ),
                keys=("Ctrl+G",),
                hear="A numbered list of places, then the one you chose.",
                note="Settings, inside Go To, chooses which ten places are on it.",
            ),
        ),
        closing=(
            "Nicely done. You can now reach any place in a couple of keystrokes. "
            "Next, Find takes you to any podcast or episode in a word or two."
        ),
        then=("find", "now-playing"),
    ),
    Tutorial(
        slug="find",
        title="Find",
        track="first-hour",
        minutes=4,
        surfaces=("QUILL Cast", "Search Everywhere"),
        summary=(
            "Find a podcast, an episode or one of your own notes by typing a word "
            "or two. Then play it, or do anything else with it, and get back to "
            "your library exactly as you left it."
        ),
        steps=(
            Step(
                title="Go to Find from anywhere",
                body=(
                    "Find looks through podcast names, episode titles and the notes "
                    "you wrote yourself, all at once. It sits near the top of the "
                    "window, and this key takes you there from anywhere in Cast."
                ),
                keys=("Ctrl+F", "Alt+N"),
                hear="Find, edit.",
            ),
            Step(
                title="Type a word or two",
                body=(
                    "Type part of a podcast's name, an episode title, or something "
                    "from one of your notes. The list beside Places fills with "
                    "matches, and when you pause typing Cast says how many it found."
                ),
                hear="How many matches, such as 14 matches for bristol.",
            ),
            Step(
                title="Move into the matches",
                body=(
                    "Down Arrow moves into the results. Each row says what it is, "
                    "such as The Daily, a podcast. Podcasts come first, then episodes "
                    "newest first, then your notes."
                ),
                keys=("Down Arrow",),
                hear="The first match, and what kind of thing it is.",
            ),
            Step(
                title="Play it, or do something else",
                body=(
                    "Enter plays what you are on. Shift+F10 or the Applications key "
                    "opens everything else you can do with it: queue it, download it, "
                    "read its show notes, and the rest."
                ),
                keys=("Enter", "Shift+F10"),
                hear="The episode playing, or its menu.",
                check="playing",
            ),
            Step(
                title="Put your library back",
                body=(
                    "Press Escape to leave Find. Your library comes back with the "
                    "cursor right where you left it, so a quick look never loses your "
                    "place in a long list."
                ),
                keys=("Escape",),
                hear="Your place again, with the cursor where you left it.",
            ),
            Step(
                title="Narrow every list instead",
                body=(
                    "When you want fewer rows rather than one row, View, Show narrows "
                    "every list at once: All Episodes, Unheard Only, Started Only, "
                    "Downloaded Only or Played Only. View, Sort Episodes puts them in "
                    "the order you like."
                ),
                keys=("Alt+V",),
                hear="Each list showing only what you chose.",
            ),
        ),
        closing=(
            "That is it. Between the Places list, Go To and Find, nothing in Cast "
            "is more than a few keys away."
        ),
        then=("now-playing",),
    ),
    Tutorial(
        slug="now-playing",
        title="Now Playing",
        track="first-hour",
        minutes=7,
        surfaces=("Now Playing",),
        summary=(
            "Now Playing is a window with every control for the episode you are "
            "hearing: position, speed, volume, chapters, show notes and a note of "
            "your own. It sits beside the main window, and Tab takes you through "
            "it all."
        ),
        steps=(
            Step(
                title="Open Now Playing",
                body=(
                    "Now Playing is a window of its own, beside the main one. It is "
                    "a nice place to sit for an evening without your library in the "
                    "way. Ctrl+2 always opens it, and you will find it on the Window "
                    "and Episode menus too."
                ),
                command="podcasts.now_playing",
                keys=("Ctrl+2", "Ctrl+Alt+2"),
                hear="Now Playing, then the podcast's name.",
            ),
            Step(
                title="Read what is playing, and from where",
                body=(
                    "The first lines name the podcast, the episode, and where it is "
                    "playing from, such as the Inbox or the Play Queue. Tab moves you "
                    "on through everything else in the window."
                ),
                keys=("Tab",),
                hear="The podcast, the episode, then where it is playing from.",
            ),
            Step(
                title="Move with the Position slider",
                body=(
                    "Left and Right Arrow move 5 seconds, Page Up and Page Down move "
                    "30, and Home and End go to the start and the end. Cast says "
                    "where you are after each move."
                ),
                keys=("Left Arrow", "Right Arrow", "Page Up", "Page Down"),
                hear="Your new position after each move.",
            ),
            Step(
                title="Choose a speed, or a volume",
                body=(
                    "Speed is a list of speeds, with Custom for one you type. Volume "
                    "is a slider, with Mute beside it. Further on are the sleep timer "
                    "controls, which the Sleep and speed lesson covers."
                ),
                keys=("Tab", "Down Arrow"),
                hear="The speed or volume you chose.",
            ),
            Step(
                title="Jump to a chapter",
                body=(
                    "The Chapters list shows the episode's chapters, and the one "
                    "playing says playing. Press Enter on any row to go there. An "
                    "episode without chapters may still have some that Cast worked "
                    "out for you."
                ),
                keys=("Tab", "Enter"),
                hear="The chapter list, then the episode at the chapter you chose.",
            ),
            Step(
                title="Leave a note as you listen",
                body=(
                    "Your note is a box for a thought about this episode. Type it and "
                    "move on. Cast saves it when you leave the box, so there is no "
                    "button to press. Empty the box to remove the note. You will find "
                    "it with the episode's notes elsewhere too."
                ),
                keys=("Tab",),
                hear="Note saved.",
            ),
            Step(
                title="Ask how long is left, or ask everything",
                body=(
                    "Time Remaining tells you how far in you are, how much is left, "
                    "and how long that will really take at your speed. Player "
                    "Information puts every detail about the episode in a box you can "
                    "read at your own pace and copy from. Both work from anywhere in "
                    "Cast."
                ),
                command="podcasts.time_remaining",
                keys=("Ctrl+Shift+T", "Ctrl+I"),
                hear="Something like 12:04 of 31:50, 20 minutes left.",
            ),
            Step(
                title="Go back to the main window",
                body=(
                    "Ctrl+1 always takes you back to the main window. Ctrl+W or "
                    "Alt+F4 hides Now Playing, and Ctrl+2 brings it back with your "
                    "place in it intact. The episode keeps playing either way."
                ),
                keys=("Ctrl+1", "Ctrl+W"),
                hear="The main window, on the row you left.",
                note=(
                    "Switch to Now Playing when playback starts, in Preferences under "
                    "Playing, brings this window forward every time an episode starts."
                ),
            ),
        ),
        closing=(
            "Now Playing is for the episode, and the main window is for everything "
            "else. Ctrl+1 and Ctrl+2 move you between them whenever you like."
        ),
        then=("keys", "sleep-and-speed"),
    ),
    Tutorial(
        slug="when-something-breaks",
        title="When something breaks",
        track="first-hour",
        minutes=7,
        surfaces=("Recent Problems", "Activity", "Undo History", "QUILL Cast"),
        summary=(
            "Everybody presses the wrong thing now and then. Here you will hear a "
            "message again, look back over what happened, see what went wrong and "
            "why, take back a mistake, and ask any window what it is for."
        ),
        steps=(
            Step(
                title="Hear the last thing again",
                body=(
                    "Messages go by fast, and you may have been busy with something "
                    "else. Press F9 and Cast says the last thing it told you again, "
                    "along with what you can do about it."
                ),
                command="app.repeat_last_result",
                keys=("F9",),
                hear="Cast's last message, again.",
            ),
            Step(
                title="Look back over this session",
                body=(
                    "Activity lists everything Cast has told you since you opened it, "
                    "good news and bad, newest first, one sentence a row. Enter on a "
                    "row does the first thing it offers. Retry tries it again, and "
                    "Copy Details copies the row in case you want to write to support."
                ),
                command="app.activity",
                keys=("Shift+F9",),
                hear="Activity, then the newest thing Cast reported.",
            ),
            Step(
                title="See what went wrong",
                body=(
                    "Recent Problems keeps the things that went wrong, today and "
                    "before: a podcast that would not load, a download that failed, a "
                    "stream that dropped. Each one says why and when. Retry tries one "
                    "again, and Copy All gives you the list with any passwords left out."
                ),
                command="app.recent_problems",
                keys=("Ctrl+Alt+Shift+P",),
                hear="Recent Problems, then the newest failure with its reason.",
                note=(
                    "Things Cast tried on its own and could not do, such as looking "
                    "at a watched folder, are written here too, even when they were "
                    "not worth interrupting you for."
                ),
            ),
            Step(
                title="Take back the last thing you did",
                body=(
                    "Undo Last Action brings back the last podcast you unfollowed, "
                    "the last episodes you removed or the last thing you marked, and "
                    "tells you what it restored. Press it again for the one before. "
                    "You will find it on the Edit menu, which is Alt+I in Cast."
                ),
                command="app.undo_last",
                keys=("Ctrl+Z",),
                hear="Undid, then what it brought back.",
                note=(
                    "When an action can be undone, Cast ends its message with Ctrl+Z "
                    "undoes this. Every question that would delete something starts "
                    "on No, so pressing Enter too soon is always safe."
                ),
            ),
            Step(
                title="Take back an older step on its own",
                body=(
                    "Sometimes the mistake was a few steps ago, and you want to keep "
                    "what you did since. Edit, Undo History lists the last ten things "
                    "you can take back, newest first. Choose one and press Undo This "
                    "One. Only that step is undone."
                ),
                keys=("Alt+I", "H"),
                hear="Undo History, then the newest thing you can take back.",
            ),
            Step(
                title="Ask any window what it is for",
                body=(
                    "Every window in Cast answers F1. You hear what the window is for, "
                    "then what the control you are on does. On a checkbox and not sure "
                    "what checking it will change? Press F1 first and find out."
                ),
                keys=("F1",),
                hear="What the window is for, then what this control does.",
            ),
            Step(
                title="Find a command you have forgotten",
                body=(
                    "Can't remember where something lives? The Command Palette lists "
                    "every command in Cast, even the Advanced ones and any you switched "
                    "off. Type a few letters, such as sleep or backup, arrow to the "
                    "command and press Enter. If it cannot run right now, it tells you "
                    "why."
                ),
                keys=("Ctrl+Shift+P",),
                hear="The Command Palette, then the commands matching what you type.",
            ),
            Step(
                title="Write to a person",
                body=(
                    "Still stuck? Get Help from Support, on the Help menu, opens your "
                    "own mail program with a message ready to go, so you can read it "
                    "over before you send it. A real person reads every message. Paste "
                    "in anything from Recent Problems or Activity that might help."
                ),
                keys=("Ctrl+Alt+F2",),
                hear="The support window, then your mail program with the message ready.",
                note="The address is support@community-access.org.",
            ),
        ),
        closing=(
            "Very little in Cast can go wrong for good. When something does, "
            "reach for F9, Recent Problems and Ctrl+Z first. You have finished your "
            "first hour."
        ),
        then=("the-inbox",),
    ),
)
