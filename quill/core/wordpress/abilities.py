"""Abilities: actions a site offers AI, opt-in one by one (wordpress.md 9.15).

WordPress 6.9 lets a site describe actions it offers to AI agents
(``wp-abilities/v1``). QUILL follows the vendor tools rule (code.md decision
4): QUILL owns the tools, and a site's ability is one of them only when the
person says so.

* Every ability is **listed by name** and **off until checked**, kept per
  site on this computer (:class:`AbilityChoices`).
* An ability that is on is still **approved per use**: the person is asked
  every time, with the ability's name and exactly what it will be given.
* What ran is **shown in the answer** (:func:`answer_with_uses`).

Ask the Site runs a two-step turn through the editor's chosen AI, with no
vendor tool calling at all: QUILL describes the abilities that are on and
asks for either an answer or one ``RUN`` line (:func:`plan_prompt`,
:func:`parse_plan`); when it asks to run one, QUILL asks the person, runs it
on the site, and sends the result back for the answer (:func:`answer_prompt`).

Wx-free; every request goes through
:class:`~quill.core.wordpress.api.WordPressApi`.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from quill.core.storage import read_json, write_json_atomic
from quill.core.wordpress.api import WordPressApi
from quill.core.wordpress.site import plain_text

NAMESPACE = "wp-abilities/v1"
#: How much of an ability's answer goes back to the AI.
RESULT_LIMIT = 6000


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


@dataclass(frozen=True)
class Ability:
    name: str
    label: str
    description: str
    category: str = ""
    readonly: bool = False
    destructive: bool = False
    input_schema: dict[str, Any] = field(default_factory=dict)
    idempotent: bool = False

    @property
    def run_method(self) -> str:
        """The Abilities REST method implied by WordPress's annotations."""
        if self.readonly:
            return "GET"
        if self.destructive and self.idempotent:
            return "DELETE"
        return "POST"

    def spoken(self, on: bool) -> str:
        kind = "changes nothing" if self.readonly else "can change the site"
        if self.destructive:
            kind = "can delete or overwrite"
        state = "on" if on else "off"
        return f"{self.label}, {state}, {kind}: {self.description or self.name}"

    def details(self) -> str:
        inputs = ", ".join(sorted((self.input_schema.get("properties") or {}).keys()))
        return (
            f"Name: {self.name}\n"
            f"Category: {self.category or 'none'}\n"
            f"Takes: {inputs or 'nothing'}\n"
            f"{self.description}"
        )


def ability_from(raw: Any) -> Ability | None:
    if not isinstance(raw, dict) or not raw.get("name"):
        return None
    meta = _as_dict(raw.get("meta"))
    notes = _as_dict(meta.get("annotations"))
    schema = _as_dict(raw.get("input_schema"))
    return Ability(
        name=str(raw["name"]),
        label=plain_text(str(raw.get("label") or raw["name"])),
        description=plain_text(str(raw.get("description") or "")),
        category=str(raw.get("category") or ""),
        readonly=bool(notes.get("readonly", False)),
        destructive=bool(notes.get("destructive", False)),
        input_schema=dict(schema or {}),
        idempotent=bool(notes.get("idempotent", False)),
    )


def list_abilities(api: WordPressApi) -> list[Ability]:
    found = [ability_from(r) for r in api.iter_collection(f"{NAMESPACE}/abilities")]
    return sorted((a for a in found if a is not None), key=lambda a: a.label.casefold())


def run_ability(api: WordPressApi, ability: Ability, given: dict[str, Any]) -> Any:
    """Run one ability using its annotated method and bracketed query input."""
    route = f"{NAMESPACE}/abilities/{ability.name}/run"
    method = ability.run_method
    if method in ("GET", "DELETE"):
        params: dict[str, Any] = {}

        def flatten(value: Any, key: str) -> None:
            if isinstance(value, Mapping):
                for name, child in value.items():
                    flatten(child, f"{key}[{name}]")
            elif isinstance(value, (list, tuple)):
                for index, child in enumerate(value):
                    flatten(child, f"{key}[{index}]")
            else:
                params[key] = value

        for name, value in given.items():
            flatten(value, f"input[{name}]")
        return api.request(method, route, params=params).payload
    return api.post(route, {"input": given} if given else {})


