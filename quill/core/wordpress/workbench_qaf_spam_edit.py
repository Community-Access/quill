"""Changing QUILL Accessible Forms' spam settings from the Workbench (complete.md WP-C).

The read side is :mod:`quill.core.wordpress.workbench_qaf_spam`. This is the
write side, over the routes QAF added for it (QAF README, "Spam settings over
REST"):

- ``POST qaf/v1/spam``: only what is sent changes; ``if_revision`` refuses a
  write made after somebody else's (409); the OOPSpam key is write-only.
- ``GET``/``POST qaf/v1/spam/questions`` and ``POST``/``DELETE
  qaf/v1/spam/questions/{id}``: the site's own question bank. A question's id
  comes from its words, so an id read before somebody else changed it
  answers 404.
- ``GET qaf/v1/spam/weeks``: this week's question numbers and the weeks
  before, newest first; the weekly Watch compares them.

Every change is read again first (the conflict check), sent, and then read
back and compared (the verify), and the sentence said afterwards says what
the site now holds. The OOPSpam key is the one value that is never in a
preview, a sentence, Change History or an error: only "a new key" and
whether one is saved.

Writes need ``qaf/v1``. A site that lists only ``baf/v1`` runs the older
BITS Accessible Forms build (or a QAF whose old name is a read-only alias),
so its settings are shown and :func:`write_refusal` says why they cannot be
changed from QUILL. Wx-free.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import replace
from typing import Any

from quill.core.wordpress.api import WordPressApiError
from quill.core.workbench.actions import ActionRow, Tier
from quill.core.workbench.properties import FieldChange, FieldKind, FieldSpec, SheetSpec

__all__ = [
    "KEYLESS",
    "PROVIDERS",
    "QAF_SPAM_ROWS",
    "SpamConflict",
    "add_question",
    "delete_question",
    "edit_question",
    "namespace_note",
    "parse_answers",
    "question_line",
    "read_questions",
    "read_weeks",
    "save_spam_settings",
    "spam_body",
    "spam_preview",
    "spam_values",
    "weekly_watch",
    "weeks_text",
    "with_spam_fields",
    "write_refusal",
]

WRITE_NAMESPACE = "qaf/v1"
LEGACY_NAMESPACE = "baf/v1"

#: Each check QAF runs, in the order its Settings > Spam lists them.
PROVIDERS: Mapping[str, str] = {
    "honeypot": "Hidden trap field",
    "time": "Time to fill",
    "links": "Link count",
    "patterns": "Code in answers",
    "blocklist": "WordPress's disallowed and moderation words",
    "rate_limit": "Rate limit",
    "token": "Form token",
    "captcha": "CAPTCHA",
    "akismet": "Akismet (sends what visitors type to Akismet)",
    "oopspam": "OOPSpam (sends what visitors type to OOPSpam)",
    "cleantalk": "CleanTalk (sends what visitors type to CleanTalk)",
    "shield": "Shield Security",
    "altcha": "Proof of work",
    "challenge": "Questions",
}
_KINDS: Mapping[str, str] = {
    "sense": "Everyday sense questions",
    "instruction": "Follow-an-instruction questions",
    "choice": "Pick-the-answer questions",
    "order": "Put-in-order questions",
    "maths": "Sums (a barrier for people with dyscalculia)",
}
#: (setting, label, lowest, highest), as QAF checks them.
_NUMBERS: tuple[tuple[str, str, int, int], ...] = (
    ("min_seconds", "Fewest seconds on the page", 3, 120),
    ("max_links", "Most links in an answer", 0, 50),
    ("oopspam_threshold", "OOPSpam score that holds", 1, 6),
    ("altcha_max_number", "Proof of work, largest number", 1000, 1000000),
)
_MODES: Mapping[str, str] = {
    "auto": "Only when the other checks are unsure",
    "always": "On every form",
    "never": "Never; hold doubtful forms instead",
}
_SEND_ANYWAY = ("send_anyway_after", "Offer Send Anyway after this many wrong answers", 1, 10)
_KEY = "qaf_oopspam_key"
_KEY_CLEAR = "qaf_oopspam_key_clear"
_P = "qaf_"  # every field this module adds is named qaf_<setting>, so none meets the site sheet's


def command(verb: str) -> str:
    """The same ids as :func:`quill.core.wordpress.workbench_window_menu.command`."""
    return f"wordpress.workbench.{verb}"


QAF_SPAM_ROWS: tuple[ActionRow, ...] = (
    ActionRow(
        command("spam_questions"),
        "Form Spam Questions...",
        Tier.WRITE,
        "",
        "The questions of the site's own that QUILL Accessible Forms asks: add one, or change "
        "or remove one, after a preview. The checks and limits are on the site's Properties, "
        "Spam page (Alt+Shift+Enter).",
    ),
    ActionRow(
        command("spam_weeks"),
        "Form Spam by Week",
        Tier.READ,
        "",
        "Week by week, newest first: the questions QUILL Accessible Forms asked, answered, "
        "answered wrongly and let through with Send Anyway.",
    ),
)
"""The site row's QAF spam commands (complete.md WP-C)."""

