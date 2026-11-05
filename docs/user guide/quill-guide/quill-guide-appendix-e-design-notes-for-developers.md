# Appendix E: Design notes for developers

The last appendix is for people who build on QUILL or are curious about
how parts of it were designed. It is written for developers, so it talks
about code, files and plans in a way the rest of this guide does not. Some
of what it describes was planned rather than built; the chapters and
Appendix A describe what QUILL does today.

## The Developer Console design document


### Feature name

**QUILL Developer Console and Automation API**

### Status

Proposed for **QUILL 1.1**, with the Python console eligible for a 1.0 experimental/dev-preview flag if the command registry and announcement infrastructure are stable enough.

### Owner

Community Access

### Target platform

Windows 10 and Windows 11

### Target users

* QUILL developers
* QUILL power users
* Accessibility professionals
* Blind programmers and technical writers
* Macro authors
* Support/debugging users working with Community Access staff
* Future Quillins/plugin developers

### 1. Vision

QUILL should provide a screen-reader-first developer console that lets trusted users inspect and manipulate the running editor through a stable automation API.

The console is not an afterthought, a hidden debug hack, or a generic unsafe scripting surface. It is a first-class, accessible automation layer that exposes QUILL's command system, document model, editor state, diagnostics, and accessibility announcement pipeline in a predictable way.

The goal is to let a developer or power user type commands such as:

```python
q.insert_text("Hello from QUILL.")
q.goto_line(42)
q.run_command("quill.document.wordCount")
q.run_command("quill.markdown.normalizeHeadings")
```

or, in TypeScript:

```ts
await quill.insertText("Hello from TypeScript.");
await quill.gotoLine(42);
const stats = await quill.documentStats();
console.log(stats.words);
```

Every editor-changing action must go through the QUILL command registry or official scripting API so undo, dirty-state tracking, accessibility announcements, status bar updates, telemetry, and tests remain consistent.

### 2. Problem statement

QUILL is becoming a rich writing and document environment with commands, macros, Quillins, profiles, diagnostics, document intake, spell checking, format conversion, and accessibility-aware UI behavior.

Without a developer console and automation API:

* Developers must debug by adding temporary logging or breakpoints.
* Support staff cannot easily inspect user state during troubleshooting.
* Power users cannot automate repetitive editor actions.
* Macro support risks becoming a separate one-off system instead of using the same command architecture as the rest of QUILL.
* Future Quillins may lack a simple interactive testing surface.
* Accessibility professionals cannot quickly inspect document state, selection state, command availability, profile gating, or announcement behavior.

QUILL needs an embedded, accessible command line for trusted local development and automation.

### 3. Goals

1. Provide an accessible Python console inside the running QUILL app.
2. Provide a TypeScript automation console through a controlled Node subprocess bridge.
3. Expose a stable `q` / `quill` scripting object instead of raw internal objects.
4. Route all mutations through the command registry or official scripting API.
5. Preserve undo/redo, dirty-state tracking, backups, status bar updates, and screen-reader announcements.
6. Make console results easy to review with NVDA, JAWS, Narrator, braille displays, and keyboard-only workflows.
7. Support command history, multi-line input, copy/paste, saved snippets, and transcript export.
8. Gate the feature behind profiles and explicit settings so it does not surprise ordinary users.
9. Make the console useful for macro development, plugin development, support diagnostics, and test automation.
10. Never enable remote execution by default.

### 4. Non-goals

1. QUILL will not provide a public remote execution service in v1.
2. QUILL will not allow untrusted scripts to run silently.
3. QUILL will not expose arbitrary internal object mutation as the recommended workflow.
4. QUILL will not make Python or TypeScript scripting required for normal use.
5. QUILL will not replace a full IDE, debugger, or terminal.
6. QUILL will not guarantee sandbox security for arbitrary malicious code in the local Python console.
7. QUILL will not let scripts bypass document protection, source-file safety, cloud-consent prompts, or profile safety rules.

### 5. User stories

#### 5.1 Developer

As a QUILL developer, I want to open a console, inspect the active document, run commands, and test editor behavior without rebuilding or adding temporary menu items.

Example:

```python
q.doc.name
q.selection.text
q.goto_line(100)
q.run_command("quill.find.next")
```

#### 5.2 Accessibility tester

As an accessibility tester, I want to inspect the focused region, active command, current screen-reader announcement backend, and the last announcements so I can diagnose what a user experienced.

Example:

```python
q.a11y.last_announcements()
q.a11y.announce("Testing announcement path.")
q.focus.describe()
```

#### 5.3 Macro author

As a power user, I want to experiment with commands interactively and save successful sequences as a macro.

