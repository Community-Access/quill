# QUILL University: plan of record

Status: plan, written 2026-11-07. Nothing in it is built yet. The decisions
that are Jeff's to make are listed in section 13, and the work still to do is
at the bottom under Remaining tasks.

## 1. What this is

QUILL University is a course, spread over weeks, that teaches the whole QUILL
family: QUILL, QUILL Lite, Quill Radio, QUILL Cast, Quill Weather, Quill
Converter, Quill Inkwell, Quill Studio, QUILL Transcribe, Quill Player and
Quill Beacon, plus the skills that cut across them, such as AI, GitHub and
accessible documents.

The most important decision in this plan is what the course is not. It is not
a second set of lessons. We already have a lot of teaching material, and most
of it is generated from the code so it cannot go stale:

- About 160 in-app guided lessons across six apps, in the shared tutorial
  window (Help, then Tutorials, in each app). Today's generated books count 45
  lessons for QUILL, 31 for QUILL Lite, 44 for Quill Radio, 25 for QUILL Cast,
  11 for Quill Weather and 5 for QUILL Transcribe. Each lesson already carries
  its own length in minutes.
- Ten follow-along tutorials in `docs/tutorials/`, published to
  `docs/site/tutorials/` by `docs/tutorials/build_html.py`, with an eleventh,
  on practising GitHub safely, being written on its own branch.
- The QUILL Cast, a 54-episode audio course on QUILL in eight parts, with a
  transcript for every episode (`docs/podcast/`).
- A user guide for every app, a QUILL Lite AI guide, and the GitHub Guide
  (`docs/user guide/github-guide/`, eleven chapters, for QUILL and QUILL
  Lite).
- The public practice repository `Community-Access/quill-github-practice`,
  a template people copy, with a Set up practice workflow.

So QUILL University is a **syllabus and the glue around it**. It puts the
existing pieces in an order, in weeks someone can actually get through,
and adds only what is missing: a short introduction to each week, practice
files, a checkpoint at the end of the week, an instructor's edition, and
versions in audio and braille. Where a lesson already exists, the course points
at it and never copies it. A copied lesson is a lesson that is right in one
place and wrong in the other by the next release.

## 2. Who it is for

### Learners

Blind and low-vision people first, most of them screen-reader users, some
using magnification, some using a braille display, and a few using braille
alone. The course runs from the person who installed their first app last
week to the power user who wants to rebind everything and automate the rest.

What we assume a learner can already do, and say so up front:

- Use Windows with their own screen reader at a basic level: start a program,
  move through a menu, a dialog and a list, type and edit text, and open a
  file.
- Know their screen reader's own keys for reading and for the mouse cursor
  or review cursor, if they need them.

We do not teach the screen reader itself. The orientation page points
people who are not there yet at their screen reader's own training, and at
their local rehab or assistive technology service, rather than half-teaching
it badly.

### Trainers

Rehab teachers, assistive technology instructors, vocational counsellors,
library and school staff, and the friend or family member who ends up being
the help desk. They need things a learner does not: a time plan for a class,
what to set up beforehand, what usually goes wrong, how to adapt for a
learner with low vision or one who reads braille only, and a way to show a
learner has done the work. That is the instructor's edition (section 8).

### What the course must never assume

- That the learner can see the screen, or that the trainer can see the
  learner's screen.
- That the learner has an account anywhere. The core course needs no
  account, no sign-in and no internet beyond downloading the apps. Only the
  AI and GitHub tracks need accounts, and they say so before the first
  lesson.
- That the learner uses a particular screen reader. Every lesson is written
  to work with NVDA, JAWS and Narrator, and says when they differ.

## 3. Shape: tracks, weeks, sessions, lessons

### The units

- **Lesson**: one thing you can do afterwards. 3 to 20 minutes. Almost always
  an existing in-app lesson, follow-along tutorial, podcast episode or guide
  chapter.
- **Session**: one sitting, 30 to 45 minutes. A short introduction, three to
  six lessons, and a practice task. A session is the right size for one class
  period and for one evening at home.
- **Week**: three sessions and a checkpoint. About two to two and a half hours
  of work, never more than three. A week has one theme and ends with
  something the learner can do that they could not do on Monday.
