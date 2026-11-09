"""Fakes for the Command Key (docs/design/command-key.md 14.2), wx-free.

``FakeRegistry`` scripts what is registered, what is available, and changes
between asking and running. ``FakeHost`` is an app: it hands the session its
candidates and records every word spoken (speech and braille are one channel
here, as they are through the announcement service) and every question asked.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field

from quill.core.command_catalogue import CommandSpec, Risk, rows_for_app
from quill.core.command_catalogue.policy import Elsewhere, Unavailable
from quill.core.command_catalogue.resolver import Candidate


@dataclass
class FakeRegistry:
    """Registered ids, their unavailability reasons, and what ran."""

    ids: set[str]
    reasons: dict[str, str] = field(default_factory=dict)
    ran: list[str] = field(default_factory=list)
    repeats: list[int] = field(default_factory=list)
    #: Called just before a run, to change the world under the session's feet.
    before_run: Callable[[str], None] | None = None
    _armed: int = 1

    def get(self, command_id: str) -> object | None:
        return object() if command_id in self.ids else None

    def unavailable_reason(self, command_id: str) -> str:
        return self.reasons.get(command_id, "")

    def arm_repeat(self, count: int) -> None:
        self._armed = count
        self.repeats.append(count)

    def run(self, command_id: str) -> None:
        if command_id not in self.ids:
            raise KeyError(command_id)
        if self.before_run is not None:
            self.before_run(command_id)
        for _ in range(self._armed):
            self.ran.append(command_id)
        self._armed = 1


@dataclass
class FakeHost:
    """One app window, scripted."""

    app: str
    registry: FakeRegistry
    rows: tuple[CommandSpec, ...] = ()
    other_apps: tuple[tuple[str, CommandSpec], ...] = ()
    confirm_answer: bool = True
    #: Which of the offered choices "Did you mean" picks; None means Escape.
    choose_index: int | None = 0
    help_pick: str | None = None
    with_args: Callable[[CommandSpec, Mapping[str, object]], bool] | None = None
    spoken: list[str] = field(default_factory=list)
    questions: list[str] = field(default_factory=list)
    offered_choices: list[tuple[str, ...]] = field(default_factory=list)
    help_filters: list[str] = field(default_factory=list)
    dictation_help_shown: int = 0

    def __post_init__(self) -> None:
        if not self.rows:
            self.rows = rows_for_app(self.app)

    def candidates(self) -> Sequence[Candidate]:
        return tuple(
            Candidate(spec)
            for spec in self.rows
            if spec.risk is not Risk.NEVER
            and spec.id in self.registry.ids
            and not self.registry.unavailable_reason(spec.id)
        )

    def elsewhere(self) -> Elsewhere:
        unavailable = tuple(
            Unavailable(spec, self.registry.unavailable_reason(spec.id))
            for spec in self.rows
            if spec.offered
            and spec.id in self.registry.ids
            and self.registry.unavailable_reason(spec.id)
        )
        never = tuple(spec for spec in self.rows if not spec.offered)
        return Elsewhere(unavailable=unavailable, never=never, other_apps=self.other_apps)

    def announce(self, text: str) -> None:
        self.spoken.append(text)

    def confirm(self, question: str) -> bool:
        self.questions.append(question)
        return self.confirm_answer

    def choose(self, choices: Sequence[Candidate]) -> Candidate | None:
        self.offered_choices.append(tuple(item.spec.id for item in choices))
        if self.choose_index is None or self.choose_index >= len(choices):
            return None
        return choices[self.choose_index]

    def show_help(self, help_filter: str) -> Candidate | None:
        self.help_filters.append(help_filter)
        if self.help_pick is None:
            return None
        return next((item for item in self.candidates() if item.spec.id == self.help_pick), None)

    def show_dictation_help(self) -> None:
        self.dictation_help_shown += 1

    def run_with_args(self, spec: CommandSpec, args: Mapping[str, object]) -> bool:
        return self.with_args(spec, args) if self.with_args is not None else False


def host_for(app: str, *, disabled: Mapping[str, str] | None = None, **kwargs: object) -> FakeHost:
    """A host where every row of *app* is registered, minus any *disabled* ones' availability."""
    rows = rows_for_app(app)
    registry = FakeRegistry(ids={spec.id for spec in rows}, reasons=dict(disabled or {}))
    return FakeHost(app, registry, rows, **kwargs)  # type: ignore[arg-type]


# -- tiers 3 and 4 --------------------------------------------------------------


@dataclass
class FakeJevClient:
    """Jev, scripted: a rule from the request to an answer, or an error to raise.

    Records every request body, so a test can assert what was and was not sent.
    """

    rule: Callable[[object], dict[str, object]] | None = None
    error: Exception | None = None
    requests: list[dict[str, object]] = field(default_factory=list)

    def decide(self, request: object) -> object:
        from quill.core.command_catalogue.jev import parse_answer

        body = getattr(request, "body", {})
        self.requests.append(dict(body))
        if self.error is not None:
            raise self.error
        raw = self.rule(request) if self.rule is not None else {}
        return parse_answer(raw, getattr(request, "offered", ()))


def jev_answer(
    probabilities: Mapping[str, float],
    *,
    fits: float = 0.9,
    confidence: float | None = None,
    is_question: float = 0.0,
    size: str = "",
) -> dict[str, object]:
    """A raw Jev answer in TypeSafe's shape (answers, model, usage)."""
    top = max(probabilities.values()) if probabilities else 0.0
    n = max(len(probabilities), 2)
    conf = confidence if confidence is not None else (top - 1 / n) / (1 - 1 / n)
    answers: dict[str, object] = {
        "action": {
            "type": "choice",
            "probabilities": dict(probabilities),
            "confidence": max(0.0, conf),
        },
        "fits": {"type": "noul", "noul": fits},
        "is_question": {"type": "noul", "noul": is_question},
    }
    if size:
        answers["size"] = {"type": "choice", "choice": size}
    return {"model": "jev-1.14.0", "answers": answers, "usage": {"input_tokens": 2100}}


@dataclass
class FakeCommandPickEngine:
    """Choose Your AI, scripted: a reply, or an exception."""

    reply: str = "none"
    error: Exception | None = None
    prompts: list[str] = field(default_factory=list)

    def __call__(self, prompt: str) -> str:
        self.prompts.append(prompt)
        if self.error is not None:
            raise self.error
        return self.reply