KEYLESS: dict[str, str] = {
    command("spam_questions"): (
        "A site's own questions are written once and changed now and then, from the site's "
        "context menu (rule 9); the settings beside them are on Alt+Shift+Enter."
    ),
    command("spam_weeks"): (
        "Read now and then, when spam is in question (rule 9); the weekly Watch says each "
        "new week's numbers without being asked."
    ),
}
"""Why each command has no key of its own (rule 8)."""


class SpamConflict(WordPressApiError):
    """The spam settings changed on the site after they were read; nothing was sent."""

    code = "QUILL-WORDPRESS-SPAM-CONFLICT"


# -- which namespace ---------------------------------------------------------------------


def namespace_note(namespace: str) -> str:
    """Which QUILL Accessible Forms the site runs, in a sentence."""
    if namespace == WRITE_NAMESPACE:
        return "This site runs QUILL Accessible Forms (qaf/v1)."
    if namespace == LEGACY_NAMESPACE:
        return (
            "This site runs the older BITS Accessible Forms (baf/v1). Its spam settings can be "
            "read here, but are changed in wp-admin until the site has QUILL Accessible Forms."
        )
    return "This site has no QUILL Accessible Forms."


def write_refusal(namespace: str, state: Mapping[str, Any] | None) -> str:
    """Why the spam settings cannot be changed from QUILL, or "" when they can."""
    if not state:
        return "This site's QUILL Accessible Forms does not show its spam settings to QUILL."
    if namespace != WRITE_NAMESPACE:
        return namespace_note(namespace)
    if "revision" not in state or "can_edit" not in state:
        return (
            "This site's QUILL Accessible Forms is older than the route that changes spam "
            "settings, so they are changed in wp-admin, under Settings, Spam."
        )
    if not state.get("can_edit"):
        return (
            "Changing the spam settings needs the site's Manage Options capability, or QUILL "
            "Accessible Forms' own Manage Settings."
        )
    return ""


# -- the Spam page -------------------------------------------------------------------------


def _part(state: Mapping[str, Any], key: str) -> Mapping[str, Any]:
    found = state.get(key)
    return found if isinstance(found, Mapping) else {}


def _check(setting: str, label: str, help_text: str) -> FieldSpec:
    return FieldSpec(f"{_P}{setting}", label, FieldKind.CHECK, help=help_text)


