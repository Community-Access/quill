# Chapter 10: AI help

AI help can summarize a passage, tidy your wording, answer a question about
your document, translate, and more. It is off when you first install QUILL
Lite. To use it you do two things: switch it on, and accept the privacy
agreement. Doing only one of them is not enough. *Switching on AI help*, in
Chapter 11, explains why there are two steps, and the three places you can
find the agreement.

If you would like the app to walk you through it, the tutorial *Asking a
question about a document* covers turning it on, connecting, asking and
checking what you have left.

Once it is on, you have one window to work in, called the pad. It can do
seventeen things, and two keys open it:

- **AI Assistant** (**Ctrl+Alt+G**) opens the pad where you are.
- **Ask About This Document** (**Ctrl+Alt+Z**) opens the same pad with **Ask a
  question about the document** already chosen, so you can go straight to
  typing your question.
- **Ask AI a Question** (**Ctrl+6**) opens the **AI Conversation** about the
  document you are in. Its first line says which AI you are asking. Each
  message takes your selection, or else the paragraph or section you are in,
  the title and the headings, read fresh every time, and never the whole file.
- **Prompt Library** (**Ctrl+7**) runs one of your saved prompts on the
  selection. See *Your saved prompts*, below.

There are also twelve questions you can ask about the word you are on, under
**Tools > Dictionary**. They are explained in *Dictionary*, in Chapter 7.

## How Tools > AI is laid out

**Tools > AI** reads in four groups, in the same order as the AI menu of every
other app in the family, and every command keeps its key wherever it sits:

1. **Ask:** Ask AI a Question (**Ctrl+6**), Ask About This Document
   (**Ctrl+Alt+Z**), Ask About an Image (**Ctrl+F5**), AI Assistant
   (**Ctrl+Alt+G**) and Prompt Library (**Ctrl+7**).
2. **Work on your document:** Do a Document Task (**Ctrl+3**), Propose Alt Text
   and Tidy Dictated Text (**Ctrl+F3**).
3. **Which AI:** Which AI Am I Using (**Ctrl+8**) and Choose Your AI
   (**Ctrl+4**).
4. **Accounts and Usage**, a submenu of the windows you open now and then: Use
   My Own AI Key (**Alt+F2**), Use My ChatGPT Subscription (**Alt+F5**), Connect
   or Sign Out (**Ctrl+Alt+Shift+F10**), Usage (**Ctrl+Alt+Shift+F9**), Web
   Searches Left (**Ctrl+9**) and the Privacy Agreement (**Ctrl+Alt+Shift+K**).

Your own key can come from OpenAI, Google Gemini, Anthropic Claude, OpenRouter
or Ollama Cloud, from a service of your own, or from Ollama running on this
computer, which is free and sends nothing anywhere.

## Using the AI pad

### What the pad looks like, top to bottom

1. **What will be sent.** A read-only box holding exactly the text that will
   go, and nothing else from your document. It is worth arrowing through it
   before you press anything.
2. **Send this much.** A chooser that appears when there is more than one
   sensible choice: what you selected, the paragraph you are in, or the whole
   section. The box above changes to match as you choose.
3. **What do you want done?** A list of the seventeen things the pad can do.
   Arrow through it, or press a letter to jump:

| Choose | You get |
|---|---|
| **Summarize** | A few plain sentences saying what this passage says |
| **Rewrite** | The same meaning, clearer and shorter |
| **Proofread** | Spelling, grammar and punctuation corrected, wording left alone |
| **Explain** | What this passage means, in plain language |
| **Shorten** | The same passage at about half the length, every important fact kept |
| **Simplify** | Plain, easy-to-read language: short sentences, everyday words, technical terms explained |
| **Make more formal** | The same meaning in a professional tone, for work or official letters |
| **Make friendlier** | The same meaning in a warmer tone, as if to someone you know |
| **Turn into a list** | A bulleted list, or numbered steps when the passage describes a process |
| **Find action items** | Every task, who does it and by when, and every date or deadline, one per line |
| **Suggest headings** | Headings that divide a long passage into sections you can jump between by heading, and where each goes |
| **Continue writing** | A next paragraph in the same voice, for you to keep, change or throw away |
| **Write an email reply** | Select an email you received; get a polite reply to edit, with decisions left in [square brackets] |
| **Translate** | The passage in the language you choose, from twenty, meaning and formatting kept |
| **Ask a question about the document** | You type a question; QUILL Lite finds the parts of the document that answer it and sends only those |
| **Ask a general question** | You type any question; only the question is sent, nothing from your document |
| **Have a conversation** | A window where you talk back and forth; each reply remembers what was said before |

4. **Your question.** This box appears only for the three choices where you
   type something. For **Have a conversation** it is your first message, and
   you can leave it empty: the conversation window then opens ready for you.
   For **Translate**, you get a **Translate into** list instead, with twenty
   languages. Spanish is chosen until you pick another.
5. **Put the answer in.** Where the answer goes when it arrives. See *Where
   the answer goes*, below.
6. **Send.** Nothing leaves your computer until you press it.

A few things worth knowing about the choices:

- A general question is one question and one answer. The next question does
  not remember the last one. If you want it to remember, choose **Have a
  conversation** instead (see *Having a conversation*, below).
- Answers to a general question and conversation replies can be longer than
  the others: about 1,000 tokens, which is roughly 750 words.
- Any of the seventeen can be switched off on QUILL's service from time to
  time. If the one you chose is off, the pad tells you when you press Send,
  and nothing is used.
- QUILL's free service can add a tool without a new version of QUILL Lite. A
  tool it offers that your copy does not have built in appears at the end of
  the list, after **Have a conversation**. Press `F1` on it to hear what it
  does; **Send** runs it like any other choice, and it uses one request. The
  first time you open the pad, a new tool can take a moment to appear. These
  tools are offered only on QUILL's free service, not with your own API key or
  your ChatGPT plan.

### What comes back, and what you can do with it

The answer arrives in a read-only box of its own. Under it are these buttons:

- **Replace My Selection**
- **Review Changes**, which compares the answer with your selection change by
  change (see below).
- **Insert Below**
- **Copy**
- **Try Again**
- **Follow Up**, which carries on from this answer as a conversation.

The first three only appear when they make sense. For example, if you did not
select anything, there is nothing to replace or review.

Nothing is changed in your document for you. Proofread, for instance, tells
you what it found and leaves every character alone until you press Replace My
Selection. You always get to read it first.

### Reviewing the changes word by word

**Review Changes** opens **Review AI Changes**, the review window QUILL uses
for its AI edits. It lists every change the answer would make to your
selection, one per line. Arrow to one and press **Alt+D** to read it in
**Change details**: what was there, what would replace it, and for a small
change the exact words that differ and the sentence they are in. Every change
starts checked. Press Space to uncheck one you want to keep as it was, then choose
**Apply Checked**, or **Accept All** for every change. It goes in as one edit,
so **Ctrl+Z** takes it all back. **Reject All**, or Escape, changes nothing.

#### Keeping some words of a change and not others

In prose, one change is often a whole paragraph, and the AI may have changed
three words in it: one you like, one you do not, and one you are unsure about.
You no longer have to take all three or none.