Example:

```python
q.begin_macro("Clean OCR text")
q.run_command("quill.text.normalizeUnicode")
q.run_command("quill.text.dehyphenateLines")
q.run_command("quill.text.reflowParagraphs")
q.end_macro()
```

#### 5.4 Support technician

As a support technician, I want a user to run a safe diagnostic command and copy the output into an email or support ticket.

Example:

```python
q.support.diagnostic_summary()
```

#### 5.5 TypeScript user

As a developer more comfortable with TypeScript, I want to run async commands against QUILL using a typed API and receive clear errors.

Example:

```ts
const doc = await quill.activeDocument();
await quill.gotoLine(25);
console.log(doc.name);
```

### 6. Feature placement

The feature appears in the following command surfaces:

#### Tools menu

`Tools > Advanced > Developer Console`

Submenu items:

* Open Python Console
* Open TypeScript Console
* Open Console Transcript
* Save Current Console as Macro
* Manage Console Snippets
* Console Safety Settings
* Copy Diagnostic Summary

#### Command palette

Commands:

* `quill.console.openPython`
* `quill.console.openTypeScript`
* `quill.console.clear`
* `quill.console.copyTranscript`
* `quill.console.saveTranscript`
* `quill.console.saveInputAsSnippet`
* `quill.console.insertSnippet`
* `quill.console.runSelection`
* `quill.console.runCurrentDocument`
* `quill.console.showContext`
* `quill.console.resetNamespace`
* `quill.console.restartTypeScriptWorker`
* `quill.console.openSafetySettings`

#### Feature profiles

Default visibility:

| Profile                              | Python console | TypeScript console | Macro recording | Remote console |
| ------------------------------------ | -------------- | ------------------ | --------------- | -------------- |
| Essential                            | Off            | Off                | Off             | Locked off     |
| Casual Writer                        | Off            | Off                | Quiet           | Locked off     |
| Reader and Student                   | Off            | Off                | Off             | Locked off     |
| Office and Admin                     | Off            | Off                | Quiet           | Locked off     |
| Accessibility Professional           | Off            | Off                | On              | Locked off     |
| Developer                            | On             | On                 | On              | Locked off     |
| Braille and Screen Reader Power User | Off            | Off                | On              | Locked off     |
| Full Quill                           | On             | On                 | On              | Locked off     |

Remote execution remains unavailable unless an experimental developer build explicitly enables it.

### 7. UX requirements

#### 7.1 Console window layout

The console is a standard wx dialog or frame using stock controls.

Required controls:

1. **Transcript output**

   * Read-only multi-line `wx.TextCtrl`
   * Receives command output, errors, return values, announcements, and command prompts
   * Supports select all, copy, find, and save transcript

2. **Command input**

   * Editable `wx.TextCtrl`
   * Single-line by default
   * Multi-line mode available with a toggle or `Shift+Enter`
   * Enter runs the current command when the command is complete

3. **Language selector**

   * Python
   * TypeScript
   * Future: command-only mode

4. **Status line**

   * Shows current language, prompt state, active document, and worker status

5. **Buttons**

   * Run
   * Clear
   * Copy transcript
   * Save transcript
   * Insert snippet
   * Help
   * Close

#### 7.2 Keyboard behavior

Required shortcuts:

| Shortcut     | Action                                                                                    |
| ------------ | ----------------------------------------------------------------------------------------- |
| Enter        | Execute current command                                                                   |
| Shift+Enter  | Insert newline in multi-line input                                                        |
| Ctrl+Enter   | Force execute multi-line command                                                          |
| Up/Down      | Previous/next command history when input cursor is at boundary                            |
| Ctrl+L       | Clear transcript                                                                          |
| Ctrl+Shift+C | Copy transcript                                                                           |
| Ctrl+S       | Save transcript                                                                           |
| Ctrl+F       | Find in transcript                                                                        |
| F6           | Move between transcript, input, status, and buttons                                       |
| Esc          | Return focus to editor if console is non-modal; close if modal confirmation is not needed |
| F1           | Open console help                                                                         |
| Ctrl+Space   | Trigger completion if available                                                           |
| Tab          | Insert indentation in multi-line mode or move focus depending on setting                  |

#### 7.3 Screen-reader behavior

The console must be fully usable with NVDA, JAWS, and Narrator.

Requirements:

* Every control has a clear accessible name.
* The transcript announces new output without stealing focus.
* Errors are announced with the prefix "Error".
* Return values are announced with the prefix "Result".
* Long output is not automatically spoken in full; the console announces a summary and lets the user review the transcript.
* The console supports a "copy last result" command.
* The console supports a "speak last result" command.
* The console uses QUILL's central announcement path.
* Braille users can review the transcript as plain text.
* No custom drawn controls are allowed in the primary console workflow.

