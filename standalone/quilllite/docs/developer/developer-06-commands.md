# Chapter 6: Running commands and reading their output

## What this chapter covers

The agent runs your tests and builds by asking to run a command. This chapter
covers the Run This Command? window line by line, the three warnings, how a
command runs and how long it may take, the one-sentence result you hear, and
the full output as a document you can read at your own pace.

## Run This Command?

When the agent wants to run something, **Run This Command?** opens over the
task window. Focus starts on **What will run**, one sentence that says what,
where and why:

> Run pytest -q tests/test_cli.py in your project folder cli-tool, to check
> the new test.

The reason at the end is the agent's own, in its own words.

Below it, **Command** holds the exact text, as it will run, in a read-only
field. Arrow through it to check every character, or read it on a braille
display. This is the text that runs, so it is the text to check.

If QUILL found a risk, a third field, **Warning**, follows. Then the buttons:

- **Allow once**, the default: Enter runs it.
- **Always allow this command here,** only when there is no warning: runs it
  and adds it to the project's allow list.
- **Don't allow:** Escape. The agent is told, and carries on without it.

The question only opens while you are in the task window. If you are
somewhere else in QUILL, you hear once "The project task is waiting for you.
Press Ctrl+3 to answer." and the question waits for you.

## The three warnings

QUILL, not the AI, reads the command and adds a warning when one applies.
There can be more than one.

- **"This may reach the internet."** For installers and network tools:
  `pip install` and the other Python package tools (`uv`, `poetry`, `pipx`,
  `conda`, `mamba`), `npm install` and its relatives, `npx`, `curl`, `wget`,
  `Invoke-WebRequest`, `Invoke-RestMethod`, `ssh`, `scp`, `ftp`, `git clone`,
  `fetch` and `pull`, `winget`, `choco`, `scoop`, `cargo install`, `go get`,
  `dotnet restore` and `gem install`, and anything with a web address in it.
- **"This deletes files."** For `del`, `erase`, `rm`, `rmdir`, `rd`,
  `Remove-Item`, `Clear-Content`, `unlink`, `git clean` and `git rm`.
- **"This runs outside the project."** For an argument that names a path
  outside the project folder, absolute or climbing out with `..`. The program
  itself does not count, so running your own Python from where it is
  installed does not set it off.

A command with a warning can only be allowed once. It never goes on the allow
list, because a command QUILL warns about is one somebody should look at every
time.

## How a command runs

- **In your project folder,** through the Windows command processor, `cmd`.
  So a command is written the way you would type it at a `cmd` prompt. A
  PowerShell command needs `powershell -Command` in front.
- **With a clean environment:** anything named like a token, secret,
  password, API key, access key or credential is taken out, and so is every
  setting of QUILL's own. Colour output is turned off, and Python is told to
  write UTF-8, so the output reads cleanly.
- **One at a time,** and **Stop** ends it, with every process it started.
- **Output to a file,** never read at you as it arrives.

### Long-running commands

After a command has run for five minutes, QUILL asks "The command has run for
5 minutes. Keep waiting? Choose No to stop it." Yes asks again five minutes
later. No stops the command, and the agent is told.

## The result, in one sentence

When a command finishes, you hear its result in one sentence, and the same
sentence goes in the conversation. QUILL reads the output of the common test
runners and build tools itself:

- **Tests:** pytest, unittest, Jest (and Vitest's summary in the same
  shape), `dotnet test`, `cargo test` and `go test`. You hear, for example,
  "Tests: 12 passed, 1 failed: test_verbose_prints_names." Up to three
  failing names are said, then "and 2 more".
- **Errors:** a Python traceback says where the program stopped and the last
  error line. Compiler errors in the usual `file(line,col): error` and
  `file:line:col: error` shapes are read the same way.
- **A command that was not found** says so plainly, for example "The command
  pytest was not found.", rather than a page of shell text.
- **Anything else** gets the honest fallback: "The command ended with exit
  code 1. The last error line was: ..."

Failures and counts are always spoken, whatever your feedback settings,
because no sound can say "2 failed". The task's sound cues play a different
sound for a pass and a fail, if your sound scheme has them.

When a command fails, the agent is asked to say in one plain sentence what the
error means before it tries a fix.

## The full output

The full output of every command is kept as a read-only document. Open the
last command's:

- `Alt+O`, **Output**, in the task window;
- **View > Agent Command Output** from anywhere, even with the task window
  closed. It opens the newest output kept for the open project.

It opens in the editor like any other document, so you can find in it, read
it by line, bookmark the failing test and read it in braille. With colour
turned off, there are no escape codes in it to wade through.

The agent gets a trimmed copy: the result sentence, the failure lines, and the
end of the output.

## Commands and Undo Last Turn

QUILL keeps its copy of the project before a turn first changes anything, and
that includes a command. So if a command changes files inside the project,
Undo Last Turn puts them back too. What it cannot take back is anything a
command did outside the project or on the internet.

## Where to next

- Previous: [Chapter 5: Permissions, the allow list and the bypass](developer-05-permissions.html)
- Next: [Chapter 7: Reviewing changes, and undoing a turn](developer-07-review-and-undo.html)
- [Contents](developer-guide.html)
