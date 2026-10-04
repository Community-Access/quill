# QUILLBert and QUILLBee: a guide for people writing about QUILL

QUILLVille has two characters now. This page is for anyone writing the website,
a user guide, release notes, or (later) text inside the apps, and wondering
whether one of them belongs in what they're writing. Most of the time the
answer is no. When it's yes, this is how to do it well.

Jeff introduces them to everyone else on the website, at
[Meet QUILLBert and QUILLBee](https://www.quillforall.org/meet-quillbert-and-quillbee.html). Read that
first. It sets the tone better than any rule here.

## The one-line rule

**QUILLBert discovers. QUILLBee explains.**

They belong together, and they must never feel interchangeable. If you could
swap the names on a callout and nothing would feel wrong, it's written wrong.

## Who they are

**QUILLBert** is the curious QUILLVille porcupine. He's the explorer, the
mascot, the wanderer, the one who presses the button to see what it does. He
stands for curiosity, trying things, community and fun, and for the idea that
useful technology can also be a delight. Every now and then he finds something
he probably wasn't supposed to find yet. He's "he".

**QUILLBee** is the guide. Clear, calm, patient, capable. QUILLBee explains how
things work, hands you the faster way, points out the detail that saves you a
detour, and meets you wherever you are. Refer to QUILLBee by name, or as
"they" when a pronoun is unavoidable. The name reads better anyway.

## When each one shows up

QUILLBert appears when something is worth trying:

- introducing something new, or welcoming people somewhere
- a feature that's easy to miss, or switched off by default
- celebrating a release or a milestone
- something experimental
- moving between parts of QUILLVille, from one app to another

QUILLBee appears when something is worth understanding:

- a useful tip, a keyboard shortcut, a faster way
- an accessibility feature and how to use it
- getting started, and the first few minutes with an app
- a word that needs explaining
- a common mistake and how to avoid it
- where to read more

Together, rarely. A short exchange where QUILLBert has found something and
QUILLBee explains it. Keep it to four lines or so. If the pair turns up on every
page, it stops being special, and special is the whole point.

## Their voices

**QUILLBert**: curious, energetic, warm, a bit unpredictable, occasionally
mischievous. He can be funny. The joke is on him, never on the reader. Vary how
he arrives: "QUILLBert found something", "QUILLBert noticed",
"QUILLBert wandered over here and found", "QUILLBert's Corner". Don't use the
same opener everywhere.

**QUILLBee**: calm, friendly, concise, reassuring without patting anyone on the
head. Knowledgeable without sounding like a manual wearing a hat. QUILLBee
explains and never lectures. Vary the openers here too: "QUILLBee's tip",
"QUILLBee's shortcut", "A note from QUILLBee".

For both of them, write like a person who likes the people reading. Use
contractions. Mix long sentences with short ones. A fragment now and then is
fine. Plain ASCII punctuation: no em dashes, no curly-quote habits, no
decorative symbols.

Leave these out entirely: "Whether you're a beginner or an expert", "Dive into",
"Unlock the power", "Seamlessly", "Elevate", "In today's fast-paced world",
"We're thrilled to announce", "Game-changing", "Empowering", "journey",
"endless possibilities", three-part slogans, strings of rhetorical questions,
and a summary of what you just said.

Before you keep a line, ask:

- Does a person actually talk like this?
- Is it useful?
- Is it fun without trying too hard?
- Does it belong right here?
- Would I still like it the fiftieth time I read it?

## Ground rules

- **Every line must be true.** Check keys, menu names and behaviour against the
  app's user guide (`standalone/<app>/docs/userguide.md`, or
  `docs/user guide/userguide.md` for QUILL) and, when in doubt, the keymap.
  A character who teaches a key that doesn't work is worse than no character.
- **Never inside step-by-step instructions.** A callout goes before the steps or
  after them, never between step 3 and step 4.
- **Restraint.** Not every section gets a callout. One or two on a page is
  plenty, and a page with none is normal.
- **No invented features.** There is no "Ask QUILLBee" command and no QUILLBert
  mode. Don't write as if there were. Saying they'll wander into the apps later
  is fine; promising what they'll do there is not.
- **Accessibility is never cute.** The characters can be playful about
  themselves. They're never playful about a screen reader, a disability or the
  person reading.