#### 7.4 Prompt behavior

Python prompt:

```text
>>>
```

Continuation prompt:

```text
...
```

TypeScript prompt:

```text
ts>
```

Async TypeScript pending prompt:

```text
ts*>
```

The prompt itself is included in the transcript but not required in copied code unless the user chooses "Copy with prompts".

### 8. Python console requirements

#### 8.1 Execution model

The Python console runs in-process and uses Python's embedded interpreter facilities.

The console maintains a persistent namespace for the session. Hiding the console does not destroy the namespace unless the user explicitly resets it.

#### 8.2 Default namespace

The following names are available by default:

```python
q              # Primary QUILL scripting API
app            # Application-level read-mostly object
frame          # Main frame, available for debugging
commands       # Command registry read/execute facade
doc            # Active document snapshot
editor         # Active editor snapshot
sel            # Current selection snapshot
caret          # Current caret snapshot
profile        # Active feature profile snapshot
settings       # Safe settings facade
diagnostics    # Diagnostics facade
a11y           # Announcement/testing facade
log            # Console-safe logger
wx             # wx module, developer profile only
```

#### 8.3 Snapshot refresh

The console updates snapshot variables when:

* The console opens.
* The active document changes.
* The user runs `q.refresh_context()`.
* A command changes editor state.
* The user chooses "Refresh Console Context".

Snapshot variables such as `doc`, `sel`, and `caret` are safe read-only snapshots unless explicitly documented otherwise.

#### 8.4 Python examples

```python
q.insert_text("Hello from QUILL.")
```

```python
q.replace_selection("Replacement text")
```

```python
q.goto_line(42)
```

```python
q.run_command("quill.document.wordCount")
```

```python
q.a11y.announce("This is a test announcement.")
```

```python
q.diagnostics.document_summary()
```

```python
q.commands.search("spell")
```

### 9. TypeScript console requirements

#### 9.1 Execution model

The TypeScript console runs out-of-process through a Node worker.

Python QUILL process:

* Owns the editor, document model, command registry, and UI thread.
* Sends TypeScript code to the Node worker.
* Receives JSON-RPC-style command requests from the worker.
* Executes approved commands on the wx main thread.
* Returns structured results or errors.

Node TypeScript worker:

* Receives TypeScript code.
* Transpiles it to JavaScript.
* Executes it with a limited `quill` proxy object.
* Sends editor actions back to Python as structured requests.
* Captures `console.log`, warnings, errors, and return values.

#### 9.2 TypeScript global API

The TypeScript console exposes:

```ts
quill
console
setTimeout
clearTimeout
AbortController
```

The TypeScript worker must not expose unrestricted filesystem, network, process, or shell access through the default console environment.

#### 9.3 TypeScript examples

```ts
await quill.insertText("Hello from TypeScript.");
```

```ts
await quill.replaceSelection("Replacement text");
```

```ts
await quill.gotoLine(42);
```

```ts
const stats = await quill.documentStats();
console.log(`${stats.words} words`);
```

```ts
await quill.runCommand("quill.markdown.normalizeHeadings");
```

#### 9.4 Type definitions

QUILL ships a `quill-console.d.ts` type definition file so TypeScript users get completion and documentation.

Example:

```ts
interface QuillConsoleApi {
  insertText(text: string): Promise<void>;
  replaceSelection(text: string): Promise<void>;
  gotoLine(line: number): Promise<void>;
  runCommand(commandId: string, args?: Record<string, unknown>): Promise<unknown>;
  activeDocument(): Promise<QuillDocumentSnapshot>;
  documentStats(): Promise<QuillDocumentStats>;
  announce(text: string, options?: AnnouncementOptions): Promise<void>;
}
```

#### 9.5 Worker lifecycle

The TypeScript worker starts only when the TypeScript console is opened.

The worker stops when:

* QUILL exits.
* The user closes the console and worker idle timeout expires.
* The user chooses "Restart TypeScript Worker".
* The worker exceeds memory or time limits.
* The worker crashes.

Worker crashes must not crash QUILL.

### 10. QUILL scripting API

#### 10.1 API principles

The scripting API is the official automation surface.

Rules:

1. Mutations go through the command registry.
2. Undo/redo must work.
3. Dirty state must update.
4. Status bar must update.
5. Screen-reader announcements must happen.
6. Profile and feature gates must be respected.
7. Cloud/network actions must still ask for consent.
8. Protected originals must stay protected.
9. Commands must return structured results.
10. Errors must be plain-language first, traceback second.

