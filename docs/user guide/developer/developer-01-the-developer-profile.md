# Chapter 1: Turning on the Developer profile

## What this chapter covers

Nothing in this manual appears until you ask for it. This chapter shows you
how to turn the coding tools on in QUILL and in QUILL Lite, what the
Developer profile changes area by area, how to get the tools without the rest
of the profile, and what happens when you turn them off again.

## Why there is a profile at all

Most people who use QUILL write letters, posts and books. They never need a
project task, a command runner or a test summary, and meeting one in a menu
would only be one more thing to skip past. So the coding tools live behind
one choice: the **Developer** profile. Choosing it is the opt-in. No feature
asks you again whether you want developer tools, and nobody else meets any
of them: not in the menus, not in the Command Palette, and not in the
tutorials.

Both editors use the same words for it, and the profile's description is the
same promise in both: everything in the everyday set, plus tools for writing
code, with project tasks with an AI, running commands and tests, and undo for
every change an AI makes.

## Turning it on in QUILL

Any of these does it:

- **Help > Feature Profiles > Switch Profile...** (`Alt+Shift+P`), then
  choose **Developer** from the list.
- **Tools > Customize and Support > Profiles and Features...**, then choose
  **Developer**.

The profile used to be called Developer and Power Text. Your saved settings
still know it by its old id, so nothing you set before is lost.

**Full Quill** turns the coding tools on too, because its promise is
everything.

### Only the coding tools, without the rest of the profile

If you like your current profile and only want the coding tools, open **Help >
Feature Profiles > Manage Individual Features...** (`Ctrl+Alt+F10`) and check
**Developer Tools**. That one feature carries every developer tool in QUILL,
and each of them depends on it, so a profile can never half turn them on by
accident.

## Turning it on in QUILL Lite

Open **Tools > Customize Features...** (`Ctrl+Alt+F10`) and choose the
**Developer** profile. It is Recommended plus one area, **Coding: project
tasks with an AI**: twenty of the 24 areas.

To keep your current profile and add coding alone, check **Coding: project
tasks with an AI** in the same window.

Coding is off in every other QUILL Lite profile, Everything included.
Everything means every *writing* area; coding belongs to Developer.

### One more check box in QUILL Lite: AI help

Project tasks are AI tasks, and in QUILL Lite every AI command, Do a Document
Task (`Ctrl+3`) and Choose Your AI (`Ctrl+4`) included, belongs to the area
called **AI help (sends your text to QUILL's servers)**. The Developer profile
leaves that area off, as Recommended does. So in QUILL Lite, check **AI help**
in Customize Features as well. Until you do, a project task says "AI help is
switched off. Turn it on in Tools, Customize Features."

The area's name talks about QUILL's servers because that is where the free AI
sends your text. A project task never runs on the free AI. With GitHub
Copilot, Codex or your own key, your text goes to that service and not to
QUILL's.

## In QUILL, Use Artificial Intelligence must be on

QUILL has one switch for all of its AI: **AI > Use Artificial Intelligence**.
If it is unchecked, a project task says "AI help is switched off. Turn it on
in the AI menu, Use Artificial Intelligence."

## What the Developer profile changes, area by area

### In QUILL

These are on only in Developer and Full Quill:

- **Project tasks.** Open Project Folder, Do a Project Task, Review Changes,
  Run This Command?, Undo Last Agent Turn, Stop Agent, Explain Last Turn,
  coach mode, the transcript and command output, Commands Allowed in This
  Project, and Engine Tools for This Project. Chapters 2 to 10 are about
  these.
- **Local Git.** Everything under **Tools > Git and GitHub > Local Git**:
  Uncommitted Changes, Switch Branch, stashes, Who Wrote This Line, bisect,
  Resolve Conflicts, Interactive Rebase, and Worktrees.
- **GitHub.** Opening and saving files on GitHub, the GitHub Items viewer,
  the repository administration commands under **Tools > Git and GitHub >
  GitHub**, and Codespaces. These need **GitHub Remote Access**, which
  depends on Developer Tools.
- **The Developer Console,** the Python and TypeScript consoles under
  **Tools > Advanced > Developer Console**.
- **Word Prediction** (`Ctrl+.`), which is on but quiet in the Developer
  profile.
- **Validate Agents,** the agent standards check, reached from an agent in
  the AI Library.

The Developer profile also keeps what Developer and Power Text always had:
regular expressions, formatting, macros, links, document analysis, OCR,
shell integration and the Keymap Editor on; Read Aloud, watch folders, the
character inspector and cleanup on but quiet. "Quiet" means the feature works
and stays out of the way.

### In QUILL Lite

The Developer profile adds the **Coding** area. These commands appear, and
leave again when you choose another profile:

- **File:** Open Project Folder... and Close Project.
- **Edit > Agent Work:** Undo Last Agent Turn and Stop Agent.
- **View:** Agent Task Transcript and Agent Command Output.
- **Tools:** Commands Allowed in This Project...
- **Tools > AI:** Do a Project Task..., Explain Last Turn and Engine Tools for
  This Project...

QUILL Lite has no Git, GitHub, SSH or Developer Console. Chapter 12 has the
rest of the differences.

### The tutorial

Both editors' Tutorials windows gain a Coding track, "Coding, in the
Developer profile", with one lesson: **Your first project task**. The track is
left out unless coding is on.

## Turning it off again

Choose any other profile, or uncheck **Developer Tools** (QUILL) or **Coding**
(QUILL Lite). The developer commands leave the menus and the Command Palette,
and `Ctrl+3` goes back to being Do a Document Task.

Let a running project task finish, or stop it, before you switch. If you
press a project command once coding is off, you hear "Project tasks are part
of the Developer profile. Choose the Developer profile, or turn on Developer
Tools in Customize Features."

## Safe Mode

In Safe Mode all AI is off, so project tasks are too. Open Project Folder and
Do a Project Task say "AI is off in Safe Mode. Nothing can be signed in until
QUILL starts normally." and stop.

## Where to next

- Previous: [Contents](developer-guide.html)
- Next: [Chapter 2: Opening a project, and the project boundary](developer-02-projects.html)
- [Contents](developer-guide.html)
