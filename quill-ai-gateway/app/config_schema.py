"""What every tunable limit *means*, in plain language — and what it may be set to.

``gateway_config`` stores a key and a number. That is enough for
:func:`app.limits.resolve_limit` to do its job and not nearly enough for an
operator to do theirs. This module is the missing half: for every key, the name
a person would use for it, the unit it is measured in, the range it may take,
one sentence saying what it does, and one sentence saying what happens if you
change it.

Two things depend on it, and both were missing before it existed:

**Validation.** ``PUT /admin/config/<key>`` and the dashboard's config form both
used to accept any float that parsed. Typing ``15`` where ``0.15`` was meant
raised every user's cost ceiling a hundredfold behind a cheerful green success
message. :func:`validate` is what stops that, and it reports the problem in a
sentence rather than a traceback.

**Plain language.** The dashboard's Limits page can now group keys the way an
operator thinks about them ("how much each person gets", "how much this may
cost") instead of listing them alphabetically by database key, and can show the
dollar consequence of a change beside the field that makes it.

A key with no entry here is still readable and still writable — it just gets no
bounds and no explanation. That is deliberate: an unknown key must never become
un-editable, because the fail-safe path in ``limits.py`` can invent one.
"""

from __future__ import annotations

from dataclasses import dataclass

__all__ = [
    "GROUPS",
    "GROUP_ORDER",
    "ConfigKey",
    "KEYS",
    "describe",
    "grouped_keys",
    "validate",
    "words_for_tokens",
]

#: Tokens to words, for display only. OpenAI's own rule of thumb for English
#: prose is about four characters per token, which lands near three quarters of
#: a word. Nobody thinks in tokens; every size limit in the console is shown in
#: words with the token count beside it.
_WORDS_PER_TOKEN = 0.75


def words_for_tokens(tokens: float) -> int:
    """Roughly how many English words *tokens* is, rounded to something
    speakable. Display only — never used to decide whether a request fits."""
    words = tokens * _WORDS_PER_TOKEN
    if words >= 100:
        return int(round(words / 50.0) * 50)
    return int(round(words / 10.0) * 10)


#: The four groups an operator actually thinks in, plus one for the settings
#: that exist in the schema but are not in use yet.
GROUPS: dict[str, tuple[str, str]] = {
    "allowance": (
        "How much each person gets",
        "How many requests one person may make, and how often. These are the "
        "numbers that decide what the free tier feels like to use.",
    ),
    "request_size": (
        "How big one request can be",
        "The ceiling on a single request. A request over the limit is refused "
        "before anything is sent to the model, so an oversized request never "
        "costs anything.",
    ),
    "money": (
        "How much this may cost",
        "The two spending fences. The per-person one is a second line of "
        "defence; the global one is what switches the service off.",
    ),
    "signup": (
        "Who may sign up",
        "Anyone can connect a computer without an account, which is "
        "deliberate — it is what makes this usable for someone who has never "
        "had an API key. These limits are what stop one person scripting a "
        "thousand of those.",
    ),
    "later": (
        "Not in use yet",
        "Settings for features that are not shipped. They are shown so nobody "
        "has to wonder whether they are doing something; they are not.",
    ),
}

GROUP_ORDER: tuple[str, ...] = ("allowance", "request_size", "money", "signup", "later")


@dataclass(frozen=True, slots=True)
class ConfigKey:
    """One tunable limit, described for a person rather than for the database."""

    key: str
    name: str
    group: str
    unit: str
    minimum: float
    maximum: float
    step: float
    sentence: str
    consequence: str
    cost_relevant: bool = False
    """True when changing this changes the modelled monthly bill, so the
    console must show the before-and-after cost before accepting the change."""

    @property
    def is_integer(self) -> bool:
        return self.step >= 1

    def format_value(self, value: float) -> str:
        """*value* with its unit, the way it should be read aloud."""
        if self.unit == "USD":
            return f"${value:,.2f}" if value >= 1 else f"${value:,.4f}".rstrip("0").rstrip(".")
        if self.unit == "tokens":
            return f"about {words_for_tokens(value):,} words ({int(value):,} tokens)"
        if self.unit == "bytes":
            return f"{value / (1024 * 1024):.1f} MB"
        if self.is_integer:
            return f"{int(value):,} {self.unit}"
        return f"{value:g} {self.unit}"

    def format_range(self) -> str:
        if self.unit == "USD":
            return f"between ${self.minimum:,.2f} and ${self.maximum:,.2f}"
        return f"between {self.minimum:,.0f} and {self.maximum:,.0f}"


