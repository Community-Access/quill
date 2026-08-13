# OptiLab Core, and QUILL's adapter around it

## Attribution

**OptiLab Core is the work of Lanes Audio / dgl1984.**

- Repository: <https://github.com/dgl1984/optilab>
- Author: <https://github.com/dgl1984>
- Description (upstream): *"Free accessible broadcast and mastering plug-in from
  LanesAudio for REAPER JSFX, Windows CLAP, and Winamp-compatible DSP hosts."*

QUILL uses it with thanks. Everything in `upstream/` is theirs; the only file in
this directory QUILL wrote is `quill_optilab.cpp`, and it contains **no DSP**.

## What is vendored

`upstream/` holds OptiLab Core's processing engine, copied **unmodified** from
upstream at tag `v1.4.0` (commit `fb5c5b13fc4a06efadefaaff8ffd66ebe0b562bb`):

| File | Origin |
| --- | --- |
| `upstream/OptiLabCore.h` | `native/core/OptiLabCore.h` |
| `upstream/OptiLabCore.cpp` | `native/core/OptiLabCore.cpp` |
| `upstream/LICENSE` | repository root |
| `upstream/NOTICE` | repository root |

**Do not edit anything under `upstream/`.** To take a newer release, re-copy
those four files at the new tag, update the version and commit recorded here,
in `quill/core/optilab_adapter.py` and in `quill/core/compliance.py`, and re-read
upstream's `CHANGELOG.md` for anything that changes the *mapping* in
`quill/core/optilab.py`.

## Licence

**Apache License 2.0 with the Commons Clause License Condition v1.0**, from
upstream v1.3.0 onward. Both `upstream/LICENSE` and `upstream/NOTICE` ship
alongside the code and must continue to.

The Commons Clause withholds the right to **sell the Software** — that is, to
provide a product or service to third parties for a fee whose value derives
entirely or substantially from OptiLab Core's functionality.

Upstream's NOTICE separately and explicitly grants:

> *"Commercial use of OptiLab Core as a tool for producing, processing,
> mastering, broadcasting, streaming, or otherwise creating audio is permitted
> without royalties to Lanes Audio."*

QUILL is free, and Sound Enhancements is one optional feature among many, so
QUILL's use sits squarely inside the permitted grant. That is a fact to keep
true rather than one to assume: anything that made QUILL a paid product whose
value derived substantially from this engine would need this re-read first.

## Why an adapter executable

Upstream's own `native/API.md` is explicit:

> *"This is a C++ API, not a stable C ABI. If you need to call OptiLab Core from
> C, Rust, C#, Python, or another language, wrap this C++ class in a small
> adapter owned by your project."*

So QUILL owns one. It is a **process**, not a Python extension, for the same
reason ffmpeg is: QUILL's offline audio paths already drive ffmpeg through
`stability.safe_subprocess` with an argv list and never a shell, so this slots
into an established pattern — no new failure mode, no in-process native crash
surface, and no ABI to keep in step across releases.

## Where it is and is not used

**Used:** saved files — radio recordings and audio conversion. Those already
shell out to ffmpeg, offline, with no live-preview property to protect.

**Not used, permanently:** live playback. mpv applies enhancement natively from
a filter string (`ui/audio/mpv_engine.py` sets `af`) and nothing on that path
ever holds a PCM sample in Python. Routing live audio through a subprocess would
reintroduce a relay everywhere and cost the live preview that path exists to
provide. Live playback keeps the ffmpeg chain in `quill/core/optilab.py`.

The single honest difference between the two: upstream's limiter feedback loop —
easing the lift while final limiting runs heavy — cannot be expressed in a
feed-forward ffmpeg graph at all.

## Building

Optional. With no MSVC/CMake the adapter is simply absent, `optilab_adapter.available()`
is `False`, and every caller uses the ffmpeg chain exactly as before.

```powershell
cmake -S quill/native/optilab -B quill/native/optilab/build
cmake --build quill/native/optilab/build --config Release
```

The executable lands at `build/Release/quill-optilab.exe` and is found
automatically. `QUILL_OPTILAB_ADAPTER` overrides the location.

## Protocol

```
quill-optilab --mode <podcast|stream|limiter> --rate <hz>
              [--channels <1|2>] [--input-db <db>] [--adapt <0-100>]
```

Interleaved 32-bit float PCM in on stdin, the same out on stdout. The format is
fixed and unnegotiated on purpose: the caller is ffmpeg, told exactly what to
emit (`-f f32le`), so there is no header to mis-parse. Exit codes: `0` success,
`2` bad arguments, `3` I/O failure.
