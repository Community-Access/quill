// QUILL's adapter around OptiLab Core -- a stdin/stdout PCM filter.
//
// UPSTREAM AND ATTRIBUTION
// ------------------------
// OptiLab Core is by **Lanes Audio / dgl1984**:
//
//     https://github.com/dgl1984/optilab          (the repository)
//     https://github.com/dgl1984                  (the author)
//
// The processing engine in upstream/OptiLabCore.{h,cpp} is *their* work,
// vendored unmodified at tag v1.4.0 (commit fb5c5b13fc4a06efadefaaff8ffd66eb
// e0b562bb). Licensed Apache-2.0 **with the Commons Clause v1.0** -- see
// upstream/LICENSE and upstream/NOTICE, both shipped alongside it. Their NOTICE
// grants royalty-free commercial use of OptiLab Core as a tool for producing,
// processing, broadcasting or streaming audio; the Commons Clause withholds the
// right to sell the Software itself, which QUILL does not do.
//
// Only this file is QUILL's. It contains no DSP.
//
// WHY AN ADAPTER RATHER THAN A BINDING
// ------------------------------------
// Upstream's own native/API.md is explicit: "This is a C++ API, not a stable C
// ABI. If you need to call OptiLab Core from C, Rust, C#, Python, or another
// language, wrap this C++ class in a small adapter owned by your project."
// This is that adapter, and owning it is the point -- an ABI we do not control
// is not something to expose to a Python extension across releases.
//
// It is a **process**, not a library, for the same reason ffmpeg is: QUILL's
// offline audio paths (radio recording, conversion, the enhancement relay)
// already drive ffmpeg through stability.safe_subprocess with an argv list and
// never a shell. This slots into that pattern exactly, which means no new
// failure mode, no in-process native crash surface, and no GIL questions.
//
// It is deliberately NOT used for live playback. Live enhancement is applied by
// mpv natively from a filter string (ui/audio/mpv_engine.py sets "af"), and
// nothing in that path ever holds a PCM sample in Python. Piping live audio
// through a subprocess would reintroduce a relay everywhere and cost the live
// preview that path exists to provide. See quill/core/optilab.py.
//
// PROTOCOL
// --------
//   quill-optilab --mode <podcast|stream|limiter> --rate <hz>
//                 [--channels <n>] [--input-db <db>] [--adapt <0-100>]
//
// Reads interleaved 32-bit float PCM on stdin, writes the same on stdout, in
// blocks. Format is fixed and unnegotiated on purpose: the caller is ffmpeg,
// which is told exactly what to emit (-f f32le), so there is no header to
// mis-parse and no format negotiation to get wrong.
//
// Exit codes: 0 success, 2 bad arguments, 3 I/O failure.

#include "upstream/OptiLabCore.h"

#include <cstdio>
#include <cstring>
#include <cstdlib>
#include <string>
#include <vector>

#ifdef _WIN32
#include <fcntl.h>
#include <io.h>
#endif

namespace {

// One block of frames per read. Large enough that the syscall cost disappears,
// small enough that a caller which stops reading is noticed promptly rather
// than after a buffer measured in seconds.
constexpr std::size_t kFramesPerBlock = 4096;

int usage(const char* message) {
    if (message != nullptr) {
        std::fprintf(stderr, "quill-optilab: %s\n", message);
    }
    std::fprintf(stderr,
                 "usage: quill-optilab --mode <podcast|stream|limiter> --rate <hz>\n"
                 "                     [--channels <n>] [--input-db <db>] [--adapt <0-100>]\n"
                 "\n"
                 "Reads interleaved f32le PCM on stdin, writes it on stdout.\n"
                 "OptiLab Core (c) Lanes Audio / dgl1984 -- https://github.com/dgl1984/optilab\n");
    return 2;
}

bool parse_mode(const std::string& text, OptiLabCore::Mode& out) {
    if (text == "podcast") {
        out = OptiLabCore::Mode::PodcastLeveler;
    } else if (text == "stream") {
        out = OptiLabCore::Mode::StreamPolish;
    } else if (text == "limiter") {
        out = OptiLabCore::Mode::SmoothLimiter;
    } else {
        return false;
    }
    return true;
}

double clamp(double value, double low, double high) {
    return value < low ? low : (value > high ? high : value);
}

}  // namespace

