# Glossary of QUILL Terms

These are the words you will meet in QUILL's menus, dialogs and documentation,
with what each one means. They are listed roughly in the order a new user tends
to run into them.

**Abbreviation**
A short word or phrase that QUILL turns into longer text as you type. For
example, typing `brb` could become "be right back". You manage them in the
Abbreviation Manager (`Ctrl+Shift+Grave, Shift+A`). Abbreviations expand on
their own, with no separate insert step, and they do not have fill-in
placeholders. Snippets are the ones with placeholders.

**Agent / Agent Center**
An AI helper that takes a goal you describe and turns it into a plan of several
steps. The Agent Center shows you each step before it runs, so you can check it
and approve it. Agents are built on the Writing Assistant and Prompt Studio, and
they need an AI provider set up first.

**Browse Mode / Quick Nav Mode**
A way of moving around where single keys become navigation commands. Press the
QUILL key once to turn on Quick Nav for just the next key you press. Press it
twice to lock Browse Mode on until you press Escape. While Browse Mode is on,
letter keys and arrow keys move you around instead of typing, much like your
screen reader's virtual cursor on a web page. (In the keymap the QUILL key is
written `Ctrl+Shift+Grave`; everywhere else QUILL shows it as `QUILL Key`.)

**Command Palette**
A searchable list of every QUILL command, with the key each one is on right now.
Open it with `Ctrl+Shift+P`, type any part of a command's name to narrow the
list, then press Enter to run it. It is the quickest way to anything when you do
not remember the menu or the key.

**Copy Tray**
A clipboard with twelve slots, kept inside QUILL. The Windows clipboard holds one
thing at a time; the Copy Tray lets you copy different pieces of text into
numbered slots and paste from any of them. To copy into a slot, press
`Ctrl+Shift+Grave, Shift+1` through `Ctrl+Shift+Grave, Shift+9`, then
`Ctrl+Shift+Grave, Shift+0`, `Ctrl+Shift+Grave, Shift+-` and
`Ctrl+Shift+Grave, Shift+=` for slots ten to twelve. Open the Copy Tray dialog
with `Ctrl+Alt+V`, which works much like `Win+V` does for Windows' own clipboard
history.

**Document Tab**
One open file, or one thing QUILL made for you, in the editor area. QUILL opens
everything in tabs: each file, compare summary or AI result gets its own. When
you switch tabs with `Ctrl+Tab`, QUILL tells you the tab's name.

**GLOW (Guided Layout and Output Workflow)**
QUILL's built-in checker for text quality and accessibility. GLOW looks through a
document for problems with its structure: heading levels, link text like "click
here", missing alt text, missing language information, tables without header
cells, spacing, and paragraphs that are too dense. It offers fixes that do the
same thing every time. The results open as tabs you can read. Fixing the open
document shows you a named preview and starts a compare, so you can review each
change. Fixing a file on disk writes a repaired copy and leaves the original
alone. The checks inside the editor cover plain text, Markdown and HTML. The
optional GLOW engine adds checks and fixes for DOCX, PPTX, XLSX, PDF and EPUB,
with a scored, graded report. You will find its commands on **Tools > Writing and Language** once GLOW is
turned on in the Experimental tab of Preferences.

**Keymap / Keyboard Pack (.kqp)**
The list of which key runs which QUILL command. You can change any of it in
**Preferences > Keyboard**. You can export your keymap as a `.kqp` file (a
Keyboard Pack) to share it, or import one somebody else made. Resetting the
keymap puts the factory keys back and leaves your other preferences alone.

**Macro**
A recording of things you did in QUILL that you can play back whenever you
like. Start from **Tools > Advanced > Macros > Start Recording**, do the steps you want to
repeat, then stop recording. Play it back later and QUILL repeats the steps
exactly. Macros are great for cleanup jobs you do over and over.

**Profile (Feature Profile)**
A named set of switches that decides which QUILL features you see and can use.
QUILL comes with profiles such as Writing, Developer and Accessibility. A
profile hides the features you do not need for the work in front of you, so the
menus and option dialogs stay short. Change or edit profiles in
**More Preferences > Profiles and Features**.

**Prompt Studio**
The place to write and save AI prompts you want to reuse, with named blanks you
fill in each time. A Prompt Studio template might be "Rewrite for Plain Language:
${input:text}", where you supply the text each time you run it. Prompts are
saved as `.pqp` files, and you can import and export them.

**Quillin (Extension)**
An add-on for QUILL, also called an extension. A Quillin can add commands, menu
items, AI prompts or automation scripts. Each one has a `manifest.json` file
that describes what it does. Quillins run in a separate process, so if one
crashes it cannot take the editor down with it. That is not a security sandbox,
though: what keeps Quillins honest is code review and the Author Covenant. QUILL
comes with several Quillins already (word count, AI writing prompts), and you
can install others. The Quillin Manager is in **Preferences > Extensions**.

