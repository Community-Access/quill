"""QUILL Cast, track 3: listening well -- six of its seven lessons.

The hour itself. The keys that work while something plays; speed, silences
and the sleep timer; chapters and skipping what you did not come for; shaping
the sound; keeping a moment; and reading what the publisher sent.

The track's seventh lesson, listening statistics, lives in
:mod:`.making_it_yours` beside the other lessons about your own data; the
catalogue orders by track, so it still comes last in this one.
"""

from __future__ import annotations

from quill.core.tutorials.model import Step, Tutorial

TUTORIALS: tuple[Tutorial, ...] = (
    Tutorial(
        slug="keys",
        title="Keys",
        track="listening",
        minutes=7,
        surfaces=("QUILL Cast",),
        summary=(
            "Learn the menus by their letters and the keys that work while "
            "something plays. Then find one sheet of every key, move a key that "
            "does not suit you, and reach Cast from any program."
        ),
        steps=(
            Step(
                title="Learn the menus by their letters",
                body=(
                    "The menus are Podcasts, Edit, View, Episode, Downloads, Window and "
                    "Help. Every menu row tells you its key, so opening a menu is a "
                    "gentle way to learn keys as you go. One to watch for: Edit is "
                    "Alt+I in Cast, because Episode has Alt+E."
                ),
                keys=("Alt+P", "Alt+I", "Alt+V", "Alt+E", "Alt+D", "Alt+W", "Alt+H"),
                hear="Each menu, then its first row with its key.",
            ),
            Step(
                title="Play, stop, skip and move by chapter",
                body=(
                    "These work from anywhere in Cast: play or pause, stop, skip "
                    "forward and back, and next and previous chapter. Each one tells "
                    "you what it did, so you never have to guess."
                ),
                keys=(
                    "Ctrl+P",
                    "Ctrl+.",
                    "Ctrl+Right",
                    "Ctrl+Left",
                    "Ctrl+Alt+Right",
                    "Ctrl+Alt+Left",
                ),
                hear="The new position, or the chapter's name.",
                check="playing",
            ),
            Step(
                title="Go to a time",
                body=(
                    "A friend says the good bit starts an hour and two minutes in. Go "
                    "to Position takes 1:02:00, or 62:00, or a number of seconds, and "
                    "you are there when you press Enter."
                ),
                command="podcasts.go_to_position",
                keys=("Ctrl+Alt+J",),
                hear="The new position.",
            ),
            Step(
                title="Scan past an advert",
                body=(
                    "Hold Shift+Right while an episode plays and it races along at "
                    "four times speed. You can still just about follow the words. Let "
                    "go when you hear the part you want, and Cast drops back to the "
                    "speed you were listening at."
                ),
                keys=("Shift+Right",),
                hear="Scanning forward, 4 times speed; then your own speed when you let go.",
            ),
            Step(
                title="Use the Winamp letters in a list",
                body=(
                    "If your fingers learned on Winamp, its letters work in every list "
                    "in the main window: Z, X, C, V and B for previous, play, pause, "
                    "stop and next, and T for elapsed or remaining time. They never "
                    "fire while you are typing in a text box."
                ),
                keys=("Z", "X", "C", "V", "B"),
                hear="Each one saying what it did.",
                note=(
                    "Would you rather type a letter to jump through a list? Turn off "
                    "Winamp playback keys in Preferences, under Playing."
                ),
            ),
            Step(
                title="See every key on one sheet",
                body=(
                    "The Keyboard Shortcuts Sheet lists every key Cast answers to, "
                    "including any you changed. Try typing download in its filter, "
                    "and you hear only the keys about downloading. Copy All puts the "
                    "list on the clipboard."
                ),
                keys=("Ctrl+Alt+Shift+K",),
                hear="The sheet, then only the keys that match what you type.",
            ),
            Step(
                title="Move a key that does not suit you",
                body=(
                    "Keyboard Shortcuts, on the Help menu, lets you give any command a "
                    "new key, and warns you if it is already taken. Keys are shared "
                    "with QUILL and Quill Radio. Once you change a key, these lessons "
                    "tell you your key, not the one Cast came with."
                ),
                keys=("Ctrl+Alt+Shift+W",),
                hear="The command you chose, then its new key.",
            ),
            Step(
                title="Reach Cast from any program",
                body=(
                    "Ctrl+Alt+Shift+F12 shows or hides Cast from whatever window you "
                    "are in, and the episode keeps playing. Global Hotkeys gives a "
                    "few more commands keys that work everywhere, such as Play/Pause "
                    "and Time Remaining. Media keys work too."
                ),
                keys=("Ctrl+Alt+Shift+F12", "Ctrl+Alt+Shift+H"),
                hear="Cast saying it is hidden in the tray, or shown.",
            ),
        ),
        closing=(
            "Nobody learns these all at once, so be kind to yourself. Use the menus "
            "for a week, and the keys you reach for most will stick on their own."
        ),
        then=("sleep-and-speed",),
    ),
    Tutorial(
        slug="sleep-and-speed",
        title="Sleep and speed",
        track="listening",
        minutes=6,
        surfaces=("QUILL Cast", "Now Playing"),
        summary=(
            "Give each podcast its own speed, shorten the silences, and fall asleep "
            "to a podcast without it playing all night. Your place is still saved "
            "in the morning."
        ),
        steps=(
            Step(
                title="Speed up the podcast that is playing",
                body=(
                    "Each press moves a tenth, anywhere from half speed to five "
                    "times. Cast tells you the new speed and that it belongs to this "
                    "podcast, and remembers it. So the fast talker stays slow and the "
                    "rambling one stays quick, and you never have to touch it again."
                ),
                command="podcasts.speed_up",
                keys=("Ctrl+Shift+Up", "Ctrl+Shift+Down"),
                hear="The new speed, and the podcast it belongs to.",
            ),
            Step(
                title="Put it back to normal",
                body=(
                    "Normal speed puts this podcast back to normal. If you press the "
                    "speed keys with nothing playing, you set the speed for every "
                    "podcast that does not have its own. Cast tells you which one you "
                    "changed."
                ),
                command="podcasts.speed_reset",
                keys=("Ctrl+Shift+0",),
                hear="Normal speed, and whose it is.",
            ),
            Step(
                title="Shorten the silences",
                body=(
                    "Long pauses add up over an hour. Skip Silence shortens them, so "
                    "an episode takes less time without anyone sounding rushed. Like "
                    "speed, it belongs to the podcast that is playing. Press it again "
                    "to turn it off."
                ),
                keys=("Ctrl+Shift+9",),
                hear="Skip Silence on.",
            ),
            Step(
                title="Set a sleep timer",
                body=(
                    "Off to bed? Sleep Timer offers a number of minutes, End of this "
                    "episode, or Custom for your own number. Press Start. A minute "
                    "before it stops, Cast warns you, and then the sound fades gently "
                    "away."
                ),
                keys=("Ctrl+Alt+T",),
                hear="The timer started, and how long it will run.",
            ),
            Step(
                title="Sleep at the end of this episode",
                body=(
                    "This sets the timer straight to the end of the episode. If you "
                    "skip ahead, the timer moves with you. The Sleep timer cell in the "
                    "status bar tells you how long is left at any time."
                ),
                keys=("Ctrl+Alt+Shift+T",),
                hear="Cast saying it will stop at the end of this episode.",
            ),
            Step(
                title="Ask for five more minutes",
                body=(
                    "Not quite asleep? This adds five minutes, even once the sound has "
                    "started to fade. To turn the timer off, open the Sleep Timer "
                    "again and press Cancel Sleep Timer."
                ),
                keys=("Ctrl+Alt+X",),
                hear="Five more minutes, and when it will now stop.",
            ),
            Step(
                title="Stop after this one, tonight only",
                body=(
                    "Stop After This Episode stops at the end of this episode instead "
                    "of moving on, and then turns itself off, so tomorrow the queue "
                    "carries on as usual. Press it again before then to cancel it."
                ),
                command="podcasts.stop_after_episode",
                keys=("Ctrl+Alt+Shift+A",),
                hear="Stopping after this episode.",
            ),
        ),
        closing=(
            "Sleep well. However playback stops, Cast remembers your place, and "
            "tomorrow picks up exactly where tonight left off."
        ),
        then=("chapters-and-skipping",),
    ),
    Tutorial(
        slug="chapters-and-skipping",
        title="Chapters, and skipping what you did not come for",
        track="listening",
        minutes=7,
        surfaces=("QUILL Cast", "Settings for"),
        summary=(
            "Move by chapter, skip a chapter you never want, and skip the same "
            "intro and outro every week. Cast can even work out chapters for an "
            "episode that came without any."
        ),
        steps=(
            Step(
                title="Move by chapter",
                body=(
                    "Many episodes are split into chapters: the news, the interview, "
                    "the listener questions. Next and Previous Chapter hop straight "
                    "between them, and Cast says each chapter's name as you arrive."
                ),
                keys=("Ctrl+Alt+Right", "Ctrl+Alt+Left"),
                hear="The chapter's name as you arrive.",
            ),
            Step(
                title="See the whole list",
                body=(
                    "Chapters, on an episode's menu, lists each chapter's name and "
                    "where it starts. Arrow to one and press Enter to go there. If a "
                    "podcast marks only its highlights, the list calls them Moments "
                    "this podcast marked."
                ),
                keys=("Shift+F10", "Enter"),
                hear="Each chapter, with where it starts.",
            ),
            Step(
                title="Skip a chapter you never want",
                body=(
                    "In the Chapters list, Skip This Chapter marks one you would "
                    "rather miss. When playback reaches it, Cast jumps past. Skip "
                    "Nothing clears every mark. The marks last only until you close "
                    "Cast, so tomorrow starts fresh."
                ),
                keys=("Alt+S", "Alt+N"),
                hear="Skipping chapter, and its name, when playback reaches it.",
            ),
            Step(
                title="Skip the intro and outro every time",
                body=(
                    "Tired of the same long intro every week? In Settings for This "
                    "Podcast, Skip the first jumps over it, and Stop this far before "
                    "the end leaves off the credits. The intro skip only happens when "
                    "an episode starts from the beginning."
                ),
                keys=("Ctrl+Alt+,",),
                hear="Your settings saved for that podcast.",
                check="settings-changed",
            ),
            Step(
                title="Let Cast work out chapters",
                body=(
                    "Most episodes come without chapters, and Cast can find some for "
                    "you. In Preferences, under Chapters, How long to spend looking "
                    "offers not long, a while, or as long as it takes. The longest "
                    "listens to the whole episode on your own computer, without the "
                    "internet."
                ),
                keys=("Ctrl+,",),
                hear="The Chapters section, and its first choice.",
            ),
            Step(
                title="Ask for chapters on one episode now",
                body=(
                    "Analyse Chapters, on a downloaded episode's menu, works them out "
                    "while you wait, then opens Review Chapters. Preview This Mark "
                    "plays a few seconds either side. If one is in the wrong place, "
                    "Nudge Earlier and Nudge Later fix it. Save Chapters keeps them."
                ),
                keys=("Shift+F10", "Alt+P"),
                hear="How Cast is getting on, then the chapters it found.",
            ),
        ),
        closing=(
            "Chapters Cast worked out say so in the list, along with how sure Cast "
            "is, so you always know which ones came from the podcast itself."
        ),
        then=("shape-the-sound",),
    ),
    Tutorial(
        slug="shape-the-sound",
        title="Shape the sound",
        track="listening",
        minutes=5,
        surfaces=("QUILL Cast", "Settings for"),
        summary=(
            "Clear up a muddy recording, even out the quiet and loud parts, boost "
            "one quiet podcast without touching the rest, and choose which ear and "
            "which speakers you hear it in."
        ),
        steps=(
            Step(
                title="Open Sound Enhancements",
                body=(
                    "Play an episode first, then open Sound Enhancements to change "
                    "how it sounds. Like speed, what you choose belongs to the podcast "
                    "that is playing, or to every podcast when nothing is."
                ),
                keys=("Ctrl+E",),
                hear="Sound Enhancements, then the Quick preset.",
            ),
            Step(
                title="Try a preset",
                body=(
                    "Quick preset offers Flat, Bass Boost, Voice Clarity and Podcast. "
                    "Voice Clarity is a good first try for a muddy recording. The "
                    "Bass, Mid and Treble sliders are there for finer control."
                ),
                keys=("Down Arrow",),
                hear="Each preset as you arrow to it.",
            ),
            Step(
                title="Even out loud and quiet",
                body=(
                    "Even Out Volume brings quiet and loud parts closer together. It "
                    "is lovely for a loud guest and a softly spoken host. Press OK and "
                    "playback picks up at the same spot with the new sound."
                ),
                keys=("Tab", "Space", "Enter"),
                hear="The episode carrying on from the same spot.",
            ),
            Step(
                title="Boost one quiet podcast",
                body=(
                    "One podcast always sounds recorded in a cupboard. In its Settings "
                    "for This Podcast, set Volume Boost to Low, Medium or High. Cast "
                    "applies it every time that podcast plays, and leaves everything "
                    "else alone."
                ),
                keys=("Ctrl+Alt+,",),
                hear="Your settings saved for that podcast.",
                check="settings-changed",
            ),
            Step(
                title="Choose which ear",
                body=(
                    "Audio Output Mode moves through stereo, mono, left ear only and "
                    "right ear only. Many people like one ear for the podcast and the "
                    "other for their screen reader."
                ),
                keys=("Ctrl+Shift+M",),
                hear="The new output mode.",
            ),
            Step(
                title="Choose which speakers",
                body=(
                    "Audio Output Device chooses the speakers or headphones Cast plays "
                    "through. If Cast cannot switch itself, it says so and offers the "
                    "Windows sound settings, which remember your choice."
                ),
                keys=("Ctrl+Shift+K",),
                hear="The devices you can play through.",
            ),
        ),
        closing=(
            "Play with these until the sound suits your ears. Sound Enhancements "
            "uses FFmpeg, a tool that comes with Cast. If it is ever missing, the "
            "episode still plays, and Cast tells you why."
        ),
        then=("keep-a-moment",),
    ),
    Tutorial(
        slug="keep-a-moment",
        title="Keep a moment",
        track="listening",
        minutes=6,
        surfaces=("Bookmarks", "QUILL Cast"),
        summary=(
            "Bookmark a moment with one key, add a note to say why, and find your "
            "bookmarks again later. You will also write a longer note and share a "
            "moment with a friend."
        ),
        steps=(
            Step(
                title="Bookmark this moment",
                body=(
                    "A guest recommends a book and you want to remember where. One "
                    "key marks that spot. There is no window and nothing to type, and "
                    "the episode keeps playing."
                ),
                command="app.bookmark_moment",
                keys=("Ctrl+Alt+A",),
                hear="Cast saying the bookmark is saved.",
            ),
            Step(
                title="Bookmark with a note",
                body=(
                    "Sometimes you want to say why, right then. Bookmark with a Note "
                    "opens a small box. Type a few words, such as the book the guest "
                    "recommends, and press Enter. The note is up to you. Enter on an "
                    "empty box still makes the bookmark."
                ),
                keys=("Ctrl+Shift+D",),
                hear="Cast saying the bookmark is saved, with your note.",
            ),
            Step(
                title="See this episode's bookmarks",
                body=(
                    "Bookmarks in This Episode shows only the bookmarks in the episode "
                    "that is playing, or the one you are on. The same list is a button "
                    "away in Now Playing, and About This Episode has a Bookmarks tab."
                ),
                keys=("Ctrl+Shift+J",),
                hear="The bookmarks in this episode, each with where it is.",
            ),
            Step(
                title="See every bookmark",
                body=(
                    "The Bookmarks window lists them all. Go There plays that episode "
                    "from that moment. Edit Note, Share, Delete and Export are beside "
                    "it. If you use Quill Radio, its bookmarks are in the same list."
                ),
                command="app.bookmarks",
                keys=("Ctrl+Alt+Shift+J",),
                hear="Bookmarks, then each one with what it is in and where.",
            ),
            Step(
                title="Write a note at this point",
                body=(
                    "Add Episode Note keeps your words and the time together, for "
                    "when a bookmark is not enough. Episode Notes, on any episode's "
                    "menu, shows that episode's notes, and selecting one takes you to "
                    "that moment."
                ),
                keys=("Ctrl+Alt+N",),
                hear="Cast saying the note is saved.",
            ),
            Step(
                title="Share a moment",
                body=(
                    "Want a friend to hear something? Share This Moment, on the playing "
                    "episode's menu, copies a sentence with the podcast, the episode "
                    "and the time, such as 41 minutes 12 seconds, with a link. It "
                    "makes sense to anyone, even read out over the phone."
                ),
                keys=("Shift+F10",),
                hear="Cast saying the moment is copied.",
            ),
        ),
        closing=(
            "Your bookmarks and notes stay on your computer, go with you in a "
            "backup, and are shared with Quill Radio."
        ),
        then=("what-the-feed-published",),
    ),
    Tutorial(
        slug="what-the-feed-published",
        title="Show notes, and what else the podcast sent",
        track="listening",
        minutes=6,
        surfaces=("About This Episode", "QUILL Cast"),
        summary=(
            "Read the show notes like a small document and follow a link or a "
            "time in them. You will also copy the notes, see who is on an episode, "
            "read a transcript, and ask AI about notes that run long."
        ),
        steps=(
            Step(
                title="Read the show notes",
                body=(
                    "Wondering what an episode is about before you play it? Its notes "
                    "are one Tab away from the list. Read them with your usual reading "
                    "keys."
                ),
                keys=("Tab", "Alt+O"),
                hear="The notes, from the top.",
            ),
            Step(
                title="Move by heading and by link",
                body=(
                    "H and Shift+H move between headings. Tab and Shift+Tab move from "
                    "link to link, and Enter opens one in your browser. A timestamp "
                    "such as 12:34 is a link too: Enter plays the episode from there."
                ),
                keys=("H", "Shift+H", "Tab", "Enter"),
                hear="Link, and its name; or Timestamp, and a time.",
            ),
            Step(
                title="Copy the notes, or list the links",
                body=(
                    "Copy Notes copies them as plain text and tells you how many "
                    "words. The Applications key on it offers Markdown or formatted "
                    "text too. Links lists every link with where it goes. View in "
                    "Browser shows the notes as the podcast wrote them."
                ),
                keys=("Alt+C", "Alt+K", "Alt+R"),
                hear="How many words it copied, or how many links there are.",
            ),
            Step(
                title="Open About This Episode",
                body=(
                    "Many podcasts send more than a title: who is on it, the best "
                    "moments, podcasts they recommend, a way to support them. Before "
                    "the window opens, Cast sums it up in one line. Ctrl+Tab moves "
                    "between the tabs, and you only get tabs that have something in "
                    "them."
                ),
                keys=("Ctrl+Shift+A", "Ctrl+Tab"),
                hear="Extra details for this episode, then a count of each kind.",
            ),
            Step(
                title="Read the transcript",
                body=(
                    "When a podcast publishes a transcript, Read Transcript on the "
                    "episode's menu opens it in a reader that follows along as the "
                    "episode plays. Arrow to any line and press Enter to hear the "
                    "moment it was spoken."
                ),
                keys=("Shift+F10",),
                hear="The transcript, following along as the episode plays.",
            ),
            Step(
                title="Ask AI about notes that run long",
                body=(
                    "AI help stays off until you turn it on in Preferences, under The "
                    "window, and nothing is sent until you ask. Once it is on, Help, "
                    "AI Features has Ask About These Show Notes and the Free AI "
                    "Assistant, which can sum up, explain or shorten them for you."
                ),
                command="tools.hosted_ai_ask_document",
                keys=("Ctrl+Alt+Z", "Ctrl+Alt+G"),
                hear="The privacy agreement the first time; after that, a box for your question.",
            ),
        ),
        closing=(
            "You cannot change show notes, so an AI answer comes with a Copy button "
            "if you want to keep it."
        ),
        then=("how-much-did-i-listen",),
    ),
)
