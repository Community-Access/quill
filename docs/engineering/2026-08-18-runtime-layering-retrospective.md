# The runtime diet, the dead engines, and the day the office could finally build

*An engineering retrospective, 2026-08-17 and 2026-08-18. Written in plain
English on purpose: the lessons here are worth more than the megabytes, and
lessons nobody can read are lessons nobody keeps. The technical record with
every measurement is
[the runtime layering delta](../design/2026-08-17-runtime-layering-delta.md);
the procedure it produced is
[build-machine-sync](../build-machine-sync.md).*

## The one-paragraph version

Every QuillVille app used to install one enormous 735 MB engine stuffed with
everything any app might ever want. Over two days the engine went to 335 MB
and then to **294 MB**, the heavy audio and video tools moved to the three
apps that actually play sound, three voices that had been silently broken for
months came back from the dead, a British writer can finally pick the British
dictionary that was sitting on her disk the whole time, and a second machine
built the runtime for the first time and got the same answer as the first.
Nothing lost its powers. Several things got theirs back.

## What changed, in plain words

- **The engine went on a diet: 735 to 294 MB.** Not by cutting features — by
  cutting a compiler, a second copy of Python, a test framework, three
  engines that could not run, and a few dozen packages that rode along from
  one machine's Python for months with nothing in the product able to call
  them. Nobody will miss any of it, because nothing could ever reach it.

- **Three voices came back from the dead.** Two dictation engines and the
  neural voices shipped broken, and the app swore they were fine because it
  only ever asked "are you there?" — never "do you work?". The broken copies
  are gone, so the real ones — downloaded fresh, verified, working — can
  finally answer the call.

- **Twenty-two Englishes appeared out of thin air.** They were always
  installed; the language chooser refused to see them because it looked only
  at the download folder. Now every one is on the menu, each with a name a
  screen reader says like a person: "English (South Africa)", never "en_ZA".
  Twelve more languages — German, Italian, both Portugueses, Dutch, Polish,
  Russian, Swedish, Danish, Norwegian, Czech, Romanian — are built, pinned,
  and licensed, about ten megabytes for all twelve, waiting on one publish
  command.

- **The heavy tools travel with the bands that play them.** ffmpeg and mpv —
  304 MB — no longer stow away in every installer. Radio, Cast and Studio
  pack their own; Weather just carries the forecast. And an app that carries
  no instruments now strips the shared work area before packing, so build
  order can never sneak 304 MB into a forecast app again.

- **What ships is declared, not inherited.** The runtime's contents used to
  be whatever the build machine happened to have installed. Every real
  feature is now named in the project — the GLOW large-print engine, Windows
  OCR, Report a Bug, GitHub open and save, the documents stack — so any
  machine that follows the instructions builds the same product. The proof:
  a machine that had never built the runtime built it, both gates green,
  every feature probed working inside the finished bundle.

- **The Lite editions finally tell the truth.** The tiny 2–3 MB installers
  have always promised to download the shared runtime when it is missing —
  from a release asset that no build produced and no release carried. The
  runtime's standalone installer now exists and gets built like everything
  else.

- **The family has its first per-app Offline Edition.** Audio Studio's
  `-Offline` installer bundles the dictation engine and a starter model,
  fetched at build time from the same pinned, verified vault the in-app
  download uses — offline and online users end up with byte-identical
  components. And because the runtime is shared, installing it gives every
  QuillVille app on the machine offline dictation.

## How you get the things that are not in the box

The apps keep their installers small by leaving the biggest, rarest things
out of the box, and the way you get them is the same every time:

1. **Nothing downloads without consent.** The offer says what it is and how
   big it is, and waits.
2. **Every download is verified.** Each component is pinned to an exact
   SHA-256 fingerprint in the source; a file that does not match to the byte
   is refused.
3. **Once fetched, it is yours.** It lands in your data folder and works
   offline forever after.
4. **The box never fights the download.** A broken copy baked into the app
   used to beat a working copy on disk, silently and permanently. A build
   rule with a gate behind it now makes that impossible.
5. **Remove is honest.** If a component can be removed, the list offers
   Remove; if it is part of the app, it does not pretend otherwise.

And for people the internet cannot reach, the Offline Editions bundle those
same verified bytes at build time. Same truth, two delivery paths.

## What we learned

1. **A broken copy in the box beats a working copy on disk.** Anything baked
   in wins over the same thing installed later, permanently. A component
   meant to be downloaded on demand must never also be packaged in.
2. **"Is it present?" is not "does it work?"** Three engines answered yes to
   the first and no to the second, for months, and the app only asked the
   first.
3. **A gate that compares names cannot catch behaviour.** The gate that found
   the dead engines runs the finished build and imports things. Both
   name-comparing gates had passed every broken build.
4. **What ships must not depend on what one laptop has.** Half the size drift
   between machines traced to packages that happened to be installed where
   the build ran. Declare, or drift.
5. **Check who actually uses a thing before deciding what it costs.** The
   spell checker looked like a shared cost across eight apps; only the editor
   can call it. That one fact changed the language plan completely.
6. **A written specification is not a shipped feature.** Social's spell check
   has a keymap entry and a PRD section and no code. Know which side of that
   line a thing is on before planning around it.
7. **Poke the built artifact; do not read its file list.** Every real finding
   came from running the packaged app and asking it to load things.
8. **Shared build areas need owners.** The runtime dist is written by one
   build and packed by the next; the day this was forgotten, a text-expansion
   app shipped 304 MB of media tools. Now every non-media app strips before
   it packs.
9. **When a promise depends on an asset, gate the asset.** The Lite
   installers' runtime download pointed at a file that did not exist, on
   every release, and nothing could notice. If a URL is part of the product,
   something must build and publish what it points at.

## Where the numbers stand

Measured, not estimated, 2026-08-18:

| Thing | Before | After |
|---|---|---|
| Shared runtime | 734.9 MB | 294.1 MB |
| Quill Weather installer | 191.5 MB | 103.6 MB |
| QUILL Cast installer | 178.0 MB | 94.8 MB |
| Quill Radio installer | 230.4 MB (2.2.0) | 157.2 MB |
| Dead speech engines shipping | 3 | 0 |
| English dictionaries a user could choose | 1 | 22 (+12 pending publish) |
| Machines that could build the runtime | 1 | any that follow the README |

## What remains

- Publish the runtime installer and the twelve dictionary assets (two upload
  commands; the entries and instructions are staged beside the artifacts).
- Move Cast, Social, Beacon and Inkwell's installers to the shared-runtime
  layout so they gain Lite and Companion flavors.
- Stage 3 of the original plan (a documents layer and a spell-check layer,
  so seven apps drop what only the editor uses) and Stage 4 (price a
  shared-library ffmpeg before touching the 194 MB pair).
- Social's spell checker: specified, keymapped, unbuilt.