When the change you are on holds two or more word edits, a second list appears
under **Changes**: **Words in this change**. Press `Alt+W` to go to it, or
`Tab` from the Changes list. Each row is one word edit with the sentence it is
in, so arrowing down the list reads you each edit in context. Every row starts
checked. Press `Space` to drop an edit: the original words stay there, and the
rest of the change still goes in. `Alt+C` takes you back to **Changes**, and
`Alt+D` to **Change details**, which shows the sentence before and after for
the word edit you are on.

For example, the AI rewrote "The quick brown fox jumps over the lazy dog. It
was very tired that day." The Words list says:

- Changed "quick" to "rapid", in: The rapid brown fox leaps over the lazy dog.
- Changed "jumps" to "leaps", in: The rapid brown fox leaps over the lazy dog.
- Changed "very" to "rather", in: It was rather tired that day.

Uncheck the first and choose **Apply Checked**. Your document now says "The
quick brown fox leaps over the lazy dog. It was rather tired that day." You
hear "Applied 1 change, 1 of them in part, as one undo step", and `Ctrl+Z`
takes the whole thing back.

A few things to know:

- Drop every word edit in a change and the change itself is unchecked; you
  hear "No word edits left in this change, so it will not be applied". Check
  one back and the change is checked again. Checking or unchecking a whole
  change in the Changes list checks or unchecks all its word edits.
- **Accept All** still takes every change and every word edit, checked or not,
  and the result is exactly the AI's version. **Reject All** still changes
  nothing.
- A change with only one word edit has no Words list, because its own check
  box already says everything. A change shown as whole lines (a rewrite, or
  spacing only) has none either.
- Changes to spacing between the words of a change go in with the change
  whenever any of its word edits does; nobody is asked about a space.

### Where the answer goes

The pad's **Put the answer in** list has three choices:

- **The AI Result window.** The starting choice: you read the answer first,
  then choose what to do with it, as above.
- **My document, at the cursor.** The answer goes straight in where the cursor
  is, as one edit **Ctrl+Z** takes back, and QUILL Lite reads it aloud.
- **The clipboard.** The answer goes on the clipboard and is read aloud. Your
  document does not change.

QUILL Lite remembers your choice until you change it. It applies to every
answer: from the pad, the Chat Key and the Prompt Library.

### How answers are read aloud

AI answers usually come written in Markdown, with `#` before a heading, `**`
around bold words and `-` before each item of a list. When QUILL Lite reads an
answer aloud, it reads the words and leaves those symbols out, so you never
hear "star star" or "hash hash", or a link's whole web address.

That happens wherever an answer is spoken: an answer put **at the cursor** or
**on the clipboard**, and every reply in an **AI Conversation**.

Only what you hear changes. What goes into your document, onto the clipboard,
into the answer window or into the conversation is the answer exactly as it
came, symbols and all.

For example, with **Put the answer in** set to **My document, at the cursor**,
an answer of

```text
## Summary

**Three** points:

- Costs went down.
- See [the report](https://example.com/report).
```

goes into your document as those six lines, and you hear: "Answer inserted at
the cursor. Press Control Z to undo. Summary Three points: Costs went down. See
the report."

A few things are worth knowing. A link is read by its words, never its address.
A picture is read as "image" and its description. A block of code is read as
"code block": the code itself is in your document, where you can read it a
character at a time. The answer window is not read out for you; your screen
reader reads it as text, so you can check the formatting first.

### Your saved prompts

**Prompt Library** (**Ctrl+7**) is QUILL's library of prompts: the ones QUILL
comes with, such as Make Concise and Formal Tone, and any you write with **New
Prompt**. Choose one and press **Run with AI**, or **Enter**. The window
closes, your selection goes where the prompt says `{selection}`, and the
prompt is sent to the AI as a general question, using one request. If the
prompt with your text in it is bigger than the free limit allows, you are told
and nothing is sent. **Import** and **Export** share prompts with QUILL and with
other people as a prompt pack file.

**Your prompts are QUILL's prompts too.** The Prompt Library reads the one list
the whole family shares, `prompts.json` in QUILL's data folder, so a prompt you
save here shows up in QUILL and the other way round. The first time this
version starts, the prompts QUILL Lite kept in its own folder are brought into
that list once, in the background. A prompt both had becomes one; two
different prompts with the same name are both kept, and the second is named
after where it came from, such as "Tighten (from QUILL Lite)". The old file is
left as it was for one release. On a computer without QUILL, nothing is
written to QUILL's folder until you have a prompt to keep.

### What is sent, and when

Text is only sent when you press Send in the pad, or send a message in a
conversation. Then the text you asked about, either the selection or the
document, goes to the AI in use (QUILL's own service, unless you chose another
in Choose Your AI) and the answer comes back. Nothing is
sent while you type, nothing is sent in the background, and closing the pad
without asking sends nothing at all.

## Having a conversation

**Have a conversation** opens the **AI Conversation** window. You talk back and
forth, and each reply knows what was said before it.

There are two ways in:

- Choose **Have a conversation** in the pad.
- Press **Follow Up** in any answer window to carry on from that answer. If
  the answer was about your document, the follow-up keeps sending the same
  passages, so you can keep asking about them.

### What is in the conversation window

From top to bottom:

1. **About this conversation.** What goes with each message, and which service
   answers it.
2. **Conversation.** Everything said so far, newest at the end, as "You:" and
   "AI:" paragraphs. It is read-only. Press Shift+Tab from the message box to
   reach it.
3. **Your message.** This is where you start. Type, then press **Enter** to
   send.
4. The buttons: **Send**, **New Conversation**, **Copy Last Reply**,
   **Messages...**, **Export Conversation...**, **Saved Conversations**,
   **Insert Last Reply Below**, and Close.
5. **Status.** Whether it is working, what answered, or what went wrong.

When a reply arrives, it is read aloud and added to the conversation. You stay
in the message box, so you can answer straight away.

Nothing goes into your document unless you press **Insert Last Reply Below**,
and **Ctrl+Z** takes that back like any other edit.

### Saved conversations

Every conversation is saved on this computer as it goes. Press **Saved
Conversations** (**Alt+V**) in the conversation window to see them, newest
first, each with how it began, how many messages it holds and when it was last
used. Press **Enter** on one to open it and carry on where it left off, or
**Delete** to remove it; QUILL Lite asks first. **New Conversation** starts a
new saved conversation and keeps the old one.

### Going back over a conversation

In the conversation window:

- **Alt+1** reads the newest message aloud, **Alt+2** the one before it, and so on
  up to **Alt+0** for the tenth newest. Each is said with its place and its
  speaker, for example "Message 4 of 9, AI: ...", and the newest starts with
  "Newest". Focus stays in **Your message** and your half-typed message stays
  where it is. With fewer messages than the key asks for, you hear how many
  there are, for example "There are only 2 messages so far. Alt+2 reads the
  oldest."
- **Messages...** (**Alt+G**) lists every message, oldest first, one row each. Press
  **Enter** to open a message in a reading window where its headings and
  tables are real ones (in browse mode, **H** moves by heading and **T** by
  table), or **Read as Text** to see it exactly as it arrived in a plain text
  box. Close it with **Escape** and you are back on the same row; the list opens
  on that row again next time.
- **Export Conversation...** (**Alt+X**) saves the whole conversation as a **Word
  document** or a **Text file** you name. Every message is kept in order with
  who said it: in Word, each message is a level-2 heading such as "Message 3
  of 8, AI" with the message beneath it and its tables as real Word tables; in
  a text file, each message is a paragraph starting "You:" or "AI:". The Save
  As window asks before replacing a file, **Cancel** writes nothing, and your
  document is never changed. If the file cannot be written, you hear why and
  any file already there is left as it was.
