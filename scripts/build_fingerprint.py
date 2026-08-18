"""Capture what a build machine actually is, and diff two of them.

WHY THIS EXISTS
---------------
``quillville-runtime.spec`` builds with ``collect_all("quill")``, so PyInstaller
ships whatever happens to be importable on the machine that runs it. Two
checkouts at the same commit therefore produce different installers, and the
only symptom is the file size. ``check_build_env.py`` guards the floor (is
everything ``[runtime]`` needs present?) and ``check_runtime_inventory.py``
guards the ceiling (did a package appear or vanish?), but neither answers the
question you actually have when two machines disagree: *what is different
between them, and which one is right?*

This does. Run ``capture`` on each machine, carry one JSON to the other, run
``compare``. The report is exhaustive and boring on purpose: interpreter,
every installed distribution and its version, the SHA-256 of every staged
binary dependency, the size of every top-level item in the built runtime, and
the size of every release artifact. Whatever is making one machine's installer
bigger is in that list.

Usage::

    # on each machine, at the checkout root
    python scripts/build_fingerprint.py capture --label work -o work.json
    python scripts/build_fingerprint.py capture --label home -o home.json

    # then, with both files in one place
    python scripts/build_fingerprint.py compare work.json home.json

Not to be confused with ``scripts/footprint_report.py``, which measures an
*installed build tree* release-over-release for the AI footprint/optimization
phase. This one measures the *build machine* -- its interpreter, its installed
distributions, its staged binaries -- because that is what decides what the next
installer contains.

``capture`` reads only; it never installs, builds, or modifies anything. Parts
of the fingerprint that need something not present (no built runtime, no staged
ffmpeg, no git) are recorded as absent rather than failing, so a fresh clone
still produces a usable file.

``compare`` always exits 0 so a human can read a drifted report in peace;
``--fail-on-drift`` makes it exit 1 when anything that can change what a build
ships differs (interpreter version, packages, staged binaries, runtime
contents, artifact sizes), so it can gate CI. Machine identity -- commit,
branch, dirty state, interpreter path, OS -- never counts: two machines
legitimately differ there.

Output is plain ASCII, one fact per line, for screen-reader review.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import subprocess
import sys
import sysconfig
from importlib import metadata
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]

#: Binaries staged by scripts/fetch_build_deps.py and copied verbatim into the
#: shipped runtime. These are pinned by SHA-256 upstream, so a mismatch here
#: means one machine is building from something other than the pinned asset --
#: the single most consequential difference two machines can have, because it
#: is 300 MB of the payload and it is not caught by any import-based gate.
_STAGED_BINARIES = (
    "build/deps/ffmpeg/ffmpeg.exe",
    "build/deps/ffmpeg/ffprobe.exe",
    "build/deps/mpv/libmpv-2.dll",
)

#: Built runtime dists worth measuring, relative to the checkout root.
_RUNTIME_DIST = "standalone/runtime/dist/QuillVilleRuntime"

#: Where each app drops its release artifacts. The main QUILL editor builds to
#: dist/windows (slim) and dist/windows-offline (Offline Edition): the portable
#: zip sits at the top of each tree and the compiled Setup.exe under
#: installer/Output. Deliberately not dist/** -- the portable/ tree is build
#: payload (python313.zip, launcher exes), not artifacts.
_DIST_GLOBS = (
    "standalone/*/dist/*.exe",
    "standalone/*/dist/*.zip",
    "dist/windows*/*.zip",
    "dist/windows*/installer/Output/*.exe",
)


def _run(args: list[str], cwd: Path | None = None) -> str | None:
    """Stdout of *args*, or None if the command is missing or fails."""
    try:
        result = subprocess.run(
            args, cwd=cwd, capture_output=True, text=True, timeout=60, check=False
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if result.returncode != 0:
        return None
    return result.stdout.strip()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _tree_size(path: Path) -> int:
    if path.is_file():
        return path.stat().st_size
    return sum(p.stat().st_size for p in path.rglob("*") if p.is_file())


def _git(repo: Path) -> dict[str, object]:
    commit = _run(["git", "rev-parse", "HEAD"], cwd=repo)
    branch = _run(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=repo)
    status = _run(["git", "status", "--porcelain"], cwd=repo)
    return {
        "commit": commit,
        "branch": branch,
        "dirty": bool(status) if status is not None else None,
        "changed_files": len(status.splitlines()) if status else 0,
    }


def _interpreter() -> dict[str, object]:
    stdlib = Path(sysconfig.get_paths()["stdlib"])
    return {
        "executable": sys.executable,
        "version": platform.python_version(),
        "implementation": platform.python_implementation(),
        "externally_managed": (stdlib / "EXTERNALLY-MANAGED").exists(),
        "os": f"{platform.system()} {platform.release()} ({platform.machine()})",
    }


def _packages() -> dict[str, str]:
    """Every installed distribution -> version, normalized and sorted.

    ``importlib.metadata`` rather than shelling out to pip: it reports what
    *this* interpreter can import, which is exactly what PyInstaller will sweep.
    """
    found: dict[str, str] = {}
    for dist in metadata.distributions():
        name = (dist.metadata["Name"] or "").strip()
        if not name:
            continue
        found[name.casefold().replace("_", "-")] = dist.version or "?"
    return dict(sorted(found.items()))


def _staged(repo: Path) -> dict[str, object]:
    out: dict[str, object] = {}
    for rel in _STAGED_BINARIES:
        path = repo / rel
        if path.is_file():
            out[rel] = {"bytes": path.stat().st_size, "sha256": _sha256(path)}
        else:
            out[rel] = None
    return out


def _runtime_contents(repo: Path) -> dict[str, object] | None:
    """Byte size of every top-level item in the built runtime, if one exists.

    Sizes, not just names: ``check_runtime_inventory.py`` already answers
    "which packages are here"; the question this file exists for is "which of
    them is 60 MB bigger over there".
    """
    dist = repo / _RUNTIME_DIST
    if not (dist / "QuillVilleRuntime.exe").is_file():
        return None
    areas: dict[str, object] = {"total_bytes": _tree_size(dist)}
    for area in ("_internal", "tools"):
        base = dist / area
        if not base.is_dir():
            continue
        areas[area] = dict(
            sorted(
                ((item.name, _tree_size(item)) for item in base.iterdir()),
                key=lambda pair: -pair[1],
            )
        )
    marker = dist / "quillville-runtime.json"
    if marker.is_file():
        try:
            areas["marker"] = json.loads(marker.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            areas["marker"] = None
    return areas


def _artifacts(repo: Path) -> dict[str, int]:
    found: dict[str, int] = {}
    for pattern in _DIST_GLOBS:
        for path in repo.glob(pattern):
            found[path.relative_to(repo).as_posix()] = path.stat().st_size
    return dict(sorted(found.items()))


def capture(repo: Path, label: str) -> dict[str, object]:
    return {
        "schema": 1,
        "label": label,
        "repo": str(repo),
        "git": _git(repo),
        "interpreter": _interpreter(),
        "packages": _packages(),
        "staged_binaries": _staged(repo),
        "runtime": _runtime_contents(repo),
        "artifacts": _artifacts(repo),
    }


# -- comparison ---------------------------------------------------------------


def _mb(value: float) -> str:
    return f"{value / 1024 / 1024:,.1f} MB"


def _heading(text: str) -> None:
    print()
    print(text)
    print("-" * len(text))


def _compare_packages(a: dict[str, object], b: dict[str, object]) -> int:
    left: dict[str, str] = a["packages"]  # type: ignore[assignment]
    right: dict[str, str] = b["packages"]  # type: ignore[assignment]
    only_left = sorted(set(left) - set(right))
    only_right = sorted(set(right) - set(left))
    differing = sorted(n for n in set(left) & set(right) if left[n] != right[n])

    _heading("Installed packages")
    print(f"  {a['label']}: {len(left)} distributions; {b['label']}: {len(right)}")
    if only_left:
        print(f"  only on {a['label']} ({len(only_left)}):")
        for name in only_left:
            print(f"    - {name} {left[name]}")
    if only_right:
        print(f"  only on {b['label']} ({len(only_right)}):")
        for name in only_right:
            print(f"    - {name} {right[name]}")
    if differing:
        print(f"  different versions ({len(differing)}):")
        for name in differing:
            print(f"    - {name}: {a['label']} {left[name]} vs {b['label']} {right[name]}")
    if not (only_left or only_right or differing):
        print("  identical.")
    return len(only_left) + len(only_right) + len(differing)


def _compare_staged(a: dict[str, object], b: dict[str, object]) -> int:
    left: dict[str, object] = a["staged_binaries"]  # type: ignore[assignment]
    right: dict[str, object] = b["staged_binaries"]  # type: ignore[assignment]
    _heading("Staged binary dependencies (ffmpeg, mpv)")
    drift = 0
    for rel in sorted(set(left) | set(right)):
        one, two = left.get(rel), right.get(rel)
        if one is None and two is None:
            print(f"  {rel}: absent on both")
        elif one is None or two is None:
            present = a["label"] if two is None else b["label"]
            print(f"  {rel}: present only on {present}")
            drift += 1
        elif one["sha256"] != two["sha256"]:  # type: ignore[index]
            print(f"  {rel}: DIFFERENT BYTES")
            print(f"    {a['label']}: {_mb(one['bytes'])}  sha256 {one['sha256'][:16]}...")  # type: ignore[index]
            print(f"    {b['label']}: {_mb(two['bytes'])}  sha256 {two['sha256'][:16]}...")  # type: ignore[index]
            drift += 1
        else:
            print(f"  {rel}: identical ({_mb(one['bytes'])})")  # type: ignore[index]
    return drift


def _compare_runtime(a: dict[str, object], b: dict[str, object]) -> int:
    left = a.get("runtime")
    right = b.get("runtime")
    _heading("Built shared runtime")
    if not left or not right:
        missing = [f["label"] for f in (a, b) if not f.get("runtime")]
        print(f"  no built runtime on: {', '.join(str(m) for m in missing)}")
        print("  (build one with standalone\\runtime\\build_runtime.ps1 to compare contents)")
        # Absence of data, not drift: capture works on a fresh clone on purpose.
        return 0

    total_a, total_b = left["total_bytes"], right["total_bytes"]  # type: ignore[index]
    print(f"  total: {a['label']} {_mb(total_a)} vs {b['label']} {_mb(total_b)}")
    delta = total_a - total_b  # type: ignore[operator]
    if delta:
        side = "larger" if delta > 0 else "smaller"
        print(f"  difference: {_mb(abs(delta))} {side} on {a['label']}")
    else:
        print("  difference: none")

    drift = 0
    for area in ("_internal", "tools"):
        one: dict[str, int] = left.get(area) or {}  # type: ignore[assignment]
        two: dict[str, int] = right.get(area) or {}  # type: ignore[assignment]
        rows = []
        for name in set(one) | set(two):
            rows.append((name, one.get(name, 0), two.get(name, 0)))
        rows = [r for r in rows if r[1] != r[2]]
        rows.sort(key=lambda r: -abs(r[1] - r[2]))
        print(f"  {area}: {len(rows)} item(s) differ")
        for name, size_a, size_b in rows[:25]:
            if not size_b:
                print(f"    - {name}: only on {a['label']} ({_mb(size_a)})")
            elif not size_a:
                print(f"    - {name}: only on {b['label']} ({_mb(size_b)})")
            else:
                print(f"    - {name}: {_mb(size_a)} vs {_mb(size_b)}")
        if len(rows) > 25:
            print(f"    ... and {len(rows) - 25} more")
        drift += len(rows)
    if not drift and delta:
        # Only root-level files differ (nothing in _internal or tools moved);
        # still a real content difference.
        drift = 1
    return drift


def _compare_simple(a: dict[str, object], b: dict[str, object]) -> int:
    drift = 0
    _heading("Checkout and interpreter")
    for field, section in (("commit", "git"), ("branch", "git"), ("dirty", "git")):
        one = (a[section] or {}).get(field)  # type: ignore[union-attr,index]
        two = (b[section] or {}).get(field)  # type: ignore[union-attr,index]
        flag = "" if one == two else "   <-- differs"
        print(f"  {field}: {a['label']} {one} | {b['label']} {two}{flag}")
    # Machine identity (executable path, OS) is context; the interpreter version
    # and its managed state decide which wheels install, so those two are drift.
    for field in ("version", "executable", "os", "externally_managed"):
        one = a["interpreter"][field]  # type: ignore[index]
        two = b["interpreter"][field]  # type: ignore[index]
        flag = "" if one == two else "   <-- differs"
        print(f"  {field}: {a['label']} {one} | {b['label']} {two}{flag}")
        if one != two and field in ("version", "externally_managed"):
            drift += 1

    _heading("Release artifacts")
    one_art: dict[str, int] = a["artifacts"]  # type: ignore[assignment]
    two_art: dict[str, int] = b["artifacts"]  # type: ignore[assignment]
    for name in sorted(set(one_art) | set(two_art)):
        size_a, size_b = one_art.get(name), two_art.get(name)
        if size_a is None:
            print(f"  {name}: only on {b['label']} ({_mb(size_b)})")
            drift += 1
        elif size_b is None:
            print(f"  {name}: only on {a['label']} ({_mb(size_a)})")
            drift += 1
        elif size_a != size_b:
            print(f"  {name}: {_mb(size_a)} vs {_mb(size_b)}  (delta {_mb(abs(size_a - size_b))})")
            drift += 1
        else:
            print(f"  {name}: identical ({_mb(size_a)})")
    return drift


def compare(a: dict[str, object], b: dict[str, object]) -> int:
    """Print the full report; return how many ship-affecting differences it found."""
    print(f"Comparing '{a['label']}' (left) against '{b['label']}' (right).")
    drift = _compare_simple(a, b)
    drift += _compare_staged(a, b)
    drift += _compare_packages(a, b)
    drift += _compare_runtime(a, b)
    _heading("What to do with this")
    print("  - packages only on one side are the usual cause of an installer size gap:")
    print("    collect_all() sweeps them in. Uninstall the stray, or add it to")
    print("    pyproject [runtime] if it is genuinely needed, then rebaseline")
    print("    standalone/runtime/runtime-inventory.json with --write.")
    print("  - a staged-binary SHA mismatch means one machine is not building from")
    print("    the pinned asset. Re-stage with:")
    print("      python scripts/fetch_build_deps.py --only ffmpeg --force")
    print("  - a git commit difference explains everything else; sync that first.")
    _heading("Drift")
    if drift:
        print(f"  {drift} difference(s) that can change what a build ships.")
    else:
        print("  none.")
    print("  (commit, branch, dirty state, interpreter path and OS are context,")
    print("  not drift: two machines legitimately differ there.)")
    return drift


def _load(path: Path) -> dict[str, object]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema") != 1:
        raise SystemExit(f"{path}: unknown fingerprint schema {data.get('schema')!r}")
    return data


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    sub = parser.add_subparsers(dest="command", required=True)

    cap = sub.add_parser("capture", help="write this machine's build fingerprint")
    cap.add_argument("--label", default=platform.node() or "this-machine")
    cap.add_argument("-o", "--out", type=Path, default=Path("build-fingerprint.json"))
    cap.add_argument("--repo", type=Path, default=_REPO_ROOT)

    cmp_ = sub.add_parser("compare", help="diff two fingerprints")
    cmp_.add_argument("left", type=Path)
    cmp_.add_argument("right", type=Path)
    cmp_.add_argument(
        "--fail-on-drift",
        action="store_true",
        help="exit 1 if anything that can change what a build ships differs "
        "(machine identity -- commit, branch, paths -- never counts)",
    )

    args = parser.parse_args()

    if args.command == "capture":
        data = capture(args.repo.resolve(), args.label)
        args.out.write_text(json.dumps(data, indent=2), encoding="utf-8")
        runtime = data["runtime"]
        print(f"Fingerprint for '{args.label}' written to {args.out}")
        print(
            f"  interpreter: {data['interpreter']['executable']} ({data['interpreter']['version']})"
        )  # type: ignore[index]
        print(f"  packages:    {len(data['packages'])}")  # type: ignore[arg-type]
        print(f"  commit:      {data['git']['commit']} (dirty: {data['git']['dirty']})")  # type: ignore[index]
        print(f"  runtime:     {_mb(runtime['total_bytes']) if runtime else 'not built'}")  # type: ignore[index]
        print(f"  artifacts:   {len(data['artifacts'])}")  # type: ignore[arg-type]
        return 0

    drift = compare(_load(args.left), _load(args.right))
    if args.fail_on_drift and drift:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
