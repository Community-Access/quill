"""What the Command Key does with a sentence (command-key.md 6.2, 6.4, 8 and 10).

:func:`decide` turns a sentence into a :class:`Decision` without doing anything:
run this, confirm this, ask which of these, show the help list, undo, repeat,
or refuse and say why. :class:`CommandKeySession` carries a decision out, and
is **the only code in the family that runs a command for a sentence** -- a
source test holds that line, because every safety rule below lives here:

- only a command on the candidate list is ever run, whatever chose it;
- a NEVER command is never on that list, so it is never run;
- a CONFIRM command always asks first, at any confidence;
- the command is checked again just before it runs, and is not run if it
  stopped being available;
- the run is always ``registry.run(id)``, the same call a menu makes;
- everything said is the app's own words.

All of it is wx-free. The app supplies a :class:`CommandKeyHost` -- its
registry, its candidate list, and how it speaks, confirms and shows a list.
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Protocol

from quill.core.command_catalogue.args import ReadArgs, read_args
from quill.core.command_catalogue.errors import CommandNoLongerAvailable, CommandNotOffered
from quill.core.command_catalogue.resolver import ACT_SCORE, ASK_SCORE, Candidate, Ranked, resolve
from quill.core.command_catalogue.spec import CommandSpec, Kind, Risk
from quill.core.command_catalogue.words import normalize

__all__ = [
    "CommandKeyHost",
    "CommandKeySession",
    "Decision",
    "Outcome",
    "Refusal",
    "Unavailable",
    "decide",
]

_log = logging.getLogger(__name__)

#: A refusal may point at a window this loosely matched: it only explains, never runs.
POINTER_SCORE = 0.4

#: How many of the box's own actions "undo that" can walk back.
UNDO_DEPTH = 5

HELP_PHRASES = frozenset({
    "help",
    "what can i say",
    "what can i say here",
    "what can i ask",
    "what can i ask here",
    "what can i do",
    "what can i do here",
    "what can you do",
    "what can i type",
    "what are my options",
    "list commands",
})
DICTATION_HELP_PHRASES = frozenset({
    "what can i say while dictating",
    "what can i say when dictating",
    "dictation help",
    "help with dictation",
})
_HELP_ABOUT = ("what can i say about ", "what can i do with ", "what can i do about ", "help with ")
UNDO_PHRASES = frozenset({
    "undo that",
    "undo what you did",
    "undo the last command",
    "reverse that",
})
REPEAT_PHRASES = frozenset({"do that again", "again", "once more", "repeat", "same again", "more"})
CANCEL_PHRASES = frozenset({"cancel", "never mind", "nevermind", "nothing", "forget it"})
#: Words that mean the person wants something sent, deleted, signed in to or
#: given away. A sentence holding one is refused as NEVER unless the command it
#: matched says that word itself (Clear Bookmarks says "clear").
DANGER_VERBS = frozenset({
    "delete",
    "erase",
    "remove",
    "wipe",
    "destroy",
    "send",
    "email",
    "publish",
    "post",
    "upload",
    "push",
    "share",
    "sign",
    "login",
    "logout",
    "password",
    "install",
    "uninstall",
    "update",
    "clear",
    "exit",
    "quit",
})
#: How a request for Ask usually starts: a question about the world, or a
#: piece of writing. Only consulted when nothing in the window matched.
_ASK_OPENINGS = (
    "why ",
    "who ",
    "how do ",
    "how does ",
    "how is ",
    "explain ",
    "write me ",
    "write a ",
    "tell me about ",
    "tell me a ",
    "what is a ",
    "what is the meaning ",
    "summarize ",
    "summarise ",
    "translate ",
    "can you write ",
)


class Outcome(StrEnum):
    RUN = "run"
    CHOOSE = "choose"
    HELP = "help"
    DICTATION_HELP = "dictation_help"
    UNDO = "undo"
    REPEAT = "repeat"
    CANCEL = "cancel"
    REFUSE = "refuse"
    EMPTY = "empty"


class Refusal(StrEnum):
    """The kinds of "no", matching the corpus's ``refuse`` values."""

    NOT_HERE = "not_here"
    NEVER = "never"
    ASK = "ask"
    OTHER_APP = "other_app"
    DISABLED = "disabled"


