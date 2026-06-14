"""
Generate Ink sound pack WAV files using thoughtfully designed earcons.

Techniques used:
- ADSR envelopes for dynamic shaping
- Exponential frequency sweeps (chirps) for rising/falling effects
- Additive synthesis with inharmonic partials for bell tones
- White noise bursts for click/attack transients
- Square and triangle waveforms for buzz and softer tones
- Exponential amplitude decay for resonant sounds

Run from the repo root:
    python scripts/gen_ink_sounds.py
"""

from __future__ import annotations

import math
import random
import struct
import wave
from pathlib import Path

SR = 44100
OUT = Path(__file__).parent.parent / "quill" / "assets" / "sound_packs" / "ink"


# ---------------------------------------------------------------------------
# Core synthesis primitives
# ---------------------------------------------------------------------------


def _clamp_pcm(s: float) -> int:
    return max(-32768, min(32767, int(s * 32767)))


def pcm(samples: list[float]) -> bytes:
    return b"".join(struct.pack("<h", _clamp_pcm(s)) for s in samples)


def write_wav(name: str, samples: list[float], vol: float = 1.0) -> None:
    data = pcm([s * vol for s in samples])
    path = OUT / name
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(data)
    duration_ms = len(samples) * 1000 // SR
    print(f"  {name}: {duration_ms}ms")


def ms(t_ms: float) -> int:
    return int(SR * t_ms / 1000)


# ---------------------------------------------------------------------------
# Oscillators (return one sample at index i)
# ---------------------------------------------------------------------------


def sine_at(freq: float, i: int) -> float:
    return math.sin(2 * math.pi * freq * i / SR)


def tri_at(freq: float, i: int) -> float:
    phase = (freq * i / SR) % 1.0
    return (4 * phase - 1) if phase < 0.5 else (3 - 4 * phase)


def sqr_at(freq: float, i: int) -> float:
    return 1.0 if math.sin(2 * math.pi * freq * i / SR) >= 0 else -1.0


# ---------------------------------------------------------------------------
# Envelope helpers
# ---------------------------------------------------------------------------


def adsr(i: int, n: int, atk: int, dec: int, sus: float, rel: int) -> float:
    if i < atk:
        return i / max(atk, 1)
    if i < atk + dec:
        return 1.0 - ((i - atk) / max(dec, 1)) * (1.0 - sus)
    if i < n - rel:
        return sus
    return sus * (n - i) / max(rel, 1)


def exp_decay(i: int, half_life_ms: float) -> float:
    """Exponential decay: 1.0 at i=0, halves every half_life_ms."""
    return 2.0 ** (-i / (half_life_ms * SR / 1000))


def edge(i: int, n: int, ramp_ms: float = 5.0) -> float:
    """Quick linear ramp in/out to prevent click artifacts."""
    r = ms(ramp_ms)
    return min(1.0, i / max(r, 1)) * min(1.0, (n - i) / max(r, 1))


# ---------------------------------------------------------------------------
# Sound builders
# ---------------------------------------------------------------------------


def _sweep(
    f1: float,
    f2: float,
    dur_ms: float,
    osc=sine_at,
    env_fn=None,
) -> list[float]:
    """Exponential frequency glide from f1 to f2."""
    n = ms(dur_ms)
    out = []
    for i in range(n):
        t = i / max(n - 1, 1)
        freq = f1 * ((f2 / f1) ** t)
        e = env_fn(i, n) if env_fn else edge(i, n)
        out.append(osc(freq, i) * e)
    return out


def _tone(
    freq: float,
    dur_ms: float,
    osc=sine_at,
    env_fn=None,
) -> list[float]:
    n = ms(dur_ms)
    return [osc(freq, i) * (env_fn(i, n) if env_fn else edge(i, n)) for i in range(n)]


def _noise(dur_ms: float, env_fn=None) -> list[float]:
    rng = random.Random(42)
    n = ms(dur_ms)
    return [rng.uniform(-1.0, 1.0) * (env_fn(i, n) if env_fn else edge(i, n)) for i in range(n)]


def _silence(dur_ms: float) -> list[float]:
    return [0.0] * ms(dur_ms)


def _concat(*parts: list[float]) -> list[float]:
    result: list[float] = []
    for p in parts:
        result.extend(p)
    return result


