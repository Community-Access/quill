# QUILL 0.9.0 Beta 3

## One Editor. Every Format. A Community Moving Forward Together.

*From Community Access. Free. Optional by design. Private by default. Built with you.*

QUILL 0.9.0 Beta 3 is more than another beta. It is a celebration of what becomes possible when people test boldly, report honestly, imagine generously, and build together.

At the heart of this release is one transformative promise: **One Editor, Every Format**. The braille correction explored with the community in Beta 2 is now proven, polished, and enabled by default for everyone. RTF and Word documents become genuinely editable rich documents. A single Document Format switcher lets one living document move among plain text, Markdown, HTML, Rich Text, and Word without forcing you into a different editing world.

Around that centerpiece is an extraordinary collection of community-powered progress: every open community bug report addressed, portable updates made clearer, imports made safer, Narrator treated as a first-class screen reader, GitHub transformed from a viewing window into a working environment, local git conflicts made understandable, the Offline Edition made truly offline, and a constellation of small accessibility-first tools designed to make daily work faster and more humane.

Every shortcut is explained. Every important safeguard is named. Every limitation is stated honestly. Nothing here asks you to discover essential behavior by accident.

This is the full, friendly companion to the **“0.9.0 Beta 3”** section of `CHANGELOG.md`. The shorter summaries shown under **Help > What's New** and **Check for Updates** come from that changelog. This document tells the complete story: what changed, why it matters, how to use it, and how the community helped make it real.

---

## The Heart of Beta 3: One Editor, Every Format

For years, document formats have tried to dictate the experience: one tool for plain text, another for Markdown, another for rich text, another for Word. Beta 3 turns that relationship around. The format now serves the writer. The editor remains familiar.

### The braille fix graduates — enabled for everyone by default

In Beta 2, we asked braille display users to step into an experimental space, test a proposed correction, and tell us exactly what happened. You did. Your reports confirmed that it works.

Text now begins in **braille cell 1**, eliminating the long-standing “cell two” behavior that RichEdit controls share with Microsoft Word. When text is selected, the display now shows **dots 7-8**, restoring the tactile selection feedback braille users expect.

In Beta 3, the experiment becomes the standard. There is nothing special to turn on, no Experimental tab to find, and no restart ritual. Every document opens in the same native Windows editor QUILL users already know, now carrying the braille correction automatically.

Two straightforward checkboxes under **Preferences > Braille** control the complete behavior, and both are checked by default:

- **Fix braille cell alignment and selection dots (recommended)** — enables the system-edit emulation that starts braille output in cell 1 and exposes selection dots.
- **Hide editor border (required for braille cell alignment)** — testing revealed that the visible editor border itself shifts braille output away from cell 1. The borderless frame is therefore a functional part of the correction, not merely a visual preference. If you uncheck it, QUILL warns you clearly that braille cell alignment will break before applying the change.

Users who experimented with alternate editor surfaces in earlier betas are brought forward automatically. Those retired experimental settings are removed during upgrade, the new default is applied, and QUILL explains once, in plain language, that the editor settings were simplified.

This is exactly how a beta should work: the community tests an idea, the evidence guides the decision, and a better default reaches everyone.

### Rich text becomes real: RTF documents are truly formatted in the editor

Open an `.rtf` file in Beta 3 and the formatting is no longer flattened, simulated, or merely described. It is there, alive in the document.

Bold text is genuinely bold. Headings carry real sizes. **Ctrl+B** applies true bold formatting. **Insert > Heading 2** creates an actual heading. **Describe Formatting at Cursor** reads the live document state and can report, for example: “Arial, 14 point, bold, centered.”

The guiding rule is simple and powerful: **bold means bold — and QUILL speaks the language of the document you are editing.**

- In Markdown, **Ctrl+B** continues to wrap the selection in `**`, exactly as it always has.
- In HTML, the same command produces `<strong>`.
- In RTF, it applies real rich-text bold.

One command. One familiar intention. The correct result for the current format.

Rich mode changes presentation, not the trusted foundation beneath it. Search, spell check, AI commands, read aloud, bookmarks, inline notes, and braille continue working with the same document text they always have. Autosave also protects the full rich document: snapshots include formatting as well as text, so crash recovery can restore your bold, headings, and other formatting rather than recovering only the words.

Plain-text documents remain respectfully plain. The first time you use a formatting command in a `.txt` file, QUILL asks once what you intend:

- Treat the document as Markdown.
- Convert it to Rich Text.
- Keep it as plain text.

Choose **stay plain**, and QUILL remembers the answer instead of asking repeatedly.

### Word documents become editable — without pretending nothing can be lost

A `.docx` file can now open for genuine rich editing and save back as a real Word document.

Word files can contain structures QUILL’s editor cannot fully preserve, including tables, images, comments, tracked changes, headers, and footers. Rather than hiding that reality, QUILL meets it with clarity at the moment it matters:

- A **clean Word file**, containing nothing QUILL cannot carry, opens directly in rich mode.
- A Word file containing unsupported features identifies those features specifically and asks how you want to proceed: open for reading and plain editing, which is the safe default; edit as Rich Text while understanding exactly what cannot survive a save; or edit a copy while leaving the original untouched.
- The first rich save over a flagged original automatically creates a **timestamped backup** beside it.

QUILL never silently rewrites a complex Word file while asking you to trust that everything survived. The editor gives you meaningful choices, protects the original, and lets you decide.

### One switcher connects the formats

The new **Document Format** switcher brings the promise together.

Open it through any of these paths:

- **Format > Document Format...**
- **Ctrl+Shift+Grave, K**
- The Command Palette
- The new **Format** cell on the status bar, which displays the current format and opens the switcher when you press Enter on it

From there, the current document can move among:

- Plain text
- Markdown
- HTML
- Rich Text (RTF)
- Word (`.docx`)

The conversion is meaningful, not cosmetic. Moving a Markdown draft into Rich Text turns `# headings` into real headings. Moving a rich document into Markdown first produces a specific warning naming anything that will not survive the conversion.

A format change also never silently overwrites the old file. The next save proposes a filename with the correct extension — for example, `notes.md` becomes `notes.rtf` — so the file on disk always tells the truth about the format inside it.

### Rich editing on macOS — ready from the first launch

Rich mode ships ready to use on the Mac. The macOS editor remains the same native text view VoiceOver users already know, and the application now **bundles everything required for rich mode**. There is nothing additional to install and nothing to configure.

Open an `.rtf` or Word document and it appears formatted. **Ctrl+B** applies genuine bold and announces “Bold.” **Insert > Heading 2** applies a real heading. **Describe Formatting at Cursor** reports the live formatting, such as “Helvetica, 14 point, bold.”

If the rich-text bridge is ever unavailable on a particular system, QUILL does not collapse or strand the document. It opens the same content as editable text and places a clear explanation in the status area. Nothing breaks, nothing is discarded, and VoiceOver continues reading the same native control.

#### Mac and VoiceOver testers: your experience is the promotion gate

Please put this through a real workflow:

1. Open an `.rtf` file.
2. Apply formatting.
3. Save it.
4. Close and reopen it.
5. Confirm that the formatting survived.

For VoiceOver users, please also test whether typing echo, arrow-key review, and selection announcements continue to work normally. Check whether formatted content — such as a bold word or a sized heading — reads and navigates correctly.

Send the result through **Help > Report a Bug** and include your macOS version. A report that says “it works perfectly” is every bit as valuable as a failure report. Real-hardware evidence in both directions is the promotion gate, just as braille users’ Beta 2 reports made the Windows correction ready for everyone.

---

## Community Reports, Real Repairs

Every bug report is a person encountering friction while trying to create, read, learn, or contribute. Beta 3 treats those reports accordingly: not as loose tickets to close, but as invitations to make QUILL more trustworthy.

### Portable updates now offer an actual next step

A community member on Mastodon reported that a portable update finished with only **Open folder** and **Close**. QUILL downloaded the correct portable ZIP, but offered no in-app path to use it. The user had to open the folder, locate the archive, and extract it manually.

The underlying detection was already correct: portable installations received the portable ZIP rather than the Windows installer. The problem came afterward. The completion dialog knew how to act on `.exe` and `.msi` files, but a `.zip` fell through to a bare folder-opening path.

