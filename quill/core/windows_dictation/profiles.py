"""Named dictation profiles, and what each one does with structure (D-23).

A profile is a frozen overlay on the person's Dictation Settings: the pause,
the fillers, the punctuation, how structure is written, and which word list it
uses. **Standard** is no overlay at all -- dictation exactly as it was before
profiles existed, headings written as Markdown marks -- and it is the default,
so nobody's dictation changes until they choose a profile.

* **Email** -- fillers out, punctuation in, formatted structure.
* **Document** -- formatted structure: in a QUILL document that can hold
  formatting, "heading two" and "bold that" use the editor's own commands;
  anywhere else nothing is typed for them, and dictation says why.
* **Markdown** -- headings, bold and italic as Markdown marks, everywhere.
* **Chat** -- plain text: heading marks write nothing, bold and italic are
  refused with a sentence. Fillers out.
* **Coding** -- Markdown marks, fillers out, no automatic punctuation (you say
  every mark), a longer pause.
* **Verbatim** -- every word as said: fillers kept, plain structure.

**Switching is manual only**: Dictation Settings, QUILL Transcribe's Dictation
Profile window and tray, or by voice ("QUILL email mode"). There is no automatic
switch per program (dict.md section 6). **Lock profile** stops voice switching.
The profile in use shows in the status cell, the tray name and Dictation Status.

**For other code.** :func:`active_profile_name` answers which profile is in use
for any settings object (both editors', QUILL Transcribe's, Inkwell's), and
:attr:`NamedProfile.word_list` is the name a per-profile word list is filed
under (D-20/D-21 read it). Both never raise.

Pure and wx-free.
"""

from __future__ import annotations

from dataclasses import dataclass

__all__ = [
    "DEFAULT_PROFILE",
    "FORMAT_REFUSAL",
    "HEADING_REFUSAL",
    "PLAIN_REFUSAL",
    "PROFILES",
    "STRUCTURES",
    "NamedProfile",
    "active_profile",
    "active_profile_name",
    "coerce_profile",
    "profile_by_id",
    "profile_labels",
]

#: How structure is written: ``markdown`` marks, ``formatted`` through the
#: editor's own commands, or ``plain`` text.
STRUCTURES = ("markdown", "formatted", "plain")

DEFAULT_PROFILE = "standard"

#: Said when a formatted profile meets a place with no formatting.
HEADING_REFUSAL = "Headings work in QUILL documents or the Markdown profile."
FORMAT_REFUSAL = "Bold and italic work in QUILL documents or the Markdown profile."
PLAIN_REFUSAL = "This profile writes plain text, so nothing was formatted."


@dataclass(frozen=True, slots=True)
class NamedProfile:
    """One profile: what it overrides, and how it writes structure.

    ``None`` for an override means "as Dictation Settings say"."""

    id: str
    name: str
    description: str
    structure: str = "markdown"
    pause: str | None = None
    remove_fillers: bool | None = None
    auto_punctuation: bool | None = None

    @property
    def word_list(self) -> str:
        """The name a per-profile word list is filed under (D-20/D-21)."""
        return self.id


PROFILES: tuple[NamedProfile, ...] = (
    NamedProfile(
        "standard",
        "Standard",
        "Your Dictation Settings as they are; headings are written as Markdown marks.",
    ),
    NamedProfile(
        "email",
        "Email",
        "For messages: fillers removed, punctuation added, headings and bold "
        "through QUILL's own formatting where the document has it.",
        structure="formatted",
        remove_fillers=True,
        auto_punctuation=True,
    ),
    NamedProfile(
        "document",
        "Document",
        "For letters and reports: headings, bold and italic through QUILL's own "
        "formatting; elsewhere they type nothing and dictation says so.",
        structure="formatted",
    ),
    NamedProfile(
        "markdown",
        "Markdown",
        "Headings, bold and italic written as Markdown marks, in any program.",
        structure="markdown",
    ),
    NamedProfile(
        "chat",
        "Chat",
        "Plain text for chat and messages: no heading marks, fillers removed.",
        structure="plain",
        remove_fillers=True,
    ),
    NamedProfile(
        "coding",
        "Coding",
        "For code and comments: you say every mark, fillers removed, a longer pause.",
        structure="markdown",
        pause="long",
        remove_fillers=True,
        auto_punctuation=False,
    ),
    NamedProfile(
        "verbatim",
        "Verbatim",
        "Every word as you said it: fillers kept, plain text.",
        structure="plain",
        remove_fillers=False,
    ),
)

_BY_ID = {profile.id: profile for profile in PROFILES}


def coerce_profile(value: object) -> str:
    """A known profile id, or the default for anything else."""
    text = str(value or "").strip().lower()
    return text if text in _BY_ID else DEFAULT_PROFILE


def profile_by_id(profile_id: object) -> NamedProfile:
    return _BY_ID[coerce_profile(profile_id)]


def active_profile(settings: object) -> NamedProfile:
    """The profile *settings* has in use. Never raises."""
    try:
        return profile_by_id(getattr(settings, "windows_dictation_profile", DEFAULT_PROFILE))
    except Exception:  # noqa: BLE001 - a settings object of any shape
        return _BY_ID[DEFAULT_PROFILE]


def active_profile_name(settings: object) -> str:
    """The id of the profile in use ("standard", "email", ...): the simple API
    other code asks, for example to choose a per-profile word list."""
    return active_profile(settings).id


def profile_labels() -> list[tuple[str, str]]:
    """``(id, "Name: description")`` for a chooser, in order."""
    return [(profile.id, f"{profile.name}: {profile.description}") for profile in PROFILES]
