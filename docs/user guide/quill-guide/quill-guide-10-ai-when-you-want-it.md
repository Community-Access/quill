# Chapter 10: AI, when you want it

This chapter is about the AI help built into QUILL, and the first thing to know
is that you never have to use it. QUILL is a complete editor without it, and
nothing you write is sent anywhere until you ask. If you would like a paragraph
summarised, tidied or explained, QUILL's own free AI is ready with no account
and no key. If you already pay for ChatGPT or GitHub Copilot, or have your own
key, you can use those instead: **Choose Your AI** (`Ctrl+4`) is the one place
to pick, and **Which AI Am I Using** (`Ctrl+8`) tells you which one answers.
Further on you will find document tasks, which hand a job with several steps to
Copilot or Codex, and the library where you can save your own prompts, skills
and agents. Every answer is text: no AI in QUILL draws charts, diagrams or
pictures.

## QUILL's own free AI

You do not need an account, a key, or a decision about which company sees your
writing. QUILL runs its own AI service, it is free, and it is the first thing in
the **AI** menu (the `&AI` menu, so `Alt` then `A` opens it).

### What the AI menu offers

The AI menu reads in four groups, and every app in the family uses the same
order, so once you know one AI menu you know them all. Every command keeps its
key wherever it sits.

**Ask:**

| Key | Command | What it does |
|---|---|---|
| `Ctrl+Alt+G` | Free AI Assistant... | Summarise, rewrite, proofread, shorten or explain the passage you are in |
| `Ctrl+Alt+Z` | Ask About This Document... | Ask a question about what you are writing |
| `Ctrl+6` | Ask AI a Question... | Ask: a conversation about this document, with the AI in use |
| `Ctrl+7` | Prompt Library... | Run one of your saved prompts on the selection, on the AI in use |
| `Ctrl+F5` | Ask About an Image... | A picture described, on any AI in use that can see pictures |

**Work on your document:**

| Key | Command | What it does |
|---|---|---|
| `Ctrl+3` | Do a Document Task... | Tell GitHub Copilot or Codex what to do to this document |
| | Propose Alt Text... | Alt text for every picture that has none, one at a time, for you to approve |
| | Do a Project Task... | In the Developer profile, with a project folder open, `Ctrl+3` opens this instead: a task in a folder of code |
| `Ctrl+F3` | Tidy Dictated Text... | Dictation's misheard words and punctuation corrected, nothing else changed |
| `Ctrl+F10` | Dictionary > Word Explorer... | Everything about the word you are on, as used in this sentence |
| `Ctrl+Alt+Shift+'` | Dictionary > Define in Context | What the word means here, and what you might be confusing it with |
| `Ctrl+Shift+;` | Dictionary > Synonyms That Fit | Replacements that keep the sentence's meaning, already in the right form |
| `Ctrl+Alt+Shift+]` | Dictionary > Find the Word For... | The reverse dictionary: describe the meaning, get the word |

**Which AI:**

| Key | Command | What it does |
|---|---|---|
| `Ctrl+8` | Which AI Am I Using | Says which AI is in use; pressed twice, opens Choose Your AI |
| `Ctrl+4` | Choose Your AI... | The one window for where your AI comes from |

**Accounts and Usage** (a submenu: windows you open now and then, each still on its own key):

| Key | Command | What it does |
|---|---|---|
| `Alt+F2` | Use My Own AI Key... | Your own key from OpenAI, Google Gemini, Anthropic Claude, OpenRouter or Ollama Cloud, a service of your own, or Ollama on this computer, free and private |
| `Alt+F5` | Use My ChatGPT Subscription... | Choose Your AI on your plan's row, ready to sign in |
| `Ctrl+Alt+Shift+F4` | Connect or Sign Out... | Connect this computer, or disconnect it |
| `Ctrl+Alt+Shift+F2` | AI Usage... | One list: what each AI you have set up has used |
| `Ctrl+9` | Web Searches Left | How many of this month's web searches are left |
| `Ctrl+Alt+Shift+K` | Privacy Agreement... | Read what is sent, and accept or withdraw |

QUILL Lite has every command in this table, so anything you learn in one editor
you have learned in both, and all but two of the keys are the same. Usage and
Connect differ: in QUILL, `Ctrl+Alt+Shift+F7` to `F12` open the other
QuillVille apps, so QUILL uses `F2` and `F4` for those two, while QUILL Lite,
which has no apps to open, uses `Ctrl+Alt+Shift+F9` and `F10`. Choose Your AI,
Which AI Am I Using and Do a Document Task (`Ctrl+4`, `Ctrl+8` and `Ctrl+3`)
are on the same keys in both.

Each command runs on whichever AI is in use: QUILL's free AI, your ChatGPT
plan, GitHub Copilot, Codex or your own key. *Choose Your AI*, later in this
chapter, is where you pick. A few need something the free AI does not have
(pictures, document tasks, the dictionary, Tidy Dictated Text), and when the AI
in use cannot do a command, its menu name says what it needs.

### What it works on

The free AI works on the selection. With nothing selected it takes the
paragraph you are in, or else the section. It never sends the whole file.

Nothing is applied without a keystroke from you. Every answer arrives in a
window with **Replace** and **Insert** buttons, and both go through the ordinary
undo list. If you typed over the text while the answer was on its way, Replace
is not offered, and QUILL tells you so instead of writing the answer somewhere
it does not belong.

Beside Replace is **Review Changes...**. It opens **Review AI Changes**, the
same review window QUILL's AI agents use: every change the answer would make to
your selection, one per line, and for a small change the exact words that
differ and the sentence they are in. Uncheck any change you want to keep as it
was, then apply the rest. It goes in as one edit, so `Ctrl+Z` takes it all back.

### Where the answer goes

The pad has a list called **Put the answer in**, with three choices:

- **The AI Result window** (the first choice and the starting one). You read
  the answer first and then choose Replace, Review Changes, Insert Below, Copy,
  Try Again or Follow Up.
- **My document, at the cursor.** The answer goes straight into your document
  where the cursor is, as one edit `Ctrl+Z` takes back, and QUILL reads it
  aloud.
- **The clipboard.** The answer goes on the clipboard and QUILL reads it aloud.
  Your document does not change.

QUILL remembers your choice (the setting `ai_answer_delivery`) until you change
it, and it applies to every answer: from the pad, the Chat Key and the Prompt
Library.

### How AI answers are spoken

AI models write their answers in Markdown, the plain-text formatting with `#`
for headings, `**` for bold and `-` for list items. On screen that is
harmless. Read aloud, it is noise: your screen reader would say "star star"
and "hash hash", and read every link's whole web address. So whenever QUILL
**speaks** an AI answer, it speaks the words and leaves the symbols out.

This applies everywhere an answer is spoken:

- an answer put **at the cursor** or **on the clipboard** (above), which QUILL
  reads aloud because focus does not move;
- each reply in an **AI Conversation**, in this window or a saved one;
- **Ask Quill**'s replies, whether announced, read aloud by QUILL's own voice
  or by the AI voice (see *Asking out loud and hearing the answer*), and the
  progress Ask Quill announces while a long answer is still arriving.

**What you hear, and what you get.** Only the spoken copy changes. What goes
into your document, onto the clipboard, into the AI Result window or into the
conversation transcript is the answer exactly as it arrived, Markdown and all.
If you asked for a Markdown table, you get a Markdown table.

**An example.** You set **Put the answer in** to **My document, at the
cursor** and ask for a summary. The AI sends back:

```text
## Summary

**Three** points:

- Costs went down.
- See [the report](https://example.com/report).
```

Your document gets those six lines exactly. You hear: "Answer inserted at the
cursor. Press Control Z to undo. Summary Three points: Costs went down. See
the report."

**What is left out, and what is kept:**

- Heading marks, bold and italic marks, list bullets and quote marks are
  dropped; the words they mark are kept.
- A link is read by its words ("the report"), never by its address.
- A picture is read as "image" and its description.
- A block of code is read as "code block". Code read aloud a symbol at a time
  is rarely what you want from an announcement; the code itself is in your
  document or the window, where you can read it character by character.

The answer in the AI Result window is not read out for you: focus lands on it
and your screen reader reads it as text, symbols included, so you can check
the formatting before you use it.

### Ask (Ctrl+6)

Press `Ctrl+6` (**AI > Ask AI a Question...**) to open the **AI Conversation**
window about the document you are in. Its first line says which AI you are
asking, such as "Asking My ChatGPT plan about this document." Type your
question and press `Enter`. With each message QUILL sends your selection, or
else the paragraph or section the cursor is in, the document's title and its
headings, read fresh every time, so you can move around the document between
questions. It never sends the whole file. **Ask Quill** (`Alt+Q`) is still
there for the advanced companion; it has not changed.

### Your prompts on the AI in use (Ctrl+7)

`Ctrl+7` (**AI > Prompt Library...**) opens the **Prompt Library**,
with the same prompts as the Prompts tab of **AI > AI Library...**: QUILL's
built-in prompts, the ones you wrote, and
the ones your Quillins add. Choose a prompt and press **Run with AI**. The
window closes, your selection is put where the prompt says `{selection}`, and
the prompt goes to the AI in use as a general question; on the free AI that is
one request. The answer arrives the way you chose. On the free AI, if the
prompt with your text in it is bigger than the free limit allows, QUILL says so
and sends nothing.

**One list of your prompts, for the whole family.** The prompts you save are
kept in one file, `prompts.json` in QUILL's data folder, and QUILL Lite's
Prompt Library reads the same file. The first time this version starts, QUILL
brings in the prompts you had saved elsewhere: Prompt Studio's, the image
description styles you wrote, and QUILL Lite's own list. A prompt that is the
same in two places becomes one. Two different prompts with the same name are
both kept, and the second is named after where it came from, for example
"Tighten (from QUILL Lite)". This happens once, quietly, in the background, and
the old files are left exactly as they were for one release in case anything
needs checking.

### Searching the web (Ctrl+9)

QUILL's free service can search the web for you, ten times a month. When the
service has search switched on, the pad's list ends with **Search the web**:
type a question, press **Send**, and the answer comes back with the sites it
used. Each search also uses one ordinary request.

Press `Ctrl+9` (**AI > Accounts and Usage > Web Searches Left**) to hear how many of this month's
searches are left and when they start again. If the service is not offering
web search at the moment, `Ctrl+9` says that instead. The pad's **Search the
web** choice and its ten searches are part of the free service only. On your
ChatGPT plan, the model can search for itself once you check **Allow web
search** in **Plan Options...** (see *Choose Your AI*, below); with your own key
there is no web search.

You never wait for it, either. Requests run in the background, so you can keep
typing, save, switch documents or close the window while an answer is coming.

> **QUILLBee's tip:** Changed your mind about an AI edit? Press `Ctrl+Z`. It
> comes back out exactly like anything else you typed.

### The Free AI Assistant pad (Ctrl+Alt+G)

The pad has a list called **What do you want done?** with seventeen choices.
Press a letter in the list to jump.

- The four basics: Summarize, Rewrite, Proofread and Explain.
- Ten writing tools: **Shorten**, **Simplify**, **Make more formal**, **Make
  friendlier**, **Turn into a list**, **Find action items**, **Suggest
  headings**, **Continue writing**, **Write an email reply** and **Translate**.
  When you choose Translate, a **Translate into** list appears with twenty
  languages. If the answer comes back the same as your text, QUILL says so
  rather than showing it as a translation: the text may already be in that
  language, or the AI could not tell what language it was in.
- Three that need you to type: Ask a question about the document, Ask a
  general question, and Have a conversation.

Every one of them is a single request of the same size, so the writing tools
cost no more of your allowance than Summarize.

### New tools from QUILL's free service

QUILL's free service can add a tool without a new version of QUILL. A tool it
offers that your copy does not have built in appears at the end of the **What
do you want done?** list, after **Have a conversation**. Press `F1` on it to
hear what it does. **Send** runs it like any other choice, and it uses one
request.

The first time you open the pad, a new tool can take a moment to appear at the
end of the list. These tools are offered only on QUILL's free service: with
your own API key or your ChatGPT plan, the list has the seventeen built-in
choices.

### Having a conversation

Choose **Have a conversation** in the pad, or press **Follow Up** in any answer
window, and the **AI Conversation** window opens. Here you can talk back and
forth, and each reply remembers what was said before.

1. Focus is in **Your message**. Type, then press `Enter`.
2. Each reply is read aloud as it arrives and added to the **Conversation**
   above. Press `Shift+Tab` to reach it.
3. Beside Send are **Copy Last Reply**, **Insert Last Reply Below**, **New
   Conversation**, **Messages...** and **Export Conversation...** (both
   described below).

If you started with a question about the document, each follow-up keeps
sending the same passages, so you can keep asking about them.

Every conversation is saved on this computer as it goes, in the same place Ask
Quill keeps its sessions, so **AI Session Branches** shows them too. Press
**Saved Conversations...** in the conversation window to see them, newest
first. Press `Enter` on one to open it and carry on where it left off, or
**Delete** to remove it (QUILL asks first). **New Conversation** starts a new
saved conversation; the old one stays saved.

**Going back over the conversation.** In the conversation window:

- `Alt+1` reads the newest message aloud, `Alt+2` the one before it, and so on
  up to `Alt+0` for the tenth newest. Each is said with its place and its
  speaker, for example "Message 4 of 9, AI: ...", and the newest starts with
  "Newest". Focus stays in **Your message** and your half-typed message stays
  where it is. With fewer messages than the key asks for, you hear how many
  there are, for example "There are only 2 messages so far. Alt+2 reads the
  oldest."
- **Messages...** lists every message, oldest first, one row each. Press
  `Enter` to open a message in a reading window where its headings and
  tables are real ones (in browse mode, `H` moves by heading and `T` by
  table), or **Read as Text** to see it exactly as it arrived in a plain text
  box. Close it with `Escape` and you are back on the same row; the list opens
  on that row again next time.
- **Export Conversation...** saves the whole conversation as a **Word
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
cheaper". Press `Alt+3` to hear the first plan again, and **Export
Conversation...** to keep both plans in a Word file, each under its own
heading.

These work the same on QUILL's free AI, your own key, your ChatGPT plan and
GitHub Copilot, and every one saves to the same **Saved Conversations**.

On the free AI each message counts as one request, and conversations have a
monthly share of 40 of your 100 requests. The conversation so far goes with
each message only as far as the ordinary size limit allows, so no message costs
more than any other, and a long conversation slowly forgets its beginning. The
window tells you the first time that happens. With your own OpenAI or Gemini
key there is no such limit: the whole conversation goes, billed to your
account.

There is a monthly, a daily and an hourly allowance, and a smaller one for a
computer's first 48 hours. Free AI limits, later in this chapter, has every
number and every rule.

### Nothing is sent until you ask

The free AI makes no request when QUILL starts, while you type, when you save,
when you are idle or when focus moves. If you leave it switched on and never
use it, QUILL makes no network call for it at all.