**Recovery / Session Recovery**
QUILL quietly saves a copy of your work every so often. If QUILL closes when you
did not expect it (a crash, a power cut, an accidental close), it notices the
unsaved work the next time it starts and offers to bring back the last version
it kept. Recovery files are kept apart from your own saved files, so a damaged
recovery file can never overwrite your original. Manage them in
**File > Restore Backup...**.

**Remote Site**
A saved connection to a server, so QUILL can open and save files there directly.
QUILL works with FTP, SFTP, HTTPS (WebDAV) and S3-compatible object storage. You
name and save sites in **File > Open from Remote > Manage Remote Sites...**, so you do
not have to type your sign-in details every time. Each site keeps the host, port,
protocol, sign-in details (encrypted on Windows with DPAPI) and a starting
folder.

**Safe Mode**
A way of starting QUILL with AI, Watch Folder and Quillin extensions turned off.
Use it when a Quillin or an AI provider is causing trouble and you want a clean
start. Start QUILL with `--safe-mode` on the command line, or set
`QUILL_SAFE_MODE=1` as an environment variable before you start it. In Safe
Mode, the status bar tells you which features are off.

**Session (AI Session)**
An ongoing conversation between you and an AI provider inside QUILL. A session
has a name, a provider, a model and the history of what was said. You can keep
several named sessions and switch between them. Sessions are kept on your
computer and can be exported. The Writing Assistant always works inside a
session.

**Skill / Skill Library**
A named AI workflow you can reuse, made of several steps (prompts, transforms
and conditions). A skill is more organised than a single prompt: each step can
pass what it produced on to the next. The Skill Library (the Skills tab of **AI > AI Library...**)
is where you browse, run and write skills. Skills are stored as `.json` files;
the skills you write and share by hand are `.sqp` files, and Appendix B shows
you how.

**Snippet**
A block of text you reuse, inserted at the cursor when you ask for it. A snippet
can have fill-in blanks: `${input:name}` asks you to type something,
`${choice:a|b}` gives you a list to pick from, `${date}` and `${time}` fill in
the date and time, and `${cursor}` marks where the cursor lands afterwards.
Insert one with `Ctrl+Shift+Grave, S`, and manage them with
`Ctrl+Shift+Grave, Shift+S`. Abbreviations are different: they expand on their
own as you type.

**Sound Pack**
A set of sound files QUILL plays as feedback that is not speech: key sounds,
navigation tones, alert chimes and, if you want them, tones for indentation
levels when you write code. A Sound Pack is loaded from a named folder, and you
can swap packs in Preferences. The default pack uses synthesised bell tones. A
custom pack can use any WAV files, as long as they follow the naming
convention.

**Template**
A ready-made document shape to start new writing from. QUILL has two kinds.
Snippets (**Insert > Insert Snippet...**, `Ctrl+Shift+Grave, S`) insert reusable blocks with fill-in blanks
anywhere. The **Accessible Vault's Insert Template** command fills in note
templates from your vault's Templates folder: it fills in `{{date}}` and
`{{title}}`, asks you any `{{prompt}}` questions, and puts the cursor at
`{{cursor}}`.

**Watch Folder**
A folder QUILL keeps an eye on while it runs. Drop a supported file into it, and
QUILL opens the file as a new document tab (or deals with it by that folder's
own rules). It is handy for transcriptions, dictation and reviewing a batch of
files. Set it up in **Tools > Watch Folder**.

**WebView / Side Preview**
The pane beside the editor that shows your document as a rendered page. Open it
from the **View** menu, or turn on Auto Side-by-Side Preview and it opens on its
own. `Alt+F6` moves focus to it, and while it is open it is one of the places
`F6` cycles through. It uses Microsoft Edge WebView2 and shows Markdown, HTML
and plain text, updating as you type. The preview is read-only and never
changes your document.

**Welcome Guide**
A short getting-started document that opens inside QUILL as a document tab. The
full User Guide opens in your browser; the Welcome Guide shows only the features
your current profile has turned on. Open it from
**Help > Open Welcome Guide**.

**Writing Assistant**
QUILL's AI writing panel. Tell it what you want to do in plain words and it
suggests the QUILL commands that fit best. It also has ready-made rewrite,
summarize, continue and grammar actions, and it can run a limited Python
transform on the current document (with a list of allowed imports and limits on
resources, which is not a security boundary). It works inside an AI Session and
needs an AI provider set up in Preferences.

**QUILL Key**
The key combination `Ctrl+Shift+Grave` (the grave or backtick key, above Tab).
Press it once and the next key you press is a QUILL key command. Press it twice
to lock Quick Nav Mode on. Most of QUILL's more powerful features start with
the QUILL key. QUILL tells you each chord as you press it, and you can change
any of them in **Preferences > Keyboard**. In menus, the Keyboard Reference, the
status bar and the cheat sheet, these chords are written `QUILL Key + <key>`. In
`keymap.json` and the Keymap Editor, the same chord is written
`Ctrl+Shift+Grave, <key>`.

---

- Previous: [Appendix E: Design notes for developers](quill-guide-appendix-e-design-notes-for-developers.html)
- Next: [Licences and notices](quill-guide-licences-and-notices.html)
- [Contents](../userguide.html)
