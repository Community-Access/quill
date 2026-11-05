# Chapter 10: The transcript, and what QUILL keeps

## What this chapter covers

A project task is not a stream of chat you have to remember. This chapter
covers the conversation in the task window, the transcript, which is the whole
task as a document with a heading for each turn, how to keep a copy, and
everything QUILL keeps about a project and where.

## The conversation

**Conversation** (`Alt+C`) in the task window is the live, read-only record of
the task: what you asked, the plan, each step, the changes, each command's
result and the closing summary. It fills in quietly; QUILL speaks only the
moments your screen reader cannot know about. Read it with the arrow keys.

Two keys land you in the right place:

- `Alt+P`, **Plan**, puts the cursor on the latest plan. Before there is one
  you hear "There is no plan yet in this task."
- `Alt+H`, **Changes**, puts the cursor on the latest list of changes. Before
  any you hear "No changes have been made in this task yet."

## The transcript

The transcript is the whole task as a Markdown document, made for heading
navigation. Open it:

- `Alt+R`, **Transcript**, in the task window;
- **View > Agent Task Transcript** from anywhere, with the task window open or
  closed.

It opens in the editor like any other document, so find, bookmarks, Read
Aloud and braille all work on it, and your heading keys move through it. Its
shape:

```text
# Project task: Add a --verbose flag to cli.py

Project: cli-tool

## Turn 1: you asked

Add a --verbose flag to cli.py that prints each file as it is processed.

### Plan

1. Read cli.py and its tests.
2. Add the flag to the argument parser.
3. Print each file name when the flag is on.
4. Add a test.

### Changes

- cli.py, changed, 3 changes, taken
- tests/test_cli.py, new file, 24 lines, taken

### Commands

- pytest -q tests/test_cli.py: Tests: 12 passed, 1 failed.

### Result

Turn 1. Done. Changed cli.py and added tests/test_cli.py. ...

## Turn 2: you asked
```

Headings never skip a level. A turn may also have **Questions for you**
(questions the agent asked) and **Where to look** (places coach mode pointed
to), and a coach-mode turn's heading ends "(coach mode)". When any of an
engine's own tools were on, the Plan section says which.

Before the first turn you hear "Nothing has happened in this task yet."

### Keeping a copy

The transcript is kept in QUILL's own data, not in your project. Each new
task window starts a new transcript, and it replaces the one before for that
project. To keep one, open it and use **Save As** to put a copy wherever you
want: beside your project, in your notes, or attached to a bug report.

## The command output

Every command's full output is kept too, one file per command. **Output**
(`Alt+O`) or **View > Agent Command Output** opens the newest. Chapter 6
covers reading it.

## What QUILL keeps, and where

Everything QUILL keeps about a project lives in its own data folder in your
user profile, in a folder of its own for each project, never in the project
folder:

- the list of recent projects, the last ten;
- the transcript of the latest task;
- each command's output;
- the checkpoints for Undo Last Turn, the last 10 turns;
- the project's allowed commands, and whether Run commands without asking is
  on;
- your answer about the project's agent notes;
- the engine tools you checked, per engine.

Nothing is added to your repository unless you save something there yourself.
That is also why a project you clone can never bring its own allowed commands
or engine tools with it.

A damaged settings file for a project reads as the safe default: no allowed
commands, the bypass off, and every engine tool off.

## Where to next

- Previous: [Chapter 9: Coach mode and explanations](developer-09-coach-mode.html)
- Next: [Chapter 11: Code editing in the editor itself](developer-11-code-editing.html)
- [Contents](developer-guide.html)
