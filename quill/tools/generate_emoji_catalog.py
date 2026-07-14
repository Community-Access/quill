"""Dev-only generator for QUILL's committed emoji catalog (docs/planning/emo.md,
now folded into the PRD's Accessible Emoji Picker section).

QUILL never fetches emoji data at runtime (network_egress_audit.py's "no
surprise network calls" rule, and the app must work fully offline and in Safe
Mode). Instead, a maintainer re-runs this script when Unicode publishes a new
emoji version (roughly annual) and commits the regenerated
``quill/data/emoji_catalog.json`` like any other data update.

Three tiers of source data, most to least authoritative (see the module
docstring in quill.core.emoji_data for how the runtime consumes them):

1. Unicode Consortium's ``emoji-test.txt`` -- the category tree, the official
   short name, and which code points are standard emoji at all.
2. Unicode CLDR's English annotations -- search keywords per emoji.
3. ``iamcal/emoji-data`` (MIT) -- legacy ASCII emoticon aliases (``:)``,
   ``<3``, ...) that Unicode itself does not define.

A rich, one-to-two-sentence visual description (what the emoji actually
looks like, not just its Unicode name) has no authoritative source at all.
Scraping a picker like Emojipedia was considered and rejected in emo.md's own
plan (not an open dataset; licensing/ToS risk). This script instead asks an
LLM to *write* an original description per emoji from its Unicode
name/category/keywords -- the same "generate, don't scrape" approach QUILL
already uses nowhere else, chosen specifically to avoid that risk. Requires
``OPENAI_API_KEY`` (or ``--api-key``); with neither, descriptions fall back to
a purely mechanical synthesis ("Category > subgroup. Name.") so the script
still produces a usable (if blander) catalog offline.

Usage::

    python -m quill.tools.generate_emoji_catalog --out quill/data/emoji_catalog.json
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from quill.core.safe_xml import fromstring as _safe_xml_fromstring

_EMOJI_VERSION = "16.0"
_EMOJI_TEST_URL = f"https://unicode.org/Public/emoji/{_EMOJI_VERSION}/emoji-test.txt"
_CLDR_ANNOTATIONS_URL = (
    "https://raw.githubusercontent.com/unicode-org/cldr/main/common/annotations/en.xml"
)
_IAMCAL_EMOJI_DATA_URL = "https://raw.githubusercontent.com/iamcal/emoji-data/master/emoji.json"

_LINE_RE = re.compile(r"^([0-9A-Fa-f ]+)\s*;\s*(\S+)\s*#\s*(\S+)\s*E[\d.]+\s*(.+)$")

_OPENAI_MODEL = "gpt-4o-mini"
_OPENAI_BATCH_SIZE = 40
_DEFAULT_TIMEOUT = 60.0


@dataclass
class RawEmoji:
    char: str
    name: str
    category: str
    subgroup: str
    keywords: list[str] = field(default_factory=list)
    emoticons: list[str] = field(default_factory=list)
    description: str = ""
    # False until a real LLM description lands -- distinct from checking
    # description text against the mechanical fallback format, which is
    # fragile (an entry with no keywords produces a shorter fallback string
    # that a naive "does it look synthesized" check could misjudge).
    llm_generated: bool = False


def _fetch(url: str, *, timeout: float = _DEFAULT_TIMEOUT) -> str:
    if not url.lower().startswith("https://"):
        raise ValueError(f"Refusing a non-HTTPS source URL: {url}")
    with urllib.request.urlopen(url, timeout=timeout) as resp:  # noqa: S310 - HTTPS enforced
        return resp.read().decode("utf-8")


def parse_emoji_test(text: str) -> list[RawEmoji]:
    """Tier 1: the category tree, official names, and fully-qualified emoji.

    Only ``fully-qualified`` lines are kept -- ``unqualified``/
    ``minimally-qualified`` are legacy/alternate encodings of the same emoji
    (an ``unqualified`` variant later gained a required VS16), and
    ``component`` lines (skin-tone modifiers, ZWJ joiner) are not standalone
    emoji at all.
    """
    entries: list[RawEmoji] = []
    group = ""
    subgroup = ""
    for line in text.splitlines():
        if line.startswith("# group:"):
            group = line.split(":", 1)[1].strip()
            continue
        if line.startswith("# subgroup:"):
            subgroup = line.split(":", 1)[1].strip()
            continue
        if not line or line.startswith("#"):
            continue
        m = _LINE_RE.match(line)
        if not m:
            continue
        _cps, status, char, name = m.groups()
        if status != "fully-qualified":
            continue
        entries.append(RawEmoji(char=char, name=name.strip(), category=group, subgroup=subgroup))
    return entries


def parse_cldr_keywords(xml_text: str) -> dict[str, list[str]]:
    """Tier 2: CLDR's default (non-``tts``) annotation per code point -> keywords."""
    root = _safe_xml_fromstring(xml_text)
    out: dict[str, list[str]] = {}
    for node in root.iter("annotation"):
        if node.get("type") == "tts":
            continue
        cp = node.get("cp")
        text = node.text or ""
        if not cp or not text:
            continue
        out[cp] = [w.strip() for w in text.split("|") if w.strip()]
    return out