#### 10.2 Python API shape

```python
class QuillScriptAPI:
    def insert_text(self, text: str) -> None: ...
    def replace_selection(self, text: str) -> None: ...
    def selected_text(self) -> str: ...
    def document_text(self) -> str: ...
    def set_document_text(self, text: str) -> None: ...
    def goto_line(self, line: int) -> None: ...
    def goto_offset(self, offset: int) -> None: ...
    def run_command(self, command_id: str, **kwargs): ...
    def command_exists(self, command_id: str) -> bool: ...
    def list_commands(self, query: str | None = None) -> list[CommandInfo]: ...
    def active_document(self) -> DocumentSnapshot: ...
    def document_stats(self) -> DocumentStats: ...
    def refresh_context(self) -> None: ...
```

#### 10.3 TypeScript API shape

```ts
interface QuillApi {
  insertText(text: string): Promise<void>;
  replaceSelection(text: string): Promise<void>;
  selectedText(): Promise<string>;
  documentText(): Promise<string>;
  setDocumentText(text: string): Promise<void>;
  gotoLine(line: number): Promise<void>;
  gotoOffset(offset: number): Promise<void>;
  runCommand(commandId: string, args?: Record<string, unknown>): Promise<unknown>;
  commandExists(commandId: string): Promise<boolean>;
  listCommands(query?: string): Promise<CommandInfo[]>;
  activeDocument(): Promise<DocumentSnapshot>;
  documentStats(): Promise<DocumentStats>;
  refreshContext(): Promise<void>;
}
```

#### 10.4 Safe facades

The console exposes safe facades instead of raw internals wherever possible.

Required facades:

* `q.documents`
* `q.editor`
* `q.selection`
* `q.commands`
* `q.bookmarks`
* `q.search`
* `q.spell`
* `q.markdown`
* `q.text`
* `q.a11y`
* `q.diagnostics`
* `q.profile`
* `q.settings`
* `q.support`
* `q.macros`
* `q.quillins`

### 11. Command registry integration

Every console-callable command must declare metadata:

```python
Command(
    id="quill.editor.insertText",
    title="Insert Text",
    description="Insert text at the current caret position.",
    handler=insert_text_handler,
    default_key=None,
    when="editorFocus",
    scriptable=True,
    mutates_document=True,
    undo_group="typing",
    requires_consent=False,
    profile_feature="developer.console",
)
```

Required metadata fields for scriptable commands:

* `id`
* `title`
* `description`
* `scriptable`
* `mutates_document`
* `undo_group`
* `requires_consent`
* `profile_feature`
* `privacy_label`
* `network_label`
* `return_schema`
* `argument_schema`

The console refuses to run commands marked `scriptable=False` unless developer unsafe mode is enabled.

### 12. Macro integration

The console is the fastest path to creating and testing macros.

Requirements:

* Users can save selected console history as a macro.
* Macros are stored as command sequences by default, not arbitrary Python code.
* Python macros are developer-profile-only.
* TypeScript macros are developer-profile-only.
* Command-sequence macros are allowed in more profiles.
* Macro execution shows a preview when it will modify the document.
* Macro execution is one undo group unless the macro author explicitly splits undo groups.
* Macro failures stop execution and announce the failed step.

Example command-sequence macro:

```json
{
  "name": "Clean OCR text",
  "steps": [
    {"command": "quill.text.normalizeUnicode"},
    {"command": "quill.text.dehyphenateLines"},
    {"command": "quill.text.reflowParagraphs"}
  ]
}
```

### 13. Security and safety

#### 13.1 Local trust model

The Python console is trusted local code execution.

QUILL must clearly warn users:

```text
The Developer Console can run code inside QUILL.
Only run commands you understand or received from a trusted source.
```

This warning appears:

* The first time the console opens.
* When enabling the feature from Settings.
* When pasting multi-line code from the clipboard.
* When attempting to enable unsafe developer mode.

#### 13.2 Remote execution

Remote execution is locked off by default.

Requirements:

* No listening socket in stable builds.
* No hidden remote console.
* No command-line flag that silently enables remote execution.
* Experimental remote console, if ever added, must bind to localhost only by default.
* Remote console must require an explicit one-time token.
* Remote console must show a persistent status bar warning.
* Remote console must auto-disable on restart unless the user explicitly chooses otherwise.

#### 13.3 Dangerous operations

The console must prompt or block for:

* Running shell commands
* Reading arbitrary files outside allowed locations
* Writing arbitrary files outside QUILL-controlled flows
* Sending document content to network services
* Installing Quillins
* Changing profile safety rules
* Disabling backups or crash recovery
* Accessing protected source documents
* Running pasted multi-line code