The first time you reach for it, QUILL shows you exactly what is sent and what
is kept, and nothing leaves your computer until you accept. You can come to that
same agreement three ways: **AI > Accounts and Usage > Privacy Agreement...** (`Ctrl+Alt+Shift+K`),
Preferences, and Customize Features. All three show the same answer, so they
never disagree.

If you withdraw, QUILL signs this computer out of the free AI as well, so no
sign-in is left behind for a service you have said no to. QUILL remembers which
version of the agreement you accepted (the setting
`ai_privacy_accepted_version`), so if what is sent ever changes in an important
way, you are asked again.

## Basic and Advanced menus

The AI menu starts out **Basic**. It shows the five free AI commands above, the
**Use Artificial Intelligence** switch, and **Show advanced AI features**. Basic
is for everybody who just wants a paragraph tidied up.

The full menu has much more: provider setup, Ask Quill, the agents, Proofread,
Transform, Translate, Read Aloud, Transcribe, More, the AI Library and the AI
Hub. It is worth having once you have chosen which company should see your
writing and have a key to paste in.

Nothing is taken away in Basic. Every advanced command keeps its keyboard
shortcut and stays in the Command Palette; Basic only changes what the menu
offers. Check **Show advanced AI features** near the bottom of the AI menu and
everything comes back at once. QUILL remembers your choice.

If you already had AI set up when you updated (you had run the wizard, or saved
a provider key), QUILL leaves you in Advanced, so no menu you were using
disappears.

## Setting up AI with the wizard

The first item in the AI menu is **Set Up AI...**, labelled "start here" until
you have used it. It is a short wizard that gets you to working AI in a minute,
in plain words.

1. **Welcome.** A short note on what QUILL's AI does, and that it is optional,
   shown to you before anything changes, and private by default.
2. **How would you like AI to run?** Pick one:
   - **On your device with Ollama.** Private and free. It runs on your computer
     with no account or key, and QUILL connects to Ollama installed there.
   - **Use an AI account.** The most capable models. Connect Claude, OpenAI,
     Gemini, OpenRouter or Ollama Cloud with a key you paste once, which QUILL
     stores safely on this computer.
   - **Not right now.** AI stays off, and you can set it up any time later.
3. **Connect.** For an account, pick a provider, paste your key, and press
   **Test connection** before you go on. For on-device AI, QUILL points itself
   at Ollama.
4. **You're all set.** A short summary of what you can now do, and a **Keep it
   simple** checkbox that turns on **Basic mode**.

QUILL also offers the wizard when you reach for AI before it is set up, for
example when you ask for minutes from a transcript, so you never hit a dead
end. Run **Set Up AI** again whenever you want to change provider or mode.

Basic mode is the default on a new install, and it hides the whole advanced
menu, not just the agents. The wizard's **Keep it simple** checkbox turns it
on, and **Show advanced AI features** turns it off.

## Using AI for free

You never have to pay to use AI in QUILL. Besides QUILL's own free AI, the
Connect step of the wizard recommends two free paths and picks good settings
for you.

- **Most private, free.** Pick **Ollama (on your device)**. A model runs on your
  own computer: no account, no key, it works offline, and nothing you write
  leaves your machine. The quality is more modest than the big cloud models.
  If Ollama is not installed yet, do not install it by hand. **AI > Set Up Local
  AI (Ollama)...** does the whole job: it reports your computer's memory,
  graphics card and free disk space, downloads and starts the official
  installer, downloads a model that suits your computer, and connects QUILL to
  it. Each step tells you what to do next, and it never moves on without you.
- **Best quality, free.** Pick **OpenRouter**. Choose **Get API key** to open
  OpenRouter's key page in your browser, create a free key and paste it back.
  QUILL picks a strong free writing model for you (at the moment a free Llama
  3.3 70B model). The model's description says **Free**, so you always know a
  choice costs nothing.

Every provider that needs a key has a **Get API key** button beside the key box
that opens the right sign-up page.

A few honest notes:

- Free cloud models can be **slower** and are **rate-limited**. Because the
  key is **your own**, that limit is yours alone; nobody else shares it, and it
  costs nobody anything.
- Free hosted models may keep or train on what you send, under their own terms.
  If your writing is confidential, use the private **on-device** option.
- **What works on free models:** everyday help works well, such as Rewrite,
  Summarize, Expand, Continue, Fix Grammar, Table of Contents, translating and
  proofreading. **Ask Quill** works too; on a small model it keeps its steps
  simple so it answers instead of stalling. The longest multi-step agent tasks
  are where a stronger paid model still does better. QUILL tells you when a
  task would benefit from one, but never stops you trying on a free model.
