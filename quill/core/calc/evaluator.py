"""Safe scientific expression evaluator for the QUILL Calculator.

Evaluates arithmetic and scientific expressions -- ``4 + 12 / 2``,
``sqrt(264)``, ``sin(pi/6)``, ``5!``, ``2^10`` -- plus the natural-language forms
users actually type (``what is the square root of 264``, ``10 percent of
500``, ``15% of 240``). It parses the text to a Python AST and walks only an
allowlist of node types, operators, functions, and constants; there is **no
``eval``**, no attribute access, no name lookup outside the allowlist, so text
pulled from a document can never execute code.

Pure, wx-free, strict-typed. Raises :class:`CalculatorError` (coded) on anything
it cannot evaluate, with a plain-language message suitable to speak.
"""

from __future__ import annotations

import ast
import math
import operator
import re
from collections.abc import Callable
from typing import Any, cast

from quill.core.error_codes import CodedError


class CalculatorError(CodedError):
    """The expression could not be evaluated (syntax, unknown name, math error)."""

    code = "QUILL-CALC-EVAL-INVALID"


Number = float | int

_BIN_OPS: dict[type[ast.operator], Callable[[Any, Any], Any]] = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}
_UNARY_OPS: dict[type[ast.unaryop], Callable[[Any], Any]] = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}

_CONSTANTS: dict[str, float] = {
    "pi": math.pi,
    "e": math.e,
    "tau": math.tau,
    "inf": math.inf,
}


def _factorial(x: Number) -> int:
    if x < 0 or (isinstance(x, float) and not x.is_integer()):
        raise CalculatorError("Factorial needs a whole number that is zero or more.")
    return math.factorial(int(x))


def _log(x: Number, base: Number | None = None) -> float:
    return math.log(x) if base is None else math.log(x, base)


#: The allowlisted functions. Trig is in radians; ``sind``/``cosd``/``tand`` take
#: degrees for convenience. Everything here is a plain math function -- no I/O.
_FUNCTIONS: dict[str, Callable[..., Number]] = {
    "sqrt": math.sqrt,
    "cbrt": lambda x: math.copysign(abs(x) ** (1 / 3), x),
    "abs": abs,
    "round": round,
    "floor": math.floor,
    "ceil": math.ceil,
    "trunc": math.trunc,
    "exp": math.exp,
    "log": _log,  # natural log, or log(x, base)
    "ln": math.log,
    "log10": math.log10,
    "log2": math.log2,
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
    "asin": math.asin,
    "acos": math.acos,
    "atan": math.atan,
    "atan2": math.atan2,
    "sind": lambda x: math.sin(math.radians(x)),
    "cosd": lambda x: math.cos(math.radians(x)),
    "tand": lambda x: math.tan(math.radians(x)),
    "sinh": math.sinh,
    "cosh": math.cosh,
    "tanh": math.tanh,
    "degrees": math.degrees,
    "radians": math.radians,
    "gcd": math.gcd,
    "hypot": math.hypot,
    "factorial": _factorial,
    "fact": _factorial,
    "min": min,
    "max": max,
    "sum": lambda *a: sum(a),
    "pow": pow,
    "mod": operator.mod,
    "sign": lambda x: (x > 0) - (x < 0),
}


# -- natural-language normalization ------------------------------------------


