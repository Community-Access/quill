"""Quill Weather, track 2: being warned.

This is what the app is actually for. Five lessons: start the watch,
understand exactly what it does and does not promise, rehearse an alert
without waiting for weather, tune what gets through, and keep the watch
running when nothing else is.
"""

from __future__ import annotations

from quill.core.tutorials.model import Step, Tutorial

TUTORIALS: tuple[Tutorial, ...] = (
    Tutorial(
        slug="start-watching",
        title="Start the watch",
        track="watch",
        minutes=5,
        surfaces=("Quill Weather",),
        summary=(
            "Turn on Weather Monitoring, hear what it says as it starts, and know "
            "precisely what it is watching and how often."
        ),
        steps=(
            Step(
                title="Turn it on",
                body=(
                    "Weather Monitoring -- the Weather Guardian -- watches your "
                    "saved places' official watches, warnings and advisories and "
                    "speaks each new one the moment it is issued. The same key "
                    "turns it off, and the menu item says which it will do."
                ),
                command="weather.monitor_toggle",
                hear=(
                    "A single combined summary: 3 places: Tucson, Boston, "
                    "and Reno. All clear right now."
                ),
                check="monitoring-on",
            ),
            Step(
                title="Know that it watches all of them",
                body=(
                    "Every saved place is watched at once, with no setup: home, "
                    "work and family are all covered. Each alert names its place "
                    "when it is spoken and in its tray notification, so you never "
                    "have to work out which town a warning is for."
                ),
                hear="Each alert prefixed with the place it is for.",
            ),
            Step(
                title="Hear what an urgent one sounds like",
                body=(
                    "The most serious events -- a tornado warning, a flash flood "
                    "warning -- interrupt whatever your screen reader is saying. "
                    "Everything else waits its turn. That distinction is the whole "
                    "reason interrupting speech exists, and it is used sparingly on "
                    "purpose."
                ),
                hear="An interrupting announcement, then the alert, then the tray notice.",
            ),
            Step(
                title="Understand the rhythm",
                body=(
                    "While a warning is active it checks much more often -- as fast "
                    "as once a minute -- so you hear about changes quickly, then "
                    "eases back when the weather clears. You do not set that; it "
                    "follows the weather."
                ),
                hear="Nothing: this is what you will not notice happening.",
            ),
            Step(
                title="Snooze it without switching it off",
                body=(
                    "Pause Alert Checks stops the checking temporarily; the same "
                    "item then reads Resume Alert Checks. Use it for the hour you "
                    "are in a meeting rather than turning the watch off and "
                    "forgetting to turn it back on."
                ),
                command="weather.monitor_pause",
                hear="Alert checks paused -- and the menu item now offering to resume.",
                check="monitoring-paused",
            ),
            Step(
                title="Know that it comes back by itself",
                body=(
                    "Monitoring keeps running while the window is in the tray, and "
                    "starts again automatically the next time you launch. Choosing "
                    "Stop Weather Monitoring is what turns it off for good."
                ),
                hear="At the next launch: the same combined summary as when you started it.",
            ),
        ),
        closing=("The watch is the app. Everything else here is about making sure it reaches you."),
        then=("rehearse-an-alert", "what-gets-through"),
    ),
    Tutorial(
        slug="rehearse-an-alert",
        title="Rehearse an alert",
        track="watch",
        minutes=3,
        surfaces=("Quill Weather",),
        summary=(
            "See and hear exactly what a real warning will be like, at a moment of "
            "your choosing rather than at three in the morning."
        ),
        steps=(
            Step(
                title="Send yourself a test",
                body=(
                    "Test Alert shows you the whole thing: the spoken words, the "
                    "sound using your own sound settings, a system-tray "
                    "notification, and the alert window. All of it clearly marked "
                    "as a test."
                ),
                command="weather.test_alert",
                hear="The alert sound, then the spoken test alert.",
            ),
            Step(
                title="Dismiss it the way you will dismiss a real one",
                body=(
                    "The window closes with OK or Escape. Practising that once, "
                    "calmly, is worth more than reading about it -- the real one "
                    "arrives while you are doing something else."
                ),
                keys=("Enter", "Escape"),
                hear="The window closing.",
            ),
            Step(
                title="Know what it did not do",
                body=(
                    "It sends nothing over the internet and does not touch your "
                    "real monitoring. Nothing you do here can cost you a genuine "
                    "warning, which is what makes it safe to try whenever you like."
                ),
                hear="Nothing: this is the promise behind the button.",
            ),
            Step(
                title="Try it again after changing the sound",
                body=(
                    "This is also the right way to audition an alert sound: change "
                    "it in Settings, come back and test, and hear it in the exact "
                    "form a real alert will use, repeats included."
                ),
                command="weather.settings",
                hear="Your chosen sound, the number of times you asked for.",
            ),
        ),
        closing=(
            "Rehearse once when you set the app up, and again any time you change "
            "the sound or the severity filter."
        ),
        then=("what-gets-through",),
    ),
    Tutorial(
        slug="what-gets-through",
        title="Decide what gets through",
        track="watch",
        minutes=5,
        surfaces=("Weather Settings", "Quill Weather"),
        summary=(
            "Severity, event names, the sound and how often it repeats -- the four "
            "settings that decide whether the watch is useful or noisy."
        ),
        steps=(
            Step(
                title="Open Settings",
                body=(
                    "Four things here decide what an alert costs you. Everything "
                    "else in this window is about how the weather reads; this is "
                    "about how it interrupts."
                ),
                command="weather.settings",
                hear="Entered Weather Settings.",
            ),
            Step(
                title="Set the severity floor",
                body=(
                    "Show everything, or only Moderate and above, Severe and above, "
                    "and so on. Somewhere on the coast a Small Craft Advisory is "
                    "news; two hundred miles inland it is noise, and the app cannot "
                    "know which you are."
                ),
                hear="The severity choice read back.",
            ),
            Step(
                title="Hide the events you never want",
                body=(
                    "Below it is a list of specific event names to hide, one per "
                    "line. This is the finer tool: keep every severity but never "
                    "hear about Air Quality Alerts again, without dropping the "
                    "floor and losing something else."
                ),
                hear="Nothing spoken: the effect shows up the next time one of those is issued.",
            ),
            Step(
                title="Choose the sound, and hear it",
                body=(
                    "The alert sound can be switched off, or replaced with a .wav "
                    "of your own -- there is a Play button so you can hear a "
                    "candidate before committing, and Use Default to go back."
                ),
                hear="The sound you chose, played once.",
            ),
            Step(
                title="Decide how insistent it is",
                body=(
                    "The sound can play from one to ten times per alert. Once is "
                    "polite; five is what you want if you are in another room and "
                    "the tornado siren is the point of owning this app."
                ),
                hear="The repeat count read back.",
            ),
            Step(
                title="Set how often it refreshes",
                body=(
                    "The refresh interval governs the Weather Center's own "
                    "updating. It is never allowed faster than the National Weather "
                    "Service's recommended minimum, which is a courtesy to a free "
                    "public service everybody depends on."
                ),
                hear="The interval read back.",
            ),
        ),
        closing=(
            "A watch you have tuned is a watch you leave on. That is the only "
            "measure that matters here."
        ),
        then=("always-watching",),
    ),
    Tutorial(
        slug="always-watching",
        title="Keep the watch running",
        track="watch",
        minutes=5,
        surfaces=("Quill Weather",),
        summary=(
            "The tray, the global key, starting with Windows, and the background "
            "check that works with no Quill Weather running at all."
        ),
        steps=(
            Step(
                title="Send the window to the tray",
                body=(
                    "Minimize to Tray tucks the window away and monitoring keeps "
                    "going. Quill Weather is built to keep running: the window is a "
                    "way of asking it things, not the app itself."
                ),
                keys=("Ctrl+W",),
                hear="Hidden to the tray.",
            ),
            Step(
                title="Get it back from anywhere",
                body=(
                    "Ctrl+Alt+Shift+W shows and hides Quill Weather from any "
                    "program, even without focus, and says which it did. The chord "
                    "is unique to this app -- QUILL is Ctrl+Alt+Shift+Q and Quill "
                    "Radio is Ctrl+Alt+Shift+R -- so the three never collide."
                ),
                keys=("Ctrl+Alt+Shift+W",),
                hear="Shown -- and Hidden to the tray when you press it again.",
                note=(
                    "If another program already owns that chord, Quill Weather "
                    "leaves it alone rather than fighting for it, and the tray icon "
                    "still works."
                ),
            ),
            Step(
                title="Make closing safe",
                body=(
                    "By default the close button also goes to the tray rather than "
                    "quitting, so a stray Alt+F4 does not end your watch. Only Exit "
                    "truly quits. Options has the switch if you would rather close "
                    "mean close."
                ),
                keys=("Ctrl+Alt+C",),
                hear="The setting read back.",
            ),
            Step(
                title="Start watching at sign-in",
                body=(
                    "Start Quill Weather with Windows launches it when you sign in. "
                    "Pair it with Start minimized to the tray and the watch is on "
                    "from the moment you sit down, with no window in your way."
                ),
                keys=("Ctrl+Alt+W", "Ctrl+Alt+M"),
                hear="Each setting read back.",
            ),
            Step(
                title="Be covered with nothing running at all",
                body=(
                    "Check for alerts in the background registers a Windows "
                    "scheduled task that checks on your interval and shows a toast "
                    "if it finds something -- so you are covered even with no Quill "
                    "Weather process running."
                ),
                keys=("Ctrl+Alt+B",),
                hear="The setting read back, and Windows confirming the task.",
            ),
            Step(
                title="Know what the tray menu holds",
                body=(
                    "Right-click the tray icon, or use the Applications key, for "
                    "the current monitoring status, Open Weather Center, Quick "
                    "Weather, Start or Stop Monitoring, Open Quill Radio, Open "
                    "QUILL, Show and Exit."
                ),
                keys=("Shift+F10",),
                hear="The menu, led by the monitoring status.",
            ),
        ),
        closing=(
            "Between the tray, the startup entry and the background task, there "
            "is no state of your computer in which the watch quietly is not "
            "running without your having chosen that."
        ),
        then=("noaa-radio-voice",),
    ),
    Tutorial(
        slug="noaa-radio-voice",
        title="NOAA Weather Radio, out loud",
        track="watch",
        minutes=3,
        surfaces=("Quill Weather",),
        summary=(
            "Play the National Weather Service's own broadcast voice for your "
            "area, and know what it is and is not a substitute for."
        ),
        steps=(
            Step(
                title="Listen to your local transmitter",
                body=(
                    "One command plays the transmitter covering your saved place: "
                    "your county's first, or the nearest one whose coverage includes "
                    "you. If you have not set a place yet it tells you that instead "
                    "of failing silently."
                ),
                command="weather.noaa_listen",
                hear=(
                    "The transmitter named -- call sign, frequency and place -- then the broadcast."
                ),
            ),
            Step(
                title="Treat it as an ordinary station",
                body=(
                    "Once it is playing it behaves like any other station in the "
                    "family: favourite it, record it, schedule it. It is the same "
                    "player underneath."
                ),
                hear="Whatever the transport key you press announces.",
            ),
            Step(
                title="Know it works offline",
                body=(
                    "The complete directory -- 1,035 transmitters across every "
                    "state and territory -- ships inside the app, so the local "
                    "lookup and the browsable state-by-state tree work with no "
                    "internet at all."
                ),
                hear="Nothing: this is what you will not notice going wrong.",
            ),
            Step(
                title="Refresh the directory when you want to",
                body=(
                    "Update NOAA Weather Radio Directory pulls the newest list on "
                    "demand, off the UI thread, and announces the result. A failure "
                    "leaves your existing data untouched, and the bundled copy is "
                    "always the floor."
                ),
                command="weather.noaa_update",
                hear="How many transmitters it found.",
            ),
            Step(
                title="Know what it is not",
                body=(
                    "The audio stream is a companion to the text weather, not a "
                    "replacement for a dedicated NOAA Weather Radio receiver with "
                    "alert tones. An internet re-stream depends on the internet, "
                    "which is exactly what a storm takes away."
                ),
                hear="Nothing: this is the sentence that matters on the worst day.",
            ),
        ),
        closing=(
            "The broadcast voice for company, the alert watch for warnings, and a "
            "real receiver for the day the power goes."
        ),
    ),
)
