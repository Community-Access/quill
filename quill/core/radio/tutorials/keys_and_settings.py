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
            "Change any key to one you prefer, give the player keys that work "
            "even while you are in another program, and find out which keys "
            "already work everywhere."
        ),
        steps=(
            Step(
                title="Find the key you want to change",
                body=(
                    "Keyboard Shortcuts, on the Help menu, opens the Keymap "
                    "Editor. It lists every command and its key, and you can "
                    "search it. Type part of a command's name, or type or press "
                    "a key to find out what it does."
                ),
                keys=("Ctrl+Alt+K",),
                hear="Keymap Editor, then the Search box.",
            ),
            Step(
                title="Assign a key and hear the objection",
                body=(
                    "Select a command and choose Edit Keybinding. If the key you "
                    "press is already used, the editor tells you which command "
                    "has it and asks before taking it. Keys your screen reader "
                    "needs are not allowed, and you get a warning for keys "
                    "another program already uses everywhere. That way you never "
                    "end up with a key that does nothing."
                ),
                keys=("Alt+E",),
                hear=(
                    "Either your new key confirmed, or the name of the command that already has it."
                ),
                note=(
                    "Your keys are shared with QUILL and QUILL Cast, so a key "
                    "you change here changes there too."
                ),
            ),
            Step(
                title="Check what you actually have",
                body=(
                    "The Keyboard Shortcuts Sheet always shows the keys you "
                    "really have, so after a change it shows your new key. It "
                    "also lists keys that are not on any menu, such as F6 for "
                    "the status bar, the Winamp letters in the Recordings list, "
                    "and Shift+F10 for a row's actions, each with the window it "
                    "works in."
                ),
                keys=("Ctrl+Alt+Shift+K",),
                hear="A filter box, then how many shortcuts are listed.",
            ),
            Step(
                title="Give the player a system-wide key",
                body=(
                    "Global Hotkeys, on the Help menu, lets you set keys that "
                    "work even while you are in another program. They are only "
                    "for safe playback commands: play/pause, stop, mute, volume "
                    "up and down, and show or hide to the tray. Choose Assign, "
                    "press the key you want, then Save."
                ),
                keys=("Ctrl+Alt+G",),
                hear="Global Hotkeys, then a list of commands, each with its global key or none.",
                note=(
                    "None are set to start with. If another program already "
                    "uses a key, Quill Radio leaves it alone and tells you which "
                    "ones were taken."
                ),
            ),
            Step(
                title="Use the two you already have",
                body=(
                    "Two keys work everywhere without any setup. The media keys "
                    "on your keyboard play, pause and stop while Quill Radio is "
                    "running, even from the tray. And Ctrl+Alt+Shift+R shows or "
                    "hides the Quill Radio window from any program. Each Quill "
                    "app has its own key for this, so they never get mixed up."
                ),
                keys=("Ctrl+Alt+Shift+R",),
                hear="Quill Radio hidden to the tray, then Quill Radio shown.",
            ),
            Step(
                title="Know the block that is not yours to take",
                body=(
                    "Quill Radio never uses Ctrl+Alt with an arrow key. JAWS and "
                    "NVDA use those keys to move around tables, so a key there "
                    "would stop working whenever you read a table. When you "
                    "choose your own keys, it is best to leave them alone too."
                ),
                hear="Nothing. This step is just good to know.",
            ),
        ),
        closing=(
            "The lessons always name commands rather than keys, so once you "
            "change a key, the lessons show your new key too. Make it yours."
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
            "A friendly walk through Preferences, stopping only at the settings "
            "you will really notice. Everything else is fine just as it is."
        ),
        steps=(
            Step(
                title="Open Preferences",
                body=(
                    "Preferences is one window with a lot in it. Instead of "
                    "reading it from top to bottom, this lesson stops at six "
                    "settings. The rest are set sensibly already, and you can "
                    "leave them until you find a reason to change them."
                ),
                keys=("Ctrl+,",),
                hear="Quill Radio Preferences, and its first checkbox.",
            ),
            Step(
                title="Decide what closing the window means",
                body=(
                    "When closing the window offers Ask every time, Exit, or "
                    "Minimize to Tray. It decides what happens when you close the "
                    "main window. Station > Exit always really closes Quill "
                    "Radio. Further down, the checkbox Alt+F4 minimizes to the "
                    "system tray is a separate choice. Turn it on, and Alt+F4 "
                    "tucks the radio away while it keeps playing."
                ),
                hear="When closing the window, combo box, and its current choice.",
                note=(
                    "If you are recording, Quill Radio always asks before it "
                    "closes, because closing stops the recording."
                ),
            ),
            Step(
                title="Leave the playback engine alone unless something is wrong",
                body=(
                    "Playback engine: Automatic uses the mpv engine when it is "
                    "there. That is what lets you pause and rewind live radio, "
                    "choose an output device, use Volume Boost, and play stations "
                    "in more formats. Windows Media (classic) is there if you "
                    "ever want the old way back."
                ),
                hear="Playback engine, combo box, Automatic (recommended).",
                note=(
                    "If Rewind, Volume Boost or the output device say they need "
                    "the mpv engine, check this setting. If it is already on "
                    "Automatic, Audio Health will tell you if the engine is "
                    "missing."
                ),
            ),
            Step(
                title="Send the radio to a different speaker",
                body=(
                    "Radio output device, in Preferences, and Output Device on "
                    "the Audio menu, send just the radio to a second sound card "
                    "or a USB headset. Your screen reader and Quill Radio's own "
                    "sounds stay where they are. So you can have the radio in "
                    "the speakers and your screen reader in your headphones."
                ),
                keys=("Ctrl+Shift+D",),
                hear="Output Device, the device list, then Output device and the name you chose.",
                note=(
                    "If you unplug the device, Quill Radio remembers it for next "
                    "time. Meanwhile it plays through your usual device and "
                    "tells you so."
                ),
            ),
            Step(
                title="Make the text bigger",
                body=(
                    "Text Size, on the View menu, offers Normal, Large or Larger. "
                    "It makes the favorites list, the buttons, the now playing "
                    "line and the status bar bigger, and it is remembered next "
                    "time."
                ),
                keys=("Ctrl+Alt+1", "Ctrl+Alt+2", "Ctrl+Alt+3"),
                hear="Text size, and the size you chose.",
            ),
            Step(
                title="Turn off whole areas you never use",
                body=(
                    "Customize Features, on the View menu, hides a whole menu and "
                    "everything on it. Right now that is Recording, for anyone "
                    "who just wants a plain radio with less to arrow past. "
                    "Nothing is deleted. Check it again and it comes back. The "
                    "menu changes the next time you open Quill Radio."
                ),
                keys=("Ctrl+Alt+C",),
                hear=(
                    "Recording, with a short description of what it covers. After OK, "
                    "Feature settings saved."
                ),
            ),
            Step(
                title="Put your setup where a sync service can see it",
                body=(
                    "The Data Folder button in Preferences shows where all your "
                    "Quill apps keep your settings, favorites, subscriptions and "
                    "listening places. Move it into a folder that Dropbox, "
                    "OneDrive, Google Drive or iCloud already syncs, and your "
                    "whole setup follows you between computers. No account and "
                    "no sign-in needed."
                ),
                hear="Data Folder, the current folder, and an offer to restart after a change.",
                note=(
                    "One thing to remember: do not run Quill apps on two "
                    "computers using the same folder at the same time. If you "
                    "do, Quill Radio tells you next time it opens."
                ),
            ),
        ),
        closing=(
            "That is six settings, and you are done. If you only change one, "
            "make it what closing the window does. It decides whether the radio "
            "keeps playing when your hand slips."
        ),
    ),
)
