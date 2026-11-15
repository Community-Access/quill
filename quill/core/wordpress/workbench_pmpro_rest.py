"""Paid Memberships Pro's own REST namespace, ``pmpro/v1`` (complete.md 10B.3).

PMPro has two doors. Its **abilities** (``wp-abilities/v1``, WordPress 6.9
and PMPro 3.9 or later) are what :mod:`~quill.core.wordpress.workbench_pmpro`
reads first. Its older **REST routes** (``pmpro/v1``, every PMPro since 2.x)
are used here for three things:

- a member's levels, as the fallback when the site exposes no abilities
  (:func:`member_levels`);
- **Has Access**: whether a person may see a post or page
  (:func:`has_access`, ``pmpro/v1/has_membership_access``);
- **Discount Codes**: read one code by its code, and create one after a
  preview (:func:`read_discount_code`, :func:`discount_preview`,
  :func:`create_discount_code`). ``pmpro/v1`` has no route that lists every
  code, so the list says so and opens Memberships > Discount Codes in wp-admin
  unless the site offers a discount-codes ability.

The site checks the caller's PMPro capability on every call. Nothing here
reads or sends payment details. Wx-free.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from quill.core.wordpress.api import WordPressApiError
from quill.core.wordpress.site import plain_text
from quill.core.wordpress.workbench_no_rest import ADMIN_SCREENS, admin_link
from quill.core.wordpress.workbench_rows import WbRow

if TYPE_CHECKING:
    from quill.core.wordpress.api import WordPressApi
    from quill.core.wordpress.workbench_load import SiteContext

__all__ = [
    "DISCOUNT_ABILITY",
    "PMPRO_NAMESPACE",
    "AccessAnswer",
    "DiscountSpec",
    "create_discount_code",
    "discount_body",
    "discount_preview",
    "discount_row",
    "has_access",
    "load_discount_codes",
    "member_levels",
    "read_discount_code",
]

PMPRO_NAMESPACE = "pmpro/v1"
DISCOUNT_ABILITY = "pmpro/discount-codes-query"
_ACCESS = "pmpro/v1/has_membership_access"
_LEVELS_FOR_USER = "pmpro/v1/get_membership_levels_for_user"
_DISCOUNT = "pmpro/v1/discount_code"


def _items(raw: Any) -> list[dict[str, Any]]:
    if isinstance(raw, Mapping):
        raw = list(raw.values()) if all(isinstance(v, Mapping) for v in raw.values()) else [raw]
    return [dict(item) for item in raw or [] if isinstance(item, Mapping)]


def member_levels(api: WordPressApi, user_id: int) -> list[dict[str, Any]]:
    """The person's current levels through ``pmpro/v1`` (no past ones: the route has none)."""
    raw = api.get(_LEVELS_FOR_USER, user_id=user_id)
    return [level for level in _items(raw) if level.get("id") or level.get("name")]


@dataclass(frozen=True)
class AccessAnswer:
    """Whether a person may see a post, and through which levels."""

    allowed: bool
    levels: tuple[str, ...] = ()

    def sentence(self, person: str, post: str, site: str) -> str:
        if self.allowed and self.levels:
            return f"{person} can see {post} on {site}, through {', '.join(self.levels)}."
        if self.allowed:
            return f"{person} can see {post} on {site}."
        if self.levels:
            return (
                f"{person} cannot see {post} on {site}. It needs one of these levels: "
                f"{', '.join(self.levels)}."
            )
        return f"{person} cannot see {post} on {site}."


def _access_from(raw: Any) -> AccessAnswer:
    """PMPro answers a bool, or ``[bool, level ids, level names]`` when asked for levels."""
    if isinstance(raw, bool):
        return AccessAnswer(raw)
    if isinstance(raw, Mapping):
        allowed = raw.get("has_access", raw.get("access"))
        names = raw.get("levels") or raw.get("level_names") or []
        return AccessAnswer(bool(allowed), tuple(str(n) for n in names if n))
    if isinstance(raw, list) and raw:
        names = raw[2] if len(raw) > 2 and isinstance(raw[2], list) else []
        return AccessAnswer(bool(raw[0]), tuple(str(n) for n in names if n))
    if isinstance(raw, (int, str)):
        return AccessAnswer(str(raw).strip().lower() in ("1", "true", "yes"))
    raise WordPressApiError("Paid Memberships Pro did not say whether this person has access.")


def has_access(api: WordPressApi, user_id: int, post_id: int) -> AccessAnswer:
    """Whether *user_id* may see *post_id*, as PMPro decides it."""
    return _access_from(api.get(_ACCESS, user_id=user_id, post_id=post_id))


# -- discount codes ----------------------------------------------------------------------


@dataclass(frozen=True)
class DiscountSpec:
    """A new discount code: the code, the levels it applies to and its terms."""

    code: str
    levels: tuple[int, ...]
    initial_payment: str = "0"
    uses: int = 0
    starts: str = ""
    expires: str = ""


