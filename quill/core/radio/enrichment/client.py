"""The app's side of station packs: install a verified pack, and say what it holds.

wx-free. The details pane and the search window (``quill/ui/radio``) call
these; everything here is plain values and sentences.

**Where a pack comes from.** A release build can carry a pack in
``quill/data/radio-enrichment/`` (beside the catalog seed), and
:func:`install_bundled` imports it the first time the store is opened, or when
the bundled pack is newer than the installed one. A downloaded weekly pack
would arrive through :func:`install_pack_file` the same way. **There is no
download in this build**: fetching the weekly pack needs a consent setting and
an entry in ``network_egress_audit``, and waits on the data-terms decision.

Every route goes through :func:`quill.core.radio.enrichment.pack.open_verified`,
so a pack that is not signed by the publisher key bundled with this build is
refused before a byte of it is parsed.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from quill.core.radio.enrichment import EnrichmentError, PackRefusedError
from quill.core.radio.enrichment.facts import StationFacts
from quill.core.radio.enrichment.pack import PACK_NAME, SourceCredit, open_verified
from quill.core.radio.enrichment.store import EnrichmentStore, ImportResult

if TYPE_CHECKING:
    from nacl import signing as nacl_signing


def bundled_dir() -> Path:
    """Where a build ships its pack: ``quill/data/radio-enrichment``."""
    return Path(__file__).resolve().parents[3] / "data" / "radio-enrichment"


def install_pack_file(
    store: EnrichmentStore,
    pack_path: Path,
    *,
    public_key: nacl_signing.VerifyKey | None = None,
    only_if_newer: bool = True,
) -> ImportResult | None:
    """Verify *pack_path* and import it. None when it is not newer than what is installed.

    Raises :class:`PackRefusedError` for an untrusted or damaged pack, and
    :class:`EnrichmentError` when the store cannot take it; either way the
    facts already installed stay exactly as they were.
    """
    pack = open_verified(pack_path, public_key=public_key)
    if only_if_newer:
        installed = store.built_at()
        if installed and pack.built_at <= installed:
            return None
    return store.import_pack(pack)


def install_bundled(
    store: EnrichmentStore,
    *,
    directory: Path | None = None,
    public_key: nacl_signing.VerifyKey | None = None,
) -> ImportResult | None:
    """Import the pack this build ships, when there is one and it is newer."""
    pack_path = (directory if directory is not None else bundled_dir()) / PACK_NAME
    if not pack_path.is_file():
        return None
    return install_pack_file(store, pack_path, public_key=public_key)


def open_store(data_dir: Path | str) -> EnrichmentStore:
    """The profile's store, recreated when it is unreadable (it is derived data)."""
    store = EnrichmentStore.in_data_dir(data_dir)
    try:
        store.count()
    except EnrichmentError:
        store.destroy()
        store = EnrichmentStore.in_data_dir(data_dir)
        store.count()
    return store


def outcome_sentence(result: ImportResult | None) -> str:
    """The one spoken outcome of an import: counts, never just "done"."""
    if result is None:
        return "The station details are already up to date."
    parts = [f"{result.added:,} new", f"{result.changed:,} changed"]
    if result.removed:
        parts.append(f"{result.removed:,} removed")
    return f"Station details updated: {', '.join(parts)}; {result.total:,} stations in all."


def refusal_sentence(error: PackRefusedError | EnrichmentError) -> str:
    """The sentence for a refused or failed import; the old facts are kept."""
    said = str(error.args[0]) if error.args else "The station pack could not be used."
    return f"{said} The station details you already had are unchanged."


_LABELS: tuple[tuple[str, str], ...] = (
    ("name", "Name"),
    ("call_sign", "Call sign"),
    ("frequency", "Frequency"),
    ("slogan", "Slogan"),
    ("genre", "Format"),
    ("tags", "Tags"),
    ("city", "City"),
    ("state", "State or province"),
    ("country", "Country"),
    ("language", "Language"),
    ("owner", "Owner"),
    ("homepage", "Home page"),
    ("description", "Description"),
    ("summary", "Summary"),
)


def details_lines(facts: StationFacts, credits: list[SourceCredit] | None = None) -> list[str]:
    """The details pane, one labelled line per known fact, credits last.

    Every line starts with its label, so a listener arrowing line by line hears
    what each value is before the value. Unknown facts are left out rather than
    read as "Slogan: unknown" fourteen times.
    """
    lines = [
        f"{label}: {' '.join(str(getattr(facts, name)).split())}"
        for name, label in _LABELS
        if getattr(facts, name)
    ]
    if facts.confirmed:
        lines.append(f"Last confirmed: {facts.confirmed}")
    titles = {credit.id: credit.title for credit in credits or []}
    by_source: dict[str, list[str]] = {}
    labels = dict(_LABELS)
    for name, source_id in sorted(facts.provenance.items()):
        if name in labels and bool(getattr(facts, name)):
            by_source.setdefault(source_id, []).append(labels[name].lower())
    if by_source:
        described = "; ".join(
            f"{titles.get(source_id, source_id)} ({', '.join(names)})"
            for source_id, names in sorted(by_source.items())
        )
        lines.append(f"Where these facts came from: {described}")
    if facts.attribution:
        lines.append(f"Credit: {facts.attribution}")
    for credit in credits or []:
        if credit.attribution and credit.id in by_source:
            lines.append(f"Credit: {credit.attribution}")
    return lines


def details_text(facts: StationFacts | None, credits: list[SourceCredit] | None = None) -> str:
    """The details pane's whole text, or the sentence for "nothing known"."""
    if facts is None:
        return "The station pack has nothing about this station."
    return "\n".join(details_lines(facts, credits))


def status_sentence(store: EnrichmentStore | None) -> str:
    """What is installed, in one sentence, for the top of the window."""
    if store is None:
        return "Station details are not available."
    try:
        total = store.count()
        built = store.built_at()
    except EnrichmentError:
        return "The station details could not be read."
    if not total:
        return (
            "No station pack is installed yet, so there are no station details "
            "to search. A pack arrives with a Quill Radio update."
        )
    return f"{total:,} stations with details, from the pack built {built[:10]}."


__all__ = [
    "bundled_dir",
    "details_lines",
    "details_text",
    "install_bundled",
    "install_pack_file",
    "open_store",
    "outcome_sentence",
    "refusal_sentence",
    "status_sentence",
]
