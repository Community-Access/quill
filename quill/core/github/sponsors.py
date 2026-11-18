"""People > Sponsorships, and a person's Sponsor node (GitHub PRD 14.3).

GitHub Sponsors lets you pay someone who maintains open source, monthly or
once. Here it is read as sentences and acted on with care, because it spends
real money:

* **People > Sponsorships** lists who you sponsor ("You sponsor sam: $5 a
  month, since 2025-02-01.") and who sponsors you ("jo sponsors you: $10 a
  month, since 2026-03-04."), the second as person rows.
* **Sponsor**, under any person, says whether they take sponsorships, their
  description, whether you sponsor them already, and each tier as a row:
  "$5 a month: Coffee. Keeps the lights on."
* **Sponsor at This Tier...** on a tier asks public or private, then has you
  type their login before GitHub charges anything (``createSponsorship``).
* **Cancel Sponsorship...** stops a monthly sponsorship after asking
  (``cancelSponsorship``).

Takes the Workbench's :class:`~quill.core.github.workbench_api.GitHubApi`.
wx-free and strict-typed.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from quill.core.error_codes import CodedError
from quill.core.github.explore_models import ExploreRow
from quill.core.github.workbench_api import GitHubApi

__all__ = [
    "SponsorError",
    "cancel_sponsorship",
    "fetch_sponsor_page",
    "fetch_sponsorships",
    "price_words",
    "sponsor",
]


class SponsorError(CodedError):
    """Sponsorships could not be read or changed; the message is said."""

    code = "QUILL-GITHUB-SPONSORS"


_TIER = "tier { id name description monthlyPriceInDollars isOneTime }"
_MINE = f"""
query {{
  viewer {{
    sponsorshipsAsSponsor(first: 100, activeOnly: true) {{
      nodes {{
        createdAt
        sponsorable {{ ... on User {{ login }} ... on Organization {{ login }} }}
        {_TIER}
      }}
    }}
    sponsorshipsAsMaintainer(first: 100, activeOnly: true) {{
      nodes {{
        createdAt
        sponsorEntity {{ ... on User {{ login }} ... on Organization {{ login }} }}
        {_TIER}
      }}
    }}
  }}
}}
"""
_PAGE = """
query($login: String!) {
  repositoryOwner(login: $login) {
    ... on Sponsorable {
      hasSponsorsListing
      viewerIsSponsoring
      sponsorsListing {
        shortDescription
        tiers(first: 30) {
          nodes { id name description monthlyPriceInDollars isOneTime isCustomAmount }
        }
      }
    }
  }
}
"""
_CREATE = """
mutation($login: String!, $tier: ID!, $privacy: SponsorshipPrivacy!) {
  createSponsorship(
    input: {sponsorableLogin: $login, tierId: $tier, privacyLevel: $privacy}
  ) { sponsorship { createdAt } }
}
"""
_CANCEL = """
mutation($login: String!) {
  cancelSponsorship(input: {sponsorableLogin: $login}) { clientMutationId }
}
"""


def price_words(tier: Mapping[str, Any]) -> str:
    dollars = tier.get("monthlyPriceInDollars")
    amount = f"${dollars:,}" if isinstance(dollars, int) else "an amount"
    return f"{amount} once" if tier.get("isOneTime") else f"{amount} a month"


def _login(value: object) -> str:
    return str(value.get("login") or "") if isinstance(value, Mapping) else ""


def _nodes(value: object) -> list[Mapping[str, Any]]:
    nodes = value.get("nodes") if isinstance(value, Mapping) else None
    return [node for node in nodes or () if isinstance(node, Mapping)]


def fetch_sponsorships(api: GitHubApi, warnings: list[str] | None = None) -> list[ExploreRow]:
    data = api.graphql(_MINE, {})
    viewer = data.get("viewer") if isinstance(data, Mapping) else None
    if not isinstance(viewer, Mapping):
        raise SponsorError("GitHub sent nothing about your sponsorships.")
    rows = []
    for node in _nodes(viewer.get("sponsorshipsAsSponsor")):
        who = _login(node.get("sponsorable"))
        tier = node.get("tier") if isinstance(node.get("tier"), Mapping) else {}
        since = str(node.get("createdAt") or "")[:10]
        label = f"You sponsor {who}: {price_words(tier or {})}, since {since}."
        url = f"https://github.com/sponsors/{who}"
        rows.append(ExploreRow(label, f"{label}\n{url}", url, "", "sponsorship", who))
    for node in _nodes(viewer.get("sponsorshipsAsMaintainer")):
        who = _login(node.get("sponsorEntity"))
        tier = node.get("tier") if isinstance(node.get("tier"), Mapping) else {}
        since = str(node.get("createdAt") or "")[:10]
        label = f"{who} sponsors you: {price_words(tier or {})}, since {since}."
        url = f"https://github.com/{who}"
        rows.append(ExploreRow(label, f"{label}\n{url}", url, "", "person", who))
    if not rows and warnings is not None:
        warnings.append("You sponsor nobody, and nobody sponsors you, on GitHub Sponsors.")
    return rows


def fetch_sponsor_page(api: GitHubApi, login: str) -> list[ExploreRow]:
    """Whether *login* takes sponsorships, whether you sponsor them, and each tier."""
    data = api.graphql(_PAGE, {"login": login})
    owner = data.get("repositoryOwner") if isinstance(data, Mapping) else None
    url = f"https://github.com/sponsors/{login}"
    if not isinstance(owner, Mapping):
        raise SponsorError(f"GitHub has no account called {login}.")
    if not owner.get("hasSponsorsListing"):
        label = f"{login} does not take sponsorships on GitHub Sponsors."
        return [ExploreRow(label, label, f"https://github.com/{login}", "", "sponsor_note", login)]
    listing = (
        owner.get("sponsorsListing") if isinstance(owner.get("sponsorsListing"), Mapping) else {}
    )
    rows = []
    state = (
        "You sponsor them already."
        if owner.get("viewerIsSponsoring")
        else "You do not sponsor them yet."
    )
    about = str((listing or {}).get("shortDescription") or "").strip()
    head = f"{login} takes sponsorships. {state}" + (f" {about}" if about else "")
    rows.append(ExploreRow(head, f"{head}\n{url}", url, "", "sponsor_note", login))
    for tier in _nodes((listing or {}).get("tiers")):
        if tier.get("isCustomAmount"):
            continue
        name = str(tier.get("name") or "")
        text = str(tier.get("description") or "").strip().splitlines()
        label = f"{price_words(tier)}: {name}." + (f" {text[0]}" if text else "")
        detail = f"{label}\n" + "\n".join(text[1:]) + f"\n{url}"
        rows.append(
            ExploreRow(label, detail.strip(), url, login, "sponsor_tier", str(tier.get("id") or ""))
        )
    return rows


def sponsor(api: GitHubApi, login: str, tier_id: str, price: str, *, public: bool) -> str:
    """Sponsor *login* at the tier chosen. GitHub charges the payment method on file."""
    api.graphql(
        _CREATE, {"login": login, "tier": tier_id, "privacy": "PUBLIC" if public else "PRIVATE"}
    )
    who = "publicly" if public else "privately"
    return f"You now sponsor {login} {who}, {price}. GitHub sends you a receipt."


def cancel_sponsorship(api: GitHubApi, login: str) -> str:
    api.graphql(_CANCEL, {"login": login})
    return f"Cancelled your sponsorship of {login}. Nothing more is charged for it."
