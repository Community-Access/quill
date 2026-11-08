"""What one catalogue row is (command-key.md section 5.2).

The static half of the family command catalogue: what a command *is*, written
once, wx-free. The runtime half -- whether it can run right now -- stays in
:class:`quill.core.commands.CommandRegistry` and its per-command probes. The two
are joined by command id and by nothing else.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

__all__ = ["Arg", "ArgKind", "CommandSpec", "Kind", "Risk"]


class Risk(StrEnum):
    """Whether a sentence may run the command (section 5.3)."""

    #: Runs when the match is confident.
    SAFE = "safe"
    #: Always asks first, at any confidence.
    CONFIRM = "confirm"
    #: Never offered to a sentence; stays in the palette and on its key.
    NEVER = "never"


class Kind(StrEnum):
    """What running the command does, which decides what is said afterwards."""

    ACTION = "action"
    TOGGLE = "toggle"
    OPENS_DIALOG = "opens_dialog"
    #: Answers a question from the app ("what's playing"). Its handler speaks.
    READOUT = "readout"
    #: One step of a stepped value: louder, faster, bigger.
    STEP = "step"


class ArgKind(StrEnum):
    """The argument shapes the local reader understands (section 5.4)."""

    STEPPED = "stepped"
    NUMBER = "number"
    DURATION = "duration"
    WHEN = "when"
    CHOICE = "choice"
    #: Matched on the computer against the person's own list; never sent anywhere.
    NAME = "name"
    FILE = "file"


@dataclass(frozen=True, slots=True)
class Arg:
    """One argument a command can take from a sentence."""

    name: str
    kind: ArgKind
    #: The closed set, for :attr:`ArgKind.CHOICE`.
    choices: tuple[str, ...] = ()
    required: bool = False


@dataclass(frozen=True, slots=True)
class CommandSpec:
    """One command, as every reader of the catalogue sees it.

    ``title`` is the spoken name. ``aliases`` are short keys the matcher scores
    against; ``examples`` are whole sentences a person might say, shown in help
    and each one a test. ``description`` is what the person wants, in their
    words, not what the code does.
    """

    id: str
    title: str
    description: str = ""
    aliases: tuple[str, ...] = ()
    examples: tuple[str, ...] = ()
    args: tuple[Arg, ...] = ()
    risk: Risk = Risk.NEVER
    kind: Kind = Kind.ACTION
    #: F1 surface names (window titles); empty means anywhere in the app.
    surfaces: tuple[str, ...] = ()
    #: The menu it lives in, for help pages.
    group: str = ""
    #: The command that undoes or reverses this one, when there is one.
    opposite: str = ""
    #: The handler says its own result, so the Command Key says nothing after it.
    announces_itself: bool = False
    #: Offered to the AI agents and Ask's ``decide``. Never on CONFIRM or NEVER.
    agent_ok: bool = False
    #: Where a person finds it, for "I won't do that from a sentence. It's in ...".
    where: str = ""
    apps: tuple[str, ...] = field(default=("quill",))

    @property
    def offered(self) -> bool:
        """True when a sentence may reach this command at all."""
        return self.risk is not Risk.NEVER

    def words(self) -> tuple[str, ...]:
        """The title, aliases and examples, lower-cased: what a matcher reads."""
        return tuple(text.lower() for text in (self.title, *self.aliases, *self.examples) if text)
