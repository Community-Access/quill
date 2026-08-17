"""Filler-word removal for transcripts, two-tiered and language-honest.

Dictation transcribes the "um"s and "uh"s a speaker never meant as text. The
obvious fix — strip a list of fillers — has a trap the Handy project
(D:\\code\\handy, ``src-tauri/src/audio_toolkit/text.rs``, MIT) documented from
production and this port keeps: **many fillers are real words in another
language.** "um" is Portuguese for "a/an" and German for "at/around"; "ha" is
Spanish "has"; "mm" is millimetres everywhere. Removing those unconditionally
deletes a user's actual words.

So removal is two tiers:

- **Universal tier** — tokens that are hesitation noises in every language this
  code will meet ("uh", "uhm", "hmm", ...). Removed whenever the feature is on,
  no language evidence needed. Deliberately conservative: anything that is a
  real word *somewhere* stays out of this tier.
- **Language-gated tier** — fillers that are safe only when the transcript's
  language is *known* (explicitly selected by the user, or reported by an
  engine that detects it, e.g. Parakeet 3). Unknown language = this tier does
  nothing. It fails closed, exactly like Handy's confidence-gated detector.

A **custom list replaces both tiers** — an explicit user override needs no
language evidence, and an explicitly *empty* custom list disables built-in
removal while leaving the master toggle on (the power-user escape hatch). The
master toggle (default **off**, per the PRD's conservative-normalization rule
§17) precedes everything.

Removal is token-wise and punctuation-preserving: "Um, hello" -> "hello", not
", hello". Pure, stdlib-only, wx-free; unit-tested directly. Applied by
:func:`quill.core.speech.dictation.refine.refine_transcript`.
"""

from __future__ import annotations

import re

#: Hesitation noises, not words, in any supported language. Includes the
#: Cyrillic pair so Russian/Ukrainian transcripts are covered by the universal
#: tier too.
UNIVERSAL_FILLER_WORDS: frozenset[str] = frozenset({
    "uh",
    "uhm",
    "umm",
    "uhh",
    "uhhh",
    "ehh",
    "ehm",
    "ahm",
    "hmm",
    "hm",
    "mmm",
    "хм",
    "ммм",
})

#: Fillers that collide with real words elsewhere, keyed by primary language
#: code. Only consulted with language evidence. "um" stays out of the English
#: list's neighbours: Portuguese ("a/an") and German ("at/around") transcripts
#: keep it as text.
_GATED_FILLERS: dict[str, frozenset[str]] = {
    "en": frozenset({"um", "er", "erm", "mm", "mhm", "uh-huh", "mm-hmm"}),
    "es": frozenset({"eh", "este", "em"}),
    "fr": frozenset({"euh", "ben", "hein"}),
    "de": frozenset({"äh", "ähm", "öh", "öhm", "mh"}),
    "pt": frozenset({"é", "eh", "ãh", "hã"}),
    "it": frozenset({"ehm", "beh", "mah"}),
    "nl": frozenset({"eh", "ehm", "uhm"}),
    "ru": frozenset({"э", "эм", "ну", "мм"}),
    "uk": frozenset({"е", "ем", "ну"}),
    "pl": frozenset({"yyy", "eee", "no"}),
    "sv": frozenset({"eh", "öh", "hmm"}),
    "ja": frozenset({"えーと", "あの", "その", "えー"}),
    "zh": frozenset({"那个", "这个", "嗯"}),
}

_TOKEN = re.compile(r"(\s+)")
_EDGE_PUNCT = ".,;:!?…"


def gated_filler_words_for_language(language: str) -> frozenset[str]:
    """The language-gated tier for *language* ("pt-BR" and "pt" both -> pt)."""
    primary = language.strip().split("-")[0].split("_")[0].lower()
    return _GATED_FILLERS.get(primary, frozenset())


def _is_filler(token: str, fillers: frozenset[str]) -> bool:
    core = token.strip(_EDGE_PUNCT + "\"'").lower()
    return core in fillers


def remove_filler_words(
    text: str,
    *,
    language: str = "",
    custom_filler_words: list[str] | tuple[str, ...] | None = None,
    enabled: bool = False,
) -> str:
    """Remove configured fillers from *text* (pure).

    ``language`` is the transcript's language when known ("" = unknown; the
    gated tier then stays inert). ``custom_filler_words`` replaces both built-in
    tiers when not None — an empty list therefore disables built-in removal.
    ``enabled`` is the master toggle and precedes everything.

    A removed token takes its following space with it and leaves neighbouring
    punctuation attached to real words, so "Well, um, yes" -> "Well, yes".
    """
    if not enabled or not text:
        return text
    if custom_filler_words is not None:
        fillers = frozenset(w.strip().lower() for w in custom_filler_words if w.strip())
    else:
        fillers = UNIVERSAL_FILLER_WORDS | (
            gated_filler_words_for_language(language) if language else frozenset()
        )
    if not fillers:
        return text

    parts = _TOKEN.split(text)
    out: list[str] = []
    index = 0
    while index < len(parts):
        part = parts[index]
        if part and not part.isspace() and _is_filler(part, fillers):
            # A filler that carried sentence punctuation ("Um,") hands it to the
            # flow by simply vanishing with its trailing whitespace; leading
            # whitespace already emitted stays, so words join with one space.
            if index + 1 < len(parts) and parts[index + 1].isspace():
                index += 2
                continue
            index += 1
            continue
        out.append(part)
        index += 1
    cleaned = "".join(out)
    # Collapse any doubled spaces a removal left behind, and re-trim edges.
    cleaned = re.sub(r"[ \t]{2,}", " ", cleaned).strip()
    # A removal directly after an opening quote/bracket can leave " ,": tidy the
    # commonest artefacts without touching legitimate punctuation.
    cleaned = re.sub(r"\s+([.,;:!?])", r"\1", cleaned)
    return cleaned