#### 13.4 TypeScript worker limits

Default limits:

| Limit                  | Default                     |
| ---------------------- | --------------------------- |
| Execution timeout      | 30 seconds                  |
| Idle timeout           | 10 minutes                  |
| Memory warning         | 256 MB                      |
| Memory hard limit      | 512 MB                      |
| Output flood threshold | 100 KB                      |
| Max transcript size    | 5 MB before rotation prompt |

Long-running TypeScript scripts must support cancellation.

### 14. Accessibility requirements

The console must pass QUILL's normal accessibility gates.

Required tests:

* NVDA reads console controls correctly.
* JAWS reads console controls correctly.
* Narrator reads console controls correctly.
* F6 cycles through console regions.
* Escape behavior is predictable.
* New output does not steal focus.
* Long output is summarized.
* Errors are reviewable character-by-character.
* Braille display review works through the transcript control.
* High contrast mode remains readable.
* Large font mode does not clip prompts or buttons.
* Keyboard-only users can run, copy, save, clear, and close.
* No console action traps focus.

### 15. Error handling

Errors appear in three layers:

1. Plain-language summary
2. Actionable suggestion
3. Technical details, expandable or copyable

Example:

```text
Error: Unknown command "quill.markdown.fixHeading".
Suggestion: Run q.commands.search("heading") to find matching commands.
Details: CommandNotFoundError: quill.markdown.fixHeading
```

Python tracebacks are available but collapsed behind "Show technical details" unless the active profile is Developer.

TypeScript stack traces are captured and mapped to the user's submitted code when possible.

### 16. Logging and transcripts

The console keeps a local transcript of:

* Commands entered
* Results
* Errors
* Warnings
* Announcements triggered by console commands
* Worker lifecycle events
* Macro recording markers

Privacy requirements:

* Transcripts are not sent anywhere automatically.
* Document text is included only when commands print or return it.
* "Copy diagnostic summary" redacts document content by default.
* Users can save transcripts manually.
* Support packages ask before including transcript content.

### 17. Settings

Settings page: `Settings > Developer Console and Automation`

Settings:

* Enable Developer Console
* Enable Python Console
* Enable TypeScript Console
* Show first-run safety warning again
* Require confirmation before pasted multi-line execution
* Require confirmation before document-wide mutation
* Allow script access to raw wx objects
* Allow shell commands
* Allow filesystem access
* TypeScript worker path
* TypeScript worker timeout
* Transcript retention
* History retention
* Clear history on exit
* Enable completions
* Enable result announcements
* Output verbosity: concise, normal, verbose
* Unsafe developer mode

Dangerous settings are available only in Developer or Full Quill profiles.

### 18. Data storage

Suggested files:

```text
%APPDATA%\Quill\console\
  history.jsonl
  snippets.json
  transcripts\
  types\
    quill-console.d.ts
  ts-worker\
    worker.js
```

Portable mode stores the same structure next to the portable QUILL configuration directory.

History entries contain:

```json
{
  "timestamp": "2026-06-10T00:00:00Z",
  "language": "python",
  "input": "q.document_stats()",
  "success": true
}
```

History must not store command output by default.

### 19. Technical architecture

#### 19.1 New modules

```text
quill/
  core/
    scripting.py              Official QuillScriptAPI facade
    script_context.py         Active console context snapshots
    script_permissions.py     Console permission checks
    script_results.py         Structured result and error models
  devtools/
    console_window.py         wx console UI
    python_console.py         Embedded Python console
    ts_console.py             Python-side TypeScript bridge
    ts_worker_protocol.py     JSON-RPC message schema
    completions.py            Completion provider
    history.py                Console history manager
    snippets.py               Snippet manager
    transcripts.py            Transcript manager
  tools/
    ts_worker/
      worker.ts               TypeScript worker source
      worker.js               Built worker
      quill-console.d.ts      Type definitions
```

#### 19.2 Threading model

Rules:

* UI mutations must run on the wx main thread.
* Console input handling may occur in the UI thread only for quick commands.
* Long commands must run as background tasks.
* TypeScript worker communication runs asynchronously.
* Results are marshaled back to the UI through QUILL's event queue or `wx.CallAfter`.
* Command cancellation must be supported for long-running tasks.

#### 19.3 Command execution flow

```text
User enters command
    ↓
Console parser receives input
    ↓
Python console or TypeScript worker executes code
    ↓
Code calls q / quill API
    ↓
API validates permission, profile, and command metadata
    ↓
Command registry executes command
    ↓
Document/editor/status/a11y systems update
    ↓
Structured result returns to console
    ↓
Transcript updates and concise result is announced
```