Beta 3 adds an **Extract now** button for portable updates. QUILL extracts the ZIP into a ready-to-run sibling folder and reveals that folder instead of leaving you at the raw archive.

QUILL still does not replace its own running files while open. You must copy your `data` folder and swap the folders yourself, just as with any portable application update. What disappears is the needless archaeology of locating and unpacking the download.

### Pandoc imports can no longer “succeed” with an empty document

A community member reported — and correctly identified the root cause of — a serious import failure. Using **File > Import > EPUB Book** could produce an entirely empty document while QUILL announced success.

Pandoc emits UTF-8. QUILL’s shared subprocess helper had been decoding that output using the operating system’s default locale encoding. On Windows systems whose locale uses a legacy code page rather than UTF-8, decoding could fail and leave QUILL with no text, yet the import path still reported success.

Beta 3 makes two important corrections:

- Subprocess output is always decoded as UTF-8, with a safe fallback so even genuinely non-UTF-8 bytes cannot crash the process or silently blank the result.
- The Pandoc import path now fails loudly when no output is received instead of handing the user an empty page and calling it success.

Because many tools share this subprocess helper, the change strengthens far more than EPUB import. It is a broader reliability improvement across every feature that travels through that path.

### Speech and Dictation opens again

Four testers independently found the same crash. Opening **Tools > Speech > Speech and Dictation** raised a `TypeError` instead of displaying the dialog, whether the Offline or Online tab was involved.

The dialog constructor had gained two required arguments — `kokoro_ok` and `kokoro_can_install` — but its caller had not been updated to supply them. Beta 3 now populates both values using the same availability logic already used for Vosk, and the Speech and Dictation dialog opens normally again.

### The Kokoro installation message now points to the menu that actually exists

While investigating Kokoro, the same tester found that selecting it before its optional component was installed produced outdated directions: “Tools > Speech > Install Kokoro ONNX will fetch it.” That menu item had already moved into **Help > Download Optional Components** in an earlier release.

The message now sends users to the correct place.

### A keystroke can no longer arrive before the editor exists and bring down macOS

On macOS, an extremely early or late keystroke — before the first document tab finished initializing or after the last one closed — could trigger `AttributeError: 'MainFrame' object has no attribute 'editor'` inside the global keyboard hook.

Two neighboring checks already guarded against that lifecycle edge case; one still accessed the editor directly. All three checks are now consistent and defensive.

### On macOS, the letter G is a letter again

One of the most surprising reports in this cycle came from a completely blank document: pressing **G**, uppercase or lowercase, opened Find instead of typing the character. Every other letter behaved normally.

The cause lived in the keyboard-shortcut hint shown at the right side of a menu item. **Find Next** uses **Cmd+G** on macOS. QUILL embeds that visible hint after a literal tab in the menu label, and wxWidgets interprets the text after that tab as a second keyboard shortcut, separate from QUILL’s own shortcut system.

wxWidgets recognizes modifier words such as “Ctrl,” “Alt,” and “Shift,” but not “Cmd.” Rather than rejecting the unsupported hint, it dropped “Cmd,” retained the bare **G**, and registered that single letter as a system-level shortcut for Find Next. The shortcut then intercepted every G before it could reach the editor.

This could affect every macOS-only `Cmd+something` hint, not only Find Next. Beta 3 changes how the hint is built so wxWidgets receives a modifier name it understands, while the visible shortcut continues to read **Cmd+G** exactly as Mac users expect.

### Portable updates now describe the manual swap honestly

After downloading a portable update and restarting, a user reasonably asked why the old version still appeared.

Portable updates have never installed themselves automatically in any QUILL release. The downloaded ZIP has always required a manual replacement step. Previously, that meant choosing **Open folder** and extracting it yourself. With the new **Extract now** button, QUILL performs the extraction, but you still swap the new folder into place.

If QUILL’s wording suggested that the update would apply automatically “on next launch,” the wording was the bug. Beta 3 tightens both this document and the in-app dialog so **swap it into place** is unmistakably described as the manual step it has always been.

### Tree-navigator dialogs no longer expand a root that is intentionally hidden

**Go to Entry in Notebook** and related tree-navigation dialogs could open with a `wxAssertionError`. The underlying correction had already reached the development branch before Beta 2 froze, but it belongs in this record for anyone who encountered the problem on a Beta 2 build.

The dialogs no longer attempt to expand their intentionally hidden root node.

### Narrator becomes a first-class citizen

George Kerscher reported that QUILL’s self-voice spoke at the same time as Narrator, especially in the Command Palette. Beta 3 addresses both the detection problem and the announcement path.

#### Narrator detection now uses the Windows API marker

In addition to its process check, QUILL now reads the marker Windows maintains while Narrator is active: the named `NarratorRunning` system event. This is one inexpensive API call with no process scan.

Narrator can no longer escape detection because of timing, process visibility, or elevation differences.

#### QUILL announcements now travel through Narrator

QUILL now raises announcements as **UI Automation notification events**, the channel Narrator has supported since Windows 10 version 1709.

Status changes, Command Palette narration, and other QUILL feedback can therefore arrive in the user’s own One Core voice, spoken by Narrator itself — just as dedicated bridges deliver announcements through JAWS or NVDA.

If the notification channel is unavailable on a particular system, the message is placed in the status bar. The old failure mode is removed unconditionally: when any screen reader is running, QUILL’s SAPI self-voice is silenced, including announcements previously marked as “forced.” QUILL will no longer talk over the screen reader.

One important caveat remains. The direct Narrator path is verified in code and automated tests, but it still needs real Narrator users to confirm the complete experience. Please test Beta 3 and report through **Help > Report a Bug** whether announcements arrive once, through One Core, and in the expected voice.

### Starter Snippet Packs now behave like an accessible list

In Beta 2, **Install Starter Snippet Packs** required pressing Space on an invisible checkbox that provided no feedback before Enter would work.

The interface is now a standard multi-select list. Arrow to `daily-writing` and press Enter to install it. Hold Shift or Ctrl to select several packs, and your screen reader announces the selected state as you move.

### The Application Status page remembers where you are

A tester supplied precise reproduction steps: open **Help > Status Page**, move down through any list, and watch focus jump back to the first row before you can act.

The page refreshes every two seconds to keep task and download progress current. Each refresh had been rebuilding the lists without preserving the focused row.

Beta 3 keeps focus anchored across refreshes. You can now navigate the lists under **Status**, **Tasks & Downloads**, and **Features** without being pulled back to the top.

### Creating a Notebook on macOS can no longer crash through window activation

Shannon Dyer encountered a hard macOS crash while creating a Notebook: `SystemError: ActivateEvent returned a result with an exception set`.

A window-activation handler collided with a wx assertion while dialogs were being torn down. That handler exists only to return focus to the document, so it is now fully contained. A focus-restoration attempt can no longer take down the entire application.

### Crash and feedback reports now identify the exact beta

Two reports arrived for a bug already corrected in Beta 2, yet they appeared to be regressions because every 0.9.0 beta identified itself only as “0.9.0.”

Reports now include the full version string, such as **0.9.0 Beta 2**, making an older installation immediately recognizable.

If you encounter the Profiles and Features crash involving `_LazyString`, update to the current beta; that issue was already fixed there.

### QUILL no longer offers crash recovery when there is no crash evidence

Two automatic crash-recovery submissions contained only normal background activity until the application stopped. There was no exception, no error, and no actionable trace. That pattern is consistent with an external termination — such as a forced shutdown or killed task — rather than a crash inside QUILL.

Beta 3 turns that observation into a real behavior change. Before showing crash recovery, QUILL now looks for genuine evidence in the log: an `ERROR`, a `CRITICAL`, or a traceback.

An inconclusive exit no longer produces the **“Quill detected an unclean exit”** dialog because there is nothing meaningful to diagnose. A real crash still records an error and offers recovery exactly as before.

The autosave snapshot is never removed or altered by this decision. It remains on disk either way. The only change is whether QUILL asks you to recover after an exit for which the log contains no evidence of a crash.

### Insert > Date and Time's submenu now actually opens

Jayson Smith reported it precisely: open the Insert menu, arrow up to **Date and Time**, press Right Arrow to open the submenu, and land in the **Format** menu instead.

