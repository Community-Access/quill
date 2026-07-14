"""The lightweight structural equation navigator (no MathCAT required)."""

from __future__ import annotations

import pytest

pytest.importorskip("latex2mathml")

from quill.core.math.navigator import (
    EquationNavigator,
    MathNavigatorError,
    node_kind_label,
    parse_equation,
    read_aloud,
)


def test_parse_equation_accepts_bare_latex() -> None:
    root = parse_equation("a^2 + b^2 = c^2")
    assert root.tag.endswith("math")


def test_parse_equation_accepts_raw_mathml() -> None:
    mathml = '<math xmlns="http://www.w3.org/1998/Math/MathML"><mi>x</mi></math>'
    root = parse_equation(mathml)
    assert root.tag.endswith("math")


def test_parse_equation_rejects_malformed_input() -> None:
    with pytest.raises(MathNavigatorError):
        parse_equation("")


def test_parse_equation_rejects_malformed_mathml() -> None:
    with pytest.raises(MathNavigatorError):
        parse_equation("<math><mi>x</mi>")


# -- read_aloud ----------------------------------------------------------------


def test_read_aloud_pythagorean_theorem() -> None:
    root = parse_equation("a^2 + b^2 = c^2")
    assert read_aloud(root) == "a squared plus b squared equals c squared"


def test_read_aloud_slope_intercept() -> None:
    root = parse_equation("y = mx + b")
    assert read_aloud(root) == "y equals m x plus b"


def test_read_aloud_quadratic_formula() -> None:
    root = parse_equation(r"x = \frac{-b \pm \sqrt{b^2 - 4ac}}{2a}")
    assert read_aloud(root) == (
        "x equals the fraction minus b plus or minus the square root of "
        "b squared minus 4 a c over 2 a"
    )


def test_read_aloud_third_power_uses_cubed() -> None:
    root = parse_equation("x^3")
    assert read_aloud(root) == "x cubed"


def test_read_aloud_higher_power_spells_out() -> None:
    root = parse_equation("x^5")
    assert read_aloud(root) == "x to the power 5"


# -- EquationNavigator -----------------------------------------------------------


def test_navigator_root_label_and_reading() -> None:
    root = parse_equation("a^2 + b^2 = c^2")
    nav = EquationNavigator(root)
    assert nav.at_root()
    assert nav.reading() == "a squared plus b squared equals c squared"


def test_navigator_child_options_have_no_roles_for_a_plain_group() -> None:
    root = parse_equation("a^2 + b^2 = c^2")
    nav = EquationNavigator(root)
    options = nav.child_options()
    assert [opt.role for opt in options] == ["", "", "", "", ""]
    assert [opt.label for opt in options] == [
        "a squared",
        "plus",
        "b squared",
        "equals",
        "c squared",
    ]


def test_navigator_descend_into_fraction_shows_numerator_denominator() -> None:
    root = parse_equation(r"x = \frac{-b \pm \sqrt{b^2 - 4ac}}{2a}")
    nav = EquationNavigator(root)
    # child 0 = x, child 1 = equals, child 2 = the fraction
    fraction_index = next(i for i, opt in enumerate(nav.child_options()) if opt.label == "Fraction")
    nav.descend(fraction_index)
    assert nav.label() == "Fraction"
    roles = [opt.role for opt in nav.child_options()]
    assert roles == ["Numerator", "Denominator"]


def test_navigator_ascend_returns_to_parent() -> None:
    root = parse_equation(r"\frac{a}{b}")
    nav = EquationNavigator(root)
    nav.descend(0)
    assert not nav.at_root()
    nav.ascend()
    assert nav.at_root()


def test_navigator_ascend_at_root_is_a_noop() -> None:
    root = parse_equation("a^2")
    nav = EquationNavigator(root)
    nav.ascend()
    assert nav.at_root()


def test_navigator_reset_jumps_back_to_root() -> None:
    root = parse_equation(r"\frac{a}{b}")
    nav = EquationNavigator(root)
    nav.descend(0)
    nav.reset()
    assert nav.at_root()


def test_navigator_is_leaf_true_for_a_bare_variable() -> None:
    # latex2mathml wraps even a lone variable in a single-child <mrow>; the
    # navigator collapses that transparently so this is a leaf, not a "Group".
    root = parse_equation("x")
    nav = EquationNavigator(root)
    assert nav.is_leaf()
    assert nav.child_options() == []


def test_navigator_is_leaf_false_for_a_fraction() -> None:
    root = parse_equation(r"\frac{a}{b}")
    nav = EquationNavigator(root)
    assert not nav.is_leaf()


# -- node_kind_label -------------------------------------------------------------


def test_node_kind_label_operator_reads_as_word() -> None:
    root = parse_equation("a = b")
    nav = EquationNavigator(root)
    equals_option = next(opt for opt in nav.child_options() if opt.label == "equals")
    assert equals_option is not None


def test_node_kind_label_unknown_element_falls_back_to_tag_name() -> None:
    import xml.etree.ElementTree as ET

    element = ET.fromstring("<mfenced><mi>x</mi></mfenced>")
    assert node_kind_label(element) == "mfenced"