### 20. Completion and help

The console should provide discoverability without requiring users to memorize APIs.

Completion sources:

* `q` methods
* command ids
* active document properties
* macro names
* snippet names
* settings keys
* feature ids

Help commands:

```python
q.help()
q.help("insert_text")
q.commands.search("bookmark")
q.describe_command("quill.editor.gotoLine")
q.examples("markdown")
```

TypeScript equivalents:

```ts
await quill.help();
await quill.commands.search("bookmark");
await quill.describeCommand("quill.editor.gotoLine");
```

### 21. Testing strategy

#### 21.1 Unit tests

* `QuillScriptAPI.insert_text` routes through command registry.
* `replace_selection` creates one undoable operation.
* `goto_line` rejects invalid line numbers with plain-language errors.
* `run_command` refuses non-scriptable commands.
* Profile gates hide or reject console commands properly.
* Permission checks block dangerous operations.
* Snapshot refresh updates document, selection, and caret state.
* TypeScript protocol serializes and deserializes results correctly.
* Worker crash returns a structured error.

#### 21.2 Integration tests

* Open Python console, run `q.insert_text`, verify document changes.
* Run document-wide command, verify undo restores prior state.
* Run command that announces result, verify announcement transcript.
* Open TypeScript console, run `await quill.insertText(...)`.
* Restart TypeScript worker and verify QUILL stays alive.
* Save console history as macro and run macro.
* Copy diagnostic summary and verify redaction.
* Paste multi-line code and verify confirmation prompt.

#### 21.3 Accessibility tests

* NVDA reads transcript and input controls.
* JAWS reads transcript and input controls.
* Narrator reads transcript and input controls.
* F6 region cycling works.
* Escape returns focus predictably.
* High contrast and large fonts work.
* Long output does not cause speech flood.
* Error details are reachable and copyable.

#### 21.4 Security tests

* Remote execution is not listening in stable builds.
* TypeScript worker cannot directly access unrestricted shell by default.
* Console cannot bypass network consent.
* Console cannot silently overwrite protected source documents.
* Pasted multi-line execution triggers confirmation.
* Unsafe developer mode cannot be enabled by imported profile alone.

### 22. Success criteria

The feature is successful when:

1. A developer can open the Python console and inspect/manipulate the active document through `q`.
2. A TypeScript user can run async editor commands through `quill`.
3. All document mutations are undoable.
4. Screen-reader users can operate the console without custom scripts.
5. Console commands respect profile, permission, and consent rules.
6. Long or failed commands do not crash QUILL.
7. TypeScript worker crashes do not crash QUILL.
8. Support diagnostics can be copied without leaking document content by default.
9. Macro creation can reuse console command history.
10. CI covers unit, integration, accessibility, and safety behavior.

### 23. MVP scope

#### MVP: Python Developer Console

Included:

* Python console window
* `q` scripting API
* Command registry execution
* Transcript output
* History
* Clear/copy/save transcript
* Basic completions
* Plain-language errors
* First-run safety warning
* Profile gating
* Undo-aware document mutations
* Accessibility tests with NVDA

Not included in MVP:

* TypeScript console
* Macro recording from history
* Advanced snippets
* Remote execution
* Raw wx unsafe mode
* Plugin authoring APIs

#### MVP+1: TypeScript Console

Included:

* Node worker bridge
* TypeScript transpilation
* `quill` async proxy
* Type definitions
* Worker restart
* Worker timeout and memory limits
* Console output capture
* TypeScript examples

#### MVP+2: Macro and Quillin authoring

Included:

* Save console history as macro
* Snippet manager
* Quillin test harness
* Command-sequence macro editor
* Console-based plugin diagnostics

### 24. Open questions

1. Should Python console be included in QUILL 1.0 as hidden experimental functionality?
2. Should the console be modal, non-modal, or dockable?
3. Should command history persist by default or require opt-in?
4. Should TypeScript support be bundled or require Node detection?
5. Should a minimal embedded JS engine be considered later for users who do not have Node?
6. Should console snippets sync with macros, or remain separate?
7. Should support technicians have a restricted "diagnostics-only console" mode?
8. Should unsafe developer mode require a launch flag in addition to a setting?
9. Should QUILL ship sample scripts for OCR cleanup, Markdown repair, and diagnostics?
10. Should console transcript export support Markdown, plain text, and JSON?

### 25. Example first-run warning

```text
Developer Console

This console can run commands inside QUILL and may change the current document.
Only run commands you understand or received from a trusted source.

Recommended:
- Use q.run_command(...) or documented q methods.
- Do not paste code from unknown sources.
- Save your document before running document-wide commands.

[Open Console] [Cancel] [Learn More]
```

