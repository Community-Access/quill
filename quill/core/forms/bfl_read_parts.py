"""The rest of the BFL reader: blocks, item modifiers, choices and the other statements.

Part of the port of BAF's ``BAF_BFL_Reader`` (see :mod:`bfl_read`), split out
for GATE-11. :class:`ReaderBase` holds what does not depend on the item
grammar: reading a block, a field's modifiers and choice lines, folding flat
sections, and the library, rule, scoring, confirmation, notification,
translation and older settings statements.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from typing import Any

from quill.core.forms import expr as E
from quill.core.forms import model as M
from quill.core.forms.bfl_lex import Lexed, Token, _php_string, php_numeric

FLAGS = (
    "required", "unique", "readonly", "disabled", "multiple", "autofocus", "searchable",
    "hidden", "admin", "admin-only", "confirm", "allow-other", "allowother", "partial",
    "case_sensitive",
)  # fmt: skip
EXPRESSION_MODIFIERS = ("when", "calculate")
PROP_ALIASES = {
    "readonly": "read_only", "class": "css_class", "css": "css_class", "admin": "admin_only",
    "admin-only": "admin_only", "allow-other": "allow_other", "allowother": "allow_other",
    "confirm": "confirm_email",
}  # fmt: skip
COMPILER_SETTINGS = {
    "honeypot": "enable_honeypot", "captcha": "enable_captcha", "ajax": "ajax_submission",
    "saveAndContinue": "save_continue_enabled", "rateLimit": "rate_limit_enabled",
}  # fmt: skip
ITEM_ORDER = (
    "id", "type", "label", "help", "placeholder", "required", "default", "smart_default", "mask",
    "when", "calculation", "choices", "choice_library", "cascade", "validation", "scoring",
    "attributes", "columns", "items", "props", "__flat",
)  # fmt: skip
_SIMPLE_STRINGS = {
    "placeholder": ("placeholder",), "description": ("help",), "desc": ("help",), "help": ("help",),
    "mask": ("mask",), "library": ("choice_library",),
    "cascade_from": ("cascade", "from"), "cascadefrom": ("cascade", "from"),
    "cascade_library": ("cascade", "library"), "cascadelibrary": ("cascade", "library"),
    "empty_message": ("cascade", "empty_message"), "emptymessage": ("cascade", "empty_message"),
    "loading_message": ("cascade", "loading_message"), "loadingmessage": ("cascade", "loading_message"),  # noqa: E501
    "pattern": ("validation", "pattern"), "error_message": ("validation", "message"),
    "unique_scope": ("validation", "unique_scope"), "unique_message": ("validation", "unique_message"),  # noqa: E501
    "feedback_correct": ("scoring", "feedback_correct"),
    "feedback_incorrect": ("scoring", "feedback_incorrect"),
    "feedback_partial": ("scoring", "feedback_partial"), "explanation": ("scoring", "explanation"),
}  # fmt: skip


def order(entry: dict[str, Any], keys: tuple[str, ...]) -> dict[str, Any]:
    return {k: entry[k] for k in keys if k in entry}


def legacy_smart_default(text: str) -> str:
    """Older smart-default text (``today+7``, ``user:email``, ``geo``) as an expression."""
    t = str(text).strip(" \t\n\r\0\x0b")
    m = re.fullmatch(r"today\s*([+-])\s*(\d+)", t, re.I)
    if m:
        return f"today() {m.group(1)} {int(m.group(2))}"
    if t.lower() == "today":
        return "today()"
    if t.lower() == "geo":
        return "geo()"
    m = re.fullmatch(r"(user|query|get):([A-Za-z0-9_.-]+)", t, re.I)
    if m:
        fn = "user" if m.group(1).lower() == "user" else "query"
        return f"{fn}({E.quote(m.group(2))})"
    return E.quote(t)


def safe_attribute(name: str) -> bool:
    return (
        re.fullmatch(
            r"(data-[a-z0-9_.-]+|aria-[a-z]+|title|lang|dir|translate|contenteditable|draggable|"
            r"spellcheck|tabindex|accesskey|role|slot|part)",
            name,
        )
        is not None
    )


def _php_int(v: Any) -> int:
    if isinstance(v, bool):
        return int(v)
    if isinstance(v, (int, float)):
        return int(v)
    m = re.match(r"\s*[+-]?\d+", str(v or ""))
    return int(m.group(0)) if m else 0


class ReaderBase(Lexed):
    model: M.Model

    def parse_item_statement(self, condition: str | None) -> list[M.Item]:  # pragma: no cover
        raise NotImplementedError

    # -- blocks ------------------------------------------------------------------------
    def body(self, header: Token, on: Callable[[str, Token], bool]) -> str:  # noqa: C901
        """Inline modifiers, then an explicit block or the lines indented under ``header``."""
        explicit = False
        base = header["indent"]
        line = header["line"]
        took = False
        children = False
        while not self.at_end():
            t = self.peek()
            if (
                not explicit
                and not took
                and self.is_open(t)
                and (
                    t["line"] == line
                    or (t["first"] and (t["t"] == "LBRACE" or self.is_word(t, "begin")))
                )
            ):
                self.next()
                explicit = True
                continue
            if explicit and self.is_close(t):
                self.next()
                return "explicit"
            if not explicit and self.is_close(t):
                break
            if not explicit and t["line"] != line and t["first"] and t["indent"] <= base:
                if children or t["t"] not in ("MOD", "CHOICE"):
                    break
            if t["t"] == "MOD":
                self.next()
                on("mod", t)
                took = True
                continue
            if t["t"] == "CHOICE":
                self.next()
                on("choice", t)
                took = True
                continue
            if t["t"] == "WORD" and on("child", t):
                took = True
                children = True
                continue
            if t["t"] == "WORD" and (
                self.starts_item(t)
                or self.starts_statement(t)
                or self.is_word(t, "column")
                or self.is_word(t, "else")
            ):
                if not explicit:
                    break
                self.warn(t["line"], f"A block opened on line {line} was not closed.")
                return "explicit"
            self.warn(t["line"], f'Skipped "{t["v"]}", which BFL does not expect here.')
            self.next()
        return "explicit" if explicit else ("indent" if took else "none")

    def container(
        self,
        header: Token,
        condition: str | None,
        mod: Callable[[Token], Any],
        extra: dict[str, Callable[[Token], bool]] | None = None,
    ) -> tuple[list[M.Item], str]:
        found: list[M.Item] = []
        words = extra or {}

        def on(kind: str, t: Token) -> bool:
            if kind == "mod":
                mod(t)
                return True
            if kind == "choice":
                self.warn(
                    t["line"], f'A choice ("+ {t["v"]}") is only allowed under a choice field.'
                )
                return True
            w = str(t["v"]).lower()
            if w in words:
                return words[w](t)
            if self.starts_item(t):
                found.extend(self.parse_item_statement(condition))
                return True
            return False

        mode = self.body(header, on)
        return found, mode

    # -- item modifiers ------------------------------------------------------------------
    def item_mod(self, item: dict[str, Any], mod: Token) -> None:  # noqa: C901 - one case per modifier
        name = str(mod["v"])
        if name in EXPRESSION_MODIFIERS or name == "smart_default":
            nt = self.peek()
            if (
                name == "smart_default"
                and nt["t"] == "STRING"
                and nt["line"] == mod["line"]
                and self.peek(1)["line"] != mod["line"]
            ):
                self.next()
                item["smart_default"] = legacy_smart_default(nt["v"])
                return
            text = self.expression(self.raw_to_eol(mod), mod["line"])
            if text is None:
                return
            item[
                {"when": "when", "calculate": "calculation", "smart_default": "smart_default"}[name]
            ] = text
            return
        has, value = False, None
        if name not in FLAGS:
            has, value = self.mod_value(mod)
        else:
            nt = self.peek()
            if (
                nt["t"] == "WORD"
                and nt["line"] == mod["line"]
                and str(nt["v"]).lower() in ("true", "false")
            ):
                self.next()
                has, value = True, str(nt["v"]).lower() == "true"
        flag = bool(value) if has else True
        if name == "required":
            item["required"] = flag
        elif name == "default":
            item["default"] = value
        elif name in _SIMPLE_STRINGS:
            path = _SIMPLE_STRINGS[name]
            if len(path) == 1:
                item[path[0]] = _php_string(value)
            else:
                item.setdefault(path[0], {})[path[1]] = _php_string(value)
        elif name in ("min", "max"):
            item.setdefault("validation", {})[name] = value
        elif name in ("minlength", "min_length"):
            item.setdefault("validation", {})["min_length"] = _php_int(value)
        elif name in ("maxlength", "max_length"):
            item.setdefault("validation", {})["max_length"] = _php_int(value)
        elif name == "unique":
            item.setdefault("validation", {})["unique"] = flag
        elif name == "attr":
            attr_value = None
            if has:
                has2, attr_value = self.mod_value(mod)
                if not has2:
                    attr_value = None
            if has and attr_value is not None and safe_attribute(_php_string(value)):
                item.setdefault("attributes", {})[_php_string(value)] = attr_value
            elif has:
                self.warn(
                    mod["line"],
                    f'The attribute "{_php_string(value)}" is not allowed and was skipped.',
                )
        elif name == "correct":
            items = value if isinstance(value, list) else [value]
            item.setdefault("scoring", {})["correct"] = [_php_string(v) for v in items]
        elif name == "points":
            item.setdefault("scoring", {})["points"] = value
        elif name in ("partial", "case_sensitive"):
            item.setdefault("scoring", {})[name] = flag
        elif name == "hidden":
            item.setdefault("props", {})["visibility"] = "hidden"
        elif name == "spellcheck":
            if has and isinstance(value, str):
                spell: Any = value.lower() in ("true", "yes", "1", "on")
            else:
                spell = value if has else True
            item.setdefault("props", {})["spellcheck"] = spell
        elif name == "capture":
            item.setdefault("props", {})["capture"] = value if has else "environment"
        else:
            key = PROP_ALIASES.get(name, name.replace("-", "_"))
            item.setdefault("props", {})[key] = flag if name in FLAGS else (value if has else True)

    def choice(self, t: Token) -> dict[str, Any] | None:
        raw = str(t["v"])
        if raw == "":
            self.warn(t["line"], "An empty choice was skipped.")
            return None
        trim = " \t\n\r\0\x0b"
        if raw[0] != '"':
            if "|" in raw:
                value, label = raw.split("|", 1)
                return {"value": value.strip(trim), "label": label.strip(trim)}
            if ":" in raw:
                label, price = (x.strip(trim) for x in raw.split(":", 1))
                if php_numeric(price):
                    return {
                        "value": M.slug(label),
                        "label": label,
                        "price": float(price)
                        if "." in price or "e" in price.lower()
                        else int(price),
                    }
                return {"value": M.slug(raw), "label": raw}
            return {"value": M.slug(raw), "label": raw}
        sub = ReaderBase()
        sub.src = raw
        toks = sub.lex(raw)
        first = toks[0]
        i = 1
        if (
            len(toks) > 2
            and toks[1]["t"] == "OTHER"
            and toks[1]["v"] == "|"
            and toks[2]["t"] == "STRING"
        ):
            out: dict[str, Any] = {
                "value": _php_string(first["v"]),
                "label": _php_string(toks[2]["v"]),
            }
            i = 3
        else:
            out = {"value": M.slug(_php_string(first["v"])), "label": _php_string(first["v"])}
        for e in sub.errors:
            self.error(t["line"], e["message"])
        sub.toks = toks
        sub.p = i
        while not sub.at_end():
            m = sub.next()
            if m["t"] != "MOD":
                self.warn(t["line"], f'Skipped "{m["v"]}" in a choice.')
                continue
            has, value = sub.mod_value(m)
            if m["v"] in ("price", "points"):
                out[m["v"]] = value
            elif m["v"] in ("image", "description"):
                out[m["v"]] = _php_string(value)
            elif m["v"] == "selected":
                out["selected"] = bool(value) if has else True
            else:
                self.warn(t["line"], f'A choice has no "{m["v"]}"; it was skipped.')
        return out

    def finish_items(self, entries: list[M.Item]) -> list[M.Item]:
        """Fold flat sections (the items after one belong to it), recursively."""
        out: list[M.Item] = []
        open_at: int | None = None
        for item in entries:
            if item.get("type") == "section":
                open_at = None
                if item.get("__flat"):
                    item.pop("__flat")
                    out.append(item)
                    open_at = len(out) - 1
                    continue
            if open_at is not None:
                out[open_at]["items"].append(item)
            else:
                out.append(item)
        for item in out:
            if item.get("type") == "columns":
                for col in item["columns"]:
                    col["items"] = self.finish_items(col["items"])
            elif "items" in item:
                item["items"] = self.finish_items(item["items"])
            item.pop("__flat", None)
        return out

    # -- the other statements ---------------------------------------------------------------
    def parse_library(self) -> str | None:
        header = self.next()
        name = None
        if self.peek()["t"] in ("ID", "WORD", "STRING") and self.peek()["line"] == header["line"]:
            name = _php_string(self.next()["v"])
        choices: list[dict[str, Any]] = []

        def on(kind: str, t: Token) -> bool:
            if kind == "choice":
                c = self.choice(t)
                if c:
                    choices.append(c)
                return True
            if kind == "mod":
                self.warn(t["line"], f"A library holds only choices; @{t['v']} was skipped.")
                self.mod_value(t)
                return True
            return False

        self.body(header, on)
        if name is None:
            self.error(header["line"], "A library needs a name: library #sizes.")
            return None
        self.model.setdefault("choice_libraries", {})[name] = choices
        return name

    def parse_rule(self) -> int | None:
        header = self.next()
        rule: dict[str, Any] = {}
        if self.peek()["t"] == "WORD" and self.peek()["line"] == header["line"]:
            rule["action"] = str(self.next()["v"]).replace("-", "_").lower()
        rule["targets"] = []
        while self.peek()["t"] == "ID" and self.peek()["line"] == header["line"]:
            rule["targets"].append(self.next()["v"])

        def on(kind: str, t: Token) -> bool:
            if kind != "mod":
                return False
            if t["v"] in ("when", "value"):
                text = self.expression(self.raw_to_eol(t), t["line"])
                if text is not None:
                    rule[t["v"]] = text
            else:
                self.warn(t["line"], f"A rule has only @when and @value; @{t['v']} was skipped.")
                self.mod_value(t)
            return True

        self.body(header, on)
        if "action" not in rule:
            self.error(
                header["line"],
                "A rule needs an action: show, hide, require, optional, enable, disable, set or skip_to.",  # noqa: E501
            )
            return None
        self.model.setdefault("rules", []).append(
            order(rule, ("action", "targets", "when", "value"))
        )
        return len(self.model["rules"]) - 1

    def parse_scoring(self) -> None:
        header = self.next()
        scoring = self.model.get("scoring", {})

        def on(kind: str, t: Token) -> bool:
            if kind == "mod":
                has, value = self.mod_value(t)
                scoring[t["v"]] = value if has else True
                return True
            if kind == "child" and self.is_word(t, "outcome"):
                self.next()
                outcome: dict[str, Any] = {"id": f"outcome_{len(scoring.get('outcomes', [])) + 1}"}
                if self.peek()["t"] == "ID" and self.peek()["line"] == t["line"]:
                    outcome["id"] = self.next()["v"]

                def on_outcome(k2: str, m: Token) -> bool:
                    if k2 != "mod":
                        return False
                    if m["v"] == "when":
                        text = self.expression(self.raw_to_eol(m), m["line"])
                        if text is not None:
                            outcome["when"] = text
                    else:
                        has2, value2 = self.mod_value(m)
                        outcome[m["v"]] = value2 if has2 else True
                    return True

                self.body(t, on_outcome)
                scoring.setdefault("outcomes", []).append(outcome)
                return True
            return False

        self.body(header, on)
        self.model["scoring"] = scoring

    def parse_message_object(self, kind: str) -> int:
        header = self.next()
        key = kind + "s"
        obj: dict[str, Any] = {"id": f"{kind}_{len(self.model.get(key, [])) + 1}"}
        if self.peek()["t"] == "ID" and self.peek()["line"] == header["line"]:
            obj["id"] = self.next()["v"]
        if kind == "confirmation":
            obj["type"] = "message"
        fixed = M.FIXED_NAMES[kind]

        def on(k: str, t: Token) -> bool:
            if k != "mod":
                return False
            if t["v"] == "when":
                text = self.expression(self.raw_to_eol(t), t["line"])
                if text is not None:
                    obj["when"] = text
                return True
            has, value = self.mod_value(t)
            value = value if has else True
            if t["v"] in fixed:
                obj[t["v"]] = value
            else:
                obj.setdefault("props", {})[str(t["v"]).replace("-", "_")] = value
            return True

        self.body(header, on)
        self.model.setdefault(key, []).append(order(obj, fixed))
        return len(self.model[key]) - 1

    def parse_translation(self) -> str | None:  # noqa: C901
        header = self.next()
        lang = None
        if self.peek()["t"] in ("STRING", "WORD") and self.peek()["line"] == header["line"]:
            lang = _php_string(self.next()["v"])
        tr: dict[str, Any] = {}
        parts = {
            "page": "pages",
            "field": "fields",
            "confirmation": "confirmations",
            "outcome": "outcomes",
            "message": "messages",
        }
        allowed = {
            "pages": ("title", "description"),
            "fields": ("label", "help", "placeholder", "choices"),
            "confirmations": ("message",),
            "outcomes": ("message",),
        }

        def on(kind: str, t: Token) -> bool:
            if kind == "mod":
                _has, value = self.mod_value(t)
                if t["v"] in ("title", "description"):
                    tr[t["v"]] = _php_string(value)
                else:
                    self.warn(
                        t["line"],
                        f"A translation has @title and @description; @{t['v']} was skipped.",
                    )
                return True
            if kind != "child":
                return False
            w = str(t["v"]).lower()
            if w not in parts:
                return False
            self.next()
            ident = None
            if self.peek()["t"] in ("ID", "WORD") and self.peek()["line"] == t["line"]:
                ident = _php_string(self.next()["v"])
            if ident is None:
                self.error(t["line"], f"Say which {w} this translates: {w} #id.")
                return True
            if w == "message":
                if self.peek()["t"] == "STRING" and self.peek()["line"] == t["line"]:
                    tr.setdefault("messages", {})[ident] = self.next()["v"]
                return True
            part: dict[str, Any] = {}
            choices: dict[str, Any] = {}

            def on_part(k2: str, m: Token) -> bool:
                if k2 == "mod":
                    _h, value = self.mod_value(m)
                    key = "help" if m["v"] == "description" and w == "field" else str(m["v"])
                    part[key] = _php_string(value)
                    return True
                if k2 == "choice":
                    c = self.choice(m)
                    if c:
                        choices[c["value"]] = c["label"]
                    return True
                return False

            self.body(t, on_part)
            if choices:
                part["choices"] = choices
            keep = allowed[parts[w]]
            for k in part:
                if k not in keep:
                    self.warn(t["line"], f"A translated {w} has no @{k}; it was skipped.")
            tr.setdefault(parts[w], {})[ident] = {k: part[k] for k in keep if k in part}
            return True

        self.body(header, on)
        if lang is None:
            self.error(header["line"], 'Say which language: translation "es".')
            return None
        keys = ("title", "description", "pages", "fields", "confirmations", "outcomes", "messages")
        self.model.setdefault("translations", {})[lang] = order(tr, keys)
        return lang

    def parse_settings_block(self) -> None:
        header = self.next()
        line = header["line"]
        while not self.at_end():
            t = self.peek()
            if t["first"] and t["indent"] <= header["indent"] and t["line"] != line:
                break
            if t["t"] != "WORD":
                self.next()
                continue
            self.next()
            has, value = self.mod_value(t)
            key = COMPILER_SETTINGS.get(str(t["v"]), str(t["v"]))
            self.model.setdefault("settings", {})[key] = value if has else True