- A reply that arrives while you are reading the **Conversation** box does
  not move your place in it. If you are not in the box, it shows the end, as
  before.

Example: you ask "Plan a three-day trip to Lisbon", then "Make day two
cheaper". Press **Alt+3** to hear the first plan again, and **Export
Conversation...** to keep both plans in a Word file, each under its own
heading.

These work the same on QUILL's free AI, your own key, your ChatGPT plan and
GitHub Copilot, and every one saves to the same **Saved Conversations**.

### Long conversations on the free AI

Each message you send is one request, and conversations have their own monthly
share: 40 of your 100 requests.

To stay within the size limit, each message carries as much of the
conversation so far as will fit, newest first. That means a very long
conversation slowly forgets how it began. The first time that happens, the
window tells you: "The beginning of this conversation is no longer sent, to
stay within the free limit." Press **New Conversation** whenever you want a
fresh start.

With your own AI key there is no such limit. The whole conversation goes
with every message and is billed to your provider's account, so a long
conversation costs more per reply. It is only shortened if it grows past what
the model can read at once, and the window tells you if that happens.

## Choose Your AI

**Choose Your AI** is the one window for where your AI comes from: QUILL's free
AI, your ChatGPT plan, your GitHub Copilot, Codex or your own key. Press **Choose Your AI** (**Ctrl+4**), or
choose **Tools > AI > Choose Your AI...**. Focus lands on the list, on the one
in use. There are five things in the window, in Tab order:

- **Connections**, a list. Each row says its name and then "in use", "signed
  in" or "not set up".
- **About this connection**, one short line: what it can do, who gets your text
  and what it costs.
- **Model**, that connection's own models, the recommended one first. The free
  AI says "QUILL chooses the model".
- **One button** that follows the row: **Use This**, **Sign In...** or **Sign
  Out**.
- **Close**, or press **Escape**.

**Enter** on a row does what the button says. **Delete** on a row you are
signed in to asks whether to sign out, with **No** as the default.

A row can also say "signed out by OpenAI" or "signed out by GitHub" (the
company ended the sign-in; **Sign In...** starts it again), "not available yet"
(this copy cannot offer it yet; see below), or "not available for your account"
(your organisation has switched Copilot off for you).

QUILL Lite says nothing when the window opens or as you move along the list,
because your screen reader already reads each row. It speaks only what happened:
"Now using My ChatGPT plan.", "Signed in to My ChatGPT plan. It is now in use.",
or "Signed out. No AI is in use until you choose one." If no AI is in use, the
next AI command opens this window and says "No AI is in use. Choose one."
QUILL Lite never moves you to another AI by itself: not when you sign out, not
when a key goes missing, not when a sign-in ends or a limit is reached. Each of
those is said once, nothing is sent, and the choice stays yours.

**Use My Own AI Key** (**Alt+F2**), **Use My ChatGPT Subscription** (**Alt+F5**)
and **Connect or Sign Out** (**Ctrl+Alt+Shift+F10**) keep their keys and open
this window on their own row, with the sign-in ready.

**Signing in to GitHub Copilot.** **Sign In...** on **My GitHub Copilot** opens a
small step with a short code from GitHub. The code is spaced out so your screen
reader reads one character at a time, it is said once, and it is already on the
clipboard. Press **Open the Page**, paste or type the code on GitHub's page and
approve QUILL Lite. The step closes by itself and you hear "Signed in to My
GitHub Copilot. It is now in use." **Cancel** stops waiting at once. Copilot
Free works too: its only model is "Auto (Copilot Free chooses)". QUILL Lite
signs in to GitHub on its own, separately from QUILL.

Signing in to GitHub from inside QUILL Lite needs QUILL Lite's own registration
with GitHub. Until a build carries it, the row says "not available yet",
**About this connection** says "Not available yet: GitHub sign-in for QUILL
Lite has not been registered, so it comes in a later update.", and **Sign
In...** says the same instead of opening the step. Once you are signed in, the
pad, Ask, the Prompt Library and Ask About an Image (on a Copilot model that
sees) go to Copilot on your plan. A Copilot error is said once; nothing is
retried or switched.

**Codex** runs on your ChatGPT plan with the same sign-in, so once you are
signed in to your plan, **Use This** on **Codex, for tasks** is one key. While
Codex is in use, single requests (the pad, Ask, Ask About an Image) go straight
to your plan, and the Codex program starts only for a document task. Its usage
is your plan's. If this copy does not include the Codex engine, the row says
"not available yet".

**Plan Options.** While your ChatGPT plan's row, or Codex's, is selected and
signed in, a **Plan Options...** button appears beside the action button. It
has **Allow web search**, a check box saved as soon as you change it, and
**Forget on This Computer**, which forgets the sign-in here without telling
OpenAI. QUILL Lite stays listed under Apps in ChatGPT's settings until you
remove it there.

### Which AI Am I Using

**Which AI Am I Using** (**Ctrl+8**) says in one line which AI is in use, the
model, and one thing about usage. On GitHub Copilot that is GitHub's own count;
the first time it waits a moment for GitHub's answer. On Codex it says "Codex,
on your ChatGPT plan. Single requests go to the plan directly." Press it twice
quickly to open **Choose Your AI**.

The status bar's last cell before the message, **AI**, says the same thing
shorter: "AI: free", "AI: ChatGPT plan", "AI: Copilot, Auto", "AI: Codex",
"AI: own key", or "AI: none" when nothing is in use. Press **F6**, arrow to it
and press **Enter** to open **Choose Your AI**.

### One Usage list

**Usage** (**Ctrl+Alt+Shift+F9**) opens one list with a sentence for each AI you
have set up, each saying whose count it is: QUILL's, your provider's, or a
count kept on this computer. **Manage Usage** opens the selected one's own page.
It is all text, with no meter or chart.

### When the AI in use cannot do something

The command stays in the menu with its key, and its name says what it needs,
such as **Ask About an Image (needs a connection that sees)**. Pressing it sends
nothing and asks whether to switch to one that can, with **Yes** as the default.

## Do a Document Task

**Do a Document Task** (**Ctrl+3**), in **Tools > AI**, hands a job with several
steps to GitHub Copilot or Codex, whichever is in use: "Fix the heading levels,
then build a table of contents", or "Turn these notes into actions grouped by
owner." On any other AI its name says "(needs Copilot or Codex)" and pressing
it offers to switch.

The window has six things, in Tab order: **Conversation**, a read-only record
of the task; **Status**, which says "Using GitHub Copilot" or "Using Codex on
your ChatGPT plan"; **Instruction**, where focus starts; **Send**; **Stop**; and
**Close**. Type what you want done and press **Enter**. While the task runs,
what you type goes to it as a follow-up. **Stop** ends it at once, and
**Close** stops a task that is still running.

Nothing changes without you. Before a step that changes something, **Allow This
Step?** says in one sentence what will happen: **Enter** is **Allow once**,
**Allow for this task** stops it asking about that kind of step until the task
ends, and **Escape** is **Don't allow**. Every edit then opens **Review AI
Changes**, so you accept or reject each change, and each one undoes with
**Ctrl+Z**. The next task asks again.

When the task ends you hear its summary, such as "Done. 1 change applied:
Changed the document. Each can be undone with Control Z." It is built from what
really happened and says how many changes you declined; the AI's own summary
follows in the conversation. Nothing else is spoken; the conversation fills in
quietly, one **Shift+Tab** away.

