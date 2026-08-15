"""Naming a section after what it is *about*, not after the words it opens with.

The gap tier 5 was always meant to close, and the reason inferred chapters were
never quite worth having. Tier 3 titles a section with its literal opening words;
tier 4 titles them ``Section 1``, ``Section 2``. Neither says what the part is
about, which is the entire point of a chapter list.

Two rules decide how much text a section is named from, and getting them the
wrong way round is the classic mistake:

* **Where the text is already in hand -- a published transcript, or one Deep just
  produced -- the section's whole text is used.** Reading less would save nothing
  and lose accuracy.
* **Only where naming would otherwise require transcribing audio nobody has asked
  to pay for** is the section sampled. A twelve-section hour then costs twelve
  minutes of transcription rather than sixty.

And the sample is never *only* the opening. A section's first minute is very
often the tail of the previous topic, a transition, an ad read, or
throat-clearing, with the real subject arriving later -- so it is the opening
plus a short probe from the middle. Naming a chapter after the thing the host was
just finishing is exactly the confident-but-wrong output rule A-10 exists to
prevent.

**One batched call, never one per chapter.** Twelve sections is one request whose
answer is twelve titles. Per-chapter calls would be twelve times the cost, twelve
times the latency, and twelve chances for one to fail and leave a list with a
hole in it.

wx-free, strict-typed. The model is a callable the caller supplies -- this module
never chooses a provider, never touches the network, and is fully testable
without either.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence

from quill.core.podcasts.chapters import PodcastChapter
from quill.core.podcasts.inference_budget import InferenceBudget

#: The whole prompt. Deliberately strict about *shape* -- one title per line, in
#: order -- because a chatty answer is unparseable, and deliberately strict about
#: *honesty*: a section it cannot summarise must be left alone rather than given
#: a plausible invention.
PROMPT = (
    "Below are numbered sections of one podcast episode, each with the words "
    "spoken in it.\n\n"
    "Write a short title for each section: at most eight words, describing what "
    "the section is ABOUT. No quotation marks, no numbering, no trailing full "
    "stop, no commentary.\n\n"
    "Return exactly one title per line, in the same order as the sections. If a "
    "section is too unclear to title, write a single hyphen for that line rather "
    "than guessing.\n\n"
)

#: A model reply of this is "I could not tell", and the existing title stays.
DECLINED = "-"

#: The most words a chapter title may carry. Longer is a sentence, and a
#: sentence in a list somebody arrows through is a wall.
MAX_TITLE_WORDS = 8


def clean_title(raw: str) -> str:
    """One model line as a usable title, or "" when it is not one.

    Strips the shapes models add unbidden -- quotes, numbering, a trailing
    period, a "Title:" prefix -- and clamps the length. Returns "" for a decline
    so the caller keeps whatever title it already had.
    """
    text = (raw or "").strip()
    if not text or text == DECLINED:
        return ""
    for prefix in ("title:", "chapter:", "section:"):
        if text.lower().startswith(prefix):
            text = text[len(prefix) :].strip()
    text = text.strip("\"'“”‘’ \t")
    while text[:1].isdigit() and (". " in text[:5] or ") " in text[:5]):
        text = text.split(" ", 1)[1].strip() if " " in text else ""
    text = text.rstrip(" .")
    words = text.split()
    if not words:
        return ""
    return " ".join(words[:MAX_TITLE_WORDS])


def sample_text(
    text: str,
    *,
    budget: InferenceBudget,
    whole: bool,
) -> str:
    """The words a section is named from.

    *whole* is the caller saying "the text is already here" -- a published
    transcript, or one Deep produced -- in which case all of it is used. Only
    when the alternative is paying to transcribe more audio does this sample:
    the opening, plus a probe from the middle, so a section whose real subject
    arrives after an ad read is still named correctly.
    """
    words = text.split()
    if whole or not words:
        return text.strip()
    # Roughly 150 words a minute of speech: the sample sizes are expressed in
    # seconds because that is what the budget is about, and this is the only
    # place that converts.
    opening = max(1, int(budget.sample_seconds * 150 / 60))
    probe = max(0, int(budget.middle_probe_seconds * 150 / 60))
    if len(words) <= opening + probe:
        return text.strip()
    middle = len(words) // 2
    return " ".join([*words[:opening], "...", *words[middle : middle + probe]]).strip()


def build_prompt(sections: Sequence[str]) -> str:
    """The one batched request: every section, numbered, in order."""
    body = "\n\n".join(
        f"Section {index}:\n{text.strip()}" for index, text in enumerate(sections, start=1)
    )
    return PROMPT + body


def parse_titles(reply: str, expected: int) -> list[str]:
    """The model's reply as *expected* titles, padding with "" for anything short.

    Padding rather than failing: eleven good titles and one gap is a better list
    than no list, and a gap keeps the title the chapter already had.
    """
    lines = [line for line in (reply or "").splitlines() if line.strip()]
    titles = [clean_title(line) for line in lines[:expected]]
    titles.extend([""] * max(0, expected - len(titles)))
    return titles


def name_sections(
    chapters: Sequence[PodcastChapter],
    texts: Sequence[str],
    ask: Callable[[str], str],
    *,
    budget: InferenceBudget,
    whole_text_available: bool = True,
) -> list[PodcastChapter]:
    """Retitle *chapters* from *texts*, in one call. Failures change nothing.

    ``ask`` is the caller's model call -- the frame's assistant, absent in Safe
    Mode. Any failure leaves every chapter exactly as it was, because a chapter
    list that lost its titles to a network error is worse than one whose titles
    were never improved.
    """
    rows = list(chapters)
    if not rows or len(texts) != len(rows):
        return rows
    samples = [sample_text(text, budget=budget, whole=whole_text_available) for text in texts]
    if not any(sample.strip() for sample in samples):
        return rows
    try:
        reply = ask(build_prompt(samples))
    except Exception:  # noqa: BLE001 - an unnamed chapter list is still a chapter list
        return rows
    titles = parse_titles(reply, len(rows))
    named: list[PodcastChapter] = []
    for chapter, title in zip(rows, titles, strict=True):
        if not title:
            named.append(chapter)
            continue
        named.append(
            PodcastChapter(
                start_ms=chapter.start_ms,
                title=title,
                image_url=chapter.image_url,
                link_url=chapter.link_url,
                end_ms=chapter.end_ms,
                source=chapter.source,
                confidence=chapter.confidence,
                # The reason gains the naming step, because "how was this
                # titled" and "how was this boundary found" are two different
                # questions and the report answers both.
                reason=(
                    f"{chapter.reason}; titled by a model from the words spoken"
                    if chapter.reason
                    else "titled by a model from the words spoken"
                ),
            )
        )
    return named
