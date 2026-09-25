# QUILL Lite Basic Dictation
## Product Requirements Document

**Product:** QUILL Lite  
**Feature:** Basic Dictation  
**Platform:** Windows first  
**Implementation language:** Python  
**Status:** Proposed  
**Priority:** High  

---

# 1. Executive Summary

QUILL Lite will include a lightweight, highly accessible dictation capability as part of the normal installation.

The target experience is:

> **Press a key → speak → pause → hear a short confirmation sound → text appears → continue speaking.**

The user should not have to open a separate dictation window, download a large speech model, manage recordings, or understand speech-recognition technology.

The Windows implementation should use the Windows speech-recognition platform through lightweight Python WinRT bindings rather than bundling Whisper, Vosk, Torch, ONNX Runtime, FFmpeg, or another large speech stack.

QUILL will own the editing behavior. Windows will recognize speech; QUILL will interpret editing commands such as:

- new line
- new paragraph
- comma
- period
- question mark
- exclamation point
- colon
- semicolon
- open quote
- close quote
- open parenthesis
- close parenthesis
- tab
- scratch that
- delete that
- undo that
- stop dictation
- literal ...

A future phase may add a lightweight wake phrase such as:

> **Quill dictate**

The wake-word system should be independent from full speech recognition so that QUILL does not need to keep a large transcription model running continuously.

---

# 2. Problem Statement

Existing dictation solutions often introduce one or more of the following problems:

- large model downloads;
- high CPU, GPU, RAM, or NPU requirements;
- separate floating windows;
- unpredictable focus changes;
- inaccessible visual-only status;
- unclear phrase completion;
- complicated microphone setup;
- cloud-service configuration;
- recording and transcription workflows instead of direct editing;
- difficulty knowing when recognized text has actually been inserted;
- inconsistent behavior with screen readers.

QUILL Lite needs something much simpler.

The goal is not to build Dragon, Whisper, or a complete voice-control environment.

The goal is to make speaking text into a QUILL document almost as simple as typing it.

---

# 3. Product Vision

A user working in a QUILL Lite document should be able to:

1. Place the caret where text should be entered.
2. Press the Dictation keyboard command.
3. Hear a Start earcon.
4. Speak naturally.
5. Pause naturally.
6. Have QUILL receive the finalized recognition result.
7. Have QUILL interpret any spoken editing commands.
8. Insert the resulting text or perform the requested editor action.
9. Hear a Commit earcon only after the result has been applied.
10. Continue speaking without restarting dictation.
11. Repeat indefinitely.
12. Press the Dictation command again or say "stop dictation."
13. Hear a Stop earcon.

Focus must remain in the editor throughout normal operation.

---

# 4. Core Product Principle

The feature must be explainable in one sentence:

> **Press the Dictation key, speak naturally, and every time you pause QUILL places the words into your document and lets you keep talking.**

Everything else should remain implementation detail.

---

# 5. Goals

## 5.1 Lightweight

The basic feature must not require QUILL to bundle or download a large speech-to-text model.

The preferred target is:

- no Whisper model;
- no Torch;
- no ONNX Runtime;
- no FFmpeg;
- no Vosk model;
- no NumPy requirement solely for dictation;
- no GPU requirement;
- no NPU requirement.

## 5.2 Broad Machine Support

The feature should work on ordinary supported Windows machines, including lower-powered systems.

It must not require:

- Copilot+ PC hardware;
- NVIDIA GPU;
- dedicated AI accelerator;
- unusually large amounts of memory.

## 5.3 Accessible by Default

The feature must be usable with:

- JAWS;
- NVDA;
- Narrator;
- keyboard-only interaction;
- magnification;
- no vision.

No essential state may be communicated visually only.

## 5.4 High Confidence

The user must know when text has actually been inserted.

The Commit earcon must therefore be tied to the **successful application of a finalized recognition result**, not merely silence detection.

---

# 6. Primary Interaction

The default keyboard behavior should be a toggle.

First press:

> Start dictation.

Second press:

> Stop dictation.

The shortcut must be configurable.

A menu command must also be available for discoverability.

Suggested menu:

```text
Tools
  Dictation
    Start Dictation
    Stop Dictation
    Dictation Settings
```

---

# 7. Continuous Phrase Dictation

Dictation must remain active across phrase boundaries.

Expected sequence:

```text
User speaks
    ↓
User pauses
    ↓
Windows returns finalized recognition result
    ↓
QUILL parses commands and text
    ↓
QUILL applies result to editor
    ↓
QUILL plays Commit earcon
    ↓
Recognition remains active
    ↓
User continues speaking
```