### 26. Example diagnostic summary command

Python:

```python
q.support.diagnostic_summary()
```

Output:

```text
QUILL diagnostic summary
Version: 1.1.0-dev
Profile: Developer
Active document: chapter-7.md
Modified: yes
Documents open: 3
Screen reader detected: NVDA
Announcement backend: auto
Python console: enabled
TypeScript console: available
Last command: quill.editor.gotoLine
Last error: none
Document content included: no
```

### 27. Definition of done

This feature is done when:

* The Python console is fully keyboard accessible.
* The Python console exposes the official `q` scripting API.
* TypeScript console runs through a subprocess bridge and cannot crash QUILL.
* All editor mutations go through the command registry or scripting API.
* Undo/redo, dirty-state, status bar, and accessibility announcements remain correct after console-driven changes.
* Profile gating and safety settings work.
* First-run safety warnings are present.
* Console history, transcript copy, and transcript save work.
* Dangerous actions require confirmation or are blocked.
* Automated tests cover command execution, accessibility, worker failure, permissions, and undo behavior.
* User documentation explains examples, risks, and safe patterns.


---


## How the Copy Tray was built

### What Was Built

Copy Tray is a nine-slot persistent clipboard integrated across QUILL's menu
bar, keyboard layer, dialog system, and system tray icon. Every slot holds text
that survives application restarts.

#### Core model (`quill/core/copy_tray.py`)

A pure Python model with no wx dependency. `CopyTray` owns nine `TraySlot`
instances. Each slot has `text`, `label`, and `copied_at`. The model reads and
writes `copy_tray.json` in the QUILL data directory using `write_json_atomic`
(temp file + `os.replace`). A corrupt file causes a silent fresh start; it
never raises to the UI.

#### UI mixin (`quill/ui/main_frame_copy_tray.py`)

`CopyTrayMixin` is mixed into `MainFrame`. Methods:

- `copy_to_tray_slot(n)` -- copies the editor selection to slot n; announces
  slot number and text preview.
- `paste_from_tray_slot(n)` -- inserts slot n text at cursor (or replaces
  selection); announces slot number and label.
- `open_copy_tray()` -- opens the management dialog; pastes if the user chooses
  Paste and returns to the editor.
- `clear_all_tray_slots()` -- Yes/No confirmation (default No); clears all nine
  slots on Yes.

#### Dialog (`quill/ui/copy_tray_dialog.py`)

A resizable wx.Dialog with a ListBox and five action buttons. Each list row
shows slot number, optional label, and a 60-character preview. The list
receives focus on open. Buttons: Paste (Enter), Copy Selection Here, Set
Label..., Clear Slot, Close (Escape). Double-click pastes. Button states
update on every selection change: Paste and Clear Slot are disabled on empty
slots; Copy Selection Here is disabled when no editor text is selected.

#### Keyboard bindings (`quill/core/keymap.py`)

| Key | Action |
| --- | --- |
| `Ctrl+Alt+Shift+1` through `Ctrl+Alt+Shift+9` | Paste from slot 1-9 |
| `Ctrl+Shift+Grave, Shift+1` through `Ctrl+Shift+Grave, Shift+9` | Copy selection to slot 1-9 |
| `Ctrl+Alt+V` | Open Copy Tray dialog |

The paste bindings use the number row with `Ctrl+Shift`. These keys were
confirmed free across the entire QUILL keymap. QUILL-key bare digits 1-6 are
heading shortcuts; adding Shift produces a distinct chord with no conflict.

All 20 commands (`edit.open_copy_tray`, `edit.clear_all_tray_slots`,
`edit.copy_to_tray_1..9`, `edit.paste_from_tray_1..9`) are registered in
the keymap and appear in the Command Palette. All are reassignable in the
Keymap Editor.

#### Menu integration (`quill/ui/main_frame_menu.py`)

`Edit > Copy Tray` submenu with:
- Copy to Slot 1-9
- Paste from Slot 1-9
- Open Copy Tray...
- Clear All Tray Slots

The 18 per-slot items use dedicated `wx.NewIdRef()` IDs (`_id_copy_tray_slots`
and `_id_paste_tray_slots` arrays). Management commands are recirculated from
the power tools manifest via `_append_power_tools_copy_tray_items`.

#### Power tools manifest (`quill/ui/main_frame_power_tools_menu.py`)

New `"copy_tray"` group with `edit.open_copy_tray` and
`edit.clear_all_tray_slots`. New recirculation helper
`_append_power_tools_copy_tray_items`. The 18 individual slot commands are also
registered in the manifest for Command Palette discoverability.

