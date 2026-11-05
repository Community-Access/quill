# Appendix A: The QUILL Developer Console

This appendix is for people who like to script and automate. Nobody needs it
to write, and if you never open the console you are missing nothing you use
every day. If you are a developer, a power user, an accessibility tester or
someone building a Quillin, read on. The QUILL Developer Console (QDC for
short) lets you look inside the running editor and drive it from code.

## What the QDC is

The Developer Console is a scripting window built into QUILL. You can inspect
and automate the editor while it runs, without rebuilding anything or adding
temporary menu items.

It is switched off by default for the Essential, Casual Writer and Reader and
Student profiles.
You will find it under the Developer, Power Text and Full QUILL profiles.

There are two consoles:

- **Python console.** Runs inside QUILL, with full access to the scripting API
  through the name `q`. Its prompt is `>>>`, and `...` while you are in the
  middle of a block.
- **TypeScript console.** Runs through a Node subprocess. Its API is
  asynchronous and is called `quill`. Its prompt is `ts>`, and `ts*>` while an
  async operation is still running.

Both share the same transcript window, and both speak through QUILL's usual
announcements.

## Opening the console

Choose **Tools > Advanced > Developer Console > Open Python Console** or
**Tools > Advanced > Developer Console > Open TypeScript Console**.

From the Command Palette, the commands are `quill.console.openPython` and
`quill.console.openTypeScript`.

The console opens as its own dialog. Press `Esc` to send focus back to the
editor. The dialog stays open, and keeps everything you defined, until you
close it yourself.

## Console layout

Press `F6` to move between the five areas of the console:

1. **Transcript.** Read-only. Shows prompts, output, errors and return values.
2. **Input.** One line by default. `Shift+Enter` adds a new line, so you can
   type a block of several lines.
3. **Language selector.** Switches between Python and TypeScript.
4. **Status line.** The current language, prompt state, active document and
   worker status.
5. **Buttons.** Run, Clear, Copy transcript, Save transcript, Insert snippet,
   Help and Close.

## Keyboard reference

These keys work inside the console window.

| Key | Action |
| --- | --- |
| Enter | Execute current command |
| Shift+Enter | Insert newline (multi-line input) |
| Ctrl+Enter | Force execute multi-line block |
| Up / Down | Previous / next history (when cursor is at line boundary) |
| Ctrl+L | Clear transcript |
| Ctrl+Shift+C | Copy transcript |
| Ctrl+S | Save transcript |
| Ctrl+F | Find in transcript |
| F6 | Move between transcript, input, status, and buttons |
| Esc | Return focus to editor |
| F1 | Console help |
| Ctrl+Space | Trigger completion |

## Python console

### Available names

These names are ready for you as soon as the console opens:

| Name | What it is |
| --- | --- |
| `q` | Primary QUILL scripting API, start here |
| `app` | Application-level read-mostly object |
| `commands` | Command registry facade |
| `doc` | Active document snapshot |
| `editor` | Active editor snapshot |
| `sel` | Current selection snapshot |
| `caret` | Current caret snapshot |
| `profile` | Active feature profile snapshot |
| `settings` | Safe settings facade |
| `diagnostics` | Diagnostics facade |
| `a11y` | Announcement / testing facade |
| `log` | Console-safe logger |
| `wx` | wx module (Developer profile only) |

`doc`, `sel` and `caret` are read-only snapshots, taken at the moment they
were captured. They refresh when the active document changes. Otherwise, call
`q.refresh_context()` to pull in the current state.

The `q` API also has these facades: `q.selection`, `q.doc`, `q.editor`,
`q.settings`, `q.profile`, `q.bookmarks`, `q.quillins`, `q.macros` (with
`q.begin_macro` and `q.end_macro`), `q.spell`, `q.diagnostics`, `q.a11y`,
`q.commands`, `q.focus` and `q.support`, plus `q.describe_command`.

### Basic operations

Insert text at the cursor:

```python
>>> q.insert_text("Hello from QUILL.")
```

Replace the current selection:

```python
>>> q.replace_selection("Replacement text")
```

Jump to a line:

```python
>>> q.goto_line(42)
```

Run a built-in command by its ID:

```python
>>> q.run_command("quill.document.wordCount")
```

