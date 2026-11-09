"""Jev as the Command Key's assist: the client, its failures, reading its answer.

docs/design/command-key.md section 7. Jev is TypeSafe's decision model,
``POST https://api.typesafe.ai/v1/systemone``. It is asked only what tiers 1
and 2 could not settle, and only ever chooses among the candidates it was sent.

**Two routes.**

- **The gateway** (the default): ``POST /v1/decide`` on the Community Access
  gateway (``quill-ai-gateway/app/routes/decide.py``, on lp.csedesigns.com),
  with the person's device token. The gateway holds the TypeSafe key, caps use,
  and builds the request itself from its own copy of the catalogue, so the
  client sends only the app, the catalogue version, the ids of the commands it
  can run now (in tier 2's order) and the state. :class:`GatewayJev` answers
  ``disabled`` when it has no base URL.
- **An own key**, for development and for anybody who wants to pay TypeSafe
  themselves. The key is read from Windows Credential Manager (a generic
  credential named ``QUILL TypeSafe dev key``), never from a file, never
  logged, never shown.

**Limits.** Three seconds from the client, in all. A 429's ``retry-after`` is
honoured only within those three seconds. One request in flight at a time.

**Failure is visible, never silent.** Each failure is a coded error (GATE-EC).
A limit, a spent credit or a server switch-off is remembered until the next
day, so the app says one line once and stops asking (section 7.7).
"""

from __future__ import annotations

import json
import threading
import time
import urllib.error
import urllib.request
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import date
from typing import Any, Protocol

from quill.core.command_catalogue.jev_request import NONE_OF_THESE, JevRequest
from quill.core.error_codes import CodedError

__all__ = [
    "DEV_KEY_TARGET",
    "TYPESAFE_URL",
    "GatewayJev",
    "JevAnswer",
    "JevBadAnswer",
    "JevClient",
    "JevDisabled",
    "JevError",
    "JevFailed",
    "JevLimit",
    "JevNoCredit",
    "JevVerdict",
    "OwnKeyJev",
    "Throttle",
    "parse_answer",
    "read_answer",
]

TYPESAFE_URL = "https://api.typesafe.ai/v1/systemone"
#: Said in the live report beside the numbers, so nobody mistakes them for a target.
JEV_MODEL_NOTE = "A few hundred phrasings are a sample, not evidence; see section 14.8."
#: The Windows Credential Manager entry the own-key route reads (generic credential).
DEV_KEY_TARGET = "QUILL TypeSafe dev key"
#: The whole budget for one request, from the client (7.6).
TIMEOUT_SECONDS = 3.0
_USER_AGENT = "QUILL-CommandKey/1"  # Cloudflare refuses Python's default (18.2)

# -- thresholds (6.4), pinned with the model -----------------------------------
ACT_CONFIDENCE = 0.7
ACT_FITS = 0.7
ACT_MARGIN = 0.2
ASK_CONFIDENCE = 0.4
REFUSE_FITS = 0.3
QUESTION = 0.7


class JevError(CodedError):
    """Jev could not answer. The app falls back, and says so once."""

    code = "QUILL-AI-DECIDE-FAILED"
    #: Remembered until tomorrow, so the app stops asking (7.7).
    lasts_the_day = False
    #: The one line the app says, the first time.
    fallback_line = "Jev isn't answering, so I matched it here."


class JevFailed(JevError):
    code = "QUILL-AI-DECIDE-FAILED"


class JevLimit(JevError):
    code = "QUILL-AI-DECIDE-LIMIT"
    lasts_the_day = True
    fallback_line = "Jev's daily limit is reached, so I matched it here."


class JevNoCredit(JevError):
    code = "QUILL-AI-DECIDE-NO-CREDIT"
    lasts_the_day = True
    fallback_line = "Jev's credit is spent for now, so I matched it here."


class JevDisabled(JevError):
    code = "QUILL-AI-DECIDE-DISABLED"
    lasts_the_day = True
    fallback_line = "Jev is turned off, so I matched it here."


class JevBadAnswer(JevError):
    code = "QUILL-AI-DECIDE-BAD-ANSWER"


@dataclass(frozen=True, slots=True)
class JevAnswer:
    """What Jev said, already checked against what it was offered."""

    probabilities: Mapping[str, float]
    confidence: float
    fits: float
    is_question: float = 0.0
    size: str = ""
    correction: float = 0.0
    model: str = ""
    input_tokens: int = 0

    def ranked(self) -> list[tuple[str, float]]:
        return sorted(self.probabilities.items(), key=lambda item: (-item[1], item[0]))


class JevClient(Protocol):
    def decide(self, request: JevRequest) -> JevAnswer: ...