The user must not need to press the Dictation key between sentences or paragraphs.

---

# 8. Spoken Command Layer

QUILL should treat speech recognition and editor commands as separate responsibilities.

Windows answers:

> What words were spoken?

QUILL answers:

> What should those words do inside the editor?

The command parser should be ordinary Python and should not require an AI model.

Example:

```text
Recognized:
"hello everyone period new paragraph welcome to quill lite period"

QUILL interpretation:

Hello everyone.

Welcome to QUILL Lite.
```

---

# 9. Initial Command Vocabulary

The following commands should be supported in the first production release where practical.

| Spoken phrase | Action |
|---|---|
| new line | Insert one line break |
| newline | Insert one line break |
| new paragraph | Insert paragraph break |
| tab | Perform configured tab behavior |
| comma | Insert `,` |
| period | Insert `.` |
| full stop | Insert `.` |
| question mark | Insert `?` |
| exclamation point | Insert `!` |
| exclamation mark | Insert `!` |
| colon | Insert `:` |
| semicolon | Insert `;` |
| open quote | Insert opening quotation mark |
| close quote | Insert closing quotation mark |
| open parenthesis | Insert `(` |
| close parenthesis | Insert `)` |
| open bracket | Insert `[` |
| close bracket | Insert `]` |
| dash | Insert configured dash |
| hyphen | Insert `-` |
| new page | Optional future editor action |
| scratch that | Remove last dictated transaction |
| delete that | Remove last dictated transaction |
| undo that | Invoke QUILL undo |
| stop dictation | Stop the current dictation session |
| literal ... | Insert the following command-like phrase literally |

The command vocabulary should be implemented in one data-driven location so it can be expanded without rewriting the recognition layer.

---

# 10. Literal Escape

Some command phrases can also occur in ordinary prose.

For example:

> There is a new line of products coming out.

QUILL must avoid changing every occurrence of "new line" into a line break.

At minimum, QUILL should support an explicit escape phrase:

> **literal new line**

which inserts:

```text
new line
```

rather than performing the command.

The parser should be designed so future versions can use more sophisticated contextual rules.

---

# 11. Command Parsing Strategy

The parser should not be implemented as a series of uncontrolled global string replacements.

Recommended approach:

1. Normalize recognized text.
2. Tokenize into words and recognized command phrases.
3. Match the longest known command phrase first.
4. Respect `literal` escape mode.
5. Produce editor actions rather than directly modifying the text control.
6. Execute those actions through QUILL's editor abstraction.

Example action objects:

```python
InsertText("Hello everyone")
InsertPunctuation(".")
NewParagraph()
InsertText("Welcome to QUILL Lite")
InsertPunctuation(".")
```

This architecture keeps recognition, parsing, and editor manipulation independent.

---

# 12. Dictated Phrase Transactions

Every finalized phrase should be treated as a transaction.

Suggested representation:

```python
from dataclasses import dataclass

@dataclass
class DictatedPhrase:
    original_recognition: str
    inserted_text: str
    start_position: int
    end_position: int
    timestamp: float
```

This allows QUILL to implement:

> scratch that

without guessing or sending simulated keystrokes.

If the last phrase occupied characters 582 through 641, QUILL can remove exactly that transaction.

This is safer than synthesizing Ctrl+Z and allows QUILL to keep normal undo semantics intact.

---

# 13. Undo Behavior

Each finalized dictated phrase should normally create one undo unit.

Example:

```text
Phrase 1
Phrase 2
Phrase 3
```

Pressing Ctrl+Z once should remove Phrase 3.

The implementation must integrate with QUILL's existing editor undo stack where possible.

`scratch that` may either:

- remove the last dictation transaction directly; or
- call an editor-specific transaction undo operation.

It should not blindly send keyboard shortcuts.

---

# 14. Text Selection Behavior

If text is selected when dictation starts:

- the first inserted dictated content should replace the selection;
- the caret should remain at the end of the inserted content;
- subsequent phrases should continue from that location.

QUILL must use the normal editor APIs rather than clipboard injection.

---

# 15. Spacing and Punctuation Rules

QUILL must normalize phrase boundaries carefully.

It must avoid:

```text
Sentence one.Sentence two.
```

and:

```text
Sentence one.   Sentence two.
```

The insertion layer should determine whether a space is required based on:

- the preceding character;
- the next character;
- punctuation;
- paragraph boundaries;
- command output.

Examples:

- no space before comma;
- one space after a completed sentence when continuing the same paragraph;
- no extra space immediately after a new line;
- no extra space before closing punctuation;
- no unintended trimming of the user's existing text.

---

# 16. Structural and Formatting Commands

QUILL Dictation must understand document structure and formatting, not merely plain text and punctuation.

These commands are part of the MVP.

The dictation layer should express user intent semantically and allow the active QUILL editor/document type to determine the actual representation.

For example:

> make that heading 2

means:

> Apply semantic Heading Level 2 formatting to the target paragraph.

It does **not** mean:

> Type two hash characters.

This distinction allows the same spoken command to work correctly in Markdown and rich-text documents.

---

# 31. Bold Commands

The MVP should support both prospective and retrospective bold formatting.

## Prospective

Spoken:

```text
start bold
accessibility matters
stop bold
```

QUILL produces a bold-formatted phrase.

## Retrospective

Spoken:

```text
accessibility matters
bold that
```

or:

```text
make that bold
```

QUILL applies bold to the most recent dictated phrase or current selection according to targeting rules.

Supported commands:

```text
start bold
stop bold
bold that
make that bold
```

---

# 32. Underline Commands

The MVP should support:

```text
start underline
stop underline
underline that
make that underlined
```

For rich text, QUILL should apply actual underline character formatting.

Markdown has no universal native underline syntax.

Default Markdown behavior should therefore be:

> Underline is not available in Markdown.

QUILL may later offer an advanced option to emit HTML such as:

```html
<u>underlined text</u>
```

but this should not be the default.

---

# 33. Heading Commands

QUILL Dictation must support Heading 1 through Heading 6.

Accepted forms should include:

```text
heading 1
heading one
heading 2
heading two
heading 3
heading three
heading 4
heading four
heading 5
heading five
heading 6
heading six
```

Retrospective forms should include:

```text
make that heading 1
make that heading one
make that heading 2
make that heading two
...
make that heading 6
make that heading six
```

The normal target should be the current or most recently dictated paragraph.

For Markdown:

```text
Heading 1 → # Heading
Heading 2 → ## Heading
Heading 3 → ### Heading
Heading 4 → #### Heading
Heading 5 → ##### Heading
Heading 6 → ###### Heading
```

For rich text:

```text
Heading 1 → semantic Heading 1 paragraph style
Heading 2 → semantic Heading 2 paragraph style
...
Heading 6 → semantic Heading 6 paragraph style
```

The user should not need to know the underlying syntax.

---

# 34. Bulleted Lists

QUILL Dictation must provide a conversational list mode.

Supported start commands:

```text
start bulleted list
start bullet list
begin bulleted list
begin bullet list
```

Within an active list:

```text
next item
```

ends the current item and starts the next.

To leave the list:

```text
end list
stop list
```

Example:

```text
start bulleted list
accessibility testing
next item
documentation
next item
screen reader support
end list
```

Markdown result:

```markdown
- Accessibility testing
- Documentation
- Screen reader support
```

Rich-text result:

- a real semantic bulleted list;
- not manually typed decorative bullet characters.

Retrospective conversion should also be supported:

```text
make that a bulleted list
make those a bulleted list
```

where the target is a current selection or recent dictated block.

---

# 35. Numbered Lists

Supported commands:

```text
start numbered list
start number list
begin numbered list
begin number list
next item
end list
stop list
```

Example:

```text
start numbered list
install QUILL
next item
open the editor
next item
start dictation
end list
```

Markdown result:

```markdown
1. Install QUILL
2. Open the editor
3. Start dictation
```

Rich-text result:

- a semantic ordered list;
- not manually typed number strings.

Retrospective forms:

```text
make that a numbered list
make those a numbered list
```

---

# 36. Prospective and Retrospective Commands

QUILL should support both ways of working.

## Prospective

The user announces formatting first:

```text
start bold
important text
stop bold
```

## Retrospective

The user dictates first and formats afterward:

```text
important text
make that bold
```

Retrospective commands are especially important because users often decide how something should be formatted only after hearing or reviewing what they dictated.

The MVP should prioritize natural retrospective forms such as:

```text
make that bold
make that underlined
make that heading 2
make that a bulleted list
make that a numbered list
```

---

# 37. Formatting State

The Dictation Controller should maintain a small semantic formatting context.

Conceptually:

```python
@dataclass
class DictationContext:
    bold: bool = False
    underline: bool = False
    list_type: str | None = None
    heading_level: int | None = None
```

Spoken commands modify semantic state.

Example:

```text
start bold
    ↓
SetFormatting(bold=True)

this is important
    ↓
InsertText("This is important")

stop bold
    ↓
SetFormatting(bold=False)
```

The speech recognizer must not be responsible for document formatting.

---

# 38. Semantic Editor Actions

The command parser should emit high-level editor operations.

Examples:

```python
InsertText("Accessibility matters")
InsertPunctuation(".")
NewLine()
NewParagraph()

BeginBold()
EndBold()
ApplyBoldToTarget()

BeginUnderline()
EndUnderline()
ApplyUnderlineToTarget()

ApplyHeading(level=2)

BeginList(kind="bullet")
BeginList(kind="numbered")
NextListItem()
EndList()

ConvertTargetToList(kind="bullet")
ConvertTargetToList(kind="numbered")
```

The active editor/document adapter determines how these actions are represented.

This provides a consistent voice interface across document types.

---

# 39. Markdown Behavior

For Markdown documents, semantic actions should produce conventional Markdown.

Examples:

```text
Bold          → **text**
Heading 1     → # Heading
Heading 2     → ## Heading
Bulleted list → - Item
Numbered list → 1. Item
```

QUILL should preserve valid Markdown structure.

Dictation should not require users to speak Markdown punctuation explicitly.

A user says:

> make that heading 2

not:

> insert two pound signs.

---

# 40. Rich-Text Behavior

For rich-text documents, QUILL must use the document/editor's actual semantic formatting operations.

Examples:

```text
Bold          → bold character formatting
Underline     → underline character formatting
Heading 1     → Heading 1 paragraph style
Heading 2     → Heading 2 paragraph style
Bulleted list → semantic unordered list
Numbered list → semantic ordered list
```

QUILL should avoid visual-only formatting when a semantic structure exists.

For headings, paragraph styles are preferred over merely increasing font size or weight.

---

# 41. Target Resolution for "That"

Commands such as:

```text
bold that
scratch that
make that heading 2
make that a numbered list
```

require predictable target resolution.

Recommended target priority:

1. current explicit selection, if one exists;
2. most recent dictated transaction;
3. most recent dictated paragraph when the command is paragraph-structural;
4. current paragraph as a controlled fallback.

Examples:

- `bold that` targets the selection or most recent dictated phrase;
- `make that heading 2` targets the selection's paragraph or most recent dictated paragraph;
- `make that a bulleted list` targets selected/recent paragraphs.

Target behavior must be consistent and documented.

---

# 42. List State

The Dictation Context should track active list mode.

Example:

```python
list_type = None
list_type = "bullet"
list_type = "numbered"
```

When list mode is active:

- dictated phrase text belongs to the current list item;
- `next item` commits the current item and starts the next;
- `end list` exits the list and returns to normal paragraph mode.

If the user says `new paragraph` while in a list, QUILL must define the behavior clearly.

Recommended MVP behavior:

- `next item` creates the next list item;
- `new line` inserts a line break within the current list item;
- `new paragraph` exits the list and begins a normal paragraph;
- `end list` explicitly exits the list.

This gives each command a distinct meaning.

---

# 43. Expanded MVP Command Vocabulary

The required MVP command set now includes:

## Text and spacing

```text
new line
newline
new paragraph
tab
literal ...
```

## Punctuation

```text
comma
period
full stop
question mark
exclamation point
exclamation mark
colon
semicolon
open quote
close quote
open parenthesis
close parenthesis
open bracket
close bracket
hyphen
dash
```

## Correction

```text
scratch that
delete that
undo that
```

## Bold

```text
start bold
stop bold
bold that
make that bold
```

## Underline

```text
start underline
stop underline
underline that
make that underlined
```

## Headings

```text
heading 1
heading one
...
heading 6
heading six
make that heading 1
...
make that heading 6
```

## Bulleted lists

```text
start bulleted list
start bullet list
begin bulleted list
next item
end list
stop list
make that a bulleted list
```

## Numbered lists

```text
start numbered list
start number list
begin numbered list
next item
end list
stop list
make that a numbered list
```

## Session

```text
stop dictation
```

---

# 30. Recognition Architecture

Recommended pipeline:

```text
Microphone
    ↓
Windows Speech Recognition
    ↓
Python WinRT binding
    ↓
windows_recognizer.py
    ↓
Dictation Controller
    ↓
Command Parser
    ↓
EditorAction objects
    ↓
QUILL editor abstraction
    ↓
Commit earcon
```

The editor itself should not contain Windows speech API code.

---

# 31. Recommended Python Package Layout