Send a screen-reader announcement:

```python
>>> q.a11y.announce("Test announcement.")
```

### Inspecting state

Read the name of the active document:

```python
>>> doc.name
'notes.txt'
```

Read the current selection:

```python
>>> sel.text
'selected words here'
```

Read where the caret is (line and column both start at 1):

```python
>>> caret.line, caret.column
(12, 5)
```

Search for commands by keyword:

```python
>>> commands.search("spell")
['quill.spell.check', 'quill.spell.addWord', 'quill.spell.nextError']
```

Get a diagnostic summary, which is handy when you are asking for support:

```python
>>> q.support.diagnostic_summary()
```

### Accessibility diagnostics

Hear again what QUILL last announced:

```python
>>> q.a11y.last_announcements()
['Title Case applied', '5 words selected']
```

Describe where focus is right now:

```python
>>> q.focus.describe()
'Editor: notes.txt, line 12, col 5, no selection'
```

### Multi-line blocks

Press `Shift+Enter` to add new lines, then `Enter` or `Ctrl+Enter` to run the
block:

```python
>>> def count_words(text):
...     return len(text.split())
...
>>> count_words(doc.text)
487
```

### When a command runs too long

If something you type into the Python console runs away, a loop that never
ends say, QUILL stops it after **Python console execution timeout** seconds
(Settings > Administration) and tells you "Stopped after 30 seconds." It is
30 to begin with, and you can set anything from 5 to 300. A command that is
waiting on the system, such as a long sleep, stops as soon as that wait is
over.

### Macro recording

You can record a run of commands as a macro and use it again later:

```python
>>> q.begin_macro("Clean OCR text")
>>> q.run_command("quill.text.normalizeUnicode")
>>> q.run_command("quill.text.dehyphenateLines")
>>> q.run_command("quill.text.reflowParagraphs")
>>> q.end_macro()
Macro saved: "Clean OCR text"
```

## TypeScript console

The TypeScript console needs Node.js on your PATH. If QUILL cannot find it, it
tells you so and offers to help you install it.

### TypeScript prompt behavior

```text
ts> await quill.insertText("Hello.");
ts*>
Result: undefined
```

`ts>` means the console is ready. `ts*>` means an async operation is still in
flight. Results and errors land in the transcript by themselves.

### Available globals

| Global | What it is |
| --- | --- |
| `quill` | Async QUILL scripting proxy |
| `console` | Captured: `.log()`, `.warn()`, `.error()` appear in transcript |
| `setTimeout` / `clearTimeout` | Standard timer |
| `AbortController` | For cancellable operations |

### Basic TypeScript operations

Insert text:

```ts
ts> await quill.insertText("Hello from TypeScript.");
```

Replace the selection:

```ts
ts> await quill.replaceSelection("Replacement text");
```

Jump to a line:

```ts
ts> await quill.gotoLine(42);
```

Run a built-in command:

```ts
ts> await quill.runCommand("quill.markdown.normalizeHeadings");
```

### Inspecting state from TypeScript

```ts
ts> const doc = await quill.activeDocument();
ts> console.log(doc.name);
notes.txt
```

```ts
ts> const stats = await quill.documentStats();
ts> console.log(`${stats.words} words, ${stats.lines} lines`);
487 words, 38 lines
```

### Multi-line TypeScript

Press `Shift+Enter` to build a block over several lines, then `Ctrl+Enter` to
run it:

```ts
ts> const text = await quill.getText();
ts> const words = text.trim().split(/\s+/).filter(Boolean);
ts> await quill.announce(`${words.length} words`);
```

### TypeScript type definitions

QUILL comes with a file called `quill-console.d.ts`. If you have Node.js and a
code editor that understands TypeScript, copy the file into your project and
you get completion:

```ts
// quill is typed as:
interface QuillConsoleApi {
  insertText(text: string): Promise<void>;
  replaceSelection(text: string): Promise<void>;
  gotoLine(line: number): Promise<void>;
  runCommand(commandId: string, args?: Record<string, unknown>): Promise<unknown>;
  activeDocument(): Promise<QuillDocumentSnapshot>;
  documentStats(): Promise<QuillDocumentStats>;
  announce(text: string): Promise<void>;
}
```

## Screen-reader notes