def _number(value: object, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise JevBadAnswer(f"Jev's answer had no number for {name}.")
    number = float(value)
    if not 0.0 <= number <= 1.0:
        raise JevBadAnswer(f"Jev's answer for {name} was out of range.")
    return number


def parse_answer(raw: Mapping[str, Any], offered: Sequence[str]) -> JevAnswer:
    """Check Jev's JSON and keep only options that were offered.

    An option outside the offer is not merely dropped: it means the answer is
    for some other request, so the whole answer is refused (6.2, "output").
    """
    answers = raw.get("answers")
    if not isinstance(answers, Mapping):
        raise JevBadAnswer("Jev's answer had no answers.")
    action = answers.get("action")
    if not isinstance(action, Mapping):
        raise JevBadAnswer("Jev's answer had no action.")
    probabilities = action.get("probabilities")
    if not isinstance(probabilities, Mapping) or not probabilities:
        raise JevBadAnswer("Jev's answer had no probabilities.")
    allowed = set(offered) | {NONE_OF_THESE}
    checked: dict[str, float] = {}
    for option, value in probabilities.items():
        if option not in allowed:
            raise JevBadAnswer("Jev answered with a command it was not offered.")
        checked[str(option)] = _number(value, "an option")
    fits_answer = answers.get("fits", {})
    fits = _number(fits_answer.get("noul") if isinstance(fits_answer, Mapping) else None, "fits")
    question = answers.get("is_question", {})
    is_question = (
        _number(question.get("noul"), "is_question") if isinstance(question, Mapping) else 0.0
    )
    size_answer = answers.get("size", {})
    size = str(size_answer.get("choice", "")) if isinstance(size_answer, Mapping) else ""
    correction_answer = answers.get("correction", {})
    correction = (
        _number(correction_answer.get("noul"), "correction")
        if isinstance(correction_answer, Mapping) and "noul" in correction_answer
        else 0.0
    )
    usage = raw.get("usage", {})
    tokens = usage.get("input_tokens", 0) if isinstance(usage, Mapping) else 0
    return JevAnswer(
        probabilities=checked,
        confidence=_number(action.get("confidence", 0.0), "confidence"),
        fits=fits,
        is_question=is_question,
        size=size if size in {"small", "large"} else "",
        correction=correction,
        model=str(raw.get("model", "")),
        input_tokens=int(tokens) if isinstance(tokens, int) else 0,
    )


@dataclass(frozen=True, slots=True)
class JevVerdict:
    """What the policy does with Jev's answer (7.5)."""

    kind: str  # "act", "ask", "refuse", "readout"
    ids: tuple[str, ...] = ()
    size: str = ""


def read_answer(answer: JevAnswer, readouts: frozenset[str] = frozenset()) -> JevVerdict:
    """Section 7.5's order: fit, question, confident, split, otherwise no."""
    if answer.fits < REFUSE_FITS:
        return JevVerdict("refuse")
    ranked = [(cid, p) for cid, p in answer.ranked() if cid != NONE_OF_THESE]
    none_p = answer.probabilities.get(NONE_OF_THESE, 0.0)
    if not ranked or (ranked[0][1] <= none_p):
        return JevVerdict("refuse")
    top_id, top_p = ranked[0]
    second = ranked[1][1] if len(ranked) > 1 else 0.0
    if answer.is_question >= QUESTION and top_id in readouts:
        return JevVerdict("readout", (top_id,))
    if (
        answer.confidence >= ACT_CONFIDENCE
        and answer.fits >= ACT_FITS
        and top_p - second >= ACT_MARGIN
    ):
        return JevVerdict("act", (top_id,), answer.size)
    if answer.confidence >= ASK_CONFIDENCE or top_p - second < ACT_MARGIN:
        close = tuple(cid for cid, p in ranked[:3] if top_p - p < ACT_MARGIN and p > none_p)
        if close:
            return JevVerdict("ask", close, answer.size)
    return JevVerdict("refuse")


# -- the routes ---------------------------------------------------------------------


@dataclass
class Throttle:
    """One request in flight, and the day's "stop asking" after a limit."""

    today: Callable[[], date] = date.today
    _lock: threading.Lock = field(default_factory=threading.Lock)
    _stopped_on: date | None = None
    _stopped_by: JevError | None = None

    def stopped(self) -> JevError | None:
        if self._stopped_on is not None and self._stopped_on == self.today():
            return self._stopped_by
        self._stopped_on = self._stopped_by = None
        return None

    def stop_for_the_day(self, error: JevError) -> None:
        self._stopped_on = self.today()
        self._stopped_by = error


def _error_for(status: int, payload: Mapping[str, Any]) -> JevError:
    reason = str(payload.get("error", "") or payload.get("code", "")).lower()
    if "no_credit" in reason or status == 402:
        return JevNoCredit("TypeSafe credit is spent.")
    if "disabled" in reason:
        return JevDisabled("Jev is turned off on the server.")
    if "limit" in reason or status == 429:
        return JevLimit("Jev's limit is reached.")
    return JevFailed(f"Jev answered with status {status}.")


def _post_json(
    url: str,
    body: Mapping[str, Any],
    bearer: str,
    deadline: float,
    clock: Callable[[], float] = time.monotonic,
) -> dict[str, Any]:
    """The Command Key's one outbound call (an egress row covers it).

    Sends only the body :mod:`jev_request` built and checked. The bearer is a
    device token or a TypeSafe key; it is never logged and never in an error.
    """
    from quill.core.net import verified_ssl_context

    data = json.dumps(body).encode("utf-8")
    request = urllib.request.Request(url, data=data, method="POST")
    request.add_header("Content-Type", "application/json")
    request.add_header("Accept", "application/json")
    request.add_header("User-Agent", _USER_AGENT)
    request.add_header("Authorization", f"Bearer {bearer}")
    while True:
        remaining = deadline - clock()
        if remaining <= 0:
            raise JevFailed("Jev took longer than three seconds.")
        try:
            with urllib.request.urlopen(  # noqa: S310 - https only, verified context
                request, timeout=remaining, context=verified_ssl_context()
            ) as response:
                raw = response.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as error:
            try:
                payload = json.loads(error.read().decode("utf-8", errors="replace") or "{}")
            except (json.JSONDecodeError, OSError):
                payload = {}
            retry_after = error.headers.get("retry-after") if error.headers else None
            if error.code == 429 and retry_after and not _limit_reason(payload):
                wait = _seconds(retry_after)
                if wait is not None and clock() + wait < deadline:
                    time.sleep(wait)
                    continue
            raise _error_for(error.code, payload if isinstance(payload, dict) else {}) from None
        except (urllib.error.URLError, TimeoutError, OSError):
            raise JevFailed("Jev could not be reached.") from None
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            raise JevBadAnswer("Jev's answer was not JSON.") from None
        if not isinstance(parsed, dict):
            raise JevBadAnswer("Jev's answer was not an object.")
        return parsed


def _limit_reason(payload: object) -> bool:
    return isinstance(payload, dict) and bool(payload.get("error"))


def _seconds(value: str) -> float | None:
    try:
        return max(0.0, float(value))
    except ValueError:
        return None


class _Route:
    def __init__(self, throttle: Throttle | None = None) -> None:
        self.throttle = throttle or Throttle()

    def _call(self, request: JevRequest) -> dict[str, Any]:  # pragma: no cover - abstract
        raise NotImplementedError

    def decide(self, request: JevRequest) -> JevAnswer:
        stopped = self.throttle.stopped()
        if stopped is not None:
            raise stopped
        if not self.throttle._lock.acquire(blocking=False):
            raise JevFailed("Jev is still answering the last request.")
        try:
            raw = self._call(request)
        except JevError as error:
            if error.lasts_the_day:
                self.throttle.stop_for_the_day(error)
            raise
        finally:
            self.throttle._lock.release()
        return parse_answer(raw, request.offered)


class OwnKeyJev(_Route):
    """TypeSafe directly, with a key from Credential Manager (development, own key)."""

    def __init__(
        self,
        key: Callable[[], str] | None = None,
        *,
        post: Callable[..., dict[str, Any]] = _post_json,
        throttle: Throttle | None = None,
    ) -> None:
        super().__init__(throttle)
        self._key = key or _key_from_credential_manager
        self._post = post

    def _call(self, request: JevRequest) -> dict[str, Any]:
        key = self._key()
        if not key:
            raise JevDisabled("No TypeSafe key is stored.")
        return self._post(TYPESAFE_URL, request.body, key, time.monotonic() + TIMEOUT_SECONDS)


class GatewayJev(_Route):
    """``/v1/decide`` on the Community Access gateway, with the device token (7.6)."""

    def __init__(
        self,
        base_url: str = "",
        token: Callable[[], str] = lambda: "",
        *,
        post: Callable[..., dict[str, Any]] = _post_json,
        throttle: Throttle | None = None,
    ) -> None:
        super().__init__(throttle)
        self._base_url = base_url.rstrip("/")
        self._token = token
        self._post = post

    def _call(self, request: JevRequest) -> dict[str, Any]:
        if not self._base_url:
            raise JevDisabled("No gateway address is set.")
        token = self._token()
        if not token:
            raise JevDisabled("This computer is not signed in to QUILL's free AI.")
        body = {
            "app": request.body["state"].get("app", ""),
            "catalogue_version": _catalogue_version(),
            "question_set": request.question_set,
            # Ids only, in tier 2's order: the gateway keeps the descriptions.
            "candidates": list(request.offered),
            "state": request.body["state"],
        }
        return self._post(
            f"{self._base_url}/v1/decide", body, token, time.monotonic() + TIMEOUT_SECONDS
        )


def _catalogue_version() -> str:
    from quill.core.command_catalogue.jev_request import CATALOGUE_VERSION

    return CATALOGUE_VERSION


def _key_from_credential_manager() -> str:
    """The development key, or "" when there is none. Never logged or shown."""
    try:
        from quill.platform.windows.credential_manager import load_generic_credential

        stored = load_generic_credential(DEV_KEY_TARGET)
    except Exception:  # noqa: BLE001 - no Credential Manager means no key
        return ""
    return stored.secret if stored is not None else ""
