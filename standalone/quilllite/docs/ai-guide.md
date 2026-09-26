# QUILL Lite's free AI: the complete guide

*QUILL Lite 1.0. Updated September 25, 2026.*

QUILL's free AI helps with the writing in front of you: summarize it, rewrite
it, proofread it, explain it, or answer a question about the document you have
open. It is built into QUILL Lite, it is free, and it needs no account, no
password and no card.

This guide explains everything: how to start, what each command does, exactly
which text is sent, what happens to the answer, the limits, and your privacy.

## Contents

- [Starting, in about a minute](#starting-in-about-a-minute)
- [The keys](#the-keys)
- [The AI pad](#the-ai-pad)
- [The five things it can do](#the-five-things-it-can-do)
- [Exactly what is sent](#exactly-what-is-sent)
- [Asking about a whole document](#asking-about-a-whole-document)
- [When something is too long](#when-something-is-too-long)
- [The answer window](#the-answer-window)
- [Usage, About and your support ID](#usage-about-and-your-support-id)
- [Limits, and when they start again](#limits-and-when-they-start-again)
- [When something goes wrong](#when-something-goes-wrong)
- [Your privacy](#your-privacy)
- [Signing out and changing your mind](#signing-out-and-changing-your-mind)
- [Using your own OpenAI key: no limits](#using-your-own-openai-key-no-limits)
- [Questions people ask](#questions-people-ask)

## Starting, in about a minute

You do this once per computer.

1. **Open the agreement.** Press **Ctrl+Alt+Shift+K**, or choose **Tools ▸ AI ▸
   Privacy Agreement**. It is there even while AI help is switched off.
2. **Read it, and choose I Agree.** It says what is sent, what is kept, what is
   not kept, and how to change your mind. Agreeing switches AI help on; there is
   no second switch to find. Choosing **No Thanks** sends nothing and changes
   nothing.
3. **Connect this computer.** The Connect window opens by itself, already
   showing an **eight-character code**, spoken as well as shown. Press **Open
   the Connect Page**: your browser opens with the code filled in, so all that
   is left is **Confirm**. The window says when you are connected.
   - Not at the computer you are connecting? Type the code at the address the
     window names, on any device. A phone is fine.
   - **Say the Code Again** reads it one character at a time, and **Copy the
     Code** puts it on the clipboard.
4. **Try it.** Put the cursor in any paragraph, press **Ctrl+Alt+G**, choose
   **Summarize**, and press **Send**.

There is no account, no password and no email address. The code is the whole
of it.

Reaching for any AI command before you have agreed shows you the agreement
first. Reaching for one before this computer is connected takes you to the
Connect window.

## The keys

All six are in **Tools ▸ AI**.

| Command | Key |
|---|---|
| AI Assistant | Ctrl+Alt+G |
| Ask About This Document | Ctrl+Alt+Z |
| Usage | Ctrl+Alt+Shift+F9 |
| Connect or Sign Out | Ctrl+Alt+Shift+F10 |
| Privacy Agreement | Ctrl+Alt+Shift+K |
| Use My Own OpenAI Key | Alt+F2 |

Every key can be changed in **Tools ▸ Keyboard Manager**.

**Escape closes every AI window.** Nothing is lost by closing: the pad and the
answer are about a moment, and nothing in your document changes unless you
pressed a button that said so.

## The AI pad

**Ctrl+Alt+G** opens the pad on whatever your cursor is in. From top to
bottom:

1. **About to send** — one sentence: how much will be sent, from where, and
   whether it fits the free limit. For example, "About to send 84 words from
   this paragraph."
2. **What will be sent** — a read-only box holding *exactly* the text that will
   go, and nothing else. Focus starts here, so the first thing you hear is the
   text itself. Arrow through it at your own pace.
3. **Send this much** — which part of your document to send. Only offered when
   there is a real choice; see [Exactly what is sent](#exactly-what-is-sent).
4. **What do you want done?** — the five things, in a list. Press **F1** on any
   one to hear what it does.
5. **Your question** — only there when you choose **Ask a question about the
   document**.
6. **Send**, and **Close**.
7. **Status** — what happened to the last request: working, how many requests
   it used, or what went wrong.

Every line in the pad is reachable with **Tab**, including the summary and the
status, so nothing is said once and lost.

**The editor never waits for the AI.** Requests run in the background. Keep
typing, save, switch documents, or close the pad while the answer is on its way.

## The five things it can do

- **Summarize** — a few plain sentences saying what the passage says. Good for
  the long email, the dense report, the terms and conditions nobody reads.
- **Rewrite** — the same meaning, clearer and shorter. Good for the paragraph
  you have rewritten four times and still do not like.
- **Proofread** — spelling, grammar and punctuation corrected, your wording left
  alone. The corrected text comes back for you to compare with your own; nothing
  in your document changes until you choose to put it there.
- **Explain** — what the passage means, in plain language. Good for jargon, a
  legal clause, or a paragraph that will not sit still.
- **Ask a question about the document** — type a question, and QUILL Lite finds
  the parts of the document that answer it. See [Asking about a whole
  document](#asking-about-a-whole-document).

**Ctrl+Alt+Z** opens the pad with the question already chosen, so you can type
straight away.

## Exactly what is sent

For Summarize, Rewrite, Proofread and Explain, the pad sends **one piece** of
your document, and it picks the piece like this:

1. **If you have selected text**, the selection is sent.
2. **If you have not**, the **paragraph your cursor is in** is sent. A paragraph
   is the text between one blank line and the next. You do not have to select
   anything: put the cursor anywhere in the paragraph and press the key.
3. **If your document has headings**, you can choose **This section** instead:
   everything from the heading above your cursor to the next heading.

**Send this much** lets you switch between whichever of those apply —
**What I have selected**, **This paragraph**, **This section** — and the
**What will be sent** box rewrites itself the moment you change it. When only
one of them applies, the chooser is not shown at all, because a choice with one
option is just another stop on every Tab.

A few details worth knowing:

- **Sections follow Markdown-style headings** — lines that start with `#`, or a
  line underlined with `===` or `---`. In a document without them, **This
  section** is not offered.
- **A document with no blank lines is one paragraph.** In that case "this
  paragraph" is the whole file, and the size check below is what stops a very
  long one.
- **Nothing else goes with it.** Not the rest of the document, not the file's
  name, not where it is saved. The box shows the whole of what is sent.

## Asking about a whole document

**Ask a question about the document** works differently, and it is why a long
document is a perfectly fair thing to ask about.

Instead of sending the whole file, QUILL Lite reads it **on your own
computer**, splits it into passages of about **180 words**, each labelled with
the heading it sits under, and picks the **three passages most likely to answer
your question**. It sends only those, with your question.

- **The pad shows you the passages it chose** before you press Send, in the
  **What will be sent** box, each one named "Excerpt 1, from *heading*". If
  they are not the right ones, rephrase the question with the words the
  document itself would use.
- **A passage whose heading matches your question counts for more**, because a
  heading is the author's own label for what the passage is about.
- **A question with no useful words in it** — "what is it?" — gets the opening
  passages of the document, which is a better guess than nothing.
- **A very long document** is searched up to about the first 375,000 words. The
  pad says so when that happens; put the cursor nearer what you mean, or select
  a part and use one of the other four instead.
- **The answer comes from those passages.** If the document says something
  somewhere else, the AI did not see it.

## When something is too long

One request can hold about **3,000 tokens** — roughly **2,250 words** or
**12,000 characters**, counting the text, your question and the instructions
together. The answer itself is up to about 500 tokens, a few hundred words.

If what you are about to send is bigger, the pad says so **before** you press
Send, in words rather than tokens — "That is about 4,000 words, and the free
limit is about 2,250." Select less, or choose a smaller part in **Send this
much**. Nothing is sent and nothing is used.

## The answer window

The answer arrives in its own window, titled after what you asked for —
**Summary**, **Rewrite**, **Proofread**, **Explanation** or **Answer**. Focus
lands on the answer, so your screen reader starts reading it. Under it:

- **Replace My Selection** — puts the answer where your selection was. Only
  offered when you had text selected, and only while that text is still exactly
  where it was: if you changed it while the answer was on its way, Replace is
  left out rather than writing the answer over words it was not about.
- **Insert Below** — puts the answer underneath the paragraph your cursor is in,
  after a blank line, rather than in the middle of a sentence.
- **Copy** — puts the answer on the clipboard.
- **Try Again** — sends the same text again for a different answer. This uses
  one more request.
- **Requests** — how much of your allowance this answer used.

**Every edit can be undone.** Replace and Insert Below go through the ordinary
undo, so **Ctrl+Z** takes an AI edit back exactly like your own typing.

## Usage, About and your support ID

**Usage** shows what you have used and what is left this month and today, when
each count starts again, and your **support ID**. It asks the service every time
you open it, so the numbers are always current. **Sign Out This Computer** and
**Copy Support ID** are here too.

**Help ▸ About** shows the same allowance and support ID, under **QUILL's free
AI**, once this computer is connected. Give it a moment after About opens: the
numbers are fetched while you read.

With **your own OpenAI key** saved, both show something different: the model in
use and where your OpenAI usage page is, instead of an allowance. See *Using your
own OpenAI key*, below.

Your **support ID** is a short code like `A1B2-C3D4`. It is the only way support
can find your account, because there is no name on it. **Get Help from Support**
puts it into your message automatically when this computer is connected.

## Limits, and when they start again

The service is free because it is shared, so there is an allowance:

| Limit | How many | Starts again |
|---|---|---|
| Requests a month | 100 | The 1st of the month |
| Requests a day | 20 | Every night |
| Requests an hour | 8 | At the top of each hour |
| Any one kind of request a month | 60 | The 1st of the month |
| A new connection's first 48 hours | 15 | Rises to 100 on its own |

These are the service's current settings. They live on the service, not in
the program, so they can change without an update — and **Usage** always shows
the numbers that apply to you right now.

- **The service keeps time in UTC.** The daily count starts again at midnight
  UTC: **8 PM Eastern** or **5 PM Pacific** in summer, an hour earlier in
  winter. The monthly count starts again at midnight UTC on the 1st.
- **Only answers count.** A request that does not come back with an answer — too
  long, no connection, a problem on the service, a limit already reached — uses
  nothing. Opening Usage or About uses nothing.
- **A new connection starts smaller.** For its first 48 hours a newly connected
  computer has 15 requests, and then the full allowance applies by itself. It is
  how a free service with no accounts stops somebody scripting connection after
  connection. Signing out and connecting again starts a new connection, so it is
  never a way to get more.
- **Computers sharing one internet connection** — a household, a class, a
  library — also share a few limits on that address: how many can be connected
  at once, how many new connections an hour, and a monthly total. Signing a
  computer out gives its place back. If a class runs into these, write to
  support.
- **Need more?** Choose **Get Help from Support** and say what it is for — a
  course, a deadline, a book. Support can raise your allowance, including ending
  the new-connection allowance early. It applies from your next request; there
  is nothing to reinstall and nothing to reconnect.

## When something goes wrong

When a request fails, the pad's **Status** line says what happened and what to
do, and **focus moves to it** so your screen reader reads it — and you can read
it again with the arrow keys. If the pad is not in front at the time, the
message is spoken instead, and focus is waiting on it when you come back.

The message ends with an error code, such as `QUILL-AI-GATEWAY-QUOTA` for a
limit. It is worth including if you write to support. The common ones:

- **A limit was reached.** The message names the limit and when it starts again.
  Nothing was used.
- **No connection.** Nothing was sent and nothing was used. Try again when you
  are online.
- **The free AI is paused.** The service has a spending ceiling for everybody
  together; when it is reached, the free AI pauses for everyone until the 1st.
  This is rare, and nothing is wrong with your computer.
- **This computer was signed out.** Choose **Connect or Sign Out** and connect
  again.

## Your privacy

- **What is sent:** only the text shown in **What will be sent**, plus your
  question if you asked one. It goes to QUILL's service and on to OpenAI, which
  writes the answer.
- **What is kept:** how many requests you made, how big they were, which of the
  five you used, and what it cost.
- **What is not kept:** what you wrote. What came back. Your name, your email
  address, or anything else that identifies you — connecting a computer creates
  an account with no name on it at all.
- **When it is sent:** only when you press **Send**. Nothing is sent as you type,
  on save, in the background, or when you open the pad. Closing the pad without
  pressing Send sends nothing.

The service's own page, **https://ai.community-access.org**, explains the same
things and publishes what the service costs to run.

## Signing out and changing your mind

- **Sign Out This Computer** is in **Usage**. Press it twice — the second press
  confirms. You can connect again at any time.
- **Reading the agreement again is safe.** Once you have agreed, **Privacy
  Agreement** (Ctrl+Alt+Shift+K) opens it with two buttons: **Keep Using AI**,
  which is what Enter and Escape do, and **Withdraw and Sign Out**. Nothing
  changes unless you choose the second.
- **Withdrawing** switches AI help off **and** signs this computer out, in one
  step, because keeping the key to a service you have just declined would be the
  wrong way round.
- **Privacy Agreement opens whether or not AI is switched on**, and whether or
  not you ever agreed. A door you can only reach by agreeing to something is not
  a door.

## Using your own OpenAI key: no limits

If you have an OpenAI account, you can use **your own key** instead of QUILL's
free service, and **every limit goes away**: no monthly, daily or hourly
allowance, no 2,250-word ceiling, no smaller first 48 hours.

**Tools ▸ AI ▸ Use My Own OpenAI Key** (**Alt+F2**) opens one window:

1. **About this** — a read-only box saying exactly where your text goes.
   Arrow through it once.
2. **OpenAI API key** — paste your key here. You make one at
   platform.openai.com, under API keys. It starts with `sk-`.
3. **Model** — a list of every model your key can use for text, filled
   from your OpenAI account once the key is checked: **Luna 6 first, then the
   other GPT-6 models**, then the rest by name. Each row says roughly what it
   costs, for example "gpt-6-luna, about $0.57 per 100 requests (estimate)", so
   arrowing down the list is enough to compare them. Models that cannot answer
   text — speech, transcription, images, embeddings — are left out.
4. **Cost estimate** — the chosen model's estimate per request and per 100
   requests. **These are estimates to help you compare, not OpenAI's prices.**
   A typical request here is about a page in and a paragraph back; the real
   prices are at openai.com/api/pricing.
5. **Status** — whether a key is saved, and what the last test said.
6. **Test the Key** — checks the key with OpenAI, fills the model list,
   then sends one tiny request to the chosen model and says whether it
   answered. The request costs a fraction of a cent.
7. **Remove the Saved Key** — forgets the key **at once** and puts AI help
   straight back on QUILL's free service.

Press **OK** and the key is saved. QUILL Lite says "AI help uses your own OpenAI
key, with no limits."

**Change the model at any time.** With a key saved, opening this window
lists your models straight away: press **Alt+F2**, pick another, press OK.

**There is no separate switch.** While a key is saved, AI help uses it; remove
the key and AI help is back on the free service, with its free allowance, the
moment you do. Nothing else to find and turn off.

**What changes with your own key:**

- Your text goes **straight from this computer to OpenAI**, on your account.
  Nothing passes through QUILL's servers, so QUILL records nothing at all —
  not even the count it keeps for the free service.
- **OpenAI bills you** for each request, under OpenAI's own terms and privacy
  policy.
- **Usage** (**Ctrl+Alt+Shift+F9**) opens a different window: which model is
  answering, that no allowance applies, and an **Open My OpenAI Usage** button
  that takes you to your OpenAI account's usage page, which is where your
  requests and charges are. There is no Sign Out and no support ID in it,
  because neither applies. **Help ▸ About** likewise shows the model and that
  page's address instead of the free allowance.
- You do not need to connect this computer, and the free service's agreement
  is not asked for: it is about QUILL's servers, which this route never touches.
- The pad, the five things it can do, and what comes back are **exactly the
  same**, down to the instructions sent with your text. The pad still tells you
  before sending something very large, because with your own key a large request
  costs you money.

**Where the key is kept.** In Windows' own credential store, not in a settings
file, and it is never shown again once saved — the box stays empty and says
a key is saved. A portable copy keeps it in an encrypted file instead. QUILL and
QUILL Lite share it: a key saved in either works in both, and removing it in
either removes it from both.

**If a request fails**, you hear why, followed by error code
`QUILL-AI-OWN-KEY-FAILED`. The usual causes are a mistyped key, a model your
account cannot use, or an OpenAI account with no credit. **Test the Key** tells
you which.

## Questions people ask

**Do I need an account?** No. No name, no email, no password. The
eight-character code connects this computer, and that is all.

**Does it cost anything?** No. It is paid for by Community Access. If you use your own OpenAI key instead, OpenAI bills your account and there are no limits.

**Can it change my document without asking?** No. Nothing goes into your
document until you press **Replace My Selection** or **Insert Below**, and
**Ctrl+Z** takes either back.

**Does it read my whole document?** Only when you ask a question about the
document, and even then only the three passages it picks are sent — and the pad
shows you which before you press Send.

**Why is my allowance 15 when I was told 100?** This computer connected less
than 48 hours ago. The full allowance applies by itself when that time is up;
Usage says exactly when.

**Why did my daily requests come back in the evening?** The service keeps time
in UTC, so in North America the new day starts in the evening.

**Who do I ask for help?** Choose **Get Help from Support** in the Help menu, or
write to **support@community-access.org**. A person reads it.