- **Track**: a run of weeks on one app or one skill. One to four weeks.
- **Term**: a suggested run of tracks, eight weeks long, for people and
  classes who want a schedule. Terms are a convenience. The tracks are the
  real structure, and anyone can take them in any order the prerequisites
  allow.

Why weeks of about two hours: that is what a learner with a job, or a rehab
student with other classes, can keep up, and it is what a trainer can fit into
one or two class sessions a week. Self-paced learners can go faster; nothing
is locked.

### Every week has the same five parts

The same order every week, so a screen-reader user can jump by heading to the
part they want without hunting:

1. **This week**: what you will be able to do by the end, what you need
   first, and how long it takes. A few sentences.
2. **Listen** (optional): the matching QUILL Cast episode or a course audio
   lesson, for people who learn better by ear first.
3. **Do**: the sessions, each a list of lessons in order. Each item says
   where the lesson lives (in the app, on the website, in a guide) and how
   long it takes.
4. **Practise**: a task with the week's practice files, written as a goal
   rather than steps ("make this letter ready to send"), so the learner has to
   put the lessons together on their own.
5. **Check yourself**: the checkpoint (section 6), then **Going further**,
   which points at the user guide chapters for people who want every detail.

### Tracks

The **Core track** comes first, for everyone, and is one week long:

- Installing a QuillVille app, and the difference between the installer and
  the portable version.
- The habits every app in the family shares: F1 answers everywhere with what
  the window is for and what the focused control does; every menu item shows
  its key; Help, then Tutorials, opens the guided lessons; the command list
  finds anything by name; settings, and the feedback setting that chooses
  between sounds and speech.
- Where your files and settings live, backing them up, and Safe Mode when
  something will not start.
- Getting help: the user guide, the tutorials, and writing to support. Not
  GitHub issues.
- Choosing your path through the rest of the course.

Then one **app track** per app. Proposed lengths, set by how much each app
already teaches:

| Track | Weeks | Built mostly from |
| --- | --- | --- |
| QUILL Lite | 2 | its 31 in-app lessons, user guide, AI guide |
| QUILL | 4 | 45 in-app lessons, tutorials 1 to 7, the QUILL Cast |
| Quill Radio | 2 | 44 in-app lessons, tutorial 9 |
| QUILL Cast | 1 | 25 in-app lessons, tutorial 10 |
| Quill Weather | 1 | 11 in-app lessons, user guide |
| Quill Converter | 1 | user guide; lessons to write |
| Quill Inkwell | 1 | user guide; lessons to write |
| QUILL Transcribe | 1 | 5 in-app lessons, user guide |
| Quill Studio | 2 | user guide, tutorial 4; lessons to write |
| Quill Player | 1 | user guide; lessons to write |
| Quill Beacon | 1 | user guide; lessons to write |

Weather, Converter and Inkwell are short enough to share a week in a term
schedule, and the terms below do that.

Then the **cross-family tracks**, which belong to no single app:

- **AI across the family** (2 weeks): Choose Your AI, the free hosted AI,
  using your own key or subscription, Ask, the AI features in each app, what
  is sent where, and responsible use. Built from `docs/design/codex.md`
  sections as they ship, the AI lessons in QUILL and QUILL Lite, the QUILL
  Cast AI part (episodes 34 to 39), the QUILL Lite AI guide and the
  responsible AI use page.
- **GitHub** (3 weeks): from signing in to reviewing a pull request, built
  from the GitHub Guide, tutorial 8, the practising GitHub safely tutorial,
  and the practice repository. Week one never touches a real project.
- **Accessible documents** (2 weeks): Word, EPUB, PDF, DAISY and braille out
  of QUILL; rescuing a scanned PDF; GLOW checking and fixing; math. Built
  from tutorials 3, 6 and 7, Converter, and QUILL Cast parts 3 and 7.
- **Audio production** (2 weeks): Read Aloud and voices, narration, the
  Audio Studio, Quill Studio, and publishing a podcast feed. Tutorial 4, QUILL
  Cast part 5, and Studio.
- **Writing and organising** (2 weeks): Story Studio, the Accessible Vault,
  daily notes and Git sync. Tutorial 5 and QUILL Cast part 7.
- **Publishing on the web** (1 week): WordPress and Forms, from the in-app
  WordPress and Forms lessons and `docs/design/wordpress.md` as it ships.
