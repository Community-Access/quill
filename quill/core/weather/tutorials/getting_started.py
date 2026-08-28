"""Quill Weather, track 1: the first ten minutes.

Three lessons. Add a place, read everything the app knows about it, and learn
the one key that answers without opening anything. Somebody who does only
these three has a working weather app.
"""

from __future__ import annotations

from quill.core.tutorials.model import Step, Tutorial

TUTORIALS: tuple[Tutorial, ...] = (
    Tutorial(
        slug="first-location",
        title="Add your first place",
        track="start",
        minutes=4,
        surfaces=("Quill Weather",),
        summary=(
            "Search for somewhere by ZIP code, town, county or address, pick the "
            "right one out of the results, and give it a name you would actually "
            "say."
        ),
        steps=(
            Step(
                title="Open Add Location",
                body=(
                    "On a fresh installation there is no saved place yet, so this "
                    "is the first thing to do. The main window is deliberately "
                    "small -- a status line and three buttons -- and everything "
                    "else lives on the menu bar."
                ),
                command="weather.add_location",
                hear="Entered the Add Location window, with focus in the search box.",
            ),
            Step(
                title="Search the way you think of the place",
                body=(
                    "A ZIP code, a town and state (Tucson, AZ), a county name, an "
                    "address, or exact coordinates like 32.2, -110.9 all work. Use "
                    "whichever you have; there is no right form to learn."
                ),
                keys=("Enter",),
                hear="A results list, and how many places matched.",
            ),
            Step(
                title="Pick the right one out of the results",
                body=(
                    "A search can match more than one place -- there are "
                    "Springfields in Illinois, Missouri and several other states -- "
                    "so the app never guesses. Arrow to the one you meant, and "
                    "choose Add Selected."
                ),
                keys=("Down arrow", "Alt+A"),
                hear="Each result read as a whole place, then the one you added.",
                check="location-added",
            ),
            Step(
                title="Give it a name you would say out loud",
                body=(
                    "Type a friendly name -- Home, Mom's, Work -- into the name "
                    "field before you add it. The official name of a place is often "
                    "a county and a state you would never use in conversation, and "
                    "this is the name every announcement will use."
                ),
                hear="The place added under your own name for it.",
            ),
            Step(
                title="Know what the first place means",
                body=(
                    "The first place you add becomes your primary location: the one "
                    "Quick Weather answers about, and the one the local NOAA Weather "
                    "Radio lookup uses. Add as many more as you like afterwards."
                ),
                hear="Nothing: this is the fact that explains Quick Weather's answer.",
            ),
            Step(
                title="Read the safety note once",
                body=(
                    "Quill Weather is an additional accessible weather tool. "
                    "Delivery can be delayed by network, device or provider "
                    "problems, so keep a NOAA Weather Radio, Wireless Emergency "
                    "Alerts and local emergency instructions as your primary "
                    "channels. That is stated here rather than buried."
                ),
                hear="Nothing: this is the paragraph worth reading twice.",
            ),
        ),
        closing=(
            "One place is enough to start. Everything comes from free, "
            "no-account sources -- the National Weather Service for conditions, "
            "the forecast and alerts, Open-Meteo for the extended outlook and air "
            "quality, OpenStreetMap for the search."
        ),
        then=("read-the-weather", "one-line-answer"),
    ),
    Tutorial(
        slug="read-the-weather",
        title="Read everything it knows",
        track="start",
        minutes=6,
        surfaces=("Weather Center", "Quill Weather"),
        summary=(
            "The Weather Center, top to bottom, in the order it is written to be "
            "read: what is dangerous, what it is like now, what is coming, and "
            "where the numbers came from."
        ),
        steps=(
            Step(
                title="Open the Weather Center",
                body=(
                    "It reads top to bottom in priority order, which is the whole "
                    "design: the most urgent thing is the first thing, not the "
                    "prettiest thing."
                ),
                command="weather.now",
                hear="Entered Weather Now, with the alerts list first if there are any.",
            ),
            Step(
                title="Start with the alerts, if there are any",
                body=(
                    "Watches, warnings and advisories, most severe first. Arrow "
                    "through them and the full official text -- including the "
                    "instructions, which is the part that tells you what to do -- "
                    "appears in the read-only box just below, where you can review "
                    "and copy it."
                ),
                keys=("Down arrow", "Tab"),
                hear="Each alert's headline, then its full text in the box below.",
                note=(
                    "When there are no alerts that box is hidden rather than empty, "
                    "so you never stop on a field with nothing in it."
                ),
            ),
            Step(
                title="Read the current conditions as a paragraph",
                body=(
                    "Temperature, feels-like, sky, humidity, dew point, wind and "
                    "gusts, cloud, pressure, visibility, chance of precipitation, "
                    "sunrise and sunset, ultraviolet index and air quality -- "
                    "written out as sentences for speech rather than as a table of "
                    "abbreviations."
                ),
                keys=("Tab",),
                hear="A warm paragraph, with the observation time in the place's own zone.",
            ),
            Step(
                title="Notice the two clocks",
                body=(
                    "The report leads with the local day and time where you "
                    "searched, the time where you are, and when the reading was "
                    "taken -- checked just now, or the exact minute in your own "
                    "clock for an older one. When both are in the same zone it says "
                    "so once instead of repeating itself."
                ),
                hear="Right now it is Thursday, 9:51 AM in Tucson, and 6:51 AM where you are.",
            ),
            Step(
                title="Walk the forecast",
                body=(
                    "The National Weather Service period forecast -- This "
                    "Afternoon, Tonight, and on. Arrow the list and each period's "
                    "full text appears below, led by its day and temperature so it "
                    "stands alone when read out of order."
                ),
                keys=("Down arrow",),
                hear="Each period's name, then its detail in the box below.",
            ),
            Step(
                title="Look further out, and hour by hour",
                body=(
                    "The daily outlook reaches about ten days (up to sixteen), each "
                    "day one friendly line. The hourly list gives temperature, sky "
                    "and chance of precipitation for the coming hours. Both are "
                    "lengths you set in Settings, and either can be switched off."
                ),
                keys=("Tab", "Down arrow"),
                hear=(
                    "Monday, July 20: Clear. High 98, low 75 degrees. "
                    "Sunrise 5:42 AM, sunset 7:38 PM."
                ),
            ),
            Step(
                title="Check where the numbers came from",
                body=(
                    "The status line names the National Weather Service office and "
                    "the observation station. Two stations a few miles apart can "
                    "disagree about the wind, and knowing which one you are reading "
                    "is the difference between a puzzle and a fact."
                ),
                keys=("Tab",),
                hear="The office and the station, by name.",
            ),
            Step(
                title="Refresh, and leave",
                body=(
                    "Refresh pulls the latest at any time. Close leaves anything you "
                    "are playing untouched -- the radio keeps going, which is the "
                    "point of a weather window that lives beside a radio."
                ),
                keys=("Alt+R", "Escape"),
                hear="The reading refreshed, then the window closing.",
            ),
        ),
        closing=(
            "That is everything the app knows about a place. The next lesson is "
            "the same answer in one line, without opening anything."
        ),
        then=("one-line-answer",),
    ),
    Tutorial(
        slug="one-line-answer",
        title="The one-line answer",
        track="start",
        minutes=3,
        surfaces=("Quill Weather",),
        summary=(
            "Quick Weather speaks a summary of your primary place without opening "
            "a window -- and you decide what goes in it."
        ),
        steps=(
            Step(
                title="Ask, and listen",
                body=(
                    "One key, one sentence, no window. This is the key to keep in "
                    "your fingers: it is the answer to the question people actually "
                    "ask twenty times a day."
                ),
                command="weather.quick",
                hear=(
                    "Here is the weather for Tucson, Arizona. It is 96 degrees and "
                    "mostly clear. It feels like 101. The wind is from the "
                    "west-northwest at 5 miles per hour. There is one active alert."
                ),
            ),
            Step(
                title="Hear the alert count in it",
                body=(
                    "When something is active, the line ends with how many alerts "
                    "there are and names the most urgent. That is deliberate: the "
                    "quick answer should never be the one that leaves out the "
                    "warning."
                ),
                hear="There is one active alert. The most urgent is an Excessive Heat Warning.",
            ),
            Step(
                title="Decide what the line says",
                body=(
                    "Settings has a Quick Weather section: feels-like, wind, "
                    "humidity, the active-alert count and the age of the data can "
                    "each be turned on or off. A one-line answer that takes eight "
                    "seconds to speak is not a quick answer."
                ),
                command="weather.settings",
                hear="Each toggle read back as you set it.",
            ),
            Step(
                title="Jump straight to the alerts instead",
                body=(
                    "Active Alerts opens the Weather Center with focus already on "
                    "the alerts list, which is the fewest keystrokes between you and "
                    "the official text of a warning."
                ),
                command="weather.alerts",
                hear="Entered Weather Now, on the alerts list.",
            ),
        ),
        closing=(
            "Quick Weather for the everyday question, Active Alerts for the "
            "serious one, the Weather Center when you want everything."
        ),
        then=("start-watching",),
    ),
)