def _mix(*channels: list[float]) -> list[float]:
    n = max(len(c) for c in channels)
    out = [0.0] * n
    for ch in channels:
        for i, s in enumerate(ch):
            out[i] += s
    mx = max((abs(x) for x in out), default=1.0) or 1.0
    return [x / mx for x in out] if mx > 1.0 else out


def _bell(
    fund: float,
    dur_ms: float,
    partials: tuple[tuple[float, float], ...] = (
        (1.000, 1.00),
        (2.756, 0.50),
        (5.404, 0.25),
        (8.933, 0.10),
    ),
) -> list[float]:
    """Inharmonic partials with exponential decay — classic bell sound."""
    n = ms(dur_ms)
    out = []
    for i in range(n):
        s = 0.0
        for ratio, amp in partials:
            half = dur_ms * 0.25 / ratio
            s += amp * exp_decay(i, half) * sine_at(fund * ratio, i)
        out.append(s * edge(i, n, ramp_ms=2))
    mx = max((abs(x) for x in out), default=1.0) or 1.0
    return [x / mx for x in out]


# ---------------------------------------------------------------------------
# Envelopes as lambdas (defined at module level for clarity)
# ---------------------------------------------------------------------------


def _click_env(i: int, n: int) -> float:
    return edge(i, n, 2) * exp_decay(i, 8)


def _swell_env(atk_ms: float, dec_ms: float, sus: float, rel_ms: float):
    def fn(i: int, n: int) -> float:
        return adsr(i, n, ms(atk_ms), ms(dec_ms), sus, ms(rel_ms))

    return fn


# ---------------------------------------------------------------------------
# Sound design — one block per event
# ---------------------------------------------------------------------------