int main(int argc, char** argv) {
    OptiLabCore::Mode mode = OptiLabCore::Mode::PodcastLeveler;
    bool have_mode = false;
    double rate = 0.0;
    long channels = 2;
    double input_db = 0.0;
    double adapt = 0.0;
    bool have_input_db = false;

    for (int i = 1; i < argc; ++i) {
        const std::string flag = argv[i];
        const bool has_value = (i + 1) < argc;
        if (flag == "--mode" && has_value) {
            if (!parse_mode(argv[++i], mode)) {
                return usage("--mode must be podcast, stream or limiter");
            }
            have_mode = true;
        } else if (flag == "--rate" && has_value) {
            rate = std::atof(argv[++i]);
        } else if (flag == "--channels" && has_value) {
            channels = std::strtol(argv[++i], nullptr, 10);
        } else if (flag == "--input-db" && has_value) {
            input_db = std::atof(argv[++i]);
            have_input_db = true;
        } else if (flag == "--adapt" && has_value) {
            adapt = std::atof(argv[++i]);
        } else if (flag == "--version") {
            std::printf("quill-optilab (OptiLab Core 1.4.0 by Lanes Audio / dgl1984)\n");
            return 0;
        } else {
            return usage(("unknown or incomplete argument: " + flag).c_str());
        }
    }

    if (!have_mode) {
        return usage("--mode is required");
    }
    if (rate < 8000.0 || rate > 384000.0) {
        return usage("--rate must be a sample rate between 8000 and 384000");
    }
    if (channels < 1 || channels > 2) {
        // Upstream's engine is mono/stereo. Refusing is honest; silently
        // downmixing somebody's multichannel file would not be.
        return usage("--channels must be 1 or 2");
    }

#ifdef _WIN32
    // Without this, Windows translates 0x0A in the PCM stream into 0x0D 0x0A
    // and the audio is corrupted in a way that sounds like clicks rather than
    // like a bug.
    _setmode(_fileno(stdin), _O_BINARY);
    _setmode(_fileno(stdout), _O_BINARY);
#endif

    OptiLabCore core;
    core.prepare(rate);

    OptiLabCore::Parameters params = OptiLabCore::defaultParameters(mode);
    if (have_input_db) {
        params.inputDriveDb = clamp(input_db, -24.0, 24.0);
    }
    params.autoAdaptPct = clamp(adapt, 0.0, 100.0);
    core.setParameters(params);

    const std::size_t block_samples = kFramesPerBlock * static_cast<std::size_t>(channels);
    std::vector<float> buffer(block_samples);

    for (;;) {
        const std::size_t got = std::fread(buffer.data(), sizeof(float), block_samples, stdin);
        if (got == 0) {
            if (std::ferror(stdin)) {
                std::fprintf(stderr, "quill-optilab: read failed\n");
                return 3;
            }
            break;  // clean EOF
        }
        // A partial block at end-of-stream is normal; process exactly what
        // arrived rather than padding, so the output length matches the input.
        const std::size_t frames = got / static_cast<std::size_t>(channels);
        if (frames > 0) {
            core.processInterleaved(buffer.data(), frames, static_cast<std::size_t>(channels));
        }
        if (std::fwrite(buffer.data(), sizeof(float), got, stdout) != got) {
            std::fprintf(stderr, "quill-optilab: write failed\n");
            return 3;
        }
    }

    if (std::fflush(stdout) != 0) {
        std::fprintf(stderr, "quill-optilab: flush failed\n");
        return 3;
    }
    return 0;
}