def parse_iamcal_emoticons(raw_json: str) -> dict[str, list[str]]:
    """Tier 3: legacy ASCII emoticon aliases, keyed by the emoji character."""
    data = json.loads(raw_json)
    out: dict[str, list[str]] = {}
    for item in data:
        unified = item.get("unified", "")
        if not unified:
            continue
        try:
            char = "".join(chr(int(part, 16)) for part in unified.split("-"))
        except ValueError:
            continue
        aliases: list[str] = []
        if item.get("text"):
            aliases.append(item["text"])
        for extra in item.get("texts") or []:
            if extra not in aliases:
                aliases.append(extra)
        if aliases:
            out[char] = aliases
    return out


def _synthesized_description(entry: RawEmoji) -> str:
    """The mechanical fallback baseline: not prose-quality, but usable offline
    and with no LLM/network dependency."""
    kw = ", ".join(entry.keywords[:5])
    tail = f" Associated words: {kw}." if kw else ""
    return f"{entry.category} > {entry.subgroup}. {entry.name}.{tail}"


@dataclass
class TokenUsage:
    """Running token totals across a generation run, for a cost estimate."""

    prompt_tokens: int = 0
    completion_tokens: int = 0
    batches: int = 0

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens

    def add(self, prompt_tokens: int, completion_tokens: int) -> None:
        self.prompt_tokens += prompt_tokens
        self.completion_tokens += completion_tokens
        self.batches += 1

    def summary(self, *, model: str) -> str:
        # gpt-4o-mini pricing as of this writing; a rough estimate only -- check
        # platform.openai.com/usage for the authoritative, billed figure.
        rate_per_million = {"gpt-4o-mini": (0.15, 0.60)}
        in_rate, out_rate = rate_per_million.get(model, (0.0, 0.0))
        cost = (self.prompt_tokens / 1_000_000) * in_rate + (
            self.completion_tokens / 1_000_000
        ) * out_rate
        cost_note = f", est. ${cost:.4f}" if (in_rate or out_rate) else ""
        return (
            f"{self.batches} batches, {self.prompt_tokens} prompt + "
            f"{self.completion_tokens} completion = {self.total_tokens} tokens{cost_note}"
        )