def spam_fields() -> tuple[FieldSpec, ...]:
    """The QAF settings on the site sheet's Spam page, each with its F1 help."""
    fields: list[FieldSpec] = [
        _check(
            f"provider_{pid}",
            label,
            f"Whether QUILL Accessible Forms runs this check: {label}. A check that doubts a "
            "form holds it as spam for you to look at; none refuses one.",
        )
        for pid, label in PROVIDERS.items()
    ]
    fields += [
        FieldSpec(
            f"{_P}{key}",
            label,
            FieldKind.NUMBER,
            help=f"{label}: a whole number from {low} to {high}.",
        )
        for key, label, low, high in _NUMBERS
    ]
    fields += [
        _check(
            "use_disallowed",
            "Use WordPress's disallowed words",
            "Hold a form whose answers "
            "have a word from Settings, Discussion, Disallowed Comment Keys.",
        ),  # fmt: skip
        _check(
            "use_moderation",
            "Use WordPress's moderation words",
            "Hold a form whose answers have a word from Settings, Discussion, Comment Moderation.",
        ),  # fmt: skip
        FieldSpec(
            f"{_P}challenge_mode",
            "Ask a question",
            FieldKind.CHOICE,
            help="When a visitor is asked a question before the form is sent. A form can "
            "choose its own in its settings.",
            choices=tuple(_MODES.values()),
        ),
    ]
    fields += [
        _check(f"kind_{kind}", label, f"Whether questions of this kind are asked: {label}.")
        for kind, label in _KINDS.items()
    ]
    key, label, low, high = _SEND_ANYWAY
    fields += [
        FieldSpec(
            f"{_P}{key}",
            label,
            FieldKind.NUMBER,
            help=f"From {low} to {high}. Whoever takes Send Anyway is never turned away: the "
            "form is held for you to look at.",
        ),
        FieldSpec(
            _KEY,
            "New OOPSpam key",
            FieldKind.SECRET,
            help="Type a new OOPSpam key to replace the saved one, or leave this empty to keep "
            "it. QUILL never shows, speaks or keeps the saved key; it only says whether one "
            "is saved.",
        ),
        _check(
            "oopspam_key_clear",
            "Remove the saved OOPSpam key",
            "Remove the saved OOPSpam "
            "key when you save. OOPSpam stops running until a new key is saved.",
        ),  # fmt: skip
    ]
    return tuple(fields)


def with_spam_fields(sheet: SheetSpec, page_key: str = "spam") -> SheetSpec:
    """*sheet* with the QAF settings added to its Spam page, after what it already shows."""
    pages = tuple(
        replace(page, fields=page.fields + spam_fields()) if page.key == page_key else page
        for page in sheet.pages
    )
    return replace(sheet, pages=pages)


def spam_values(state: Mapping[str, Any]) -> dict[str, Any]:
    """The Spam page's QAF fields from ``GET qaf/v1/spam``; the key field is always empty."""
    values: dict[str, Any] = {}
    states = {
        str(p.get("id")): bool(p.get("enabled"))
        for p in state.get("providers") or []
        if isinstance(p, Mapping)
    }
    for pid in PROVIDERS:
        values[f"{_P}provider_{pid}"] = states.get(pid, False)
    limits = _part(state, "limits")
    for key, _label, _low, _high in _NUMBERS:
        values[f"{_P}{key}"] = str(limits.get(key, ""))
    values[f"{_P}use_disallowed"] = bool(limits.get("use_disallowed"))
    values[f"{_P}use_moderation"] = bool(limits.get("use_moderation"))
    questions = _part(state, "questions")
    values[f"{_P}challenge_mode"] = _MODES.get(str(questions.get("mode")), _MODES["auto"])
    kinds = _part(questions, "kinds")
    for kind in _KINDS:
        values[f"{_P}kind_{kind}"] = bool(kinds.get(kind))
    values[f"{_P}send_anyway_after"] = str(questions.get("send_anyway_after", ""))
    values[_KEY] = ""
    values[_KEY_CLEAR] = False
    return values


def _whole(label: str, value: Any, low: int, high: int) -> int:
    try:
        number = int(str(value).strip())
    except ValueError:
        number = low - 1
    if not low <= number <= high:
        raise WordPressApiError(f"{label} must be a whole number from {low} to {high}.")
    return number


