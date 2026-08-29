"""Quill Weather, track 3: making it yours.

Three lessons about the parts you meet after the first week: several places
rather than one, the settings that change how the weather reads, and living
beside the rest of the family.
"""

from __future__ import annotations

from quill.core.tutorials.model import Step, Tutorial

TUTORIALS: tuple[Tutorial, ...] = (
    Tutorial(
        slug="more-than-one-place",
        title="More than one place",
        track="yours",
        minutes=4,
        surfaces=("Weather Center", "Quill Weather"),
        summary=(
            "Add the places you care about, switch between them, and know which "
            "of them the watch covers and which one Quick Weather answers about."
        ),
        steps=(
            Step(
                title="Add a second place",
                body=(
                    "Home is rarely the only place that matters -- work, a parent's "
                    "town, the city a flight lands in tomorrow. Add each one the "
                    "same way, and name each one the way you would say it."
                ),
                command="weather.add_location",
                hear="The place added, under your name for it.",
                check="location-added",
            ),
            Step(
                title="Switch between them",
                body=(
                    "The Location chooser at the top of the Weather Center moves "
                    "between your saved places, and everything below it -- alerts, "
                    "conditions, forecast, outlook -- follows."
                ),
                command="weather.now",
                hear="The place you chose, then its own weather.",
            ),
            Step(
                title="Know which one Quick Weather answers about",
                body=(
                    "Quick Weather always answers for your primary place, which is "
                    "the first one you added. That is what makes it a one-key "
                    "answer: it never has to ask which place you meant."
                ),
                command="weather.quick",
                hear="The primary place, named at the start of the line.",
            ),
            Step(
                title="Know which ones the watch covers",
                body=(
                    "All of them, with no setup. Starting the watch says so as one "
                    "sentence across the places -- 3 places: Tucson, Boston, and "
                    "Reno. All clear right now -- and every alert names its own "
                    "place when it speaks."
                ),
                hear="The combined summary, naming each place.",
            ),
            Step(
                title="Remove one you no longer need",
                body=(
                    "Select it in the Location chooser and press Remove Location "
                    "(Alt+M), or the Delete key in the list. It goes immediately "
                    "and without a confirmation, which is worth knowing before you "
                    "press it; the watch simply stops covering that place."
                ),
                keys=("Delete",),
                hear="The place removed, by name.",
            ),
        ),
        closing=(
            "Places are cheap: the watch covers all of them at once, and only "
            "Quick Weather needs to know which one is first."
        ),
        then=("how-the-weather-reads",),
    ),
    Tutorial(
        slug="how-the-weather-reads",
        title="Decide how the weather reads",
        track="yours",
        minutes=5,
        surfaces=("Weather Settings",),
        summary=(
            "Units, how much forecast, and which details are in the paragraph -- "
            "the settings that decide how long the app takes to tell you "
            "something."
        ),
        steps=(
            Step(
                title="Open Settings and start with units",
                body=(
                    "Temperature in Fahrenheit or Celsius; wind in miles per hour, "
                    "kilometres per hour, knots or metres per second. Set these "
                    "first, because every other number in the app is read in them."
                ),
                command="weather.settings",
                hear="Each unit read back.",
            ),
            Step(
                title="Decide how much forecast you want",
                body=(
                    "Forecast periods to show, extended daily outlook in days, and "
                    "hourly forecast in hours. Each can be set to zero, which turns "
                    "that list off entirely rather than leaving an empty control to "
                    "arrow past."
                ),
                hear="Each length read back.",
            ),
            Step(
                title="Choose what is in the conditions paragraph",
                body=(
                    "A checkbox each for feels-like, humidity, dew point, wind and "
                    "gusts, cloud cover, pressure, visibility, chance of "
                    "precipitation, sunrise and sunset, the moon, the ultraviolet "
                    "index, air quality and the current local time there. "
                    "Temperature and sky always show."
                ),
                hear="Each detail as you tick or untick it.",
                note=(
                    "This is a speech setting wearing a display setting's clothes: "
                    "every box you leave ticked is a clause you hear on every "
                    "reading, for the rest of your life with the app."
                ),
            ),
            Step(
                title="Keep the moon, or drop it",
                body=(
                    "Phase, how full it is, moonrise and moonset are computed on "
                    "your own machine with no extra lookup, so keeping them costs "
                    "no time and no network -- only the seconds it takes to speak "
                    "them."
                ),
                hear="The moon's phase and times, if you kept them.",
            ),
            Step(
                title="Turn off the second clock if you never travel",
                body=(
                    "The local-time line is there because a forecast for somewhere "
                    "two zones away is easy to misread. If all your places share "
                    "your clock, switching it off makes every reading shorter."
                ),
                hear="One fewer sentence at the top of every reading.",
            ),
        ),
        closing=(
            "Nothing here changes what the app can tell you. It changes how long "
            "it takes to tell you, which is the setting that matters most when "
            "you ask twenty times a day."
        ),
        then=("weather-and-the-family",),
    ),
    Tutorial(
        slug="weather-and-the-family",
        title="Weather beside the other apps",
        track="yours",
        minutes=4,
        surfaces=("Quill Weather",),
        summary=(
            "Reaching QUILL and Quill Radio, turning off whole areas you never "
            "use, keeping the app current, and where its help lives."
        ),
        steps=(
            Step(
                title="Open the family",
                body=(
                    "The QuillVille menu opens the other apps -- QUILL, Quill "
                    "Radio, and the rest -- and each has its own show/hide chord so "
                    "they never fight. Quill Weather never launches something you "
                    "did not ask for."
                ),
                keys=("Alt+Q",),
                hear="The other apps, listed by name.",
            ),
            Step(
                title="Turn off an area you never use",
                body=(
                    "Customize Features leaves out a whole area and every command "
                    "under it -- the NOAA radio rows, for instance, if you never "
                    "listen. Nothing is deleted; tick it again and it comes back."
                ),
                keys=("Ctrl+Alt+F",),
                hear="Each area with a short description of what it covers.",
            ),
            Step(
                title="Find the help that is already here",
                body=(
                    "The User Guide and the Release Notes ship beside the app and "
                    "open from the Help menu -- worth knowing because for several "
                    "releases they were installed and unreachable, which is the "
                    "same as not shipping them."
                ),
                keys=("Ctrl+Alt+G", "Ctrl+Alt+R"),
                hear="The document opening in your browser.",
            ),
            Step(
                title="Press F1 wherever you are standing",
                body=(
                    "F1 answers for the control under focus: what this window is "
                    "for, then what this control does and how to drive it, in a "
                    "field you can arrow through and copy. Escape puts you back "
                    "exactly where you were."
                ),
                keys=("F1",),
                hear="The window's purpose, then the control's own help.",
            ),
            Step(
                title="Stay current",
                body=(
                    "Check for Updates compares your version with the newest "
                    "release and downloads the edition you are running, with spoken "
                    "progress. Being current matters more here than in most apps: "
                    "this one is watching for warnings."
                ),
                keys=("Ctrl+Alt+U",),
                hear="Either what is available, or that you are up to date.",
            ),
        ),
        closing=(
            "Quill Weather is deliberately small. Everything it does not do, "
            "another app in the family does -- and it will open that app for you."
        ),
    ),
)
