"""The three lessons that did not belong in any other track's argument.

Community Picks is a curated list rather than a directory, so it sits apart
from the finding track. Spotify is experimental and needs setting up, which no
other source does. Quillins are extensions -- the one place where somebody
else's code contributes to the app -- and they deserve their own honest page.
"""

from __future__ import annotations

from quill.core.tutorials.model import Step, Tutorial

TUTORIALS: tuple[Tutorial, ...] = (
    Tutorial(
        slug="community-picks",
        title="Community Picks, and suggesting one",
        track="beyond",
        minutes=5,
        surfaces=("Community Picks", "ACB Media Podcasts"),
        summary=(
            "Add stations and podcasts from a hand-picked list that is kept up "
            "to date for you, and suggest something for the list yourself by "
            "email. No account and no website needed."
        ),
        steps=(
            Step(
                title="Open the picks",
                body=(
                    "Community Picks is a hand-picked list of stations, podcasts "
                    "and places. Arrow through the Available list, and press Tab "
                    "to Description to hear what one is. Press Add for the one "
                    "you are on, or Add All for the whole list. Anything you "
                    "already have is marked, so nothing is added twice."
                ),
                command="radio.community_picks",
                hear=(
                    "Reading the Community Picks list, then Community Picks and its Available list."
                ),
            ),
            Step(
                title="Know why it works offline",
                body=(
                    "A copy of the list comes with Quill Radio, so it works the "
                    "very first time, with no internet, and even if the website "
                    "is down. When Quill Radio can fetch a newer list, it uses "
                    "that. If it cannot, it uses the copy it has, so the window "
                    "is never empty."
                ),
                hear=(
                    "The heading, adding Showing the list that came with the app when it "
                    "is using its own copy."
                ),
                note=(
                    "The list is signed, and Quill Radio checks the signature "
                    "before using it. That way only Community Access can change "
                    "what it offers you."
                ),
            ),
            Step(
                title="Understand what retiring a pick does",
                body=(
                    "When a pick is retired, it disappears from this window, and "
                    "nothing you already added is touched. Your favorite stays "
                    "and your subscription stays. This list can only ever offer, "
                    "never take away."
                ),
                hear="Nothing. This is just a promise worth knowing.",
            ),
            Step(
                title="Add ACB's whole podcast lineup the same way",
                body=(
                    "ACB Media Podcasts works the same way. It shows everything "
                    "ACB publishes, with the ones you already have marked, so "
                    "you can add the rest without any doubles."
                ),
                command="radio.acb_podcasts",
                hear=(
                    "Reading ACB's podcast directory, then ACB Media Podcasts and its "
                    "Available list."
                ),
            ),
            Step(
                title="Suggest something for the list",
                body=(
                    "Suggest a Station or Podcast takes your suggestion and opens "
                    "your own email program with a message to "
                    "support@community-access.org, ready to go. Press Send there, "
                    "and a real person at Community Access reads it. No login, no "
                    "account and no website. If it is already on the list, you "
                    "are told before anything is written."
                ),
                command="radio.suggest_pick",
                hear="Your mail program has opened with your suggestion written. Press Send there.",
            ),
        ),
        closing=(
            "The list is updated whenever a suggestion is approved, so a station "
            "added on a Tuesday reaches everyone that same Tuesday. Thank you for "
            "helping it grow."
        ),
    ),
    Tutorial(
        slug="spotify-experimental",
        title="Spotify, honestly",
        track="beyond",
        minutes=9,
        surfaces=("Connect to Spotify", "Browse Spotify"),
        summary=(
            "Set up Spotify search and browsing with your own Client ID. Before "
            "you spend ten minutes on it, find out exactly what a free account "
            "can and cannot do here."
        ),
        steps=(
            Step(
                title="Read what a free account gets first",
                body=(
                    "With a free account, you can search Spotify from inside "
                    "Quill Radio and browse your saved shows, episodes, songs and "
                    "playlists. What you cannot do is play the sound inside Quill "
                    "Radio. Spotify does not allow other apps to play free "
                    "account audio, and says so itself."
                ),
                hear="Nothing yet. This step helps you decide whether the rest is worth it.",
                note=(
                    "This is only about where the sound plays, not whether you "
                    "can listen. On a free account, a good plan is to let Quill "
                    "Radio do the searching, which is the fiddly part with a "
                    "screen reader, and play what you find in Spotify's own app."
                ),
            ),
            Step(
                title="Create your own app identity",
                body=(
                    "Quill Radio does not come with a Spotify sign-in of its own, "
                    "so you make your own, and your details never pass through "
                    "anyone else. Go to Spotify's developer dashboard, sign in "
                    "with your normal Spotify account, and choose Create app. It "
                    "is free, and a free account is fine."
                ),
                hear="Nothing from Quill Radio. This step happens in your web browser.",
            ),
            Step(
                title="Fill in the app's details exactly",
                body=(
                    "The name and description are just for you. The Redirect URI "
                    "must be exactly http://127.0.0.1:43217/callback, letter for "
                    "letter, including the number after the colon. That is how "
                    "Spotify sends the finished sign-in back to your computer. "
                    "Check Web API and Web Playback SDK."
                ),
                hear="Nothing. You are still in your web browser.",
            ),
            Step(
                title="Copy the Client ID, and leave the secret alone",
                body=(
                    "Open your new app's settings and copy the Client ID. You "
                    "will also see a Client secret. You do not need it, so do "
                    "not paste it anywhere. Quill Radio only needs the Client ID "
                    "to sign you in."
                ),
                hear="Nothing yet.",
            ),
            Step(
                title="Connect",
                body=(
                    "Connect to Spotify asks for your Client ID and starts the "
                    "sign-in. Your web browser opens Spotify's own page, you "
                    "approve, and Spotify sends you back to Quill Radio on your "
                    "own computer."
                ),
                command="spotify.connect",
                keys=("Ctrl+Alt+P",),
                hear="Which kind of account you signed in with, straight away.",
                note=(
                    "Your sign-in is kept safely in Windows' own password store, "
                    "never in an ordinary file, together with your Client ID. "
                    "Disconnecting clears them all together."
                ),
            ),
            Step(
                title="Search and play",
                body=(
                    "Browse Spotify is a search box with a list of results. "
                    "Type, arrow, press Enter. With Premium, a Spotify item plays "
                    "right in Quill Radio, and all the keys you know still work: "
                    "play and stop, volume, the status bar, the tray, and any "
                    "global hotkeys you set up."
                ),
                command="spotify.browse",
                keys=("Ctrl+Alt+O",),
                hear="The results, then playback if your account is Premium.",
            ),
            Step(
                title="Know the two hard limits",
                body=(
                    "Spotify music can never be recorded or downloaded, on any "
                    "account, because it is copy-protected. And like everything "
                    "that uses the internet, Spotify is off in Safe Mode."
                ),
                hear="If you try, Quill Radio tells you no, and why.",
            ),
            Step(
                title="Know where it lives if you do not use it",
                body=(
                    "Connect to Spotify and Browse Spotify sit together near the "
                    "end of the Station menu, and are left out in Safe Mode. "
                    "There is no switch to hide them. If you never set Spotify "
                    "up, they are just two items to arrow past."
                ),
                keys=("Alt+S",),
                hear="Connect to Spotify, then Browse Spotify, on the Station menu.",
            ),
        ),
        closing=(
            "Ten minutes of setup, just once, gets you search and browsing on any "
            "account, and playback with Premium. Quill Radio tells you which kind "
            "of account you have, so you never have to guess."
        ),
    ),
    Tutorial(
        slug="quillins-in-radio",
        title="Quillins: extensions in a radio",
        track="yours",
        minutes=4,
        surfaces=("Quill Radio", "Browse Stations"),
        summary=(
            "Find out what a Quillin is, where Quillins show up in Quill Radio, "
            "and what one can add to Browse Stations."
        ),
        steps=(
            Step(
                title="Know that there is no menu to find",
                body=(
                    "Quillins are small, safe add-ons for Quill apps. Quill Radio "
                    "uses them, but in this version it has no Quillins menu. The "
                    "Quillins that come with Quill Radio still work, so what they "
                    "add shows up where you already look: in Browse Stations and "
                    "in search."
                ),
                hear=(
                    "Nothing. The menu bar goes from QuillVille straight to Help, and that "
                    "is how it should be."
                ),
                note=(
                    "Each Quillin says which apps it is for, so only ones made "
                    "for Quill Radio show up here."
                ),
            ),
            Step(
                title="See what one can contribute",
                body=(
                    "A Quillin can add a whole source of stations, not just "
                    "search results. When one is installed and turned on, a "
                    "Quillin Sources branch appears in Browse Stations, with a "
                    "folder for each source and its categories and stations. You "
                    "can play them and keep them as favorites like any others."
                ),
                keys=("Ctrl+B",),
                hear="Quillin Sources, and the added source beneath it.",
                check="window:Browse Stations",
            ),
            Step(
                title="Notice when there is nothing to notice",
                body=(
                    "If no Quillin is adding a source, the branch is simply not "
                    "there, rather than there and empty. So you never have to "
                    "wonder why a folder has nothing in it."
                ),
                hear="Nothing. This is the branch you will not find.",
            ),
            Step(
                title="Search finds them too",
                body=(
                    "Search All Sources searches Quillin sources along with "
                    "everything else. The Radio Community Directory sample that "
                    "comes with Quill Radio shows everything a Quillin can do, "
                    "including a station whose address is only looked up when "
                    "you play it."
                ),
                hear="Results from the added source, mixed in with the rest.",
            ),
            Step(
                title="Know when they are off",
                body=(
                    "Quillins are off in Safe Mode. Quillins from other people "
                    "are also turned off in this version, so only the ones that "
                    "come with Quill Radio run. If the Quillin Sources branch is "
                    "missing, that is why."
                ),
                hear="A missing branch, rather than an error.",
            ),
        ),
        closing=(
            "Quillins in Quill Radio are kept small on purpose: a source, a "
            "search, a list of stations. None of them can touch your files."
        ),
    ),
)