- **Developer** (2 weeks, for power users): coding in QUILL, Check This File,
  the agents, Quillins and building your own. From the coding lessons,
  `docs/design/code.md` and QUILL Cast episodes 50 and 51.

### Prerequisites

Kept short and written on every track's first page. Core is required before
everything. Then:

- QUILL or QUILL Lite before any cross-family track except GitHub's first week.
- QUILL Cast after Quill Radio is recommended, not required. They share the
  player keys, and Radio teaches them first.
- Transcribe and Studio before Audio production.
- The GitHub track's first week before Developer.
- AI across the family before the AI parts of Writing and Developer.

A prerequisite is a recommendation with a reason ("Radio teaches the player
keys that Cast takes for granted"), never a lock. Nothing in the course
checks whether you did the earlier track.

### Paths and terms

Four suggested paths, so a learner does not face fifteen tracks on day one:

- **Writer**: Core, QUILL Lite, Accessible documents, AI, then QUILL if they
  want more.
- **Listener**: Core, Radio, Cast, Weather, then Player.
- **Producer**: Core, Transcribe, Studio, Cast, Audio production.
- **Power user**: Core, QUILL, GitHub, AI, Developer.

And two eight-week terms for classes:

- **Term 1, The family** (first to ship): week 1 Core; weeks 2 and 3 QUILL
  Lite; week 4 Radio, first half; week 5 Radio second half with Cast; week 6
  Weather and Inkwell; week 7 Converter with the start of Accessible
  documents; week 8 AI across the family, first week, and a final project.
- **Term 2, Going deeper**: QUILL (4 weeks), GitHub (3 weeks), and a final
  project. Later terms are put together from the remaining tracks as they
  become ready.

The final project in a term is one real task chosen from a short list (make
an accessible newsletter; record, edit and publish a five-minute show; build a
listening lineup for the week and record one show from it), done with the
practice files and the learner's own work.

## 4. A sample week, to show the shape

This is Term 1, week 4, built entirely from Quill Radio's existing in-app
lessons. The minutes are the ones the lessons already carry.

**This week.** By Friday you will play, keep and organise stations, find
almost anything to listen to, and know how to get yourself unstuck. You need
the Core week and Quill Radio installed. About two hours.

**Listen.** No QUILL Cast episode covers Radio yet; this is where a course
audio lesson would go (section 9).

**Do.**

- Session 1, Your first hour (23 minutes of lessons, plus the introduction):
  Play your first station; Keep a station, and find it tomorrow; The player
  follows you; Do anything by name; Getting unstuck.
- Session 2, Finding something to listen to (42 minutes): Wander the browse
  tree; Search every directory at once; Find a station by its web address;
  Find stations by name, tag and country; Add a station nobody lists; The
  catalog on your own disk; When a station will not play. A trainer with a
  short class splits this one, and the instructor's edition says where.
- Session 3, Making it yours, first half (26 minutes): Folders, and an order
  of your own; Ten stations, no list at all; Make the keys yours; The settings
  actually worth changing.

**Practise.** Using the practice station list, make a folder of three
stations for mornings and one for the evening, put them in the order you
want, and give the one you use most a key of its own. Then delete the
folders, so your real favourites are as you left them.

**Check yourself.** Do it, then answer it:

- Task: with Quill Radio in the background and another program in front,
  pause and resume the player without switching to Radio. What did you hear?
- Questions (answers on the next page, under their own heading): Where do you
  go when a station will not play? What is the difference between a favourite
  and a folder? How do you find out what key a command has, if the menu does
  not show one?

**Going further.** The Quill Radio user guide chapters on browsing, favourites
and settings.

Week 5 picks up at Recording and More than radio, with the QUILL Cast track
starting on the third day.

## 5. Practice files and sandboxes

### Practice files

Each track gets a small practice pack: the files its lessons and practice
tasks use, made for the course and free of anyone's real information.

- QUILL and QUILL Lite: a messy letter to tidy, a long report with headings
  to navigate, a document with accessibility problems for GLOW to find, a
  short manuscript for Story Studio, a table to edit.
- Converter and Accessible documents: a scanned PDF (a real scan of a page we
  wrote), a Word file, an EPUB, a Markdown file.
- Radio: a station list file to import, so every learner sees the same
  stations whatever the directories return that week.
- Cast: the course's own podcast feed. Following the course in Cast is the
  practice.
- Transcribe and Studio: two or three minutes of course audio with two
  speakers, recorded by us, so nobody has to bring a recording and nobody
  transcribes a stranger.
- Weather: nothing to ship. The app already rehearses an alert.
- Inkwell: an abbreviation set to import.
- GitHub: the practice repository, which is already a template with a Set
  up practice workflow.

Where they live: the source files live under `quill/` as package data (a
path such as `quill/core/university/practice/<track>/`), for the same reason
feature code never lives in `standalone/`: every gate scopes to `quill/`.
They ship in every installer and portable zip, because nothing a lesson needs
is downloaded on first use. Each pack is also on the website as one zip for
trainers preparing a room of computers.

How a learner gets them: the course page says where they are on disk, and
phase 2 adds an Open Practice Files command to each app's Help menu, which
copies the app's pack into a QUILL University folder in Documents and opens
it. Copying, never opening the installed copy, so a learner can wreck a
practice file and start again.

### Sandboxes

The risk of practice is that it changes the learner's real setup: favourites
added, keys rebound, a podcast followed. Phase 1 handles it the plain way:
every practice task that changes something ends with undoing it, and says so,
as the sample week does.

A real practice mode, an app started on a separate throwaway profile, is a
bigger piece of work in every app and is not in phase 1. Section 13 asks
whether to build it later.

## 6. Checkpoints and quizzes

Nothing in QUILL University is graded, timed or required to go on. That is
the same rule as the in-app lessons. A checkpoint is there so a learner knows
they have it, and so a trainer knows what to go over again.

Each week's checkpoint has two parts:

- **A task**, with what you should hear when it worked, the same way every
  in-app lesson step says what to listen for. Where an app already has a
  tutorial check for that state (the tutorial model's `check` field, such as
  "something is playing now"), the checkpoint can use it, so the app notices
  when you have done it.
- **Three to five questions**, as a plain numbered list. The answers are on
  their own page, or under their own heading below a clear "answers follow"
  line, so nobody reads an answer by arrowing one line too far. No drag and
  drop, no matching columns, no timers, no images, no multiple choice that
  only makes sense when you can see all the options at once.

Progress is the learner's own: the tutorial window already keeps lesson
progress on the learner's computer (`quill/core/tutorials/progress.py`).
The course adds no account and sends nothing anywhere.

## 7. Completion certificates

Recommended: a certificate the learner makes themselves, on their own
computer. At the end of a track or a term, a page on the site asks for the
name to print and the track, and produces an accessible PDF and a plain text
version. Nothing is sent to us, so nothing is verified by us, and the
certificate says so in plain words: it records that the learner says they
completed the course.

For classes, the instructor's edition has a version a trainer fills in and
signs, which carries the trainer's organisation rather than ours. That is
the one an employer or a rehab case file can lean on, because the trainer saw
the work.

A certificate we verify ourselves would need accounts, records of learners
and someone to look after them. That is a different kind of project, and
section 13 asks whether Jeff wants it at all.

## 8. The instructor's edition

One page per week, next to the learner's page, never mixed into it. Each
has:

- Objectives in a sentence or two, and how they connect to the next week.
- A time plan for a 60-minute and a 90-minute class, saying which lessons to
  do together, which to set as homework, and where to split a long session.
- Setting up: which apps and versions, the practice pack, a test of the
  screen reader with each app, and anything the network at an agency or
  school is likely to block (station streams, AI services, GitHub).
- What usually goes wrong. Seeded from the `note` fields the in-app lessons
  already carry and from what reaches support, and added to as trainers tell
  us.
- Differences between NVDA, JAWS and Narrator for that week's work.
- Adapting the week: for magnification users, for braille display users, for
  a learner who reads braille only (everything QUILL speaks is also brailled,
  which the course can rely on), for a learner with some hearing loss, and
  for learners who need more time.
- Teaching remotely: sharing computer sound so the trainer hears the
  learner's screen reader, and asking a learner what they heard rather than
  what they see.
- The checkpoint answers, and the signed certificate.

The instructor's edition is public. Hiding it helps nobody, and plenty of
learners teach themselves with a trainer's notes.

## 9. Audio and braille-ready versions

### Audio

Two kinds of audio, kept apart:

- **The QUILL Cast** stays what it is: the audio course on QUILL. Weeks that
  match an episode point at it.
- **Course audio lessons**: one short episode per week (10 to 15 minutes),
  introducing the week and walking through the hardest part of it, for the
  apps the QUILL Cast does not cover (Radio, Cast, Weather, Converter,
  Inkwell, Studio, Transcribe, Player, Beacon). Made with the same pipeline
  and the same two Kokoro hosts, scripts in the same `[LIAM]` and
  `[JESSICA]` format, with a transcript for every episode, which the site link
  gate already checks for. Whether these are a new feed or a new part of the
  QUILL Cast feed is decision 6 in section 13.

Every week's text page also reads well aloud, and trainers can point learners
at QUILL's or QUILL Lite's own Read Aloud to hear it.

### Braille, large print and offline

Each track is published, beside its web pages, as:

- **EPUB**, the same way every document in `docs/` already has one.
- **A braille-ready file** (BRF), Unified English Braille contracted, made
  with QUILL's own braille production rather than a separate tool, so the
  course proves the feature it teaches. Uncontracted on request.
- **DAISY**, from QUILL's DAISY export, for players and readers that prefer
  it.
- **Large print**, which is the web page and its print stylesheet: no
  separate file to keep up.

These are built from the same generated Markdown as the web pages, so they
cannot say anything different.

## 10. Delivery

### On the website

A new section of quillforall.org at `docs/site/university/`, linked from the
site's main navigation and from `docs.html`:

- `index.html`: who it is for, what you need, how to choose a path, the
  terms, and which tracks are ready today.
- One page per track, one per week, and one instructor's page per week.
- The practice packs, the braille, EPUB and DAISY files, and the certificate
  page.

The week pages link to the existing tutorial pages under
`docs/site/tutorials/`, the app tutorial books under `docs/site/docs/`, the
user guides and the podcast transcripts. They do not copy them.

### From inside each app

Three steps, in this order:

1. Nothing new in phase 1. Help, then Tutorials, is already in every app that
   has lessons, and it is the offline heart of the course.
2. Phase 2 adds QUILL University to each released app's Help menu. It opens
   that app's track page in the learner's browser. Every app that gets it
   needs a key or a written reason under the family rules (rule 8, and rule 9
   for something used once in a while), a label built with the live key, an
   access key that collides with nothing, F1 help at the construction site,
   and an entry in the network egress audit if it is classed as one. QUILL and
   QUILL Lite get it in the same change, so QUILL Lite is never ahead.
3. Later, the tutorial window could show which lessons belong to the week the
   learner is on. Only if trainers ask for it.

Whether the course pages also ship inside each installer, for learners with no
internet at home or in class, is decision 7.

## 11. Keeping it accurate

The course is only worth having if it is right on the day someone uses it.
Keys and menus move, and a lesson that teaches a key that now does something
else is worse than no lesson. The repo already solves this three times
(GATE-KEYREF, GATE-HELPREF and GATE-TUTDOC) by generating the document from
the code. The course does the same.

### One source: a course manifest in code

The course is described in a wx-free package, `quill/core/university/`, in
the same style as the tutorial content modules: plain data saying which
tracks there are, which weeks are in each, and which sessions and items are
in each week. An item points at something that already exists, by an
identifier rather than by a copy:

- an in-app lesson, by app and lesson id in its `TutorialSet`;
- a follow-along tutorial, by file;
- a QUILL Cast episode, by number;
- a user guide or GitHub Guide chapter, by file and heading;
- a practice file, by path.

The authored text in the manifest is only the glue: each week's introduction,
the practice task, the checkpoint and the instructor's notes. Any key in that
text is written as a command id and rendered with the shipped default through
`DEFAULT_KEYMAP` and `APP_KEYMAPS`, exactly as the tutorial books are. Never
a typed chord.

A generator, `quill/tools/build_university.py`, renders the manifest to
Markdown under `docs/university/` and to the web pages under
`docs/site/university/`, and the braille, EPUB and DAISY versions from the
Markdown.

### GATE-UNIDOC: the checks

A pytest gate, plus a row in `platform_report`, that fails when:

- **The generated pages have drifted** from the manifest (the same check as
  the other generated references, with `--write` to regenerate).
- **A reference resolves to nothing**: a lesson id no longer in its app's
  tutorial set, a tutorial file renamed, a guide heading that is gone, a
  practice file missing, a QUILL Cast episode not in `episodes.json`. An
  episode whose audio is not published in `audio_assets.json` is linked as a
  transcript only, the same rule the site uses.
- **Authored text contains a chord**: a pattern check for Ctrl, Alt, Shift,
  Insert, Windows and function-key chords in the manifest's prose, so a key
  can only arrive through a command id.
- **A command id is unknown** to the command registry, which is how a renamed
  or removed command shows up.
- **A week is over its time**: the gate adds up the minutes the lessons carry
  plus the authored estimates, and fails a week over three hours. When a
  lesson grows, the week that holds it says so.
- **A track that is not ready is published**: each track names its app's
  status (section 12), and only a released, signed-off track builds web
  pages. Draft tracks still build their Markdown, so they can be reviewed.

Menu paths ("Help, then Tutorials") are the one thing harder to check than
keys, because the tutorial books state their door as text. The first version
keeps menu paths to a short list in the manifest, each paired with the command
id at its end, and a test checks that command still lives in that menu, using
the same menu data the menu shape gate reads. That is phase 3, not phase 1.

### The other gates the course must respect

- **GATE-SITE-LINKS**: every file the course adds under `docs/` (outside
  `docs/site/`) is flattened into `/docs/` by its bare name, so every course
  file starts with `university-` (for example
  `docs/university/university-term-1-week-04.md`). This plan's own name,
  `quill-university.md`, is unique today. The site link test models the new
  `docs/site/university/` pages like the rest of the shell, so a broken link
  in a week fails the build.
- **The documentation chord gates**: the generated course Markdown joins the
  corpus that `test_documentation_chords.py` reads, and the QUILL Lite pages
  join GATE-DOCKEY's, so a chord the course teaches must be bound and must
  belong to the command named beside it. Generating keys from command ids
  should make both pass by construction; the gates are there for when it does
  not.
- **Docs HTML and EPUB parity**: every Markdown file under `docs/` keeps its
  HTML and EPUB siblings, which the pre-commit hook already enforces.
- **Test file names**: the gate's test needs a basename used nowhere else in
  `tests/`, such as `test_university_course.py`, because test directories are
  not packages.

### What a gate cannot check

Whether a week still makes sense. Each week records the app version it was
last walked against, with a screen reader. `platform_report` lists, as a
warning rather than a failure, the weeks walked against a version older than
the app's current minor version. Before each app release, its track's
warnings are part of the release checklist, and a week is walked with NVDA and
JAWS before it is published for the first time, with the result in
`docs/qa/`.

## 12. Which apps are ready, and how a new one joins

### The bar for a track

An app gets a published track only when all of these are true:

1. It is publicly released, with a dated release in its changelog and a
   download on the site.
2. Its screen-reader sign-off is done, with nothing open for it in
   `docs/qa/screen-reader-checks-2026-10.md` or its successor.
3. Its user guide is current for that release.
4. It has in-app lessons in the shared tutorial window and a generated book
   (GATE-TUTDOC), or follow-along tutorials written for the track.
5. Its F1 help gate is in `platform_report`.
6. Its practice pack exists and has been used once by someone who is not
   the author.

### Where each app stands, as the changelogs say on 2026-11-07

This needs Jeff to confirm (decision 1). It is read from the changelogs, not
from what is actually published.

| App | Latest in its changelog | Track |
| --- | --- | --- |
| QUILL | 1.0.0 | Term 1 uses it lightly; its full track is Term 2 |
| QUILL Lite | 2.0.0, undated | phase 1 |
| Quill Radio | 3.2.0, 2026-10-03 | phase 1 |
| QUILL Cast | 2.0.0, 2026-10-03 | phase 1 |
| Quill Weather | 2.2.1, 2026-10-08 | phase 1 |
| Quill Converter | 1.0.0, 2026-09-28 | phase 1, lessons to write |
| Quill Inkwell | 1.0.0 | phase 1, lessons to write |
| QUILL Transcribe | 1.0.0, code done | waits for its screen-reader pass |
| Quill Studio | 2.0.0 built, not released | waits for 2.0 |
| Quill Player | Unreleased | waits for release |
| Quill Beacon | 0.1.0 | waits for 1.0 |

QUILL Transcribe's 1.0 release, and so its track, waits for the 77-item
screen-reader pass in the sign-off document. Its five in-app lessons and its
user guide already exist, so its track can be written as a draft now and
published the day the pass is done.

### How a new app joins

When an app finishes, its track goes through the same steps, so adding one is
routine rather than a project:

1. Add the track to the manifest as a draft, pointing at the app's lessons,
   tutorials and guide.
2. Write the glue: the week introductions, the practice task, the checkpoint
   and the instructor's notes. Write in-app lessons first if the app has
   none: they serve the app's own users whether or not they take the course.
3. Make the practice pack.
4. Record the course audio lesson.
5. Walk the weeks with NVDA and JAWS.
6. When the app meets the bar above, change the track's status to
   published, which is the change that makes the gate build its web pages and
   adds it to the index.

## 13. Decisions for Jeff

1. **Which apps count as released and finished today**, for phase 1. The
   table in section 12 is read from changelogs. In particular: is QUILL Lite
   2.0.0 out, are QUILL 1.0.0 and Inkwell 1.0.0 out, and is QUILL in Term 1
   at all, or does Term 1 teach QUILL Lite as the editor and leave QUILL to
   Term 2?
2. **The name in the menus and on the site.** "QUILL University" throughout,
   or something shorter in a Help menu.
3. **Certificates**: the self-made certificate and the trainer-signed one
   (recommended), neither, or a verified certificate run by Community Access,
   which means accounts and records of learners.
4. **Practice mode**: build a separate throwaway profile in each app later,
   or keep practice as "do it, then undo it" for good.
5. **Licence for the course text**, so agencies can adapt it for their
   classes. A Creative Commons licence such as CC BY 4.0 would allow that;
   the code licence does not obviously cover teaching material.
6. **Course audio**: a new podcast feed for QUILL University, or a new part
   of the QUILL Cast feed. A new feed keeps the QUILL Cast about QUILL; one
   feed means one subscription.
7. **Offline copies**: ship each app's track pages inside its installer (in
   keeping with bundling everything, and useful in classrooms without
   internet), or keep the course on the website with the downloadable
   packs.