def spam_body(pending: Sequence[FieldChange]) -> dict[str, Any]:
    """What ``POST qaf/v1/spam`` is sent for the Spam page's changed QAF fields.

    Fields of the page that are not QAF's are left out. A number out of its
    range raises :class:`WordPressApiError` with a sentence saying the range.
    """
    numbers = {
        f"{_P}{k}": (label, low, high, k) for k, label, low, high in (*_NUMBERS, _SEND_ANYWAY)
    }
    modes = {label: mode for mode, label in _MODES.items()}
    body: dict[str, Any] = {}
    for change in pending:
        key, after = change.key, change.after
        if key == _KEY:
            if str(after or "").strip():
                body["oopspam_api_key"] = str(after).strip()
        elif key == _KEY_CLEAR:
            if after:
                body["oopspam_api_key_clear"] = True
        elif key.startswith(f"{_P}provider_"):
            body.setdefault("providers", {})[key[len(f"{_P}provider_") :]] = bool(after)
        elif key.startswith(f"{_P}kind_"):
            body.setdefault("challenge_kinds", {})[key[len(f"{_P}kind_") :]] = bool(after)
        elif key in numbers:
            label, low, high, setting = numbers[key]
            body[setting] = _whole(label, after, low, high)
        elif key == f"{_P}challenge_mode":
            body["challenge_mode"] = modes.get(str(after), str(after))
        elif key in (f"{_P}use_disallowed", f"{_P}use_moderation"):
            body[key[len(_P) :]] = bool(after)
    if "oopspam_api_key" in body and body.get("oopspam_api_key_clear"):
        raise WordPressApiError("Type a new OOPSpam key or remove the saved one, not both.")
    return body


def _on(value: Any) -> str:
    return "on" if value else "off"


def spam_preview(body: Mapping[str, Any], site: str) -> list[str]:
    """One line per change, for the preview. The key itself is never in it."""
    lines: list[str] = []
    for pid, on in (body.get("providers") or {}).items():
        lines.append(f"{PROVIDERS.get(pid, pid)}: turned {_on(on)}.")
    labels = {k: label for k, label, _l, _h in (*_NUMBERS, _SEND_ANYWAY)}
    for key, label in labels.items():
        if key in body:
            lines.append(f"{label}: {body[key]}.")
    for key, label in (("use_disallowed", "WordPress's disallowed words"),
                       ("use_moderation", "WordPress's moderation words")):  # fmt: skip
        if key in body:
            lines.append(f"{label}: {'used' if body[key] else 'not used'}.")
    if "challenge_mode" in body:
        lines.append(
            f"Ask a question: {_MODES.get(body['challenge_mode'], body['challenge_mode'])}."
        )
    for kind, on in (body.get("challenge_kinds") or {}).items():
        lines.append(f"{_KINDS.get(kind, kind)}: {'asked' if on else 'not asked'}.")
    if "oopspam_api_key" in body:
        lines.append("The OOPSpam key: replaced with the new key you typed.")
    if body.get("oopspam_api_key_clear"):
        lines.append("The OOPSpam key: removed. OOPSpam stops running until a new one is saved.")
    lines.append(f"Saved to {site}, then read back to check.")
    return lines


def _state_value(state: Mapping[str, Any], setting: str) -> Any:
    limits = _part(state, "limits")
    questions = _part(state, "questions")
    if setting in limits:
        return limits[setting]
    if setting == "challenge_mode":
        return questions.get("mode")
    if setting == "send_anyway_after":
        return questions.get("send_anyway_after")
    return None


