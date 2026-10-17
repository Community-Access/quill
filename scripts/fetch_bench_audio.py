"""Download the public speech datasets dictation's benchmark uses (dict.md B-1b).

**Dev-only.** Never shipped, never run by the app, never in an installer, and
never run by a test: the tests use tiny synthetic folders. It downloads only
when a person runs it and says yes::

    python scripts/fetch_bench_audio.py --list
    python scripts/fetch_bench_audio.py librispeech-test-clean          # asks first
    python scripts/fetch_bench_audio.py librispeech-test-clean --pin    # first fetch: pin the hash
    python scripts/fetch_bench_audio.py torgo --local D:/corpora/torgo  # by licence: your own copy
    python scripts/fetch_bench_audio.py --pin-subset librispeech-test-clean

Every dataset, with its licence, attribution, size, source and pinned SHA-256,
is in ``scripts/bench_datasets.json``. Then::

    python scripts/dictbench.py --dataset librispeech-test-clean --subset default

**Where it goes.** A cache *outside* the repository, so no audio can be
committed by accident: ``QUILL_BENCH_AUDIO`` when set, otherwise
``%LOCALAPPDATA%\\QUILL-bench\\bench-audio`` (``~/.cache/quill-bench/bench-audio``
elsewhere). A path inside the repository is refused.

**Checked.** Every archive is checked against its pinned SHA-256 before it is
unpacked; a mismatch deletes the download and stops. An archive with no pinned
hash is refused unless ``--pin`` is given, which downloads it, prints the hash
and writes it into ``bench_datasets.json`` for a person to review and commit.
Archives are unpacked with tarfile's ``data`` filter, so nothing lands outside
the dataset's own folder.

**By licence.** Datasets behind an account, a request or an agreement (Common
Voice, CHiME, TORGO, the Speech Accessibility Project and others) are never
fetched. The script prints where to ask for them, and ``--local PATH``
registers a copy you already have.

**Hosts it contacts** (it is outside ``quill/``, so the network egress audit
does not scan it; ``tests/unit/scripts/test_bench_datasets.py`` checks this
list against the JSON):

* www.openslr.org -- LibriSpeech and MUSAN
* huggingface.co -- FLEURS

Nothing is uploaded, and nothing is fetched in CI (``CI`` set) at all.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import sys
import tarfile
import urllib.parse
from collections.abc import Callable, Iterable
from pathlib import Path
from typing import Any

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO / "scripts") not in sys.path:
    sys.path.insert(0, str(_REPO / "scripts"))
DATASETS_FILE = _REPO / "scripts" / "bench_datasets.json"
SUBSETS_FILE = _REPO / "scripts" / "bench_subsets.json"
CACHE_VARIABLE = "QUILL_BENCH_AUDIO"
#: The hosts the archives may come from; the docstring names each one.
ALLOWED_HOSTS = frozenset({"www.openslr.org", "huggingface.co"})
PREPARED = "prepared"
SPEAKERS = "speakers.tsv"
SPEAKER_FIELDS = ("file", "speaker", "accent", "gender", "language", "group")
_CHUNK = 1 << 20


# --------------------------------------------------------------------------- #
# The table
# --------------------------------------------------------------------------- #


def load_table(path: Path = DATASETS_FILE) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def datasets(table: dict[str, Any] | None = None) -> dict[str, dict[str, Any]]:
    """``{id: entry}`` from ``bench_datasets.json``."""
    table = table if table is not None else load_table()
    return {entry["id"]: entry for entry in table["datasets"]}


def dataset(dataset_id: str, table: dict[str, Any] | None = None) -> dict[str, Any]:
    found = datasets(table).get(dataset_id)
    if found is None:
        raise SystemExit(f"Unknown dataset: {dataset_id}. Try --list.")
    return found


def may_be_in_training_data(entry: dict[str, Any], model_id: str) -> bool:
    """dict.md's contamination flag: the set is in *model_id*'s training data,
    or in everyone's (``"*"``)."""
    from bench_scoring import model_family

    named = entry.get("contaminated_models") or []
    return "*" in named or model_id in named or model_family(model_id) in named


# --------------------------------------------------------------------------- #
# The cache
# --------------------------------------------------------------------------- #


