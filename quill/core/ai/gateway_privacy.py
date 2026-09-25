"""The agreement somebody has to accept before any of their writing is sent.

One place for the words, and one number for the version. wx-free, so QUILL and
QUILL Lite show the same text rather than two texts that start the same and
drift.

**Why this is separate from the feature switch.** The switchable area answers
"does this feature exist in my copy of QUILL Lite"; the agreement answers "have I
agreed to what it does". They are genuinely different questions and conflating
them gets one of them wrong: an area switched on by a profile, by a settings
import or by somebody else using the machine would otherwise be consent nobody
gave, and an area switched off for tidiness would otherwise throw away an
agreement that was given.

So both must be true. Turning the feature on prompts for the agreement, and
declining leaves the feature present and unusable rather than silently
switching it back off -- because a switch that flips itself back is a switch
somebody will fight.

**Why it is versioned.** :data:`AGREEMENT_VERSION` is stored alongside the
acceptance, so a *material* change to what is sent or kept can ask again.
Bumping it re-prompts everybody, which is the point and also why it must not be
bumped for a typo: consent people are asked for twice a year is consent they
stop reading.
"""

from __future__ import annotations

__all__ = [
    "AGREEMENT_VERSION",
    "AGREEMENT_TITLE",
    "SUMMARY",
    "agreement_text",
    "is_accepted",
]

#: Bump only when what is sent, or what is kept, materially changes.
AGREEMENT_VERSION = 1

AGREEMENT_TITLE = "QUILL AI: what is sent, and what is kept"

#: The one-paragraph version, for a checkbox label or a status line. Says the
#: two things somebody must know before deciding, and nothing else.
SUMMARY = (
    "AI help sends the passage you ask about to QUILL's servers and on to "
    "OpenAI, which writes the answer. QUILL records how many requests you make "
    "and how big they were, never what you wrote or what came back."
)


def agreement_text() -> str:
    """The full agreement, as it is read aloud.

    Written to be *heard*: short paragraphs with their own headings, the
    important word early in each sentence, and no clause that needs a second
    pass. A wall of legal prose is a wall a screen-reader user has to listen to
    end-to-end before finding the one fact they wanted, so the facts come first
    and the reassurances after.
    """
    return "\n\n".join([
        "What happens when you use AI help",
        "The passage you have selected -- or, for a question about a document, "
        "up to three excerpts QUILL Lite picks on this computer -- is sent over "
        "the internet to QUILL's servers, and from there to OpenAI, which "
        "writes the answer. The answer comes back to you and is shown in a "
        "window. Nothing is put into your document until you choose to put it "
        "there.",
        "What QUILL keeps",
        "How many requests you made, how big they were, which of the five "
        "features you used, and what they cost. That is all, and it is what "
        "lets QUILL keep the service free and notice if something goes wrong.",
        "What QUILL does not keep",
        "What you wrote. What came back. Your name, your email address, your "
        "documents, or anything that identifies you -- connecting a computer "
        "creates an account with no name on it at all.",
        "What OpenAI does with it",
        "QUILL sends your passage to OpenAI to get the answer. What OpenAI "
        "keeps is governed by its own terms, not QUILL's. If that matters for "
        "what you are writing, do not use this feature for it.",
        "What this costs you",
        "Nothing. There is a monthly allowance, and Tools, AI, Usage says how "
        "much of it is left. When it runs out it starts again by itself.",
        "If you would rather not",
        "Say no. QUILL Lite works exactly as it does now -- every other feature "
        "is untouched, and nothing is sent anywhere. You can change your mind "
        "later in Tools, AI, or in Preferences, or in Customize Features. If "
        "you have your own AI provider account, that route never involves "
        "QUILL's servers at all.",
    ])


def is_accepted(accepted_version: int) -> bool:
    """Whether *accepted_version* is current enough to use the feature.

    A stored version behind :data:`AGREEMENT_VERSION` counts as not accepted, so
    a material change asks again rather than assuming an old yes still covers a
    new thing.
    """
    return accepted_version >= AGREEMENT_VERSION