A task can only read your document, propose edits and run a short list of safe
QUILL Lite commands. It cannot reach the web, your files or anything else, and
it answers in plain text, never charts. Whatever the engine keeps while it
works is deleted when the task ends or you press **Stop**. If Copilot or Codex
is in use but cannot be started, you hear "Document tasks need My GitHub
Copilot or Codex. Press Ctrl+4 to choose one."

## Propose Alt Text

**Tools > AI > Propose Alt Text...** opens the same window with the request
already typed in: give alt text to every picture in this document that has
none. Press **Enter** to send it, or change it first. It has no key of its own;
**Ctrl+3** reaches the same window.

The task proposes short alt text for each Markdown or HTML picture that is
missing it, one at a time, and each proposal opens **Review AI Changes** on
that one change, undone with **Ctrl+Z**. When the AI in use can see pictures,
the task may ask to look at one, and **Allow This Step?** names it; the first
picture on each AI also asks whether pictures may go to that company. Only
pictures saved on this computer are sent, never one from a web address. On an
AI that cannot see, the proposals come from the words around each picture.
QUILL has the same command in its AI menu.

## Propose Alt Text

**Tools > AI > Propose Alt Text...** opens the same window as Do a Document
Task with the request already typed in: give alt text to every picture in this
document that has none. Press **Enter** to send it as it is, or change it
first. It has no key of its own, because **Ctrl+3** gets you to the same
window; from the menu it is **Alt+T**, **A**, **T**.

The task finds the document's pictures, in Markdown and HTML alike, and
proposes short alt text for each one that is missing it, one picture at a
time. Each proposal opens **Review AI Changes** on just that change, so you
hear exactly what will be written, and each one undoes with **Ctrl+Z**.
Pictures that already have alt text are left alone.

If the AI in use can see pictures, the task may ask to look at one, and
**Allow This Step?** names the picture first. Only pictures saved on this
computer are ever sent; a picture on a web address is never fetched. On an AI
that cannot see pictures, every proposal comes from the words around the
picture, and the summary says so. Like Do a Document Task, it needs GitHub
Copilot or Codex.

## QUILL's free AI

Unless you choose otherwise, AI help runs on QUILL's own free service. There
is no account, no password and no email address to give. You connect each
computer once, and then you have a monthly allowance.

### Connecting this computer

1. Open **Tools > AI > Accounts and Usage > Connect or Sign Out** (**Ctrl+Alt+Shift+F10**). If you
   have just accepted the agreement and this computer is not connected yet,
   you are brought here automatically.
2. The window gets an eight-character code from QUILL and reads it out to
   you. The code is also in a read-only box, where you can arrow through it one
   character at a time. **Say the Code Again** repeats it, and **Copy the
   Code** puts it on the clipboard.
3. Press **Open the Connect Page**. Your browser opens with the code already
   filled in. Press **Confirm** on that page. If you prefer, you can type the
   code into the web address the window names on any other device with a
   browser, such as your phone.
4. Come back to QUILL Lite. The window changes to say you are connected, and
   you will hear that it worked. Your focus stays where it was.

Afterwards, the window says you are connected and tells you this computer's
**support ID**, which is what to give if you ever write to support about AI.
It is also in **Help > About QUILL Lite**. To disconnect this computer, open
**Choose Your AI** (**Ctrl+4**), arrow to **QUILL's free AI** and press
**Delete**, or **Sign Out** when it is the AI in use.

Each computer connects separately. Signing one out does not sign out the
others.

**What is recorded.** When you use AI, the text you asked about goes to QUILL
and on to the model that writes the answer. QUILL records how many requests you
make and how big they were. It does not record what you wrote or what came
back.

### How much you can send at once

One request can be about **3,000 tokens**. That is roughly **2,250 words** or
**12,000 characters**, counting your document text, your question and the
instructions together.

If what you chose is bigger than that, the pad tells you before anything is
sent, in words rather than tokens: "that is about 4,000 words, and the free
limit is about 2,250". Select less and try again. Nothing is sent in the
meantime.

The answer is capped at about 500 tokens, which is a few hundred words. For a
general question it is about 1,000.

A long document still works. **Ask About This Document** does not send the
whole file. It picks the **three passages most likely to answer your
question**, each about 180 words and labeled with the heading it sits under,
and sends those. So you can ask about a hundred-page document; the limit is on
how much goes in one request, not on how long your document is. The pad shows
you which passages it chose before anything is sent.

### Checking what you have left

- **Usage** (**Ctrl+Alt+Shift+F9**) shows what each AI you have set up has
  used, the free AI included. Look here before you run out, rather than finding
  out when a request is turned down.
- **Web Searches Left** (**Ctrl+9**) says how many of this month's web searches
  are left. See *Searching the web on the free AI*, below.
- **Help > About QUILL Lite** shows the same allowance, and this computer's
  **support ID**, under **QUILL's free AI**. The numbers are fetched fresh each
  time, so give it a moment after About opens.
- **Connect or Sign Out** (**Ctrl+Alt+Shift+F10**) connects this computer, or
  disconnects it. Signing out does not take back your agreement. Taking back
  your agreement does sign you out.
- **Privacy Agreement** (**Ctrl+Alt+Shift+K**) always opens, whether AI help
  is switched on or not, and whether you have accepted or not. You can always
  read what you are agreeing to.

All of these keys are listed again in *Every key, in one table*, under
**Tools > AI**.

### Limits, and when they start again

The free AI is shared by everyone who uses it, so it has limits. Here is every
one of them in one place.

#### Your allowance at a glance

These are the service's current settings. They can change without an update
to QUILL Lite, and **Usage** always shows the numbers that apply to you right
now.

| Limit | How many | Starts again |
|---|---|---|
| Requests a month | 100 | The 1st of the month |
| Requests a day | 20 | Every night |
| Requests an hour | 8 | At the top of each hour |
| Any one kind of request a month | 60 | The 1st of the month |
| A new connection's first 48 hours | 15 | Rises to 100 on its own |

"Any one kind" means that Summarize, Rewrite, Proofread, Explain and Ask About
This Document each have a monthly share of 60, so no single one can use up
your whole month. The daily and hourly limits are there to catch something
running away by mistake. Ordinary work stays well inside them.

#### When the counts start again

The service keeps time in **UTC**, not in your own time zone:

- **The hour** starts again on the hour.
- **The day** starts again at **midnight UTC**. That is **8 PM Eastern** or
  **5 PM Pacific** in summer, and an hour earlier in winter. So in North
  America, your new day's requests arrive in the evening.
- **The month** starts again at **midnight UTC on the 1st**. Usage shows the
  exact date.

#### What counts as a request

One request is one press of **Send** that comes back with an answer. **Try
Again** is another request.

A request that does not produce an answer is **not counted**. That includes
one that was too long, one sent with no internet connection, one that hit a
problem on the service, and one sent after a limit was already reached.
Opening Usage or About never uses anything.

#### When the AI service is busy

Every AI service has busy moments: too many people at once, a server
restarting, a request that took too long. QUILL now handles them the same way
on the free AI, your own OpenAI or Google Gemini key, and a ChatGPT plan:

- It **tries the request up to three times**, one second apart and then two,
  when the service answers that it is busy, overloaded, timed out or asked to
  slow down (the HTTP answers 408, 409, 429, 500, 502, 503 and 504).
