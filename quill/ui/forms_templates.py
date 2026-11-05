"""The New Form templates (wordpress.md 17a.4.1), as form models.

wx-free. Each template is the form model QAF stores (plain dicts), so New
Form writes it as canonical BFL through the core's own writer and every
template is a form the core can read back. They are short on purpose: a
contact form is three questions, and a template is a start, not a finished
form. Every person-detail question carries its autofill hint, because Check
This Form asks for one (17a.5).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

Model = dict[str, Any]


def _f(kind: str, fid: str, label: str, **extra: Any) -> dict[str, Any]:
    item: dict[str, Any] = {"id": fid, "type": kind, "label": label}
    item.update(extra)
    return item


def _choices(*labels: str) -> list[dict[str, str]]:
    return [{"value": _value(label), "label": label} for label in labels]


def _value(label: str) -> str:
    out = "".join(c if c.isalnum() else "-" for c in label.lower())
    while "--" in out:
        out = out.replace("--", "-")
    return out.strip("-")


def _name() -> dict[str, Any]:
    return _f("text", "name", "Your name", required=True, props={"autocomplete": "name"})


def _email(help_text: str = "We only use this to reply to you.") -> dict[str, Any]:
    return _f(
        "email", "email", "Email address", required=True, help=help_text,
        props={"autocomplete": "email"},
    )  # fmt: skip


def _phone() -> dict[str, Any]:
    return _f("phone", "phone", "Phone number", props={"autocomplete": "tel"})


def _blank() -> list[dict[str, Any]]:
    return [_f("text", "question_1", "First question")]


def _contact() -> list[dict[str, Any]]:
    return [_name(), _email(), _f("textarea", "message", "Your message", required=True)]


def _event() -> list[dict[str, Any]]:
    return [
        _name(),
        _email("We send your confirmation here."),
        _f("number", "guests", "How many people are coming, including you?", required=True,
           default=1, validation={"min": 1, "max": 10},
           help="A number from 1 to 10."),
        _f("radio", "access", "Do you need any access arrangements?",
           choices=_choices("No", "Yes")),
        _f("textarea", "access_details", "Tell us what you need", when='#access is "yes"'),
    ]  # fmt: skip


def _membership() -> list[dict[str, Any]]:
    return [
        _name(),
        _email(),
        _phone(),
        _f("address", "address", "Postal address", props={"autocomplete": "street-address"}),
        _f("radio", "level", "Membership", required=True,
           choices=_choices("Individual", "Household", "Student")),
        _f("radio", "format", "How would you like to receive our newsletter?",
           choices=_choices("Email", "Large print", "Braille", "Audio")),
    ]  # fmt: skip


def _survey() -> list[dict[str, Any]]:
    return [
        _f("rating", "overall", "Overall, how would you rate us?", required=True),
        _f("radio", "again", "Would you use us again?", choices=_choices("Yes", "No", "Not sure")),
        _f("textarea", "better", "What could we do better?"),
    ]  # fmt: skip


def _accessibility() -> list[dict[str, Any]]:
    return [
        _f("website", "page", "Which page or service is this about?",
           help="The web address, or a few words that describe it."),
        _f("textarea", "problem", "What happened?", required=True),
        _f("checkbox", "technology", "What were you using?",
           choices=_choices("Screen reader", "Magnifier", "Voice control", "Keyboard only",
                            "Something else")),
        _f("radio", "reply", "May we contact you about this?", choices=_choices("Yes", "No")),
        _f("email", "email", "Email address", when='#reply is "yes"',
           props={"autocomplete": "email"}),
    ]  # fmt: skip


def _volunteer() -> list[dict[str, Any]]:
    return [
        _name(),
        _email(),
        _phone(),
        _f("checkbox", "days", "Which days can you help?",
           choices=_choices("Monday", "Tuesday", "Wednesday", "Thursday", "Friday",
                            "Saturday", "Sunday")),
        _f("textarea", "skills", "Anything you would especially like to do?"),
    ]  # fmt: skip


@dataclass(frozen=True)
class Template:
    id: str
    name: str
    description: str
    build: Any  # () -> list of items

    def model(self, title: str) -> Model:
        """A new form with this template's questions, called *title*."""
        model: Model = {
            "version": 1,
            "title": title.strip() or self.name,
            "pages": [{"id": "page_1", "items": self.build()}],
        }
        return model


TEMPLATES: tuple[Template, ...] = (
    Template("blank", "Blank", "One question to start from.", _blank),
    Template("contact", "Contact form", "Name, email address and a message.", _contact),
    Template(
        "event",
        "Event registration",
        "Name, email, how many are coming, and access arrangements, asked only when needed.",
        _event,
    ),
    Template(
        "membership",
        "Membership renewal",
        "Contact details, membership level, and how they would like the newsletter.",
        _membership,
    ),
    Template("survey", "Survey", "A rating, a yes or no, and room to say more.", _survey),
    Template(
        "accessibility",
        "Accessibility feedback",
        "Where the problem was, what happened, what they use, and whether to reply.",
        _accessibility,
    ),
    Template(
        "volunteer",
        "Volunteer sign-up",
        "Contact details, the days they can help, and what they would like to do.",
        _volunteer,
    ),
)
