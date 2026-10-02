"""AI word tools: a dictionary, a thesaurus and a usage guide that read the sentence.

The offline thesaurus knows every sense of "bank"; it cannot know which one this
sentence means. These tools send **the word and the sentence it sits in** --
never the rest of the document -- and ask for an answer shaped for a listener:
a short explanation, and, where there is something to put in the document, a
list of choices that each say why.

Scope, by decision (Jeff, 2026-10-01): these run **only** on the listener's
own OpenAI key or their ChatGPT subscription, never on QUILL's free hosted AI.
The free service is metered per person and these are cheap, frequent calls --
the kind that would spend somebody's day of free help on synonyms. The UI
checks the route before it asks (``AiService.direct``); this module only builds
prompts and reads answers, and knows nothing about routes.

wx-free, strict-typed, pure. One feature id, :data:`FEATURE`, carries a single
system instruction (``own_key.INSTRUCTIONS``); each tool is a user prompt.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass

#: The feature id every word tool sends under (``own_key.INSTRUCTIONS``).
FEATURE = "word_tools"

#: The system instruction. JSON out, because the answer is read aloud and
#: its choices are put into a document: free prose would have to be parsed by
#: guesswork, and a choice with a preamble glued to it is a broken edit.
INSTRUCTIONS = (
    "You are a careful English dictionary, thesaurus and usage guide inside a "
    "word processor used by blind and low-vision writers who listen to every "
    "answer. Answer the task about the given word as it is used in the given "
    "sentence. Reply with a single JSON object and nothing else, of the form "
    '{"answer": "...", "choices": [{"text": "...", "note": "..."}]}. '
    '"answer" is plain prose for listening: no markdown, no bullet characters, '
    "no headings, at most about 80 words unless the task asks for more. "
    '"choices" are exact replacement or insertion texts, already in the right '
    "grammatical form and capitalisation for the sentence, each with a note of "
    "a few words; use an empty list when the task has nothing to put in the "
    "document. Never invent a word or a meaning; say so when you are unsure."
)

#: Most choices a list shows. Enough to choose from by ear.
MAX_CHOICES = 12


@dataclass(frozen=True, slots=True)
class WordTool:
    """One thing to ask about a word."""

    id: str
    #: Menu label, with its access key.
    label: str
    #: The task, written into the prompt.
    task: str
    #: Whether the answer offers text to put in the document.
    offers_choices: bool
    #: What a chosen choice does: replace the word, or insert at the caret.
    action: str = "replace"


REPLACE = "replace"
INSERT = "insert"

TOOLS: tuple[WordTool, ...] = (
    WordTool(
        "define",
        "&Define in Context",
        "Define the word as it is used in this sentence, then name its part of "
        "speech. If it has another common meaning a reader might confuse it with, "
        "say so in one sentence.",
        offers_choices=False,
    ),
    WordTool(
        "synonyms",
        "&Synonyms That Fit",
        "Give replacements that keep this sentence's meaning and register, best "
        "first, each already inflected to fit the sentence. In the answer, say in "
        "one sentence which sense of the word the sentence uses.",
        offers_choices=True,
    ),
    WordTool(
        "simpler",
        "S&impler Word",
        "Give plainer, more widely known replacements that keep the meaning, best "
        "first. In the answer, say in one sentence what is lost, if anything.",
        offers_choices=True,
    ),
    WordTool(
        "formal",
        "More &Formal Word",
        "Give more formal or precise replacements suited to professional writing, best first.",
        offers_choices=True,
    ),
    WordTool(
        "vivid",
        "More &Vivid Word",
        "Give livelier, more vivid or more specific replacements that still fit "
        "this sentence, best first.",
        offers_choices=True,
    ),
    WordTool(
        "opposites",
        "&Opposites",
        "Give antonyms that would fit this sentence in the word's place, best first.",
        offers_choices=True,
    ),
    WordTool(
        "right_word",
        "Is This the &Right Word?",
        "Say whether this is the right word here. Check for commonly confused "
        "words (affect and effect, complement and compliment, its and it's and "
        "the like), wrong register and wrong meaning. If it is right, say so "
        "plainly and give no choices. If not, explain the difference briefly "
        "and give the right word as the first choice.",
        offers_choices=True,
    ),
    WordTool(
        "examples",
        "Use It in a S&entence",
        "Give three short example sentences using the word in the same sense as "
        "this sentence, in the answer, each on its own line. No choices.",
        offers_choices=False,
    ),
    WordTool(
        "origin",
        "Where It Comes Fro&m",
        "Give the word's origin and how its meaning developed, in plain prose. No choices.",
        offers_choices=False,
    ),
    WordTool(
        "pronounce",
        "How to Say I&t",
        "Say how to pronounce the word: syllables with the stressed one in "
        "capitals, a plain respelling, and the IPA. Mention any common "
        "mispronunciation. No choices.",
        offers_choices=False,
    ),
    WordTool(
        "rhymes",
        "R&hymes",
        "Give words that rhyme with this word, perfect rhymes first, then near "
        "rhymes, each with its syllable count as the note.",
        offers_choices=True,
    ),
)

#: The reverse dictionary: describe a meaning, get the word. Not on a word, so
#: not in :data:`TOOLS`; its prompt is :func:`find_word_prompt`.
FIND_WORD = WordTool(
    "find_word",
    "Find the &Word For...",
    "",
    offers_choices=True,
    action=INSERT,
)

TOOLS_BY_ID: dict[str, WordTool] = {tool.id: tool for tool in (*TOOLS, FIND_WORD)}

#: Everything at once, for the Word Explorer.
EXPLORE = WordTool(
    "explore",
    "Word &Explorer...",
    "Explore the word as used in this sentence. In the answer, in this order "
    "and as short paragraphs: its meaning here and its part of speech; how to "
    "say it (syllables with the stress in capitals); one example sentence; "
    "where it comes from, in one sentence; and any word it is commonly "
    "confused with. The choices are the best replacements that fit the "
    "sentence, each already in the right form.",
    offers_choices=True,
)
TOOLS_BY_ID[EXPLORE.id] = EXPLORE


def word_prompt(tool: WordTool, word: str, sentence: str) -> str:
    """The user message for *tool* about *word* in *sentence*."""
    context = sentence.strip() or word
    return f"Task: {tool.task}\nWord: {word}\nSentence: {context}\nAt most {MAX_CHOICES} choices."


def find_word_prompt(description: str, sentence: str = "") -> str:
    """The reverse dictionary's user message: a meaning in, words out."""
    where = f"\nIt will go into this sentence: {sentence.strip()}" if sentence.strip() else ""
    return (
        "Task: Find the word or short phrase the writer is looking for, from "
        "their description. Give the best candidates as choices, best first, "
        "each with a note of a few words saying how it differs from the others. "
        "In the answer, say in one sentence which you think fits best and why."
        f"\nDescription: {description.strip()}{where}\n"
        f"At most {MAX_CHOICES} choices."
    )