def verify_problems(body: Mapping[str, Any], state: Mapping[str, Any]) -> list[str]:
    """What the site does not hold of *body* after the save (empty when all of it took)."""
    problems: list[str] = []
    providers = {
        str(p.get("id")): bool(p.get("enabled"))
        for p in state.get("providers") or []
        if isinstance(p, Mapping)
    }
    for pid, on in (body.get("providers") or {}).items():
        if providers.get(pid) != bool(on):
            problems.append(f"{PROVIDERS.get(pid, pid)} is still {_on(providers.get(pid))}")
    questions = _part(state, "questions")
    kinds = _part(questions, "kinds")
    for kind, on in (body.get("challenge_kinds") or {}).items():
        if bool(kinds.get(kind)) != bool(on):
            problems.append(f"{_KINDS.get(kind, kind)} did not change")
    for setting in (*(k for k, *_ in _NUMBERS), "send_anyway_after", "challenge_mode",
                    "use_disallowed", "use_moderation"):  # fmt: skip
        if setting in body and _state_value(state, setting) != body[setting]:
            problems.append(f"{setting.replace('_', ' ')} is {_state_value(state, setting)}")
    if "oopspam_api_key" in body and not state.get("oopspam_key_saved"):
        problems.append("the site says no OOPSpam key is saved")
    if body.get("oopspam_api_key_clear") and state.get("oopspam_key_saved"):
        problems.append("the site still has an OOPSpam key saved")
    return problems


def save_spam_settings(
    api: Any, namespace: str, revision: str, body: Mapping[str, Any]
) -> tuple[str, dict[str, Any]]:
    """Read again, send, read back. Returns the sentence to say and the state now saved.

    Raises :class:`SpamConflict` (nothing sent) when the settings changed on
    the site since *revision* was read, by somebody else's hand or QAF's own
    page; and :class:`WordPressApiError` for a refusal, whose sentence never
    repeats the key.
    """
    route = f"{namespace}/spam"
    now = api.get(route)
    if not isinstance(now, Mapping) or str(now.get("revision", "")) != revision:
        raise SpamConflict(
            "The spam settings were changed on the site since they were read, so nothing was "
            "sent. Open the site's Properties again to see them as they are now.",
            status=409,
        )
    try:
        api.post(route, {**body, "if_revision": revision})
    except WordPressApiError as exc:
        if exc.status == 409:
            raise SpamConflict(
                "Somebody changed the spam settings at the same moment, so nothing was saved. "
                "Open the site's Properties again to see them as they are now.",
                status=409,
            ) from None
        raise
    after = api.get(route)
    after = dict(after) if isinstance(after, Mapping) else {}
    problems = verify_problems(body, after)
    count = len(spam_preview(body, "")) - 1
    changes = "1 spam setting" if count == 1 else f"{count} spam settings"
    if problems:
        return (
            f"Saved {changes}, but reading them back, {'; '.join(problems)}. "
            "Check Settings, Spam in wp-admin.",
            after,
        )
    return f"Saved {changes}, and read them back from the site.", after


# -- the question bank ---------------------------------------------------------------------


def read_questions(api: Any, namespace: str) -> list[dict[str, Any]]:
    """The site's own questions: id, question, answers."""
    found = api.get(f"{namespace}/spam/questions")
    rows = found.get("questions") if isinstance(found, Mapping) else None
    return [
        {
            "id": str(q.get("id", "")),
            "question": str(q.get("question", "")),
            "answers": [str(a) for a in q.get("answers") or []],
        }
        for q in rows or []
        if isinstance(q, Mapping)
    ]


def question_line(q: Mapping[str, Any]) -> str:
    answers = list(q.get("answers") or [])
    said = "; ".join(answers)
    return f"{q.get('question', '')} Right answer{'s' if len(answers) != 1 else ''}: {said}."


def parse_answers(text: str) -> list[str]:
    """Answers typed with a semicolon between them; blanks and repeats dropped."""
    seen: list[str] = []
    for part in text.split(";"):
        part = " ".join(part.split())
        if part and part not in seen:
            seen.append(part)
    return seen


def _bank_ids(api: Any, namespace: str) -> set[str]:
    return {q["id"] for q in read_questions(api, namespace)}


def add_question(api: Any, namespace: str, question: str, answers: Sequence[str]) -> str:
    """Add a question and check the site now has it; the sentence to say."""
    made = api.post(f"{namespace}/spam/questions", {"question": question, "answers": list(answers)})
    qid = str(made.get("id", "")) if isinstance(made, Mapping) else ""
    if qid and qid in _bank_ids(api, namespace):
        return f"Added the question. The site asks it now: {question}"
    return "The site took the question, but reading the bank back, it is not there."


