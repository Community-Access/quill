"""Fill It In Yourself, without the window: pages, answers, rules (wordpress.md 17a.6).

wx-free. A :class:`FillSession` is one run through a form, in one of its
languages: which page you are on, what you have answered, and what the core's
rules evaluator (:func:`quill.core.forms.rules.evaluate_form`) says that
shows, hides, works out and still needs. The window in
:mod:`quill.ui.forms_fill_window` only draws it, so everything that decides
what a person hears is tested here without a display.

Submit sends nothing. It says what would have been sent, as question and
answer pairs, and what the rules worked out.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from quill.core.forms import model as M
from quill.ui import forms_doc as fd

#: Types the window cannot offer as a control; it says so instead (17a.6).
NOT_HERE: frozenset[str] = frozenset({
    "fileupload", "signature", "map", "social", "captcha", "payment", "matrix", "likert",
    "ranking", "repeater", "appointment", "table", "image_choice", "product", "coupon",
})  # fmt: skip
#: Types that are never a question: nothing to answer, nothing to say.
NOT_QUESTIONS: frozenset[str] = frozenset({"hidden", "submit", "save", "progress", "summary"})
#: Types whose answer is worked out, not typed.
WORKED_OUT: frozenset[str] = frozenset({"calculation", "total", "price"})
#: Several answers at once.
MANY: frozenset[str] = frozenset({"checkbox", "multiselect"})
#: One answer from a list.
ONE: frozenset[str] = frozenset({"radio", "select", "rating", "nps", "quiz"})
#: One check box.
YES_NO: frozenset[str] = frozenset({"consent", "toggle"})


def localize(model: fd.Model, language: str) -> fd.Model:
    """A copy of the form in *language*; the core's translation (forms.translate)."""
    from quill.core.forms import translate

    return translate.localize(model, language)


def choices_of(item: fd.Item, model: fd.Model | None = None) -> list[tuple[str, str]]:
    """``(value, label)`` for each choice: its own, the form's library, BAF's, or a scale."""
    from quill.core.forms import libraries

    return [(str(v), str(label)) for v, label in libraries.choices_for(item, model)]


@dataclass
class Change:
    """What one answer changed, in the words to say."""

    appeared: list[str] = field(default_factory=list)
    disappeared: list[str] = field(default_factory=list)

    def sentence(self) -> str:
        parts = []
        if self.appeared:
            parts.append(
                _listed(self.appeared) + (" appears." if len(self.appeared) == 1 else " appear.")
            )
        if self.disappeared:
            parts.append(
                _listed(self.disappeared)
                + (" is hidden." if len(self.disappeared) == 1 else " are hidden.")
            )
        return " ".join(parts)


def _listed(names: list[str]) -> str:
    return names[0] if len(names) == 1 else ", ".join(names[:-1]) + " and " + names[-1]


