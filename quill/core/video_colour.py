"""BT.709 colour for every H.264 file Studio writes (VIDEO-004).

Pictures arrive as RGB (the screen, a still picture) or as a camera's own
YUV. Left to itself FFmpeg converts RGB with the BT.601 matrix and writes no
colour tags, so an HD player has to guess -- and guesses wrong: pure red
comes out at Y 81 where BT.709 puts it at 63, and the whole picture looks
washed out. A blind presenter cannot see that, so the file must be right by
construction: convert with the BT.709 matrix to limited ("TV") range, and say
so in the stream.

The lesson, and the numbers, are from Tony Gebhard's TG Drop Deck
(https://github.com/tonygeb23/tg-drop-deck), which measured exactly this
fault on its own recordings. No code was copied.
"""

from __future__ import annotations

#: The conversion step: the BT.709 matrix to limited range, size unchanged.
#: It goes right before ``format=yuv420p`` so the scaler that produces the
#: YUV picture is the one told which matrix to use.
COLOUR_FILTER = "scale=out_color_matrix=bt709:out_range=tv"
#: The scaler marks the matrix and range on each frame but leaves primaries
#: and transfer unset, and FFmpeg now takes the frame's description over the
#: encoder's ``-color_primaries``/``-color_trc`` -- measured on FFmpeg 9,
#: where only two of the four tags reached the file without this step.
FRAME_TAGS = "setparams=color_primaries=bt709:color_trc=bt709:colorspace=bt709:range=tv"

#: The colour description written into the stream and the container.
COLOUR_TAGS: tuple[str, ...] = (
    "-colorspace",
    "bt709",
    "-color_primaries",
    "bt709",
    "-color_trc",
    "bt709",
    "-color_range",
    "tv",
)

#: What ``ffprobe`` reports for a correctly tagged stream.
EXPECTED_PROBE = {
    "color_space": "bt709",
    "color_primaries": "bt709",
    "color_transfer": "bt709",
    "color_range": "tv",
}


def to_yuv420p() -> str:
    """The filter steps that turn any picture into tagged BT.709 4:2:0."""
    return f"{COLOUR_FILTER},format=yuv420p,{FRAME_TAGS}"


def colour_tags() -> list[str]:
    return list(COLOUR_TAGS)


def colour_problems(found: dict[str, str]) -> list[str]:
    """Each colour field that is not what VIDEO-004 asks for, as a phrase."""
    problems = []
    for key, want in EXPECTED_PROBE.items():
        have = (found.get(key) or "").strip() or "not set"
        if have != want:
            problems.append(f"{key.replace('_', ' ')} is {have}, not {want}")
    return problems