# --------------------------------------------------------------------------- #
# Which are on, per site, on this computer


class AbilityChoices:
    """The abilities a person turned on for one site. Everything else is off."""

    def __init__(self, root: Path, site_id: str) -> None:
        safe = re.sub(r"[^A-Za-z0-9_-]", "_", site_id) or "site"
        self.path = root / "abilities" / f"{safe}.json"

    def on(self) -> set[str]:
        raw = read_json(self.path, default={})
        names = raw.get("on", []) if isinstance(raw, dict) else []
        return {str(n) for n in names}

    def set(self, name: str, on: bool) -> None:
        names = self.on()
        if on:
            names.add(name)
        else:
            names.discard(name)
        write_json_atomic(self.path, {"on": sorted(names)})


# --------------------------------------------------------------------------- #
# Ask the Site: the two-step turn


def plan_prompt(site_name: str, question: str, abilities: list[Ability]) -> str:
    lines = [
        f"You are helping someone with their WordPress site, {site_name}.",
        "The person may let you use these abilities of the site. Each runs only if they "
        "approve it.",
    ]
    for a in abilities:
        props = sorted((a.input_schema.get("properties") or {}).keys())
        takes = f" Input fields: {', '.join(props)}." if props else " It takes no input."
        lines.append(f"- {a.name}: {a.label}. {a.description}{takes}")
    lines += [
        "If one ability would help you answer, reply with exactly one line and nothing else:",
        "RUN <ability name> <input as a JSON object>",
        "Otherwise answer the question directly, in plain words.",
        "",
        f"Question: {question.strip()}",
    ]
    return "\n".join(lines)


_RUN = re.compile(r"^\s*RUN\s+(\S+)\s*(\{.*\})?\s*$", re.S)


def parse_plan(answer: str, abilities: list[Ability]) -> tuple[Ability, dict[str, Any]] | None:
    """The ability the AI asked to run and its input, or None for a plain answer.

    Only an ability that is on can come back; a name the AI made up is a plain
    answer, never a run.
    """
    match = _RUN.match(answer.strip())
    if match is None:
        return None
    by_name = {a.name: a for a in abilities}
    ability = by_name.get(match.group(1))
    if ability is None:
        return None
    given: dict[str, Any] = {}
    if match.group(2):
        try:
            value = json.loads(match.group(2))
        except ValueError:
            return None
        if not isinstance(value, dict):
            return None
        given = value
    return ability, given


def approval_message(site_name: str, ability: Ability, given: dict[str, Any]) -> str:
    what = json.dumps(given, ensure_ascii=False) if given else "nothing"
    effect = (
        "It only reads."
        if ability.readonly
        else "It can change the site."
        if not ability.destructive
        else "It can delete or overwrite things on the site."
    )
    return (
        f"The AI asks to run {ability.label} ({ability.name}) on {site_name}, given {what}. "
        f"{effect} Run it this once?"
    )


def result_text(result: Any) -> str:
    text = result if isinstance(result, str) else json.dumps(result, ensure_ascii=False)
    return text if len(text) <= RESULT_LIMIT else text[:RESULT_LIMIT] + " ... (cut short)"


def answer_prompt(
    site_name: str, question: str, ability: Ability, given: dict[str, Any], result: Any
) -> str:
    return (
        f"You asked to run the ability {ability.name} on {site_name} with "
        f"{json.dumps(given, ensure_ascii=False)}. It answered:\n{result_text(result)}\n\n"
        "Now answer the person's question in plain words. Do not ask to run anything else.\n\n"
        f"Question: {question.strip()}"
    )


def answer_with_uses(
    answer: str, site_name: str, uses: list[tuple[Ability, dict[str, Any]]]
) -> str:
    """The answer, then what ran on the site to get it."""
    if not uses:
        return f"{answer.strip()}\n\nNo ability of {site_name} was used."
    used = "; ".join(
        f"{a.label} ({a.name}), given {json.dumps(g, ensure_ascii=False) if g else 'nothing'}"
        for a, g in uses
    )
    return f"{answer.strip()}\n\nUsed on {site_name}: {used}."