def _feature_cap(feature: str, label: str) -> ConfigKey:
    return ConfigKey(
        key=f"feature_cap.{feature}",
        name=f"{label} — requests per person per month",
        group="allowance",
        unit="requests",
        minimum=0,
        maximum=1000,
        step=1,
        sentence=(
            f"A ceiling on {label.lower()} specifically, inside the overall monthly "
            "total. Someone who uses nothing else can still only make this many."
        ),
        consequence=(
            "Raising it lets one feature use more of a person's monthly total. It "
            "cannot take them past the overall monthly limit, so this never "
            "increases the bill on its own."
        ),
    )


KEYS: dict[str, ConfigKey] = {
    entry.key: entry
    for entry in (
        # --- How much each person gets ------------------------------------
        ConfigKey(
            key="monthly_request_cap",
            name="Free requests per person, per month",
            group="allowance",
            unit="requests",
            minimum=0,
            maximum=1000,
            step=1,
            sentence=(
                "How many AI requests one person may make between the 1st and the "
                "end of the month. The count starts again automatically on the 1st."
            ),
            consequence=(
                "This is the main dial on what the service costs. Doubling it "
                "roughly doubles the worst-case monthly bill."
            ),
            cost_relevant=True,
        ),
        ConfigKey(
            key="daily_request_cap",
            name="Free requests per person, per day",
            group="allowance",
            unit="requests",
            minimum=0,
            maximum=500,
            step=1,
            sentence=(
                "How many requests one person may make in a day. This is what stops "
                "a whole month's allowance disappearing in an afternoon."
            ),
            consequence=(
                "Raising it does not raise the monthly total, so it cannot increase "
                "the bill. It does let one person spend their allowance faster."
            ),
        ),
        ConfigKey(
            key="hourly_request_cap",
            name="Free requests per person, per hour",
            group="allowance",
            unit="requests",
            minimum=0,
            maximum=200,
            step=1,
            sentence=(
                "How many requests one person may make in an hour. The cheapest "
                "check of the lot, and the first line against a runaway script."
            ),
            consequence=(
                "Raising it does not raise the monthly total. Set it too low and "
                "ordinary bursts of real work get refused."
            ),
        ),
        ConfigKey(
            key="device_hourly_request_cap",
            name="Free requests per computer, per hour",
            group="allowance",
            unit="requests",
            minimum=0,
            maximum=200,
            step=1,
            sentence=(
                "The same hourly limit, counted per computer rather than per person. "
                "If a token leaks, this is what bounds the damage to a handful of "
                "requests an hour until somebody revokes it."
            ),
            consequence=(
                "Raising it widens the blast radius of a leaked token. It does not "
                "raise the monthly total."
            ),
        ),
        ConfigKey(
            key="review_daily_request_cap",
            name="Requests per day while under review",
            group="allowance",
            unit="requests",
            minimum=0,
            maximum=100,
            step=1,
            sentence=(
                "The smaller daily limit that applies to somebody you have put under "
                "review. A soft throttle, never a silent block — they are told it "
                "applies and told to contact support."
            ),
            consequence=(
                "Raising it makes review mode gentler and less effective. Setting it "
                "to zero turns review into a block, which is what the Paused status "
                "is for; use that instead so the person is told plainly."
            ),
        ),
        _feature_cap("summarize", "Summarize"),
        _feature_cap("rewrite", "Rewrite"),
        _feature_cap("proofread", "Proofread"),
        _feature_cap("explain", "Explain"),
        _feature_cap("document_qna", "Questions about documents"),
        # --- How big one request can be -----------------------------------
        ConfigKey(
            key="max_input_tokens",
            name="Biggest passage that may be sent",
            group="request_size",
            unit="tokens",
            minimum=100,
            maximum=100_000,
            step=50,
            sentence=(
                "The most text one request may contain, counting the passage and any "
                "document excerpts together. Anything larger is refused before it is "
                "sent, so it costs nothing."
            ),
            consequence=(
                "This is the second dial on cost. It sets what a single request can "
                "cost at worst, so doubling it roughly doubles the worst case."
            ),
            cost_relevant=True,
        ),
        ConfigKey(
            key="max_output_tokens",
            name="Longest answer the model may give",
            group="request_size",
            unit="tokens",
            minimum=50,
            maximum=16_000,
            step=50,
            sentence=(
                "The most the model may write back. Answers are billed at five times "
                "the rate of the text sent in, so this matters more than its size "
                "suggests."
            ),
            consequence=(
                "Output costs five times what input does, so raising this moves the "
                "bill faster than raising the passage limit by the same amount."
            ),
            cost_relevant=True,
        ),
        ConfigKey(
            key="max_chunks_per_request",
            name="Document excerpts per question",
            group="request_size",
            unit="excerpts",
            minimum=1,
            maximum=20,
            step=1,
            sentence=(
                "When somebody asks a question about a document, QUILL picks the "
                "best-matching passages on their own computer and sends this many. "
                "Checked separately from the size limit, so many small excerpts "
                "cannot be used to get around it."
            ),
            consequence=(
                "More excerpts means better answers and bigger requests. It does "
                "not raise the bill on its own: the size limit above still "
                "applies to all of them added together, and that is the ceiling "
                "cost is actually measured against."
            ),
        ),
        # --- How much this may cost ---------------------------------------
        ConfigKey(
            key="monthly_cost_cap_usd",
            name="Cost ceiling per person, per month",
            group="money",
            unit="USD",
            minimum=0.0,
            maximum=100.0,
            step=0.01,
            sentence=(
                "A second fence behind the request limit: one person's requests may "
                "not cost more than this in a month, whatever happens. It should sit "
                "comfortably above what the request limit can actually reach, so it "
                "only ever catches something genuinely wrong."
            ),
            consequence=(
                "Set it below what the monthly request limit can reach and people "
                "will be cut off early. Set it far above and it stops being a fence "
                "at all."
            ),
        ),
        ConfigKey(
            key="global_monthly_budget_usd",
            name="Total budget for everyone, per month",
            group="money",
            unit="USD",
            minimum=0.0,
            maximum=10_000.0,
            step=1.0,
            sentence=(
                "When total spending across everybody reaches this, QUILL's free AI "
                "switches off for everyone until an admin turns it back on. You are "
                "alerted at 50%, 75% and 90% first."
            ),
            consequence=(
                "This is a backstop, not a budget to spend up to. Leave room above "
                "the worst case — if it can be reached in normal use, it will "
                "eventually switch the service off mid-month."
            ),
        ),
        # --- Who may sign up ------------------------------------------------
        ConfigKey(
            key="new_account_hours",
            name="How long an account counts as new",
            group="signup",
            unit="hours",
            minimum=0,
            maximum=720,
            step=1,
            sentence=(
                "A brand-new account gets a smaller allowance for this long, then "
                "the full one. Somebody exploring barely notices; somebody making "
                "throwaway accounts gets a fraction of the value out of each."
            ),
            consequence=(
                "Setting it to zero removes the ramp entirely, which makes farming "
                "accounts worth several times more."
            ),
        ),
        ConfigKey(
            key="new_account_request_cap",
            name="Requests a new account gets",
            group="signup",
            unit="requests",
            minimum=0,
            maximum=1000,
            step=1,
            sentence=(
                "The monthly allowance while an account is still new. Applies "
                "instead of the normal monthly limit, not on top of it."
            ),
            consequence=(
                "Raising it toward the normal monthly limit removes most of the "
                "protection. Lowering it too far makes a real first session "
                "frustrating."
            ),
        ),
        ConfigKey(
            key="registration_hourly_cap_per_ip",
            name="New computers per internet address, per hour",
            group="signup",
            unit="sign-ups",
            minimum=0,
            maximum=1000,
            step=1,
            sentence=(
                "How many times one internet address may start the connect-a-computer "
                "flow in an hour. Zero disables sign-ups from everywhere, which is "
                "almost certainly not what you want."
            ),
            consequence=(
                "Too low and a household, an office or a school behind one address "
                "cannot all sign up on the same day. Too high and scripting accounts "
                "is free again."
            ),
        ),
        ConfigKey(
            key="registration_daily_cap_per_ip",
            name="New computers per internet address, per day",
            group="signup",
            unit="sign-ups",
            minimum=0,
            maximum=5000,
            step=1,
            sentence=(
                "The same limit over a day. A shared address — an office, a library, "
                "a university — should still fit comfortably inside it."
            ),
            consequence=(
                "This is the one most likely to catch real users in a big shared "
                "building. Raise it if legitimate sign-ups are being refused."
            ),
        ),
        # --- Not in use yet --------------------------------------------------
        ConfigKey(
            key="max_image_bytes",
            name="Biggest image file (images not shipped)",
            group="later",
            unit="bytes",
            minimum=0,
            maximum=20 * 1024 * 1024,
            step=1024,
            sentence=(
                "Reserved for describing pictures, which is not a shipped feature. "
                "Nothing reads this today."
            ),
            consequence="Nothing. The feature it belongs to is switched off.",
        ),
        ConfigKey(
            key="max_image_edge_px",
            name="Biggest image side (images not shipped)",
            group="later",
            unit="pixels",
            minimum=0,
            maximum=8000,
            step=100,
            sentence=(
                "Reserved for describing pictures, which is not a shipped feature. "
                "Nothing reads this today."
            ),
            consequence="Nothing. The feature it belongs to is switched off.",
        ),
        ConfigKey(
            key="daily_image_cap",
            name="Images per person per day (images not shipped)",
            group="later",
            unit="requests",
            minimum=0,
            maximum=200,
            step=1,
            sentence=(
                "Reserved for describing pictures, which is not a shipped feature. "
                "Nothing reads this today."
            ),
            consequence="Nothing. The feature it belongs to is switched off.",
        ),
    )
}