def normalize(expression: str) -> str:
    """Turn friendly phrasing into a math expression the parser understands.

    Handles ``what is``/``calculate`` lead-ins, ``x`` as multiply, ``^`` as
    power, ``percent of`` / ``% of`` (``10% of 500`` -> ``(10/100)*500``), a bare
    trailing ``%`` (``25%`` -> ``(25/100)``), and ``square/cube root of N``.
    """
    text = expression.strip().lower()
    # Strip a conversational lead-in and any trailing question mark.
    text = re.sub(r"^\s*(what\s+is|whats|what's|calculate|compute|evaluate)\b[:\s]*", "", text)
    text = re.sub(r"^the\s+", "", text)  # "...the square root of" -> "square root of"
    text = text.rstrip("?").strip()
    text = text.replace("plus", "+").replace("minus", "-")
    text = re.sub(r"\btimes\b|\bmultiplied by\b", "*", text)
    text = re.sub(r"\bdivided by\b|\bover\b", "/", text)
    # "square root of N" / "cube root of N" -> sqrt(N) / cbrt(N), wrapping the
    # following number or parenthesized group so the result actually parses.
    text = re.sub(r"\bsquare\s+root\s+of\s+(\([^)]*\)|[\d][\d.,]*)", r"sqrt(\1)", text)
    text = re.sub(r"\bcube\s+root\s+of\s+(\([^)]*\)|[\d][\d.,]*)", r"cbrt(\1)", text)
    text = re.sub(r"\bsquared\b", "**2", text)
    text = re.sub(r"\bcubed\b", "**3", text)
    # Factorial postfix: "5!" -> factorial(5).
    text = re.sub(r"(\d+)\s*!", r"factorial(\1)", text)
    # "A percent of B" / "A% of B" -> (A/100)*B
    text = re.sub(r"(\d+(?:\.\d+)?)\s*(?:percent|%)\s+of\s+", r"(\1/100)*", text)
    # A bare trailing percent: "25%" -> (25/100)
    text = re.sub(r"(\d+(?:\.\d+)?)\s*%", r"(\1/100)", text)
    # "x" used as a multiply sign between numbers/parens (not inside a name).
    text = re.sub(r"(?<=[\d)\s])[x×](?=[\d(\s])", "*", text)
    text = text.replace("×", "*").replace("÷", "/")
    text = text.replace("^", "**")
    return text.strip()


# -- evaluation ---------------------------------------------------------------


def _eval_node(node: ast.AST) -> Number:
    if isinstance(node, ast.Expression):
        return _eval_node(node.body)
    if isinstance(node, ast.Constant):
        if isinstance(node.value, bool) or not isinstance(node.value, (int, float)):
            raise CalculatorError("Only numbers are allowed.")
        return node.value
    if isinstance(node, ast.BinOp):
        bin_op = _BIN_OPS.get(type(node.op))
        if bin_op is None:
            raise CalculatorError("That operator is not supported.")
        return cast(Number, bin_op(_eval_node(node.left), _eval_node(node.right)))
    if isinstance(node, ast.UnaryOp):
        un_op = _UNARY_OPS.get(type(node.op))
        if un_op is None:
            raise CalculatorError("That operator is not supported.")
        return cast(Number, un_op(_eval_node(node.operand)))
    if isinstance(node, ast.Name):
        if node.id in _CONSTANTS:
            return _CONSTANTS[node.id]
        raise CalculatorError(f"'{node.id}' is not a known name.")
    if isinstance(node, ast.Call):
        return _eval_call(node)
    raise CalculatorError("That expression is not something I can calculate.")


def _eval_call(node: ast.Call) -> Number:
    if not isinstance(node.func, ast.Name):
        raise CalculatorError("That function call is not supported.")
    name = node.func.id
    func = _FUNCTIONS.get(name)
    if func is None:
        raise CalculatorError(f"'{name}' is not a known function.")
    if node.keywords:
        raise CalculatorError("Functions here take plain values, not named arguments.")
    args = [_eval_node(a) for a in node.args]
    try:
        return cast(Number, func(*args))
    except CalculatorError:
        raise
    except (ValueError, TypeError, ZeroDivisionError, OverflowError) as error:
        raise CalculatorError(f"{name}: {error}") from error


def evaluate(expression: str) -> Number:
    """Evaluate a scientific/natural-language expression to a number.

    Raises :class:`CalculatorError` on empty input, a parse failure, an unknown
    name/function, or a math error (division by zero, domain error, overflow).
    """
    normalized = normalize(expression)
    if not normalized:
        raise CalculatorError("There is nothing to calculate.")
    try:
        tree = ast.parse(normalized, mode="eval")
    except SyntaxError as error:
        raise CalculatorError("That does not look like a valid calculation.") from error
    try:
        result = _eval_node(tree)
    except ZeroDivisionError as error:
        raise CalculatorError("You cannot divide by zero.") from error
    except OverflowError as error:
        raise CalculatorError("That result is too large to calculate.") from error
    if isinstance(result, bool) or not isinstance(result, (int, float)):
        raise CalculatorError("That did not produce a number.")
    if isinstance(result, float) and (math.isnan(result) or math.isinf(result)):
        raise CalculatorError("That result is not a finite number.")
    return result


def format_result(value: Number) -> str:
    """A clean, speakable rendering of a result: integers show with no decimal
    point; other values trim trailing zeros and cap at 10 significant places."""
    if isinstance(value, int) or (isinstance(value, float) and value.is_integer()):
        return str(int(value))
    text = f"{value:.10g}"
    return text
