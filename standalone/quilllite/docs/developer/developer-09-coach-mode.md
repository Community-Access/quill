# Chapter 9: Coach mode and explanations

## What this chapter covers

QUILL's project tasks are meant for people learning to code as much as for
people who already do. This chapter covers coach mode, where the agent teaches
and you type; Explain Last Turn, which asks the agent what it did and why;
Why This Change? for one change; and the plain-language errors every task
gives you.

## Coach mode

**Coach mode** (`Alt+A`) is a check box in the task window. When it is
checked:

- the agent cannot change any file and cannot run commands. It keeps only the
  reading tools;
- it reads the project, explains in plain words, and points you to an exact
  place: "Look at cli.py line 40: the loop over files";
- it tells you what you could type there, and why, one small step at a time;
- you make the change yourself, in the editor, with all of QUILL's ordinary
  editing.

That is how a tutor works. You learn the code by changing it, and the agent
is there for the questions.

Coach mode is chosen per turn: the turn starts with the box as it is when you
press Enter. The status line adds "Coach mode", the conversation marks the
turn "Turn 2, coach mode.", and the transcript heads it "Turn 2: you asked
(coach mode)". Places the agent pointed to are listed in the transcript under
"Where to look".

Uncheck the box to let the next turn make changes again.

## Explain Last Turn

After any turn, **Explain Last Turn** asks the agent to explain what it
changed in the last turn and why, file by file, naming each file and line, in
plain words for someone learning. Nothing is changed. The explanation becomes
a turn of its own in the conversation and the transcript.

- `Alt+X`, **Explain Last Turn**, in the task window;
- **AI > Explain Last Turn** in QUILL, or **Tools > AI > Explain Last Turn** in
  QUILL Lite. It brings the task window forward and asks.

Explain Last Turn works on the task in the open task window. With no task
window open, or before the first turn, you hear "There is no turn to explain
yet." Once a task window is closed, its turns can still be undone (Chapter 7)
but not explained.

## Why This Change?

In Review Changes, **Why This Change?** (`Alt+W`) says the reason the agent
gave for the change you are on: "The agent's reason: ..." The agent is asked
to give a short reason with every change, so this is usually there. When it is
not, you hear "The agent gave no reason for this change to cli.py." The same
reason is also at the end of **Change details**.

## Errors in plain words

When a command fails, the agent is asked to say in one plain sentence what the
error means, before it tries a fix. You also hear QUILL's own sentence for the
result (Chapter 6), and the full output is one key away (`Alt+O`).

## A question from the agent

If the agent needs something only you know, it asks. The question goes in the
conversation, starting "Question for you:", and in the transcript under
"Questions for you". The agent then ends its turn. Type your answer in
**Instruction** and press Enter.

## A suggested way to learn

1. Open a small practice project (Chapter 3).
2. Check Coach mode and ask what the code does, or how to fix a failing test.
3. Make the change yourself and save it. To run the tests, uncheck Coach mode
   for one turn and ask the agent to run them; coach mode never runs
   commands.
4. Use Explain Last Turn after any turn where the agent made changes you do
   not understand.
5. Read the transcript (Chapter 10) afterwards. It is a record of what you
   learned.

## Where to next

- Previous: [Chapter 8: Agent notes in the repository](developer-08-agent-notes.html)
- Next: [Chapter 10: The transcript, and what QUILL keeps](developer-10-transcript.html)
- [Contents](developer-guide.html)