8. **Live cohorts**: whether Community Access ever runs scheduled classes
   with a start date, or the course stays self-paced with trainers running
   their own.

## Remaining tasks

Remove each one as it is done, and record it in a short progress log above
this list when the first one lands.

Phase 1: the course for released apps

- Get Jeff's answers to the decisions in section 13.
- Create `quill/core/university/` with the manifest model (track, week,
  session, item, checkpoint) and the Core track.
- Write `quill/tools/build_university.py` to render Markdown and site pages.
- Write GATE-UNIDOC (`tests/unit/docs/test_university_course.py`) and add it
  to `platform_report`.
- Extend the site link test's model to `docs/site/university/` and add the
  course Markdown to the documentation chord corpora.
- Write the Core week.
- Write the QUILL Lite, Radio, Cast and Weather tracks from their existing
  lessons.
- Write in-app lessons for Converter and Inkwell, then their tracks.
- Make the practice packs for those tracks and ship them in their installers
  and portable zips.
- Write the checkpoints for every phase 1 week.
- Build `docs/site/university/index.html`, the track and week pages, and add
  the section to the site navigation.
- Walk every phase 1 week with NVDA and JAWS, and record the result in
  `docs/qa/`.

Phase 2: trainers, formats and the apps

- Write the instructor's edition for every phase 1 week.
- Build the certificate page and the trainer-signed version.
- Generate the braille, EPUB and DAISY versions, and the practice pack zips.
- Add QUILL University and Open Practice Files to each released app's Help
  menu, QUILL and QUILL Lite in the same change.

Phase 3: audio and the cross-family tracks

- Write and record a course audio lesson for each week the QUILL Cast does
  not cover.
- Write the AI, Accessible documents, Writing and organising, Audio
  production, Publishing on the web and Developer tracks.
- Write the GitHub track once the practising GitHub safely tutorial has
  landed, using the practice repository.
- Add the menu-path check to GATE-UNIDOC.
- Add the "last walked against" warning to `platform_report`.

Phase 4: apps as they finish

- QUILL Transcribe: draft its track now; publish it when its screen-reader
  pass in the sign-off document is complete.
- Quill Studio: write in-app lessons and its track; publish when 2.0 is
  released.
- Quill Player and Quill Beacon: in-app lessons and tracks when each is
  released.
- Put Term 2 together, and later terms from the tracks that are ready.