- When the service says how long to wait, QUILL waits that long instead, up to
  20 seconds. If it asks for longer, QUILL tells you now rather than leave you
  listening to silence.
- It **never sends a request twice when the service says not to**, because a
  second copy might be counted, or charged, twice. Your free AI allowance being
  used up, or your ChatGPT plan's usage, is said at once too: trying again
  cannot change it.
- **You only hear the end of it.** While QUILL is trying again you hear
  nothing new; if the last try fails, you hear that one failure, in the same
  words as before. If a try succeeds, you just get your answer.
- A streamed answer that has already started to arrive is never started again,
  so you never hear the beginning twice.

For example, you press Summarize at a busy moment. The first try is answered
"the service is busy", QUILL waits a second and tries again, and the answer
arrives. All you notice is that it took a second longer.

#### When you reach a limit

The AI window tells you **which** limit you reached and **when it starts
again**. Your focus moves to that message, so you can read it again with the
arrow keys. It ends with an error code, `QUILL-AI-GATEWAY-QUOTA`, which is
useful to include if you write to support.

Nothing is used, nothing in your document changes, and the rest of the editor
carries on as normal. Wait until the time it names, or ask for more (see
*Asking for more*, below).

If the message says QUILL's free AI is **paused**, it is not about you. The
service has a spending limit for everyone together, and when that is reached,
the free AI pauses for everyone until the 1st. This is rare, and you are told
when it happens.

#### A new connection starts smaller

For its **first 48 hours**, a newly connected computer gets **15 requests**.
After that, the full allowance applies **on its own**. You do not need to do
anything. This keeps people from connecting over and over to get a fresh
allowance each time, and most people trying it out do not reach 15 on the
first day.

While it applies, **Usage** and **About** say so and tell you exactly when it
ends. Signing out and connecting again starts a new connection, so it never
gets you more.

#### Computers that share an internet connection

A household, a classroom or a library usually shares one internet address.
A few limits apply to that address as a whole: how many computers can be
connected from it at once, how many new connections it can make in an hour,
and a monthly total shared by every computer on it. They are generous for a
home, and the exact numbers are not published. Signing a computer out frees up
its place.

If a class or a computer lab runs into these limits, write to support. This
is exactly the kind of thing they can help with.

#### Asking for more

1. Choose **Get Help from Support** in the Help menu (**Ctrl+Alt+F2**).
2. Say what you need and why: a course, a deadline, a book.
3. Send it. If this computer is connected, its **support ID** is added to the
   message for you, and that is all support needs to find you. There is no
   account name or password to give.

Support can raise your monthly allowance, and can end the smaller
new-connection allowance early. The change applies from your next request. You
do not need to sign out, reconnect or update anything, and Usage shows the new
number the next time you open it.

Your support ID is also in **Help > About QUILL Lite** and in **Usage**, with a **Copy
Support ID** button, if you would rather write from somewhere else.

## Using your own AI key

If you have a key from OpenAI, Google Gemini, Anthropic, OpenRouter, Ollama
Cloud or another OpenAI-compatible service, or Ollama on your own computer,
you can use **your own key** instead of QUILL's free service. Then **every
limit goes away**: no
monthly, daily or hourly allowance, no 2,250-word ceiling, and no smaller first
48 hours. You pay the provider for what you use.

### Setting it up

Open **Tools > AI > Accounts and Usage > Use My Own AI Key** (**Alt+F2**). The window has these
parts, from top to bottom:

1. **Provider.** Choose **OpenAI**, **Google Gemini**, **Anthropic Claude**,
   **OpenRouter**, **Ollama Cloud**, a **Custom OpenAI-compatible service**, or
   **Ollama on this computer**, which needs no key. Everything else in the
   window follows this choice: where your text goes, which key, which models
   and whose prices. AI help uses the key saved for the provider you choose
   here, and never another one. QUILL never guesses the provider from a key or
   a model name.
2. **About this.** A read-only box that says exactly where your text goes.
   Arrow through it once.
3. **API key.** Paste the key for the provider you chose. An OpenAI key comes
   from platform.openai.com, under API keys, and starts with `sk-`. A Gemini
   key comes from Google AI Studio at aistudio.google.com/apikey. The About box
   says where to get a key for each of the others.
4. **Model.** A list of every model your key can use for text, filled in from
   your account once the key is checked. For OpenAI, **Luna 6 comes first,
   then the other GPT-6 models**. For Gemini, **2.5 Flash comes first, then 2.5
   Pro**. The rest follow by name. Each row says roughly what it costs, for
   example "gpt-6-luna, about $0.57 per 100 requests (estimate)", so you can
   compare them just by arrowing down. Models that cannot answer in text, such
   as speech, transcription, image and embedding models, are left out.
5. **Cost estimate.** What the chosen model costs per request and per 100
   requests, at the chosen provider's prices. **These are estimates to help you
   compare, not the provider's actual prices.** A typical request is about a
   page of text in and a paragraph back. The real prices are at
   openai.com/api/pricing and ai.google.dev/pricing.
6. **Status.** Whether a key is saved for the chosen provider, what the last
   test said, and whether a key for the other provider is saved too.
7. **Test the Key.** Checks the key with your provider, fills in the model
   list, then sends one tiny request to the chosen model and tells you whether
   it answered. That request costs a fraction of a cent.
8. **Remove the Saved Key.** Forgets the chosen provider's key **straight
   away**. If your own key was the AI in use, no AI is in use until you choose
   one.

Press **OK** to save. QUILL Lite says "AI help uses your own OpenAI key, with no
limits", or "your own Google Gemini key".

**To change the model later**, press **Alt+F2** again. With a key saved, your
models are listed straight away. Pick another and press OK.

**Saving a key is choosing it.** Press OK with a key saved and your own key is
the AI in use. Remove it while it is in use and no AI is in use until you pick
one in **Choose Your AI**; the next AI command says "No AI is in use. Choose
one." Your text never moves to the free AI unless you choose it.

**Ollama on this computer needs no key.** Install Ollama from ollama.com, pull
a model, and choose **Ollama on this computer**. The About box starts with
"Runs on this computer. Nothing is sent.", and that is exactly what happens:
the model runs on your computer, nothing is billed and nothing leaves it. The
key box is off, a **Server address** box says where Ollama listens (usually
`http://localhost:11434`), the Model list is whatever Ollama has, and the test
button reads **Test the Connection**. A custom service has a Server address
too. These providers used to be set up in QUILL's AI Hub; they are the same
providers, with the same saved keys, in this one window in both editors.

**You can save both keys.** The Provider list decides which one is used. If
you choose OpenAI, a saved Gemini key just sits there unused. The status line
tells you it is there, and choosing Google Gemini is how you use it. Your text
only ever goes to the company you chose.

**With a Gemini key, Ask About an Image works too.** Gemini's models can read
pictures, and so can a picture-reading model in Ollama on this computer. The
free service and the other providers here cannot, so with a Gemini key,
**Ctrl+F5** works just as it does with a ChatGPT subscription.

### What changes with your own key

- Your text goes **straight from your computer to the provider you chose**,
  on your account. Nothing passes through QUILL's servers, so QUILL records
  nothing at all, not even the request count it keeps for the free service.
  With Ollama on this computer, nothing leaves the computer.
- **That company bills you** for each request, under its own terms and privacy
  policy. Ollama on this computer bills nothing.