## The callout component (website)

One pattern covers both characters. The styles live in
`docs/site/assets/style.css`, in the block headed "QUILLVille characters".

### Markup

```html
<div class="qv-callout qv-callout--bee">
  <p class="qv-callout__label">QUILLBee's shortcut</p>
  <p>Every guide on this page is built on headings. ...</p>
</div>
```

- A plain `<div>`, not an `<aside>` or any other landmark. A callout is a
  short aside in the reading flow, and you meet it by reading, not by jumping
  to it.
- The **label** is a real `<p>` and always comes first. It names the character
  in words ("QUILLBee's tip", "QUILLBert found something"), so the meaning never
  depends on colour, a border or a picture. It's what someone hears first.
- No ARIA at all: no `aria-label`, no `aria-labelledby`, no `role="note"`.
  The visible label already says who is talking, and it is the first thing
  read.
- An optional link goes in its own `<p>` at the end, with link text that makes
  sense on its own ("Try the QUILL Cast lesson", not "click here").

Why not a landmark? We tried it first, as a named `<aside>`. A screen reader
then said the name twice every time you arrowed in: once as the landmark and
once as the label. Jeff chose to hear it once (2026-10-03). The cost is that
the landmark key no longer jumps between callouts, which is fine: they are
few, and they are never where the information you need lives.

### Variants

| Class | Who | Visual cue besides the label |
| --- | --- | --- |
| `qv-callout--bert` | QUILLBert | dashed left edge, dashed badge |
| `qv-callout--bee` | QUILLBee | solid left edge, solid badge |
| `qv-callout--both` | the pair | double left edge, double badge |

The border style is the second cue because Windows High Contrast recolours
borders instead of throwing them away. Colour is the third cue and only
decorates. Body text stays at the page's normal text colour in light, dark and
high-contrast modes, so contrast never depends on the character.

### The exchange (both characters)

One paragraph per line, with the speaker's name in text:

```html
<div class="qv-callout qv-callout--both">
  <p class="qv-callout__label">QUILLBert and QUILLBee</p>
  <p class="qv-line"><strong class="qv-line__who">QUILLBert:</strong> I found something.</p>
  <p class="qv-line"><strong class="qv-line__who">QUILLBee:</strong> You pressed every button again, didn't you?</p>
</div>
```

Paragraphs rather than a list or a table: a list adds "list, four items" for
no benefit, and a table makes a conversation into a grid. No ARIA is needed.

### Headings

Most callouts don't have one. Add a heading only when the callout is
substantial, and only at the level the page's outline needs at that spot:
never skip a level, and never add an `h2` just to make it look important. The
stylesheet makes any level look the same inside a callout, so pick the level
for the outline and not for the size.

### Pictures

There's no artwork yet, and nobody should invent any. When there is, an
`<img class="qv-callout__art">` goes straight after the label and floats to the
side. If the picture only repeats the label (a portrait of QUILLBee beside
"QUILLBee's tip"), use `alt=""`. If it shows something the words don't, describe
that in the alt text. Never put the character's name only in the picture.

### Motion, sound and interaction

None. No animation, no hover tricks, no sound, nothing that plays by itself.
The only focusable thing in a callout is an ordinary link, which already gets
the site's focus ring. If motion is ever added, it must stop under
`prefers-reduced-motion`.

### Readable without CSS

Strip the styles and a callout is still a short paragraph that starts with a
name. Check that it reads well that way. It's how many readers meet it.

## In user guides

User guides are Markdown and get rendered to HTML, EPUB and the in-app help, so
the pattern has to survive all of them. Use a **blockquote with the label in
bold**:

```markdown
> **QUILLBee's tip:** Forgotten where something lives? Press Ctrl+Shift+P and
> type a word, like "sort" or "print".
```

Why a blockquote and not a `#### QUILLBee's tip` heading: a heading lands in the
heading list and the table of contents, so ten tips turn a guide's outline into
noise, and it has to fit the level of whatever section it's in. A blockquote
stays out of the outline, is announced as a quote that can be skipped, and
renders sensibly on GitHub, in pandoc's HTML and in an EPUB reader. The
tutorials index (`docs/tutorials/README.md`) already uses it.

