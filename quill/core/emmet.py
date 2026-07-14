"""Emmet-style markup abbreviation expansion (MVP subset).

Expands compact abbreviations such as ``ul.menu>li.item$*3>a[href]{Item $}``
into full HTML, and a small set of common shorthand into CSS declarations.
This module is pure (no ``wx`` import) and has no dependency on the rest of
QUILL beyond :data:`quill.core.tagging.VOID_HTML_TAGS`.

Supported HTML grammar: child (``>``), sibling (``+``), climb-up (``^``),
grouping (``()``), multiplication (``*N``), numbering (``$``, ``$$``, ...),
ids (``#id``), classes (``.a.b``), attributes (``[attr="value" bool-attr]``),
text content (``{...}``), implicit tags for common parents (``ul`` -> ``li``,
``table`` -> ``tr``, etc.), and a handful of canned accessibility snippets
(``!``, ``!a11y``, ``skiplink``, ``form:a11y``, ``table:a11y``).

Deliberately out of scope for this MVP (tracked as Phase 2/3 backlog, see
``docs/Product Requirement Documents and Specifications/QUILL-PRD.md``):
placeholder/tab-stop cursor navigation after expansion, a snippet manager,
Quillin extension points for custom expansion providers, Markdown-specific
abbreviations, numbering modifiers (``@-``, ``@N``), chaining children
directly after a multiplied group, and a full fuzzy CSS abbreviation engine
(only a curated common subset is implemented here).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from quill.core.tagging import VOID_HTML_TAGS

_VOID_TAGS = frozenset(
    VOID_HTML_TAGS | {"area", "base", "col", "embed", "param", "source", "track", "wbr"}
)

#: Default child tag for a primary segment that has no explicit tag name
#: (e.g. ``ul>.item`` -> ``ul>li.item``), keyed by the immediate parent tag.
_IMPLICIT_TAG_BY_PARENT: dict[str, str] = {
    "ul": "li",
    "ol": "li",
    "table": "tr",
    "tbody": "tr",
    "thead": "tr",
    "tfoot": "tr",
    "tr": "td",
    "select": "option",
    "optgroup": "option",
    "dl": "dt",
}
_DEFAULT_IMPLICIT_TAG = "div"

#: Attributes implicitly added to common tags when not already specified.
_DEFAULT_ATTRS_BY_TAG: dict[str, tuple[tuple[str, str | None], ...]] = {
    "a": (("href", ""),),
    "img": (("src", ""), ("alt", "")),
    "input": (("type", "text"),),
    "link": (("rel", "stylesheet"), ("href", "")),
    "script": (("src", ""),),
    "iframe": (("src", ""),),
    "textarea": (),
    "label": (),
}

_NUMBERING_RE = re.compile(r"\$+")


class EmmetSyntaxError(ValueError):
    """Raised when an abbreviation cannot be parsed."""


@dataclass
class EmmetNode:
    tag: str | None = None
    id: str | None = None
    classes: list[str] = field(default_factory=list)
    attrs: list[tuple[str, str | None]] = field(default_factory=list)
    text: str | None = None
    children: list[EmmetNode] = field(default_factory=list)
    multiplier: int = 1
    is_fragment: bool = False

    def clone(self) -> EmmetNode:
        return EmmetNode(
            tag=self.tag,
            id=self.id,
            classes=list(self.classes),
            attrs=list(self.attrs),
            text=self.text,
            children=[child.clone() for child in self.children],
            multiplier=self.multiplier,
            is_fragment=self.is_fragment,
        )


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------

_TAG_CHARS = re.compile(r"[A-Za-z][A-Za-z0-9:-]*")
_IDENT_CHARS = re.compile(r"[A-Za-z0-9_$-]+")
_ATTR_NAME_CHARS = re.compile(r"[A-Za-z_:][A-Za-z0-9_:-]*")


class _Parser:
    def __init__(self, text: str) -> None:
        self.text = text
        self.pos = 0
        self.length = len(text)

    def _peek(self) -> str:
        return self.text[self.pos] if self.pos < self.length else ""

    def _expect(self, char: str) -> None:
        if self._peek() != char:
            raise EmmetSyntaxError(f"Expected '{char}' at position {self.pos} in '{self.text}'")
        self.pos += 1

    def parse(self) -> list[EmmetNode]:
        levels: list[tuple[list[EmmetNode], str | None]] = [([], None)]
        self._parse_expression(levels)
        if self.pos != self.length:
            raise EmmetSyntaxError(
                f"Unexpected '{self._peek()}' at position {self.pos} in '{self.text}'"
            )
        return levels[0][0]

    def _parse_expression(self, levels: list[tuple[list[EmmetNode], str | None]]) -> None:
        while True:
            self._parse_term(levels)
            if self._peek() == "^":
                while self._peek() == "^":
                    if len(levels) > 1:
                        levels.pop()
                    self.pos += 1
                continue
            if self._peek() == "+":
                self.pos += 1
                continue
            break

    def _parse_term(self, levels: list[tuple[list[EmmetNode], str | None]]) -> None:
        current_list, parent_tag = levels[-1]
        if self._peek() == "(":
            self.pos += 1
            inner_levels: list[tuple[list[EmmetNode], str | None]] = [([], parent_tag)]
            self._parse_expression(inner_levels)
            self._expect(")")
            group_nodes = inner_levels[0][0]
            if self._peek() == "*":
                self.pos += 1
                count = self._parse_int()
                fragment = EmmetNode(children=group_nodes, multiplier=count, is_fragment=True)
                current_list.append(fragment)
            else:
                current_list.extend(group_nodes)
            if self._peek() == ">":
                raise EmmetSyntaxError(
                    "Chaining children directly after a group, e.g. '(a+b)>c', "
                    "is not supported yet."
                )
            return

        node = self._parse_element(parent_tag)
        current_list.append(node)
        if self._peek() == "*":
            self.pos += 1
            node.multiplier = self._parse_int()
        while self._peek() == ">":
            self.pos += 1
            levels.append((node.children, node.tag))
            # The recursive call consumes its own '>' chain (if any) before
            # returning, so this loop only ever runs its body once per '>'
            # immediately following this node.
            self._parse_term(levels)

    def _parse_int(self) -> int:
        start = self.pos
        while self.pos < self.length and self.text[self.pos].isdigit():
            self.pos += 1
        if self.pos == start:
            return 1
        return int(self.text[start : self.pos])

    def _parse_element(self, parent_tag: str | None) -> EmmetNode:
        tag_match = _TAG_CHARS.match(self.text, self.pos)
        tag: str | None
        if tag_match:
            tag = tag_match.group(0)
            self.pos = tag_match.end()
        else:
            tag = None

        node = EmmetNode()
        node_id: str | None = None
        classes: list[str] = []
        while self._peek() in ("#", "."):
            marker = self._peek()
            self.pos += 1
            ident_match = _IDENT_CHARS.match(self.text, self.pos)
            if not ident_match:
                raise EmmetSyntaxError(
                    f"Expected identifier after '{marker}' at position {self.pos} in '{self.text}'"
                )
            ident = ident_match.group(0)
            self.pos = ident_match.end()
            if marker == "#":
                node_id = ident
            else:
                classes.append(ident)

        attrs: list[tuple[str, str | None]] = []
        if self._peek() == "[":
            self.pos += 1
            attrs = self._parse_attrs()
            self._expect("]")

        text: str | None = None
        if self._peek() == "{":
            self.pos += 1
            end = self.text.find("}", self.pos)
            if end == -1:
                raise EmmetSyntaxError(f"Unterminated text content in '{self.text}'")
            text = self.text[self.pos : end]
            self.pos = end + 1

        if tag is None:
            tag = _IMPLICIT_TAG_BY_PARENT.get(parent_tag or "", _DEFAULT_IMPLICIT_TAG)

        node.tag = tag
        node.id = node_id
        node.classes = classes
        node.attrs = attrs
        node.text = text
        return node

    def _parse_attrs(self) -> list[tuple[str, str | None]]:
        attrs: list[tuple[str, str | None]] = []
        while True:
            while self._peek() == " ":
                self.pos += 1
            if self._peek() in ("]", ""):
                break
            name_match = _ATTR_NAME_CHARS.match(self.text, self.pos)
            if not name_match:
                raise EmmetSyntaxError(
                    f"Expected attribute name at position {self.pos} in '{self.text}'"
                )
            name = name_match.group(0)
            self.pos = name_match.end()
            if self._peek() == "=":
                self.pos += 1
                value = self._parse_attr_value()
                attrs.append((name, value))
            else:
                attrs.append((name, None))
        return attrs

    def _parse_attr_value(self) -> str:
        quote = self._peek()
        if quote in ("'", '"'):
            self.pos += 1
            end = self.text.find(quote, self.pos)
            if end == -1:
                raise EmmetSyntaxError(f"Unterminated attribute value in '{self.text}'")
            value = self.text[self.pos : end]
            self.pos = end + 1
            return value
        start = self.pos
        while self.pos < self.length and self.text[self.pos] not in " ]":
            self.pos += 1
        return self.text[start : self.pos]


def parse_html_abbreviation(abbreviation: str) -> list[EmmetNode]:
    """Parse *abbreviation* into a forest of root :class:`EmmetNode` (pre-expansion)."""
    stripped = abbreviation.strip()
    if not stripped:
        raise EmmetSyntaxError("Abbreviation is empty.")
    return _Parser(stripped).parse()


_ABBREVIATION_TOKEN_RE = re.compile(r"\S+$")


def extract_abbreviation_before_cursor(text: str, cursor: int) -> tuple[int, int]:
    """Find the span of non-whitespace text on the current line immediately
    before *cursor* -- the abbreviation a user just typed and wants expanded
    in place. Returns ``(cursor, cursor)`` when there is nothing to expand.
    """
    line_start = text.rfind("\n", 0, cursor) + 1
    segment = text[line_start:cursor]
    match = _ABBREVIATION_TOKEN_RE.search(segment)
    if not match:
        return cursor, cursor
    return line_start + match.start(), cursor


# ---------------------------------------------------------------------------
# Expansion (multiplier + numbering resolution)
# ---------------------------------------------------------------------------


def _substitute_numbering(value: str, index: int, total: int) -> str:
    def repl(match: re.Match[str]) -> str:
        width = len(match.group(0))
        return str(index).zfill(width) if width > 1 else str(index)

    return _NUMBERING_RE.sub(repl, value)


def _apply_numbering(node: EmmetNode, index: int, total: int) -> None:
    if node.id is not None:
        node.id = _substitute_numbering(node.id, index, total)
    node.classes = [_substitute_numbering(c, index, total) for c in node.classes]
    node.attrs = [
        (name, _substitute_numbering(value, index, total) if value is not None else value)
        for name, value in node.attrs
    ]
    if node.text is not None:
        node.text = _substitute_numbering(node.text, index, total)


def _expand_node(node: EmmetNode, ambient: tuple[int, int] = (1, 1)) -> list[EmmetNode]:
    """Resolve one node's multiplier/numbering, propagating ``ambient`` (the
    nearest enclosing repetition's index/total) to descendants that have no
    multiplier of their own -- so ``li*3>span.label$`` numbers the span by
    its enclosing ``li`` instance rather than always rendering ``label1``.
    """
    if node.is_fragment:
        total = max(node.multiplier, 1)
        result: list[EmmetNode] = []
        for index in range(1, total + 1):
            for template in node.children:
                result.extend(_expand_node(template.clone(), ambient=(index, total)))
        return result

    total = max(node.multiplier, 1)
    if total > 1:
        result = []
        for index in range(1, total + 1):
            copy = node.clone()
            copy.multiplier = 1
            result.extend(_expand_node(copy, ambient=(index, total)))
        return result

    copy = node.clone()
    _apply_numbering(copy, ambient[0], ambient[1])
    expanded_children: list[EmmetNode] = []
    for child in copy.children:
        expanded_children.extend(_expand_node(child, ambient=ambient))
    copy.children = expanded_children
    return [copy]


def expand_tree(roots: list[EmmetNode]) -> list[EmmetNode]:
    """Resolve multipliers and ``$`` numbering, returning the final tree."""
    expanded: list[EmmetNode] = []
    for root in roots:
        expanded.extend(_expand_node(root))
    return expanded


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------


def _render_attrs(node: EmmetNode) -> str:
    parts: list[str] = []
    if node.id:
        parts.append(f'id="{node.id}"')
    if node.classes:
        parts.append(f'class="{" ".join(node.classes)}"')
    seen_names = {"id", "class"} | {name for name, _ in node.attrs}
    for name, value in node.attrs:
        if value is None:
            parts.append(name)
        else:
            parts.append(f'{name}="{value}"')
    for name, default_value in _DEFAULT_ATTRS_BY_TAG.get(node.tag or "", ()):
        if name in seen_names:
            continue
        if default_value is None:
            parts.append(name)
        else:
            parts.append(f'{name}="{default_value}"')
    return (" " + " ".join(parts)) if parts else ""


def _render_node(node: EmmetNode, depth: int, indent: str) -> list[str]:
    pad = indent * depth
    attrs = _render_attrs(node)
    tag = node.tag or "div"
    if tag in _VOID_TAGS and not node.children and not node.text:
        return [f"{pad}<{tag}{attrs}>"]
    if not node.children:
        return [f"{pad}<{tag}{attrs}>{node.text or ''}</{tag}>"]
    lines = [f"{pad}<{tag}{attrs}>"]
    for child in node.children:
        lines.extend(_render_node(child, depth + 1, indent))
    lines.append(f"{pad}</{tag}>")
    return lines


def render_html(roots: list[EmmetNode], *, indent: str = "  ") -> str:
    """Render an already-expanded tree (see :func:`expand_tree`) as HTML."""
    lines: list[str] = []
    for root in roots:
        lines.extend(_render_node(root, 0, indent))
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Canned accessibility / boilerplate snippets, checked before grammar parsing
# ---------------------------------------------------------------------------

_SNIPPETS: dict[str, str] = {
    "!": (
        "<!DOCTYPE html>\n"
        '<html lang="en">\n'
        "<head>\n"
        '  <meta charset="UTF-8">\n'
        '  <meta name="viewport" content="width=device-width, initial-scale=1.0">\n'
        "  <title></title>\n"
        "</head>\n"
        "<body>\n\n"
        "</body>\n"
        "</html>"
    ),
    "!a11y": (
        "<!DOCTYPE html>\n"
        '<html lang="en">\n'
        "<head>\n"
        '  <meta charset="UTF-8">\n'
        '  <meta name="viewport" content="width=device-width, initial-scale=1.0">\n'
        "  <title></title>\n"
        "</head>\n"
        "<body>\n"
        '  <a class="skip-link" href="#main-content">Skip to main content</a>\n'
        "  <header>\n"
        "  </header>\n"
        '  <main id="main-content">\n'
        "  </main>\n"
        "  <footer>\n"
        "  </footer>\n"
        "</body>\n"
        "</html>"
    ),
    "skiplink": (
        '<a class="skip-link" href="#main-content">Skip to main content</a>\n'
        '<main id="main-content">\n'
        "</main>"
    ),
    "form:a11y": (
        "<form>\n"
        "  <fieldset>\n"
        "    <legend></legend>\n"
        '    <label for="field1"></label>\n'
        '    <input type="text" id="field1" name="field1">\n'
        "  </fieldset>\n"
        '  <button type="submit">Submit</button>\n'
        "</form>"
    ),
    "table:a11y": (
        "<table>\n"
        "  <caption></caption>\n"
        "  <thead>\n"
        "    <tr>\n"
        '      <th scope="col"></th>\n'
        '      <th scope="col"></th>\n'
        "    </tr>\n"
        "  </thead>\n"
        "  <tbody>\n"
        "    <tr>\n"
        "      <td></td>\n"
        "      <td></td>\n"
        "    </tr>\n"
        "  </tbody>\n"
        "</table>"
    ),
}


def expand_html_abbreviation(abbreviation: str, *, indent: str = "  ") -> str:
    """Expand *abbreviation* to HTML, checking canned snippets first."""
    snippet = _SNIPPETS.get(abbreviation.strip())
    if snippet is not None:
        return snippet
    roots = parse_html_abbreviation(abbreviation)
    expanded = expand_tree(roots)
    return render_html(expanded, indent=indent)


# ---------------------------------------------------------------------------
# CSS abbreviations (curated common subset)
# ---------------------------------------------------------------------------

_CSS_BARE_ABBREVIATIONS: dict[str, str] = {
    "m": "margin: ;",
    "p": "padding: ;",
    "w": "width: ;",
    "h": "height: ;",
    "d": "display: ;",
    "d:n": "display: none;",
    "d:b": "display: block;",
    "d:f": "display: flex;",
    "d:i": "display: inline;",
    "d:ib": "display: inline-block;",
    "d:g": "display: grid;",
    "pos": "position: ;",
    "pos:a": "position: absolute;",
    "pos:r": "position: relative;",
    "pos:f": "position: fixed;",
    "pos:s": "position: sticky;",
    "fl": "float: left;",
    "fr": "float: right;",
    "ov": "overflow: ;",
    "ov:h": "overflow: hidden;",
    "ov:a": "overflow: auto;",
    "ov:s": "overflow: scroll;",
    "bg": "background: ;",
    "bgc": "background-color: ;",
    "c": "color: ;",
    "fz": "font-size: ;",
    "fw": "font-weight: ;",
    "fw:b": "font-weight: bold;",
    "ta": "text-align: ;",
    "ta:c": "text-align: center;",
    "ta:l": "text-align: left;",
    "ta:r": "text-align: right;",
    "td:n": "text-decoration: none;",
    "jc": "justify-content: ;",
    "jc:c": "justify-content: center;",
    "ai": "align-items: ;",
    "ai:c": "align-items: center;",
    "b": "border: ;",
    "bd": "border: ;",
    "br": "border-radius: ;",
    "cur": "cursor: ;",
    "cur:p": "cursor: pointer;",
    "op": "opacity: ;",
    "z": "z-index: ;",
}

_CSS_BOX_PROPERTIES: dict[str, str] = {
    "m": "margin",
    "mt": "margin-top",
    "mr": "margin-right",
    "mb": "margin-bottom",
    "ml": "margin-left",
    "p": "padding",
    "pt": "padding-top",
    "pr": "padding-right",
    "pb": "padding-bottom",
    "pl": "padding-left",
    "w": "width",
    "h": "height",
    "t": "top",
    "r": "right",
    "b": "bottom",
    "l": "left",
}

_CSS_NUMERIC_RE = re.compile(r"^([a-z]+)(-?\d+(?:-\-?\d+){0,3})$")
#: Splits a numbers run like "10-20" or "10--20" into ["10", "20"] / ["10", "-20"]:
#: a single "-" is a value separator, a doubled "--" is separator + sign.
_CSS_VALUE_RE = re.compile(r"(?:^|-)(-?\d+)")


def expand_css_abbreviation(abbreviation: str) -> str | None:
    """Expand a curated common-subset CSS abbreviation, or ``None`` if unknown."""
    text = abbreviation.strip()
    if text in _CSS_BARE_ABBREVIATIONS:
        return _CSS_BARE_ABBREVIATIONS[text]
    match = _CSS_NUMERIC_RE.match(text)
    if match:
        prefix, numbers = match.groups()
        if prefix in _CSS_BOX_PROPERTIES:
            property_name = _CSS_BOX_PROPERTIES[prefix]
            tokens = _CSS_VALUE_RE.findall(numbers)
            values = [f"{n}px" if n != "0" else "0" for n in tokens]
            return f"{property_name}: {' '.join(values)};"
    return None


# ---------------------------------------------------------------------------
# Explain (human-readable, screen-reader-friendly description)
# ---------------------------------------------------------------------------


def _describe_node(node: EmmetNode) -> str:
    parts = [node.tag or "div"]
    if node.id:
        parts.append(f"#{node.id}")
    if node.classes:
        parts.append("." + ".".join(node.classes))
    descriptor = "".join(parts)
    extras: list[str] = []
    if node.attrs:
        attr_names = ", ".join(name for name, _ in node.attrs)
        extras.append(f"attributes: {attr_names}")
    if node.multiplier > 1:
        extras.append(f"repeated {node.multiplier} times, numbered 1 to {node.multiplier}")
    if node.text:
        extras.append(f'text: "{node.text}"')
    if extras:
        descriptor += " (" + "; ".join(extras) + ")"
    return descriptor


def explain_abbreviation(abbreviation: str) -> str:
    """Return a plain-text, indented description of the parsed (pre-expansion) tree."""
    stripped = abbreviation.strip()
    snippet = _SNIPPETS.get(stripped)
    if snippet is not None:
        return f"'{stripped}' is a built-in snippet that inserts a fixed block of markup."
    roots = parse_html_abbreviation(abbreviation)

    lines: list[str] = []

    def walk(node: EmmetNode, depth: int) -> None:
        pad = "  " * depth
        if node.is_fragment:
            suffix = f" (repeated {node.multiplier} times)" if node.multiplier > 1 else ""
            lines.append(f"{pad}- group{suffix}")
            for child in node.children:
                walk(child, depth + 1)
            return
        lines.append(f"{pad}- {_describe_node(node)}")
        for child in node.children:
            walk(child, depth + 1)

    for root in roots:
        walk(root, 0)
    return "\n".join(lines)