- While an answer is on its way, **Send** becomes **Stop** (`Alt+S`). Stopping
  closes a Gemini stream immediately; for another route it discards that
  request's eventual answer. It never stops a request from another AI window.
- **Usage** (**Ctrl+Alt+Shift+F9**) has a row for your key, and **Manage
  Usage** opens your provider's usage page, such as your OpenAI or Google AI
  Studio account, where your requests and charges are listed. **Help > About QUILL Lite**
  shows the model and that page's address instead of the free allowance.
- You do not need to connect this computer, and you are not asked to accept
  the free service's agreement. That agreement is about QUILL's servers, and
  your text never goes there.
- The pad, its seventeen choices, and what comes back are all the same, down
  to the instructions sent along with your text.
- **There are no limits.** Nothing is turned down for being too long, the
  answer is not capped, and **Ask a question about the document** sends the
  whole document instead of the three best passages, so nothing is missed.
- **You get warnings instead of limits.** The *About to send* line tells you
  how many words are going and roughly what they will cost with the model you
  chose. That is an estimate, not your actual bill, and the answer costs
  extra. It also tells you when the text is more than the free service would
  accept, and, for something very large, that it may be more than the model
  can read at once. In that case, the provider turns the request down and
  charges nothing.

### Where the key is kept

Your key is kept in Windows' own credential store, not in a settings file.
Once saved, it is never shown again: the box stays empty and says a key is
saved. A portable copy of QUILL Lite keeps it in an encrypted file instead.

QUILL and QUILL Lite share the key. A key saved in either one works in both,
and removing it in either removes it from both.

### If a request fails

You hear what went wrong, followed by the error code
`QUILL-AI-OWN-KEY-FAILED`, and the message names the provider. The usual
causes are a mistyped key, a model your account cannot use, an account with no
credit, or the wrong provider chosen for the key you saved. **Test the Key**
tells you which one it is.

### If the AI you use is not available

QUILL Lite never quietly sends your text to a different company from the one
you chose. Every AI command goes to the one AI chosen in **Choose Your AI**. If
that AI cannot take a request, for example because your Gemini key has gone
from Windows' credential store or OpenAI ended your ChatGPT sign-in, nothing is
sent and you hear why, once:

> Your ChatGPT plan sign-in has ended. Nothing was sent. Press Ctrl+4 to sign
> in again or choose another.

If no AI is in use at all, you hear "No AI is in use. Choose one." and Choose
Your AI opens. QUILL Lite does not offer the free AI, or anything else, in its
place; switching is something you do.

This covers the pad, the Chat Key, the Prompt Library, AI conversations, **Ask
About an Image** and document tasks. Changing the AI yourself is never
questioned: signing in or out, **Use This**, or saving or removing a key all
count as your choice. A request that simply *fails* (no connection, a limit
reached) is said once, with what to do, and nothing is retried.

## Using your ChatGPT subscription

If you already pay for ChatGPT (a paid plan such as Plus or Pro), QUILL Lite can
use that plan for its AI commands, and you never handle a key. You sign in
once, in your browser, just as you sign in to ChatGPT itself.

From then on, the pad, its seventeen choices, Ask About This Document and
conversations all run on your plan. There is **no per-request bill**, and
nothing passes through QUILL's servers.

Requests draw on your plan's own usage limits, which are shared with ChatGPT
itself and any other app you have connected. In ChatGPT, **Settings > Usage**
shows how much each app used and lets you set a weekly limit for it. When the
limit is reached, QUILL Lite says so and does not switch to an API key; you can
wait for it to reset, or choose another AI yourself.

You also get two things the free service cannot do: **descriptions of
pictures**, and **web search** when you want an answer about something
current. Both are described later in this chapter. The same sign-in also
unlocks **Codex**, for document tasks.

### Signing in

1. Press **Use My ChatGPT Subscription** (**Alt+F5**), in **Tools > AI**.
   **Choose Your AI** opens on **My ChatGPT plan**, with the sign-in step
   ready. (**Sign In...** on that row does the same.)
2. The step says "To use My ChatGPT plan, approve QUILL Lite on OpenAI's
   page." Press **Open the Page**. Your browser opens on OpenAI's own sign-in
   page. Sign in as you would to ChatGPT. When the page asks whether **QUILL
   Lite** may use your plan, allow it.
3. Come back to QUILL Lite. The step closes by itself and you hear "Signed in
   to My ChatGPT plan. It is now in use." You are done.

You stay signed in until you sign out or remove the app in ChatGPT's
settings; a brief problem on OpenAI's side no longer signs you out.

If the browser did not open, the step shows the address to paste into any
browser on this computer. **Cancel** gives up without changing anything.

### Once you are signed in

Everything about the plan is in **Choose Your AI** (**Ctrl+4**):

1. **Model**, on the plan's row. Every model your plan offers, read from your
   account, the first marked "(recommended)". Whichever you choose is saved at
   once.
2. **Plan Options...**, beside the action button while the plan's row is
   selected. **Allow web search** is off until you check it; when it is on, the
   model may look things up on the web through OpenAI to answer a question.
   **Forget on This Computer** forgets the sign-in here without telling OpenAI,
   for a computer that is offline or a sign-in you already removed in
   ChatGPT's settings.
3. **Sign Out**, the action button while the plan is in use. It asks OpenAI to
   cancel QUILL Lite's sign-in and forgets it on this computer. Afterwards no
   AI is in use until you choose one; QUILL Lite does not move you to the free
   service or to a key by itself.
4. **Usage** (**Ctrl+Alt+Shift+F9**) has your plan's row, and **Manage Usage**
   opens ChatGPT's own usage page, the place to see your plan's limits and
   what you have left.

Being signed in to your plan and having a saved key do not fight: whichever
one you chose is the one in use, and the other waits until you choose it.

### What changes on your plan

- Your text goes **straight from your computer to OpenAI**, on your account,
  under OpenAI's terms and privacy policy. Nothing passes through QUILL's
  servers, and QUILL keeps no copy.
- **What you use counts toward your plan's own usage limits**, which OpenAI
  sets. When you reach one, QUILL Lite tells you in plain words, with the
  error code `QUILL-AI-CHATGPT-LIMIT`. Manage Usage, in the Usage window,
  shows when it resets.
- **Usage** (**Ctrl+Alt+Shift+F9**) has a row for your plan with the requests
  QUILL Lite sent today, counted on this computer, and **Manage Usage** opens
  your plan's own page. **Help > About QUILL Lite** shows the account and the
  model instead of the free allowance.
- You do not need to connect this computer to the free service, and you are
  not asked to accept the free service's agreement, because your text never
  goes to QUILL's servers. **About this connection** in Choose Your AI tells
  you where it does go.
- The pad, its seventeen choices, and what comes back are **exactly the
  same**, down to the instructions sent with your text. There is no size
  limit, so instead of turning anything down, the *About to send* line tells
  you how many words are going and that they count toward your plan.
- **Conversations send the whole conversation** with each message, so a long
  one remembers its beginning for as long as the model can read it.

### Where the sign-in is kept

QUILL Lite keeps only a sign-in token, in Windows' credential store (or an
encrypted file in a portable copy), under QUILL Lite's own name. QUILL Lite
never sees your ChatGPT password.

**Each QUILL app signs in on its own.** QUILL Lite, QUILL and Quill Radio each
appear separately under Apps in ChatGPT's settings, and signing one out leaves
the others as they were.

### If a request fails