@dataclass(frozen=True, slots=True)
class Unavailable:
    """A row that is here but cannot run now, with the probe's reason."""

    spec: CommandSpec
    reason: str


@dataclass(frozen=True, slots=True)
class Decision:
    outcome: Outcome
    candidate: Candidate | None = None
    choices: tuple[Candidate, ...] = ()
    args: ReadArgs = field(default_factory=lambda: ReadArgs(remainder=""))
    refusal: Refusal | None = None
    message: str = ""
    help_filter: str = ""
    tier: int = 0

    @property
    def command_id(self) -> str:
        return self.candidate.spec.id if self.candidate is not None else ""


# -- refusal sentences: short, and the app's own words (14.6: at most 12 words) --

NOT_HERE_MESSAGE = "I can't do that here. Say 'what can I say' for ideas."
ASK_MESSAGE = "That's a question for Ask, on the AI menu."


def never_message(spec: CommandSpec) -> str:
    return f"Not from a sentence: it's in {spec.where}."


def disabled_message(item: Unavailable) -> str:
    return item.reason or f"{item.spec.title} can't be done right now."


def other_app_message(app_name: str) -> str:
    return f"That's in {app_name}."


def _danger_in(text: str, spec: CommandSpec | None) -> str:
    words = set(normalize(text).split())
    hits = words & DANGER_VERBS
    if not hits:
        return ""
    if spec is not None:
        own = set(" ".join(normalize(phrase) for phrase in spec.words()).split())
        own |= set(spec.id.replace(".", "_").split("_"))
        hits -= own
    return sorted(hits)[0] if hits else ""


def _looks_like_ask(text: str) -> bool:
    padded = normalize(text) + " "
    return padded.startswith(_ASK_OPENINGS)


def _shared(text: str) -> Decision | None:
    said = normalize(text)
    if not said:
        return Decision(Outcome.EMPTY)
    if said in HELP_PHRASES:
        return Decision(Outcome.HELP)
    if said in DICTATION_HELP_PHRASES:
        return Decision(Outcome.DICTATION_HELP)
    for opening in _HELP_ABOUT:
        if said.startswith(opening) and said != opening.strip():
            return Decision(Outcome.HELP, help_filter=said[len(opening) :].strip())
    if said in UNDO_PHRASES:
        return Decision(Outcome.UNDO)
    if said in REPEAT_PHRASES:
        return Decision(Outcome.REPEAT)
    if said in CANCEL_PHRASES:
        return Decision(Outcome.CANCEL)
    return None


@dataclass(frozen=True, slots=True)
class Elsewhere:
    """Everything this window cannot do, used only to explain a refusal.

    Never run, never sent to any engine (section 11.5).
    """

    unavailable: tuple[Unavailable, ...] = ()
    never: tuple[CommandSpec, ...] = ()
    #: Rows other family apps offer, with the app's display name.
    other_apps: tuple[tuple[str, CommandSpec], ...] = ()


def _explain(text: str, elsewhere: Elsewhere) -> Decision:
    """Why this window can't, and where it can, when that is known."""
    pools: list[tuple[Refusal, list[Candidate], Callable[[Candidate], str]]] = []
    disabled = {item.spec.id: item for item in elsewhere.unavailable}
    pools.append((
        Refusal.DISABLED,
        [Candidate(item.spec) for item in elsewhere.unavailable],
        lambda found: disabled_message(disabled[found.spec.id]),
    ))
    pools.append((
        Refusal.NEVER,
        [Candidate(spec) for spec in elsewhere.never],
        lambda found: never_message(found.spec),
    ))
    names = {spec.id: name for name, spec in elsewhere.other_apps}
    pools.append((
        Refusal.OTHER_APP,
        [Candidate(spec) for _name, spec in elsewhere.other_apps],
        lambda found: other_app_message(names[found.spec.id]),
    ))
    for kind, pool, say in pools:
        if not pool:
            continue
        found = resolve(text, pool)
        best = found.best
        if best is not None and (found.confident or best.score >= ACT_SCORE):
            return Decision(
                Outcome.REFUSE, refusal=kind, message=say(best.candidate), args=found.args
            )
    if _looks_like_ask(text):
        return Decision(Outcome.REFUSE, refusal=Refusal.ASK, message=ASK_MESSAGE)
    return Decision(Outcome.REFUSE, refusal=Refusal.NOT_HERE, message=NOT_HERE_MESSAGE)