def describe(key: str) -> ConfigKey | None:
    """The description of *key*, or ``None`` for a key this module has never
    heard of (which is allowed — see the module docstring)."""
    return KEYS.get(key)


def grouped_keys() -> list[tuple[str, str, str, list[ConfigKey]]]:
    """Every described key, grouped the way the console displays them:
    ``(group_id, heading, blurb, keys)`` in :data:`GROUP_ORDER`."""
    out: list[tuple[str, str, str, list[ConfigKey]]] = []
    for group_id in GROUP_ORDER:
        heading, blurb = GROUPS[group_id]
        members = [entry for entry in KEYS.values() if entry.group == group_id]
        members.sort(key=lambda entry: entry.name)
        if members:
            out.append((group_id, heading, blurb, members))
    return out


def validate(key: str, value: float) -> str | None:
    """``None`` if *value* is an acceptable setting for *key*, otherwise a
    complete sentence saying what is wrong and what was typed.

    An undescribed key validates as acceptable — the alternative is a key that
    cannot be edited at all, which is worse than one that cannot be bounded.
    """
    entry = KEYS.get(key)
    if entry is None:
        return None
    if value != value or value in (float("inf"), float("-inf")):  # NaN / inf
        return f"{entry.name} must be an ordinary number."
    if value < entry.minimum or value > entry.maximum:
        typed = entry.format_value(value) if value >= 0 else f"{value:g}"
        return f"{entry.name} must be {entry.format_range()}. You typed {typed}."
    return None