Suggested structure:

```text
quill/
  dictation/
    __init__.py
    controller.py
    windows_recognizer.py
    commands.py
    actions.py
    phrase_history.py
    sounds.py
    settings.py
    document_adapter.py
```

Responsibilities:

## `controller.py`

Owns the dictation state machine.

Responsibilities include:

- start;
- stop;
- session lifecycle;
- error handling;
- interaction with current editor;
- phrase commit;
- earcons.

## `windows_recognizer.py`

Owns Windows speech API interaction.

It should expose clean callbacks such as:

```python
on_started()
on_result(text, confidence)
on_error(error)
on_stopped()
```

## `commands.py`

Converts recognized language into semantic editor actions.

## `actions.py`

Defines actions such as:

```python
InsertText
InsertPunctuation
NewLine
NewParagraph
ScratchThat
Undo
StopDictation
```

## `phrase_history.py`

Tracks committed dictation transactions.

## `sounds.py`

Loads and plays earcons.

## `settings.py`

Contains dictation-specific settings and defaults.

---

# 32. Windows Speech Dependency Strategy

The preferred implementation is Microsoft's Windows Runtime speech-recognition API exposed to Python through PyWinRT packages.

Expected dependencies are approximately:

```text
winrt-runtime
winrt-Windows.Foundation
winrt-Windows.Globalization
winrt-Windows.Media.SpeechRecognition
```

Additional small WinRT namespace packages may be pulled transitively depending on the exact implementation.

These dependencies are bindings to Windows APIs, not speech models.

The final dependency list should be confirmed during the engineering spike and pinned in the QUILL Lite dependency lock file.

---

# 33. Dependencies Explicitly Not Required for MVP

Do not add the following solely for basic dictation unless the architecture changes after testing:

```text
SpeechRecognition
PyAudio
Whisper
openai-whisper
faster-whisper
Torch
ONNX Runtime
Vosk
NumPy
FFmpeg
```

The objective is to avoid turning a basic convenience feature into a large AI runtime.

---

# 34. Python Packaging

The speech components must be tested in the same packaged environment used by QUILL Lite.

If QUILL Lite uses PyInstaller, validation must include:

- PyInstaller discovery of WinRT modules;
- required hidden imports;
- native DLL inclusion;
- x64 build;
- ARM64 build if QUILL Lite supports ARM64;
- installer upgrade;
- installer repair;
- uninstall;
- clean Windows installation.

Any PyInstaller hooks required for PyWinRT must be documented in the repository.

---

# 35. Windows Package Identity

The chosen Windows speech-recognition API may require Windows package identity.

QUILL Lite should retain its existing desktop installer architecture and investigate a lightweight identity package registered during installation.

Conceptual installer layout:

```text
QUILL-Lite-Setup.exe
    |
    +-- Normal QUILL Lite files
    |
    +-- Python/WinRT dependencies
    |
    +-- Dictation earcons
    |
    +-- Lightweight Windows package identity
```

The package-identity work is a required technical spike before production commitment.

The goal is **not** to force QUILL Lite into a Microsoft Store-only deployment model.

---

# 36. State Machine

Recommended states:

```text
OFF
 |
 | start
 v
STARTING
 |
 v
LISTENING
 |
 | speech detected
 v
RECOGNIZING
 |
 | finalized result
 v
PROCESSING
 |
 | applied to document
 v
COMMITTED
 |
 +-------------------> LISTENING
 |
 | stop
 v
STOPPING
 |
 v
OFF
```

Any unrecoverable error should return safely to `OFF`.

The microphone must never remain active when QUILL believes dictation has stopped.

---

# 37. Earcons

QUILL should ship with four short nonverbal sounds.

## 23.1 Start Earcon

Meaning:

> Dictation is listening.

Recommended design:

- two short ascending tones;
- approximately 150–250 ms total;
- positive but subtle.

## 23.2 Commit Earcon

Meaning:

> The recognized phrase has been successfully applied to the document.

This is the most frequently heard sound.

Recommended design:

- extremely short;
- gentle;
- approximately 40–80 ms;
- not a harsh click;
- lower volume than Start and Stop.

The Commit earcon must play **after** the editor action succeeds.

## 23.3 Stop Earcon

Meaning:

> Dictation is no longer listening.

Recommended design:

- two short descending tones;
- approximately 150–250 ms total.

## 23.4 Error Earcon

Meaning:

> Dictation requires attention or could not continue.

Recommended design:

- short double pulse or low-low tone;
- clearly different from the other three;
- not startling.

