"""Quill Radio's guided tutorials: the catalogue, assembled.

The content lives in one module per half-track, so no single file grows past
the size a person can hold in their head, and so a lesson can be found by the
name of the thing it teaches rather than by scrolling. This module is the only
thing anything else imports: it puts them in teaching order and hands out the
pure helpers from :mod:`quill.core.radio.tutorials.model`.

Order matters here. ``CATALOGUE`` is the order the contents tree reads, and
the contents tree is the first thing a new listener meets, so it runs from
"you have never opened this app" to "you have relied on it for a month".
"""

from __future__ import annotations

from quill.core.radio.tutorials import (
    beyond_podcasts,
    beyond_tv,
    browsing,
    extras,
    favorites_and_rows,
    first_hour,
    keys_and_settings,
    living_care,
    living_daily,
    own_sources,
    recording_basics,
    recording_more,
)
from quill.core.radio.tutorials.model import (
    TRACKS as TRACKS,
)
from quill.core.radio.tutorials.model import (
    KeyLookup as KeyLookup,
)
from quill.core.radio.tutorials.model import (
    Progress as Progress,
)
from quill.core.radio.tutorials.model import (
    Step as Step,
)
from quill.core.radio.tutorials.model import (
    Track as Track,
)
from quill.core.radio.tutorials.model import (
    Tutorial as Tutorial,
)
from quill.core.radio.tutorials.model import (
    by_slug as _by_slug,
)
from quill.core.radio.tutorials.model import (
    contents_label as contents_label,
)
from quill.core.radio.tutorials.model import (
    for_surface as _for_surface,
)
from quill.core.radio.tutorials.model import (
    key_phrase as key_phrase,
)
from quill.core.radio.tutorials.model import (
    render_step as render_step,
)
from quill.core.radio.tutorials.model import (
    render_tutorial as render_tutorial,
)
from quill.core.radio.tutorials.model import (
    search as _search,
)
from quill.core.radio.tutorials.model import (
    step_heading as step_heading,
)
from quill.core.radio.tutorials.model import (
    track_titles as track_titles,
)
from quill.core.radio.tutorials.model import (
    tutorials_in as _tutorials_in,
)
from quill.core.radio.tutorials.model import (
    validate as validate,
)

#: Every lesson, in the order its own module lists it.
_AUTHORED: tuple[Tutorial, ...] = (
    *first_hour.TUTORIALS,
    *browsing.TUTORIALS,
    *own_sources.TUTORIALS,
    *favorites_and_rows.TUTORIALS,
    *keys_and_settings.TUTORIALS,
    *recording_basics.TUTORIALS,
    *recording_more.TUTORIALS,
    *beyond_podcasts.TUTORIALS,
    *beyond_tv.TUTORIALS,
    *living_daily.TUTORIALS,
    *living_care.TUTORIALS,
    *extras.TUTORIALS,
)

#: Every lesson, in teaching order: by track, and within a track by the order
#: its module lists it. Grouping here rather than by hand means a lesson can
#: live in whichever module it reads best in -- the three in ``extras`` belong
#: to three different tracks -- without anybody maintaining a second order.
CATALOGUE: tuple[Tutorial, ...] = tuple(
    tutorial for track in TRACKS for tutorial in _AUTHORED if tutorial.track == track.id
)


def all_tutorials() -> tuple[Tutorial, ...]:
    return CATALOGUE


def find(slug: str) -> Tutorial | None:
    return _by_slug(slug, CATALOGUE)


def in_track(track_id: str) -> list[Tutorial]:
    return _tutorials_in(track_id, CATALOGUE)


def search(query: str) -> list[Tutorial]:
    return _search(query, CATALOGUE)


def for_surface(title: str) -> list[Tutorial]:
    return _for_surface(title, CATALOGUE)


def total_minutes() -> int:
    return sum(tutorial.minutes for tutorial in CATALOGUE)


def total_steps() -> int:
    return sum(tutorial.step_count for tutorial in CATALOGUE)
