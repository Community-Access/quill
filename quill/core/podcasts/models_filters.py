"""Episode Filters: the stored shape of one podcast's ingest rules.

A podcast that publishes three things in one feed -- the show, the trailers,
and the daily two-minute segment -- gives you no way to follow only the one
you want. Cast's answer had been the Inbox and a lot of manual dismissing:
every unwanted item still arrived, still had to be triaged, and still counted
against an Inbox cap that a person set for a different reason.

Episode Filters is the missing decision, made **before** an episode is routed:
a per-podcast rule set that says whether a genuinely new feed item reaches the
Inbox and the auto-queue at all. It is deliberately *not* a delete: a filtered
episode stays in the podcast's own list with its played state, position,
download and bookmarks untouched, which is what makes a wrong rule survivable.

This module is the **data**, and only the data -- the record, its serialised
form, and the coercion that makes a hand-edited or half-written settings file
behave like a sane one. The matching, the preview and the decisions live in
:mod:`quill.core.podcasts.episode_filters`, and applying a saved rule set to
episodes you already have lives in
:mod:`quill.core.podcasts.episode_filter_maintenance`. Split the same way
``models_settings`` is split from the dialogs that edit it, and for the same
reason: the on-disk schema and the behaviour over it change at different rates.

**Every failure here fails open.** An unknown ``version``, a malformed record,
a rule with nothing in it: the answer is always "no filter", never "filter
everything out". The cost of failing open is an episode you did not want; the
cost of failing closed is a podcast that silently stops arriving and no
message anywhere saying why.

wx-free, strict-typed, pure data.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from quill.core.podcasts.models_queue import coerce_int as _coerce_int

#: The stored configuration version. A file written by a *newer* build reads as
#: no filter at all (see :meth:`EpisodeFilterConfiguration.from_dict`) rather
#: than being partially understood -- half a rule set is the one outcome worse
#: than none.
FILTER_CONFIG_VERSION = 1

#: Keep everything **except** what a rule matches. The common case: a show you
#: follow that also publishes a segment you do not want.
MODE_FILTER_MATCHING = "filter_matching"
#: Keep **only** what a rule matches. The narrow case: one strand of a feed
#: that carries several. Much sharper, and much easier to get wrong, which is
#: why every safety rule in this feature exists for this mode.
MODE_KEEP_MATCHING = "keep_matching"
FILTER_MODES: tuple[str, ...] = (MODE_FILTER_MATCHING, MODE_KEEP_MATCHING)

#: ``*`` matches any run of characters, ``?`` matches exactly one, and every
#: other regular-expression metacharacter is a literal. This is the path
#: almost everybody wants and the only one that can be written correctly
#: without knowing what a metacharacter is.
PATTERN_WILDCARD = "wildcard"
#: A full Python regular expression, for somebody who asked for one.
PATTERN_REGEX = "regex"
#: No title criterion at all -- a duration-only rule.
PATTERN_NONE = ""
PATTERN_KINDS: tuple[str, ...] = (PATTERN_NONE, PATTERN_WILDCARD, PATTERN_REGEX)

#: How the two title kinds read out loud, and in the rules list.
PATTERN_KIND_LABELS: dict[str, str] = {
    PATTERN_NONE: "No title rule",
    PATTERN_WILDCARD: "Wildcard title",
    PATTERN_REGEX: "Regular expression title",
}

#: How the two modes read out loud.
MODE_LABELS: dict[str, str] = {
    MODE_FILTER_MATCHING: "Keep everything except episodes a rule matches",
    MODE_KEEP_MATCHING: "Keep only episodes a rule matches",
}

# -- scopes: which parts of the app a filter actually governs -----------------
#
# The first cut of this feature filtered exactly one surface, the Inbox, and
# that was the wrong shape. "I do not want this podcast's daily segment" is not
# a statement about a triage list; it is a statement about the segment. Somebody
# who says it means it in the episode list, in New Episodes, in a smart
# playlist, in search -- or means it in only some of those, which is exactly why
# it has to be *theirs to say* rather than a decision the app makes for them.
#
# So a filter carries a set of scopes: the places its verdict is honoured.
# Every scope is independent, every one is reversible by unticking it, and
# **not one of them deletes anything** -- a scope that is off simply means the
# episode is visible there, which is what it always was.

#: Keep rejected episodes out of the Inbox.
SCOPE_INBOX = "inbox"
#: Do not auto-queue a rejected episode when the podcast auto-queues.
SCOPE_QUEUE = "queue"
#: Do not auto-download a rejected episode.
SCOPE_DOWNLOAD = "download"
#: Do not count or name a rejected episode in the new-episode announcement.
SCOPE_NOTIFY = "notify"
#: Hide rejected episodes from this podcast's own episode list.
SCOPE_LIBRARY = "library"
#: Hide them from the cross-show views (New Episodes, Continue Listening).
SCOPE_VIEWS = "views"
#: Keep them out of smart playlists.
SCOPE_PLAYLISTS = "playlists"
#: Keep them out of Search Everywhere.
SCOPE_SEARCH = "search"

FILTER_SCOPES: tuple[str, ...] = (
    SCOPE_INBOX,
    SCOPE_QUEUE,
    SCOPE_DOWNLOAD,
    SCOPE_NOTIFY,
    SCOPE_LIBRARY,
    SCOPE_VIEWS,
    SCOPE_PLAYLISTS,
    SCOPE_SEARCH,
)

#: The wording of each checkbox, in the order they are offered: the four
#: routing scopes first, then the four that hide.
#:
#: Eight real checkboxes, not one ``wx.CheckListBox`` -- a check-list looks
#: like the right control and is the wrong one, because a screen reader does
#: not announce a row's checked state as you arrow past it, and "is this one
#: on?" is the entire content of these rows (A11Y-SR-1, enforced by the
#: banned-pattern gate).
#:
#: Each therefore carries its own access key, and the eight are chosen to be
#: free of everything else in that window (GATE-14): I, P, N, C, T, G, K, S.
SCOPE_LABELS: dict[str, str] = {
    SCOPE_INBOX: "Keep them out of the &Inbox",
    SCOPE_QUEUE: "Never add them to the &Play Queue automatically",
    SCOPE_DOWNLOAD: "&Never download them automatically",
    SCOPE_NOTIFY: "Don't announ&ce them as new episodes",
    SCOPE_LIBRARY: "Hide them from this podcast's episode lis&t",
    SCOPE_VIEWS: "Hide them from New Episodes and Continue Listenin&g",
    SCOPE_PLAYLISTS: "&Keep them out of smart playlists",
    SCOPE_SEARCH: "Leave them out of &Search Everywhere",
}

#: How each scope reads in a spoken summary (no ampersands, third person).
SCOPE_SUMMARIES: dict[str, str] = {
    SCOPE_INBOX: "the Inbox",
    SCOPE_QUEUE: "auto-queueing",
    SCOPE_DOWNLOAD: "auto-downloading",
    SCOPE_NOTIFY: "new-episode announcements",
    SCOPE_LIBRARY: "this podcast's episode list",
    SCOPE_VIEWS: "New Episodes and Continue Listening",
    SCOPE_PLAYLISTS: "smart playlists",
    SCOPE_SEARCH: "Search Everywhere",
}

#: What a brand-new filter governs before anybody touches the checkboxes.
#:
#: The four **routing** scopes, and none of the four **hiding** ones. Routing
#: is what a filter is for -- "stop putting this in front of me" -- and it is
#: entirely undoable, because an episode that was not queued can still be
#: queued. Hiding an episode from a list is a stronger act: it changes what
#: somebody can find, and a person who has not asked for that should not
#: discover it. So the strong half is opt-in, one tick at a time, and every
#: tick is reversible.
DEFAULT_SCOPES: frozenset[str] = frozenset({SCOPE_INBOX, SCOPE_QUEUE, SCOPE_DOWNLOAD, SCOPE_NOTIFY})

#: The scopes that *hide* an episode from a list rather than merely declining
#: to route it. Grouped because they share a safety requirement: wherever one
#: of these is in force, there must be a way to see what it hid (the episode
#: list's own "Filtered out" view).
HIDING_SCOPES: frozenset[str] = frozenset({
    SCOPE_LIBRARY,
    SCOPE_VIEWS,
    SCOPE_PLAYLISTS,
    SCOPE_SEARCH,
})


def _one_of(value: object, allowed: tuple[str, ...], default: str) -> str:
    wanted = str(value or "").strip().lower()
    return wanted if wanted in allowed else default


def wildcard_to_regex(pattern: str) -> str:
    """A wildcard pattern as a regular expression source.

    ``*`` and ``?`` are the whole vocabulary; **everything else is escaped**,
    including the characters a regular expression would otherwise treat as
    special. A podcast whose segment is literally called ``Q+A (short)``
    should be matchable by typing ``Q+A*``, and it is only matchable that way
    if ``+`` and the brackets mean themselves.

    Anchored by the caller, not here: :func:`re.fullmatch` is what decides
    whether ``*date*`` has to cover the whole title, and keeping the anchoring
    out of the source keeps this function honest about what it translates.
    """
    out: list[str] = []
    for char in pattern:
        if char == "*":
            out.append(".*")
        elif char == "?":
            out.append(".")
        else:
            out.append(re.escape(char))
    return "".join(out)


@dataclass(slots=True)
class EpisodeFilterRule:
    """One rule: a title criterion, a duration criterion, or both.

    Within a rule the criteria are **and**-ed -- "a title like ``*bonus*``
    that is also at least 45 minutes" is one rule, not two. Across the rules
    of a configuration they are **or**-ed, which is what makes each rule
    independently switchable without any of them changing what the others
    mean.

    ``name`` is the listener's own label, and it is what the rules list and
    every announcement lead with. A rule with no name reads as its criteria,
    which is worse but never silent.
    """

    name: str = ""
    enabled: bool = True
    pattern_kind: str = PATTERN_WILDCARD
    pattern: str = ""
    case_sensitive: bool = False
    #: A **minimum** duration in whole minutes; 0 = no duration criterion.
    #: V1 has no maximum and no relative rule ("the longest one published that
    #: day") -- both were considered and deferred rather than guessed at.
    min_duration_minutes: int = 0

    # -- what this rule actually asks ---------------------------------------

    @property
    def has_title_criterion(self) -> bool:
        """Whether this rule asks anything about the title."""
        return self.pattern_kind in (PATTERN_WILDCARD, PATTERN_REGEX) and bool(self.pattern.strip())

    @property
    def has_duration_criterion(self) -> bool:
        """Whether this rule asks anything about the duration."""
        return self.min_duration_minutes > 0

    @property
    def pattern_error(self) -> str:
        """Why this rule's pattern cannot be used, or ``""`` when it can.

        Only a regular expression can be *invalid*: a wildcard pattern is
        escaped into one, so there is no such thing as a wildcard that will
        not compile. Returned as the message rather than a bool because the
        save gate speaks it, and "that pattern is not valid" without the
        reason is a dead end.
        """
        if self.pattern_kind != PATTERN_REGEX or not self.pattern.strip():
            return ""
        try:
            re.compile(self.pattern)
        except re.error as exc:
            return str(exc)
        return ""

    @property
    def is_usable(self) -> bool:
        """Whether this rule can decide anything about an episode.

        A rule with no criterion at all, or with a regular expression that
        does not compile, is **not** usable -- and an unusable rule never
        matches, in either mode. That is the single most important sentence in
        this feature: it is what stops a damaged rule from quietly rejecting
        an entire podcast under Keep matching.
        """
        if self.pattern_error:
            return False
        return self.has_title_criterion or self.has_duration_criterion

    # -- storage -------------------------------------------------------------

    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "enabled": self.enabled,
            "pattern_kind": self.pattern_kind,
            "pattern": self.pattern,
            "case_sensitive": self.case_sensitive,
            "min_duration_minutes": self.min_duration_minutes,
        }

    @classmethod
    def from_dict(cls, data: object) -> EpisodeFilterRule | None:
        """One stored rule, or ``None`` when the entry is not a record.

        Coerced, never trusted: an unknown ``pattern_kind`` reads as "no title
        rule" rather than as a wildcard, because a pattern the file meant one
        way and this build reads another way is exactly how a rule starts
        matching things nobody asked it to.
        """
        if not isinstance(data, dict):
            return None
        kind = _one_of(data.get("pattern_kind"), PATTERN_KINDS, PATTERN_NONE)
        return cls(
            name=str(data.get("name", "") or "").strip(),
            enabled=bool(data.get("enabled", True)),
            pattern_kind=kind,
            pattern=str(data.get("pattern", "") or ""),
            case_sensitive=bool(data.get("case_sensitive", False)),
            min_duration_minutes=max(0, _coerce_int(data.get("min_duration_minutes"), 0)),
        )


@dataclass(slots=True)
class EpisodeFilterConfiguration:
    """One podcast's whole rule set: the switch, the mode, and the rules.

    ``enabled`` is the top-level switch and it governs **ingest only**.
    Preview deliberately runs against a draft whose switch is off, because
    previewing before activating is the entire point of having a preview --
    the first build shipped without that and it was the defect device testing
    found first.
    """

    enabled: bool = False
    mode: str = MODE_FILTER_MATCHING
    rules: list[EpisodeFilterRule] = field(default_factory=list)
    #: Which parts of the app honour this filter's verdict -- see
    #: :data:`FILTER_SCOPES`. A rule set decides *what* a rejected episode is;
    #: the scopes decide *where that means anything*, which is the half that
    #: makes one feature answer "keep it out of my Inbox", "hide it from the
    #: list entirely", and "just don't download it" without three features.
    scopes: set[str] = field(default_factory=lambda: set(DEFAULT_SCOPES))
    version: int = FILTER_CONFIG_VERSION

    # -- what is actually in force -------------------------------------------

    @property
    def enabled_rules(self) -> list[EpisodeFilterRule]:
        """The rules the listener has switched on, usable or not."""
        return [rule for rule in self.rules if rule.enabled]

    @property
    def usable_rules(self) -> list[EpisodeFilterRule]:
        """The rules that are switched on **and** can decide something.

        The list every ingest decision is made against. An enabled rule whose
        regular expression does not compile is not in it, so a pattern that
        broke between one build and the next degrades to "this rule does
        nothing" instead of to "this podcast does nothing".
        """
        return [rule for rule in self.enabled_rules if rule.is_usable]

    @property
    def is_active(self) -> bool:
        """Whether this configuration changes what happens at ingest.

        Switched on, carrying at least one usable enabled rule, **and** given
        at least one place to mean something. Keep matching with no usable rule
        would otherwise reject every episode of the podcast, so it is defined
        here as inactive and the whole feed goes through untouched -- the
        fail-open rule, stated once, where the save gate, the ingest path and
        every list that hides an episode can all read it.

        Scopes are part of the same sentence: a filter with every scope
        unticked has been told to change nothing anywhere, and the honest
        reading of that is "not active" rather than "active but invisible".
        """
        return self.enabled and bool(self.usable_rules) and bool(self.active_scopes)

    @property
    def active_scopes(self) -> set[str]:
        """The stored scopes, minus anything this build does not know."""
        return {scope for scope in self.scopes if scope in FILTER_SCOPES}

    def governs(self, scope: str) -> bool:
        """Whether this filter's verdict is honoured in *scope*.

        The single question every consumer asks. False for an inactive
        configuration whatever its scopes say, so no caller has to remember to
        check both.
        """
        return self.is_active and scope in self.scopes

    # -- storage -------------------------------------------------------------

    def to_dict(self) -> dict[str, object]:
        return {
            "version": self.version,
            "enabled": self.enabled,
            "mode": self.mode,
            "scopes": sorted(self.scopes),
            "rules": [rule.to_dict() for rule in self.rules],
        }

    @classmethod
    def from_dict(cls, data: object) -> EpisodeFilterConfiguration | None:
        """A stored configuration, or ``None`` for "no filter".

        ``None`` -- not an empty configuration -- for anything this build
        cannot read: a non-record, or a version it does not know. The caller
        treats ``None`` as "this podcast has no filter", which is the same
        behaviour a podcast had before the feature existed. A future version
        that adds a criterion therefore degrades, on an older build, to the
        podcast simply not being filtered, rather than to being filtered by
        half a rule.
        """
        if not isinstance(data, dict):
            return None
        version = _coerce_int(data.get("version"), 0)
        if version != FILTER_CONFIG_VERSION:
            return None
        rules: list[EpisodeFilterRule] = []
        raw_rules = data.get("rules")
        for entry in raw_rules if isinstance(raw_rules, list) else []:
            rule = EpisodeFilterRule.from_dict(entry)
            if rule is not None:
                rules.append(rule)
        # A file with no ``scopes`` key predates them and meant the routing
        # four; unknown scope names are dropped rather than kept, so a build
        # can never honour a scope it has no code for. An explicitly empty
        # list stays empty -- "governs nothing" is a thing somebody can mean.
        raw_scopes = data.get("scopes")
        scopes = (
            {str(entry) for entry in raw_scopes if str(entry) in FILTER_SCOPES}
            if isinstance(raw_scopes, list)
            else set(DEFAULT_SCOPES)
        )
        return cls(
            enabled=bool(data.get("enabled", False)),
            mode=_one_of(data.get("mode"), FILTER_MODES, MODE_FILTER_MATCHING),
            rules=rules,
            scopes=scopes,
            version=FILTER_CONFIG_VERSION,
        )

    def copy(self) -> EpisodeFilterConfiguration:
        """A deep-enough copy for the editor to edit as a draft.

        The dialog edits a draft and writes it back only on Save, so Cancel
        has to be able to leave the stored configuration exactly as it was --
        including its rule objects, which are mutable.
        """
        return EpisodeFilterConfiguration(
            enabled=self.enabled,
            mode=self.mode,
            scopes=set(self.scopes),
            rules=[
                EpisodeFilterRule(
                    name=rule.name,
                    enabled=rule.enabled,
                    pattern_kind=rule.pattern_kind,
                    pattern=rule.pattern,
                    case_sensitive=rule.case_sensitive,
                    min_duration_minutes=rule.min_duration_minutes,
                )
                for rule in self.rules
            ],
            version=self.version,
        )


__all__ = [
    "DEFAULT_SCOPES",
    "FILTER_CONFIG_VERSION",
    "FILTER_MODES",
    "FILTER_SCOPES",
    "HIDING_SCOPES",
    "MODE_FILTER_MATCHING",
    "MODE_KEEP_MATCHING",
    "MODE_LABELS",
    "PATTERN_KINDS",
    "PATTERN_KIND_LABELS",
    "PATTERN_NONE",
    "PATTERN_REGEX",
    "PATTERN_WILDCARD",
    "SCOPE_DOWNLOAD",
    "SCOPE_INBOX",
    "SCOPE_LABELS",
    "SCOPE_LIBRARY",
    "SCOPE_NOTIFY",
    "SCOPE_PLAYLISTS",
    "SCOPE_QUEUE",
    "SCOPE_SEARCH",
    "SCOPE_SUMMARIES",
    "SCOPE_VIEWS",
    "EpisodeFilterConfiguration",
    "EpisodeFilterRule",
    "wildcard_to_regex",
]
