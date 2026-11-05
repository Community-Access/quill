"""What the Forms AI commands send, and how their answers are read (wordpress.md 17a.9).

wx-free. Each prompt is built here so a test can read exactly what would leave
the computer, and each command says what it sends before it sends it. Every
answer is a **proposal**: it is checked here (a draft must read as BFL, a hint
must be a real autofill token), and nothing is applied until the person has
read it and said yes.

- **Draft a Form:** a sentence or two in, BFL 1 out.
- **Plain Language:** the questions' labels and help text in, simpler words out.
- **Suggest Autofill Hints and Help Text:** the flagged questions' labels and
  types in, ``autocomplete`` tokens and help out. No answers are ever sent.
- **Summarise Responses:** the answers themselves, after a consent question
  every time that says how many responses would go.
"""

from __future__ import annotations

import json
import re
from typing import Any

from quill.core.forms import model as M

#: Longest text sent in one request, in characters (about 15,000 words).
MAX_SEND = 90_000

#: The HTML autocomplete tokens a field may carry (the WHATWG list).
AUTOFILL_TOKENS: frozenset[str] = frozenset(
    """name honorific-prefix given-name additional-name family-name honorific-suffix nickname
    username new-password current-password one-time-code organization-title organization
    street-address address-line1 address-line2 address-line3 address-level4 address-level3
    address-level2 address-level1 country country-name postal-code cc-name cc-given-name
    cc-additional-name cc-family-name cc-number cc-exp cc-exp-month cc-exp-year cc-csc cc-type
    transaction-currency transaction-amount language bday bday-day bday-month bday-year sex url
    photo tel tel-country-code tel-national tel-area-code tel-local tel-extension email impp
    off on""".split()
)
#: Card tokens: QUILL never suggests them. Payment stays in WordPress (17a.11).
_PAYMENT = frozenset(t for t in AUTOFILL_TOKENS if t.startswith(("cc-", "transaction-")))

#: Field types that can take a hint, and the ones that ask for a person's details.
HINTABLE = frozenset("text email phone name address number date website".split())
_FORMAT_RULES = ("min", "max", "min_length", "max_length", "pattern")

_BFL_GUIDE = """BFL 1 is a plain-text form language. Rules:
- The first line is: bfl 1
- The second line is: form "Title of the form"
- Each question is one line: TYPE #id "Question"
  TYPE is one of: text, textarea, email, phone, number, date, time, name, address,
  website, select, radio, checkbox, consent, rating, likert.
  The id is lower case letters, digits and underscores, unique in the form.
- Settings for a question go on the lines under it, indented two spaces:
  @required, @description "help text", @placeholder "example",
  @autocomplete "email" (an HTML autocomplete token).
- Choices for select, radio and checkbox go under the question, indented two
  spaces, one per line: + Choice label
- Sections and pages: section #id "Heading" and page #id "Title", with their
  questions indented two spaces under them.
Example:
bfl 1
form "Spring fair"

text #name "Your name"
  @required
  @autocomplete "name"
email #email "Email address"
  @required
  @autocomplete "email"
radio #heard "How did you hear about us?"
  + A friend
  + Somewhere else
"""


def draft_prompt(description: str) -> str:
    return (
        "Write an accessible web form in BFL from this description.\n\n"
        + _BFL_GUIDE
        + "\nWrite every question as a plain question a person can answer, with a visible "
        "label. Mark only what is truly needed as required. Give name, email, phone and "
        "address questions their autocomplete hint. Answer with the BFL only, nothing "
        "before or after it.\n\nDescription:\n" + description.strip()[:MAX_SEND]
    )


def extract_bfl(answer: str) -> str:
    """The BFL in an answer, without a code fence or a sentence around it."""
    text = answer.strip()
    fenced = re.search(r"```[a-zA-Z]*\n(.*?)```", text, re.DOTALL)
    if fenced:
        text = fenced.group(1)
    start = re.search(r"^\s*bfl\s+1\s*$", text, re.MULTILINE)
    if start:
        text = text[start.start() :]
    return text.strip() + "\n"


# --------------------------------------------------------------------------- #
# Plain Language


def wording(model: M.Model) -> dict[str, dict[str, str]]:
    """Each question's label and help, by id: everything Plain Language sends."""
    out: dict[str, dict[str, str]] = {}
    for item in M.iter_items(model):
        if not item.get("id") or not (item.get("label") or item.get("help")):
            continue
        entry = {"label": str(item.get("label") or "")}
        if item.get("help"):
            entry["help"] = str(item["help"])
        out[str(item["id"])] = entry
    return out


def plain_language_prompt(model: M.Model) -> str:
    return (
        "Rewrite these form questions and their help text in plain language: short, "
        "everyday words, one idea at a time, addressed to the person filling it in. Keep "
        "each question's meaning exactly; do not add or remove questions. Answer with JSON "
        'only, in the same shape: {"id": {"label": "...", "help": "..."}}. Leave out any '
        "question that is already plain.\n\n" + json.dumps(wording(model), ensure_ascii=False)
    )