def _better_elsewhere(text: str, best: Ranked | None, elsewhere: Elsewhere) -> Decision | None:
    """A refusal when a command that is here but off, or NEVER, fits better.

    Without this, switching the right command off would let the next-best one
    run in its place -- "save all my documents" running Save -- which is the
    swap section 14.4 forbids. The command asked for is refused, with its reason.
    """
    disabled = {item.spec.id: item for item in elsewhere.unavailable}
    pool = [Candidate(item.spec) for item in elsewhere.unavailable]
    pool += [Candidate(spec) for spec in elsewhere.never]
    if not pool:
        return None
    rival = resolve(text, pool).best
    if rival is None or rival.score < ASK_SCORE:
        return None
    if best is not None and best.score > rival.score:
        return None
    spec = rival.candidate.spec
    if spec.id in disabled:
        message = disabled_message(disabled[spec.id])
        return Decision(Outcome.REFUSE, refusal=Refusal.DISABLED, message=message)
    return Decision(Outcome.REFUSE, refusal=Refusal.NEVER, message=never_message(spec))


def _exactly_in_another_app(text: str, elsewhere: Elsewhere) -> Decision | None:
    """When nothing here is sure, a word-for-word command in another app wins.

    "go back to live" is loosely Undo in the editor, and exactly Jump to Live
    in Quill Radio; offering Undo would be the wrong question.
    """
    if not elsewhere.other_apps:
        return None
    names = {spec.id: name for name, spec in elsewhere.other_apps}
    found = resolve(text, [Candidate(spec) for _name, spec in elsewhere.other_apps])
    best = found.best
    if best is None or best.score < 1.0 or not found.confident:
        return None
    message = other_app_message(names[best.candidate.spec.id])
    return Decision(Outcome.REFUSE, refusal=Refusal.OTHER_APP, message=message)


def decide(
    text: str,
    candidates: Sequence[Candidate],
    elsewhere: Elsewhere | None = None,
) -> Decision:
    """What to do with *text*, given this window's *candidates*. Does nothing."""
    shared = _shared(text)
    if shared is not None:
        return shared
    elsewhere = elsewhere or Elsewhere()
    offered = [candidate for candidate in candidates if candidate.spec.risk is not Risk.NEVER]
    found = resolve(text, offered)
    best = found.best
    rival = _better_elsewhere(text, best, elsewhere)
    if rival is not None:
        return rival
    sure = best.candidate.spec if best is not None and best.score >= ASK_SCORE else None
    danger = _danger_in(text, sure)
    if danger:
        never = _explain(text, Elsewhere(never=elsewhere.never))
        if never.refusal is Refusal.NEVER:
            return never
        # Point at the window where it is done: the closest command that opens one.
        window = next(
            (
                item.candidate.spec
                for item in found.ranked
                if item.score >= POINTER_SCORE and item.candidate.spec.kind is Kind.OPENS_DIALOG
            ),
            None,
        )
        if window is not None:
            message = f"Not from a sentence: it's in {window.title}."
        else:
            message = "Not from a sentence: use its menu instead."
        return Decision(Outcome.REFUSE, refusal=Refusal.NEVER, message=message)
    if best is not None and found.confident:
        return Decision(Outcome.RUN, candidate=best.candidate, args=found.args, tier=best.tier)
    away = _exactly_in_another_app(text, elsewhere)
    if away is not None:
        return away
    if found.close and not _looks_like_ask(text):
        if len(found.close) == 1:
            only = found.close[0]
            return Decision(
                Outcome.CHOOSE, choices=(only.candidate,), args=found.args, tier=only.tier
            )
        return Decision(
            Outcome.CHOOSE,
            choices=tuple(item.candidate for item in found.close),
            args=found.args,
            tier=found.close[0].tier,
        )
    return _explain(text, elsewhere)