The cause was a startup ordering gap, not a keyboard-handling bug. QUILL builds its menu bar before Quillins finish loading — deliberately, so a slow or misbehaving Quillin can never delay the window appearing or bring the whole launch down. But nothing rebuilt the menu bar afterward, so the bundled `insert-tools` Quillin's three contributions (Insert Date, Insert Time, Insert Date and Time) never actually landed inside the **Date and Time** submenu. The submenu itself was still there — created unconditionally — just permanently empty. With nothing inside to open, Right Arrow had nowhere to go but onward to the next top-level menu.

QUILL now rebuilds the menu bar once Quillin loading finishes at startup, and again after any enable, disable, install, remove, or reload in the Quillins Manager. The **Date and Time** submenu opens correctly now, and so does every other menu location a Quillin contributes to.

### Manage Versions no longer renders as a silent, unexplained blank list

While tracking down the Date and Time submenu fix above, we found a related rough edge already noted in planning as “Snapshots vs Versions”: **File > Notebook > Manage Versions** on a notebook that had never had a Version saved showed a genuinely empty list — no placeholder, no explanation. Tabbing into it told you nothing about whether the feature was working.

The list now shows **“(No versions saved yet)”** and disables Rename and Delete until there is something to act on, matching the “(No open documents in workspace)” pattern QUILL already uses in the Snapshots menu.

### A per-machine install no longer needs administrator elevation to run at full speed

Tyler Rodick installed QUILL system-wide (Program Files, all users) instead of per-user, and noticed something specific: startup was several seconds faster the first time he ran it as administrator than it was running normally afterward.

The cause was a gap in a fix QUILL already had. comtypes — the library behind SAPI speech, Narrator's UIA announcement bridge, and the Rich Edit rich-text object model — writes a generated wrapper file to disk the first time it touches each of those three COM interfaces. Its default location is inside its own package folder, which a per-machine install makes read-only without elevation. QUILL already redirected this cache to a writable per-user folder, but only did the redirecting once, from inside the SAPI code path — Narrator's and Rich Edit's own comtypes calls only inherited that redirect if SAPI happened to run first in the same session. Whichever one ran first without that accident of ordering fell back to comtypes' own read-only default and degraded silently.

Every comtypes call site now requests the redirect itself before touching comtypes, rather than counting on another feature to have already done it. None of the three depends on session ordering anymore, on any install type, with or without administrator elevation.

### Check for Updates could hand a Windows user the macOS download

A release that only publishes assets for one platform — which is exactly what happened when a Beta 3 Windows build failed in CI while the macOS build succeeded — used to fall through to whatever asset *was* published, regardless of platform. A Windows client checking for updates against that release got pointed at the release's only file: a `.dmg`.

Asset selection now excludes every other platform's installer extensions outright, and a release with nothing installable for the running platform is skipped entirely, so Check for Updates falls back to the newest release that actually has a matching build for you rather than ever offering a foreign-platform link.

---

## GitHub Grows from a Viewer into a Workspace