def edit_question(
    api: Any, namespace: str, qid: str, *, question: str | None = None,
    answers: Sequence[str] | None = None,
) -> str:  # fmt: skip
    """Change a question and check: the new one is there and the old one is gone."""
    body: dict[str, Any] = {}
    if question is not None:
        body["question"] = question
    if answers is not None:
        body["answers"] = list(answers)
    made = api.post(f"{namespace}/spam/questions/{qid}", body)
    new_id = str(made.get("id", "")) if isinstance(made, Mapping) else ""
    ids = _bank_ids(api, namespace)
    if new_id in ids and (new_id == qid or qid not in ids):
        return "Changed the question, and read it back from the site."
    return "The site took the change, but reading the bank back, it does not show it."


def delete_question(api: Any, namespace: str, qid: str) -> str:
    """Remove a question and check it is gone."""
    api.delete(f"{namespace}/spam/questions/{qid}")
    if qid in _bank_ids(api, namespace):
        return "The site said the question was removed, but it is still in the bank."
    return "Removed the question; the site no longer asks it."


# -- past weeks and the weekly Watch ---------------------------------------------------------


def read_weeks(api: Any, namespace: str, weeks: int = 12) -> list[dict[str, Any]] | None:
    """Past weeks, newest first; None when this QAF has no such route or refuses."""
    try:
        found = api.get(f"{namespace}/spam/weeks", weeks=weeks)
    except WordPressApiError:
        return None
    rows = found.get("weeks") if isinstance(found, Mapping) else None
    if not isinstance(rows, list):
        return None
    return [dict(w) for w in rows if isinstance(w, Mapping)]


def _week_line(week: Mapping[str, Any]) -> str:
    return (
        f"{week.get('week', '')}: {week.get('asked', 0)} asked, {week.get('passed', 0)} answered, "
        f"{week.get('failed', 0)} answered wrongly, {week.get('sent_anyway', 0)} sent anyway."
    )


def weeks_text(weeks: Sequence[Mapping[str, Any]] | None) -> str:
    """Past weeks, one line each, newest first, the current week said so."""
    if weeks is None:
        return (
            "This site's QUILL Accessible Forms keeps only this week's numbers (it is older "
            "than spam/weeks)."
        )
    if not weeks:
        return "No weeks yet."
    lines = [f"This week, {_week_line(weeks[0])}"]
    lines += [_week_line(w) for w in weeks[1:]]
    return "\n".join(lines)


def weekly_watch(
    site: str, api: Any, namespaces: Sequence[str], last_week: str
) -> tuple[str, list[str]]:
    """The Form spam Watch: once a week, last week's numbers against the week before.

    Returns the week to remember and what to say. The first sample says
    nothing; a site without QAF, or with a QAF older than spam/weeks, keeps
    *last_week* and says nothing.
    """
    clean = {n.strip("/") for n in namespaces}
    namespace = next((n for n in (WRITE_NAMESPACE, LEGACY_NAMESPACE) if n in clean), "")
    if not namespace:
        return last_week, []
    weeks = read_weeks(api, namespace, weeks=3)
    if not weeks:
        return last_week, []
    current = str(weeks[0].get("week", ""))
    if not last_week or current == last_week or len(weeks) < 2:
        return current or last_week, []
    ended, before = weeks[1], (weeks[2] if len(weeks) > 2 else {})
    said = f"Form spam questions on {site}, week {_week_line(ended)}"
    asked, earlier = int(ended.get("asked", 0) or 0), int(before.get("asked", 0) or 0)
    if before:
        if asked > earlier:
            said += f" Up from {earlier} asked the week before."
        elif asked < earlier:
            said += f" Down from {earlier} asked the week before."
        else:
            said += " The same as the week before."
    return current, [said]