---

# 38. Sound File Format

Recommended bundled format:

```text
WAV
PCM
16-bit
mono
44.1 kHz
```

Reasons:

- universally supported by Windows;
- tiny at these durations;
- no codec dependency;
- easy to generate;
- easy to play from Python.

The sounds should be stored as application resources, for example:

```text
resources/
  sounds/
    dictation-start.wav
    dictation-commit.wav
    dictation-stop.wav
    dictation-error.wav
```

---

# 39. Playing Sounds in Python

On Windows, the standard-library `winsound` module is sufficient for WAV playback.

Example:

```python
import winsound

winsound.PlaySound(
    "resources/sounds/dictation-commit.wav",
    winsound.SND_FILENAME | winsound.SND_ASYNC
)
```

This adds no third-party audio dependency.

If QUILL already has a central sound service, dictation should use that service instead.

---

# 40. Generating the Earcons

QUILL should keep sound generation reproducible.

The repository should contain a script:

```text
tools/generate_dictation_sounds.py
```

The script should use only the Python standard library.

This has several advantages:

- no audio editor is required;
- every developer can regenerate the exact assets;
- tones can be adjusted through constants;
- source generation is auditable;
- binary WAV files do not become mysterious hand-created assets.

A reference generator is included with this PRD.

Run:

```text
python generate_dictation_sounds.py
```

It produces:

```text
dictation-start.wav
dictation-commit.wav
dictation-stop.wav
dictation-error.wav
```

---

# 41. Sound Design Guidance

Earcons must work well with speech output.

Avoid:

- long sounds;
- speech clips;
- high-volume beeps;
- extremely high frequencies;
- tones that mask a screen reader;
- sounds easily confused with Windows system alerts.

Suggested frequency area:

```text
400 Hz – 1200 Hz
```

Suggested peak level:

- comfortably below full-scale;
- Commit softer than Start/Stop;
- Error distinct but not dramatically louder.

The generated examples intentionally use simple sine tones with short fades to prevent audible clicks.

---

# 42. Earcon Accessibility Settings

Initial settings:

```text
Dictation Sounds

[x] Start sound
[x] Phrase committed sound
[x] Stop sound
[x] Error sound

Volume:
System/application default
```

Future versions may support individual volume levels.

Users must be able to disable earcons without losing access to dictation status through menus or screen-reader announcements.

---

# 43. Screen Reader Announcements

Optional announcements may include:

```text
Dictation on
Dictation off
Dictation unavailable
```

Do not announce:

```text
Listening
Listening
Listening
Recognizing
Recognizing
```

during normal continuous operation.

The user should not be flooded with status messages between phrases.

The Commit earcon is intended to provide lightweight phrase-completion feedback.

---

# 44. Microphone Selection

MVP:

> Use the Windows default input microphone.

Do not create a complex microphone-management interface unless testing shows it is necessary.

Future versions may offer explicit device selection.

If no microphone is available, provide an accessible error message and return to the `OFF` state.

---

# 45. Privacy

QUILL itself should:

- not record speech to WAV files during normal dictation;
- not retain microphone audio;
- not upload audio to a QUILL server;
- not write recognized text to diagnostic logs by default;
- not include dictated text in telemetry;
- document when the selected Windows speech service uses online processing.

Diagnostic logging must redact or omit recognized content unless the user explicitly enables a developer diagnostic mode.

---

# 46. Network Behavior

QUILL must not assume that all Windows speech modes are offline.

Engineering must explicitly test and document:

- whether the selected recognizer requires Internet access;
- what happens when connectivity is lost;
- whether recognition language packs affect behavior;
- whether Windows settings affect availability.

If an Internet connection is required and unavailable, QUILL must report the condition clearly.

---

# 47. Wake Word — Phase Two

A future hands-free mode should support a phrase such as:

> Quill dictate

Potential stop phrase:

> Quill stop dictation

Wake-word detection should be separate from full transcription.

This allows QUILL to use a very small keyword-spotting implementation rather than keeping a large speech-to-text model running continuously.

Requirements:

- optional;
- disabled by default initially;
- very low idle CPU use;
- very small model/resource size;
- clearly indicated microphone state;
- configurable activation phrase if technically practical.

Preferred operating modes:

1. wake word only while QUILL is active;
2. optionally, wake word while QUILL is running in the background.

The second mode should require explicit user opt-in.

---

# 48. Windows Voice Typing Compatibility Option

Windows Voice Typing (`Win+H`) may be investigated as a fallback or compatibility feature.

