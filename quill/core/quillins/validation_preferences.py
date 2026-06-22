"""Quillin preferences-page validation, split from validation.py (GATE-11).

The declarative ``contributes.preferences`` validators are a self-contained
cluster (only ``_validate_preferences`` is called externally). They share a
few private helpers and key-set constants with :mod:`quill.core.quillins.validation`;
that module imports ``_validate_preferences`` back at call scope so there is no
import-time cycle.
"""

from __future__ import annotations

from quill.core.quillins.validation import (
    _PREF_CONDITION_KEYS,
    _PREF_PAGE_KEYS,
    _PREF_SECTION_KEYS,
    _PREF_SETTING_KEYS,
    _PREF_SETTING_TYPES,
    _PREF_TAB_KEYS,
    _check_unknown_keys,
    _require_str,
)


def _validate_pref_condition(raw: object, label: str, errors: list[str]) -> None:
    if not isinstance(raw, dict):
        errors.append(f"{label} must be an object with 'setting' and 'equals'")
        return
    _check_unknown_keys(raw, _PREF_CONDITION_KEYS, label, errors)
    if "setting" not in raw:
        errors.append(f"{label} must have 'setting'")
    else:
        _require_str(raw.get("setting"), f"{label}.setting", errors)
    if "equals" not in raw:
        errors.append(f"{label} must have 'equals'")


def _validate_pref_settings_list(raw: object, label: str, errors: list[str]) -> None:
    if not isinstance(raw, list):
        errors.append(f"{label} must be an array")
        return
    for si, setting in enumerate(raw):
        slabel = f"{label}[{si}]"
        if not isinstance(setting, dict):
            errors.append(f"{slabel} must be an object")
            continue
        _check_unknown_keys(setting, _PREF_SETTING_KEYS, slabel, errors)
        _require_str(setting.get("key"), f"{slabel}.key", errors)
        _require_str(setting.get("label"), f"{slabel}.label", errors)
        stype = _require_str(setting.get("type"), f"{slabel}.type", errors)
        if stype is not None and stype not in _PREF_SETTING_TYPES:
            errors.append(
                f"{slabel}.type must be one of {sorted(_PREF_SETTING_TYPES)} (got '{stype}')"
            )
        if "default" not in setting:
            errors.append(f"{slabel} must have 'default'")
        if "description" not in setting:
            errors.append(f"{slabel} must have 'description'")
        if "search_keywords" in setting:
            kws = setting["search_keywords"]
            if not isinstance(kws, list):
                errors.append(f"{slabel}.search_keywords must be an array")
            else:
                for ki, kw in enumerate(kws):
                    if not isinstance(kw, str):
                        errors.append(f"{slabel}.search_keywords[{ki}] must be a string")
                    elif len(kw) > 64:
                        errors.append(
                            f"{slabel}.search_keywords[{ki}] must be at most 64 characters"
                        )
        if "visible_when" in setting:
            _validate_pref_condition(setting["visible_when"], f"{slabel}.visible_when", errors)
        if "enabled_when" in setting:
            _validate_pref_condition(setting["enabled_when"], f"{slabel}.enabled_when", errors)


def _validate_pref_sections_list(raw: object, label: str, errors: list[str]) -> None:
    if not isinstance(raw, list):
        errors.append(f"{label} must be an array")
        return
    for si, section in enumerate(raw):
        slabel = f"{label}[{si}]"
        if not isinstance(section, dict):
            errors.append(f"{slabel} must be an object")
            continue
        _check_unknown_keys(section, _PREF_SECTION_KEYS, slabel, errors)
        _require_str(section.get("id"), f"{slabel}.id", errors)
        title = _require_str(section.get("title"), f"{slabel}.title", errors)
        if title is not None and not (1 <= len(title) <= 80):
            errors.append(f"{slabel}.title must be 1-80 characters")
        if "settings" in section:
            _validate_pref_settings_list(section["settings"], f"{slabel}.settings", errors)
        if "visible_when" in section:
            _validate_pref_condition(section["visible_when"], f"{slabel}.visible_when", errors)
        if "enabled_when" in section:
            _validate_pref_condition(section["enabled_when"], f"{slabel}.enabled_when", errors)


def _validate_pref_tabs(raw: object, parent_label: str, errors: list[str]) -> None:
    if not isinstance(raw, list):
        errors.append(f"{parent_label}.tabs must be an array")
        return
    for ti, tab in enumerate(raw):
        tlabel = f"{parent_label}.tabs[{ti}]"
        if not isinstance(tab, dict):
            errors.append(f"{tlabel} must be an object")
            continue
        _check_unknown_keys(tab, _PREF_TAB_KEYS, tlabel, errors)
        _require_str(tab.get("id"), f"{tlabel}.id", errors)
        title = _require_str(tab.get("title"), f"{tlabel}.title", errors)
        if title is not None and not (1 <= len(title) <= 60):
            errors.append(f"{tlabel}.title must be 1-60 characters")
        if "description" not in tab:
            errors.append(f"{tlabel} must have 'description'")
        if "order" not in tab or not isinstance(tab.get("order"), int):
            errors.append(f"{tlabel} must have 'order' as an integer")
        if "sections" in tab:
            _validate_pref_sections_list(tab["sections"], f"{tlabel}.sections", errors)
        if "visible_when" in tab:
            _validate_pref_condition(tab["visible_when"], f"{tlabel}.visible_when", errors)
        if "enabled_when" in tab:
            _validate_pref_condition(tab["enabled_when"], f"{tlabel}.enabled_when", errors)


def _validate_preferences(raw: object, errors: list[str]) -> tuple[object, ...]:
    if not isinstance(raw, list):
        errors.append("contributes.preferences must be an array")
        return ()
    result: list[object] = []
    for index, page in enumerate(raw):
        label = f"contributes.preferences[{index}]"
        if not isinstance(page, dict):
            errors.append(f"{label} must be an object")
            continue
        _check_unknown_keys(page, _PREF_PAGE_KEYS, label, errors)
        _require_str(page.get("id"), f"{label}.id", errors)
        title = _require_str(page.get("title"), f"{label}.title", errors)
        if title is not None and not (1 <= len(title) <= 80):
            errors.append(f"{label}.title must be 1-80 characters")
        desc = _require_str(page.get("description"), f"{label}.description", errors)
        if desc is not None and len(desc) > 400:
            errors.append(f"{label}.description must be at most 400 characters")
        if "tabs" in page:
            _validate_pref_tabs(page["tabs"], label, errors)
        if "sections" in page:
            _validate_pref_sections_list(page["sections"], f"{label}.sections", errors)
        if "settings" in page:
            _validate_pref_settings_list(page["settings"], f"{label}.settings", errors)
        result.append(page)
    return tuple(result)
