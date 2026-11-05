# Chapter 3: Your first project task

## What this chapter covers

This chapter walks through one whole project task, from an empty practice
folder to an undone turn, and says what you hear at each step. It works the
same in QUILL and QUILL Lite. Allow about fifteen minutes. If you would rather
be guided inside the editor, the lesson **Your first project task** in **Help
> Tutorials...** (`Ctrl+Alt+F1`) covers the same ground.

## Before you start

You need three things:

- **The Developer profile,** or Developer Tools (QUILL) or Coding (QUILL Lite)
  checked on its own. In QUILL Lite, check **AI help** as well. Chapter 1 has
  the details.
- **An AI that can run tasks,** chosen in **Choose Your AI** (`Ctrl+4`): My
  GitHub Copilot, Codex, or My own key with Anthropic Claude or Ollama on this
  computer. QUILL's free AI does not run tasks. Chapter 4 helps you choose.
- **A practice folder.** Use a copy, not your real work, the first time.
  Undo Last Turn puts files back, but practising on a copy costs nothing.

## Step 1: make a practice folder

Make an empty folder, for example `cli-tool`, and put one small file of code
in it with a mistake. A Python file is easiest:

```python
def add(a, b):
    return a - b
```

Save it as `calc.py`. If you want the agent to have tests to run, add a
second file, `test_calc.py`:

```python
import unittest
from calc import add


class AddTests(unittest.TestCase):
    def test_add(self):
        self.assertEqual(add(2, 3), 5)


if __name__ == "__main__":
    unittest.main()
```

## Step 2: open the folder as a project

Choose **File > Open Project Folder...**, then **Browse for a Folder...**, and
pick the folder.

You hear: "Project cli-tool is open." The status bar's Project part now names
it.

## Step 3: open the task window and ask

Press `Ctrl+3`. With a project open, it opens **Do a Project Task**. Focus is
in **Instruction**. Type one plain request:

> Fix the add function and run the tests.

and press Enter.

If your folder has notes for AI agents, such as an `AGENTS.md`, QUILL asks
once first, in **Use This Project's Agent Notes?** Chapter 8 explains the
choices. A practice folder has none, so this does not appear.

You hear nothing at first. The conversation fills in quietly, and the status
line says "Working". QUILL does not read streaming text at you.

## Step 4: read the plan

Before it changes anything, the agent records its plan as numbered steps.
You hear "The plan is ready. 3 steps." Focus does not move.

Press `Alt+P`. The cursor lands on the plan in the conversation, under a line
that says "Plan:". Read it with the arrow keys. Nothing has changed yet. If
you want something different, type it in Instruction, for example "don't
touch the tests", and press Enter.

## Step 5: review the change

The agent reads `calc.py` (reading needs no permission) and proposes an edit.
Proposed changes are not written. Before a command runs, and when a turn
ends with changes, **Review Changes** opens.

You hear the window's title and the first file's row: "calc.py, changed, 1
change, taken". Every proposed change starts out taken.

Press Enter on the row. Focus moves to **Change details**, which reads:

> calc.py. Change 1 of 1, line 2, in function add. Accepted.

then "In this line: changed - to +.", then the line as it is now and as it
was, each led by its line number.

Press `Alt+A` to Accept or `Alt+R` to Reject. Then press Enter on **Apply
Accepted Changes**, which writes what you accepted at once. Escape, or **Reject
All**, writes nothing.

## Step 6: allow the test command

The agent asks to run the tests. **Run This Command?** opens, with focus on
one sentence:

> Run python -m unittest in your project folder cli-tool, to check the fix.

Tab once to **Command** and arrow through the exact text. Nothing here reaches
the internet or deletes anything, so there is no Warning line. Press Enter for
**Allow once**.

When the command finishes, you hear the result in one sentence: "Tests: 1
passed." The full output is one key away: `Alt+O`.

## Step 7: hear the closing summary

When the turn ends, the closing summary is built from what really happened,
not from what the AI says it did. You hear something like:

> Turn 1. Done. Changed calc.py. Ran 1 command; the last result: Tests: 1
> passed. Undo Last Turn puts every file back.

## Step 8: undo the whole turn

Press `Alt+U`, Undo Last Turn. You hear "Undid turn 1. calc.py is back as it
was." The mistake is back, so you can try again.

The same works with the task window closed: **Edit > Agent Work > Undo Last
Agent Turn**, which in QUILL is also `Ctrl+Shift+Grave, U`.

## Step 9: try coach mode

Check **Coach mode** (`Alt+A`) and ask:

> How do I fix the add function myself?

In coach mode the agent changes nothing and runs nothing. It explains and
points you to a place, such as "Look at calc.py line 2: the operator is a
minus." You make the change yourself in the editor. Chapter 9 has more.

## Stopping at any point

**Stop** (`Alt+T`) in the task window stops the task at once, with any command
it is running. From any other window, choose **Edit > Agent Work > Stop
Agent**; in QUILL that is also `Ctrl+Shift+Grave, K`.

## If you are elsewhere when the task needs you

Nothing pops up over your typing. If you are in another QUILL window when the
task has a question, you hear once "The project task is waiting for you.
Press Ctrl+3 to answer." and the Project part of the status bar adds ",
waiting for you". Press `Ctrl+3` and the question opens. If QUILL is not the
window in front at all, it says nothing.

## That is the whole loop

Every change is reviewed before it is written, every command asks first, and
one command undoes a turn. The rest of this manual is detail on each part.

## Where to next

- Previous: [Chapter 2: Opening a project, and the project boundary](developer-02-projects.html)
- Next: [Chapter 4: Engines, and choosing one](developer-04-engines.html)
- [Contents](developer-guide.html)