- New output in the transcript is announced, and focus stays where it is.
- Errors are announced starting with the word "Error".
- Return values are announced starting with the word "Result".
- Long output is summed up in the announcement. Read the transcript with your
  screen reader for the full text.
- `Ctrl+Shift+C` copies the transcript at any time.
- The console speaks through Prism, the same announcement path every other
  part of QUILL uses.
- Every control is a standard Windows control. Nothing is custom-drawn.

## Console safety settings

There is no menu row for them: open the Command Palette (`Ctrl+Shift+P`)
and run the command `quill.console.openSafetySettings`.

| Setting | Default | Notes |
| --- | --- | --- |
| Python console enabled | Profile-dependent | Off for Essential / Casual Writer |
| TypeScript console enabled | Profile-dependent | Off except Developer profile |
| Require developer profile | On | Prevents accidental access in the Casual Writer profile |
| Max execution time (Python) | 30 s | Hard kill after timeout |
| Max execution time (TypeScript) | 30 s | Worker restart after timeout |
| Allow `wx` module access | Developer profile only | Not available in any other profile |
| Remote console | Locked off | Not available in QUILL 1.x |

## Transcript commands

You can run these from the Command Palette while the console is open.

| Command | What it does |
| --- | --- |
| `quill.console.copyTranscript` | Copy entire transcript to clipboard |
| `quill.console.saveTranscript` | Save transcript to a file |
| `quill.console.clear` | Clear the transcript |
| `quill.console.saveInputAsSnippet` | Save the current input as a named snippet |
| `quill.console.insertSnippet` | Insert a saved snippet into input |
| `quill.console.runSelection` | Run selected text in the transcript as a command |
| `quill.console.runCurrentDocument` | Run the active QUILL document as a script |
| `quill.console.showContext` | Print current snapshot values to transcript |
| `quill.console.resetNamespace` | Reset the Python namespace (clears all variables) |
| `quill.console.restartTypeScriptWorker` | Kill and restart the Node worker |

## For Quillin authors

The console is a good place to try out a Quillin while you build it. Load
your Quillin, open the Python console, and look at its manifest and the
commands it adds:

```python
>>> from quill.core.quillins.loader import get_loader
>>> loader = get_loader()
>>> ext = loader.get_extension("com.example.myextension")
>>> ext.manifest
ExtensionManifest(id='com.example.myextension', runtime='python', ...)
>>> ext.manifest.contributes.commands
(ExtensionCommand(id='ext.myext.run', title='My Command', ...),)
```

Run one of its commands straight through the command registry:

```python
>>> q.run_command("ext.myext.run")
```

Then check what it announced:

```python
>>> q.a11y.last_announcements()
['My command completed: 3 items processed']
```

For a Node.js Quillin, the TypeScript console is the natural place to test:

```ts
ts> await quill.runCommand("ext.myext.nodeHandler");
ts> // Check the last announcement
ts> const ann = await quill.lastAnnouncement();
ts> console.log(ann);
```

## What the console can and cannot do yet

The console is built and working under the Developer, Power Text and Full
QUILL profiles, at **Tools > Advanced > Developer Console**. Here is what you
get today:

- The Python console and its console window.
- The TypeScript console, running through a Node subprocess.
- The `q` scripting API: the text, navigation and command methods, plus the
  facades `q.selection`, `q.doc`, `q.editor`, `q.settings`, `q.profile`,
  `q.bookmarks`, `q.quillins`, `q.macros` (with `q.begin_macro` and
  `q.end_macro`), `q.spell`, `q.diagnostics`, `q.a11y`, `q.commands`,
  `q.focus` and `q.support`, plus `q.describe_command`.

Some examples in this appendix were written for a fuller API than the console
has today. If a call shown here does not work, the list above is the one to
trust. The full scripting contract, with its own map of what is implemented,
is in `docs/quillins.md`.

## Where to go next

The thinking behind the console, and the plans for it, are in Appendix E,
Developer Console design document. If you build Quillins, `docs/quillins.md`
is your reference.

---

- Previous: [A last word](quill-guide-a-last-word.html)
- Next: [Appendix B: Writing skills for QUILL](quill-guide-appendix-b-writing-skills-for-quill.html)
- [Contents](../userguide.html)
