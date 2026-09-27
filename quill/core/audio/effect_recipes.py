"""Named effect recipes: the Converter's "make it sound better" in one choice.

The processing catalogue (:mod:`quill.core.audio.dsp`) has sixteen switches,
and a switch is a question: *do I want a de-esser?* Most people bringing a
recording to a converter do not know, and should not have to. They know the
problem -- "the speech is too quiet under the music", "there is a hum",
"this needs to pass ACX" -- so each recipe here is named for the problem it
solves and turns on the switches that solve it, in the order the catalogue
already applies them.

``custom`` is the escape hatch: the Converter's Effects dialog edits a
:class:`~quill.core.audio.dsp.DspOptions` directly and the result travels as
the custom recipe. Every recipe applies to the audio of a video conversion
too, so "Louder dialogue" on a film gives a new film with clearer speech.

Pure and wx-free.
"""

from __future__ import annotations

from dataclasses import dataclass

from quill.core.audio.dsp import DspOptions, build_dsp_filters


@dataclass(frozen=True, slots=True)
class EffectRecipe:
    """A named, one-choice set of effects."""

    id: str
    name: str
    description: str
    dsp: DspOptions


EFFECT_RECIPES: tuple[EffectRecipe, ...] = (
    EffectRecipe("none", "No effects", "The sound is converted exactly as it is.", DspOptions()),
    EffectRecipe(
        "clean_speech",
        "Clean up speech",
        "Removes rumble, hum and steady background hiss, softens harsh s sounds, "
        "and sets a comfortable listening level.",
        DspOptions(
            high_pass=True,
            remove_hum=True,
            noise_reduction=True,
            deesser=True,
            loudness="podcast",
            limiter=True,
        ),
    ),
    EffectRecipe(
        "podcast",
        "Podcast ready",
        "Cleans the voice, evens out loud and quiet speakers, and meets the "
        "podcast loudness standard of -16 LUFS.",
        DspOptions(
            high_pass=True,
            noise_reduction=True,
            deesser=True,
            compressor=True,
            loudness="podcast",
            limiter=True,
        ),
    ),
    EffectRecipe(
        "audiobook",
        "Audiobook, ACX ready",
        "Rumble filter, gentle noise reduction and the ACX loudness window of "
        "-20 LUFS with peaks held under -3 dB, as Audible requires.",
        DspOptions(high_pass=True, noise_reduction=True, loudness="audiobook", limiter=True),
    ),
    EffectRecipe(
        "voice_clarity",
        "Clearer voice for listening",
        "Lifts the frequencies that carry consonants, trims muddiness, and evens "
        "out the level -- easier on the ears and on hearing aids.",
        DspOptions(
            high_pass=True, voice_clarity=True, compressor=True, speech_normalize=True, limiter=True
        ),
    ),
    EffectRecipe(
        "dialogue",
        "Louder dialogue for films and TV",
        "Brings speech forward over music and effects, then evens out the "
        "loudness so explosions and whispers sit closer together.",
        DspOptions(dialogue_boost=True, leveler=True, loudness="podcast", limiter=True),
    ),
    EffectRecipe(
        "night",
        "Night listening",
        "Quiet parts come up and loud parts come down, so you can listen at low "
        "volume without reaching for the control.",
        DspOptions(compressor=True, leveler=True, limiter=True),
    ),
    EffectRecipe(
        "music",
        "Music, streaming loudness",
        "Normalizes to -14 LUFS, the level Spotify, YouTube and Apple Music play "
        "at, with a safety limiter.",
        DspOptions(loudness="music", limiter=True),
    ),
    EffectRecipe(
        "broadcast",
        "Broadcast standard, EBU R128",
        "Normalizes to -23 LUFS, the loudness standard for television and radio.",
        DspOptions(loudness="broadcast", limiter=True),
    ),
    EffectRecipe(
        "remove_hum",
        "Remove electrical hum",
        "Notches out 50 and 60 Hz mains hum and its first harmonic, and the rumble below it.",
        DspOptions(high_pass=True, remove_hum=True),
    ),
    EffectRecipe(
        "reduce_noise",
        "Reduce background noise",
        "Takes down steady hiss, fan and air-conditioner noise.",
        DspOptions(noise_reduction=True),
    ),
    EffectRecipe(
        "remove_silence",
        "Remove long silences",
        "Cuts every pause longer than half a second -- lectures and voice memos "
        "get shorter without losing a word.",
        DspOptions(trim_silence=True),
    ),
    EffectRecipe(
        "bass",
        "Bass boost",
        "Adds warmth and weight to thin-sounding music or small speakers.",
        DspOptions(bass_boost=True, limiter=True),
    ),
)

#: The recipe id the Effects dialog's own settings travel under.
CUSTOM_RECIPE_ID = "custom"

#: The recipe selected by default: change nothing.
DEFAULT_RECIPE_ID = "none"

_BY_ID: dict[str, EffectRecipe] = {recipe.id: recipe for recipe in EFFECT_RECIPES}


def recipe_by_id(recipe_id: str) -> EffectRecipe | None:
    """A built-in recipe by id, or ``None``."""
    return _BY_ID.get(recipe_id.strip().lower())


def recipe_choices() -> list[tuple[str, str]]:
    """``(id, spoken label)`` for the Effects choice, custom last."""
    rows = [(recipe.id, f"{recipe.name} -- {recipe.description}") for recipe in EFFECT_RECIPES]
    rows.append((CUSTOM_RECIPE_ID, "Custom -- the effects you chose in the Effects dialog"))
    return rows


def recipe_filters(recipe_id: str, custom: DspOptions | None = None) -> tuple[str, ...]:
    """The ``-af`` filter fragments for a recipe (``custom`` reads *custom*)."""
    if recipe_id == CUSTOM_RECIPE_ID:
        return build_dsp_filters(custom or DspOptions())
    recipe = recipe_by_id(recipe_id)
    return build_dsp_filters(recipe.dsp) if recipe is not None else ()


def describe_custom(dsp: DspOptions) -> str:
    """A short spoken summary of a custom effect set ("No effects" when empty)."""
    names: list[str] = []
    for flag, label in (
        ("high_pass", "rumble filter"),
        ("remove_hum", "hum removal"),
        ("noise_reduction", "noise reduction"),
        ("trim_silence", "silence removal"),
        ("deesser", "de-esser"),
        ("voice_clarity", "voice clarity"),
        ("bass_boost", "bass boost"),
        ("treble_boost", "treble boost"),
        ("dialogue_boost", "dialogue boost"),
        ("compressor", "compressor"),
        ("speech_normalize", "speech leveling"),
        ("leveler", "volume leveler"),
        ("limiter", "limiter"),
    ):
        if getattr(dsp, flag):
            names.append(label)
    if dsp.loudness:
        names.append(f"{dsp.loudness} loudness")
    if dsp.gain_db:
        names.append(f"gain {dsp.gain_db:+g} dB")
    if abs(dsp.tempo - 1.0) > 1e-6:
        names.append(f"speed {dsp.tempo:g}x")
    if dsp.fade_in_s:
        names.append(f"fade in {dsp.fade_in_s:g} s")
    if dsp.fade_out_s:
        names.append(f"fade out {dsp.fade_out_s:g} s")
    return ", ".join(names) if names else "No effects"
