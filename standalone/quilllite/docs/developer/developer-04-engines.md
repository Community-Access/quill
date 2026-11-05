# Chapter 4: Engines, and choosing one

## What this chapter covers

The engine is the AI that does the work: it plans, reads, proposes changes and
asks to run commands. This chapter covers the four that can run a project
task, how to choose one, what each costs and where your text goes, why every
engine behaves the same in front of you, and how to let an engine use its own
tools as well as QUILL's, if you want that.

## Which AI can run a project task

A project task needs an AI that can use tools. In **Choose Your AI**
(`Ctrl+4`), each row's About line ends with "Agent tasks: yes." or "Agent
tasks: no." These say yes:

- **My GitHub Copilot.** Runs on your own Copilot plan, through the GitHub
  Copilot runtime QUILL ships with. "Billed to your Copilot plan."
- **Codex, for tasks.** Runs on your ChatGPT plan, through OpenAI's Codex
  app server. "Runs tasks on your ChatGPT plan."
- **My own key, with Anthropic Claude.** QUILL drives Claude through the
  Claude Agent SDK on your own Anthropic key, which goes only to the SDK's own
  process. Claude's own tools are all turned off; only QUILL's project tools
  are open to it. Billed per request to your own key.
- **My own key, with Ollama on this computer.** Practice mode. QUILL labels it
  "Practice, on this computer. Nothing is sent. Slower and less capable." QUILL
  runs the task loop itself and talks only to Ollama on your own computer.

These say no, and do not run tasks:

- **QUILL's free AI.** It answers questions about a selection, but never runs
  an agent.
- **My ChatGPT plan,** the chat connection. Use **Codex, for tasks** on the
  same plan instead.
- **My own key** with any other provider: OpenAI, Google Gemini, OpenRouter,
  Ollama Cloud or a service of your own. These answer in text only.

If the AI you have chosen cannot run tasks, nothing is sent: QUILL tells you,
and offers to switch.

## Choosing

Press `Ctrl+4`, move to the row you want, and press **Use This**, or **Sign
In...** if you have not signed in yet. For My own key, choose the provider and
model in that row's own window. Your choice applies to Do a Document Task and
Do a Project Task alike.

Some plain advice:

- **Already pay for Copilot?** Start there. It is the main path, and the one
  most tested.
- **Have a ChatGPT plan?** Codex runs tasks on it.
- **Have an Anthropic key?** Claude works well for code, and you pay per
  request.
- **Learning, teaching a class, or want to try without an account?** Ollama
  on this computer. It needs Ollama installed with a model that can use tools,
  and it makes more mistakes. Nothing leaves your computer.

## Every engine behaves the same in front of you

QUILL gives every engine the same project tools, and keeps the engine's own
file and shell tools off. That is what makes the promises in this manual hold
whichever one you choose:

- every change waits in Review Changes before it reaches your disk;
- every command asks first, in the same window, with the same warnings;
- the plan, the result sentences and the closing summary are worded by QUILL,
  not by the engine;
- Undo Last Turn works the same way.

The closing summary is built from QUILL's own record of what happened, never
from what the model says it did.

## How each engine is held

- **Copilot** sees only QUILL's tools. Every other kind of permission it asks
  for is refused and logged.
- **Codex** runs with a read-only sandbox, asks for approval of anything
  untrusted, and has its built-in tools off. Its file changes arrive as a
  unified diff, which goes to Review Changes like any other.
- **Claude** gets QUILL's tools as a set named `quill`. Every one of Claude's
  own tools is denied by name.
- **Ollama** runs in QUILL's own loop, which stops on Stop, on a plain answer,
  or after 60 requests. QUILL refuses to send it to any address but your own
  computer.

A task also stops itself after 40 steps in one turn and asks "The task stopped
after 40 steps. Continue?" Yes carries on; No ends the turn.

## Engine tools, only if you choose

By default the engine uses only QUILL's project tools. If you want, you can
let it use some of its own as well, for one project at a time.

Choose **AI > Engine Tools for This Project...** (in QUILL Lite, **Tools > AI
> Engine Tools for This Project...**), or press `Alt+L` in the task window.
The window lists the engine's own tools, one check box each:

- **GitHub Copilot:** Read files (view), Search file contents (grep), Find
  files by name (glob), Edit files (edit), Run shell commands (bash), Fetch
  web pages (web_fetch) and Search the web (web_search).
- **Codex:** Run commands (Codex's shell) and Change files (Codex's
  apply_patch).
- **Claude:** Read files (Read), Search file contents (Grep), Find files by
  name (Glob), Edit files (Edit and Write), Run shell commands (Bash) and Fetch
  web pages (WebFetch).

Know what you are turning on. The window says it plainly at the top:

> These are the engine's own tools, not QUILL's. QUILL asks you before each
> use, but an engine's own edit tool writes straight to disk without Review
> Changes, and its shell can do anything your account can. Undo Last Turn
> still puts the project's files back. All of them are off until you check
> them, and the choice is kept in QUILL for this project only.

So:

- every tool is off until you check it, for that engine and that project
  only;
- each use still asks you, in **Allow This Step?**, which says "The engine's
  own shell tool:" and what it wants;
- a tool you did not check is refused without asking you, and the refusal is
  logged as something that should not have happened;
- a turn with any of them on says so in the conversation and under the
  transcript's Plan heading: "Also on for this project: GitHub Copilot's own
  tools: ..."

Undo Last Turn still works after an engine's own edit, because QUILL keeps its
copy of the project before the turn first changes anything.

For an engine with no tools of its own to offer, the window does not open and
you hear "This engine offers no tools of its own here." That is what you hear
with Ollama, and, in this version, with Claude on your own key too: its tools
are listed in this chapter but the window does not yet offer them.

## What is never available, whatever you choose

No engine can push to a remote, publish a package, force anything against a
remote or change system settings through QUILL. Chapter 5 has the list.

## Where to next

- Previous: [Chapter 3: Your first project task](developer-03-first-project-task.html)
- Next: [Chapter 5: Permissions, the allow list and the bypass](developer-05-permissions.html)
- [Contents](developer-guide.html)