You hear what went wrong, followed by an error code:

- `QUILL-AI-CHATGPT-SIGNED-OUT`: OpenAI no longer accepts this computer's
  sign-in. The row says "signed out by OpenAI"; press **Sign In...** on it
  again.
- `QUILL-AI-CHATGPT-LIMIT`: your plan's usage is used up for now.
- `QUILL-AI-CHATGPT-UNAVAILABLE`: OpenAI is not letting other apps use plans
  just now.
- `QUILL-AI-CHATGPT-FAILED`: anything else. The sentence before the code says
  what to check.

## Extras on a subscription or your own key

### Ask About an Image

**Tools > AI > Ask About an Image** (**Ctrl+F5**) tells you what is in a
picture. It could be a screenshot someone sent you, a photo of a letter, a
chart in a report, or a restaurant's menu from its website. Choose the file,
ask a question or ask nothing, and hear what the model sees.

It needs an AI that can see pictures: your ChatGPT plan or Codex, a GitHub
Copilot model that sees, a Google Gemini key, or a picture-reading model in
Ollama on this computer. On any other AI the menu says **Ask About an Image
(needs a connection that sees)...**, and pressing it sends nothing and offers
to switch to one that can, with **Yes** as the default.

This and nothing else in QUILL Lite looks at a picture, and only at a file you
choose. QUILL Lite has no AI that looks at your screen, and none that makes
pictures or charts: every answer is text.

1. Press **Ctrl+F5**. The Ask About an Image window opens, with focus in
   **Image file**.
2. Type or paste the file's full path, or press **Browse** (Alt+B) to pick it.
   JPEG, PNG, WebP and GIF pictures all work.
3. **Your question** (Alt+Q) is optional. Leave it empty to get a plain
   description written for a blind reader: what the picture is, what matters
   most in it, and every word of any text in it, written out exactly. Or ask
   something, such as "what does the sign say", "is anyone smiling" or "what
   is the total on this receipt". You get the answer first, then just the
   description that helps.
4. Press **Enter** for **Ask**. You hear "Working." If the file is not really
   a picture, or is over 20 MB, you are told so here and nothing is sent.
   Otherwise the picture goes to the model.
5. The answer opens in the **Image Description** window, with focus on the
   text so your screen reader reads it. **Insert Below** puts it into your
   document under the paragraph you are in, which is handy for captioning a
   picture in something you are writing. **Copy** puts it on the clipboard,
   and **Ctrl+Z** takes an insert back.

Only the picture and your question are sent. Nothing from your document goes
with them.

### Tidy Dictated Text

Speech recognition writes what it heard, and that is not always what you
meant: "their" for "there", a name it has never met, two words run together, a
comma where a period belonged, and every "um" you did not know you said.
**Tools > AI > Tidy Dictated Text** (**Ctrl+F3**) fixes exactly those things
and nothing else.

It works on any AI except the free one: your ChatGPT plan, GitHub Copilot,
Codex or your own key. It is not available on the free service. On the free
AI it tells you so and opens Choose Your AI on your plan's row.

1. Dictate as usual (**Ctrl+F11**, talk, pause). When the paragraph is done,
   leave the cursor in it, or select exactly the part you want tidied.
2. Press **Ctrl+F3**. You hear "Working." The selection, or the whole
   paragraph the cursor is in, goes to the model. It is asked to fix misheard
   words, punctuation and capital letters, and to remove fillers and false
   starts, while keeping your meaning, your wording and your order.
3. The **Tidied Dictation** window opens with focus on the corrected text, so
   you hear it first. **Replace My Selection** puts it where the dictated text
   was. **Copy** puts it on the clipboard. **Escape** keeps what you had. If
   you typed in that paragraph while waiting for the answer, Replace is not
   offered, and the window tells you why.
4. **Ctrl+Z** takes a replacement back in one step.

Nothing changes until you press Replace, and the model is told not to add
anything. A tidied paragraph says what you said, spelled the way you meant it.

### My Dictation Instructions

You can tell Tidy Dictated Text how you like your writing. Open **Dictation
Settings** (**Alt+Shift+F6**), press **More Dictation Settings...**
(**Alt+A**), then **My Dictation Instructions...** (**Alt+I**). A short file
opens in QUILL Lite. Write one instruction per line, in plain words, and save it:

- Write numbers as digits.
- Use British spelling.
- QUILL is always written in capitals.
- Never change legal terms.

From then on, Tidy Dictated Text follows them. They go with the passage you
tidy, and only then: never with every phrase as you talk. The AI is told that
your dictated text is something to correct, never a request to answer, so
"ask Sam to send the report" comes back tidied, not answered.

### Web search

Most of what the AI does works only from what you send it. Sometimes, though,
you need an answer about the world today: whether an event has been announced,
what a word has come to mean this year, what a web page says right now.

With **Allow web search** checked in your plan's **Plan Options**, the model
may search the web through OpenAI when a question needs it, and tell you what
it found. This works for **Ask a general question**, **Ask a question about the
document** and conversations. It is off until you turn it on, because a search
sends your question somewhere else too, and that is your choice to make.

To turn it on:

1. Press **Alt+F5**. Choose Your AI opens on **My ChatGPT plan**.
2. Tab to **Plan Options...** and press it.
3. Press **Alt+W**, or Tab to **Allow web search**, and press **Space**. It is
   saved straight away. Press **Escape** to close the options.

Press Space on the same check box to turn it off again.

### Searching the web on the free AI

QUILL's free service can search the web too, ten times a month for each
computer's account. When the service has search switched on, the pad's list
ends with **Search the web**: type a question, press **Send**, and the answer
comes back with the sites it used, one per line. Each search also uses one
ordinary request.

Press **Ctrl+9** (**Tools > AI > Accounts and Usage > Web Searches Left**) to hear how many searches
are left this month and when they start again. If the service is not offering
web search at the moment, Ctrl+9 says that instead. On your ChatGPT plan, use
**Allow web search** above instead; with your own key there is no web search.

## Coding: project tasks, in the Developer profile

