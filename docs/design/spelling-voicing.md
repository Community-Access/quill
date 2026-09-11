# Spelling voicing: how a misspelling is reported, and why

Applies to **QUILL and QuillLite together**. Every rule here lives in shared
code -- `quill/core/spelling/voicing.py`, `quill/core/spellcheck.py` -- so
neither editor can drift ahead of the other, and a listener who tunes this in
one finds the other already tuned.

## The problem this solves

A misspelling is the one thing in an editor that speech alone cannot convey.
"receive" and "recieve" are the same sound. A sighted user gets a red squiggle
under the wrong letters and knows instantly; a listener told "not in dictionary,
recieve" has been handed a word they cannot tell from the correct one. That is a
report, not an answer.

**The letters are the answer.** Everything below is about delivering them
without becoming a nuisance -- because the same feature that helps once an hour
is intolerable forty times a minute, and the difference between those two is
entirely a matter of timing, phrasing and restraint.

Three surfaces report a misspelling, and each needs a different voice:

| Surface | What it must do | What it must not do |
|---|---|---|
| While you type | Tell you something is wrong | Interrupt the sentence you are writing |
| When you land on one | Tell you *which letters* are wrong | Repeat what your screen reader just said |
| In the review or suggestions list | Let you tell two spellings apart | Make you sit through eleven letters you did not need |

## What was actually broken

Three defects, all found by reading the code against these three surfaces.

**The as-you-type alert had never fired.** Both editors called
`misspelling_at(text, caret)`, which by construction matches only a word
*beginning exactly at the caret* -- it is the bounded helper written for a
different question. While typing left to right the caret is always at or past
the *end* of the word just finished, so the condition was never true. The earcon,
the status line and the whole feature were unreachable except by arrowing back
onto the first letter of a bad word. Fixed by
`misspelling_behind()`, which asks the question the surface actually has: *what
word did you just finish, and is it a word?*

**Landing on a misspelling never spelled it.** Next and Previous Misspelling
selected the word and set a status line. The screen reader read the selection --
so a listener heard "recieve", which is the sound of the word they meant, and
learned nothing. Fixed by spelling it out after a pause.

**Ordinals were misspellings, and one shape was worse than that.** `"the 13th
of May"` reported **`"th"`** as a misspelling, at an offset inside a number, for
a word nobody typed: the pattern started at the first letter it found and the
digits before it were invisible to it. `"1st"` and `"23rd"` escaped only because
"st" and "rd" happen to be in the wordlist. One lookbehind fixed that and the
whole family it belongs to -- 3D, 1080p, 500ml, 12pt, v2beta -- every one of
which was a spoken interruption and none of which was ever a spelling mistake.

## The rules

### While you type: a sound, and not a voice

Speech here interrupts the very sentence it is commenting on, and somebody
composing a paragraph is the person least able to afford it. So the alert is an
earcon, the status bar carries the words, and F7 still finds everything.

**The alert fires on a word you have finished**, not on one you are in the
middle of. "Finished" means there is a terminator -- a space, a comma, a
newline -- between the word and the caret. Without that rule a checker judges
"recie" while you are still typing "receive" and cries wolf on the way to every
long word.

**The earcon is "the slip"**: a note that starts in tune and slides flat, 58 ms,
the quietest cue in the pack. It is the sound of the thing it reports -- a word
that was almost right. It has to be unique because it fires more often than any
other earcon, and an alert you cannot tell from four others is one you learn to
ignore; every other negative cue in the pack is a discrete two-note descent or a
buzz, and nothing else glides. A 3 ms noise tick opens it so it cuts through a
synthesiser on shape rather than on volume, which is the trade any alert that
fires this often has to make.

It can be **silenced outright** (`spelling_alert_sound`), it can be **spoken as
well** for somebody who wants that (`spelling_alert_speech`, off by default), and
its **repeat interval is tunable** (`spelling_alert_repeat_ms`) so one stubborn
proper noun does not become a drum. Zero means alert every time, because a
throttle you cannot switch off is one that eventually hides something.

### When you land on one: the word, a pause, then the letters

Two utterances, never one. A single utterance cannot be interrupted, so somebody
who recognised the word from its first syllable would have to sit through eleven
more letters. A pause and a separate utterance means a fast user never hears the
spelling at all -- they have already pressed the next key and the pending
spell-aloud is cancelled -- while somebody who waits gets it in full.

