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

## Where it is used

Three settings, one control (Sound Enhancements > **Exact OptiLab processing**):

| Choice | What runs the polish |
| --- | --- |
| Off (the default) | The ffmpeg chain in `quill/core/optilab.py`, everywhere |
| When saving | The real engine on recordings and converted files; the chain live |
| When saving and while listening | The real engine on both |

**Saved files** are the easy case and the default recommendation. Recordings and
conversion already shell out to ffmpeg, offline; a file is processed once,
afterwards, with no live-preview property to protect and no reconnect to avoid.
A recording is post-processed **after** it finishes, never during -- an adapter
fault mid-capture must not be able to cost somebody the show they were recording.

## Why real-time playback is the hard case

Not impossible -- QUILL does it when asked -- but it cannot be free, and the
reasons are structural rather than a missing feature:

1. **It is a separate process, by upstream's own instruction.** `native/API.md`
   states the C++ API is *"not a stable C ABI"* and asks consumers to *"wrap this
   C++ class in a small adapter owned by your project"*. So the audio has to
   physically travel through another program. No filter string can express
   "someone else's DSP" to mpv or to ffmpeg, and mpv does not host CLAP, so the
   plug-in build is no use on this path either.
2. **Nothing on the live path ever holds a sample.** mpv is handed a filter
   string (`ui/audio/mpv_engine.py` sets `af`) and does all the work itself. That
   is the design's central virtue -- it is why every enhancement previews with no
   gap and no reconnect, and why one graph serves live radio, podcasts and
   recordings -- and it is exactly what an external engine cannot join.
3. **So live means relaying.** Decode the stream, pipe it through the engine,
   re-encode it, serve the result on a loopback URL (`EnhanceRelay.start` in
   `core/audio_enhance.py`). Three processes where there was none, and it costs:
   a slower start, an MP3 re-encode generation, more CPU, and a reconnect on
   **every** settings change -- the engine is prepared with a mode and a sample
   rate at start-up and cannot be re-parameterised mid-stream. "Hear it as you
   move the control" is precisely the property this option trades away.

The alternatives were considered and rejected: a custom libavfilter wrapping
`optilab-core` (heavy, and it needs an ffmpeg that will load it); an in-process
Python extension (a real-time callback beside a garbage-collected runtime, over
an ABI upstream explicitly does not offer); an mpv CLAP host (mpv has none).

The honest framing is therefore not "live is impossible" but **"live costs the
instant preview, and the listener chooses"** -- which is why the setting names the
surface rather than the engine, states the cost inside the option, and is off by
default.

## What the real engine actually gets you

The one difference that can be stated with confidence: upstream's limiter
feedback loop -- easing the lift and withdrawing bass assistance *while* final
limiting runs heavy -- cannot be expressed in a feed-forward ffmpeg graph at all.

Beyond that, the chain reproduces the *shape* of three modes and does not contain
upstream's gated AGC, six-band density processing, adaptive bass and top control,
stereo processing or hybrid final stage; its Podcast and Limiter ceilings (-1.5
and -2.0 dBFS) are QUILL's own, not upstream's -0.1, and its Input default is 0 dB
where upstream's `inputDriveDb` is 3.5.

On gentle material the two may be indistinguishable, and nothing here should
imply otherwise.

## Building

Optional. With no MSVC/CMake the adapter is simply absent, `optilab_adapter.available()`
is `False`, and every caller uses the ffmpeg chain exactly as before.

The supported way is the wrapper, which is also what the release builds call:

```powershell
python scripts\build_native_optilab.py
```

It configures and builds Release, then copies the executable **beside these
sources** (`quill/native/optilab/quill-optilab.exe`) -- the first place
`optilab_adapter.find_adapter` looks -- so a checkout that has built once is a
checkout where the end-to-end tests actually run rather than skip. With no
toolchain it prints what is missing and exits 0.

Or by hand:

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