def _openai_batch_descriptions(
    batch: list[RawEmoji], *, api_key: str, model: str, timeout: float
) -> tuple[dict[str, str], tuple[int, int]]:
    """One OpenAI chat-completions call describing a batch of emoji.

    Returns ``({char: description}, (prompt_tokens, completion_tokens))``. A
    char missing from the model's response (malformed JSON, a dropped item)
    is simply absent -- the caller falls back to the synthesized description
    for that entry, never blocks the batch.
    """
    items = [
        {
            "char": e.char,
            "name": e.name,
            "category": e.category,
            "subgroup": e.subgroup,
            "keywords": e.keywords[:6],
        }
        for e in batch
    ]
    system = (
        "You write concise, vivid, one-to-two-sentence visual descriptions of "
        "emoji for screen-reader users who cannot see them. Describe what the "
        "emoji actually looks like -- colors, shapes, facial expression, "
        "objects, pose -- in plain language. Do not just restate the Unicode "
        "name or list the keywords back. Reply with ONLY a JSON object mapping "
        "each input 'char' to its description string, no other text."
    )
    user = json.dumps(items, ensure_ascii=False)
    payload = json.dumps({
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "response_format": {"type": "json_object"},
        "temperature": 0.4,
    }).encode("utf-8")
    request = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=payload,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as resp:  # noqa: S310 - HTTPS enforced
        body = json.loads(resp.read().decode("utf-8"))
    content = body["choices"][0]["message"]["content"]
    parsed = json.loads(content)
    described = {k: str(v).strip() for k, v in parsed.items() if isinstance(v, str) and v.strip()}
    usage = body.get("usage") or {}
    tokens = (int(usage.get("prompt_tokens", 0)), int(usage.get("completion_tokens", 0)))
    return described, tokens


def _run_batches(
    entries: list[RawEmoji],
    *,
    api_key: str,
    model: str,
    batch_size: int,
    timeout: float,
    progress: bool,
    checkpoint: Callable[[], None] | None,
    usage: TokenUsage,
    label: str,
) -> None:
    """One pass of LLM batches over *entries* (a full run, or a retry-the-
    stragglers pass), accumulating into the shared *usage* totals in place."""
    total_batches = (len(entries) + batch_size - 1) // batch_size
    for i in range(0, len(entries), batch_size):
        batch = entries[i : i + batch_size]
        batch_num = i // batch_size + 1
        if progress:
            print(
                f"  [{label}] batch {batch_num}/{total_batches} ({len(batch)} emoji)...",
                file=sys.stderr,
            )
        try:
            described, (prompt_tokens, completion_tokens) = _openai_batch_descriptions(
                batch, api_key=api_key, model=model, timeout=timeout
            )
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, KeyError) as exc:
            print(
                f"    [{label}] batch {batch_num} failed, keeping synthesized fallback: {exc}",
                file=sys.stderr,
            )
            if checkpoint is not None:
                checkpoint()
            continue
        for entry in batch:
            if entry.char in described:
                entry.description = described[entry.char]
                entry.llm_generated = True
        usage.add(prompt_tokens, completion_tokens)
        if progress:
            print(f"    tokens so far: {usage.summary(model=model)}", file=sys.stderr)
        if checkpoint is not None:
            checkpoint()
        time.sleep(0.2)  # gentle pacing; not rate-limit-critical at this batch size