- **QUILL tidies on-device answers for you.** Small on-device models have a few
  habits. When you use Rewrite, Summarize, Expand, Continue or Shorten on the
  on-device model, QUILL gives the model worked examples first, then checks the
  answer for hedging ("it seems", "arguably"), editorialising ("clearly",
  "obviously") and filler openings ("In today's world", "It is important to
  note"), and tries once more to remove them. Fix Grammar and Improve Reading
  Order are left alone, so your own wording is never changed. This happens only
  on the on-device model; cloud answers are left as they come.

You can change your provider or model any time in **Use My Own AI Key**
(`Alt+F2`). The AI Hub no longer has a provider list of its own.

## AI Assistant

Beyond the free AI, QUILL has a full AI assistant. You can run it on your own
computer (llama.cpp with a local GGUF model) or connect a provider: Ollama
(local), Ollama Cloud, OpenAI, Claude, OpenRouter, Google Gemini, or a custom
OpenAI-compatible endpoint. Every provider is optional, and you choose it
yourself. Keys are kept in the Windows Credential Manager, with a
DPAPI-encrypted file as a fallback, and are never written to disk as plain
text. Where your keys are kept, later in this chapter, has the details.

### Setting up an AI provider

Open **AI > Accounts and Usage > Use My Own AI Key...** (`Alt+F2`) to choose a provider, save its
key and pick a model. It used to be the AI Hub's job; the Hub's Provider page
now just says which provider is in use and opens Use My Own AI Key.

- **OpenRouter.** Paste your OpenRouter key. One OpenRouter key reaches many
  models, including Claude, GPT-4o and Gemini.
- **OpenAI.** Paste your OpenAI API key.
- **Ollama on this computer.** No key needed. Install Ollama (`ollama serve`)
  and choose it; QUILL looks for it at `http://localhost:11434`. If Ollama runs
  on a different port or computer, change the Server address.

You can also set a **Default model for prompt runs**
(`ai_prompt_default_model`). Leave it blank and Ask AI and the Prompt Library
use the same model, or name a more capable model here for prompt library work.

### Ask Quill (Alt+Q) and Ask AI

**AI > Ask Quill...** (`Alt+Q`) opens the assistant as a conversation.
You can ask questions, draft text, suggest edits, and run QUILL commands, and
nothing changes until you approve it. The window shows the provider and model in
use, and you can switch either one there.

Earlier versions also had a separate, plain Ask AI question window. It has
been folded into **AI > Ask Quill...**, which is now the one chat window for
questions with your own AI provider. For a quick conversation about the
document on whichever AI is in use, use **AI > Ask AI a Question...**
(`Ctrl+6`), described earlier in this chapter.

### Check Grammar with AI

**AI > Proofread > Check Grammar with AI...** sends the selected text, or the
whole document if nothing is selected, to your AI model and asks it to review
the grammar. The answer lists each correction as the original phrase, the
corrected phrase and the reason. Nothing is changed for you; you make the
corrections yourself.

Out of the box, the model is told to list only the corrections needed and not
to rewrite the passage. To give it different instructions, open the Prompt
Library, find the built-in "Check Grammar" prompt and edit its text. The
command uses your version from then on.

## Free AI limits, and when they start again

QUILL's free AI is free because everybody shares it, so it has limits. Here is
every one of them in one place. **AI Usage** (`Ctrl+Alt+Shift+F2`) shows
where you stand.

### Your allowance at a glance

These are the service's current settings. QUILL reads them from the service
each time, so they can change without an update, and **Usage** always shows the
numbers that apply to you right now.

| Limit | How many | Starts again |
|---|---|---|
| Requests a month | 100 | The 1st of the month |
| Requests a day | 20 | Every night |
| Requests an hour | 8 | At the top of each hour |
| Any one kind of request a month | 60 | The 1st of the month |
| A new connection's first 48 hours | 15 | Rises to 100 on its own |

"Any one kind" means Summarize, Rewrite, Proofread, Explain and Ask About This
Document each have a monthly share of 60, so no single one can use up the whole
month. The daily and hourly limits are there to stop something running away
with a month's worth in an afternoon. Ordinary work rarely comes near them.

### When the counts start again

The service keeps time in **UTC**, not your own time zone.

- **The hour** starts again on the hour.
- **The day** starts again at **midnight UTC**. That is **8 PM Eastern** or
  **5 PM Pacific** in summer, an hour earlier in winter, so in North America
  the new day's requests arrive in the evening.
- **The month** starts again at **midnight UTC on the 1st**. Usage shows the
  exact date.

### What counts as a request

One request is one press of **Send** that comes back with an answer. **Try
Again** is another request. A request that brings no answer is **not
counted**: if it was too long, if there was no connection, if the service had a
problem, or if you had already reached a limit, nothing is used. Opening Usage
or About never uses anything.

### When the AI service is busy

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

### When you reach a limit

The AI window tells you **which** limit you reached and **when it starts
again**, and focus moves to that message so you can read it again with the
arrow keys. It ends with an error code, `QUILL-AI-GATEWAY-QUOTA` for a limit,
which is worth including if you write to support. Nothing is used, nothing in
your document changes, and the rest of QUILL carries on as normal. Wait until
the time it gives you, or ask for more (see Asking for more, below).

If the message says QUILL's free AI is **paused**, it is not about you. The
service has one spending ceiling for everybody together, and when that is
reached the free AI pauses for everyone until the 1st. This is rare, and QUILL
tells you when it happens.

### A new connection starts smaller

For its **first 48 hours**, a computer that has just connected gets **15
requests**, and then the full allowance starts **on its own**. You do not need
to do anything. It stops somebody connecting over and over for a fresh
allowance each time, and someone trying the free AI out rarely uses 15 on the
first day. While it applies, **Usage** and **About** say so and tell you exactly
when it ends. Signing out and connecting again starts a new connection, so it
never gets you more.

### Computers that share an internet connection

A household, a classroom or a library usually reaches the internet through one
address, and a few limits apply to that address as a whole: how many computers
can be connected from it at once, how many new connections it can make in an
hour, and a monthly total shared by every computer on it. They are generous for
a home. The exact numbers are not published, so that nobody can use them to
make connections by the hundred. Signing a computer out gives its place back.

If a class or a lab runs into these limits, write to support. Helping with
exactly this is part of their job.

### Asking for more

Choose **Get Help from Support** in the Help menu, and say what you need and
why: a course, a deadline, a book. When this computer is connected, its
**support ID** goes into the message by itself, and that is all support needs
to find you; there is no account name or password to give. Support can raise
your monthly allowance, and can end the new-connection allowance early. The
change applies from your next request. You do not need to sign out, reconnect
or update, and Usage shows the new number the next time you open it.

Your support ID is also in **Help > About Quill**, if you would rather
write from somewhere else.

## Using your own AI key

If you have an account with OpenAI, Google Gemini, Anthropic, OpenRouter,
Ollama Cloud or another OpenAI-compatible service, or Ollama on your own
computer, you can use **your own key** instead of QUILL's free service, and
**every limit goes away**: no
monthly, daily or hourly allowance, no 2,250-word ceiling, and no smaller first
48 hours.

### Setting up your key (Alt+F2)

**AI > Accounts and Usage > Use My Own AI Key...** (`Alt+F2`) opens one window. Its parts, in Tab
order:

- **Provider.** **OpenAI**, **Google Gemini**, **Anthropic Claude**,
  **OpenRouter**, **Ollama Cloud**, **Custom OpenAI-compatible service**, or
  **Ollama on this computer**. The last five used to live in the AI Hub's
  Provider list; that list is gone and they are all here now. Everything else
  in the window follows this choice: where your text goes, which key, which
  models and whose prices. AI help uses the key saved for the provider you
  choose here, never another one. The choice is saved with your settings
  (`ai_own_key_provider`), and QUILL never guesses it from a key or a model
  name.
- **About this.** A read-only box that says exactly where your text goes. Arrow
  through it once.
- **API key.** Paste the key for the provider you chose. An OpenAI key comes
  from platform.openai.com, under API keys, and starts with `sk-`. A Gemini key
  comes from Google AI Studio at aistudio.google.com/apikey. The About box
  says where to get a key for each of the others.
- **Server address.** Only for a custom service and for Ollama on this
  computer; it is off for the others, whose address never changes. Ollama
  usually listens at `http://localhost:11434`. An address you saved in the AI
  Hub before is filled in for you.
- **Model.** Every model your key can use for text, filled in from your account
  once the key is checked. For OpenAI, **Luna 6 first, then the other GPT-6
  models**; for Gemini, **2.5 Flash first, then 2.5 Pro**; then the rest by
  name. Each row says roughly what it costs, for example "gpt-6-luna, about
  $0.57 per 100 requests (estimate)", so arrowing down the list is enough to
  compare them. Your choice is saved as `ai_own_key_model`. Models that cannot
  answer in text (speech, transcription, images, embeddings) are left out.
- **Cost estimate.** The chosen model's estimated cost per request and per 100
  requests, at that provider's prices. **These are estimates to help you
  compare, not the provider's prices.** A typical request is about a page in
  and a paragraph back. The real prices are at openai.com/api/pricing and
  ai.google.dev/pricing.
- **Status.** Whether a key is saved for the chosen provider, what the last test
  said, and whether a key for the other provider is saved too.
- **Test the Key.** Checks the key with your provider, fills the model list,
  then sends one tiny request to the chosen model and tells you whether it
  answered. That request costs a fraction of a cent.
- **Remove the Saved Key.** Forgets the chosen provider's key **at once**. If
  your own key was the AI in use, no AI is in use until you choose one; QUILL
  does not move you to the free AI by itself.

Press **OK** and the key is saved. QUILL says "AI help uses your own OpenAI key,
with no limits", or names your own Google Gemini key.

To change the model later, press `Alt+F2`. With a key saved, the list of models
is there straight away. Pick another and press OK.

Saving a key is choosing it: press OK with a key saved and your own key is the
AI in use, the same as **Use This** on its row in **Choose Your AI**. Remove the
key while it is in use and no AI is in use until you pick one; the next AI
command says "No AI is in use. Choose one." Nothing goes to the free AI
instead unless you choose it.

**Ollama on this computer needs no key.** Install Ollama from ollama.com,
pull a model, and choose **Ollama on this computer**. The About box starts with
"Runs on this computer. Nothing is sent.", and that is the whole story: the
model runs on your own computer, nothing is billed and nothing leaves it. The
key box is off, the Model list is whatever Ollama says it has, and the test
button reads **Test the Connection**, which checks Ollama is running. A model
that Ollama says can read pictures answers Ask About an Image too.

**One choice for all of QUILL's AI.** When you press OK, the provider you chose
is also the one the advanced AI features use (Ask Quill, Run Agent, the AI
Library, Proofread, Transform and the rest). You no longer set it up twice.

You can save both keys. The Provider list decides which one is used. With
OpenAI chosen, a saved Gemini key just waits; the Status line tells you it is
there, and choosing Google Gemini puts it to work. QUILL never decides from
which key exists or from a model's name, so a request never goes to a company
you did not choose.

With a Gemini key, **Ask About an Image** works too. Gemini's models can read
pictures, so `Ctrl+F5` answers on a Gemini key just as it does on a ChatGPT
plan. Ollama on this computer can too, with a model Ollama says reads pictures.
The free service, and an OpenAI, Anthropic, OpenRouter, Ollama Cloud or custom
key here, cannot; with one of those in use, Ask About an Image says what it
needs and offers to switch.

### What changes with your own key

- Your text goes **straight from this computer to the provider you chose**, on
  your account. Nothing passes through QUILL's servers, so QUILL records
  nothing at all, not even the count it keeps for the free service. With
  Ollama on this computer, nothing leaves the computer at all.
- **That company bills you** for each request, under its own terms and privacy
  policy. Ollama on this computer bills nothing.
- While an answer is on its way, **Send** becomes **Stop** (`Alt+S`). Stopping
  closes a Gemini stream immediately; for another route it discards that
  request's eventual answer. It never stops a request from another AI window.
- **AI Usage** (`Ctrl+Alt+Shift+F2`) has a row for your key: how many
  requests are left this minute, from the provider's last answer, where it
  reports one. **Manage Usage** opens your provider's usage page, such as your
  OpenAI or Google AI Studio account, where your requests and charges are. **Help > About**
  also shows the model and that page's address instead of the free allowance.
- You do not need to connect this computer, and you are not asked to accept the
  free service's agreement, which covers QUILL's servers. Your own key never
  touches them.
- The pad, what it can do, and what comes back are the same, down to the
  instructions sent with your text.
- **There are no limits.** Nothing is refused for being too long, the answer is
  not cut short, and **Ask a question about the document** sends the whole
  document instead of the three passages that match best, so nothing is missed.
- **You get warnings instead of limits.** The *About to send* line tells you
  how many words are going and roughly what they cost with the model you chose
  (an estimate, not your provider's bill), and that the answer costs extra. It
  also tells you when the text is more than the free service would accept, and,
  for something very large, that it may be more than the model can read at
  once. In that case the provider refuses it and charges nothing.

### Where your own key is kept

In Windows' own credential store, not a settings file. Once saved it is never
shown again: the box stays empty and says a key is saved. A portable copy of
QUILL keeps it in an encrypted file instead. QUILL and QUILL Lite share the
key, so a key saved in either works in both, and removing it in either removes
it from both.

### If a request fails

You hear why, followed by the error code `QUILL-AI-OWN-KEY-FAILED`, and the
message names the provider. The usual causes are a mistyped key, a model your
account cannot use, an account with no credit, or the wrong provider chosen for
the key you saved. **Test the Key** tells you which.

## Which AI is in use

QUILL keeps one record of which AI answers you: QUILL's free AI, your ChatGPT
plan, your GitHub Copilot, Codex, or your own key. The choice is saved with
your settings as `ai_connection`.

The first time you start this version, QUILL keeps what you already had. If you
were signed in with ChatGPT, your plan stays in use. If not, and you had a key
saved, your key stays in use. Otherwise it is the free AI. Nothing changes for
you.

After that, signing in is choosing. Sign in with ChatGPT and your plan is in
use. Sign in to GitHub Copilot and Copilot is in use. Save a key in **Use My
Own AI Key** and your key is in use. Connect the free AI and the free AI is in
use. **Use This** in **Choose Your AI** switches to a row you are already
signed in to, without signing anything.

If you sign out of the one in use, no AI is in use until you pick one. QUILL
does not quietly send your text to the free AI or to your key instead. The next
AI command says "No AI is in use. Choose one."

If OpenAI ends your ChatGPT sign-in itself, you hear "Your ChatGPT plan sign-in
has ended. Nothing was sent. Press Ctrl+4 to sign in again or choose another."
GitHub ending a Copilot sign-in is said the same way. Nothing is retried, and
nothing goes anywhere else. A limit works the same way, on any AI: you hear it
once, for example "Your ChatGPT plan's limit for QUILL is reached. Nothing was
sent. Manage usage is in the Usage window.", and QUILL neither tries again nor
switches.

QUILL counts the requests it sends on your ChatGPT plan, today and this week,
along with the token counts OpenAI reports back. That count stays on this
computer and is always called a local count. OpenAI's own usage page is the
real answer about your plan.

Two more settings hold a model each: `ai_copilot_model` for GitHub Copilot and
`ai_codex_model` for Codex. Empty means the service picks.

Answers are always plain text. QUILL asks every AI not to draw charts, graphs or
diagrams, and if one sends something like that anyway, you get it as text, not
a picture.

## Choose Your AI

**Choose Your AI** is the one window for where your AI comes from. Press
`Ctrl+4`, or choose **AI > Choose Your AI...**. Focus lands on the list, on the
one in use, and the window has five things in it, in Tab order:

- **Connections**, a list. Each row says its name, then whether it is in use,
  signed in or not set up: "QUILL's free AI, in use", "My ChatGPT plan, signed
  in", "My GitHub Copilot, not set up", "Codex, for tasks, signed in", "My own
  key, OpenAI, signed in".
- **About this connection**, a short read-only line: what it can do, and who
  gets your text and what it costs. For example "Text and pictures, per model.
  Agent tasks: no. Goes to OpenAI and counts toward your ChatGPT plan."
- **Model**, the models that connection offers, from its own list. The first
  one is the service's recommendation and says "(recommended)". The free AI
  says "QUILL chooses the model", and a row you have not signed in to says
  "Sign in to see the models".
- **One button that follows the row.** **Use This** on a row you are signed in
  to, **Sign In...** on one that is not set up, and **Sign Out** on the one in
  use.
- **Close**. `Escape` closes the window too.

`Enter` on a row does what the button says. `Delete` on a row you are signed in
to asks whether to sign out of it, and **No** is the default, so a stray key
does nothing.

A row can say three more things. "Signed out by OpenAI" or "signed out by
GitHub" means the company ended the sign-in itself; **Sign In...** starts it
again. "Not available yet" means this copy of QUILL cannot offer that
connection; the Copilot and Codex paragraphs below say when. "Not available for your
account" means your organisation has switched Copilot off for you; About says
so in one sentence.

QUILL does not talk over your screen reader here. When the window opens, or you
move along the list, your screen reader already reads the row and its state, so
QUILL says nothing. It only speaks when something happens that your screen
reader cannot know: "Now using My ChatGPT plan.", "Signed in to My ChatGPT plan.
It is now in use.", or "Signed out. No AI is in use until you choose one." The
row's own words change at the same moment, so arrowing away and back tells you
the truth.

Signing in uses what you already know. **My ChatGPT plan** opens a small step
with **Open the Page**, which takes you to OpenAI's sign-in page; approve QUILL
there and the step closes by itself. **My own key** opens **Use My Own AI Key**,
with its Provider list. **QUILL's free AI** opens its Connect step, the same one
as before, and only when you ask for it.

**My GitHub Copilot** uses the same small step, with one more field: a short
code from GitHub. QUILL spaces the code out so your screen reader reads one
character at a time, says it once, and puts it on the clipboard. **Open the
Page** takes you to GitHub's page, where you paste or type the code and approve
QUILL. The step closes by itself and you hear "Signed in to My GitHub Copilot.
It is now in use." **Cancel** stops waiting straight away. Copilot Free works
too; its model list has one entry, "Auto (Copilot Free chooses)". QUILL signs in
to GitHub on its own, separately from QUILL Lite and from the GitHub sign-in
QUILL uses for your repositories.

Signing in to GitHub from inside QUILL needs QUILL's own registration with
GitHub. Until a build carries it, the row says "not available yet", **About this
connection** says "Not available yet: GitHub sign-in for QUILL has not been
registered, so it comes in a later update.", and **Sign In...** tells you the
same thing instead of opening the step. Nothing about Copilot is sent anywhere
until then.

Once you are signed in and Copilot is in use, the pad, Ask, the Prompt Library
and Ask About an Image (on a Copilot model that can see) all go to Copilot on
your plan. If Copilot answers with an error, you hear it once; QUILL does not
try again and does not switch to another AI.

**Codex, for tasks** runs on your ChatGPT plan, with the same sign-in. Once you
are signed in to your plan, **Use This** on the Codex row is the only key to
press. Codex is there for document tasks (below). While it is in use, single
requests such as a rewrite, Ask or Ask About an Image go straight to your plan,
the same as on the ChatGPT row, and the Codex program itself starts only when
you begin a document task. Its usage is your plan's, so AI Usage shows it on
the ChatGPT row. If this copy of QUILL does not include the Codex engine, the
row says "not available yet" and About says so.

While your ChatGPT plan's row, or Codex's, is selected and signed in, one more
button appears beside the action button: **Plan Options...**. It
opens two choices that used to live in the plan's own window. **Allow web
search** is a check box: when it is checked, the model may search the web
through OpenAI to answer you, and it is saved as soon as you change it.
**Forget on This Computer** forgets the sign-in here without telling OpenAI,
for a computer that is offline or a sign-in you already removed in ChatGPT's
settings. QUILL stays listed under Apps in ChatGPT's settings until you remove
it there. If your plan, or Codex, was the AI in use, no AI is in use afterwards.
**Close** closes the options; every choice is already saved.

The older commands keep their keys and now open this window on their own row,
with the sign-in step ready: **Use My Own AI Key** (`Alt+F2`), **Use My ChatGPT
Subscription** (`Alt+F5`) and **Connect or Sign Out** (`Ctrl+Alt+Shift+F4`).

In Safe Mode the window still opens, says that AI is off in Safe Mode, and
nothing can be signed in.

### Which AI Am I Using (Ctrl+8)

Press `Ctrl+8` and QUILL says, in one line, which AI is in use, the model, and
one thing about usage when there is something to say. On your ChatGPT plan that
is the plan, the model you chose, and "3 requests today from QUILL, counted on
this computer." On GitHub Copilot it adds GitHub's own count, such as "41 of 300
premium requests this month, by GitHub's count." The first time, that waits a
moment for GitHub's answer; after that it is said at once. On Codex it says
"Codex, on your ChatGPT plan. Single requests go to the plan directly." Press
`Ctrl+8` twice quickly and it opens **Choose Your AI** instead. With no AI in
use it says so: "No AI is in use. Choose one."

### The AI cell in the status bar

The status bar has a cell called **AI**, near the end, that says the same thing
shorter: "AI: free", "AI: ChatGPT plan", "AI: Copilot, Auto", "AI: Codex" or
"AI: own key". It says "AI: none" when no AI is in use, and "AI: off" when AI
help is switched off. Press `F6` to reach the status bar, arrow to it, and press
`Enter` to open **Choose Your AI**.

### AI Usage

**AI > Accounts and Usage > AI Usage...** (`Ctrl+Alt+Shift+F2`) opens one list, with one sentence
for each AI you have set up, and each sentence says whose count it is. A count
QUILL keeps on this computer is always called that; a number from a service is
named as that service's. For example:

- "QUILL's free AI: 14 of 50 requests today, by QUILL's count. Resets at
  midnight."
- "My ChatGPT plan: 23 requests today from QUILL, counted on this computer.
  OpenAI sets the limits; Manage usage opens them."
- "My GitHub Copilot: 41 of 300 premium requests this month, by GitHub's
  count." QUILL asks GitHub when the list opens and says that row once when the
  answer arrives.

**Manage Usage** opens the selected one's own page in your browser. It is all
text. There is no meter, gauge or chart.

### When the AI in use cannot do something

Every AI command stays in the menu with its key. When the AI in use cannot do
one, its menu name says what it needs, for example **Ask About an Image (needs
a connection that sees)...**. Pressing it sends nothing. QUILL asks instead,
"Pictures need a connection that can see. My ChatGPT plan can. Switch to it and
ask?", with **Yes** as the default because you just asked for it. **Yes**
switches and carries on. If nothing you have set up can do it, **Yes** opens
**Choose Your AI** on a row that can.

## Do a Document Task (Ctrl+3)

Some jobs take more than one step: "Fix the heading levels, then build a table
of contents, then list broken links", or "Turn these notes into actions grouped
by owner." **AI > Do a Document Task...** (`Ctrl+3`) hands a job like that to
**GitHub Copilot** or **Codex**, whichever is in use, and it works through the
steps with QUILL's own editing tools.

Only those two can do tasks. On any other AI the menu says **Do a Document Task
(needs Copilot or Codex)...**, and pressing it sends nothing and offers to
switch, the same way as any other AI command.

The window has six things in it, in Tab order:

- **Conversation**, a read-only record of the task: what you asked, each step,
  and the summary at the end.
- **Status**, which says "Using GitHub Copilot" or "Using Codex on your ChatGPT
  plan", and whether it is working.
- **Instruction**, where focus starts. Type what you want done and press
  `Enter`. While a task is running, what you type here goes to it as a
  follow-up.
- **Send**, which does the same as `Enter`.
- **Stop**, which stops the task straight away. Changes already made
  stay, and each one undoes with `Ctrl+Z`.
- **Close**, which also stops a task that is still running.

Nothing changes without you. Before a step that changes something, a small
window, **Allow This Step?**, says in one sentence what will happen. Press
`Enter` for **Allow once**, choose **Allow for this task** to stop being asked
about that kind of step until this task ends, or press `Escape` for **Don't
allow**. Every edit to your document then opens **Review AI Changes**, the same
review you already know, so you can accept or reject each change. Nothing
carries over to the next task: it asks again.

QUILL says only what your screen reader cannot know. When the task ends, you
hear its summary, for example "Done. 2 changes applied: Changed the document;
Ran a command. Each can be undone with Control Z." The summary is built from
what actually happened, not from what the AI says it did, and it also tells you
how many changes you declined. A task you stop starts "Stopped."; one that
could not finish starts "The task could not finish." The AI's own short
summary follows in the conversation. The conversation and status fill in
quietly; `Shift+Tab` takes you to them.

**What a task can use.** Only QUILL's own document tools: reading the outline,
a section, the selection or the whole document, checking accessibility,
proposing an edit, and running a short list of QUILL commands that are safe to
run. It cannot use the web, your files, a command window or anything outside
the document, and the engine's own tools for those are switched off. It is
told to answer in plain text and never to draw charts or diagrams.

**When there is no engine.** If GitHub Copilot or Codex is in use but this copy
of QUILL cannot start it, you hear "Document tasks need My GitHub Copilot or
Codex. Press Ctrl+4 to choose one." In Safe Mode, document tasks are off with
the rest of AI.

**What is kept.** Nothing about a task outlives it: what the engine keeps while
it works is deleted when the task ends, when you press Stop, and again before
the next task starts, so even a crash leaves nothing behind. The changes you allowed stay in your document, where
`Ctrl+Z` takes each one back.

## Propose Alt Text

**AI > Propose Alt Text...** opens the same window as Do a Document Task with
the request already typed in: give alt text to every picture in this document
that has none. Press `Enter` to send it as it is, or change it first. It has no
key of its own, because `Ctrl+3` gets you to the same window.

The task lists the document's pictures, Markdown and HTML alike, and proposes
short alt text for each one that is missing it, one picture at a time. Each
proposal opens **Review AI Changes** on just that change, so you hear exactly
what will be written, and each one undoes with `Ctrl+Z`. Pictures that already
have alt text are left alone.

If the AI in use can see pictures, the task may ask to look at one. **Allow
This Step?** names the picture ("Send the picture beach.png from this document
to your AI, to describe it"), and the first picture on each AI also asks
whether pictures may go to that company at all. Only pictures saved on this
computer are ever sent; a picture on a web address is never fetched, and the
task writes its proposal from the words around it and tells you it could not
see it. On an AI that cannot see pictures, every proposal comes from the
words around the picture, and the summary says so.

A Word or EPUB file you opened through Import / Convert keeps its pictures
inside the original file, so the task can propose alt text for them from the
words only.

## Project tasks: coding with an AI

A project task is Do a Document Task for a folder of code. You tell the AI what
you want done in your project, and it plans, reads your files and proposes
changes, but nothing is written until you accept it and no command runs until
you allow it.

This section is for people who write code. Everything in it is part of the
Developer feature profile, and nobody else meets any of it: not in the menus,
not in the command palette and not in the tutorials.

### Turning it on: the Developer profile

Choose the **Developer** profile in **Profiles and Features...**, or press
`Alt+Shift+P` and pick it from the list. It used to be called Developer and
Power Text, and it keeps the regular-expression, cleanup and analysis tools it
always had. It is the only profile, apart from Full Quill, that turns on the
coding features: project tasks, commands and tests, undo for every change an
AI makes, coach mode, and the git extras.

The other developer tools in QUILL live behind the same profile now: the shell,
Git and GitHub, Codespaces, IntelliSense, the Developer Console and the agent
standards check. In every other profile they are off, not just quiet.

If you want these tools without the rest of the Developer profile, open **Help
> Feature Profiles > Manage Individual Features** and check **Developer Tools**.
That one feature carries all of them.

If you leave the Developer profile while a project task is running, the task
finishes first and its window stays open until then. You hear "Developer tools
are off now. The project task that was running will finish first; its window
stays open until then."

If you press a project command without the Developer profile, you hear "Project
tasks are part of the Developer profile. Choose the Developer profile, or turn
on Developer Tools in Customize Features." In Safe Mode, project tasks are off
with the rest of AI.

### Which AI can do a project task

A project task needs an AI that can use tools. These can:

- **GitHub Copilot**, on your own Copilot plan.
- **Codex**, on your ChatGPT plan.
- **Claude**, on My own key with the Anthropic Claude provider. QUILL drives it
  through the Claude Agent SDK, with your own Anthropic key, and only QUILL's
  project tools are open to it.
- **Ollama on this computer**, on My own key, as practice mode. QUILL labels it
  "Practice, on this computer. Nothing is sent. Slower and less capable." It
  is a good way to learn how a task goes without an account, but it needs a
  model that can use tools, and it makes more mistakes.

QUILL's free AI does not run project tasks. Choose the one you want in **Choose
Your AI** (`Ctrl+4`).

Every engine gets the same tools, the same review and the same questions. What
you hear does not change with the engine.

### Opening a project

A project is a folder. Choose **File > Open Project Folder...**. The window
lists your recent projects first; press `Enter` on one to open it, or choose
**Browse for a Folder...** to pick any other folder. You hear "Project
cli-tool is open, on branch main." (or just "Project cli-tool is open." when
the folder is not a git repository).

The status bar gains a **Project** cell, the first time you open a project. It
says "Project cli-tool, main", and adds ", waiting for you" when the task has a
question you have not seen. `Enter` on the cell opens the task.

**File > Close Project** closes it. If a task is still running, QUILL asks you
to stop it or let it finish first.

### The task window

With a project open, `Ctrl+3` opens **Do a Project Task** instead of Do a
Document Task. With no project open, `Ctrl+3` is the document task, as before.
You can also choose **AI > Do a Project Task...**.

Focus starts in **Instruction**. Type what you want, for example "Add a
--verbose flag to cli.py that prints each file as it is processed, and add a
test", and press `Enter`. While a task runs, what you type goes to it as a
follow-up.

The window's keys:

- `Alt+I` Instruction, where you type.
- `Alt+S` Send, the same as `Enter`.
- `Alt+C` Conversation, the read-only record of the task.
- `Alt+P` Plan puts the cursor on the latest plan in the conversation.
- `Alt+H` Changes puts the cursor on the latest list of changes.
- `Alt+O` Output opens the last command's full output as a document.
- `Alt+R` Transcript opens the whole task as a document.
- `Alt+U` Undo Last Turn.
- `Alt+X` Explain Last Turn.
- `Alt+A` Coach mode, a check box.
- `Alt+W` Allowed Commands.
- `Alt+L` Engine Tools.
- `Alt+T` Stop.

The status line says which AI is working, the project, and what is happening:
working, waiting for you, coach mode, or "Commands run without asking" when you
have turned that on.

QUILL speaks only what your screen reader cannot know: the plan is ready, the
task needs you, a command's result, a turn applied, undone, stopped or done.
The conversation fills in quietly. No streaming text is read at you.

If you are working in another document when the task needs you, nothing pops
up over your typing. You hear "The project task is waiting for you. Press
Ctrl+3 to answer." once, and `Ctrl+3` brings the window back with the question
open. If QUILL is not the window in front, it says nothing at all; the Project
cell tells you when you come back.

### The plan

Before it changes anything, the agent writes its plan as numbered steps in
plain words, under a Plan heading in the conversation. You hear "The plan is
ready. 4 steps." Focus does not move. Press `Alt+P` to land on the plan and
read it. If you want something different, type it as a follow-up, such as
"don't touch the README", and press `Enter`.

The agent reads your files without asking, but only inside the project folder.
Secret files, such as `.env` files, keys, certificates and credential files,
are never listed, read or sent.

### Review Changes

When a turn has changes, **Review Changes** opens by itself. Nothing reaches
your disk until you accept it here.

The first list, **Files** (`Alt+F`), has one row per file, as a sentence:
"cli.py, changed, 3 changes, taken", or "tests/test_cli.py, new file, 24
lines, not taken". The last word says what you have chosen: taken, not taken,
or how many of the changes are taken. `Space` on a row takes or leaves the
whole file. `Enter` on a row moves you to its changes.

**Change details** (`Alt+D`) shows one change at a time, with line numbers and
where it is, and whether it is accepted, for example "Change 2 of 3, lines 40
to 44, in parse_args. Accepted." The buttons:

- `Alt+A` Accept takes the change shown.
- `Alt+R` Reject leaves it out.
- `Alt+N` Next Change, then the next file's.
- `Alt+P` Previous Change.
- `Alt+I` Accept All in File.
- `Alt+L` Reject All in File.
- `Alt+W` Why This Change? reads you the agent's reason for it.

`Enter` on the default button, **Apply Accepted Changes**, writes everything
you accepted at once, after QUILL has kept a copy of the project for Undo Last
Turn. `Escape` is **Reject All**, and nothing is written.

### Files you have open

When a turn changes a file you have open in QUILL, the open copy is reloaded in
place, with your cursor where it was, and you hear one line, such as "cli.py
was updated by the task." Focus stays where it was.

If the open copy has edits you have not saved, or is in rich text, QUILL leaves
it alone and tells you, so your typing is never overwritten. Reload it yourself
when you are ready to see the task's change.

### Run This Command?

When the agent wants to run a command, such as the tests, **Run This
Command?** opens. One sentence says what will run and why, for example "Run
pytest -q tests/test_cli.py in your project folder cli-tool, to check the new
test." The exact command is in a read-only **Command** field below it, so you
can arrow through it and read it on a braille display character by character.

QUILL, not the AI, looks at the command and adds a **Warning** line when one of
these applies:

- "This may reach the internet." for installers and network tools, such as
  `pip install`, `npm install` and `curl`.
- "This deletes files." for `del`, `rm`, `Remove-Item` and the like.
- "This runs outside the project." for a path that leaves the project folder.

The buttons are **Allow once** (`Enter`), **Always allow this command here**,
and **Don't allow** (`Escape`). Always allow is only offered when there is no
warning.

Some things QUILL never runs for an agent, whatever you have allowed:

- pushing to a remote, such as `git push`;
- publishing a package, such as `npm publish` or `twine upload`;
- forcing anything against a remote;
- changing system settings.

The agent is told "The person keeps this step for themselves", and tells you
the exact command so you can run it yourself if you want to.

When the command finishes, you hear its result in one sentence, such as "Tests:
12 passed, 1 failed: test_verbose_prints_names." The full output is a read-only
document: press `Alt+O` in the task window, or choose **View > Agent Command
Output**. A command that runs a long time asks "The command has run for 5
minutes. Keep waiting? Choose No to stop it."

Commands run in your project folder, with your API keys, tokens and QUILL's own
settings taken out of their environment.

### What QUILL cannot stop on Windows

Windows gives QUILL no simple way to fence a command in. Once you allow a
command, it can reach the internet, read files outside the project, and do
anything your own Windows account can do. QUILL cannot prevent that. Your
approval is the safety line, which is why QUILL shows you the exact command and
asks every time unless you choose otherwise.

### Commands Allowed in This Project

**Tools > Commands Allowed in This Project...**, or `Alt+W` in the task window,
lists the commands this project may run without asking. Always allow this
command here adds to it, and you can add your own: a command, or the start of
one, such as `pytest`, which then allows `pytest -q tests` as well. Only what
you typed or chose counts, never a pattern the AI suggests, and never a command
with a warning.

**Run commands without asking** is a check box in the same window. It is off
by default. When you check it, QUILL asks you to confirm, and says plainly that
the agent will then run any command it chooses without showing it to you, that
pushing, publishing and system changes are still never run, and that Undo Last
Turn cannot undo what a command did outside the project or on the internet.
While it is on, the status line says "Commands run without asking", and every
command it runs is noted in the conversation.

The list and this setting are kept in QUILL, for this project only. A project
folder cannot carry its own allow list, so a project you clone can never
approve its own commands.

### Undo Last Agent Turn

A turn can change many files, so one `Ctrl+Z` is not enough. **Undo Last
Turn** (`Alt+U` in the task window) puts back every file the last turn changed,
across the whole project, removes the files it made, and says what it did, starting
"Undid turn 2."

It works after you close the task window too: choose **Edit > Agent Work >
Undo Last Agent Turn**, or press `Ctrl+Shift+Grave, U` (press the QUILL key,
then U). QUILL keeps the last 10 turns of each project.

If you have edited one of those files since the turn, undo refuses rather than
lose your work. It says which file, for example "cli.py has changed since the
agent's turn. Undo would lose your edits.", and offers to open the file as it
was before the agent's turn, to compare. **Yes** opens that copy as a separate
document. Your own file is not changed either way.

Undo puts files back. It cannot take back what a command did outside the
project or on the internet.

### Stop Agent

**Stop** (`Alt+T`) in the task window stops the task straight away, and the
command it is running stops with it. From anywhere else in QUILL, choose **Edit
> Agent Work > Stop Agent**, or press `Ctrl+Shift+Grave, K` (press the QUILL
key, then K). It stops a document task too. If nothing is running, you hear
"No agent task is running."

### Coach mode and Explain Last Turn

**Coach mode** (`Alt+A`) is a check box in the task window. When it is checked,
the agent does not change files or run commands. It reads the project,
explains, and points you to a file and line, such as "Look at cli.py line 40",
and tells you what you could type there and why. You make the change yourself
in QUILL. It is meant for people learning to code.

**Explain Last Turn** (`Alt+X` in the window, or **AI > Explain Last Turn**)
asks the agent to explain what it changed in the last turn and why, file by
file, in plain words. Nothing is changed.

In Review Changes, **Why This Change?** (`Alt+W`) does the same for one change.

When a command fails, the agent is asked to say what the error means in one
plain sentence before it tries a fix.

### Agent notes in a project

Many projects carry notes for AI agents: `AGENTS.md`, `CLAUDE.md`, `GEMINI.md`,
`.github/copilot-instructions.md` and the files in `.github/instructions`,
Cursor's rules in `.cursor/rules`, and the older `.cursorrules`,
`.windsurfrules` and `.clinerules`. QUILL finds all of them, including an
`AGENTS.md` in a subfolder.

The first time you start a task in a project that has them, **Use This
Project's Agent Notes?** asks once. You hear which files it found, for example
"This project has notes for AI agents in AGENTS.md. Use them for tasks here?"
Choose **Use Them**, **Don't Use Them**, or **Read Them First**, which opens
them read-only. QUILL remembers your answer for that project.

Text in those files is never an instruction QUILL obeys. Nothing in them can
approve a command or a change; you still decide every one.

### Engine tools, only if you choose

By default the AI uses only QUILL's own project tools, which is what makes
review and approval work the same on every engine. **AI > Engine Tools for
This Project...**, or `Alt+L` in the task window, lists the engine's own tools
as check boxes: for GitHub Copilot, its file reader, search, file finder,
editor, shell and web tools; for Codex, its command runner and patch tool; for
Claude, its own reader, search, editor, shell and web fetch.

All of them are off until you check them, for that engine and that project
only. Each use still asks you first. Know what you are turning on: an engine's
own edit tool writes straight to disk without Review Changes, and its shell can
do anything your account can. Undo Last Turn still puts the project's files
back, because QUILL keeps its copy before the turn starts. A turn that has any
of them on says so in the conversation and under the plan.

### The transcript

The whole task is a document, with a heading for each turn and subheadings for
Plan, Changes, Commands and Result, so your heading keys move through it. Press
`Alt+R` in the task window, or choose **View > Agent Task Transcript**. It
opens in QUILL like any other document, so you can find, bookmark, read aloud
and braille it. It is Markdown already: **Save As** puts a copy wherever you
want one.

### Where QUILL keeps its records

Everything QUILL keeps about a project lives in QUILL's own app data, in your
user profile, never in the project folder: the recent projects, the
transcripts, command output, the copies for Undo Last Turn, the allow list,
your answer about agent notes and your engine tool choices. Nothing is added to
your repository unless you save something there yourself.

### The tutorial: Your first project task

The Tutorials window has a Coding track, "Coding, in the Developer profile",
with one lesson, **Your first project task**. It takes about twelve minutes. It
has you make a practice folder, open it as a project, ask for one change, read
the plan, review the change, allow the test command and hear the result, undo
the whole turn, and try coach mode. Each step tells you what you should hear.
The track only shows in the Developer profile.

### The menus at a glance

- **File:** Open Project Folder... and Close Project.
- **Edit > Agent Work:** Undo Last Agent Turn (`Ctrl+Shift+Grave, U`) and Stop
  Agent (`Ctrl+Shift+Grave, K`).
- **View:** Agent Task Transcript and Agent Command Output.
- **Tools:** Commands Allowed in This Project...
- **AI:** Do a Project Task... (`Ctrl+3` with a project open), Explain Last
  Turn, and Engine Tools for This Project...

The commands without a key can be given one in the Keymap Editor.

## If the AI you chose is not available

QUILL never quietly answers with a different AI from the one you chose. If
what you set up cannot be used right now, QUILL either tells you once, or
asks you first; which one depends on where your text would go instead.

**When your text would stay on this computer, you are told once.** If the
provider in your AI settings cannot be reached and Ask Quill falls back to the
on-device model, you hear, as Ask Quill opens: "Anthropic was not available, so
Quill is using the on-device model instead. Check your provider and key in the
AI settings to restore it." Nothing leaves the computer, so there is nothing to
agree to.

**When your text would go to a different company, you are asked first.** A
**Use a Different AI Provider?** or **Send to a Different AI?** box opens. The
question is the whole message, so your screen reader reads it as the box opens,
and **No** is the default button, so pressing Enter out of habit sends nothing.

- **Ask Quill and QUILL's AI tools.** The provider in your AI settings is
  unavailable, and Ask Quill's own setup was once pointed at another cloud
  provider. Before this change, Ask Quill used that other provider without a
  word. Now it keeps the on-device model and asks, for example: "Anthropic is
  not available right now. Use openai instead? That sends your text to openai
  over the internet. Choose No and nothing is sent." **Yes** uses it for the
  rest of this chat. **No** keeps the on-device model.
- **The pad, Ask, the Prompt Library, conversations, Ask About an Image and
  document tasks** follow the one choice in **Choose Your AI**. If the AI you
  chose cannot take a request (its key has gone from Windows' credential
  store, or OpenAI or GitHub ended its sign-in), nothing is sent and you hear
  why, for example "Your ChatGPT plan sign-in has ended. Nothing was sent.
  Press Ctrl+4 to sign in again or choose another." If nothing is in use at
  all, you hear "No AI is in use. Choose one." and Choose Your AI opens. QUILL
  never picks another AI for you; switching is always something you do.

Changing the AI yourself is never questioned: signing in or out, choosing
**Use This**, or saving or removing a key all count as your choice.

**Limits.** A request that *fails* (no connection, a limit reached) is not a
fallback: you hear why it failed, once, and Ask Quill may suggest switching to
your on-device model, but it never switches for you.

## Using your ChatGPT subscription

If you already pay for ChatGPT, QUILL can run its AI commands on your plan.
There is no key to paste and no bill per request.

1. Press `Alt+F5` (**AI > Accounts and Usage > Use My ChatGPT Subscription...**). **Choose Your AI**
   opens on **My ChatGPT plan**, with its sign-in step ready. (Pressing
   **Sign In...** on that row in `Ctrl+4` does the same.)
2. Press **Open the Page**. Your browser opens on OpenAI's own sign-in page.
   Allow "QUILL" to use your plan. If the browser does not open, the step shows
   the address to paste into one.
3. Come back to QUILL. The step closes by itself and you hear "Signed in to My
   ChatGPT plan. It is now in use."

You stay signed in until you sign out or remove the app in ChatGPT's settings; a brief problem on OpenAI's side no longer signs you out.

From then on the pad, its seventeen choices, Ask About This Document and
conversations go straight from this computer to OpenAI on your plan, with no
charge per request and nothing through QUILL's servers.

Requests draw on your plan's own usage limits, which are shared with ChatGPT
itself and any other app you have connected. In ChatGPT, **Settings > Usage**
shows how much each app used and lets you set a weekly limit for it. When the
limit is reached, QUILL says so and does not switch to an API key; you can
wait for it to reset, or choose another AI yourself.

Once you are signed in, everything about the plan is in **Choose Your AI**:

- **Model**, on the plan's row: your plan's own models, read from your account,
  the first marked "(recommended)". Whichever you choose is saved at once.
- **Plan Options...**: **Allow web search** (off until you check it; when it is
  on, the model may search the web through OpenAI to answer a question) and
  **Forget on This Computer**.
- **Sign Out**, the action button while the plan is in use. It asks OpenAI to
  cancel QUILL's sign-in and forgets it here. Afterwards no AI is in use until
  you choose one.
- **AI Usage** (`Ctrl+Alt+Shift+F2`) has the plan's row, and **Manage Usage**
  opens your plan's own page, which shows its limits and what is left.

### How the sign-in works

Each QuillVille app signs in on its own. QUILL's sign-in is not QUILL Lite's,
QUILL Cast's or Quill Radio's; each appears under its own name in Apps in
ChatGPT's settings, and signing out of one leaves the others signed in. When
another app is already signed in on this computer, the Status line says so,
because your browser is then signed in already and Open the Page is a
single Allow instead of a password.

Being signed in to your plan and having a saved key do not fight: whichever
one you chose in **Choose Your AI** is the one in use, and the other waits. The
plan needs neither the free service's connection nor its agreement, which
covers QUILL's servers. QUILL keeps only a refresh token, in Windows'
credential store, under QUILL's own name. About names the account and the
model.

When something goes wrong, the message carries a code and tells you what to do
next: `QUILL-AI-CHATGPT-SIGNED-OUT` (sign in again), `-LIMIT` (you have used
the plan's allowance for now), `-UNAVAILABLE`, `-SIGNIN` or `-FAILED`.

### Ask About an Image (Ctrl+F5)

This is the one AI command that works on a file. Choose a JPEG, PNG, WebP or
GIF picture, ask a question about it or none, and hear what the model sees: a
description written for a blind reader, with any text in the picture copied out
exactly. The answer opens in an Image Description window with Insert Below and
Copy, and `Ctrl+Z` takes an insert back. It needs an AI that can see pictures:
your ChatGPT plan or Codex, a GitHub Copilot model that sees, a Gemini key, or a
picture-reading model in Ollama on this computer. On any other AI the menu says
**Ask About an Image (needs a connection that sees)...**, and pressing it sends
nothing and offers to switch to one that can. Only the picture and your
question are sent.

Pictures and the editor: this, and **Suggest alt text with AI** in **Insert >
Image...**, are the only AI features in QUILL that look at a picture, and both
work only on pictures you choose. QUILL has no AI that looks at your screen or
makes pictures or charts; every answer is text.

### Tidy Dictated Text (Ctrl+F3)

This is the AI for dictation. The selection, or else the paragraph at the
cursor, goes to the model with an instruction to correct what speech
recognition got wrong (sound-alike words, names, words run together,
punctuation, capitals, fillers and false starts) and to change nothing else.
The Tidied Dictation window offers Replace My Selection, and `Ctrl+Z` takes it
back in one step. It runs on any AI except the free one: your ChatGPT plan,
GitHub Copilot, Codex or your own key, and never on the free allowance. On the
free AI it says so and opens Choose Your AI on your plan's row.

#### My Dictation Instructions

You can tell Tidy Dictated Text how you like your writing. Open **Dictation
Settings** (**Alt+Shift+F6**), press **More Dictation Settings...**
(`Alt+A`), then **My Dictation Instructions...** (`Alt+I`). A short file
opens in QUILL. Write one instruction per line, in plain words, and save it:

- Write numbers as digits.
- Use British spelling.
- QUILL is always written in capitals.
- Never change legal terms.

From then on, Tidy Dictated Text follows them. They go with the passage you
tidy, and only then: never with every phrase as you talk. The AI is told that
your dictated text is something to correct, never a request to answer, so
"ask Sam to send the report" comes back tidied, not answered.

### The Dictionary submenu

The Dictionary submenu of the AI menu is a dictionary that reads the sentence.
It asks thirteen questions about the word you are on. Each sends the word and
the sentence it sits in, never the rest of the document, and the answer is
written to be listened to. Where it helps, you also get a list of choices, each
saying why.

- **Define in Context** (`Ctrl+Alt+Shift+'`)
- **Synonyms That Fit** (`Ctrl+Shift+;`)
- **Simpler Word** (`Ctrl+Shift+-`)
- **More Formal Word** (`Ctrl+Shift+=`)
- **More Vivid Word** (`Ctrl+Shift+'`)
- **Opposites** (`Alt+Shift+-`)
- **Is This the Right Word?** (`Ctrl+Alt+Shift+/`)
- **Use It in a Sentence** (`Alt+Shift+=`)
- **Where It Comes From** (`Alt+Shift+,`)
- **How to Say It** (`Alt+Shift+'`)
- **Rhymes** (`Ctrl+Alt+Shift+;`)
- **Word Explorer** (`Ctrl+F10`), which answers all of them at once
- **Find the Word For...** (`Ctrl+Alt+Shift+]`), the reverse dictionary

The same items are in the *Dictionary for "word"* submenu when you press the
Applications key on a word. The answer window opens on the answer. Press `Tab`
to reach the **Choices**, then `Enter` or **Use This Word** replaces the word as
one undo step (Find the Word For inserts at the cursor instead). It only does so
while the word is still where it was.

Like Tidy Dictated Text, the dictionary runs on any AI except the free one. A
dictionary gets asked a hundred times a day, and that would spend a free
allowance on synonyms. On the free AI it says so and opens Choose Your AI on
your plan's row. QUILL Lite has the same thirteen items on the same keys.

## Where your keys are kept

### Portable mode and key storage

Normally QUILL keeps AI provider keys in the **Windows Credential Manager**,
which ties them to your Windows user account. If you run QUILL from a
self-contained folder, for example on a network share or a USB drive, portable
mode keeps all your keys in that folder with the rest of your QUILL data.

#### Turning on portable mode

The portable bundle comes with an empty `data\` folder next to `quill.exe`, and
that folder is what tells QUILL to run portable. There is nothing to set: just
run `quill.exe` from the bundle's main folder. The Setup Wizard's **Data
location** page notices the portable install and offers the portable choice for
you. To turn an installed copy into a portable one, copy the install folder to
a USB drive and make an empty `data\` folder at its top level; QUILL switches to
portable mode the next time it starts from there.

If you used to set `QUILL_PORTABLE=1`, you no longer need to; QUILL ignores it
now, and the `data\` folder is what counts.

Nothing is written to the computer you plug into. Extract the zip, run
`quill.exe`, and your settings, keymap and everything else go straight into the
`data\` folder beside it. No folder appears in `%APPDATA%` on that computer.

If you ran a portable QUILL before version 1.0 and your settings look as if
they have reset, they have not. Older portable copies kept them in
`%APPDATA%\Quill` on that computer. Copy that folder's contents into the
bundle's `data\` folder to bring them across.

You can still choose otherwise. Picking **Windows profile** in Preferences or
the Setup Wizard is remembered and wins over the bundle, because a choice you
make yourself always beats a default. The same goes for every QuillVille app
with a portable build: Quill Radio, QUILL Cast, Quill Weather, Audio Studio,
Converter, Inkwell, Beacon, Media Player and QUILL Lite.

#### Keys in portable mode

In portable mode, keys are kept in a file called `keys.enc` in the QUILL data
folder. It is encrypted with Windows DPAPI, so it is protected by your Windows
user account.

The encrypted file only opens for the Windows account that made it. Copy it to
another computer or another Windows account and it cannot be read, so you will
need to type your keys in again there. Portable mode gives you a
self-contained folder on one computer; it does not carry your keys from one
computer to another.

### How QUILL protects your keys and sign-ins

Everything secret QUILL holds for you (AI provider keys, remote site passwords,
and the sign-in tokens for any online service you connect) goes into one
protected store. On Windows that is the Windows Credential Manager, or the
DPAPI-encrypted `keys.enc` file in portable mode; on macOS it is the login
Keychain. QUILL never writes a secret as plain text, and never puts one in a
settings file, a log, a diagnostic bundle or its own program files.

When you sign out of a service, QUILL clears every secret that service stored,
in one step, so nothing is left behind. No secret is ever part of QUILL itself,
so there is nothing to dig out of the program: your keys and tokens live only
in your operating system's protected store, tied to your account. If QUILL ever
adds a sign-in for another service, such as an online library, its tokens will
be kept there too.

### Keys from environment variables

For developers and test machines, keys can also come from environment
variables, whichever storage mode is on. These always win and are never saved
to disk.

| Provider | Environment variable |
| --- | --- |
| OpenRouter | `QUILL_OPENROUTER_KEY` |
| OpenAI | `QUILL_OPENAI_KEY` |
| Ollama Cloud | `QUILL_OLLAMA_KEY` |
| AI Assistant | `QUILL_ASSISTANT_KEY` |

## The AI Library

**AI > AI Library...** is the one home for everything QUILL can do with AI on
your writing. It has three tabs, all with the same buttons (Run, Edit,
Enable/Disable, Import, Export):

- **Prompts.** Single instructions you run on the selection or document, such
  as "Rewrite warmly" or "Summarize". New, Edit, Delete, and Promote a prompt
  into a Skill.
- **Skills.** Workflows of several steps, saved as `.sqp` packs you can share.
  Run, Import, Export and Remove them, and Promote a Skill into an Agent.
- **Agents.** The catalogue of agents that can use tools (Writing Companion,
  Reviewer, Code Doctor and more), plus any you have saved yourself. Run them
  through the reviewed gateway, or Validate one against the agent standard.

The three grow into one another. **Promote** turns a Prompt into a Skill and a
Skill into an Agent, so you can start simple and add power when you need it.
Anything you build is yours to Export and share, and a friend or colleague can
Import it.

### Build an AI Action

On the Skills tab, **Build Action...** opens a simple form. It is the easiest
way to teach QUILL something new, and there is no syntax to learn.

1. **Name** your action, for example "My Monday standup notes".
2. **Start from** a built-in example (Meeting Minutes, Action Items and the
   rest) or a blank page. An example fills in the instructions for you to
   adjust.
3. **Describe what you want in plain language.** That is all the
   "programming" there is: no Markdown, no metadata, no syntax.
4. **Attach a reference** if you like: an agenda, your house style, or an
   earlier example you were happy with. QUILL matches its format and wording,
   as in "Make minutes that look like last month's."
5. **Save.** Your action becomes a real Skill in the Library, ready to Run on
   any document, change later, Promote to an Agent, or share.

### Prompt Library

The full prompt manager is the **Prompts** tab of **AI > AI Library...**,
which holds Prompts, Skills and Agents in one window. (Type "Prompt Library"
in the Command Palette, `Ctrl+Shift+P`, to open the older stand-alone prompt
window this section describes.)

On the left is a list of every prompt; type in the search field to filter it by
name or category. On the right is the selected prompt's instructions, and an
optional input field where you can type or paste text to use instead of the
selection.

To run a prompt:

1. Select a prompt in the list, or type in the search field to find it.
2. If you like, paste text into the input field. Left blank, QUILL uses the
   selection in the editor, or the whole document.
3. Press **Run with AI**. The result opens in the AI Response window.

#### Built-in prompts

QUILL comes with eighteen prompts you can use straight away or as starting
points:

- Editing and tone: Check Grammar, Fix Grammar, Improve Clarity, Make Concise,
  Active Voice, Formal Tone, Conversational Tone, **Paraphrase**.
- Structure: Summarize, Convert to Bullet Points, **Generate FAQs**,
  **Step-by-Step Instructions**.
- Writing: Continue from Here, **Draft a Speech**, **Summary Email**, **Social
  Media Post** (280 characters or fewer).
- Research: Define This Term, Find Counterarguments.

The ones in bold are the newer one-shot tools.

Built-in prompts are always there. You can change their wording or disable
them, but you cannot delete them.

#### Managing prompts

- **New Prompt.** A small window: type a name, choose a category, and write the
  instructions. Put `{selection}` where you want QUILL to insert the text.
- **Edit.** Change the name, category or instructions of a prompt you made.
  For a built-in prompt you can change its text; your version is saved and the
  original is kept.
- **Disable/Enable.** Hides or shows a prompt in the list without deleting it.
  Handy for built-ins you never use.
- **Delete.** Removes a prompt you made. Built-in prompts cannot be deleted.

#### Prompts from Quillins

Quillins can add prompts to the library with a `prompts.json` file. The bundled
`ai-writing-prompts` Quillin adds 7 more: Expand This, Vary Sentence Rhythm,
Make More Vivid, Write a Title, Generate Outline, Suggest Supporting Evidence
and Plain Language. They appear in the list and run like any other prompt, but
they are not saved into your own library file.

#### Sharing prompt packs

QUILL shares prompt collections as `.pqp` (Prompt Quill Pack) files.

- **Import .pqp.** Choose a file, and every prompt in it is added. Prompts
  whose names are already in your library are skipped.
- **Export .pqp.** Saves all the prompts you have made to a `.pqp` file you can
  share or keep as a backup.

A `.pqp` file is plain JSON that is easy to read:

```json
{
  "schema": "quill.prompt-pack/1",
  "name": "My Writing Prompts",
  "prompts": [
    {
      "name": "Make Punchy",
      "text": "Rewrite this as a punchy one-liner: {selection}",
      "category": "Editing"
    }
  ]
}
```

### Skill Library

A prompt is one instruction. A skill is a series of steps, and each step can
use what the step before it produced.

Skills live on the **Skills** tab of **AI > AI Library...**. (The older
stand-alone Skill Library window is still in the Command Palette,
`Ctrl+Shift+P`, as "Skill Library".)

A skill has a name, a description and a list of steps. If the skill asks for
choices, such as tone, reading level or kind of output, QUILL asks you for them
before it runs. Each step then sends its prompt to the AI in turn and hands the
answer on to the next step.

#### Bundled skills

Four skills come with QUILL, in the `ai-writing-skills` Quillin:

- **Accessible Rewrite.** Looks for plain-language problems in your text (long
  sentences, passive voice, jargon), then rewrites it for the reading level you
  choose: Grade 6, 8 or 10. The rewrite replaces the selection when you Accept.
- **Research and Draft.** Finds the main topic of your selection, gathers five
  supporting facts, then drafts a paragraph in the tone and length you choose.
- **Meeting Notes to Action Items.** Reads meeting notes, pulls out every
  action item with its owner and deadline, checks for any it missed, and writes
  a clean follow-up summary. The result goes to the clipboard.
- **Argument Strengthener.** Works out how your argument fits together, finds
  its weak points and the counterarguments, then writes a stronger version for
  the audience you choose.

#### Running a skill

1. Open **AI > AI Library...** and go to the **Skills** tab.
2. Select a skill in the list.
3. Press **Run**. If the skill needs choices, a small window appears; fill them
   in and press OK.
4. QUILL says "Running step 1 of N..." as each step starts.
5. When it finishes, the result window appears. Read it, then press **Accept**
   to put it in your document (for skills that do that), or **Copy** to copy it
   to the clipboard.

Each step waits for the whole answer before the next one starts, instead of
showing it word by word. That keeps every step's result complete and easy to
read.

#### Writing and sharing skills

A skill is a `.sqp` (Skill Quill Pack) file: a plain Markdown document with
YAML front matter at the top. Open any `.sqp` file in QUILL to read and edit
it, and share a skill by sharing the file. The appendix on writing skills, at
the end of this guide, walks you through it, and the full reference is section
20 of `docs/quillins.md`.

To check a skill file for mistakes before you share it, run:

```
python -m quill.tools.sqp_validator yourskill.sqp
```

## The rest of the AI menu

Once **Show advanced AI features** is checked, the AI menu holds everything
QUILL's assistant can do. Here are the parts this chapter has not covered yet.

### Quick writing actions

**AI > Transform Selection** has the small writing chores, so they never pull
you out of the editor: **Rewrite Selection**, **Summarize Selection**,
**Expand Selection**, **Continue Writing**, **Fix Grammar** and **Generate
Table of Contents**.

Rewrite Selection, Summarize Selection, Continue Writing and Fix Grammar work
with or without a selection:

- **Rewrite Selection** and **Fix Grammar** act on your selection if you have
  one. Otherwise they use the paragraph at the cursor.
- **Summarize Selection** acts on your selection if you have one. Otherwise it
  summarizes the whole document.
- **Continue Writing** uses your selection as the lead-in if you have one.
  Otherwise it continues from the full document.

QUILL tells you the scope it chose before anything happens, for example
"Rewrite paragraph (42 words)", so you always know what the action will
change. If there is nothing to act on, QUILL says so ("Nothing to rewrite")
and sends nothing. If AI is turned off, these actions say "AI is turned off.
Enable 'Use Artificial Intelligence' in the AI menu." and do nothing else.

On the **on-device model**, Summarize works in two passes. The first pulls
the plain observations out of your text. The second writes a short summary
from those observations, to a word budget, with the original out of view.
This keeps a small local model much closer to what your text actually says,
so it does not invent its own interpretation. Cloud providers do it in a
single pass, because they do not need the help.

### Rewrite & Improve Selection

**AI > Rewrite & Improve Selection** changes with the kind of document you are
in, so it only offers what makes sense there. In ordinary writing it has
**Rewrite clearly**, **Shorten**, **Make warmer**, **Review** and **Check
accessibility**. In a code file it offers jobs for code instead. Select the
text first and choose one. The rewritten text takes the place of your
selection, and `Ctrl+Z` puts the original back if you prefer it.

### Run Agent

An agent is a helper with one job and the skills for it. **AI > Run Agent**
lists every agent QUILL has: Accessibility Editor, Citation & Link Fixer,
Code Doctor, Data Cleaner, GitHub Maintainer, Markdown Publisher, Math Tutor,
Meeting Notes to Action Items, Plain-Language Rewriter, PRD Architect, QUILL
Concierge, Release Notes Builder, Researcher, Reviewer, Summarizer and Writing
Companion. Choose one and it works on your selection or your document,
whichever it was made for. One that changes your selection does it in place.
One that changes the whole document shows you a preview first, and nothing
changes until you accept it. One that only reports opens what it found in a
new document.

Agents can only use a short, safe list of editing tools, and they still need
AI turned on. In Safe Mode, or with AI off, the items stay on the menu but
tell you why they cannot run. The AI Library, below, is where you look at an
agent more closely, or make your own.

### Your writing instructions

**AI > More > Writing Instructions...** opens a short document of rules the
assistant always follows when it writes for you: who you are writing for, the
tone you like, words you never want to see. The first time, QUILL starts it
for you with those three headings to fill in. It is an ordinary document, so
edit it however you like and save it. The assistant reads it again every time
it writes, so a change counts straight away.

### Writing Assistant, Prompt Studio and Agent Center

These three older windows are no longer on the menu, because the AI Library
now does their jobs in one place. You can still reach them by name from the
Command Palette (`Ctrl+Shift+P`):

- **Writing Assistant** finds the QUILL commands that match what you type,
  and offers ready-made prompts for rewriting, summarizing, continuing and
  fixing grammar. It is also where Ask Quill Chat lives, described in the next
  topic.
- **Prompt Studio** lets you build your own reusable prompts with template
  variables.
- **Agent Center** writes a guided plan for a task. You review the plan
  before sending it to the Writing Assistant.

### Run Python

**Run Python...**, a button in the Writing Assistant, runs a small piece of
restricted Python against the current document text and selection, so you can
transform text in ways no menu command offers. The restriction is a list of
allowed imports and some limits on time and memory. It is not a security
boundary. Only run Python code you trust or wrote yourself.

### Connecting to an AI provider

The quickest way in is **Use My Own AI Key** (**AI > Accounts and Usage > Use My Own AI Key...**,
`Alt+F2`). In short:

1. Choose a provider: OpenAI, Google Gemini, Anthropic Claude, OpenRouter,
   Ollama Cloud, a custom OpenAI-compatible service, or Ollama on this
   computer.
2. Paste the key, unless it is Ollama on this computer, which needs none.
3. For a custom service or a local Ollama, check the Server address.
4. Press **Test the Key** (for Ollama, **Test the Connection**). The Model list
   fills from your account or from Ollama.
5. Pick a model and press OK. The basic AI commands and the advanced features
   both use it from then on.

Most cloud providers come with their host URL already filled in, so setup is
mostly about the key. For an unusual OpenAI-compatible endpoint, choose Custom
and set the host and model yourself. With Google Gemini, a model you pick from
the list QUILL fetches works as it is. Gemini names its models
`models/gemini-...`, and QUILL drops that prefix for you.

QUILL keeps any key you enter in Windows Credential Manager, with a
DPAPI-encrypted file as a fallback, and speaks the result of every check in
plain words.

#### Connection status messages

Each message tells you what to do next:

- "Authentication failed. Check your API key." The key was rejected (HTTP
  401). Enter it again.
- "Access denied. Your API key is valid but lacks permission for this model
  or region." The key works but is not allowed for that model, region or
  billing tier (HTTP 403). Check the provider's model access, billing or
  quota.
- "The AI provider is warming up. Try again in a moment." The model is still
  loading. QUILL retries briefly on its own before telling you this.
- "The local AI server is not running. Start Ollama and try again." QUILL
  could not reach your local endpoint.
- "Rate limited by the AI provider. Wait a moment and try again." You sent
  requests too quickly.
- "Your saved API key could not be unlocked on this device. Open AI
  Connection and enter the key again." This shows in the AI status line when a
  saved key cannot be decrypted. It can happen after you move a portable copy
  of QUILL to a different Windows account or computer. Open AI Connection and
  enter the key again.

### Trust and privacy baseline

- The first time you run QUILL, it shows a trust and privacy consent
  acknowledgement.
- QUILL does not keep AI chat transcripts by default.
- Nothing goes to a cloud service until you choose an AI action yourself.
- API keys are stored in Windows Credential Manager when it is available,
  with DPAPI-encrypted storage as a fallback.

For the full policy, see the repository's `docs/legal/PRIVACY.md` and
`docs/legal/RESPONSIBLE_AI_USE.md`. The AI Privacy Reference at the end of
this chapter lists exactly what each AI action sends, and where.

## Ask Quill Chat setup (on-device AI)

Ask Quill Chat (**AI > Ask Quill...**, `Alt+Q`) is a message-style assistant.
You type, it answers. It can also draft text, suggest edits and run QUILL
commands for you, but nothing changes until you approve it.

It can run entirely on your own computer:

- Windows and Linux: `llama.cpp` (`llama-cpp-python`, with a GGUF model).
- macOS on Apple Silicon, macOS 26 or later: Apple Foundation Models.

To set up the on-device model:

1. Install the dependencies: `pip install -r requirements.txt`
2. Put a `.gguf` model in `%APPDATA%\\Quill\\models\\` (Windows), or set the
   `QUILL_LLAMA_MODEL` environment variable to the model's full path.
3. Open **AI > Ask Quill...** and send a prompt. (The older Writing Assistant
   window is no longer on the menu; type "Writing Assistant" in the Command
   Palette, `Ctrl+Shift+P`, if you still want it.)

You can connect another provider instead of the on-device model: Ollama on
your own computer or in the cloud, or a custom endpoint.

### Getting around the chat

The whole conversation is an accessible web page. Each turn is a heading
named for the speaker, so you can jump between turns with your screen
reader's heading keys. New replies are announced as they arrive, and the
message box sits inside the page. Press `Escape` to close the chat. It has
been checked with NVDA, JAWS and VoiceOver.

A bar at the top always shows the **active provider and model**, so you know
what is answering. Select **Change provider or model** to open the picker
right there. Choose a provider and model, enter a key if one is needed, and
select **Save**. That choice also becomes the default for your next chat.

### Asking out loud and hearing the answer

Press `Ctrl+F9` in Ask Quill to ask a question by voice. Press it once to
start recording and again to stop. QUILL turns your speech into text **on
your own machine** and sends the text. Nothing you record leaves the
computer.

**AI > Voice Reply Settings...** chooses how answers come back. The setting
covers every reply, however you asked:

- **Announce a short summary**: the default. Brief, spoken by your screen
  reader, offline and free.
- **Show as text only**: nothing is spoken. Read the reply in the transcript.
- **Read aloud with QUILL's own voice**: the full reply, in whichever offline
  voice you use for Read Aloud (Kokoro, Piper, eSpeak, DECtalk, SAPI).
  Offline and free.
- **Read aloud with the AI voice**: the full reply, in a voice from **OpenAI**
  or **Google Gemini**.

A few things to know about these choices:

- When a reply is **spoken**, you hear all of it. The length limit is only for
  announcements, so a spoken reply is never cut off mid-sentence. Set the
  limit to 0 to have the whole reply announced too.
- The length you set covers **everything** Ask Quill announces: answers,
  error messages, and the summary of an edit it suggests. Errors and edit
  suggestions are always announcements, whichever reply mode you pick, and
  follow the length you chose.
- Choosing **AI voice** shows the provider, model and voice. The voice list
  always matches the provider you picked, so you cannot pair an OpenAI
  provider with a Gemini voice by mistake. **Preview this voice** reads a
  sample line so you can hear it first.
- The AI voices cost money and are less private than the others. The reply
  text goes to OpenAI or Google to be spoken, and you are billed per
  character. The dialog tells you this and estimates the cost of a typical
  reply. QUILL never picks an AI voice for you.
- If an AI voice cannot be used, for instance because there is no API key for
  that provider, QUILL reads the reply in an offline voice instead and tells
  you why. You never lose an answer because a voice was unavailable.

> **QUILLBee's tip:** Every turn in Ask Quill is a heading, so your screen
> reader's heading key hops from answer to answer. When you are done,
> `Escape` closes the chat.

### Putting chat content into your document

- The **Insert into document** controls at the bottom put chat content
  straight into the editor. Choose the **scope**, **Last response** or
  **Entire transcript**, and the **format**, **Plain text**, **Markdown** or
  **HTML**, then select **Insert**. The whole transcript includes the speaker
  labels. The last response goes in as just its content.
- **Copy Last Response** copies the most recent reply to the clipboard.

### Reading back, listing and exporting the conversation

Three things help in a long chat, and they work the same way in the **AI
Conversation** window (see Having a conversation, earlier in this chapter).

**Hear a recent message without moving.** Press `Alt+1` to hear the newest
message, `Alt+2` for the one before it, and so on up to `Alt+0` for the tenth
newest. Each one is said with its place and its speaker, for example "Message 7
of 12, You: what about the budget?". The newest starts with the word "Newest".
Nothing moves: focus stays in your message, and anything you had half typed is
still there. These keys work from the message box and from anywhere else in
the Ask Quill window.

- With fewer messages than the key asks for, QUILL says how many there are,
  for example "There are only 3 messages so far. Alt+3 reads the oldest."
- The message is read as words, not Markdown: no hash marks, stars or link
  addresses. To read it exactly as it arrived, use the message list below.
- Example: you ask for a summary, then ask two follow-up questions. The
  summary is now five messages back (your two questions and their two
  replies came after it), so `Alt+5` reads it again while you keep typing
  your next question.

**Message List...** (a button at the bottom of the window; `Tab` reaches it)
shows every message in one list, oldest first, each row like "Message 2 of 6,
Quill: Here is the plan...". The list starts on the newest message, or on the
row you were on last time.

- `Enter` (or **Open**) shows that message in a reading window where its
  headings and tables are real ones. In your screen reader's browse mode, `H`
  moves by heading and `T` by table, and the table commands read a row or a
  column with its headers.
- **Read as Text** shows the same message exactly as it arrived, Markdown and
  all, in a plain text box you can arrow through, select and copy.
- Close either one with `Escape` and you are back on the same row of the list.

**Export Conversation...** saves the whole conversation to a file of its own.
Choose **Word document** or **Text file** in the Save As window and name it.

- Every message is kept, in order, with who said it. In a Word file each
  message is a level-2 heading, "Message 3 of 12, Quill", with the message
  underneath. Headings inside a reply become level 3 and lower, and tables
  become real Word tables. In a text file each message is a paragraph that
  starts with its speaker, "You:" or "Quill:".
- If the file already exists, the Save As window asks before replacing it.
  Choosing **Cancel** writes nothing.
- Your document is never touched. Exporting does not insert anything, change
  your document's name or mark it saved. (To put chat text into your
  document, use **Insert into document** above.)
- If the file cannot be written (a folder you cannot write to, or a drive that
  is full), QUILL says why, and any file already there is left as it was.

**Headings in the chat.** Each message is a level-2 heading naming who said
it. A reply that has its own headings now has them at level 3 and below, so
your screen reader's heading list shows the conversation, and each reply's
sections sit inside their message.

**If the chat window cannot show its web view** (on a few computers the
built-in browser component is missing), the conversation is a plain list
instead, one row per message. Press `Enter` on a row to open that message
with its headings and tables, and you come back to the same row. When a new
reply arrives while you are reading the list, your place in it does not move.

### What the assistant will and will not do

- It answers in the chat by default. Greetings and questions never turn into
  document edits.
- Anything that would change your document (insert, replace, run a command)
  waits for you to choose `Approve` or `Discard`.
- If the model or runtime is unavailable, QUILL tells you plainly and changes
  nothing.
- **Train Writing Style** (**AI > More > Train Writing Style...**) teaches the
  assistant your own style, from samples or from the current document.

## The AI Hub

The **AI Hub** (**AI > AI Hub...**) holds the settings for QUILL's advanced AI
features: the agent engines, audio services, document services, your custom
instructions and saved sessions.

### Choosing a provider

The Hub used to have its own Provider list. It is gone, because it was a second
way to pick an AI. Every provider it offered (Ollama on this computer, Ollama
Cloud, Claude, OpenRouter and a custom OpenAI-compatible service) is in **Use My
Own AI Key** now, beside OpenAI and Google Gemini, and the provider you choose
there is the one the advanced features use. Each provider still keeps its own
key, so switching never loses another one's.

The Hub's **Provider** page says which provider is in use and has one button,
**Open Use My Own AI Key**. It saves the Hub, closes it and opens that window.

Ollama Cloud's free personal-use tier, with lower limits, is there too. Use
**Prompt Studio** to save reusable templates and **Agent Center** to build
guided task prompts.

Word and CSV files open in the normal plain-text editor, and AI connection and
chat work with them as usual.

### The tabs

The AI Hub has eight tabs:

- **Provider**: which provider the advanced features use, and the **Open Use
  My Own AI Key** button, where you change it.
- **On-Device**: what Ollama on this computer is and how to start with it. The
  Ollama address is set in Use My Own AI Key now.
- **Audio Services**: enter your Deepgram API key for speaker diarization, and
  set the default maximum number of speakers.
- **Services**: document conversion and OCR, including which services send
  anything off your computer.
- **Instructions**: read, change and share the built-in instructions for every
  AI task. See Custom Instructions below.
- **Sessions**: your saved AI sessions.
- **Advanced**: a privacy consent summary listing every action that sends
  data, and an explanation of Safe Mode. (The old Reset AI Settings button
  reset the provider; choosing another provider in Use My Own AI Key does
  that now.)

The **Engines** tab, second in the row, is covered in the AI engines topic below.

### Custom Instructions

Every AI task in QUILL comes with built-in instructions that tell the AI how
to behave. For example, the spell check instructions tell it to leave
technical terms alone and not to flag British spellings. Each set is plain
text, sent ahead of every AI request for that task. The **Instructions** tab
in the AI Hub lets you read them, add to them, replace them, or turn them off.

To change a task's instructions:

1. Open **AI > AI Hub...** and go to the **Instructions** tab.
2. Select a task from the list on the left, for example "AI Spell Check".
3. The built-in default appears in the lower panel for reference.
4. Type your own instructions in the editor above it. Leave the editor empty
   to use the built-in default. Tasks you have changed show a `*` in the list.
5. Use **Copy Default to Editor** to start from the built-in text and change
   it, instead of writing from scratch.
6. Use **Reset to Default** to throw away your changes and go back to the
   built-in text.
7. Clear **Enable custom instructions for this task** to send no instructions
   at all for that task. The AI then gets only the base prompt.
8. Select **OK** to save. Changes take effect at once.

#### What each task gets by default

| Task | Default instruction focus |
|------|--------------------------|
| Ask Quill / Chat | Calm, direct expert partner; insert-only text returns without preamble |
| AI Spell Check | Copy editor: genuine errors only, preserve technical terms and consistent spellings |
| Grammar and Style | Professional editor: actionable issues, preserve author voice |
| Rewrite | Improve clarity without erasing author voice; no added content |
| Summarize | One-fifth length, same register, core argument only |
| Expand | Develop into richer prose, match tone exactly |
| Table of Contents | Explicit headings only, Markdown hierarchy, no invented structure |
| Translate | Natural expression over literal fidelity, preserve formatting |
| AI Thesaurus | Contextual synonyms ranked by interchangeability, register noted |
| Document Q&A | Grounded answers only; "not in document" stated explicitly |
| Research Agent | Key points, assumptions, gaps, and suggested next actions |
| Accessibility Tune-Up | Plain language, short sentences, descriptive text suggestions |

The Summarize default is what cloud providers get: one pass, aiming at about
one-fifth of the original length. On the **on-device model**, Summarize runs
its two passes instead, and the second writes to a fixed **word budget** of
about 150 words, not a fraction of the original, which stops a small local
model padding or inventing. Your own instructions still shape how that final
summary reads.

#### Markdown documents keep their formatting

When the document you are working on is **Markdown**, QUILL adds one more
sentence to the instructions for every task that hands your own text back:
AI Spell Check, Grammar and Style, Rewrite, Summarize, Expand and Translate.
(**Check Grammar with AI** is a Prompt Library prompt rather than one of these
tasks; edit its prompt if you want it to say the same.)
It tells the AI to keep the Markdown exactly as it is (headings, lists, bold
and italic, links, pictures, tables and code), never to remove or convert it,
and never to report it as a spelling, grammar or style mistake.

Before this, only Translate had that rule. A rewrite of a Markdown file could
come back with its `##` headings turned into plain sentences and its bullet
list run together into a paragraph, and the grammar check could list `**bold**`
as a typing mistake.

**How QUILL knows it is Markdown.** The same way the rest of QUILL does: the
**Document Language** you pinned for this document, if you pinned one;
otherwise the file's name (`.md`, `.markdown`, `.mdown` or `.mkd`); and, for a
document with no such name, what is in it (headings starting with `#`, list
items, links or code fences near the top).

**An example.** In `notes.md`, select:

```text
## Next steps

- email the team abuot the date
- book the room
```

and run **AI > Proofread > Grammar and Style Check...**. The check reports "abuot" and nothing
else: not the `##`, not the hyphens.

**Limits.** The sentence is added to your own instructions too, and to a task
whose instructions you have turned off, because keeping your document's
structure is not a matter of style. Answers *about* a document (Document Q&A,
the Research Agent, the AI Thesaurus) are new text rather than yours, so they
are left alone. The Free AI Assistant pad and the AI Conversation window use
QUILL's free service's own instructions, which are not covered by this
setting.

#### Sharing instructions

Your custom instructions are saved in
`<AppData>/Quill/ai_custom_instructions.json`. You can copy that file to
another computer, or share single task prompts with other QUILL users.

#### How custom instructions reduce cost

QUILL sends your instructions as a separate system message, apart from the
document text. That lets your AI provider cache the unchanging part of the
request, so you are not billed in full for sending the same instructions every
time:

- **Anthropic Claude**: QUILL marks the system message with
  `cache_control: ephemeral` and sends the required beta header. Claude keeps
  it cached for five minutes, and each cache hit costs about 10% of the normal
  input price. If you run several AI tasks in one sitting, the instructions
  usually come from the cache on every call after the first.
- **OpenAI (GPT-4o and later)**: caching is automatic. OpenAI caches prompt
  beginnings longer than 1024 tokens and reuses them within a session at
  about 50% of the normal input price. Because the system message is always
  the same, it qualifies whenever it reaches that size.
- **Ollama and other local models**: the model server handles caching itself.
  There is nothing to set up, and the system message is sent once per
  connection.
- **Gemini**: instructions go in Gemini's own `systemInstruction` field.
  Whether they are cached depends on Google's current context-caching policy.

You do not have to set anything. As long as at least one custom instruction is
on, or the built-in defaults are in use, QUILL uses caching with every
provider that supports it.

## AI engines

QUILL's agent is the step-by-step help behind Ask Quill and the AI Library
agents, where you review every change. It can run on more than one
**engine**. The built-in **Native** engine always works, with whichever
provider you connected above. Two other kinds are for people who already pay
for something:

- **GitHub Copilot**: if you already pay for GitHub Copilot, you can use that
  subscription directly. A short spoken device code signs you in, no API key
  needed, and it runs on your plan's models.
- **Claude Agent** and **OpenAI Agents**: these connect with the Anthropic or
  OpenAI **API key** you already have. They do not use a ChatGPT or Claude
  chat subscription, because those plans do not include API access.

To choose an engine, open **AI Hub > Engines**, the Engines tab of the AI Hub:

1. Pick **GitHub Copilot**, **OpenAI Agents** or **Claude Agent**, or leave it
   on Native.
2. Select **Set Up / Install...**. For Copilot, which now comes with QUILL,
   this is only the sign-in: the same step as **Choose Your AI**, with GitHub's
   code spaced out and on the clipboard. For the other two, the first time,
   QUILL installs the small connector it needs. **OpenAI Agents** and
   **Claude Agent** use your own API key instead of a sign-in, so once the
   connector is installed, **Set Up** opens a small dialog where you paste,
   save or remove that key. It also tells you whether a key is already saved.
   The change applies at once, with no restart.
3. Select **Set as Active Engine**. From then on, Ask Quill and the agents run
   on that engine, and a status line names it.

The **AI Setup Wizard** offers this too. Choose
**"Use an AI agent you already pay for"** and it takes you straight to the
Engines tab when it finishes.

To change engines without opening the hub, run **Switch AI Engine** from the
Command Palette (`Ctrl+Shift+P`). Each time you run it, QUILL moves on to the
next engine and tells you which one is now active. It has no key to begin
with; give it one in the Keyboard Manager if you switch often.

Whichever engine you pick, your document is just as safe. QUILL makes every
edit itself: the engine only suggests, and each change arrives as an
accessible accept or reject preview that undoes in one step. The vendor
agents run in a text-only mode with their own file-editing and shell tools
switched off, so only QUILL can touch your document, and only with your
approval. All of this is optional, off until you turn it on, and disabled in
Safe Mode.

Signing in to GitHub for Copilot from inside QUILL needs QUILL's own GitHub
registration, which is built in. Until a build carries it, the Sign In button
says sign-in is not available yet, and Copilot still works if you have signed
in with the Copilot or GitHub command-line tool. Copilot keeps its own
sign-in, separate from the one QUILL uses for your repositories, so signing
out of one leaves the other alone.

### The AI and Assistant page in Settings

Providers, models and keys live in the AI Hub. This page holds the switches
and the everyday choices:

- **Use Artificial Intelligence** is the same master switch as the one on the
  AI menu.
- **Open AI Hub...** takes you to the AI Hub, where you set up providers,
  models and keys.
- **Allow external engines** is off to begin with. It lets QUILL run a helper
  program you trust, on your own computer, for a feature that needs one. You
  only need it when a Quillin's instructions ask for it. **External engine
  name** and **External engine command** say which program it is and how to
  start it, and **Enable this external engine** turns that one on. QUILL only
  accepts Node, Python or its own engine program here, and nothing starts
  until both switches are on.
- **Voice question reply** decides what happens when you ask Ask Quill a
  question by voice: a short spoken summary (the default), text only, QUILL's
  own voice, or the AI voice, which is billed by your provider.
  **Announcement length limit** says how many characters that summary may run
  to; 0 speaks the whole reply.
- **Enable writing assistant** and **Assistant prompt style** turn on the
  writing assistant and choose its tone: balanced, concise, gentle or
  technical.
- **Ask AI default provider** and **Ask AI default model** are what Ask AI
  starts on. **AI prompt default model** is the model for prompts from the
  prompt library. Leave a model blank to take the first one offered.
- **Ollama base URL** is where your Ollama server is, if it is not on this
  computer.
- **Default image description style** and **Show style picker before image
  description** decide how Describe Image words its answer. The styles you add
  or hide yourself are kept under **More Preferences > AI Connection**, on the
  **Image Prompt Styles...** button.

Every setting on the page answers F1, and **Find a setting** at the top of
Settings finds any of them, on any page, even one you have not opened yet.

## AI Language Tools

These commands in the AI menu do language work on your document: put scrambled
text back in order, check spelling and grammar, translate, and find the right
word.

### Improve Reading Order (AI)

Some documents arrive with their text in the wrong order: a two-column PDF
that comes out as one jumbled stream, a page with sidebars or text boxes, or
lines out of sequence. **AI > More > Improve Reading Order...** (also in the
command palette) sends the current document's text to your AI provider and
asks it to put the text back in natural reading order. It merges columns into
one flow, joins lines broken mid-sentence, and works out headings, lists and
tables. It keeps your exact wording, and never summarizes, adds or removes
anything.

- **It always asks first.** Before anything is sent, QUILL names the provider,
  its host, and the document's approximate size in pages. Choose **No** and
  nothing is sent.
- **Your document is never changed.** The improved version opens as a **new,
  unsaved document**. Pressing `Ctrl+S` there offers **Save As**, so you decide
  whether and where to keep it. Your original stays exactly as it was.
- **Limits.** It will not take a document longer than the page limit
  (**Settings > `reading_order_max_pages`**, default 40), so a huge, slow or
  costly request cannot happen by accident. It is unavailable in Safe Mode.
- **It uses your own AI provider.** It is not tied to any one service. It uses
  whichever AI you set up in **AI > Set Up AI**: **OpenAI**, **Claude**,
  **Google Gemini**, **OpenRouter**, **Ollama** (local), **Ollama Cloud**, or
  any **custom OpenAI-compatible endpoint**. You bring the account and key.
  QUILL bundles none and adds nothing to your bill.
- **It can stay on your computer.** If you have not set up a cloud provider,
  QUILL uses its **bundled, on-device model**: Apple's on-device model on a
  supported Mac, otherwise a local model that runs on your processor. Then the
  whole repair happens **on your computer with nothing uploaded**. The
  confirmation always names the exact provider and host before anything is
  sent, and if AI is not set up at all, QUILL offers the setup wizard instead
  of failing quietly.

For a *scanned* PDF, which is only pictures of pages with no text, use
**File > Import > Import / Convert Document (OCR)** instead. That reads the
page images and can structure the result. Improve Reading Order is for a
document that already has text, just in the wrong order.

### AI Spell Check

QUILL can send your document to your AI provider for a spelling check. An AI
connection must be set up and turned on, and no text is sent until you choose
the command.

- **AI Spell Check** (**AI > Proofread > Spell Check...**) sends your document and
  returns a list of corrections. A review dialog lets you accept, skip or
  override each one before anything changes.
- **AI Spell Check Interactive** (**AI > Proofread > Spell Check Interactive...**)
  works paragraph by paragraph. While you review one paragraph, QUILL fetches
  the next one's corrections in the background, so the dialog stays quick on
  long documents.

### AI Grammar and Style Check

**AI > Proofread > Grammar and Style Check...** checks the document for grammar,
punctuation, clarity, style and word choice. It has no key by default; you can
give it one in the Keymap Editor. Issues appear in a list grouped by category,
and you can:

- Show just one category (Grammar, Punctuation, Clarity, Style, Word Choice).
- Accept or skip single issues.
- Accept or skip a whole category at once.
- Accept all the issues that are left.
- Press **Apply and Close** to apply the fixes you accepted as one undo step.

### Translate Selection and Translate Document

**AI > Translate > Translate Selection...** and **AI > Translate > Translate
Document...** translate
your text into a language you choose in the dialog. Translate Selection has no
key by default; you can give it one in the Keymap Editor.

**Translate from** is the language your text is in. It starts on **Detect**,
which lets the translator work it out. Choose the language yourself when
Detect gets it wrong: a short passage, or one that mixes two languages, is
easy to misread.

You can choose between two providers:

- **AI Assistant** (the default) uses your cloud or local AI. It works with any
  provider that can follow instructions: OpenAI, Claude, Gemini, Ollama and
  compatible endpoints.
- **LibreTranslate** is a free, open-source translation engine that can run
  entirely on your own computer, with no internet connection once it is
  installed. This is the most private choice: your text never leaves your
  machine. To install it:

  ```
  pip install libretranslate
  libretranslate
  ```
  Then enter `http://localhost:5000` as the URL in the translation dialog.

When the translation is ready, you choose what to do with it:

- **Copy to Clipboard** copies it without changing your document.
- **Replace Original** puts it in place of the selection or the document.
- **Open as New Document** opens it in a new, unsaved document tab.

**When nothing was translated.** Sometimes the text comes back exactly as you
sent it. That usually means it was already in the language you picked: you
asked for English and the passage was English all along, or the provider
quietly turned Spanish into Spanish. QUILL does not dress that up as a
translation. The result box says "The translation came back the same as the
original. The source language may be wrong; choose it instead of Detect." and
takes focus,
so your screen reader reads the sentence to you. Copy to Clipboard, Replace
Original and Open as New Document stay unavailable, because there is nothing
new to use. Spacing, line breaks and capital letters do not count as a
difference, so a result that only rewrapped your lines gets the same message.
Choose the language your text is in from **Translate from**, or pick another
provider, and press **Translate Now** again.

### AI Thesaurus

**AI > More > AI Thesaurus...** finds synonyms for a word using your AI provider. A
printed thesaurus lists every sense of a word; this one reads the sentence the
word is in and gives you synonyms that fit what you meant. It has no key by
default; you can give it one in the Keymap Editor.

1. Put the cursor on a word, or select it.
2. Choose **AI > More > AI Thesaurus...**.
3. The dialog opens with the word filled in and synonyms loading.
4. Arrow through the list. Each item gives the synonym and a short note on how
   it is used.
5. Press `Enter` or select **Replace Word** to put it in your document.
6. To look up another word without closing, type it in the search box.

Only the word (up to 80 characters) and the sentence around it (up to 400
characters) are sent. The full document is never sent for a thesaurus lookup.

## Read Aloud with AI Voice

**AI > Read Aloud > Read Selection Aloud** and
**AI > Read Aloud > Read Document Aloud** use a cloud speech service to read your
text in a natural, expressive voice. They sit alongside the on-device Read
Aloud, which uses local voices such as SAPI 5, Piper, Kokoro, eSpeak and
DECtalk.

Choose the provider, model and voice under **Settings > Read Aloud**:

- **OpenAI**: 11 voices (Alloy, Ash, Ballad, Coral, Echo, Fable, Nova, Onyx,
  Sage, Shimmer, Verse), with `tts-1` (fast) or `tts-1-hd` (higher quality).
- **Google Gemini**: 30 voices (Kore, Puck, Aoede, Fenrir, Zephyr and more),
  with Gemini 2.5 Flash (fast) or Pro (higher quality).
- **ElevenLabs (export only)**: premium, audiobook-grade narration, with
  Multilingual v2 (high quality) or Turbo v2.5 (fast). ElevenLabs is for
  **audio export**, not live reading. It needs the optional `elevenlabs`
  package (`pip install quill[elevenlabs]`) and an **ElevenLabs API key**
  credential, the same key the ElevenLabs transcription provider uses.

Add the API key for your chosen provider in the AI Hub. ElevenLabs uses your
stored "ElevenLabs API key" credential.

- **AI > Read Aloud > Stop AI Reading** stops the current reading.
- **AI > Read Aloud > Export Document as Audio...** saves the whole document as an audio
  file you choose: MP3 for OpenAI and ElevenLabs, WAV for Gemini. The status
  bar shows an estimated cost before the export starts. If you pick ElevenLabs
  for *live* reading, QUILL reminds you it is for export only for now.

Long documents are split only between sentences, never in the middle of a
word, so the audio never stops at an awkward spot. Gemini exports add a short
pause at the end so the last sentence is not clipped.

Your text goes to the provider you chose (`api.openai.com` or
`generativelanguage.googleapis.com`) in chunks split at sentences. QUILL
stores no audio. The AI Privacy Reference below lists the ways to opt out.

## Document Q&A

**AI > More > Document Q&A...** opens a window where you ask questions about your
current document, or about a PDF or text file you choose. It stays open while
you work, so you can switch back to your document or any other window and
return.

- Ask follow-up questions. The window keeps a history of your questions and
  the answers.
- The AI answers only from the document's text.
- Each answer includes an excerpt showing where in the document it came from.
- **Copy or Insert** puts the answer text at the cursor.
- For a document longer than 80 000 characters, only the first 80 000 are
  used, and the window tells you exactly how much ("the answer used the first
  80,000 of its 120,000 characters"), out loud as well as on screen. Status
  changes and errors in this window are spoken too.

To ask about a PDF, select **Browse File** and choose the file. QUILL pulls the
text out on your computer; no internet connection is needed for that.

## Reviewing what the AI suggests

### Reviewing AI changes word by word

Whenever an AI feature wants to change your document, QUILL opens the
**Review AI Changes** dialog and edits nothing directly. It is a checklist of
changes you accept or reject one at a time, and whatever you accept is applied
as a single undo step. Nothing touches the document until you say so.

Each change tells you exactly what it is, with the sentence around it, so you
do not have to hear a whole line twice and listen for the difference. For
example: "Changed 'quick' to 'rapid' at line 3." The details pane adds
**Sentence before** and **Sentence after**, so you can judge a one-word edit
in context, and the full old and new lines are still there below for a
complete review.

When a change really is a rewrite, with many scattered edits or whole passages
replaced, QUILL shows it as old and new lines instead, because forty word
pairs in a row are harder to follow than two whole lines. Changes to spacing
alone are also shown as lines, never spoken as word edits.

### Keeping some words of a change and not others

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

### Suggest Document Metadata

**Suggest Document Metadata...** (in the command palette, and you can give it
a key in the Keymap Editor) asks your AI to suggest front matter for the
current document: a title, a one- or two-sentence summary, a few topic tags
and a category. The suggestions open in a review dialog, one field at a time.
You hear the field name, what it holds now, and the suggested value, then
choose **Accept**, **Accept and Next**, **Skip** or **Copy Value**.

Two safeguards protect what you already have. If a field already holds
something, QUILL asks before replacing it, and the default answer is No. And
nothing touches your document while you review: only **Apply Accepted** writes
the fields you approved into the document's front matter, as one undo step.
Close without applying and the document is exactly as it was.

### Agentic Document Tasks

The AI menu has quick tasks that do one job on your document or selection and
show you the result:

| Command | What it does |
|---------|-------------|
| AI > Transform Selection > Rewrite Selection | Rewrites the selected text for clarity. |
| AI > Transform Selection > Summarize Selection | Produces a concise summary. |
| AI > Transform Selection > Expand Selection | Develops a brief outline or passage into fuller prose. |
| AI > Transform Selection > Generate Table of Contents | Reads the document and returns a table of contents as a Markdown list, with levels. |

All four open an **Agent Result** dialog, where you can:

- Read the result, with a step log if a second, refining pass was run.
- **Insert at Cursor**: put the result in without replacing anything.
- **Replace Selection**: put the result in place of the current selection.
- **Copy**: copy the result to the clipboard.
- **Re-Run**: run the same task again, if the first result was not right.

## AI Privacy Reference

Every AI action in QUILL happens only when you ask for it. Nothing runs in the
background. This table shows what each action sends, and where:

| Action | Data sent | Service | Opt-out |
|---|---|---|---|
| AI Spell Check | Document text (chunked at about 60 000 chars) | Your configured AI provider | Do not invoke the action |
| AI Grammar Check | Document text (chunked at about 40 000 chars) | Your configured AI provider | Do not invoke the action |
| Translate (AI provider) | Selected text or full document | Your configured AI provider | Use LibreTranslate instead |
| Translate (LibreTranslate) | Selected text or full document | Your LibreTranslate server (default: localhost) | Not needed |
| AI Thesaurus | Word being looked up + one sentence of context (no full document) | Your configured AI provider | Do not invoke the action |
| Rewrite / Summarize / Expand / TOC | Selected text or full document | Your configured AI provider | Do not invoke the action |
| Document Q&A | Document text (up to 80 000 chars) + question | Your configured AI provider | Do not invoke the action |
| Read Aloud (AI Voice) | Selected text or document (split on sentence boundaries) | OpenAI (`api.openai.com`), Google Gemini (`generativelanguage.googleapis.com`), or ElevenLabs (`api.elevenlabs.io`, audio export only), per your Settings > Read Aloud choice | Use a local voice (SAPI 5, Piper, Kokoro, eSpeak, DECtalk) |
| Transcribe Audio | Audio file bytes (up to 25 MB) | OpenAI Whisper (`api.openai.com`) | Transcribe locally with a Quillin extension |
| Speaker Diarization | Audio file bytes (up to 2 GB) | Deepgram (`api.deepgram.com`) | Disable diarization in the transcription dialog |

### What QUILL never does

- QUILL never sends data in the background. Every AI call comes from something
  you chose to do.
- QUILL does not log your document content, API keys or AI responses to any
  Anthropic or QUILL telemetry endpoint. QUILL has no telemetry.
- API keys stay on your computer (Windows Credential Manager, with DPAPI as a
  fallback). They are never sent to a QUILL server.
- The crash reporter (**Help > Save Diagnostics**) removes API keys, file paths
  and anything that looks like a secret before it writes the diagnostic
  bundle.

### Keeping everything on your computer

If you would rather your text never left your machine:

- Use **Ollama (local)** as your AI provider. Spell check, grammar and
  translation requests then go only to Ollama on your own computer.
- Use **LibreTranslate**, installed locally, for translation.
- Use **Piper** or **Kokoro** for Read Aloud. These are local voices.
- Avoid the Transcribe and Diarize actions, which need cloud services.

## What you learned, and where to go next

You learned that AI in QUILL is optional and only acts when you ask. You can
use the free AI or your own key, sign in with a ChatGPT subscription, and set
it all up with the wizard and the AI Hub. You met Ask AI, the prompt and skill
libraries, the quick writing actions, Ask Quill Chat, and the AI engines. You
saw the language tools (reading order, spelling, grammar, translation and the
AI thesaurus), AI voices, Document Q&A, and how every change waits for your
review. And you know exactly what each action sends.

To practise, open **Help > Tutorials...** (`Ctrl+Alt+F1`) and try the track
"The assistant, if you want one": "Set up the assistant, or do not", "Ask, and
run a prompt" and "The assistant on one piece of text".

Next, Chapter 11, Accessibility, speech and braille, shows how to tune what
you hear and feel while you work.

---

- Previous: [Chapter 9: Dictation and transcription](quill-guide-09-dictation-and-transcription.html)
- Next: [Chapter 11: Accessibility, speech and braille](quill-guide-11-accessibility-speech-and-braille.html)
- [Contents](../userguide.html)
