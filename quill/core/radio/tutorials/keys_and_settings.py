"""Track 3, second half: the keys, and the settings that change how it feels.

Two lessons. The first is about taking the keyboard over -- rebinding, and
giving the transport a key that works while another program has focus. The
second is a guided pass through Preferences, which is long enough that most
people never read it and therefore never find the four settings that would
have changed their week.
"""

from __future__ import annotations

from quill.core.tutorials.model import Step, Tutorial

TUTORIALS: tuple[Tutorial, ...] = (
    Tutorial(
        slug="keys-that-are-yours",
        title="Make the keys yours",
        track="yours",
        minutes=6,
        surfaces=("Quill Radio", "Keyboard Shortcuts Sheet"),
        summary=(
            "Rebind anything, give the player keys that work from inside other "
            "programs, and know which keys are already system-wide before you "
            "start."
        ),
        steps=(
            Step(
                title="Find the key you want to change",
                body=(
                    "The Keyboard Manager is a searchable, conflict-aware list of "
                    "every command and the key assigned to it. Search by what the "
                    "command does rather than by its name -- the search matches "
                    "both."
                ),
                keys=("Alt+H",),
                hear="A search box, then commands with their current keys.",
            ),
            Step(
                title="Assign a key and hear the objection",
                body=(
                    "Assign a new key and the manager warns you if it is already "
                    "in use, or if it is a risky one such as a plain letter or an "
                    "arrow key. Clear a key to leave a command reachable only by "
                    "menu, or restore the defaults for everything."
                ),
                hear="Either the new key confirmed, or the conflict named.",
                note=(
                    "The keymap is shared with QUILL and QUILL Cast, so a "
                    "shortcut you change here changes it in the editor too. A few "
                    "commands whose default is a two-key chord keep their built-in "
                    "key until you next launch the app."
                ),
            ),
            Step(
                title="Check what you actually have",
                body=(
                    "The Keyboard Shortcuts Sheet is built by reading the menu bar "
                    "in front of you, so after a rebinding it says your key rather "
                    "than the default. It also lists the keys no menu item carries "
                    "-- F6 into the status bar, the Winamp letters in the "
                    "Recordings list, Shift+F10 for a row's actions -- each with "
                    "the window it works in."
                ),
                keys=("Ctrl+Alt+Shift+K",),
                hear="A filter box, then the number of shortcuts listed.",
            ),
            Step(
                title="Give the player a system-wide key",
                body=(
                    "Global Hotkeys assigns a key that works while another program "
                    "has focus, for the safe playback verbs only: play/pause, "
                    "stop, mute, volume up and down, and show or hide to the tray. "
                    "A global key can never trigger anything that changes a "
                    "document or a file."
                ),
                keys=("Alt+H",),
                hear="Each transport action with its global key, or none.",
                note=(
                    "None are set by default. The first time you assign one, Quill "
                    "Radio reminds you that a system-wide key may override the "
                    "same key in another program -- and a key another app already "
                    "owns is left alone rather than fought over."
                ),
            ),
            Step(
                title="Use the two you already have",
                body=(
                    "Two system-wide keys work without being set up. Your "
                    "keyboard's media keys drive play/pause and stop while Quill "
                    "Radio runs, even from the tray; and Ctrl+Alt+Shift+R shows or "
                    "hides the window from any program. Each app in the family "
                    "uses its own chord, so they never clash."
                ),
                keys=("Ctrl+Alt+Shift+R",),
                hear="Hidden to the tray, then Shown.",
            ),
            Step(
                title="Know the block that is not yours to take",
                body=(
                    "Nothing in Quill Radio sits on Ctrl+Alt+arrow. That block "
                    "belongs to JAWS's and NVDA's table navigation, and a key "
                    "there works everywhere except while somebody is reading a "
                    "table. If you are choosing your own keys, leave it alone for "
                    "the same reason."
                ),
                hear="Nothing: this is a rule, not an action.",
            ),
        ),
        closing=(
            "Every tutorial in this set names commands rather than keys, so once "
            "you have rebound something the lessons say your key too."
        ),
        then=("settings-worth-changing",),
    ),
    Tutorial(
        slug="settings-worth-changing",
        title="The settings actually worth changing",
        track="yours",
        minutes=8,
        surfaces=("Preferences", "Quill Radio"),
        summary=(
            "A guided pass through Preferences, stopping only at the settings "
            "that change something you will notice. Everything else can stay as "
            "it is."
        ),
        steps=(
            Step(
                title="Open Preferences",
                body=(
                    "Preferences is one window with a lot in it. Rather than "
                    "reading it top to bottom, this lesson stops at six settings; "
                    "the rest are sensible defaults that you can leave alone until "
                    "something makes you want them."
                ),
                keys=("Ctrl+,",),
                hear="Entered Preferences.",
            ),
            Step(
                title="Decide what closing the window means",
                body=(
                    "When closing the window offers Ask every time, Exit, or "
                    "Minimize to Tray, and governs the titlebar X and Station > "
                    "Exit. Beside it, Alt+F4 minimizes to the system tray is its "
                    "own switch: turn it on and the reflexive close tucks the "
                    "radio away still playing, while X and Exit keep the setting "
                    "above."
                ),
                hear="The choice read back.",
                note=(
                    "The one thing that always asks first is a recording in "
                    "progress, because exiting stops the capture."
                ),
            ),
            Step(
                title="Leave the playback engine alone unless something is wrong",
                body=(
                    "Automatic uses the bundled mpv engine, which is what powers "
                    "pausing and rewinding live radio, the output device choice, "
                    "Volume Boost, track titles from the stream, and stations in "
                    "more formats. Windows Media (classic) is exactly the "
                    "pre-1.1 behaviour if you ever want it back."
                ),
                hear="The engine name read back.",
                note=(
                    "If Rewind, Volume Boost or the output device say they need "
                    "the mpv engine, this setting is why -- or the bundled engine "
                    "is missing, which Audio Health will tell you."
                ),
            ),
            Step(
                title="Send the radio to a different speaker",
                body=(
                    "Radio output device routes just the radio to a second sound "
                    "card or a USB headset. Your screen reader and Quill Radio's "
                    "own sounds stay on the system default device, which is the "
                    "whole reason this setting exists rather than your using "
                    "Windows' own."
                ),
                keys=("Ctrl+Shift+D",),
                hear="The device list, and the one currently in use.",
                note=(
                    "An unplugged device is remembered rather than reset, and if "
                    "it cannot be used the radio plays through the default and "
                    "says so."
                ),
            ),
            Step(
                title="Make the text bigger",
                body=(
                    "Text Size on the View menu -- Normal, Large or Larger -- "
                    "scales the favorites list, the buttons, the now-playing line "
                    "and the status bar. It is remembered between sessions."
                ),
                keys=("Alt+V",),
                hear="The size read back, and the window redrawn.",
            ),
            Step(
                title="Turn off whole areas you never use",
                body=(
                    "Customize Features leaves out a whole menu and every command "
                    "under it -- Recording, for instance, if you want a plain "
                    "radio and nothing else to arrow past. Nothing is deleted; "
                    "tick it again and it comes back, and a feature added in a "
                    "future version arrives switched on."
                ),
                keys=("Alt+V",),
                hear="Each area with a short description of what it covers.",
            ),
            Step(
                title="Put your setup where a sync service can see it",
                body=(
                    "The Data Folder button opens the family-wide data location -- "
                    "settings, favorites, subscriptions and playback positions for "
                    "every Quill app. Point it at a folder Dropbox, OneDrive, "
                    "Google Drive or iCloud already syncs and your whole setup "
                    "travels between computers, with no account and no sign-in."
                ),
                hear="The current folder, and an offer to restart after a change.",
                note=(
                    "One rule: do not run Quill apps on two computers against the "
                    "same folder at the same time. If you do, the next launch says "
                    "so rather than letting two machines fight over one profile."
                ),
            ),
        ),
        closing=(
            "Six settings. If you only change one, make it the closing "
            "behaviour -- it is the one that decides whether the radio keeps "
            "playing when your hand slips."
        ),
    ),
)