def cache_root() -> Path:
    """The cache folder, outside the repository. Refuses one inside it."""
    override = os.environ.get(CACHE_VARIABLE, "").strip()
    if override:
        root = Path(override)
    elif os.name == "nt" and os.environ.get("LOCALAPPDATA"):
        root = Path(os.environ["LOCALAPPDATA"]) / "QUILL-bench" / "bench-audio"
    else:
        root = Path.home() / ".cache" / "quill-bench" / "bench-audio"
    resolved = root.resolve()
    if resolved == _REPO or _REPO in resolved.parents:
        raise SystemExit(
            f"{resolved} is inside the repository. Benchmark audio is kept outside it, "
            f"so none can be committed; set {CACHE_VARIABLE} to a folder elsewhere."
        )
    return resolved


def dataset_folder(dataset_id: str) -> Path:
    return cache_root() / dataset_id


def prepared_folder(dataset_id: str) -> Path:
    """Where ``dictbench --dataset`` reads: WAVs, transcripts.txt, speakers.tsv.
    A ``--local`` registration points somewhere else."""
    link = dataset_folder(dataset_id) / "local.txt"
    if link.is_file():
        return Path(link.read_text(encoding="utf-8").strip())
    return dataset_folder(dataset_id) / PREPARED


# --------------------------------------------------------------------------- #
# Downloading and checking
# --------------------------------------------------------------------------- #


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(_CHUNK), b""):
            digest.update(block)
    return digest.hexdigest()


def check_host(url: str) -> None:
    host = urllib.parse.urlparse(url).hostname or ""
    if urllib.parse.urlparse(url).scheme != "https" or host not in ALLOWED_HOSTS:
        raise SystemExit(f"{url} is not on an allowed host ({', '.join(sorted(ALLOWED_HOSTS))}).")


def _download(url: str, target: Path) -> None:  # pragma: no cover - network, by a person only
    """Download *url* to *target*, resuming the ``.part`` file after a dropped
    connection (the first real fetch, 2026-10-17, was reset mid-file more than
    once). The SHA-256 check afterwards is what proves the bytes are whole."""
    import time
    import urllib.error
    import urllib.request

    check_host(url)
    partial = target.with_suffix(target.suffix + ".part")
    for attempt in range(8):
        done = partial.stat().st_size if partial.is_file() else 0
        headers = {"User-Agent": "QUILL-bench/1"}
        if done:
            headers["Range"] = f"bytes={done}-"
        request = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                resumed = done and response.status == 206
                total = int(response.headers.get("Content-Length") or 0) + (done if resumed else 0)
                with partial.open("ab" if resumed else "wb") as out:
                    done = done if resumed else 0
                    for block in iter(lambda: response.read(_CHUNK), b""):
                        out.write(block)
                        done += len(block)
                        if total:
                            print(f"  {done * 100 // total}%", end="\r")
            break
        except (urllib.error.URLError, OSError) as error:
            if attempt == 7:
                raise
            print(f"\n  connection lost ({error}); resuming")
            time.sleep(2 + 2 * attempt)
    partial.replace(target)
    print()


def verify(path: Path, expected: str | None) -> str:
    """The file's SHA-256; a mismatch deletes it and stops."""
    actual = sha256_of(path)
    if expected and actual != expected.lower():
        path.unlink(missing_ok=True)
        raise SystemExit(
            f"{path.name}: SHA-256 {actual} does not match the pinned {expected}. "
            "The download was deleted. Check the source before pinning a new hash."
        )
    return actual


def safe_unpack(archive: Path, into: Path) -> None:
    """Unpack *archive* with tarfile's ``data`` filter: no absolute paths, no
    ``..``, no links out of *into*, no device files."""
    into.mkdir(parents=True, exist_ok=True)
    with tarfile.open(archive) as tar:
        tar.extractall(into, filter="data")


def fetch(
    entry: dict[str, Any],
    *,
    pin: bool,
    confirm: Callable[[str], bool],
    download: Callable[[str, Path], None] = _download,
) -> list[tuple[str, str]]:
    """Download, verify and unpack every archive of *entry*.

    Returns ``(url, sha256)`` for each archive, so ``--pin`` can record them.
    """
    if os.environ.get("CI"):
        raise SystemExit("Benchmark audio is never downloaded in CI.")
    access = entry.get("access")
    if access != "auto":
        raise SystemExit(by_request_sentence(entry))
    unpinned = [a["url"] for a in entry["archives"] if not a.get("sha256")]
    if unpinned and not pin:
        raise SystemExit(
            f"{entry['id']} has no pinned SHA-256 yet. Run again with --pin to download it, "
            "record its hash in bench_datasets.json, and review that change before committing."
        )
    question = (
        f"{entry['name']}: {entry['size']}. Licence: {entry['licence']}. "
        f"Download to {dataset_folder(entry['id'])}?"
    )
    if not confirm(question):
        raise SystemExit("Nothing was downloaded.")
    folder = dataset_folder(entry["id"])
    raw = folder / "raw"
    raw.mkdir(parents=True, exist_ok=True)
    recorded: list[tuple[str, str]] = []
    for archive in entry["archives"]:
        check_host(archive["url"])
        name = Path(urllib.parse.urlparse(archive["url"]).path).name
        target = raw / name
        if not target.is_file():
            print(f"Downloading {archive['url']}")
            download(archive["url"], target)
        digest = verify(target, archive.get("sha256"))
        recorded.append((archive["url"], digest))
        if name.endswith((".tar.gz", ".tgz", ".tar")):
            safe_unpack(target, raw / "unpacked")
    (folder / "ATTRIBUTION.txt").write_text(attribution_text(entry), encoding="utf-8")
    return recorded