# -- carrying a decision out -----------------------------------------------------


class Registry(Protocol):
    def get(self, command_id: str) -> object | None: ...
    def unavailable_reason(self, command_id: str) -> str: ...
    def run(self, command_id: str) -> None: ...
    def arm_repeat(self, count: int) -> None: ...


class CommandKeyHost(Protocol):
    """What an app gives the Command Key. Every method is the app's own."""

    app: str
    registry: Registry

    def candidates(self) -> Sequence[Candidate]: ...
    def elsewhere(self) -> Elsewhere: ...
    def announce(self, text: str) -> None: ...
    def confirm(self, question: str) -> bool: ...
    def choose(self, choices: Sequence[Candidate]) -> Candidate | None: ...
    def show_help(self, help_filter: str) -> Candidate | None: ...
    def show_dictation_help(self) -> None: ...
    def run_with_args(self, spec: CommandSpec, args: Mapping[str, object]) -> bool: ...


@dataclass(frozen=True, slots=True)
class _Done:
    spec: CommandSpec
    steps: int


def confirm_question(spec: CommandSpec) -> str:
    return f"{spec.title}? Enter to go ahead, Escape to cancel."


@dataclass
class CommandKeySession:
    """One app's Command Key: decides, confirms, re-checks and runs.

    The undo ring and the last command live here, so "undo that" and "do that
    again" mean the box's own last actions, in this app, and nothing else.
    """

    host: CommandKeyHost
    #: Called with every decision, for tests and for the palette's usage memory.
    on_decision: Callable[[Decision], None] | None = None
    #: Tiers 3 and 4 (:mod:`assist`): asked only what tiers 1 and 2 left open.
    assist: Callable[[str, Sequence[Candidate]], object | None] | None = None
    _done: list[_Done] = field(default_factory=list)

    def submit(self, text: str) -> Decision:
        candidates = tuple(self.host.candidates())
        decision = decide(text, candidates, self.host.elsewhere())
        decision = self._assisted(text, candidates, decision)
        if self.on_decision is not None:
            self.on_decision(decision)
        self._carry_out(decision, candidates)
        return decision

    def _assisted(
        self, text: str, candidates: tuple[Candidate, ...], decision: Decision
    ) -> Decision:
        """Ask the assist, but only about what the offline tiers left open.

        A refusal made on purpose -- NEVER, a dangerous verb, switched off here,
        another app's -- is never handed to an engine to second-guess.
        """
        open_question = decision.outcome is Outcome.CHOOSE or (
            decision.outcome is Outcome.REFUSE
            and decision.refusal in {Refusal.NOT_HERE, Refusal.ASK}
        )
        if self.assist is None or not open_question or not candidates:
            return decision
        offered = [item for item in candidates if item.spec.risk is not Risk.NEVER]
        suggested = self.assist(text, offered)
        kind = getattr(suggested, "kind", "")
        picked = tuple(getattr(suggested, "candidates", ()))
        args = getattr(suggested, "args", decision.args)
        tier = int(getattr(suggested, "tier", 3))
        if kind == "run" and len(picked) == 1:
            return Decision(Outcome.RUN, candidate=picked[0], args=args, tier=tier)
        if kind == "choose" and picked:
            return Decision(Outcome.CHOOSE, choices=picked[:3], args=args, tier=tier)
        return decision

    def run_candidate(self, candidate: Candidate, args: ReadArgs | None = None) -> bool:
        """Run one chosen row (from "Did you mean" or the help list), with every check."""
        return self._run(candidate, args or ReadArgs(remainder=""), tuple(self.host.candidates()))

    # -- the outcomes ---------------------------------------------------------

    def _carry_out(self, decision: Decision, candidates: tuple[Candidate, ...]) -> None:
        outcome = decision.outcome
        if outcome is Outcome.RUN and decision.candidate is not None:
            self._run(decision.candidate, decision.args, candidates)
        elif outcome is Outcome.CHOOSE:
            picked = self.host.choose(decision.choices)
            if picked is not None:
                self._run(picked, decision.args, tuple(self.host.candidates()))
        elif outcome is Outcome.HELP:
            picked = self.host.show_help(decision.help_filter)
            if picked is not None:
                self._run(picked, ReadArgs(remainder=""), tuple(self.host.candidates()))
        elif outcome is Outcome.DICTATION_HELP:
            self.host.show_dictation_help()
        elif outcome is Outcome.UNDO:
            self._undo(candidates)
        elif outcome is Outcome.REPEAT:
            self._repeat(candidates)
        elif outcome is Outcome.REFUSE:
            self.host.announce(decision.message)

    def _offered(self, candidate: Candidate, candidates: tuple[Candidate, ...]) -> bool:
        ids = {item.spec.id for item in candidates}
        if candidate.spec.id in ids and candidate.spec.risk is not Risk.NEVER:
            return True
        error = CommandNotOffered(f"{candidate.spec.id} was chosen but not offered")
        _log.error("%s", error)
        return False

    def _still_available(self, spec: CommandSpec) -> bool:
        registry = self.host.registry
        reason = ""
        if registry.get(spec.id) is None:
            reason = f"{spec.title} can't be done right now."
        else:
            reason = registry.unavailable_reason(spec.id)
        if not reason:
            return True
        _log.info("%s", CommandNoLongerAvailable(f"{spec.id}: {reason}"))
        self.host.announce(reason)
        return False

    def _run(self, candidate: Candidate, args: ReadArgs, candidates: tuple[Candidate, ...]) -> bool:
        spec = candidate.spec
        if not self._offered(candidate, candidates):
            self.host.announce(NOT_HERE_MESSAGE)
            return False
        if spec.risk is Risk.CONFIRM and not self.host.confirm(confirm_question(spec)):
            return False
        if not self._still_available(spec):
            return False
        steps = args.steps if spec.kind is Kind.STEP else 1
        found = args.as_dict()
        if not (found and self.host.run_with_args(spec, found)):
            if steps > 1:
                self.host.registry.arm_repeat(steps)
            self.host.registry.run(spec.id)
        self._done.append(_Done(spec, steps))
        del self._done[:-UNDO_DEPTH]
        if not spec.announces_itself and spec.kind not in {Kind.OPENS_DIALOG, Kind.READOUT}:
            self.host.announce(f"{spec.title}.")
        return True

    def _undo(self, candidates: tuple[Candidate, ...]) -> None:
        if not self._done:
            self.host.announce("Nothing to undo from here yet.")
            return
        last = self._done[-1]
        by_id = {item.spec.id: item for item in candidates}
        opposite = by_id.get(last.spec.opposite) if last.spec.opposite else None
        if opposite is None and last.spec.kind is Kind.TOGGLE:
            # A toggle is undone by throwing it again.
            opposite = by_id.get(last.spec.id)
        elif opposite is None and last.spec.kind is Kind.ACTION:
            opposite = next((by_id[uid] for uid in _UNDO_IDS if uid in by_id), None)
        if opposite is None:
            self.host.announce(f"I can't undo {last.spec.title}.")
            return
        self._done.pop()
        if self._run(
            opposite, ReadArgs(remainder="", size="large" if last.steps > 1 else ""), candidates
        ):
            self._done.pop()

    def _repeat(self, candidates: tuple[Candidate, ...]) -> None:
        if not self._done:
            self.host.announce("Nothing to do again yet.")
            return
        last = self._done[-1]
        here = next((item for item in candidates if item.spec.id == last.spec.id), None)
        if here is None:
            self.host.announce(NOT_HERE_MESSAGE)
            return
        self._run(here, ReadArgs(remainder="", size="large" if last.steps > 1 else ""), candidates)


#: The commands that mean "undo" in each app, for an action with no opposite.
_UNDO_IDS = ("edit.undo", "lite.cmd_undo", "app.undo_last")


def parse_only(text: str) -> ReadArgs:
    """The arguments in *text*, read the way :func:`decide` reads them."""
    return read_args(normalize(text))


def describe(ranked: Ranked) -> str:
    """A row as "Did you mean" lists it: its title, then its key when it has one."""
    spec = ranked.candidate.spec
    return f"{spec.title}, {ranked.candidate.key}" if ranked.candidate.key else spec.title
