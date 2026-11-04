"""Reading BFL into the form model, keeping every byte.

This reads BFL as BAF's language guide documents it (all four block styles,
choices in any position, ``if`` and ``columns`` bodies), plus the spellings
the model needs that BAF's guide does not have yet (``@when``, ``@calculate``,
``@score``, ``@choice_score``, ``@translate``, ``outcome``, conditions in the
full expression language, every model field type, and repeater children).
:mod:`bfl_spelling` lists them.

It is deliberately not a copy of BAF's PHP parser, which today drops the first
choice of an indented list and the first field of an indented ``if`` (see
:mod:`baf_parser` and the conformance report). Where the two disagree,
:func:`quill.core.forms.baf_compare.divergences` says so in a sentence.

**Islands.** A line QUILL cannot read — an unknown keyword, a stray word, a
condition that does not parse, BAF's export dialect — becomes an
:class:`~quill.core.forms.model.Island` holding the line and any lines
indented under it, exactly. A modifier QUILL does not know is kept, as
written, in the field's ``settings["unknown_modifiers"]``. Comments are
islands too, so a round trip through the JSON model keeps them.

The result is a :class:`BflDocument`: the model plus where each statement came
from, which :mod:`bfl_write` uses to write unchanged statements back byte for
byte and regenerate only what was edited.
"""

from __future__ import annotations

from typing import Any

from quill.core.forms import bfl_lexer as L
from quill.core.forms import expr as E
from quill.core.forms.baf_parser import (
    split_choice,
)
from quill.core.forms.bfl_lexer import Token
from quill.core.forms.bfl_parts import (
    _EXPR_MODIFIERS,
    _VERSION,
    ALIASES,
    CHOICE_KEYWORD_TYPES,
    BflDocument,
    Cursor,
    FormHeader,
    Stmt,
    VersionLine,
    _and,
    _apply,
    _known,
    _Malformed,
)
from quill.core.forms.errors import ExpressionError, FormVersionError
from quill.core.forms.model import (
    FIELD_TYPES,
    MODEL_VERSION,
    Choice,
    Columns,
    Field,
    Form,
    Island,
    Item,
    Outcome,
    Page,
    Section,
)


