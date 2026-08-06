"""Catalog integrity: every recipe must compile, match its own sample, and read well.

A recipe that fails on its own sample would teach a screen-reader user that
the tool lies; these tests make that structurally impossible.
"""

from __future__ import annotations

import re

import pytest

from quill.core.regex_helper import CATEGORIES, RECIPES, RegexRecipe, recipes_by_category

_VALID_DIFFICULTIES = {"basic", "intermediate", "advanced"}


def test_catalog_has_at_least_100_recipes() -> None:
    assert len(RECIPES) >= 100


def test_every_category_is_non_empty() -> None:
    grouped = recipes_by_category()
    assert tuple(grouped) == CATEGORIES
    for category, recipes in grouped.items():
        assert recipes, f"category {category!r} has no recipes"


def test_every_recipe_category_is_known() -> None:
    for recipe in RECIPES:
        assert recipe.category in CATEGORIES, recipe.name


def test_recipe_names_are_unique() -> None:
    names = [recipe.name for recipe in RECIPES]
    assert len(names) == len(set(names))


def test_difficulties_are_valid() -> None:
    for recipe in RECIPES:
        assert recipe.difficulty in _VALID_DIFFICULTIES, recipe.name


@pytest.mark.parametrize("recipe", RECIPES, ids=lambda r: r.name)
def test_every_pattern_compiles(recipe: RegexRecipe) -> None:
    re.compile(recipe.pattern)


@pytest.mark.parametrize("recipe", RECIPES, ids=lambda r: r.name)
def test_every_sample_contains_a_match(recipe: RegexRecipe) -> None:
    assert re.search(recipe.pattern, recipe.sample) is not None, (
        f"{recipe.name}: pattern {recipe.pattern!r} finds nothing in its own sample"
    )


@pytest.mark.parametrize(
    "recipe",
    [r for r in RECIPES if r.replace_template is not None],
    ids=lambda r: r.name,
)
def test_replace_templates_survive_re_sub(recipe: RegexRecipe) -> None:
    assert recipe.replace_template is not None
    re.sub(recipe.pattern, recipe.replace_template, recipe.sample)
    assert recipe.replace_note, f"{recipe.name}: replace_template without a replace_note"


def test_capture_and_replace_recipes_all_have_templates() -> None:
    for recipe in recipes_by_category()["Capture and replace"]:
        assert recipe.replace_template is not None, recipe.name
        assert recipe.replace_note, recipe.name


def test_explanations_are_sentences_not_jargon() -> None:
    for recipe in RECIPES:
        assert recipe.explanation.strip().endswith("."), recipe.name
        assert len(recipe.explanation.split()) >= 5, recipe.name