Beta 2 introduced the read-only GitHub Items viewer. Beta 3 begins unifying the best ideas from [GHManage](https://github.com/kellylford/GHManage) — Kelly Ford's open-source, screen-reader-first GitHub browser, QUILL's reference viewer for this entire integration — and fastgh, and moves QUILL toward something much bigger: a keyboard-first GitHub environment where information can be found, understood, and — with explicit consent — acted upon. Every feature below with a GHManage ancestor keeps its idea and extends it with something specific to QUILL.

### GitHub Items gains pins, favorites, real search, automatic repository awareness, and View Upstream

The first group of improvements adds five everyday capabilities:

- **Pinned repositories.** The **Pinned...** button holds a short, intentional list of the repositories you use most. Select one to load it immediately, or pin and unpin the currently loaded repository from the same menu. You no longer need to retype `owner/repo` every time.
- **Favorites.** Press **Ctrl+D** on any selected issue, pull request, branch, or release to bookmark it. **Favorites...** lists bookmarks from every repository and opens the selected item in your browser. These bookmarks remain entirely on your machine.
- **Full GitHub search syntax.** Press **Ctrl+F**, enter a GitHub query such as `label:bug is:open crash` or `author:alice is:pr`, and press Enter. Search is scoped to the loaded repository. Clear the search to restore the normal list.
- **Local git awareness.** When the document you are editing lives inside a git clone whose `origin` points to GitHub, the repository field fills itself in automatically. This works for any file regardless of how it was opened, not only files reached through QUILL’s GitHub commands.
- **View Upstream.** Load a repository that's a fork, and the **View Upstream** button enables itself the moment QUILL confirms it. Press it and the parent repository loads in its place — the only path there before was retyping the parent's name by hand.

### Pull-request differences become something you can understand, not a wall of symbols

Select a pull request and choose **Diff...** to browse its changed files in an accessible list.

QUILL sends each file’s before-and-after content through the same comparison engine used by **Compare Documents**. Instead of forcing you through a dense stream of plus and minus signs, it presents a numbered walk through meaningful changes, such as:

> Difference 2 of 5. Text changed at line 41. main: ... this PR: ...

The changed words are described directly.

- A newly added file is read as its content.
- A deleted file is announced as deleted.
- A binary or oversized file falls back honestly to its available change counts.

### Batch operations are powerful — and deliberately fenced by consent

The GitHub Items list now supports multi-selection. Select several rows, press **Batch...**, and close, reopen, or add a label to all selected items at once.

This is the deliberate exception to the viewer’s read-only foundation, so the boundaries are explicit:

- Batch actions require a signed-in account.
- Anonymous viewing remains fully read-only.
- Before anything changes, the confirmation identifies the exact action and the exact item numbers involved.
- If some items fail, QUILL tells you which ones failed and why, while allowing successful items to complete.

### AI can turn a hundred-comment thread into a useful starting point

A hundred-comment issue late at night is not a humane reading experience.

Press **Summarize** on an issue or pull request and QUILL’s AI creates a brief, plain-prose TL;DR covering:

- What the thread is about
- Where it currently stands
- What remains unresolved
- The apparent next step

The summary appears in the details pane and is announced. It uses the same AI connection, privacy, and consent gates as every other QUILL AI feature. Nothing is transmitted or generated until you choose **Summarize**.

### Compare two branches without leaving the list

Switch the Items viewer to the **Branches** view, select one, and press **Compare...** (or **Ctrl+Shift+B**). Unlike Batch and Actions, this needs no signed-in account — it never writes to GitHub. Type a base branch, then the branch to compare against it (the selected row prefills the second prompt), and QUILL reports how far the two have diverged, lists every commit between them, and walks each changed file's differences the same accessible way **Diff...** does on a pull request.

### Run a workflow straight from the list

A new **Workflows** view sits alongside Workflow Runs — it shows the workflow *definitions* in the repository (the `.yml` files) rather than their run history. Select one and press **Enter**, or use **Actions... > Run ... on Branch...**, and QUILL asks for a branch, confirms, and dispatches the run. This needs a signed-in account; if the workflow doesn't accept manual (`workflow_dispatch`) runs, GitHub's own refusal is reported plainly instead of QUILL guessing.

### Filter what you've already loaded, instantly

**Quick filter** (Ctrl+Shift+F) is a second, different kind of narrowing from Search: it filters the rows already sitting in the list, live as you type, with no network round trip. It never steals keyboard focus away from the box you're typing in, and — since re-announcing "12 items" on every keystroke would fight a screen reader's own character echo — it stays silent while you type and only speaks the result count once you stop. Escape clears it.

Three smaller navigation additions round this out: **Columns...** lets you choose which fields appear as list columns for the current view, and remembers your choice the next time you open the viewer; **Backspace** in the Commits view (reached by pressing Enter on a branch) steps straight back to the branch list; and the repository field now accepts a pasted `github.com` URL or `git@github.com:` remote, not just `owner/repo`.

The viewer and every GitHub feature continue to honor QUILL’s token, consent, and Safe Mode controls. A wiki browser and additional parts of the broader unification review remain on the roadmap; notifications move from roadmap to reality later in this release.

**With thanks.** Every feature in this section traces back to [GHManage](https://github.com/kellylford/GHManage), Kelly Ford's open-source GitHub browser — pinned repositories, favorites, real search, local git awareness, View Upstream, the PR diff viewer, Compare Branches, the Workflows view, and Quick Filter all started as ideas GHManage shipped first. QUILL's job in each case was to extend that idea with something the rest of the app already had to offer — routing differences through QUILL's own compare engine, or keeping Quick Filter quiet enough not to fight a screen reader's character echo — not to reinvent it. This integration would not exist in its current form without GHManage to learn from.

---

## GitHub Stops Being a One-Way Window

Before Beta 3, QUILL could show you a great deal of GitHub while changing very little. You could browse a repository, open a file, save that one file back, list issues and pull requests, and perform limited batch labeling or state changes. Creating repositories, opening and merging pull requests, or deleting obsolete branches still pushed you into the browser.

The planning document at `docs/planning/github.md` examines how far QUILL can go without adding a dependency on the `gh` CLI. Beta 3 ships the part of that plan we can support confidently: repository administration, richer item actions, organization browsing, releases, workflow dispatch, notifications, and security alerts.

### A new Tools > GitHub command center

**Tools > GitHub** is a new submenu containing eight repository commands:

- **Create Repository...** — provide a name and description, choose public or private visibility, and optionally select an organization. After creation, QUILL offers to synchronize a local folder immediately. Say yes and move directly from “no repository” to “a local folder pushing to GitHub” without opening a browser.
- **Fork Repository...** — fork the repository and receive the same offer to create or connect a local synchronized folder.
- **Rename Repository...** — change the repository name from within QUILL.
- **Change Repository Visibility...** — move between public and private visibility with an explicit confirmation.
- **Change Default Branch...** — select the branch GitHub should treat as the default.
- **Delete Branch...** — remove a branch through a guarded workflow.
- **Configure Branch Protection...** — choose a branch, set the number of required approving reviews, specify required status checks, or select an option to clear existing protection.
- **Commit Multiple Files...** — choose several local files and commit them together in one atomic commit. This is intentionally different from **Save to GitHub**, which handles only the currently open document.

### The Items viewer gains an Actions menu

Alongside **Batch...**, the Issues, Pull Requests, Branches, and Commits viewer now includes **Actions...** with commands for:

- **New Issue...**
- **New Pull Request...**
- **Merge Pull Request...** when a pull request is selected
- **Delete Branch...** when a branch is selected
- **Re-run Workflow** when a workflow run is selected
- **View Artifacts...** when a workflow run is selected
- **Reply to Thread...**
- **Edit This Comment...**
- **Delete This Comment...**

The comment actions build on the existing **Alt+N** and **Alt+P** navigation. Move to the relevant comment, then reply to, edit, or delete that specific comment.

### Download a workflow run's build artifacts, without your token leaking to a third party

Choosing **View Artifacts...** on a workflow run opens a small list of that run's build artifacts — name, size, and whether GitHub has already let it expire. From there:

- **Download Selected...** or **Download All...** ask for a destination folder, then save each artifact as a zip file.
- If a file of that name already exists, QUILL asks before overwriting it.
- A progress dialog with **Cancel** tracks the download; you can stop it at any point.
- **Open Run in Browser** takes you straight to the run on GitHub.

The download itself needed a deliberate design decision, not a default one. GitHub's artifact download link redirects to a short-lived, signed URL hosted elsewhere (Azure Blob Storage in production) — and your GitHub token must never travel to that second host. Standard redirect-following would send it there anyway, and reaching into PyGithub's private internals to work around that felt like the wrong kind of shortcut. QUILL instead follows the redirect itself: it blocks the automatic follow, reads the redirect target, and makes exactly one more request to that address with no `Authorization` header attached. Your token only ever goes to `github.com`.

### Signed-in actions remain signed-in actions

None of the write commands operates anonymously. Each requires an authenticated account. When you are not signed in, QUILL offers to begin sign-in from the point of need instead of simply refusing and leaving you to find another route.

Four high-consequence actions require stronger confirmation than an ordinary Yes/No prompt:

- Renaming a repository
- Changing repository visibility
- Deleting a branch
- Merging a pull request

For those operations, you must retype the exact repository name, branch name, or pull-request number. These are the actions for which an accidental Enter can be particularly difficult to reverse.

Every other write action uses a clear confirmation that names precisely what is about to change.

All thirteen GitHub commands — the eight new administration commands plus the five browsing commands present since QUILL 0.5.0 — now appear in the Command Palette and ship with default QUILL Key chords. Every chord can be reassigned in Preferences.

### Organizations, releases, workflows, notifications, and security alerts

Five additional commands complete the read-mostly side of the plan:

- **Browse Organization Repositories...** — choose from the organizations associated with your account and then browse that organization’s repositories. Teams remain intentionally out of scope.
- **Create Release...** — choose a tag, supply optional release notes or use GitHub’s automatically generated notes from merged pull requests, and create the release as a draft or publish it.
- **Dispatch Workflow...** — run a workflow against a branch or tag, equivalent to choosing **Run workflow** on GitHub’s website.
- **Notifications...** — open a genuine inbox spanning all repositories rather than only the repository currently loaded.
- **Security Alerts...** — review a repository’s open Dependabot alerts.

### Codespaces and Copilot CLI — needs your help to confirm it actually works

Four more Tools > GitHub commands round out this release's GitHub work, and they work a little differently from everything above: instead of talking to GitHub's API directly, they run your own installed `gh` command-line tool.

**Codespaces...** lists your active Codespaces — name, repository, current state — and lets you Stop or Delete one from a menu. **Create Codespace...** asks for a repository and an optional branch and creates a new one. This is the one command in QUILL's entire GitHub integration that carries a real cost: Codespaces consume GitHub compute and storage minutes, and the confirmation dialog says exactly that before anything happens, rather than the general "this changes something on GitHub" wording every other GitHub command uses.

**Ask Copilot for a Command...** and **Explain a Command...** are small but genuinely useful: describe what you're trying to do in plain language and get a suggested git or `gh` command back, or paste in a command you don't recognize and get a plain-language explanation of what it does.

We are asking for your help here specifically. These four commands are thoroughly unit-tested against a simulated `gh` tool — the argument-building and response-parsing logic is solid — but none of it has been exercised against a real Codespaces-enabled repository or real Copilot CLI access on an actual device. If you use Codespaces or Copilot CLI, please try these commands and tell us what happened through **Help > Report a Bug**, good or bad.

**Don't have `git` or `gh` installed?** Both are now available right from **Help > Download Optional Components** — a portable copy of Git for Windows, and the GitHub CLI for Windows and macOS, each checksum-verified the same way every other optional download is. QUILL always prefers a copy you already have on your system first; these exist purely so Tools > Local Git and these four Codespaces/Copilot commands work for someone who has never installed either.

### What is not included — because confidence matters more than pretending

Before implementing these commands, we checked the actual boundaries of PyGithub instead of assuming that every GitHub capability had a stable wrapper.

Several ideas from the original plan remain out for concrete reasons:

- **Discussions** has a PyGithub entry point, but it requires a hand-written GraphQL field-selection string. Shipping that without live repository validation would mean shipping a guess.
- **Projects (v2)** has no PyGithub support. The library supports only the classic Projects API that GitHub has been sunsetting, so building against it would produce a feature that fails on many modern repositories.
- **Packages** has no PyGithub support.
- **Transferring a repository to another owner** also lacks a wrapped method. This was initially described as renaming in the plan, but transfer is the actual operation.

Discussions, Projects v2, Packages, and repository transfer remain legitimate future candidates when they can be implemented and verified responsibly.

---

## Local Git, Reimagined for Screen Reader Users

This section is not about GitHub. It is about `git` itself — and it may be the capability in Beta 3 of which we are proudest.

Traditional git tools expose complex operations as punctuation-heavy text and visually arranged changes. QUILL starts from a different question: what would these workflows look like if structure, sequence, context, and choice were communicated directly?

### Merge conflicts become a guided conversation

Anyone who has worked with git has eventually encountered conflict markers:

```text
<<<<<<<
=======
>>>>>>>
```

A screen reader encounters those markers as line noise unless the user manually reconstructs the surrounding structure. The git CLI, GitHub Desktop, and most graphical merge tools were not designed around that experience. None of them is also the trusted editor in which a screen reader user already writes.

QUILL is.

Open **Tools > Local Git > Resolve Conflicts...** and QUILL parses each conflicted file into meaningful parts. It then walks through the conflicts one at a time, announcing language such as:

> Conflict 1 of 3: your version says X; their version says Y.

For each conflict, choose to:

- Keep yours
- Keep theirs
- Keep both
- Enter a different replacement

The process continues through every conflict in every affected file, preserving structure and making the decision explicit.

### Interactive rebase becomes an accessible list instead of editable syntax

`git rebase -i` normally opens a generated text file and expects you to reorder commits and change commands such as `pick`, `squash`, `reword`, or `drop` without damaging the syntax.

**Interactive Rebase...** replaces that fragile visual editing task with a real dialog:

- One commit appears on each row.
- Each row has an action selected from a dropdown.
- **Move Up** and **Move Down** reorder commits directly.

Under the hood, QUILL uses the same mechanism employed by graphical git clients: git can send its generated todo list to any program named as the sequence editor. QUILL becomes that program and returns the structured list built in the accessible dialog.

If a rebase step causes a conflict, the same guided conflict resolver opens automatically. Resolve the conflict, and QUILL continues the rebase.

### The rest of the local git toolkit

The new local git experience also includes:

- **Uncommitted Changes...** — stage or unstage work through an accessible comparison rather than a raw diff.
- **Switch Branch...** — change branches with a guard that prevents uncommitted work from following you unexpectedly.
- **Stash Changes...** and **Manage Stashes...** — create and manage stashes through guided interfaces.
- **Who Wrote This Line...** — make git blame useful by speaking the result for the current line.
- **Start Bisect...** and **End Bisect** — turn `git bisect` into a plain conversation asking whether the current version is good or bad.

These commands do not contact GitHub or any network service. They operate entirely through local git and work with any repository you point QUILL toward.

We tested them against real repositories performing real operations: divergent branches producing a real merge conflict, and an interactive rebase that encountered a conflict partway through and then had to continue. Subprocess orchestration earns trust by surviving the actual workflow, not by looking correct on paper.

Everything across these three GitHub chapters — browsing and saving files, working issues and pull requests, administering a repository, and resolving a merge conflict — is also taught end to end in [Tutorial 8: GitHub inside QUILL](../tutorials/08-github-inside-quill.md).

---

## Headers and Footers Become Part of the Document

Beta 2’s Header/Footer Builder could apply headers and footers during printing, but the saved files themselves did not contain them.

Beta 3 carries them into the document:

- Save as `.docx` and the header or footer becomes a real Word header or footer.
- Page numbers use a live Word field, so Word continues renumbering them as the document changes.
- Save as `.rtf` and QUILL writes the equivalent native RTF header and footer groups.
- Roman numeral numbering carries through.
- A custom starting page number carries through.
- A different first page carries through.

An empty header/footer specification changes nothing, and a header can never become the reason a save fails.

---

## QUILL Sync: Let Trusted Tools Carry the Work

We explored what it would mean to build a complete QUILL synchronization service: QUILL accounts, QUILL-hosted storage, a custom synchronization engine, and the operational burden that comes with all of it.

We chose not to build a new cloud merely because we could.

Cloud-synchronized folders and git already solve the essential problems well. Beta 3 lets QUILL work with those systems instead of competing with them. Two focused capabilities deliver practical synchronization without making QUILL a storage provider.

### Synchronize settings through a folder you already trust

The existing **“Where should QUILL store your data?”** option was originally created so users could move their application data away from the system drive. It also serves as a straightforward settings synchronization mechanism.

Point QUILL’s data location to a folder already synchronized by OneDrive, Dropbox, Google Drive, or iCloud. Your settings, snippets, dictionaries, and keymap then travel with that folder across devices. QUILL writes normal files; the provider’s sync client handles transport.

The setup wizard now explains this use clearly and names the important limitation: do not run QUILL simultaneously on two devices that share the same synchronized data folder. This path has no cross-device conflict-resolution system.

### Synchronize any folder with GitHub

**Tools > Sync Folder with GitHub...** works with any folder: notes, a writing project, source code, or an entire body of work.

When the selected folder is already a git repository with a remote, QUILL commits, pulls, and pushes it in the background.

When the folder is not yet configured, QUILL explains exactly what it proposes to do:

> This runs `git init`, then adds the remote repository you provide as `origin`.

Nothing changes until you approve. Provide the repository URL and the folder becomes synchronized.

If the same file changed in both locations, QUILL lists the conflicts by name and stops. It never resolves the situation through a silent overwrite.

The engine is familiar because it is the same foundation used by Accessible Vault’s **Sync Vault** command, generalized from vaults to any folder.

QUILL relies on your installed git and the credentials git already knows — an SSH key or the account stored in your system’s git credential manager. It does not create or store a second set of credentials. The behavior mirrors a normal `git push` from the terminal.

Like every network-touching feature, folder synchronization is disabled in Safe Mode.

The reasoning behind this approach, including the larger synchronization design that was considered and rejected, is preserved in `docs/engineering/sync-engine-history.md`.

---

## Small Features, Enormous Everyday Impact

Some features change an architecture. Others remove one interruption, one unnecessary dialog, one repeated search, or one inaccessible ritual from a person’s day. Beta 3 makes room for both.

These accessibility-first additions came from real workflows and direct requests. They are small enough to feel natural and powerful enough to become habits.

### The Clipboard Collector now reaches beyond QUILL

Dean Martineau asked for the behavior familiar from EdSharp: turn on the collector, copy from anywhere, and let every captured item flow into the active document.

That is now exactly what happens.

While **Toggle Clipboard Collector** is enabled, QUILL watches the system clipboard. Copy text from a browser, an email, a terminal, or another application and QUILL appends it to the open document, saving as it goes.

The implementation is intentionally light. QUILL performs one inexpensive check roughly once per second and touches the clipboard only when its contents have actually changed. Copies made within QUILL still arrive immediately, and each distinct clipboard item is collected exactly once.

### QUILL can become Thunderbird’s external editor

Martin Courcelles asked to write email in QUILL. The happy discovery is that the underlying behavior already works.

QUILL’s one-process-per-file model matches what Thunderbird’s **External Editor Revived** add-on expects. The user guide now includes a complete **Using QUILL as an external editor** walkthrough:

1. Install the Thunderbird add-on.
2. Point it to `quill.exe`.
3. Press **Ctrl+E** in a Thunderbird compose window.
4. Write using the full QUILL editing environment.
5. Save and close the QUILL document.
6. The text returns to the Thunderbird message.

### The Windows installer can add QUILL to PATH

The installer now includes an optional **Add Quill to PATH** task. It is unchecked by default and appears beside the existing file-association choices.

Enable it and the command `quill` resolves from any terminal or from a shortcut’s **Target** field without requiring the complete installation path.

The change is per-user only. It requires no elevation and affects no other Windows account.

Already installed Beta 2 or an earlier build? Run the installer again and select the task to add it retroactively.

### A temporary bookmark for “right here, right now”

Sometimes you do not need a named landmark, a list, or a persistent record. You simply need to mark this exact place and return a few moments later.

- **Ctrl+Shift+K** sets one unnamed bookmark at the cursor. There is no dialog. QUILL announces: “Temporary bookmark set.”
- **Alt+Shift+K** returns to it immediately. There is no picker. QUILL announces: “Jumped to temporary bookmark.”

Setting another temporary bookmark replaces the previous one without prompting. Only one exists at a time.

It does **not** persist across sessions. Closing and reopening QUILL clears it. That is deliberate: this is disposable working memory for the next few minutes, not a replacement for the existing unlimited, persistent **Set Bookmark...**, **Go To Bookmark...**, and **List Bookmarks...** commands.

### Ten numbered quick bookmarks, each one keystroke away

Beta 3 also adds ten fixed bookmark slots numbered 0 through 9.

- **Alt+Shift+0** through **Alt+Shift+9** sets the corresponding slot at the cursor. For example: “Quick bookmark 3 set.”
- **Ctrl+Alt+Shift+0** through **Ctrl+Alt+Shift+9** jumps directly to that slot. QUILL announces “Jumped to quick bookmark 3,” or “Quick bookmark 3 is not set” when the slot is empty.

These are direct chords. There is no menu to open and no bookmark mode to enter first.

Internally, the slots are stored as normal named bookmarks with generated names such as **Quick 3**. That means they persist per document across restarts just like existing named bookmarks. There is nothing new to configure and no separate storage system to maintain.

### Alt+F7 checks only the word under the cursor

Press **Alt+F7** to run **Spell Check Word** on the current word.

When the word is correct, QUILL says so and returns you immediately to your work.

When the word is misspelled, a compact list opens with the same choices available from the right-click spelling menu:

- Suggested replacements
- **Add to Dictionary**
- **Ignore**

Arrow to an option and press Enter, or press Escape to cancel without changing anything.

This is the focused-word spelling workflow familiar from Microsoft Office. Use **F7** for a systematic review of the full document. Use **Alt+F7** when you need an answer about the one word at the cursor.

### Ranked spelling puts the most repeated problem first

Press **Ctrl+Shift+L** to open a misspelling list ranked by frequency.

The existing **Misspelling List** on **Alt+Shift+L** remains unchanged and continues to present words in document order. The new ranked view begins with the misspelling that occurs most often and shows the count in each entry, for example:

> teh (Ln 12, Col 4, 8 occurrences)

This Kurzweil 1000-inspired feature came directly from a longtime user. In an OCR document or a draft containing a repeated typo, correcting the most frequent problem first can eliminate a large portion of the noise immediately.

Arrow through the list and press Enter to jump to an occurrence, exactly as in the regular misspelling list. Users who prefer reviewing from the beginning of the document can continue using **Alt+Shift+L**.

### Ranked Spelling Review brings the full F7 workflow into frequency order

**Alt+Shift+F7** opens the complete guided Spelling Review, but orders issues from most frequent to least frequent.

It includes every action available in the normal F7 dialog:

- **Change**
- **Change All**
- **Ignore Once**
- **Ignore All**
- **Add to Dictionary**
- **Undo Last**

This is designed for difficult documents: rough OCR, systematic autocorrect failures, and files containing the same few errors dozens of times.

Choose **Change All** on the first item and the ranking recalculates immediately. The most frequent remaining issue rises to the top, allowing you to keep clearing the largest groups of errors first.

**F7** and **Alt+Shift+F7** use the same dialog and the same actions. Only the presentation order changes: document order for F7, frequency order for Alt+Shift+F7.

### Favorite folders remember what matters, not merely what was recent

Windows recent folders answer one question: what did you open lately?

Favorite folders answer a different and often more useful one: what must always be easy to reach?

A folder holding a document your supervisor might request at any moment may deserve permanent prominence even if you have not opened it in months. Beta 3 adds a short, curated favorites list modeled on a valued Kurzweil 1000 workflow.

- **Ctrl+Alt+Shift+A — Add Favorite Folder.** Adds the folder containing the current document. An untitled document must be saved first because QUILL needs a real folder path.
- **Ctrl+Alt+Shift+R — Remove Favorite Folder...** Opens the favorites list and lets you choose one to remove.
- **Ctrl+Alt+Shift+O — Open From Favorite Folder...** Opens the new Quick Open experience scoped to your favorite folders.

All three commands also appear under **File > Favorite Folders** for users who prefer menu navigation.

### Quick Open searches across favorite folders as you type

Press **Ctrl+Alt+Shift+O** and a compact dialog opens with focus already in the search box.

Begin typing any part of a filename. The results below filter live and case-insensitively across every favorite folder, following the same type-to-filter rhythm as **Ctrl+P** in Visual Studio Code.

Each result identifies the favorite folder it came from, which matters when multiple folders contain similarly named files. Arrow to a result and press Enter, or choose **OK**, to open it. Press Escape or **Cancel** to leave everything unchanged.

By default, the search includes only files at the top level of each favorite folder. It does not recurse into subfolders. That keeps results immediate even when a favorite contains a large nested tree and reinforces the intentionally curated nature of the feature.

Enable **Include subfolders** when a deeper search is needed. Recursive results are capped at a few thousand files so a very large favorite cannot freeze the dialog.

QUILL does not impose a single project-root or workspace model like Visual Studio Code, so Quick Open deliberately searches the user’s chosen favorites rather than attempting to scan the entire computer.

### Accessible code folding reduces clutter without hiding content from you

QUILL can now fold heading sections and fenced code blocks — the ```` ``` ```` through ```` ``` ```` structure used in Markdown and embedded code — while preserving complete access to every word.

The commands are:

- **Ctrl+Alt+Shift+F — Toggle Fold.** Folds or unfolds the smallest foldable region containing the cursor. QUILL announces exactly what happened, such as “Folded: 14 lines under ‘Chapter Two’” or “Unfolded: ‘Chapter Two.’”
- **Alt+Shift+] — Next Fold.** Moves to the next foldable boundary, whether expanded or folded, and announces the label, state, and line count: “‘Chapter Three,’ expanded, 22 lines.”
- **Alt+Shift+[ — Previous Fold.** Performs the same navigation in reverse.
- **Ctrl+Alt+Shift+L — List Folds...** Opens a complete list of foldable regions, each with its current state and line count. Select one to jump to it directly.

The accessibility design is intentionally different from folding in most editors.

Mainstream folding generally hides lines visually and makes ordinary arrow navigation skip silently over the collapsed content. A screen reader user may have no reliable way to know whether text was removed, folded, or simply bypassed.

QUILL never creates that uncertainty.

**The document text is never changed, and normal character, word, and line navigation is never intercepted.** Fold state exists for the four folding commands to describe and use. Arrow through a folded region normally and every word remains available exactly as though the region were expanded.

Folding changes the behavior of fold-specific jump commands. It never makes reachable content silently unreachable.

### Insert Emoji — 3,781 emoji, findable by ear, described in words

QUILL already has Insert Special Character for the case where you know exactly which Unicode code point you want. Emoji are the opposite problem: you don't know the code point, you might not even remember the exact name, and you cannot see a picture grid to recognize one by eye. Every mainstream emoji picker is built around that grid — rows of small pictures meant to be scanned visually — which makes the entire category of feature effectively unusable without sight. Insert Emoji is built the other way around, from the ground up, for browsing and finding by ear.

**Insert > Insert Emoji... (Alt+Period)** opens on every complete, standard emoji Unicode currently defines — 3,781 of them, current as of Unicode's 16.0 emoji release — organized into the same nine categories Unicode itself uses:

| Category | Emoji |
| --- | --- |
| People & Body | 2,261 |
| Flags | 270 |
| Objects | 264 |
| Symbols | 224 |
| Travel & Places | 218 |
| Smileys & Emotion | 169 |
| Animals & Nature | 159 |
| Food & Drink | 131 |
| Activities | 85 |

*(“People & Body” includes every skin-tone and gesture variant Unicode defines as its own standalone emoji, which is why it dwarfs the others.)*

The dialog is two ways into the same list. **Search**, at the top, live-filters as you type and matches in order of confidence: the emoji symbol itself, if you paste or type one in; a legacy typed alias like `:)`, `:D`, or `<3`, for the smiley shorthand habit many people already have; a match against the emoji's official Unicode name or one of its keywords; and, as a last resort, a match inside the emoji's own written description — so a half-remembered phrase like “melting” or “puddle” can still surface the right result even when that word never appears in the emoji's official name or keyword list. **Category**, a list on the left, is the browse path: pick a category and its emoji fill the results list, for exploring rather than searching.

Whichever way you got there, arrowing through the results list updates a live **description pane** with everything QUILL knows about the selected emoji: category and subgroup, official name, keywords, any legacy typed alias, and — the piece that makes this genuinely usable without sight — a real, original one-to-two-sentence description of what the emoji actually looks like: colors, shape, expression, pose. Press **Insert**, or press Enter directly on a result, and it lands at your cursor; **Cancel** or Escape backs out with nothing inserted.

Two more entries sit at the very top of the category list, ahead of Unicode's nine groupings: **Favorites** and **Recent**. Select any emoji and press **Add to Favorites** to star it for one-step access from then on — the button relabels to **Remove from Favorites** once it is, and works from any view, search results included. **Recent** fills itself in automatically: the last 30 emoji you've actually inserted, most-recently-used first, so the ones you reach for constantly never need a search or a category dig again. Removing something from Favorites, or clearing out Recent, only changes what shows up in those two shortcuts — the emoji itself is never touched and is still exactly as findable under its normal category or by search as it always was.

Every one of those 3,781 descriptions is text QUILL generated itself, purpose-built for this feature — from Unicode's own official names, categories, and keywords, through an AI model, in QUILL's own words — rather than copied or scraped from another picker's site, which would have carried real licensing risk. The whole catalog, descriptions included, ships as a single bundled file built entirely offline ahead of time; using the picker itself makes no network connection at all, in Safe Mode or anywhere else.

### Internet Radio — listen in the background while you write

**Tools > Media > Internet Radio** brings live internet radio into QUILL itself, built to keep playing quietly in the background while you keep typing, not to pull focus away from your document.

**Browse Stations...** searches [RadioBrowser](https://api.radio-browser.info), a free, keyless, community-run directory of internet radio streams — no account, no advertising, and no commercial API terms to depend on or lose access to later. A search box takes a station name, and two optional fields narrow it further by tag/genre or by country. Alongside search sits a category list with two entries that need no network call at all to see: **Favorites**, your own saved stations, and **ACB Media**, the American Council of the Blind's ten Live365 stations, bundled directly into QUILL because the mission overlap is direct and immediate access matters. Whatever station you've selected, a read-only details pane reports everything QUILL knows about it — country, language, tags, codec and bitrate, community vote count, homepage, and the stream URL itself — so you know what you're about to listen to before you press Play.

Not every station worth listening to is in RadioBrowser's directory. **Add Custom Station...** takes any stream link directly — name, URL, an optional homepage and tags — with a **Test** button that plays it right there in the dialog before you commit to saving it. And when all you have is a station's own website, **Find Streams from a Website...** takes the address you type, fetches that one page, and lists every stream-shaped link it finds (an `<audio>` tag, a `.pls`/`.m3u` playlist link, a URL that looks like a Shoutcast or Icecast mount point) with a plain-language reason for each — Test to preview, then **Use This Link...** to carry the guessed name and stream URL straight into Add Custom Station. This deliberately fetches and reads one page rather than opening a full interactive browser inside QUILL: station pages almost always list their stream as a plain link, and a screen-reader-native results list beats navigating an embedded browser for this particular job.

Every one of these dialogs shares the same single player, which is what makes "listen while you keep writing" work at all: closing the station browser, the custom-station dialog, or the link finder never stops the music, because playback lives independently of any of them. Once something is playing, a **Radio** cell appears on the status bar showing the station and state — click it, or press Enter on it, to play or pause; right-click (or open its context menu from the keyboard) for Stop, Mute, a **Favorite Stations** quick-switch, and a shortcut back into the full browser. Minimize QUILL to the system tray and the same controls follow you there, in the tray icon's right-click menu, alongside a live Now Playing line. And you never have to leave the editor to reach for any of it: **Ctrl+Shift+Grave**, then **N**, toggles play/pause; then **0** stops; then **9** mutes — all fully remappable, like every other QUILL Key chord.

Radio volume is QUILL's own — a slider right in the station browser, separate entirely from your Windows system volume and separate from your screen reader's own speech volume, so you can set the music quietly under your speech without touching either of those.

Two things worth naming plainly. First, `docs/planning/radio.md` compares QUILL's approach against FastPlay and ACB Link, the two existing accessible radio players this feature learned from, and explains a deliberate scope decision: TuneIn and iHeartRadio (both undocumented, reverse-engineered commercial APIs with no public terms) and YouTube audio are not in QUILL and are not planned — RadioBrowser alone covers the real need without that risk. Second, stream recording and scheduled recording are real, planned next steps, tracked in that same planning document, not something this beta silently promises and doesn't deliver. Podcasts, described next, ship in this same release.

---

### Podcasts — subscribe, organize, download, and never lose your place

**Tools > Media > Podcasts...** is QUILL's own podcast client: subscribe to shows, organize them into folders, download episodes for offline listening, and pick up exactly where you left off — all without ever pulling focus away from your writing any more than Internet Radio does, and sharing that feature's central design idea of one player that outlives any dialog you close.

**Finding and adding shows.** The Podcasts dialog's **Add Podcast...** button opens a search box against Apple's free, keyless iTunes Search directory — the same starting point most podcast apps use — with a results list and a **Subscribe to Selected** button. If a show isn't in that directory, or you already know its feed address, **Add by Feed URL** takes it directly. And if you're moving from another podcast app, **Import OPML...** reads that app's whole subscription list in one step, folder structure included, so switching to QUILL doesn't mean re-subscribing to everything by hand; **Export OPML...** writes the same structure back out, so you're never locked in.

**Organizing your library.** Shows live in a folder tree on the left of the Podcasts dialog — genuinely nested, as deep as you like — with an episode list on the right for whatever show or folder is selected, the same tree-and-list shape Radio's own dialogs already established. **New Folder...** creates a folder (nested under whatever's currently selected), and a show's context menu can pause it — keeping it, its episodes, and any downloads fully in your library while it stops fetching or downloading anything new, for a show you want to keep without actively following right now.

**Downloads, and two pause controls that mean different things.** Every download runs on its own dedicated background thread, separate from QUILL's shared task pool, so a big backlog of episodes never slows down AI calls, transcription, or anything else running in the background. Pausing downloads is two genuinely independent controls, not one setting doing double duty: **Pause All Downloads** (from the tray, the status bar, or the Podcasts dialog) stops the queue from *starting* anything new, while whatever's already mid-transfer keeps running to completion; pausing one specific episode halts that transfer immediately, wherever it is, and resuming it later continues from the exact byte it left off via an HTTP Range request rather than starting over. Retention — what happens to a downloaded file over time — is a setting per podcast (or a global default): keep every episode forever, keep only the most recent few, or delete a file automatically the moment you finish listening to it.

**Playback that behaves like Radio's.** The Podcasts dialog drives the same kind of single, app-owned player Radio uses: closing the dialog never stops an episode that's playing, and starting a different episode always replaces whatever was playing rather than layering two streams — QUILL never plays two things at once. Your position within an episode is saved automatically, so returning to a podcast — even much later — resumes exactly where you stopped, and that position is stored the same way QUILL Sync already carries your settings between machines, so the sync story here is "already works" rather than "planned." A **Speed** control in the dialog sets playback rate per podcast from 0.75x to 2.0x, remembered the next time you open that show — read faster through a familiar host's cadence, or slow down a dense interview, independently per show.

**Rich context menus, everywhere you'd expect one.** Right-click (or open the context menu from the keyboard) on an episode for Play/Pause, Stop, Download, Pause/Resume Download, Remove Downloaded Copy, Mark as Played/Unplayed, and Copy Episode Link — every action reachable without leaving the list. Right-click a show in the folder tree for Refresh Feed, Pause/Resume This Podcast's Downloads, and Unsubscribe; right-click a folder for New Folder. Unsubscribing also works with the plain Delete key on a selected show — downloaded files are kept on disk unless you separately remove them.

**Everywhere Radio already lives, Podcasts lives too.** A **Podcasts** status bar cell appears the first time you play something, mirroring Radio's cell exactly: click or press Enter to play/pause, open its context menu for Stop and Pause/Resume All Downloads. The system tray's right-click menu gets the same controls for when QUILL is minimized. **Ctrl+Shift+Grave**, then **8**, toggles play/pause; then **7** stops — both remappable QUILL Key chords, and deliberately adjacent to Radio's own N/0/9 chords rather than colliding with them.

No video podcasts, ever — audio only, matching every other playback surface in QUILL. This release is Phase 1 of the plan in `docs/planning/podcasts.md`: chapter navigation and transcript viewing/export (the feed already parses Podcasting 2.0 chapter and transcript URLs as forward schema for this), a separate Inbox view, a cross-show Play Queue, local (imported-file) podcasts, and rich sorting/filtering are the real, planned next phases — tracked in that same document, not silently promised here.

---

## Introducing the Offline Edition, and Real Polish for the AI Setup Wizard and Audio Studio

### A build for machines with no internet at all

QUILL normally keeps its everyday installer small by downloading its bigger optional pieces — Pandoc, offline speech engines, neural voices, the braille pack, and more — only when you actually reach for them.

The new **Offline Edition** build inverts that: every optional component ships inside the installer and the portable bundle up front. QUILL is fully functional the moment it's installed, with no internet connection ever needed. That makes it the right choice for an air-gapped machine, a locked-down work laptop, or anywhere your first login can't reach the internet.

**Help > Download Optional Components** reflects the difference honestly: under the Offline Edition, each component shows as already **Bundled** — or, for the handful the offline build doesn't carry, **Not included** — instead of offering a Download button that has nothing left to fetch. The regular, smaller installer and portable download are unchanged and remain the default for everyone else.

The section right after this one covers a real gap a community member found in the Offline Edition's first pass, and how it was closed.

### The AI Setup Wizard treats Ollama fairly

A never-configured install's saved settings default to provider "Ollama" — a reasonable default, but the wizard's "remember what you already set up" logic mistook that default for proof you'd deliberately added Ollama. The result: on first run, the wizard silently marked Ollama as already configured, quietly dropped it from the Provider list, and left only key-requiring cloud providers to choose from — even on a machine where Ollama had never been touched.

The wizard now confirms a local Ollama server actually answers before treating it as configured. A related, simpler bug in the AI Hub's Provider tab is fixed alongside it: the API key field stayed active for every provider regardless of whether one was actually needed, making Ollama's key field look required when nothing ever enforced it. It now greys out correctly for Ollama and any other no-key provider.

Two smaller Setup Wizard rough edges are fixed in the same pass. Reaching the Connect step (or removing a provider from the Added list) could land focus straight in an API key field instead of the Provider list — jarring, and easy to misread as "Ollama needs a key too." Focus now always starts on the Provider list itself. The Remove button also used to look clickable the instant anything was added, whether or not you'd actually selected an entry; it now stays disabled until a real selection exists.

### Ollama, wherever it actually runs — and pull a model without a terminal

The Setup Wizard always assumed Ollama lived at `localhost`, even though reaching an Ollama server on another machine on your network was never actually wired up end to end. A new **Ollama server address** field on the Connect step — shown only when Ollama is selected, defaulting to localhost — now genuinely drives the verify, model-list, and Finish steps, so a LAN or self-hosted Ollama is a real, working choice.

Choosing your default model used to mean opening a terminal and typing `ollama pull <model>` yourself. The Model step now shows which recommended models are already installed and offers a **Pull model** button on the rest, with live download progress, selecting the model for you the moment it's ready.

### Preferences lands you on the right control when you switch tabs

Using Ctrl+Tab or Ctrl+Shift+Tab to move between Preferences tabs — or clicking a different one — moved the visible page but left keyboard focus wherever it had been, so a screen reader sometimes announced just "Panel" instead of the new tab's first real field. Switching tabs now always moves focus to that tab's first control, matching the routing every other tabbed dialog in QUILL already uses.

### Audio Studio gets a working Cancel button, an honest log, and a tidier WAV output

Generating audio for a whole folder of documents had no Cancel button at all, and pressing Escape just dinged — there was no way to stop a run short of quitting QUILL outright. Cancel (and Escape) now work properly: whatever file is currently synthesizing finishes normally, so you never end up with a half-written audio file, and the run stops cleanly before starting the next one.

The diagnostics log used to record only which document was up next, not the chunk-by-chunk progress the on-screen dialog already showed — so glancing at the log during (or after) a run told you far less than watching the screen did. The log now mirrors that same chunk-by-chunk detail.

Choosing WAV as your export format used to drop the file right next to your source document, the same place MP3 already lands — awkward for a format that tends to produce large files. WAV output now goes into an **Audio Output** subfolder beside the document it came from; exporting recursively through nested folders gives each subfolder its own Audio Output folder rather than funneling everything into one shared location at the top.

### QUILL warns before Alt+F4 abandons real work in progress

Closing QUILL while an Audio Studio export was running used to exit immediately, mid-job, with no warning at all. QUILL now asks first — close and stop the job now, or leave QUILL open so it can finish — and mentions **File > Send to Tray** as a way to keep it running quietly in the background instead. Routine background activity (search and replace, dictation, downloads) is unaffected; only genuinely hard-to-redo jobs like an Audio Studio export trigger the warning.

---

## The Offline Edition Is Finally True to Its Name

A community member installed the Offline Edition and discovered that Kokoro neural voices still requested an internet connection on first use — inside a build whose defining promise is that the internet should not be required.

That report did not become a one-line patch. It triggered an audit of every optional speech component QUILL offers. Beta 3 closes every gap found in that audit except one clearly documented remaining limitation.

### What “Offline Edition” is supposed to mean

The Offline Edition should be self-contained: the components a user can reasonably expect to use are already on the computer, and normal operation requires no internet connection after installation.

Kokoro’s voice model files were already included. The missing piece was the software engine that reads those models. Kokoro’s underlying package and several supporting libraries were still being installed the first time the voice was selected.

On a truly offline computer, the model was present but unusable because the engine tried to cross a network connection that did not exist.

### Kokoro now installs and speaks entirely from local files

The Offline Edition now contains everything required to install Kokoro neural voices. No connection is needed during first use or any later use.

### whisper.cpp now includes its starter model

QUILL’s default speech-to-text engine, **whisper.cpp**, now ships with its starter model already present.

This was the most important gap in the audit. whisper.cpp is not merely an optional engine a user might choose later; it is the transcription path QUILL reaches for automatically. An Offline Edition unable to transcribe until it downloaded a model was not genuinely offline. That contradiction is now resolved.

### Faster Whisper, Vosk, and MP3 chapter markers are locally complete

Three smaller optional components receive the same treatment:

- **Faster Whisper**
- **Vosk**
- **MP3 chapter-marker support**

Choose any of them in the Offline Edition and installation completes without a network connection.

Vosk also becomes more reliable in the process. It depended on one supporting library that previously came only from the internet even when the verified Vosk package itself was available locally. That final external dependency is now bundled.

A second, more fundamental Vosk problem surfaced during this beta's own build process: Vosk also lists a subtitle-file helper library as a dependency that QUILL never actually uses, and that library has never published a ready-to-install package — only its source code. Because the Offline Edition build only ever installs verified, ready-to-install packages (never source code that would need to be compiled), it rejected that one unused dependency every time, which meant the Offline Edition installer could not be built at all until this was found and fixed. It now fetches exactly what Vosk actually needs and skips the one piece it doesn't.

### Piper arrives with an engine and a ready-to-speak voice

Piper is now fully prepared for offline use as well.

The Offline Edition bundles:

- Piper’s engine
- Integrity verification against the same pinned fingerprint at build time and again during installation
- A ready-to-use starter voice: **Lessac, US English, medium quality**

Select Piper after an Offline Edition installation and it speaks without contacting the network. Additional voices remain available from the online catalog whenever a connection is available and the user chooses to download them.

### The one remaining offline gap

**Node.js-based Quillins** still require an internet connection the first time they are used, even in the Offline Edition.

This is a known and tracked limitation, not an overlooked dependency. It remains on the list for future work.

---

## Built by the Community, Not Merely Released to It

Every fix in Beta 3 traces to a specific community report. Nine reports, spanning issues **#939 through #953**, are now closed with an explanation of what was discovered and, where a change was needed, what was done.

The two reports containing no crash evidence — **#940** and **#948** — were not dismissed as unreproducible. They inspired QUILL to recognize that pattern itself and stop presenting crash recovery when the log contains nothing actionable.

Ranked spelling and favorite folders came directly from a tester’s side-by-side comparison with another product. The same conversation also called for an instant single-word spelling check, and **Alt+F7** arrives in this release alongside them.

The braille correction moved from experiment to default because braille users tested it.

The macOS corrections exist because testers described experiences that sounded improbable until the underlying toolkit behavior made them completely explainable.

The Offline Edition became genuinely offline because a community member tested its promise rather than assuming the label was enough.

This is not simply how QUILL improves. **This is how QUILL is built.**

---

## Toward 1.0 — Together

Beta 3 moves the 0.9.0 cycle closer to 1.0 with a stronger editor, clearer safeguards, deeper accessibility, and a growing set of workflows shaped by the people who use them.

Please keep exploring. Open the formats that matter to you. Try the braille behavior, Narrator announcements, VoiceOver rich editing, portable update flow, local git tools, GitHub commands, spell-checking workflows, folder favorites, folding, speech engines, and offline installation.

When something surprises you — beautifully or badly — use **Help > Report a Bug** and tell us what happened.

A successful report matters. A failure report matters. A strange edge case matters. A feature request grounded in real work matters.

Thank you for testing. Thank you for challenging assumptions. Thank you for helping turn an editor into a community-built place where more people can create, contribute, and belong.

**QUILL 0.9.0 Beta 3 is here. One editor. Every format. Built with you.**
