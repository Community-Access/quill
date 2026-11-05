# Chapter 2: Opening a project, and the project boundary

## What this chapter covers

A project is a folder. This chapter covers opening one and closing it, the
Project part of the status bar, what changes about `Ctrl+3` while a project
is open, and the boundary: exactly what the agent may see inside your folder,
what it never sees, and how much it reads at a time.

## A project is just a folder

There is nothing to set up and no project file. Any folder will do: a git
repository, a folder of scripts, or a book manuscript. QUILL never writes
anything into the folder to mark it as a project. Everything it keeps about a
project lives in its own data folder in your user profile (Chapter 10 lists
what).

## Opening one

Choose **File > Open Project Folder...**. The **Open Project Folder** window
lists your recent projects first, newest at the top, so the usual case is Down
Arrow and Enter. Each row says the folder's name and then its full path. QUILL
remembers your last ten projects.

To open a folder that is not in the list, choose **Browse for a Folder...**,
which opens the Windows folder picker. The first time, the list says "No
recent projects yet." and focus starts on Browse for a Folder.

When the folder opens you hear "Project cli-tool is open, on branch main.",
or "Project cli-tool is open." when the folder is not a git repository. Here
and all through this manual, cli-tool stands for your own folder's name.

Only one project is open at a time, for every window of the editor. Opening
another closes the first. If a task is still running you hear "A project task
is running. Stop it, or let it finish, before closing the project." and
nothing changes.

## The Project part of the status bar

While a project is open, the status bar has a **Project** part. It says
"Project cli-tool, main", and adds ", waiting for you" when the task has a
question you have not seen yet. Press Enter on it to open the task.

- In QUILL the part is hidden until the first time you open a project; then
  QUILL shows it for you. You can hide it again in **Tools > Customize and
  Support > Status Bar Layout...**.
- In QUILL Lite the part is there only while a project is open, so nobody
  without one ever meets it.

## What changes about Ctrl+3

`Ctrl+3` is the front door to AI tasks in both editors. With a project open,
it opens **Do a Project Task**. With no project open, it is Do a Document
Task, as it always was. One key, one window, and the window's status line
says which project it is working on.

## Closing a project

Choose **File > Close Project**. You hear "The project is closed." and `Ctrl+3`
goes back to Do a Document Task. If a task is running, QUILL asks you to stop
it or let it finish first.

## The project boundary

QUILL, not the AI, decides what the agent may see. These rules hold whichever
engine you use.

### Inside the folder only

Every path the agent names is checked and must stay inside the project folder,
after symbolic links and junctions are followed. QUILL refuses:

- paths that climb out with `..`;
- absolute paths and network (UNC) paths;
- Windows device names, such as `con` or `nul`;
- alternate data streams, such as `file.txt:hidden`.

### Secrets are invisible

Files that look like secrets are never listed, read, searched, copied for
undo, or sent. That includes:

- `.env` files and anything named like one (`.env.local`, `prod.env`);
- keys and certificates: `*.pem`, `*.key`, `*.pfx`, `*.p12`, `*.keystore`,
  `*.jks`, and `id_rsa`, `id_dsa`, `id_ecdsa` and `id_ed25519` files;
- password databases: `*.kdbx` and `*.kdb`;
- files named `credentials...`, `secrets...`, `secret.*`, `*.token`,
  `token.json` and `tokens.json`;
- `.npmrc`, `.pypirc`, `.netrc`, `_netrc`, `.git-credentials` and
  `.htpasswd`;
- everything inside `.ssh`, `.aws`, `.gnupg`, `.azure` and git's own `.git`
  folder.

When a listing skips some, the agent is told how many: "3 files hidden by
QUILL because they look like secrets; ask the person if you need what is in
them." So it knows something is there, and asks you rather than guessing.

On top of that, every excerpt of a file that is sent is scrubbed for keys and
tokens that live in ordinary files.

### Folders that are skipped

Generated and cached folders are never listed or searched: `node_modules`,
`__pycache__`, `.venv`, `venv`, `.mypy_cache`, `.pytest_cache`,
`.ruff_cache`, `.tox`, `.idea` and `.vs`. Files your `.gitignore` ignores are
left out of listings too, and the agent is told how many.

### How much is read at a time

- One read returns at most 400 lines, with line numbers. The agent asks for
  the next range when it needs more, which keeps the cost down on a plan
  that counts requests.
- A listing returns at most 600 entries, and a search at most 200 matches.
- A file bigger than 2 MB is never read whole or searched.
- Pictures, PDFs, archives, programs and other binary files are described
  ("PNG image, 48 KB") and never sent.

### What the agent can do inside the boundary

The agent works only through QUILL's own project tools. It can list files,
read them, search them, read a file's outline (its functions and classes),
read the git branch and changed files, record a plan, ask you a question, and
propose changes: an edit, a new file, a deletion or a rename. It can ask to
run a command. Reading needs no permission. Every change goes to Review
Changes (Chapter 7) and every command asks first (Chapters 5 and 6).

In coach mode the agent keeps only the reading tools, plus one for pointing
you to a file and line (Chapter 9).

## Where to next

- Previous: [Chapter 1: Turning on the Developer profile](developer-01-the-developer-profile.html)
- Next: [Chapter 3: Your first project task](developer-03-first-project-task.html)
- [Contents](developer-guide.html)
