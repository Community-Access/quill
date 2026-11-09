"""The Jev request, built from what is safe to send (command-key.md 7.2 to 7.4).

Shared, wx-free code: the client builds exactly this, and the Community Access
gateway runs a copy of it for ``/v1/decide``, so the own-key route and the
gateway route ask Jev the same questions about the same state.

**What is sent.** The words typed or heard (at most 300 characters), the app's
id, the surface name, the ids of the last few commands the box ran, the last
"Did you mean" offer, whether the computer found a number or a duration, and
the candidate commands' own descriptions and one example each.

**What is never sent.** Document text, the selection, file names, station or
episode names, places, account names, or anything a Quillin contributes.
:func:`payload_is_private` is the check the property tests run on every
request, and :func:`build_request` refuses to build one that fails it.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from quill.core.command_catalogue.args import ReadArgs
from quill.core.command_catalogue.resolver import Candidate
from quill.core.command_catalogue.spec import ArgKind, Kind
from quill.core.error_codes import CodedError

__all__ = [
    "JEV_MODEL",
    "MAX_CANDIDATES",
    "MAX_REQUEST_CHARS",
    "NONE_OF_THESE",
    "JevRequest",
    "PrivateDataInRequest",
    "build_request",
    "payload_is_private",
]

#: The pinned model (7.6). A new version runs the recorded suite before this moves.
JEV_MODEL = "jev-1.14.0"
#: The catalogue version the gateway's copy of the descriptions is keyed by.
CATALOGUE_VERSION = "2026-11-09"
#: At most this many candidates go in one choice (Jev allows 255; 7.4).
MAX_CANDIDATES = 60
MAX_REQUEST_CHARS = 300
#: The option every choice carries, because a choice always picks something.
NONE_OF_THESE = "none"
_RECENT = 5


class PrivateDataInRequest(CodedError):
    """A request would have carried something the person never agreed to send."""

    code = "QUILL-AI-DECIDE-PRIVATE-DATA"


@dataclass(frozen=True, slots=True)
class JevRequest:
    """One request: the body for TypeSafe, and the ids its choice offered."""

    body: Mapping[str, Any]
    offered: tuple[str, ...]
    #: The candidate ids, so a "group" fan-out can map back. Same as offered today.
    question_set: str = "basic"
    private_words: tuple[str, ...] = field(default=(), repr=False)


def _criterion(candidate: Candidate) -> str:
    spec = candidate.spec
    example = f' For example: "{spec.examples[0]}".' if spec.examples else ""
    return f"{spec.description or spec.title}.{example}"


def _state(
    text: str,
    app: str,
    surface: str,
    args: ReadArgs,
    recent: Sequence[str],
    last_offer: Sequence[str],
    heard_alternatives: Sequence[str],
) -> dict[str, Any]:
    state: dict[str, Any] = {
        "request": text[:MAX_REQUEST_CHARS],
        "app": app,
        "surface": surface,
        "recent": [{"id": command_id} for command_id in list(recent)[-_RECENT:]],
        "last_offer": list(last_offer),
        "local_matches": {"number": args.number, "duration_seconds": args.seconds},
    }
    if heard_alternatives:
        state["heard_alternatives"] = [item[:MAX_REQUEST_CHARS] for item in heard_alternatives[:2]]
    return state


def _questions(candidates: Sequence[Candidate], with_correction: bool) -> dict[str, Any]:
    criteria = {item.spec.id: _criterion(item) for item in candidates}
    criteria[NONE_OF_THESE] = "None of these: the request asks for something else."
    questions: dict[str, Any] = {
        "fits": {
            "type": "noul",
            "instructions": (
                "The request asks this app to do one of the listed actions, or asks what it can do."
            ),
        },
        "action": {
            "type": "choice",
            "instructions": "Which action does the request ask for?",
            "criteria": criteria,
        },
        "is_question": {
            "type": "noul",
            "instructions": "The request asks for information, not an action.",
        },
    }
    if any(arg.kind is ArgKind.STEPPED for item in candidates for arg in item.spec.args) or any(
        item.spec.kind is Kind.STEP for item in candidates
    ):
        questions["size"] = {
            "type": "choice",
            "instructions": "If the action is a step, how big a step does the request want?",
            "criteria": {"small": "A little, or one step.", "large": "A lot, or several steps."},
        }
    if with_correction:
        questions["correction"] = {
            "type": "noul",
            "instructions": "The request corrects or rejects the previous result.",
        }
    return questions


def payload_is_private(body: Mapping[str, Any], private_words: Sequence[str]) -> bool:
    """True when none of *private_words* appears anywhere in the request body.

    *private_words* are the person's own: the document's text, its file name,
    station and episode names, places, account names. A name typed into the
    request itself is still the person's words, so the check is on everything
    *except* ``state.request`` and ``state.heard_alternatives``.
    """
    import json

    state = dict(body.get("state", {}))
    state.pop("request", None)
    state.pop("heard_alternatives", None)
    rest = json.dumps({**body, "state": state}, ensure_ascii=False).lower()
    return not any(word and word.lower() in rest for word in private_words)


def build_request(
    text: str,
    candidates: Sequence[Candidate],
    *,
    app: str,
    surface: str,
    args: ReadArgs,
    recent: Sequence[str] = (),
    last_offer: Sequence[str] = (),
    heard_alternatives: Sequence[str] = (),
    private_words: Sequence[str] = (),
) -> JevRequest:
    """The request for *text*, over at most :data:`MAX_CANDIDATES` candidates.

    The candidates are kept in the order given (tier 2's ranking, so the right
    answer is usually near the top) and never cut to tier 2's top few, because
    Jev exists for the cases tier 2 misjudges (7.4).
    """
    chosen = tuple(candidates[:MAX_CANDIDATES])
    body = {
        "model": JEV_MODEL,
        "state": _state(text, app, surface, args, recent, last_offer, heard_alternatives),
        "questions": _questions(chosen, with_correction=bool(recent or last_offer)),
    }
    if not payload_is_private(body, private_words):
        raise PrivateDataInRequest("A request to Jev would have carried private words.")
    return JevRequest(
        body=body,
        offered=tuple(item.spec.id for item in chosen),
        private_words=tuple(private_words),
    )
