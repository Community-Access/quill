"""WooCommerce > Settings in the Workbench, through ``wc/v3/settings`` (Package 10).

Every settings group the shop lists (General, Products, Tax, Shipping,
Accounts, Emails and each email, Advanced, and whatever an extension adds)
is read, and each setting becomes a row: its group, its label and its value
in words. **Change Setting** offers a choice where WooCommerce gives one
(a select, radio or check box) and a typed value otherwise, previews the old
and new value, and sends ``POST wc/v3/settings/{group}/{id}`` with
``value``. A password-style setting (an API key, say) is never read aloud,
copied into a row, or changed here; its row says so and wp-admin changes it.
Wx-free.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from quill.core.wordpress.api import WordPressApiError
from quill.core.wordpress.plugin_shop_seo import SHOP_NAMESPACE, ShopValueError
from quill.core.wordpress.workbench_rows import WbRow

__all__ = [
    "SECRET_TYPES",
    "SettingChoice",
    "choices_for",
    "load_settings_rows",
    "setting_preview",
    "setting_row",
    "spoken_value",
    "value_to_send",
]

SECRET_TYPES = frozenset({"password"})
"""Setting types never read aloud, kept in a row, or changed from the Workbench."""

_HIDDEN = "hidden: a password-style setting is changed in wp-admin"


def _options(raw: Mapping[str, Any]) -> dict[str, str]:
    options = raw.get("options")
    return {str(k): str(v) for k, v in options.items()} if isinstance(options, Mapping) else {}


def spoken_value(raw: Mapping[str, Any]) -> str:
    """The setting's value as a person would say it."""
    kind = str(raw.get("type", "") or "")
    value = raw.get("value")
    if kind in SECRET_TYPES:
        return _HIDDEN
    if kind == "checkbox":
        return "on" if str(value) == "yes" else "off"
    options = _options(raw)
    if isinstance(value, list):
        return ", ".join(options.get(str(v), str(v)) for v in value) or "none"
    if options:
        return options.get(str(value), str(value) or "not set")
    text = str(value if value is not None else "").strip()
    return text or "not set"


def setting_row(group_id: str, group_label: str, raw: Mapping[str, Any], site: str) -> WbRow:
    kind = str(raw.get("type", "") or "")
    label = str(raw.get("label", "") or raw.get("id", ""))
    said = spoken_value(raw)
    secret = kind in SECRET_TYPES
    return WbRow(
        kind="shop_setting",
        site=site,
        key=f"{group_id}/{raw.get('id', '')}",
        cells={"group": group_label, "setting": label, "value": said},
        detail=(
            f"WooCommerce > Settings > {group_label} > {label}: {said}. "
            + str(raw.get("description", "") or "").strip()
        ).strip(),
        subkind="woocommerce",
        raw={
            "group": group_id,
            "group_label": group_label,
            "id": str(raw.get("id", "") or ""),
            "label": label,
            "type": kind,
            "value": None if secret else raw.get("value"),
            "options": _options(raw),
            "said": said,
        },
    )


def load_settings_rows(api: Any, site: str) -> list[WbRow]:
    """Every group's settings, group by group; a group that cannot be read is said, not hidden."""
    groups = api.get(f"{SHOP_NAMESPACE}/settings")
    rows: list[WbRow] = []
    for group in groups if isinstance(groups, list) else []:
        if not isinstance(group, Mapping) or not group.get("id"):
            continue
        group_id, group_label = str(group["id"]), str(group.get("label") or group["id"])
        try:
            found = api.get(f"{SHOP_NAMESPACE}/settings/{group_id}")
        except WordPressApiError as exc:
            rows.append(
                WbRow(
                    kind="shop_setting",
                    site=site,
                    key=f"{group_id}/",
                    cells={"group": group_label, "setting": "(the whole group)", "value": ""},
                    detail=f"{group_label} could not be read: {exc.plain}",
                    subkind="woocommerce",
                    raw={"group": group_id, "group_label": group_label, "id": ""},
                )
            )
            continue
        for raw in found if isinstance(found, list) else []:
            if isinstance(raw, Mapping) and raw.get("id"):
                rows.append(setting_row(group_id, group_label, raw, site))
    return rows


@dataclass(frozen=True)
class SettingChoice:
    """How Change Setting asks: a list of (value, words), or typed text when empty."""

    values: tuple[tuple[str, str], ...]


def choices_for(raw: Mapping[str, Any]) -> SettingChoice:
    kind = str(raw.get("type", "") or "")
    if kind in SECRET_TYPES:
        raise ShopValueError(
            f"{raw.get('label', 'This setting')} is a password-style setting, so QUILL neither "
            "reads it aloud nor changes it. Change it in WooCommerce > Settings in wp-admin."
        )
    if kind == "checkbox":
        return SettingChoice((("yes", "on"), ("no", "off")))
    if kind in ("select", "radio", "single_select_country", "single_select_page"):
        options = raw.get("options") or {}
        return SettingChoice(tuple((str(k), str(v)) for k, v in dict(options).items()))
    if kind == "multiselect" or kind == "multi_select_countries":
        raise ShopValueError(
            f"{raw.get('label', 'This setting')} takes several values at once; change it in "
            "WooCommerce > Settings in wp-admin, where each is a check box."
        )
    return SettingChoice(())


def value_to_send(raw: Mapping[str, Any], answer: str) -> Any:
    """The value in the type WooCommerce stores; a number setting must be a number."""
    kind = str(raw.get("type", "") or "")
    text = answer.strip()
    if kind == "number":
        try:
            float(text)
        except ValueError as exc:
            raise ShopValueError(f"{raw.get('label', 'This setting')} needs a number.") from exc
    if kind == "email" and text and "@" not in text:
        raise ShopValueError(f"{raw.get('label', 'This setting')} needs an email address.")
    return text


def setting_preview(raw: Mapping[str, Any], new: Any, site: str) -> list[str]:
    after = spoken_value({**raw, "value": new})
    return [
        f"WooCommerce > Settings > {raw.get('group_label', '')} > {raw.get('label', '')} on "
        f"{site}: {raw.get('said', 'not set')} becomes {after}.",
        "It takes effect for shoppers at once. Nothing else is changed.",
    ]


def setting_route(raw: Mapping[str, Any]) -> str:
    return f"{SHOP_NAMESPACE}/settings/{raw.get('group', '')}/{raw.get('id', '')}"