# -- reading the answer -------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class WordChoice:
    text: str
    note: str = ""

    def spoken(self) -> str:
        return f"{self.text} -- {self.note}" if self.note else self.text


@dataclass(frozen=True, slots=True)
class WordAnswer:
    answer: str
    choices: tuple[WordChoice, ...]


_FENCE = re.compile(r"^```(?:json)?\s*|\s*```$", re.IGNORECASE)
_MARKDOWN = re.compile(r"(\*\*|__|^#+\s*|^\s*[-*•]\s+)", re.MULTILINE)


def _plain(text: str) -> str:
    return _MARKDOWN.sub("", text).strip()


def parse_answer(raw: str) -> WordAnswer:
    """The model's reply as an answer and choices. Never raises.

    A reply that is not the JSON asked for is still an answer -- the prose is
    kept, with nothing offered for the document, because a choice guessed out
    of free text is exactly the broken edit the JSON exists to prevent.
    """
    text = _FENCE.sub("", (raw or "").strip()).strip()
    data: object = None
    try:
        data = json.loads(text)
    except ValueError:
        start, end = text.find("{"), text.rfind("}")
        if 0 <= start < end:
            try:
                data = json.loads(text[start : end + 1])
            except ValueError:
                data = None
    if not isinstance(data, dict):
        return WordAnswer(_plain(text), ())
    answer = _plain(str(data.get("answer", "") or ""))
    choices: list[WordChoice] = []
    seen: set[str] = set()
    raw_choices = data.get("choices")
    for item in raw_choices if isinstance(raw_choices, list) else []:
        if isinstance(item, dict):
            choice_text = str(item.get("text", "") or "").strip()
            note = _plain(str(item.get("note", "") or ""))
        else:
            choice_text, note = str(item or "").strip(), ""
        if not choice_text or choice_text.lower() in seen or "\n" in choice_text:
            continue
        seen.add(choice_text.lower())
        choices.append(WordChoice(choice_text, note))
        if len(choices) >= MAX_CHOICES:
            break
    return WordAnswer(answer, tuple(choices))


__all__ = [
    "EXPLORE",
    "FEATURE",
    "FIND_WORD",
    "INSERT",
    "INSTRUCTIONS",
    "MAX_CHOICES",
    "REPLACE",
    "TOOLS",
    "TOOLS_BY_ID",
    "WordAnswer",
    "WordChoice",
    "WordTool",
    "find_word_prompt",
    "parse_answer",
    "word_prompt",
]