class _Reader(Cursor):
    def __init__(self, text: str) -> None:
        super().__init__(text)
        self.form = Form()
        self.page = self.form.pages[0]
        self.section: Section | None = None
        self.page_count = 1
        self.saw_form = False
        self.first_page_used = False

    # -- statements -----------------------------------------------------------
    def statements(
        self, parent: int, explicit: bool, cond: str | None, sink: list[Item] | None
    ) -> list[Stmt]:
        """Read statements whose lines are indented deeper than ``parent``.

        ``explicit`` blocks end at a closer instead. ``cond`` is the condition
        of the enclosing ``if`` blocks; ``sink`` the column list items go to
        (None for the page).
        """
        out: list[Stmt] = []
        while True:
            save = self.i
            self.skip_blank()
            if explicit and self.is_close():
                return out
            if self.eof() or (not explicit and self.indent_of(self.tok().pos) <= parent):
                self.i = save
                return out
            first = self.tok()
            mark = self.mark(sink)
            try:
                objs = self.statement(cond, sink)
            except _Malformed as bad:
                self.rollback(mark, sink)
                objs = [self.island(bad.reason, sink)]
            out.append(Stmt(self.start_of(first), self.span_end(), objs))

    def mark(self, sink: list[Item] | None) -> tuple[Any, ...]:
        section = self.section
        return (
            self.i, self.page, len(self.page.items), section,
            len(section.items) if section else 0, len(sink) if sink is not None else 0,
            len(self.form.pages), len(self.form.outcomes),
            {k: dict(v) for k, v in self.form.translations.items()},
            self.counter, self.page_count, self.saw_form, self.first_page_used,
        )  # fmt: skip

    def rollback(self, mark: tuple[Any, ...], sink: list[Item] | None) -> None:
        """Undo a statement that turned out to be an island."""
        (self.i, self.page, n_page, self.section, n_section, n_sink, n_pages, n_out,
         translations, self.counter, self.page_count, self.saw_form,
         self.first_page_used) = mark  # fmt: skip
        del self.page.items[n_page:]
        if self.section is not None:
            del self.section.items[n_section:]
        if sink is not None:
            del sink[n_sink:]
        del self.form.pages[n_pages:]
        del self.form.outcomes[n_out:]
        self.form.translations = translations

    def island(self, reason: str, sink: list[Item] | None) -> Island:
        first = self.tok()
        level = self.indent_of(first.pos)
        line = self.line_of(first.pos)
        depth = 0  # blocks the island opened and has not closed yet
        while not self.eof():
            t = self.tok()
            if t.type in (L.NEWLINE, L.INDENT):
                self.i += 1
                continue
            same = self.line_of(t.pos) == line
            if not (same or depth > 0 or self.indent_of(t.pos) > level):
                break
            if self.is_open():
                depth += 1
            elif self.is_close():
                if depth == 0 and not same:
                    break
                depth = max(0, depth - 1)
            line = self.line_of(t.pos)
            self.i += 1
        while self.i > 0 and self.toks[self.i - 1].type in (L.NEWLINE, L.INDENT):
            self.i -= 1
        isl = Island(self.text[self.start_of(first) : self.span_end()], reason)
        self.place(isl, sink)
        return isl

    def place(self, item: Item, sink: list[Item] | None) -> None:
        if sink is not None:
            sink.append(item)
        elif self.section is not None and not isinstance(item, Section):
            self.section.items.append(item)
        else:
            self.page.items.append(item)

    def statement(self, cond: str | None, sink: list[Item] | None) -> list[Any]:
        t = self.tok()
        if t.type == L.COMMENT and self.i == self.first_content() and _VERSION.fullmatch(t.value):
            self.i += 1
            if not self.end_of_line_or_comment():
                raise _Malformed("Something follows the version on its line.")
            found = _VERSION.fullmatch(t.value)
            self.form.version = int(found.group(1)) if found else MODEL_VERSION
            if self.form.version > MODEL_VERSION:
                raise FormVersionError(
                    f"This form was written for BFL version {self.form.version}; this copy of "
                    f"QUILL reads up to version {MODEL_VERSION}. Update QUILL to open it."
                )
            return [VersionLine()]
        if t.type == L.COMMENT:
            self.i += 1
            if not self.end_of_line_or_comment():
                raise _Malformed("Something follows this comment on its line.")
            isl = Island(self.text[self.start_of(t) : self.span_end()], "comment")
            self.place(isl, sink)
            return [isl]
        word = t.value.lower() if t.type in (L.KEYWORD, L.STRING) and self.bare(t) else ""
        if word == "form" and t.type == L.KEYWORD and sink is None and cond is None:
            return self.form_line()
        if word == "page" and sink is None and cond is None:
            return [self.page_line()]
        if word == "section":
            return [self.section_line(cond, sink)]
        if word == "columns":
            return [self.columns(cond, sink)]
        if word in ("if", "conditional"):
            return self.conditional(cond, sink)
        if word == "outcome" and sink is None and cond is None:
            return [self.outcome()]
        kind = ALIASES.get(word, word)
        if kind in FIELD_TYPES and kind != "section":
            item = self.field_statement(cond)
            self.place(item, sink)
            return [item]
        raise _Malformed(f"QUILL does not know {t.value!r} as the start of a line in a form.")

    def form_line(self) -> list[Any]:
        line_tok = self.tok()
        if self.saw_form:
            raise _Malformed("A form has one form line; this is a second.")
        self.saw_form = True
        self.i += 1
        title = ""
        if self.at(L.STRING):
            title = self.tok().value
            self.i += 1
        target: dict[str, Any] = {}
        self.modifier_run(line_tok, target, allow_body=True)
        known = {"description", "ajax", "honeypot", "captcha", "save_and_continue", "rate_limit",
                 "captcha_type", "submit_label", "success_message", "redirect_url",
                 "unknown_modifiers", "translations"}  # fmt: skip
        if set(target) - known:
            raise _Malformed("This form line has settings a form cannot hold.")
        self.form.title = title
        s = self.form.settings
        for key in ("description",):
            if key in target:
                self.form.description = str(target.pop(key))
        for key in ("ajax", "honeypot", "captcha", "save_and_continue", "rate_limit"):
            if target.pop(key, False):
                setattr(s, key, True)
        for key in ("captcha_type", "submit_label", "success_message", "redirect_url"):
            if key in target:
                setattr(s, key, str(target.pop(key)))
        self.take_translations(target, "")
        unknown = target.pop("unknown_modifiers", None)
        if unknown:
            s.extra["unknown_modifiers"] = unknown
        return [FormHeader()]

    def page_line(self) -> Page:
        line_tok = self.tok()
        self.i += 1
        first = self.form.pages[0]
        reuse = (
            not self.first_page_used
            and not first.items
            and len(self.form.pages) == 1
            and not first.title
        )
        page = first if reuse else Page(id=f"page_{self.page_count + 1}")
        title = ""
        if self.at(L.STRING):
            title = self.tok().value
            self.i += 1
        target: dict[str, Any] = {}
        self.modifier_run(line_tok, target, allow_body=True)
        if set(target) - {"description", "visible_when", "translations"}:
            raise _Malformed("A page line takes only @description and @when.")
        if not reuse:
            self.page_count += 1
            self.form.pages.append(page)
        self.first_page_used = True
        self.take_translations(target, f"page.{page.id}.")
        page.title = title
        page.description = str(target.pop("description", ""))
        page.visible_when = target.pop("visible_when", None)
        self.page, self.section = page, None
        return page

    def section_line(self, cond: str | None, sink: list[Item] | None) -> Section:
        line_tok = self.tok()
        self.i += 1
        section = Section(id=self.new_id())
        if self.at(L.STRING):
            section.title = self.tok().value
            self.i += 1
        target: dict[str, Any] = {}
        self.modifier_run(line_tok, target, allow_body=True)
        self.take_translations(target, f"section.{section.id}.")
        section.description = str(target.pop("description", ""))
        section.visible_when = _and(cond, target.pop("visible_when", None))
        if target:
            raise _Malformed("A section line takes only @description and @when.")
        self.place(section, sink)
        if sink is None:
            self.section = section
        return section

    def outcome(self) -> Outcome:
        line_tok = self.tok()
        self.i += 1
        if not self.at(L.STRING):
            raise _Malformed("An outcome needs its message in quotes.")
        message = self.tok().value
        self.i += 1
        target: dict[str, Any] = {}
        self.modifier_run(line_tok, target, allow_body=True)
        self.take_translations(target, f"outcome.{len(self.form.outcomes) + 1}.")
        when = target.pop("visible_when", None)
        if when is None or target:
            raise _Malformed("An outcome needs @when and nothing else.")
        result = Outcome(when=when, message=message)
        self.form.outcomes.append(result)
        return result

    # -- if and columns -----------------------------------------------------------
    def conditional(self, cond: str | None, sink: list[Item] | None) -> list[Any]:
        head = self.tok()
        self.i += 1
        text = self.expression(head)
        block_cond = _and(cond, text)
        saved = self.section
        objs: list[Any] = []
        for stmt in self.body(head, block_cond, sink):
            objs.extend(stmt.objs)
        if sink is not None:
            self.section = saved
        return objs

    def body(self, head: Token, cond: str | None, sink: list[Item] | None) -> list[Stmt]:
        while self.at(L.COMMENT):
            self.i += 1
        if self.is_open() and self.same_line(head.pos, self.tok().pos):
            self.i += 1
            stmts = self.statements(-1, True, cond, sink)
            if not self.is_close():
                raise _Malformed("This block is never closed.")
            self.i += 1
            return stmts
        if self.tok().type not in (L.NEWLINE, L.EOF):
            raise _Malformed(f"I did not expect {self.tok().value!r} here.")
        return self.statements(self.indent_of(head.pos), False, cond, sink)

    def columns(self, cond: str | None, sink: list[Item] | None) -> Columns:
        head = self.tok()
        self.i += 1
        item = Columns(id=self.new_id(), visible_when=cond)
        if self.at(L.NUMBER):
            item.count = int(float(self.tok().value))
            self.i += 1
        saved = self.section
        explicit = self.is_open() and self.same_line(head.pos, self.tok().pos)
        if explicit:
            self.i += 1
        elif self.tok().type not in (L.NEWLINE, L.EOF, L.COMMENT):
            raise _Malformed("A columns line takes only a number.")
        level = self.indent_of(head.pos)
        closed = not explicit
        while True:
            save = self.i
            self.skip_blank()
            if explicit and self.is_close():
                self.i += 1
                closed = True
                break
            if self.eof() or (not explicit and self.indent_of(self.tok().pos) <= level):
                self.i = save
                break
            if not self.at(L.KEYWORD, "column"):
                raise _Malformed("A columns layout holds only column blocks.")
            col_tok = self.tok()
            self.i += 1
            column: list[Item] = []
            self.body(col_tok, None, column)
            item.columns.append(column)
        if not closed:
            raise _Malformed("This columns block is never closed.")
        self.section = saved
        self.place(item, sink)
        return item

    def expression(self, head: Token) -> str:
        start = self.tok().pos
        if self.tok().type in (L.NEWLINE, L.EOF):
            raise _Malformed("This needs a condition after it.")
        try:
            node, end = E.parse_embedded(self.text, start)
        except ExpressionError as exc:
            raise _Malformed(f"I cannot read this condition: {exc}") from exc
        while not self.eof() and self.tok().pos < end and self.tok().type != L.NEWLINE:
            if self.tok().end > end:
                raise _Malformed("Put anything after this rule on its own line.")
            self.i += 1
        return E.to_text(node)

    # -- fields -------------------------------------------------------------------
    def field_statement(self, cond: str | None) -> Field:
        head = self.tok()
        kind = ALIASES.get(head.value.lower(), head.value.lower())
        self.i += 1
        item = Field(id=self.new_id(), type=kind)
        if self.at(L.IDENTIFIER):
            item.id = self.tok().value
            self.i += 1
        t = self.tok()
        if t.type == L.STRING and not self.is_library(t):
            item.label = t.value
            self.i += 1
        elif (
            t.type == L.KEYWORD
            and t.value not in ("begin", "end")
            and t.value not in L.LIBRARY_KEYWORDS
            and self.same_line(head.pos, t.pos)
        ):
            item.label = self.text[t.pos : t.end]
            self.i += 1
        if (self.at(L.KEYWORD) or self.at(L.STRING)) and self.is_library(self.tok()):
            item.choice_library = self.tok().value
            self.i += 1
        target: dict[str, Any] = {}
        self.modifier_run(head, target, allow_body=True, owner=item)
        self.take_translations(target, f"field.{item.id}.")
        _apply(item, target)
        item.visible_when = _and(cond, item.visible_when)
        return item

    def take_translations(self, target: dict[str, Any], prefix: str) -> None:
        """``@translate fr label "Courriel"`` into ``form.translations``."""
        for values in target.pop("translations", []):
            key = prefix + ".".join(values[1:-1])
            if prefix == "" and key in ("submit_label", "success_message"):
                key = "settings." + key
            self.form.translations.setdefault(values[0], {})[key] = values[-1]

    def is_library(self, t: Token) -> bool:
        return self.bare(t) and t.value in L.LIBRARY_KEYWORDS

    def modifier_run(
        self, head: Token, target: dict[str, Any], *, allow_body: bool, owner: Field | None = None
    ) -> None:
        """Modifiers and choices after a head token: same line, a block, then indented lines."""
        level = self.indent_of(head.pos)
        self.items_on_line(target, owner, head_line=True)
        if self.is_open() and self.same_line(head.pos, self.tok().pos):
            self.i += 1
            while True:
                self.skip_blank()
                if self.eof():
                    raise _Malformed("This block is never closed.")
                if self.is_close():
                    self.i += 1
                    break
                if owner is not None and owner.type == "repeater" and self.child_field_here():
                    owner.fields.append(self.field_statement(None))
                    continue
                if not self.one_item(target, owner):
                    raise _Malformed(f"I did not expect {self.tok().value!r} in this block.")
            self.items_on_line(target, owner)
        if self.tok().type not in (L.NEWLINE, L.EOF):
            raise _Malformed(f"I did not expect {self.tok().value!r} here.")
        if not allow_body:
            return
        while True:
            save = self.i
            self.skip_blank()
            if self.eof() or self.indent_of(self.tok().pos) <= level:
                self.i = save
                return
            if owner is not None and owner.type == "repeater" and self.child_field_here():
                owner.fields.append(self.field_statement(None))
                continue
            if not (self.at(L.MODIFIER) or self.at(L.CHOICE)):
                self.i = save
                return
            self.items_on_line(target, owner)
            if self.tok().type not in (L.NEWLINE, L.EOF):
                raise _Malformed(f"I did not expect {self.tok().value!r} here.")

    def child_field_here(self) -> bool:
        t = self.tok()
        word = t.value.lower() if t.type in (L.KEYWORD, L.STRING) and self.bare(t) else ""
        return ALIASES.get(word, word) in FIELD_TYPES and word != "section"

    def items_on_line(
        self, target: dict[str, Any], owner: Field | None, *, head_line: bool = False
    ) -> None:
        while True:
            if head_line and self.at(L.CHOICE):
                raise _Malformed("Choices go on their own lines, under the question.")
            if not self.one_item(target, owner):
                break
        while self.at(L.COMMENT):
            self.i += 1

    def one_item(self, target: dict[str, Any], owner: Field | None) -> bool:
        if self.at(L.CHOICE):
            if owner is None or (owner.type not in CHOICE_KEYWORD_TYPES):
                raise _Malformed("Only a choice question takes + choices.")
            c = split_choice(self.tok().value)
            owner.choices.append(Choice(c["value"], c["label"], c.get("price")))
            self.i += 1
            return True
        if self.at(L.COMMENT):
            self.i += 1
            return True
        if not self.at(L.MODIFIER):
            return False
        self.modifier(target)
        return True

    def args(self) -> list[Token]:
        out: list[Token] = []
        while True:
            t = self.tok()
            if t.type in (L.STRING, L.NUMBER, L.IDENTIFIER) or (
                t.type == L.KEYWORD and t.value not in ("end", "begin")
            ):
                out.append(t)
                self.i += 1
            elif t.type == L.BRACKET_OPEN and not out:
                self.i += 1
                while not self.at(L.BRACKET_CLOSE):
                    if self.tok().type in (L.NEWLINE, L.EOF):
                        raise _Malformed("This list is never closed with ].")
                    if self.tok().type in (L.STRING, L.KEYWORD):
                        out.append(self.tok())
                    self.i += 1
                self.i += 1
                return out
            else:
                return out

    def modifier(self, target: dict[str, Any]) -> None:
        mod = self.tok()
        name = mod.value
        self.i += 1
        quoted = self.at(L.STRING) and not self.bare(self.tok())
        if name in _EXPR_MODIFIERS or (name == "smart_default" and not quoted):
            text = self.expression(mod)
            key = {"when": "visible_when", "smart_default": "default_expr"}.get(name, name)
            target[key] = _and(target.get(key), text) if key == "visible_when" else text
            return
        args = self.args()
        values = [a.value for a in args]
        raw = self.text[mod.pos : self.toks[self.i - 1].end]
        if not _known(name, args, target, values):
            target.setdefault("unknown_modifiers", []).append(raw)


def read_bfl(text: str) -> BflDocument:
    """BFL text to a :class:`BflDocument` (the model plus its sources)."""
    reader = _Reader(text)
    stmts = reader.statements(-1, False, None, None)
    form = reader.form
    doc = BflDocument(text=text, form=form, statements=stmts)
    previous = 0
    for stmt in stmts:
        stmt.gap = text[previous : stmt.start]
        previous = stmt.end
    doc.tail = text[previous:]
    from quill.core.forms.bfl_write import snapshot

    for stmt in stmts:
        stmt.objs = [doc.header if isinstance(o, FormHeader) else o for o in stmt.objs]
        for obj in stmt.objs:
            if isinstance(obj, VersionLine):
                doc.version = obj
        for obj in stmt.objs:
            doc.snapshots[id(obj)] = snapshot(obj, form)
    doc.snapshots[id(doc.header)] = snapshot(doc.header, form)
    return doc


def read_form(text: str) -> Form:
    """BFL text to the form model."""
    return read_bfl(text).form
