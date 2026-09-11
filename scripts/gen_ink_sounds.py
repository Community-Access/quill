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
    expand_samples = _concat(
        _noise(6, _click_env),
        _sweep(400, 1000, 75, sine_at, _swell_env(5, 20, 0.3, 25)),
    )
    write_wav("expand.wav", expand_samples, vol=0.70)

    # -- abbreviation_deleted: exact time-reverse of expand (true mirror) -----
    # Reversing the rising chirp gives a falling chirp, and the click moves to
    # the tail, so "delete" is the unmistakable opposite of "expand".
    write_wav("delete.wav", list(reversed(expand_samples)), vol=0.70)

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

    # -- spelling_alert: "the slip" ------------------------------------------
    # A note that starts in tune and slides flat. That is the whole design, and
    # it is the sound of the thing it reports: a word that was almost right.
    #
    # It has to be unique in this pack, because it fires more often than any
    # other earcon here -- every completed misspelled word while somebody is
    # typing -- and an alert you cannot tell from four other alerts is one you
    # learn to ignore. Every negative cue in Ink is either a *discrete* two-note
    # descent (search_not_found, ai_error, conversation_error,
    # radio_stream_error) or a buzz (error). Nothing else *glides*, so a
    # continuous bend is recognisable before the first tenth of it has played
    # and cannot be confused with any of them.
    #
    # Four properties it has to have, and each is why a number is what it is:
    #
    # * **Short.** 58 ms, tick included. It lands between two keystrokes, not
    #   across them.
    # * **Quiet.** vol 0.38, the lowest of any alert in the pack. It fires
    #   during typing, which is the moment a listener can least afford volume.
    # * **Legible anyway.** A 3 ms noise tick opens it, so it cuts through a
    #   synthesiser mid-sentence on shape rather than on loudness -- which is
    #   the trade every alert that fires this often has to make.
    # * **Not alarming.** It falls, it decays, and it resolves nowhere. The
    #   bend is 200 cents and it *accelerates* (t squared), so the ear hears a
    #   note going flat rather than a musical interval being played. A whole
    #   tone stated as two notes would be a tune; slid into, it is a slip.
    def slip_env(i: int, n: int) -> float:
        return exp_decay(i, 20) * edge(i, n, 3)

    def _slip(f_from: float, f_to: float, dur_ms: float) -> list[float]:
        """A triangle glide whose bend accelerates: in tune, then falling away."""
        n = ms(dur_ms)
        out = []
        for i in range(n):
            t = i / max(n - 1, 1)
            freq = f_from * ((f_to / f_from) ** (t * t))
            env = slip_env(i, n)
            # A touch of the octave for body. Any more and the glide reads as a
            # chord sliding rather than one note going wrong.
            out.append((tri_at(freq, i) + 0.25 * sine_at(freq * 2, i)) * env)
        peak = max((abs(x) for x in out), default=1.0) or 1.0
        return [x / peak for x in out] if peak > 1.0 else out

    write_wav(
        "spelling.wav",
        _concat(
            _noise(3, lambda i, n: exp_decay(i, 1.2) * 0.5),
            _slip(523.25, 466.16, 55),
        ),
        vol=0.38,
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

    # -- browse_mode_on: thin rising sweep ("stepping back/up into browse") ---
    # A rising glide (not a steady tone) so the time-reversed browse_off is an
    # audibly different falling glide rather than the same pitch backwards.
    browse_on_samples = _mix(
        _sweep(880, 1760, 130, tri_at, _swell_env(8, 20, 0.5, 25)),
        _sweep(440, 880, 130, sine_at, lambda i, n: _swell_env(8, 20, 0.5, 25)(i, n) * 0.2),
    )
    write_wav("browse_on.wav", browse_on_samples, vol=0.45)

    # -- browse_mode_off: exact time-reverse of browse_on (clear falling glide)
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

    # -- dictation_locked_on: firm low->high triangle "lock engaged" (distinct
    #    timbre and interval from rec_start, so Locked Dictation is recognisably
    #    different from Hold-to-Dictate) -------------------------------------
    lock_on_samples = _concat(
        _tone(330, 70, tri_at, _swell_env(4, 12, 0.5, 25)),
        _silence(10),
        _tone(495, 95, tri_at, _swell_env(4, 14, 0.5, 30)),
    )
    write_wav("dict_lock_on.wav", lock_on_samples, vol=0.70)

    # -- dictation_locked_off: exact time-reverse of dict_lock_on ------------
    write_wav("dict_lock_off.wav", list(reversed(lock_on_samples)), vol=0.70)

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

    # -- Voice conversation cues (Hey QUILL Phase 2) ------------------------
    # Warm bell sequences on consonant intervals, ported from the ADP Assistant
    # palette (plan §3.3). Each note is a soft inharmonic bell; a sequence is
    # concatenated with tiny gaps so it rings rather than beeps.
    def _bell_seq(freqs: list[float], note_ms: float, gap_ms: float = 24) -> list[float]:
        parts: list[list[float]] = []
        for index, freq in enumerate(freqs):
            if index:
                parts.append(_silence(gap_ms))
            parts.append(_bell(freq, note_ms))
        return _concat(*parts)

    # ------------------------------------------------------------------
    # Audio identity: per-slot earcons, the
    # 5-percent progress ladder, selection and document-boundary cues, and
    # the soundcard keep-alive. Slot identity rides a C-major pentatonic so
    # every numbered slot is a note you learn; families differ by timbre.
    # ------------------------------------------------------------------

    def _pentatonic(degree: int, base: float = 261.63) -> float:
        """Frequency of pentatonic scale degree N (C D E G A, octave-wrapped)."""
        offsets = (0, 2, 4, 7, 9)
        octave, position = divmod(degree, len(offsets))
        return base * (2.0 ** (octave + offsets[position] / 12.0))

    # -- copy_slot_1..12: soft marimba tap at the slot's own pitch -----------
    # A tiny noise attack + a warm sine-with-octave body, short enough to
    # never delay the spoken confirmation that follows it.
    def marimba_env(i: int, n: int) -> float:
        return exp_decay(i, 26) * edge(i, n, 2)

    for slot in range(1, 13):
        freq = _pentatonic(slot - 1)
        write_wav(
            f"copy_slot_{slot}.wav",
            _concat(
                _noise(3, _click_env),
                _mix(
                    _tone(freq, 85, sine_at, marimba_env),
                    _tone(freq * 2, 85, sine_at, lambda i, n: marimba_env(i, n) * 0.35),
                ),
            ),
            vol=0.55,
        )

    # -- bookmark_slot_0..9: bright triangle chirp at the slot's pitch -------
    # Same scale, different voice: a quick upward glide into the slot note so
    # bookmarks never blur into copy-tray taps.
    for slot in range(10):
        freq = _pentatonic(slot)
        write_wav(
            f"bookmark_slot_{slot}.wav",
            _sweep(freq * 0.84, freq, 70, tri_at, _swell_env(3, 12, 0.35, 22)),
            vol=0.5,
        )

    # -- progress_5..progress_100: a rising blip ladder ----------------------
    # Pitch climbs one octave across the run (320 Hz at 5%, 640 Hz at 100%).
    # Quarter marks (25/50/75) add a soft perfect fifth so the landmarks
    # stand out; 100% resolves with a tiny two-note "done".
    def blip_env(i: int, n: int) -> float:
        return adsr(i, n, ms(2), ms(8), 0.4, ms(14))

    for pct in range(5, 101, 5):
        freq = 320.0 * (2.0 ** (pct / 100.0))
        layers = [_tone(freq, 42, sine_at, blip_env)]
        if pct in (25, 50, 75):
            layers.append(_tone(freq * 1.5, 42, sine_at, lambda i, n: blip_env(i, n) * 0.3))
        blip = _mix(*layers)
        if pct == 100:
            blip = _concat(blip, _silence(14), _tone(freq * 1.25, 60, sine_at, blip_env))
        write_wav(f"progress_{pct}.wav", blip, vol=0.42)

    # -- progress_tick: the indeterminate heartbeat --------------------------
    write_wav("progress_tick.wav", _tone(500, 26, sine_at, _click_env), vol=0.3)

    # -- selection_started / selection_completed: a mirrored gate ------------
    # Two quick triangle notes rising a fourth to open the selection; the
    # exact reverse closes it. Shorter and lighter than the SSH connect pair
    # so the families never collide.
    selection_open = _concat(
        _tone(523, 40, tri_at, _swell_env(2, 8, 0.35, 14)),
        _silence(8),
        _tone(698, 55, tri_at, _swell_env(2, 10, 0.35, 18)),
    )
    write_wav("selection_started.wav", selection_open, vol=0.5)
    write_wav("selection_completed.wav", list(reversed(selection_open)), vol=0.5)

    # -- document_top / document_bottom: ceiling tick, floor thud ------------
    def ceiling_env(i: int, n: int) -> float:
        return exp_decay(i, 10) * edge(i, n, 2)

    write_wav("document_top.wav", _tone(1318, 45, sine_at, ceiling_env), vol=0.45)

    def floor_env(i: int, n: int) -> float:
        return exp_decay(i, 22) * edge(i, n, 3)

    write_wav(
        "document_bottom.wav",
        _mix(
            _tone(165, 70, sine_at, floor_env),
            _tone(330, 70, sine_at, lambda i, n: floor_env(i, n) * 0.25),
        ),
        vol=0.5,
    )

    # -- keepalive: two seconds of true silence ------------------------------
    # Played on a timer (opt-in) purely to keep USB/Bluetooth audio devices
    # from powering down and clipping the start of the next real earcon.
    write_wav("keepalive.wav", _silence(2000), vol=0.0)

    # on: C-E-G rising — a warm "hello".
    write_wav("conversation_on.wav", _bell_seq([523, 659, 784], 150), vol=0.55)
    # off: falling — settle "goodbye".
    write_wav("conversation_off.wav", _bell_seq([659, 523, 392], 150), vol=0.55)
    # wake: bright two-note lift — "I'm here" (used from Phase 3).
    write_wav("conversation_wake.wav", _bell_seq([587, 880], 130), vol=0.55)
    # listen: soft two-note — "go ahead" (quieter; it fires often).
    write_wav("conversation_listen.wav", _bell_seq([523, 659], 120), vol=0.38)
    # review: gentle rise — "got it".
    write_wav("conversation_review.wav", _bell_seq([659, 784], 130), vol=0.50)
    # ready: sparkle — "answer's here / done".
    write_wav("conversation_ready.wav", _bell_seq([659, 988], 150), vol=0.55)
    # idle: single soft tone — "resting".
    write_wav("conversation_idle.wav", _bell(440, 220), vol=0.34)
    # thinking tick: quiet blip — "still working".
    write_wav("conversation_thinking_tick.wav", _bell(330, 150), vol=0.28)
    # error: low fall — "something's off" (calm, not alarming).
    write_wav("conversation_error.wav", _bell_seq([392, 294], 150), vol=0.5)

    # ------------------------------------------------------------------
    # Companion-app cues. These fourteen ids shipped in the catalogue with
    # no sounds and no call sites, so Radio, Cast, Weather and Beacon were
    # silent. Each family gets its own voice, so you know WHICH app spoke
    # before you parse WHAT it said: Radio is warm sine (broadcast), Cast is
    # bell-like (an episode is a discrete thing), Weather is a deliberate
    # alert, Beacon is a single capture blip.
    # ------------------------------------------------------------------

    def radio_env(i: int, n: int) -> float:
        return adsr(i, n, ms(4), ms(14), 0.42, ms(22))

    # connecting: a rising fifth — reaching out, not yet arrived.
    write_wav(
        "radio_connecting.wav",
        _concat(
            _tone(392, 55, sine_at, radio_env),
            _silence(10),
            _tone(587, 65, sine_at, radio_env),
        ),
        vol=0.55,
    )
    # playing: that fifth resolving up to the octave — arrival.
    radio_playing = _concat(
        _tone(587, 50, sine_at, radio_env),
        _silence(8),
        _mix(
            _tone(784, 90, sine_at, radio_env),
            _tone(1568, 90, sine_at, lambda i, n: radio_env(i, n) * 0.2),
        ),
    )
    write_wav("radio_playing.wav", radio_playing, vol=0.55)
    # stopped: the exact time-reverse of playing — unmistakably its opposite.
    write_wav("radio_stopped.wav", list(reversed(radio_playing)), vol=0.55)
    # buffering: two soft equal pulses — waiting, going nowhere yet.
    buffer_pulse = _tone(440, 45, sine_at, lambda i, n: exp_decay(i, 16) * edge(i, n, 3))
    write_wav("radio_buffering.wav", _concat(buffer_pulse, _silence(70), buffer_pulse), vol=0.40)
    # stream error: a falling minor third with a breath of noise — audibly in
    # the radio family (so you know it is the stream), clearly negative, and
    # not the harsh generic error buzz.
    write_wav(
        "radio_stream_error.wav",
        _concat(
            _noise(5, _click_env),
            _mix(
                _tone(466, 70, sine_at, radio_env),
                _tone(466, 70, sqr_at, lambda i, n: radio_env(i, n) * 0.12),
            ),
            _silence(8),
            _tone(370, 95, sine_at, radio_env),
        ),
        vol=0.55,
    )
    # recording started / stopped: a firm low-to-high pair and its mirror,
    # deliberately lower and rounder than transcription's rec_start/rec_stop
    # so "the radio is recording" never sounds like "dictation is listening".
    radio_rec = _concat(
        _tone(294, 70, sine_at, radio_env),
        _silence(10),
        _tone(440, 95, sine_at, radio_env),
    )
    write_wav("radio_recording_started.wav", radio_rec, vol=0.6)
    write_wav("radio_recording_stopped.wav", list(reversed(radio_rec)), vol=0.6)
    # favorite added: a bright quick lift — a small delight.
    write_wav(
        "radio_favorite_added.wav",
        _concat(
            _tone(880, 40, tri_at, _swell_env(2, 8, 0.35, 14)),
            _tone(1320, 55, tri_at, _swell_env(2, 10, 0.35, 20)),
        ),
        vol=0.5,
    )

    # Reminder: the one cue in these apps that arrives because the listener
    # asked to be interrupted at a moment they chose. So it is deliberately
    # *unlike* its neighbours -- three rising bell tones on a major triad, the
    # third held, which reads as a question being asked rather than a task
    # reporting itself finished. Bell-voiced so it carries over speech without
    # being sharp, and quiet enough (0.45) that it is a tap on the shoulder
    # rather than an alarm; the weather alert is the app's only alarm and it
    # sounds nothing like this on purpose.
    write_wav(
        "radio_reminder.wav",
        _concat(
            _bell(587, 110),  # D5
            _silence(30),
            _bell(740, 110),  # F#5
            _silence(30),
            _bell(880, 300),  # A5, held -- the unresolved "well?"
        ),
        vol=0.45,
    )

    # Cast: bell-voiced. Started and complete are inversions of each other.
    write_wav("cast_download_started.wav", _bell_seq([523, 659], 120), vol=0.5)
    write_wav("cast_download_complete.wav", _bell_seq([659, 523], 120), vol=0.5)
    # episode finished: a longer, lower resolve — the end of a listen.
    write_wav("cast_episode_finished.wav", _bell_seq([523, 392], 200), vol=0.45)

    # Weather: a real alert. Two urgent tones then a held third — musical
    # rather than a klaxon, but this fires for genuine warnings, so it is the
    # one cue in the pack that must never be easy to ignore.
    weather_env = _swell_env(3, 10, 0.55, 20)
    write_wav(
        "weather_alert.wav",
        _concat(
            _tone(880, 90, sine_at, weather_env),
            _silence(50),
            _tone(880, 90, sine_at, weather_env),
            _silence(50),
            _mix(
                _tone(1046, 200, sine_at, _swell_env(4, 20, 0.5, 60)),
                _tone(698, 200, sine_at, lambda i, n: _swell_env(4, 20, 0.5, 60)(i, n) * 0.35),
            ),
        ),
        vol=0.7,
    )

    # Beacon: a capture is an instant, so its cue is one.
    write_wav(
        "beacon_captured.wav",
        _concat(_noise(4, _click_env), _tone(988, 45, tri_at, _swell_env(2, 8, 0.3, 16))),
        vol=0.5,
    )
    write_wav(
        "beacon_sync_complete.wav",
        _concat(
            _tone(659, 45, tri_at, _swell_env(2, 8, 0.3, 14)),
            _silence(8),
            _tone(988, 70, tri_at, _swell_env(2, 10, 0.35, 24)),
        ),
        vol=0.5,
    )

    print("Done.")

    # =====================================================================
    # The desktop-parity family (2026-09-10)
    # =====================================================================
    # Every desktop suite since the nineties has had a sound scheme, and the
    # events in it are the same everywhere because they are the moments a user
    # actually has: open, save, close, cut, copy, paste, delete, undo, redo,
    # print, and the four message tones. QUILL had earcons for its own clever
    # features and none for those -- so the sounds fired for an abbreviation
    # expanding and stayed silent for a paste.
    #
    # For a listener that ordering is exactly backwards. The clever features
    # announce themselves in words; the ordinary ones are silent by design,
    # because a screen reader says nothing when a paste lands. An earcon is the
    # only feedback those moments can have without speech, which makes them the
    # ones that most needed sounds.
    #
    # The family rule, so nineteen new cues do not become nineteen new things to
    # learn: **related events share a timbre and differ by direction.** Undo and
    # redo are one figure played backwards from each other. Open and close are
    # one bell pair rising and falling. Cut, copy and paste are one clipboard
    # timbre in three positions. You learn a family once and read its members.

    # -- Clipboard: one timbre, three gestures -----------------------------
    # A dry wooden tick, high and very short, because the clipboard is the
    # fastest thing anybody does repeatedly and a tone with a tail would smear
    # into the next keystroke.
    def clip_env(i: int, n: int) -> float:
        return exp_decay(i, 7) * edge(i, n, 1.5)

    def _tick(freq: float, dur_ms: float = 26) -> list[float]:
        return _mix(
            _tone(freq, dur_ms, tri_at, clip_env),
            _noise(dur_ms, lambda i, n: exp_decay(i, 2) * 0.30),
        )

    # cut: two ticks, very close -- the scissors gesture.
    write_wav("text_cut.wav", _concat(_tick(1480), _silence(22), _tick(1245)), vol=0.42)
    # copy: one tick and its quieter shadow -- there are two of it now.
    write_wav(
        "text_copied.wav",
        _concat(_tick(1245), _silence(38), _mix([s * 0.45 for s in _tick(1245)])),
        vol=0.42,
    )
    # paste: the tick lands, and something arrives under it. A falling fifth
    # settling, so the gesture reads as "put down" rather than "picked up".
    write_wav(
        "text_pasted.wav",
        _mix(
            _concat(_tick(1245), _silence(60)),
            _concat(_silence(18), _sweep(784, 523, 70, sine_at, lambda i, n: exp_decay(i, 24))),
        ),
        vol=0.46,
    )
    # delete: a dry low thud with a breath of noise -- something removed, not
    # something moved. Deliberately the lowest of the four.
    write_wav(
        "text_deleted.wav",
        _mix(
            _tone(196, 70, tri_at, lambda i, n: exp_decay(i, 16) * edge(i, n, 2)),
            _noise(28, lambda i, n: exp_decay(i, 5) * 0.22),
        ),
        vol=0.44,
    )

    # -- Undo and redo: one figure, played both ways -----------------------
    # The pair has to be *mirror* images, not merely different: undo and redo
    # are the only two commands in an editor whose entire meaning is direction,
    # and a listener who has to think about which sound they just heard has
    # lost the benefit. So redo is undo reversed, sample for sample.
    def _swoop(f_from: float, f_to: float) -> list[float]:
        return _mix(
            _sweep(f_from, f_to, 95, tri_at, lambda i, n: adsr(i, n, ms(4), ms(30), 0.45, ms(40))),
            _sweep(
                f_from * 2,
                f_to * 2,
                95,
                sine_at,
                lambda i, n: adsr(i, n, ms(4), ms(30), 0.18, ms(40)),
            ),
        )

    undo_swoop = _swoop(587.33, 440.00)  # D5 down to A4: taking something back
    write_wav("undo_performed.wav", undo_swoop, vol=0.50)
    write_wav("redo_performed.wav", list(reversed(undo_swoop)), vol=0.50)
    # nothing to undo: a muted tap against a wall. No pitch movement at all,
    # which is the point -- the stack did not move either.
    write_wav(
        "nothing_to_undo.wav",
        _mix(
            _tone(147, 55, tri_at, lambda i, n: exp_decay(i, 10) * edge(i, n, 2)),
            _noise(20, lambda i, n: exp_decay(i, 4) * 0.18),
        ),
        vol=0.38,
    )

    # -- Documents and the app: one bell pair, four directions -------------
    # Bells rather than the sine blips document_created uses, so the pair is
    # audibly a different family from "a new empty document" -- opening a file
    # and creating one are different events and used to sound alike.
    write_wav("document_opened.wav", _bell_seq([523, 784], 100), vol=0.52)
    write_wav("document_closed.wav", _bell_seq([784, 523], 100), vol=0.48)

    # The app itself: three notes, so a launch is unmistakably not a document.
    # Rising for hello, the same three falling for goodbye.
    #
    # A *warm triangle swell*, not a bell, and that is a correction rather than
    # a preference. The first version of this was `_bell_seq([659, 523, 392])`,
    # which is note for note what conversation_off already plays -- two
    # different events making one sound, which is the one thing an earcon set
    # cannot afford. Changing the notes alone would not have been enough
    # either: the conversation cues own the bell timbre in this pack, so the
    # app's own cue takes a different instrument and keeps the whole family
    # clear of them. C-G-C, an opening fifth into the octave, so a launch reads
    # as a door rather than as a chord.
    def _breath(freq: float, dur_ms: float, peak: float = 1.0) -> list[float]:
        return _mix(
            _tone(freq, dur_ms, tri_at, lambda i, n: _swell_env(8, 22, 0.5, 30)(i, n) * peak),
            _tone(
                freq * 2,
                dur_ms,
                sine_at,
                lambda i, n: _swell_env(8, 22, 0.5, 30)(i, n) * peak * 0.22,
            ),
        )

    app_hello = _concat(
        _breath(261.63, 95),
        _silence(10),
        _breath(392.00, 95),
        _silence(10),
        _breath(523.25, 150),
    )
    write_wav("app_started.wav", app_hello, vol=0.52)
    write_wav(
        "app_exiting.wav",
        _concat(
            _breath(523.25, 95),
            _silence(10),
            _breath(392.00, 95),
            _silence(10),
            _breath(261.63, 150),
        ),
        vol=0.46,
    )

    # -- Printing: a mechanism, then a resolution --------------------------
    print_tick = _tone(880, 30, sqr_at, lambda i, n: exp_decay(i, 6) * edge(i, n, 2))
    write_wav("print_started.wav", _concat(print_tick, _silence(45), print_tick), vol=0.34)
    write_wav(
        "print_complete.wav",
        _concat(print_tick, _silence(45), print_tick, _silence(30), _bell(1047, 150)),
        vol=0.46,
    )

    # -- The message tones -------------------------------------------------
    # error and warning already exist. These are the other two every desktop
    # has, and QUILL had neither: a neutral one for "here is a fact" and a
    # rising one for "I need an answer". Rising, because a question rises --
    # that is the one piece of prosody every listener already reads.
    write_wav("information.wav", _bell(659, 170), vol=0.42)
    # A bell, then a *bend upward* -- and the bend is the point. The first
    # version was `_bell_seq([587, 880])`, which is note for note what
    # conversation_wake plays: two events, one sound. Discrete notes were never
    # going to work here anyway, because every other cue in the pack is made of
    # discrete notes. A glide is the prosody of a spoken question, it is the
    # only rising glide in the message family, and it cannot be mistaken for a
    # two-note lift no matter which two notes that lift uses.
    write_wav(
        "question.wav",
        _concat(
            _bell(587, 95),
            _sweep(659, 988, 130, tri_at, lambda i, n: _swell_env(6, 20, 0.5, 45)(i, n)),
        ),
        vol=0.44,
    )
    # task complete: two quick ticks and a bell landing on top of them. The
    # first attempt was `_bell_seq([659, 880])`, which starts on the same note
    # and runs to nearly the same length as conversation_review -- close enough
    # that the two were one sound to the ear. Two *ticks* before the bell is a
    # different shape, not merely different pitches, so it reads as "that
    # finished" rather than as another bell in the conversation family. Also
    # unlike ai_done, which is the assistant's own arpeggio: a background job
    # ending is not an answer arriving.
    complete_tick = _tone(784, 26, tri_at, lambda i, n: exp_decay(i, 6) * edge(i, n, 2))
    write_wav(
        "task_complete.wav",
        _concat(complete_tick, _silence(26), complete_tick, _silence(20), _bell(1319, 190)),
        vol=0.50,
    )

    # -- voice_preview_generating: its own sound at last -------------------
    # It shared ai_start.wav with ai_thinking_started, which is two events
    # making one sound -- and the two are not even the same kind of waiting.
    # The assistant thinking is a question in flight; a voice preview is an
    # engine warming up, which is what this is: a breath of noise opening into
    # a tone, like a throat clearing before it speaks.
    write_wav(
        "voice_preview.wav",
        _mix(
            _noise(70, lambda i, n: min(1.0, i / max(1, ms(30))) * exp_decay(i, 40) * 0.16),
            _concat(
                _silence(18),
                _sweep(330, 494, 90, tri_at, lambda i, n: _swell_env(6, 18, 0.45, 30)(i, n)),
            ),
        ),
        vol=0.42,
    )

    # -- The four editor events that had no sound at all -------------------
    # word_corrected: a fast flip up a semitone -- something was swapped for
    # something better, and it happened *to* you rather than by you.
    write_wav(
        "word_corrected.wav",
        _concat(
            _tone(988, 32, tri_at, lambda i, n: exp_decay(i, 8) * edge(i, n, 2)),
            _tone(1047, 42, tri_at, lambda i, n: exp_decay(i, 12) * edge(i, n, 2)),
        ),
        vol=0.40,
    )
    # list_entered: three tiny ticks, because a list is a number of things.
    list_tick = _tone(1319, 20, sine_at, lambda i, n: exp_decay(i, 5) * edge(i, n, 1.5))
    write_wav(
        "list_entered.wav",
        _concat(list_tick, _silence(28), list_tick, _silence(28), list_tick),
        vol=0.32,
    )
    # transcription_word_inserted: the quietest cue in the pack, because it
    # fires once per spoken word. Any louder and dictation becomes a woodpecker.
    write_wav(
        "transcription_word_inserted.wav",
        _tone(1568, 16, sine_at, lambda i, n: exp_decay(i, 3) * edge(i, n, 1)),
        vol=0.20,
    )


if __name__ == "__main__":
    generate_all()