def enrich_with_llm_descriptions(
    entries: list[RawEmoji],
    *,
    api_key: str | None,
    model: str = _OPENAI_MODEL,
    batch_size: int = _OPENAI_BATCH_SIZE,
    timeout: float = _DEFAULT_TIMEOUT,
    progress: bool = True,
    checkpoint: Callable[[], None] | None = None,
    max_retry_rounds: int = 3,
) -> TokenUsage:
    """Fill in ``entry.description`` for every entry, in place.

    Every entry gets the synthesized fallback first (so a partial/failed run
    still produces a usable catalog), then LLM descriptions overwrite it
    batch by batch. A single batch's failure is logged and skipped -- one bad
    network blip must never lose the whole run's progress.

    After the initial pass, entries still on the synthesized fallback (a
    failed batch, or an item the model dropped from its JSON response) are
    retried in fresh batches, up to ``max_retry_rounds`` times or until none
    remain -- "fix any that are missing" as a real, built-in step rather than
    a one-off manual patch-up. Each retry round uses a smaller batch size
    (halved, floor 5) since a shrinking straggler set benefits more from
    fewer chances for one bad item to sink a whole batch than from raw
    throughput.

    ``checkpoint``, if given, is called after every batch in every round
    (success or failure) -- typically a closure that writes the catalog-so-far
    to disk, so a run that dies partway through (or one you just want to
    watch progress on) still has a real, inspectable, up-to-date output file
    instead of nothing until the very end.

    Returns the accumulated :class:`TokenUsage` for a cost estimate --
    ``platform.openai.com/usage`` is still the authoritative, billed figure.
    """
    for entry in entries:
        if not entry.llm_generated:
            entry.description = _synthesized_description(entry)
    usage = TokenUsage()
    if not api_key:
        return usage

    _run_batches(
        entries,
        api_key=api_key,
        model=model,
        batch_size=batch_size,
        timeout=timeout,
        progress=progress,
        checkpoint=checkpoint,
        usage=usage,
        label="main",
    )

    round_batch_size = batch_size
    for round_num in range(1, max_retry_rounds + 1):
        stragglers = [e for e in entries if not e.llm_generated]
        if not stragglers:
            break
        round_batch_size = max(5, round_batch_size // 2)
        if progress:
            print(
                f"  {len(stragglers)} entries still on the fallback description; "
                f"retry round {round_num}/{max_retry_rounds} (batch size {round_batch_size})...",
                file=sys.stderr,
            )
        _run_batches(
            stragglers,
            api_key=api_key,
            model=model,
            batch_size=round_batch_size,
            timeout=timeout,
            progress=progress,
            checkpoint=checkpoint,
            usage=usage,
            label=f"retry {round_num}",
        )

    still_missing = [e for e in entries if not e.llm_generated]
    if still_missing and progress:
        sample = ", ".join(f"{e.char} ({e.name})" for e in still_missing[:10])
        print(
            f"  {len(still_missing)} entries kept the mechanical fallback description "
            f"after {max_retry_rounds} retry rounds: {sample}"
            + (", ..." if len(still_missing) > 10 else ""),
            file=sys.stderr,
        )
    return usage


def retry_missing_descriptions(
    entries: list[RawEmoji],
    *,
    api_key: str | None,
    model: str = _OPENAI_MODEL,
    batch_size: int = _OPENAI_BATCH_SIZE,
    timeout: float = _DEFAULT_TIMEOUT,
    progress: bool = True,
    checkpoint: Callable[[], None] | None = None,
    max_retry_rounds: int = 3,
) -> TokenUsage:
    """``--fix-missing``'s real work: retry ONLY the entries not already
    marked ``llm_generated`` (see :func:`_load_existing_entries`), never a
    full main pass over every entry -- unlike :func:`enrich_with_llm_descriptions`,
    which always assumes it is starting fresh. Calling the wrong one here
    silently re-describes (and re-bills) an already-complete catalog from
    scratch, which is exactly the bug this function exists to avoid.
    """
    usage = TokenUsage()
    if not api_key:
        return usage
    round_batch_size = batch_size
    for round_num in range(1, max_retry_rounds + 1):
        stragglers = [e for e in entries if not e.llm_generated]
        if not stragglers:
            break
        if round_num > 1:
            round_batch_size = max(5, round_batch_size // 2)
        if progress:
            print(
                f"  {len(stragglers)} entries still on the fallback description; "
                f"retry round {round_num}/{max_retry_rounds} (batch size {round_batch_size})...",
                file=sys.stderr,
            )
        _run_batches(
            stragglers,
            api_key=api_key,
            model=model,
            batch_size=round_batch_size,
            timeout=timeout,
            progress=progress,
            checkpoint=checkpoint,
            usage=usage,
            label=f"fix-missing retry {round_num}",
        )
    return usage


def _catalog_dict(entries: list[RawEmoji]) -> dict:
    return {
        "unicode_emoji_version": _EMOJI_VERSION,
        "source_urls": {
            "unicode_emoji_test": _EMOJI_TEST_URL,
            "cldr_annotations": _CLDR_ANNOTATIONS_URL,
            "iamcal_emoji_data": _IAMCAL_EMOJI_DATA_URL,
        },
        "entries": [
            {
                "char": e.char,
                "name": e.name,
                "category": e.category,
                "subgroup": e.subgroup,
                "keywords": e.keywords,
                "emoticons": e.emoticons,
                "description": e.description,
            }
            for e in entries
        ],
    }


def _write_catalog(catalog: dict, out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(catalog, ensure_ascii=False, indent=2, sort_keys=False) + "\n", encoding="utf-8"
    )


def validate_catalog(catalog: dict) -> list[str]:
    """Data-completeness problems in *catalog*, worst-first; empty if clean.

    Runs at the end of every generation (and every ``--fix-missing`` repair
    pass) so a bad run is caught here rather than shipped -- the same
    "catches a bad generator run before it ships" check emo.md's own test
    plan asked for, now a real, always-on part of the tool instead of a
    separate manual test someone has to remember to run.
    """
    problems: list[str] = []
    entries = catalog.get("entries") or []
    if not entries:
        problems.append("catalog has zero entries")
        return problems

    seen_chars: set[str] = set()
    for entry in entries:
        char = entry.get("char", "")
        name = entry.get("name", "") or "(unnamed)"
        label = f"{char!r} ({name})"
        if not char:
            problems.append(f"entry with no char: {name}")
            continue
        if char in seen_chars:
            problems.append(f"duplicate char: {label}")
        seen_chars.add(char)
        if not entry.get("name"):
            problems.append(f"{label}: missing name")
        if not entry.get("category"):
            problems.append(f"{label}: missing category")
        if not entry.get("subgroup"):
            problems.append(f"{label}: missing subgroup")
        if not entry.get("description", "").strip():
            problems.append(f"{label}: missing description")
        if not isinstance(entry.get("keywords"), list):
            problems.append(f"{label}: keywords is not a list")
        if not isinstance(entry.get("emoticons"), list):
            problems.append(f"{label}: emoticons is not a list")

    expected_count = 3700  # a sanity floor, not the exact Unicode 16.0 count
    if len(entries) < expected_count:
        problems.append(
            f"only {len(entries)} entries -- expected roughly {expected_count}+ "
            "for a full Unicode emoji-test.txt parse; the source fetch or parser "
            "may have failed partway through"
        )
    return problems


def _load_existing_entries(path: Path) -> list[RawEmoji]:
    """Reconstruct :class:`RawEmoji` rows from an already-generated catalog
    file, for ``--fix-missing``. An entry whose description differs from what
    :func:`_synthesized_description` would produce for it right now is
    treated as already real (``llm_generated=True``) and left alone; an
    identical one is a straggler eligible for retry."""
    raw = json.loads(path.read_text(encoding="utf-8"))
    entries: list[RawEmoji] = []
    for item in raw.get("entries", []):
        entry = RawEmoji(
            char=item["char"],
            name=item["name"],
            category=item["category"],
            subgroup=item["subgroup"],
            keywords=list(item.get("keywords") or []),
            emoticons=list(item.get("emoticons") or []),
            description=item.get("description", ""),
        )
        entry.llm_generated = entry.description != _synthesized_description(entry)
        entries.append(entry)
    return entries


def build_catalog(
    *,
    api_key: str | None,
    offline_fixtures_dir: Path | None = None,
    checkpoint_path: Path | None = None,
) -> tuple[dict, TokenUsage]:
    """Returns ``(catalog, usage)``.

    ``checkpoint_path``, if given, gets the catalog-so-far written to it after
    every LLM batch -- open it in another window (or ``tail -f`` its JSON) to
    watch descriptions land in something real as the run progresses, and to
    never lose more than one batch's progress if the run dies partway through.
    """
    if offline_fixtures_dir is not None:
        emoji_test_text = (offline_fixtures_dir / "emoji-test.txt").read_text(encoding="utf-8")
        cldr_text = (offline_fixtures_dir / "annotations_en.xml").read_text(encoding="utf-8")
        iamcal_text = (offline_fixtures_dir / "emoji-data-iamcal.json").read_text(encoding="utf-8")
    else:
        print("Fetching Unicode emoji-test.txt...", file=sys.stderr)
        emoji_test_text = _fetch(_EMOJI_TEST_URL)
        print("Fetching CLDR English annotations...", file=sys.stderr)
        cldr_text = _fetch(_CLDR_ANNOTATIONS_URL)
        print("Fetching iamcal/emoji-data (emoticon aliases)...", file=sys.stderr)
        iamcal_text = _fetch(_IAMCAL_EMOJI_DATA_URL)

    entries = parse_emoji_test(emoji_test_text)
    keywords_by_char = parse_cldr_keywords(cldr_text)
    emoticons_by_char = parse_iamcal_emoticons(iamcal_text)
    for entry in entries:
        entry.keywords = keywords_by_char.get(entry.char, [])
        entry.emoticons = emoticons_by_char.get(entry.char, [])

    print(f"Parsed {len(entries)} fully-qualified emoji.", file=sys.stderr)

    checkpoint = None
    if checkpoint_path is not None:
        checkpoint = lambda: _write_catalog(_catalog_dict(entries), checkpoint_path)  # noqa: E731

    usage = enrich_with_llm_descriptions(entries, api_key=api_key, checkpoint=checkpoint)

    return _catalog_dict(entries), usage


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("quill/data/emoji_catalog.json"),
        help="Output path for the generated catalog JSON. Also checkpointed to after "
        "every LLM batch, so it is watchable/tail-able and never fully lost if a long "
        "run dies partway through.",
    )
    parser.add_argument(
        "--api-key",
        default=os.environ.get("OPENAI_API_KEY", ""),
        help="OpenAI API key for description generation (env OPENAI_API_KEY by default). "
        "Omit to fall back to mechanical descriptions with no network calls.",
    )
    parser.add_argument(
        "--offline-fixtures",
        type=Path,
        default=None,
        help="Directory with pre-downloaded emoji-test.txt / annotations_en.xml / "
        "emoji-data-iamcal.json, to regenerate without re-fetching Tier 1-3 sources.",
    )
    parser.add_argument(
        "--fix-missing",
        action="store_true",
        help="Load the catalog already at --out and retry only the entries still on "
        "the mechanical fallback description (a prior run's failed/dropped batches), "
        "instead of regenerating the whole catalog from scratch.",
    )
    args = parser.parse_args(argv)

    if args.fix_missing:
        if not args.out.exists():
            print(f"--fix-missing needs an existing catalog at {args.out}", file=sys.stderr)
            return 1
        entries = _load_existing_entries(args.out)
        stragglers_before = sum(1 for e in entries if not e.llm_generated)
        print(
            f"Loaded {len(entries)} entries from {args.out}; "
            f"{stragglers_before} still on the fallback description.",
            file=sys.stderr,
        )
        checkpoint = lambda: _write_catalog(_catalog_dict(entries), args.out)  # noqa: E731
        usage = retry_missing_descriptions(
            entries, api_key=args.api_key or None, checkpoint=checkpoint
        )
        catalog = _catalog_dict(entries)
    else:
        catalog, usage = build_catalog(
            api_key=args.api_key or None,
            offline_fixtures_dir=args.offline_fixtures,
            checkpoint_path=args.out,
        )

    _write_catalog(catalog, args.out)
    print(f"Wrote {len(catalog['entries'])} entries to {args.out}", file=sys.stderr)
    if usage.batches:
        print(f"Token usage: {usage.summary(model=_OPENAI_MODEL)}", file=sys.stderr)

    problems = validate_catalog(catalog)
    if problems:
        print(f"Validation found {len(problems)} issue(s):", file=sys.stderr)
        for problem in problems[:30]:
            print(f"  - {problem}", file=sys.stderr)
        if len(problems) > 30:
            print(f"  ... and {len(problems) - 30} more", file=sys.stderr)
    else:
        print("Validation: catalog is complete, no issues found.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
