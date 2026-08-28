"""The three lessons that did not belong in any other track's argument.

Community Picks is a curated list rather than a directory, so it sits apart
from the finding track. Spotify is experimental and needs setting up, which no
other source does. Quillins are extensions -- the one place where somebody
else's code contributes to the app -- and they deserve their own honest page.
"""

from __future__ import annotations

from quill.core.radio.tutorials.model import Step, Tutorial

TUTORIALS: tuple[Tutorial, ...] = (
    Tutorial(
        slug="community-picks",
        title="Community Picks, and suggesting one",
        track="beyond",
        minutes=5,
        surfaces=("Community Picks", "ACB Media Podcasts"),
        summary=(
            "Add stations and podcasts from a curated list that is kept up to "
            "date on the web, and put something on that list yourself without a "
            "GitHub account or a browser."
        ),
        steps=(
            Step(
                title="Open the picks",
                body=(
                    "Community Picks is a hand-curated list of stations, podcasts "
                    "and places rather than a directory. Arrow the list to hear what "
                    "each one is, tick the ones you want, and they are added in one "
                    "go."
                ),
                command="radio.community_picks",
                hear="Entered Community Picks, then each entry with its description.",
            ),
            Step(
                title="Know why it works offline",
                body=(
                    "A copy ships with the app, so the picker works on first run, "
                    "with no connection, and if the site is ever down. A fetched copy "
                    "supersedes it and a failed fetch falls back to it -- never to an "
                    "empty window."
                ),
                hear="The summary line, saying how old this copy is.",
                note=(
                    "The list is signed, and the signature is checked against the "
                    "same publisher key that signs Quillins and releases. This file "
                    "causes the app to add stations, so whoever could replace it "
                    "could point you at content you did not choose."
                ),
            ),
            Step(
                title="Understand what retiring a pick does",
                body=(
                    "A pick that is retired vanishes from the picker and nothing you "
                    "already added is touched. Your favorite stays, your subscription "
                    "stays. A catalogue that could reach into your library would be "
                    "one worth refusing to fetch at all."
                ),
                hear="Nothing: this is the promise behind the window.",
            ),
            Step(
                title="Add ACB's whole podcast lineup the same way",
                body=(
                    "ACB Media Podcasts uses the same picker: everything ACB "
                    "publishes, with what you already have marked, so you add the "
                    "rest without duplicating anything."
                ),
                command="radio.acb_podcasts",
                hear="Entered ACB Media Podcasts, then the lineup.",
            ),
            Step(
                title="Suggest something for the list",
                body=(
                    "Suggest a Station or Podcast takes your suggestion here and "
                    "makes it a real issue, with the issue number read back to you -- "
                    "no login, no account, no web form designed by somebody else. "
                    "Duplicates are caught before anything is sent."
                ),
                command="radio.suggest_pick",
                hear="The issue number, read back.",
            ),
        ),
        closing=(
            "The list is rebuilt on the site whenever a suggestion is approved, so "
            "a station added on a Tuesday reaches everybody on Tuesday rather than "
            "at the next installer."
        ),
    ),
    Tutorial(
        slug="spotify-experimental",
        title="Spotify, honestly",
        track="beyond",
        minutes=9,
        surfaces=("Connect to Spotify", "Browse Spotify"),
        summary=(
            "Set up Spotify search and browsing with your own Client ID, and "
            "understand precisely what a free account can and cannot do here "
            "before you spend the ten minutes."
        ),
        steps=(
            Step(
                title="Read what a free account gets first",
                body=(
                    "On a free account you can search Spotify from inside Quill "
                    "Radio and browse your saved shows, episodes, tracks and "
                    "playlists. What you cannot do is have audio start inside Quill "
                    "Radio -- Spotify does not license other applications to stream "
                    "free-tier audio, and says so in its own developer "
                    "documentation."
                ),
                hear="Nothing: this step is the one that decides whether the rest is worth doing.",
                note=(
                    "This is about where the audio plays, not whether you may listen. "
                    "The sensible use on a free account is to let Quill Radio do the "
                    "finding -- the part that is genuinely awkward with a screen "
                    "reader -- and play what you find in Spotify's own app."
                ),
            ),
            Step(
                title="Create your own app identity",
                body=(
                    "Quill Radio ships no Spotify identity, so you supply your own "
                    "and nothing of yours passes through anybody else's. Go to "
                    "Spotify's developer dashboard, sign in with your ordinary "
                    "account, and choose Create app. There is no charge and a free "
                    "account works."
                ),
                hear="Nothing from Quill Radio: this step happens in your browser.",
            ),
            Step(
                title="Fill in the app's details exactly",
                body=(
                    "Name and description are only for you. The Redirect URI must be "
                    "http://127.0.0.1:43217/callback, character for character, "
                    "including the port -- that address is how Spotify hands the "
                    "finished sign-in back to your own computer. Tick Web API and Web "
                    "Playback SDK."
                ),
                hear="Nothing: this is still the browser.",
            ),
            Step(
                title="Copy the Client ID, and leave the secret alone",
                body=(
                    "Open your new app's settings and copy the Client ID. You will "
                    "also see a Client secret: you do not need it and you should not "
                    "paste it anywhere. Quill Radio signs in with the modern PKCE "
                    "flow, which needs only the ID."
                ),
                hear="Nothing yet.",
            ),
            Step(
                title="Connect",
                body=(
                    "Connect to Spotify takes the Client ID and starts the sign-in: "
                    "your browser opens Spotify's own approval page, you approve, and "
                    "Spotify returns to a tiny local address your own machine is "
                    "listening on for exactly that one moment."
                ),
                command="spotify.connect",
                hear="Which kind of account you signed in with, straight away.",
                note=(
                    "Your tokens go into the Windows credential vault -- never a "
                    "plain file and never a log -- with the Client ID beside them, so "
                    "the whole connection lives in one place and clears together."
                ),
            ),
            Step(
                title="Search and play",
                body=(
                    "Browse Spotify is a search box with a results list. Type, arrow, "
                    "press Enter. A Spotify item plays through the hidden Web Playback "
                    "engine, and everything you already know keeps working -- "
                    "play/stop, volume, the status bar, the tray, and any global "
                    "hotkeys you assigned."
                ),
                command="spotify.browse",
                hear="The results, then playback if your account is Premium.",
            ),
            Step(
                title="Know the two hard limits",
                body=(
                    "A Spotify selection can never be recorded or downloaded on any "
                    "account, because the audio is copy-protected. And Spotify, like "
                    "every network feature, is off in Safe Mode."
                ),
                hear="The refusal, with the reason, if you try.",
            ),
            Step(
                title="Hide it if you are not going to use it",
                body=(
                    "Turn Spotify off in Customize Features and the two menu items "
                    "disappear. An experimental capability you have decided against is "
                    "just two more rows to arrow past."
                ),
                keys=("Alt+V",),
                hear="The feature list, with Spotify unticked.",
            ),
        ),
        closing=(
            "Ten minutes of setup, once, for search and browsing that work on any "
            "account -- and playback only if you have Premium. Quill Radio tells "
            "you which you signed in with rather than leaving you to guess."
        ),
    ),
    Tutorial(
        slug="quillins-in-radio",
        title="Quillins: extensions in a radio",
        track="yours",
        minutes=4,
        surfaces=("Quill Radio", "Browse Stations"),
        summary=(
            "What a Quillin is, where they appear in Quill Radio, and what one can "
            "contribute to the browse tree."
        ),
        steps=(
            Step(
                title="Find the menu",
                body=(
                    "Quill Radio runs Quillins -- QUILL's small, sandboxed, "
                    "permission-gated add-ons -- from its own Quillins menu, opened "
                    "with Alt+N. A Quillin says in its manifest which apps it is for, "
                    "so only add-ons written for Quill Radio appear here."
                ),
                keys=("Alt+N",),
                hear="The Quillins menu, listing the ones installed for this app.",
                note=(
                    "It asked for Alt+Q until August 2026, which QuillVille already "
                    "had, so it never opened. There is now a check that stops any "
                    "menu in the family shipping without an Alt key or sharing one "
                    "with its neighbour."
                ),
            ),
            Step(
                title="See what one can contribute",
                body=(
                    "A Quillin can contribute a whole station source, not only search "
                    "results. When one is installed and enabled, a Quillin Sources "
                    "branch appears in Browse Stations -- one folder per contributed "
                    "source, with its categories and its stations, playable and "
                    "favouritable like anything else."
                ),
                command="radio.browse",
                hear="Quillin Sources, and the contributed source beneath it.",
                check="window:Browse Stations",
            ),
            Step(
                title="Notice when there is nothing to notice",
                body=(
                    "With no Quillin contributing a source, that branch is simply "
                    "absent rather than present and empty. An empty branch is a "
                    "question you have to answer; an absent one is not."
                ),
                hear="Nothing: this is the branch you will not find.",
            ),
            Step(
                title="Search finds them too",
                body=(
                    "A contributed source is searched by Search All Sources along "
                    "with everything else, and the bundled Radio Community Directory "
                    "sample shows authors the whole shape -- including a station whose "
                    "address is only worked out at the moment you play it."
                ),
                hear="Results from the contributed source, mixed in with the rest.",
            ),
            Step(
                title="Know when they are off",
                body=(
                    "Quillins are off in Safe Mode, and third-party Quillins remain "
                    "disabled in this release -- the bundled ones are the foundation. "
                    "If the menu is empty, that is why."
                ),
                hear="An empty or absent menu, rather than a failure.",
            ),
        ),
        closing=(
            "Extensions in a radio app are a small idea deliberately: a source, a "
            "search, a directory. Nothing here can reach your files."
        ),
    ),
)