**The pause is different per surface, and both are tunable.** In the review
dialog you are stopped and deciding, so the default is 800 ms. Moving through a
document with Next Misspelling you may be travelling, so its default is 600 ms.
A spell-aloud you always outrun is one more thing to cancel; one you always wait
for is a metronome.

### In a list of corrections: the same treatment

Choosing between "receive" and "recieve" by ear is exactly as impossible in a
list of suggestions as it was in the document, so arrowing onto a suggestion
spells it after a pause, and arrowing on cancels it. Spelling the *first*
suggestion automatically on arrival is available and **off by default**: it
doubles the arrival announcement, which is welcome when you are learning a word
and noise when you are checking one.

### Letters can be said three ways

Plain letters are fastest and are what most people want. The **phonetic
alphabet** is unambiguous where B, D, E, P, T and V are one sound with a rumour
attached -- a fast voice, a poor speaker, a noisy room. **Both** is for learning
a word rather than checking one.

Letters are spoken in upper case whatever the word does, because several voices
read a lone lower-case letter as a word ("a", "i") while every voice reads an
upper-case one as a letter. That loses the fact that a letter *was* capitalised,
so `spell_aloud_capitals` puts it back explicitly: "cap M, C, cap D" is how you
hear that a surname is MacDonald and not Macdonald. Hyphens, apostrophes and
underscores are named rather than paused over, because a pause is not a hyphen.

## The settings

Twelve names, identical in both editors. QUILL renders them from
`settings_specs.py`; QuillLite has its own Spelling Announcements window.

| Setting | Default | What it decides |
|---|---|---|
| `spelling_alert_sound` | on | Play the earcon when you finish a misspelled word |
| `spelling_alert_speech` | off | Also say the word |
| `spelling_alert_repeat_ms` | 750 | Shortest gap between two alerts for the same word; 0 means always |
| `spell_aloud_enabled` | on | Spell misspelled words out at all |
| `spell_aloud_delay_ms` | 800 | Pause before spelling, in the review |
| `spell_aloud_on_navigation` | on | Spell the word you land on with Next/Previous Misspelling |
| `spell_aloud_navigation_delay_ms` | 600 | The shorter pause for that |
| `spell_aloud_suggestions` | on | Spell each suggestion as you arrow onto it |
| `spell_aloud_suggestion_delay_ms` | 600 | Pause before that |
| `spell_aloud_first_suggestion` | off | Also spell the top suggestion on arrival |
| `spell_aloud_style` | letters | Letters, phonetic alphabet, or both |
| `spell_aloud_capitals` | on | Say "cap" before an upper-case letter |

QUILL keeps `spell_review_spell_word` and `spell_review_spell_word_pause_ms` as
the review dialog's own switch and pause, and they win over the shared pair
there: somebody who switched spelling off for the F7 dialog specifically meant
the F7 dialog.

## Where the code is

- `quill/core/spelling/voicing.py` -- the policies, the letter formatter, and
  the one-pending-utterance scheduler. wx-free; the timer arrives as a factory
  so every rule is testable without a display.
- `quill/core/spellcheck.py` -- `misspelling_behind()` (the as-you-type
  question) and the ordinal guard in `_WORD_PATTERN`.
- `quill/core/spelling/announcements.py` -- the review dialog's verbosity, now
  spelling through the shared voice.
- `scripts/gen_ink_sounds.py` -- "the slip", under `spelling.wav`.

## Deliberately not done

**One-utterance phrasing.** "Misspelled word receive, r e c e i v e" as a single
breath is how some tools do it. Two utterances are better: you can interrupt
between them, and the pause is the whole mechanism by which a fast user pays
nothing for a feature a careful user needs.

**Line numbers in the misspelling list.** Easy to add, and a line number is not
something a listener navigates by. Worth asking a real user before building.

**A "remove word from the dictionary" command.** Teaching a word with one
keystroke is permanent, and the only remedy today is hand-editing JSON. This is
a real gap and the right shape for it is a *list* of the words you have taught,
not a remove-at-cursor key -- because removing a word only helps if you can find
it again. Not built here; worth its own change.