def discount_body(spec: DiscountSpec) -> dict[str, Any]:
    """The ``pmpro/v1/discount_code`` body: one level row per level, no recurring billing."""
    return {
        "code": spec.code,
        "uses": spec.uses,
        "starts": spec.starts,
        "expires": spec.expires,
        "levels": [
            {
                "level": level,
                "initial_payment": spec.initial_payment,
                "billing_amount": "0",
                "cycle_number": "0",
                "cycle_period": "Month",
                "billing_limit": "0",
                "trial_amount": "0",
                "trial_limit": "0",
                "expiration_number": "0",
                "expiration_period": "Day",
            }
            for level in spec.levels
        ],
    }


def discount_preview(spec: DiscountSpec, site: str, level_names: Mapping[int, str]) -> list[str]:
    """What the code will be, one line each, before anything is sent."""
    uses = "unlimited uses" if spec.uses <= 0 else f"{spec.uses} uses"
    lines = [
        f"Code {spec.code} on {site}: {uses}, starts {spec.starts or 'today'}, "
        f"expires {spec.expires or 'never'}."
    ]
    for level in spec.levels:
        name = level_names.get(level) or f"Level {level}"
        lines.append(
            f"{name} (level {level}): initial payment {spec.initial_payment}, "
            "no recurring billing, no expiry."
        )
    return lines


def discount_row(site: str, raw: Mapping[str, Any], site_url: str = "") -> WbRow:
    code = str(raw.get("code") or f"Code {raw.get('id', '')}")
    uses = str(raw.get("uses") or "0")
    used = str(raw.get("used") or raw.get("times_used") or "")
    starts = str(raw.get("starts") or "")
    expires = str(raw.get("expires") or "")
    levels = raw.get("levels") or []
    names = [
        plain_text(str(level.get("name") or f"Level {level.get('level') or level.get('id')}"))
        for level in levels
        if isinstance(level, Mapping)
    ]
    cells = {
        "code": code,
        "uses": "unlimited" if uses in ("", "0") else uses,
        "used": used,
        "starts": starts,
        "expires": expires or "never",
        "levels": ", ".join(names),
    }
    detail = (
        f"Discount code {code}: {cells['uses']} uses"
        + (f", used {used} times" if used else "")
        + f", starts {starts or 'not said'}, expires {cells['expires']}"
        + (f", for {cells['levels']}" if names else "")
        + "."
    )
    return WbRow(
        "pmpro",
        site,
        str(raw.get("id") or code),
        cells,
        detail,
        link=admin_link(site_url, "pmpro_discount_codes"),
        subkind="discount_code",
        raw=dict(raw),
    )


def read_discount_code(api: WordPressApi, code: str) -> dict[str, Any]:
    raw = api.get(_DISCOUNT, code=code)
    if not isinstance(raw, Mapping) or not (raw.get("code") or raw.get("id")):
        raise WordPressApiError(f"There is no discount code {code} on {api.site_name}.")
    return dict(raw)


def create_discount_code(api: WordPressApi, spec: DiscountSpec) -> dict[str, Any]:
    raw = api.post(_DISCOUNT, discount_body(spec))
    return dict(raw) if isinstance(raw, Mapping) else {"code": spec.code}


def _note(ctx: SiteContext) -> WbRow:
    screen = ADMIN_SCREENS["pmpro_discount_codes"]
    link = admin_link(ctx.url, "pmpro_discount_codes")
    where = f" Enter opens {screen.name} in wp-admin for the full list." if link else ""
    return WbRow(
        "pmpro",
        ctx.name,
        "discount-codes-note",
        {"code": "Every code", "uses": "", "used": "", "starts": "", "expires": "", "levels": ""},
        f"{screen.why} Look Up a Discount Code reads one; New Discount Code makes one after a "
        f"preview.{where}",
        link=link,
        subkind="discount_note",
    )


def load_discount_codes(ctx: SiteContext) -> list[WbRow]:
    """Every code when the site offers the ability; otherwise the row that says why not."""
    from quill.core.wordpress.abilities import NAMESPACE, list_abilities, run_ability

    rows: list[WbRow] = []
    if ctx.info is None or ctx.info.supports(NAMESPACE):
        try:
            found = {a.name: a for a in list_abilities(ctx.api)}
        except WordPressApiError:
            found = {}
        ability = found.get(DISCOUNT_ABILITY)
        if ability is not None and ability.readonly:
            answer = run_ability(ctx.api, ability, {"limit": 100, "page": 1})
            items: Sequence[Any] = answer.get("items", []) if isinstance(answer, Mapping) else []
            rows = [discount_row(ctx.name, i, ctx.url) for i in items if isinstance(i, Mapping)]
            return rows
    if ctx.info is not None and not ctx.info.supports(PMPRO_NAMESPACE):
        return [
            WbRow(
                "fact",
                ctx.name,
                "pmpro-not-available",
                {"fact": "Paid Memberships Pro", "value": "Not on this site"},
                f"{ctx.name} does not offer Paid Memberships Pro's REST routes (pmpro/v1).",
            )
        ]
    return [_note(ctx)]