def write_pins(recorded: Iterable[tuple[str, str]], path: Path = DATASETS_FILE) -> None:
    """Record downloaded hashes in the table, for a person to review and commit."""
    hashes = dict(recorded)
    table = load_table(path)
    for entry in table["datasets"]:
        for archive in entry["archives"]:
            if archive["url"] in hashes:
                archive["sha256"] = hashes[archive["url"]]
    path.write_text(json.dumps(table, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def by_request_sentence(entry: dict[str, Any]) -> str:
    if entry.get("access") == "not_usable":
        return f"{entry['name']} is not usable by QUILL: {entry['licence']}."
    if entry.get("access") == "assets":
        return (
            f"{entry['name']} is built by scripts/bench_librivox.py, or downloaded from "
            "QUILL's assets-v1 release once it is published. Register a built copy with --local."
        )
    where = entry.get("licence_url") or entry.get("source_url") or "its publisher"
    return (
        f"{entry['name']} is never downloaded automatically ({entry['licence']}). "
        f"Ask for it at {where}, then register your copy with --local PATH."
    )


def attribution_text(entry: dict[str, Any]) -> str:
    return (
        f"{entry['name']}\n{entry['attribution']}\nLicence: {entry['licence']}\n"
        f"Source: {entry['source_url']}\n"
    )


def register_local(entry: dict[str, Any], path: Path) -> Path:
    """Point ``--dataset ID`` at a folder you already have (by-licence sets)."""
    if not (path / "transcripts.txt").is_file():
        raise SystemExit(
            f"{path} has no transcripts.txt. Prepare it as dictbench expects: 16 kHz mono "
            "WAVs, transcripts.txt, and optionally speakers.tsv."
        )
    folder = dataset_folder(entry["id"])
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "local.txt").write_text(str(path.resolve()), encoding="utf-8")
    return path


# --------------------------------------------------------------------------- #
# Preparing: every layout becomes WAVs + transcripts.txt + speakers.tsv
# --------------------------------------------------------------------------- #


def write_prepared(
    out: Path, rows: Iterable[tuple[str, str, dict[str, str]]], audio: Callable[[str, Path], None]
) -> int:
    """Write *rows* (name, text, speaker fields) with *audio* making each WAV."""
    out.mkdir(parents=True, exist_ok=True)
    transcripts: list[str] = []
    speakers: list[str] = ["\t".join(SPEAKER_FIELDS)]
    count = 0
    for name, text, fields in rows:
        audio(name, out / name)
        transcripts.append(f"{name}\t{text}")
        speakers.append("\t".join([name, *[fields.get(f, "") for f in SPEAKER_FIELDS[1:]]]))
        count += 1
    (out / "transcripts.txt").write_text("\n".join(transcripts) + "\n", encoding="utf-8")
    (out / SPEAKERS).write_text("\n".join(speakers) + "\n", encoding="utf-8")
    return count


def librispeech_rows(unpacked: Path) -> list[tuple[str, str, dict[str, str], Path]]:
    """LibriSpeech's ``*.trans.txt`` and ``SPEAKERS.TXT`` as rows.

    Its transcripts are upper case with no punctuation, so only word errors mean
    anything on it; punctuation scores are left out for this layout.
    """
    genders: dict[str, str] = {}
    for speakers_file in unpacked.rglob("SPEAKERS.TXT"):
        for line in speakers_file.read_text(encoding="utf-8", errors="replace").splitlines():
            if line.startswith(";") or "|" not in line:
                continue
            parts = [part.strip() for part in line.split("|")]
            genders[parts[0]] = {"F": "female", "M": "male"}.get(parts[1], "")
    rows: list[tuple[str, str, dict[str, str], Path]] = []
    for trans in sorted(unpacked.rglob("*.trans.txt")):
        for line in trans.read_text(encoding="utf-8").splitlines():
            utterance, _sep, text = line.partition(" ")
            if not text:
                continue
            speaker = utterance.split("-")[0]
            fields = {"speaker": speaker, "gender": genders.get(speaker, ""), "language": "en"}
            source = trans.parent / f"{utterance}.flac"
            rows.append((f"{utterance}.wav", text.strip().lower(), fields, source))
    return rows


def fleurs_rows(
    raw: Path, unpacked: Path, language: str
) -> list[tuple[str, str, dict[str, str], Path]]:
    """FLEURS's ``test.tsv`` (id, file, raw transcription, normalised, words,
    samples, gender) as rows; the raw transcription keeps punctuation."""
    rows: list[tuple[str, str, dict[str, str], Path]] = []
    for tsv in sorted(raw.glob("*.tsv")):
        for line in tsv.read_text(encoding="utf-8").splitlines():
            parts = line.split("\t")
            if len(parts) < 3:
                continue
            speaker_id, file_name, text = parts[0], parts[1], parts[2]
            gender = parts[6].strip().lower() if len(parts) > 6 else ""
            found = next(unpacked.rglob(file_name), None)
            if found is None:
                continue
            name = Path(file_name).with_suffix(".wav").name
            fields = {"speaker": speaker_id, "gender": gender, "language": language}
            rows.append((name, text.strip(), fields, found))
    return rows


def to_wav16(source: Path, target: Path) -> None:
    """Any file soundfile reads, as 16 kHz mono 16-bit WAV."""
    import numpy as np
    import soundfile as sf

    samples, rate = sf.read(str(source), dtype="float32", always_2d=True)
    mono = samples.mean(axis=1)
    if rate != 16_000:
        mono = resample(mono, rate, 16_000)
    sf.write(str(target), np.clip(mono, -1.0, 1.0), 16_000, subtype="PCM_16")


def resample(samples: Any, source_rate: int, target_rate: int) -> Any:
    """Band-limited resampling by Fourier transform: no scipy needed, and good
    enough for clips of a few seconds to a few minutes."""
    import numpy as np

    samples = np.asarray(samples, dtype=np.float32)
    if source_rate == target_rate or samples.size == 0:
        return samples
    count = max(1, round(samples.size * target_rate / source_rate))
    spectrum = np.fft.rfft(samples)
    keep = count // 2 + 1
    resized = np.zeros(keep, dtype=spectrum.dtype)
    resized[: min(keep, spectrum.size)] = spectrum[: min(keep, spectrum.size)]
    out = np.fft.irfft(resized, n=count) * (count / samples.size)
    return out.astype(np.float32)


def prepare(entry: dict[str, Any]) -> int:
    """Turn the unpacked download into the folder dictbench reads."""
    layout = entry.get("layout")
    folder = dataset_folder(entry["id"])
    raw = folder / "raw"
    unpacked = raw / "unpacked"
    if layout == "noise":
        return 0  # used raw, by bench_commands.py --noise
    if layout == "librispeech":
        rows = librispeech_rows(unpacked)
    elif layout == "fleurs":
        rows = fleurs_rows(raw, unpacked, (entry.get("languages") or ["en"])[0])
    else:
        raise SystemExit(f"{entry['id']} has no automatic preparation; use --local.")
    sources = {name: source for name, _text, _fields, source in rows}
    out = folder / PREPARED
    return write_prepared(
        out,
        ((name, text, fields) for name, text, fields, _source in rows),
        lambda name, target: to_wav16(sources[name], target),
    )


# --------------------------------------------------------------------------- #
# Fixed, seeded subsets
# --------------------------------------------------------------------------- #


def read_speakers(folder: Path) -> dict[str, dict[str, str]]:
    """``{file: {speaker, accent, gender, language, group}}`` from speakers.tsv."""
    path = folder / SPEAKERS
    if not path.is_file():
        return {}
    lines = path.read_text(encoding="utf-8-sig").splitlines()
    if not lines:
        return {}
    header = lines[0].split("\t")
    found: dict[str, dict[str, str]] = {}
    for line in lines[1:]:
        if not line.strip() or line.startswith("#"):
            continue
        values = dict(zip(header, line.split("\t"), strict=False))
        name = values.pop("file", "")
        if name:
            found[name] = values
    return found


def seeded_subset(
    names: Iterable[str],
    *,
    seed: int,
    count: int,
    speakers: dict[str, dict[str, str]] | None = None,
    per_speaker: int = 0,
) -> list[str]:
    """*count* names chosen with *seed*, the same on every computer.

    With *per_speaker*, no speaker gives more than that many, so a prolific
    reader cannot dominate (B-1a's balance rule, applied to every set).
    """
    ordered = sorted(names)
    random.Random(seed).shuffle(ordered)
    chosen: list[str] = []
    taken: dict[str, int] = {}
    for name in ordered:
        speaker = (speakers or {}).get(name, {}).get("speaker", "")
        if per_speaker and speaker and taken.get(speaker, 0) >= per_speaker:
            continue
        chosen.append(name)
        taken[speaker] = taken.get(speaker, 0) + 1
        if len(chosen) >= count:
            break
    return sorted(chosen)


def load_subsets(path: Path = SUBSETS_FILE) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def subset_names(
    dataset_id: str, subset: str, folder: Path, path: Path = SUBSETS_FILE
) -> list[str]:
    """The stored names of *subset*, or -- when not pinned yet -- the seeded
    choice from what is in *folder* (and a note saying so)."""
    table = load_subsets(path)
    spec = table.get("subsets", {}).get(dataset_id, {}).get(subset)
    if spec is None:
        spec = table.get("defaults", {}).get(subset)
    if spec is None:
        raise SystemExit(f"No subset named {subset!r} for {dataset_id}.")
    if spec.get("names"):
        return list(spec["names"])
    from_folder = [
        line.split("\t", 1)[0].split(" ", 1)[0]
        for line in (folder / "transcripts.txt").read_text(encoding="utf-8-sig").splitlines()
        if line.strip() and not line.startswith("#")
    ]
    print(f"Note: subset {subset!r} of {dataset_id} is not pinned yet; chose it with its seed.")
    return seeded_subset(
        from_folder,
        seed=int(spec["seed"]),
        count=int(spec["count"]),
        speakers=read_speakers(folder),
        per_speaker=int(spec.get("per_speaker", 0)),
    )


def pin_subset(dataset_id: str, subset: str, path: Path = SUBSETS_FILE) -> list[str]:
    """Store the subset's names, so every run compares like with like."""
    folder = prepared_folder(dataset_id)
    names = subset_names(dataset_id, subset, folder, path)
    table = load_subsets(path)
    base = dict(table.get("defaults", {}).get(subset, {}))
    entry = table.setdefault("subsets", {}).setdefault(dataset_id, {}).setdefault(subset, base)
    entry["names"] = names
    path.write_text(json.dumps(table, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return names


# --------------------------------------------------------------------------- #
# The command line
# --------------------------------------------------------------------------- #


def describe(entry: dict[str, Any]) -> str:
    pinned = all(a.get("sha256") for a in entry["archives"]) if entry["archives"] else None
    state = {True: "pinned", False: "not pinned", None: "no archive"}[pinned]
    return (
        f"{entry['id']:30} {entry['part']:5} {entry['access']:11} {entry['size']:>18}  "
        f"{state:10} {entry['licence'][:60]}"
    )


def _ask(question: str) -> bool:  # pragma: no cover - a person answers
    return input(f"{question} [y/N] ").strip().lower() in {"y", "yes"}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("dataset", nargs="?", help="a dataset id (see --list)")
    parser.add_argument("--list", action="store_true", help="every dataset and its licence")
    parser.add_argument(
        "--pin", action="store_true", help="download an unpinned archive and record its hash"
    )
    parser.add_argument("--yes", action="store_true", help="do not ask before downloading")
    parser.add_argument("--local", type=Path, help="register a copy you already have")
    parser.add_argument("--pin-subset", metavar="ID", help="store the default subset's names")
    parser.add_argument("--subset", default="default", help="which subset --pin-subset stores")
    args = parser.parse_args(argv)

    if args.list:
        for entry in datasets().values():
            print(describe(entry))
        print(f"Cache: {cache_root()}")
        return 0
    if args.pin_subset:
        names = pin_subset(args.pin_subset, args.subset)
        print(f"Stored {len(names)} names for {args.pin_subset} ({args.subset}).")
        return 0
    if not args.dataset:
        parser.error("name a dataset, or use --list")
    entry = dataset(args.dataset)
    if args.local:
        register_local(entry, args.local)
        print(f"{entry['id']} now reads {args.local}.")
        return 0
    recorded = fetch(entry, pin=args.pin, confirm=(lambda _q: True) if args.yes else _ask)
    if args.pin:
        write_pins(recorded)
        print("Hashes written to bench_datasets.json. Review the change before committing it.")
    files = prepare(entry)
    print(f"{entry['id']}: {files} recordings ready in {prepared_folder(entry['id'])}.")
    print(f"Attribution: {dataset_folder(entry['id']) / 'ATTRIBUTION.txt'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