def parse_json_object(answer: str) -> dict[str, Any]:
    """The first JSON object in an answer, or an empty one."""
    text = answer.strip()
    fenced = re.search(r"```[a-zA-Z]*\n(.*?)```", text, re.DOTALL)
    if fenced:
        text = fenced.group(1)
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end <= start:
        return {}
    try:
        found = json.loads(text[start : end + 1])
    except ValueError:
        return {}
    return found if isinstance(found, dict) else {}


def plain_changes(model: M.Model, answer: str) -> list[tuple[str, str, str, str]]:
    """``(id, part, before, after)`` for each label or help the AI made plainer."""
    proposed = parse_json_object(answer)
    out: list[tuple[str, str, str, str]] = []
    for item_id, before in wording(model).items():
        after = proposed.get(item_id)
        if not isinstance(after, dict):
            continue
        for part in ("label", "help"):
            new = " ".join(str(after.get(part) or "").split())
            old = before.get(part, "")
            if new and old and new != old:
                out.append((item_id, part, old, new))
    return out


# --------------------------------------------------------------------------- #
# Suggest Autofill Hints and Help Text


def needs_help(model: M.Model) -> dict[str, dict[str, str]]:
    """The questions Check This Form flags here: no hint on a detail, or a rule with no help."""
    out: dict[str, dict[str, str]] = {}
    for item_id, item in M.fields(model).items():
        kind = str(item.get("type", ""))
        props = item.get("props") or {}
        hinted = props.get("autocomplete") or (item.get("attributes") or {}).get("autocomplete")
        validation = item.get("validation") or {}
        rule = item.get("mask") or any(k in validation for k in _FORMAT_RULES)
        wants: list[str] = []
        if kind in HINTABLE and not hinted:
            wants.append("autocomplete")
        if rule and not item.get("help"):
            wants.append("help")
        if wants:
            entry = {"label": str(item.get("label") or ""), "type": kind, "wants": ",".join(wants)}
            if rule:
                entry["rule"] = json.dumps({k: validation[k] for k in validation} or item["mask"])
            out[item_id] = entry
    return out


def autofill_prompt(model: M.Model) -> str:
    return (
        "For each form question below, suggest what it wants. 'autocomplete' wants the HTML "
        "autocomplete token that lets a browser fill it in (for example name, email, tel, "
        'street-address, postal-code), or "off" when no token fits. "help" wants one short '
        "sentence telling the person what format is expected. Never suggest payment card "
        'tokens. Answer with JSON only: {"id": {"autocomplete": "...", "help": "..."}}.\n\n'
        + json.dumps(needs_help(model), ensure_ascii=False)
    )


def autofill_changes(model: M.Model, answer: str) -> list[tuple[str, str, str]]:
    """``(id, "autocomplete" or "help", value)`` for each usable suggestion."""
    proposed = parse_json_object(answer)
    out: list[tuple[str, str, str]] = []
    for item_id, wanted in needs_help(model).items():
        found = proposed.get(item_id)
        if not isinstance(found, dict):
            continue
        token = str(found.get("autocomplete") or "").strip().lower()
        if (
            "autocomplete" in wanted["wants"]
            and token in AUTOFILL_TOKENS
            and token not in _PAYMENT
            and token not in ("off", "on")
        ):
            out.append((item_id, "autocomplete", token))
        help_text = " ".join(str(found.get("help") or "").split())
        if "help" in wanted["wants"] and help_text:
            out.append((item_id, "help", help_text))
    return out


# --------------------------------------------------------------------------- #
# Summarise Responses


def summary_prompt(form_title: str, rows: list[list[tuple[str, str]]]) -> tuple[str, int]:
    """The prompt, and how many responses fit in it (the rest are left out, and said)."""
    head = (
        f"These are the responses to a form called {form_title!r}. Write a short summary for "
        "the form's owner: how many responded, the main patterns in each question's answers, "
        "and anything unusual. Do not quote names, email addresses, phone numbers or street "
        "addresses.\n\n"
    )
    body: list[str] = []
    used = len(head)
    sent = 0
    for number, pairs in enumerate(rows, 1):
        block = f"Response {number}\n" + "\n".join(f"{q}: {a}" for q, a in pairs) + "\n\n"
        if used + len(block) > MAX_SEND:
            break
        body.append(block)
        used += len(block)
        sent += 1
    return head + "".join(body), sent


__all__ = [
    "AUTOFILL_TOKENS",
    "MAX_SEND",
    "autofill_changes",
    "autofill_prompt",
    "draft_prompt",
    "extract_bfl",
    "needs_help",
    "parse_json_object",
    "plain_changes",
    "plain_language_prompt",
    "summary_prompt",
    "wording",
]