This part is for people who write code. Everybody else can skip it: none of
it appears unless you choose the **Developer** profile (see [Making QUILL Lite
smaller (or larger)](lite-guide-11-making-quill-lite-yours.html#making-quill-lite-smaller-or-larger) in Chapter 11).

A project task is Do a Document Task grown up. Instead of one document, the
AI works on a whole folder: it reads the files, plans, proposes changes to
several of them, and runs your tests. You stay in charge of every step.
Nothing it proposes is written until you accept it, no command runs until you
allow it, and one command puts every file back.

QUILL has exactly the same thing, from the same code, in the same menus.

### Turning it on

Choose the **Developer** profile in **Tools > Customize Features**
(**Ctrl+Alt+F10**), or check **Coding: project tasks with an AI** there on its
own. Either way the project commands appear in the menus below, and they leave
again when you choose another profile.

Project tasks need a connection that runs tasks: **My GitHub Copilot** or
**Codex** on your ChatGPT plan, or, on your own key, **Claude** or **Ollama on
this computer**. QUILL's free AI does not run tasks. Choose with **Choose Your
AI** (**Ctrl+4**).

### Where the commands are

They sit where you would look for that kind of command:

| Menu | Commands |
|---|---|
| **File** | **Open Project Folder...**, **Close Project** |
| **Edit > Agent Work** | **Undo Last Agent Turn**, **Stop Agent** |
| **View** | **Agent Task Transcript**, **Agent Command Output** |
| **Tools** | **Commands Allowed in This Project...** |
| **Tools > AI** | **Do a Project Task...**, **Explain Last Turn**, **Engine Tools for This Project...** |

None of them has a key of its own. There was no key free in both editors, and
you rarely need one: **Ctrl+3** opens Do a Project Task whenever a project is
open, and the task window has a key for everything else.

### Opening a project

A project is just a folder. **File > Open Project Folder...** lists the
projects you opened before, newest first, so the usual case is Down Arrow and
Enter. **Browse for a Folder...** picks any other one.

QUILL Lite says "Project", the folder's name, "is open", and the status bar
gains a **Project** part that names it, with its git branch when it has one.
That part is only there while a project is open. Enter on it opens the task.

The first time you run a task in a project that has notes written for AI
agents, such as `AGENTS.md`, `CLAUDE.md`, `GEMINI.md`, Copilot's instruction
files or Cursor's rules, QUILL Lite asks once whether to use them. **Read Them
First** shows their text in the same window. Nothing in those files can approve
a command or a change. They are the project's words, not yours.

### The task window

Press **Ctrl+3**. The window is the one Do a Document Task uses, with more keys:

| Key | What it does |
|---|---|
| **Alt+I** | the instruction field, where focus starts |
| **Alt+C** | the conversation, read with the arrow keys |
| **Alt+P** | puts the cursor on the latest plan |
| **Alt+H** | puts the cursor on the latest list of changes |
| **Alt+O** | opens the last command's full output |
| **Alt+R** | opens the whole task as a document, one heading per turn |
| **Alt+U** | Undo Last Turn |
| **Alt+X** | Explain Last Turn |
| **Alt+A** | Coach mode |
| **Alt+W** | Commands Allowed in This Project |
| **Alt+L** | Engine Tools for This Project |
| **Alt+T** | Stop |

Type what you want, such as "fix the add function and run the tests", and press
Enter. The conversation fills in silently. QUILL Lite speaks only when something
happens that you would want to know: "The plan is ready", with the number of
steps; a command's result; the turn's closing summary. If you are in another
window of QUILL Lite when the task needs an answer, it says once "The project
task is waiting for you. Press Ctrl+3 to answer." and waits.

### Reviewing changes

When the agent has edits, **Review Changes** opens. The list has one row per
file, as a whole sentence: "cli.py, changed, 3 changes, taken". The row says
whether the file is taken, so there is no check box to listen for.

- **Space** on a row takes or leaves the whole file.
- **Enter** moves to its changes. Each one says where it is ("Change 2 of 3,
  lines 40 to 44, in function parse_args"), what changed in a line ("changed
  tokn to token"), and every line with its line number first. Indentation is
  said as a count when it changes.
- **Accept** and **Reject** act on the change shown; **Next Change** and
  **Previous Change** move on and back, into the next file too.
- **Why This Change?** says the reason the agent gave.
- **Apply Accepted Changes** writes everything you accepted at once.
  **Reject All**, or Escape, writes nothing.

When a file you have open is changed, it reloads in place with your cursor
where it was, and QUILL Lite says so once. A document with unsaved edits, or
in rich text, is left alone and named, so your typing is never overwritten.

### Commands and tests

When the agent wants to run something, **Run This Command?** shows one sentence
on what, where and why, then the exact command, which you can arrow through.
When QUILL Lite sees a risk it adds a warning: "This may reach the internet.",
"This deletes files." or "This runs outside the project."

- **Allow once** runs it. Enter does the same.
- **Always allow this command here** runs it and adds it to this project's
  list. It is only offered when there is no warning.
- **Don't allow**, or Escape, does not.

Some things are never run for the agent: pushing, publishing a package,
forcing a remote, and changing system settings. The agent is told to ask you
to do those yourself.

Test results come back as one sentence, such as "Tests: 12 passed, 1 failed:
test_verbose_prints_names." The full output is a document: **Alt+O** in the task
window, or **View > Agent Command Output**.

Be clear about one thing. QUILL Lite cannot stop a command you allow from
reaching the internet or doing anything your own account can do. Windows gives
it no way to without administrator features. That is why every command asks.

**Commands Allowed in This Project** is your list of commands that run without
asking. A line allows that exact command, or any command that starts with it
and a space, so `pytest` allows `pytest -q tests`. The list lives in QUILL's
own data, never in the project, so a project you download cannot approve its
own commands. The same window has **Run commands without asking**. It is off
until you check it, it asks you to confirm, and while it is on the task window's
status line says so.

### Undo, Stop, and Explain

**Undo Last Agent Turn** (**Edit > Agent Work**) puts back every file the last
turn changed and removes files it made, then says "Undid turn 3" and which
files. Before each turn QUILL Lite keeps a private copy of the project in its
own data, never in your git history. If you have edited one of those files
since, undo refuses rather than lose your work, names the file, and offers to
open it as it was before the turn so you can compare.

**Stop Agent** stops the task and the command it is running, from any window.

**Explain Last Turn** asks the agent what it changed and why, in plain words,
without changing anything. **Coach mode** goes further: the agent does not
change files or run commands at all. It explains, points you to a file and
line, and you make the change yourself. It is a good way to learn.

### Engine tools

By default the AI uses only QUILL's own tools, so every change is reviewed and
every command approved. **Engine Tools for This Project...** lists the engine's
own tools, such as Copilot's shell and editor, as check boxes. They are all off
until you check them, each use still asks you, and their edits go straight to
disk without Review Changes. A turn that has any on says so in its plan.

### Engines

- **My GitHub Copilot** and **Codex** run tasks on your account.
- **Claude**, on your own Anthropic key, runs through the Claude Agent SDK
  with QUILL's tools and none of Claude Code's own unless you turn them on.
- **Ollama on this computer** is practice mode: "Practice, on this computer.
  Nothing is sent. Slower and less capable." Good for a classroom or for
  learning without signing in to anything.

### Where things are kept

Everything QUILL Lite remembers about a project lives in its own data folder,
not in the project: the recent projects, your answer about the agent notes,
the allowed commands, the engine tools you checked, the checkpoints for undo,
command output, and the task's transcript. **View > Agent Task Transcript**
opens the transcript as a Markdown document; use **Save As** to keep a copy
anywhere. Safe Mode turns project tasks off, like the rest of the AI.

To practise once, slowly, open **Help > Tutorials...** (**Ctrl+Alt+F1**) and
choose *Your first project task*. It appears only in the Developer profile.

## What you learned, and where to go next

You now know how to open the AI pad, pick one of its seventeen choices, and
decide whether to use what comes back. You know how to connect to QUILL's
free service and keep an eye on your allowance, and how to switch to your own
key or your ChatGPT subscription when you want no limits, picture
descriptions or web search.

If you would like to practise with the app guiding you, open **Help >
Tutorials...** (**Ctrl+Alt+F1**) and choose *Asking a question about a
document*. For the twelve word questions, see *Dictionary* in Chapter 7, and
to get the most out of Tidy Dictated Text, read Chapter 9, Writing by voice.

Next, Chapter 11, Making QUILL Lite yours, shows you how to shape the app
around you, including where AI help is switched on and off.

---

- Previous: [Chapter 9: Writing by voice](lite-guide-09-writing-by-voice.html)
- Next: [Chapter 11: Making QUILL Lite yours](lite-guide-11-making-quill-lite-yours.html)
- [Contents](../userguide.html)