It should not be the primary architecture because QUILL would have limited control over:

- phrase-result events;
- recognition lifecycle;
- error state;
- commit timing;
- UI behavior.

If implemented, it should be labeled clearly as:

> Use Windows Voice Typing

rather than being presented as QUILL-native dictation.

---

# 49. Windows Voice Access Compatibility

QUILL should coexist cleanly with Windows Voice Access.

Voice Access users should still be able to dictate and control Windows normally.

QUILL should not depend on Voice Access for its internal phrase lifecycle.

Where possible, test simultaneous or alternating use so the user does not end up with two microphone systems fighting over state.

---

# 50. Settings

Keep settings deliberately small.

Suggested initial dialog:

```text
Dictation

Keyboard shortcut:
[ configurable ]

Language:
[ System Default ]

Sounds:
[x] Start sound
[x] Phrase committed sound
[x] Stop sound
[x] Error sound

Screen reader announcements:
[x] Announce dictation on and off

Microphone:
System default

Wake word:
[ ] Enable wake word
    Future feature
```

The feature must work well without requiring the user to open this dialog.

---

# 51. Error Handling

QUILL must provide accessible handling for:

- no microphone;
- microphone permission denied;
- Windows speech recognition unavailable;
- unsupported language;
- missing Windows speech resources;
- Internet unavailable when required;
- recognizer initialization failure;
- recognizer unexpectedly stopping;
- microphone disconnected;
- document read-only;
- editor unavailable;
- package identity registration failure.

Failure must never:

- corrupt document contents;
- crash QUILL;
- leave the microphone active unexpectedly;
- move focus to an inaccessible control;
- silently fail.

---

# 52. Performance Requirements

Target behavior:

- start-to-listening feels immediate;
- approximately one second or less under normal conditions;
- phrase commit occurs as soon as a finalized result is available;
- Commit earcon occurs immediately after insertion;
- negligible CPU use while dictation is off;
- no noticeable editor lag on low-end supported machines.

Wake-word mode, if added, must also have low idle resource use.

---

# 53. Accessibility Requirements

The feature must be fully operable:

- without a mouse;
- without vision;
- without color;
- with screen readers;
- with magnification;
- using the keyboard alone.

Starting dictation must not:

- open an unnecessary floating window;
- steal editor focus;
- move the caret;
- require mouse interaction.

The current dictation state must be exposed programmatically through the menu/status UI.

---

# 54. Visual Status

QUILL may show a nonmodal status such as:

```text
Dictation: Off
Dictation: Listening
Dictation: Recognizing
Dictation: Unavailable
```

This display must not receive focus during normal dictation.

Visual presentation is secondary to keyboard, sound, and accessible programmatic state.

---

# 55. Non-Goals for Version One

Version One will not attempt to provide:

- full computer voice control;
- Dragon-style macro systems;
- speaker identification;
- meeting transcription;
- audio-file transcription;
- multi-speaker transcription;
- translation;
- AI rewriting;
- voice cloning;
- custom acoustic model training;
- a full natural-language editor agent.

These capabilities should not delay basic dictation.

---

# 56. Technical Spike

Before full production development, implement a minimal proof of concept.

It must answer the following questions.

## 42.1 Recognition

Can Python successfully use the selected Windows speech-recognition API through PyWinRT?

## 42.2 Accuracy

Is conversational dictation accurate enough for real QUILL users?

Test:

- ordinary prose;
- technical terminology;
- accessibility terminology;
- names;
- punctuation commands.

## 42.3 Continuous Results

Do finalized phrase boundaries feel natural for:

> speak → pause → commit → continue?

## 42.4 Latency

How quickly does the recognizer finalize a phrase after a natural pause?

## 42.5 Package Identity

Can the existing QUILL Lite installer reliably install and register any required Windows package identity?

Test:

- clean install;
- upgrade;
- repair;
- uninstall;
- reinstall.

## 42.6 PyInstaller

Can the WinRT packages be bundled reliably with the current Python packaging toolchain?

## 42.7 Screen Readers

Test with:

- JAWS;
- NVDA;
- Narrator.

Confirm:

- no focus theft;
- no repeated unwanted announcements;
- correct editing feedback;
- no keyboard conflicts.

## 42.8 Machine Classes

Test at least:

- lower-end supported Windows PC;
- typical office laptop;
- high-performance desktop;
- ARM64 Windows device if QUILL Lite supports ARM64.

---

# 57. Accuracy Test Vocabulary

The test corpus should intentionally include words commonly important to QUILL users:

```text
QUILL
QUILL Lite
Quillbert
JAWS
NVDA
Narrator
VoiceOver
WCAG
accessibility
GitHub
Markdown
Python
PowerShell
Microsoft
Windows
screen reader
new line
new paragraph
```

The tests must also determine whether command phrases can be distinguished reliably from literal prose.

---

# 58. MVP Acceptance Criteria

The MVP is complete when:

1. Dictation installs as part of QUILL Lite.
2. No separate large speech model download is required.
3. A configurable keyboard command starts dictation.
4. A Start earcon confirms listening.
5. The active editor keeps focus.
6. Speech is recognized continuously.
7. A natural pause produces a finalized phrase.
8. QUILL parses supported command phrases.
9. `new line` works.
10. `new paragraph` works.
11. Basic punctuation commands work.
12. `literal ...` prevents command interpretation.
13. `start bold`, `stop bold`, `bold that`, and `make that bold` work.
14. Underline commands work in supported rich-text documents and fail accessibly in Markdown.
15. Heading 1 through Heading 6 commands work semantically.
16. `make that heading N` works for the current/recent target.
17. Bulleted-list dictation mode works.
18. Numbered-list dictation mode works.
19. `next item` advances to the next list item.
20. `end list` exits list mode predictably.
21. `make that a bulleted list` works for a supported target.
22. `make that a numbered list` works for a supported target.
23. QUILL applies semantic editor actions appropriate to Markdown or rich text.
24. A Commit earcon plays only after successful application.
25. The user can immediately continue speaking.
26. `scratch that` removes the last dictated transaction.
27. Normal undo continues to work.
28. The keyboard command stops dictation.
29. `stop dictation` can stop the session if reliable.
30. A Stop earcon confirms that listening ended.
31. Errors are exposed accessibly.
32. JAWS, NVDA, and Narrator work without focus disruption.
33. Low-end supported systems remain responsive.
34. QUILL does not retain microphone recordings.
35. QUILL does not log dictated text by default.
36. Dictation failure cannot damage the document.

---

# 59. Phase Two

After MVP stabilization, evaluate:

- lightweight wake-word detection;
- user-defined vocabulary;
- user-defined spoken commands;
- explicit microphone selection;
- additional punctuation;
- capitalization commands;
- advanced selection commands;
- spelling mode;
- offline recognition alternatives;
- macOS native speech adapter.

Potential commands include:

```text
capitalize that
all caps that
select that
delete word
delete sentence
go to end of line
go to beginning of line
```

These should be added only after the basic experience remains predictable.

---

# 60. Recommended Implementation Order

## Milestone 1 — Python Speech Spike

Use PyWinRT to receive finalized recognition results.

## Milestone 2 — Command Parser

Implement:

- new line;
- new paragraph;
- punctuation;
- literal escape.

## Milestone 3 — Editor Actions

Apply parsed actions through QUILL's editor abstraction.

## Milestone 4 — Phrase Transactions

Track committed phrases and implement `scratch that`.

## Milestone 5 — Continuous Session

Keep recognition active across pauses.

## Milestone 6 — Earcons

Add Start, Commit, Stop, and Error sounds.

## Milestone 7 — Accessibility

Perform JAWS, NVDA, and Narrator testing.

## Milestone 8 — Packaging

Complete PyInstaller and installer/package-identity integration.

## Milestone 9 — Settings and Failure Handling

Add shortcut configuration, sounds, language, announcements, and diagnostics.

## Milestone 10 — Wake-Word Prototype

Evaluate a lightweight keyword-spotting solution independently from transcription.

---

# 61. Repository Deliverables

Suggested repository changes:

```text
quill/
  dictation/
    __init__.py
    controller.py
    windows_recognizer.py
    commands.py
    actions.py
    phrase_history.py
    sounds.py
    settings.py

resources/
  sounds/
    dictation-start.wav
    dictation-commit.wav
    dictation-stop.wav
    dictation-error.wav

tools/
  generate_dictation_sounds.py

docs/
  quill-lite-dictation-prd.md
```

---

# 62. Recommended Decision

Proceed first with a small Windows/Python technical spike using:

> **Python + PyWinRT + Windows speech recognition + QUILL command parser + QUILL editor transactions + standard-library WAV earcons**

Do not add a large embedded speech model until this approach has been tested and shown to be insufficient.

The desired production experience remains:

> **Start dictation, speak naturally, pause, hear the commit sound, and keep talking.**

QUILL should own the editing intelligence while Windows provides the speech recognition.