class FillSession:
    def __init__(self, model: fd.Model, language: str | None = None) -> None:
        self.source = model
        self.language = language or str(model.get("language") or "en")
        self.model = localize(model, self.language)
        self.answers: dict[str, Any] = self._starting_answers()
        self.page = 0
        self.state = self._evaluate()
        self.page = self._first_shown(0, 1)

    # -- languages ---------------------------------------------------------- #

    def languages(self) -> list[str]:
        own = str(self.source.get("language") or "en")
        return [own] + sorted(lang for lang in self.source.get("translations") or {} if lang != own)

    def set_language(self, language: str) -> None:
        self.language = language
        self.model = localize(self.source, language)
        self.state = self._evaluate()

    # -- what is on screen -------------------------------------------------- #

    def pages(self) -> list[fd.Item]:
        return list(self.model.get("pages") or [])

    def shown_pages(self) -> list[int]:
        return [i for i, p in enumerate(self.pages()) if p.get("id") not in self.state.hidden]

    def page_items(self) -> list[tuple[int, fd.Item]]:
        """``(depth, item)`` for everything on this page, shown or not, in order."""
        pages = self.pages()
        if not pages:
            return []
        return [
            (depth, item)
            for depth, item in fd._walk(pages[self.page].get("items") or [], 0)
            if item.get("type") not in NOT_QUESTIONS
        ]

    def is_shown(self, item: fd.Item) -> bool:
        return str(item.get("id")) not in self.state.hidden

    def heading(self) -> str:
        page = self.pages()[self.page] if self.pages() else {}
        shown = self.shown_pages()
        number = shown.index(self.page) + 1 if self.page in shown else 1
        title = f": {page['title']}" if page.get("title") else ""
        return f"Page {number} of {max(1, len(shown))}{title}"

    def worked_out(self, item_id: str) -> str:
        value = self.state.calculated.get(item_id, self.state.values.get(item_id))
        return "" if value is None else str(value)

    def back_possible(self) -> bool:
        return self._first_shown(self.page - 1, -1) != -1

    def is_last(self) -> bool:
        return self._first_shown(self.page + 1, 1) == -1 or not self.shown_pages()

    # -- answering ---------------------------------------------------------- #

    def answer(self, item_id: str, value: Any) -> Change:
        """Record an answer; say what it showed or hid on this page."""
        before = {str(i.get("id")) for _d, i in self.page_items() if self.is_shown(i)}
        if value in ("", [], None):
            self.answers.pop(item_id, None)
        else:
            self.answers[item_id] = value
        self.state = self._evaluate()
        after = {str(i.get("id")) for _d, i in self.page_items() if self.is_shown(i)}
        names = {str(i.get("id")): fd.name_of(i) for _d, i in self.page_items()}
        return Change(
            [names[i] for i in names if i in after - before],
            [names[i] for i in names if i in before - after],
        )

    def missing_here(self) -> list[str]:
        """The required questions on this page that still need an answer, by name."""
        here = {str(i.get("id")): fd.name_of(i) for _d, i in self.page_items()}
        return [here[i] for i in self.state.missing_required if i in here]

    def next(self) -> bool:
        """Go forward, following a skip rule; False on the last page."""
        target = self.state.skip_to
        pages = self.pages()
        if target:
            index = next((i for i, p in enumerate(pages) if p.get("id") == target), -1)
            if index > self.page:
                self.page = index
                return True
        found = self._first_shown(self.page + 1, 1)
        if found == -1:
            return False
        self.page = found
        return True

    def back(self) -> bool:
        found = self._first_shown(self.page - 1, -1)
        if found == -1:
            return False
        self.page = found
        return True

    # -- submitting --------------------------------------------------------- #

    def summary(self) -> str:
        """What would have been sent, and what the rules worked out. Nothing is sent."""
        lines = ["Nothing was sent. This is what the form would send:", ""]
        for page_number in self.shown_pages():
            for _depth, item in fd._walk(self.pages()[page_number].get("items") or [], 0):
                if not M.is_field_type(item.get("type")) or not self.is_shown(item):
                    continue
                if item.get("type") in NOT_QUESTIONS:
                    continue
                lines.append(f"{fd.name_of(item)}: {self._spoken(item)}")
        missing = [
            fd.name_of(M.find(self.model, i) or {"id": i}) for i in self.state.missing_required
        ]
        if missing:
            lines += ["", "Still needs an answer: " + ", ".join(missing) + "."]
        if self.state.score:
            lines += ["", f"Score: {self.state.score}"]
        if self.state.outcome:
            lines += ["", str(self.state.outcome.get("message", ""))]
        for where, problem in self.state.problems:
            lines += ["", f"A rule on {where} could not be worked out: {problem}"]
        return "\n".join(lines)

    def _spoken(self, item: fd.Item) -> str:
        item_id = str(item.get("id"))
        if item.get("type") in WORKED_OUT or item.get("calculation"):
            return self.worked_out(item_id) or "nothing yet"
        value = self.answers.get(item_id)
        if value is None or value == "" or value == []:
            return "no answer"
        labels = dict(choices_of(item, self.model))
        if isinstance(value, list):
            return ", ".join(labels.get(str(v), str(v)) for v in value)
        if isinstance(value, bool):
            return "yes" if value else "no"
        return labels.get(str(value), str(value))

    # -- plumbing ------------------------------------------------------------ #

    def _starting_answers(self) -> dict[str, Any]:
        """Each question's fixed or smart default (``today + 7``), as the site starts it."""
        from quill.core.forms.rules import smart_default

        out: dict[str, Any] = {}
        for item in M.iter_items(self.model):
            if "default" in item or "smart_default" in item:
                try:
                    value = smart_default(item)
                except Exception:  # noqa: BLE001 - a broken default starts empty
                    value = None
                if value not in (None, ""):
                    out[str(item["id"])] = value
        return out

    def _evaluate(self) -> Any:
        from quill.core.forms.rules import evaluate_form

        return evaluate_form(self.model, self.answers)

    def _first_shown(self, start: int, step: int) -> int:
        pages = self.pages()
        index = start
        while 0 <= index < len(pages):
            if pages[index].get("id") not in self.state.hidden:
                return index
            index += step
        return -1 if (start != 0 or step != 1) else 0
