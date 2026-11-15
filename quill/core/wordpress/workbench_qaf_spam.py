"""QUILL Accessible Forms' spam handling, as the Workbench reads and uses it (complete.md WP-C).

QAF holds what its checks doubt and never drops it; the Workbench's part is to
say why an entry was held, to mark it through QAF's own routes so the spam
providers learn and a released entry's notifications go out, and to show the
site's spam settings on the Spam page of the site's Properties:

- ``POST qaf/v1/entries/{id}/spam`` and ``.../not-spam``: the entry's status
  changes, every running provider is told (Akismet and OOPSpam learn) and an
  entry held when it arrived is submitted at last, once. A site whose QAF is
  older than those routes answers 404, and the entry's ``status`` is set
  instead, which moves it but tells nobody (:func:`mark_entry`).
- ``GET qaf/v1/spam``: which checks are on, each provider's state, the
  limits, when a question is asked, how many questions are the site's own,
  and this week's question numbers. No key is ever in the reply.

Changing them is :mod:`quill.core.wordpress.workbench_qaf_spam_edit`, over
the routes QAF added for it (``POST qaf/v1/spam``, ``spam/questions``,
``spam/weeks``); a site still on ``baf/v1`` is read only. What QAF still does
not expose is the blocklist itself: it is WordPress's own Disallowed Comment
Keys, which the REST API does not show, so it is changed in wp-admin.
Wx-free.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any

from quill.core.wordpress.api import WordPressApiError

if TYPE_CHECKING:
    from quill.core.wordpress.workbench_load import SiteContext
    from quill.core.wordpress.workbench_rows import WbRow

__all__ = [
    "form_spam_text",
    "held_reason",
    "mark_entry",
    "read_spam_state",
    "spam_namespace",
    "spam_state_text",
]

_MODES = {
    "auto": "only when the checks are unsure",
    "always": "on every form",
    "never": "never",
}
_KINDS = {
    "sense": "common-sense questions",
    "instruction": "follow-an-instruction questions",
    "choice": "pick-the-answer questions",
    "order": "put-in-order questions",
    "maths": "sums",
}


def held_reason(raw: Mapping[str, Any]) -> str:
    """Why QAF held an entry, as one sentence ("" when it says nothing)."""
    spam = raw.get("spam")
    if not isinstance(spam, Mapping):
        return ""
    reason = str(spam.get("reason") or "").strip().rstrip(".")
    check = str(spam.get("check") or "").strip()
    if not reason and not check:
        return ""
    said = f"Held because: {reason or 'a check doubted it'}"
    if check and check != "person":
        said += f" ({check} check"
        score, top = spam.get("score"), spam.get("score_max")
        if score is not None:
            said += f", score {score:g}" if isinstance(score, (int, float)) else f", score {score}"
            if top is not None:
                said += f" of {top:g}" if isinstance(top, (int, float)) else f" of {top}"
        said += ")"
    return said + "."


def mark_entry(api: Any, row: WbRow, spam: bool) -> list[str]:
    """Mark one QAF entry Spam or Not Spam; returns the providers QAF told (may be empty)."""
    route = f"{row.route}/{'spam' if spam else 'not-spam'}"
    try:
        answer = api.post(route, {})
    except WordPressApiError as exc:
        if exc.status not in (404, 405):
            raise
        api.post(row.route, {"status": "spam" if spam else "active"})  # QAF before 13a.5
        return []
    told = answer.get("told") if isinstance(answer, Mapping) else None
    return [str(t) for t in told] if isinstance(told, list) else []


def read_spam_state(ctx: SiteContext, namespace: str) -> dict[str, Any] | None:
    """``GET {namespace}/spam``, or None when this QAF has no such route or refuses."""
    try:
        state = ctx.api.get(f"{namespace}/spam")
    except WordPressApiError:
        return None
    return dict(state) if isinstance(state, Mapping) else None


def _provider_line(item: Mapping[str, Any]) -> str:
    label = str(item.get("label") or item.get("id") or "A check")
    if not item.get("enabled"):
        state = "off"
    elif item.get("runs"):
        state = "on and running"
    elif not item.get("available"):
        state = "on, but cannot run"
    else:
        state = "on, not running"
    line = f"{label}: {state}"
    if item.get("sends_content") and item.get("enabled"):
        line += "; sends what visitors type to its service"
    note = str(item.get("note") or "").strip()
    return line + (f". {note.rstrip('.')}." if note else ".")


def spam_state_text(state: Mapping[str, Any] | None) -> str:
    """The Spam page's account of QAF's checks, one line each."""
    if not state:
        return (
            "This site's QUILL Accessible Forms does not show its spam settings to QUILL "
            "(qaf/v1/spam needs QAF with Settings > Spam, and permission to see entries)."
        )
    lines = [_provider_line(p) for p in state.get("providers") or [] if isinstance(p, Mapping)]
    limits = state.get("limits") if isinstance(state.get("limits"), Mapping) else {}
    if limits:
        lines.append(
            f"Limits: at least {limits.get('min_seconds', '?')} seconds on the page; at most "
            f"{limits.get('max_links', '?')} links; OOPSpam holds at a score of "
            f"{limits.get('oopspam_threshold', '?')}; proof of work up to "
            f"{limits.get('altcha_max_number', '?')}. WordPress's disallowed words "
            f"{'are' if limits.get('use_disallowed') else 'are not'} used, and its moderation "
            f"words {'are' if limits.get('use_moderation') else 'are not'}."
        )
    questions = state.get("questions") if isinstance(state.get("questions"), Mapping) else {}
    if questions:
        kinds = questions.get("kinds")
        kinds = kinds if isinstance(kinds, Mapping) else {}
        on = [_KINDS.get(str(k), str(k)) for k, v in kinds.items() if v]
        mode = _MODES.get(str(questions.get("mode")), str(questions.get("mode") or "not said"))
        per_form = questions.get("form_modes")
        lines.append(
            f"Questions are asked {mode}"
            + (f", using {', '.join(on)}" if on else "")
            + f"; {questions.get('site_questions', 0)} are the site's own; Send Anyway is "
            f"offered after {questions.get('send_anyway_after', '?')} wrong answers."
            + (f" {len(per_form)} forms choose their own." if per_form else "")
        )
        week = questions.get("this_week")
        if isinstance(week, Mapping):
            lines.append(
                f"This week ({week.get('week', '')}): {week.get('asked', 0)} asked, "
                f"{week.get('passed', 0)} answered, {week.get('failed', 0)} answered wrongly, "
                f"{week.get('sent_anyway', 0)} sent anyway."
            )
    if "oopspam_key_saved" in state:
        saved = "is saved" if state.get("oopspam_key_saved") else "is not saved"
        lines.append(f"The OOPSpam key {saved}; QAF never shows it.")
    if "revision" in state:
        lines.append(
            "Change them on this page, below"
            + ("" if state.get("can_edit") else ", with the site's Manage Options capability")
            + "; the site's own questions are Form Spam Questions on the site's context menu."
        )
    else:
        lines.append(
            "These are changed in wp-admin, under Settings, Spam: this QAF is older than the "
            "route that changes them."
        )
    return "\n".join(lines)


def spam_namespace(ctx: SiteContext) -> str:
    """``qaf/v1``, else ``baf/v1``, whichever the site lists; else ``""``."""
    from quill.core.forms import qaf_site

    info = ctx.info
    if info is not None:
        return next((ns for ns in qaf_site.NAMESPACES if info.supports(ns)), "")
    return qaf_site.site_namespace(ctx.api) or ""


def form_spam_text(ctx: SiteContext) -> str:
    """The Spam page's QAF lines for this site, read now (QAF's namespace, then ``baf/v1``)."""
    namespace = spam_namespace(ctx)
    if not namespace:
        return "This site has no QUILL Accessible Forms, so there are no form spam checks to show."
    return spam_state_text(read_spam_state(ctx, namespace))
