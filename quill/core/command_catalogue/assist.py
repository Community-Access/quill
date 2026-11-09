"""Tiers 3 and 4: Jev, then the person's own AI (command-key.md 6.3, 7.5, 7.10).

An assist is asked only when tiers 1 and 2 could not settle a sentence -- a
"Did you mean" or an "I can't do that here" -- and never for a refusal the
policy made on purpose (a NEVER command, a dangerous verb, a command switched
off here). It is handed the same candidate list, and whatever it answers goes
back through the same policy: the id must be a candidate, CONFIRM still asks,
and the command is checked again just before it runs.

- :class:`JevAssist` is tier 3. A failure says one line, once ("Jev's daily
  limit is reached, so I matched it here"), then falls to tier 4 or to the
  offline answer.
- :class:`CommandPickAssist` is tier 4, Choose Your AI. It has no calibrated
  confidence, so it acts without asking only when it agrees with tier 2's best
  guess and the command is SAFE; otherwise it asks (6.4).

Neither ever puts an engine's own words in front of the person: every line
said is the app's.
"""

from __future__ import annotations

import logging
import re
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field

from quill.core.command_catalogue.args import ReadArgs
from quill.core.command_catalogue.jev import JevClient, JevError, read_answer
from quill.core.command_catalogue.jev_request import NONE_OF_THESE, build_request
from quill.core.command_catalogue.resolver import Candidate, rank
from quill.core.command_catalogue.spec import Kind, Risk
from quill.core.error_codes import CodedError

__all__ = [
    "Assist",
    "CommandPickAssist",
    "CommandPickFailed",
    "JevAssist",
    "command_pick_prompt",
    "parse_command_pick",
]

_log = logging.getLogger(__name__)


class CommandPickFailed(CodedError):
    """Choose Your AI could not pick a command (tier 4)."""

    code = "QUILL-AI-COMMANDPICK-FAILED"


@dataclass(frozen=True, slots=True)
class Assisted:
    """What an assist suggests: run one, or ask between some. Never more."""

    kind: str  # "run" or "choose"
    candidates: tuple[Candidate, ...]
    args: ReadArgs
    tier: int


Assist = Callable[[str, Sequence[Candidate]], "Assisted | None"]


def _ordered(text: str, candidates: Sequence[Candidate]) -> tuple[list[Candidate], ReadArgs]:
    """Tier 2's ranking first, then every other candidate: the list is never cut."""
    ranked, args = rank(text, candidates)
    first = [item.candidate for item in ranked]
    seen = {item.spec.id for item in first}
    return first + [item for item in candidates if item.spec.id not in seen], args


@dataclass
class JevAssist:
    """Tier 3: Jev, through the gateway or an own key."""

    client: JevClient
    app: str
    announce: Callable[[str], None]
    surface: str = ""
    fallback: Assist | None = None
    recent: Callable[[], Sequence[str]] = lambda: ()
    #: The person's own words to keep out of every request: document text,
    #: file names, stations. Asked for per request (7.2).
    private_words: Callable[[], Sequence[str]] = lambda: ()
    _said: set[str] = field(default_factory=set)

    def __call__(self, text: str, candidates: Sequence[Candidate]) -> Assisted | None:
        ordered, args = _ordered(text, candidates)
        if not ordered:
            return None
        try:
            request = build_request(
                text,
                ordered,
                app=self.app,
                surface=self.surface,
                args=args,
                recent=self.recent(),
                private_words=self.private_words(),
            )
            answer = self.client.decide(request)
        except JevError as error:
            _log.info("%s", error)
            if error.code not in self._said:
                self._said.add(error.code)
                line = error.fallback_line
                if self.fallback is not None:  # tier 4 is next, so say so (7.7)
                    line = line.replace("so I matched it here", "so I'm asking your AI")
                self.announce(line)
            return self.fallback(text, candidates) if self.fallback is not None else None
        except CodedError as error:  # a private word: nothing was sent
            _log.warning("%s", error)
            return None
        readouts = frozenset(item.spec.id for item in ordered if item.spec.kind is Kind.READOUT)
        verdict = read_answer(answer, readouts)
        by_id = {item.spec.id: item for item in ordered}
        picked = tuple(by_id[cid] for cid in verdict.ids if cid in by_id)
        if verdict.kind in {"act", "readout"} and picked:
            size = verdict.size or args.size
            return Assisted(
                "run", picked[:1], ReadArgs(args.remainder, args.number, args.seconds, size), 3
            )
        if verdict.kind == "ask" and picked:
            return Assisted("choose", picked, args, 3)
        return None


def command_pick_prompt(text: str, candidates: Sequence[Candidate]) -> str:
    """One question for the person's AI: the request, and the ids to choose from."""
    lines = [
        "A person asked an app to do something. Reply with exactly one command id "
        "from this list, or with the word none if nothing in the list fits. Reply "
        "with the id only.",
        "",
        f"Request: {text[:300]}",
        "",
        "Commands:",
    ]
    for item in candidates:
        spec = item.spec
        lines.append(f"- {spec.id}: {spec.description or spec.title}")
    return "\n".join(lines)


def parse_command_pick(reply: str, candidates: Sequence[Candidate]) -> Candidate | None:
    """The one candidate named in *reply*, or None for "none", nothing, or several.

    The reply may come wrapped in prose or quotes; an id is found as a whole
    token. An id that is not a candidate is not found at all, so it cannot run.
    """
    ids = {item.spec.id: item for item in candidates}
    tokens = set(re.findall(r"[a-z][a-z0-9_]*(?:\.[a-z0-9_]+)+", reply.lower()))
    named = [ids[token] for token in tokens if token in ids]
    if len(named) != 1:
        return None
    return named[0]


@dataclass
class CommandPickAssist:
    """Tier 4: the AI chosen in Choose Your AI, asked one question."""

    ask: Callable[[str], str]

    def __call__(self, text: str, candidates: Sequence[Candidate]) -> Assisted | None:
        ordered, args = _ordered(text, candidates)
        if not ordered:
            return None
        try:
            reply = self.ask(command_pick_prompt(text, ordered[:60]))
        except Exception as error:  # noqa: BLE001 - any engine failure is one coded failure
            _log.info("%s", CommandPickFailed(str(error) or type(error).__name__))
            return None
        if reply.strip().lower() == NONE_OF_THESE:
            return None
        picked = parse_command_pick(reply, ordered)
        if picked is None:
            return None
        ranked, _args = rank(text, ordered)
        agrees = bool(ranked) and ranked[0].candidate.spec.id == picked.spec.id
        if agrees and picked.spec.risk is Risk.SAFE:
            return Assisted("run", (picked,), args, 4)
        return Assisted("choose", (picked,), args, 4)