#### System tray integration (`quill/ui/main_frame.py`)

The `_on_tray_right_click` method now builds a **Copy Tray** submenu listing
every occupied slot with its label (if any) and a 50-character text preview.
Clicking a slot calls `_tray_paste_slot(n)`, which restores the main window if
it is hidden, then pastes the slot content. If all slots are empty, the submenu
shows "(all slots empty)" as a disabled item. "Open Copy Tray..." is always
present at the bottom of the submenu.

#### Documentation

- `docs/userguide.md` -- complete feature reference with keyboard
  tables, dialog walkthrough, accessibility notes, and workflow tips.
- `docs/QUILL-PRD.md` -- section 5.77 added with motivation, operations table,
  keyboard defaults, storage spec, accessibility guarantees, and implementation
  map.
- `docs/userguide.md` -- "Copy Tray" section added in Writing and Editing,
  before "Copy With Source", with full keyboard tables and a tips block.

---

### The User Experience

#### First encounter

You open QUILL to write a long document while researching from several other
sources. You read a quote you want to use, select it, and press
`Ctrl+Shift+Grave, Shift+1`. QUILL says "Copied to slot 1". You read another
fragment. `Ctrl+Shift+Grave, Shift+2`. "Copied to slot 2". A third. Slot 3.

You switch to your draft. Where you want the first quote, press `Ctrl+Alt+Shift+1`.
QUILL says "Pasted from slot 1" and the text is there. The system clipboard was
never disturbed. The other two quotes are still in their slots.

You close QUILL. Come back tomorrow. Slots 1, 2, and 3 still hold their
contents.

#### Using labels

After a few days you decide to give slot 1 a permanent home: your email
signature. You open `Ctrl+Alt+V`, navigate to slot 1, press Set
Label..., type "signature", press Enter. Now when you paste, QUILL says "Pasted
from slot 1 (signature)". The slot is identifiable without looking at a screen.

#### From the system tray

QUILL is minimized to the system tray while you read in another browser. You
right-click the QUILL icon. The menu shows:

```
Show Quill
Copy Tray  >
  1.  signature — Hi, I wanted to follow up...
  2.  Hello world...
  3.  import sys, os, pathlib...
  ...
  Open Copy Tray...
Sticky Notes...
Exit Quill
```

You click slot 3. QUILL restores its window and pastes the import block at
your cursor. You minimize again.

#### Screen reader workflow

Press `Ctrl+Alt+Shift+5`. QUILL says "Slot 5 is empty." You know immediately
without opening a dialog or reading the screen. Select some text, press
`Ctrl+Shift+Grave, Shift+5`. "Copied to slot 5." Move elsewhere. Press
`Ctrl+Alt+Shift+5`. "Pasted from slot 5." Everything happened through voice, at
typing speed, with standard modifier+number chords.

---


## Ideas for later: double-tap keys

The user asked whether pressing a key twice quickly could trigger an alternative
action. For Copy Tray, the natural double-tap behaviour would be:

- **Single `Ctrl+Shift+N`** -- paste from slot N immediately.
- **Double `Ctrl+Shift+N`** (two presses within ~300ms) -- peek: QUILL speaks
  what is in slot N *without pasting* ("Slot 3: Hello world..."). This lets
  a screen-reader user verify a slot's content before committing to paste.

Implementing double-tap detection requires a timer in the QUILL-key prefix
state machine, a 300ms debounce, and a clear screen-reader announcement
pattern. It is architecturally clean and would make the Copy Tray even more
efficient for screen-reader-only workflows. This is noted here as a planned
enhancement, not yet implemented.

Other places in QUILL where double-tap patterns could add value:

- **Double QUILL key** (two presses of `Ctrl+Shift+Grave`) = open Copy Tray
  dialog, similar to how Windows `Win+V` opens clipboard history.
- **Double `F3`** = repeat the last Find All and jump to the next cluster of
  matches.
- **Double `Ctrl+Z`** = undo back to the last explicit save point.
- **Double `Ctrl+G`** = return to the previous location (ping-pong navigation).
- **Double `Escape`** = collapse all side panels and return focus to the editor.

These should be evaluated selectively -- double-tap timing is sensitive and can
interfere with rapid typists. The patterns with the clearest benefit and the
lowest collision risk are: Copy Tray peek and QUILL-key-double-press for the
tray dialog.

---

---

- Previous: [Appendix D: Notes from earlier versions](quill-guide-appendix-d-notes-from-earlier-versions.html)
- Next: [Glossary of QUILL Terms](quill-guide-glossary.html)
- [Contents](../userguide.html)