Same rules as the website: sparingly, never inside numbered steps, and every
key checked. In a long guide, a handful in the whole document is about right.
The QUILL Cast user guide will be the first guide to carry them.

## In release notes

Release notes are where QUILLBert is most at home, because a release is a pile
of new things to find. Good spots:

- QUILLBert pointing at one new thing worth trying first.
- QUILLBee on what upgrading means in practice ("Install over the old version
  and you keep everything").
- At most one exchange, for the change most likely to surprise people.

Keep them out of the list of fixes. A bug fix is not an occasion.

## Later: inside the apps

This is future direction, not a plan of record and not a promise. If and when
the characters move into QUILL, QUILL Lite, Quill Radio, QUILL Cast and the
rest, the natural places are:

- **First run**, where QUILLBert says hello and gets out of the way.
- **What's New**, where QUILLBert points at one thing and QUILLBee says how to
  use it.
- **F1 help**, where a QUILLBee tip could follow the authored help text. It must
  never replace it, and the F1 audit's rules still apply.
- **Empty states**, such as an empty favorites list, where a line from
  QUILLBert is better than silence.

In the apps, the screen-reader rules come first. Nothing the screen reader
already says gets said again (GATE-13), a character never speaks on focus, and
a verbosity setting is not an excuse for a chatty one.

## Examples

### Good

1. **QUILLBee's shortcut:** "Forgotten where something lives? Press Ctrl+Shift+P
   and type a word, like "sort" or "print". You don't need to know which menu
   it's in." *One real key, checked against the guide, and it saves time today.*
2. **QUILLBert noticed:** "There's a switch in Tools > Customize Features that's
   easy to miss. Turn on Go To Anything... QUILLBert turned it on anyway. Of
   course he did." *A real, off-by-default feature, and the joke is on him.*
3. **QUILLBee's shortcut:** "If you already live on the H key, you know this
   one. If not: press H to hop from one section to the next." *It respects the
   expert and helps the newcomer in the same breath.*
4. **QUILLBert's Corner:** "QUILLBert wandered in while we were rewriting this
   page and hasn't left since." *A welcome with a wink, and short.*
5. **QUILLBert and QUILLBee**, on the Wake-Up Timer: he tries it at three in the
   morning; QUILLBee gives the key and the two limits that matter. *Discovery,
   then the facts, including what it can't do.*
6. **QUILLBert found something:** "QUILL Cast doesn't have a page of its own on
   this site yet, so QUILLBert went digging" and found the lesson. *He points
   at something real that people would otherwise miss.*
7. **A note from QUILLBee:** "Upgrading? Install over the old version and you
   keep everything." *Answers the question people actually have on release
   day.*
8. **QUILLBee's tip:** "Lost in Quill Radio? F1 tells you what the window
   you're in is for, and Escape closes it." *Reassuring, two keys, no fuss.*

### Not good

1. "QUILLBee's tip: Dive into QUILL and unlock endless possibilities!"
   *Banned phrases, and it says nothing at all.*
2. "QUILLBert: Oopsie! Lost again, little buddy? Don't worry!" *Talks down to
   the reader and makes them the joke.*
3. "QUILLBee: Accessibility is super fun, and screen readers are adorable!"
   *Never make accessibility cute.*
4. A QUILLBee tip between step 3 and step 4 of a setup guide. *It breaks the
   steps exactly when someone is following them.*
5. "Stuck? Just ask QUILLBee!" *There is no Ask QUILLBee. Don't promise a
   feature that doesn't exist.*
6. "QUILLBert's tip: press Ctrl+Q to see him dance." *An invented key with
   invented behaviour. Someone will press it.*
7. A "QUILLBert's Corner" at the end of every section of a page. *By the third
   one, people skip them, including the one that mattered.*
8. QUILLBert walking through five settings in order, while QUILLBee cracks
   jokes. *They've swapped jobs. Explaining is QUILLBee's.*
9. A callout that's only a coloured box or a bee picture, with the name in
   `aria-label` and nothing visible. *Meaning by colour and image, and invisible
   to anyone reading the text.*
10. "Whether you're a beginner or an expert, QUILLBee is here for your journey."
    *A slogan, and two banned phrases in one sentence.*