def generate_all() -> None:
    print(f"Writing sounds to {OUT}")

    # -- abbreviation_expanded: soft noise click + rising chirp (unfolding) --
    write_wav(
        "expand.wav",
        _concat(
            _noise(6, _click_env),
            _sweep(400, 1000, 75, sine_at, _swell_env(5, 20, 0.3, 25)),
        ),
        vol=0.70,
    )

    # -- abbreviation_deleted: click + falling chirp (mirror of expand) ------
    write_wav(
        "delete.wav",
        _concat(
            _noise(6, _click_env),
            _sweep(1000, 400, 75, sine_at, _swell_env(5, 15, 0.2, 30)),
        ),
        vol=0.70,
    )

    # -- snippet_inserted: double click + longer rising tone (more content) --
    write_wav(
        "snippet.wav",
        _concat(
            _noise(5, _click_env),
            _silence(12),
            _noise(5, _click_env),
            _silence(15),
            _sweep(440, 880, 70, sine_at, _swell_env(4, 20, 0.25, 25)),
        ),
        vol=0.75,
    )

    # -- autocomplete_accepted: crisp double-tick snap (distinct from expand) -
    # A bright two-step triangle "snap into place"; shorter and harder-edged
    # than expand's soft noise+sine sweep so the two never sound alike.
    write_wav(
        "autocomplete.wav",
        _concat(
            _tone(880, 28, tri_at, _swell_env(2, 6, 0.3, 10)),
            _silence(6),
            _tone(1320, 42, tri_at, _swell_env(2, 8, 0.35, 16)),
        ),
        vol=0.55,
    )

    # -- document_saved: very soft low tick with 2nd harmonic (settled) ------
    def save_env(i: int, n: int) -> float:
        return exp_decay(i, 30) * edge(i, n, 3)

    write_wav(
        "save.wav",
        _mix(
            _tone(300, 80, sine_at, save_env),
            _tone(600, 80, sine_at, lambda i, n: save_env(i, n) * 0.3),
        ),
        vol=0.55,
    )

    # -- document_created: ascending two-tone (opening) ----------------------
    write_wav(
        "create.wav",
        _concat(
            _tone(440, 60, sine_at, _swell_env(5, 15, 0.4, 20)),
            _silence(10),
            _tone(660, 80, sine_at, _swell_env(5, 20, 0.35, 30)),
        ),
        vol=0.70,
    )

    # -- search_found: short positive rising chirp ---------------------------
    write_wav(
        "found.wav",
        _sweep(660, 880, 65, sine_at, _swell_env(5, 15, 0.3, 25)),
        vol=0.70,
    )

    # -- search_not_found: classic two-tone descend ("nope") -----------------
    write_wav(
        "notfound.wav",
        _concat(
            _tone(440, 65, sine_at, _swell_env(5, 10, 0.5, 20)),
            _silence(15),
            _tone(330, 65, sine_at, _swell_env(5, 10, 0.4, 25)),
        ),
        vol=0.70,
    )

    # -- search_wrapped: rise + descend, "loop" sense ------------------------
    write_wav(
        "wrap.wav",
        _concat(
            _sweep(440, 880, 55, sine_at, _swell_env(5, 10, 0.4, 20)),
            _silence(8),
            _tone(550, 45, sine_at, _swell_env(5, 10, 0.3, 20)),
        ),
        vol=0.70,
    )

    # -- heading_jumped: crisp click + sharp navigation tone -----------------
    write_wav(
        "nav_heading.wav",
        _concat(
            _noise(4, lambda i, n: edge(i, n, 1) * exp_decay(i, 5)),
            _tone(770, 55, tri_at, _swell_env(3, 12, 0.35, 20)),
        ),
        vol=0.65,
    )

    # -- table_entered: double-tap same pitch (grid feel) --------------------
    write_wav(
        "nav_table.wav",
        _concat(
            _tone(550, 35, tri_at, _swell_env(3, 8, 0.3, 12)),
            _silence(18),
            _tone(550, 35, tri_at, _swell_env(3, 8, 0.3, 12)),
        ),
        vol=0.65,
    )

    # -- browse_mode_on: thin high triangle tone with slow attack ("step back")
    def browse_env(i: int, n: int) -> float:
        r_in = ms(15)
        r_out = ms(20)
        return min(1.0, i / max(r_in, 1)) * min(1.0, (n - i) / max(r_out, 1))

    browse_on_samples = _mix(
        _tone(1760, 120, tri_at, browse_env),
        _tone(880, 120, sine_at, lambda i, n: browse_env(i, n) * 0.2),
    )
    write_wav("browse_on.wav", browse_on_samples, vol=0.45)

    # -- browse_mode_off: exact time-reverse of browse_on --------------------
    write_wav("browse_off.wav", list(reversed(browse_on_samples)), vol=0.45)

    # -- ai_thinking_started: four-note ascending arpeggio (shimmer) ---------
    arp_env = _swell_env(3, 10, 0.3, 15)
    ai_start_samples = _concat(
        _tone(440, 40, sine_at, arp_env),
        _tone(550, 40, sine_at, arp_env),
        _tone(660, 40, sine_at, arp_env),
        _tone(880, 50, sine_at, arp_env),
    )
    write_wav("ai_start.wav", ai_start_samples, vol=0.65)

    # -- ai_response_received: exact time-reverse of ai_start ----------------
    write_wav("ai_done.wav", list(reversed(ai_start_samples)), vol=0.65)

    # -- ai_error: descending AI arpeggio over a soft buzz (distinct) --------
    # Ties to the AI sound family (arpeggio shape) but clearly negative: a
    # minor descending three-note figure with a square-wave underlay, so it
    # is never mistaken for ai_done (the bright reverse of ai_start) or for
    # the generic error buzz.
    def ai_err_env(i: int, n: int) -> float:
        return adsr(i, n, ms(2), ms(8), 0.35, ms(14))

    write_wav(
        "ai_error.wav",
        _concat(
            _mix(
                _tone(784, 55, sine_at, ai_err_env),
                _tone(784, 55, sqr_at, lambda i, n: ai_err_env(i, n) * 0.18),
            ),
            _silence(8),
            _mix(
                _tone(523, 55, sine_at, ai_err_env),
                _tone(523, 55, sqr_at, lambda i, n: ai_err_env(i, n) * 0.18),
            ),
            _silence(8),
            _mix(
                _tone(392, 80, sine_at, ai_err_env),
                _tone(392, 80, sqr_at, lambda i, n: ai_err_env(i, n) * 0.22),
            ),
        ),
        vol=0.60,
    )

    # -- error: double square-wave buzz (intentionally harsh) ----------------
    def buzz_env(i: int, n: int) -> float:
        return adsr(i, n, ms(3), ms(20), 0.4, ms(20))

    single_buzz = _mix(
        _tone(220, 85, sqr_at, buzz_env),
        _tone(220, 85, sine_at, lambda i, n: buzz_env(i, n) * 0.4),
    )
    write_wav(
        "error.wav",
        _concat(single_buzz, _silence(30), single_buzz),
        vol=0.60,
    )

    # -- warning: single descending triangle sweep (softer than error) -------
    write_wav(
        "warning.wav",
        _sweep(440, 300, 90, tri_at, _swell_env(5, 20, 0.4, 30)),
        vol=0.60,
    )

    # -- transcription_started: ascending two-tone ("radio open") ------------
    rec_start_samples = _concat(
        _tone(660, 55, sine_at, _swell_env(5, 10, 0.5, 20)),
        _silence(12),
        _tone(880, 70, sine_at, _swell_env(5, 12, 0.45, 25)),
    )
    write_wav("rec_start.wav", rec_start_samples, vol=0.70)

    # -- transcription_stopped: exact time-reverse of rec_start --------------
    write_wav("rec_stop.wav", list(reversed(rec_start_samples)), vol=0.70)

    # -- ssh_connected: two clear ascending beeps ----------------------------
    connect_samples = _concat(
        _tone(660, 60, sine_at, _swell_env(5, 10, 0.5, 20)),
        _silence(20),
        _tone(880, 75, sine_at, _swell_env(5, 15, 0.5, 25)),
    )
    write_wav("connect.wav", connect_samples, vol=0.70)

    # -- ssh_disconnected: exact time-reverse of connect ---------------------
    write_wav("disconnect.wav", list(reversed(connect_samples)), vol=0.70)

    # -- sound_on: bright 3-note ascending "ta-da" (notifications enabled) --
    arp3_env = _swell_env(3, 8, 0.45, 18)
    sound_on_samples = _concat(
        _tone(440, 35, sine_at, arp3_env),
        _tone(660, 35, sine_at, arp3_env),
        _tone(880, 50, sine_at, arp3_env),
    )
    write_wav("sound_on.wav", sound_on_samples, vol=0.70)

    # -- sound_off: exact time-reverse of sound_on (notifications disabled) --
    write_wav("sound_off.wav", list(reversed(sound_on_samples)), vol=0.70)

    # ------------------------------------------------------------------
    # Compare mode (issue #186). Five distinct earcons; the enter/exit
    # pair are time-reversals, next/previous are a high/low tick pair, and
    # no-more is a soft low double-thud (a gentle "blocked" cue).
    # ------------------------------------------------------------------

    # -- compare_enter_mode: rising perfect fifth (opening a comparison) -----
    compare_enter_samples = _concat(
        _tone(523, 50, tri_at, _swell_env(4, 12, 0.4, 18)),
        _silence(8),
        _tone(784, 70, tri_at, _swell_env(4, 16, 0.35, 24)),
    )
    write_wav("compare_enter.wav", compare_enter_samples, vol=0.60)

    # -- compare_exit_mode: exact time-reverse of enter (closing) ------------
    write_wav("compare_exit.wav", list(reversed(compare_enter_samples)), vol=0.60)

    # -- compare_next_difference: crisp high tick (move forward) -------------
    write_wav(
        "compare_next.wav",
        _tone(740, 45, tri_at, _swell_env(2, 8, 0.3, 16)),
        vol=0.55,
    )

    # -- compare_previous_difference: crisp low tick (move back) -------------
    write_wav(
        "compare_prev.wav",
        _tone(523, 45, tri_at, _swell_env(2, 8, 0.3, 16)),
        vol=0.55,
    )

    # -- compare_no_more_differences: soft low double-thud ("blocked") -------
    def thud_env(i: int, n: int) -> float:
        return exp_decay(i, 18) * edge(i, n, 3)

    no_more_thud = _tone(196, 55, sine_at, thud_env)
    write_wav(
        "compare_none.wav",
        _concat(no_more_thud, _silence(20), no_more_thud),
        vol=0.55,
    )

    print("Done.")


if __name__ == "__main__":
    generate_all()
